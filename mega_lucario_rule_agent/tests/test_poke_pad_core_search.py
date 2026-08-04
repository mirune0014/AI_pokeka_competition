from copy import deepcopy
from dataclasses import replace

import pytest

from mega_lucario_rule_agent.attack_outcomes import build_attack_outcome_table
from mega_lucario_rule_agent.certificates import (
    POKE_PAD_CORE_COVERAGE_SCOPE,
    POKE_PAD_CORE_UNRESOLVED_PRIORITIES,
    ProofSchema,
    poke_pad_core_eligible_classes,
    poke_pad_core_formation_proof,
)
from mega_lucario_rule_agent.main import AgentRuntime
from mega_lucario_rule_agent.features import (
    build_deck_features,
    build_resource_ledger,
)
from mega_lucario_rule_agent.resolver import ResourceCost, resolve_proposals
from mega_lucario_rule_agent.resource_ledger import ReservationKind
from mega_lucario_rule_agent.routes import enumerate_poke_pad_core_search_routes
from mega_lucario_rule_agent.state_view import (
    AreaType,
    LogType,
    OptionType,
    PhysicalRef,
    SelectContext,
    SelectType,
    SemanticOption,
    SemanticOptionKey,
    build_semantic_options,
)
from mega_lucario_rule_agent.transactions import (
    ResumeStatus,
    StartStatus,
    TransactionStore,
)
from mega_lucario_rule_agent.tests.test_attack_outcomes import (
    card,
    checked_state,
    observation,
    pokemon,
    pokemon_catalog_row,
    registry_for,
)
from mega_lucario_rule_agent.tests.test_transaction_terminal_receipts import (
    _event,
)


POKE_PAD_TEXT = (
    "Search your deck for a Pokemon that doesn't have a Rule Box, reveal it, "
    "and put it into your hand. Then, shuffle your deck. (Pokemon {ex}, "
    "Pokemon {V}, etc. have Rule Boxes.)"
)


def poke_pad_row(*, text=POKE_PAD_TEXT):
    return {
        "cardId": 1152,
        "cardType": 1,
        "name": "Poke Pad",
        "hp": 0,
        "energyType": 0,
        "weakness": None,
        "resistance": None,
        "basic": False,
        "stage1": False,
        "stage2": False,
        "ex": False,
        "megaEx": False,
        "tera": False,
        "attacks": [],
        "skills": [{"name": "Poke Pad", "text": text}],
    }


def core_rows(*extra_ids):
    rows = [
        pokemon_catalog_row(673, "Makuhita", hp=70),
        pokemon_catalog_row(675, "Lunatone", hp=110),
        pokemon_catalog_row(676, "Solrock", hp=110),
        pokemon_catalog_row(677, "Riolu", hp=80),
    ]
    if 678 in extra_ids:
        rows.append(
            pokemon_catalog_row(
                678,
                "Mega Lucario ex",
                hp=340,
                basic=False,
                stage1=True,
                ex=True,
                mega_ex=True,
            )
        )
    return tuple(rows)


