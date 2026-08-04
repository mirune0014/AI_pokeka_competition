from mega_lucario_rule_agent.attack_outcomes import build_attack_outcome_table
from mega_lucario_rule_agent.card_meta import (
    ATTACK_META_BY_ID,
    CARD_META_BY_ID,
    CardType,
    EnergyType,
)
from mega_lucario_rule_agent.features import build_deck_features
from mega_lucario_rule_agent.public_effects import build_public_effect_registry
from mega_lucario_rule_agent.routes import (
    enumerate_aura_continuity_routes,
    enumerate_evolution_routes,
    enumerate_fighting_gong_routes,
    enumerate_minimal_ppp_routes,
    enumerate_safe_draw_supporter_routes,
)
from mega_lucario_rule_agent.state_view import (
    AreaType,
    OptionType,
    build_semantic_options,
)
from mega_lucario_rule_agent.transactions import TransactionStage
from mega_lucario_rule_agent.tests.test_attack_outcomes import (
    card,
    checked_state,
    observation,
    pokemon,
)


_CARD_TYPES = {
    CardType.POKEMON: 0,
    CardType.ITEM: 1,
    CardType.TOOL: 2,
    CardType.SUPPORTER: 3,
    CardType.BASIC_ENERGY: 5,
}
_ENERGY_TYPES = {
    EnergyType.GRASS: 1,
    EnergyType.PSYCHIC: 3,
    EnergyType.FIGHTING: 6,
}


def _card_row(meta):
    return {
        "cardId": meta.card_id,
        "cardType": _CARD_TYPES[meta.card_type],
        "name": meta.name,
        "hp": meta.hp if isinstance(meta.hp, int) else 0,
        "energyType": _ENERGY_TYPES.get(meta.energy_type, 0),
        "weakness": _ENERGY_TYPES.get(meta.weakness),
        "resistance": _ENERGY_TYPES.get(meta.resistance),
        "basic": meta.basic,
        "stage1": meta.stage1,
        "stage2": meta.stage2,
        "ex": meta.ex,
        "megaEx": meta.mega_ex,
        "tera": meta.tera,
        "attacks": list(meta.attack_ids),
        "skills": [
            {"name": effect.name, "text": effect.text} for effect in meta.effects
        ],
    }


