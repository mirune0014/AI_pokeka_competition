import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest


CANDIDATE_DIR = Path(__file__).resolve().parents[1]
WORKSPACE = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(CANDIDATE_DIR))

import main  # noqa: E402


REPLAY_DIR = (
    WORKSPACE
    / "autonomous_gold_20260715"
    / "audits"
    / "whole_agent_20260716"
    / "refresh_20260716_0503"
    / "replays_current_minus_prior"
)


def observation(episode, step, player):
    with (REPLAY_DIR / f"episode_{episode}_replay.json").open(encoding="utf-8") as handle:
        replay = json.load(handle)
    return copy.deepcopy(replay["steps"][step][player]["observation"])


def set_energy(pokemon, count, player_index, first_serial=99000):
    pokemon["energies"] = [main.METAL_ENERGY] * count
    pokemon["energyCards"] = [
        {
            "id": main.METAL_ENERGY,
            "serial": first_serial + index,
            "playerIndex": player_index,
        }
        for index in range(count)
    ]


class Continuity2SemanticInvariantTests(unittest.TestCase):
    def setUp(self):
        main._CONTINUITY_PENDING = None
        main._CONTINUITY_PENDING_EVENT = None
        main.CONTINUITY_LATEST_TRACE = None
        os.environ.pop(main._CONTINUITY_TRACE_ENV, None)

    def test_real_ko_router_covers_lucario_and_starmie_frames(self):
        cases = (
            (86160574, 79, 1, main.ARCHALUDON_EX, 300),
            (86161083, 42, 1, main.DURALUDON, 230),
        )
        for episode, step, player, card_id, hp in cases:
            with self.subTest(episode=episode):
                raw = observation(episode, step, player)
                self.assertEqual(raw["current"]["players"][player]["active"], [])
                plan = main.build_continuity2_plan(main.to_observation_class(copy.deepcopy(raw)))
                self.assertEqual(plan["choice"]["kind"], "KO_PROMOTE_CERTIFIED_H1")
                self.assertEqual(plan["H1_after_KO"]["identity"]["card_id"], card_id)
                self.assertEqual(plan["H1_after_KO"]["identity"]["hp"], hp)
                self.assertEqual(plan["response_envelope"]["active_total_max"], 0)
                self.assertEqual(
                    plan["response_envelope"]["response_route"],
                    "TO_ACTIVE_PRE_H1_CHECKUP",
                )
                self.assertEqual(plan["response_envelope"]["payable_attacks"], [])
                self.assertEqual(
                    plan["H1_after_KO"]["h1_primary_gate"]["state"], "READY"
                )
                self.assertEqual(main.agent(copy.deepcopy(raw)), [0])

    def test_ignore_wr_and_active_effects_are_separate(self):
        crustle_raw = observation(86162213, 38, 0)
        crustle_obs = main.to_observation_class(crustle_raw)
        crustle_profile = main._continuity_incoming_profile(
            crustle_obs,
            main.opp_active_pokemon(crustle_obs),
            main.ALL_ATTACKS[479],
            main.active_pokemon(crustle_obs),
        )
        self.assertEqual(crustle_profile["active_damage"], 90)  # FML still applies.

        starmie_raw = observation(86161083, 42, 1)
        starmie_obs = main.to_observation_class(starmie_raw)
        nebula = main._continuity_incoming_profile(
            starmie_obs,
            main.opp_active_pokemon(starmie_obs),
            main.ALL_ATTACKS[1488],
            main.my_state(starmie_obs).bench[0],
        )
        self.assertEqual(nebula["active_damage"], 210)  # FML and W/R are ignored.

        ordinary_raw = observation(86162213, 38, 0)
        ordinary_raw["current"]["stadium"] = []
        ordinary_obs = main.to_observation_class(ordinary_raw)
        ordinary = SimpleNamespace(attackId=999001, name="Ordinary", damage=120, text="")
        resistance = main._continuity_incoming_profile(
            ordinary_obs,
            main.opp_active_pokemon(ordinary_obs),
            ordinary,
            main.active_pokemon(ordinary_obs),
        )
        self.assertEqual(resistance["active_damage"], 90)

    def test_active_evolve_projection_retains_damage_tools_energy_and_identity(self):
        raw = observation(86160056, 35, 0)
        plan = main.build_continuity2_plan(main.to_observation_class(raw))
        identity = plan["H0"]["identity"]
        self.assertEqual(identity["card_id"], main.ARCHALUDON_EX)
        self.assertEqual(identity["current_card_id"], main.DURALUDON)
        self.assertEqual(identity["future_card_id"], main.ARCHALUDON_EX)
        self.assertEqual((identity["hp"], identity["max_hp"]), (360, 400))
        self.assertEqual(identity["retained_damage"], 40)
        self.assertEqual(identity["energy_count"], 3)
        self.assertEqual(plan["H0"]["attack"]["attack_id"], main.METAL_DEFENDER)
        self.assertEqual(plan["H0"]["readiness"], "READY_AFTER_EVOLVE_ALLOY")
        self.assertEqual(plan["H1_survive"]["identity"]["card_id"], main.ARCHALUDON_EX)

    def test_alloy_start_reservations_persist_without_callback_expansion(self):
        self.assertEqual(main.agent(observation(86160056, 35, 0)), [0])
        start = copy.deepcopy(main._CONTINUITY_PENDING)
        self.assertEqual(start["target_queue"], [{
            "line_key": "p0:line:169:3",
            "role": "H0",
            "count": 2,
            "deficit": 2,
        }])

        activate = observation(86160056, 36, 0)
        player = activate["current"]["players"][0]
        set_energy(player["active"][0], 3, 0, 99100)
        set_energy(player["bench"][0], 1, 0, 99200)
        self.assertEqual(main.agent(copy.deepcopy(activate)), [0])
        self.assertEqual(main._CONTINUITY_PENDING["target_queue"], start["target_queue"])
        self.assertEqual(
            main._CONTINUITY_PENDING["reserved_energy_serials"],
            start["reserved_energy_serials"],
        )

        attach = observation(86160056, 37, 0)
        player = attach["current"]["players"][0]
        set_energy(player["active"][0], 3, 0, 99300)
        set_energy(player["bench"][0], 1, 0, 99400)
        self.assertEqual(main.agent(copy.deepcopy(attach)), [0, 1])
        assigned = main._CONTINUITY_PENDING["assigned_energy"]
        self.assertEqual(len(assigned), 2)
        self.assertEqual({item["line_key"] for item in assigned}, {"p0:line:169:3"})
        self.assertEqual(len({item["serial"] for item in assigned}), 2)

    def test_alloy_exact_one_and_h0_before_h1_split(self):
        start = observation(86160056, 35, 0)
        player = start["current"]["players"][0]
        set_energy(player["active"][0], 2, 0, 99420)
        set_energy(player["bench"][0], 2, 0, 99430)
        player["hand"].append({
            "id": main.METAL_ENERGY, "serial": 99450, "playerIndex": 0,
        })
        player["handCount"] = len(player["hand"])
        self.assertEqual(main.agent(start), [0])
        queue = main._CONTINUITY_PENDING["target_queue"]
        self.assertEqual([item["role"] for item in queue], ["H0", "H1_after_KO"])
        self.assertEqual([item["count"] for item in queue], [1, 1])
        self.assertEqual(main._CONTINUITY_PENDING["reserved_energy_serials"], [52, 53])
        self.assertEqual(
            [item["line_key"] for item in main._CONTINUITY_PENDING["assigned_energy"]],
            ["p0:line:169:3", "p0:line:169:4"],
        )

    def test_turbo_frozen_target_materialization_failure_is_fail_closed(self):
        self.assertEqual(main.agent(observation(86160574, 28, 1)), [0])
        callback = observation(86160574, 29, 1)
        starmie = observation(86161083, 42, 1)["current"]["players"][0]["active"]
        callback["current"]["players"][0]["active"] = copy.deepcopy(starmie)
        self.assertEqual(main.agent(callback), [])
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["choice"]["exact_count"], 0)
        self.assertEqual(
            main.CONTINUITY_LATEST_TRACE["choice"]["kind"],
            "H0_PROOF_FAIL_CLOSED_ZERO",
        )
        role = main.CONTINUITY_LATEST_TRACE["H1_after_KO"]
        self.assertNotEqual(role["readiness"], "READY_AFTER_TURBO")
        self.assertEqual(
            main.CONTINUITY_LATEST_TRACE["pending_event"]["reason"],
            "ABANDON_H0_PROOF_FROZEN_H1_GATE_REJECTED",
        )
        self.assertEqual(
            main.CONTINUITY_LATEST_TRACE["h1_materialized_target_results"][0]
            ["materialized_targets"][0]["reason"],
            "POST_RESPONSE_TARGET_MATERIALIZATION_FAILED",
        )
        self.assertIsNone(main._CONTINUITY_PENDING)

    def test_turbo_releases_future_manual_and_owns_exposed_energy_once(self):
        self.assertEqual(main.agent(observation(86160574, 28, 1)), [0])
        callback = observation(86160574, 29, 1)
        player = callback["current"]["players"][1]
        set_energy(player["bench"][0], 2, 1, 99500)
        player["hand"].append({
            "id": main.METAL_ENERGY, "serial": 99550, "playerIndex": 1,
        })
        player["handCount"] = len(player["hand"])
        self.assertEqual(main.agent(callback), [0])
        assigned = main._CONTINUITY_PENDING["assigned_energy"]
        self.assertEqual(len(assigned), 1)
        reservations = main.CONTINUITY_LATEST_TRACE["ledger"]["reservations"]
        tokens = [item["token"] for item in reservations]
        self.assertNotIn("budget:manual_next", tokens)
        self.assertNotIn("hand:99550", tokens)
        self.assertEqual(len(tokens), len(set(tokens)))
        self.assertTrue(any(token.startswith("capability:turbo:") for token in tokens))
        self.assertTrue(any(token.startswith("effect_energy:") for token in tokens))

    def test_turbo_ko_cannot_be_preempted_by_development_retreat(self):
        raw = observation(86160574, 28, 1)
        set_energy(raw["current"]["players"][1]["bench"][0], 3, 1, 99600)
        raw["current"]["players"][0]["active"][0]["hp"] = 50
        obs = main.to_observation_class(copy.deepcopy(raw))
        slots = main.continuity_slots(obs)
        active = next(slot for slot in slots if slot["area"] == int(main.AreaType.ACTIVE))
        bench = [slot for slot in slots if slot["area"] == int(main.AreaType.BENCH)]
        self.assertTrue(main._continuity_meaningful_legal_attack(obs, active, bench))
        self.assertIsNone(main._continuity_retreat_target(obs, active, bench))
        self.assertEqual(main.agent(raw), [0])  # Turbo Flare takes the KO.

    def test_pending_effect_serial_mismatch_fails_closed(self):
        self.assertEqual(main.agent(observation(86160056, 35, 0)), [0])
        alloy = observation(86160056, 36, 0)
        alloy["select"]["contextCard"]["serial"] += 1000
        self.assertEqual(main.agent(alloy), [1])  # NO
        self.assertIsNone(main._CONTINUITY_PENDING)
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["pending_event"]["event"], "ABANDON")

    def test_attach_from_validates_effect_and_assigned_energy_serials(self):
        for step in (35, 36, 37):
            main.agent(observation(86160056, step, 0))
        wrong_effect = observation(86160056, 38, 0)
        wrong_effect["select"]["effect"]["serial"] += 1000
        main.agent(wrong_effect)
        self.assertIsNone(main._CONTINUITY_PENDING)
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["pending_event"]["event"], "ABANDON")

        self.setUp()
        for step in (35, 36, 37):
            main.agent(observation(86160056, step, 0))
        wrong_energy = observation(86160056, 38, 0)
        wrong_energy["select"]["contextCard"]["serial"] += 1000
        main.agent(wrong_energy)
        self.assertIsNone(main._CONTINUITY_PENDING)
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["pending_event"]["event"], "ABANDON")

        self.setUp()
        self.assertEqual(main.agent(observation(86160574, 28, 1)), [0])
        turbo = observation(86160574, 29, 1)
        turbo["select"]["effect"]["serial"] += 1000
        self.assertEqual(main.agent(turbo), [])
        self.assertIsNone(main._CONTINUITY_PENDING)
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["pending_event"]["event"], "ABANDON")

    def test_turn_budgets_bench_capacity_and_atomic_rollback(self):
        raw = observation(86161083, 74, 1)
        ledger = main._continuity_resource_ledger(main.to_observation_class(raw))
        budget_tokens = {resource["token"] for resource in ledger["resources"]}
        self.assertTrue({
            "budget:supporter_now", "budget:stadium_now", "budget:attack_now",
        }.issubset(budget_tokens))
        self.assertTrue(any(token.startswith("bench_slot:") for token in budget_tokens))
        before = copy.deepcopy(ledger)
        self.assertFalse(main._continuity_reserve_many(ledger, [
            ("budget:attack_now", "H0", "attack"),
            ("missing:physical", "H0", "missing"),
        ]))
        self.assertEqual(
            next(item for item in ledger["resources"] if item["token"] == "budget:attack_now")["owner"],
            next(item for item in before["resources"] if item["token"] == "budget:attack_now")["owner"],
        )
        self.assertEqual(ledger["reservations"], before["reservations"])
        self.assertEqual(len(ledger["atomic_failures"]), 1)

    def test_manual_h0_fails_closed_for_attack_locks_and_confusion(self):
        base = observation(86161083, 74, 1)
        set_energy(base["current"]["players"][1]["active"][0], 2, 1, 99700)
        base["select"]["option"] = [
            option for option in base["select"]["option"]
            if option.get("type") != int(main.OptionType.ATTACK)
        ]

        first_turn = copy.deepcopy(base)
        first_turn["current"]["turn"] = 1
        first_turn["current"]["firstPlayer"] = 1
        plan = main.build_continuity2_plan(main.to_observation_class(first_turn))
        self.assertEqual(plan["H0"]["readiness"], "ATTACK_LOCKED")

        for status in ("asleep", "paralyzed"):
            locked = copy.deepcopy(base)
            locked["current"]["players"][1][status] = True
            plan = main.build_continuity2_plan(main.to_observation_class(locked))
            self.assertEqual(plan["H0"]["readiness"], "ATTACK_LOCKED")

        confused = copy.deepcopy(base)
        confused["current"]["players"][1]["confused"] = True
        plan = main.build_continuity2_plan(main.to_observation_class(confused))
        self.assertEqual(plan["H0"]["readiness"], "UNKNOWN")
        self.assertNotEqual(plan.get("choice", {}).get("kind"), "H0_LAST_MANUAL_PREREQUISITE")

    def test_ultra_ball_protects_only_one_named_physical_metal(self):
        raw = observation(86161083, 74, 1)
        player = raw["current"]["players"][1]
        set_energy(player["active"][0], 2, 1, 99800)
        metals = [card for card in player["hand"] if card["id"] == main.METAL_ENERGY]
        self.assertTrue(metals)
        player["hand"].append({
            "id": main.METAL_ENERGY, "serial": 99850, "playerIndex": 1,
        })
        player["handCount"] = len(player["hand"])
        metal_indices = [
            index for index, card in enumerate(player["hand"])
            if card["id"] == main.METAL_ENERGY
        ]
        evolution_index = next(
            index for index, card in enumerate(player["hand"])
            if card["id"] == main.ARCHALUDON_EX
        )
        raw["select"] = {
            "type": 1,
            "context": int(main.SelectContext.DISCARD),
            "minCount": 2,
            "maxCount": 2,
            "remainDamageCounter": 0,
            "remainEnergyCost": 0,
            "option": [
                {"type": 3, "area": 2, "index": index, "playerIndex": 1}
                for index in metal_indices + [evolution_index]
            ],
            "deck": None,
            "contextCard": None,
            "effect": {"id": main.ULTRA_BALL, "serial": 99860, "playerIndex": 1},
        }
        plan = main.build_continuity2_plan(main.to_observation_class(copy.deepcopy(raw)))
        protected = plan["protected_option_keys"]
        self.assertEqual(len(protected), 1)
        protected_serial = protected[0][14]
        self.assertEqual(protected_serial, metals[0]["serial"])
        self.assertNotEqual(protected_serial, 99850)
        self.assertNotEqual(protected_serial, player["hand"][evolution_index]["serial"])

    def test_hero_cape_rewrites_survival_certificate(self):
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
        plan = main.build_continuity2_plan(main.to_observation_class(raw))
        self.assertEqual(plan["H1_survive"]["readiness"], "READY_AFTER_SURVIVAL")
        self.assertEqual(plan["H1"]["identity"]["hp"], plan["H0"]["identity"]["hp"])
        self.assertEqual(
            plan["H1"]["identity"]["max_hp"], plan["H0"]["identity"]["max_hp"]
        )
        self.assertEqual(plan["H0_execution_transition"]["kind"], "TOOL_ATTACH")

    def test_same_class_ceiling_uses_unoverridden_legacy_score_once(self):
        raw = observation(86161083, 74, 1)
        set_energy(raw["current"]["players"][1]["bench"][1], 2, 1, 99900)
        obs = main.to_observation_class(raw)
        plan = main.build_continuity2_plan(obs)
        raw_ceiling = max(
            main._continuity_raw_main_score(obs, option)
            for option in obs.select.option if option.type == main.OptionType.ATTACH
        )
        self.assertEqual(plan["choice"]["mode"], "SAME_CLASS_TIE")
        self.assertEqual(plan["choice"]["score"], raw_ceiling + 0.25)


if __name__ == "__main__":
    unittest.main()
