from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import planner_public_damage_continuity as damage


HERE = Path(__file__).resolve().parent
COLLECTOR_PATH = HERE / "verification" / "c3_sidecar_collector.py"
SPEC = importlib.util.spec_from_file_location(
    "_c3_sidecar_collector", COLLECTOR_PATH
)
collector = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(collector)


class C3SidecarCollectorTests(unittest.TestCase):
    def trace(self, closure, *, guard="SAFE_NO_ACTION", stage="NO_ACTION"):
        return {
            "rule_version": collector.RULE,
            "parent_closure_sha256": collector.PARENT_CLOSURE,
            "candidate_closure_sha256": closure,
            "raw_parent_action": [0],
            "proposed_action": [0],
            "applied_action": [0],
            "damage_rows": [],
            "modifier_ledger": [],
            "basic_candidates": [],
            "selected_basic": None,
            "guard_class": guard,
            "guard_failure": None,
            "transaction_stage": stage,
            "parent_post_fingerprint": None,
            "candidate_post_fingerprint": None,
            "premium_power_pro_multiplicity": None,
            "evidenced_policy_cap": None,
            "safety_cap": None,
            "promotion_removal_context": None,
            "route_rows": [],
            "line_importance_rows": [],
            "metric_exception": None,
            "decision_id": None,
            "observation_fingerprint": "O",
        }

    def write_sidecar(
        self,
        root,
        events,
        *,
        opponent="silver",
        seat=0,
        seed_base=100,
        game_file=0,
    ):
        path = (
            root
            / "runs"
            / "candidate"
            / opponent
            / f"seed_{seed_base}"
            / f"seat_{seat}"
            / "sidecars"
            / f"game_{game_file:04d}.jsonl"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(json.dumps(event) + "\n" for event in events),
            encoding="utf-8",
        )

    def events(
        self,
        trace,
        *,
        ordinal=0,
        opponent="silver",
        seat=0,
        seed_base=100,
        seed=None,
        game=0,
        result=-1,
    ):
        if seed is None:
            seed = seed_base + game
        common = {
            "version": "candidate",
            "opponent": opponent,
            "policy_seat": seat,
            "seed_base": seed_base,
            "seed": seed,
            "game": game,
            "callback_ordinal": ordinal,
        }
        return [
            dict(
                common,
                event="CALL_START",
                observation={"result": result},
            ),
            dict(
                common,
                event="CALL_END",
                structurally_valid=True,
                exception=None,
                selected_action=trace["applied_action"],
                version_trace_name="LAST_STAGED_POLICY_TRACE",
                version_trace=trace,
            ),
        ]

    def mechanism_trace(
        self,
        closure,
        decision_id,
        *,
        stage="ARMED",
        observation="O",
    ):
        trace = self.trace(
            closure,
            guard="CAP_LOW_COST_BOARDOUT_AVOIDANCE",
            stage=stage,
        )
        trace.update(
            {
                "applied_action": [1],
                "proposed_action": [1],
                "selected_basic": {
                    "card_id": 343,
                    "serial": 81,
                },
                "parent_post_fingerprint": "P",
                "candidate_post_fingerprint": "C",
                "outcome_linkage": {
                    "semantic_parent_action": ["ATTACK", 1071],
                    "same_threat_in_both_projections": True,
                    "parent_boardout": True,
                    "candidate_boardout_prevented": True,
                    "tactical_outcome_equal": True,
                },
                "decision_id": decision_id,
                "observation_fingerprint": observation,
                "promotion_removal_context": (
                    "PARENT_ACTIVE_THREAT_REMOVAL_WITH_RESIDUAL"
                ),
                "damage_rows": [
                    {"continuity": "REPEATABLE_READY"}
                ],
            }
        )
        return trace

    def test_checked_no_action_row_passes_integrity(self):
        closure = damage.policy_closure_sha256()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trace = self.trace(closure)
            self.write_sidecar(root, self.events(trace))
            rows, summary = collector.collect_suite(
                root, candidate_closure=closure
            )
        self.assertEqual(len(rows), 1)
        self.assertEqual(summary["integrity_gate"], "PASS")
        self.assertEqual(
            summary["overall_gate"], "INSUFFICIENT_EVIDENCE"
        )
        self.assertFalse(summary["win_rate_aggregated"])

    def test_reach_requires_four_continuities_and_promotion_contexts(self):
        closure = damage.policy_closure_sha256()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for opponent_index, opponent in enumerate(
                ("silver", "marnie", "cynthia")
            ):
                seat = opponent_index % 2
                events = []
                for ordinal in range(10):
                    guard = (
                        "FLOOR_BOARDOUT_AVOIDANCE"
                        if ordinal % 2 == 0
                        else "CAP_LOW_COST_BOARDOUT_AVOIDANCE"
                    )
                    trace = self.trace(
                        closure, guard=guard, stage="ARMED"
                    )
                    trace.update(
                        {
                            "applied_action": [1],
                            "proposed_action": [1],
                            "selected_basic": {
                                "card_id": 343,
                                "serial": 81,
                            },
                            "parent_post_fingerprint": "P",
                            "candidate_post_fingerprint": "C",
                            "outcome_linkage": {
                                "same_threat_in_both_projections": True,
                                "parent_boardout": True,
                                "candidate_boardout_prevented": True,
                                "tactical_outcome_equal": True,
                            },
                            "decision_id": (
                                f"D-{opponent}-{ordinal}"
                            ),
                            "promotion_removal_context": (
                                "FORCED_ACTIVE_PROMOTION"
                            ),
                            "damage_rows": [
                                {"continuity": continuity}
                                for continuity in sorted(
                                    collector.CONTINUITY_CLASSES
                                )
                            ],
                        }
                    )
                    events.extend(
                        self.events(
                            trace,
                            ordinal=ordinal,
                            opponent=opponent,
                            seat=seat,
                            game=opponent_index,
                        )
                    )
                self.write_sidecar(
                    root,
                    events,
                    opponent=opponent,
                    seat=seat,
                    game_file=opponent_index,
                )
            _, summary = collector.collect_suite(
                root, candidate_closure=closure
            )
        self.assertEqual(summary["supported_threat_count"], 30)
        self.assertEqual(
            summary["promotion_removal_context_count"], 30
        )
        self.assertEqual(
            set(summary["continuity_counts"]),
            collector.CONTINUITY_CLASSES,
        )
        self.assertEqual(summary["reach_gate"], "PASS")
        self.assertEqual(summary["overall_gate"], "PASS")

    def test_reach_dedupes_transaction_stages_by_decision(self):
        closure = damage.policy_closure_sha256()

        def mechanism_trace(decision_id, stage):
            trace = self.trace(
                closure,
                guard="CAP_LOW_COST_BOARDOUT_AVOIDANCE",
                stage=stage,
            )
            trace.update(
                {
                    "applied_action": [1],
                    "proposed_action": [1],
                    "selected_basic": {
                        "card_id": 343,
                        "serial": 81,
                    },
                    "parent_post_fingerprint": "P",
                    "candidate_post_fingerprint": "C",
                    "outcome_linkage": {
                        "semantic_parent_action": ["ATTACK", 1071],
                        "same_threat_in_both_projections": True,
                        "parent_boardout": True,
                        "candidate_boardout_prevented": True,
                        "tactical_outcome_equal": True,
                    },
                    "decision_id": decision_id,
                    "promotion_removal_context": (
                        "PARENT_ACTIVE_THREAT_REMOVAL_WITH_RESIDUAL"
                    ),
                    "damage_rows": [
                        {"continuity": "REPEATABLE_READY"}
                    ],
                }
            )
            return trace

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events = []
            for ordinal, (decision_id, stage) in enumerate(
                (
                    ("D-SAME", "ARMED"),
                    ("D-SAME", "DUPLICATE_REBIND"),
                    ("D-SAME", "COMPLETED"),
                    ("D-OTHER", "ARMED"),
                )
            ):
                trace = mechanism_trace(decision_id, stage)
                if stage == "COMPLETED":
                    trace["observation_fingerprint"] = "O-POST-BASIC"
                events.extend(
                    self.events(
                        trace,
                        ordinal=ordinal,
                    )
                )
            self.write_sidecar(root, events)
            _, summary = collector.collect_suite(
                root, candidate_closure=closure
            )
        self.assertEqual(
            summary["guard_class_counts"][
                "CAP_LOW_COST_BOARDOUT_AVOIDANCE"
            ],
            4,
        )
        self.assertEqual(summary["supported_threat_count"], 2)
        self.assertEqual(
            summary["reach_guard_class_counts"][
                "CAP_LOW_COST_BOARDOUT_AVOIDANCE"
            ],
            2,
        )
        self.assertEqual(
            summary["promotion_removal_context_count"], 2
        )
        self.assertEqual(
            summary["continuity_counts"]["REPEATABLE_READY"], 2
        )
        self.assertEqual(
            summary["callback_continuity_counts"][
                "REPEATABLE_READY"
            ],
            4,
        )
        self.assertEqual(summary["integrity_gate"], "PASS")

    def test_origin_stage_observation_conflict_still_fails(self):
        closure = damage.policy_closure_sha256()
        first = self.trace(
            closure,
            guard="CAP_LOW_COST_BOARDOUT_AVOIDANCE",
            stage="ARMED",
        )
        first["decision_id"] = "D-CONFLICT"
        first["observation_fingerprint"] = "O-ONE"
        second = dict(first)
        second["observation_fingerprint"] = "O-TWO"
        second["transaction_stage"] = "DUPLICATE_REBIND"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_sidecar(
                root,
                self.events(first, ordinal=0)
                + self.events(second, ordinal=1),
            )
            _, summary = collector.collect_suite(
                root, candidate_closure=closure
            )
        self.assertEqual(summary["decision_conflict_count"], 1)
        self.assertEqual(summary["integrity_gate"], "FAIL")

    def test_cross_game_instances_do_not_conflict_but_state_dedupes(self):
        closure = damage.policy_closure_sha256()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = self.mechanism_trace(
                closure,
                "D-CROSS-GAME",
                observation="O-GAME-0",
            )
            second = self.mechanism_trace(
                closure,
                "D-CROSS-GAME",
                observation="O-GAME-1",
            )
            self.write_sidecar(
                root,
                self.events(first, game=0),
                game_file=0,
            )
            self.write_sidecar(
                root,
                self.events(second, game=1),
                game_file=1,
            )
            _, summary = collector.collect_suite(
                root, candidate_closure=closure
            )
        self.assertEqual(summary["decision_conflict_count"], 0)
        self.assertEqual(summary["reach_transaction_instance_count"], 2)
        self.assertEqual(summary["reach_decision_count"], 1)
        self.assertEqual(summary["supported_threat_count"], 1)
        self.assertEqual(summary["integrity_gate"], "PASS")

    def test_non_live_origin_callback_is_excluded_from_reach(self):
        closure = damage.policy_closure_sha256()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trace = self.mechanism_trace(
                closure,
                "D-TERMINAL",
                observation="O-TERMINAL",
            )
            self.write_sidecar(
                root,
                self.events(trace, result=0),
            )
            _, summary = collector.collect_suite(
                root, candidate_closure=closure
            )
        self.assertEqual(summary["non_live_reach_exclusion_count"], 1)
        self.assertEqual(summary["reach_transaction_instance_count"], 0)
        self.assertEqual(summary["reach_decision_count"], 0)
        self.assertEqual(summary["supported_threat_count"], 0)
        self.assertEqual(summary["integrity_gate"], "PASS")

    def test_multiple_suites_union_before_unique_state_counting(self):
        closure = damage.policy_closure_sha256()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_root = root / "shard_a"
            second_root = root / "shard_b"
            first = self.mechanism_trace(
                closure,
                "D-UNION",
                observation="O-UNION-A",
            )
            second = self.mechanism_trace(
                closure,
                "D-UNION",
                observation="O-UNION-B",
            )
            self.write_sidecar(
                first_root,
                self.events(first, game=0),
                game_file=0,
            )
            self.write_sidecar(
                second_root,
                self.events(second, game=1),
                game_file=1,
            )
            _, summary = collector.collect_suites(
                [first_root, second_root],
                candidate_closure=closure,
            )
        self.assertEqual(summary["input_suite_count"], 2)
        self.assertEqual(summary["decision_conflict_count"], 0)
        self.assertEqual(summary["reach_transaction_instance_count"], 2)
        self.assertEqual(summary["reach_decision_count"], 1)
        self.assertEqual(summary["supported_threat_count"], 1)
        self.assertEqual(summary["integrity_gate"], "PASS")

    def test_split_callback_halves_across_sources_fail_integrity(self):
        closure = damage.policy_closure_sha256()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_root = root / "shard_a"
            second_root = root / "shard_b"
            trace = self.mechanism_trace(
                closure,
                "D-SPLIT",
                observation="O-SPLIT",
            )
            events = self.events(trace)
            self.write_sidecar(first_root, [events[0]])
            self.write_sidecar(second_root, [events[1]])
            _, summary = collector.collect_suites(
                [first_root, second_root],
                candidate_closure=closure,
            )
        self.assertEqual(summary["unmatched_callback_start_count"], 1)
        self.assertEqual(summary["unmatched_callback_end_count"], 1)
        self.assertEqual(summary["sidecar_without_local_pair_count"], 2)
        self.assertEqual(summary["integrity_gate"], "FAIL")

    def test_requested_empty_suite_is_rejected(self):
        closure = damage.policy_closure_sha256()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_root = root / "shard_a"
            empty_root = root / "empty_shard"
            empty_root.mkdir()
            trace = self.trace(closure)
            self.write_sidecar(first_root, self.events(trace))
            with self.assertRaises(ValueError):
                collector.collect_suites(
                    [first_root, empty_root],
                    candidate_closure=closure,
                )

    def test_sidecar_without_local_callback_pair_fails_integrity(self):
        closure = damage.policy_closure_sha256()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_sidecar(root, [{"event": "IGNORED"}])
            rows, summary = collector.collect_suite(
                root, candidate_closure=closure
            )
        self.assertEqual(rows, [])
        self.assertEqual(summary["sidecar_without_local_pair_count"], 1)
        self.assertEqual(summary["integrity_gate"], "FAIL")

    def test_path_and_event_game_identity_mismatch_fails_integrity(self):
        closure = damage.policy_closure_sha256()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trace = self.mechanism_trace(
                closure,
                "D-BAD-IDENTITY",
                observation="O-BAD-IDENTITY",
            )
            events = self.events(trace)
            for event in events:
                event["game"] = 1
            self.write_sidecar(root, events, game_file=0)
            _, summary = collector.collect_suite(
                root, candidate_closure=closure
            )
        self.assertEqual(summary["identity_invalid_count"], 2)
        self.assertEqual(summary["reach_decision_count"], 0)
        self.assertEqual(summary["integrity_gate"], "FAIL")

    def test_same_decision_with_different_state_evidence_fails(self):
        closure = damage.policy_closure_sha256()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = self.mechanism_trace(
                closure,
                "D-EVIDENCE-CONFLICT",
                observation="O-EVIDENCE-0",
            )
            second = self.mechanism_trace(
                closure,
                "D-EVIDENCE-CONFLICT",
                observation="O-EVIDENCE-1",
            )
            second["guard_class"] = "FLOOR_BOARDOUT_AVOIDANCE"
            self.write_sidecar(
                root,
                self.events(first, game=0),
                game_file=0,
            )
            self.write_sidecar(
                root,
                self.events(second, game=1),
                game_file=1,
            )
            _, summary = collector.collect_suite(
                root, candidate_closure=closure
            )
        self.assertEqual(summary["decision_conflict_count"], 0)
        self.assertEqual(summary["state_evidence_conflict_count"], 1)
        self.assertEqual(summary["reach_decision_count"], 1)
        self.assertEqual(summary["integrity_gate"], "FAIL")

    def test_wrong_closure_and_unsupported_change_fail(self):
        closure = damage.policy_closure_sha256()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trace = self.trace("0" * 64)
            trace["applied_action"] = [1]
            self.write_sidecar(root, self.events(trace))
            _, summary = collector.collect_suite(
                root, candidate_closure=closure
            )
        self.assertEqual(summary["closure_mismatch_count"], 1)
        self.assertEqual(summary["integrity_gate"], "FAIL")
        self.assertEqual(summary["overall_gate"], "FAIL")

    def test_armed_change_requires_exact_mechanism_linkage(self):
        closure = damage.policy_closure_sha256()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            trace = self.trace(
                closure,
                guard="CAP_LOW_COST_BOARDOUT_AVOIDANCE",
                stage="ARMED",
            )
            trace.update(
                {
                    "applied_action": [2],
                    "proposed_action": [2],
                    "selected_basic": {"card_id": 343, "serial": 81},
                    "parent_post_fingerprint": "P",
                    "candidate_post_fingerprint": "C",
                    "outcome_linkage": {
                        "same_threat_in_both_projections": True,
                        "parent_boardout": True,
                        "candidate_boardout_prevented": True,
                        "tactical_outcome_equal": True,
                    },
                    "decision_id": "D",
                }
            )
            self.write_sidecar(root, self.events(trace))
            _, summary = collector.collect_suite(
                root, candidate_closure=closure
            )
        self.assertEqual(
            summary["unsupported_action_change_count"], 0
        )
        self.assertEqual(summary["integrity_gate"], "PASS")


if __name__ == "__main__":
    unittest.main()
