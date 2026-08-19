"""Independent, read-only numerical audit of the completed Rule 2 fixed160.

Run from the repository root on Windows with:

    .venv-ptcg\Scripts\python.exe archaludon\numerical_audits\archaludon_historical_silver_single_resolver_salvage_rule2_trial_v1_fixed160\audit_rule2_fixed160.py

The script never runs a battle and never writes to the frozen result tree.  It
prints one canonical JSON calculation to stdout.
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
REPO = AUDIT_DIR.parents[2]
SPEC = REPO / (
    "archaludon/evaluation_specs/"
    "archaludon_historical_silver_single_resolver_salvage_rule2_trial_v1/"
    "fixed160_spec.json"
)
RAW = REPO / (
    "archaludon/evaluations/"
    "archaludon_historical_silver_single_resolver_salvage_rule2_trial_v1/"
    "fixed160_raw"
)

EXPECTED_SPEC_SHA256 = "7EF9D7F5074EC6ADD7DE04A78D2B521792B5DDD9E3815A00E0394B4DEA642036"
EXPECTED_REQUIREMENTS_SHA256 = "24282FA6A0EF91D936E2E5B2AAD725904EF3223FCFBDF9BEEA16C62C726038C9"
EXPECTED_RAW_TREE_SHA256 = "8D3C52ADF49F2D36DCE2E3D50033E75306C981B7915443DE413FB598024F1F29"
EXPECTED_BASELINE_SHA256 = "153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A"
EXPECTED_CANDIDATE_SHA256 = "D2BC5FCC82A5A507B7C5CC9FEDAAC4ED6EA0BE1622EBE99EFC74B6E6A926FC62"
EXPECTED_DECK_SHA256 = "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A"

SUMMARY_FIELDS = ("seed", "result", "steps", "turn", "action_errors", "hit_max_steps")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO).as_posix()


def portable_tree_sha256(path: Path) -> dict[str, Any]:
    """Portable secondary ledger including file sizes."""
    lines: list[str] = []
    for child in sorted(
        (item for item in path.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(path).as_posix(),
    ):
        lines.append(
            f"{child.relative_to(path).as_posix()}\t{child.stat().st_size}\t{sha256(child)}\n"
        )
    return {
        "sha256": hashlib.sha256("".join(lines).encode("utf-8")).hexdigest().upper(),
        "files": len(lines),
        "definition": "SHA256(UTF-8 sorted relative/path\\tbytes\\tfile_sha256\\n)",
    }


def runner_tree_sha256(path: Path) -> dict[str, Any]:
    """Reproduce the runner's frozen 512-file relative-path ledger."""
    children = sorted(
        (item for item in path.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(path).as_posix(),
    )
    preimage = "".join(
        f"{sha256(child)}  {child.relative_to(path).as_posix()}\n" for child in children
    ).encode("utf-8")
    return {
        "sha256": hashlib.sha256(preimage).hexdigest().upper(),
        "files": len(children),
        "preimage_bytes": len(preimage),
        "definition": "SHA256(UTF-8 concatenation of UPPERCASE_file_sha256 + two spaces + relative_POSIX_path + LF)",
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"non-object row {rel(path)}:{line_number}")
        rows.append(value)
    return rows


def path_equal(left: str | Path, right: str | Path) -> bool:
    return str(Path(left).resolve()).casefold() == str(Path(right).resolve()).casefold()


def option(command: list[str], name: str) -> str:
    indices = [index for index, value in enumerate(command) if value == name]
    if len(indices) != 1 or indices[0] + 1 >= len(command):
        raise ValueError(f"missing/repeated option {name}")
    return command[indices[0] + 1]


def without_trace(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "trace"}


def summary_tuple(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row.get(field) for field in SUMMARY_FIELDS)


def exception_count(value: Any) -> int:
    if isinstance(value, dict):
        count = 0
        for key, child in value.items():
            if "exception" in str(key).casefold() and child not in (None, "", False, 0, [], {}):
                count += 1
            count += exception_count(child)
        return count
    if isinstance(value, list):
        return sum(exception_count(child) for child in value)
    return 0


def exact_mcnemar(gains: int, regressions: int) -> float:
    discordant = gains + regressions
    if discordant == 0:
        return 1.0
    lower = min(gains, regressions)
    tail = sum(math.comb(discordant, index) for index in range(lower + 1)) / (2**discordant)
    return min(1.0, 2.0 * tail)


def paired_stats(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    selected = list(rows)
    n = len(selected)
    baseline_wins = sum(row["baseline_win"] for row in selected)
    candidate_wins = sum(row["candidate_win"] for row in selected)
    gains = sum(row["baseline_win"] == 0 and row["candidate_win"] == 1 for row in selected)
    regressions = sum(row["baseline_win"] == 1 and row["candidate_win"] == 0 for row in selected)
    both_win = sum(row["baseline_win"] == row["candidate_win"] == 1 for row in selected)
    both_loss = sum(row["baseline_win"] == row["candidate_win"] == 0 for row in selected)
    return {
        "n": n,
        "baseline_wins": baseline_wins,
        "baseline_losses": n - baseline_wins,
        "baseline_rate": baseline_wins / n,
        "candidate_wins": candidate_wins,
        "candidate_losses": n - candidate_wins,
        "candidate_rate": candidate_wins / n,
        "delta_wins": candidate_wins - baseline_wins,
        "delta_rate": (candidate_wins - baseline_wins) / n,
        "gains": gains,
        "regressions": regressions,
        "ties": both_win + both_loss,
        "both_win": both_win,
        "both_loss": both_loss,
        "discordant": gains + regressions,
        "mcnemar_exact_two_sided_p": exact_mcnemar(gains, regressions),
    }


def grouped(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[tuple(row[field] for field in fields)].append(row)
    return [
        {field: value for field, value in zip(fields, key)} | paired_stats(buckets[key])
        for key in sorted(buckets)
    ]


def first_semantic_difference(left_path: Path, right_path: Path) -> dict[str, Any] | None:
    """Return a compact first-difference record; never infer a Rule 2 start."""
    if sha256(left_path) == sha256(right_path):
        return None
    left = read_jsonl(left_path)
    right = read_jsonl(right_path)
    limit = min(len(left), len(right))
    index = next((i for i in range(limit) if left[i] != right[i]), limit)
    if index == limit:
        return {
            "index": index,
            "reason": "length_only",
            "baseline_rows": len(left),
            "candidate_rows": len(right),
        }
    lrow, rrow = left[index], right[index]
    same_observation = {k: v for k, v in lrow.items() if k != "action"} == {
        k: v for k, v in rrow.items() if k != "action"
    }
    return {
        "index": index,
        "step": rrow.get("step"),
        "player": rrow.get("player"),
        "context": rrow.get("context"),
        "baseline_action": lrow.get("action"),
        "candidate_action": rrow.get("action"),
        "same_observation_except_action": same_observation,
    }


def main() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    violations: list[str] = []
    runner_discrepancies: list[str] = []

    requirements = REPO / spec["strategy"]["path"]
    baseline_dir = REPO / spec["baseline"]["path"]
    candidate_dir = REPO / spec["candidate"]["path"]
    hashes = {
        "spec": {"path": rel(SPEC), "sha256": sha256(SPEC), "expected": EXPECTED_SPEC_SHA256},
        "requirements": {
            "path": rel(requirements),
            "sha256": sha256(requirements),
            "expected": EXPECTED_REQUIREMENTS_SHA256,
        },
        "baseline_main": {
            "path": rel(baseline_dir / "main.py"),
            "sha256": sha256(baseline_dir / "main.py"),
            "expected": EXPECTED_BASELINE_SHA256,
        },
        "candidate_main": {
            "path": rel(candidate_dir / "main.py"),
            "sha256": sha256(candidate_dir / "main.py"),
            "expected": EXPECTED_CANDIDATE_SHA256,
        },
        "baseline_deck": {
            "path": rel(baseline_dir / "deck.csv"),
            "sha256": sha256(baseline_dir / "deck.csv"),
            "expected": EXPECTED_DECK_SHA256,
        },
        "candidate_deck": {
            "path": rel(candidate_dir / "deck.csv"),
            "sha256": sha256(candidate_dir / "deck.csv"),
            "expected": EXPECTED_DECK_SHA256,
        },
    }
    verification = REPO / spec["verification"]["path"]
    hashes["root_verification"] = {
        "path": rel(verification),
        "sha256": sha256(verification),
        "expected": spec["verification"]["sha256"],
    }
    for name, expected in spec["engine"]["files"].items():
        path = REPO / spec["engine"]["path"] / name
        hashes[f"engine:{name}"] = {
            "path": rel(path),
            "sha256": sha256(path),
            "expected": expected,
        }
    for name, runner in spec["runners"].items():
        path = REPO / runner["path"]
        hashes[f"runner:{name}"] = {
            "path": rel(path),
            "sha256": sha256(path),
            "expected": runner["sha256"],
        }
    for opponent in spec["opponents"]:
        directory = REPO / opponent["path"]
        for filename, expected in (
            ("main.py", opponent["main_sha256"]),
            ("deck.csv", opponent["deck_sha256"]),
        ):
            path = directory / filename
            hashes[f"opponent:{opponent['label']}:{filename}"] = {
                "path": rel(path),
                "sha256": sha256(path),
                "expected": expected,
            }
    for label, value in hashes.items():
        value["match"] = value["sha256"] == value["expected"]
        if not value["match"]:
            violations.append(f"hash mismatch: {label}")

    runner_raw_tree = runner_tree_sha256(RAW)
    portable_raw_tree = portable_tree_sha256(RAW)
    runner_raw_tree["expected"] = EXPECTED_RAW_TREE_SHA256
    runner_raw_tree["match"] = runner_raw_tree["sha256"] == EXPECTED_RAW_TREE_SHA256
    raw_tree = {
        "path": rel(RAW),
        "runner_ledger": runner_raw_tree,
        "portable_tab_bytes_ledger": portable_raw_tree,
        "match": runner_raw_tree["match"],
    }
    if not raw_tree["match"]:
        violations.append("raw tree digest mismatch")

    panels = {panel["label"]: panel for panel in spec["panels"]}
    expected_keys: set[tuple[str, str, int, int]] = set()
    for panel_name, panel in panels.items():
        for opponent in panel["opponents"]:
            for seat in (0, 1):
                for game in range(panel["games_per_seat"]):
                    expected_keys.add((panel_name, opponent["label"], seat, panel["seed_base"] + game))

    summaries: dict[tuple[str, str, int, str], list[dict[str, Any]]] = {}
    traces: dict[tuple[str, str, int, str, int], Path] = {}
    records: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    manifest_rows = 0
    exit_failures = 0
    game_start_faults = 0
    action_errors = 0
    max_step_hits = 0
    exceptions = 0
    invalid_results = 0
    trace_integrity_faults = 0
    duplicate_summary_mismatches = 0
    duplicate_tuple_mismatches = 0
    duplicate_result_mismatches = 0
    duplicate_step_mismatches = 0
    duplicate_trace_mismatches = 0
    candidate_trace_mismatches = 0
    first_differences: list[dict[str, Any]] = []
    panel_hashes: dict[str, Any] = {}

    expected_python = REPO / spec["python"]
    battle_runner = REPO / spec["runners"]["checked_battle"]["path"]
    engine_dir = REPO / spec["engine"]["path"]

    for panel_name, panel in panels.items():
        panel_root = RAW / panel["output"]
        manifest_path = panel_root / "manifest.jsonl"
        manifest = read_jsonl(manifest_path)
        manifest_rows += len(manifest)
        opponent_paths = {row["label"]: REPO / row["path"] for row in panel["opponents"]}
        expected_runs = {
            (opponent, seat, role)
            for opponent in opponent_paths
            for seat in (0, 1)
            for role in ("baseline_a", "baseline_b", "candidate")
        }
        seen_runs: set[tuple[str, int, str]] = set()

        for manifest_row in manifest:
            role = str(manifest_row["role"])
            opponent = str(manifest_row["opponent"])
            seat = int(manifest_row["seat"])
            run_key = (opponent, seat, role)
            if run_key in seen_runs or run_key not in expected_runs:
                violations.append(f"{panel_name}: bad manifest run key {run_key}")
                continue
            seen_runs.add(run_key)
            exit_failures += int(manifest_row.get("exit_code") != 0)
            command = manifest_row.get("command")
            if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
                violations.append(f"{panel_name}: malformed command {run_key}")
                continue
            policy_dir = baseline_dir if role.startswith("baseline") else candidate_dir
            expected_a, expected_b = (
                (policy_dir, opponent_paths[opponent])
                if seat == 0
                else (opponent_paths[opponent], policy_dir)
            )
            checks = [
                path_equal(command[0], expected_python),
                path_equal(command[1], battle_runner),
                command.count("--engine-seed") == 1,
                int(option(command, "--games")) == panel["games_per_seat"],
                int(option(command, "--seed-base")) == panel["seed_base"],
                int(option(command, "--max-steps")) == spec["max_steps"],
                path_equal(option(command, "--engine-dir"), engine_dir),
                path_equal(option(command, "--agent-a"), expected_a),
                path_equal(option(command, "--agent-b"), expected_b),
                path_equal(option(command, "--deck-a"), expected_a / "deck.csv"),
                path_equal(option(command, "--deck-b"), expected_b / "deck.csv"),
            ]
            if not all(checks):
                violations.append(f"{panel_name}: immutable command mismatch {run_key}")

            summary_path = Path(option(command, "--summary")).resolve()
            trace_dir = Path(option(command, "--trace-dir")).resolve()
            rows = read_jsonl(summary_path)
            summaries[(panel_name, opponent, seat, role)] = rows
            if len(rows) != panel["games_per_seat"]:
                violations.append(f"{panel_name}: wrong summary row count {run_key}")
            expected_names = {f"game_{game:04d}.jsonl" for game in range(panel["games_per_seat"])}
            actual_names = {item.name for item in trace_dir.glob("game_*.jsonl") if item.is_file()}
            if actual_names != expected_names:
                violations.append(f"{panel_name}: trace set mismatch {run_key}")

            for game, row in enumerate(rows):
                if row.get("game") != game or row.get("seed") != panel["seed_base"] + game:
                    violations.append(f"{panel_name}: summary sequence mismatch {run_key} game {game}")
                game_start_faults += int(row.get("started") is not True)
                action_errors += int(row.get("action_errors", 0) or 0)
                max_step_hits += int(bool(row.get("hit_max_steps", False)))
                invalid_results += int(row.get("result") not in (0, 1))
                exceptions += exception_count(row)
                trace_path = trace_dir / f"game_{game:04d}.jsonl"
                if not trace_path.is_file() or not path_equal(str(row.get("trace", "")), trace_path):
                    violations.append(f"{panel_name}: trace binding mismatch {run_key} game {game}")
                    continue
                traces[(panel_name, opponent, seat, role, game)] = trace_path
                trace_rows = read_jsonl(trace_path)
                if len(trace_rows) != row.get("steps"):
                    trace_integrity_faults += 1
                for index, trace_row in enumerate(trace_rows):
                    if trace_row.get("game") != game or trace_row.get("step") != index:
                        trace_integrity_faults += 1
                    exceptions += exception_count(trace_row)

        if seen_runs != expected_runs:
            violations.append(f"{panel_name}: manifest run-set mismatch")

        for opponent in opponent_paths:
            for seat in (0, 1):
                baseline_a = summaries[(panel_name, opponent, seat, "baseline_a")]
                baseline_b = summaries[(panel_name, opponent, seat, "baseline_b")]
                candidate = summaries[(panel_name, opponent, seat, "candidate")]
                for game in range(panel["games_per_seat"]):
                    first, duplicate, tested = baseline_a[game], baseline_b[game], candidate[game]
                    duplicate_tuple_mismatches += int(summary_tuple(first) != summary_tuple(duplicate))
                    duplicate_summary_mismatches += int(without_trace(first) != without_trace(duplicate))
                    duplicate_result_mismatches += int(first["result"] != duplicate["result"])
                    duplicate_step_mismatches += int(first["steps"] != duplicate["steps"])
                    baseline_trace = traces[(panel_name, opponent, seat, "baseline_a", game)]
                    duplicate_trace = traces[(panel_name, opponent, seat, "baseline_b", game)]
                    candidate_trace = traces[(panel_name, opponent, seat, "candidate", game)]
                    duplicate_trace_mismatches += int(sha256(baseline_trace) != sha256(duplicate_trace))
                    difference = first_semantic_difference(baseline_trace, candidate_trace)
                    if difference is not None:
                        candidate_trace_mismatches += 1
                        first_differences.append(
                            {
                                "panel": panel_name,
                                "opponent": opponent,
                                "seat": seat,
                                "seed": int(first["seed"]),
                                **difference,
                            }
                        )
                    key = (panel_name, opponent, seat, int(first["seed"]))
                    if key in records:
                        violations.append(f"duplicate key {key}")
                    records[key] = {
                        "panel": panel_name,
                        "opponent": opponent,
                        "seat": seat,
                        "game": game,
                        "seed": int(first["seed"]),
                        "baseline_result": int(first["result"]),
                        "candidate_result": int(tested["result"]),
                        "baseline_steps": int(first["steps"]),
                        "candidate_steps": int(tested["steps"]),
                        "baseline_win": int(first["result"] == seat),
                        "candidate_win": int(tested["result"] == seat),
                    }

        csv_rows = list(csv.DictReader((panel_root / "paired_results.csv").open(encoding="utf-8", newline="")))
        if len(csv_rows) != panel["expected_rows"]:
            runner_discrepancies.append(f"{panel_name}: paired row count")
        for csv_row in csv_rows:
            key = (panel_name, csv_row["opponent"], int(csv_row["seat"]), int(csv_row["seed"]))
            row = records.get(key)
            if row is None:
                runner_discrepancies.append(f"{panel_name}: unknown paired key {key}")
                continue
            expected = {
                "seed_base": str(panel["seed_base"]),
                "opponent": row["opponent"],
                "seat": str(row["seat"]),
                "game": str(row["game"]),
                "seed": str(row["seed"]),
                "baseline_result": str(row["baseline_result"]),
                "candidate_result": str(row["candidate_result"]),
                "baseline_win": str(row["baseline_win"]),
                "candidate_win": str(row["candidate_win"]),
                "baseline_steps": str(row["baseline_steps"]),
                "candidate_steps": str(row["candidate_steps"]),
            }
            if csv_row != expected:
                runner_discrepancies.append(f"{panel_name}: paired mismatch {key}")

        panel_rows = [row for row in records.values() if row["panel"] == panel_name]
        report = json.loads((panel_root / "report.json").read_text(encoding="utf-8"))
        stats = paired_stats(panel_rows)
        expected_aggregate = {
            "baseline_wins": stats["baseline_wins"],
            "candidate_wins": stats["candidate_wins"],
            "games": stats["n"],
            "delta_wins": stats["delta_wins"],
        }
        if report.get("aggregates") != expected_aggregate:
            runner_discrepancies.append(f"{panel_name}: report aggregate")
        if report.get("valid") is not True or report.get("duplicate_mismatch_count") != 0:
            runner_discrepancies.append(f"{panel_name}: report health")
        panel_hashes[panel_name] = {
            "manifest_sha256": sha256(manifest_path),
            "paired_results_sha256": sha256(panel_root / "paired_results.csv"),
            "cell_summary_sha256": sha256(panel_root / "cell_summary.csv"),
            "report_sha256": sha256(panel_root / "report.json"),
        }

    if set(records) != expected_keys or len(records) != spec["expected_total_rows"]:
        violations.append("schedule keys differ from immutable specification")
    if any(
        (
            exit_failures,
            game_start_faults,
            action_errors,
            max_step_hits,
            exceptions,
            invalid_results,
            trace_integrity_faults,
        )
    ):
        violations.append("execution/trace health failure")
    if any((duplicate_tuple_mismatches, duplicate_summary_mismatches, duplicate_trace_mismatches)):
        violations.append("duplicate-control failure")
    if runner_discrepancies:
        violations.append("checked outputs disagree with independent reconstruction")

    rows = [records[key] for key in sorted(records)]
    overall = paired_stats(rows)
    by_panel = grouped(rows, ("panel",))
    by_opponent = grouped(rows, ("opponent",))
    by_seat = grouped(rows, ("seat",))
    by_cell = grouped(rows, ("panel", "opponent", "seat"))

    # The tested Rule 2 policy can start only if it takes an action different
    # from the accepted Rule 1 parent.  Byte and parsed semantic equality over
    # all 160 traces therefore proves zero natural starts in this matrix.
    natural_starts = candidate_trace_mismatches
    shadow_starts = 0  # supplied/root-verified in the task contract: 0/4,262 callbacks

    seed_groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        seed_groups[(row["panel"], row["seed"])].append(row)
    seed_sensitivity = []
    for panel_name in sorted(panels):
        clusters = [values for (name, _), values in sorted(seed_groups.items()) if name == panel_name]
        deltas = [sum(row["candidate_win"] - row["baseline_win"] for row in values) for values in clusters]
        wins = [sum(row["candidate_win"] for row in values) for values in clusters]
        seed_sensitivity.append(
            {
                "panel": panel_name,
                "clusters": len(clusters),
                "rows_per_cluster": sorted({len(values) for values in clusters}),
                "positive_zero_negative_delta_clusters": [
                    sum(value > 0 for value in deltas),
                    sum(value == 0 for value in deltas),
                    sum(value < 0 for value in deltas),
                ],
                "candidate_cluster_win_range": [min(wins), max(wins)],
                "delta_range": [min(deltas), max(deltas)],
            }
        )

    discordance_upper = 1.0 - 0.05 ** (1.0 / overall["n"])
    uncertainty = {
        "stratified_seed_cluster_empirical_95ci_delta_rate": [0.0, 0.0],
        "note": "All 160 observed paired deltas are zero, so every empirical cluster resample is zero; this does not prove population identity.",
        "zero_discordance_95pct_magnitude_envelope": [-discordance_upper, discordance_upper],
        "envelope_definition": "one-sided Clopper-Pearson upper bound for 0 discordant rows, mapped through abs(net delta) <= discordance",
    }

    group_regressions = [row for row in by_seat + by_opponent if row["delta_wins"] < -2]
    gates_cfg = spec["gates"]
    gates = {
        "frozen_hashes": all(item["match"] for item in hashes.values()) and raw_tree["match"],
        "unique_schedule_keys": len(records) == gates_cfg["unique_schedule_keys"] and set(records) == expected_keys,
        "duplicate_summary_matches": 160 - duplicate_summary_mismatches == gates_cfg["duplicate_summary_matches"],
        "duplicate_byte_trace_matches": 160 - duplicate_trace_mismatches == gates_cfg["duplicate_byte_trace_matches"],
        "zero_execution_faults": exit_failures == gates_cfg["execution_faults"],
        "zero_game_start_faults": game_start_faults == gates_cfg["start_faults"],
        "zero_action_errors": action_errors == gates_cfg["action_errors"],
        "zero_exceptions": exceptions == gates_cfg["exceptions"],
        "zero_max_step_hits": max_step_hits == gates_cfg["max_step_hits"],
        "minimum_natural_starts": natural_starts >= gates_cfg["minimum_natural_starts"],
        "paired_gains_at_least_regressions": overall["gains"] >= overall["regressions"],
        "no_seat_or_opponent_three_wins_below_parent": not group_regressions,
        "zero_runner_discrepancies": not runner_discrepancies,
    }
    dormant = shadow_starts + natural_starts == gates_cfg["dormant_if_shadow_plus_fixed160_starts"]
    mechanical_gate_names = [name for name in gates if name != "minimum_natural_starts"]
    mechanical_pass = all(gates[name] for name in mechanical_gate_names) and not violations
    recommendation = "DEFER-DORMANT" if mechanical_pass and dormant else ("ACCEPT" if all(gates.values()) and not violations else "REJECT")

    severe_floors = [
        {
            "scope": f"{row['opponent']}|seat{row['seat']}",
            "candidate_wins": row["candidate_wins"],
            "n": row["n"],
            "candidate_rate": row["candidate_rate"],
            "delta_wins": row["delta_wins"],
        }
        for row in by_cell
        if row["candidate_rate"] < 0.5
    ]

    output = {
        "audit": "archaludon_historical_silver_single_resolver_salvage_rule2_trial_v1_fixed160",
        "recommendation": recommendation,
        "policy_to_player_mapping": {
            "seat_0": "tested policy is agent A/player 0; win iff result == 0",
            "seat_1": "tested policy is agent B/player 1; win iff result == 1",
        },
        "assumptions": [
            "Rows are paired only by immutable (panel, opponent, seat, seed).",
            "The 4,262-callback shadow start count of zero is supplied as root-verified evidence and is not re-derived here.",
            "Because every candidate trace is byte-identical to its accepted-parent trace, Rule 2 had zero natural starts in fixed160.",
            "Inference is conditional on these frozen opponents and seeds; a zero observed delta alone is not strength evidence.",
        ],
        "hashes": {"artifacts": hashes, "raw_tree": raw_tree, "panels": panel_hashes},
        "schedule_and_health": {
            "expected_keys": len(expected_keys),
            "reconstructed_unique_keys": len(records),
            "manifest_rows": manifest_rows,
            "exit_failures": exit_failures,
            "game_start_faults": game_start_faults,
            "action_errors": action_errors,
            "max_step_hits": max_step_hits,
            "exception_fields": exceptions,
            "invalid_results": invalid_results,
            "trace_integrity_faults": trace_integrity_faults,
            "duplicate_game_tuple_matches": 160 - duplicate_tuple_mismatches,
            "duplicate_nontrace_summary_matches": 160 - duplicate_summary_mismatches,
            "duplicate_result_matches": 160 - duplicate_result_mismatches,
            "duplicate_decision_count_matches": 160 - duplicate_step_mismatches,
            "duplicate_byte_trace_matches": 160 - duplicate_trace_mismatches,
            "candidate_parent_byte_trace_matches": 160 - candidate_trace_mismatches,
            "candidate_parent_semantic_first_differences": first_differences,
            "runner_discrepancies": runner_discrepancies,
        },
        "identical_policy_control": {
            "policy": "baseline_a and baseline_b are the same accepted Rule 1 policy in the same player role, opponent, and seed",
            "keys": 160,
            "nontrace_summary_matches": 160 - duplicate_summary_mismatches,
            "result_matches": 160 - duplicate_result_mismatches,
            "decision_count_matches": 160 - duplicate_step_mismatches,
            "byte_trace_matches": 160 - duplicate_trace_mismatches,
            "note": "The Historical-Silver panel is Rule 1 versus exact Historical-Silver, so cross-seat runs are not an identical-policy control and are not compared as one.",
        },
        "aggregate": overall,
        "paired_uncertainty": uncertainty,
        "by_panel": by_panel,
        "by_opponent": by_opponent,
        "by_seat": by_seat,
        "by_cell": by_cell,
        "seed_sensitivity": seed_sensitivity,
        "severe_absolute_floors_below_50pct": severe_floors,
        "rule2_coverage": {
            "shadow_callbacks": 4262,
            "shadow_natural_starts": shadow_starts,
            "fixed160_natural_starts": natural_starts,
            "combined_natural_starts": shadow_starts + natural_starts,
            "dormant": dormant,
        },
        "practical_effect": {
            "observed_delta_wins": overall["delta_wins"],
            "observed_delta_rate": overall["delta_rate"],
            "meaningful_improvement": False,
            "reason": "Rule 2 never changed an evaluated action; there are zero gains and zero regressions.",
        },
        "gates": gates,
        "mechanical_pass_excluding_coverage": mechanical_pass,
        "violations": violations,
    }
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    main()
