from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from ptcg_common import DEFAULT_ENGINE_DIR, ensure_engine_on_path


LOG_PLAY = 10
LOG_ATTACH = 11
LOG_EVOLVE = 12
LOG_MOVE_ATTACHED = 14
LOG_ATTACK = 15
LOG_MOVE_CARD = 6
LOG_RESULT = 23

AREA_TRASH = 3
AREA_ACTIVE = 4
AREA_BENCH = 5


def iter_trace_files(path: Path):
    if path.is_file():
        yield path
    else:
        yield from sorted(path.rglob("*.jsonl"))


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_game_summaries(path: Path) -> dict[int, dict[str, Any]]:
    return {
        int(row["game"]): row
        for row in load_rows(path)
        if isinstance(row.get("game"), int)
    }


def card_name(card_names: dict[int, str], card_id: int | None) -> str:
    if card_id is None:
        return ""
    return card_names.get(card_id, str(card_id))


def merge_terminal_summary(
    row: dict[str, Any], terminal: dict[str, Any], card_names: dict[int, str]
) -> None:
    row["result"] = terminal.get("result", row.get("result"))
    row["turn"] = terminal.get("turn", row.get("turn"))
    for player in (0, 1):
        row[f"p{player}_deck"] = terminal.get(f"p{player}_deck", row.get(f"p{player}_deck"))
        row[f"p{player}_prizes_left"] = terminal.get(
            f"p{player}_prizes", row.get(f"p{player}_prizes_left")
        )
        row[f"p{player}_active"] = card_name(
            card_names, terminal.get(f"p{player}_active")
        )
        row[f"p{player}_active_hp"] = terminal.get(f"p{player}_active_hp")
        row[f"p{player}_bench"] = ";".join(
            card_name(card_names, card_id)
            for card_id in terminal.get(f"p{player}_bench") or []
        )
    row["terminal_source"] = "game_summary"


