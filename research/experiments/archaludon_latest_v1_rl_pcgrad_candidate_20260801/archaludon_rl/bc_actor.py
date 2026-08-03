"""Independent behavior-cloned actor policy without a teacher score margin."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import math
import time
from typing import Any, Mapping, Sequence

import torch

from .decision_contract import (
    DecisionContract,
    GuardCategory,
    GuardResult,
    ProtectedFallback,
)
from .effect_features import EffectCatalog, EffectFeatureSet, extract_effect_features
from .encoders import encode_action, encode_state
from .public_state import enum_int, get_field, project_public_state
from .semantic_action import SemanticOption, semantic_options, validate_engine_action
from .teacher_adapter import LatestV1Teacher, TeacherDecision


BC_POLICY_SCHEMA_VERSION = "behavior-cloned-actor-policy-v1"
BC_POLICY_FORMULA = (
    "masked_softmax(actor_logits);deployment=legal_argmax;"
    "teacher_margin=0;teacher=failure_or_explicit_major_safety_fallback_only"
)
BC_POLICY_SCHEMA_SHA256 = hashlib.sha256(
    json.dumps(
        {
            "schema_version": BC_POLICY_SCHEMA_VERSION,
            "formula": BC_POLICY_FORMULA,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest().upper()
MODEL_TIMEOUT_SECONDS = 0.050


def batched_actor_logits(
    model: Any,
    state_vectors: torch.Tensor,
    action_vectors: torch.Tensor,
) -> torch.Tensor:
    """Run the unchanged actor representation over padded [B,A,*] inputs."""

    if state_vectors.ndim != 2 or action_vectors.ndim != 3:
        raise ValueError("BC actor expects states [B,S] and actions [B,A,D]")
    if state_vectors.shape[0] != action_vectors.shape[0]:
        raise ValueError("BC actor batch size mismatch")
    state_hidden = model.state_encoder(state_vectors)
    action_hidden = model.action_encoder(action_vectors)
    expanded_state = state_hidden.unsqueeze(1).expand(-1, action_hidden.shape[1], -1)
    return model.residual_head(
        torch.cat((expanded_state, action_hidden), dim=-1)
    ).squeeze(-1)


def apply_legal_action_mask(
    logits: torch.Tensor,
    legal_mask: torch.Tensor,
) -> torch.Tensor:
    if logits.shape != legal_mask.shape or legal_mask.dtype != torch.bool:
        raise ValueError("legal-action mask shape/dtype mismatch")
    if logits.ndim == 1:
        if not bool(legal_mask.any()):
            raise ValueError("no legal action is selectable")
    elif logits.ndim == 2:
        if not bool(legal_mask.any(dim=1).all()):
            raise ValueError("a BC batch row has no legal action")
    else:
        raise ValueError("masked logits must be rank one or two")
    if not bool(torch.isfinite(logits).all()):
        raise ValueError("actor logits are non-finite")
    return logits.masked_fill(~legal_mask, -torch.inf)


def masked_argmax(logits: Sequence[float], legal_mask: Sequence[bool]) -> int:
    if len(logits) != len(legal_mask) or not logits:
        raise ValueError("actor logits/legal mask length mismatch")
    candidates = [
        index
        for index, allowed in enumerate(legal_mask)
        if bool(allowed)
    ]
    if not candidates:
        raise ValueError("no legal action is selectable")
    values = [float(value) for value in logits]
    if any(not math.isfinite(value) for value in values):
        raise ValueError("actor logits are non-finite")
    return max(candidates, key=lambda index: (values[index], -index))


def masked_probabilities(
    logits: Sequence[float], legal_mask: Sequence[bool]
) -> tuple[float, ...]:
    selected = [
        float(value) if bool(allowed) else -math.inf
        for value, allowed in zip(logits, legal_mask)
    ]
    finite = [value for value in selected if math.isfinite(value)]
    if not finite:
        raise ValueError("no finite legal actor logit")
    offset = max(finite)
    weights = [
        math.exp(value - offset) if math.isfinite(value) else 0.0
        for value in selected
    ]
    total = sum(weights)
    if not total > 0.0 or not math.isfinite(total):
        raise ValueError("actor softmax is invalid")
    return tuple(weight / total for weight in weights)


@dataclass(frozen=True)
class BCPolicyDecision:
    action: tuple[int, ...]
    teacher_action: tuple[int, ...]
    neural_shadow_action: tuple[int, ...] | None
    fallback_used: bool
    fallback_reason: str | None
    guard: GuardResult
    logits: tuple[float, ...]
    probabilities: tuple[float, ...]
    checkpoint_sha256: str | None
    teacher_call_count: int
    actor_used: bool
    model_failure_kind: str | None = None
    model_timeout: bool = False
    collection_mode: str = "deployment"
    sampled_stochastically: bool = False
    ppo_eligible: bool = False
    behavior_schema_sha256: str = BC_POLICY_SCHEMA_SHA256
    schema_version: str = BC_POLICY_SCHEMA_VERSION

    @property
    def residuals(self) -> tuple[float, ...]:
        """Compatibility alias used by the bounded deployment telemetry."""

        return self.logits

    @property
    def legal_option_count(self) -> int:
        return len(self.guard.legal_option_mask)


def _soft_guard(guard: GuardResult, teacher: TeacherDecision, reason: str) -> GuardResult:
    return replace(
        guard,
        protected_fallback=ProtectedFallback(
            action=teacher.action,
            hard=False,
            reason=reason,
        ),
    )


def _hard_guard(guard: GuardResult, teacher: TeacherDecision, reason: str) -> GuardResult:
    categories = tuple(
        dict.fromkeys((*guard.categories, GuardCategory.EXECUTION_INVARIANT))
    )
    counts = dict(guard.counts)
    counts[GuardCategory.EXECUTION_INVARIANT.value] = (
        counts.get(GuardCategory.EXECUTION_INVARIANT.value, 0) + 1
    )
    return replace(
        guard,
        actor_learnable=False,
        ppo_eligible=False,
        actor_option_mask=tuple(False for _ in guard.legal_option_mask),
        counts=counts,
        reasons=(*guard.reasons, reason),
        categories=categories,
        protected_fallback=ProtectedFallback(
            action=teacher.action,
            hard=True,
            reason=reason,
        ),
    )


def _protocol_guard(teacher: TeacherDecision, option_count: int) -> GuardResult:
    legal = tuple(True for _ in range(option_count))
    return GuardResult(
        actor_learnable=False,
        ppo_eligible=False,
        legal_option_mask=legal,
        actor_option_mask=tuple(False for _ in legal),
        counts={},
        reasons=("deterministic_protocol_surface",),
        categories=(GuardCategory.SURFACE_EXCLUDED,),
        protected_fallback=ProtectedFallback(
            action=teacher.action,
            hard=False,
            reason="deterministic_protocol_surface",
        ),
    )


class BehaviorCloningPolicy:
    """Teacher-labeled actor logits with teacher used only as a fail-closed path."""

    def __init__(
        self,
        teacher: LatestV1Teacher,
        *,
        model: Any,
        checkpoint_sha256: str,
        catalog: EffectCatalog | None = None,
        decision_contract: DecisionContract | None = None,
        model_timeout_seconds: float = MODEL_TIMEOUT_SECONDS,
    ) -> None:
        if model is None:
            raise ValueError("BC deployment requires a trained actor checkpoint")
        if model_timeout_seconds <= 0.0:
            raise ValueError("model timeout must be positive")
        self.teacher = teacher
        self.model = model
        self.checkpoint_sha256 = checkpoint_sha256
        self.catalog = catalog or EffectCatalog()
        self.decision_contract = decision_contract or DecisionContract()
        self.model_timeout_seconds = float(model_timeout_seconds)

    def _decision(
        self,
        teacher: TeacherDecision,
        guard: GuardResult,
        *,
        action: tuple[int, ...],
        logits: Sequence[float] = (),
        probabilities: Sequence[float] = (),
        actor_used: bool,
        fallback_used: bool = False,
        fallback_reason: str | None = None,
        model_failure_kind: str | None = None,
        model_timeout: bool = False,
    ) -> BCPolicyDecision:
        neural = action if actor_used else None
        return BCPolicyDecision(
            action=action,
            teacher_action=teacher.action,
            neural_shadow_action=neural,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            guard=guard,
            logits=tuple(float(value) for value in logits),
            probabilities=tuple(float(value) for value in probabilities),
            checkpoint_sha256=self.checkpoint_sha256,
            teacher_call_count=teacher.call_count,
            actor_used=actor_used,
            model_failure_kind=model_failure_kind,
            model_timeout=model_timeout,
        )

    def _fallback(
        self,
        teacher: TeacherDecision,
        guard: GuardResult,
        reason: str,
        *,
        logits: Sequence[float] = (),
        probabilities: Sequence[float] = (),
        model_failure_kind: str | None = None,
        model_timeout: bool = False,
    ) -> BCPolicyDecision:
        hardened = _hard_guard(guard, teacher, reason)
        return self._decision(
            teacher,
            hardened,
            action=teacher.action,
            logits=logits,
            probabilities=probabilities,
            actor_used=False,
            fallback_used=True,
            fallback_reason=reason,
            model_failure_kind=model_failure_kind,
            model_timeout=model_timeout,
        )

    def decide(self, observation: Any) -> BCPolicyDecision:
        teacher = self.teacher.decide(observation)
        select = get_field(observation, "select")
        if select is None:
            guard = _protocol_guard(teacher, 0)
            validate_engine_action(observation, teacher.action_list())
            return self._decision(
                teacher,
                guard,
                action=teacher.action,
                actor_used=False,
            )

        raw_options = list(get_field(select, "option", ()) or ())
        option_count = len(raw_options)
        if option_count <= 1:
            guard = _protocol_guard(teacher, option_count)
            validate_engine_action(observation, teacher.action_list())
            return self._decision(
                teacher,
                guard,
                action=teacher.action,
                actor_used=False,
            )

        projection: Mapping[str, Any] | None = None
        options: tuple[SemanticOption, ...] = ()
        effects: tuple[EffectFeatureSet, ...] = ()
        state_vector: tuple[float, ...] | None = None
        action_vectors: tuple[tuple[float, ...], ...] = ()
        try:
            options = semantic_options(observation)
            projection = project_public_state(observation)
            effects = tuple(
                extract_effect_features(projection, option, self.catalog)
                for option in options
            )
            unknown = sorted(
                {
                    f"{index}:{field}"
                    for index, feature_set in enumerate(effects)
                    for field in feature_set.unknown_fields
                }
            )
            guard = self.decision_contract.evaluate(
                observation,
                teacher,
                unknown_effect_fields=unknown,
            )
            state_vector = tuple(encode_state(projection))
            action_vectors = tuple(
                tuple(encode_action(option, feature_set))
                for option, feature_set in zip(options, effects)
            )
        except Exception as exc:
            guard = self.decision_contract.evaluate(observation, teacher)
            return self._fallback(
                teacher,
                guard,
                f"schema_or_encoding_failure:{type(exc).__name__}:{exc}",
                model_failure_kind=type(exc).__name__,
            )

        critical = {
            GuardCategory.ENGINE_ILLEGAL,
            GuardCategory.EXECUTION_INVARIANT,
        }
        if any(category in critical for category in guard.categories):
            return self._fallback(
                teacher,
                guard,
                "explicit_major_safety:" + ";".join(guard.reasons),
            )

        minimum = enum_int(get_field(select, "minCount"))
        maximum = enum_int(get_field(select, "maxCount"))
        if (
            minimum != 1
            or maximum != 1
            or len(teacher.action) != 1
        ):
            return self._fallback(
                teacher,
                guard,
                f"explicit_major_safety:unsupported_cardinality:{minimum}:{maximum}:{len(teacher.action)}",
            )

        legal_mask = tuple(bool(value) for value in guard.legal_option_mask)
        if (
            state_vector is None
            or len(options) != option_count
            or len(action_vectors) != option_count
            or len(legal_mask) != option_count
        ):
            return self._fallback(
                teacher,
                guard,
                "unselectable_actor_surface",
            )

        logits: tuple[float, ...] = ()
        probabilities: tuple[float, ...] = ()
        try:
            started = time.monotonic()
            raw_logits, _ = self.model.predict(state_vector, action_vectors)
            elapsed = time.monotonic() - started
            if elapsed > self.model_timeout_seconds:
                raise TimeoutError(
                    f"model inference {elapsed:.6f}s exceeded {self.model_timeout_seconds:.6f}s"
                )
            logits = tuple(float(value) for value in raw_logits)
            selected = masked_argmax(logits, legal_mask)
            probabilities = masked_probabilities(logits, legal_mask)
            action = (selected,)
            validate_engine_action(observation, list(action))
        except Exception as exc:
            return self._fallback(
                teacher,
                guard,
                f"model_or_selection_failure:{type(exc).__name__}:{exc}",
                logits=logits,
                probabilities=probabilities,
                model_failure_kind=type(exc).__name__,
                model_timeout=isinstance(exc, TimeoutError),
            )

        return self._decision(
            teacher,
            _soft_guard(guard, teacher, "actor_logits_selected"),
            action=action,
            logits=logits,
            probabilities=probabilities,
            actor_used=True,
        )
