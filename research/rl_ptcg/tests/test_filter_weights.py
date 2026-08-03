import unittest

from research.rl_ptcg.filter_weights import filter_weights, matchup_from_key


class FilterTests(unittest.TestCase):
    def test_matchup_parser_and_filter(self):
        self.assertEqual("starmie", matchup_from_key("matchup_card=starmie:123"))
        self.assertEqual(
            "alakazam", matchup_from_key("public_matchup_type=alakazam:8")
        )
        self.assertIsNone(matchup_from_key("card_id=123"))
        weights = {
            "matchup_card=starmie:123": 1.0,
            "public_matchup_type=starmie:8": 4.0,
            "matchup_type=generic:7": 2.0,
            "card_id=123": 3.0,
        }
        self.assertEqual(
            {
                "matchup_card=starmie:123": 1.0,
                "public_matchup_type=starmie:8": 4.0,
            },
            filter_weights(weights, ["starmie"]),
        )
        self.assertEqual(
            {"public_matchup_type=starmie:8": 4.0},
            filter_weights(weights, ["starmie"], ["public_matchup_"]),
        )
        self.assertEqual(
            {"public_matchup_type=starmie:8": 4.0},
            filter_weights(weights, ["starmie"], min_abs=2.5),
        )
        self.assertEqual(
            {
                "matchup_card=starmie:123": 0.5,
                "public_matchup_type=starmie:8": 2.0,
            },
            filter_weights(weights, ["starmie"], scale=0.5),
        )


if __name__ == "__main__":
    unittest.main()
