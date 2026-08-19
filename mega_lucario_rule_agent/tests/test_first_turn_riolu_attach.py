from copy import deepcopy
from dataclasses import replace

import pytest

from mega_lucario_rule_agent.certificates import (
    FIRST_TURN_RIOLU_ATTACH_COVERAGE,
    FIRST_TURN_RIOLU_ATTACH_SCOPE,
    FIRST_TURN_RIOLU_ATTACH_UNRESOLVED,
    CertificateKind,
    ProofSchema,
)
from mega_lucario_rule_agent.features import (
    build_deck_features,
    build_resource_ledger,
)
from mega_lucario_rule_agent.resource_ledger import (
    MANUAL_ATTACH_ENERGY_RESERVATION_ID,
    Reservation,
    ReservationKind,
    ResourceLedger,
    reserve_manual_attach_energy,
)
from mega_lucario_rule_agent.resolver import (
    ResolverTier,
    ResourceCost,
    resolve_proposals,
)
from mega_lucario_rule_agent.routes import (
    enumerate_basic_bench_routes,
    enumerate_first_turn_riolu_attach_routes,
)
from mega_lucario_rule_agent.state_view import (
    AreaType,
    OptionType,
    PublicHistoryTracker,
    build_public_state,
    build_semantic_options,
)
from mega_lucario_rule_agent.tests.test_attack_outcomes import (
    basic_energy_catalog_row,
    card,
    pokemon,
    pokemon_catalog_row,
    registry_for,
)


def _player(active, bench, hand, *, hidden=False):
    return {
        "active": [active],
        "bench": list(bench),
        "benchMax": 5,
        "deckCount": 40,
        "discard": [],
        "prize": [None] * 6,
        "handCount": len(hand),
        "hand": None if hidden else list(hand),
        "poisoned": False,
        "burned": False,
        "asleep": False,
        "paralyzed": False,
        "confused": False,
    }


def _checked_state(observation):
    tracker = PublicHistoryTracker()
    initial = deepcopy(observation)
    initial["logs"] = []
    build_public_state(initial, game_epoch=17, history_tracker=tracker)
    return build_public_state(
        deepcopy(observation),
        game_epoch=17,
        history_tracker=tracker,
    )


def _attach_case(
    *,
    seat=0,
    first_player=None,
    turn=1,
    energy_attached=False,
    active=None,
    bench=(),
    hand_cards=((6, 50),),
    include_attack=False,
    duplicate_attach=False,
    include_basic_play=False,
    registry=None,
):
    first_player = seat if first_player is None else first_player
    active = active or pokemon(677, 10, player=seat, hp=80, max_hp=80)
    own_hand = tuple(card(card_id, serial, seat) for card_id, serial in hand_cards)
    opponent_seat = 1 - seat
    opponent = pokemon(
        900,
        110,
        player=opponent_seat,
        hp=300,
        max_hp=300,
    )
    players = [None, None]
    players[seat] = _player(active, bench, own_hand)
    players[opponent_seat] = _player(opponent, (), (None,) * 5, hidden=True)

    attach_options = []
    targets = ((int(AreaType.ACTIVE), 0, active),) + tuple(
        (int(AreaType.BENCH), index, value)
        for index, value in enumerate(bench)
    )
    for hand_index, hand_card in enumerate(own_hand):
        if hand_card["id"] not in (6, 1159):
            continue
        for target_zone, target_index, _ in targets:
            attach_options.append(
                {
                    "type": int(OptionType.ATTACH),
                    "area": int(AreaType.HAND),
                    "index": hand_index,
                    "inPlayArea": target_zone,
                    "inPlayIndex": target_index,
                }
            )
    if duplicate_attach and attach_options:
        attach_options.append(deepcopy(attach_options[0]))
    options = list(attach_options)
    if include_basic_play:
        options.extend(
            {
                "type": int(OptionType.PLAY),
                "index": index,
            }
            for index, hand_card in enumerate(own_hand)
            if hand_card["id"] in (673, 675, 676, 677)
        )
    if include_attack:
        options.append(
            {"type": int(OptionType.ATTACK), "attackId": 981}
        )
    options.append({"type": int(OptionType.END), "playerIndex": seat})

    observation = {
        "select": {
            "type": 0,
            "context": 0,
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": options,
            "deck": None,
            "contextCard": None,
            "effect": None,
        },
        "logs": [],
        "current": {
            "turn": turn,
            "turnActionCount": 0,
            "yourIndex": seat,
            "firstPlayer": first_player,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": energy_attached,
            "retreated": False,
            "result": -1,
            "stadium": [],
            "looking": None,
            "players": players,
        },
    }
    registry = registry or registry_for(
        (981,),
        extra_rows=(
            pokemon_catalog_row(673, "Makuhita", hp=70),
            pokemon_catalog_row(675, "Lunatone", hp=110),
            pokemon_catalog_row(676, "Solrock", hp=110),
        ),
    )
    state = _checked_state(observation)
    semantic_options = build_semantic_options(observation)
    features = build_deck_features(state, semantic_options, registry)
    ledger = build_resource_ledger(state)
    proposals = enumerate_first_turn_riolu_attach_routes(
        state,
        semantic_options,
        features,
        registry,
    )
    return (
        observation,
        registry,
        state,
        semantic_options,
        features,
        ledger,
        proposals,
    )


