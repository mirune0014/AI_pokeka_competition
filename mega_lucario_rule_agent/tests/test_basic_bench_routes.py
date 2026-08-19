from copy import deepcopy
from dataclasses import replace

import pytest

from mega_lucario_rule_agent.certificates import (
    CertificateKind,
    ProofSchema,
    basic_bench_proof,
)
from mega_lucario_rule_agent.features import (
    PublicMatchupFlag,
    build_deck_features,
    build_resource_ledger,
)
from mega_lucario_rule_agent.resolver import (
    ResolverTier,
    ResourceCost,
    resolve_proposals,
)
from mega_lucario_rule_agent.resource_ledger import ReservationKind
from mega_lucario_rule_agent.routes import enumerate_basic_bench_routes
from mega_lucario_rule_agent.state_view import (
    ActionSpec,
    AreaType,
    SelectContext,
    OptionType,
    build_semantic_options,
)
from mega_lucario_rule_agent.tests.test_attack_outcomes import (
    card,
    checked_state,
    observation,
    pokemon,
    pokemon_catalog_row,
    registry_for,
)


_HP = {
    673: 70,
    675: 110,
    676: 110,
    677: 80,
    678: 340,
}


def own_pokemon(card_id, serial):
    return pokemon(
        card_id,
        serial,
        hp=_HP[card_id],
        max_hp=_HP[card_id],
    )


def catalog_rows():
    return (
        pokemon_catalog_row(673, "Makuhita", hp=70),
        pokemon_catalog_row(675, "Lunatone", hp=110),
        pokemon_catalog_row(676, "Solrock", hp=110),
        pokemon_catalog_row(677, "Riolu", hp=80),
        pokemon_catalog_row(
            678,
            "Mega Lucario ex",
            hp=340,
            basic=False,
            stage1=True,
            mega_ex=True,
        ),
    )


def build_case(
    hand_cards,
    *,
    active_id=678,
    bench_ids=(),
    opponent_id=900,
    opponent_hp=300,
    opponent_row=None,
):
    active = own_pokemon(active_id, 10)
    bench = tuple(
        own_pokemon(card_id, 20 + index) for index, card_id in enumerate(bench_ids)
    )
    target = pokemon(
        opponent_id,
        110,
        player=1,
        hp=opponent_hp,
        max_hp=opponent_hp,
    )
    obs = observation(
        (),
        own_active=active,
        own_bench=bench,
        opponent_active=target,
    )
    obs["current"]["players"][0]["hand"] = [
        card(card_id, serial) for card_id, serial in hand_cards
    ]
    obs["current"]["players"][0]["handCount"] = len(hand_cards)
    obs["select"]["option"] = [
        {"type": int(OptionType.PLAY), "index": index}
        for index in range(len(hand_cards))
    ] + [{"type": int(OptionType.END), "playerIndex": 0}]
    target_row = opponent_row or pokemon_catalog_row(
        opponent_id,
        "Test Target",
        hp=opponent_hp,
    )
    registry = registry_for(
        (),
        target_row=target_row,
        extra_rows=catalog_rows(),
    )
    state = checked_state(obs)
    options = build_semantic_options(obs)
    features = build_deck_features(state, options, registry)
    ledger = build_resource_ledger(state)
    proposals = enumerate_basic_bench_routes(
        state,
        options,
        features,
        registry,
    )
    return obs, registry, state, options, features, ledger, proposals


def rejection_for(resolution, rule_id):
    return next(
        rejection for rejection in resolution.rejections if rejection.rule_id == rule_id
    )


def test_missing_engine_is_the_only_proposed_role_and_rebinds_after_permutation():
    (
        obs,
        registry,
        state,
        options,
        _,
        ledger,
        proposals,
    ) = build_case(
        (
            (675, 21),
            (677, 30),
            (676, 22),
            (673, 40),
            (675, 20),
        )
    )

    assert len(proposals) == 3
    assert {proposal.proof.fact("purpose") for proposal in proposals} == {
        "ENGINE_COMPLETION"
    }
    assert {proposal.certificate_kind for proposal in proposals} == {
        CertificateKind.ENGINE_COMPLETION
    }
    assert all(
        proposal.proof.schema == ProofSchema.BASIC_BENCH_V1 for proposal in proposals
    )

    resolution = resolve_proposals(
        state,
        options,
        ledger,
        proposals,
        registry=registry,
    )
    selected = resolution.selected.action_spec.choices[0]
    assert (selected.card_id, selected.card_serial) == (675, 20)
    assert selected.player_index == state.seat
    assert selected.source_zone == 2
    assert selected.source_index is None
    assert resolution.bound_action == (4,)

    permuted_obs = deepcopy(obs)
    permuted_obs["current"]["players"][0]["hand"] = list(
        reversed(permuted_obs["current"]["players"][0]["hand"])
    )
    permuted_state = checked_state(permuted_obs)
    permuted_options = build_semantic_options(permuted_obs)
    permuted_ledger = build_resource_ledger(permuted_state)
    rebound = resolve_proposals(
        permuted_state,
        permuted_options,
        permuted_ledger,
        tuple(reversed(proposals)),
        registry=registry,
    )
    assert rebound.selected.action_spec == resolution.selected.action_spec
    assert rebound.bound_action == (0,)


