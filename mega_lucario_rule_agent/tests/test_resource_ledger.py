import pytest

from mega_lucario_rule_agent.resource_ledger import (
    InsufficientUnreservedResources,
    ReservationKind,
    ResourceLedger,
    ResourceLedgerError,
)
from mega_lucario_rule_agent.state_view import AreaType, PhysicalRef


def ref(card_id, serial, owner=0, zone=AreaType.HAND):
    return PhysicalRef(card_id, serial, owner, int(zone), serial)


def test_hard_reservation_protects_one_physical_copy_only():
    first = ref(6, 11)
    second = ref(6, 12)
    ledger = ResourceLedger((second, first)).reserve_exact(
        "manual_attach",
        ReservationKind.HARD_RESERVED,
        "only current-turn manual attachment",
        (first,),
    )
    assert ledger.visible_refs == (first, second)
    assert ledger.is_hard_reserved(first)
    assert not ledger.is_reserved(second)
    assert ledger.surplus_count((6,)) == 1
    assert not ledger.affords((first,))
    assert ledger.affords((second,))


def test_role_minimum_uses_lower_card_id_then_serial_deterministically():
    visible = (ref(1182, 4), ref(1152, 9), ref(1152, 3))
    first = ResourceLedger(visible).reserve_minimum(
        "hand_rebuild_one",
        ReservationKind.ROLE_RESERVED_ONE,
        "keep one Lillie or Judge",
        (1182, 1152),
        1,
    )
    second = ResourceLedger(tuple(reversed(visible))).reserve_minimum(
        "hand_rebuild_one",
        ReservationKind.ROLE_RESERVED_ONE,
        "keep one Lillie or Judge",
        (1152, 1182),
        1,
    )
    assert first.reserved_refs == second.reserved_refs == (ref(1152, 3),)


def test_additive_route_reservations_use_distinct_physical_copies():
    visible = (ref(678, 20), ref(678, 21), ref(678, 22))
    ledger = ResourceLedger(visible).reserve_minimum(
        "current_mega",
        ReservationKind.CURRENT_ROUTE,
        "evolve the current Riolu",
        (678,),
        1,
    )
    ledger = ledger.reserve_minimum(
        "next_mega",
        ReservationKind.NEXT_ATTACKER,
        "retain a second Mega line",
        (678,),
        1,
    )
    assert ledger.reserved_refs == (ref(678, 20), ref(678, 21))
    assert ledger.unreserved_refs((678,)) == (ref(678, 22),)


def test_safe_cost_check_reports_reserved_unknown_and_duplicate_refs():
    protected = ref(677, 30)
    surplus = ref(673, 31)
    ledger = ResourceLedger((protected, surplus)).reserve_exact(
        "only_riolu",
        ReservationKind.HARD_RESERVED,
        "first Riolu line",
        (protected,),
    )
    check = ledger.check_cost((protected, ref(6, 99), surplus, surplus))
    assert not check.affordable
    assert "DUPLICATE_COST_REF" in check.rejection_reasons
    assert "RESERVED:only_riolu" in check.rejection_reasons
    assert any(reason.startswith("UNKNOWN_COST_REF:") for reason in check.rejection_reasons)


def test_insufficient_reservation_fails_without_changing_original_ledger():
    original = ResourceLedger((ref(678, 40),))
    with pytest.raises(InsufficientUnreservedResources):
        original.reserve_minimum(
            "two_megas",
            ReservationKind.NEXT_ATTACKER,
            "two simultaneous evolution routes",
            (678,),
            2,
        )
    assert original.reservations == ()
    assert original.surplus_count() == 1


def test_release_restores_surplus_and_unknown_release_fails():
    energy = ref(6, 50)
    ledger = ResourceLedger((energy,)).reserve_exact(
        "attach",
        ReservationKind.HARD_RESERVED,
        "manual attachment",
        (energy,),
    )
    released = ledger.release("attach")
    assert released.affords((energy,))
    assert released.reservations == ()
    with pytest.raises(ResourceLedgerError, match="unknown"):
        released.release("attach")


def test_inexact_duplicate_and_overlapping_physical_refs_fail_closed():
    with pytest.raises(ResourceLedgerError, match="require"):
        ResourceLedger((PhysicalRef(6, None, 0, int(AreaType.HAND)),))
    with pytest.raises(ResourceLedgerError, match="duplicate"):
        ResourceLedger((ref(6, 60), ref(7, 60)))
    with pytest.raises(ResourceLedgerError, match="both players"):
        ResourceLedger((ref(6, 63, owner=0), ref(6, 64, owner=1)))

    visible = (ref(6, 61), ref(6, 62))
    ledger = ResourceLedger(visible).reserve_exact(
        "first",
        ReservationKind.CURRENT_ROUTE,
        "first use",
        (visible[0],),
    )
    with pytest.raises(InsufficientUnreservedResources):
        ledger.reserve_exact(
            "second",
            ReservationKind.NEXT_ATTACKER,
            "cannot reuse one physical card",
            (visible[0],),
        )


def test_declared_role_must_contain_every_reserved_card():
    with pytest.raises(ResourceLedgerError, match="outside"):
        ResourceLedger((ref(6, 70),)).reserve_exact(
            "wrong_role",
            ReservationKind.ROLE_RESERVED_ONE,
            "invalid role declaration",
            (ref(6, 70),),
            role_card_ids=(1152, 1182),
        )
