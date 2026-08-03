from __future__ import annotations

import copy
import unittest

import planner_deck_adaptation_v1 as v1
import planner_policy as core
import planner_runtime_model as runtime_model
import planner_v2_h1_unique_attach as v2
import test_v2_h1_unique_attach as fixtures


class V2Fix7FinalReviewTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixtures.V2H1UniqueAttachTests(methodName="runTest")
        self.fx.setUp()

    def tearDown(self):
        self.fx.tearDown()

    def assert_fault(self, reason):
        self.assertIsNone(v2.V2_TRANSACTION)
        trace = v2.LAST_V2_CONTINUITY_TRACE
        self.assertEqual(trace["transaction_outcome"], "FAULT_ABORT")
        self.assertTrue(trace["irreversible_abort_fault"])
        self.assertEqual(trace["transaction_abort_reason"], reason)

    def assert_valid(self, obs, action):
        parsed = fixtures.policy.to_observation_class(self.fx.raw(obs))
        self.assertTrue(v1.model.action_is_valid(parsed, action))

    def test_basic_post_attach_unrecoverable_rolls_back_and_faults(self):
        start = self.fx.start(5)
        self.fx.begin(start)
        post = self.fx.post_attach_main(start)
        before = v2._policy_snapshot(fixtures.policy)

        def unrecoverable(_raw):
            fixtures.policy.ability_used_dudunsparce = True
            core.INTEGRATED_TRACE_LOG.append({"basic_uof": True})
            raise v1.UnrecoverableObservationFault("BASIC_UOF")

        returned = v2.agent(fixtures.policy, unrecoverable, self.fx.raw(post))
        self.assert_valid(post, returned)
        self.assert_fault("POST_ATTACH_UNRECOVERABLE")
        self.assertEqual(v2._policy_snapshot(fixtures.policy), before)

    def test_telepath_post_attach_unrecoverable_rolls_back_and_faults(self):
        start = self.fx.start(19)
        self.fx.begin(start)
        child = self.fx.telepath_child(start)
        self.assertEqual(self.fx.invoke(child), [])
        main = self.fx.after_telepath_child(child)
        before = v2._policy_snapshot(fixtures.policy)

        def unrecoverable(_raw):
            fixtures.policy.ability_used_fezandipiti = True
            v1.V1_DUPLICATES["TELEPATH_UOF"] = (("KEY",),)
            raise v1.UnrecoverableObservationFault("TELEPATH_UOF")

        returned = v2.agent(fixtures.policy, unrecoverable, self.fx.raw(main))
        self.assert_valid(main, returned)
        self.assert_fault("POST_ATTACH_UNRECOVERABLE")
        self.assertEqual(v2._policy_snapshot(fixtures.policy), before)

    def test_already_aborted_unrecoverable_is_not_double_handled(self):
        start = self.fx.start(5)
        self.fx.begin(start)
        malformed = copy.deepcopy(start)
        malformed.select.minCount = 2
        malformed.select.maxCount = 1
        with self.assertRaisesRegex(
            v1.UnrecoverableObservationFault,
            "V2_UNRECOVERABLE_IRREVERSIBLE_FAULT_ACTION",
        ):
            self.fx.invoke(malformed)
        self.assertIsNone(v2.V2_TRANSACTION)
        trace = v2.LAST_V2_CONTINUITY_TRACE
        self.assertEqual(trace["transaction_abort_reason"], "BASIC_ATTACH_DELTA_MISMATCH")
        self.assertNotEqual(trace["transaction_abort_reason"], "POST_ATTACH_UNRECOVERABLE")

    def test_attach_duplicate_exact_and_semantic_reorder_pass(self):
        start = self.fx.start(5)
        self.fx.begin(start)
        calls_before = len(self.fx.calls)
        self.assertEqual(self.fx.invoke(copy.deepcopy(start)), [0])
        self.assertEqual(len(self.fx.calls), calls_before)

        reordered = copy.deepcopy(start)
        reordered.select.option = list(reversed(reordered.select.option))
        raw = self.fx.raw(reordered)
        snapshot = runtime_model.public_snapshot(
            fixtures.policy, fixtures.policy.to_observation_class(raw)
        )
        self.assertEqual(snapshot.sha256, v2.V2_TRANSACTION["start_snapshot_hash"])
        self.assertEqual(v2.agent(fixtures.policy, self.fx.delegate, raw), [2])
        self.assertEqual(len(self.fx.calls), calls_before)
        self.assertEqual(
            v2.LAST_V2_CONTINUITY_TRACE["stage"], "ATTACH_DUPLICATE_REBOUND"
        )

    def test_attach_duplicate_deck_none_to_empty_faults(self):
        start = self.fx.start(5)
        self.fx.begin(start)
        malformed = copy.deepcopy(start)
        malformed.select.deck = []
        raw = self.fx.raw(malformed)
        snapshot = runtime_model.public_snapshot(
            fixtures.policy, fixtures.policy.to_observation_class(raw)
        )
        self.assertEqual(snapshot.sha256, v2.V2_TRANSACTION["start_snapshot_hash"])
        returned = v2.agent(fixtures.policy, self.fx.delegate, raw)
        self.assert_valid(malformed, returned)
        self.assert_fault("ATTACH_DUPLICATE_PUBLIC_MISMATCH")

    def test_telepath_duplicate_exact_and_semantic_reorder_pass(self):
        start = self.fx.start(19)
        self.fx.begin(start)
        child = self.fx.telepath_child(start)
        self.assertEqual(self.fx.invoke(child), [])
        calls_before = len(self.fx.calls)
        self.assertEqual(self.fx.invoke(copy.deepcopy(child)), [])
        self.assertEqual(len(self.fx.calls), calls_before)

        reordered = copy.deepcopy(child)
        reordered.select.deck = list(reversed(reordered.select.deck))
        reordered.select.option = list(reversed(reordered.select.option))
        for index, option in enumerate(reordered.select.option):
            option.index = index
        raw = self.fx.raw(reordered)
        snapshot = runtime_model.public_snapshot(
            fixtures.policy, fixtures.policy.to_observation_class(raw)
        )
        self.assertEqual(
            snapshot.sha256,
            v2.V2_TRANSACTION["telepath_child_snapshot_hash"],
        )
        self.assertEqual(v2.agent(fixtures.policy, self.fx.delegate, raw), [])
        self.assertEqual(len(self.fx.calls), calls_before)
        self.assertEqual(
            v2.LAST_V2_CONTINUITY_TRACE["stage"],
            "TELEPATH_EMPTY_CHILD_DUPLICATE_REBOUND",
        )

    def test_telepath_duplicate_extra_child_deck_card_faults(self):
        start = self.fx.start(19)
        self.fx.begin(start)
        child = self.fx.telepath_child(start)
        self.assertEqual(self.fx.invoke(child), [])
        malformed = copy.deepcopy(child)
        malformed.select.deck.append(self.fx.card(741, 0, 8999))
        raw = self.fx.raw(malformed)
        snapshot = runtime_model.public_snapshot(
            fixtures.policy, fixtures.policy.to_observation_class(raw)
        )
        self.assertEqual(
            snapshot.sha256,
            v2.V2_TRANSACTION["telepath_child_snapshot_hash"],
        )
        returned = v2.agent(fixtures.policy, self.fx.delegate, raw)
        self.assert_valid(malformed, returned)
        self.assert_fault("TELEPATH_CHILD_DUPLICATE_INVALID")

    def test_attack_duplicate_exact_and_semantic_reorder_pass(self):
        _, attack_main = self.fx.dispatch_basic()
        calls_before = len(self.fx.calls)
        expected = [self.fx.attack_index(attack_main)]
        self.assertEqual(self.fx.invoke(copy.deepcopy(attack_main)), expected)
        self.assertEqual(len(self.fx.calls), calls_before)

        reordered = copy.deepcopy(attack_main)
        reordered.select.option = list(reversed(reordered.select.option))
        raw = self.fx.raw(reordered)
        snapshot = runtime_model.public_snapshot(
            fixtures.policy, fixtures.policy.to_observation_class(raw)
        )
        self.assertEqual(snapshot.sha256, v2.V2_TRANSACTION["attack_snapshot_hash"])
        self.assertEqual(v2.agent(fixtures.policy, self.fx.delegate, raw), [1])
        self.assertEqual(len(self.fx.calls), calls_before)
        self.assertEqual(
            v2.LAST_V2_CONTINUITY_TRACE["stage"], "ATTACK_DUPLICATE_REBOUND"
        )

    def test_attack_duplicate_deck_none_to_empty_faults(self):
        _, attack_main = self.fx.dispatch_basic()
        malformed = copy.deepcopy(attack_main)
        malformed.select.deck = []
        raw = self.fx.raw(malformed)
        snapshot = runtime_model.public_snapshot(
            fixtures.policy, fixtures.policy.to_observation_class(raw)
        )
        self.assertEqual(snapshot.sha256, v2.V2_TRANSACTION["attack_snapshot_hash"])
        returned = v2.agent(fixtures.policy, self.fx.delegate, raw)
        self.assert_valid(malformed, returned)
        self.assert_fault("ATTACK_DUPLICATE_PUBLIC_MISMATCH")

    def test_completion_delegate_sees_global_transaction_cleared(self):
        _, attack_main = self.fx.dispatch_basic()
        verify = self.fx.ko_verify(attack_main)
        expected = [0]

        def completion(_raw):
            self.assertIsNone(v2.V2_TRANSACTION)
            return expected

        returned = v2.agent(fixtures.policy, completion, self.fx.raw(verify))
        self.assertIs(returned, expected)
        self.assertIsNone(v2.V2_TRANSACTION)
        self.assertEqual(
            v2.LAST_V2_CONTINUITY_TRACE["transaction_outcome"], "COMPLETE"
        )
        self.assertTrue(v2.LAST_V2_CONTINUITY_TRACE["KO_resolved"])

    def test_completion_exception_with_cleared_global_rolls_back_and_faults(self):
        _, attack_main = self.fx.dispatch_basic()
        verify = self.fx.ko_verify(attack_main)
        before = v2._policy_snapshot(fixtures.policy)

        def completion(_raw):
            self.assertIsNone(v2.V2_TRANSACTION)
            fixtures.policy.ability_used_fezandipiti = True
            core.INTEGRATED_TRACE_LOG.append({"completion": True})
            raise RuntimeError("completion failure")

        returned = v2.agent(fixtures.policy, completion, self.fx.raw(verify))
        self.assert_valid(verify, returned)
        self.assert_fault("COMPLETION_DELEGATE_EXCEPTION")
        self.assertEqual(v2._policy_snapshot(fixtures.policy), before)


if __name__ == "__main__":
    unittest.main()