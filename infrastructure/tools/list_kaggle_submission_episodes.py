from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from scan_kaggle_episodes import build_opener, download_replay, post_json


LIST_EPISODES_PATH = "/api/i/competitions.EpisodeService/ListEpisodes"


def target_row(
    episode: dict[str, Any],
    teams: dict[int, dict[str, Any]],
    submission_id: int,
) -> dict[str, Any]:
    agents = episode.get("agents") or []
    target = next((agent for agent in agents if agent.get("submissionId") == submission_id), {})
    opponent = next((agent for agent in agents if agent.get("id") != target.get("id")), {})

    return {
        "episode_id": episode.get("id", ""),
        "create_time": episode.get("createTime", ""),
        "end_time": episode.get("endTime", ""),
        "state": episode.get("state", ""),
        "type": episode.get("type", ""),
        "target_reward": target.get("reward", ""),
        "target_initial_score": target.get("initialScore", ""),
        "target_updated_score": target.get("updatedScore", ""),
        "opponent_team": teams.get(opponent.get("teamId"), {}).get("teamName", ""),
        "opponent_submission_id": opponent.get("submissionId", ""),
        "opponent_reward": opponent.get("reward", ""),
        "opponent_initial_score": opponent.get("initialScore", ""),
        "opponent_updated_score": opponent.get("updatedScore", ""),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List Kaggle public episodes for one submission id.")
    parser.add_argument("--submission-id", type=int, required=True)
    parser.add_argument("--out-dir", type=Path, default=Path("_local_generated/analysis_outputs/kaggle_live"))
    parser.add_argument("--prefix", default="")
    parser.add_argument("--save-replays", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = args.prefix or f"submission_{args.submission_id}"

    opener = build_opener()
    status, data, error = post_json(opener, LIST_EPISODES_PATH, {"submissionId": args.submission_id})
    if not data:
        raise SystemExit(f"ListEpisodes failed {status}: {error}")

    json_path = out_dir / f"{prefix}_episodes.json"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    teams = {team.get("id"): team for team in data.get("teams") or []}
    rows = []
    for episode in data.get("episodes") or []:
        row = target_row(episode, teams, args.submission_id)
        if args.save_replays and row["episode_id"]:
            replay_path = out_dir / f"episode_{row['episode_id']}_replay.json"
            row["replay_downloaded"] = replay_path.exists() or download_replay(
                opener, int(row["episode_id"]), replay_path
            )
        else:
            row["replay_downloaded"] = ""
        rows.append(row)

    csv_path = out_dir / f"{prefix}_episodes.csv"
    fieldnames = [
        "episode_id",
        "create_time",
        "end_time",
        "state",
        "type",
        "target_reward",
        "target_initial_score",
        "target_updated_score",
        "opponent_team",
        "opponent_submission_id",
        "opponent_reward",
        "opponent_initial_score",
        "opponent_updated_score",
        "replay_downloaded",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({"status": status, "episodes": len(rows), "csv": str(csv_path), "json": str(json_path)}))


if __name__ == "__main__":
    main()
