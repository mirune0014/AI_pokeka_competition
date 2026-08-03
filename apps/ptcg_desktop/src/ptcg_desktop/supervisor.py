from __future__ import annotations

import multiprocessing
import time
import uuid
from dataclasses import dataclass
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any

from .artifacts import ArtifactVerificationError, cleanup_stage, sha256_file, stage_artifact, trusted_manifest
from .config import DEFAULT_AGENT_TIMEOUT_SECONDS, DEFAULT_ENGINE_TIMEOUT_SECONDS, DEFAULT_MAX_STEPS
from .deck import validate_deck
from .failures import classify_failure
from .models import MatchPhase, MatchResult
from .protocol import MessageTracker, ProtocolError, make_envelope, receive_message, send_message
from .replay import ReplayError, load_replay
from .windows_job import JobObjectError, WindowsJob
from .worker import worker_main


class SupervisorError(RuntimeError):
    pass


WORKER_EVENT_OPS = {
    "worker.ready",
    "phase.changed",
    "match.started",
    "state.update",
    "decision.required",
    "decision.accepted",
    "match.finished",
    "replay.sealed",
    "error",
}
NON_FATAL_WORKER_ERRORS = {"invalid_decision_payload", "decision_rejected"}


@dataclass(frozen=True)
class MatchLaunch:
    artifact_source: Path
    human_deck: list[int]
    human_seat: int
    replay_path: Path
    artifact_manifest: dict[str, Any] | None = None
    human_deck_source_sha256: str = ""
    max_steps: int = DEFAULT_MAX_STEPS
    ai_display_delay_ms: int = 0
    agent_timeout_seconds: float = DEFAULT_AGENT_TIMEOUT_SECONDS
    engine_timeout_seconds: float = DEFAULT_ENGINE_TIMEOUT_SECONDS


