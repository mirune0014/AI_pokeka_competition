from __future__ import annotations

from research.experiments.archaludon_rollout_q_v1.rollout_q.agent_loader import load_baseline, load_opponent
from research.experiments.archaludon_rollout_q_v1.rollout_q.branch_runner import _player, _terminal
from research.experiments.archaludon_rollout_q_v1.rollout_q.complete_action import (
    enumerate_complete_actions,
    observation_complete_actions,
    observation_option_rows,
)
from research.experiments.archaludon_rollout_q_v1.rollout_q.config import load_spec
from research.experiments.archaludon_rollout_q_v1.rollout_q.source_collector import (
    _battle_start,
    _load_engine,
    _opponent_rows,
    resolve_opponent_dir,
)


def _option(index: int, option_type: int = 3) -> dict:
    return {
        'engine_index': index,
        'identity': f'option-{index}',
        'payload': {
            'option_type': option_type,
            'fields': {'index': index},
            'source_card_id': 100 + index,
            'target_card_id': None,
        },
        'execution_payload': {'engine_index': index, 'fields': {'index': index}},
    }


def test_main_complete_candidates_and_baseline_membership():
    options = [_option(0), _option(1)]
    candidates = enumerate_complete_actions(options, minimum=1, maximum=1, context=0)
    assert len(candidates.candidates) == 2
    assert candidates.candidate_index_for(options, (1,)) is not None
    assert candidates.candidates[1].selected_options[0]['execution_payload']['engine_index'] == 1


def test_live_main_candidates_contain_formal_baseline_action():
    config = load_spec()
    battle_start, battle_select, battle_finish, _ = _load_engine()
    baseline = load_baseline(config.baseline_dir, 'complete_action_test_baseline')
    opponent_row = _opponent_rows()[0]
    opponent = load_opponent(resolve_opponent_dir(opponent_row, config), str(opponent_row['id']))
    seed = 910000123
    baseline.seed(seed)
    opponent.seed(seed)
    decks = (baseline.deck, opponent.deck)
    observation, start_data = _battle_start(battle_start, decks, seed)
    assert observation, start_data
    try:
        for _ in range(config.worker_max_steps):
            if _terminal(observation) is not None:
                break
            select = observation.get('select')
            if not select:
                break
            if _player(observation) == 0:
                action = baseline(observation)
                context = int(select.get('context', -1))
                if context == 0:
                    candidates = observation_complete_actions(observation)
                    option_rows = observation_option_rows(observation)
                    assert candidates.candidate_index_for(option_rows, action) is not None
                    return
            else:
                action = opponent(observation)
            observation = battle_select(list(action))
    finally:
        battle_finish()
    raise AssertionError('no live MAIN decision was encountered')
