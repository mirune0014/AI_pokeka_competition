from __future__ import annotations

import json
import os
import secrets
import sys
import time
import traceback
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any

from .artifacts import deck_hash, manifest_file_hashes, manifest_files, verify_artifact
from .config import DEFAULT_MAX_STEPS
from .decisions import (
    DecisionError,
    DecisionRequestState,
    InvalidSelectionError,
    UnsafeOptionError,
    build_decision_request,
    validate_agent_action,
)
from .deck import DeckValidationError, validate_deck
from .engine_runtime import EngineRuntime, load_runtime
from .failures import classify_failure, human_forfeit, normal_result
from .human_view import HumanViewProjector, ProjectionError, sanitize_public_logs
from .models import MatchPhase, MatchResult, MatchStateMachine
from .protocol import MessageTracker, ProtocolError, make_envelope, receive_message, send_message
from .replay import ReplayBuilder, ReplayError


PARENT_OPS = {"match.start", "deck.validate", "decision.submit", "match.forfeit", "worker.shutdown"}
AI_PRE_ACTION_CUE_MS = 150


def ai_delay_segments(milliseconds: int) -> tuple[int, int]:
    """Split the presentation interval into a short cue and a post-action dwell."""
    before = min(max(milliseconds, 0), AI_PRE_ACTION_CUE_MS)
    return before, max(0, milliseconds - before)


