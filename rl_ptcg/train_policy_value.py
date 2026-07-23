"""Behavior-clone the rule policy and learn terminal value on trajectory JSONL."""
from __future__ import annotations

import argparse
from dataclasses import replace
from hashlib import blake2b
import json
import math
from pathlib import Path
import random

import torch
from torch.utils.data import DataLoader, Dataset

try:
    from .encoding import SCHEMA
    from .policy_value import DEFAULT_MATCHUP_NAMES, ModelConfig, PolicyValueNet, greedy_selection, selection_nll
    from .trajectory import TrajectoryRecord, read_jsonl
except ImportError:
    from encoding import SCHEMA
    from policy_value import DEFAULT_MATCHUP_NAMES, ModelConfig, PolicyValueNet, greedy_selection, selection_nll
    from trajectory import TrajectoryRecord, read_jsonl


def action_indices(action) -> list[int]:
    if isinstance(action, int):
        return [action]
    if isinstance(action, list):
        return [int(value) for value in action]
    return []


def rule_features(scores: list[float], count: int) -> list[list[float]]:
    if not scores:
        return [[0.0, 0.0] for _ in range(count)]
    clean = [max(-1e6, min(1e6, float(value))) for value in scores]
    mean = sum(clean) / len(clean)
    spread = max(max(clean) - min(clean), 1.0)
    order = sorted(range(len(clean)), key=lambda index: (-clean[index], index))
    ranks = {index: rank for rank, index in enumerate(order)}
    denominator = max(1, len(clean) - 1)
    return [
        [max(-2.0, min(2.0, (value - mean) / spread)), 1.0 - ranks[index] / denominator]
        for index, value in enumerate(clean)
    ]


def validation_episode(episode_id: str, fraction: float) -> bool:
    digest = blake2b(episode_id.encode("ascii", "backslashreplace"), digest_size=8).digest()
    return int.from_bytes(digest, "big") / float(2**64) < fraction


def deck_signature(record: TrajectoryRecord) -> str:
    if not record.opponent_deck:
        return "opponent:" + (record.opponent or record.matchup or "unknown")
    return "deck:" + ",".join(str(card_id) for card_id in sorted(record.opponent_deck))


def validation_record(record: TrajectoryRecord, fraction: float, group: str) -> bool:
    key = record.episode_id if group == "episode" else deck_signature(record)
    return validation_episode(key, fraction)


def canonical_matchup(value: str | None) -> str:
    text = (value or "unknown").lower()
    if "alak" in text:
        return "alakazam"
    if "arch" in text:
        return "archaludon"
    if "luc" in text:
        return "lucario"
    if "starmie" in text:
        return "starmie"
    if text.startswith("gt_") or "great_tusk" in text or "crustle" in text:
        return "great_tusk"
    if "drag" in text:
        return "dragapult"
    if "marnie" in text or text == "generic":
        return "marnie"
    if "iono" in text:
        return "iono"
    if "cynthia" in text:
        return "cynthia"
    if "okidogi" in text:
        return "okidogi"
    return "unknown"


def matchup_index(value: str | None, names=DEFAULT_MATCHUP_NAMES) -> int:
    name = canonical_matchup(value)
    return names.index(name) if name in names else 0


class Records(Dataset):
    def __init__(self, records: list[TrajectoryRecord]):
        self.records = records

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        return self.records[index]


