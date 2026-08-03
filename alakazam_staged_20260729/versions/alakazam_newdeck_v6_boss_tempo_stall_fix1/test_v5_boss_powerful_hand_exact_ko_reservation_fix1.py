from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

import _cumulative_parent as parent
import main
import planner_boss_powerful_hand_exact_ko_reservation as fix10
import planner_deck_adaptation_v1 as deck_v1
import planner_policy as core
import planner_public_survival_bench0 as survival
import planner_public_tactical_monotonicity as fix9

HERE = Path(__file__).resolve().parent
FIXTURES = (
    HERE.parents[1]
    / "fixtures"
    / "episode_89096241_public_observations"
)
REPLAY_SHA256 = "E10E204CECE7C6EEE63C153650A4C69D81719C68F5B0CAF650B18C826A28F035"
CLEAN_PARENT = core.parent_state_snapshot(parent)


class BossPowerfulHandExactKOReservationFix1Tests(unittest.TestCase):
    def setUp(self):
        self._reset()

    def tearDown(self):
        self._reset()

    def _reset(self):
        core.restore_parent_state(parent, CLEAN_PARENT)
        core.reset_integrated_state()
        deck_v1.reset()
        survival.reset()
        fix9.reset()
        fix10.reset()
        main.LAST_V0_PORT_TRACE = None
        main.LAST_V1_PACKAGE_TRACE = None
        main.LAST_STAGED_POLICY_TRACE = None

    def fixture(self, name):
        payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        self.assertEqual(payload["episode_id"], 89096241)
        self.assertEqual(payload["seat"], 0)
        self.assertEqual(payload["source_replay_sha256"], REPLAY_SHA256)
        return copy.deepcopy(payload["observation"])

    @staticmethod
    def action_card_id(raw, action):
        option = raw["select"]["option"][action[0]]
        if option["type"] == 7:
            owner = raw["current"]["yourIndex"]
            return raw["current"]["players"][owner]["hand"][option["index"]]["id"]
        return option.get("attackId")

    @staticmethod
    def restore_unspent_poffin(raw):
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        matches = [card for card in mine["discard"] if card["serial"] == 27]
        if len(matches) != 1:
            raise AssertionError("exact replay Poffin serial 27 is not uniquely discarded")
        mine["discard"] = [card for card in mine["discard"] if card["serial"] != 27]
        mine["hand"].append(matches[0])
        mine["handCount"] = len(mine["hand"])
        return raw

    def run_outer(self, raw, parent_action):
        with mock.patch.object(main, "_complete_fix9_agent", return_value=parent_action):
            return main.agent(copy.deepcopy(raw))

    def atomic_main_raw(self):
        raw = self.fixture("step_111_seat0_main.json")
        owner = raw["current"]["yourIndex"]
        opponent = raw["current"]["players"][1 - owner]
        exact_two_prize = copy.deepcopy(opponent["bench"][1])
        self.assertEqual((exact_two_prize["id"], exact_two_prize["serial"], exact_two_prize["hp"]), (190, 82, 300))
        three_prize_survivor = {
            "appearThisTurn": False,
            "energies": [],
            "energyCards": [],
            "hp": 380,
            "id": 652,
            "maxHp": 380,
            "playerIndex": 1 - owner,
            "preEvolution": [],
            "serial": 84,
            "tools": [],
        }
        opponent["bench"] = [exact_two_prize, three_prize_survivor]
        return raw

    def boss_target_after(self, initial):
        raw = copy.deepcopy(initial)
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        boss = [card for card in mine["hand"] if card["serial"] == 39]
        self.assertEqual(len(boss), 1)
        mine["hand"] = [card for card in mine["hand"] if card["serial"] != 39]
        mine["handCount"] = len(mine["hand"])
        raw["current"]["supporterPlayed"] = True
        raw["current"]["turnActionCount"] += 1
        opponent = raw["current"]["players"][1 - owner]
        raw["select"] = {
            "type": 1,
            "context": 3,
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "contextCard": None,
            "effect": copy.deepcopy(boss[0]),
            "deck": None,
            "option": [
                {"type": 3, "area": 5, "index": index, "playerIndex": 1 - owner}
                for index in range(len(opponent["bench"]))
            ],
        }
        raw["step"] += 1
        return raw

    def main_after_target(self, target_prompt, target_index=0):
        raw = copy.deepcopy(target_prompt)
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        opponent = raw["current"]["players"][1 - owner]
        old_active = opponent["active"][0]
        selected = opponent["bench"][target_index]
        opponent["active"] = [selected]
        opponent["bench"][target_index] = old_active
        mine["discard"].append(copy.deepcopy(raw["select"]["effect"]))
        raw["current"]["turnActionCount"] += 1
        raw["select"] = {
            "type": 0,
            "context": 0,
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "contextCard": None,
            "effect": None,
            "deck": None,
            "option": [
                {"type": 13, "attackId": 1072},
                {"type": 12},
                {"type": 14},
            ],
        }
        raw["step"] += 1
        return raw

    def rare_candy_raw(self, hand_count):
        raw = self.atomic_main_raw()
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        while len(mine["hand"]) < hand_count:
            offset = len(mine["hand"])
            mine["hand"].append({
                "id": 1152,
                "serial": 910000 + offset,
                "playerIndex": owner,
            })
            mine["deckCount"] -= 1
        mine["handCount"] = len(mine["hand"])
        candy_hand_index = next(
            index for index, card in enumerate(mine["hand"])
            if card["id"] == 1079
        )
        raw["select"]["option"].append({"type": 7, "index": candy_hand_index})
        return raw, [len(raw["select"]["option"]) - 1]

    def one_prize_exact_ko_raw(self, terminal):
        raw = self.fixture("step_111_seat0_main.json")
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        by_serial = {card["serial"]: card for card in mine["hand"]}
        mine["hand"] = [
            copy.deepcopy(by_serial[27]),
            copy.deepcopy(by_serial[39]),
            copy.deepcopy(by_serial[37]),
            copy.deepcopy(by_serial[45]),
            copy.deepcopy(by_serial[42]),
        ]
        mine["handCount"] = 5
        mine["prize"] = mine["prize"][: 1 if terminal else 2]
        opponent = raw["current"]["players"][1 - owner]
        opponent["bench"] = [{
            "appearThisTurn": False,
            "energies": [],
            "energyCards": [],
            "hp": 80,
            "id": 742,
            "maxHp": 80,
            "playerIndex": 1 - owner,
            "preEvolution": [],
            "serial": 82,
            "tools": [],
        }]
        raw["select"]["option"] = [
            {"type": 7, "index": 0},
            {"type": 7, "index": 1},
            {"type": 13, "attackId": 1072},
            {"type": 12},
            {"type": 14},
        ]
        return raw

    def test_exact_replay_main_parent_poffin_candidate_boss_and_trace(self):
        raw = self.fixture("step_111_seat0_main.json")
        self.assertEqual(raw["step"], 111)
        self.assertEqual(raw["current"]["turn"], 9)
        owner = raw["current"]["yourIndex"]
        self.assertEqual(raw["current"]["players"][owner]["handCount"], 16)

        parent_action = main._complete_fix9_agent(copy.deepcopy(raw))
        self.assertEqual(parent_action, [7])
        self.assertEqual(self.action_card_id(raw, parent_action), 1086)
        self.assertIsNone(main.LAST_STAGED_POLICY_TRACE["selected_rule"])

        self._reset()
        action = main.agent(copy.deepcopy(raw))
        self.assertEqual(action, [4])
        self.assertEqual(self.action_card_id(raw, action), 1182)
        trace = main.LAST_STAGED_POLICY_TRACE
        self.assertEqual(trace["selected_rule"], fix10.RULE_NAME)
        self.assertEqual(trace["fix10_parent_action"], [7])
        self.assertEqual(trace["parent_closure_sha256"], fix10.PARENT_CLOSURE_SHA256)
        details = trace["boss_exact_ko_reservation"]
        self.assertEqual(details["certified_target"], {
            "bench_index": 1,
            "target_serial": 82,
            "remaining_hp": 300,
            "prizes": 2,
            "terminal": False,
        })
        self.assertEqual(details["pre_action_hand"], 16)
        self.assertEqual(details["optional_action_hand_cost"], 1)
        self.assertEqual(details["boss_cost"], 1)
        self.assertEqual(details["projected_attack_hand"], 15)
        self.assertEqual(details["projected_damage"], 300)
        self.assertTrue(details["projected_ko"])
        self.assertEqual(details["post_optional_projected_attack_hand"], 14)
        self.assertEqual(details["post_optional_projected_damage"], 280)
        self.assertFalse(details["post_optional_projected_ko"])

    def test_immediate_boss_child_selects_the_exact_ko_target(self):
        raw = self.restore_unspent_poffin(
            self.fixture("step_114_seat0_boss_target.json")
        )
        owner = raw["current"]["yourIndex"]
        self.assertEqual(raw["current"]["players"][owner]["handCount"], 15)
        original = main._complete_survival_agent
        main._complete_survival_agent = lambda _raw: [0]
        try:
            action = main.agent(copy.deepcopy(raw))
        finally:
            main._complete_survival_agent = original
        self.assertEqual(action, [1])
        selected = raw["select"]["option"][action[0]]
        target = raw["current"]["players"][1 - owner]["bench"][selected["index"]]
        self.assertEqual((target["id"], target["serial"], target["hp"]), (190, 82, 300))
        trace = main.LAST_STAGED_POLICY_TRACE
        self.assertEqual(trace["selected_rule"], "EFFECTIVE_TARGET_SAFETY")
        self.assertEqual(trace["reason_tags"], ["TARGET_CHILD_SELECT_HIGHER_PRIZE_KO"])
        self.assertEqual(trace["effective_targets"][1]["damage"], 300)
        self.assertTrue(trace["effective_targets"][1]["ko"])

    def test_following_main_selects_powerful_hand(self):
        raw = self.restore_unspent_poffin(self.fixture("step_115_seat0_main.json"))
        owner = raw["current"]["yourIndex"]
        self.assertEqual(raw["current"]["players"][owner]["handCount"], 15)
        original = main._complete_survival_agent
        main._complete_survival_agent = lambda _raw: [2]
        try:
            action = main.agent(copy.deepcopy(raw))
        finally:
            main._complete_survival_agent = original
        self.assertEqual(action, [0])
        self.assertEqual(self.action_card_id(raw, action), 1072)
        trace = main.LAST_STAGED_POLICY_TRACE
        self.assertEqual(trace["selected_rule"], "EXACT_KO_FLOOR")
        self.assertEqual(trace["reason_tags"], ["END_BEFORE_EXACT_KO"])
        self.assertEqual(trace["exact_ko"]["damage"], 300)

    def test_boss_stall_and_immediate_kadabra_prize_stay_parent_selected(self):
        stall = self.fixture("step_111_seat0_main.json")
        owner = stall["current"]["yourIndex"]
        opponent = stall["current"]["players"][1 - owner]
        for target in opponent["bench"]:
            target["hp"] = target["maxHp"] = 400
        boss_action = [4]
        self.assertEqual(self.run_outer(stall, boss_action), boss_action)
        self.assertIsNone(fix10.LAST_FIX10_TRACE)

        kadabra = self.fixture("step_111_seat0_main.json")
        active = kadabra["current"]["players"][owner]["active"][0]
        active["id"] = 742
        active["hp"] = active["maxHp"] = 80
        active["preEvolution"] = active["preEvolution"][:1]
        kadabra["select"]["option"][10]["attackId"] = 1071
        kadabra_attack = [10]
        self.assertEqual(self.run_outer(kadabra, kadabra_attack), kadabra_attack)
        self.assertEqual(self.action_card_id(kadabra, kadabra_attack), 1071)
        self.assertIsNone(fix10.LAST_FIX10_TRACE)

    def test_two_hit_setup_and_lethal_preserving_spend_are_allowed(self):
        two_hit = self.fixture("step_111_seat0_main.json")
        owner = two_hit["current"]["yourIndex"]
        opponent = two_hit["current"]["players"][1 - owner]
        opponent["bench"][1]["hp"] = opponent["bench"][1]["maxHp"] = 400
        parent_poffin = [7]
        self.assertEqual(self.run_outer(two_hit, parent_poffin), parent_poffin)
        self.assertIsNone(fix10.LAST_FIX10_TRACE)

        preserving = self.fixture("step_111_seat0_main.json")
        mine = preserving["current"]["players"][owner]
        mine["hand"].append({
            "id": 1152,
            "serial": 900001,
            "playerIndex": owner,
        })
        mine["handCount"] = len(mine["hand"])
        mine["deckCount"] -= 1
        self.assertEqual(mine["handCount"], 17)
        self.assertEqual(self.run_outer(preserving, parent_poffin), parent_poffin)
        self.assertIsNone(fix10.LAST_FIX10_TRACE)

    def test_unplayable_boss_and_known_zero_or_unknown_effect_fail_closed(self):
        unavailable = self.fixture("step_111_seat0_main.json")
        owner = unavailable["current"]["yourIndex"]
        hand = unavailable["current"]["players"][owner]["hand"]
        unavailable["select"]["option"] = [
            option
            for option in unavailable["select"]["option"]
            if not (
                option["type"] == 7
                and hand[option["index"]]["id"] == 1182
            )
        ]
        poffin_index = next(
            index
            for index, option in enumerate(unavailable["select"]["option"])
            if option["type"] == 7 and hand[option["index"]]["id"] == 1086
        )
        self.assertEqual(self.run_outer(unavailable, [poffin_index]), [poffin_index])
        self.assertIsNone(fix10.LAST_FIX10_TRACE)

        known_zero = self.fixture("step_111_seat0_main.json")
        target = known_zero["current"]["players"][1 - owner]["bench"][1]
        target["energies"].append(0)
        target["energyCards"].append({
            "id": 11,
            "serial": 900002,
            "playerIndex": 1 - owner,
        })
        self.assertEqual(self.run_outer(known_zero, [7]), [7])
        self.assertIsNone(fix10.LAST_FIX10_TRACE)

        unknown = self.fixture("step_111_seat0_main.json")
        target = unknown["current"]["players"][1 - owner]["bench"][1]
        target["energyCards"][0]["id"] = 999999
        self.assertEqual(self.run_outer(unknown, [7]), [7])
        self.assertIsNone(fix10.LAST_FIX10_TRACE)

    def test_atomic_saved_two_prize_target_over_three_prize_survivor_then_attack(self):
        initial = self.atomic_main_raw()
        target_prompt = self.boss_target_after(initial)
        following_main = self.main_after_target(target_prompt, target_index=0)

        original = main._complete_survival_agent
        main._complete_survival_agent = lambda _raw: [1]
        try:
            parent_target = main._complete_fix9_agent(copy.deepcopy(target_prompt))
        finally:
            main._complete_survival_agent = original
        self.assertEqual(parent_target, [1])
        self.assertEqual(target_prompt["current"]["players"][1]["bench"][1]["id"], 652)

        self._reset()
        parent_main = main._complete_fix9_agent(copy.deepcopy(initial))
        self.assertEqual(parent_main, [7])
        self._reset()
        boss_action = main.agent(copy.deepcopy(initial))
        self.assertEqual(boss_action, [4])
        self.assertEqual(fix10.FIX10_TRANSACTION["stage"], "EXPECT_BOSS_TARGET")
        self.assertEqual(fix10.FIX10_TRANSACTION["target_serial"], 82)

        with mock.patch.object(
            main,
            "_complete_fix9_agent",
            side_effect=AssertionError("owned TARGET must not delegate"),
        ):
            target_action = main.agent(copy.deepcopy(target_prompt))
        self.assertEqual(target_action, [0])
        self.assertEqual(main.LAST_STAGED_POLICY_TRACE["transaction_stage"], "TARGET_REBOUND")
        self.assertEqual(fix10.FIX10_TRANSACTION["stage"], "EXPECT_ATTACK")

        with mock.patch.object(
            main,
            "_complete_fix9_agent",
            side_effect=AssertionError("owned ATTACK must not delegate"),
        ):
            attack_action = main.agent(copy.deepcopy(following_main))
        self.assertEqual(attack_action, [0])
        self.assertEqual(self.action_card_id(following_main, attack_action), 1072)
        self.assertEqual(main.LAST_STAGED_POLICY_TRACE["transaction_stage"], "ATTACK_COMMITTED")
        self.assertIsNone(fix10.FIX10_TRANSACTION)

    def test_rare_candy_loss_triggers_boss_but_preserved_ko_keeps_candy(self):
        losing, candy_action = self.rare_candy_raw(17)
        action = self.run_outer(losing, candy_action)
        self.assertEqual(action, [4])
        details = main.LAST_STAGED_POLICY_TRACE["boss_exact_ko_reservation"]
        self.assertEqual(details["optional_action_card_id"], 1079)
        self.assertEqual(details["optional_action_hand_cost"], 2)
        self.assertEqual(details["projected_attack_hand"], 16)
        self.assertEqual(details["projected_damage"], 320)
        self.assertEqual(details["post_optional_projected_attack_hand"], 14)
        self.assertEqual(details["post_optional_projected_damage"], 280)
        self.assertIsNotNone(fix10.FIX10_TRANSACTION)

        self._reset()
        preserving, candy_action = self.rare_candy_raw(18)
        action = self.run_outer(preserving, candy_action)
        self.assertEqual(action, candy_action)
        self.assertEqual(
            preserving["current"]["players"][preserving["current"]["yourIndex"]]["handCount"],
            18,
        )
        self.assertIsNone(fix10.FIX10_TRANSACTION)
        self.assertIsNone(fix10.LAST_FIX10_TRACE)

    def test_nonterminal_one_prize_is_excluded_but_terminal_one_prize_arms(self):
        nonterminal = self.one_prize_exact_ko_raw(terminal=False)
        self.assertEqual(self.run_outer(nonterminal, [0]), [0])
        self.assertIsNone(fix10.FIX10_TRANSACTION)

        self._reset()
        terminal = self.one_prize_exact_ko_raw(terminal=True)
        self.assertEqual(self.run_outer(terminal, [0]), [1])
        certificate = fix10.FIX10_TRANSACTION["certificate"]
        self.assertEqual(certificate["certified_target"]["prizes"], 1)
        self.assertTrue(certificate["certified_target"]["terminal"])

    def test_prompt_turn_and_public_fingerprint_mismatch_clear_before_parent(self):
        initial = self.atomic_main_raw()
        exact_target = self.boss_target_after(initial)

        cases = []
        prompt = copy.deepcopy(exact_target)
        prompt["select"] = copy.deepcopy(initial["select"])
        cases.append(("prompt", prompt, "EXPECTED_BOSS_TARGET_PROMPT"))
        turn = copy.deepcopy(exact_target)
        turn["current"]["turn"] += 1
        cases.append(("turn", turn, "TURN_MISMATCH"))
        fingerprint = copy.deepcopy(exact_target)
        fingerprint["current"]["players"][0]["bench"][0]["hp"] -= 10
        cases.append(("fingerprint", fingerprint, "PUBLIC_FINGERPRINT_MISMATCH"))

        for name, malformed, expected_reason in cases:
            with self.subTest(name=name):
                self._reset()
                self.assertEqual(main.agent(copy.deepcopy(initial)), [4])
                seen = []

                def parent_delegate(_raw):
                    seen.append(fix10.FIX10_TRANSACTION)
                    return [0]

                with mock.patch.object(main, "_complete_fix9_agent", side_effect=parent_delegate):
                    self.assertEqual(main.agent(copy.deepcopy(malformed)), [0])
                self.assertEqual(seen, [None])
                self.assertIsNone(fix10.FIX10_TRANSACTION)
                self.assertEqual(main.LAST_STAGED_POLICY_TRACE["transaction_stage"], "ABORTED")
                self.assertEqual(main.LAST_STAGED_POLICY_TRACE["transaction_failure"], expected_reason)

    def test_candidate_closure_is_independently_reproducible(self):
        rows = [fix10._closure_row("main.py", (HERE / "main.py").read_bytes())]
        for path in HERE.glob("*.py"):
            if path.name.startswith("test") or path.name in {"main.py", "_policy_main.py"}:
                continue
            rows.append(fix10._closure_row(path.name, path.read_bytes()))
        rows.append(fix10._closure_row("runtime/main.py", (HERE / "runtime" / "main.py").read_bytes()))
        rows.append(fix10._closure_row("deck.csv", (HERE / "deck.csv").read_bytes()))
        expected = hashlib.sha256("".join(sorted(rows)).encode()).hexdigest().upper()
        self.assertEqual(fix10.PARENT_CLOSURE_SHA256, "FDD25914489AE74F6A0454BF70A484BC545F2C468BDC88C2653AD85F018F999E")
        self.assertEqual(fix10._closure(), expected)
        self.assertNotEqual(expected, fix10.PARENT_CLOSURE_SHA256)


if __name__ == "__main__":
    unittest.main()