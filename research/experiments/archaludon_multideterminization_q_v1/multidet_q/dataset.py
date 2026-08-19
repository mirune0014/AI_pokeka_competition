"""Build one expected-Q learning sample per branch group."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_task_builder import read_tasks
from research.experiments.archaludon_rollout_q_v1.rollout_q.dataset import episode_split

from .config import MultiDetConfig, input_path, output_path, read_json, write_json
from .worker import GROUP_SCHEMA, load_task_groups


DATASET_SCHEMA = "archaludon-multidet-expected-q-dataset-v1"


def _family(candidate: Mapping[str, Any]) -> str:
    values: list[str] = []
    for option in candidate.get("selected_options", ()):
        payload = option.get("semantic_payload") or option.get("payload") or {}
        if isinstance(payload, Mapping):
            value = payload.get("option_type", payload.get("type", "empty"))
        else:
            value = "empty"
        values.append(str(value))
    return "empty" if not values else "+".join(sorted(values))


def _read_merged(config: MultiDetConfig) -> list[dict[str, Any]]:
    path = output_path(config, "full", "merged_groups.jsonl")
    if not path.is_file():
        raise FileNotFoundError(path)
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def build_dataset(config: MultiDetConfig) -> dict[str, Any]:
    groups = load_task_groups(config)
    merged = _read_merged(config)
    task_by_group = {group_id: sorted(tasks, key=lambda item: (int(item.candidate_index), item.task_id)) for group_id, tasks in groups.items()}
    rows: list[dict[str, Any]] = []
    for result in sorted(merged, key=lambda item: str(item["branch_group_id"])):
        group_id = str(result["branch_group_id"])
        tasks = task_by_group.get(group_id)
        if tasks is None:
            raise RuntimeError(f"merged group has no task metadata: {group_id}")
        if result.get("schema_version") != GROUP_SCHEMA or result.get("status") != "OK":
            raise RuntimeError(f"merged group is not OK: {group_id}")
        candidate_results = {int(item["candidate_index"]): item for item in result["candidates"]}
        if set(candidate_results) != {int(task.candidate_index) for task in tasks}:
            raise RuntimeError(f"candidate set mismatch in dataset group: {group_id}")
        baseline_task = next(task for task in tasks if int(task.candidate_index) == int(task.baseline_candidate_index))
        baseline_result = candidate_results[int(baseline_task.candidate_index)]
        candidates: list[dict[str, Any]] = []
        ordered_tasks = [baseline_task] + sorted(
            [task for task in tasks if task.task_id != baseline_task.task_id],
            key=lambda item: item.candidate_identity,
        )
        for task in ordered_tasks:
            value = candidate_results[int(task.candidate_index)]
            candidate = next(item for item in task.candidates if int(item["candidate_index"]) == int(task.candidate_index))
            target_q = float(value["mean_reward"])
            target_delta = None if task.task_id == baseline_task.task_id else float(value["mean_delta"])
            target_lcb90 = None if task.task_id == baseline_task.task_id else float(value["delta_lcb90"])
            candidates.append(
                {
                    "task_id": task.task_id,
                    "candidate_index": int(task.candidate_index),
                    "canonical_identity": task.candidate_identity,
                    "is_baseline": task.task_id == baseline_task.task_id,
                    "action": list(task.candidate_action),
                    "selected_options": [dict(item) for item in candidate.get("selected_options", ())],
                    "family": _family(candidate),
                    "target_q": target_q,
                    "target_delta": target_delta,
                    "target_lcb90": target_lcb90,
                    "rewards": list(value["rewards"]),
                    "mean_reward": target_q,
                    "mean_delta": target_delta,
                    "delta_lcb90": target_lcb90,
                    "delta_ucb90": None if task.task_id == baseline_task.task_id else float(value["delta_ucb90"]),
                    "positive_delta_count": int(value.get("positive_delta_count", 0)),
                    "zero_delta_count": int(value.get("zero_delta_count", 0)),
                    "negative_delta_count": int(value.get("negative_delta_count", 0)),
                }
            )
        select = (baseline_task.public_state.get("select") or {}) if isinstance(baseline_task.public_state, Mapping) else {}
        rows.append(
            {
                "source_episode_id": baseline_task.source_episode_id,
                "opponent_id": baseline_task.opponent_id,
                "seat": int(baseline_task.seat),
                "seed": int(baseline_task.seed),
                "branch_group_id": group_id,
                "branch_step_index": int(baseline_task.branch_step_index),
                "context": int(select.get("context", 0) or 0),
                "split": episode_split(baseline_task.source_episode_id),
                "public_state": dict(baseline_task.public_state),
                "baseline_candidate_index": int(baseline_task.baseline_candidate_index),
                "baseline_reward": float(baseline_result["mean_reward"]),
                "candidate_count": len(candidates),
                "candidates": candidates,
            }
        )
    output = output_path(config, "dataset_through_round_00.json")
    if output.exists():
        raise FileExistsError(output)
    payload = {
        "schema_version": DATASET_SCHEMA,
        "through_round": 0,
        "group_count": len(rows),
        "rows": rows,
    }
    write_json(output, payload)
    alternative_candidates = [candidate for row in rows for candidate in row["candidates"] if not candidate["is_baseline"]]
    summary = {
        "schema_version": "archaludon-multidet-dataset-summary-v1",
        "group_count": len(rows),
        "training_groups": sum(int(row["split"] == "training") for row in rows),
        "validation_groups": sum(int(row["split"] == "validation") for row in rows),
        "candidate_rows": len(alternative_candidates) + len(rows),
        "alternative_candidate_rows": len(alternative_candidates),
        "robust_improved_candidates": sum(int((candidate["target_lcb90"] or 0.0) > 0.0) for candidate in alternative_candidates),
        "robust_worse_candidates": sum(int((candidate.get("delta_ucb90") or 0.0) < 0.0) for candidate in alternative_candidates),
        "uncertain_candidates": sum(int(not ((candidate["target_lcb90"] or 0.0) > 0.0 or (candidate.get("delta_ucb90") or 0.0) < 0.0)) for candidate in alternative_candidates),
        "dataset_path": str(output),
    }
    write_json(output_path(config, "dataset_through_round_00_summary.json"), summary)
    return summary


def load_dataset(config: MultiDetConfig) -> dict[str, Any]:
    path = output_path(config, "dataset_through_round_00.json")
    if not path.is_file():
        raise FileNotFoundError(path)
    return read_json(path)


__all__ = ["DATASET_SCHEMA", "build_dataset", "load_dataset"]
