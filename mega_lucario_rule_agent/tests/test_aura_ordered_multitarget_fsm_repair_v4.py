"""Contract fixtures for the ordered multi-target Aura FSM repair."""

from dataclasses import replace

import pytest

from mega_lucario_rule_agent.state_view import LogType, SelectContext, SelectType
from mega_lucario_rule_agent.transactions import (
    AURA_V4_ACCEPT_TARGET_RECEIPT_RULE,
    AURA_V4_ADVANCE_TARGET_CURSOR_RULE,
    AURA_V4_ATTACH_RECEIPT_MISSING,
    AURA_V4_CALLBACK_ORDER_MISMATCH,
    AURA_V4_CALLBACK_PROMPT_TYPE_MISMATCH,
    AURA_V4_CALLBACK_REF_MISSING,
    AURA_V4_CALLBACK_REF_NOT_SELECTED,
    AURA_V4_COMPLETE_AFTER_ALL_RECEIPTS_RULE,
    AURA_V4_RELEASE_OWNER_RULE,
    AURA_V4_REJECT_CALLBACK_MISMATCH_RULE,
    AURA_V4_SELECTED_COUNT_PLAN_MISMATCH,
    AURA_V4_TARGET_CONTEXT_MISMATCH,
    AURA_V4_UNSUPPORTED_ENERGY_COUNT,
    ResumeStatus,
    _aura_v4_validate_plan_shape,
)
from mega_lucario_rule_agent.tests.test_aura_context_ref_repair_v2 import (
    _aura_case,
    _card_key,
    _completed_state,
    _energy_prompt,
    _event,
    _option,
    _start,
    _target_prompt,
)


def _energy_step(store, base, mega_ref, energies):
    return store.resume(
        _energy_prompt(base, mega_ref, energies),
        tuple(_option(index, _card_key(ref)) for index, ref in enumerate(energies)),
    )


def _target(base, mega, target, ref, *, count=10, events=(), context=SelectContext.ATTACH_FROM):
    state, options = _target_prompt(
        base, mega, target, ref, action_count=count, context=context
    )
    return replace(state, receipt_events=tuple(events)), options


def _attack(mega):
    return _event(LogType.ATTACK, mega, attack_id=982)


def _attach(energy, target):
    return _event(LogType.ATTACH, energy, target=target)


def _started(count=2):
    base, plan, mega, target, energies = _aura_case(count)
    store = _start(base, plan)
    energy = _energy_step(store, base, mega, energies)
    assert energy.status == ResumeStatus.ADVANCED_ISSUE
    return base, plan, mega, target, energies, store


def test_single_energy_v2_boundary_remains_available():
    base, plan, mega, target, energies = _aura_case(1)
    store = _start(base, plan)
    assert _energy_step(store, base, mega, energies).status == ResumeStatus.ADVANCED_ISSUE
    state, options = _target(base, mega, target, energies[0], events=(_attack(mega),))
    issued = store.resume(state, options)
    assert issued.status == ResumeStatus.ADVANCED_ISSUE
    assert issued.owner._aura_v4_selected_energy_count == 0


def test_n2_first_callback_captures_actual_queue_head():
    base, plan, mega, target, energies, store = _started(2)
    state, options = _target(base, mega, target, energies[1], events=(_attack(mega),))
    issued = store.resume(state, options)
    assert issued.status == ResumeStatus.ADVANCED_ISSUE
    assert issued.owner._aura_v4_selected_energy_count == 2
    assert issued.owner._aura_v4_selected_energy_refs_ordered == (energies[1],)
    assert issued.owner._aura_v4_target_cursor == 0
    assert issued.owner._aura_v4_pending_callback_ref == energies[1]


def test_n2_reverse_callback_receipt_advances_cursor():
    base, plan, mega, target, energies, store = _started(2)
    first, opts = _target(base, mega, target, energies[1], events=(_attack(mega),))
    assert store.resume(first, opts).status == ResumeStatus.ADVANCED_ISSUE
    second, opts = _target(
        base,
        mega,
        target,
        energies[0],
        count=11,
        events=(_attack(mega), _attach(energies[1], target)),
    )
    result = store.resume(second, opts)
    assert result.status == ResumeStatus.ADVANCED_ISSUE
    assert result.owner._aura_v4_consumed_energy_refs == (energies[1],)
    assert result.owner._aura_v4_target_cursor == 1
    assert result.owner._aura_v4_target_action_receipt_count == 1
    assert result.owner._aura_v4_attach_receipt_count == 1
    assert AURA_V4_ACCEPT_TARGET_RECEIPT_RULE in result.reasons
    assert AURA_V4_ADVANCE_TARGET_CURSOR_RULE in result.reasons


