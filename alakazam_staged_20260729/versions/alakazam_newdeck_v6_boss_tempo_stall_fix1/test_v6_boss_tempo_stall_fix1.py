from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest
from unittest import mock

import _cumulative_parent as parent
import main
import planner_boss_powerful_hand_exact_ko_reservation as fix10
import planner_boss_tempo_stall as tempo
import planner_deck_adaptation_v1 as deck_v1
import planner_policy as core
import planner_public_survival_bench0 as survival
import planner_public_tactical_monotonicity as fix9


HERE = Path(__file__).resolve().parent
FIXTURE = (
    HERE.parents[1]
    / "fixtures"
    / "episode_89096241_public_observations"
    / "step_111_seat0_main.json"
)
CLEAN_PARENT = core.parent_state_snapshot(parent)


class BossTempoStallFix1Tests(unittest.TestCase):
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
        tempo.reset()
        main.LAST_V0_PORT_TRACE = None
        main.LAST_V1_PACKAGE_TRACE = None
        main.LAST_STAGED_POLICY_TRACE = None

    @staticmethod
    def _fixture():
        payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        return copy.deepcopy(payload["observation"])

    def _main_position(self, target_id=652):
        raw = self._fixture()
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        theirs = raw["current"]["players"][1 - owner]

        # Preserve the replay serial and public shape, but place an exact card
        # whose printed attacks and retreat both need at least two Energy.
        target = theirs["bench"][0]
        target.update(
            {
                "id": target_id,
                "hp": parent.card_table[target_id].hp,
                "maxHp": parent.card_table[target_id].hp,
                "energies": [],
                "energyCards": [],
                "preEvolution": [],
                "tools": [],
            }
        )
        # Keep the other two-prize target outside immediate Boss-KO range for
        # the positive stall fixture.
        theirs["bench"][1]["hp"] = 400
        theirs["bench"][1]["maxHp"] = 400
        theirs["bench"][1]["tools"] = [
            {"id": 1159, "serial": 900002, "playerIndex": 1 - owner}
        ]

        # The setup progress is concrete and already legal: evolve the first
        # benched Abra into the Kadabra placed in hand.
        mine["hand"].append(
            {"id": 742, "serial": 900001, "playerIndex": owner}
        )
        mine["handCount"] = len(mine["hand"])
        raw["select"]["option"].append(
            {
                "type": 9,
                "area": 2,
                "index": len(mine["hand"]) - 1,
                "inPlayArea": 5,
                "inPlayIndex": 1,
            }
        )
        return raw, [len(raw["select"]["option"]) - 1]

    @staticmethod
    def _boss_target_prompt(initial):
        raw = copy.deepcopy(initial)
        owner = raw["current"]["yourIndex"]
        mine = raw["current"]["players"][owner]
        theirs = raw["current"]["players"][1 - owner]
        boss = next(card for card in mine["hand"] if card["serial"] == 39)
        mine["hand"] = [card for card in mine["hand"] if card["serial"] != 39]
        mine["handCount"] = len(mine["hand"])
        raw["current"]["supporterPlayed"] = True
        raw["current"]["turnActionCount"] += 1
        raw["select"] = {
            "type": 1,
            "context": 3,
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "contextCard": None,
            "effect": copy.deepcopy(boss),
            "deck": None,
            "option": [
                {
                    "type": 3,
                    "area": 5,
                    "index": index,
                    "playerIndex": 1 - owner,
                }
                for index in range(len(theirs["bench"]))
            ],
        }
        raw["step"] += 1
        return raw

    @staticmethod
    def _run_outer(raw, parent_action):
        with mock.patch.object(
            main, "_complete_fix10_agent", return_value=parent_action
        ):
            return main.agent(copy.deepcopy(raw))

    def test_ready_attacker_heavy_target_and_legal_setup_progress_fire(self):
        raw, progress_action = self._main_position()
        action = self._run_outer(raw, progress_action)

        self.assertEqual(action, [4])
        self.assertEqual(
            raw["current"]["players"][raw["current"]["yourIndex"]]["hand"][
                raw["select"]["option"][action[0]]["index"]
            ]["id"],
            1182,
        )
        self.assertEqual(tempo.TEMPO_BOSS_TRANSACTION["target_serial"], 84)
        trace = main.LAST_STAGED_POLICY_TRACE
        self.assertEqual(trace["selected_rule"], tempo.RULE_NAME)
        self.assertEqual(trace["tempo_boss_parent_action"], progress_action)
        self.assertTrue(
            trace["boss_tempo_certificate"]["hidden_switch_risk_accepted"]
        )

    def test_boss_child_rebounds_to_the_certified_target(self):
        raw, progress_action = self._main_position()
        self._run_outer(raw, progress_action)
        prompt = self._boss_target_prompt(raw)

        action = self._run_outer(prompt, [1])

        self.assertEqual(action, [0])
        self.assertEqual(
            prompt["current"]["players"][1]["bench"][
                prompt["select"]["option"][action[0]]["index"]
            ]["serial"],
            84,
        )
        self.assertIsNone(tempo.TEMPO_BOSS_TRANSACTION)
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["transaction_stage"],
            "TARGET_REBOUND",
        )

    def test_current_exact_ko_is_not_replaced(self):
        raw, progress_action = self._main_position()
        owner = raw["current"]["yourIndex"]
        raw["current"]["players"][1 - owner]["active"][0]["hp"] = 320

        action = self._run_outer(raw, progress_action)

        self.assertEqual(action, progress_action)
        self.assertIsNone(tempo.TEMPO_BOSS_TRANSACTION)

    def test_immediate_two_prize_boss_ko_is_not_replaced_by_stall(self):
        raw, progress_action = self._main_position()
        owner = raw["current"]["yourIndex"]
        theirs = raw["current"]["players"][1 - owner]
        # The second benched Archaludon ex has 300 HP and two prizes.  With
        # seventeen cards before Boss, Powerful Hand still reaches 320.
        theirs["bench"][1]["hp"] = 300
        theirs["bench"][1]["maxHp"] = 300
        theirs["bench"][1]["tools"] = []
        self.assertEqual((theirs["bench"][1]["id"], theirs["bench"][1]["hp"]), (190, 300))

        action = self._run_outer(raw, progress_action)

        self.assertEqual(action, progress_action)
        self.assertIsNone(tempo.TEMPO_BOSS_TRANSACTION)

    def test_target_that_can_attack_after_one_attachment_is_rejected(self):
        raw, progress_action = self._main_position(target_id=22)

        action = self._run_outer(raw, progress_action)

        self.assertEqual(action, progress_action)
        self.assertIsNone(tempo.TEMPO_BOSS_TRANSACTION)

    def test_target_with_only_one_retreat_cost_is_rejected(self):
        raw, progress_action = self._main_position(target_id=56)

        action = self._run_outer(raw, progress_action)

        self.assertEqual(action, progress_action)
        self.assertIsNone(tempo.TEMPO_BOSS_TRANSACTION)

    def test_parent_fix10_transaction_has_priority(self):
        raw, progress_action = self._main_position()
        fix10.FIX10_TRANSACTION = {"stage": "EXPECT_BOSS_TARGET"}

        action = self._run_outer(raw, progress_action)

        self.assertEqual(action, progress_action)
        self.assertEqual(
            fix10.FIX10_TRANSACTION,
            {"stage": "EXPECT_BOSS_TARGET"},
        )
        self.assertIsNone(tempo.TEMPO_BOSS_TRANSACTION)


if __name__ == "__main__":
    unittest.main()
