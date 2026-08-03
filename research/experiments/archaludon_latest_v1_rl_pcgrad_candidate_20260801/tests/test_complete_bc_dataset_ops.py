from __future__ import annotations

import unittest

from archaludon_rl.complete_bc_dataset_ops import (
    merge_complete_bc_payloads,
    payload_from_dagger_rows,
)
from archaludon_rl.encoders import ACTION_DIM, STATE_DIM


def _episode(episode_id: str) -> dict[str, object]:
    return {
        "episode_id": episode_id,
        "opponent_id": "test_opponent",
        "seat": 0,
        "seed": 1,
        "split": "train",
        "terminal_result": 0,
        "action_errors": 0,
        "max_step_hit": False,
    }


def _row(episode_index: int, family: str, value: float) -> dict[str, object]:
    return {
        "episode_index": episode_index,
        "state": [value] * STATE_DIM,
        "option_vectors": [
            [value] * ACTION_DIM,
            [value + 1.0] * ACTION_DIM,
        ],
        "candidate_members": [(0,), (1,)],
        "target": 1,
        "family": family,
        "optional": False,
        "multiple": False,
        "duplicate_canonical_actions": 0,
    }


class CompleteBCDatasetOpsTests(unittest.TestCase):
    def test_merge_preserves_locked_validation_and_appends_train_only_rows(self):
        base = payload_from_dagger_rows(
            episodes=[_episode("base_train"), _episode("base_validation")],
            rows=[_row(0, "1", 1.0), _row(1, "2", 2.0)],
            source={"kind": "base-fixture"},
        )
        base["episodes"][1]["split"] = "validation"
        base["counts"]["train_episodes"] = 1
        base["counts"]["validation_episodes"] = 1
        addition = payload_from_dagger_rows(
            episodes=[_episode("dagger_train")],
            rows=[_row(0, "3", 3.0)],
            source={"kind": "dagger-fixture"},
        )

        merged = merge_complete_bc_payloads(
            base=base,
            additions=[addition],
            source={"kind": "merged-fixture"},
        )

        self.assertEqual(merged["counts"]["episodes"], 3)
        self.assertEqual(merged["counts"]["train_episodes"], 2)
        self.assertEqual(merged["counts"]["validation_episodes"], 1)
        self.assertEqual(merged["counts"]["decisions"], 3)
        self.assertEqual(
            merged["tensors"]["episode_indices"].tolist(), [0, 1, 2]
        )
        self.assertEqual(
            merged["tensors"]["states"][1].tolist(),
            base["tensors"]["states"][1].tolist(),
        )
        self.assertEqual(
            merged["tensors"]["option_offsets"].tolist(), [0, 2, 4, 6]
        )
        self.assertEqual(
            merged["tensors"]["decision_candidate_offsets"].tolist(),
            [0, 2, 4, 6],
        )
        self.assertEqual(set(merged["family_table"]), {"1", "2", "3"})

    def test_merge_rejects_validation_from_dagger_addition(self):
        base = payload_from_dagger_rows(
            episodes=[_episode("base_train"), _episode("base_validation")],
            rows=[_row(0, "1", 1.0), _row(1, "2", 2.0)],
            source={"kind": "base-fixture"},
        )
        base["episodes"][1]["split"] = "validation"
        addition = payload_from_dagger_rows(
            episodes=[_episode("bad_validation")],
            rows=[_row(0, "3", 3.0)],
            source={"kind": "dagger-fixture"},
        )
        addition["episodes"][0]["split"] = "validation"
        with self.assertRaisesRegex(ValueError, "may not add validation"):
            merge_complete_bc_payloads(
                base=base,
                additions=[addition],
                source={"kind": "merged-fixture"},
            )


if __name__ == "__main__":
    unittest.main()
