import unittest

from research.rl_ptcg.encoding import OPTION_FEATURE_NAMES, SCHEMA, STATE_FEATURE_NAMES, encode_observation


class Item:
    def __init__(self, **values):
        self.__dict__.update(values)


def observation(as_objects=False):
    mine = {"deckCount": 34, "handCount": 5, "hand": [{"id": 900}], "prize": [None] * 6,
            "active": [{"id": 10, "hp": 120, "maxHp": 180, "energyCards": [{"id": 101}], "tools": [{"id": 102}]}],
            "bench": [{"id": 11, "hp": 80, "maxHp": 90, "energies": [3]}], "discard": [{"id": 20}], "lostZone": [{"id": 21}]}
    opp = {"deckCount": 33, "handCount": 7, "hand": [{"id": 777}], "prize": [{"id": 778}] * 6,
           "active": [{"id": 30, "hp": 100, "maxHp": 220}], "bench": [], "discard": [{"id": 40}], "lostZone": []}
    select = {"type": 0, "context": 35, "minCount": 1, "maxCount": 1,
              "option": [{"type": 7, "cardId": 10, "attackId": 2, "area": 4, "index": 0, "playerIndex": 0}]}
    data = {"current": {"turn": 3, "turnActionCount": 2, "yourIndex": 0, "firstPlayer": 0, "stadium": [{"id": 50}], "players": [mine, opp]}, "select": select}
    if not as_objects:
        return data
    current = dict(data["current"])
    current["players"] = [Item(**mine), Item(**opp)]
    return Item(current=Item(**current), select=Item(**select))


class EncodingTests(unittest.TestCase):
    def test_fixed_schema_and_public_board_values(self):
        encoded = encode_observation(observation())
        self.assertEqual(len(STATE_FEATURE_NAMES), len(encoded.state_vector))
        self.assertEqual(len(OPTION_FEATURE_NAMES), len(encoded.option_vectors[0]))
        self.assertEqual("ptcg-public-v4", SCHEMA.version)
        values = dict(zip(STATE_FEATURE_NAMES, encoded.state_vector))
        self.assertEqual(10.0, values["self_active_card_id"])
        self.assertEqual(60.0, values["self_active_damage"])
        self.assertEqual(40.0, values["opponent_discard_0_id"])
        self.assertEqual(50.0, values["stadium_id"])

    def test_hidden_hand_and_prize_ids_do_not_change_encoding(self):
        first = observation()
        second = observation()
        second["current"]["players"][1]["hand"][0]["id"] = 123456
        second["current"]["players"][1]["prize"][0]["id"] = 654321
        self.assertEqual(encode_observation(first).state_vector, encode_observation(second).state_vector)

    def test_visible_own_hand_and_play_card_are_encoded(self):
        encoded = encode_observation(observation())
        state = dict(zip(STATE_FEATURE_NAMES, encoded.state_vector))
        option = dict(zip(OPTION_FEATURE_NAMES, encoded.option_vectors[0]))
        self.assertEqual(900.0, state["self_hand_0_id"])
        self.assertEqual(10.0, option["card_id"])

        play = observation()
        play["select"]["option"] = [{"type": 7, "index": 0}]
        play_encoded = encode_observation(play)
        play_option = dict(zip(OPTION_FEATURE_NAMES, play_encoded.option_vectors[0]))
        self.assertEqual(900.0, play_option["card_id"])

    def test_attach_resolves_source_and_target_cards(self):
        data = observation()
        data["select"]["option"] = [{
            "type": 8, "area": 2, "index": 0, "inPlayArea": 4, "inPlayIndex": 0,
        }]
        option = dict(zip(OPTION_FEATURE_NAMES, encode_observation(data).option_vectors[0]))
        self.assertEqual(900.0, option["card_id"])
        self.assertEqual(10.0, option["target_card_id"])

    def test_observation_objects_are_supported(self):
        encoded = encode_observation(observation(as_objects=True))
        self.assertEqual(1, len(encoded.option_vectors))
        self.assertEqual(10.0, encoded.option_vectors[0][OPTION_FEATURE_NAMES.index("card_id")])

    def test_value_perspective_can_be_fixed_after_turn_passes(self):
        data = observation()
        data["current"]["yourIndex"] = 1
        encoded = encode_observation(data, perspective_seat=0)
        values = dict(zip(STATE_FEATURE_NAMES, encoded.state_vector))
        self.assertEqual(0.0, values["seat"])
        self.assertEqual(0.0, values["acting_is_self"])
        self.assertEqual(10.0, values["self_active_card_id"])
        self.assertEqual(30.0, values["opponent_active_card_id"])
        self.assertEqual(-1.0, values["self_hand_0_id"])


if __name__ == "__main__":
    unittest.main()
