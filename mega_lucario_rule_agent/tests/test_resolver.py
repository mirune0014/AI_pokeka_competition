from dataclasses import replace

import pytest

from mega_lucario_rule_agent.certificates import (
    CertificateKind,
    ProofSchema,
    safe_fallback_proof,
)
from mega_lucario_rule_agent.resolver import (
    Proposal,
    ProposalDisposition,
    ResolverMetrics,
    ResolverTier,
    ResourceCost,
    proposal_digest,
    resolve_proposals,
)
from mega_lucario_rule_agent.resource_ledger import (
    ReservationKind,
    ResourceLedger,
)
from mega_lucario_rule_agent.state_view import (
    ActionSpec,
    AreaType,
    OptionType,
    PhysicalRef,
    PlayerView,
    PokemonView,
    PublicState,
    SelectContext,
    SelectType,
    SemanticOption,
    SemanticOptionKey,
)


def ref(card_id, serial, owner, zone):
    return PhysicalRef(card_id, serial, owner, int(zone), serial)


def pokemon(card_id, serial, owner, zone, hp, max_hp):
    return PokemonView(
        ref=ref(card_id, serial, owner, zone),
        hp=hp,
        max_hp=max_hp,
        appear_this_turn=False,
        energy_types=(),
        energy_refs=(),
        tool_refs=(),
        pre_evolution_refs=(),
    )


def player(index, active, hand_refs=(), hand_count=None):
    return PlayerView(
        index=index,
        active=(active,),
        active_slot_count=1,
        hidden_active_count=0,
        bench=(),
        hand_refs=tuple(hand_refs),
        discard_refs=(),
        prize_refs=(),
        prize_count=6,
        deck_count=40,
        hand_count=len(hand_refs) if hand_count is None else hand_count,
        bench_max=5,
        poisoned=False,
        burned=False,
        asleep=False,
        paralyzed=False,
        confused=False,
    )


def state():
    hand_energy = ref(6, 100, 0, AreaType.HAND)
    return PublicState(
        game_epoch=7,
        seat=0,
        turn=5,
        turn_action_count=4,
        first_player=0,
        supporter_played=False,
        stadium_played=False,
        energy_attached=False,
        retreated=False,
        result=-1,
        own=player(
            0,
            pokemon(678, 10, 0, AreaType.ACTIVE, 340, 340),
            hand_refs=(hand_energy,),
        ),
        opponent=player(
            1,
            pokemon(999, 20, 1, AreaType.ACTIVE, 200, 200),
            hand_count=5,
        ),
        stadium_refs=(),
        looking_refs=(),
        select_context=int(SelectContext.MAIN),
        min_count=1,
        max_count=1,
        effect_ref=None,
        context_ref=None,
        select_type=int(SelectType.MAIN),
        remaining_damage_counter=0,
        remaining_energy_cost=0,
    )


def attack_spec(attack_id):
    return ActionSpec.single(
        SemanticOptionKey(
            option_type=int(OptionType.ATTACK),
            player_index=0,
            attack_id=attack_id,
        )
    )


def end_spec():
    return ActionSpec.single(
        SemanticOptionKey(
            option_type=int(OptionType.END),
            player_index=0,
        )
    )


def options_for(*specs):
    return tuple(
        SemanticOption(index=index, key=spec.choices[0])
        for index, spec in enumerate(specs)
    )


def proposal(
    current,
    legal,
    spec,
    rule_id,
    tier=None,
    certificate_kind=CertificateKind.SAFE_FALLBACK,
    action_spec=None,
    resource_cost=None,
    reservation_ids=(),
    transaction_plan=None,
    metrics=None,
    tiebreak=None,
):
    proof = safe_fallback_proof(current, legal, spec, rule_id)
    if tier is None:
        tier = (
            ResolverTier.PASS
            if spec.choices[0].option_type == int(OptionType.END)
            else ResolverTier.RESOURCE_PRESERVING_FALLBACK
        )
    if tiebreak is None:
        tiebreak = (
            (int(OptionType.END),)
            if spec.choices[0].option_type == int(OptionType.END)
            else (int(OptionType.ATTACK), spec.choices[0].attack_id)
        )
    return Proposal(
        rule_id=rule_id,
        tier=tier,
        action_spec=spec if action_spec is None else action_spec,
        certificate_kind=certificate_kind,
        proof=proof,
        resource_cost=ResourceCost() if resource_cost is None else resource_cost,
        reservation_ids=reservation_ids,
        transaction_plan=transaction_plan,
        metrics=ResolverMetrics() if metrics is None else metrics,
        deterministic_tiebreak=tiebreak,
    )


