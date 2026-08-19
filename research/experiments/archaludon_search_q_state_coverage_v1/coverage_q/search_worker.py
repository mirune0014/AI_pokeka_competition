"""Six-shard paired-determinization worker using the frozen Search-Q runtime."""

from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
import time
from typing import Any, Mapping, Sequence

from research.experiments.archaludon_multideterminization_q_v1.multidet_q.hidden_sampler import sample_hidden_zones
from research.experiments.archaludon_multideterminization_q_v1.multidet_q.search_runtime import _load_api, replay_to_branch_root, run_candidate_search
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import BranchTask, SourceTrace

from .config import CoverageConfig, output_path, write_json
from .search_plan import STAGES, group_shard, load_plan


GROUP_SCHEMA = "archaludon-search-q-state-coverage-group-v1"


def _tasks(config: CoverageConfig) -> dict[str, list[BranchTask]]:
    path = output_path(config, "manifests", "branch_tasks.jsonl")
    groups: dict[str, list[BranchTask]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            raw = json.loads(line)
            task = BranchTask.from_dict(raw)
            groups[task.branch_group_id].append(task)
    for group in groups.values():
        group.sort(key=lambda item: (item.candidate_index, item.task_id))
    return dict(groups)


def _trace(config: CoverageConfig, task: BranchTask) -> SourceTrace:
    for split in ("training", "calibration", "offline_test"):
        path = output_path(config, "source", split, f"{task.source_episode_id}.json")
        if path.is_file():
            return SourceTrace.from_dict(json.loads(path.read_text(encoding="utf-8")))
    raise FileNotFoundError(task.source_episode_id)


def _sample_std(values: Sequence[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def _stats(task: BranchTask, rewards: Sequence[float], baseline: Sequence[float], *, is_baseline: bool, z: float) -> dict[str, Any]:
    if len(rewards) != len(baseline):
        raise RuntimeError("paired reward length mismatch")
    mean = sum(rewards) / len(rewards)
    std = _sample_std(rewards)
    row: dict[str, Any] = {
        "task_id": task.task_id,
        "candidate_index": int(task.candidate_index),
        "canonical_identity": task.candidate_identity,
        "is_baseline": bool(is_baseline),
        "rewards": [float(value) for value in rewards],
        "mean_reward": float(mean),
        "sample_std": float(std),
        "standard_error": float(std / math.sqrt(len(rewards)) if rewards else 0.0),
    }
    if not is_baseline:
        deltas = [float(value) - float(base) for value, base in zip(rewards, baseline)]
        delta_mean = sum(deltas) / len(deltas)
        delta_std = _sample_std(deltas)
        delta_se = delta_std / math.sqrt(len(deltas)) if deltas else 0.0
        row.update(
            {
                "paired_deltas": deltas,
                "mean_delta": float(delta_mean),
                "delta_sample_std": float(delta_std),
                "delta_standard_error": float(delta_se),
                "delta_lcb90": float(delta_mean - z * delta_se),
                "delta_ucb90": float(delta_mean + z * delta_se),
                "positive_delta_count": sum(int(value > 0.0) for value in deltas),
                "zero_delta_count": sum(int(value == 0.0) for value in deltas),
                "negative_delta_count": sum(int(value < 0.0) for value in deltas),
            }
        )
    return row


def run_group(config: CoverageConfig, tasks: Sequence[BranchTask], rollout_count: int) -> dict[str, Any]:
    ordered = sorted(tasks, key=lambda item: (item.candidate_index, item.task_id))
    if not ordered:
        raise ValueError("empty branch group")
    group_id = ordered[0].branch_group_id
    baseline_tasks = [task for task in ordered if task.candidate_index == task.baseline_candidate_index]
    if len(baseline_tasks) != 1:
        raise ValueError("group must contain exactly one baseline candidate")
    baseline_task = baseline_tasks[0]
    trace = _trace(config, baseline_task)
    rewards: dict[str, list[float]] = {task.task_id: [] for task in ordered}
    fingerprints: list[str] = []
    api = _load_api()
    for rollout_index in range(int(rollout_count)):
        hidden_root = replay_to_branch_root(config, baseline_task, trace)
        hidden = sample_hidden_zones(
            hidden_root.observation,
            branch_group_id=group_id,
            rollout_index=rollout_index,
            your_deck=hidden_root.source_policy.deck,
            opponent_deck=hidden_root.opponent_policy.deck,
            api_module=api,
        )
        fingerprints.append(hidden.fingerprint)
        for task in ordered:
            root = hidden_root if task.task_id == baseline_task.task_id else replay_to_branch_root(config, task, trace)
            reward = run_candidate_search(
                root,
                hidden,
                task.candidate_action,
                branch_group_id=group_id,
                rollout_index=rollout_index,
                max_steps=config.maximum_search_steps,
                manual_coin=config.manual_coin,
            )
            if reward not in (-1.0, 0.0, 1.0):
                raise RuntimeError("search reward is outside {-1,0,1}")
            rewards[task.task_id].append(float(reward))
    baseline_rewards = rewards[baseline_task.task_id]
    candidates = []
    for task in ordered:
        value = next(item for item in task.candidates if int(item["candidate_index"]) == task.candidate_index)
        row = _stats(task, rewards[task.task_id], baseline_rewards, is_baseline=task.task_id == baseline_task.task_id, z=config.lcb_z_value)
        row.update({"selected_options": [dict(item) for item in value.get("selected_options", ())], "action": list(task.candidate_action), "family": _family(value)})
        candidates.append(row)
    return {
        "schema_version": GROUP_SCHEMA,
        "split": _split_from_episode(baseline_task.source_episode_id),
        "stage": "",
        "source_episode_id": baseline_task.source_episode_id,
        "branch_group_id": group_id,
        "opponent_id": baseline_task.opponent_id,
        "seat": baseline_task.seat,
        "branch_step_index": baseline_task.branch_step_index,
        "candidate_count": len(candidates),
        "baseline_candidate_index": baseline_task.baseline_candidate_index,
        "baseline_reward": float(sum(baseline_rewards) / len(baseline_rewards)) if baseline_rewards else 0.0,
        "rollout_count": int(rollout_count),
        "determinization_fingerprints": fingerprints,
        "candidates": candidates,
        "status": "OK",
    }


def _split_from_episode(episode_id: str) -> str:
    text = str(episode_id)
    if "_offline_test_" in text:
        return "offline_test"
    parts = text.split("_")
    for split in ("training", "calibration", "offline_test"):
        if split in parts:
            return split
    raise ValueError(f"cannot infer split from episode id: {episode_id}")


def _family(candidate: Mapping[str, Any]) -> str:
    values = []
    for option in candidate.get("selected_options", ()):
        payload = option.get("semantic_payload") or option.get("payload") or {}
        values.append(str(payload.get("option_type", payload.get("type", "empty"))) if isinstance(payload, Mapping) else "empty")
    return "empty" if not values else "+".join(sorted(values))


def _read_resume(path: Path, expected: Mapping[str, Sequence[BranchTask]], shard_count: int, shard_index: int) -> tuple[list[dict[str, Any]], set[str], int]:
    if not path.is_file():
        return [], set(), 0
    raw_lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    truncated = 0
    for index, raw in enumerate(raw_lines):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except Exception:
            if index == len(raw_lines) - 1 and not raw.endswith(("\n", "\r")):
                truncated += 1
                break
            raise RuntimeError(f"malformed result before final line: {path}:{index + 1}")
        group_id = str(row.get("branch_group_id", ""))
        if group_id in seen:
            raise RuntimeError(f"duplicate group result: {group_id}")
        if group_id not in expected or group_shard(group_id, shard_count) != shard_index:
            raise RuntimeError(f"result is not assigned to this worker: {group_id}")
        candidate_rows = row.get("candidates", ())
        if row.get("status") != "OK" or len(candidate_rows) != len(expected[group_id]):
            raise RuntimeError(f"incomplete group result: {group_id}")
        rollout_count = int(row.get("rollout_count", 0))
        if rollout_count <= 0 or any(len(candidate.get("rewards", ())) != rollout_count for candidate in candidate_rows):
            raise RuntimeError(f"rollout count mismatch: {group_id}")
        seen.add(group_id)
        rows.append(row)
    if truncated:
        path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")
    return rows, seen, truncated


def run_stage(config: CoverageConfig, stage: str, *, shard_count: int = 6, shard_index: int = 0) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError(stage)
    plan = {str(row["branch_group_id"]): row for row in load_plan(config) if row.get("stage") == stage}
    tasks = _tasks(config)
    groups = {group_id: tasks[group_id] for group_id in sorted(plan) if group_id in tasks and group_shard(group_id, shard_count) == shard_index}
    if set(groups) != {group_id for group_id in plan if group_shard(group_id, shard_count) == shard_index}:
        raise RuntimeError("search plan/task group mismatch")
    output = output_path(config, "search", stage, f"shard_{shard_index:03d}_of_{shard_count:03d}.jsonl")
    _, completed, truncated = _read_resume(output, groups, shard_count, shard_index)
    output.parent.mkdir(parents=True, exist_ok=True)
    errors = 0
    started = time.perf_counter()
    with output.open("a", encoding="utf-8", newline="\n") as handle:
        for group_id in sorted(groups):
            if group_id in completed:
                continue
            try:
                row = run_group(config, groups[group_id], int(plan[group_id]["determinizations"]))
                row["stage"] = stage
            except Exception as exc:
                errors += 1
                row = {"schema_version": GROUP_SCHEMA, "split": plan[group_id]["split"], "stage": stage, "source_episode_id": plan[group_id]["source_episode_id"], "branch_group_id": group_id, "opponent_id": plan[group_id]["opponent_id"], "seat": plan[group_id]["seat"], "branch_step_index": plan[group_id]["branch_step_index"], "candidate_count": plan[group_id]["candidate_count"], "rollout_count": 0, "determinization_fingerprints": [], "candidates": [], "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n")
            handle.flush()
    persisted = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines() if line.strip()]
    summary = {"schema_version": "archaludon-search-q-worker-summary-v1", "stage": stage, "shard_count": shard_count, "shard_index": shard_index, "group_count": len(groups), "completed_groups": len(completed), "written_groups": len(groups) - len(completed), "truncated_final_lines": truncated, "error_count": errors, "elapsed_seconds": time.perf_counter() - started, "rollouts": sum(int(row.get("rollout_count", 0)) * len(row.get("candidates", ())) for row in persisted if row.get("status") == "OK"), "output_path": str(output)}
    write_json(output.with_name(output.stem + "_summary.json"), summary)
    if errors:
        raise RuntimeError(f"{errors} search group(s) failed")
    return summary


__all__ = ["GROUP_SCHEMA", "run_group", "run_stage"]
