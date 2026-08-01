"""Behavior cloning over complete legal-action candidate indices."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random
from typing import Any, Mapping, Sequence

import torch
from torch.nn import functional as F

from .build_complete_bc_dataset import DATASET_SCHEMA_VERSION
from .encoders import ACTION_DIM, STATE_DIM
from .frozen_sources import checkpoint_source_hashes, sha256_file
from .model import checkpoint_metadata, load_checkpoint, save_checkpoint, sha256_checkpoint
from .train_bc import ACTOR_PREFIXES, actor_state_sha256


TRAINING_SCHEMA_VERSION = "complete-action-behavior-cloning-v1"


def _load_dataset(path: Path) -> dict[str, Any]:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != DATASET_SCHEMA_VERSION
        or int(payload.get("state_dim", -1)) != STATE_DIM
        or int(payload.get("action_dim", -1)) != ACTION_DIM
    ):
        raise ValueError("complete-action BC dataset schema mismatch")
    tensors = payload.get("tensors") or {}
    required = {
        "states",
        "option_vectors",
        "option_offsets",
        "decision_candidate_offsets",
        "candidate_member_offsets",
        "candidate_members",
        "targets",
        "episode_indices",
        "family_indices",
        "optional_flags",
        "multiple_flags",
    }
    if set(tensors) != required:
        raise ValueError("complete-action BC dataset tensor set mismatch")
    return payload


def _split_indices(payload: Mapping[str, Any]) -> tuple[list[int], list[int]]:
    episodes = payload["episodes"]
    validation_episode_indices = {
        index for index, row in enumerate(episodes) if row["split"] == "validation"
    }
    episode_indices = payload["tensors"]["episode_indices"]
    train: list[int] = []
    validation: list[int] = []
    for index, episode_index in enumerate(episode_indices.tolist()):
        (validation if episode_index in validation_episode_indices else train).append(index)
    if not train or not validation:
        raise ValueError("complete-action BC train/validation rows are empty")
    return train, validation


def _collate(
    payload: Mapping[str, Any],
    indices: Sequence[int],
    *,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    tensors = payload["tensors"]
    option_offsets = tensors["option_offsets"]
    decision_candidate_offsets = tensors["decision_candidate_offsets"]
    candidate_member_offsets = tensors["candidate_member_offsets"]
    candidate_members = tensors["candidate_members"]
    maximum_options = max(
        int(option_offsets[index + 1] - option_offsets[index]) for index in indices
    )
    maximum_candidates = max(
        int(decision_candidate_offsets[index + 1] - decision_candidate_offsets[index])
        for index in indices
    )
    states = tensors["states"][list(indices)].to(device)
    options = torch.zeros(
        (len(indices), maximum_options, ACTION_DIM),
        dtype=torch.float32,
        device=device,
    )
    membership = torch.zeros(
        (len(indices), maximum_candidates, maximum_options),
        dtype=torch.float32,
        device=device,
    )
    mask = torch.zeros(
        (len(indices), maximum_candidates),
        dtype=torch.bool,
        device=device,
    )
    targets = tensors["targets"][list(indices)].to(device)
    for batch_index, row_index in enumerate(indices):
        option_start = int(option_offsets[row_index])
        option_end = int(option_offsets[row_index + 1])
        option_count = option_end - option_start
        if option_count:
            options[batch_index, :option_count] = tensors["option_vectors"][option_start:option_end].to(device)
        candidate_start = int(decision_candidate_offsets[row_index])
        candidate_end = int(decision_candidate_offsets[row_index + 1])
        mask[batch_index, : candidate_end - candidate_start] = True
        for local_candidate, candidate_index in enumerate(range(candidate_start, candidate_end)):
            member_start = int(candidate_member_offsets[candidate_index])
            member_end = int(candidate_member_offsets[candidate_index + 1])
            members = candidate_members[member_start:member_end].to(device=device, dtype=torch.int64)
            if len(members):
                membership[batch_index, local_candidate, members] = 1.0
    return states, options, membership, mask, targets


def _logits(
    model: Any,
    states: torch.Tensor,
    options: torch.Tensor,
    membership: torch.Tensor,
    mask: torch.Tensor,
) -> torch.Tensor:
    state_hidden = model.state_encoder(states)
    option_hidden = model.action_encoder(options)
    pooled = torch.bmm(membership, option_hidden)
    expanded_state = state_hidden.unsqueeze(1).expand(-1, pooled.shape[1], -1)
    logits = model.residual_head(torch.cat((expanded_state, pooled), dim=-1)).squeeze(-1)
    if logits.shape != mask.shape or not bool(torch.isfinite(logits).all()):
        raise ValueError("complete-action batched logits are invalid")
    return logits.masked_fill(~mask, -torch.inf)


def _batches(indices: Sequence[int], batch_size: int) -> list[Sequence[int]]:
    return [indices[start : start + batch_size] for start in range(0, len(indices), batch_size)]


def evaluate(
    model: Any,
    payload: Mapping[str, Any],
    indices: Sequence[int],
    *,
    batch_size: int,
    device: torch.device,
) -> dict[str, Any]:
    tensors = payload["tensors"]
    inverse_families = {value: key for key, value in payload["family_table"].items()}
    total_loss = total_entropy = 0.0
    correct = 0
    family_total: Counter[str] = Counter()
    family_correct: Counter[str] = Counter()
    optional_total = optional_correct = 0
    multiple_total = multiple_correct = 0
    model.eval()
    with torch.no_grad():
        for batch in _batches(indices, batch_size):
            states, options, membership, mask, targets = _collate(payload, batch, device=device)
            logits = _logits(model, states, options, membership, mask)
            losses = F.cross_entropy(logits, targets, reduction="none")
            probabilities = F.softmax(logits, dim=1)
            log_probabilities = F.log_softmax(logits, dim=1).masked_fill(~mask, 0.0)
            entropy = -(probabilities * log_probabilities).sum(dim=1)
            predicted = logits.argmax(dim=1)
            flags = predicted.eq(targets)
            total_loss += float(losses.sum().cpu())
            total_entropy += float(entropy.sum().cpu())
            correct += int(flags.sum().cpu())
            for local, row_index in enumerate(batch):
                hit = int(bool(flags[local]))
                family = inverse_families[int(tensors["family_indices"][row_index])]
                family_total[family] += 1
                family_correct[family] += hit
                if bool(tensors["optional_flags"][row_index]):
                    optional_total += 1
                    optional_correct += hit
                if bool(tensors["multiple_flags"][row_index]):
                    multiple_total += 1
                    multiple_correct += hit
    rows = len(indices)
    return {
        "rows": rows,
        "complete_action_teacher_top1_correct": correct,
        "complete_action_teacher_top1_accuracy": correct / rows,
        "cross_entropy": total_loss / rows,
        "entropy": total_entropy / rows,
        "illegal_action_count": 0,
        "representability_fallback_count": 0,
        "by_action_family": {
            family: {
                "rows": family_total[family],
                "teacher_top1_correct": family_correct[family],
                "teacher_top1_accuracy": family_correct[family] / family_total[family],
            }
            for family in sorted(family_total)
        },
        "optional_selection": {
            "rows": optional_total,
            "teacher_top1_correct": optional_correct,
            "teacher_top1_accuracy": None if optional_total == 0 else optional_correct / optional_total,
        },
        "multiple_selection": {
            "rows": multiple_total,
            "teacher_top1_correct": multiple_correct,
            "teacher_top1_accuracy": None if multiple_total == 0 else multiple_correct / multiple_total,
        },
    }


def train(args: argparse.Namespace) -> dict[str, Any]:
    if args.epochs <= 0 or args.batch_size <= 0 or args.learning_rate <= 0:
        raise ValueError("complete-action BC hyperparameters must be positive")
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA was requested but is unavailable")
    output_checkpoint = args.output_checkpoint.resolve()
    report_path = args.report.resolve()
    if output_checkpoint.exists() or report_path.exists():
        raise FileExistsError("complete-action BC output already exists")
    output_checkpoint.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(args.seed)
    torch.use_deterministic_algorithms(True)
    payload = _load_dataset(args.dataset)
    train_indices, validation_indices = _split_indices(payload)
    source_hashes = checkpoint_source_hashes()
    model, _, _ = load_checkpoint(
        args.input_checkpoint,
        expected_source_hashes=source_hashes,
        device=device,
    )
    for parameter in model.value_head.parameters():
        parameter.requires_grad_(False)
    actor_parameters = [
        parameter
        for name, parameter in model.named_parameters()
        if name.startswith(ACTOR_PREFIXES)
    ]
    optimizer = torch.optim.Adam(actor_parameters, lr=args.learning_rate)
    generator = torch.Generator(device="cpu")
    generator.manual_seed(args.seed)
    epoch_losses: list[float] = []
    model.train()
    for epoch in range(args.epochs):
        permutation = torch.randperm(len(train_indices), generator=generator).tolist()
        shuffled = [train_indices[index] for index in permutation]
        loss_sum = 0.0
        seen = 0
        for batch in _batches(shuffled, args.batch_size):
            states, options, membership, mask, targets = _collate(payload, batch, device=device)
            logits = _logits(model, states, options, membership, mask)
            loss = F.cross_entropy(logits, targets)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(actor_parameters, args.gradient_clip)
            optimizer.step()
            loss_sum += float(loss.detach().cpu()) * len(batch)
            seen += len(batch)
        epoch_loss = loss_sum / seen
        epoch_losses.append(epoch_loss)
        print(json.dumps({"seed": args.seed, "epoch": epoch + 1, "epochs": args.epochs, "train_cross_entropy": epoch_loss}), flush=True)

    train_metrics = evaluate(
        model,
        payload,
        train_indices,
        batch_size=args.batch_size,
        device=device,
    )
    validation_metrics = evaluate(
        model,
        payload,
        validation_indices,
        batch_size=args.batch_size,
        device=device,
    )
    actor_sha = actor_state_sha256(model)
    metadata = checkpoint_metadata(
        source_hashes=source_hashes,
        training={
            "schema_version": TRAINING_SCHEMA_VERSION,
            "algorithm": "complete_legal_action_behavior_cloning",
            "complete_action_actor_logits_only": True,
            "teacher_fixed_margin": 0.0,
            "candidate_softmax": True,
            "set_pooling": "sum_of_selected_option_embeddings",
            "dataset_sha256": sha256_file(args.dataset),
            "input_checkpoint_sha256": sha256_checkpoint(args.input_checkpoint),
            "seed": args.seed,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "future_ppo_kl_reference_accepted": False,
            "future_ppo_kl_reference_candidate": True,
            "actor_state_sha256": actor_sha,
            "value_head_used": False,
        },
    )
    checkpoint_sha = save_checkpoint(output_checkpoint, model, metadata, optimizer=optimizer)
    reloaded, reloaded_metadata, _ = load_checkpoint(
        output_checkpoint,
        expected_source_hashes=source_hashes,
        device=device,
    )
    reload_sha = actor_state_sha256(reloaded)
    reload_validation = evaluate(
        reloaded,
        payload,
        validation_indices,
        batch_size=args.batch_size,
        device=device,
    )
    if reload_sha != actor_sha or reload_validation != validation_metrics:
        raise ValueError("complete-action BC save/reload changed validation results")
    report = {
        "schema_version": TRAINING_SCHEMA_VERSION,
        "seed": args.seed,
        "configuration": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "gradient_clip": args.gradient_clip,
            "device": str(device),
            "validation_model_selection": False,
            "state_encoder_architecture_changed": False,
            "reward_changed": False,
            "ppo_performed": False,
        },
        "inputs": {
            "dataset": str(args.dataset.resolve()),
            "dataset_sha256": sha256_file(args.dataset),
            "input_checkpoint": str(args.input_checkpoint.resolve()),
            "input_checkpoint_sha256": sha256_checkpoint(args.input_checkpoint),
            "train_rows": len(train_indices),
            "validation_rows": len(validation_indices),
            "train_episodes": payload["counts"]["train_episodes"],
            "validation_episodes": payload["counts"]["validation_episodes"],
            "episode_overlap_count": 0,
        },
        "training": {
            "first_epoch_cross_entropy": epoch_losses[0],
            "final_epoch_cross_entropy": epoch_losses[-1],
            "metrics": train_metrics,
        },
        "validation": validation_metrics,
        "checkpoint": {
            "path": str(output_checkpoint),
            "sha256": checkpoint_sha,
            "actor_state_sha256": actor_sha,
            "reload_actor_state_sha256": reload_sha,
            "reload_metrics_match": True,
            "future_ppo_kl_reference_accepted": False,
            "metadata_training": reloaded_metadata["training"],
        },
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"seed": args.seed, "validation": validation_metrics, "checkpoint_sha256": checkpoint_sha}, ensure_ascii=False))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--input-checkpoint", type=Path, required=True)
    parser.add_argument("--output-checkpoint", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--gradient-clip", type=float, default=1.0)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    return parser


def main(argv: list[str] | None = None) -> int:
    train(build_parser().parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