class MatchSupervisor:
    def __init__(self) -> None:
        self.context = multiprocessing.get_context("spawn")
        self.process: multiprocessing.Process | None = None
        self.connection: Connection | None = None
        self.job: WindowsJob | None = None
        self.match_id: str | None = None
        self.stage_path: Path | None = None
        self.human_seat = 0
        self.ai_display_delay_ms = 0
        self.agent_timeout_seconds = DEFAULT_AGENT_TIMEOUT_SECONDS
        self.engine_timeout_seconds = DEFAULT_ENGINE_TIMEOUT_SECONDS
        self.exit_code: int | None = None
        self.match_finished_received = False
        self.last_phase = MatchPhase.PREPARING
        self.phase_started = time.monotonic()
        self.result: MatchResult | None = None
        self.replay_candidate: dict[str, Any] | None = None
        self.replay_available = False
        self.tracker = MessageTracker()
        self.events: list[dict[str, Any]] = []

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.is_alive()

    @property
    def finalized(self) -> bool:
        """Return true only after exit handling and replay verification finish."""
        return self.process is None and self.exit_code is not None

    def start(self, launch: MatchLaunch) -> str:
        if self.process is not None:
            raise SupervisorError("a worker already exists")
        validate_deck(launch.human_deck)
        if launch.human_seat not in (0, 1):
            raise ValueError("human seat must be 0 or 1")
        if type(launch.ai_display_delay_ms) is not int or not 0 <= launch.ai_display_delay_ms <= 10_000:
            raise ValueError("AI display delay must be between 0 and 10000 ms")
        if not 1.0 <= float(launch.agent_timeout_seconds) <= 600.0:
            raise ValueError("agent timeout must be between 1 and 600 seconds")
        if not 1.0 <= float(launch.engine_timeout_seconds) <= 600.0:
            raise ValueError("engine timeout must be between 1 and 600 seconds")
        self.human_seat = launch.human_seat
        self.ai_display_delay_ms = launch.ai_display_delay_ms
        self.agent_timeout_seconds = float(launch.agent_timeout_seconds)
        self.engine_timeout_seconds = float(launch.engine_timeout_seconds)
        self.exit_code = None
        self.match_finished_received = False
        self.match_id = str(uuid.uuid4())
        artifact_manifest = launch.artifact_manifest or trusted_manifest()
        self.stage_path = stage_artifact(launch.artifact_source, self.match_id, manifest=artifact_manifest)
        parent: Connection | None = None
        child: Connection | None = None
        process: multiprocessing.Process | None = None
        job: WindowsJob | None = None
        try:
            parent, child = self.context.Pipe(duplex=True)
            process = self.context.Process(target=worker_main, args=(child,), name=f"PTCGMatch-{self.match_id}")
            process.start()
            child.close()
            child = None
            job = WindowsJob()
            job.assign_pid(process.pid)
            payload = {
                "stage_path": str(self.stage_path),
                "artifact_manifest": artifact_manifest,
                "human_deck": list(launch.human_deck),
                "human_seat": launch.human_seat,
                "human_deck_source_sha256": launch.human_deck_source_sha256,
                "replay_path": str(launch.replay_path.resolve()),
                "max_steps": launch.max_steps,
                "ai_display_delay_ms": launch.ai_display_delay_ms,
            }
            send_message(parent, make_envelope("match.start", self.match_id, payload))
        except Exception:
            if child is not None:
                child.close()
            if process is not None and process.pid is not None:
                try:
                    if process.is_alive():
                        if job is not None:
                            job.terminate(70)
                        else:
                            process.terminate()
                    process.join(timeout=5)
                except Exception:
                    pass
            if parent is not None:
                parent.close()
            if job is not None:
                job.close()
            self._cleanup_stage()
            self.process = None
            self.connection = None
            self.job = None
            raise
        self.connection = parent
        self.process = process
        self.job = job
        return self.match_id

    def _handle(self, event: dict[str, Any]) -> None:
        self.tracker.accept(event)
        if event["match_id"] != self.match_id:
            raise SupervisorError("worker sent a different match id")
        op = event["message_type"]
        payload = event["payload"]
        if op == "phase.changed":
            self.last_phase = MatchPhase(payload["phase"])
            self.phase_started = time.monotonic()
        elif op == "match.finished":
            raw = payload["result"]
            self.result = MatchResult(**raw)
            self.match_finished_received = True
        elif op == "replay.sealed":
            self.replay_candidate = dict(payload)
        elif op == "error":
            code = payload.get("code")
            if isinstance(code, str) and code not in NON_FATAL_WORKER_ERRORS:
                self.result = classify_failure(code, self.human_seat, phase=self.last_phase)
        self.events.append(event)

    def _receive_one(self) -> None:
        assert self.connection is not None
        self._handle(receive_message(self.connection, allowed_ops=WORKER_EVENT_OPS))

    def poll(self, timeout: float = 0.0) -> list[dict[str, Any]]:
        if self.connection is None:
            return []
        start = len(self.events)
        try:
            if timeout > 0 and self.connection.poll(timeout):
                self._receive_one()
            while self.connection is not None and self.connection.poll(0):
                self._receive_one()
        except (ProtocolError, SupervisorError, KeyError, TypeError, ValueError):
            self.result = classify_failure("ipc_protocol_error", self.human_seat, phase=self.last_phase)
            self.terminate()
        except (EOFError, BrokenPipeError, OSError):
            # A normal worker closes its endpoint immediately before the process
            # fully exits. Preserve an already received terminal result instead
            # of relabeling that short close/exit race as an IPC failure.
            if self.running and self.result is None:
                self.result = classify_failure("ipc_disconnected", self.human_seat, phase=self.last_phase)
                self.terminate()
        self._enforce_timeout()
        self._finalize_if_exited()
        return self.events[start:]

    def _enforce_timeout(self) -> None:
        if not self.running:
            return
        elapsed = time.monotonic() - self.phase_started
        limit = (
            self.agent_timeout_seconds + self.ai_display_delay_ms / 1000.0
            if self.last_phase == MatchPhase.AGENT_THINKING
            else self.engine_timeout_seconds
        )
        if self.last_phase == MatchPhase.WAITING_FOR_HUMAN:
            return
        if elapsed > limit:
            human_seat = self._human_seat_from_events()
            self.result = classify_failure("timeout", human_seat, phase=self.last_phase)
            self.terminate()

    def _human_seat_from_events(self) -> int:
        for event in reversed(self.events):
            state = event.get("payload", {}).get("state")
            if isinstance(state, dict) and state.get("human_seat") in (0, 1):
                return state["human_seat"]
        return self.human_seat

    def submit_decision(self, request_id: str, state_revision: int, tokens: list[str]) -> None:
        if self.connection is None or self.match_id is None:
            raise SupervisorError("no active match")
        send_message(
            self.connection,
            make_envelope(
                "decision.submit",
                self.match_id,
                {"request_id": request_id, "state_revision": state_revision, "tokens": list(tokens)},
            ),
        )

    def forfeit(self) -> None:
        if self.connection is None or self.match_id is None:
            raise SupervisorError("no active match")
        send_message(self.connection, make_envelope("match.forfeit", self.match_id, {}))

    def terminate(self) -> None:
        if self.process is not None and self.process.is_alive():
            try:
                if self.job is not None:
                    self.job.terminate(70)
                else:
                    self.process.terminate()
            except Exception:
                self.process.terminate()
            self.process.join(timeout=5)
        self._finalize_if_exited()

    def _finalize_if_exited(self) -> None:
        if self.process is None or self.process.is_alive():
            return
        if self.connection is not None:
            try:
                while self.connection.poll(0.05):
                    self._receive_one()
            except (EOFError, BrokenPipeError, OSError):
                pass
            except (ProtocolError, SupervisorError, KeyError, TypeError, ValueError):
                self.result = classify_failure("ipc_protocol_error", self.human_seat, phase=self.last_phase)
        self.process.join(timeout=0)
        self.exit_code = self.process.exitcode
        self.replay_available = False
        if self.replay_candidate is not None:
            try:
                if self.replay_candidate.get("complete") is not True:
                    raise ReplayError("replay is explicitly incomplete")
                path = Path(self.replay_candidate["path"]).resolve()
                if sha256_file(path) != self.replay_candidate["sha256"]:
                    raise ReplayError("sealed replay hash mismatch")
                replay = load_replay(path)
                if replay.manifest.get("complete") is not True:
                    raise ReplayError("sealed replay manifest is incomplete")
                replay_result = MatchResult(**replay.result)
                if replay_result.replay_complete is not True:
                    raise ReplayError("sealed replay result is incomplete")
                if self.result is None:
                    # replay.sealed is emitted only after the atomic rename.
                    # If the worker exits before match.finished, the verified
                    # replay result completes the terminal transaction.
                    self.result = replay_result
                    self.match_finished_received = True
                elif self.result.to_dict() != replay_result.to_dict():
                    raise ReplayError("terminal result disagrees with sealed replay")
                self.replay_available = True
            except (OSError, KeyError, TypeError, ValueError, ReplayError):
                self.replay_available = False
                if self.result is None or self.replay_candidate.get("complete") is True:
                    self.result = classify_failure(
                        "replay_verification_failed",
                        self._human_seat_from_events(),
                        phase=self.last_phase,
                    )
        if self.result is None:
            self.result = classify_failure("worker_exit", self._human_seat_from_events(), phase=self.last_phase)
        elif (
            self.replay_candidate is None
            and self.match_finished_received
            and self.result.classification != "system_error"
        ):
            self.result = classify_failure("replay_missing", self.human_seat, phase=self.last_phase)
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        if self.job is not None:
            self.job.close()
            self.job = None
        self._cleanup_stage()
        self.process = None

    def _cleanup_stage(self) -> None:
        if self.stage_path is not None:
            try:
                cleanup_stage(self.stage_path)
            except OSError:
                pass
            self.stage_path = None

    def close(self) -> None:
        if self.process is not None and self.process.is_alive():
            try:
                if self.connection is not None and self.match_id is not None:
                    send_message(self.connection, make_envelope("worker.shutdown", self.match_id, {}))
            except Exception:
                pass
            self.process.join(timeout=1)
            if self.process.is_alive():
                self.terminate()
        self._finalize_if_exited()


