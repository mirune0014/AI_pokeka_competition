from __future__ import annotations

from dataclasses import replace

import pytest

from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.config import load_config
from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.supervisor import Supervisor, project_split_stats


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
