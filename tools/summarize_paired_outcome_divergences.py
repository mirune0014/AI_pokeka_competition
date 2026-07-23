#!/usr/bin/env python3
"""Summarize verified outcomes and first actions for replayed paired flips."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from compare_local_trace_first_divergences import summarize_pair


def read_summary(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != 1:
        raise ValueError(f"expected one summary row in {path}, got {len(rows)}")
    return rows[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    manifest_path = args.root / "manifest.jsonl"
    manifest = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line]
    grouped: dict[tuple[int, int], dict[str, dict]] = defaultdict(dict)
    for row in manifest:
        grouped[(int(row["seed"]), int(row["seat"]))][row["role"]] = row

    output = []
    for (seed, seat), roles in sorted(grouped.items()):
        if set(roles) != {"baseline", "candidate"}:
            raise ValueError(f"missing role for seed={seed} seat={seat}: {sorted(roles)}")
        summaries = {role: read_summary(Path(row["summary"])) for role, row in roles.items()}
        actual_wins = {role: int(summary.get("result") == seat) for role, summary in summaries.items()}
        expected_wins = {role: int(row["expected_win"]) for role, row in roles.items()}
        if actual_wins != expected_wins:
            raise ValueError(
                f"outcome mismatch seed={seed} seat={seat}: actual={actual_wins} expected={expected_wins}"
            )

        baseline_trace = Path(roles["baseline"]["trace_dir"]) / "game_0000.jsonl"
        candidate_trace = Path(roles["candidate"]["trace_dir"]) / "game_0000.jsonl"
        first = summarize_pair(baseline_trace, candidate_trace, seat)
        baseline_final = summaries["baseline"]
        candidate_final = summaries["candidate"]
        output.append({
            "seed": seed,
            "seat": seat,
            "flip": "gain" if actual_wins["candidate"] else "loss",
            "baseline_win": actual_wins["baseline"],
            "candidate_win": actual_wins["candidate"],
            "first_step": first["step"],
            "first_player": first["player"],
            "stadium_id": first["stadium_id"],
            "target_id": first["target_id"],
            "target_hp": first["target_hp"],
            "baseline_action": first["baseline_action"],
            "candidate_action": first["candidate_action"],
            "baseline_reason": first["baseline_reason"],
            "candidate_reason": first["candidate_reason"],
            "baseline_option": first["baseline_option"],
            "candidate_option": first["candidate_option"],
            "baseline_steps": baseline_final.get("steps"),
            "candidate_steps": candidate_final.get("steps"),
            "baseline_final_prizes": baseline_final.get(f"p{seat}_prizes"),
            "candidate_final_prizes": candidate_final.get(f"p{seat}_prizes"),
            "baseline_trace": str(baseline_trace),
            "candidate_trace": str(candidate_trace),
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    print(json.dumps({
        "games": len(output),
        "gains": sum(row["flip"] == "gain" for row in output),
        "losses": sum(row["flip"] == "loss" for row in output),
        "output": str(args.out),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
