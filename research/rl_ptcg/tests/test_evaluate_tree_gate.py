import unittest

import numpy as np

from research.rl_ptcg.evaluate_tree_gate import build_pairs, threshold_metrics


def option(score, **features):
    return {"normalized_score": score, "features": features}


class TreeGateEvaluationTests(unittest.TestCase):
    def test_pair_labels_use_all_non_baseline_options(self):
        examples = [{
            "options": [
                option(1.0, bias=1, matchup_card=1),
                option(0.5, bias=1, matchup_card=1),
                option(0.0, bias=1, matchup_card=1),
            ],
            "baseline_action": [0],
            "expert_action": [2],
            "matchup": "synthetic",
            "metadata": {"episode_id": "a"},
        }]
        pairs, states = build_pairs(examples, feature_set="coarse")
        self.assertEqual([0, 1], [row["label"] for row in pairs])
        self.assertEqual([1, 2], [row["candidate_index"] for row in pairs])
        self.assertNotIn("c:matchup_card", pairs[0]["features"])
        self.assertEqual([0, 1], states[0]["pair_indices"])

    def test_threshold_metrics_are_state_level(self):
        examples = [
            {
                "options": [option(1.0), option(0.0)],
                "baseline_action": [0], "expert_action": [1],
                "matchup": "a", "metadata": {"episode_id": "one"},
            },
            {
                "options": [option(1.0), option(0.0)],
                "baseline_action": [0], "expert_action": [0],
                "matchup": "b", "metadata": {"episode_id": "two"},
            },
        ]
        pairs, states = build_pairs(examples)
        report = threshold_metrics(states, pairs, np.asarray([0.9, 0.8]), 0.7)
        self.assertEqual(1, report["overall"]["changed_correct"])
        self.assertEqual(1, report["overall"]["unchanged_false_override"])
        self.assertEqual(0.5, report["overall"]["override_precision"])


if __name__ == "__main__":
    unittest.main()
