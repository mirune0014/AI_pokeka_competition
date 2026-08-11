"""Pilot and full group workers for paired determinization rollouts."""

from __future__ import annotations

from collections import defaultdict
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_task_builder import read_tasks
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import BranchTask, SourceTrace

from .config import MultiDetConfig, input_path, output_path, write_json
from .hidden_sampler import sample_hidden_zones
from .search_runtime import replay_to_branch_root, run_candidate_search


GROUP_SCHEMA = "archaludon-multidet-group-result-v1"


def _groups(tasks: Iterable[BranchTask]) -> dict[str, list[BranchTask]]:
    result: dict[str, list[BranchTask]] = defaultdict(list)
    for task in tasks:
        result[task.branch_group_id].append(task)
    for group in result.values():
        group.sort(key=lambda item: (int(item.candidate_index), item.task_id))
    return dict(result)


def load_task_groups(config: MultiDetConfig) -> dict[str, list[BranchTask]]:
    path = input_path(config, "tasks", "all_tasks.jsonl")
    return _groups(read_tasks(path))


def select_pilot_groups(config: MultiDetConfig, groups: Mapping[str, Sequence[BranchTask]]) -> dict[str, list[BranchTask]]:
    by_cell: dict[tuple[str, int], list[str]] = defaultdict(list)
    for group_id, tasks in groups.items():
        if not tasks:
            continue
        by_cell[(str(tasks[0].opponent_id), int(tasks[0].seat))].append(group_id)
    selected: dict[str, list[BranchTask]] = {}
    for cell, group_ids in sorted(by_cell.items()):
        for group_id in sorted(group_ids)[: int(config.pilot_groups_per_opponent_seat)]:
            selected[group_id] = list(groups[group_id])
    return selected


def assigned(group_id: str, shard_count: int, shard_index: int) -> bool:
    return int(group_id[:16], 16) % int(shard_count) == int(shard_index)


