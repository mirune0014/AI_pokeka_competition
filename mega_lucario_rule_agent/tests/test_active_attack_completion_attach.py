from copy import deepcopy
from dataclasses import replace

import pytest

import mega_lucario_rule_agent.attack_outcomes as attack_outcomes_module
import mega_lucario_rule_agent.public_effects as public_effects_module
from mega_lucario_rule_agent.attack_outcomes import build_attack_outcome_table
from mega_lucario_rule_agent.public_effects import EffectCardProfile
from mega_lucario_rule_agent.certificates import (
    ACTIVE_ATTACK_COMPLETION_COVERAGE,
    ACTIVE_ATTACK_COMPLETION_RULE_ID,
    CertificateKind,
    ProofSchema,
)
from mega_lucario_rule_agent.features import build_deck_features, build_resource_ledger
from mega_lucario_rule_agent.main import AgentRuntime
from mega_lucario_rule_agent.resource_ledger import (
    ACTIVE_ATTACK_COMPLETION_RESERVATION_ID,
    ReservationKind,
    reserve_active_attack_completion_energy,
    reserve_manual_attach_energy,
)
from mega_lucario_rule_agent.resolver import (
    ResolverTier,
    ResourceCost,
    resolve_proposals,
)
from mega_lucario_rule_agent.routes import (
    enumerate_active_attack_completion_routes,
    enumerate_attack_routes,
    enumerate_poke_pad_core_search_routes,
)
from mega_lucario_rule_agent.state_view import (
    ActionSpec,
    AreaType,
    LogType,
    OptionType,
    PublicHistoryTracker,
    build_public_state,
    build_semantic_options,
)
from mega_lucario_rule_agent.tests.test_attack_outcomes import (
    card,
    pokemon,
    pokemon_catalog_row,
    registry_for,
)
from mega_lucario_rule_agent.tests.test_poke_pad_core_search import poke_pad_row

_TEST_CATALOG_PATCH = None
_TRAINER_PROFILE_ROWS = (
    (
        1140,
        "iron defender",
        1,
        (
            (
                "iron defender",
                "98d6389529ef834dccc37410e87f7d56c9f18a698d301b7a9e23aa6232b06323",
            ),
        ),
    ),
    (
        1228,
        "acerola's mischief",
        3,
        (
            (
                "acerola's mischief",
                "5b5b8f38efb7b81d3d9646a2787059ee5ec562f0fc17582686630ca6c04a6b55",
            ),
        ),
    ),
)


@pytest.fixture(autouse=True)
def _synthetic_catalog_gate(monkeypatch):
    """Bind synthetic registries to the production trainer witness in tests only."""

    global _TEST_CATALOG_PATCH
    _TEST_CATALOG_PATCH = monkeypatch
    yield
    _TEST_CATALOG_PATCH = None


def _add_audited_trainer_profiles(registry, *, tamper=False, patch_catalog=True):
    profiles = []
    for card_id, card_name, card_type, signatures in _TRAINER_PROFILE_ROWS:
        profiles.append(
            EffectCardProfile(
                card_id=card_id,
                card_name=card_name + " changed"
                if tamper and card_id == 1140
                else card_name,
                card_type=card_type,
                energy_type=0,
                skill_signatures=signatures,
                registered_skill_effect_ids=(),
                unregistered_skill_signatures=signatures,
                issuer_token=public_effects_module._EFFECT_CARD_PROFILE_ISSUER_TOKEN,
            )
        )
    retained = tuple(
        profile
        for profile in registry.effect_profiles
        if profile.card_id not in (1140, 1228)
    )
    object.__setattr__(
        registry,
        "effect_profiles",
        tuple(sorted(retained + tuple(profiles), key=lambda value: value.card_id)),
    )
    if patch_catalog:
        assert _TEST_CATALOG_PATCH is not None
        _TEST_CATALOG_PATCH.setattr(
            attack_outcomes_module,
            "ACTIVE_ATTACK_COMPLETION_EXPECTED_CATALOG_SHA256",
            registry.catalog_sha256,
        )
    return registry


