from __future__ import annotations

import torch

from research.experiments.archaludon_multideterminization_q_v1.multidet_q.semantic_encoder import SemanticVocab
from research.experiments.archaludon_search_q_state_coverage_v1.coverage_q.model_bridge import assert_model_structure_equal, build_model, parameter_count, parameter_signature


def _state() -> dict:
    return {"turn": 1, "turn_action_count": 0, "first_player_relative": 0, "supporter_played": False, "stadium_played": False, "energy_attached": False, "retreated": False, "stadium": [], "players": [{"deck_count": 50, "hand_count": 1, "prize_count": 6, "bench": [], "active": [], "discard": [], "status": {}}, {"deck_count": 50, "hand_count": 1, "prize_count": 6, "bench": [], "active": [], "discard": [], "status": {}}], "select": {"type": 0, "context": 0, "min_count": 1, "max_count": 1, "remain_damage_counter": 0, "remain_energy_cost": 0, "option_count": 1}}


def test_adapter_has_identical_parameter_signature_and_variable_candidates_forward() -> None:
    vocab = SemanticVocab(max_card_id=10, max_attack_id=10)
    left = build_model(vocab)
    right = build_model(vocab)
    assert parameter_signature(left) == parameter_signature(right)
    assert parameter_count(left) == parameter_count(right)
    assert_model_structure_equal(left, right)
    rows = [{"selected_options": [], "order_sensitive": False}, {"selected_options": [], "order_sensitive": True}]
    scores = left.score_group({"public_state": _state(), "context": 0, "candidates": rows})
    assert scores.shape == (2,)
    loss = scores.sum()
    loss.backward()
    assert bool(torch.isfinite(loss))
    assert all(parameter.grad is None or bool(torch.isfinite(parameter.grad).all()) for parameter in left.parameters())
