import copy
import json
import unittest

from rl_ptcg.public_state import canonical_public_state, public_state_hash


class PublicStateTests(unittest.TestCase):
    def observation(self):
        return {
            "search_begin_input": {"future": "excluded"},
            "current": {
                "turn": 4, "yourIndex": 0,
                "players": [
                    {"deckCount": 20, "handCount": 3, "active": [{"id": 11, "hp": 90, "serial": 7}],
                     "bench": [{"id": 12, "hp": 60, "serial": 8}], "hand": [{"id": 999}],
                     "deck": [{"id": 998}], "discard": [{"id": 13, "serial": 9}]},
                    {"deckCount": 18, "handCount": 4, "active": [{"id": 21, "hp": 120}], "bench": []},
                ],
                "stadium": [{"id": 30, "serial": 5}],
            },
            "select": {"minCount": 1, "maxCount": 1, "option": [
                {"type": "Attack", "index": 0, "serial": 12, "cardId": 11},
                {"type": "Attack", "index": 1, "serial": 13, "cardId": 11},
            ]},
        }

    def test_hash_ignores_hidden_zones_and_raw_serials(self):
        first = self.observation()
        second = copy.deepcopy(first)
        second["current"]["players"][0]["deck"] = [{"id": 1}, {"id": 2}]
        second["current"]["players"][0]["active"][0]["serial"] = 1000
        second["select"]["option"][0]["serial"] = 2000
        self.assertEqual(public_state_hash(first, 0), public_state_hash(second, 0))
        encoded = json.dumps(canonical_public_state(first, 0))
        self.assertNotIn("serial", encoded)
        self.assertNotIn("search_begin_input", encoded)
        self.assertIn("999", encoded)
        self.assertNotIn("998", encoded)

    def test_hash_includes_own_hand_but_not_opponent_hidden_hand(self):
        original = self.observation()
        own_changed = copy.deepcopy(original)
        own_changed["current"]["players"][0]["hand"] = [{"id": 997}]
        opponent_changed = copy.deepcopy(original)
        opponent_changed["current"]["players"][1]["hand"] = [{"id": 996}]
        self.assertNotEqual(public_state_hash(original, 0), public_state_hash(own_changed, 0))
        self.assertEqual(public_state_hash(original, 0), public_state_hash(opponent_changed, 0))

    def test_unordered_public_zones_and_hand_have_stable_hashes(self):
        original = self.observation()
        original["current"]["players"][0]["hand"] = [{"id": 3}, {"id": 2}]
        original["current"]["players"][0]["discard"] = [{"id": 5}, {"id": 4}]
        reordered = copy.deepcopy(original)
        reordered["current"]["players"][0]["hand"].reverse()
        reordered["current"]["players"][0]["discard"].reverse()
        self.assertEqual(public_state_hash(original, 0), public_state_hash(reordered, 0))

    def test_hash_changes_for_public_board_or_legal_option_change(self):
        original = self.observation()
        board_changed = copy.deepcopy(original)
        board_changed["current"]["players"][0]["bench"][0]["hp"] = 50
        option_changed = copy.deepcopy(original)
        option_changed["select"]["option"][1]["index"] = 2
        original_hash = public_state_hash(original, 0)
        self.assertNotEqual(original_hash, public_state_hash(board_changed, 0))
        self.assertNotEqual(original_hash, public_state_hash(option_changed, 0))


if __name__ == "__main__":
    unittest.main()
