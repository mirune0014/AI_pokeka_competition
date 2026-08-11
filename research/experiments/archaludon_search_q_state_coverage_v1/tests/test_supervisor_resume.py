from __future__ import annotations

from dataclasses import replace

import pytest

from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.config import load_config
from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.supervisor import Supervisor


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