def rejection_for(resolution, rule_id):
    return next(value for value in resolution.rejections if value.rule_id == rule_id)


def test_attack_fallback_precedes_pass_and_rebinds_after_option_permutation():
    current = state()
    attack = attack_spec(982)
    end = end_spec()
    original_legal = options_for(attack, end)
    proposals = (
        proposal(current, original_legal, end, "PASS"),
        proposal(current, original_legal, attack, "ATTACK_982"),
    )

    permuted_legal = options_for(end, attack)
    resolution = resolve_proposals(
        current,
        permuted_legal,
        ResourceLedger(()),
        proposals,
    )

    assert resolution.selected.rule_id == "ATTACK_982"
    assert resolution.bound_action == (1,)
    assert resolution.stats.proposed == 2
    assert resolution.stats.accepted == 2
    assert resolution.stats.rejected == 0
    evaluations = {value.rule_id: value for value in resolution.evaluations}
    assert evaluations["ATTACK_982"].disposition == ProposalDisposition.SELECTED
    assert evaluations["ATTACK_982"].reasons == ()
    assert (
        evaluations["PASS"].disposition
        == ProposalDisposition.VALID_NOT_SELECTED
    )
    assert evaluations["PASS"].reasons == ("LOWER_RESOLVER_RANK",)


def test_attack_tie_is_deterministic_and_independent_of_proposal_input_order():
    current = state()
    aura = attack_spec(982)
    brave = attack_spec(983)
    legal = options_for(brave, aura)
    aura_proposal = proposal(current, legal, aura, "Z_AURA")
    brave_proposal = proposal(current, legal, brave, "A_BRAVE")

    forward = resolve_proposals(
        current,
        legal,
        ResourceLedger(()),
        (brave_proposal, aura_proposal),
    )
    reverse = resolve_proposals(
        current,
        legal,
        ResourceLedger(()),
        (aura_proposal, brave_proposal),
    )

    assert forward.selected.rule_id == "Z_AURA"
    assert reverse.selected.rule_id == "Z_AURA"
    assert forward.bound_action == reverse.bound_action == (1,)
    assert forward.evaluations == reverse.evaluations


def test_state_or_legal_option_change_invalidates_a_previously_issued_proof():
    current = state()
    attack = attack_spec(982)
    legal = options_for(attack)
    candidate = proposal(current, legal, attack, "STALE_CHECK")

    changed_state = replace(
        current,
        opponent=replace(
            current.opponent,
            active=(
                replace(
                    current.opponent.active[0],
                    hp=current.opponent.active[0].hp - 10,
                ),
            ),
        ),
    )
    stale_state = resolve_proposals(
        changed_state,
        legal,
        ResourceLedger(()),
        (candidate,),
    )
    assert "PROOF_STATE_STALE" in rejection_for(
        stale_state,
        "STALE_CHECK",
    ).reasons

    changed_legal = options_for(attack, end_spec())
    stale_options = resolve_proposals(
        current,
        changed_legal,
        ResourceLedger(()),
        (candidate,),
    )
    assert "PROOF_OPTIONS_STALE" in rejection_for(
        stale_options,
        "STALE_CHECK",
    ).reasons


def test_duplicate_semantic_live_option_is_rejected_instead_of_using_lowest_index():
    current = state()
    attack = attack_spec(982)
    legal = options_for(attack)
    candidate = proposal(current, legal, attack, "DUPLICATE_CHECK")
    duplicate_legal = options_for(attack, attack)

    resolution = resolve_proposals(
        current,
        duplicate_legal,
        ResourceLedger(()),
        (candidate,),
    )
    reasons = rejection_for(resolution, "DUPLICATE_CHECK").reasons
    assert "DUPLICATE_SEMANTIC_OPTION" in reasons
    assert "PROOF_OPTIONS_STALE" in reasons
    assert resolution.selected is None