ATTACK_BY_CARD = {673: 976, 674: 978, 675: 979, 676: 980, 677: 981, 678: 982}
HP_BY_CARD = {673: 70, 674: 140, 675: 110, 676: 110, 677: 80, 678: 340}


def _player(active, bench, hand, *, discard=(), hidden=False, status=None):
    status = status or {}
    return {
        "active": [active],
        "bench": list(bench),
        "benchMax": 5,
        "deckCount": 40,
        "discard": list(discard),
        "prize": [None] * 6,
        "handCount": len(hand),
        "hand": None if hidden else list(hand),
        "poisoned": bool(status.get("poisoned", False)),
        "burned": bool(status.get("burned", False)),
        "asleep": bool(status.get("asleep", False)),
        "paralyzed": bool(status.get("paralyzed", False)),
        "confused": bool(status.get("confused", False)),
    }


def _checked_state(observation, *, previous_attack=None, epoch=41):
    tracker = PublicHistoryTracker()
    initial = deepcopy(observation)
    initial["current"]["turn"] = max(1, observation["current"]["turn"] - 2)
    initial["current"]["turnActionCount"] = 0
    initial["logs"] = []
    if previous_attack is not None:
        active = initial["current"]["players"][initial["current"]["yourIndex"]][
            "active"
        ][0]
        initial["logs"].append(
            {
                "type": int(LogType.ATTACK),
                "playerIndex": initial["current"]["yourIndex"],
                "cardId": active["id"],
                "serial": active["serial"],
                "attackId": previous_attack,
            }
        )
    build_public_state(initial, game_epoch=epoch, history_tracker=tracker)
    current = deepcopy(observation)
    current["logs"] = []
    return build_public_state(current, game_epoch=epoch, history_tracker=tracker)


def _registry(
    active_card_id,
    *,
    attack_ids=None,
    include_poke_pad=False,
    malformed_energy=False,
    target_energy_type=6,
):
    attack_ids = tuple(attack_ids or (ATTACK_BY_CARD[active_card_id],))
    extras = []
    if active_card_id != 675:
        extras.append(pokemon_catalog_row(675, "Lunatone", hp=110))
    if active_card_id != 676:
        extras.append(pokemon_catalog_row(676, "Solrock", hp=110))
    if active_card_id != 677:
        extras.append(pokemon_catalog_row(677, "Riolu", hp=80))
    if include_poke_pad:
        extras.append(poke_pad_row())
    target_row = pokemon_catalog_row(
        900, "Test Target", hp=300, energy_type=target_energy_type
    )
    registry = registry_for(attack_ids, target_row=target_row, extra_rows=tuple(extras))
    if not malformed_energy:
        return registry
    from mega_lucario_rule_agent.tests.test_attack_outcomes import (
        basic_energy_catalog_row,
    )

    return registry_for(
        attack_ids,
        target_row=target_row,
        extra_rows=tuple(extras) + (basic_energy_catalog_row(6, energy_type=1),),
    )


