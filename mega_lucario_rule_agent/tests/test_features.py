from copy import deepcopy
from dataclasses import replace

import pytest

from mega_lucario_rule_agent.features import (
    PublicMatchupFlag,
    build_deck_features,
    build_resource_ledger,
)
from mega_lucario_rule_agent.state_view import (
    LogType,
    OptionType,
    PublicHistoryTracker,
    build_public_state,
    build_semantic_options,
)
from mega_lucario_rule_agent.tests.test_attack_outcomes import (
    EFFECT_TEXT,
    card,
    checked_state,
    observation,
    pokemon,
    pokemon_catalog_row,
    registry_for,
)


def own_support_rows():
    return (
        pokemon_catalog_row(675, "Lunatone", hp=110),
        pokemon_catalog_row(676, "Solrock", hp=110),
        pokemon_catalog_row(677, "Riolu", hp=80),
    )


def feature_observation():
    obs = observation(
        (982,),
        own_active=pokemon(
            678,
            10,
            hp=200,
            max_hp=340,
            energy_cards=((6, 101),),
        ),
        own_bench=(
            pokemon(676, 11, hp=110),
            pokemon(
                675,
                12,
                hp=110,
                energy_cards=((6, 102), (6, 103)),
            ),
            pokemon(677, 13, hp=80),
        ),
        own_discard=(card(6, 104),),
        opponent_active=pokemon(
            849,
            20,
            player=1,
            hp=450,
            max_hp=450,
        ),
    )
    obs["current"]["players"][0]["hand"] = [
        card(6, 105),
        card(678, 106),
        card(1229, 107),
    ]
    obs["current"]["players"][0]["handCount"] = 3
    obs["current"]["players"][1]["handCount"] = 8
    obs["select"]["option"].append(
        {
            "type": int(OptionType.PLAY),
            "playerIndex": 0,
            "area": 2,
            "index": 2,
        }
    )
    obs["select"]["option"].append(
        {
            "type": int(OptionType.SKILL),
            "playerIndex": 0,
            "cardId": 675,
            "serial": 12,
        }
    )
    return obs


def feature_registry():
    return registry_for(
        (982,),
        target_row=pokemon_catalog_row(
            849,
            "Mega Lopunny ex",
            hp=450,
            weakness=6,
            basic=False,
            stage1=True,
            mega_ex=True,
        ),
        extra_rows=own_support_rows(),
    )


def test_deck_features_bind_the_exact_state_options_and_registry():
    obs = feature_observation()
    registry = feature_registry()
    state = checked_state(obs)
    options = build_semantic_options(obs)

    features = build_deck_features(state, options, registry)

    assert features.matches(state, tuple(reversed(options)), registry)
    assert features.verify_integrity()
    assert len(features.digest()) == 64
    assert features.engine_complete
    assert features.missing_engine_card_ids == ()
    assert features.lucario_line_count == 2
    assert features.mega_count == 1
    assert features.hariyama_line_count == 0
    assert features.ready_now
    assert features.legal_attack_ids == (982,)
    assert features.ready_attacker_count == 2
    assert features.ready_non_ex_attacker_count == 1
    assert features.next_turn_ready_attacker_count == 2
    assert features.hand_fighting_energy_count == 1
    assert features.discard_fighting_energy_count == 1
    assert features.safe_bench_slots == 1
    assert not features.board_out_risk
    assert features.mega_brave_locked is False
    assert features.wally_reboot_candidate
    assert features.wally_reboot_feasible is None
    assert features.lunar_cycle_feasible
    assert features.draw_buffer_after_plan == 39
    assert features.own_turn_number == 2
    assert set(features.public_flags) == {
        PublicMatchupFlag.FIGHTING_WEAK_HIGH_PRIZE,
        PublicMatchupFlag.LARGE_PUBLIC_HAND,
    }
    deficits = {
        value.current_card_id: value.deficit_now
        for value in features.attack_energy_deficit_by_target
    }
    assert deficits == {675: 0, 676: 1, 677: 1, 678: 0}

    fewer_options = options[:-1]
    assert not features.matches(state, fewer_options, registry)
    with pytest.raises(ValueError, match="same observation"):
        build_deck_features(state, fewer_options, registry)

    changed_registry = registry_for(
        (982,),
        target_row=pokemon_catalog_row(
            849,
            "Mega Lopunny ex",
            hp=450,
            weakness=None,
            basic=False,
            stage1=True,
            mega_ex=True,
        ),
        extra_rows=own_support_rows(),
    )
    assert not features.matches(state, options, changed_registry)

    tampered = replace(features, ready_attacker_count=99)
    assert not tampered.verify_integrity()
    assert not tampered.matches(state, options, registry)