def build_case(
    *,
    attack_ids=(),
    active_id=676,
    bench_ids=(675,),
    hand_cards=((1152, 30),),
    known_prizes=True,
    confused=False,
    item_text=POKE_PAD_TEXT,
    own_discard=(),
):
    active_hp = (
        340
        if active_id == 678
        else 80
        if active_id == 677
        else 70
        if active_id == 673
        else 110
    )
    active = pokemon(
        active_id,
        10,
        hp=active_hp,
        max_hp=active_hp,
        energy_cards=tuple((6, 50 + index) for index in range(3)) if attack_ids else (),
    )
    bench = tuple(
        pokemon(
            card_id,
            20 + index,
            hp=(70 if card_id == 673 else 80 if card_id == 677 else 110),
            max_hp=(70 if card_id == 673 else 80 if card_id == 677 else 110),
        )
        for index, card_id in enumerate(bench_ids)
    )
    obs = observation(
        attack_ids,
        own_active=active,
        own_bench=bench,
        own_discard=own_discard,
        confused=confused,
    )
    hand = [card(card_id, serial) for card_id, serial in hand_cards]
    obs["current"]["players"][0]["hand"] = hand
    obs["current"]["players"][0]["handCount"] = len(hand)
    if known_prizes:
        obs["current"]["players"][0]["prize"] = [
            card(6, 900 + index) for index in range(6)
        ]
    obs["select"]["option"] = (
        [
            {"type": int(OptionType.ATTACK), "attackId": attack_id}
            for attack_id in attack_ids
        ]
        + [
            {"type": int(OptionType.PLAY), "index": index}
            for index, hand_card in enumerate(hand)
            if hand_card["id"] == 1152
        ]
        + [{"type": int(OptionType.END), "playerIndex": 0}]
    )
    extras = list(core_rows(678 if active_id == 678 and not attack_ids else -1))
    extras.append(poke_pad_row(text=item_text))
    registry = registry_for(attack_ids, extra_rows=tuple(extras))
    state = checked_state(obs)
    options = build_semantic_options(obs)
    features = build_deck_features(state, options, registry)
    attack_table = build_attack_outcome_table(state, options, registry)
    ledger = build_resource_ledger(state)
    proposals = enumerate_poke_pad_core_search_routes(
        state,
        options,
        features,
        attack_table,
        registry,
    )
    return obs, registry, state, options, features, attack_table, ledger, proposals


def rejection_reasons(state, options, ledger, proposal, registry):
    resolution = resolve_proposals(
        state,
        options,
        ledger,
        (proposal,),
        registry=registry,
    )
    assert resolution.selected is None
    return resolution.rejections[0].reasons


def test_empty_exact_attack_surface_issues_closed_core_search_proof():
    _, registry, state, options, features, table, ledger, proposals = build_case()

    assert table.rows == ()
    assert table.build_unknown_reasons == ("NO_ATTACK_OPTION",)
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.rule_id == "R_SEARCH_POKE_PAD_CORE_FORMATION_V1"
    assert proposal.proof.schema == ProofSchema.POKE_PAD_CORE_FORMATION_V1
    assert proposal.proof.fact("eligible_classes") == ((677,),)
    assert proposal.proof.fact("coverage_scope") == POKE_PAD_CORE_COVERAGE_SCOPE
    assert not proposal.proof.fact("full_requirement_covered")
    assert (
        proposal.proof.fact("unresolved_higher_search_priorities")
        == POKE_PAD_CORE_UNRESOLVED_PRIORITIES
    )
    assert proposal.proof.fact("safe_bench_slots_before") == features.safe_bench_slots
    assert proposal.resource_cost.irreversible_refs[0].card_id == 1152
    resolution = resolve_proposals(
        state,
        options,
        ledger,
        proposals,
        registry=registry,
    )
    assert resolution.selected == proposal
    assert resolution.bound_action == (0,)


def test_role_suppression_uses_hand_active_bench_and_riolu_line():
    _, _, riolu_state, _, _, _, _, riolu_proposals = build_case(
        hand_cards=((1152, 30), (677, 31)),
    )
    assert poke_pad_core_eligible_classes(riolu_state) == ()
    assert riolu_proposals == ()

    _, _, hand_state, _, _, _, _, _ = build_case(
        active_id=673,
        bench_ids=(675,),
        hand_cards=((1152, 30), (676, 31)),
    )
    assert poke_pad_core_eligible_classes(hand_state) == ((677,),)

    _, _, play_state, _, _, _, _, _ = build_case(
        active_id=678,
        bench_ids=(675, 677),
    )
    assert poke_pad_core_eligible_classes(play_state) == ((676,),)


def test_lowest_physical_source_is_used_and_safety_gates_fail_closed():
    _, _, _, _, _, _, _, proposals = build_case(
        hand_cards=((1152, 31), (1152, 30)),
    )
    assert len(proposals) == 1
    assert proposals[0].action_spec.choices[0].card_serial == 30
    assert proposals[0].resource_cost.irreversible_refs[0].serial == 30

    _, _, _, _, full_features, _, _, full_proposals = build_case(
        bench_ids=(675, 677, 673, 678),
    )
    assert full_features.safe_bench_slots == 0
    assert full_proposals == ()

    assert build_case(known_prizes=False)[-1] == ()
    assert build_case(item_text="Search for any card.")[-1] == ()


