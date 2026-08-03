from __future__ import annotations

import copy
from dataclasses import asdict
import json
from pathlib import Path
import unittest

from cg.api import (
    AreaType,
    Option,
    OptionType,
    search_begin,
    search_end,
    search_step,
    to_observation_class,
)

import _cumulative_parent as policy
import main
import planner_deck_adaptation_v1 as v1
import planner_policy as core
import test_v1_compliance_patch as compliance_tests


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
FIXTURES = (
    REPO_ROOT
    / "alakazam_staged_20260729"
    / "fixtures"
    / "episode_88844273_public_observations"
)
STEP148 = (
    FIXTURES
    / "step_148_energized_kadabra_alakazam_in_hand_main.json"
)
REPLAY = Path(r"C:\Users\amuam\Downloads\88844273.json")


class ExactEvolutionKoFix2Tests(unittest.TestCase):
    def setUp(self):
        v1.reset()
        core.INTEGRATED_TRANSACTION = None
        core.INTEGRATED_DUPLICATE_CACHE.clear()
        self.base = json.loads(
            STEP148.read_text(encoding="utf-8")
        )["observation"]

    def invoke(self, raw, fallback=None):
        calls = []
        baseline = [7] if fallback is None else fallback
        action = v1.agent(
            policy,
            lambda value: calls.append(value) or baseline,
            copy.deepcopy(raw),
        )
        self.assertLessEqual(len(calls), 1)
        return action

    def owner_player(self, raw):
        owner = raw["current"]["yourIndex"]
        return owner, raw["current"]["players"][owner]

    def target_player(self, raw):
        owner = raw["current"]["yourIndex"]
        return raw["current"]["players"][1 - owner]

    def set_boundary(self, deck_count, hand_count, target_hp):
        raw = copy.deepcopy(self.base)
        _, mine = self.owner_player(raw)
        mine["deckCount"] = deck_count
        mine["hand"] = mine["hand"][:hand_count]
        mine["handCount"] = hand_count
        self.target_player(raw)["active"][0]["hp"] = target_hp
        evolves = [
            option
            for option in raw["select"]["option"]
            if option["type"] == int(OptionType.EVOLVE)
        ]
        self.assertEqual(len(evolves), 3)
        if hand_count <= 10:
            raw["select"]["option"] = [
                option
                for index, option in enumerate(raw["select"]["option"])
                if option["type"] != int(OptionType.EVOLVE) or index == 0
            ]
        return raw

    def assert_nonfire(self, raw):
        v1.reset()
        action = self.invoke(raw)
        self.assertEqual(action, [7])
        self.assertNotEqual(
            v1.LAST_V1_PACKAGE_TRACE["selected_rule"],
            v1.RULE_ALAKAZAM_EXACT_EVOLUTION_KO,
        )
        self.assertIsNone(v1.V1_TRANSACTION)

    def test_actual_fixture_actions_and_trace_identity(self):
        expected = {67: [0], 98: [0], 121: [4], 148: [0]}
        for path in sorted(FIXTURES.glob("step_*.json")):
            fixture = json.loads(path.read_text(encoding="utf-8"))
            step = fixture["source_step_index"]
            v1.reset()
            action = main.agent(copy.deepcopy(fixture["observation"]))
            self.assertEqual(action, expected[step])
            if step == 148:
                self.assertEqual(fixture["expected_baseline_action"], [7])
                self.assertEqual(
                    v1.LAST_V1_PACKAGE_TRACE["selected_rule"],
                    v1.RULE_ALAKAZAM_EXACT_EVOLUTION_KO,
                )
                self.assertEqual(
                    v1.V1_TRANSACTION["planned_psychic_draw_choice"],
                    "YES",
                )
                self.assertEqual(v1.V1_TRANSACTION["planned_post_hand"], 14)
                self.assertEqual(v1.V1_TRANSACTION["planned_post_deck"], 4)

    def test_deck_boundaries_and_exact_damage(self):
        cases = (
            (4, 12, 280, "YES", 14, 1),
            (3, 10, 180, "NO", 9, 3),
            (2, 10, 180, "NO", 9, 2),
            (1, 10, 180, "NO", 9, 1),
        )
        for deck, hand, hp, choice, post_hand, post_deck in cases:
            with self.subTest(deck=deck):
                v1.reset()
                raw = self.set_boundary(deck, hand, hp)
                if deck == 4:
                    target = self.target_player(raw)["active"][0]
                    target["id"] = 687
                    target["hp"] = 280
                    target["maxHp"] = 280
                self.assertEqual(self.invoke(raw), [0])
                transaction = v1.V1_TRANSACTION
                self.assertEqual(
                    transaction["rule"],
                    v1.RULE_ALAKAZAM_EXACT_EVOLUTION_KO,
                )
                self.assertEqual(
                    transaction["planned_psychic_draw_choice"], choice
                )
                self.assertEqual(
                    transaction["planned_post_hand"], post_hand
                )
                self.assertEqual(
                    transaction["planned_post_deck"], post_deck
                )

    def test_no_math_not_yes_math_and_hp_plus_one_fail_closed(self):
        self.assert_nonfire(self.set_boundary(3, 10, 181))
        self.assert_nonfire(self.set_boundary(4, 8, 201))

    def test_deck_zero_requires_public_prize_terminal(self):
        terminal = self.set_boundary(0, 10, 180)
        _, mine = self.owner_player(terminal)
        mine["prize"] = mine["prize"][:2]
        self.assertEqual(self.invoke(terminal), [0])
        self.assertEqual(
            v1.V1_TRANSACTION["planned_psychic_draw_choice"], "NO"
        )
        self.assertEqual(v1.V1_TRANSACTION["planned_post_hand"], 9)
        self.assertEqual(v1.V1_TRANSACTION["planned_post_deck"], 0)

        nonterminal = self.set_boundary(0, 10, 180)
        _, mine = self.owner_player(nonterminal)
        mine["prize"] = mine["prize"][:3]
        self.assert_nonfire(nonterminal)

    def test_option_reorder_and_owner_mirror_choose_same_serials(self):
        reordered = copy.deepcopy(self.base)
        reordered["select"]["option"].reverse()
        target_index = next(
            index
            for index, option in enumerate(reordered["select"]["option"])
            if option["type"] == int(OptionType.EVOLVE)
            and option["area"] == int(AreaType.HAND)
            and option["index"] == 0
            and option["inPlayArea"] == int(AreaType.ACTIVE)
            and option["inPlayIndex"] == 0
        )
        self.assertEqual(self.invoke(reordered), [target_index])

        v1.reset()
        mirrored = copy.deepcopy(self.base)
        mirrored["current"]["players"].reverse()
        mirrored["current"]["yourIndex"] = (
            1 - mirrored["current"]["yourIndex"]
        )
        mirrored["current"]["firstPlayer"] = (
            1 - mirrored["current"]["firstPlayer"]
        )

        def mirror_owner(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key == "playerIndex" and item in (0, 1):
                        value[key] = 1 - item
                    else:
                        mirror_owner(item)
            elif isinstance(value, list):
                for item in value:
                    mirror_owner(item)

        mirror_owner(mirrored)
        self.assertEqual(self.invoke(mirrored), [0])
        self.assertEqual(v1.V1_TRANSACTION["card_serial"], 73)
        self.assertEqual(v1.V1_TRANSACTION["kadabra_serial"], 67)

    def test_candidate_count_duplicates_and_serial_sharing_fail_closed(self):
        no_target = copy.deepcopy(self.base)
        del no_target["select"]["option"][0]
        self.assert_nonfire(no_target)

        semantic_duplicate = copy.deepcopy(self.base)
        semantic_duplicate["select"]["option"].append(
            copy.deepcopy(semantic_duplicate["select"]["option"][0])
        )
        self.assert_nonfire(semantic_duplicate)

        second_source = copy.deepcopy(self.base)
        _, mine = self.owner_player(second_source)
        extra = copy.deepcopy(mine["hand"][0])
        extra["serial"] = 9001
        mine["hand"].append(extra)
        mine["handCount"] += 1
        option = copy.deepcopy(second_source["select"]["option"][0])
        option["index"] = len(mine["hand"]) - 1
        second_source["select"]["option"].append(option)
        self.assert_nonfire(second_source)

        shared_source = copy.deepcopy(self.base)
        _, mine = self.owner_player(shared_source)
        bench_kadabra = copy.deepcopy(mine["active"][0])
        bench_kadabra["serial"] = 9010
        bench_kadabra["preEvolution"][0]["serial"] = 9011
        bench_kadabra["energyCards"][0]["serial"] = 9012
        mine["bench"][0] = bench_kadabra
        option = copy.deepcopy(shared_source["select"]["option"][0])
        option["inPlayArea"] = int(AreaType.BENCH)
        option["inPlayIndex"] = 0
        shared_source["select"]["option"].append(option)
        self.assert_nonfire(shared_source)

    def test_malformed_unrelated_and_unstable_target_options_fail_closed(self):
        malformed = copy.deepcopy(self.base)
        malformed["select"]["option"][7]["index"] = 999
        self.assert_nonfire(malformed)

        unstable = copy.deepcopy(self.base)
        unstable["select"]["option"][0]["index"] = 999
        self.assert_nonfire(unstable)

        wrong_owner = copy.deepcopy(self.base)
        wrong_owner["select"]["option"][0]["playerIndex"] = 0
        self.assert_nonfire(wrong_owner)

    def test_lineage_tool_energy_status_effect_prize_and_bench_guards(self):
        mutations = []

        immature = copy.deepcopy(self.base)
        self.owner_player(immature)[1]["active"][0][
            "appearThisTurn"
        ] = True
        mutations.append(("immature", immature))

        lineage = copy.deepcopy(self.base)
        self.owner_player(lineage)[1]["active"][0][
            "preEvolution"
        ][0]["id"] = 305
        mutations.append(("lineage", lineage))

        tool = copy.deepcopy(self.base)
        self.owner_player(tool)[1]["active"][0]["tools"] = [
            {"id": 1172, "serial": 9020, "playerIndex": 1}
        ]
        mutations.append(("tool", tool))

        energy = copy.deepcopy(self.base)
        self.owner_player(energy)[1]["active"][0]["energies"] = []
        self.owner_player(energy)[1]["active"][0]["energyCards"] = []
        mutations.append(("energy", energy))

        status = copy.deepcopy(self.base)
        self.owner_player(status)[1]["asleep"] = True
        mutations.append(("status", status))

        effect = copy.deepcopy(self.base)
        effect["current"]["stadium"] = [
            {"id": 999999, "serial": 9021, "playerIndex": 0}
        ]
        mutations.append(("effect", effect))

        bench = copy.deepcopy(self.base)
        self.target_player(bench)["bench"] = []
        mutations.append(("bench", bench))

        for name, raw in mutations:
            with self.subTest(name=name):
                self.assert_nonfire(raw)

        original = policy.prize_count
        try:
            policy.prize_count = lambda pokemon: None
            self.assert_nonfire(copy.deepcopy(self.base))
        finally:
            policy.prize_count = original

    def test_current_terminal_ko_boss_and_mine_precedence_unchanged(self):
        fx = compliance_tests.V1CompliancePatchTests(
            methodName="runTest"
        )
        fx.setUp()
        try:
            current, _ = fx.bench_alakazam_observation()
            current.current.players[0].prize = [None]
            self.assertEqual(fx.call(current, [1]), [1])
            self.assertIn(
                "CURRENT_EXACT_TERMINAL_KO_PRECEDENCE",
                v1.LAST_V1_PACKAGE_TRACE["reason_tags"],
            )

            v1.reset()
            boss, hand = fx.main_obs(
                hand_ids=[1182, 1152, 1152, 1152, 1152, 1152],
                target_hp=50,
                options_card_ids=[1182],
            )
            boss.current.players[0].prize = [None, None]
            boss.current.players[1].active = [
                fx.ready_psyduck(20, ready=False)
            ]
            boss.current.players[1].bench = [fx.boss_target(23, 100)]
            self.assertEqual(fx.call(boss, [1]), [0])
            self.assertEqual(
                v1.LAST_V1_PACKAGE_TRACE["selected_rule"], v1.RULE_BOSS
            )

            v1.reset()
            mine, _ = fx.main_obs(
                hand_ids=[1152, 1266, 1152, 1152, 1152, 1152],
                target_hp=100,
                options_card_ids=[1266],
            )
            mine.current.players[1].active = [fx.tera_target(3)]
            play = mine.select.option[0]
            mine.select.option = [
                Option(OptionType.END),
                play,
                Option(OptionType.ATTACK, attackId=1072),
            ]
            self.assertEqual(fx.call(mine, [0]), [1])
            self.assertEqual(
                v1.LAST_V1_PACKAGE_TRACE["selected_rule"], v1.RULE_MINE
            )
        finally:
            fx.tearDown()

    def test_checked_engine_full_chain_hidden_mask_and_duplicates(self):
        replay = json.loads(REPLAY.read_text(encoding="utf-8"))
        hidden = replay["steps"][0][0]["visualize"][147]["current"]
        initial_raw = copy.deepcopy(self.base)
        initial = to_observation_class(copy.deepcopy(initial_raw))
        owner = initial.current.yourIndex
        opponent = 1 - owner
        ids = lambda cards: [card["id"] for card in cards if card]

        v1.reset()
        action = main.agent(copy.deepcopy(initial_raw))
        self.assertEqual(action, [0])
        duplicate = main.agent(copy.deepcopy(initial_raw))
        self.assertEqual(duplicate, action)

        state = search_begin(
            initial,
            ids(hidden["players"][owner]["deck"]),
            ids(hidden["players"][owner]["prize"]),
            ids(hidden["players"][opponent]["deck"]),
            ids(hidden["players"][opponent]["prize"]),
            ids(hidden["players"][opponent]["hand"]),
            [],
        )
        callbacks = []
        try:
            for expected in ([0], [13], [0, 1]):
                state = search_step(state.searchId, action)
                raw = asdict(copy.deepcopy(state.observation))
                callback_owner = raw["current"]["yourIndex"]
                for player in raw["current"]["players"]:
                    player["prize"] = [None] * len(player["prize"])
                raw["current"]["players"][1 - callback_owner][
                    "hand"
                ] = None
                raw["current"]["looking"] = None

                action = main.agent(copy.deepcopy(raw))
                trace = copy.deepcopy(v1.LAST_V1_PACKAGE_TRACE)
                repeated = main.agent(copy.deepcopy(raw))
                self.assertEqual(repeated, action)
                self.assertEqual(action, expected)
                self.assertNotIn(
                    "V1_IRREVERSIBLE_ABORT_FAULT",
                    trace["reason_tags"],
                )
                callbacks.append((raw, action, trace))
        finally:
            search_end()

        ability, main_callback, prize = callbacks
        self.assertEqual(
            ability[0]["current"]["players"][owner]["handCount"], 11
        )
        self.assertEqual(
            ability[0]["current"]["players"][owner]["deckCount"], 7
        )
        self.assertEqual(
            main_callback[0]["current"]["players"][owner]["handCount"], 14
        )
        self.assertEqual(
            main_callback[0]["current"]["players"][owner]["deckCount"], 4
        )
        self.assertEqual(
            main_callback[0]["select"]["option"][13]["attackId"], 1072
        )
        self.assertEqual(prize[0]["select"]["minCount"], 2)
        self.assertEqual(prize[0]["select"]["maxCount"], 2)
        self.assertEqual(
            len(prize[0]["current"]["players"][opponent]["active"]), 0
        )
        self.assertIn("V1_TRANSACTION_COMPLETE", prize[2]["reason_tags"])
        self.assertIsNone(v1.V1_TRANSACTION)

    def test_deck_zero_terminal_uses_exact_prize_prompt_verifier(self):
        replay = json.loads(REPLAY.read_text(encoding="utf-8"))
        hidden = replay["steps"][0][0]["visualize"][147]["current"]
        initial = to_observation_class(copy.deepcopy(self.base))
        owner = initial.current.yourIndex
        opponent = 1 - owner
        ids = lambda cards: [card["id"] for card in cards if card]

        state = search_begin(
            initial,
            ids(hidden["players"][owner]["deck"]),
            ids(hidden["players"][owner]["prize"]),
            ids(hidden["players"][opponent]["deck"]),
            ids(hidden["players"][opponent]["prize"]),
            ids(hidden["players"][opponent]["hand"]),
            [],
        )
        try:
            ability_state = search_step(state.searchId, [0])
            main_state = search_step(ability_state.searchId, [0])
            prize_state = search_step(main_state.searchId, [13])
            ability_template = asdict(
                copy.deepcopy(ability_state.observation)
            )
            main_template = asdict(copy.deepcopy(main_state.observation))
            prize_template = asdict(copy.deepcopy(prize_state.observation))
        finally:
            search_end()

        def mask(raw):
            callback_owner = raw["current"]["yourIndex"]
            for player in raw["current"]["players"]:
                player["prize"] = [None] * len(player["prize"])
            raw["current"]["players"][1 - callback_owner]["hand"] = None
            raw["current"]["looking"] = None
            return raw

        start = copy.deepcopy(self.base)
        start_mine = start["current"]["players"][owner]
        start_mine["deckCount"] = 0
        start_mine["prize"] = start_mine["prize"][:2]
        v1.reset()
        self.assertEqual(self.invoke(start), [0])
        self.assertEqual(
            v1.V1_TRANSACTION["planned_psychic_draw_choice"], "NO"
        )

        ability = mask(ability_template)
        ability["current"]["players"][owner]["deckCount"] = 0
        ability["current"]["players"][owner]["prize"] = [None, None]
        self.assertEqual(self.invoke(ability, fallback=[0]), [1])
        self.assertEqual(v1.V1_TRANSACTION["psychic_draw_choice"], "NO")

        attack = copy.deepcopy(ability)
        attack["current"]["turnActionCount"] += 1
        attack["select"] = copy.deepcopy(main_template["select"])
        attack["select"]["option"] = [
            option
            for option in attack["select"]["option"]
            if option["type"]
            in (int(OptionType.ATTACK), int(OptionType.END))
            and (
                option["type"] != int(OptionType.ATTACK)
                or option["attackId"] == 1072
            )
        ]
        attack_index = next(
            index
            for index, option in enumerate(attack["select"]["option"])
            if option["type"] == int(OptionType.ATTACK)
        )
        self.assertEqual(
            self.invoke(attack, fallback=[len(attack["select"]["option"]) - 1]),
            [attack_index],
        )
        self.assertEqual(
            v1.V1_TRANSACTION["stage"], "await_added_attack_verify"
        )
        self.assertEqual(
            v1.V1_TRANSACTION["attack_resolution"]["expected_damage"], 220
        )

        prize = copy.deepcopy(attack)
        prize["current"]["turnActionCount"] += 1
        target = prize["current"]["players"][opponent]["active"].pop()
        prize["current"]["players"][opponent]["discard"].append(
            {
                "id": target["id"],
                "serial": target["serial"],
                "playerIndex": opponent,
            }
        )
        prize["select"] = copy.deepcopy(prize_template["select"])
        prize["select"]["minCount"] = 2
        prize["select"]["maxCount"] = 2
        prize["select"]["option"] = prize["select"]["option"][:2]
        prize["logs"] = copy.deepcopy(prize_template["logs"])
        damage_logs = [
            log for log in prize["logs"] if log["type"] == 16
        ]
        self.assertEqual(len(damage_logs), 1)
        damage_logs[0]["value"] = -220

        action = self.invoke(prize, fallback=[0, 1])
        trace = copy.deepcopy(v1.LAST_V1_PACKAGE_TRACE)
        self.assertEqual(action, [0, 1])
        self.assertIn("V1_TRANSACTION_COMPLETE", trace["reason_tags"])
        self.assertNotIn(
            "V1_IRREVERSIBLE_ABORT_FAULT", trace["reason_tags"]
        )
        self.assertIsNone(v1.V1_TRANSACTION)
        self.assertEqual(self.invoke(prize, fallback=[0, 1]), action)


if __name__ == "__main__":
    unittest.main()
