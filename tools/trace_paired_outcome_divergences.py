#!/usr/bin/env python3
"""Replay baseline/candidate outcome flips with scored local traces."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run_local_battle.py"


def battle_command(args, policy: Path, seat: int, seed: int, summary: Path, trace_dir: Path) -> list[str]:
    if seat == 0:
        agent_a, agent_b = policy, args.opponent
    else:
        agent_a, agent_b = args.opponent, policy
    return [
        sys.executable,
        str(RUNNER),
        "--engine-dir", str(args.engine),
        "--agent-a", str(agent_a),
        "--deck-a", str(agent_a / "deck.csv"),
        "--agent-b", str(agent_b),
        "--deck-b", str(agent_b / "deck.csv"),
        "--games", "1",
        "--max-steps", str(args.max_steps),
        "--seed-base", str(seed),
        "--engine-seed",
        "--summary", str(summary),
        "--trace-dir", str(trace_dir),
        "--trace-scores",
        "--trace-score-limit", "30",
        "--trace-options",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--opponent", type=Path, required=True)
    parser.add_argument("--paired", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-steps", type=int, default=1000)
    args = parser.parse_args()

    with args.paired.open(encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["baseline_win"] != row["candidate_win"]]

    args.out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for row in rows:
        seat = int(row["seat"])
        seed = int(row["seed"])
        for role, policy in (("baseline", args.baseline), ("candidate", args.candidate)):
            stem = f"seed_{seed}_p{seat}_{role}"
            summary = args.out / f"{stem}.jsonl"
            trace_dir = args.out / stem
            command = battle_command(args, policy, seat, seed, summary, trace_dir)
            completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            (args.out / f"{stem}.stdout.txt").write_text(completed.stdout, encoding="utf-8")
            (args.out / f"{stem}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
            manifest.append({
                "seed": seed,
                "seat": seat,
                "role": role,
                "expected_win": int(row[f"{role}_win"]),
                "exit_code": completed.returncode,
                "summary": str(summary),
                "trace_dir": str(trace_dir),
                "command": command,
            })
            if completed.returncode:
                raise RuntimeError(f"{stem} failed with exit {completed.returncode}")

    manifest_path = args.out / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as handle:
        for row in manifest:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    print(json.dumps({"flipped_games": len(rows), "runs": len(manifest), "manifest": str(manifest_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
