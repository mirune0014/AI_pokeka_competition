from dataclasses import replace

import pytest

from mega_lucario_rule_agent.resolver import (
    action_spec_digest,
    proposal_digest,
    resolve_proposals,
    resolution_invariant_reasons,
)
from mega_lucario_rule_agent.resource_ledger import (
    ReservationKind,
    ResourceLedger,
)
from mega_lucario_rule_agent.state_view import (
    ActionSpec,
    AreaType,
    PhysicalRef,
    SelectContext,
)
from mega_lucario_rule_agent.telemetry import (
    DifferenceKind,
    RecordType,
    RunContext,
    TelemetryProjection,
    TelemetryRecorder,
    canonical_json_line,
    find_first_difference,
    make_game_end_event,
    make_resolution_event,
    make_transaction_event,
    make_turn_end_event,
)
from mega_lucario_rule_agent.tests.test_resolver import (
    attack_spec,
    end_spec,
    options_for,
    proposal,
    state,
)
from mega_lucario_rule_agent.tests.test_transactions import (
    NO_KEY,
    ROOT_KEY,
    YES_KEY,
    effect_state as transaction_effect_state,
    options as transaction_options,
    state as transaction_state,
    two_step_plan,
)
from mega_lucario_rule_agent.transactions import (
    ResumeResult,
    ResumeStatus,
    TransactionStore,
)


RUN = RunContext(
    seat=0,
    episode_id=12345,
    opponent_id="historical_silver",
    seed=314159,
    game_index=7,
)


def _resolved(current, legal, proposals, ledger=None):
    return resolve_proposals(
        current,
        legal,
        ResourceLedger(()) if ledger is None else ledger,
        proposals,
    )


def _single_decision(current, attack_id, rule_id, legal=None):
    spec = attack_spec(attack_id)
    legal = options_for(spec) if legal is None else legal
    candidate = proposal(current, legal, spec, rule_id)
    resolution = _resolved(current, legal, (candidate,))
    return make_resolution_event(
        current,
        legal,
        (candidate,),
        resolution,
        ResourceLedger(()),
        run_context=RUN,
    )


def _trace(*events, dropped_count=0, record_error_count=0):
    sequenced = tuple(
        dict(event, sequence=index + dropped_count)
        for index, event in enumerate(events)
    )
    return {
        "schema_version": "mega_lucario_telemetry_v1",
        "records": sequenced,
        "buffer": {
            "dropped_count": dropped_count,
            "first_dropped_sequence": 0 if dropped_count else None,
            "last_dropped_sequence": dropped_count - 1 if dropped_count else None,
            "record_error_count": record_error_count,
            "sink_error_count": 0,
            "next_sequence": dropped_count + len(sequenced),
        },
    }


