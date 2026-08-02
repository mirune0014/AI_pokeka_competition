"""Independent read-only audit of the immutable Rule 1 fixed160 outputs.

Run on Windows from the repository root with:

    .venv-rl\Scripts\python.exe autonomous_gold_20260715\numerical_audits\archaludon_historical_silver_single_resolver_salvage_v1_rule1_fixed160\audit_rule1_fixed160.py

The calculator reads the frozen specification, policies, checked runners, and
completed raw outputs.  It prints canonical JSON and does not write, repair,
or expand any evaluated artifact.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


AUDIT_DIR = Path(__file__).resolve().parent
REPO_ROOT = AUDIT_DIR.parents[2]
SPEC = (
    REPO_ROOT
    / "autonomous_gold_20260715/evaluation_specs/archaludon_historical_silver_single_resolver_salvage_v1_rule1/fixed160_spec.json"
)
RAW_ROOT = (
    REPO_ROOT
    / "autonomous_gold_20260715/evaluations/archaludon_historical_silver_single_resolver_salvage_v1/rule1_fixed160_raw"
)

EXPECTED_SPEC_SHA256 = "E2B8986663A43A7F6F52888E487F39B8D059CDCDDF441A3E87D8C093DF15274C"
EXPECTED_RAW_TREE_SHA256 = "DB612879410B9FE53AF97B33A33212CD80C3FD24FEAD8184DA224F805616C6DD"
EXPECTED_BASELINE_MAIN_SHA256 = "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
EXPECTED_CANDIDATE_MAIN_SHA256 = "153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A"
EXPECTED_DECK_SHA256 = "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A"

GAME_FIELDS = ("seed", "result", "steps", "turn", "action_errors", "hit_max_steps")
CINDERACE = 666
DURALUDON = 169
SETUP_BENCH_CONTEXT = 2


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def tree_sha256(path: Path) -> dict[str, Any]:
    """Hash sorted relative/path, byte size, and file SHA-256 ledger lines."""
    entries: list[str] = []
    for child in sorted(
        (item for item in path.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(path).as_posix(),
    ):
        relative = child.relative_to(path).as_posix()
        entries.append(f"{relative}\t{child.stat().st_size}\t{sha256(child)}\n")
    return {
        "sha256": hashlib.sha256("".join(entries).encode("utf-8")).hexdigest().upper(),
        "files": len(entries),
        "ledger_definition": "SHA256(UTF-8 sorted relative/path\\tbytes\\tfile_sha256\\n)",
    }


def runner_tree_sha256(path: Path) -> dict[str, Any]:
    """Reproduce the parent-supplied PowerShell full-path run ledger."""
    files = sorted(
        (item.resolve() for item in path.rglob("*") if item.is_file()),
        key=lambda item: str(item).casefold(),
    )
    preimage = "\n".join(
        f"{sha256(item)}  {item}" for item in files
    ).encode("utf-8")
    return {
        "sha256": hashlib.sha256(preimage).hexdigest().upper(),
        "files": len(files),
        "preimage_bytes": len(preimage),
        "ledger_definition": "SHA256(UTF-8 LF-join, no terminal LF, of uppercase_file_sha256 + two spaces + absolute Windows FullName; PowerShell FullName ascending)",
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON: {rel(path)}:{line_number}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"non-object JSON row: {rel(path)}:{line_number}")
        rows.append(value)
    return rows


def path_equal(left: str | Path, right: str | Path) -> bool:
    return str(Path(left).resolve()).casefold() == str(Path(right).resolve()).casefold()


def command_option(command: list[str], name: str) -> str:
    positions = [index for index, value in enumerate(command) if value == name]
    if len(positions) != 1 or positions[0] + 1 >= len(command):
        raise ValueError(f"command option {name!r} missing or repeated")
    return command[positions[0] + 1]


def without_trace(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "trace"}


def game_tuple(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row.get(field) for field in GAME_FIELDS)


def exception_value_count(value: Any) -> int:
    """Count populated fields whose key explicitly names an exception."""
    if isinstance(value, dict):
        count = 0
        for key, child in value.items():
            if "exception" in str(key).casefold() and child not in (None, "", False, 0, [], {}):
                count += 1
            count += exception_value_count(child)
        return count
    if isinstance(value, list):
        return sum(exception_value_count(child) for child in value)
    return 0


def exact_mcnemar_two_sided(gains: int, regressions: int) -> float:
    discordant = gains + regressions
    if discordant == 0:
        return 1.0
    lower = min(gains, regressions)
    probability = sum(math.comb(discordant, index) for index in range(lower + 1)) / (2**discordant)
    return min(1.0, 2.0 * probability)


def paired_stats(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    selected = list(rows)
    n = len(selected)
    baseline_wins = sum(row["baseline_win"] for row in selected)
    candidate_wins = sum(row["candidate_win"] for row in selected)
    gains = sum(row["baseline_win"] == 0 and row["candidate_win"] == 1 for row in selected)
    regressions = sum(row["baseline_win"] == 1 and row["candidate_win"] == 0 for row in selected)
    both_win = sum(row["baseline_win"] == 1 and row["candidate_win"] == 1 for row in selected)
    both_loss = sum(row["baseline_win"] == 0 and row["candidate_win"] == 0 for row in selected)
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
        "mcnemar_exact_two_sided_p": exact_mcnemar_two_sided(gains, regressions),
    }


def grouped_stats(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in fields)].append(row)
    output: list[dict[str, Any]] = []
    for key in sorted(groups):
        output.append({field: value for field, value in zip(fields, key)} | paired_stats(groups[key]))
    return output


def trace_snapshot_value(row: dict[str, Any], seat: int, field: str) -> Any:
    snapshot = row.get("snapshot") or {}
    return snapshot.get(f"p{seat}_{field}")


def first_trace_difference(
    baseline_path: Path,
    candidate_path: Path,
    *,
    seat: int,
) -> dict[str, Any] | None:
    """Classify a same-seed first trace difference as the exact Rule 1 mechanism."""
    if sha256(baseline_path) == sha256(candidate_path):
        return None
    baseline = read_jsonl(baseline_path)
    candidate = read_jsonl(candidate_path)
    first = next(
        (
            index
            for index in range(min(len(baseline), len(candidate)))
            if baseline[index] != candidate[index]
        ),
        min(len(baseline), len(candidate)),
    )
    faults: list[str] = []
    if first >= len(baseline) or first >= len(candidate):
        return {
            "valid_rule1_start": False,
            "first_difference_index": first,
            "faults": ["trace ended before a comparable first-difference row"],
        }

    left = baseline[first]
    right = candidate[first]
    left_observation = {key: value for key, value in left.items() if key != "action"}
    right_observation = {key: value for key, value in right.items() if key != "action"}
    if left_observation != right_observation:
        faults.append("first-difference observations are not identical")
    if left.get("context") != SETUP_BENCH_CONTEXT:
        faults.append("first difference is not SETUP_BENCH_POKEMON")
    if left.get("player") != seat or right.get("player") != seat:
        faults.append("first difference is not the candidate policy player")
    if left.get("action") != []:
        faults.append("parent setup-Bench action is not empty")
    action = right.get("action")
    if not (
        isinstance(action, list)
        and len(action) == 1
        and isinstance(action[0], int)
        and not isinstance(action[0], bool)
        and 0 <= action[0] < int(right.get("option_count", -1))
    ):
        faults.append("candidate action is not one legal option index")
    if right.get("min_count") != 0 or not isinstance(right.get("max_count"), int) or right["max_count"] < 1:
        faults.append("setup-Bench count bounds are not 0..positive")
    own_hand = right.get("own_hand_ids")
    if not isinstance(own_hand, list) or DURALUDON not in own_hand:
        faults.append("candidate hand does not visibly contain Duraludon")
    snapshot = right.get("snapshot") or {}
    if snapshot.get("turn") != 0 or snapshot.get("result") != -1 or snapshot.get("your_index") != seat:
        faults.append("first difference is not an open turn-zero candidate callback")
    cinderace_commit = any(
        isinstance(log, dict)
        and log.get("playerIndex") == seat
        and log.get("cardId") == CINDERACE
        and log.get("toArea") == 4
        for log in (right.get("logs") or [])
    )
    if not cinderace_commit:
        faults.append("same-callback logs do not show candidate Cinderace committed Active")

    post_index = None
    for index in range(first + 1, len(candidate)):
        active = trace_snapshot_value(candidate[index], seat, "active")
        bench = trace_snapshot_value(candidate[index], seat, "bench")
        if active == CINDERACE and isinstance(bench, list) and DURALUDON in bench:
            post_index = index
            if bench.count(DURALUDON) != 1:
                faults.append("first visible post-state has other than one benched Duraludon")
            break
    if post_index is None:
        faults.append("no later trace snapshot shows Cinderace Active plus Duraludon Bench")
    else:
        baseline_post = next(
            (
                row
                for row in baseline[first + 1 :]
                if trace_snapshot_value(row, seat, "active") == CINDERACE
            ),
            None,
        )
        if baseline_post is None:
            faults.append("baseline has no comparable visible Cinderace Active post-state")
        else:
            baseline_bench = trace_snapshot_value(baseline_post, seat, "bench")
            if isinstance(baseline_bench, list) and DURALUDON in baseline_bench:
                faults.append("baseline empty action nevertheless shows Duraludon Bench")

    return {
        "valid_rule1_start": not faults,
        "first_difference_index": first,
        "step": right.get("step"),
        "candidate_action": action,
        "visible_hand_duraludon_count": own_hand.count(DURALUDON) if isinstance(own_hand, list) else None,
        "post_state_index": post_index,
        "faults": faults,
    }


def verify_file(
    output: dict[str, Any],
    violations: list[str],
    label: str,
    path: Path,
    expected: str,
) -> None:
    actual = sha256(path)
    match = actual == expected.upper()
    output[label] = {
        "path": rel(path),
        "bytes": path.stat().st_size,
        "sha256": actual,
        "expected": expected.upper(),
        "match": match,
    }
    if not match:
        violations.append(f"hash mismatch: {label}")


def main() -> None:
    violations: list[str] = []
    runner_discrepancies: list[str] = []
    spec = json.loads(SPEC.read_text(encoding="utf-8"))

    artifact_hashes: dict[str, Any] = {}
    verify_file(artifact_hashes, violations, "spec", SPEC, EXPECTED_SPEC_SHA256)
    baseline_dir = REPO_ROOT / spec["baseline"]["path"]
    candidate_dir = REPO_ROOT / spec["candidate"]["path"]
    verify_file(
        artifact_hashes,
        violations,
        "baseline_main",
        baseline_dir / "main.py",
        spec["baseline"]["main_sha256"],
    )
    verify_file(
        artifact_hashes,
        violations,
        "candidate_main",
        candidate_dir / "main.py",
        spec["candidate"]["main_sha256"],
    )
    verify_file(
        artifact_hashes,
        violations,
        "candidate_exact_parent",
        candidate_dir / "_historical_silver_parent.py",
        spec["baseline"]["main_sha256"],
    )
    verify_file(
        artifact_hashes,
        violations,
        "baseline_deck",
        baseline_dir / "deck.csv",
        spec["baseline"]["deck_sha256"],
    )
    verify_file(
        artifact_hashes,
        violations,
        "candidate_deck",
        candidate_dir / "deck.csv",
        spec["candidate"]["deck_sha256"],
    )
    verify_file(
        artifact_hashes,
        violations,
        "strategy",
        REPO_ROOT / spec["strategy"]["path"],
        spec["strategy"]["sha256"],
    )
    verify_file(
        artifact_hashes,
        violations,
        "root_rule1_verification",
        REPO_ROOT / spec["verification"]["path"],
        spec["verification"]["sha256"],
    )
    for name, expected in spec["engine"]["files"].items():
        verify_file(
            artifact_hashes,
            violations,
            f"engine:{name}",
            REPO_ROOT / spec["engine"]["path"] / name,
            expected,
        )
    for name, runner in spec["runners"].items():
        verify_file(
            artifact_hashes,
            violations,
            f"runner:{name}",
            REPO_ROOT / runner["path"],
            runner["sha256"],
        )
    opponent_specs = {row["label"]: row for row in spec["opponents"]}
    for opponent, row in opponent_specs.items():
        directory = REPO_ROOT / row["path"]
        verify_file(artifact_hashes, violations, f"opponent_main:{opponent}", directory / "main.py", row["main_sha256"])
        verify_file(artifact_hashes, violations, f"opponent_deck:{opponent}", directory / "deck.csv", row["deck_sha256"])

    if artifact_hashes["baseline_main"]["sha256"] != EXPECTED_BASELINE_MAIN_SHA256:
        violations.append("baseline is not the parent-supplied exact Silver hash")
    if artifact_hashes["candidate_main"]["sha256"] != EXPECTED_CANDIDATE_MAIN_SHA256:
        violations.append("candidate is not the parent-supplied Rule 1 hash")
    if artifact_hashes["baseline_deck"]["sha256"] != EXPECTED_DECK_SHA256:
        violations.append("baseline deck is not the frozen common deck")

    portable_raw_tree = tree_sha256(RAW_ROOT)
    runner_raw_tree = runner_tree_sha256(RAW_ROOT)
    runner_raw_tree["expected"] = EXPECTED_RAW_TREE_SHA256
    runner_raw_tree["match"] = runner_raw_tree["sha256"] == EXPECTED_RAW_TREE_SHA256
    raw_tree = {
        "path": rel(RAW_ROOT),
        "files": runner_raw_tree["files"],
        "runner_full_path_ledger": runner_raw_tree,
        "portable_relative_path_ledger": portable_raw_tree,
        "match": runner_raw_tree["match"],
    }
    if not raw_tree["match"]:
        violations.append("raw-tree digest mismatch")

    expected_python = REPO_ROOT / spec["python"]
    battle_runner = REPO_ROOT / spec["runners"]["checked_battle"]["path"]
    engine_dir = REPO_ROOT / spec["engine"]["path"]
    panel_specs = {row["label"]: row for row in spec["panels"]}
    expected_keys: set[tuple[str, str, int, int]] = set()
    for panel, panel_spec in panel_specs.items():
        for opponent in panel_spec["opponents"]:
            for seat in (0, 1):
                for game in range(panel_spec["games_per_seat"]):
                    expected_keys.add((panel, opponent["label"], seat, panel_spec["seed_base"] + game))

    records: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    baseline_schedule: set[tuple[str, str, int, int]] = set()
    candidate_schedule: set[tuple[str, str, int, int]] = set()
    summaries: dict[tuple[str, str, int, str], list[dict[str, Any]]] = {}
    trace_paths: dict[tuple[str, str, int, str, int], Path] = {}
    manifest_rows = 0
    exit_failures = 0
    start_faults = 0
    action_errors = 0
    max_step_hits = 0
    invalid_results = 0
    exception_fields = 0
    malformed_trace_rows = 0
    trace_step_faults = 0
    duplicate_tuple_mismatches = 0
    duplicate_summary_mismatches = 0
    duplicate_result_mismatches = 0
    duplicate_decision_count_mismatches = 0
    duplicate_trace_mismatches = 0
    panel_hashes: dict[str, Any] = {}

    for panel, panel_spec in panel_specs.items():
        panel_root = RAW_ROOT / panel_spec["output"]
        manifest_path = panel_root / "manifest.jsonl"
        manifest = read_jsonl(manifest_path)
        manifest_rows += len(manifest)
        expected_opponents = {row["label"]: REPO_ROOT / row["path"] for row in panel_spec["opponents"]}
        expected_run_keys = {
            (opponent, seat, role)
            for opponent in expected_opponents
            for seat in (0, 1)
            for role in ("baseline_a", "baseline_b", "candidate")
        }
        seen_run_keys: set[tuple[str, int, str]] = set()
        if len(manifest) != len(expected_run_keys):
            violations.append(f"{panel}: manifest row count {len(manifest)} != {len(expected_run_keys)}")

        for manifest_row in manifest:
            role = str(manifest_row.get("role"))
            opponent = str(manifest_row.get("opponent"))
            seat = int(manifest_row.get("seat", -1))
            run_key = (opponent, seat, role)
            if run_key in seen_run_keys:
                violations.append(f"{panel}: duplicate manifest key {run_key}")
            seen_run_keys.add(run_key)
            if run_key not in expected_run_keys:
                violations.append(f"{panel}: unexpected manifest key {run_key}")
                continue
            exit_code = int(manifest_row.get("exit_code", -1))
            exit_failures += int(exit_code != 0)
            command = manifest_row.get("command")
            if not isinstance(command, list) or not all(isinstance(value, str) for value in command):
                violations.append(f"{panel}: malformed command for {run_key}")
                continue
            try:
                if not path_equal(command[0], expected_python):
                    violations.append(f"{panel}: wrong Python for {run_key}")
                if not path_equal(command[1], battle_runner):
                    violations.append(f"{panel}: wrong battle runner for {run_key}")
                if command.count("--engine-seed") != 1:
                    violations.append(f"{panel}: --engine-seed absent/repeated for {run_key}")
                if int(command_option(command, "--games")) != panel_spec["games_per_seat"]:
                    violations.append(f"{panel}: wrong games for {run_key}")
                if int(command_option(command, "--seed-base")) != panel_spec["seed_base"]:
                    violations.append(f"{panel}: wrong seed base for {run_key}")
                if int(command_option(command, "--max-steps")) != spec["max_steps"]:
                    violations.append(f"{panel}: wrong max steps for {run_key}")
                if not path_equal(command_option(command, "--engine-dir"), engine_dir):
                    violations.append(f"{panel}: wrong engine for {run_key}")
            except (ValueError, IndexError) as exc:
                violations.append(f"{panel}: malformed command options for {run_key}: {exc}")
                continue

            policy_dir = baseline_dir if role in {"baseline_a", "baseline_b"} else candidate_dir
            opponent_dir = expected_opponents[opponent]
            expected_a, expected_b = (policy_dir, opponent_dir) if seat == 0 else (opponent_dir, policy_dir)
            if not path_equal(command_option(command, "--agent-a"), expected_a):
                violations.append(f"{panel}: wrong agent A for {run_key}")
            if not path_equal(command_option(command, "--agent-b"), expected_b):
                violations.append(f"{panel}: wrong agent B for {run_key}")
            if not path_equal(command_option(command, "--deck-a"), expected_a / "deck.csv"):
                violations.append(f"{panel}: wrong deck A for {run_key}")
            if not path_equal(command_option(command, "--deck-b"), expected_b / "deck.csv"):
                violations.append(f"{panel}: wrong deck B for {run_key}")

            summary_path = Path(command_option(command, "--summary")).resolve()
            trace_dir = Path(command_option(command, "--trace-dir")).resolve()
            for labelled_path, label in ((summary_path, "summary"), (trace_dir, "trace directory")):
                try:
                    labelled_path.relative_to(panel_root.resolve())
                except ValueError:
                    violations.append(f"{panel}: {label} outside raw panel for {run_key}")
            rows = read_jsonl(summary_path)
            summaries[(panel, opponent, seat, role)] = rows
            if len(rows) != panel_spec["games_per_seat"]:
                violations.append(f"{panel}: summary rows {len(rows)} for {run_key}")
            expected_trace_names = {f"game_{game:04d}.jsonl" for game in range(panel_spec["games_per_seat"])}
            actual_trace_names = {path.name for path in trace_dir.glob("game_*.jsonl") if path.is_file()}
            if actual_trace_names != expected_trace_names:
                violations.append(f"{panel}: trace-file set mismatch for {run_key}")

            for index, row in enumerate(rows):
                if row.get("game") != index or row.get("seed") != panel_spec["seed_base"] + index:
                    violations.append(f"{panel}: game/seed sequence fault for {run_key} row {index}")
                start_faults += int(row.get("started") is not True)
                action_errors += int(row.get("action_errors", 0) or 0)
                max_step_hits += int(bool(row.get("hit_max_steps", False)))
                invalid_results += int(row.get("result") not in (0, 1))
                exception_fields += exception_value_count(row)
                trace_path = Path(str(row.get("trace", ""))).resolve()
                expected_trace = trace_dir / f"game_{index:04d}.jsonl"
                if not path_equal(trace_path, expected_trace) or not expected_trace.is_file():
                    violations.append(f"{panel}: summary trace binding fault for {run_key} game {index}")
                    continue
                trace_paths[(panel, opponent, seat, role, index)] = expected_trace
                try:
                    trace_rows = read_jsonl(expected_trace)
                except ValueError:
                    malformed_trace_rows += 1
                    continue
                if len(trace_rows) != row.get("steps"):
                    trace_step_faults += 1
                for trace_index, trace_row in enumerate(trace_rows):
                    if trace_row.get("game") != index or trace_row.get("step") != trace_index:
                        trace_step_faults += 1
                    exception_fields += exception_value_count(trace_row)

        if seen_run_keys != expected_run_keys:
            violations.append(f"{panel}: manifest run-key set mismatch")

        for opponent in expected_opponents:
            for seat in (0, 1):
                baseline_a = summaries[(panel, opponent, seat, "baseline_a")]
                baseline_b = summaries[(panel, opponent, seat, "baseline_b")]
                candidate = summaries[(panel, opponent, seat, "candidate")]
                for game in range(panel_spec["games_per_seat"]):
                    first = baseline_a[game]
                    duplicate = baseline_b[game]
                    tested = candidate[game]
                    duplicate_tuple_mismatches += int(game_tuple(first) != game_tuple(duplicate))
                    duplicate_summary_mismatches += int(without_trace(first) != without_trace(duplicate))
                    duplicate_result_mismatches += int(first.get("result") != duplicate.get("result"))
                    duplicate_decision_count_mismatches += int(first.get("steps") != duplicate.get("steps"))
                    first_trace = trace_paths[(panel, opponent, seat, "baseline_a", game)]
                    duplicate_trace = trace_paths[(panel, opponent, seat, "baseline_b", game)]
                    duplicate_trace_mismatches += int(sha256(first_trace) != sha256(duplicate_trace))

                    baseline_key = (panel, opponent, seat, int(first["seed"]))
                    candidate_key = (panel, opponent, seat, int(tested["seed"]))
                    baseline_schedule.add(baseline_key)
                    candidate_schedule.add(candidate_key)
                    if baseline_key != candidate_key:
                        violations.append(f"baseline/candidate schedule mismatch: {baseline_key} vs {candidate_key}")
                    if baseline_key in records:
                        violations.append(f"duplicate schedule key {baseline_key}")
                    records[baseline_key] = {
                        "panel": panel,
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
                        "baseline_trace": first_trace,
                        "candidate_trace": trace_paths[(panel, opponent, seat, "candidate", game)],
                    }

        csv_rows = list(csv.DictReader((panel_root / "paired_results.csv").open(newline="", encoding="utf-8")))
        panel_expected_rows = panel_spec["expected_rows"]
        if len(csv_rows) != panel_expected_rows:
            runner_discrepancies.append(f"{panel}: paired_results rows {len(csv_rows)} != {panel_expected_rows}")
        for csv_row in csv_rows:
            key = (panel, csv_row["opponent"], int(csv_row["seat"]), int(csv_row["seed"]))
            record = records.get(key)
            if record is None:
                runner_discrepancies.append(f"{panel}: paired_results unknown key {key}")
                continue
            expected_csv = {
                "seed_base": str(panel_spec["seed_base"]),
                "opponent": record["opponent"],
                "seat": str(record["seat"]),
                "game": str(record["game"]),
                "seed": str(record["seed"]),
                "baseline_result": str(record["baseline_result"]),
                "candidate_result": str(record["candidate_result"]),
                "baseline_win": str(record["baseline_win"]),
                "candidate_win": str(record["candidate_win"]),
                "baseline_steps": str(record["baseline_steps"]),
                "candidate_steps": str(record["candidate_steps"]),
            }
            if csv_row != expected_csv:
                runner_discrepancies.append(f"{panel}: paired_results mismatch for {key}")

        panel_rows = [row for row in records.values() if row["panel"] == panel]
        expected_cells = {
            (row["opponent"], row["seat"]): row
            for row in grouped_stats(panel_rows, ("opponent", "seat"))
        }
        cell_rows = list(csv.DictReader((panel_root / "cell_summary.csv").open(newline="", encoding="utf-8")))
        if len(cell_rows) != len(expected_cells):
            runner_discrepancies.append(f"{panel}: cell_summary row count mismatch")
        for cell in cell_rows:
            key = (cell["opponent"], int(cell["seat"]))
            expected = expected_cells.get(key)
            if expected is None or cell != {
                "seed_base": str(panel_spec["seed_base"]),
                "opponent": key[0],
                "seat": str(key[1]),
                "games": str(expected["n"] if expected else ""),
                "baseline_wins": str(expected["baseline_wins"] if expected else ""),
                "candidate_wins": str(expected["candidate_wins"] if expected else ""),
                "delta_wins": str(expected["delta_wins"] if expected else ""),
            }:
                runner_discrepancies.append(f"{panel}: cell_summary mismatch for {key}")

        report = json.loads((panel_root / "report.json").read_text(encoding="utf-8"))
        panel_total = paired_stats(panel_rows)
        expected_aggregate = {
            "baseline_wins": panel_total["baseline_wins"],
            "candidate_wins": panel_total["candidate_wins"],
            "games": panel_total["n"],
            "delta_wins": panel_total["delta_wins"],
        }
        if report.get("aggregates") != expected_aggregate:
            runner_discrepancies.append(f"{panel}: report aggregate mismatch")
        if report.get("valid") is not True or report.get("invalid_reasons") != [] or report.get("duplicate_mismatch_count") != 0:
            runner_discrepancies.append(f"{panel}: report health fields mismatch")

        panel_tree = tree_sha256(panel_root)
        panel_hashes[panel] = {
            "path": rel(panel_root),
            "tree_sha256": panel_tree["sha256"],
            "files": panel_tree["files"],
            "manifest_sha256": sha256(manifest_path),
            "paired_results_sha256": sha256(panel_root / "paired_results.csv"),
            "report_sha256": sha256(panel_root / "report.json"),
        }

    if baseline_schedule != expected_keys:
        violations.append("baseline schedule does not equal the immutable expected key set")
    if candidate_schedule != expected_keys:
        violations.append("candidate schedule does not equal the immutable expected key set")
    if set(records) != expected_keys:
        violations.append("reconstructed record keys do not equal the immutable expected key set")
    if len(records) != spec["expected_total_rows"]:
        violations.append(f"record count {len(records)} != {spec['expected_total_rows']}")
    if duplicate_tuple_mismatches or duplicate_summary_mismatches or duplicate_trace_mismatches:
        violations.append("duplicate-control equality failed")
    if exit_failures or start_faults or action_errors or max_step_hits or invalid_results or exception_fields:
        violations.append("execution health gate failed")
    if malformed_trace_rows or trace_step_faults:
        violations.append("trace integrity gate failed")
    if runner_discrepancies:
        violations.append("checked runner outputs disagree with independent reconstruction")

    rows = [records[key] for key in sorted(records)]
    activation_ledger: list[dict[str, Any]] = []
    trace_diff_games = 0
    mechanism_faults = 0
    for record in rows:
        classification = first_trace_difference(
            record["baseline_trace"], record["candidate_trace"], seat=record["seat"]
        )
        if classification is None:
            continue
        trace_diff_games += 1
        mechanism_faults += int(not classification["valid_rule1_start"])
        activation_ledger.append(
            {
                "panel": record["panel"],
                "opponent": record["opponent"],
                "seat": record["seat"],
                "game": record["game"],
                "seed": record["seed"],
                "baseline_win": record["baseline_win"],
                "candidate_win": record["candidate_win"],
                "outcome_delta": record["candidate_win"] - record["baseline_win"],
                "step_delta": record["candidate_steps"] - record["baseline_steps"],
                **classification,
            }
        )
    natural_starts = sum(row["valid_rule1_start"] for row in activation_ledger)
    if mechanism_faults or natural_starts != trace_diff_games:
        violations.append("one or more candidate first differences is not exact Rule 1 shape")

    overall = paired_stats(rows)
    by_panel = grouped_stats(rows, ("panel",))
    by_opponent = grouped_stats(rows, ("opponent",))
    by_seat = grouped_stats(rows, ("seat",))
    by_cell = grouped_stats(rows, ("panel", "opponent", "seat"))
    starts_by_seat = Counter(row["seat"] for row in activation_ledger if row["valid_rule1_start"])
    starts_by_opponent = Counter(row["opponent"] for row in activation_ledger if row["valid_rule1_start"])
    starts_by_cell = Counter(
        (row["opponent"], row["seat"])
        for row in activation_ledger
        if row["valid_rule1_start"]
    )

    seed_clusters: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        seed_clusters[(row["panel"], row["seed"])].append(row)
    seed_sensitivity: list[dict[str, Any]] = []
    for panel in sorted(panel_specs):
        clusters = [values for (name, _seed), values in sorted(seed_clusters.items()) if name == panel]
        cluster_deltas = [sum(row["candidate_win"] - row["baseline_win"] for row in values) for values in clusters]
        candidate_cluster_wins = [sum(row["candidate_win"] for row in values) for values in clusters]
        seed_sensitivity.append(
            {
                "panel": panel,
                "clusters": len(clusters),
                "rows_per_cluster": sorted({len(values) for values in clusters}),
                "positive_zero_negative_net_delta_clusters": [
                    sum(value > 0 for value in cluster_deltas),
                    sum(value == 0 for value in cluster_deltas),
                    sum(value < 0 for value in cluster_deltas),
                ],
                "net_delta_range_wins": [min(cluster_deltas), max(cluster_deltas)],
                "candidate_cluster_win_range": [min(candidate_cluster_wins), max(candidate_cluster_wins)],
            }
        )

    quartiles: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        quartiles[(row["panel"], row["game"] // 5 + 1)].append(row)
    seed_quartiles = [
        {"panel": panel, "quartile": quartile, **paired_stats(values)}
        for (panel, quartile), values in sorted(quartiles.items())
    ]

    # Same immutable seeds are reused across seats/opponents, so the primary
    # empirical paired interval resamples whole seed clusters within panel.
    # Every observed row delta is exactly zero, hence every possible resample
    # is also zero and the empirical interval is deterministically [0, 0].
    all_row_deltas = [row["candidate_win"] - row["baseline_win"] for row in rows]
    if any(all_row_deltas):
        violations.append("calculator invariant violated: nonzero delta requires bootstrap implementation")
        seed_cluster_empirical_ci = None
    else:
        seed_cluster_empirical_ci = [0.0, 0.0]
    # The empirical interval cannot express unseen discordance.  With 0 of n
    # discordant pairs, a one-sided 95% Clopper-Pearson upper bound on the
    # discordance probability is 1 - .05**(1/n); |net paired delta| cannot
    # exceed discordance, yielding a conservative symmetric magnitude envelope.
    discordance_upper = 1.0 - 0.05 ** (1.0 / overall["n"])
    paired_uncertainty = {
        "primary_stratified_seed_cluster_empirical_95ci": seed_cluster_empirical_ci,
        "primary_interval_note": "degenerate because all 160 observed paired row deltas are zero; it is not proof of population identity",
        "exact_zero_discordance_95pct_magnitude_envelope": [-discordance_upper, discordance_upper],
        "exact_envelope_definition": "one-sided 95% Clopper-Pearson upper bound for 0 discordant rows, mapped through |net delta| <= discordance",
    }

    mirror_p0 = summaries[("historical_silver", "historical_silver", 0, "baseline_a")]
    mirror_p1 = summaries[("historical_silver", "historical_silver", 1, "baseline_a")]
    identical_summary_matches = sum(
        without_trace(left) == without_trace(right) for left, right in zip(mirror_p0, mirror_p1)
    )
    identical_trace_matches = sum(
        sha256(trace_paths[("historical_silver", "historical_silver", 0, "baseline_a", game)])
        == sha256(trace_paths[("historical_silver", "historical_silver", 1, "baseline_a", game)])
        for game in range(panel_specs["historical_silver"]["games_per_seat"])
    )
    identical_policy_control = {
        "policy": "exact Historical-Silver as both agent A/player 0 and agent B/player 1",
        "seeds": len(mirror_p0),
        "nontrace_summary_matches": identical_summary_matches,
        "byte_trace_matches": identical_trace_matches,
        "player0_results": sum(row["result"] == 0 for row in mirror_p0),
        "player1_results": sum(row["result"] == 1 for row in mirror_p0),
        "interpretation": "the 11/9 seat-labelled split is complementary labeling of 20 identical games",
    }
    if identical_summary_matches != len(mirror_p0) or identical_trace_matches != len(mirror_p0):
        violations.append("identical-policy mirror control mismatch")

    gates_config = spec["gates"]
    group_regressions = [row for row in by_seat + by_opponent if row["delta_wins"] <= -3]
    gates = {
        "frozen_hashes": not any("hash mismatch" in item for item in violations) and raw_tree["match"],
        "unique_schedule_keys": len(records) == gates_config["unique_schedule_keys"] and set(records) == expected_keys,
        "exact_baseline_candidate_schedule_equality": baseline_schedule == candidate_schedule == expected_keys,
        "duplicate_summary_matches": len(records) - duplicate_summary_mismatches == gates_config["duplicate_summary_matches"],
        "duplicate_byte_trace_matches": len(records) - duplicate_trace_mismatches == gates_config["duplicate_byte_trace_matches"],
        "zero_execution_faults": exit_failures == gates_config["execution_faults"],
        "zero_start_faults": start_faults == gates_config["start_faults"],
        "zero_action_errors": action_errors == gates_config["action_errors"],
        "zero_exceptions": exception_fields == gates_config["exceptions"],
        "zero_max_step_hits": max_step_hits == gates_config["max_step_hits"],
        "minimum_natural_starts": natural_starts >= gates_config["minimum_natural_starts"],
        "minimum_starts_each_seat": all(starts_by_seat[seat] >= gates_config["minimum_starts_per_seat"] for seat in (0, 1)),
        "paired_gains_at_least_regressions": overall["gains"] >= overall["regressions"],
        "no_seat_or_opponent_three_wins_below_parent": not group_regressions,
        "zero_mechanism_faults": mechanism_faults == 0,
        "zero_runner_discrepancies": not runner_discrepancies,
    }
    overall_pass = all(gates.values()) and not violations

    compact_activation_keys: list[str] = []
    for row in activation_ledger:
        compact_activation_keys.append(
            f"{row['panel']}|{row['opponent']}|seat{row['seat']}|seed{row['seed']}"
        )

    result = {
        "audit": "archaludon_historical_silver_single_resolver_salvage_v1_rule1_fixed160",
        "assessment": "PASS" if overall_pass else "FAIL",
        "assumptions": [
            "Each panel directory structurally supplies the required panel field because the checked runner emits one paired_results.csv per panel.",
            "A policy win is result == 0 at seat 0 (agent A/player 0) and result == 1 at seat 1 (agent B/player 1).",
            "Rows are paired by the immutable (panel, opponent, seat, seed) key; no player-0 win counter is reused for seat 1.",
            "Natural Rule 1 starts are counted only when the same-state first trace difference is parent [] versus one candidate setup-Bench option, with visible Cinderace-Active commitment and a later Cinderace/Duraludon board post-state.",
            "Inference is conditional on the frozen opponents and seeds; no aggregate delta alone establishes strength.",
        ],
        "policy_to_player_mapping": {
            "seat_0": "tested policy is agent A/player 0; win iff result == 0",
            "seat_1": "tested policy is agent B/player 1; win iff result == 1",
        },
        "hashes": {
            "artifacts": artifact_hashes,
            "raw_tree": raw_tree,
            "panels": panel_hashes,
        },
        "schedule_and_health": {
            "expected_keys": len(expected_keys),
            "reconstructed_unique_keys": len(records),
            "manifest_rows": manifest_rows,
            "exit_failures": exit_failures,
            "start_faults": start_faults,
            "action_errors": action_errors,
            "exception_fields": exception_fields,
            "max_step_hits": max_step_hits,
            "invalid_results": invalid_results,
            "malformed_trace_rows": malformed_trace_rows,
            "trace_step_faults": trace_step_faults,
            "duplicate_game_tuple_matches": len(records) - duplicate_tuple_mismatches,
            "duplicate_nontrace_summary_matches": len(records) - duplicate_summary_mismatches,
            "duplicate_result_matches": len(records) - duplicate_result_mismatches,
            "duplicate_decision_count_matches": len(records) - duplicate_decision_count_mismatches,
            "duplicate_byte_trace_matches": len(records) - duplicate_trace_mismatches,
            "runner_discrepancies": runner_discrepancies,
        },
        "identical_policy_control": identical_policy_control,
        "aggregate": overall,
        "paired_uncertainty": paired_uncertainty,
        "by_panel": by_panel,
        "by_opponent": by_opponent,
        "by_seat": by_seat,
        "by_cell": by_cell,
        "seed_sensitivity": seed_sensitivity,
        "seed_quartiles": seed_quartiles,
        "rule1_mechanism": {
            "candidate_trace_different_games": trace_diff_games,
            "natural_starts": natural_starts,
            "starts_by_seat": {str(seat): starts_by_seat[seat] for seat in (0, 1)},
            "starts_by_opponent": dict(sorted(starts_by_opponent.items())),
            "starts_by_opponent_and_seat": {
                f"{opponent}|seat{seat}": starts_by_cell[(opponent, seat)]
                for opponent in sorted({row["opponent"] for row in rows})
                for seat in (0, 1)
            },
            "mechanism_faults": mechanism_faults,
            "activation_outcome_gains": sum(row["outcome_delta"] > 0 for row in activation_ledger),
            "activation_outcome_regressions": sum(row["outcome_delta"] < 0 for row in activation_ledger),
            "activation_outcome_ties": sum(row["outcome_delta"] == 0 for row in activation_ledger),
            "activation_keys": compact_activation_keys,
        },
        "practical_effect": {
            "observed_delta_wins": overall["delta_wins"],
            "observed_delta_rate": overall["delta_rate"],
            "meaningful_improvement": False,
            "reason": "zero paired gains and zero paired regressions; Rule 1 activated naturally but changed no game outcome",
        },
        "gates": gates,
        "violations": violations,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    main()
