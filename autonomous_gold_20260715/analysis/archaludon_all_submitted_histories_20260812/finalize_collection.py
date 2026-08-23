from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUBMISSIONS = ROOT / "submissions"
REPLAYS = ROOT / "replays"

metadata = json.loads((ROOT / "submission_metadata.json").read_text(encoding="utf-8"))
metadata_by_id = {int(item["submission_id"]): item for item in metadata}
rows = []
processed_ids = []
failed_json = []
for submission_dir in sorted(SUBMISSIONS.iterdir(), key=lambda path: int(path.name)):
    if not submission_dir.is_dir() or not submission_dir.name.isdigit():
        continue
    submission_id = int(submission_dir.name)
    episodes_path = submission_dir / "episodes.json"
    if not episodes_path.exists():
        failed_json.append(submission_id)
        continue
    data = json.loads(episodes_path.read_text(encoding="utf-8"))
    processed_ids.append(submission_id)
    teams = {team.get("id"): team for team in data.get("teams") or []}
    for episode in data.get("episodes") or []:
        episode_id = episode.get("id")
        agents = episode.get("agents") or []
        target = next((agent for agent in agents if agent.get("submissionId") == submission_id), {})
        opponent = next((agent for agent in agents if agent.get("id") != target.get("id")), {})
        replay_path = REPLAYS / f"episode_{episode_id}.json"
        rows.append(
            {
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
                "replay_downloaded": replay_path.exists() and replay_path.stat().st_size > 0,
            }
        )

fields = list(rows[0]) if rows else ["submission_id", "episode_id"]
with (ROOT / "all_submission_episodes.csv").open("w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

overview = []
for submission_id, item in metadata_by_id.items():
    own_rows = [row for row in rows if int(row["submission_id"]) == submission_id]
    replay_ids = {int(row["episode_id"]) for row in own_rows if row.get("episode_id") and row["replay_downloaded"]}
    overview.append(
        {
            "submission_id": submission_id,
            "date": item.get("date", ""),
            "status": item.get("status", ""),
            "public_score": item.get("public_score", ""),
            "file_name": item.get("file_name", ""),
            "classification": item.get("classification", ""),
            "episodes_listed": len(own_rows),
            "replays_downloaded": len(replay_ids),
            "raw_json_present": (SUBMISSIONS / str(submission_id) / "episodes.json").exists(),
            "fully_processed_before_stop": (SUBMISSIONS / str(submission_id) / "episodes.csv").exists(),
        }
    )
with (ROOT / "submission_overview.csv").open("w", encoding="utf-8", newline="") as handle:
    fields = list(overview[0]) if overview else []
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    writer.writerows(overview)

zero_length_replay_files = sorted(
    path for path in REPLAYS.glob("episode_*.json") if path.stat().st_size == 0
)
replay_files = sorted(
    path for path in REPLAYS.glob("episode_*.json") if path.stat().st_size > 0
)
unique_ids = sorted({int(row["episode_id"]) for row in rows if row.get("episode_id")})
downloaded_ids = sorted({int(path.stem.split("_")[-1]) for path in replay_files})
unprocessed_ids = sorted(set(metadata_by_id) - set(processed_ids))
missing_replays = sorted(
    (set(unique_ids) - set(downloaded_ids))
    | {int(path.stem.split("_")[-1]) for path in zero_length_replay_files}
)

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()

packet = {
    "title": "Archaludon submitted-history collection (stopped on user request)",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "competition": "pokemon-tcg-ai-battle",
    "selection_rule": metadata and "filename contains archaludon, filename contains rule3v3, or exact generic submission.tar.gz",
    "selected_submission_count": len(metadata),
    "processed_submission_count": len(processed_ids),
    "unprocessed_submission_ids": unprocessed_ids,
    "episode_rows_listed": len(rows),
    "unique_episode_ids_listed": len(unique_ids),
    "replay_files_downloaded": len(replay_files),
    "zero_length_replay_files": [str(path.relative_to(ROOT)) for path in zero_length_replay_files],
    "missing_replay_ids_from_listed_episodes": missing_replays,
    "replay_bytes": sum(path.stat().st_size for path in replay_files),
    "replay_content_sha256": "not computed for the 5GB raw set; each file remains unmodified and is indexed by path/size",
    "caution": "High historical scores are not causal proof; older agents/opponent pool and validation/public sample differ. GPT PRO must separate opponent-population, sample-size, deck, and policy effects before recommending changes.",
    "files": {},
}
for path in [ROOT / "submission_metadata.json", ROOT / "all_submission_episodes.csv", ROOT / "submission_overview.csv"]:
    packet["files"][str(path.relative_to(ROOT))] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
(ROOT / "COLLECTION_MANIFEST.json").write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")

brief = f"""# GPT PRO brief: Archaludon submitted histories

Collection stopped at the user's request after the current partial set was preserved.

- Selected by API metadata: **{len(metadata)}** Archaludon-labelled submissions (plus historical `rule3v3` and the ambiguous `submission.tar.gz`).
- Fully processed before stop: **{len(processed_ids)}** submissions.
- Unprocessed submission IDs: `{', '.join(map(str, unprocessed_ids))}`.
- Episode rows listed for processed submissions: **{len(rows)}**; unique episode IDs: **{len(unique_ids)}**.
- Full replay JSONs downloaded: **{len(replay_files)}**; total raw size: **{sum(path.stat().st_size for path in replay_files):,} bytes**.
- Listed episodes without a downloaded replay: **{len(missing_replays)}**.

The complete raw set is under `replays/`. Per-submission raw `ListEpisodes` JSONs are under `submissions/`. The authoritative index and hashes are in `COLLECTION_MANIFEST.json` and `submission_overview.csv`.

## Interpretation guard

Do not treat an old high public score as proof that its policy is stronger: older submissions faced a different opponent pool, different time, and different sample size; some were exploratory or RL-labelled. Separate deck identity, opponent distribution, validation/public variance, and actual policy changes. The currently accepted Lillie safety fix is a rare safety repair, not evidence of a global win-rate gain.
"""
(ROOT / "GPT_PRO_BRIEF.md").write_text(brief, encoding="utf-8")
print(json.dumps({
    "selected_submissions": len(metadata),
    "processed_submissions": len(processed_ids),
    "unprocessed_submissions": len(unprocessed_ids),
    "episode_rows": len(rows),
    "unique_episode_ids": len(unique_ids),
    "replay_files": len(replay_files),
    "missing_replays": len(missing_replays),
}, ensure_ascii=False))
