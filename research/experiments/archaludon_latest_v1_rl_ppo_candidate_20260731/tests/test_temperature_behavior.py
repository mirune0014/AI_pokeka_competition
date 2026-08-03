from __future__ import annotations

import math
from pathlib import Path
import random
import tempfile
import unittest

import torch

from archaludon_rl.frozen_sources import checkpoint_source_hashes
from archaludon_rl.model import (
    ResidualActorCritic,
    checkpoint_metadata,
    load_checkpoint,
    save_checkpoint,
)
from archaludon_rl.policy import PolicyConfig, ResidualPolicy
from archaludon_rl.reference_policy import (
    BEHAVIOR_FORMULA_ID,
    BEHAVIOR_POLICY_SCHEMA_VERSION,
    BEHAVIOR_SUPPORT_MIXTURE,
    BEHAVIOR_TEMPERATURE,
    CANONICAL_REFERENCE_POLICY_CONFIG,
    ReferencePolicy,
    behavior_policy_sha256,
    canonical_behavior_policy_receipt,
    validate_behavior_policy_identity,
)
from archaludon_rl.train_ppo import (
    _torch_behavior_anchor_kl,
    _torch_behavior_distribution,
)
from archaludon_rl.upgrade_iteration004_checkpoint import upgrade_checkpoint

from .helpers import FakeModel, StubTeacher, exact_telemetry, observation