def test_feature_resource_ledger_contains_only_exact_visible_own_cards():
    obs = feature_observation()
    state = checked_state(obs)

    ledger = build_resource_ledger(state)

    assert ledger.owner == 0
    assert ledger.visible_count((6,)) == 5
    assert ledger.visible_count((1229,)) == 1
    assert all(ref_value.owner == state.seat for ref_value in ledger.visible_refs)


def test_mega_brave_lock_uses_public_lineage_history_only():
    obs = feature_observation()
    registry = feature_registry()
    state = checked_state(obs, previous_attack=983)
    options = build_semantic_options(obs)

    features = build_deck_features(state, options, registry)

    assert state.history_complete
    assert features.mega_brave_locked is True

    tracker = PublicHistoryTracker()
    initial = deepcopy(obs)
    initial["current"]["turn"] = 1
    initial["current"]["turnActionCount"] = 0
    initial["logs"] = [
        {
            "type": int(LogType.ATTACK),
            "playerIndex": 0,
            "cardId": 678,
            "serial": 10,
            "attackId": 983,
        }
    ]
    build_public_state(initial, game_epoch=7, history_tracker=tracker)
    switched = deepcopy(obs)
    switched["current"]["players"][0]["active"][0]["serial"] = 14
    switched["logs"] = []
    switched_state = build_public_state(
        switched,
        game_epoch=7,
        history_tracker=tracker,
    )
    switched_options = build_semantic_options(switched)
    switched_features = build_deck_features(
        switched_state,
        switched_options,
        registry,
    )
    assert switched_features.mega_brave_locked is False


def test_public_matchup_flags_use_visible_cards_not_archetype_names():
    crustle = pokemon_catalog_row(
        345,
        "Crustle",
        hp=150,
        basic=False,
        stage1=True,
        skills=(
            {
                "name": "Mysterious Rock Inn",
                "text": EFFECT_TEXT["MYSTERIOUS_ROCK_INN"],
            },
        ),
    )
    dragapult = pokemon_catalog_row(
        121,
        "Dragapult ex",
        hp=320,
        basic=False,
        stage2=True,
        ex=True,
    )
    registry = registry_for(
        (982,),
        target_row=crustle,
        extra_rows=own_support_rows() + (dragapult,),
    )
    obs = feature_observation()
    obs["current"]["players"][1]["active"] = [
        pokemon(345, 20, player=1, hp=150)
    ]
    obs["current"]["players"][1]["bench"] = [
        pokemon(121, 21, player=1, hp=320)
    ]
    state = checked_state(obs)
    options = build_semantic_options(obs)

    features = build_deck_features(state, options, registry)

    assert PublicMatchupFlag.EX_DAMAGE_PREVENTION in features.public_flags
    assert PublicMatchupFlag.BENCH_SPREAD_THREAT in features.public_flags
    assert features.public_damage_prevention is True
    assert features.public_bench_damage_threat is True
    assert features.public_gust_or_lock_threat is None
    assert "PUBLIC_GUST_OR_LOCK_THREAT_NOT_PROVEN" in features.unknown_reasons

    safeguard = pokemon_catalog_row(
        330,
        "Sylveon",
        hp=120,
        skills=(
            {
                "name": "Safeguard",
                "text": EFFECT_TEXT["MYSTERIOUS_ROCK_INN"],
            },
        ),
    )
    safeguard_registry = registry_for(
        (982,),
        target_row=safeguard,
        extra_rows=own_support_rows(),
    )
    safeguard_obs = feature_observation()
    safeguard_obs["current"]["players"][1]["active"] = [
        pokemon(330, 20, player=1, hp=120)
    ]
    safeguard_state = checked_state(safeguard_obs)
    safeguard_options = build_semantic_options(safeguard_obs)
    safeguard_features = build_deck_features(
        safeguard_state,
        safeguard_options,
        safeguard_registry,
    )
    assert PublicMatchupFlag.EX_DAMAGE_PREVENTION in (
        safeguard_features.public_flags
    )
    assert safeguard_features.public_damage_prevention is True


