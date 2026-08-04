from dataclasses import replace

import pytest

from mega_lucario_rule_agent.damage import (
    build_bound_damage_table,
    evaluate_attack_damage,
)
from mega_lucario_rule_agent.fallback import (
    FallbackBindError,
    fault_containment_action,
    resolve_forced_or_setup,
    safe_fallback,
    validate_live_action,
)
from mega_lucario_rule_agent.resource_ledger import (
    ReservationKind,
    ResourceLedger,
)
from mega_lucario_rule_agent.state_view import (
    AreaType,
    OptionType,
    PhysicalRef,
    PlayerView,
    PokemonView,
    PublicState,
    SelectContext,
    SelectType,
    SemanticOption,
    SemanticOptionKey,
)


def ref(card_id, serial, owner, zone):
    return PhysicalRef(card_id, serial, owner, int(zone), serial)


def pokemon(card_id, serial, owner, zone, *, energy_serials=(), hp=100):
    return PokemonView(
        ref=ref(card_id, serial, owner, zone),
        hp=hp,
        max_hp=hp,
        appear_this_turn=False,
        energy_types=tuple(6 for _ in energy_serials),
        energy_refs=tuple(
            ref(6, energy_serial, owner, AreaType.ENERGY)
            for energy_serial in energy_serials
        ),
        tool_refs=(),
        pre_evolution_refs=(),
    )


def player(index, *, active=(), bench=(), hand_refs=()):
    return PlayerView(
        index=index,
        active=tuple(active),
        active_slot_count=len(tuple(active)),
        hidden_active_count=0,
        bench=tuple(bench),
        hand_refs=tuple(hand_refs),
        discard_refs=(),
        prize_refs=(),
        prize_count=6,
        deck_count=40,
        hand_count=len(tuple(hand_refs)) if index == 0 else 5,
        bench_max=5,
        poisoned=False,
        burned=False,
        asleep=False,
        paralyzed=False,
        confused=False,
    )


def state(
    *,
    context=SelectContext.MAIN,
    select_type=SelectType.MAIN,
    min_count=1,
    max_count=1,
    own_active=None,
    own_bench=(),
    hand_refs=(),
    opponent_hp=100,
):
    if own_active is None and context != SelectContext.SETUP_ACTIVE_POKEMON:
        own_active = pokemon(678, 10, 0, AreaType.ACTIVE)
    active = () if own_active is None else (own_active,)
    return PublicState(
        game_epoch=3,
        seat=0,
        turn=4,
        turn_action_count=2,
        first_player=0,
        supporter_played=False,
        stadium_played=False,
        energy_attached=False,
        retreated=False,
        result=-1,
        own=player(
            0,
            active=active,
            bench=own_bench,
            hand_refs=hand_refs,
        ),
        opponent=player(
            1,
            active=(pokemon(999, 20, 1, AreaType.ACTIVE, hp=opponent_hp),),
        ),
        stadium_refs=(),
        looking_refs=(),
        select_context=int(context),
        min_count=min_count,
        max_count=max_count,
        effect_ref=None,
        context_ref=None,
        select_type=int(select_type),
        remaining_damage_counter=0,
        remaining_energy_cost=0,
    )


def key(
    option_type,
    *,
    player_index=0,
    card_id=None,
    serial=None,
    zone=None,
    attack_id=None,
    source_index=None,
):
    return SemanticOptionKey(
        option_type=int(option_type),
        player_index=player_index,
        card_id=card_id,
        card_serial=serial,
        source_zone=None if zone is None else int(zone),
        source_index=source_index,
        attack_id=attack_id,
    )


def options(*keys):
    return tuple(
        SemanticOption(index=index, key=value)
        for index, value in enumerate(keys)
    )


def empty_ledger():
    return ResourceLedger(())


def hidden_setup_bench_state(
    hand_refs,
    *,
    min_count=0,
    max_count=5,
    own_bench=(),
):
    current = state(
        context=SelectContext.SETUP_BENCH_POKEMON,
        select_type=SelectType.CARD,
        min_count=min_count,
        max_count=max_count,
        own_bench=own_bench,
        hand_refs=hand_refs,
    )
    return replace(
        current,
        own=replace(
            current.own,
            active=(),
            active_slot_count=1,
            hidden_active_count=1,
        ),
    )


