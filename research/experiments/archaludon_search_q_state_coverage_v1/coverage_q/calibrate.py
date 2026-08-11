"""Calibration and immutable one-override selection for the three-model ensemble."""

from __future__ import annotations

from collections import defaultdict
import statistics
from typing import Any, Mapping, Sequence

import torch

from .config import CoverageConfig, output_path, write_json
from .dataset import load_dataset
from .model_bridge import load_checkpoint


def outcome(delta: float) -> str:
    return "positive" if delta > 0 else "negative" if delta < 0 else "equal"


def _aggregate(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    deltas = [float(record["mean_delta"]) for record in records]
    return {
        "override_episodes": len(records),
        "positive_episode": sum(int(record["outcome"] == "positive") for record in records),
        "equal_episode": sum(int(record["outcome"] == "equal") for record in records),
        "negative_episode": sum(int(record["outcome"] == "negative") for record in records),
        "actual_mean_delta_total": sum(deltas),
        "actual_mean_delta_mean": sum(deltas) / len(deltas) if deltas else 0.0,
        "actual_mean_delta_median": statistics.median(deltas) if deltas else None,
        "lcb90_positive": sum(int(float(record["delta_lcb90"]) > 0) for record in records),
        "ucb90_negative": sum(int(float(record["delta_ucb90"]) < 0) for record in records),
    }


def _by_dimension(records: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    buckets: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        buckets[str(record[key])].append(record)
    return {name: _aggregate(rows) for name, rows in sorted(buckets.items())}


def _models(config: CoverageConfig, milestone: str) -> tuple[list[Any], list[dict[str, Any]]]:
    models: list[Any] = []
    failures: list[dict[str, Any]] = []
    for seed in config.training_seeds:
        path = output_path(config, "checkpoints", milestone, f"seed_{int(seed)}.pt")
        try:
            model, _ = load_checkpoint(path)
            models.append(model)
        except Exception as exc:
            failures.append({"seed": int(seed), "error": f"{type(exc).__name__}: {exc}"})
    return models, failures


def select_candidate(threshold_rows: Sequence[Mapping[str, Any]], *, minimum_overrides: int = 100) -> Mapping[str, Any] | None:
    candidates = [row for row in threshold_rows if int(row.get("override_episodes", 0)) >= minimum_overrides and float(row.get("actual_mean_delta_total", 0.0)) > 0.0 and int(row.get("positive_episode", 0)) > int(row.get("negative_episode", 0)) and int(row.get("lcb90_positive", 0)) > int(row.get("ucb90_negative", 0))]
    if not candidates:
        return None
    return max(candidates, key=lambda row: (float(row["actual_mean_delta_total"]), -int(row["negative_episode"]), float(row["threshold"]), int(str(row.get("milestone", "m00")).lstrip("m") or 0)))


def calibrate(config: CoverageConfig) -> dict[str, Any]:
    dataset = load_dataset(config, "calibration")["rows"]
    all_thresholds: list[dict[str, Any]] = []
    model_failures: list[dict[str, Any]] = []
    records_by_milestone: dict[str, list[dict[str, Any]]] = {}
    for milestone in ("m05", "m10", "m20"):
        models, failures = _models(config, milestone)
        model_failures.extend([{**failure, "milestone": milestone} for failure in failures])
        records: list[dict[str, Any]] = []
        if len(models) == 3:
            for row in dataset:
                try:
                    scores = [model.score_group(row).detach().cpu().float() for model in models]
                    candidates = list(row["candidates"])
                    best = [int(torch.argmax(score).item()) for score in scores]
                    if len({candidates[index]["canonical_identity"] for index in best}) != 1:
                        continue
                    best_index = best[0]
                    if candidates[best_index].get("is_baseline"):
                        continue
                    baseline_index = next(index for index, candidate in enumerate(candidates) if candidate.get("is_baseline"))
                    margins = [float(score[best_index] - score[baseline_index]) for score in scores]
                    selected = candidates[best_index]
                    records.append({"branch_group_id": row["branch_group_id"], "source_episode_id": row["source_episode_id"], "opponent_id": row["opponent_id"], "seat": row["seat"], "family": selected.get("family", "empty"), "canonical_identity": selected["canonical_identity"], "mean_delta": float(selected["mean_delta"]), "delta_lcb90": float(selected["delta_lcb90"]), "delta_ucb90": float(selected["delta_ucb90"]), "outcome": outcome(float(selected["mean_delta"])), "ensemble_min_margin": min(margins), "first_override_step": row["branch_step_index"]})
                except Exception as exc:
                    model_failures.append({"milestone": milestone, "branch_group_id": row.get("branch_group_id"), "error": f"{type(exc).__name__}: {exc}"})
        records_by_milestone[milestone] = records
        for threshold in config.margin_thresholds:
            selected = [record for record in records if float(record["ensemble_min_margin"]) >= float(threshold)]
            row = _aggregate(selected)
            row.update({"milestone": milestone, "threshold": float(threshold), "calibration_episodes": len(dataset), "opponent": _by_dimension(selected, "opponent_id"), "seat": _by_dimension(selected, "seat"), "family": _by_dimension(selected, "family"), "first_override_step_median": statistics.median([record["first_override_step"] for record in selected]) if selected else None, "first_override_step_p90": sorted(record["first_override_step"] for record in selected)[max(0, int(len(selected) * 0.9) - 1)] if selected else None})
            all_thresholds.append(row)
    selected = select_candidate(all_thresholds, minimum_overrides=config.offline_test_minimum_override_episodes)
    selected_payload = {"schema_version": "archaludon-search-q-selected-candidate-v1", "selected": None if selected is None else {"milestone": selected["milestone"], "threshold": selected["threshold"]}, "selection": selected}
    write_json(output_path(config, "calibration", "selected_candidate.json"), selected_payload)
    summary = {"schema_version": "archaludon-search-q-calibration-v1", "calibration_episodes": len(dataset), "model_failure_count": len(model_failures), "model_failures": model_failures, "thresholds": all_thresholds, "passed": selected is not None, "selected": selected_payload["selected"], "records": records_by_milestone}
    write_json(output_path(config, "calibration", "calibration_summary.json"), summary)
    return summary


__all__ = ["calibrate", "outcome", "select_candidate"]
