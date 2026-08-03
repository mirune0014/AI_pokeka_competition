from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

import _cumulative_parent as policy
import main
import planner_deck_adaptation_v1 as v1
import planner_next_attacker_distance_shadow as c2
import planner_policy as core


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
FIXTURES = (
    REPO_ROOT
    / "alakazam"
    / "fixtures"
    / "episode_88844273_public_observations"
)
STEP148 = (
    FIXTURES
    / "step_148_energized_kadabra_alakazam_in_hand_main.json"
)
REPLAY_88843743 = Path(r"C:\Users\amuam\Downloads\88843743.json")


class NextAttackerDistanceShadowFix4Tests(unittest.TestCase):
    def setUp(self):
        v1.reset()
        core.reset_integrated_state()
        policy.ability_used_dudunsparce = False
        self.base = json.loads(
            STEP148.read_text(encoding="utf-8")
        )["observation"]

    def mine(self, raw):
        current = raw["current"]
        return current["players"][current["yourIndex"]]

    def analyze(self, raw, action=None):
        return c2.analyze(
            copy.deepcopy(raw),
            [0] if action is None else action,
        )

    def active_alakazam(self):
        raw = copy.deepcopy(self.base)
        mine = self.mine(raw)
        kadabra = mine["active"][0]
        alakazam = mine["hand"].pop(0)
        mine["handCount"] -= 1
        evolved = copy.deepcopy(kadabra)
        evolved.update(
            {
                "id": 743,
                "serial": alakazam["serial"],
                "hp": 140,
                "maxHp": 140,
                "appearThisTurn": True,
                "preEvolution": [
                    copy.deepcopy(kadabra["preEvolution"][0]),
                    {
                        "id": 742,
                        "serial": kadabra["serial"],
                        "playerIndex": raw["current"]["yourIndex"],
                    },
                ],
            }
        )
        mine["active"] = [evolved]
        raw["select"]["option"] = [
            option
            for option in raw["select"]["option"]
            if option.get("type") not in (9, 13, 14)
        ] + [{"attackId": 1072, "type": 13}, {"type": 14}]
        return raw

    def run_away_observation(self):
        if not REPLAY_88843743.is_file():
            self.skipTest("public replay loader input is unavailable")
        replay = json.loads(
            REPLAY_88843743.read_text(encoding="utf-8")
        )
        return replay["steps"][22][1]["observation"]

    def test_active_alakazam_ready_is_certified_zero_distance(self):
        trace = self.analyze(self.active_alakazam())
        route = trace["best_primary_route"]
        self.assertIsNone(trace["metric_exception"])
        self.assertEqual(
            (
                route["route_class"],
                route["turn_delay"],
                route["main_actions"],
                route["forced_prompts"],
            ),
            ("CERTIFIED", 0, 0, 0),
        )
        self.assertEqual(
            route["witness"]["template"],
            "ACTIVE_ALAKAZAM_POWERFUL_HAND_READY",
        )

    def test_bench_alakazam_exact_forced_promotion(self):
        raw = self.active_alakazam()
        mine = self.mine(raw)
        mine["bench"] = [mine["active"].pop()]
        raw["select"].update(
            {
                "type": 1,
                "context": 4,
                "minCount": 1,
                "maxCount": 1,
                "option": [
                    {
                        "area": 5,
                        "index": 0,
                        "playerIndex": raw["current"]["yourIndex"],
                        "type": 3,
                    }
                ],
            }
        )
        trace = self.analyze(raw)
        route = trace["best_primary_route"]
        self.assertEqual(route["route_class"], "CERTIFIED")
        self.assertEqual(route["turn_delay"], 0)
        self.assertEqual(route["main_actions"], 0)
        self.assertEqual(route["forced_prompts"], 1)
        self.assertIn("EXACT_PROMOTION", json.dumps(route))

    def test_run_away_draw_three_is_exact_plus_sixty(self):
        raw = copy.deepcopy(self.run_away_observation())
        mine = self.mine(raw)
        kadabra = mine["bench"][0]
        kadabra.update(
            {
                "id": 743,
                "serial": 74,
                "hp": 140,
                "maxHp": 140,
                "preEvolution": [
                    {
                        "id": 741,
                        "serial": 63,
                        "playerIndex": raw["current"]["yourIndex"],
                    },
                    {
                        "id": 742,
                        "serial": 70,
                        "playerIndex": raw["current"]["yourIndex"],
                    },
                ],
            }
        )
        trace = self.analyze(raw)
        route = trace["best_primary_route"]
        self.assertEqual(route["route_class"], "CERTIFIED")
        self.assertEqual(
            route["witness"]["template"],
            "BENCH_ALAKAZAM_POWERFUL_HAND_READY_AFTER_RUN_AWAY",
        )
        self.assertEqual(trace["certified_draw_count"], 3)
        self.assertEqual(trace["certified_draw_damage_delta"], 60)
        self.assertEqual(route["projected_hand_count"], 8)
        self.assertEqual(route["projected_powerful_hand_damage"], 160)

    def test_run_away_unknown_identities_do_not_certify_alakazam(self):
        trace = self.analyze(self.run_away_observation())
        self.assertEqual(
            trace["best_primary_route"]["route_class"], "POSSIBLE"
        )
        self.assertIn(
            "NEEDS_ALAKAZAM",
            trace["best_primary_route"]["witness"][
                "missing_requirements"
            ],
        )
        self.assertEqual(
            trace["best_fallback_route"]["route_class"], "CERTIFIED"
        )
        self.assertEqual(trace["certified_draw_count"], 3)
        self.assertEqual(trace["certified_draw_damage_delta"], 60)

    def test_kadabra_evolve_and_attach_current_turn(self):
        raw = copy.deepcopy(self.base)
        mine = self.mine(raw)
        active = mine["active"][0]
        active["energies"] = []
        active["energyCards"] = []
        energy = next(
            card for card in mine["discard"] if card["id"] == 5
        )
        mine["discard"].remove(energy)
        mine["hand"].append(energy)
        mine["handCount"] += 1
        raw["select"]["option"].insert(
            -2,
            {
                "area": 2,
                "index": len(mine["hand"]) - 1,
                "inPlayArea": 4,
                "inPlayIndex": 0,
                "type": 8,
            },
        )
        route = self.analyze(raw)["best_primary_route"]
        self.assertEqual(route["route_class"], "CERTIFIED")
        self.assertEqual(route["turn_delay"], 0)
        self.assertEqual(route["main_actions"], 2)
        self.assertEqual(route["forced_prompts"], 1)

    def test_appeared_abra_waits_two_turns_and_switch_attack_is_not_ready(self):
        raw = copy.deepcopy(self.base)
        mine = self.mine(raw)
        active = mine["active"][0]
        active.update(
            {
                "id": 741,
                "serial": active["preEvolution"][0]["serial"],
                "hp": 50,
                "maxHp": 50,
                "appearThisTurn": True,
                "preEvolution": [],
            }
        )
        raw["select"]["option"] = [
            option
            for option in raw["select"]["option"]
            if option.get("type") != 9
        ]
        trace = self.analyze(raw)
        primary = trace["best_primary_route"]
        fallback = trace["best_fallback_route"]
        self.assertEqual(primary["route_class"], "CERTIFIED")
        self.assertEqual(primary["turn_delay"], 2)
        self.assertEqual(fallback["route_class"], "CERTIFIED")
        self.assertEqual(fallback["turn_delay"], 1)
        self.assertNotEqual(fallback["turn_delay"], 0)

    def test_missing_component_possible_and_complete_no_deck_impossible(self):
        possible = copy.deepcopy(self.base)
        mine = self.mine(possible)
        alakazam = mine["hand"].pop(0)
        mine["discard"].append(alakazam)
        mine["handCount"] -= 1
        possible["select"]["option"] = [
            option
            for option in possible["select"]["option"]
            if option.get("type") != 9
        ]
        route = self.analyze(possible)["best_primary_route"]
        self.assertEqual(route["route_class"], "POSSIBLE")

        impossible = copy.deepcopy(possible)
        self.mine(impossible)["deckCount"] = 0
        route = self.analyze(impossible)["best_primary_route"]
        self.assertEqual(route["route_class"], "IMPOSSIBLE")

    def test_malformed_stack_energy_and_status_fail_closed_unknown(self):
        malformed = copy.deepcopy(self.base)
        self.mine(malformed)["active"][0]["preEvolution"][0][
            "id"
        ] = 305

        energy = copy.deepcopy(self.base)
        self.mine(energy)["active"][0]["energyCards"] = []

        status = copy.deepcopy(self.base)
        del self.mine(status)["asleep"]

        for name, raw in (
            ("stack", malformed),
            ("energy", energy),
            ("status", status),
        ):
            with self.subTest(name=name):
                trace = self.analyze(raw)
                self.assertIsNone(trace["metric_exception"])
                self.assertEqual(
                    trace["best_primary_route"]["route_class"],
                    "UNKNOWN",
                )

    def test_unknown_dominates_unproven_impossible(self):
        unknown = c2._distance(
            "UNKNOWN", None, None, None, "UNRESOLVED"
        )
        impossible = c2._distance(
            "IMPOSSIBLE", 2, 0, 0, "ENUMERATED"
        )
        reduced = c2.reduce_routes([impossible, unknown])
        self.assertEqual(reduced["route_class"], "UNKNOWN")
        self.assertEqual(reduced["witness"]["template"], "UNRESOLVED")

    def test_option_reorder_preserves_semantic_distance(self):
        original = self.analyze(self.base)
        reordered = copy.deepcopy(self.base)
        reordered["select"]["option"].reverse()
        changed = self.analyze(reordered)

        def semantic(trace):
            route = trace["best_primary_route"]
            return (
                route["route_class"],
                route["turn_delay"],
                route["main_actions"],
                route["forced_prompts"],
            )

        self.assertEqual(semantic(original), semantic(changed))
        self.assertEqual(
            original["route_rows"], changed["route_rows"]
        )

    def test_duplicate_callback_has_identical_trace_and_action_evidence(self):
        first = self.analyze(self.base, action=(0,))
        second = self.analyze(self.base, action=(0,))
        self.assertEqual(first, second)
        self.assertEqual(first["action_python_type"], "builtins.tuple")
        self.assertTrue(
            all(first["action_identity"].values())
        )

    def test_duplicate_option_fails_closed_without_action_mutation(self):
        raw = copy.deepcopy(self.base)
        raw["select"]["option"].append(
            copy.deepcopy(raw["select"]["option"][0])
        )
        sentinel = [7, 3]
        trace = self.analyze(raw, action=sentinel)
        self.assertEqual(
            trace["best_primary_route"]["route_class"], "UNKNOWN"
        )
        self.assertEqual(trace["raw_parent_action"], sentinel)
        self.assertEqual(trace["applied_action"], sentinel)
        self.assertTrue(
            trace["action_identity"]["returned_parent_object_unchanged"]
        )

    def test_episode_88844273_actions_trace_and_metric_wrapper_name(self):
        expected = {67: [0], 98: [0], 121: [4], 148: [0]}
        for path in sorted(FIXTURES.glob("step_*.json")):
            fixture = json.loads(path.read_text(encoding="utf-8"))
            v1.reset()
            core.reset_integrated_state()
            action = main.agent(
                copy.deepcopy(fixture["observation"])
            )
            trace = main.LAST_STAGED_POLICY_TRACE
            self.assertEqual(
                action, expected[fixture["source_step_index"]]
            )
            self.assertEqual(trace["rule_version"], c2.RULE_VERSION)
            self.assertIsNone(trace["metric_exception"])
            self.assertIsInstance(
                trace["observation_fingerprint"], str
            )
            self.assertEqual(len(trace["observation_fingerprint"]), 64)
            self.assertEqual(
                trace["parent_trace"]["LAST_V0_PORT_TRACE"],
                main.LAST_V0_PORT_TRACE,
            )
            self.assertEqual(
                trace["parent_trace"]["LAST_V1_PACKAGE_TRACE"],
                main.LAST_V1_PACKAGE_TRACE,
            )
            for field in (
                "parent_post_fingerprint",
                "candidate_post_fingerprint",
                "expose_state_fingerprint",
                "wall_state_fingerprint",
                "premium_power_pro_multiplicity",
                "evidenced_policy_cap",
                "safety_cap",
                "hold_entry_turn",
                "hold_deadline",
                "distance_progress_by_turn",
            ):
                self.assertIn(field, trace)

        tool_path = REPO_ROOT / "infrastructure" / "tools" / "alakazam_staged_metrics.py"
        spec = importlib.util.spec_from_file_location(
            "_c2_test_metrics", tool_path
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        trace_name, wrapped_trace = module.version_trace([main])
        self.assertEqual(trace_name, "LAST_STAGED_POLICY_TRACE")
        self.assertEqual(
            wrapped_trace["rule_version"], c2.RULE_VERSION
        )

    def test_entrypoint_returns_exact_parent_object_on_analyzer_exception(self):
        sentinel = (3, 1)
        original_agent = main._deck_v1.agent
        original_analyze = main._c2_shadow.analyze
        original_trace = main._deck_v1.LAST_V1_PACKAGE_TRACE
        main._deck_v1.LAST_V1_PACKAGE_TRACE = {
            "selected_action": sentinel
        }
        main._deck_v1.agent = (
            lambda parent_module, delegate, raw: sentinel
        )

        def explode(*args, **kwargs):
            raise RuntimeError("fixture")

        main._c2_shadow.analyze = explode
        try:
            returned = main.agent({"select": {}})
        finally:
            main._deck_v1.agent = original_agent
            main._c2_shadow.analyze = original_analyze
            main._deck_v1.LAST_V1_PACKAGE_TRACE = original_trace
        self.assertIs(returned, sentinel)
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["metric_exception"],
            "RuntimeError",
        )
        self.assertEqual(
            main.LAST_STAGED_POLICY_TRACE["action_python_type"],
            "builtins.tuple",
        )

    def test_entrypoint_does_not_change_parent_transaction_state(self):
        sentinel_action = [4, 2]
        sentinel_transaction = {
            "kind": "PARENT_TEST_TRANSACTION",
            "stage": "await_fixture",
        }
        original_agent = main._deck_v1.agent
        original_transaction = core.INTEGRATED_TRANSACTION
        original_trace = main._deck_v1.LAST_V1_PACKAGE_TRACE
        main._deck_v1.LAST_V1_PACKAGE_TRACE = {
            "selected_action": sentinel_action
        }
        main._deck_v1.agent = (
            lambda parent_module, delegate, raw: sentinel_action
        )
        core.INTEGRATED_TRANSACTION = sentinel_transaction
        try:
            returned = main.agent(copy.deepcopy(self.base))
            self.assertIs(returned, sentinel_action)
            self.assertIs(
                core.INTEGRATED_TRANSACTION,
                sentinel_transaction,
            )
            self.assertTrue(
                main.LAST_STAGED_POLICY_TRACE["transaction_state"][
                    "integrated_transaction_active"
                ]
            )
        finally:
            core.INTEGRATED_TRANSACTION = original_transaction
            main._deck_v1.agent = original_agent
            main._deck_v1.LAST_V1_PACKAGE_TRACE = original_trace

    def test_runtime_exposes_dynamic_complete_trace(self):
        runtime_path = HERE / "runtime" / "main.py"
        spec = importlib.util.spec_from_file_location(
            "_c2_runtime_test", runtime_path
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        module.agent(copy.deepcopy(self.base))
        trace = module.get_last_staged_policy_trace()
        self.assertEqual(trace["rule_version"], c2.RULE_VERSION)
        self.assertIs(
            module.LAST_STAGED_POLICY_TRACE,
            module._source_module.LAST_STAGED_POLICY_TRACE,
        )

    def test_line_removal_importance_unique_and_fail_closed(self):
        trace = self.analyze(self.base)
        self.assertEqual(
            trace["line_importance_rows"][0]["importance"],
            "UNIQUE",
        )
        malformed = copy.deepcopy(self.base)
        self.mine(malformed)["active"][0]["preEvolution"][0][
            "serial"
        ] = self.mine(malformed)["active"][0]["serial"]
        trace = self.analyze(malformed)
        self.assertEqual(
            trace["line_importance_rows"][0]["importance"],
            "UNKNOWN_IMPORTANCE",
        )


if __name__ == "__main__":
    unittest.main()
