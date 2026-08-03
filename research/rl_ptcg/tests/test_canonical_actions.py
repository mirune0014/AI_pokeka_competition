import copy
import unittest

from research.rl_ptcg.canonical_actions import (
    CanonicalTransaction,
    canonicalize_option,
    canonicalize_prompt_action,
    resolve_prompt_action,
)


class Item:
    def __init__(self, **values):
        self.__dict__.update(values)


def observation(*, seat=0, as_objects=False):
    players = [
        {
            "hand": [{"id": 101}, {"id": 102}],
            "active": [{"id": 201, "energyCards": [{"id": 301}], "tools": [{"id": 401}]}],
            "bench": [{"id": 202}], "discard": [{"id": 501}],
        },
        {
            "hand": [{"id": 901}], "active": [{"id": 601}],
            "bench": [{"id": 602}], "discard": [{"id": 701}],
        },
    ]
    if seat == 1:
        players.reverse()
    data = {
        "current": {"yourIndex": seat, "players": players, "stadium": [{"id": 801}]},
        "select": {
            "context": "ATTACH", "minCount": 1, "maxCount": 2,
            "remainEnergyCost": 1, "remainDamageCounter": 3, "effect": {"id": 777},
            "option": [
                {"type": "ATTACH", "area": 2, "index": 0, "playerIndex": seat,
                 "inPlayArea": 4, "inPlayIndex": 0, "inPlayPlayerIndex": seat, "serial": 11},
                {"type": "TARGET", "area": 5, "index": 0, "playerIndex": 1 - seat,
                 "serial": 12, "number": 2, "count": 1, "specialConditionType": "POISON"},
            ],
        },
    }
    if not as_objects:
        return data
    return Item(current=Item(**data["current"]), select=Item(**data["select"]))


class CanonicalActionsTests(unittest.TestCase):
    def test_option_ignores_serial_ordinal_and_zone_indices_and_resolves_public_cards(self):
        first = observation()
        second = copy.deepcopy(first)
        second["select"]["option"][0].update({"index": 1, "serial": 999})
        second["current"]["players"][0]["hand"].reverse()
        canonical = canonicalize_option(first, first["select"]["option"][0])
        changed = canonicalize_option(second, second["select"]["option"][0])
        self.assertEqual(canonical, changed)
        payload = canonical.to_dict()
        self.assertEqual(101, payload["source_card_id"])
        self.assertEqual(201, payload["target_card_id"])
        self.assertEqual("hand", payload["source_zone"])
        self.assertEqual("self", payload["source_relation"])
        self.assertEqual({"damage_counter": 3, "energy": 1}, payload["remaining_cost"])
        self.assertEqual(777, payload["effect_source_id"])
        self.assertNotIn("serial", str(payload))
        self.assertNotIn("index", payload)

    def test_player_relation_normalizes_under_seat_swap_and_objects_work(self):
        first = canonicalize_option(observation(seat=0), observation(seat=0)["select"]["option"][1])
        swapped = observation(seat=1, as_objects=True)
        second = canonicalize_option(swapped, swapped.select.option[1])
        self.assertEqual("opponent", first.source_relation)
        self.assertEqual(first, second)
        self.assertEqual(602, second.source_card_id)

    def test_multiselect_duplicates_are_order_invariant_and_hash_stable(self):
        data = observation()
        duplicate = copy.deepcopy(data["select"]["option"][0])
        duplicate["serial"] = 1000
        data["select"]["option"] = [duplicate, data["select"]["option"][0], data["select"]["option"][1]]
        first = canonicalize_prompt_action(data, [0, 1])
        reordered = copy.deepcopy(data)
        reordered["select"]["option"].reverse()
        second = canonicalize_prompt_action(reordered, [1, 2])
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.stable_id, second.stable_id)
        self.assertEqual(2, len(first.selections))

    def test_round_trip_consumes_duplicates_after_option_reordering(self):
        data = observation()
        data["select"]["option"] = [copy.deepcopy(data["select"]["option"][0]) for _ in range(2)]
        action = canonicalize_prompt_action(data, [0, 1])
        changed = copy.deepcopy(data)
        changed["select"]["option"].reverse()
        self.assertEqual([0, 1], resolve_prompt_action(changed, action))

    def test_missing_semantic_action_and_invalid_size_are_clear_failures(self):
        data = observation()
        action = canonicalize_prompt_action(data, [0])
        data["select"]["option"] = [data["select"]["option"][1]]
        with self.assertRaisesRegex(ValueError, "matching legal option"):
            resolve_prompt_action(data, action)
        with self.assertRaisesRegex(ValueError, "invalid action size"):
            canonicalize_prompt_action(observation(), [])

    def test_transaction_is_immutable_and_composes_prompt_steps(self):
        step = canonicalize_prompt_action(observation(), [0])
        transaction = CanonicalTransaction()
        composed = transaction.append(step)
        self.assertEqual((), transaction.steps)
        self.assertEqual((step,), composed.steps)
        self.assertNotEqual(transaction.stable_id, composed.stable_id)


if __name__ == "__main__":
    unittest.main()
