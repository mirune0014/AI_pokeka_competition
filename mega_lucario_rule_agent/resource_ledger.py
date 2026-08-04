"""Immutable physical-card reservations for deterministic route planning."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, Optional, Sequence, Tuple

try:  # Package import in tests.
    from .state_view import PhysicalRef
except ImportError:  # Flat submission import from main.py.
    from state_view import PhysicalRef


class ReservationKind(IntEnum):
    HARD_RESERVED = 0
    CURRENT_ROUTE = 1
    NEXT_ATTACKER = 2
    MATCHUP_MINIMUM = 3
    ROLE_RESERVED_ONE = 4


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

    def __post_init__(self) -> None:
        if not self.reservation_id or not self.reservation_id.strip():
            raise ResourceLedgerError("reservation_id must be non-empty")
        if not self.reason or not self.reason.strip():
            raise ResourceLedgerError("reservation reason must be non-empty")
        normalized_refs = _ref_tuple(self.refs)
        identities = tuple(_physical_identity(ref_value) for ref_value in normalized_refs)
        if not normalized_refs:
            raise ResourceLedgerError("a reservation must contain at least one physical card")
        if len(set(identities)) != len(identities):
            raise ResourceLedgerError("a reservation cannot contain duplicate physical cards")
        normalized_ids = tuple(sorted(set(int(card_id) for card_id in self.role_card_ids)))
        if any(card_id <= 0 for card_id in normalized_ids):
            raise ResourceLedgerError("role_card_ids must contain positive card IDs")
        if normalized_ids and any(
            int(ref_value.card_id) not in normalized_ids for ref_value in normalized_refs
        ):
            raise ResourceLedgerError("reserved card is outside the declared role_card_ids")
        object.__setattr__(self, "kind", ReservationKind(self.kind))
        object.__setattr__(self, "refs", normalized_refs)
        object.__setattr__(self, "role_card_ids", normalized_ids)

    def sort_key(self) -> Tuple[object, ...]:
        return (
            int(self.kind),
            self.reservation_id,
            self.reason,
            tuple(ref_value.sort_key() for ref_value in self.refs),
            self.role_card_ids,
        )


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

        object.__setattr__(self, "visible_refs", visible)
        object.__setattr__(self, "reservations", reservations)

    @property
    def owner(self) -> Optional[int]:
        return None if not self.visible_refs else int(self.visible_refs[0].owner)

    @property
    def reserved_refs(self) -> Tuple[PhysicalRef, ...]:
        return _ref_tuple(
            ref_value
            for reservation in self.reservations
            for ref_value in reservation.refs
        )

    def reservation_for(self, ref_value: PhysicalRef) -> Optional[Reservation]:
        for reservation in self.reservations:
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
        self, card_ids: Optional[Iterable[int]] = None
    ) -> Tuple[PhysicalRef, ...]:
        wanted = None if card_ids is None else frozenset(int(card_id) for card_id in card_ids)
        reserved = set(self.reserved_refs)
        return tuple(
            ref_value
            for ref_value in self.visible_refs
            if ref_value not in reserved
            and (wanted is None or int(ref_value.card_id) in wanted)
        )

    def surplus_count(self, card_ids: Optional[Iterable[int]] = None) -> int:
        return len(self.unreserved_refs(card_ids))

    def check_cost(self, cost_refs: Sequence[PhysicalRef]) -> CostCheck:
        raw_cost = tuple(cost_refs)
        reasons = []
        normalized = []
        identities = []
        for ref_value in raw_cost:
            try:
                _require_exact_ref(ref_value)
            except ResourceLedgerError:
                reasons.append("INEXACT_COST_REF")
                continue
            normalized.append(ref_value)
            identities.append(_physical_identity(ref_value))
        if len(set(identities)) != len(identities):
            reasons.append("DUPLICATE_COST_REF")

        visible = set(self.visible_refs)
        for ref_value in normalized:
            if ref_value not in visible:
                reasons.append("UNKNOWN_COST_REF:{0}".format(ref_value.sort_key()))
                continue
            reservation = self.reservation_for(ref_value)
            if reservation is not None:
                reasons.append("RESERVED:{0}".format(reservation.reservation_id))
        normalized_tuple = tuple(sorted(normalized, key=lambda value: value.sort_key()))
        unique_reasons = tuple(sorted(set(reasons)))
        return CostCheck(not unique_reasons, normalized_tuple, unique_reasons)

    def affords(self, cost_refs: Sequence[PhysicalRef]) -> bool:
        return self.check_cost(cost_refs).affordable

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
        if not self.affords(reservation.refs):
            check = self.check_cost(reservation.refs)
            raise InsufficientUnreservedResources(
                "cannot reserve physical cards: {0}".format(
                    ",".join(check.rejection_reasons)
                )
            )
        return ResourceLedger(self.visible_refs, self.reservations + (reservation,))

    def reserve_minimum(
        self,
        reservation_id: str,
        kind: ReservationKind,
        reason: str,
        role_card_ids: Sequence[int],
        count: int,
    ) -> "ResourceLedger":
        normalized_ids = tuple(sorted(set(int(card_id) for card_id in role_card_ids)))
        if not normalized_ids or any(card_id <= 0 for card_id in normalized_ids):
            raise ResourceLedgerError("role_card_ids must contain positive card IDs")
        if int(count) <= 0:
            raise ResourceLedgerError("reservation count must be positive")
        candidates = self.unreserved_refs(normalized_ids)
        if len(candidates) < int(count):
            raise InsufficientUnreservedResources(
                "need {0} unreserved cards from role {1}; found {2}".format(
                    int(count), normalized_ids, len(candidates)
                )
            )
        return self.reserve_exact(
            reservation_id=reservation_id,
            kind=kind,
            reason=reason,
            refs=candidates[: int(count)],
            role_card_ids=normalized_ids,
        )

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


__all__ = [
    "CostCheck",
    "InsufficientUnreservedResources",
    "Reservation",
    "ReservationKind",
    "ResourceLedger",
    "ResourceLedgerError",
]
