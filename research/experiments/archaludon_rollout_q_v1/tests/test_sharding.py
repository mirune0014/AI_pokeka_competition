from __future__ import annotations

import hashlib

from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_runner import _assigned
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import BranchTask


def _task(seed: int, candidate_index: int = 0) -> BranchTask:
    group = hashlib.sha256(f'group-{seed}'.encode('utf-8')).hexdigest()
    return BranchTask.create(
        source_episode_id=f'round_00_episode_{seed}',
        opponent_id='opponent',
        seat=seed % 2,
        seed=seed,
        branch_step_index=seed,
        candidate_index=candidate_index,
        candidate_action=(candidate_index,),
        candidate_identity=f'identity-{seed}-{candidate_index}',
        baseline_candidate_index=0,
        baseline_action=(0,),
        branch_group=group,
        public_state={},
        candidates=(
            {'candidate_index': 0, 'action': [0], 'canonical_identity': f'identity-{seed}-0'},
            {'candidate_index': 1, 'action': [1], 'canonical_identity': f'identity-{seed}-1'},
        ),
    )


def test_every_task_maps_to_exactly_one_shard_and_is_stable():
    tasks = [_task(seed) for seed in range(30)]
    for task in tasks:
        assigned = [_assigned(task, 7, index) for index in range(7)]
        assert sum(assigned) == 1
        assert assigned == [_assigned(task, 7, index) for index in range(7)]


def test_all_candidates_in_one_group_map_to_one_shard():
    baseline = _task(99, 0)
    alternative = _task(99, 1)
    assert baseline.branch_group_id == alternative.branch_group_id
    assert [_assigned(baseline, 11, index) for index in range(11)] == [
        _assigned(alternative, 11, index) for index in range(11)
    ]
