"""Full-support latest-action reference prior and residual policy transform."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import random
from typing import Any, Mapping, Sequence


REFERENCE_PRIOR_SCHEMA_VERSION = "archaludon-reference-prior-v1"
BEHAVIOR_POLICY_SCHEMA_VERSION = "temperature-sharpened-full-support-v1"
BEHAVIOR_FORMULA_ID = (
    "mu_i=0.98*softmax((log(w_i)+2*tanh(clamp(r_i,-3,3)))/0.65)_i+0.02/K;"
    "w_teacher=exp(3);w_other=1"
)
BEHAVIOR_TEMPERATURE = 0.65
BEHAVIOR_SUPPORT_MIXTURE = 0.02
BEHAVIOR_ANCHOR_KL_ID = "zero-residual-mu-anchor-v1"
BEHAVIOR_ANCHOR_KL_DIRECTION = "KL(mu_current||mu_zero)"
BEHAVIOR_ANCHOR_REFERENCE_FORMULA_ID = (
    "mu_zero=same_behavior_formula_with_all_residuals_zero"
)
BEHAVIOR_ANCHOR_SURFACE_IDENTITY = (
    "same_teacher_index+legal_option_count+ordered_semantic_action_sha256"
)


@dataclass(frozen=True)
class ReferencePolicyConfig:
    teacher_margin: float = 3.0
    residual_cap: float = 3.0
    residual_scale: float = 2.0
    exploration_epsilon: float = 0.02

    def validate(self) -> None:
        values = (
            self.teacher_margin,
            self.residual_cap,
            self.residual_scale,
            self.exploration_epsilon,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in values
        ):
            raise ValueError("reference-policy configuration must be finite numeric")
        if self.teacher_margin <= 0:
            raise ValueError("teacher_margin must be positive")
        if self.residual_cap <= 0 or self.residual_scale <= 0:
            raise ValueError("residual cap/scale must be positive")
        if not 0 < self.exploration_epsilon < 1:
            raise ValueError("exploration_epsilon must be in (0, 1)")


CANONICAL_REFERENCE_POLICY_CONFIG = ReferencePolicyConfig()
_REFERENCE_PRIOR_RECEIPT_FIELDS = {
    "schema_version",
    "teacher_margin",
    "residual_cap",
    "residual_scale",
    "exploration_epsilon",
}
_BEHAVIOR_POLICY_RECEIPT_FIELDS = {
    "schema_version",
    "formula_id",
    "teacher_log_weight",
    "other_log_weight",
    "residual_cap",
    "residual_scale",
    "temperature",
    "support_mixture",
    "anchor_kl_id",
    "anchor_kl_direction",
    "anchor_reference_formula_id",
    "anchor_surface_identity",
}


def canonical_reference_prior_receipt() -> dict[str, Any]:
    """Return the one canonical, JSON-safe reference-prior configuration."""

    config = CANONICAL_REFERENCE_POLICY_CONFIG
    config.validate()
    return {
        "schema_version": REFERENCE_PRIOR_SCHEMA_VERSION,
        "teacher_margin": float(config.teacher_margin),
        "residual_cap": float(config.residual_cap),
        "residual_scale": float(config.residual_scale),
        "exploration_epsilon": float(config.exploration_epsilon),
    }


def reference_prior_sha256(receipt: Mapping[str, Any] | None = None) -> str:
    """Hash a reference-prior receipt using the repository JSON convention."""

    payload = (
        canonical_reference_prior_receipt()
        if receipt is None
        else dict(receipt)
    )
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def canonical_behavior_policy_receipt() -> dict[str, Any]:
    """Return the exact iteration-004 behavior transform identity."""

    config = CANONICAL_REFERENCE_POLICY_CONFIG
    config.validate()
    if float(config.exploration_epsilon) != BEHAVIOR_SUPPORT_MIXTURE:
        raise AssertionError("canonical support mixture/configuration mismatch")
    return {
        "schema_version": BEHAVIOR_POLICY_SCHEMA_VERSION,
        "formula_id": BEHAVIOR_FORMULA_ID,
        "teacher_log_weight": float(config.teacher_margin),
        "other_log_weight": 0.0,
        "residual_cap": float(config.residual_cap),
        "residual_scale": float(config.residual_scale),
        "temperature": BEHAVIOR_TEMPERATURE,
        "support_mixture": BEHAVIOR_SUPPORT_MIXTURE,
        "anchor_kl_id": BEHAVIOR_ANCHOR_KL_ID,
        "anchor_kl_direction": BEHAVIOR_ANCHOR_KL_DIRECTION,
        "anchor_reference_formula_id": BEHAVIOR_ANCHOR_REFERENCE_FORMULA_ID,
        "anchor_surface_identity": BEHAVIOR_ANCHOR_SURFACE_IDENTITY,
    }


def behavior_policy_sha256(receipt: Mapping[str, Any] | None = None) -> str:
    payload = (
        canonical_behavior_policy_receipt()
        if receipt is None
        else dict(receipt)
    )
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def behavior_action_order_sha256(
    ordered_actions: Sequence[Mapping[str, Any]],
) -> str:
    """Bind probability indices to the ordered semantic action surface."""

    encoded = json.dumps(
        {"ordered_legal_actions": [dict(row) for row in ordered_actions]},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def validate_behavior_policy_identity(
    receipt: Mapping[str, Any],
    schema_sha256: str,
) -> dict[str, Any]:
    """Reject any noncanonical formula or behavior hyperparameter receipt."""

    canonical = canonical_behavior_policy_receipt()
    if not isinstance(receipt, Mapping) or set(receipt) != _BEHAVIOR_POLICY_RECEIPT_FIELDS:
        raise ValueError("behavior-policy receipt schema mismatch")
    for field in (
        "teacher_log_weight",
        "other_log_weight",
        "residual_cap",
        "residual_scale",
        "temperature",
        "support_mixture",
    ):
        value = receipt.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise ValueError(
                f"behavior-policy numeric field is invalid: {field}"
            )
    for field in (
        "schema_version",
        "formula_id",
        "anchor_kl_id",
        "anchor_kl_direction",
        "anchor_reference_formula_id",
        "anchor_surface_identity",
    ):
        if not isinstance(receipt.get(field), str):
            raise ValueError(
                f"behavior-policy string field is invalid: {field}"
            )
    if dict(receipt) != canonical:
        raise ValueError("behavior-policy canonical formula/configuration mismatch")
    if (
        not isinstance(schema_sha256, str)
        or schema_sha256 != behavior_policy_sha256(canonical)
    ):
        raise ValueError("behavior-policy schema SHA256 mismatch")
    return canonical


def validate_reference_prior_identity(
    receipt: Mapping[str, Any],
    prior_schema_sha256: str,
) -> ReferencePolicyConfig:
    """Validate the canonical receipt/hash pair and return its typed config."""

    if not isinstance(receipt, Mapping) or set(receipt) != _REFERENCE_PRIOR_RECEIPT_FIELDS:
        raise ValueError("reference-prior receipt schema mismatch")
    if receipt.get("schema_version") != REFERENCE_PRIOR_SCHEMA_VERSION:
        raise ValueError("reference-prior schema version mismatch")
    canonical = canonical_reference_prior_receipt()
    for field in _REFERENCE_PRIOR_RECEIPT_FIELDS - {"schema_version"}:
        value = receipt.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) != canonical[field]
        ):
            raise ValueError(
                f"reference-prior canonical configuration mismatch: {field}"
            )
    normalized = {
        "schema_version": receipt["schema_version"],
        **{
            field: float(receipt[field])
            for field in (
                "teacher_margin",
                "residual_cap",
                "residual_scale",
                "exploration_epsilon",
            )
        },
    }
    expected_hash = reference_prior_sha256(normalized)
    if (
        not isinstance(prior_schema_sha256, str)
        or prior_schema_sha256 != expected_hash
    ):
        raise ValueError("reference-prior schema SHA256 mismatch")
    config = ReferencePolicyConfig(
        teacher_margin=normalized["teacher_margin"],
        residual_cap=normalized["residual_cap"],
        residual_scale=normalized["residual_scale"],
        exploration_epsilon=normalized["exploration_epsilon"],
    )
    config.validate()
    return config


@dataclass(frozen=True)
class PolicyDistribution:
    q_latest: tuple[float, ...]
    bounded_residuals: tuple[float, ...]
    probabilities: tuple[float, ...]


@dataclass(frozen=True)
class Selection:
    index: int
    logprob: float
    distribution: PolicyDistribution


class ReferencePolicy:
    def __init__(self, config: ReferencePolicyConfig | None = None) -> None:
        self.config = config or CANONICAL_REFERENCE_POLICY_CONFIG
        self.config.validate()

    def latest_prior(self, option_count: int, teacher_index: int) -> tuple[float, ...]:
        if not isinstance(option_count, int) or isinstance(option_count, bool):
            raise ValueError("option count must be a strict integer")
        if not isinstance(teacher_index, int) or isinstance(teacher_index, bool):
            raise ValueError("teacher index must be a strict integer")
        if option_count < 2:
            raise ValueError("reference prior requires at least two options")
        if not 0 <= teacher_index < option_count:
            raise ValueError("teacher index outside option surface")
        weights = [1.0] * option_count
        weights[teacher_index] = math.exp(self.config.teacher_margin)
        total = sum(weights)
        base = [weight / total for weight in weights]
        epsilon = self.config.exploration_epsilon
        mixed = [
            (1.0 - epsilon) * probability + epsilon / option_count
            for probability in base
        ]
        if any(not probability > 0 for probability in mixed):
            raise AssertionError("latest prior lost full support")
        normalized = tuple(mixed)
        if (
            any(not math.isfinite(probability) for probability in normalized)
            or not math.isclose(
                sum(normalized), 1.0, rel_tol=0.0, abs_tol=1e-12
            )
        ):
            raise AssertionError("latest prior is not finite and normalized")
        return normalized

    def distribution(
        self,
        option_count: int,
        teacher_index: int,
        residuals: Sequence[float],
    ) -> PolicyDistribution:
        if len(residuals) != option_count:
            raise ValueError("one residual is required per legal option")
        q_latest = self.latest_prior(option_count, teacher_index)
        cap = self.config.residual_cap
        bounded = tuple(max(-cap, min(cap, float(value))) for value in residuals)
        if any(not math.isfinite(value) for value in bounded):
            raise ValueError("residuals must be finite")
        log_weights = [0.0] * option_count
        log_weights[teacher_index] = float(self.config.teacher_margin)
        logits = [
            (
                log_weight
                + self.config.residual_scale * math.tanh(residual)
            )
            / BEHAVIOR_TEMPERATURE
            for log_weight, residual in zip(log_weights, bounded)
        ]
        offset = max(logits)
        weights = [math.exp(logit - offset) for logit in logits]
        total = sum(weights)
        base_probabilities = [weight / total for weight in weights]
        support = float(self.config.exploration_epsilon)
        probabilities = tuple(
            (1.0 - support) * probability + support / option_count
            for probability in base_probabilities
        )
        if any(
            not probability > support / option_count
            for probability in probabilities
        ):
            raise AssertionError("residual policy lost full support")
        if (
            any(not math.isfinite(probability) for probability in probabilities)
            or not math.isclose(
                sum(probabilities), 1.0, rel_tol=0.0, abs_tol=1e-12
            )
        ):
            raise AssertionError("residual policy is not finite and normalized")
        return PolicyDistribution(q_latest, bounded, probabilities)

    def deployment_argmax(self, distribution: PolicyDistribution) -> Selection:
        index = max(
            range(len(distribution.probabilities)),
            key=lambda candidate: (distribution.probabilities[candidate], -candidate),
        )
        return Selection(
            index=index,
            logprob=math.log(distribution.probabilities[index]),
            distribution=distribution,
        )

    def training_sample(
        self,
        distribution: PolicyDistribution,
        rng: random.Random | None = None,
    ) -> Selection:
        generator = rng or random.Random()
        threshold = generator.random()
        cumulative = 0.0
        index = len(distribution.probabilities) - 1
        for candidate, probability in enumerate(distribution.probabilities):
            cumulative += probability
            if threshold < cumulative:
                index = candidate
                break
        return Selection(
            index=index,
            logprob=math.log(distribution.probabilities[index]),
            distribution=distribution,
        )

    def inversion_residual(self, q_high: float, q_low: float) -> float:
        """Symmetric +/- residual magnitude required to tie two priors."""

        if not (q_high > q_low > 0):
            return 0.0
        ratio = math.log(q_high / q_low) / (2.0 * self.config.residual_scale)
        if ratio >= 1.0:
            return math.inf
        return math.atanh(ratio)

    def reachability_diagnostics(
        self, option_count: int, teacher_index: int
    ) -> dict[str, object]:
        q_latest = self.latest_prior(option_count, teacher_index)
        log_weights = [0.0] * option_count
        log_weights[teacher_index] = float(self.config.teacher_margin)
        swing = 2.0 * self.config.residual_scale * math.tanh(
            self.config.residual_cap
        )
        reachable: list[bool] = []
        inversion: list[float] = []
        for candidate, log_weight in enumerate(log_weights):
            strongest_other = max(
                log_weights[index]
                for index in range(option_count)
                if index != candidate
            )
            gap = strongest_other - log_weight
            reachable.append(gap < swing - 1e-12)
            inversion.append(
                self.inversion_residual(
                    math.exp(strongest_other), math.exp(log_weight)
                )
                if strongest_other > log_weight
                else 0.0
            )
        return {
            "q_latest": q_latest,
            "residual_logit_swing": swing,
            "behavior_temperature": BEHAVIOR_TEMPERATURE,
            "behavior_support_mixture": float(self.config.exploration_epsilon),
            "argmax_reachable": tuple(reachable),
            "inversion_residual": tuple(inversion),
            "surface_wide_reachable": all(reachable),
        }

    def assert_surface_reachable(self, option_count: int, teacher_index: int) -> None:
        diagnostic = self.reachability_diagnostics(option_count, teacher_index)
        if not diagnostic["surface_wide_reachable"]:
            raise ValueError(
                "configured teacher margin/residual cap makes a legal option "
                "mathematically unable to become argmax"
            )
        zero = self.distribution(option_count, teacher_index, [0.0] * option_count)
        zero_max = max(zero.probabilities)
        if (
            self.deployment_argmax(zero).index != teacher_index
            or sum(
                math.isclose(
                    probability,
                    zero_max,
                    rel_tol=0.0,
                    abs_tol=1e-15,
                )
                for probability in zero.probabilities
            )
            != 1
        ):
            raise ValueError("teacher is not the unique zero-residual argmax")
        cap = float(self.config.residual_cap)
        for candidate in range(option_count):
            residuals = [-cap] * option_count
            residuals[candidate] = cap
            distribution = self.distribution(
                option_count,
                teacher_index,
                residuals,
            )
            largest = max(distribution.probabilities)
            if (
                self.deployment_argmax(distribution).index != candidate
                or sum(
                    math.isclose(
                        probability,
                        largest,
                        rel_tol=0.0,
                        abs_tol=1e-15,
                    )
                    for probability in distribution.probabilities
                )
                != 1
            ):
                raise ValueError(
                    "configured residual bounds do not make every legal option "
                    "a unique argmax"
                )
