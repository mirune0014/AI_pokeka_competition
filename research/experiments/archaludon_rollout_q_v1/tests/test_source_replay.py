from __future__ import annotations

from research.experiments.archaludon_rollout_q_v1.rollout_q.source_collector import trace_observation_hash


def test_same_public_observation_hash_ignores_engine_search_scratch():
    first = {'current': {'turn': 1}, 'select': {'context': 0}, 'search_begin_input': 'first-buffer'}
    second = {'current': {'turn': 1}, 'select': {'context': 0}, 'search_begin_input': 'second-buffer'}
    assert trace_observation_hash(first) == trace_observation_hash(second)


def test_action_prefix_record_is_plain_tuple():
    assert tuple([0, 2]) == (0, 2)
