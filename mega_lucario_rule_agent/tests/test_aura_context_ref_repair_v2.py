from dataclasses import replace

import pytest

from mega_lucario_rule_agent.state_view import (
    ActionSpec,
    AreaType,
    LogType,
    OptionType,
    PhysicalRef,
    PlayerView,
    PokemonView,
    PublicReceiptEvent,
    PublicState,
    SelectContext,
    SelectType,
    SemanticOption,
    SemanticOptionKey,
)
from mega_lucario_rule_agent.transactions import (
    AURA_CTXREF_BIND_RULE,
    AURA_CTXREF_CAPTURE_RULE,
    AURA_CTXREF_COMPLETE_RULE,
    AURA_CTXREF_OWNER_RULE,
    AURA_CTXREF_RELEASE_RULE,
    ResumeStatus,
    StartStatus,
    TransactionPlan,
    TransactionStage,
    TransactionStep,
    TransactionStore,
    OwnerKind,
    build_aura_jab_plan,
    _prompt_match_reasons,
)


PROOF_DIGEST = "0" * 64


def _ref(card_id, serial, owner, zone, lineage=None):
    return PhysicalRef(
        card_id,
        serial,
        owner,
        int(zone),
        serial if lineage is None else lineage,
    )


def _pokemon(card_id, serial, owner, zone, *, energies=()):
    return PokemonView(
        ref=_ref(card_id, serial, owner, zone),
        hp=100,
        max_hp=100,
        appear_this_turn=False,
        energy_types=tuple(1 for _ in energies),
        energy_refs=tuple(energies),
        tool_refs=(),
        pre_evolution_refs=(),
    )


def _player(index, active, bench=(), hand=(), discard=()):
    return PlayerView(
        index=index,
        active=(active,),
        active_slot_count=1,
        hidden_active_count=0,
        bench=tuple(bench),
        hand_refs=tuple(hand),
        discard_refs=tuple(discard),
        prize_refs=(),
        prize_count=6,
        deck_count=40,
        hand_count=len(hand) if index == 0 else 5,
        bench_max=5,
        poisoned=False,
        burned=False,
        asleep=False,
        paralyzed=False,
        confused=False,
    )


def _state(
    own,
    opponent,
    *,
    turn_action_count=8,
    turn=5,
    game_epoch=9,
    context=SelectContext.MAIN,
    select_type=SelectType.MAIN,
    min_count=1,
    max_count=1,
    effect_ref=None,
    context_ref=None,
    events=(),
    result=-1,
):
    return PublicState(
        game_epoch=game_epoch,
        seat=0,
        turn=turn,
        turn_action_count=turn_action_count,
        first_player=0,
        supporter_played=False,
        stadium_played=False,
        energy_attached=False,
        retreated=False,
        result=result,
        own=own,
        opponent=opponent,
        stadium_refs=(),
        looking_refs=(),
        select_context=int(context),
        min_count=min_count,
        max_count=max_count,
        effect_ref=effect_ref,
        context_ref=context_ref,
        select_type=int(select_type),
        looking_open=False,
        select_deck_open=False,
        remaining_damage_counter=0,
        remaining_energy_cost=0,
        receipt_events=tuple(events),
    )


def _option(index, key):
    return SemanticOption(index=index, key=key)


def _card_key(ref_value):
    return SemanticOptionKey(
        option_type=int(OptionType.CARD),
        player_index=ref_value.owner,
        card_id=ref_value.card_id,
        card_serial=ref_value.serial,
        source_zone=ref_value.zone,
        source_lineage_serial=(
            ref_value.lineage_serial
            if ref_value.zone in (int(AreaType.ACTIVE), int(AreaType.BENCH))
            else None
        ),
    )


def _attack_key():
    return SemanticOptionKey(
        option_type=int(OptionType.ATTACK),
        player_index=0,
        attack_id=982,
    )


def _event(log_type, ref_value, *, attack_id=None, target=None):
    return PublicReceiptEvent(
        log_type=int(log_type),
        player_index=0,
        card_id=ref_value.card_id,
        serial=ref_value.serial,
        from_area=None,
        to_area=None,
        card_id_target=None if target is None else target.card_id,
        serial_target=None if target is None else target.serial,
        serial_bench=None,
        attack_id=attack_id,
        value=None,
    )


