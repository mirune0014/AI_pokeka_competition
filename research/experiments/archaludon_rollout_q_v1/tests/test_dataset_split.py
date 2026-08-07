from __future__ import annotations

from research.experiments.archaludon_rollout_q_v1.rollout_q import override_policy, source_collector
from research.experiments.archaludon_rollout_q_v1.rollout_q import dataset as dataset_module
from research.experiments.archaludon_rollout_q_v1.rollout_q.dataset import complete_action_feature, episode_split
from research.experiments.archaludon_rollout_q_v1.rollout_q.config import load_spec
from research.experiments.archaludon_rollout_q_v1.rollout_q.source_collector import _collect_one, _load_engine, _opponent_rows, resolve_opponent_dir
from research.experiments.archaludon_rollout_q_v1.rollout_q.trace_schema import BranchPoint, BranchResult, BranchTask, SourceTrace


def test_episode_split_is_deterministic_and_exclusive():
    values = [episode_split(f'episode-{index}') for index in range(100)]
    assert set(values) <= {'training', 'validation'}
    assert [episode_split('episode-7')] * 2 == ['training' if episode_split('episode-7') == 'training' else 'validation'] * 2


def test_complete_action_set_pooling_has_fixed_width():
    vectors = [[1.0, 2.0], [3.0, 4.0]]
    feature = complete_action_feature(vectors, (0, 1))
    assert feature == [4.0, 6.0, 2.0, 3.0, 3.0, 4.0, 2 / 6]


def test_source_saved_state_matches_override_encoding_on_same_raw_observation(monkeypatch):
    config = load_spec()
    original = source_collector.encode_observation
    captures = {}

    def capture(observation):
        encoded = original(observation)
        override_encoded = override_policy.encode_observation(observation)
        key = source_collector.trace_observation_hash(observation)
        captures[key] = (
            tuple(float(value) for value in encoded.state_vector),
            tuple(tuple(float(value) for value in row) for row in encoded.option_vectors),
            tuple(float(value) for value in override_encoded.state_vector),
        )
        return encoded

    monkeypatch.setattr(source_collector, 'encode_observation', capture)
    row = _opponent_rows()[0]
    trace = _collect_one(
        config=config,
        round_index=0,
        opponent_id=str(row['id']),
        opponent_dir=resolve_opponent_dir(row, config),
        seat=0,
        seed=910000789,
        engine=_load_engine(),
        max_steps=config.worker_max_steps,
    )
    assert trace.branch_points
    for point in trace.branch_points:
        state, options, override_state = captures[point.raw_observation_sha256]
        assert point.state_vector == state == override_state
        assert point.option_vectors == options


def test_equal_reward_alternative_is_retained_with_unweighted_label(monkeypatch):
    point = BranchPoint(
        branch_group_id='group-1',
        step_index=3,
        raw_observation_sha256='observation-1',
        public_state={'select': {'context': 0}},
        baseline_action=(0,),
        baseline_candidate_index=0,
        candidates=(
            {'candidate_index': 0, 'action': [0], 'canonical_identity': 'baseline', 'selected_options': []},
            {'candidate_index': 1, 'action': [1], 'canonical_identity': 'alternative', 'selected_options': []},
        ),
        state_vector=(1.0, 2.0, 3.0),
        option_vectors=((1.0, 0.0), (0.0, 1.0)),
    )
    trace = SourceTrace(
        episode_id='round_00_episode_seat0_seed1',
        opponent_id='opponent',
        seat=0,
        seed=1,
        terminal_result=0,
        terminal_reward=1.0,
        clean_terminal=True,
        steps=(),
        branch_points=(point,),
    )
    tasks = [
        BranchTask.create(
            source_episode_id=trace.episode_id,
            opponent_id=trace.opponent_id,
            seat=trace.seat,
            seed=trace.seed,
            branch_step_index=point.step_index,
            candidate_index=index,
            candidate_action=point.candidates[index]['action'],
            candidate_identity=point.candidates[index]['canonical_identity'],
            baseline_candidate_index=0,
            baseline_action=point.baseline_action,
            branch_group=point.branch_group_id,
            public_state=point.public_state,
            candidates=point.candidates,
        )
        for index in (0, 1)
    ]
    results = [
        BranchResult(task_id=tasks[0].task_id, branch_group_id='group-1', candidate_index=0, candidate_identity='baseline', is_baseline_candidate=True, status='OK', terminal_result=0, reward=1.0, engine_steps=1, clean_terminal=True, action_errors=0, max_step_hit=False),
        BranchResult(task_id=tasks[1].task_id, branch_group_id='group-1', candidate_index=1, candidate_identity='alternative', is_baseline_candidate=False, status='OK', terminal_result=0, reward=1.0, engine_steps=1, clean_terminal=True, action_errors=0, max_step_hit=False),
    ]
    monkeypatch.setattr(dataset_module, '_load_round_data', lambda config, round_index: ({task.task_id: task for task in tasks}, {trace.episode_id: trace}, results))
    rows = dataset_module._rows_for_round(load_spec(), 0)
    assert len(rows) == 1
    assert rows[0]['outcome_class'] == 'EQUAL'
    assert rows[0]['reward_delta'] == 0.0
    assert rows[0]['label'] == 0.0
    assert rows[0]['weight'] == 1.0
    assert rows[0]['state'] == [1.0, 2.0, 3.0]
