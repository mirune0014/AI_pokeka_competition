"""Resumable stage supervisor and the bounded 96-game Pilot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from .calibrate import calibrate
from .config import CoverageConfig, PILOT_OUTPUT_ROOT, ensure_output, output_path, read_json, write_json
from .dataset import build_datasets
from .merge import merge_all
from .offline_test import offline_test
from .search_plan import STAGES, build_plan, load_plan
from .search_worker import run_stage
from .schedule import SPLITS, all_plans, plans_by_episode
from .source import collect_source, load_source_traces
from .train_milestones import pilot_optimizer_steps, train


# This is the single marker order used by both fresh and resumed Full runs.
# The final offline-test marker is distinct from the earlier Search-Q stage,
# which avoids the historical duplicate ``offline_test`` marker.
FULL_STAGES = (
    "source",
    "build_plan",
    "calibration",
    "offline_test",
    "train_m05",
    "train_m10_increment",
    "train_m20_increment",
    "merge",
    "datasets",
    "train",
    "calibrate",
    "offline_test_final",
)


@dataclass(frozen=True)
class ResumeState:
    status: Mapping[str, Any]
    completed_stages: tuple[str, ...]
    next_stage: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Supervisor:
    def __init__(self, config: CoverageConfig) -> None:
        self.config = config
        self.root = config.output_dir
        self.status_path = output_path(config, "supervisor_status.json")
        self.marker_dir = output_path(config, "stage_markers")

    def status(self, *, stage: str, error: str | None = None, last_successful_stage: str | None = None, **extra: Any) -> dict[str, Any]:
        current = json.loads(self.status_path.read_text(encoding="utf-8")) if self.status_path.is_file() else {}
        value = {"current_stage": stage, "started_at": current.get("started_at", _now()), "updated_at": _now(), "worker_pids": current.get("worker_pids", []), "worker_exit_codes": current.get("worker_exit_codes", {}), "completed_shards": current.get("completed_shards", []), "total_shards": current.get("total_shards", self.config.worker_count), "error": error, "last_successful_stage": last_successful_stage or current.get("last_successful_stage")}
        value.update(extra)
        write_json(self.status_path, value)
        return value

    def marker(self, stage: str, payload: Any = None) -> None:
        path = self.marker_dir / f"{stage}.complete.json"
        if path.exists():
            raise RuntimeError(f"duplicate completion marker: {path}")
        write_json(path, {"stage": stage, "completed_at": _now(), "payload": payload})

    def done(self, stage: str) -> bool:
        return (self.marker_dir / f"{stage}.complete.json").is_file()

    def run_stage(self, stage: str, action: Callable[[], Any]) -> Any:
        if self.done(stage):
            return json.loads((self.marker_dir / f"{stage}.complete.json").read_text(encoding="utf-8")).get("payload")
        self.status(stage=stage)
        try:
            result = action()
            self.marker(stage, result)
            self.status(stage=stage, last_successful_stage=stage)
            return result
        except Exception as exc:
            self.status(stage="blocked", error=f"{type(exc).__name__}: {exc}")
            raise


def _stage_marker_path(config: CoverageConfig, stage: str) -> Path:
    return output_path(config, "stage_markers", f"{stage}.complete.json")


def _iter_payload_mappings(value: Any):
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _iter_payload_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_payload_mappings(child)


def _validate_marker_payload(stage: str, payload: Any) -> None:
    bad_fields = ("error_count", "missing", "duplicate", "action_error", "max_step")
    for mapping in _iter_payload_mappings(payload):
        for field in bad_fields:
            if field not in mapping:
                continue
            try:
                value = int(mapping[field])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid {stage} marker field {field}: {mapping[field]!r}") from exc
            if value > 0:
                raise ValueError(f"unsafe {stage} completion marker: {field}={value}")


def _validate_resume_root(config: CoverageConfig) -> ResumeState:
    root = config.output_dir
    if not root.is_dir():
        raise FileNotFoundError(f"resume output root is missing: {root}")
    status_path = output_path(config, "supervisor_status.json")
    marker_dir = output_path(config, "stage_markers")
    if not status_path.is_file():
        raise FileNotFoundError(f"resume status file is missing: {status_path}")
    if not marker_dir.is_dir():
        raise FileNotFoundError(f"resume stage marker directory is missing: {marker_dir}")
    try:
        status = read_json(status_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"resume status is not valid JSON: {status_path}") from exc
    if not isinstance(status, Mapping):
        raise ValueError("resume status must be a JSON object")
    if status.get("error") is not None:
        raise ValueError(f"cannot resume status with error: {status.get('error')}")
    current_stage = status.get("current_stage")
    if current_stage not in FULL_STAGES:
        raise ValueError(f"unknown resume current_stage: {current_stage!r}")

    completed: list[str] = []
    saw_gap = False
    for stage in FULL_STAGES:
        marker = _stage_marker_path(config, stage)
        if marker.is_file():
            if saw_gap:
                raise ValueError(f"non-contiguous stage markers: {stage}")
            try:
                marker_value = read_json(marker)
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid stage marker: {marker}") from exc
            if not isinstance(marker_value, Mapping) or marker_value.get("stage") != stage:
                raise ValueError(f"stage marker identity mismatch: {marker}")
            _validate_marker_payload(stage, marker_value.get("payload"))
            completed.append(stage)
        else:
            saw_gap = True
    if len(completed) == len(FULL_STAGES):
        raise ValueError("run is already complete")
    next_stage = FULL_STAGES[len(completed)]
    if current_stage != next_stage:
        raise ValueError(
            f"resume current_stage mismatch: status={current_stage!r} next={next_stage!r}"
        )
    last_successful = status.get("last_successful_stage")
    expected_last = completed[-1] if completed else None
    if last_successful is not None and last_successful != expected_last:
        raise ValueError(
            f"resume last_successful_stage mismatch: status={last_successful!r} expected={expected_last!r}"
        )
    return ResumeState(status=status, completed_stages=tuple(completed), next_stage=next_stage)


def _stage_search(config: CoverageConfig, stage: str) -> dict[str, Any]:
    summaries = []
    for shard_index in range(config.worker_count):
        summaries.append(run_stage(config, stage, shard_count=config.worker_count, shard_index=shard_index))
    return {"stage": stage, "shards": summaries}


def _pilot_source_split_stats(config: CoverageConfig, source: Mapping[str, Any]) -> dict[str, dict[str, int]]:
    """Count every Pilot source branch group and candidate, before caps."""

    plans = plans_by_episode(all_plans(config, pilot=True))
    stats = {
        split: {"source_games": 0, "source_branch_groups": 0, "source_candidates": 0}
        for split in SPLITS
    }
    for trace in load_source_traces(config, plans.values()):
        plan = plans.get(trace.episode_id)
        if plan is None:
            raise ValueError(f"Pilot source trace is outside the fixed schedule: {trace.episode_id}")
        row = stats[plan.split]
        row["source_games"] += 1
        if trace.clean_terminal:
            row["source_branch_groups"] += len(trace.branch_points)
            row["source_candidates"] += sum(len(point.candidates) for point in trace.branch_points)
    expected_games = {
        split: int(source.get("split", {}).get(split, {}).get("emitted", 0))
        for split in SPLITS
    }
    for split in SPLITS:
        if stats[split]["source_games"] != expected_games[split]:
            raise ValueError(
                f"Pilot source game mismatch for {split}: "
                f"traces={stats[split]['source_games']} summary={expected_games[split]}"
            )
    return stats


def project_split_stats(config: CoverageConfig, source_stats: Mapping[str, Mapping[str, int]]) -> dict[str, dict[str, float]]:
    """Project all source groups with split-specific Search-Q determinization."""

    projected: dict[str, dict[str, float]] = {}
    for split in SPLITS:
        row = source_stats[split]
        source_games = int(row["source_games"])
        source_groups = int(row["source_branch_groups"])
        source_candidates = int(row["source_candidates"])
        if source_games <= 0 or source_groups <= 0 or source_candidates <= 0:
            raise ValueError(f"Pilot source stats are empty for {split}: {row}")
        full_games = int(config.source_games[split])
        groups_per_game = source_groups / source_games
        candidates_per_group = source_candidates / source_groups
        projected_groups = groups_per_game * full_games
        projected_candidates = projected_groups * candidates_per_group
        determinizations = int(config.determinizations[split])
        projected_rollouts = projected_candidates * determinizations
        projected[split] = {
            "pilot_source_games": float(source_games),
            "pilot_source_branch_groups": float(source_groups),
            "pilot_source_candidates": float(source_candidates),
            "groups_per_game": groups_per_game,
            "candidates_per_group": candidates_per_group,
            "projected_source_games": float(full_games),
            "projected_groups": projected_groups,
            "projected_candidates": projected_candidates,
            "determinizations": float(determinizations),
            "projected_rollouts": projected_rollouts,
        }
    return projected


def _search_projection_input(config: CoverageConfig, search: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Attach measured shard elapsed time when reusing completed Pilot output."""

    result: dict[str, dict[str, Any]] = {}
    for stage, summary in search.items():
        elapsed = 0.0
        stage_dir = output_path(config, "search", stage)
        for path in stage_dir.glob("shard_*_summary.json"):
            elapsed += float(read_json(path).get("elapsed_seconds", 0.0))
        result[stage] = {**summary, "elapsed_seconds": elapsed}
    return result


