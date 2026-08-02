from __future__ import annotations

import math
from pathlib import Path
import tempfile
import unittest

import torch
from torch.nn import functional as F

from archaludon_rl.bc_actor import (
    BehaviorCloningPolicy,
    apply_legal_action_mask,
    batched_actor_logits,
)
from archaludon_rl.frozen_sources import checkpoint_source_hashes
from archaludon_rl.evaluate_bc import _baseline_from_result, _compact_audit_directory
from archaludon_rl.model import (
    ResidualActorCritic,
    checkpoint_metadata,
    load_checkpoint,
    save_checkpoint,
)
from archaludon_rl.train_bc import actor_state_sha256

from .helpers import FakeModel, StubTeacher, observation


class BehaviorCloningTests(unittest.TestCase):
    def test_evaluation_accepts_both_baseline_result_schemas(self):
        baseline = {"arm_id": "iteration004", "overall": {"win_rate": 0.5}}
        self.assertEqual(_baseline_from_result({"baseline": baseline}), baseline)
        self.assertEqual(
            _baseline_from_result({"iteration004_baseline": baseline}), baseline
        )
        with self.assertRaisesRegex(ValueError, "neither baseline"):
            _baseline_from_result({})

    def test_evaluation_audit_directory_is_compact_and_deterministic(self):
        output_root = Path("C:/workspace/analysis_outputs/fixed_evaluation")
        first = _compact_audit_directory(
            output_root,
            "complete_bc_seed2026080211",
            "ogerpon_cornerstone_public_seat0",
        )
        repeated = _compact_audit_directory(
            output_root,
            "complete_bc_seed2026080211",
            "ogerpon_cornerstone_public_seat0",
        )
        other = _compact_audit_directory(
            output_root,
            "complete_bc_seed2026080211",
            "ogerpon_cornerstone_public_seat1",
        )
        self.assertEqual(first, repeated)
        self.assertNotEqual(first, other)
        self.assertEqual(first.parent, output_root / "audit")
        self.assertEqual(len(first.name), 16)

    def test_actor_logits_have_no_teacher_margin(self):
        teacher = StubTeacher(action=(0,))
        decision = BehaviorCloningPolicy(
            teacher,
            model=FakeModel([-1.0, 1.0]),
            checkpoint_sha256="A" * 64,
            model_timeout_seconds=1.0,
        ).decide(observation())
        self.assertEqual(decision.action, (1,))
        self.assertTrue(decision.actor_used)
        self.assertFalse(decision.fallback_used)
        self.assertEqual(teacher.calls, 1)

    def test_legal_mask_blocks_higher_illegal_logit(self):
        logits = torch.tensor([[1.0, 100.0, 2.0]])
        mask = torch.tensor([[True, False, True]], dtype=torch.bool)
        masked = apply_legal_action_mask(logits, mask)
        self.assertEqual(int(masked.argmax(dim=1)[0]), 2)
        self.assertTrue(torch.isneginf(masked[0, 1]))

    def test_nan_actor_output_falls_back_to_teacher(self):
        teacher = StubTeacher(action=(0,))
        decision = BehaviorCloningPolicy(
            teacher,
            model=FakeModel([math.nan, 0.0]),
            checkpoint_sha256="B" * 64,
            model_timeout_seconds=1.0,
        ).decide(observation())
        self.assertEqual(decision.action, teacher.action)
        self.assertTrue(decision.fallback_used)
        self.assertEqual(decision.model_failure_kind, "ValueError")

    def test_unsupported_multiselect_is_explicit_safety_fallback(self):
        teacher = StubTeacher(action=(0, 1))
        decision = BehaviorCloningPolicy(
            teacher,
            model=FakeModel([0.0, 1.0, 2.0]),
            checkpoint_sha256="C" * 64,
            model_timeout_seconds=1.0,
        ).decide(
            observation(
                options=[{"type": 14}, {"type": 14}, {"type": 14}],
                minimum=2,
                maximum=2,
            )
        )
        self.assertEqual(decision.action, teacher.action)
        self.assertTrue(decision.fallback_used)
        self.assertIn("unsupported_cardinality", decision.fallback_reason)

    def test_normal_bc_training_step_and_checkpoint_reload(self):
        torch.manual_seed(4)
        model = ResidualActorCritic()
        for parameter in model.value_head.parameters():
            parameter.requires_grad_(False)
        actor_parameters = [
            parameter
            for name, parameter in model.named_parameters()
            if not name.startswith("value_head.")
        ]
        optimizer = torch.optim.Adam(actor_parameters, lr=1e-2)
        states = torch.randn(4, model.config.state_dim)
        actions = torch.randn(4, 3, model.config.action_dim)
        mask = torch.tensor(
            [[True, True, False], [True, True, True], [True, False, True], [True, True, True]],
            dtype=torch.bool,
        )
        targets = torch.tensor([1, 2, 2, 0], dtype=torch.long)
        initial = F.cross_entropy(
            apply_legal_action_mask(batched_actor_logits(model, states, actions), mask),
            targets,
        )
        for _ in range(20):
            logits = apply_legal_action_mask(
                batched_actor_logits(model, states, actions),
                mask,
            )
            loss = F.cross_entropy(logits, targets)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
        final = F.cross_entropy(
            apply_legal_action_mask(batched_actor_logits(model, states, actions), mask),
            targets,
        )
        self.assertLess(float(final), float(initial))
        actor_sha = actor_state_sha256(model)
        metadata = checkpoint_metadata(
            source_hashes=checkpoint_source_hashes(),
            training={
                "algorithm": "teacher_action_behavior_cloning",
                "actor_logits_only": True,
                "teacher_fixed_margin": 0.0,
                "legal_action_mask": True,
                "future_ppo_kl_reference": True,
            },
        )
        with tempfile.TemporaryDirectory() as temporary:
            checkpoint = Path(temporary) / "bc.pt"
            save_checkpoint(checkpoint, model, metadata, optimizer=optimizer)
            reloaded, reloaded_metadata, _ = load_checkpoint(
                checkpoint,
                expected_source_hashes=checkpoint_source_hashes(),
            )
        self.assertEqual(actor_state_sha256(reloaded), actor_sha)
        self.assertEqual(
            reloaded_metadata["training"]["algorithm"],
            "teacher_action_behavior_cloning",
        )


if __name__ == "__main__":
    unittest.main()
