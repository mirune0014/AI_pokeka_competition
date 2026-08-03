"""Fixed-data behavior cloning for an independent legal-action actor."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random
from typing import Any, Iterable, Mapping, Sequence

import torch
from torch.nn import functional as F

from .bc_actor import apply_legal_action_mask, batched_actor_logits
from .encoders import ACTION_DIM, STATE_DIM
from .frozen_sources import checkpoint_source_hashes, sha256_file
from .model import (
    checkpoint_metadata,
    load_checkpoint,
    save_checkpoint,
    sha256_checkpoint,
)


BC_TRAINING_SCHEMA_VERSION = "behavior-cloning-training-v1"
ACTOR_PREFIXES = ("state_encoder.", "action_encoder.", "residual_head.")


@dataclass(frozen=True)
class BCRow:
    episode_id: str
    decision_index: int
    state_vector: tuple[float, ...]
    action_vectors: tuple[tuple[float, ...], ...]
    legal_mask: tuple[bool, ...]
    teacher_index: int
    option_type: int
    locked_validation: bool


def actor_state_sha256(model: Any) -> str:
    digest = hashlib.sha256()
    selected = {
        name: tensor.detach().cpu().contiguous()
        for name, tensor in model.state_dict().items()
        if name.startswith(ACTOR_PREFIXES)
    }
    for name in sorted(selected):
        tensor = selected[name]
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(str(tensor.dtype).encode("ascii") + b"\0")
        digest.update(json.dumps(list(tensor.shape), separators=(",", ":")).encode("ascii") + b"\0")
        digest.update(tensor.numpy().tobytes(order="C"))
    return digest.hexdigest().upper()


def _episode_paths(episodes_dir: Path) -> list[Path]:
    paths = sorted(episodes_dir.glob("*.json"))
    if not paths:
        raise ValueError("BC episode directory contains no JSON episodes")
    if any(not path.is_file() or path.is_symlink() for path in paths):
        raise ValueError("BC episode inputs must be regular JSON files")
    return paths


def _extract_rows(
    episodes: Sequence[Mapping[str, Any]],
    *,
    locked_validation: bool,
) -> tuple[list[BCRow], Counter[str]]:
    rows: list[BCRow] = []
    excluded: Counter[str] = Counter()
    for episode in episodes:
        episode_id = str(episode["episode_id"])
        for decision in episode.get("decisions") or ():
            teacher = tuple(decision.get("teacher_action") or ())
            options = tuple(decision.get("legal_semantic_options") or ())
            state = tuple(decision.get("state_vector") or ())
            actions = tuple(
                tuple(vector) for vector in (decision.get("action_vectors") or ())
            )
            mask_source = decision.get("legal_option_mask")
            legal_mask = tuple(
                bool(value)
                for value in (
                    mask_source
                    if mask_source is not None
                    else (True for _ in options)
                )
            )
            if len(teacher) != 1:
                excluded["teacher_action_not_single_index"] += 1
                continue
            if len(options) < 2:
                excluded["fewer_than_two_options"] += 1
                continue
            teacher_index = teacher[0]
            if (
                not isinstance(teacher_index, int)
                or isinstance(teacher_index, bool)
                or not 0 <= teacher_index < len(options)
            ):
                excluded["invalid_teacher_index"] += 1
                continue
            if (
                len(state) != STATE_DIM
                or len(actions) != len(options)
                or any(len(vector) != ACTION_DIM for vector in actions)
                or len(legal_mask) != len(options)
            ):
                excluded["missing_or_wrong_vector_shape"] += 1
                continue
            if not any(legal_mask):
                excluded["no_legal_action"] += 1
                continue
            if not legal_mask[teacher_index]:
                excluded["teacher_action_masked_illegal"] += 1
                continue
            try:
                option_type = int(options[teacher_index]["payload"]["option_type"])
            except (KeyError, TypeError, ValueError):
                excluded["missing_teacher_option_type"] += 1
                continue
            values = (*state, *(value for vector in actions for value in vector))
            if any(not math.isfinite(float(value)) for value in values):
                excluded["nonfinite_vector"] += 1
                continue
            rows.append(
                BCRow(
                    episode_id=episode_id,
                    decision_index=int(decision["decision_index"]),
                    state_vector=tuple(float(value) for value in state),
                    action_vectors=tuple(
                        tuple(float(value) for value in vector) for vector in actions
                    ),
                    legal_mask=legal_mask,
                    teacher_index=teacher_index,
                    option_type=option_type,
                    locked_validation=bool(
                        locked_validation and decision.get("ppo_eligible")
                    ),
                )
            )
    return rows, excluded


def load_bc_split(
    episodes_dir: Path,
    split_spec_path: Path,
) -> dict[str, Any]:
    split_spec = json.loads(split_spec_path.read_text(encoding="utf-8"))
    validation_ids = tuple(str(value) for value in split_spec["validation_episode_ids"])
    validation_set = set(validation_ids)
    paths = _episode_paths(episodes_dir)
    episodes = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    by_id: dict[str, Mapping[str, Any]] = {}
    path_by_id: dict[str, Path] = {}
    for path, episode in zip(paths, episodes):
        episode_id = str(episode.get("episode_id"))
        if not episode_id or episode_id in by_id:
            raise ValueError("BC episodes have a missing or duplicate episode_id")
        by_id[episode_id] = episode
        path_by_id[episode_id] = path
    missing = validation_set - set(by_id)
    if missing:
        raise ValueError(f"locked validation episodes are missing: {sorted(missing)}")
    train_ids = tuple(sorted(set(by_id) - validation_set))
    if not train_ids or set(train_ids) & validation_set:
        raise ValueError("BC episode train/validation split is invalid")
    train_episodes = [by_id[episode_id] for episode_id in train_ids]
    validation_episodes = [by_id[episode_id] for episode_id in validation_ids]
    train_rows, train_excluded = _extract_rows(
        train_episodes,
        locked_validation=False,
    )
    validation_rows, validation_excluded = _extract_rows(
        validation_episodes,
        locked_validation=True,
    )
    if not train_rows or not validation_rows:
        raise ValueError("BC split has no supervised rows")
    expected_locked = int(split_spec["expected"]["validation_ppo_row_count"])
    locked_count = sum(row.locked_validation for row in validation_rows)
    if locked_count != expected_locked:
        raise ValueError(
            f"locked validation row count mismatch: {locked_count} != {expected_locked}"
        )
    dataset_receipt = hashlib.sha256()
    for episode_id in sorted(by_id):
        dataset_receipt.update(episode_id.encode("utf-8") + b"\0")
        dataset_receipt.update(sha256_file(path_by_id[episode_id]).encode("ascii") + b"\n")
    return {
        "train_rows": train_rows,
        "validation_rows": validation_rows,
        "train_episode_ids": train_ids,
        "validation_episode_ids": validation_ids,
        "train_excluded": dict(sorted(train_excluded.items())),
        "validation_excluded": dict(sorted(validation_excluded.items())),
        "dataset_sha256": dataset_receipt.hexdigest().upper(),
        "episode_receipts": {
            episode_id: sha256_file(path_by_id[episode_id])
            for episode_id in sorted(by_id)
        },
    }


def _batches(
    rows: Sequence[BCRow],
    indices: Sequence[int],
    batch_size: int,
) -> Iterable[list[BCRow]]:
    for start in range(0, len(indices), batch_size):
        yield [rows[index] for index in indices[start : start + batch_size]]


def _collate(
    rows: Sequence[BCRow],
    device: str,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    maximum = max(len(row.action_vectors) for row in rows)
    states = torch.tensor(
        [row.state_vector for row in rows],
        dtype=torch.float32,
        device=device,
    )
    actions = torch.zeros(
        (len(rows), maximum, ACTION_DIM),
        dtype=torch.float32,
        device=device,
    )
    mask = torch.zeros(
        (len(rows), maximum),
        dtype=torch.bool,
        device=device,
    )
    targets = torch.tensor(
        [row.teacher_index for row in rows],
        dtype=torch.long,
        device=device,
    )
    for index, row in enumerate(rows):
        count = len(row.action_vectors)
        actions[index, :count] = torch.tensor(
            row.action_vectors,
            dtype=torch.float32,
            device=device,
        )
        mask[index, :count] = torch.tensor(
            row.legal_mask,
            dtype=torch.bool,
            device=device,
        )
    return states, actions, mask, targets


def evaluate(
    model: Any,
    rows: Sequence[BCRow],
    *,
    batch_size: int,
    device: str,
) -> dict[str, Any]:
    model.eval()
    cross_entropy_sum = 0.0
    entropy_sum = 0.0
    correct = 0
    illegal = 0
    family_total: Counter[int] = Counter()
    family_correct: Counter[int] = Counter()
    locked_total = 0
    locked_correct = 0
    predictions: list[int] = []
    with torch.no_grad():
        indices = list(range(len(rows)))
        offset = 0
        for batch in _batches(rows, indices, batch_size):
            states, actions, mask, targets = _collate(batch, device)
            logits = apply_legal_action_mask(
                batched_actor_logits(model, states, actions),
                mask,
            )
            losses = F.cross_entropy(logits, targets, reduction="none")
            probabilities = F.softmax(logits, dim=1)
            log_probabilities = F.log_softmax(logits, dim=1)
            entropy = -(probabilities * log_probabilities.masked_fill(~mask, 0.0)).sum(dim=1)
            predicted = logits.argmax(dim=1)
            cross_entropy_sum += float(losses.sum().cpu())
            entropy_sum += float(entropy.sum().cpu())
            correct_flags = predicted.eq(targets)
            correct += int(correct_flags.sum().cpu())
            for local_index, row in enumerate(batch):
                prediction = int(predicted[local_index].cpu())
                predictions.append(prediction)
                illegal += int(not row.legal_mask[prediction])
                family_total[row.option_type] += 1
                family_correct[row.option_type] += int(bool(correct_flags[local_index]))
                if row.locked_validation:
                    locked_total += 1
                    locked_correct += int(bool(correct_flags[local_index]))
            offset += len(batch)
    if offset != len(rows) or len(predictions) != len(rows):
        raise AssertionError("BC evaluation row accounting failed")
    family_metrics = {
        str(option_type): {
            "rows": family_total[option_type],
            "teacher_top1_correct": family_correct[option_type],
            "teacher_top1_accuracy": family_correct[option_type] / family_total[option_type],
        }
        for option_type in sorted(family_total)
    }
    return {
        "rows": len(rows),
        "teacher_top1_correct": correct,
        "teacher_top1_accuracy": correct / len(rows),
        "cross_entropy": cross_entropy_sum / len(rows),
        "entropy": entropy_sum / len(rows),
        "illegal_action_count": illegal,
        "fallback_count": 0,
        "locked_validation_rows": locked_total,
        "locked_validation_teacher_argmax_matches": locked_correct,
        "locked_validation_teacher_argmax_accuracy": (
            None if locked_total == 0 else locked_correct / locked_total
        ),
        "by_option_type": family_metrics,
        "predictions": predictions,
    }


def train(args: argparse.Namespace) -> dict[str, Any]:
    if args.device != "cpu":
        raise ValueError("the minimal deterministic BC experiment uses CPU only")
    if args.epochs <= 0 or args.batch_size <= 0 or args.learning_rate <= 0.0:
        raise ValueError("BC epochs, batch size, and learning rate must be positive")
    output_checkpoint = Path(args.output_checkpoint)
    report_path = Path(args.report)
    if output_checkpoint.exists() or report_path.exists():
        raise FileExistsError("BC output checkpoint/report already exists")
    output_checkpoint.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)

    split = load_bc_split(Path(args.episodes_dir), Path(args.split_spec))
    train_rows: list[BCRow] = split["train_rows"]
    validation_rows: list[BCRow] = split["validation_rows"]
    source_hashes = checkpoint_source_hashes()
    model, input_metadata, _ = load_checkpoint(
        Path(args.input_checkpoint),
        expected_source_hashes=source_hashes,
        device=args.device,
    )
    for parameter in model.value_head.parameters():
        parameter.requires_grad_(False)
    actor_parameters = [
        parameter
        for name, parameter in model.named_parameters()
        if name.startswith(ACTOR_PREFIXES)
    ]
    if not actor_parameters:
        raise ValueError("BC model exposes no actor parameters")
    optimizer = torch.optim.Adam(actor_parameters, lr=args.learning_rate)
    generator = torch.Generator(device="cpu")
    generator.manual_seed(args.seed)
    epoch_losses: list[float] = []
    model.train()
    for _ in range(args.epochs):
        permutation = torch.randperm(len(train_rows), generator=generator).tolist()
        loss_sum = 0.0
        seen = 0
        for batch in _batches(train_rows, permutation, args.batch_size):
            states, actions, mask, targets = _collate(batch, args.device)
            logits = apply_legal_action_mask(
                batched_actor_logits(model, states, actions),
                mask,
            )
            loss = F.cross_entropy(logits, targets)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(actor_parameters, 1.0)
            optimizer.step()
            loss_sum += float(loss.detach().cpu()) * len(batch)
            seen += len(batch)
        epoch_losses.append(loss_sum / seen)

    train_metrics = evaluate(
        model,
        train_rows,
        batch_size=args.batch_size,
        device=args.device,
    )
    validation_metrics = evaluate(
        model,
        validation_rows,
        batch_size=args.batch_size,
        device=args.device,
    )
    actor_sha = actor_state_sha256(model)
    metadata = checkpoint_metadata(
        source_hashes=source_hashes,
        training={
            "schema_version": BC_TRAINING_SCHEMA_VERSION,
            "algorithm": "teacher_action_behavior_cloning",
            "actor_logits_only": True,
            "teacher_fixed_margin": 0.0,
            "legal_action_mask": True,
            "input_checkpoint_sha256": sha256_checkpoint(args.input_checkpoint),
            "dataset_sha256": split["dataset_sha256"],
            "split_spec_sha256": sha256_file(Path(args.split_spec)),
            "seed": args.seed,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "actor_state_sha256": actor_sha,
            "future_ppo_kl_reference": True,
            "value_head_used": False,
        },
    )
    checkpoint_sha = save_checkpoint(
        output_checkpoint,
        model,
        metadata,
        optimizer=optimizer,
    )
    reloaded, reloaded_metadata, _ = load_checkpoint(
        output_checkpoint,
        expected_source_hashes=source_hashes,
        device=args.device,
    )
    reload_actor_sha = actor_state_sha256(reloaded)
    reload_validation = evaluate(
        reloaded,
        validation_rows,
        batch_size=args.batch_size,
        device=args.device,
    )
    reload_predictions_match = (
        validation_metrics["predictions"] == reload_validation["predictions"]
    )
    if actor_sha != reload_actor_sha or not reload_predictions_match:
        raise ValueError("BC checkpoint save/reload changed actor outputs")

    major_family_threshold = int(args.major_family_min_validation_rows)
    major_family_results = {
        family: metrics
        for family, metrics in validation_metrics["by_option_type"].items()
        if int(metrics["rows"]) >= major_family_threshold
    }
    offline_pass = bool(
        validation_metrics["teacher_top1_accuracy"] >= 0.98
        and major_family_results
        and all(
            metrics["teacher_top1_accuracy"] >= 0.95
            for metrics in major_family_results.values()
        )
        and validation_metrics["illegal_action_count"] == 0
        and validation_metrics["fallback_count"] == 0
    )
    validation_metrics.pop("predictions")
    train_metrics.pop("predictions")
    reload_validation.pop("predictions")
    report = {
        "schema_version": BC_TRAINING_SCHEMA_VERSION,
        "seed": args.seed,
        "configuration": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "device": args.device,
            "teacher_fixed_margin": 0.0,
            "actor_logits_only": True,
            "legal_action_mask": True,
            "major_family_min_validation_rows": major_family_threshold,
        },
        "inputs": {
            "input_checkpoint": str(Path(args.input_checkpoint).resolve()),
            "input_checkpoint_sha256": sha256_checkpoint(args.input_checkpoint),
            "input_actor_state_sha256": actor_state_sha256(
                load_checkpoint(
                    Path(args.input_checkpoint),
                    expected_source_hashes=source_hashes,
                    device=args.device,
                )[0]
            ),
            "episodes_dir": str(Path(args.episodes_dir).resolve()),
            "dataset_sha256": split["dataset_sha256"],
            "split_spec": str(Path(args.split_spec).resolve()),
            "split_spec_sha256": sha256_file(Path(args.split_spec)),
            "train_episode_count": len(split["train_episode_ids"]),
            "validation_episode_count": len(split["validation_episode_ids"]),
            "episode_overlap_count": len(
                set(split["train_episode_ids"]) & set(split["validation_episode_ids"])
            ),
        },
        "dataset": {
            "train_supervised_rows": len(train_rows),
            "validation_supervised_rows": len(validation_rows),
            "train_excluded": split["train_excluded"],
            "validation_excluded": split["validation_excluded"],
        },
        "training": {
            "first_epoch_cross_entropy": epoch_losses[0],
            "final_epoch_cross_entropy": epoch_losses[-1],
            "train_metrics": train_metrics,
        },
        "validation": validation_metrics,
        "major_family_validation": major_family_results,
        "checkpoint": {
            "path": str(output_checkpoint.resolve()),
            "sha256": checkpoint_sha,
            "actor_state_sha256": actor_sha,
            "future_ppo_kl_reference": True,
            "reload_actor_state_sha256": reload_actor_sha,
            "reload_predictions_match": reload_predictions_match,
            "metadata_training": reloaded_metadata["training"],
        },
        "offline_provisional_pass": offline_pass,
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-checkpoint", required=True)
    parser.add_argument("--episodes-dir", required=True)
    parser.add_argument("--split-spec", required=True)
    parser.add_argument("--output-checkpoint", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--major-family-min-validation-rows", type=int, default=10)
    parser.add_argument("--device", default="cpu")
    return parser


def main() -> int:
    report = train(build_parser().parse_args())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
