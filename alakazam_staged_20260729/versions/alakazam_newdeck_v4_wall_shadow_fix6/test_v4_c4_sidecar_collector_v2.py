from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from verification import c4_sidecar_collector as frozen
from verification import c4_sidecar_collector_v2 as amended


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
CLOSURE = (
    "FA46897E4762CB1B55C9DED36EC3A06CA9CF4F9FE7C4233BE8414CC25D86DF4E"
)
NEGATIVE_SIDECAR = (
    REPO_ROOT
    / "alakazam_staged_20260729"
    / "metrics"
    / "formal_v4_c4_wall_shadow_fix6_trace_a"
    / "runs"
    / "c4"
    / "alakazam_mirror"
    / "seed_202608500"
    / "seat_0"
    / "sidecars"
    / "game_0005.jsonl"
)


def events() -> list[dict]:
    return [
        json.loads(line)
        for line in NEGATIVE_SIDECAR.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def negative_pair() -> tuple[dict, dict, dict]:
    rows = events()
    start = next(
        row
        for row in rows
        if row.get("event") == "CALL_START"
        and row.get("callback_ordinal") == 10
    )
    end = next(
        row
        for row in rows
        if row.get("event") == "CALL_END"
        and row.get("callback_ordinal") == 10
    )
    material = frozen._canonical_public_state_material(start["observation"])
    if material is None:
        raise AssertionError("durable observation is not canonical")
    return material, end, end["version_trace"]


class NoLiveLineErratumTests(unittest.TestCase):
    def test_exact_negative_shape_is_monotonically_excluded(self):
        material, end, trace = negative_pair()
        self.assertTrue(amended._negative_shape(trace))
        self.assertEqual(
            trace["candidate_rows"][0]["certification"],
            "PRESERVE_CHANCE",
        )
        self.assertIsNone(trace["protected_line"])
        self.assertEqual(
            amended.amended_decision_class(trace),
            None,
        )
        frozen_faults = frozen._trace_schema_faults(
            trace,
            CLOSURE,
            material,
        )
        self.assertTrue(frozen_faults["sparse"])
        amended_faults = amended.amended_trace_schema_faults(
            trace,
            CLOSURE,
            material,
        )
        self.assertFalse(any(amended_faults.values()), amended_faults)
        self.assertTrue(all(frozen._action_faults(end, trace).values()))

    def test_missing_or_mutated_evidence_remains_fatal(self):
        material, _, trace = negative_pair()

        missing = copy.deepcopy(trace)
        missing.pop("threat")
        self.assertTrue(
            any(
                amended.amended_trace_schema_faults(
                    missing,
                    CLOSURE,
                    material,
                ).values()
            )
        )

        raw_faults = amended.amended_trace_schema_faults(
            trace,
            CLOSURE,
            {},
        )
        self.assertTrue(raw_faults["raw_state"])

        strict = copy.deepcopy(trace)
        strict["candidate_rows"][1]["certification"] = "STRICT"
        strict["candidate_rows"][1]["wall_class"] = frozen.STRICT
        self.assertFalse(amended._negative_shape(strict))
        self.assertTrue(
            any(
                amended.amended_trace_schema_faults(
                    strict,
                    CLOSURE,
                    material,
                ).values()
            )
        )

        wall_chance = copy.deepcopy(trace)
        wall_chance["candidate_rows"][1]["certification"] = (
            "PRESERVE_CHANCE"
        )
        wall_chance["candidate_rows"][1]["wall_class"] = frozen.CHANCE
        self.assertFalse(amended._negative_shape(wall_chance))

        projection = copy.deepcopy(trace)
        projection["wall_projection"]["chosen"] = {"kind": "fabricated"}
        self.assertFalse(amended._negative_shape(projection))

        duplicate = copy.deepcopy(trace)
        duplicate["candidate_rows"][1]["rejection_codes"].append(
            duplicate["candidate_rows"][1]["rejection_codes"][0]
        )
        self.assertFalse(amended._negative_shape(duplicate))

    def test_action_mutation_is_not_hidden(self):
        _, end, trace = negative_pair()
        mutated = copy.deepcopy(end)
        mutated["selected_action"] = list(mutated["selected_action"]) + [999]
        faults = frozen._action_faults(mutated, trace)
        self.assertFalse(faults["value"])

    def test_single_durable_game_has_no_integrity_fault_after_exclusion(self):
        with tempfile.TemporaryDirectory(prefix="c4-v2-test-") as name:
            root = Path(name)
            destination = (
                root
                / "runs"
                / "c4"
                / "alakazam_mirror"
                / "seed_202608500"
                / "seat_0"
                / "sidecars"
                / "game_0005.jsonl"
            )
            destination.parent.mkdir(parents=True)
            shutil.copyfile(NEGATIVE_SIDECAR, destination)
            _, summary = amended.collect_suite(
                [root],
                expected_candidate_closure=CLOSURE,
            )
        self.assertEqual(summary["input_file_count"], 1)
        self.assertEqual(summary["callback_start_count"], 72)
        self.assertEqual(summary["callback_end_count"], 72)
        self.assertEqual(summary["sparse_trace_or_row_fault_count"], 0)
        self.assertEqual(
            summary["negative_only_no_live_exclusion_count"],
            9,
        )
        self.assertEqual(
            summary["negative_only_duplicate_diagnostic_row_count"],
            9,
        )
        self.assertEqual(summary["integrity_gate"], "PASS")
        self.assertEqual(summary["overall_gate"], "INSUFFICIENT_EVIDENCE")


if __name__ == "__main__":
    unittest.main()
