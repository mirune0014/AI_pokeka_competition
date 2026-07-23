"""Bounded, reproducible construction of Phase 1 Gold replay data."""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import uuid
from typing import Any, Iterable, Mapping, Sequence

from .replay_records import ReplayDecisionRecord, read_jsonl
from .replay_reconstruction import group_replay_transactions, iter_replay_decisions
from .split_manifest import DEFAULT_COMPONENT_FIELDS, SPLITS, SplitItem, build_split_manifest, load_split_manifest, write_split_manifest


SCHEMA_VERSION = "gold_replay_dataset.v1"
ARTIFACTS = ("decision_records.jsonl", "retrospective_transactions.jsonl", "split_manifest.json", "dataset_manifest.json")
REQUIRED_SEAT_COLUMNS = frozenset({"episode_id", "file", "player_index", "team", "reward", "archetype", "deck_id", "deck"})
REQUIRED_SELECTION_COLUMNS = frozenset({
    "episode_id", "player_index", "team", "gold_rank", "gold_score", "team_id",
    "last_submission_date_utc", "submission_version_proxy", "gold_snapshot_sha256",
    "gold_snapshot_path", "gold_snapshot_timestamp_utc", "gold_proxy_confidence",
    "match_timestamp_utc", "replay_sha256", "file",
})


def _json_bytes(value: Any, *, indent: int | None = None) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":") if indent is None else None,
                       ensure_ascii=True, indent=indent) + "\n").encode("ascii")


def _split_bytes(value: Any) -> bytes:
    """Match split_manifest.write_split_manifest's platform text serialization."""
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("ascii").replace(b"\n", os.linesep.encode("ascii"))


def _hash_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _read_json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read replay {path}: {error}") from error
    if not isinstance(value, Mapping):
        raise ValueError(f"replay {path} is not a JSON object")
    return value


def _portable(path: Path, *, workspace: Path, input_root: Path) -> str:
    resolved = path.resolve()
    for root in (workspace.resolve(), input_root.resolve()):
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            pass
    return path.name


def _field(row: Mapping[str, str], *names: str) -> str:
    lowered = {key.lower(): value for key, value in row.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value is not None:
            return value.strip()
    return ""


def _leaderboard(path: Path) -> tuple[dict[str, dict[str, str]], list[dict[str, str]]]:
    raw = path.read_bytes()
    try:
        rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines()))
    except (UnicodeDecodeError, csv.Error) as error:
        raise ValueError(f"could not read leaderboard CSV: {error}") from error
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        team = _field(row, "TeamName", "team", "team_name")
        rank = _field(row, "Rank", "rank", "ranking")
        if not team or not rank:
            continue
        try:
            parsed_rank = int(rank)
        except ValueError:
            continue
        normalized = {str(k): "" if v is None else str(v) for k, v in row.items()}
        normalized["rank"] = str(parsed_rank)
        if team in result and result[team]["rank"] != normalized["rank"]:
            raise ValueError(f"leaderboard has conflicting ranks for team {team!r}")
        result[team] = normalized
    if not result:
        raise ValueError("leaderboard CSV has no rows with team and rank")
    return result, rows


def _seat_rows(path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))
    if not rows or not REQUIRED_SEAT_COLUMNS.issubset(rows[0]):
        raise ValueError("seat metadata CSV is missing required decks.csv columns")
    return [{str(key): "" if value is None else str(value) for key, value in row.items()} for row in rows]


def _selection_rows(path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))
    if not rows or not REQUIRED_SELECTION_COLUMNS.issubset(rows[0]):
        raise ValueError("Gold selection CSV is missing required frozen-catalog columns")
    normalized = [{str(key): "" if value is None else str(value) for key, value in row.items()} for row in rows]
    keys = [(row["episode_id"], row["player_index"]) for row in normalized]
    if len(set(keys)) != len(keys):
        raise ValueError("Gold selection CSV has duplicate episode/seat rows")
    return normalized


def _episode_id(replay: Mapping[str, Any]) -> str:
    info = replay.get("info") if isinstance(replay.get("info"), Mapping) else {}
    return str(info.get("EpisodeId") or replay.get("episode_id") or replay.get("EpisodeId") or "unknown")


