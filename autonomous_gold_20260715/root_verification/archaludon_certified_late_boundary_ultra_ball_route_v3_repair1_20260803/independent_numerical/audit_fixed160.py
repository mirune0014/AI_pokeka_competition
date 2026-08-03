from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


OUT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[4]
OVERLAY_SPEC = REPO_ROOT / (
    "autonomous_gold_20260715/evaluation_specs/"
    "archaludon_certified_late_boundary_ultra_ball_route_v3_repair1/"
    "fixed160_spec.json"
)
RAW_ROOT = REPO_ROOT / (
    "autonomous_gold_20260715/evaluations/"
    "archaludon_certified_late_boundary_ultra_ball_route_v3_repair1/"
    "fixed160_raw"
)

EXPECTED_HASHES = {
    "overlay_spec": "7C8BF76AAAF1909F4DD364DBD7184062F5DC29AC0968B6414EA3E1CD61A3A96F",
    "candidate_main": "3D95357E75E0B00CB679C1A31F6612AD1FA0EF44914E8ECA8C272CE9220027C3",
    "baseline_main": "4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35",
    "historical_silver/paired_results.csv": "1117F92F98A668D9DF22CE829BCB3D075E56E524DE3A96CD2BE68E676A5BFCF8",
    "historical_silver/report.json": "37706612165C1E2D80C3485C70D0AC571CF6F7148EA79C96B342390A376B7315",
    "historical_silver/cell_summary.csv": "BD30AEA1526B09FAE2147F5DE0D072AB56BCC0546E2B6485E5A938090F89A1F4",
    "historical_silver/manifest.jsonl": "510C4E606DDA0B0991F5344F92C6E7CE3A35FFA176258E7185DB81DCB4092D47",
    "adjacent_population/paired_results.csv": "F6B2596699ABB1CE767EF35B39A38A75DB4F2229DCED2132F8BFE4D9A6CA771E",
    "adjacent_population/report.json": "AF692679EE949E2D6B72A3EE1283361A1F6A1A5C7A1DFEB16FF6F7D639BBCCE4",
    "adjacent_population/cell_summary.csv": "BAF347F4C437B5028B053CC2601A2562DCCBD4EEC053E225505EB42258B0E96C",
    "adjacent_population/manifest.jsonl": "0E2A7445A8F1DD684B46A29A39A4EB1A257CE80589144FB0B68FA630B9BEB194",
}

PAIRED_FIELDS = [
    "seed_base",
    "opponent",
    "seat",
    "game",
    "seed",
    "baseline_result",
    "candidate_result",
    "baseline_win",
    "candidate_win",
    "baseline_steps",
    "candidate_steps",
]
DUPLICATE_FIELDS = (
    "seed",
    "result",
    "steps",
    "turn",
    "action_errors",
    "hit_max_steps",
)
ROLES = ("baseline_a", "baseline_b", "candidate")
Z_95 = 1.959963984540054


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise AssertionError(f"non-object JSONL row: {path}:{line_number}")
        rows.append(value)
    return rows


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def arg_after(command: list[str], flag: str) -> str | None:
    try:
        index = command.index(flag)
    except ValueError:
        return None
    return command[index + 1] if index + 1 < len(command) else None


def canonical(path_text: str | None) -> str | None:
    if path_text is None:
        return None
    return str(Path(path_text).resolve()).casefold()


def wilson_95(wins: int, games: int) -> tuple[float | None, float | None]:
    if games == 0:
        return None, None
    rate = wins / games
    z2 = Z_95 * Z_95
    denominator = 1.0 + z2 / games
    center = (rate + z2 / (2.0 * games)) / denominator
    half = (
        Z_95
        * math.sqrt(rate * (1.0 - rate) / games + z2 / (4.0 * games * games))
        / denominator
    )
    return center - half, center + half


def zero_event_upper(n: int, *, alpha: float, two_sided: bool) -> float | None:
    if n <= 0:
        return None
    tail = alpha / 2.0 if two_sided else alpha
    return 1.0 - tail ** (1.0 / n)


