"""Assign every collected branch group to exactly one Search-Q stage."""

from __future__ import annotations

from collections import defaultdict
import json
from typing import Any, Mapping

from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_task_builder import tasks_for_trace

from .config import CoverageConfig, output_path, write_json
from .schedule import SourceEpisodePlan, all_plans, plans_by_episode
from .source import load_source_traces


STAGES = ("calibration", "offline_test", "train_m05", "train_m10_increment", "train_m20_increment")


def _stage(plan: SourceEpisodePlan) -> str:
    if plan.split == "calibration":
        return "calibration"
    if plan.split == "offline_test":
        return "offline_test"
    if "m05" in plan.training_milestones:
        return "train_m05"
    if "m10" in plan.training_milestones:
        return "train_m10_increment"
    return "train_m20_increment"


def _selected_for_pilot(records: list[dict[str, Any]], plans: Mapping[str, SourceEpisodePlan]) -> list[dict[str, Any]]:
    by_cell: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        plan = plans[str(row["source_episode_id"])]
        by_cell[(plan.opponent_id, plan.seat, str(row["stage"]))].append(row)
    limits = {"train_m05": 6, "train_m10_increment": 6, "train_m20_increment": 6, "calibration": 2, "offline_test": 2}
    selected: list[dict[str, Any]] = []
    # Training groups are selected by stage, with six per cell in aggregate.
    for key, values in sorted(by_cell.items()):
        selected.extend(sorted(values, key=lambda row: str(row["branch_group_id"]))[: limits[key[2]]])
    return selected


def select_group_records(
    records: list[dict[str, Any]],
    plans: Mapping[str, SourceEpisodePlan],
    *,
    pilot: bool = False,
) -> list[dict[str, Any]]:
    """Apply the Pilot-only group caps, leaving Full plans uncapped.

    The source collector and the Full supervisor both produce one record for
    every eligible branch group.  Keeping the selection in this small helper
    makes the boundary explicit and testable: ``pilot=False`` is an identity
    selection, while ``pilot=True`` is the bounded technical-gate sample.
    """

    ordered = sorted(records, key=lambda row: str(row["branch_group_id"]))
    selected = _selected_for_pilot(ordered, plans) if pilot else ordered
    seen: dict[str, str] = {}
    for row in selected:
        group_id = str(row["branch_group_id"])
        stage = str(row["stage"])
        previous = seen.get(group_id)
        if previous is not None and previous != stage:
            raise ValueError(f"branch group assigned to multiple stages: {group_id}")
        seen[group_id] = stage
    return selected


def build_plan(config: CoverageConfig, *, pilot: bool = False) -> dict[str, Any]:
    plans = plans_by_episode(all_plans(config, pilot=pilot))
    tasks_rows: list[dict[str, Any]] = []
    group_rows: dict[str, dict[str, Any]] = {}
    traces = load_source_traces(config, plans.values())
    if len(traces) != len(plans):
        raise ValueError(f"source trace count mismatch: traces={len(traces)} expected={len(plans)}")
    for trace in traces:
        plan = plans.get(trace.episode_id)
        if plan is None:
            raise ValueError(f"trace is not in fixed schedule: {trace.episode_id}")
        for task in tasks_for_trace(trace):
            tasks_rows.append({"schema_version": "archaludon-branch-task-v1", **task.to_dict()})
            group_rows.setdefault(
                task.branch_group_id,
                {
                    "branch_group_id": task.branch_group_id,
                    "source_episode_id": task.source_episode_id,
                    "split": plan.split,
                    "milestones": list(plan.training_milestones),
                    "stage": _stage(plan),
                    "determinizations": int(config.determinizations[plan.split]),
                    "candidate_count": len(task.candidates),
                    "opponent_id": plan.opponent_id,
                    "seat": plan.seat,
                    "branch_step_index": task.branch_step_index,
                },
            )
    expected_groups = sum(len(trace.branch_points) for trace in traces if trace.clean_terminal)
    if len(group_rows) != expected_groups:
        raise ValueError(f"source branch group mismatch: records={len(group_rows)} expected={expected_groups}")
    records = select_group_records(list(group_rows.values()), plans, pilot=pilot)
    selected_ids = {str(row["branch_group_id"]) for row in records}
    tasks_rows = [row for row in tasks_rows if str(row["branch_group_id"]) in selected_ids]
    manifest = output_path(config, "manifests", "search_plan.jsonl")
    tasks_path = output_path(config, "manifests", "branch_tasks.jsonl")
    manifest.parent.mkdir(parents=True, exist_ok=True)
    for path, rows in ((manifest, records), (tasks_path, tasks_rows)):
        if path.exists():
            old = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if old != rows:
                raise FileExistsError(f"plan artifact differs from existing file: {path}")
        else:
            path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")
    stage_counts = {stage: sum(int(row["stage"] == stage) for row in records) for stage in STAGES}
    result = {"schema_version": "archaludon-search-q-plan-v1", "pilot": bool(pilot), "groups": len(records), "tasks": len(tasks_rows), "stage_counts": stage_counts, "path": str(manifest)}
    write_json(output_path(config, "manifests", "search_plan_summary.json"), result)
    return result


def load_plan(config: CoverageConfig) -> list[dict[str, Any]]:
    path = output_path(config, "manifests", "search_plan.jsonl")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def group_shard(branch_group_id: str, shard_count: int) -> int:
    return int(str(branch_group_id)[:16], 16) % int(shard_count)


__all__ = ["STAGES", "build_plan", "group_shard", "load_plan", "select_group_records"]
