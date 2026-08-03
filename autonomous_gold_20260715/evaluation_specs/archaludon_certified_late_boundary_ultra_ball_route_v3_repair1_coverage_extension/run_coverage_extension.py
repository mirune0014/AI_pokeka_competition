from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE / "coverage_extension_spec.json"
RULE3_ID = "CERTIFIED_LATE_BOUNDARY_ULTRA_BALL_ROUTE_V3"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def checked_file(relative: str, expected: str) -> Path:
    path = ROOT / relative
    if not path.is_file():
        raise AssertionError(f"missing frozen file: {relative}")
    actual = sha256(path)
    if actual != expected:
        raise AssertionError(
            f"hash mismatch: {relative}: expected {expected}, got {actual}"
        )
    return path


def load_and_validate() -> tuple[dict, dict]:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    base_path = checked_file(
        spec["schedule_base"]["path"],
        spec["schedule_base"]["sha256"],
    )
    base = json.loads(base_path.read_text(encoding="utf-8"))
    checked_file(spec["strategy"]["path"], spec["strategy"]["sha256"])
    checked_file(
        spec["verification"]["path"], spec["verification"]["sha256"]
    )
    checked_file(
        spec["independent_numerical"]["path"],
        spec["independent_numerical"]["sha256"],
    )
    for name in ("parent", "candidate", "diagnostic_candidate"):
        policy = spec[name]
        checked_file(f"{policy['path']}/main.py", policy["main_sha256"])
        checked_file(f"{policy['path']}/deck.csv", policy["deck_sha256"])
    for opponent in spec["opponents"]:
        checked_file(f"{opponent['path']}/main.py", opponent["main_sha256"])
        checked_file(f"{opponent['path']}/deck.csv", opponent["deck_sha256"])
    for runner in base["runners"].values():
        checked_file(runner["path"], runner["sha256"])
    for relative, expected in base["engine"]["files"].items():
        checked_file(f"{base['engine']['path']}/{relative}", expected)
    if not (ROOT / base["python"]).is_file():
        raise AssertionError("missing frozen Python")
    expected = (
        (spec["seed_last"] - spec["seed_first"] + 1)
        * len(spec["opponents"])
        * len(spec["seats"])
    )
    if expected != spec["max_primary_keys"]:
        raise AssertionError((expected, spec["max_primary_keys"]))
    return spec, base


def pair_command(
    spec: dict,
    base: dict,
    opponent: dict,
    seed: int,
    output: Path,
) -> list[str]:
    return [
        str(ROOT / base["python"]),
        str(ROOT / base["runners"]["trace_preservation_wrapper"]["path"]),
        "--engine-dir",
        str(ROOT / base["engine"]["path"]),
        "--baseline",
        str(ROOT / spec["parent"]["path"]),
        "--candidate",
        str(ROOT / spec["diagnostic_candidate"]["path"]),
        "--opponent",
        f"{opponent['label']}={ROOT / opponent['path']}",
        "--games-per-seat",
        "1",
        "--seed-base",
        str(seed),
        "--max-steps",
        str(spec["max_steps"]),
        "--output-dir",
        str(output),
    ]


