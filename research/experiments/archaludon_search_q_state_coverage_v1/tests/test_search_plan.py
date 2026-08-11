from __future__ import annotations

from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.search_plan import STAGES, group_shard


def test_stage_names_and_fixed_group_shard() -> None:
    assert STAGES == ("calibration", "offline_test", "train_m05", "train_m10_increment", "train_m20_increment")
    group_id = "0123456789abcdef" + "0" * 48
    assert group_shard(group_id, 6) == int(group_id[:16], 16) % 6
    assert group_shard(group_id, 6) == group_shard(group_id, 6)
