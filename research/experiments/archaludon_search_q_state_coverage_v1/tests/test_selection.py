from __future__ import annotations

from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.calibrate import select_candidate
from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.final_evaluate import mcnemar_p_value


def test_selection_tie_breaking_and_mcnemar() -> None:
    rows = [
        {"milestone": "m05", "threshold": 0.02, "override_episodes": 100, "actual_mean_delta_total": 2.0, "positive_episode": 60, "negative_episode": 40, "lcb90_positive": 10, "ucb90_negative": 2},
        {"milestone": "m10", "threshold": 0.20, "override_episodes": 100, "actual_mean_delta_total": 2.0, "positive_episode": 65, "negative_episode": 35, "lcb90_positive": 12, "ucb90_negative": 2},
    ]
    assert select_candidate(rows)["milestone"] == "m10"
    assert mcnemar_p_value(0, 0) == 1.0
    assert 0.0 <= mcnemar_p_value(3, 1) <= 1.0
