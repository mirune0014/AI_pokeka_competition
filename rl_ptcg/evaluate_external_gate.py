"""Train a replay gate on one submission window and test another."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.feature_extraction import DictVectorizer

from .evaluate_tree_gate import build_pairs, read_examples, threshold_metrics


def _int32_csr(matrix):
    matrix.indices = matrix.indices.astype(np.int32, copy=False)
    matrix.indptr = matrix.indptr.astype(np.int32, copy=False)
    return matrix


def evaluate(args):
    train_examples = read_examples(args.train_data)
    validation_examples = read_examples(args.validation_data)
    if args.matchup:
        allowed = set(args.matchup)
        train_examples = [row for row in train_examples if str(row.get("matchup")) in allowed]
        validation_examples = [
            row for row in validation_examples if str(row.get("matchup")) in allowed
        ]
    train_pairs, _train_states = build_pairs(train_examples, feature_set=args.feature_set)
    validation_pairs, validation_states = build_pairs(
        validation_examples, feature_set=args.feature_set
    )
    vectorizer = DictVectorizer(sparse=True, dtype=np.float32)
    train_matrix = _int32_csr(vectorizer.fit_transform([
        pair["features"] for pair in train_pairs
    ]))
    validation_matrix = _int32_csr(vectorizer.transform([
        pair["features"] for pair in validation_pairs
    ]))
    train_labels = np.asarray([pair["label"] for pair in train_pairs], dtype=np.int8)
    validation_labels = np.asarray([
        pair["label"] for pair in validation_pairs
    ], dtype=np.int8)
    train_targets = np.asarray([
        np.nan if pair["target"] is None else float(pair["target"])
        for pair in train_pairs
    ], dtype=np.float64)
    validation_targets = np.asarray([
        np.nan if pair["target"] is None else float(pair["target"])
        for pair in validation_pairs
    ], dtype=np.float64)
    sample_weight = np.ones(len(train_pairs), dtype=np.float64)
    sample_weight[train_labels == 1] = args.positive_weight
    model_args = {
        "n_estimators": args.estimators,
        "learning_rate": args.learning_rate,
        "max_depth": args.max_depth,
        "min_samples_leaf": args.min_samples_leaf,
        "random_state": args.seed,
    }
    if args.objective == "classifier":
        model = GradientBoostingClassifier(**model_args)
        model.fit(train_matrix, train_labels, sample_weight=sample_weight)
        predictions = model.predict_proba(validation_matrix)[:, 1]
        regression = None
    else:
        if np.isnan(train_targets).any() or np.isnan(validation_targets).any():
            raise ValueError("advantage objective requires rollout targets")
        model = GradientBoostingRegressor(loss="huber", **model_args)
        model.fit(train_matrix, train_targets, sample_weight=sample_weight)
        predictions = model.predict(validation_matrix)
        residual = predictions - validation_targets
        regression = {
            "mae": float(np.mean(np.abs(residual))),
            "rmse": float(np.sqrt(np.mean(residual ** 2))),
            "correlation": float(np.corrcoef(predictions, validation_targets)[0, 1]),
        }
    reports = [
        threshold_metrics(validation_states, validation_pairs, predictions, threshold)
        for threshold in args.threshold
    ]
    return {
        "train_data": [str(path) for path in args.train_data],
        "validation_data": [str(path) for path in args.validation_data],
        "train_examples": len(train_examples),
        "validation_examples": len(validation_examples),
        "train_episodes": len({pair["episode_id"] for pair in train_pairs}),
        "validation_episodes": len({pair["episode_id"] for pair in validation_pairs}),
        "train_pairs": len(train_pairs),
        "validation_pairs": len(validation_pairs),
        "train_positive_pairs": int(train_labels.sum()),
        "validation_positive_pairs": int(validation_labels.sum()),
        "features": int(len(vectorizer.feature_names_)),
        "config": {
            "objective": args.objective,
            "feature_set": args.feature_set,
            "positive_weight": args.positive_weight,
            "estimators": args.estimators,
            "learning_rate": args.learning_rate,
            "max_depth": args.max_depth,
            "min_samples_leaf": args.min_samples_leaf,
            "seed": args.seed,
            "matchup": list(args.matchup or []),
        },
        "regression": regression,
        "thresholds": reports,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-data", action="append", type=Path, required=True)
    parser.add_argument("--validation-data", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--objective", choices=["classifier", "advantage"], default="classifier")
    parser.add_argument("--feature-set", choices=["all", "coarse"], default="all")
    parser.add_argument("--positive-weight", type=float, default=8.0)
    parser.add_argument("--estimators", type=int, default=80)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--min-samples-leaf", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--matchup", action="append", default=[])
    parser.add_argument("--threshold", action="append", type=float, default=None)
    args = parser.parse_args()
    if args.threshold is None:
        args.threshold = (
            [0.05, 0.1, 0.15, 0.2, 0.3]
            if args.objective == "advantage" else [0.5, 0.6, 0.7, 0.8, 0.9]
        )
    report = evaluate(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(json.dumps({
        "train_examples": report["train_examples"],
        "validation_examples": report["validation_examples"],
        "train_positive_pairs": report["train_positive_pairs"],
        "validation_positive_pairs": report["validation_positive_pairs"],
        "regression": report["regression"],
        "thresholds": [
            {"threshold": row["threshold"], **row["overall"]}
            for row in report["thresholds"]
        ],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
