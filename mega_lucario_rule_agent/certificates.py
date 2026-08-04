"""Closed, state-bound certificates for deterministic rule proposals."""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from enum import Enum, IntEnum
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence, Tuple

try:  # Package import in tests.
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


_PROOF_ISSUER_TOKEN = object()


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
    return (
        bool(action_spec.order_sensitive),
        tuple(choice.canonical() for choice in action_spec.choices),
    )


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
        if self.is_valid and self.kind in (
            CertificateKind.WIN_NOW,
            CertificateKind.PRIZE_GAIN_NOW,
        ) and self.guaranteed_prizes <= 0:
            raise ValueError("Prize certificates must guarantee at least one Prize")
        schema_kind_compatibility = {
            ProofSchema.SAFE_FALLBACK_V1: {CertificateKind.SAFE_FALLBACK},
        }
        if CertificateKind(self.kind) not in schema_kind_compatibility[ProofSchema(self.schema)]:
            raise ValueError("certificate schema and kind are incompatible")

        object.__setattr__(self, "kind", CertificateKind(self.kind))
        object.__setattr__(self, "schema", ProofSchema(self.schema))
        object.__setattr__(self, "facts", tuple(sorted(normalized_facts)))
        object.__setattr__(self, "rejection_reasons", normalized_reasons)

    def fact(self, name: str, default: Any = None) -> Any:
        return next((value for key, value in self.facts if key == name), default)

    def digest(self) -> str:
        payload = {
            "kind": int(self.kind),
            "schema": self.schema.value,
            "state_fingerprint": self.state_fingerprint,
            "action_spec": _canonical_action_spec(self.action_spec),
            "is_valid": self.is_valid,
            "guaranteed_prizes": self.guaranteed_prizes,
            "facts": self.facts,
            "rejection_reasons": self.rejection_reasons,
        }
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
    return CertificateProof(
        kind=kind,
        schema=schema,
        state_fingerprint=public_state_fingerprint(state),
        action_spec=action_spec,
        is_valid=is_valid,
        guaranteed_prizes=guaranteed_prizes,
        facts=tuple(facts.items()),
        rejection_reasons=tuple(rejection_reasons),
        _issuer_token=_PROOF_ISSUER_TOKEN,
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


__all__ = [
    "CertificateKind",
    "CertificateProof",
    "ProofSchema",
    "legal_options_fingerprint",
    "safe_fallback_proof",
]
