from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


GIBLE = 379
GABITE = 380
GARCHOMP_EX = 381
ROSELIA = 341
ROSERADE = 342

MAIN_LINE = {GIBLE, GABITE, GARCHOMP_EX}
SUPPORT_LINE = {ROSELIA, ROSERADE}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Find public opening decisions where Cynthia chose a redundant main-line "
            "body instead of completing a two-main-plus-support board."
        )
    )
    parser.add_argument("--seat0-traces", type=Path, required=True)
    parser.add_argument("--seat0-summary", type=Path, required=True)
    parser.add_argument("--seat1-traces", type=Path, required=True)
    parser.add_argument("--seat1-summary", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def score_rows(row: dict[str, Any]) -> list[dict[str, Any]]:
    scores = row.get("scores") or []
    return scores if isinstance(scores, list) else [scores]


def selected_scores(row: dict[str, Any]) -> list[dict[str, Any]]:
    selected = {value for value in (row.get("action") or []) if isinstance(value, int)}
    return [score for score in score_rows(row) if score.get("selected") or score.get("index") in selected]


def selected_reasons(row: dict[str, Any]) -> list[str]:
    return [str(score.get("reason") or "") for score in selected_scores(row)]


def available_reasons(row: dict[str, Any]) -> list[str]:
    return [str(score.get("reason") or "") for score in score_rows(row)]


def board_counts(snapshot: dict[str, Any], seat: int) -> dict[str, int]:
    active = snapshot.get(f"p{seat}_active")
    bench = list(snapshot.get(f"p{seat}_bench") or [])
    cards = ([active] if active is not None else []) + bench
    return {
        "board": len(cards),
        "bench": len(bench),
        "main": sum(card in MAIN_LINE for card in cards),
        "gible": sum(card == GIBLE for card in cards),
        "gabite": sum(card == GABITE for card in cards),
        "garchomp": sum(card == GARCHOMP_EX for card in cards),
        "support": sum(card in SUPPORT_LINE for card in cards),
        "roselia": sum(card == ROSELIA for card in cards),
        "roserade": sum(card == ROSERADE for card in cards),
    }


def classify_opportunity(
    row: dict[str, Any],
    seat: int,
    previous_reason: str,
) -> str | None:
    snapshot = row.get("snapshot") or {}
    board = board_counts(snapshot, seat)
    selected = selected_reasons(row)
    available = available_reasons(row)
    context = int(row.get("context") or 0)

    if board["support"] == 0 and context == 5:
        selected_gible = sum(reason == "bench Gible" for reason in selected)
        selected_roselia = sum(reason == "bench Roselia" for reason in selected)
        if (
            selected_gible > 0
            and selected_roselia == 0
            and "bench Roselia" in available
            and board["main"] >= 1
            and board["main"] + selected_gible >= 2
        ):
            return "poffin_redundant_gible_over_roselia"

    if board["support"] == 0 and context == 2:
        if (
            "setup bench Gible" in selected
            and "setup bench Roselia" in available
            and board["main"] >= 2
        ):
            return "setup_redundant_gible_over_roselia"

    if board["support"] == 0 and context == 0:
        if (
            "bench Gible" in selected
            and "bench Roselia" in available
            and board["main"] >= 2
        ):
            return "hand_redundant_gible_over_roselia"

    selected_main_search = any(
        reason.startswith(("take Gible", "take Gabite", "take Garchomp"))
        for reason in selected
    )
    if context == 7 and board["main"] >= 2 and selected_main_search:
        if board["support"] == 0 and any(reason.startswith("take Roselia") for reason in available):
            return f"{previous_reason or 'search'}_main_over_roselia"
        if (
            board["roselia"] > 0
            and board["roserade"] == 0
            and any(reason.startswith("take Roserade") for reason in available)
        ):
            return f"{previous_reason or 'search'}_main_over_roserade"

    return None


def analyze_trace(
    path: Path, seat: int, terminal: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = read_jsonl(path)
    result = int(terminal["result"])
    won = result == seat
    game = int(rows[0]["game"])
    seed = int(terminal["seed"])
    opportunities: list[dict[str, Any]] = []
    previous_reason = ""
    attack_seen = False
    turn3_state: dict[str, int] | None = None

    for row in rows:
        if row.get("player") != seat:
            continue
        snapshot = row.get("snapshot") or {}
        turn = int(snapshot.get("turn") or 0)
        board = board_counts(snapshot, seat)
        if turn == 3 and int(row.get("context") or 0) == 0:
            turn3_state = board

        category = classify_opportunity(row, seat, previous_reason)
        if category is not None:
            opportunities.append(
                {
                    "seat": seat,
                    "game": game,
                    "seed": seed,
                    "won": int(won),
                    "turn": turn,
                    "pre_first_attack": int(not attack_seen),
                    "min_count": int(row.get("min_count") or 0),
                    "max_count": int(row.get("max_count") or 0),
                    "category": category,
                    "source_reason": previous_reason,
                    "selected_reasons": ";".join(selected_reasons(row)),
                    "available_reasons": ";".join(available_reasons(row)),
                    **board,
                    "trace": str(path),
                }
            )

        current_reasons = selected_reasons(row)
        if current_reasons:
            previous_reason = current_reasons[0]
        selected_options = selected_scores(row)
        if any((score.get("option") or {}).get("type") == 13 for score in selected_options):
            attack_seen = True

    turn3_state = turn3_state or {
        "board": 0,
        "bench": 0,
        "main": 0,
        "gible": 0,
        "gabite": 0,
        "garchomp": 0,
        "support": 0,
        "roselia": 0,
        "roserade": 0,
    }
    game_row = {
        "seat": seat,
        "game": game,
        "seed": seed,
        "won": int(won),
        "opportunity_count": len(opportunities),
        "early_opportunity_count": sum(
            event["pre_first_attack"] and event["turn"] <= 3 for event in opportunities
        ),
        **{f"turn3_{key}": value for key, value in turn3_state.items()},
        "trace": str(path),
    }
    return opportunities, game_row


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def rate(wins: int, games: int) -> str:
    return "n/a" if games == 0 else f"{wins / games:.2%}"


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    events: list[dict[str, Any]] = []
    games: list[dict[str, Any]] = []
    inputs = (
        (0, args.seat0_traces, args.seat0_summary),
        (1, args.seat1_traces, args.seat1_summary),
    )
    for seat, directory, summary_path in inputs:
        terminals = {int(row["game"]): row for row in read_jsonl(summary_path)}
        for path in sorted(directory.glob("game_*.jsonl")):
            game = int(path.stem.split("_")[-1])
            trace_events, game_row = analyze_trace(path, seat, terminals[game])
            events.extend(trace_events)
            games.append(game_row)

    write_csv(args.out_dir / "opportunities.csv", events)
    write_csv(args.out_dir / "games.csv", games)

    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_category[event["category"]].append(event)
    affected = {int(row["seat"]) * 1_000_000 + int(row["game"]) for row in events}
    early_affected = {
        int(row["seat"]) * 1_000_000 + int(row["game"])
        for row in events
        if row["pre_first_attack"] and row["turn"] <= 3
    }
    game_by_key = {
        int(row["seat"]) * 1_000_000 + int(row["game"]): row for row in games
    }

    lines = [
        "# Cynthia opening-route opportunities",
        "",
        f"- games: {len(games)}",
        f"- total events: {len(events)}",
        f"- affected games: {len(affected)}",
        f"- affected before first attack by turn 3: {len(early_affected)}",
        "",
        "## Event categories",
        "",
        "| category | events | games | wins | game win rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for category, rows in sorted(by_category.items()):
        keys = {int(row["seat"]) * 1_000_000 + int(row["game"]) for row in rows}
        wins = sum(int(game_by_key[key]["won"]) for key in keys)
        lines.append(f"| {category} | {len(rows)} | {len(keys)} | {wins} | {rate(wins, len(keys))} |")

    lines.extend(
        [
            "",
            "## Route outcome",
            "",
            "| group | games | wins | win rate | turn-3 Roserade | turn-3 2 main + support |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    groups = {
        "early missed opportunity": [game_by_key[key] for key in early_affected],
        "no early missed opportunity": [
            row
            for key, row in game_by_key.items()
            if key not in early_affected
        ],
        "all": games,
    }
    for name, rows in groups.items():
        wins = sum(int(row["won"]) for row in rows)
        roserade = sum(int(row["turn3_roserade"]) > 0 for row in rows)
        complete = sum(
            int(row["turn3_main"]) >= 2 and int(row["turn3_support"]) >= 1
            for row in rows
        )
        lines.append(
            f"| {name} | {len(rows)} | {wins} | {rate(wins, len(rows))} | "
            f"{roserade} | {complete} |"
        )

    (args.out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