@pytest.mark.parametrize("invalid_index", (999, -1, True))
def test_malformed_live_option_indices_are_never_returned(invalid_index):
    current = state()
    attack = attack_spec(982)
    legal = options_for(attack)
    candidate = proposal(current, legal, attack, "BAD_INDEX_CHECK")
    malformed = (
        SemanticOption(index=invalid_index, key=attack.choices[0]),
    )

    resolution = resolve_proposals(
        current,
        malformed,
        ResourceLedger(()),
        (candidate,),
    )

    assert "LEGAL_OPTION_INDEX_INVALID" in rejection_for(
        resolution,
        "BAD_INDEX_CHECK",
    ).reasons
    assert resolution.bound_action is None


def test_colliding_or_incomplete_live_option_index_sets_are_rejected():
    current = state()
    attack = attack_spec(982)
    end = end_spec()
    legal = options_for(attack, end)
    candidate = proposal(current, legal, attack, "INDEX_SET_CHECK")

    collision = (
        SemanticOption(index=0, key=attack.choices[0]),
        SemanticOption(index=0, key=end.choices[0]),
    )
    collision_resolution = resolve_proposals(
        current,
        collision,
        ResourceLedger(()),
        (candidate,),
    )
    collision_reasons = rejection_for(
        collision_resolution,
        "INDEX_SET_CHECK",
    ).reasons
    assert "LEGAL_OPTION_INDEX_COLLISION" in collision_reasons
    assert "LEGAL_OPTION_INDEX_SET_INCOMPLETE" in collision_reasons

    incomplete = (
        SemanticOption(index=0, key=attack.choices[0]),
        SemanticOption(index=2, key=end.choices[0]),
    )
    incomplete_resolution = resolve_proposals(
        current,
        incomplete,
        ResourceLedger(()),
        (candidate,),
    )
    incomplete_reasons = rejection_for(
        incomplete_resolution,
        "INDEX_SET_CHECK",
    ).reasons
    assert "LEGAL_OPTION_INDEX_INVALID" in incomplete_reasons
    assert "LEGAL_OPTION_INDEX_SET_INCOMPLETE" in incomplete_reasons


def test_valid_index_permutation_does_not_change_semantic_selection():
    current = state()
    attack = attack_spec(982)
    end = end_spec()
    canonical = options_for(attack, end)
    candidate = proposal(current, canonical, attack, "INDEX_PERMUTATION")
    permuted_sequence = (
        SemanticOption(index=1, key=end.choices[0]),
        SemanticOption(index=0, key=attack.choices[0]),
    )

    resolution = resolve_proposals(
        current,
        permuted_sequence,
        ResourceLedger(()),
        (candidate,),
    )

    assert resolution.selected.rule_id == "INDEX_PERMUTATION"
    assert resolution.bound_action == (0,)


def test_safe_profile_rejects_tier_kind_and_action_spec_escalation():
    current = state()
    aura = attack_spec(982)
    brave = attack_spec(983)
    legal = options_for(aura, brave)
    wrong_tier = proposal(
        current,
        legal,
        aura,
        "WRONG_TIER",
        tier=ResolverTier.EXACT_WIN_NOW,
    )
    wrong_kind = proposal(
        current,
        legal,
        aura,
        "WRONG_KIND",
        certificate_kind=CertificateKind.WIN_NOW,
    )
    wrong_action = proposal(
        current,
        legal,
        aura,
        "WRONG_ACTION",
        action_spec=brave,
        tiebreak=(int(OptionType.ATTACK), 983),
    )

    resolution = resolve_proposals(
        current,
        legal,
        ResourceLedger(()),
        (wrong_tier, wrong_kind, wrong_action),
    )

    assert "PROFILE_TIER_FORBIDDEN" in rejection_for(
        resolution,
        "WRONG_TIER",
    ).reasons
    assert "CERTIFICATE_KIND_MISMATCH" in rejection_for(
        resolution,
        "WRONG_KIND",
    ).reasons
    assert "PROFILE_KIND_FORBIDDEN" in rejection_for(
        resolution,
        "WRONG_KIND",
    ).reasons
    assert "PROOF_ACTION_MISMATCH" in rejection_for(
        resolution,
        "WRONG_ACTION",
    ).reasons
    assert set(ProofSchema) == {
        ProofSchema.SAFE_FALLBACK_V1,
        ProofSchema.ATTACK_OUTCOME_V1,
        ProofSchema.BASIC_BENCH_V1,
        ProofSchema.POKE_PAD_CORE_FORMATION_V1,
        ProofSchema.FIRST_TURN_RIOLU_ATTACH_V1,
    }