def _case(
    active_card_id,
    *,
    seat=0,
    first_player=None,
    turn=2,
    active_energy_serials=(),
    hand_energy_serials=(50,),
    active_remaining_hp=None,
    bench_card_ids=(),
    manual_used=False,
    discard_energy_serials=(),
    status=None,
    include_existing_attack=False,
    duplicate_attach=False,
    include_poke_pad=False,
    previous_attack=None,
    malformed_energy=False,
    target_energy_type=6,
    opponent_discard_card_ids=(),
    trainer_profile_tamper=False,
    patch_catalog_gate=True,
    registry_override=None,
):
    first_player = 1 - seat if first_player is None else first_player
    active = pokemon(
        active_card_id,
        10,
        player=seat,
        hp=(
            HP_BY_CARD[active_card_id]
            if active_remaining_hp is None
            else active_remaining_hp
        ),
        max_hp=HP_BY_CARD[active_card_id],
        energy_cards=tuple((6, serial) for serial in active_energy_serials),
    )
    bench = tuple(
        pokemon(
            card_id,
            20 + index,
            player=seat,
            hp=HP_BY_CARD[card_id],
            max_hp=HP_BY_CARD[card_id],
        )
        for index, card_id in enumerate(bench_card_ids)
    )
    hand = [card(6, serial, seat) for serial in hand_energy_serials]
    discard = [card(6, serial, seat) for serial in discard_energy_serials]
    if include_poke_pad:
        hand.append(card(1152, 90, seat))
    opponent_seat = 1 - seat
    opponent = pokemon(900, 110, player=opponent_seat, hp=300, max_hp=300)
    opponent_discard = tuple(
        card(card_id, 200 + index, opponent_seat)
        for index, card_id in enumerate(opponent_discard_card_ids)
    )
    players = [None, None]
    players[seat] = _player(active, bench, hand, discard=discard, status=status)
    players[opponent_seat] = _player(
        opponent, (), (None,) * 5, discard=opponent_discard, hidden=True
    )

    options = []
    for hand_index, hand_card in enumerate(hand):
        if hand_card["id"] != 6:
            continue
        options.append(
            {
                "type": int(OptionType.ATTACH),
                "area": int(AreaType.HAND),
                "index": hand_index,
                "inPlayArea": int(AreaType.ACTIVE),
                "inPlayIndex": 0,
            }
        )
        for bench_index, _ in enumerate(bench):
            options.append(
                {
                    "type": int(OptionType.ATTACH),
                    "area": int(AreaType.HAND),
                    "index": hand_index,
                    "inPlayArea": int(AreaType.BENCH),
                    "inPlayIndex": bench_index,
                }
            )
    if duplicate_attach and options:
        options.insert(0, deepcopy(options[0]))
    if include_poke_pad:
        options.append(
            {
                "type": int(OptionType.PLAY),
                "index": len(hand) - 1,
            }
        )
    if include_existing_attack:
        options.append(
            {
                "type": int(OptionType.ATTACK),
                "attackId": ATTACK_BY_CARD[active_card_id],
            }
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
            "turnActionCount": 2,
            "yourIndex": seat,
            "firstPlayer": first_player,
            "supporterPlayed": False,
            "stadiumPlayed": False,
            "energyAttached": manual_used,
            "retreated": False,
            "result": -1,
            "stadium": [],
            "looking": None,
            "players": players,
        },
    }
    registry = (
        registry_override
        if registry_override is not None
        else _registry(
            active_card_id,
            include_poke_pad=include_poke_pad,
            malformed_energy=malformed_energy,
            target_energy_type=target_energy_type,
        )
    )
    registry = _add_audited_trainer_profiles(
        registry,
        tamper=trainer_profile_tamper,
        patch_catalog=patch_catalog_gate,
    )
    state = _checked_state(observation, previous_attack=previous_attack)
    semantic_options = build_semantic_options(observation)
    ledger = build_resource_ledger(state)
    proposals = enumerate_active_attack_completion_routes(
        state,
        semantic_options,
        registry,
    )
    return observation, registry, state, semantic_options, ledger, proposals


def _selected_case(active_card_id, **kwargs):
    values = _case(active_card_id, **kwargs)
    proposal = values[-1][0]
    reserved = reserve_active_attack_completion_energy(
        values[-2],
        proposal.resource_cost.irreversible_refs[0],
    )
    resolution = resolve_proposals(
        values[2],
        values[3],
        reserved,
        (proposal,),
        registry=values[1],
    )
    assert resolution.selected == proposal
    return values, proposal, reserved, resolution


def _post_attach_attack_route(values, proposal):
    observation, registry, _, _, _, _ = values
    post = deepcopy(observation)
    seat = post["current"]["yourIndex"]
    own = post["current"]["players"][seat]
    energy_serial = proposal.proof.fact("energy_serial")
    own["hand"] = [value for value in own["hand"] if value["serial"] != energy_serial]
    own["handCount"] = len(own["hand"])
    own["active"][0]["energies"].append(6)
    own["active"][0]["energyCards"].append(card(6, energy_serial, seat))
    post["current"]["energyAttached"] = True
    post["current"]["turnActionCount"] += 1
    post["select"]["option"] = [
        {
            "type": int(OptionType.ATTACK),
            "attackId": proposal.proof.fact("chosen_attack_id"),
        },
        {"type": int(OptionType.END), "playerIndex": seat},
    ]
    post_state = _checked_state(post, epoch=43)
    post_options = build_semantic_options(post)
    table = build_attack_outcome_table(post_state, post_options, registry)
    attack_routes = enumerate_attack_routes(post_state, post_options, table, registry)
    resolution = resolve_proposals(
        post_state,
        post_options,
        build_resource_ledger(post_state),
        attack_routes,
        registry=registry,
    )
    assert resolution.selected is not None
    assert resolution.selected.proof.schema == ProofSchema.ATTACK_OUTCOME_V1
    assert resolution.selected.action_spec.choices[0].attack_id == proposal.proof.fact(
        "chosen_attack_id"
    )
    assert resolution.bound_action == (0,)