ATTACK_982 = key(OptionType.ATTACK, attack_id=982)
ATTACK_983 = key(OptionType.ATTACK, attack_id=983)
END = key(OptionType.END)
YES = key(OptionType.YES)
NO = key(OptionType.NO)


def test_live_action_validation_rejects_bool_duplicate_range_and_count_errors():
    current = state(context=SelectContext.DISCARD, select_type=SelectType.CARD)
    legal = options(
        key(OptionType.CARD, card_id=6, serial=1, zone=AreaType.HAND),
        key(OptionType.CARD, card_id=6, serial=2, zone=AreaType.HAND),
    )
    assert validate_live_action(current, legal, (0,)) == ()
    assert "ACTION_INDEX_INVALID" in validate_live_action(current, legal, (True,))
    assert "ACTION_INDEX_DUPLICATE" in validate_live_action(current, legal, (0, 0))
    assert "ACTION_INDEX_OUT_OF_RANGE" in validate_live_action(current, legal, (2,))
    assert "ACTION_BELOW_MIN_COUNT" in validate_live_action(
        current,
        legal,
        (),
    )

    malformed = (
        SemanticOption(index=0, key=legal[0].key),
        SemanticOption(index=0, key=legal[1].key),
    )
    assert "LEGAL_OPTION_INDEX_COLLISION" in validate_live_action(
        current,
        malformed,
        (0,),
    )


def test_optional_unsupported_prompt_skips_without_consuming_an_option():
    current = state(
        context=SelectContext.FIRST_EFFECT,
        select_type=SelectType.CARD,
        min_count=0,
        max_count=2,
    )
    legal = options(
        key(OptionType.CARD, card_id=6, serial=1, zone=AreaType.DISCARD),
        key(OptionType.CARD, card_id=6, serial=2, zone=AreaType.DISCARD),
    )
    decision = resolve_forced_or_setup(current, legal, empty_ledger())
    assert decision.reason_code == "UNSUPPORTED_OPTIONAL_SKIP"
    assert decision.unsupported_effect
    assert decision.bind_now(current, legal) == ()

    no_options = resolve_forced_or_setup(current, (), empty_ledger())
    assert no_options.reason_code == "EMPTY_OPTIONAL_PROMPT"
    assert no_options.bind_now(current, ()) == ()

    impossible = replace(current, min_count=1, max_count=1)
    assert resolve_forced_or_setup(impossible, (), empty_ledger()) is None


def test_unsupported_yes_no_declines_independent_of_option_order():
    current = state(
        context=SelectContext.ACTIVATE,
        select_type=SelectType.YES_NO,
    )
    first = options(YES, NO)
    second = options(NO, YES)
    first_decision = resolve_forced_or_setup(current, first, empty_ledger())
    second_decision = resolve_forced_or_setup(current, second, empty_ledger())
    assert first_decision.choices == second_decision.choices == (NO,)
    assert first_decision.bind_now(current, first) == (1,)
    assert second_decision.bind_now(current, second) == (0,)


def test_unique_legal_action_uses_callback_local_raw_locator_only():
    current = state(
        context=SelectContext.FIRST_EFFECT,
        select_type=SelectType.CARD,
    )
    unstable_key = key(
        OptionType.CARD,
        zone=AreaType.LOOKING,
        source_index=3,
    )
    decision = resolve_forced_or_setup(
        current,
        options(unstable_key),
        empty_ledger(),
    )
    assert decision.reason_code == "UNIQUE_LEGAL_ACTION"
    assert decision.bind_now(current, options(unstable_key)) == (0,)
    assert not hasattr(decision, "bound_action")


def test_mandatory_multiselect_uses_minimum_and_places_hard_reservation_last():
    first_ref = ref(6, 31, 0, AreaType.HAND)
    second_ref = ref(6, 32, 0, AreaType.HAND)
    third_ref = ref(6, 33, 0, AreaType.HAND)
    current = state(
        context=SelectContext.DISCARD,
        select_type=SelectType.CARD,
        min_count=2,
        max_count=3,
        hand_refs=(first_ref, second_ref, third_ref),
    )
    first_key = key(OptionType.CARD, card_id=6, serial=31, zone=AreaType.HAND)
    second_key = key(OptionType.CARD, card_id=6, serial=32, zone=AreaType.HAND)
    third_key = key(OptionType.CARD, card_id=6, serial=33, zone=AreaType.HAND)
    ledger = ResourceLedger((first_ref, second_ref, third_ref)).reserve_exact(
        "ONLY_ATTACK_ENERGY",
        ReservationKind.HARD_RESERVED,
        "preserve current attack",
        (first_ref,),
    )
    legal = options(first_key, third_key, second_key)
    decision = resolve_forced_or_setup(current, legal, ledger)
    assert decision.reason_code == "UNSUPPORTED_MANDATORY_MINIMUM"
    assert {value.card_serial for value in decision.choices} == {32, 33}
    assert decision.bind_now(current, legal) == (1, 2)


