import unittest

from research.rl_ptcg.evaluate_policy_value import add_metric, average_finished, blank_metrics, finish


class EvaluatePolicyValueMetricTests(unittest.TestCase):
    def test_all_state_metrics_remain_the_existing_shape(self):
        metrics = blank_metrics()
        add_metric(metrics, True, 1.0, 1.0)
        result = finish(metrics)
        self.assertEqual(result["records"], 1)
        self.assertEqual(result["policy_exact"], 1.0)
        self.assertEqual(result["value_mae"], 0.0)
        self.assertEqual(result["win_brier"], 0.0)
        self.assertEqual(
            set(result),
            {"records", "policy_exact", "value_mae", "win_brier",
             "mean_predicted_value", "mean_target_value"},
        )

    def test_episode_balanced_view_gives_long_and_short_episodes_equal_weight(self):
        short = blank_metrics()
        add_metric(short, True, 1.0, 1.0)
        long = blank_metrics()
        for _ in range(9):
            add_metric(long, False, -1.0, 1.0)

        result = average_finished([short, long])

        self.assertEqual(result["records"], 2)
        self.assertEqual(result["policy_exact"], 0.5)
        self.assertEqual(result["value_mae"], 1.0)

    def test_first_decision_is_one_observation_per_episode(self):
        first = blank_metrics()
        second = blank_metrics()
        add_metric(first, True, 1.0, 1.0)
        add_metric(second, False, -1.0, 1.0)

        # The evaluator's first-decision accumulator receives only the first
        # row for each public (opponent, episode_id) pair.
        result = finish(first)
        self.assertEqual(result["records"], 1)
        self.assertEqual(result["policy_exact"], 1.0)
        self.assertNotEqual(finish(first)["policy_exact"], finish(second)["policy_exact"])

    def test_value_only_observation_does_not_change_policy_accuracy(self):
        metrics = blank_metrics()
        add_metric(metrics, True, 0.5, 1.0)
        add_metric(metrics, None, -0.5, -1.0)
        result = finish(metrics)
        self.assertEqual(result["records"], 2)
        self.assertEqual(result["policy_exact"], 1.0)


if __name__ == "__main__":
    unittest.main()