def _registry(*, target_hp=300):
    cards = [_card_row(meta) for meta in CARD_META_BY_ID.values()]
    cards.append(
        {
            "cardId": 900,
            "cardType": 0,
            "name": "Test Target",
            "hp": target_hp,
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
        }
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
    return build_public_effect_registry(cards, attacks)


def _case(
    *,
    attack_ids=(),
    active,
    bench=(),
    hand=(),
    discard=(),
    raw_options=(),
    opponent_hp=300,
    opponent_hand=5,
    ppp_count=0,
):
    obs = observation(
        attack_ids,
        own_active=active,
        own_bench=bench,
        own_discard=discard,
        opponent_active=pokemon(
            900,
            900,
            player=1,
            hp=opponent_hp,
            max_hp=opponent_hp,
        ),
    )
    obs["current"]["players"][0]["hand"] = list(hand)
    obs["current"]["players"][0]["handCount"] = len(hand)
    obs["current"]["players"][1]["handCount"] = opponent_hand
    obs["select"]["option"] = list(raw_options)
    registry = _registry(target_hp=opponent_hp)
    state = checked_state(obs, ppp_count=ppp_count)
    options = build_semantic_options(obs)
    features = build_deck_features(state, options, registry)
    outcomes = build_attack_outcome_table(state, options, registry)
    return state, options, features, outcomes, registry


def test_fighting_gong_and_attack_ready_mega_evolution_emit():
    gong = card(1142, 30)
    current = _case(
        active=pokemon(675, 10, hp=110, energy_cards=((6, 50),)),
        hand=(gong,),
        raw_options=({"type": int(OptionType.PLAY), "index": 0},),
    )
    proposals = enumerate_fighting_gong_routes(
        current[0], current[1], current[2], current[4]
    )
    assert len(proposals) == 1
    assert proposals[0].proof.fact("purpose") == "CURRENT_ATTACK_ENERGY"
    assert proposals[0].transaction_plan.steps[
        0
    ].deferred_card_choice.ordered_card_id_classes == ((6,),)

    evolution = card(678, 31)
    current = _case(
        active=pokemon(677, 10, hp=80, energy_cards=((6, 50),)),
        hand=(evolution,),
        raw_options=(
            {
                "type": int(OptionType.EVOLVE),
                "area": int(AreaType.HAND),
                "index": 0,
                "inPlayArea": int(AreaType.ACTIVE),
                "inPlayIndex": 0,
            },
        ),
    )
    proposals = enumerate_evolution_routes(
        current[0], current[1], current[2], current[4]
    )
    assert len(proposals) == 1
    assert proposals[0].proof.fact("same_turn_attack") is True


def test_aura_uses_three_energy_hariyama_threshold_for_makuhita():
    current = _case(
        attack_ids=(982,),
        active=pokemon(678, 10, hp=340, energy_cards=((6, 50),)),
        bench=(pokemon(673, 20, hp=70),),
        hand=(card(674, 30),),
        discard=(card(6, 60), card(6, 61), card(6, 62)),
        raw_options=({"type": int(OptionType.ATTACK), "attackId": 982},),
    )
    proposals = enumerate_aura_continuity_routes(*current)
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.proof.fact("energy_count") == 3
    assert len(proposal.transaction_plan.reserved_refs) == 3
    assert proposal.transaction_plan.steps[0].expected_max_count == 3
    assert len(proposal.transaction_plan.steps) == 4


def test_minimal_ppp_and_safe_draw_prefixes_emit():
    ppp = card(1141, 30)
    current = _case(
        attack_ids=(982,),
        active=pokemon(678, 10, hp=340, energy_cards=((6, 50),)),
        hand=(ppp,),
        opponent_hp=160,
        raw_options=(
            {"type": int(OptionType.PLAY), "index": 0},
            {"type": int(OptionType.ATTACK), "attackId": 982},
        ),
    )
    proposals = enumerate_minimal_ppp_routes(
        current[0], current[1], current[2], current[3], current[4]
    )
    assert len(proposals) == 1
    assert proposals[0].proof.fact("additional_ppp_required") == 1

    judge = card(1213, 30)
    energy = card(6, 31)
    current = _case(
        active=pokemon(677, 10, hp=80, energy_cards=((6, 50),)),
        hand=(judge, energy),
        opponent_hand=8,
        raw_options=(
            {"type": int(OptionType.PLAY), "index": 0},
            {
                "type": int(OptionType.ATTACH),
                "area": int(AreaType.HAND),
                "index": 1,
                "inPlayArea": int(AreaType.ACTIVE),
                "inPlayIndex": 0,
            },
        ),
    )
    proposals = enumerate_safe_draw_supporter_routes(
        current[0], current[1], current[2], current[4]
    )
    assert any(
        proposal.action_spec.choices[0].card_id == 1213 for proposal in proposals
    )

    current = _case(
        active=pokemon(677, 10, hp=80, energy_cards=((6, 50),)),
        hand=(card(1227, 30),),
        raw_options=({"type": int(OptionType.PLAY), "index": 0},),
    )
    proposals = enumerate_safe_draw_supporter_routes(
        current[0], current[1], current[2], current[4]
    )
    assert any(
        proposal.action_spec.choices[0].card_id == 1227 for proposal in proposals
    )

    current = _case(
        active=pokemon(678, 10, hp=340, energy_cards=((6, 50),)),
        bench=(pokemon(675, 20, hp=110), pokemon(676, 21, hp=110)),
        hand=(card(6, 31), card(6, 32)),
        raw_options=(
            {
                "type": int(OptionType.SKILL),
                "cardId": 675,
                "serial": 20,
                "playerIndex": 0,
            },
        ),
    )
    proposals = enumerate_safe_draw_supporter_routes(
        current[0], current[1], current[2], current[4]
    )
    lunar = next(
        proposal
        for proposal in proposals
        if proposal.action_spec.choices[0].card_id == 675
    )
    assert lunar.transaction_plan.steps[0].stage == TransactionStage.SELECT_COST
    assert lunar.transaction_plan.steps[0].stochastic_boundary is True
