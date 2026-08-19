"""Closed, state-bound certificates for deterministic rule proposals."""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from enum import Enum, IntEnum
import hashlib
import json
import secrets
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

try:  # Package import in tests.
    from .attack_outcomes import (
        BoundAttackOutcomeTable,
        build_active_post_attach_attack_completion,
        build_gust_attack_outcome_table,
        build_post_wally_productive_attack,
        build_public_opponent_attack_threat,
        is_fully_exact_attack_completion_outcome,
    )
    from .card_meta import CARD_META_BY_ID
    from .features import (
        DeckFeatures,
        PublicMatchupFlag,
        build_deck_features,
        build_resource_ledger,
    )
    from .public_effects import PublicEffectRegistry
    from .resource_ledger import (
        DeckAvailabilityProof,
        ACTIVE_ATTACK_COMPLETION_RESERVATION_ID,
        MANUAL_ATTACH_ENERGY_RESERVATION_ID,
        ResourceLedger,
        prove_deck_availability_from_state,
    )
    from .state_view import (
        ActionSpec,
        AreaType,
        OptionType,
        PhysicalRef,
        PublicState,
        SemanticBindError,
        SemanticOption,
        SemanticOptionKey,
        is_stable_main_state,
        public_state_fingerprint,
        semantic_option_multiset,
    )
except ImportError:  # Flat submission import from main.py.
    from attack_outcomes import (
        BoundAttackOutcomeTable,
        build_active_post_attach_attack_completion,
        build_gust_attack_outcome_table,
        build_post_wally_productive_attack,
        build_public_opponent_attack_threat,
        is_fully_exact_attack_completion_outcome,
    )
    from card_meta import CARD_META_BY_ID
    from features import (
        DeckFeatures,
        PublicMatchupFlag,
        build_deck_features,
        build_resource_ledger,
    )
    from public_effects import PublicEffectRegistry
    from resource_ledger import (
        DeckAvailabilityProof,
        ACTIVE_ATTACK_COMPLETION_RESERVATION_ID,
        MANUAL_ATTACH_ENERGY_RESERVATION_ID,
        ResourceLedger,
        prove_deck_availability_from_state,
    )
    from state_view import (
        ActionSpec,
        AreaType,
        OptionType,
        PhysicalRef,
        PublicState,
        SemanticBindError,
        SemanticOption,
        SemanticOptionKey,
        is_stable_main_state,
        public_state_fingerprint,
        semantic_option_multiset,
    )


class CertificateKind(IntEnum):
    WIN_NOW = 0
    DENY_CERTAIN_LOSS = 1
    PRIZE_GAIN_NOW = 2
    SAME_ATTACK_PLUS_CONTINUITY = 3
    ATTACK_COMPLETION = 4
    FIRST_ATTACK_ACCELERATION = 5
    ENGINE_COMPLETION = 6
    RESOURCE_IMPROVEMENT = 7
    SAFE_FALLBACK = 8


class ProofSchema(str, Enum):
    SAFE_FALLBACK_V1 = "safe_fallback_v1"
    ATTACK_OUTCOME_V1 = "attack_outcome_v1"
    BASIC_BENCH_V1 = "basic_bench_v1"
    POKE_PAD_CORE_FORMATION_V1 = "poke_pad_core_formation_v1"
    FIRST_TURN_RIOLU_ATTACH_V1 = "first_turn_riolu_attach_v1"
    ACTIVE_POST_ATTACH_ATTACK_COMPLETION_V1 = "active_post_attach_attack_completion_v1"
    WALLY_SURVIVAL_V1 = "wally_survival_v1"
    CAPE_SURVIVAL_V1 = "cape_survival_v1"
    GUST_DOMINANCE_V1 = "gust_dominance_v1"
    DECK_RULE_V1 = "deck_rule_v1"


ACTIVE_ATTACK_COMPLETION_RULE_ID = (
    "R_ATTACH_002_GOING_SECOND_OT1_ACTIVE_SINGLE_ATTACK_COMPLETION_V1"
)
ACTIVE_ATTACK_COMPLETION_COVERAGE = "R_ATTACH_002_ACTIVE_COMPLETION_CLAUSE_ONLY"
ACTIVE_ATTACK_COMPLETION_UNRESOLVED = (
    "OPPONENT_DERIVED_ATTACK_LOCK_TRACKER",
    "METAL_TARGETS_EXCLUDED_DUE_UNSERIALIZED_IRON_DEFENDER",
    "PERSISTENT_TRAINERS_BOUND_TO_AUDITED_CATALOG_WITNESS",
)

FIRST_TURN_RIOLU_ATTACH_COVERAGE = "R_ATTACH_001_DEFAULT_CLAUSE_ONLY_V1"
FIRST_TURN_RIOLU_ATTACH_SCOPE = "RESOURCE_STAGING_ONLY"
FIRST_TURN_RIOLU_ATTACH_UNRESOLVED = (
    "ALTERNATIVE_NEXT_TURN_PRIZE",
    "NEXT_OPPONENT_TURN_MAX_DAMAGE",
)

POKE_PAD_CORE_COVERAGE_SCOPE = "POKE_PAD_CORE_FORMATION_ONLY"
POKE_PAD_CORE_UNRESOLVED_PRIORITIES = (
    "CURRENT_TURN_WIN_OR_PRIZE_SEARCH",
    "CURRENT_ATTACK_COMPLETION_SEARCH",
    "SAME_ATTACK_NEXT_ATTACKER_SEARCH",
    "MATCHUP_AND_SECOND_LINE_SEARCH",
)
POKE_PAD_EFFECT_ID = "POKE_PAD_CORE_SEARCH"
POKE_PAD_CARD_ID = 1152
POKE_PAD_ITEM_CARD_TYPE = 1
_FIGHTING_ENERGY_CARD_ID = 6
_RIOLU_CARD_ID = 677
_ACCELERATING_STAB_ATTACK_ID = 981

_BASIC_BENCH_CARD_IDS = frozenset((673, 675, 676, 677))
_BASIC_BENCH_ROLE_BY_CARD_ID = {
    673: "HARIYAMA_LINE",
    674: "HARIYAMA_LINE",
    675: "LUNATONE_ENGINE",
    676: "SOLROCK_ENGINE",
    677: "LUCARIO_LINE",
    678: "LUCARIO_LINE",
}
_BASIC_BENCH_PURPOSE_PRIORITY = {
    "ENGINE_COMPLETION": 0,
    "FIRST_RIOLU": 1,
    "BOARD_OUT_BACKUP": 2,
    "MATCHUP_MAKUHITA": 3,
    "SPREAD_BACKUP_RIOLU": 4,
}
_BASIC_BENCH_KIND = {
    "ENGINE_COMPLETION": CertificateKind.ENGINE_COMPLETION,
    "FIRST_RIOLU": CertificateKind.FIRST_ATTACK_ACCELERATION,
    "BOARD_OUT_BACKUP": CertificateKind.RESOURCE_IMPROVEMENT,
    "MATCHUP_MAKUHITA": CertificateKind.RESOURCE_IMPROVEMENT,
    "SPREAD_BACKUP_RIOLU": CertificateKind.FIRST_ATTACK_ACCELERATION,
}


_PROOF_ISSUER_TOKEN = object()
_PROOF_INTEGRITY_KEY = secrets.token_bytes(32)


def _canonical_fact_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, PhysicalRef):
        return value.sort_key()
    if isinstance(value, (tuple, list)):
        return tuple(_canonical_fact_value(item) for item in value)
    raise ValueError("certificate facts must be immutable primitive values")


def _canonical_action_spec(action_spec: ActionSpec) -> Tuple[Any, ...]:
    return action_spec.canonical()


def _proof_payload(
    *,
    kind: CertificateKind,
    schema: ProofSchema,
    state_fingerprint: str,
    action_spec: ActionSpec,
    is_valid: bool,
    guaranteed_prizes: int,
    facts: Tuple[Tuple[str, Any], ...],
    rejection_reasons: Tuple[str, ...],
) -> Mapping[str, Any]:
    return {
        "kind": int(kind),
        "schema": ProofSchema(schema).value,
        "state_fingerprint": state_fingerprint,
        "action_spec": _canonical_action_spec(action_spec),
        "is_valid": is_valid,
        "guaranteed_prizes": guaranteed_prizes,
        "facts": facts,
        "rejection_reasons": rejection_reasons,
    }


def _proof_integrity_digest(**values: Any) -> str:
    payload = _proof_payload(**values)
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(_PROOF_INTEGRITY_KEY + serialized).hexdigest()


