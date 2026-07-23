"""Train a dependency-free sparse residual from rollout-expert JSONL labels."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .sparse_expert import evaluate, train
except ImportError:
    from sparse_expert import evaluate, train


def read_examples(paths):
    rows = []
    for path in paths or []:
        with Path(path).open("r", encoding="ascii") as handle:
            rows.extend(json.loads(line) for line in handle if line.strip())
    return rows


def filter_features(rows, prefixes):
    if not prefixes or "*" in prefixes:
        return rows
    output = []
    for row in rows:
        copied = {**row, "options": []}
        for option in row.get("options", []):
            copied["options"].append({
                **option,
                "features": {
                    key: value for key, value in option.get("features", {}).items()
                    if any(str(key).startswith(prefix) for prefix in prefixes)
                },
            })
        output.append(copied)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-data", action="append", type=Path, required=True)
    parser.add_argument("--validation-data", action="append", type=Path, default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--learning-rate", type=float, default=0.2)
    parser.add_argument("--l2", type=float, default=0.001)
    parser.add_argument("--weight-clip", type=float, default=2.0)
    parser.add_argument("--residual-cap", type=float, default=0.35)
    parser.add_argument("--changed-weight", type=float, default=4.0)
    parser.add_argument("--feature-prefix", action="append", default=["matchup"])
    args = parser.parse_args()
    train_rows = filter_features(read_examples(args.train_data), args.feature_prefix)
    validation_rows = filter_features(read_examples(args.validation_data), args.feature_prefix)
    before = evaluate(train_rows, {}, args.residual_cap)
    result = train(
        train_rows, epochs=args.epochs, learning_rate=args.learning_rate,
        l2=args.l2, weight_clip=args.weight_clip, residual_cap=args.residual_cap,
        changed_weight=args.changed_weight,
    )
    report = {
        "train_before": before,
        "train_after": result["metrics"],
        "validation_before": evaluate(validation_rows, {}, args.residual_cap),
        "validation": evaluate(validation_rows, result["weights"], args.residual_cap),
        "weights": len(result["weights"]),
        "feature_prefixes": args.feature_prefix,
        "config": {
            "epochs": args.epochs, "learning_rate": args.learning_rate, "l2": args.l2,
            "weight_clip": args.weight_clip, "residual_cap": args.residual_cap,
            "changed_weight": args.changed_weight,
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "weights.json").write_text(
        json.dumps(result["weights"], indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    (args.output_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
