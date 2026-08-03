import unittest

from research.rl_ptcg.train_cem import add_relative_scores, assert_duplicate_results, dimensions


class RelativeCemScoreTests(unittest.TestCase):
    def test_dimensions_can_be_restricted_to_one_matchup(self):
        names = dimensions(("alakazam",))

        self.assertEqual(7, len(names))
        self.assertTrue(all(name.startswith("public_matchup_type=alakazam:") for name in names))

    def test_turn_type_dimensions_can_be_restricted_to_selected_buckets(self):
        names = dimensions(("archaludon",), "turn_type", ("4", "10"))

        self.assertEqual(14, len(names))
        self.assertIn("public_matchup_turn_type=archaludon:4:8", names)
        self.assertIn("public_matchup_turn_type=archaludon:10:8", names)

    def test_penalizes_candidate_that_sacrifices_one_opponent_bucket(self):
        results = [
            {
                "candidate": 0,
                "mean_reward": 0.6,
                "by_opponent": {
                    "a": {"mean_reward": 0.9},
                    "b": {"mean_reward": 0.3},
                },
            },
            {
                "candidate": 1,
                "mean_reward": 0.5,
                "by_opponent": {
                    "a": {"mean_reward": 0.5},
                    "b": {"mean_reward": 0.5},
                },
            },
        ]

        scored = add_relative_scores(results, worst_bucket_weight=0.25)

        self.assertAlmostEqual(scored[0]["mean_gain"], 0.1)
        self.assertAlmostEqual(scored[0]["worst_bucket_gain"], -0.2)
        self.assertAlmostEqual(scored[0]["robust_gain"], 0.05)
        self.assertEqual(scored[1]["robust_gain"], 0.0)

    def test_zero_candidate_is_found_by_id_not_position(self):
        results = [
            {"candidate": 1, "mean_reward": 0.4, "by_opponent": {"a": {"mean_reward": 0.4}}},
            {"candidate": 0, "mean_reward": 0.5, "by_opponent": {"a": {"mean_reward": 0.5}}},
        ]

        scored = add_relative_scores(results)

        self.assertEqual(scored[0]["robust_gain"], 0.0)
        self.assertAlmostEqual(scored[1]["robust_gain"], 0.125)

    def test_duplicate_control_detects_unseeded_engine_noise(self):
        common = {
            "wins": 5, "losses": 3, "errors": 0,
            "by_opponent": {"a": {"mean_reward": 0.25}},
        }
        results = [
            {"candidate": 0, "mean_reward": 0.25, **common},
            {"candidate": 1, "mean_reward": 0.20, **common},
        ]

        with self.assertRaisesRegex(RuntimeError, "seeded local engine"):
            assert_duplicate_results(results)

    def test_duplicate_control_accepts_identical_results(self):
        common = {
            "mean_reward": 0.25, "wins": 5, "losses": 3, "errors": 0,
            "by_opponent": {"a": {"mean_reward": 0.25}},
        }

        assert_duplicate_results([
            {"candidate": 0, **common},
            {"candidate": 1, **common},
        ])


if __name__ == "__main__":
    unittest.main()
