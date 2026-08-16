from types import SimpleNamespace

import pytest

from infrastructure.tools import run_local_battle
from mega_lucario_rule_agent.main import AgentRuntime
from mega_lucario_rule_agent.resolver import Resolution, ResolutionStats
from mega_lucario_rule_agent.state_view import OptionType, SelectContext
from mega_lucario_rule_agent.telemetry import SCHEMA_VERSION, TelemetryRecorder
from mega_lucario_rule_agent.tests.test_main_runtime import (
    empty_registry,
    observation,
    pokemon,
)
from mega_lucario_rule_agent.tests.test_transactions import (
    END_KEY,
    ROOT_KEY,
    effect_state,
    options,
    state as transaction_state,
    two_step_plan,
)
from mega_lucario_rule_agent.transactions import ResumeStatus, TransactionStore


def _end_observation():
    return observation(
        [{"type": int(OptionType.END)}],
        own_active=pokemon(676, 10, hp=110),
    )


def test_malformed_state_keeps_legal_raw_action_and_lifetime_fault_details():
    runtime = AgentRuntime(registry=empty_registry())
    malformed = {
        "select": {
            "type": 0,
            "context": int(SelectContext.MAIN),
            "minCount": 1,
            "maxCount": 1,
            "option": [
                {"type": int(OptionType.END)},
                {"type": int(OptionType.ATTACK), "attackId": 982},
            ],
        },
        "current": {"turn": 1, "result": -1},
    }

    assert runtime.act(malformed) == [1]
    status = runtime.validation_status()
    assert status["run_failed"]
    assert status["runtime_fault_latched"]
    assert status["last_exception"]["class"] == "ValueError"
    assert "players" in status["last_exception"]["message"]
    assert status["last_containment_reason"] == "RAW_MINIMUM_AFTER_EXCEPTION"
    assert len(status["last_prompt_fingerprint"]) == 64
    assert status["last_decision_source"] == "RAW_CONTAINMENT"
    assert status["last_emitted_action"] == (1,)
    assert status["last_emitted_action_validated"] is True
    assert status["emitted_action_count"] == 1


def test_containment_secondary_exception_records_first_and_second_failures():
    runtime = AgentRuntime(registry=empty_registry())

    def primary(*_args):
        raise RuntimeError("first\nexception")

    def secondary(*_args):
        raise LookupError("second\rexception")

    runtime._decide_checked = primary
    runtime._contained_action = secondary

    assert runtime.act(_end_observation()) == [0]
    drained = runtime.drain_validation_telemetry()
    faults = [
        row["validation_fault"]
        for row in drained["telemetry"]["records"]
        if "validation_fault" in row
    ]
    messages = [
        row["exception"]["message"]
        for row in faults
        if row["exception"] is not None
    ]
    assert "first exception" in messages
    assert "second exception" in messages
    assert "CONTAINMENT_SECONDARY_EXCEPTION" in drained["status"]["failure_codes"]


def test_only_missing_certified_stable_main_fallback_marks_unsupported():
    runtime = AgentRuntime(registry=empty_registry())
    runtime._safe_main_action = lambda *_args, **_kwargs: None

    assert runtime.act(_end_observation()) == [0]
    status = runtime.validation_status()
    assert status["unsupported_stable_main_count"] == 1
    assert "UNSUPPORTED_STABLE_MAIN" in status["failure_codes"]


def test_transaction_fault_survives_owner_release_and_new_game():
    runtime = AgentRuntime(registry=empty_registry())
    store = TransactionStore()
    store.start(two_step_plan(), transaction_state(), options(ROOT_KEY))
    fault = store.resume(
        effect_state(SelectContext.SWITCH),
        options(END_KEY),
    )
    assert fault.status == ResumeStatus.IRREVERSIBLE_FAULT
    runtime._validation.note_transaction(store, fault)
    released = store.resume(transaction_state(action_count=7), options(END_KEY))
    assert released.status == ResumeStatus.FAULT_RELEASED
    runtime._transactions = store

    runtime._begin_game()

    status = runtime.validation_status()
    assert status["transaction_run_fault_latched"]
    assert status["run_failed"]
    assert "TRANSACTION_RUN_FAULT" in status["failure_codes"]


