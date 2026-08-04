from mega_lucario_rule_agent.attack_outcomes import (
    build_attack_outcome_table,
    build_public_opponent_attack_threat,
)
from mega_lucario_rule_agent.card_meta import (
    ATTACK_META_BY_ID,
    CARD_META_BY_ID,
    CardType,
    EnergyType,
)
from mega_lucario_rule_agent.features import build_deck_features, build_resource_ledger
from mega_lucario_rule_agent.public_effects import build_public_effect_registry
from mega_lucario_rule_agent.resolver import resolve_proposals
from mega_lucario_rule_agent.routes import (
    enumerate_gust_routes,
    enumerate_safe_draw_supporter_routes,
    enumerate_wally_routes,
)
from mega_lucario_rule_agent.state_view import OptionType, build_semantic_options
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


def _registry(
    *,
    opponent_attacks=(2001,),
    opponent_damage=100,
    opponent_text="",
    opponent_hp=300,
    own_resistance=3,
):
    cards = [_card_row(meta) for meta in CARD_META_BY_ID.values()]
    lucario = next(row for row in cards if row["cardId"] == 678)
    lucario["weakness"] = 3
    lucario["resistance"] = own_resistance
    cards.extend(
        (
            {
                "cardId": 7,
                "cardType": 5,
                "name": "Basic Psychic Energy",
                "hp": 0,
                "energyType": 3,
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
            },
            {
                "cardId": 900,
                "cardType": 0,
                "name": "Public Psychic Attacker",
                "hp": opponent_hp,
                "energyType": 3,
                "weakness": None,
                "resistance": None,
                "basic": True,
                "stage1": False,
                "stage2": False,
                "ex": False,
                "megaEx": False,
                "tera": False,
                "attacks": list(opponent_attacks),
                "skills": [],
            },
            {
                "cardId": 901,
                "cardType": 0,
                "name": "Terminal Bench Mega ex",
                "hp": 100,
                "energyType": 1,
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
    if opponent_attacks:
        attacks.append(
            {
                "attackId": 2001,
                "name": "Public Fixed Hit",
                "text": opponent_text,
                "damage": opponent_damage,
                # Colorless must be payable by the attached Psychic Energy.
                "energies": [0],
            }
        )
    return build_public_effect_registry(cards, attacks)


def _opponent_active(*, hp=300, with_energy=True):
    result = pokemon(
        900,
        900,
        player=1,
        hp=hp,
        max_hp=hp,
        energy_cards=((7, 70),) if with_energy else (),
    )
    result["energies"] = [3] if with_energy else []
    return result


def _case(
    *,
    own_hp=160,
    own_energy=((6, 50),),
    opponent_damage=100,
    opponent_text="",
    opponent_attacks=(2001,),
    opponent_hp=300,
    hand=(1229,),
    raw_options=None,
    opponent_bench=(),
    own_prizes=6,
    opponent_prizes=6,
    opponent_hand=5,
    deck_count=40,
    poisoned=False,
    burned=False,
    confused=False,
):
    hand_cards = tuple(card(card_id, 30 + index) for index, card_id in enumerate(hand))
    if raw_options is None:
        raw_options = (
            {"type": int(OptionType.PLAY), "index": 0},
            {"type": int(OptionType.ATTACK), "attackId": 982},
        )
    obs = observation(
        (982,),
        own_active=pokemon(
            678,
            10,
            hp=own_hp,
            max_hp=340,
            energy_cards=own_energy,
        ),
        opponent_active=_opponent_active(hp=opponent_hp),
        opponent_bench=opponent_bench,
        own_prizes=own_prizes,
        opponent_prizes=opponent_prizes,
    )
    obs["current"]["players"][0]["hand"] = list(hand_cards)
    obs["current"]["players"][0]["handCount"] = len(hand_cards)
    obs["current"]["players"][0]["deckCount"] = deck_count
    obs["current"]["players"][0]["poisoned"] = poisoned
    obs["current"]["players"][0]["burned"] = burned
    obs["current"]["players"][0]["confused"] = confused
    obs["current"]["players"][1]["handCount"] = opponent_hand
    obs["select"]["option"] = list(raw_options)
    registry = _registry(
        opponent_attacks=opponent_attacks,
        opponent_damage=opponent_damage,
        opponent_text=opponent_text,
        opponent_hp=opponent_hp,
    )
    state = checked_state(obs)
    options = build_semantic_options(obs)
    features = build_deck_features(state, options, registry)
    outcomes = build_attack_outcome_table(state, options, registry)
    return state, options, features, outcomes, registry


def _wally(case):
    return enumerate_wally_routes(
        case[0], case[1], case[2], case[3], case[4]
    )


def test_low_printed_damage_uses_weakness_resistance_and_emits_wally():
    case = _case(own_hp=200, opponent_damage=120)
    threat = build_public_opponent_attack_threat(case[0], case[4])

    assert threat.exact
    assert threat.max_damage == 210  # 120 * Psychic weakness - 30 resistance
    assert threat.knockout_before_heal is True
    assert threat.knockout_after_heal is False
    proposals = _wally(case)
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.proof.fact("before_hp") == 200
    assert proposal.proof.fact("after_hp") == 340
    assert proposal.proof.fact("max_opponent_attack_ids") == (2001,)
    assert proposal.proof.fact("reestablished_attack_id") == 982
    assert proposal.proof.fact("certificate_status") == "PROVISIONAL_GENERIC_GATE_A1"
    steps = proposal.transaction_plan.steps
    assert len(steps) == 2
    assert steps[0].stage == TransactionStage.SELECT_EFFECT_TARGET
    assert steps[1].stage == TransactionStage.SELECT_ENERGY
    assert steps[1].action_spec.choices[0].card_serial == 50


def test_no_public_attacks_turns_gate0_wally_one_to_zero():
    case = _case(
        own_hp=160,
        opponent_damage=180,
        opponent_attacks=(),
    )
    threat = build_public_opponent_attack_threat(case[0], case[4])

    assert threat.exact
    assert threat.max_damage == 0
    assert threat.max_attack_ids == ()
    assert _wally(case) == ()


def test_heal_still_ko_and_already_survives_do_not_emit():
    assert _wally(_case(own_hp=160, opponent_damage=220)) == ()
    assert _wally(_case(own_hp=200, opponent_damage=100)) == ()


def test_terminal_boss_is_preferred_and_wally_is_not_strong():
    bench = (pokemon(901, 901, player=1, hp=100, max_hp=100),)
    case = _case(
        own_hp=160,
        opponent_damage=100,
        hand=(1229, 1182),
        own_prizes=3,
        opponent_prizes=3,
        opponent_bench=bench,
        raw_options=(
            {"type": int(OptionType.PLAY), "index": 0},
            {"type": int(OptionType.PLAY), "index": 1},
            {"type": int(OptionType.ATTACK), "attackId": 982},
        ),
    )
    gust = enumerate_gust_routes(
        case[0], case[1], case[2], case[3], case[4]
    )

    assert len(gust) == 1
    assert gust[0].action_spec.choices[0].card_id == 1182
    assert gust[0].proof.fact("terminal") is True
    wally = _wally(case)
    assert len(wally) == 1
    resolution = resolve_proposals(
        case[0],
        case[1],
        build_resource_ledger(case[0]),
        gust + wally,
        registry=case[4],
    )
    assert resolution.selected is not None
    assert resolution.selected.action_spec.choices[0].card_id == 1182


def test_unknown_wally_does_not_suppress_judge_and_records_reason():
    case = _case(
        opponent_text="Unsupported coin flip.",
        hand=(1229, 1213),
        opponent_hand=8,
        raw_options=(
            {"type": int(OptionType.PLAY), "index": 0},
            {"type": int(OptionType.PLAY), "index": 1},
            {"type": int(OptionType.ATTACK), "attackId": 982},
        ),
    )
    threat = build_public_opponent_attack_threat(case[0], case[4])

    assert not threat.exact
    assert threat.unknown_reasons == ("UNSUPPORTED_PAYABLE_ATTACK_EFFECT_2001",)
    assert _wally(case) == ()
    draw = enumerate_safe_draw_supporter_routes(
        case[0], case[1], case[2], case[4]
    )
    assert any(row.action_spec.choices[0].card_id == 1213 for row in draw)


def test_two_returned_energy_one_reattach_restores_aura():
    case = _case(
        own_hp=160,
        own_energy=((6, 50), (6, 51)),
        raw_options=(
            {"type": int(OptionType.PLAY), "index": 0},
            {"type": int(OptionType.ATTACK), "attackId": 982},
            {"type": int(OptionType.ATTACK), "attackId": 983},
        ),
    )
    proposals = _wally(case)

    assert len(proposals) == 1
    assert proposals[0].proof.fact("reestablished_attack_id") == 982
    assert proposals[0].proof.fact("reattach_ref")[3] == 50


def test_empty_deck_or_own_unresolved_status_has_no_strong_wally():
    assert _wally(_case(deck_count=0)) == ()
    assert _wally(_case(poisoned=True)) == ()
    assert _wally(_case(burned=True)) == ()
    assert _wally(_case(confused=True)) == ()


def test_current_exact_game_win_blocks_wally():
    case = _case(
        own_hp=160,
        opponent_damage=100,
        opponent_hp=100,
        own_prizes=1,
    )

    assert any(row.exact_game_win for row in case[3].rows)
    assert _wally(case) == ()


def test_attack_catalog_identity_is_separate_and_duplicate_is_unknown():
    clean = _registry(opponent_damage=100)
    changed = _registry(opponent_damage=110)

    assert clean.catalog_sha256 == changed.catalog_sha256
    assert clean.attack_catalog_sha256 != changed.attack_catalog_sha256
    assert clean.digest != changed.digest
    duplicated_attacks = [
        {
            "attackId": profile.attack_id,
            "name": profile.attack_name,
            "text": profile.effect_text,
            "damage": profile.printed_damage,
            "energies": list(profile.energy_cost),
        }
        for profile in clean.attack_profiles
    ]
    duplicate = next(row for row in duplicated_attacks if row["attackId"] == 2001)
    duplicated = build_public_effect_registry(
        tuple(_card_row(meta) for meta in CARD_META_BY_ID.values()),
        (*duplicated_attacks, dict(duplicate)),
    )
    assert duplicated.attack_profile(2001) is None
    assert 2001 in duplicated.ambiguous_attack_ids
