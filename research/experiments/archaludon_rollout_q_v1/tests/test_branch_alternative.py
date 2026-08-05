from __future__ import annotations

from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_runner import _EpisodeReplay, _result_from_replay
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import BranchTask


def _task() -> BranchTask:
    return BranchTask.create(
        source_episode_id='round_00_test_seat0_seed1',
        opponent_id='test',
        seat=0,
        seed=1,
        branch_step_index=2,
        candidate_index=1,
        candidate_action=(1,),
        candidate_identity='candidate',
        baseline_candidate_index=0,
        baseline_action=(0,),
        branch_group='group',
        public_state={},
        candidates=(
            {'candidate_index': 0, 'action': [0], 'canonical_identity': 'baseline'},
            {'candidate_index': 1, 'action': [1], 'canonical_identity': 'candidate'},
        ),
    )


def test_alternative_result_is_clean_and_not_baseline():
    result = _result_from_replay(
        _task(),
        _EpisodeReplay(0, -1.0, 10, 0, False, True, [(0,), (1,)]),
    )
    assert result.status == 'OK'
    assert result.is_baseline_candidate is False
    assert result.reward == -1.0