def collate(records: list[TrajectoryRecord]) -> dict:
    max_options = max(len(record.option_vectors) for record in records)
    state_size = len(SCHEMA.state_feature_names)
    option_size = len(SCHEMA.option_feature_names)
    state = torch.full((len(records), state_size), -1.0, dtype=torch.float32)
    options = torch.full((len(records), max_options, option_size), -1.0, dtype=torch.float32)
    mask = torch.zeros((len(records), max_options), dtype=torch.bool)
    rules = torch.zeros((len(records), max_options, 2), dtype=torch.float32)
    rewards = torch.zeros(len(records), dtype=torch.float32)
    value_weights = torch.ones(len(records), dtype=torch.float32)
    policy_targets = torch.zeros(len(records), dtype=torch.bool)
    changed_targets = torch.zeros(len(records), dtype=torch.bool)
    selections = []
    matchup_ids = torch.zeros(len(records), dtype=torch.long)
    opponent_decks = torch.full((len(records), 60), -1, dtype=torch.long)
    for row, record in enumerate(records):
        if record.schema_version != SCHEMA.version:
            raise ValueError("trajectory schema mismatch: " + record.schema_version)
        state[row] = torch.tensor(record.state_vector, dtype=torch.float32)
        count = len(record.option_vectors)
        options[row, :count] = torch.tensor(record.option_vectors, dtype=torch.float32)
        mask[row, :count] = True
        rules[row, :count] = torch.tensor(rule_features(record.rule_scores, count), dtype=torch.float32)
        rewards[row] = float(record.reward or 0.0)
        value_weights[row] = float(record.value_weight)
        policy_targets[row] = bool(record.policy_target)
        changed_targets[row] = bool(
            record.policy_target
            and set(action_indices(record.selected_action)) != set(action_indices(record.rule_action))
        )
        selections.append(action_indices(record.selected_action) if record.policy_target else [])
        matchup_ids[row] = matchup_index(record.matchup or record.opponent)
        if record.opponent_deck:
            deck = [int(card_id) for card_id in record.opponent_deck[:60]]
            opponent_decks[row, :len(deck)] = torch.tensor(deck, dtype=torch.long)
    return {
        "state": state,
        "options": options,
        "mask": mask,
        "rule_features": rules,
        "reward": rewards,
        "value_weight": value_weights,
        "policy_target": policy_targets,
        "changed_target": changed_targets,
        "selections": selections,
        "matchup_ids": matchup_ids,
        "opponent_deck": opponent_decks,
        "metadata": [(record.opponent or "unknown", record.matchup or "unknown", record.episode_id,
                      record.step, record.policy_target)
                     for record in records],
    }


def load_records(paths: list[Path], max_records: int | None) -> list[TrajectoryRecord]:
    records = []
    for path in paths:
        inputs = sorted(path.glob("shard-*.jsonl")) if path.is_dir() else [path]
        if not inputs:
            raise FileNotFoundError("no trajectory shards found in %s" % path)
        for input_path in inputs:
            records.extend(read_jsonl(input_path))
            if max_records is not None and len(records) >= max_records:
                return records[:max_records]
    return records


