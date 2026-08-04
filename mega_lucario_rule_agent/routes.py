"""Finite, checked route enumeration for the Mega Lucario deck."""

from __future__ import annotations

import hashlib
import json
from math import ceil
from typing import Sequence, Tuple

try:  # Package import in tests.
    from .attack_outcomes import BoundAttackOutcomeTable
    from .certificates import (
        CertificateKind,
        ACTIVE_ATTACK_COMPLETION_RULE_ID,
        active_post_attach_attack_completion_proof,
        attack_outcome_proof,
        deck_rule_proof,
        basic_bench_proof,
        first_turn_riolu_attach_proof,
        poke_pad_core_eligible_classes,
        poke_pad_core_formation_proof,
    )
    from .features import DeckFeatures, PublicMatchupFlag
    from .public_effects import PublicEffectRegistry
    from .resource_ledger import (
        MANUAL_ATTACH_ENERGY_RESERVATION_ID,
        ACTIVE_ATTACK_COMPLETION_RESERVATION_ID,
        prove_deck_availability_from_state,
    )
    from .resolver import (
        Proposal,
        ResourceCost,
        ResolverTier,
        canonical_proposal_tiebreak,
    )
    from .state_view import (
        ActionSpec,
        AreaType,
        OptionType,
        PhysicalRef,
        PublicState,
        SemanticOption,
    )
    from .transactions import (
        build_aura_jab_plan,
        build_deck_search_plan,
        build_lunar_cycle_plan,
        build_poke_pad_core_search_plan,
    )
except ImportError:  # Flat submission import from main.py.
    from attack_outcomes import BoundAttackOutcomeTable
    from certificates import (
        deck_rule_proof,
        CertificateKind,
        ACTIVE_ATTACK_COMPLETION_RULE_ID,
        active_post_attach_attack_completion_proof,
        attack_outcome_proof,
        basic_bench_proof,
        first_turn_riolu_attach_proof,
        poke_pad_core_eligible_classes,
        poke_pad_core_formation_proof,
    )
    from features import DeckFeatures, PublicMatchupFlag
    from public_effects import PublicEffectRegistry
    from resource_ledger import (
        MANUAL_ATTACH_ENERGY_RESERVATION_ID,
        ACTIVE_ATTACK_COMPLETION_RESERVATION_ID,
        prove_deck_availability_from_state,
    )
    from resolver import (
        Proposal,
        ResourceCost,
        ResolverTier,
        canonical_proposal_tiebreak,
    )
    from state_view import (
        ActionSpec,
        AreaType,
        OptionType,
        PhysicalRef,
        PublicState,
        SemanticOption,
    )
    from transactions import (
        build_aura_jab_plan,
        build_deck_search_plan,
        build_lunar_cycle_plan,
        build_poke_pad_core_search_plan,
    )


_ATTACK_TIERS = {
    CertificateKind.WIN_NOW: ResolverTier.EXACT_WIN_NOW,
    CertificateKind.PRIZE_GAIN_NOW: ResolverTier.EXACT_CURRENT_TURN_PRIZE,
    CertificateKind.ATTACK_COMPLETION: ResolverTier.BEST_CERTIFIED_ATTACK,
}