def test_makuhita_attach_then_corkscrew_punch():
    values, proposal, _, _ = _selected_case(673)
    assert proposal.proof.fact("chosen_attack_id") == 976
    assert proposal.proof.fact("candidate_attack_ids") == (976,)
    assert proposal.proof.fact("deficit_before") == 1
    assert proposal.proof.fact("deficit_after") == 0
    _post_attach_attack_route(values, proposal)


def test_solrock_requires_lunatone_bench_for_positive_cosmic_beam():
    _, proposal, _, _ = _selected_case(676, bench_card_ids=(675,))
    assert proposal.proof.fact("chosen_attack_id") == 980
    assert proposal.proof.fact("chosen_final_damage") == 70
    assert _case(676)[-1] == ()


def test_riolu_and_lunatone_exact_energy_gaps_are_fail_closed():
    assert _case(677)[-1][0].proof.fact("chosen_attack_id") == 981
    assert (
        _case(675, active_energy_serials=(60,))[-1][0].proof.fact("chosen_attack_id")
        == 979
    )
    assert _case(675)[-1] == ()


def test_mega_lucario_one_energy_deficit_selects_exact_aura_jab():
    values, proposal, _, _ = _selected_case(678)
    assert proposal.proof.fact("chosen_attack_id") == 982
    assert proposal.proof.fact("chosen_final_damage") == 130
    _post_attach_attack_route(values, proposal)


@pytest.mark.parametrize(
    "kwargs",
    (
        {"manual_used": True},
        {"turn": 1},
        {"status": {"asleep": True}},
        {"status": {"confused": True}},
        {"malformed_energy": True},
        {"include_existing_attack": True},
    ),
)
def test_timing_status_unsupported_and_existing_attack_do_not_propose(kwargs):
    assert _case(673, **kwargs)[-1] == ()


def _reasons(state, options, ledger, proposal, registry):
    resolution = resolve_proposals(
        state,
        options,
        ledger,
        (proposal,),
        registry=registry,
    )
    assert resolution.selected is None
    return resolution.rejections[0].reasons


def test_canonical_energy_duplicate_option_and_resolver_tamper_checks():
    values = _case(673, hand_energy_serials=(60, 50), bench_card_ids=(675,))
    observation, registry, state, options, ledger, proposals = values
    proposal = proposals[0]
    source = proposal.resource_cost.irreversible_refs[0]
    other = next(
        ref for ref in ledger.visible_refs if ref.card_id == 6 and ref != source
    )
    assert source.serial == 50
    assert _case(673, duplicate_attach=True)[-1] == ()
    assert "ACTIVE_ATTACK_COMPLETION_RESERVATION_MISSING" in _reasons(
        state, options, ledger, proposal, registry
    )
    foreign = reserve_manual_attach_energy(ledger, source)
    assert "ACTIVE_ATTACK_COMPLETION_FOREIGN_RESERVATION" in _reasons(
        state, options, foreign, proposal, registry
    )
    wrong = reserve_active_attack_completion_energy(ledger, other)
    assert "ACTIVE_ATTACK_COMPLETION_RESERVATION_REF_MISMATCH" in _reasons(
        state, options, wrong, proposal, registry
    )
    correct = reserve_active_attack_completion_energy(ledger, source)
    tampered_cost = replace(proposal, resource_cost=ResourceCost((other,)))
    assert "ACTIVE_ATTACK_COMPLETION_COST_MISMATCH" in _reasons(
        state, options, correct, tampered_cost, registry
    )
    bench_key = next(
        option.key
        for option in options
        if option.key.target_zone == int(AreaType.BENCH)
        and option.key.card_serial == source.serial
    )
    wrong_target = replace(proposal, action_spec=ActionSpec.single(bench_key))
    wrong_target_reasons = _reasons(state, options, correct, wrong_target, registry)
    assert "PROOF_ACTION_MISMATCH" in wrong_target_reasons
    changed = deepcopy(observation)
    changed["current"]["energyAttached"] = True
    changed_state = _checked_state(changed)
    changed_options = build_semantic_options(changed)
    assert "PROOF_STATE_STALE" in _reasons(
        changed_state, changed_options, correct, proposal, registry
    )


