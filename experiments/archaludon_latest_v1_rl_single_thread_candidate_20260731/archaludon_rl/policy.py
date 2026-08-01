"""One-teacher-call residual-policy orchestration with exact hard fallback."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import math
import random
import time
from typing import Any, Mapping, Sequence

from .decision_contract import (
    DecisionContract,
    GuardCategory,
    GuardResult,
    ProtectedFallback,
)
from .effect_features import EffectCatalog, EffectFeatureSet, extract_effect_features
from .encoders import encode_action, encode_state
from .public_state import project_public_state
from .reference_policy import (
    CANONICAL_REFERENCE_POLICY_CONFIG,
    REFERENCE_PRIOR_SCHEMA_VERSION,
    PolicyDistribution,
    ReferencePolicy,
    canonical_reference_prior_receipt,
    reference_prior_sha256,
)
from .semantic_action import SemanticOption, semantic_options, validate_engine_action
from .teacher_adapter import LatestV1Teacher, TeacherDecision


POLICY_SCHEMA_VERSION = "residual-policy-v3"
MODEL_TIMEOUT_SECONDS = 0.050


@dataclass(frozen=True)
class PolicyConfig:
    mode: str = "deployment"  # deployment | training
    model_timeout_seconds: float = MODEL_TIMEOUT_SECONDS

    def validate(self) -> None:
        if self.mode not in ("deployment", "training"):
            raise ValueError("mode must be deployment or training")
        if self.model_timeout_seconds <= 0:
            raise ValueError("model timeout must be positive")


@dataclass(frozen=True)
class PolicyDecision:
    action: tuple[int, ...]
    teacher_action: tuple[int, ...]
    neural_shadow_action: tuple[int, ...] | None
    ppo_eligible: bool
    fallback_used: bool
    fallback_reason: str | None
    guard: GuardResult
    projection: Mapping[str, Any] | None
    semantic_options: tuple[SemanticOption, ...]
    effects: tuple[EffectFeatureSet, ...]
    state_vector: tuple[float, ...] | None
    action_vectors: tuple[tuple[float, ...], ...]
    q_latest: tuple[float, ...]
    residuals: tuple[float, ...]
    final_probabilities: tuple[float, ...]
    behavior_logprob: float | None
    value: float | None
    teacher_telemetry: tuple[dict[str, Any], ...]
    teacher_call_count: int
    checkpoint_sha256: str | None
    collection_mode: str
    sampled_stochastically: bool
    prior_schema_version: str
    prior_schema_sha256: str
    legal_option_count: int
    teacher_probability: float | None
    reachability_diagnostics: Mapping[str, Any] = field(default_factory=dict)
    model_failure_kind: str | None = None
    model_timeout: bool = False
    schema_version: str = POLICY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            not isinstance(self.legal_option_count, int)
            or isinstance(self.legal_option_count, bool)
            or self.legal_option_count < 0
        ):
            raise ValueError("legal option count must be a strict nonnegative integer")
        if self.prior_schema_version != REFERENCE_PRIOR_SCHEMA_VERSION:
            raise ValueError("policy decision reference-prior schema mismatch")
        if self.prior_schema_sha256 != reference_prior_sha256():
            raise ValueError("policy decision reference-prior SHA256 mismatch")
        protected = bool(
            self.fallback_used or self.guard.protected_fallback.hard
        )
        if (
            not isinstance(self.model_timeout, bool)
            or (self.model_failure_kind is not None and not self.fallback_used)
            or (self.model_timeout and self.model_failure_kind != "TimeoutError")
            or (self.model_timeout and not self.fallback_used)
        ):
            raise ValueError("structured model-failure status is inconsistent")
        if protected and (
            self.action != self.teacher_action
            or self.ppo_eligible
            or self.sampled_stochastically
            or self.behavior_logprob is not None
        ):
            raise ValueError(
                "protected decisions must be teacher-exact, unsampled, and PPO-ineligible"
            )
        if self.ppo_eligible:
            teacher_index = (
                self.teacher_action[0] if len(self.teacher_action) == 1 else None
            )
            if (
                self.collection_mode != "training"
                or not self.sampled_stochastically
                or self.fallback_used
                or self.legal_option_count < 2
                or len(self.semantic_options) != self.legal_option_count
                or len(self.action_vectors) != self.legal_option_count
                or len(self.q_latest) != self.legal_option_count
                or not isinstance(teacher_index, int)
                or isinstance(teacher_index, bool)
                or not 0 <= teacher_index < self.legal_option_count
                or self.teacher_probability is None
                or not math.isfinite(float(self.teacher_probability))
                or not math.isclose(
                    float(self.teacher_probability),
                    float(self.q_latest[teacher_index]),
                    rel_tol=0.0,
                    abs_tol=1e-12,
                )
            ):
                raise ValueError("eligible policy decision prior contract is incomplete")


def _force_execution_fallback(
    guard: GuardResult, teacher: TeacherDecision, reason: str
) -> GuardResult:
    categories = tuple(
        dict.fromkeys((*guard.categories, GuardCategory.EXECUTION_INVARIANT))
    )
    counts = dict(guard.counts)
    counts[GuardCategory.EXECUTION_INVARIANT.value] = (
        counts.get(GuardCategory.EXECUTION_INVARIANT.value, 0) + 1
    )
    return GuardResult(
        actor_learnable=False,
        ppo_eligible=False,
        legal_option_mask=guard.legal_option_mask,
        actor_option_mask=tuple(False for _ in guard.legal_option_mask),
        counts=counts,
        reasons=(*guard.reasons, reason),
        categories=categories,
        protected_fallback=ProtectedFallback(
            action=teacher.action, hard=True, reason=reason
        ),
    )


class ResidualPolicy:
    def __init__(
        self,
        teacher: LatestV1Teacher,
        *,
        model: Any | None = None,
        checkpoint_sha256: str | None = None,
        catalog: EffectCatalog | None = None,
        reference_policy: ReferencePolicy | None = None,
        decision_contract: DecisionContract | None = None,
        config: PolicyConfig | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.teacher = teacher
        self.model = model
        self.checkpoint_sha256 = checkpoint_sha256
        self.catalog = catalog or EffectCatalog()
        self.reference_policy = reference_policy or ReferencePolicy()
        if self.reference_policy.config != CANONICAL_REFERENCE_POLICY_CONFIG:
            raise ValueError("Phase 0 uses one fixed reference-policy configuration")
        self.prior_receipt = canonical_reference_prior_receipt()
        self.prior_schema_version = str(self.prior_receipt["schema_version"])
        self.prior_schema_sha256 = reference_prior_sha256(self.prior_receipt)
        self.decision_contract = decision_contract or DecisionContract()
        self.config = config or PolicyConfig()
        self.config.validate()
        self.rng = rng or random.Random()

    def decide(self, observation: Any) -> PolicyDecision:
        # There is exactly one teacher call and no adapter-side retry cache.
        teacher = self.teacher.decide(observation)
        if getattr(observation, "select", None) is None and not isinstance(
            observation, dict
        ):
            select = None
        else:
            select = (
                observation.get("select")
                if isinstance(observation, dict)
                else getattr(observation, "select", None)
            )
        raw_options = (
            select.get("option")
            if isinstance(select, Mapping)
            else getattr(select, "option", None)
        )
        legal_option_count = (
            len(raw_options) if isinstance(raw_options, (list, tuple)) else 0
        )
        if select is None:
            empty_guard = GuardResult(
                actor_learnable=False,
                ppo_eligible=False,
                legal_option_mask=(),
                actor_option_mask=(),
                counts={GuardCategory.SURFACE_EXCLUDED.value: 1},
                reasons=("deck_request",),
                categories=(GuardCategory.SURFACE_EXCLUDED,),
                protected_fallback=ProtectedFallback(
                    teacher.action, True, "deck_request"
                ),
            )
            return PolicyDecision(
                action=teacher.action,
                teacher_action=teacher.action,
                neural_shadow_action=None,
                ppo_eligible=False,
                fallback_used=True,
                fallback_reason="deck_request",
                guard=empty_guard,
                projection=None,
                semantic_options=(),
                effects=(),
                state_vector=None,
                action_vectors=(),
                q_latest=(),
                residuals=(),
                final_probabilities=(),
                behavior_logprob=None,
                value=None,
                teacher_telemetry=teacher.telemetry,
                teacher_call_count=teacher.call_count,
                checkpoint_sha256=self.checkpoint_sha256,
                collection_mode=self.config.mode,
                sampled_stochastically=False,
                prior_schema_version=self.prior_schema_version,
                prior_schema_sha256=self.prior_schema_sha256,
                legal_option_count=0,
                teacher_probability=None,
            )

        options: tuple[SemanticOption, ...] = ()
        effects: tuple[EffectFeatureSet, ...] = ()
        projection: Mapping[str, Any] | None = None
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
                observation, teacher, unknown_effect_fields=unknown
            )
            state_vector = tuple(encode_state(projection))
            action_vectors = tuple(
                tuple(encode_action(option, feature_set))
                for option, feature_set in zip(options, effects)
            )
            represented: dict[tuple[float, ...], str] = {}
            for option, vector in zip(options, action_vectors):
                previous_identity = represented.get(vector)
                if (
                    previous_identity is not None
                    and previous_identity != option.identity
                ):
                    raise ValueError(
                        "distinct semantic actions share one action vector"
                    )
                represented[vector] = option.identity
        except Exception as exc:
            guard = self.decision_contract.evaluate(observation, teacher)
            guard = _force_execution_fallback(
                guard, teacher, f"schema_failure:{type(exc).__name__}:{exc}"
            )
            return self._fallback_decision(
                teacher,
                guard,
                projection,
                options,
                effects,
                state_vector,
                action_vectors,
                legal_option_count,
                reason=guard.protected_fallback.reason,
            )

        if self.model is None:
            # A missing checkpoint is exact latest-v1 parity, never an
            # untrained stochastic policy.
            return self._fallback_decision(
                teacher,
                guard,
                projection,
                options,
                effects,
                state_vector,
                action_vectors,
                legal_option_count,
                reason="no_checkpoint_exact_latest",
            )

        # A surface that the Phase-0 actor cannot represent is not a model
        # failure.  Return the teacher before inference.  Free-MAIN callbacks
        # protected only by a latest-v1 owner/rule may still run inference so
        # that their neural shadow action is available for diagnostics.
        noninferable_categories = {
            GuardCategory.ENGINE_ILLEGAL,
            GuardCategory.EXECUTION_INVARIANT,
            GuardCategory.SURFACE_EXCLUDED,
        }
        if (
            not guard.actor_learnable
            and any(
                category in noninferable_categories
                for category in guard.categories
            )
        ):
            return self._fallback_decision(
                teacher,
                guard,
                projection,
                options,
                effects,
                state_vector,
                action_vectors,
                legal_option_count,
                reason=guard.protected_fallback.reason,
            )

        residuals: tuple[float, ...] = ()
        value: float | None = None
        q_latest: tuple[float, ...] = ()
        probabilities: tuple[float, ...] = ()
        neural_shadow: tuple[int, ...] | None = None
        reachability: Mapping[str, Any] = {}
        try:
            started = time.monotonic()
            raw_residuals, raw_value = self.model.predict(
                state_vector, action_vectors
            )
            elapsed = time.monotonic() - started
            if elapsed > self.config.model_timeout_seconds:
                raise TimeoutError(
                    f"model inference {elapsed:.6f}s exceeded "
                    f"{self.config.model_timeout_seconds:.6f}s"
                )
            residuals = tuple(float(value_) for value_ in raw_residuals)
            value = float(raw_value)
            if (
                len(residuals) != len(options)
                or not math.isfinite(value)
                or any(not math.isfinite(item) for item in residuals)
            ):
                raise ValueError("non-finite or wrong-sized model output")
            teacher_index = teacher.action[0] if teacher.action else 0
            reachability = self.reference_policy.reachability_diagnostics(
                len(options), teacher_index
            )
            self.reference_policy.assert_surface_reachable(len(options), teacher_index)
            distribution = self.reference_policy.distribution(
                len(options), teacher_index, residuals
            )
            q_latest = distribution.q_latest
            probabilities = distribution.probabilities
            shadow_selection = self.reference_policy.deployment_argmax(distribution)
            neural_shadow = (shadow_selection.index,)
            validate_engine_action(observation, list(neural_shadow))
        except Exception as exc:
            model_failure_kind = type(exc).__name__
            model_timeout = isinstance(exc, TimeoutError)
            guard = _force_execution_fallback(
                guard,
                teacher,
                f"model_failure:{type(exc).__name__}:{exc}",
            )
            return self._fallback_decision(
                teacher,
                guard,
                projection,
                options,
                effects,
                state_vector,
                action_vectors,
                legal_option_count,
                reason=guard.protected_fallback.reason,
                residuals=residuals,
                q_latest=q_latest,
                probabilities=probabilities,
                value=value,
                neural_shadow=neural_shadow,
                reachability=reachability,
                model_failure_kind=model_failure_kind,
                model_timeout=model_timeout,
            )

        if not guard.actor_learnable:
            return self._fallback_decision(
                teacher,
                guard,
                projection,
                options,
                effects,
                state_vector,
                action_vectors,
                legal_option_count,
                reason=guard.protected_fallback.reason,
                residuals=residuals,
                q_latest=q_latest,
                probabilities=probabilities,
                value=value,
                neural_shadow=neural_shadow,
                reachability=reachability,
            )

        distribution = PolicyDistribution(q_latest, residuals, probabilities)
        selection = (
            self.reference_policy.training_sample(distribution, self.rng)
            if self.config.mode == "training"
            else self.reference_policy.deployment_argmax(distribution)
        )
        selected = (selection.index,)
        try:
            validate_engine_action(observation, list(selected))
        except (TypeError, ValueError) as exc:
            guard = _force_execution_fallback(
                guard, teacher, f"invalid_neural_selection:{exc}"
            )
            return self._fallback_decision(
                teacher,
                guard,
                projection,
                options,
                effects,
                state_vector,
                action_vectors,
                legal_option_count,
                reason=guard.protected_fallback.reason,
                residuals=residuals,
                q_latest=q_latest,
                probabilities=probabilities,
                value=value,
                neural_shadow=neural_shadow,
            )
        return PolicyDecision(
            action=selected,
            teacher_action=teacher.action,
            neural_shadow_action=neural_shadow,
            ppo_eligible=self.config.mode == "training",
            fallback_used=False,
            fallback_reason=None,
            guard=guard,
            projection=projection,
            semantic_options=options,
            effects=effects,
            state_vector=state_vector,
            action_vectors=action_vectors,
            q_latest=q_latest,
            residuals=residuals,
            final_probabilities=probabilities,
            behavior_logprob=(
                selection.logprob if self.config.mode == "training" else None
            ),
            value=value,
            teacher_telemetry=teacher.telemetry,
            teacher_call_count=teacher.call_count,
            checkpoint_sha256=self.checkpoint_sha256,
            collection_mode=self.config.mode,
            sampled_stochastically=self.config.mode == "training",
            prior_schema_version=self.prior_schema_version,
            prior_schema_sha256=self.prior_schema_sha256,
            legal_option_count=legal_option_count,
            teacher_probability=float(q_latest[teacher.action[0]]),
            reachability_diagnostics=reachability,
        )

    def _fallback_decision(
        self,
        teacher: TeacherDecision,
        guard: GuardResult,
        projection: Mapping[str, Any] | None,
        options: tuple[SemanticOption, ...],
        effects: tuple[EffectFeatureSet, ...],
        state_vector: tuple[float, ...] | None,
        action_vectors: tuple[tuple[float, ...], ...],
        legal_option_count: int,
        *,
        reason: str,
        residuals: tuple[float, ...] = (),
        q_latest: tuple[float, ...] = (),
        probabilities: tuple[float, ...] = (),
        value: float | None = None,
        neural_shadow: tuple[int, ...] | None = None,
        reachability: Mapping[str, Any] | None = None,
        model_failure_kind: str | None = None,
        model_timeout: bool = False,
    ) -> PolicyDecision:
        return PolicyDecision(
            action=teacher.action,
            teacher_action=teacher.action,
            neural_shadow_action=neural_shadow,
            ppo_eligible=False,
            fallback_used=True,
            fallback_reason=reason,
            guard=guard,
            projection=projection,
            semantic_options=options,
            effects=effects,
            state_vector=state_vector,
            action_vectors=action_vectors,
            q_latest=q_latest,
            residuals=residuals,
            final_probabilities=probabilities,
            behavior_logprob=None,
            value=value,
            teacher_telemetry=teacher.telemetry,
            teacher_call_count=teacher.call_count,
            checkpoint_sha256=self.checkpoint_sha256,
            collection_mode=self.config.mode,
            sampled_stochastically=False,
            prior_schema_version=self.prior_schema_version,
            prior_schema_sha256=self.prior_schema_sha256,
            legal_option_count=legal_option_count,
            teacher_probability=(
                float(q_latest[teacher.action[0]])
                if (
                    len(teacher.action) == 1
                    and isinstance(teacher.action[0], int)
                    and not isinstance(teacher.action[0], bool)
                    and 0 <= teacher.action[0] < len(q_latest)
                )
                else None
            ),
            reachability_diagnostics=dict(reachability or {}),
            model_failure_kind=model_failure_kind,
            model_timeout=model_timeout,
        )