def _uuid_timestamp(replay: Mapping[str, Any]) -> str | None:
    info = replay.get("info") if isinstance(replay.get("info"), Mapping) else {}
    for value in (replay.get("id"), replay.get("replay_id"), replay.get("replayId"), info.get("id"), info.get("ReplayId"), info.get("EpisodeId")):
        try:
            parsed = uuid.UUID(str(value))
        except (ValueError, AttributeError, TypeError):
            continue
        if parsed.version == 1:
            unix_ticks = parsed.time - 0x01B21DD213814000
            seconds, remaining_ticks = divmod(unix_ticks, 10_000_000)
            return (
                datetime(1970, 1, 1, tzinfo=timezone.utc)
                + timedelta(seconds=seconds, microseconds=remaining_ticks // 10)
            ).isoformat()
    return None


def _seed(replay: Mapping[str, Any]) -> str:
    for container in (replay.get("configuration"), replay.get("config"), replay.get("info")):
        if isinstance(container, Mapping) and container.get("seed") is not None:
            return str(container["seed"])
    return "unknown"


def _deck_variant(deck: str) -> str:
    cards = deck.split()
    if len(cards) != 60:
        raise ValueError(f"deck must contain exactly 60 cards, got {len(cards)}")
    return _hash_bytes(_json_bytes(sorted(cards)))


def _submission_proxy(leader: Mapping[str, str]) -> str:
    team_id = _field(leader, "TeamId", "team_id", "id")
    submitted = _field(leader, "LastSubmissionDate", "last_submission_date")
    if not team_id or not submitted:
        raise ValueError("selected leaderboard team is missing TeamId or LastSubmissionDate for submission proxy")
    return f"team:{team_id}:last_submission:{submitted}"


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # Kaggle leaderboard CSV timestamps are UTC even when the offset is
        # omitted. Treating them as the Windows host timezone moves the
        # submission boundary by nine hours on the current JST workstation.
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError as error:
        raise ValueError("selected leaderboard team has an invalid LastSubmissionDate") from error


def _terminal(replay: Mapping[str, Any], reward: str) -> dict[str, Any]:
    rewards = replay.get("rewards")
    winner = None
    if isinstance(rewards, list) and rewards:
        try:
            values = [float(value) for value in rewards]
            maximum = max(values)
            winners = [index for index, value in enumerate(values) if value == maximum]
            winner = winners[0] if len(winners) == 1 else None
        except (TypeError, ValueError):
            pass
    return {"winner_seat": winner, "seat_reward": reward}


def _replay_paths(inputs: Sequence[str | Path]) -> tuple[list[Path], Path]:
    paths: list[Path] = []
    roots: list[Path] = []
    for raw in inputs:
        path = Path(raw)
        if path.is_dir():
            roots.append(path)
            paths.extend(sorted(candidate for candidate in path.rglob("*.json") if candidate.is_file()))
        elif path.is_file():
            roots.append(path.parent)
            paths.append(path)
        else:
            raise FileNotFoundError(f"replay input does not exist: {path}")
    if not paths:
        raise ValueError("no replay JSON files found")
    return sorted(set(paths), key=lambda path: str(path).lower()), min(roots, key=lambda path: len(path.parts))


def build_gold_replay_dataset(
    replay_inputs: Sequence[str | Path], *, seat_metadata_csv: str | Path,
    leaderboard_csv: str | Path | None = None, gold_selection_csv: str | Path | None = None,
    output_dir: str | Path, gold_rank_max: int = 20, split_seed: str = "gold-replay-v1",
    holdout_style_families: Iterable[str] = (), blind_date_periods: Iterable[str] = (),
    development_date_periods: Iterable[str] = (), component_fields: Iterable[str] = DEFAULT_COMPONENT_FIELDS,
    development_fraction: float = 0.15, blind_fraction: float = 0.15,
    workspace: str | Path | None = None,
) -> dict[str, Any]:
    """Build the immutable Gold artifacts and return their compact audit summary."""
    if gold_rank_max < 1:
        raise ValueError("gold_rank_max must be positive")
    workspace_path = Path(workspace) if workspace is not None else Path.cwd()
    if (leaderboard_csv is None) == (gold_selection_csv is None):
        raise ValueError("provide exactly one of leaderboard_csv or gold_selection_csv")

    leaders: dict[str, dict[str, str]] = {}
    frozen_selections: dict[tuple[str, int], dict[str, str]] = {}
    leaderboard_hash: str | None = None
    selection_catalog_hash: str | None = None
    selection_catalog_rows: list[dict[str, str]] = []
    if leaderboard_csv is not None:
        leaders, _ = _leaderboard(Path(leaderboard_csv))
        leaderboard_hash = _hash_bytes(Path(leaderboard_csv).read_bytes())
        selection_source: dict[str, Any] = {
            "mode": "single_leaderboard_snapshot",
            "path": str(Path(leaderboard_csv)),
            "sha256": leaderboard_hash,
            "selection_provenance": "gold_snapshot_proxy",
        }
    else:
        selection_path = Path(gold_selection_csv)
        selection_catalog_rows = _selection_rows(selection_path)
        selection_catalog_hash = _hash_bytes(selection_path.read_bytes())
        frozen_selections = {
            (row["episode_id"], int(row["player_index"])): row
            for row in selection_catalog_rows
        }
        selection_source = {
            "mode": "frozen_gold_selection_catalog",
            "path": str(selection_path),
            "sha256": selection_catalog_hash,
            "snapshot_sha256s": sorted({row["gold_snapshot_sha256"] for row in selection_catalog_rows}),
            "selection_provenance": "gold_snapshot_proxy",
        }
        if not replay_inputs:
            replay_inputs = tuple(
                sorted({
                    str((workspace_path / row["file"]).resolve())
                    if not Path(row["file"]).is_absolute() else row["file"]
                    for row in selection_catalog_rows
                })
            )

    replay_paths, input_root = _replay_paths(replay_inputs)
    selection_source["path"] = _portable(
        Path(leaderboard_csv if leaderboard_csv is not None else gold_selection_csv),
        workspace=workspace_path,
        input_root=input_root,
    )
    seats = _seat_rows(Path(seat_metadata_csv))
    seats_by_episode: dict[str, list[dict[str, str]]] = defaultdict(list)
    for seat in seats:
        seats_by_episode[seat["episode_id"]].append(seat)

    replays: dict[str, tuple[Path, Mapping[str, Any], str]] = {}
    source_rows: list[dict[str, Any]] = []
    for path in replay_paths:
        raw = path.read_bytes()
        replay, digest, episode = _read_json(path), _hash_bytes(raw), None
        episode = _episode_id(replay)
        existing = replays.get(episode)
        if existing is not None:
            if existing[2] != digest:
                raise ValueError(f"conflicting checksums for episode {episode}")
            continue
        replays[episode] = (path, replay, digest)
        source_rows.append({"path": _portable(path, workspace=workspace_path, input_root=input_root), "sha256": digest,
                            "mtime_ns": path.stat().st_mtime_ns, "episode_id": episode,
                            "uuid_v1_timestamp": _uuid_timestamp(replay), "seed": _seed(replay)})

    records: list[ReplayDecisionRecord] = []
    transactions: list[dict[str, Any]] = []
    selected_seats: list[dict[str, Any]] = []
    skips: Counter[str] = Counter()
    for episode, (path, replay, digest) in sorted(replays.items()):
        episode_seats = {int(row["player_index"]): row for row in seats_by_episode.get(episode, []) if row["player_index"].strip().lstrip("-").isdigit()}
        for seat_index, row in sorted(episode_seats.items()):
            opponent = next((item for index, item in episode_seats.items() if index != seat_index), None)
            timestamp = _uuid_timestamp(replay)
            if timestamp is None:
                skips["replay_uuid_v1_timestamp_missing"] += 1
                continue
            try:
                variant = _deck_variant(row["deck"])
            except ValueError as error:
                skips[str(error)] += 1
                continue

            frozen = frozen_selections.get((episode, seat_index)) if gold_selection_csv is not None else None
            if gold_selection_csv is not None:
                if frozen is None:
                    skips["not_in_frozen_gold_selection"] += 1
                    continue
                if frozen["team"] != row["team"]:
                    raise ValueError(f"Gold selection team mismatch for episode {episode} seat {seat_index}")
                if frozen["replay_sha256"].lower() != digest.lower():
                    raise ValueError(f"Gold selection replay checksum mismatch for episode {episode}")
                timestamp_delta = abs(_parse_timestamp(frozen["match_timestamp_utc"]) - _parse_timestamp(timestamp))
                if timestamp_delta > timedelta(microseconds=1):
                    raise ValueError(f"Gold selection match timestamp mismatch for episode {episode}")
                try:
                    selected_rank = int(frozen["gold_rank"])
                    submitted_at = _parse_timestamp(frozen["last_submission_date_utc"])
                except ValueError as error:
                    raise ValueError(f"invalid frozen Gold selection for episode {episode}: {error}") from error
                if selected_rank > gold_rank_max:
                    skips["frozen_selection_outside_rank_limit"] += 1
                    continue
                proxy = frozen["submission_version_proxy"]
                if not proxy:
                    raise ValueError(f"Gold selection submission proxy missing for episode {episode}")
                snapshot_hash = frozen["gold_snapshot_sha256"].lower()
                if len(snapshot_hash) != 64 or any(character not in "0123456789abcdef" for character in snapshot_hash):
                    raise ValueError(f"Gold selection snapshot checksum invalid for episode {episode}")
                selected_score = frozen["gold_score"]
                proxy_confidence = frozen["gold_proxy_confidence"]
                snapshot_path = frozen["gold_snapshot_path"]
                snapshot_timestamp = frozen["gold_snapshot_timestamp_utc"]
            else:
                leader = leaders.get(row["team"])
                if leader is None:
                    skips["team_not_in_leaderboard"] += 1
                    continue
                selected_rank = int(leader["rank"])
                if selected_rank > gold_rank_max:
                    skips["non_gold_team"] += 1
                    continue
                try:
                    proxy = _submission_proxy(leader)
                    submitted_at = _parse_timestamp(_field(leader, "LastSubmissionDate", "last_submission_date"))
                except ValueError as error:
                    skips[str(error)] += 1
                    continue
                snapshot_hash = str(leaderboard_hash)
                selected_score = _field(leader, "Score", "score", "publicLeaderboardScore")
                proxy_confidence = "single_snapshot_temporal_gate"
                snapshot_path = selection_source["path"]
                snapshot_timestamp = "unknown"
            if submitted_at > _parse_timestamp(timestamp):
                skips["leaderboard_submission_postdates_replay"] += 1
                continue
            portable_replay = _portable(path, workspace=workspace_path, input_root=input_root)
            metadata = {"submission_id_is_proxy": True, "leaderboard_rank": selected_rank,
                        "leaderboard_score": selected_score,
                        "leaderboard_sha256": snapshot_hash, "selection_provenance": "gold_snapshot_proxy",
                        "gold_proxy_confidence": proxy_confidence, "gold_snapshot_path": snapshot_path,
                        "gold_snapshot_timestamp_utc": snapshot_timestamp,
                        "configuration_seed": _seed(replay), "replay_sha256": digest, "deck_variant_sha256": variant,
                        "source_replay_path": portable_replay, "source_file_mtime_ns": path.stat().st_mtime_ns,
                        "match_timestamp_utc": timestamp}
            if selection_catalog_hash is not None:
                metadata["selection_catalog_sha256"] = selection_catalog_hash
            decisions = list(iter_replay_decisions(replay, seats=[seat_index]))
            if not decisions:
                skips["no_valid_decisions"] += 1
                continue
            selected_seats.append({
                "episode_id": episode,
                "seat": seat_index,
                "team": row["team"],
                "rank": selected_rank,
                "leaderboard_score": selected_score,
                "last_submission_date_utc": submitted_at.isoformat(),
                "selection_provenance": "gold_snapshot_proxy",
                "gold_proxy_confidence": proxy_confidence,
                "gold_snapshot_path": snapshot_path,
                "gold_snapshot_sha256": snapshot_hash,
                "gold_snapshot_timestamp_utc": snapshot_timestamp,
                "replay_sha256": digest,
                "source_replay_path": portable_replay,
                "match_timestamp_utc": timestamp,
                "configuration_seed": _seed(replay),
                "submission_id": proxy,
                "deck_variant": variant,
                "own_archetype": row["archetype"] or None,
                "opponent_archetype": None if opponent is None else opponent["archetype"] or None,
                "reward": row["reward"],
            })
            seat_records: list[ReplayDecisionRecord] = []
            for decision_step, decision in enumerate(decisions):
                record = ReplayDecisionRecord.from_observation(
                    decision.observation, decision.raw_action, episode_id=episode, submission_id=proxy,
                    style_id=row["team"], decision_step=decision_step, replay_step=decision.replay_step,
                    acting_seat=seat_index, own_archetype=row["archetype"] or None,
                    opponent_archetype=None if opponent is None else opponent["archetype"] or None,
                    public_history=decision.public_history,
                    private_action_history=decision.private_action_history,
                    terminal_result=_terminal(replay, row["reward"]),
                    timestamp=timestamp, source_metadata=metadata, label_source="observed_replay",
                )
                seat_records.append(record)
            records.extend(seat_records)
            by_step = {record.replay_step: record.decision_id for record in seat_records}
            for transaction in group_replay_transactions(decisions):
                children = [by_step[step] for step in transaction.replay_steps[1:] if step in by_step]
                row_data = transaction.to_dict()
                row_data["supervision_metadata"] = {"root_decision_id": by_step.get(transaction.root_replay_step), "child_decision_ids": children}
                transactions.append(row_data)

    records.sort(key=lambda record: (record.episode_id, record.acting_seat, record.replay_step, record.decision_id))
    transactions.sort(key=lambda row: row["transaction_id"])
    decision_bytes = b"".join(_json_bytes(record.to_dict()) for record in records)
    transaction_bytes = b"".join(_json_bytes(row) for row in transactions)
    if not records:
        raise ValueError("no Gold replay decision records were produced")
    split_items = []
    record_by_seat = {(row["episode_id"], row["seat"]): row for row in selected_seats}
    for record in records:
        selected = record_by_seat[(record.episode_id, record.acting_seat)]
        split_items.append(SplitItem(record.decision_id, record.episode_id, record.submission_id, record.style_id,
                                     record.timestamp[:10] if record.timestamp != "unknown" else "unknown", _seed(replays[record.episode_id][1]),
                                     _field(selected, "deck_variant") or record.source_metadata["deck_variant_sha256"], record.own_archetype))
    component_fields = tuple(component_fields)
    holdout_style_families = tuple(holdout_style_families)
    blind_date_periods = tuple(blind_date_periods)
    development_date_periods = tuple(development_date_periods)
    split = build_split_manifest(
        split_items,
        source_dataset_sha256=_hash_bytes(decision_bytes),
        seed=str(split_seed),
        development_fraction=development_fraction,
        blind_fraction=blind_fraction,
        holdout_style_families=holdout_style_families,
        blind_date_periods=blind_date_periods,
        development_date_periods=development_date_periods,
        component_fields=component_fields,
    )
    split_bytes = _split_bytes(split)
    counts = {"archetype": dict(sorted(Counter(record.own_archetype or "unknown" for record in records).items())),
              "style": dict(sorted(Counter(record.style_id for record in records).items())),
              "result": dict(sorted(Counter(str(record.terminal_result.get("seat_reward")) for record in records).items()))}
    manifest: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "source_replays": sorted(source_rows, key=lambda row: row["episode_id"]),
        "selection_source": selection_source,
        "seat_metadata": {"path": _portable(Path(seat_metadata_csv), workspace=workspace_path, input_root=input_root), "sha256": _hash_bytes(Path(seat_metadata_csv).read_bytes())},
        "gold_rank_max": gold_rank_max,
        "split_seed": str(split_seed),
        "split_configuration": {
            "component_fields": list(component_fields),
            "holdout_style_families": sorted(holdout_style_families),
            "blind_date_periods": sorted(blind_date_periods),
            "development_date_periods": sorted(development_date_periods),
            "development_fraction": development_fraction,
            "blind_fraction": blind_fraction,
        },
        "selected_seats": sorted(selected_seats, key=lambda row: (row["episode_id"], row["seat"])),
        "record_count": len(records), "transaction_count": len(transactions), "counts": counts, "skips": dict(sorted(skips.items())),
        "output_sha256": {"decision_records.jsonl": _hash_bytes(decision_bytes), "retrospective_transactions.jsonl": _hash_bytes(transaction_bytes), "split_manifest.json": _hash_bytes(split_bytes)}}
    manifest["manifest_sha256"] = _hash_bytes(_json_bytes(manifest))
    manifest_bytes = _json_bytes(manifest, indent=2)

    destination = Path(output_dir)
    artifacts = {"decision_records.jsonl": decision_bytes, "retrospective_transactions.jsonl": transaction_bytes,
                 "split_manifest.json": split_bytes, "dataset_manifest.json": manifest_bytes}
    for name, payload in artifacts.items():
        target = destination / name
        if target.exists() and target.read_bytes() != payload:
            raise FileExistsError(f"refusing to replace non-identical artifact: {target}")
    destination.mkdir(parents=True, exist_ok=True)
    for name, payload in artifacts.items():
        target = destination / name
        if not target.exists():
            if name == "split_manifest.json":
                write_split_manifest(target, split)
            else:
                target.write_bytes(payload)
    return {"output_dir": str(destination), "record_count": len(records), "transaction_count": len(transactions),
            "dataset_manifest_sha256": manifest["manifest_sha256"], "decision_records_sha256": _hash_bytes(decision_bytes)}


