from __future__ import annotations

import copy
import unittest

import planner_deck_adaptation_v1 as v1
import planner_policy as core
import planner_runtime_model as runtime_model
import planner_v2_h1_unique_attach as v2
import test_v2_h1_unique_attach as fixtures


class V2Fix8ActiveOwnerGateTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixtures.V2H1UniqueAttachTests(methodName="runTest")
        self.fx.setUp()

    def tearDown(self):
        self.fx.tearDown()

    def assert_owner_fault(self):
        self.assertIsNone(v2.V2_TRANSACTION)
        trace = v2.LAST_V2_CONTINUITY_TRACE
        self.assertEqual(trace["stage"], "FAULT_ABORT")
        self.assertEqual(trace["transaction_outcome"], "FAULT_ABORT")
        self.assertTrue(trace["irreversible_abort_fault"])
        self.assertEqual(
            trace["transaction_abort_reason"], "NEW_V1_OWNER_DURING_V2"
        )
        self.assertNotIn(
            trace["stage"],
            (
                "ATTACH_DUPLICATE_REBOUND",
                "TELEPATH_EMPTY_CHILD_DUPLICATE_REBOUND",
                "ATTACK_DUPLICATE_REBOUND",
            ),
        )

    def test_basic_attach_duplicate_with_current_v1_cache_faults_first(self):
        start = self.fx.start(5)
        self.fx.begin(start)
        raw = self.fx.raw(copy.deepcopy(start))
        parsed = fixtures.policy.to_observation_class(raw)
        snapshot = runtime_model.public_snapshot(fixtures.policy, parsed)
        self.assertEqual(snapshot.sha256, v2.V2_TRANSACTION["start_snapshot_hash"])
        v1.V1_DUPLICATES[snapshot.sha256] = (("CURRENT_V1_OWNER",),)
        calls_before = len(self.fx.calls)

        returned = v2.agent(fixtures.policy, self.fx.delegate, raw)
        self.assertTrue(v1.model.action_is_valid(parsed, returned))
        self.assertEqual(len(self.fx.calls), calls_before)
        self.assert_owner_fault()

    def test_telepath_child_with_current_core_cache_faults_before_stage(self):
        start = self.fx.start(19)
        self.fx.begin(start)
        child = self.fx.telepath_child(start)
        raw = self.fx.raw(child)
        parsed = fixtures.policy.to_observation_class(raw)
        snapshot = runtime_model.public_snapshot(fixtures.policy, parsed)
        core.INTEGRATED_DUPLICATE_CACHE[snapshot.sha256] = (
            ("CURRENT_CORE_OWNER",),
        )
        calls_before = len(self.fx.calls)

        returned = v2.agent(fixtures.policy, self.fx.delegate, raw)
        self.assertTrue(v1.model.action_is_valid(parsed, returned))
        self.assertEqual(len(self.fx.calls), calls_before)
        self.assert_owner_fault()

    def test_attack_duplicate_with_current_parent_generic_cache_faults_first(self):
        _, attack_main = self.fx.dispatch_basic()
        raw = self.fx.raw(copy.deepcopy(attack_main))
        parsed = fixtures.policy.to_observation_class(raw)
        fixtures.policy._last_decision_signature = fixtures.policy._decision_signature(
            parsed, raw
        )
        fixtures.policy._last_decision_action = (
            self.fx.attack_index(attack_main),
        )
        calls_before = len(self.fx.calls)

        returned = v2.agent(fixtures.policy, self.fx.delegate, raw)
        self.assertTrue(v1.model.action_is_valid(parsed, returned))
        self.assertEqual(len(self.fx.calls), calls_before)
        self.assert_owner_fault()

    def test_attack_duplicate_with_current_exact_prize_cache_faults_first(self):
        _, attack_main = self.fx.dispatch_basic()
        raw = self.fx.raw(copy.deepcopy(attack_main))
        parsed = fixtures.policy.to_observation_class(raw)
        action = [self.fx.attack_index(attack_main)]
        raw_signature = fixtures.policy._two_prize_freeze_raw(raw)
        fixtures.policy._exact_prize_lane_remember(raw_signature, action)
        self.assertEqual(
            fixtures.policy._exact_prize_lane_duplicate_action(raw_signature),
            action,
        )
        calls_before = len(self.fx.calls)

        returned = v2.agent(fixtures.policy, self.fx.delegate, raw)
        self.assertTrue(v1.model.action_is_valid(parsed, returned))
        self.assertEqual(len(self.fx.calls), calls_before)
        self.assert_owner_fault()

    def test_stale_parent_duplicate_records_do_not_block_attack_replay(self):
        _, attack_main = self.fx.dispatch_basic()
        raw = self.fx.raw(copy.deepcopy(attack_main))
        parsed = fixtures.policy.to_observation_class(raw)
        fixtures.policy._last_decision_signature = ("STALE",)
        fixtures.policy._last_decision_action = (1,)
        fixtures.policy._exact_prize_lane_duplicate.clear()
        fixtures.policy._exact_prize_lane_duplicate.update(
            raw_signature=("STALE",),
            action=(1,),
        )
        calls_before = len(self.fx.calls)

        returned = v2.agent(fixtures.policy, self.fx.delegate, raw)
        self.assertEqual(returned, [self.fx.attack_index(attack_main)])
        self.assertEqual(len(self.fx.calls), calls_before)
        self.assertIsNotNone(v2.V2_TRANSACTION)
        self.assertEqual(
            v2.LAST_V2_CONTINUITY_TRACE["stage"],
            "ATTACK_DUPLICATE_REBOUND",
        )


if __name__ == "__main__":
    unittest.main()