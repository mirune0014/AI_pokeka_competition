from __future__ import annotations

from research.experiments.archaludon_rollout_q_v1.rollout_q.complete_action import enumerate_complete_actions


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
