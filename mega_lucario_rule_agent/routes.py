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
    )
    from .features import DeckFeatures
    from .public_effects import PublicEffectRegistry
    from .resolver import (
        Proposal,
        ResolverTier,
        canonical_proposal_tiebreak,
    )
    from .state_view import ActionSpec, OptionType, PublicState, SemanticOption
except ImportError:  # Flat submission import from main.py.
    from attack_outcomes import BoundAttackOutcomeTable
    from certificates import (
        CertificateKind,
        attack_outcome_proof,
        basic_bench_proof,
    )
    from features import DeckFeatures
    from public_effects import PublicEffectRegistry
    from resolver import Proposal, ResolverTier, canonical_proposal_tiebreak
    from state_view import ActionSpec, OptionType, PublicState, SemanticOption


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


__all__ = ["enumerate_attack_routes", "enumerate_basic_bench_routes"]
