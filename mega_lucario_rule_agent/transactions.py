"""One-owner transaction state machine with fail-closed prompt rebinding."""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field, replace
from enum import Enum
import hashlib
import json
from typing import Optional, Sequence, Tuple

try:  # Package import in tests.
    from .state_view import (
        ActionSpec,
        AreaType,
        OptionType,
        PhysicalRef,
        PromptFingerprint,
        PublicState,
        SemanticBindError,
        SemanticOption,
        is_stable_main_state,
        make_prompt_fingerprint,
    )
except ImportError:  # Flat submission import from main.py.
    from state_view import (
        ActionSpec,
        AreaType,
        OptionType,
        PhysicalRef,
        PromptFingerprint,
        PublicState,
        SemanticBindError,
        SemanticOption,
        is_stable_main_state,
        make_prompt_fingerprint,
    )


class OwnerKind(str, Enum):
    ULTRA_BALL_ROUTE = "ULTRA_BALL_ROUTE"
    SEARCH_RESOLUTION = "SEARCH_RESOLUTION"
    LUNAR_CYCLE_RESOLUTION = "LUNAR_CYCLE_RESOLUTION"
    AURA_JAB_ATTACH = "AURA_JAB_ATTACH"
    WALLY_REBOOT = "WALLY_REBOOT"
    HARIYAMA_GUST = "HARIYAMA_GUST"
    BOSS_GUST = "BOSS_GUST"
    SWITCH_RESOLUTION = "SWITCH_RESOLUTION"
    CAPE_ATTACH = "CAPE_ATTACH"
    FORCED_PROMOTION = "FORCED_PROMOTION"
    FAULT_CONTAINMENT = "FAULT_CONTAINMENT"


class TransactionStage(str, Enum):
    INITIATION = "INITIATION"
    SELECT_COST = "SELECT_COST"
    SELECT_SEARCH_TARGET = "SELECT_SEARCH_TARGET"
    SELECT_PLACEMENT = "SELECT_PLACEMENT"
    SELECT_EFFECT_TARGET = "SELECT_EFFECT_TARGET"
    SELECT_ENERGY = "SELECT_ENERGY"
    SELECT_SWITCH_TARGET = "SELECT_SWITCH_TARGET"
    SELECT_GUST_TARGET = "SELECT_GUST_TARGET"
    SELECT_RETURN_CARD = "SELECT_RETURN_CARD"
    SELECT_TOOL_TARGET = "SELECT_TOOL_TARGET"
    SELECT_PROMOTION = "SELECT_PROMOTION"
    COMPLETE = "COMPLETE"
    FAULT_CONTAINMENT = "FAULT_CONTAINMENT"


class StartStatus(str, Enum):
    STARTED = "STARTED"
    OWNER_COLLISION = "OWNER_COLLISION"
    PLAN_STATE_MISMATCH = "PLAN_STATE_MISMATCH"


class ResumeStatus(str, Enum):
    NO_OWNER = "NO_OWNER"
    ISSUE = "ISSUE"
    DUPLICATE_REISSUE = "DUPLICATE_REISSUE"
    ADVANCED_ISSUE = "ADVANCED_ISSUE"
    PRECOMMIT_ABORTED = "PRECOMMIT_ABORTED"
    IRREVERSIBLE_FAULT = "IRREVERSIBLE_FAULT"
    FAULT_CONTAINMENT = "FAULT_CONTAINMENT"
    FAULT_RELEASED = "FAULT_RELEASED"
    COMPLETED = "COMPLETED"
    STOCHASTIC_RELEASE = "STOCHASTIC_RELEASE"
    TURN_RELEASE = "TURN_RELEASE"
    GAME_RELEASE = "GAME_RELEASE"


class TransactionStoreError(ValueError):
    """Raised when a caller violates an owner or commit boundary."""


