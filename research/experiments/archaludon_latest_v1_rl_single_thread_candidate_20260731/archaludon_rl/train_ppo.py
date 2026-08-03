"""CLI for genuine on-policy residual PPO trajectory rows."""

from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any, Mapping

import torch

from .effect_features import (
    EFFECT_FIELD_NAMES,
    EFFECT_SCHEMA_VERSION,
    EffectFeatureSet,
    FeatureStatus,
    FeatureValue,
)
from .encoders import ACTION_DIM, STATE_DIM, encode_action, encode_state
from .frozen_sources import (
    checkpoint_source_hashes,
    find_repo_root,
    seeded_engine_dir,
    sha256_file,
    verify_frozen_sources,
)
from .model import (
    checkpoint_metadata,
    load_checkpoint,
    save_checkpoint,
    sha256_checkpoint,
)
from .policy import POLICY_SCHEMA_VERSION
from .public_state import SCHEMA_VERSION as PUBLIC_STATE_SCHEMA_VERSION
from .reference_policy import (
    REFERENCE_PRIOR_SCHEMA_VERSION,
    ReferencePolicy,
    ReferencePolicyConfig,
    validate_reference_prior_identity,
)
from .runtime_contract import validate_runtime_receipt
from .semantic_action import SemanticOption
from .trajectory import (
    COLLECTION_SPEC_SCHEMA_VERSION,
    DATASET_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    TRAJECTORY_SCHEMA_VERSION,
    collection_spec_sha256,
    compare_duplicate_traces,
    dataset_sha256,
    json_sha256,
    load_opponent_population_spec,
)

_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")


@dataclass(frozen=True)
class PPOConfig:
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_ratio: float = 0.2
    value_coef: float = 0.5
    entropy_coef: float = 0.01
    anchor_kl_target: float = 0.02
    anchor_kl_initial_coef: float = 0.1
    anchor_kl_hard_stop: float = 0.10
    gradient_clip: float = 0.5
    learning_rate: float = 3e-4
    epochs: int = 4

    def validate(self) -> None:
        if not 0.0 < self.gamma <= 1.0:
            raise ValueError("gamma must be in (0, 1]")
        if not 0.0 < self.gae_lambda <= 1.0:
            raise ValueError("gae_lambda must be in (0, 1]")
        if not 0.0 < self.clip_ratio < 1.0:
            raise ValueError("clip_ratio must be in (0, 1)")
        if self.value_coef < 0.0 or self.entropy_coef < 0.0:
            raise ValueError("loss coefficients must be nonnegative")
        if (
            self.anchor_kl_target <= 0.0
            or self.anchor_kl_initial_coef < 0.0
            or self.anchor_kl_hard_stop <= self.anchor_kl_target
        ):
            raise ValueError("anchor KL configuration is invalid")
        if self.gradient_clip <= 0.0 or self.learning_rate <= 0.0:
            raise ValueError("gradient clip and learning rate must be positive")
        if (
            not isinstance(self.epochs, int)
            or isinstance(self.epochs, bool)
            or self.epochs <= 0
        ):
            raise ValueError("epochs must be a positive integer")


@dataclass(frozen=True)
class ManifestDataset:
    manifest_path: Path
    manifest_sha256: str
    manifest: Mapping[str, Any]
    episode_paths: tuple[Path, ...]
    episodes: tuple[dict[str, Any], ...]


def _manifest_episode_path(
    manifest_root: Path,
    episode_root: Path,
    relative_path: Any,
) -> Path:
    if not isinstance(relative_path, str) or not relative_path:
        raise ValueError("episode receipt path must be a nonempty string")
    pure = PurePosixPath(relative_path)
    if (
        pure.is_absolute()
        or relative_path != pure.as_posix()
        or len(pure.parts) != 2
        or pure.parts[0] != "episodes"
        or pure.parts[1] in ("", ".", "..")
        or ".." in pure.parts
        or "\\" in relative_path
    ):
        raise ValueError(f"unsafe episode receipt path: {relative_path}")
    candidate = manifest_root.joinpath(*pure.parts)
    if candidate.parent != episode_root or candidate.suffix.lower() != ".json":
        raise ValueError(f"episode receipt must be a flat JSON file: {relative_path}")
    return candidate


