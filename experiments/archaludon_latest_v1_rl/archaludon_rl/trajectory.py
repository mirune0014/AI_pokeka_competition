"""Atomic terminal-episode trajectory and run-manifest contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from typing import Any, Mapping

from .effect_features import EFFECT_SCHEMA_VERSION
from .encoders import encoder_metadata
from .policy import PolicyDecision
from .policy import POLICY_SCHEMA_VERSION
from .public_state import (
    SCHEMA_VERSION as PUBLIC_STATE_SCHEMA_VERSION,
    public_state_hash,
    raw_observation_hash,
)
from .reference_policy import (
    REFERENCE_PRIOR_SCHEMA_VERSION,
    validate_reference_prior_identity,
)
from .runtime_contract import (
    canonical_runtime_receipt,
)


TRAJECTORY_SCHEMA_VERSION = "trajectory-v5"
MANIFEST_SCHEMA_VERSION = "run-manifest-v5"
COLLECTION_SPEC_SCHEMA_VERSION = "collection-spec-v3"
DATASET_SCHEMA_VERSION = "trajectory-dataset-v2"
OPPONENT_POPULATION_SCHEMA_VERSION = "archaludon-rl-opponent-population-v1"
_SAFE_OPPONENT_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9_]{0,63}")
_SAFE_POPULATION_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_SHA256_PATTERN = re.compile(r"[A-F0-9]{64}")


def _is_reparse_or_symlink(path: Path) -> bool:
    if path.is_symlink():
        return True
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return bool(
        attributes
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _validate_safe_opponent_id(value: Any) -> str:
    if not isinstance(value, str) or not _SAFE_OPPONENT_ID_PATTERN.fullmatch(value):
        raise ValueError(
            "opponent ID must be canonical lowercase snake_case with at most 64 characters"
        )
    return value


def _canonical_repo_relative_path(value: Any, *, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError(f"{label} must be a canonical repository-relative POSIX path")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or pure.as_posix() != value
        or not pure.parts
        or any(part in ("", ".", "..") for part in pure.parts)
        or ":" in pure.parts[0]
    ):
        raise ValueError(f"{label} must be a canonical repository-relative POSIX path")
    return pure


def _ordinary_path_within_repo(
    repo_root: Path,
    path: Path,
    *,
    label: str,
    expect_file: bool,
) -> Path:
    repo = repo_root.resolve(strict=True)
    absolute = path if path.is_absolute() else Path.cwd() / path
    try:
        relative = absolute.absolute().relative_to(repo)
    except ValueError as exc:
        raise ValueError(f"{label} must be contained in the repository") from exc
    cursor = repo
    for part in relative.parts:
        cursor = cursor / part
        if not cursor.exists():
            raise FileNotFoundError(f"{label} is missing: {cursor}")
        if _is_reparse_or_symlink(cursor):
            raise ValueError(f"{label} must not contain links: {cursor}")
    resolved = absolute.resolve(strict=True)
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise ValueError(f"{label} escapes the repository") from exc
    if expect_file and not resolved.is_file():
        raise ValueError(f"{label} must be an ordinary file: {resolved}")
    if not expect_file and not resolved.is_dir():
        raise ValueError(f"{label} must be an ordinary directory: {resolved}")
    return resolved


def load_opponent_population_spec(
    population_spec_path: Path | str,
    *,
    repo_root: Path,
) -> tuple[dict[str, Any], tuple[dict[str, str], ...]]:
    """Load and verify one canonical ordered opponent population."""

    repo = repo_root.resolve(strict=True)
    spec_path = _ordinary_path_within_repo(
        repo,
        Path(population_spec_path),
        label="opponent population spec",
        expect_file=True,
    )
    spec_relative = spec_path.relative_to(repo).as_posix()
    raw_bytes = spec_path.read_bytes()
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("opponent population spec must be UTF-8 JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "population_id",
        "opponents",
    }:
        raise ValueError("opponent population spec has an invalid top-level schema")
    if payload.get("schema_version") != OPPONENT_POPULATION_SCHEMA_VERSION:
        raise ValueError("opponent population spec schema mismatch")
    population_id = payload.get("population_id")
    if (
        not isinstance(population_id, str)
        or not _SAFE_POPULATION_ID_PATTERN.fullmatch(population_id)
    ):
        raise ValueError("opponent population ID is not canonical or safe")
    raw_opponents = payload.get("opponents")
    if not isinstance(raw_opponents, list) or not raw_opponents:
        raise ValueError("opponent population must contain at least one opponent")

    seen_ids: set[str] = set()
    table: list[dict[str, str]] = []
    for raw_row in raw_opponents:
        if not isinstance(raw_row, dict) or set(raw_row) != {
            "id",
            "path",
            "main_sha256",
            "deck_sha256",
        }:
            raise ValueError("opponent population contains an invalid opponent row")
        opponent_id = _validate_safe_opponent_id(raw_row.get("id"))
        if opponent_id in seen_ids:
            raise ValueError(f"duplicate opponent ID in population: {opponent_id}")
        seen_ids.add(opponent_id)
        relative = _canonical_repo_relative_path(
            raw_row.get("path"),
            label=f"opponent path for {opponent_id}",
        )
        opponent_dir = _ordinary_path_within_repo(
            repo,
            repo.joinpath(*relative.parts),
            label=f"opponent directory for {opponent_id}",
            expect_file=False,
        )
        hashes: dict[str, str] = {}
        for filename, field in (
            ("main.py", "main_sha256"),
            ("deck.csv", "deck_sha256"),
        ):
            expected = raw_row.get(field)
            if not isinstance(expected, str) or not _SHA256_PATTERN.fullmatch(expected):
                raise ValueError(
                    f"opponent {opponent_id} has an invalid {field} receipt"
                )
            source_path = _ordinary_path_within_repo(
                repo,
                opponent_dir / filename,
                label=f"opponent {opponent_id} {filename}",
                expect_file=True,
            )
            actual = hashlib.sha256(source_path.read_bytes()).hexdigest().upper()
            if actual != expected:
                raise ValueError(
                    f"opponent {opponent_id} {filename} SHA256 mismatch: "
                    f"expected {expected}, got {actual}"
                )
            hashes[field] = actual
        table.append(
            {
                "id": opponent_id,
                "path": relative.as_posix(),
                "main_sha256": hashes["main_sha256"],
                "deck_sha256": hashes["deck_sha256"],
            }
        )
    receipt = {
        "schema_version": OPPONENT_POPULATION_SCHEMA_VERSION,
        "population_id": population_id,
        "path": spec_relative,
        "bytes": len(raw_bytes),
        "sha256": hashlib.sha256(raw_bytes).hexdigest().upper(),
        "opponent_count": len(table),
    }
    return receipt, tuple(table)


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(
                payload,
                stream,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    finally:
        temporary = Path(temporary_name)
        if temporary.exists():
            temporary.unlink()


def json_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def collection_spec_sha256(
    *,
    run_id: str,
    source_hashes: Mapping[str, str],
    checkpoint_sha256: str,
    reference_prior_receipt: Mapping[str, Any],
    reference_prior_schema_sha256: str,
    engine_receipt: Mapping[str, Any],
    runtime_receipt: Mapping[str, Any],
    runtime_receipt_sha256: str,
    mode: str,
    duplicate_mode: bool,
    schedule: tuple[Mapping[str, Any], ...],
    schedule_sha256: str,
    opponent_population_receipt: Mapping[str, Any],
    opponent_table: tuple[Mapping[str, Any], ...],
    command: tuple[str, ...],
    episode_directory: str,
) -> str:
    validate_reference_prior_identity(
        reference_prior_receipt,
        reference_prior_schema_sha256,
    )
    runtime_row = canonical_runtime_receipt(
        runtime_receipt, runtime_receipt_sha256
    )
    return json_sha256(
        {
            "schema_version": COLLECTION_SPEC_SCHEMA_VERSION,
            "run_id": str(run_id),
            "source_hashes": dict(source_hashes),
            "checkpoint_sha256": str(checkpoint_sha256),
            "reference_prior_receipt": dict(reference_prior_receipt),
            "reference_prior_schema_sha256": str(
                reference_prior_schema_sha256
            ),
            "engine_receipt": dict(engine_receipt),
            "runtime_receipt": runtime_row,
            "runtime_receipt_sha256": str(runtime_receipt_sha256),
            "mode": str(mode),
            "duplicate_mode": bool(duplicate_mode),
            "schedule": tuple(dict(row) for row in schedule),
            "schedule_sha256": str(schedule_sha256),
            "opponent_population_receipt": dict(opponent_population_receipt),
            "opponent_table": tuple(dict(row) for row in opponent_table),
            "command": tuple(command),
            "episode_directory": str(episode_directory),
        }
    )


def dataset_sha256(
    collection_spec_hash: str,
    episode_receipts: tuple[Mapping[str, Any], ...],
    *,
    reference_prior_receipt: Mapping[str, Any],
    reference_prior_schema_sha256: str,
    runtime_receipt: Mapping[str, Any],
    runtime_receipt_sha256: str,
) -> str:
    validate_reference_prior_identity(
        reference_prior_receipt,
        reference_prior_schema_sha256,
    )
    runtime_row = canonical_runtime_receipt(
        runtime_receipt, runtime_receipt_sha256
    )
    return json_sha256(
        {
            "schema_version": DATASET_SCHEMA_VERSION,
            "collection_spec_sha256": str(collection_spec_hash),
            "reference_prior_schema_version": reference_prior_receipt[
                "schema_version"
            ],
            "reference_prior_schema_sha256": str(
                reference_prior_schema_sha256
            ),
            "runtime_receipt": runtime_row,
            "runtime_receipt_sha256": str(runtime_receipt_sha256),
            "episode_receipts": tuple(dict(row) for row in episode_receipts),
        }
    )


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    source_hashes: Mapping[str, str]
    checkpoint_sha256: str
    reference_prior_receipt: Mapping[str, Any]
    reference_prior_schema_sha256: str
    engine_receipt: Mapping[str, Any]
    runtime_receipt: Mapping[str, Any]
    runtime_receipt_sha256: str
    mode: str
    duplicate_mode: bool
    schedule: tuple[Mapping[str, Any], ...]
    schedule_sha256: str
    collection_spec_sha256: str
    opponent_population_receipt: Mapping[str, Any]
    opponent_table: tuple[Mapping[str, Any], ...]
    command: tuple[str, ...]
    episode_directory: str
    episode_receipts: tuple[Mapping[str, Any], ...]
    dataset_sha256: str | None
    complete: bool
    created_at_utc: str
    completed_at_utc: str | None
    collection_spec_schema_version: str = COLLECTION_SPEC_SCHEMA_VERSION
    dataset_schema_version: str = DATASET_SCHEMA_VERSION
    schema_version: str = MANIFEST_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        source_hashes: Mapping[str, str],
        checkpoint_sha256: str,
        reference_prior_receipt: Mapping[str, Any],
        reference_prior_schema_sha256: str,
        engine_receipt: Mapping[str, Any],
        runtime_receipt: Mapping[str, Any],
        runtime_receipt_sha256: str,
        mode: str,
        duplicate_mode: bool = False,
        schedule: tuple[Mapping[str, Any], ...] = (),
        opponent_population_receipt: Mapping[str, Any],
        opponent_table: tuple[Mapping[str, Any], ...],
        command: tuple[str, ...] = (),
    ) -> "RunManifest":
        schedule_rows = tuple(dict(row) for row in schedule)
        schedule_hash = json_sha256({"schedule": schedule_rows})
        source_rows = dict(source_hashes)
        prior_receipt = dict(reference_prior_receipt)
        validate_reference_prior_identity(
            prior_receipt,
            reference_prior_schema_sha256,
        )
        engine_rows = dict(engine_receipt)
        runtime_row = canonical_runtime_receipt(
            runtime_receipt, runtime_receipt_sha256
        )
        population_row = dict(opponent_population_receipt)
        opponent_rows = tuple(dict(row) for row in opponent_table)
        command_row = tuple(command)
        collection_spec_hash = collection_spec_sha256(
            run_id=str(run_id),
            source_hashes=source_rows,
            checkpoint_sha256=str(checkpoint_sha256),
            reference_prior_receipt=prior_receipt,
            reference_prior_schema_sha256=str(
                reference_prior_schema_sha256
            ),
            engine_receipt=engine_rows,
            runtime_receipt=runtime_row,
            runtime_receipt_sha256=str(runtime_receipt_sha256),
            mode=str(mode),
            duplicate_mode=bool(duplicate_mode),
            schedule=schedule_rows,
            schedule_sha256=schedule_hash,
            opponent_population_receipt=population_row,
            opponent_table=opponent_rows,
            command=command_row,
            episode_directory="episodes",
        )
        return cls(
            run_id=run_id,
            source_hashes=source_rows,
            checkpoint_sha256=checkpoint_sha256,
            reference_prior_receipt=prior_receipt,
            reference_prior_schema_sha256=reference_prior_schema_sha256,
            engine_receipt=engine_rows,
            runtime_receipt=runtime_row,
            runtime_receipt_sha256=str(runtime_receipt_sha256),
            mode=mode,
            duplicate_mode=duplicate_mode,
            schedule=schedule_rows,
            schedule_sha256=schedule_hash,
            collection_spec_sha256=collection_spec_hash,
            opponent_population_receipt=population_row,
            opponent_table=opponent_rows,
            command=command_row,
            episode_directory="episodes",
            episode_receipts=(),
            dataset_sha256=None,
            complete=False,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
            completed_at_utc=None,
        )

    def finalize(
        self, episode_receipts: tuple[Mapping[str, Any], ...]
    ) -> "RunManifest":
        if self.complete:
            raise ValueError("run manifest is already complete")
        receipt_by_identity: dict[tuple[str, int, int], dict[str, Any]] = {}
        for raw_row in episode_receipts:
            row = dict(raw_row)
            identity = (
                _validate_safe_opponent_id(row["opponent_id"]),
                int(row["seat"]),
                int(row["seed"]),
            )
            if identity in receipt_by_identity:
                raise ValueError("duplicate episode receipt identity")
            receipt_by_identity[identity] = row
        schedule_identities = tuple(
            (
                _validate_safe_opponent_id(row["opponent_id"]),
                int(row["seat"]),
                int(row["seed"]),
            )
            for row in self.schedule
        )
        if len(set(schedule_identities)) != len(schedule_identities):
            raise ValueError("duplicate schedule (opponent_id, seat, seed) identity")
        if set(receipt_by_identity) != set(schedule_identities):
            raise ValueError("episode receipts do not exactly cover schedule")
        rows: list[dict[str, Any]] = []
        for schedule_row, identity in zip(self.schedule, schedule_identities):
            receipt = receipt_by_identity[identity]
            if str(receipt.get("episode_id")) != str(schedule_row.get("episode_id")):
                raise ValueError("episode receipt ID does not match its schedule row")
            rows.append(receipt)
        ordered_rows = tuple(rows)
        dataset_hash = dataset_sha256(
            self.collection_spec_sha256,
            ordered_rows,
            reference_prior_receipt=self.reference_prior_receipt,
            reference_prior_schema_sha256=self.reference_prior_schema_sha256,
            runtime_receipt=self.runtime_receipt,
            runtime_receipt_sha256=self.runtime_receipt_sha256,
        )
        return replace(
            self,
            episode_receipts=ordered_rows,
            dataset_sha256=dataset_hash,
            complete=True,
            completed_at_utc=datetime.now(timezone.utc).isoformat(),
        )

    def write(self, path: Path | str) -> None:
        if not self.complete or self.dataset_sha256 is None:
            raise ValueError("incomplete run manifests may not be published")
        _atomic_json(Path(path), asdict(self))


class EpisodeBuilder:
    def __init__(
        self,
        *,
        run_id: str,
        episode_id: str,
        opponent_id: str,
        seat: int,
        seed: int,
        source_hashes: Mapping[str, str],
        checkpoint_sha256: str,
        reference_prior_receipt: Mapping[str, Any],
        reference_prior_schema_sha256: str,
        collection_spec_sha256: str,
        schedule_sha256: str,
        runtime_receipt: Mapping[str, Any],
        runtime_receipt_sha256: str,
        mode: str = "training",
    ) -> None:
        if seat not in (0, 1):
            raise ValueError("seat must be 0 or 1")
        if mode not in ("training", "deployment"):
            raise ValueError("mode must be training or deployment")
        prior_receipt = dict(reference_prior_receipt)
        validate_reference_prior_identity(
            prior_receipt,
            reference_prior_schema_sha256,
        )
        runtime_row = canonical_runtime_receipt(
            runtime_receipt, runtime_receipt_sha256
        )
        if runtime_row["checkpoint_sha256"] != checkpoint_sha256:
            raise ValueError("episode/runtime checkpoint SHA256 mismatch")
        self.header = {
            "schema_version": TRAJECTORY_SCHEMA_VERSION,
            "run_id": str(run_id),
            "episode_id": str(episode_id),
            "opponent_id": _validate_safe_opponent_id(opponent_id),
            "seat": seat,
            "seed": int(seed),
            "source_hashes": dict(source_hashes),
            "checkpoint_sha256": checkpoint_sha256,
            "reference_prior_receipt": prior_receipt,
            "reference_prior_schema_sha256": reference_prior_schema_sha256,
            "runtime_receipt": runtime_row,
            "runtime_receipt_sha256": str(runtime_receipt_sha256),
            "collection_spec_sha256": collection_spec_sha256,
            "schedule_sha256": schedule_sha256,
            "mode": mode,
            "public_state_schema_version": PUBLIC_STATE_SCHEMA_VERSION,
            "effect_schema_version": EFFECT_SCHEMA_VERSION,
            "policy_schema_version": POLICY_SCHEMA_VERSION,
            "dataset_schema_version": DATASET_SCHEMA_VERSION,
            "encoder": encoder_metadata(),
        }
        self.decisions: list[dict[str, Any]] = []
        self.finished = False

    def append(self, observation: Any, decision: PolicyDecision) -> None:
        if self.finished:
            raise RuntimeError("cannot append to finished episode")
        if decision.collection_mode != self.header["mode"]:
            raise ValueError("decision/episode collection mode mismatch")
        if (
            decision.prior_schema_version != REFERENCE_PRIOR_SCHEMA_VERSION
            or decision.prior_schema_version
            != self.header["reference_prior_receipt"]["schema_version"]
            or decision.prior_schema_sha256
            != self.header["reference_prior_schema_sha256"]
        ):
            raise ValueError("decision/episode reference-prior identity mismatch")
        if (
            not isinstance(decision.legal_option_count, int)
            or isinstance(decision.legal_option_count, bool)
            or decision.legal_option_count < 0
        ):
            raise ValueError("decision legal option count must be a strict integer")
        row_is_ppo = bool(
            decision.ppo_eligible
            and decision.collection_mode == "training"
            and decision.sampled_stochastically
            and not decision.fallback_used
            and not decision.guard.protected_fallback.hard
        )
        if row_is_ppo and (
            len(decision.q_latest) != decision.legal_option_count
            or decision.teacher_probability is None
        ):
            raise ValueError("eligible decision lacks the complete reference prior")
        if row_is_ppo and decision.projection is not None:
            next_hash = public_state_hash(decision.projection)
            for previous in reversed(self.decisions):
                if previous["ppo_eligible"]:
                    if previous["next_public_state_sha256"] is not None:
                        raise AssertionError("eligible transition was linked twice")
                    previous["next_public_state_sha256"] = next_hash
                    break
        row = {
            "decision_index": len(self.decisions),
            "raw_observation_sha256": raw_observation_hash(observation),
            "public_projection": decision.projection,
            "legal_semantic_options": [
                {
                    "engine_index": option.engine_index,
                    "identity": option.identity,
                    "payload": option.identity_payload,
                }
                for option in decision.semantic_options
            ],
            "state_vector": decision.state_vector,
            "action_vectors": decision.action_vectors,
            "effect_features": [
                feature_set.to_jsonable() for feature_set in decision.effects
            ],
            "legal_option_mask": decision.guard.legal_option_mask,
            "actor_option_mask": decision.guard.actor_option_mask,
            "guard_counts": decision.guard.counts,
            "guard_reasons": decision.guard.reasons,
            "guard_categories": [
                category.value for category in decision.guard.categories
            ],
            "q_latest": decision.q_latest,
            "prior_schema_version": decision.prior_schema_version,
            "prior_schema_sha256": decision.prior_schema_sha256,
            "legal_option_count": decision.legal_option_count,
            "teacher_probability": decision.teacher_probability,
            "residuals": decision.residuals,
            "final_probabilities": decision.final_probabilities,
            "reachability_diagnostics": decision.reachability_diagnostics,
            "prior_nonzero_count": sum(
                float(value) > 0.0 for value in decision.q_latest
            ),
            "argmax_reachable_count": sum(
                bool(value)
                for value in decision.reachability_diagnostics.get(
                    "argmax_reachable", ()
                )
            ),
            "teacher_action": decision.teacher_action,
            "neural_shadow_action": decision.neural_shadow_action,
            "final_action": decision.action,
            "behavior_logprob": decision.behavior_logprob,
            "value": decision.value,
            "teacher_telemetry": decision.teacher_telemetry,
            "teacher_call_count": decision.teacher_call_count,
            "collection_mode": decision.collection_mode,
            "sampled_stochastically": decision.sampled_stochastically,
            "policy_schema_version": decision.schema_version,
            "source_hashes": self.header["source_hashes"],
            "checkpoint_sha256": decision.checkpoint_sha256,
            "ppo_eligible": row_is_ppo,
            "fallback_used": bool(decision.fallback_used),
            "protected": bool(
                decision.fallback_used or decision.guard.protected_fallback.hard
            ),
            "fallback_reason": decision.fallback_reason,
            "model_failure_kind": decision.model_failure_kind,
            "model_timeout": decision.model_timeout,
            "reward": 0.0,
            "next_public_state_sha256": None,
            "terminated": False,
            "truncated": False,
            "done": False,
        }
        self.decisions.append(row)

    def finish(
        self,
        *,
        terminal_result: int,
        clean_terminal: bool,
        action_errors: int = 0,
        exception: str | None = None,
        max_step_hit: bool = False,
        terminal_observation: Any | None = None,
        engine_steps: int,
    ) -> dict[str, Any]:
        if self.finished:
            raise RuntimeError("episode already finished")
        self.finished = True
        if (
            not isinstance(engine_steps, int)
            or isinstance(engine_steps, bool)
            or engine_steps < 0
        ):
            raise ValueError("engine steps must be a strict nonnegative integer")
        seat = self.header["seat"]
        reward = (
            1.0
            if terminal_result == seat
            else (0.0 if terminal_result == 2 else -1.0)
        )
        last_eligible: dict[str, Any] | None = None
        for row in reversed(self.decisions):
            if row["ppo_eligible"]:
                row["reward"] = reward
                last_eligible = row
                break
        clean = bool(
            clean_terminal
            and terminal_result in (0, 1, 2)
            and action_errors == 0
            and exception is None
            and not max_step_hit
        )
        if last_eligible is not None:
            last_eligible["terminated"] = bool(
                terminal_result in (0, 1, 2) and not max_step_hit
            )
            last_eligible["truncated"] = bool(max_step_hit)
            last_eligible["done"] = bool(
                last_eligible["terminated"] or last_eligible["truncated"]
            )
            if terminal_observation is not None:
                last_eligible["next_public_state_sha256"] = public_state_hash(
                    terminal_observation
                )
        return {
            **self.header,
            "terminal": True,
            "clean_terminal": clean,
            "terminal_result": terminal_result,
            "terminal_reward": reward,
            "action_errors": int(action_errors),
            "exception": exception,
            "max_step_hit": bool(max_step_hit),
            "engine_steps": engine_steps,
            "decisions": self.decisions,
        }


def publish_clean_episode(path: Path | str, episode: Mapping[str, Any]) -> str:
    if (
        episode.get("schema_version") != TRAJECTORY_SCHEMA_VERSION
        or not episode.get("terminal")
        or not episode.get("clean_terminal")
        or not isinstance(episode.get("engine_steps"), int)
        or isinstance(episode.get("engine_steps"), bool)
        or int(episode.get("engine_steps")) < 0
    ):
        raise ValueError("only clean terminal trajectory episodes may be published")
    runtime_row = episode.get("runtime_receipt")
    runtime_hash = episode.get("runtime_receipt_sha256")
    if not isinstance(runtime_row, Mapping) or not isinstance(runtime_hash, str):
        raise ValueError("published episode runtime receipt is missing")
    canonical_runtime_receipt(runtime_row, runtime_hash)
    if runtime_row.get("checkpoint_sha256") != episode.get(
        "checkpoint_sha256"
    ):
        raise ValueError("published episode runtime/checkpoint mismatch")
    destination = Path(path)
    _atomic_json(destination, episode)
    return json_sha256(episode)


def record_failure(
    ledger_path: Path | str, *, episode_id: str, reason: str, details: Any = None
) -> None:
    path = Path(ledger_path)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(
            payload.get("failures"), list
        ):
            raise ValueError("invalid failures ledger")
    else:
        payload = {
            "schema_version": "failure-ledger-v1",
            "failures": [],
        }
    payload["failures"].append(
        {
            "episode_id": str(episode_id),
            "reason": str(reason),
            "details": details,
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    _atomic_json(path, payload)


def canonical_decision_trace(episode: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "public_projection": json.loads(
                json.dumps(row.get("public_projection"), allow_nan=False)
            ),
            "legal_semantic_options": json.loads(
                json.dumps(row.get("legal_semantic_options"), allow_nan=False)
            ),
            "legal_option_mask": list(row.get("legal_option_mask") or ()),
            "actor_option_mask": list(row.get("actor_option_mask") or ()),
            "teacher_action": list(row.get("teacher_action") or ()),
            "neural_shadow_action": list(
                row.get("neural_shadow_action") or ()
            ),
            "final_action": list(row.get("final_action") or ()),
            "ppo_eligible": row.get("ppo_eligible"),
            "fallback_used": row.get("fallback_used"),
            "protected": row.get("protected"),
            "fallback_reason": row.get("fallback_reason"),
            "model_failure_kind": row.get("model_failure_kind"),
            "model_timeout": row.get("model_timeout"),
            "sampled_stochastically": row.get("sampled_stochastically"),
            "q_latest": list(row.get("q_latest") or ()),
            "residuals": list(row.get("residuals") or ()),
            "final_probabilities": list(
                row.get("final_probabilities") or ()
            ),
            "behavior_logprob": row.get("behavior_logprob"),
        }
        for row in episode.get("decisions", ())
    )


def compare_duplicate_traces(
    first: Mapping[str, Any], second: Mapping[str, Any]
) -> dict[str, Any]:
    first_identity = {
        "run_id": first.get("run_id"),
        "opponent_id": first.get("opponent_id"),
        "seat": first.get("seat"),
        "seed": first.get("seed"),
    }
    second_identity = {
        "run_id": second.get("run_id"),
        "opponent_id": second.get("opponent_id"),
        "seat": second.get("seat"),
        "seed": second.get("seed"),
    }
    identity_equal = first_identity == second_identity
    terminal_equal = first.get("terminal_result") == second.get(
        "terminal_result"
    )
    engine_steps_equal = first.get("engine_steps") == second.get(
        "engine_steps"
    )
    left = canonical_decision_trace(first)
    right = canonical_decision_trace(second)
    mismatches = [
        index
        for index in range(max(len(left), len(right)))
        if index >= len(left) or index >= len(right) or left[index] != right[index]
    ]
    return {
        "equal": (
            identity_equal
            and terminal_equal
            and engine_steps_equal
            and not mismatches
        ),
        "identity_equal": identity_equal,
        "terminal_equal": terminal_equal,
        "engine_steps_equal": engine_steps_equal,
        "first_identity": first_identity,
        "second_identity": second_identity,
        "mismatch_indices": mismatches,
        "first_trace_sha256": json_sha256({"trace": left}),
        "second_trace_sha256": json_sha256({"trace": right}),
    }