def _semantic_key_suffix(action_spec: ActionSpec) -> str:
    payload = json.dumps(
        action_spec.canonical(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]


def enumerate_attack_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Enumerate direct attacks whose result can be certified from public state."""

    if not isinstance(state, PublicState):
        raise ValueError("attack routes require a PublicState")
    if not isinstance(attack_outcomes, BoundAttackOutcomeTable):
        raise ValueError("attack routes require a checked attack outcome table")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("attack routes require a checked public effect registry")
    if not attack_outcomes.matches(state, legal_options, registry):
        return ()

    proposals = []
    for outcome in attack_outcomes.rows:
        action_spec = ActionSpec.single(outcome.option_key)
        try:
            proof = attack_outcome_proof(
                state,
                legal_options,
                registry,
                attack_outcomes,
                action_spec,
            )
        except ValueError:
            continue
        tier = _ATTACK_TIERS.get(proof.kind)
        if tier is None:
            continue
        proposals.append(
            Proposal(
                rule_id="DIRECT_{0}_{1}_{2}".format(
                    proof.kind.name,
                    outcome.attack_id,
                    _semantic_key_suffix(action_spec),
                ),
                tier=tier,
                action_spec=action_spec,
                certificate_kind=proof.kind,
                proof=proof,
                deterministic_tiebreak=canonical_proposal_tiebreak(
                    action_spec,
                    proof,
                ),
            )
        )
    return tuple(
        sorted(
            proposals,
            key=lambda proposal: (
                int(proposal.tier),
                proposal.rule_id,
                proposal.action_spec.canonical(),
            ),
        )
    )


def enumerate_basic_bench_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Enumerate only role-improving, flex-slot-safe Basic placements."""

    if not isinstance(state, PublicState):
        raise ValueError("Basic Bench routes require a PublicState")
    if not isinstance(features, DeckFeatures):
        raise ValueError("Basic Bench routes require checked DeckFeatures")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("Basic Bench routes require a checked registry")
    if not features.matches(state, legal_options, registry):
        return ()

    proposals = []
    for option in legal_options:
        if option.key.option_type != int(OptionType.PLAY):
            continue
        action_spec = ActionSpec.single(option.key)
        try:
            proof = basic_bench_proof(
                state,
                legal_options,
                registry,
                features,
                action_spec,
            )
        except ValueError:
            continue
        proposals.append(
            Proposal(
                rule_id="BASIC_BENCH_{0}_{1}_{2}".format(
                    proof.fact("purpose"),
                    option.key.card_id,
                    _semantic_key_suffix(action_spec),
                ),
                tier=ResolverTier.SAFE_ENGINE_COMPLETION,
                action_spec=action_spec,
                certificate_kind=proof.kind,
                proof=proof,
                deterministic_tiebreak=canonical_proposal_tiebreak(
                    action_spec,
                    proof,
                ),
            )
        )
    return tuple(
        sorted(
            proposals,
            key=lambda proposal: (
                int(proposal.tier),
                proposal.deterministic_tiebreak,
                proposal.rule_id,
                proposal.action_spec.canonical(),
            ),
        )
    )


def enumerate_first_turn_riolu_attach_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Emit at most one exact default-clause R-ATTACH-001 proposal."""

    if not isinstance(state, PublicState):
        raise ValueError("first-turn Riolu attach routes require a PublicState")
    if not isinstance(features, DeckFeatures):
        raise ValueError("first-turn Riolu attach routes require DeckFeatures")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("first-turn Riolu attach routes require a checked registry")
    if not features.matches(state, legal_options, registry):
        return ()

    for option in legal_options:
        if option.key.option_type != int(OptionType.ATTACH):
            continue
        action_spec = ActionSpec.single(option.key)
        try:
            proof = first_turn_riolu_attach_proof(
                state,
                legal_options,
                registry,
                features,
                action_spec,
            )
        except ValueError:
            continue
        source_refs = tuple(
            ref_value
            for ref_value in state.own.hand_refs
            if ref_value.sort_key() == proof.fact("source_ref")
        )
        if len(source_refs) != 1:
            continue
        proposal = Proposal(
            rule_id="R_ATTACH_001_{0}".format(
                _semantic_key_suffix(action_spec),
            ),
            tier=ResolverTier.ROUTE_CRITICAL_MANUAL_ATTACH,
            action_spec=action_spec,
            certificate_kind=CertificateKind.FIRST_ATTACK_ACCELERATION,
            proof=proof,
            resource_cost=ResourceCost(source_refs),
            reservation_ids=(MANUAL_ATTACH_ENERGY_RESERVATION_ID,),
            deterministic_tiebreak=canonical_proposal_tiebreak(
                action_spec,
                proof,
            ),
        )
        return (proposal,)
    return ()


def enumerate_active_attack_completion_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Emit at most one exact current-turn Active attack completion."""

    if not isinstance(state, PublicState):
        raise ValueError("Active attack completion routes require a PublicState")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("Active attack completion routes require a checked registry")
    for option in sorted(legal_options, key=lambda value: value.key.sort_key()):
        if option.key.option_type != int(OptionType.ATTACH):
            continue
        action_spec = ActionSpec.single(option.key)
        try:
            proof = active_post_attach_attack_completion_proof(
                state,
                legal_options,
                registry,
                action_spec,
            )
        except ValueError:
            continue
        source_refs = tuple(
            ref_value
            for ref_value in state.own.hand_refs
            if ref_value.sort_key() == proof.fact("source_ref")
        )
        if len(source_refs) != 1:
            continue
        proposal = Proposal(
            rule_id=ACTIVE_ATTACK_COMPLETION_RULE_ID,
            tier=ResolverTier.ATTACK_COMPLETION,
            action_spec=action_spec,
            certificate_kind=CertificateKind.ATTACK_COMPLETION,
            proof=proof,
            resource_cost=ResourceCost(source_refs),
            reservation_ids=(ACTIVE_ATTACK_COMPLETION_RESERVATION_ID,),
            deterministic_tiebreak=canonical_proposal_tiebreak(
                action_spec,
                proof,
            ),
        )
        return (proposal,)
    return ()


def enumerate_poke_pad_core_search_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Emit at most one closed Poke Pad core-formation transaction."""

    if not isinstance(state, PublicState):
        raise ValueError("Poke Pad routes require a PublicState")
    if not isinstance(features, DeckFeatures):
        raise ValueError("Poke Pad routes require checked DeckFeatures")
    if not isinstance(attack_outcomes, BoundAttackOutcomeTable):
        raise ValueError("Poke Pad routes require a checked attack table")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("Poke Pad routes require a checked registry")
    if not features.matches(state, legal_options, registry):
        return ()
    classes = poke_pad_core_eligible_classes(state)
    if not classes:
        return ()
    acceptable_ids = tuple(
        sorted(card_id for card_class in classes for card_id in card_class)
    )
    availability = prove_deck_availability_from_state(
        state,
        acceptable_ids,
        required_count=1,
    )
    if not availability.is_guaranteed:
        return ()
    for option in sorted(
        legal_options,
        key=lambda value: value.key.sort_key(),
    ):
        if option.key.option_type != int(OptionType.PLAY) or option.key.card_id != 1152:
            continue
        action_spec = ActionSpec.single(option.key)
        try:
            proof = poke_pad_core_formation_proof(
                state,
                legal_options,
                registry,
                features,
                attack_outcomes,
                availability,
                action_spec,
            )
        except ValueError:
            continue
        source_fact = proof.fact("source_ref")
        source_refs = tuple(
            ref_value
            for ref_value in state.own.hand_refs
            if ref_value.sort_key() == source_fact
        )
        if len(source_refs) != 1:
            continue
        transaction_plan = build_poke_pad_core_search_plan(
            state,
            source_refs[0],
            action_spec,
            classes,
            availability,
            proof.digest(),
        )
        return (
            Proposal(
                rule_id="R_SEARCH_POKE_PAD_CORE_FORMATION_V1",
                tier=ResolverTier.ROUTE_CRITICAL_SEARCH,
                action_spec=action_spec,
                certificate_kind=CertificateKind.RESOURCE_IMPROVEMENT,
                proof=proof,
                resource_cost=ResourceCost(source_refs),
                transaction_plan=transaction_plan,
                deterministic_tiebreak=canonical_proposal_tiebreak(
                    action_spec,
                    proof,
                ),
            ),
        )
    return ()


def _exact_hand_ref(state: PublicState, option: SemanticOption) -> PhysicalRef | None:
    key = option.key
    matches = tuple(
        ref_value
        for ref_value in state.own.hand_refs
        if ref_value.card_id == key.card_id
        and ref_value.serial == key.card_serial
        and ref_value.owner == state.seat
        and ref_value.zone == int(AreaType.HAND)
    )
    return matches[0] if len(matches) == 1 else None


def _board_pokemon_for_option(state: PublicState, option: SemanticOption):
    key = option.key
    return next(
        (
            pokemon
            for pokemon in state.own.active + state.own.bench
            if pokemon.ref.zone == key.target_zone
            and pokemon.ref.lineage_serial == key.target_lineage_serial
        ),
        None,
    )


def _in_play_source_ref(
    state: PublicState, option: SemanticOption
) -> PhysicalRef | None:
    key = option.key
    matches = tuple(
        pokemon.ref
        for pokemon in state.own.active + state.own.bench
        if pokemon.ref.card_id == key.card_id
        and pokemon.ref.serial == key.card_serial
        and pokemon.ref.zone == key.source_zone
        and pokemon.ref.lineage_serial == key.source_lineage_serial
    )
    return matches[0] if len(matches) == 1 else None


def enumerate_fighting_gong_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Search only a guaranteed route-critical Fighting target."""

    if not features.matches(state, legal_options, registry):
        return ()
    hand_ids = tuple(ref_value.card_id for ref_value in state.own.hand_refs)
    active_deficit = next(
        (
            value.deficit_now
            for value in features.attack_energy_deficit_by_target
            if state.own_active is not None and value.target_ref == state.own_active.ref
        ),
        None,
    )
    classes: Tuple[Tuple[int, ...], ...] = ()
    purpose = ""
    if (
        not features.ready_now
        and not state.energy_attached
        and features.hand_fighting_energy_count == 0
        and active_deficit == 1
    ):
        classes = ((6,),)
        purpose = "CURRENT_ATTACK_ENERGY"
    elif features.missing_engine_card_ids:
        classes = tuple((card_id,) for card_id in features.missing_engine_card_ids)
        purpose = "MISSING_ENGINE"
    elif features.lucario_line_count == 0 and 677 not in hand_ids:
        classes = ((677,),)
        purpose = "FIRST_RIOLU"
    elif (
        features.hariyama_line_count == 0
        and 673 not in hand_ids
        and PublicMatchupFlag.EX_DAMAGE_PREVENTION in features.public_flags
    ):
        classes = ((673,),)
        purpose = "FIRST_MAKUHITA"
    if not classes or state.own.deck_count <= 1:
        return ()
    acceptable_ids = tuple(sorted(card_id for values in classes for card_id in values))
    availability = prove_deck_availability_from_state(
        state,
        acceptable_ids,
        required_count=1,
    )
    if not availability.is_guaranteed:
        return ()
    for option in sorted(legal_options, key=lambda value: value.key.sort_key()):
        if option.key.option_type != int(OptionType.PLAY) or option.key.card_id != 1142:
            continue
        source_ref = _exact_hand_ref(state, option)
        if source_ref is None:
            continue
        action_spec = ActionSpec.single(option.key)
        proof = deck_rule_proof(
            state,
            legal_options,
            registry,
            features,
            action_spec,
            route_code="R_SEARCH_FIGHTING_GONG_ROUTE_CRITICAL_V1",
            kind=CertificateKind.RESOURCE_IMPROVEMENT,
            facts={
                "route_priority": 0,
                "purpose": purpose,
                "ordered_card_id_classes": classes,
                "availability": availability.canonical(),
                "source_ref": source_ref,
            },
        )
        plan = build_deck_search_plan(
            state,
            source_ref,
            action_spec,
            classes,
            availability,
            proof.digest(),
        )
        return (
            Proposal(
                rule_id="R_SEARCH_FIGHTING_GONG_ROUTE_CRITICAL_V1",
                tier=ResolverTier.ROUTE_CRITICAL_SEARCH,
                action_spec=action_spec,
                certificate_kind=proof.kind,
                proof=proof,
                resource_cost=ResourceCost((source_ref,)),
                transaction_plan=plan,
                deterministic_tiebreak=canonical_proposal_tiebreak(action_spec, proof),
            ),
        )
    return ()


def enumerate_evolution_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Prefer attack-ready/protective Mega evolution, with a non-ex escape."""

    if not features.matches(state, legal_options, registry):
        return ()
    mega_proposals = []
    hariyama_proposals = []
    for option in sorted(legal_options, key=lambda value: value.key.sort_key()):
        if option.key.option_type != int(OptionType.EVOLVE):
            continue
        source_ref = _exact_hand_ref(state, option)
        target = _board_pokemon_for_option(state, option)
        if source_ref is None or target is None:
            continue
        action_spec = ActionSpec.single(option.key)
        if source_ref.card_id == 678 and target.ref.card_id == 677:
            active_ready = (
                target.ref.zone == int(AreaType.ACTIVE)
                and len(target.energy_refs) >= 1
                and not state.own.asleep
                and not state.own.paralyzed
            )
            spread_protection = (
                target.ref.zone == int(AreaType.BENCH)
                and features.public_bench_damage_threat is True
            )
            if not active_ready and not spread_protection:
                continue
            if features.opponent_prizes_remaining <= 3:
                active_target = features.opponent_active
                immediate_prize = (
                    active_ready
                    and features.public_damage_prevention is False
                    and active_target is not None
                    and active_target.remaining_hp <= 130
                )
                if not immediate_prize:
                    continue
            kind = (
                CertificateKind.ATTACK_COMPLETION
                if active_ready
                else CertificateKind.FIRST_ATTACK_ACCELERATION
            )
            proof = deck_rule_proof(
                state,
                legal_options,
                registry,
                features,
                action_spec,
                route_code="R_EVO_MEGA_ATTACK_OR_PROTECTION_V1",
                kind=kind,
                facts={
                    "route_priority": 0 if active_ready else 1,
                    "source_ref": source_ref,
                    "target_ref": target.ref,
                    "same_turn_attack": active_ready,
                    "spread_protection": spread_protection,
                    "opponent_prizes_remaining": features.opponent_prizes_remaining,
                },
            )
            mega_proposals.append(
                Proposal(
                    rule_id="R_EVO_MEGA_{0}".format(_semantic_key_suffix(action_spec)),
                    tier=ResolverTier.CERTIFIED_EVOLUTION,
                    action_spec=action_spec,
                    certificate_kind=proof.kind,
                    proof=proof,
                    resource_cost=ResourceCost((source_ref,)),
                    deterministic_tiebreak=canonical_proposal_tiebreak(
                        action_spec, proof
                    ),
                )
            )
        elif (
            source_ref.card_id == 674
            and target.ref.card_id == 673
            and PublicMatchupFlag.EX_DAMAGE_PREVENTION in features.public_flags
        ):
            proof = deck_rule_proof(
                state,
                legal_options,
                registry,
                features,
                action_spec,
                route_code="R_EVO_HARIYAMA_NONEX_ESCAPE_V1",
                kind=CertificateKind.FIRST_ATTACK_ACCELERATION,
                facts={
                    "route_priority": 2,
                    "source_ref": source_ref,
                    "target_ref": target.ref,
                    "ex_damage_prevention": True,
                },
            )
            hariyama_proposals.append(
                Proposal(
                    rule_id="R_EVO_HARIYAMA_{0}".format(
                        _semantic_key_suffix(action_spec)
                    ),
                    tier=ResolverTier.CERTIFIED_EVOLUTION,
                    action_spec=action_spec,
                    certificate_kind=proof.kind,
                    proof=proof,
                    resource_cost=ResourceCost((source_ref,)),
                    deterministic_tiebreak=canonical_proposal_tiebreak(
                        action_spec, proof
                    ),
                )
            )
    return tuple(mega_proposals or hariyama_proposals)


def enumerate_aura_continuity_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Concentrate Aura Jab Energy on one incomplete Bench attacker."""

    if not features.matches(
        state, legal_options, registry
    ) or not attack_outcomes.matches(state, legal_options, registry):
        return ()
    aura_option = next(
        (
            option
            for option in legal_options
            if option.key.option_type == int(OptionType.ATTACK)
            and option.key.attack_id == 982
        ),
        None,
    )
    if aura_option is None:
        return ()
    outcome = attack_outcomes.get_for_option(aura_option.key)
    callback = None if outcome is None else outcome.callback
    if callback is None or not callback.requires_selection:
        return ()
    available = tuple(callback.available_source_refs[:3])
    if not available:
        return ()
    deficits = {
        value.target_ref: value.deficit_now
        for value in features.attack_energy_deficit_by_target
    }
    hand_ids = {ref_value.card_id for ref_value in state.own.hand_refs}
    ex_block = PublicMatchupFlag.EX_DAMAGE_PREVENTION in features.public_flags
    non_ex_ids = frozenset((673, 674, 675, 676, 677))
    normal_priority = {678: 0, 677: 1, 674: 2, 673: 3, 676: 4, 675: 5}
    blocked_priority = {674: 0, 673: 1, 676: 2, 675: 3, 677: 4}
    candidates = []
    for target_ref in callback.eligible_target_refs:
        deficit = deficits.get(target_ref)
        if target_ref.card_id == 673 and 674 in hand_ids:
            attached = next(
                (
                    len(pokemon.energy_refs)
                    for pokemon in state.own.active + state.own.bench
                    if pokemon.ref == target_ref
                ),
                0,
            )
            deficit = max(0, 3 - attached)
        if (
            not isinstance(deficit, int)
            or isinstance(deficit, bool)
            or deficit <= 0
            or deficit > len(available)
            or deficit > 3
        ):
            continue
        if ex_block and target_ref.card_id not in non_ex_ids:
            continue
        priority = (blocked_priority if ex_block else normal_priority).get(
            target_ref.card_id,
            99,
        )
        candidates.append((priority, deficit, target_ref.sort_key(), target_ref))
    if not candidates:
        return ()
    _, count, _, target_ref = min(candidates)
    energy_refs = available[:count]
    action_spec = ActionSpec.single(aura_option.key)
    if outcome.exact_game_win:
        kind = CertificateKind.WIN_NOW
        tier = ResolverTier.EXACT_WIN_NOW
        guaranteed_prizes = int(outcome.prizes_taken or 0)
    elif (
        outcome.exact_ko
        and isinstance(outcome.prizes_taken, int)
        and outcome.prizes_taken > 0
    ):
        kind = CertificateKind.PRIZE_GAIN_NOW
        tier = ResolverTier.EXACT_CURRENT_TURN_PRIZE
        guaranteed_prizes = int(outcome.prizes_taken)
    else:
        kind = CertificateKind.SAME_ATTACK_PLUS_CONTINUITY
        tier = ResolverTier.SAME_ATTACK_PLUS_CONTINUITY
        guaranteed_prizes = 0
    proof = deck_rule_proof(
        state,
        legal_options,
        registry,
        features,
        action_spec,
        route_code="R_AURA_JAB_CONCENTRATED_COMPLETION_V1",
        kind=kind,
        guaranteed_prizes=guaranteed_prizes,
        facts={
            "route_priority": 0,
            "target_ref": target_ref,
            "energy_refs": tuple(ref_value.sort_key() for ref_value in energy_refs),
            "energy_count": count,
            "ex_damage_prevention": ex_block,
            "exact_ko": outcome.exact_ko,
        },
    )
    plan = build_aura_jab_plan(
        state,
        action_spec,
        energy_refs,
        target_ref,
        proof.digest(),
    )
    return (
        Proposal(
            rule_id="R_AURA_JAB_CONCENTRATED_COMPLETION_V1",
            tier=tier,
            action_spec=action_spec,
            certificate_kind=proof.kind,
            proof=proof,
            transaction_plan=plan,
            deterministic_tiebreak=canonical_proposal_tiebreak(action_spec, proof),
        ),
    )


def enumerate_minimal_ppp_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Play one PPP only while progressing toward the exact minimal breakpoint."""

    if (
        not features.matches(state, legal_options, registry)
        or not attack_outcomes.matches(state, legal_options, registry)
        or not isinstance(state.ppp_count, int)
        or isinstance(state.ppp_count, bool)
    ):
        return ()
    ppp_options = tuple(
        sorted(
            (
                option
                for option in legal_options
                if option.key.option_type == int(OptionType.PLAY)
                and option.key.card_id == 1141
            ),
            key=lambda value: value.key.sort_key(),
        )
    )
    if not ppp_options or any(outcome.exact_ko for outcome in attack_outcomes.rows):
        return ()
    candidates = []
    for outcome in attack_outcomes.rows:
        if (
            not outcome.exact_damage
            or outcome.final_damage is None
            or outcome.final_damage <= 0
            or outcome.before_weakness is None
            or outcome.weakness_multiplier is None
            or outcome.resistance_reduction is None
            or outcome.field_reduction is None
            or outcome.damage_before_prevention != outcome.final_damage
            or outcome.damage_before_ko_prevention != outcome.final_damage
            or outcome.prevention_effects
        ):
            continue
        old_attacks = ceil(outcome.target_starting_hp / outcome.final_damage)
        for additional in range(1, len(ppp_options) + 1):
            before = outcome.before_weakness + 30 * additional
            after = max(
                0,
                before * outcome.weakness_multiplier - outcome.resistance_reduction,
            )
            new_damage = max(0, after - outcome.field_reduction)
            if new_damage <= 0:
                continue
            new_attacks = ceil(outcome.target_starting_hp / new_damage)
            is_ko = new_damage >= outcome.target_starting_hp
            if not is_ko and new_attacks >= old_attacks:
                continue
            candidates.append(
                (
                    0 if is_ko else 1,
                    additional,
                    new_attacks,
                    outcome.attack_id,
                    new_damage,
                    old_attacks,
                )
            )
            break
    if not candidates:
        return ()
    ko_rank, required, new_attacks, attack_id, new_damage, old_attacks = min(candidates)
    option = ppp_options[0]
    source_ref = _exact_hand_ref(state, option)
    if source_ref is None:
        return ()
    action_spec = ActionSpec.single(option.key)
    proof = deck_rule_proof(
        state,
        legal_options,
        registry,
        features,
        action_spec,
        route_code="R_PPP_EXACT_MINIMUM_BREAKPOINT_V1",
        kind=CertificateKind.ATTACK_COMPLETION,
        facts={
            "route_priority": required,
            "attack_id": attack_id,
            "additional_ppp_required": required,
            "new_damage": new_damage,
            "old_attacks_needed": old_attacks,
            "new_attacks_needed": new_attacks,
            "reaches_ko": ko_rank == 0,
            "source_ref": source_ref,
        },
    )
    return (
        Proposal(
            rule_id="R_PPP_EXACT_MINIMUM_BREAKPOINT_V1",
            tier=ResolverTier.MINIMAL_PPP,
            action_spec=action_spec,
            certificate_kind=proof.kind,
            proof=proof,
            resource_cost=ResourceCost((source_ref,)),
            deterministic_tiebreak=canonical_proposal_tiebreak(action_spec, proof),
        ),
    )


def enumerate_safe_draw_supporter_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Emit safe Lunar/Judge/Lillie prefixes and replan after their draw."""

    if not features.matches(state, legal_options, registry):
        return ()
    proposals = []
    if features.lunar_cycle_feasible:
        energies = tuple(
            sorted(
                (
                    ref_value
                    for ref_value in state.own.hand_refs
                    if ref_value.card_id == 6
                ),
                key=lambda value: value.sort_key(),
            )
        )
        reserve = int(not state.energy_attached and not features.ready_now)
        if len(energies) > reserve:
            energy_ref = energies[-1]
            for option in sorted(legal_options, key=lambda value: value.key.sort_key()):
                if (
                    option.key.option_type
                    not in (int(OptionType.ABILITY), int(OptionType.SKILL))
                    or option.key.card_id != 675
                ):
                    continue
                source_ref = _in_play_source_ref(state, option)
                if source_ref is None:
                    continue
                action_spec = ActionSpec.single(option.key)
                proof = deck_rule_proof(
                    state,
                    legal_options,
                    registry,
                    features,
                    action_spec,
                    route_code="R_LUNAR_SAFE_PREFIX_V1",
                    kind=CertificateKind.RESOURCE_IMPROVEMENT,
                    facts={
                        "route_priority": 0,
                        "source_ref": source_ref,
                        "energy_ref": energy_ref,
                        "draw_buffer_after": features.draw_buffer_after_plan,
                        "manual_attach_reserve": reserve,
                    },
                )
                plan = build_lunar_cycle_plan(
                    state,
                    source_ref,
                    energy_ref,
                    action_spec,
                    proof.digest(),
                )
                proposals.append(
                    Proposal(
                        rule_id="R_LUNAR_SAFE_PREFIX_V1",
                        tier=ResolverTier.SAFE_DRAW_OR_DISRUPTION,
                        action_spec=action_spec,
                        certificate_kind=proof.kind,
                        proof=proof,
                        resource_cost=ResourceCost((energy_ref,)),
                        transaction_plan=plan,
                        deterministic_tiebreak=canonical_proposal_tiebreak(
                            action_spec, proof
                        ),
                    )
                )
                break

    critical_action_pending = any(
        (
            option.key.option_type == int(OptionType.PLAY)
            and option.key.card_id in (1182, 1229)
        )
        for option in legal_options
    )
    if state.supporter_played or critical_action_pending:
        return tuple(proposals)
    hand_ids = tuple(ref_value.card_id for ref_value in state.own.hand_refs)
    missing_role = (
        bool(features.missing_engine_card_ids)
        or features.lucario_line_count == 0
        or (features.hand_fighting_energy_count == 0 and not features.ready_now)
        or (
            677
            in tuple(
                pokemon.ref.card_id for pokemon in state.own.active + state.own.bench
            )
            and 678 not in hand_ids
        )
    )
    supporter_choice = None
    supporter_code = ""
    route_priority = 99
    if (
        features.opponent_hand_count >= 8
        and state.own.hand_count <= 4
        and state.own.deck_count >= 5
    ):
        supporter_choice = 1213
        supporter_code = "R_SUPPORTER_JUDGE_LARGE_PUBLIC_HAND_V1"
        route_priority = 1
    else:
        lillie_target = 8 if state.own.prize_count == 6 else 6
        if (
            missing_role
            and state.own.hand_count <= lillie_target - 2
            and state.own.deck_count >= lillie_target + 1
        ):
            supporter_choice = 1227
            supporter_code = "R_SUPPORTER_LILLIE_ROLE_REBUILD_V1"
            route_priority = 2
    if supporter_choice is None:
        return tuple(proposals)
    option = next(
        (
            value
            for value in sorted(legal_options, key=lambda row: row.key.sort_key())
            if value.key.option_type == int(OptionType.PLAY)
            and value.key.card_id == supporter_choice
        ),
        None,
    )
    if option is None:
        return tuple(proposals)
    source_ref = _exact_hand_ref(state, option)
    if source_ref is None:
        return tuple(proposals)
    action_spec = ActionSpec.single(option.key)
    proof = deck_rule_proof(
        state,
        legal_options,
        registry,
        features,
        action_spec,
        route_code=supporter_code,
        kind=CertificateKind.RESOURCE_IMPROVEMENT,
        facts={
            "route_priority": route_priority,
            "source_ref": source_ref,
            "own_hand_count": state.own.hand_count,
            "opponent_hand_count": features.opponent_hand_count,
            "missing_role": missing_role,
            "draw_buffer_after": features.draw_buffer_after_plan,
        },
    )
    proposals.append(
        Proposal(
            rule_id=supporter_code,
            tier=ResolverTier.SAFE_DRAW_OR_DISRUPTION,
            action_spec=action_spec,
            certificate_kind=proof.kind,
            proof=proof,
            resource_cost=ResourceCost((source_ref,)),
            deterministic_tiebreak=canonical_proposal_tiebreak(action_spec, proof),
        )
    )
    return tuple(proposals)


def enumerate_requirement_routes(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
) -> Tuple[Proposal, ...]:
    """Enumerate the integrated high-frequency requirement routes."""

    proposals = []
    proposals.extend(
        enumerate_aura_continuity_routes(
            state, legal_options, features, attack_outcomes, registry
        )
    )
    proposals.extend(
        enumerate_evolution_routes(state, legal_options, features, registry)
    )
    proposals.extend(
        enumerate_fighting_gong_routes(state, legal_options, features, registry)
    )
    proposals.extend(
        enumerate_safe_draw_supporter_routes(state, legal_options, features, registry)
    )
    proposals.extend(
        enumerate_minimal_ppp_routes(
            state, legal_options, features, attack_outcomes, registry
        )
    )
    return tuple(proposals)


__all__ = [
    "enumerate_active_attack_completion_routes",
    "enumerate_attack_routes",
    "enumerate_aura_continuity_routes",
    "enumerate_basic_bench_routes",
    "enumerate_evolution_routes",
    "enumerate_fighting_gong_routes",
    "enumerate_first_turn_riolu_attach_routes",
    "enumerate_minimal_ppp_routes",
    "enumerate_poke_pad_core_search_routes",
    "enumerate_requirement_routes",
    "enumerate_safe_draw_supporter_routes",
]
