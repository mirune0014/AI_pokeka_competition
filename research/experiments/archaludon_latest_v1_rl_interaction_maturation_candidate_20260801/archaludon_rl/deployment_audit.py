"""Bounded opt-in JSONL telemetry for deployment-smoke policy decisions."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import threading
import time
from typing import Any, Iterable, Mapping
import uuid


AUDIT_DIRECTORY_ENVIRONMENT = "ARCHALUDON_RL_DEPLOYMENT_AUDIT_DIR"
AUDIT_SCHEMA_VERSION = "archaludon-deployment-audit-v1"
_PROCESS_REGISTRY_LOCK = threading.Lock()
_PROCESS_STREAMS: dict[int, dict[str, Any]] = {}


def _reset_process_registry_for_tests() -> None:
    """Forget closed test streams; production keeps one identity for each PID."""

    with _PROCESS_REGISTRY_LOCK:
        _PROCESS_STREAMS.clear()


def _json_line(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


class DeploymentAudit:
    """One append-only, fsynced audit stream owned by the current process."""

    def __init__(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError("deployment audit directory must be a real directory")
        self.directory = directory.resolve(strict=True)
        self._lock = threading.Lock()
        self._pid = -1
        self._process_identity = ""
        self._path: Path | None = None
        self._descriptor: int | None = None
        self._bind_current_process()

    @classmethod
    def from_environment(
        cls, environment: Mapping[str, str] | None = None
    ) -> DeploymentAudit | None:
        env = os.environ if environment is None else environment
        raw = env.get(AUDIT_DIRECTORY_ENVIRONMENT, "")
        if not raw:
            return None
        if raw != raw.strip():
            raise ValueError("deployment audit directory has surrounding whitespace")
        return cls(Path(raw))

    @property
    def path(self) -> Path:
        self._ensure_current_process()
        assert self._path is not None
        return self._path

    @property
    def process_identity(self) -> str:
        self._ensure_current_process()
        return self._process_identity

    def _bind_current_process(self) -> None:
        if self._descriptor is not None:
            os.close(self._descriptor)
        pid = os.getpid()
        with _PROCESS_REGISTRY_LOCK:
            registered = _PROCESS_STREAMS.get(pid)
            if registered is None:
                nonce = f"{pid}\0{time.time_ns()}\0{uuid.uuid4().hex}".encode(
                    "ascii"
                )
                identity = hashlib.sha256(nonce).hexdigest().upper()
                path = self.directory / f"deployment-audit-{pid}-{identity}.jsonl"
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_APPEND
                descriptor = os.open(path, flags, 0o600)
                registered = {
                    "directory": self.directory,
                    "identity": identity,
                    "path": path,
                    "lock": threading.Lock(),
                }
                _PROCESS_STREAMS[pid] = registered
            else:
                if registered["directory"] != self.directory:
                    raise ValueError(
                        "one process cannot own deployment audit streams in multiple directories"
                    )
                path = registered["path"]
                if not path.is_file() or path.is_symlink():
                    raise ValueError("registered deployment audit stream is unavailable")
                descriptor = os.open(path, os.O_WRONLY | os.O_APPEND)
            self._pid = pid
            self._process_identity = registered["identity"]
            self._path = registered["path"]
            self._lock = registered["lock"]
            self._descriptor = descriptor

    def _ensure_current_process(self) -> None:
        if self._pid != os.getpid():
            self._bind_current_process()

    def record(self, decision: Any, *, game_epoch: int, callback_ordinal: int) -> None:
        self._ensure_current_process()
        if (
            not isinstance(game_epoch, int)
            or isinstance(game_epoch, bool)
            or game_epoch <= 0
            or not isinstance(callback_ordinal, int)
            or isinstance(callback_ordinal, bool)
            or callback_ordinal <= 0
        ):
            raise ValueError("deployment audit ordinals must be positive integers")
        protected = bool(
            decision.fallback_used or decision.guard.protected_fallback.hard
        )
        if (
            decision.collection_mode != "deployment"
            or decision.sampled_stochastically
            or decision.ppo_eligible
        ):
            raise ValueError("deployment audit row is sampled or PPO-eligible")
        if protected and tuple(decision.action) != tuple(decision.teacher_action):
            raise ValueError("protected deployment decision is not teacher-exact")
        residuals = tuple(float(value) for value in decision.residuals)
        row = {
            "schema_version": AUDIT_SCHEMA_VERSION,
            "process_id": self._pid,
            "process_identity": self._process_identity,
            "game_epoch": game_epoch,
            "callback_ordinal": callback_ordinal,
            "collection_mode": decision.collection_mode,
            "checkpoint_sha256": decision.checkpoint_sha256,
            "action": list(decision.action),
            "teacher_action": list(decision.teacher_action),
            "neural_shadow_action": (
                None
                if decision.neural_shadow_action is None
                else list(decision.neural_shadow_action)
            ),
            "protected": protected,
            "fallback_used": bool(decision.fallback_used),
            "fallback_reason": decision.fallback_reason,
            "ppo_eligible": bool(decision.ppo_eligible),
            "sampled_stochastically": bool(decision.sampled_stochastically),
            "candidate_decision_used": bool(
                not protected and not decision.fallback_used
            ),
            "candidate_action_differs_from_teacher": bool(
                not protected
                and not decision.fallback_used
                and tuple(decision.action) != tuple(decision.teacher_action)
            ),
            "model_failure_kind": decision.model_failure_kind,
            "model_timeout": bool(decision.model_timeout),
            "legal_option_count": int(decision.legal_option_count),
            "residual_count": len(residuals),
            "residuals_finite": all(math.isfinite(value) for value in residuals),
            "behavior_receipt_sha256": decision.behavior_schema_sha256,
            "teacher_call_count": int(decision.teacher_call_count),
        }
        payload = _json_line(row)
        with self._lock:
            assert self._descriptor is not None
            offset = 0
            while offset < len(payload):
                written = os.write(self._descriptor, payload[offset:])
                if written <= 0:
                    raise OSError("deployment audit append made no progress")
                offset += written
            os.fsync(self._descriptor)

    def close(self) -> None:
        with self._lock:
            if self._descriptor is not None:
                os.close(self._descriptor)
                self._descriptor = None


def validate_deployment_audit_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    expected_checkpoint_sha256: str | None,
    require_no_model_failures: bool = True,
) -> dict[str, Any]:
    materialized = [dict(row) for row in rows]
    if not materialized:
        raise ValueError("deployment audit contains no rows")
    required = {
        "schema_version",
        "process_id",
        "process_identity",
        "game_epoch",
        "callback_ordinal",
        "collection_mode",
        "checkpoint_sha256",
        "action",
        "teacher_action",
        "neural_shadow_action",
        "protected",
        "fallback_used",
        "fallback_reason",
        "ppo_eligible",
        "sampled_stochastically",
        "candidate_decision_used",
        "candidate_action_differs_from_teacher",
        "model_failure_kind",
        "model_timeout",
        "legal_option_count",
        "residual_count",
        "residuals_finite",
        "behavior_receipt_sha256",
        "teacher_call_count",
    }
    process_identities: dict[int, str] = {}
    previous_ordinals: dict[tuple[int, str, int], int] = {}
    model_failures = 0
    model_timeouts = 0
    protected_count = 0
    candidate_decisions = 0
    candidate_action_changes = 0
    for row in materialized:
        if set(row) != required or row.get("schema_version") != AUDIT_SCHEMA_VERSION:
            raise ValueError("deployment audit row schema mismatch")
        if (
            row.get("collection_mode") != "deployment"
            or row.get("ppo_eligible") is not False
            or row.get("sampled_stochastically") is not False
        ):
            raise ValueError("deployment audit contains sampled/PPO-eligible row")
        if row.get("checkpoint_sha256") != expected_checkpoint_sha256:
            raise ValueError("deployment audit checkpoint mismatch")
        if row.get("teacher_call_count") != 1:
            raise ValueError("deployment audit teacher-call count mismatch")
        if row.get("residuals_finite") is not True:
            raise ValueError("deployment audit contains non-finite residuals")
        pid = row.get("process_id")
        identity = row.get("process_identity")
        epoch = row.get("game_epoch")
        ordinal = row.get("callback_ordinal")
        if (
            not isinstance(pid, int)
            or isinstance(pid, bool)
            or pid <= 0
            or not isinstance(identity, str)
            or len(identity) != 64
            or not isinstance(epoch, int)
            or isinstance(epoch, bool)
            or epoch <= 0
            or not isinstance(ordinal, int)
            or isinstance(ordinal, bool)
            or ordinal <= 0
        ):
            raise ValueError("deployment audit process/game identity is invalid")
        prior_identity = process_identities.get(pid)
        if prior_identity is not None and prior_identity != identity:
            raise ValueError("deployment audit has duplicate process ID identities")
        process_identities[pid] = identity
        sequence_key = (pid, identity, epoch)
        expected_ordinal = previous_ordinals.get(sequence_key, 0) + 1
        if ordinal != expected_ordinal:
            raise ValueError("deployment audit callback ordinal is not contiguous")
        previous_ordinals[sequence_key] = ordinal
        protected = row.get("protected")
        fallback = row.get("fallback_used")
        if not isinstance(protected, bool) or not isinstance(fallback, bool):
            raise ValueError("deployment audit protection flags are invalid")
        if protected:
            protected_count += 1
            if row.get("action") != row.get("teacher_action"):
                raise ValueError("deployment audit protected-action mismatch")
        failure_kind = row.get("model_failure_kind")
        timeout = row.get("model_timeout")
        if failure_kind is not None:
            if not isinstance(failure_kind, str) or not fallback or not protected:
                raise ValueError("deployment audit model-failure status is inconsistent")
            model_failures += 1
        if timeout:
            if failure_kind != "TimeoutError":
                raise ValueError("deployment audit timeout status is inconsistent")
            model_timeouts += 1
        candidate = row.get("candidate_decision_used")
        changed = row.get("candidate_action_differs_from_teacher")
        if not isinstance(candidate, bool) or not isinstance(changed, bool):
            raise ValueError("deployment audit candidate-decision flags are invalid")
        expected_candidate = not protected and not fallback
        if candidate != expected_candidate:
            raise ValueError("deployment audit candidate-decision count is untrustworthy")
        expected_changed = candidate and row.get("action") != row.get("teacher_action")
        if changed != expected_changed:
            raise ValueError("deployment audit candidate-action delta is untrustworthy")
        candidate_decisions += int(candidate)
        candidate_action_changes += int(changed)
    if require_no_model_failures and model_failures:
        raise ValueError("deployment audit contains fail-closed model failures")
    return {
        "row_count": len(materialized),
        "process_count": len(process_identities),
        "protected_count": protected_count,
        "candidate_decision_count": candidate_decisions,
        "candidate_action_change_count": candidate_action_changes,
        "model_failure_count": model_failures,
        "model_timeout_count": model_timeouts,
    }


def load_and_validate_deployment_audit(
    directory: Path,
    *,
    expected_checkpoint_sha256: str | None,
    require_no_model_failures: bool = True,
) -> dict[str, Any]:
    paths = sorted(directory.glob("deployment-audit-*.jsonl"))
    if not paths:
        raise ValueError("deployment audit directory contains no process files")
    rows: list[dict[str, Any]] = []
    file_processes: set[int] = set()
    for path in paths:
        if not path.is_file() or path.is_symlink():
            raise ValueError("deployment audit contains a non-regular process file")
        file_rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line
        ]
        if not file_rows:
            raise ValueError("deployment audit process file is empty")
        identities = {
            (row.get("process_id"), row.get("process_identity"))
            for row in file_rows
        }
        if len(identities) != 1:
            raise ValueError("deployment audit file mixes process identities")
        identity = next(iter(identities))
        if identity[0] in file_processes:
            raise ValueError("deployment audit process has multiple files")
        file_processes.add(identity[0])
        expected_name = f"deployment-audit-{identity[0]}-{identity[1]}.jsonl"
        if path.name != expected_name:
            raise ValueError("deployment audit process filename mismatch")
        rows.extend(file_rows)
    summary = validate_deployment_audit_rows(
        rows,
        expected_checkpoint_sha256=expected_checkpoint_sha256,
        require_no_model_failures=require_no_model_failures,
    )
    if summary["process_count"] != len(paths):
        raise ValueError("deployment audit process/file count mismatch")
    return {**summary, "files": [str(path.resolve()) for path in paths]}