def test_lunar_cycle_requires_a_legal_skill_energy_and_draw_buffer():
    obs = feature_observation()
    registry = feature_registry()

    no_skill = deepcopy(obs)
    no_skill["select"]["option"] = no_skill["select"]["option"][:-1]
    no_skill_state = checked_state(no_skill)
    no_skill_options = build_semantic_options(no_skill)
    assert not build_deck_features(
        no_skill_state,
        no_skill_options,
        registry,
    ).lunar_cycle_feasible

    short_deck = deepcopy(obs)
    short_deck["current"]["players"][0]["deckCount"] = 3
    short_deck_state = checked_state(short_deck)
    short_deck_options = build_semantic_options(short_deck)
    assert not build_deck_features(
        short_deck_state,
        short_deck_options,
        registry,
    ).lunar_cycle_feasible

    no_energy = deepcopy(obs)
    no_energy["current"]["players"][0]["hand"] = [
        card(678, 106),
        card(1229, 107),
    ]
    no_energy["current"]["players"][0]["handCount"] = 2
    no_energy_state = checked_state(no_energy)
    no_energy_options = build_semantic_options(no_energy)
    no_energy_features = build_deck_features(
        no_energy_state,
        no_energy_options,
        registry,
    )
    assert not no_energy_features.lunar_cycle_feasible
    assert no_energy_features.next_turn_ready_attacker_count == 1

    only_attach_energy = deepcopy(obs)
    only_attach_energy["current"]["players"][0]["active"][0]["energies"] = []
    only_attach_energy["current"]["players"][0]["active"][0]["energyCards"] = []
    only_attach_energy["current"]["players"][0]["hand"] = [card(6, 105)]
    only_attach_energy["current"]["players"][0]["handCount"] = 1
    only_attach_energy["select"]["option"] = [
        only_attach_energy["select"]["option"][-1]
    ]
    only_attach_state = checked_state(only_attach_energy)
    only_attach_options = build_semantic_options(only_attach_energy)
    assert not build_deck_features(
        only_attach_state,
        only_attach_options,
        registry,
    ).lunar_cycle_feasible


def test_wally_reboot_is_only_a_publicly_legal_candidate_not_a_survival_claim():
    obs = feature_observation()
    registry = feature_registry()
    state = checked_state(obs)
    options = build_semantic_options(obs)
    features = build_deck_features(state, options, registry)

    assert features.wally_reboot_candidate
    assert features.wally_reboot_feasible is None
    assert "WALLY_REBOOT_SURVIVAL_NOT_PROVEN" in features.unknown_reasons

    no_wally_option = deepcopy(obs)
    no_wally_option["select"]["option"] = (
        no_wally_option["select"]["option"][:1]
        + no_wally_option["select"]["option"][2:]
    )
    no_wally_state = checked_state(no_wally_option)
    no_wally_options = build_semantic_options(no_wally_option)
    no_wally_features = build_deck_features(
        no_wally_state,
        no_wally_options,
        registry,
    )
    assert not no_wally_features.wally_reboot_candidate


def test_features_reject_incomplete_combat_source_instead_of_defaulting_facts():
    obs = feature_observation()
    del obs["current"]["energyAttached"]
    state = checked_state(obs)
    options = build_semantic_options(obs)

    assert not state.source_combat_complete
    with pytest.raises(ValueError, match="complete public combat"):
        build_deck_features(state, options, feature_registry())