def test_active_owner_is_audited_at_finalize_and_new_game_without_deletion():
    runtime = AgentRuntime(registry=empty_registry())
    store = TransactionStore()
    store.start(two_step_plan(), transaction_state(), options(ROOT_KEY))
    runtime._transactions = store

    finalized = runtime.finalize_validation_game()
    assert finalized["unfinished_owner_at_game_end"] == 1
    assert runtime.transactions.owner is not None

    runtime._begin_game()
    status = runtime.validation_status()
    assert status["owner_at_new_game_start"] == 1
    assert status["last_owner_snapshot"]["transaction_id"] == "TX-1"


def test_clean_finalize_is_idempotent():
    runtime = AgentRuntime(registry=empty_registry())

    first = runtime.finalize_validation_game("GAME_END")
    second = runtime.finalize_validation_game("GAME_END")

    assert first == second
    assert not second["run_failed"]
    assert second["unfinished_owner_at_game_end"] == 0


def test_drain_does_not_clear_status_or_lifetime_latches():
    runtime = AgentRuntime(registry=empty_registry())
    runtime._validation.note_unsupported_stable_main()
    before = runtime.validation_status()

    runtime.drain_validation_telemetry()
    after = runtime.validation_status()

    assert after["run_failed"] == before["run_failed"]
    assert after["failure_codes"] == before["failure_codes"]
    assert after["unsupported_stable_main_count"] == 1


def test_bounded_overflow_sink_and_record_errors_latch_telemetry_health():
    def broken_sink(_line):
        raise OSError("sink unavailable")

    recorder = TelemetryRecorder.memory(max_records=1, mirror_sink=broken_sink)
    for index in range(2):
        recorder.record_validation_fault(
            epoch=0,
            code="FAULT_{0}".format(index),
            prompt_fingerprint="0" * 64,
        )
    recorder.record_event({"schema_version": SCHEMA_VERSION})

    health = recorder.validation_health()
    assert not health["healthy"]
    assert health["lifetime_dropped_count"] == 1
    assert health["lifetime_sink_error_count"] == 2
    assert health["lifetime_record_error_count"] == 1
    recorder.drain_envelope()
    assert recorder.validation_health() == health | {"buffered_records": 0}


def test_normal_decision_records_prompt_route_and_certificate():
    runtime = AgentRuntime(registry=empty_registry())

    assert runtime.act(_end_observation()) == [0]

    status = runtime.validation_status()
    assert len(status["last_prompt_fingerprint"]) == 64
    assert status["last_route_id"]
    assert status["last_certificate_id"]
    assert status["last_decision_source"] == "SAFE_FALLBACK"
    assert status["last_resolution_status"] == "SELECTED"
    assert status["last_emitted_action"] == (0,)
    assert status["last_emitted_action_validated"] is True
    assert status["last_emitted_rule_id"] == "FALLBACK_PASS"
    assert status["emitted_action_count"] == 1
    assert not status["run_failed"]


def test_no_selection_receipt_clears_stale_rule_provenance():
    runtime = AgentRuntime(registry=empty_registry())
    assert runtime.act(_end_observation()) == [0]
    assert runtime.validation_status()["last_route_id"] == "FALLBACK_PASS"

    runtime._validation.note_resolution(
        Resolution(
            selected=None,
            bound_action=None,
            rejections=(),
            evaluations=(),
            stats=ResolutionStats(proposed=0, accepted=0, rejected=0),
        ),
        decision_source="SINGLE_RESOLVER",
    )
    status = runtime.validation_status()
    assert status["last_decision_source"] == "RESOLVER"
    assert status["last_resolution_status"] == "NO_SELECTION"
    assert status["last_route_id"] is None
    assert status["last_certificate_id"] is None
    assert status["last_emitted_rule_id"] is None


def test_callback_receipts_are_persisted_in_order_without_changing_status_fields():
    runtime = AgentRuntime(registry=empty_registry())

    assert runtime.act(_end_observation()) == [0]
    assert runtime.act(_end_observation()) == [0]

    status = runtime.validation_status()
    receipts = status["callback_receipts"]
    assert status["callback_receipt_count"] == 2
    assert status["emitted_action_count"] == 2
    assert [receipt["receipt_index"] for receipt in receipts] == [1, 2]
    assert [receipt["decision_source"] for receipt in receipts] == [
        "SAFE_FALLBACK",
        "SAFE_FALLBACK",
    ]
    assert [receipt["action"] for receipt in receipts] == [(0,), (0,)]
    assert all(receipt["action_validated"] is True for receipt in receipts)
    assert all(receipt["rule_id"] == "FALLBACK_PASS" for receipt in receipts)


