"""Closed, state-bound certificates for deterministic rule proposals."""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from enum import Enum, IntEnum
import hashlib
import json
import secrets
from typing import Any, Iterable, Mapping, Sequence, Tuple

try:  # Package import in tests.
    from .attack_outcomes import BoundAttackOutcomeTable
    from .public_effects import PublicEffectRegistry
    from .state_view import (
        ActionSpec,
        OptionType,
        PhysicalRef,
        PublicState,
        SemanticBindError,
        SemanticOption,
        is_stable_main_state,
        public_state_fingerprint,
        semantic_option_multiset,
    )
except ImportError:  # Flat submission import from main.py.
    from attack_outcomes import BoundAttackOutcomeTable
    from public_effects import PublicEffectRegistry
    from state_view import (
        ActionSpec,
        OptionType,
        PhysicalRef,
        PublicState,
        SemanticBindError,
        SemanticOption,
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
    "ProofSchema",
    "attack_outcome_proof",
    "legal_options_fingerprint",
    "safe_fallback_proof",
]
