"""Fit a conservative signature table on one replay window and test another."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

import numpy as np

from .evaluate_signature_gate import signature
from .evaluate_tree_gate import build_pairs, read_examples, threshold_metrics


def evaluate(args):
    train_examples = read_examples(args.train_data)
    validation_examples = read_examples(args.validation_data)
    train_pairs, _ = build_pairs(train_examples, feature_set="all")
    validation_pairs, validation_states = build_pairs(validation_examples, feature_set="all")
    buckets = defaultdict(list)
    for pair in train_pairs:
        target = pair.get("target")
        if target is not None:
            buckets[signature(pair["features"], args.signature)].append(float(target))
    table = {
        key: sum(values) / len(values)
        for key, values in buckets.items()
        if len(values) >= args.min_support
    }
    predictions = np.asarray([
        table.get(signature(pair["features"], args.signature), -math.inf)
        for pair in validation_pairs
    ], dtype=np.float64)
    finite = np.isfinite(predictions)
    targets = np.asarray([
        np.nan if pair.get("target") is None else float(pair["target"])
        for pair in validation_pairs
    ], dtype=np.float64)
    reports = [
        threshold_metrics(validation_states, validation_pairs, predictions, threshold)
        for threshold in args.threshold
    ]
    return {
        "train_data": [str(path) for path in args.train_data],
        "validation_data": [str(path) for path in args.validation_data],
        "train_examples": len(train_examples),
        "validation_examples": len(validation_examples),
        "train_pairs": len(train_pairs),
        "validation_pairs": len(validation_pairs),
        "table_entries": len(table),
        "coverage": float(finite.mean()),
        "covered_mae": (
            float(np.mean(np.abs(predictions[finite] - targets[finite])))
            if finite.any() else None
        ),
        "config": {
            "signature": args.signature,
            "min_support": args.min_support,
        },
        "thresholds": reports,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-data", action="append", type=Path, required=True)
    parser.add_argument("--validation-data", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--signature", choices=["action", "board"], default="action")
    parser.add_argument("--min-support", type=int, default=3)
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
        "table_entries": report["table_entries"],
        "thresholds": [
            {"threshold": row["threshold"], **row["overall"]}
            for row in report["thresholds"]
        ],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
