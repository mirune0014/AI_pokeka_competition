#!/usr/bin/env python3
"""Audit Cynthia's selected damage claims against local trace outcomes."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


CORKSCREW_DIVE = 531
DRACONIC_BUSTER = 532
ATTACK_BASE_DAMAGE = {CORKSCREW_DIVE: 100, DRACONIC_BUSTER: 260}
ATTACK_NAMES = {CORKSCREW_DIVE: "Corkscrew Dive", DRACONIC_BUSTER: "Draconic Buster"}
ROSERADE = 342
KNOWN_STADIUMS = {1244, 1261}  # Full Metal Lab, Forest of Vitality


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def selected_attack_ko(row: dict) -> dict | None:
    for score in row.get("scores", []):
        attack_id = score.get("option", {}).get("attackId")
        if (
            score.get("selected")
            and attack_id in ATTACK_BASE_DAMAGE
            and "KO" in score.get("reason", "")
        ):
            return score
    return None


def actual_damage(rows: list[dict], index: int, attacker: int, attack_id: int) -> int | None:
    target = 1 - attacker
    for future in rows[index + 1 : index + 5]:
        logs = future.get("logs", [])
        used_buster = any(
            log.get("type") == 15
            and log.get("playerIndex") == attacker
            and log.get("attackId") == attack_id
            for log in logs
        )
        if not used_buster:
            continue
        for log in logs:
            if log.get("type") == 16 and log.get("playerIndex") == target:
                return abs(int(log.get("value", 0) or 0))
    return None


def stadium_before(rows: list[dict], index: int) -> int | None:
    stadium = None
    for row in rows[: index + 1]:
        for log in row.get("logs", []):
            card_id = log.get("cardId")
            if log.get("type") == 10 and card_id in KNOWN_STADIUMS:
                stadium = card_id
    return stadium


def game_result(path: Path, game: int | None, rows: list[dict]) -> int | None:
    trace_result = rows[-1].get("snapshot", {}).get("result")
    if trace_result in {0, 1}:
        return int(trace_result)
    summary_path = path.parent.parent / f"{path.parent.name}_games.csv"
    if not summary_path.exists() or game is None:
        return None
    with summary_path.open(encoding="utf-8", newline="") as handle:
        for summary in csv.DictReader(handle):
            if int(summary["game"]) == int(game):
                result = int(summary["result"])
                return result if result in {0, 1} else None
    return None


def audit_trace(path: Path) -> list[dict]:
    rows = load_rows(path)
    if not rows:
        return []
    records = []
    for index, row in enumerate(rows):
        selected = selected_attack_ko(row)
        if selected is None:
            continue
        attack_id = int(selected["option"]["attackId"])
        player = int(row["player"])
        snapshot = row["snapshot"]
        own_prefix = f"p{player}"
        target_prefix = f"p{1 - player}"
        own_cards = [snapshot.get(f"{own_prefix}_active")]
        own_cards.extend(snapshot.get(f"{own_prefix}_bench", []))
        target_hp = snapshot.get(f"{target_prefix}_active_hp")
        observed_damage = actual_damage(rows, index, player, attack_id)
        predicted_damage = ATTACK_BASE_DAMAGE[attack_id] + 30 * own_cards.count(ROSERADE)
        winner = game_result(path, row.get("game"), rows)
        records.append(
            {
                "trace": str(path),
                "game": row.get("game"),
                "step": row.get("step"),
                "turn": snapshot.get("turn"),
                "player": player,
                "attack_id": attack_id,
                "attack_name": ATTACK_NAMES[attack_id],
                "target_id": snapshot.get(f"{target_prefix}_active"),
                "target_hp": target_hp,
                "roserades": own_cards.count(ROSERADE),
                "stadium_id": stadium_before(rows, index),
                "predicted_damage": predicted_damage,
                "actual_damage": observed_damage,
                "false_ko": bool(
                    target_hp is not None
                    and observed_damage is not None
                    and observed_damage < target_hp
                ),
                "winner": winner,
                "cynthia_win": winner == player if winner is not None else None,
                "reason": selected.get("reason"),
            }
        )
    return records


def trace_files(inputs: list[Path]) -> list[Path]:
    found = []
    for path in inputs:
        if path.is_file():
            found.append(path)
        else:
            found.extend(path.rglob("*.jsonl"))
    return sorted(set(found))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    records = []
    for path in trace_files(args.paths):
        records.extend(audit_trace(path))

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(records[0]) if records else [])
            if records:
                writer.writeheader()
                writer.writerows(records)

    false_kos = [record for record in records if record["false_ko"]]
    false_busters = [record for record in false_kos if record["attack_id"] == DRACONIC_BUSTER]
    false_corkscrews = [record for record in false_kos if record["attack_id"] == CORKSCREW_DIVE]
    print(
        json.dumps(
            {
                "trace_files": len(trace_files(args.paths)),
                "selected_attack_ko": len(records),
                "selected_buster_ko": sum(record["attack_id"] == DRACONIC_BUSTER for record in records),
                "selected_corkscrew_ko": sum(record["attack_id"] == CORKSCREW_DIVE for record in records),
                "false_ko": len(false_kos),
                "false_buster_ko": len(false_busters),
                "false_corkscrew_ko": len(false_corkscrews),
                "false_ko_cynthia_wins": sum(record["cynthia_win"] is True for record in false_kos),
                "false_ko_unknown_results": sum(record["cynthia_win"] is None for record in false_kos),
                "false_ko_rows": false_kos,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
