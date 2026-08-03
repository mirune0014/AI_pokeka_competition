"""Regression certificate that the superseded broad C3 action path is inert."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from unittest import mock

import _cumulative_parent as parent
import main
import planner_deck_adaptation_v1 as deck_v1
import planner_policy as core
import planner_public_damage_continuity as damage
import planner_public_survival_bench0 as rule


REPLAY = Path(r"C:\Users\amuam\Downloads\88843743.json")
INITIAL_PARENT_STATE = core.parent_state_snapshot(parent)


class SupersededBroadC3RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        replay = json.loads(REPLAY.read_text(encoding="utf-8"))
        cls.obs = {
            index: replay["steps"][index][1]["observation"]
            for index in (22, 23, 24, 27)
        }

    def setUp(self):
        core.restore_parent_state(parent, INITIAL_PARENT_STATE)
        core.reset_integrated_state()
        deck_v1.reset()
        deck_v1.REMOVED_RULE_HITS = []
        deck_v1.COMPLIANCE_BLOCK_TAG = None
        rule.reset()
        main.LAST_V0_PORT_TRACE = None
        main.LAST_V1_PACKAGE_TRACE = None
        main.LAST_STAGED_POLICY_TRACE = None

    def test_deck_handshake_resets_outer_and_parent_state(self):
        rule.C3_TRANSACTION = {"stale": True}
        core.INTEGRATED_TRANSACTION = {"kind": "stale"}
        deck_v1.V1_TRANSACTION = {"rule": "stale"}
        deck = main.agent({"select": None, "current": None})
        self.assertEqual(deck, rule.exact_deck())
        self.assertEqual(len(deck), 60)
        self.assertIsNone(rule.C3_TRANSACTION)
        self.assertIsNone(core.INTEGRATED_TRANSACTION)
        self.assertIsNone(deck_v1.V1_TRANSACTION)

    def test_preceding_parent_actions_remain_unchanged(self):
        main.agent({"select": None, "current": None})
        actions = [
            main.agent(copy.deepcopy(self.obs[index]))
            for index in (22, 23, 24)
        ]
        self.assertEqual(actions, [[2], [0], [3]])
        self.assertIsNone(rule.C3_TRANSACTION)

    def test_observed_parent_attack_is_exact_and_broad_evaluator_unused(self):
        main.agent({"select": None, "current": None})
        for index in (22, 23, 24):
            main.agent(copy.deepcopy(self.obs[index]))
        observation = copy.deepcopy(self.obs[27])
        with mock.patch.object(
            damage,
            "evaluate_survival_decision",
            side_effect=AssertionError("broad C3 evaluator must be inert"),
        ):
            action = main.agent(observation)
        self.assertEqual(action, [3])
        self.assertEqual(
            damage.semantic_action(observation, action),
            ("ATTACK", 1071),
        )
        self.assertIsNone(rule.C3_TRANSACTION)
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["guard_failure"],
            "PARENT_SEMANTIC_NOT_END",
        )
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["rule_version"],
            rule.RULE_VERSION,
        )
        self.assertTrue(
            main.LAST_STAGED_POLICY_TRACE["action_identity"][
                "returned_parent_object_unchanged"
            ]
        )


if __name__ == "__main__":
    unittest.main()
