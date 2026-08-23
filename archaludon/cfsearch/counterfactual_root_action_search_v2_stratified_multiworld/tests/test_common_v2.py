import unittest

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from common_v2 import (  # noqa: E402
    action_transformation,
    energy_target_eligibility,
    public_context_tags,
    validate_public_zone_contract,
)


def observation():
    return {
        "select": {
            "context": 0,
            "type": 0,
            "option": [
                {"type": 8, "index": 8, "inPlayArea": 0, "inPlayIndex": 0},
                {"type": 8, "index": 8, "inPlayArea": 1, "inPlayIndex": 0},
                {"type": 14, "index": 253},
                {"type": 7, "index": 24},
            ],
        },
        "current": {
            "yourIndex": 0,
            "supporterPlayed": False,
            "players": [
                {"active": [{"id": 24, "serial": 1, "hp": 120, "maxHp": 130}], "bench": [], "deckCount": 20, "handCount": 4, "prize": [1, 2]},
                {"active": [{"id": 84, "serial": 2, "hp": 200, "maxHp": 220}], "bench": [], "deckCount": 4, "handCount": 5, "prize": [3, 4]},
            ],
        },
    }


class CommonV2Tests(unittest.TestCase):
    def test_energy_requires_two_distinct_targets(self):
        result = energy_target_eligibility(observation())
        self.assertTrue(result["eligible"])
        self.assertEqual(result["eligible_energy_serials"], ["8"])

    def test_energy_requires_main_and_unattached(self):
        obs = observation()
        obs["select"]["context"] = 1
        self.assertFalse(energy_target_eligibility(obs)["eligible"])
        obs = observation()
        obs["current"]["energyAttached"] = True
        self.assertFalse(energy_target_eligibility(obs)["eligible"])

    def test_transformation_and_public_tags(self):
        obs = observation()
        self.assertEqual(action_transformation(obs, [2], [3]), "T1_ATTACK_TO_DEVELOP")
        tags = public_context_tags(obs)
        self.assertIn("C_BENCH_EMPTY", tags)
        self.assertIn("C_ACTIVE_DAMAGED", tags)
        self.assertIn("C_MULTI_ATTACH_TARGET", tags)

    def test_formal_world_is_fail_closed_without_zone_mirrors(self):
        result = validate_public_zone_contract(observation(), {"your_deck": list(range(1, 61))})
        self.assertFalse(result["formal_eligible"])
        self.assertTrue(any(item.startswith("world.") for item in result["missing_public_fields"]))


if __name__ == "__main__":
    unittest.main()