def validate_deck_in_worker(
    stage_path: Path,
    deck: list[int],
    human_seat: int,
    *,
    artifact_manifest: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    validate_deck(deck)
    selected_manifest = artifact_manifest or trusted_manifest()
    context = multiprocessing.get_context("spawn")
    parent: Connection | None = None
    child: Connection | None = None
    process: multiprocessing.Process | None = None
    job: WindowsJob | None = None
    try:
        parent, child = context.Pipe(duplex=True)
        process = context.Process(target=worker_main, args=(child,), name="PTCGDeckValidation")
        process.start()
        child.close()
        child = None
        job = WindowsJob()
        job.assign_pid(process.pid)
        match_id = f"deck-{uuid.uuid4()}"
        send_message(
            parent,
            make_envelope(
                "deck.validate",
                match_id,
                {
                    "stage_path": str(stage_path.resolve()),
                    "artifact_manifest": selected_manifest,
                    "human_deck": list(deck),
                    "human_seat": human_seat,
                },
            ),
        )
        if not parent.poll(timeout):
            job.terminate(71)
            process.join(timeout=5)
            raise SupervisorError("deck validation timed out")
        event = receive_message(parent, allowed_ops={"deck.validated", "error"})
        if event["message_type"] == "error":
            raise SupervisorError(event["payload"].get("code", "deck validation failed"))
        process.join(timeout=5)
        if process.is_alive():
            job.terminate(72)
            process.join(timeout=5)
        return event["payload"]
    finally:
        if child is not None:
            child.close()
        if process is not None and process.pid is not None:
            try:
                if process.is_alive():
                    if job is not None:
                        job.terminate(72)
                    else:
                        process.terminate()
                process.join(timeout=5)
            except Exception:
                pass
        if parent is not None:
            parent.close()
        if job is not None:
            job.close()
