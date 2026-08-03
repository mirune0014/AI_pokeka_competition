#!/usr/bin/env python3
"""Audit public-state opportunities to shelter Cynthia's first Gabite.

The audit reads scored JSONL traces. It does not simulate a counterfactual or
use hidden deck information. A row qualifies when the baseline evolves an
energized Active Gible to Gabite while the same Gabite card can legally evolve
a Benched Gible and Gible already has a legal attack.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


GIBLE = 379
GABITE = 380
GARCHOMP_EX = 381
EVOLVE = 9
ATTACK = 13
ACTIVE_AREA = 4
BENCH_AREA = 5
DISCARD_AREA = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seat0-traces", required=True, type=Path)
    parser.add_argument("--seat1-traces", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    return parser.parse_args()


def selected_score(row: dict) -> dict | None:
    for scored in row.get("scores", []):
        if scored.get("selected"):
            return scored
    return None


def is_gabite_evolution(scored: dict) -> bool:
    option = scored.get("option", {})
    return option.get("type") == EVOLVE and scored.get("reason") == "evolve Gabite"


def selected_card_id(row: dict) -> int | None:
    action = row.get("action") or []
    options = row.get("options") or []
    if not action or action[0] >= len(options):
        return None
    option = options[action[0]]
    if option.get("type") != 3 or option.get("area") != 1:
        return None
    deck_ids = row.get("selection_deck_ids") or []
    index = option.get("index")
    if not isinstance(index, int) or index >= len(deck_ids):
        return None
    return deck_ids[index]


def log_discards_active_gabite(row: dict, seat: int) -> bool:
    return any(
        log.get("type") == 6
        and log.get("playerIndex") == seat
        and log.get("cardId") == GABITE
        and log.get("fromArea") == ACTIVE_AREA
        and log.get("toArea") == DISCARD_AREA
        for log in row.get("logs", [])
    )


def audit_game(path: Path, seat: int) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    findings: list[dict] = []
    prefix = f"p{seat}_"

    for row_index, row in enumerate(rows):
        if row.get("player") != seat:
            continue
        scored = selected_score(row)
        if not scored or not is_gabite_evolution(scored):
            continue
        selected_option = scored.get("option", {})
        if selected_option.get("inPlayArea") != ACTIVE_AREA:
            continue

        snapshot = row.get("snapshot", {})
        active = snapshot.get(prefix + "active")
        active_energy = snapshot.get(prefix + "active_energy") or 0
        bench = snapshot.get(prefix + "bench") or []
        in_play = [active, *bench]
        if (
            active != GIBLE
            or active_energy < 1
            or GIBLE not in bench
            or GABITE in in_play
            or GARCHOMP_EX in in_play
        ):
            continue

        bench_options: list[dict] = []
        for alternative in row.get("scores", []):
            if not is_gabite_evolution(alternative):
                continue
            option = alternative.get("option", {})
            bench_index = option.get("inPlayIndex")
            if (
                option.get("inPlayArea") == BENCH_AREA
                and isinstance(bench_index, int)
                and 0 <= bench_index < len(bench)
                and bench[bench_index] == GIBLE
            ):
                bench_options.append(option)
        if not bench_options:
            continue

        legal_gible_attack = any(
            option.get("type") == ATTACK for option in row.get("options", [])
        )
        if not legal_gible_attack:
            continue

        target_turn = snapshot.get("turn")
        garchomp_secured = GARCHOMP_EX in (row.get("own_hand_ids") or [])
        call_fetched_garchomp = False
        immediate_gabite_ko_score = False
        active_gabite_discarded = False
        next_own_turn_seen = False
        next_own_turn_garchomp_in_hand = False

        for later in rows[row_index + 1 :]:
            later_turn = later.get("snapshot", {}).get("turn")
            if later.get("player") == seat and later_turn != target_turn:
                next_own_turn_seen = True
                next_own_turn_garchomp_in_hand = GARCHOMP_EX in (
                    later.get("own_hand_ids") or []
                )
                break

            if log_discards_active_gabite(later, seat):
                active_gabite_discarded = True

            if later.get("player") != seat or later_turn != target_turn:
                continue
            if GARCHOMP_EX in (later.get("own_hand_ids") or []):
                garchomp_secured = True
            if later.get("effect_card_id") == GABITE and selected_card_id(later) == GARCHOMP_EX:
                call_fetched_garchomp = True
                garchomp_secured = True
            if any(
                score.get("option", {}).get("type") == ATTACK
                and " KO" in score.get("reason", "")
                for score in later.get("scores", [])
            ):
                immediate_gabite_ko_score = True

        garchomp_already_held = GARCHOMP_EX in (row.get("own_hand_ids") or [])
        public_route_secured = garchomp_already_held or call_fetched_garchomp
        result = snapshot.get("result")
        findings.append(
            {
                "seat": seat,
                "game": row.get("game"),
                "trace": str(path),
                "line": row_index + 1,
                "turn": target_turn,
                "result": result,
                "active_energy": active_energy,
                "bench_gible_options": len(bench_options),
                "garchomp_already_held": garchomp_already_held,
                "call_fetched_garchomp": call_fetched_garchomp,
                "garchomp_secured_by_turn_end": garchomp_secured,
                "public_route_secured": public_route_secured,
                "immediate_active_gabite_ko_score": immediate_gabite_ko_score,
                "active_gabite_discarded_before_next_own_turn": active_gabite_discarded,
                "next_own_turn_seen": next_own_turn_seen,
                "garchomp_in_hand_next_own_turn": next_own_turn_garchomp_in_hand,
                "strict_certificate": bool(
                    public_route_secured
                    and active_gabite_discarded
                    and not immediate_gabite_ko_score
                ),
            }
        )
    return findings


def counts(rows: list[dict]) -> dict:
    strict = [row for row in rows if row["strict_certificate"]]
    return {
        "opportunities": len(rows),
        "strict_certificates": len(strict),
        "strict_by_seat": {
            str(seat): sum(row["seat"] == seat for row in strict) for seat in (0, 1)
        },
        "strict_wins": sum(row["result"] == 1 for row in strict),
        "strict_losses": sum(row["result"] == -1 for row in strict),
        "active_gabite_discarded": sum(
            row["active_gabite_discarded_before_next_own_turn"] for row in rows
        ),
        "garchomp_secured": sum(row["garchomp_secured_by_turn_end"] for row in rows),
        "immediate_active_gabite_ko_score": sum(
            row["immediate_active_gabite_ko_score"] for row in rows
        ),
    }


def main() -> None:
    args = parse_args()
    rows: list[dict] = []
    for seat, directory in ((0, args.seat0_traces), (1, args.seat1_traces)):
        for path in sorted(directory.glob("game_*.jsonl")):
            rows.extend(audit_game(path, seat))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.out_dir / "certificates.csv"
    if rows:
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    else:
        csv_path.write_text("", encoding="utf-8")

    summary = counts(rows)
    summary["csv"] = str(csv_path)
    summary_path = args.out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