def legal_options_fingerprint(options: Sequence[SemanticOption]) -> str:
    payload = [
        (key.canonical(), count) for key, count in semantic_option_multiset(options)
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class CertificateProof:
    kind: CertificateKind
    schema: ProofSchema
    state_fingerprint: str
    action_spec: ActionSpec
    is_valid: bool
    guaranteed_prizes: int
    facts: Tuple[Tuple[str, Any], ...]
    rejection_reasons: Tuple[str, ...]
    _issuer_token: object = dataclass_field(repr=False, compare=False)
    _integrity_digest: str = dataclass_field(
        default="",
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if self._issuer_token is not _PROOF_ISSUER_TOKEN:
            raise ValueError(
                "CertificateProof values must be created by a checked issuer"
            )
        if not isinstance(self.action_spec, ActionSpec):
            raise ValueError("certificate action_spec must be an ActionSpec")
        if (
            not isinstance(self.state_fingerprint, str)
            or len(self.state_fingerprint) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.state_fingerprint
            )
        ):
            raise ValueError(
                "certificate requires a lowercase SHA-256 state fingerprint"
            )
        if not isinstance(self.is_valid, bool):
            raise ValueError("certificate is_valid must be boolean")
        if (
            isinstance(self.guaranteed_prizes, bool)
            or not isinstance(self.guaranteed_prizes, int)
            or self.guaranteed_prizes < 0
        ):
            raise ValueError("guaranteed_prizes must be a non-negative exact integer")

        normalized_facts = []
        seen_names = set()
        for name, value in self.facts:
            if not isinstance(name, str) or not name:
                raise ValueError("certificate fact names must be non-empty strings")
            if name in seen_names:
                raise ValueError("certificate fact names must be unique")
            seen_names.add(name)
            normalized_facts.append((name, _canonical_fact_value(value)))
        normalized_reasons = tuple(sorted(set(self.rejection_reasons)))
        if any(
            not isinstance(reason, str) or not reason for reason in normalized_reasons
        ):
            raise ValueError("certificate rejection reasons must be non-empty strings")
        if self.is_valid and normalized_reasons:
            raise ValueError("a valid certificate cannot contain rejection reasons")
        if not self.is_valid and not normalized_reasons:
            raise ValueError("an invalid certificate must explain its rejection")
        if (
            self.is_valid
            and self.kind == CertificateKind.PRIZE_GAIN_NOW
            and self.guaranteed_prizes <= 0
        ):
            raise ValueError(
                "Prize-gain certificates must guarantee at least one Prize"
            )
        schema_kind_compatibility = {
            ProofSchema.SAFE_FALLBACK_V1: {CertificateKind.SAFE_FALLBACK},
            ProofSchema.ATTACK_OUTCOME_V1: {
                CertificateKind.WIN_NOW,
                CertificateKind.PRIZE_GAIN_NOW,
                CertificateKind.ATTACK_COMPLETION,
            },
            ProofSchema.BASIC_BENCH_V1: {
                CertificateKind.FIRST_ATTACK_ACCELERATION,
                CertificateKind.ENGINE_COMPLETION,
                CertificateKind.RESOURCE_IMPROVEMENT,
            },
            ProofSchema.POKE_PAD_CORE_FORMATION_V1: {
                CertificateKind.RESOURCE_IMPROVEMENT,
            },
            ProofSchema.FIRST_TURN_RIOLU_ATTACH_V1: {
                CertificateKind.FIRST_ATTACK_ACCELERATION,
            },
            ProofSchema.ACTIVE_POST_ATTACH_ATTACK_COMPLETION_V1: {
                CertificateKind.ATTACK_COMPLETION,
            },
            ProofSchema.WALLY_SURVIVAL_V1: {
                CertificateKind.RESOURCE_IMPROVEMENT,
            },
            ProofSchema.CAPE_SURVIVAL_V1: {
                CertificateKind.RESOURCE_IMPROVEMENT,
            },
            ProofSchema.GUST_DOMINANCE_V1: {
                CertificateKind.PRIZE_GAIN_NOW,
            },
            ProofSchema.DECK_RULE_V1: set(CertificateKind),
        }
        if (
            CertificateKind(self.kind)
            not in schema_kind_compatibility[ProofSchema(self.schema)]
        ):
            raise ValueError("certificate schema and kind are incompatible")

        expected_integrity = _proof_integrity_digest(
            kind=CertificateKind(self.kind),
            schema=ProofSchema(self.schema),
            state_fingerprint=self.state_fingerprint,
            action_spec=self.action_spec,
            is_valid=self.is_valid,
            guaranteed_prizes=self.guaranteed_prizes,
            facts=tuple(sorted(normalized_facts)),
            rejection_reasons=normalized_reasons,
        )
        if not secrets.compare_digest(self._integrity_digest, expected_integrity):
            raise ValueError("certificate integrity receipt does not match its fields")

        object.__setattr__(self, "kind", CertificateKind(self.kind))
        object.__setattr__(self, "schema", ProofSchema(self.schema))
        object.__setattr__(self, "facts", tuple(sorted(normalized_facts)))
        object.__setattr__(self, "rejection_reasons", normalized_reasons)

    def fact(self, name: str, default: Any = None) -> Any:
        return next((value for key, value in self.facts if key == name), default)

    def verify_integrity(self) -> bool:
        """Recheck the issuer receipt against the proof's current frozen fields."""

        if self._issuer_token is not _PROOF_ISSUER_TOKEN:
            return False
        try:
            if not isinstance(self.action_spec, ActionSpec):
                return False
            normalized_facts = []
            seen_names = set()
            for name, value in self.facts:
                if not isinstance(name, str) or not name or name in seen_names:
                    return False
                seen_names.add(name)
                normalized_facts.append((name, _canonical_fact_value(value)))
            normalized_reasons = tuple(sorted(set(self.rejection_reasons)))
            expected = _proof_integrity_digest(
                kind=CertificateKind(self.kind),
                schema=ProofSchema(self.schema),
                state_fingerprint=self.state_fingerprint,
                action_spec=self.action_spec,
                is_valid=self.is_valid,
                guaranteed_prizes=self.guaranteed_prizes,
                facts=tuple(sorted(normalized_facts)),
                rejection_reasons=normalized_reasons,
            )
        except (TypeError, ValueError):
            return False
        return secrets.compare_digest(self._integrity_digest, expected)

    def digest(self) -> str:
        payload = _proof_payload(
            kind=self.kind,
            schema=self.schema,
            state_fingerprint=self.state_fingerprint,
            action_spec=self.action_spec,
            is_valid=self.is_valid,
            guaranteed_prizes=self.guaranteed_prizes,
            facts=self.facts,
            rejection_reasons=self.rejection_reasons,
        )
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


def _make_proof(
    *,
    kind: CertificateKind,
    schema: ProofSchema,
    state: PublicState,
    action_spec: ActionSpec,
    is_valid: bool,
    guaranteed_prizes: int,
    facts: Mapping[str, Any],
    rejection_reasons: Iterable[str],
) -> CertificateProof:
    normalized_facts = tuple(
        sorted((name, _canonical_fact_value(value)) for name, value in facts.items())
    )
    normalized_reasons = tuple(sorted(set(rejection_reasons)))
    return CertificateProof(
        kind=kind,
        schema=schema,
        state_fingerprint=public_state_fingerprint(state),
        action_spec=action_spec,
        is_valid=is_valid,
        guaranteed_prizes=guaranteed_prizes,
        facts=normalized_facts,
        rejection_reasons=normalized_reasons,
        _issuer_token=_PROOF_ISSUER_TOKEN,
        _integrity_digest=_proof_integrity_digest(
            kind=kind,
            schema=schema,
            state_fingerprint=public_state_fingerprint(state),
            action_spec=action_spec,
            is_valid=is_valid,
            guaranteed_prizes=guaranteed_prizes,
            facts=normalized_facts,
            rejection_reasons=normalized_reasons,
        ),
    )


def safe_fallback_proof(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    action_spec: ActionSpec,
    reason_code: str,
) -> CertificateProof:
    if not isinstance(reason_code, str) or not reason_code.strip():
        raise ValueError("safe fallback reason_code must be non-empty")
    if not is_stable_main_state(state):
        raise ValueError("safe fallback requires an unfinished stable MAIN state")
    if len(action_spec.choices) != 1:
        raise ValueError("safe fallback requires exactly one semantic action")
    action_key = action_spec.choices[0]
    if action_key.player_index != state.seat:
        raise ValueError("safe fallback action owner must match the acting seat")
    if action_key.option_type not in (int(OptionType.ATTACK), int(OptionType.END)):
        raise ValueError("safe fallback proof only covers ATTACK or END")
    if action_key.option_type == int(OptionType.ATTACK) and (
        isinstance(action_key.attack_id, bool)
        or not isinstance(action_key.attack_id, int)
        or action_key.attack_id <= 0
    ):
        raise ValueError("safe fallback ATTACK requires an exact positive attack_id")
    if (
        action_key.option_type == int(OptionType.END)
        and action_key.attack_id is not None
    ):
        raise ValueError("safe fallback END cannot carry an attack_id")
    try:
        rebound = action_spec.bind(
            legal_options,
            min_count=state.min_count,
            max_count=state.max_count,
        )
    except SemanticBindError as error:
        raise ValueError(
            "safe fallback action must bind uniquely to the current legal options"
        ) from error
    if len(rebound) != 1:
        raise ValueError("safe fallback must resolve to exactly one legal option")
    return _make_proof(
        kind=CertificateKind.SAFE_FALLBACK,
        schema=ProofSchema.SAFE_FALLBACK_V1,
        state=state,
        action_spec=action_spec,
        is_valid=True,
        guaranteed_prizes=0,
        facts={
            "reason_code": reason_code.strip(),
            "option_type": action_key.option_type,
            "attack_id": action_key.attack_id,
            "legal_options_fingerprint": legal_options_fingerprint(legal_options),
        },
        rejection_reasons=(),
    )


_RESERVED_DECK_ROUTE_CODES = frozenset(
    (
        "R_WALLY_THREE_PRIZE_REBOOT_V1",
        "R_CAPE_EXPLICIT_PROTECTION_V1",
        "R_GUST_BOSS_EXACT_DOMINANCE_A3",
        "R_GUST_HARIYAMA_EXACT_DOMINANCE_A3",
    )
)


def deck_rule_proof(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    registry: PublicEffectRegistry,
    features: DeckFeatures,
    action_spec: ActionSpec,
    *,
    route_code: str,
    kind: CertificateKind,
    guaranteed_prizes: int = 0,
    facts: Optional[Mapping[str, Any]] = None,
) -> CertificateProof:
    """Issue one narrow, state-bound proof for an integrated deck rule."""

    if not isinstance(route_code, str) or not route_code.strip():
        raise ValueError("deck route_code must be a non-empty string")
    if route_code != route_code.strip():
        raise ValueError("deck route_code must be trimmed")
    if route_code in _RESERVED_DECK_ROUTE_CODES:
        raise ValueError("reserved routes require a dedicated checked proof schema")
    if not is_stable_main_state(state):
        raise ValueError("deck rules require stable MAIN")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("deck rules require a checked registry")
    if not isinstance(features, DeckFeatures) or not features.matches(
        state,
        legal_options,
        registry,
    ):
        raise ValueError("deck rules require current checked features")
    if not isinstance(action_spec, ActionSpec) or len(action_spec.choices) != 1:
        raise ValueError("deck rules require exactly one semantic action")
    try:
        rebound = action_spec.bind(
            legal_options,
            min_count=state.min_count,
            max_count=state.max_count,
        )
    except SemanticBindError as error:
        raise ValueError("deck rule action must bind uniquely") from error
    if len(rebound) != 1:
        raise ValueError("deck rule action must resolve to one option")
    kind_value = CertificateKind(kind)
    if (
        isinstance(guaranteed_prizes, bool)
        or not isinstance(guaranteed_prizes, int)
        or guaranteed_prizes < 0
    ):
        raise ValueError("guaranteed_prizes must be a non-negative exact int")
    if kind_value in (CertificateKind.WIN_NOW, CertificateKind.PRIZE_GAIN_NOW):
        if guaranteed_prizes <= 0:
            raise ValueError("winning and Prize deck rules require a Prize claim")
    elif guaranteed_prizes != 0:
        raise ValueError("non-Prize deck rules cannot claim guaranteed Prizes")

    supplied = dict(facts or {})
    reserved_names = {
        "route_code",
        "option_type",
        "legal_options_fingerprint",
        "registry_digest",
        "features_digest",
    }
    if reserved_names.intersection(supplied):
        raise ValueError("deck rule facts cannot replace bound common facts")
    supplied.update(
        {
            "route_code": route_code,
            "option_type": action_spec.choices[0].option_type,
            "legal_options_fingerprint": legal_options_fingerprint(legal_options),
            "registry_digest": registry.digest,
            "features_digest": features.digest(),
        }
    )
    return _make_proof(
        kind=kind_value,
        schema=ProofSchema.DECK_RULE_V1,
        state=state,
        action_spec=action_spec,
        is_valid=True,
        guaranteed_prizes=guaranteed_prizes,
        facts=supplied,
        rejection_reasons=(),
    )


def _is_exact_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _manual_attach_refs(
    state: PublicState,
    key: SemanticOptionKey,
) -> Optional[Tuple[PhysicalRef, Any]]:
    if (
        not isinstance(key, SemanticOptionKey)
        or not _is_exact_int(key.card_serial)
        or key.card_serial < 0
        or not _is_exact_int(key.target_zone)
        or key.target_zone not in (int(AreaType.ACTIVE), int(AreaType.BENCH))
        or not _is_exact_int(key.target_lineage_serial)
        or key.target_lineage_serial < 0
    ):
        return None
    expected = SemanticOptionKey(
        option_type=int(OptionType.ATTACH),
        player_index=state.seat,
        card_id=_FIGHTING_ENERGY_CARD_ID,
        card_serial=int(key.card_serial),
        source_zone=int(AreaType.HAND),
        target_zone=int(key.target_zone),
        target_lineage_serial=int(key.target_lineage_serial),
    )
    if key != expected:
        return None
    sources = tuple(
        ref_value
        for ref_value in state.own.hand_refs
        if (
            ref_value.card_id == _FIGHTING_ENERGY_CARD_ID
            and ref_value.serial == key.card_serial
            and ref_value.owner == state.seat
            and ref_value.zone == int(AreaType.HAND)
        )
    )
    board = (
        state.own.active if key.target_zone == int(AreaType.ACTIVE) else state.own.bench
    )
    targets = tuple(
        pokemon
        for pokemon in board
        if (
            pokemon.ref.card_id == _RIOLU_CARD_ID
            and pokemon.ref.owner == state.seat
            and pokemon.ref.zone == key.target_zone
            and pokemon.lineage_serial == key.target_lineage_serial
            and _is_exact_int(pokemon.ref.serial)
            and not pokemon.energy_types
            and not pokemon.energy_refs
        )
    )
    if len(sources) != 1 or len(targets) != 1:
        return None
    return sources[0], targets[0]


def _riolu_attach_rows(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    features: DeckFeatures,
) -> Tuple[Tuple[Any, ...], ...]:
    rows = []
    for option in legal_options:
        refs = _manual_attach_refs(state, option.key)
        if refs is None:
            continue
        source_ref, target = refs
        deficits = tuple(
            value
            for value in features.attack_energy_deficit_by_target
            if (
                value.target_ref == target.ref
                and value.current_card_id == _RIOLU_CARD_ID
                and value.minimum_attack_cost == 1
                and value.attached_energy_count == 0
                and value.deficit_now == 1
                and value.deficit_after_one_attach == 0
            )
        )
        if len(deficits) != 1:
            continue
        zone_priority = 0 if target.ref.zone == int(AreaType.ACTIVE) else 1
        rank = (
            zone_priority,
            -int(target.remaining_hp),
            int(target.lineage_serial),
            int(source_ref.serial),
            option.key.sort_key(),
        )
        rows.append(
            (
                rank,
                option.key,
                source_ref,
                target.ref,
                int(target.remaining_hp),
                zone_priority,
            )
        )
    return tuple(sorted(rows, key=lambda row: row[0]))


def first_turn_riolu_attach_proof(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    registry: PublicEffectRegistry,
    features: DeckFeatures,
    action_spec: ActionSpec,
) -> CertificateProof:
    """Certify only the default first-turn Riolu Energy-staging clause."""

    if not is_stable_main_state(state):
        raise ValueError("first-turn Riolu attach requires stable MAIN")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("first-turn Riolu attach requires a checked registry")
    if not isinstance(features, DeckFeatures) or not features.matches(
        state,
        legal_options,
        registry,
    ):
        raise ValueError("first-turn Riolu attach requires current checked features")
    if (
        state.first_player not in (0, 1)
        or state.seat != state.first_player
        or state.turn != 1
        or features.own_turn_number != 1
        or state.energy_attached
        or features.manual_attach_used
        or state.attacked_this_turn
        or features.attacked_this_turn
    ):
        raise ValueError("first-turn Riolu attach timing is not exact")
    if features.legal_attack_ids or any(
        option.key.option_type == int(OptionType.ATTACK) for option in legal_options
    ):
        raise ValueError("first-turn Riolu attach cannot coexist with a legal attack")
    energy_profile = registry.effect_profile(_FIGHTING_ENERGY_CARD_ID)
    if (
        not registry.is_effectless_basic_energy(_FIGHTING_ENERGY_CARD_ID)
        or energy_profile is None
        or energy_profile.energy_type != 6
        or not registry.binding_admitted(
            "ACCELERATING_STAB",
            card_id=_RIOLU_CARD_ID,
            entry_id=_ACCELERATING_STAB_ATTACK_ID,
        )
    ):
        raise ValueError("first-turn Riolu attach metadata is not fully admitted")
    if len(action_spec.choices) != 1:
        raise ValueError("first-turn Riolu attach requires exactly one action")
    rows = _riolu_attach_rows(state, legal_options, features)
    if not rows or action_spec.choices[0] != rows[0][1]:
        raise ValueError("first-turn Riolu attach action is not canonical")
    try:
        rebound = action_spec.bind(
            legal_options,
            min_count=state.min_count,
            max_count=state.max_count,
        )
    except SemanticBindError as error:
        raise ValueError("first-turn Riolu attach must bind uniquely") from error
    if len(rebound) != 1:
        raise ValueError("first-turn Riolu attach must resolve to one option")

    rank, _, source_ref, target_ref, remaining_hp, zone_priority = rows[0]
    return _make_proof(
        kind=CertificateKind.FIRST_ATTACK_ACCELERATION,
        schema=ProofSchema.FIRST_TURN_RIOLU_ATTACH_V1,
        state=state,
        action_spec=action_spec,
        is_valid=True,
        guaranteed_prizes=0,
        facts={
            "legal_options_fingerprint": legal_options_fingerprint(legal_options),
            "state_digest": public_state_fingerprint(state),
            "registry_digest": registry.digest,
            "features_digest": features.digest(),
            "option_type": int(OptionType.ATTACH),
            "source_ref": source_ref,
            "target_ref": target_ref,
            "reservation_id": MANUAL_ATTACH_ENERGY_RESERVATION_ID,
            "attack_id": _ACCELERATING_STAB_ATTACK_ID,
            "energy_count_before": 0,
            "energy_count_after": 1,
            "deficit_before": 1,
            "deficit_after": 0,
            "coverage": FIRST_TURN_RIOLU_ATTACH_COVERAGE,
            "proof_scope": FIRST_TURN_RIOLU_ATTACH_SCOPE,
            "full_requirement_compliance": False,
            "unresolved_exception_codes": FIRST_TURN_RIOLU_ATTACH_UNRESOLVED,
            "target_zone_priority": zone_priority,
            "target_remaining_hp": remaining_hp,
            "target_lineage_serial": int(target_ref.lineage_serial),
            "energy_serial": int(source_ref.serial),
            "canonical_rank": rank[:-1],
        },
        rejection_reasons=(),
    )


def _active_attack_completion_attach_refs(
    state: PublicState,
    key: SemanticOptionKey,
) -> Optional[Tuple[PhysicalRef, PhysicalRef]]:
    active = state.own_active
    if (
        active is None
        or not isinstance(key, SemanticOptionKey)
        or not _is_exact_int(key.card_serial)
        or key.card_serial < 0
        or not _is_exact_int(key.target_lineage_serial)
        or key.target_lineage_serial < 0
    ):
        return None
    expected = SemanticOptionKey(
        option_type=int(OptionType.ATTACH),
        player_index=state.seat,
        card_id=_FIGHTING_ENERGY_CARD_ID,
        card_serial=int(key.card_serial),
        source_zone=int(AreaType.HAND),
        target_zone=int(AreaType.ACTIVE),
        target_lineage_serial=int(key.target_lineage_serial),
    )
    if key != expected:
        return None
    sources = tuple(
        ref_value
        for ref_value in state.own.hand_refs
        if (
            ref_value.card_id == _FIGHTING_ENERGY_CARD_ID
            and ref_value.serial == key.card_serial
            and ref_value.owner == state.seat
            and ref_value.zone == int(AreaType.HAND)
        )
    )
    if (
        len(sources) != 1
        or len(state.own.active) != 1
        or active.ref.owner != state.seat
        or active.ref.zone != int(AreaType.ACTIVE)
        or active.ref.lineage_serial != key.target_lineage_serial
    ):
        return None
    return sources[0], active.ref


def _active_attack_completion_rows(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    registry: PublicEffectRegistry,
) -> Tuple[Tuple[Any, ...], ...]:
    rows = []
    for option in legal_options:
        refs = _active_attack_completion_attach_refs(state, option.key)
        if refs is None:
            continue
        source_ref, target_ref = refs
        completion = build_active_post_attach_attack_completion(
            state,
            legal_options,
            registry,
            source_ref,
            target_ref,
        )
        if completion is None:
            continue
        rank = (
            int(source_ref.serial),
            option.key.sort_key(),
        )
        rows.append((rank, option.key, completion))
    return tuple(sorted(rows, key=lambda row: row[0]))


def active_post_attach_attack_completion_proof(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    registry: PublicEffectRegistry,
    action_spec: ActionSpec,
) -> CertificateProof:
    """Certify the one-attach Active attack-completion rule."""

    if not is_stable_main_state(state):
        raise ValueError("Active attack completion requires stable MAIN")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("Active attack completion requires a checked registry")
    if len(action_spec.choices) != 1:
        raise ValueError("Active attack completion requires exactly one action")
    rows = _active_attack_completion_rows(state, legal_options, registry)
    if not rows or action_spec.choices[0] != rows[0][1]:
        raise ValueError("Active attack completion action is not canonical")
    try:
        rebound = action_spec.bind(
            legal_options,
            min_count=state.min_count,
            max_count=state.max_count,
        )
    except SemanticBindError as error:
        raise ValueError(
            "Active attack completion ATTACH must bind uniquely"
        ) from error
    if len(rebound) != 1:
        raise ValueError("Active attack completion must resolve to one ATTACH")

    _, _, completion = rows[0]
    candidate_rows = completion.candidate_rows
    return _make_proof(
        kind=CertificateKind.ATTACK_COMPLETION,
        schema=ProofSchema.ACTIVE_POST_ATTACH_ATTACK_COMPLETION_V1,
        state=state,
        action_spec=action_spec,
        is_valid=True,
        guaranteed_prizes=0,
        facts={
            "legal_options_fingerprint": legal_options_fingerprint(legal_options),
            "state_digest": public_state_fingerprint(state),
            "registry_digest": registry.digest,
            "catalog_sha256": completion.catalog_sha256,
            "persistent_trainer_audit_fingerprint": (
                completion.persistent_trainer_audit_fingerprint
            ),
            "rule_id": ACTIVE_ATTACK_COMPLETION_RULE_ID,
            "option_type": int(OptionType.ATTACH),
            "source_ref": completion.source_ref,
            "target_ref": completion.target_ref,
            "reservation_id": ACTIVE_ATTACK_COMPLETION_RESERVATION_ID,
            "target_energy_type": completion.target_energy_type,
            "target_energy_type_exact": True,
            "metal_targets_excluded": True,
            "persistent_trainer_tracking_scope": "FULL_CATALOG_1140_1228_WITNESS",
            "energy_card_id": _FIGHTING_ENERGY_CARD_ID,
            "energy_type": 6,
            "energy_serial": int(completion.source_ref.serial),
            "energy_types_before": completion.energy_types_before,
            "energy_types_after": completion.energy_types_after,
            "coverage": ACTIVE_ATTACK_COMPLETION_COVERAGE,
            "full_requirement_compliance": False,
            "unresolved_requirement_codes": ACTIVE_ATTACK_COMPLETION_UNRESOLVED,
            "global_turn": 2,
            "own_turn_number": 1,
            "pre_payable": completion.pre_payable,
            "post_payable": completion.post_payable,
            "post_table_and_outcome_fully_exact": True,
            "deficit_before": 1,
            "deficit_after": 0,
            "attack_id": completion.chosen_attack_id,
            "chosen_attack_id": completion.chosen_attack_id,
            "chosen_final_damage": completion.chosen_final_damage,
            "chosen_future_lock_cost": completion.chosen_future_lock_cost,
            "chosen_energy_cost": completion.chosen_energy_cost,
            "candidate_set": candidate_rows,
            "candidate_attack_ids": tuple(row[0] for row in candidate_rows),
            "canonical_attack_rank": (
                -completion.chosen_final_damage,
                completion.chosen_future_lock_cost,
                completion.chosen_attack_id,
                completion.chosen_energy_cost,
            ),
            "currently_legal_attack_ids": completion.pre_payable,
            "same_attack_locked": False,
            "status_and_turn_legal": True,
            "exact_positive_damage": True,
            "consumes_manual_attach": True,
            "transaction_owner_required": False,
        },
        rejection_reasons=(),
    )


def _basic_play_source_ref(
    state: PublicState,
    key: SemanticOptionKey,
) -> Optional[PhysicalRef]:
    if (
        not isinstance(key, SemanticOptionKey)
        or not _is_exact_int(key.card_id)
        or not _is_exact_int(key.card_serial)
    ):
        return None
    expected = SemanticOptionKey(
        option_type=int(OptionType.PLAY),
        player_index=state.seat,
        card_id=int(key.card_id),
        card_serial=int(key.card_serial),
        source_zone=int(AreaType.HAND),
    )
    if (
        key != expected
        or key.card_id not in _BASIC_BENCH_CARD_IDS
        or key.card_serial < 0
    ):
        return None
    matches = tuple(
        ref_value
        for ref_value in state.own.hand_refs
        if (
            ref_value.card_id == key.card_id
            and ref_value.serial == key.card_serial
            and ref_value.owner == state.seat
            and ref_value.zone == int(AreaType.HAND)
        )
    )
    if len(matches) != 1:
        return None
    meta = CARD_META_BY_ID.get(int(key.card_id))
    if meta is None or not meta.basic:
        return None
    return matches[0]


def _basic_bench_purpose(
    features: DeckFeatures,
    card_id: int,
) -> Optional[str]:
    if card_id in features.missing_engine_card_ids:
        return "ENGINE_COMPLETION"
    if card_id == 677 and features.lucario_line_count == 0:
        return "FIRST_RIOLU"
    if features.board_out_risk:
        return "BOARD_OUT_BACKUP"
    flags = frozenset(features.public_flags)
    if (
        card_id == 673
        and features.hariyama_line_count == 0
        and flags.intersection(
            (
                PublicMatchupFlag.EX_DAMAGE_PREVENTION,
                PublicMatchupFlag.ONE_PRIZE_MEDIUM_HP_RESISTANT,
            )
        )
    ):
        return "MATCHUP_MAKUHITA"
    if (
        card_id == 677
        and features.lucario_line_count < 2
        and PublicMatchupFlag.BENCH_SPREAD_THREAT in flags
    ):
        return "SPREAD_BACKUP_RIOLU"
    return None


def _basic_board_role(card_id: Optional[int]) -> Optional[str]:
    if not _is_exact_int(card_id):
        return None
    return _BASIC_BENCH_ROLE_BY_CARD_ID.get(int(card_id))


def _board_out_choice_rank(
    state: PublicState,
    key: SemanticOptionKey,
) -> Tuple[Any, ...]:
    occupied_roles = frozenset(
        role
        for role in (
            _basic_board_role(pokemon.ref.card_id)
            for pokemon in state.own.active + state.own.bench
        )
        if role is not None
    )
    role = _basic_board_role(key.card_id)
    meta = CARD_META_BY_ID.get(int(key.card_id))
    hp = meta.hp if meta is not None and _is_exact_int(meta.hp) else 0
    return (
        int(role is None or role in occupied_roles),
        -int(hp),
        int(key.card_id),
        int(key.card_serial),
        key.sort_key(),
    )


def basic_bench_proof(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    registry: PublicEffectRegistry,
    features: DeckFeatures,
    action_spec: ActionSpec,
) -> CertificateProof:
    """Certify one exact role-improving Basic placement from HAND to Bench."""

    if not is_stable_main_state(state):
        raise ValueError("Basic Bench proof requires an unfinished stable MAIN state")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("Basic Bench proof requires a checked registry")
    if not isinstance(features, DeckFeatures) or not features.matches(
        state,
        legal_options,
        registry,
    ):
        raise ValueError("Basic Bench proof requires current checked features")
    if len(action_spec.choices) != 1:
        raise ValueError("Basic Bench proof requires exactly one semantic action")
    key = action_spec.choices[0]
    source_ref = _basic_play_source_ref(state, key)
    if source_ref is None:
        raise ValueError("Basic Bench action requires one exact own HAND Basic")
    if len(state.own.bench) >= state.own.bench_max:
        raise ValueError("Basic Bench action requires a physical Bench slot")
    try:
        rebound = action_spec.bind(
            legal_options,
            min_count=state.min_count,
            max_count=state.max_count,
        )
    except SemanticBindError as error:
        raise ValueError(
            "Basic Bench action must bind uniquely to the current legal options"
        ) from error
    if len(rebound) != 1:
        raise ValueError("Basic Bench action must resolve to exactly one option")

    candidate_rows = []
    for option in legal_options:
        candidate_ref = _basic_play_source_ref(state, option.key)
        if candidate_ref is None:
            continue
        purpose = _basic_bench_purpose(features, int(option.key.card_id))
        if purpose is not None:
            candidate_rows.append((option.key, candidate_ref, purpose))
    if not candidate_rows:
        raise ValueError("no role-improving Basic Bench candidate is proven")
    best_priority = min(
        _BASIC_BENCH_PURPOSE_PRIORITY[purpose] for _, _, purpose in candidate_rows
    )
    purpose = _basic_bench_purpose(features, int(key.card_id))
    if purpose is None or _BASIC_BENCH_PURPOSE_PRIORITY[purpose] != best_priority:
        raise ValueError("Basic Bench action is below the current role priority")
    if features.safe_bench_slots <= 0 and not (
        purpose == "BOARD_OUT_BACKUP" and features.board_out_risk
    ):
        raise ValueError("Basic Bench action would consume the flexible Bench slot")
    if purpose == "BOARD_OUT_BACKUP":
        boardout_keys = tuple(
            candidate_key
            for candidate_key, _, candidate_purpose in candidate_rows
            if candidate_purpose == purpose
        )
        if key != min(
            boardout_keys,
            key=lambda value: _board_out_choice_rank(state, value),
        ):
            raise ValueError("Basic Bench board-out backup is not canonical")

    board_ids = tuple(
        int(pokemon.ref.card_id)
        for pokemon in state.own.active + state.own.bench
        if _is_exact_int(pokemon.ref.card_id)
    )
    after_ids = board_ids + (int(key.card_id),)
    engine_after = 675 in after_ids and 676 in after_ids
    lucario_after = sum(card_id in (677, 678) for card_id in after_ids)
    hariyama_after = sum(card_id in (673, 674) for card_id in after_ids)
    return _make_proof(
        kind=_BASIC_BENCH_KIND[purpose],
        schema=ProofSchema.BASIC_BENCH_V1,
        state=state,
        action_spec=action_spec,
        is_valid=True,
        guaranteed_prizes=0,
        facts={
            "legal_options_fingerprint": legal_options_fingerprint(legal_options),
            "registry_digest": registry.digest,
            "features_digest": features.digest(),
            "option_type": int(OptionType.PLAY),
            "source_ref": source_ref,
            "purpose": purpose,
            "purpose_priority": _BASIC_BENCH_PURPOSE_PRIORITY[purpose],
            "bench_count_before": len(state.own.bench),
            "bench_count_after": len(state.own.bench) + 1,
            "bench_max": state.own.bench_max,
            "safe_bench_slots_before": features.safe_bench_slots,
            "safe_bench_slots_after": max(0, features.safe_bench_slots - 1),
            "board_out_risk_before": features.board_out_risk,
            "board_out_risk_after": len(after_ids) <= 1,
            "engine_complete_before": features.engine_complete,
            "engine_complete_after": engine_after,
            "lucario_line_count_before": features.lucario_line_count,
            "lucario_line_count_after": lucario_after,
            "hariyama_line_count_before": features.hariyama_line_count,
            "hariyama_line_count_after": hariyama_after,
            "public_flags": tuple(flag.value for flag in features.public_flags),
        },
        rejection_reasons=(),
    )


def poke_pad_core_eligible_classes(
    state: PublicState,
) -> Tuple[Tuple[int, ...], ...]:
    """Return only currently missing core Basic roles in approved order."""

    if not isinstance(state, PublicState):
        raise ValueError("Poke Pad role derivation requires a PublicState")
    known_ids = {
        int(ref_value.card_id)
        for ref_value in state.own.hand_refs
        if _is_exact_int(ref_value.card_id)
    }
    for pokemon in state.own.active + state.own.bench:
        if _is_exact_int(pokemon.ref.card_id):
            known_ids.add(int(pokemon.ref.card_id))
        known_ids.update(
            int(ref_value.card_id)
            for ref_value in pokemon.pre_evolution_refs
            if _is_exact_int(ref_value.card_id)
        )
    classes = []
    for engine_card_id in (675, 676):
        if engine_card_id not in known_ids:
            classes.append((engine_card_id,))
    if not known_ids.intersection((677, 678)):
        classes.append((677,))
    return tuple(classes)


def _poke_pad_source_rows(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
) -> Tuple[Tuple[SemanticOptionKey, PhysicalRef], ...]:
    rows = []
    hand_refs = {
        (
            ref_value.card_id,
            ref_value.serial,
            ref_value.owner,
            ref_value.zone,
        ): ref_value
        for ref_value in state.own.hand_refs
        if ref_value.card_id == POKE_PAD_CARD_ID
    }
    for option in legal_options:
        key = option.key
        expected = SemanticOptionKey(
            option_type=int(OptionType.PLAY),
            player_index=state.seat,
            card_id=POKE_PAD_CARD_ID,
            card_serial=key.card_serial,
            source_zone=int(AreaType.HAND),
        )
        if key != expected or not _is_exact_int(key.card_serial) or key.card_serial < 0:
            continue
        source_ref = hand_refs.get(
            (
                POKE_PAD_CARD_ID,
                int(key.card_serial),
                state.seat,
                int(AreaType.HAND),
            )
        )
        if source_ref is not None:
            rows.append((key, source_ref))
    return tuple(
        sorted(
            rows,
            key=lambda row: (int(row[1].serial), row[0].sort_key()),
        )
    )


def _poke_pad_attack_preservation_facts(
    attack_outcomes: BoundAttackOutcomeTable,
) -> Tuple[Tuple[object, ...], ...]:
    if attack_outcomes.rows:
        if attack_outcomes.build_unknown_reasons or any(
            not row.exact or row.callback is not None for row in attack_outcomes.rows
        ):
            raise ValueError("Poke Pad requires exact current attack rows")
    elif attack_outcomes.build_unknown_reasons != ("NO_ATTACK_OPTION",):
        raise ValueError("Poke Pad requires an exact empty attack surface")
    return tuple(
        (
            row.option_key.canonical(),
            row.attack_id,
            row.exact_game_win,
            row.exact_ko,
            row.prizes_taken,
            row.wins_game,
        )
        for row in attack_outcomes.rows
    )


def poke_pad_core_formation_proof(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    registry: PublicEffectRegistry,
    features: DeckFeatures,
    attack_outcomes: BoundAttackOutcomeTable,
    availability_proof: DeckAvailabilityProof,
    action_spec: ActionSpec,
) -> CertificateProof:
    """Certify the narrow Poke Pad engine/first-Riolu formation prefix."""

    if not is_stable_main_state(state):
        raise ValueError("Poke Pad search requires stable MAIN")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("Poke Pad search requires a checked registry")
    if not isinstance(features, DeckFeatures) or not features.matches(
        state,
        legal_options,
        registry,
    ):
        raise ValueError("Poke Pad search requires current checked features")
    if not isinstance(attack_outcomes, BoundAttackOutcomeTable) or not (
        attack_outcomes.matches(state, legal_options, registry)
    ):
        raise ValueError("Poke Pad search requires the current attack table")
    attack_facts = _poke_pad_attack_preservation_facts(attack_outcomes)
    effect_profile = registry.effect_profile(POKE_PAD_CARD_ID)
    if (
        effect_profile is None
        or effect_profile.card_name != "poke pad"
        or effect_profile.card_type != POKE_PAD_ITEM_CARD_TYPE
        or effect_profile.energy_type != 0
        or not effect_profile.all_skills_registered
        or len(effect_profile.skill_signatures) != 1
        or effect_profile.registered_skill_effect_ids != (POKE_PAD_EFFECT_ID,)
        or not registry.binding_admitted(
            POKE_PAD_EFFECT_ID,
            card_id=POKE_PAD_CARD_ID,
            entry_id=0,
        )
    ):
        raise ValueError("Poke Pad catalog/effect identity is not fully admitted")
    if features.safe_bench_slots <= 0:
        raise ValueError("Poke Pad target has no flex-safe Bench slot")
    classes = poke_pad_core_eligible_classes(state)
    if not classes:
        raise ValueError("Poke Pad has no missing approved core role")
    acceptable_ids = tuple(
        sorted(card_id for card_class in classes for card_id in card_class)
    )
    current_availability = prove_deck_availability_from_state(
        state,
        acceptable_ids,
        required_count=1,
    )
    if (
        not isinstance(availability_proof, DeckAvailabilityProof)
        or availability_proof != current_availability
        or not availability_proof.is_guaranteed
        or availability_proof.rejection_reasons
    ):
        raise ValueError("Poke Pad acceptable union is not guaranteed in deck")
    if len(action_spec.choices) != 1:
        raise ValueError("Poke Pad search requires one initiation action")
    source_rows = _poke_pad_source_rows(state, legal_options)
    if not source_rows or action_spec.choices[0] != source_rows[0][0]:
        raise ValueError("Poke Pad source is not the lowest legal physical serial")
    try:
        rebound = action_spec.bind(
            legal_options,
            min_count=state.min_count,
            max_count=state.max_count,
        )
    except SemanticBindError as error:
        raise ValueError("Poke Pad PLAY must bind uniquely") from error
    if len(rebound) != 1:
        raise ValueError("Poke Pad PLAY must resolve to one option")
    source_ref = source_rows[0][1]
    attack_required_refs = tuple(
        ref_value.sort_key()
        for ref_value in (attack_outcomes.attacker_ref, attack_outcomes.target_ref)
        if ref_value is not None
    )
    return _make_proof(
        kind=CertificateKind.RESOURCE_IMPROVEMENT,
        schema=ProofSchema.POKE_PAD_CORE_FORMATION_V1,
        state=state,
        action_spec=action_spec,
        is_valid=True,
        guaranteed_prizes=0,
        facts={
            "legal_options_fingerprint": legal_options_fingerprint(legal_options),
            "registry_digest": registry.digest,
            "features_digest": features.digest(),
            "attack_state_fingerprint": attack_outcomes.state_fingerprint,
            "attack_options_fingerprint": (
                attack_outcomes.semantic_options_fingerprint
            ),
            "attack_registry_digest": attack_outcomes.registry_digest,
            "attack_build_reasons": attack_outcomes.build_unknown_reasons,
            "attack_rows": attack_facts,
            "attack_required_refs_preserved": attack_required_refs,
            "option_type": int(OptionType.PLAY),
            "source_ref": source_ref,
            "source_card_id": POKE_PAD_CARD_ID,
            "source_effect_id": POKE_PAD_EFFECT_ID,
            "source_effect_profile": effect_profile.canonical(),
            "resource_cost_refs": (source_ref,),
            "consumes_attack_action": False,
            "consumes_manual_attach": False,
            "consumes_supporter": False,
            "manual_attach_used_before": features.manual_attach_used,
            "supporter_used_before": features.supporter_used,
            "eligible_classes": classes,
            "eligible_acceptable_ids": acceptable_ids,
            "availability_proof": availability_proof.canonical(),
            "required_count": 1,
            "safe_bench_slots_before": features.safe_bench_slots,
            "coverage_scope": POKE_PAD_CORE_COVERAGE_SCOPE,
            "full_requirement_covered": False,
            "unresolved_higher_search_priorities": (
                POKE_PAD_CORE_UNRESOLVED_PRIORITIES
            ),
            "acceptable_set_preservation_outside_scope": False,
        },
        rejection_reasons=(),
    )


def attack_outcome_proof(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    registry: PublicEffectRegistry,
    attack_outcomes: BoundAttackOutcomeTable,
    action_spec: ActionSpec,
) -> CertificateProof:
    """Issue one strict current-attack certificate from a fully bound outcome row."""

    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("attack proof requires a checked public effect registry")
    if not isinstance(attack_outcomes, BoundAttackOutcomeTable):
        raise ValueError("attack proof requires a checked attack outcome table")
    if not attack_outcomes.matches(state, legal_options, registry):
        raise ValueError(
            "attack proof table must match the current state, options, and registry"
        )
    if len(action_spec.choices) != 1:
        raise ValueError("attack proof requires exactly one semantic action")
    action_key = action_spec.choices[0]
    if action_key.player_index != state.seat:
        raise ValueError("attack proof action owner must match the acting seat")
    if (
        action_key.option_type != int(OptionType.ATTACK)
        or isinstance(action_key.attack_id, bool)
        or not isinstance(action_key.attack_id, int)
        or action_key.attack_id <= 0
    ):
        raise ValueError("attack proof requires an exact positive ATTACK ID")
    try:
        rebound = action_spec.bind(
            legal_options,
            min_count=state.min_count,
            max_count=state.max_count,
        )
    except SemanticBindError as error:
        raise ValueError(
            "attack proof action must bind uniquely to the current legal options"
        ) from error
    if len(rebound) != 1:
        raise ValueError("attack proof must resolve to exactly one legal option")

    outcome = attack_outcomes.get_for_option(action_key)
    if outcome is None or not outcome.authoritative:
        raise ValueError("attack proof requires one authoritative outcome")
    if outcome.attack_id != action_key.attack_id:
        raise ValueError("attack proof outcome does not match the semantic attack")

    prizes_taken = outcome.prizes_taken
    if prizes_taken is None:
        raise ValueError("attack proof requires an exact Prize result")
    if outcome.exact_game_win:
        kind = CertificateKind.WIN_NOW
    elif not is_fully_exact_attack_completion_outcome(attack_outcomes, outcome):
        raise ValueError(
            "non-winning attack proof requires full exact non-loss admission"
        )
    elif outcome.wins_game is not False:
        raise ValueError("attack proof has an inconsistent terminal result")
    elif outcome.exact_ko and prizes_taken > 0:
        kind = CertificateKind.PRIZE_GAIN_NOW
    else:
        kind = CertificateKind.ATTACK_COMPLETION

    return _make_proof(
        kind=kind,
        schema=ProofSchema.ATTACK_OUTCOME_V1,
        state=state,
        action_spec=action_spec,
        is_valid=True,
        guaranteed_prizes=(
            prizes_taken
            if kind in (CertificateKind.WIN_NOW, CertificateKind.PRIZE_GAIN_NOW)
            else 0
        ),
        facts={
            "legal_options_fingerprint": legal_options_fingerprint(legal_options),
            "registry_digest": attack_outcomes.registry_digest,
            "option_key": outcome.option_key.canonical(),
            "attack_id": outcome.attack_id,
            "attacker_ref": outcome.attacker_ref,
            "target_ref": outcome.target_ref,
            "final_damage": outcome.final_damage,
            "target_starting_hp": outcome.target_starting_hp,
            "damage_margin": outcome.damage_margin,
            "knockout": outcome.knockout,
            "prizes_taken": prizes_taken,
            "wins_game": outcome.wins_game,
            "loses_game": outcome.loses_game,
            "draws_game": outcome.draws_game,
            "future_lock_cost": outcome.future_lock_cost,
            "callback_requires_selection": bool(
                outcome.callback is not None and outcome.callback.requires_selection
            ),
        },
        rejection_reasons=(),
    )


_GUST_STRATEGIC_METRIC_NAMES = (
    "terminal_win",
    "prizes_taken",
    "opponent_prizes_after",
    "negative_attacks_to_next_prize",
    "attached_energy_removed",
    "public_threat_damage_removed",
    "engine_denial",
    "evolution_denial",
    "tool_cards_removed",
    "pre_evolution_cards_removed",
    "negative_target_hp_after",
    "printed_prize_value",
)


def _a4_common_context(
    state,
    legal_options,
    ledger,
    attack_outcomes,
    registry,
    action_spec,
):
    if not is_stable_main_state(state):
        raise ValueError("A4 verifier requires stable MAIN")
    if not isinstance(registry, PublicEffectRegistry):
        raise ValueError("A4 verifier requires the current checked registry")
    if not isinstance(ledger, ResourceLedger):
        raise ValueError("A4 verifier requires a live ResourceLedger")
    expected_ledger = build_resource_ledger(state)
    if (
        ledger.visible_refs != expected_ledger.visible_refs
        or ledger.owner != state.seat
    ):
        raise ValueError("A4 verifier rejects a stale resource ledger")
    if not isinstance(
        attack_outcomes, BoundAttackOutcomeTable
    ) or not attack_outcomes.matches(state, legal_options, registry):
        raise ValueError("A4 verifier requires the current attack table")
    features = build_deck_features(state, legal_options, registry)
    if not isinstance(action_spec, ActionSpec) or len(action_spec.choices) != 1:
        raise ValueError("A4 verifier requires one proposed semantic action")
    try:
        rebound = action_spec.bind(
            legal_options,
            min_count=state.min_count,
            max_count=state.max_count,
        )
    except SemanticBindError as error:
        raise ValueError("A4 verifier action does not bind uniquely") from error
    if len(rebound) != 1:
        raise ValueError("A4 verifier action must bind to one option")
    return features, action_spec.choices[0]


def _a4_source_ref(state, key, card_id):
    matches = tuple(
        ref_value
        for ref_value in state.own.hand_refs
        if ref_value.card_id == card_id
        and ref_value.card_id == key.card_id
        and ref_value.serial == key.card_serial
        and ref_value.owner == state.seat
        and ref_value.zone == int(AreaType.HAND)
        and key.source_zone == int(AreaType.HAND)
    )
    return matches[0] if len(matches) == 1 else None


def _a4_require_free_cost(ledger, *refs):
    if any(ref_value not in ledger.visible_refs for ref_value in refs):
        raise ValueError("A4 verifier ref is not visible in the live ledger")
    check = ledger.check_cost(refs)
    if not check.affordable or check.rejection_reasons:
        raise ValueError("A4 verifier resource cost is reserved or unavailable")


def _a4_board_target(state, key):
    matches = tuple(
        pokemon
        for pokemon in state.own.active + state.own.bench
        if pokemon.ref.zone == key.target_zone
        and pokemon.ref.lineage_serial == key.target_lineage_serial
    )
    return matches[0] if len(matches) == 1 else None


def verify_wally_survival_certificate(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    ledger: ResourceLedger,
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
    action_spec: ActionSpec,
) -> CertificateProof:
    """Independently prove the local Wally survival and attack restoration."""

    features, key = _a4_common_context(
        state, legal_options, ledger, attack_outcomes, registry, action_spec
    )
    if key.option_type != int(OptionType.PLAY) or key.card_id != 1229:
        raise ValueError("Wally verifier requires the exact Wally PLAY action")
    source_ref = _a4_source_ref(state, key, 1229)
    if source_ref is None:
        raise ValueError("Wally verifier cannot bind its physical source")
    _a4_require_free_cost(ledger, source_ref)
    if any(
        option.key.option_type == int(OptionType.PLAY)
        and option.key.card_id in (1213, 1227)
        for option in legal_options
    ):
        raise ValueError("Wally verifier cannot exactly compare Judge or Lillie")
    if (
        state.supporter_played
        or state.energy_attached
        or state.own.poisoned
        or state.own.burned
        or state.own.asleep
        or state.own.paralyzed
        or state.own.confused
        or state.own.deck_count < 1
    ):
        raise ValueError("Wally verifier rejects the current turn conditions")
    target = state.own_active
    if (
        target is None
        or target.ref.card_id != 678
        or target.damage <= 0
        or not target.energy_refs
    ):
        raise ValueError("Wally verifier requires a damaged energized Active Mega")
    exact_surface = bool(attack_outcomes.rows) and all(
        outcome.authoritative
        and outcome.legality_exact
        and outcome.legal is True
        and outcome.payable is True
        and outcome.terminal_exact
        and isinstance(outcome.wins_game, bool)
        for outcome in attack_outcomes.rows
    )
    if not exact_surface or any(
        outcome.wins_game is True for outcome in attack_outcomes.rows
    ):
        raise ValueError("Wally verifier requires exact attacks and no direct win")
    threat = build_public_opponent_attack_threat(state, registry)
    if (
        not threat.exact
        or threat.knockout_before_heal is not True
        or threat.knockout_after_heal is not False
    ):
        raise ValueError("Wally verifier requires an exact public survival flip")
    post_attacks = tuple(
        result
        for result in (
            build_post_wally_productive_attack(
                state, registry, source_ref, reattach_ref
            )
            for reattach_ref in sorted(
                target.energy_refs, key=lambda value: value.sort_key()
            )
        )
        if result is not None
    )
    if not post_attacks:
        raise ValueError("Wally verifier cannot reestablish a productive attack")
    post_attack = post_attacks[0]
    if post_attack.reattach_ref not in ledger.visible_refs or ledger.is_reserved(
        post_attack.reattach_ref
    ):
        raise ValueError("Wally verifier reattach ref is unavailable")
    return _make_proof(
        kind=CertificateKind.RESOURCE_IMPROVEMENT,
        schema=ProofSchema.WALLY_SURVIVAL_V1,
        state=state,
        action_spec=action_spec,
        is_valid=True,
        guaranteed_prizes=0,
        facts={
            "route_code": "R_WALLY_THREE_PRIZE_REBOOT_V1",
            "route_priority": 0,
            "legal_options_fingerprint": legal_options_fingerprint(legal_options),
            "registry_digest": registry.digest,
            "features_digest": features.digest(),
            "source_ref": source_ref,
            "target_ref": target.ref,
            "reattach_ref": post_attack.reattach_ref,
            "damage_healed": target.damage,
            "before_hp": target.remaining_hp,
            "after_hp": target.max_hp,
            "max_opponent_attack_ids": threat.max_attack_ids,
            "max_opponent_damage": threat.max_damage,
            "knockout_before_heal": True,
            "knockout_after_heal": False,
            "reestablished_attack_id": post_attack.attack_id,
            "reestablished_attack_damage": post_attack.final_damage,
            "deck_buffer": state.own.deck_count,
            "current_direct_win": False,
            "certificate_status": "VERIFIED_GATE_A4",
        },
        rejection_reasons=(),
    )


def _a4_productive_attack(target, attack_outcomes):
    rows = []
    for row in attack_outcomes.rows:
        if (
            row.attacker_ref != target.ref
            or not row.authoritative
            or not row.legality_exact
            or row.legal is not True
            or row.payable is not True
            or not row.exact_damage
            or row.final_damage is None
            or row.final_damage <= 0
            or row.knockout is not False
            or row.attacker_damage != 0
            or not row.post_attack_exact
            or row.attacker_hp_after is None
            or row.attacker_hp_after <= 0
            or not row.terminal_exact
            or row.loses_game is not False
            or row.draws_game is not False
        ):
            continue
        rows.append((-row.final_damage, row.attack_id, row.option_key.sort_key(), row))
    return None if not rows else min(rows)[-1]


def _a4_cape_candidates(state, legal_options, ledger, attack_outcomes, registry):
    candidates = []
    for option in legal_options:
        key = option.key
        if key.option_type != int(OptionType.ATTACH) or key.card_id != 1159:
            continue
        source_ref = _a4_source_ref(state, key, 1159)
        target = _a4_board_target(state, key)
        if source_ref is None or target is None or target.tool_refs:
            continue
        try:
            _a4_require_free_cost(ledger, source_ref)
        except ValueError:
            continue
        profile = registry.profile(target.ref.card_id)
        if profile is None or any(
            energy_ref.card_id is None
            or not registry.is_effectless_basic_energy(energy_ref.card_id)
            for energy_ref in target.energy_refs
        ):
            continue
        prize_value = profile.prize_value
        if (
            target.ref.zone == int(AreaType.BENCH)
            and target.ref.card_id == 677
            and target.damage > 0
        ):
            branch, route_priority = "BENCH_SPREAD", 1
        elif target.ref.zone == int(AreaType.ACTIVE):
            if profile.mega_ex and prize_value == 3:
                branch, route_priority = "ACTIVE_RESPONSE", 0
            elif target.ref.card_id == 674:
                branch, route_priority = "ACTIVE_RESPONSE", 2
            elif prize_value == 1:
                branch, route_priority = "ACTIVE_RESPONSE", 3
            else:
                continue
        else:
            continue
        before_hp = (target.remaining_hp, target.max_hp)
        after_hp = (target.remaining_hp + 100, target.max_hp + 100)
        threat = build_public_opponent_attack_threat(
            state,
            registry,
            target_ref=target.ref,
            before_hp_state=before_hp,
            after_hp_state=after_hp,
            admit_spread_attacks=True,
        )
        if (
            not threat.exact
            or threat.jamming_active is not False
            or threat.knockout_before_heal is not True
            or threat.knockout_after_heal is not False
        ):
            continue
        response_target = state.own_active if branch == "BENCH_SPREAD" else target
        if response_target is None:
            continue
        if branch == "BENCH_SPREAD":
            active_hp = (response_target.remaining_hp, response_target.max_hp)
            active_threat = build_public_opponent_attack_threat(
                state,
                registry,
                target_ref=response_target.ref,
                before_hp_state=active_hp,
                after_hp_state=active_hp,
                admit_spread_attacks=True,
            )
            if (
                not active_threat.exact
                or active_threat.jamming_active is not False
                or active_threat.knockout_before_heal is not False
            ):
                continue
        productive = _a4_productive_attack(response_target, attack_outcomes)
        preserves = productive is not None
        terminal_preservation = state.opponent.prize_count <= prize_value
        if branch == "ACTIVE_RESPONSE" and not preserves and not terminal_preservation:
            continue
        candidates.append(
            (
                route_priority,
                target.ref.sort_key(),
                source_ref.sort_key(),
                option,
                source_ref,
                target,
                {
                    "route_code": "R_CAPE_EXPLICIT_PROTECTION_V1",
                    "route_priority": route_priority,
                    "source_ref": source_ref,
                    "target_ref": target.ref,
                    "branch": branch,
                    "hp_before": before_hp[0],
                    "max_hp_before": before_hp[1],
                    "hp_after": after_hp[0],
                    "max_hp_after": after_hp[1],
                    "opponent_attack_ids": threat.max_attack_ids,
                    "max_target_loss": threat.max_damage,
                    "ko_without": True,
                    "ko_with": False,
                    "target_prize_value": prize_value,
                    "prevented_prizes": prize_value if terminal_preservation else 0,
                    "productive_attack_id": None
                    if productive is None
                    else productive.attack_id,
                    "post_attack_hp": None
                    if productive is None
                    else productive.attacker_hp_after
                    + (100 if branch == "ACTIVE_RESPONSE" else 0),
                    "jamming_active": False,
                    "existing_tool_refs": (),
                    "preserves_productive_attack": preserves,
                    "prevents_terminal_prize_loss": terminal_preservation,
                    "other_tool_opportunity_cost": 0,
                    "certificate_status": "VERIFIED_GATE_A4",
                },
            )
        )
    return tuple(sorted(candidates, key=lambda row: row[:3]))


def verify_cape_survival_certificate(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    ledger: ResourceLedger,
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
    action_spec: ActionSpec,
) -> CertificateProof:
    """Independently prove the globally best exact Hero's Cape survival flip."""

    features, key = _a4_common_context(
        state, legal_options, ledger, attack_outcomes, registry, action_spec
    )
    if key.option_type != int(OptionType.ATTACH) or key.card_id != 1159:
        raise ValueError("Cape verifier requires the exact Cape ATTACH action")
    candidates = _a4_cape_candidates(
        state, legal_options, ledger, attack_outcomes, registry
    )
    if not candidates:
        raise ValueError("Cape verifier found no exact survival candidate")
    chosen = candidates[0]
    if ActionSpec.single(chosen[3].key) != action_spec:
        raise ValueError(
            "Cape verifier action is not the global deterministic candidate"
        )
    facts = dict(chosen[6])
    facts.update(
        {
            "legal_options_fingerprint": legal_options_fingerprint(legal_options),
            "registry_digest": registry.digest,
            "features_digest": features.digest(),
        }
    )
    return _make_proof(
        kind=CertificateKind.RESOURCE_IMPROVEMENT,
        schema=ProofSchema.CAPE_SURVIVAL_V1,
        state=state,
        action_spec=action_spec,
        is_valid=True,
        guaranteed_prizes=0,
        facts=facts,
        rejection_reasons=(),
    )


def _gust_physical_tiebreak(ref):
    return (
        -1 if ref.serial is None else ref.serial,
        -1 if ref.lineage_serial is None else ref.lineage_serial,
        -1 if ref.card_id is None else ref.card_id,
    )


def _gust_metric_row(target, outcome, registry, threat_damage, require_exact_ko):
    profile = (
        None if target.ref.card_id is None else registry.profile(target.ref.card_id)
    )
    if (
        profile is None
        or not outcome.authoritative
        or not outcome.legality_exact
        or outcome.legal is not True
        or outcome.payable is not True
        or not outcome.exact_damage
        or (require_exact_ko and not outcome.exact_ko)
        or not outcome.prize_exact
        or outcome.prizes_taken is None
        or outcome.own_prizes_after is None
        or outcome.opponent_prizes_after is None
        or not outcome.terminal_exact
        or outcome.wins_game is None
        or outcome.loses_game is not False
        or outcome.draws_game is not False
        or outcome.target_hp_after is None
    ):
        return None
    evolution_denial = None
    if not registry.malformed_pokemon_card_ids and not registry.ambiguous_card_ids:
        evolution_denial = sum(
            1
            for candidate in registry.profiles
            if candidate.evolves_from == profile.card_name
        )
    facts = {
        "terminal_win": outcome.wins_game,
        "exact_ko": outcome.exact_ko,
        "prizes_taken": outcome.prizes_taken,
        "own_prizes_after": outcome.own_prizes_after,
        "opponent_prizes_after": outcome.opponent_prizes_after,
        "attacks_to_next_prize": 1 if outcome.exact_ko else None,
        "attached_energy_removed": len(target.energy_refs),
        "tool_cards_removed": len(target.tool_refs),
        "pre_evolution_cards_removed": len(target.pre_evolution_refs),
        "engine_denial": len(profile.registered_skill_effect_ids),
        "evolution_denial": evolution_denial,
        "public_threat_damage_removed": threat_damage,
        "target_hp_after": outcome.target_hp_after,
        "printed_prize_value": profile.prize_value,
        "original_target_ref": target.ref,
    }
    key = (
        int(outcome.wins_game),
        outcome.prizes_taken,
        outcome.opponent_prizes_after,
        -1 if outcome.exact_ko else None,
        len(target.energy_refs),
        threat_damage,
        len(profile.registered_skill_effect_ids),
        evolution_denial,
        len(target.tool_refs),
        len(target.pre_evolution_refs),
        -outcome.target_hp_after,
        profile.prize_value,
    )
    return key, facts


def _compare_gust_keys(left, right, allow_shared_unknown=False):
    if len(left) != len(_GUST_STRATEGIC_METRIC_NAMES) or len(right) != len(
        _GUST_STRATEGIC_METRIC_NAMES
    ):
        return None
    for left_value, right_value in zip(left, right):
        if left_value is None or right_value is None:
            if allow_shared_unknown and left_value is None and right_value is None:
                continue
            return None
        if left_value != right_value:
            return 1 if left_value > right_value else -1
    return 0


def _best_gust_outcome(target, table, registry, threat_damage, require_exact_ko):
    candidates = []
    for outcome in table.rows:
        metric = _gust_metric_row(
            target, outcome, registry, threat_damage, require_exact_ko
        )
        if metric is not None:
            candidates.append((outcome, metric[0], metric[1]))
    if not candidates:
        return None
    chosen = candidates[0]
    for candidate in candidates[1:]:
        comparison = _compare_gust_keys(candidate[1], chosen[1], True)
        if comparison is None:
            return None
        if comparison > 0 or (
            comparison == 0 and candidate[0].attack_id < chosen[0].attack_id
        ):
            chosen = candidate
    return chosen


def _derive_gust_choice(state, legal_options, attack_outcomes, registry):
    if any(outcome.exact_game_win for outcome in attack_outcomes.rows):
        return None
    attack_ids = tuple(
        sorted(
            {
                outcome.attack_id
                for outcome in attack_outcomes.rows
                if outcome.authoritative
                and outcome.legality_exact
                and outcome.legal is True
                and outcome.payable is True
            }
        )
    )
    current_target = state.opponent_active
    if not attack_ids or current_target is None:
        return None
    current_threat = build_public_opponent_attack_threat(state, registry)
    current = _best_gust_outcome(
        current_target,
        attack_outcomes,
        registry,
        current_threat.max_damage if current_threat.exact else None,
        False,
    )
    if current is None:
        return None
    bench = []
    for original_target in state.opponent.bench:
        surface = build_gust_attack_outcome_table(
            state, legal_options, registry, original_target.ref, attack_ids
        )
        if surface is None:
            continue
        hypothetical_state, table = surface
        threat = build_public_opponent_attack_threat(hypothetical_state, registry)
        candidate = _best_gust_outcome(
            hypothetical_state.opponent_active,
            table,
            registry,
            threat.max_damage if threat.exact else None,
            True,
        )
        if candidate is not None:
            bench.append(
                (
                    original_target,
                    candidate[0],
                    candidate[1],
                    {**candidate[2], "original_target_ref": original_target.ref},
                )
            )
    maximal = []
    for candidate in bench:
        comparisons = tuple(
            _compare_gust_keys(candidate[2], other[2])
            for other in bench
            if other is not candidate
        )
        if all(value is not None and value >= 0 for value in comparisons):
            maximal.append(candidate)
    if not maximal or any(
        _compare_gust_keys(left[2], right[2]) != 0
        for left in maximal
        for right in maximal
    ):
        return None
    chosen = min(maximal, key=lambda row: _gust_physical_tiebreak(row[0].ref))
    dominance = _compare_gust_keys(chosen[2], current[1])
    if dominance is None or dominance <= 0:
        return None
    dominance_field = next(
        (
            name
            for name, left, right in zip(
                _GUST_STRATEGIC_METRIC_NAMES, chosen[2], current[1]
            )
            if left is not None and right is not None and left != right
        ),
        None,
    )
    if dominance_field is None:
        return None
    return chosen, current, attack_ids, dominance_field


def _same_gust_outcome(before, after):
    return (
        after is not None
        and after.authoritative
        and after.legality_exact
        and after.legal is True
        and after.payable is True
        and after.exact_damage
        and after.final_damage == before.final_damage
        and after.knockout == before.knockout
        and after.prize_exact
        and after.prizes_taken == before.prizes_taken
        and after.own_prizes_after == before.own_prizes_after
        and after.opponent_prizes_after == before.opponent_prizes_after
        and after.terminal_exact
        and after.wins_game == before.wins_game
        and after.loses_game == before.loses_game
        and after.draws_game == before.draws_game
    )


def verify_gust_dominance_certificate(
    state: PublicState,
    legal_options: Sequence[SemanticOption],
    ledger: ResourceLedger,
    attack_outcomes: BoundAttackOutcomeTable,
    registry: PublicEffectRegistry,
    action_spec: ActionSpec,
) -> CertificateProof:
    """Independently prove the full exact current-Active/Bench gust matrix."""

    features, key = _a4_common_context(
        state, legal_options, ledger, attack_outcomes, registry, action_spec
    )
    derived = _derive_gust_choice(state, legal_options, attack_outcomes, registry)
    if derived is None:
        raise ValueError("Gust verifier found no exact dominant Bench target")
    chosen, current, attack_ids, dominance_field = derived
    target, planned, strategic_key, metric_facts = chosen
    evolution_target_ref = None
    if key.option_type == int(OptionType.PLAY) and key.card_id == 1182:
        if state.supporter_played:
            raise ValueError("Boss verifier rejects an already used supporter")
        source_ref = _a4_source_ref(state, key, 1182)
        route_code = "R_GUST_BOSS_EXACT_DOMINANCE_A3"
        route_priority = 1
        supporter_cost = 1
    elif key.option_type == int(OptionType.EVOLVE) and key.card_id == 674:
        source_ref = _a4_source_ref(state, key, 674)
        own_target = _a4_board_target(state, key)
        if (
            own_target is None
            or own_target.ref.card_id != 673
            or own_target.ref.zone != int(AreaType.BENCH)
        ):
            raise ValueError("Heave verifier requires an exact Bench Makuhita")
        evolution_target_ref = own_target.ref
        post_surface = build_gust_attack_outcome_table(
            state,
            legal_options,
            registry,
            target.ref,
            attack_ids,
            evolution_source_ref=source_ref,
            evolution_target_ref=evolution_target_ref,
        )
        post = None if post_surface is None else post_surface[1].get(planned.attack_id)
        if not _same_gust_outcome(planned, post):
            raise ValueError("Heave verifier cannot preserve the planned exact attack")
        route_code = "R_GUST_HARIYAMA_EXACT_DOMINANCE_A3"
        route_priority = 0
        supporter_cost = 0
    else:
        raise ValueError("Gust verifier requires exact Boss or Hariyama action")
    if source_ref is None:
        raise ValueError("Gust verifier cannot bind its physical source")
    _a4_require_free_cost(ledger, source_ref)
    facts = {
        "route_code": route_code,
        "route_priority": route_priority,
        "legal_options_fingerprint": legal_options_fingerprint(legal_options),
        "registry_digest": registry.digest,
        "features_digest": features.digest(),
        "source_ref": source_ref,
        "evolution_target_ref": evolution_target_ref,
        "gust_target_ref": target.ref,
        "attack_id": planned.attack_id,
        "damage_floor": planned.final_damage,
        "terminal": planned.wins_game is True,
        "strategic_key": strategic_key,
        "current_active_strategic_key": current[1],
        "dominance_field": dominance_field,
        "current_active_terminal_win": current[2]["terminal_win"],
        "current_active_prizes_taken": current[2]["prizes_taken"],
        "preserves_planned_attack": True,
        "supporter_opportunity_cost": supporter_cost,
        "certificate_status": "VERIFIED_GATE_A4",
        **metric_facts,
    }
    return _make_proof(
        kind=CertificateKind.PRIZE_GAIN_NOW,
        schema=ProofSchema.GUST_DOMINANCE_V1,
        state=state,
        action_spec=action_spec,
        is_valid=True,
        guaranteed_prizes=planned.prizes_taken,
        facts=facts,
        rejection_reasons=(),
    )


def _gust_matrix_exactly_resolved(
    state,
    legal_options,
    attack_outcomes,
    registry,
):
    attack_ids = tuple(
        sorted(
            {
                outcome.attack_id
                for outcome in attack_outcomes.rows
                if outcome.authoritative
                and outcome.legality_exact
                and outcome.legal is True
                and outcome.payable is True
            }
        )
    )
    if not attack_ids or not build_public_opponent_attack_threat(state, registry).exact:
        return False

    def exact_rows(table):
        for attack_id in attack_ids:
            row = table.get(attack_id)
            if (
                row is None
                or not row.authoritative
                or not row.legality_exact
                or row.legal is not True
                or row.payable is not True
                or not row.exact_damage
                or not row.prize_exact
                or row.prizes_taken is None
                or row.own_prizes_after is None
                or row.opponent_prizes_after is None
                or not row.terminal_exact
                or row.wins_game is None
                or row.loses_game is not False
                or row.draws_game is not False
                or row.target_hp_after is None
            ):
                return False
        return True

    if not exact_rows(attack_outcomes):
        return False
    for target in state.opponent.bench:
        surface = build_gust_attack_outcome_table(
            state,
            legal_options,
            registry,
            target.ref,
            attack_ids,
        )
        if surface is None:
            return False
        hypothetical_state, table = surface
        if not build_public_opponent_attack_threat(
            hypothetical_state, registry
        ).exact or not exact_rows(table):
            return False
    return True


def wally_higher_priority_supporter_status(
    state,
    legal_options,
    ledger,
    attack_outcomes,
    registry,
):
    boss_specs = tuple(
        ActionSpec.single(option.key)
        for option in legal_options
        if option.key.option_type == int(OptionType.PLAY) and option.key.card_id == 1182
    )
    if not boss_specs:
        return "ABSENT_EXACT"
    saw_unknown = False
    for action_spec in boss_specs:
        try:
            proof = verify_gust_dominance_certificate(
                state,
                legal_options,
                ledger,
                attack_outcomes,
                registry,
                action_spec,
            )
        except ValueError:
            if _gust_matrix_exactly_resolved(
                state, legal_options, attack_outcomes, registry
            ):
                continue
            saw_unknown = True
            continue
        if proof.fact("terminal") is True:
            return "VALID_EXACT"
    return "UNKNOWN" if saw_unknown else "ABSENT_EXACT"


__all__ = [
    "CertificateKind",
    "CertificateProof",
    "FIRST_TURN_RIOLU_ATTACH_COVERAGE",
    "FIRST_TURN_RIOLU_ATTACH_SCOPE",
    "FIRST_TURN_RIOLU_ATTACH_UNRESOLVED",
    "POKE_PAD_CARD_ID",
    "ACTIVE_ATTACK_COMPLETION_COVERAGE",
    "ACTIVE_ATTACK_COMPLETION_RULE_ID",
    "ACTIVE_ATTACK_COMPLETION_UNRESOLVED",
    "POKE_PAD_CORE_COVERAGE_SCOPE",
    "POKE_PAD_CORE_UNRESOLVED_PRIORITIES",
    "POKE_PAD_EFFECT_ID",
    "ProofSchema",
    "active_post_attach_attack_completion_proof",
    "poke_pad_core_eligible_classes",
    "poke_pad_core_formation_proof",
    "attack_outcome_proof",
    "basic_bench_proof",
    "deck_rule_proof",
    "first_turn_riolu_attach_proof",
    "legal_options_fingerprint",
    "safe_fallback_proof",
    "verify_wally_survival_certificate",
    "verify_cape_survival_certificate",
    "verify_gust_dominance_certificate",
    "wally_higher_priority_supporter_status",
]