def test_first_riolu_follows_completed_engine_and_uses_lowest_serial():
    (
        _,
        registry,
        state,
        options,
        _,
        ledger,
        proposals,
    ) = build_case(
        ((677, 31), (673, 40), (677, 30)),
        active_id=676,
        bench_ids=(675,),
    )

    assert len(proposals) == 2
    assert {proposal.proof.fact("purpose") for proposal in proposals} == {"FIRST_RIOLU"}
    resolution = resolve_proposals(
        state,
        options,
        ledger,
        proposals,
        registry=registry,
    )
    selected = resolution.selected.action_spec.choices[0]
    assert (selected.card_id, selected.card_serial) == (677, 30)


def test_boardout_guard_chooses_a_distinct_role_and_holds_second_riolu():
    (
        _,
        registry,
        state,
        options,
        features,
        ledger,
        proposals,
    ) = build_case(
        ((677, 30), (673, 40)),
        active_id=677,
    )

    assert features.board_out_risk
    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.proof.fact("purpose") == "BOARD_OUT_BACKUP"
    assert proposal.action_spec.choices[0].card_id == 673
    resolution = resolve_proposals(
        state,
        options,
        ledger,
        proposals,
        registry=registry,
    )
    assert resolution.selected == proposal


def test_normal_role_placement_preserves_the_last_flexible_bench_slot():
    (
        _,
        _,
        _,
        _,
        features,
        _,
        proposals,
    ) = build_case(
        ((675, 40),),
        active_id=678,
        bench_ids=(676, 677, 673, 678),
    )

    assert features.safe_bench_slots == 0
    assert features.missing_engine_card_ids == (675,)
    assert proposals == ()


def test_public_resistant_target_promotes_matchup_makuhita_only():
    alakazam = pokemon_catalog_row(
        743,
        "Alakazam",
        hp=140,
        resistance=6,
        basic=False,
        stage2=True,
    )
    (
        _,
        registry,
        state,
        options,
        features,
        ledger,
        proposals,
    ) = build_case(
        ((673, 40), (677, 41)),
        active_id=678,
        bench_ids=(676, 675, 677),
        opponent_id=743,
        opponent_hp=140,
        opponent_row=alakazam,
    )

    assert PublicMatchupFlag.ONE_PRIZE_MEDIUM_HP_RESISTANT in features.public_flags
    assert len(proposals) == 1
    assert proposals[0].proof.fact("purpose") == "MATCHUP_MAKUHITA"
    assert proposals[0].action_spec.choices[0].card_id == 673
    assert (
        resolve_proposals(
            state,
            options,
            ledger,
            proposals,
            registry=registry,
        ).selected
        == proposals[0]
    )


def test_public_spread_promotes_exactly_one_backup_riolu():
    dragapult = pokemon_catalog_row(
        121,
        "Dragapult ex",
        hp=320,
        basic=False,
        stage2=True,
        ex=True,
    )
    (
        _,
        _,
        _,
        _,
        features,
        _,
        proposals,
    ) = build_case(
        ((673, 40), (677, 31), (677, 30)),
        active_id=678,
        bench_ids=(676, 675),
        opponent_id=121,
        opponent_hp=320,
        opponent_row=dragapult,
    )

    assert PublicMatchupFlag.BENCH_SPREAD_THREAT in features.public_flags
    assert len(proposals) == 2
    assert {proposal.proof.fact("purpose") for proposal in proposals} == {
        "SPREAD_BACKUP_RIOLU"
    }
    assert {proposal.action_spec.choices[0].card_serial for proposal in proposals} == {
        30,
        31,
    }


