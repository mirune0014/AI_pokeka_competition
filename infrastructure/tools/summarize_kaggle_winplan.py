from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from ptcg_common import DEFAULT_ENGINE_DIR, ensure_engine_on_path, write_csv


LOG_PLAY = 10
LOG_ATTACH = 11
LOG_EVOLVE = 12
LOG_ATTACK = 15


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text())


def card_id(card: dict[str, Any] | None) -> int | None:
    if not card:
        return None
    value = card.get("id", card.get("cardId"))
    return value if isinstance(value, int) else None


def zone_cards(player: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [card for card in (player.get(key) or []) if isinstance(card, dict)]


def board_ids(player: dict[str, Any]) -> list[int]:
    cards = zone_cards(player, "active") + zone_cards(player, "bench")
    return [value for card in cards if (value := card_id(card)) is not None]


def prize_count(player: dict[str, Any]) -> int | None:
    prizes = player.get("prize")
    return len(prizes) if isinstance(prizes, list) else None


def target_seat_map(episodes_doc: dict[str, Any], submission_id: int) -> dict[int, int]:
    result: dict[int, int] = {}
    for episode in episodes_doc.get("episodes") or []:
        episode_id = episode.get("id")
        if not isinstance(episode_id, int):
            continue
        for position, agent in enumerate(episode.get("agents") or []):
            if agent.get("submissionId") != submission_id:
                continue
            index = agent.get("index", position)
            if isinstance(index, int):
                result[episode_id] = index
            break
    return result


def episode_metadata(episodes_doc: dict[str, Any], submission_id: int) -> dict[int, dict[str, Any]]:
    teams = {team.get("id"): team for team in episodes_doc.get("teams") or []}
    result: dict[int, dict[str, Any]] = {}
    for episode in episodes_doc.get("episodes") or []:
        episode_id = episode.get("id")
        if not isinstance(episode_id, int):
            continue
        agents = episode.get("agents") or []
        target = next((agent for agent in agents if agent.get("submissionId") == submission_id), {})
        opponent = next((agent for agent in agents if agent is not target), {})
        result[episode_id] = {
            "reward": target.get("reward"),
            "opponent_team": teams.get(opponent.get("teamId"), {}).get("teamName", ""),
            "opponent_submission_id": opponent.get("submissionId", ""),
            "opponent_initial_score": opponent.get("initialScore", ""),
            "target_updated_score": target.get("updatedScore", ""),
            "episode_type": episode.get("type", ""),
        }
    return result


def target_seat_from_team(replay: dict[str, Any], target_team: str) -> int | None:
    teams = (replay.get("info") or {}).get("TeamNames") or []
    matches = [index for index, team in enumerate(teams) if team == target_team]
    return matches[0] if len(matches) == 1 else None


def target_entries(replay: dict[str, Any], seat: int):
    for step, pair in enumerate(replay.get("steps") or []):
        if seat >= len(pair or []):
            continue
        entry = pair[seat]
        if not isinstance(entry, dict):
            continue
        observation = entry.get("observation") or {}
        current = observation.get("current") or {}
        players = current.get("players") or []
        if len(players) <= seat:
            continue
        yield step, entry, observation, current, players[seat]


def new_logs(current: list[dict[str, Any]], previous: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if current == previous:
        return []
    if previous and len(current) >= len(previous) and current[: len(previous)] == previous:
        return current[len(previous) :]
    return current


def replay_events(replay: dict[str, Any]):
    """Yield each cumulative-log event once, including terminal opponent frames."""
    previous_logs: list[dict[str, Any]] = []
    sequence = 0
    for pair in replay.get("steps") or []:
        observations: list[tuple[list[dict[str, Any]], dict[str, Any]]] = []
        for entry in pair or []:
            if not isinstance(entry, dict):
                continue
            observation = entry.get("observation") or {}
            logs = [log for log in observation.get("logs") or [] if isinstance(log, dict)]
            if logs:
                observations.append((logs, observation.get("current") or {}))
        if not observations:
            continue
        logs, current = max(observations, key=lambda item: len(item[0]))
        for log in new_logs(logs, previous_logs):
            turn = current.get("turn")
            player = log.get("playerIndex")
            # Attacks end the turn, so their first visible log can be in the
            # opponent's next observation (or only in a terminal frame).
            if (
                log.get("type") == LOG_ATTACK
                and isinstance(turn, int)
                and isinstance(player, int)
                and current.get("yourIndex") != player
            ):
                turn -= 1
            yield sequence, turn, current, log
            sequence += 1
        previous_logs = logs


def summarize_replay(
    replay_path: Path,
    seat: int,
    card_names: dict[int, str],
    attack_names: dict[int, str],
    *,
    line_card_ids: set[int],
    focus_energy_ids: set[int],
    focus_target_ids: set[int],
    focus_play_ids: set[int] | None = None,
) -> dict[str, Any]:
    replay = read_json(replay_path)
    episode_id = (replay.get("info") or {}).get("EpisodeId", "")
    rewards = replay.get("rewards") or []
    reward = rewards[seat] if seat < len(rewards) else None
    initial_prizes: int | None = None
    first_prize_turn: int | None = None
    first_prize_line_count: int | None = None
    first_prize_board = ""
    first_attack_turn: int | None = None
    first_attack_name = ""
    first_attack_line_count: int | None = None
    first_attack_board = ""
    first_evolve_turn: int | None = None
    first_focus_attach_turn: int | None = None
    first_focus_attach_line_count: int | None = None
    first_focus_attach_board = ""
    max_line_count = 0
    max_board_count = 0
    attack_turns: list[int] = []
    attack_events: list[tuple[int, int]] = []
    focus_play_turns: list[int] = []
    focus_play_events: list[tuple[int, int]] = []
    focus_play_count = 0
    attack_counts: Counter[str] = Counter()
    play_counts: Counter[str] = Counter()
    attach_counts: Counter[str] = Counter()
    final_turn: int | None = None
    final_prizes: int | None = None
    final_opp_deck: int | None = None
    final_opp_prizes: int | None = None
    focus_play_ids = focus_play_ids or set()

    def labels(ids: list[int]) -> str:
        return ";".join(card_names.get(value, str(value)) for value in ids)

    for _, _, observation, current, mine in target_entries(replay, seat):
        players = current.get("players") or []
        opp = players[1 - seat] if len(players) > 1 - seat else {}
        turn = current.get("turn")
        if isinstance(turn, int):
            final_turn = turn
        board = board_ids(mine)
        line_count = sum(value in line_card_ids for value in board)
        max_line_count = max(max_line_count, line_count)
        max_board_count = max(max_board_count, len(board))
        prizes = prize_count(mine)
        opp_prizes = prize_count(opp)
        if isinstance(opp_prizes, int):
            final_opp_prizes = opp_prizes
        opp_deck = opp.get("deckCount")
        if isinstance(opp_deck, int):
            final_opp_deck = opp_deck
        if isinstance(prizes, int):
            final_prizes = prizes
            if prizes > 0:
                initial_prizes = max(initial_prizes or prizes, prizes)
            if initial_prizes is not None and prizes < initial_prizes and first_prize_turn is None:
                first_prize_turn = turn if isinstance(turn, int) else None
                first_prize_line_count = line_count
                first_prize_board = labels(board)

    for sequence, turn, current, log in replay_events(replay):
        if log.get("playerIndex") != seat:
            continue
        players = current.get("players") or []
        mine = players[seat] if len(players) > seat else {}
        board = board_ids(mine)
        line_count = sum(value in line_card_ids for value in board)
        typ = log.get("type")
        if typ == LOG_PLAY:
            value = log.get("cardId")
            play_counts[card_names.get(value, str(value))] += 1
            if value in focus_play_ids:
                focus_play_count += 1
                if isinstance(turn, int):
                    focus_play_turns.append(turn)
                    focus_play_events.append((sequence, turn))
        elif typ == LOG_EVOLVE and first_evolve_turn is None:
            first_evolve_turn = turn if isinstance(turn, int) else None
        elif typ == LOG_ATTACK:
            attack_id = log.get("attackId")
            name = attack_names.get(attack_id, str(attack_id))
            attack_counts[name] += 1
            if isinstance(turn, int):
                attack_turns.append(turn)
                attack_events.append((sequence, turn))
            if first_attack_turn is None:
                first_attack_turn = turn if isinstance(turn, int) else None
                first_attack_name = name
                first_attack_line_count = line_count
                first_attack_board = labels(board)
        elif typ == LOG_ATTACH:
            source = log.get("cardId")
            target = log.get("cardIdTarget")
            attach_counts[
                f"{card_names.get(source, str(source))}->{card_names.get(target, str(target))}"
            ] += 1
            if (
                source in focus_energy_ids
                and target in focus_target_ids
                and first_focus_attach_turn is None
            ):
                first_focus_attach_turn = turn if isinstance(turn, int) else None
                first_focus_attach_line_count = line_count
                first_focus_attach_board = labels(board)

    unique_attack_turns = sorted(set(attack_turns))
    unique_focus_play_turns = sorted(set(focus_play_turns))
    first_focus_play_turn = unique_focus_play_turns[0] if unique_focus_play_turns else None
    first_focus_sequence = focus_play_events[0][0] if focus_play_events else None
    attacks_after_first_focus = (
        [(sequence, turn) for sequence, turn in attack_events if sequence > first_focus_sequence]
        if first_focus_sequence is not None
        else []
    )
    attack_turns_after_first_focus = [turn for _, turn in attacks_after_first_focus]
    first_attack_after_focus_turn = (
        attack_turns_after_first_focus[0] if attack_turns_after_first_focus else None
    )
    focus_play_turns_with_attack = len(set(unique_focus_play_turns) & set(unique_attack_turns))
    gaps = [max(0, (later - earlier) // 2 - 1) for earlier, later in zip(unique_attack_turns, unique_attack_turns[1:])]
    return {
        "episode_id": episode_id,
        "seat": seat,
        "reward": reward,
        "result": "win" if reward == 1 else "loss" if reward == -1 else "draw",
        "final_turn": final_turn,
        "initial_prizes": initial_prizes,
        "final_prizes": final_prizes,
        "final_opp_prizes": final_opp_prizes,
        "final_opp_deck": final_opp_deck,
        "win_condition": (
            "deckout" if reward == 1 and final_opp_deck == 0
            else "non_deckout" if reward == 1
            else "loss_or_draw"
        ),
        "first_evolve_turn": first_evolve_turn,
        "first_attack_turn": first_attack_turn,
        "first_attack": first_attack_name,
        "first_attack_line_count": first_attack_line_count,
        "first_attack_board": first_attack_board,
        "first_prize_turn": first_prize_turn,
        "first_prize_line_count": first_prize_line_count,
        "first_prize_board": first_prize_board,
        "first_focus_attach_turn": first_focus_attach_turn,
        "first_focus_attach_line_count": first_focus_attach_line_count,
        "first_focus_attach_board": first_focus_attach_board,
        "max_line_count": max_line_count,
        "max_board_count": max_board_count,
        "attack_count": len(unique_attack_turns),
        "missed_attack_turns_after_first": sum(gaps),
        "max_missed_attack_streak": max(gaps, default=0),
        "focus_play_count": focus_play_count,
        "first_focus_play_turn": first_focus_play_turn,
        "focus_play_turns_with_attack": focus_play_turns_with_attack,
        "first_attack_after_focus_turn": first_attack_after_focus_turn,
        "first_attack_after_focus_delay": (
            max(0, (first_attack_after_focus_turn - first_focus_play_turn) // 2)
            if first_attack_after_focus_turn is not None and first_focus_play_turn is not None
            else None
        ),
        "attacks_after_first_focus_play": len(attacks_after_first_focus),
        "focus_play_recovered_to_attack": first_attack_after_focus_turn is not None,
        "top_attacks": "; ".join(f"{name} x{count}" for name, count in attack_counts.most_common()),
        "top_plays": "; ".join(f"{name} x{count}" for name, count in play_counts.most_common(10)),
        "top_attaches": "; ".join(f"{name} x{count}" for name, count in attach_counts.most_common(10)),
        "replay": str(replay_path),
    }


def rate(rows: list[dict[str, Any]], predicate) -> float | None:
    return sum(bool(predicate(row)) for row in rows) / len(rows) if rows else None


def win_rate(rows: list[dict[str, Any]]) -> float | None:
    return rate(rows, lambda row: row.get("reward") == 1)


def median_value(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [row[key] for row in rows if isinstance(row.get(key), int)]
    return statistics.median(values) if values else None


def aggregate(rows: list[dict[str, Any]], line_threshold: int) -> dict[str, Any]:
    public = [row for row in rows if row.get("episode_type") == "EPISODE_TYPE_PUBLIC"]
    source = public or rows
    wide = [row for row in source if (row.get("first_attack_line_count") or 0) >= line_threshold]
    thin = [row for row in source if row not in wide]
    return {
        "episodes": len(rows),
        "public_episodes": len(public),
        "wins": sum(row.get("reward") == 1 for row in source),
        "losses": sum(row.get("reward") == -1 for row in source),
        "deckout_wins": sum(row.get("win_condition") == "deckout" for row in source),
        "non_deckout_wins": sum(row.get("win_condition") == "non_deckout" for row in source),
        "win_rate": win_rate(source),
        "median_first_attack_turn": median_value(source, "first_attack_turn"),
        "median_first_prize_turn": median_value(source, "first_prize_turn"),
        "median_first_attack_line_count": median_value(source, "first_attack_line_count"),
        "line_threshold": line_threshold,
        "first_attack_line_threshold_rate": rate(
            source, lambda row: (row.get("first_attack_line_count") or 0) >= line_threshold
        ),
        "first_prize_line_threshold_rate": rate(
            source, lambda row: (row.get("first_prize_line_count") or 0) >= line_threshold
        ),
        "focus_attach_rate": rate(source, lambda row: row.get("first_focus_attach_turn") is not None),
        "focus_play_rate": rate(source, lambda row: row.get("focus_play_count", 0) > 0),
        "focus_play_win_rate": win_rate([row for row in source if row.get("focus_play_count", 0) > 0]),
        "no_focus_play_win_rate": win_rate([row for row in source if row.get("focus_play_count", 0) == 0]),
        "focus_play_recovery_rate": rate(
            [row for row in source if row.get("focus_play_count", 0) > 0],
            lambda row: row.get("focus_play_recovered_to_attack"),
        ),
        "focus_play_same_turn_attack_rate": rate(
            [row for row in source if row.get("focus_play_count", 0) > 0],
            lambda row: row.get("focus_play_turns_with_attack", 0) > 0,
        ),
        "median_attacks_after_first_focus_play": median_value(
            [row for row in source if row.get("focus_play_count", 0) > 0],
            "attacks_after_first_focus_play",
        ),
        "win_rate_with_wide_first_attack": win_rate(wide),
        "wide_first_attack_games": len(wide),
        "win_rate_without_wide_first_attack": win_rate(thin),
        "thin_first_attack_games": len(thin),
        "median_missed_attack_turns_after_first": median_value(source, "missed_attack_turns_after_first"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize proactive win-plan milestones from Kaggle replays.")
    parser.add_argument("--episodes-json", type=Path)
    parser.add_argument("--submission-id", type=int)
    parser.add_argument("--replay-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--target-team", default="")
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    parser.add_argument("--line-card-id", type=int, action="append", default=[])
    parser.add_argument("--focus-energy-id", type=int, action="append", default=[])
    parser.add_argument("--focus-target-id", type=int, action="append", default=[])
    parser.add_argument("--focus-play-id", type=int, action="append", default=[])
    parser.add_argument("--line-threshold", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.episodes_json and args.submission_id is None:
        raise SystemExit("--submission-id is required with --episodes-json")
    if not args.episodes_json and not args.target_team:
        raise SystemExit("provide --episodes-json/--submission-id or --target-team")
    ensure_engine_on_path(args.engine_dir)
    try:
        from cg.api import all_attack, all_card_data

        card_names = {card.cardId: card.name for card in all_card_data()}
        attack_names = {attack.attackId: attack.name for attack in all_attack()}
    except Exception as exc:
        card_names = {}
        attack_names = {}
        print(f"warning: engine names unavailable; using numeric IDs ({exc})", file=sys.stderr)
    episodes_doc = read_json(args.episodes_json) if args.episodes_json else {}
    seats = target_seat_map(episodes_doc, args.submission_id) if args.submission_id is not None else {}
    metadata = episode_metadata(episodes_doc, args.submission_id) if args.submission_id is not None else {}
    rows: list[dict[str, Any]] = []
    skipped: list[str] = []
    for replay_path in sorted(args.replay_dir.glob("episode_*_replay.json")):
        replay = read_json(replay_path)
        episode_id = (replay.get("info") or {}).get("EpisodeId")
        seat = seats.get(episode_id)
        if seat is None and args.target_team:
            seat = target_seat_from_team(replay, args.target_team)
        if seat is None:
            skipped.append(str(replay_path))
            continue
        row = summarize_replay(
            replay_path,
            seat,
            card_names,
            attack_names,
            line_card_ids=set(args.line_card_id),
            focus_energy_ids=set(args.focus_energy_id),
            focus_target_ids=set(args.focus_target_id),
            focus_play_ids=set(args.focus_play_id),
        )
        row.update(metadata.get(episode_id, {}))
        rows.append(row)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    write_csv(args.out_dir / "episodes.csv", rows, fields)
    summary = aggregate(rows, args.line_threshold)
    summary["submission_id"] = args.submission_id
    summary["target_team"] = args.target_team
    summary["skipped_replays"] = skipped
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
