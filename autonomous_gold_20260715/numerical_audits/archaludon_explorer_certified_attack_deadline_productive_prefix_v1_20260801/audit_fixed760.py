"""Independent, read-only audit of the prepared fixed760 paired evaluation.

Run from the repository root with:
    .venv-rl\Scripts\python.exe autonomous_gold_20260715\numerical_audits\archaludon_explorer_certified_attack_deadline_productive_prefix_v1_20260801\audit_fixed760.py

The script reads the immutable spec and completed raw runner outputs.  It writes
nothing; its complete machine-readable audit is emitted as JSON on stdout.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[3]
SPEC_REL = Path(
    "autonomous_gold_20260715/evaluation_specs/"
    "archaludon_explorer_certified_attack_deadline_productive_prefix_v1/"
    "fixed760_spec.json"
)
RAW_REL = Path(
    "autonomous_gold_20260715/evaluations/"
    "archaludon_explorer_certified_attack_deadline_productive_prefix_v1/"
    "fixed760_raw_20260801"
)
SPEC_PATH = ROOT / SPEC_REL
RAW_ROOT = ROOT / RAW_REL
EXPECTED_SPEC_SHA256 = "22CBACA72FCD23D0909C205D8EF05FF3E8630998F687A2A054AAE937EC0E492F"
GAME_FIELDS = ("seed", "result", "steps", "turn", "action_errors", "hit_max_steps")
POLICY_MAIN = "main.py"
POLICY_DECK = "deck.csv"


_hash_cache: dict[Path, tuple[str, int, int]] = {}


def hash_file(path: Path) -> tuple[str, int, int]:
    """Return (sha256, byte count, newline count), cached by resolved path."""
    path = path.resolve()
    cached = _hash_cache.get(path)
    if cached is not None:
        return cached
    digest = hashlib.sha256()
    size = 0
    newlines = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
            newlines += chunk.count(b"\n")
    value = (digest.hexdigest().upper(), size, newlines)
    _hash_cache[path] = value
    return value


def sha256(path: Path) -> str:
    return hash_file(path)[0]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"non-object JSON at {path}:{line_number}")
            rows.append(value)
    return rows


def command_arg(command: list[str], name: str) -> str | None:
    try:
        return command[command.index(name) + 1]
    except (ValueError, IndexError):
        return None


def normalized_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "trace"}


def schedule_key(panel: str, opponent: str, seat: int, seed: int) -> tuple[str, str, int, int]:
    return panel, opponent, seat, seed


def wilson_interval(wins: int, games: int, z: float = 1.959963984540054) -> list[float]:
    if games == 0:
        return [float("nan"), float("nan")]
    p = wins / games
    denominator = 1.0 + z * z / games
    center = (p + z * z / (2.0 * games)) / denominator
    half = z * math.sqrt(p * (1.0 - p) / games + z * z / (4.0 * games * games)) / denominator
    return [center - half, center + half]


def zero_discordance_delta_interval(games: int, alpha: float = 0.05) -> list[float]:
    """Conservative paired-risk-difference CI when zero pairs are discordant.

    With q=P(any discordance), |candidate_rate-baseline_rate| <= q.  For zero
    observed discordances, 1-alpha**(1/n) is the exact one-sided Clopper-Pearson
    upper bound for q.  Therefore [-upper,+upper] covers the paired rate
    difference with at least 1-alpha confidence.
    """
    upper = 1.0 - alpha ** (1.0 / games)
    return [-upper, upper]


def exact_mcnemar_p(gains: int, regressions: int) -> float:
    discordant = gains + regressions
    if discordant == 0:
        return 1.0
    tail = min(gains, regressions)
    probability = sum(math.comb(discordant, k) for k in range(tail + 1)) / (2**discordant)
    return min(1.0, 2.0 * probability)


def summarize(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    values = list(rows)
    games = len(values)
    baseline_wins = sum(row["baseline_win"] for row in values)
    candidate_wins = sum(row["candidate_win"] for row in values)
    gains = sum(row["baseline_win"] == 0 and row["candidate_win"] == 1 for row in values)
    regressions = sum(row["baseline_win"] == 1 and row["candidate_win"] == 0 for row in values)
    ties = games - gains - regressions
    discordant = gains + regressions
    delta = (candidate_wins - baseline_wins) / games if games else float("nan")
    paired_interval = (
        zero_discordance_delta_interval(games) if games and discordant == 0 else None
    )
    return {
        "games": games,
        "baseline_wins": baseline_wins,
        "baseline_losses": games - baseline_wins,
        "baseline_rate": baseline_wins / games if games else None,
        "baseline_wilson95": wilson_interval(baseline_wins, games) if games else None,
        "candidate_wins": candidate_wins,
        "candidate_losses": games - candidate_wins,
        "candidate_rate": candidate_wins / games if games else None,
        "candidate_wilson95": wilson_interval(candidate_wins, games) if games else None,
        "delta_wins": candidate_wins - baseline_wins,
        "delta_rate": delta,
        "gains": gains,
        "regressions": regressions,
        "ties": ties,
        "discordant_pairs": discordant,
        "mcnemar_exact_two_sided_p": exact_mcnemar_p(gains, regressions),
        "paired_delta_conservative95": paired_interval,
    }


def grouped_summaries(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in fields)].append(row)
    output: list[dict[str, Any]] = []
    for key in sorted(groups):
        output.append({field: value for field, value in zip(fields, key)} | summarize(groups[key]))
    return output


def first_trace_difference(baseline_path: Path, candidate_path: Path, policy_seat: int) -> dict[str, Any]:
    baseline_rows = read_jsonl(baseline_path)
    candidate_rows = read_jsonl(candidate_path)
    limit = min(len(baseline_rows), len(candidate_rows))
    for index in range(limit):
        baseline = baseline_rows[index]
        candidate = candidate_rows[index]
        if baseline != candidate:
            differing_fields = sorted(key for key in set(baseline) | set(candidate) if baseline.get(key) != candidate.get(key))
            return {
                "trace_index": index,
                "baseline_step": baseline.get("step"),
                "candidate_step": candidate.get("step"),
                "baseline_player": baseline.get("player"),
                "candidate_player": candidate.get("player"),
                "policy_seat": policy_seat,
                "baseline_context": baseline.get("context"),
                "candidate_context": candidate.get("context"),
                "baseline_action": baseline.get("action"),
                "candidate_action": candidate.get("action"),
                "direct_policy_action_difference": (
                    baseline.get("player") == policy_seat
                    and candidate.get("player") == policy_seat
                    and baseline.get("action") != candidate.get("action")
                ),
                "differing_fields": differing_fields,
            }
    return {
        "trace_index": limit,
        "baseline_length": len(baseline_rows),
        "candidate_length": len(candidate_rows),
        "policy_seat": policy_seat,
        "direct_policy_action_difference": False,
        "differing_fields": ["trace_length"],
    }


def main() -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    spec_hash = sha256(SPEC_PATH)

    source_checks: list[dict[str, Any]] = []

    def add_source_check(label: str, relative_path: str | Path, expected: str | None) -> None:
        path = ROOT / Path(relative_path)
        observed = sha256(path) if path.is_file() else None
        source_checks.append(
            {
                "label": label,
                "path": path.relative_to(ROOT).as_posix() if path.exists() else str(relative_path),
                "expected_sha256": expected,
                "observed_sha256": observed,
                "matches": observed == expected if expected is not None else None,
            }
        )

    add_source_check("spec", SPEC_REL, EXPECTED_SPEC_SHA256)
    add_source_check("strategy", spec["strategy"]["path"], spec["strategy"]["sha256"])
    add_source_check("root_verification", spec["verification"]["path"], spec["verification"]["sha256"])
    add_source_check(
        "baseline_main",
        Path(spec["baseline"]["path"]) / POLICY_MAIN,
        spec["baseline"]["main_sha256"],
    )
    add_source_check(
        "baseline_deck",
        Path(spec["baseline"]["path"]) / POLICY_DECK,
        spec["baseline"]["deck_sha256"],
    )
    add_source_check(
        "candidate_main",
        Path(spec["candidate"]["path"]) / POLICY_MAIN,
        spec["candidate"]["main_sha256"],
    )
    add_source_check(
        "candidate_deck",
        Path(spec["candidate"]["path"]) / POLICY_DECK,
        spec["candidate"]["deck_sha256"],
    )
    for label, runner in sorted(spec["runners"].items()):
        add_source_check(f"runner_{label}", runner["path"], runner["sha256"])
    for relative_path, expected in sorted(spec["engine"]["files"].items()):
        add_source_check(
            f"engine_{relative_path}",
            Path(spec["engine"]["path"]) / relative_path,
            expected,
        )
    for opponent in spec["opponents"]:
        add_source_check(
            f"opponent_{opponent['label']}_main",
            Path(opponent["path"]) / POLICY_MAIN,
            opponent["main_sha256"],
        )
        add_source_check(
            f"opponent_{opponent['label']}_deck",
            Path(opponent["path"]) / POLICY_DECK,
            opponent["deck_sha256"],
        )

    historical = next(panel for panel in spec["panels"] if panel["label"] == "historical_silver")
    historical_path = Path(historical["opponents"][0]["path"])
    add_source_check("historical_silver_main_observed_only", historical_path / POLICY_MAIN, None)
    add_source_check("historical_silver_deck_observed_only", historical_path / POLICY_DECK, None)

    expected_keys: set[tuple[str, str, int, int]] = set()
    expected_cell_specs: dict[tuple[str, str, int], dict[str, Any]] = {}
    panel_specs = {panel["label"]: panel for panel in spec["panels"]}
    for panel in spec["panels"]:
        for opponent in panel["opponents"]:
            for seat in (0, 1):
                expected_cell_specs[(panel["label"], opponent["label"], seat)] = {
                    "seed_base": int(panel["seed_base"]),
                    "games": int(panel["games_per_seat"]),
                    "opponent_path": opponent["path"],
                }
                for game in range(int(panel["games_per_seat"])):
                    expected_keys.add(
                        schedule_key(
                            panel["label"],
                            opponent["label"],
                            seat,
                            int(panel["seed_base"]) + game,
                        )
                    )

    physical_headers: dict[str, list[str]] = {}
    raw_paired_rows: list[dict[str, Any]] = []
    critical_raw_files: dict[str, str] = {}
    runner_reports: dict[str, dict[str, Any]] = {}
    runner_cell_rows: dict[str, list[dict[str, str]]] = {}
    manifests: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    manifest_rows_total = 0
    manifest_duplicate_keys = 0
    manifest_nonzero_exits = 0
    manifest_command_faults: list[str] = []

    expected_python = (ROOT / Path(spec["python"])).resolve()
    expected_battle_runner = (ROOT / Path(spec["runners"]["checked_battle"]["path"])).resolve()
    expected_engine = (ROOT / Path(spec["engine"]["path"])).resolve()
    expected_baseline = (ROOT / Path(spec["baseline"]["path"])).resolve()
    expected_candidate = (ROOT / Path(spec["candidate"]["path"])).resolve()

    for panel_name, panel_spec in panel_specs.items():
        panel_dir = RAW_ROOT / panel_spec["output"]
        paired_path = panel_dir / "paired_results.csv"
        manifest_path = panel_dir / "manifest.jsonl"
        report_path = panel_dir / "report.json"
        cell_path = panel_dir / "cell_summary.csv"
        for path in (paired_path, manifest_path, report_path, cell_path):
            critical_raw_files[path.relative_to(ROOT).as_posix()] = sha256(path)

        with paired_path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            physical_headers[panel_name] = list(reader.fieldnames or [])
            for raw in reader:
                raw_paired_rows.append(
                    {
                        "panel": panel_name,
                        "seed_base": int(raw["seed_base"]),
                        "opponent": raw["opponent"],
                        "seat": int(raw["seat"]),
                        "game": int(raw["game"]),
                        "seed": int(raw["seed"]),
                        "baseline_result": int(raw["baseline_result"]),
                        "candidate_result": int(raw["candidate_result"]),
                        "baseline_win": int(raw["baseline_win"]),
                        "candidate_win": int(raw["candidate_win"]),
                        "baseline_steps": int(raw["baseline_steps"]),
                        "candidate_steps": int(raw["candidate_steps"]),
                    }
                )

        runner_reports[panel_name] = json.loads(report_path.read_text(encoding="utf-8"))
        with cell_path.open("r", newline="", encoding="utf-8") as handle:
            runner_cell_rows[panel_name] = list(csv.DictReader(handle))

        for manifest in read_jsonl(manifest_path):
            manifest_rows_total += 1
            key = (panel_name, manifest["opponent"], int(manifest["seat"]), manifest["role"])
            if key in manifests:
                manifest_duplicate_keys += 1
            manifests[key] = manifest
            if int(manifest.get("exit_code", -1)) != 0:
                manifest_nonzero_exits += 1

            command = [str(value) for value in manifest.get("command", [])]
            cell_spec = expected_cell_specs.get(key[:3])
            if not command or Path(command[0]).resolve() != expected_python:
                manifest_command_faults.append(f"{key}: python executable mismatch")
            if len(command) < 2 or Path(command[1]).resolve() != expected_battle_runner:
                manifest_command_faults.append(f"{key}: battle runner mismatch")
            if "--engine-seed" not in command:
                manifest_command_faults.append(f"{key}: --engine-seed missing")
            if command_arg(command, "--engine-dir") is None or Path(command_arg(command, "--engine-dir") or "").resolve() != expected_engine:
                manifest_command_faults.append(f"{key}: engine path mismatch")
            if cell_spec is None:
                manifest_command_faults.append(f"{key}: unexpected cell")
                continue
            if int(command_arg(command, "--games") or -1) != int(cell_spec["games"]):
                manifest_command_faults.append(f"{key}: games mismatch")
            if int(command_arg(command, "--seed-base") or -1) != int(cell_spec["seed_base"]):
                manifest_command_faults.append(f"{key}: seed-base mismatch")
            if int(command_arg(command, "--max-steps") or -1) != int(spec["max_steps"]):
                manifest_command_faults.append(f"{key}: max-steps mismatch")
            policy_path = expected_candidate if manifest["role"] == "candidate" else expected_baseline
            policy_arg = "--agent-a" if int(manifest["seat"]) == 0 else "--agent-b"
            if command_arg(command, policy_arg) is None or Path(command_arg(command, policy_arg) or "").resolve() != policy_path:
                manifest_command_faults.append(f"{key}: policy/player mapping mismatch")

    expected_manifest_keys = {
        (*cell_key, role)
        for cell_key in expected_cell_specs
        for role in ("baseline_a", "baseline_b", "candidate")
    }
    manifest_missing_keys = sorted(expected_manifest_keys - set(manifests))
    manifest_extra_keys = sorted(set(manifests) - expected_manifest_keys)

    summaries: dict[tuple[str, str, int, str], dict[int, dict[str, Any]]] = {}
    malformed_or_missing_summaries = 0
    summary_row_count = 0
    start_faults = 0
    action_errors = 0
    max_step_hits = 0
    explicit_exception_records = 0
    invalid_results = 0
    missing_traces = 0
    trace_step_count_mismatches = 0

    for key in sorted(expected_manifest_keys):
        manifest = manifests.get(key)
        if manifest is None:
            malformed_or_missing_summaries += 1
            continue
        command = [str(value) for value in manifest["command"]]
        summary_arg = command_arg(command, "--summary")
        if summary_arg is None:
            malformed_or_missing_summaries += 1
            continue
        summary_path = Path(summary_arg)
        try:
            rows = read_jsonl(summary_path)
        except (OSError, ValueError, json.JSONDecodeError):
            malformed_or_missing_summaries += 1
            continue
        expected_games = expected_cell_specs[key[:3]]["games"]
        if len(rows) != expected_games:
            malformed_or_missing_summaries += 1
        by_seed: dict[int, dict[str, Any]] = {}
        for row in rows:
            summary_row_count += 1
            seed = int(row.get("seed", -1))
            by_seed[seed] = row
            if row.get("started") is not True:
                start_faults += 1
            action_errors += int(row.get("action_errors", 0) or 0)
            max_step_hits += int(bool(row.get("hit_max_steps", False)))
            if any(row.get(field) for field in ("exception", "exception_type", "exception_message")):
                explicit_exception_records += 1
            if row.get("result") not in (0, 1):
                invalid_results += 1
            trace_value = row.get("trace")
            trace_path = Path(trace_value) if trace_value else None
            if trace_path is None or not trace_path.is_file():
                missing_traces += 1
            else:
                _, _, newline_count = hash_file(trace_path)
                if newline_count != int(row.get("steps", -1)):
                    trace_step_count_mismatches += 1
        summaries[key] = by_seed

    role_schedule_sets: dict[str, set[tuple[str, str, int, int]]] = defaultdict(set)
    role_schedule_duplicate_counts: Counter[str] = Counter()
    for (panel, opponent, seat, role), rows_by_seed in summaries.items():
        for seed in rows_by_seed:
            key = schedule_key(panel, opponent, seat, seed)
            if key in role_schedule_sets[role]:
                role_schedule_duplicate_counts[role] += 1
            role_schedule_sets[role].add(key)

    paired_keys = [
        schedule_key(row["panel"], row["opponent"], row["seat"], row["seed"])
        for row in raw_paired_rows
    ]
    paired_key_counts = Counter(paired_keys)
    paired_duplicate_key_count = sum(count - 1 for count in paired_key_counts.values() if count > 1)

    duplicate_game_field_matches = 0
    duplicate_result_matches = 0
    duplicate_step_matches = 0
    duplicate_normalized_summary_matches = 0
    duplicate_trace_byte_matches = 0
    candidate_normalized_summary_matches = 0
    candidate_trace_byte_matches = 0
    candidate_trace_byte_mismatches = 0
    candidate_first_direct_action_differences = 0
    first_difference_context_counts: Counter[str] = Counter()
    first_difference_examples: list[dict[str, Any]] = []

    recomputed_rows: list[dict[str, Any]] = []
    raw_by_key = {
        schedule_key(row["panel"], row["opponent"], row["seat"], row["seed"]): row
        for row in raw_paired_rows
    }
    raw_pair_discrepancies: list[dict[str, Any]] = []

    for logical_key in sorted(expected_keys):
        panel, opponent, seat, seed = logical_key
        baseline_a = summaries.get((panel, opponent, seat, "baseline_a"), {}).get(seed)
        baseline_b = summaries.get((panel, opponent, seat, "baseline_b"), {}).get(seed)
        candidate = summaries.get((panel, opponent, seat, "candidate"), {}).get(seed)
        if baseline_a is None or baseline_b is None or candidate is None:
            continue

        if tuple(baseline_a.get(field) for field in GAME_FIELDS) == tuple(baseline_b.get(field) for field in GAME_FIELDS):
            duplicate_game_field_matches += 1
        if baseline_a.get("result") == baseline_b.get("result"):
            duplicate_result_matches += 1
        if baseline_a.get("steps") == baseline_b.get("steps"):
            duplicate_step_matches += 1
        if normalized_summary(baseline_a) == normalized_summary(baseline_b):
            duplicate_normalized_summary_matches += 1
        if sha256(Path(baseline_a["trace"])) == sha256(Path(baseline_b["trace"])):
            duplicate_trace_byte_matches += 1

        if normalized_summary(baseline_a) == normalized_summary(candidate):
            candidate_normalized_summary_matches += 1
        candidate_trace_equal = sha256(Path(baseline_a["trace"])) == sha256(Path(candidate["trace"]))
        if candidate_trace_equal:
            candidate_trace_byte_matches += 1
        else:
            candidate_trace_byte_mismatches += 1
            difference = first_trace_difference(Path(baseline_a["trace"]), Path(candidate["trace"]), seat)
            if difference["direct_policy_action_difference"]:
                candidate_first_direct_action_differences += 1
            context_key = str(difference.get("baseline_context"))
            first_difference_context_counts[context_key] += 1
            if len(first_difference_examples) < 8:
                first_difference_examples.append(
                    {
                        "panel": panel,
                        "opponent": opponent,
                        "seat": seat,
                        "seed": seed,
                        **difference,
                    }
                )

        baseline_result = int(baseline_a["result"])
        candidate_result = int(candidate["result"])
        # run_local_battle result is the winning player index.  The tested
        # policy is player 0 in seat 0 and player 1 in seat 1.
        recomputed = {
            "panel": panel,
            "opponent": opponent,
            "seat": seat,
            "seed": seed,
            "baseline_result": baseline_result,
            "candidate_result": candidate_result,
            "baseline_win": int(baseline_result == seat),
            "candidate_win": int(candidate_result == seat),
            "baseline_steps": int(baseline_a["steps"]),
            "candidate_steps": int(candidate["steps"]),
        }
        recomputed_rows.append(recomputed)
        raw = raw_by_key.get(logical_key)
        if raw is None:
            raw_pair_discrepancies.append({"key": logical_key, "reason": "missing raw paired row"})
        else:
            differing = [
                field
                for field in (
                    "baseline_result",
                    "candidate_result",
                    "baseline_win",
                    "candidate_win",
                    "baseline_steps",
                    "candidate_steps",
                )
                if raw[field] != recomputed[field]
            ]
            if differing:
                raw_pair_discrepancies.append({"key": logical_key, "differing_fields": differing})

    aggregate = summarize(recomputed_rows)
    by_panel = grouped_summaries(recomputed_rows, ("panel",))
    by_panel_opponent = grouped_summaries(recomputed_rows, ("panel", "opponent"))
    by_cell = grouped_summaries(recomputed_rows, ("panel", "opponent", "seat"))
    by_seat = grouped_summaries(recomputed_rows, ("seat",))

    step_diff_rows = [row for row in recomputed_rows if row["baseline_steps"] != row["candidate_steps"]]
    step_change = {
        "different_step_count": len(step_diff_rows),
        "candidate_shorter_count": sum(row["candidate_steps"] < row["baseline_steps"] for row in step_diff_rows),
        "candidate_longer_count": sum(row["candidate_steps"] > row["baseline_steps"] for row in step_diff_rows),
        "net_candidate_minus_baseline_steps": sum(
            row["candidate_steps"] - row["baseline_steps"] for row in recomputed_rows
        ),
        "total_baseline_steps": sum(row["baseline_steps"] for row in recomputed_rows),
        "total_candidate_steps": sum(row["candidate_steps"] for row in recomputed_rows),
        "changed_games_both_policy_wins": sum(
            row["baseline_win"] == 1 and row["candidate_win"] == 1 for row in step_diff_rows
        ),
        "by_cell": grouped_summaries(step_diff_rows, ("panel", "opponent", "seat")) if step_diff_rows else [],
    }

    seed_groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in recomputed_rows:
        seed_groups[(row["panel"], row["seed"])].append(row)
    seed_sensitivity: list[dict[str, Any]] = []
    for panel in sorted(panel_specs):
        panel_rates: list[float] = []
        panel_deltas: list[float] = []
        for (group_panel, _seed), rows in sorted(seed_groups.items()):
            if group_panel != panel:
                continue
            summary = summarize(rows)
            panel_rates.append(float(summary["candidate_rate"]))
            panel_deltas.append(float(summary["delta_rate"]))
        seed_sensitivity.append(
            {
                "panel": panel,
                "distinct_engine_seeds": len(panel_rates),
                "games_per_seed": sorted({len(rows) for (group_panel, _), rows in seed_groups.items() if group_panel == panel}),
                "candidate_seed_group_rate_min": min(panel_rates),
                "candidate_seed_group_rate_max": max(panel_rates),
                "candidate_seed_group_rate_sd": statistics.pstdev(panel_rates),
                "paired_delta_min": min(panel_deltas),
                "paired_delta_max": max(panel_deltas),
                "paired_delta_sd": statistics.pstdev(panel_deltas),
            }
        )

    runner_discrepancies: list[str] = []
    for panel_row in by_panel:
        panel = panel_row["panel"]
        report = runner_reports[panel]
        expected_aggregate = report.get("aggregates", {})
        for field in ("baseline_wins", "candidate_wins", "games", "delta_wins"):
            observed = panel_row[field]
            if int(expected_aggregate.get(field, -999999)) != int(observed):
                runner_discrepancies.append(f"{panel} report aggregate {field}")
        if report.get("valid") is not True or report.get("invalid_reasons") != []:
            runner_discrepancies.append(f"{panel} runner validity flags")
        if int(report.get("duplicate_mismatch_count", -1)) != 0:
            runner_discrepancies.append(f"{panel} duplicate mismatch report")

        cell_lookup = {
            (row["opponent"], int(row["seat"])): row for row in runner_cell_rows[panel]
        }
        for cell in [row for row in by_cell if row["panel"] == panel]:
            raw_cell = cell_lookup.get((cell["opponent"], int(cell["seat"])))
            if raw_cell is None:
                runner_discrepancies.append(f"{panel}/{cell['opponent']}/p{cell['seat']} missing cell summary")
                continue
            for field in ("games", "baseline_wins", "candidate_wins", "delta_wins"):
                if int(raw_cell[field]) != int(cell[field]):
                    runner_discrepancies.append(f"{panel}/{cell['opponent']}/p{cell['seat']} {field}")

    severe_floor_threshold = 0.40
    severe_cells = [
        {
            "panel": row["panel"],
            "opponent": row["opponent"],
            "seat": row["seat"],
            "candidate_wins": row["candidate_wins"],
            "games": row["games"],
            "candidate_rate": row["candidate_rate"],
        }
        for row in by_cell
        if float(row["candidate_rate"]) < severe_floor_threshold
    ]
    below_half_cells = [
        {
            "panel": row["panel"],
            "opponent": row["opponent"],
            "seat": row["seat"],
            "candidate_rate": row["candidate_rate"],
        }
        for row in by_cell
        if float(row["candidate_rate"]) < 0.50
    ]

    raw_files_before = {
        path.resolve(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in RAW_ROOT.rglob("*")
        if path.is_file()
    }
    raw_tree_digest = hashlib.sha256()
    raw_total_bytes = 0
    for path in sorted(raw_files_before, key=lambda value: value.relative_to(RAW_ROOT).as_posix()):
        digest, size, _ = hash_file(path)
        raw_total_bytes += size
        relative = path.relative_to(RAW_ROOT).as_posix()
        raw_tree_digest.update(relative.encode("utf-8"))
        raw_tree_digest.update(b"\0")
        raw_tree_digest.update(bytes.fromhex(digest))
        raw_tree_digest.update(b"\n")
    raw_files_after = {
        path.resolve(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in RAW_ROOT.rglob("*")
        if path.is_file()
    }
    raw_snapshot_stable = raw_files_before == raw_files_after

    execution_faults = (
        manifest_nonzero_exits
        + len(manifest_missing_keys)
        + len(manifest_extra_keys)
        + manifest_duplicate_keys
        + malformed_or_missing_summaries
        + missing_traces
        + invalid_results
        + trace_step_count_mismatches
        + len(manifest_command_faults)
    )
    exception_count = explicit_exception_records + manifest_nonzero_exits
    regressing_cells = sum(row["delta_wins"] < 0 for row in by_cell)
    gates = spec["gates"]
    gate_results = {
        "unique_schedule_keys": {
            "required": gates["unique_schedule_keys"],
            "observed": len(paired_key_counts),
            "pass": len(paired_key_counts) == gates["unique_schedule_keys"] and paired_duplicate_key_count == 0,
        },
        "duplicate_summary_matches": {
            "required": gates["duplicate_summary_matches"],
            "observed": duplicate_game_field_matches,
            "pass": duplicate_game_field_matches == gates["duplicate_summary_matches"],
        },
        "duplicate_byte_trace_matches": {
            "required": gates["duplicate_byte_trace_matches"],
            "observed": duplicate_trace_byte_matches,
            "pass": duplicate_trace_byte_matches == gates["duplicate_byte_trace_matches"],
        },
        "execution_faults": {
            "required": gates["execution_faults"],
            "observed": execution_faults,
            "pass": execution_faults == gates["execution_faults"],
        },
        "start_faults": {
            "required": gates["start_faults"],
            "observed": start_faults,
            "pass": start_faults == gates["start_faults"],
        },
        "action_errors": {
            "required": gates["action_errors"],
            "observed": action_errors,
            "pass": action_errors == gates["action_errors"],
        },
        "exceptions": {
            "required": gates["exceptions"],
            "observed": exception_count,
            "pass": exception_count == gates["exceptions"],
        },
        "max_step_hits": {
            "required": gates["max_step_hits"],
            "observed": max_step_hits,
            "pass": max_step_hits == gates["max_step_hits"],
        },
        "panel_seat_opponent_cell_regressions": {
            "required": gates["panel_seat_opponent_cell_regressions"],
            "observed": regressing_cells,
            "pass": regressing_cells == gates["panel_seat_opponent_cell_regressions"],
        },
    }

    required_schema = set(spec["required_output_schema"])
    physical_schema_has_panel = all("panel" in header for header in physical_headers.values())
    logical_fields = set(raw_paired_rows[0]) if raw_paired_rows else set()
    output = {
        "audit": {
            "spec_path": SPEC_REL.as_posix(),
            "spec_sha256": spec_hash,
            "spec_sha_matches": spec_hash == EXPECTED_SPEC_SHA256,
            "raw_root": RAW_REL.as_posix(),
            "raw_file_count": len(raw_files_before),
            "raw_total_bytes": raw_total_bytes,
            "raw_tree_sha256": raw_tree_digest.hexdigest().upper(),
            "raw_tree_hash_definition": "SHA256 over sorted relative POSIX path + NUL + binary file SHA256 + LF",
            "raw_snapshot_stable_during_audit": raw_snapshot_stable,
            "critical_raw_file_sha256": critical_raw_files,
        },
        "source_hash_checks": source_checks,
        "source_expected_hash_mismatch_count": sum(check["matches"] is False for check in source_checks),
        "historical_silver_hash_note": "Current main/deck hashes are recorded, but fixed760_spec supplies no expected hash for the historical_silver panel opponent.",
        "schema": {
            "physical_csv_headers": physical_headers,
            "physical_panel_column_present": physical_schema_has_panel,
            "logical_panel_materialization": "panel is added from the spec-declared partition directory",
            "logical_required_schema_satisfied": required_schema <= logical_fields,
            "missing_logical_required_fields": sorted(required_schema - logical_fields),
        },
        "schedule": {
            "expected_logical_rows": len(expected_keys),
            "raw_paired_rows": len(raw_paired_rows),
            "unique_raw_schedule_keys": len(paired_key_counts),
            "raw_duplicate_schedule_key_count": paired_duplicate_key_count,
            "raw_keys_equal_expected": set(paired_key_counts) == expected_keys,
            "manifest_rows": manifest_rows_total,
            "manifest_expected_rows": len(expected_manifest_keys),
            "manifest_duplicate_keys": manifest_duplicate_keys,
            "manifest_missing_keys": manifest_missing_keys,
            "manifest_extra_keys": manifest_extra_keys,
            "manifest_command_fault_count": len(manifest_command_faults),
            "manifest_command_faults": manifest_command_faults,
            "summary_rows_all_three_roles": summary_row_count,
            "role_schedule_counts": {role: len(keys) for role, keys in sorted(role_schedule_sets.items())},
            "role_duplicate_schedule_counts": dict(role_schedule_duplicate_counts),
            "baseline_a_schedule_equals_candidate": role_schedule_sets["baseline_a"] == role_schedule_sets["candidate"],
            "baseline_a_schedule_equals_baseline_b": role_schedule_sets["baseline_a"] == role_schedule_sets["baseline_b"],
            "all_role_schedules_equal_expected": all(role_schedule_sets[role] == expected_keys for role in ("baseline_a", "baseline_b", "candidate")),
        },
        "player_mapping": {
            "seat_0": "tested policy is agent A / player 0; win iff run_local_battle result == 0",
            "seat_1": "tested policy is agent B / player 1; win iff run_local_battle result == 1",
            "mapping_manifest_verified": not any("policy/player mapping mismatch" in fault for fault in manifest_command_faults),
        },
        "faults": {
            "manifest_nonzero_exits": manifest_nonzero_exits,
            "malformed_or_missing_summaries": malformed_or_missing_summaries,
            "start_faults_all_roles": start_faults,
            "action_errors_all_roles": action_errors,
            "explicit_exception_records": explicit_exception_records,
            "exception_proxy_including_nonzero_exits": exception_count,
            "max_step_hits_all_roles": max_step_hits,
            "invalid_terminal_results_all_roles": invalid_results,
            "missing_trace_files": missing_traces,
            "trace_line_count_vs_steps_mismatches": trace_step_count_mismatches,
            "execution_fault_composite": execution_faults,
        },
        "duplicate_control": {
            "game_field_matches": duplicate_game_field_matches,
            "result_matches": duplicate_result_matches,
            "decision_count_matches": duplicate_step_matches,
            "full_summary_matches_excluding_trace_path": duplicate_normalized_summary_matches,
            "byte_trace_matches": duplicate_trace_byte_matches,
        },
        "independent_recompute": {
            "recomputed_rows": len(recomputed_rows),
            "raw_paired_row_discrepancy_count": len(raw_pair_discrepancies),
            "raw_paired_row_discrepancies": raw_pair_discrepancies[:20],
            "runner_report_or_cell_discrepancy_count": len(runner_discrepancies),
            "runner_report_or_cell_discrepancies": runner_discrepancies,
            "aggregate": aggregate,
            "by_panel": by_panel,
            "by_panel_opponent": by_panel_opponent,
            "by_panel_opponent_seat": by_cell,
            "by_seat_all_panels": by_seat,
        },
        "mechanism_and_step_shadow": {
            "candidate_full_summary_matches_excluding_trace_path": candidate_normalized_summary_matches,
            "candidate_byte_trace_matches": candidate_trace_byte_matches,
            "candidate_byte_trace_mismatches": candidate_trace_byte_mismatches,
            "mismatches_with_direct_policy_action_as_first_difference": candidate_first_direct_action_differences,
            "first_difference_context_counts": dict(sorted(first_difference_context_counts.items())),
            "first_difference_compact_examples": first_difference_examples,
            "step_change": step_change,
            "interpretation_boundary": "A changed action/trace establishes behavioral activation on this schedule, but unchanged terminal outcomes establish zero observed strength gain; the raw trace alone does not name the source-level branch responsible.",
        },
        "seed_sensitivity": seed_sensitivity,
        "floors": {
            "descriptive_severe_floor_threshold": severe_floor_threshold,
            "threshold_is_acceptance_gate": False,
            "severe_cells": severe_cells,
            "below_half_cells": below_half_cells,
        },
        "uncertainty": {
            "design": "matched binary outcomes on identical panel/opponent/seat/engine-seed keys",
            "fixed_schedule_delta": aggregate["delta_rate"],
            "mcnemar_exact_two_sided_p": aggregate["mcnemar_exact_two_sided_p"],
            "paired_delta_conservative95": aggregate["paired_delta_conservative95"],
            "paired_interval_method": "zero-discordance exact one-sided Clopper-Pearson upper bound q_U=1-0.05^(1/n), then |paired risk difference|<=q",
            "inference_assumption": "Interval generalizes only if the fixed engine seeds/cells are treated as exchangeable draws from a target schedule population; the audited fixed-schedule delta itself is exactly known.",
        },
        "acceptance_gates": gate_results,
        "all_supplied_gates_pass": all(result["pass"] for result in gate_results.values()),
    }
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