def test_duplicate_semantics_bind_to_lowest_live_indices_without_persistence():
    current = state(
        context=SelectContext.DISCARD,
        select_type=SelectType.CARD,
        min_count=2,
        max_count=2,
    )
    duplicate = key(
        OptionType.CARD,
        zone=AreaType.LOOKING,
        source_index=0,
    )
    legal = options(duplicate, duplicate)
    decision = resolve_forced_or_setup(current, legal, empty_ledger())
    assert decision.choices == (duplicate, duplicate)
    assert decision.bind_now(current, legal) == (0, 1)


def test_setup_active_uses_required_priority_and_lowest_serial():
    hand = (
        ref(677, 40, 0, AreaType.HAND),
        ref(676, 42, 0, AreaType.HAND),
        ref(676, 41, 0, AreaType.HAND),
        ref(675, 43, 0, AreaType.HAND),
    )
    current = state(
        context=SelectContext.SETUP_ACTIVE_POKEMON,
        select_type=SelectType.CARD,
        own_active=None,
        hand_refs=hand,
    )
    legal = options(
        key(OptionType.CARD, card_id=677, serial=40, zone=AreaType.HAND),
        key(OptionType.CARD, card_id=676, serial=42, zone=AreaType.HAND),
        key(OptionType.CARD, card_id=675, serial=43, zone=AreaType.HAND),
        key(OptionType.CARD, card_id=676, serial=41, zone=AreaType.HAND),
    )
    decision = resolve_forced_or_setup(current, legal, empty_ledger())
    assert decision.reason_code == "SETUP_ACTIVE_PRIORITY"
    assert decision.choices[0].card_id == 676
    assert decision.choices[0].card_serial == 41
    assert decision.bind_now(current, legal) == (3,)


def test_setup_first_chooses_yes():
    first_state = state(
        context=SelectContext.IS_FIRST,
        select_type=SelectType.YES_NO,
    )
    first = resolve_forced_or_setup(
        first_state,
        options(NO, YES),
        empty_ledger(),
    )
    assert first.reason_code == "SETUP_CHOOSE_FIRST"
    assert first.choices == (YES,)



def test_setup_bench_active_solrock_completes_roles_and_holds_duplicates():
    hand = (
        ref(675, 20, 0, AreaType.HAND),
        ref(677, 30, 0, AreaType.HAND),
        ref(677, 31, 0, AreaType.HAND),
        ref(673, 40, 0, AreaType.HAND),
        ref(676, 41, 0, AreaType.HAND),
    )
    current = hidden_setup_bench_state(hand)
    legal = options(
        key(OptionType.CARD, card_id=677, serial=31, zone=AreaType.HAND),
        key(OptionType.CARD, card_id=676, serial=41, zone=AreaType.HAND),
        key(OptionType.CARD, card_id=673, serial=40, zone=AreaType.HAND),
        key(OptionType.CARD, card_id=675, serial=20, zone=AreaType.HAND),
        key(OptionType.CARD, card_id=677, serial=30, zone=AreaType.HAND),
    )
    active = key(
        OptionType.CARD,
        card_id=676,
        serial=10,
        zone=AreaType.HAND,
    )

    decision = resolve_forced_or_setup(
        current,
        legal,
        empty_ledger(),
        setup_active_choice=active,
    )

    assert decision.reason_code == "SETUP_BENCH_ROLE_PLAN"
    assert {
        (choice.card_id, choice.card_serial)
        for choice in decision.choices
    } == {(675, 20), (677, 30), (673, 40)}
    assert decision.bind_now(current, legal) == (2, 3, 4)

    permuted = options(*(option.key for option in reversed(legal)))
    rebound = resolve_forced_or_setup(
        current,
        permuted,
        empty_ledger(),
        setup_active_choice=active,
    )
    assert set(rebound.choices) == set(decision.choices)
    assert rebound.bind_now(current, permuted) == (0, 1, 2)