def test_tier_nine_beats_poke_pad_and_has_no_transaction_owner():
    values = _case(673, include_poke_pad=True)
    observation, registry, state, options, ledger, attach_routes = values
    attach = attach_routes[0]
    features = build_deck_features(state, options, registry)
    table = build_attack_outcome_table(state, options, registry)
    poke_routes = enumerate_poke_pad_core_search_routes(
        state,
        options,
        features,
        table,
        registry,
    )
    assert poke_routes
    reserved = reserve_active_attack_completion_energy(
        ledger,
        attach.resource_cost.irreversible_refs[0],
    )
    resolution = resolve_proposals(
        state,
        options,
        reserved,
        attach_routes + poke_routes,
        registry=registry,
    )
    assert resolution.selected == attach
    assert attach.tier == ResolverTier.ATTACK_COMPLETION
    assert attach.tier < ResolverTier.ROUTE_CRITICAL_SEARCH
    assert attach.certificate_kind == CertificateKind.ATTACK_COMPLETION
    assert attach.proof.schema == ProofSchema.ACTIVE_POST_ATTACH_ATTACK_COMPLETION_V1
    assert attach.transaction_plan is None
    _post_attach_attack_route(values, attach)


@pytest.mark.parametrize("seat", (0, 1))
def test_both_seats_are_deterministic_and_use_schema_specific_reservation(seat):
    first = _case(673, seat=seat)
    second = _case(673, seat=seat)
    left = first[-1][0]
    right = second[-1][0]
    assert left.action_spec == right.action_spec
    assert left.proof.facts == right.proof.facts
    assert left.reservation_ids == (ACTIVE_ATTACK_COMPLETION_RESERVATION_ID,)
    assert left.transaction_plan is None
    reserved = reserve_active_attack_completion_energy(
        first[-2],
        left.resource_cost.irreversible_refs[0],
    )
    reservation = reserved.get_reservation(ACTIVE_ATTACK_COMPLETION_RESERVATION_ID)
    assert reservation is not None
    assert reservation.kind == ReservationKind.HARD_RESERVED
    assert reservation.refs == left.resource_cost.irreversible_refs
    assert all(
        value.reservation_id == ACTIVE_ATTACK_COMPLETION_RESERVATION_ID
        for value in reserved.bound_reservations
    )


def test_going_second_turn_one_uses_global_turn_two():
    assert _case(673, seat=0, first_player=0, turn=1)[-1] == ()
    _, proposal, _, resolution = _selected_case(
        673,
        seat=1,
        first_player=0,
        turn=2,
    )
    assert proposal.proof.fact("chosen_attack_id") == 976
    assert resolution.bound_action is not None


def test_wrong_actor_turn_parity_is_rejected():
    assert _case(673, seat=1, first_player=0, turn=1)[-1] == ()
    assert _case(673, seat=0, first_player=0, turn=2)[-1] == ()


@pytest.mark.parametrize(
    ("active_card_id", "kwargs"),
    (
        (673, {}),
        (674, {"active_energy_serials": (60, 61)}),
        (675, {"active_energy_serials": (60,)}),
        (676, {"bench_card_ids": (675,)}),
        (677, {}),
        (678, {}),
    ),
)
def test_every_admitted_path_has_one_runtime_equivalent_attack_candidate(
    active_card_id,
    kwargs,
):
    proposal = _case(active_card_id, **kwargs)[-1][0]
    candidate_set = proposal.proof.fact("candidate_set")
    assert len(candidate_set) == 1
    assert candidate_set[0][0] == proposal.proof.fact("chosen_attack_id")