def summarize_game(
    path: Path,
    card_names: dict[int, str],
    attack_names: dict[int, str],
    *,
    line_card_ids: set[int] | None = None,
    focus_attach_card_ids: set[int] | None = None,
    recovery_card_ids: set[int] | None = None,
) -> dict[str, Any]:
    rows = load_rows(path)
    if not rows:
        return {"trace": str(path), "steps": 0}

    attacks: list[str] = []
    evolves: list[str] = []
    plays: list[str] = []
    attaches: list[str] = []
    moved_from_board: list[str] = []
    fan_moves = 0
    grimmsnarl_attacks = 0
    result = None
    previous_logs: list[dict[str, Any]] = []
    first_attack: dict[int, tuple[int | None, str]] = {}
    first_attack_board: dict[int, str] = {}
    first_attack_line_count: dict[int, int] = {}
    first_evolve_turn: dict[int, int | None] = {}
    first_prize_turn: dict[int, int | None] = {}
    first_prize_board: dict[int, str] = {}
    first_prize_line_count: dict[int, int] = {}
    min_line_after_first_prize: dict[int, int] = {}
    first_focus_attach_turn: dict[int, int | None] = {}
    first_focus_attach_board: dict[int, str] = {}
    first_focus_attach_line_count: dict[int, int] = {}
    first_focus_attach_prizes: dict[int, int | None] = {}
    initial_prizes: dict[int, int] = {}
    max_board = {0: 0, 1: 0}
    attack_turns: dict[int, list[int]] = {0: [], 1: []}
    pending_recovery_turns: dict[int, list[int]] = {0: [], 1: []}
    recovery_delays: dict[int, list[int]] = {0: [], 1: []}
    recovery_losses = {0: 0, 1: 0}
    line_card_ids = line_card_ids or set()
    focus_attach_card_ids = focus_attach_card_ids or set()
    recovery_card_ids = recovery_card_ids or set()
    cumulative_logs = any(
        previous
        and len(current) > len(previous)
        and current[: len(previous)] == previous
        for previous, current in zip(
            ((row.get("logs") or []) for row in rows),
            ((row.get("logs") or []) for row in rows[1:]),
        )
    )

    def snapshot_board(snapshot: dict[str, Any], player: int) -> list[int]:
        active_id = snapshot.get(f"p{player}_active")
        bench_ids = snapshot.get(f"p{player}_bench") or []
        return ([active_id] if active_id is not None else []) + list(bench_ids)

    for row in rows:
        snapshot = row.get("snapshot") or {}
        turn = snapshot.get("turn")
        for player in (0, 1):
            board = snapshot_board(snapshot, player)
            max_board[player] = max(max_board[player], len(board))
            prizes = snapshot.get(f"p{player}_prizes")
            if isinstance(prizes, int) and prizes > 0:
                initial_prizes[player] = max(initial_prizes.get(player, 0), prizes)
                if prizes < initial_prizes[player] and player not in first_prize_turn:
                    first_prize_turn[player] = turn
                    first_prize_board[player] = ";".join(card_name(card_names, card_id) for card_id in board)
                    first_prize_line_count[player] = sum(card_id in line_card_ids for card_id in board)
                if prizes < initial_prizes[player] and player in first_prize_turn:
                    line_count = sum(card_id in line_card_ids for card_id in board)
                    min_line_after_first_prize[player] = min(
                        min_line_after_first_prize.get(player, line_count), line_count
                    )

        logs = row.get("logs") or []
        if cumulative_logs and previous_logs and logs[: len(previous_logs)] == previous_logs:
            new_logs = logs[len(previous_logs):]
        else:
            new_logs = logs
        previous_logs = logs

        for log in new_logs:
            typ = log.get("type")
            player = log.get("playerIndex")
            prefix = f"p{player}:"
            if typ == LOG_ATTACK:
                attack_id = log.get("attackId")
                name = attack_names.get(attack_id, str(attack_id))
                attacks.append(prefix + name)
                first_attack.setdefault(player, (turn, name))
                if isinstance(player, int) and player not in first_attack_board:
                    board = snapshot_board(snapshot, player)
                    first_attack_board[player] = ";".join(
                        card_name(card_names, card_id) for card_id in board
                    )
                    first_attack_line_count[player] = sum(
                        card_id in line_card_ids for card_id in board
                    )
                if isinstance(player, int) and isinstance(turn, int):
                    attack_turns[player].append(turn)
                    if pending_recovery_turns[player]:
                        recovery_delays[player].extend(
                            turn - loss_turn for loss_turn in pending_recovery_turns[player]
                        )
                        pending_recovery_turns[player].clear()
                if log.get("cardId") == 648:
                    grimmsnarl_attacks += 1
            elif typ == LOG_EVOLVE:
                evolves.append(prefix + card_name(card_names, log.get("cardId")))
                first_evolve_turn.setdefault(player, turn)
            elif typ == LOG_PLAY:
                plays.append(prefix + card_name(card_names, log.get("cardId")))
            elif typ == LOG_ATTACH:
                attaches.append(
                    prefix
                    + card_name(card_names, log.get("cardId"))
                    + "->"
                    + card_name(card_names, log.get("cardIdTarget"))
                )
                if (
                    isinstance(player, int)
                    and isinstance(turn, int)
                    and log.get("cardIdTarget") in focus_attach_card_ids
                ):
                    first_focus_attach_turn.setdefault(player, turn)
                    if player not in first_focus_attach_board:
                        board = snapshot_board(snapshot, player)
                        first_focus_attach_board[player] = ";".join(
                            card_name(card_names, card_id) for card_id in board
                        )
                        first_focus_attach_line_count[player] = sum(
                            card_id in line_card_ids for card_id in board
                        )
                        first_focus_attach_prizes[player] = snapshot.get(f"p{player}_prizes")
            elif typ == LOG_MOVE_ATTACHED:
                fan_moves += 1
            elif typ == LOG_MOVE_CARD and log.get("toArea") == AREA_TRASH and log.get("fromArea") in {AREA_ACTIVE, AREA_BENCH}:
                moved_from_board.append(prefix + card_name(card_names, log.get("cardId")))
                if (
                    isinstance(player, int)
                    and isinstance(turn, int)
                    and log.get("cardId") in recovery_card_ids
                ):
                    recovery_losses[player] += 1
                    pending_recovery_turns[player].append(turn)
            elif typ == LOG_RESULT:
                result = log.get("result")

    final = rows[-1].get("snapshot") or {}
    attack_counts = Counter(attacks)
    evolve_counts = Counter(evolves)
    play_counts = Counter(plays)
    attach_counts = Counter(attaches)
    board_trash_counts = Counter(moved_from_board)

    def missed_attack_metrics(player: int) -> tuple[int, int]:
        turns = sorted(set(attack_turns[player]))
        missed = [max(0, (later - earlier) // 2 - 1) for earlier, later in zip(turns, turns[1:])]
        return sum(missed), max(missed, default=0)

    p0_missed_attacks, p0_max_missed_streak = missed_attack_metrics(0)
    p1_missed_attacks, p1_max_missed_streak = missed_attack_metrics(1)
    return {
        "trace": str(path),
        "game": rows[-1].get("game"),
        "steps": len(rows),
        "result": result if result is not None else final.get("result"),
        "turn": final.get("turn"),
        "p0_deck": final.get("p0_deck"),
        "p1_deck": final.get("p1_deck"),
        "p0_prizes_left": final.get("p0_prizes"),
        "p1_prizes_left": final.get("p1_prizes"),
        "p0_active": card_name(card_names, final.get("p0_active")),
        "p0_active_hp": final.get("p0_active_hp"),
        "p1_active": card_name(card_names, final.get("p1_active")),
        "p1_active_hp": final.get("p1_active_hp"),
        "p0_bench": ";".join(card_name(card_names, x) for x in final.get("p0_bench") or []),
        "p1_bench": ";".join(card_name(card_names, x) for x in final.get("p1_bench") or []),
        "p0_first_attack_turn": first_attack.get(0, (None, ""))[0],
        "p0_first_attack": first_attack.get(0, (None, ""))[1],
        "p0_first_attack_board": first_attack_board.get(0, ""),
        "p0_first_attack_line_count": first_attack_line_count.get(0),
        "p1_first_attack_turn": first_attack.get(1, (None, ""))[0],
        "p1_first_attack": first_attack.get(1, (None, ""))[1],
        "p1_first_attack_board": first_attack_board.get(1, ""),
        "p1_first_attack_line_count": first_attack_line_count.get(1),
        "p0_first_evolve_turn": first_evolve_turn.get(0),
        "p1_first_evolve_turn": first_evolve_turn.get(1),
        "p0_first_prize_turn": first_prize_turn.get(0),
        "p1_first_prize_turn": first_prize_turn.get(1),
        "p0_first_prize_board": first_prize_board.get(0, ""),
        "p1_first_prize_board": first_prize_board.get(1, ""),
        "p0_first_prize_line_count": first_prize_line_count.get(0),
        "p1_first_prize_line_count": first_prize_line_count.get(1),
        "p0_min_line_after_first_prize": min_line_after_first_prize.get(0),
        "p1_min_line_after_first_prize": min_line_after_first_prize.get(1),
        "p0_first_focus_attach_turn": first_focus_attach_turn.get(0),
        "p1_first_focus_attach_turn": first_focus_attach_turn.get(1),
        "p0_first_focus_attach_board": first_focus_attach_board.get(0, ""),
        "p1_first_focus_attach_board": first_focus_attach_board.get(1, ""),
        "p0_first_focus_attach_line_count": first_focus_attach_line_count.get(0),
        "p1_first_focus_attach_line_count": first_focus_attach_line_count.get(1),
        "p0_first_focus_attach_prizes": first_focus_attach_prizes.get(0),
        "p1_first_focus_attach_prizes": first_focus_attach_prizes.get(1),
        "p0_attack_count": len(attack_turns[0]),
        "p1_attack_count": len(attack_turns[1]),
        "p0_missed_attack_turns_after_first": p0_missed_attacks,
        "p1_missed_attack_turns_after_first": p1_missed_attacks,
        "p0_max_missed_attack_streak": p0_max_missed_streak,
        "p1_max_missed_attack_streak": p1_max_missed_streak,
        "p0_recovery_card_losses": recovery_losses[0],
        "p1_recovery_card_losses": recovery_losses[1],
        "p0_recovered_to_attack": len(recovery_delays[0]),
        "p1_recovered_to_attack": len(recovery_delays[1]),
        "p0_max_recovery_turns": max(recovery_delays[0], default=None),
        "p1_max_recovery_turns": max(recovery_delays[1], default=None),
        "p0_max_board": max_board[0],
        "p1_max_board": max_board[1],
        "grimmsnarl_attacks": grimmsnarl_attacks,
        "fan_moves": fan_moves,
        "top_attacks": "; ".join(f"{name} x{count}" for name, count in attack_counts.most_common(8)),
        "top_evolves": "; ".join(f"{name} x{count}" for name, count in evolve_counts.most_common(8)),
        "top_plays": "; ".join(f"{name} x{count}" for name, count in play_counts.most_common(10)),
        "top_attaches": "; ".join(f"{name} x{count}" for name, count in attach_counts.most_common(8)),
        "board_to_trash": "; ".join(f"{name} x{count}" for name, count in board_trash_counts.most_common(10)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize local battle JSONL traces.")
    parser.add_argument("trace_path", type=Path)
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--game-summary", type=Path)
    parser.add_argument("--line-card-id", type=int, action="append", default=[])
    parser.add_argument("--focus-attach-card-id", type=int, action="append", default=[])
    parser.add_argument("--recovery-card-id", type=int, action="append", default=[])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_engine_on_path(args.engine_dir)
    from cg.api import all_attack, all_card_data

    card_names = {card.cardId: card.name for card in all_card_data()}
    attack_names = {attack.attackId: attack.name for attack in all_attack()}
    rows = [
        summarize_game(
            path,
            card_names,
            attack_names,
            line_card_ids=set(args.line_card_id),
            focus_attach_card_ids=set(args.focus_attach_card_id),
            recovery_card_ids=set(args.recovery_card_id),
        )
        for path in iter_trace_files(args.trace_path)
    ]
    if args.game_summary:
        terminal_by_game = load_game_summaries(args.game_summary)
        for row in rows:
            terminal = terminal_by_game.get(row.get("game"))
            if terminal:
                merge_terminal_summary(row, terminal, card_names)
    if not rows:
        print("No trace files found.")
        return

    fieldnames = list(rows[0].keys())
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {args.out}")

    for row in rows[:20]:
        print(
            f"{Path(row['trace']).parent.name}/{Path(row['trace']).name}: "
            f"result={row.get('result')} p0_prizes={row.get('p0_prizes_left')} "
            f"p1_prizes={row.get('p1_prizes_left')} grimmsnarl_attacks={row.get('grimmsnarl_attacks')} "
            f"fan_moves={row.get('fan_moves')} board_to_trash={row.get('board_to_trash')}"
        )


if __name__ == "__main__":
    main()
