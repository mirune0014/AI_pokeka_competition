from __future__ import annotations

from research.experiments.archaludon_rollout_q_v1.rollout_q.agent_loader import load_baseline, load_opponent
from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_runner import _player, _terminal
from research.experiments.archaludon_rollout_q_v1.rollout_q.config import load_spec
from research.experiments.archaludon_rollout_q_v1.rollout_q.source_collector import (
    _battle_start,
    _collect_one,
    _load_engine,
    _opponent_rows,
    resolve_opponent_dir,
    trace_observation_hash,
    _cell_counts,
)


def _replay_prefix(trace, config, prefix_length: int) -> list[str]:
    battle_start, battle_select, battle_finish, _ = _load_engine()
    baseline = load_baseline(config.baseline_dir, 'source_replay_baseline')
    row = _opponent_rows()[0]
    opponent = load_opponent(resolve_opponent_dir(row, config), str(row['id']))
    baseline.seed(trace.seed)
    opponent.seed(trace.seed)
    decks = (baseline.deck, opponent.deck) if trace.seat == 0 else (opponent.deck, baseline.deck)
    observation, start_data = _battle_start(battle_start, decks, trace.seed)
    assert observation, start_data
    hashes: list[str] = []
    try:
        for step in trace.steps[:prefix_length]:
            assert _terminal(observation) is None
            assert _player(observation) == step.current_player
            assert trace_observation_hash(observation) == step.raw_observation_sha256
            hashes.append(trace_observation_hash(observation))
            action = baseline(observation) if step.current_player == trace.seat else opponent(observation)
            assert tuple(action) == step.action
            observation = battle_select(list(step.action))
    finally:
        battle_finish()
    return hashes


def test_same_public_observation_hash_ignores_engine_search_scratch():
    first = {'current': {'turn': 1}, 'select': {'context': 0}, 'search_begin_input': 'first-buffer'}
    second = {'current': {'turn': 1}, 'select': {'context': 0}, 'search_begin_input': 'second-buffer'}
    assert trace_observation_hash(first) == trace_observation_hash(second)


def test_seeded_engine_replays_one_real_prefix_twice():
    config = load_spec()
    assert _cell_counts(32) == [2] * 16
    engine = _load_engine()
    row = _opponent_rows()[0]
    trace = _collect_one(
        config=config,
        round_index=0,
        opponent_id=str(row['id']),
        opponent_dir=resolve_opponent_dir(row, config),
        seat=0,
        seed=910000321,
        engine=engine,
        max_steps=config.worker_max_steps,
    )
    prefix_length = min(12, len(trace.steps))
    assert prefix_length > 0
    first = _replay_prefix(trace, config, prefix_length)
    second = _replay_prefix(trace, config, prefix_length)
    assert first == second


def test_action_prefix_record_is_plain_tuple():
    assert tuple([0, 2]) == (0, 2)
