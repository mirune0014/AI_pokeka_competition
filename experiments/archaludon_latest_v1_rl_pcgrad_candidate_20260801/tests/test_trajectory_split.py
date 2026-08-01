from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import torch

from archaludon_rl.encoders import ACTION_DIM, STATE_DIM
from archaludon_rl.model import ResidualActorCritic
from archaludon_rl.reference_policy import (
    canonical_reference_prior_receipt,
    reference_prior_sha256,
    validate_reference_prior_identity,
)
from archaludon_rl.train_ppo import PPOConfig, _ppo_batch_objective
from archaludon_rl.trajectory_split import (
    SPLIT_SCHEMA_VERSION,
    load_locked_trajectory_split,
)


class LockedTrajectorySplitTests(unittest.TestCase):
    def test_split_is_deterministic_disjoint_and_complete(self):
        manifest_hash = "A" * 64
        dataset_hash = "B" * 64
        episodes = tuple(
            {
                "episode_id": f"episode-{index}",
                "opponent_id": f"opponent-{index}",
                "seat": index % 2,
                "seed": 100 + index,
                "terminal_result": index % 2 if index != 3 else 1 - index % 2,
                "decisions": [
                    {"ppo_eligible": True, "decision_index": index * 10 + offset}
                    for offset in range(index + 1)
                ],
            }
            for index in range(4)
        )
        validation_ids = ("episode-1", "episode-3")
        algorithm = "unit-test-split"
        seed = "7"
        digest = hashlib.sha256(
            "\0".join(
                (algorithm, dataset_hash, seed, *sorted(validation_ids))
            ).encode("utf-8")
        ).hexdigest().upper()
        spec = {
            "schema_version": SPLIT_SCHEMA_VERSION,
            "algorithm_id": algorithm,
            "selection_seed": seed,
            "selection_digest": digest,
            "manifest_sha256": manifest_hash,
            "dataset_sha256": dataset_hash,
            "validation_episode_ids": list(validation_ids),
            "expected": {
                "train_episode_count": 2,
                "validation_episode_count": 2,
                "train_ppo_row_count": 4,
                "validation_ppo_row_count": 6,
                "validation_opponent_count": 2,
                "validation_seat_counts": {"1": 2},
                "validation_seed_counts": {"101": 1, "103": 1},
                "validation_outcome_counts": {"loss": 1, "win": 1},
            },
        }
        dataset = SimpleNamespace(
            manifest_sha256=manifest_hash,
            manifest={"dataset_sha256": dataset_hash},
            episodes=episodes,
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "split.json"
            path.write_text(json.dumps(spec), encoding="utf-8")
            first = load_locked_trajectory_split(dataset, path)
            second = load_locked_trajectory_split(dataset, path)
        self.assertEqual(
            [row["episode_id"] for row in first.train_episodes],
            ["episode-0", "episode-2"],
        )
        self.assertEqual(
            [row["episode_id"] for row in first.validation_episodes],
            ["episode-1", "episode-3"],
        )
        self.assertEqual(first.receipt, second.receipt)
        self.assertEqual(first.receipt["train_ppo_row_count"], 4)
        self.assertEqual(first.receipt["validation_ppo_row_count"], 6)

    def test_validation_evaluation_does_not_change_train_gradient(self):
        torch.manual_seed(9)
        model = ResidualActorCritic()
        reference = validate_reference_prior_identity(
            canonical_reference_prior_receipt(), reference_prior_sha256()
        )

        def row(episode_id: str, scale: float):
            state = [scale] * STATE_DIM
            actions = [[0.0] * ACTION_DIM, [scale] * ACTION_DIM]
            with torch.no_grad():
                residuals, _ = model(
                    torch.tensor(state, dtype=torch.float32),
                    torch.tensor(actions, dtype=torch.float32),
                )
                from archaludon_rl.train_ppo import _torch_behavior_distribution

                _, log_probabilities = _torch_behavior_distribution(
                    residuals, teacher_index=0, reference_config=reference
                )
            episode = {"episode_id": episode_id}
            decision = {
                "decision_index": 0,
                "state_vector": state,
                "action_vectors": actions,
                "teacher_action": [0],
                "final_action": [1],
                "behavior_logprob": float(log_probabilities[1]),
            }
            return episode, decision

        train_rows = [row("train", 0.25)]
        validation_rows = [row("validation", -0.5)]
        config = PPOConfig(epochs=1)
        train_advantages = {("train", 0): (1.0, 0.5)}
        validation_advantages = {("validation", 0): (-5.0, -2.0)}

        def train_gradient():
            model.zero_grad(set_to_none=True)
            batch = _ppo_batch_objective(
                model,
                train_rows,
                train_advantages,
                torch.tensor([1.0]),
                config=config,
                kl_coef=0.1,
                device="cpu",
                reference_config=reference,
            )
            batch["loss"].backward()
            return tuple(
                parameter.grad.detach().clone()
                for parameter in model.parameters()
                if parameter.grad is not None
            )

        before = train_gradient()
        with torch.no_grad():
            _ppo_batch_objective(
                model,
                validation_rows,
                validation_advantages,
                torch.tensor([-100.0]),
                config=config,
                kl_coef=0.1,
                device="cpu",
                reference_config=reference,
            )
        after = train_gradient()
        self.assertEqual(len(before), len(after))
        self.assertTrue(all(torch.equal(left, right) for left, right in zip(before, after)))


if __name__ == "__main__":
    unittest.main()
