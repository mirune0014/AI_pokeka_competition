from mega_lucario_rule_agent.attack_outcomes import build_attack_outcome_table
from mega_lucario_rule_agent.card_meta import ATTACK_META_BY_ID, CARD_META_BY_ID
from mega_lucario_rule_agent.features import build_deck_features
from mega_lucario_rule_agent.public_effects import build_public_effect_registry
from mega_lucario_rule_agent.routes import enumerate_cape_routes
from mega_lucario_rule_agent.state_view import AreaType, OptionType, build_semantic_options
from mega_lucario_rule_agent.tests.test_attack_outcomes import (
    card,
    checked_state,
    effect_catalog_row,
    observation,
    pokemon,
)
from mega_lucario_rule_agent.tests.test_wally_public_survival import (
    _ENERGY_TYPES,
    _card_row,
    _case,
    _opponent_active,
    _registry,
)


def _cape_options(*, with_attack=True):
    rows = [
        {
            "type": int(OptionType.ATTACH),
            "area": int(AreaType.HAND),
            "index": 0,
            "inPlayArea": int(AreaType.ACTIVE),
            "inPlayIndex": 0,
        }
    ]
    if with_attack:
        rows.append({"type": int(OptionType.ATTACK), "attackId": 982})
    return tuple(rows)


def _cape(case):
    return enumerate_cape_routes(
        case[0], case[1], case[2], case[3], case[4]
    )


def _active_case(
    *,
    own_hp=160,
    opponent_damage=100,
    opponent_attacks=(2001,),
    opponent_prizes=6,
    with_attack=True,
):
    return _case(
        own_hp=own_hp,
        opponent_damage=opponent_damage,
        opponent_attacks=opponent_attacks,
        opponent_prizes=opponent_prizes,
        hand=(1159,),
        raw_options=_cape_options(with_attack=with_attack),
    )


def test_active_ko_delta_with_productive_attack_emits_cape_and_facts():
    # Printed 100 becomes 170 after Psychic weakness and Fighting resistance.
    proposals = _cape(_active_case())

    assert len(proposals) == 1
    proof = proposals[0].proof
    assert proof.fact("branch") == "ACTIVE_RESPONSE"
    assert proof.fact("hp_before") == 160
    assert proof.fact("max_hp_before") == 340
    assert proof.fact("hp_after") == 260
    assert proof.fact("max_hp_after") == 440
    assert proof.fact("opponent_attack_ids") == (2001,)
    assert proof.fact("max_target_loss") == 170
    assert proof.fact("ko_without") is True
    assert proof.fact("ko_with") is False
    assert proof.fact("target_prize_value") == 3
    assert proof.fact("productive_attack_id") == 982
    assert proof.fact("preserves_productive_attack") is True
    assert proof.fact("prevents_terminal_prize_loss") is False
    assert proof.fact("certificate_status") == "PROVISIONAL_GENERIC_GATE_A2"


def test_gate0_no_attacks_and_non_delta_cases_do_not_emit():
    assert _cape(
        _active_case(opponent_damage=180, opponent_attacks=())
    ) == ()
    # 200 * 2 - 30 = 370, so Cape still cannot save 160 + 100 HP.
    assert _cape(_active_case(opponent_damage=200)) == ()
    # 170 damage already leaves an Active at 200 HP alive without Cape.
    assert _cape(_active_case(own_hp=200)) == ()


def test_delta_without_productive_attack_or_terminal_loss_does_not_emit():
    assert _cape(_active_case(with_attack=False)) == ()


def test_exact_three_prize_terminal_loss_is_sufficient_without_attack():
    proposals = _cape(
        _active_case(with_attack=False, opponent_prizes=3)
    )

    assert len(proposals) == 1
    proof = proposals[0].proof
    assert proof.fact("productive_attack_id") is None
    assert proof.fact("preserves_productive_attack") is False
    assert proof.fact("prevents_terminal_prize_loss") is True
    assert proof.fact("prevented_prizes") == 3


def test_existing_tool_blocks_cape_even_when_survival_delta_exists():
    obs = observation(
        (982,),
        own_active=pokemon(
            678,
            10,
            hp=160,
            max_hp=440,
            energy_cards=((6, 50),),
            tools=((1159, 80),),
        ),
        opponent_active=_opponent_active(),
    )
    obs["current"]["players"][0]["hand"] = [card(1159, 30)]
    obs["current"]["players"][0]["handCount"] = 1
    obs["select"]["option"] = list(_cape_options())
    registry = _registry(opponent_damage=100)
    state = checked_state(obs)
    options = build_semantic_options(obs)
    features = build_deck_features(state, options, registry)
    outcomes = build_attack_outcome_table(state, options, registry)

    assert enumerate_cape_routes(
        state, options, features, outcomes, registry
    ) == ()


