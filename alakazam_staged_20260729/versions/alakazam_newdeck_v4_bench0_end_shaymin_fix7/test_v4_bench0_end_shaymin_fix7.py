from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from unittest import mock

import _cumulative_parent as parent
import planner_deck_adaptation_v1 as deck_v1
import planner_policy as core
import planner_public_damage_continuity as damage
import planner_public_survival_bench0 as rule
import planner_runtime_model as runtime_model


MANIFEST = Path(__file__).with_name(
    "bench0_end_shaymin_observed_manifest.json"
)
INITIAL_PARENT_STATE = core.parent_state_snapshot(parent)
POSITIVE_FINGERPRINTS = {
    "9439FA80633914043CF51D644210B7FCF5EA1360FF9A47977A544D14F8BB84F9",
    "43D22FE6CDBDC51B2BB9E42AE8177AF3C1E705CD97164C1E194F25F0E73B34EA",
    "1100490679DB048CA2C3E630CA45B41C77F149D505AD6C7F3C5939DE283F25CC",
    "3FBDCF78C0D8C20F5897561E215312C7FA0FF01FDFC3D116726CEF613C16FA42",
}
TRANSACTION_FINGERPRINTS = {
    "D39835F04EC0945DCE0267CA6E695E1C4E98034AF4FC8D466A6524BCE96581B7",
    "98FDBA8B6E678EF2E92E822F8557E6F392B25481C05015CCE2449A58CD2985E1",
    "C392B095EB00D8750F5AC37D90C03B932C59A0FF4FC4C5BB890A20178146B4BF",
}


def pokemon(card_id: int, serial: int, owner: int) -> dict:
    return {
        "appearThisTurn": False,
        "energies": [],
        "energyCards": [],
        "hp": 80,
        "id": card_id,
        "maxHp": 80,
        "playerIndex": owner,
        "preEvolution": [],
        "serial": serial,
        "tools": [],
    }


def observation(
    *,
    active_id: int = 305,
    opponent_prizes: int = 3,
    shaymin_serial: int = 81,
) -> dict:
    owner = 0
    return {
        "fixture_fingerprint": None,
        "current": {
            "turn": 7,
            "turnActionCount": 4,
            "yourIndex": owner,
            "firstPlayer": 0,
            "result": -1,
            "energyAttached": False,
            "retreated": False,
            "stadiumPlayed": False,
            "supporterPlayed": False,
            "stadium": [],
            "players": [
                {
                    "active": [pokemon(active_id, 11, owner)],
                    "bench": [],
                    "discard": [],
                    "lost": [],
                    "prize": [None] * 6,
                    "hand": [
                        {"id": 741, "playerIndex": owner, "serial": 70},
                        {
                            "id": 343,
                            "playerIndex": owner,
                            "serial": shaymin_serial,
                        },
                    ],
                    "handCount": 2,
                    "deckCount": 30,
                    "benchMax": 5,
                    "asleep": False,
                    "burned": False,
                    "confused": False,
                    "paralyzed": False,
                    "poisoned": False,
                },
                {
                    "active": [pokemon(900, 51, 1)],
                    "bench": [],
                    "discard": [],
                    "lost": [],
                    "prize": [None] * opponent_prizes,
                    "handCount": 4,
                    "deckCount": 30,
                    "benchMax": 5,
                    "asleep": False,
                    "burned": False,
                    "confused": False,
                    "paralyzed": False,
                    "poisoned": False,
                },
            ],
        },
        "select": {
            "context": 0,
            "type": 0,
            "minCount": 1,
            "maxCount": 1,
            "option": [
                {"index": 1, "type": 7},
                {"type": 14},
            ],
        },
        "logs": [],
    }


def post_shaymin(obs: dict, *, options: list[dict] | None = None) -> dict:
    after = copy.deepcopy(obs)
    mine = after["current"]["players"][0]
    selected = mine["hand"].pop(1)
    mine["handCount"] -= 1
    benched = pokemon(selected["id"], selected["serial"], 0)
    benched["appearThisTurn"] = True
    mine["bench"] = [benched]
    after["current"]["turnActionCount"] += 1
    after["select"]["option"] = (
        copy.deepcopy(options)
        if options is not None
        else [{"type": 14}, {"attackId": 1071, "type": 13}]
    )
    after["logs"] = [
        {
            "cardId": 343,
            "playerIndex": 0,
            "serial": selected["serial"],
            "type": 10,
        }
    ]
    return after


