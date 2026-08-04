from dataclasses import replace

import pytest

from mega_lucario_rule_agent.resource_ledger import (
    MANUAL_ATTACH_ENERGY_RESERVATION_ID,
    InsufficientUnreservedResources,
    ReservationKind,
    ResourceLedger,
    ResourceLedgerError,
    prove_deck_availability,
    prove_deck_availability_from_state,
    reserve_manual_attach_energy,
)
from mega_lucario_rule_agent.state_view import (
    AreaType,
    PhysicalRef,
    PlayerView,
    PublicState,
    SelectType,
)


def ref(card_id, serial, owner=0, zone=AreaType.HAND):
    return PhysicalRef(card_id, serial, owner, int(zone), serial)


def player_view(index, hand_refs=(), prize_count=6, deck_count=40):
    return PlayerView(
        index=index,
        active=(),
        active_slot_count=0,
        hidden_active_count=0,
        bench=(),
        hand_refs=tuple(hand_refs),
        discard_refs=(),
        prize_refs=(),
        prize_count=prize_count,
        deck_count=deck_count,
        hand_count=len(hand_refs) if index == 0 else 0,
        bench_max=5,
        poisoned=False,
        burned=False,
        asleep=False,
        paralyzed=False,
        confused=False,
    )


def public_state(own, opponent, looking_refs=()):
    return PublicState(
        game_epoch=0,
        seat=0,
        turn=1,
        turn_action_count=0,
        first_player=0,
        supporter_played=False,
        stadium_played=False,
        energy_attached=False,
        retreated=False,
        result=-1,
        own=own,
        opponent=opponent,
        stadium_refs=(),
        looking_refs=tuple(looking_refs),
        select_context=0,
        min_count=1,
        max_count=1,
        effect_ref=None,
        context_ref=None,
        select_type=int(SelectType.MAIN),
        remaining_damage_counter=0,
        remaining_energy_cost=0,
    )


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


def test_cost_and_surplus_are_zone_scoped_by_default():
    discard_energy = ref(6, 80, zone=AreaType.DISCARD)
    ledger = ResourceLedger((discard_energy,))
    check = ledger.check_cost((discard_energy,))
    assert not check.affordable
    assert "INVALID_COST_ZONE:3" in check.rejection_reasons
    assert ledger.surplus_count((6,)) == 0
    assert ledger.affords((discard_energy,), allowed_zones=(AreaType.DISCARD,))
    assert ledger.surplus_count((6,), allowed_zones=(AreaType.DISCARD,)) == 1
    with pytest.raises(InsufficientUnreservedResources):
        ledger.reserve_minimum(
            "hand_energy",
            ReservationKind.ROLE_RESERVED_ONE,
            "hand-only attachment resource",
            (6,),
            1,
        )


def test_overlapping_role_minima_are_jointly_reassigned_independent_of_call_order():
    narrow_card = ref(1121, 90)
    broad_only_card = ref(1142, 91)
    visible = (narrow_card, broad_only_card)

    broad_first = ResourceLedger(visible).reserve_minimum(
        "broad",
        ReservationKind.ROLE_RESERVED_ONE,
        "one generic search card",
        (1121, 1142),
        1,
    )
    broad_first = broad_first.reserve_minimum(
        "narrow",
        ReservationKind.CURRENT_ROUTE,
        "the only route-specific search card",
        (1121,),
        1,
    )

    narrow_first = ResourceLedger(tuple(reversed(visible))).reserve_minimum(
        "narrow",
        ReservationKind.CURRENT_ROUTE,
        "the only route-specific search card",
        (1121,),
        1,
    )
    narrow_first = narrow_first.reserve_minimum(
        "broad",
        ReservationKind.ROLE_RESERVED_ONE,
        "one generic search card",
        (1142, 1121),
        1,
    )

    def binding(ledger, reservation_id):
        return next(
            reservation.refs
            for reservation in ledger.bound_reservations
            if reservation.reservation_id == reservation_id
        )

    assert binding(broad_first, "narrow") == binding(narrow_first, "narrow") == (
        narrow_card,
    )
    assert binding(broad_first, "broad") == binding(narrow_first, "broad") == (
        broad_only_card,
    )


def test_cost_check_reassigns_a_broad_role_when_an_alternative_exists():
    first = ref(1121, 100)
    second = ref(1142, 101)
    broad = ResourceLedger((first, second)).reserve_minimum(
        "search_one",
        ReservationKind.ROLE_RESERVED_ONE,
        "retain either search card",
        (1121, 1142),
        1,
    )
    assert broad.reservation_for(first).reservation_id == "search_one"
    assert broad.affords((first,))

    constrained = broad.reserve_minimum(
        "exact_role",
        ReservationKind.CURRENT_ROUTE,
        "retain card 1121 specifically",
        (1121,),
        1,
    )
    assert not constrained.affords((first,))
    assert "RESERVATION_CONSTRAINT" in constrained.check_cost(
        (first,)
    ).rejection_reasons