@pytest.mark.parametrize(
    ("active_card_id", "expected_card_ids"),
    (
        (677, {676, 675, 673}),
        (673, {676, 675, 677}),
    ),
)
def test_setup_bench_nonengine_active_builds_both_engine_halves(
    active_card_id,
    expected_card_ids,
):
    hand = (
        ref(676, 20, 0, AreaType.HAND),
        ref(675, 21, 0, AreaType.HAND),
        ref(677, 22, 0, AreaType.HAND),
        ref(673, 23, 0, AreaType.HAND),
    )
    current = hidden_setup_bench_state(hand)
    legal = options(
        key(OptionType.CARD, card_id=677, serial=22, zone=AreaType.HAND),
        key(OptionType.CARD, card_id=673, serial=23, zone=AreaType.HAND),
        key(OptionType.CARD, card_id=675, serial=21, zone=AreaType.HAND),
        key(OptionType.CARD, card_id=676, serial=20, zone=AreaType.HAND),
    )
    active = key(
        OptionType.CARD,
        card_id=active_card_id,
        serial=10,
        zone=AreaType.HAND,
    )

    decision = resolve_forced_or_setup(
        current,
        legal,
        empty_ledger(),
        setup_active_choice=active,
    )

    assert {choice.card_id for choice in decision.choices} == expected_card_ids
    assert len(decision.choices) == 3


def test_setup_bench_boardout_guard_can_use_only_duplicate_role():
    hand = (ref(676, 20, 0, AreaType.HAND),)
    current = hidden_setup_bench_state(hand)
    legal = options(
        key(OptionType.CARD, card_id=676, serial=20, zone=AreaType.HAND),
    )
    active = key(
        OptionType.CARD,
        card_id=676,
        serial=10,
        zone=AreaType.HAND,
    )

    decision = resolve_forced_or_setup(
        current,
        legal,
        empty_ledger(),
        setup_active_choice=active,
    )

    assert decision.choices == (legal[0].key,)
    assert decision.bind_now(current, legal) == (0,)


def test_setup_bench_without_trusted_active_only_applies_boardout_guard():
    hand = (
        ref(677, 30, 0, AreaType.HAND),
        ref(676, 20, 0, AreaType.HAND),
        ref(675, 21, 0, AreaType.HAND),
        ref(673, 40, 0, AreaType.HAND),
    )
    current = hidden_setup_bench_state(hand)
    legal = options(
        key(OptionType.CARD, card_id=677, serial=30, zone=AreaType.HAND),
        key(OptionType.CARD, card_id=676, serial=20, zone=AreaType.HAND),
        key(OptionType.CARD, card_id=675, serial=21, zone=AreaType.HAND),
        key(OptionType.CARD, card_id=673, serial=40, zone=AreaType.HAND),
    )

    decision = resolve_forced_or_setup(current, legal, empty_ledger())

    assert len(decision.choices) == 1
    assert (decision.choices[0].card_id, decision.choices[0].card_serial) == (
        675,
        21,
    )


def test_setup_bench_min_count_overrides_normal_four_card_limit():
    hand = (
        ref(675, 20, 0, AreaType.HAND),
        ref(677, 30, 0, AreaType.HAND),
        ref(677, 31, 0, AreaType.HAND),
        ref(673, 40, 0, AreaType.HAND),
        ref(676, 41, 0, AreaType.HAND),
    )
    current = hidden_setup_bench_state(hand, min_count=5, max_count=5)
    legal = options(
        *(
            key(
                OptionType.CARD,
                card_id=ref_value.card_id,
                serial=ref_value.serial,
                zone=AreaType.HAND,
            )
            for ref_value in hand
        )
    )
    active = key(
        OptionType.CARD,
        card_id=676,
        serial=10,
        zone=AreaType.HAND,
    )

    decision = resolve_forced_or_setup(
        current,
        legal,
        empty_ledger(),
        setup_active_choice=active,
    )

    assert len(decision.choices) == 5
    assert decision.bind_now(current, legal) == (0, 1, 2, 3, 4)