def _is_exact_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_exact_ref(ref_value: PhysicalRef) -> None:
    if not isinstance(ref_value, PhysicalRef):
        raise ValueError("transaction references must be PhysicalRef values")
    if (
        not _is_exact_int(ref_value.card_id)
        or int(ref_value.card_id) <= 0
        or not _is_exact_int(ref_value.serial)
        or int(ref_value.serial) < 0
        or not _is_exact_int(ref_value.owner)
        or int(ref_value.owner) not in (0, 1)
        or not _is_exact_int(ref_value.zone)
        or int(ref_value.zone) <= 0
    ):
        raise ValueError(
            "transaction references require exact card, serial, owner, and zone"
        )


def _normalize_refs(refs: Sequence[PhysicalRef]) -> Tuple[PhysicalRef, ...]:
    values = tuple(refs)
    for ref_value in values:
        _require_exact_ref(ref_value)
    identities = tuple((int(ref.owner), int(ref.serial)) for ref in values)
    if len(set(identities)) != len(identities):
        raise ValueError("transaction references cannot repeat one physical card")
    return tuple(sorted(values, key=lambda value: value.sort_key()))


def _validate_persisted_action_spec(action_spec: ActionSpec) -> None:
    if len(set(action_spec.choices)) != len(action_spec.choices):
        raise ValueError("transaction action_spec cannot repeat a semantic choice")
    for key in action_spec.choices:
        if not _is_exact_int(key.option_type) or key.option_type < 0:
            raise ValueError("transaction option_type must be an exact integer")
        if key.source_index is not None:
            raise ValueError("transaction action_spec cannot persist a raw source_index")
        if key.relation is not None:
            raise ValueError("transaction action_spec cannot persist a raw target relation")
        if any(value is not None for value in (key.card_id, key.card_serial, key.source_zone)):
            if (
                not _is_exact_int(key.card_id)
                or key.card_id <= 0
                or not _is_exact_int(key.card_serial)
                or key.card_serial < 0
                or not _is_exact_int(key.player_index)
                or key.player_index not in (0, 1)
                or not _is_exact_int(key.source_zone)
                or key.source_zone <= 0
            ):
                raise ValueError(
                    "persisted card actions require card ID, serial, owner, and zone"
                )
        if key.target_lineage_serial is not None and (
            not _is_exact_int(key.target_lineage_serial)
            or key.target_lineage_serial < 0
            or not _is_exact_int(key.target_zone)
            or key.target_zone <= 0
        ):
            raise ValueError("persisted target lineage requires an exact target zone")
        if key.target_zone in (int(AreaType.ACTIVE), int(AreaType.BENCH)) and (
            not _is_exact_int(key.target_lineage_serial)
            or key.target_lineage_serial < 0
        ):
            raise ValueError("in-play transaction targets require a lineage serial")
        if key.option_type == int(OptionType.ATTACK) and (
            not _is_exact_int(key.attack_id) or key.attack_id <= 0
        ):
            raise ValueError("persisted ATTACK actions require a positive attack_id")


