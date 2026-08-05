from __future__ import annotations

from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_runner import _assigned
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import BranchTask


def _task(seed: int) -> BranchTask:
    return BranchTask.create(
        source_episode_id=f'round_00_episode_{seed}',
        opponent_id='opponent',
        seat=seed % 2,
        seed=seed,
        branch_step_index=seed,
        candidate_index=0,
        candidate_action=(0,),
        candidate_identity=f'identity-{seed}',
        baseline_candidate_index=0,
        baseline_action=(0,),
        branch_group=f'group-{seed}',
        public_state={},
        candidates=({'candidate_index': 0, 'action': [0], 'canonical_identity': f'identity-{seed}'},),
    )


def test_every_task_maps_to_exactly_one_shard_and_is_stable():
    tasks = [_task(seed) for seed in range(30)]
    for task in tasks:
        assigned = [_assigned(task, 7, index) for index in range(7)]
        assert sum(assigned) == 1
        assert assigned == [_assigned(task, 7, index) for index in range(7)]
