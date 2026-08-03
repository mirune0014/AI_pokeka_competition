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
    / "archaludon"
    / "implementation"
    / "archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2"
    / "run_union_replay_shadow.py"
)
SOURCE_RUNNER_SHA256 = (
    "9912B36D166FED9314CDCF4778C2950950E32F13D764E1ADA2545D24688AC9E9"
)
CANDIDATE_MAIN = (
    ROOT
    / "archaludon"
    / "candidates"
    / "archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2"
    / "main.py"
)
CANDIDATE_SHA256 = (
    "DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8"
)
OLD_CSV = (
    ROOT
    / "archaludon"
    / "live"
    / "55083165"
    / "refresh_20260730_0724"
    / "submission_55083165_20260730_0724_episodes.csv"
)
OLD_CSV_SHA256 = (
    "183D47E34201562C8F58B0812C2A42C4DFFE25056DF3D95B8F9A57C4C2259327"
)
NEW_CSV = (
    ROOT
    / "archaludon"
    / "live"
    / "55083165"
    / "refresh_20260730_0756"
    / "submission_55083165_20260730_0756_episodes.csv"
)
NEW_CSV_SHA256 = (
    "750A6192D95BF53CFB33B8A9EBFD263A9E9E4378B9CD0A3FE4CAA88EA09513D9"
)
REPLAY_DIR = NEW_CSV.parent
EXPECTED_NEW_IDS = {88876193}
EXPECTED_REPLAY_SHA256 = {
    88876193: "6402F4863863254A7624227EC6998E16C1A3DB326988D56DB48B21362A99AC9D"
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
for row in new_rows:
    episode = int(row["episode_id"])
    path = REPLAY_DIR / f"episode_{episode}_replay.json"
    if sha256(path) != EXPECTED_REPLAY_SHA256[episode]:
        raise AssertionError(("replay changed", episode))
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
            "population": "hero_new1_0756",
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
    "frozen_cumulative_union_shadow_new1_0756",
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
