import torch

from research.experiments.archaludon_multideterminization_q_v1.multidet_q.semantic_encoder import SemanticEncoder, SemanticVocab


def _state():
    return {
        "turn": 3,
        "turn_action_count": 2,
        "first_player_relative": 0,
        "supporter_played": False,
        "stadium_played": False,
        "energy_attached": True,
        "retreated": False,
        "players": [
            {"deck_count": 40, "hand_count": 5, "prize_count": 6, "bench": [], "status": {name: False for name in ("poisoned", "burned", "asleep", "paralyzed", "confused")}, "hand": [{"id": 1}]},
            {"deck_count": 42, "hand_count": 7, "prize_count": 6, "bench": [], "status": {name: False for name in ("poisoned", "burned", "asleep", "paralyzed", "confused")}},
        ],
        "select": {"type": 0, "context": 0, "min_count": 1, "max_count": 1, "remain_damage_counter": 0, "remain_energy_cost": 0, "option_count": 2},
        "stadium": [],
        "looking_visible": [],
    }


def _candidate(serial):
    return {
        "canonical_identity": "candidate",
        "order_sensitive": False,
        "selected_options": [{
            "serial": serial,
            "semantic_payload": {"option_type": 13, "fields": {"attackId": 5, "index": 0}},
            "execution_payload": {"source_card_id": 1, "target_card_id": 2, "fields": {"attackId": 5, "index": 0}},
        }],
    }


def test_semantic_encoder_uses_embeddings_and_ignores_serial():
    torch.manual_seed(4)
    encoder = SemanticEncoder(SemanticVocab(max_card_id=20, max_attack_id=20))
    state_hidden = encoder.encode_state(_state())
    candidate_one = encoder.encode_candidate(_candidate(10), context=0)
    candidate_two = encoder.encode_candidate(_candidate(999), context=0)
    empty = encoder.encode_candidate({"selected_options": [], "order_sensitive": False}, context=0)
    assert state_hidden.shape == (256,)
    assert candidate_one.shape == (128,)
    assert torch.equal(candidate_one, candidate_two)
    assert empty.shape == (128,)
    assert torch.isfinite(state_hidden).all()