class TemperatureBehaviorTests(unittest.TestCase):
    def test_probability_formula_is_exact_finite_normalized_and_supported(self):
        option_count = 4
        teacher_index = 2
        residuals = [-4.0, -1.0, 0.5, 4.0]
        distribution = ReferencePolicy().distribution(
            option_count,
            teacher_index,
            residuals,
        )
        config = CANONICAL_REFERENCE_POLICY_CONFIG
        bounded = [
            max(-config.residual_cap, min(config.residual_cap, value))
            for value in residuals
        ]
        log_weights = [0.0] * option_count
        log_weights[teacher_index] = 3.0
        logits = [
            (log_weight + 2.0 * math.tanh(residual))
            / BEHAVIOR_TEMPERATURE
            for log_weight, residual in zip(log_weights, bounded)
        ]
        offset = max(logits)
        weights = [math.exp(value - offset) for value in logits]
        total = sum(weights)
        base_probabilities = [weight / total for weight in weights]
        expected = tuple(
            (1.0 - BEHAVIOR_SUPPORT_MIXTURE) * probability
            + BEHAVIOR_SUPPORT_MIXTURE / option_count
            for probability in base_probabilities
        )
        self.assertEqual(distribution.probabilities, expected)
        self.assertTrue(all(math.isfinite(value) for value in expected))
        self.assertAlmostEqual(sum(expected), 1.0, places=15)
        self.assertTrue(
            all(
                value > BEHAVIOR_SUPPORT_MIXTURE / option_count
                for value in expected
            )
        )

    def test_zero_teacher_argmax_and_every_action_extreme_reachability(self):
        policy = ReferencePolicy()
        cap = CANONICAL_REFERENCE_POLICY_CONFIG.residual_cap
        for option_count in (2, 3, 7, 19, 20, 21):
            for teacher_index in range(option_count):
                zero = policy.distribution(
                    option_count, teacher_index, [0.0] * option_count
                )
                maximum = max(zero.probabilities)
                self.assertEqual(policy.deployment_argmax(zero).index, teacher_index)
                self.assertEqual(zero.probabilities.count(maximum), 1)
                for candidate in range(option_count):
                    residuals = [-cap] * option_count
                    residuals[candidate] = cap
                    extreme = policy.distribution(
                        option_count, teacher_index, residuals
                    )
                    self.assertEqual(
                        policy.deployment_argmax(extreme).index,
                        candidate,
                    )
                    self.assertEqual(
                        extreme.probabilities.count(max(extreme.probabilities)),
                        1,
                    )

    def test_seeded_sampling_is_deterministic_and_uses_mu(self):
        policy = ReferencePolicy()
        distribution = policy.distribution(7, 3, [0.5, -0.5, 0.0, 0.0, 1.0, -1.0, 2.0])
        first = random.Random(731004)
        second = random.Random(731004)
        left = [policy.training_sample(distribution, first).index for _ in range(2000)]
        right = [policy.training_sample(distribution, second).index for _ in range(2000)]
        self.assertEqual(left, right)
        self.assertEqual(set(left), set(range(7)))

    def test_python_and_torch_mu_logprob_entropy_and_identity_ratio_match(self):
        policy = ReferencePolicy()
        residual_values = [-4.0, -1.25, 0.0, 0.75, 4.0]
        python_distribution = policy.distribution(5, 2, residual_values)
        torch_probabilities, torch_logprobabilities = (
            _torch_behavior_distribution(
                torch.tensor(residual_values, dtype=torch.float64),
                teacher_index=2,
                reference_config=CANONICAL_REFERENCE_POLICY_CONFIG,
            )
        )
        for index, expected in enumerate(python_distribution.probabilities):
            actual = float(torch_probabilities[index])
            self.assertAlmostEqual(actual, expected, places=15)
            ratio = math.exp(
                float(torch_logprobabilities[index]) - math.log(expected)
            )
            self.assertAlmostEqual(ratio, 1.0, places=14)
        python_entropy = -sum(
            probability * math.log(probability)
            for probability in python_distribution.probabilities
        )
        torch_entropy = float(
            -(torch_probabilities * torch_logprobabilities).sum()
        )
        self.assertAlmostEqual(torch_entropy, python_entropy, places=14)

    def test_zero_residual_anchor_has_zero_kl_and_gradient(self):
        residuals = torch.zeros(7, dtype=torch.float64, requires_grad=True)
        anchor_kl = _torch_behavior_anchor_kl(
            residuals,
            teacher_index=4,
            reference_config=CANONICAL_REFERENCE_POLICY_CONFIG,
        )
        self.assertAlmostEqual(float(anchor_kl.detach()), 0.0, places=15)
        anchor_kl.backward()
        self.assertIsNotNone(residuals.grad)
        self.assertLess(float(residuals.grad.abs().max()), 1e-14)

    def test_nonzero_anchor_kl_matches_independent_python_calculation(self):
        residual_values = [-2.0, 0.25, 1.5, -0.75]
        residuals = torch.tensor(
            residual_values, dtype=torch.float64, requires_grad=True
        )
        measured = _torch_behavior_anchor_kl(
            residuals,
            teacher_index=1,
            reference_config=CANONICAL_REFERENCE_POLICY_CONFIG,
        )
        policy = ReferencePolicy()
        current = policy.distribution(4, 1, residual_values).probabilities
        zero = policy.distribution(4, 1, [0.0] * 4).probabilities
        independent = sum(
            probability * math.log(probability / anchor_probability)
            for probability, anchor_probability in zip(current, zero)
        )
        self.assertGreater(independent, 0.0)
        self.assertAlmostEqual(
            float(measured.detach()), independent, places=14
        )
        measured.backward()
        self.assertGreater(float(residuals.grad.abs().max()), 0.0)

    def test_behavior_receipt_rejects_bool_for_every_numeric_field(self):
        numeric_fields = (
            "teacher_log_weight",
            "other_log_weight",
            "residual_cap",
            "residual_scale",
            "temperature",
            "support_mixture",
        )
        for field in numeric_fields:
            with self.subTest(field=field):
                receipt = canonical_behavior_policy_receipt()
                receipt[field] = bool(receipt[field])
                with self.assertRaisesRegex(ValueError, "numeric field"):
                    validate_behavior_policy_identity(
                        receipt,
                        behavior_policy_sha256(receipt),
                    )

    def test_protected_and_model_fallback_do_not_consume_policy_rng(self):
        protected_rng = random.Random(20260731)
        protected_state = protected_rng.getstate()
        protected_teacher = StubTeacher(
            telemetry=(
                exact_telemetry(
                    active_owner_before="protected-owner",
                    active_owner_after="protected-owner",
                    precedence_reason="rank2_active_transaction_owner",
                    winning_rule_id="protected-owner",
                ),
            )
        )
        ResidualPolicy(
            protected_teacher,
            model=FakeModel([-3.0, 3.0]),
            checkpoint_sha256="B" * 64,
            config=PolicyConfig(mode="training", model_timeout_seconds=1.0),
            rng=protected_rng,
        ).decide(observation())
        self.assertEqual(protected_rng.getstate(), protected_state)

        fallback_rng = random.Random(20260731)
        fallback_state = fallback_rng.getstate()
        ResidualPolicy(
            StubTeacher(),
            model=FakeModel([math.nan, 0.0]),
            checkpoint_sha256="C" * 64,
            config=PolicyConfig(mode="training", model_timeout_seconds=1.0),
            rng=fallback_rng,
        ).decide(observation())
        self.assertEqual(fallback_rng.getstate(), fallback_state)

    def test_protected_callback_remains_exact_unsampled_teacher(self):
        teacher = StubTeacher(
            telemetry=(
                exact_telemetry(
                    active_owner_before="protected-owner",
                    active_owner_after="protected-owner",
                    precedence_reason="rank2_active_transaction_owner",
                    winning_rule_id="protected-owner",
                ),
            )
        )
        result = ResidualPolicy(
            teacher,
            model=FakeModel([-3.0, 3.0]),
            checkpoint_sha256="A" * 64,
            config=PolicyConfig(mode="training", model_timeout_seconds=1.0),
            rng=random.Random(1),
        ).decide(observation())
        self.assertEqual(result.action, result.teacher_action)
        self.assertFalse(result.ppo_eligible)
        self.assertFalse(result.sampled_stochastically)
        self.assertIsNone(result.behavior_logprob)
        self.assertEqual(result.behavior_formula_id, BEHAVIOR_FORMULA_ID)
        self.assertEqual(
            result.behavior_schema_version,
            BEHAVIOR_POLICY_SCHEMA_VERSION,
        )
        self.assertEqual(
            result.behavior_schema_sha256,
            behavior_policy_sha256(canonical_behavior_policy_receipt()),
        )

    def test_legacy_zero_checkpoint_upgrade_is_byte_distinct_and_weight_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            current_path = root / "current.pt"
            legacy_path = root / "legacy.pt"
            upgraded_path = root / "upgraded.pt"
            sources = checkpoint_source_hashes()
            model = ResidualActorCritic()
            save_checkpoint(
                current_path,
                model,
                checkpoint_metadata(source_hashes=sources),
            )
            payload = torch.load(
                current_path, map_location="cpu", weights_only=False
            )
            payload["metadata"]["model_schema_version"] = (
                "residual-actor-critic-v2"
            )
            del payload["metadata"]["behavior_policy_receipt"]
            del payload["metadata"]["behavior_policy_schema_sha256"]
            torch.save(payload, legacy_path)
            with self.assertRaisesRegex(ValueError, "model schema"):
                load_checkpoint(legacy_path, expected_source_hashes=sources)
            report = upgrade_checkpoint(legacy_path, upgraded_path)
            upgraded, metadata, optimizer = load_checkpoint(
                upgraded_path,
                expected_source_hashes=sources,
            )
            self.assertNotEqual(
                report["input_checkpoint_sha256"],
                report["output_checkpoint_sha256"],
            )
            self.assertIsNone(optimizer)
            self.assertEqual(
                metadata["behavior_policy_schema_sha256"],
                behavior_policy_sha256(),
            )
            for name, value in model.state_dict().items():
                self.assertTrue(torch.equal(value, upgraded.state_dict()[name]))


if __name__ == "__main__":
    unittest.main()