def _aura_case(energy_count=1):
    mega = _pokemon(678, 30, 0, AreaType.ACTIVE)
    target = _pokemon(675, 21, 0, AreaType.BENCH)
    energies = tuple(
        _ref(6, 7 + index, 0, AreaType.DISCARD)
        for index in range(energy_count)
    )
    own = _player(0, mega, (target,), discard=energies)
    opponent = _player(1, _pokemon(999, 90, 1, AreaType.ACTIVE))
    base = _state(own, opponent)
    plan = build_aura_jab_plan(
        base,
        ActionSpec.single(_attack_key()),
        energies,
        target.ref,
        PROOF_DIGEST,
    )
    return base, plan, mega.ref, target.ref, energies


def _start(base, plan):
    store = TransactionStore()
    started = store.start(
        plan,
        base,
        (_option(0, plan.initiation.action_spec.choices[0]),),
    )
    assert started.status == StartStatus.STARTED
    return store


def _energy_prompt(base, mega_ref, energies):
    own = base.own
    return _state(
        own,
        base.opponent,
        turn_action_count=9,
        context=SelectContext.ATTACH_TO,
        select_type=SelectType.CARD,
        min_count=0,
        max_count=len(energies),
        effect_ref=mega_ref,
    )


def _target_prompt(base, mega_ref, target_ref, context_ref, *, action_count=10, options=None, context=SelectContext.ATTACH_FROM):
    if options is None:
        options = (_option(0, _card_key(target_ref)),)
    return _state(
        base.own,
        base.opponent,
        turn_action_count=action_count,
        context=context,
        select_type=SelectType.CARD,
        min_count=1,
        max_count=1,
        effect_ref=mega_ref,
        context_ref=context_ref,
    ), tuple(options)


def _completed_state(base, target_ref, energies, *, turn=5, game_epoch=9):
    target = replace(
        base.own.bench[0],
        energy_refs=tuple(energies),
        energy_types=tuple(1 for _ in energies),
    )
    own = replace(
        base.own,
        bench=(target,),
        discard_refs=(),
    )
    events = (
        _event(LogType.ATTACK, base.own.active[0].ref, attack_id=982),
    ) + tuple(
        _event(LogType.ATTACH, energy, target=target_ref)
        for energy in energies
    )
    return _state(
        own,
        base.opponent,
        turn_action_count=11,
        turn=turn,
        game_epoch=game_epoch,
        events=events,
    )


def _run_to_target(energy_count=1, *, context_ref=None, options=None, context=SelectContext.ATTACH_FROM):
    base, plan, mega_ref, target_ref, energies = _aura_case(energy_count)
    store = _start(base, plan)
    energy_result = store.resume(
        _energy_prompt(base, mega_ref, energies),
        tuple(_option(index, _card_key(ref_value)) for index, ref_value in enumerate(energies)),
    )
    assert energy_result.status == ResumeStatus.ADVANCED_ISSUE
    actual_ref = energies[0] if context_ref is None else context_ref
    target_state, target_options = _target_prompt(
        base,
        mega_ref,
        target_ref,
        actual_ref,
        options=options,
        context=context,
    )
    return store, base, plan, mega_ref, target_ref, energies, target_state, target_options


def test_fixture_static_target_would_reproduce_the_old_fault():
    base, plan, mega_ref, target_ref, energies = _aura_case()
    old_target_step = plan.steps[1]
    target_state, target_options = _target_prompt(
        base, mega_ref, target_ref, energies[0]
    )
    assert old_target_step.expected_context_ref is None
    reasons, _, _ = _prompt_match_reasons(
        target_state,
        target_options,
        old_target_step,
    )
    assert reasons == ("UNEXPECTED_CONTEXT_REF",)


def test_exact_post_energy_ref_binds_target_and_completes():
    store, base, plan, mega_ref, target_ref, energies, target_state, target_options = _run_to_target()
    issued = store.resume(target_state, target_options)
    assert issued.status == ResumeStatus.ADVANCED_ISSUE
    assert issued.owner.expected_context_ref == energies[0]
    assert set(issued.reasons) == {
        AURA_CTXREF_CAPTURE_RULE,
        AURA_CTXREF_OWNER_RULE,
        AURA_CTXREF_BIND_RULE,
    }

    completed = store.resume(_completed_state(base, target_ref, energies), ())
    assert completed.status == ResumeStatus.COMPLETED
    assert set(completed.reasons) == {
        AURA_CTXREF_COMPLETE_RULE,
        AURA_CTXREF_RELEASE_RULE,
    }
    assert not store.has_owner
    assert not store.run_fault_latched