def test_agent_runtime_main_wiring_attaches_then_attacks_without_transaction_owner():
    values = _case(673, include_poke_pad=True)
    observation, registry = values[:2]
    seat = observation["current"]["yourIndex"]
    runtime = AgentRuntime(registry=registry)

    prelude = deepcopy(observation)
    prelude["current"]["turn"] = 1
    prelude["current"]["turnActionCount"] = 0
    prelude_own = prelude["current"]["players"][seat]
    prelude_own["hand"] = []
    prelude_own["handCount"] = 0
    prelude["select"]["option"] = [{"type": int(OptionType.END), "playerIndex": seat}]
    assert runtime.act(prelude) == [0]
    assert runtime.transactions.owner is None

    attach_action = runtime.act(observation)
    assert len(attach_action) == 1
    attach_raw = observation["select"]["option"][attach_action[0]]
    assert attach_raw["type"] == int(OptionType.ATTACH)
    assert attach_raw["inPlayArea"] == int(AreaType.ACTIVE)
    assert runtime.transactions.owner is None
    assert not runtime.runtime_fault_latched

    post = deepcopy(observation)
    own = post["current"]["players"][seat]
    energy = next(value for value in own["hand"] if value["id"] == 6)
    own["hand"] = [value for value in own["hand"] if value is not energy]
    own["handCount"] = len(own["hand"])
    own["active"][0]["energies"].append(6)
    own["active"][0]["energyCards"].append(card(6, energy["serial"], seat))
    post["current"]["energyAttached"] = True
    post["current"]["turnActionCount"] += 1
    post["select"]["option"] = [
        {"type": int(OptionType.ATTACK), "attackId": 976},
        {"type": int(OptionType.END), "playerIndex": seat},
    ]
    attack_action = runtime.act(post)
    assert len(attack_action) == 1
    attack_raw = post["select"]["option"][attack_action[0]]
    assert attack_raw["type"] == int(OptionType.ATTACK)
    assert attack_raw["attackId"] == 976
    assert runtime.transactions.owner is None
    assert not runtime.runtime_fault_latched


def test_scope_facts_bind_global_two_empty_pre_and_singleton_post():
    _, proposal, _, _ = _selected_case(673)
    assert proposal.rule_id == ACTIVE_ATTACK_COMPLETION_RULE_ID
    assert proposal.proof.fact("rule_id") == ACTIVE_ATTACK_COMPLETION_RULE_ID
    assert proposal.proof.fact("coverage") == ACTIVE_ATTACK_COMPLETION_COVERAGE
    assert proposal.proof.fact("full_requirement_compliance") is False
    assert proposal.proof.fact("global_turn") == 2
    assert proposal.proof.fact("own_turn_number") == 1
    assert proposal.proof.fact("pre_payable") == ()
    assert proposal.proof.fact("post_payable") == (976,)
    assert proposal.proof.fact("post_table_and_outcome_fully_exact") is True
    assert proposal.proof.fact("target_energy_type") == 6
    assert proposal.proof.fact("target_energy_type_exact") is True


@pytest.mark.parametrize(("seat", "first_player"), ((0, 1), (1, 0)))
def test_global_two_succeeds_for_both_second_player_seats(seat, first_player):
    _, proposal, _, resolution = _selected_case(
        673, seat=seat, first_player=first_player, turn=2
    )
    assert proposal.proof.fact("global_turn") == 2
    assert resolution.bound_action is not None


@pytest.mark.parametrize("turn", (1, 3, 4))
def test_only_global_turn_two_is_admitted(turn):
    assert _case(673, turn=turn)[-1] == ()


def test_pre_attach_payable_attack_set_must_be_empty():
    assert _case(673, active_energy_serials=(60,))[-1] == ()


def test_nonmetal_target_with_public_iron_defender_discard_is_still_admitted():
    _, proposal, _, _ = _selected_case(
        673,
        target_energy_type=6,
        opponent_discard_card_ids=(1140,),
    )
    assert proposal.proof.fact("target_energy_type") == 6


