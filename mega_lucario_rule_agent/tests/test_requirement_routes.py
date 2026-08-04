from mega_lucario_rule_agent.attack_outcomes import build_attack_outcome_table
from mega_lucario_rule_agent.card_meta import (
    ATTACK_META_BY_ID,
    CARD_META_BY_ID,
    CardType,
    EnergyType,
)
from mega_lucario_rule_agent.features import build_deck_features, build_resource_ledger
from mega_lucario_rule_agent.public_effects import build_public_effect_registry
from mega_lucario_rule_agent.resolver import ResolverTier, resolve_proposals
from mega_lucario_rule_agent.routes import (
    enumerate_aura_continuity_routes,
    enumerate_cape_routes,
    enumerate_continuity_attach_routes,
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
    SelectContext,
    SelectType,
    build_semantic_options,
)
from mega_lucario_rule_agent.transactions import (
    ResumeStatus,
    TransactionStage,
    TransactionStore,
)
from mega_lucario_rule_agent.tests.test_attack_outcomes import (
    card,
    checked_state,
    effect_catalog_row,
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
        "evolvesFrom": meta.evolves_from,
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


def _registry(*, target_hp=300, unsafe_heave=False):
    cards = [_card_row(meta) for meta in CARD_META_BY_ID.values()]
    if unsafe_heave:
        hariyama = next(row for row in cards if row["cardId"] == 674)
        hariyama["skills"] = [
            {"name": "Unsupported Heave", "text": "Unsupported Heave"}
        ]
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
            "attacks": [2001],
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
    cards.extend(
        (
            {
                "cardId": 902,
                "cardType": 0,
                "name": "Bench Two Prize ex",
                "evolvesFrom": None,
                "hp": 100,
                "energyType": 0,
                "weakness": None,
                "resistance": None,
                "basic": True,
                "stage1": False,
                "stage2": False,
                "ex": True,
                "megaEx": False,
                "tera": False,
                "attacks": [],
                "skills": [],
            },
            {
                "cardId": 903,
                "cardType": 0,
                "name": "Durable One Prize",
                "evolvesFrom": None,
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
                "cardId": 905,
                "cardType": 0,
                "name": "Durable Two Prize ex",
                "evolvesFrom": None,
                "hp": 200,
                "energyType": 0,
                "weakness": None,
                "resistance": None,
                "basic": True,
                "stage1": False,
                "stage2": False,
                "ex": True,
                "megaEx": False,
                "tera": False,
                "attacks": [],
                "skills": [],
            },
            effect_catalog_row("LILLIES_PEARL"),
            effect_catalog_row("JAMMING_TOWER"),
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
    attacks.append(
        {
            "attackId": 2001,
            "name": "Exact Fixed Threat",
            "text": "",
            "damage": 50,
            "energies": [6],
        }
    )
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
    opponent_active=None,
    own_prizes=6,
    opponent_prizes=6,
    stadium=(),
    unsafe_heave=False,
):
    obs = observation(
        attack_ids,
        own_active=active,
        own_bench=bench,
        own_discard=discard,
        opponent_active=opponent_active
        or pokemon(
            900,
            900,
            player=1,
            hp=opponent_hp,
            max_hp=opponent_hp,
        ),
        opponent_bench=opponent_bench,
        own_prizes=own_prizes,
        opponent_prizes=opponent_prizes,
        stadium=stadium,
    )
    obs["current"]["players"][0]["hand"] = list(hand)
    obs["current"]["players"][0]["prize"] = [
        card(6, 950 + index) for index in range(own_prizes)
    ]
    obs["current"]["players"][1]["prize"] = [
        card(6, 960 + index, player=1) for index in range(opponent_prizes)
    ]
    obs["current"]["players"][0]["handCount"] = len(hand)
    obs["current"]["players"][1]["handCount"] = opponent_hand
    obs["select"]["option"] = list(raw_options)
    registry = _registry(target_hp=opponent_hp, unsafe_heave=unsafe_heave)
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


def _boss_gust_case(
    *,
    opponent_active=None,
    opponent_bench=(),
    own_prizes=6,
    opponent_prizes=6,
    stadium=(),
    reverse_options=False,
):
    raw_options = (
        {"type": int(OptionType.ATTACK), "attackId": 982},
        {"type": int(OptionType.PLAY), "index": 0},
    )
    if reverse_options:
        raw_options = tuple(reversed(raw_options))
    return _case(
        attack_ids=(982,),
        active=pokemon(678, 10, hp=340, energy_cards=((6, 50),)),
        hand=(card(1182, 30),),
        raw_options=raw_options,
        opponent_active=opponent_active,
        opponent_bench=opponent_bench,
        own_prizes=own_prizes,
        opponent_prizes=opponent_prizes,
        stadium=stadium,
    )


def test_gust_exact_two_prize_energy_target_and_terminal_direction():
    target = pokemon(
        902,
        920,
        player=1,
        hp=100,
        energy_cards=((6, 921), (6, 922)),
    )
    ordinary = _boss_gust_case(
        opponent_active=pokemon(903, 910, player=1, hp=300),
        opponent_bench=(target,),
        own_prizes=6,
        opponent_prizes=2,
    )
    proposals = enumerate_gust_routes(
        ordinary[0], ordinary[1], ordinary[2], ordinary[3], ordinary[4]
    )
    assert len(proposals) == 1
    assert proposals[0].tier == ResolverTier.STRICTLY_SUPERIOR_GUST
    assert proposals[0].proof.fact("prizes_taken") == 2
    assert proposals[0].proof.fact("attached_energy_removed") == 2
    assert proposals[0].proof.fact("terminal_win") is False
    assert proposals[0].proof.fact("original_target_ref")[3] == 920
    assert proposals[0].proof.fact("dominance_field") == "prizes_taken"

    terminal = _boss_gust_case(
        opponent_active=pokemon(903, 910, player=1, hp=300),
        opponent_bench=(target,),
        own_prizes=2,
        opponent_prizes=6,
    )
    proposal = enumerate_gust_routes(
        terminal[0], terminal[1], terminal[2], terminal[3], terminal[4]
    )[0]
    assert proposal.proof.fact("terminal_win") is True
    assert proposal.proof.fact("own_prizes_after") == 0
    assert proposal.tier == ResolverTier.TERMINAL_OR_SUPERIOR_GUST


def test_gust_keeps_current_three_prize_active_over_bench_two_prize():
    current = _boss_gust_case(
        opponent_active=pokemon(901, 930, player=1, hp=100),
        opponent_bench=(pokemon(902, 931, player=1, hp=100),),
    )
    assert (
        enumerate_gust_routes(
            current[0], current[1], current[2], current[3], current[4]
        )
        == ()
    )


def test_gust_same_prize_prefers_energy_and_registered_ability_denial():
    current = _boss_gust_case(
        opponent_active=pokemon(903, 940, player=1, hp=300),
        opponent_bench=(
            pokemon(676, 941, player=1, hp=110),
            pokemon(
                675,
                942,
                player=1,
                hp=110,
                energy_cards=((6, 943), (6, 944)),
            ),
        ),
    )
    proposal = enumerate_gust_routes(
        current[0], current[1], current[2], current[3], current[4]
    )[0]
    assert proposal.proof.fact("gust_target_ref")[3] == 942
    assert proposal.proof.fact("attached_energy_removed") == 2
    assert proposal.proof.fact("engine_denial") == 1
    assert proposal.proof.fact("dominance_field") == "prizes_taken"


def test_gust_rejects_high_energy_bench_target_without_exact_ko():
    current = _boss_gust_case(
        opponent_active=pokemon(903, 950, player=1, hp=300),
        opponent_bench=(
            pokemon(
                905,
                951,
                player=1,
                hp=200,
                energy_cards=((6, 952), (6, 953), (6, 954)),
            ),
        ),
    )
    assert (
        enumerate_gust_routes(
            current[0], current[1], current[2], current[3], current[4]
        )
        == ()
    )


def test_gust_allows_registered_tool_attached_exact_ko_target():
    current = _boss_gust_case(
        opponent_active=pokemon(903, 960, player=1, hp=300),
        opponent_bench=(
            pokemon(902, 961, player=1, hp=100, tools=((1172, 962),)),
        ),
    )
    proposal = enumerate_gust_routes(
        current[0], current[1], current[2], current[3], current[4]
    )[0]
    assert proposal.proof.fact("gust_target_ref")[3] == 961
    assert proposal.proof.fact("tool_cards_removed") == 1


def test_gust_registered_stadium_is_not_a_blanket_stop():
    current = _boss_gust_case(
        opponent_active=pokemon(903, 970, player=1, hp=300),
        opponent_bench=(pokemon(902, 971, player=1, hp=100),),
        stadium=(card(1246, 972, player=1),),
    )
    proposal = enumerate_gust_routes(
        current[0], current[1], current[2], current[3], current[4]
    )[0]
    assert proposal.proof.fact("gust_target_ref")[3] == 971


def test_gust_rejects_unsafe_heave_and_retains_boss():
    current = _case(
        attack_ids=(982,),
        active=pokemon(678, 10, hp=340, energy_cards=((6, 50),)),
        bench=(pokemon(673, 20, hp=70),),
        hand=(card(674, 30), card(1182, 31)),
        opponent_active=pokemon(903, 980, player=1, hp=300),
        opponent_bench=(pokemon(902, 981, player=1, hp=100),),
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
        unsafe_heave=True,
    )
    proposals = enumerate_gust_routes(
        current[0], current[1], current[2], current[3], current[4]
    )
    assert len(proposals) == 1
    assert proposals[0].action_spec.choices[0].card_id == 1182
    assert proposals[0].proof.fact("supporter_opportunity_cost") == 1


def test_terminal_boss_resolves_over_wally_cape_and_development():
    current = _case(
        attack_ids=(982,),
        active=pokemon(
            678,
            10,
            hp=40,
            max_hp=340,
            energy_cards=((6, 50),),
        ),
        bench=(pokemon(677, 20, hp=80, energy_cards=((6, 51),)),),
        hand=(
            card(1182, 30),
            card(1229, 31),
            card(1159, 32),
            card(678, 33),
        ),
        opponent_active=pokemon(
            900,
            990,
            player=1,
            hp=200,
            energy_cards=((6, 991),),
        ),
        opponent_hp=200,
        opponent_bench=(pokemon(901, 993, player=1, hp=100),),
        own_prizes=3,
        opponent_prizes=6,
        raw_options=(
            {"type": int(OptionType.ATTACK), "attackId": 982},
            {"type": int(OptionType.PLAY), "index": 0},
            {"type": int(OptionType.PLAY), "index": 1},
            {
                "type": int(OptionType.ATTACH),
                "area": int(AreaType.HAND),
                "index": 2,
                "inPlayArea": int(AreaType.ACTIVE),
                "inPlayIndex": 0,
            },
            {
                "type": int(OptionType.EVOLVE),
                "area": int(AreaType.HAND),
                "index": 3,
                "inPlayArea": int(AreaType.BENCH),
                "inPlayIndex": 0,
            },
        ),
    )
    gust = enumerate_gust_routes(
        current[0], current[1], current[2], current[3], current[4]
    )
    wally = enumerate_wally_routes(
        current[0], current[1], current[2], current[3], current[4]
    )
    cape = enumerate_cape_routes(
        current[0], current[1], current[2], current[3], current[4]
    )
    development = enumerate_evolution_routes(
        current[0], current[1], current[2], current[4]
    )
    assert gust and wally and cape and development
    resolution = resolve_proposals(
        current[0],
        current[1],
        build_resource_ledger(current[0]),
        gust + wally + cape + development,
        registry=current[4],
    )
    assert resolution.selected is not None
    assert resolution.selected.action_spec.choices[0].card_id == 1182
    assert resolution.selected.tier == ResolverTier.TERMINAL_OR_SUPERIOR_GUST


def test_gust_bench_and_main_option_reversal_keep_same_physical_target():
    lower_physical_ref = pokemon(902, 1001, player=1, hp=100)
    higher_physical_ref = pokemon(902, 1002, player=1, hp=100)
    first = _boss_gust_case(
        opponent_active=pokemon(903, 1000, player=1, hp=300),
        opponent_bench=(higher_physical_ref, lower_physical_ref),
    )
    reversed_case = _boss_gust_case(
        opponent_active=pokemon(903, 1000, player=1, hp=300),
        opponent_bench=(lower_physical_ref, higher_physical_ref),
        reverse_options=True,
    )
    first_proposal = enumerate_gust_routes(
        first[0], first[1], first[2], first[3], first[4]
    )[0]
    reversed_proposal = enumerate_gust_routes(
        reversed_case[0],
        reversed_case[1],
        reversed_case[2],
        reversed_case[3],
        reversed_case[4],
    )[0]
    assert first_proposal.proof.fact("gust_target_ref")[3] == 1001
    assert reversed_proposal.proof.fact("gust_target_ref")[3] == 1001
    assert first_proposal.transaction_plan.target_refs[0].serial == 1001
    assert reversed_proposal.transaction_plan.target_refs[0].serial == 1001

    callback_obs = observation(
        (),
        own_active=pokemon(678, 10, hp=340, energy_cards=((6, 50),)),
        opponent_active=pokemon(903, 1000, player=1, hp=300),
        opponent_bench=(higher_physical_ref, lower_physical_ref),
    )
    callback_obs["current"]["turnActionCount"] = 5
    callback_obs["current"]["supporterPlayed"] = True
    callback_obs["current"]["players"][0]["hand"] = []
    callback_obs["current"]["players"][0]["handCount"] = 0
    callback_obs["current"]["players"][0]["discard"] = [card(1182, 30)]
    callback_obs["select"] = {
        "type": int(SelectType.CARD),
        "context": int(SelectContext.SWITCH),
        "minCount": 1,
        "maxCount": 1,
        "remainDamageCounter": 0,
        "remainEnergyCost": 0,
        "option": [
            {
                "type": int(OptionType.CARD),
                "playerIndex": 1,
                "area": int(AreaType.BENCH),
                "index": 1,
            },
            {
                "type": int(OptionType.CARD),
                "playerIndex": 1,
                "area": int(AreaType.BENCH),
                "index": 0,
            },
        ],
        "deck": None,
        "contextCard": None,
        "effect": card(1182, 30),
    }
    callback_state = checked_state(callback_obs)
    callback_options = build_semantic_options(callback_obs)
    store = TransactionStore()
    started = store.start(
        first_proposal.transaction_plan,
        first[0],
        first[1],
    )
    assert started.bound_action == (1,)
    resumed = store.resume(callback_state, callback_options)
    assert resumed.status == ResumeStatus.ADVANCED_ISSUE
    assert resumed.bound_action == (0,)


def test_wally_does_not_emit_without_a_public_opponent_attack():
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
    proposals = enumerate_wally_routes(
        current[0], current[1], current[2], current[3], current[4]
    )
    assert proposals == ()


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
    proposals = enumerate_cape_routes(
        current[0], current[1], current[2], current[3], current[4]
    )
    # An opponent with no public attack is no longer a Cape survival claim.
    assert proposals == ()


def test_midgame_attach_completes_exact_active_deficit():
    current = _case(
        active=pokemon(677, 10, hp=80),
        hand=(card(6, 30),),
        raw_options=(
            {
                "type": int(OptionType.ATTACH),
                "area": int(AreaType.HAND),
                "index": 0,
                "inPlayArea": int(AreaType.ACTIVE),
                "inPlayIndex": 0,
            },
        ),
    )
    proposals = enumerate_continuity_attach_routes(
        current[0],
        current[1],
        current[2],
        current[4],
        build_resource_ledger(current[0]),
    )
    assert len(proposals) == 1
    assert proposals[0].proof.fact("purpose") == "CURRENT_ATTACK_COMPLETION"
    assert proposals[0].proof.fact("deficit_after") == 0
    assert proposals[0].action_spec.choices[0].target_lineage_serial == 10


def test_midgame_attach_builds_hariyama_threshold_without_surplus_attach():
    current = _case(
        attack_ids=(982,),
        active=pokemon(678, 10, hp=340, energy_cards=((6, 50),)),
        bench=(pokemon(673, 20, hp=80, energy_cards=((6, 60),)),),
        hand=(card(6, 30), card(674, 31)),
        raw_options=(
            {
                "type": int(OptionType.ATTACH),
                "area": int(AreaType.HAND),
                "index": 0,
                "inPlayArea": int(AreaType.BENCH),
                "inPlayIndex": 0,
            },
            {"type": int(OptionType.ATTACK), "attackId": 982},
        ),
    )
    proposals = enumerate_continuity_attach_routes(
        current[0],
        current[1],
        current[2],
        current[4],
        build_resource_ledger(current[0]),
    )
    assert len(proposals) == 1
    assert proposals[0].proof.fact("target_ref")[2] == 673
    assert proposals[0].proof.fact("deficit_before") == 2
    assert proposals[0].proof.fact("deficit_after") == 1


def test_midgame_energy_backed_mega_and_hariyama_evolution_emit():
    current = _case(
        attack_ids=(982,),
        active=pokemon(678, 10, hp=340, energy_cards=((6, 50),)),
        bench=(pokemon(677, 20, hp=80, energy_cards=((6, 60),)),),
        hand=(card(678, 30),),
        raw_options=(
            {
                "type": int(OptionType.EVOLVE),
                "area": int(AreaType.HAND),
                "index": 0,
                "inPlayArea": int(AreaType.BENCH),
                "inPlayIndex": 0,
            },
            {"type": int(OptionType.ATTACK), "attackId": 982},
        ),
    )
    proposals = enumerate_evolution_routes(
        current[0], current[1], current[2], current[4]
    )
    assert len(proposals) == 1
    assert proposals[0].proof.fact("energy_continuity") is True
    assert proposals[0].proof.fact("same_turn_attack") is False

    current = _case(
        attack_ids=(982,),
        active=pokemon(678, 10, hp=340, energy_cards=((6, 50),)),
        bench=(
            pokemon(
                673,
                20,
                hp=80,
                energy_cards=((6, 60), (6, 61), (6, 62)),
            ),
        ),
        hand=(card(674, 30),),
        raw_options=(
            {
                "type": int(OptionType.EVOLVE),
                "area": int(AreaType.HAND),
                "index": 0,
                "inPlayArea": int(AreaType.BENCH),
                "inPlayIndex": 0,
            },
            {"type": int(OptionType.ATTACK), "attackId": 982},
        ),
    )
    proposals = enumerate_evolution_routes(
        current[0], current[1], current[2], current[4]
    )
    assert len(proposals) == 1
    assert proposals[0].proof.fact("energy_ready") is True
