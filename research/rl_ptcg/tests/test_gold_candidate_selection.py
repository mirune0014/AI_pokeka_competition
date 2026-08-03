import json
import math
import unittest

from research.rl_ptcg.gold_candidate_selection import _incremental_gold


class GoldCandidateSelectionTests(unittest.TestCase):
    def test_incremental_gold_requires_exactly_one_new_action(self):
        state = {
            "gold_incremental": True,
            "candidate_sets": {
                "rule_diverse": ["a", "b"],
                "rule_plus_gold": ["a", "b", "g"],
            },
        }
        self.assertEqual("g", _incremental_gold(state))
        state["candidate_sets"]["rule_plus_gold"].append("g2")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            _incremental_gold(state)


if __name__ == "__main__":
    unittest.main()