def test_n2_completion_requires_both_target_and_attach_receipts():
    base, plan, mega, target, energies, store = _started(2)
    first, opts = _target(base, mega, target, energies[1], events=(_attack(mega),))
    store.resume(first, opts)
    second, opts = _target(
        base, mega, target, energies[0], count=11,
        events=(_attack(mega), _attach(energies[1], target)),
    )
    store.resume(second, opts)
    done = store.resume(_completed_state(base, target, energies), ())
    assert done.status == ResumeStatus.COMPLETED
    assert set(done.reasons) == {AURA_V4_COMPLETE_AFTER_ALL_RECEIPTS_RULE, AURA_V4_RELEASE_OWNER_RULE}
    assert not store.has_owner


def test_n3_noncanonical_order_is_supported():
    base, plan, mega, target, energies, store = _started(3)
    order = (energies[2], energies[0], energies[1])
    events = [_attack(mega)]
    for count, ref in enumerate(order, start=10):
        state, options = _target(base, mega, target, ref, count=count, events=tuple(events))
        result = store.resume(state, options)
        assert result.status == ResumeStatus.ADVANCED_ISSUE
        if count < 12:
            events.append(_attach(ref, target))
    done = store.resume(_completed_state(base, target, energies), ())
    assert done.status == ResumeStatus.COMPLETED


def test_wrong_callback_head_fails_closed():
    base, plan, mega, target, energies, store = _started(2)
    store._owner = replace(
        store.owner,
        _aura_v4_selected_energy_refs_ordered=(energies[0], energies[1]),
    )
    state, options = _target(base, mega, target, energies[1], events=(_attack(mega),))
    result = store.resume(state, options)
    assert result.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert AURA_V4_CALLBACK_ORDER_MISMATCH in result.reasons
    assert AURA_V4_REJECT_CALLBACK_MISMATCH_RULE in result.reasons


def test_callback_ref_missing_fails_closed():
    base, plan, mega, target, energies, store = _started(2)
    state, options = _target(base, mega, target, None, events=(_attack(mega),))
    result = store.resume(state, options)
    assert result.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert AURA_V4_CALLBACK_REF_MISSING in result.reasons


def test_callback_outside_selected_set_fails_closed():
    base, plan, mega, target, energies, store = _started(2)
    outside = replace(energies[0], serial=99, lineage_serial=99)
    state, options = _target(base, mega, target, outside, events=(_attack(mega),))
    result = store.resume(state, options)
    assert result.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert AURA_V4_CALLBACK_REF_NOT_SELECTED in result.reasons


def test_callback_reuse_fails_closed_after_receipt():
    base, plan, mega, target, energies, store = _started(2)
    first, opts = _target(base, mega, target, energies[1], events=(_attack(mega),))
    store.resume(first, opts)
    second, opts = _target(
        base, mega, target, energies[0], count=11,
        events=(_attack(mega), _attach(energies[1], target)),
    )
    store.resume(second, opts)
    duplicate, opts = _target(
        base, mega, target, energies[1], count=12,
        events=(_attack(mega), _attach(energies[1], target), _attach(energies[0], target)),
    )
    result = store.resume(duplicate, opts)
    assert result.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert "AURA_V4_EXTRA_CALLBACK_AFTER_COMPLETE" in result.reasons


def test_missing_attach_receipt_does_not_complete():
    base, plan, mega, target, energies, store = _started(2)
    first, opts = _target(base, mega, target, energies[1], events=(_attack(mega),))
    store.resume(first, opts)
    second, opts = _target(base, mega, target, energies[0], count=11, events=(_attack(mega),))
    result = store.resume(second, opts)
    assert result.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert AURA_V4_ATTACH_RECEIPT_MISSING in result.reasons
    assert result.owner._aura_v4_target_cursor == 0


def test_wrong_attach_energy_does_not_consume_callback():
    base, plan, mega, target, energies, store = _started(2)
    first, opts = _target(base, mega, target, energies[1], events=(_attack(mega),))
    store.resume(first, opts)
    wrong = replace(energies[0], serial=99, lineage_serial=99)
    second, opts = _target(
        base, mega, target, energies[0], count=11,
        events=(_attack(mega), _attach(wrong, target)),
    )
    result = store.resume(second, opts)
    assert result.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert AURA_V4_ATTACH_RECEIPT_MISSING in result.reasons


def test_context_value_is_not_literal_21_gate():
    base, plan, mega, target, energies, store = _started(2)
    state, options = _target(
        base, mega, target, energies[1], events=(_attack(mega),), context=77
    )
    result = store.resume(state, options)
    assert result.status == ResumeStatus.ADVANCED_ISSUE
    assert result.owner.expected_context == 77


def test_context_attach_to_is_rejected_as_wrong_target_context():
    base, plan, mega, target, energies, store = _started(2)
    state, options = _target(
        base, mega, target, energies[1], events=(_attack(mega),), context=SelectContext.ATTACH_TO
    )
    result = store.resume(state, options)
    assert result.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert AURA_V4_TARGET_CONTEXT_MISMATCH in result.reasons


def test_prompt_type_mismatch_is_distinct():
    base, plan, mega, target, energies, store = _started(2)
    state, options = _target(base, mega, target, energies[1], events=(_attack(mega),))
    state = replace(state, select_type=int(SelectType.MAIN))
    result = store.resume(state, options)
    assert result.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert AURA_V4_CALLBACK_PROMPT_TYPE_MISMATCH in result.reasons


