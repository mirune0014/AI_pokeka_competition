from __future__ import annotations

from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.config import load_config
from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.schedule import all_plans, cell_counts, plans_for_split


def test_fixed_schedule_counts_seeds_and_nested_milestones() -> None:
    config = load_config()
    assert len(plans_for_split(config, "training")) == 18000
    assert len(plans_for_split(config, "calibration")) == 1000
    assert len(plans_for_split(config, "offline_test")) == 1000
    assert cell_counts(18000) == (1125,) * 16
    assert cell_counts(1000) == (63,) * 8 + (62,) * 8
    assert cell_counts(1000, remainder_first=False) == (62,) * 8 + (63,) * 8
    plans = all_plans(config)
    assert len({plan.seed for plan in plans}) == len(plans)
    assert len({plan.episode_id for plan in plans}) == len(plans)
    training = plans_for_split(config, "training")
    assert sum("m05" in plan.training_milestones for plan in training) == 4500
    assert sum("m10" in plan.training_milestones for plan in training) == 9000
    assert sum("m20" in plan.training_milestones for plan in training) == 18000
    for plan in training:
        assert set(plan.training_milestones) in ({"m05", "m10", "m20"}, {"m10", "m20"}, {"m20"})
