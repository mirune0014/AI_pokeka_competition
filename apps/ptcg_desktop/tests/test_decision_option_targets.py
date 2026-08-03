from __future__ import annotations

import unittest

from helpers import card, normal_observation
from ptcg_desktop.decisions import build_decision_request


class DecisionOptionTargetTests(unittest.TestCase):
    def test_empty_option_list_is_valid_when_zero_is_required(self) -> None:
        obs = normal_observation()
        obs["select"].update({"type": 1, "minCount": 0, "maxCount": 0, "option": []})

        state = build_decision_request(obs, 4)

        self.assertEqual(state.request["options"], [])
        self.assertEqual(state.submit(state.request["request_id"], 4, []), [])

    def test_tool_option_resolves_the_attached_tool_not_its_pokemon(self) -> None:
        obs = normal_observation()
        active = obs["current"]["players"][0]["active"][0]
        active["tools"] = [card(777, 7001, 0)]
        obs["select"].update(
            {
                "type": 2,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": 4, "area": 4, "index": 0, "playerIndex": 0, "toolIndex": 0}],
            }
        )

        state = build_decision_request(
            obs,
            5,
            card_names={777: "テストどうぐ"},
            target_token=lambda value: f"serial-{value['serial']}",
        )

        option = state.request["options"][0]
        self.assertEqual(option["label"], "テストどうぐ")
        self.assertEqual(option["card_id"], 777)
        self.assertEqual(option["option_type"], 4)
        self.assertEqual(option["choice_number"], 1)
        self.assertEqual(option["target_token"], "serial-7001")

    def test_attach_option_identifies_its_in_play_target(self) -> None:
        obs = normal_observation()
        target = obs["current"]["players"][0]["bench"][0]
        obs["select"].update(
            {
                "type": 0,
                "minCount": 1,
                "maxCount": 1,
                "option": [{"type": 8, "area": 2, "index": 0, "inPlayArea": 5, "inPlayIndex": 0}],
            }
        )

        state = build_decision_request(
            obs,
            6,
            card_names={401: "手札カード", target["id"]: "対象ポケモン"},
            target_token=lambda value: f"serial-{value['serial']}",
        )

        option = state.request["options"][0]
        self.assertEqual(option["label"], "手札カード → 対象ポケモン")
        self.assertEqual(option["detail"], "「手札カード」を「対象ポケモン」につける")
        self.assertEqual(option["card_id"], 401)
        self.assertEqual(option["target_card_id"], target["id"])
        self.assertEqual(option["target_token"], f"serial-{target['serial']}")

    def test_energy_unit_option_keeps_its_count_for_localized_display(self) -> None:
        obs = normal_observation()
        obs["select"].update(
            {
                "type": 4,
                "context": 30,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {
                        "type": 6,
                        "area": 4,
                        "index": 0,
                        "playerIndex": 0,
                        "energyIndex": 0,
                        "count": 2,
                    }
                ],
            }
        )

        state = build_decision_request(obs, 7, card_names={8: "基本鋼エネルギー"})

        option = state.request["options"][0]
        self.assertEqual(option["label"], "基本鋼エネルギー（2 個分）")
        self.assertEqual(option["energy_count"], 2)
        self.assertEqual(option["choice_number"], 1)

    def test_hidden_prize_options_are_named_as_prizes_without_leaking_cards(self) -> None:
        obs = normal_observation()
        obs["select"].update(
            {
                "type": 1,
                "context": 7,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {"type": 3, "area": 6, "index": 0, "playerIndex": 0},
                    {"type": 3, "area": 6, "index": 1, "playerIndex": 0},
                ],
            }
        )

        state = build_decision_request(obs, 7, card_names={999: "秘密のカード"})

        self.assertEqual(state.request["prompt"], "取るサイドを選んでください。番号は現在の候補順です。")
        self.assertEqual([option["label"] for option in state.request["options"]], ["サイド1", "サイド2"])
        self.assertEqual([option["choice_number"] for option in state.request["options"]], [1, 2])
        for option in state.request["options"]:
            self.assertNotIn("card_id", option)
            self.assertNotIn("target_card_id", option)
            self.assertNotIn("area", option)
            self.assertNotIn("index", option)
            self.assertIsNone(option["target_token"])
        second = state.request["options"][1]["token"]
        self.assertEqual(state.submit(state.request["request_id"], 7, [second]), [1])


if __name__ == "__main__":
    unittest.main()
