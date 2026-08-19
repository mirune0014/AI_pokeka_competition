from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import secrets
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


REPLAY_NAME = re.compile(r"^episode_([1-9][0-9]*)_replay\.json$")
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def read_json_object(path: Path) -> Tuple[bytes, Dict[str, Any]]:
    if not path.is_file() or path.is_symlink():
        raise ValueError("JSON source must be one regular non-symlink file: {0}".format(path))
    payload = path.read_bytes()
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("malformed UTF-8 JSON: {0}".format(path)) from error
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object: {0}".format(path))
    return payload, value


def exact_positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("{0} must be an exact positive integer".format(label))
    return value


def episode_ids_for_submission(document: Dict[str, Any], submission_id: int) -> Tuple[int, ...]:
    submissions = document.get("submissions")
    episodes = document.get("episodes")
    if not isinstance(submissions, list) or not isinstance(episodes, list):
        raise ValueError("episode metadata must contain list-valued submissions and episodes")

    matching_submissions = [
        row
        for row in submissions
        if isinstance(row, dict) and row.get("id") == submission_id
    ]
    if len(matching_submissions) != 1:
        raise ValueError("metadata must contain the requested submission exactly once")
    if matching_submissions[0].get("status") != "COMPLETE":
        raise ValueError("requested submission metadata is not COMPLETE")

    episode_ids: List[int] = []
    for index, episode in enumerate(episodes):
        if not isinstance(episode, dict):
            raise ValueError("episode row {0} is not an object".format(index))
        episode_id = exact_positive_int(episode.get("id"), "episode id")
        if episode.get("state") != "COMPLETED":
            raise ValueError("episode {0} is not COMPLETED".format(episode_id))
        episode_type = episode.get("type")
        if episode_type not in (
            "EPISODE_TYPE_PUBLIC",
            "EPISODE_TYPE_VALIDATION",
        ):
            raise ValueError(
                "episode {0} has unsupported type {1!r}".format(
                    episode_id, episode_type
                )
            )
        agents = episode.get("agents")
        if (
            not isinstance(agents, list)
            or len(agents) != 2
            or any(not isinstance(agent, dict) for agent in agents)
        ):
            raise ValueError("episode {0} must contain two agent objects".format(episode_id))
        target_agents = [
            agent
            for agent in agents
            if agent.get("submissionId") == submission_id
        ]
        expected_target_agents = 1 if episode_type == "EPISODE_TYPE_PUBLIC" else 2
        if len(target_agents) != expected_target_agents:
            raise ValueError(
                "episode {0} has {1} target agents; expected {2} for {3}".format(
                    episode_id,
                    len(target_agents),
                    expected_target_agents,
                    episode_type,
                )
            )
        episode_ids.append(episode_id)

    if not episode_ids:
        raise ValueError("episode metadata is empty")
    if len(episode_ids) != len(set(episode_ids)):
        raise ValueError("episode metadata contains duplicate episode IDs")
    return tuple(sorted(episode_ids))


def replay_sources(
    replay_dir: Path,
    episode_ids: Sequence[int],
) -> Tuple[Tuple[str, Path, bytes], ...]:
    if not replay_dir.is_dir() or replay_dir.is_symlink():
        raise ValueError("replay directory must be a regular directory: {0}".format(replay_dir))

    actual: Dict[int, Path] = {}
    unexpected_names: List[str] = []
    for path in sorted(replay_dir.glob("episode_*_replay.json"), key=lambda value: value.name):
        match = REPLAY_NAME.fullmatch(path.name)
        if match is None:
            unexpected_names.append(path.name)
            continue
        episode_id = int(match.group(1))
        if episode_id in actual:
            raise ValueError("duplicate replay filename for episode {0}".format(episode_id))
        if not path.is_file() or path.is_symlink():
            raise ValueError("replay must be one regular non-symlink file: {0}".format(path))
        actual[episode_id] = path

    expected = set(episode_ids)
    actual_ids = set(actual)
    missing = sorted(expected - actual_ids)
    extra = sorted(actual_ids - expected)
    if unexpected_names or missing or extra:
        raise ValueError(
            "replay closure mismatch: unexpected_names={0}, missing={1}, extra={2}".format(
                unexpected_names, missing, extra
            )
        )

    rows: List[Tuple[str, Path, bytes]] = []
    for episode_id in sorted(expected):
        path = actual[episode_id]
        payload, replay = read_json_object(path)
        replay_info = replay.get("info")
        if not isinstance(replay_info, dict):
            raise ValueError("replay has no info object: {0}".format(path))
        replay_id = exact_positive_int(replay_info.get("EpisodeId"), "replay info.EpisodeId")
        if replay_id != episode_id:
            raise ValueError(
                "replay root id {0} does not match filename episode {1}".format(
                    replay_id, episode_id
                )
            )
        steps = replay.get("steps")
        statuses = replay.get("statuses")
        if not isinstance(steps, list) or not steps:
            raise ValueError("replay has no completed step history: {0}".format(path))
        if (
            not isinstance(statuses, list)
            or len(statuses) != 2
            or any(not isinstance(status, str) for status in statuses)
            or any(status in ("ACTIVE", "INACTIVE") for status in statuses)
        ):
            raise ValueError("replay has a non-terminal status vector: {0}".format(path))
        rows.append((path.name, path, payload))
    return tuple(rows)


def zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def build_zip(sources: Sequence[Tuple[str, Path, bytes]]) -> bytes:
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, _, payload in sorted(sources, key=lambda value: value[0]):
            archive.writestr(
                zip_info(name),
                payload,
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
    return raw.getvalue()


def file_rows(sources: Sequence[Tuple[str, Path, bytes]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for name, _, payload in sorted(sources, key=lambda value: value[0]):
        rows.append(
            {
                "bytes": len(payload),
                "file": name,
                "sha256": sha256_bytes(payload),
            }
        )
    return rows


def verify_zip(payload: bytes, rows: Sequence[Dict[str, Any]]) -> None:
    expected_names = [str(row["file"]) for row in rows]
    with zipfile.ZipFile(io.BytesIO(payload), mode="r") as archive:
        infos = archive.infolist()
        if [info.filename for info in infos] != expected_names:
            raise AssertionError("ZIP entries are not the exact sorted source closure")
        if any(
            info.is_dir()
            or info.date_time != FIXED_ZIP_TIME
            or info.create_system != 3
            or info.external_attr != 0o100644 << 16
            or info.compress_type != zipfile.ZIP_DEFLATED
            for info in infos
        ):
            raise AssertionError("ZIP entry metadata is not canonical")
        for info, row in zip(infos, rows):
            content = archive.read(info)
            if len(content) != row["bytes"] or sha256_bytes(content) != row["sha256"]:
                raise AssertionError("ZIP entry content mismatch: {0}".format(info.filename))


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def stage_payload(destination: Path, payload: bytes) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = destination.with_name(
        ".{0}.{1}.{2}.pending".format(
            destination.name,
            os.getpid(),
            secrets.token_hex(8),
        )
    )
    write_new(staged, payload)
    return staged


def publish_pair(
    out_zip: Path,
    zip_payload: bytes,
    manifest_path: Path,
    manifest_payload: bytes,
) -> None:
    staged_zip = None
    staged_manifest = None
    published: List[Path] = []
    try:
        staged_zip = stage_payload(out_zip, zip_payload)
        staged_manifest = stage_payload(manifest_path, manifest_payload)
        os.link(staged_zip, out_zip)
        published.append(out_zip)
        os.link(staged_manifest, manifest_path)
        published.append(manifest_path)
    except Exception:
        for path in reversed(published):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise
    finally:
        for path in (staged_zip, staged_manifest):
            if path is None:
                continue
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and deterministically bundle one complete Kaggle submission replay snapshot."
    )
    parser.add_argument("--submission-id", type=int, required=True)
    parser.add_argument("--episodes-json", type=Path, required=True)
    parser.add_argument("--replay-dir", type=Path)
    parser.add_argument("--out-zip", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    submission_id = exact_positive_int(args.submission_id, "submission id")
    replay_argument = args.replay_dir or args.episodes_json.parent
    for label, path in (
        ("episodes JSON", args.episodes_json),
        ("replay directory", replay_argument),
        ("ZIP destination", args.out_zip),
        ("manifest destination", args.manifest),
    ):
        if path.is_symlink():
            raise ValueError("{0} may not be a symlink: {1}".format(label, path))
    episodes_json = args.episodes_json.resolve()
    replay_dir = replay_argument.resolve()
    out_zip = args.out_zip.resolve()
    manifest_path = args.manifest.resolve()
    if out_zip == manifest_path:
        raise ValueError("ZIP and manifest destinations must differ")
    if out_zip.exists() or manifest_path.exists():
        raise FileExistsError("bundle destinations must not already exist")
    for destination in (out_zip, manifest_path):
        if destination.parent.resolve() == replay_dir:
            raise ValueError("bundle destinations must be outside the replay directory")

    metadata_payload, document = read_json_object(episodes_json)
    episode_ids = episode_ids_for_submission(document, submission_id)
    replay_rows = replay_sources(replay_dir, episode_ids)
    sources = tuple(
        sorted(
            replay_rows + ((episodes_json.name, episodes_json, metadata_payload),),
            key=lambda value: value[0],
        )
    )
    if len({name for name, _, _ in sources}) != len(sources):
        raise ValueError("bundle source names are not unique")
    if out_zip in {path.resolve() for _, path, _ in sources} or manifest_path in {
        path.resolve() for _, path, _ in sources
    }:
        raise ValueError("bundle destination overlaps a source file")

    rows = file_rows(sources)
    if rows[-1]["file"] != episodes_json.name and not any(
        row["file"] == episodes_json.name for row in rows
    ):
        raise AssertionError("raw episode metadata is absent from bundle closure")
    metadata_row = next(row for row in rows if row["file"] == episodes_json.name)
    if metadata_row["bytes"] != len(metadata_payload) or metadata_row["sha256"] != sha256_bytes(
        metadata_payload
    ):
        raise AssertionError("raw episode metadata changed during validation")

    zip_payload = build_zip(sources)
    verify_zip(zip_payload, rows)
    manifest = {
        "schema_version": "kaggle_submission_replay_bundle_v1",
        "submission_id": submission_id,
        "episode_count": len(episode_ids),
        "episode_ids": list(episode_ids),
        "entry_count": len(rows),
        "files": rows,
        "zip": {
            "bytes": len(zip_payload),
            "compression": "deflate-9",
            "entry_time": "1980-01-01T00:00:00",
            "file": out_zip.name,
            "sha256": sha256_bytes(zip_payload),
        },
    }
    manifest_payload = json_bytes(manifest)
    publish_pair(out_zip, zip_payload, manifest_path, manifest_payload)
    print(
        json.dumps(
            {
                "status": "COMPLETE",
                "submission_id": submission_id,
                "episodes": len(episode_ids),
                "entries": len(rows),
                "zip": str(out_zip),
                "zip_sha256": sha256_bytes(zip_payload),
                "manifest": str(manifest_path),
                "manifest_sha256": sha256_bytes(manifest_payload),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)