def test_setup_bench_rejects_nonhand_foreign_unknown_and_duplicate_physical_options():
    hand = (
        ref(675, 20, 0, AreaType.HAND),
        ref(999, 50, 0, AreaType.HAND),
    )
    current = hidden_setup_bench_state(hand)
    valid = key(
        OptionType.CARD,
        card_id=675,
        serial=20,
        zone=AreaType.HAND,
    )
    legal = options(
        key(OptionType.CARD, card_id=675, serial=20, zone=AreaType.DECK),
        key(
            OptionType.CARD,
            player_index=1,
            card_id=675,
            serial=20,
            zone=AreaType.HAND,
        ),
        key(OptionType.CARD, card_id=999, serial=50, zone=AreaType.HAND),
        valid,
        valid,
    )
    active = key(
        OptionType.CARD,
        card_id=676,
        serial=10,
        zone=AreaType.HAND,
    )

    decision = resolve_forced_or_setup(
        current,
        legal,
        empty_ledger(),
        setup_active_choice=active,
    )

    assert decision.choices == (valid,)
    assert decision.bind_now(current, legal) == (3,)


def test_setup_bench_uses_current_seat_instead_of_hardcoded_player_zero():
    hand = (ref(675, 20, 1, AreaType.HAND),)
    current = hidden_setup_bench_state(())
    current = replace(
        current,
        seat=1,
        own=replace(
            current.own,
            index=1,
            hand_refs=hand,
            hand_count=1,
        ),
        opponent=replace(current.opponent, index=0),
    )
    legal = options(
        key(
            OptionType.CARD,
            player_index=1,
            card_id=675,
            serial=20,
            zone=AreaType.HAND,
        ),
    )
    active = key(
        OptionType.CARD,
        player_index=1,
        card_id=676,
        serial=10,
        zone=AreaType.HAND,
    )

    decision = resolve_forced_or_setup(
        current,
        legal,
        empty_ledger(),
        setup_active_choice=active,
    )

    assert decision.choices == (legal[0].key,)


def test_forced_promotion_prefers_uninvested_one_prize_over_riolu_and_mega():
    makuhita = pokemon(673, 30, 0, AreaType.BENCH)
    riolu = pokemon(677, 31, 0, AreaType.BENCH)
    mega = pokemon(678, 32, 0, AreaType.BENCH, energy_serials=(80,))
    current = state(
        context=SelectContext.TO_ACTIVE,
        select_type=SelectType.CARD,
        own_bench=(riolu, mega, makuhita),
    )
    legal = options(
        key(OptionType.CARD, card_id=678, serial=32, zone=AreaType.BENCH),
        key(OptionType.CARD, card_id=677, serial=31, zone=AreaType.BENCH),
        key(OptionType.CARD, card_id=673, serial=30, zone=AreaType.BENCH),
    )
    decision = resolve_forced_or_setup(current, legal, empty_ledger())
    assert decision.reason_code == "FORCED_PROMOTION_LOWEST_LIABILITY"
    assert decision.choices[0].card_id == 673
    assert decision.bind_now(current, legal) == (2,)

    unique_mega = options(legal[0].key)
    unique = resolve_forced_or_setup(current, unique_mega, empty_ledger())
    assert unique.reason_code == "UNIQUE_LEGAL_ACTION"
    assert unique.bind_now(current, unique_mega) == (0,)


