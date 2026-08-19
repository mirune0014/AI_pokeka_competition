"""Completeness and integrity merge for the four full group shards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import MultiDetConfig, output_path, write_json
from .worker import GROUP_SCHEMA, load_task_groups, assigned


def _read_lines(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError(f"non-object group line: {path}:{line_number}")
        rows.append(value)
    return rows


def merge_full(config: MultiDetConfig, *, shard_count: int) -> dict[str, Any]:
    if int(shard_count) != 4:
        raise ValueError("full merge is frozen to four shards")
    groups = load_task_groups(config)
    expected_group_ids = set(groups)
    actual: dict[str, dict[str, Any]] = {}
    duplicate_group_count = 0
    extra_group_count = 0
    error_count = 0
    candidate_count = 0
    missing_candidates = 0
    invalid_candidates = 0
    rollout_count_errors = 0
    fingerprint_errors = 0
    for shard_index in range(4):
        path = output_path(config, "full", f"shard_{shard_index:03d}_of_004.jsonl")
        for row in _read_lines(path):
            group_id = str(row.get("branch_group_id", ""))
            if group_id not in expected_group_ids or not assigned(group_id, 4, shard_index):
                extra_group_count += 1
                continue
            if group_id in actual:
                duplicate_group_count += 1
                continue
            actual[group_id] = row
            if row.get("schema_version") != GROUP_SCHEMA or row.get("status") != "OK":
                error_count += 1
                continue
            expected_tasks = sorted(groups[group_id], key=lambda item: (int(item.candidate_index), item.task_id))
            candidates = row.get("candidates")
            if not isinstance(candidates, list) or len(candidates) != len(expected_tasks):
                missing_candidates += max(0, len(expected_tasks) - (len(candidates) if isinstance(candidates, list) else 0))
                invalid_candidates += 1
                continue
            expected_by_index = {int(task.candidate_index): task for task in expected_tasks}
            actual_indexes: set[int] = set()
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    invalid_candidates += 1
                    continue
                index = int(candidate.get("candidate_index", -1))
                actual_indexes.add(index)
                task = expected_by_index.get(index)
                if task is None or str(candidate.get("task_id")) != task.task_id or str(candidate.get("canonical_identity")) != task.candidate_identity:
                    invalid_candidates += 1
                rewards = candidate.get("rewards")
                if not isinstance(rewards, list) or len(rewards) != config.full_determinizations:
                    rollout_count_errors += 1
            if actual_indexes != set(expected_by_index):
                missing_candidates += len(set(expected_by_index) - actual_indexes)
            fingerprints = row.get("determinization_fingerprints")
            if not isinstance(fingerprints, list) or len(fingerprints) != config.full_determinizations:
                fingerprint_errors += 1
            candidate_count += len(candidates)
    missing_group_count = len(expected_group_ids - set(actual))
    if missing_group_count or extra_group_count or duplicate_group_count or error_count or missing_candidates or invalid_candidates or rollout_count_errors or fingerprint_errors:
        summary = {
            "schema_version": "archaludon-multidet-merge-summary-v1",
            "group_count": len(expected_group_ids),
            "merged_group_count": len(actual),
            "task_count": sum(len(tasks) for tasks in groups.values()),
            "candidate_count": candidate_count,
            "missing_group_count": missing_group_count,
            "extra_group_count": extra_group_count,
            "duplicate_group_count": duplicate_group_count,
            "missing_candidate_count": missing_candidates,
            "invalid_candidate_count": invalid_candidates,
            "rollout_count_error_count": rollout_count_errors,
            "fingerprint_error_count": fingerprint_errors,
            "error_count": error_count,
            "status": "ERROR",
        }
        write_json(output_path(config, "full", "merge_summary.json"), summary)
        raise RuntimeError(f"full merge completeness check failed: {summary}")
    merged_path = output_path(config, "full", "merged_groups.jsonl")
    with merged_path.open("w", encoding="utf-8", newline="\n") as handle:
        for group_id in sorted(actual):
            handle.write(json.dumps(actual[group_id], sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n")
    summary = {
        "schema_version": "archaludon-multidet-merge-summary-v1",
        "group_count": len(expected_group_ids),
        "merged_group_count": len(actual),
        "task_count": sum(len(tasks) for tasks in groups.values()),
        "candidate_count": candidate_count,
        "missing_group_count": 0,
        "extra_group_count": 0,
        "duplicate_group_count": 0,
        "missing_candidate_count": 0,
        "invalid_candidate_count": 0,
        "rollout_count_error_count": 0,
        "fingerprint_error_count": 0,
        "error_count": 0,
        "status": "OK",
        "merged_path": str(merged_path),
    }
    write_json(output_path(config, "full", "merge_summary.json"), summary)
    return summary


__all__ = ["merge_full"]