class WorkerFailure(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class MatchSpec:
    stage_path: Path
    artifact_manifest: dict[str, Any]
    human_deck: list[int]
    human_seat: int
    human_deck_source_sha256: str
    replay_path: Path
    max_steps: int
    ai_display_delay_ms: int

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "MatchSpec":
        if set(payload) != {
            "stage_path",
            "artifact_manifest",
            "human_deck",
            "human_seat",
            "human_deck_source_sha256",
            "replay_path",
            "max_steps",
            "ai_display_delay_ms",
        }:
            raise WorkerFailure("invalid_start_payload")
        artifact_manifest = payload["artifact_manifest"]
        deck = payload["human_deck"]
        seat = payload["human_seat"]
        source_sha256 = payload["human_deck_source_sha256"]
        max_steps = payload["max_steps"]
        ai_display_delay_ms = payload["ai_display_delay_ms"]
        if not isinstance(artifact_manifest, dict):
            raise WorkerFailure("invalid_artifact_manifest")
        try:
            manifest_files(artifact_manifest)
        except ValueError as exc:
            raise WorkerFailure("invalid_artifact_manifest") from exc
        if not isinstance(deck, list) or not all(type(card) is int for card in deck):
            raise WorkerFailure("invalid_human_deck")
        if type(seat) is not int or seat not in (0, 1):
            raise WorkerFailure("invalid_human_seat")
        if not isinstance(source_sha256, str) or (
            source_sha256
            and (len(source_sha256) != 64 or any(character not in "0123456789ABCDEFabcdef" for character in source_sha256))
        ):
            raise WorkerFailure("invalid_human_deck_source_hash")
        if type(max_steps) is not int or not 1 <= max_steps <= 100_000:
            raise WorkerFailure("invalid_max_steps")
        if type(ai_display_delay_ms) is not int or not 0 <= ai_display_delay_ms <= 10_000:
            raise WorkerFailure("invalid_ai_display_delay")
        if not isinstance(payload["stage_path"], str) or not isinstance(payload["replay_path"], str):
            raise WorkerFailure("invalid_path")
        return cls(
            Path(payload["stage_path"]).resolve(),
            artifact_manifest,
            deck,
            seat,
            source_sha256.upper() or deck_hash(deck),
            Path(payload["replay_path"]).resolve(),
            max_steps,
            ai_display_delay_ms,
        )


class WorkerSession:
    def __init__(self, connection: Connection, match_id: str, spec: MatchSpec):
        self.connection = connection
        self.match_id = match_id
        self.spec = spec
        self.tracker = MessageTracker()
        self.machine = MatchStateMachine()
        self.revision = 0
        self.steps = 0
        self.public_log: list[dict[str, Any]] = []
        self.last_view_revision = -1
        self.pending: DecisionRequestState | None = None
        self.runtime: EngineRuntime | None = None
        self.replay = ReplayBuilder(match_id)
        self.projector: HumanViewProjector | None = None
        self.battle_live = False
        self.replay_complete = True
        self.started_at = time.monotonic()
        self.started_at_utc = datetime.now(timezone.utc).isoformat()

    def emit(self, op: str, payload: dict[str, Any]) -> None:
        send_message(self.connection, make_envelope(op, self.match_id, payload))

    def move(self, phase: MatchPhase) -> None:
        self.machine.move(phase)
        self.emit("phase.changed", {"phase": phase.value})

    def _verified_runtime(self) -> EngineRuntime:
        report = verify_artifact(self.spec.stage_path, self.spec.artifact_manifest)
        if not report.verified:
            raise WorkerFailure("staged_artifact_mismatch")
        self.move(MatchPhase.STARTING)
        try:
            runtime = load_runtime(self.spec.stage_path, load_agent=True)
        except Exception as exc:
            raise WorkerFailure("runtime_load_failed") from exc
        known = set(runtime.card_names)
        try:
            validate_deck(self.spec.human_deck, known)
        except DeckValidationError as exc:
            raise WorkerFailure("human_deck_invalid") from exc
        self.runtime = runtime
        self.projector = HumanViewProjector(self.match_id, self.spec.human_seat, secrets.token_bytes(32), runtime.card_names)
        return runtime

    def _visual_state(self, obs: dict[str, Any], *, captured_after: str) -> tuple[str, dict[str, Any]]:
        assert self.runtime is not None
        try:
            visual_payload = self.runtime.visualize_data()
            visual = json.loads(visual_payload)
            if not isinstance(visual, list) or not visual or not isinstance(visual[-1], dict):
                raise ReplayError("visualizer history is empty")
            self.replay.ingest_visualizer(visual, revision=self.revision, captured_after=captured_after)
        except (ValueError, ReplayError) as exc:
            self.replay_complete = False
            raise WorkerFailure("replay_capture_failed") from exc
        return visual_payload, visual[-1]

    def _enrich_public_log(self, public: list[dict[str, Any]]) -> None:
        assert self.runtime is not None
        card_fields = (
            "card_id",
            "active_card_id",
            "bench_card_id",
            "before_card_id",
            "after_card_id",
            "target_card_id",
        )
        for item in public:
            for field in card_fields:
                card_id = item.get(field)
                fallback = self.runtime.card_names.get(card_id) if type(card_id) is int else None
                if fallback:
                    item[f"{field}_fallback_name"] = fallback
            attack_id = item.get("attack_id")
            attack_fallback = self.runtime.attack_names.get(attack_id) if type(attack_id) is int else None
            if attack_fallback:
                item["attack_fallback_name"] = attack_fallback

    def _send_view(
        self,
        obs: dict[str, Any],
        full_frame: dict[str, Any],
        *,
        action_actor_seat: int | None = None,
    ) -> None:
        if self.last_view_revision == self.revision:
            return
        assert self.projector is not None
        try:
            view = self.projector.project(full_frame, obs, revision=self.revision, phase=self.machine.phase)
        except ProjectionError as exc:
            raise WorkerFailure("unsafe_human_view_projection") from exc
        acting = (obs.get("current") or {}).get("yourIndex")
        logs_source = obs.get("logs", []) if acting == self.spec.human_seat else full_frame.get("logs", [])
        public = sanitize_public_logs(logs_source, human_seat=self.spec.human_seat)
        self._enrich_public_log(public)
        revision_log = [{"revision": self.revision, **item} for item in public]
        self.public_log.extend(revision_log)
        self.emit(
            "state.update",
            {
                "state": view,
                "public_log": revision_log,
                "action_actor_seat": action_actor_seat,
            },
        )
        self.last_view_revision = self.revision

    def _poll_control(self) -> MatchResult | None:
        while self.connection.poll(0):
            incoming = receive_message(
                self.connection,
                allowed_ops={"decision.submit", "match.forfeit", "worker.shutdown"},
            )
            self.tracker.accept(incoming)
            if incoming["match_id"] != self.match_id:
                raise WorkerFailure("match_id_mismatch")
            if incoming["message_type"] == "match.forfeit":
                return human_forfeit(self.spec.human_seat)
            if incoming["message_type"] == "worker.shutdown":
                raise WorkerFailure("parent_shutdown")
            self.emit("error", {"code": "decision_rejected", "summary": "現在は選択を受け付けていません。"})
        return None

    def _wait_for_human(self, obs: dict[str, Any]) -> list[int] | MatchResult:
        assert self.runtime is not None and self.projector is not None
        self.move(MatchPhase.WAITING_FOR_HUMAN)
        try:
            self.pending = build_decision_request(
                obs,
                self.revision,
                card_names=self.runtime.card_names,
                attack_names=self.runtime.attack_names,
                target_token=lambda card: self.projector.state_token_for_card(card, seat=self.spec.human_seat),
            )
        except UnsafeOptionError as exc:
            raise WorkerFailure("unsupported_safe_projection") from exc
        self.emit("decision.required", {"decision": self.pending.request})
        while True:
            incoming = receive_message(self.connection, allowed_ops={"decision.submit", "match.forfeit", "worker.shutdown"})
            self.tracker.accept(incoming)
            if incoming["match_id"] != self.match_id:
                raise WorkerFailure("match_id_mismatch")
            if incoming["message_type"] == "match.forfeit":
                return human_forfeit(self.spec.human_seat)
            if incoming["message_type"] == "worker.shutdown":
                raise WorkerFailure("parent_shutdown")
            payload = incoming["payload"]
            if set(payload) != {"request_id", "state_revision", "tokens"}:
                self.emit("error", {"code": "invalid_decision_payload", "summary": "選択を受理できません。"})
                continue
            try:
                action = self.pending.submit(payload["request_id"], payload["state_revision"], payload["tokens"])
            except DecisionError:
                self.emit("error", {"code": "decision_rejected", "summary": "古い、または不正な選択です。"})
                continue
            self.emit(
                "decision.accepted",
                {
                    "request_id": self.pending.request["request_id"],
                    "state_revision": self.pending.request["state_revision"],
                },
            )
            self.pending = None
            return action

    def _agent_action(self, obs: dict[str, Any]) -> list[int]:
        assert self.runtime is not None and self.runtime.agent is not None
        self.move(MatchPhase.AGENT_THINKING)
        pre_action_ms, _ = ai_delay_segments(self.spec.ai_display_delay_ms)
        if pre_action_ms:
            time.sleep(pre_action_ms / 1000.0)
        try:
            action = self.runtime.agent(obs)
        except BaseException as exc:
            raise WorkerFailure("agent_exception") from exc
        try:
            return validate_agent_action(obs, action)
        except InvalidSelectionError as exc:
            raise WorkerFailure("agent_invalid_action") from exc

    def _finish_battle(self) -> None:
        if self.battle_live and self.runtime is not None:
            try:
                self.runtime.battle_finish()
            finally:
                self.battle_live = False

    def _seal(self, result: MatchResult) -> tuple[Path, str]:
        assert self.runtime is not None
        artifact_hashes = manifest_file_hashes(self.spec.artifact_manifest)
        artifact = {
            "submission_id": self.spec.artifact_manifest.get("submission_id"),
            "artifact_manifest_id": self.spec.artifact_manifest["manifest_id"],
            "trust_mode": self.spec.artifact_manifest.get("trust_mode", "verified_submission"),
            "content_sha256": self.spec.artifact_manifest.get("content_sha256"),
            "files": artifact_hashes,
            "main_sha256": artifact_hashes["main.py"],
            "agent_deck_sha256": artifact_hashes["deck.csv"],
            "engine_dll_sha256": artifact_hashes["cg/cg.dll"],
        }
        settings = {
            "human_seat": self.spec.human_seat,
            "human_deck_source_sha256": self.spec.human_deck_source_sha256,
            "started_at_utc": self.started_at_utc,
            "max_steps": self.spec.max_steps,
            "ai_display_delay_ms": self.spec.ai_display_delay_ms,
            "seeded_reproduction": False,
            "app_protocol": 1,
        }
        decks = {
            "human": self.spec.human_deck,
            "human_sha256": deck_hash(self.spec.human_deck),
            "agent": self.runtime.agent_deck,
            "agent_sha256": deck_hash(self.runtime.agent_deck),
        }
        diagnostics = {
            "steps": self.steps,
            "elapsed_ms": round((time.monotonic() - self.started_at) * 1000),
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "final_phase": MatchPhase.FINISHED.value,
            "complete": self.replay_complete,
        }
        return self.replay.seal(
            self.spec.replay_path,
            artifact=artifact,
            settings=settings,
            decks=decks,
            public_log=self.public_log,
            result=result.to_dict(),
            diagnostics=diagnostics,
        )

    def run(self) -> None:
        self.emit("worker.ready", {"protocol_version": 1})
        runtime = self._verified_runtime()
        decks = [self.spec.human_deck, runtime.agent_deck] if self.spec.human_seat == 0 else [runtime.agent_deck, self.spec.human_deck]
        try:
            obs, start_data = runtime.battle_start(decks[0], decks[1])
        except Exception as exc:
            raise WorkerFailure("battle_start_failed") from exc
        if not obs:
            raise WorkerFailure(f"battle_start_rejected_{getattr(start_data, 'errorPlayer', 'x')}_{getattr(start_data, 'errorType', 'x')}")
        self.battle_live = True
        self.emit(
            "match.started",
            {
                "submission_id": self.spec.artifact_manifest.get("submission_id"),
                "artifact_manifest_id": self.spec.artifact_manifest["manifest_id"],
            },
        )
        _, full_frame = self._visual_state(obs, captured_after="battle_start")
        final_result: MatchResult | None = None
        failure_code: str | None = None
        try:
            while True:
                current = obs.get("current")
                if not isinstance(current, dict):
                    raise WorkerFailure("missing_current_state")
                engine_result = current.get("result")
                if engine_result in (0, 1, 2):
                    final_result = normal_result(engine_result)
                    break
                control_result = self._poll_control()
                if control_result is not None:
                    final_result = control_result
                    break
                if self.steps >= self.spec.max_steps:
                    raise WorkerFailure("max_steps")
                select = obs.get("select")
                if not isinstance(select, dict) or not isinstance(select.get("option"), list):
                    raise WorkerFailure("missing_legal_options")
                if not select["option"] and not (
                    select.get("minCount") == 0 and select.get("maxCount") == 0
                ):
                    raise WorkerFailure("missing_legal_options")
                self._send_view(obs, full_frame)
                acting_seat = current.get("yourIndex")
                if acting_seat == self.spec.human_seat:
                    action_or_result = self._wait_for_human(obs)
                    if isinstance(action_or_result, MatchResult):
                        final_result = action_or_result
                        break
                    action = action_or_result
                    actor_is_agent = False
                elif acting_seat == 1 - self.spec.human_seat:
                    action = self._agent_action(obs)
                    actor_is_agent = True
                    control_result = self._poll_control()
                    if control_result is not None:
                        final_result = control_result
                        break
                else:
                    raise WorkerFailure("invalid_acting_seat")
                self.move(MatchPhase.ENGINE_PROCESSING)
                try:
                    obs = runtime.battle_select(action)
                except Exception as exc:
                    code = "agent_selection_rejected" if actor_is_agent else "engine_rejected_human_selection"
                    raise WorkerFailure(code) from exc
                self.steps += 1
                self.revision += 1
                _, full_frame = self._visual_state(obs, captured_after="battle_select")
                self._send_view(obs, full_frame, action_actor_seat=acting_seat)
                if actor_is_agent:
                    _, post_action_ms = ai_delay_segments(self.spec.ai_display_delay_ms)
                    if post_action_ms:
                        time.sleep(post_action_ms / 1000.0)
        except WorkerFailure as exc:
            failure_code = exc.code
            final_result = classify_failure(exc.code, self.spec.human_seat, phase=self.machine.phase)
        assert final_result is not None
        final_current = full_frame.get("current") if isinstance(full_frame, dict) else {}
        first_player = final_current.get("firstPlayer") if isinstance(final_current, dict) else None
        turn_count = final_current.get("turn") if isinstance(final_current, dict) else 0
        final_result = replace(
            final_result,
            artifact_manifest_id=self.spec.artifact_manifest["manifest_id"],
            human_seat=self.spec.human_seat,
            first_player=first_player if first_player in (0, 1) else None,
            turn_count=turn_count if type(turn_count) is int else 0,
            battle_select_count=self.steps,
            replay_complete=self.replay_complete,
        )
        self.move(MatchPhase.FINISHING)
        self._finish_battle()
        self.move(MatchPhase.FINISHED)
        try:
            replay_path, replay_hash = self._seal(final_result)
        except Exception as exc:
            raise WorkerFailure("replay_seal_failed") from exc
        self.move(MatchPhase.REPLAY_SEALED)
        self.emit(
            "replay.sealed",
            {
                "path": str(replay_path),
                "sha256": replay_hash,
                "schema_version": 1,
                "failure_code": failure_code,
                "complete": self.replay_complete,
            },
        )
        self.emit("match.finished", {"result": final_result.to_dict()})


def _validate_deck(connection: Connection, envelope: dict[str, Any]) -> None:
    match_id = envelope["match_id"]
    payload = envelope["payload"]
    if set(payload) != {"stage_path", "artifact_manifest", "human_deck", "human_seat"}:
        raise WorkerFailure("invalid_deck_validation_payload")
    stage = Path(payload["stage_path"]).resolve() if isinstance(payload["stage_path"], str) else None
    artifact_manifest = payload["artifact_manifest"]
    deck = payload["human_deck"]
    seat = payload["human_seat"]
    if (
        stage is None
        or not isinstance(artifact_manifest, dict)
        or not isinstance(deck, list)
        or not all(type(card) is int for card in deck)
        or seat not in (0, 1)
    ):
        raise WorkerFailure("invalid_deck_validation_payload")
    report = verify_artifact(stage, artifact_manifest)
    if not report.verified:
        raise WorkerFailure("staged_artifact_mismatch")
    runtime = load_runtime(stage, load_agent=True)
    validated = validate_deck(deck, set(runtime.card_names))
    deck_list = [
        {
            "card_id": card_id,
            "count": validated.cards.count(card_id),
            "name": runtime.card_names.get(card_id, f"カード {card_id}"),
        }
        for card_id in sorted(set(validated.cards))
    ]
    decks = [list(validated.cards), runtime.agent_deck] if seat == 0 else [runtime.agent_deck, list(validated.cards)]
    battle_live = False
    try:
        obs, start_data = runtime.battle_start(decks[0], decks[1])
        if not obs:
            send_message(
                connection,
                make_envelope(
                    "deck.validated",
                    match_id,
                    {
                        "structure_verified": True,
                        "known_ids_verified": True,
                        "engine_accepted": False,
                        "error_player": getattr(start_data, "errorPlayer", None),
                        "error_type": getattr(start_data, "errorType", None),
                        "regulation_verified": False,
                        "deck_list": deck_list,
                    },
                ),
            )
            return
        battle_live = True
        send_message(
            connection,
            make_envelope(
                "deck.validated",
                match_id,
                {
                    "structure_verified": True,
                    "known_ids_verified": True,
                    "engine_accepted": True,
                    "error_player": None,
                    "error_type": None,
                    "regulation_verified": False,
                    "deck_list": deck_list,
                },
            ),
        )
    finally:
        if battle_live:
            runtime.battle_finish()


def worker_main(connection: Connection) -> None:
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    devnull = open(os.devnull, "w", encoding="utf-8")
    sys.stdout = devnull
    sys.stderr = devnull
    match_id = "bootstrap"
    try:
        first = receive_message(connection, allowed_ops={"match.start", "deck.validate"})
        match_id = first["match_id"]
        if first["message_type"] == "deck.validate":
            _validate_deck(connection, first)
        else:
            spec = MatchSpec.from_payload(first["payload"])
            WorkerSession(connection, match_id, spec).run()
    except (EOFError, BrokenPipeError):
        pass
    except BaseException as exc:
        try:
            code = exc.code if isinstance(exc, WorkerFailure) else "worker_unhandled"
            send_message(
                connection,
                make_envelope(
                    "error",
                    match_id,
                    {"code": code, "summary": "対戦ワーカーが終了しました。", "exception_type": type(exc).__name__},
                ),
            )
        except BaseException:
            pass
    finally:
        try:
            connection.close()
        finally:
            devnull.close()
