from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUTPUT = ROOT / (
    "autonomous_gold_20260715/evaluations/"
    "archaludon_certified_late_boundary_ultra_ball_route_v3_repair1/"
    "coverage_extension_314159265_314159304"
)
SPEC_PATH = ROOT / (
    "autonomous_gold_20260715/evaluation_specs/"
    "archaludon_certified_late_boundary_ultra_ball_route_v3_repair1_coverage_extension/"
    "coverage_extension_spec.json"
)
DESTINATION = Path(__file__).resolve().parent / "ROOT_RECOMPUTE.json"
RULE3_ID = "CERTIFIED_LATE_BOUNDARY_ULTRA_BALL_ROUTE_V3"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    manifest_rows = [
        json.loads(line)
        for line in (OUTPUT / "extension_manifest.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    expected_pairs = [
        (seed, opponent["label"])
        for seed in range(spec["seed_first"], spec["seed_last"] + 1)
        for opponent in spec["opponents"]
    ]
    observed_pairs = [(row["seed"], row["opponent"]) for row in manifest_rows]
    if observed_pairs != expected_pairs:
        raise AssertionError("pair schedule mismatch")

    primary_keys = []
    telemetry_rows = []
    report_invalid = 0
    duplicate_mismatch = 0
    manifest_hash_mismatch = 0
    candidate_trace_mismatch = 0
    outcome_mismatch = 0
    step_mismatch = 0
    outcome_mismatch_keys = []
    step_mismatch_keys = []
    trace_mismatch_keys = []

    for row in manifest_rows:
        pair = Path(row["output"])
        files = {
            "report_sha256": pair / "report.json",
            "paired_results_sha256": pair / "paired_results.csv",
            "manifest_sha256": pair / "manifest.jsonl",
            "telemetry_sha256": pair / "telemetry.jsonl",
        }
        for field, path in files.items():
            if sha256(path) != row[field]:
                manifest_hash_mismatch += 1
        report = json.loads((pair / "report.json").read_text(encoding="utf-8"))
        if report.get("valid") is not True or report.get("invalid_reasons"):
            report_invalid += 1
        duplicate_mismatch += int(report.get("duplicate_mismatch_count", -1))
        with (pair / "paired_results.csv").open(
            "r", encoding="utf-8", newline=""
        ) as stream:
            paired = list(csv.DictReader(stream))
        if len(paired) != 2:
            raise AssertionError((pair, len(paired)))
        for result in paired:
            key = (
                "coverage_extension",
                result["opponent"],
                int(result["seat"]),
                int(result["seed"]),
            )
            primary_keys.append(key)
            if result["baseline_result"] != result["candidate_result"]:
                outcome_mismatch += 1
                outcome_mismatch_keys.append(key)
            if result["baseline_steps"] != result["candidate_steps"]:
                step_mismatch += 1
                step_mismatch_keys.append(
                    {
                        "key": key,
                        "baseline_steps": int(result["baseline_steps"]),
                        "candidate_steps": int(result["candidate_steps"]),
                    }
                )
            traces = pair / "throwaway_traces"
            baseline = next(
                traces.glob(f"*_p{result['seat']}_baseline_a/game_0000.jsonl")
            )
            candidate = next(
                traces.glob(f"*_p{result['seat']}_candidate/game_0000.jsonl")
            )
            baseline_trace_sha = sha256(baseline)
            candidate_trace_sha = sha256(candidate)
            if baseline_trace_sha != candidate_trace_sha:
                candidate_trace_mismatch += 1
                trace_mismatch_keys.append(
                    {
                        "key": key,
                        "baseline_trace_sha256": baseline_trace_sha,
                        "candidate_trace_sha256": candidate_trace_sha,
                        "baseline_trace": str(baseline),
                        "candidate_trace": str(candidate),
                    }
                )
        for raw in (pair / "telemetry.jsonl").read_text(encoding="utf-8").splitlines():
            if raw.strip():
                telemetry_rows.append(json.loads(raw))

    starts = []
    completions = []
    faults = []
    for row in telemetry_rows:
        telemetry = row.get("telemetry") or {}
        owner_after = telemetry.get("owner_after") or {}
        if (
            telemetry.get("selected_source") == RULE3_ID
            and telemetry.get("owner_before") is None
            and owner_after.get("owner") == RULE3_ID
            and owner_after.get("stage") == "ULTRA_PLAY_EMITTED"
        ):
            starts.append(row)
        if telemetry.get("rule3_completed") is True:
            completions.append(row)
        if (
            telemetry.get("irreversible_abort_fault")
            or telemetry.get("rule3_fault_latched")
            or telemetry.get("rule3_run_failed")
        ):
            faults.append(row)

    expected_keys = {
        ("coverage_extension", opponent["label"], seat, seed)
        for seed in range(spec["seed_first"], spec["seed_last"] + 1)
        for opponent in spec["opponents"]
        for seat in spec["seats"]
    }
    observed_keys = set(primary_keys)
    result = {
        "spec_sha256": sha256(SPEC_PATH),
        "pair_rows": len(manifest_rows),
        "expected_pair_rows": len(expected_pairs),
        "primary_key_rows": len(primary_keys),
        "unique_primary_keys": len(observed_keys),
        "missing_primary_keys": len(expected_keys - observed_keys),
        "extra_primary_keys": len(observed_keys - expected_keys),
        "duplicate_primary_key_rows": len(primary_keys) - len(observed_keys),
        "manifest_hash_mismatches": manifest_hash_mismatch,
        "invalid_pair_reports": report_invalid,
        "duplicate_mismatches": duplicate_mismatch,
        "baseline_candidate_outcome_mismatches": outcome_mismatch,
        "baseline_candidate_step_mismatches": step_mismatch,
        "baseline_candidate_trace_mismatches": candidate_trace_mismatch,
        "outcome_mismatch_keys": outcome_mismatch_keys,
        "step_mismatch_keys": step_mismatch_keys,
        "trace_mismatch_keys": trace_mismatch_keys,
        "telemetry_rows": len(telemetry_rows),
        "extension_starts": len(starts),
        "extension_completions": len(completions),
        "extension_fault_rows": len(faults),
        "extension_routes": sorted(
            {
                (row.get("telemetry") or {}).get("rule3_route_kind")
                for row in completions
                if (row.get("telemetry") or {}).get("rule3_route_kind")
            }
        ),
        "start_parent_boundaries": sorted(
            {
                (row.get("telemetry") or {}).get("rule3_parent_boundary")
                for row in starts
                if (row.get("telemetry") or {}).get("rule3_parent_boundary")
            }
        ),
        "mechanically_exact_parent_behavior": (
            outcome_mismatch == 0
            and step_mismatch == 0
            and candidate_trace_mismatch == 0
        ),
        "coverage_gate_met": False,
        "strength_interpretation": "FORBIDDEN_COVERAGE_ONLY",
    }
    DESTINATION.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
