"""Closed, state-bound certificates for deterministic rule proposals."""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from enum import Enum, IntEnum
import hashlib
import json
import secrets
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

try:  # Package import in tests.
    from .attack_outcomes import BoundAttackOutcomeTable
    from .card_meta import CARD_META_BY_ID
    from .features import (
        DeckFeatures,
        PublicMatchupFlag,
    )
    from .public_effects import PublicEffectRegistry
    from .resource_ledger import (
        DeckAvailabilityProof,
        MANUAL_ATTACH_ENERGY_RESERVATION_ID,
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
    from attack_outcomes import BoundAttackOutcomeTable
    from card_meta import CARD_META_BY_ID
    from features import DeckFeatures, PublicMatchupFlag
    from public_effects import PublicEffectRegistry
    from resource_ledger import (
        DeckAvailabilityProof,
        MANUAL_ATTACH_ENERGY_RESERVATION_ID,
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


FIRST_TURN_RIOLU_ATTACH_COVERAGE = (
    "R_ATTACH_001_DEFAULT_CLAUSE_ONLY_V1"
)
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
        (key.canonical(), count)
        for key, count in semantic_option_multiset(options)
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
            raise ValueError("CertificateProof values must be created by a checked issuer")
        if not isinstance(self.action_spec, ActionSpec):
            raise ValueError("certificate action_spec must be an ActionSpec")
        if (
            not isinstance(self.state_fingerprint, str)
            or len(self.state_fingerprint) != 64
            or any(character not in "0123456789abcdef" for character in self.state_fingerprint)
        ):
            raise ValueError("certificate requires a lowercase SHA-256 state fingerprint")
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
        if any(not isinstance(reason, str) or not reason for reason in normalized_reasons):
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
            raise ValueError("Prize-gain certificates must guarantee at least one Prize")
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
        }
        if CertificateKind(self.kind) not in schema_kind_compatibility[ProofSchema(self.schema)]:
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
        sorted(
            (name, _canonical_fact_value(value))
            for name, value in facts.items()
        )
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
    if action_key.option_type == int(OptionType.END) and action_key.attack_id is not None:
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
        state.own.active
        if key.target_zone == int(AreaType.ACTIVE)
        else state.own.bench
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
        zone_priority = (
            0 if target.ref.zone == int(AreaType.ACTIVE) else 1
        )
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
        option.key.option_type == int(OptionType.ATTACK)
        for option in legal_options
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
        raise ValueError(
            "first-turn Riolu attach must bind uniquely"
        ) from error
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
        _BASIC_BENCH_PURPOSE_PRIORITY[purpose]
        for _, _, purpose in candidate_rows
    )
    purpose = _basic_bench_purpose(features, int(key.card_id))
    if (
        purpose is None
        or _BASIC_BENCH_PURPOSE_PRIORITY[purpose] != best_priority
    ):
        raise ValueError("Basic Bench action is below the current role priority")
    if (
        features.safe_bench_slots <= 0
        and not (
            purpose == "BOARD_OUT_BACKUP"
            and features.board_out_risk
        )
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
    elif not outcome.exact:
        raise ValueError(
            "non-winning attack proof requires a fully exact authoritative outcome"
        )
    elif outcome.loses_game is True or outcome.draws_game is True:
        raise ValueError("attack proof cannot promote an exact loss or draw")
    elif not attack_outcomes.exact:
        raise ValueError(
            "non-winning attack proof requires every legal attack outcome to be exact"
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
                outcome.callback is not None
                and outcome.callback.requires_selection
            ),
        },
        rejection_reasons=(),
    )


__all__ = [
    "CertificateKind",
    "CertificateProof",
    "FIRST_TURN_RIOLU_ATTACH_COVERAGE",
    "FIRST_TURN_RIOLU_ATTACH_SCOPE",
    "FIRST_TURN_RIOLU_ATTACH_UNRESOLVED",
    "POKE_PAD_CARD_ID",
    "POKE_PAD_CORE_COVERAGE_SCOPE",
    "POKE_PAD_CORE_UNRESOLVED_PRIORITIES",
    "POKE_PAD_EFFECT_ID",
    "ProofSchema",
    "poke_pad_core_eligible_classes",
    "poke_pad_core_formation_proof",
    "attack_outcome_proof",
    "basic_bench_proof",
    "first_turn_riolu_attach_proof",
    "legal_options_fingerprint",
    "safe_fallback_proof",
]
