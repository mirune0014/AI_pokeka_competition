from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
COLLECTOR_PATH = HERE / "verification" / "c2_sidecar_collector.py"
SPEC = importlib.util.spec_from_file_location(
    "_c2_sidecar_collector", COLLECTOR_PATH
)
collector = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(collector)


class C2SidecarCollectorTests(unittest.TestCase):
    def test_collector_requires_fix4b_rule(self):
        self.assertEqual(
            collector.RULE,
            "V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4B",
        )

    def trace(self, fingerprint, route_class):
        action = [0]
        return {
            "schema_version": 4,
            "rule_version": collector.RULE,
            "raw_parent_action": action,
            "applied_action": action,
            "action_python_type": "builtins.list",
            "action_identity": {
                "value_equal": True,
                "type_equal": True,
                "order_equal": True,
                "returned_parent_object_unchanged": True,
            },
            "metric_exception": None,
            "observation_fingerprint": fingerprint,
            "route_rows": [
                {
                    "line_id": 10,
                    "primary_distance": {
                        "route_class": route_class,
                        "turn_delay": 0,
                        "main_actions": 0,
                        "forced_prompts": 0,
                    },
                    "fallback_attack_distance": {
                        "route_class": route_class,
                        "turn_delay": 0,
                        "main_actions": 0,
                        "forced_prompts": 0,
                    },
                }
            ],
            "best_primary_route": {"route_class": route_class},
            "best_fallback_route": {"route_class": route_class},
            "unsupported_reasons": [],
        }

    def events(
        self,
        *,
        version,
        opponent,
        seat,
        ordinal,
        fingerprint,
        route_class,
        seed=101,
        game=0,
    ):
        common = {
            "version": version,
            "opponent": opponent,
            "policy_seat": seat,
            "seed_base": 100,
            "seed": seed,
            "game": game,
            "callback_ordinal": ordinal,
        }
        return [
            {**common, "event": "CALL_START", "observation": {}},
            {
                **common,
                "event": "CALL_END",
                "selected_action": [0],
                "structurally_valid": True,
                "exception": None,
                "version_trace_name": "LAST_STAGED_POLICY_TRACE",
                "version_trace": self.trace(
                    fingerprint, route_class
                ),
            },
        ]

    def write_sidecar(
        self,
        root,
        *,
        opponent,
        seat,
        events,
        game=0,
    ):
        path = (
            root
            / "runs"
            / "candidate"
            / opponent
            / "seed_100"
            / f"seat_{seat}"
            / "sidecars"
            / f"game_{game:04d}.jsonl"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(
                json.dumps(row, sort_keys=True) + "\n"
                for row in events
            ),
            encoding="utf-8",
            newline="\n",
        )
        return path

    def test_raw_rows_hashes_and_duplicates_are_deterministic(self):
        with tempfile.TemporaryDirectory(
            dir=HERE / "verification"
        ) as directory:
            root = Path(directory)
            events = []
            events.extend(
                self.events(
                    version="candidate",
                    opponent="marnie",
                    seat=0,
                    ordinal=0,
                    fingerprint="A" * 64,
                    route_class="CERTIFIED",
                )
            )
            events.extend(
                self.events(
                    version="candidate",
                    opponent="marnie",
                    seat=0,
                    ordinal=1,
                    fingerprint="A" * 64,
                    route_class="CERTIFIED",
                )
            )
            path = self.write_sidecar(
                root,
                opponent="marnie",
                seat=0,
                events=events,
            )
            rows1, summary1 = collector.collect_suite(root)
            rows2, summary2 = collector.collect_suite(root)
            self.assertEqual(rows1, rows2)
            self.assertEqual(summary1, summary2)
            self.assertEqual(summary1["input_file_count"], 1)
            self.assertEqual(
                summary1["input_files"][0]["sha256"],
                collector._sha256(path),
            )
            self.assertEqual(summary1["unique_state_count"], 1)
            self.assertEqual(
                summary1["duplicate_decision_count"], 1
            )
            self.assertTrue(
                summary1[
                    "duplicate_decisions_excluded_from_unique_states"
                ]
            )
            self.assertEqual(
                summary1["route_class_unique_state_counts"][
                    "CERTIFIED"
                ],
                1,
            )
            self.assertEqual(
                summary1["overall_gate"],
                "INSUFFICIENT_EVIDENCE",
            )
            self.assertFalse(summary1["win_rate_aggregated"])
            self.assertTrue(
                all(
                    row["trace_rule_version"] == collector.RULE
                    and row["action_identity_ok"]
                    for row in rows1
                )
            )

    def test_coverage_gate_counts_unique_states_not_callbacks(self):
        with tempfile.TemporaryDirectory(
            dir=HERE / "verification"
        ) as directory:
            root = Path(directory)
            opponents = (
                "marnie",
                "historical_silver",
                "alakazam_mirror",
            )
            classes = collector.ROUTE_CLASSES
            grouped = {}
            for index in range(52):
                opponent = opponents[index % len(opponents)]
                seat = index % 2
                grouped.setdefault((opponent, seat), []).extend(
                    self.events(
                        version="candidate",
                        opponent=opponent,
                        seat=seat,
                        ordinal=index,
                        fingerprint=f"{index:064X}",
                        route_class=classes[index % 4],
                        seed=1000 + index,
                    )
                )
            for game, ((opponent, seat), events) in enumerate(
                sorted(grouped.items())
            ):
                self.write_sidecar(
                    root,
                    opponent=opponent,
                    seat=seat,
                    events=events,
                    game=game,
                )
            rows, summary = collector.collect_suite(root)
            self.assertGreater(len(rows), 52)
            self.assertEqual(summary["unique_state_count"], 52)
            self.assertEqual(summary["seat_count"], 2)
            self.assertEqual(summary["opponent_count"], 3)
            self.assertEqual(
                summary["non_mirror_opponent_count"], 2
            )
            self.assertTrue(
                all(
                    count >= 5
                    for count in summary[
                        "route_class_unique_state_counts"
                    ].values()
                )
            )
            self.assertEqual(summary["action_identity_gate"], "PASS")
            self.assertEqual(summary["metric_exception_gate"], "PASS")
            self.assertEqual(summary["trace_integrity_gate"], "PASS")
            self.assertEqual(summary["coverage_gate"], "PASS")
            self.assertEqual(summary["overall_gate"], "PASS")

    def test_action_mismatch_and_duplicate_callback_key_fail(self):
        with tempfile.TemporaryDirectory(
            dir=HERE / "verification"
        ) as directory:
            root = Path(directory)
            events = self.events(
                version="candidate",
                opponent="marnie",
                seat=0,
                ordinal=0,
                fingerprint="B" * 64,
                route_class="UNKNOWN",
            )
            duplicate = json.loads(json.dumps(events[1]))
            duplicate["selected_action"] = [1]
            events.append(duplicate)
            self.write_sidecar(
                root,
                opponent="marnie",
                seat=0,
                events=events,
            )
            _, summary = collector.collect_suite(root)
            self.assertEqual(
                summary["duplicate_callback_key_count"], 1
            )
            self.assertEqual(
                summary["action_identity_failure_count"], 1
            )
            self.assertEqual(summary["action_identity_gate"], "FAIL")
            self.assertEqual(summary["overall_gate"], "FAIL")


if __name__ == "__main__":
    unittest.main()