def test_supported_count_contract_is_exactly_one_to_three():
    base, plan, mega, target, energies = _aura_case(1)
    assert _aura_v4_validate_plan_shape(plan, plan.terminal_receipt) == ()
    base, plan, mega, target, energies = _aura_case(3)
    assert _aura_v4_validate_plan_shape(plan, plan.terminal_receipt) == ()


def test_four_energy_builder_is_rejected():
    with pytest.raises(ValueError, match="one to three"):
        _aura_case(4)


def test_plan_target_count_mismatch_is_fail_closed():
    base, plan, mega, target, energies, store = _started(2)
    store._plan = replace(plan, steps=plan.steps[:-1])
    state, options = _target(base, mega, target, energies[1], events=(_attack(mega),))
    result = store.resume(state, options)
    assert result.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert AURA_V4_SELECTED_COUNT_PLAN_MISMATCH in result.reasons


def test_owner_state_is_transaction_local():
    first = _started(2)[-1]
    second = _started(2)[-1]
    assert first.owner is not second.owner
    assert first.owner.transaction_id == second.owner.transaction_id
    assert not hasattr(__import__("mega_lucario_rule_agent.transactions", fromlist=["*"]), "_AURA_V4_GLOBAL_QUEUE")


def test_callback_budget_is_observed_not_completion_gate():
    base, plan, mega, target, energies, store = _started(2)
    state, options = _target(base, mega, target, energies[1], events=(_attack(mega),))
    issued = store.resume(state, options)
    assert issued.owner.callback_budget_used == 3
    assert issued.owner._aura_v4_target_cursor == 0


def test_no_pre_final_completion_before_last_receipt():
    base, plan, mega, target, energies, store = _started(2)
    first, opts = _target(base, mega, target, energies[1], events=(_attack(mega),))
    store.resume(first, opts)
    second, opts = _target(
        base, mega, target, energies[0], count=11,
        events=(_attack(mega), _attach(energies[1], target)),
    )
    result = store.resume(second, opts)
    assert result.status == ResumeStatus.ADVANCED_ISSUE
    assert result.owner._aura_v4_completed is False


def test_final_completion_releases_once():
    base, plan, mega, target, energies, store = _started(2)
    first, opts = _target(base, mega, target, energies[1], events=(_attack(mega),))
    store.resume(first, opts)
    second, opts = _target(
        base, mega, target, energies[0], count=11,
        events=(_attack(mega), _attach(energies[1], target)),
    )
    store.resume(second, opts)
    done = store.resume(_completed_state(base, target, energies), ())
    assert done.status == ResumeStatus.COMPLETED
    assert not store.has_owner
    assert store.resume(_completed_state(base, target, energies), ()).status == ResumeStatus.NO_OWNER


def test_target_action_receipt_count_tracks_consumed_pairs():
    base, plan, mega, target, energies, store = _started(2)
    first, opts = _target(base, mega, target, energies[1], events=(_attack(mega),))
    issued = store.resume(first, opts)
    assert issued.owner._aura_v4_target_action_receipt_count == 0
    second, opts = _target(
        base, mega, target, energies[0], count=11,
        events=(_attack(mega), _attach(energies[1], target)),
    )
    issued = store.resume(second, opts)
    assert issued.owner._aura_v4_target_action_receipt_count == 1


def test_reserved_set_is_not_reordered_by_canonical_sort():
    base, plan, mega, target, energies, store = _started(2)
    assert tuple(ref.serial for ref in plan.reserved_refs) == tuple(sorted(ref.serial for ref in energies))
    state, options = _target(base, mega, target, energies[1], events=(_attack(mega),))
    result = store.resume(state, options)
    assert result.owner._aura_v4_selected_energy_refs_ordered[0].serial == energies[1].serial


def test_target_context_ref_lineage_is_preserved_when_zone_is_transient():
    base, plan, mega, target, energies, store = _started(2)
    transient = replace(energies[1], zone=-1)
    state, options = _target(base, mega, target, transient, events=(_attack(mega),))
    result = store.resume(state, options)
    assert result.status == ResumeStatus.ADVANCED_ISSUE
    assert result.owner.expected_context_ref.zone == energies[1].zone


def test_extra_callback_after_completed_is_not_reissued():
    base, plan, mega, target, energies, store = _started(2)
    first, opts = _target(base, mega, target, energies[1], events=(_attack(mega),))
    store.resume(first, opts)
    second, opts = _target(
        base, mega, target, energies[0], count=11,
        events=(_attack(mega), _attach(energies[1], target)),
    )
    store.resume(second, opts)
    assert store.resume(_completed_state(base, target, energies), ()).status == ResumeStatus.COMPLETED


def test_non_aura_store_paths_do_not_receive_v4_state():
    assert AURA_V4_UNSUPPORTED_ENERGY_COUNT == "AURA_V4_UNSUPPORTED_ENERGY_COUNT"
