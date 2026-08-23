"""One-owner transaction state machine with fail-closed prompt rebinding."""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field, replace
from enum import Enum
import hashlib
import json
from collections import Counter
from typing import Optional, Sequence, Tuple

try:  # Package import in tests.
    from .state_view import (
        ActionSpec,
        AreaType,
        LogType,
        OptionType,
        PhysicalRef,
        PromptFingerprint,
        PublicReceiptEvent,
        PublicState,
        SelectContext,
        SelectType,
        public_state_fingerprint,
        SemanticBindError,
        SemanticOption,
        SemanticOptionKey,
        is_stable_main_state,
        make_prompt_fingerprint,
    )
    from .resource_ledger import (
        DeckAvailabilityProof,
        FIXED_DECK_COUNTER_HASH,
        FIXED_DECK_SIZE,
        prove_deck_availability_from_state,
    )
except ImportError:  # Flat submission import from main.py.
    from state_view import (
        ActionSpec,
        AreaType,
        LogType,
        OptionType,
        PhysicalRef,
        PromptFingerprint,
        PublicReceiptEvent,
        PublicState,
        SelectContext,
        SelectType,
        public_state_fingerprint,
        SemanticBindError,
        SemanticOption,
        SemanticOptionKey,
        is_stable_main_state,
        make_prompt_fingerprint,
    )
    from resource_ledger import (
        DeckAvailabilityProof,
        FIXED_DECK_COUNTER_HASH,
        FIXED_DECK_SIZE,
        prove_deck_availability_from_state,
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


class TerminalReceiptProfile(str, Enum):
    POKE_PAD_SEARCH = "POKE_PAD_SEARCH"
    FIGHTING_GONG_SEARCH = "FIGHTING_GONG_SEARCH"
    LUNAR_CYCLE = "LUNAR_CYCLE"
    AURA_JAB = "AURA_JAB"
    ULTRA_BALL = "ULTRA_BALL"
    BOSS_GUST = "BOSS_GUST"
    HARIYAMA_GUST = "HARIYAMA_GUST"
    WALLY_REBOOT = "WALLY_REBOOT"
    SWITCH = "SWITCH"


class TerminalReceiptStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    UNKNOWN = "UNKNOWN"


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


# B_ML_AURA_CONTEXT_REF_BINDING_REPAIR_V2.  These are deliberately emitted as
# transaction reason codes rather than a new telemetry framework so existing
# transaction records retain the full before/after owner state.
AURA_CTXREF_CAPTURE_RULE = "R_ML_AURA_CTXREF_CAPTURE_AFTER_ENERGY_V2"
AURA_CTXREF_BIND_RULE = "R_ML_AURA_CTXREF_BIND_TARGET_STEP_V2"
AURA_CTXREF_OWNER_RULE = "R_ML_AURA_CTXREF_VALIDATE_OWNER_V2"
AURA_CTXREF_COMPLETE_RULE = "R_ML_AURA_CTXREF_COMPLETE_TARGET_V2"
AURA_CTXREF_AMBIGUOUS_RULE = "R_ML_AURA_CTXREF_REJECT_AMBIGUOUS_V2"
AURA_CTXREF_RELEASE_RULE = "R_ML_AURA_CTXREF_RELEASE_OWNER_V2"

# B_ML_AURA_ORDERED_MULTI_TARGET_FSM_REPAIR_V4.  The V4 identifiers are kept
# explicit because the transaction stream is the audit trail for this repair.
# They intentionally do not encode a card serial, a context number, or a
# fixed target count.
AURA_V4_SUPPORTED_ENERGY_COUNTS = frozenset({1, 2, 3})
AURA_V4_CAPTURE_SELECTED_QUEUE_RULE = "R_ML_AURA_V4_CAPTURE_SELECTED_QUEUE"
AURA_V4_VALIDATE_SELECTED_SET_RULE = "R_ML_AURA_V4_VALIDATE_SELECTED_SET"
AURA_V4_BIND_CALLBACK_REF_RULE = "R_ML_AURA_V4_BIND_CALLBACK_REF"
AURA_V4_VALIDATE_CALLBACK_ORDER_RULE = "R_ML_AURA_V4_VALIDATE_CALLBACK_ORDER"
AURA_V4_ACCEPT_TARGET_RECEIPT_RULE = "R_ML_AURA_V4_ACCEPT_TARGET_RECEIPT"
AURA_V4_ADVANCE_TARGET_CURSOR_RULE = "R_ML_AURA_V4_ADVANCE_TARGET_CURSOR"
AURA_V4_COMPLETE_AFTER_ALL_RECEIPTS_RULE = "R_ML_AURA_V4_COMPLETE_AFTER_ALL_RECEIPTS"
AURA_V4_REJECT_CALLBACK_MISMATCH_RULE = "R_ML_AURA_V4_REJECT_CALLBACK_MISMATCH"
AURA_V4_RELEASE_OWNER_RULE = "R_ML_AURA_V4_RELEASE_OWNER"

# Exact V4 reason codes.  Keeping these as constants prevents a telemetry
# consumer from having to infer a failure from a free-form message.
AURA_V4_UNSUPPORTED_ENERGY_COUNT = "AURA_V4_UNSUPPORTED_ENERGY_COUNT"
AURA_V4_SELECTED_ORDER_UNAVAILABLE = "AURA_V4_SELECTED_ORDER_UNAVAILABLE"
AURA_V4_SELECTED_COUNT_PLAN_MISMATCH = "AURA_V4_SELECTED_COUNT_PLAN_MISMATCH"
AURA_V4_SELECTED_SET_RESERVED_MISMATCH = "AURA_V4_SELECTED_SET_RESERVED_MISMATCH"
AURA_V4_DUPLICATE_SELECTED_REF = "AURA_V4_DUPLICATE_SELECTED_REF"
AURA_V4_CALLBACK_REF_MISSING = "AURA_V4_CALLBACK_REF_MISSING"
AURA_V4_CALLBACK_REF_NOT_SELECTED = "AURA_V4_CALLBACK_REF_NOT_SELECTED"
AURA_V4_CALLBACK_REF_ALREADY_CONSUMED = "AURA_V4_CALLBACK_REF_ALREADY_CONSUMED"
AURA_V4_CALLBACK_ORDER_MISMATCH = "AURA_V4_CALLBACK_ORDER_MISMATCH"
AURA_V4_CALLBACK_OWNER_MISMATCH = "AURA_V4_CALLBACK_OWNER_MISMATCH"
AURA_V4_CALLBACK_TRANSACTION_MISMATCH = "AURA_V4_CALLBACK_TRANSACTION_MISMATCH"
AURA_V4_CALLBACK_PROMPT_TYPE_MISMATCH = "AURA_V4_CALLBACK_PROMPT_TYPE_MISMATCH"
AURA_V4_TARGET_CONTEXT_MISMATCH = "AURA_V4_TARGET_CONTEXT_MISMATCH"
AURA_V4_TARGET_REF_MISMATCH = "AURA_V4_TARGET_REF_MISMATCH"
AURA_V4_TARGET_OWNER_MISMATCH = "AURA_V4_TARGET_OWNER_MISMATCH"
AURA_V4_TARGET_RECEIPT_MISSING = "AURA_V4_TARGET_RECEIPT_MISSING"
AURA_V4_ATTACH_RECEIPT_MISSING = "AURA_V4_ATTACH_RECEIPT_MISSING"
AURA_V4_EXTRA_CALLBACK_AFTER_COMPLETE = "AURA_V4_EXTRA_CALLBACK_AFTER_COMPLETE"
AURA_V4_RELEASE_COUNT_MISMATCH = "AURA_V4_RELEASE_COUNT_MISMATCH"

# Compatibility aliases are retained for callers of the preliminary local
# candidate.  They now point to the exact V4 rule IDs and are not emitted as
# an additional rule family.
AURA_MULTI_CALLBACK_CAPTURE_RULE = AURA_V4_CAPTURE_SELECTED_QUEUE_RULE
AURA_MULTI_CALLBACK_CONSUME_RULE = AURA_V4_ACCEPT_TARGET_RECEIPT_RULE
AURA_MULTI_CALLBACK_BIND_RULE = AURA_V4_BIND_CALLBACK_REF_RULE
AURA_MULTI_CALLBACK_RECEIPT_RULE = AURA_V4_ACCEPT_TARGET_RECEIPT_RULE
AURA_MULTI_CALLBACK_COMPLETE_RULE = AURA_V4_COMPLETE_AFTER_ALL_RECEIPTS_RULE
AURA_MULTI_CALLBACK_RELEASE_RULE = AURA_V4_RELEASE_OWNER_RULE

# B_ML_AURA_TERMINAL_RECEIPT_TURN_BOUNDARY_REPAIR_V1.  The pending marker is
# a transaction-local receipt-wait state, not a receipt generator or a turn
# transition exemption.  It is consumed exactly once only after the final
# single-energy Aura callback has been issued.
AURA_TERMINAL_PENDING_RECEIPT_STORE_RULE = (
    "R_ML_AURA_TERMINAL_RECEIPT_STORE_PENDING_V1"
)
AURA_TERMINAL_PENDING_RECEIPT_CONSUME_RULE = (
    "R_ML_AURA_TERMINAL_RECEIPT_CONSUME_NEXT_CALLBACK_V1"
)
AURA_TERMINAL_PENDING_RECEIPT_REJECT_RULE = (
    "R_ML_AURA_TERMINAL_RECEIPT_REJECT_PENDING_MISMATCH_V1"
)
AURA_TERMINAL_PENDING_RECEIPT_MISMATCH = (
    "AURA_TERMINAL_PENDING_RECEIPT_MISMATCH"
)


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
            raise ValueError(
                "transaction action_spec cannot persist a raw source_index"
            )
        if key.relation is not None:
            raise ValueError(
                "transaction action_spec cannot persist a raw target relation"
            )
        if any(
            value is not None
            for value in (key.card_id, key.card_serial, key.source_zone)
        ):
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
        if key.source_lineage_serial is not None and (
            not _is_exact_int(key.source_lineage_serial)
            or key.source_lineage_serial < 0
            or key.source_zone not in (int(AreaType.ACTIVE), int(AreaType.BENCH))
        ):
            raise ValueError(
                "persisted source lineage requires an active or bench source zone"
            )
        if key.source_zone in (int(AreaType.ACTIVE), int(AreaType.BENCH)) and (
            not _is_exact_int(key.source_lineage_serial)
            or key.source_lineage_serial < 0
        ):
            raise ValueError("in-play transaction sources require a lineage serial")
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
class DeferredCardClassChoice:
    """A hidden-zone target policy materialized only after options are public."""

    ordered_card_id_classes: Tuple[Tuple[int, ...], ...]
    owner: int
    allowed_source_zones: Tuple[int, ...] = (int(AreaType.DECK),)
    option_type: int = int(OptionType.CARD)
    selection_count: int = 1
    require_match: bool = True
    availability_proof: Optional[DeckAvailabilityProof] = None

    def __post_init__(self) -> None:
        classes = tuple(tuple(card_ids) for card_ids in self.ordered_card_id_classes)
        if not classes or any(not card_ids for card_ids in classes):
            raise ValueError("deferred card classes must be non-empty")
        flattened = tuple(card_id for card_ids in classes for card_id in card_ids)
        if any(not _is_exact_int(card_id) or card_id <= 0 for card_id in flattened):
            raise ValueError("deferred card IDs must be positive exact integers")
        if len(set(flattened)) != len(flattened):
            raise ValueError("deferred card IDs cannot repeat across classes")
        if not _is_exact_int(self.owner) or self.owner not in (0, 1):
            raise ValueError("deferred choice owner must be 0 or 1")
        zones = tuple(self.allowed_source_zones)
        if not zones or any(not _is_exact_int(zone) or zone <= 0 for zone in zones):
            raise ValueError("deferred source zones must be positive exact integers")
        if len(set(zones)) != len(zones):
            raise ValueError("deferred source zones cannot repeat")
        if not _is_exact_int(self.option_type) or self.option_type < 0:
            raise ValueError("deferred option_type must be an exact integer")
        if self.selection_count != 1 or not _is_exact_int(self.selection_count):
            raise ValueError(
                "deferred card choice currently requires selection_count=1"
            )
        if self.availability_proof is not None and not isinstance(
            self.availability_proof, DeckAvailabilityProof
        ):
            raise ValueError("deferred availability proof has an invalid type")
        if not isinstance(self.require_match, bool):
            raise ValueError("deferred require_match must be boolean")
        object.__setattr__(self, "ordered_card_id_classes", classes)
        object.__setattr__(self, "allowed_source_zones", tuple(sorted(zones)))

    def canonical(self) -> Tuple[object, ...]:
        return (
            self.ordered_card_id_classes,
            self.owner,
            self.allowed_source_zones,
            self.option_type,
            self.selection_count,
            self.require_match,
            (
                None
                if self.availability_proof is None
                else self.availability_proof.canonical()
            ),
        )


@dataclass(frozen=True)
class TransactionStep:
    stage: TransactionStage
    expected_select_type: int
    expected_context: int
    expected_min_count: int
    expected_max_count: int
    action_spec: Optional[ActionSpec]
    irreversible_on_emit: bool
    expected_effect_ref: Optional[PhysicalRef] = None
    expected_context_ref: Optional[PhysicalRef] = None
    effect_or_attack_id: Optional[int] = None
    stochastic_boundary: bool = False
    deferred_card_choice: Optional[DeferredCardClassChoice] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "stage", TransactionStage(self.stage))
        if self.stage in (
            TransactionStage.COMPLETE,
            TransactionStage.FAULT_CONTAINMENT,
        ):
            raise ValueError("terminal stages cannot be declared as executable steps")
        if (
            not _is_exact_int(self.expected_select_type)
            or self.expected_select_type < 0
        ):
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
        has_action = isinstance(self.action_spec, ActionSpec)
        has_deferred = isinstance(
            self.deferred_card_choice,
            DeferredCardClassChoice,
        )
        if has_action == has_deferred:
            raise ValueError(
                "transaction step requires exactly one action_spec or deferred choice"
            )
        if self.action_spec is not None:
            _validate_persisted_action_spec(self.action_spec)
        if not isinstance(self.irreversible_on_emit, bool):
            raise ValueError("irreversible_on_emit must be boolean")
        action_count = (
            len(self.action_spec.choices)
            if self.action_spec is not None
            else self.deferred_card_choice.selection_count
        )
        if not self.expected_min_count <= action_count <= self.expected_max_count:
            raise ValueError("transaction action count is outside the expected bounds")
        if self.expected_effect_ref is not None:
            _require_exact_ref(self.expected_effect_ref)
        if self.expected_context_ref is not None:
            _require_exact_ref(self.expected_context_ref)
        if self.effect_or_attack_id is not None and (
            not _is_exact_int(self.effect_or_attack_id) or self.effect_or_attack_id <= 0
        ):
            raise ValueError(
                "effect_or_attack_id must be None or a positive exact integer"
            )
        if not isinstance(self.stochastic_boundary, bool):
            raise ValueError("stochastic_boundary must be boolean")

    def canonical(self) -> Tuple[object, ...]:
        return (
            self.stage.value,
            self.expected_select_type,
            self.expected_context,
            self.expected_min_count,
            self.expected_max_count,
            (
                None
                if self.action_spec is None
                else self.action_spec.canonical_choices()
            ),
            (
                None
                if self.action_spec is None
                else bool(self.action_spec.order_sensitive)
            ),
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
            (
                None
                if self.deferred_card_choice is None
                else self.deferred_card_choice.canonical()
            ),
        )


