from copy import deepcopy
from types import SimpleNamespace

import pytest

from mega_lucario_rule_agent.state_view import (
    ActionSpec,
    AreaType,
    OptionType,
    SelectContext,
    SelectType,
    SemanticBindError,
    build_public_state,
    build_semantic_options,
    is_stable_main_state,
    make_prompt_fingerprint,
    public_state_fingerprint,
)


def card(card_id, serial, player=0):
    return {"id": card_id, "serial": serial, "playerIndex": player}


def pokemon(card_id, serial, player=0, hp=100, energies=None, pre=None):
    energies = energies or []
    return {
        "id": card_id,
        "serial": serial,
        "playerIndex": player,
        "hp": hp,
        "maxHp": hp,
        "appearThisTurn": False,
        "energies": [6 for _ in energies],
        "energyCards": [card(6, value, player) for value in energies],
        "tools": [],
        "preEvolution": pre or [],
    }


def observation(options, context=SelectContext.MAIN, min_count=1, max_count=1):
    return {
        "select": {
            "type": 0,
            "context": int(context),
            "minCount": min_count,
            "maxCount": max_count,
            "option": options,
            "deck": None,
            "contextCard": None,
            "effect": None,
        },
        "logs": [],
        "current": {
            "turn": 3,
            "turnActionCount": 4,
            "yourIndex": 0,
            "firstPlayer": 0,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": False,
            "retreated": False,
            "result": -1,
            "stadium": [],
            "looking": None,
            "players": [
                {
                    "active": [pokemon(676, 10, hp=110)],
                    "bench": [pokemon(677, 20, hp=80)],
                    "benchMax": 5,
                    "deckCount": 40,
                    "discard": [card(6, 70)],
                    "prize": [None] * 6,
                    "handCount": 3,
                    "hand": [card(673, 31), card(673, 32), card(6, 33)],
                    "poisoned": False,
                    "burned": False,
                    "asleep": False,
                    "paralyzed": False,
                    "confused": False,
                },
                {
                    "active": [pokemon(100, 110, player=1, hp=100)],
                    "bench": [],
                    "benchMax": 5,
                    "deckCount": 40,
                    "discard": [],
                    "prize": [None] * 6,
                    "handCount": 5,
                    "hand": None,
                    "poisoned": False,
                    "burned": False,
                    "asleep": False,
                    "paralyzed": False,
                    "confused": False,
                },
            ],
        },
    }


def namespace_tree(value):
    if isinstance(value, dict):
        return SimpleNamespace(**{key: namespace_tree(item) for key, item in value.items()})
    if isinstance(value, list):
        return [namespace_tree(item) for item in value]
    return value


def hand_card_option(index):
    return {
        "type": int(OptionType.CARD),
        "area": int(AreaType.HAND),
        "index": index,
        "playerIndex": 0,
    }


def test_same_card_id_different_serial_binds_physical_copy_after_permutation():
    obs = observation([hand_card_option(0), hand_card_option(1)])
    semantic = build_semantic_options(obs)
    wanted = ActionSpec.single(semantic[1].key)
    assert wanted.bind(semantic, 1, 1) == [1]

    permuted = deepcopy(obs)
    permuted["current"]["players"][0]["hand"][0:2] = list(
        reversed(permuted["current"]["players"][0]["hand"][0:2])
    )
    permuted["select"]["option"] = [hand_card_option(0), hand_card_option(1)]
    rebound = build_semantic_options(permuted)
    assert wanted.bind(rebound, 1, 1) == [0]


def test_ambiguous_semantic_key_fails_closed():
    obs = observation([hand_card_option(0), hand_card_option(1)])
    obs["current"]["players"][0]["hand"][1] = card(673, 31)
    semantic = build_semantic_options(obs)
    with pytest.raises(SemanticBindError):
        ActionSpec.single(semantic[0].key).bind(semantic, 1, 1)


def test_multiselect_rebinds_two_distinct_serials_and_enforces_counts():
    obs = observation(
        [hand_card_option(0), hand_card_option(2), hand_card_option(1)],
        context=SelectContext.DISCARD,
        min_count=2,
        max_count=2,
    )
    semantic = build_semantic_options(obs)
    spec = ActionSpec((semantic[0].key, semantic[2].key))
    assert spec.bind(semantic, 2, 2) == [0, 2]
    with pytest.raises(SemanticBindError):
        ActionSpec.single(semantic[0].key).bind(semantic, 2, 2)


