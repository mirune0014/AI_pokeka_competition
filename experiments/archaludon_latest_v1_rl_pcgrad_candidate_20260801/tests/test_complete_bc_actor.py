from __future__ import annotations

import unittest

import torch

from archaludon_rl.complete_bc_actor import CompleteActionBehaviorCloningPolicy
from archaludon_rl.model import ResidualActorCritic

from .helpers import StubTeacher, observation


class CompleteBCActorTests(unittest.TestCase):
    def test_optional_surface_uses_complete_candidate_without_fallback(self):
        model = ResidualActorCritic()
        decision = CompleteActionBehaviorCloningPolicy(
            StubTeacher(action=(1,)),
            model=model,
            checkpoint_sha256="A" * 64,
            model_timeout_seconds=1.0,
        ).decide(
            observation(
                options=[{"type": 3, "area": 2, "index": 0, "playerIndex": 0}, {"type": 3, "area": 2, "index": 1, "playerIndex": 0}],
                minimum=0,
                maximum=1,
                select_context=7,
            )
        )
        self.assertTrue(decision.actor_used)
        self.assertFalse(decision.fallback_used)
        self.assertFalse(decision.representability_failure)
        self.assertEqual(decision.action, ())

    def test_multiple_surface_returns_engine_valid_complete_action(self):
        model = ResidualActorCritic()
        decision = CompleteActionBehaviorCloningPolicy(
            StubTeacher(action=(2, 1)),
            model=model,
            checkpoint_sha256="B" * 64,
            model_timeout_seconds=1.0,
        ).decide(
            observation(
                options=[
                    {"type": 3, "area": 2, "index": 0, "playerIndex": 0},
                    {"type": 3, "area": 2, "index": 1, "playerIndex": 0},
                    {"type": 3, "area": 3, "index": 0, "playerIndex": 0},
                ],
                minimum=2,
                maximum=2,
                select_context=8,
            )
        )
        self.assertTrue(decision.actor_used)
        self.assertFalse(decision.fallback_used)
        self.assertEqual(len(decision.action), 2)
        self.assertEqual(len(set(decision.action)), 2)

    def test_nonfinite_model_is_explicit_teacher_fallback(self):
        model = ResidualActorCritic()
        with torch.no_grad():
            model.residual_head[-1].bias.fill_(float("nan"))
        teacher = StubTeacher(action=(0,))
        decision = CompleteActionBehaviorCloningPolicy(
            teacher,
            model=model,
            checkpoint_sha256="C" * 64,
            model_timeout_seconds=1.0,
        ).decide(observation())
        self.assertTrue(decision.fallback_used)
        self.assertEqual(decision.action, teacher.action)
        self.assertEqual(decision.model_failure_kind, "ValueError")


if __name__ == "__main__":
    unittest.main()
