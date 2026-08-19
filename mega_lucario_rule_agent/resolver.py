"""Single deterministic resolver for checked rule proposals.

The frozen baseline intentionally accepts only live-bound safe fallback
certificates.  Enabling a stronger route therefore requires an explicit
certificate schema, issuer, and resolver-profile code change.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field as dataclass_field
from enum import Enum, IntEnum
import hashlib
import json
from typing import Any, Optional, Sequence, Tuple

try:  # Package import in tests.
    from .attack_outcomes import (
        active_attack_completion_registry_audit,
        build_attack_outcome_table,
    )
    from .certificates import (
        CertificateKind,
        ACTIVE_ATTACK_COMPLETION_COVERAGE,
        ACTIVE_ATTACK_COMPLETION_RULE_ID,
        ACTIVE_ATTACK_COMPLETION_UNRESOLVED,
        CertificateProof,
        ProofSchema,
        active_post_attach_attack_completion_proof,
        basic_bench_proof,
        deck_rule_proof,
        first_turn_riolu_attach_proof,
        legal_options_fingerprint,
        poke_pad_core_eligible_classes,
        poke_pad_core_formation_proof,
        verify_cape_survival_certificate,
        verify_gust_dominance_certificate,
        verify_wally_survival_certificate,
        wally_higher_priority_supporter_status,
    )
    from .features import build_deck_features
    from .public_effects import PublicEffectRegistry
    from .resource_ledger import (
        MANUAL_ATTACH_ENERGY_RESERVATION_ID,
        ACTIVE_ATTACK_COMPLETION_RESERVATION_ID,
        ReservationKind,
        ResourceLedger,
        ResourceLedgerError,
        prove_deck_availability_from_state,
    )
    from .state_view import (
        ActionSpec,
        OptionType,
        PhysicalRef,
        PublicState,
        SemanticBindError,
        SemanticOption,
        public_state_fingerprint,
    )
    from .transactions import (
        TransactionPlan,
        build_boss_gust_plan,
        build_hariyama_gust_plan,
        build_poke_pad_core_search_plan,
        build_wally_plan,
    )
except ImportError:  # Flat submission import from main.py.
    from attack_outcomes import (
        active_attack_completion_registry_audit,
        build_attack_outcome_table,
    )
    from certificates import (
        CertificateKind,
        ACTIVE_ATTACK_COMPLETION_COVERAGE,
        ACTIVE_ATTACK_COMPLETION_RULE_ID,
        ACTIVE_ATTACK_COMPLETION_UNRESOLVED,
        CertificateProof,
        ProofSchema,
        active_post_attach_attack_completion_proof,
        basic_bench_proof,
        deck_rule_proof,
        first_turn_riolu_attach_proof,
        legal_options_fingerprint,
        poke_pad_core_eligible_classes,
        poke_pad_core_formation_proof,
        verify_cape_survival_certificate,
        verify_gust_dominance_certificate,
        verify_wally_survival_certificate,
        wally_higher_priority_supporter_status,
    )
    from features import build_deck_features
    from public_effects import PublicEffectRegistry
    from resource_ledger import (
        MANUAL_ATTACH_ENERGY_RESERVATION_ID,
        ACTIVE_ATTACK_COMPLETION_RESERVATION_ID,
        ReservationKind,
        ResourceLedger,
        ResourceLedgerError,
        prove_deck_availability_from_state,
    )
    from state_view import (
        ActionSpec,
        OptionType,
        PhysicalRef,
        PublicState,
        SemanticBindError,
        SemanticOption,
        public_state_fingerprint,
    )
    from transactions import (
        TransactionPlan,
        build_boss_gust_plan,
        build_hariyama_gust_plan,
        build_poke_pad_core_search_plan,
        build_wally_plan,
    )


class ResolverTier(IntEnum):
    ACTIVE_TRANSACTION_CONTINUATION = 1
    FORCED_OR_SETUP = 2
    EXACT_WIN_NOW = 3
    DENY_CERTAIN_LOSS = 4
    TERMINAL_OR_SUPERIOR_GUST = 5
    SURVIVAL_CRITICAL_WALLY = 6
    STRICTLY_SUPERIOR_GUST = 7
    EXACT_CURRENT_TURN_PRIZE = 8
    SAME_ATTACK_PLUS_CONTINUITY = 9
    ATTACK_COMPLETION = 10
    CERTIFIED_EVOLUTION = 11
    ROUTE_CRITICAL_SEARCH = 12
    ROUTE_CRITICAL_MANUAL_ATTACH = 13
    SAFE_DRAW_OR_DISRUPTION = 14
    CERTIFIED_SURVIVAL = 15
    MINIMAL_PPP = 16
    BEST_CERTIFIED_ATTACK = 17
    SAFE_ENGINE_COMPLETION = 18
    RESOURCE_PRESERVING_FALLBACK = 19
    PASS = 20


class MetricSchema(str, Enum):
    NO_CLAIMS_V1 = "no_claims_v1"


def _optional_nonnegative_int(value: Optional[int], name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(
            "{0} must be None or a non-negative exact integer".format(name)
        )


@dataclass(frozen=True)
class ResolverMetrics:
    schema: MetricSchema = MetricSchema.NO_CLAIMS_V1
    supporter_opportunity_cost: Optional[int] = None
    prize_liability_after: Optional[int] = None
    ready_attackers_after: Optional[int] = None
    draw_buffer_after: Optional[int] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema", MetricSchema(self.schema))
        _optional_nonnegative_int(
            self.supporter_opportunity_cost,
            "supporter_opportunity_cost",
        )
        _optional_nonnegative_int(self.prize_liability_after, "prize_liability_after")
        _optional_nonnegative_int(self.ready_attackers_after, "ready_attackers_after")
        _optional_nonnegative_int(self.draw_buffer_after, "draw_buffer_after")

    @property
    def has_claims(self) -> bool:
        return any(
            value is not None
            for value in (
                self.supporter_opportunity_cost,
                self.prize_liability_after,
                self.ready_attackers_after,
                self.draw_buffer_after,
            )
        )


def _require_exact_ref(ref_value: PhysicalRef) -> None:
    if not isinstance(ref_value, PhysicalRef):
        raise ValueError("resource costs must contain PhysicalRef values")
    if (
        isinstance(ref_value.card_id, bool)
        or not isinstance(ref_value.card_id, int)
        or ref_value.card_id <= 0
        or isinstance(ref_value.serial, bool)
        or not isinstance(ref_value.serial, int)
        or ref_value.serial < 0
        or isinstance(ref_value.owner, bool)
        or not isinstance(ref_value.owner, int)
        or ref_value.owner not in (0, 1)
        or isinstance(ref_value.zone, bool)
        or not isinstance(ref_value.zone, int)
        or ref_value.zone <= 0
    ):
        raise ValueError("resource costs require exact card, serial, owner, and zone")


@dataclass(frozen=True)
class ResourceCost:
    irreversible_refs: Tuple[PhysicalRef, ...] = ()

    def __post_init__(self) -> None:
        refs = tuple(self.irreversible_refs)
        for ref_value in refs:
            _require_exact_ref(ref_value)
        identities = tuple((int(ref.owner), int(ref.serial)) for ref in refs)
        if len(set(identities)) != len(identities):
            raise ValueError("resource cost cannot repeat one physical card")
        object.__setattr__(
            self,
            "irreversible_refs",
            tuple(sorted(refs, key=lambda value: value.sort_key())),
        )


@dataclass(frozen=True)
class Proposal:
    rule_id: str
    tier: ResolverTier
    action_spec: ActionSpec
    certificate_kind: CertificateKind
    proof: CertificateProof
    resource_cost: ResourceCost = dataclass_field(default_factory=ResourceCost)
    reservation_ids: Tuple[str, ...] = ()
    transaction_plan: Optional[Any] = None
    metrics: ResolverMetrics = dataclass_field(default_factory=ResolverMetrics)
    deterministic_tiebreak: Tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        if (
            not isinstance(self.rule_id, str)
            or not self.rule_id
            or self.rule_id != self.rule_id.strip()
        ):
            raise ValueError("proposal rule_id must be a non-empty trimmed string")
        if not isinstance(self.action_spec, ActionSpec):
            raise ValueError("proposal action_spec must be an ActionSpec")
        if not isinstance(self.proof, CertificateProof):
            raise ValueError("proposal proof must be a CertificateProof")
        if not isinstance(self.resource_cost, ResourceCost):
            raise ValueError("proposal resource_cost must be a ResourceCost")
        reservation_ids = tuple(self.reservation_ids)
        if any(
            not isinstance(value, str) or not value or value != value.strip()
            for value in reservation_ids
        ):
            raise ValueError(
                "proposal reservation_ids must be non-empty trimmed strings"
            )
        if len(set(reservation_ids)) != len(reservation_ids):
            raise ValueError("proposal reservation_ids must be unique")
        if not isinstance(self.metrics, ResolverMetrics):
            raise ValueError("proposal metrics must be ResolverMetrics")
        tiebreak = tuple(self.deterministic_tiebreak)
        if any(
            isinstance(value, bool) or not isinstance(value, (int, str))
            for value in tiebreak
        ):
            raise ValueError(
                "deterministic_tiebreak must contain exact integers or strings"
            )
        object.__setattr__(self, "tier", ResolverTier(self.tier))
        object.__setattr__(
            self,
            "certificate_kind",
            CertificateKind(self.certificate_kind),
        )
        object.__setattr__(self, "reservation_ids", tuple(sorted(reservation_ids)))
        object.__setattr__(self, "deterministic_tiebreak", tiebreak)


@dataclass(frozen=True)
class ProposalRejection:
    proposal_digest: str
    rule_id: str
    action_digest: str
    reasons: Tuple[str, ...]


class ProposalDisposition(str, Enum):
    SELECTED = "SELECTED"
    VALID_NOT_SELECTED = "VALID_NOT_SELECTED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class ProposalEvaluation:
    proposal_digest: str
    rule_id: str
    action_digest: str
    disposition: ProposalDisposition
    reasons: Tuple[str, ...]


@dataclass(frozen=True)
class ResolutionStats:
    proposed: int
    accepted: int
    rejected: int


@dataclass(frozen=True)
class Resolution:
    selected: Optional[Proposal]
    bound_action: Optional[Tuple[int, ...]]
    rejections: Tuple[ProposalRejection, ...]
    evaluations: Tuple[ProposalEvaluation, ...]
    stats: ResolutionStats

    @property
    def has_selection(self) -> bool:
        return self.selected is not None


_ALLOWED_KINDS_BY_SCHEMA = {
    ProofSchema.SAFE_FALLBACK_V1: frozenset((CertificateKind.SAFE_FALLBACK,)),
    ProofSchema.ATTACK_OUTCOME_V1: frozenset(
        (
            CertificateKind.WIN_NOW,
            CertificateKind.PRIZE_GAIN_NOW,
            CertificateKind.ATTACK_COMPLETION,
        )
    ),
    ProofSchema.BASIC_BENCH_V1: frozenset(
        (
            CertificateKind.FIRST_ATTACK_ACCELERATION,
            CertificateKind.ENGINE_COMPLETION,
            CertificateKind.RESOURCE_IMPROVEMENT,
        )
    ),
    ProofSchema.POKE_PAD_CORE_FORMATION_V1: frozenset(
        (CertificateKind.RESOURCE_IMPROVEMENT,)
    ),
    ProofSchema.FIRST_TURN_RIOLU_ATTACH_V1: frozenset(
        (CertificateKind.FIRST_ATTACK_ACCELERATION,)
    ),
    ProofSchema.ACTIVE_POST_ATTACH_ATTACK_COMPLETION_V1: frozenset(
        (CertificateKind.ATTACK_COMPLETION,)
    ),
    ProofSchema.WALLY_SURVIVAL_V1: frozenset((CertificateKind.RESOURCE_IMPROVEMENT,)),
    ProofSchema.CAPE_SURVIVAL_V1: frozenset((CertificateKind.RESOURCE_IMPROVEMENT,)),
    ProofSchema.GUST_DOMINANCE_V1: frozenset((CertificateKind.PRIZE_GAIN_NOW,)),
    ProofSchema.DECK_RULE_V1: frozenset(CertificateKind),
}
_ALLOWED_TIERS_BY_SCHEMA = {
    ProofSchema.SAFE_FALLBACK_V1: frozenset(
        (
            ResolverTier.RESOURCE_PRESERVING_FALLBACK,
            ResolverTier.PASS,
        )
    ),
    ProofSchema.ATTACK_OUTCOME_V1: frozenset(
        (
            ResolverTier.EXACT_WIN_NOW,
            ResolverTier.EXACT_CURRENT_TURN_PRIZE,
            ResolverTier.BEST_CERTIFIED_ATTACK,
        )
    ),
    ProofSchema.BASIC_BENCH_V1: frozenset((ResolverTier.SAFE_ENGINE_COMPLETION,)),
    ProofSchema.POKE_PAD_CORE_FORMATION_V1: frozenset(
        (ResolverTier.ROUTE_CRITICAL_SEARCH,)
    ),
    ProofSchema.FIRST_TURN_RIOLU_ATTACH_V1: frozenset(
        (ResolverTier.ROUTE_CRITICAL_MANUAL_ATTACH,)
    ),
    ProofSchema.ACTIVE_POST_ATTACH_ATTACK_COMPLETION_V1: frozenset(
        (ResolverTier.ATTACK_COMPLETION,)
    ),
    ProofSchema.WALLY_SURVIVAL_V1: frozenset((ResolverTier.SURVIVAL_CRITICAL_WALLY,)),
    ProofSchema.CAPE_SURVIVAL_V1: frozenset((ResolverTier.CERTIFIED_SURVIVAL,)),
    ProofSchema.GUST_DOMINANCE_V1: frozenset(
        (ResolverTier.TERMINAL_OR_SUPERIOR_GUST, ResolverTier.STRICTLY_SUPERIOR_GUST)
    ),
    ProofSchema.DECK_RULE_V1: frozenset(
        (
            ResolverTier.EXACT_WIN_NOW,
            ResolverTier.TERMINAL_OR_SUPERIOR_GUST,
            ResolverTier.SURVIVAL_CRITICAL_WALLY,
            ResolverTier.STRICTLY_SUPERIOR_GUST,
            ResolverTier.EXACT_CURRENT_TURN_PRIZE,
            ResolverTier.SAME_ATTACK_PLUS_CONTINUITY,
            ResolverTier.ATTACK_COMPLETION,
            ResolverTier.CERTIFIED_EVOLUTION,
            ResolverTier.ROUTE_CRITICAL_SEARCH,
            ResolverTier.ROUTE_CRITICAL_MANUAL_ATTACH,
            ResolverTier.SAFE_DRAW_OR_DISRUPTION,
            ResolverTier.CERTIFIED_SURVIVAL,
            ResolverTier.MINIMAL_PPP,
        )
    ),
}
_ALLOWED_COMBINATIONS = frozenset(
    (
        (
            ProofSchema.SAFE_FALLBACK_V1,
            CertificateKind.SAFE_FALLBACK,
            ResolverTier.RESOURCE_PRESERVING_FALLBACK,
            int(OptionType.ATTACK),
        ),
        (
            ProofSchema.SAFE_FALLBACK_V1,
            CertificateKind.SAFE_FALLBACK,
            ResolverTier.PASS,
            int(OptionType.END),
        ),
        (
            ProofSchema.ATTACK_OUTCOME_V1,
            CertificateKind.WIN_NOW,
            ResolverTier.EXACT_WIN_NOW,
            int(OptionType.ATTACK),
        ),
        (
            ProofSchema.ATTACK_OUTCOME_V1,
            CertificateKind.PRIZE_GAIN_NOW,
            ResolverTier.EXACT_CURRENT_TURN_PRIZE,
            int(OptionType.ATTACK),
        ),
        (
            ProofSchema.ATTACK_OUTCOME_V1,
            CertificateKind.ATTACK_COMPLETION,
            ResolverTier.BEST_CERTIFIED_ATTACK,
            int(OptionType.ATTACK),
        ),
        (
            ProofSchema.BASIC_BENCH_V1,
            CertificateKind.FIRST_ATTACK_ACCELERATION,
            ResolverTier.SAFE_ENGINE_COMPLETION,
            int(OptionType.PLAY),
        ),
        (
            ProofSchema.BASIC_BENCH_V1,
            CertificateKind.ENGINE_COMPLETION,
            ResolverTier.SAFE_ENGINE_COMPLETION,
            int(OptionType.PLAY),
        ),
        (
            ProofSchema.BASIC_BENCH_V1,
            CertificateKind.RESOURCE_IMPROVEMENT,
            ResolverTier.SAFE_ENGINE_COMPLETION,
            int(OptionType.PLAY),
        ),
        (
            ProofSchema.POKE_PAD_CORE_FORMATION_V1,
            CertificateKind.RESOURCE_IMPROVEMENT,
            ResolverTier.ROUTE_CRITICAL_SEARCH,
            int(OptionType.PLAY),
        ),
        (
            ProofSchema.FIRST_TURN_RIOLU_ATTACH_V1,
            CertificateKind.FIRST_ATTACK_ACCELERATION,
            ResolverTier.ROUTE_CRITICAL_MANUAL_ATTACH,
            int(OptionType.ATTACH),
        ),
        (
            ProofSchema.ACTIVE_POST_ATTACH_ATTACK_COMPLETION_V1,
            CertificateKind.ATTACK_COMPLETION,
            ResolverTier.ATTACK_COMPLETION,
            int(OptionType.ATTACH),
        ),
        (
            ProofSchema.WALLY_SURVIVAL_V1,
            CertificateKind.RESOURCE_IMPROVEMENT,
            ResolverTier.SURVIVAL_CRITICAL_WALLY,
            int(OptionType.PLAY),
        ),
        (
            ProofSchema.CAPE_SURVIVAL_V1,
            CertificateKind.RESOURCE_IMPROVEMENT,
            ResolverTier.CERTIFIED_SURVIVAL,
            int(OptionType.ATTACH),
        ),
        (
            ProofSchema.GUST_DOMINANCE_V1,
            CertificateKind.PRIZE_GAIN_NOW,
            ResolverTier.TERMINAL_OR_SUPERIOR_GUST,
            int(OptionType.PLAY),
        ),
        (
            ProofSchema.GUST_DOMINANCE_V1,
            CertificateKind.PRIZE_GAIN_NOW,
            ResolverTier.STRICTLY_SUPERIOR_GUST,
            int(OptionType.PLAY),
        ),
        (
            ProofSchema.GUST_DOMINANCE_V1,
            CertificateKind.PRIZE_GAIN_NOW,
            ResolverTier.TERMINAL_OR_SUPERIOR_GUST,
            int(OptionType.EVOLVE),
        ),
    )
)
_DECK_RULE_COMBINATIONS = frozenset(
    (
        (
            ProofSchema.DECK_RULE_V1,
            CertificateKind.WIN_NOW,
            ResolverTier.EXACT_WIN_NOW,
            int(OptionType.ATTACK),
        ),
        (
            ProofSchema.DECK_RULE_V1,
            CertificateKind.PRIZE_GAIN_NOW,
            ResolverTier.EXACT_CURRENT_TURN_PRIZE,
            int(OptionType.ATTACK),
        ),
        (
            ProofSchema.DECK_RULE_V1,
            CertificateKind.SAME_ATTACK_PLUS_CONTINUITY,
            ResolverTier.SAME_ATTACK_PLUS_CONTINUITY,
            int(OptionType.ATTACK),
        ),
        (
            ProofSchema.DECK_RULE_V1,
            CertificateKind.ATTACK_COMPLETION,
            ResolverTier.CERTIFIED_EVOLUTION,
            int(OptionType.EVOLVE),
        ),
        (
            ProofSchema.DECK_RULE_V1,
            CertificateKind.FIRST_ATTACK_ACCELERATION,
            ResolverTier.CERTIFIED_EVOLUTION,
            int(OptionType.EVOLVE),
        ),
        (
            ProofSchema.DECK_RULE_V1,
            CertificateKind.RESOURCE_IMPROVEMENT,
            ResolverTier.ROUTE_CRITICAL_SEARCH,
            int(OptionType.PLAY),
        ),
        (
            ProofSchema.DECK_RULE_V1,
            CertificateKind.RESOURCE_IMPROVEMENT,
            ResolverTier.SAFE_DRAW_OR_DISRUPTION,
            int(OptionType.PLAY),
        ),
        (
            ProofSchema.DECK_RULE_V1,
            CertificateKind.RESOURCE_IMPROVEMENT,
            ResolverTier.SAFE_DRAW_OR_DISRUPTION,
            int(OptionType.ABILITY),
        ),
        (
            ProofSchema.DECK_RULE_V1,
            CertificateKind.RESOURCE_IMPROVEMENT,
            ResolverTier.SAFE_DRAW_OR_DISRUPTION,
            int(OptionType.SKILL),
        ),
        (
            ProofSchema.DECK_RULE_V1,
            CertificateKind.ATTACK_COMPLETION,
            ResolverTier.MINIMAL_PPP,
            int(OptionType.PLAY),
        ),
        (
            ProofSchema.DECK_RULE_V1,
            CertificateKind.ATTACK_COMPLETION,
            ResolverTier.ATTACK_COMPLETION,
            int(OptionType.PLAY),
        ),
        (
            ProofSchema.DECK_RULE_V1,
            CertificateKind.ATTACK_COMPLETION,
            ResolverTier.ROUTE_CRITICAL_MANUAL_ATTACH,
            int(OptionType.ATTACH),
        ),
        (
            ProofSchema.DECK_RULE_V1,
            CertificateKind.FIRST_ATTACK_ACCELERATION,
            ResolverTier.ROUTE_CRITICAL_MANUAL_ATTACH,
            int(OptionType.ATTACH),
        ),
    )
)
_ALLOWED_COMBINATIONS = _ALLOWED_COMBINATIONS | _DECK_RULE_COMBINATIONS


def action_spec_digest(action_spec: ActionSpec) -> str:
    payload = {
        "order_sensitive": bool(action_spec.order_sensitive),
        "choices": action_spec.canonical_choices(),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _transaction_plan_digest(transaction_plan: Optional[Any]) -> Optional[str]:
    if transaction_plan is None:
        return None
    if not isinstance(transaction_plan, TransactionPlan):
        return "INVALID_TRANSACTION_PLAN"
    return transaction_plan.digest()


def proposal_digest(proposal: Proposal) -> str:
    """Hash every policy-relevant proposal field for exact trace matching."""

    if not isinstance(proposal, Proposal):
        raise ValueError("proposal_digest requires a Proposal")
    payload = {
        "rule_id": proposal.rule_id,
        "tier": int(proposal.tier),
        "action_digest": action_spec_digest(proposal.action_spec),
        "certificate_kind": int(proposal.certificate_kind),
        "proof_digest": proposal.proof.digest(),
        "resource_cost": [
            ref_value.sort_key()
            for ref_value in proposal.resource_cost.irreversible_refs
        ],
        "reservation_ids": proposal.reservation_ids,
        "transaction_plan_digest": _transaction_plan_digest(proposal.transaction_plan),
        "metrics": {
            "schema": proposal.metrics.schema.value,
            "supporter_opportunity_cost": (proposal.metrics.supporter_opportunity_cost),
            "prize_liability_after": proposal.metrics.prize_liability_after,
            "ready_attackers_after": proposal.metrics.ready_attackers_after,
            "draw_buffer_after": proposal.metrics.draw_buffer_after,
        },
        "deterministic_tiebreak": proposal.deterministic_tiebreak,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _own_known_refs(state: PublicState) -> frozenset[PhysicalRef]:
    refs = list(state.own.hand_refs)
    refs.extend(state.own.discard_refs)
    refs.extend(state.own.prize_refs)
    for pokemon in state.own.active + state.own.bench:
        refs.append(pokemon.ref)
        refs.extend(pokemon.energy_refs)
        refs.extend(pokemon.tool_refs)
        refs.extend(pokemon.pre_evolution_refs)
    refs.extend(
        ref_value
        for ref_value in state.stadium_refs + state.looking_refs
        if ref_value.owner == state.seat
    )
    return frozenset(refs)


def canonical_proposal_tiebreak(
    action_spec: ActionSpec,
    proof: CertificateProof,
) -> Tuple[int, ...]:
    """Return the only accepted deterministic tiebreak for a checked proof."""

    if not isinstance(action_spec, ActionSpec) or not isinstance(
        proof,
        CertificateProof,
    ):
        raise ValueError("canonical tiebreak requires an action and proof")
    if len(action_spec.choices) != 1:
        return ()
    key = action_spec.choices[0]
    if key.option_type == int(OptionType.ATTACK):
        if (
            isinstance(key.attack_id, bool)
            or not isinstance(key.attack_id, int)
            or key.attack_id <= 0
        ):
            return ()
        if proof.schema == ProofSchema.ATTACK_OUTCOME_V1:
            damage_margin = proof.fact("damage_margin")
            final_damage = proof.fact("final_damage")
            future_lock_cost = proof.fact("future_lock_cost")
            if any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in (damage_margin, final_damage, future_lock_cost)
            ):
                return ()
            if proof.kind == CertificateKind.WIN_NOW:
                return (
                    int(OptionType.ATTACK),
                    -damage_margin,
                    future_lock_cost,
                    int(key.attack_id),
                )
            if proof.kind == CertificateKind.PRIZE_GAIN_NOW:
                return (
                    int(OptionType.ATTACK),
                    future_lock_cost,
                    -final_damage,
                    int(key.attack_id),
                )
            if proof.kind == CertificateKind.ATTACK_COMPLETION:
                return (
                    int(OptionType.ATTACK),
                    -final_damage,
                    future_lock_cost,
                    int(key.attack_id),
                )
            return ()
        return int(OptionType.ATTACK), int(key.attack_id)
    if key.option_type == int(OptionType.END):
        return (int(OptionType.END),)
    if (
        key.option_type == int(OptionType.PLAY)
        and proof.schema == ProofSchema.BASIC_BENCH_V1
    ):
        purpose_priority = proof.fact("purpose_priority")
        if (
            isinstance(purpose_priority, bool)
            or not isinstance(purpose_priority, int)
            or purpose_priority < 0
            or isinstance(key.card_id, bool)
            or not isinstance(key.card_id, int)
            or key.card_id <= 0
            or isinstance(key.card_serial, bool)
            or not isinstance(key.card_serial, int)
            or key.card_serial < 0
        ):
            return ()
        return (
            int(OptionType.PLAY),
            int(purpose_priority),
            int(key.card_id),
            int(key.card_serial),
        )
    if (
        key.option_type == int(OptionType.PLAY)
        and proof.schema == ProofSchema.POKE_PAD_CORE_FORMATION_V1
    ):
        if (
            isinstance(key.card_id, bool)
            or not isinstance(key.card_id, int)
            or key.card_id != 1152
            or isinstance(key.card_serial, bool)
            or not isinstance(key.card_serial, int)
            or key.card_serial < 0
        ):
            return ()
        return (
            int(OptionType.PLAY),
            int(key.card_id),
            int(key.card_serial),
        )
    if (
        key.option_type == int(OptionType.ATTACH)
        and proof.schema == ProofSchema.FIRST_TURN_RIOLU_ATTACH_V1
    ):
        zone_priority = proof.fact("target_zone_priority")
        remaining_hp = proof.fact("target_remaining_hp")
        lineage_serial = proof.fact("target_lineage_serial")
        energy_serial = proof.fact("energy_serial")
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in (
                zone_priority,
                remaining_hp,
                lineage_serial,
                energy_serial,
            )
        ):
            return ()
        return (
            int(OptionType.ATTACH),
            int(zone_priority),
            -int(remaining_hp),
            int(lineage_serial),
            int(energy_serial),
        )
    if (
        key.option_type == int(OptionType.ATTACH)
        and proof.schema == ProofSchema.ACTIVE_POST_ATTACH_ATTACK_COMPLETION_V1
    ):
        energy_serial = proof.fact("energy_serial")
        final_damage = proof.fact("chosen_final_damage")
        future_lock_cost = proof.fact("chosen_future_lock_cost")
        attack_id = proof.fact("chosen_attack_id")
        if (
            any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in (
                    energy_serial,
                    final_damage,
                    future_lock_cost,
                    attack_id,
                )
            )
            or energy_serial < 0
            or final_damage <= 0
            or future_lock_cost not in (0, 1)
            or attack_id <= 0
        ):
            return ()
        return (
            int(OptionType.ATTACH),
            int(energy_serial),
            -int(final_damage),
            int(future_lock_cost),
            int(attack_id),
        )
    if proof.schema in (
        ProofSchema.DECK_RULE_V1,
        ProofSchema.WALLY_SURVIVAL_V1,
        ProofSchema.CAPE_SURVIVAL_V1,
        ProofSchema.GUST_DOMINANCE_V1,
    ):
        route_priority = proof.fact("route_priority")
        if (
            isinstance(route_priority, bool)
            or not isinstance(route_priority, int)
            or route_priority < 0
        ):
            return ()
        sentinel = 2**63 - 1
        return (
            int(key.option_type),
            int(route_priority),
            key.card_id if isinstance(key.card_id, int) else sentinel,
            key.card_serial if isinstance(key.card_serial, int) else sentinel,
        )
    return ()


def _expected_tiebreak(proposal: Proposal) -> Tuple[int, ...]:
    return canonical_proposal_tiebreak(proposal.action_spec, proposal.proof)


def proposal_rank_key(proposal: Proposal) -> Tuple[Any, ...]:
    """Return the complete deterministic resolver ordering key."""

    if not isinstance(proposal, Proposal):
        raise ValueError("proposal_rank_key requires a Proposal")
    sentinel = 2**63 - 1
    key = proposal.action_spec.choices[0]
    card_id = key.card_id if key.card_id is not None else sentinel
    serial = key.card_serial if key.card_serial is not None else sentinel
    return (
        int(proposal.tier),
        -int(proposal.proof.guaranteed_prizes),
        len(proposal.resource_cost.irreversible_refs),
        int(card_id),
        int(serial),
        proposal.deterministic_tiebreak,
        proposal.rule_id,
        proposal.action_spec.canonical_choices(),
        proposal.proof.digest(),
    )


def _matching_option_reasons(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    action_spec: ActionSpec,
) -> Tuple[Tuple[str, ...], Optional[Tuple[int, ...]]]:
    reasons = []
    for choice in action_spec.choices:
        count = sum(option.key == choice for option in legal_options)
        if count == 0:
            reasons.append("ACTION_NOT_FOUND")
        elif count > 1:
            reasons.append("DUPLICATE_SEMANTIC_OPTION")
    if not state.min_count <= len(action_spec.choices) <= state.max_count:
        reasons.append("ACTION_COUNT_OUT_OF_RANGE")
    if reasons:
        return tuple(sorted(set(reasons))), None
    try:
        bound = tuple(
            action_spec.bind(
                legal_options,
                min_count=state.min_count,
                max_count=state.max_count,
            )
        )
    except SemanticBindError:
        return ("ACTION_BIND_FAILURE",), None
    return (), bound


def _legal_option_index_reasons(
    legal_options: Sequence[SemanticOption],
) -> Tuple[str, ...]:
    indices = tuple(option.index for option in legal_options)
    exact_indices = tuple(
        index
        for index in indices
        if isinstance(index, int) and not isinstance(index, bool)
    )
    reasons = []
    if len(exact_indices) != len(indices) or any(
        index < 0 or index >= len(legal_options) for index in exact_indices
    ):
        reasons.append("LEGAL_OPTION_INDEX_INVALID")
    if len(set(exact_indices)) != len(exact_indices):
        reasons.append("LEGAL_OPTION_INDEX_COLLISION")
    if set(exact_indices) != set(range(len(legal_options))):
        reasons.append("LEGAL_OPTION_INDEX_SET_INCOMPLETE")
    return tuple(reasons)


def _validate_proposal(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    ledger: ResourceLedger,
    proposal: Proposal,
    duplicate_rule_id: bool,
    legal_option_index_reasons: Tuple[str, ...],
    registry: Optional[PublicEffectRegistry],
) -> Tuple[Tuple[str, ...], Optional[Tuple[int, ...]]]:
    reasons = []
    if duplicate_rule_id:
        reasons.append("DUPLICATE_RULE_ID")
    reasons.extend(legal_option_index_reasons)
    if not proposal.proof.is_valid:
        reasons.append("PROOF_INVALID")
    if not proposal.proof.verify_integrity():
        reasons.append("PROOF_INTEGRITY_INVALID")
    if proposal.certificate_kind != proposal.proof.kind:
        reasons.append("CERTIFICATE_KIND_MISMATCH")
    allowed_kinds = _ALLOWED_KINDS_BY_SCHEMA.get(proposal.proof.schema, frozenset())
    allowed_tiers = _ALLOWED_TIERS_BY_SCHEMA.get(proposal.proof.schema, frozenset())
    if proposal.proof.schema not in _ALLOWED_KINDS_BY_SCHEMA:
        reasons.append("PROFILE_SCHEMA_FORBIDDEN")
    if proposal.certificate_kind not in allowed_kinds:
        reasons.append("PROFILE_KIND_FORBIDDEN")
    if proposal.tier not in allowed_tiers:
        reasons.append("PROFILE_TIER_FORBIDDEN")

    option_type = (
        proposal.action_spec.choices[0].option_type
        if len(proposal.action_spec.choices) == 1
        else None
    )
    combination = (
        proposal.proof.schema,
        proposal.certificate_kind,
        proposal.tier,
        option_type,
    )
    if combination not in _ALLOWED_COMBINATIONS:
        reasons.append("PROFILE_OPTION_TYPE_FORBIDDEN")
    if proposal.proof.schema == ProofSchema.SAFE_FALLBACK_V1:
        if proposal.proof.guaranteed_prizes != 0:
            reasons.append("PROFILE_PRIZE_CLAIM_FORBIDDEN")
    elif proposal.proof.schema == ProofSchema.ATTACK_OUTCOME_V1:
        if not isinstance(registry, PublicEffectRegistry):
            reasons.append("CURRENT_REGISTRY_REQUIRED")
        elif proposal.proof.fact("registry_digest") != registry.digest:
            reasons.append("PROOF_REGISTRY_STALE")
        proven_prizes = proposal.proof.fact("prizes_taken")
        if (
            isinstance(proven_prizes, bool)
            or not isinstance(proven_prizes, int)
            or proven_prizes < 0
        ):
            reasons.append("ATTACK_PRIZE_FACT_INVALID")
        elif proposal.certificate_kind in (
            CertificateKind.WIN_NOW,
            CertificateKind.PRIZE_GAIN_NOW,
        ):
            if proposal.proof.guaranteed_prizes != proven_prizes:
                reasons.append("ATTACK_PRIZE_CLAIM_MISMATCH")
        elif proposal.proof.guaranteed_prizes != 0:
            reasons.append("ATTACK_COMPLETION_PRIZE_CLAIM_FORBIDDEN")
    elif proposal.proof.schema == ProofSchema.BASIC_BENCH_V1:
        if proposal.proof.guaranteed_prizes != 0:
            reasons.append("BASIC_BENCH_PRIZE_CLAIM_FORBIDDEN")
        if not isinstance(registry, PublicEffectRegistry):
            reasons.append("CURRENT_REGISTRY_REQUIRED")
        else:
            try:
                current_features = build_deck_features(
                    state,
                    legal_options,
                    registry,
                )
            except (RuntimeError, ValueError):
                reasons.append("BASIC_BENCH_FEATURE_RECOMPUTE_FAILED")
            else:
                if proposal.proof.fact("registry_digest") != registry.digest:
                    reasons.append("PROOF_REGISTRY_STALE")
                if proposal.proof.fact("features_digest") != current_features.digest():
                    reasons.append("BASIC_BENCH_FEATURES_STALE")
                try:
                    expected_proof = basic_bench_proof(
                        state,
                        legal_options,
                        registry,
                        current_features,
                        proposal.action_spec,
                    )
                except ValueError:
                    reasons.append("BASIC_BENCH_RECOMPUTE_REJECTED")
                else:
                    if expected_proof.digest() != proposal.proof.digest():
                        reasons.append("BASIC_BENCH_PROOF_MISMATCH")
    elif proposal.proof.schema == ProofSchema.POKE_PAD_CORE_FORMATION_V1:
        if proposal.proof.guaranteed_prizes != 0:
            reasons.append("POKE_PAD_PRIZE_CLAIM_FORBIDDEN")
        if not isinstance(registry, PublicEffectRegistry):
            reasons.append("CURRENT_REGISTRY_REQUIRED")
        else:
            try:
                current_features = build_deck_features(
                    state,
                    legal_options,
                    registry,
                )
                current_attack_outcomes = build_attack_outcome_table(
                    state,
                    legal_options,
                    registry,
                )
                current_classes = poke_pad_core_eligible_classes(state)
                current_acceptable_ids = tuple(
                    sorted(
                        card_id
                        for card_class in current_classes
                        for card_id in card_class
                    )
                )
                current_availability = prove_deck_availability_from_state(
                    state,
                    current_acceptable_ids,
                    required_count=1,
                )
                expected_proof = poke_pad_core_formation_proof(
                    state,
                    legal_options,
                    registry,
                    current_features,
                    current_attack_outcomes,
                    current_availability,
                    proposal.action_spec,
                )
            except (RuntimeError, ValueError):
                reasons.append("POKE_PAD_RECOMPUTE_REJECTED")
            else:
                if proposal.proof.fact("registry_digest") != registry.digest:
                    reasons.append("PROOF_REGISTRY_STALE")
                if proposal.proof.fact("features_digest") != current_features.digest():
                    reasons.append("POKE_PAD_FEATURES_STALE")
                if expected_proof.digest() != proposal.proof.digest():
                    reasons.append("POKE_PAD_PROOF_MISMATCH")
    elif proposal.proof.schema == ProofSchema.FIRST_TURN_RIOLU_ATTACH_V1:
        if proposal.proof.guaranteed_prizes != 0:
            reasons.append("RIOLU_ATTACH_PRIZE_CLAIM_FORBIDDEN")
        if not isinstance(registry, PublicEffectRegistry):
            reasons.append("CURRENT_REGISTRY_REQUIRED")
        else:
            try:
                current_features = build_deck_features(
                    state,
                    legal_options,
                    registry,
                )
            except (RuntimeError, ValueError):
                reasons.append("RIOLU_ATTACH_FEATURE_RECOMPUTE_FAILED")
            else:
                if proposal.proof.fact("registry_digest") != registry.digest:
                    reasons.append("PROOF_REGISTRY_STALE")
                if proposal.proof.fact("features_digest") != current_features.digest():
                    reasons.append("RIOLU_ATTACH_FEATURES_STALE")
                try:
                    expected_proof = first_turn_riolu_attach_proof(
                        state,
                        legal_options,
                        registry,
                        current_features,
                        proposal.action_spec,
                    )
                except ValueError:
                    reasons.append("RIOLU_ATTACH_RECOMPUTE_REJECTED")
                else:
                    if expected_proof.digest() != proposal.proof.digest():
                        reasons.append("RIOLU_ATTACH_PROOF_MISMATCH")
    elif proposal.proof.schema == ProofSchema.ACTIVE_POST_ATTACH_ATTACK_COMPLETION_V1:
        if proposal.proof.guaranteed_prizes != 0:
            reasons.append("ACTIVE_ATTACK_COMPLETION_PRIZE_CLAIM_FORBIDDEN")
        expected_actor = (
            state.first_player
            if state.first_player in (0, 1) and state.turn % 2 == 1
            else 1 - state.first_player
            if state.first_player in (0, 1)
            else None
        )
        if (
            state.turn != 2
            or state.first_player not in (0, 1)
            or state.seat == state.first_player
            or expected_actor != state.seat
        ):
            reasons.append("ACTIVE_ATTACK_COMPLETION_TIMING_INVALID")
        if (
            proposal.rule_id != ACTIVE_ATTACK_COMPLETION_RULE_ID
            or proposal.proof.fact("rule_id") != ACTIVE_ATTACK_COMPLETION_RULE_ID
        ):
            reasons.append("ACTIVE_ATTACK_COMPLETION_RULE_ID_MISMATCH")
        if (
            proposal.proof.fact("coverage") != ACTIVE_ATTACK_COMPLETION_COVERAGE
            or proposal.proof.fact("full_requirement_compliance") is not False
            or proposal.proof.fact("unresolved_requirement_codes")
            != ACTIVE_ATTACK_COMPLETION_UNRESOLVED
        ):
            reasons.append("ACTIVE_ATTACK_COMPLETION_SCOPE_FACT_MISMATCH")
        if (
            proposal.proof.fact("global_turn") != 2
            or proposal.proof.fact("own_turn_number") != 1
        ):
            reasons.append("ACTIVE_ATTACK_COMPLETION_TURN_FACT_MISMATCH")
        pre_payable = proposal.proof.fact("pre_payable")
        post_payable = proposal.proof.fact("post_payable")
        if pre_payable != ():
            reasons.append("ACTIVE_ATTACK_COMPLETION_PRE_PAYABLE_NOT_EMPTY")
        if (
            not isinstance(post_payable, tuple)
            or len(post_payable) != 1
            or post_payable != (proposal.proof.fact("chosen_attack_id"),)
            or proposal.proof.fact("candidate_attack_ids") != post_payable
            or proposal.proof.fact("post_table_and_outcome_fully_exact") is not True
        ):
            reasons.append("ACTIVE_ATTACK_COMPLETION_POST_PAYABLE_NOT_SINGLETON")
        if not isinstance(registry, PublicEffectRegistry):
            reasons.append("CURRENT_REGISTRY_REQUIRED")
        else:
            if proposal.proof.fact("registry_digest") != registry.digest:
                reasons.append("PROOF_REGISTRY_STALE")
            registry_audit = active_attack_completion_registry_audit(registry)
            if registry_audit is None:
                reasons.append("ACTIVE_ATTACK_COMPLETION_REGISTRY_AUDIT_REJECTED")
            elif (
                proposal.proof.fact("catalog_sha256") != registry_audit[0]
                or proposal.proof.fact("persistent_trainer_audit_fingerprint")
                != registry_audit[1]
            ):
                reasons.append("ACTIVE_ATTACK_COMPLETION_REGISTRY_AUDIT_MISMATCH")
            target = state.opponent_active
            target_profiles = (
                ()
                if target is None
                else tuple(
                    profile
                    for profile in registry.profiles
                    if profile.card_id == target.ref.card_id
                )
            )
            target_type = proposal.proof.fact("target_energy_type")
            if (
                proposal.proof.fact("target_energy_type_exact") is not True
                or len(target_profiles) != 1
                or isinstance(target_type, bool)
                or not isinstance(target_type, int)
                or target_type <= 0
                or target_type == 8
                or target_profiles[0].energy_type != target_type
            ):
                reasons.append("ACTIVE_ATTACK_COMPLETION_TARGET_TYPE_REJECTED")
            try:
                expected_proof = active_post_attach_attack_completion_proof(
                    state,
                    legal_options,
                    registry,
                    proposal.action_spec,
                )
            except ValueError:
                reasons.append("ACTIVE_ATTACK_COMPLETION_RECOMPUTE_REJECTED")
            else:
                if expected_proof.digest() != proposal.proof.digest():
                    reasons.append("ACTIVE_ATTACK_COMPLETION_PROOF_MISMATCH")
    elif proposal.proof.schema in (
        ProofSchema.WALLY_SURVIVAL_V1,
        ProofSchema.CAPE_SURVIVAL_V1,
        ProofSchema.GUST_DOMINANCE_V1,
    ):
        expected_proof = None
        if not isinstance(registry, PublicEffectRegistry):
            reasons.append("CURRENT_REGISTRY_REQUIRED")
        else:
            try:
                current_attack_outcomes = build_attack_outcome_table(
                    state, legal_options, registry
                )
                if proposal.proof.schema == ProofSchema.WALLY_SURVIVAL_V1:
                    expected_proof = verify_wally_survival_certificate(
                        state,
                        legal_options,
                        ledger,
                        current_attack_outcomes,
                        registry,
                        proposal.action_spec,
                    )
                    expected_rule = "R_WALLY_THREE_PRIZE_REBOOT_V1"
                    expected_tier = ResolverTier.SURVIVAL_CRITICAL_WALLY
                elif proposal.proof.schema == ProofSchema.CAPE_SURVIVAL_V1:
                    expected_proof = verify_cape_survival_certificate(
                        state,
                        legal_options,
                        ledger,
                        current_attack_outcomes,
                        registry,
                        proposal.action_spec,
                    )
                    expected_rule = "R_CAPE_EXPLICIT_PROTECTION_V1"
                    expected_tier = ResolverTier.CERTIFIED_SURVIVAL
                else:
                    expected_proof = verify_gust_dominance_certificate(
                        state,
                        legal_options,
                        ledger,
                        current_attack_outcomes,
                        registry,
                        proposal.action_spec,
                    )
                    expected_rule = expected_proof.fact("route_code")
                    expected_tier = (
                        ResolverTier.TERMINAL_OR_SUPERIOR_GUST
                        if proposal.action_spec.choices[0].option_type
                        == int(OptionType.EVOLVE)
                        or expected_proof.fact("terminal") is True
                        else ResolverTier.STRICTLY_SUPERIOR_GUST
                    )
            except (RuntimeError, ValueError):
                reasons.append("A4_PROOF_RECOMPUTE_REJECTED")
            else:
                if expected_proof.digest() != proposal.proof.digest():
                    reasons.append("A4_PROOF_MISMATCH")
                if proposal.rule_id != expected_rule:
                    reasons.append("A4_RULE_ID_MISMATCH")
                if proposal.proof.fact("route_code") != expected_rule:
                    reasons.append("A4_PROOF_ROUTE_MISMATCH")
                if proposal.tier != expected_tier:
                    reasons.append("A4_TIER_MISMATCH")
                if proposal.proof.fact("certificate_status") != "VERIFIED_GATE_A4":
                    reasons.append("A4_STATUS_MISMATCH")
                if proposal.proof.schema == ProofSchema.WALLY_SURVIVAL_V1:
                    higher_status = wally_higher_priority_supporter_status(
                        state,
                        legal_options,
                        ledger,
                        current_attack_outcomes,
                        registry,
                    )
                    if higher_status != "ABSENT_EXACT":
                        reasons.append(
                            "WALLY_HIGHER_PRIORITY_SUPPORTER_{0}".format(higher_status)
                        )
                if (
                    proposal.proof.schema == ProofSchema.GUST_DOMINANCE_V1
                    and proposal.proof.guaranteed_prizes
                    != expected_proof.fact("prizes_taken")
                ):
                    reasons.append("A4_GUST_PRIZE_MISMATCH")

        source_fact = (
            None if expected_proof is None else expected_proof.fact("source_ref")
        )
        source_matches = tuple(
            ref_value
            for ref_value in state.own.hand_refs
            if ref_value.sort_key() == source_fact
        )
        source_ref = source_matches[0] if len(source_matches) == 1 else None
        if source_ref is None:
            reasons.append("A4_SOURCE_REF_INVALID")
        elif source_ref not in ledger.visible_refs:
            reasons.append("A4_SOURCE_NOT_IN_LEDGER")
        if source_ref is None or proposal.resource_cost.irreversible_refs != (
            source_ref,
        ):
            reasons.append("A4_RESOURCE_COST_MISMATCH")
        if proposal.reservation_ids:
            reasons.append("A4_RESERVATION_FORBIDDEN")
        cost_check = ledger.check_cost(proposal.resource_cost.irreversible_refs)
        reasons.extend(
            "LEDGER_COST_REJECTED:{0}".format(reason)
            for reason in cost_check.rejection_reasons
        )

        expected_plan = None
        if expected_proof is not None and source_ref is not None:
            if proposal.proof.schema == ProofSchema.WALLY_SURVIVAL_V1:
                target_matches = tuple(
                    pokemon.ref
                    for pokemon in state.own.active
                    if pokemon.ref.sort_key() == expected_proof.fact("target_ref")
                )
                target_ref = target_matches[0] if len(target_matches) == 1 else None
                energy_refs = (
                    () if state.own_active is None else state.own_active.energy_refs
                )
                reattach_matches = tuple(
                    ref_value
                    for ref_value in energy_refs
                    if ref_value.sort_key() == expected_proof.fact("reattach_ref")
                )
                reattach_ref = (
                    reattach_matches[0] if len(reattach_matches) == 1 else None
                )
                if target_ref is not None and reattach_ref is not None:
                    expected_plan = build_wally_plan(
                        state,
                        source_ref,
                        target_ref,
                        reattach_ref,
                        proposal.action_spec,
                        expected_proof.digest(),
                    )
            elif proposal.proof.schema == ProofSchema.GUST_DOMINANCE_V1:
                target_matches = tuple(
                    pokemon.ref
                    for pokemon in state.opponent.bench
                    if pokemon.ref.sort_key() == expected_proof.fact("gust_target_ref")
                )
                target_ref = target_matches[0] if len(target_matches) == 1 else None
                if target_ref is not None:
                    if (
                        expected_proof.fact("route_code")
                        == "R_GUST_BOSS_EXACT_DOMINANCE_A3"
                    ):
                        expected_plan = build_boss_gust_plan(
                            state,
                            source_ref,
                            target_ref,
                            proposal.action_spec,
                            expected_proof.digest(),
                        )
                    elif (
                        expected_proof.fact("route_code")
                        == "R_GUST_HARIYAMA_EXACT_DOMINANCE_A3"
                    ):
                        expected_plan = build_hariyama_gust_plan(
                            state,
                            source_ref,
                            target_ref,
                            proposal.action_spec,
                            expected_proof.digest(),
                        )
        if proposal.proof.schema == ProofSchema.CAPE_SURVIVAL_V1:
            if proposal.transaction_plan is not None:
                reasons.append("A4_CAPE_TRANSACTION_FORBIDDEN")
        elif expected_plan is None:
            reasons.append("A4_TRANSACTION_RECOMPUTE_REJECTED")
        elif (
            proposal.transaction_plan != expected_plan
            or not isinstance(proposal.transaction_plan, TransactionPlan)
            or proposal.transaction_plan.digest() != expected_plan.digest()
        ):
            reasons.append("A4_TRANSACTION_PLAN_MISMATCH")
    elif proposal.proof.schema == ProofSchema.DECK_RULE_V1:
        if not isinstance(registry, PublicEffectRegistry):
            reasons.append("CURRENT_REGISTRY_REQUIRED")
        else:
            try:
                current_features = build_deck_features(
                    state,
                    legal_options,
                    registry,
                )
                common_names = {
                    "route_code",
                    "option_type",
                    "legal_options_fingerprint",
                    "registry_digest",
                    "features_digest",
                }
                extra_facts = {
                    name: value
                    for name, value in proposal.proof.facts
                    if name not in common_names
                }
                expected_proof = deck_rule_proof(
                    state,
                    legal_options,
                    registry,
                    current_features,
                    proposal.action_spec,
                    route_code=proposal.proof.fact("route_code"),
                    kind=proposal.certificate_kind,
                    guaranteed_prizes=proposal.proof.guaranteed_prizes,
                    facts=extra_facts,
                )
            except (RuntimeError, ValueError):
                reasons.append("DECK_RULE_RECOMPUTE_REJECTED")
            else:
                if proposal.proof.fact("registry_digest") != registry.digest:
                    reasons.append("PROOF_REGISTRY_STALE")
                if proposal.proof.fact("features_digest") != current_features.digest():
                    reasons.append("DECK_RULE_FEATURES_STALE")
                if expected_proof.digest() != proposal.proof.digest():
                    reasons.append("DECK_RULE_PROOF_MISMATCH")
    if proposal.proof.state_fingerprint != public_state_fingerprint(state):
        reasons.append("PROOF_STATE_STALE")
    if proposal.proof.action_spec != proposal.action_spec:
        reasons.append("PROOF_ACTION_MISMATCH")
    if proposal.proof.fact("legal_options_fingerprint") != legal_options_fingerprint(
        legal_options
    ):
        reasons.append("PROOF_OPTIONS_STALE")

    option_reasons, bound = _matching_option_reasons(
        state,
        legal_options,
        proposal.action_spec,
    )
    reasons.extend(option_reasons)

    if ledger.owner is not None and ledger.owner != state.seat:
        reasons.append("LEDGER_OWNER_MISMATCH")
    known_refs = _own_known_refs(state)
    if any(ref_value not in known_refs for ref_value in ledger.visible_refs):
        reasons.append("LEDGER_REF_NOT_IN_STATE")
    if proposal.proof.schema == ProofSchema.BASIC_BENCH_V1:
        source_fact = proposal.proof.fact("source_ref")
        source_matches = tuple(
            ref_value
            for ref_value in state.own.hand_refs
            if ref_value.sort_key() == source_fact
        )
        if len(source_matches) != 1:
            reasons.append("BASIC_BENCH_SOURCE_REF_INVALID")
        elif source_matches[0] not in ledger.visible_refs:
            reasons.append("BASIC_BENCH_SOURCE_NOT_IN_LEDGER")
        else:
            source_ref = source_matches[0]
            reservation = ledger.reservation_for(source_ref)
            if reservation is not None:
                reasons.append(
                    "BASIC_BENCH_SOURCE_RESERVED:{0}".format(reservation.reservation_id)
                )
    if proposal.proof.schema == ProofSchema.POKE_PAD_CORE_FORMATION_V1:
        source_fact = proposal.proof.fact("source_ref")
        source_matches = tuple(
            ref_value
            for ref_value in state.own.hand_refs
            if ref_value.sort_key() == source_fact
        )
        source_ref = source_matches[0] if len(source_matches) == 1 else None
        if source_ref is None:
            reasons.append("POKE_PAD_SOURCE_REF_INVALID")
        elif source_ref not in ledger.visible_refs:
            reasons.append("POKE_PAD_SOURCE_NOT_IN_LEDGER")
        if source_ref is None or proposal.resource_cost.irreversible_refs != (
            source_ref,
        ):
            reasons.append("POKE_PAD_COST_MISMATCH")
        if proposal.reservation_ids:
            reasons.append("POKE_PAD_RESERVATION_FORBIDDEN")
        cost_check = ledger.check_cost(proposal.resource_cost.irreversible_refs)
        reasons.extend(
            "LEDGER_COST_REJECTED:{0}".format(reason)
            for reason in cost_check.rejection_reasons
        )
        if not isinstance(proposal.transaction_plan, TransactionPlan):
            reasons.append("POKE_PAD_TRANSACTION_REQUIRED")
        else:
            try:
                current_classes = poke_pad_core_eligible_classes(state)
                current_acceptable_ids = tuple(
                    sorted(
                        card_id
                        for card_class in current_classes
                        for card_id in card_class
                    )
                )
                current_availability = prove_deck_availability_from_state(
                    state,
                    current_acceptable_ids,
                    required_count=1,
                )
                expected_plan = build_poke_pad_core_search_plan(
                    state,
                    source_ref,
                    proposal.action_spec,
                    current_classes,
                    current_availability,
                    proposal.proof.digest(),
                )
            except (RuntimeError, ValueError):
                reasons.append("POKE_PAD_TRANSACTION_RECOMPUTE_REJECTED")
            else:
                if (
                    proposal.transaction_plan != expected_plan
                    or proposal.transaction_plan.digest() != expected_plan.digest()
                ):
                    reasons.append("POKE_PAD_TRANSACTION_PLAN_MISMATCH")
    elif proposal.proof.schema == ProofSchema.FIRST_TURN_RIOLU_ATTACH_V1:
        source_fact = proposal.proof.fact("source_ref")
        target_fact = proposal.proof.fact("target_ref")
        source_matches = tuple(
            ref_value
            for ref_value in state.own.hand_refs
            if ref_value.sort_key() == source_fact
        )
        target_matches = tuple(
            pokemon.ref
            for pokemon in state.own.active + state.own.bench
            if pokemon.ref.sort_key() == target_fact
        )
        source_ref = source_matches[0] if len(source_matches) == 1 else None
        target_ref = target_matches[0] if len(target_matches) == 1 else None
        if source_ref is None:
            reasons.append("RIOLU_ATTACH_SOURCE_REF_INVALID")
        elif source_ref not in ledger.visible_refs:
            reasons.append("RIOLU_ATTACH_SOURCE_NOT_IN_LEDGER")
        if target_ref is None:
            reasons.append("RIOLU_ATTACH_TARGET_REF_INVALID")
        elif target_ref not in ledger.visible_refs:
            reasons.append("RIOLU_ATTACH_TARGET_NOT_IN_LEDGER")
        if source_ref is None or proposal.resource_cost.irreversible_refs != (
            source_ref,
        ):
            reasons.append("RIOLU_ATTACH_COST_MISMATCH")
        expected_reservation_ids = (MANUAL_ATTACH_ENERGY_RESERVATION_ID,)
        if proposal.reservation_ids != expected_reservation_ids:
            reasons.append("RIOLU_ATTACH_RESERVATION_ID_MISMATCH")
        if proposal.proof.fact("reservation_id") != MANUAL_ATTACH_ENERGY_RESERVATION_ID:
            reasons.append("RIOLU_ATTACH_PROOF_RESERVATION_MISMATCH")
        reservation = ledger.get_reservation(MANUAL_ATTACH_ENERGY_RESERVATION_ID)
        if reservation is None:
            reasons.append("RIOLU_ATTACH_RESERVATION_MISSING")
        else:
            bound_reservations = tuple(
                value
                for value in ledger.bound_reservations
                if value.reservation_id == MANUAL_ATTACH_ENERGY_RESERVATION_ID
            )
            if reservation.kind != ReservationKind.HARD_RESERVED:
                reasons.append("RIOLU_ATTACH_RESERVATION_NOT_HARD")
            if (
                source_ref is None
                or reservation.is_role_constraint
                or reservation.refs != (source_ref,)
                or len(bound_reservations) != 1
                or bound_reservations[0].refs != (source_ref,)
            ):
                reasons.append("RIOLU_ATTACH_RESERVATION_REF_MISMATCH")
            try:
                ephemeral = ledger.release(MANUAL_ATTACH_ENERGY_RESERVATION_ID)
            except ResourceLedgerError:
                reasons.append("RIOLU_ATTACH_RESERVATION_RELEASE_FAILED")
            else:
                if source_ref is not None:
                    cost_check = ephemeral.check_cost((source_ref,))
                    reasons.extend(
                        "LEDGER_COST_REJECTED:{0}".format(reason)
                        for reason in cost_check.rejection_reasons
                    )
    elif proposal.proof.schema == ProofSchema.ACTIVE_POST_ATTACH_ATTACK_COMPLETION_V1:
        source_fact = proposal.proof.fact("source_ref")
        target_fact = proposal.proof.fact("target_ref")
        source_matches = tuple(
            ref_value
            for ref_value in state.own.hand_refs
            if ref_value.sort_key() == source_fact
        )
        target_matches = tuple(
            pokemon.ref
            for pokemon in state.own.active
            if pokemon.ref.sort_key() == target_fact
        )
        source_ref = source_matches[0] if len(source_matches) == 1 else None
        target_ref = target_matches[0] if len(target_matches) == 1 else None
        if source_ref is None:
            reasons.append("ACTIVE_ATTACK_COMPLETION_SOURCE_REF_INVALID")
        elif source_ref not in ledger.visible_refs:
            reasons.append("ACTIVE_ATTACK_COMPLETION_SOURCE_NOT_IN_LEDGER")
        if target_ref is None:
            reasons.append("ACTIVE_ATTACK_COMPLETION_TARGET_REF_INVALID")
        elif target_ref not in ledger.visible_refs:
            reasons.append("ACTIVE_ATTACK_COMPLETION_TARGET_NOT_IN_LEDGER")
        if source_ref is None or proposal.resource_cost.irreversible_refs != (
            source_ref,
        ):
            reasons.append("ACTIVE_ATTACK_COMPLETION_COST_MISMATCH")
        expected_reservation_ids = (ACTIVE_ATTACK_COMPLETION_RESERVATION_ID,)
        if proposal.reservation_ids != expected_reservation_ids:
            reasons.append("ACTIVE_ATTACK_COMPLETION_RESERVATION_ID_MISMATCH")
        if (
            proposal.proof.fact("reservation_id")
            != ACTIVE_ATTACK_COMPLETION_RESERVATION_ID
        ):
            reasons.append("ACTIVE_ATTACK_COMPLETION_PROOF_RESERVATION_MISMATCH")
        reservation = ledger.get_reservation(ACTIVE_ATTACK_COMPLETION_RESERVATION_ID)
        if reservation is None:
            reasons.append("ACTIVE_ATTACK_COMPLETION_RESERVATION_MISSING")
            if (
                source_ref is not None
                and ledger.reservation_for(source_ref) is not None
            ):
                reasons.append("ACTIVE_ATTACK_COMPLETION_FOREIGN_RESERVATION")
        else:
            bound_reservations = tuple(
                value
                for value in ledger.bound_reservations
                if value.reservation_id == ACTIVE_ATTACK_COMPLETION_RESERVATION_ID
            )
            if reservation.kind != ReservationKind.HARD_RESERVED:
                reasons.append("ACTIVE_ATTACK_COMPLETION_RESERVATION_NOT_HARD")
            if (
                source_ref is None
                or reservation.is_role_constraint
                or reservation.refs != (source_ref,)
                or len(bound_reservations) != 1
                or bound_reservations[0].refs != (source_ref,)
            ):
                reasons.append("ACTIVE_ATTACK_COMPLETION_RESERVATION_REF_MISMATCH")
            try:
                ephemeral = ledger.release(ACTIVE_ATTACK_COMPLETION_RESERVATION_ID)
            except ResourceLedgerError:
                reasons.append("ACTIVE_ATTACK_COMPLETION_RESERVATION_RELEASE_FAILED")
            else:
                if source_ref is not None:
                    cost_check = ephemeral.check_cost((source_ref,))
                    reasons.extend(
                        "LEDGER_COST_REJECTED:{0}".format(reason)
                        for reason in cost_check.rejection_reasons
                    )
    elif proposal.proof.schema in (
        ProofSchema.WALLY_SURVIVAL_V1,
        ProofSchema.CAPE_SURVIVAL_V1,
        ProofSchema.GUST_DOMINANCE_V1,
    ):
        pass
    elif proposal.proof.schema == ProofSchema.DECK_RULE_V1:
        cost_check = ledger.check_cost(proposal.resource_cost.irreversible_refs)
        reasons.extend(
            "LEDGER_COST_REJECTED:{0}".format(reason)
            for reason in cost_check.rejection_reasons
        )
        if proposal.reservation_ids:
            reasons.append("DECK_RULE_RESERVATION_FORBIDDEN")
        if proposal.transaction_plan is not None and not isinstance(
            proposal.transaction_plan,
            TransactionPlan,
        ):
            reasons.append("INVALID_TRANSACTION_PLAN")
    else:
        cost_check = ledger.check_cost(proposal.resource_cost.irreversible_refs)
        reasons.extend(
            "LEDGER_COST_REJECTED:{0}".format(reason)
            for reason in cost_check.rejection_reasons
        )
        if proposal.resource_cost.irreversible_refs:
            reasons.append("PROFILE_RESOURCE_COST_FORBIDDEN")
        for reservation_id in proposal.reservation_ids:
            if ledger.get_reservation(reservation_id) is None:
                reasons.append("UNKNOWN_RESERVATION_ID:{0}".format(reservation_id))
        if proposal.reservation_ids:
            reasons.append("PROFILE_RESERVATION_FORBIDDEN")
    if (
        proposal.proof.schema
        not in (
            ProofSchema.POKE_PAD_CORE_FORMATION_V1,
            ProofSchema.DECK_RULE_V1,
            ProofSchema.WALLY_SURVIVAL_V1,
            ProofSchema.CAPE_SURVIVAL_V1,
            ProofSchema.GUST_DOMINANCE_V1,
        )
        and proposal.transaction_plan is not None
    ):
        if not isinstance(proposal.transaction_plan, TransactionPlan):
            reasons.append("INVALID_TRANSACTION_PLAN")
        reasons.append("PROFILE_TRANSACTION_FORBIDDEN")
    if proposal.metrics.schema != MetricSchema.NO_CLAIMS_V1:
        reasons.append("METRIC_SCHEMA_FORBIDDEN")
    if proposal.metrics.has_claims:
        reasons.append("PROFILE_METRIC_CLAIM_FORBIDDEN")
    expected_tiebreak = _expected_tiebreak(proposal)
    if not expected_tiebreak:
        reasons.append("TIEBREAK_ACTION_MISMATCH")
    elif proposal.deterministic_tiebreak != expected_tiebreak:
        reasons.append("NONCANONICAL_TIEBREAK")

    unique_reasons = tuple(sorted(set(reasons)))
    return unique_reasons, None if unique_reasons else bound


def resolution_invariant_reasons(
    proposals: Sequence[Proposal],
    resolution: Resolution,
    *,
    state: Optional[PublicState] = None,
    legal_options: Optional[Sequence[SemanticOption]] = None,
) -> Tuple[str, ...]:
    """Audit the trace contract and, when supplied, the emitted raw binding."""

    if not isinstance(resolution, Resolution):
        return ("RESOLUTION_TYPE_INVALID",)
    proposal_values = tuple(proposals)
    if any(not isinstance(proposal, Proposal) for proposal in proposal_values):
        return ("PROPOSAL_TYPE_INVALID",)
    reasons = []
    evaluations = tuple(resolution.evaluations)
    if len(evaluations) != len(proposal_values):
        reasons.append("EVALUATION_COUNT_MISMATCH")
    if resolution.stats.proposed != len(proposal_values):
        reasons.append("PROPOSED_STATS_MISMATCH")

    proposal_keys = Counter(
        (
            proposal_digest(proposal),
            proposal.rule_id,
            action_spec_digest(proposal.action_spec),
        )
        for proposal in proposal_values
    )
    evaluation_keys = Counter(
        (
            evaluation.proposal_digest,
            evaluation.rule_id,
            evaluation.action_digest,
        )
        for evaluation in evaluations
    )
    if proposal_keys != evaluation_keys:
        reasons.append("EVALUATION_PROPOSAL_DIGEST_MISMATCH")

    selected_evaluations = tuple(
        value
        for value in evaluations
        if value.disposition == ProposalDisposition.SELECTED
    )
    valid_not_selected = tuple(
        value
        for value in evaluations
        if value.disposition == ProposalDisposition.VALID_NOT_SELECTED
    )
    rejected_evaluations = tuple(
        value
        for value in evaluations
        if value.disposition == ProposalDisposition.REJECTED
    )
    categorized_count = (
        len(selected_evaluations) + len(valid_not_selected) + len(rejected_evaluations)
    )
    if categorized_count != len(evaluations):
        reasons.append("EVALUATION_DISPOSITION_INVALID")
    if resolution.stats.accepted != len(selected_evaluations) + len(valid_not_selected):
        reasons.append("ACCEPTED_STATS_MISMATCH")
    if resolution.stats.rejected != len(rejected_evaluations):
        reasons.append("REJECTED_STATS_MISMATCH")
    if len(resolution.rejections) != len(rejected_evaluations):
        reasons.append("REJECTION_COUNT_MISMATCH")

    if resolution.selected is None:
        if selected_evaluations:
            reasons.append("SELECTED_DISPOSITION_WITHOUT_SELECTION")
        if resolution.bound_action is not None:
            reasons.append("BOUND_ACTION_WITHOUT_SELECTION")
    else:
        selected_key = (
            proposal_digest(resolution.selected),
            resolution.selected.rule_id,
            action_spec_digest(resolution.selected.action_spec),
        )
        if len(selected_evaluations) != 1:
            reasons.append("SELECTED_DISPOSITION_COUNT_INVALID")
        elif (
            selected_evaluations[0].proposal_digest,
            selected_evaluations[0].rule_id,
            selected_evaluations[0].action_digest,
        ) != selected_key:
            reasons.append("SELECTED_DISPOSITION_MISMATCH")
        if resolution.bound_action is None:
            reasons.append("SELECTION_WITHOUT_BOUND_ACTION")
        if (state is None) != (legal_options is None):
            reasons.append("BOUND_ACTION_VALIDATION_CONTEXT_INCOMPLETE")
        elif state is not None and legal_options is not None:
            if not isinstance(state, PublicState):
                reasons.append("BOUND_ACTION_STATE_INVALID")
            else:
                binding_reasons, expected_bound = _matching_option_reasons(
                    state,
                    legal_options,
                    resolution.selected.action_spec,
                )
                reasons.extend(
                    "BOUND_ACTION_REBIND:{0}".format(reason)
                    for reason in binding_reasons
                )
                if not binding_reasons and resolution.bound_action != expected_bound:
                    reasons.append("BOUND_ACTION_MISMATCH")

    if any(value.reasons for value in selected_evaluations):
        reasons.append("SELECTED_HAS_REASONS")
    if any(value.reasons != ("LOWER_RESOLVER_RANK",) for value in valid_not_selected):
        reasons.append("VALID_NOT_SELECTED_REASON_INVALID")
    if any(not value.reasons for value in rejected_evaluations):
        reasons.append("REJECTED_WITHOUT_REASONS")
    rejection_keys = Counter(
        (
            value.proposal_digest,
            value.rule_id,
            value.action_digest,
            value.reasons,
        )
        for value in resolution.rejections
    )
    rejected_evaluation_keys = Counter(
        (
            value.proposal_digest,
            value.rule_id,
            value.action_digest,
            value.reasons,
        )
        for value in rejected_evaluations
    )
    if rejection_keys != rejected_evaluation_keys:
        reasons.append("REJECTION_EVALUATION_MISMATCH")
    return tuple(sorted(set(reasons)))


def resolve_proposals(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    ledger: ResourceLedger,
    proposals: Sequence[Proposal],
    *,
    registry: Optional[PublicEffectRegistry] = None,
) -> Resolution:
    """Select one proposal without mutating transactions or synthesizing PASS."""

    if not isinstance(ledger, ResourceLedger):
        raise ValueError("resolver requires a ResourceLedger")
    if registry is not None and not isinstance(registry, PublicEffectRegistry):
        raise ValueError("resolver registry must be a PublicEffectRegistry")
    proposal_values = tuple(proposals)
    if any(not isinstance(proposal, Proposal) for proposal in proposal_values):
        raise ValueError("resolver proposals must all be Proposal values")

    rule_counts = Counter(proposal.rule_id for proposal in proposal_values)
    legal_option_index_reasons = _legal_option_index_reasons(legal_options)
    accepted = []
    rejected = []
    for proposal in proposal_values:
        current_proposal_digest = proposal_digest(proposal)
        current_action_digest = action_spec_digest(proposal.action_spec)
        reasons, bound = _validate_proposal(
            state,
            legal_options,
            ledger,
            proposal,
            duplicate_rule_id=rule_counts[proposal.rule_id] > 1,
            legal_option_index_reasons=legal_option_index_reasons,
            registry=registry,
        )
        if reasons:
            rejected.append(
                ProposalRejection(
                    proposal_digest=current_proposal_digest,
                    rule_id=proposal.rule_id,
                    action_digest=current_action_digest,
                    reasons=reasons,
                )
            )
        else:
            accepted.append(
                (
                    proposal_rank_key(proposal),
                    proposal,
                    bound,
                    current_proposal_digest,
                    current_action_digest,
                )
            )

    accepted.sort(key=lambda row: row[0])
    rejected_tuple = tuple(
        sorted(
            rejected,
            key=lambda value: (
                value.proposal_digest,
                value.rule_id,
                value.action_digest,
                value.reasons,
            ),
        )
    )
    selected = accepted[0] if accepted else None
    evaluations = [
        ProposalEvaluation(
            proposal_digest=rejection.proposal_digest,
            rule_id=rejection.rule_id,
            action_digest=rejection.action_digest,
            disposition=ProposalDisposition.REJECTED,
            reasons=rejection.reasons,
        )
        for rejection in rejected_tuple
    ]
    for index, row in enumerate(accepted):
        evaluations.append(
            ProposalEvaluation(
                proposal_digest=row[3],
                rule_id=row[1].rule_id,
                action_digest=row[4],
                disposition=(
                    ProposalDisposition.SELECTED
                    if index == 0
                    else ProposalDisposition.VALID_NOT_SELECTED
                ),
                reasons=() if index == 0 else ("LOWER_RESOLVER_RANK",),
            )
        )
    evaluations_tuple = tuple(
        sorted(
            evaluations,
            key=lambda value: (
                value.proposal_digest,
                value.rule_id,
                value.action_digest,
                value.disposition.value,
                value.reasons,
            ),
        )
    )
    resolution = Resolution(
        selected=None if selected is None else selected[1],
        bound_action=None if selected is None else selected[2],
        rejections=rejected_tuple,
        evaluations=evaluations_tuple,
        stats=ResolutionStats(
            proposed=len(proposal_values),
            accepted=len(accepted),
            rejected=len(rejected_tuple),
        ),
    )
    invariant_reasons = resolution_invariant_reasons(
        proposal_values,
        resolution,
        state=state,
        legal_options=legal_options,
    )
    if invariant_reasons:
        raise RuntimeError(
            "resolver trace invariant failed: {0}".format("|".join(invariant_reasons))
        )
    return resolution


__all__ = [
    "MetricSchema",
    "Proposal",
    "ProposalDisposition",
    "ProposalEvaluation",
    "ProposalRejection",
    "Resolution",
    "ResolutionStats",
    "ResolverMetrics",
    "ResolverTier",
    "ResourceCost",
    "action_spec_digest",
    "canonical_proposal_tiebreak",
    "proposal_digest",
    "proposal_rank_key",
    "resolve_proposals",
    "resolution_invariant_reasons",
]