def verify_gold_replay_dataset(output_dir: str | Path) -> dict[str, Any]:
    """Validate every immutable Phase 1 artifact and its cross-file bindings."""
    root = Path(output_dir)
    try:
        manifest = json.loads((root / "dataset_manifest.json").read_text(encoding="ascii"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read Gold dataset manifest: {error}") from error
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported Gold dataset manifest schema")
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if manifest.get("manifest_sha256") != _hash_bytes(_json_bytes(unsigned)):
        raise ValueError("Gold dataset manifest SHA256 does not validate")
    expected_outputs = manifest.get("output_sha256")
    if not isinstance(expected_outputs, dict):
        raise ValueError("Gold dataset manifest has no output checksum map")
    for name in ("decision_records.jsonl", "retrospective_transactions.jsonl", "split_manifest.json"):
        path = root / name
        if not path.is_file() or _hash_bytes(path.read_bytes()) != expected_outputs.get(name):
            raise ValueError(f"Gold dataset artifact checksum does not validate: {name}")
    split = load_split_manifest(root / "split_manifest.json")
    if split["source_dataset_sha256"] != expected_outputs["decision_records.jsonl"]:
        raise ValueError("split manifest is not bound to the decision record dataset")
    records = read_jsonl(root / "decision_records.jsonl")
    if len(records) != int(manifest.get("record_count", -1)):
        raise ValueError("Gold dataset record count does not validate")
    record_ids = [record.decision_id for record in records]
    split_ids = [str(item["item_id"]) for item in split["items"]]
    if len(set(record_ids)) != len(record_ids) or sorted(record_ids) != sorted(split_ids):
        raise ValueError("Gold dataset decisions and split membership do not match exactly")
    return {"manifest": manifest, "split_manifest": split, "records": records}


def load_gold_replay_split(
    output_dir: str | Path,
    split_name: str,
    *,
    allow_blind: bool = False,
) -> list[ReplayDecisionRecord]:
    """Load one verified split; blind remains sealed unless explicitly opened."""
    if split_name not in SPLITS:
        raise ValueError(f"unknown Gold replay split: {split_name}")
    if split_name == "blind" and not allow_blind:
        raise PermissionError("blind Gold replay split is sealed; pass allow_blind=True only for the one-time final evaluation")
    verified = verify_gold_replay_dataset(output_dir)
    membership = {
        str(item["item_id"]): str(item["split"])
        for item in verified["split_manifest"]["items"]
    }
    return [
        record for record in verified["records"]
        if membership[record.decision_id] == split_name
    ]
