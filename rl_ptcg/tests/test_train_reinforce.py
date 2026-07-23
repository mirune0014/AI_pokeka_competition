import json
import tempfile
import unittest
from pathlib import Path

from rl_ptcg.train_reinforce import (
    load_weights,
    scheduled_opponent_and_seat,
    select_gradient_features,
)


class TrainTests(unittest.TestCase):
    def test_load_weights_normalizes_numbers(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "weights.json"
            path.write_text(json.dumps({"a": 1, "b": "-0.25"}), encoding="ascii")
            self.assertEqual({"a": 1.0, "b": -0.25}, load_weights(path))

    def test_load_weights_rejects_non_finite_values(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "weights.json"
            path.write_text('{"bad": NaN}', encoding="ascii")
            with self.assertRaises(ValueError):
                load_weights(path)

    def test_matchup_scope_drops_cross_matchup_features(self):
        gradient = {
            "bias": 1.0,
            "card_id=1": 2.0,
            "matchup_card=archaludon:1": 3.0,
            "public_matchup_type=alakazam:8": 4.0,
        }
        self.assertEqual(
            {
                "matchup_card=archaludon:1": 3.0,
                "public_matchup_type=alakazam:8": 4.0,
            },
            select_gradient_features(gradient, "matchup"),
        )
        self.assertIs(gradient, select_gradient_features(gradient, "all"))

    def test_schedule_pairs_both_seats_for_each_opponent(self):
        opponents = ["a", "b", "c"]
        self.assertEqual(
            [
                ("a", 0), ("a", 1),
                ("b", 0), ("b", 1),
                ("c", 0), ("c", 1),
                ("a", 0), ("a", 1),
            ],
            [scheduled_opponent_and_seat(opponents, game_id) for game_id in range(8)],
        )


if __name__ == "__main__":
    unittest.main()