def _pilot_projection(config: CoverageConfig, source: Mapping[str, Any], search: Mapping[str, Any], model: Mapping[str, Any]) -> dict[str, Any]:
    groups = sum(int(item.get("groups", 0)) for item in search.values())
    candidates = sum(int(item.get("candidates", 0)) for item in search.values())
    rollouts = sum(int(item.get("rollouts", 0)) for item in search.values())
    elapsed = sum(
        float(stage.get("elapsed_seconds", 0.0))
        if not stage.get("shards")
        else sum(float(item.get("elapsed_seconds", 0.0)) for item in stage.get("shards", ()))
        for stage in search.values()
    )
    rollouts_per_second = rollouts / elapsed if elapsed > 0 else 0.0
    source_stats = _pilot_source_split_stats(config, source)
    split_projection = project_split_stats(config, source_stats)
    source_games = sum(int(row["source_games"]) for row in source_stats.values())
    full_groups = sum(float(row["projected_groups"]) for row in split_projection.values())
    full_candidates = sum(float(row["projected_candidates"]) for row in split_projection.values())
    full_rollouts = sum(float(row["projected_rollouts"]) for row in split_projection.values())
    projected_hours = full_rollouts / (rollouts_per_second * config.worker_count * 3600.0) if rollouts_per_second > 0 else float("inf")
    pilot_root = config.output_dir
    search_root = output_path(config, "search")
    output_bytes = sum(path.stat().st_size for path in search_root.rglob("*") if path.is_file())
    disk = shutil.disk_usage(pilot_root.anchor or str(pilot_root))
    free_bytes = int(disk.free)
    source_errors = list(source.get("errors", ()))
    search_error_count = sum(int(item.get("error_count", 0)) for stage in search.values() for item in stage.get("shards", ()))
    gate = {
        "source_games": source_games,
        "pilot_source_branch_groups": sum(int(row["source_branch_groups"]) for row in source_stats.values()),
        "pilot_source_candidates": sum(int(row["source_candidates"]) for row in source_stats.values()),
        "training_groups": int(search.get("train_m05", {}).get("groups", 0)),
        "calibration_groups": int(search.get("calibration", {}).get("groups", 0)),
        "offline_test_groups": int(search.get("offline_test", {}).get("groups", 0)),
        "source_clean": int(source.get("clean", 0)),
        "source_action_error": int(source.get("action_error", 0)),
        "source_max_step": int(source.get("max_step", 0)),
        "search_error": search_error_count,
        "duplicate_group": 0,
        "prefix_mismatch": 0,
        "hidden_mismatch": 0,
        "model_success": bool(model.get("success")),
        "rollouts": rollouts,
        "rollouts_per_second": rollouts_per_second,
        "projected_full_source_groups": full_groups,
        "projected_full_candidate_count": full_candidates,
        "projected_full_search_rollouts": full_rollouts,
        "projected_training_rollouts": float(split_projection["training"]["projected_rollouts"]),
        "projected_calibration_rollouts": float(split_projection["calibration"]["projected_rollouts"]),
        "projected_offline_test_rollouts": float(split_projection["offline_test"]["projected_rollouts"]),
        "split_projection": split_projection,
        "pilot_search_output_bytes": int(output_bytes),
        "bytes_per_rollout": output_bytes / rollouts if rollouts else 0.0,
        "projected_search_hours_6_workers": projected_hours,
        "projected_output_bytes": int((output_bytes / rollouts) * full_rollouts) if rollouts else 0,
        "free_disk_bytes": free_bytes,
    }
    gate["technical_gate_passed"] = bool(
        source_games == 96
        and gate["training_groups"] >= 96
        and gate["calibration_groups"] >= 32
        and gate["offline_test_groups"] >= 32
        and gate["source_clean"] == 96
        and gate["source_action_error"] == 0
        and gate["source_max_step"] == 0
        and search_error_count == 0
        and gate["model_success"]
        and output_bytes > 0
        and projected_hours <= config.maximum_projected_search_hours
        and free_bytes >= gate["projected_output_bytes"] * 1.5 + 10 * 1024 ** 3
        and not source_errors
    )
    return gate


