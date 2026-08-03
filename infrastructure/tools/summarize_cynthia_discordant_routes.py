from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from analyze_cynthia_arch_structure import analyze_game


FIELDS = (
    "won",
    "turns",
    "own_prizes_left",
    "opponent_prizes_left",
    "prizes_taken",
    "board_out_loss",
    "attack_count",
    "attack_sequence",
    "first_attack_turn",
    "first_attack_name",
    "first_attack_board",
    "first_attack_garchomp",
    "first_attack_roselia",
    "first_attack_roserade",
    "first_attack_backup_energy1",
    "buster_count",
    "first_buster_turn",
    "first_buster_ko",
    "first_buster_board",
    "first_buster_backup_energy1",
    "post_buster_attack",
    "max_board",
    "max_garchomp",
    "max_roserade",
    "own_turn2_board",
    "own_turn2_garchomp",
    "own_turn2_roserade",
    "own_turn3_board",
    "own_turn3_garchomp",
    "own_turn3_roserade",
    "own_turn3_backup_garchomp_energy1",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Root-recompute paired Cynthia route metrics for discordant traces."
    )
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def read_terminal(trace: Path) -> dict[str, Any]:
    summary = Path(str(trace.parent) + ".jsonl")
    with summary.open(encoding="utf-8") as handle:
        return json.loads(next(line for line in handle if line.strip()))


def read_trace_rows(trace: Path) -> list[dict[str, Any]]:
    with trace.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def divergence_state(trace: Path, step: int, seat: int) -> dict[str, Any]:
    rows = read_trace_rows(trace)
    row = next(row for row in rows if int(row.get("step") or -1) == step)
    snapshot = row.get("snapshot") or {}
    own = f"p{seat}_"
    opponent = f"p{1 - seat}_"
    return {
        "divergence_turn": int(snapshot.get("turn") or 0),
        "divergence_own_active": snapshot.get(own + "active"),
        "divergence_own_active_energy": snapshot.get(own + "active_energy"),
        "divergence_own_bench": ";".join(str(value) for value in snapshot.get(own + "bench") or []),
        "divergence_own_bench_energy": ";".join(str(value) for value in snapshot.get(own + "bench_energy") or []),
        "divergence_own_hand": snapshot.get(own + "hand"),
        "divergence_own_deck": snapshot.get(own + "deck"),
        "divergence_own_prizes": snapshot.get(own + "prizes"),
        "divergence_opponent_active": snapshot.get(opponent + "active"),
        "divergence_opponent_active_energy": snapshot.get(opponent + "active_energy"),
        "divergence_opponent_bench": ";".join(str(value) for value in snapshot.get(opponent + "bench") or []),
        "divergence_opponent_bench_energy": ";".join(str(value) for value in snapshot.get(opponent + "bench_energy") or []),
        "divergence_opponent_deck": snapshot.get(opponent + "deck"),
        "divergence_opponent_prizes": snapshot.get(opponent + "prizes"),
        "divergence_available_reasons": ";".join(
            str(score.get("reason") or "") for score in row.get("scores") or []
        ),
    }


def main() -> None:
    args = parse_args()
    with args.pairs.open(newline="", encoding="utf-8-sig") as handle:
        pairs = list(csv.DictReader(handle))
    output: list[dict[str, Any]] = []
    for pair in pairs:
        seat = int(pair["seat"])
        before_trace = Path(pair["baseline_trace"])
        after_trace = Path(pair["candidate_trace"])
        before = analyze_game(before_trace, read_terminal(before_trace), {}, seat)
        after = analyze_game(after_trace, read_terminal(after_trace), {}, seat)
        row: dict[str, Any] = {
            "seed": int(pair["seed"]),
            "seat": seat,
            "flip": pair["flip"],
            "stadium_id": pair.get("stadium_id"),
            **divergence_state(before_trace, int(pair["first_step"]), seat),
        }
        for field in FIELDS:
            row[f"baseline_{field}"] = before.get(field)
            row[f"candidate_{field}"] = after.get(field)
        output.append(row)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    print(json.dumps({"pairs": len(output), "out": str(args.out)}))


if __name__ == "__main__":
    main()
