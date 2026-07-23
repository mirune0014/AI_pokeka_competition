from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Join Kaggle submission episodes with extracted replay decks and summarize losses."
    )
    parser.add_argument("--episodes-csv", type=Path, required=True)
    parser.add_argument("--decks-csv", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="submission")
    parser.add_argument("--target-team", default="rurumi")
    parser.add_argument("--include-validation", action="store_true")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def parse_int(value: str) -> int:
    try:
        return int(float(value or 0))
    except ValueError:
        return 0


def win_rate(wins: int, games: int) -> str:
    if games <= 0:
        return ""
    return f"{wins / games:.4f}"


def replay_priority(row: dict[str, str]) -> tuple[int, int]:
    file_name = row.get("file", "")
    is_replay = "episode_" in file_name and file_name.endswith("_replay.json")
    has_archetype = bool(row.get("archetype") and row.get("archetype") != "unknown")
    return int(is_replay), int(has_archetype)


def build_opponent_deck_index(
    deck_rows: list[dict[str, str]],
    target_team: str,
) -> dict[str, dict[str, str]]:
    by_episode: dict[str, dict[str, str]] = {}
    for row in deck_rows:
        episode_id = row.get("episode_id", "")
        if not episode_id:
            continue
        if row.get("team", "") == target_team:
            continue
        current = by_episode.get(episode_id)
        if current is None or replay_priority(row) > replay_priority(current):
            by_episode[episode_id] = row
    return by_episode


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    episodes = read_csv(args.episodes_csv)
    decks = read_csv(args.decks_csv)
    opponent_decks = build_opponent_deck_index(decks, args.target_team)

    joined: list[dict[str, Any]] = []
    for episode in episodes:
        episode_type = episode.get("type", "")
        if not args.include_validation and episode_type != "EPISODE_TYPE_PUBLIC":
            continue
        episode_id = episode.get("episode_id", "")
        deck = opponent_decks.get(episode_id, {})
        reward = parse_int(episode.get("target_reward", ""))
        joined.append(
            {
                "episode_id": episode_id,
                "create_time": episode.get("create_time", ""),
                "end_time": episode.get("end_time", ""),
                "type": episode_type,
                "reward": reward,
                "opponent_team": episode.get("opponent_team", ""),
                "opponent_submission_id": episode.get("opponent_submission_id", ""),
                "opponent_initial_score": episode.get("opponent_initial_score", ""),
                "target_initial_score": episode.get("target_initial_score", ""),
                "target_updated_score": episode.get("target_updated_score", ""),
                "opponent_archetype": deck.get("archetype", "missing"),
                "opponent_deck_id": deck.get("deck_id", ""),
                "opponent_deck": deck.get("deck", ""),
                "replay": deck.get("file", ""),
            }
        )

    grouped: dict[str, dict[str, int]] = defaultdict(lambda: {"games": 0, "wins": 0, "losses": 0, "draws": 0})
    for row in joined:
        archetype = str(row["opponent_archetype"] or "missing")
        bucket = grouped[archetype]
        bucket["games"] += 1
        reward = int(row["reward"])
        if reward > 0:
            bucket["wins"] += 1
        elif reward < 0:
            bucket["losses"] += 1
        else:
            bucket["draws"] += 1

    summary = [
        {
            "opponent_archetype": archetype,
            "games": values["games"],
            "wins": values["wins"],
            "losses": values["losses"],
            "draws": values["draws"],
            "win_rate": win_rate(values["wins"], values["games"]),
        }
        for archetype, values in grouped.items()
    ]
    summary.sort(key=lambda row: (-int(row["losses"]), -int(row["games"]), row["opponent_archetype"]))

    losses = [row for row in joined if int(row["reward"]) < 0]

    joined_path = args.out_dir / f"{args.prefix}_joined.csv"
    summary_path = args.out_dir / f"{args.prefix}_archetype_summary.csv"
    losses_path = args.out_dir / f"{args.prefix}_losses.csv"

    joined_fields = [
        "episode_id",
        "create_time",
        "end_time",
        "type",
        "reward",
        "opponent_team",
        "opponent_submission_id",
        "opponent_initial_score",
        "target_initial_score",
        "target_updated_score",
        "opponent_archetype",
        "opponent_deck_id",
        "opponent_deck",
        "replay",
    ]
    write_csv(joined_path, joined, joined_fields)
    write_csv(
        summary_path,
        summary,
        ["opponent_archetype", "games", "wins", "losses", "draws", "win_rate"],
    )
    write_csv(losses_path, losses, joined_fields)

    print(
        json.dumps(
            {
                "episodes": len(joined),
                "losses": len(losses),
                "joined": str(joined_path),
                "summary": str(summary_path),
                "losses_csv": str(losses_path),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
