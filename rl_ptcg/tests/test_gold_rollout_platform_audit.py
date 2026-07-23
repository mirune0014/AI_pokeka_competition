import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rl_ptcg.gold_rollout_platform_audit import compare_platform_outputs, compare_rows


class GoldRolloutPlatformAuditTests(unittest.TestCase):
    def row(self, action="a", utility=1.0):
        return {
            "state_id": "s", "batch_id": 0, "action": action,
            "hypothesis_signature": "h", "opponent_policy_index": "o",
            "continuation_policy_index": "c", "particle_index": 0,
            "hidden_world_id": "w", "scenario_weight": 1.0,
            "terminal_utility": utility,
        }

    def test_balanced_platform_discordance_preserves_action_mean(self):
        left = [self.row("a", -1.0), dict(self.row("a", 1.0), particle_index=1)]
        right = [self.row("a", 1.0), dict(self.row("a", -1.0), particle_index=1)]
        result = compare_rows(left, right)
        self.assertTrue(result["structural_rows_equal"])
        self.assertEqual(2, result["utility_discordant_rows"])
        self.assertEqual(1, result["left_better_rows"])
        self.assertEqual(1, result["right_better_rows"])
        self.assertEqual(0.0, result["max_abs_action_mean_utility_delta"])

    def test_structural_mismatch_is_reported(self):
        left = [self.row()]
        right = [copy.deepcopy(left[0])]
        right[0]["hidden_world_id"] = "other"
        result = compare_rows(left, right)
        self.assertFalse(result["structural_rows_equal"])
        self.assertEqual(0, result["common_rows"])

    def test_separate_verification_workspaces_are_recorded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            left_workspace = root / "downloaded_kaggle_workspace"
            right_workspace = root / "local_workspace"
            left = left_workspace / "outputs" / "run"
            right = right_workspace / "outputs" / "run"
            for output, platform in ((left, "Kaggle Linux"), (right, "WSL Linux")):
                (output / "shards" / "s").mkdir(parents=True)
                manifest = {
                    "state_ids": ["s"], "batch_ids": [0],
                    "runtime": {"platform": platform}, "engine": {"binary_sha256": platform},
                    "config": {"seed": "paired"},
                }
                shard = {
                    "state_id": "s", "batch_id": 0, "candidate_ids": ["a"],
                    "rows_sha256": "unused", "rows": [self.row()],
                }
                report = {
                    "posterior_weighted_teacher_statistics": {
                        "per_state_batch": [{"state_id": "s", "batch_id": 0, "action_rank": ["a"]}],
                    },
                }
                (output / "run_manifest.json").write_text(json.dumps(manifest), encoding="ascii")
                (output / "shards" / "s" / "batch_000.json").write_text(
                    json.dumps(shard), encoding="ascii",
                )
                (output / "report.json").write_text(json.dumps(report), encoding="ascii")
        
            with patch(
                "rl_ptcg.gold_rollout_platform_audit.verify_oracle_output",
                side_effect=[{"rows": 1}, {"rows": 1}],
            ):
                result = compare_platform_outputs(
                    left, right, root, left_workspace, right_workspace,
                )
            self.assertEqual("gold_rollout_platform_audit.v2", result["schema_version"])
            self.assertEqual(
                "downloaded_kaggle_workspace", result["left"]["verification_workspace"],
            )
            self.assertEqual("local_workspace", result["right"]["verification_workspace"])
            self.assertTrue(result["semantic_run_config_equal"])


if __name__ == "__main__":
    unittest.main()
