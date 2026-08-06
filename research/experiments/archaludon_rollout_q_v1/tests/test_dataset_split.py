from __future__ import annotations

from research.experiments.archaludon_rollout_q_v1.rollout_q import override_policy, source_collector
from research.experiments.archaludon_rollout_q_v1.rollout_q.dataset import complete_action_feature, episode_split
from research.experiments.archaludon_rollout_q_v1.rollout_q.config import load_spec
from research.experiments.archaludon_rollout_q_v1.rollout_q.source_collector import _collect_one, _load_engine, _opponent_rows, resolve_opponent_dir


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
