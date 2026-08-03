"""Evaluate a conservative replay-derived signature policy table."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from .evaluate_tree_gate import build_pairs, read_examples, threshold_metrics


ACTION_FAMILIES = {
    "attack_id", "card_id", "card_target", "option_type", "target_card_id",
    "target_energy", "target_hp", "type_context",
}
BOARD_FAMILIES = {
    "matchup", "opp_active", "opp_bench", "opp_prize", "own_active",
    "own_bench", "own_prize", "supporter_played", "turn",
}


def _family(pair_key):
    key = pair_key.split(":", 1)[-1]
    return key.split("=", 1)[0]


def signature(features, mode):
    allowed = ACTION_FAMILIES | (BOARD_FAMILIES if mode == "board" else set())
    values = []
    for key, value in features.items():
        if not key.startswith(("c:", "b:")) or _family(key) not in allowed:
            continue
        if value:
            values.append((key, round(float(value), 4)))
    delta = float(features.get("delta_normalized", 0.0))
    delta_bucket = max(-4, min(4, math.floor(delta * 4.0)))
    values.append(("delta_bucket", delta_bucket))
    return tuple(sorted(values))


def evaluate(args):
    examples = read_examples(args.data)
    pairs, state_rows = build_pairs(examples, feature_set="all")
    labels = np.asarray([pair["label"] for pair in pairs], dtype=np.int8)
    groups = np.asarray([pair["episode_id"] for pair in pairs])
    targets = np.asarray([
        np.nan if pair["target"] is None else float(pair["target"])
        for pair in pairs
    ], dtype=np.float64)
    if np.isnan(targets).any():
        raise ValueError("signature evaluation requires rollout_delta_mean")
    signatures = [signature(pair["features"], args.signature) for pair in pairs]
    splitter = StratifiedGroupKFold(
        n_splits=args.folds, shuffle=True, random_state=args.seed
    )
    predictions = np.full(len(pairs), -math.inf, dtype=np.float64)
    dummy = np.zeros(len(pairs), dtype=np.int8)
    fold_details = []
    for fold_index, (train_indices, validation_indices) in enumerate(
        splitter.split(dummy, labels, groups), start=1
    ):
        buckets = defaultdict(list)
        for index in train_indices:
            buckets[signatures[index]].append(float(targets[index]))
        table = {
            key: sum(values) / len(values)
            for key, values in buckets.items()
            if len(values) >= args.min_support
        }
        for index in validation_indices:
            predictions[index] = table.get(signatures[index], -math.inf)
        fold_details.append({
            "fold": fold_index,
            "table_entries": len(table),
            "covered_pairs": int(np.isfinite(predictions[validation_indices]).sum()),
            "validation_pairs": int(len(validation_indices)),
        })
    reports = [
        threshold_metrics(state_rows, pairs, predictions, threshold)
        for threshold in args.threshold
    ]
    finite = np.isfinite(predictions)
    return {
        "data": [str(path) for path in args.data],
        "examples": len(examples),
        "episodes": len(set(groups)),
        "pairs": len(pairs),
        "positive_pairs": int(labels.sum()),
        "config": {
            "signature": args.signature,
            "min_support": args.min_support,
            "folds": args.folds,
            "seed": args.seed,
        },
        "coverage": float(finite.mean()),
        "covered_mae": (
            float(np.mean(np.abs(predictions[finite] - targets[finite])))
            if finite.any() else None
        ),
        "fold_details": fold_details,
        "thresholds": reports,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--signature", choices=["action", "board"], default="action")
    parser.add_argument("--min-support", type=int, default=3)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--threshold", action="append", type=float, default=None)
    args = parser.parse_args()
    if args.threshold is None:
        args.threshold = [0.05, 0.1, 0.15, 0.2]
    report = evaluate(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(json.dumps({
        "coverage": report["coverage"],
        "covered_mae": report["covered_mae"],
        "thresholds": [
            {"threshold": row["threshold"], **row["overall"]}
            for row in report["thresholds"]
        ],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
