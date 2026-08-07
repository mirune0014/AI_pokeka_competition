from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import torch

from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_runner import _EpisodeReplay, _result_from_replay, run_branch_group
from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_task_builder import tasks_for_trace
from research.experiments.archaludon_rollout_q_v1.rollout_q.config import load_spec, round_dir
from research.experiments.archaludon_rollout_q_v1.rollout_q.override_policy import RoundPolicyResources
from research.experiments.archaludon_rollout_q_v1.rollout_q.source_collector import (
    _collect_one,
    _load_engine,
    _opponent_rows,
    resolve_opponent_dir,
)
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import write_record
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import BranchTask


def _synthetic_task() -> BranchTask:
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
        _synthetic_task(),
        _EpisodeReplay(0, -1.0, 10, 0, False, True, [(0,), (1,)]),
    )
    assert result.status == 'OK'
    assert result.is_baseline_candidate is False
    assert result.reward == -1.0


def test_real_alternative_candidate_reaches_clean_terminal(tmp_path: Path):
    base_config = load_spec()
    config = replace(base_config, output_root=str(tmp_path))
    row = _opponent_rows()[0]
    trace = _collect_one(
        config=config,
        round_index=0,
        opponent_id=str(row['id']),
        opponent_dir=resolve_opponent_dir(row, config),
        seat=0,
        seed=910000654,
        engine=_load_engine(),
        max_steps=config.worker_max_steps,
    )
    assert trace.clean_terminal and trace.branch_points
    trace_path = round_dir(config, 0) / 'source_traces' / f'{trace.episode_id}.json'
    write_record(trace_path, trace.to_dict())
    all_tasks = tasks_for_trace(trace)
    group = [task for task in all_tasks if task.branch_group_id == trace.branch_points[0].branch_group_id]
    baseline = next(task for task in group if task.candidate_index == task.baseline_candidate_index)
    alternative = next(task for task in group if task.candidate_index != task.baseline_candidate_index)
    results = run_branch_group(config, [baseline, alternative])
    by_index = {result.candidate_index: result for result in results}
    assert by_index[baseline.candidate_index].status == 'OK'
    assert by_index[alternative.candidate_index].status == 'OK'
    assert by_index[alternative.candidate_index].clean_terminal


def test_round1_forced_override_is_used_by_source_and_branch(tmp_path: Path):
    base_config = load_spec()
    config = replace(base_config, output_root=str(tmp_path), override_minimum_support=0)

    class ConstantPositiveModel(torch.nn.Module):
        def forward(self, state, candidate, baseline):
            return torch.full((candidate.shape[0],), 10.0, dtype=candidate.dtype)

    models = (ConstantPositiveModel(), ConstantPositiveModel(), ConstantPositiveModel())
    resources = RoundPolicyResources(checkpoint_round=0, models=models, support={})
    row = _opponent_rows()[0]
    trace = _collect_one(
        config=config,
        round_index=1,
        opponent_id=str(row['id']),
        opponent_dir=resolve_opponent_dir(row, config),
        seat=0,
        seed=910000987,
        engine=_load_engine(),
        max_steps=config.worker_max_steps,
        source_policy_factory=lambda baseline: resources.bind(baseline, config),
    )
    assert trace.clean_terminal and trace.branch_points
    assert trace.source_override_count > 0
    trace_path = round_dir(config, 1) / 'source_traces' / f'{trace.episode_id}.json'
    write_record(trace_path, trace.to_dict())
    all_tasks = tasks_for_trace(trace)
    group = [task for task in all_tasks if task.branch_group_id == trace.branch_points[0].branch_group_id]
    baseline = next(task for task in group if task.candidate_index == task.baseline_candidate_index)
    alternative = next(task for task in group if task.candidate_index != task.baseline_candidate_index)
    results = run_branch_group(config, [baseline, alternative], resources=resources)
    by_index = {result.candidate_index: result for result in results}
    assert by_index[baseline.candidate_index].status == 'OK'
    assert by_index[baseline.candidate_index].is_baseline_candidate
    assert by_index[alternative.candidate_index].status == 'OK'
    assert by_index[alternative.candidate_index].clean_terminal
    assert by_index[alternative.candidate_index].action_errors == 0
    assert not by_index[alternative.candidate_index].max_step_hit