def test_safe_main_fallback_never_elevates_legacy_target_only_damage_to_exact_ko():
    current = state(opponent_hp=200)
    legal = options(ATTACK_982, ATTACK_983, END)
    damage = build_bound_damage_table(current, (982, 983))
    outcome = safe_fallback(current, legal, damage, empty_ledger())
    assert len(outcome.proposals) == 2
    assert outcome.resolution.selected == outcome.proposals[0]
    assert outcome.resolution.stats.proposed == 2
    assert outcome.decision.reason_code == "FALLBACK_LEGAL_ATTACK_982"
    assert outcome.decision.bind_now(current, legal) == (0,)
    assert "LEGACY_TARGET_ONLY_DAMAGE_UNTRUSTED" in outcome.reasons

    no_legacy = safe_fallback(current, legal, {}, empty_ledger())
    assert no_legacy.decision.choices == outcome.decision.choices

    unbound_exact = safe_fallback(
        current,
        legal,
        damage.as_dict(),
        empty_ledger(),
    )
    assert unbound_exact.decision.choices == outcome.decision.choices
    assert "DAMAGE_TABLE_UNBOUND" in unbound_exact.reasons
    assert "LEGACY_TARGET_ONLY_DAMAGE_UNTRUSTED" in unbound_exact.reasons

    no_exact = {
        982: evaluate_attack_damage(
            982,
            target_remaining_hp=200,
            unsupported_effects=("UNKNOWN_PUBLIC_SHIELD",),
        ),
        983: evaluate_attack_damage(983, target_remaining_hp=400),
    }
    legal_attack = safe_fallback(current, legal, no_exact, empty_ledger())
    assert legal_attack.decision.reason_code == "FALLBACK_LEGAL_ATTACK_982"
    assert "DAMAGE_TABLE_UNBOUND" in legal_attack.reasons
    assert "LEGACY_TARGET_ONLY_DAMAGE_UNTRUSTED" in legal_attack.reasons

    passed = safe_fallback(current, options(END), {}, empty_ledger())
    assert passed.decision.reason_code == "FALLBACK_PASS"
    assert passed.decision.bind_now(current, options(END)) == (0,)


def test_stale_bound_damage_never_elevates_an_old_exact_ko():
    old_state = state(opponent_hp=200)
    old_damage = build_bound_damage_table(old_state, (982, 983))
    current = state(opponent_hp=100)
    legal = options(ATTACK_982, ATTACK_983, END)

    outcome = safe_fallback(current, legal, old_damage, empty_ledger())

    assert outcome.decision.reason_code == "FALLBACK_LEGAL_ATTACK_982"
    assert "DAMAGE_TABLE_STATE_STALE" in outcome.reasons
    assert "LEGACY_TARGET_ONLY_DAMAGE_UNTRUSTED" in outcome.reasons


def test_main_fallback_rebinds_after_permutation_and_never_uses_raw_order():
    current = state()
    first = options(ATTACK_983, ATTACK_982, END)
    second = options(END, ATTACK_982, ATTACK_983)
    first_outcome = safe_fallback(current, first, {}, empty_ledger())
    second_outcome = safe_fallback(current, second, {}, empty_ledger())
    assert first_outcome.decision.choices == second_outcome.decision.choices == (
        ATTACK_982,
    )
    assert first_outcome.decision.bind_now(current, first) == (1,)
    assert second_outcome.decision.bind_now(current, second) == (1,)


def test_duplicate_main_attack_is_not_treated_as_a_unique_safe_action():
    current = state()
    legal = options(ATTACK_982, ATTACK_982, END)
    outcome = safe_fallback(current, legal, {}, empty_ledger())
    assert outcome.decision.reason_code == "FALLBACK_PASS"
    assert "DUPLICATE_SEMANTIC_ATTACK" in outcome.reasons


def test_fault_containment_marks_the_action_and_never_acts_on_stable_main():
    effect_state = state(
        context=SelectContext.ACTIVATE,
        select_type=SelectType.YES_NO,
    )
    decision = fault_containment_action(
        effect_state,
        options(YES, NO),
        empty_ledger(),
    )
    assert decision.fault_containment
    assert decision.unsupported_effect
    assert decision.reason_code == "IRREVERSIBLE_FAULT:UNSUPPORTED_EFFECT_DECLINE"
    assert decision.bind_now(effect_state, options(YES, NO)) == (1,)
    assert (
        fault_containment_action(
            state(),
            options(ATTACK_982, END),
            empty_ledger(),
        )
        is None
    )


def test_decision_bind_fails_closed_when_prompt_changes():
    current = state(
        context=SelectContext.ACTIVATE,
        select_type=SelectType.YES_NO,
    )
    decision = resolve_forced_or_setup(
        current,
        options(YES, NO),
        empty_ledger(),
    )
    with pytest.raises(FallbackBindError, match="SEMANTIC_CHOICE_NOT_FOUND"):
        decision.bind_now(current, options(YES))


def test_invalid_damage_table_is_rejected_before_policy_selection():
    current = state()
    with pytest.raises(ValueError, match="match"):
        safe_fallback(
            current,
            options(ATTACK_982),
            {982: evaluate_attack_damage(983, target_remaining_hp=100)},
            empty_ledger(),
        )
