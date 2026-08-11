"""Thin source-collection adapter around the frozen Rollout-Q collector."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from research.experiments.archaludon_rollout_q_v1.rollout_q.config import load_spec as load_rollout_spec
from research.experiments.archaludon_rollout_q_v1.rollout_q.source_collector import (
    _collect_one,
    _load_engine,
    _opponent_rows,
    resolve_opponent_dir,
)
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import BranchPoint, SourceTrace

from .config import CoverageConfig, canonical_json, output_path, write_json
from .schedule import SourceEpisodePlan, all_plans, plans_by_episode


def _rewrite_trace(trace: SourceTrace, plan: SourceEpisodePlan) -> SourceTrace:
    points = tuple(
        replace(
            point,
            branch_group_id=hashlib.sha256(f"{plan.episode_id}|{point.step_index}".encode("utf-8")).hexdigest(),
        )
        for point in trace.branch_points
    )
    return replace(trace, episode_id=plan.episode_id, branch_points=points)


def _surface_hash(point: BranchPoint) -> str:
    payload = canonical_json(point.public_state) + "|" + "|".join(sorted(str(item["canonical_identity"]) for item in point.candidates))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _trace_hash(point: BranchPoint) -> str:
    return hashlib.sha256(canonical_json(point.public_state).encode("utf-8")).hexdigest()


def _write_trace(path: Path, trace: SourceTrace) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = SourceTrace.from_dict(json.loads(path.read_text(encoding="utf-8")))
        if existing.to_dict() != trace.to_dict():
            raise FileExistsError(f"source output differs from existing artifact: {path}")
        return
    path.write_text(json.dumps(trace.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")


def collect_source(config: CoverageConfig, *, pilot: bool = False, shard_count: int | None = None, shard_index: int | None = None) -> dict[str, Any]:
    """Collect only the requested shard; never deletes or overwrites traces."""

    plans = all_plans(config, pilot=pilot)
    if shard_count is not None:
        if shard_index is None or not 0 <= int(shard_index) < int(shard_count):
            raise ValueError("invalid source shard")
        plans = [plan for plan in plans if int(hashlib.sha256(plan.episode_id.encode("utf-8")).hexdigest()[:16], 16) % int(shard_count) == int(shard_index)]
    old_config = load_rollout_spec()
    engine = _load_engine()
    rows = {str(row["id"]): row for row in _opponent_rows()}
    emitted: list[SourceTrace] = []
    errors: list[dict[str, Any]] = []
    for plan in plans:
        path = output_path(config, "source", plan.split, f"{plan.episode_id}.json")
        try:
            if path.is_file():
                trace = SourceTrace.from_dict(json.loads(path.read_text(encoding="utf-8")))
            else:
                row = rows.get(plan.opponent_id)
                if row is None:
                    raise KeyError(plan.opponent_id)
                trace = _collect_one(
                    config=old_config,
                    round_index=0,
                    opponent_id=plan.opponent_id,
                    opponent_dir=resolve_opponent_dir(row, old_config),
                    seat=plan.seat,
                    seed=plan.seed,
                    engine=engine,
                    max_steps=config.maximum_search_steps,
                    source_policy_factory=None,
                )
                trace = _rewrite_trace(trace, plan)
                _write_trace(path, trace)
            emitted.append(trace)
        except Exception as exc:
            errors.append({"episode_id": plan.episode_id, "error": f"{type(exc).__name__}: {exc}"})
    summary: dict[str, Any] = {
        "schema_version": "archaludon-search-q-source-summary-v1",
        "pilot": bool(pilot),
        "requested": len(plans),
        "emitted": len(emitted),
        "clean": sum(int(trace.clean_terminal) for trace in emitted),
        "split": {split: {"requested": sum(int(plan.split == split) for plan in plans), "emitted": sum(int(trace.episode_id.startswith(f"coverage_v1_{split}_")) for trace in emitted), "clean": sum(int(trace.clean_terminal and trace.episode_id.startswith(f"coverage_v1_{split}_")) for trace in emitted)} for split in ("training", "calibration", "offline_test")},
        "cell_counts": {f"{plan.opponent_id}|seat{plan.seat}": sum(int(item.cell_index == plan.cell_index) for item in plans) for plan in plans},
        "action_error": sum(int(trace.action_errors) for trace in emitted),
        "max_step": sum(int(trace.max_step_hit) for trace in emitted),
        "source_model_failure": sum(int(trace.source_model_failure_count) for trace in emitted),
        "eligible_branch_group_count": sum(len(trace.branch_points) for trace in emitted),
        "unique_public_state_hash_count": len({_trace_hash(point) for trace in emitted for point in trace.branch_points}),
        "unique_decision_surface_hash_count": len({_surface_hash(point) for trace in emitted for point in trace.branch_points}),
        "duplicate_public_state_rate": None,
        "duplicate_decision_surface_rate": None,
        "errors": errors,
        "engine_dir": str(engine[3]),
        "source_root": str(output_path(config, "source")),
    }
    total_points = int(summary["eligible_branch_group_count"])
    if total_points:
        summary["duplicate_public_state_rate"] = 1.0 - float(summary["unique_public_state_hash_count"]) / total_points
        summary["duplicate_decision_surface_rate"] = 1.0 - float(summary["unique_decision_surface_hash_count"]) / total_points
    write_json(output_path(config, "source", "source_summary.json"), summary)
    if errors:
        raise RuntimeError(f"source collection failed for {len(errors)} episode(s)")
    return summary


def load_source_traces(config: CoverageConfig, plans: Iterable[SourceEpisodePlan] | None = None) -> list[SourceTrace]:
    selected = plans_by_episode(plans or all_plans(config))
    result: list[SourceTrace] = []
    for plan in selected.values():
        path = output_path(config, "source", plan.split, f"{plan.episode_id}.json")
        if path.is_file():
            result.append(SourceTrace.from_dict(json.loads(path.read_text(encoding="utf-8"))))
    return sorted(result, key=lambda trace: trace.episode_id)


__all__ = ["collect_source", "load_source_traces"]