class Harness:
    def __init__(self):
        self.surface = {
            "LAST_V0_PORT_TRACE": None,
            "LAST_V1_PACKAGE_TRACE": None,
            "LAST_STAGED_POLICY_TRACE": {"rule_version": "PARENT"},
        }

    def snapshot(self):
        return copy.deepcopy(self.surface)

    def restore(self, value):
        self.surface = copy.deepcopy(value)

    def publish(self, trace, parent_surface):
        self.surface = copy.deepcopy(parent_surface)
        self.surface["LAST_STAGED_POLICY_TRACE"] = copy.deepcopy(trace)

    @property
    def trace(self):
        return self.surface["LAST_STAGED_POLICY_TRACE"]


class Bench0EndShayminFix7Tests(unittest.TestCase):
    def setUp(self):
        core.restore_parent_state(parent, INITIAL_PARENT_STATE)
        core.reset_integrated_state()
        deck_v1.reset()
        deck_v1.REMOVED_RULE_HITS = []
        deck_v1.COMPLIANCE_BLOCK_TAG = None
        rule.reset()
        self.harness = Harness()
        self.parsed_patch = mock.patch.object(
            parent, "to_observation_class", return_value=object()
        )
        self.parity_patch = mock.patch.object(
            runtime_model, "raw_parsed_agree", return_value=True
        )
        self.parsed_patch.start()
        self.parity_patch.start()

    def tearDown(self):
        self.parity_patch.stop()
        self.parsed_patch.stop()

    def call(self, obs, complete_parent):
        return rule.agent(
            obs,
            complete_parent,
            parent=parent,
            trace_snapshot=self.harness.snapshot,
            trace_restore=self.harness.restore,
            trace_publish=self.harness.publish,
        )

    def arm(self, obs=None, complete_parent=None):
        obs = copy.deepcopy(obs or observation())
        parent_action = [1]
        complete_parent = complete_parent or (lambda _obs: parent_action)
        action = self.call(obs, complete_parent)
        self.assertEqual(action, [0])
        self.assertIsNotNone(rule.C3_TRANSACTION)
        self.assertEqual(self.harness.trace["transaction_stage"], "ARMED")
        return obs

    def assert_parent_exact(self, obs, parent_action, **patches):
        contexts = [
            mock.patch.object(target, name, value)
            for (target, name), value in patches.items()
        ]
        for context in contexts:
            context.start()
        try:
            returned = self.call(obs, lambda _obs: parent_action)
        finally:
            for context in reversed(contexts):
                context.stop()
        self.assertIs(returned, parent_action)
        self.assertIsNone(rule.C3_TRANSACTION)
        self.assertTrue(
            self.harness.trace["action_identity"][
                "returned_parent_object_unchanged"
            ]
        )

    def test_manifest_has_exact_17_classified_rows_and_hashes(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        fixtures = manifest["fixtures"]
        self.assertEqual(len(fixtures), 17)
        grouped = {
            name: {row["fingerprint"] for row in fixtures if row["classification"] == name}
            for name in (
                "positive",
                "transaction_negative",
                "prize_futile_negative",
            )
        }
        self.assertEqual(grouped["positive"], POSITIVE_FINGERPRINTS)
        self.assertEqual(
            grouped["transaction_negative"], TRANSACTION_FINGERPRINTS
        )
        self.assertEqual(len(grouped["prize_futile_negative"]), 10)
        self.assertEqual(
            manifest["source"]["reach_audit"]["sha256"],
            "152F230A5E3D55C280CBA3F4A64FC8E87AC3DA1C3A741F5AF6B14FFEE93A42C2",
        )
        self.assertEqual(
            manifest["source"]["verified_row_csv"]["sha256"],
            "11692093A46A33FDDAEE037DBCCA193B1C4E300C59EAFA50380FDD0A19018DEB",
        )
        self.assertEqual(
            manifest["source"]["end_reach_input"]["sha256"],
            "0C5F0DE8BD940A8B557C1D9C6C94B403E6DFBFE7A19EF4F67EECCB7FAAC33E7D",
        )

    def test_four_fixed_positive_fingerprints_fire_including_existing_win(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        positives = [
            row for row in manifest["fixtures"]
            if row["classification"] == "positive"
        ]
        for row in positives:
            with self.subTest(fingerprint=row["fingerprint"]):
                rule.reset()
                core.reset_integrated_state()
                deck_v1.reset()
                obs = observation(
                    active_id=row["own_active_id"],
                    opponent_prizes=row["opponent_remaining_prizes"],
                )
                obs["fixture_fingerprint"] = row["fingerprint"]
                action = self.call(obs, lambda _obs: [1])
                self.assertEqual(action, [0])
                self.assertEqual(
                    damage.semantic_action(obs, action), ("OTHER", 7)
                )
                self.assertEqual(
                    self.harness.trace["guard_class"],
                    "BENCH0_END_SHAYMIN_EMERGENCY",
                )
                if row["opponent"] == "kangaskhan_crustle":
                    self.assertEqual(row["final_outcome"], "POLICY_WIN")

    def test_three_transaction_fingerprints_refuse_exact_parent(self):
        for index, fingerprint in enumerate(sorted(TRANSACTION_FINGERPRINTS)):
            with self.subTest(fingerprint=fingerprint):
                rule.reset()
                core.reset_integrated_state()
                deck_v1.reset()
                if index % 2:
                    deck_v1.V1_TRANSACTION = {
                        "rule": fingerprint,
                        "stage": "OBSERVED",
                    }
                else:
                    core.INTEGRATED_TRANSACTION = {
                        "kind": fingerprint,
                        "stage": "OBSERVED",
                    }
                obs = observation()
                obs["fixture_fingerprint"] = fingerprint
                parent_action = [1]
                returned = self.call(obs, lambda _obs: parent_action)
                self.assertIs(returned, parent_action)
                self.assertEqual(
                    self.harness.trace["guard_failure"],
                    "PARENT_TRANSACTION_IN_PROGRESS",
                )

    def test_two_prize_futile_fingerprints_refuse_exact_parent(self):
        for fingerprint, active_id, prizes in (
            (
                "A9636A2B0655F3A57FDC1CFEBEB675088D0B9E07AEAE5B1ED613551588B1D82D",
                305,
                1,
            ),
            (
                "4DD4B0A7BF15C8905B3F63C2551E05BD24DF6EF1E3DE311FAB3E060D679C38D4",
                140,
                1,
            ),
        ):
            with self.subTest(fingerprint=fingerprint):
                rule.reset()
                obs = observation(
                    active_id=active_id, opponent_prizes=prizes
                )
                obs["fixture_fingerprint"] = fingerprint
                parent_action = [1]
                returned = self.call(obs, lambda _obs: parent_action)
                self.assertIs(returned, parent_action)
                self.assertEqual(
                    self.harness.trace["guard_failure"], "PRIZE_FUTILE"
                )

    def test_parent_attack_never_uses_inherited_broad_c3_path(self):
        obs = observation()
        obs["select"]["option"].insert(
            1, {"attackId": 1071, "type": 13}
        )
        parent_action = [1]
        self.assertEqual(
            damage.semantic_action(obs, parent_action), ("ATTACK", 1071)
        )
        self.assert_parent_exact(obs, parent_action)
        self.assertEqual(
            self.harness.trace["guard_failure"],
            "PARENT_SEMANTIC_NOT_END",
        )

    def test_bench_nonempty_refuses_exact_parent(self):
        obs = observation()
        obs["current"]["players"][0]["bench"] = [pokemon(741, 22, 0)]
        self.assert_parent_exact(obs, [1])
        self.assertEqual(
            self.harness.trace["guard_failure"], "OWN_BENCH_NOT_EMPTY"
        )

    def test_no_shaymin_and_only_abra_dunsparce_refuse(self):
        for cards in (
            [{"id": 741, "playerIndex": 0, "serial": 70}],
            [
                {"id": 741, "playerIndex": 0, "serial": 70},
                {"id": 305, "playerIndex": 0, "serial": 71},
            ],
        ):
            with self.subTest(cards=cards):
                rule.reset()
                obs = observation()
                obs["current"]["players"][0]["hand"] = cards
                obs["current"]["players"][0]["handCount"] = len(cards)
                obs["select"]["option"] = [
                    {"index": 0, "type": 7},
                    {"type": 14},
                ]
                self.assert_parent_exact(obs, [1])
                self.assertEqual(
                    self.harness.trace["guard_failure"],
                    "SHAYMIN_NOT_IN_HAND",
                )

    def test_serial_index_mismatch_refuses_exact_parent(self):
        obs = observation()
        obs["select"]["option"][0].update(
            {"cardId": 343, "serial": 999}
        )
        self.assert_parent_exact(obs, [1])
        self.assertEqual(
            self.harness.trace["guard_failure"],
            "SHAYMIN_PLAY_OPTION_NOT_EXACT",
        )

    def test_duplicate_play_option_for_one_shaymin_refuses(self):
        obs = observation()
        obs["select"]["option"].insert(1, {"index": 1, "type": 7})
        self.assert_parent_exact(obs, [2])
        self.assertEqual(
            self.harness.trace["guard_failure"],
            "SHAYMIN_PLAY_OPTION_AMBIGUITY",
        )

    def test_multiple_shaymin_physical_ambiguity_refuses(self):
        obs = observation()
        obs["current"]["players"][0]["hand"].append(
            {"id": 343, "playerIndex": 0, "serial": 82}
        )
        obs["current"]["players"][0]["handCount"] += 1
        obs["select"]["option"].insert(1, {"index": 2, "type": 7})
        self.assert_parent_exact(obs, [2])
        self.assertEqual(
            self.harness.trace["guard_failure"],
            "SHAYMIN_PHYSICAL_AMBIGUITY",
        )

    def test_raw_parsed_mismatch_refuses_exact_parent(self):
        obs = observation()
        parent_action = [1]
        with mock.patch.object(
            runtime_model, "raw_parsed_agree", return_value=False
        ):
            returned = self.call(obs, lambda _obs: parent_action)
        self.assertIs(returned, parent_action)
        self.assertEqual(
            self.harness.trace["guard_failure"],
            "RAW_PARSED_DISAGREEMENT",
        )

    def test_non_main_or_non_live_refuses_exact_parent(self):
        for field, value in (
            ("context", 4),
            ("type", 9),
        ):
            with self.subTest(field=field):
                rule.reset()
                obs = observation()
                obs["select"][field] = value
                self.assert_parent_exact(obs, [1])
                self.assertEqual(
                    self.harness.trace["guard_failure"],
                    "NOT_LIVE_NORMAL_MAIN",
                )
        rule.reset()
        obs = observation()
        obs["current"]["result"] = 0
        self.assert_parent_exact(obs, [1])
        self.assertEqual(
            self.harness.trace["guard_failure"], "NOT_LIVE_NORMAL_MAIN"
        )

    def test_stadium_opponent_and_damage_metadata_do_not_guard_fire(self):
        obs = observation(active_id=743, opponent_prizes=6)
        obs["opponent_name"] = "arbitrary-unrecognized-opponent"
        obs["current"]["stadium"] = [
            {"id": 9999, "playerIndex": 1, "serial": 91}
        ]
        obs["current"]["players"][0]["active"][0]["hp"] = 1
        obs["current"]["players"][1]["active"][0]["hp"] = 999
        action = self.call(obs, lambda _obs: [1])
        self.assertEqual(action, [0])
        self.assertEqual(
            self.harness.trace["guard_class"],
            "BENCH0_END_SHAYMIN_EMERGENCY",
        )

    def test_transaction_created_by_initial_parent_refuses(self):
        obs = observation()
        parent_action = [1]

        def complete_parent(_obs):
            deck_v1.V1_TRANSACTION = {
                "rule": "CREATED_DURING_PARENT",
                "stage": "OPEN",
            }
            return parent_action

        returned = self.call(obs, complete_parent)
        self.assertIs(returned, parent_action)
        self.assertIsNone(rule.C3_TRANSACTION)
        self.assertEqual(
            self.harness.trace["guard_failure"],
            "PARENT_TRANSACTION_IN_PROGRESS",
        )

    def test_duplicate_callback_rebinds_exact_serial_without_parent_reentry(self):
        obs = observation()
        calls = 0

        def complete_parent(_obs):
            nonlocal calls
            calls += 1
            return [1]

        self.arm(obs, complete_parent)
        duplicate = copy.deepcopy(obs)
        duplicate["select"]["option"] = list(
            reversed(duplicate["select"]["option"])
        )
        rebound = self.call(duplicate, complete_parent)
        self.assertEqual(calls, 1)
        self.assertEqual(rebound, [1])
        selected = duplicate["select"]["option"][rebound[0]]
        hand_card = duplicate["current"]["players"][0]["hand"][
            selected["index"]
        ]
        self.assertEqual(
            (selected["type"], hand_card["id"], hand_card["serial"]),
            (7, 343, 81),
        )
        self.assertEqual(
            self.harness.trace["transaction_stage"], "DUPLICATE_REBIND"
        )

    def test_valid_hand_to_bench_reentry_preserves_parent_end(self):
        obs = observation()
        calls = 0

        def complete_parent(current_obs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return [1]
            self.assertEqual(len(current_obs["select"]["option"]), 2)
            return [0]

        self.arm(obs, complete_parent)
        after = post_shaymin(obs)
        action = self.call(after, complete_parent)
        self.assertEqual(calls, 2)
        self.assertEqual(damage.semantic_action(after, action), ("END", None))
        self.assertIsNone(rule.C3_TRANSACTION)
        self.assertEqual(
            self.harness.trace["transaction_stage"], "COMPLETED"
        )

    def test_invalid_hand_to_bench_fails_to_current_parent_action(self):
        obs = observation()
        current_parent_action = [0]
        calls = 0

        def complete_parent(_obs):
            nonlocal calls
            calls += 1
            return [1] if calls == 1 else current_parent_action

        self.arm(obs, complete_parent)
        after = post_shaymin(obs)
        after["current"]["players"][0]["bench"][0]["serial"] = 999
        returned = self.call(after, complete_parent)
        self.assertIs(returned, current_parent_action)
        self.assertEqual(
            self.harness.trace["guard_failure"],
            "TRANSACTION_BENCH_IDENTITY_MISMATCH",
        )

    def test_unrelated_public_mutation_fails_to_current_parent_action(self):
        obs = observation()
        current_parent_action = [0]
        calls = 0

        def complete_parent(_obs):
            nonlocal calls
            calls += 1
            return [1] if calls == 1 else current_parent_action

        self.arm(obs, complete_parent)
        after = post_shaymin(obs)
        after["current"]["supporterPlayed"] = True
        returned = self.call(after, complete_parent)
        self.assertIs(returned, current_parent_action)
        self.assertEqual(
            self.harness.trace["guard_failure"],
            "TRANSACTION_UNRELATED_PUBLIC_MUTATION",
        )

    def test_non_distinct_main_fails_to_current_parent_action(self):
        obs = observation()
        current_parent_action = [1]
        calls = 0

        def complete_parent(_obs):
            nonlocal calls
            calls += 1
            return [1] if calls == 1 else current_parent_action

        self.arm(obs, complete_parent)
        same_state = copy.deepcopy(obs)
        same_state["select"]["option"].insert(
            0, {"attackId": 1071, "type": 13}
        )
        returned = self.call(same_state, complete_parent)
        self.assertIs(returned, current_parent_action)
        self.assertEqual(
            self.harness.trace["guard_failure"],
            "TRANSACTION_TURN_OR_ACTION_COUNT_MISMATCH",
        )

    def test_reentry_end_missing_returns_current_parent_with_fault(self):
        obs = observation()
        attack_action = [0]
        calls = 0

        def complete_parent(_obs):
            nonlocal calls
            calls += 1
            return [1] if calls == 1 else attack_action

        self.arm(obs, complete_parent)
        after = post_shaymin(
            obs, options=[{"attackId": 1071, "type": 13}]
        )
        returned = self.call(after, complete_parent)
        self.assertIs(returned, attack_action)
        self.assertEqual(
            self.harness.trace["guard_failure"],
            "REENTRY_SAVED_END_NOT_LEGAL",
        )

    def test_reentry_parent_transaction_returns_current_parent_with_fault(self):
        obs = observation()
        current_action = [0]
        calls = 0

        def complete_parent(_obs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return [1]
            deck_v1.V1_TRANSACTION = {
                "rule": "REENTRY_FIXTURE",
                "stage": "OPEN",
            }
            return current_action

        self.arm(obs, complete_parent)
        after = post_shaymin(obs, options=[{"type": 14}])
        returned = self.call(after, complete_parent)
        self.assertIs(returned, current_action)
        self.assertEqual(
            self.harness.trace["guard_failure"],
            "REENTRY_PARENT_TRANSACTION_IN_PROGRESS",
        )

    def test_reentry_mismatch_rebinds_saved_end_after_exact_restore(self):
        obs = observation()
        calls = 0

        def complete_parent(_obs):
            nonlocal calls
            calls += 1
            return [1] if calls == 1 else [1]

        self.arm(obs, complete_parent)
        after = post_shaymin(obs)
        action = self.call(after, complete_parent)
        self.assertEqual(damage.semantic_action(after, action), ("END", None))
        self.assertEqual(
            self.harness.trace["guard_failure"],
            "FULL_POLICY_SEMANTIC_REENTRY_MISMATCH",
        )

    def test_game_reset_clears_transaction_and_returns_exact_deck(self):
        self.arm()
        deck = self.call(
            {"select": None, "current": None}, lambda _obs: self.fail()
        )
        self.assertEqual(deck, rule.exact_deck())
        self.assertEqual(len(deck), 60)
        self.assertIsNone(rule.C3_TRANSACTION)
        self.assertEqual(rule.C3_DUPLICATES, {})


if __name__ == "__main__":
    unittest.main()
