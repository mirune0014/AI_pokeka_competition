"""Run the frozen calibration choice against offline-test rows only."""

from __future__ import annotations

import json
from typing import Any

from .calibrate import _models, _aggregate
from .config import CoverageConfig, output_path, write_json
from .dataset import load_dataset


def offline_test(config: CoverageConfig) -> dict[str, Any]:
    selected = json.loads(output_path(config, "calibration", "selected_candidate.json").read_text(encoding="utf-8")).get("selected")
    if not selected:
        result = {"schema_version": "archaludon-search-q-offline-test-v1", "status": "OFFLINE_TEST_REJECTED", "reason": "no calibration candidate"}
        write_json(output_path(config, "offline_test", "offline_test_summary.json"), result)
        return result
    milestone, threshold = str(selected["milestone"]), float(selected["threshold"])
    models, failures = _models(config, milestone)
    rows = load_dataset(config, "offline_test")["rows"]
    records: list[dict[str, Any]] = []
    for row in rows:
        if len(models) != 3:
            break
        scores = [model.score_group(row) for model in models]
        best = [int(score.argmax().item()) for score in scores]
        candidates = row["candidates"]
        if len({candidates[index]["canonical_identity"] for index in best}) != 1:
            continue
        index = best[0]
        base = next(i for i, candidate in enumerate(candidates) if candidate.get("is_baseline"))
        if index == base:
            continue
        margins = [float(score[index].item() - score[base].item()) for score in scores]
        if min(margins) < threshold:
            continue
        candidate = candidates[index]
        records.append({"mean_delta": float(candidate["mean_delta"]), "delta_lcb90": float(candidate["delta_lcb90"]), "delta_ucb90": float(candidate["delta_ucb90"]), "outcome": "positive" if float(candidate["mean_delta"]) > 0 else "negative" if float(candidate["mean_delta"]) < 0 else "equal"})
    aggregate = _aggregate(records)
    passed = not failures and len(records) >= config.offline_test_minimum_override_episodes and aggregate["actual_mean_delta_total"] > 0 and aggregate["positive_episode"] > aggregate["negative_episode"] and aggregate["lcb90_positive"] > aggregate["ucb90_negative"]
    result = {"schema_version": "archaludon-search-q-offline-test-v1", "status": "OFFLINE_TEST_PASSED" if passed else "OFFLINE_TEST_REJECTED", "milestone": milestone, "threshold": threshold, "model_failure_count": len(failures), "override_episodes": len(records), "aggregate": aggregate}
    write_json(output_path(config, "offline_test", "offline_test_summary.json"), result)
    return result


__all__ = ["offline_test"]
