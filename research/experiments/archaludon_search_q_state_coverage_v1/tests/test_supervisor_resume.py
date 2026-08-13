from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.config import load_config
from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.supervisor import (
    FULL_STAGES,
    Supervisor,
    _validate_resume_root,
    project_split_stats,
    run_supervisor,
)


def _resume_root(tmp_path: Path, *, current_stage: str = "calibration", last_successful_stage: str | None = "build_plan"):
    root = tmp_path / "full"
    (root / "stage_markers").mkdir(parents=True)
    status = {
        "current_stage": current_stage,
        "started_at": "2026-08-12T02:52:11.918990+00:00",
        "updated_at": "2026-08-12T06:18:43.006430+00:00",
        "worker_pids": [],
        "worker_exit_codes": {},
        "completed_shards": [],
        "total_shards": 6,
        "error": None,
        "last_successful_stage": last_successful_stage,
    }
    (root / "supervisor_status.json").write_text(json.dumps(status), encoding="utf-8")
    for stage in ("source", "build_plan"):
        (root / "stage_markers" / f"{stage}.complete.json").write_text(
            json.dumps({"stage": stage, "completed_at": "2026-08-12T00:00:00+00:00", "payload": {}}),
            encoding="utf-8",
        )
    return root


def test_completed_stage_is_skipped_and_duplicate_marker_is_rejected(tmp_path) -> None:
    config = replace(load_config(), output_root=str(tmp_path))
    config.output_dir.mkdir(parents=True, exist_ok=True)
    supervisor = Supervisor(config)
    calls = []
    assert supervisor.run_stage("synthetic", lambda: calls.append(1) or {"ok": True}) == {"ok": True}
    assert supervisor.run_stage("synthetic", lambda: calls.append(2) or {"ok": False}) == {"ok": True}
    assert calls == [1]
    with pytest.raises(RuntimeError, match="duplicate completion marker"):
        supervisor.marker("synthetic", {"again": True})


def test_projection_uses_split_specific_determinizations() -> None:
    config = load_config()
    projected = project_split_stats(
        config,
        {
            "training": {"source_games": 64, "source_branch_groups": 497, "source_candidates": 2953},
            "calibration": {"source_games": 16, "source_branch_groups": 128, "source_candidates": 818},
            "offline_test": {"source_games": 16, "source_branch_groups": 126, "source_candidates": 762},
        },
    )

    assert projected["training"]["determinizations"] == 4.0
    assert projected["calibration"]["determinizations"] == 16.0
    assert projected["offline_test"]["determinizations"] == 16.0
    assert projected["training"]["projected_rollouts"] == pytest.approx(3322125.0)
    assert projected["calibration"]["projected_rollouts"] == pytest.approx(818000.0)
    assert projected["offline_test"]["projected_rollouts"] == pytest.approx(762000.0)
    assert sum(row["projected_rollouts"] for row in projected.values()) == pytest.approx(4902125.0)


def test_launcher_logs_are_outside_full_output_root() -> None:
    script = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "start_supervisor.ps1"
    ).read_text(encoding="utf-8")

    assert "archaludon_search_q_state_coverage_v1_launcher_logs" in script
    assert "$stdoutPath = Join-Path $launcherLogRoot" in script
    assert "$stderrPath = Join-Path $launcherLogRoot" in script
    assert "-RedirectStandardOutput $stdoutPath" in script
    assert "-RedirectStandardError $stderrPath" in script
    assert "supervisor.stdout.log" not in script
    assert "supervisor.stderr.log" not in script


def test_fresh_supervisor_rejects_nonempty_output(tmp_path) -> None:
    config = replace(load_config(), output_root=str(tmp_path / "full"))
    config.output_dir.mkdir(parents=True)
    (config.output_dir / "preserve.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError, match="output already exists and is not empty"):
        run_supervisor(config, resume=False)


def test_resume_requires_output_root_and_status(tmp_path) -> None:
    config = replace(load_config(), output_root=str(tmp_path / "full"))
    with pytest.raises(FileNotFoundError, match="output root is missing"):
        run_supervisor(config, resume=True)
    config.output_dir.mkdir(parents=True)
    (config.output_dir / "stage_markers").mkdir()
    with pytest.raises(FileNotFoundError, match="status file is missing"):
        run_supervisor(config, resume=True)


def test_valid_calibration_resume_finds_contiguous_prefix(tmp_path) -> None:
    root = _resume_root(tmp_path)
    config = replace(load_config(), output_root=str(root))
    state = _validate_resume_root(config)
    assert state.completed_stages == ("source", "build_plan")
    assert state.next_stage == "calibration"


def test_resume_rejects_noncontiguous_markers(tmp_path) -> None:
    root = _resume_root(tmp_path, last_successful_stage="source")
    (root / "stage_markers" / "build_plan.complete.json").unlink()
    (root / "stage_markers" / "calibration.complete.json").write_text(
        json.dumps({"stage": "calibration", "payload": {}}), encoding="utf-8"
    )
    config = replace(load_config(), output_root=str(root))
    with pytest.raises(ValueError, match="non-contiguous"):
        _validate_resume_root(config)


@pytest.mark.parametrize("stage", ["blocked", "complete"])
def test_resume_rejects_blocked_or_complete_status(tmp_path, stage: str) -> None:
    root = _resume_root(tmp_path, current_stage=stage)
    config = replace(load_config(), output_root=str(root))
    with pytest.raises(ValueError, match="unknown resume current_stage"):
        _validate_resume_root(config)


def test_resume_rejects_current_stage_mismatch(tmp_path) -> None:
    root = _resume_root(tmp_path, current_stage="offline_test")
    config = replace(load_config(), output_root=str(root))
    with pytest.raises(ValueError, match="current_stage mismatch"):
        _validate_resume_root(config)


def test_resume_rejects_bad_completed_marker_payload(tmp_path) -> None:
    root = _resume_root(tmp_path)
    (root / "stage_markers" / "build_plan.complete.json").write_text(
        json.dumps({"stage": "build_plan", "payload": {"error_count": 1}}), encoding="utf-8"
    )
    config = replace(load_config(), output_root=str(root))
    with pytest.raises(ValueError, match="unsafe build_plan completion marker"):
        _validate_resume_root(config)


def test_resume_switch_and_git_root_resolution_are_wired() -> None:
    script_dir = Path(__file__).resolve().parents[1] / "scripts"
    launcher = (script_dir / "start_supervisor.ps1").read_text(encoding="utf-8")
    status = (script_dir / "status.ps1").read_text(encoding="utf-8")
    assert "[switch]$Resume" in launcher
    assert '$arguments += "--resume"' in launcher
    assert "if ($Resume)" in launcher
    assert "git -C $scriptDirectory rev-parse --show-toplevel" in status