def test_nonexact_and_callback_attack_surfaces_suppress_search():
    _, _, _, _, _, nonexact_table, _, nonexact = build_case(
        attack_ids=(983,),
        active_id=678,
        confused=True,
    )
    assert len(nonexact_table.rows) == 1
    assert not nonexact_table.rows[0].exact
    assert nonexact == ()

    _, _, _, _, _, callback_table, _, callback = build_case(
        attack_ids=(982,),
        active_id=678,
    )
    assert len(callback_table.rows) == 1
    assert callback_table.rows[0].callback is not None
    assert callback == ()


def test_availability_union_tamper_is_rejected_by_proof_issuer():
    _, registry, state, options, features, table, _, proposals = build_case(
        active_id=673,
        bench_ids=(),
    )
    assert len(proposals) == 1
    proposal = proposals[0]
    policy = proposal.transaction_plan.steps[0].deferred_card_choice
    assert policy.ordered_card_id_classes == ((675,), (676,), (677,))
    assert policy.availability_proof.card_ids == (675, 676, 677)
    tampered = replace(policy.availability_proof, card_ids=(675,))

    with pytest.raises(ValueError, match="acceptable union"):
        poke_pad_core_formation_proof(
            state,
            options,
            registry,
            features,
            table,
            tampered,
            proposal.action_spec,
        )


def test_resolver_recomputes_cost_plan_and_reservations():
    _, registry, state, options, _, _, ledger, proposals = build_case()
    proposal = proposals[0]
    source_ref = proposal.resource_cost.irreversible_refs[0]

    missing_cost = replace(proposal, resource_cost=ResourceCost(()))
    assert "POKE_PAD_COST_MISMATCH" in rejection_reasons(
        state,
        options,
        ledger,
        missing_cost,
        registry,
    )

    source_none = replace(
        proposal,
        transaction_plan=replace(proposal.transaction_plan, source_ref=None),
    )
    assert "POKE_PAD_TRANSACTION_PLAN_MISMATCH" in rejection_reasons(
        state,
        options,
        ledger,
        source_none,
        registry,
    )

    plan_tamper = replace(
        proposal,
        transaction_plan=replace(
            proposal.transaction_plan,
            transaction_id=proposal.transaction_plan.transaction_id + "_FORGED",
        ),
    )
    assert "POKE_PAD_TRANSACTION_PLAN_MISMATCH" in rejection_reasons(
        state,
        options,
        ledger,
        plan_tamper,
        registry,
    )

    hard = ledger.reserve_exact(
        "TEST_HARD_PAD",
        ReservationKind.HARD_RESERVED,
        "test exact source reservation",
        (source_ref,),
    )
    assert any(
        reason.startswith("LEDGER_COST_REJECTED:RESERVED:TEST_HARD_PAD")
        for reason in rejection_reasons(state, options, hard, proposal, registry)
    )

    role = ledger.reserve_minimum(
        "TEST_ROLE_PAD",
        ReservationKind.ROLE_RESERVED_ONE,
        "test role source reservation",
        (1152,),
        1,
        (int(AreaType.HAND),),
    )
    assert "LEDGER_COST_REJECTED:RESERVATION_CONSTRAINT" in rejection_reasons(
        state,
        options,
        role,
        proposal,
        registry,
    )


def search_prompt(
    state,
    serials,
    *,
    effect_serial=30,
    duplicate=False,
    cards=None,
):
    targets = (
        tuple((677, serial) for serial in serials) if cards is None else tuple(cards)
    )
    keys = tuple(
        SemanticOptionKey(
            option_type=int(OptionType.CARD),
            player_index=state.seat,
            card_id=card_id,
            card_serial=serial,
            source_zone=int(AreaType.DECK),
        )
        for card_id, serial in targets
    )
    options = tuple(
        SemanticOption(index=index, key=key) for index, key in enumerate(keys)
    )
    if duplicate and keys:
        options = options + (SemanticOption(index=len(options), key=keys[0]),)
    callback_state = replace(
        state,
        turn_action_count=state.turn_action_count + 1,
        select_context=int(SelectContext.TO_HAND),
        select_type=int(SelectType.CARD),
        min_count=0,
        max_count=1,
        effect_ref=PhysicalRef(1152, effect_serial, state.seat, None, effect_serial),
        context_ref=None,
        select_deck_open=True,
    )
    return callback_state, options


