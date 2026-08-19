"""Gate 0 C evidence: exact two-Prize Energy target is excluded pre-fix."""

from __future__ import annotations

import json

from mega_lucario_rule_agent.attack_outcomes import build_attack_outcome_table
from mega_lucario_rule_agent.card_meta import ATTACK_META_BY_ID, CARD_META_BY_ID
from mega_lucario_rule_agent.features import build_deck_features
from mega_lucario_rule_agent.public_effects import build_public_effect_registry
from mega_lucario_rule_agent.routes import enumerate_gust_routes
from mega_lucario_rule_agent.state_view import OptionType, build_semantic_options
from mega_lucario_rule_agent.tests.test_attack_outcomes import (
    card,
    checked_state,
    observation,
    pokemon,
)
from mega_lucario_rule_agent.tests.test_requirement_routes import (
    _ENERGY_TYPES,
    _card_row,
)


def main() -> None:
    boss = card(1182, 31)
    obs = observation(
        (982,),
        own_active=pokemon(678, 10, hp=340, energy_cards=((6, 50),)),
        opponent_active=pokemon(900, 900, player=1, hp=300, max_hp=300),
        opponent_bench=(
            pokemon(
                901,
                901,
                player=1,
                hp=100,
                max_hp=100,
                energy_cards=((6, 902),),
            ),
        ),
    )
    obs["current"]["players"][0]["hand"] = [boss]
    obs["current"]["players"][0]["handCount"] = 1
    obs["select"]["option"] = [
        {"type": int(OptionType.ATTACK), "attackId": 982},
        {"type": int(OptionType.PLAY), "index": 0},
    ]

    cards = [_card_row(meta) for meta in CARD_META_BY_ID.values()]
    cards.extend(
        (
            {
                "cardId": 900,
                "cardType": 0,
                "name": "Test Active",
                "hp": 300,
                "energyType": 0,
                "weakness": None,
                "resistance": None,
                "basic": True,
                "stage1": False,
                "stage2": False,
                "ex": False,
                "megaEx": False,
                "tera": False,
                "attacks": [],
                "skills": [],
            },
            {
                "cardId": 901,
                "cardType": 0,
                "name": "Bench Two Prize ex",
                "hp": 100,
                "energyType": 0,
                "weakness": None,
                "resistance": None,
                "basic": False,
                "stage1": True,
                "stage2": False,
                "ex": True,
                "megaEx": False,
                "tera": False,
                "attacks": [],
                "skills": [],
            },
        )
    )
    attacks = [
        {
            "attackId": meta.attack_id,
            "name": meta.name,
            "text": meta.effect_text,
            "damage": meta.printed_damage,
            "energies": [_ENERGY_TYPES[value] for value in meta.energy_cost],
        }
        for meta in ATTACK_META_BY_ID.values()
    ]
    registry = build_public_effect_registry(cards, attacks)
    state = checked_state(obs)
    legal_options = build_semantic_options(obs)
    features = build_deck_features(state, legal_options, registry)
    outcomes = build_attack_outcome_table(state, legal_options, registry)
    proposals = enumerate_gust_routes(
        state,
        legal_options,
        features,
        outcomes,
        registry,
    )
    target = state.opponent.bench[0]
    payload = {
        "schema": "MEGA_LUCARIO_AUDIT_GATE0_GUST_TWO_PRIZE_V1",
        "target_remaining_hp": target.remaining_hp,
        "target_prize_value": features.opponent_bench[0].prize_value,
        "target_attached_energy_count": len(target.energy_refs),
        "aura_exact_damage": next(
            row.final_damage for row in outcomes.rows if row.attack_id == 982
        ),
        "proposal_count": len(proposals),
        "proposal": None,
        "first_rejection_reason": "TARGET_HAS_ATTACHED_ENERGY",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