def _all_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _all_keys(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _all_keys(item)


def test_resolution_event_is_order_independent_and_contains_full_rank_trace():
    current = state()
    attack = attack_spec(982)
    end = end_spec()
    original_legal = options_for(attack, end)
    proposals = (
        proposal(current, original_legal, end, "PASS"),
        proposal(current, original_legal, attack, "ATTACK_982"),
    )
    original = _resolved(current, original_legal, proposals)

    permuted_legal = options_for(end, attack)
    permuted = _resolved(
        current,
        permuted_legal,
        tuple(reversed(proposals)),
    )
    first = make_resolution_event(
        current,
        original_legal,
        proposals,
        original,
        ResourceLedger(()),
        run_context=RUN,
    )
    second = make_resolution_event(
        current,
        permuted_legal,
        tuple(reversed(proposals)),
        permuted,
        ResourceLedger(()),
        run_context=RUN,
    )

    assert canonical_json_line(first) == canonical_json_line(second)
    evaluations = first["derived"]["proposal_evaluations"]
    assert len(evaluations) == 2
    assert all(value["resolver_rank_key"] for value in evaluations)
    assert first["derived"]["selected"]["rule_id"] == "ATTACK_982"
    assert "bound_action" not in canonical_json_line(first)
    assert "raw_option" not in canonical_json_line(first)


def test_ledger_policy_binding_and_proposal_reservation_are_correlated():
    current = state()
    attack = attack_spec(982)
    legal = options_for(attack)
    hand_energy = current.own.hand_refs[0]
    ledger = ResourceLedger((hand_energy,)).reserve_exact(
        "CURRENT_ATTACK_ENERGY",
        ReservationKind.HARD_RESERVED,
        "preserve current attack",
        (hand_energy,),
    )
    candidate = proposal(
        current,
        legal,
        attack,
        "RESERVATION_TRACE",
        reservation_ids=("CURRENT_ATTACK_ENERGY",),
    )
    resolution = _resolved(current, legal, (candidate,), ledger)
    event = make_resolution_event(
        current,
        legal,
        (candidate,),
        resolution,
        ledger,
        run_context=RUN,
    )

    resources = event["derived"]["resources"]
    reservation = resources["reservations"][0]
    evaluation = event["derived"]["proposal_evaluations"][0]
    assert len(resources["ledger_policy_digest"]) == 64
    assert len(resources["ledger_binding_digest"]) == 64
    assert evaluation["proposal_digest"] == proposal_digest(candidate)
    assert evaluation["reservation_bindings"] == [
        {
            "reservation_id": "CURRENT_ATTACK_ENERGY",
            "binding_digest": reservation["binding_digest"],
        }
    ]


def test_public_projection_is_noninterfering_for_hidden_refs_and_looking():
    current = state()
    attack = attack_spec(982)
    legal = options_for(attack)
    baseline_proposal = proposal(current, legal, attack, "PUBLIC_REDACTION")
    baseline_resolution = _resolved(current, legal, (baseline_proposal,))

    hidden_hand = PhysicalRef(700001, 700002, 0, int(AreaType.HAND), 700002)
    hidden_prize = PhysicalRef(700003, 700004, 0, int(AreaType.PRIZE), 700004)
    opponent_hand = PhysicalRef(700005, 700006, 1, int(AreaType.HAND), 700006)
    looking = PhysicalRef(700007, 700008, 0, int(AreaType.LOOKING), 700008)
    changed = replace(
        current,
        game_epoch=current.game_epoch + 1,
        own=replace(
            current.own,
            hand_refs=(hidden_hand,),
            prize_refs=(hidden_prize,),
        ),
        opponent=replace(current.opponent, hand_refs=(opponent_hand,)),
        looking_refs=(looking,),
        looking_open=True,
    )
    baseline_public = make_resolution_event(
        current,
        legal,
        (baseline_proposal,),
        baseline_resolution,
        ResourceLedger(()),
        projection=TelemetryProjection.PUBLIC_REDACTED,
        run_context=RUN,
    )
    changed_public = make_resolution_event(
        changed,
        legal,
        (baseline_proposal,),
        baseline_resolution,
        ResourceLedger(()),
        projection=TelemetryProjection.PUBLIC_REDACTED,
        run_context=RUN,
    )
    baseline_internal = make_resolution_event(
        current,
        legal,
        (baseline_proposal,),
        baseline_resolution,
        ResourceLedger(()),
        run_context=RUN,
    )
    changed_internal = make_resolution_event(
        changed,
        legal,
        (baseline_proposal,),
        baseline_resolution,
        ResourceLedger(()),
        run_context=RUN,
    )

    assert canonical_json_line(baseline_public) == canonical_json_line(changed_public)
    assert canonical_json_line(baseline_internal) != canonical_json_line(changed_internal)
    forbidden = {
        "hand_refs",
        "prize_refs",
        "looking",
        "facts",
        "resource_cost",
        "reservation_ids",
    }
    assert forbidden.isdisjoint(set(_all_keys(changed_public)))
    public_text = canonical_json_line(changed_public)
    assert all(str(secret) not in public_text for secret in range(700001, 700009))
    with pytest.raises(ValueError, match="INTERNAL_AGENT_VISIBLE"):
        find_first_difference(
            _trace(baseline_public),
            _trace(changed_public),
            run_context=RUN,
        )


def test_off_memory_and_failing_sink_do_not_change_resolution():
    current = state()
    attack = attack_spec(982)
    legal = options_for(attack)
    candidate = proposal(current, legal, attack, "NO_OP_INVARIANCE")
    resolution = _resolved(current, legal, (candidate,))

    off = TelemetryRecorder.off()
    off.record_resolution(
        current,
        legal,
        (candidate,),
        resolution,
        ResourceLedger(()),
    )

    def broken_sink(_line):
        raise RuntimeError("sink failure must not escape")

    memory = TelemetryRecorder.memory(max_records=4, mirror_sink=broken_sink)
    memory.record_resolution(
        current,
        legal,
        (candidate,),
        resolution,
        ResourceLedger(()),
    )
    repeated = _resolved(current, legal, (candidate,))

    assert off.snapshot() == ()
    assert memory.sink_error_count == 1
    assert memory.record_error_count == 0
    assert len(memory.snapshot()) == 1
    assert repeated == resolution


def test_transaction_events_repeat_origin_correlation_without_raw_indices():
    current = transaction_state()
    root_options = transaction_options(ROOT_KEY)
    transaction_plan = two_step_plan()
    store = TransactionStore()
    start_result = store.start(transaction_plan, current, root_options)
    recorder = TelemetryRecorder.memory(max_records=4)
    recorder.record_transaction(
        current,
        root_options,
        start_result,
        owner_before=None,
        origin_proposal_digest="a" * 64,
        rule_id="SEARCH_ROUTE",
        plan_digest=transaction_plan.digest(),
    )

    next_state = transaction_effect_state(SelectContext.ACTIVATE)
    owner_before = store.owner
    resume_result = store.resume(next_state, transaction_options(YES_KEY))
    recorder.record_transaction(
        next_state,
        transaction_options(YES_KEY),
        resume_result,
        owner_before=owner_before,
    )
    recorder.record_fault(
        next_state,
        source="TRANSACTION_STORE",
        code="TEST_FAULT",
        transaction_state=resume_result.owner,
    )

    records = recorder.snapshot()
    assert len(records) == 3
    for record in records[:2]:
        correlation = record["transaction"]["correlation"]
        assert correlation == {
            "origin_proposal_digest": "a" * 64,
            "rule_id": "SEARCH_ROUTE",
            "plan_digest": transaction_plan.digest(),
            "complete": True,
            "integrity_reasons": [],
        }
        assert "bound_action" not in canonical_json_line(record)
    assert records[2]["fault"]["transaction_correlation"] == records[1][
        "transaction"
    ]["correlation"]
    assert store.owner == resume_result.owner

    incomplete = TelemetryRecorder.memory(max_records=1)
    incomplete.record_transaction(
        current,
        root_options,
        start_result,
        owner_before=None,
    )
    incomplete_correlation = incomplete.snapshot()[0]["transaction"]["correlation"]
    assert not incomplete_correlation["complete"]
    assert set(incomplete_correlation["integrity_reasons"]) == {
        "ORIGIN_PROPOSAL_DIGEST_MISSING",
        "ORIGIN_RULE_ID_MISSING",
    }


def test_unordered_transaction_action_is_canonical_and_origin_registry_is_bounded():
    current = replace(
        transaction_effect_state(SelectContext.ACTIVATE),
        min_count=2,
        max_count=2,
    )
    legal = transaction_options(YES_KEY, NO_KEY)
    forward = ResumeResult(
        ResumeStatus.ISSUE,
        ActionSpec((YES_KEY, NO_KEY), order_sensitive=False),
        (0, 1),
        None,
        (),
    )
    reverse = ResumeResult(
        ResumeStatus.ISSUE,
        ActionSpec((NO_KEY, YES_KEY), order_sensitive=False),
        (0, 1),
        None,
        (),
    )
    common = {
        "owner_before": None,
        "origin_proposal_digest": "a" * 64,
        "rule_id": "UNORDERED",
        "plan_digest": "b" * 64,
        "run_context": RUN,
    }
    forward_event = make_transaction_event(current, legal, forward, **common)
    reverse_event = make_transaction_event(current, legal, reverse, **common)
    assert action_spec_digest(forward.action_spec) == action_spec_digest(
        reverse.action_spec
    )
    assert (
        forward_event["transaction"]["result"]["action"]
        == reverse_event["transaction"]["result"]["action"]
    )

    recorder = TelemetryRecorder.memory(max_records=1)
    first_plan = two_step_plan()
    first_result = TransactionStore().start(
        first_plan,
        transaction_state(),
        transaction_options(ROOT_KEY),
    )
    recorder.record_transaction(
        transaction_state(),
        transaction_options(ROOT_KEY),
        first_result,
        owner_before=None,
        origin_proposal_digest="c" * 64,
        rule_id="FIRST",
    )
    second_plan = replace(first_plan, transaction_id="TX-SECOND")
    second_result = TransactionStore().start(
        second_plan,
        transaction_state(),
        transaction_options(ROOT_KEY),
    )
    recorder.record_transaction(
        transaction_state(),
        transaction_options(ROOT_KEY),
        second_result,
        owner_before=None,
        origin_proposal_digest="d" * 64,
        rule_id="SECOND",
    )
    assert len(recorder._transaction_origins) == 1

    recorder.record_game_end(
        RUN,
        replace(transaction_state(), result=0),
        steps=2,
        action_errors=0,
        hit_max_steps=False,
        exit_code=0,
    )
    assert recorder._transaction_origins == {}


def test_bounded_buffer_reports_exact_dropped_sequence_range():
    current = state()
    recorder = TelemetryRecorder.memory(max_records=2)
    for index in range(4):
        recorder.record_fault(current, source="TEST", code="FAULT_{0}".format(index))

    envelope = recorder.drain_envelope()
    assert tuple(record["sequence"] for record in envelope["records"]) == (2, 3)
    assert envelope["buffer"]["dropped_count"] == 2
    assert envelope["buffer"]["first_dropped_sequence"] == 0
    assert envelope["buffer"]["last_dropped_sequence"] == 1

    recorder = TelemetryRecorder.memory(max_records=1)
    recorder.record_fault(current, source="TEST", code="FIRST")
    recorder.record_fault(current, source="TEST", code="SECOND")
    drained = recorder.drain()
    assert drained[0]["record_type"] == RecordType.BUFFER_STATUS.value
    assert drained[0]["buffer"]["dropped_count"] == 1


def test_public_recorder_rejects_untyped_internal_event_but_typed_event_is_safe():
    start = state()
    end = replace(start, turn_action_count=start.turn_action_count + 1)
    recorder = TelemetryRecorder.memory(
        max_records=2,
        projection=TelemetryProjection.PUBLIC_REDACTED,
    )
    recorder.record_event(make_turn_end_event(RUN, start, end))
    assert recorder.snapshot() == ()
    assert recorder.record_error_count == 1

    recorder.record_turn_end(RUN, start, end)
    record = recorder.snapshot()[0]
    assert record["projection"] == TelemetryProjection.PUBLIC_REDACTED.value
    assert record["observed"]["agent_view_state_fingerprint_start"] is None
    assert record["observed"]["agent_view_state_fingerprint_end"] is None


def test_runner_turn_game_and_first_difference_events_are_explicit():
    start = state()
    counter_only = replace(
        start,
        turn_action_count=start.turn_action_count + 1,
    )
    assert not make_turn_end_event(RUN, start, counter_only)[
        "turn_end_board_delta"
    ]["changed"]
    end = replace(
        start,
        turn_action_count=start.turn_action_count + 1,
        opponent=replace(
            start.opponent,
            prize_count=start.opponent.prize_count - 1,
        ),
    )
    turn_event = make_turn_end_event(RUN, start, end)
    assert turn_event["turn_end_board_delta"]["players"]["p1"]["prize_count"] == -1
    final = replace(end, result=0)
    game_event = make_game_end_event(
        RUN,
        final,
        steps=123,
        action_errors=0,
        hit_max_steps=False,
        exit_code=0,
    )
    assert game_event["game_result"]["result"] == 0

    shared_legal = options_for(attack_spec(982), attack_spec(983))
    baseline = _single_decision(
        start,
        982,
        "BASELINE_ATTACK",
        shared_legal,
    )
    candidate = _single_decision(
        start,
        983,
        "CANDIDATE_ATTACK",
        shared_legal,
    )
    difference = find_first_difference(
        _trace(baseline),
        _trace(candidate),
        run_context=RUN,
    )
    assert difference["comparison"]["common_prefix_verified"]
    assert difference["comparison"]["difference_kind"] is None
    classified = find_first_difference(
        _trace(baseline),
        _trace(candidate),
        run_context=RUN,
        difference_kind=DifferenceKind.RESOURCE_EFFICIENCY_DIFFERENCE,
    )
    assert (
        classified["comparison"]["difference_kind"]
        == DifferenceKind.RESOURCE_EFFICIENCY_DIFFERENCE.value
    )
    with pytest.raises(ValueError, match="complete episode metadata"):
        make_turn_end_event(RunContext(seat=0), start, end)


def test_first_difference_requires_complete_same_run_trace_envelopes():
    current = state()
    shared_legal = options_for(attack_spec(982), attack_spec(983))
    baseline = _single_decision(current, 982, "RULE_A", shared_legal)
    candidate = _single_decision(current, 983, "RULE_B", shared_legal)

    incomplete = find_first_difference(
        _trace(baseline, dropped_count=1),
        _trace(candidate),
        run_context=RUN,
    )
    assert incomplete["comparison"]["fault_code"] == "TRACE_INCOMPLETE"
    assert not incomplete["comparison"]["common_prefix_verified"]
    assert "BASELINE:DROPPED_RECORDS" in incomplete["comparison"][
        "baseline_integrity_reasons"
    ]

    wrong_run = dict(candidate, run=dict(candidate["run"], seed=RUN.seed + 1))
    mismatch = find_first_difference(
        _trace(baseline),
        _trace(wrong_run),
        run_context=RUN,
    )
    assert mismatch["comparison"]["fault_code"] == "RUN_CONTEXT_MISMATCH"
    assert mismatch["comparison"]["candidate_mismatch_indices"] == (0,)


def test_first_difference_compares_transaction_actions_and_legal_surface():
    current = transaction_effect_state(SelectContext.ACTIVATE)
    legal = transaction_options(YES_KEY, NO_KEY)
    yes_result = ResumeResult(
        ResumeStatus.ISSUE,
        ActionSpec.single(YES_KEY),
        (0,),
        None,
        (),
    )
    no_result = ResumeResult(
        ResumeStatus.ISSUE,
        ActionSpec.single(NO_KEY),
        (1,),
        None,
        (),
    )
    yes_event = make_transaction_event(
        current,
        legal,
        yes_result,
        owner_before=None,
        origin_proposal_digest="a" * 64,
        rule_id="YES_RULE",
        plan_digest="b" * 64,
        run_context=RUN,
    )
    no_event = make_transaction_event(
        current,
        legal,
        no_result,
        owner_before=None,
        origin_proposal_digest="c" * 64,
        rule_id="NO_RULE",
        plan_digest="d" * 64,
        run_context=RUN,
    )
    difference = find_first_difference(
        _trace(yes_event),
        _trace(no_event),
        run_context=RUN,
    )
    assert difference["comparison"]["baseline"]["record_type"] == "TRANSACTION"
    assert difference["comparison"]["baseline"]["action"] != difference[
        "comparison"
    ]["candidate"]["action"]

    lifecycle = make_transaction_event(
        current,
        legal,
        ResumeResult(ResumeStatus.NO_OWNER, None, None, None, ()),
        owner_before=None,
        origin_proposal_digest=None,
        rule_id=None,
        plan_digest=None,
        run_context=RUN,
    )
    assert (
        find_first_difference(
            _trace(lifecycle, yes_event),
            _trace(yes_event),
            run_context=RUN,
        )
        is None
    )

    legal_changed = dict(
        yes_event,
        observed=dict(
            yes_event["observed"],
            legal_semantic_action_multiset=(),
        ),
    )
    legal_fault = find_first_difference(
        _trace(yes_event),
        _trace(legal_changed),
        run_context=RUN,
    )
    assert (
        legal_fault["comparison"]["fault_code"]
        == "STATE_DESYNC:LEGAL_SURFACE_MISMATCH"
    )


def test_first_difference_ignores_record_container_for_same_semantic_action():
    current = state()
    decision = _single_decision(current, 982, "SAME_RULE")
    selected = decision["derived"]["selected"]
    transaction_container = {
        "schema_version": decision["schema_version"],
        "record_type": RecordType.TRANSACTION.value,
        "projection": decision["projection"],
        "run": decision["run"],
        "observed": decision["observed"],
        "transaction": {
            "correlation": {
                "origin_proposal_digest": selected["proposal_digest"],
                "rule_id": selected["rule_id"],
            },
            "result": {"action": selected["action"]},
        },
    }
    assert (
        find_first_difference(
            _trace(decision),
            _trace(transaction_container),
            run_context=RUN,
        )
        is None
    )


def test_first_difference_distinguishes_no_op_from_state_desync():
    current = state()
    baseline = _single_decision(current, 982, "RULE_A")
    semantic_no_op = _single_decision(current, 982, "RULE_B")
    no_op = find_first_difference(
        _trace(baseline),
        _trace(semantic_no_op),
        run_context=RUN,
    )
    assert no_op["comparison"]["difference_kind"] == DifferenceKind.NO_OP_DIFFERENCE.value

    changed = replace(
        current,
        opponent=replace(
            current.opponent,
            active=(replace(current.opponent.active[0], hp=190),),
        ),
    )
    desynced = _single_decision(changed, 982, "RULE_A")
    state_fault = find_first_difference(
        _trace(baseline),
        _trace(desynced),
        run_context=RUN,
    )
    assert state_fault["comparison"]["fault_code"] == "STATE_DESYNC"
    assert (
        state_fault["comparison"]["difference_kind"]
        == DifferenceKind.IMPLEMENTATION_FAULT.value
    )


def test_resolution_invariants_and_strict_json_fail_closed():
    current = state()
    attack = attack_spec(982)
    legal = options_for(attack)
    candidate = proposal(current, legal, attack, "INVARIANT")
    resolution = _resolved(current, legal, (candidate,))
    assert (
        resolution_invariant_reasons(
            (candidate,),
            resolution,
            state=current,
            legal_options=legal,
        )
        == ()
    )

    broken = replace(
        resolution,
        stats=replace(resolution.stats, proposed=99),
    )
    assert "PROPOSED_STATS_MISMATCH" in resolution_invariant_reasons(
        (candidate,),
        broken,
        state=current,
        legal_options=legal,
    )
    with pytest.raises(ValueError, match="resolution invariant"):
        make_resolution_event(
            current,
            legal,
            (candidate,),
            broken,
            ResourceLedger(()),
            projection=TelemetryProjection.PUBLIC_REDACTED,
        )
    bad_bound = replace(resolution, bound_action=(999,))
    assert "BOUND_ACTION_MISMATCH" in resolution_invariant_reasons(
        (candidate,),
        bad_bound,
        state=current,
        legal_options=legal,
    )
    with pytest.raises(ValueError, match="BOUND_ACTION_MISMATCH"):
        make_resolution_event(
            current,
            legal,
            (candidate,),
            bad_bound,
            ResourceLedger(()),
        )

    transaction_current = transaction_state()
    transaction_legal = transaction_options(ROOT_KEY)
    transaction_plan = two_step_plan()
    transaction_result = TransactionStore().start(
        transaction_plan,
        transaction_current,
        transaction_legal,
    )
    with pytest.raises(ValueError, match="TRANSACTION_BOUND_ACTION_MISMATCH"):
        make_transaction_event(
            transaction_current,
            transaction_legal,
            replace(transaction_result, bound_action=(999,)),
            owner_before=None,
            origin_proposal_digest="a" * 64,
            rule_id="BOUND_CHECK",
            plan_digest=transaction_plan.digest(),
        )
    with pytest.raises(ValueError, match="unsupported"):
        canonical_json_line({"not_allowed": float("nan")})
