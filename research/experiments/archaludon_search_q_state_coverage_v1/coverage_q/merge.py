"""Merge six immutable search shards without changing group results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import CoverageConfig, output_path, write_json
from .search_plan import load_plan
from .search_worker import GROUP_SCHEMA


def merge_stage(config: CoverageConfig, stage: str, *, shard_count: int = 6) -> dict[str, Any]:
    expected = {str(row["branch_group_id"]): row for row in load_plan(config) if row.get("stage") == stage}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for shard_index in range(shard_count):
        path = output_path(config, "search", stage, f"shard_{shard_index:03d}_of_{shard_count:03d}.jsonl")
        if not path.is_file():
            raise FileNotFoundError(path)
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            group_id = str(row.get("branch_group_id"))
            if group_id in seen:
                raise RuntimeError(f"duplicate group in merged search: {group_id}")
            if group_id not in expected or row.get("schema_version") != GROUP_SCHEMA:
                raise RuntimeError(f"unexpected group in merged search: {group_id}")
            if row.get("status") != "OK":
                raise RuntimeError(f"search group failed: {group_id}")
            seen.add(group_id)
            rows.append(row)
    if seen != set(expected):
        raise RuntimeError(f"search group coverage mismatch: expected {len(expected)} got {len(seen)}")
    rows.sort(key=lambda row: str(row["branch_group_id"]))
    path = output_path(config, "search", stage, "merged.jsonl")
    if path.exists():
        existing = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if existing != rows:
            raise FileExistsError(f"merged output differs from existing artifact: {path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")
    result = {"schema_version": "archaludon-search-q-merge-summary-v1", "stage": stage, "groups": len(rows), "candidates": sum(len(row.get("candidates", ())) for row in rows), "rollouts": sum(int(row.get("rollout_count", 0)) * len(row.get("candidates", ())) for row in rows), "path": str(path)}
    write_json(output_path(config, "search", stage, "merge_summary.json"), result)
    return result


def merge_all(config: CoverageConfig, *, shard_count: int = 6) -> dict[str, Any]:
    return {stage: merge_stage(config, stage, shard_count=shard_count) for stage in ("calibration", "offline_test", "train_m05", "train_m10_increment", "train_m20_increment")}


__all__ = ["merge_all", "merge_stage"]
