from __future__ import annotations

import copy
import unittest

import planner_deck_adaptation_v1 as v1
import planner_policy as core
import planner_v2_h1_unique_attach as v2
import test_v2_h1_unique_attach as fixtures


class V2ProbeRollbackTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixtures.V2H1UniqueAttachTests(methodName="runTest")
        self.fx.setUp()

    def tearDown(self):
        self.fx.tearDown()

    def test_firing_rolls_back_every_v1_probe_mutable_surface(self):
        start = self.fx.start(5)
        raw = self.fx.raw(start)
        attack = [self.fx.attack_index(start)]
        parent = self.fx.parent_state
        before_parent = core.parent_state_snapshot(fixtures.policy)
        before_transaction = copy.deepcopy(core.INTEGRATED_TRANSACTION)
        before_duplicates = copy.deepcopy(core.INTEGRATED_DUPLICATE_CACHE)
        before_order = list(core._DUPLICATE_ORDER)
        before_log = copy.deepcopy(core.INTEGRATED_TRACE_LOG)
        before_latest = core.INTEGRATED_LATEST_TRACE
        before_v1_transaction = copy.deepcopy(v1.V1_TRANSACTION)
        before_v1_duplicates = copy.deepcopy(v1.V1_DUPLICATES)
        before_removed = copy.deepcopy(v1.REMOVED_RULE_HITS)
        before_trace = v1.LAST_V1_PACKAGE_TRACE
        before_compliance = v1.COMPLIANCE_BLOCK_TAG

        def mutating_v1_probe(_raw):
            fixtures.policy.ability_used_dudunsparce = True
            core.INTEGRATED_TRACE_LOG.append({"probe": True})
            core.INTEGRATED_LATEST_TRACE = {"probe": True}
            core._DUPLICATE_ORDER.append("UNRELATED")
            v1.V1_DUPLICATES["UNRELATED"] = (("KEY",),)
            v1.REMOVED_RULE_HITS = [{"probe": True}]
            v1.COMPLIANCE_BLOCK_TAG = "PROBE"
            v1.LAST_V1_PACKAGE_TRACE = {
                "public_snapshot_hash": None,
                "context": 0,
                "selected_action": attack,
                "selected_rule": None,
                "reason_tags": [
                    "CURRENT_EXACT_NONTERMINAL_KO_PRESERVED",
                    "V0_FALLBACK",
                ],
                "added_rule_hits": [],
                "removed_rule_hit_status": "KNOWN",
                "removed_rule_hits": [],
            }
            return attack

        returned = v2.agent(fixtures.policy, mutating_v1_probe, raw)
        self.assertEqual(returned, [0])
        self.assertIsNotNone(v2.V2_TRANSACTION)
        self.assertEqual(
            core.parent_state_snapshot(fixtures.policy), before_parent
        )
        self.assertEqual(core.INTEGRATED_TRANSACTION, before_transaction)
        self.assertEqual(
            core.INTEGRATED_DUPLICATE_CACHE, before_duplicates
        )
        self.assertEqual(core._DUPLICATE_ORDER, before_order)
        self.assertEqual(core.INTEGRATED_TRACE_LOG, before_log)
        self.assertIs(core.INTEGRATED_LATEST_TRACE, before_latest)
        self.assertEqual(v1.V1_TRANSACTION, before_v1_transaction)
        self.assertEqual(v1.V1_DUPLICATES, before_v1_duplicates)
        self.assertEqual(v1.REMOVED_RULE_HITS, before_removed)
        self.assertIs(v1.LAST_V1_PACKAGE_TRACE, before_trace)
        self.assertEqual(v1.COMPLIANCE_BLOCK_TAG, before_compliance)
        self.assertEqual(parent, self.fx.parent_state)


if __name__ == "__main__":
    unittest.main()
