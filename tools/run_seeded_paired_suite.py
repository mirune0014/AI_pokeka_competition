"""Run deterministic, seat-balanced paired policy evaluations.

Each schedule cell is run as baseline control A, baseline control B, and the
candidate.  The duplicate controls make an engine or policy nondeterminism
visible before candidate deltas are used.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
RUN_LOCAL_BATTLE = REPO_ROOT / "tools" / "run_local_battle.py"
GAME_FIELDS = ("seed", "result", "steps", "turn", "action_errors", "hit_max_steps")


def parse_opponent(value: str) -> tuple[str, Path]:
    """Parse a named opponent while preserving Windows paths containing colons."""
    name, separator, path = value.partition("=")
    if not separator or not name or not path:
        raise argparse.ArgumentTypeError("--opponent must be NAME=PATH")
    return name, Path(path)


def policy_won(record: dict[str, Any], policy_seat: int) -> bool:
    return record.get("result") == policy_seat


def build_command(
    *,
    engine_dir: Path,
    policy_dir: Path,
    opponent_dir: Path,
    policy_seat: int,
    seed_base: int,
    games_per_seat: int,
    max_steps: int,
    summary_path: Path,
    trace_dir: Path,
    python_executable: str | Path = sys.executable,
) -> list[str]:
    if policy_seat == 0:
        agent_a, agent_b = policy_dir, opponent_dir
    else:
        agent_a, agent_b = opponent_dir, policy_dir
    return [
        str(python_executable), str(RUN_LOCAL_BATTLE),
        "--engine-dir", str(engine_dir),
        "--agent-a", str(agent_a), "--deck-a", str(agent_a / "deck.csv"),
        "--agent-b", str(agent_b), "--deck-b", str(agent_b / "deck.csv"),
        "--games", str(games_per_seat), "--max-steps", str(max_steps),
        "--seed-base", str(seed_base), "--engine-seed",
        "--summary", str(summary_path), "--trace-dir", str(trace_dir),
    ]


def read_summary(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"summary was not created: {path}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON in {path}:{line_number}") from exc
    return records


def game_tuple(record: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(record.get(field) for field in GAME_FIELDS)


def duplicate_mismatches(left: Iterable[dict[str, Any]], right: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    left_rows, right_rows = list(left), list(right)
    mismatches: list[dict[str, Any]] = []
    for game_index in range(max(len(left_rows), len(right_rows))):
        first = left_rows[game_index] if game_index < len(left_rows) else None
        second = right_rows[game_index] if game_index < len(right_rows) else None
        if first is None or second is None or game_tuple(first) != game_tuple(second):
            mismatches.append({"game": game_index, "control_a": first, "control_b": second})
    return mismatches


def summarize_cells(cells: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[Any, ...], dict[str, int]] = defaultdict(lambda: {"baseline_wins": 0, "candidate_wins": 0, "games": 0})
    for cell in cells:
        key = (cell["seed_base"], cell["opponent"], cell["seat"])
        group = groups[key]
        group["baseline_wins"] += sum(policy_won(row, cell["seat"]) for row in cell["baseline"])
        group["candidate_wins"] += sum(policy_won(row, cell["seat"]) for row in cell["candidate"])
        group["games"] += len(cell["candidate"])

    panels = []
    for (seed_base, opponent, seat), values in sorted(groups.items()):
        panels.append({"seed_base": seed_base, "opponent": opponent, "seat": seat, **values,
                       "delta_wins": values["candidate_wins"] - values["baseline_wins"]})

    def rollup(keys: tuple[str, ...]) -> list[dict[str, Any]]:
        rows: dict[tuple[Any, ...], dict[str, int]] = defaultdict(lambda: {"baseline_wins": 0, "candidate_wins": 0, "games": 0})
        for panel in panels:
            group = rows[tuple(panel[key] for key in keys)]
            for field in ("baseline_wins", "candidate_wins", "games"):
                group[field] += panel[field]
        return [{key: value for key, value in zip(keys, group_key)} | values |
                 {"delta_wins": values["candidate_wins"] - values["baseline_wins"]}
                for group_key, values in sorted(rows.items())]

    total = {field: sum(panel[field] for panel in panels) for field in ("baseline_wins", "candidate_wins", "games")}
    total["delta_wins"] = total["candidate_wins"] - total["baseline_wins"]
    return {"panels": panels, "by_opponent": rollup(("opponent",)), "by_seat": rollup(("seat",)), "aggregates": total}


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_suite(args: argparse.Namespace, run_process: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.jsonl"
    cells: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    invalid_reasons: list[str] = []
    sequence = 0

    for seed_base in args.seed_base:
        for opponent_name, opponent_path in args.opponent:
            for seat in (0, 1):
                runs: dict[str, list[dict[str, Any]]] = {}
                for role, policy_dir in (("baseline_a", args.baseline), ("baseline_b", args.baseline), ("candidate", args.candidate)):
                    stem = f"{sequence:04d}_{seed_base}_{opponent_name}_p{seat}_{role}"
                    summary_path = output_dir / "summaries" / f"{stem}.jsonl"
                    trace_dir = output_dir / "throwaway_traces" / stem
                    command = build_command(engine_dir=args.engine_dir, policy_dir=policy_dir, opponent_dir=opponent_path,
                                            policy_seat=seat, seed_base=seed_base, games_per_seat=args.games_per_seat,
                                            max_steps=args.max_steps, summary_path=summary_path, trace_dir=trace_dir)
                    started = time.monotonic()
                    try:
                        completed = run_process(command, cwd=str(REPO_ROOT), check=False, capture_output=True, text=True)
                        exit_code = int(completed.returncode)
                    except OSError as exc:
                        completed, exit_code = None, -1
                        invalid_reasons.append(f"subprocess could not start for {stem}: {exc}")
                    runtime = time.monotonic() - started
                    manifest.append({"sequence": sequence, "role": role, "seed_base": seed_base, "opponent": opponent_name,
                                     "seat": seat, "command": command, "exit_code": exit_code, "runtime_seconds": runtime})
                    shutil.rmtree(trace_dir, ignore_errors=True)
                    if exit_code != 0:
                        invalid_reasons.append(f"subprocess failed for {stem} (exit {exit_code})")
                        runs[role] = []
                        break
                    try:
                        runs[role] = read_summary(summary_path)
                    except ValueError as exc:
                        invalid_reasons.append(str(exc))
                        runs[role] = []
                        break
                    if len(runs[role]) != args.games_per_seat:
                        invalid_reasons.append(f"expected {args.games_per_seat} records in {summary_path}, got {len(runs[role])}")
                        break
                    if any(row.get("action_errors", 0) or row.get("hit_max_steps", False) for row in runs[role]):
                        invalid_reasons.append(f"action error or max-step hit in {stem}")
                        break
                    if role == "baseline_b":
                        control_mismatches = duplicate_mismatches(runs["baseline_a"], runs["baseline_b"])
                        if control_mismatches:
                            invalid_reasons.append(
                                f"duplicate baseline mismatch in seed={seed_base}, opponent={opponent_name}, seat={seat}"
                            )
                            break
                    sequence += 1
                baseline_a, baseline_b, candidate = (runs.get(name, []) for name in ("baseline_a", "baseline_b", "candidate"))
                mismatches = duplicate_mismatches(baseline_a, baseline_b)
                if mismatches and not any("duplicate baseline mismatch" in reason for reason in invalid_reasons):
                    invalid_reasons.append(f"duplicate baseline mismatch in seed={seed_base}, opponent={opponent_name}, seat={seat}")
                cells.append({"seed_base": seed_base, "opponent": opponent_name, "seat": seat,
                              "baseline": baseline_a, "candidate": candidate, "duplicate_mismatches": mismatches})
                if invalid_reasons:
                    break
            if invalid_reasons:
                break
        if invalid_reasons:
            break

    with manifest_path.open("w", encoding="utf-8") as handle:
        for row in manifest:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    paired_rows = []
    for cell in cells:
        for index in range(max(len(cell["baseline"]), len(cell["candidate"]))):
            baseline = cell["baseline"][index] if index < len(cell["baseline"]) else {}
            candidate = cell["candidate"][index] if index < len(cell["candidate"]) else {}
            paired_rows.append({"seed_base": cell["seed_base"], "opponent": cell["opponent"], "seat": cell["seat"], "game": index,
                                "seed": baseline.get("seed", candidate.get("seed", "")), "baseline_result": baseline.get("result", ""),
                                "candidate_result": candidate.get("result", ""), "baseline_win": int(policy_won(baseline, cell["seat"])),
                                "candidate_win": int(policy_won(candidate, cell["seat"])), "baseline_steps": baseline.get("steps", ""),
                                "candidate_steps": candidate.get("steps", "")})
    write_csv(output_dir / "paired_results.csv", paired_rows, list(paired_rows[0]) if paired_rows else ["seed_base", "opponent", "seat", "game", "seed", "baseline_result", "candidate_result", "baseline_win", "candidate_win", "baseline_steps", "candidate_steps"])
    summary = summarize_cells(cells)
    cell_rows = summary["panels"]
    write_csv(output_dir / "cell_summary.csv", cell_rows, ["seed_base", "opponent", "seat", "games", "baseline_wins", "candidate_wins", "delta_wins"])
    report = {"valid": not invalid_reasons, "invalid_reasons": invalid_reasons, "duplicate_mismatch_count": sum(len(cell["duplicate_mismatches"]) for cell in cells), **summary}
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seeded paired local-battle policy evaluation.")
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--opponent", type=parse_opponent, action="append", required=True)
    parser.add_argument("--games-per-seat", type=int, required=True)
    parser.add_argument("--seed-base", type=int, action="append", required=True)
    parser.add_argument("--max-steps", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.games_per_seat <= 0 or args.max_steps <= 0:
        parser.error("--games-per-seat and --max-steps must be positive")
    return args


def main() -> None:
    report = run_suite(parse_args())
    print(json.dumps({"valid": report["valid"], "aggregates": report["aggregates"], "duplicate_mismatch_count": report["duplicate_mismatch_count"]}))
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
