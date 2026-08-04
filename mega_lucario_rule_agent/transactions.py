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
        OptionType,
        PhysicalRef,
        PromptFingerprint,
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
        OptionType,
        PhysicalRef,
        PromptFingerprint,
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
            fault_latched=False,
            fault_code=None,
            _issuer_token=_STATE_ISSUER_TOKEN,
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
        reasons, bound, materialized_action = _prompt_match_reasons(
            state,
            legal_options,
            step,
        )
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
            last_action_spec=materialized_action,
            semantic_action_specs=(
                self._owner.semantic_action_specs + (materialized_action,)
            ),
            step_index=step_index,
            callback_budget_used=self._owner.callback_budget_used + 1,
            committed=(self._owner.committed or step.irreversible_on_emit),
        )
        return ResumeResult(
            status,
            materialized_action,
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
            if _stable_main(state):
                self._release_owner()
                return ResumeResult(
                    ResumeStatus.STOCHASTIC_RELEASE,
                    None,
                    None,
                    None,
                    ("STOCHASTIC_BOUNDARY_REPLAN",),
                )
            return self._failure_result(("UNEXPECTED_PROMPT_AFTER_STOCHASTIC_STEP",))

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
    "DeferredCardClassChoice",
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
    "build_poke_pad_core_search_plan",
    "build_aura_jab_plan",
    "build_deck_search_plan",
    "build_lunar_cycle_plan",
]
