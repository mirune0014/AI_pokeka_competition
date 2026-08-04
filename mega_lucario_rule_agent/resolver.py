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
    from .certificates import (
        CertificateKind,
        CertificateProof,
        ProofSchema,
        legal_options_fingerprint,
    )
    from .resource_ledger import ResourceLedger
    from .state_view import (
        ActionSpec,
        OptionType,
        PhysicalRef,
        PublicState,
        SemanticBindError,
        SemanticOption,
        public_state_fingerprint,
    )
except ImportError:  # Flat submission import from main.py.
    from certificates import (
        CertificateKind,
        CertificateProof,
        ProofSchema,
        legal_options_fingerprint,
    )
    from resource_ledger import ResourceLedger
    from state_view import (
        ActionSpec,
        OptionType,
        PhysicalRef,
        PublicState,
        SemanticBindError,
        SemanticOption,
        public_state_fingerprint,
    )


class ResolverTier(IntEnum):
    ACTIVE_TRANSACTION_CONTINUATION = 1
    FORCED_OR_SETUP = 2
    EXACT_WIN_NOW = 3
    DENY_CERTAIN_LOSS = 4
    TERMINAL_OR_SUPERIOR_GUST = 5
    SURVIVAL_CRITICAL_WALLY = 6
    EXACT_CURRENT_TURN_PRIZE = 7
    SAME_ATTACK_PLUS_CONTINUITY = 8
    ATTACK_COMPLETION = 9
    CERTIFIED_EVOLUTION = 10
    ROUTE_CRITICAL_SEARCH = 11
    ROUTE_CRITICAL_MANUAL_ATTACH = 12
    SAFE_DRAW_OR_DISRUPTION = 13
    CERTIFIED_SURVIVAL = 14
    MINIMAL_PPP = 15
    BEST_CERTIFIED_ATTACK = 16
    SAFE_ENGINE_COMPLETION = 17
    RESOURCE_PRESERVING_FALLBACK = 18
    PASS = 19


class MetricSchema(str, Enum):
    NO_CLAIMS_V1 = "no_claims_v1"


def _optional_nonnegative_int(value: Optional[int], name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("{0} must be None or a non-negative exact integer".format(name))


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
        if not isinstance(self.metrics, ResolverMetrics):
            raise ValueError("proposal metrics must be ResolverMetrics")
        tiebreak = tuple(self.deterministic_tiebreak)
        if any(
            isinstance(value, bool) or not isinstance(value, (int, str))
            for value in tiebreak
        ):
            raise ValueError("deterministic_tiebreak must contain exact integers or strings")
        object.__setattr__(self, "tier", ResolverTier(self.tier))
        object.__setattr__(
            self,
            "certificate_kind",
            CertificateKind(self.certificate_kind),
        )
        object.__setattr__(self, "deterministic_tiebreak", tiebreak)


@dataclass(frozen=True)
class ProposalRejection:
    rule_id: str
    action_digest: str
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
    stats: ResolutionStats

    @property
    def has_selection(self) -> bool:
        return self.selected is not None


_BASELINE_ALLOWED_SCHEMA = ProofSchema.SAFE_FALLBACK_V1
_BASELINE_ALLOWED_KIND = CertificateKind.SAFE_FALLBACK
_BASELINE_ALLOWED_TIERS = frozenset(
    (
        ResolverTier.RESOURCE_PRESERVING_FALLBACK,
        ResolverTier.PASS,
    )
)
_BASELINE_ALLOWED_COMBINATIONS = frozenset(
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
    )
)


