import math

from research.experiments.archaludon_multideterminization_q_v1.multidet_q.worker import _candidate_stats
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import BranchTask


def _task(index):
    return BranchTask.create(
        source_episode_id="round_00_test_seat0_seed1",
        opponent_id="test",
        seat=0,
        seed=1,
        branch_step_index=1,
        candidate_index=index,
        candidate_action=[index],
        candidate_identity=str(index),
        baseline_candidate_index=0,
        baseline_action=[0],
        branch_group="0" * 64,
        public_state={"select": {"context": 0}},
        candidates=[{"candidate_index": index, "action": [index], "canonical_identity": str(index)}],
    )


def test_paired_delta_and_confidence_interval():
    row = _candidate_stats(_task(1), [1.0, -1.0, 1.0, 0.0], [0.0, -1.0, 0.0, 0.0], is_baseline=False, z_value=1.281551565545)
    assert row["rewards"] == [1.0, -1.0, 1.0, 0.0]
    assert row["paired_deltas"] == [1.0, 0.0, 1.0, 0.0]
    assert row["positive_delta_count"] == 2
    assert row["zero_delta_count"] == 2
    assert row["negative_delta_count"] == 0
    assert math.isclose(row["mean_delta"], 0.5)
    assert math.isclose(row["delta_lcb90"], row["mean_delta"] - 1.281551565545 * row["delta_standard_error"])
    assert math.isclose(row["delta_ucb90"], row["mean_delta"] + 1.281551565545 * row["delta_standard_error"])
