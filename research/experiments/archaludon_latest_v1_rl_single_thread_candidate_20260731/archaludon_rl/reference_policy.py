"""Full-support latest-action reference prior and residual policy transform."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import random
from typing import Any, Mapping, Sequence


REFERENCE_PRIOR_SCHEMA_VERSION = "archaludon-reference-prior-v1"


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
        logits = [
            math.log(q) + self.config.residual_scale * math.tanh(residual)
            for q, residual in zip(q_latest, bounded)
        ]
        offset = max(logits)
        weights = [math.exp(logit - offset) for logit in logits]
        total = sum(weights)
        probabilities = tuple(weight / total for weight in weights)
        if any(not probability > 0 for probability in probabilities):
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
        swing = 2.0 * self.config.residual_scale * math.tanh(
            self.config.residual_cap
        )
        reachable: list[bool] = []
        inversion: list[float] = []
        for candidate, probability in enumerate(q_latest):
            strongest_other = max(
                q_latest[index] for index in range(option_count) if index != candidate
            )
            gap = math.log(strongest_other / probability)
            reachable.append(gap < swing - 1e-12)
            inversion.append(
                self.inversion_residual(strongest_other, probability)
                if strongest_other > probability
                else 0.0
            )
        return {
            "q_latest": q_latest,
            "residual_logit_swing": swing,
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
