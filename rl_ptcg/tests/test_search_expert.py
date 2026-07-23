import unittest

from rl_ptcg.search_expert import SearchDecision, candidate_actions


class Item:
    def __init__(self, **values):
        self.__dict__.update(values)


class SearchExpertTests(unittest.TestCase):
    def test_search_decision_scenario_values_defaults_to_none(self):
        decision = SearchDecision([0], [0], False, "test", [], 0, 0)
        self.assertIsNone(decision.scenario_values)
        self.assertIsNone(decision.scenario_errors)

    def test_candidates_keep_baseline_and_exclude_optional_negative(self):
        observation = Item(select=Item(
            minCount=1, maxCount=2, option=[Item(), Item(), Item(), Item()]
        ))
        actions = candidate_actions(observation, [10, 9, 1, -100], [0, 1], top_options=4)
        self.assertEqual([0, 1], actions[0])
        self.assertIn([0], actions)
        self.assertFalse(any(3 in action and len(action) > 1 for action in actions))

    def test_single_select_enumerates_top_options(self):
        observation = {"select": {"minCount": 1, "maxCount": 1, "option": [{}, {}, {}]}}
        actions = candidate_actions(observation, [3, 2, 1], [0], top_options=3)
        self.assertEqual([[0], [1], [2]], actions)

    def test_complete_enumerates_all_counts_and_negative_options(self):
        observation = {"select": {"minCount": 1, "maxCount": 2, "option": [{}, {}, {}]}}
        actions = candidate_actions(
            observation, [10, -5, -20], [2], top_options=1, max_actions=1, mode="complete"
        )
        self.assertEqual([[2], [0], [1], [0, 1], [0, 2], [1, 2]], actions)

    def test_complete_mode_guard_raises(self):
        observation = {"select": {"minCount": 0, "maxCount": 3, "option": [{}, {}, {}, {}]}}
        with self.assertRaisesRegex(ValueError, "max_complete_actions"):
            candidate_actions(observation, [0, 0, 0, 0], [], mode="complete", max_complete_actions=10)


if __name__ == "__main__":
    unittest.main()