def test_fault_containment_rehomes_reason_and_clears_stale_provenance():
    runtime = AgentRuntime(registry=empty_registry())
    validation = runtime._validation
    validation.last_route_id = "STALE_ROUTE"
    validation.last_certificate_id = "STALE_CERTIFICATE"
    validation.last_resolution_status = "SELECTED"
    validation.last_resolution_stats = {"proposed": 1, "accepted": 1, "rejected": 0}
    validation.last_emitted_rule_id = "STALE_RULE"

    validation.note_emission(
        [0],
        decision_source="FAULT_CONTAINMENT",
        rule_id="IRREVERSIBLE_FAULT:EXAMPLE",
        fault_reason="IRREVERSIBLE_FAULT:EXAMPLE",
    )
    status = runtime.validation_status()
    receipt = status["callback_receipts"][0]
    assert status["last_decision_source"] == "FAULT_CONTAINMENT"
    assert status["last_fault_reason"] == "IRREVERSIBLE_FAULT:EXAMPLE"
    assert status["last_route_id"] is None
    assert status["last_certificate_id"] is None
    assert status["last_resolution_status"] is None
    assert status["last_resolution_stats"] is None
    assert status["last_emitted_rule_id"] is None
    assert receipt["fault_reason"] == "IRREVERSIBLE_FAULT:EXAMPLE"
    assert receipt["rule_id"] is None
    assert receipt["route_id"] is None
    assert receipt["certificate_id"] is None


def test_single_resolver_compatibility_alias_is_canonicalized_to_resolver():
    runtime = AgentRuntime(registry=empty_registry())
    runtime._validation.note_resolution(
        Resolution(
            selected=None,
            bound_action=None,
            rejections=(),
            evaluations=(),
            stats=ResolutionStats(proposed=0, accepted=0, rejected=0),
        ),
        decision_source="SINGLE_RESOLVER",
    )
    status = runtime.validation_status()
    assert status["last_decision_source"] == "RESOLVER"
    assert status["source_alias_normalizations"] == 1


def test_finalize_is_idempotent_and_does_not_duplicate_callback_receipts():
    runtime = AgentRuntime(registry=empty_registry())
    assert runtime.act(_end_observation()) == [0]
    before = runtime.validation_status()["callback_receipts"]

    first = runtime.finalize_validation_game("GAME_END")
    second = runtime.finalize_validation_game("GAME_END")

    assert first == second
    assert second["callback_receipt_count"] == 1
    assert second["callback_receipts"] == before


def test_runner_hooked_fault_marks_validation_failed_and_main_exits_nonzero(
    monkeypatch,
    tmp_path,
):
    status = {
        "telemetry_enabled": True,
        "run_failed": True,
        "failure_codes": ("SYNTHETIC_FAULT",),
        "telemetry_health": {"healthy": True},
    }
    module = SimpleNamespace(
        validation_status=lambda: status,
        drain_validation_telemetry=lambda: {
            "status": status,
            "telemetry": {
                "records": (),
                "lifetime_health": {"healthy": True},
            },
        },
        finalize_validation_game=lambda _reason="GAME_END": status,
    )

    def legal_agent(_obs):
        return [0]

    legal_agent.module = module
    monitor = run_local_battle.AgentValidationMonitor([legal_agent])
    monitor.after_callback(0)
    monitor.finalize_all("GAME_END")
    assert monitor.summary()["validation_failed"]
    assert "AGENT_0:SYNTHETIC_FAULT" in monitor.summary()[
        "validation_failure_codes"
    ]

    args = SimpleNamespace(
        no_trace=True,
        trace_dir=None,
        summary=tmp_path / "summary.jsonl",
        games=1,
        engine_dir=tmp_path,
    )
    monkeypatch.setattr(run_local_battle, "parse_args", lambda: args)
    monkeypatch.setattr(run_local_battle, "ensure_engine_on_path", lambda _path: None)
    monkeypatch.setattr(
        run_local_battle,
        "run_game",
        lambda _args, _index: {"validation_failed": True},
    )
    with pytest.raises(SystemExit) as exc_info:
        run_local_battle.main()
    assert exc_info.value.code == 1