@pytest.mark.parametrize("seat", (0, 1))
@pytest.mark.parametrize("target_zone", (AreaType.ACTIVE, AreaType.BENCH))
def test_first_turn_attach_is_exact_partial_proof_for_both_seats_and_zones(
    seat,
    target_zone,
):
    if target_zone == AreaType.ACTIVE:
        active = pokemon(677, 10, player=seat, hp=60, max_hp=80)
        bench = ()
    else:
        active = pokemon(676, 20, player=seat, hp=110, max_hp=110)
        bench = (pokemon(677, 10, player=seat, hp=60, max_hp=80),)
    _, registry, state, options, _, ledger, proposals = _attach_case(
        seat=seat,
        active=active,
        bench=bench,
    )

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.tier == ResolverTier.ROUTE_CRITICAL_MANUAL_ATTACH
    assert proposal.certificate_kind == CertificateKind.FIRST_ATTACK_ACCELERATION
    assert proposal.proof.schema == ProofSchema.FIRST_TURN_RIOLU_ATTACH_V1
    assert proposal.proof.guaranteed_prizes == 0
    assert proposal.proof.fact("coverage") == FIRST_TURN_RIOLU_ATTACH_COVERAGE
    assert proposal.proof.fact("proof_scope") == FIRST_TURN_RIOLU_ATTACH_SCOPE
    assert proposal.proof.fact("full_requirement_compliance") is False
    assert (
        proposal.proof.fact("unresolved_exception_codes")
        == FIRST_TURN_RIOLU_ATTACH_UNRESOLVED
    )
    assert proposal.proof.fact("deficit_before") == 1
    assert proposal.proof.fact("deficit_after") == 0
    assert proposal.reservation_ids == (MANUAL_ATTACH_ENERGY_RESERVATION_ID,)
    assert len(proposal.resource_cost.irreversible_refs) == 1

    reserved = reserve_manual_attach_energy(
        ledger,
        proposal.resource_cost.irreversible_refs[0],
    )
    snapshot = reserved.reservations
    resolution = resolve_proposals(
        state,
        options,
        reserved,
        proposals,
        registry=registry,
    )
    assert resolution.selected == proposal
    assert resolution.bound_action is not None
    assert reserved.reservations == snapshot
    reservation = reserved.get_reservation(MANUAL_ATTACH_ENERGY_RESERVATION_ID)
    assert reservation is not None
    assert reservation.kind == ReservationKind.HARD_RESERVED
    assert reservation.refs == proposal.resource_cost.irreversible_refs


def _selected_target_and_energy(**kwargs):
    *_, proposals = _attach_case(**kwargs)
    assert len(proposals) == 1
    key = proposals[0].action_spec.choices[0]
    return key.target_lineage_serial, key.card_serial


def test_attach_tiebreak_is_active_then_hp_lineage_and_energy_serial():
    active = pokemon(677, 90, hp=5, max_hp=80)
    bench = (
        pokemon(677, 30, hp=70, max_hp=80),
        pokemon(677, 20, hp=70, max_hp=80),
        pokemon(677, 10, hp=40, max_hp=80),
    )
    assert _selected_target_and_energy(
        active=active,
        bench=bench,
        hand_cards=((6, 60), (6, 50)),
    ) == (90, 50)

    non_riolu_active = pokemon(676, 90, hp=110, max_hp=110)
    assert _selected_target_and_energy(
        active=non_riolu_active,
        bench=bench,
        hand_cards=((6, 60), (6, 50)),
    ) == (20, 50)


@pytest.mark.parametrize(
    "overrides",
    (
        {"seat": 0, "first_player": 1},
        {"turn": 2},
        {"energy_attached": True},
        {"include_attack": True},
        {"active": pokemon(676, 10, hp=110, max_hp=110)},
        {
            "active": pokemon(
                677,
                10,
                hp=80,
                max_hp=80,
                energy_cards=((6, 70),),
            )
        },
        {"duplicate_attach": True},
    ),
)
def test_attach_route_rejects_timing_target_energy_and_binding_failures(overrides):
    *_, proposals = _attach_case(**overrides)
    assert proposals == ()


def test_type_eight_hero_cape_is_not_misclassified_as_manual_energy():
    *_, proposals = _attach_case(hand_cards=((1159, 50),))
    assert proposals == ()


def test_malformed_basic_energy_catalog_suppresses_the_route():
    malformed = registry_for(
        (981,),
        extra_rows=(basic_energy_catalog_row(6, energy_type=1),),
    )
    *_, proposals = _attach_case(registry=malformed)
    assert proposals == ()


