from dataclasses import replace

import pytest

from mega_lucario_rule_agent.features import (
    build_deck_features,
    build_resource_ledger,
)
from mega_lucario_rule_agent.resolver import resolve_proposals
from mega_lucario_rule_agent.routes import (
    enumerate_continuity_attach_routes,
    enumerate_fighting_gong_routes,
)
from mega_lucario_rule_agent.state_view import (
    AreaType,
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
)
from mega_lucario_rule_agent.tests.test_requirement_routes import _case, _registry


def _opening_case(
    *,
    bench=(),
    extra_hand=(),
    active_energy=(),
    attack_ids=(),
    energy_attached=False,
    include_attach=True,
):
    gong = card(1142, 30)
    energy = card(6, 31)
    hand = [gong, energy, *extra_hand]
    obs = observation(
        attack_ids,
        own_active=pokemon(
            676,
            10,
            hp=110,
            max_hp=110,
            energy_cards=active_energy,
        ),
        own_bench=bench,
    )
    obs["current"]["turn"] = 1
    obs["current"]["turnActionCount"] = 4
    obs["current"]["energyAttached"] = energy_attached
    obs["current"]["players"][0]["hand"] = hand
    obs["current"]["players"][0]["handCount"] = len(hand)
    obs["current"]["players"][0]["prize"] = [card(6, 950 + index) for index in range(6)]
    raw_options = [{"type": int(OptionType.PLAY), "index": 0}]
    if include_attach:
        raw_options.append(
            {
                "type": int(OptionType.ATTACH),
                "area": int(AreaType.HAND),
                "index": 1,
                "inPlayArea": int(AreaType.ACTIVE),
                "inPlayIndex": 0,
            }
        )
    raw_options.extend(
        {"type": int(OptionType.ATTACK), "attackId": attack_id}
        for attack_id in attack_ids
    )
    obs["select"]["option"] = raw_options

    registry = _registry()
    state = checked_state(obs)
    options = build_semantic_options(obs)
    features = build_deck_features(state, options, registry)
    proposals = enumerate_fighting_gong_routes(
        state,
        options,
        features,
        registry,
    )
    return state, options, features, registry, proposals


def _search_prompt(state, cards):
    keys = tuple(
        SemanticOptionKey(
            option_type=int(OptionType.CARD),
            player_index=state.seat,
            card_id=card_id,
            card_serial=serial,
            source_zone=int(AreaType.DECK),
        )
        for card_id, serial in cards
    )
    options = tuple(
        SemanticOption(index=index, key=key) for index, key in enumerate(keys)
    )
    callback_state = replace(
        state,
        turn_action_count=state.turn_action_count + 1,
        select_context=int(SelectContext.TO_HAND),
        select_type=int(SelectType.CARD),
        min_count=0,
        max_count=1,
        effect_ref=PhysicalRef(1142, 30, state.seat, None, 30),
        context_ref=None,
        select_deck_open=True,
    )
    return callback_state, options


def _selected_search_card(state, options, proposal, cards):
    store = TransactionStore()
    started = store.start(proposal.transaction_plan, state, options)
    assert started.status is StartStatus.STARTED
    callback_state, callback_options = _search_prompt(state, cards)
    issued = store.resume(callback_state, callback_options)
    assert issued.status is ResumeStatus.ADVANCED_ISSUE
    return issued.action_spec.choices[0].card_id


def test_trace_step_five_emits_gong_and_selects_lunatone_from_full_union():
    state, options, _, _, proposals = _opening_case()

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.action_spec.choices[0].card_id == 1142
    assert proposal.proof.fact("purpose") == "STALLED_SOLROCK_OPENING"
    policy = proposal.transaction_plan.steps[0].deferred_card_choice
    assert policy.ordered_card_id_classes == ((675,), (677,), (6,))
    assert policy.availability_proof.card_ids == (6, 675, 677)
    assert policy.availability_proof.is_guaranteed
    assert (
        _selected_search_card(
            state,
            options,
            proposal,
            ((6, 43), (677, 42), (675, 41)),
        )
        == 675
    )


@pytest.mark.parametrize(
    ("cards", "expected_card_id"),
    (
        (((6, 43), (677, 42)), 677),
        (((6, 43),), 6),
    ),
)
def test_stalled_gong_selects_highest_available_fallback(cards, expected_card_id):
    state, options, _, _, proposals = _opening_case()

    assert len(proposals) == 1
    assert (
        _selected_search_card(
            state,
            options,
            proposals[0],
            cards,
        )
        == expected_card_id
    )


@pytest.mark.parametrize(
    "case_kwargs",
    (
        {
            "bench": tuple(
                pokemon(673, 20 + index, hp=70, max_hp=70) for index in range(5)
            )
        },
        {"extra_hand": (card(677, 32),)},
        {"extra_hand": (card(678, 32),)},
        {"bench": (pokemon(677, 20, hp=80, max_hp=80),)},
        {"bench": (pokemon(678, 20, hp=340, max_hp=340),)},
        {"active_energy": ((6, 50),)},
        {"attack_ids": (980,)},
        {"energy_attached": True},
        {"include_attach": False},
    ),
)
def test_stalled_gong_guards_suppress_unsafe_or_redundant_routes(case_kwargs):
    assert _opening_case(**case_kwargs)[4] == ()


def test_deck_rule_continuity_attach_is_selected_only_with_lunatone_on_bench():
    with_lunatone = _case(
        active=pokemon(676, 10, hp=110, max_hp=110),
        bench=(pokemon(675, 20, hp=110, max_hp=110),),
        hand=(card(6, 30),),
        raw_options=(
            {
                "type": int(OptionType.ATTACH),
                "area": int(AreaType.HAND),
                "index": 0,
                "inPlayArea": int(AreaType.ACTIVE),
                "inPlayIndex": 0,
            },
        ),
    )
    proposals = enumerate_continuity_attach_routes(
        with_lunatone[0],
        with_lunatone[1],
        with_lunatone[2],
        with_lunatone[4],
        build_resource_ledger(with_lunatone[0]),
    )
    assert len(proposals) == 1
    resolution = resolve_proposals(
        with_lunatone[0],
        with_lunatone[1],
        build_resource_ledger(with_lunatone[0]),
        proposals,
        registry=with_lunatone[4],
    )
    assert resolution.selected == proposals[0]
    assert resolution.rejections == ()

    without_lunatone = _case(
        active=pokemon(676, 10, hp=110, max_hp=110),
        hand=(card(6, 30),),
        raw_options=(
            {
                "type": int(OptionType.ATTACH),
                "area": int(AreaType.HAND),
                "index": 0,
                "inPlayArea": int(AreaType.ACTIVE),
                "inPlayIndex": 0,
            },
        ),
    )
    assert (
        enumerate_continuity_attach_routes(
            without_lunatone[0],
            without_lunatone[1],
            without_lunatone[2],
            without_lunatone[4],
            build_resource_ledger(without_lunatone[0]),
        )
        == ()
    )
