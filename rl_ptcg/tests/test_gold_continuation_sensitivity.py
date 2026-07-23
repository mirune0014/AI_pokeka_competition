from __future__ import annotations

import unittest

from rl_ptcg.gold_continuation_sensitivity import summarize_shard_rows


class ContinuationSensitivityRowsTest(unittest.TestCase):
    def _rows(self):
        rows = []
        utilities = {
            "continuation-a": {"baseline": [-1.0, 1.0], "target": [1.0, 1.0], "other": [-1.0, -1.0]},
            "continuation-b": {"baseline": [-1.0, -1.0], "target": [-1.0, 1.0], "other": [1.0, 1.0]},
        }
        for continuation, actions in utilities.items():
            for action, values in actions.items():
                for utility in values:
                    rows.append({
                        "continuation_policy_index": continuation,
                        "action": action,
                        "scenario_weight": 0.25,
                        "terminal_utility": utility,
                    })
        return rows

    def test_weighted_target_advantage_is_computed_per_continuation(self):
        result = summarize_shard_rows(
            self._rows(),
            continuation_policy_ids=["continuation-a", "continuation-b"],
            candidate_ids=["baseline", "target", "other"],
            target_action="target",
            baseline_action="baseline",
        )
        self.assertEqual([item["advantage_win_probability"] for item in result], [0.5, 0.5])
        self.assertEqual([item["target_rank"] for item in result], [1, 2])

    def test_missing_continuation_cell_is_rejected(self):
        rows = [row for row in self._rows() if not (
            row["continuation_policy_index"] == "continuation-b" and row["action"] == "target"
        )]
        with self.assertRaisesRegex(ValueError, "has no rows"):
            summarize_shard_rows(
                rows,
                continuation_policy_ids=["continuation-a", "continuation-b"],
                candidate_ids=["baseline", "target", "other"],
                target_action="target",
                baseline_action="baseline",
            )

    def test_single_continuation_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "at least two"):
            summarize_shard_rows(
                self._rows(),
                continuation_policy_ids=["continuation-a"],
                candidate_ids=["baseline", "target", "other"],
                target_action="target",
                baseline_action="baseline",
            )


if __name__ == "__main__":
    unittest.main()
