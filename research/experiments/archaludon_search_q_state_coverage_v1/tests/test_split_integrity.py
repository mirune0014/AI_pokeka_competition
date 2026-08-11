from __future__ import annotations

from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.config import load_config
from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.schedule import all_plans


def test_splits_are_disjoint_and_milestones_are_nested() -> None:
    config = load_config()
    plans = all_plans(config)
    by_episode = {plan.episode_id: plan for plan in plans}
    assert len(by_episode) == 20000
    assert {plan.split for plan in plans} == {"training", "calibration", "offline_test"}
    assert all((not plan.training_milestones) for plan in plans if plan.split != "training")
    training = [plan for plan in plans if plan.split == "training"]
    m05 = {plan.episode_id for plan in training if "m05" in plan.training_milestones}
    m10 = {plan.episode_id for plan in training if "m10" in plan.training_milestones}
    m20 = {plan.episode_id for plan in training if "m20" in plan.training_milestones}
    assert m05 < m10 < m20
    assert not ({plan.episode_id for plan in plans if plan.split == "calibration"} & {plan.episode_id for plan in plans if plan.split == "training"})
    assert not ({plan.episode_id for plan in plans if plan.split == "offline_test"} & {plan.episode_id for plan in plans if plan.split != "offline_test"})