def test_safe_profile_rejects_cost_transaction_metric_and_tiebreak_claims():
    current = state()
    attack = attack_spec(982)
    legal = options_for(attack)
    hand_energy = current.own.hand_refs[0]
    ledger = ResourceLedger((hand_energy,))
    with_cost = proposal(
        current,
        legal,
        attack,
        "WITH_COST",
        resource_cost=ResourceCost((hand_energy,)),
    )
    with_transaction = proposal(
        current,
        legal,
        attack,
        "WITH_TRANSACTION",
        transaction_plan=object(),
    )
    with_metric = proposal(
        current,
        legal,
        attack,
        "WITH_METRIC",
        metrics=ResolverMetrics(supporter_opportunity_cost=1),
    )
    wrong_tiebreak = proposal(
        current,
        legal,
        attack,
        "WRONG_TIEBREAK",
        tiebreak=(int(OptionType.ATTACK), 999999),
    )

    resolution = resolve_proposals(
        current,
        legal,
        ledger,
        (with_cost, with_transaction, with_metric, wrong_tiebreak),
    )

    assert "PROFILE_RESOURCE_COST_FORBIDDEN" in rejection_for(
        resolution,
        "WITH_COST",
    ).reasons
    assert "PROFILE_TRANSACTION_FORBIDDEN" in rejection_for(
        resolution,
        "WITH_TRANSACTION",
    ).reasons
    assert "INVALID_TRANSACTION_PLAN" in rejection_for(
        resolution,
        "WITH_TRANSACTION",
    ).reasons
    assert "PROFILE_METRIC_CLAIM_FORBIDDEN" in rejection_for(
        resolution,
        "WITH_METRIC",
    ).reasons
    assert "NONCANONICAL_TIEBREAK" in rejection_for(
        resolution,
        "WRONG_TIEBREAK",
    ).reasons


def test_ledger_must_be_owned_by_actor_and_bound_to_current_known_refs():
    current = state()
    attack = attack_spec(982)
    legal = options_for(attack)
    candidate = proposal(current, legal, attack, "LEDGER_CHECK")
    foreign_ref = ref(6, 777, 1, AreaType.HAND)
    foreign_ledger = ResourceLedger((foreign_ref,))

    resolution = resolve_proposals(
        current,
        legal,
        foreign_ledger,
        (candidate,),
    )
    reasons = rejection_for(resolution, "LEDGER_CHECK").reasons
    assert "LEDGER_OWNER_MISMATCH" in reasons
    assert "LEDGER_REF_NOT_IN_STATE" in reasons


def test_reservation_ids_are_exactly_traced_and_frozen_profile_rejects_them():
    current = state()
    attack = attack_spec(982)
    legal = options_for(attack)
    hand_energy = current.own.hand_refs[0]
    ledger = ResourceLedger((hand_energy,)).reserve_exact(
        "CURRENT_ATTACK_ENERGY",
        ReservationKind.HARD_RESERVED,
        "preserve current attack",
        (hand_energy,),
    )
    known = proposal(
        current,
        legal,
        attack,
        "KNOWN_RESERVATION",
        reservation_ids=("CURRENT_ATTACK_ENERGY",),
    )
    unknown = proposal(
        current,
        legal,
        attack,
        "UNKNOWN_RESERVATION",
        reservation_ids=("NOT_DECLARED",),
    )

    resolution = resolve_proposals(current, legal, ledger, (unknown, known))

    known_rejection = rejection_for(resolution, "KNOWN_RESERVATION")
    unknown_rejection = rejection_for(resolution, "UNKNOWN_RESERVATION")
    assert "PROFILE_RESERVATION_FORBIDDEN" in known_rejection.reasons
    assert "UNKNOWN_RESERVATION_ID:NOT_DECLARED" in unknown_rejection.reasons
    assert known_rejection.proposal_digest == proposal_digest(known)
    assert unknown_rejection.proposal_digest == proposal_digest(unknown)
    assert len(resolution.evaluations) == resolution.stats.proposed == 2
    assert all(
        value.disposition == ProposalDisposition.REJECTED
        for value in resolution.evaluations
    )