def recalculate_pilot_projection(config: CoverageConfig) -> dict[str, Any]:
    """Recompute only the projection from completed Pilot artifacts."""

    pilot_config = config.with_output_root(PILOT_OUTPUT_ROOT)
    summary_path = output_path(pilot_config, "pilot_summary.json")
    summary = read_json(summary_path)
    projection_input = _search_projection_input(pilot_config, summary["search"])
    gate = _pilot_projection(
        pilot_config,
        read_json(output_path(pilot_config, "source", "source_summary.json")),
        projection_input,
        summary["model"],
    )
    summary["projection"] = gate
    write_json(summary_path, summary)
    return gate


def run_pilot(config: CoverageConfig) -> dict[str, Any]:
    pilot_config = config.with_output_root(PILOT_OUTPUT_ROOT)
    if not pilot_config.output_dir.exists() or not any(pilot_config.output_dir.iterdir()):
        ensure_output(pilot_config)
    supervisor = Supervisor(pilot_config)
    source = supervisor.run_stage("source", lambda: collect_source(pilot_config, pilot=True))
    plan = supervisor.run_stage("build_plan", lambda: build_plan(pilot_config, pilot=True))
    search: dict[str, Any] = {}
    for stage in ("calibration", "offline_test", "train_m05", "train_m10_increment", "train_m20_increment"):
        search[stage] = supervisor.run_stage(stage, lambda stage=stage: _stage_search(pilot_config, stage))
    merged = supervisor.run_stage("merge", lambda: merge_all(pilot_config, shard_count=pilot_config.worker_count))
    datasets = supervisor.run_stage("datasets", lambda: build_datasets(pilot_config))
    model = supervisor.run_stage("model", lambda: pilot_optimizer_steps(pilot_config))
    projection_input = {
        stage: {**summary, "elapsed_seconds": sum(float(item.get("elapsed_seconds", 0.0)) for item in search.get(stage, {}).get("shards", ())) }
        for stage, summary in merged.items()
    }
    gate = _pilot_projection(pilot_config, source, projection_input, model)
    write_json(output_path(pilot_config, "pilot_summary.json"), {"schema_version": "archaludon-search-q-pilot-summary-v1", "source": source, "plan": plan, "search": merged, "datasets": datasets, "model": model, "projection": gate})
    supervisor.marker("complete", gate)
    supervisor.status(stage="complete", last_successful_stage="complete", technical_gate_passed=bool(gate["technical_gate_passed"]))
    if not gate["technical_gate_passed"]:
        raise RuntimeError("Pilot technical gate failed")
    return gate


