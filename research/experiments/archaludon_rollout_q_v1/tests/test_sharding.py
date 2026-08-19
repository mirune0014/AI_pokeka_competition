from __future__ import annotations

import hashlib
import json
from pathlib import Path

from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_runner import _assigned, _load_and_repair_existing_results
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import BRANCH_RESULT_SCHEMA, BranchResult, BranchTask


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


def test_partial_group_and_truncated_final_line_are_repaired(tmp_path: Path):
    complete = [_task(100, 0), _task(100, 1)]
    partial = [_task(101, 0), _task(101, 1)]

    def result(task: BranchTask) -> BranchResult:
        return BranchResult(
            task_id=task.task_id,
            branch_group_id=task.branch_group_id,
            candidate_index=task.candidate_index,
            candidate_identity=task.candidate_identity,
            is_baseline_candidate=task.candidate_index == task.baseline_candidate_index,
            status='OK',
            terminal_result=0,
            reward=1.0,
            engine_steps=1,
            clean_terminal=True,
            action_errors=0,
            max_step_hit=False,
        )

    path = tmp_path / 'shard.jsonl'
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps({'schema_version': BRANCH_RESULT_SCHEMA, **result(complete[0]).to_dict()}))
        handle.write('\n')
        handle.write(json.dumps({'schema_version': BRANCH_RESULT_SCHEMA, **result(complete[1]).to_dict()}))
        handle.write('\n')
        handle.write(json.dumps({'schema_version': BRANCH_RESULT_SCHEMA, **result(partial[0]).to_dict()}))
        handle.write('\n')
        handle.write('{"schema_version":"truncated"')
    kept, completed, repaired, truncated = _load_and_repair_existing_results(
        path,
        {complete[0].branch_group_id: complete, partial[0].branch_group_id: partial},
    )
    assert {row.task_id for row in kept} == {task.task_id for task in complete}
    assert completed == {complete[0].branch_group_id}
    assert repaired == 1
    assert truncated == 1
    assert len(path.read_text(encoding='utf-8').splitlines()) == 2
