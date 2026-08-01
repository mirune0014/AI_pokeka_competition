"""Locked whole-trajectory train/validation splits for PPO."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .frozen_sources import sha256_file
from .trajectory import json_sha256


SPLIT_SCHEMA_VERSION = "locked-trajectory-split-v1"


@dataclass(frozen=True)
class LockedTrajectorySplit:
    spec_path: Path
    spec_sha256: str
    train_episodes: tuple[dict[str, Any], ...]
    validation_episodes: tuple[dict[str, Any], ...]
    receipt: Mapping[str, Any]


def _selection_digest(
    algorithm_id: str,
    dataset_sha256: str,
    selection_seed: str,
    validation_episode_ids: tuple[str, ...],
) -> str:
    payload = "\0".join(
        (
            algorithm_id,
            dataset_sha256,
            selection_seed,
            *sorted(validation_episode_ids),
        )
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _ppo_keys(episodes: tuple[dict[str, Any], ...]) -> tuple[tuple[str, int], ...]:
    return tuple(
        (str(episode["episode_id"]), int(row["decision_index"]))
        for episode in episodes
        for row in episode.get("decisions") or ()
        if row.get("ppo_eligible")
    )


def _counts(values: list[Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        key = str(value)
        result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items()))


def _outcome(episode: Mapping[str, Any]) -> str:
    terminal_result = int(episode["terminal_result"])
    seat = int(episode["seat"])
    if terminal_result == 2:
        return "draw"
    return "win" if terminal_result == seat else "loss"


def load_locked_trajectory_split(
    dataset: Any,
    split_spec_path: Path,
) -> LockedTrajectorySplit:
    """Validate a split spec and preserve manifest order on both sides."""

    path = split_spec_path.resolve(strict=True)
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "algorithm_id",
        "selection_seed",
        "selection_digest",
        "manifest_sha256",
        "dataset_sha256",
        "validation_episode_ids",
        "expected",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("trajectory split spec schema mismatch")
    if payload["schema_version"] != SPLIT_SCHEMA_VERSION:
        raise ValueError("trajectory split spec version mismatch")
    if payload["manifest_sha256"] != dataset.manifest_sha256:
        raise ValueError("trajectory split manifest SHA-256 mismatch")
    dataset_hash = str(dataset.manifest.get("dataset_sha256"))
    if payload["dataset_sha256"] != dataset_hash:
        raise ValueError("trajectory split dataset SHA-256 mismatch")

    episodes = tuple(dataset.episodes)
    ids = tuple(str(episode["episode_id"]) for episode in episodes)
    if len(ids) != len(set(ids)):
        raise ValueError("trajectory split input contains duplicate episode IDs")
    validation_ids = tuple(payload["validation_episode_ids"])
    if (
        not validation_ids
        or len(validation_ids) != len(set(validation_ids))
        or any(not isinstance(value, str) or not value for value in validation_ids)
    ):
        raise ValueError("trajectory split validation IDs are invalid")
    unknown = set(validation_ids) - set(ids)
    if unknown:
        raise ValueError(f"trajectory split contains unknown episode IDs: {sorted(unknown)}")
    digest = _selection_digest(
        str(payload["algorithm_id"]),
        dataset_hash,
        str(payload["selection_seed"]),
        validation_ids,
    )
    if digest != payload["selection_digest"]:
        raise ValueError("trajectory split selection digest mismatch")

    validation_set = set(validation_ids)
    train = tuple(episode for episode in episodes if episode["episode_id"] not in validation_set)
    validation = tuple(
        episode for episode in episodes if episode["episode_id"] in validation_set
    )
    train_keys = _ppo_keys(train)
    validation_keys = _ppo_keys(validation)
    all_keys = _ppo_keys(episodes)
    if set(train_keys) & set(validation_keys):
        raise ValueError("trajectory split leaks PPO decisions across partitions")
    if set(train_keys) | set(validation_keys) != set(all_keys):
        raise ValueError("trajectory split does not cover all PPO decisions")

    actual = {
        "train_episode_count": len(train),
        "validation_episode_count": len(validation),
        "train_ppo_row_count": len(train_keys),
        "validation_ppo_row_count": len(validation_keys),
        "validation_opponent_count": len(
            {str(episode["opponent_id"]) for episode in validation}
        ),
        "validation_seat_counts": _counts(
            [int(episode["seat"]) for episode in validation]
        ),
        "validation_seed_counts": _counts(
            [int(episode["seed"]) for episode in validation]
        ),
        "validation_outcome_counts": _counts(
            [_outcome(episode) for episode in validation]
        ),
    }
    if payload["expected"] != actual:
        raise ValueError(
            f"trajectory split constraints mismatch: expected={payload['expected']!r}, "
            f"actual={actual!r}"
        )

    receipt = {
        "schema_version": SPLIT_SCHEMA_VERSION,
        "split_spec_path": str(path),
        "split_spec_sha256": sha256_file(path),
        "algorithm_id": payload["algorithm_id"],
        "selection_seed": payload["selection_seed"],
        "selection_digest": digest,
        "manifest_sha256": dataset.manifest_sha256,
        "dataset_sha256": dataset_hash,
        **actual,
        "train_episode_ids": [str(episode["episode_id"]) for episode in train],
        "validation_episode_ids": [
            str(episode["episode_id"]) for episode in validation
        ],
        "train_episode_ids_sha256": json_sha256(
            [str(episode["episode_id"]) for episode in train]
        ),
        "validation_episode_ids_sha256": json_sha256(
            [str(episode["episode_id"]) for episode in validation]
        ),
        "train_ppo_keys_sha256": json_sha256([list(key) for key in train_keys]),
        "validation_ppo_keys_sha256": json_sha256(
            [list(key) for key in validation_keys]
        ),
    }
    return LockedTrajectorySplit(
        spec_path=path,
        spec_sha256=receipt["split_spec_sha256"],
        train_episodes=train,
        validation_episodes=validation,
        receipt=receipt,
    )
