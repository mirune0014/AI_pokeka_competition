from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKET = ROOT / "GPT_PRO_REVIEW_PACKET.zip"
names = [
    "GPT_PRO_BRIEF.md",
    "submission_overview.csv",
    "all_submission_episodes.csv",
    "submission_metadata.json",
    "COLLECTION_MANIFEST.json",
]
for path in sorted((ROOT / "submissions").glob("*/episodes.json")):
    names.append(str(path.relative_to(ROOT)))

loss_targets = {55422059, 55383153, 54738887, 54757713, 55120278, 55126164}
with (ROOT / "all_submission_episodes.csv").open(encoding="utf-8", newline="") as handle:
    rows = list(csv.DictReader(handle))
selected_replay_ids = []
for submission_id in sorted(loss_targets):
    losses = [
        row
        for row in rows
        if int(row["submission_id"]) == submission_id
        and str(row.get("target_reward", "")) == "-1"
        and row.get("replay_downloaded") == "True"
    ]
    selected_replay_ids.extend(int(row["episode_id"]) for row in losses[:4])
for episode_id in selected_replay_ids:
    replay = ROOT / "replays" / f"episode_{episode_id}.json"
    if replay.exists() and replay.stat().st_size > 0:
        names.append(str(replay.relative_to(ROOT)))

with zipfile.ZipFile(PACKET, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for name in names:
        path = ROOT / name
        if path.exists() and path.stat().st_size > 0:
            archive.write(path, arcname=name)
    archive.writestr(
        "PACKET_README.md",
        (
            "# GPT PRO review packet\n\n"
            "This packet contains the authoritative submission/episode indexes, "
            "all per-submission ListEpisodes JSONs downloaded before the user "
            "stopped collection, and representative loss replays from current "
            "and historical high-score Archaludon submissions. The complete raw "
            "replay set remains under the sibling replays directory; it is "
            "intentionally not embedded because it is approximately 5 GB.\n"
        ),
    )
print(json.dumps({"packet": str(PACKET), "bytes": PACKET.stat().st_size, "sample_replays": len(selected_replay_ids)}))
