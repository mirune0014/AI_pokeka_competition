"""Deployment policy for the behavior-cloned complete-action actor."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import time
from typing import Any, Mapping, Sequence

import torch

from .bc_actor import _hard_guard, _protocol_guard, _soft_guard
from .catalog import EffectCatalog
from .complete_action import (
    complete_action_logits,
    observation_complete_actions,
    observation_option_rows,
)
from .decision_contract import DecisionContract, GuardCategory, GuardResult
from .effect_features import extract_effect_features
from .encoders import encode_action, encode_state
from .public_state import get_field, project_public_state
from .semantic_action import semantic_options, validate_engine_action
from .teacher_adapter import LatestV1Teacher, TeacherDecision


POLICY_SCHEMA_VERSION = "complete-action-bc-policy-v1"
POLICY_FORMULA = "softmax(complete_action_logits);deployment=argmax;teacher_margin=0"
POLICY_SCHEMA_SHA256 = hashlib.sha256(
    json.dumps(
        {"schema_version": POLICY_SCHEMA_VERSION, "formula": POLICY_FORMULA},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest().upper()


@dataclass(frozen=True)
class CompleteBCDecision:
    action: tuple[int, ...]
    teacher_action: tuple[int, ...]
    neural_shadow_action: tuple[int, ...] | None
    fallback_used: bool
    fallback_reason: str | None
    representability_failure: bool
    guard: GuardResult
    logits: tuple[float, ...]
    probabilities: tuple[float, ...]
    checkpoint_sha256: str
    teacher_call_count: int
    actor_used: bool
    legal_option_count: int
    model_failure_kind: str | None = None
    model_timeout: bool = False
    collection_mode: str = "deployment"
    sampled_stochastically: bool = False
    ppo_eligible: bool = False
    behavior_schema_sha256: str = POLICY_SCHEMA_SHA256
    schema_version: str = POLICY_SCHEMA_VERSION

    @property
    def residuals(self) -> tuple[float, ...]:
        return self.logits


class CompleteActionBehaviorCloningPolicy:
    def __init__(
        self,
        teacher: LatestV1Teacher,
        *,
        model: Any,
        checkpoint_sha256: str,
        catalog: EffectCatalog | None = None,
        decision_contract: DecisionContract | None = None,
        model_timeout_seconds: float = 0.050,
    ) -> None:
        if model is None or model_timeout_seconds <= 0:
            raise ValueError("complete-action BC requires a model and positive timeout")
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
        legal_candidate_count: int,
        logits: Sequence[float] = (),
        probabilities: Sequence[float] = (),
        actor_used: bool,
        fallback_used: bool = False,
        fallback_reason: str | None = None,
        representability_failure: bool = False,
        model_failure_kind: str | None = None,
        model_timeout: bool = False,
    ) -> CompleteBCDecision:
        return CompleteBCDecision(
            action=action,
            teacher_action=teacher.action,
            neural_shadow_action=action if actor_used else None,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            representability_failure=representability_failure,
            guard=guard,
            logits=tuple(float(value) for value in logits),
            probabilities=tuple(float(value) for value in probabilities),
            checkpoint_sha256=self.checkpoint_sha256,
            teacher_call_count=teacher.call_count,
            actor_used=actor_used,
            legal_option_count=legal_candidate_count,
            model_failure_kind=model_failure_kind,
            model_timeout=model_timeout,
        )

    def _fallback(
        self,
        teacher: TeacherDecision,
        guard: GuardResult,
        reason: str,
        *,
        legal_candidate_count: int,
        representability_failure: bool = False,
        logits: Sequence[float] = (),
        probabilities: Sequence[float] = (),
        model_failure_kind: str | None = None,
        model_timeout: bool = False,
    ) -> CompleteBCDecision:
        return self._decision(
            teacher,
            _hard_guard(guard, teacher, reason),
            action=teacher.action,
            legal_candidate_count=legal_candidate_count,
            logits=logits,
            probabilities=probabilities,
            actor_used=False,
            fallback_used=True,
            fallback_reason=reason,
            representability_failure=representability_failure,
            model_failure_kind=model_failure_kind,
            model_timeout=model_timeout,
        )

    def decide(self, observation: Any) -> CompleteBCDecision:
        teacher = self.teacher.decide(observation)
        select = get_field(observation, "select")
        if select is None:
            validate_engine_action(observation, teacher.action_list())
            return self._decision(
                teacher,
                _protocol_guard(teacher, 0),
                action=teacher.action,
                legal_candidate_count=0,
                actor_used=False,
            )
        try:
            semantic = semantic_options(observation)
            option_rows = observation_option_rows(observation)
            projection: Mapping[str, Any] = project_public_state(observation)
            effects = tuple(
                extract_effect_features(projection, option, self.catalog)
                for option in semantic
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
            candidates = observation_complete_actions(observation)
            state_vector = encode_state(projection)
            action_vectors = [
                encode_action(option, feature_set)
                for option, feature_set in zip(semantic, effects)
            ]
        except Exception as exc:
            guard = self.decision_contract.evaluate(observation, teacher)
            return self._fallback(
                teacher,
                guard,
                f"schema_or_encoding_failure:{type(exc).__name__}:{exc}",
                legal_candidate_count=0,
                model_failure_kind=type(exc).__name__,
            )
        critical = {GuardCategory.ENGINE_ILLEGAL, GuardCategory.EXECUTION_INVARIANT}
        if any(category in critical for category in guard.categories):
            return self._fallback(
                teacher,
                guard,
                "explicit_major_safety:" + ";".join(guard.reasons),
                legal_candidate_count=len(candidates.candidates),
            )
        teacher_candidate = candidates.candidate_index_for(option_rows, teacher.action)
        if teacher_candidate is None:
            return self._fallback(
                teacher,
                guard,
                "representability_failure:teacher_action_not_in_complete_candidates",
                legal_candidate_count=len(candidates.candidates),
                representability_failure=True,
            )
        logits: tuple[float, ...] = ()
        probabilities: tuple[float, ...] = ()
        try:
            device = next(self.model.parameters()).device
            state = torch.tensor(state_vector, dtype=torch.float32, device=device)
            options = torch.tensor(action_vectors, dtype=torch.float32, device=device)
            started = time.monotonic()
            with torch.no_grad():
                raw_logits = complete_action_logits(self.model, state, options, candidates)
                raw_probabilities = torch.softmax(raw_logits, dim=0)
            elapsed = time.monotonic() - started
            if elapsed > self.model_timeout_seconds:
                raise TimeoutError(
                    f"model inference {elapsed:.6f}s exceeded {self.model_timeout_seconds:.6f}s"
                )
            logits = tuple(float(value) for value in raw_logits.detach().cpu().tolist())
            probabilities = tuple(
                float(value) for value in raw_probabilities.detach().cpu().tolist()
            )
            if any(not math.isfinite(value) for value in (*logits, *probabilities)):
                raise ValueError("complete-action logits or probabilities are non-finite")
            selected_index = max(range(len(logits)), key=lambda index: (logits[index], -index))
            action = candidates.candidates[selected_index].action
            validate_engine_action(observation, list(action))
        except Exception as exc:
            return self._fallback(
                teacher,
                guard,
                f"model_or_selection_failure:{type(exc).__name__}:{exc}",
                legal_candidate_count=len(candidates.candidates),
                logits=logits,
                probabilities=probabilities,
                model_failure_kind=type(exc).__name__,
                model_timeout=isinstance(exc, TimeoutError),
            )
        return self._decision(
            teacher,
            _soft_guard(guard, teacher, "complete_action_actor_selected"),
            action=action,
            legal_candidate_count=len(candidates.candidates),
            logits=logits,
            probabilities=probabilities,
            actor_used=True,
        )