def test_transaction_selects_lowest_serial_after_permutation_and_completes():
    _, _, state, options, _, _, _, proposals = build_case()
    plan = proposals[0].transaction_plan
    store = TransactionStore()

    started = store.start(plan, state, options)
    assert started.status is StartStatus.STARTED
    assert started.bound_action == (0,)
    callback_state, callback_options = search_prompt(state, (41, 40))
    issued = store.resume(callback_state, callback_options)
    assert issued.status is ResumeStatus.ADVANCED_ISSUE
    assert issued.action_spec.choices[0].card_serial == 40
    assert issued.bound_action == (1,)

    repeated = store.resume(callback_state, callback_options)
    assert repeated.status is ResumeStatus.DUPLICATE_REISSUE
    assert repeated.bound_action == (1,)

    source_discard = replace(plan.source_ref, zone=int(AreaType.DISCARD))
    selected_deck = PhysicalRef(
        677,
        40,
        state.seat,
        int(AreaType.DECK),
        40,
    )
    selected_hand = replace(selected_deck, zone=int(AreaType.HAND))
    stable_own = replace(
        state.own,
        hand_refs=tuple(
            ref_value
            for ref_value in state.own.hand_refs
            if (ref_value.card_id, ref_value.serial) != (1152, 30)
        )
        + (selected_hand,),
        hand_count=state.own.hand_count,
        discard_refs=state.own.discard_refs + (source_discard,),
        deck_count=state.own.deck_count - 1,
    )
    stable_after = replace(
        state,
        turn_action_count=state.turn_action_count + 2,
        own=stable_own,
        receipt_events=(
            _event(LogType.PLAY, ref_value=plan.source_ref),
            _event(LogType.MOVE_CARD, ref_value=selected_deck, from_area=int(AreaType.DECK), to_area=int(AreaType.HAND)),
        ),
    )
    completed = store.resume(stable_after, options)
    assert completed.status is ResumeStatus.COMPLETED
    assert not store.has_owner


@pytest.mark.parametrize(
    ("cards", "expected_card_id", "expected_serial", "expected_bound"),
    (
        (((677, 5), (675, 12), (676, 9), (675, 10)), 675, 10, (3,)),
        (((677, 5), (676, 9), (676, 8)), 676, 8, (2,)),
        (((677, 5), (677, 4)), 677, 4, (1,)),
    ),
)
def test_transaction_uses_ordered_role_fallback_and_lowest_serial(
    cards,
    expected_card_id,
    expected_serial,
    expected_bound,
):
    _, _, state, options, _, _, _, proposals = build_case(
        active_id=673,
        bench_ids=(),
    )
    plan = proposals[0].transaction_plan
    assert plan.steps[0].deferred_card_choice.ordered_card_id_classes == (
        (675,),
        (676,),
        (677,),
    )
    store = TransactionStore()
    assert store.start(plan, state, options).status is StartStatus.STARTED
    callback_state, callback_options = search_prompt(state, (), cards=cards)

    issued = store.resume(callback_state, callback_options)
    assert issued.status is ResumeStatus.ADVANCED_ISSUE
    assert issued.action_spec.choices[0].card_id == expected_card_id
    assert issued.action_spec.choices[0].card_serial == expected_serial
    assert issued.bound_action == expected_bound


