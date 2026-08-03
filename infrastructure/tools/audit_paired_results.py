from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recompute paired policy results from raw rows.")
    parser.add_argument("paired_csv", type=Path)
    parser.add_argument("--runner-report", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--block-size", type=int, default=50)
    parser.add_argument("--min-candidate-wins", type=int)
    parser.add_argument("--min-seat-wins", type=int)
    parser.add_argument("--min-delta-wins", type=int)
    parser.add_argument("--max-mcnemar-p", type=float)
    return parser.parse_args()


def exact_mcnemar_p(gains: int, losses: int) -> float:
    discordant = gains + losses
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, value) for value in range(min(gains, losses) + 1))
    return min(1.0, 2.0 * tail / (2**discordant))


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    games = len(rows)
    baseline_wins = sum(row["baseline_win"] for row in rows)
    candidate_wins = sum(row["candidate_win"] for row in rows)
    gains = sum(row["baseline_win"] == 0 and row["candidate_win"] == 1 for row in rows)
    losses = sum(row["baseline_win"] == 1 and row["candidate_win"] == 0 for row in rows)
    return {
        "games": games,
        "baseline_wins": baseline_wins,
        "candidate_wins": candidate_wins,
        "delta_wins": candidate_wins - baseline_wins,
        "baseline_rate": baseline_wins / games if games else None,
        "candidate_rate": candidate_wins / games if games else None,
        "gains": gains,
        "losses": losses,
        "discordant": gains + losses,
        "mcnemar_exact_two_sided_p": exact_mcnemar_p(gains, losses),
    }


def main() -> None:
    args = parse_args()
    with args.paired_csv.open(newline="", encoding="utf-8-sig") as handle:
        raw_rows = list(csv.DictReader(handle))
    rows: list[dict[str, Any]] = []
    keys: set[tuple[int, str, int, int, int]] = set()
    duplicate_keys: list[tuple[int, str, int, int, int]] = []
    for raw in raw_rows:
        row = {
            "seed_base": int(raw["seed_base"]),
            "opponent": raw["opponent"],
            "seat": int(raw["seat"]),
            "game": int(raw["game"]),
            "seed": int(raw["seed"]),
            "baseline_win": int(raw["baseline_win"]),
            "candidate_win": int(raw["candidate_win"]),
        }
        key = (row["seed_base"], row["opponent"], row["seat"], row["game"], row["seed"])
        if key in keys:
            duplicate_keys.append(key)
        keys.add(key)
        rows.append(row)

    by_seat_rows: dict[int, list[dict[str, Any]]] = defaultdict(list)
    by_block_rows: dict[tuple[int, str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_seat_rows[row["seat"]].append(row)
        block = row["game"] // args.block_size
        by_block_rows[(row["seed_base"], row["opponent"], row["seat"], block)].append(row)

    total = summarize(rows)
    by_seat = {str(seat): summarize(group) for seat, group in sorted(by_seat_rows.items())}
    blocks = [
        {
            "seed_base": key[0],
            "opponent": key[1],
            "seat": key[2],
            "block": key[3],
            **summarize(group),
        }
        for key, group in sorted(by_block_rows.items())
    ]
    runner_report = None
    if args.runner_report:
        runner_report = json.loads(args.runner_report.read_text(encoding="utf-8"))

    gates: dict[str, bool] = {
        "unique_schedule_keys": not duplicate_keys,
        "runner_valid": bool(runner_report and runner_report.get("valid"))
        if args.runner_report
        else True,
        "duplicate_controls_exact": runner_report.get("duplicate_mismatch_count") == 0
        if runner_report
        else True,
    }
    if args.min_candidate_wins is not None:
        gates["candidate_absolute"] = total["candidate_wins"] >= args.min_candidate_wins
    if args.min_seat_wins is not None:
        gates["seat_floor"] = all(
            summary["candidate_wins"] >= args.min_seat_wins for summary in by_seat.values()
        )
    if args.min_delta_wins is not None:
        gates["paired_delta"] = total["delta_wins"] >= args.min_delta_wins
    if args.max_mcnemar_p is not None:
        gates["mcnemar"] = total["mcnemar_exact_two_sided_p"] < args.max_mcnemar_p
    gates["block_direction"] = (
        sum(block["delta_wins"] > 0 for block in blocks) >= max(0, len(blocks) - 1)
        and all(block["delta_wins"] >= -1 for block in blocks)
    )

    output = {
        "paired_csv": str(args.paired_csv),
        "rows": len(rows),
        "duplicate_keys": duplicate_keys,
        "total": total,
        "by_seat": by_seat,
        "blocks": blocks,
        "gates": gates,
        "all_gates_pass": all(gates.values()),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"total": total, "gates": gates, "all_gates_pass": output["all_gates_pass"]}))


if __name__ == "__main__":
    main()
