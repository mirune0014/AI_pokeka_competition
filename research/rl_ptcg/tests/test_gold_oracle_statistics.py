import copy
import unittest

from research.rl_ptcg.gold_oracle_statistics import (
    GoldOracleStatisticsError,
    summarize_direct_comparisons,
    summarize_gold_oracle,
)


class GoldOracleStatisticsTests(unittest.TestCase):
    def make_data(self):
        state = {
            "state_id": "state",
            "decision_id": "decision",
            "episode_id": "episode",
            "candidate_sets": {
                "baseline": ["a"],
                "rule_top3": ["a"],
                "rule_topK": ["a"],
                "rule_diverse": ["a"],
                "rule_plus_gold": ["a", "g"],
            },
        }
        rows = []
        for batch in (0, 1):
            for hypothesis, mass, gold_value in (("known", 0.75, 1.0), ("unknown", 0.25, -1.0)):
                for policy in ("p0", "p1"):
                    for particle in (0, 1):
                        scenario_weight = mass / 2.0
                        common = {
                            "state_id": "state", "decision_id": "decision",
                            "episode_id": "episode", "batch_id": batch,
                            "baseline_action": "a", "particle_index": particle,
                            "opponent_policy_index": policy,
                            "continuation_policy_index": "c0",
                            "hypothesis_signature": hypothesis,
                            "hypothesis_kind": hypothesis,
                            "posterior_mass": mass,
                            "scenario_weight": scenario_weight,
                            "hidden_world_id": "%s-%d-%d" % (hypothesis, batch, particle),
                        }
                        rows.append({**common, "action": "a", "terminal_utility": -1.0})
                        rows.append({**common, "action": "g", "terminal_utility": gold_value})
        return rows, {"state": state}

    def test_posterior_weighted_advantage_and_stability(self):
        rows, states = self.make_data()
        report = summarize_gold_oracle(
            rows, states, bootstrap_repetitions=100, bootstrap_seed=7,
        )
        self.assertEqual(1, report["state_count"])
        self.assertEqual(2, report["batch_count"])
        self.assertEqual(1.0, report["batch_top1_agreement"])
        self.assertEqual(1, report["stable_label_count"])
        self.assertAlmostEqual(0.75, report["mean_rule_plus_gold_gap_vs_rule_diverse_win_probability"])
        unit = report["per_state_batch"][0]
        self.assertAlmostEqual(1.5, unit["actions"]["g"]["advantage_terminal_utility"])
        self.assertAlmostEqual(0.75, unit["actions"]["g"]["advantage_win_probability"])
        self.assertEqual("g", unit["oracle_action"])
        self.assertTrue(report["gold_gap_episode_bootstrap"]["insufficient_episode_clusters"])

    def test_unmatched_action_set_is_rejected(self):
        rows, states = self.make_data()
        broken = copy.deepcopy(rows)
        broken.pop()
        with self.assertRaisesRegex(GoldOracleStatisticsError, "unmatched action"):
            summarize_gold_oracle(broken, states, bootstrap_repetitions=10)

    def test_four_batch_stability_uses_later_batches(self):
        rows, states = self.make_data()
        first_batch = [copy.deepcopy(row) for row in rows if row["batch_id"] == 0]
        for batch in (2, 3):
            for template in first_batch:
                row = copy.deepcopy(template)
                row["batch_id"] = batch
                row["hidden_world_id"] = "%s-b%d" % (row["hidden_world_id"], batch)
                if row["action"] == "g":
                    row["terminal_utility"] = -1.0
                rows.append(row)
        report = summarize_gold_oracle(rows, states, bootstrap_repetitions=10)
        self.assertEqual(4, report["batch_count"])
        self.assertEqual(0.0, report["batch_top1_agreement"])
        self.assertEqual(0, report["stable_label_count"])

    def test_four_batch_stable_label_records_every_batch(self):
        rows, states = self.make_data()
        first_batch = [copy.deepcopy(row) for row in rows if row["batch_id"] == 0]
        for batch in (2, 3):
            for template in first_batch:
                row = copy.deepcopy(template)
                row["batch_id"] = batch
                row["hidden_world_id"] = "%s-b%d" % (row["hidden_world_id"], batch)
                rows.append(row)
        report = summarize_gold_oracle(rows, states, bootstrap_repetitions=10)
        self.assertEqual(1, report["stable_label_count"])
        self.assertEqual([0, 1, 2, 3], report["stable_labels"][0]["batch_ids"])

    def test_direct_gold_comparison_uses_rule_reference(self):
        rows, states = self.make_data()
        report = summarize_direct_comparisons(
            rows,
            states,
            {"state": {"reference_action": "a", "candidate_action": "g"}},
            bootstrap_repetitions=100,
            bootstrap_seed=9,
        )
        self.assertAlmostEqual(0.75, report["mean_upper_bound_gold_gap_win_probability"])
        self.assertEqual(1, report["positive_lcb_in_both_batches_states"])
        self.assertEqual(0, report["ucb_below_one_point_in_both_batches_states"])
        self.assertTrue(
            report["per_state_batch"][0]["is_upper_bound_on_gold_vs_full_rule_oracle"]
        )

    def test_direct_comparison_uses_every_available_batch(self):
        rows, states = self.make_data()
        first_batch = [copy.deepcopy(row) for row in rows if row["batch_id"] == 0]
        for batch in (2, 3):
            for template in first_batch:
                row = copy.deepcopy(template)
                row["batch_id"] = batch
                row["hidden_world_id"] = "%s-b%d" % (row["hidden_world_id"], batch)
                if row["action"] == "g":
                    row["terminal_utility"] = -1.0
                rows.append(row)
        report = summarize_direct_comparisons(
            rows,
            states,
            {"state": {"reference_action": "a", "candidate_action": "g"}},
            bootstrap_repetitions=10,
        )
        self.assertEqual(4, report["batch_count"])
        self.assertEqual(0.0, report["batch_sign_agreement"])
        self.assertEqual(0, report["positive_lcb_in_both_batches_states"])


if __name__ == "__main__":
    unittest.main()