def test_deck_availability_uses_unknown_prizes_as_conservative_target_copies():
    outside = (ref(678, 110, zone=AreaType.DISCARD),)
    guaranteed = prove_deck_availability(
        card_ids=(678,),
        owner=0,
        own_deck_count=30,
        known_outside_deck_refs=outside,
        known_prized_refs=(),
        unknown_prize_count=2,
        required_count=1,
    )
    assert guaranteed.total_copies == 4
    assert guaranteed.owner == 0
    assert guaranteed.fixed_deck_size == 60
    assert len(guaranteed.deck_counter_hash) == 64
    assert len(guaranteed.deck_state_hash) == 64
    assert guaranteed.canonical()[0] == (678,)
    assert guaranteed.known_outside_deck == 1
    assert guaranteed.lower_bound_in_deck == 1
    assert guaranteed.is_guaranteed

    not_guaranteed = prove_deck_availability(
        card_ids=(678,),
        owner=0,
        own_deck_count=30,
        known_outside_deck_refs=outside,
        known_prized_refs=(),
        unknown_prize_count=3,
        required_count=1,
    )
    assert not_guaranteed.lower_bound_in_deck == 0
    assert not not_guaranteed.is_guaranteed
    assert "LOWER_BOUND_BELOW_REQUIRED" in not_guaranteed.rejection_reasons


def test_deck_availability_rejects_wrong_zones_owners_and_inexact_counts():
    proof = prove_deck_availability(
        card_ids=(677,),
        owner=0,
        own_deck_count=True,
        known_outside_deck_refs=(ref(677, 120, zone=AreaType.DECK),),
        known_prized_refs=(ref(677, 121, owner=1, zone=AreaType.HAND),),
        unknown_prize_count=0,
        required_count=1,
    )
    assert not proof.is_guaranteed
    assert {
        "INVALID_DECK_COUNT",
        "INVALID_OUTSIDE_DECK_ZONE",
        "INVALID_PRIZE_ZONE",
        "WRONG_OWNER_REF",
    }.issubset(set(proof.rejection_reasons))


def test_state_availability_collects_known_own_zones_and_rejects_looking_state():
    state = public_state(
        player_view(0, hand_refs=(ref(678, 130),), prize_count=2, deck_count=30),
        player_view(1),
    )
    proof = prove_deck_availability_from_state(state, (678,))
    assert proof.known_outside_deck == 1
    assert proof.unknown_prize_count == 2
    assert proof.lower_bound_in_deck == 1
    assert proof.is_guaranteed

    changed_count = public_state(
        replace(state.own, deck_count=29),
        state.opponent,
    )
    changed_proof = prove_deck_availability_from_state(changed_count, (678,))
    assert changed_proof.deck_state_hash != proof.deck_state_hash

    unstable = public_state(
        state.own,
        state.opponent,
        looking_refs=(ref(678, 131, zone=AreaType.LOOKING),),
    )
    unstable_proof = prove_deck_availability_from_state(unstable, (678,))
    assert not unstable_proof.is_guaranteed
    assert "UNSTABLE_LOOKING_ZONE" in unstable_proof.rejection_reasons

    selecting = public_state(state.own, state.opponent)
    selecting = PublicState(
        **{
            **selecting.__dict__,
            "select_context": 7,
        }
    )
    selecting_proof = prove_deck_availability_from_state(selecting, (678,))
    assert not selecting_proof.is_guaranteed
    assert "UNSTABLE_SELECTION_CONTEXT" in selecting_proof.rejection_reasons


def test_manual_attach_helper_hard_reserves_one_exact_visible_fighting_energy():
    energy = ref(6, 501)
    surplus = ref(6, 502)
    ledger = ResourceLedger((surplus, energy))
    reserved = reserve_manual_attach_energy(ledger, energy)

    reservation = reserved.get_reservation(MANUAL_ATTACH_ENERGY_RESERVATION_ID)
    assert reservation is not None
    assert reservation.kind is ReservationKind.HARD_RESERVED
    assert reservation.refs == (energy,)
    assert reservation.role_card_ids == (6,)
    assert reserved.is_hard_reserved(energy)
    assert not ledger.is_reserved(energy)

    with pytest.raises(ResourceLedgerError, match="already exists"):
        reserve_manual_attach_energy(reserved, surplus)
    with pytest.raises(ResourceLedgerError, match="HAND Fighting Energy"):
        reserve_manual_attach_energy(ledger, ref(677, 503))
    with pytest.raises(ResourceLedgerError, match="HAND Fighting Energy"):
        reserve_manual_attach_energy(ledger, ref(6, 501, zone=AreaType.DISCARD))

    released = reserved.release(MANUAL_ATTACH_ENERGY_RESERVATION_ID)
    assert released.affords((energy,))
    assert released.affords((surplus,))
    assert released.reservations == ()
    assert ledger.reservations == ()