def _basic_energy_row(card_id, name, energy_type):
    return {
        "cardId": card_id,
        "cardType": 5,
        "name": name,
        "hp": 0,
        "energyType": energy_type,
        "weakness": None,
        "resistance": None,
        "basic": False,
        "stage1": False,
        "stage2": False,
        "ex": False,
        "megaEx": False,
        "tera": False,
        "attacks": [],
        "skills": [],
    }


def _spread_registry():
    cards = [_card_row(meta) for meta in CARD_META_BY_ID.values()]
    cards.extend(
        (
            _basic_energy_row(7001, "Basic Fire Energy", 2),
            _basic_energy_row(7002, "Basic Water Energy", 5),
            {
                "cardId": 121,
                "cardType": 0,
                "name": "Dragapult ex",
                "evolvesFrom": "Drakloak",
                "hp": 320,
                "energyType": 9,
                "weakness": None,
                "resistance": None,
                "basic": False,
                "stage1": False,
                "stage2": True,
                "ex": True,
                "megaEx": False,
                "tera": True,
                "attacks": [153, 154],
                "skills": [],
            },
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
    attacks.extend(
        (
            {
                "attackId": 153,
                "name": "Jet Headbutt",
                "text": "",
                "damage": 70,
                "energies": [0],
            },
            {
                "attackId": 154,
                "name": "Phantom Dive",
                "text": (
                    "Put 6 damage counters on your opponent’s Benched "
                    "Pokémon in any way you like."
                ),
                "damage": 200,
                "energies": [2, 5],
            },
        )
    )
    return build_public_effect_registry(cards, attacks)


def _spread_case(*, reverse_options=False, jamming=False):
    opponent = pokemon(
        121,
        110,
        player=1,
        hp=320,
        max_hp=320,
        energy_cards=((7001, 71), (7002, 72)),
    )
    opponent["energies"] = [2, 5]
    bench = (
        pokemon(677, 20, hp=20, max_hp=80),
        pokemon(677, 21, hp=20, max_hp=80),
    )
    jamming_row = effect_catalog_row("JAMMING_TOWER")
    obs = observation(
        (982,),
        own_active=pokemon(
            678,
            10,
            hp=340,
            max_hp=340,
            energy_cards=((6, 50),),
        ),
        own_bench=bench,
        opponent_active=opponent,
        stadium=(card(jamming_row["cardId"], 500),) if jamming else (),
    )
    obs["current"]["players"][0]["hand"] = [card(1159, 30)]
    obs["current"]["players"][0]["handCount"] = 1
    attach_options = [
        {
            "type": int(OptionType.ATTACH),
            "area": int(AreaType.HAND),
            "index": 0,
            "inPlayArea": int(AreaType.BENCH),
            "inPlayIndex": index,
        }
        for index in (0, 1)
    ]
    if reverse_options:
        attach_options.reverse()
    obs["select"]["option"] = [
        *attach_options,
        {"type": int(OptionType.ATTACK), "attackId": 982},
    ]
    registry = _spread_registry()
    state = checked_state(obs)
    options = build_semantic_options(obs)
    features = build_deck_features(state, options, registry)
    outcomes = build_attack_outcome_table(state, options, registry)
    return state, options, features, outcomes, registry


def test_exact_phantom_dive_saves_damaged_bench_riolu_order_independently():
    first = _cape(_spread_case())
    reversed_rows = _cape(_spread_case(reverse_options=True))

    assert len(first) == len(reversed_rows) == 1
    assert first[0].action_spec.choices[0].target_lineage_serial == 20
    assert reversed_rows[0].action_spec.choices[0].target_lineage_serial == 20
    proof = first[0].proof
    assert proof.fact("branch") == "BENCH_SPREAD"
    assert proof.fact("opponent_attack_ids") == (154,)
    assert proof.fact("max_target_loss") == 60
    assert proof.fact("ko_without") is True
    assert proof.fact("ko_with") is False
    assert proof.fact("certificate_status") == "PROVISIONAL_GENERIC_GATE_A2"


def test_jamming_tower_blocks_exact_bench_cape_delta():
    assert _cape(_spread_case(jamming=True)) == ()
