from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable


GIBLE = 379
GABITE = 380
GARCHOMP = 381
ROSELIA = 341
ROSERADE = 342

ATTACK_NAMES = {
    529: "Rock Hurl",
    530: "Dragonslice",
    531: "Corkscrew Dive",
    532: "Draconic Buster",
    540: "Raging Curse",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Cynthia board formation in wins and losses versus Archaludon."
    )
    parser.add_argument("--seat0-traces", type=Path, required=True)
    parser.add_argument("--seat0-summary", type=Path, required=True)
    parser.add_argument("--seat0-games", type=Path, required=True)
    parser.add_argument("--seat1-traces", type=Path, required=True)
    parser.add_argument("--seat1-summary", type=Path, required=True)
    parser.add_argument("--seat1-games", type=Path, required=True)
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


def read_csv_by_game(path: Path) -> dict[int, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {int(row["game"]): row for row in csv.DictReader(handle)}


def selected_option(row: dict[str, Any]) -> dict[str, Any] | None:
    action = row.get("action") or []
    options = row.get("options") or []
    if len(action) != 1:
        return None
    index = action[0]
    if not isinstance(index, int) or not 0 <= index < len(options):
        return None
    option = options[index]
    return option if isinstance(option, dict) else None


def board_state(snapshot: dict[str, Any], seat: int) -> dict[str, int]:
    active = snapshot.get(f"p{seat}_active")
    bench = list(snapshot.get(f"p{seat}_bench") or [])
    bench_energy = list(snapshot.get(f"p{seat}_bench_energy") or [])
    active_energy = int(snapshot.get(f"p{seat}_active_energy") or 0)
    all_cards = ([active] if active is not None else []) + bench

    def count(card_id: int) -> int:
        return sum(card == card_id for card in all_cards)

    bench_garchomp_energies = [
        int(bench_energy[index] or 0)
        for index, card in enumerate(bench)
        if card == GARCHOMP and index < len(bench_energy)
    ]
    return {
        "board": len(all_cards),
        "gible": count(GIBLE),
        "gabite": count(GABITE),
        "garchomp": count(GARCHOMP),
        "roselia": count(ROSELIA),
        "roserade": count(ROSERADE),
        "active_garchomp": int(active == GARCHOMP),
        "active_energy": active_energy,
        "bench_garchomp": len(bench_garchomp_energies),
        "backup_garchomp_energy1": sum(value >= 1 for value in bench_garchomp_energies),
        "backup_garchomp_energy2": sum(value >= 2 for value in bench_garchomp_energies),
    }


def prizes_gained_after_attack(
    rows: list[dict[str, Any]],
    start: int,
    seat: int,
    own_prizes: int,
    terminal_prizes: int,
) -> int:
    observed = [own_prizes]
    reached_next_attack = False
    for row in rows[start + 1 :]:
        snapshot = row.get("snapshot")
        if isinstance(snapshot, dict):
            observed.append(int(snapshot.get(f"p{seat}_prizes") or 0))
        option = selected_option(row)
        if row.get("player") == seat and option and option.get("type") == 13:
            reached_next_attack = True
            break
    if not reached_next_attack:
        observed.append(terminal_prizes)
    return own_prizes - min(observed)


def as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def analyze_game(
    trace_path: Path,
    terminal: dict[str, Any],
    trace_summary: dict[str, str],
    seat: int,
) -> dict[str, Any]:
    rows = read_jsonl(trace_path)
    game = int(terminal["game"])
    result = int(terminal["result"])
    won = result == seat
    terminal_prizes = int(terminal.get(f"p{seat}_prizes") or 0)
    attacks: list[dict[str, Any]] = []
    max_state = Counter()
    end_state_by_turn: dict[int, dict[str, int]] = {}

    for index, row in enumerate(rows):
        snapshot = row.get("snapshot")
        if isinstance(snapshot, dict):
            state = board_state(snapshot, seat)
            for key in ("board", "gible", "gabite", "garchomp", "roselia", "roserade"):
                max_state[key] = max(max_state[key], state[key])
            if row.get("player") == seat and row.get("context") == 0:
                turn = int(snapshot.get("turn") or 0)
                if turn > 0:
                    end_state_by_turn[turn] = {
                        **state,
                        "prizes": int(snapshot.get(f"p{seat}_prizes") or 0),
                    }

        if row.get("player") != seat:
            continue
        option = selected_option(row)
        if not option or option.get("type") != 13:
            continue
        snapshot = row.get("snapshot") or {}
        attack_id = int(option.get("attackId"))
        state = board_state(snapshot, seat)
        own_prizes = int(snapshot.get(f"p{seat}_prizes") or 0)
        opponent_prizes = int(snapshot.get(f"p{1 - seat}_prizes") or 0)
        alternatives = [
            score_row
            for score_row in (row.get("scores") or [])
            if not score_row.get("selected")
            and float(score_row.get("score") or 0) > 0
            and (score_row.get("option") or {}).get("type") not in {12, 13, 14}
        ]
        alternatives.sort(key=lambda score_row: float(score_row.get("score") or 0), reverse=True)
        call_available = any(
            score_row.get("reason") == "Champion's Call" for score_row in alternatives
        )
        prizes_gained = prizes_gained_after_attack(
            rows, index, seat, own_prizes, terminal_prizes
        )
        attacks.append(
            {
                "turn": int(snapshot.get("turn") or 0),
                "attack_id": attack_id,
                "attack_name": ATTACK_NAMES.get(attack_id, str(attack_id)),
                "own_prizes": own_prizes,
                "opponent_prizes": opponent_prizes,
                "opponent_active": snapshot.get(f"p{1 - seat}_active"),
                "opponent_active_hp": snapshot.get(f"p{1 - seat}_active_hp"),
                "prizes_gained": prizes_gained,
                "prize_gain": prizes_gained > 0,
                "best_nonattack_score": alternatives[0].get("score") if alternatives else None,
                "best_nonattack_reason": alternatives[0].get("reason") if alternatives else None,
                "nonattack_reasons": ";".join(
                    str(score_row.get("reason") or "") for score_row in alternatives
                ),
                "call_available": call_available,
                "deck_count": int(snapshot.get(f"p{seat}_deck") or 0),
                **state,
            }
        )

    first = attacks[0] if attacks else {}
    busters = [attack for attack in attacks if attack["attack_id"] == 532]
    corkscrews = [attack for attack in attacks if attack["attack_id"] == 531]
    first_buster = busters[0] if busters else {}
    attack_turns = [attack["turn"] for attack in attacks]
    post_buster_attack = False
    if first_buster:
        post_buster_attack = any(
            attack["turn"] > first_buster["turn"] for attack in attacks
        )

    own_prizes_left = int(terminal.get(f"p{seat}_prizes") or 0)
    opponent_prizes_left = int(terminal.get(f"p{1 - seat}_prizes") or 0)
    own_active = terminal.get(f"p{seat}_active")
    own_bench = terminal.get(f"p{seat}_bench") or []
    board_out_loss = not won and own_active is None and not own_bench
    own_turn_states = [end_state_by_turn[turn] for turn in sorted(end_state_by_turn)]

    prefix = f"p{seat}_"
    output = {
        "seat": seat,
        "game": game,
        "seed": int(terminal["seed"]),
        "won": int(won),
        "result": result,
        "turns": int(terminal.get("turn") or 0),
        "own_prizes_left": own_prizes_left,
        "opponent_prizes_left": opponent_prizes_left,
        "prizes_taken": 6 - own_prizes_left,
        "board_out_loss": int(board_out_loss),
        "attack_count": len(attacks),
        "attack_turns": ";".join(str(value) for value in attack_turns),
        "attack_sequence": ";".join(attack["attack_name"] for attack in attacks),
        "first_attack_turn": first.get("turn"),
        "first_attack_name": first.get("attack_name"),
        "first_attack_board": first.get("board"),
        "first_attack_gible": first.get("gible"),
        "first_attack_gabite": first.get("gabite"),
        "first_attack_garchomp": first.get("garchomp"),
        "first_attack_roselia": first.get("roselia"),
        "first_attack_roserade": first.get("roserade"),
        "first_attack_bench_garchomp": first.get("bench_garchomp"),
        "first_attack_backup_energy1": first.get("backup_garchomp_energy1"),
        "first_attack_backup_energy2": first.get("backup_garchomp_energy2"),
        "first_attack_prize_gain": int(bool(first.get("prize_gain"))),
        "first_attack_best_nonattack_score": first.get("best_nonattack_score"),
        "first_attack_best_nonattack_reason": first.get("best_nonattack_reason"),
        "first_attack_nonattack_reasons": first.get("nonattack_reasons"),
        "first_attack_call_available": int(bool(first.get("call_available"))),
        "attack_with_call_available_count": sum(
            attack["call_available"] for attack in attacks
        ),
        "game_winning_attack_over_call_count": sum(
            attack["call_available"]
            and attack["prizes_gained"] >= attack["own_prizes"]
            for attack in attacks
        ),
        "min_deck_when_attacking_over_call": min(
            (attack["deck_count"] for attack in attacks if attack["call_available"]),
            default=None,
        ),
        "corkscrew_count": len(corkscrews),
        "buster_count": len(busters),
        "buster_ko_count": sum(attack["prize_gain"] for attack in busters),
        "buster_noko_count": sum(not attack["prize_gain"] for attack in busters),
        "first_buster_turn": first_buster.get("turn"),
        "first_buster_ko": int(bool(first_buster.get("prize_gain"))),
        "first_buster_board": first_buster.get("board"),
        "first_buster_bench_garchomp": first_buster.get("bench_garchomp"),
        "first_buster_backup_energy1": first_buster.get("backup_garchomp_energy1"),
        "first_buster_backup_energy2": first_buster.get("backup_garchomp_energy2"),
        "post_buster_attack": int(post_buster_attack),
        "max_board": max_state["board"],
        "max_garchomp": max_state["garchomp"],
        "max_roserade": max_state["roserade"],
        "summary_first_prize_turn": as_int(trace_summary.get(prefix + "first_prize_turn")),
        "summary_first_prize_line_count": as_int(
            trace_summary.get(prefix + "first_prize_line_count")
        ),
        "summary_min_line_after_first_prize": as_int(
            trace_summary.get(prefix + "min_line_after_first_prize")
        ),
        "summary_missed_attacks_after_first": as_int(
            trace_summary.get(prefix + "missed_attack_turns_after_first")
        ),
        "summary_max_missed_attack_streak": as_int(
            trace_summary.get(prefix + "max_missed_attack_streak")
        ),
    }
    for own_turn in range(1, 5):
        state = own_turn_states[own_turn - 1] if len(own_turn_states) >= own_turn else {}
        for key in (
            "board",
            "gible",
            "gabite",
            "garchomp",
            "roselia",
            "roserade",
            "bench_garchomp",
            "backup_garchomp_energy1",
            "backup_garchomp_energy2",
            "prizes",
        ):
            output[f"own_turn{own_turn}_{key}"] = state.get(key)
    return output


def numeric_summary(rows: list[dict[str, Any]], key: str) -> str:
    values = [float(row[key]) for row in rows if row.get(key) not in (None, "")]
    if not values:
        return "n/a"
    return f"mean={mean(values):.2f}, median={median(values):.2f}, n={len(values)}"


def condition_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conditions = {
        "all": lambda row: True,
        "first attack is Garchomp": lambda row: row.get("first_attack_name")
        in {"Corkscrew Dive", "Draconic Buster"},
        "first attack by turn 5": lambda row: row.get("first_attack_turn") is not None
        and row["first_attack_turn"] <= 5,
        "Garchomp present at first attack": lambda row: (row.get("first_attack_garchomp") or 0)
        >= 1,
        "Roserade present at first attack": lambda row: (row.get("first_attack_roserade") or 0)
        >= 1,
        "two Garchomp at first attack": lambda row: (row.get("first_attack_garchomp") or 0)
        >= 2,
        "energy-bearing backup at first attack": lambda row: (
            row.get("first_attack_backup_energy1") or 0
        )
        >= 1,
        "first attack takes prize": lambda row: row.get("first_attack_prize_gain") == 1,
        "first attack leaves Champion's Call unused": lambda row: row.get(
            "first_attack_call_available"
        )
        == 1,
        "any attack leaves Champion's Call unused": lambda row: row.get(
            "attack_with_call_available_count", 0
        )
        >= 1,
        "game-winning attack correctly skips Call": lambda row: row.get(
            "game_winning_attack_over_call_count", 0
        )
        >= 1,
        "uses Buster": lambda row: row.get("buster_count", 0) >= 1,
        "first Buster takes prize": lambda row: row.get("first_buster_ko") == 1,
        "Buster with energy-bearing backup": lambda row: row.get("buster_count", 0) >= 1
        and (row.get("first_buster_backup_energy1") or 0) >= 1,
        "Buster without energy-bearing backup": lambda row: row.get("buster_count", 0) >= 1
        and (row.get("first_buster_backup_energy1") or 0) == 0,
        "attacks after first Buster": lambda row: row.get("post_buster_attack") == 1,
        "takes at least one prize": lambda row: row.get("prizes_taken", 0) >= 1,
        "takes at least four prizes": lambda row: row.get("prizes_taken", 0) >= 4,
        "max board at least five": lambda row: row.get("max_board", 0) >= 5,
        "max two Garchomp": lambda row: row.get("max_garchomp", 0) >= 2,
        "max one Roserade": lambda row: row.get("max_roserade", 0) >= 1,
        "Garchomp by own turn 2": lambda row: (row.get("own_turn2_garchomp") or 0)
        >= 1,
        "Garchomp by own turn 3": lambda row: (row.get("own_turn3_garchomp") or 0)
        >= 1,
        "Roserade by own turn 2": lambda row: (row.get("own_turn2_roserade") or 0)
        >= 1,
        "Roserade by own turn 3": lambda row: (row.get("own_turn3_roserade") or 0)
        >= 1,
        "Garchomp and Roserade by own turn 3": lambda row: (
            (row.get("own_turn3_garchomp") or 0) >= 1
            and (row.get("own_turn3_roserade") or 0) >= 1
        ),
        "two Garchomp by own turn 3": lambda row: (row.get("own_turn3_garchomp") or 0)
        >= 2,
        "energy backup by own turn 3": lambda row: (
            row.get("own_turn3_backup_garchomp_energy1") or 0
        )
        >= 1,
        "Garchomp Roserade and backup by own turn 3": lambda row: (
            (row.get("own_turn3_garchomp") or 0) >= 1
            and (row.get("own_turn3_roserade") or 0) >= 1
            and (row.get("own_turn3_backup_garchomp_energy1") or 0) >= 1
        ),
        "Garchomp without Roserade on own turn 3": lambda row: (
            (row.get("own_turn3_garchomp") or 0) >= 1
            and (row.get("own_turn3_roserade") or 0) == 0
        ),
        "no Garchomp on own turn 3": lambda row: (row.get("own_turn3_garchomp") or 0)
        == 0,
        "first attack is basic line": lambda row: row.get("first_attack_name")
        in {"Rock Hurl", "Dragonslice"},
        "first Garchomp attack with Roserade": lambda row: row.get("first_attack_name")
        in {"Corkscrew Dive", "Draconic Buster"}
        and (row.get("first_attack_roserade") or 0) >= 1,
        "first Garchomp attack without Roserade": lambda row: row.get("first_attack_name")
        in {"Corkscrew Dive", "Draconic Buster"}
        and (row.get("first_attack_roserade") or 0) == 0,
    }
    output: list[dict[str, Any]] = []
    for label, predicate in conditions.items():
        selected = [row for row in rows if predicate(row)]
        wins = sum(row["won"] for row in selected)
        output.append(
            {
                "condition": label,
                "games": len(selected),
                "wins": wins,
                "win_rate": wins / len(selected) if selected else None,
                "coverage": len(selected) / len(rows) if rows else None,
            }
        )
    return output


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    all_rows: list[dict[str, Any]] = []
    for seat, trace_dir, terminal_path, games_path in (
        (0, args.seat0_traces, args.seat0_summary, args.seat0_games),
        (1, args.seat1_traces, args.seat1_summary, args.seat1_games),
    ):
        terminal_by_game = {int(row["game"]): row for row in read_jsonl(terminal_path)}
        summaries = read_csv_by_game(games_path)
        for trace_path in sorted(trace_dir.glob("game_*.jsonl")):
            game = int(trace_path.stem.split("_")[-1])
            all_rows.append(
                analyze_game(trace_path, terminal_by_game[game], summaries[game], seat)
            )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir / "games.csv", all_rows)
    conditions = condition_rows(all_rows)
    write_csv(args.out_dir / "condition_win_rates.csv", conditions)

    wins = [row for row in all_rows if row["won"]]
    losses = [row for row in all_rows if not row["won"]]
    metric_keys = (
        "first_attack_turn",
        "first_attack_board",
        "first_attack_garchomp",
        "first_attack_roserade",
        "first_attack_backup_energy1",
        "attack_count",
        "corkscrew_count",
        "buster_count",
        "buster_ko_count",
        "buster_noko_count",
        "first_buster_turn",
        "first_buster_board",
        "first_buster_backup_energy1",
        "prizes_taken",
        "max_board",
        "max_garchomp",
        "max_roserade",
        "summary_missed_attacks_after_first",
        "attack_with_call_available_count",
        "game_winning_attack_over_call_count",
        "min_deck_when_attacking_over_call",
        "own_turn2_board",
        "own_turn2_garchomp",
        "own_turn2_roserade",
        "own_turn3_board",
        "own_turn3_garchomp",
        "own_turn3_roserade",
        "own_turn3_backup_garchomp_energy1",
        "own_turn4_board",
        "own_turn4_garchomp",
        "own_turn4_roserade",
        "own_turn4_backup_garchomp_energy1",
    )
    attack_win = Counter(row["first_attack_name"] or "none" for row in wins)
    attack_loss = Counter(row["first_attack_name"] or "none" for row in losses)

    seat_rows = {
        seat: [row for row in all_rows if row["seat"] == seat]
        for seat in (0, 1)
    }
    lines = [
        "# Cynthia versus historical Silver Archaludon: structural diagnosis",
        "",
        f"- games: {len(all_rows)}",
        f"- wins: {len(wins)} ({len(wins) / len(all_rows):.2%})",
        f"- seat 0: {sum(row['won'] for row in seat_rows[0])}/{len(seat_rows[0])}",
        f"- seat 1: {sum(row['won'] for row in seat_rows[1])}/{len(seat_rows[1])}",
        f"- board-out losses: {sum(row['board_out_loss'] for row in losses)}/{len(losses)}",
        "",
        "## Win/loss metric contrast",
        "",
        "| metric | wins | losses |",
        "|---|---:|---:|",
    ]
    for key in metric_keys:
        lines.append(f"| {key} | {numeric_summary(wins, key)} | {numeric_summary(losses, key)} |")
    lines.extend(
        [
            "",
            "## First attack distribution",
            "",
            f"- wins: {dict(attack_win)}",
            f"- losses: {dict(attack_loss)}",
            "",
            "## Conditional win rates",
            "",
            "| condition | games | wins | win rate | coverage |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in conditions:
        win_rate = "n/a" if row["win_rate"] is None else f"{row['win_rate']:.2%}"
        coverage = "n/a" if row["coverage"] is None else f"{row['coverage']:.2%}"
        lines.append(
            f"| {row['condition']} | {row['games']} | {row['wins']} | {win_rate} | {coverage} |"
        )
    (args.out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.out_dir / 'games.csv'}")
    print(f"Wrote {args.out_dir / 'condition_win_rates.csv'}")
    print(f"Wrote {args.out_dir / 'summary.md'}")


if __name__ == "__main__":
    main()
