"""Deterministic, policy-neutral telemetry with no agent-side file I/O.

The agent core records only information available at the callback boundary.
Runner-only helpers add episode metadata, turn-end deltas, final results, and
paired first differences.  Recording is OFF by default and every ``record_*``
method is deliberately no-throw so observability cannot change play.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union

try:  # Package import in tests.
    from .resolver import (
        Proposal,
        ProposalEvaluation,
        Resolution,
        proposal_digest,
        proposal_rank_key,
        resolution_invariant_reasons,
    )
    from .resource_ledger import ResourceLedger
    from .state_view import (
        ActionSpec,
        PhysicalRef,
        PublicState,
        SemanticBindError,
        SemanticOption,
        public_board_fingerprint,
        public_board_payload,
        public_state_fingerprint,
        semantic_option_multiset,
    )
    from .transactions import (
        ResumeResult,
        StartResult,
        TransactionPlan,
        TransactionState,
    )
except ImportError:  # Flat submission import from main.py.
    from resolver import (
        Proposal,
        ProposalEvaluation,
        Resolution,
        proposal_digest,
        proposal_rank_key,
        resolution_invariant_reasons,
    )
    from resource_ledger import ResourceLedger
    from state_view import (
        ActionSpec,
        PhysicalRef,
        PublicState,
        SemanticBindError,
        SemanticOption,
        public_board_fingerprint,
        public_board_payload,
        public_state_fingerprint,
        semantic_option_multiset,
    )
    from transactions import ResumeResult, StartResult, TransactionPlan, TransactionState


SCHEMA_VERSION = "mega_lucario_telemetry_v1"


class TelemetryMode(str, Enum):
    OFF = "OFF"
    MEMORY = "MEMORY"


class TelemetryProjection(str, Enum):
    INTERNAL_AGENT_VISIBLE = "INTERNAL_AGENT_VISIBLE"
    PUBLIC_REDACTED = "PUBLIC_REDACTED"


class RecordType(str, Enum):
    DECISION = "DECISION"
    TRANSACTION = "TRANSACTION"
    TURN_END = "TURN_END"
    GAME_END = "GAME_END"
    FAULT = "FAULT"
    FIRST_DIFFERENCE = "FIRST_DIFFERENCE"
    BUFFER_STATUS = "BUFFER_STATUS"


class DifferenceKind(str, Enum):
    INTENDED_STRATEGIC_DIFFERENCE = "INTENDED_STRATEGIC_DIFFERENCE"
    RESOURCE_EFFICIENCY_DIFFERENCE = "RESOURCE_EFFICIENCY_DIFFERENCE"
    TIEBREAK_ONLY = "TIEBREAK_ONLY"
    IMPLEMENTATION_FAULT = "IMPLEMENTATION_FAULT"
    UNSUPPORTED_EFFECT = "UNSUPPORTED_EFFECT"
    NO_OP_DIFFERENCE = "NO_OP_DIFFERENCE"


def _exact_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _identifier(value: Optional[Union[int, str]], name: str) -> Optional[Union[int, str]]:
    if value is None:
        return None
    if _exact_int(value):
        return int(value)
    if (
        isinstance(value, str)
        and value
        and value == value.strip()
        and chr(10) not in value
        and chr(13) not in value
        and "\\n" not in value
        and "\\r" not in value
        and len(value) <= 256
    ):
        return value
    raise ValueError("{0} must be a bounded integer or identifier string".format(name))


@dataclass(frozen=True)
class RunContext:
    seat: int
    episode_id: Optional[Union[int, str]] = None
    opponent_id: Optional[Union[int, str]] = None
    seed: Optional[int] = None
    game_index: Optional[int] = None

    def __post_init__(self) -> None:
        if not _exact_int(self.seat) or self.seat not in (0, 1):
            raise ValueError("run context seat must be 0 or 1")
        object.__setattr__(
            self,
            "episode_id",
            _identifier(self.episode_id, "episode_id"),
        )
        object.__setattr__(
            self,
            "opponent_id",
            _identifier(self.opponent_id, "opponent_id"),
        )
        for name in ("seed", "game_index"):
            value = getattr(self, name)
            if value is not None and (not _exact_int(value) or value < 0):
                raise ValueError("{0} must be a non-negative exact integer".format(name))

    def payload(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "opponent_id": self.opponent_id,
            "seat": self.seat,
            "seed": self.seed,
            "game_index": self.game_index,
        }


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, str)):
        return value
    if _exact_int(value):
        return int(value)
    if isinstance(value, Enum):
        return _json_value(value.value)
    if isinstance(value, PhysicalRef):
        return list(value.sort_key())
    if isinstance(value, Mapping):
        normalized = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("telemetry mapping keys must be strings")
            normalized[key] = _json_value(item)
        return normalized
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    raise ValueError("telemetry contains an unsupported value")


def canonical_json_line(record: Mapping[str, Any]) -> str:
    """Serialize one strict record; never use ``default=str`` fallbacks."""

    normalized = _json_value(record)
    encoded = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ) + "\\n"


    return encoded[:-2] + chr(10)


def telemetry_record_hash(record: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_line(record).encode("utf-8")).hexdigest()


def _run_payload(context: Optional[RunContext], seat: int) -> Dict[str, Any]:
    if context is None:
        return RunContext(seat=seat).payload()
    if not isinstance(context, RunContext) or context.seat != seat:
        raise ValueError("run context must match the acting seat")
    return context.payload()


def _runner_payload(context: RunContext) -> Dict[str, Any]:
    if not isinstance(context, RunContext):
        raise ValueError("runner event requires a RunContext")
    if any(
        value is None
        for value in (
            context.episode_id,
            context.opponent_id,
            context.seed,
            context.game_index,
        )
    ):
        raise ValueError("runner event requires complete episode metadata")
    return context.payload()


def _action_payload(action_spec: Optional[ActionSpec]) -> Optional[Dict[str, Any]]:
    if action_spec is None:
        return None
    if not isinstance(action_spec, ActionSpec):
        raise ValueError("telemetry action must be an ActionSpec")
    payload = {
        "order_sensitive": action_spec.order_sensitive,
        "choices": action_spec.canonical_choices(),
    }
    payload["action_digest"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def _legal_payload(
    legal_options: Sequence[SemanticOption],
) -> Tuple[Dict[str, Any], ...]:
    return tuple(
        {
            "semantic_key": key.canonical(),
            "count": count,
        }
        for key, count in semantic_option_multiset(legal_options)
    )


def _observed_payload(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    projection: TelemetryProjection,
) -> Dict[str, Any]:
    payload = {
        "turn": state.turn,
        "turn_action_count": state.turn_action_count,
        "engine_result": state.result,
        "public_board_fingerprint": public_board_fingerprint(state),
        "actor_seat": state.seat,
    }
    if projection == TelemetryProjection.INTERNAL_AGENT_VISIBLE:
        payload["agent_view_state_fingerprint"] = public_state_fingerprint(state)
        payload["legal_semantic_action_multiset"] = _legal_payload(legal_options)
    else:
        payload["agent_view_state_fingerprint"] = None
        payload["legal_semantic_action_multiset"] = {
            "redacted": True,
        }
    return payload


def _payload_digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json_line(payload).encode("utf-8")).hexdigest()


def _ledger_payload(
    ledger: ResourceLedger,
    projection: TelemetryProjection,
) -> Dict[str, Any]:
    if not isinstance(ledger, ResourceLedger):
        raise ValueError("telemetry ledger must be a ResourceLedger")
    if projection == TelemetryProjection.PUBLIC_REDACTED:
        return {"redacted": True}

    bound_by_id = {
        reservation.reservation_id: reservation
        for reservation in ledger.bound_reservations
    }
    reservations = []
    for declaration in ledger.reservations:
        bound = bound_by_id[declaration.reservation_id]
        declaration_payload = {
            "reservation_id": declaration.reservation_id,
            "kind": declaration.kind.name,
            "reason": declaration.reason,
            "declared_refs": [
                ref_value.sort_key() for ref_value in declaration.refs
            ],
            "role_card_ids": declaration.role_card_ids,
            "required_count": declaration.required_count,
            "allowed_zones": declaration.allowed_zones,
        }
        binding_payload = {
            "reservation_id": declaration.reservation_id,
            "bound_refs": [ref_value.sort_key() for ref_value in bound.refs],
        }
        reservations.append(
            {
                "declaration": declaration_payload,
                "declaration_digest": _payload_digest(declaration_payload),
                "binding": binding_payload,
                "binding_digest": _payload_digest(binding_payload),
            }
        )
    reservations.sort(key=lambda value: value["declaration"]["reservation_id"])
    policy_payload = {
        "owner": ledger.owner,
        "declarations": [value["declaration"] for value in reservations],
    }
    binding_payload = {
        "owner": ledger.owner,
        "bindings": [value["binding"] for value in reservations],
    }
    return {
        "owner": ledger.owner,
        "ledger_policy_digest": _payload_digest(policy_payload),
        "ledger_binding_digest": _payload_digest(binding_payload),
        "reservations": reservations,
    }


def _transaction_state_payload(
    owner: Optional[TransactionState],
    projection: TelemetryProjection,
) -> Optional[Dict[str, Any]]:
    if owner is None:
        return None
    if not isinstance(owner, TransactionState):
        raise ValueError("transaction owner must be TransactionState or None")
    if projection == TelemetryProjection.PUBLIC_REDACTED:
        return {"redacted": True}
    return {
        "transaction_id": owner.transaction_id,
        "plan_digest": owner.plan_digest,
        "owner_kind": owner.owner_kind.value,
        "origin_owner_kind": owner.origin_owner_kind.value,
        "stage": owner.stage.value,
        "game_epoch": owner.game_epoch,
        "seat": owner.seat,
        "turn": owner.turn,
        "start_action_count": owner.start_action_count,
        "source_ref": owner.source_ref,
        "target_refs": owner.target_refs,
        "reserved_refs": owner.reserved_refs,
        "expected_effect_ref": owner.expected_effect_ref,
        "expected_context_ref": owner.expected_context_ref,
        "expected_select_type": owner.expected_select_type,
        "expected_context": owner.expected_context,
        "expected_min_count": owner.expected_min_count,
        "expected_max_count": owner.expected_max_count,
        "last_prompt_fingerprint": (
            None
            if owner.last_prompt_fingerprint is None
            else owner.last_prompt_fingerprint.digest()
        ),
        "last_action": _action_payload(owner.last_action_spec),
        "step_index": owner.step_index,
        "callback_budget_used": owner.callback_budget_used,
        "committed": owner.committed,
        "fault_latched": owner.fault_latched,
        "fault_code": owner.fault_code,
    }


def _proposal_payload(
    proposal: Proposal,
    evaluation: ProposalEvaluation,
    ledger_payload: Mapping[str, Any],
) -> Dict[str, Any]:
    current_digest = proposal_digest(proposal)
    if current_digest != evaluation.proposal_digest:
        raise ValueError("proposal evaluation digest mismatch")
    reservations = {
        value["declaration"]["reservation_id"]: value
        for value in ledger_payload.get("reservations", ())
    }
    reservation_bindings = []
    for reservation_id in proposal.reservation_ids:
        value = reservations.get(reservation_id)
        reservation_bindings.append(
            {
                "reservation_id": reservation_id,
                "binding_digest": (
                    None if value is None else value["binding_digest"]
                ),
            }
        )
    proof = proposal.proof
    return {
        "proposal_digest": current_digest,
        "rule_id": proposal.rule_id,
        "tier": int(proposal.tier),
        "resolver_rank_key": proposal_rank_key(proposal),
        "action": _action_payload(proposal.action_spec),
        "certificate_kind": proposal.certificate_kind.name,
        "proof": {
            "schema": proof.schema.value,
            "proof_digest": proof.digest(),
            "is_valid": proof.is_valid,
            "guaranteed_prizes": proof.guaranteed_prizes,
            "state_fingerprint": proof.state_fingerprint,
            "facts": proof.facts,
            "rejection_reasons": proof.rejection_reasons,
        },
        "resource_cost": [
            ref_value.sort_key()
            for ref_value in proposal.resource_cost.irreversible_refs
        ],
        "reservation_ids": proposal.reservation_ids,
        "reservation_bindings": reservation_bindings,
        "transaction_plan_digest": (
            proposal.transaction_plan.digest()
            if isinstance(proposal.transaction_plan, TransactionPlan)
            else None
        ),
        "metrics": {
            "schema": proposal.metrics.schema.value,
            "supporter_opportunity_cost": (
                proposal.metrics.supporter_opportunity_cost
            ),
            "prize_liability_after": proposal.metrics.prize_liability_after,
            "ready_attackers_after": proposal.metrics.ready_attackers_after,
            "draw_buffer_after": proposal.metrics.draw_buffer_after,
        },
        "disposition": evaluation.disposition.value,
        "reason_codes": evaluation.reasons,
    }


def _join_proposal_evaluations(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    proposals: Sequence[Proposal],
    resolution: Resolution,
    ledger_payload: Mapping[str, Any],
) -> Tuple[Dict[str, Any], ...]:
    invariant_reasons = resolution_invariant_reasons(
        proposals,
        resolution,
        state=state,
        legal_options=legal_options,
    )
    if invariant_reasons:
        raise ValueError("resolution invariant: {0}".format("|".join(invariant_reasons)))
    buckets: Dict[str, list[Proposal]] = {}
    for proposal in proposals:
        buckets.setdefault(proposal_digest(proposal), []).append(proposal)
    rows = []
    for evaluation in resolution.evaluations:
        candidates = buckets.get(evaluation.proposal_digest, [])
        if not candidates:
            raise ValueError("resolution evaluation has no proposal")
        proposal = candidates.pop()
        rows.append(_proposal_payload(proposal, evaluation, ledger_payload))
    if any(buckets.values()):
        raise ValueError("proposal has no resolution evaluation")
    return tuple(
        sorted(rows, key=lambda value: canonical_json_line(value))
    )


def make_resolution_event(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    proposals: Sequence[Proposal],
    resolution: Resolution,
    ledger: ResourceLedger,
    *,
    projection: TelemetryProjection = TelemetryProjection.INTERNAL_AGENT_VISIBLE,
    run_context: Optional[RunContext] = None,
    decision_source: str = "SINGLE_RESOLVER",
    transaction_before: Optional[TransactionState] = None,
    transaction_after: Optional[TransactionState] = None,
) -> Dict[str, Any]:
    projection = TelemetryProjection(projection)
    if not isinstance(state, PublicState) or not isinstance(resolution, Resolution):
        raise ValueError("resolution telemetry requires checked state and resolution")
    if not isinstance(decision_source, str) or not decision_source.strip():
        raise ValueError("decision_source must be a non-empty code")
    invariant_reasons = resolution_invariant_reasons(
        proposals,
        resolution,
        state=state,
        legal_options=legal_options,
    )
    if invariant_reasons:
        raise ValueError(
            "resolution invariant: {0}".format("|".join(invariant_reasons))
        )
    ledger_payload = _ledger_payload(ledger, projection)
    if projection == TelemetryProjection.PUBLIC_REDACTED:
        derived = {
            "redacted": True,
            "selected": None,
            "proposal_evaluations": {"redacted": True},
            "resources": ledger_payload,
            "transaction_before": _transaction_state_payload(
                transaction_before,
                projection,
            ),
            "transaction_after": _transaction_state_payload(
                transaction_after,
                projection,
            ),
        }
    else:
        evaluations = _join_proposal_evaluations(
            state,
            legal_options,
            proposals,
            resolution,
            ledger_payload,
        )
        selected = None
        if resolution.selected is not None:
            selected = next(
                value
                for value in evaluations
                if value["proposal_digest"] == proposal_digest(resolution.selected)
                and value["disposition"] == "SELECTED"
            )
        derived = {
            "decision_source": decision_source.strip(),
            "proposal_evaluations": evaluations,
            "selected": selected,
            "resources": ledger_payload,
            "transaction_before": _transaction_state_payload(
                transaction_before,
                projection,
            ),
            "transaction_after": _transaction_state_payload(
                transaction_after,
                projection,
            ),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RecordType.DECISION.value,
        "projection": projection.value,
        "run": _run_payload(run_context, state.seat),
        "observed": _observed_payload(state, legal_options, projection),
        "derived": derived,
    }


def _transaction_result_payload(
    result: Union[StartResult, ResumeResult],
    projection: TelemetryProjection,
) -> Dict[str, Any]:
    if not isinstance(result, (StartResult, ResumeResult)):
        raise ValueError("transaction result must be StartResult or ResumeResult")
    if projection == TelemetryProjection.PUBLIC_REDACTED:
        return {"redacted": True}
    return {
        "result_type": type(result).__name__,
        "status": result.status.value,
        "action": _action_payload(result.action_spec),
        "owner_after": _transaction_state_payload(result.owner, projection),
        "reason_codes": result.reasons,
    }


def _transaction_binding_reasons(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    result: Union[StartResult, ResumeResult],
) -> Tuple[str, ...]:
    if not isinstance(result, (StartResult, ResumeResult)):
        return ("TRANSACTION_RESULT_TYPE_INVALID",)
    action_spec = result.action_spec
    bound_action = result.bound_action
    if action_spec is None:
        return () if bound_action is None else ("BOUND_ACTION_WITHOUT_SEMANTIC_ACTION",)
    if not isinstance(action_spec, ActionSpec):
        return ("SEMANTIC_ACTION_TYPE_INVALID",)
    if bound_action is None:
        return ("SEMANTIC_ACTION_WITHOUT_BOUND_ACTION",)
    try:
        rebound = tuple(
            action_spec.bind(
                legal_options,
                min_count=state.min_count,
                max_count=state.max_count,
            )
        )
    except SemanticBindError:
        return ("TRANSACTION_ACTION_REBIND_FAILURE",)
    if not isinstance(bound_action, tuple) or bound_action != rebound:
        return ("TRANSACTION_BOUND_ACTION_MISMATCH",)
    return ()


def _origin_correlation_payload(
    state: PublicState,
    owners: Sequence[TransactionState],
    origin_proposal_digest: Optional[str],
    rule_id: Optional[str],
    plan_digest: Optional[str],
    extra_reasons: Sequence[str] = (),
) -> Dict[str, Any]:
    integrity_reasons = list(extra_reasons)
    if len({owner.transaction_id for owner in owners}) > 1:
        integrity_reasons.append("TRANSACTION_ID_CONFLICT")
    if any(owner.seat != state.seat for owner in owners):
        integrity_reasons.append("OWNER_SEAT_MISMATCH")
    if any(owner.game_epoch != state.game_epoch for owner in owners):
        integrity_reasons.append("OWNER_GAME_EPOCH_MISMATCH")
    if any(owner.turn != state.turn for owner in owners):
        integrity_reasons.append("OWNER_TURN_MISMATCH")
    owner_plan_digests = {owner.plan_digest for owner in owners}
    if len(owner_plan_digests) > 1:
        integrity_reasons.append("OWNER_PLAN_DIGEST_CONFLICT")
    if (
        not isinstance(origin_proposal_digest, str)
        or len(origin_proposal_digest) != 64
        or any(
            character not in "0123456789abcdef"
            for character in origin_proposal_digest
        )
    ):
        integrity_reasons.append("ORIGIN_PROPOSAL_DIGEST_MISSING")
    if not isinstance(rule_id, str) or not rule_id.strip():
        integrity_reasons.append("ORIGIN_RULE_ID_MISSING")
    if (
        not isinstance(plan_digest, str)
        or len(plan_digest) != 64
        or any(
            character not in "0123456789abcdef"
            for character in plan_digest
        )
    ):
        integrity_reasons.append("PLAN_DIGEST_MISSING")
    elif owner_plan_digests and plan_digest not in owner_plan_digests:
        integrity_reasons.append("PLAN_DIGEST_OWNER_MISMATCH")
    normalized_reasons = tuple(sorted(set(integrity_reasons)))
    return {
        "origin_proposal_digest": origin_proposal_digest,
        "rule_id": rule_id,
        "plan_digest": plan_digest,
        "complete": not normalized_reasons,
        "integrity_reasons": normalized_reasons,
    }


def make_transaction_event(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    result: Union[StartResult, ResumeResult],
    *,
    owner_before: Optional[TransactionState],
    origin_proposal_digest: Optional[str],
    rule_id: Optional[str],
    plan_digest: Optional[str],
    correlation_reasons: Sequence[str] = (),
    projection: TelemetryProjection = TelemetryProjection.INTERNAL_AGENT_VISIBLE,
    run_context: Optional[RunContext] = None,
) -> Dict[str, Any]:
    projection = TelemetryProjection(projection)
    if not isinstance(state, PublicState):
        raise ValueError("transaction telemetry requires a PublicState")
    binding_reasons = _transaction_binding_reasons(state, legal_options, result)
    if binding_reasons:
        raise ValueError(
            "transaction binding invariant: {0}".format("|".join(binding_reasons))
        )
    if projection == TelemetryProjection.INTERNAL_AGENT_VISIBLE:
        owners = tuple(
            owner
            for owner in (owner_before, result.owner)
            if owner is not None
        )
        correlation = _origin_correlation_payload(
            state,
            owners,
            origin_proposal_digest,
            rule_id,
            plan_digest,
            correlation_reasons,
        )
    else:
        correlation = {"redacted": True}
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RecordType.TRANSACTION.value,
        "projection": projection.value,
        "run": _run_payload(run_context, state.seat),
        "observed": _observed_payload(state, legal_options, projection),
        "transaction": {
            "correlation": correlation,
            "owner_before": _transaction_state_payload(owner_before, projection),
            "result": _transaction_result_payload(result, projection),
        },
    }


def make_fault_event(
    state: PublicState,
    *,
    source: str,
    code: str,
    transaction_state: Optional[TransactionState] = None,
    origin_proposal_digest: Optional[str] = None,
    rule_id: Optional[str] = None,
    plan_digest: Optional[str] = None,
    correlation_reasons: Sequence[str] = (),
    projection: TelemetryProjection = TelemetryProjection.INTERNAL_AGENT_VISIBLE,
    run_context: Optional[RunContext] = None,
) -> Dict[str, Any]:
    projection = TelemetryProjection(projection)
    for value, name in ((source, "source"), (code, "code")):
        if (
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or chr(10) in value
            or chr(13) in value
            or "\\n" in value
            or "\\r" in value
            or len(value) > 256
        ):
            raise ValueError("fault {0} must be a bounded code".format(name))
    if projection == TelemetryProjection.INTERNAL_AGENT_VISIBLE:
        transaction_correlation = (
            None
            if transaction_state is None
            else _origin_correlation_payload(
                state,
                (transaction_state,),
                origin_proposal_digest,
                rule_id,
                plan_digest,
                correlation_reasons,
            )
        )
        fault = {
            "source": source,
            "code": code,
            "transaction_state": _transaction_state_payload(
                transaction_state,
                projection,
            ),
            "transaction_correlation": transaction_correlation,
        }
    else:
        fault = {"fault_present": True, "details_redacted": True}
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RecordType.FAULT.value,
        "projection": projection.value,
        "run": _run_payload(run_context, state.seat),
        "observed": {
            "turn": state.turn,
            "turn_action_count": state.turn_action_count,
            "actor_seat": state.seat,
            "public_board_fingerprint": public_board_fingerprint(state),
            "agent_view_state_fingerprint": (
                public_state_fingerprint(state)
                if projection == TelemetryProjection.INTERNAL_AGENT_VISIBLE
                else None
            ),
        },
        "fault": fault,
    }


class TelemetryRecorder:
    """Bounded in-memory recorder; disabled unless explicitly constructed."""

    def __init__(
        self,
        mode: TelemetryMode = TelemetryMode.OFF,
        *,
        projection: TelemetryProjection = TelemetryProjection.INTERNAL_AGENT_VISIBLE,
        max_records: int = 1,
        mirror_sink: Optional[Any] = None,
    ) -> None:
        self._mode = TelemetryMode(mode)
        self._projection = TelemetryProjection(projection)
        if not _exact_int(max_records) or max_records <= 0:
            raise ValueError("max_records must be a positive exact integer")
        if mirror_sink is not None and not callable(mirror_sink):
            raise ValueError("mirror_sink must be callable or None")
        self._max_records = max_records
        self._mirror_sink = mirror_sink
        self._records: list[Tuple[int, str]] = []
        self._next_sequence = 0
        self._dropped_count = 0
        self._first_dropped_sequence: Optional[int] = None
        self._last_dropped_sequence: Optional[int] = None
        self._record_error_count = 0
        self._sink_error_count = 0
        self._transaction_origins: Dict[
            Tuple[int, int, str],
            Dict[str, Optional[str]],
        ] = {}

    @classmethod
    def off(
        cls,
        projection: TelemetryProjection = TelemetryProjection.INTERNAL_AGENT_VISIBLE,
    ) -> "TelemetryRecorder":
        return cls(TelemetryMode.OFF, projection=projection, max_records=1)

    @classmethod
    def memory(
        cls,
        max_records: int = 10000,
        projection: TelemetryProjection = TelemetryProjection.INTERNAL_AGENT_VISIBLE,
        mirror_sink: Optional[Any] = None,
    ) -> "TelemetryRecorder":
        return cls(
            TelemetryMode.MEMORY,
            projection=projection,
            max_records=max_records,
            mirror_sink=mirror_sink,
        )

    @property
    def enabled(self) -> bool:
        return self._mode == TelemetryMode.MEMORY

    @property
    def record_error_count(self) -> int:
        return self._record_error_count

    @property
    def sink_error_count(self) -> int:
        return self._sink_error_count

    @property
    def dropped_count(self) -> int:
        return self._dropped_count

    def _remember_transaction_origin(
        self,
        key: Tuple[int, int, str],
        payload: Dict[str, Optional[str]],
    ) -> None:
        if key in self._transaction_origins:
            self._transaction_origins.pop(key)
        elif len(self._transaction_origins) >= self._max_records:
            oldest_key = next(iter(self._transaction_origins))
            self._transaction_origins.pop(oldest_key)
        self._transaction_origins[key] = payload

    @staticmethod
    def _transaction_origin_key(
        owners: Sequence[TransactionState],
    ) -> Optional[Tuple[int, int, str]]:
        present = tuple(owner for owner in owners if owner is not None)
        if not present:
            return None
        identities = {
            (owner.game_epoch, owner.seat, owner.transaction_id)
            for owner in present
        }
        if len(identities) != 1:
            return None
        return next(iter(identities))

    def _resolve_transaction_correlation(
        self,
        key: Optional[Tuple[int, int, str]],
        *,
        origin_proposal_digest: Optional[str],
        rule_id: Optional[str],
        plan_digest: Optional[str],
        owner_plan_digest: Optional[str],
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Tuple[str, ...]]:
        remembered = self._transaction_origins.get(key, {}) if key is not None else {}
        correlation_reasons = []

        def resolve(field, explicit, conflict_code):
            remembered_value = remembered.get(field)
            if (
                explicit is not None
                and remembered_value is not None
                and explicit != remembered_value
            ):
                correlation_reasons.append(conflict_code)
                return remembered_value
            return explicit if explicit is not None else remembered_value

        resolved_origin = resolve(
            "origin_proposal_digest",
            origin_proposal_digest,
            "ORIGIN_PROPOSAL_DIGEST_CONFLICT",
        )
        resolved_rule = resolve(
            "rule_id",
            rule_id,
            "ORIGIN_RULE_ID_CONFLICT",
        )
        resolved_plan = resolve(
            "plan_digest",
            plan_digest,
            "PLAN_DIGEST_REGISTRY_CONFLICT",
        )
        if resolved_plan is None:
            resolved_plan = owner_plan_digest
        if key is not None and any(
            value is not None
            for value in (resolved_origin, resolved_rule, resolved_plan)
        ):
            self._remember_transaction_origin(
                key,
                {
                    "origin_proposal_digest": resolved_origin,
                    "rule_id": resolved_rule,
                    "plan_digest": resolved_plan,
                },
            )
        return (
            resolved_origin,
            resolved_rule,
            resolved_plan,
            tuple(correlation_reasons),
        )

    def _append(self, record: Mapping[str, Any]) -> None:
        if not self.enabled:
            return
        try:
            sequence = self._next_sequence
            self._next_sequence += 1
            sequenced = dict(record)
            sequenced["sequence"] = sequence
            line = canonical_json_line(sequenced)
            if self._mirror_sink is not None:
                try:
                    self._mirror_sink(line)
                except Exception:
                    self._sink_error_count += 1
            if len(self._records) >= self._max_records:
                dropped_sequence, _ = self._records.pop(0)
                self._dropped_count += 1
                if self._first_dropped_sequence is None:
                    self._first_dropped_sequence = dropped_sequence
                self._last_dropped_sequence = dropped_sequence
            self._records.append((sequence, line))
        except Exception:
            self._record_error_count += 1

    def record_resolution(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
        proposals: Sequence[Proposal],
        resolution: Resolution,
        ledger: ResourceLedger,
        *,
        run_context: Optional[RunContext] = None,
        decision_source: str = "SINGLE_RESOLVER",
        transaction_before: Optional[TransactionState] = None,
        transaction_after: Optional[TransactionState] = None,
    ) -> None:
        if not self.enabled:
            return
        try:
            event = make_resolution_event(
                state,
                legal_options,
                proposals,
                resolution,
                ledger,
                projection=self._projection,
                run_context=run_context,
                decision_source=decision_source,
                transaction_before=transaction_before,
                transaction_after=transaction_after,
            )
            selected = resolution.selected
            if (
                selected is not None
                and isinstance(selected.transaction_plan, TransactionPlan)
            ):
                plan = selected.transaction_plan
                self._remember_transaction_origin(
                    (plan.game_epoch, plan.seat, plan.transaction_id),
                    {
                        "origin_proposal_digest": proposal_digest(selected),
                        "rule_id": selected.rule_id,
                        "plan_digest": plan.digest(),
                    },
                )
            self._append(event)
        except Exception:
            self._record_error_count += 1

    def record_transaction(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
        result: Union[StartResult, ResumeResult],
        *,
        owner_before: Optional[TransactionState],
        run_context: Optional[RunContext] = None,
        origin_proposal_digest: Optional[str] = None,
        rule_id: Optional[str] = None,
        plan_digest: Optional[str] = None,
    ) -> None:
        if not self.enabled:
            return
        try:
            owner_after = result.owner
            owners = tuple(
                owner
                for owner in (owner_before, owner_after)
                if owner is not None
            )
            key = self._transaction_origin_key(owners)
            owner_for_plan = owner_after or owner_before
            (
                resolved_origin,
                resolved_rule,
                resolved_plan,
                correlation_reasons,
            ) = self._resolve_transaction_correlation(
                key,
                origin_proposal_digest=origin_proposal_digest,
                rule_id=rule_id,
                plan_digest=plan_digest,
                owner_plan_digest=(
                    None if owner_for_plan is None else owner_for_plan.plan_digest
                ),
            )
            event = make_transaction_event(
                state,
                legal_options,
                result,
                owner_before=owner_before,
                origin_proposal_digest=resolved_origin,
                rule_id=resolved_rule,
                plan_digest=resolved_plan,
                correlation_reasons=correlation_reasons,
                projection=self._projection,
                run_context=run_context,
            )
            self._append(event)
        except Exception:
            self._record_error_count += 1

    def record_fault(
        self,
        state: PublicState,
        *,
        source: str,
        code: str,
        transaction_state: Optional[TransactionState] = None,
        run_context: Optional[RunContext] = None,
        origin_proposal_digest: Optional[str] = None,
        rule_id: Optional[str] = None,
        plan_digest: Optional[str] = None,
    ) -> None:
        if not self.enabled:
            return
        try:
            owners = (
                () if transaction_state is None else (transaction_state,)
            )
            key = self._transaction_origin_key(owners)
            (
                resolved_origin,
                resolved_rule,
                resolved_plan,
                correlation_reasons,
            ) = self._resolve_transaction_correlation(
                key,
                origin_proposal_digest=origin_proposal_digest,
                rule_id=rule_id,
                plan_digest=plan_digest,
                owner_plan_digest=(
                    None
                    if transaction_state is None
                    else transaction_state.plan_digest
                ),
            )
            self._append(
                make_fault_event(
                    state,
                    source=source,
                    code=code,
                    transaction_state=transaction_state,
                    origin_proposal_digest=resolved_origin,
                    rule_id=resolved_rule,
                    plan_digest=resolved_plan,
                    correlation_reasons=correlation_reasons,
                    projection=self._projection,
                    run_context=run_context,
                )
            )
        except Exception:
            self._record_error_count += 1

    def record_event(self, record: Mapping[str, Any]) -> None:
        """Internal-only hook for a checked runner event mapping."""

        if not self.enabled:
            return
        try:
            if self._projection != TelemetryProjection.INTERNAL_AGENT_VISIBLE:
                raise ValueError(
                    "PUBLIC_REDACTED recorder requires typed runner methods"
                )
            if record.get("schema_version") != SCHEMA_VERSION:
                raise ValueError("runner event schema mismatch")
            if record.get("projection") != self._projection.value:
                raise ValueError("runner event projection mismatch")
            if record.get("record_type") not in {
                RecordType.TURN_END.value,
                RecordType.GAME_END.value,
                RecordType.FIRST_DIFFERENCE.value,
            }:
                raise ValueError("record_event accepts runner records only")
            self._append(record)
        except Exception:
            self._record_error_count += 1

    def record_turn_end(
        self,
        run_context: RunContext,
        start_state: PublicState,
        end_state: PublicState,
    ) -> None:
        if not self.enabled:
            return
        try:
            self._append(
                make_turn_end_event(
                    run_context,
                    start_state,
                    end_state,
                    projection=self._projection,
                )
            )
        except Exception:
            self._record_error_count += 1

    def record_game_end(
        self,
        run_context: RunContext,
        final_state: PublicState,
        *,
        steps: int,
        action_errors: int,
        hit_max_steps: bool,
        exit_code: int,
        fault_codes: Iterable[str] = (),
    ) -> None:
        if not self.enabled:
            return
        try:
            self._append(
                make_game_end_event(
                    run_context,
                    final_state,
                    steps=steps,
                    action_errors=action_errors,
                    hit_max_steps=hit_max_steps,
                    exit_code=exit_code,
                    fault_codes=fault_codes,
                    projection=self._projection,
                )
            )
            self._transaction_origins = {
                key: value
                for key, value in self._transaction_origins.items()
                if key[0] != final_state.game_epoch
            }
        except Exception:
            self._record_error_count += 1

    def record_first_difference(
        self,
        baseline_trace: Mapping[str, Any],
        candidate_trace: Mapping[str, Any],
        *,
        run_context: RunContext,
        difference_kind: Optional[DifferenceKind] = None,
    ) -> None:
        if not self.enabled:
            return
        try:
            if self._projection != TelemetryProjection.INTERNAL_AGENT_VISIBLE:
                raise ValueError(
                    "first difference requires INTERNAL_AGENT_VISIBLE telemetry"
                )
            event = find_first_difference(
                baseline_trace,
                candidate_trace,
                run_context=run_context,
                difference_kind=difference_kind,
            )
            if event is not None:
                self._append(event)
        except Exception:
            self._record_error_count += 1

    def snapshot(self) -> Tuple[Dict[str, Any], ...]:
        return tuple(json.loads(line) for _, line in self._records)

    def snapshot_json_lines(self) -> Tuple[str, ...]:
        return tuple(line for _, line in self._records)

    def drain_envelope(self) -> Dict[str, Any]:
        records = self.snapshot()
        envelope = {
            "schema_version": SCHEMA_VERSION,
            "records": records,
            "buffer": {
                "dropped_count": self._dropped_count,
                "first_dropped_sequence": self._first_dropped_sequence,
                "last_dropped_sequence": self._last_dropped_sequence,
                "record_error_count": self._record_error_count,
                "sink_error_count": self._sink_error_count,
                "next_sequence": self._next_sequence,
            },
        }
        self._records = []
        self._dropped_count = 0
        self._first_dropped_sequence = None
        self._last_dropped_sequence = None
        self._record_error_count = 0
        self._sink_error_count = 0
        return envelope

    def drain(self) -> Tuple[Dict[str, Any], ...]:
        envelope = self.drain_envelope()
        buffer = envelope["buffer"]
        if any(
            buffer[name] not in (0, None)
            for name in (
                "dropped_count",
                "first_dropped_sequence",
                "last_dropped_sequence",
                "record_error_count",
                "sink_error_count",
            )
        ):
            status = {
                "schema_version": SCHEMA_VERSION,
                "record_type": RecordType.BUFFER_STATUS.value,
                "buffer": buffer,
            }
            return (status,) + tuple(envelope["records"])
        return tuple(envelope["records"])


def make_turn_end_event(
    run_context: RunContext,
    start_state: PublicState,
    end_state: PublicState,
    *,
    projection: TelemetryProjection = TelemetryProjection.INTERNAL_AGENT_VISIBLE,
) -> Dict[str, Any]:
    """Runner-only turn envelope built after the engine exposes the end state."""

    projection = TelemetryProjection(projection)
    if not isinstance(start_state, PublicState) or not isinstance(end_state, PublicState):
        raise ValueError("turn-end telemetry requires PublicState values")
    if run_context.seat != start_state.seat or run_context.seat != end_state.seat:
        raise ValueError("turn-end run context must match the observed seat")
    before = public_board_payload(start_state)
    after = public_board_payload(end_state)
    before_board = {
        key: value
        for key, value in before.items()
        if key not in ("turn", "turn_action_count")
    }
    after_board = {
        key: value
        for key, value in after.items()
        if key not in ("turn", "turn_action_count")
    }
    player_deltas = {}
    for seat_name in ("p0", "p1"):
        before_counts = before["players"][seat_name]["counts"]
        after_counts = after["players"][seat_name]["counts"]
        player_deltas[seat_name] = {
            "deck_count": after_counts[0] - before_counts[0],
            "hand_count": after_counts[1] - before_counts[1],
            "prize_count": after_counts[2] - before_counts[2],
            "discard_count": (
                len(after["players"][seat_name]["discard_refs"])
                - len(before["players"][seat_name]["discard_refs"])
            ),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RecordType.TURN_END.value,
        "projection": projection.value,
        "run": _runner_payload(run_context),
        "observed": {
            "actor_seat": run_context.seat,
            "turn_start": start_state.turn,
            "turn_end": end_state.turn,
            "turn_action_count_start": start_state.turn_action_count,
            "turn_action_count_end": end_state.turn_action_count,
            "public_board_fingerprint_start": public_board_fingerprint(start_state),
            "public_board_fingerprint_end": public_board_fingerprint(end_state),
            "agent_view_state_fingerprint_start": (
                public_state_fingerprint(start_state)
                if projection == TelemetryProjection.INTERNAL_AGENT_VISIBLE
                else None
            ),
            "agent_view_state_fingerprint_end": (
                public_state_fingerprint(end_state)
                if projection == TelemetryProjection.INTERNAL_AGENT_VISIBLE
                else None
            ),
        },
        "turn_end_board_delta": {
            "changed": before_board != after_board,
            "players": player_deltas,
            "before": before,
            "after": after,
        },
    }


def make_game_end_event(
    run_context: RunContext,
    final_state: PublicState,
    *,
    steps: int,
    action_errors: int,
    hit_max_steps: bool,
    exit_code: int,
    fault_codes: Iterable[str] = (),
    projection: TelemetryProjection = TelemetryProjection.INTERNAL_AGENT_VISIBLE,
) -> Dict[str, Any]:
    """Runner-only final result envelope; the agent must not infer these fields."""

    projection = TelemetryProjection(projection)
    if not isinstance(final_state, PublicState) or run_context.seat != final_state.seat:
        raise ValueError("game-end state must match the run context seat")
    for value, name in (
        (steps, "steps"),
        (action_errors, "action_errors"),
        (exit_code, "exit_code"),
    ):
        if not _exact_int(value) or (name != "exit_code" and value < 0):
            raise ValueError("{0} must be an exact integer".format(name))
    if not isinstance(hit_max_steps, bool):
        raise ValueError("hit_max_steps must be boolean")
    normalized_faults = tuple(sorted(set(fault_codes)))
    if any(not isinstance(code, str) or not code for code in normalized_faults):
        raise ValueError("fault_codes must be non-empty strings")
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RecordType.GAME_END.value,
        "projection": projection.value,
        "run": _runner_payload(run_context),
        "observed": {
            "actor_seat": run_context.seat,
            "turn": final_state.turn,
            "turn_action_count": final_state.turn_action_count,
            "public_board_fingerprint": public_board_fingerprint(final_state),
            "agent_view_state_fingerprint": (
                public_state_fingerprint(final_state)
                if projection == TelemetryProjection.INTERNAL_AGENT_VISIBLE
                else None
            ),
        },
        "game_result": {
            "result": final_state.result,
            "steps": steps,
            "action_errors": action_errors,
            "hit_max_steps": hit_max_steps,
            "exit_code": exit_code,
            "fault_codes": (
                normalized_faults
                if projection == TelemetryProjection.INTERNAL_AGENT_VISIBLE
                else ()
            ),
        },
    }


def _trace_records(
    trace: Mapping[str, Any],
    label: str,
) -> Tuple[Tuple[Mapping[str, Any], ...], Tuple[str, ...]]:
    reasons = []
    if not isinstance(trace, Mapping):
        return (), ("{0}:TRACE_ENVELOPE_REQUIRED".format(label),)
    if trace.get("schema_version") != SCHEMA_VERSION:
        reasons.append("{0}:SCHEMA_MISMATCH".format(label))
    raw_records = trace.get("records")
    if (
        not isinstance(raw_records, (tuple, list))
        or any(not isinstance(record, Mapping) for record in raw_records)
    ):
        reasons.append("{0}:RECORDS_INVALID".format(label))
        records: Tuple[Mapping[str, Any], ...] = ()
    else:
        records = tuple(raw_records)
        if any(
            record.get("schema_version") != SCHEMA_VERSION
            for record in records
        ):
            reasons.append("{0}:RECORD_SCHEMA_MISMATCH".format(label))
        envelope_record_types = {
            RecordType.DECISION.value,
            RecordType.TRANSACTION.value,
            RecordType.TURN_END.value,
            RecordType.GAME_END.value,
            RecordType.FAULT.value,
            RecordType.FIRST_DIFFERENCE.value,
        }
        if any(
            record.get("record_type") not in envelope_record_types
            for record in records
        ):
            reasons.append("{0}:RECORD_TYPE_INVALID".format(label))
        if any(not isinstance(record.get("run"), Mapping) for record in records):
            reasons.append("{0}:RECORD_RUN_MISSING".format(label))
        game_end_indices = tuple(
            index
            for index, record in enumerate(records)
            if record.get("record_type") == RecordType.GAME_END.value
        )
        if len(game_end_indices) != 1:
            reasons.append("{0}:GAME_END_COUNT_INVALID".format(label))
        elif game_end_indices[0] != len(records) - 1:
            reasons.append("{0}:GAME_END_NOT_LAST".format(label))
        if any(
            record.get("record_type") == RecordType.TRANSACTION.value
            and record.get("transaction", {}).get("result", {}).get("action")
            is not None
            and (
                record.get("transaction", {})
                .get("correlation", {})
                .get("complete")
                is not True
                or record.get("transaction", {})
                .get("correlation", {})
                .get("integrity_reasons")
                not in ((), [])
            )
            for record in records
        ):
            reasons.append(
                "{0}:TRANSACTION_CORRELATION_INCOMPLETE".format(label)
            )
    buffer = trace.get("buffer")
    if not isinstance(buffer, Mapping):
        reasons.append("{0}:BUFFER_METADATA_MISSING".format(label))
        return records, tuple(sorted(set(reasons)))

    for field in ("dropped_count", "record_error_count", "next_sequence"):
        value = buffer.get(field)
        if not _exact_int(value) or value < 0:
            reasons.append("{0}:{1}_INVALID".format(label, field.upper()))
    if buffer.get("dropped_count") != 0:
        reasons.append("{0}:DROPPED_RECORDS".format(label))
    if buffer.get("record_error_count") != 0:
        reasons.append("{0}:RECORD_ERRORS".format(label))
    if buffer.get("dropped_count") == 0 and any(
        buffer.get(field) is not None
        for field in ("first_dropped_sequence", "last_dropped_sequence")
    ):
        reasons.append("{0}:DROP_RANGE_WITHOUT_DROPS".format(label))

    sequence_values = tuple(record.get("sequence") for record in records)
    next_sequence = buffer.get("next_sequence")
    if any(not _exact_int(value) or value < 0 for value in sequence_values):
        reasons.append("{0}:SEQUENCE_INVALID".format(label))
    elif sequence_values:
        expected = tuple(range(len(sequence_values)))
        if sequence_values != expected:
            reasons.append("{0}:SEQUENCE_GAP_OR_NONZERO_START".format(label))
        if _exact_int(next_sequence) and next_sequence != len(sequence_values):
            reasons.append("{0}:NEXT_SEQUENCE_MISMATCH".format(label))
    elif _exact_int(next_sequence) and next_sequence != 0:
        reasons.append("{0}:EMPTY_TRACE_NONZERO_SEQUENCE".format(label))
    return records, tuple(sorted(set(reasons)))


def _trace_integrity_fault(
    run_context: RunContext,
    baseline_reasons: Sequence[str],
    candidate_reasons: Sequence[str],
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": RecordType.FIRST_DIFFERENCE.value,
        "projection": TelemetryProjection.INTERNAL_AGENT_VISIBLE.value,
        "run": _runner_payload(run_context),
        "comparison": {
            "index": None,
            "common_prefix_verified": False,
            "common_prefix_length": 0,
            "fault_code": "TRACE_INCOMPLETE",
            "difference_kind": DifferenceKind.IMPLEMENTATION_FAULT.value,
            "baseline_integrity_reasons": tuple(baseline_reasons),
            "candidate_integrity_reasons": tuple(candidate_reasons),
        },
    }


def _comparison_rows(
    events: Sequence[Mapping[str, Any]],
) -> Tuple[Mapping[str, Any], ...]:
    return tuple(
        event
        for event in events
        if (
            event.get("record_type")
            in (RecordType.DECISION.value, RecordType.TRANSACTION.value)
            and _selected_signature(event)[2] is not None
        )
        or event.get("record_type") == RecordType.FAULT.value
        or (
            event.get("record_type") == RecordType.TRANSACTION.value
            and event.get("transaction", {}).get("result", {}).get("status")
            == "IRREVERSIBLE_FAULT"
        )
    )


def _row_kind(event: Mapping[str, Any]) -> str:
    return "ACTION" if _selected_signature(event)[2] is not None else "FAULT"


def _fault_signature(event: Mapping[str, Any]) -> Tuple[Any, ...]:
    if event.get("record_type") == RecordType.FAULT.value:
        fault = event.get("fault", {})
        correlation = fault.get("transaction_correlation")
        return (
            RecordType.FAULT.value,
            fault.get("source"),
            fault.get("code"),
            correlation,
        )
    transaction = event.get("transaction", {})
    result = transaction.get("result", {})
    correlation = transaction.get("correlation", {})
    return (
        RecordType.TRANSACTION.value,
        result.get("status"),
        result.get("reason_codes"),
        correlation,
    )


def _selected_signature(event: Mapping[str, Any]) -> Tuple[Any, Any, Any]:
    if event.get("record_type") == RecordType.DECISION.value:
        selected = event.get("derived", {}).get("selected")
        if not isinstance(selected, Mapping):
            return None, None, None
        return (
            selected.get("proposal_digest"),
            selected.get("rule_id"),
            selected.get("action"),
        )
    transaction = event.get("transaction", {})
    correlation = transaction.get("correlation", {})
    result = transaction.get("result", {})
    return (
        correlation.get("origin_proposal_digest"),
        correlation.get("rule_id"),
        result.get("action"),
    )


def find_first_difference(
    baseline_trace: Mapping[str, Any],
    candidate_trace: Mapping[str, Any],
    *,
    run_context: RunContext,
    difference_kind: Optional[DifferenceKind] = None,
) -> Optional[Dict[str, Any]]:
    """Find the first semantic difference without inventing a causal label."""

    baseline_events, baseline_integrity = _trace_records(
        baseline_trace,
        "BASELINE",
    )
    candidate_events, candidate_integrity = _trace_records(
        candidate_trace,
        "CANDIDATE",
    )
    if baseline_integrity or candidate_integrity:
        return _trace_integrity_fault(
            run_context,
            baseline_integrity,
            candidate_integrity,
        )
    if any(
        event.get("record_type")
        in (RecordType.DECISION.value, RecordType.TRANSACTION.value)
        and event.get("projection")
        != TelemetryProjection.INTERNAL_AGENT_VISIBLE.value
        for event in baseline_events + candidate_events
    ):
        raise ValueError(
            "first-difference comparison requires INTERNAL_AGENT_VISIBLE actions"
        )
    baseline = _comparison_rows(baseline_events)
    candidate = _comparison_rows(candidate_events)
    if any(
        event.get("projection")
        != TelemetryProjection.INTERNAL_AGENT_VISIBLE.value
        for event in baseline + candidate
    ):
        raise ValueError(
            "first-difference comparison requires INTERNAL_AGENT_VISIBLE actions"
        )
    expected_run = _runner_payload(run_context)
    baseline_run_events = tuple(
        event for event in baseline_events if "run" in event
    )
    candidate_run_events = tuple(
        event for event in candidate_events if "run" in event
    )
    baseline_run_mismatch = tuple(
        index
        for index, event in enumerate(baseline_run_events)
        if event.get("run") != expected_run
    )
    candidate_run_mismatch = tuple(
        index
        for index, event in enumerate(candidate_run_events)
        if event.get("run") != expected_run
    )
    if baseline_run_mismatch or candidate_run_mismatch:
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": RecordType.FIRST_DIFFERENCE.value,
            "projection": TelemetryProjection.INTERNAL_AGENT_VISIBLE.value,
            "run": expected_run,
            "comparison": {
                "index": None,
                "common_prefix_verified": False,
                "common_prefix_length": 0,
                "fault_code": "RUN_CONTEXT_MISMATCH",
                "difference_kind": DifferenceKind.IMPLEMENTATION_FAULT.value,
                "baseline_mismatch_indices": baseline_run_mismatch,
                "candidate_mismatch_indices": candidate_run_mismatch,
            },
        }
    common_prefix = 0
    for index in range(min(len(baseline), len(candidate))):
        baseline_observed = baseline[index].get("observed", {})
        candidate_observed = candidate[index].get("observed", {})
        baseline_agent_state = baseline_observed.get(
            "agent_view_state_fingerprint"
        )
        candidate_agent_state = candidate_observed.get(
            "agent_view_state_fingerprint"
        )
        baseline_public_state = baseline_observed.get("public_board_fingerprint")
        candidate_public_state = candidate_observed.get("public_board_fingerprint")
        agent_state_matches = (
            baseline_agent_state == candidate_agent_state
            if baseline_agent_state is not None and candidate_agent_state is not None
            else baseline_public_state == candidate_public_state
        )
        public_state_matches = baseline_public_state == candidate_public_state
        baseline_legal = baseline_observed.get("legal_semantic_action_multiset")
        candidate_legal = candidate_observed.get("legal_semantic_action_multiset")
        baseline_kind = _row_kind(baseline[index])
        candidate_kind = _row_kind(candidate[index])
        legal_surface_matches = (
            baseline_legal == candidate_legal
            if baseline_kind == candidate_kind == "ACTION"
            else True
        )
        if not agent_state_matches or not public_state_matches or not legal_surface_matches:
            if not agent_state_matches or not public_state_matches:
                fault_code = "STATE_DESYNC"
            else:
                fault_code = "STATE_DESYNC:LEGAL_SURFACE_MISMATCH"
            return {
                "schema_version": SCHEMA_VERSION,
                "record_type": RecordType.FIRST_DIFFERENCE.value,
                "projection": TelemetryProjection.INTERNAL_AGENT_VISIBLE.value,
                "run": _runner_payload(run_context),
                "comparison": {
                    "index": index,
                    "common_prefix_verified": False,
                    "common_prefix_length": common_prefix,
                    "fault_code": fault_code,
                    "difference_kind": DifferenceKind.IMPLEMENTATION_FAULT.value,
                    "baseline_agent_view_state_fingerprint": baseline_agent_state,
                    "candidate_agent_view_state_fingerprint": candidate_agent_state,
                    "baseline_public_board_fingerprint": baseline_public_state,
                    "candidate_public_board_fingerprint": candidate_public_state,
                    "baseline_legal_surface_digest": _payload_digest(
                        {"legal": baseline_legal}
                    ),
                    "candidate_legal_surface_digest": _payload_digest(
                        {"legal": candidate_legal}
                    ),
                },
            }

        if baseline_kind != candidate_kind:
            return {
                "schema_version": SCHEMA_VERSION,
                "record_type": RecordType.FIRST_DIFFERENCE.value,
                "projection": TelemetryProjection.INTERNAL_AGENT_VISIBLE.value,
                "run": _runner_payload(run_context),
                "comparison": {
                    "index": index,
                    "common_prefix_verified": True,
                    "common_prefix_length": common_prefix,
                    "fault_code": "FAULT_ACTION_SEQUENCE_MISMATCH",
                    "difference_kind": DifferenceKind.IMPLEMENTATION_FAULT.value,
                    "baseline_row_kind": baseline_kind,
                    "candidate_row_kind": candidate_kind,
                },
            }
        if baseline_kind == "FAULT":
            baseline_fault = _fault_signature(baseline[index])
            candidate_fault = _fault_signature(candidate[index])
            if baseline_fault != candidate_fault:
                return {
                    "schema_version": SCHEMA_VERSION,
                    "record_type": RecordType.FIRST_DIFFERENCE.value,
                    "projection": TelemetryProjection.INTERNAL_AGENT_VISIBLE.value,
                    "run": _runner_payload(run_context),
                    "comparison": {
                        "index": index,
                        "common_prefix_verified": True,
                        "common_prefix_length": common_prefix,
                        "fault_code": "FAULT_RECORD_MISMATCH",
                        "difference_kind": DifferenceKind.IMPLEMENTATION_FAULT.value,
                        "baseline_fault": baseline_fault,
                        "candidate_fault": candidate_fault,
                    },
                }
            common_prefix += 1
            continue

        baseline_selected = _selected_signature(baseline[index])
        candidate_selected = _selected_signature(candidate[index])
        baseline_action = baseline_selected[2]
        candidate_action = candidate_selected[2]
        proposal_differs = baseline_selected[:2] != candidate_selected[:2]
        action_differs = baseline_action != candidate_action
        if proposal_differs or action_differs:
            if not action_differs:
                classification = DifferenceKind.NO_OP_DIFFERENCE
                classification_source = "AUTOMATIC_SEMANTIC_NO_OP"
            else:
                classification = (
                    None
                    if difference_kind is None
                    else DifferenceKind(difference_kind)
                )
                classification_source = (
                    "AUDITOR_REQUIRED"
                    if classification is None
                    else "AUDITOR_SUPPLIED"
                )
            return {
                "schema_version": SCHEMA_VERSION,
                "record_type": RecordType.FIRST_DIFFERENCE.value,
                "projection": TelemetryProjection.INTERNAL_AGENT_VISIBLE.value,
                "run": _runner_payload(run_context),
                "comparison": {
                    "index": index,
                    "common_prefix_verified": True,
                    "common_prefix_length": common_prefix,
                    "fault_code": None,
                    "difference_kind": (
                        None if classification is None else classification.value
                    ),
                    "classification_source": classification_source,
                    "agent_view_state_fingerprint": baseline_agent_state,
                    "public_board_fingerprint": baseline_public_state,
                    "baseline": {
                        "record_type": baseline[index].get("record_type"),
                        "proposal_digest": baseline_selected[0],
                        "rule_id": baseline_selected[1],
                        "action": baseline_action,
                    },
                    "candidate": {
                        "record_type": candidate[index].get("record_type"),
                        "proposal_digest": candidate_selected[0],
                        "rule_id": candidate_selected[1],
                        "action": candidate_action,
                    },
                },
            }
        common_prefix += 1

    if len(baseline) != len(candidate):
        remaining = (
            baseline[common_prefix:]
            if len(baseline) > len(candidate)
            else candidate[common_prefix:]
        )
        fault_only = bool(remaining) and all(
            _row_kind(event) == "FAULT" for event in remaining
        )
        return {
            "schema_version": SCHEMA_VERSION,
            "record_type": RecordType.FIRST_DIFFERENCE.value,
            "projection": TelemetryProjection.INTERNAL_AGENT_VISIBLE.value,
            "run": _runner_payload(run_context),
            "comparison": {
                "index": common_prefix,
                "common_prefix_verified": False,
                "common_prefix_length": common_prefix,
                "fault_code": (
                    "FAULT_EVENT_COUNT_MISMATCH"
                    if fault_only
                    else "STATE_DESYNC:ACTION_EVENT_COUNT_MISMATCH"
                ),
                "difference_kind": DifferenceKind.IMPLEMENTATION_FAULT.value,
                "baseline_action_event_count": len(baseline),
                "candidate_action_event_count": len(candidate),
            },
        }
    return None


__all__ = [
    "DifferenceKind",
    "RecordType",
    "RunContext",
    "SCHEMA_VERSION",
    "TelemetryMode",
    "TelemetryProjection",
    "TelemetryRecorder",
    "canonical_json_line",
    "find_first_difference",
    "make_fault_event",
    "make_game_end_event",
    "make_resolution_event",
    "make_transaction_event",
    "make_turn_end_event",
    "telemetry_record_hash",
]