def _is_reparse_or_symlink(path: Path) -> bool:
    if path.is_symlink():
        return True
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return bool(
        attributes
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def load_manifest_dataset(
    manifest_path: Path,
    *,
    input_checkpoint_sha256: str,
    expected_source_hashes: Mapping[str, str],
    expected_reference_prior_receipt: Mapping[str, Any],
    expected_reference_prior_schema_sha256: str,
) -> ManifestDataset:
    unresolved_path = (
        manifest_path
        if manifest_path.is_absolute()
        else Path.cwd() / manifest_path
    )
    if not unresolved_path.is_file():
        raise ValueError("run manifest is missing")
    if _is_reparse_or_symlink(unresolved_path):
        raise ValueError("run manifest must not be a link")
    path = unresolved_path.resolve(strict=True)
    if path.name != "run_manifest.json":
        raise ValueError("trainer requires the canonical run_manifest.json")
    manifest_candidates = tuple(path.parent.glob("run_manifest*.json"))
    if len(manifest_candidates) != 1 or manifest_candidates[0].resolve() != path:
        raise ValueError("collection directory must contain exactly one run manifest")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("run manifest must contain a JSON object")
    manifest_schema = payload.get("schema_version")
    if manifest_schema != MANIFEST_SCHEMA_VERSION:
        if manifest_schema in (
            "run-manifest-v1",
            "run-manifest-v2",
            "run-manifest-v3",
            "run-manifest-v4",
        ):
            raise ValueError(
                "unsafe prior run manifest schema lacks the current identity contract"
            )
        raise ValueError("run manifest schema mismatch")
    if not payload.get("complete"):
        raise ValueError("run manifest is not complete")
    if payload.get("mode") != "training":
        raise ValueError("run manifest is not training-mode")
    if dict(payload.get("source_hashes") or {}) != dict(expected_source_hashes):
        raise ValueError("run manifest frozen-source receipt mismatch")
    if payload.get("checkpoint_sha256") != input_checkpoint_sha256:
        raise ValueError("run manifest/input checkpoint mismatch")
    if (
        payload.get("collection_spec_schema_version")
        != COLLECTION_SPEC_SCHEMA_VERSION
        or payload.get("dataset_schema_version") != DATASET_SCHEMA_VERSION
    ):
        raise ValueError("run manifest collection/dataset schema mismatch")
    manifest_prior_receipt = payload.get("reference_prior_receipt")
    manifest_prior_hash = payload.get("reference_prior_schema_sha256")
    if not isinstance(manifest_prior_receipt, dict):
        raise ValueError("run manifest reference-prior receipt missing")
    validate_reference_prior_identity(
        manifest_prior_receipt,
        manifest_prior_hash,
    )
    if (
        dict(manifest_prior_receipt)
        != dict(expected_reference_prior_receipt)
        or manifest_prior_hash != expected_reference_prior_schema_sha256
    ):
        raise ValueError("run manifest/checkpoint reference-prior mismatch")
    manifest_runtime_receipt = payload.get("runtime_receipt")
    manifest_runtime_hash = payload.get("runtime_receipt_sha256")
    if not isinstance(manifest_runtime_receipt, dict) or not isinstance(
        manifest_runtime_hash, str
    ):
        raise ValueError("run manifest runtime receipt is missing")
    validate_runtime_receipt(
        manifest_runtime_receipt,
        manifest_runtime_hash,
    )
    if (
        manifest_runtime_receipt.get("checkpoint_sha256")
        != input_checkpoint_sha256
    ):
        raise ValueError("run manifest runtime/checkpoint mismatch")
    run_id = payload.get("run_id")
    if not isinstance(run_id, str) or not _RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("run manifest run ID is not a canonical string")

    verification = verify_frozen_sources()
    api_path = (seeded_engine_dir() / "cg" / "api.py").resolve()
    expected_engine_receipt = {
        "runtime_manifest_sha256": verification[
            "engine_runtime_manifest_sha256"
        ],
        "cg_api_path": str(api_path),
        "cg_api_sha256": sha256_file(api_path),
    }
    if dict(payload.get("engine_receipt") or {}) != expected_engine_receipt:
        raise ValueError("run manifest checked-engine receipt mismatch")

    raw_schedule = payload.get("schedule")
    if not isinstance(raw_schedule, list) or not raw_schedule:
        raise ValueError("run manifest schedule is missing or empty")
    schedule = tuple(dict(row) for row in raw_schedule)
    schedule_hash = json_sha256({"schedule": schedule})
    if payload.get("schedule_sha256") != schedule_hash:
        raise ValueError("run manifest schedule hash mismatch")
    episode_directory = payload.get("episode_directory")
    if episode_directory != "episodes":
        raise ValueError("run manifest episode directory mismatch")
    command = payload.get("command")
    if not isinstance(command, list) or not command:
        raise ValueError("run manifest command is missing")
    population_receipt = payload.get("opponent_population_receipt")
    if (
        not isinstance(population_receipt, dict)
        or not isinstance(population_receipt.get("path"), str)
    ):
        raise ValueError("run manifest opponent population receipt is incomplete")
    raw_opponent_table = payload.get("opponent_table")
    if not isinstance(raw_opponent_table, list) or not raw_opponent_table:
        raise ValueError("run manifest opponent table is missing or empty")
    repo = find_repo_root().resolve()
    current_population_receipt, current_opponent_table = (
        load_opponent_population_spec(
            repo / population_receipt["path"],
            repo_root=repo,
        )
    )
    if dict(population_receipt) != current_population_receipt:
        raise ValueError("run manifest opponent population spec receipt mismatch")
    opponent_table = tuple(dict(row) for row in raw_opponent_table)
    if opponent_table != current_opponent_table:
        raise ValueError("run manifest opponent table/current population mismatch")
    opponent_id_set = {row["id"] for row in current_opponent_table}
    spec_hash = collection_spec_sha256(
        run_id=str(payload.get("run_id")),
        source_hashes=dict(payload["source_hashes"]),
        checkpoint_sha256=str(payload["checkpoint_sha256"]),
        reference_prior_receipt=dict(manifest_prior_receipt),
        reference_prior_schema_sha256=str(manifest_prior_hash),
        engine_receipt=dict(payload["engine_receipt"]),
        runtime_receipt=dict(manifest_runtime_receipt),
        runtime_receipt_sha256=manifest_runtime_hash,
        mode=str(payload["mode"]),
        duplicate_mode=bool(payload.get("duplicate_mode")),
        schedule=schedule,
        schedule_sha256=schedule_hash,
        opponent_population_receipt=dict(population_receipt),
        opponent_table=opponent_table,
        command=tuple(str(value) for value in command),
        episode_directory=episode_directory,
    )
    if payload.get("collection_spec_sha256") != spec_hash:
        raise ValueError("run manifest collection-spec hash mismatch")

    schedule_identities: set[tuple[str, str, int, int]] = set()
    schedule_episode_ids: set[str] = set()
    schedule_opponent_seat_seeds: set[tuple[str, int, int]] = set()
    for row in schedule:
        episode_id = row.get("episode_id")
        opponent_id = row.get("opponent_id")
        seat = row.get("seat")
        seed = row.get("seed")
        game = row.get("game")
        replicas = row.get("replicas")
        if (
            not isinstance(episode_id, str)
            or not episode_id
            or not isinstance(opponent_id, str)
            or opponent_id not in opponent_id_set
            or not isinstance(seat, int)
            or isinstance(seat, bool)
            or seat not in (0, 1)
            or not isinstance(seed, int)
            or isinstance(seed, bool)
            or not isinstance(game, int)
            or isinstance(game, bool)
            or game < 0
            or replicas != (2 if payload.get("duplicate_mode") else 1)
        ):
            raise ValueError("run manifest contains an invalid schedule row")
        expected_episode_id = (
            f"{run_id}_opponent_{opponent_id}_seat{seat}_seed{seed}"
        )
        if episode_id != expected_episode_id:
            raise ValueError("run manifest schedule episode ID is not canonical")
        identity = (episode_id, opponent_id, seat, seed)
        if identity in schedule_identities:
            raise ValueError("run manifest contains a duplicate schedule identity")
        schedule_identities.add(identity)
        if episode_id in schedule_episode_ids:
            raise ValueError("run manifest contains a duplicate schedule episode ID")
        schedule_episode_ids.add(episode_id)
        opponent_seat_seed = (opponent_id, seat, seed)
        if opponent_seat_seed in schedule_opponent_seat_seeds:
            raise ValueError(
                "run manifest contains a duplicate schedule "
                "(opponent_id, seat, seed)"
            )
        schedule_opponent_seat_seeds.add(opponent_seat_seed)

    raw_receipts = payload.get("episode_receipts")
    if not isinstance(raw_receipts, list) or not raw_receipts:
        raise ValueError("run manifest has no episode receipts")
    receipts = tuple(dict(row) for row in raw_receipts)
    if len(receipts) != len(schedule):
        raise ValueError("run manifest episode/schedule counts differ")
    if payload.get("dataset_sha256") != dataset_sha256(
        spec_hash,
        receipts,
        reference_prior_receipt=manifest_prior_receipt,
        reference_prior_schema_sha256=manifest_prior_hash,
        runtime_receipt=manifest_runtime_receipt,
        runtime_receipt_sha256=manifest_runtime_hash,
    ):
        raise ValueError("run manifest dataset hash mismatch")

    manifest_root = path.parent
    episode_root = (manifest_root / episode_directory).resolve()
    if not episode_root.is_dir():
        raise ValueError("manifest episode directory is missing")
    if _is_reparse_or_symlink(manifest_root / episode_directory):
        raise ValueError("manifest episode directory must not be a link")
    receipt_paths: list[Path] = []
    receipt_identities: set[tuple[str, str, int, int]] = set()
    receipt_episode_ids: set[str] = set()
    receipt_opponent_seat_seeds: set[tuple[str, int, int]] = set()
    receipt_file_hashes: set[str] = set()
    receipt_path_set: set[Path] = set()
    audit_receipt_path_set: set[Path] = set()
    episodes: list[dict[str, Any]] = []
    for receipt in receipts:
        if (
            not isinstance(receipt.get("run_id"), str)
            or not isinstance(receipt.get("episode_id"), str)
            or not isinstance(receipt.get("opponent_id"), str)
            or receipt.get("opponent_id") not in opponent_id_set
            or not isinstance(receipt.get("seat"), int)
            or isinstance(receipt.get("seat"), bool)
            or receipt.get("seat") not in (0, 1)
            or not isinstance(receipt.get("seed"), int)
            or isinstance(receipt.get("seed"), bool)
        ):
            raise ValueError(
                "episode receipt identity fields have invalid scalar types"
            )
        receipt_episode_id = receipt.get("episode_id")
        receipt_opponent_id = receipt.get("opponent_id")
        expected_relative_path = (
            f"episodes/{receipt_episode_id}.json"
            if isinstance(receipt_episode_id, str)
            and isinstance(receipt_opponent_id, str)
            and f"_opponent_{receipt_opponent_id}_" in receipt_episode_id
            else None
        )
        if receipt.get("path") != expected_relative_path:
            raise ValueError(
                "unsafe episode receipt path: must safely include its opponent ID"
            )
        episode_path = _manifest_episode_path(
            manifest_root,
            episode_root,
            receipt.get("path"),
        )
        if episode_path in receipt_path_set:
            raise ValueError("run manifest contains a duplicate episode path")
        receipt_path_set.add(episode_path)
        if not episode_path.is_file():
            raise ValueError(f"manifest episode is missing: {episode_path}")
        if _is_reparse_or_symlink(episode_path):
            raise ValueError(f"manifest episode must not be a link: {episode_path}")
        resolved_episode = episode_path.resolve(strict=True)
        if resolved_episode.parent != episode_root:
            raise ValueError(f"manifest episode escapes its directory: {episode_path}")
        if receipt.get("bytes") != episode_path.stat().st_size:
            raise ValueError(f"manifest episode size mismatch: {episode_path}")
        actual_file_hash = sha256_file(episode_path)
        if receipt.get("sha256") != actual_file_hash:
            raise ValueError(f"manifest episode SHA256 mismatch: {episode_path}")
        if actual_file_hash in receipt_file_hashes:
            raise ValueError("run manifest contains a duplicate episode SHA256")
        receipt_file_hashes.add(actual_file_hash)
        episode = json.loads(episode_path.read_text(encoding="utf-8"))
        if not isinstance(episode, dict):
            raise ValueError(f"trajectory must contain a JSON object: {episode_path}")
        trajectory_schema = episode.get("schema_version")
        if trajectory_schema != TRAJECTORY_SCHEMA_VERSION:
            if trajectory_schema in (
                "trajectory-v1",
                "trajectory-v2",
                "trajectory-v3",
                "trajectory-v4",
            ):
                raise ValueError(
                    "unsafe prior trajectory schema lacks the current identity contract"
                )
            raise ValueError(f"trajectory schema mismatch: {episode_path}")
        if not episode.get("terminal") or not episode.get("clean_terminal"):
            raise ValueError(f"unclean or nonterminal trajectory: {episode_path}")
        if (
            not isinstance(episode.get("run_id"), str)
            or not isinstance(episode.get("episode_id"), str)
            or not isinstance(episode.get("opponent_id"), str)
            or episode.get("opponent_id") not in opponent_id_set
            or not isinstance(episode.get("seat"), int)
            or isinstance(episode.get("seat"), bool)
            or episode.get("seat") not in (0, 1)
            or not isinstance(episode.get("seed"), int)
            or isinstance(episode.get("seed"), bool)
        ):
            raise ValueError(
                "episode header identity fields have invalid scalar types"
            )
        identity = (
            str(receipt.get("episode_id")),
            receipt.get("opponent_id"),
            receipt.get("seat"),
            receipt.get("seed"),
        )
        if identity in receipt_identities:
            raise ValueError("run manifest contains a duplicate episode identity")
        receipt_identities.add(identity)
        if identity[0] in receipt_episode_ids:
            raise ValueError("run manifest contains a duplicate episode ID")
        receipt_episode_ids.add(identity[0])
        opponent_seat_seed = (identity[1], identity[2], identity[3])
        if opponent_seat_seed in receipt_opponent_seat_seeds:
            raise ValueError(
                "run manifest contains a duplicate receipt "
                "(opponent_id, seat, seed)"
            )
        receipt_opponent_seat_seeds.add(opponent_seat_seed)
        if (
            receipt.get("run_id") != payload.get("run_id")
            or episode.get("run_id") != payload.get("run_id")
            or episode.get("episode_id") != identity[0]
            or episode.get("opponent_id") != identity[1]
            or episode.get("seat") != identity[2]
            or episode.get("seed") != identity[3]
            or episode.get("source_hashes") != payload.get("source_hashes")
            or episode.get("checkpoint_sha256") != input_checkpoint_sha256
            or episode.get("reference_prior_receipt")
            != manifest_prior_receipt
            or episode.get("reference_prior_schema_sha256")
            != manifest_prior_hash
            or episode.get("runtime_receipt") != manifest_runtime_receipt
            or episode.get("runtime_receipt_sha256")
            != manifest_runtime_hash
            or episode.get("collection_spec_sha256") != spec_hash
            or episode.get("schedule_sha256") != schedule_hash
            or episode.get("mode") != "training"
            or episode.get("dataset_schema_version") != DATASET_SCHEMA_VERSION
        ):
            raise ValueError("episode header does not match its run manifest")
        if (
            not isinstance(episode.get("engine_steps"), int)
            or isinstance(episode.get("engine_steps"), bool)
            or episode.get("engine_steps") < 0
        ):
            raise ValueError("episode engine-step count is invalid")
        if payload.get("duplicate_mode"):
            audit = episode.get("duplicate_audit") or {}
            if (
                audit.get("equal") is not True
                or audit.get("terminal_equal") is not True
                or audit.get("engine_steps_equal") is not True
                or audit.get("first_trace_sha256")
                != audit.get("second_trace_sha256")
            ):
                raise ValueError("duplicate-audit episode lacks equal A/B traces")
            raw_replica_receipts = audit.get("replica_receipts")
            if not isinstance(raw_replica_receipts, list) or len(
                raw_replica_receipts
            ) != 2:
                raise ValueError("duplicate audit replica receipts are missing")
            replica_episodes: list[dict[str, Any]] = []
            receipt_keys = {
                "replica",
                "path",
                "bytes",
                "sha256",
                "clean_terminal",
                "terminal_result",
                "engine_steps",
                "fallback_count",
                "model_failure_count",
                "model_timeout_count",
            }
            for replica_index, replica in enumerate(("a", "b")):
                replica_receipt = dict(raw_replica_receipts[replica_index])
                expected_audit_path = (
                    f"audit/{episode['episode_id']}_{replica}.json"
                )
                expected_replica_episode_id = (
                    f"{episode['episode_id']}_audit_{replica}"
                )
                if (
                    set(replica_receipt) != receipt_keys
                    or replica_receipt.get("replica") != replica
                    or replica_receipt.get("path") != expected_audit_path
                    or replica_receipt.get("clean_terminal") is not True
                    or any(
                        not isinstance(replica_receipt.get(field), int)
                        or isinstance(replica_receipt.get(field), bool)
                        or replica_receipt.get(field) < 0
                        for field in (
                            "bytes",
                            "engine_steps",
                            "fallback_count",
                            "model_failure_count",
                            "model_timeout_count",
                        )
                    )
                    or not isinstance(
                        replica_receipt.get("terminal_result"), int
                    )
                    or isinstance(
                        replica_receipt.get("terminal_result"), bool
                    )
                    or replica_receipt.get("terminal_result") not in (0, 1, 2)
                    or replica_receipt.get("model_failure_count") != 0
                    or replica_receipt.get("model_timeout_count") != 0
                ):
                    raise ValueError("duplicate audit replica status receipt failed")
                audit_path = manifest_root.joinpath(
                    *PurePosixPath(expected_audit_path).parts
                )
                audit_root = (manifest_root / "audit").resolve()
                if (
                    not audit_path.is_file()
                    or _is_reparse_or_symlink(audit_path)
                    or audit_path.resolve(strict=True).parent != audit_root
                    or replica_receipt.get("bytes") != audit_path.stat().st_size
                    or replica_receipt.get("sha256") != sha256_file(audit_path)
                ):
                    raise ValueError("duplicate audit replica file receipt failed")
                resolved_audit_path = audit_path.resolve(strict=True)
                if resolved_audit_path in audit_receipt_path_set:
                    raise ValueError("duplicate audit replica path is repeated")
                audit_receipt_path_set.add(resolved_audit_path)
                replica_episode = json.loads(
                    audit_path.read_text(encoding="utf-8")
                )
                if (
                    not isinstance(replica_episode, dict)
                    or replica_episode.get("schema_version")
                    != TRAJECTORY_SCHEMA_VERSION
                    or replica_episode.get("run_id") != episode.get("run_id")
                    or replica_episode.get("episode_id")
                    != expected_replica_episode_id
                    or replica_episode.get("opponent_id")
                    != episode.get("opponent_id")
                    or replica_episode.get("seat") != episode.get("seat")
                    or replica_episode.get("seed") != episode.get("seed")
                    or replica_episode.get("source_hashes")
                    != episode.get("source_hashes")
                    or replica_episode.get("reference_prior_receipt")
                    != episode.get("reference_prior_receipt")
                    or replica_episode.get("reference_prior_schema_sha256")
                    != episode.get("reference_prior_schema_sha256")
                    or replica_episode.get("clean_terminal") is not True
                    or replica_episode.get("runtime_receipt")
                    != manifest_runtime_receipt
                    or replica_episode.get("runtime_receipt_sha256")
                    != manifest_runtime_hash
                    or replica_episode.get("checkpoint_sha256")
                    != input_checkpoint_sha256
                    or replica_episode.get("collection_spec_sha256")
                    != episode.get("collection_spec_sha256")
                    or replica_episode.get("schedule_sha256")
                    != episode.get("schedule_sha256")
                    or replica_episode.get("mode") != episode.get("mode")
                    or replica_episode.get("public_state_schema_version")
                    != episode.get("public_state_schema_version")
                    or replica_episode.get("effect_schema_version")
                    != episode.get("effect_schema_version")
                    or replica_episode.get("policy_schema_version")
                    != episode.get("policy_schema_version")
                    or replica_episode.get("dataset_schema_version")
                    != episode.get("dataset_schema_version")
                    or replica_episode.get("encoder") != episode.get("encoder")
                    or replica_episode.get("terminal") is not True
                    or not isinstance(replica_episode.get("action_errors"), int)
                    or isinstance(replica_episode.get("action_errors"), bool)
                    or replica_episode.get("action_errors") != 0
                    or replica_episode.get("exception") is not None
                    or replica_episode.get("max_step_hit") is not False
                    or replica_episode.get("terminal_result") not in (0, 1, 2)
                    or replica_episode.get("terminal_result")
                    != episode.get("terminal_result")
                    or not isinstance(replica_episode.get("engine_steps"), int)
                    or isinstance(replica_episode.get("engine_steps"), bool)
                    or replica_episode.get("engine_steps") < 0
                    or replica_episode.get("engine_steps")
                    != episode.get("engine_steps")
                    or replica_receipt.get("terminal_result")
                    != replica_episode.get("terminal_result")
                    or replica_receipt.get("engine_steps")
                    != replica_episode.get("engine_steps")
                ):
                    raise ValueError("duplicate audit replica episode mismatch")
                replica_decisions = tuple(
                    replica_episode.get("decisions", ())
                )
                if any(
                    not isinstance(row.get("fallback_used"), bool)
                    or not isinstance(row.get("model_timeout"), bool)
                    or (
                        row.get("model_failure_kind") is not None
                        and not isinstance(row.get("model_failure_kind"), str)
                    )
                    or (
                        row.get("model_failure_kind") is not None
                        and not row.get("fallback_used")
                    )
                    or (
                        row.get("model_timeout")
                        and row.get("model_failure_kind") != "TimeoutError"
                    )
                    for row in replica_decisions
                ):
                    raise ValueError(
                        "duplicate audit structured model-failure status is invalid"
                    )
                if (
                    replica_receipt.get("fallback_count")
                    != sum(
                        row.get("fallback_used") is True
                        for row in replica_decisions
                    )
                    or replica_receipt.get("model_failure_count")
                    != sum(
                        row.get("model_failure_kind") is not None
                        for row in replica_decisions
                    )
                    or replica_receipt.get("model_timeout_count")
                    != sum(
                        row.get("model_timeout") is True
                        for row in replica_decisions
                    )
                ):
                    raise ValueError("duplicate audit replica status mismatch")
                replica_episodes.append(replica_episode)
            recomputed_audit = compare_duplicate_traces(
                replica_episodes[0], replica_episodes[1]
            )
            if any(
                audit.get(field) != recomputed_audit.get(field)
                for field in (
                    "equal",
                    "identity_equal",
                    "terminal_equal",
                    "engine_steps_equal",
                    "first_identity",
                    "second_identity",
                    "mismatch_indices",
                    "first_trace_sha256",
                    "second_trace_sha256",
                )
            ):
                raise ValueError("duplicate audit comparison cannot be reproduced")
        receipt_paths.append(resolved_episode)
        episodes.append(episode)

    if receipt_identities != schedule_identities:
        raise ValueError("episode receipts do not exactly cover the schedule")
    schedule_sequence = tuple(
        (
            str(row["episode_id"]),
            str(row["opponent_id"]),
            int(row["seat"]),
            int(row["seed"]),
        )
        for row in schedule
    )
    receipt_sequence = tuple(
        (
            str(row["episode_id"]),
            str(row["opponent_id"]),
            int(row["seat"]),
            int(row["seed"]),
        )
        for row in receipts
    )
    if receipt_sequence != schedule_sequence:
        raise ValueError("episode receipt order does not match the schedule")
    actual_episode_files: set[Path] = set()
    for candidate in episode_root.iterdir():
        if (
            not candidate.is_file()
            or _is_reparse_or_symlink(candidate)
            or candidate.suffix.lower() != ".json"
        ):
            raise ValueError("episode directory contains an extra non-episode entry")
        actual_episode_files.add(candidate.resolve(strict=True))
    if actual_episode_files != receipt_path_set:
        raise ValueError("episode directory contains missing or extra JSON files")
    audit_directory = manifest_root / "audit"
    if payload.get("duplicate_mode"):
        if not audit_directory.is_dir() or _is_reparse_or_symlink(audit_directory):
            raise ValueError("duplicate audit directory is missing or linked")
        actual_audit_files: set[Path] = set()
        for candidate in audit_directory.iterdir():
            if (
                not candidate.is_file()
                or _is_reparse_or_symlink(candidate)
                or candidate.suffix.lower() != ".json"
            ):
                raise ValueError(
                    "duplicate audit directory contains an extra invalid entry"
                )
            actual_audit_files.add(candidate.resolve(strict=True))
        if actual_audit_files != audit_receipt_path_set:
            raise ValueError("duplicate audit directory receipt closure mismatch")
    return ManifestDataset(
        manifest_path=path,
        manifest_sha256=sha256_file(path),
        manifest=payload,
        episode_paths=tuple(receipt_paths),
        episodes=tuple(episodes),
    )


def _validate_rows(
    episodes: list[dict[str, Any]],
    *,
    checkpoint_sha256: str,
    source_hashes: Mapping[str, str],
    expected_encoder: Mapping[str, Any],
    behavior_model: Any,
    reference_prior_receipt: Mapping[str, Any],
    reference_prior_schema_sha256: str,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    prior_config = validate_reference_prior_identity(
        reference_prior_receipt,
        reference_prior_schema_sha256,
    )
    reference_policy = ReferencePolicy(prior_config)
    rows: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for episode in episodes:
        if episode.get("mode") != "training":
            raise ValueError("PPO accepts training-mode episodes only")
        if (
            episode.get("public_state_schema_version")
            != PUBLIC_STATE_SCHEMA_VERSION
            or episode.get("effect_schema_version") != EFFECT_SCHEMA_VERSION
            or episode.get("policy_schema_version") != POLICY_SCHEMA_VERSION
        ):
            raise ValueError("episode component schema mismatch")
        if episode.get("checkpoint_sha256") != checkpoint_sha256:
            raise ValueError("episode/checkpoint hash mismatch")
        if dict(episode.get("source_hashes") or {}) != dict(source_hashes):
            raise ValueError("episode/checkpoint source receipt mismatch")
        if dict(episode.get("encoder") or {}) != dict(expected_encoder):
            raise ValueError("episode/checkpoint encoder schema mismatch")
        episode_prior_receipt = episode.get("reference_prior_receipt")
        episode_prior_hash = episode.get("reference_prior_schema_sha256")
        if not isinstance(episode_prior_receipt, dict):
            raise ValueError("episode reference-prior receipt missing")
        validate_reference_prior_identity(
            episode_prior_receipt,
            episode_prior_hash,
        )
        if (
            episode_prior_receipt != dict(reference_prior_receipt)
            or episode_prior_hash != reference_prior_schema_sha256
        ):
            raise ValueError("episode/checkpoint reference-prior mismatch")
        eligible_in_episode: list[dict[str, Any]] = []
        for row in episode.get("decisions") or ():
            if not isinstance(row.get("fallback_used"), bool):
                raise ValueError("decision fallback status must be a boolean")
            model_failure_kind = row.get("model_failure_kind")
            model_timeout = row.get("model_timeout")
            if (
                not isinstance(model_timeout, bool)
                or (
                    model_failure_kind is not None
                    and not isinstance(model_failure_kind, str)
                )
                or (model_failure_kind is not None and not row["fallback_used"])
                or (model_timeout and model_failure_kind != "TimeoutError")
            ):
                raise ValueError("decision structured model-failure status is invalid")
            if model_failure_kind is not None or model_timeout:
                raise ValueError(
                    "dataset contains a model timeout/fallback decision"
                )
            if row.get("policy_schema_version") != POLICY_SCHEMA_VERSION:
                raise ValueError("decision policy schema mismatch")
            if (
                row.get("prior_schema_version")
                != REFERENCE_PRIOR_SCHEMA_VERSION
                or row.get("prior_schema_version")
                != episode_prior_receipt["schema_version"]
                or row.get("prior_schema_sha256") != episode_prior_hash
            ):
                raise ValueError("decision/episode reference-prior mismatch")
            legal_option_count = row.get("legal_option_count")
            if (
                not isinstance(legal_option_count, int)
                or isinstance(legal_option_count, bool)
                or legal_option_count < 0
            ):
                raise ValueError(
                    "decision legal option count must be a strict nonnegative integer"
                )
            projection = row.get("public_projection") or {}
            select = projection.get("select") or {}
            projected_option_count = select.get("option_count")
            if (
                not isinstance(projected_option_count, int)
                or isinstance(projected_option_count, bool)
                or projected_option_count != legal_option_count
            ):
                raise ValueError(
                    "decision legal option count/public projection mismatch"
                )
            actions = row.get("action_vectors") or ()
            semantic_rows = row.get("legal_semantic_options") or ()
            effect_rows = row.get("effect_features") or ()
            legal_mask = row.get("legal_option_mask") or ()
            actor_mask = row.get("actor_option_mask") or ()
            if any(
                len(surface) != legal_option_count
                for surface in (
                    actions,
                    semantic_rows,
                    effect_rows,
                    legal_mask,
                    actor_mask,
                )
            ):
                raise ValueError("decision legal option dimensional closure mismatch")
            if row.get("checkpoint_sha256") != checkpoint_sha256:
                raise ValueError("decision/checkpoint hash mismatch")
            if dict(row.get("source_hashes") or {}) != dict(source_hashes):
                raise ValueError("decision/checkpoint source receipt mismatch")
            q_latest = row.get("q_latest")
            teacher_probability = row.get("teacher_probability")
            teacher_action = row.get("teacher_action") or ()
            if q_latest:
                if (
                    not isinstance(q_latest, (list, tuple))
                    or len(q_latest) != legal_option_count
                    or any(
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not math.isfinite(float(value))
                        or float(value) <= 0.0
                        for value in q_latest
                    )
                ):
                    raise ValueError("reference prior lost support or dimension")
                if not math.isclose(
                    sum(float(value) for value in q_latest),
                    1.0,
                    rel_tol=0.0,
                    abs_tol=1e-9,
                ):
                    raise ValueError("reference prior is not normalized")
                if (
                    len(teacher_action) != 1
                    or not isinstance(teacher_action[0], int)
                    or isinstance(teacher_action[0], bool)
                    or not 0 <= teacher_action[0] < legal_option_count
                ):
                    raise ValueError(
                        "decision teacher action cannot index its reference prior"
                    )
                teacher_index = teacher_action[0]
                if (
                    isinstance(teacher_probability, bool)
                    or not isinstance(teacher_probability, (int, float))
                    or not math.isfinite(float(teacher_probability))
                    or teacher_probability != q_latest[teacher_index]
                ):
                    raise ValueError(
                        "stored teacher probability does not match reference prior"
                    )
                recomputed_prior = reference_policy.latest_prior(
                    legal_option_count,
                    teacher_index,
                )
                if tuple(float(value) for value in q_latest) != recomputed_prior:
                    raise ValueError("stored latest prior cannot be reproduced")
            elif teacher_probability is not None:
                raise ValueError(
                    "teacher probability must be absent when no prior was evaluated"
                )
            if row.get("ppo_eligible") and (
                not isinstance(q_latest, (list, tuple))
                or not q_latest
                or len(q_latest) != legal_option_count
                or teacher_probability is None
            ):
                raise ValueError(
                    "PPO-eligible decision lacks complete reference-prior provenance"
                )
            if row.get("protected") and (
                row.get("ppo_eligible")
                or row.get("sampled_stochastically")
                or row.get("behavior_logprob") is not None
                or tuple(row.get("final_action") or ())
                != tuple(teacher_action)
            ):
                raise ValueError(
                    "protected decision is not teacher-exact and PPO-ineligible"
                )
            if not row.get("ppo_eligible"):
                continue
            eligible_in_episode.append(row)
            if row.get("protected") or row.get("fallback_reason") is not None:
                raise ValueError("protected/fallback row marked PPO eligible")
            if (
                row.get("collection_mode") != "training"
                or not row.get("sampled_stochastically")
            ):
                raise ValueError("PPO row was not sampled by the training policy")
            if row.get("teacher_call_count") != 1:
                raise ValueError("PPO row does not have exactly one teacher call")
            telemetry = row.get("teacher_telemetry") or ()
            if len(telemetry) != 1:
                raise ValueError("PPO row does not have one telemetry row")
            final_telemetry = telemetry[0]
            if (
                final_telemetry.get("precedence_reason")
                != "rank17_exact_parent"
                or final_telemetry.get("winning_rule_id")
                != "exact_historical_silver"
                or final_telemetry.get("eligible_rule_ids")
                or final_telemetry.get("active_owner_before") is not None
                or final_telemetry.get("active_owner_after") is not None
                or final_telemetry.get("active_transaction_owner") is not None
                or final_telemetry.get("rollback_reason")
                or final_telemetry.get("caught_exceptions")
                or final_telemetry.get("invalid_or_emergency_fallback")
                or final_telemetry.get("duplicate_or_reset_state") is not None
                or final_telemetry.get("option_binding_result")
                not in (None, "BOUND")
            ):
                raise ValueError("PPO row is not an exact free-MAIN rank17 decision")
            if (
                select.get("type") != 0
                or select.get("context") != 0
                or select.get("min_count") != 1
                or select.get("max_count") != 1
                or legal_option_count < 2
            ):
                raise ValueError("PPO row lies outside the Phase-0 actor surface")
            if row.get("behavior_logprob") is None or row.get("value") is None:
                raise ValueError("on-policy row lacks behavior logprob/value")
            if not math.isfinite(float(row["behavior_logprob"])) or not math.isfinite(
                float(row["value"])
            ):
                raise ValueError("on-policy row contains non-finite behavior data")
            state = row.get("state_vector") or ()
            q_latest = q_latest or ()
            residuals = row.get("residuals") or ()
            probabilities = row.get("final_probabilities") or ()
            final_action = row.get("final_action") or ()
            if len(state) != STATE_DIM:
                raise ValueError("state vector dimension mismatch")
            if not actions or any(len(action) != ACTION_DIM for action in actions):
                raise ValueError("action vector dimension mismatch")
            if len(residuals) != len(actions) or any(
                not math.isfinite(float(value)) for value in residuals
            ):
                raise ValueError("stored residual dimension/non-finite mismatch")
            if len(probabilities) != len(actions) or any(
                not math.isfinite(float(value)) or float(value) <= 0
                for value in probabilities
            ):
                raise ValueError("stored behavior distribution is invalid")
            if not math.isclose(
                sum(float(value) for value in probabilities),
                1.0,
                rel_tol=0.0,
                abs_tol=1e-6,
            ):
                raise ValueError("behavior distribution is not normalized")
            if len(final_action) != 1 or not 0 <= int(final_action[0]) < len(actions):
                raise ValueError("PPO row final action is not one legal option")
            selected = int(final_action[0])
            if not math.isclose(
                float(row["behavior_logprob"]),
                math.log(float(probabilities[selected])),
                rel_tol=0.0,
                abs_tol=1e-6,
            ):
                raise ValueError("behavior logprob does not match sampled distribution")
            if (
                len(actor_mask) != len(actions)
                or not all(bool(value) for value in actor_mask)
            ):
                raise ValueError("PPO row does not retain the complete actor surface")
            recomputed_state = encode_state(projection)
            if any(
                not math.isclose(float(left), float(right), abs_tol=1e-9)
                for left, right in zip(recomputed_state, state)
            ):
                raise ValueError("stored state vector does not match public projection")
            semantic_options: list[SemanticOption] = []
            effect_sets: list[EffectFeatureSet] = []
            for semantic_row, effect_row in zip(semantic_rows, effect_rows):
                payload = semantic_row.get("payload") or {}
                option = SemanticOption(
                    engine_index=int(semantic_row["engine_index"]),
                    option_type=int(payload["option_type"]),
                    fields=tuple(
                        (str(name), None if value is None else int(value))
                        for name, value in (payload.get("fields") or {}).items()
                    ),
                    source_card_id=payload.get("source_card_id"),
                    target_card_id=payload.get("target_card_id"),
                )
                if option.identity != semantic_row.get("identity"):
                    raise ValueError("stored semantic option identity mismatch")
                raw_fields = effect_row.get("fields") or {}
                if (
                    effect_row.get("schema_version") != EFFECT_SCHEMA_VERSION
                    or set(raw_fields) != set(EFFECT_FIELD_NAMES)
                ):
                    raise ValueError("stored effect feature schema mismatch")
                feature_set = EffectFeatureSet(
                    option_identity=str(effect_row.get("option_identity")),
                    fields={
                        name: FeatureValue(
                            FeatureStatus(raw_fields[name]["status"]),
                            raw_fields[name].get("value"),
                        )
                        for name in raw_fields
                    },
                    schema_version=str(effect_row.get("schema_version")),
                )
                if feature_set.option_identity != option.identity:
                    raise ValueError("effect/semantic option identity mismatch")
                semantic_options.append(option)
                effect_sets.append(feature_set)
            recomputed_actions = [
                encode_action(option, effects)
                for option, effects in zip(semantic_options, effect_sets)
            ]
            for expected, stored in zip(recomputed_actions, actions):
                if len(expected) != len(stored) or any(
                    not math.isclose(
                        float(left), float(right), rel_tol=0.0, abs_tol=1e-9
                    )
                    for left, right in zip(expected, stored)
                ):
                    raise ValueError(
                        "stored action vector does not match semantic/effect payload"
                    )
            predicted_residuals, predicted_value = behavior_model.predict(
                state, actions
            )
            if len(predicted_residuals) != len(residuals) or any(
                not math.isclose(
                    float(left), float(right), rel_tol=0.0, abs_tol=1e-6
                )
                for left, right in zip(predicted_residuals, residuals)
            ):
                raise ValueError(
                    "stored residuals were not generated by claimed checkpoint"
                )
            if not math.isclose(
                float(predicted_value),
                float(row["value"]),
                rel_tol=0.0,
                abs_tol=1e-6,
            ):
                raise ValueError(
                    "stored value was not generated by claimed checkpoint"
                )
            if len(teacher_action) != 1:
                raise ValueError("PPO row teacher action is not singleton")
            recomputed_distribution = reference_policy.distribution(
                legal_option_count,
                teacher_action[0],
                predicted_residuals,
            )
            if any(
                not math.isclose(float(left), float(right), abs_tol=1e-7)
                for left, right in zip(recomputed_distribution.q_latest, q_latest)
            ):
                raise ValueError("stored latest prior cannot be reproduced")
            if any(
                not math.isclose(float(left), float(right), abs_tol=1e-7)
                for left, right in zip(
                    recomputed_distribution.probabilities, probabilities
                )
            ):
                raise ValueError(
                    "stored behavior probabilities cannot be reproduced"
                )
            rows.append((episode, row))
        if eligible_in_episode:
            if any(row.get("done") for row in eligible_in_episode[:-1]):
                raise ValueError("nonterminal PPO row marked done")
            last = eligible_in_episode[-1]
            if not last.get("done") or not last.get("terminated") or last.get("truncated"):
                raise ValueError("last PPO row lacks a clean terminal transition")
            if any(row.get("next_public_state_sha256") is None for row in eligible_in_episode):
                raise ValueError("PPO transition lacks next-state audit hash")
    if not rows:
        raise ValueError("teacher-only dataset has no genuine on-policy PPO rows")
    return rows


def _gae(
    episodes: list[dict[str, Any]], config: PPOConfig
) -> dict[tuple[str, int], tuple[float, float]]:
    result: dict[tuple[str, int], tuple[float, float]] = {}
    for episode in episodes:
        eligible = [
            row for row in episode.get("decisions") or () if row.get("ppo_eligible")
        ]
        advantage = 0.0
        next_value = 0.0
        for row in reversed(eligible):
            value = float(row["value"])
            reward = float(row.get("reward", 0.0))
            delta = reward + config.gamma * next_value - value
            advantage = (
                delta
                + config.gamma * config.gae_lambda * advantage
            )
            result[(str(episode["episode_id"]), int(row["decision_index"]))] = (
                advantage,
                advantage + value,
            )
            next_value = value
    return result


def _mean_anchor_kl(
    model: Any,
    rows: list[tuple[dict[str, Any], dict[str, Any]]],
    *,
    device: str,
    reference_config: ReferencePolicyConfig,
) -> float:
    values: list[torch.Tensor] = []
    with torch.no_grad():
        for _, row in rows:
            state = torch.tensor(
                row["state_vector"], dtype=torch.float32, device=device
            )
            actions = torch.tensor(
                row["action_vectors"], dtype=torch.float32, device=device
            )
            residuals, _ = model(state, actions)
            q_latest = torch.tensor(
                row["q_latest"], dtype=torch.float32, device=device
            )
            logits = (
                torch.log(q_latest)
                + reference_config.residual_scale
                * torch.tanh(
                    torch.clamp(
                        residuals,
                        -reference_config.residual_cap,
                        reference_config.residual_cap,
                    )
                )
            )
            log_probs = torch.log_softmax(logits, dim=0)
            probabilities = torch.softmax(logits, dim=0)
            values.append(
                (probabilities * (log_probs - torch.log(q_latest))).sum()
            )
    if not values:
        raise ValueError("cannot measure KL without on-policy rows")
    measured = torch.stack(values).mean()
    if not torch.isfinite(measured):
        raise ValueError("post-update anchor KL is non-finite")
    return float(measured.detach().cpu())


def train(
    *,
    input_checkpoint: Path,
    manifest_path: Path,
    output_checkpoint: Path,
    config: PPOConfig | None = None,
    device: str = "cpu",
) -> dict[str, Any]:
    cfg = config or PPOConfig()
    cfg.validate()
    if input_checkpoint.resolve() == output_checkpoint.resolve():
        raise ValueError("output checkpoint must not overwrite the input checkpoint")
    input_hash = sha256_checkpoint(input_checkpoint)
    current_source_hashes = checkpoint_source_hashes()
    model, metadata, optimizer_state = load_checkpoint(
        input_checkpoint,
        expected_source_hashes=current_source_hashes,
        device=device,
    )
    prior_receipt = metadata.get("reference_prior_receipt")
    prior_hash = metadata.get("reference_prior_schema_sha256")
    if not isinstance(prior_receipt, dict) or not isinstance(prior_hash, str):
        raise ValueError("checkpoint reference-prior identity missing after validation")
    reference_config = validate_reference_prior_identity(
        prior_receipt,
        prior_hash,
    )
    dataset = load_manifest_dataset(
        manifest_path,
        input_checkpoint_sha256=input_hash,
        expected_source_hashes=current_source_hashes,
        expected_reference_prior_receipt=prior_receipt,
        expected_reference_prior_schema_sha256=prior_hash,
    )
    source_hashes = current_source_hashes
    episodes = list(dataset.episodes)
    rows = _validate_rows(
        episodes,
        checkpoint_sha256=input_hash,
        source_hashes=source_hashes,
        expected_encoder=metadata.get("encoder") or {},
        behavior_model=model,
        reference_prior_receipt=prior_receipt,
        reference_prior_schema_sha256=prior_hash,
    )
    advantages = _gae(episodes, cfg)
    advantage_values = torch.tensor(
        [
            advantages[(str(episode["episode_id"]), int(row["decision_index"]))][0]
            for episode, row in rows
        ],
        dtype=torch.float32,
        device=device,
    )
    advantage_mean = advantage_values.mean()
    advantage_std = advantage_values.std(unbiased=False).clamp_min(1e-8)
    normalized_advantages = (advantage_values - advantage_mean) / advantage_std
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg.learning_rate)
    if optimizer_state is not None:
        optimizer.load_state_dict(optimizer_state)
    kl_coef = cfg.anchor_kl_initial_coef
    stopped_early = False
    epoch_reports: list[dict[str, float]] = []

    for epoch in range(cfg.epochs):
        optimizer.zero_grad()
        losses: list[torch.Tensor] = []
        kls: list[torch.Tensor] = []
        entropies: list[torch.Tensor] = []
        policy_losses: list[torch.Tensor] = []
        value_losses: list[torch.Tensor] = []
        for row_index, (episode, row) in enumerate(rows):
            state = torch.tensor(row["state_vector"], dtype=torch.float32, device=device)
            actions = torch.tensor(
                row["action_vectors"], dtype=torch.float32, device=device
            )
            residuals, value = model(state, actions)
            q_latest = torch.tensor(
                row["q_latest"], dtype=torch.float32, device=device
            )
            logits = (
                torch.log(q_latest)
                + reference_config.residual_scale
                * torch.tanh(
                    torch.clamp(
                        residuals,
                        -reference_config.residual_cap,
                        reference_config.residual_cap,
                    )
                )
            )
            log_probs = torch.log_softmax(logits, dim=0)
            probs = torch.softmax(logits, dim=0)
            selected = int(row["final_action"][0])
            new_logprob = log_probs[selected]
            old_logprob = torch.tensor(
                float(row["behavior_logprob"]), dtype=torch.float32, device=device
            )
            ratio = torch.exp(new_logprob - old_logprob)
            advantage = normalized_advantages[row_index]
            unclipped = ratio * advantage
            clipped = torch.clamp(
                ratio, 1.0 - cfg.clip_ratio, 1.0 + cfg.clip_ratio
            ) * advantage
            policy_loss = -torch.minimum(unclipped, clipped)
            target = advantages[
                (str(episode["episode_id"]), int(row["decision_index"]))
            ][1]
            value_loss = (value - float(target)).pow(2)
            entropy = -(probs * log_probs).sum()
            anchor_kl = (
                probs * (log_probs - torch.log(q_latest))
            ).sum()
            loss = (
                policy_loss
                + cfg.value_coef * value_loss
                - cfg.entropy_coef * entropy
                + kl_coef * anchor_kl
            )
            losses.append(loss)
            kls.append(anchor_kl)
            entropies.append(entropy)
            policy_losses.append(policy_loss)
            value_losses.append(value_loss)
        total_loss = torch.stack(losses).mean()
        mean_kl = torch.stack(kls).mean()
        if not torch.isfinite(total_loss) or not torch.isfinite(mean_kl):
            raise ValueError("non-finite PPO objective")
        if float(mean_kl.detach().cpu()) > cfg.anchor_kl_hard_stop:
            stopped_early = True
            epoch_reports.append(
                {
                    "epoch": float(epoch),
                    "anchor_kl": float(mean_kl.detach().cpu()),
                    "early_stop": 1.0,
                }
            )
            break
        model_before = copy.deepcopy(model.state_dict())
        optimizer_before = copy.deepcopy(optimizer.state_dict())
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.gradient_clip)
        optimizer.step()
        measured_kl = _mean_anchor_kl(
            model,
            rows,
            device=device,
            reference_config=reference_config,
        )
        if measured_kl > cfg.anchor_kl_hard_stop:
            model.load_state_dict(model_before, strict=True)
            optimizer.load_state_dict(optimizer_before)
            stopped_early = True
            epoch_reports.append(
                {
                    "epoch": float(epoch),
                    "anchor_kl": measured_kl,
                    "early_stop": 1.0,
                    "rolled_back": 1.0,
                }
            )
            break
        epoch_reports.append(
            {
                "epoch": float(epoch),
                "loss": float(total_loss.detach().cpu()),
                "policy_loss": float(torch.stack(policy_losses).mean().detach().cpu()),
                "value_loss": float(torch.stack(value_losses).mean().detach().cpu()),
                "entropy": float(torch.stack(entropies).mean().detach().cpu()),
                "anchor_kl": measured_kl,
                "kl_coef": kl_coef,
                "early_stop": 0.0,
                "rolled_back": 0.0,
            }
        )
        if measured_kl > cfg.anchor_kl_target * 1.5:
            kl_coef *= 2.0
        elif measured_kl < cfg.anchor_kl_target / 1.5:
            kl_coef = max(1e-6, kl_coef / 2.0)

    output_metadata = checkpoint_metadata(
        source_hashes=source_hashes,
        training={
            "input_checkpoint_sha256": input_hash,
            "run_id": dataset.manifest["run_id"],
            "manifest_path": str(dataset.manifest_path),
            "manifest_sha256": dataset.manifest_sha256,
            "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
            "reference_prior_receipt": prior_receipt,
            "reference_prior_schema_sha256": prior_hash,
            "runtime_receipt": dataset.manifest["runtime_receipt"],
            "runtime_receipt_sha256": dataset.manifest[
                "runtime_receipt_sha256"
            ],
            "collection_spec_sha256": dataset.manifest[
                "collection_spec_sha256"
            ],
            "schedule_sha256": dataset.manifest["schedule_sha256"],
            "dataset_sha256": dataset.manifest["dataset_sha256"],
            "opponent_population_receipt": dataset.manifest[
                "opponent_population_receipt"
            ],
            "opponent_table": dataset.manifest["opponent_table"],
            "episode_receipts": dataset.manifest["episode_receipts"],
            "on_policy_rows": len(rows),
            "ppo_config": asdict(cfg),
            "stopped_early": stopped_early,
            "final_kl_coef": kl_coef,
            "epoch_reports": epoch_reports,
        },
    )
    output_hash = save_checkpoint(
        output_checkpoint, model, output_metadata, optimizer=optimizer
    )
    return {
        "input_checkpoint_sha256": input_hash,
        "output_checkpoint_sha256": output_hash,
        "manifest_sha256": dataset.manifest_sha256,
        "dataset_sha256": dataset.manifest["dataset_sha256"],
        "on_policy_rows": len(rows),
        "stopped_early": stopped_early,
        "epoch_reports": epoch_reports,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-checkpoint", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-checkpoint", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--epochs", type=int, default=PPOConfig.epochs)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = PPOConfig(epochs=args.epochs)
    report = train(
        input_checkpoint=args.input_checkpoint,
        manifest_path=args.manifest,
        output_checkpoint=args.output_checkpoint,
        config=config,
        device=args.device,
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