@dataclass(frozen=True)
class TerminalReceiptSpec:
    """Immutable, builder-selected terminal contract for one production route."""

    profile: TerminalReceiptProfile
    source_ref: PhysicalRef
    target_refs: Tuple[PhysicalRef, ...]
    reserved_refs: Tuple[PhysicalRef, ...]
    expected_play_card_id: Optional[int] = None
    expected_attack_id: Optional[int] = None
    expected_evolve_card_id: Optional[int] = None
    evolve_target_lineage_serial: Optional[int] = None
    expected_draw_count: int = 0
    start_deck_count: Optional[int] = None
    start_target_hp: Optional[int] = None
    start_target_max_hp: Optional[int] = None
    original_energy_refs: Tuple[PhysicalRef, ...] = ()
    allow_automatic_completion: bool = True
    allow_same_turn_completion: bool = True
    allow_turn_transition: bool = False
    missing_callback_is_fault: bool = True
    irreversible_fault_on_missing_receipt: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "profile", TerminalReceiptProfile(self.profile))
        _require_exact_ref(self.source_ref)
        target_refs = _normalize_refs(self.target_refs)
        reserved_refs = _normalize_refs(self.reserved_refs)
        original_energy_refs = _normalize_refs(self.original_energy_refs)
        for value in (
            self.expected_play_card_id,
            self.expected_attack_id,
            self.expected_evolve_card_id,
            self.evolve_target_lineage_serial,
            self.start_deck_count,
            self.start_target_hp,
            self.start_target_max_hp,
        ):
            if value is not None and (not _is_exact_int(value) or value < 0):
                raise ValueError("terminal receipt integer facts must be exact")
        if not _is_exact_int(self.expected_draw_count) or self.expected_draw_count < 0:
            raise ValueError("expected_draw_count must be a nonnegative exact int")
        policy_values = (
            self.allow_automatic_completion,
            self.allow_same_turn_completion,
            self.allow_turn_transition,
            self.missing_callback_is_fault,
            self.irreversible_fault_on_missing_receipt,
        )
        if any(not isinstance(value, bool) for value in policy_values):
            raise ValueError("terminal receipt policies must be boolean")
        if self.allow_turn_transition != (
            self.profile == TerminalReceiptProfile.AURA_JAB
        ):
            raise ValueError("only Aura Jab may allow a turn transition")
        object.__setattr__(self, "target_refs", target_refs)
        object.__setattr__(self, "reserved_refs", reserved_refs)
        object.__setattr__(self, "original_energy_refs", original_energy_refs)

    def canonical(self) -> Tuple[object, ...]:
        return (
            self.profile.value,
            self.source_ref.sort_key(),
            tuple(ref_value.sort_key() for ref_value in self.target_refs),
            tuple(ref_value.sort_key() for ref_value in self.reserved_refs),
            self.expected_play_card_id,
            self.expected_attack_id,
            self.expected_evolve_card_id,
            self.evolve_target_lineage_serial,
            self.expected_draw_count,
            self.start_deck_count,
            self.start_target_hp,
            self.start_target_max_hp,
            tuple(ref_value.sort_key() for ref_value in self.original_energy_refs),
            self.allow_automatic_completion,
            self.allow_same_turn_completion,
            self.allow_turn_transition,
            self.missing_callback_is_fault,
            self.irreversible_fault_on_missing_receipt,
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
    terminal_receipt: Optional[TerminalReceiptSpec] = None

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
        if not _is_exact_int(self.start_action_count) or self.start_action_count < 0:
            raise ValueError("start_action_count must be a non-negative exact integer")
        if self.source_ref is not None:
            _require_exact_ref(self.source_ref)
            if self.source_ref.owner != self.seat:
                raise ValueError("transaction source must be owned by the acting seat")
        target_refs = _normalize_refs(self.target_refs)
        reserved_refs = _normalize_refs(self.reserved_refs)
        if any(ref_value.owner != self.seat for ref_value in reserved_refs):
            raise ValueError(
                "reserved transaction resources must belong to the acting seat"
            )
        if not isinstance(self.initiation, TransactionStep):
            raise ValueError("transaction plan requires an initiation step")
        if self.initiation.stage != TransactionStage.INITIATION:
            raise ValueError("transaction initiation must use the INITIATION stage")
        if self.initiation.action_spec is None:
            raise ValueError("transaction initiation cannot use a deferred choice")
        steps = tuple(self.steps)
        if any(not isinstance(step, TransactionStep) for step in steps):
            raise ValueError(
                "transaction continuation steps must be TransactionStep values"
            )
        all_steps = (self.initiation,) + steps
        for step in all_steps:
            policy = step.deferred_card_choice
            if policy is None:
                continue
            if policy.owner != self.seat:
                raise ValueError(
                    "deferred choice owner must match the transaction seat"
                )
        stochastic_indices = tuple(
            index for index, step in enumerate(all_steps) if step.stochastic_boundary
        )
        if stochastic_indices and stochastic_indices != (len(all_steps) - 1,):
            raise ValueError("a stochastic boundary must be the final transaction step")
        object.__setattr__(self, "owner_kind", owner_kind)
        object.__setattr__(self, "target_refs", target_refs)
        object.__setattr__(self, "reserved_refs", reserved_refs)
        object.__setattr__(self, "steps", steps)
        if self.terminal_receipt is not None and not isinstance(
            self.terminal_receipt, TerminalReceiptSpec
        ):
            raise ValueError("terminal_receipt must be a TerminalReceiptSpec")

    @property
    def semantic_action_specs(self) -> Tuple[ActionSpec, ...]:
        return tuple(
            step.action_spec
            for step in (self.initiation,) + self.steps
            if step.action_spec is not None
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
            "terminal_receipt": (
                None if self.terminal_receipt is None
                else self.terminal_receipt.canonical()
            ),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


def build_poke_pad_core_search_plan(
    state: PublicState,
    source_ref: PhysicalRef,
    action_spec: ActionSpec,
    ordered_card_id_classes: Sequence[Sequence[int]],
    availability_proof: DeckAvailabilityProof,
    proof_digest: str,
) -> TransactionPlan:
    """Build the one approved Poke Pad initiation/search transaction."""

    if not isinstance(state, PublicState) or not _stable_main(state):
        raise ValueError("Poke Pad search plan requires stable MAIN")
    _require_exact_ref(source_ref)
    if (
        source_ref.card_id != 1152
        or source_ref.owner != state.seat
        or source_ref.zone != int(AreaType.HAND)
        or source_ref not in state.own.hand_refs
    ):
        raise ValueError("Poke Pad search source must be one exact own HAND card")
    if not isinstance(action_spec, ActionSpec) or len(action_spec.choices) != 1:
        raise ValueError("Poke Pad search plan requires one initiation action")
    _validate_persisted_action_spec(action_spec)
    key = action_spec.choices[0]
    if (
        key.option_type != int(OptionType.PLAY)
        or key.player_index != state.seat
        or key.card_id != source_ref.card_id
        or key.card_serial != source_ref.serial
        or key.source_zone != source_ref.zone
    ):
        raise ValueError("Poke Pad initiation must bind the exact physical source")
    if not isinstance(availability_proof, DeckAvailabilityProof):
        raise ValueError("Poke Pad plan requires a deck availability proof")
    if (
        not isinstance(proof_digest, str)
        or len(proof_digest) != 64
        or any(character not in "0123456789abcdef" for character in proof_digest)
    ):
        raise ValueError("Poke Pad plan requires a lowercase proof SHA-256")
    classes = tuple(tuple(card_ids) for card_ids in ordered_card_id_classes)
    policy = DeferredCardClassChoice(
        ordered_card_id_classes=classes,
        owner=state.seat,
        allowed_source_zones=(int(AreaType.DECK),),
        option_type=int(OptionType.CARD),
        selection_count=1,
        require_match=True,
        availability_proof=availability_proof,
    )
    transaction_payload = {
        "profile": "R_SEARCH_POKE_PAD_CORE_FORMATION_V1",
        "state": public_state_fingerprint(state),
        "source_ref": source_ref.sort_key(),
        "action": action_spec.canonical(),
        "classes": classes,
        "availability": availability_proof.canonical(),
        "proof_digest": proof_digest,
    }
    transaction_hash = hashlib.sha256(
        json.dumps(
            transaction_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return TransactionPlan(
        transaction_id="POKE_PAD_CORE_{0}".format(transaction_hash[:24]),
        owner_kind=OwnerKind.SEARCH_RESOLUTION,
        game_epoch=state.game_epoch,
        seat=state.seat,
        turn=state.turn,
        start_action_count=state.turn_action_count,
        source_ref=source_ref,
        target_refs=(),
        reserved_refs=(),
        terminal_receipt=TerminalReceiptSpec(
            profile=TerminalReceiptProfile.POKE_PAD_SEARCH,
            source_ref=source_ref,
            target_refs=(),
            reserved_refs=(),
            expected_play_card_id=1152,
            start_deck_count=state.own.deck_count,
        ),
        initiation=TransactionStep(
            stage=TransactionStage.INITIATION,
            expected_select_type=int(SelectType.MAIN),
            expected_context=int(SelectContext.MAIN),
            expected_min_count=1,
            expected_max_count=1,
            action_spec=action_spec,
            irreversible_on_emit=True,
            expected_effect_ref=None,
            expected_context_ref=None,
            effect_or_attack_id=1152,
        ),
        steps=(
            TransactionStep(
                stage=TransactionStage.SELECT_SEARCH_TARGET,
                expected_select_type=int(SelectType.CARD),
                expected_context=int(SelectContext.TO_HAND),
                expected_min_count=0,
                expected_max_count=1,
                action_spec=None,
                irreversible_on_emit=False,
                expected_effect_ref=source_ref,
                expected_context_ref=None,
                effect_or_attack_id=1152,
                deferred_card_choice=policy,
            ),
        ),
    )


def _card_spec_for_ref(ref_value: PhysicalRef) -> ActionSpec:
    _require_exact_ref(ref_value)
    return ActionSpec.single(
        SemanticOptionKey(
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
    )


def _require_proof_digest(proof_digest: str) -> None:
    if (
        not isinstance(proof_digest, str)
        or len(proof_digest) != 64
        or any(character not in "0123456789abcdef" for character in proof_digest)
    ):
        raise ValueError("transaction plan requires a lowercase proof SHA-256")


def build_deck_search_plan(
    state: PublicState,
    source_ref: PhysicalRef,
    action_spec: ActionSpec,
    ordered_card_id_classes: Sequence[Sequence[int]],
    availability_proof: DeckAvailabilityProof,
    proof_digest: str,
) -> TransactionPlan:
    """Build a guaranteed Fighting Gong search using physical source identity."""

    if not isinstance(state, PublicState) or not _stable_main(state):
        raise ValueError("deck search plan requires stable MAIN")
    _require_exact_ref(source_ref)
    if (
        source_ref.card_id != 1142
        or source_ref.owner != state.seat
        or source_ref.zone != int(AreaType.HAND)
        or source_ref not in state.own.hand_refs
    ):
        raise ValueError("Fighting Gong source must be one exact own HAND card")
    if not isinstance(action_spec, ActionSpec) or len(action_spec.choices) != 1:
        raise ValueError("deck search plan requires one initiation action")
    _validate_persisted_action_spec(action_spec)
    key = action_spec.choices[0]
    if (
        key.option_type != int(OptionType.PLAY)
        or key.player_index != state.seat
        or key.card_id != source_ref.card_id
        or key.card_serial != source_ref.serial
        or key.source_zone != source_ref.zone
    ):
        raise ValueError("Fighting Gong initiation must bind its physical source")
    if not isinstance(availability_proof, DeckAvailabilityProof):
        raise ValueError("deck search plan requires an availability proof")
    _require_proof_digest(proof_digest)
    classes = tuple(tuple(card_ids) for card_ids in ordered_card_id_classes)
    policy = DeferredCardClassChoice(
        ordered_card_id_classes=classes,
        owner=state.seat,
        allowed_source_zones=(int(AreaType.DECK),),
        option_type=int(OptionType.CARD),
        selection_count=1,
        require_match=True,
        availability_proof=availability_proof,
    )
    payload = (
        "FIGHTING_GONG_ROUTE_V1",
        public_state_fingerprint(state),
        source_ref.sort_key(),
        action_spec.canonical(),
        classes,
        availability_proof.canonical(),
        proof_digest,
    )
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return TransactionPlan(
        transaction_id="FIGHTING_GONG_{0}".format(digest[:24]),
        owner_kind=OwnerKind.SEARCH_RESOLUTION,
        game_epoch=state.game_epoch,
        seat=state.seat,
        turn=state.turn,
        start_action_count=state.turn_action_count,
        source_ref=source_ref,
        target_refs=(),
        reserved_refs=(),
        terminal_receipt=TerminalReceiptSpec(
            profile=TerminalReceiptProfile.FIGHTING_GONG_SEARCH,
            source_ref=source_ref,
            target_refs=(),
            reserved_refs=(),
            expected_play_card_id=1142,
            start_deck_count=state.own.deck_count,
        ),
        initiation=TransactionStep(
            stage=TransactionStage.INITIATION,
            expected_select_type=int(SelectType.MAIN),
            expected_context=int(SelectContext.MAIN),
            expected_min_count=1,
            expected_max_count=1,
            action_spec=action_spec,
            irreversible_on_emit=True,
            effect_or_attack_id=1142,
        ),
        steps=(
            TransactionStep(
                stage=TransactionStage.SELECT_SEARCH_TARGET,
                expected_select_type=int(SelectType.CARD),
                expected_context=int(SelectContext.TO_HAND),
                expected_min_count=0,
                expected_max_count=1,
                action_spec=None,
                irreversible_on_emit=False,
                expected_effect_ref=source_ref,
                effect_or_attack_id=1142,
                deferred_card_choice=policy,
            ),
        ),
    )


def build_lunar_cycle_plan(
    state: PublicState,
    source_ref: PhysicalRef,
    energy_ref: PhysicalRef,
    action_spec: ActionSpec,
    proof_digest: str,
) -> TransactionPlan:
    """Build Lunar Cycle through the exact discard and stochastic boundary."""

    if not isinstance(state, PublicState) or not _stable_main(state):
        raise ValueError("Lunar Cycle plan requires stable MAIN")
    _require_exact_ref(source_ref)
    _require_exact_ref(energy_ref)
    _require_proof_digest(proof_digest)
    own_board_refs = tuple(
        pokemon.ref for pokemon in state.own.active + state.own.bench
    )
    if source_ref.card_id != 675 or source_ref not in own_board_refs:
        raise ValueError("Lunar Cycle source must be an in-play Lunatone")
    if (
        energy_ref.card_id != 6
        or energy_ref.owner != state.seat
        or energy_ref.zone != int(AreaType.HAND)
        or energy_ref not in state.own.hand_refs
    ):
        raise ValueError("Lunar Cycle cost must be an exact Fighting Energy in HAND")
    _validate_persisted_action_spec(action_spec)
    key = action_spec.choices[0]
    if key.option_type not in (int(OptionType.ABILITY), int(OptionType.SKILL)):
        raise ValueError("Lunar Cycle initiation must be ABILITY or SKILL")
    payload = (
        "LUNAR_CYCLE_SAFE_PREFIX_V1",
        public_state_fingerprint(state),
        source_ref.sort_key(),
        energy_ref.sort_key(),
        action_spec.canonical(),
        proof_digest,
    )
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return TransactionPlan(
        transaction_id="LUNAR_CYCLE_{0}".format(digest[:24]),
        owner_kind=OwnerKind.LUNAR_CYCLE_RESOLUTION,
        game_epoch=state.game_epoch,
        seat=state.seat,
        turn=state.turn,
        start_action_count=state.turn_action_count,
        source_ref=source_ref,
        target_refs=(),
        reserved_refs=(energy_ref,),
        terminal_receipt=TerminalReceiptSpec(
            profile=TerminalReceiptProfile.LUNAR_CYCLE,
            source_ref=source_ref,
            target_refs=(),
            reserved_refs=(energy_ref,),
            expected_draw_count=3,
            start_deck_count=state.own.deck_count,
            original_energy_refs=(energy_ref,),
        ),
        initiation=TransactionStep(
            stage=TransactionStage.INITIATION,
            expected_select_type=int(SelectType.MAIN),
            expected_context=int(SelectContext.MAIN),
            expected_min_count=1,
            expected_max_count=1,
            action_spec=action_spec,
            irreversible_on_emit=True,
            effect_or_attack_id=675,
        ),
        steps=(
            TransactionStep(
                stage=TransactionStage.SELECT_COST,
                expected_select_type=int(SelectType.CARD),
                expected_context=int(SelectContext.DISCARD),
                expected_min_count=1,
                expected_max_count=1,
                action_spec=_card_spec_for_ref(energy_ref),
                irreversible_on_emit=True,
                expected_effect_ref=source_ref,
                effect_or_attack_id=675,
                stochastic_boundary=True,
            ),
        ),
    )


def build_aura_jab_plan(
    state: PublicState,
    action_spec: ActionSpec,
    energy_refs: Sequence[PhysicalRef],
    target_ref: PhysicalRef,
    proof_digest: str,
) -> TransactionPlan:
    """Attach exact discard Energy refs to one Bench target after Aura Jab."""

    if not isinstance(state, PublicState) or not _stable_main(state):
        raise ValueError("Aura Jab plan requires stable MAIN")
    active = state.own_active
    if active is None or active.ref.card_id != 678:
        raise ValueError("Aura Jab source must be the Active Mega Lucario ex")
    _require_exact_ref(target_ref)
    _require_proof_digest(proof_digest)
    bench_refs = tuple(pokemon.ref for pokemon in state.own.bench)
    if target_ref not in bench_refs:
        raise ValueError("Aura Jab target must be one exact own Bench Pokemon")
    energies = _normalize_refs(energy_refs)
    all_discard_energy = tuple(
        ref_value for ref_value in state.own.discard_refs if ref_value.card_id == 6
    )
    if not 1 <= len(energies) <= min(3, len(all_discard_energy)):
        raise ValueError("Aura Jab must attach one to three available Energy cards")
    if any(
        ref_value.card_id != 6
        or ref_value.owner != state.seat
        or ref_value.zone != int(AreaType.DISCARD)
        or ref_value not in all_discard_energy
        for ref_value in energies
    ):
        raise ValueError("Aura Jab Energy refs must be exact discard Fighting Energy")
    _validate_persisted_action_spec(action_spec)
    key = action_spec.choices[0]
    if key.option_type != int(OptionType.ATTACK) or key.attack_id != 982:
        raise ValueError("Aura Jab plan initiation must be attack 982")
    payload = (
        "AURA_JAB_CONCENTRATION_V1",
        public_state_fingerprint(state),
        active.ref.sort_key(),
        tuple(ref_value.sort_key() for ref_value in energies),
        target_ref.sort_key(),
        action_spec.canonical(),
        proof_digest,
    )
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    target_step = TransactionStep(
        stage=TransactionStage.SELECT_EFFECT_TARGET,
        expected_select_type=int(SelectType.CARD),
        expected_context=int(SelectContext.ATTACH_FROM),
        expected_min_count=1,
        expected_max_count=1,
        action_spec=_card_spec_for_ref(target_ref),
        irreversible_on_emit=True,
        expected_effect_ref=active.ref,
        effect_or_attack_id=982,
    )
    return TransactionPlan(
        transaction_id="AURA_JAB_{0}".format(digest[:24]),
        owner_kind=OwnerKind.AURA_JAB_ATTACH,
        game_epoch=state.game_epoch,
        seat=state.seat,
        turn=state.turn,
        start_action_count=state.turn_action_count,
        source_ref=active.ref,
        target_refs=(target_ref,),
        reserved_refs=energies,
        terminal_receipt=TerminalReceiptSpec(
            profile=TerminalReceiptProfile.AURA_JAB,
            source_ref=active.ref,
            target_refs=(target_ref,),
            reserved_refs=energies,
            expected_attack_id=982,
            allow_turn_transition=True,
        ),
        initiation=TransactionStep(
            stage=TransactionStage.INITIATION,
            expected_select_type=int(SelectType.MAIN),
            expected_context=int(SelectContext.MAIN),
            expected_min_count=1,
            expected_max_count=1,
            action_spec=action_spec,
            irreversible_on_emit=True,
            effect_or_attack_id=982,
        ),
        steps=(
            TransactionStep(
                stage=TransactionStage.SELECT_ENERGY,
                expected_select_type=int(SelectType.CARD),
                expected_context=int(SelectContext.ATTACH_TO),
                expected_min_count=0,
                expected_max_count=min(3, len(all_discard_energy)),
                action_spec=ActionSpec(
                    tuple(
                        _card_spec_for_ref(ref_value).choices[0]
                        for ref_value in energies
                    )
                ),
                irreversible_on_emit=True,
                expected_effect_ref=active.ref,
                effect_or_attack_id=982,
            ),
        )
        + tuple(target_step for _ in energies),
    )


def build_ultra_ball_plan(
    state: PublicState,
    source_ref: PhysicalRef,
    discard_refs: Sequence[PhysicalRef],
    action_spec: ActionSpec,
    ordered_card_id_classes: Sequence[Sequence[int]],
    availability_proof: DeckAvailabilityProof,
    proof_digest: str,
) -> TransactionPlan:
    """Discard two safe exact cards, then take one guaranteed Pokemon."""

    if not isinstance(state, PublicState) or not _stable_main(state):
        raise ValueError("Ultra Ball plan requires stable MAIN")
    _require_exact_ref(source_ref)
    if (
        source_ref.card_id != 1121
        or source_ref.owner != state.seat
        or source_ref.zone != int(AreaType.HAND)
        or source_ref not in state.own.hand_refs
    ):
        raise ValueError("Ultra Ball source must be one exact own HAND card")
    discards = _normalize_refs(discard_refs)
    if len(discards) != 2 or source_ref in discards:
        raise ValueError("Ultra Ball requires two distinct non-source discards")
    if any(
        ref_value.owner != state.seat
        or ref_value.zone != int(AreaType.HAND)
        or ref_value not in state.own.hand_refs
        for ref_value in discards
    ):
        raise ValueError("Ultra Ball discard refs must be exact own HAND cards")
    _validate_persisted_action_spec(action_spec)
    key = action_spec.choices[0]
    if (
        key.option_type != int(OptionType.PLAY)
        or key.card_id != source_ref.card_id
        or key.card_serial != source_ref.serial
        or key.source_zone != source_ref.zone
    ):
        raise ValueError("Ultra Ball initiation must bind its physical source")
    if not isinstance(availability_proof, DeckAvailabilityProof):
        raise ValueError("Ultra Ball requires a deck availability proof")
    _require_proof_digest(proof_digest)
    classes = tuple(tuple(card_ids) for card_ids in ordered_card_id_classes)
    policy = DeferredCardClassChoice(
        ordered_card_id_classes=classes,
        owner=state.seat,
        allowed_source_zones=(int(AreaType.DECK),),
        option_type=int(OptionType.CARD),
        selection_count=1,
        require_match=True,
        availability_proof=availability_proof,
    )
    payload = (
        "ULTRA_BALL_SAFE_ROUTE_V1",
        public_state_fingerprint(state),
        source_ref.sort_key(),
        tuple(ref_value.sort_key() for ref_value in discards),
        action_spec.canonical(),
        classes,
        availability_proof.canonical(),
        proof_digest,
    )
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return TransactionPlan(
        transaction_id="ULTRA_BALL_{0}".format(digest[:24]),
        owner_kind=OwnerKind.ULTRA_BALL_ROUTE,
        game_epoch=state.game_epoch,
        seat=state.seat,
        turn=state.turn,
        start_action_count=state.turn_action_count,
        source_ref=source_ref,
        target_refs=(),
        reserved_refs=discards,
        terminal_receipt=TerminalReceiptSpec(
            profile=TerminalReceiptProfile.ULTRA_BALL,
            source_ref=source_ref,
            target_refs=(),
            reserved_refs=discards,
            expected_play_card_id=1121,
            start_deck_count=state.own.deck_count,
        ),
        initiation=TransactionStep(
            stage=TransactionStage.INITIATION,
            expected_select_type=int(SelectType.MAIN),
            expected_context=int(SelectContext.MAIN),
            expected_min_count=1,
            expected_max_count=1,
            action_spec=action_spec,
            irreversible_on_emit=True,
            effect_or_attack_id=1121,
        ),
        steps=(
            TransactionStep(
                stage=TransactionStage.SELECT_COST,
                expected_select_type=int(SelectType.CARD),
                expected_context=int(SelectContext.DISCARD),
                expected_min_count=2,
                expected_max_count=2,
                action_spec=ActionSpec(
                    tuple(
                        _card_spec_for_ref(ref_value).choices[0]
                        for ref_value in discards
                    )
                ),
                irreversible_on_emit=True,
                expected_effect_ref=source_ref,
                effect_or_attack_id=1121,
            ),
            TransactionStep(
                stage=TransactionStage.SELECT_SEARCH_TARGET,
                expected_select_type=int(SelectType.CARD),
                expected_context=int(SelectContext.TO_HAND),
                expected_min_count=0,
                expected_max_count=1,
                action_spec=None,
                irreversible_on_emit=False,
                expected_effect_ref=source_ref,
                effect_or_attack_id=1121,
                deferred_card_choice=policy,
            ),
        ),
    )


def build_boss_gust_plan(
    state: PublicState,
    source_ref: PhysicalRef,
    target_ref: PhysicalRef,
    action_spec: ActionSpec,
    proof_digest: str,
) -> TransactionPlan:
    """Select one exact opposing Bench target after Boss's Orders."""

    if not isinstance(state, PublicState) or not _stable_main(state):
        raise ValueError("Boss gust plan requires stable MAIN")
    _require_exact_ref(source_ref)
    _require_exact_ref(target_ref)
    _require_proof_digest(proof_digest)
    if (
        source_ref.card_id != 1182
        or source_ref not in state.own.hand_refs
        or target_ref not in tuple(pokemon.ref for pokemon in state.opponent.bench)
    ):
        raise ValueError("Boss gust refs must identify its source and opposing Bench")
    _validate_persisted_action_spec(action_spec)
    if (
        action_spec.choices[0].option_type != int(OptionType.PLAY)
        or action_spec.choices[0].card_id != 1182
    ):
        raise ValueError("Boss gust initiation must be Boss's Orders")
    payload = (
        "BOSS_GUST_EXACT_KO_V1",
        public_state_fingerprint(state),
        source_ref.sort_key(),
        target_ref.sort_key(),
        action_spec.canonical(),
        proof_digest,
    )
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return TransactionPlan(
        transaction_id="BOSS_GUST_{0}".format(digest[:24]),
        owner_kind=OwnerKind.BOSS_GUST,
        game_epoch=state.game_epoch,
        seat=state.seat,
        turn=state.turn,
        start_action_count=state.turn_action_count,
        source_ref=source_ref,
        target_refs=(target_ref,),
        reserved_refs=(),
        terminal_receipt=TerminalReceiptSpec(
            profile=TerminalReceiptProfile.BOSS_GUST,
            source_ref=source_ref,
            target_refs=(target_ref,),
            reserved_refs=(),
            expected_play_card_id=1182,
        ),
        initiation=TransactionStep(
            stage=TransactionStage.INITIATION,
            expected_select_type=int(SelectType.MAIN),
            expected_context=int(SelectContext.MAIN),
            expected_min_count=1,
            expected_max_count=1,
            action_spec=action_spec,
            irreversible_on_emit=True,
            effect_or_attack_id=1182,
        ),
        steps=(
            TransactionStep(
                stage=TransactionStage.SELECT_GUST_TARGET,
                expected_select_type=int(SelectType.CARD),
                expected_context=int(SelectContext.SWITCH),
                expected_min_count=1,
                expected_max_count=1,
                action_spec=_card_spec_for_ref(target_ref),
                irreversible_on_emit=True,
                expected_effect_ref=source_ref,
                effect_or_attack_id=1182,
            ),
        ),
    )


def build_hariyama_gust_plan(
    state: PublicState,
    source_ref: PhysicalRef,
    target_ref: PhysicalRef,
    action_spec: ActionSpec,
    proof_digest: str,
) -> TransactionPlan:
    """Accept Heave-Ho Catcher and gust one exact opposing Bench target."""

    if not isinstance(state, PublicState) or not _stable_main(state):
        raise ValueError("Hariyama gust plan requires stable MAIN")
    _require_exact_ref(source_ref)
    _require_exact_ref(target_ref)
    _require_proof_digest(proof_digest)
    if (
        source_ref.card_id != 674
        or source_ref not in state.own.hand_refs
        or target_ref not in tuple(pokemon.ref for pokemon in state.opponent.bench)
    ):
        raise ValueError("Hariyama gust refs must identify its source and target")
    _validate_persisted_action_spec(action_spec)
    key = action_spec.choices[0]
    if key.option_type != int(OptionType.EVOLVE) or key.card_id != 674:
        raise ValueError("Hariyama gust initiation must be an evolution")
    yes_spec = ActionSpec.single(
        SemanticOptionKey(
            option_type=int(OptionType.YES),
            player_index=state.seat,
        )
    )
    payload = (
        "HARIYAMA_HEAVE_HO_EXACT_KO_V1",
        public_state_fingerprint(state),
        source_ref.sort_key(),
        target_ref.sort_key(),
        action_spec.canonical(),
        proof_digest,
    )
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return TransactionPlan(
        transaction_id="HARIYAMA_GUST_{0}".format(digest[:24]),
        owner_kind=OwnerKind.HARIYAMA_GUST,
        game_epoch=state.game_epoch,
        seat=state.seat,
        turn=state.turn,
        start_action_count=state.turn_action_count,
        source_ref=source_ref,
        target_refs=(target_ref,),
        reserved_refs=(),
        terminal_receipt=TerminalReceiptSpec(
            profile=TerminalReceiptProfile.HARIYAMA_GUST,
            source_ref=source_ref,
            target_refs=(target_ref,),
            reserved_refs=(),
            expected_evolve_card_id=674,
            evolve_target_lineage_serial=key.target_lineage_serial,
        ),
        initiation=TransactionStep(
            stage=TransactionStage.INITIATION,
            expected_select_type=int(SelectType.MAIN),
            expected_context=int(SelectContext.MAIN),
            expected_min_count=1,
            expected_max_count=1,
            action_spec=action_spec,
            irreversible_on_emit=True,
            effect_or_attack_id=674,
        ),
        steps=(
            TransactionStep(
                stage=TransactionStage.SELECT_EFFECT_TARGET,
                expected_select_type=int(SelectType.YES_NO),
                expected_context=int(SelectContext.ACTIVATE),
                expected_min_count=1,
                expected_max_count=1,
                action_spec=yes_spec,
                irreversible_on_emit=True,
                expected_context_ref=source_ref,
                effect_or_attack_id=674,
            ),
            TransactionStep(
                stage=TransactionStage.SELECT_GUST_TARGET,
                expected_select_type=int(SelectType.CARD),
                expected_context=int(SelectContext.SWITCH),
                expected_min_count=1,
                expected_max_count=1,
                action_spec=_card_spec_for_ref(target_ref),
                irreversible_on_emit=True,
                expected_effect_ref=source_ref,
                effect_or_attack_id=674,
            ),
        ),
    )


def build_wally_plan(
    state: PublicState,
    source_ref: PhysicalRef,
    target_ref: PhysicalRef,
    reattach_ref: PhysicalRef,
    action_spec: ActionSpec,
    proof_digest: str,
) -> TransactionPlan:
    """Heal one exact evolved target, reattach one returned Energy, then replan."""

    if not isinstance(state, PublicState) or not _stable_main(state):
        raise ValueError("Wally plan requires stable MAIN")
    _require_exact_ref(source_ref)
    _require_exact_ref(target_ref)
    _require_exact_ref(reattach_ref)
    _require_proof_digest(proof_digest)
    target = next(
        (
            pokemon
            for pokemon in state.own.active + state.own.bench
            if pokemon.ref == target_ref
        ),
        None,
    )
    if (
        source_ref.card_id != 1229
        or source_ref not in state.own.hand_refs
        or target is None
        or target_ref.card_id not in (674, 678)
    ):
        raise ValueError("Wally refs must identify its source and evolved target")
    if (
        reattach_ref.card_id != 6
        or target is None
        or reattach_ref not in target.energy_refs
    ):
        raise ValueError("Wally reattach must be one exact attached Fighting Energy")
    reattach_spec = ActionSpec.single(
        SemanticOptionKey(
            option_type=int(OptionType.ATTACH),
            player_index=state.seat,
            card_id=reattach_ref.card_id,
            card_serial=reattach_ref.serial,
            source_zone=int(AreaType.HAND),
            target_zone=target_ref.zone,
            target_lineage_serial=target_ref.lineage_serial,
        )
    )
    _validate_persisted_action_spec(action_spec)
    if (
        action_spec.choices[0].option_type != int(OptionType.PLAY)
        or action_spec.choices[0].card_id != 1229
    ):
        raise ValueError("Wally initiation must bind Wally's Compassion")
    payload = (
        "WALLY_REBOOT_NARROW_V1",
        public_state_fingerprint(state),
        source_ref.sort_key(),
        reattach_ref.sort_key(),
        target_ref.sort_key(),
        action_spec.canonical(),
        proof_digest,
    )
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return TransactionPlan(
        transaction_id="WALLY_{0}".format(digest[:24]),
        owner_kind=OwnerKind.WALLY_REBOOT,
        game_epoch=state.game_epoch,
        seat=state.seat,
        turn=state.turn,
        start_action_count=state.turn_action_count,
        source_ref=source_ref,
        target_refs=(target_ref,),
        reserved_refs=(reattach_ref,),
        terminal_receipt=TerminalReceiptSpec(
            profile=TerminalReceiptProfile.WALLY_REBOOT,
            source_ref=source_ref,
            target_refs=(target_ref,),
            reserved_refs=(reattach_ref,),
            expected_play_card_id=1229,
            start_target_hp=target.hp,
            start_target_max_hp=target.max_hp,
            original_energy_refs=target.energy_refs,
        ),
        initiation=TransactionStep(
            stage=TransactionStage.INITIATION,
            expected_select_type=int(SelectType.MAIN),
            expected_context=int(SelectContext.MAIN),
            expected_min_count=1,
            expected_max_count=1,
            action_spec=action_spec,
            irreversible_on_emit=True,
            effect_or_attack_id=1229,
        ),
        steps=(
            TransactionStep(
                stage=TransactionStage.SELECT_EFFECT_TARGET,
                expected_select_type=int(SelectType.CARD),
                expected_context=int(SelectContext.HEAL),
                expected_min_count=1,
                expected_max_count=1,
                action_spec=_card_spec_for_ref(target_ref),
                irreversible_on_emit=True,
                expected_effect_ref=source_ref,
                effect_or_attack_id=1229,
            ),
            TransactionStep(
                stage=TransactionStage.SELECT_ENERGY,
                expected_select_type=int(SelectType.MAIN),
                expected_context=int(SelectContext.MAIN),
                expected_min_count=1,
                expected_max_count=1,
                action_spec=reattach_spec,
                irreversible_on_emit=True,
                effect_or_attack_id=1229,
            ),
        ),
    )


def build_switch_plan(
    state: PublicState,
    source_ref: PhysicalRef,
    target_ref: PhysicalRef,
    action_spec: ActionSpec,
    proof_digest: str,
) -> TransactionPlan:
    """Switch to one exact own Bench attacker."""

    if not isinstance(state, PublicState) or not _stable_main(state):
        raise ValueError("Switch plan requires stable MAIN")
    _require_exact_ref(source_ref)
    _require_exact_ref(target_ref)
    _require_proof_digest(proof_digest)
    if (
        source_ref.card_id != 1123
        or source_ref not in state.own.hand_refs
        or target_ref not in tuple(pokemon.ref for pokemon in state.own.bench)
    ):
        raise ValueError("Switch refs must identify its source and own Bench")
    _validate_persisted_action_spec(action_spec)
    if (
        action_spec.choices[0].option_type != int(OptionType.PLAY)
        or action_spec.choices[0].card_id != 1123
    ):
        raise ValueError("Switch initiation must bind the Switch item")
    payload = (
        "SWITCH_READY_ATTACKER_V1",
        public_state_fingerprint(state),
        source_ref.sort_key(),
        target_ref.sort_key(),
        action_spec.canonical(),
        proof_digest,
    )
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return TransactionPlan(
        transaction_id="SWITCH_{0}".format(digest[:24]),
        owner_kind=OwnerKind.SWITCH_RESOLUTION,
        game_epoch=state.game_epoch,
        seat=state.seat,
        turn=state.turn,
        start_action_count=state.turn_action_count,
        source_ref=source_ref,
        target_refs=(target_ref,),
        reserved_refs=(),
        terminal_receipt=TerminalReceiptSpec(
            profile=TerminalReceiptProfile.SWITCH,
            source_ref=source_ref,
            target_refs=(target_ref,),
            reserved_refs=(),
            expected_play_card_id=1123,
        ),
        initiation=TransactionStep(
            stage=TransactionStage.INITIATION,
            expected_select_type=int(SelectType.MAIN),
            expected_context=int(SelectContext.MAIN),
            expected_min_count=1,
            expected_max_count=1,
            action_spec=action_spec,
            irreversible_on_emit=True,
            effect_or_attack_id=1123,
        ),
        steps=(
            TransactionStep(
                stage=TransactionStage.SELECT_SWITCH_TARGET,
                expected_select_type=int(SelectType.CARD),
                expected_context=int(SelectContext.SWITCH),
                expected_min_count=1,
                expected_max_count=1,
                action_spec=_card_spec_for_ref(target_ref),
                irreversible_on_emit=True,
                expected_effect_ref=source_ref,
                effect_or_attack_id=1123,
            ),
        ),
    )


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
    receipt_events: Tuple[PublicReceiptEvent, ...]
    fault_latched: bool
    fault_code: Optional[str]
    _issuer_token: object = dataclass_field(repr=False, compare=False)
    # V4 Aura state is transaction-local and intentionally lives on the
    # existing owner record.  It is not part of the immutable plan digest and
    # never becomes module-global state.
    _aura_v4_selected_energy_refs_ordered: Tuple[PhysicalRef, ...] = ()
    _aura_v4_selected_energy_count: int = 0
    _aura_v4_target_cursor: int = 0
    _aura_v4_pending_callback_ref: Optional[PhysicalRef] = None
    _aura_v4_consumed_energy_refs: Tuple[PhysicalRef, ...] = ()
    _aura_v4_target_action_receipt_count: int = 0
    _aura_v4_attach_receipt_count: int = 0
    _aura_v4_completed: bool = False
    _aura_v4_owner_released: bool = False
    # The turn-boundary repair keeps only the receipt-wait identity.  The
    # actual PublicReceiptEvent stream remains authoritative and is never
    # synthesized here.
    _pending_terminal_receipt: bool = False
    _pending_terminal_owner: Optional[int] = None
    _pending_terminal_transaction_id: Optional[str] = None
    _pending_terminal_plan_digest: Optional[str] = None
    _pending_terminal_expected_context_ref: Optional[PhysicalRef] = None
    _pending_terminal_turn: Optional[int] = None

    @property
    def aura_callback_refs(self) -> Tuple[PhysicalRef, ...]:
        """Compatibility view of the observed V4 callback queue."""

        return self._aura_v4_selected_energy_refs_ordered

    def __post_init__(self) -> None:
        if self._issuer_token is not _STATE_ISSUER_TOKEN:
            raise ValueError(
                "TransactionState values must be created by TransactionStore"
            )


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
    exact_indices = tuple(index for index in indices if _is_exact_int(index))
    reasons = []
    if len(exact_indices) != len(indices) or any(
        index < 0 or index >= len(legal_options) for index in exact_indices
    ):
        reasons.append("LEGAL_OPTION_INDEX_INVALID")
    if len(set(exact_indices)) != len(exact_indices):
        reasons.append("LEGAL_OPTION_INDEX_COLLISION")
    if set(exact_indices) != set(range(len(legal_options))):
        reasons.append("LEGAL_OPTION_INDEX_SET_INCOMPLETE")
    return tuple(reasons)


def _materialize_step_action(
    step: TransactionStep,
    legal_options: Sequence[SemanticOption],
) -> Tuple[Optional[ActionSpec], Tuple[str, ...]]:
    if step.action_spec is not None:
        return step.action_spec, ()
    policy = step.deferred_card_choice
    if policy is None:
        return None, ("TRANSACTION_STEP_ACTION_MISSING",)
    counts = Counter(option.key for option in legal_options)
    eligible = tuple(
        option
        for option in legal_options
        if option.key.option_type == policy.option_type
        and option.key.player_index == policy.owner
        and option.key.source_zone in policy.allowed_source_zones
        and _is_exact_int(option.key.card_id)
        and option.key.card_id > 0
        and _is_exact_int(option.key.card_serial)
        and option.key.card_serial >= 0
        and option.key.source_index is None
    )
    for card_class in policy.ordered_card_id_classes:
        card_order = {card_id: index for index, card_id in enumerate(card_class)}
        hits = tuple(
            sorted(
                (option for option in eligible if option.key.card_id in card_order),
                key=lambda option: (
                    card_order[option.key.card_id],
                    option.key.card_serial,
                    option.key.sort_key(),
                    option.index,
                ),
            )
        )
        if not hits:
            continue
        selected = hits[0]
        if counts[selected.key] != 1:
            return None, ("DEFERRED_DUPLICATE_SEMANTIC_CHOICE",)
        materialized = ActionSpec.single(selected.key)
        try:
            _validate_persisted_action_spec(materialized)
        except ValueError:
            return None, ("DEFERRED_PHYSICAL_IDENTITY_INVALID",)
        return materialized, ()
    if policy.require_match:
        return None, ("DEFERRED_CARD_CLASS_NOT_FOUND",)
    return ActionSpec.empty(), ()


def _prompt_match_reasons(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    step: TransactionStep,
    *,
    action_spec_override: Optional[ActionSpec] = None,
) -> Tuple[
    Tuple[str, ...],
    Optional[Tuple[int, ...]],
    Optional[ActionSpec],
]:
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
    if action_spec_override is not None:
        action_spec = action_spec_override
        materialization_reasons: Tuple[str, ...] = ()
    else:
        action_spec, materialization_reasons = _materialize_step_action(
            step,
            legal_options,
        )
    reasons.extend(materialization_reasons)
    bound = None
    if action_spec is not None:
        try:
            bound = tuple(
                action_spec.bind(
                    legal_options,
                    min_count=step.expected_min_count,
                    max_count=step.expected_max_count,
                )
            )
        except SemanticBindError:
            reasons.append("SEMANTIC_BIND_FAILURE")
    unique_reasons = tuple(sorted(set(reasons)))
    return (
        unique_reasons,
        None if unique_reasons else bound,
        None if unique_reasons else action_spec,
    )


def _same_identity(left: PhysicalRef, right: PhysicalRef) -> bool:
    return (
        left.owner == right.owner
        and left.card_id == right.card_id
        and left.serial == right.serial
    )


def _ref_is_in(ref_value: PhysicalRef, refs: Sequence[PhysicalRef]) -> bool:
    return any(_same_identity(ref_value, candidate) for candidate in refs)


def _player_pokemon(state: PublicState, owner: int):
    player = state.own if state.own.index == owner else state.opponent
    return player.active + player.bench


def _target_is_active(state: PublicState, ref_value: PhysicalRef) -> bool:
    player = state.own if state.own.index == ref_value.owner else state.opponent
    return any(_same_identity(ref_value, pokemon.ref) for pokemon in player.active)


def _event_matches_card(
    event: PublicReceiptEvent,
    log_type: LogType,
    owner: int,
    ref_value: PhysicalRef,
) -> bool:
    return (
        event.log_type == int(log_type)
        and event.player_index == owner
        and event.card_id == ref_value.card_id
        and event.serial == ref_value.serial
    )


def _has_play(
    events: Sequence[PublicReceiptEvent],
    owner: int,
    source_ref: PhysicalRef,
    card_id: int,
) -> bool:
    return source_ref.card_id == card_id and any(
        _event_matches_card(event, LogType.PLAY, owner, source_ref)
        for event in events
    )


def _has_move(
    events: Sequence[PublicReceiptEvent],
    owner: int,
    ref_value: PhysicalRef,
    from_area: AreaType,
    to_area: AreaType,
) -> bool:
    return any(
        _event_matches_card(event, LogType.MOVE_CARD, owner, ref_value)
        and event.from_area == int(from_area)
        and event.to_area == int(to_area)
        for event in events
    )


def _has_attach(
    events: Sequence[PublicReceiptEvent],
    owner: int,
    energy_ref: PhysicalRef,
    target_ref: PhysicalRef,
) -> bool:
    return any(
        _event_matches_card(event, LogType.ATTACH, owner, energy_ref)
        and event.serial_target == target_ref.serial
        for event in events
    )


def _aura_callback_ref_matches(
    expected: PhysicalRef,
    actual: PhysicalRef,
) -> bool:
    """Match an Aura callback ref without binding its transient zone."""

    if not _source_identity_matches(expected, actual):
        return False
    return (
        expected.lineage_serial is None
        or actual.lineage_serial == expected.lineage_serial
    )


def _aura_v4_identity(ref_value: PhysicalRef) -> Tuple[object, ...]:
    """Return the stable physical identity used by the V4 selected set."""

    return (
        ref_value.card_id,
        ref_value.serial,
        ref_value.owner,
        ref_value.lineage_serial,
    )


def _aura_v4_ref_from_key(key: SemanticOptionKey) -> Optional[PhysicalRef]:
    if (
        key.option_type != int(OptionType.CARD)
        or not _is_exact_int(key.card_id)
        or not _is_exact_int(key.card_serial)
        or not _is_exact_int(key.player_index)
        or not _is_exact_int(key.source_zone)
    ):
        return None
    return PhysicalRef(
        key.card_id,
        key.card_serial,
        key.player_index,
        key.source_zone,
        key.source_lineage_serial,
    )


def _aura_v4_is_multi(spec: Optional[TerminalReceiptSpec]) -> bool:
    return bool(
        spec is not None
        and spec.profile == TerminalReceiptProfile.AURA_JAB
        and len(spec.reserved_refs) >= 2
    )


def _aura_v4_validate_plan_shape(
    plan: TransactionPlan,
    spec: TerminalReceiptSpec,
) -> Tuple[str, ...]:
    count = len(spec.reserved_refs)
    reasons = []
    if count not in AURA_V4_SUPPORTED_ENERGY_COUNTS:
        reasons.append(AURA_V4_UNSUPPORTED_ENERGY_COUNT)
    if len(plan.steps) - 1 != count:
        reasons.append(AURA_V4_SELECTED_COUNT_PLAN_MISMATCH)
    if any(
        step.stage != TransactionStage.SELECT_EFFECT_TARGET
        for step in plan.steps[1:]
    ):
        reasons.append(AURA_V4_CALLBACK_TRANSACTION_MISMATCH)
    return tuple(reasons)


def _aura_v4_selected_refs_from_action(
    action_spec: Optional[ActionSpec],
) -> Tuple[Optional[PhysicalRef], ...]:
    if action_spec is None:
        return ()
    return tuple(_aura_v4_ref_from_key(key) for key in action_spec.choices)


def _aura_v4_validate_selected_set(
    plan: TransactionPlan,
    action_spec: Optional[ActionSpec],
) -> Tuple[Tuple[PhysicalRef, ...], Tuple[str, ...]]:
    """Validate the Energy selection without sorting its observed order."""

    spec = plan.terminal_receipt
    if spec is None or spec.profile != TerminalReceiptProfile.AURA_JAB:
        return (), ()
    reasons = list(_aura_v4_validate_plan_shape(plan, spec))
    if reasons:
        return (), tuple(reasons)
    refs = _aura_v4_selected_refs_from_action(action_spec)
    if any(ref_value is None for ref_value in refs):
        return (), (AURA_V4_SELECTED_SET_RESERVED_MISMATCH,)
    selected = tuple(ref_value for ref_value in refs if ref_value is not None)
    if len(selected) != len(set(_aura_v4_identity(ref_value) for ref_value in selected)):
        reasons.append(AURA_V4_DUPLICATE_SELECTED_REF)
    if len(selected) != len(spec.reserved_refs):
        reasons.append(AURA_V4_SELECTED_COUNT_PLAN_MISMATCH)

    def same_selection(left: PhysicalRef, right: PhysicalRef) -> bool:
        # Energy action keys intentionally omit lineage for discard cards.  A
        # callback ref, in contrast, may carry lineage; the stable card/serial/
        # owner identity and validated discard zone are the selected-set gate.
        return (
            left.card_id == right.card_id
            and left.serial == right.serial
            and left.owner == right.owner
            and left.zone == right.zone
        )

    if len(selected) != len(spec.reserved_refs) or any(
        not any(same_selection(value, reserved) for value in selected)
        for reserved in spec.reserved_refs
    ) or any(
        not any(same_selection(value, reserved_ref) for reserved_ref in spec.reserved_refs)
        for value in selected
    ):
        reasons.append(AURA_V4_SELECTED_SET_RESERVED_MISMATCH)
    return selected, tuple(sorted(set(reasons)))


def _aura_consumed_callback_refs(
    owner: TransactionState,
    spec: TerminalReceiptSpec,
) -> Tuple[PhysicalRef, ...]:
    """Return target callback refs in the exact order already accepted.

    V4 records every successfully issued target callback on the owner.  A few
    legacy receipt fixtures construct an owner at a later step directly; for
    those fixtures only, attach receipts provide a conservative fallback.
    The fallback is never used for the first target callback, where the engine
    may expose the current Energy attach receipt in the same prompt snapshot.
    """

    refs = []
    for actual in owner.aura_callback_refs:
        match = next(
            (
                ref_value
                for ref_value in spec.reserved_refs
                if _aura_callback_ref_matches(ref_value, actual)
            ),
            None,
        )
        if match is not None and not any(
            _aura_callback_ref_matches(match, prior) for prior in refs
        ):
            refs.append(match)
    if refs or owner.step_index < 1:
        return tuple(refs)
    # Compatibility path for existing terminal-receipt fixtures that mutate
    # step_index without replaying the prior callback through _issue_step.
    for ref_value in spec.reserved_refs:
        if _has_attach(
            owner.receipt_events,
            spec.source_ref.owner,
            ref_value,
            spec.target_refs[0],
        ):
            refs.append(ref_value)
    return tuple(refs)


def _has_unknown_receipt_field(
    events: Sequence[PublicReceiptEvent],
    log_types: Sequence[LogType],
    owner: int,
) -> bool:
    expected = frozenset(int(value) for value in log_types)
    return any(
        event.log_type in expected
        and event.player_index in (None, owner)
        and event.serial is None
        for event in events
    )


def _selected_deck_target(
    owner: TransactionState,
) -> Optional[PhysicalRef]:
    for action_spec in reversed(owner.semantic_action_specs):
        for key in action_spec.choices:
            if (
                key.option_type == int(OptionType.CARD)
                and key.source_zone == int(AreaType.DECK)
                and _is_exact_int(key.player_index)
                and _is_exact_int(key.card_id)
                and _is_exact_int(key.card_serial)
            ):
                return PhysicalRef(
                    key.card_id,
                    key.card_serial,
                    key.player_index,
                    int(AreaType.DECK),
                    key.card_serial,
                )
    return None


def _receipt_failure(
    events: Sequence[PublicReceiptEvent],
    log_types: Sequence[LogType],
    owner: int,
    reason: str,
) -> Tuple[TerminalReceiptStatus, Tuple[str, ...]]:
    status = (
        TerminalReceiptStatus.UNKNOWN
        if _has_unknown_receipt_field(events, log_types, owner)
        else TerminalReceiptStatus.INCOMPLETE
    )
    return status, (reason,)


def _wally_return_receipt(
    spec: TerminalReceiptSpec,
    state: PublicState,
    events: Sequence[PublicReceiptEvent],
    *,
    require_all_in_hand: bool = True,
) -> Tuple[TerminalReceiptStatus, Tuple[str, ...]]:
    target_ref = spec.target_refs[0]
    target = next(
        (
            pokemon
            for pokemon in _player_pokemon(state, target_ref.owner)
            if _same_identity(target_ref, pokemon.ref)
        ),
        None,
    )
    damage = (
        None
        if spec.start_target_hp is None or spec.start_target_max_hp is None
        else spec.start_target_max_hp - spec.start_target_hp
    )
    healed = damage is not None and damage > 0 and any(
        event.log_type == int(LogType.HP_CHANGE)
        and event.player_index == spec.source_ref.owner
        and event.serial == target_ref.serial
        and event.value == damage
        for event in events
    )
    returned = all(
        _has_move(
            events,
            spec.source_ref.owner,
            ref_value,
            AreaType.ENERGY,
            AreaType.HAND,
        )
        and (
            not require_all_in_hand
            or _ref_is_in(ref_value, state.own.hand_refs)
        )
        for ref_value in spec.original_energy_refs
    )
    target_healed = (
        target is not None
        and spec.start_target_max_hp is not None
        and target.hp == spec.start_target_max_hp
        and target.max_hp == spec.start_target_max_hp
    )
    if healed and returned and target_healed:
        return TerminalReceiptStatus.COMPLETE, ()
    return _receipt_failure(
        events,
        (LogType.HP_CHANGE, LogType.MOVE_CARD),
        spec.source_ref.owner,
        "WALLY_RETURN_RECEIPT_MISSING",
    )


def _terminal_receipt_status(
    plan: TransactionPlan,
    owner: TransactionState,
    state: PublicState,
) -> Tuple[TerminalReceiptStatus, Tuple[str, ...]]:
    spec = plan.terminal_receipt
    if spec is None:
        return TerminalReceiptStatus.INCOMPLETE, ("TERMINAL_RECEIPT_UNDECLARED",)
    events = owner.receipt_events
    seat = spec.source_ref.owner
    source_discarded = _ref_is_in(spec.source_ref, state.own.discard_refs)

    if spec.profile in (
        TerminalReceiptProfile.POKE_PAD_SEARCH,
        TerminalReceiptProfile.FIGHTING_GONG_SEARCH,
        TerminalReceiptProfile.ULTRA_BALL,
    ):
        target_ref = _selected_deck_target(owner)
        play_ok = _has_play(
            events,
            seat,
            spec.source_ref,
            int(spec.expected_play_card_id or 0),
        )
        target_ok = target_ref is not None and _has_move(
            events,
            seat,
            target_ref,
            AreaType.DECK,
            AreaType.HAND,
        )
        target_in_hand = target_ref is not None and _ref_is_in(
            target_ref, state.own.hand_refs
        )
        deck_ok = (
            spec.start_deck_count is not None
            and state.own.deck_count == spec.start_deck_count - 1
        )
        costs_ok = all(
            _ref_is_in(ref_value, state.own.discard_refs)
            for ref_value in spec.reserved_refs
        )
        if (
            play_ok
            and source_discarded
            and target_ok
            and target_in_hand
            and deck_ok
            and costs_ok
        ):
            return TerminalReceiptStatus.COMPLETE, ()
        return _receipt_failure(
            events,
            (LogType.PLAY, LogType.MOVE_CARD),
            seat,
            "SEARCH_TERMINAL_RECEIPT_MISSING",
        )

    if spec.profile == TerminalReceiptProfile.LUNAR_CYCLE:
        energy_ref = spec.reserved_refs[0]
        cost_ok = _has_move(
            events, seat, energy_ref, AreaType.HAND, AreaType.DISCARD
        ) and _ref_is_in(energy_ref, state.own.discard_refs)
        draw_serials = {
            event.serial
            for event in events
            if event.log_type == int(LogType.DRAW)
            and event.player_index == seat
            and event.card_id is not None
            and event.serial is not None
        }
        deck_ok = (
            spec.start_deck_count is not None
            and state.own.deck_count == spec.start_deck_count - spec.expected_draw_count
        )
        lineage_ok = any(
            pokemon.lineage_serial == spec.source_ref.lineage_serial
            for pokemon in _player_pokemon(state, seat)
        )
        if (
            cost_ok
            and len(draw_serials) == spec.expected_draw_count
            and deck_ok
            and lineage_ok
        ):
            return TerminalReceiptStatus.COMPLETE, ()
        return _receipt_failure(
            events,
            (LogType.MOVE_CARD, LogType.DRAW),
            seat,
            "LUNAR_CYCLE_TERMINAL_RECEIPT_MISSING",
        )

    if spec.profile == TerminalReceiptProfile.AURA_JAB:
        target_ref = spec.target_refs[0]
        attack_ok = any(
            _event_matches_card(event, LogType.ATTACK, seat, spec.source_ref)
            and event.attack_id == spec.expected_attack_id
            for event in events
        )
        if _aura_v4_is_multi(spec):
            selected_count = owner._aura_v4_selected_energy_count
            selected_refs = owner._aura_v4_selected_energy_refs_ordered
            selected_set = {
                _aura_v4_identity(ref_value)
                for ref_value in selected_refs
            }
            reserved_set = {
                _aura_v4_identity(ref_value)
                for ref_value in spec.reserved_refs
            }
            target = next(
                (
                    pokemon
                    for pokemon in _player_pokemon(state, target_ref.owner)
                    if _same_identity(target_ref, pokemon.ref)
                ),
                None,
            )
            board_ok = target is not None and all(
                _ref_is_in(ref_value, target.energy_refs)
                for ref_value in spec.reserved_refs
            )
            if (
                selected_count in AURA_V4_SUPPORTED_ENERGY_COUNTS
                and selected_count == len(spec.reserved_refs)
                and len(selected_refs) == selected_count
                and selected_set == reserved_set
                and owner._aura_v4_target_cursor == selected_count
                and len(owner._aura_v4_consumed_energy_refs) == selected_count
                and owner._aura_v4_target_action_receipt_count == selected_count
                and owner._aura_v4_attach_receipt_count == selected_count
                and owner._aura_v4_pending_callback_ref is None
                and not owner.fault_latched
                and attack_ok
                and board_ok
            ):
                return TerminalReceiptStatus.COMPLETE, ()
            if (
                selected_count in AURA_V4_SUPPORTED_ENERGY_COUNTS
                and owner._aura_v4_target_action_receipt_count
                > owner._aura_v4_attach_receipt_count
            ):
                return _receipt_failure(
                    events,
                    (LogType.ATTACK, LogType.ATTACH),
                    seat,
                    AURA_V4_ATTACH_RECEIPT_MISSING,
                )
            return _receipt_failure(
                events,
                (LogType.ATTACK, LogType.ATTACH),
                seat,
                AURA_V4_TARGET_RECEIPT_MISSING,
            )
        attaches_ok = all(
            _has_attach(events, seat, ref_value, target_ref)
            for ref_value in spec.reserved_refs
        )
        target = next(
            (
                pokemon
                for pokemon in _player_pokemon(state, target_ref.owner)
                if _same_identity(target_ref, pokemon.ref)
            ),
            None,
        )
        board_ok = target is not None and all(
            _ref_is_in(ref_value, target.energy_refs)
            for ref_value in spec.reserved_refs
        )
        if attack_ok and attaches_ok and board_ok:
            return TerminalReceiptStatus.COMPLETE, ()
        return _receipt_failure(
            events,
            (LogType.ATTACK, LogType.ATTACH),
            seat,
            "AURA_JAB_TERMINAL_RECEIPT_MISSING",
        )

    if spec.profile == TerminalReceiptProfile.BOSS_GUST:
        target_ref = spec.target_refs[0]
        switch_ok = any(
            event.log_type == int(LogType.SWITCH)
            and event.player_index == target_ref.owner
            and event.serial_bench == target_ref.serial
            for event in events
        )
        if (
            _has_play(events, seat, spec.source_ref, 1182)
            and source_discarded
            and switch_ok
            and _target_is_active(state, target_ref)
        ):
            return TerminalReceiptStatus.COMPLETE, ()
        return _receipt_failure(
            events,
            (LogType.PLAY, LogType.SWITCH),
            seat,
            "BOSS_GUST_TERMINAL_RECEIPT_MISSING",
        )

    if spec.profile == TerminalReceiptProfile.HARIYAMA_GUST:
        target_ref = spec.target_refs[0]
        evolve_ok = any(
            _event_matches_card(event, LogType.EVOLVE, seat, spec.source_ref)
            and event.serial_target == spec.evolve_target_lineage_serial
            for event in events
        )
        lineage_ok = any(
            pokemon.ref.card_id == 674
            and pokemon.lineage_serial == spec.evolve_target_lineage_serial
            for pokemon in _player_pokemon(state, seat)
        )
        switch_ok = any(
            event.log_type == int(LogType.SWITCH)
            and event.player_index == target_ref.owner
            and event.serial_bench == target_ref.serial
            for event in events
        )
        if evolve_ok and lineage_ok and switch_ok and _target_is_active(state, target_ref):
            return TerminalReceiptStatus.COMPLETE, ()
        return _receipt_failure(
            events,
            (LogType.EVOLVE, LogType.SWITCH),
            seat,
            "HARIYAMA_GUST_TERMINAL_RECEIPT_MISSING",
        )

    if spec.profile == TerminalReceiptProfile.WALLY_REBOOT:
        intermediate, _ = _wally_return_receipt(
            spec,
            state,
            events,
            require_all_in_hand=False,
        )
        target_ref = spec.target_refs[0]
        chosen_ref = spec.reserved_refs[0]
        target = next(
            (
                pokemon
                for pokemon in _player_pokemon(state, target_ref.owner)
                if _same_identity(target_ref, pokemon.ref)
            ),
            None,
        )
        attach_ok = _has_attach(events, seat, chosen_ref, target_ref)
        chosen_attached = target is not None and _ref_is_in(
            chosen_ref, target.energy_refs
        )
        others_in_hand = all(
            _ref_is_in(ref_value, state.own.hand_refs)
            for ref_value in spec.original_energy_refs
            if not _same_identity(ref_value, chosen_ref)
        )
        if (
            intermediate == TerminalReceiptStatus.COMPLETE
            and _has_play(events, seat, spec.source_ref, 1229)
            and source_discarded
            and attach_ok
            and chosen_attached
            and others_in_hand
        ):
            return TerminalReceiptStatus.COMPLETE, ()
        return _receipt_failure(
            events,
            (LogType.PLAY, LogType.HP_CHANGE, LogType.MOVE_CARD, LogType.ATTACH),
            seat,
            "WALLY_TERMINAL_RECEIPT_MISSING",
        )

    if spec.profile == TerminalReceiptProfile.SWITCH:
        target_ref = spec.target_refs[0]
        switch_ok = any(
            event.log_type == int(LogType.SWITCH)
            and event.player_index == seat
            and event.serial_bench == target_ref.serial
            for event in events
        )
        if (
            _has_play(events, seat, spec.source_ref, 1123)
            and source_discarded
            and switch_ok
            and _target_is_active(state, target_ref)
        ):
            return TerminalReceiptStatus.COMPLETE, ()
        return _receipt_failure(
            events,
            (LogType.PLAY, LogType.SWITCH),
            seat,
            "SWITCH_TERMINAL_RECEIPT_MISSING",
        )

    return TerminalReceiptStatus.UNKNOWN, ("TERMINAL_RECEIPT_PROFILE_UNKNOWN",)


def _aura_completion_reasons(spec: TerminalReceiptSpec) -> Tuple[str, ...]:
    if _aura_v4_is_multi(spec):
        return (
            AURA_V4_COMPLETE_AFTER_ALL_RECEIPTS_RULE,
            AURA_V4_RELEASE_OWNER_RULE,
        )
    return (AURA_CTXREF_COMPLETE_RULE, AURA_CTXREF_RELEASE_RULE)


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
        transaction_steps = (plan.initiation,) + plan.steps
        for step_index, step in enumerate(transaction_steps):
            policy = step.deferred_card_choice
            if policy is None:
                continue
            proof = policy.availability_proof
            if proof is None:
                if any(
                    prior_step.irreversible_on_emit
                    for prior_step in transaction_steps[:step_index]
                ):
                    reasons.append("DECK_AVAILABILITY_PROOF_REQUIRED")
                continue
            card_ids = tuple(
                sorted(
                    card_id
                    for card_class in policy.ordered_card_id_classes
                    for card_id in card_class
                )
            )
            if not proof.is_guaranteed or proof.rejection_reasons:
                reasons.append("DECK_AVAILABILITY_PROOF_NOT_GUARANTEED")
            if proof.owner != policy.owner or proof.owner != plan.seat:
                reasons.append("DECK_AVAILABILITY_OWNER_MISMATCH")
            if proof.card_ids != card_ids:
                reasons.append("DECK_AVAILABILITY_TARGET_CLASS_MISMATCH")
            if proof.required_count != policy.selection_count:
                reasons.append("DECK_AVAILABILITY_REQUIRED_COUNT_MISMATCH")
            if (
                proof.fixed_deck_size != FIXED_DECK_SIZE
                or proof.deck_counter_hash != FIXED_DECK_COUNTER_HASH
            ):
                reasons.append("DECK_AVAILABILITY_DECK_HASH_MISMATCH")
            if proof.own_deck_count != state.own.deck_count:
                reasons.append("DECK_AVAILABILITY_DECK_COUNT_MISMATCH")
            current_proof = prove_deck_availability_from_state(
                state,
                card_ids,
                required_count=policy.selection_count,
            )
            if not current_proof.is_guaranteed:
                reasons.append("DECK_AVAILABILITY_NOT_GUARANTEED")
            if current_proof.deck_state_hash != proof.deck_state_hash:
                reasons.append("DECK_AVAILABILITY_STATE_MISMATCH")
            if current_proof != proof:
                reasons.append("DECK_AVAILABILITY_PROOF_CONTENT_MISMATCH")
        if reasons:
            return StartResult(
                StartStatus.PLAN_STATE_MISMATCH,
                None,
                None,
                None,
                tuple(sorted(set(reasons))),
            )

        initiation_reasons, bound, initiation_action = _prompt_match_reasons(
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
            last_action_spec=initiation_action,
            semantic_action_specs=(initiation_action,),
            step_index=-1,
            callback_budget_used=1,
            committed=plan.initiation.irreversible_on_emit,
            receipt_events=(),
            fault_latched=False,
            fault_code=None,
            _issuer_token=_STATE_ISSUER_TOKEN,
            _aura_v4_selected_energy_refs_ordered=(),
            _aura_v4_selected_energy_count=0,
            _aura_v4_target_cursor=0,
            _aura_v4_pending_callback_ref=None,
            _aura_v4_consumed_energy_refs=(),
            _aura_v4_target_action_receipt_count=0,
            _aura_v4_attach_receipt_count=0,
            _aura_v4_completed=False,
            _aura_v4_owner_released=False,
        )
        self._plan = plan
        self._owner = owner
        return StartResult(
            StartStatus.STARTED,
            initiation_action,
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
            raise TransactionStoreError(
                "a committed transaction cannot be precommit-aborted"
            )
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

    def _aura_v4_reconcile_pending_receipt(
        self,
    ) -> Tuple[str, ...]:
        """Consume one target only after its target and ATTACH receipts exist."""

        if self._owner is None or self._plan is None:
            return ()
        spec = self._plan.terminal_receipt
        owner = self._owner
        if not _aura_v4_is_multi(spec):
            return ()
        if owner._aura_v4_completed:
            return (AURA_V4_EXTRA_CALLBACK_AFTER_COMPLETE,)
        pending = owner._aura_v4_pending_callback_ref
        if pending is None:
            return ()
        if owner._aura_v4_target_cursor >= owner._aura_v4_selected_energy_count:
            return (AURA_V4_EXTRA_CALLBACK_AFTER_COMPLETE,)
        target_ref = spec.target_refs[0]
        if not _has_attach(owner.receipt_events, owner.seat, pending, target_ref):
            return (
                AURA_V4_ATTACH_RECEIPT_MISSING,
                "AURA_PRECEDING_ATTACH_RECEIPT_MISSING",
                AURA_V4_ACCEPT_TARGET_RECEIPT_RULE,
            )
        if any(
            _aura_callback_ref_matches(pending, consumed)
            for consumed in owner._aura_v4_consumed_energy_refs
        ):
            return (
                AURA_V4_CALLBACK_REF_ALREADY_CONSUMED,
                AURA_V4_REJECT_CALLBACK_MISMATCH_RULE,
            )
        consumed = owner._aura_v4_consumed_energy_refs + (pending,)
        cursor = owner._aura_v4_target_cursor + 1
        target_receipts = owner._aura_v4_target_action_receipt_count + 1
        attach_receipts = owner._aura_v4_attach_receipt_count + 1
        self._owner = replace(
            owner,
            _aura_v4_consumed_energy_refs=consumed,
            _aura_v4_target_cursor=cursor,
            _aura_v4_pending_callback_ref=None,
            _aura_v4_target_action_receipt_count=target_receipts,
            _aura_v4_attach_receipt_count=attach_receipts,
        )
        return (
            AURA_V4_ACCEPT_TARGET_RECEIPT_RULE,
            AURA_V4_ADVANCE_TARGET_CURSOR_RULE,
        )

    def _aura_v4_backfill_legacy_owner_state(self) -> None:
        """Give pre-V4 terminal fixtures the same transaction-local fields.

        A few checked terminal-receipt tests construct an owner directly at a
        later step instead of replaying the preceding callbacks.  This
        compatibility boundary is deterministic and only runs when every V4
        field is still at its initial value; live callback order remains
        authoritative whenever the fields are populated normally.
        """

        if self._owner is None or self._plan is None:
            return
        spec = self._plan.terminal_receipt
        owner = self._owner
        if not _aura_v4_is_multi(spec) or owner._aura_v4_selected_energy_count:
            return
        count = len(spec.reserved_refs)
        issued_targets = max(0, owner.step_index)
        if issued_targets <= 0:
            return
        issued_targets = min(issued_targets, count)
        queue = tuple(spec.reserved_refs[:issued_targets])
        pending = queue[-1]
        cursor = max(0, issued_targets - 1)
        consumed = queue[:-1]
        self._owner = replace(
            owner,
            _aura_v4_selected_energy_refs_ordered=queue,
            _aura_v4_selected_energy_count=count,
            _aura_v4_target_cursor=cursor,
            _aura_v4_pending_callback_ref=pending,
            _aura_v4_consumed_energy_refs=consumed,
            _aura_v4_target_action_receipt_count=cursor,
            _aura_v4_attach_receipt_count=cursor,
        )

    def _pending_terminal_receipt_identity_reasons(
        self,
        spec: Optional[TerminalReceiptSpec],
    ) -> Tuple[str, ...]:
        """Validate the transaction-local pending Aura receipt identity.

        This check deliberately compares only the owner/transaction/plan and
        bound callback identity captured when the terminal callback was
        issued.  The current turn is not an identity field: the known fault is
        precisely that the callback is observed after a turn boundary.
        """

        if self._owner is None or self._plan is None:
            return ()
        owner = self._owner
        if not owner._pending_terminal_receipt:
            return ()
        if (
            spec is None
            or spec.profile != TerminalReceiptProfile.AURA_JAB
            or _aura_v4_is_multi(spec)
        ):
            return (
                AURA_TERMINAL_PENDING_RECEIPT_MISMATCH,
                AURA_TERMINAL_PENDING_RECEIPT_REJECT_RULE,
            )
        expected = owner.expected_context_ref
        pending_expected = owner._pending_terminal_expected_context_ref
        if (
            owner._pending_terminal_owner != owner.seat
            or owner._pending_terminal_transaction_id != owner.transaction_id
            or owner._pending_terminal_plan_digest != owner.plan_digest
            or owner._pending_terminal_turn != owner.turn
            or not isinstance(expected, PhysicalRef)
            or not isinstance(pending_expected, PhysicalRef)
            or not _aura_callback_ref_matches(pending_expected, expected)
        ):
            return (
                AURA_TERMINAL_PENDING_RECEIPT_MISMATCH,
                AURA_TERMINAL_PENDING_RECEIPT_REJECT_RULE,
            )
        return ()

    def _consume_pending_terminal_receipt(
        self,
        spec: Optional[TerminalReceiptSpec],
        completion_reasons: Sequence[str],
    ) -> Optional[ResumeResult]:
        """Consume a valid pending Aura receipt exactly once.

        Returning ``None`` means that no pending marker exists and the normal
        terminal-receipt path should continue.  A mismatch is fail-closed;
        it never falls through to a turn-based acceptance path.
        """

        if self._owner is None or not self._owner._pending_terminal_receipt:
            return None
        mismatch_reasons = self._pending_terminal_receipt_identity_reasons(spec)
        if mismatch_reasons:
            return self._failure_result(mismatch_reasons)
        owner = self._owner
        self._owner = replace(
            owner,
            _pending_terminal_receipt=False,
            _pending_terminal_owner=None,
            _pending_terminal_transaction_id=None,
            _pending_terminal_plan_digest=None,
            _pending_terminal_expected_context_ref=None,
            _pending_terminal_turn=None,
        )
        self._release_owner()
        return ResumeResult(
            ResumeStatus.COMPLETED,
            None,
            None,
            None,
            tuple(completion_reasons),
        )

    def _aura_target_step_override(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
        step_index: int,
    ) -> Tuple[Optional[TransactionStep], Tuple[str, ...]]:
        """Bind an Aura target callback to the exact Energy context ref.

        The immutable plan intentionally contains no callback-time context ref:
        the engine supplies that ref only after the preceding Energy action has
        been accepted.  The binding lives on the owner for this emission and is
        never written back into the plan digest.
        """

        if self._owner is None or self._plan is None:
            raise TransactionStoreError("cannot bind Aura target without an owner")
        spec = self._plan.terminal_receipt
        if (
            spec is None
            or spec.profile != TerminalReceiptProfile.AURA_JAB
            or step_index < 1
        ):
            return None, ()
        if not _aura_v4_is_multi(spec):
            # The one-Energy V2 contract remains intentionally unchanged.
            if step_index >= len(self._plan.steps) or step_index > len(spec.reserved_refs):
                return None, ("AURA_CTXREF_TRANSACTION_MISMATCH", AURA_CTXREF_BIND_RULE)
            consumed_refs = _aura_consumed_callback_refs(self._owner, spec)
            if len(consumed_refs) < step_index - 1:
                return None, ("AURA_PRECEDING_ATTACH_RECEIPT_MISSING", AURA_CTXREF_COMPLETE_RULE)
            if len(consumed_refs) > step_index - 1:
                return None, ("AURA_MULTI_CALLBACK_STATE_MISMATCH", AURA_CTXREF_COMPLETE_RULE)
            actual_ref = state.context_ref
            if not isinstance(actual_ref, PhysicalRef):
                return None, ("AURA_CTXREF_NEXT_REF_MISSING", AURA_CTXREF_CAPTURE_RULE)
            if actual_ref.owner != self._owner.seat:
                return None, ("AURA_CTXREF_OWNER_MISMATCH", AURA_CTXREF_OWNER_RULE)
            identity_matches = tuple(
                ref_value for ref_value in spec.reserved_refs
                if _aura_callback_ref_matches(ref_value, actual_ref)
            )
            if len(identity_matches) != 1:
                return None, (
                    "AURA_CTXREF_CONTEXT_MISMATCH"
                    if not identity_matches else "AURA_CTXREF_AMBIGUOUS_NEXT_PROMPT",
                    AURA_CTXREF_BIND_RULE,
                )
            expected_energy = identity_matches[0]
        else:
            shape_reasons = _aura_v4_validate_plan_shape(self._plan, spec)
            if shape_reasons:
                return None, shape_reasons
            owner = self._owner
            if owner._aura_v4_completed:
                return None, (
                    AURA_V4_EXTRA_CALLBACK_AFTER_COMPLETE,
                    AURA_V4_REJECT_CALLBACK_MISMATCH_RULE,
                )
            if owner._aura_v4_pending_callback_ref is not None:
                return None, (
                    AURA_V4_TARGET_RECEIPT_MISSING,
                    AURA_V4_REJECT_CALLBACK_MISMATCH_RULE,
                )
            if owner._aura_v4_target_cursor >= owner._aura_v4_selected_energy_count:
                return None, (
                    AURA_V4_EXTRA_CALLBACK_AFTER_COMPLETE,
                    AURA_V4_REJECT_CALLBACK_MISMATCH_RULE,
                )
            if state.select_type != int(SelectType.CARD):
                return None, (
                    AURA_V4_CALLBACK_PROMPT_TYPE_MISMATCH,
                    AURA_V4_REJECT_CALLBACK_MISMATCH_RULE,
                )
            if state.select_context is None or state.select_context == int(SelectContext.ATTACH_TO):
                return None, (
                    AURA_V4_TARGET_CONTEXT_MISMATCH,
                    AURA_V4_REJECT_CALLBACK_MISMATCH_RULE,
                )
            actual_ref = state.context_ref
            if not isinstance(actual_ref, PhysicalRef):
                return None, (
                    AURA_V4_CALLBACK_REF_MISSING,
                    AURA_V4_REJECT_CALLBACK_MISMATCH_RULE,
                )
            if actual_ref.owner != owner.seat:
                return None, (
                    AURA_V4_CALLBACK_OWNER_MISMATCH,
                    AURA_V4_TARGET_OWNER_MISMATCH,
                    AURA_V4_REJECT_CALLBACK_MISMATCH_RULE,
                )
            identity_matches = tuple(
                ref_value for ref_value in spec.reserved_refs
                if _aura_callback_ref_matches(ref_value, actual_ref)
            )
            if not identity_matches:
                return None, (
                    AURA_V4_CALLBACK_REF_NOT_SELECTED,
                    AURA_V4_TARGET_REF_MISMATCH,
                    AURA_V4_REJECT_CALLBACK_MISMATCH_RULE,
                )
            if len(identity_matches) != 1:
                return None, (
                    AURA_V4_CALLBACK_REF_NOT_SELECTED,
                    AURA_V4_REJECT_CALLBACK_MISMATCH_RULE,
                )
            expected_energy = identity_matches[0]
            if any(
                _aura_callback_ref_matches(expected_energy, consumed)
                for consumed in owner._aura_v4_consumed_energy_refs
            ):
                return None, (
                    AURA_V4_CALLBACK_REF_ALREADY_CONSUMED,
                    AURA_V4_REJECT_CALLBACK_MISMATCH_RULE,
                )
            queue = owner._aura_v4_selected_energy_refs_ordered
            cursor = owner._aura_v4_target_cursor
            if queue and cursor < len(queue):
                if not _aura_callback_ref_matches(queue[cursor], actual_ref):
                    return None, (
                        AURA_V4_CALLBACK_ORDER_MISMATCH,
                        AURA_V4_VALIDATE_CALLBACK_ORDER_RULE,
                        AURA_V4_REJECT_CALLBACK_MISMATCH_RULE,
                    )

        step = self._plan.steps[step_index]
        # A target action must resolve to exactly one legal semantic option.  A
        # duplicate option is not a reason to guess which target the engine
        # intended; preserve the existing fail-closed transaction path.
        target_key = None
        if step.action_spec is not None and len(step.action_spec.choices) == 1:
            target_key = step.action_spec.choices[0]
        if target_key is None:
            return None, ("AURA_CTXREF_TRANSACTION_MISMATCH", AURA_CTXREF_BIND_RULE)
        target_hits = sum(option.key == target_key for option in legal_options)
        if target_hits > 1:
            return None, (
                "AURA_CTXREF_AMBIGUOUS_NEXT_PROMPT",
                AURA_CTXREF_AMBIGUOUS_RULE,
            )
        if target_hits == 0:
            return None, ("AURA_CTXREF_CONTEXT_MISMATCH", AURA_CTXREF_BIND_RULE)

        # The engine's callback ref is authoritative for card/serial/owner,
        # but some live prompts intentionally omit its transient zone.  The
        # persisted TransactionStep still requires a concrete zone, while
        # `_source_identity_matches` deliberately treats zone as non-binding.
        # Normalize only this AURA binding to the reserved Energy's validated
        # discard zone; do not relax the general exact-ref contract.
        bound_ref = PhysicalRef(
            actual_ref.card_id,
            actual_ref.serial,
            actual_ref.owner,
            expected_energy.zone,
            (
                actual_ref.lineage_serial
                if actual_ref.lineage_serial is not None
                else expected_energy.lineage_serial
            ),
        )
        return replace(
            step,
            expected_context=state.select_context
            if _aura_v4_is_multi(spec)
            else step.expected_context,
            expected_context_ref=bound_ref,
        ), ()

    def _issue_step(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
        step_index: int,
        status: ResumeStatus,
        *,
        step_override: Optional[TransactionStep] = None,
        reason_codes: Sequence[str] = (),
    ) -> ResumeResult:
        if self._owner is None or self._plan is None:
            raise TransactionStoreError("cannot issue without an active owner")
        step = self._plan.steps[step_index] if step_override is None else step_override
        reasons, bound, materialized_action = _prompt_match_reasons(
            state,
            legal_options,
            step,
        )
        if reasons:
            override_rule = (
                AURA_MULTI_CALLBACK_BIND_RULE
                if (
                    step_override is not None
                    and self._plan.terminal_receipt is not None
                    and self._plan.terminal_receipt.profile
                    == TerminalReceiptProfile.AURA_JAB
                    and len(self._plan.terminal_receipt.reserved_refs) >= 2
                )
                else AURA_CTXREF_BIND_RULE
            )
            return self._failure_result(
                tuple(reasons)
                + ((override_rule,) if step_override is not None else ())
            )
        spec = self._plan.terminal_receipt
        v4 = _aura_v4_is_multi(spec)
        v4_selected_refs: Tuple[PhysicalRef, ...] = ()
        v4_reason_codes = list(reason_codes)
        if v4 and step.stage == TransactionStage.SELECT_ENERGY:
            v4_selected_refs, selected_reasons = _aura_v4_validate_selected_set(
                self._plan,
                materialized_action,
            )
            if selected_reasons:
                return self._failure_result(
                    tuple(selected_reasons)
                    + (AURA_V4_VALIDATE_SELECTED_SET_RULE,)
                )
            v4_reason_codes.extend(
                (
                    AURA_V4_CAPTURE_SELECTED_QUEUE_RULE,
                    AURA_V4_VALIDATE_SELECTED_SET_RULE,
                )
            )
        v4_queue = self._owner._aura_v4_selected_energy_refs_ordered
        v4_pending = self._owner._aura_v4_pending_callback_ref
        if v4 and step.stage == TransactionStage.SELECT_EFFECT_TARGET:
            actual_bound = step.expected_context_ref
            if actual_bound is None:
                return self._failure_result(
                    (
                        AURA_V4_CALLBACK_REF_MISSING,
                        AURA_V4_REJECT_CALLBACK_MISMATCH_RULE,
                    )
                )
            matched = next(
                (
                    reserved
                    for reserved in spec.reserved_refs
                    if _aura_callback_ref_matches(reserved, actual_bound)
                ),
                actual_bound,
            )
            if not v4_queue:
                v4_queue = (matched,)
            elif self._owner._aura_v4_target_cursor >= len(v4_queue):
                v4_queue = v4_queue + (matched,)
            v4_pending = matched
            v4_reason_codes.extend(
                (
                    AURA_V4_BIND_CALLBACK_REF_RULE,
                    AURA_V4_VALIDATE_CALLBACK_ORDER_RULE,
                )
            )
        pending_terminal = bool(
            spec is not None
            and spec.profile == TerminalReceiptProfile.AURA_JAB
            and not _aura_v4_is_multi(spec)
            and step_index == len(self._plan.steps) - 1
            and isinstance(step.expected_context_ref, PhysicalRef)
        )
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
            last_action_spec=materialized_action,
            semantic_action_specs=(
                self._owner.semantic_action_specs + (materialized_action,)
            ),
            step_index=step_index,
            callback_budget_used=self._owner.callback_budget_used + 1,
            committed=(self._owner.committed or step.irreversible_on_emit),
            _aura_v4_selected_energy_refs_ordered=(
                ()
                if v4 and step.stage == TransactionStage.SELECT_ENERGY
                else v4_queue
            ),
            _aura_v4_selected_energy_count=(
                len(v4_selected_refs)
                if v4 and step.stage == TransactionStage.SELECT_ENERGY
                else self._owner._aura_v4_selected_energy_count
            ),
            _aura_v4_pending_callback_ref=v4_pending,
            _pending_terminal_receipt=(
                True if pending_terminal else self._owner._pending_terminal_receipt
            ),
            _pending_terminal_owner=(
                self._owner.seat
                if pending_terminal
                else self._owner._pending_terminal_owner
            ),
            _pending_terminal_transaction_id=(
                self._owner.transaction_id
                if pending_terminal
                else self._owner._pending_terminal_transaction_id
            ),
            _pending_terminal_plan_digest=(
                self._owner.plan_digest
                if pending_terminal
                else self._owner._pending_terminal_plan_digest
            ),
            _pending_terminal_expected_context_ref=(
                step.expected_context_ref
                if pending_terminal
                else self._owner._pending_terminal_expected_context_ref
            ),
            _pending_terminal_turn=(
                self._owner.turn
                if pending_terminal
                else self._owner._pending_terminal_turn
            ),
        )
        return ResumeResult(
            status,
            materialized_action,
            bound,
            self._owner,
            tuple(v4_reason_codes),
        )

    def resume(
        self,
        state: PublicState,
        legal_options: Sequence[SemanticOption],
    ) -> ResumeResult:
        if self._owner is None or self._plan is None:
            return ResumeResult(ResumeStatus.NO_OWNER, None, None, None, ())

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

        spec = self._plan.terminal_receipt
        aura_v4_receipt_reason_codes: Tuple[str, ...] = ()
        if spec is None:
            if state.game_epoch != self._owner.game_epoch:
                return self._failure_result(
                    ("UNRECEIPTED_TRANSACTION_GAME_EPOCH_CHANGED",)
                )
            if (
                state.seat != self._owner.seat
                or state.turn != self._owner.turn
                or state.result != -1
            ):
                return self._failure_result(
                    ("UNRECEIPTED_TRANSACTION_TURN_OR_RESULT_CHANGED",)
                )
        else:
            if state.game_epoch != self._owner.game_epoch:
                return self._failure_result(("TERMINAL_RECEIPT_GAME_EPOCH_CHANGED",))
            if any(
                not isinstance(event, PublicReceiptEvent)
                for event in state.receipt_events
            ):
                return self._failure_result(("TERMINAL_RECEIPT_EVENT_INVALID",))
            receipt_by_identity = {
                event.canonical(): event for event in self._owner.receipt_events
            }
            for event in state.receipt_events:
                receipt_by_identity.setdefault(event.canonical(), event)
            self._owner = replace(
                self._owner,
                receipt_events=tuple(receipt_by_identity.values()),
            )
            if _aura_v4_is_multi(spec):
                self._aura_v4_backfill_legacy_owner_state()
                aura_v4_receipt_reason_codes = self._aura_v4_reconcile_pending_receipt()
                if any(
                    reason in (
                        AURA_V4_ATTACH_RECEIPT_MISSING,
                        AURA_V4_CALLBACK_REF_ALREADY_CONSUMED,
                        AURA_V4_EXTRA_CALLBACK_AFTER_COMPLETE,
                    )
                    for reason in aura_v4_receipt_reason_codes
                ):
                    return self._failure_result(aura_v4_receipt_reason_codes)
            receipt_status, receipt_reasons = _terminal_receipt_status(
                self._plan,
                self._owner,
                state,
            )
            final_callback_issued = self._owner.step_index >= len(self._plan.steps) - 1
            if state.seat != self._owner.seat or state.result != -1:
                return self._failure_result(
                    ("TERMINAL_RECEIPT_SEAT_OR_RESULT_CHANGED",) + receipt_reasons
                )
            pending_terminal = self._owner._pending_terminal_receipt
            if pending_terminal and final_callback_issued and (
                state.turn != self._owner.turn
                or receipt_status == TerminalReceiptStatus.COMPLETE
            ):
                was_aura = (
                    spec.profile == TerminalReceiptProfile.AURA_JAB
                    and self._owner.expected_context_ref is not None
                )
                completion_reasons = (
                    _aura_completion_reasons(spec)
                    if was_aura
                    else ()
                )
                pending_result = self._consume_pending_terminal_receipt(
                    spec,
                    completion_reasons,
                )
                if pending_result is not None:
                    return pending_result
            if state.turn != self._owner.turn:
                if (
                    spec.allow_turn_transition
                    and final_callback_issued
                    and receipt_status == TerminalReceiptStatus.COMPLETE
                ):
                    was_aura = (
                        spec.profile == TerminalReceiptProfile.AURA_JAB
                        and self._owner.expected_context_ref is not None
                    )
                    completion_reasons = (
                        _aura_completion_reasons(spec)
                        if was_aura
                        else ()
                    )
                    if _aura_v4_is_multi(spec):
                        self._owner = replace(
                            self._owner,
                            _aura_v4_completed=True,
                            _aura_v4_owner_released=True,
                        )
                    self._release_owner()
                    return ResumeResult(
                        ResumeStatus.COMPLETED,
                        None,
                        None,
                        None,
                        completion_reasons,
                    )
                return self._failure_result(
                    ("TERMINAL_RECEIPT_TURN_CHANGED",) + receipt_reasons
                )
            if (
                spec.allow_automatic_completion
                and spec.allow_same_turn_completion
                and final_callback_issued
                and receipt_status == TerminalReceiptStatus.COMPLETE
            ):
                was_aura = (
                    spec.profile == TerminalReceiptProfile.AURA_JAB
                    and self._owner.expected_context_ref is not None
                )
                completion_reasons = (
                    _aura_completion_reasons(spec)
                    if was_aura
                    else ()
                )
                if _aura_v4_is_multi(spec):
                    self._owner = replace(
                        self._owner,
                        _aura_v4_completed=True,
                        _aura_v4_owner_released=True,
                    )
                self._release_owner()
                return ResumeResult(
                    ResumeStatus.COMPLETED,
                    None,
                    None,
                    None,
                    completion_reasons,
                )

        last_action_count = (
            None
            if self._owner.last_prompt_fingerprint is None
            else self._owner.last_prompt_fingerprint.turn_action_count
        )
        if state.turn_action_count < self._owner.start_action_count or (
            last_action_count is not None
            and state.turn_action_count < last_action_count
        ):
            return self._failure_result(("TURN_ACTION_COUNT_REGRESSED",))

        current_step = (
            self._plan.initiation
            if self._owner.step_index == -1
            else self._plan.steps[self._owner.step_index]
        )
        if (
            spec is not None
            and spec.profile == TerminalReceiptProfile.AURA_JAB
            and self._owner.step_index >= 1
            and current_step.stage == TransactionStage.SELECT_EFFECT_TARGET
            and self._owner.expected_context_ref is not None
        ):
            current_step = replace(
                current_step,
                expected_context_ref=self._owner.expected_context_ref,
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
        if current_prompt.digest() == self._owner.last_prompt_fingerprint.digest():
            reasons, bound, rebound_action = _prompt_match_reasons(
                state,
                legal_options,
                current_step,
                action_spec_override=self._owner.last_action_spec,
            )
            if reasons:
                return self._failure_result(reasons)
            return ResumeResult(
                ResumeStatus.DUPLICATE_REISSUE,
                rebound_action,
                bound,
                self._owner,
                (),
            )

        if current_step.stochastic_boundary:
            if spec is None and _stable_main(state):
                self._release_owner()
                return ResumeResult(
                    ResumeStatus.STOCHASTIC_RELEASE,
                    None,
                    None,
                    None,
                    ("STOCHASTIC_BOUNDARY_REPLAN",),
                )
            if spec is not None and _stable_main(state):
                return self._failure_result(
                    ("STOCHASTIC_TERMINAL_RECEIPT_MISSING",) + receipt_reasons
                )
            return self._failure_result(("UNEXPECTED_PROMPT_AFTER_STOCHASTIC_STEP",))

        next_index = self._owner.step_index + 1
        if next_index >= len(self._plan.steps):
            if (
                spec is not None
                and _aura_v4_is_multi(spec)
                and state.context_ref is not None
            ):
                return self._failure_result(
                    (
                        AURA_V4_EXTRA_CALLBACK_AFTER_COMPLETE,
                        AURA_V4_REJECT_CALLBACK_MISMATCH_RULE,
                    )
                )
            if spec is None and _stable_main(state):
                self._release_owner()
                return ResumeResult(
                    ResumeStatus.COMPLETED,
                    None,
                    None,
                    None,
                    (),
                )
            if spec is not None and _stable_main(state):
                return self._failure_result(
                    ("TERMINAL_RECEIPT_MISSING_AT_MAIN",) + receipt_reasons
                )
            return self._failure_result(("UNEXPECTED_PROMPT_AFTER_FINAL_STEP",))

        if spec is not None and spec.profile == TerminalReceiptProfile.WALLY_REBOOT:
            if next_index == len(self._plan.steps) - 1:
                return_status, return_reasons = _wally_return_receipt(
                    spec,
                    state,
                    self._owner.receipt_events,
                )
                if return_status != TerminalReceiptStatus.COMPLETE:
                    return self._failure_result(
                        ("WALLY_REATTACH_BEFORE_RETURN_RECEIPT",) + return_reasons
                    )

        if (
            spec is not None
            and spec.profile == TerminalReceiptProfile.AURA_JAB
            and next_index >= 2
        ):
            consumed_refs = _aura_consumed_callback_refs(self._owner, spec)
            if len(consumed_refs) < next_index - 1:
                return self._failure_result(
                    (
                        "AURA_PRECEDING_ATTACH_RECEIPT_MISSING",
                        AURA_MULTI_CALLBACK_RECEIPT_RULE
                        if len(spec.reserved_refs) >= 2
                        else AURA_CTXREF_COMPLETE_RULE,
                    )
                )

        step_override, aura_binding_reasons = self._aura_target_step_override(
            state,
            legal_options,
            next_index,
        )
        if aura_binding_reasons:
            return self._failure_result(aura_binding_reasons)
        repair_reason_codes = (
            (
                *aura_v4_receipt_reason_codes,
                AURA_V4_BIND_CALLBACK_REF_RULE,
                AURA_V4_VALIDATE_CALLBACK_ORDER_RULE,
            )
            if step_override is not None and len(spec.reserved_refs) >= 2
            else (
                AURA_CTXREF_CAPTURE_RULE,
                AURA_CTXREF_OWNER_RULE,
                AURA_CTXREF_BIND_RULE,
            )
            if step_override is not None
            else ()
        )

        return self._issue_step(
            state,
            legal_options,
            next_index,
            ResumeStatus.ADVANCED_ISSUE,
            step_override=step_override,
            reason_codes=repair_reason_codes,
        )


__all__ = [
    "AURA_V4_SUPPORTED_ENERGY_COUNTS",
    "AURA_V4_CAPTURE_SELECTED_QUEUE_RULE",
    "AURA_V4_VALIDATE_SELECTED_SET_RULE",
    "AURA_V4_BIND_CALLBACK_REF_RULE",
    "AURA_V4_VALIDATE_CALLBACK_ORDER_RULE",
    "AURA_V4_ACCEPT_TARGET_RECEIPT_RULE",
    "AURA_V4_ADVANCE_TARGET_CURSOR_RULE",
    "AURA_V4_COMPLETE_AFTER_ALL_RECEIPTS_RULE",
    "AURA_V4_REJECT_CALLBACK_MISMATCH_RULE",
    "AURA_V4_RELEASE_OWNER_RULE",
    "AURA_V4_UNSUPPORTED_ENERGY_COUNT",
    "AURA_V4_SELECTED_ORDER_UNAVAILABLE",
    "AURA_V4_SELECTED_COUNT_PLAN_MISMATCH",
    "AURA_V4_SELECTED_SET_RESERVED_MISMATCH",
    "AURA_V4_DUPLICATE_SELECTED_REF",
    "AURA_V4_CALLBACK_REF_MISSING",
    "AURA_V4_CALLBACK_REF_NOT_SELECTED",
    "AURA_V4_CALLBACK_REF_ALREADY_CONSUMED",
    "AURA_V4_CALLBACK_ORDER_MISMATCH",
    "AURA_V4_CALLBACK_OWNER_MISMATCH",
    "AURA_V4_CALLBACK_TRANSACTION_MISMATCH",
    "AURA_V4_CALLBACK_PROMPT_TYPE_MISMATCH",
    "AURA_V4_TARGET_CONTEXT_MISMATCH",
    "AURA_V4_TARGET_REF_MISMATCH",
    "AURA_V4_TARGET_OWNER_MISMATCH",
    "AURA_V4_TARGET_RECEIPT_MISSING",
    "AURA_V4_ATTACH_RECEIPT_MISSING",
    "AURA_V4_EXTRA_CALLBACK_AFTER_COMPLETE",
    "AURA_V4_RELEASE_COUNT_MISMATCH",
    "AURA_MULTI_CALLBACK_BIND_RULE",
    "AURA_MULTI_CALLBACK_CAPTURE_RULE",
    "AURA_MULTI_CALLBACK_COMPLETE_RULE",
    "AURA_MULTI_CALLBACK_CONSUME_RULE",
    "AURA_MULTI_CALLBACK_RECEIPT_RULE",
    "AURA_MULTI_CALLBACK_RELEASE_RULE",
    "AURA_TERMINAL_PENDING_RECEIPT_STORE_RULE",
    "AURA_TERMINAL_PENDING_RECEIPT_CONSUME_RULE",
    "AURA_TERMINAL_PENDING_RECEIPT_REJECT_RULE",
    "AURA_TERMINAL_PENDING_RECEIPT_MISMATCH",
    "DeferredCardClassChoice",
    "FaultRecord",
    "OwnerKind",
    "ResumeResult",
    "ResumeStatus",
    "StartResult",
    "StartStatus",
    "TerminalReceiptProfile",
    "TerminalReceiptSpec",
    "TerminalReceiptStatus",
    "TransactionPlan",
    "TransactionStage",
    "TransactionState",
    "TransactionStep",
    "TransactionStore",
    "TransactionStoreError",
    "build_poke_pad_core_search_plan",
    "build_aura_jab_plan",
    "build_boss_gust_plan",
    "build_hariyama_gust_plan",
    "build_switch_plan",
    "build_ultra_ball_plan",
    "build_wally_plan",
    "build_deck_search_plan",
    "build_lunar_cycle_plan",
]