def run_epoch(model, loader, device, optimizer, policy_weight, value_weight,
              changed_policy_weight, train):
    model.train(train)
    totals = {"loss": 0.0, "policy": 0.0, "value": 0.0, "value_weight": 0.0,
              "exact": 0, "policy_records": 0, "changed_exact": 0,
              "changed_records": 0, "records": 0}
    context = torch.enable_grad() if train else torch.inference_mode()
    with context:
        for batch in loader:
            state = batch["state"].to(device)
            options = batch["options"].to(device)
            mask = batch["mask"].to(device)
            rules = batch["rule_features"].to(device)
            matchup_ids = batch["matchup_ids"].to(device)
            opponent_deck = batch["opponent_deck"].to(device)
            reward = batch["reward"].to(device)
            value_weight_tensor = batch["value_weight"].to(device)
            logits, value = model(state, options, mask, rules, matchup_ids, opponent_deck)
            row_weights = torch.where(
                batch["changed_target"].to(device),
                torch.full((state.shape[0],), float(changed_policy_weight), device=device),
                torch.ones(state.shape[0], device=device),
            )
            policy_loss = selection_nll(logits, mask, batch["selections"], row_weights)
            value_elements = torch.nn.functional.smooth_l1_loss(
                value, reward, beta=0.2, reduction="none"
            )
            value_denominator = value_weight_tensor.sum().clamp_min(1e-8)
            value_loss = (value_elements * value_weight_tensor).sum() / value_denominator
            loss = policy_weight * policy_loss + value_weight * value_loss
            if train:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
            predictions = greedy_selection(logits.detach().cpu(), [len(x) for x in batch["selections"]])
            target_rows = batch["policy_target"].tolist()
            changed_rows = batch["changed_target"].tolist()
            exact = sum(
                bool(is_target) and set(a) == set(b)
                for a, b, is_target in zip(predictions, batch["selections"], target_rows)
            )
            size = len(batch["selections"])
            totals["loss"] += float(loss.detach()) * size
            totals["policy"] += float(policy_loss.detach()) * size
            totals["value"] += float((value_elements.detach() * value_weight_tensor).sum())
            totals["value_weight"] += float(value_denominator.detach())
            totals["exact"] += exact
            totals["changed_exact"] += sum(
                bool(is_changed) and set(a) == set(b)
                for a, b, is_changed in zip(predictions, batch["selections"], changed_rows)
            )
            totals["changed_records"] += sum(bool(value) for value in changed_rows)
            totals["policy_records"] += sum(bool(value) for value in target_rows)
            totals["records"] += size
    count = max(1, totals["records"])
    return {
        "loss": totals["loss"] / count,
        "policy_loss": totals["policy"] / count,
        "value_loss": totals["value"] / max(1e-8, totals["value_weight"]),
        "policy_exact": totals["exact"] / max(1, totals["policy_records"]),
        "policy_records": totals["policy_records"],
        "changed_policy_exact": totals["changed_exact"] / max(1, totals["changed_records"]),
        "changed_policy_records": totals["changed_records"],
        "records": totals["records"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", action="append", type=Path, required=True)
    parser.add_argument("--validation-data", action="append", type=Path, default=[],
                        help="Optional external trajectory files/directories used only for validation.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--value-weight", type=float, default=0.5)
    parser.add_argument("--policy-weight", type=float, default=1.0)
    parser.add_argument("--changed-policy-weight", type=float, default=1.0)
    parser.add_argument("--best-metric", choices=("loss", "policy_loss", "value_loss"), default="value_loss")
    parser.add_argument("--validation-fraction", type=float, default=0.15)
    parser.add_argument("--validation-group", choices=("episode", "deck"), default="episode",
                        help="Keep whole deck signatures together to measure deck generalization.")
    parser.add_argument("--exclude-opponent", action="append", default=[],
                        help="Drop a labeled opponent from training; may be repeated.")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-records", type=int)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--hidden-dim", type=int, default=256)
    parser.add_argument("--option-hidden-dim", type=int, default=128)
    parser.add_argument("--card-embedding-dim", type=int, default=12)
    parser.add_argument("--matchup-embedding-dim", type=int, default=16)
    parser.add_argument("--deck-embedding-dim", type=int, default=24)
    parser.add_argument("--dropout", type=float, default=0.05)
    parser.add_argument("--rule-prior-scale", type=float, default=1.0)
    parser.add_argument("--residual-logit-cap", type=float, default=1.0)
    parser.add_argument("--ignore-opponent-deck", action="store_true")
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--min-epochs", type=int, default=5)
    args = parser.parse_args()
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    records = load_records(args.data, args.max_records)
    if args.exclude_opponent:
        excluded = set(args.exclude_opponent)
        records = [record for record in records if (record.opponent or "unknown") not in excluded]
    if not records:
        parser.error("no trajectory records found")
    if args.validation_data:
        train_records = records
        valid_records = load_records(args.validation_data, None)
        validation_group_name = "external"
    else:
        train_records = [
            record for record in records
            if not validation_record(record, args.validation_fraction, args.validation_group)
        ]
        valid_records = [
            record for record in records
            if validation_record(record, args.validation_fraction, args.validation_group)
        ]
        validation_group_name = args.validation_group
    if not train_records or not valid_records:
        parser.error("train/validation split is empty")
    split_summary = {
        "records": len(records), "train_records": len(train_records),
        "validation_records": len(valid_records), "validation_group": validation_group_name,
        "train_deck_signatures": len({deck_signature(record) for record in train_records}),
        "validation_deck_signatures": len({deck_signature(record) for record in valid_records}),
        "excluded_opponents": sorted(args.exclude_opponent),
    }
    if args.ignore_opponent_deck:
        train_records = [replace(record, opponent_deck=None) for record in train_records]
        valid_records = [replace(record, opponent_deck=None) for record in valid_records]
    print(json.dumps({
        **split_summary,
    }, sort_keys=True), flush=True)
    config = ModelConfig(
        tuple(SCHEMA.state_feature_names), tuple(SCHEMA.option_feature_names),
        hidden_dim=args.hidden_dim, option_hidden_dim=args.option_hidden_dim,
        card_embedding_dim=args.card_embedding_dim,
        matchup_embedding_dim=args.matchup_embedding_dim,
        deck_embedding_dim=args.deck_embedding_dim,
        dropout=args.dropout,
        rule_prior_scale=args.rule_prior_scale,
        residual_logit_cap=args.residual_logit_cap,
    )
    device = torch.device(args.device)
    model = PolicyValueNet(config).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )
    generator = torch.Generator().manual_seed(args.seed)
    train_loader = DataLoader(
        Records(train_records), batch_size=args.batch_size, shuffle=True,
        collate_fn=collate, num_workers=0, generator=generator,
    )
    valid_loader = DataLoader(
        Records(valid_records), batch_size=args.batch_size, shuffle=False,
        collate_fn=collate, num_workers=0,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "split_summary.json").write_text(
        json.dumps(split_summary, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    history = []
    best_loss = math.inf
    stale_epochs = 0
    for epoch in range(1, args.epochs + 1):
        train_metrics = run_epoch(
            model, train_loader, device, optimizer, args.policy_weight, args.value_weight,
            args.changed_policy_weight, True
        )
        valid_metrics = run_epoch(
            model, valid_loader, device, None, args.policy_weight, args.value_weight,
            args.changed_policy_weight, False
        )
        row = {"epoch": epoch, "train": train_metrics, "validation": valid_metrics}
        history.append(row)
        checkpoint = {
            "model_config": config.to_dict(),
            "model_state": model.state_dict(),
            "schema": SCHEMA.to_dict(),
            "epoch": epoch,
            "metrics": row,
            "training": {
                "data": [str(path) for path in args.data],
                "seed": args.seed,
                "validation_fraction": args.validation_fraction,
                "validation_group": validation_group_name,
                "validation_data": [str(path) for path in args.validation_data],
                "excluded_opponents": sorted(args.exclude_opponent),
                "policy_weight": args.policy_weight,
                "changed_policy_weight": args.changed_policy_weight,
                "value_weight": args.value_weight,
                "best_metric": args.best_metric,
                "ignore_opponent_deck": args.ignore_opponent_deck,
                "rule_prior_scale": args.rule_prior_scale,
                "residual_logit_cap": args.residual_logit_cap,
            },
        }
        torch.save(checkpoint, args.output_dir / ("checkpoint_%04d.pt" % epoch))
        candidate_metric = valid_metrics[args.best_metric]
        if candidate_metric < best_loss:
            best_loss = candidate_metric
            stale_epochs = 0
            torch.save(checkpoint, args.output_dir / "best.pt")
        else:
            stale_epochs += 1
        (args.output_dir / "history.json").write_text(
            json.dumps(history, indent=2, sort_keys=True), encoding="ascii"
        )
        print(json.dumps(row, sort_keys=True), flush=True)
        if epoch >= args.min_epochs and stale_epochs >= args.patience:
            print("early stopping after %d stale epochs" % stale_epochs)
            break
    print("best validation %s" % args.best_metric, best_loss)


if __name__ == "__main__":
    main()
