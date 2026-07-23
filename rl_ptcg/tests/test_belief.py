import random
import unittest

from rl_ptcg.belief import compatible_deck_hypotheses, sample_hidden_zones, sample_search_guess


class BeliefTests(unittest.TestCase):
    def test_deck_catalog_filters_publicly_impossible_hypotheses(self):
        observation = {"current": {"yourIndex": 0, "players": [
            {}, {"active": [{"id": 12}], "bench": [], "discard": [{"id": 12}], "lostZone": []},
        ]}}
        compatible = [12, 12] + [20] * 58
        impossible = [12] + [20] * 59
        self.assertEqual(
            [compatible], compatible_deck_hypotheses(observation, [impossible, compatible, compatible])
        )

    def test_hidden_zones_preserve_counts_and_known_prize(self):
        deck = [1, 1, 2, 2, 3, 3, 4, 4]
        zones = sample_hidden_zones(deck, [1, 2], [3], 3, 2, 1, random.Random(5))
        self.assertEqual(3, len(zones.deck))
        self.assertEqual(2, len(zones.prize))
        self.assertIn(3, zones.prize)
        self.assertEqual(1, len(zones.hand))
        self.assertEqual(0, len(zones.unused))

    def test_search_guess_never_uses_hidden_opponent_identity(self):
        observation = {
            "current": {"yourIndex": 0, "players": [
                {"deckCount": 2, "handCount": 1, "hand": [{"id": 1}], "prize": [None],
                 "active": [{"id": 2}], "bench": [], "discard": []},
                {"deckCount": 2, "handCount": 1, "hand": [{"id": 999}], "prize": [None],
                 "active": [{"id": 5}], "bench": [], "discard": []},
            ]}
        }
        guess = sample_search_guess(observation, [1, 2, 3, 4, 8], [5, 6, 7, 8, 9], random.Random(3))
        self.assertNotIn(999, guess.opponent_hand)
        self.assertEqual(2, len(guess.opponent_deck))
        self.assertEqual(1, len(guess.opponent_prize))
        self.assertEqual(1, len(guess.opponent_hand))


if __name__ == "__main__":
    unittest.main()
