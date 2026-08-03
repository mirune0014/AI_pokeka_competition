from __future__ import annotations

import copy
import unittest

import planner_deck_adaptation_v1 as v1
import planner_policy as core
import planner_runtime_model as runtime_model
import planner_v2_h1_unique_attach as v2
import test_v2_h1_unique_attach as fixtures


class V2Fix6ReviewFindingTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixtures.V2H1UniqueAttachTests(methodName="runTest")
        self.fx.setUp()

    def tearDown(self):
        self.fx.tearDown()

    def assert_deferred(self, returned, expected):
        self.assertIs(returned, expected)
        self.assertIsNone(v2.V2_TRANSACTION)
        self.assertIn(v2.TAG_DEFER, v2.LAST_V2_CONTINUITY_TRACE["reason_tags"])

    def assert_policy_snapshot_equal(self, expected):
        current = v2._policy_snapshot(fixtures.policy)
        self.assertEqual(current["delegate"]["parent"], expected["delegate"]["parent"])
        self.assertEqual(current["delegate"]["transaction"], expected["delegate"]["transaction"])
        self.assertEqual(current["delegate"]["duplicate_cache"], expected["delegate"]["duplicate_cache"])
        self.assertEqual(current["delegate"]["duplicate_order"], expected["delegate"]["duplicate_order"])
        self.assertEqual(current["delegate"]["trace_log"], expected["delegate"]["trace_log"])
        self.assertIs(current["delegate"]["latest_trace"], expected["delegate"]["latest_trace"])
        self.assertEqual(current["v1_transaction"], expected["v1_transaction"])
        self.assertEqual(current["v1_duplicates"], expected["v1_duplicates"])
        self.assertEqual(current["removed_rule_hits"], expected["removed_rule_hits"])
        self.assertIs(current["last_v1_trace"], expected["last_v1_trace"])
        self.assertEqual(current["compliance_block"], expected["compliance_block"])

    def test_post_call_v1_and_core_duplicate_owners_defer(self):
        for owner in ("v1", "core"):
            with self.subTest(owner=owner):
                v2.reset()
                v1.reset()
                self.fx.set_benign_v1_trace()
                core.INTEGRATED_TRANSACTION = None
                core.INTEGRATED_DUPLICATE_CACHE.clear()
                core._DUPLICATE_ORDER.clear()
                start = self.fx.start(5)
                raw = self.fx.raw(start)
                parsed = fixtures.policy.to_observation_class(raw)
                snapshot = runtime_model.public_snapshot(fixtures.policy, parsed)
                expected = [self.fx.attack_index(start)]

                def duplicate_delegate(_raw):
                    if owner == "v1":
                        v1.V1_DUPLICATES[snapshot.sha256] = (("POST",),)
                    else:
                        core.INTEGRATED_DUPLICATE_CACHE[snapshot.sha256] = (("POST",),)
                    return expected

                returned = v2.agent(fixtures.policy, duplicate_delegate, raw)
                self.assert_deferred(returned, expected)

    def test_post_call_parent_decision_duplicate_defer(self):
        start = self.fx.start(5)
        raw = self.fx.raw(start)
        expected = [self.fx.attack_index(start)]

        def duplicate_delegate(current_raw):
            parsed = fixtures.policy.to_observation_class(current_raw)
            fixtures.policy._last_decision_signature = fixtures.policy._decision_signature(
                parsed, current_raw
            )
            fixtures.policy._last_decision_action = tuple(expected)
            return expected

        returned = v2.agent(fixtures.policy, duplicate_delegate, raw)
        self.assert_deferred(returned, expected)

    def test_post_call_parent_prize_lane_duplicate_defer(self):
        start = self.fx.start(5)
        raw = self.fx.raw(start)
        expected = [self.fx.attack_index(start)]

        def duplicate_delegate(current_raw):
            raw_signature = fixtures.policy._two_prize_freeze_raw(current_raw)
            fixtures.policy._exact_prize_lane_remember(raw_signature, expected)
            return expected

        returned = v2.agent(fixtures.policy, duplicate_delegate, raw)
        self.assert_deferred(returned, expected)

    def test_stale_parent_duplicate_records_do_not_block(self):
        fixtures.policy._last_decision_signature = ("STALE",)
        fixtures.policy._last_decision_action = (2,)
        fixtures.policy._exact_prize_lane_duplicate.clear()
        fixtures.policy._exact_prize_lane_duplicate.update(
            raw_signature=("STALE",),
            action=(2,),
        )
        start = self.fx.start(5)
        self.fx.next_action = [self.fx.attack_index(start)]
        returned = self.fx.invoke(start)
        self.assertEqual(returned, [0])
        self.assertIsNotNone(v2.V2_TRANSACTION)
        self.assertEqual(
            v2.LAST_V2_CONTINUITY_TRACE["stage"], "ATTACH_DISPATCHED"
        )

    def test_attach_duplicate_hash_uses_retained_rollback_state(self):
        fixtures.policy.ability_used_dudunsparce = False
        start = self.fx.start(5)
        raw = self.fx.raw(start)
        expected = [self.fx.attack_index(start)]

        def mutating_probe(_raw):
            fixtures.policy.ability_used_dudunsparce = True
            return expected

        returned = v2.agent(fixtures.policy, mutating_probe, raw)
        self.assertEqual(returned, [0])
        self.assertFalse(fixtures.policy.ability_used_dudunsparce)
        retained = runtime_model.public_snapshot(
            fixtures.policy, fixtures.policy.to_observation_class(raw)
        )
        self.assertEqual(v2.V2_TRANSACTION["start_snapshot_hash"], retained.sha256)

        duplicate = copy.deepcopy(start)
        duplicate.select.option = list(reversed(duplicate.select.option))

        def forbidden_delegate(_raw):
            raise AssertionError("attach duplicate delegated")

        replay = v2.agent(
            fixtures.policy, forbidden_delegate, self.fx.raw(duplicate)
        )
        self.assertEqual(replay, [2])
        self.assertEqual(
            v2.LAST_V2_CONTINUITY_TRACE["stage"],
            "ATTACH_DUPLICATE_REBOUND",
        )

    def test_attack_duplicate_hash_uses_retained_call_state(self):
        fixtures.policy.ability_used_dudunsparce = False
        start = self.fx.start(5)
        self.fx.begin(start)
        attack_main = self.fx.post_attach_main(start)
        raw = self.fx.raw(attack_main)
        expected = [self.fx.attack_index(attack_main)]

        def mutating_delegate(_raw):
            fixtures.policy.ability_used_dudunsparce = True
            return expected

        returned = v2.agent(fixtures.policy, mutating_delegate, raw)
        self.assertIs(returned, expected)
        self.assertTrue(fixtures.policy.ability_used_dudunsparce)
        retained = runtime_model.public_snapshot(
            fixtures.policy, fixtures.policy.to_observation_class(raw)
        )
        self.assertEqual(
            v2.V2_TRANSACTION["attack_snapshot_hash"], retained.sha256
        )

        duplicate = copy.deepcopy(attack_main)
        duplicate.select.option = list(reversed(duplicate.select.option))

        def forbidden_delegate(_raw):
            raise AssertionError("attack duplicate delegated")

        replay = v2.agent(
            fixtures.policy, forbidden_delegate, self.fx.raw(duplicate)
        )
        self.assertEqual(replay, [1])
        self.assertEqual(
            v2.LAST_V2_CONTINUITY_TRACE["stage"],
            "ATTACK_DUPLICATE_REBOUND",
        )

    def test_telepath_empty_child_duplicate_replay_is_owned(self):
        start = self.fx.start(19)
        self.fx.begin(start)
        child = self.fx.telepath_child(start)
        self.assertEqual(self.fx.invoke(child), [])
        calls_before = len(self.fx.calls)
        self.assertEqual(self.fx.invoke(copy.deepcopy(child)), [])
        self.assertEqual(len(self.fx.calls), calls_before)
        self.assertEqual(
            v2.LAST_V2_CONTINUITY_TRACE["stage"],
            "TELEPATH_EMPTY_CHILD_DUPLICATE_REBOUND",
        )
        self.assertEqual(v2.V2_TRANSACTION["stage"], "await_telepath_main")

    def test_failed_attack_delegate_probe_rolls_back_all_policy_state(self):
        start = self.fx.start(5)
        self.fx.begin(start)
        attack_main = self.fx.post_attach_main(start)
        before = v2._policy_snapshot(fixtures.policy)

        def failed_probe(_raw):
            fixtures.policy.ability_used_dudunsparce = True
            core.INTEGRATED_TRANSACTION = {"probe": True}
            core.INTEGRATED_DUPLICATE_CACHE["PROBE"] = (("KEY",),)
            core._DUPLICATE_ORDER.append("PROBE")
            core.INTEGRATED_TRACE_LOG.append({"probe": True})
            core.INTEGRATED_LATEST_TRACE = {"probe": True}
            v1.V1_TRANSACTION = {"probe": True}
            v1.V1_DUPLICATES["PROBE"] = (("KEY",),)
            v1.REMOVED_RULE_HITS = [{"probe": True}]
            v1.LAST_V1_PACKAGE_TRACE = {"selected_rule": "PROBE", "reason_tags": []}
            v1.COMPLIANCE_BLOCK_TAG = "PROBE"
            return [self.fx.attack_index(attack_main)]

        returned = v2.agent(
            fixtures.policy, failed_probe, self.fx.raw(attack_main)
        )
        parsed = fixtures.policy.to_observation_class(self.fx.raw(attack_main))
        self.assertTrue(v1.model.action_is_valid(parsed, returned))
        self.fx.assert_fault()
        self.assert_policy_snapshot_equal(before)

    def test_post_attach_helper_exception_is_contained(self):
        start = self.fx.start(5)
        self.fx.begin(start)
        post = self.fx.post_attach_main(start)
        original = v2._attach_delta_exact

        def explode(*_args, **_kwargs):
            raise RuntimeError("post-attach helper failure")

        v2._attach_delta_exact = explode
        try:
            returned = self.fx.invoke(post)
        finally:
            v2._attach_delta_exact = original
        parsed = fixtures.policy.to_observation_class(self.fx.raw(post))
        self.assertTrue(v1.model.action_is_valid(parsed, returned))
        self.fx.assert_fault()
        self.assertEqual(
            v2.LAST_V2_CONTINUITY_TRACE["transaction_abort_reason"],
            "POST_ATTACH_EXCEPTION",
        )

    def test_completion_delegate_exception_is_contained_and_rolled_back(self):
        _, attack_main = self.fx.dispatch_basic()
        verify = self.fx.ko_verify(attack_main)
        before = v2._policy_snapshot(fixtures.policy)

        def exploding_completion(_raw):
            fixtures.policy.ability_used_fezandipiti = True
            core.INTEGRATED_TRACE_LOG.append({"completion": True})
            raise RuntimeError("completion delegation failure")

        returned = v2.agent(
            fixtures.policy, exploding_completion, self.fx.raw(verify)
        )
        parsed = fixtures.policy.to_observation_class(self.fx.raw(verify))
        self.assertTrue(v1.model.action_is_valid(parsed, returned))
        self.fx.assert_fault()
        self.assertEqual(
            v2.LAST_V2_CONTINUITY_TRACE["transaction_abort_reason"],
            "COMPLETION_DELEGATE_EXCEPTION",
        )
        self.assert_policy_snapshot_equal(before)


if __name__ == "__main__":
    unittest.main()