from __future__ import annotations

import argparse
import csv
import http.client
import json
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any


BASE_URL = "https://www.kaggle.com"
COMPETITION = "pokemon-tcg-ai-battle"
GET_EPISODE_PATH = "/api/i/competitions.EpisodeService/GetEpisode"
_THREAD_LOCAL = threading.local()


def build_opener() -> urllib.request.OpenerDirector:
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", "Mozilla/5.0 Codex Kaggle episode scanner")]

    # Seed Kaggle web cookies. The internal API requires the XSRF-TOKEN cookie value
    # to be mirrored in the X-XSRF-TOKEN header.
    seed_url = f"{BASE_URL}/competitions/{COMPETITION}/submissions"
    with opener.open(seed_url, timeout=30) as response:
        response.read(512)

    xsrf = None
    for cookie in jar:
        if cookie.name == "XSRF-TOKEN":
            xsrf = cookie.value
            break
    if not xsrf:
        raise RuntimeError("Could not obtain Kaggle XSRF-TOKEN cookie.")

    opener.xsrf_token = xsrf  # type: ignore[attr-defined]
    return opener


def thread_opener() -> urllib.request.OpenerDirector:
    opener = getattr(_THREAD_LOCAL, "opener", None)
    if opener is None:
        opener = build_opener()
        _THREAD_LOCAL.opener = opener
    return opener


def post_json(opener: urllib.request.OpenerDirector, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any] | None, str]:
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/competitions/{COMPETITION}/submissions",
        "X-XSRF-TOKEN": getattr(opener, "xsrf_token"),
        "X-Kaggle-Build-Version": "",
    }
    request = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method="POST")
    try:
        with opener.open(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body), ""
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return exc.code, None, body[:500]
    except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.RemoteDisconnected, OSError) as exc:
        return 0, None, f"{type(exc).__name__}: {exc}"[:500]


def get_episode(opener: urllib.request.OpenerDirector, episode_id: int) -> tuple[int, dict[str, Any] | None, str]:
    return post_json(opener, GET_EPISODE_PATH, {"episodeId": episode_id})


def download_replay(opener: urllib.request.OpenerDirector, episode_id: int, output: Path) -> bool:
    output.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BASE_URL}/competitions/episodes/{episode_id}/replay.json"
    try:
        with opener.open(url, timeout=60) as response, output.open("wb") as f:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
        return True
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError, http.client.RemoteDisconnected, OSError):
        return False


def find_team_name(teams: list[dict[str, Any]], team_id: int | None) -> str:
    if team_id is None:
        return ""
    for team in teams:
        if team.get("id") == team_id:
            return str(team.get("teamName") or "")
    return ""


def row_from_episode(episode_id: int, status: int, data: dict[str, Any], target_submission_id: int) -> dict[str, Any]:
    episode = data.get("episode") or {}
    agents = episode.get("agents") or []
    teams = data.get("teams") or []

    target_agents = [agent for agent in agents if agent.get("submissionId") == target_submission_id]
    target_agent = target_agents[0] if target_agents else {}
    target_team_id = target_agent.get("teamId")
    opponent_agents = [
        agent
        for agent in agents
        if agent.get("teamId") != target_team_id or agent.get("submissionId") != target_submission_id
    ]
    opponent_agent = opponent_agents[0] if opponent_agents else {}

    return {
        "episode_id": episode_id,
        "http_status": status,
        "target_submission_hit": bool(target_agents),
        "create_time": episode.get("createTime", ""),
        "end_time": episode.get("endTime", ""),
        "state": episode.get("state", ""),
        "type": episode.get("type", ""),
        "seed": episode.get("seed", ""),
        "target_team_id": target_team_id or "",
        "target_team": find_team_name(teams, target_team_id),
        "target_agent_id": target_agent.get("id", ""),
        "target_reward": target_agent.get("reward", ""),
        "target_initial_score": target_agent.get("initialScore", ""),
        "target_updated_score": target_agent.get("updatedScore", ""),
        "opponent_team_id": opponent_agent.get("teamId", ""),
        "opponent_team": find_team_name(teams, opponent_agent.get("teamId")),
        "opponent_submission_id": opponent_agent.get("submissionId", ""),
        "opponent_reward": opponent_agent.get("reward", ""),
        "agents_json": json.dumps(agents, ensure_ascii=False),
        "teams_json": json.dumps(teams, ensure_ascii=False),
    }


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan Kaggle PTCG episode IDs for a target submission.")
    parser.add_argument("--submission-id", type=int, required=True)
    parser.add_argument("--start", type=int, required=True, help="First episode ID, inclusive.")
    parser.add_argument("--end", type=int, required=True, help="Last episode ID, inclusive.")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--replay-dir", type=Path)
    parser.add_argument("--save-replays", choices=["none", "hits", "all"], default="hits")
    parser.add_argument("--write-all", action="store_true", help="Write all existing episodes, not only target hits.")
    parser.add_argument("--sleep", type=float, default=0.0, help="Delay between episode requests.")
    parser.add_argument("--workers", type=int, default=1, help="Parallel worker count for episode requests.")
    return parser.parse_args()