def test_context_ref_without_transient_zone_binds_using_reserved_energy_zone():
    store, _, _, _, _, energies, target_state, target_options = _run_to_target(
        context_ref=replace(energies_placeholder(), zone=None)
    )
    issued = store.resume(target_state, target_options)
    assert issued.status == ResumeStatus.ADVANCED_ISSUE
    assert issued.owner.expected_context_ref.card_id == energies[0].card_id
    assert issued.owner.expected_context_ref.serial == energies[0].serial
    assert issued.owner.expected_context_ref.owner == energies[0].owner
    assert issued.owner.expected_context_ref.zone == energies[0].zone


def test_duplicate_target_callback_is_reissued_once_without_callback_growth():
    store, _, _, _, _, energies, target_state, target_options = _run_to_target()
    issued = store.resume(target_state, target_options)
    budget = issued.owner.callback_budget_used
    duplicate = store.resume(target_state, target_options)
    assert duplicate.status == ResumeStatus.DUPLICATE_REISSUE
    assert duplicate.owner.expected_context_ref == energies[0]
    assert duplicate.owner.callback_budget_used == budget


def test_missing_post_energy_ref_fails_closed_with_rule_code():
    store, _, _, _, _, _, target_state, target_options = _run_to_target(context_ref=None)
    failed = store.resume(replace(target_state, context_ref=None), target_options)
    assert failed.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert "AURA_CTXREF_NEXT_REF_MISSING" in failed.reasons
    assert AURA_CTXREF_CAPTURE_RULE in failed.reasons


def test_post_energy_ref_owner_mismatch_fails_closed():
    store, _, _, _, _, energies, target_state, target_options = _run_to_target(
        context_ref=replace(energies_ref := energies_placeholder(), owner=1)
    )
    failed = store.resume(target_state, target_options)
    assert failed.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert "AURA_CTXREF_OWNER_MISMATCH" in failed.reasons
    assert AURA_CTXREF_OWNER_RULE in failed.reasons


def energies_placeholder():
    return _ref(6, 7, 0, AreaType.DISCARD)


def test_stale_pending_ref_is_replaced_by_actual_callback_ref():
    store, _, _, _, _, energies, target_state, target_options = _run_to_target()
    store._owner = replace(
        store.owner,
        expected_context_ref=_ref(6, 999, 0, AreaType.DISCARD),
    )
    issued = store.resume(target_state, target_options)
    assert issued.status == ResumeStatus.ADVANCED_ISSUE
    assert issued.owner.expected_context_ref == energies[0]


def test_ambiguous_target_option_fails_closed():
    base, plan, mega_ref, target_ref, energies = _aura_case()
    store = _start(base, plan)
    store.resume(
        _energy_prompt(base, mega_ref, energies),
        (_option(0, _card_key(energies[0])),),
    )
    duplicate_options = (
        _option(0, _card_key(target_ref)),
        _option(1, _card_key(target_ref)),
    )
    target_state, _ = _target_prompt(
        base, mega_ref, target_ref, energies[0], options=duplicate_options
    )
    failed = store.resume(target_state, duplicate_options)
    assert failed.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert "AURA_CTXREF_AMBIGUOUS_NEXT_PROMPT" in failed.reasons
    assert AURA_CTXREF_OWNER_RULE not in failed.reasons


def test_context_ref_not_reserved_fails_closed():
    store, _, _, _, _, _, target_state, target_options = _run_to_target(
        context_ref=_ref(6, 99, 0, AreaType.DISCARD)
    )
    failed = store.resume(target_state, target_options)
    assert failed.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert "AURA_CTXREF_CONTEXT_MISMATCH" in failed.reasons