def test_proposal_rejects_duplicate_or_blank_reservation_ids():
    current = state()
    attack = attack_spec(982)
    legal = options_for(attack)
    with pytest.raises(ValueError, match="unique"):
        proposal(
            current,
            legal,
            attack,
            "DUPLICATE_RESERVATIONS",
            reservation_ids=("ONE", "ONE"),
        )
    with pytest.raises(ValueError, match="trimmed"):
        proposal(
            current,
            legal,
            attack,
            "BLANK_RESERVATION",
            reservation_ids=(" ",),
        )


def test_wrong_safe_tier_option_pair_and_duplicate_rule_ids_fail_closed():
    current = state()
    attack = attack_spec(982)
    end = end_spec()
    legal = options_for(attack, end)
    attack_as_pass = proposal(
        current,
        legal,
        attack,
        "ATTACK_AS_PASS",
        tier=ResolverTier.PASS,
    )
    end_as_attack = proposal(
        current,
        legal,
        end,
        "END_AS_ATTACK",
        tier=ResolverTier.RESOURCE_PRESERVING_FALLBACK,
    )
    duplicate_one = proposal(current, legal, attack, "DUPLICATE_RULE")
    duplicate_two = proposal(current, legal, end, "DUPLICATE_RULE")

    resolution = resolve_proposals(
        current,
        legal,
        ResourceLedger(()),
        (attack_as_pass, end_as_attack, duplicate_one, duplicate_two),
    )

    assert "PROFILE_OPTION_TYPE_FORBIDDEN" in rejection_for(
        resolution,
        "ATTACK_AS_PASS",
    ).reasons
    assert "PROFILE_OPTION_TYPE_FORBIDDEN" in rejection_for(
        resolution,
        "END_AS_ATTACK",
    ).reasons
    duplicate_rejections = [
        value for value in resolution.rejections if value.rule_id == "DUPLICATE_RULE"
    ]
    assert len(duplicate_rejections) == 2
    assert all("DUPLICATE_RULE_ID" in value.reasons for value in duplicate_rejections)
    assert resolution.selected is None


def test_resolver_does_not_synthesize_pass_when_every_proposal_is_rejected():
    current = state()
    attack = attack_spec(982)
    legal = options_for(attack)
    invalid = proposal(
        current,
        legal,
        attack,
        "INVALID_ONLY",
        tier=ResolverTier.EXACT_WIN_NOW,
    )

    resolution = resolve_proposals(
        current,
        legal,
        ResourceLedger(()),
        (invalid,),
    )

    assert resolution.selected is None
    assert resolution.bound_action is None
    assert resolution.stats.accepted == 0
    assert resolution.stats.rejected == 1


def test_proposal_structural_values_fail_closed():
    current = state()
    attack = attack_spec(982)
    legal = options_for(attack)
    proof = safe_fallback_proof(current, legal, attack, "STRUCTURAL")

    with pytest.raises(ValueError, match="rule_id"):
        Proposal(
            rule_id=" ",
            tier=ResolverTier.RESOURCE_PRESERVING_FALLBACK,
            action_spec=attack,
            certificate_kind=CertificateKind.SAFE_FALLBACK,
            proof=proof,
            deterministic_tiebreak=(int(OptionType.ATTACK), 982),
        )
    with pytest.raises(ValueError, match="exact integers or strings"):
        Proposal(
            rule_id="BOOL_TIEBREAK",
            tier=ResolverTier.RESOURCE_PRESERVING_FALLBACK,
            action_spec=attack,
            certificate_kind=CertificateKind.SAFE_FALLBACK,
            proof=proof,
            deterministic_tiebreak=(True,),
        )
