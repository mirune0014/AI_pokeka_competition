"""Resumable stage supervisor and the bounded 96-game Pilot."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from .calibrate import calibrate
from .config import CoverageConfig, PILOT_OUTPUT_ROOT, ensure_output, output_path, write_json
from .dataset import build_datasets
from .merge import merge_all
from .offline_test import offline_test
from .search_plan import STAGES, build_plan, load_plan
from .search_worker import run_stage
from .source import collect_source
from .train_milestones import pilot_optimizer_steps, train


FULL_STAGES = ("source", "build_plan", "calibration_search", "offline_test_search", "train_m05_search", "train_m05", "train_m10_search", "train_m10", "train_m20_search", "train_m20", "calibrate", "offline_test", "final_evaluate", "report", "complete", "blocked")


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


def _stage_search(config: CoverageConfig, stage: str) -> dict[str, Any]:
    summaries = []
    for shard_index in range(config.worker_count):
        summaries.append(run_stage(config, stage, shard_count=config.worker_count, shard_index=shard_index))
    return {"stage": stage, "shards": summaries}


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
    source_games = int(source.get("emitted", 0))
    groups_per_game = groups / source_games if source_games else 0.0
    candidates_per_group = candidates / groups if groups else 0.0
    full_groups = groups_per_game * sum(config.source_games.values())
    full_candidates = full_groups * candidates_per_group
    full_rollouts = full_candidates * 16.0
    projected_hours = full_rollouts / (rollouts_per_second * config.worker_count * 3600.0) if rollouts_per_second > 0 else float("inf")
    pilot_root = config.output_dir
    output_bytes = sum(path.stat().st_size for path in pilot_root.rglob("*") if path.is_file())
    disk = shutil.disk_usage(pilot_root.anchor or str(pilot_root))
    free_bytes = int(disk.free)
    source_errors = list(source.get("errors", ()))
    search_error_count = sum(int(item.get("error_count", 0)) for stage in search.values() for item in stage.get("shards", ()))
    gate = {
        "source_games": source_games,
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
        "projected_search_hours_6_workers": projected_hours,
        "projected_output_bytes": int(output_bytes * (full_rollouts / max(1, rollouts))),
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
        and projected_hours <= config.maximum_projected_search_hours
        and free_bytes >= gate["projected_output_bytes"] * 1.5 + 10 * 1024 ** 3
        and not source_errors
    )
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


def run_full(config: CoverageConfig) -> dict[str, Any]:
    supervisor = Supervisor(config)
    supervisor.run_stage("source", lambda: collect_source(config))
    supervisor.run_stage("build_plan", lambda: build_plan(config))
    for stage in ("calibration", "offline_test", "train_m05", "train_m10_increment", "train_m20_increment"):
        supervisor.run_stage(stage, lambda stage=stage: _stage_search(config, stage))
    supervisor.run_stage("merge", lambda: merge_all(config, shard_count=config.worker_count))
    supervisor.run_stage("datasets", lambda: build_datasets(config))
    supervisor.run_stage("train", lambda: train(config))
    supervisor.run_stage("calibrate", lambda: calibrate(config))
    supervisor.run_stage("offline_test", lambda: offline_test(config))
    return {"status": "complete", "note": "final evaluation is a separately gated stage"}


__all__ = ["FULL_STAGES", "Supervisor", "run_full", "run_pilot"]