def test_target_action_mismatch_fails_closed():
    store, base, _, mega_ref, _, energies, _, _ = _run_to_target()
    wrong_target = _ref(677, 27, 0, AreaType.BENCH)
    target_state, target_options = _target_prompt(
        base, mega_ref, _ref(675, 21, 0, AreaType.BENCH), energies[0],
        options=(_option(0, _card_key(wrong_target)),),
    )
    failed = store.resume(target_state, target_options)
    assert failed.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert "AURA_CTXREF_CONTEXT_MISMATCH" in failed.reasons


def test_target_prompt_type_mismatch_remains_fail_closed():
    store, _, _, _, _, _, target_state, target_options = _run_to_target(
        context=SelectContext.ATTACH_TO
    )
    failed = store.resume(target_state, target_options)
    assert failed.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert "UNEXPECTED_CONTEXT" in failed.reasons


def test_non_discard_energy_cannot_create_an_aura_plan():
    base, _, _, _, _ = _aura_case()
    hand_energy = _ref(6, 77, 0, AreaType.HAND)
    with pytest.raises(ValueError, match="exact discard Fighting Energy"):
        build_aura_jab_plan(
            base,
            ActionSpec.single(_attack_key()),
            (hand_energy,),
            base.own.bench[0].ref,
            PROOF_DIGEST,
        )


def test_two_energy_callbacks_bind_in_declared_order():
    base, plan, mega_ref, target_ref, energies = _aura_case(2)
    store = _start(base, plan)
    energy_result = store.resume(
        _energy_prompt(base, mega_ref, energies),
        tuple(_option(index, _card_key(value)) for index, value in enumerate(energies)),
    )
    assert energy_result.status == ResumeStatus.ADVANCED_ISSUE
    first_state, first_options = _target_prompt(
        base, mega_ref, target_ref, energies[0], action_count=10
    )
    first_state = replace(
        first_state,
        receipt_events=(_event(LogType.ATTACK, mega_ref, attack_id=982), _event(LogType.ATTACH, energies[0], target=target_ref)),
    )
    first = store.resume(first_state, first_options)
    assert first.status == ResumeStatus.ADVANCED_ISSUE
    second_state, second_options = _target_prompt(
        base, mega_ref, target_ref, energies[1], action_count=11
    )
    second_state = replace(
        second_state,
        receipt_events=first_state.receipt_events,
    )
    second = store.resume(second_state, second_options)
    assert second.status == ResumeStatus.ADVANCED_ISSUE
    assert second.owner.expected_context_ref == energies[1]
    completed = store.resume(_completed_state(base, target_ref, energies), ())
    assert completed.status == ResumeStatus.COMPLETED


def test_game_epoch_change_is_not_hidden_by_context_binding():
    store, _, _, _, _, _, target_state, target_options = _run_to_target()
    failed = store.resume(
        replace(target_state, game_epoch=target_state.game_epoch + 1),
        target_options,
    )
    assert failed.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert "TERMINAL_RECEIPT_GAME_EPOCH_CHANGED" in failed.reasons


def test_non_aura_transaction_does_not_emit_aura_rules():
    source = _ref(1121, 30, 0, AreaType.HAND)
    base = _state(
        _player(0, _pokemon(678, 10, 0, AreaType.ACTIVE), hand=(source,)),
        _player(1, _pokemon(999, 20, 1, AreaType.ACTIVE)),
    )
    action = ActionSpec.single(
        SemanticOptionKey(
            option_type=int(OptionType.PLAY),
            player_index=0,
            card_id=1121,
            card_serial=30,
            source_zone=int(AreaType.HAND),
        )
    )
    plan = TransactionPlan(
        transaction_id="NON-AURA",
        owner_kind=OwnerKind.SEARCH_RESOLUTION,
        game_epoch=base.game_epoch,
        seat=0,
        turn=base.turn,
        start_action_count=base.turn_action_count,
        source_ref=source,
        target_refs=(),
        reserved_refs=(),
        initiation=TransactionStep(
            stage=TransactionStage.INITIATION,
            expected_select_type=int(SelectType.MAIN),
            expected_context=int(SelectContext.MAIN),
            expected_min_count=1,
            expected_max_count=1,
            action_spec=action,
            irreversible_on_emit=True,
        ),
        steps=(),
    )
    store = _start(base, plan)
    completed = store.resume(replace(base, turn_action_count=9), ())
    assert completed.status == ResumeStatus.COMPLETED
    assert not any(code.startswith("R_ML_AURA_CTXREF_") for code in completed.reasons)
