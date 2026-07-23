"""Evaluate policy agreement and value calibration by opponent bucket."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path

import torch
from torch.utils.data import DataLoader

try:
    from .policy_value import ModelConfig, PolicyValueNet, greedy_selection
    from .train_policy_value import Records, collate, load_records
except ImportError:
    from policy_value import ModelConfig, PolicyValueNet, greedy_selection
    from train_policy_value import Records, collate, load_records


def blank_metrics():
    return {"records": 0, "policy_exact": 0, "value_abs": 0.0, "brier": 0.0,
            "predicted_value": 0.0, "target_value": 0.0, "_policy_records": 0}


def finish(value):
    count = max(1, value["records"])
    return {
        "records": value["records"],
        "policy_exact": value["policy_exact"] / max(1, value["_policy_records"]),
        "value_mae": value["value_abs"] / count,
        "win_brier": value["brier"] / count,
        "mean_predicted_value": value["predicted_value"] / count,
        "mean_target_value": value["target_value"] / count,
    }


def add_metric(value, exact, predicted, target):
    """Add one public trajectory observation to an accumulator."""
    value["records"] += 1
    if exact is not None:
        value["policy_exact"] += int(exact)
        value["_policy_records"] += 1
    value["value_abs"] += abs(predicted - target)
    value["brier"] += ((predicted + 1.0) * 0.5 - (target + 1.0) * 0.5) ** 2
    value["predicted_value"] += predicted
    value["target_value"] += target


def average_finished(values):
    """Average finished metrics, giving every episode equal weight."""
    if not values:
        return finish(blank_metrics())
    result = {key: 0.0 for key in finish(blank_metrics())}
    result["records"] = len(values)
    for value in values:
        metrics = finish(value)
        for key in result:
            if key != "records":
                result[key] += metrics[key]
    for key in result:
        if key != "records":
            result[key] /= len(values)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--data", action="append", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=512)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    device = torch.device(args.device)
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    model = PolicyValueNet(ModelConfig.from_dict(checkpoint["model_config"])).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    records = load_records(args.data, None)
    loader = DataLoader(Records(records), batch_size=args.batch_size, shuffle=False,
                        collate_fn=collate, num_workers=0)
    buckets = defaultdict(blank_metrics)
    first_decisions = defaultdict(blank_metrics)
    episodes = defaultdict(lambda: defaultdict(blank_metrics))
    seen_first = set()
    with torch.inference_mode():
        for batch in loader:
            state = batch["state"].to(device)
            options = batch["options"].to(device)
            mask = batch["mask"].to(device)
            rules = batch["rule_features"].to(device)
            matchup_ids = batch["matchup_ids"].to(device)
            opponent_deck = batch["opponent_deck"].to(device)
            target = batch["reward"].to(device)
            logits, predicted = model(state, options, mask, rules, matchup_ids, opponent_deck)
            actions = greedy_selection(logits.cpu(), [len(x) for x in batch["selections"]])
            for row, metadata in enumerate(batch["metadata"]):
                opponent = metadata[0]
                policy_target = bool(metadata[4])
                exact = set(actions[row]) == set(batch["selections"][row]) if policy_target else None
                pred = float(predicted[row])
                truth = float(target[row])
                episode_key = (opponent, metadata[2])
                metric = (exact, pred, truth)
                for name in ("overall", opponent):
                    add_metric(buckets[name], *metric)
                    add_metric(episodes[name][episode_key], *metric)
                    first_key = (name, episode_key)
                    if policy_target and first_key not in seen_first:
                        seen_first.add(first_key)
                        add_metric(first_decisions[name], *metric)
    report = {}
    for name in sorted(buckets):
        report[name] = finish(buckets[name])
        report[name]["first_trainee_decision"] = finish(first_decisions[name])
        report[name]["episode_balanced"] = average_finished(list(episodes[name].values()))
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="ascii")


if __name__ == "__main__":
    main()
