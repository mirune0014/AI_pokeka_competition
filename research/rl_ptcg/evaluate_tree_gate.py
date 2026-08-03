"""Evaluate a conservative tree gate on replay rollout labels.

The gate compares every non-baseline legal option with the baseline option.
Cross-validation is grouped by Kaggle episode so states from one battle never
appear in both training and validation folds.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.feature_extraction import DictVectorizer
from sklearn.model_selection import StratifiedGroupKFold


def read_examples(paths):
    examples = []
    for path in paths:
        with path.open("r", encoding="ascii") as handle:
            examples.extend(json.loads(line) for line in handle if line.strip())
    return examples


def keep_option_feature(key, feature_set):
    if feature_set == "all":
        return True
    family = str(key).split("=", 1)[0]
    if family.startswith("belief_"):
        return True
    if family.startswith("matchup_"):
        return False
    return family in {
        "attack_id", "baseline_normalized", "baseline_rank",
        "baseline_score_bucket", "bias", "card_damage", "card_energy",
        "card_hp", "card_id", "card_target", "energy_attached", "matchup",
        "opp_active", "opp_bench", "opp_bench_has", "opp_deck", "opp_hand",
        "opp_prize", "option_count", "option_type", "own_active", "own_bench",
        "own_bench_has", "own_deck", "own_hand", "own_hand_has", "own_prize",
        "public_matchup", "select_context", "supporter_played", "target_card_id", "target_damage",
        "target_energy", "target_hp", "turn", "turn_action_count", "type_context",
    }


def pair_features(example, candidate_index, baseline_index, feature_set="all"):
    options = example["options"]
    candidate = options[candidate_index]
    baseline = options[baseline_index]
    candidate_score = float(candidate.get("normalized_score", 0.0))
    baseline_score = float(baseline.get("normalized_score", 0.0))
    features = {
        "candidate_normalized": candidate_score,
        "baseline_normalized": baseline_score,
        "delta_normalized": candidate_score - baseline_score,
    }
    for key, value in candidate.get("features", {}).items():
        if keep_option_feature(key, feature_set):
            features["c:" + str(key)] = float(value)
    for key, value in baseline.get("features", {}).items():
        if keep_option_feature(key, feature_set):
            features["b:" + str(key)] = float(value)
    return features


def build_pairs(examples, feature_set="all"):
    pairs = []
    state_rows = []
    for state_index, example in enumerate(examples):
        baseline_action = list(map(int, example.get("baseline_action", [])))
        expert_action = list(map(int, example.get("expert_action", [])))
        if len(baseline_action) != 1 or len(expert_action) != 1:
            continue
        baseline_index = baseline_action[0]
        expert_index = expert_action[0]
        episode_id = str(example.get("metadata", {}).get("episode_id", "unknown"))
        pair_indices = []
        for candidate_index in range(len(example.get("options", []))):
            if candidate_index == baseline_index:
                continue
            pair_indices.append(len(pairs))
            pairs.append({
                "features": pair_features(
                    example, candidate_index, baseline_index, feature_set=feature_set
                ),
                "label": int(expert_index != baseline_index and candidate_index == expert_index),
                "target": example["options"][candidate_index].get("rollout_delta_mean"),
                "target_lower": example["options"][candidate_index].get("rollout_delta_lower"),
                "episode_id": episode_id,
                "state_index": state_index,
                "candidate_index": candidate_index,
            })
        if pair_indices:
            state_rows.append({
                "state_index": state_index,
                "episode_id": episode_id,
                "matchup": str(example.get("matchup") or "unknown"),
                "baseline_index": baseline_index,
                "expert_index": expert_index,
                "pair_indices": pair_indices,
            })
    return pairs, state_rows


def threshold_metrics(state_rows, pairs, probabilities, threshold):
    totals = Counter()
    per_matchup = defaultdict(Counter)
    selected = []
    for state in state_rows:
        best_pair_index = max(
            state["pair_indices"],
            key=lambda index: (float(probabilities[index]), -pairs[index]["candidate_index"]),
        )
        probability = float(probabilities[best_pair_index])
        selected_index = (
            pairs[best_pair_index]["candidate_index"]
            if probability >= threshold else state["baseline_index"]
        )
        changed = state["expert_index"] != state["baseline_index"]
        override = selected_index != state["baseline_index"]
        correct = selected_index == state["expert_index"]
        bucket = per_matchup[state["matchup"]]
        totals["states"] += 1
        bucket["states"] += 1
        if changed:
            totals["changed_states"] += 1
            bucket["changed_states"] += 1
            if correct:
                totals["changed_correct"] += 1
                bucket["changed_correct"] += 1
            elif override:
                totals["changed_wrong_override"] += 1
                bucket["changed_wrong_override"] += 1
            else:
                totals["changed_missed"] += 1
                bucket["changed_missed"] += 1
        else:
            totals["unchanged_states"] += 1
            bucket["unchanged_states"] += 1
            if override:
                totals["unchanged_false_override"] += 1
                bucket["unchanged_false_override"] += 1
        if override:
            totals["overrides"] += 1
            bucket["overrides"] += 1
            target = pairs[best_pair_index].get("target")
            lower = pairs[best_pair_index].get("target_lower")
            if target is not None:
                target = float(target)
                totals["rollout_labeled_overrides"] += 1
                bucket["rollout_labeled_overrides"] += 1
                totals["rollout_delta_sum"] += target
                bucket["rollout_delta_sum"] += target
                if target >= 0.0:
                    totals["rollout_nonworse_overrides"] += 1
                    bucket["rollout_nonworse_overrides"] += 1
                if target > 0.0:
                    totals["rollout_positive_overrides"] += 1
                    bucket["rollout_positive_overrides"] += 1
            if lower is not None and float(lower) >= 0.0:
                totals["rollout_safe_overrides"] += 1
                bucket["rollout_safe_overrides"] += 1
        selected.append({
            "state_index": state["state_index"],
            "episode_id": state["episode_id"],
            "matchup": state["matchup"],
            "probability": probability,
            "selected_index": selected_index,
            "baseline_index": state["baseline_index"],
            "expert_index": state["expert_index"],
        })

    def finish(counter):
        output = dict(counter)
        output["override_precision"] = (
            counter["changed_correct"] / counter["overrides"]
            if counter["overrides"] else 0.0
        )
        output["changed_recall"] = (
            counter["changed_correct"] / counter["changed_states"]
            if counter["changed_states"] else 0.0
        )
        output["unchanged_false_override_rate"] = (
            counter["unchanged_false_override"] / counter["unchanged_states"]
            if counter["unchanged_states"] else 0.0
        )
        output["rollout_nonworse_rate"] = (
            counter["rollout_nonworse_overrides"] / counter["rollout_labeled_overrides"]
            if counter["rollout_labeled_overrides"] else 0.0
        )
        output["rollout_positive_rate"] = (
            counter["rollout_positive_overrides"] / counter["rollout_labeled_overrides"]
            if counter["rollout_labeled_overrides"] else 0.0
        )
        output["rollout_safe_rate"] = (
            counter["rollout_safe_overrides"] / counter["rollout_labeled_overrides"]
            if counter["rollout_labeled_overrides"] else 0.0
        )
        output["rollout_mean_delta"] = (
            counter["rollout_delta_sum"] / counter["rollout_labeled_overrides"]
            if counter["rollout_labeled_overrides"] else 0.0
        )
        return output

    return {
        "threshold": float(threshold),
        "overall": finish(totals),
        "per_matchup": {key: finish(value) for key, value in sorted(per_matchup.items())},
        "selected": selected,
    }


def evaluate(args):
    examples = read_examples(args.data)
    if args.matchup:
        allowed = set(args.matchup)
        examples = [row for row in examples if str(row.get("matchup")) in allowed]
    pairs, state_rows = build_pairs(examples, feature_set=args.feature_set)
    feature_rows = [pair["features"] for pair in pairs]
    labels = np.asarray([pair["label"] for pair in pairs], dtype=np.int8)
    targets = np.asarray([
        np.nan if pair["target"] is None else float(pair["target"])
        for pair in pairs
    ], dtype=np.float64)
    if args.objective == "advantage" and np.isnan(targets).any():
        raise ValueError("advantage objective requires rollout_delta_mean on every candidate")
    groups = np.asarray([pair["episode_id"] for pair in pairs])
    if labels.sum() < args.folds:
        raise ValueError("too few positive pairs for requested folds")
    splitter = StratifiedGroupKFold(
        n_splits=args.folds, shuffle=True, random_state=args.seed
    )
    probabilities = np.full(len(pairs), np.nan, dtype=np.float64)
    folds = []
    dummy = np.zeros(len(pairs), dtype=np.int8)
    for fold_index, (train_indices, validation_indices) in enumerate(
        splitter.split(dummy, labels, groups), start=1
    ):
        vectorizer = DictVectorizer(sparse=True, dtype=np.float32)
        train_rows = [feature_rows[index] for index in train_indices]
        validation_rows = [feature_rows[index] for index in validation_indices]
        train_matrix = vectorizer.fit_transform(train_rows)
        validation_matrix = vectorizer.transform(validation_rows)
        # Windows scipy may produce int64 sparse indices, while sklearn's tree
        # implementation requires int32 CSR index arrays.
        train_matrix.indices = train_matrix.indices.astype(np.int32, copy=False)
        train_matrix.indptr = train_matrix.indptr.astype(np.int32, copy=False)
        validation_matrix.indices = validation_matrix.indices.astype(np.int32, copy=False)
        validation_matrix.indptr = validation_matrix.indptr.astype(np.int32, copy=False)
        train_labels = labels[train_indices]
        sample_weight = np.ones(len(train_indices), dtype=np.float64)
        sample_weight[train_labels == 1] = args.positive_weight
        model_args = {
            "n_estimators": args.estimators,
            "learning_rate": args.learning_rate,
            "max_depth": args.max_depth,
            "min_samples_leaf": args.min_samples_leaf,
            "random_state": args.seed + fold_index,
        }
        if args.objective == "classifier":
            model = GradientBoostingClassifier(**model_args)
            model.fit(train_matrix, train_labels, sample_weight=sample_weight)
            probabilities[validation_indices] = model.predict_proba(validation_matrix)[:, 1]
        else:
            model = GradientBoostingRegressor(loss="huber", **model_args)
            model.fit(train_matrix, targets[train_indices], sample_weight=sample_weight)
            probabilities[validation_indices] = model.predict(validation_matrix)
        folds.append({
            "fold": fold_index,
            "train_pairs": int(len(train_indices)),
            "validation_pairs": int(len(validation_indices)),
            "train_positives": int(train_labels.sum()),
            "validation_positives": int(labels[validation_indices].sum()),
            "train_episodes": int(len(set(groups[train_indices]))),
            "validation_episodes": int(len(set(groups[validation_indices]))),
            "features": int(len(vectorizer.feature_names_)),
        })
    if np.isnan(probabilities).any():
        raise RuntimeError("cross-validation did not predict every pair")
    reports = [
        threshold_metrics(state_rows, pairs, probabilities, threshold)
        for threshold in args.threshold
    ]
    report = {
        "data": [str(path) for path in args.data],
        "examples": len(examples),
        "evaluated_states": len(state_rows),
        "episodes": len(set(groups)),
        "pairs": len(pairs),
        "positive_pairs": int(labels.sum()),
        "config": {
            "folds": args.folds,
            "seed": args.seed,
            "estimators": args.estimators,
            "learning_rate": args.learning_rate,
            "max_depth": args.max_depth,
            "min_samples_leaf": args.min_samples_leaf,
            "positive_weight": args.positive_weight,
            "feature_set": args.feature_set,
            "objective": args.objective,
            "matchup": list(args.matchup or []),
        },
        "fold_details": folds,
        "thresholds": reports,
    }
    if args.objective == "advantage":
        residual = probabilities - targets
        report["regression"] = {
            "mae": float(np.mean(np.abs(residual))),
            "rmse": float(np.sqrt(np.mean(residual ** 2))),
            "correlation": float(np.corrcoef(probabilities, targets)[0, 1]),
            "target_mean": float(np.mean(targets)),
            "target_positive": int(np.sum(targets > 0.0)),
        }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--estimators", type=int, default=80)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--min-samples-leaf", type=int, default=10)
    parser.add_argument("--positive-weight", type=float, default=8.0)
    parser.add_argument("--feature-set", choices=["all", "coarse"], default="all")
    parser.add_argument("--objective", choices=["classifier", "advantage"], default="classifier")
    parser.add_argument("--matchup", action="append", default=[])
    parser.add_argument(
        "--threshold", type=float, action="append",
        default=None,
    )
    args = parser.parse_args()
    if args.threshold is None:
        args.threshold = (
            [0.05, 0.1, 0.15, 0.2, 0.3]
            if args.objective == "advantage" else [0.5, 0.6, 0.7, 0.8, 0.9]
        )
    report = evaluate(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="ascii")
    compact = {
        "examples": report["examples"],
        "episodes": report["episodes"],
        "pairs": report["pairs"],
        "positive_pairs": report["positive_pairs"],
        "thresholds": [
            {"threshold": row["threshold"], **row["overall"]}
            for row in report["thresholds"]
        ],
    }
    print(json.dumps(compact, sort_keys=True))


if __name__ == "__main__":
    main()
