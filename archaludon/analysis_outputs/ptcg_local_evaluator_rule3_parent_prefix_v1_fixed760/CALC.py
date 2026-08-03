"""Read-only numerical audit for Rule 3 parent-prefix fixed760 outputs.

Run from the repository root on Windows with:
  .venv-rl\Scripts\python.exe archaludon\analysis_outputs\ptcg_local_evaluator_rule3_parent_prefix_v1_fixed760\CALC.py

The script reads frozen specifications and completed raw runner outputs and
prints JSON. It never runs simulations or writes into the raw output tree.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


AUDIT_DIR = Path(__file__).resolve().parent
REPO_ROOT = AUDIT_DIR.parents[2]
SPEC_PATH = REPO_ROOT / "archaludon/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_rule3_parent_prefix_v1/fixed760_spec.json"
EXPECTED_SPEC_SHA256 = "AD0C31C9DF83ADD924D30129A3A99961CFA10F89019731C6CFC61BEBBB02B4D8"
GAME_FIELDS = ("seed", "result", "steps", "turn", "action_errors", "hit_max_steps")
HASH_CACHE: dict[Path, str] = {}


def sha256(path: Path) -> str:
    path = path.resolve()
    cached = HASH_CACHE.get(path)
    if cached is not None:
        return cached
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    value = digest.hexdigest().upper()
    HASH_CACHE[path] = value
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def same_path(left: str | Path, right: str | Path) -> bool:
    return str(Path(left).resolve()).casefold() == str(Path(right).resolve()).casefold()


def option(command: list[str], name: str) -> str:
    index = command.index(name)
    return command[index + 1]


def game_tuple(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row.get(field) for field in GAME_FIELDS)


def without_trace(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "trace"}


def exact_mcnemar_p(gains: int, regressions: int) -> float:
    discordant = gains + regressions
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, index) for index in range(min(gains, regressions) + 1)) / (2**discordant)
    return min(1.0, 2 * tail)


def paired_stats(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    selected = list(rows)
    n = len(selected)
    parent_wins = sum(row["parent_win"] for row in selected)
    candidate_wins = sum(row["candidate_win"] for row in selected)
    gains = sum(row["parent_win"] == 0 and row["candidate_win"] == 1 for row in selected)
    regressions = sum(row["parent_win"] == 1 and row["candidate_win"] == 0 for row in selected)
    both_win = sum(row["parent_win"] == 1 and row["candidate_win"] == 1 for row in selected)
    both_loss = n - gains - regressions - both_win
    return {
        "n": n,
        "parent_wins": parent_wins,
        "parent_losses": n - parent_wins,
        "parent_rate": parent_wins / n,
        "candidate_wins": candidate_wins,
        "candidate_losses": n - candidate_wins,
        "candidate_rate": candidate_wins / n,
        "delta_wins": candidate_wins - parent_wins,
        "delta_rate": (candidate_wins - parent_wins) / n,
        "gains": gains,
        "regressions": regressions,
        "ties": n - gains - regressions,
        "both_win": both_win,
        "both_loss": both_loss,
        "exact_mcnemar_two_sided_p": exact_mcnemar_p(gains, regressions),
    }


def grouped(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> dict[str, Any]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in fields)].append(row)
    return {"|".join(map(str, key)): paired_stats(value) for key, value in sorted(groups.items())}


def tree_digest(root: Path) -> dict[str, Any]:
    ledger: list[str] = []
    total_bytes = 0
    files = sorted((path for path in root.rglob("*") if path.is_file()), key=lambda path: path.relative_to(root).as_posix())
    for path in files:
        size = path.stat().st_size
        total_bytes += size
        ledger.append(f"{path.relative_to(root).as_posix()}\t{size}\t{sha256(path)}\n")
    return {
        "files": len(files),
        "bytes": total_bytes,
        "sha256": hashlib.sha256("".join(ledger).encode("utf-8")).hexdigest().upper(),
        "definition": "SHA256(UTF-8 sorted relative/path\\tbytes\\tfile_sha256\\n)",
    }


def artifact_hash_checks(spec: dict[str, Any], base_spec: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}

    def check(name: str, path: Path, expected: str) -> None:
        actual = sha256(path)
        checks[name] = {"path": rel(path), "expected": expected, "actual": actual, "match": actual == expected}

    check("rule3_spec", SPEC_PATH, EXPECTED_SPEC_SHA256)
    schedule_base_path = REPO_ROOT / spec["schedule_base"]["path"]
    check("schedule_base_spec", schedule_base_path, spec["schedule_base"]["sha256"])
    check("strategy", REPO_ROOT / spec["strategy"]["path"], spec["strategy"]["sha256"])
    check("verification", REPO_ROOT / spec["verification"]["path"], spec["verification"]["sha256"])
    for label in ("baseline", "candidate"):
        policy = spec[label]
        root = REPO_ROOT / policy["path"]
        check(f"{label}_main", root / "main.py", policy["main_sha256"])
        check(f"{label}_deck", root / "deck.csv", policy["deck_sha256"])
    for label, runner in base_spec["runners"].items():
        check(f"runner_{label}", REPO_ROOT / runner["path"], runner["sha256"])
    for relative_path, expected in base_spec["engine"]["files"].items():
        check(f"engine_{relative_path}", REPO_ROOT / base_spec["engine"]["path"] / relative_path, expected)
    for opponent in base_spec["opponents"]:
        root = REPO_ROOT / opponent["path"]
        check(f"opponent_{opponent['label']}_main", root / "main.py", opponent["main_sha256"])
        check(f"opponent_{opponent['label']}_deck", root / "deck.csv", opponent["deck_sha256"])
    return {
        "checks": checks,
        "checked": len(checks),
        "mismatches": [name for name, value in checks.items() if not value["match"]],
    }


def parse_raw(spec: dict[str, Any], base_spec: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_root = REPO_ROOT / spec["output_root"]
    baseline_dir = REPO_ROOT / spec["baseline"]["path"]
    candidate_dir = REPO_ROOT / spec["candidate"]["path"]
    engine_dir = REPO_ROOT / base_spec["engine"]["path"]
    battle_runner = REPO_ROOT / base_spec["runners"]["checked_battle"]["path"]
    python_exe = REPO_ROOT / base_spec["python"]

    role_records: dict[str, dict[tuple[str, str, int, int], dict[str, Any]]] = {
        "baseline_a": {}, "baseline_b": {}, "candidate": {}
    }
    violations: list[str] = []
    manifest_rows = 0
    exit_failures = 0
    start_faults = 0
    action_errors = 0
    exception_rows = 0
    explicit_fault_rows = 0
    max_step_hits = 0
    invalid_results = 0
    total_summary_rows = 0
    runner_discrepancies: list[str] = []
    panel_file_hashes: dict[str, Any] = {}

    panels_by_label = {panel["label"]: panel for panel in base_spec["panels"]}
    for panel_label, panel in panels_by_label.items():
        panel_root = raw_root / panel["output"]
        opponent_paths = {item["label"]: REPO_ROOT / item["path"] for item in panel["opponents"]}
        manifest = read_jsonl(panel_root / "manifest.jsonl")
        manifest_rows += len(manifest)
        expected_manifest = len(opponent_paths) * 2 * 3
        if len(manifest) != expected_manifest:
            violations.append(f"{panel_label}: manifest rows {len(manifest)} != {expected_manifest}")

        seen_runs: set[tuple[str, int, str]] = set()
        for entry in manifest:
            role = entry["role"]
            opponent = entry["opponent"]
            seat = int(entry["seat"])
            run_key = (opponent, seat, role)
            if run_key in seen_runs:
                violations.append(f"{panel_label}: duplicate manifest run {run_key}")
            seen_runs.add(run_key)
            command = entry["command"]
            if int(entry["exit_code"]) != 0:
                exit_failures += 1
            if not same_path(command[0], python_exe):
                violations.append(f"{panel_label}: wrong Python {run_key}")
            if not same_path(command[1], battle_runner):
                violations.append(f"{panel_label}: wrong battle runner {run_key}")
            if "--engine-seed" not in command:
                violations.append(f"{panel_label}: missing --engine-seed {run_key}")
            if not same_path(option(command, "--engine-dir"), engine_dir):
                violations.append(f"{panel_label}: wrong engine {run_key}")
            if int(option(command, "--games")) != int(panel["games_per_seat"]):
                violations.append(f"{panel_label}: wrong games {run_key}")
            if int(option(command, "--max-steps")) != int(base_spec["max_steps"]):
                violations.append(f"{panel_label}: wrong max steps {run_key}")
            if int(option(command, "--seed-base")) != int(panel["seed_base"]):
                violations.append(f"{panel_label}: wrong seed base {run_key}")
            if opponent not in opponent_paths:
                violations.append(f"{panel_label}: unexpected opponent {opponent}")
                continue

            policy_dir = baseline_dir if role in {"baseline_a", "baseline_b"} else candidate_dir
            opponent_dir = opponent_paths[opponent]
            expected_a, expected_b = (policy_dir, opponent_dir) if seat == 0 else (opponent_dir, policy_dir)
            if not same_path(option(command, "--agent-a"), expected_a) or not same_path(option(command, "--agent-b"), expected_b):
                violations.append(f"{panel_label}: policy/player mapping mismatch {run_key}")
            if not same_path(option(command, "--deck-a"), expected_a / "deck.csv") or not same_path(option(command, "--deck-b"), expected_b / "deck.csv"):
                violations.append(f"{panel_label}: deck mapping mismatch {run_key}")

            summary_path = Path(option(command, "--summary")).resolve()
            try:
                summary_path.relative_to(panel_root.resolve())
            except ValueError:
                violations.append(f"{panel_label}: summary outside raw root {run_key}")
            summary_rows = read_jsonl(summary_path)
            total_summary_rows += len(summary_rows)
            if len(summary_rows) != int(panel["games_per_seat"]):
                violations.append(f"{panel_label}: summary count mismatch {run_key}")
            for game_index, summary in enumerate(summary_rows):
                expected_seed = int(panel["seed_base"]) + game_index
                if summary.get("game") != game_index or summary.get("seed") != expected_seed:
                    violations.append(f"{panel_label}: game/seed mismatch {run_key}/{game_index}")
                start_faults += int(summary.get("started") is not True)
                action_errors += int(summary.get("action_errors", 0) or 0)
                exception_rows += int(any(value for key, value in summary.items() if "exception" in key.casefold()))
                explicit_fault_rows += int(any(value for key, value in summary.items() if key.casefold() in {"fault", "faults", "error", "errors", "error_message"}))
                max_step_hits += int(bool(summary.get("hit_max_steps", False)))
                invalid_results += int(summary.get("result") not in (0, 1))
                trace_path = Path(summary["trace"]).resolve()
                if not trace_path.is_file():
                    violations.append(f"{panel_label}: missing trace {run_key}/{game_index}")
                key = (panel_label, opponent, seat, expected_seed)
                if key in role_records[role]:
                    violations.append(f"{panel_label}: duplicate schedule key for role {role}: {key}")
                role_records[role][key] = summary

        expected_runs = {
            (opponent, seat, role)
            for opponent in opponent_paths
            for seat in (0, 1)
            for role in ("baseline_a", "baseline_b", "candidate")
        }
        if seen_runs != expected_runs:
            violations.append(f"{panel_label}: manifest run-key set mismatch")

        panel_file_hashes[panel_label] = {
            "manifest": sha256(panel_root / "manifest.jsonl"),
            "paired_results": sha256(panel_root / "paired_results.csv"),
            "cell_summary": sha256(panel_root / "cell_summary.csv"),
            "report": sha256(panel_root / "report.json"),
        }

    schedule_sets = {role: set(records) for role, records in role_records.items()}
    schedule_equality = schedule_sets["baseline_a"] == schedule_sets["baseline_b"] == schedule_sets["candidate"]
    expected_keys = int(base_spec["expected_total_rows"])
    for role, keys in schedule_sets.items():
        if len(keys) != expected_keys:
            violations.append(f"{role}: unique keys {len(keys)} != {expected_keys}")
    if not schedule_equality:
        violations.append("baseline/candidate schedule sets differ")

    rows: list[dict[str, Any]] = []
    duplicate_summary_matches = 0
    duplicate_full_nontrace_matches = 0
    duplicate_byte_trace_matches = 0
    parent_candidate_game_tuple_matches = 0
    parent_candidate_full_nontrace_matches = 0
    parent_candidate_byte_trace_matches = 0
    parent_candidate_trace_mismatches: list[dict[str, Any]] = []
    for key in sorted(schedule_sets["baseline_a"] & schedule_sets["baseline_b"] & schedule_sets["candidate"]):
        baseline_a = role_records["baseline_a"][key]
        baseline_b = role_records["baseline_b"][key]
        candidate = role_records["candidate"][key]
        duplicate_summary_matches += int(game_tuple(baseline_a) == game_tuple(baseline_b))
        duplicate_full_nontrace_matches += int(without_trace(baseline_a) == without_trace(baseline_b))
        parent_candidate_game_tuple_matches += int(game_tuple(baseline_a) == game_tuple(candidate))
        parent_candidate_full_nontrace_matches += int(without_trace(baseline_a) == without_trace(candidate))
        baseline_a_trace = Path(baseline_a["trace"])
        baseline_b_trace = Path(baseline_b["trace"])
        candidate_trace = Path(candidate["trace"])
        duplicate_byte_trace_matches += int(
            baseline_a_trace.stat().st_size == baseline_b_trace.stat().st_size
            and sha256(baseline_a_trace) == sha256(baseline_b_trace)
        )
        parent_trace_sha = sha256(baseline_a_trace)
        candidate_trace_sha = sha256(candidate_trace)
        candidate_trace_equal = (
            baseline_a_trace.stat().st_size == candidate_trace.stat().st_size
            and parent_trace_sha == candidate_trace_sha
        )
        parent_candidate_byte_trace_matches += int(candidate_trace_equal)
        panel_label, opponent, seat, seed = key
        if not candidate_trace_equal:
            parent_candidate_trace_mismatches.append({
                "panel": panel_label,
                "opponent": opponent,
                "seat": seat,
                "seed": seed,
                "parent_trace": rel(baseline_a_trace),
                "parent_bytes": baseline_a_trace.stat().st_size,
                "parent_sha256": parent_trace_sha,
                "candidate_trace": rel(candidate_trace),
                "candidate_bytes": candidate_trace.stat().st_size,
                "candidate_sha256": candidate_trace_sha,
            })
        rows.append({
            "panel": panel_label,
            "opponent": opponent,
            "seat": seat,
            "seed": seed,
            "parent_result": baseline_a["result"],
            "candidate_result": candidate["result"],
            "parent_steps": baseline_a["steps"],
            "candidate_steps": candidate["steps"],
            "parent_win": int(baseline_a["result"] == seat),
            "candidate_win": int(candidate["result"] == seat),
        })

    # Compare checked paired CSVs and reports with the independent reconstruction.
    reconstructed = {(row["panel"], row["opponent"], row["seat"], row["seed"]): row for row in rows}
    for panel_label, panel in panels_by_label.items():
        panel_root = raw_root / panel["output"]
        paired_rows = list(csv.DictReader((panel_root / "paired_results.csv").open(newline="", encoding="utf-8")))
        panel_expected = int(panel["expected_rows"])
        if len(paired_rows) != panel_expected:
            runner_discrepancies.append(f"{panel_label}: paired CSV rows {len(paired_rows)} != {panel_expected}")
        for csv_row in paired_rows:
            key = (panel_label, csv_row["opponent"], int(csv_row["seat"]), int(csv_row["seed"]))
            raw = reconstructed.get(key)
            if raw is None:
                runner_discrepancies.append(f"{panel_label}: unknown CSV key {key}")
                continue
            expected = {
                "seed_base": str(panel["seed_base"]),
                "opponent": raw["opponent"],
                "seat": str(raw["seat"]),
                "game": str(raw["seed"] - int(panel["seed_base"])),
                "seed": str(raw["seed"]),
                "baseline_result": str(raw["parent_result"]),
                "candidate_result": str(raw["candidate_result"]),
                "baseline_win": str(raw["parent_win"]),
                "candidate_win": str(raw["candidate_win"]),
                "baseline_steps": str(raw["parent_steps"]),
                "candidate_steps": str(raw["candidate_steps"]),
            }
            if csv_row != expected:
                runner_discrepancies.append(f"{panel_label}: CSV mismatch {key}")
        report = read_json(panel_root / "report.json")
        panel_rows = [row for row in rows if row["panel"] == panel_label]
        stats = paired_stats(panel_rows)
        expected_aggregate = {
            "baseline_wins": stats["parent_wins"],
            "candidate_wins": stats["candidate_wins"],
            "games": stats["n"],
            "delta_wins": stats["delta_wins"],
        }
        if report.get("aggregates") != expected_aggregate:
            runner_discrepancies.append(f"{panel_label}: report aggregate mismatch")
        if report.get("valid") is not True or report.get("invalid_reasons") != [] or report.get("duplicate_mismatch_count") != 0:
            runner_discrepancies.append(f"{panel_label}: report validity mismatch")

    if duplicate_summary_matches != expected_keys:
        violations.append(f"duplicate summary matches {duplicate_summary_matches} != {expected_keys}")
    if duplicate_byte_trace_matches != expected_keys:
        violations.append(f"duplicate trace matches {duplicate_byte_trace_matches} != {expected_keys}")
    if exit_failures or start_faults or action_errors or exception_rows or explicit_fault_rows or max_step_hits or invalid_results:
        violations.append("execution health counters are nonzero")
    if runner_discrepancies:
        violations.append("checked runner outputs disagree with raw reconstruction")

    validation = {
        "raw_root": rel(raw_root),
        "row_count": len(rows),
        "unique_keys": {role: len(keys) for role, keys in schedule_sets.items()},
        "schedule_equality": schedule_equality,
        "manifest_rows": manifest_rows,
        "total_summary_rows_all_three_roles": total_summary_rows,
        "exit_failures": exit_failures,
        "start_faults": start_faults,
        "action_errors": action_errors,
        "exception_rows": exception_rows,
        "explicit_fault_rows": explicit_fault_rows,
        "max_step_hits": max_step_hits,
        "invalid_results": invalid_results,
        "duplicate_summary_matches": duplicate_summary_matches,
        "duplicate_full_nontrace_matches": duplicate_full_nontrace_matches,
        "duplicate_byte_trace_matches": duplicate_byte_trace_matches,
        "parent_candidate_game_tuple_matches": parent_candidate_game_tuple_matches,
        "parent_candidate_full_nontrace_matches": parent_candidate_full_nontrace_matches,
        "parent_candidate_byte_trace_matches": parent_candidate_byte_trace_matches,
        "parent_candidate_trace_mismatch_count": len(parent_candidate_trace_mismatches),
        "parent_candidate_trace_mismatches": parent_candidate_trace_mismatches,
        "runner_discrepancies": runner_discrepancies,
        "violations": violations,
        "panel_file_hashes": panel_file_hashes,
    }
    return rows, validation


def gate_results(rows: list[dict[str, Any]], validation: dict[str, Any], base_spec: dict[str, Any]) -> dict[str, Any]:
    gates = base_spec["gates"]
    overall = paired_stats(rows)
    by_seat = grouped(rows, ("seat",))
    by_opponent = grouped(rows, ("opponent",))
    mirror = by_opponent["historical_silver"]
    adjacent = {name: stats for name, stats in by_opponent.items() if name != "historical_silver"}
    seat_drops = {seat: stats["parent_wins"] - stats["candidate_wins"] for seat, stats in by_seat.items()}
    adjacent_drops = {name: stats["parent_wins"] - stats["candidate_wins"] for name, stats in adjacent.items()}
    checks = {
        "unique_schedule_keys": {
            "actual": validation["unique_keys"]["candidate"], "required": gates["unique_schedule_keys"],
            "pass": validation["unique_keys"]["candidate"] == gates["unique_schedule_keys"],
        },
        "duplicate_summary_matches": {
            "actual": validation["duplicate_summary_matches"], "required": gates["duplicate_summary_matches"],
            "pass": validation["duplicate_summary_matches"] == gates["duplicate_summary_matches"],
        },
        "duplicate_byte_trace_matches": {
            "actual": validation["duplicate_byte_trace_matches"], "required": gates["duplicate_byte_trace_matches"],
            "pass": validation["duplicate_byte_trace_matches"] == gates["duplicate_byte_trace_matches"],
        },
        "execution_faults": {"actual": validation["exit_failures"], "required": 0, "pass": validation["exit_failures"] == 0},
        "start_faults": {"actual": validation["start_faults"], "required": 0, "pass": validation["start_faults"] == 0},
        "action_errors": {"actual": validation["action_errors"], "required": 0, "pass": validation["action_errors"] == 0},
        "exceptions": {"actual": validation["exception_rows"], "required": 0, "pass": validation["exception_rows"] == 0},
        "max_step_hits": {"actual": validation["max_step_hits"], "required": 0, "pass": validation["max_step_hits"] == 0},
        "candidate_wins_minimum": {
            "actual": overall["candidate_wins"], "required_minimum": gates["candidate_wins_minimum"],
            "pass": overall["candidate_wins"] >= gates["candidate_wins_minimum"],
        },
        "paired_gains_at_least_regressions": {
            "actual": [overall["gains"], overall["regressions"]], "required": True,
            "pass": overall["gains"] >= overall["regressions"],
        },
        "per_seat_baseline_drop_maximum": {
            "actual_drops": seat_drops, "required_maximum": gates["per_seat_baseline_drop_maximum"],
            "pass": max(seat_drops.values()) <= gates["per_seat_baseline_drop_maximum"],
        },
        "historical_silver_mirror_candidate_wins_minimum": {
            "actual": mirror["candidate_wins"], "required_minimum": gates["historical_silver_mirror_candidate_wins_minimum"],
            "pass": mirror["candidate_wins"] >= gates["historical_silver_mirror_candidate_wins_minimum"],
        },
        "adjacent_opponent_baseline_drop_maximum": {
            "actual_drops": adjacent_drops, "required_maximum": gates["adjacent_opponent_baseline_drop_maximum"],
            "pass": max(adjacent_drops.values()) <= gates["adjacent_opponent_baseline_drop_maximum"],
        },
        "strengthened_candidate_wins_minimum": {
            "actual": overall["candidate_wins"], "required_minimum": gates["strengthened_candidate_wins_minimum"],
            "pass": overall["candidate_wins"] >= gates["strengthened_candidate_wins_minimum"],
        },
        "strengthened_both_seats_nonworse": {
            "actual_drops": seat_drops, "required": True,
            "pass": all(drop <= 0 for drop in seat_drops.values()),
        },
    }
    return {
        "inherited_from_schedule_base": checks,
        "passed": [name for name, result in checks.items() if result["pass"]],
        "failed": [name for name, result in checks.items() if not result["pass"]],
    }


def main() -> None:
    spec = read_json(SPEC_PATH)
    base_spec_path = REPO_ROOT / spec["schedule_base"]["path"]
    base_spec = read_json(base_spec_path)
    artifacts = artifact_hash_checks(spec, base_spec)
    rows, validation = parse_raw(spec, base_spec)
    overall = paired_stats(rows)
    by_panel = grouped(rows, ("panel",))
    by_opponent = grouped(rows, ("opponent",))
    by_seat = grouped(rows, ("seat",))
    by_cell = grouped(rows, ("opponent", "seat"))
    adjacent_opponents = {key: value for key, value in by_opponent.items() if key != "historical_silver"}
    adjacent_cells = {key: value for key, value in by_cell.items() if not key.startswith("historical_silver|")}
    raw_root = REPO_ROOT / spec["output_root"]

    output = {
        "calculation": {
            "script": rel(Path(__file__)),
            "policy_player_mapping": {
                "seat0": "policy is agent A/player 0; policy win iff result == 0",
                "seat1": "policy is agent B/player 1; policy win iff result == 1",
            },
            "trace_equality": "equal byte length and SHA-256",
        },
        "specification": {
            "path": rel(SPEC_PATH),
            "sha256": sha256(SPEC_PATH),
            "literal_gates": spec.get("gates"),
            "schedule_base_path": rel(base_spec_path),
            "schedule_base_sha256": sha256(base_spec_path),
        },
        "artifact_hashes": artifacts,
        "validation": validation,
        "statistics": {
            "overall": overall,
            "by_panel": by_panel,
            "by_opponent": by_opponent,
            "by_seat": by_seat,
            "by_opponent_seat": by_cell,
            "floors": {
                "historical_mirror": by_opponent["historical_silver"],
                "adjacent_panel": by_panel["adjacent_population"],
                "lowest_adjacent_opponent": min(adjacent_opponents.items(), key=lambda item: item[1]["candidate_rate"]),
                "lowest_adjacent_opponent_seat": min(adjacent_cells.items(), key=lambda item: item[1]["candidate_rate"]),
            },
        },
        "gates": gate_results(rows, validation, base_spec),
        "raw_output": {
            "path": rel(raw_root),
            "tree": tree_digest(raw_root),
        },
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
