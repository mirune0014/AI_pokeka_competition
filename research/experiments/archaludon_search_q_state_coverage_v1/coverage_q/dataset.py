"""Build the existing expected-Q dataset schema for nested milestones."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Mapping

from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import BranchTask

from .config import CoverageConfig, output_path, write_json
from .search_plan import load_plan


DATASET_SCHEMA = "archaludon-search-q-state-coverage-dataset-v1"


def _family(candidate: Mapping[str, Any]) -> str:
    values = []
    for option in candidate.get("selected_options", ()):
        payload = option.get("semantic_payload") or option.get("payload") or {}
        values.append(str(payload.get("option_type", payload.get("type", "empty"))) if isinstance(payload, Mapping) else "empty")
    return "empty" if not values else "+".join(sorted(values))


def _task_groups(config: CoverageConfig) -> dict[str, list[BranchTask]]:
    path = output_path(config, "manifests", "branch_tasks.jsonl")
    groups: dict[str, list[BranchTask]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            task = BranchTask.from_dict(json.loads(line))
            groups[task.branch_group_id].append(task)
    for values in groups.values():
        values.sort(key=lambda task: (task.candidate_index, task.task_id))
    return dict(groups)


def _merged_rows(config: CoverageConfig, stage: str) -> list[dict[str, Any]]:
    path = output_path(config, "search", stage, "merged.jsonl")
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _dataset_row(result: Mapping[str, Any], tasks: list[BranchTask], milestones: list[str]) -> dict[str, Any]:
    baseline_task = next(task for task in tasks if task.candidate_index == task.baseline_candidate_index)
    result_by_index = {int(candidate["candidate_index"]): candidate for candidate in result["candidates"]}
    candidates: list[dict[str, Any]] = []
    for task in tasks:
        candidate_meta = next(item for item in task.candidates if int(item["candidate_index"]) == task.candidate_index)
        value = result_by_index[task.candidate_index]
        is_baseline = task.candidate_index == task.baseline_candidate_index
        candidates.append(
            {
                "task_id": task.task_id,
                "candidate_index": task.candidate_index,
                "canonical_identity": task.candidate_identity,
                "is_baseline": is_baseline,
                "action": list(task.candidate_action),
                "selected_options": [dict(item) for item in candidate_meta.get("selected_options", ())],
                "selected_option_semantic_payload": [dict(item.get("semantic_payload", {})) for item in candidate_meta.get("selected_options", ())],
                "family": _family(candidate_meta),
                "target_q": float(value["mean_reward"]),
                "target_delta": None if is_baseline else float(value["mean_delta"]),
                "delta_lcb90": None if is_baseline else float(value["delta_lcb90"]),
                "delta_ucb90": None if is_baseline else float(value["delta_ucb90"]),
                "mean_reward": float(value["mean_reward"]),
                "mean_delta": None if is_baseline else float(value["mean_delta"]),
                "rewards": list(value.get("rewards", ())),
                "positive_delta_count": int(value.get("positive_delta_count", 0)),
                "zero_delta_count": int(value.get("zero_delta_count", 0)),
                "negative_delta_count": int(value.get("negative_delta_count", 0)),
            }
        )
    return {
        "source_episode_id": baseline_task.source_episode_id,
        "split": str(result["split"]),
        "milestones": list(milestones),
        "branch_group_id": baseline_task.branch_group_id,
        "opponent_id": baseline_task.opponent_id,
        "seat": int(baseline_task.seat),
        "seed": int(baseline_task.seed),
        "branch_step_index": int(baseline_task.branch_step_index),
        "public_state": dict(baseline_task.public_state),
        "context": int((baseline_task.public_state.get("select") or {}).get("context", 0) or 0),
        "baseline_candidate_index": int(baseline_task.baseline_candidate_index),
        "baseline_reward": float(result.get("baseline_reward", 0.0)),
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def _write_dataset(config: CoverageConfig, name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    path = output_path(config, "datasets", f"{name}.json")
    payload = {"schema_version": DATASET_SCHEMA, "dataset": name, "group_count": len(rows), "rows": rows}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != payload:
            raise FileExistsError(f"dataset differs from existing artifact: {path}")
    else:
        write_json(path, payload)
    return {"dataset": name, "groups": len(rows), "path": str(path)}


def build_datasets(config: CoverageConfig) -> dict[str, Any]:
    tasks = _task_groups(config)
    plan_by_group = {str(row["branch_group_id"]): row for row in load_plan(config)}
    stage_rows = {stage: _merged_rows(config, stage) for stage in ("train_m05", "train_m10_increment", "train_m20_increment", "calibration", "offline_test")}
    built: dict[str, list[dict[str, Any]]] = {}
    built["training_m05"] = [_dataset_row(row, tasks[str(row["branch_group_id"])], list(plan_by_group[str(row["branch_group_id"])]["milestones"])) for row in stage_rows["train_m05"]]
    built["training_m10"] = built["training_m05"] + [_dataset_row(row, tasks[str(row["branch_group_id"])], list(plan_by_group[str(row["branch_group_id"])]["milestones"])) for row in stage_rows["train_m10_increment"]]
    built["training_m20"] = built["training_m10"] + [_dataset_row(row, tasks[str(row["branch_group_id"])], list(plan_by_group[str(row["branch_group_id"])]["milestones"])) for row in stage_rows["train_m20_increment"]]
    built["calibration"] = [_dataset_row(row, tasks[str(row["branch_group_id"])], []) for row in stage_rows["calibration"]]
    built["offline_test"] = [_dataset_row(row, tasks[str(row["branch_group_id"])], []) for row in stage_rows["offline_test"]]
    summaries = {name: _write_dataset(config, name, rows) for name, rows in built.items()}
    source_ids: dict[str, str] = {}
    for name, rows in built.items():
        for row in rows:
            prior = source_ids.setdefault(row["source_episode_id"], name)
            if prior != name and row["split"] != "training":
                raise RuntimeError(f"source episode leaked across split datasets: {row['source_episode_id']}")
    result = {"schema_version": "archaludon-search-q-dataset-summary-v1", "datasets": summaries, "training_m05_groups": len(built["training_m05"]), "training_m10_groups": len(built["training_m10"]), "training_m20_groups": len(built["training_m20"]), "calibration_groups": len(built["calibration"]), "offline_test_groups": len(built["offline_test"])}
    write_json(output_path(config, "datasets", "dataset_summary.json"), result)
    return result


def load_dataset(config: CoverageConfig, name: str) -> dict[str, Any]:
    path = output_path(config, "datasets", f"{name}.json")
    return json.loads(path.read_text(encoding="utf-8"))


__all__ = ["DATASET_SCHEMA", "build_datasets", "load_dataset"]
