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
import planner_public_survival_bench0 as survival
import planner_runtime_model as runtime_model


REPLAY = Path(r"C:\Users\amuam\Downloads\88843743.json")
INITIAL_PARENT_STATE = core.parent_state_snapshot(parent)


class PublicSurvivalBench0Fix5Tests(unittest.TestCase):
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
        survival.reset()
        main.LAST_V0_PORT_TRACE = None
        main.LAST_V1_PACKAGE_TRACE = None
        main.LAST_STAGED_POLICY_TRACE = None

    def prime_to_obs27(self):
        deck = main.agent({"select": None, "current": None})
        self.assertEqual(len(deck), 60)
        actions = [
            main.agent(copy.deepcopy(self.obs[index]))
            for index in (22, 23, 24)
        ]
        self.assertEqual(actions, [[2], [0], [3]])

    def arm_obs27(self, observation=None):
        self.prime_to_obs27()
        obs = copy.deepcopy(observation or self.obs[27])
        action = main.agent(obs)
        self.assertEqual(action, [2])
        self.assertIsNotNone(survival.C3_TRANSACTION)
        return obs, action

    def post_basic_observation(self, original=None, *, reorder=True):
        obs = copy.deepcopy(original or self.obs[27])
        mine = obs["current"]["players"][1]
        selected = mine["hand"].pop(5)
        self.assertEqual((selected["id"], selected["serial"]), (343, 81))
        mine["handCount"] -= 1
        mine["bench"] = [
            {
                "appearThisTurn": True,
                "energies": [],
                "energyCards": [],
                "hp": 80,
                "id": 343,
                "maxHp": 80,
                "playerIndex": 1,
                "preEvolution": [],
                "serial": 81,
                "tools": [],
            }
        ]
        obs["current"]["turnActionCount"] += 1
        obs["logs"] = [
            {"cardId": 343, "playerIndex": 1, "serial": 81, "type": 10}
        ]
        obs["select"]["option"] = (
            [{"type": 14}, {"attackId": 1071, "type": 13}]
            if reorder
            else [{"attackId": 1071, "type": 13}, {"type": 14}]
        )
        return obs

    def test_deck_callback_is_exact_60_and_resets_c3(self):
        survival.C3_TRANSACTION = {"stage": "stale"}
        survival.PUBLIC_LEDGER["ambiguous"] = True
        deck = main.agent({"select": None, "current": None})
        self.assertEqual(deck, survival.exact_deck())
        self.assertEqual(len(deck), 60)
        self.assertIsNone(survival.C3_TRANSACTION)
        self.assertFalse(survival.PUBLIC_LEDGER["ambiguous"])
        self.assertFalse(survival.PUBLIC_LEDGER["boundary_certified"])

    def test_deck_callback_resets_complete_delegate_boundary_state(self):
        core.INTEGRATED_TRANSACTION = {"kind": "stale"}
        core.INTEGRATED_DUPLICATE_CACHE["stale"] = (("END",),)
        core._DUPLICATE_ORDER.append("stale")
        core.INTEGRATED_TRACE_LOG.append({"stale": True})
        core.INTEGRATED_LATEST_TRACE = {"stale": True}
        deck_v1.V1_TRANSACTION = {"rule": "stale"}
        deck_v1.V1_DUPLICATES["stale"] = (("END",),)
        deck_v1.REMOVED_RULE_HITS = [{"stale": True}]
        deck_v1.COMPLIANCE_BLOCK_TAG = "stale"
        parent._hilda_source_latch["stale"] = True
        parent._exact_prize_lane_duplicate["stale"] = True
        parent._last_decision_signature = ("stale",)
        main.LAST_STAGED_POLICY_TRACE = {"stale": True}
        deck = main.agent({"select": None, "current": None})
        self.assertEqual(deck, survival.exact_deck())
        self.assertIsNone(core.INTEGRATED_TRANSACTION)
        self.assertEqual(core.INTEGRATED_DUPLICATE_CACHE, {})
        self.assertEqual(core._DUPLICATE_ORDER, [])
        self.assertEqual(core.INTEGRATED_TRACE_LOG, [])
        self.assertIsNone(core.INTEGRATED_LATEST_TRACE)
        self.assertIsNone(deck_v1.V1_TRANSACTION)
        self.assertEqual(deck_v1.V1_DUPLICATES, {})
        self.assertEqual(deck_v1.REMOVED_RULE_HITS, [])
        self.assertIsNone(deck_v1.COMPLIANCE_BLOCK_TAG)
        snapshot = core.parent_state_snapshot(parent)
        for name, value in snapshot.items():
            if name == "pre_turn":
                self.assertEqual(value, 0)
            elif isinstance(value, (dict, list)):
                self.assertFalse(value)
            elif isinstance(value, bool):
                self.assertFalse(value)
            else:
                self.assertIsNone(value)
        self.assertIsNone(main.LAST_STAGED_POLICY_TRACE)

    def test_exact_episode_four_observations(self):
        self.prime_to_obs27()
        action = main.agent(copy.deepcopy(self.obs[27]))
        self.assertEqual(action, [2])
        trace = main.LAST_STAGED_POLICY_TRACE
        self.assertEqual(trace["rule_version"], damage.RULE_VERSION)
        self.assertEqual(trace["transaction_stage"], "ARMED")
        self.assertEqual(
            (
                trace["selected_basic"]["card_id"],
                trace["selected_basic"]["serial"],
            ),
            (343, 81),
        )
        self.assertEqual(trace["raw_parent_action"], [3])
        self.assertEqual(trace["applied_action"], [2])
        self.assertFalse(trace["action_identity"]["value_equal"])
        self.assertFalse(
            trace["action_identity"]["returned_parent_object_unchanged"]
        )

    def test_run_away_promotion_and_hilda_are_not_changed(self):
        main.agent({"select": None, "current": None})
        for index, expected in ((22, [2]), (23, [0]), (24, [3])):
            action = main.agent(copy.deepcopy(self.obs[index]))
            self.assertEqual(action, expected)
            self.assertEqual(
                main.LAST_STAGED_POLICY_TRACE["transaction_stage"],
                "NO_ACTION",
            )
            self.assertIsNone(survival.C3_TRANSACTION)

    def test_duplicate_reorders_options_and_does_not_reenter_parent(self):
        self.prime_to_obs27()
        calls = 0
        original = main._complete_parent_agent

        def counted(obs):
            nonlocal calls
            calls += 1
            return original(obs)

        with mock.patch.object(main, "_complete_parent_agent", counted):
            obs = copy.deepcopy(self.obs[27])
            self.assertEqual(main.agent(obs), [2])
            self.assertEqual(calls, 1)
            duplicate = copy.deepcopy(obs)
            duplicate["select"]["option"] = list(
                reversed(duplicate["select"]["option"])
            )
            rebound = main.agent(duplicate)
            self.assertEqual(calls, 1)
            selected = duplicate["select"]["option"][rebound[0]]
            hand_card = duplicate["current"]["players"][1]["hand"][
                selected["index"]
            ]
            self.assertEqual(
                (selected["type"], hand_card["id"], hand_card["serial"]),
                (7, 343, 81),
            )
            self.assertEqual(
                main.LAST_STAGED_POLICY_TRACE["transaction_stage"],
                "DUPLICATE_REBIND",
            )

    def test_exact_transaction_verification_and_full_reentry_once(self):
        self.prime_to_obs27()
        calls = 0
        original = main._complete_parent_agent

        def counted(obs):
            nonlocal calls
            calls += 1
            return original(obs)

        with mock.patch.object(main, "_complete_parent_agent", counted):
            initial = copy.deepcopy(self.obs[27])
            self.assertEqual(main.agent(initial), [2])
            self.assertEqual(calls, 1)
            post = self.post_basic_observation(initial)
            action = main.agent(post)
            self.assertEqual(calls, 2)
            self.assertEqual(action, [1])
            self.assertEqual(
                damage.semantic_action(post, action), ("ATTACK", 1071)
            )
            self.assertIsNone(survival.C3_TRANSACTION)
            self.assertEqual(
                main.LAST_STAGED_POLICY_TRACE["transaction_stage"],
                "COMPLETED",
            )

    def test_transaction_records_complete_pre_snapshot(self):
        self.arm_obs27()
        transaction = survival.C3_TRANSACTION
        self.assertIsInstance(transaction.get("pre"), dict)
        self.assertIn("parent", transaction["pre"])
        self.assertIn("integrated_transaction", transaction["pre"])
        self.assertIn("v1_transaction", transaction["pre"])

    def test_transaction_failure_rolls_back_original_parent_post(self):
        initial, _ = self.arm_obs27()
        transaction = copy.deepcopy(survival.C3_TRANSACTION)
        original_post = transaction["original_post"]
        post = self.post_basic_observation(initial)
        post["current"]["supporterPlayed"] = False
        action = main.agent(post)
        self.assertEqual(
            damage.semantic_action(post, action), ("ATTACK", 1071)
        )
        self.assertIsNone(survival.C3_TRANSACTION)
        self.assertEqual(
            core.parent_state_snapshot(parent), original_post["parent"]
        )
        self.assertEqual(
            deck_v1.V1_TRANSACTION, original_post["v1_transaction"]
        )
        self.assertEqual(
            deck_v1.V1_DUPLICATES, original_post["v1_duplicates"]
        )
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["transaction_stage"], "ABORTED"
        )
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["guard_failure"],
            "TRANSACTION_UNRELATED_PUBLIC_MUTATION",
        )

    def test_abort_without_semantic_rebind_runs_fresh_parent_from_pre(self):
        initial, _ = self.arm_obs27()
        post = self.post_basic_observation(initial)
        post["current"]["supporterPlayed"] = False
        post["select"]["option"] = [{"type": 14}]
        calls = 0

        def fresh_parent(_obs):
            nonlocal calls
            calls += 1
            parent._last_decision_signature = ("fresh-abort",)
            return [0]

        with mock.patch.object(
            main, "_complete_parent_agent", fresh_parent
        ):
            action = main.agent(post)
        self.assertEqual(calls, 1)
        self.assertEqual(action, [0])
        self.assertEqual(
            parent._last_decision_signature, ("fresh-abort",)
        )
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["transaction_stage"], "ABORTED"
        )

    def test_initial_analyzer_exception_retains_complete_parent(self):
        self.prime_to_obs27()
        with mock.patch.object(
            damage,
            "evaluate_survival_decision",
            side_effect=RuntimeError("forced"),
        ):
            action = main.agent(copy.deepcopy(self.obs[27]))
        self.assertEqual(action, [3])
        self.assertIsNone(survival.C3_TRANSACTION)
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["guard_failure"],
            "METRIC_EXCEPTION:RuntimeError",
        )

    def test_raw_parsed_disagreement_retains_complete_parent(self):
        self.prime_to_obs27()
        with mock.patch.object(
            runtime_model, "raw_parsed_agree", return_value=False
        ):
            action = main.agent(copy.deepcopy(self.obs[27]))
        self.assertEqual(action, [3])
        self.assertIsNone(survival.C3_TRANSACTION)
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["guard_failure"],
            "RAW_PARSED_DISAGREEMENT",
        )

    def test_existing_integrated_transaction_blocks_c3(self):
        self.prime_to_obs27()
        observation = copy.deepcopy(self.obs[27])
        local_trace = {
            "LAST_V0_PORT_TRACE": None,
            "LAST_V1_PACKAGE_TRACE": None,
            "LAST_STAGED_POLICY_TRACE": {"rule_version": "PARENT"},
        }

        def trace_snapshot():
            return copy.deepcopy(local_trace)

        def trace_restore(value):
            local_trace.clear()
            local_trace.update(copy.deepcopy(value))

        def trace_publish(trace, _surface):
            local_trace["LAST_STAGED_POLICY_TRACE"] = copy.deepcopy(trace)

        core.INTEGRATED_TRANSACTION = {"kind": "EXISTING_OWNER"}
        action_object = [3]
        returned = survival.agent(
            observation,
            lambda _obs: action_object,
            parent=parent,
            trace_snapshot=trace_snapshot,
            trace_restore=trace_restore,
            trace_publish=trace_publish,
        )
        self.assertIs(returned, action_object)
        self.assertIsNone(survival.C3_TRANSACTION)
        self.assertEqual(
            local_trace["LAST_STAGED_POLICY_TRACE"]["guard_failure"],
            "PARENT_TRANSACTION_IN_PROGRESS",
        )

    def test_c2_fields_survive_c3_trace_overlay(self):
        self.prime_to_obs27()
        main.agent(copy.deepcopy(self.obs[27]))
        trace = main.LAST_STAGED_POLICY_TRACE
        for field in (
            "route_rows",
            "line_importance_rows",
            "observation_fingerprint",
            "parent_trace",
            "transaction_state",
            "certified_draw_count",
            "certified_draw_damage_delta",
        ):
            self.assertIn(field, trace)
        for field in (
            "parent_post_fingerprint",
            "candidate_post_fingerprint",
            "premium_power_pro_multiplicity",
            "evidenced_policy_cap",
            "safety_cap",
        ):
            self.assertIn(field, trace)

    def test_reordered_initial_options_use_semantics_not_raw_index(self):
        self.prime_to_obs27()
        obs = copy.deepcopy(self.obs[27])
        obs["select"]["option"] = list(reversed(obs["select"]["option"]))
        action = main.agent(obs)
        option = obs["select"]["option"][action[0]]
        card = obs["current"]["players"][1]["hand"][option["index"]]
        self.assertEqual((option["type"], card["id"], card["serial"]), (7, 343, 81))
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["outcome_linkage"][
                "semantic_parent_action"
            ],
            ["ATTACK", 1071],
        )

    def test_ledger_play_duplicate_discard_recovery_and_turn_reset(self):
        survival.reset()
        main.agent({"select": None, "current": None})
        obs = copy.deepcopy(self.obs[27])
        survival.update_public_ledger(obs)
        self.assertEqual(survival.PUBLIC_LEDGER["unavailable"], [27])
        self.assertEqual(survival.PUBLIC_LEDGER["committed_current_turn"], [])
        self.assertGreaterEqual(
            len(survival.PUBLIC_LEDGER["family_marker_ids"]), 3
        )
        self.assertIn(676, survival.PUBLIC_LEDGER["family_marker_ids"])
        self.assertEqual(
            survival.PUBLIC_LEDGER["power_pro_seen_serials"], [27]
        )

    def test_duplicate_serial_across_hand_and_public_zone_is_ambiguous(self):
        main.agent({"select": None, "current": None})
        obs = copy.deepcopy(self.obs[27])
        duplicate = copy.deepcopy(
            obs["current"]["players"][1]["hand"][0]
        )
        obs["current"]["players"][1]["discard"].append(duplicate)
        survival.update_public_ledger(obs)
        self.assertTrue(survival.PUBLIC_LEDGER["ambiguous"])
        self.assertIsNone(survival._public_state(obs))

    def test_post_basic_requires_empty_energies_and_energy_cards(self):
        initial, _ = self.arm_obs27()
        post = self.post_basic_observation(initial)
        post["current"]["players"][1]["bench"][0]["energies"] = [5]
        action = main.agent(post)
        self.assertEqual(
            damage.semantic_action(post, action), ("ATTACK", 1071)
        )
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["guard_failure"],
            "TRANSACTION_BENCH_IDENTITY_MISMATCH",
        )

    def test_duplicate_fingerprint_includes_new_power_pro_evidence(self):
        main.agent({"select": None, "current": None})
        obs = copy.deepcopy(self.obs[27])
        survival.update_public_ledger(obs)
        before = survival._callback_fingerprint(obs)
        changed = copy.deepcopy(obs)
        changed["logs"] = list(changed.get("logs") or []) + [
            {
                "cardId": 1141,
                "fromArea": 2,
                "playerIndex": 0,
                "serial": 27,
                "toArea": 3,
                "type": 6,
            }
        ]
        survival.update_public_ledger(changed)
        after = survival._callback_fingerprint(changed)
        self.assertNotEqual(before, after)

        played = copy.deepcopy(obs)
        played["current"]["turn"] = 5
        played["current"]["turnActionCount"] = 0
        played["current"]["players"][0]["discard"].append(
            {"id": 1141, "playerIndex": 0, "serial": 26}
        )
        played["logs"] = [
            {"cardId": 1141, "playerIndex": 0, "serial": 26, "type": 10}
        ]
        survival.update_public_ledger(played)
        survival.update_public_ledger(copy.deepcopy(played))
        self.assertEqual(
            survival.PUBLIC_LEDGER["committed_current_turn"], [26]
        )

        discarded = copy.deepcopy(played)
        discarded["current"]["players"][0]["discard"].append(
            {"id": 1141, "playerIndex": 0, "serial": 25}
        )
        discarded["logs"] = [
            {
                "cardId": 1141,
                "fromArea": 2,
                "playerIndex": 0,
                "serial": 25,
                "toArea": 3,
                "type": 6,
            }
        ]
        survival.update_public_ledger(discarded)
        self.assertEqual(
            survival.PUBLIC_LEDGER["committed_current_turn"], [26]
        )
        self.assertEqual(
            survival.PUBLIC_LEDGER["unavailable"], [25, 26, 27]
        )

        recovered = copy.deepcopy(discarded)
        recovered["current"]["players"][0]["discard"] = [
            card
            for card in recovered["current"]["players"][0]["discard"]
            if card["serial"] != 25
        ]
        recovered["logs"] = [
            {
                "cardId": 1141,
                "fromArea": 3,
                "playerIndex": 0,
                "serial": 25,
                "toArea": 2,
                "type": 6,
            }
        ]
        survival.update_public_ledger(recovered)
        self.assertEqual(survival.PUBLIC_LEDGER["unavailable"], [26, 27])
        self.assertFalse(survival.PUBLIC_LEDGER["ambiguous"])

        future = copy.deepcopy(recovered)
        future["current"]["turn"] += 1
        future["current"]["turnActionCount"] = 0
        future["logs"] = []
        survival.update_public_ledger(future)
        self.assertEqual(survival.PUBLIC_LEDGER["committed_current_turn"], [])

    def test_missing_log_boundary_is_ambiguous_and_no_change(self):
        self.prime_to_obs27()
        obs = copy.deepcopy(self.obs[27])
        obs["logs"] = [None]
        with mock.patch.object(
            runtime_model, "raw_parsed_agree", return_value=True
        ), mock.patch.object(
            main, "_complete_parent_agent", return_value=[3]
        ):
            action = main.agent(obs)
        self.assertEqual(
            action, main.LAST_STAGED_POLICY_TRACE["raw_parent_action"]
        )
        self.assertTrue(survival.PUBLIC_LEDGER["ambiguous"])
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["guard_failure"],
            "PUBLIC_LEDGER_AMBIGUOUS",
        )

    def test_full_reentry_mismatch_semantically_rebinds_original_attack(self):
        initial, _ = self.arm_obs27()
        post = self.post_basic_observation(initial)
        original = main._complete_parent_agent

        def wrong_parent(obs):
            original(obs)
            return [0]  # END in the reordered post-Basic options.

        with mock.patch.object(main, "_complete_parent_agent", wrong_parent):
            action = main.agent(post)
        self.assertEqual(action, [1])
        self.assertEqual(
            damage.semantic_action(post, action), ("ATTACK", 1071)
        )
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["transaction_stage"],
            "ABORTED_AFTER_REENTRY",
        )
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["guard_failure"],
            "FULL_POLICY_SEMANTIC_REENTRY_MISMATCH",
        )

    def test_reentry_mismatch_without_rebind_keeps_fresh_state_action(self):
        initial, _ = self.arm_obs27()
        post = self.post_basic_observation(initial)
        post["select"]["option"] = [{"type": 14}]

        def fresh_parent(_obs):
            parent._last_decision_signature = ("fresh-reentry",)
            return [0]

        with mock.patch.object(
            main, "_complete_parent_agent", fresh_parent
        ):
            action = main.agent(post)
        self.assertEqual(action, [0])
        self.assertEqual(
            parent._last_decision_signature, ("fresh-reentry",)
        )
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["transaction_stage"],
            "ABORTED_AFTER_REENTRY",
        )


if __name__ == "__main__":
    unittest.main()
