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
    / "archaludon"
    / "audits"
    / "whole_agent_20260716"
    / "refresh_20260716_0503"
    / "replays_current_minus_prior"
)


def replay_observation(episode, step, player):
    path = REPLAY_DIR / f"episode_{episode}_replay.json"
    with path.open(encoding="utf-8") as handle:
        replay = json.load(handle)
    return copy.deepcopy(replay["steps"][step][player]["observation"])


class Continuity2PhaseATests(unittest.TestCase):
    def setUp(self):
        os.environ.pop(main._CONTINUITY_TRACE_ENV, None)
        main.CONTINUITY_LATEST_TRACE = None

    def test_kc_ice_cream_crosses_visible_survival_breakpoint(self):
        raw = replay_observation(86162213, 38, 0)
        obs = main.to_observation_class(raw)
        plan = main.build_continuity2_plan(obs)

        self.assertEqual(plan["objective"], "SURVIVAL_BREAKPOINT")
        self.assertEqual(plan["response_envelope"]["active_total_max"], 110)
        self.assertEqual(plan["response_envelope"]["archaludon_ex_to_active_status"], "BLOCKED")
        self.assertEqual(plan["H0"]["identity"]["card_id"], main.ARCHALUDON)
        self.assertEqual(plan["H1_survive"]["readiness"], "READY_AFTER_SURVIVAL")
        self.assertEqual(main.agent(raw), [1])  # Ice Cream, not option 2 Coated Attack.
        self.assertEqual(main.CONTINUITY_LATEST_TRACE["event"], "CHOOSE")

    def test_starmie_jetting_blow_rejects_thirty_hp_bench_line(self):
        raw = replay_observation(86161083, 74, 1)
        plan = main.build_continuity2_plan(main.to_observation_class(raw))

        self.assertEqual(plan["response_envelope"]["bench_spread_max"], 50)
        unsafe_key = "p1:line:169:66"
        rejected = {item["line_key"]: item for item in plan["H1_after_KO"]["rejected"]}
        self.assertEqual(
            rejected[unsafe_key]["reason"], "VISIBLE_BENCH_DAMAGE_OR_COUNTER_KO"
        )
        self.assertNotEqual(plan["H1_after_KO"]["identity"]["line_key"], unsafe_key)
        self.assertEqual(plan["H1_after_KO"]["identity"]["line_key"], "p1:line:169:63")

    def test_evolution_keeps_oldest_duraludon_lineage(self):
        basic = SimpleNamespace(id=169, serial=4, preEvolution=[])
        evolved = SimpleNamespace(
            id=190,
            serial=70,
            preEvolution=[SimpleNamespace(id=169, serial=4)],
        )
        self.assertEqual(
            main.continuity_lineage_key(basic, 0),
            main.continuity_lineage_key(evolved, 0),
        )
        self.assertEqual(main.continuity_lineage_key(evolved, 0), "p0:line:169:4")

    def test_specific_future_metal_is_reserved_once(self):
        raw = replay_observation(86161083, 74, 1)
        # Keep the public safe Duraludon one Metal short so H1-after-KO must bind
        # one physical hand Metal and the one future manual-attachment budget.
        safe = raw["current"]["players"][1]["bench"][1]
        safe["energies"] = safe["energies"][:2]
        safe["energyCards"] = safe["energyCards"][:2]
        raw["current"]["energyAttached"] = True
        plan = main.build_continuity2_plan(main.to_observation_class(raw))

        self.assertEqual(plan["H1_after_KO"]["readiness"], "READY_NEXT_TURN")
        tokens = [item["token"] for item in plan["ledger"]["reservations"]]
        self.assertEqual(len(tokens), len(set(tokens)))
        self.assertIn("budget:manual_next", tokens)
        self.assertTrue(any(token.startswith("hand:") for token in tokens))
        self.assertTrue(plan["ledger"]["exclusive"])
        self.assertEqual(plan["ledger"]["duplicates"], [])

    def test_survive_and_ko_branches_are_distinct(self):
        plan = main.build_continuity2_plan(
            main.to_observation_class(replay_observation(86162213, 38, 0))
        )
        self.assertEqual(plan["H1_survive"]["identity"]["line_key"], "p0:line:169:4")
        self.assertIsNone(plan["H1_after_KO"]["identity"])
        self.assertNotEqual(plan["H1_survive"], plan["H1_after_KO"])

    def test_ex_attack_to_crustle_fails_closed_and_cannot_trigger_ice(self):
        raw = replay_observation(86162213, 38, 0)
        active = raw["current"]["players"][0]["active"][0]
        active["id"] = main.ARCHALUDON_EX
        active["hp"] = 70
        active["maxHp"] = 300
        raw["select"]["option"][2]["attackId"] = main.METAL_DEFENDER
        plan = main.build_continuity2_plan(main.to_observation_class(raw))

        self.assertEqual(plan["H0"]["readiness"], "BLOCKED")
        self.assertEqual(
            plan["H0"]["blocked"][0]["reason"],
            "MYSTERIOUS_ROCK_INN_EX_DAMAGE_BLOCKED",
        )
        self.assertIsNone(plan["choice"])

    def test_cornerstone_and_unknown_effects_fail_closed(self):
        ex_attacker = SimpleNamespace(id=main.ARCHALUDON_EX)
        nonex_attacker = SimpleNamespace(id=main.ARCHALUDON)
        cornerstone = SimpleNamespace(id=main.CORNERSTONE_OGERPON_EX)
        self.assertEqual(
            main._continuity_outgoing_block(ex_attacker, cornerstone),
            "CORNERSTONE_STANCE_ABILITY_ATTACKER_BLOCKED",
        )
        self.assertIsNone(main._continuity_outgoing_block(nonex_attacker, cornerstone))

        raw = replay_observation(86162213, 38, 0)
        obs = main.to_observation_class(raw)
        unsupported = SimpleNamespace(attackId=999999, name="Unknown", damage=0, text="Do something.")
        profile = main._continuity_incoming_profile(
            obs, main.opp_active_pokemon(obs), unsupported, main.active_pokemon(obs)
        )
        self.assertEqual(profile["status"], "UNKNOWN")

    def test_plan_and_choice_are_deterministic_and_json_serializable(self):
        raw = replay_observation(86162213, 38, 0)
        obs1 = main.to_observation_class(copy.deepcopy(raw))
        obs2 = main.to_observation_class(copy.deepcopy(raw))
        first = main.build_continuity2_plan(obs1)
        second = main.build_continuity2_plan(obs2)

        self.assertEqual(first["plan_hash"], second["plan_hash"])
        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )
        self.assertEqual(main.agent(copy.deepcopy(raw)), main.agent(copy.deepcopy(raw)))

    def test_existing_immediate_attack_remains_the_choice_without_ice(self):
        raw = replay_observation(86162213, 38, 0)
        del raw["select"]["option"][1]
        raw["current"]["players"][0]["hand"] = [
            card for card in raw["current"]["players"][0]["hand"]
            if card["id"] != main.JUMBO_ICE_CREAM
        ]
        raw["current"]["players"][0]["handCount"] -= 1
        # Remaining options: Lillie, Coated Attack, End.
        self.assertEqual(main.agent(raw), [1])


if __name__ == "__main__":
    unittest.main()
