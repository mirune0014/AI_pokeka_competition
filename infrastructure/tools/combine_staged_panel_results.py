"""Combine and independently validate sharded staged-comparison results.

The checked paired runner is intentionally left unchanged.  This tool treats
each ``<seed_base>_<opponent>/attempt_N`` directory as immutable evidence,
selects the first attempt whose checked-runner report says ``valid: true``,
and then validates that selected attempt from its raw CSV, manifest, and game
summaries.  A later attempt is never substituted when root validation of the
first report-valid attempt fails.

Only Python's standard library is used so the combiner can be rerun in the
same restricted environments as the checked runner.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKED_PAIRED_RUNNER = REPO_ROOT / "infrastructure" / "tools" / "run_seeded_paired_suite.py"
RUN_LOCAL_BATTLE = REPO_ROOT / "infrastructure" / "tools" / "run_local_battle.py"
PAIRED_FIELDS = (
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
)
ROLES = ("baseline_a", "baseline_b", "candidate")
SUMMARY_DUPLICATE_FIELDS = (
    "seed",
    "result",
    "steps",
    "turn",
    "action_errors",
    "hit_max_steps",
)
ATTEMPT_RE = re.compile(r"^attempt_([0-9]+)$")
OUTPUT_NAMES = (
    "combined_paired_results.csv",
    "combined_manifest.jsonl",
    "root_combined_runner_report.json",
    "root_recomputation.json",
    "combination_provenance.json",
    "validation_report.json",
)


@dataclass(frozen=True)
class CombinationConfig:
    panel_root: Path
    out_dir: Path
    comparison_name: str
    seed_bases: tuple[int, ...]
    opponents: tuple[str, ...]
    games_per_seat: int
    max_attempts: int
    immutable_spec: Path
    execution_amendments: tuple[Path, ...]
    max_steps: int = 1000


@dataclass
class PanelData:
    seed_base: int
    opponent: str
    selected_attempt: int
    paired_rows: list[dict[str, Any]]
    manifest_rows: list[dict[str, Any]]
    manifest_raw_lines: list[str]
    summaries: dict[tuple[int, str], list[dict[str, Any]]]
    report: dict[str, Any]


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _file_record(path: Path, *, relative_to: Path | None = None) -> dict[str, Any]:
    resolved = path.resolve()
    label: str
    if relative_to is not None:
        try:
            label = resolved.relative_to(relative_to.resolve()).as_posix()
        except ValueError:
            label = str(resolved)
    else:
        label = str(resolved)
    record: dict[str, Any] = {"path": label, "exists": resolved.is_file()}
    if resolved.is_file():
        digest = hashlib.sha256()
        size = 0
        with resolved.open("rb") as handle:
            while True:
                block = handle.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
                size += len(block)
        record.update({"size": size, "sha256": digest.hexdigest().upper()})
    return record


def _attempt_file_records(attempt_dir: Path) -> list[dict[str, Any]]:
    if not attempt_dir.is_dir():
        return []
    return [
        _file_record(path, relative_to=attempt_dir)
        for path in sorted(
            (path for path in attempt_dir.rglob("*") if path.is_file()),
            key=lambda path: path.relative_to(attempt_dir).as_posix(),
        )
    ]


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _write_json(path: Path, value: Any) -> None:
    _write_text_atomic(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    raw_lines = path.read_text(encoding="utf-8-sig").splitlines()
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw_lines, 1):
        if not line.strip():
            raise ValueError(f"blank JSONL line at {path}:{line_number}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"JSONL row is not an object at {path}:{line_number}")
        rows.append(value)
    return rows, raw_lines


def _parse_csv_int(raw: dict[str, str], field: str, context: str) -> int:
    value = raw.get(field)
    if value is None or value == "":
        raise ValueError(f"{context}: {field} is blank")
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{context}: {field} is not an integer: {value!r}") from exc


def _read_paired_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != PAIRED_FIELDS:
            raise ValueError(
                f"paired header mismatch: expected {list(PAIRED_FIELDS)!r}, "
                f"got {reader.fieldnames!r}"
            )
        rows: list[dict[str, Any]] = []
        numeric = set(PAIRED_FIELDS) - {"opponent"}
        for line_number, raw in enumerate(reader, 2):
            context = f"{path}:{line_number}"
            if None in raw:
                raise ValueError(f"{context}: extra CSV fields are present")
            row = {
                field: (
                    raw[field]
                    if field == "opponent"
                    else _parse_csv_int(raw, field, context)
                )
                for field in PAIRED_FIELDS
            }
            if any(raw.get(field) is None for field in numeric):
                raise ValueError(f"{context}: missing CSV field")
            rows.append(row)
    return rows


def _option_value(
    command: Sequence[Any],
    option: str,
    errors: list[str],
    context: str,
) -> str | None:
    positions = [index for index, value in enumerate(command) if value == option]
    if len(positions) != 1:
        errors.append(f"{context}: command must contain {option} exactly once")
        return None
    position = positions[0]
    if position + 1 >= len(command):
        errors.append(f"{context}: command option {option} has no value")
        return None
    value = command[position + 1]
    if not isinstance(value, str) or value.startswith("--"):
        errors.append(f"{context}: command option {option} has an invalid value")
        return None
    return value


def _command_path(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def _schedule_hash(keys: Iterable[tuple[Any, ...]]) -> str:
    payload = "".join(_canonical_json(list(key)) + "\n" for key in keys)
    return _sha256_bytes(payload.encode("utf-8"))


def _semantic_manifest_hash(keys: Iterable[tuple[Any, ...]]) -> str:
    return _schedule_hash(keys)


def _panel_rollups(
    rows: Sequence[dict[str, Any]],
    seed_bases: Sequence[int],
    opponents: Sequence[str],
) -> dict[str, Any]:
    panel_groups: dict[tuple[int, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        panel_groups[(row["seed_base"], row["opponent"], row["seat"])].append(row)

    panels: list[dict[str, Any]] = []
    for seed_base in seed_bases:
        for opponent in opponents:
            for seat in (0, 1):
                group = panel_groups[(seed_base, opponent, seat)]
                baseline_wins = sum(row["baseline_win"] for row in group)
                candidate_wins = sum(row["candidate_win"] for row in group)
                panels.append(
                    {
                        "seed_base": seed_base,
                        "opponent": opponent,
                        "seat": seat,
                        "baseline_wins": baseline_wins,
                        "candidate_wins": candidate_wins,
                        "games": len(group),
                        "delta_wins": candidate_wins - baseline_wins,
                    }
                )

    by_opponent: list[dict[str, Any]] = []
    for opponent in opponents:
        group = [row for row in rows if row["opponent"] == opponent]
        baseline_wins = sum(row["baseline_win"] for row in group)
        candidate_wins = sum(row["candidate_win"] for row in group)
        by_opponent.append(
            {
                "opponent": opponent,
                "baseline_wins": baseline_wins,
                "candidate_wins": candidate_wins,
                "games": len(group),
                "delta_wins": candidate_wins - baseline_wins,
            }
        )

    by_seat: list[dict[str, Any]] = []
    for seat in (0, 1):
        group = [row for row in rows if row["seat"] == seat]
        baseline_wins = sum(row["baseline_win"] for row in group)
        candidate_wins = sum(row["candidate_win"] for row in group)
        by_seat.append(
            {
                "seat": seat,
                "baseline_wins": baseline_wins,
                "candidate_wins": candidate_wins,
                "games": len(group),
                "delta_wins": candidate_wins - baseline_wins,
            }
        )

    baseline_wins = sum(row["baseline_win"] for row in rows)
    candidate_wins = sum(row["candidate_win"] for row in rows)
    aggregates = {
        "baseline_wins": baseline_wins,
        "candidate_wins": candidate_wins,
        "games": len(rows),
        "delta_wins": candidate_wins - baseline_wins,
    }
    return {
        "panels": panels,
        "by_opponent": by_opponent,
        "by_seat": by_seat,
        "aggregates": aggregates,
    }


def _validate_report(
    report: dict[str, Any],
    paired_rows: Sequence[dict[str, Any]],
    seed_base: int,
    opponent: str,
    errors: list[str],
    context: str,
) -> None:
    if report.get("valid") is not True or not isinstance(report.get("valid"), bool):
        errors.append(f"{context}: report.valid is not boolean true")
    if report.get("invalid_reasons") != []:
        errors.append(f"{context}: report.invalid_reasons is not []")
    duplicate_count = report.get("duplicate_mismatch_count")
    if not _is_int(duplicate_count) or duplicate_count != 0:
        errors.append(f"{context}: report.duplicate_mismatch_count is not integer 0")

    expected = _panel_rollups(paired_rows, (seed_base,), (opponent,))
    for field in ("panels", "by_opponent", "by_seat", "aggregates"):
        if _canonical_json(report.get(field)) != _canonical_json(expected[field]):
            errors.append(f"{context}: report.{field} disagrees with raw paired rows")


def _validate_summary_rows(
    rows: Sequence[dict[str, Any]],
    *,
    seed_base: int,
    games_per_seat: int,
    errors: list[str],
    context: str,
) -> None:
    if len(rows) != games_per_seat:
        errors.append(
            f"{context}: expected {games_per_seat} summary rows, got {len(rows)}"
        )
    for index, row in enumerate(rows):
        row_context = f"{context}:row_{index}"
        if row.get("started") is not True or not isinstance(row.get("started"), bool):
            errors.append(f"{row_context}: started is not boolean true")
        if not _is_int(row.get("game")) or row.get("game") != index:
            errors.append(f"{row_context}: game is not {index}")
        if not _is_int(row.get("seed")) or row.get("seed") != seed_base + index:
            errors.append(f"{row_context}: seed is not {seed_base + index}")
        if not _is_int(row.get("result")) or row.get("result") not in (0, 1):
            errors.append(f"{row_context}: result is not integer 0 or 1")
        if not _is_int(row.get("steps")) or row.get("steps") < 0:
            errors.append(f"{row_context}: steps is not a non-negative integer")
        if not _is_int(row.get("action_errors")) or row.get("action_errors") != 0:
            errors.append(f"{row_context}: action_errors is not integer 0")
        if (
            row.get("hit_max_steps") is not False
            or not isinstance(row.get("hit_max_steps"), bool)
        ):
            errors.append(f"{row_context}: hit_max_steps is not boolean false")


def _validate_selected_attempt(
    attempt_dir: Path,
    *,
    seed_base: int,
    opponent: str,
    attempt_number: int,
    games_per_seat: int,
    max_steps: int,
    errors: list[str],
) -> PanelData | None:
    prefix = f"{seed_base}/{opponent}/attempt_{attempt_number}"
    starting_error_count = len(errors)
    report_path = attempt_dir / "report.json"
    paired_path = attempt_dir / "paired_results.csv"
    manifest_path = attempt_dir / "manifest.jsonl"

    try:
        report = _read_json(report_path)
        if not isinstance(report, dict):
            raise ValueError("report root is not an object")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"{prefix}: cannot read report.json: {exc}")
        return None
    try:
        paired_rows = _read_paired_csv(paired_path)
    except (OSError, ValueError, csv.Error) as exc:
        errors.append(f"{prefix}: cannot read paired_results.csv: {exc}")
        paired_rows = []
    try:
        manifest_rows, manifest_raw_lines = _read_jsonl(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"{prefix}: cannot read manifest.jsonl: {exc}")
        manifest_rows, manifest_raw_lines = [], []

    expected_paired_keys = [
        (seed_base, opponent, seat, game, seed_base + game)
        for seat in (0, 1)
        for game in range(games_per_seat)
    ]
    actual_paired_keys: list[tuple[Any, ...]] = []
    seen_paired_keys: set[tuple[Any, ...]] = set()
    for index, row in enumerate(paired_rows):
        key = tuple(row[field] for field in PAIRED_FIELDS[:5])
        actual_paired_keys.append(key)
        if key in seen_paired_keys:
            errors.append(f"{prefix}: duplicate paired schedule key {key!r}")
        seen_paired_keys.add(key)
        row_context = f"{prefix}:paired_row_{index}"
        if row["baseline_result"] not in (0, 1):
            errors.append(f"{row_context}: baseline_result is not 0 or 1")
        if row["candidate_result"] not in (0, 1):
            errors.append(f"{row_context}: candidate_result is not 0 or 1")
        if row["baseline_steps"] < 0 or row["candidate_steps"] < 0:
            errors.append(f"{row_context}: steps are not non-negative")
        expected_baseline_win = int(row["baseline_result"] == row["seat"])
        expected_candidate_win = int(row["candidate_result"] == row["seat"])
        if row["baseline_win"] != expected_baseline_win:
            errors.append(f"{row_context}: baseline_win is not seat-aware")
        if row["candidate_win"] != expected_candidate_win:
            errors.append(f"{row_context}: candidate_win is not seat-aware")
    if actual_paired_keys != expected_paired_keys:
        expected_set, actual_set = set(expected_paired_keys), set(actual_paired_keys)
        errors.append(
            f"{prefix}: paired schedule mismatch "
            f"(missing={len(expected_set - actual_set)}, "
            f"extra={len(actual_set - expected_set)}, "
            f"rows={len(actual_paired_keys)})"
        )

    expected_manifest = [
        (sequence, role, seat)
        for seat in (0, 1)
        for role in ROLES
        for sequence in (seat * len(ROLES) + ROLES.index(role),)
    ]
    if len(manifest_rows) != len(expected_manifest):
        errors.append(
            f"{prefix}: expected {len(expected_manifest)} manifest rows, "
            f"got {len(manifest_rows)}"
        )

    summaries: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for index, row in enumerate(manifest_rows):
        manifest_context = f"{prefix}:manifest_row_{index}"
        if index >= len(expected_manifest):
            continue
        sequence, role, seat = expected_manifest[index]
        for field, expected_value in (
            ("sequence", sequence),
            ("role", role),
            ("seed_base", seed_base),
            ("opponent", opponent),
            ("seat", seat),
            ("exit_code", 0),
        ):
            actual_value = row.get(field)
            if (
                isinstance(expected_value, int)
                and not isinstance(expected_value, bool)
                and not _is_int(actual_value)
            ) or actual_value != expected_value:
                errors.append(
                    f"{manifest_context}: {field} is {actual_value!r}, "
                    f"expected {expected_value!r}"
                )

        command = row.get("command")
        if not isinstance(command, list) or not all(
            isinstance(value, str) for value in command
        ):
            errors.append(f"{manifest_context}: command is not a string list")
            continue
        if len(command) < 2 or _command_path(command[1]) != RUN_LOCAL_BATTLE.resolve():
            errors.append(
                f"{manifest_context}: command runner is not {RUN_LOCAL_BATTLE.resolve()}"
            )
        values: dict[str, str | None] = {}
        for option in ("--games", "--max-steps", "--seed-base", "--summary"):
            values[option] = _option_value(command, option, errors, manifest_context)
        if command.count("--engine-seed") != 1:
            errors.append(
                f"{manifest_context}: command must contain --engine-seed exactly once"
            )
        for option, expected_value in (
            ("--games", games_per_seat),
            ("--max-steps", max_steps),
            ("--seed-base", seed_base),
        ):
            value = values[option]
            if value is not None:
                try:
                    parsed = int(value)
                except ValueError:
                    errors.append(
                        f"{manifest_context}: {option} value is not an integer"
                    )
                else:
                    if parsed != expected_value:
                        errors.append(
                            f"{manifest_context}: {option} is {parsed}, "
                            f"expected {expected_value}"
                        )

        expected_summary = (
            attempt_dir
            / "summaries"
            / f"{sequence:04d}_{seed_base}_{opponent}_p{seat}_{role}.jsonl"
        ).resolve()
        summary_value = values["--summary"]
        if summary_value is None:
            continue
        actual_summary = _command_path(summary_value)
        if actual_summary != expected_summary:
            errors.append(
                f"{manifest_context}: --summary path is {actual_summary}, "
                f"expected {expected_summary}"
            )
            continue
        try:
            summary_rows, _ = _read_jsonl(expected_summary)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{manifest_context}: cannot read summary: {exc}")
            continue
        _validate_summary_rows(
            summary_rows,
            seed_base=seed_base,
            games_per_seat=games_per_seat,
            errors=errors,
            context=f"{prefix}:{role}:seat_{seat}",
        )
        summaries[(seat, role)] = summary_rows

    for seat in (0, 1):
        baseline_a = summaries.get((seat, "baseline_a"), [])
        baseline_b = summaries.get((seat, "baseline_b"), [])
        candidate = summaries.get((seat, "candidate"), [])
        if len(baseline_a) == len(baseline_b) == games_per_seat:
            for game, (left, right) in enumerate(zip(baseline_a, baseline_b)):
                left_values = tuple(left.get(field) for field in SUMMARY_DUPLICATE_FIELDS)
                right_values = tuple(right.get(field) for field in SUMMARY_DUPLICATE_FIELDS)
                if _canonical_json(left_values) != _canonical_json(right_values):
                    errors.append(
                        f"{prefix}: baseline_a/b mismatch at seat={seat}, game={game}"
                    )
        if len(baseline_a) == len(candidate) == games_per_seat:
            for game in range(games_per_seat):
                paired_index = seat * games_per_seat + game
                if paired_index >= len(paired_rows):
                    continue
                paired = paired_rows[paired_index]
                baseline = baseline_a[game]
                candidate_row = candidate[game]
                comparisons = (
                    ("baseline_result", baseline.get("result")),
                    ("baseline_steps", baseline.get("steps")),
                    ("candidate_result", candidate_row.get("result")),
                    ("candidate_steps", candidate_row.get("steps")),
                )
                for field, expected_value in comparisons:
                    if paired[field] != expected_value:
                        errors.append(
                            f"{prefix}: paired {field} disagrees with summary "
                            f"at seat={seat}, game={game}"
                        )

    if paired_rows:
        _validate_report(
            report,
            paired_rows,
            seed_base,
            opponent,
            errors,
            prefix,
        )

    if len(errors) != starting_error_count:
        return None
    return PanelData(
        seed_base=seed_base,
        opponent=opponent,
        selected_attempt=attempt_number,
        paired_rows=paired_rows,
        manifest_rows=manifest_rows,
        manifest_raw_lines=manifest_raw_lines,
        summaries=summaries,
        report=report,
    )


def _validate_config(config: CombinationConfig, errors: list[str]) -> None:
    if not config.comparison_name.strip():
        errors.append("comparison_name is blank")
    if not config.seed_bases:
        errors.append("seed_bases is empty")
    if len(set(config.seed_bases)) != len(config.seed_bases):
        errors.append("seed_bases contains duplicates")
    if not config.opponents:
        errors.append("opponents is empty")
    if any(not opponent for opponent in config.opponents):
        errors.append("opponents contains a blank label")
    if len(set(config.opponents)) != len(config.opponents):
        errors.append("opponents contains duplicates")
    if config.games_per_seat <= 0:
        errors.append("games_per_seat must be positive")
    if config.max_attempts <= 0:
        errors.append("max_attempts must be positive")
    if config.max_steps <= 0:
        errors.append("max_steps must be positive")
    if not config.panel_root.is_dir():
        errors.append(f"panel_root is not a directory: {config.panel_root}")
    if not config.immutable_spec.is_file():
        errors.append(f"immutable_spec is not a file: {config.immutable_spec}")
    if not config.execution_amendments:
        errors.append("at least one execution/amendment path is required")
    for path in config.execution_amendments:
        if not path.is_file():
            errors.append(f"execution/amendment path is not a file: {path}")


def _git_info() -> dict[str, Any]:
    def invoke(arguments: list[str]) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                ["git", *arguments],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"ok": False, "error": str(exc)}
        return {
            "ok": completed.returncode == 0,
            "exit_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }

    return {
        "head": invoke(["rev-parse", "HEAD"]),
        "branch": invoke(["branch", "--show-current"]),
        "combiner_status": invoke(
            [
                "status",
                "--porcelain",
                "--",
                str(Path(__file__).resolve().relative_to(REPO_ROOT)),
            ]
        ),
    }


def _make_provenance(
    config: CombinationConfig,
    attempt_records: list[dict[str, Any]],
    selected_attempts: list[dict[str, Any]],
    errors: Sequence[str],
) -> dict[str, Any]:
    input_records = [_file_record(config.immutable_spec)]
    input_records.extend(_file_record(path) for path in config.execution_amendments)
    return {
        "schema_version": 1,
        "comparison_name": config.comparison_name,
        "panel_root": str(config.panel_root.resolve()),
        "out_dir": str(config.out_dir.resolve()),
        "configuration": {
            "seed_bases": list(config.seed_bases),
            "opponents": list(config.opponents),
            "games_per_seat": config.games_per_seat,
            "max_attempts": config.max_attempts,
            "max_steps": config.max_steps,
        },
        "inputs": input_records,
        "attempts": attempt_records,
        "selected_attempts": selected_attempts,
        "validation_error_count": len(errors),
        "tools": {
            "combiner": _file_record(Path(__file__)),
            "checked_paired_runner": _file_record(CHECKED_PAIRED_RUNNER),
            "battle_runner": _file_record(RUN_LOCAL_BATTLE),
            "python": {
                "executable": sys.executable,
                "version": sys.version,
            },
        },
        "git": _git_info(),
    }


def _ordered_expected_schedule(
    config: CombinationConfig,
) -> list[tuple[int, str, int, int, int]]:
    return [
        (seed_base, opponent, seat, game, seed_base + game)
        for seed_base in config.seed_bases
        for opponent in config.opponents
        for seat in (0, 1)
        for game in range(config.games_per_seat)
    ]


def _ordered_expected_manifest(
    config: CombinationConfig,
) -> list[tuple[int, str, int, str]]:
    return [
        (seed_base, opponent, seat, role)
        for seed_base in config.seed_bases
        for opponent in config.opponents
        for seat in (0, 1)
        for role in ROLES
    ]


def combine_panels(config: CombinationConfig) -> dict[str, Any]:
    """Validate and combine panel attempts, writing evidence reports.

    The return value is the same object written to ``validation_report.json``.
    Validation failures are reported in the object rather than raised so tests
    and callers can inspect the exact failure.  The CLI converts ``valid=false``
    to a non-zero exit status.
    """

    config = CombinationConfig(
        panel_root=config.panel_root.resolve(),
        out_dir=config.out_dir.resolve(),
        comparison_name=config.comparison_name,
        seed_bases=tuple(config.seed_bases),
        opponents=tuple(config.opponents),
        games_per_seat=config.games_per_seat,
        max_attempts=config.max_attempts,
        immutable_spec=config.immutable_spec.resolve(),
        execution_amendments=tuple(path.resolve() for path in config.execution_amendments),
        max_steps=config.max_steps,
    )
    config.out_dir.mkdir(parents=True, exist_ok=True)
    for name in OUTPUT_NAMES:
        path = config.out_dir / name
        if path.is_file():
            path.unlink()

    errors: list[str] = []
    warnings: list[str] = []
    _validate_config(config, errors)

    expected_panels = [
        (seed_base, opponent)
        for seed_base in config.seed_bases
        for opponent in config.opponents
    ]
    expected_panel_names = {
        f"{seed_base}_{opponent}" for seed_base, opponent in expected_panels
    }
    actual_panel_names: set[str] = set()
    if config.panel_root.is_dir():
        actual_panel_names = {
            path.name for path in config.panel_root.iterdir() if path.is_dir()
        }
        missing_panels = sorted(expected_panel_names - actual_panel_names)
        extra_panels = sorted(actual_panel_names - expected_panel_names)
        if missing_panels:
            errors.append(f"missing expected panel directories: {missing_panels!r}")
        if extra_panels:
            errors.append(f"unexpected panel directories: {extra_panels!r}")

    selected_attempts: list[dict[str, Any]] = []
    attempt_records: list[dict[str, Any]] = []
    panel_data: list[PanelData] = []
    for seed_base, opponent in expected_panels:
        panel_name = f"{seed_base}_{opponent}"
        panel_dir = config.panel_root / panel_name
        if not panel_dir.is_dir():
            continue
        numbered_attempts: list[tuple[int, Path]] = []
        unexpected_children: list[str] = []
        for child in panel_dir.iterdir():
            if not child.is_dir():
                continue
            match = ATTEMPT_RE.fullmatch(child.name)
            if match:
                numbered_attempts.append((int(match.group(1)), child))
            else:
                unexpected_children.append(child.name)
        numbered_attempts.sort(key=lambda item: item[0])
        if unexpected_children:
            errors.append(
                f"{panel_name}: unexpected child directories "
                f"{sorted(unexpected_children)!r}"
            )
        numbers = [number for number, _ in numbered_attempts]
        if not numbers:
            errors.append(f"{panel_name}: no attempt directories")
            continue
        if numbers != list(range(1, max(numbers) + 1)):
            errors.append(f"{panel_name}: attempt numbers are not contiguous from 1")
        if any(number > config.max_attempts for number in numbers):
            errors.append(
                f"{panel_name}: attempt number exceeds max_attempts={config.max_attempts}"
            )

        report_values: dict[int, dict[str, Any] | None] = {}
        for number, attempt_dir in numbered_attempts:
            report_value: dict[str, Any] | None = None
            report_error: str | None = None
            report_path = attempt_dir / "report.json"
            try:
                candidate = _read_json(report_path)
                if not isinstance(candidate, dict):
                    raise ValueError("report root is not an object")
                report_value = candidate
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                report_error = str(exc)
                errors.append(
                    f"{panel_name}/attempt_{number}: unreadable report.json: {exc}"
                )
            report_values[number] = report_value
            attempt_records.append(
                {
                    "seed_base": seed_base,
                    "opponent": opponent,
                    "panel": panel_name,
                    "attempt": number,
                    "path": str(attempt_dir.resolve()),
                    "report_valid": (
                        report_value.get("valid") if report_value is not None else None
                    ),
                    "report_error": report_error,
                    "files": _attempt_file_records(attempt_dir),
                }
            )

        first_valid: int | None = next(
            (
                number
                for number, _ in numbered_attempts
                if report_values[number] is not None
                and report_values[number].get("valid") is True
                and isinstance(report_values[number].get("valid"), bool)
            ),
            None,
        )
        if first_valid is None:
            errors.append(f"{panel_name}: no report-valid attempt")
            continue
        later_attempts = [number for number in numbers if number > first_valid]
        if later_attempts:
            errors.append(
                f"{panel_name}: attempts exist after first report-valid attempt "
                f"{first_valid}: {later_attempts!r}"
            )
        selected_attempts.append(
            {
                "seed_base": seed_base,
                "opponent": opponent,
                "panel": panel_name,
                "attempt": first_valid,
                "path": str((panel_dir / f"attempt_{first_valid}").resolve()),
            }
        )
        for attempt_record in attempt_records:
            if attempt_record["panel"] == panel_name:
                attempt_record["selected"] = (
                    attempt_record["attempt"] == first_valid
                )
                attempt_record["after_first_report_valid"] = (
                    attempt_record["attempt"] > first_valid
                )
        data = _validate_selected_attempt(
            panel_dir / f"attempt_{first_valid}",
            seed_base=seed_base,
            opponent=opponent,
            attempt_number=first_valid,
            games_per_seat=config.games_per_seat,
            max_steps=config.max_steps,
            errors=errors,
        )
        if data is not None:
            panel_data.append(data)

    expected_schedule = _ordered_expected_schedule(config)
    actual_rows = [
        row
        for panel in panel_data
        for row in panel.paired_rows
    ]
    actual_schedule = [
        tuple(row[field] for field in PAIRED_FIELDS[:5]) for row in actual_rows
    ]
    expected_manifest = _ordered_expected_manifest(config)
    actual_manifest = [
        (row.get("seed_base"), row.get("opponent"), row.get("seat"), row.get("role"))
        for panel in panel_data
        for row in panel.manifest_rows
    ]
    if len(panel_data) != len(expected_panels):
        errors.append(
            f"validated panel count mismatch: expected {len(expected_panels)}, "
            f"got {len(panel_data)}"
        )
    if actual_schedule != expected_schedule:
        expected_set, actual_set = set(expected_schedule), set(actual_schedule)
        errors.append(
            "combined paired schedule mismatch "
            f"(missing={len(expected_set - actual_set)}, "
            f"extra={len(actual_set - expected_set)}, "
            f"rows={len(actual_schedule)})"
        )
    if actual_manifest != expected_manifest:
        expected_set, actual_set = set(expected_manifest), set(actual_manifest)
        errors.append(
            "combined manifest schedule mismatch "
            f"(missing={len(expected_set - actual_set)}, "
            f"extra={len(actual_set - expected_set)}, "
            f"rows={len(actual_manifest)})"
        )

    validation = {
        "schema_version": 1,
        "comparison_name": config.comparison_name,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "expected_panel_count": len(expected_panels),
        "actual_panel_directory_count": len(actual_panel_names),
        "validated_panel_count": len(panel_data),
        "selected_attempts": selected_attempts,
    }
    provenance = _make_provenance(
        config, attempt_records, selected_attempts, errors
    )
    _write_json(config.out_dir / "combination_provenance.json", provenance)

    if not errors:
        rollups = _panel_rollups(actual_rows, config.seed_bases, config.opponents)
        combined_report = {
            "schema_version": 1,
            "comparison_name": config.comparison_name,
            "derived_source": {
                "kind": "root_combination_of_checked_panel_reports",
                "panel_root": str(config.panel_root),
                "panel_count": len(panel_data),
                "selection_rule": "first_attempt_with_boolean_report_valid_true",
                "root_validation": "raw_paired_manifest_and_summary_recomputation",
            },
            "valid": True,
            "invalid_reasons": [],
            "duplicate_mismatch_count": 0,
            **rollups,
        }

        paired_path = config.out_dir / "combined_paired_results.csv"
        temporary_paired = paired_path.with_name(paired_path.name + ".tmp")
        with temporary_paired.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(PAIRED_FIELDS))
            writer.writeheader()
            writer.writerows(actual_rows)
        os.replace(temporary_paired, paired_path)

        combined_manifest_text = "".join(
            line + "\n"
            for panel in panel_data
            for line in panel.manifest_raw_lines
        )
        _write_text_atomic(
            config.out_dir / "combined_manifest.jsonl",
            combined_manifest_text,
        )
        _write_json(
            config.out_dir / "root_combined_runner_report.json",
            combined_report,
        )

        recomputation = {
            "schema_version": 1,
            "comparison_name": config.comparison_name,
            "schedule_hash_definition": (
                "SHA-256 of UTF-8 canonical JSON arrays, one key per LF line; "
                "paired key=(seed_base,opponent,seat,game,seed)"
            ),
            "expected_schedule_sha256": _schedule_hash(expected_schedule),
            "actual_schedule_sha256": _schedule_hash(actual_schedule),
            "manifest_hash_definition": (
                "SHA-256 of UTF-8 canonical JSON arrays, one key per LF line; "
                "manifest key=(seed_base,opponent,seat,role)"
            ),
            "expected_manifest_schedule_sha256": _semantic_manifest_hash(
                expected_manifest
            ),
            "actual_manifest_schedule_sha256": _semantic_manifest_hash(
                actual_manifest
            ),
            "counts": {
                "expected_panels": len(expected_panels),
                "actual_panels": len(panel_data),
                "expected_paired_rows": len(expected_schedule),
                "actual_paired_rows": len(actual_rows),
                "expected_manifest_rows": len(expected_manifest),
                "actual_manifest_rows": len(actual_manifest),
                "expected_summary_rows": (
                    len(expected_panels) * 2 * len(ROLES) * config.games_per_seat
                ),
                "actual_summary_rows": sum(
                    len(rows)
                    for panel in panel_data
                    for rows in panel.summaries.values()
                ),
            },
            "mismatches": {
                "panel": 0,
                "paired_schedule": 0,
                "manifest_schedule": 0,
                "duplicate_paired_keys": 0,
                "duplicate_manifest_keys": 0,
                "seat_aware_wins": 0,
                "baseline_duplicate_summaries": 0,
                "summary_to_paired": 0,
                "report_to_raw_rollups": 0,
            },
            "output_files": {
                "combined_paired_results": _file_record(paired_path),
                "combined_manifest": _file_record(
                    config.out_dir / "combined_manifest.jsonl"
                ),
            },
            "aggregates": rollups["aggregates"],
        }
        _write_json(
            config.out_dir / "root_recomputation.json",
            recomputation,
        )

    _write_json(config.out_dir / "validation_report.json", validation)
    return validation


def _csv_values(value: str) -> tuple[str, ...]:
    values = tuple(part.strip() for part in value.split(","))
    if not values or any(not part for part in values):
        raise argparse.ArgumentTypeError("CSV value contains a blank item")
    return values


def _seed_csv(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in _csv_values(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("seed-bases must be integer CSV") from exc


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Strictly combine staged checked-runner panel attempts."
    )
    parser.add_argument("--panel-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--comparison-name", required=True)
    parser.add_argument("--seed-bases", type=_seed_csv, required=True)
    parser.add_argument("--opponents", type=_csv_values, required=True)
    parser.add_argument("--games-per-seat", type=int, required=True)
    parser.add_argument("--max-attempts", type=int, required=True)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--immutable-spec", type=Path, required=True)
    parser.add_argument(
        "--execution-amendment-path",
        "--execution-amendment",
        "--execution-path",
        "--amendment-path",
        dest="execution_amendments",
        type=Path,
        action="append",
        required=True,
        help="Repeat for every execution ledger or immutable amendment input.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = CombinationConfig(
        panel_root=args.panel_root,
        out_dir=args.out_dir,
        comparison_name=args.comparison_name,
        seed_bases=args.seed_bases,
        opponents=args.opponents,
        games_per_seat=args.games_per_seat,
        max_attempts=args.max_attempts,
        immutable_spec=args.immutable_spec,
        execution_amendments=tuple(args.execution_amendments),
        max_steps=args.max_steps,
    )
    validation = combine_panels(config)
    print(
        json.dumps(
            {
                "valid": validation["valid"],
                "comparison_name": validation["comparison_name"],
                "error_count": len(validation["errors"]),
                "errors": validation["errors"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if validation["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