def scan_one(
    episode_id: int,
    submission_id: int,
    save_replays: str,
    replay_dir: Path,
    write_all: bool,
    sleep_seconds: float,
) -> tuple[dict[str, Any] | None, dict[str, int]]:
    opener = thread_opener()
    counts = {"checked": 1, "existing": 0, "hits": 0, "downloaded_replays": 0}
    status, data, error = get_episode(opener, episode_id)
    if sleep_seconds:
        time.sleep(sleep_seconds)

    if not data:
        if write_all and status not in {400, 404}:
            return (
                {
                    "episode_id": episode_id,
                    "http_status": status,
                    "target_submission_hit": False,
                    "create_time": "",
                    "end_time": "",
                    "state": "",
                    "type": "",
                    "seed": "",
                    "target_team_id": "",
                    "target_team": "",
                    "target_agent_id": "",
                    "target_reward": "",
                    "target_initial_score": "",
                    "target_updated_score": "",
                    "opponent_team_id": "",
                    "opponent_team": "",
                    "opponent_submission_id": "",
                    "opponent_reward": "",
                    "agents_json": "",
                    "teams_json": error,
                },
                counts,
            )
        return None, counts

    counts["existing"] = 1
    row = row_from_episode(episode_id, status, data, submission_id)
    is_hit = bool(row["target_submission_hit"])
    if is_hit:
        counts["hits"] = 1

    should_save = save_replays == "all" or (save_replays == "hits" and is_hit)
    if should_save:
        output = replay_dir / f"episode_{episode_id}_replay.json"
        if download_replay(opener, episode_id, output):
            counts["downloaded_replays"] = 1

    if write_all or is_hit:
        return row, counts
    return None, counts


def main() -> None:
    args = parse_args()
    if args.end < args.start:
        raise ValueError("--end must be >= --start")

    out = args.out or Path("analysis_outputs/kaggle_live") / (
        f"scan_{args.submission_id}_{args.start}_{args.end}.csv"
    )
    replay_dir = args.replay_dir or Path("analysis_outputs/kaggle_live")

    rows: list[dict[str, Any]] = []
    counts = {"checked": 0, "existing": 0, "hits": 0, "downloaded_replays": 0}
    fieldnames = [
        "episode_id",
        "http_status",
        "target_submission_hit",
        "create_time",
        "end_time",
        "state",
        "type",
        "seed",
        "target_team_id",
        "target_team",
        "target_agent_id",
        "target_reward",
        "target_initial_score",
        "target_updated_score",
        "opponent_team_id",
        "opponent_team",
        "opponent_submission_id",
        "opponent_reward",
        "agents_json",
        "teams_json",
    ]

    worker_count = max(1, args.workers)
    episode_ids = list(range(args.start, args.end + 1))
    if worker_count == 1:
        results = (
            scan_one(
                episode_id,
                args.submission_id,
                args.save_replays,
                replay_dir,
                args.write_all,
                args.sleep,
            )
            for episode_id in episode_ids
        )
        for row, partial_counts in results:
            for key, value in partial_counts.items():
                counts[key] += value
            if row:
                rows.append(row)
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            results = executor.map(
                lambda episode_id: scan_one(
                    episode_id,
                    args.submission_id,
                    args.save_replays,
                    replay_dir,
                    args.write_all,
                    args.sleep,
                ),
                episode_ids,
            )
            for row, partial_counts in results:
                for key, value in partial_counts.items():
                    counts[key] += value
                if row:
                    rows.append(row)

    write_rows(out, rows, fieldnames)
    print(json.dumps({"out": str(out), **counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