def test_resolver_recomputes_basic_proof_and_keeps_profile_closed():
    (
        _,
        registry,
        state,
        options,
        _,
        ledger,
        proposals,
    ) = build_case(
        ((675, 20),),
        active_id=676,
    )
    proposal = proposals[0]
    accepted = resolve_proposals(
        state,
        options,
        ledger,
        (proposal,),
        registry=registry,
    )
    assert accepted.selected == proposal

    wrong_tier = replace(
        proposal,
        tier=ResolverTier.ROUTE_CRITICAL_SEARCH,
    )
    tier_rejection = resolve_proposals(
        state,
        options,
        ledger,
        (wrong_tier,),
        registry=registry,
    )
    assert (
        "PROFILE_TIER_FORBIDDEN"
        in rejection_for(
            tier_rejection,
            wrong_tier.rule_id,
        ).reasons
    )

    source_ref = next(
        ref_value for ref_value in state.own.hand_refs if ref_value.card_id == 675
    )
    with_cost = replace(
        proposal,
        resource_cost=ResourceCost((source_ref,)),
    )
    cost_rejection = resolve_proposals(
        state,
        options,
        ledger,
        (with_cost,),
        registry=registry,
    )
    assert (
        "PROFILE_RESOURCE_COST_FORBIDDEN"
        in rejection_for(
            cost_rejection,
            with_cost.rule_id,
        ).reasons
    )

    reserved_ledger = ledger.reserve_exact(
        "protect_engine",
        ReservationKind.CURRENT_ROUTE,
        "keep the exact engine Basic for another route",
        (source_ref,),
    )
    reservation_rejection = resolve_proposals(
        state,
        options,
        reserved_ledger,
        (proposal,),
        registry=registry,
    )
    assert (
        "BASIC_BENCH_SOURCE_RESERVED:protect_engine"
        in rejection_for(
            reservation_rejection,
            proposal.rule_id,
        ).reasons
    )

    changed_registry = registry_for(
        (),
        target_row=pokemon_catalog_row(
            900,
            "Changed Target",
            hp=300,
            weakness=6,
        ),
        extra_rows=catalog_rows(),
    )
    stale = resolve_proposals(
        state,
        options,
        ledger,
        (proposal,),
        registry=changed_registry,
    )
    stale_reasons = rejection_for(stale, proposal.rule_id).reasons
    assert "PROOF_REGISTRY_STALE" in stale_reasons
    assert "BASIC_BENCH_FEATURES_STALE" in stale_reasons


def test_basic_proof_rejects_setup_context_and_a_physically_full_bench():
    obs, registry, _, _, _, _, _ = build_case(
        ((675, 20),),
        active_id=676,
    )
    setup_obs = deepcopy(obs)
    setup_obs["select"]["context"] = int(SelectContext.SETUP_BENCH_POKEMON)
    setup_state = checked_state(setup_obs)
    setup_options = build_semantic_options(setup_obs)
    setup_features = build_deck_features(
        setup_state,
        setup_options,
        registry,
    )
    with pytest.raises(ValueError, match="stable MAIN"):
        basic_bench_proof(
            setup_state,
            setup_options,
            registry,
            setup_features,
            ActionSpec.single(setup_options[0].key),
        )

    (
        _,
        full_registry,
        full_state,
        full_options,
        full_features,
        _,
        _,
    ) = build_case(
        ((675, 99),),
        active_id=678,
        bench_ids=(676, 677, 673, 678, 677),
    )
    with pytest.raises(ValueError, match="physical Bench slot"):
        basic_bench_proof(
            full_state,
            full_options,
            full_registry,
            full_features,
            ActionSpec.single(full_options[0].key),
        )


def test_existing_pokemon_appear_this_turn_does_not_block_basic_placement():
    obs, registry, _, _, _, _, _ = build_case(
        ((675, 20),),
        active_id=676,
    )
    obs["current"]["players"][0]["active"][0]["appearThisTurn"] = True
    state = checked_state(obs)
    options = build_semantic_options(obs)
    features = build_deck_features(state, options, registry)

    proposals = enumerate_basic_bench_routes(
        state,
        options,
        features,
        registry,
    )

    assert len(proposals) == 1
    assert proposals[0].action_spec.choices[0].card_serial == 20


def test_basic_proof_rejects_forged_source_fields_and_duplicate_semantics():
    (
        obs,
        registry,
        state,
        options,
        features,
        _,
        proposals,
    ) = build_case(
        ((675, 20),),
        active_id=676,
    )
    key = proposals[0].action_spec.choices[0]
    forged = ActionSpec.single(replace(key, source_index=0))
    with pytest.raises(ValueError, match="exact own HAND Basic"):
        basic_bench_proof(
            state,
            options,
            registry,
            features,
            forged,
        )

    forged_target = ActionSpec.single(replace(key, target_zone=int(AreaType.BENCH)))
    with pytest.raises(ValueError, match="exact own HAND Basic"):
        basic_bench_proof(
            state,
            options,
            registry,
            features,
            forged_target,
        )

    duplicate_obs = deepcopy(obs)
    duplicate_obs["select"]["option"].insert(
        1,
        deepcopy(duplicate_obs["select"]["option"][0]),
    )
    duplicate_state = checked_state(duplicate_obs)
    duplicate_options = build_semantic_options(duplicate_obs)
    duplicate_features = build_deck_features(
        duplicate_state,
        duplicate_options,
        registry,
    )
    with pytest.raises(ValueError, match="bind uniquely"):
        basic_bench_proof(
            duplicate_state,
            duplicate_options,
            registry,
            duplicate_features,
            proposals[0].action_spec,
        )