@pytest.mark.parametrize(
    ("callback_builder", "expected_reason"),
    (
        (
            lambda state: search_prompt(state, (40,), duplicate=True),
            "DEFERRED_DUPLICATE_SEMANTIC_CHOICE",
        ),
        (
            lambda state: search_prompt(state, ()),
            "DEFERRED_CARD_CLASS_NOT_FOUND",
        ),
        (
            lambda state: search_prompt(state, (40,), effect_serial=31),
            "UNEXPECTED_EFFECT_REF",
        ),
    ),
)
def test_transaction_fail_closes_after_irreversible_prompt_drift(
    callback_builder,
    expected_reason,
):
    _, _, state, options, _, _, _, proposals = build_case()
    store = TransactionStore()
    assert (
        store.start(proposals[0].transaction_plan, state, options).status
        is StartStatus.STARTED
    )

    callback_state, callback_options = callback_builder(state)
    fault = store.resume(callback_state, callback_options)
    assert fault.status is ResumeStatus.IRREVERSIBLE_FAULT
    assert expected_reason in fault.reasons
    assert store.has_owner


def test_transaction_start_rejects_availability_union_tamper():
    _, _, state, options, _, _, _, proposals = build_case(
        active_id=673,
        bench_ids=(),
    )
    plan = proposals[0].transaction_plan
    step = plan.steps[0]
    policy = step.deferred_card_choice
    forged_availability = replace(policy.availability_proof, card_ids=(675,))
    forged_policy = replace(policy, availability_proof=forged_availability)
    forged_plan = replace(
        plan, steps=(replace(step, deferred_card_choice=forged_policy),)
    )

    rejected = TransactionStore().start(forged_plan, state, options)
    assert rejected.status is StartStatus.PLAN_STATE_MISMATCH
    assert "DECK_AVAILABILITY_TARGET_CLASS_MISMATCH" in rejected.reasons
    assert "DECK_AVAILABILITY_PROOF_CONTENT_MISMATCH" in rejected.reasons


def test_runtime_play_target_main_replans_without_fault():
    obs, registry, _, _, _, _, _, proposals = build_case()
    assert len(proposals) == 1
    runtime = AgentRuntime(registry=registry)
    prior = deepcopy(obs)
    prior["current"]["turn"] = 1
    prior["current"]["turnActionCount"] = 0
    prior["current"]["players"][0]["hand"] = []
    prior["current"]["players"][0]["handCount"] = 0
    prior["select"]["option"] = [{"type": int(OptionType.END), "playerIndex": 0}]
    assert runtime.act(prior) == [0]

    assert runtime.act(deepcopy(obs)) == [0]
    assert runtime.transactions.has_owner

    search = deepcopy(obs)
    search["current"]["turnActionCount"] += 1
    search["current"]["players"][0]["hand"] = []
    search["current"]["players"][0]["handCount"] = 0
    search["current"]["players"][0]["discard"] = [card(1152, 30)]
    search["select"].update(
        {
            "type": int(SelectType.CARD),
            "context": int(SelectContext.TO_HAND),
            "minCount": 0,
            "maxCount": 1,
            "deck": [card(677, 41), card(677, 40)],
            "effect": card(1152, 30),
            "option": [
                {
                    "type": int(OptionType.CARD),
                    "area": int(AreaType.DECK),
                    "index": 0,
                    "playerIndex": 0,
                },
                {
                    "type": int(OptionType.CARD),
                    "area": int(AreaType.DECK),
                    "index": 1,
                    "playerIndex": 0,
                },
            ],
        }
    )
    assert runtime.act(search) == [1]
    assert runtime.transactions.has_owner

    final_main = deepcopy(obs)
    final_main["current"]["turnActionCount"] += 2
    final_main["current"]["players"][0]["hand"] = [card(677, 40)]
    final_main["current"]["players"][0]["handCount"] = 1
    final_main["current"]["players"][0]["discard"] = [card(1152, 30)]
    final_main["current"]["players"][0]["deckCount"] -= 1
    final_main["select"]["option"] = [{"type": int(OptionType.END), "playerIndex": 0}]
    final_main["logs"] = [
        {
            "type": int(LogType.PLAY),
            "playerIndex": 0,
            "cardId": 1152,
            "serial": 30,
        },
        {
            "type": int(LogType.MOVE_CARD),
            "playerIndex": 0,
            "cardId": 677,
            "serial": 40,
            "fromArea": int(AreaType.DECK),
            "toArea": int(AreaType.HAND),
        },
    ]
    assert runtime.act(final_main) == [0]
    assert not runtime.transactions.has_owner
    assert not runtime.runtime_fault_latched