@dataclass(frozen=True)
class TransactionStep:
    stage: TransactionStage
    expected_select_type: int
    expected_context: int
    expected_min_count: int
    expected_max_count: int
    action_spec: ActionSpec
    irreversible_on_emit: bool
    expected_effect_ref: Optional[PhysicalRef] = None
    expected_context_ref: Optional[PhysicalRef] = None
    effect_or_attack_id: Optional[int] = None
    stochastic_boundary: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "stage", TransactionStage(self.stage))
        if self.stage in (
            TransactionStage.COMPLETE,
            TransactionStage.FAULT_CONTAINMENT,
        ):
            raise ValueError("terminal stages cannot be declared as executable steps")
        if not _is_exact_int(self.expected_select_type) or self.expected_select_type < 0:
            raise ValueError(
                "expected_select_type must be a non-negative exact integer"
            )
        if not _is_exact_int(self.expected_context) or self.expected_context < 0:
            raise ValueError("expected_context must be a non-negative exact integer")
        if (
            not _is_exact_int(self.expected_min_count)
            or not _is_exact_int(self.expected_max_count)
            or self.expected_min_count < 0
            or self.expected_max_count < self.expected_min_count
        ):
            raise ValueError("transaction step requires a valid min/max count")
        if not isinstance(self.action_spec, ActionSpec):
            raise ValueError("transaction step action_spec must be an ActionSpec")
        _validate_persisted_action_spec(self.action_spec)
        if not isinstance(self.irreversible_on_emit, bool):
            raise ValueError("irreversible_on_emit must be boolean")
        if not (
            self.expected_min_count
            <= len(self.action_spec.choices)
            <= self.expected_max_count
        ):
            raise ValueError("transaction action count is outside the expected bounds")
        if self.expected_effect_ref is not None:
            _require_exact_ref(self.expected_effect_ref)
        if self.expected_context_ref is not None:
            _require_exact_ref(self.expected_context_ref)
        if self.effect_or_attack_id is not None and (
            not _is_exact_int(self.effect_or_attack_id)
            or self.effect_or_attack_id <= 0
        ):
            raise ValueError("effect_or_attack_id must be None or a positive exact integer")
        if not isinstance(self.stochastic_boundary, bool):
            raise ValueError("stochastic_boundary must be boolean")

    def canonical(self) -> Tuple[object, ...]:
        return (
            self.stage.value,
            self.expected_select_type,
            self.expected_context,
            self.expected_min_count,
            self.expected_max_count,
            self.action_spec.canonical_choices(),
            bool(self.action_spec.order_sensitive),
            self.irreversible_on_emit,
            (
                None
                if self.expected_effect_ref is None
                else self.expected_effect_ref.sort_key()
            ),
            (
                None
                if self.expected_context_ref is None
                else self.expected_context_ref.sort_key()
            ),
            self.effect_or_attack_id,
            self.stochastic_boundary,
        )