def test_energy_unit_count_is_part_of_semantic_identity():
    obs = observation(
        [
            {
                "type": int(OptionType.ENERGY),
                "area": int(AreaType.ACTIVE),
                "index": 0,
                "energyIndex": 0,
                "count": 1,
            },
            {
                "type": int(OptionType.ENERGY),
                "area": int(AreaType.ACTIVE),
                "index": 0,
                "energyIndex": 0,
                "count": 2,
            },
        ]
    )
    obs["current"]["players"][0]["active"][0] = pokemon(
        676, 10, hp=110, energies=[71]
    )
    options = build_semantic_options(obs)
    assert options[0].key.card_serial == options[1].key.card_serial == 71
    assert options[0].key.energy_count == 1
    assert options[1].key.energy_count == 2
    assert options[0].key != options[1].key


def test_attack_and_evolution_target_use_stable_semantics():
    attack_obs = observation(
        [
            {"type": int(OptionType.ATTACK), "attackId": 983},
            {"type": int(OptionType.ATTACK), "attackId": 982},
        ],
        context=SelectContext.MAIN,
    )
    attacks = build_semantic_options(attack_obs)
    assert attacks[0].key.attack_id == 983
    assert attacks[1].key.attack_id == 982

    evolve_obs = observation(
        [
            {
                "type": int(OptionType.EVOLVE),
                "area": int(AreaType.HAND),
                "index": 0,
                "playerIndex": 0,
                "inPlayArea": int(AreaType.BENCH),
                "inPlayIndex": 0,
            }
        ]
    )
    evolve_obs["current"]["players"][0]["hand"][0] = card(678, 90)
    options = build_semantic_options(evolve_obs)
    assert options[0].key.card_serial == 90
    assert options[0].key.target_lineage_serial == 20

    evolve_obs["current"]["players"][0]["bench"].append(pokemon(677, 21, hp=80))
    wanted = ActionSpec.single(build_semantic_options(evolve_obs)[0].key)
    evolve_obs["current"]["players"][0]["bench"].reverse()
    evolve_obs["select"]["option"][0]["inPlayIndex"] = 1
    assert wanted.bind(build_semantic_options(evolve_obs), 1, 1) == [0]


def test_prompt_fingerprint_ignores_option_order_but_preserves_multiplicity():
    obs = observation([hand_card_option(0), hand_card_option(1)])
    state = build_public_state(obs, game_epoch=7)
    options = build_semantic_options(obs)
    first = make_prompt_fingerprint(state, options, owner_kind="SEARCH", stage="TARGET")

    permuted_options = tuple(reversed(options))
    second = make_prompt_fingerprint(
        state, permuted_options, owner_kind="SEARCH", stage="TARGET"
    )
    assert first.digest() == second.digest()

    duplicate = make_prompt_fingerprint(
        state, options + (options[0],), owner_kind="SEARCH", stage="TARGET"
    )
    assert duplicate.digest() != first.digest()


def test_main_prompt_fingerprint_changes_with_public_board_state():
    obs = observation([hand_card_option(0)])
    first_state = build_public_state(obs)
    first = make_prompt_fingerprint(first_state, build_semantic_options(obs))

    damaged = deepcopy(obs)
    damaged["current"]["players"][1]["active"][0]["hp"] = 60
    second_state = build_public_state(damaged)
    second = make_prompt_fingerprint(second_state, build_semantic_options(damaged))
    assert second.digest() != first.digest()

    energized = deepcopy(obs)
    energized["current"]["players"][0]["active"][0] = pokemon(
        676, 10, hp=110, energies=[72]
    )
    third_state = build_public_state(energized)
    third = make_prompt_fingerprint(third_state, build_semantic_options(energized))
    assert third.digest() != first.digest()


def test_dict_and_dataclass_like_observations_normalize_identically():
    obs = observation([hand_card_option(0), hand_card_option(1)])
    object_obs = namespace_tree(deepcopy(obs))
    dict_state = build_public_state(obs, game_epoch=9)
    object_state = build_public_state(object_obs, game_epoch=9)
    assert dict_state == object_state
    assert tuple(option.key for option in build_semantic_options(obs)) == tuple(
        option.key for option in build_semantic_options(object_obs)
    )


def test_state_fingerprint_is_deterministic_and_public_opponent_hand_only():
    obs = observation([hand_card_option(0)])
    obs["current"]["players"][1]["hand"] = [card(999, 999, player=1)]
    first = build_public_state(obs, game_epoch=2)
    second = build_public_state(deepcopy(obs), game_epoch=2)
    assert public_state_fingerprint(first) == public_state_fingerprint(second)
    assert first.opponent.hand_refs == ()
    assert first.opponent.hand_count == 5
    assert first.own.prize_count == 6
    assert first.opponent.prize_count == 6
    assert first.first_player == 0