def action_spec_digest(action_spec: ActionSpec) -> str:
    payload = {
        "order_sensitive": bool(action_spec.order_sensitive),
        "choices": [choice.canonical() for choice in action_spec.choices],
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


def _expected_tiebreak(proposal: Proposal) -> Tuple[int, ...]:
    if len(proposal.action_spec.choices) != 1:
        return ()
    key = proposal.action_spec.choices[0]
    if key.option_type == int(OptionType.ATTACK):
        if (
            isinstance(key.attack_id, bool)
            or not isinstance(key.attack_id, int)
            or key.attack_id <= 0
        ):
            return ()
        return int(OptionType.ATTACK), int(key.attack_id)
    if key.option_type == int(OptionType.END):
        return (int(OptionType.END),)
    return ()


def _proposal_rank(proposal: Proposal) -> Tuple[Any, ...]:
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
        tuple(choice.canonical() for choice in proposal.action_spec.choices),
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
        index < 0 or index >= len(legal_options)
        for index in exact_indices
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
) -> Tuple[Tuple[str, ...], Optional[Tuple[int, ...]]]:
    reasons = []
    if duplicate_rule_id:
        reasons.append("DUPLICATE_RULE_ID")
    reasons.extend(legal_option_index_reasons)
    if not proposal.proof.is_valid:
        reasons.append("PROOF_INVALID")
    if proposal.certificate_kind != proposal.proof.kind:
        reasons.append("CERTIFICATE_KIND_MISMATCH")
    if proposal.proof.schema != _BASELINE_ALLOWED_SCHEMA:
        reasons.append("PROFILE_SCHEMA_FORBIDDEN")
    if proposal.certificate_kind != _BASELINE_ALLOWED_KIND:
        reasons.append("PROFILE_KIND_FORBIDDEN")
    if proposal.tier not in _BASELINE_ALLOWED_TIERS:
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
    if combination not in _BASELINE_ALLOWED_COMBINATIONS:
        reasons.append("PROFILE_OPTION_TYPE_FORBIDDEN")
    if proposal.proof.guaranteed_prizes != 0:
        reasons.append("PROFILE_PRIZE_CLAIM_FORBIDDEN")
    if proposal.proof.state_fingerprint != public_state_fingerprint(state):
        reasons.append("PROOF_STATE_STALE")
    if proposal.proof.action_spec != proposal.action_spec:
        reasons.append("PROOF_ACTION_MISMATCH")
    if (
        proposal.proof.fact("legal_options_fingerprint")
        != legal_options_fingerprint(legal_options)
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
    cost_check = ledger.check_cost(proposal.resource_cost.irreversible_refs)
    reasons.extend(
        "LEDGER_COST_REJECTED:{0}".format(reason)
        for reason in cost_check.rejection_reasons
    )
    if proposal.resource_cost.irreversible_refs:
        reasons.append("PROFILE_RESOURCE_COST_FORBIDDEN")
    if proposal.transaction_plan is not None:
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


def resolve_proposals(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    ledger: ResourceLedger,
    proposals: Sequence[Proposal],
) -> Resolution:
    """Select one proposal without mutating transactions or synthesizing PASS."""

    if not isinstance(ledger, ResourceLedger):
        raise ValueError("resolver requires a ResourceLedger")
    proposal_values = tuple(proposals)
    if any(not isinstance(proposal, Proposal) for proposal in proposal_values):
        raise ValueError("resolver proposals must all be Proposal values")

    rule_counts = Counter(proposal.rule_id for proposal in proposal_values)
    legal_option_index_reasons = _legal_option_index_reasons(legal_options)
    accepted = []
    rejected = []
    for proposal in proposal_values:
        reasons, bound = _validate_proposal(
            state,
            legal_options,
            ledger,
            proposal,
            duplicate_rule_id=rule_counts[proposal.rule_id] > 1,
            legal_option_index_reasons=legal_option_index_reasons,
        )
        if reasons:
            rejected.append(
                ProposalRejection(
                    rule_id=proposal.rule_id,
                    action_digest=action_spec_digest(proposal.action_spec),
                    reasons=reasons,
                )
            )
        else:
            accepted.append((_proposal_rank(proposal), proposal, bound))

    accepted.sort(key=lambda row: row[0])
    rejected_tuple = tuple(
        sorted(
            rejected,
            key=lambda value: (value.rule_id, value.action_digest, value.reasons),
        )
    )
    selected = accepted[0] if accepted else None
    return Resolution(
        selected=None if selected is None else selected[1],
        bound_action=None if selected is None else selected[2],
        rejections=rejected_tuple,
        stats=ResolutionStats(
            proposed=len(proposal_values),
            accepted=len(accepted),
            rejected=len(rejected_tuple),
        ),
    )


__all__ = [
    "MetricSchema",
    "Proposal",
    "ProposalRejection",
    "Resolution",
    "ResolutionStats",
    "ResolverMetrics",
    "ResolverTier",
    "ResourceCost",
    "action_spec_digest",
    "resolve_proposals",
]
