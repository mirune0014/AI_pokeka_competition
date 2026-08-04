from dataclasses import replace

import pytest

from mega_lucario_rule_agent.state_view import (
    ActionSpec,
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
from mega_lucario_rule_agent.transactions import (
    OwnerKind,
    ResumeStatus,
    StartStatus,
    TransactionPlan,
    TransactionStage,
    TransactionState,
    TransactionStep,
    TransactionStore,
    TransactionStoreError,
)


def ref(card_id, serial, owner, zone):
    return PhysicalRef(card_id, serial, owner, int(zone), serial)


def pokemon(card_id, serial, owner, zone):
    return PokemonView(
        ref=ref(card_id, serial, owner, zone),
        hp=100,
        max_hp=100,
        appear_this_turn=False,
        energy_types=(),
        energy_refs=(),
        tool_refs=(),
        pre_evolution_refs=(),
    )


def player(index, active, hand_refs=()):
    return PlayerView(
        index=index,
        active=(active,),
        active_slot_count=1,
        hidden_active_count=0,
        bench=(),
        hand_refs=tuple(hand_refs),
        discard_refs=(),
        prize_refs=(),
        prize_count=6,
        deck_count=40,
        hand_count=len(hand_refs) if index == 0 else 5,
        bench_max=5,
        poisoned=False,
        burned=False,
        asleep=False,
        paralyzed=False,
        confused=False,
    )


SOURCE = ref(1121, 30, 0, AreaType.HAND)
RESERVED = ref(6, 31, 0, AreaType.HAND)


def state(
    *,
    context=SelectContext.MAIN,
    select_type=SelectType.MAIN,
    action_count=4,
    turn=5,
    game_epoch=9,
    effect=False,
    min_count=1,
    max_count=1,
    looking_open=False,
    deck_open=False,
    remaining_damage=0,
    remaining_energy=0,
    result=-1,
):
    effect_ref = (
        PhysicalRef(SOURCE.card_id, SOURCE.serial, SOURCE.owner, None, SOURCE.serial)
        if effect
        else None
    )
    return PublicState(
        game_epoch=game_epoch,
        seat=0,
        turn=turn,
        turn_action_count=action_count,
        first_player=0,
        supporter_played=False,
        stadium_played=False,
        energy_attached=False,
        retreated=False,
        result=result,
        own=player(
            0,
            pokemon(678, 10, 0, AreaType.ACTIVE),
            hand_refs=(SOURCE, RESERVED),
        ),
        opponent=player(
            1,
            pokemon(999, 20, 1, AreaType.ACTIVE),
        ),
        stadium_refs=(),
        looking_refs=(),
        select_context=int(context),
        min_count=min_count,
        max_count=max_count,
        effect_ref=effect_ref,
        context_ref=None,
        select_type=int(select_type),
        looking_open=looking_open,
        select_deck_open=deck_open,
        remaining_damage_counter=remaining_damage,
        remaining_energy_cost=remaining_energy,
    )


YES_KEY = SemanticOptionKey(
    option_type=int(OptionType.YES),
    player_index=0,
)
NO_KEY = SemanticOptionKey(
    option_type=int(OptionType.NO),
    player_index=0,
)
END_KEY = SemanticOptionKey(
    option_type=int(OptionType.END),
    player_index=0,
)
ROOT_KEY = SemanticOptionKey(
    option_type=int(OptionType.PLAY),
    player_index=0,
    card_id=SOURCE.card_id,
    card_serial=SOURCE.serial,
    source_zone=SOURCE.zone,
)


def options(*keys):
    return tuple(
        SemanticOption(index=index, key=key)
        for index, key in enumerate(keys)
    )


def step(
    stage,
    context,
    key,
    *,
    source=SOURCE,
    stochastic=False,
    irreversible=False,
    select_type=SelectType.YES_NO,
):
    return TransactionStep(
        stage=stage,
        expected_select_type=int(select_type),
        expected_context=int(context),
        expected_min_count=1,
        expected_max_count=1,
        action_spec=ActionSpec.single(key),
        irreversible_on_emit=irreversible,
        expected_source_ref=source,
        effect_or_attack_id=1121,
        stochastic_boundary=stochastic,
    )


def initiation(irreversible=True):
    return TransactionStep(
        stage=TransactionStage.INITIATION,
        expected_select_type=int(SelectType.MAIN),
        expected_context=int(SelectContext.MAIN),
        expected_min_count=1,
        expected_max_count=1,
        action_spec=ActionSpec.single(ROOT_KEY),
        irreversible_on_emit=irreversible,
        expected_source_ref=None,
    )


def plan(
    *steps,
    transaction_id="TX-1",
    target_refs=(),
    root_irreversible=True,
):
    return TransactionPlan(
        transaction_id=transaction_id,
        owner_kind=OwnerKind.SEARCH_RESOLUTION,
        game_epoch=9,
        seat=0,
        turn=5,
        start_action_count=4,
        source_ref=SOURCE,
        target_refs=tuple(target_refs),
        reserved_refs=(RESERVED,),
        initiation=initiation(root_irreversible),
        steps=tuple(steps),
    )


def two_step_plan(root_irreversible=True):
    return plan(
        step(
            TransactionStage.SELECT_EFFECT_TARGET,
            SelectContext.ACTIVATE,
            YES_KEY,
        ),
        step(
            TransactionStage.SELECT_RETURN_CARD,
            SelectContext.FIRST_EFFECT,
            NO_KEY,
        ),
        root_irreversible=root_irreversible,
    )


def effect_state(context, action_count=5):
    return state(
        context=context,
        select_type=SelectType.YES_NO,
        action_count=action_count,
        effect=True,
    )


def test_store_starts_exactly_one_owner_and_collision_preserves_it():
    store = TransactionStore()
    first_plan = two_step_plan()
    started = store.start(first_plan, state(), options(ROOT_KEY))
    assert started.status == StartStatus.STARTED
    assert started.action_spec == first_plan.initiation.action_spec
    assert started.bound_action == (0,)
    assert store.owner.transaction_id == "TX-1"
    assert store.owner.committed
    assert store.owner.callback_budget_used == 1
    assert store.owner.step_index == -1
    original_owner = store.owner

    collision = store.start(
        plan(*first_plan.steps, transaction_id="TX-2"),
        state(),
        options(ROOT_KEY),
    )
    assert collision.status == StartStatus.OWNER_COLLISION
    assert store.owner is original_owner


def test_irreversible_initiation_commits_atomically_with_emission():
    store = TransactionStore()
    assert not hasattr(store, "mark_committed")

    started = store.start(two_step_plan(), state(), options(ROOT_KEY))
    assert started.status == StartStatus.STARTED
    assert started.bound_action == (0,)
    assert started.owner.committed

    fault = store.resume(
        effect_state(SelectContext.SWITCH),
        options(YES_KEY),
    )
    assert fault.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert store.run_fault_latched


def test_irreversible_continuation_commits_atomically_with_emission():
    transaction_plan = plan(
        step(
            TransactionStage.SELECT_EFFECT_TARGET,
            SelectContext.ACTIVATE,
            YES_KEY,
            irreversible=True,
        ),
        root_irreversible=False,
    )
    store = TransactionStore()
    started = store.start(transaction_plan, state(), options(ROOT_KEY))
    assert not started.owner.committed

    issued = store.resume(
        effect_state(SelectContext.ACTIVATE),
        options(YES_KEY),
    )
    assert issued.status == ResumeStatus.ADVANCED_ISSUE
    assert issued.bound_action == (0,)
    assert issued.owner.committed

    fault = store.resume(
        effect_state(SelectContext.FIRST_EFFECT, action_count=6),
        options(NO_KEY),
    )
    assert fault.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert store.run_fault_latched


def test_select_type_mismatch_aborts_before_commit_and_faults_after_commit():
    mismatched = effect_state(SelectContext.ACTIVATE)
    mismatched = replace(mismatched, select_type=int(SelectType.CARD))

    provisional = TransactionStore()
    provisional.start(
        two_step_plan(root_irreversible=False),
        state(),
        options(ROOT_KEY),
    )
    precommit = provisional.resume(mismatched, options(YES_KEY))
    assert precommit.status == ResumeStatus.PRECOMMIT_ABORTED
    assert precommit.reasons == ("UNEXPECTED_SELECT_TYPE",)

    committed = TransactionStore()
    committed.start(two_step_plan(), state(), options(ROOT_KEY))
    postcommit = committed.resume(mismatched, options(YES_KEY))
    assert postcommit.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert postcommit.reasons == ("UNEXPECTED_SELECT_TYPE",)


def test_matching_select_type_still_reissues_after_option_permutation():
    transaction_plan = plan(
        TransactionStep(
            stage=TransactionStage.SELECT_EFFECT_TARGET,
            expected_select_type=int(SelectType.YES_NO),
            expected_context=int(SelectContext.ACTIVATE),
            expected_min_count=1,
            expected_max_count=1,
            action_spec=ActionSpec.single(YES_KEY),
            irreversible_on_emit=False,
            expected_source_ref=SOURCE,
            effect_or_attack_id=1121,
        )
    )
    store = TransactionStore()
    store.start(transaction_plan, state(), options(ROOT_KEY))
    current = effect_state(SelectContext.ACTIVATE)
    issued = store.resume(current, options(NO_KEY, YES_KEY))
    duplicate = store.resume(current, options(YES_KEY, NO_KEY))
    assert issued.status == ResumeStatus.ADVANCED_ISSUE
    assert issued.bound_action == (1,)
    assert duplicate.status == ResumeStatus.DUPLICATE_REISSUE
    assert duplicate.bound_action == (0,)


def test_reversible_emissions_remain_cleanly_abortable():
    transaction_plan = plan(
        step(
            TransactionStage.SELECT_EFFECT_TARGET,
            SelectContext.ACTIVATE,
            YES_KEY,
        ),
        root_irreversible=False,
    )
    store = TransactionStore()
    started = store.start(transaction_plan, state(), options(ROOT_KEY))
    assert not started.owner.committed

    issued = store.resume(
        effect_state(SelectContext.ACTIVATE),
        options(YES_KEY),
    )
    assert issued.status == ResumeStatus.ADVANCED_ISSUE
    assert not issued.owner.committed

    aborted = store.resume(
        effect_state(SelectContext.FIRST_EFFECT, action_count=6),
        options(NO_KEY),
    )
    assert aborted.status == ResumeStatus.PRECOMMIT_ABORTED
    assert not store.has_owner
    assert not store.run_fault_latched


def test_plan_identity_and_declared_refs_are_checked_before_owner_creation():
    mismatched_store = TransactionStore()
    mismatch = mismatched_store.start(
        two_step_plan(),
        state(action_count=5),
        options(ROOT_KEY),
    )
    assert mismatch.status == StartStatus.PLAN_STATE_MISMATCH
    assert "PLAN_STATE_IDENTITY_MISMATCH" in mismatch.reasons
    assert not mismatched_store.has_owner

    missing_target = ref(9999, 999, 1, AreaType.BENCH)
    missing_store = TransactionStore()
    missing = missing_store.start(
        plan(
            *two_step_plan().steps,
            target_refs=(missing_target,),
        ),
        state(),
        options(ROOT_KEY),
    )
    assert missing.status == StartStatus.PLAN_STATE_MISMATCH
    assert "PLAN_REF_NOT_IN_STATE" in missing.reasons
    assert not missing_store.has_owner


def test_duplicate_prompt_reissues_same_semantics_without_stage_or_budget_change():
    store = TransactionStore()
    started = store.start(two_step_plan(), state(), options(ROOT_KEY))
    first_prompt = effect_state(SelectContext.ACTIVATE)
    first = store.resume(first_prompt, options(YES_KEY, NO_KEY))
    assert first.status == ResumeStatus.ADVANCED_ISSUE
    assert first.bound_action == (0,)
    assert first.owner.callback_budget_used == 2
    first_owner = first.owner

    permuted = (
        SemanticOption(index=0, key=NO_KEY),
        SemanticOption(index=1, key=YES_KEY),
    )
    duplicate = store.resume(first_prompt, permuted)
    assert duplicate.status == ResumeStatus.DUPLICATE_REISSUE
    assert duplicate.bound_action == (1,)
    assert duplicate.owner.step_index == first_owner.step_index == 0
    assert duplicate.owner.callback_budget_used == first_owner.callback_budget_used == 2
    assert duplicate.owner.committed


def test_changed_prompt_advances_once_then_stable_main_completes():
    store = TransactionStore()
    store.start(two_step_plan(), state(), options(ROOT_KEY))
    first = store.resume(
        effect_state(SelectContext.ACTIVATE),
        options(YES_KEY, NO_KEY),
    )
    assert first.status == ResumeStatus.ADVANCED_ISSUE

    second = store.resume(
        effect_state(SelectContext.FIRST_EFFECT, action_count=6),
        options(NO_KEY),
    )
    assert second.status == ResumeStatus.ADVANCED_ISSUE
    assert second.bound_action == (0,)
    assert second.owner.step_index == 1
    assert second.owner.callback_budget_used == 3

    completed = store.resume(state(action_count=7), options(END_KEY))
    assert completed.status == ResumeStatus.COMPLETED
    assert completed.owner is None
    assert not store.has_owner
    assert not store.run_fault_latched


def test_precommit_bind_failure_aborts_cleanly_without_run_fault():
    store = TransactionStore()
    store.start(
        two_step_plan(root_irreversible=False),
        state(),
        options(ROOT_KEY),
    )
    aborted = store.resume(
        effect_state(SelectContext.ACTIVATE),
        options(NO_KEY),
    )
    assert aborted.status == ResumeStatus.PRECOMMIT_ABORTED
    assert "SEMANTIC_BIND_FAILURE" in aborted.reasons
    assert not store.has_owner
    assert not store.run_fault_latched


def test_explicit_abort_and_fault_apis_preserve_the_boundary_and_reason():
    provisional = TransactionStore()
    started = provisional.start(
        two_step_plan(root_irreversible=False),
        state(),
        options(ROOT_KEY),
    )
    aborted = provisional.abort_precommit(
        started.owner.transaction_id,
        "TARGET_DISAPPEARED",
    )
    assert aborted.status == ResumeStatus.PRECOMMIT_ABORTED
    assert aborted.reasons == ("TARGET_DISAPPEARED",)
    assert not provisional.has_owner
    assert not provisional.run_fault_latched

    committed = TransactionStore()
    started = committed.start(two_step_plan(), state(), options(ROOT_KEY))
    fault = committed.latch_fault(
        started.owner.transaction_id,
        "POSTCOMMIT_TARGET_DISAPPEARED",
    )
    assert fault.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert fault.reasons == ("POSTCOMMIT_TARGET_DISAPPEARED",)
    assert fault.owner.fault_latched
    assert committed.fault_history[0].code == "POSTCOMMIT_TARGET_DISAPPEARED"

    uncommitted = TransactionStore()
    started = uncommitted.start(
        two_step_plan(root_irreversible=False),
        state(),
        options(ROOT_KEY),
    )
    with pytest.raises(TransactionStoreError, match="abort_precommit"):
        uncommitted.latch_fault(started.owner.transaction_id, "WRONG_BOUNDARY")


def test_postcommit_unexpected_prompt_latches_fault_until_strict_main_boundary():
    store = TransactionStore()
    store.start(two_step_plan(), state(), options(ROOT_KEY))
    fault = store.resume(
        effect_state(SelectContext.SWITCH),
        options(YES_KEY),
    )
    assert fault.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert fault.owner.fault_latched
    assert fault.owner.owner_kind == OwnerKind.FAULT_CONTAINMENT
    assert store.run_fault_latched
    assert len(store.fault_history) == 1

    held = store.resume(
        effect_state(SelectContext.SWITCH, action_count=6),
        options(YES_KEY),
    )
    assert held.status == ResumeStatus.FAULT_CONTAINMENT
    assert store.has_owner

    not_stable = state(action_count=7, looking_open=True)
    still_held = store.resume(not_stable, options(END_KEY))
    assert still_held.status == ResumeStatus.FAULT_CONTAINMENT
    assert store.has_owner

    remaining_cost = store.resume(
        state(action_count=7, remaining_energy=1),
        options(END_KEY),
    )
    assert remaining_cost.status == ResumeStatus.FAULT_CONTAINMENT
    assert store.has_owner

    released = store.resume(state(action_count=7), options(END_KEY))
    assert released.status == ResumeStatus.FAULT_RELEASED
    assert not store.has_owner
    assert store.run_fault_latched


def test_stochastic_boundary_releases_and_requires_fresh_replanning():
    stochastic_plan = plan(
        step(
            TransactionStage.SELECT_EFFECT_TARGET,
            SelectContext.ACTIVATE,
            YES_KEY,
            stochastic=True,
        )
    )
    store = TransactionStore()
    store.start(stochastic_plan, state(), options(ROOT_KEY))
    issued = store.resume(
        effect_state(SelectContext.ACTIVATE),
        options(YES_KEY),
    )
    assert issued.status == ResumeStatus.ADVANCED_ISSUE

    released = store.resume(state(action_count=6), options(END_KEY))
    assert released.status == ResumeStatus.STOCHASTIC_RELEASE
    assert not store.has_owner


def test_stochastic_boundary_never_cleanly_releases_into_an_effect_prompt():
    stochastic_plan = plan(
        step(
            TransactionStage.SELECT_EFFECT_TARGET,
            SelectContext.ACTIVATE,
            YES_KEY,
            stochastic=True,
        )
    )
    store = TransactionStore()
    store.start(stochastic_plan, state(), options(ROOT_KEY))
    store.resume(
        effect_state(SelectContext.ACTIVATE),
        options(YES_KEY),
    )

    unexpected = store.resume(
        effect_state(SelectContext.FIRST_EFFECT, action_count=6),
        options(NO_KEY),
    )
    assert unexpected.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert "UNEXPECTED_PROMPT_AFTER_STOCHASTIC_STEP" in unexpected.reasons
    assert store.run_fault_latched


def test_duplicate_main_is_reissued_before_stable_main_completion():
    main_plan = plan(transaction_id="MAIN-DUP")
    store = TransactionStore()
    started = store.start(main_plan, state(), options(ROOT_KEY))
    duplicate = store.resume(state(), options(ROOT_KEY))
    assert started.status == StartStatus.STARTED
    assert duplicate.status == ResumeStatus.DUPLICATE_REISSUE
    assert duplicate.bound_action == (0,)
    assert duplicate.owner.callback_budget_used == 1


def test_turn_action_regression_aborts_or_faults_by_commit_boundary():
    provisional = TransactionStore()
    provisional.start(
        two_step_plan(root_irreversible=False),
        state(),
        options(ROOT_KEY),
    )
    precommit = provisional.resume(
        effect_state(SelectContext.ACTIVATE, action_count=3),
        options(YES_KEY),
    )
    assert precommit.status == ResumeStatus.PRECOMMIT_ABORTED
    assert "TURN_ACTION_COUNT_REGRESSED" in precommit.reasons

    committed = TransactionStore()
    committed.start(two_step_plan(), state(), options(ROOT_KEY))
    postcommit = committed.resume(
        effect_state(SelectContext.ACTIVATE, action_count=3),
        options(YES_KEY),
    )
    assert postcommit.status == ResumeStatus.IRREVERSIBLE_FAULT
    assert committed.run_fault_latched


def test_new_game_or_turn_releases_owner_without_erasing_fault_history():
    store = TransactionStore()
    store.start(two_step_plan(), state(), options(ROOT_KEY))
    changed_turn = store.resume(
        state(turn=6, action_count=0),
        options(END_KEY),
    )
    assert changed_turn.status == ResumeStatus.TURN_RELEASE
    assert not store.has_owner

    store.start(two_step_plan(), state(), options(ROOT_KEY))
    changed_game = store.resume(
        state(game_epoch=10),
        options(END_KEY),
    )
    assert changed_game.status == ResumeStatus.GAME_RELEASE
    assert not store.has_owner


@pytest.mark.parametrize(
    "bad_key,match",
    [
        (
            SemanticOptionKey(
                option_type=int(OptionType.CARD),
                player_index=0,
                source_zone=int(AreaType.PRIZE),
                source_index=0,
            ),
            "source_index",
        ),
        (
            SemanticOptionKey(
                option_type=int(OptionType.CARD),
                player_index=1,
                target_zone=int(AreaType.BENCH),
                relation=0,
            ),
            "target relation",
        ),
        (
            SemanticOptionKey(
                option_type=int(OptionType.ATTACK),
                player_index=0,
            ),
            "attack_id",
        ),
    ],
)
def test_transaction_steps_never_persist_raw_indices_or_inexact_attack(bad_key, match):
    with pytest.raises(ValueError, match=match):
        step(
            TransactionStage.SELECT_EFFECT_TARGET,
            SelectContext.ACTIVATE,
            bad_key,
        )


def test_transaction_state_constructor_is_closed():
    with pytest.raises(ValueError, match="TransactionStore"):
        TransactionState(
            transaction_id="FORGED",
            plan_digest="0" * 64,
            owner_kind=OwnerKind.SEARCH_RESOLUTION,
            origin_owner_kind=OwnerKind.SEARCH_RESOLUTION,
            stage=TransactionStage.INITIATION,
            game_epoch=9,
            seat=0,
            turn=5,
            start_action_count=4,
            source_ref=None,
            target_refs=(),
            reserved_refs=(),
            expected_select_type=0,
            expected_context=0,
            expected_min_count=1,
            expected_max_count=1,
            last_prompt_fingerprint=None,
            last_action_spec=None,
            semantic_action_specs=(),
            step_index=0,
            callback_budget_used=0,
            committed=False,
            fault_latched=False,
            fault_code=None,
            _issuer_token=object(),
        )


def test_active_owner_cannot_be_erased_through_run_reset():
    store = TransactionStore()
    store.start(two_step_plan(), state(), options(ROOT_KEY))
    with pytest.raises(TransactionStoreError, match="owner is active"):
        store.reset_run()
    assert store.has_owner