def test_incomplete_own_hand_fails_closed():
    obs = observation([hand_card_option(0)])
    obs["current"]["players"][0]["hand"] = None
    with pytest.raises(ValueError, match="own hand"):
        build_public_state(obs)


def test_facedown_active_slot_count_is_preserved_without_identity():
    obs = observation([hand_card_option(0)])
    obs["current"]["players"][1]["active"] = [None]
    state = build_public_state(obs)
    assert state.opponent.active == ()
    assert state.opponent.active_slot_count == 1
    assert state.opponent.hidden_active_count == 1

    obs = observation([hand_card_option(0)])
    obs["current"]["players"][0]["handCount"] = 4
    with pytest.raises(ValueError, match="own hand"):
        build_public_state(obs)


def test_play_option_infers_hand_source_and_preserves_zero_result():
    obs = observation([{"type": int(OptionType.PLAY), "index": 0}])
    obs["current"]["result"] = 0
    state = build_public_state(obs)
    option = build_semantic_options(obs)[0]
    assert state.result == 0
    assert option.key.source_zone == int(AreaType.HAND)
    assert option.key.card_id == 673
    assert option.key.card_serial == 31


def test_facedown_prize_slots_rebind_by_public_slot_not_option_position():
    obs = observation(
        [
            {
                "type": int(OptionType.CARD),
                "area": int(AreaType.PRIZE),
                "index": 0,
                "playerIndex": 0,
            },
            {
                "type": int(OptionType.CARD),
                "area": int(AreaType.PRIZE),
                "index": 1,
                "playerIndex": 0,
            },
        ],
        context=SelectContext.TO_HAND,
    )
    options = build_semantic_options(obs)
    wanted = ActionSpec.single(options[1].key)
    assert options[1].key.card_serial is None
    assert options[1].key.source_index == 1
    assert wanted.bind(options, 1, 1) == [1]

    permuted = deepcopy(obs)
    permuted["select"]["option"].reverse()
    assert wanted.bind(build_semantic_options(permuted), 1, 1) == [0]


def test_zero_selection_action_is_legal_only_with_matching_minimum():
    obs = observation([], min_count=0, max_count=1)
    options = build_semantic_options(obs)
    assert ActionSpec.empty().bind(options, 0, 1) == []
    with pytest.raises(SemanticBindError):
        ActionSpec.empty().bind(options, 1, 1)


def test_selection_surface_flags_distinguish_closed_and_empty_open_zones():
    obs = observation([hand_card_option(0)])
    closed_state = build_public_state(obs)
    closed_prompt = make_prompt_fingerprint(
        closed_state,
        build_semantic_options(obs),
    )
    assert closed_state.select_type == int(SelectType.MAIN)
    assert not closed_state.looking_open
    assert not closed_state.select_deck_open

    opened = deepcopy(obs)
    opened["current"]["looking"] = []
    opened["select"]["deck"] = []
    opened_state = build_public_state(opened)
    opened_prompt = make_prompt_fingerprint(
        opened_state,
        build_semantic_options(opened),
    )
    assert opened_state.looking_refs == ()
    assert opened_state.looking_open
    assert opened_state.select_deck_open
    assert public_state_fingerprint(opened_state) != public_state_fingerprint(
        closed_state
    )
    assert opened_prompt.digest() != closed_prompt.digest()

    card_select = deepcopy(obs)
    card_select["select"]["type"] = int(SelectType.CARD)
    card_state = build_public_state(card_select)
    assert public_state_fingerprint(card_state) != public_state_fingerprint(
        closed_state
    )


def test_stable_main_requires_a_fully_closed_main_selection_surface():
    obs = observation([hand_card_option(0)])
    stable = build_public_state(obs)
    assert is_stable_main_state(stable)

    variants = []
    card_select = deepcopy(obs)
    card_select["select"]["type"] = int(SelectType.CARD)
    variants.append(card_select)
    looking = deepcopy(obs)
    looking["current"]["looking"] = []
    variants.append(looking)
    deck_select = deepcopy(obs)
    deck_select["select"]["deck"] = []
    variants.append(deck_select)
    effect = deepcopy(obs)
    effect["select"]["effect"] = card(1121, 99)
    variants.append(effect)
    wrong_counts = deepcopy(obs)
    wrong_counts["select"]["minCount"] = 0
    variants.append(wrong_counts)

    assert all(
        not is_stable_main_state(build_public_state(variant))
        for variant in variants
    )