@pytest.mark.parametrize("opponent_discard_card_ids", ((), (1140,)))
def test_metal_target_is_rejected_with_or_without_iron_defender_discard(
    opponent_discard_card_ids,
):
    assert (
        _case(
            673,
            target_energy_type=8,
            opponent_discard_card_ids=opponent_discard_card_ids,
        )[-1]
        == ()
    )


def test_unknown_target_type_is_rejected():
    assert _case(673, target_energy_type=0)[-1] == ()


def test_catalog_and_persistent_trainer_audit_mismatches_fail_closed():
    assert _case(673, patch_catalog_gate=False)[-1] == ()
    assert _case(673, trainer_profile_tamper=True)[-1] == ()


def test_registry_digest_and_catalog_binding_are_recomputed_by_resolver():
    values, proposal, _, _ = _selected_case(673)
    second_registry = _add_audited_trainer_profiles(
        _registry(673, include_poke_pad=True)
    )
    reserved = reserve_active_attack_completion_energy(
        values[4], proposal.resource_cost.irreversible_refs[0]
    )
    reasons = _reasons(values[2], values[3], reserved, proposal, second_registry)
    assert "PROOF_REGISTRY_STALE" in reasons
    assert "ACTIVE_ATTACK_COMPLETION_REGISTRY_AUDIT_MISMATCH" in reasons


def test_hariyama_self_ko_loss_rejected_but_safe_wild_press_matches_direct_route():
    assert (
        _case(
            674,
            active_energy_serials=(60, 61),
            active_remaining_hp=70,
        )[-1]
        == ()
    )
    values, proposal, _, _ = _selected_case(
        674,
        active_energy_serials=(60, 61),
    )
    assert proposal.proof.fact("chosen_attack_id") == 978
    assert proposal.proof.fact("chosen_future_lock_cost") == 0
    _post_attach_attack_route(values, proposal)


def test_aura_jab_selection_callback_is_rejected_but_exact_variant_matches_direct():
    assert (
        _case(
            678,
            bench_card_ids=(677,),
            discard_energy_serials=(70,),
        )[-1]
        == ()
    )
    values, proposal, _, _ = _selected_case(678)
    assert proposal.proof.fact("chosen_attack_id") == 982
    _post_attach_attack_route(values, proposal)


def _patch_confront_as_one_energy(monkeypatch, *, printed_damage):
    first = attack_outcomes_module.ATTACK_META_BY_ID[976]
    second = replace(
        attack_outcomes_module.ATTACK_META_BY_ID[977],
        energy_cost=first.energy_cost,
        printed_damage=printed_damage,
    )
    monkeypatch.setitem(attack_outcomes_module.ATTACK_META_BY_ID, 977, second)
    bindings = tuple(
        replace(
            binding,
            printed_damage=printed_damage,
            energy_cost=(6,),
        )
        if binding.entry_id == 977
        else binding
        for binding in attack_outcomes_module.EFFECT_BINDINGS
    )
    monkeypatch.setattr(attack_outcomes_module, "EFFECT_BINDINGS", bindings)


@pytest.mark.parametrize("second_damage", (0, 30))
def test_multiple_post_payable_rejected_before_positive_filter(
    monkeypatch, second_damage
):
    registry = _registry(673, attack_ids=(976, 977))
    _patch_confront_as_one_energy(monkeypatch, printed_damage=second_damage)
    assert registry.profile(673).attack_ids == (976, 977)
    assert _case(673, registry_override=registry)[-1] == ()


def test_stale_source_serial_proof_is_rejected():
    values, proposal, _, _ = _selected_case(673)
    changed = deepcopy(values[0])
    changed["current"]["players"][0]["hand"][0]["serial"] = 51
    state = _checked_state(changed)
    options = build_semantic_options(changed)
    ledger = build_resource_ledger(state)
    source = next(ref for ref in ledger.visible_refs if ref.card_id == 6)
    reserved = reserve_active_attack_completion_energy(ledger, source)
    reasons = _reasons(state, options, reserved, proposal, values[1])
    assert "PROOF_STATE_STALE" in reasons
    assert "ACTIVE_ATTACK_COMPLETION_SOURCE_REF_INVALID" in reasons
