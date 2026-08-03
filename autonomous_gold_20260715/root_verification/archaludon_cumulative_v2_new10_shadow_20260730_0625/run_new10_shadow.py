from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
SOURCE_RUNNER = (
    ROOT
    / "autonomous_gold_20260715"
    / "implementation"
    / "archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2"
    / "run_union_replay_shadow.py"
)
SOURCE_RUNNER_SHA256 = (
    "9912B36D166FED9314CDCF4778C2950950E32F13D764E1ADA2545D24688AC9E9"
)
CANDIDATE_MAIN = (
    ROOT
    / "autonomous_gold_20260715"
    / "candidates"
    / "archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2"
    / "main.py"
)
CANDIDATE_SHA256 = (
    "DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8"
)
OLD_CSV = (
    ROOT
    / "autonomous_gold_20260715"
    / "live"
    / "55083165"
    / "refresh_20260730_0211"
    / "hero_0211_episodes.csv"
)
OLD_CSV_SHA256 = (
    "5B9176809A98FA2B8AE258DCECEBE97A56AD9DBA1E9BB3F51270EEEB86CCF682"
)
NEW_CSV = (
    ROOT
    / "autonomous_gold_20260715"
    / "live"
    / "55083165"
    / "refresh_20260730_0625"
    / "hero_0625_episodes.csv"
)
NEW_CSV_SHA256 = (
    "D63E9921C8CADC926F05ACA0E6F662E8A1EA4181BC938FCD8C9A04D51EED9081"
)
REPLAY_DIR = NEW_CSV.parent
EXPECTED_NEW_IDS = {
    88842275,
    88843696,
    88844385,
    88846066,
    88851544,
    88853935,
    88857786,
    88861441,
    88861800,
    88867768,
}


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def csv_rows(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


for path, expected in (
    (SOURCE_RUNNER, SOURCE_RUNNER_SHA256),
    (CANDIDATE_MAIN, CANDIDATE_SHA256),
    (OLD_CSV, OLD_CSV_SHA256),
    (NEW_CSV, NEW_CSV_SHA256),
):
    if sha256(path) != expected:
        raise AssertionError(("frozen input changed", path))

old_ids = {int(row["episode_id"]) for row in csv_rows(OLD_CSV)}
new_rows = [
    row
    for row in csv_rows(NEW_CSV)
    if int(row["episode_id"]) not in old_ids
]
if {int(row["episode_id"]) for row in new_rows} != EXPECTED_NEW_IDS:
    raise AssertionError("new episode set changed")

sources = []
expected_callbacks = 0
for row in sorted(new_rows, key=lambda item: int(item["episode_id"])):
    episode = int(row["episode_id"])
    path = REPLAY_DIR / f"episode_{episode}_replay.json"
    replay = json.loads(path.read_text(encoding="utf-8"))
    if int(replay["info"]["EpisodeId"]) != episode:
        raise AssertionError(("episode mismatch", episode))
    names = replay["info"]["TeamNames"]
    if names.count("rurumi") != 1:
        raise AssertionError(("target team missing", episode, names))
    seat = names.index("rurumi")
    reward = replay["rewards"][seat]
    if str(reward) != row["target_reward"]:
        raise AssertionError(("reward mismatch", episode, reward, row))
    for step in replay["steps"]:
        record = step[seat]
        raw = record.get("observation")
        if (
            record.get("status") != "ACTIVE"
            or not raw
            or not raw.get("select")
        ):
            continue
        if (
            not raw["select"].get("option")
            and raw["select"].get("minCount", 0) > 0
        ):
            continue
        expected_callbacks += 1
    sources.append(
        {
            "population": "hero_new10",
            "episode": episode,
            "seat": seat,
            "reward": reward,
            "filename": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "path": path,
        }
    )

spec = importlib.util.spec_from_file_location(
    "frozen_cumulative_union_shadow",
    SOURCE_RUNNER,
)
if spec is None or spec.loader is None:
    raise AssertionError("unable to load frozen union-shadow runner")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.HERE = HERE
module.EXPECTED_CALLBACKS = expected_callbacks
module.source_rows = lambda: list(sources)
module.main()
