from mega_lucario_rule_agent.attack_outcomes import build_attack_outcome_table
from mega_lucario_rule_agent.card_meta import (
    ATTACK_META_BY_ID,
    CARD_META_BY_ID,
    CardType,
    EnergyType,
)
from mega_lucario_rule_agent.features import build_deck_features, build_resource_ledger
from mega_lucario_rule_agent.public_effects import build_public_effect_registry
from mega_lucario_rule_agent.routes import (
    enumerate_aura_continuity_routes,
    enumerate_cape_routes,
    enumerate_evolution_routes,
    enumerate_fighting_gong_routes,
    enumerate_gust_routes,
    enumerate_minimal_ppp_routes,
    enumerate_safe_draw_supporter_routes,
    enumerate_switch_routes,
    enumerate_ultra_ball_routes,
    enumerate_wally_routes,
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
    cards.append(
        {
            "cardId": 901,
            "cardType": 0,
            "name": "Bench Prize ex",
            "hp": 100,
            "energyType": 0,
            "weakness": None,
            "resistance": None,
            "basic": False,
            "stage1": True,
            "stage2": False,
            "ex": True,
            "megaEx": True,
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
    opponent_bench=(),
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
        opponent_bench=opponent_bench,
    )
    obs["current"]["players"][0]["hand"] = list(hand)
    obs["current"]["players"][0]["prize"] = [card(6, 950 + index) for index in range(6)]
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


def test_ultra_ball_uses_only_safe_surplus_and_guaranteed_target():
    current = _case(
        active=pokemon(677, 10, hp=80),
        hand=(card(1121, 30), card(1121, 31), card(1121, 32)),
        raw_options=({"type": int(OptionType.PLAY), "index": 0},),
    )
    ledger = build_resource_ledger(current[0])
    proposals = enumerate_ultra_ball_routes(
        current[0],
        current[1],
        current[2],
        current[4],
        ledger,
    )
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.proof.fact("ordered_card_id_classes")[0] == (678,)
    assert tuple(
        ref_value.serial for ref_value in proposal.transaction_plan.reserved_refs
    ) == (31, 32)
    assert proposal.transaction_plan.steps[0].expected_min_count == 2
    assert proposal.transaction_plan.steps[0].expected_max_count == 2


def test_hariyama_gust_preempts_boss_for_exact_high_prize_ko():
    current = _case(
        attack_ids=(982,),
        active=pokemon(678, 10, hp=340, energy_cards=((6, 50),)),
        bench=(pokemon(673, 20, hp=70),),
        hand=(card(674, 30), card(1182, 31)),
        opponent_bench=(pokemon(901, 901, player=1, hp=100, max_hp=100),),
        raw_options=(
            {"type": int(OptionType.ATTACK), "attackId": 982},
            {
                "type": int(OptionType.EVOLVE),
                "area": int(AreaType.HAND),
                "index": 0,
                "inPlayArea": int(AreaType.BENCH),
                "inPlayIndex": 0,
            },
            {"type": int(OptionType.PLAY), "index": 1},
        ),
    )
    proposals = enumerate_gust_routes(
        current[0],
        current[1],
        current[2],
        current[3],
        current[4],
    )
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.action_spec.choices[0].card_id == 674
    assert proposal.transaction_plan.steps[0].expected_context_ref.card_id == 674
    assert proposal.transaction_plan.steps[1].expected_effect_ref.card_id == 674
    assert proposal.proof.fact("gust_target_ref")[2] == 901


def test_wally_reattaches_returned_energy_before_attack_replan():
    current = _case(
        attack_ids=(982,),
        active=pokemon(
            678,
            10,
            hp=160,
            max_hp=340,
            energy_cards=((6, 50),),
        ),
        hand=(card(1229, 30),),
        raw_options=(
            {"type": int(OptionType.PLAY), "index": 0},
            {"type": int(OptionType.ATTACK), "attackId": 982},
        ),
    )
    proposals = enumerate_wally_routes(current[0], current[1], current[2], current[4])
    assert len(proposals) == 1
    steps = proposals[0].transaction_plan.steps
    assert len(steps) == 2
    reattach = steps[1].action_spec.choices[0]
    assert reattach.option_type == int(OptionType.ATTACH)
    assert reattach.card_serial == 50
    assert reattach.source_zone == int(AreaType.HAND)
    assert reattach.target_lineage_serial == current[0].own_active.lineage_serial


def test_switch_and_cape_emit_only_for_explicit_targets():
    current = _case(
        active=pokemon(677, 10, hp=80),
        bench=(
            pokemon(
                674,
                20,
                hp=150,
                energy_cards=((6, 60), (6, 61), (6, 62)),
            ),
        ),
        hand=(card(1123, 30),),
        raw_options=({"type": int(OptionType.PLAY), "index": 0},),
    )
    proposals = enumerate_switch_routes(current[0], current[1], current[2], current[4])
    assert len(proposals) == 1
    assert proposals[0].proof.fact("target_ref")[2] == 674

    current = _case(
        attack_ids=(982,),
        active=pokemon(
            678,
            10,
            hp=160,
            max_hp=340,
            energy_cards=((6, 50),),
        ),
        hand=(card(1159, 30),),
        raw_options=(
            {
                "type": int(OptionType.ATTACH),
                "area": int(AreaType.HAND),
                "index": 0,
                "inPlayArea": int(AreaType.ACTIVE),
                "inPlayIndex": 0,
            },
            {"type": int(OptionType.ATTACK), "attackId": 982},
        ),
    )
    proposals = enumerate_cape_routes(current[0], current[1], current[2], current[4])
    assert len(proposals) == 1
    assert proposals[0].proof.fact("purpose") == "THREE_PRIZE_MEGA"