def group_summary(label: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    games = len(rows)
    baseline_wins = sum(int(row["baseline_win"]) for row in rows)
    candidate_wins = sum(int(row["candidate_win"]) for row in rows)
    gains = sum(
        int(row["baseline_win"]) == 0 and int(row["candidate_win"]) == 1
        for row in rows
    )
    regressions = sum(
        int(row["baseline_win"]) == 1 and int(row["candidate_win"]) == 0
        for row in rows
    )
    ties = games - gains - regressions
    discordant = gains + regressions
    baseline_ci = wilson_95(baseline_wins, games)
    candidate_ci = wilson_95(candidate_wins, games)
    discordance_upper = zero_event_upper(games, alpha=0.05, two_sided=True)
    return {
        "label": label,
        "games": games,
        "baseline_wins": baseline_wins,
        "candidate_wins": candidate_wins,
        "baseline_rate": baseline_wins / games if games else None,
        "candidate_rate": candidate_wins / games if games else None,
        "baseline_wilson_95_low": baseline_ci[0],
        "baseline_wilson_95_high": baseline_ci[1],
        "candidate_wilson_95_low": candidate_ci[0],
        "candidate_wilson_95_high": candidate_ci[1],
        "delta_wins": candidate_wins - baseline_wins,
        "delta_rate": (candidate_wins - baseline_wins) / games if games else None,
        "gains": gains,
        "regressions": regressions,
        "ties": ties,
        "discordant": discordant,
        "zero_discordance_two_sided_95_upper": discordance_upper
        if discordant == 0
        else None,
        "conservative_signed_delta_95_low": -discordance_upper
        if discordant == 0 and discordance_upper is not None
        else None,
        "conservative_signed_delta_95_high": discordance_upper
        if discordant == 0 and discordance_upper is not None
        else None,
    }


def summary_without_trace(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "trace"}


def main() -> None:
    overlay = read_json(OVERLAY_SPEC)
    base_spec_path = REPO_ROOT / overlay["schedule_base"]["path"]
    base_spec = read_json(base_spec_path)
    candidate_main = REPO_ROOT / overlay["candidate"]["path"] / "main.py"
    baseline_main = REPO_ROOT / overlay["baseline"]["path"] / "main.py"

    input_paths: dict[str, Path] = {
        "overlay_spec": OVERLAY_SPEC,
        "schedule_base": base_spec_path,
        "candidate_main": candidate_main,
        "baseline_main": baseline_main,
    }
    for panel in ("historical_silver", "adjacent_population"):
        for name in ("paired_results.csv", "report.json", "cell_summary.csv", "manifest.jsonl"):
            input_paths[f"{panel}/{name}"] = RAW_ROOT / panel / name

    input_hashes: dict[str, dict[str, Any]] = {}
    hash_mismatches: list[dict[str, str]] = []
    for label, path in input_paths.items():
        actual = sha256(path)
        expected = (
            overlay["schedule_base"]["sha256"]
            if label == "schedule_base"
            else EXPECTED_HASHES.get(label)
        )
        input_hashes[label] = {
            "path": rel(path),
            "sha256": actual,
            "expected_sha256": expected,
            "matches": expected is None or actual == expected,
        }
        if expected is not None and actual != expected:
            hash_mismatches.append({"label": label, "expected": expected, "actual": actual})

    if overlay["candidate"]["main_sha256"] != EXPECTED_HASHES["candidate_main"]:
        raise AssertionError("overlay candidate hash does not match immutable parent value")
    if overlay["baseline"]["main_sha256"] != EXPECTED_HASHES["baseline_main"]:
        raise AssertionError("overlay baseline hash does not match immutable parent value")
    if hash_mismatches:
        raise AssertionError(f"input hash mismatches: {hash_mismatches}")

    panel_specs = {panel["label"]: panel for panel in base_spec["panels"]}
    opponent_paths: dict[tuple[str, str], Path] = {}
    expected_keys: set[tuple[str, str, int, int]] = set()
    expected_cells: set[tuple[str, str, int]] = set()
    for panel_name, panel_spec in panel_specs.items():
        seed_base = int(panel_spec["seed_base"])
        games = int(panel_spec["games_per_seat"])
        for opponent in panel_spec["opponents"]:
            opponent_name = opponent["label"]
            opponent_paths[(panel_name, opponent_name)] = REPO_ROOT / opponent["path"]
            for seat in (0, 1):
                expected_cells.add((panel_name, opponent_name, seat))
                for game in range(games):
                    expected_keys.add((panel_name, opponent_name, seat, seed_base + game))

    runs: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    manifest_counts: dict[str, int] = {}
    manifest_exit_faults: list[dict[str, Any]] = []
    command_faults: list[dict[str, Any]] = []
    duplicate_manifest_keys: list[tuple[str, str, int, str]] = []

    for panel_name, panel_spec in panel_specs.items():
        panel_root = RAW_ROOT / panel_spec["output"]
        manifest_rows = read_jsonl(panel_root / "manifest.jsonl")
        manifest_counts[panel_name] = len(manifest_rows)
        seen_manifest: Counter[tuple[str, str, int, str]] = Counter()
        for manifest in manifest_rows:
            role = str(manifest["role"])
            opponent = str(manifest["opponent"])
            seat = int(manifest["seat"])
            key = (panel_name, opponent, seat, role)
            seen_manifest[key] += 1
            command = [str(value) for value in manifest["command"]]
            faults: list[str] = []
            if int(manifest["exit_code"]) != 0:
                manifest_exit_faults.append(
                    {"panel": panel_name, "opponent": opponent, "seat": seat, "role": role, "exit_code": manifest["exit_code"]}
                )
            if role not in ROLES:
                faults.append("unexpected_role")
            if opponent not in {item["label"] for item in panel_spec["opponents"]}:
                faults.append("unexpected_opponent")
            if seat not in (0, 1):
                faults.append("invalid_seat")
            if not command or not command[0].casefold().endswith(
                str(Path(".venv-rl/Scripts/python.exe")).replace("/", "\\").casefold()
            ):
                faults.append("wrong_python")
            if len(command) < 2 or canonical(command[1]) != canonical(str(REPO_ROOT / "tools/run_local_battle.py")):
                faults.append("wrong_runner")
            if "--engine-seed" not in command:
                faults.append("missing_engine_seed")
            if arg_after(command, "--games") != str(panel_spec["games_per_seat"]):
                faults.append("wrong_games")
            if arg_after(command, "--max-steps") != str(base_spec["max_steps"]):
                faults.append("wrong_max_steps")
            if arg_after(command, "--seed-base") != str(panel_spec["seed_base"]):
                faults.append("wrong_seed_base")

            policy_path = (
                REPO_ROOT / overlay["candidate"]["path"]
                if role == "candidate"
                else REPO_ROOT / overlay["baseline"]["path"]
            )
            opponent_path = opponent_paths.get((panel_name, opponent))
            expected_agent_a = policy_path if seat == 0 else opponent_path
            expected_agent_b = opponent_path if seat == 0 else policy_path
            if expected_agent_a is None or canonical(arg_after(command, "--agent-a")) != canonical(str(expected_agent_a)):
                faults.append("wrong_agent_a")
            if expected_agent_b is None or canonical(arg_after(command, "--agent-b")) != canonical(str(expected_agent_b)):
                faults.append("wrong_agent_b")
            if canonical(arg_after(command, "--deck-a")) != canonical(str(expected_agent_a / "deck.csv")):
                faults.append("wrong_deck_a")
            if canonical(arg_after(command, "--deck-b")) != canonical(str(expected_agent_b / "deck.csv")):
                faults.append("wrong_deck_b")

            summary_text = arg_after(command, "--summary")
            if summary_text is None:
                faults.append("missing_summary_arg")
                summary_path = panel_root / "__missing_summary__"
                summary_rows: list[dict[str, Any]] = []
            else:
                summary_path = Path(summary_text)
                try:
                    summary_path.resolve().relative_to((panel_root / "summaries").resolve())
                except ValueError:
                    faults.append("summary_outside_panel")
                summary_rows = read_jsonl(summary_path)

            if faults:
                command_faults.append(
                    {"panel": panel_name, "opponent": opponent, "seat": seat, "role": role, "faults": faults}
                )
            runs[key] = {
                "manifest": manifest,
                "summary_path": summary_path,
                "rows": summary_rows,
            }

        duplicate_manifest_keys.extend(
            key for key, count in seen_manifest.items() if count != 1
        )

    expected_run_keys = {
        (panel, opponent, seat, role)
        for panel, opponent, seat in expected_cells
        for role in ROLES
    }
    run_key_missing = sorted(expected_run_keys - set(runs))
    run_key_extra = sorted(set(runs) - expected_run_keys)

    summary_schedule: dict[str, set[tuple[str, str, int, int]]] = {
        role: set() for role in ROLES
    }
    summary_duplicate_keys: dict[str, list[tuple[str, str, int, int]]] = {
        role: [] for role in ROLES
    }
    summary_row_count_faults: list[dict[str, Any]] = []
    summary_seed_faults: list[dict[str, Any]] = []
    start_faults: list[dict[str, Any]] = []
    action_faults: list[dict[str, Any]] = []
    max_step_faults: list[dict[str, Any]] = []
    invalid_result_faults: list[dict[str, Any]] = []
    exception_faults: list[dict[str, Any]] = []

    for (panel, opponent, seat, role), run in runs.items():
        rows = run["rows"]
        games_expected = int(panel_specs[panel]["games_per_seat"])
        seed_base = int(panel_specs[panel]["seed_base"])
        if len(rows) != games_expected:
            summary_row_count_faults.append(
                {"panel": panel, "opponent": opponent, "seat": seat, "role": role, "expected": games_expected, "actual": len(rows)}
            )
        local_keys: Counter[tuple[str, str, int, int]] = Counter()
        for row_index, row in enumerate(rows):
            game = int(row.get("game", -1))
            seed = int(row.get("seed", -1))
            key = (panel, opponent, seat, seed)
            local_keys[key] += 1
            summary_schedule[role].add(key)
            if game != row_index or seed != seed_base + game:
                summary_seed_faults.append(
                    {"panel": panel, "opponent": opponent, "seat": seat, "role": role, "row_index": row_index, "game": game, "seed": seed}
                )
            if row.get("started") is not True:
                start_faults.append(
                    {"panel": panel, "opponent": opponent, "seat": seat, "role": role, "game": game, "value": row.get("started")}
                )
            action_errors = int(row.get("action_errors", 0) or 0)
            if action_errors != 0:
                action_faults.append(
                    {"panel": panel, "opponent": opponent, "seat": seat, "role": role, "game": game, "action_errors": action_errors}
                )
            if row.get("hit_max_steps") is not False:
                max_step_faults.append(
                    {"panel": panel, "opponent": opponent, "seat": seat, "role": role, "game": game, "value": row.get("hit_max_steps")}
                )
            if row.get("result") not in (0, 1, 2):
                invalid_result_faults.append(
                    {"panel": panel, "opponent": opponent, "seat": seat, "role": role, "game": game, "result": row.get("result")}
                )
            for field in ("exception", "exceptions", "error", "errors"):
                if row.get(field):
                    exception_faults.append(
                        {"panel": panel, "opponent": opponent, "seat": seat, "role": role, "game": game, "field": field, "value": row[field]}
                    )
        summary_duplicate_keys[role].extend(
            key for key, count in local_keys.items() if count != 1
        )

    schedule_checks = {
        role: {
            "unique_keys": len(summary_schedule[role]),
            "missing": sorted(expected_keys - summary_schedule[role]),
            "extra": sorted(summary_schedule[role] - expected_keys),
            "duplicates": sorted(summary_duplicate_keys[role]),
        }
        for role in ROLES
    }

    duplicate_field_mismatches: list[dict[str, Any]] = []
    duplicate_full_summary_mismatches: list[dict[str, Any]] = []
    duplicate_trace_mismatches: list[dict[str, Any]] = []
    duplicate_trace_missing: list[dict[str, Any]] = []
    candidate_step_mismatches: list[dict[str, Any]] = []
    candidate_result_mismatches: list[dict[str, Any]] = []
    reconstructed_rows: list[dict[str, Any]] = []

    for panel, opponent, seat in sorted(expected_cells):
        baseline_a = runs[(panel, opponent, seat, "baseline_a")]["rows"]
        baseline_b = runs[(panel, opponent, seat, "baseline_b")]["rows"]
        candidate = runs[(panel, opponent, seat, "candidate")]["rows"]
        seed_base = int(panel_specs[panel]["seed_base"])
        for game in range(int(panel_specs[panel]["games_per_seat"])):
            left, duplicate, tested = baseline_a[game], baseline_b[game], candidate[game]
            field_differences = {
                field: [left.get(field), duplicate.get(field)]
                for field in DUPLICATE_FIELDS
                if left.get(field) != duplicate.get(field)
            }
            if field_differences:
                duplicate_field_mismatches.append(
                    {"panel": panel, "opponent": opponent, "seat": seat, "game": game, "differences": field_differences}
                )
            if summary_without_trace(left) != summary_without_trace(duplicate):
                duplicate_full_summary_mismatches.append(
                    {"panel": panel, "opponent": opponent, "seat": seat, "game": game}
                )
            trace_a = Path(str(left.get("trace", "")))
            trace_b = Path(str(duplicate.get("trace", "")))
            if not trace_a.is_file() or not trace_b.is_file():
                duplicate_trace_missing.append(
                    {"panel": panel, "opponent": opponent, "seat": seat, "game": game, "trace_a": str(trace_a), "trace_b": str(trace_b)}
                )
            elif sha256(trace_a) != sha256(trace_b):
                duplicate_trace_mismatches.append(
                    {"panel": panel, "opponent": opponent, "seat": seat, "game": game}
                )
            if left.get("steps") != tested.get("steps"):
                candidate_step_mismatches.append(
                    {"panel": panel, "opponent": opponent, "seat": seat, "game": game, "baseline_steps": left.get("steps"), "candidate_steps": tested.get("steps")}
                )
            if left.get("result") != tested.get("result"):
                candidate_result_mismatches.append(
                    {"panel": panel, "opponent": opponent, "seat": seat, "game": game, "baseline_result": left.get("result"), "candidate_result": tested.get("result")}
                )
            reconstructed_rows.append(
                {
                    "panel": panel,
                    "seed_base": seed_base,
                    "opponent": opponent,
                    "seat": seat,
                    "game": game,
                    "seed": int(left["seed"]),
                    "baseline_result": int(left["result"]),
                    "candidate_result": int(tested["result"]),
                    "baseline_win": int(int(left["result"]) == seat),
                    "candidate_win": int(int(tested["result"]) == seat),
                    "baseline_steps": int(left["steps"]),
                    "candidate_steps": int(tested["steps"]),
                    "baseline_duplicate_result": int(duplicate["result"]),
                    "baseline_duplicate_steps": int(duplicate["steps"]),
                }
            )

    reconstructed_rows.sort(
        key=lambda row: (row["panel"], row["opponent"], row["seat"], row["seed"])
    )

    physical_csv_disagreements: list[dict[str, Any]] = []
    physical_csv_duplicate_keys: list[tuple[str, str, int, int]] = []
    physical_csv_missing_keys: list[tuple[str, str, int, int]] = []
    physical_csv_extra_keys: list[tuple[str, str, int, int]] = []
    physical_schema: dict[str, Any] = {}
    report_disagreements: list[dict[str, Any]] = []
    cell_summary_disagreements: list[dict[str, Any]] = []
    runner_reports: dict[str, Any] = {}

    reconstructed_by_panel: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in reconstructed_rows:
        reconstructed_by_panel[row["panel"]].append(row)

    for panel, expected_panel_rows in reconstructed_by_panel.items():
        panel_root = RAW_ROOT / panel_specs[panel]["output"]
        header, csv_rows = read_csv(panel_root / "paired_results.csv")
        required = list(base_spec["required_output_schema"])
        physical_schema[panel] = {
            "header": header,
            "runner_header_matches": header == PAIRED_FIELDS,
            "missing_required_fields": sorted(set(required) - set(header)),
            "extra_vs_required_fields": sorted(set(header) - set(required)),
            "panel_supplied_structurally": "panel" not in header,
        }
        actual_map: dict[tuple[str, str, int, int], dict[str, str]] = {}
        key_counts: Counter[tuple[str, str, int, int]] = Counter()
        for raw in csv_rows:
            key = (panel, raw["opponent"], int(raw["seat"]), int(raw["seed"]))
            key_counts[key] += 1
            actual_map[key] = raw
        physical_csv_duplicate_keys.extend(
            key for key, count in key_counts.items() if count != 1
        )
        expected_map = {
            (panel, row["opponent"], int(row["seat"]), int(row["seed"])): row
            for row in expected_panel_rows
        }
        physical_csv_missing_keys.extend(sorted(set(expected_map) - set(actual_map)))
        physical_csv_extra_keys.extend(sorted(set(actual_map) - set(expected_map)))
        for key in sorted(set(expected_map) & set(actual_map)):
            expected = expected_map[key]
            actual = actual_map[key]
            for field in PAIRED_FIELDS:
                if str(expected[field]) != actual[field]:
                    physical_csv_disagreements.append(
                        {"key": key, "field": field, "expected": str(expected[field]), "actual": actual[field]}
                    )

        cell_header, cell_rows = read_csv(panel_root / "cell_summary.csv")
        if cell_header != [
            "seed_base",
            "opponent",
            "seat",
            "games",
            "baseline_wins",
            "candidate_wins",
            "delta_wins",
        ]:
            cell_summary_disagreements.append(
                {"panel": panel, "kind": "header", "actual": cell_header}
            )
        recomputed_cells: dict[tuple[int, str, int], dict[str, int]] = {}
        grouped: dict[tuple[int, str, int], list[dict[str, Any]]] = defaultdict(list)
        for row in expected_panel_rows:
            grouped[(int(row["seed_base"]), row["opponent"], int(row["seat"]))].append(row)
        for key, group in grouped.items():
            baseline_wins = sum(row["baseline_win"] for row in group)
            candidate_wins = sum(row["candidate_win"] for row in group)
            recomputed_cells[key] = {
                "games": len(group),
                "baseline_wins": baseline_wins,
                "candidate_wins": candidate_wins,
                "delta_wins": candidate_wins - baseline_wins,
            }
        actual_cells = {
            (int(row["seed_base"]), row["opponent"], int(row["seat"])): {
                "games": int(row["games"]),
                "baseline_wins": int(row["baseline_wins"]),
                "candidate_wins": int(row["candidate_wins"]),
                "delta_wins": int(row["delta_wins"]),
            }
            for row in cell_rows
        }
        if recomputed_cells != actual_cells:
            cell_summary_disagreements.append(
                {"panel": panel, "kind": "content", "expected": recomputed_cells, "actual": actual_cells}
            )

        report = read_json(panel_root / "report.json")
        runner_reports[panel] = report
        expected_report = {
            "panels": [
                {
                    "seed_base": seed_base,
                    "opponent": opponent,
                    "seat": seat,
                    **values,
                }
                for (seed_base, opponent, seat), values in sorted(recomputed_cells.items())
            ]
        }
        by_opponent: dict[str, dict[str, int]] = defaultdict(
            lambda: {"baseline_wins": 0, "candidate_wins": 0, "games": 0}
        )
        by_seat: dict[int, dict[str, int]] = defaultdict(
            lambda: {"baseline_wins": 0, "candidate_wins": 0, "games": 0}
        )
        for (_, opponent, seat), values in recomputed_cells.items():
            for field in ("baseline_wins", "candidate_wins", "games"):
                by_opponent[opponent][field] += values[field]
                by_seat[seat][field] += values[field]
        expected_report["by_opponent"] = [
            {"opponent": key, **values, "delta_wins": values["candidate_wins"] - values["baseline_wins"]}
            for key, values in sorted(by_opponent.items())
        ]
        expected_report["by_seat"] = [
            {"seat": key, **values, "delta_wins": values["candidate_wins"] - values["baseline_wins"]}
            for key, values in sorted(by_seat.items())
        ]
        totals = {
            field: sum(values[field] for values in recomputed_cells.values())
            for field in ("baseline_wins", "candidate_wins", "games")
        }
        totals["delta_wins"] = totals["candidate_wins"] - totals["baseline_wins"]
        expected_report["aggregates"] = totals
        checks = {
            "valid": report.get("valid") is True,
            "invalid_reasons": report.get("invalid_reasons") == [],
            "duplicate_mismatch_count": report.get("duplicate_mismatch_count") == 0,
            "panels": report.get("panels") == expected_report["panels"],
            "by_opponent": report.get("by_opponent") == expected_report["by_opponent"],
            "by_seat": report.get("by_seat") == expected_report["by_seat"],
            "aggregates": report.get("aggregates") == expected_report["aggregates"],
        }
        report_disagreements.extend(
            {"panel": panel, "field": field, "actual": report.get(field)}
            for field, passed in checks.items()
            if not passed
        )

    total_key_counts = Counter(
        (row["panel"], row["opponent"], int(row["seat"]), int(row["seed"]))
        for row in reconstructed_rows
    )
    reconstructed_duplicate_keys = sorted(
        key for key, count in total_key_counts.items() if count != 1
    )
    reconstructed_key_set = set(total_key_counts)

    group_rows: list[dict[str, Any]] = []
    group_rows.append(group_summary("aggregate", reconstructed_rows))
    for panel in sorted(reconstructed_by_panel):
        group_rows.append(group_summary(f"panel:{panel}", reconstructed_by_panel[panel]))
    by_opponent_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_seat_rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
    by_cell_rows: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in reconstructed_rows:
        by_opponent_rows[row["opponent"]].append(row)
        by_seat_rows[int(row["seat"])].append(row)
        by_cell_rows[(row["panel"], row["opponent"], int(row["seat"]))].append(row)
    for opponent in sorted(by_opponent_rows):
        group_rows.append(group_summary(f"opponent:{opponent}", by_opponent_rows[opponent]))
    for seat in sorted(by_seat_rows):
        group_rows.append(group_summary(f"seat:{seat}", by_seat_rows[seat]))
    for panel, opponent, seat in sorted(by_cell_rows):
        group_rows.append(
            group_summary(f"cell:{panel}/{opponent}/seat{seat}", by_cell_rows[(panel, opponent, seat)])
        )

    aggregate = group_rows[0]
    one_sided_discordance_upper = zero_event_upper(
        aggregate["games"], alpha=0.05, two_sided=False
    )
    cell_groups = [row for row in group_rows if row["label"].startswith("cell:")]
    opponent_groups = [row for row in group_rows if row["label"].startswith("opponent:")]
    seat_groups = [row for row in group_rows if row["label"].startswith("seat:")]
    absolute_floor = min(cell_groups, key=lambda row: row["candidate_rate"])

    mechanical_fault_counts = {
        "manifest_exit_faults": len(manifest_exit_faults),
        "command_faults": len(command_faults),
        "missing_run_keys": len(run_key_missing),
        "extra_run_keys": len(run_key_extra),
        "duplicate_manifest_keys": len(duplicate_manifest_keys),
        "summary_row_count_faults": len(summary_row_count_faults),
        "summary_seed_faults": len(summary_seed_faults),
        "start_faults": len(start_faults),
        "action_error_rows": len(action_faults),
        "action_errors_total": sum(item["action_errors"] for item in action_faults),
        "max_step_hits": len(max_step_faults),
        "invalid_results": len(invalid_result_faults),
        "exception_faults": len(exception_faults),
        "duplicate_field_mismatches": len(duplicate_field_mismatches),
        "duplicate_full_summary_mismatches": len(duplicate_full_summary_mismatches),
        "duplicate_trace_missing": len(duplicate_trace_missing),
        "duplicate_trace_hash_mismatches": len(duplicate_trace_mismatches),
        "physical_csv_disagreements": len(physical_csv_disagreements),
        "physical_csv_duplicate_keys": len(physical_csv_duplicate_keys),
        "physical_csv_missing_keys": len(physical_csv_missing_keys),
        "physical_csv_extra_keys": len(physical_csv_extra_keys),
        "cell_summary_disagreements": len(cell_summary_disagreements),
        "report_disagreements": len(report_disagreements),
        "reconstructed_duplicate_keys": len(reconstructed_duplicate_keys),
        "reconstructed_schedule_missing": len(expected_keys - reconstructed_key_set),
        "reconstructed_schedule_extra": len(reconstructed_key_set - expected_keys),
    }
    zero_mechanical_faults = all(value == 0 for value in mechanical_fault_counts.values())

    minimum_opponent_delta = min(row["delta_wins"] for row in opponent_groups)
    minimum_seat_delta = min(row["delta_wins"] for row in seat_groups)
    minimum_cell_delta = min(row["delta_wins"] for row in cell_groups)
    gate = {
        "gains_at_least_regressions": aggregate["gains"] >= aggregate["regressions"],
        "no_seat_or_opponent_delta_le_minus_3": minimum_opponent_delta > -3
        and minimum_seat_delta > -3,
        "no_cell_delta_le_minus_3": minimum_cell_delta > -3,
        "zero_mechanical_faults": zero_mechanical_faults,
    }
    gate["pass"] = all(gate.values())

    summary = {
        "scope": {
            "candidate_path": overlay["candidate"]["path"],
            "candidate_sha256": input_hashes["candidate_main"]["sha256"],
            "baseline_path": overlay["baseline"]["path"],
            "baseline_sha256": input_hashes["baseline_main"]["sha256"],
            "raw_root": rel(RAW_ROOT),
            "expected_rows": int(base_spec["expected_total_rows"]),
            "recomputed_rows": len(reconstructed_rows),
            "manifest_runs": sum(manifest_counts.values()),
            "summary_rows": sum(len(run["rows"]) for run in runs.values()),
        },
        "input_hashes": input_hashes,
        "hash_mismatches": hash_mismatches,
        "schedule": {
            "expected_unique_keys": len(expected_keys),
            "recomputed_unique_keys": len(reconstructed_key_set),
            "reconstructed_duplicates": reconstructed_duplicate_keys,
            "reconstructed_missing": sorted(expected_keys - reconstructed_key_set),
            "reconstructed_extra": sorted(reconstructed_key_set - expected_keys),
            "role_checks": schedule_checks,
            "physical_schema": physical_schema,
        },
        "aggregate": aggregate,
        "groups": group_rows,
        "absolute_floor": absolute_floor,
        "paired_uncertainty": {
            "method": (
                "Exact Clopper-Pearson bound on the probability of any paired "
                "outcome discordance. With zero discordances, a conservative "
                "signed win-rate-difference interval is plus/minus that upper bound."
            ),
            "discordant_pairs": aggregate["discordant"],
            "two_sided_95_discordance_upper": aggregate[
                "zero_discordance_two_sided_95_upper"
            ],
            "one_sided_95_discordance_upper": one_sided_discordance_upper,
            "conservative_signed_delta_95": [
                aggregate["conservative_signed_delta_95_low"],
                aggregate["conservative_signed_delta_95_high"],
            ],
            "mcnemar": (
                "No informative discordant pairs; the discordant odds ratio is "
                "undefined and the conventional exact p-value is 1.0."
            ),
        },
        "candidate_baseline_equality": {
            "outcome_result_mismatches": len(candidate_result_mismatches),
            "step_count_mismatches": len(candidate_step_mismatches),
            "paired_gains": aggregate["gains"],
            "paired_regressions": aggregate["regressions"],
            "paired_ties": aggregate["ties"],
        },
        "duplicate_control": {
            "scheduled_pairs": len(reconstructed_rows),
            "runner_field_exact_matches": len(reconstructed_rows)
            - len(duplicate_field_mismatches),
            "full_summary_exact_matches_excluding_trace_path": len(reconstructed_rows)
            - len(duplicate_full_summary_mismatches),
            "trace_sha256_exact_matches": len(reconstructed_rows)
            - len(duplicate_trace_mismatches)
            - len(duplicate_trace_missing),
            "runner_report_mismatch_count": sum(
                int(report.get("duplicate_mismatch_count", -1))
                for report in runner_reports.values()
            ),
        },
        "mechanical_fault_counts": mechanical_fault_counts,
        "gate": gate,
        "disagreements": {
            "physical_csv": physical_csv_disagreements,
            "cell_summary": cell_summary_disagreements,
            "runner_report": report_disagreements,
            "schema_contract": {
                panel: values["missing_required_fields"]
                for panel, values in physical_schema.items()
                if values["missing_required_fields"]
            },
        },
        "interpretation_limits": [
            "Equality proves identical outcomes on the exact frozen 160 schedule only.",
            "Zero gains and zero regressions do not establish that the candidate is stronger.",
            "Equal result and step counts do not establish action-level or mechanism equality.",
            "The uncertainty bound treats scheduled pairs as exchangeable Bernoulli observations; generalization beyond the fixed opponent/seat/seed set is conditional.",
        ],
    }

    row_fields = [
        "panel",
        "opponent",
        "seat",
        "seed_base",
        "game",
        "seed",
        "baseline_result",
        "candidate_result",
        "baseline_win",
        "candidate_win",
        "baseline_steps",
        "candidate_steps",
        "baseline_duplicate_result",
        "baseline_duplicate_steps",
    ]
    write_csv(OUT_DIR / "recomputed_rows.csv", row_fields, reconstructed_rows)
    group_fields = list(group_rows[0])
    write_csv(OUT_DIR / "group_summary.csv", group_fields, group_rows)
    write_csv(
        OUT_DIR / "input_hashes.csv",
        ["label", "path", "sha256", "expected_sha256", "matches"],
        [
            {"label": label, **values}
            for label, values in sorted(input_hashes.items())
        ],
    )
    summary_path = OUT_DIR / "audit_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    output_files = [
        Path(__file__),
        OUT_DIR / "recomputed_rows.csv",
        OUT_DIR / "group_summary.csv",
        OUT_DIR / "input_hashes.csv",
        summary_path,
    ]
    report_path = OUT_DIR / "AUDIT.md"
    if report_path.exists():
        output_files.append(report_path)
    output_manifest = {
        path.name: {
            "path": rel(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in output_files
    }
    (OUT_DIR / "output_manifest.json").write_text(
        json.dumps(output_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "rows": len(reconstructed_rows),
                "baseline_wins": aggregate["baseline_wins"],
                "candidate_wins": aggregate["candidate_wins"],
                "gains": aggregate["gains"],
                "regressions": aggregate["regressions"],
                "mechanical_faults": sum(mechanical_fault_counts.values()),
                "gate_pass": gate["pass"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
