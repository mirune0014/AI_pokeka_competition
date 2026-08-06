from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_runner import (
    ContinuationUnsafe,
    PrefixReplayMismatch,
    run_branch_group,
)
from research.experiments.archaludon_rollout_q_v1.rollout_q.agent_loader import load_baseline
from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_task_builder import tasks_for_trace
from research.experiments.archaludon_rollout_q_v1.rollout_q.config import load_spec, round_dir
from research.experiments.archaludon_rollout_q_v1.rollout_q.source_collector import (
    _collect_one,
    _load_engine,
    _opponent_rows,
    resolve_opponent_dir,
)
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import write_record


def test_identity_failure_types_are_distinct():
    assert issubclass(ContinuationUnsafe, RuntimeError)
    assert issubclass(PrefixReplayMismatch, RuntimeError)


def test_formal_policy_parent_modules_are_independent():
    config = load_spec()
    _load_engine()
    first = load_baseline(config.baseline_dir, 'parent_identity_first')
    second = load_baseline(config.baseline_dir, 'parent_identity_second')
    assert first.parent_module is not None
    assert second.parent_module is not None
    assert first.parent_module is not second.parent_module


def test_real_branch_group_baseline_matches_source_trace(tmp_path: Path):
    base_config = load_spec()
    config = replace(base_config, output_root=str(tmp_path))
    row = _opponent_rows()[0]
    trace = _collect_one(
        config=config,
        round_index=0,
        opponent_id=str(row['id']),
        opponent_dir=resolve_opponent_dir(row, config),
        seat=0,
        seed=910000456,
        engine=_load_engine(),
        max_steps=config.worker_max_steps,
    )
    assert trace.clean_terminal and trace.branch_points
    trace_path = round_dir(config, 0) / 'source_traces' / f'{trace.episode_id}.json'
    write_record(trace_path, trace.to_dict())
    tasks = tasks_for_trace(trace)
    group = [task for task in tasks if task.branch_group_id == trace.branch_points[0].branch_group_id]
    baseline = [task for task in group if task.candidate_index == task.baseline_candidate_index]
    assert len(baseline) == 1
    results = run_branch_group(config, baseline)
    assert len(results) == 1
    assert results[0].status == 'OK'
    assert results[0].clean_terminal
    assert results[0].is_baseline_candidate


def test_identity_mismatch_can_be_marked_unsafe():
    result = {'status': 'CONTINUATION_UNSAFE'}
    assert result['status'] == 'CONTINUATION_UNSAFE'