@dataclass(frozen=True)
class TransactionPlan:
    transaction_id: str
    owner_kind: OwnerKind
    game_epoch: int
    seat: int
    turn: int
    start_action_count: int
    source_ref: Optional[PhysicalRef]
    target_refs: Tuple[PhysicalRef, ...]
    reserved_refs: Tuple[PhysicalRef, ...]
    initiation: TransactionStep
    steps: Tuple[TransactionStep, ...]

    def __post_init__(self) -> None:
        if (
            not isinstance(self.transaction_id, str)
            or not self.transaction_id
            or self.transaction_id != self.transaction_id.strip()
        ):
            raise ValueError("transaction_id must be a non-empty trimmed string")
        owner_kind = OwnerKind(self.owner_kind)
        if owner_kind == OwnerKind.FAULT_CONTAINMENT:
            raise ValueError("FAULT_CONTAINMENT is reserved for the store")
        if not _is_exact_int(self.game_epoch) or self.game_epoch < 0:
            raise ValueError("game_epoch must be a non-negative exact integer")
        if not _is_exact_int(self.seat) or self.seat not in (0, 1):
            raise ValueError("transaction seat must be 0 or 1")
        if not _is_exact_int(self.turn) or self.turn < 0:
            raise ValueError("transaction turn must be a non-negative exact integer")
        if (
            not _is_exact_int(self.start_action_count)
            or self.start_action_count < 0
        ):
            raise ValueError("start_action_count must be a non-negative exact integer")
        if self.source_ref is not None:
            _require_exact_ref(self.source_ref)
            if self.source_ref.owner != self.seat:
                raise ValueError("transaction source must be owned by the acting seat")
        target_refs = _normalize_refs(self.target_refs)
        reserved_refs = _normalize_refs(self.reserved_refs)
        if any(ref_value.owner != self.seat for ref_value in reserved_refs):
            raise ValueError("reserved transaction resources must belong to the acting seat")
        if not isinstance(self.initiation, TransactionStep):
            raise ValueError("transaction plan requires an initiation step")
        if self.initiation.stage != TransactionStage.INITIATION:
            raise ValueError("transaction initiation must use the INITIATION stage")
        steps = tuple(self.steps)
        if any(not isinstance(step, TransactionStep) for step in steps):
            raise ValueError("transaction continuation steps must be TransactionStep values")
        all_steps = (self.initiation,) + steps
        stochastic_indices = tuple(
            index for index, step in enumerate(all_steps) if step.stochastic_boundary
        )
        if stochastic_indices and stochastic_indices != (len(all_steps) - 1,):
            raise ValueError("a stochastic boundary must be the final transaction step")
        object.__setattr__(self, "owner_kind", owner_kind)
        object.__setattr__(self, "target_refs", target_refs)
        object.__setattr__(self, "reserved_refs", reserved_refs)
        object.__setattr__(self, "steps", steps)

    @property
    def semantic_action_specs(self) -> Tuple[ActionSpec, ...]:
        return (self.initiation.action_spec,) + tuple(
            step.action_spec for step in self.steps
        )

    def digest(self) -> str:
        payload = {
            "transaction_id": self.transaction_id,
            "owner_kind": self.owner_kind.value,
            "game_epoch": self.game_epoch,
            "seat": self.seat,
            "turn": self.turn,
            "start_action_count": self.start_action_count,
            "source_ref": (
                None if self.source_ref is None else self.source_ref.sort_key()
            ),
            "target_refs": [ref_value.sort_key() for ref_value in self.target_refs],
            "reserved_refs": [ref_value.sort_key() for ref_value in self.reserved_refs],
            "initiation": self.initiation.canonical(),
            "steps": [step.canonical() for step in self.steps],
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


_STATE_ISSUER_TOKEN = object()


@dataclass(frozen=True)
class TransactionState:
    transaction_id: str
    plan_digest: str
    owner_kind: OwnerKind
    origin_owner_kind: OwnerKind
    stage: TransactionStage
    game_epoch: int
    seat: int
    turn: int
    start_action_count: int
    source_ref: Optional[PhysicalRef]
    target_refs: Tuple[PhysicalRef, ...]
    reserved_refs: Tuple[PhysicalRef, ...]
    expected_effect_ref: Optional[PhysicalRef]
    expected_context_ref: Optional[PhysicalRef]
    expected_select_type: int
    expected_context: int
    expected_min_count: int
    expected_max_count: int
    last_prompt_fingerprint: Optional[PromptFingerprint]
    last_action_spec: Optional[ActionSpec]
    semantic_action_specs: Tuple[ActionSpec, ...]
    step_index: int
    callback_budget_used: int
    committed: bool
    fault_latched: bool
    fault_code: Optional[str]
    _issuer_token: object = dataclass_field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer_token is not _STATE_ISSUER_TOKEN:
            raise ValueError("TransactionState values must be created by TransactionStore")


@dataclass(frozen=True)
class FaultRecord:
    transaction_id: str
    origin_owner_kind: OwnerKind
    stage: TransactionStage
    game_epoch: int
    seat: int
    turn: int
    code: str


@dataclass(frozen=True)
class StartResult:
    status: StartStatus
    action_spec: Optional[ActionSpec]
    bound_action: Optional[Tuple[int, ...]]
    owner: Optional[TransactionState]
    reasons: Tuple[str, ...]


@dataclass(frozen=True)
class ResumeResult:
    status: ResumeStatus
    action_spec: Optional[ActionSpec]
    bound_action: Optional[Tuple[int, ...]]
    owner: Optional[TransactionState]
    reasons: Tuple[str, ...]


def _public_known_refs(state: PublicState) -> frozenset[PhysicalRef]:
    refs = []
    for player in (state.own, state.opponent):
        refs.extend(player.hand_refs)
        refs.extend(player.discard_refs)
        refs.extend(player.prize_refs)
        for pokemon in player.active + player.bench:
            refs.append(pokemon.ref)
            refs.extend(pokemon.energy_refs)
            refs.extend(pokemon.tool_refs)
            refs.extend(pokemon.pre_evolution_refs)
    refs.extend(state.stadium_refs)
    refs.extend(state.looking_refs)
    return frozenset(refs)


def _stable_main(state: PublicState) -> bool:
    return is_stable_main_state(state)


def _source_identity_matches(
    expected: Optional[PhysicalRef],
    actual: Optional[PhysicalRef],
) -> bool:
    if expected is None or actual is None:
        return expected is None and actual is None
    return (
        expected.card_id == actual.card_id
        and expected.serial == actual.serial
        and expected.owner == actual.owner
    )


def _legal_option_index_reasons(
    legal_options: Sequence[SemanticOption],
) -> Tuple[str, ...]:
    indices = tuple(option.index for option in legal_options)
    exact_indices = tuple(
        index
        for index in indices
        if _is_exact_int(index)
    )
    reasons = []
    if len(exact_indices) != len(indices) or any(
        index < 0 or index >= len(legal_options)
        for index in exact_indices
    ):
        reasons.append("LEGAL_OPTION_INDEX_INVALID")
    if len(set(exact_indices)) != len(exact_indices):
        reasons.append("LEGAL_OPTION_INDEX_COLLISION")
    if set(exact_indices) != set(range(len(legal_options))):
        reasons.append("LEGAL_OPTION_INDEX_SET_INCOMPLETE")
    return tuple(reasons)


def _prompt_match_reasons(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    step: TransactionStep,
) -> Tuple[Tuple[str, ...], Optional[Tuple[int, ...]]]:
    reasons = list(_legal_option_index_reasons(legal_options))
    if state.select_type != step.expected_select_type:
        reasons.append("UNEXPECTED_SELECT_TYPE")
    if state.select_context != step.expected_context:
        reasons.append("UNEXPECTED_CONTEXT")
    if state.min_count != step.expected_min_count:
        reasons.append("UNEXPECTED_MIN_COUNT")
    if state.max_count != step.expected_max_count:
        reasons.append("UNEXPECTED_MAX_COUNT")
    if not _source_identity_matches(step.expected_effect_ref, state.effect_ref):
        reasons.append("UNEXPECTED_EFFECT_REF")
    if not _source_identity_matches(step.expected_context_ref, state.context_ref):
        reasons.append("UNEXPECTED_CONTEXT_REF")
    bound = None
    try:
        bound = tuple(
            step.action_spec.bind(
                legal_options,
                min_count=step.expected_min_count,
                max_count=step.expected_max_count,
            )
        )
    except SemanticBindError:
        reasons.append("SEMANTIC_BIND_FAILURE")
    unique_reasons = tuple(sorted(set(reasons)))
    return unique_reasons, None if unique_reasons else bound


class TransactionStore:
    """Mutable runtime store containing zero or one immutable owner state."""

    def __init__(self) -> None:
        self._plan: Optional[TransactionPlan] = None
        self._owner: Optional[TransactionState] = None
        self._fault_history: Tuple[FaultRecord, ...] = ()

    @property
    def owner(self) -> Optional[TransactionState]:
        return self._owner

    @property
    def has_owner(self) -> bool:
        return self._owner is not None

    @property
    def run_fault_latched(self) -> bool:
        return bool(self._fault_history)

    @property
    def fault_history(self) -> Tuple[FaultRecord, ...]:
        return self._fault_history

    def reset_run(self) -> None:
        if self._owner is not None:
            raise TransactionStoreError(
                "cannot reset run state while a transaction owner is active"
            )
        self._plan = None
        self._owner = None
        self._fault_history = ()

    def _release_owner(self) -> None:
        self._plan = None
        self._owner = None

    def start(
        self,
        plan: TransactionPlan,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
    ) -> StartResult:
        if not isinstance(plan, TransactionPlan):
            raise ValueError("start requires a TransactionPlan")
        if self._owner is not None:
            return StartResult(
                StartStatus.OWNER_COLLISION,
                None,
                None,
                self._owner,
                ("OWNER_COLLISION",),
            )
        reasons = []
        if (
            plan.game_epoch != state.game_epoch
            or plan.seat != state.seat
            or plan.turn != state.turn
            or plan.start_action_count != state.turn_action_count
            or state.result != -1
        ):
            reasons.append("PLAN_STATE_IDENTITY_MISMATCH")
        known_refs = _public_known_refs(state)
        declared_refs = (
            (() if plan.source_ref is None else (plan.source_ref,))
            + plan.target_refs
            + plan.reserved_refs
        )
        if any(ref_value not in known_refs for ref_value in declared_refs):
            reasons.append("PLAN_REF_NOT_IN_STATE")
        if reasons:
            return StartResult(
                StartStatus.PLAN_STATE_MISMATCH,
                None,
                None,
                None,
                tuple(sorted(set(reasons))),
            )

        initiation_reasons, bound = _prompt_match_reasons(
            state,
            legal_options,
            plan.initiation,
        )
        if initiation_reasons:
            return StartResult(
                StartStatus.PLAN_STATE_MISMATCH,
                None,
                None,
                None,
                initiation_reasons,
            )
        prompt = make_prompt_fingerprint(
            state,
            legal_options,
            owner_kind=plan.owner_kind.value,
            stage=plan.initiation.stage.value,
            effect_or_attack_id=plan.initiation.effect_or_attack_id,
        )
        owner = TransactionState(
            transaction_id=plan.transaction_id,
            plan_digest=plan.digest(),
            owner_kind=plan.owner_kind,
            origin_owner_kind=plan.owner_kind,
            stage=plan.initiation.stage,
            game_epoch=plan.game_epoch,
            seat=plan.seat,
            turn=plan.turn,
            start_action_count=plan.start_action_count,
            source_ref=plan.source_ref,
            target_refs=plan.target_refs,
            reserved_refs=plan.reserved_refs,
            expected_effect_ref=plan.initiation.expected_effect_ref,
            expected_context_ref=plan.initiation.expected_context_ref,
            expected_select_type=plan.initiation.expected_select_type,
            expected_context=plan.initiation.expected_context,
            expected_min_count=plan.initiation.expected_min_count,
            expected_max_count=plan.initiation.expected_max_count,
            last_prompt_fingerprint=prompt,
            last_action_spec=plan.initiation.action_spec,
            semantic_action_specs=plan.semantic_action_specs,
            step_index=-1,
            callback_budget_used=1,
            committed=plan.initiation.irreversible_on_emit,
            fault_latched=False,
            fault_code=None,
            _issuer_token=_STATE_ISSUER_TOKEN,
        )
        self._plan = plan
        self._owner = owner
        return StartResult(
            StartStatus.STARTED,
            plan.initiation.action_spec,
            bound,
            owner,
            (),
        )

    def abort_precommit(
        self,
        transaction_id: str,
        reason: str,
    ) -> ResumeResult:
        if self._owner is None:
            return ResumeResult(
                ResumeStatus.NO_OWNER,
                None,
                None,
                None,
                ("NO_OWNER",),
            )
        if transaction_id != self._owner.transaction_id:
            raise TransactionStoreError("transaction_id does not match active owner")
        if self._owner.committed:
            raise TransactionStoreError("a committed transaction cannot be precommit-aborted")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("abort reason must be non-empty")
        reasons = (reason.strip(),)
        self._release_owner()
        return ResumeResult(
            ResumeStatus.PRECOMMIT_ABORTED,
            None,
            None,
            None,
            reasons,
        )

    def _latch_fault(self, code: str) -> TransactionState:
        if self._owner is None:
            raise TransactionStoreError("cannot latch fault without an owner")
        if not self._owner.committed:
            raise TransactionStoreError("irreversible fault requires a committed owner")
        normalized_code = code.strip() if isinstance(code, str) else ""
        if not normalized_code:
            normalized_code = "IRREVERSIBLE_FAULT"
        if not self._owner.fault_latched:
            record = FaultRecord(
                transaction_id=self._owner.transaction_id,
                origin_owner_kind=self._owner.origin_owner_kind,
                stage=self._owner.stage,
                game_epoch=self._owner.game_epoch,
                seat=self._owner.seat,
                turn=self._owner.turn,
                code=normalized_code,
            )
            self._fault_history = self._fault_history + (record,)
        self._owner = replace(
            self._owner,
            owner_kind=OwnerKind.FAULT_CONTAINMENT,
            stage=TransactionStage.FAULT_CONTAINMENT,
            fault_latched=True,
            fault_code=normalized_code,
        )
        return self._owner

    def latch_fault(
        self,
        transaction_id: str,
        reason: str,
    ) -> ResumeResult:
        if self._owner is None:
            return ResumeResult(
                ResumeStatus.NO_OWNER,
                None,
                None,
                None,
                ("NO_OWNER",),
            )
        if transaction_id != self._owner.transaction_id:
            raise TransactionStoreError("transaction_id does not match active owner")
        if not self._owner.committed:
            raise TransactionStoreError(
                "an uncommitted transaction must use abort_precommit"
            )
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("fault reason must be non-empty")
        owner = self._latch_fault(reason.strip())
        return ResumeResult(
            ResumeStatus.IRREVERSIBLE_FAULT,
            None,
            None,
            owner,
            (reason.strip(),),
        )

    def _failure_result(
        self,
        reasons: Sequence[str],
    ) -> ResumeResult:
        reason_values = tuple(sorted(set(reasons)))
        if self._owner is None:
            return ResumeResult(
                ResumeStatus.NO_OWNER,
                None,
                None,
                None,
                reason_values,
            )
        if not self._owner.committed:
            self._release_owner()
            return ResumeResult(
                ResumeStatus.PRECOMMIT_ABORTED,
                None,
                None,
                None,
                reason_values,
            )
        owner = self._latch_fault(
            "IRREVERSIBLE_FAULT:{0}".format("|".join(reason_values))
        )
        return ResumeResult(
            ResumeStatus.IRREVERSIBLE_FAULT,
            None,
            None,
            owner,
            reason_values,
        )

    def _issue_step(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
        step_index: int,
        status: ResumeStatus,
    ) -> ResumeResult:
        if self._owner is None or self._plan is None:
            raise TransactionStoreError("cannot issue without an active owner")
        step = self._plan.steps[step_index]
        reasons, bound = _prompt_match_reasons(state, legal_options, step)
        if reasons:
            return self._failure_result(reasons)
        prompt = make_prompt_fingerprint(
            state,
            legal_options,
            owner_kind=self._owner.origin_owner_kind.value,
            stage=step.stage.value,
            effect_or_attack_id=step.effect_or_attack_id,
        )
        self._owner = replace(
            self._owner,
            owner_kind=self._owner.origin_owner_kind,
            stage=step.stage,
            expected_effect_ref=step.expected_effect_ref,
            expected_context_ref=step.expected_context_ref,
            expected_select_type=step.expected_select_type,
            expected_context=step.expected_context,
            expected_min_count=step.expected_min_count,
            expected_max_count=step.expected_max_count,
            last_prompt_fingerprint=prompt,
            last_action_spec=step.action_spec,
            step_index=step_index,
            callback_budget_used=self._owner.callback_budget_used + 1,
            committed=(
                self._owner.committed
                or step.irreversible_on_emit
            ),
        )
        return ResumeResult(
            status,
            step.action_spec,
            bound,
            self._owner,
            (),
        )

    def resume(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
    ) -> ResumeResult:
        if self._owner is None or self._plan is None:
            return ResumeResult(ResumeStatus.NO_OWNER, None, None, None, ())

        if state.game_epoch != self._owner.game_epoch:
            self._release_owner()
            return ResumeResult(
                ResumeStatus.GAME_RELEASE,
                None,
                None,
                None,
                ("GAME_EPOCH_CHANGED",),
            )
        if (
            state.seat != self._owner.seat
            or state.turn != self._owner.turn
            or state.result != -1
        ):
            self._release_owner()
            return ResumeResult(
                ResumeStatus.TURN_RELEASE,
                None,
                None,
                None,
                ("TURN_OR_RESULT_CHANGED",),
            )

        if self._owner.fault_latched:
            if _stable_main(state):
                self._release_owner()
                return ResumeResult(
                    ResumeStatus.FAULT_RELEASED,
                    None,
                    None,
                    None,
                    ("FAULT_BOUNDARY_REACHED",),
                )
            return ResumeResult(
                ResumeStatus.FAULT_CONTAINMENT,
                None,
                None,
                self._owner,
                (self._owner.fault_code or "IRREVERSIBLE_FAULT",),
            )

        last_action_count = (
            None
            if self._owner.last_prompt_fingerprint is None
            else self._owner.last_prompt_fingerprint.turn_action_count
        )
        if (
            state.turn_action_count < self._owner.start_action_count
            or (
                last_action_count is not None
                and state.turn_action_count < last_action_count
            )
        ):
            return self._failure_result(("TURN_ACTION_COUNT_REGRESSED",))

        current_step = (
            self._plan.initiation
            if self._owner.step_index == -1
            else self._plan.steps[self._owner.step_index]
        )
        if self._owner.last_prompt_fingerprint is None:
            raise TransactionStoreError(
                "active owner is missing its atomic emission record"
            )

        current_prompt = make_prompt_fingerprint(
            state,
            legal_options,
            owner_kind=self._owner.origin_owner_kind.value,
            stage=current_step.stage.value,
            effect_or_attack_id=current_step.effect_or_attack_id,
        )
        if (
            current_prompt.digest()
            == self._owner.last_prompt_fingerprint.digest()
        ):
            reasons, bound = _prompt_match_reasons(
                state,
                legal_options,
                current_step,
            )
            if reasons:
                return self._failure_result(reasons)
            return ResumeResult(
                ResumeStatus.DUPLICATE_REISSUE,
                current_step.action_spec,
                bound,
                self._owner,
                (),
            )

        if current_step.stochastic_boundary:
            if _stable_main(state):
                self._release_owner()
                return ResumeResult(
                    ResumeStatus.STOCHASTIC_RELEASE,
                    None,
                    None,
                    None,
                    ("STOCHASTIC_BOUNDARY_REPLAN",),
                )
            return self._failure_result(
                ("UNEXPECTED_PROMPT_AFTER_STOCHASTIC_STEP",)
            )

        next_index = self._owner.step_index + 1
        if next_index >= len(self._plan.steps):
            if _stable_main(state):
                self._release_owner()
                return ResumeResult(
                    ResumeStatus.COMPLETED,
                    None,
                    None,
                    None,
                    (),
                )
            return self._failure_result(("UNEXPECTED_PROMPT_AFTER_FINAL_STEP",))

        return self._issue_step(
            state,
            legal_options,
            next_index,
            ResumeStatus.ADVANCED_ISSUE,
        )


__all__ = [
    "FaultRecord",
    "OwnerKind",
    "ResumeResult",
    "ResumeStatus",
    "StartResult",
    "StartStatus",
    "TransactionPlan",
    "TransactionStage",
    "TransactionState",
    "TransactionStep",
    "TransactionStore",
    "TransactionStoreError",
]
