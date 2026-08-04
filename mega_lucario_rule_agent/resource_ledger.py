"""Immutable physical-card reservations for deterministic route planning."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum
from typing import Iterable, Optional, Sequence, Tuple

try:  # Package import in tests.
    from .card_meta import (
        ADOPTED_CANONICAL_COUNTER_HASH,
        DECK_COUNTER,
        canonical_counter_hash,
    )
    from .state_view import (
        AreaType,
        PhysicalRef,
        PublicState,
        SelectContext,
        SelectType,
    )
except ImportError:  # Flat submission import from main.py.
    from card_meta import (
        ADOPTED_CANONICAL_COUNTER_HASH,
        DECK_COUNTER,
        canonical_counter_hash,
    )
    from state_view import (
        AreaType,
        PhysicalRef,
        PublicState,
        SelectContext,
        SelectType,
    )


class ReservationKind(IntEnum):
    HARD_RESERVED = 0
    CURRENT_ROUTE = 1
    NEXT_ATTACKER = 2
    MATCHUP_MINIMUM = 3
    ROLE_RESERVED_ONE = 4


FIXED_DECK_COUNTS = tuple(
    sorted((int(card_id), int(count)) for card_id, count in DECK_COUNTER.items())
)
FIXED_DECK_SIZE = sum(count for _, count in FIXED_DECK_COUNTS)
FIXED_DECK_COUNTER_HASH = canonical_counter_hash(
    card_id
    for card_id, count in FIXED_DECK_COUNTS
    for _ in range(count)
)
if (
    FIXED_DECK_SIZE != 60
    or FIXED_DECK_COUNTER_HASH != ADOPTED_CANONICAL_COUNTER_HASH
    or any(card_id <= 0 or count <= 0 for card_id, count in FIXED_DECK_COUNTS)
):
    raise RuntimeError("fixed Mega Lucario deck metadata must contain exactly 60 cards")


class ResourceLedgerError(ValueError):
    """Base error for an invalid or impossible ledger operation."""


class InsufficientUnreservedResources(ResourceLedgerError):
    """Raised when a requested physical reservation cannot be satisfied."""


def _require_exact_ref(ref_value: PhysicalRef) -> None:
    if not isinstance(ref_value, PhysicalRef):
        raise ResourceLedgerError("resource references must be PhysicalRef values")
    if (
        ref_value.card_id is None
        or ref_value.serial is None
        or ref_value.owner is None
        or ref_value.zone is None
    ):
        raise ResourceLedgerError("resource references require card_id, serial, owner, and zone")


def _ref_tuple(refs: Iterable[PhysicalRef]) -> Tuple[PhysicalRef, ...]:
    values = tuple(refs)
    for ref_value in values:
        _require_exact_ref(ref_value)
    return tuple(sorted(values, key=lambda value: value.sort_key()))


def _physical_identity(ref_value: PhysicalRef) -> Tuple[int, int]:
    _require_exact_ref(ref_value)
    return int(ref_value.owner), int(ref_value.serial)


@dataclass(frozen=True)
class Reservation:
    reservation_id: str
    kind: ReservationKind
    reason: str
    refs: Tuple[PhysicalRef, ...]
    role_card_ids: Tuple[int, ...] = ()
    required_count: int = 0
    allowed_zones: Tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.reservation_id or not self.reservation_id.strip():
            raise ResourceLedgerError("reservation_id must be non-empty")
        if not self.reason or not self.reason.strip():
            raise ResourceLedgerError("reservation reason must be non-empty")
        if any(
            isinstance(card_id, bool) or not isinstance(card_id, int)
            for card_id in self.role_card_ids
        ):
            raise ResourceLedgerError("role_card_ids must contain exact integers")
        normalized_ids = tuple(sorted(set(int(card_id) for card_id in self.role_card_ids)))
        if any(card_id <= 0 for card_id in normalized_ids):
            raise ResourceLedgerError("role_card_ids must contain positive card IDs")
        if isinstance(self.required_count, bool) or not isinstance(self.required_count, int):
            raise ResourceLedgerError("required_count must be an exact integer")
        if any(
            isinstance(zone, bool) or not isinstance(zone, int)
            for zone in self.allowed_zones
        ):
            raise ResourceLedgerError("allowed_zones must contain exact integers")
        normalized_zones = tuple(sorted(set(int(zone) for zone in self.allowed_zones)))
        if any(zone <= 0 for zone in normalized_zones):
            raise ResourceLedgerError("allowed_zones must contain positive zone IDs")

        normalized_refs = _ref_tuple(self.refs)
        identities = tuple(_physical_identity(ref_value) for ref_value in normalized_refs)
        if len(set(identities)) != len(identities):
            raise ResourceLedgerError("a reservation cannot contain duplicate physical cards")
        is_exact = bool(normalized_refs)
        is_role_constraint = (
            not normalized_refs
            and bool(normalized_ids)
            and self.required_count > 0
            and bool(normalized_zones)
        )
        if not is_exact and not is_role_constraint:
            raise ResourceLedgerError(
                "reservation must be exact refs or a positive role minimum with zones"
            )
        if is_exact and self.required_count != 0:
            raise ResourceLedgerError("exact reservations cannot also declare required_count")
        if normalized_ids and any(
            int(ref_value.card_id) not in normalized_ids for ref_value in normalized_refs
        ):
            raise ResourceLedgerError("reserved card is outside the declared role_card_ids")
        if normalized_zones and any(
            int(ref_value.zone) not in normalized_zones for ref_value in normalized_refs
        ):
            raise ResourceLedgerError("reserved card is outside the declared allowed_zones")
        object.__setattr__(self, "kind", ReservationKind(self.kind))
        object.__setattr__(self, "refs", normalized_refs)
        object.__setattr__(self, "role_card_ids", normalized_ids)
        object.__setattr__(self, "allowed_zones", normalized_zones)

    def sort_key(self) -> Tuple[object, ...]:
        return (
            int(self.kind),
            self.reservation_id,
            self.reason,
            tuple(ref_value.sort_key() for ref_value in self.refs),
            self.role_card_ids,
            self.required_count,
            self.allowed_zones,
        )

    @property
    def is_role_constraint(self) -> bool:
        return not self.refs


def _bind_reservations(
    visible_refs: Tuple[PhysicalRef, ...],
    reservations: Tuple[Reservation, ...],
) -> Tuple[Reservation, ...]:
    exact = tuple(reservation for reservation in reservations if reservation.refs)
    constraints = tuple(reservation for reservation in reservations if reservation.is_role_constraint)
    exact_identities = {
        _physical_identity(ref_value)
        for reservation in exact
        for ref_value in reservation.refs
    }
    available = tuple(
        ref_value
        for ref_value in visible_refs
        if _physical_identity(ref_value) not in exact_identities
    )
    slots = tuple(
        (reservation, slot_index)
        for reservation in constraints
        for slot_index in range(reservation.required_count)
    )
    assigned = {}
    used = set()

    def candidates_for(reservation: Reservation) -> Tuple[PhysicalRef, ...]:
        return tuple(
            ref_value
            for ref_value in available
            if _physical_identity(ref_value) not in used
            and int(ref_value.card_id) in reservation.role_card_ids
            and int(ref_value.zone) in reservation.allowed_zones
        )

    def search(remaining_slots: Tuple[Tuple[Reservation, int], ...]) -> bool:
        if not remaining_slots:
            return True
        ranked = []
        for slot in remaining_slots:
            reservation, slot_index = slot
            candidates = candidates_for(reservation)
            ranked.append(
                (
                    len(candidates),
                    len(reservation.role_card_ids),
                    reservation.role_card_ids,
                    reservation.reservation_id,
                    slot_index,
                    slot,
                    candidates,
                )
            )
        ranked.sort(key=lambda row: row[:5])
        _, _, _, _, _, chosen_slot, candidates = ranked[0]
        if not candidates:
            return False
        next_slots = tuple(slot for slot in remaining_slots if slot != chosen_slot)
        for ref_value in candidates:
            identity = _physical_identity(ref_value)
            used.add(identity)
            assigned[chosen_slot] = ref_value
            if search(next_slots):
                return True
            assigned.pop(chosen_slot, None)
            used.remove(identity)
        return False

    if not search(slots):
        raise InsufficientUnreservedResources(
            "role minimum reservations have no joint physical-card assignment"
        )

    bound = list(exact)
    for reservation in constraints:
        refs = tuple(
            assigned[(reservation, slot_index)]
            for slot_index in range(reservation.required_count)
        )
        bound.append(
            Reservation(
                reservation_id=reservation.reservation_id,
                kind=reservation.kind,
                reason=reservation.reason,
                refs=refs,
                role_card_ids=reservation.role_card_ids,
                allowed_zones=reservation.allowed_zones,
            )
        )
    return tuple(sorted(bound, key=lambda value: value.sort_key()))


@dataclass(frozen=True)
class CostCheck:
    affordable: bool
    cost_refs: Tuple[PhysicalRef, ...]
    rejection_reasons: Tuple[str, ...]


@dataclass(frozen=True)
class ResourceLedger:
    visible_refs: Tuple[PhysicalRef, ...]
    reservations: Tuple[Reservation, ...] = ()

    def __post_init__(self) -> None:
        visible = _ref_tuple(self.visible_refs)
        identities = tuple(_physical_identity(ref_value) for ref_value in visible)
        if len(set(identities)) != len(identities):
            raise ResourceLedgerError("visible resources contain a duplicate physical card")
        owners = {int(ref_value.owner) for ref_value in visible}
        if len(owners) > 1:
            raise ResourceLedgerError("one ledger cannot mix resources owned by both players")

        reservations = tuple(sorted(self.reservations, key=lambda value: value.sort_key()))
        reservation_ids = tuple(value.reservation_id for value in reservations)
        if len(set(reservation_ids)) != len(reservation_ids):
            raise ResourceLedgerError("reservation_id values must be unique")

        visible_set = set(visible)
        already_reserved = set()
        for reservation in reservations:
            for ref_value in reservation.refs:
                if ref_value not in visible_set:
                    raise ResourceLedgerError(
                        "reservation references a card outside the visible resource snapshot"
                    )
                identity = _physical_identity(ref_value)
                if identity in already_reserved:
                    raise ResourceLedgerError(
                        "one physical card cannot satisfy multiple additive reservations"
                    )
                already_reserved.add(identity)
        _bind_reservations(visible, reservations)

        object.__setattr__(self, "visible_refs", visible)
        object.__setattr__(self, "reservations", reservations)

    @property
    def owner(self) -> Optional[int]:
        return None if not self.visible_refs else int(self.visible_refs[0].owner)

    @property
    def bound_reservations(self) -> Tuple[Reservation, ...]:
        return _bind_reservations(self.visible_refs, self.reservations)

    @property
    def reserved_refs(self) -> Tuple[PhysicalRef, ...]:
        return _ref_tuple(
            ref_value
            for reservation in self.bound_reservations
            for ref_value in reservation.refs
        )

    def reservation_for(self, ref_value: PhysicalRef) -> Optional[Reservation]:
        for reservation in self.bound_reservations:
            if ref_value in reservation.refs:
                return reservation
        return None

    def get_reservation(self, reservation_id: str) -> Optional[Reservation]:
        return next(
            (
                reservation
                for reservation in self.reservations
                if reservation.reservation_id == reservation_id
            ),
            None,
        )

    def is_reserved(self, ref_value: PhysicalRef) -> bool:
        return self.reservation_for(ref_value) is not None

    def is_hard_reserved(self, ref_value: PhysicalRef) -> bool:
        reservation = self.reservation_for(ref_value)
        return reservation is not None and reservation.kind == ReservationKind.HARD_RESERVED

    def visible_count(self, card_ids: Optional[Iterable[int]] = None) -> int:
        if card_ids is None:
            return len(self.visible_refs)
        wanted = frozenset(int(card_id) for card_id in card_ids)
        return sum(int(ref_value.card_id) in wanted for ref_value in self.visible_refs)

    def reserved_count(self, card_ids: Optional[Iterable[int]] = None) -> int:
        if card_ids is None:
            return len(self.reserved_refs)
        wanted = frozenset(int(card_id) for card_id in card_ids)
        return sum(int(ref_value.card_id) in wanted for ref_value in self.reserved_refs)

    def unreserved_refs(
        self,
        card_ids: Optional[Iterable[int]] = None,
        allowed_zones: Optional[Iterable[int]] = (int(AreaType.HAND),),
    ) -> Tuple[PhysicalRef, ...]:
        wanted = None if card_ids is None else frozenset(int(card_id) for card_id in card_ids)
        zones = None if allowed_zones is None else frozenset(int(zone) for zone in allowed_zones)
        reserved = set(self.reserved_refs)
        return tuple(
            ref_value
            for ref_value in self.visible_refs
            if ref_value not in reserved
            and (wanted is None or int(ref_value.card_id) in wanted)
            and (zones is None or int(ref_value.zone) in zones)
        )

    def surplus_count(
        self,
        card_ids: Optional[Iterable[int]] = None,
        allowed_zones: Optional[Iterable[int]] = (int(AreaType.HAND),),
    ) -> int:
        return len(self.unreserved_refs(card_ids, allowed_zones))

    def check_cost(
        self,
        cost_refs: Sequence[PhysicalRef],
        allowed_zones: Optional[Iterable[int]] = (int(AreaType.HAND),),
    ) -> CostCheck:
        raw_cost = tuple(cost_refs)
        reasons = []
        normalized = []
        identities = []
        zones = None if allowed_zones is None else frozenset(int(zone) for zone in allowed_zones)
        for ref_value in raw_cost:
            try:
                _require_exact_ref(ref_value)
            except ResourceLedgerError:
                reasons.append("INEXACT_COST_REF")
                continue
            normalized.append(ref_value)
            identities.append(_physical_identity(ref_value))
            if zones is not None and int(ref_value.zone) not in zones:
                reasons.append("INVALID_COST_ZONE:{0}".format(int(ref_value.zone)))
        if len(set(identities)) != len(identities):
            reasons.append("DUPLICATE_COST_REF")

        visible = set(self.visible_refs)
        for ref_value in normalized:
            if ref_value not in visible:
                reasons.append("UNKNOWN_COST_REF:{0}".format(ref_value.sort_key()))
                continue
            reservation = next(
                (
                    declared
                    for declared in self.reservations
                    if declared.refs and ref_value in declared.refs
                ),
                None,
            )
            if reservation is not None:
                reasons.append("RESERVED:{0}".format(reservation.reservation_id))
        if not reasons:
            cost_identities = set(identities)
            remaining = tuple(
                ref_value
                for ref_value in self.visible_refs
                if _physical_identity(ref_value) not in cost_identities
            )
            try:
                _bind_reservations(remaining, self.reservations)
            except ResourceLedgerError:
                reasons.append("RESERVATION_CONSTRAINT")
        normalized_tuple = tuple(sorted(normalized, key=lambda value: value.sort_key()))
        unique_reasons = tuple(sorted(set(reasons)))
        return CostCheck(not unique_reasons, normalized_tuple, unique_reasons)

    def affords(
        self,
        cost_refs: Sequence[PhysicalRef],
        allowed_zones: Optional[Iterable[int]] = (int(AreaType.HAND),),
    ) -> bool:
        return self.check_cost(cost_refs, allowed_zones).affordable

    def reserve_exact(
        self,
        reservation_id: str,
        kind: ReservationKind,
        reason: str,
        refs: Sequence[PhysicalRef],
        role_card_ids: Sequence[int] = (),
    ) -> "ResourceLedger":
        reservation = Reservation(
            reservation_id=reservation_id,
            kind=kind,
            reason=reason,
            refs=tuple(refs),
            role_card_ids=tuple(role_card_ids),
        )
        try:
            return ResourceLedger(self.visible_refs, self.reservations + (reservation,))
        except ResourceLedgerError as error:
            raise InsufficientUnreservedResources(
                "cannot reserve physical cards: {0}".format(error)
            ) from error

    def reserve_minimum(
        self,
        reservation_id: str,
        kind: ReservationKind,
        reason: str,
        role_card_ids: Sequence[int],
        count: int,
        allowed_zones: Sequence[int] = (int(AreaType.HAND),),
    ) -> "ResourceLedger":
        if any(
            isinstance(card_id, bool) or not isinstance(card_id, int)
            for card_id in role_card_ids
        ):
            raise ResourceLedgerError("role_card_ids must contain exact integers")
        normalized_ids = tuple(sorted(set(int(card_id) for card_id in role_card_ids)))
        if not normalized_ids or any(card_id <= 0 for card_id in normalized_ids):
            raise ResourceLedgerError("role_card_ids must contain positive card IDs")
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise ResourceLedgerError("reservation count must be positive")
        reservation = Reservation(
            reservation_id=reservation_id,
            kind=kind,
            reason=reason,
            refs=(),
            role_card_ids=normalized_ids,
            required_count=count,
            allowed_zones=tuple(allowed_zones),
        )
        try:
            return ResourceLedger(self.visible_refs, self.reservations + (reservation,))
        except ResourceLedgerError as error:
            raise InsufficientUnreservedResources(
                "cannot satisfy role minimum: {0}".format(error)
            ) from error

    def release(self, reservation_id: str) -> "ResourceLedger":
        if self.get_reservation(reservation_id) is None:
            raise ResourceLedgerError("unknown reservation_id")
        return ResourceLedger(
            self.visible_refs,
            tuple(
                reservation
                for reservation in self.reservations
                if reservation.reservation_id != reservation_id
            ),
        )


@dataclass(frozen=True)
class DeckAvailabilityProof:
    card_ids: Tuple[int, ...]
    total_copies: int
    own_deck_count: int
    known_outside_deck: int
    known_prized: int
    unknown_prize_count: int
    lower_bound_in_deck: int
    required_count: int
    fixed_deck_size: int
    deck_counter_hash: str
    is_guaranteed: bool
    rejection_reasons: Tuple[str, ...]


def _is_exact_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def prove_deck_availability(
    card_ids: Sequence[int],
    owner: int,
    own_deck_count: int,
    known_outside_deck_refs: Sequence[PhysicalRef],
    known_prized_refs: Sequence[PhysicalRef],
    unknown_prize_count: int,
    required_count: int = 1,
) -> DeckAvailabilityProof:
    """Prove a conservative lower bound for a target class in the own deck."""

    reasons = []
    normalized_ids = []
    for card_id in card_ids:
        if not _is_exact_int(card_id) or int(card_id) <= 0:
            reasons.append("INVALID_CARD_ID")
        else:
            normalized_ids.append(int(card_id))
    target_ids = tuple(sorted(set(normalized_ids)))
    if not target_ids:
        reasons.append("EMPTY_TARGET_CLASS")
    if not _is_exact_int(owner) or owner not in (0, 1):
        reasons.append("INVALID_OWNER")
    if not _is_exact_int(own_deck_count) or not 0 <= own_deck_count <= 60:
        reasons.append("INVALID_DECK_COUNT")
    if (
        not _is_exact_int(unknown_prize_count)
        or not 0 <= unknown_prize_count <= 6
    ):
        reasons.append("INVALID_UNKNOWN_PRIZE_COUNT")
    if not _is_exact_int(required_count) or required_count <= 0:
        reasons.append("INVALID_REQUIRED_COUNT")

    try:
        outside_refs = _ref_tuple(known_outside_deck_refs)
    except ResourceLedgerError:
        outside_refs = ()
        reasons.append("INEXACT_OUTSIDE_DECK_REF")
    try:
        prized_refs = _ref_tuple(known_prized_refs)
    except ResourceLedgerError:
        prized_refs = ()
        reasons.append("INEXACT_PRIZE_REF")

    allowed_outside_zones = {
        int(AreaType.HAND),
        int(AreaType.DISCARD),
        int(AreaType.ACTIVE),
        int(AreaType.BENCH),
        int(AreaType.STADIUM),
        int(AreaType.ENERGY),
        int(AreaType.TOOL),
        int(AreaType.PRE_EVOLUTION),
    }
    if any(int(ref_value.zone) not in allowed_outside_zones for ref_value in outside_refs):
        reasons.append("INVALID_OUTSIDE_DECK_ZONE")
    if any(int(ref_value.zone) != int(AreaType.PRIZE) for ref_value in prized_refs):
        reasons.append("INVALID_PRIZE_ZONE")
    if _is_exact_int(owner) and owner in (0, 1):
        if any(int(ref_value.owner) != owner for ref_value in outside_refs + prized_refs):
            reasons.append("WRONG_OWNER_REF")
    identities = tuple(
        _physical_identity(ref_value) for ref_value in outside_refs + prized_refs
    )
    if len(set(identities)) != len(identities):
        reasons.append("DUPLICATE_PHYSICAL_REF")

    fixed_counts = dict(FIXED_DECK_COUNTS)
    total_copies = sum(fixed_counts.get(card_id, 0) for card_id in target_ids)
    if total_copies <= 0:
        reasons.append("TARGET_NOT_IN_FIXED_DECK")
    known_outside = sum(
        int(ref_value.card_id) in target_ids for ref_value in outside_refs
    )
    known_prized = sum(int(ref_value.card_id) in target_ids for ref_value in prized_refs)
    if known_outside + known_prized > total_copies:
        reasons.append("VISIBLE_TARGET_COUNT_EXCEEDS_FIXED_DECK")
    deck_count_value = own_deck_count if _is_exact_int(own_deck_count) else 0
    unknown_prize_value = (
        unknown_prize_count if _is_exact_int(unknown_prize_count) else 6
    )
    required_value = required_count if _is_exact_int(required_count) else 1
    lower_bound = max(
        0,
        min(
            max(0, deck_count_value),
            total_copies - known_outside - known_prized - unknown_prize_value,
        ),
    )
    if lower_bound < max(1, required_value):
        reasons.append("LOWER_BOUND_BELOW_REQUIRED")
    rejection_reasons = tuple(sorted(set(reasons)))
    return DeckAvailabilityProof(
        card_ids=target_ids,
        total_copies=total_copies,
        own_deck_count=max(0, deck_count_value),
        known_outside_deck=known_outside,
        known_prized=known_prized,
        unknown_prize_count=max(0, unknown_prize_value),
        lower_bound_in_deck=lower_bound,
        required_count=max(1, required_value),
        fixed_deck_size=FIXED_DECK_SIZE,
        deck_counter_hash=FIXED_DECK_COUNTER_HASH,
        is_guaranteed=not rejection_reasons,
        rejection_reasons=rejection_reasons,
    )


def prove_deck_availability_from_state(
    state: PublicState,
    card_ids: Sequence[int],
    required_count: int = 1,
) -> DeckAvailabilityProof:
    outside = list(state.own.hand_refs) + list(state.own.discard_refs)
    for pokemon in state.own.active + state.own.bench:
        outside.append(pokemon.ref)
        outside.extend(pokemon.energy_refs)
        outside.extend(pokemon.tool_refs)
        outside.extend(pokemon.pre_evolution_refs)
    outside.extend(
        ref_value
        for ref_value in state.stadium_refs
        if ref_value.owner == state.seat
    )
    unknown_prizes = state.own.prize_count - len(state.own.prize_refs)
    proof = prove_deck_availability(
        card_ids=card_ids,
        owner=state.seat,
        own_deck_count=state.own.deck_count,
        known_outside_deck_refs=outside,
        known_prized_refs=state.own.prize_refs,
        unknown_prize_count=unknown_prizes,
        required_count=required_count,
    )
    extra_reasons = []
    if (
        state.select_type != int(SelectType.MAIN)
        or state.select_context != int(SelectContext.MAIN)
        or state.min_count != 1
        or state.max_count != 1
        or state.effect_ref is not None
        or state.context_ref is not None
        or state.select_deck_open
        or state.turn <= 0
        or state.result != -1
    ):
        extra_reasons.append("UNSTABLE_SELECTION_CONTEXT")
    if state.looking_refs or state.looking_open:
        extra_reasons.append("UNSTABLE_LOOKING_ZONE")
    if extra_reasons:
        return replace(
            proof,
            is_guaranteed=False,
            rejection_reasons=tuple(
                sorted(set(proof.rejection_reasons + tuple(extra_reasons)))
            ),
        )
    return proof


__all__ = [
    "CostCheck",
    "DeckAvailabilityProof",
    "FIXED_DECK_COUNTS",
    "FIXED_DECK_COUNTER_HASH",
    "FIXED_DECK_SIZE",
    "InsufficientUnreservedResources",
    "Reservation",
    "ReservationKind",
    "ResourceLedger",
    "ResourceLedgerError",
    "prove_deck_availability",
    "prove_deck_availability_from_state",
]