def _run_full_stages(config: CoverageConfig, supervisor: Supervisor, start_stage: str) -> dict[str, Any]:
    actions: dict[str, Callable[[], Any]] = {
        "source": lambda: collect_source(config),
        "build_plan": lambda: build_plan(config),
        "calibration": lambda: _stage_search(config, "calibration"),
        "offline_test": lambda: _stage_search(config, "offline_test"),
        "train_m05": lambda: _stage_search(config, "train_m05"),
        "train_m10_increment": lambda: _stage_search(config, "train_m10_increment"),
        "train_m20_increment": lambda: _stage_search(config, "train_m20_increment"),
        "merge": lambda: merge_all(config, shard_count=config.worker_count),
        "datasets": lambda: build_datasets(config),
        "train": lambda: train(config),
        "calibrate": lambda: calibrate(config),
        "offline_test_final": lambda: offline_test(config),
    }
    start_index = FULL_STAGES.index(start_stage)
    for stage in FULL_STAGES[start_index:]:
        supervisor.run_stage(stage, actions[stage])
    return {"status": "complete", "note": "final evaluation is a separately gated stage"}


def _resume_supervisor(config: CoverageConfig, state: ResumeState) -> dict[str, Any]:
    supervisor = Supervisor(config)
    supervisor.status(
        stage=state.next_stage,
        error=None,
        last_successful_stage=state.completed_stages[-1] if state.completed_stages else None,
        worker_pids=[],
        worker_exit_codes={},
        completed_shards=[],
        total_shards=config.worker_count,
    )
    return _run_full_stages(config, supervisor, state.next_stage)


def run_supervisor(config: CoverageConfig, *, resume: bool = False) -> dict[str, Any]:
    if resume:
        return _resume_supervisor(config, _validate_resume_root(config))
    if config.output_dir.exists() and any(config.output_dir.iterdir()):
        raise FileExistsError(f"full output exists and is non-empty: {config.output_dir}")
    ensure_output(config)
    supervisor = Supervisor(config)
    return _run_full_stages(config, supervisor, FULL_STAGES[0])


def run_full(config: CoverageConfig) -> dict[str, Any]:
    """Backward-compatible fresh Full-run entry point."""

    return run_supervisor(config, resume=False)


__all__ = [
    "FULL_STAGES",
    "ResumeState",
    "Supervisor",
    "_validate_resume_root",
    "project_split_stats",
    "recalculate_pilot_projection",
    "run_full",
    "run_pilot",
    "run_supervisor",
]
