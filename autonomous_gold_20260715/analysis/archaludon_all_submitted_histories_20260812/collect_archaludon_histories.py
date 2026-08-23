from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import kaggle

ROOT = Path(__file__).resolve().parent
SUBMISSIONS_DIR = ROOT / "submissions"
REPLAYS_DIR = ROOT / "replays"
for directory in (SUBMISSIONS_DIR, REPLAYS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

# Archaludon entries are identified by the immutable submitted filename;
# rule3v3 was the historical Archaludon package whose filename did not carry
# the deck name. The generic tar is retained for explicit inspection.
api = kaggle.api
all_submissions = api.competition_submissions("pokemon-tcg-ai-battle", page_size=100)
selected = [
    item
    for item in all_submissions
    if "archaludon" in (item.file_name or "").lower()
    or "rule3v3" in (item.file_name or "").lower()
    or item.file_name == "submission.tar.gz"
]

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "infrastructure" / "tools"))
from scan_kaggle_episodes import build_opener, download_replay, post_json  # noqa: E402

LIST_EPISODES_PATH = "/api/i/competitions.EpisodeService/ListEpisodes"
opener = build_opener()

metadata = []
for item in selected:
    filename = item.file_name or ""
    if "rule3v3" in filename.lower():
        classification = "archaludon_rule3v3_filename"
    elif filename == "submission.tar.gz":
        classification = "ambiguous_submission_tar_in_archaludon_sequence"
    else:
        classification = "archaludon_filename"
    metadata.append(
        {
            "submission_id": int(item.ref),
            "date": item.date.isoformat() if item.date else "",
            "status": getattr(item.status, "name", str(item.status)),
            "public_score": item.public_score,
            "private_score": item.private_score,
            "file_name": filename,
            "description": item.description or "",
            "classification": classification,
            "url": item.url,
        }
    )

(ROOT / "submission_metadata.json").write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
)

all_rows: list[dict[str, object]] = []
failures: list[dict[str, object]] = []
for index, item in enumerate(selected, start=1):
    submission_id = int(item.ref)
    submission_dir = SUBMISSIONS_DIR / str(submission_id)
    submission_dir.mkdir(parents=True, exist_ok=True)
    status, data, error = post_json(opener, LIST_EPISODES_PATH, {"submissionId": submission_id})
    if not data:
        failures.append(
            {
                "submission_id": submission_id,
                "stage": "ListEpisodes",
                "status": status,
                "error": error,
            }
        )
        continue
    (submission_dir / "episodes.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    teams = {team.get("id"): team for team in data.get("teams") or []}
    target_rows = []
    for episode in data.get("episodes") or []:
        episode_id = episode.get("id")
        agents = episode.get("agents") or []
        target = next((agent for agent in agents if agent.get("submissionId") == submission_id), {})
        opponent = next((agent for agent in agents if agent.get("id") != target.get("id")), {})
        replay_path = REPLAYS_DIR / f"episode_{episode_id}.json"
        if episode_id and not replay_path.exists():
            ok = download_replay(opener, int(episode_id), replay_path)
            time.sleep(0.08)
        else:
            ok = replay_path.exists()
        row = {
            "submission_id": submission_id,
            "episode_id": episode_id,
            "create_time": episode.get("createTime", ""),
            "end_time": episode.get("endTime", ""),
            "state": episode.get("state", ""),
            "type": episode.get("type", ""),
            "target_reward": target.get("reward", ""),
            "target_initial_score": target.get("initialScore", ""),
            "target_updated_score": target.get("updatedScore", ""),
            "target_team": teams.get(target.get("teamId"), {}).get("teamName", ""),
            "opponent_team": teams.get(opponent.get("teamId"), {}).get("teamName", ""),
            "opponent_submission_id": opponent.get("submissionId", ""),
            "opponent_reward": opponent.get("reward", ""),
            "opponent_initial_score": opponent.get("initialScore", ""),
            "opponent_updated_score": opponent.get("updatedScore", ""),
            "replay_path": str(replay_path.relative_to(ROOT)) if episode_id else "",
            "replay_downloaded": bool(ok),
        }
        target_rows.append(row)
        all_rows.append(row)
    fields = list(target_rows[0]) if target_rows else ["submission_id", "episode_id"]
    with (submission_dir / "episodes.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(target_rows)
    print(f"[{index}/{len(selected)}] submission={submission_id} episodes={len(target_rows)}")
    time.sleep(0.15)

fields = list(all_rows[0]) if all_rows else ["submission_id", "episode_id"]
with (ROOT / "all_submission_episodes.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    writer.writerows(all_rows)

unique_episode_ids = sorted({int(row["episode_id"]) for row in all_rows if row.get("episode_id")})
replay_files = sorted(REPLAYS_DIR.glob("episode_*.json"))
manifest = {
    "generated_at_utc": datetime.utcnow().isoformat() + "Z",
    "competition": "pokemon-tcg-ai-battle",
    "selection_rule": "filename contains archaludon, filename contains rule3v3, or exact generic submission.tar.gz",
    "selected_submission_count": len(selected),
    "selected_submission_ids": [int(item.ref) for item in selected],
    "all_episode_rows": len(all_rows),
    "unique_episode_ids": len(unique_episode_ids),
    "replay_file_count": len(replay_files),
    "list_episode_failures": failures,
    "files": {},
}
for path in [ROOT / "submission_metadata.json", ROOT / "all_submission_episodes.csv"] + replay_files:
    digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    manifest["files"][str(path.relative_to(ROOT))] = {
        "sha256": digest,
        "bytes": path.stat().st_size,
    }
(ROOT / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({
    "selected_submissions": len(selected),
    "all_episode_rows": len(all_rows),
    "unique_episode_ids": len(unique_episode_ids),
    "replay_files": len(replay_files),
    "failures": failures,
}, ensure_ascii=False))
