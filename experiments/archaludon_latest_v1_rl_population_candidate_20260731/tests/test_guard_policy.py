from __future__ import annotations

import math
import random
from types import SimpleNamespace
import unittest

from archaludon_rl.collect_rollouts import collect
from archaludon_rl.decision_contract import DecisionContract, GuardCategory
from archaludon_rl.policy import PolicyConfig, ResidualPolicy
from archaludon_rl.teacher_adapter import TeacherDecision

from .helpers import FakeModel, StubTeacher, exact_telemetry, observation


class GuardPolicyTests(unittest.TestCase):
    def test_collection_rejects_timeout_different_from_deployment(self):
        with self.assertRaisesRegex(ValueError, "deployment timeout"):
            collect(SimpleNamespace(run_id="unit-test", timeout_seconds=1.0))

    def test_collection_rejects_unsafe_run_id_before_filesystem_access(self):
        with self.assertRaisesRegex(ValueError, "run-id"):
            collect(SimpleNamespace(run_id="../escape", timeout_seconds=0.05))

    def test_protected_owner_hard_fallback_and_shadow_logged(self):
        obs = observation()
        teacher = StubTeacher(
            telemetry=(
                exact_telemetry(
                    active_owner_before="rule-x",
                    active_owner_after="rule-x",
                    precedence_reason="rank2_active_transaction_owner",
                    winning_rule_id="rule-x",
                ),
            )
        )
        model = FakeModel([-3.0, 3.0])
        policy = ResidualPolicy(
            teacher,
            model=model,
            checkpoint_sha256="A" * 64,
            config=PolicyConfig(mode="deployment", model_timeout_seconds=1.0),
        )
        result = policy.decide(obs)
        self.assertEqual(result.action, (0,))
        self.assertEqual(result.neural_shadow_action, (1,))
        self.assertFalse(result.ppo_eligible)
        self.assertTrue(result.fallback_used)
        self.assertIn(GuardCategory.LATEST_CERTIFIED_OWNER, result.guard.categories)
        self.assertEqual(teacher.calls, 1)

    def test_all_legal_options_retained_and_unknown_effect_not_fallback(self):
        obs = observation()
        teacher = StubTeacher(
            telemetry=(
                exact_telemetry(
                    heuristic_scores=[-999999, -1],
                    proposals=[{"score": -999999, "eligible": False}],
                ),
            )
        )
        result = ResidualPolicy(
            teacher,
            model=FakeModel([0.0, 0.0]),
            checkpoint_sha256="B" * 64,
            config=PolicyConfig(mode="deployment", model_timeout_seconds=1.0),
        ).decide(obs)
        self.assertEqual(result.guard.legal_option_mask, (True, True))
        self.assertEqual(result.guard.actor_option_mask, (True, True))
        self.assertIn(GuardCategory.UNKNOWN_EFFECT, result.guard.categories)
        self.assertFalse(result.fallback_used)
        self.assertTrue(result.guard.ppo_eligible)
        self.assertFalse(result.ppo_eligible)
        self.assertEqual(result.action, result.teacher_action)

    def test_nan_is_exact_teacher_fallback_in_train_and_deploy(self):
        for mode in ("training", "deployment"):
            teacher = StubTeacher()
            result = ResidualPolicy(
                teacher,
                model=FakeModel([math.nan, 0.0]),
                checkpoint_sha256="C" * 64,
                config=PolicyConfig(mode=mode, model_timeout_seconds=1.0),
                rng=random.Random(3),
            ).decide(observation())
            self.assertEqual(result.action, result.teacher_action)
            self.assertTrue(result.fallback_used)
            self.assertFalse(result.ppo_eligible)
            self.assertIn("model_failure", result.fallback_reason)
            self.assertEqual(teacher.calls, 1)

    def test_train_deploy_eligibility_identical(self):
        obs = observation()
        training = ResidualPolicy(
            StubTeacher(),
            model=FakeModel([0.0, 0.0]),
            checkpoint_sha256="D" * 64,
            config=PolicyConfig(mode="training", model_timeout_seconds=1.0),
            rng=random.Random(2),
        ).decide(obs)
        deployment = ResidualPolicy(
            StubTeacher(),
            model=FakeModel([0.0, 0.0]),
            checkpoint_sha256="D" * 64,
            config=PolicyConfig(mode="deployment", model_timeout_seconds=1.0),
        ).decide(obs)
        self.assertEqual(training.guard.actor_learnable, deployment.guard.actor_learnable)
        self.assertEqual(training.guard.actor_option_mask, deployment.guard.actor_option_mask)
        self.assertTrue(training.ppo_eligible)
        self.assertFalse(deployment.ppo_eligible)
        self.assertTrue(training.sampled_stochastically)
        self.assertFalse(deployment.sampled_stochastically)
        self.assertIsNotNone(training.behavior_logprob)
        self.assertIsNone(deployment.behavior_logprob)

    def test_non_main_context_is_surface_excluded(self):
        model = FakeModel([0.0, 0.0])
        result = ResidualPolicy(
            StubTeacher(),
            model=model,
            checkpoint_sha256="F" * 64,
            config=PolicyConfig(mode="training", model_timeout_seconds=1.0),
        ).decide(observation(select_context=35))
        self.assertFalse(result.guard.actor_learnable)
        self.assertFalse(result.ppo_eligible)
        self.assertEqual(result.action, result.teacher_action)
        self.assertIn(GuardCategory.SURFACE_EXCLUDED, result.guard.categories)
        self.assertEqual(model.calls, 0)
        self.assertNotIn("model_failure", result.fallback_reason)

    def test_single_option_surface_is_teacher_fallback_not_model_failure(self):
        model = FakeModel([0.0])
        result = ResidualPolicy(
            StubTeacher(),
            model=model,
            checkpoint_sha256="H" * 64,
            config=PolicyConfig(mode="training", model_timeout_seconds=1.0),
        ).decide(observation(options=[{"type": 14}]))
        self.assertEqual(result.action, result.teacher_action)
        self.assertFalse(result.ppo_eligible)
        self.assertTrue(result.fallback_used)
        self.assertIn("option_count:1", result.fallback_reason)
        self.assertNotIn("model_failure", result.fallback_reason)
        self.assertEqual(model.calls, 0)

    def test_multiple_telemetry_rows_fail_closed(self):
        teacher = StubTeacher(
            telemetry=(exact_telemetry(), exact_telemetry())
        )
        result = ResidualPolicy(
            teacher,
            model=FakeModel([0.0, 0.0]),
            checkpoint_sha256="G" * 64,
            config=PolicyConfig(mode="training", model_timeout_seconds=1.0),
        ).decide(observation())
        self.assertFalse(result.ppo_eligible)
        self.assertEqual(result.action, result.teacher_action)
        self.assertIn(GuardCategory.EXECUTION_INVARIANT, result.guard.categories)

    def test_no_checkpoint_exact_parity(self):
        teacher = StubTeacher(action=(1,))
        result = ResidualPolicy(teacher, model=None).decide(observation())
        self.assertEqual(result.action, (1,))
        self.assertEqual(result.teacher_action, (1,))
        self.assertFalse(result.ppo_eligible)
        self.assertEqual(teacher.calls, 1)


if __name__ == "__main__":
    unittest.main()