def _trace(config: MultiDetConfig, task: BranchTask) -> SourceTrace:
    path = input_path(config, "source_traces", f"{task.source_episode_id}.json")
    return SourceTrace.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _sample_std(values: Sequence[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def _candidate_stats(
    task: BranchTask,
    rewards: Sequence[float],
    baseline_rewards: Sequence[float],
    *,
    is_baseline: bool,
    z_value: float,
) -> dict[str, Any]:
    if len(rewards) != len(baseline_rewards):
        raise RuntimeError("paired reward length mismatch")
    mean = sum(rewards) / len(rewards)
    std = _sample_std(rewards)
    se = std / math.sqrt(len(rewards)) if rewards else float("nan")
    row: dict[str, Any] = {
        "task_id": task.task_id,
        "candidate_index": int(task.candidate_index),
        "canonical_identity": task.candidate_identity,
        "is_baseline": bool(is_baseline),
        "rewards": [float(value) for value in rewards],
        "mean_reward": float(mean),
        "sample_std": float(std),
        "standard_error": float(se),
    }
    if not is_baseline:
        deltas = [float(reward) - float(base) for reward, base in zip(rewards, baseline_rewards)]
        delta_mean = sum(deltas) / len(deltas)
        delta_std = _sample_std(deltas)
        delta_se = delta_std / math.sqrt(len(deltas)) if deltas else float("nan")
        row.update(
            {
                "paired_deltas": deltas,
                "mean_delta": float(delta_mean),
                "delta_sample_std": float(delta_std),
                "delta_standard_error": float(delta_se),
                "delta_lcb90": float(delta_mean - z_value * delta_se),
                "delta_ucb90": float(delta_mean + z_value * delta_se),
                "positive_delta_count": sum(int(value > 0.0) for value in deltas),
                "zero_delta_count": sum(int(value == 0.0) for value in deltas),
                "negative_delta_count": sum(int(value < 0.0) for value in deltas),
            }
        )
    return row


def run_group(config: MultiDetConfig, tasks: Sequence[BranchTask], rollout_count: int) -> dict[str, Any]:
    if not tasks:
        raise ValueError("empty branch group")
    ordered = sorted(tasks, key=lambda item: (int(item.candidate_index), item.task_id))
    group_id = ordered[0].branch_group_id
    if any(task.branch_group_id != group_id for task in ordered):
        raise ValueError("group contains multiple branch_group_id values")
    baseline_tasks = [task for task in ordered if int(task.candidate_index) == int(task.baseline_candidate_index)]
    if len(baseline_tasks) != 1:
        raise ValueError("group must contain exactly one baseline candidate")
    baseline_task = baseline_tasks[0]
    trace = _trace(config, baseline_task)
    rewards: dict[str, list[float]] = {task.task_id: [] for task in ordered}
    fingerprints: list[str] = []
    for rollout_index in range(int(rollout_count)):
        hidden_root = replay_to_branch_root(config, baseline_task, trace)
        source_deck = hidden_root.source_policy.deck
        opponent_deck = hidden_root.opponent_policy.deck
        hidden = sample_hidden_zones(
            hidden_root.observation,
            branch_group_id=group_id,
            rollout_index=rollout_index,
            your_deck=source_deck,
            opponent_deck=opponent_deck,
            api_module=__import__("cg.api", fromlist=["all_card_data"]),
        )
        fingerprints.append(hidden.fingerprint)
        for task in ordered:
            root = hidden_root if task.task_id == baseline_task.task_id else replay_to_branch_root(config, task, trace)
            if root.branch_point.branch_group_id != group_id:
                raise RuntimeError("replayed root group mismatch")
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
    candidates = [
        _candidate_stats(
            task,
            rewards[task.task_id],
            baseline_rewards,
            is_baseline=task.task_id == baseline_task.task_id,
            z_value=config.lcb_z_value,
        )
        for task in ordered
    ]
    if any(len(candidate["rewards"]) != int(rollout_count) for candidate in candidates):
        raise RuntimeError("candidate rollout count mismatch")
    return {
        "schema_version": GROUP_SCHEMA,
        "branch_group_id": group_id,
        "source_episode_id": baseline_task.source_episode_id,
        "opponent_id": baseline_task.opponent_id,
        "seat": int(baseline_task.seat),
        "branch_step_index": int(baseline_task.branch_step_index),
        "rollout_count": int(rollout_count),
        "determinization_fingerprints": fingerprints,
        "baseline_candidate_index": int(baseline_task.baseline_candidate_index),
        "candidates": candidates,
        "status": "OK",
    }


def _read_existing(path: Path, expected_groups: Mapping[str, Sequence[BranchTask]]) -> tuple[list[dict[str, Any]], set[str], int]:
    if not path.is_file():
        return [], set(), 0
    expected = set(expected_groups)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    truncated = 0
    dirty = False
    raw_lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    for index, raw in enumerate(raw_lines):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except Exception:
            if index == len(raw_lines) - 1 and not raw.endswith(("\n", "\r")):
                truncated += 1
                dirty = True
                break
            raise RuntimeError(f"malformed group result before final line: {path}:{index + 1}")
        if not isinstance(row, dict) or row.get("schema_version") != GROUP_SCHEMA:
            raise RuntimeError(f"invalid group result schema: {path}:{index + 1}")
        group_id = str(row.get("branch_group_id", ""))
        if group_id in seen:
            raise RuntimeError(f"duplicate group result: {group_id}")
        if group_id not in expected:
            raise RuntimeError(f"group result is not assigned to this worker: {group_id}")
        expected_task_ids = {task.task_id for task in expected_groups[group_id]}
        actual_task_ids = {str(item.get("task_id")) for item in row.get("candidates", ())} if isinstance(row.get("candidates"), list) else set()
        if row.get("status") != "OK" or actual_task_ids != expected_task_ids:
            # A group is atomic. Its incomplete/error line is omitted so the
            # caller reruns the whole group; only the final malformed line is
            # treated as an interrupted write below.
            dirty = True
            continue
        seen.add(group_id)
        rows.append(row)
    if dirty:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n")
    return rows, seen, truncated


def run_groups(
    config: MultiDetConfig,
    groups: Mapping[str, Sequence[BranchTask]],
    *,
    output_file: Path,
    rollout_count: int,
) -> dict[str, Any]:
    expected = set(groups)
    existing_rows, completed, truncated = _read_existing(output_file, groups)
    pending = [group_id for group_id in sorted(expected) if group_id not in completed]
    output_file.parent.mkdir(parents=True, exist_ok=True)
    errors = 0
    written = 0
    started_at = time.perf_counter()
    with output_file.open("a", encoding="utf-8", newline="\n") as handle:
        for group_id in pending:
            try:
                row = run_group(config, groups[group_id], rollout_count)
            except Exception as exc:
                errors += 1
                row = {
                    "schema_version": GROUP_SCHEMA,
                    "branch_group_id": group_id,
                    "source_episode_id": groups[group_id][0].source_episode_id,
                    "opponent_id": groups[group_id][0].opponent_id,
                    "seat": int(groups[group_id][0].seat),
                    "branch_step_index": int(groups[group_id][0].branch_step_index),
                    "rollout_count": 0,
                    "determinization_fingerprints": [],
                    "baseline_candidate_index": int(groups[group_id][0].baseline_candidate_index),
                    "candidates": [],
                    "status": "ERROR",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False) + "\n")
            handle.flush()
            written += 1
    summary = {
        "schema_version": "archaludon-multidet-worker-summary-v1",
        "group_count": len(groups),
        "completed_groups_before_run": len(completed),
        "pending_groups": len(pending),
        "written_groups": written,
        "truncated_final_lines": truncated,
        "rollout_count": int(rollout_count),
        "error_count": errors,
        "elapsed_seconds": time.perf_counter() - started_at,
        "output_path": str(output_file),
    }
    write_json(output_file.with_name(output_file.stem + "_summary.json"), summary)
    if errors:
        raise RuntimeError(f"{errors} group(s) failed; see {output_file}")
    return summary


def pilot_gate(config: MultiDetConfig) -> dict[str, Any]:
    """Check the fixed pilot technical gate and write its immutable receipt."""

    groups = select_pilot_groups(config, load_task_groups(config))
    path = output_path(config, "pilot", "group_results.jsonl")
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    group_count = len(rows)
    candidate_count = sum(len(row.get("candidates", ())) for row in rows if row.get("status") == "OK")
    search_rollouts = sum(len(candidate.get("rewards", ())) for row in rows for candidate in row.get("candidates", ()))
    worker_summary_path = path.with_name("group_results_summary.json")
    worker_summary = json.loads(worker_summary_path.read_text(encoding="utf-8")) if worker_summary_path.is_file() else {}
    elapsed = float(worker_summary.get("elapsed_seconds", 0.0) or 0.0)
    rollout_per_second = search_rollouts / elapsed if elapsed > 0.0 else 0.0
    projected_full_hours = (
        (98323 * config.full_determinizations) / (rollout_per_second * 4.0) / 3600.0
        if rollout_per_second > 0.0
        else float("inf")
    )
    fingerprint_counts = [len(set(row.get("determinization_fingerprints", ()))) for row in rows if row.get("status") == "OK"]
    fingerprint_errors = sum(int(len(row.get("determinization_fingerprints", ())) != config.pilot_determinizations) for row in rows)
    candidate_missing = sum(
        int(row.get("status") != "OK" or len(row.get("candidates", ())) != len(groups.get(str(row.get("branch_group_id")), ())))
        for row in rows
    )
    error_rows = [row for row in rows if row.get("status") != "OK"]
    error_text = " ".join(str(row.get("error", "")) for row in error_rows)
    root_mismatches = sum(int(token in error_text) for token in ("SearchRootMismatch", "PrefixReplayMismatch"))
    determinization_errors = sum(int(token in error_text) for token in ("DeterminizationError", "UnsupportedRootSurface"))
    search_begin_errors = sum(int("search_begin" in str(row.get("error", ""))) for row in error_rows)
    search_step_errors = sum(int("search API error" in str(row.get("error", ""))) for row in error_rows)
    action_errors = sum(int("action" in str(row.get("error", "")).lower()) for row in error_rows)
    max_step = sum(int("maximum search steps" in str(row.get("error", ""))) for row in error_rows)

    # Compare the pilot alternatives with the immutable single-rollout Round
    # 0 results. This reads the old merge only; it never writes to it.
    old_result_path = input_path(config, "branch_results", "all_results.jsonl")
    old_results: dict[str, Any] = {}
    if old_result_path.is_file():
        from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import BranchResult
        for line in old_result_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                result = BranchResult.from_dict(json.loads(line))
                old_results[result.task_id] = result
    original_improved: list[float] = []
    original_worse: list[float] = []
    lcb_positive = 0
    ucb_negative = 0
    for row in rows:
        if row.get("status") != "OK":
            continue
        baseline = next((item for item in row.get("candidates", ()) if item.get("is_baseline")), None)
        if baseline is None:
            continue
        baseline_old = old_results.get(str(baseline.get("task_id")))
        for candidate in row.get("candidates", ()):
            if candidate.get("is_baseline"):
                continue
            lcb_positive += int(float(candidate.get("delta_lcb90", 0.0)) > 0.0)
            ucb_negative += int(float(candidate.get("delta_ucb90", 0.0)) < 0.0)
            candidate_old = old_results.get(str(candidate.get("task_id")))
            if baseline_old is None or candidate_old is None or baseline_old.reward is None or candidate_old.reward is None:
                continue
            original_delta = float(candidate_old.reward) - float(baseline_old.reward)
            if original_delta > 0.0:
                original_improved.append(float(candidate.get("mean_delta", 0.0)) > 0.0)
            elif original_delta < 0.0:
                original_worse.append(float(candidate.get("mean_delta", 0.0)) < 0.0)
    gate = {
        "groups": group_count,
        "candidates": candidate_count,
        "search_rollouts": search_rollouts,
        "root_mismatch_count": root_mismatches,
        "determinization_error_count": determinization_errors,
        "search_begin_error_count": search_begin_errors,
        "search_step_error_count": search_step_errors,
        "root_public_projection_mismatch_count": root_mismatches,
        "root_candidate_identity_mismatch_count": root_mismatches,
        "action_error_count": action_errors,
        "max_step_count": max_step,
        "candidate_missing_count": candidate_missing,
        "fingerprint_mismatch_count": fingerprint_errors,
        "determinization_completion_rate": (
            sum(int(len(candidate.get("rewards", ())) == config.pilot_determinizations) for row in rows for candidate in row.get("candidates", ())) / max(1, search_rollouts // config.pilot_determinizations)
        ),
        "unique_fingerprint_distribution": {
            "min": min(fingerprint_counts) if fingerprint_counts else None,
            "median": statistics.median(fingerprint_counts) if fingerprint_counts else None,
            "p90": _percentile(fingerprint_counts, 0.90),
            "max": max(fingerprint_counts) if fingerprint_counts else None,
        },
        "stderr_error_count": len(error_rows),
        "original_single_rollout_improved_mean_delta_positive_rate": (sum(original_improved) / len(original_improved)) if original_improved else None,
        "original_single_rollout_worse_mean_delta_negative_rate": (sum(original_worse) / len(original_worse)) if original_worse else None,
        "lcb90_positive_candidate_count": lcb_positive,
        "ucb90_negative_candidate_count": ucb_negative,
        "elapsed_seconds": elapsed,
        "rollout_per_second": rollout_per_second,
        "projected_full_hours_4_workers": projected_full_hours,
        "technical_gate_passed": bool(
            group_count >= 400
            and not error_rows
            and root_mismatches == 0
            and determinization_errors == 0
            and search_begin_errors == 0
            and search_step_errors == 0
            and action_errors == 0
            and max_step == 0
            and candidate_missing == 0
            and fingerprint_errors == 0
            and all(count >= 6 for count in fingerprint_counts)
            and projected_full_hours <= 144.0
        ),
    }
    write_json(output_path(config, "pilot", "pilot_summary.json"), gate)
    return gate


def _percentile(values: Sequence[int], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    weight = position - lower
    return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)


def run_pilot(config: MultiDetConfig) -> dict[str, Any]:
    groups = select_pilot_groups(config, load_task_groups(config))
    return run_groups(
        config,
        groups,
        output_file=output_path(config, "pilot", "group_results.jsonl"),
        rollout_count=config.pilot_determinizations,
    )


def run_full_shard(config: MultiDetConfig, *, shard_count: int, shard_index: int) -> dict[str, Any]:
    if shard_count != 4 or not 0 <= int(shard_index) < 4:
        raise ValueError("full execution is frozen to four shards")
    all_groups = load_task_groups(config)
    groups = {
        group_id: tasks
        for group_id, tasks in all_groups.items()
        if assigned(group_id, shard_count, shard_index)
    }
    return run_groups(
        config,
        groups,
        output_file=output_path(config, "full", f"shard_{shard_index:03d}_of_{shard_count:03d}.jsonl"),
        rollout_count=config.full_determinizations,
    )


__all__ = [
    "GROUP_SCHEMA",
    "assigned",
    "load_task_groups",
    "run_full_shard",
    "run_group",
    "run_groups",
    "run_pilot",
    "select_pilot_groups",
]