def telemetry_rows(output_root: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(output_root.glob("pairs/*/telemetry.jsonl")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                row = json.loads(raw)
                row["telemetry_file"] = str(path.relative_to(output_root))
                rows.append(row)
    return rows


def coverage_status(spec: dict, output_root: Path) -> dict:
    rows = telemetry_rows(output_root)
    carry = spec["fixed160_carry_in"]
    starts = []
    completions = []
    fault_rows = []
    for row in rows:
        telemetry = row.get("telemetry") or {}
        owner_before = telemetry.get("owner_before")
        owner_after = telemetry.get("owner_after") or {}
        if (
            telemetry.get("selected_source") == RULE3_ID
            and owner_before is None
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
            fault_rows.append(row)
    extension_routes = {
        (row.get("telemetry") or {}).get("rule3_route_kind")
        for row in completions
    }
    start_boundaries = {
        (row.get("telemetry") or {}).get("rule3_parent_boundary")
        for row in starts
    }
    completed_seats = set(carry["completed_seats"])
    completed_seats.update(
        row.get("seat") for row in completions if row.get("seat") in (0, 1)
    )
    total_starts = carry["natural_starts"] + len(starts)
    total_completions = carry["completed_starts"] + len(completions)
    total_faults = carry["faults"] + len(fault_rows)
    active_complete = carry["completed_active_ex"] or bool(
        {"ACTIVE_EX_FUEL_ROUTE", "ACTIVE_EX_SEARCH_ROUTE"} & extension_routes
    )
    turbo_complete = carry["completed_turbo"] or (
        "TURBO_DURALUDON_ROUTE" in extension_routes
    )
    attack_or_end = carry["attack_or_end_first_difference"] or (
        "OPPORTUNITY_CLOSING" in start_boundaries
    )
    gates = spec["stop_gates"]
    mechanical_coverage_met = all(
        (
            total_starts >= gates["minimum_cumulative_starts"],
            active_complete if gates["require_active_ex_completion"] else True,
            turbo_complete if gates["require_turbo_completion"] else True,
            attack_or_end
            if gates["require_attack_or_end_first_difference"]
            else True,
            completed_seats == {0, 1} if gates["require_both_seats"] else True,
            total_completions == total_starts,
            total_faults <= gates["maximum_faults"],
        )
    )
    return {
        "purpose": spec["purpose"],
        "extension_starts": len(starts),
        "extension_completions": len(completions),
        "extension_fault_rows": len(fault_rows),
        "cumulative_starts": total_starts,
        "cumulative_completions": total_completions,
        "cumulative_faults": total_faults,
        "completed_seats": sorted(completed_seats),
        "completed_active_ex": active_complete,
        "completed_turbo": turbo_complete,
        "attack_or_end_first_difference": attack_or_end,
        "extension_routes": sorted(route for route in extension_routes if route),
        "start_parent_boundaries": sorted(
            boundary for boundary in start_boundaries if boundary
        ),
        "mechanical_coverage_met": mechanical_coverage_met,
        "qualitative_first_difference_audit_required": True,
        "strength_interpretation_forbidden": True,
    }


def validate_pair_output(output: Path, opponent: str, seed: int) -> dict:
    report_path = output / "report.json"
    paired_path = output / "paired_results.csv"
    manifest_path = output / "manifest.jsonl"
    telemetry_path = output / "telemetry.jsonl"
    for path in (report_path, paired_path, manifest_path, telemetry_path):
        if not path.is_file():
            raise AssertionError(f"missing pair output: {path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("valid") is not True or report.get("invalid_reasons"):
        raise AssertionError(report)
    if report.get("duplicate_mismatch_count") != 0:
        raise AssertionError(report)
    with paired_path.open("r", encoding="utf-8", newline="") as stream:
        paired = list(csv.DictReader(stream))
    if len(paired) != 2:
        raise AssertionError((opponent, seed, len(paired)))
    keys = {(row["opponent"], int(row["seat"]), int(row["seed"])) for row in paired}
    if keys != {(opponent, 0, seed), (opponent, 1, seed)}:
        raise AssertionError((keys, opponent, seed))
    return {
        "panel": "coverage_extension",
        "opponent": opponent,
        "seed": seed,
        "seats": [0, 1],
        "primary_keys": 2,
        "valid": True,
        "duplicate_mismatch_count": 0,
        "output": str(output),
        "report_sha256": sha256(report_path),
        "paired_results_sha256": sha256(paired_path),
        "manifest_sha256": sha256(manifest_path),
        "telemetry_sha256": sha256(telemetry_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    spec, base = load_and_validate()
    output_root = ROOT / spec["output_root"]
    if output_root.exists():
        raise AssertionError(f"refusing existing destination: {output_root}")
    plan = [
        {
            "seed": seed,
            "opponent": opponent["label"],
            "primary_keys": 2,
        }
        for seed in range(spec["seed_first"], spec["seed_last"] + 1)
        for opponent in spec["opponents"]
    ]
    print(
        json.dumps(
            {
                "spec_sha256": sha256(SPEC_PATH),
                "runner_sha256": sha256(Path(__file__)),
                "purpose": spec["purpose"],
                "maximum_primary_keys": spec["max_primary_keys"],
                "pair_jobs": len(plan),
                "first_jobs": plan[:4],
                "last_jobs": plan[-4:],
                "execute": args.execute,
            },
            indent=2,
        )
    )
    if not args.execute:
        return
    output_root.mkdir(parents=True)
    manifest_rows = []
    status = coverage_status(spec, output_root)
    stopped_early = False
    for index, item in enumerate(plan):
        opponent = next(
            row for row in spec["opponents"] if row["label"] == item["opponent"]
        )
        pair_output = (
            output_root
            / "pairs"
            / f"{index:04d}_{item['seed']}_{item['opponent']}"
        )
        telemetry_path = pair_output / "telemetry.jsonl"
        command = pair_command(spec, base, opponent, item["seed"], pair_output)
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["RULE3_V3_TELEMETRY"] = str(telemetry_path)
        completed = subprocess.run(command, cwd=ROOT, env=env, check=False)
        if completed.returncode:
            raise SystemExit(completed.returncode)
        manifest_rows.append(
            validate_pair_output(pair_output, item["opponent"], item["seed"])
        )
        manifest_path = output_root / "extension_manifest.jsonl"
        manifest_path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in manifest_rows),
            encoding="utf-8",
        )
        status = coverage_status(spec, output_root)
        status.update(
            {
                "pair_jobs_completed": len(manifest_rows),
                "primary_keys_completed": 2 * len(manifest_rows),
                "last_seed": item["seed"],
                "last_opponent": item["opponent"],
            }
        )
        (output_root / "coverage_status.json").write_text(
            json.dumps(status, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if status["mechanical_coverage_met"]:
            stopped_early = True
            break
    completion = {
        "spec_sha256": sha256(SPEC_PATH),
        "runner_sha256": sha256(Path(__file__)),
        "stopped_early": stopped_early,
        "exhausted_schedule": len(manifest_rows) == len(plan),
        "pair_jobs_completed": len(manifest_rows),
        "primary_keys_completed": 2 * len(manifest_rows),
        "coverage_status": status,
        "interpretation": spec["interpretation"],
    }
    (output_root / "RUN_COMPLETE.json").write_text(
        json.dumps(completion, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(completion, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
