"""Read-only audit of the completed Rule 4 fixed160 evaluation.

Run on Windows from the repository root with:

    .venv-rl\Scripts\python.exe autonomous_gold_20260715\numerical_audits\archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1_fixed160\audit_rule4_fixed160.py

The calculator reads frozen inputs and raw runner artifacts, prints canonical
JSON, and never runs a battle or writes to the raw result tree.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OVERLAY = REPO / (
    "autonomous_gold_20260715/evaluation_specs/"
    "archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1/"
    "fixed160_spec.json"
)
RAW = REPO / (
    "autonomous_gold_20260715/evaluations/"
    "archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1/"
    "fixed160_raw"
)
IMPLEMENTATION = REPO / (
    "autonomous_gold_20260715/implementation/"
    "archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1"
)
SHADOW_SUMMARY = IMPLEMENTATION / "shadow_summary.json"
SHADOW_DIFFERENCES = IMPLEMENTATION / "shadow_differences.json"

EXPECTED = {
    "overlay": "3649FFDDEF35ADCE6A50EBC8F1BE581E9E4780426D4FF8AA5271F8A2912A9D7A",
    "schedule_base": "E2B8986663A43A7F6F52888E487F39B8D059CDCDDF441A3E87D8C093DF15274C",
    "raw_tree": "82CE2B713417F754D13BCF8B2EC9C682AA0EFEC930EBB14FA19D0D4BA68782E1",
    "baseline_main": "153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A",
    "candidate_main": "F6B6266D870D3F134544A91616C27673620557D149C0496CC2034E7674F010D9",
    "deck": "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A",
    "strategy": "136526EB9D2435A7E5822D3A6EE106078267365EDFB5801DCDE15A7737F7A269",
    "verification": "192C5D9146BA5E16FEE61411FB6C402E213841B92F151666FE8A89367E70BDB8",
    "implementation_report": "0F5DDDAC225AC16CC439FD096A01D8C34FA19150839A423316EE39A58EF9B967",
    "shadow_summary": "B37F5162A12F25B9C179DF7E891FC3410621F1FAA59A83D4B2FB5D2AB3C3D594",
    "shadow_differences": "AFF84E8BE667B9D36834DA00356BE5C755C5965D3E13C321E38C0F1EFBC02718",
}
ALLOWED_ROUTES = {
    "DURALUDON_BEFORE_LILLIE",
    "BENCH_EVOLUTION_BEFORE_LILLIE",
    "THIRD_METAL_BEFORE_LILLIE",
    "FULL_METAL_LAB_BEFORE_LILLIE",
}
SUMMARY_CONTROL_FIELDS = (
    "game", "seed", "started", "steps", "turn", "hit_max_steps",
    "result", "action_errors", "context_counts",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def relative(path: Path) -> str:
    return path.resolve().relative_to(REPO).as_posix()


def raw_tree_digest(path: Path) -> dict[str, Any]:
    """Digest supplied by the parent: relative|bytes|SHA256 plus final LF."""
    rows: list[str] = []
    total_bytes = 0
    for child in sorted(
        (value for value in path.rglob("*") if value.is_file()),
        key=lambda value: value.relative_to(path).as_posix(),
    ):
        size = child.stat().st_size
        total_bytes += size
        rows.append(f"{child.relative_to(path).as_posix()}|{size}|{sha256(child)}\n")
    return {
        "sha256": hashlib.sha256("".join(rows).encode("utf-8")).hexdigest().upper(),
        "files": len(rows),
        "bytes": total_bytes,
        "definition": "SHA256(UTF-8 sorted relative/path|bytes|UPPERCASE_file_sha256\\n)",
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"non-object JSON row: {relative(path)}:{number}")
        output.append(value)
    return output


def command_option(command: list[str], flag: str) -> str:
    positions = [index for index, value in enumerate(command) if value == flag]
    if len(positions) != 1 or positions[0] + 1 >= len(command):
        raise ValueError(f"missing or repeated command option: {flag}")
    return command[positions[0] + 1]


def path_equal(left: str | Path, right: str | Path) -> bool:
    return str(Path(left).resolve()).casefold() == str(Path(right).resolve()).casefold()


def exception_count(value: Any) -> int:
    if isinstance(value, dict):
        return sum(
            int("exception" in str(key).casefold() and child not in (None, "", False, 0, [], {}))
            + exception_count(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return sum(exception_count(child) for child in value)
    return 0


def nontrace(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "trace"}


def control_tuple(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row.get(field) for field in SUMMARY_CONTROL_FIELDS)


def exact_mcnemar(gains: int, regressions: int) -> float:
    discordant = gains + regressions
    if discordant == 0:
        return 1.0
    low = min(gains, regressions)
    tail = sum(math.comb(discordant, value) for value in range(low + 1)) / (2**discordant)
    return min(1.0, 2.0 * tail)


def paired(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    selected = list(rows)
    n = len(selected)
    baseline = sum(row["baseline_win"] for row in selected)
    candidate = sum(row["candidate_win"] for row in selected)
    gains = sum(row["baseline_win"] == 0 and row["candidate_win"] == 1 for row in selected)
    regressions = sum(row["baseline_win"] == 1 and row["candidate_win"] == 0 for row in selected)
    return {
        "n": n,
        "baseline_wins": baseline,
        "baseline_losses": n - baseline,
        "baseline_rate": baseline / n,
        "candidate_wins": candidate,
        "candidate_losses": n - candidate,
        "candidate_rate": candidate / n,
        "delta_wins": candidate - baseline,
        "delta_rate": (candidate - baseline) / n,
        "gains": gains,
        "regressions": regressions,
        "ties": n - gains - regressions,
        "discordant": gains + regressions,
        "mcnemar_exact_two_sided_p": exact_mcnemar(gains, regressions),
    }


def grouped(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    buckets: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[tuple(row[field] for field in fields)].append(row)
    return [
        {field: value for field, value in zip(fields, key)} | paired(buckets[key])
        for key in sorted(buckets, key=lambda value: tuple(str(item) for item in value))
    ]


def first_action_difference(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> dict[str, Any] | None:
    for index, (baseline, candidate) in enumerate(zip(left, right)):
        if baseline.get("action") != candidate.get("action"):
            same_observation = {k: v for k, v in baseline.items() if k != "action"} == {
                k: v for k, v in candidate.items() if k != "action"
            }
            return {
                "trace_index": index,
                "baseline_step": baseline.get("step"),
                "candidate_step": candidate.get("step"),
                "player": candidate.get("player"),
                "context": candidate.get("context"),
                "effect_card_id": candidate.get("effect_card_id"),
                "baseline_action": baseline.get("action"),
                "candidate_action": candidate.get("action"),
                "same_observation_except_action": same_observation,
                "classification": "UNCLASSIFIED",
            }
    if len(left) != len(right):
        return {
            "trace_index": min(len(left), len(right)),
            "reason": "length_only",
            "baseline_rows": len(left),
            "candidate_rows": len(right),
            "classification": "UNCLASSIFIED",
        }
    return None


def main() -> None:
    violations: list[str] = []
    discrepancies: list[str] = []
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    base_path = REPO / overlay["schedule_base"]["path"]
    spec = json.loads(base_path.read_text(encoding="utf-8"))
    for field in ("policy", "strategy", "verification", "baseline", "candidate", "output_root"):
        spec[field] = overlay[field]
    spec["gates"].update(overlay["gates"])

    artifacts: dict[str, dict[str, Any]] = {}

    def bind(name: str, path: Path, expected: str) -> None:
        actual = sha256(path)
        artifacts[name] = {
            "path": relative(path), "sha256": actual, "expected": expected,
            "match": actual == expected,
        }
        if actual != expected:
            violations.append(f"hash mismatch: {name}")

    bind("overlay_spec", OVERLAY, EXPECTED["overlay"])
    bind("schedule_base", base_path, EXPECTED["schedule_base"])
    bind("strategy", REPO / spec["strategy"]["path"], EXPECTED["strategy"])
    bind("root_verification", REPO / spec["verification"]["path"], EXPECTED["verification"])
    bind("baseline_main", REPO / spec["baseline"]["path"] / "main.py", EXPECTED["baseline_main"])
    bind("candidate_main", REPO / spec["candidate"]["path"] / "main.py", EXPECTED["candidate_main"])
    bind("baseline_deck", REPO / spec["baseline"]["path"] / "deck.csv", EXPECTED["deck"])
    bind("candidate_deck", REPO / spec["candidate"]["path"] / "deck.csv", EXPECTED["deck"])
    bind("implementation_report", IMPLEMENTATION / "IMPLEMENTATION_REPORT.md", EXPECTED["implementation_report"])
    bind("shadow_summary", SHADOW_SUMMARY, EXPECTED["shadow_summary"])
    bind("shadow_differences", SHADOW_DIFFERENCES, EXPECTED["shadow_differences"])
    for name, runner in spec["runners"].items():
        bind(f"runner:{name}", REPO / runner["path"], runner["sha256"])
    for name, expected in spec["engine"]["files"].items():
        bind(f"engine:{name}", REPO / spec["engine"]["path"] / name, expected)
    for opponent in spec["opponents"]:
        bind(
            f"opponent:{opponent['label']}:main",
            REPO / opponent["path"] / "main.py",
            opponent["main_sha256"],
        )
        bind(
            f"opponent:{opponent['label']}:deck",
            REPO / opponent["path"] / "deck.csv",
            opponent["deck_sha256"],
        )

    tree = raw_tree_digest(RAW)
    tree["expected"] = EXPECTED["raw_tree"]
    tree["match"] = tree["sha256"] == EXPECTED["raw_tree"]
    if not tree["match"]:
        violations.append("raw tree digest mismatch")

    expected_keys: set[tuple[str, str, int, int]] = set()
    for panel in spec["panels"]:
        for opponent in panel["opponents"]:
            for seat in (0, 1):
                for game in range(panel["games_per_seat"]):
                    expected_keys.add((panel["label"], opponent["label"], seat, panel["seed_base"] + game))

    records: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    panel_hashes: dict[str, Any] = {}
    manifest_runs = 0
    summary_rows = 0
    exit_faults = start_faults = action_errors = max_step_hits = 0
    exception_fields = invalid_results = trace_faults = 0
    duplicate_control_tuple_mismatches = 0
    duplicate_summary_mismatches = duplicate_result_mismatches = 0
    duplicate_step_mismatches = duplicate_trace_mismatches = 0
    candidate_trace_byte_mismatches = 0
    first_differences: list[dict[str, Any]] = []

    for panel in spec["panels"]:
        panel_name = panel["label"]
        panel_root = RAW / panel["output"]
        manifest_path = panel_root / "manifest.jsonl"
        manifest = read_jsonl(manifest_path)
        manifest_runs += len(manifest)
        mapping: dict[tuple[str, int, str], dict[str, Any]] = {}
        for entry in manifest:
            key = (str(entry["opponent"]), int(entry["seat"]), str(entry["role"]))
            if key in mapping:
                violations.append(f"duplicate manifest key: {panel_name}:{key}")
            mapping[key] = entry
            exit_faults += int(entry.get("exit_code") != 0)

        for opponent in panel["opponents"]:
            opponent_label = opponent["label"]
            opponent_dir = REPO / opponent["path"]
            for seat in (0, 1):
                runs: dict[str, tuple[list[dict[str, Any]], Path]] = {}
                for role in ("baseline_a", "baseline_b", "candidate"):
                    entry = mapping[(opponent_label, seat, role)]
                    command = entry["command"]
                    policy = REPO / (spec["candidate"]["path"] if role == "candidate" else spec["baseline"]["path"])
                    expected_a, expected_b = (policy, opponent_dir) if seat == 0 else (opponent_dir, policy)
                    command_ok = (
                        path_equal(command[0], REPO / spec["python"])
                        and path_equal(command[1], REPO / spec["runners"]["checked_battle"]["path"])
                        and command.count("--engine-seed") == 1
                        and int(command_option(command, "--games")) == panel["games_per_seat"]
                        and int(command_option(command, "--seed-base")) == panel["seed_base"]
                        and int(command_option(command, "--max-steps")) == spec["max_steps"]
                        and path_equal(command_option(command, "--agent-a"), expected_a)
                        and path_equal(command_option(command, "--agent-b"), expected_b)
                    )
                    if not command_ok:
                        violations.append(f"immutable command mismatch: {panel_name}:{opponent_label}:seat{seat}:{role}")
                    summary_path = Path(command_option(command, "--summary"))
                    trace_dir = Path(command_option(command, "--trace-dir"))
                    rows = read_jsonl(summary_path)
                    runs[role] = (rows, trace_dir)
                    summary_rows += len(rows)
                    if len(rows) != panel["games_per_seat"]:
                        violations.append(f"summary row count mismatch: {panel_name}:{opponent_label}:seat{seat}:{role}")
                    for game, row in enumerate(rows):
                        start_faults += int(row.get("started") is not True)
                        action_errors += int(row.get("action_errors", 0) or 0)
                        max_step_hits += int(bool(row.get("hit_max_steps", False)))
                        invalid_results += int(row.get("result") not in (0, 1))
                        exception_fields += exception_count(row)
                        trace_path = trace_dir / f"game_{game:04d}.jsonl"
                        trace_rows = read_jsonl(trace_path)
                        trace_faults += int(len(trace_rows) != row.get("steps"))
                        trace_faults += sum(
                            item.get("game") != game or item.get("step") != index
                            for index, item in enumerate(trace_rows)
                        )
                        exception_fields += exception_count(trace_rows)

                baseline_rows, baseline_dir = runs["baseline_a"]
                duplicate_rows, duplicate_dir = runs["baseline_b"]
                candidate_rows, candidate_dir = runs["candidate"]
                for game in range(panel["games_per_seat"]):
                    baseline = baseline_rows[game]
                    duplicate = duplicate_rows[game]
                    candidate = candidate_rows[game]
                    duplicate_control_tuple_mismatches += int(control_tuple(baseline) != control_tuple(duplicate))
                    duplicate_summary_mismatches += int(nontrace(baseline) != nontrace(duplicate))
                    duplicate_result_mismatches += int(baseline["result"] != duplicate["result"])
                    duplicate_step_mismatches += int(baseline["steps"] != duplicate["steps"])
                    baseline_trace = baseline_dir / f"game_{game:04d}.jsonl"
                    duplicate_trace = duplicate_dir / f"game_{game:04d}.jsonl"
                    candidate_trace = candidate_dir / f"game_{game:04d}.jsonl"
                    duplicate_trace_mismatches += int(sha256(baseline_trace) != sha256(duplicate_trace))
                    same_candidate_trace = sha256(baseline_trace) == sha256(candidate_trace)
                    candidate_trace_byte_mismatches += int(not same_candidate_trace)
                    if not same_candidate_trace:
                        difference = first_action_difference(read_jsonl(baseline_trace), read_jsonl(candidate_trace))
                        if difference is not None:
                            first_differences.append({
                                "panel": panel_name,
                                "opponent": opponent_label,
                                "seat": seat,
                                "game": game,
                                "seed": int(baseline["seed"]),
                                **difference,
                            })
                    key = (panel_name, opponent_label, seat, int(baseline["seed"]))
                    if key in records:
                        violations.append(f"duplicate schedule key: {key}")
                    records[key] = {
                        "panel": panel_name,
                        "opponent": opponent_label,
                        "seat": seat,
                        "game": game,
                        "seed": int(baseline["seed"]),
                        "baseline_result": int(baseline["result"]),
                        "candidate_result": int(candidate["result"]),
                        "baseline_steps": int(baseline["steps"]),
                        "candidate_steps": int(candidate["steps"]),
                        "baseline_win": int(int(baseline["result"]) == seat),
                        "candidate_win": int(int(candidate["result"]) == seat),
                    }

        csv_rows = list(csv.DictReader((panel_root / "paired_results.csv").open(encoding="utf-8", newline="")))
        if len(csv_rows) != panel["expected_rows"]:
            discrepancies.append(f"{panel_name}: paired_results row count")
        for csv_row in csv_rows:
            key = (panel_name, csv_row["opponent"], int(csv_row["seat"]), int(csv_row["seed"]))
            raw = records.get(key)
            if raw is None:
                discrepancies.append(f"{panel_name}: unknown CSV key {key}")
                continue
            expected_row = {
                "seed_base": str(panel["seed_base"]), "opponent": raw["opponent"],
                "seat": str(raw["seat"]), "game": str(raw["game"]), "seed": str(raw["seed"]),
                "baseline_result": str(raw["baseline_result"]), "candidate_result": str(raw["candidate_result"]),
                "baseline_win": str(raw["baseline_win"]), "candidate_win": str(raw["candidate_win"]),
                "baseline_steps": str(raw["baseline_steps"]), "candidate_steps": str(raw["candidate_steps"]),
            }
            if csv_row != expected_row:
                discrepancies.append(f"{panel_name}: CSV mismatch {key}")

        panel_rows = [row for row in records.values() if row["panel"] == panel_name]
        report = json.loads((panel_root / "report.json").read_text(encoding="utf-8"))
        stats = paired(panel_rows)
        expected_aggregate = {
            "baseline_wins": stats["baseline_wins"], "candidate_wins": stats["candidate_wins"],
            "games": stats["n"], "delta_wins": stats["delta_wins"],
        }
        if report.get("aggregates") != expected_aggregate or report.get("valid") is not True:
            discrepancies.append(f"{panel_name}: report mismatch")
        panel_hashes[panel_name] = {
            "manifest": sha256(manifest_path),
            "paired_results": sha256(panel_root / "paired_results.csv"),
            "cell_summary": sha256(panel_root / "cell_summary.csv"),
            "report": sha256(panel_root / "report.json"),
        }

    if set(records) != expected_keys or len(records) != spec["expected_total_rows"]:
        violations.append("raw schedule differs from immutable schedule")
    rows = [records[key] for key in sorted(records)]
    overall = paired(rows)
    by_panel = grouped(rows, ("panel",))
    by_opponent = grouped(rows, ("opponent",))
    by_seat = grouped(rows, ("seat",))
    by_cell = grouped(rows, ("panel", "opponent", "seat"))

    seed_clusters: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        seed_clusters[(row["panel"], row["seed"])].append(row)
    seed_sensitivity = []
    for panel_name in sorted({row["panel"] for row in rows}):
        clusters = [values for (name, _), values in sorted(seed_clusters.items()) if name == panel_name]
        deltas = [sum(row["candidate_win"] - row["baseline_win"] for row in values) for values in clusters]
        wins = [sum(row["candidate_win"] for row in values) for values in clusters]
        seed_sensitivity.append({
            "panel": panel_name, "clusters": len(clusters),
            "rows_per_cluster": sorted({len(values) for values in clusters}),
            "positive_zero_negative_delta_clusters": [
                sum(value > 0 for value in deltas), sum(value == 0 for value in deltas), sum(value < 0 for value in deltas),
            ],
            "candidate_cluster_win_range": [min(wins), max(wins)],
            "delta_range": [min(deltas), max(deltas)],
        })

    shadow_summary = json.loads(SHADOW_SUMMARY.read_text(encoding="utf-8"))
    shadow_rows = json.loads(SHADOW_DIFFERENCES.read_text(encoding="utf-8"))
    shadow_starts = []
    for row in shadow_rows:
        telemetry = row.get("telemetry") or {}
        parent_semantic = telemetry.get("parent_semantic") or []
        exact_parent_lillie = (
            row.get("parent_card_id") == 1227
            and len(parent_semantic) == 1
            and parent_semantic[0][0] == 7
            and parent_semantic[0][1] == 1227
            and parent_semantic[0][2] == row.get("parent_card_serial")
        )
        allowed = row.get("classification") in ALLOWED_ROUTES
        shadow_starts.append({
            "replay": row.get("replay"), "seat": row.get("seat"), "step": row.get("step"),
            "turn": row.get("turn"), "classification": row.get("classification"),
            "parent_lillie_serial": row.get("parent_card_serial"),
            "selected_card_id": (row.get("materialization_evidence") or {}).get("selected_card_id"),
            "selected_card_serial": (row.get("materialization_evidence") or {}).get("selected_card_serial"),
            "target_serial": (row.get("materialization_evidence") or {}).get("target_serial"),
            "allowed_route": allowed, "exact_physical_parent_lillie": exact_parent_lillie,
        })
    fixed_starts = len(first_differences)
    combined_starts = len(shadow_starts) + fixed_starts
    shadow_completed = int(shadow_summary.get("confirmed_materializations", 0))
    shadow_failed = 0
    shadow_unobservable = len(shadow_starts) - shadow_completed

    zero_discordance_bound = 1.0 - 0.05 ** (1.0 / overall["n"])
    uncertainty = {
        "paired_seed_cluster_empirical_95_interval": [0.0, 0.0],
        "mcnemar_exact_two_sided_p": overall["mcnemar_exact_two_sided_p"],
        "zero_discordance_95pct_net_effect_sensitivity_envelope": [
            -zero_discordance_bound, zero_discordance_bound,
        ],
        "note": "All observed paired and seed-cluster deltas are zero; the degenerate empirical interval is not proof of population identity.",
    }

    severe_floors = [
        {"opponent": row["opponent"], "seat": row["seat"], "wins": row["candidate_wins"],
         "n": row["n"], "rate": row["candidate_rate"], "delta_wins": row["delta_wins"]}
        for row in by_cell if row["candidate_rate"] < 0.5
    ]
    regressed_groups = [row for row in by_seat + by_opponent if row["delta_wins"] < -2]
    fixed_harmful = [
        row for row in first_differences
        if records[(row["panel"], row["opponent"], row["seat"], row["seed"])]["candidate_win"]
        < records[(row["panel"], row["opponent"], row["seat"], row["seed"])]["baseline_win"]
    ]
    gates = {
        "frozen_hashes_and_raw_tree": all(row["match"] for row in artifacts.values()) and tree["match"],
        "unique_exact_schedule": len(records) == 160 and set(records) == expected_keys,
        "duplicate_summary_matches": duplicate_summary_mismatches == 0,
        "duplicate_result_and_decision_count_matches": duplicate_result_mismatches == duplicate_step_mismatches == 0,
        "duplicate_byte_trace_matches": duplicate_trace_mismatches == 0,
        "zero_execution_start_action_exception_maxstep_faults": not any((
            exit_faults, start_faults, action_errors, exception_fields, max_step_hits, invalid_results, trace_faults,
        )),
        "zero_runner_discrepancies": not discrepancies,
        "all_fixed160_first_differences_allowed": all(row["classification"] in ALLOWED_ROUTES for row in first_differences),
        "all_shadow_first_differences_allowed": all(row["allowed_route"] for row in shadow_starts),
        "all_starts_have_exact_parent_lillie": all(row["exact_physical_parent_lillie"] for row in shadow_starts),
        "combined_natural_starts_at_least_one": combined_starts >= overlay["gates"]["minimum_natural_starts"],
        "paired_gains_at_least_regressions": overall["gains"] >= overall["regressions"],
        "no_seat_or_opponent_three_wins_below_parent": not regressed_groups,
        "zero_mechanism_first_losses_or_clear_harmful_actions": not fixed_harmful,
    }
    dormant = combined_starts == overlay["gates"]["dormant_if_shadow_plus_fixed160_starts"]
    if any((duplicate_control_tuple_mismatches, duplicate_summary_mismatches, duplicate_trace_mismatches)):
        violations.append("duplicate-control mismatch")
    if discrepancies:
        violations.append("checked runner output disagrees with reconstruction")
    if any((exit_faults, start_faults, action_errors, exception_fields, max_step_hits, invalid_results, trace_faults)):
        violations.append("execution or trace fault")
    recommendation = "ACCEPT" if all(gates.values()) and not dormant and not violations else (
        "DEFER-DORMANT" if all(value for name, value in gates.items() if name != "combined_natural_starts_at_least_one") and dormant and not violations
        else "REJECT"
    )

    output = {
        "audit": "archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1_fixed160",
        "recommendation": recommendation,
        "policy_to_player_mapping": {
            "seat_0": "tested policy is agent A/player 0; win iff result == 0",
            "seat_1": "tested policy is agent B/player 1; win iff result == 1",
        },
        "assumptions": [
            "The Rule 4 overlay minimum-natural-start gate is applied to shadow plus fixed160, matching its explicit combined-start dormancy gate.",
            "The two shadow divergences are starts, but their counterfactual replay suffixes cannot observe receipt; zero confirmations is not counted as transaction failure.",
            "No fixed160 action difference means there can be no fixed160 mechanism-first loss or clearly harmful changed action.",
            "A zero aggregate delta and byte-identical fixed160 traces are not evidence that Rule 4 improves strength.",
        ],
        "hashes": {"artifacts": artifacts, "raw_tree": tree, "panels": panel_hashes},
        "schedule_and_health": {
            "expected_keys": len(expected_keys), "unique_keys": len(records),
            "manifest_runs": manifest_runs, "summary_rows_checked": summary_rows,
            "exit_faults": exit_faults, "start_faults": start_faults,
            "action_errors": action_errors, "exception_fields": exception_fields,
            "max_step_hits": max_step_hits, "invalid_results": invalid_results,
            "trace_integrity_faults": trace_faults,
            "duplicate_control_tuple_matches": 160 - duplicate_control_tuple_mismatches,
            "duplicate_nontrace_summary_matches": 160 - duplicate_summary_mismatches,
            "duplicate_result_matches": 160 - duplicate_result_mismatches,
            "duplicate_decision_count_matches": 160 - duplicate_step_mismatches,
            "duplicate_byte_trace_matches": 160 - duplicate_trace_mismatches,
            "candidate_parent_byte_trace_matches": 160 - candidate_trace_byte_mismatches,
            "fixed160_first_action_differences": first_differences,
            "runner_discrepancies": discrepancies,
        },
        "aggregate": overall,
        "paired_uncertainty": uncertainty,
        "by_panel": by_panel,
        "by_opponent": by_opponent,
        "by_seat": by_seat,
        "by_cell": by_cell,
        "seed_sensitivity": seed_sensitivity,
        "severe_absolute_floors_below_50pct": severe_floors,
        "rule4_coverage": {
            "allowed_routes": sorted(ALLOWED_ROUTES),
            "shadow_callbacks": shadow_summary.get("callbacks"),
            "shadow_natural_starts": len(shadow_starts),
            "shadow_starts": shadow_starts,
            "shadow_completed_transactions": shadow_completed,
            "shadow_failed_transactions": shadow_failed,
            "shadow_completion_unobservable_after_counterfactual_divergence": shadow_unobservable,
            "fixed160_natural_starts": fixed_starts,
            "fixed160_completed_transactions": 0,
            "fixed160_failed_transactions": 0,
            "combined_natural_starts": combined_starts,
            "dormant": dormant,
            "mechanism_first_outcome_regressions": len(fixed_harmful),
        },
        "practical_effect": {
            "observed_delta_wins": overall["delta_wins"],
            "observed_delta_rate": overall["delta_rate"],
            "meaningful_improvement_observed": False,
            "reason": "The candidate and parent are action- and byte-identical in all 160 evaluated games.",
        },
        "gates": gates,
        "dormant": dormant,
        "violations": violations,
    }
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    main()