def test_attach_tier_precedes_normal_basic_placement():
    (
        _,
        registry,
        state,
        options,
        features,
        ledger,
        attach_proposals,
    ) = _attach_case(
        hand_cards=((6, 50), (675, 51)),
        include_basic_play=True,
    )
    basic_proposals = enumerate_basic_bench_routes(
        state,
        options,
        features,
        registry,
    )
    assert attach_proposals
    assert basic_proposals
    attach = attach_proposals[0]
    reserved = reserve_manual_attach_energy(
        ledger,
        attach.resource_cost.irreversible_refs[0],
    )
    resolution = resolve_proposals(
        state,
        options,
        reserved,
        basic_proposals + attach_proposals,
        registry=registry,
    )
    assert resolution.selected == attach


def _rejection_reasons(resolution):
    assert resolution.selected is None
    assert len(resolution.rejections) == 1
    return resolution.rejections[0].reasons


def test_resolver_requires_exact_hard_reservation_and_exact_cost():
    _, registry, state, options, _, ledger, proposals = _attach_case(
        hand_cards=((6, 50), (6, 60)),
    )
    proposal = proposals[0]
    source = proposal.resource_cost.irreversible_refs[0]
    other = next(
        ref_value
        for ref_value in ledger.visible_refs
        if ref_value.card_id == 6 and ref_value != source
    )

    missing = resolve_proposals(
        state,
        options,
        ledger,
        proposals,
        registry=registry,
    )
    assert "RIOLU_ATTACH_RESERVATION_MISSING" in _rejection_reasons(missing)

    wrong_kind = ResourceLedger(
        ledger.visible_refs,
        (
            Reservation(
                MANUAL_ATTACH_ENERGY_RESERVATION_ID,
                ReservationKind.CURRENT_ROUTE,
                "test wrong kind",
                (source,),
            ),
        ),
    )
    wrong_kind_result = resolve_proposals(
        state,
        options,
        wrong_kind,
        proposals,
        registry=registry,
    )
    assert "RIOLU_ATTACH_RESERVATION_NOT_HARD" in _rejection_reasons(
        wrong_kind_result
    )

    role_reservation = ResourceLedger(
        ledger.visible_refs,
        (
            Reservation(
                reservation_id=MANUAL_ATTACH_ENERGY_RESERVATION_ID,
                kind=ReservationKind.HARD_RESERVED,
                reason="test role minimum is not exact",
                refs=(),
                role_card_ids=(6,),
                required_count=1,
                allowed_zones=(int(AreaType.HAND),),
            ),
        ),
    )
    role_result = resolve_proposals(
        state,
        options,
        role_reservation,
        proposals,
        registry=registry,
    )
    assert "RIOLU_ATTACH_RESERVATION_REF_MISMATCH" in _rejection_reasons(
        role_result
    )

    wrong_ref = reserve_manual_attach_energy(ledger, other)
    wrong_ref_result = resolve_proposals(
        state,
        options,
        wrong_ref,
        proposals,
        registry=registry,
    )
    assert "RIOLU_ATTACH_RESERVATION_REF_MISMATCH" in _rejection_reasons(
        wrong_ref_result
    )

    correct = reserve_manual_attach_energy(ledger, source)
    forged_cost = replace(proposal, resource_cost=ResourceCost((other,)))
    cost_result = resolve_proposals(
        state,
        options,
        correct,
        (forged_cost,),
        registry=registry,
    )
    assert "RIOLU_ATTACH_COST_MISMATCH" in _rejection_reasons(cost_result)

    forged_id = replace(proposal, reservation_ids=("OTHER_RESERVATION",))
    id_result = resolve_proposals(
        state,
        options,
        correct,
        (forged_id,),
        registry=registry,
    )
    assert "RIOLU_ATTACH_RESERVATION_ID_MISMATCH" in _rejection_reasons(id_result)


def test_stale_state_and_option_multiset_are_rejected():
    observation, registry, _, _, features, ledger, proposals = _attach_case()
    proposal = proposals[0]
    reserved = reserve_manual_attach_energy(
        ledger,
        proposal.resource_cost.irreversible_refs[0],
    )
    changed = deepcopy(observation)
    changed["current"]["energyAttached"] = True
    changed_state = _checked_state(changed)
    changed_options = build_semantic_options(changed)
    stale_result = resolve_proposals(
        changed_state,
        changed_options,
        reserved,
        proposals,
        registry=registry,
    )
    reasons = _rejection_reasons(stale_result)
    assert "PROOF_STATE_STALE" in reasons

    duplicate = deepcopy(observation)
    duplicate["select"]["option"].insert(
        0,
        deepcopy(duplicate["select"]["option"][0]),
    )
    duplicate_state = _checked_state(duplicate)
    duplicate_options = build_semantic_options(duplicate)
    assert enumerate_first_turn_riolu_attach_routes(
        duplicate_state,
        duplicate_options,
        features,
        registry,
    ) == ()
