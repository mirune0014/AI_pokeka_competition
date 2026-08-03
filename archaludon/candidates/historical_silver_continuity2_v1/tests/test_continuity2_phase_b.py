import copy
import json
import os
from pathlib import Path
import sys
import unittest


CANDIDATE_DIR = Path(__file__).resolve().parents[1]
WORKSPACE = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(CANDIDATE_DIR))

import main  # noqa: E402


REPLAY_DIR = (
    WORKSPACE
    / "archaludon"
    / "audits"
    / "whole_agent_20260716"
    / "refresh_20260716_0503"
    / "replays_current_minus_prior"
)


def replay(episode):
    with (REPLAY_DIR / f"episode_{episode}_replay.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def observation(episode, step, player):
    return copy.deepcopy(replay(episode)["steps"][step][player]["observation"])


def set_energy(pokemon, count, player_index, first_serial=9000, energy_id=8):
    pokemon["energies"] = [energy_id] * count
    pokemon["energyCards"] = [
        {"id": energy_id, "serial": first_serial + index, "playerIndex": player_index}
        for index in range(count)
    ]


class Continuity2PhaseBTests(unittest.TestCase):
    def setUp(self):
        main._CONTINUITY_PENDING = None
        main._CONTINUITY_PENDING_EVENT = None
        main.CONTINUITY_LATEST_TRACE = None
        os.environ.pop(main._CONTINUITY_TRACE_ENV, None)

    def test_alloy_full_sequence_binds_active_root_and_exact_two(self):
        expected = {35: [0], 36: [0], 37: [0, 1], 38: [0], 39: [0]}
        for step in range(35, 40):
            result = main.agent(observation(86160056, step, 0))
            self.assertEqual(result, expected[step], f"step {step}")
            self.assertEqual(main._CONTINUITY_PENDING["line_key"], "p0:line:169:3")

        final = main.build_continuity2_plan(
            main.to_observation_class(observation(86160056, 40, 0))
        )
        self.assertEqual(final["H0"]["attack"]["attack_id"], main.METAL_DEFENDER)
        self.assertEqual(final["H0"]["readiness"], "READY")

    def test_alloy_declines_when_no_named_primary_deficit(self):
        raw = observation(86160056, 36, 0)
        active = raw["current"]["players"][0]["active"][0]
        set_energy(active, 3, 0)
        self.assertEqual(main.agent(raw), [1])  # NO
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["choice"]["kind"], "ALLOY_DECLINE")

    def test_turbo_exact_count_three_two_one_zero(self):
        cases = ((0, 3), (1, 2), (2, 1))
        for attached, wanted in cases:
            with self.subTest(attached=attached):
                self.setUp()
                self.assertEqual(main.agent(observation(86160574, 28, 1)), [0])
                callback = observation(86160574, 29, 1)
                line = callback["current"]["players"][1]["bench"][0]
                set_energy(line, attached, 1, first_serial=9100)
                self.assertEqual(main.agent(callback), list(range(wanted)))
                self.assertEqual(
                    main.CONTINUITY_LATEST_TRACE["choice"]["exact_count"], wanted
                )

        self.setUp()
        self.assertEqual(main.agent(observation(86160574, 28, 1)), [0])
        callback = observation(86160574, 29, 1)
        for index, line in enumerate(callback["current"]["players"][1]["bench"]):
            set_energy(line, 3, 1, first_serial=9200 + index * 10)
        self.assertEqual(main.agent(callback), [])
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["choice"]["exact_count"], 0)

    def test_turbo_repeated_callbacks_fill_one_line_before_another(self):
        self.assertEqual(main.agent(observation(86160574, 28, 1)), [0])
        self.assertEqual(main.agent(observation(86160574, 29, 1)), [0, 1, 2])
        for step in (30, 31, 32):
            raw = observation(86160574, step, 1)
            self.assertEqual(main.agent(copy.deepcopy(raw)), [0])
            first_pending = copy.deepcopy(main._CONTINUITY_PENDING)
            self.assertEqual(main.agent(copy.deepcopy(raw)), [0])
            self.assertEqual(main._CONTINUITY_PENDING, first_pending)
            self.assertEqual(main._CONTINUITY_PENDING["line_key"], "p1:line:169:64")

    def test_manual_h0_requires_actual_attach_option(self):
        raw = observation(86161083, 74, 1)
        active = raw["current"]["players"][1]["active"][0]
        set_energy(active, 2, 1, first_serial=9300)
        raw["select"]["option"] = [
            option for option in raw["select"]["option"]
            if option.get("type") != int(main.OptionType.ATTACK)
        ]
        obs = main.to_observation_class(copy.deepcopy(raw))
        plan = main.build_continuity2_plan(obs)
        self.assertEqual(plan["H0"]["readiness"], "NEEDS_MANUAL_NOW")
        self.assertEqual(plan["choice"]["kind"], "H0_LAST_MANUAL_PREREQUISITE")
        self.assertEqual(main.agent(copy.deepcopy(raw)), [0])  # Active attach.

        without_active_attach = copy.deepcopy(raw)
        without_active_attach["select"]["option"] = [
            option for option in without_active_attach["select"]["option"]
            if not (
                option.get("type") == int(main.OptionType.ATTACH)
                and option.get("inPlayArea") == int(main.AreaType.ACTIVE)
            )
        ]
        plan = main.build_continuity2_plan(main.to_observation_class(without_active_attach))
        self.assertNotEqual(plan["H0"]["readiness"], "NEEDS_MANUAL_NOW")
        self.assertFalse(
            plan.get("choice") and plan["choice"].get("kind") == "H0_LAST_MANUAL_PREREQUISITE"
        )

    def test_h1_manual_is_same_class_tie_not_global_force(self):
        raw = observation(86161083, 74, 1)
        safe = raw["current"]["players"][1]["bench"][1]
        set_energy(safe, 2, 1, first_serial=9400)
        plan = main.build_continuity2_plan(main.to_observation_class(copy.deepcopy(raw)))
        self.assertEqual(plan["H1_after_KO"]["readiness"], "READY_AFTER_MANUAL_NOW")
        self.assertEqual(plan["choice"]["mode"], "SAME_CLASS_TIE")
        # A legacy 20k item remains ahead of the attach-class ceiling.
        chosen = main.agent(copy.deepcopy(raw))[0]
        self.assertEqual(raw["select"]["option"][chosen]["type"], int(main.OptionType.PLAY))

    def test_h1_evolution_is_bound_but_only_same_class_tie(self):
        raw = observation(86161083, 74, 1)
        safe = raw["current"]["players"][1]["bench"][1]
        set_energy(safe, 1, 1, first_serial=9450)
        raw["current"]["players"][1]["discard"].extend([
            {"id": 8, "serial": 9460, "playerIndex": 1},
            {"id": 8, "serial": 9461, "playerIndex": 1},
        ])
        plan = main.build_continuity2_plan(main.to_observation_class(copy.deepcopy(raw)))
        self.assertEqual(plan["choice"]["kind"], "H1_EVOLVE_SAME_CLASS_TIE")
        self.assertEqual(plan["choice"]["mode"], "SAME_CLASS_TIE")
        self.assertEqual(
            plan["H1_after_KO"]["identity"]["line_key"], "p1:line:169:63"
        )
        self.assertEqual(plan["H1_after_KO"]["readiness"], "READY_AFTER_EVOLVE_ALLOY")
        tokens = [item["token"] for item in plan["ledger"]["reservations"]]
        self.assertEqual(len(tokens), len(set(tokens)))

    def test_zero_cost_retreat_and_promotion_stay_on_root64(self):
        self.assertEqual(main.agent(observation(86160574, 48, 1)), [10])
        self.assertEqual(main._CONTINUITY_PENDING["retreat_cost"], 0)
        self.assertEqual(main._CONTINUITY_PENDING["line_key"], "p1:line:169:64")
        switch = observation(86160574, 49, 1)
        self.assertEqual(main.agent(copy.deepcopy(switch)), [0])
        pending = copy.deepcopy(main._CONTINUITY_PENDING)
        self.assertEqual(main.agent(copy.deepcopy(switch)), [0])
        self.assertEqual(main._CONTINUITY_PENDING, pending)

    def test_ko_to_active_does_not_reuse_stale_retreat_target(self):
        promote = observation(86160574, 79, 1)
        main._CONTINUITY_PENDING = {
            "kind": "RETREAT",
            "player_index": 1,
            "turn": promote["current"]["turn"],
            "line_key": "p1:line:169:65",
            "source_active_line": "p1:line:666:73",
            "effect_serial": None,
            "retreat_cost": 0,
            "trigger_keys": [],
            "target_queue": [],
            "assigned_energy": [],
        }
        self.assertEqual(main.agent(promote), [0])  # certified ready root64, not stale root65
        self.assertIsNone(main._CONTINUITY_PENDING)
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["choice"]["kind"], "KO_PROMOTE_CERTIFIED_H1")
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["pending_event"]["event"], "ABANDON")

    def _paid_retreat_observations(self):
        raw = observation(86160574, 94, 0)
        player = raw["current"]["players"][0]
        player["active"] = [{
            "id": main.ARCHALUDON_EX,
            "serial": 9500,
            "playerIndex": 0,
            "hp": 300,
            "maxHp": 300,
            "appearThisTurn": False,
            "energies": [8, 8],
            "energyCards": [
                {"id": 8, "serial": 9501, "playerIndex": 0},
                {"id": 8, "serial": 9502, "playerIndex": 0},
            ],
            "tools": [],
            "preEvolution": [{"id": 169, "serial": 9499, "playerIndex": 0}],
        }]
        player["bench"] = [{
            "id": main.DURALUDON,
            "serial": 9600,
            "playerIndex": 0,
            "hp": 130,
            "maxHp": 130,
            "appearThisTurn": False,
            "energies": [8, 8, 8],
            "energyCards": [
                {"id": 8, "serial": 9601 + i, "playerIndex": 0} for i in range(3)
            ],
            "tools": [],
            "preEvolution": [],
        }, {
            "id": main.CINDERACE,
            "serial": 9700,
            "playerIndex": 0,
            "hp": 160,
            "maxHp": 160,
            "appearThisTurn": False,
            "energies": [8],
            "energyCards": [{"id": 8, "serial": 9701, "playerIndex": 0}],
            "tools": [],
            "preEvolution": [],
        }]
        raw["select"] = {
            "type": 0,
            "context": int(main.SelectContext.MAIN),
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": [{"type": int(main.OptionType.RETREAT)}, {"type": int(main.OptionType.END)}],
            "deck": None,
            "contextCard": None,
            "effect": None,
        }
        first_payment = copy.deepcopy(raw)
        first_payment["current"]["retreated"] = True
        first_payment["select"] = {
            "type": 4,
            "context": int(main.SelectContext.DISCARD_ENERGY),
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 2,
            "option": [
                {"type": 6, "area": 4, "index": 0, "playerIndex": 0, "energyIndex": 0, "count": 1},
                {"type": 6, "area": 4, "index": 0, "playerIndex": 0, "energyIndex": 1, "count": 1},
            ],
            "deck": None,
            "contextCard": None,
            "effect": None,
        }
        second_payment = copy.deepcopy(first_payment)
        set_energy(second_payment["current"]["players"][0]["active"][0], 1, 0, 9502)
        second_payment["select"]["remainEnergyCost"] = 1
        second_payment["select"]["option"] = [
            {"type": 6, "area": 4, "index": 0, "playerIndex": 0, "energyIndex": 0, "count": 1}
        ]
        switch = copy.deepcopy(second_payment)
        set_energy(switch["current"]["players"][0]["active"][0], 0, 0)
        switch["select"] = {
            "type": 1,
            "context": int(main.SelectContext.SWITCH),
            "minCount": 1,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": [
                {"type": 3, "area": 5, "index": 0, "playerIndex": 0},
                {"type": 3, "area": 5, "index": 1, "playerIndex": 0},
            ],
            "deck": None,
            "contextCard": None,
            "effect": None,
        }
        return raw, first_payment, second_payment, switch

    def test_paid_retreat_two_payments_and_promotion_are_one_transaction(self):
        main_obs, first, second, switch = self._paid_retreat_observations()
        self.assertEqual(main.agent(copy.deepcopy(main_obs)), [0])
        self.assertEqual(main._CONTINUITY_PENDING["retreat_cost"], 2)
        self.assertEqual(main.agent(copy.deepcopy(first)), [0])
        self.assertEqual(main.agent(copy.deepcopy(first)), [0])
        self.assertEqual(main.agent(copy.deepcopy(second)), [0])
        self.assertEqual(main.agent(copy.deepcopy(switch)), [0])
        self.assertEqual(main._CONTINUITY_PENDING["line_key"], "p0:line:169:9600")

    def test_stale_transaction_and_deck_request_reset(self):
        main_obs, first, _, _ = self._paid_retreat_observations()
        self.assertEqual(main.agent(copy.deepcopy(main_obs)), [0])
        stale = copy.deepcopy(first)
        stale["current"]["turn"] += 2
        main.build_continuity2_plan(main.to_observation_class(stale))
        self.assertIsNone(main._CONTINUITY_PENDING)
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["pending_event"]["event"], "ABANDON")

        main._CONTINUITY_PENDING = {"kind": "TURBO"}
        old_cwd = os.getcwd()
        try:
            os.chdir(CANDIDATE_DIR)
            deck = main.agent({"select": None, "logs": [], "current": None})
        finally:
            os.chdir(old_cwd)
        self.assertEqual(len(deck), 60)
        self.assertIsNone(main._CONTINUITY_PENDING)

    def test_hero_cape_requires_legal_active_attach_and_crosses_threshold(self):
        raw = observation(86162213, 38, 0)
        hand = raw["current"]["players"][0]["hand"]
        hand[1]["id"] = main.HERO_CAPE
        raw["select"]["option"][1] = {
            "type": int(main.OptionType.ATTACH),
            "area": int(main.AreaType.HAND),
            "index": 1,
            "inPlayArea": int(main.AreaType.ACTIVE),
            "inPlayIndex": 0,
        }
        plan = main.build_continuity2_plan(main.to_observation_class(copy.deepcopy(raw)))
        self.assertEqual(plan["choice"]["kind"], "CAPE_SURVIVAL_BREAKPOINT")
        self.assertEqual(main.agent(copy.deepcopy(raw)), [1])

        no_attach = copy.deepcopy(raw)
        del no_attach["select"]["option"][1]
        plan = main.build_continuity2_plan(main.to_observation_class(no_attach))
        self.assertFalse(
            plan.get("choice") and plan["choice"].get("kind") == "CAPE_SURVIVAL_BREAKPOINT"
        )

    def test_identified_stretcher_selects_named_metal_but_ultra_ball_protects_it(self):
        stretcher = observation(86161083, 74, 1)
        active = stretcher["current"]["players"][1]["active"][0]
        set_energy(active, 2, 1, first_serial=9800)
        player = stretcher["current"]["players"][1]
        player["hand"] = [card for card in player["hand"] if card["id"] != 8]
        player["handCount"] = len(player["hand"])
        player["discard"].append({"id": 8, "serial": 9810, "playerIndex": 1})
        stretcher["select"] = {
            "type": 1,
            "context": int(main.SelectContext.TO_HAND),
            "minCount": 0,
            "maxCount": 1,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": [{
                "type": 3,
                "area": int(main.AreaType.DISCARD),
                "index": len(player["discard"]) - 1,
                "playerIndex": 1,
            }],
            "deck": None,
            "contextCard": None,
            "effect": {"id": main.NIGHT_STRETCHER, "serial": 9820, "playerIndex": 1},
        }
        self.assertEqual(main.agent(stretcher), [0])
        self.assertEqual(
            main.CONTINUITY_LATEST_TRACE["choice"]["kind"],
            "STRETCHER_NAMED_PREREQUISITE",
        )

        discard = observation(86161083, 74, 1)
        set_energy(discard["current"]["players"][1]["active"][0], 2, 1, 9830)
        discard["select"] = {
            "type": 1,
            "context": int(main.SelectContext.DISCARD),
            "minCount": 2,
            "maxCount": 2,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": [
                {"type": 3, "area": 2, "index": 0, "playerIndex": 1},
                {"type": 3, "area": 2, "index": 4, "playerIndex": 1},
                {"type": 3, "area": 2, "index": 1, "playerIndex": 1},
            ],
            "deck": None,
            "contextCard": None,
            "effect": {"id": main.ULTRA_BALL, "serial": 9840, "playerIndex": 1},
        }
        selected = main.agent(discard)
        self.assertNotIn(0, selected)
        self.assertEqual(set(selected), {1, 2})

    def test_duplicate_boss_pokegear_control_is_unchanged(self):
        raw = observation(86162108, 135, 0)
        self.assertEqual(main.agent(copy.deepcopy(raw)), [1])
        chosen = main.option_card(
            main.to_observation_class(raw),
            main.to_observation_class(raw).select.option[1],
        )
        self.assertEqual(chosen.id, main.BOSS)


if __name__ == "__main__":
    unittest.main()
