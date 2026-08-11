"""Validation-only ensemble calibration for the frozen expected-Q models."""

from __future__ import annotations

from collections import defaultdict
import statistics
from typing import Any, Mapping, Sequence

import torch

from .config import MultiDetConfig, output_path, write_json
from .dataset import load_dataset
from .model import load_checkpoint


def _outcome(delta: float) -> str:
    if delta > 0.0:
        return "IMPROVED"
    if delta < 0.0:
        return "WORSE"
    return "EQUAL"


def _aggregate(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    deltas = [float(record["mean_delta"]) for record in records]
    return {
        "selected": len(records),
        "IMPROVED": sum(int(record["outcome_class"] == "IMPROVED") for record in records),
        "EQUAL": sum(int(record["outcome_class"] == "EQUAL") for record in records),
        "WORSE": sum(int(record["outcome_class"] == "WORSE") for record in records),
        "actual_mean_delta_total": sum(deltas),
        "actual_mean_delta_mean": (sum(deltas) / len(deltas)) if deltas else None,
        "actual_mean_delta_median": statistics.median(deltas) if deltas else None,
        "lcb90_positive": sum(int(float(record["delta_lcb90"]) > 0.0) for record in records),
        "ucb90_negative": sum(int(float(record["delta_ucb90"]) < 0.0) for record in records),
        "uncertain": sum(int(not (float(record["delta_lcb90"]) > 0.0 or float(record["delta_ucb90"]) < 0.0)) for record in records),
        "positive_delta_count_total": sum(int(record["positive_delta_count"]) for record in records),
        "negative_delta_count_total": sum(int(record["negative_delta_count"]) for record in records),
    }


def _by_dimension(records: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    buckets: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        buckets[str(record[key])].append(record)
    return {name: _aggregate(bucket) for name, bucket in sorted(buckets.items())}


def calibrate(config: MultiDetConfig) -> dict[str, Any]:
    dataset = load_dataset(config)
    validation = [row for row in dataset["rows"] if row.get("split") == "validation"]
    models = []
    model_failures: list[dict[str, Any]] = []
    for seed in config.training_seeds:
        path = output_path(config, "checkpoints", f"multidet_q_seed{int(seed)}.pt")
        try:
            model, payload = load_checkpoint(path)
            models.append((int(seed), model))
        except Exception as exc:
            model_failures.append({"seed": int(seed), "error": f"{type(exc).__name__}: {exc}"})
    records: list[dict[str, Any]] = []
    agreement_total = 0
    baseline_agreement = 0
    if len(models) == 3:
        for row in validation:
            try:
                scores = [model.score_group(row).detach().cpu().float() for _, model in models]
                if any(not bool(torch.isfinite(score).all()) for score in scores):
                    raise FloatingPointError("non-finite validation score")
                candidate_rows = list(row["candidates"])
                identity_to_index = {str(candidate["canonical_identity"]): index for index, candidate in enumerate(candidate_rows)}
                best_indices = [int(torch.argmax(score).item()) for score in scores]
                best_ids = [str(candidate_rows[index]["canonical_identity"]) for index in best_indices]
                if len(set(best_ids)) != 1:
                    continue
                agreement_total += 1
                best_id = best_ids[0]
                best_index = identity_to_index[best_id]
                if bool(candidate_rows[best_index]["is_baseline"]):
                    baseline_agreement += 1
                    continue
                baseline_index = next(index for index, candidate in enumerate(candidate_rows) if candidate["is_baseline"])
                margins = [float(score[best_index].item() - score[baseline_index].item()) for score in scores]
                actual = candidate_rows[best_index]
                records.append(
                    {
                        "branch_group_id": row["branch_group_id"],
                        "source_episode_id": row["source_episode_id"],
                        "opponent_id": row["opponent_id"],
                        "seat": int(row["seat"]),
                        "context": int(row.get("context", 0)),
                        "family": actual["family"],
                        "canonical_identity": best_id,
                        "model_margins": margins,
                        "ensemble_min_margin": min(margins),
                        "mean_delta": float(actual["mean_delta"]),
                        "delta_lcb90": float(actual["delta_lcb90"]),
                        "delta_ucb90": float(actual["delta_ucb90"]),
                        "positive_delta_count": int(actual["positive_delta_count"]),
                        "negative_delta_count": int(actual["negative_delta_count"]),
                        "outcome_class": _outcome(float(actual["mean_delta"])),
                    }
                )
            except Exception as exc:
                model_failures.append({"branch_group_id": row.get("branch_group_id"), "error": f"{type(exc).__name__}: {exc}"})
    threshold_rows: list[dict[str, Any]] = []
    for threshold in config.margin_thresholds:
        selected = [record for record in records if float(record["ensemble_min_margin"]) >= float(threshold)]
        aggregate = _aggregate(selected)
        aggregate.update(
            {
                "threshold": float(threshold),
                "opponent": _by_dimension(selected, "opponent_id"),
                "seat": _by_dimension(selected, "seat"),
                "family": _by_dimension(selected, "family"),
            }
        )
        threshold_rows.append(aggregate)
    passed_rows = [
        row
        for row in threshold_rows
        if int(row["selected"]) >= 100
        and float(row["actual_mean_delta_total"]) > 0.0
        and float(row["actual_mean_delta_mean"]) > 0.0
        and int(row["lcb90_positive"]) > int(row["ucb90_negative"])
        and not model_failures
    ]
    selected_threshold = None
    if passed_rows:
        selected_threshold = max(passed_rows, key=lambda row: (float(row["actual_mean_delta_total"]), float(row["threshold"]))) ["threshold"]
    summary = {
        "schema_version": "archaludon-multidet-calibration-v1",
        "validation_groups": len(validation),
        "three_model_agreement_groups": agreement_total,
        "baseline_agreement_groups": baseline_agreement,
        "alternative_agreement_groups": len(records),
        "model_failure_count": len(model_failures),
        "model_failures": model_failures,
        "thresholds": threshold_rows,
        "passed": bool(passed_rows),
        "selected_threshold": selected_threshold,
        "records": records,
    }
    write_json(output_path(config, "calibration_summary.json"), summary)
    return summary


__all__ = ["calibrate"]
