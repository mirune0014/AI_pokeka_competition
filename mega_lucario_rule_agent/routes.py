"""Finite, checked route enumeration for the Mega Lucario deck."""

from __future__ import annotations

import hashlib
import json
from typing import Sequence, Tuple

try:  # Package import in tests.
    from .attack_outcomes import BoundAttackOutcomeTable
    from .certificates import (
        CertificateKind,
        attack_outcome_proof,
        basic_bench_proof,
        first_turn_riolu_attach_proof,
        poke_pad_core_eligible_classes,
        poke_pad_core_formation_proof,
    )
    from .features import DeckFeatures
    from .public_effects import PublicEffectRegistry
    from .resource_ledger import (
        MANUAL_ATTACH_ENERGY_RESERVATION_ID,
        prove_deck_availability_from_state,
    )
    from .resolver import (
        Proposal,
        ResourceCost,
        ResolverTier,
        canonical_proposal_tiebreak,
    )
    from .state_view import ActionSpec, OptionType, PublicState, SemanticOption
    from .transactions import build_poke_pad_core_search_plan
except ImportError:  # Flat submission import from main.py.
    from attack_outcomes import BoundAttackOutcomeTable
    from certificates import (
        CertificateKind,
        attack_outcome_proof,
        basic_bench_proof,
        first_turn_riolu_attach_proof,
        poke_pad_core_eligible_classes,
        poke_pad_core_formation_proof,
    )
    from features import DeckFeatures
    from public_effects import PublicEffectRegistry
    from resource_ledger import (
        MANUAL_ATTACH_ENERGY_RESERVATION_ID,
        prove_deck_availability_from_state,
    )
    from resolver import (
        Proposal,
        ResourceCost,
        ResolverTier,
        canonical_proposal_tiebreak,
    )
    from state_view import ActionSpec, OptionType, PublicState, SemanticOption
    from transactions import build_poke_pad_core_search_plan


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


__all__ = [
    "enumerate_attack_routes",
    "enumerate_basic_bench_routes",
    "enumerate_first_turn_riolu_attach_routes",
    "enumerate_poke_pad_core_search_routes",
]
