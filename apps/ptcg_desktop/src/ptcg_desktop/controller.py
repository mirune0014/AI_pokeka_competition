from __future__ import annotations

import copy
import json
import os
import secrets
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from .artifacts import (
    ArtifactVerificationError,
    cleanup_stage,
    register_local_artifact,
    sha256_bytes,
    sha256_file,
    stage_artifact,
)
from .card_catalog import CardCatalog
from .config import default_replay_dir, logs_dir
from .deck import read_deck_csv_snapshot, validate_deck
from .replay import ReplayData, ReplayError, export_visualizer_json, load_replay
from .settings import load_settings, save_settings
from .supervisor import MatchLaunch, MatchSupervisor, validate_deck_in_worker


AGENT_ARCHIVE_FILTER = "エージェントアーカイブ (*.tar.gz *.tgz *.gz);;すべてのファイル (*.*)"


class AppController(QObject):
    screenChanged = Signal()
    setupChanged = Signal()
    busyChanged = Signal()
    errorChanged = Signal()
    matchChanged = Signal()
    replayChanged = Signal()
    shortcutRequested = Signal(str)
    _backgroundDone = Signal(str, object)

    def __init__(self) -> None:
        super().__init__()
        self._screen = "setup"
        self._busy = False
        self._error = ""
        self._settings = load_settings()
        self._artifact_verified = False
        self._artifact_status = "未登録"
        self._artifact_report: dict[str, Any] = {}
        self._artifact_manifest: dict[str, Any] = {}
        self._artifact_trust_mode = "unregistered"
        self._deck_status: dict[str, Any] = {
            "structure": False,
            "known_ids": False,
            "engine": False,
            "regulation": False,
            "cards": [],
        }
        self._human_deck: list[int] = []
        self._human_deck_source_sha256 = ""
        self._state: dict[str, Any] = {}
        self._decision: dict[str, Any] = {}
        self._decision_submitting = False
        self._public_log: list[dict[str, Any]] = []
        self._latest_action_text = "対戦開始を待っています。"
        self._latest_action_title = "対戦状況"
        self._latest_action_revision = -1
        self._result: dict[str, Any] = {}
        self._diagnostics: dict[str, Any] = {}
        self._replay_path = ""
        self._visualizer_json_path = ""
        self._visualizer_json_exact = False
        self._replay_frames: list[dict[str, Any]] = []
        self._replay_public_log: list[dict[str, Any]] = []
        self._replay_index = 0
        self._replay_full_information = False
        self._replay_human_seat = 0
        self._catalog = CardCatalog(self._settings.get("image_folder") or None)
        self._supervisor: MatchSupervisor | None = None
        self._pending_supervisor: MatchSupervisor | None = None
        self._pending_match_identity: dict[str, Any] = {}
        self._active_match_identity: dict[str, Any] = {}
        self._launch_lock = threading.Lock()
        self._shutting_down = False
        self._last_human_seat = 0
        self._result_presented = False
        self._backgroundDone.connect(self._on_background_done)
        self._timer = QTimer(self)
        self._timer.setInterval(25)
        self._timer.timeout.connect(self._poll_match)
        self._timer.start()

    @Property(str, notify=screenChanged)
    def screen(self) -> str:
        return self._screen

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=errorChanged)
    def errorText(self) -> str:
        return self._error

    @Property(str, notify=setupChanged)
    def artifactPath(self) -> str:
        return self._settings["artifact_path"]

    @Property(str, notify=setupChanged)
    def deckPath(self) -> str:
        return self._settings["deck_path"]

    @Property(str, notify=setupChanged)
    def imageFolder(self) -> str:
        return self._settings["image_folder"]

    @Property(str, notify=setupChanged)
    def replayFolder(self) -> str:
        return self._settings.get("replay_folder") or str(default_replay_dir())

    @Property(int, notify=setupChanged)
    def humanSeat(self) -> int:
        return self._settings["human_seat"]

    @Property(int, notify=setupChanged)
    def aiDisplayDelayMs(self) -> int:
        return self._settings["ai_display_delay_ms"]

    @Property(int, notify=setupChanged)
    def agentTimeoutSeconds(self) -> int:
        return self._settings["agent_timeout_seconds"]

    @Property(str, notify=setupChanged)
    def artifactStatus(self) -> str:
        return self._artifact_status

    @Property(bool, notify=setupChanged)
    def artifactReady(self) -> bool:
        return self._artifact_verified

    @Property(bool, notify=setupChanged)
    def verifiedMatch(self) -> bool:
        return self._artifact_verified and self._artifact_trust_mode == "verified_submission"

    @Property(bool, notify=setupChanged)
    def localAgentRegistered(self) -> bool:
        return self._artifact_verified and self._artifact_trust_mode == "local_registered"

    @Property(str, notify=setupChanged)
    def matchIdentityText(self) -> str:
        if self.verifiedMatch:
            return "Verified Submission · submission 55155015"
        if self.localAgentRegistered:
            identifier = str(self._artifact_manifest.get("manifest_id", "local"))
            return "自己管理ローカルエージェント · " + identifier
        return "未検証のエージェント"

    @Property("QVariantMap", notify=setupChanged)
    def artifactDetails(self) -> dict[str, Any]:
        return copy.deepcopy(self._artifact_report)

    @Property("QVariantMap", notify=setupChanged)
    def deckStatus(self) -> dict[str, Any]:
        return copy.deepcopy(self._deck_status)

    @Property(bool, notify=setupChanged)
    def canStart(self) -> bool:
        return (
            self._artifact_verified
            and bool(self._artifact_manifest)
            and all(self._deck_status.get(key) is True for key in ("structure", "known_ids", "engine"))
            and set(self._deck_status.get("validated_seats", [])) == {0, 1}
            and not self._busy
        )

    @Property("QVariantMap", notify=matchChanged)
    def stateData(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    @Property("QVariantMap", notify=matchChanged)
    def decisionData(self) -> dict[str, Any]:
        value = copy.deepcopy(self._decision)
        if value:
            value["submitting"] = self._decision_submitting
        return value

    @Property("QVariantList", notify=matchChanged)
    def publicLog(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._public_log[-200:])

    @Property(str, notify=matchChanged)
    def latestActionText(self) -> str:
        return self._latest_action_text

    @Property(str, notify=matchChanged)
    def latestActionTitle(self) -> str:
        return self._latest_action_title

    @Property(int, notify=matchChanged)
    def latestActionRevision(self) -> int:
        return self._latest_action_revision

    @Property("QVariantMap", notify=matchChanged)
    def resultData(self) -> dict[str, Any]:
        return copy.deepcopy(self._result)

    @Property("QVariantMap", notify=matchChanged)
    def diagnosticsData(self) -> dict[str, Any]:
        return copy.deepcopy(self._diagnostics)

    @Property(bool, notify=matchChanged)
    def replayAvailable(self) -> bool:
        return bool(self._replay_path and self._replay_frames)

    @Property(bool, notify=matchChanged)
    def visualizerJsonAvailable(self) -> bool:
        return bool(self._visualizer_json_path and Path(self._visualizer_json_path).is_file())

    @Property(str, notify=matchChanged)
    def visualizerJsonFileName(self) -> str:
        return Path(self._visualizer_json_path).name if self._visualizer_json_path else ""

    @Property(bool, notify=matchChanged)
    def visualizerJsonExact(self) -> bool:
        return self._visualizer_json_exact

    @Property(bool, notify=matchChanged)
    def officialVisualizerLauncherAvailable(self) -> bool:
        return self.visualizerJsonAvailable and self._official_visualizer_launcher_path().is_file()

    @Property(int, notify=replayChanged)
    def replayIndex(self) -> int:
        return self._replay_index

    @Property(int, notify=replayChanged)
    def replayCount(self) -> int:
        return len(self._replay_frames)

    @Property(bool, notify=replayChanged)
    def replayFullInformation(self) -> bool:
        return self._replay_full_information

    @Property("QVariantList", notify=replayChanged)
    def replayPublicLog(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._replay_public_log)

    @Property("QVariantMap", notify=replayChanged)
    def replayFrame(self) -> dict[str, Any]:
        if not self._replay_frames:
            return {}
        frame = self._replay_frames[self._replay_index]
        if self._replay_full_information:
            return copy.deepcopy(frame)
        return self._human_replay_frame(frame, self._replay_human_seat)

    def _set_busy(self, value: bool) -> None:
        if self._busy != value:
            self._busy = value
            self.busyChanged.emit()
            self.setupChanged.emit()

    def _set_error(self, text: str) -> None:
        self._error = text
        self.errorChanged.emit()

    def _run_background(self, operation: str, function: Callable[[], Any]) -> None:
        if self._busy:
            return
        self._set_busy(True)
        self._set_error("")

        def run() -> None:
            try:
                value: object = {"ok": True, "value": function()}
            except Exception as exc:
                value = {"ok": False, "type": type(exc).__name__}
                if isinstance(exc, ArtifactVerificationError):
                    value["report"] = exc.report.to_dict()
            self._backgroundDone.emit(operation, value)

        threading.Thread(target=run, daemon=True, name=f"PTCG-{operation}").start()

    def _select_artifact(self, selected: str) -> None:
        if not selected:
            return
        self._settings["artifact_path"] = selected
        self._artifact_verified = False
        self._artifact_status = "未登録です。内容フィンガープリントを確認して登録してください。"
        self._artifact_report = {}
        self._artifact_manifest = {}
        self._artifact_trust_mode = "unregistered"
        self._deck_status["engine"] = False
        self._deck_status["validated_seats"] = []
        self.setupChanged.emit()

    @Slot()
    def browseArtifact(self) -> None:
        self.browseArtifactArchive()

    @Slot()
    def browseArtifactArchive(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            None,
            "ローカルエージェントの tar.gz ファイルを選択",
            self.artifactPath,
            AGENT_ARCHIVE_FILTER,
        )
        self._select_artifact(selected)

    @Slot()
    def browseArtifactFolder(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            None,
            "展開済みローカルエージェントの実行ルートを選択",
            self.artifactPath,
        )
        self._select_artifact(selected)

    @Slot()
    def browseDeck(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            None,
            "60 枚デッキ CSV を選択",
            self.deckPath,
            "CSV (*.csv);;All files (*)",
        )
        if selected:
            self._settings["deck_path"] = selected
            self._deck_status = {
                "structure": False,
                "known_ids": False,
                "engine": False,
                "regulation": False,
                "cards": [],
            }
            self._human_deck_source_sha256 = ""
            self.setupChanged.emit()

    @Slot()
    def browseImages(self) -> None:
        selected = QFileDialog.getExistingDirectory(None, "カード画像フォルダーを選択", self.imageFolder)
        if selected:
            self._settings["image_folder"] = selected
            self._catalog = CardCatalog(selected)
            save_settings(self._settings)
            self.setupChanged.emit()

    @Slot()
    def browseReplayFolder(self) -> None:
        selected = QFileDialog.getExistingDirectory(None, "リプレイ保存フォルダーを選択", self.replayFolder)
        if selected:
            self._settings["replay_folder"] = selected
            save_settings(self._settings)
            self.setupChanged.emit()

    @Slot(int)
    def setHumanSeat(self, seat: int) -> None:
        if seat in (-1, 0, 1):
            self._settings["human_seat"] = seat
            self._deck_status["engine"] = False
            self.setupChanged.emit()

    @Slot(int)
    def setAiDisplayDelayMs(self, milliseconds: int) -> None:
        if type(milliseconds) is int and 400 <= milliseconds <= 10_000:
            self._settings["ai_display_delay_ms"] = milliseconds
            self.setupChanged.emit()

    @Slot(int)
    def setAgentTimeoutSeconds(self, seconds: int) -> None:
        if type(seconds) is int and 1 <= seconds <= 600:
            self._settings["agent_timeout_seconds"] = seconds
            self.setupChanged.emit()

    @Slot()
    def verifySetup(self) -> None:
        artifact = Path(self.artifactPath)
        deck_path = Path(self.deckPath)
        requested_seat = self.humanSeat
        request_context = {
            "artifact_path": self.artifactPath,
            "deck_path": self.deckPath,
            "human_seat": requested_seat,
        }

        def verify() -> dict[str, Any]:
            manifest, report = register_local_artifact(artifact)
            base = {
                "request_context": request_context,
                "manifest": manifest,
                "report": report.to_dict(),
                "deck": None,
            }
            if not report.verified:
                return base
            deck, source_bytes = read_deck_csv_snapshot(deck_path)
            shape = validate_deck(deck)
            source_sha256 = sha256_bytes(source_bytes)
            validation_id = f"validation-{uuid.uuid4()}"
            stage = stage_artifact(artifact, validation_id, manifest=manifest)
            reports: list[dict[str, Any]] = []
            compatibility_error = ""
            try:
                seats = (0, 1)
                try:
                    reports = [
                        validate_deck_in_worker(
                            stage,
                            list(shape.cards),
                            seat,
                            artifact_manifest=manifest,
                        )
                        for seat in seats
                    ]
                except Exception as exc:
                    compatibility_error = type(exc).__name__
            finally:
                cleanup_stage(stage)
            engine = {
                "known_ids_verified": bool(reports)
                and all(item.get("known_ids_verified") is True for item in reports),
                "engine_accepted": bool(reports)
                and all(item.get("engine_accepted") is True for item in reports),
                "regulation_verified": False,
                "validated_seats": list(seats) if reports else [],
                "deck_list": reports[0].get("deck_list", []) if reports else [],
                "compatibility_error": compatibility_error,
            }
            return {
                **base,
                "deck": list(shape.cards),
                "deck_source_sha256": source_sha256,
                "engine": engine,
            }

        self._run_background("verify", verify)

    def _reset_match_data(self) -> None:
        self._state = {}
        self._decision = {}
        self._decision_submitting = False
        self._public_log = []
        self._latest_action_text = "対戦開始を待っています。"
        self._latest_action_title = "対戦状況"
        self._latest_action_revision = -1
        self._result = {}
        self._diagnostics = {}
        self._replay_path = ""
        self._visualizer_json_path = ""
        self._visualizer_json_exact = False
        self._replay_frames = []
        self._replay_public_log = []
        self._replay_index = 0
        self._replay_full_information = False
        self._result_presented = False

    def _launch_match(self, seat_override: int | None = None) -> None:
        if self._shutting_down or not self.canStart:
            return
        try:
            source_sha256 = sha256_file(Path(self.deckPath))
        except OSError:
            self._set_error("デッキ原本を再確認できません。")
            return
        if source_sha256 != self._human_deck_source_sha256:
            self._deck_status["engine"] = False
            self.setupChanged.emit()
            self._set_error("検証後にデッキ原本が変更されました。再検証してください。")
            return
        requested = self.humanSeat if seat_override is None else seat_override
        seat = secrets.randbelow(2) if requested == -1 else requested
        if seat not in (0, 1):
            self._set_error("人間の座席設定が不正です。")
            return
        if self._supervisor:
            self._supervisor.close()
        self._supervisor = None
        artifact = Path(self.artifactPath)
        replay_dir = Path(self._settings.get("replay_folder") or default_replay_dir())
        replay_path = replay_dir / f"match-{uuid.uuid4()}.ptcgmatch"
        deck = list(self._human_deck)
        manifest_snapshot = copy.deepcopy(self._artifact_manifest)
        launch_identity = {
            "artifact_manifest_id": manifest_snapshot.get("manifest_id"),
            "submission_id": manifest_snapshot.get("submission_id"),
            "artifact_kind": self._artifact_trust_mode,
            "artifact_name": artifact.name,
            "human_deck_name": Path(self.deckPath).name,
        }
        ai_display_delay_ms = self.aiDisplayDelayMs
        agent_timeout_seconds = float(self.agentTimeoutSeconds)
        self._last_human_seat = seat
        save_settings(self._settings)
        supervisor = MatchSupervisor()
        with self._launch_lock:
            previous_pending = self._pending_supervisor
            self._pending_supervisor = supervisor
            self._pending_match_identity = launch_identity
        if previous_pending is not None:
            previous_pending.close()

        def start() -> MatchSupervisor:
            with self._launch_lock:
                if self._shutting_down or self._pending_supervisor is not supervisor:
                    return supervisor
                supervisor.start(
                    MatchLaunch(
                        artifact_source=artifact,
                        artifact_manifest=manifest_snapshot,
                        human_deck=deck,
                        human_seat=seat,
                        replay_path=replay_path,
                        human_deck_source_sha256=source_sha256,
                        ai_display_delay_ms=ai_display_delay_ms,
                        agent_timeout_seconds=agent_timeout_seconds,
                    )
                )
            return supervisor

        self._run_background("start", start)

    @Slot()
    def startMatch(self) -> None:
        self._launch_match()

    @Slot()
    def sameSettingsRematch(self) -> None:
        self._launch_match()

    @Slot()
    def swapSeatRematch(self) -> None:
        self._launch_match(1 - self._last_human_seat)

    @Slot("QVariantList")
    def submitDecision(self, tokens: list[str]) -> None:
        if not self._supervisor or not self._decision or self._decision_submitting:
            return
        self._decision_submitting = True
        self.matchChanged.emit()
        try:
            self._supervisor.submit_decision(
                self._decision["request_id"],
                self._decision["state_revision"],
                list(tokens),
            )
        except Exception:
            self._decision_submitting = False
            self.matchChanged.emit()
            self._set_error("選択を送信できませんでした。")

    @Slot(str)
    def chooseBoardTarget(self, target_token: str) -> None:
        options = self._decision.get("options", []) if isinstance(self._decision, dict) else []
        matches = [option for option in options if option.get("target_token") == target_token]
        if len(matches) == 1 and not self._decision_submitting:
            self.shortcutRequested.emit(matches[0]["token"])

    @Slot()
    def forfeit(self) -> None:
        if self._supervisor:
            try:
                self._supervisor.forfeit()
            except Exception:
                self._set_error("放棄要求を送信できませんでした。")

    @staticmethod
    def _human_replay_frame(frame: dict[str, Any], human_seat: int) -> dict[str, Any]:
        masked = copy.deepcopy(frame)
        payload = masked.get("payload")
        if not isinstance(payload, dict):
            return masked
        current = payload.get("current")
        if not isinstance(current, dict):
            return masked
        players = current.get("players")
        if not isinstance(players, list) or len(players) != 2:
            return masked
        opponent_seat = 1 - human_seat
        for seat, player in enumerate(players):
            if not isinstance(player, dict):
                continue
            player["deck"] = []
            prize = player.get("prize")
            player["prize"] = [None for _ in prize] if isinstance(prize, list) else []
            if seat == opponent_seat:
                player["hand"] = []
                if current.get("turn") == 0:
                    player["active"] = []
                    player["bench"] = []
        current["looking"] = None
        payload["select"] = None
        payload["selected"] = None
        payload["logs"] = []
        masked["view_mode"] = "human"
        return masked

    def _load_verified_replay(self, path: str) -> ReplayData:
        replay = load_replay(path)
        if replay.manifest.get("complete") is not True:
            raise ReplayError("replay is incomplete")
        return replay

    @Slot()
    def openReplay(self) -> None:
        if not self.replayAvailable:
            return
        self._replay_index = 0
        self._replay_full_information = False
        self._screen = "replay"
        self.replayChanged.emit()
        self.screenChanged.emit()

    def _open_local_path(self, path: Path, missing_message: str, failed_message: str) -> None:
        target = path.resolve()
        if not target.exists():
            self._set_error(missing_message)
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(target))):
            self._set_error(failed_message)

    @staticmethod
    def _official_visualizer_launcher_path() -> Path:
        return Path(__file__).resolve().parent / "assets" / "official_visualizer.html"

    @Slot()
    def openVisualizerJson(self) -> None:
        if not self._visualizer_json_path:
            self._set_error("この対戦の公式ビューワー用JSONはありません。")
            return
        self._open_local_path(
            Path(self._visualizer_json_path),
            "公式ビューワー用JSONが見つかりません。",
            "公式ビューワー用JSONを開けませんでした。",
        )

    @Slot()
    def openOfficialVisualizerLauncher(self) -> None:
        if not self.visualizerJsonAvailable:
            self._set_error("この対戦の公式ビューワー用JSONはありません。")
            return
        self._open_local_path(
            self._official_visualizer_launcher_path(),
            "公式ビューワーを開く補助ページが見つかりません。",
            "公式ビューワーを開く補助ページを起動できませんでした。",
        )

    @Slot()
    def openReplayFolder(self) -> None:
        folder = Path(self._replay_path).parent if self._replay_path else Path(self.replayFolder)
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            self._set_error("リプレイ保存フォルダーを用意できませんでした。")
            return
        self._open_local_path(
            folder,
            "リプレイ保存フォルダーが見つかりません。",
            "リプレイ保存フォルダーを開けませんでした。",
        )

    @Slot()
    def replayFirst(self) -> None:
        self.replaySeek(0)

    @Slot()
    def replayLast(self) -> None:
        self.replaySeek(max(0, len(self._replay_frames) - 1))

    @Slot()
    def replayPrevious(self) -> None:
        self.replaySeek(self._replay_index - 1)

    @Slot()
    def replayNext(self) -> None:
        self.replaySeek(self._replay_index + 1)

    @Slot(int)
    def replaySeek(self, index: int) -> None:
        if self._replay_frames:
            bounded = max(0, min(int(index), len(self._replay_frames) - 1))
            if bounded != self._replay_index:
                self._replay_index = bounded
                self.replayChanged.emit()

    @Slot(int)
    def replaySeekRevision(self, revision: int) -> None:
        if not self._replay_frames:
            return
        candidate = 0
        for index, frame in enumerate(self._replay_frames):
            if frame.get("revision", 0) <= revision:
                candidate = index
            else:
                break
        self.replaySeek(candidate)

    @Slot(bool)
    def setReplayFullInformation(self, enabled: bool) -> None:
        if bool(enabled) != self._replay_full_information:
            self._replay_full_information = bool(enabled)
            self.replayChanged.emit()

    @Slot()
    def returnToResult(self) -> None:
        self._screen = "result"
        self.screenChanged.emit()

    @Slot()
    def newMatch(self) -> None:
        if self._busy:
            return
        if self._supervisor:
            self._supervisor.close()
        self._supervisor = None
        self._active_match_identity = {}
        self._reset_match_data()
        self._screen = "setup"
        self.screenChanged.emit()
        self.matchChanged.emit()
        self.replayChanged.emit()

    def _localize_decision(self, decision: dict[str, Any]) -> dict[str, Any]:
        localized = copy.deepcopy(decision)
        options = localized.get("options")
        if not isinstance(options, list):
            return localized
        for option in options:
            if not isinstance(option, dict):
                continue
            label = str(option.get("label") or "")
            card_id = option.get("card_id")
            option_type = option.get("option_type")
            target_card_id = option.get("target_card_id")
            if option_type in {8, 9} and type(card_id) is int and type(target_card_id) is int:
                source_fallback, separator, target_fallback = label.partition(" → ")
                if not separator:
                    source_fallback = label
                    target_fallback = ""
                source_name = self._catalog.display_name(card_id, source_fallback)
                target_name = self._catalog.display_name(target_card_id, target_fallback)
                label = f"{source_name} → {target_name}"
                action = "つける" if option_type == 8 else "進化させる"
                option["detail"] = f"「{source_name}」を「{target_name}」に{action}"
            elif option_type == 6 and type(card_id) is int and type(option.get("energy_count")) is int:
                fallback_name = label.split("（", 1)[0]
                energy_name = self._catalog.display_name(card_id, fallback_name)
                label = f"{energy_name}（{option['energy_count']}個分）"
            elif type(card_id) is int:
                label = self._catalog.display_name(card_id, label)
            elif type(option.get("attack_id")) is int:
                label = self._catalog.display_attack(label)
            else:
                label = self._catalog.translate_text(label)
            option["label"] = label
            option["detail"] = self._catalog.translate_text(str(option.get("detail") or ""))
        return localized

    def _card_name_from_log(self, item: dict[str, Any], field: str) -> str:
        card_id = item.get(field)
        if type(card_id) is not int:
            return ""
        fallback = item.get(f"{field}_fallback_name")
        return self._catalog.display_name(card_id, fallback if isinstance(fallback, str) else "")

    def _format_public_log(self, item: dict[str, Any], human_seat: int) -> str:
        kind = str(item.get("type") or "")
        seat = item.get("player_index")
        actor = "あなた" if seat == human_seat else ("AI" if seat in (0, 1) else "ゲーム")
        card = self._card_name_from_log(item, "card_id")
        active = self._card_name_from_log(item, "active_card_id")
        bench = self._card_name_from_log(item, "bench_card_id")
        before = self._card_name_from_log(item, "before_card_id")
        after = self._card_name_from_log(item, "after_card_id")
        target = self._card_name_from_log(item, "target_card_id")
        attack_fallback = item.get("attack_fallback_name")
        attack = self._catalog.display_attack(attack_fallback) if isinstance(attack_fallback, str) else ""
        if not attack and type(item.get("attack_id")) is int:
            attack = f"ワザ {item['attack_id']}"
        if kind == "Shuffle":
            return f"{actor}が山札を切りました。"
        if kind == "HasBasicPokemon":
            return f"{actor}のたねポケモンを確認しました。"
        if kind == "TurnStart":
            return f"{actor}の番が始まりました。"
        if kind == "TurnEnd":
            return f"{actor}が番を終了しました。"
        if kind in {"Draw", "DrawReverse"}:
            return f"{actor}が「{card}」を引きました。" if card else f"{actor}がカードを1枚引きました。"
        if kind in {"MoveCard", "MoveCardReverse"}:
            return f"{actor}がカードを移動しました。"
        if kind == "Switch":
            names = " → ".join(name for name in (active, bench) if name)
            return f"{actor}がバトルポケモンを入れ替えました" + (f"（{names}）" if names else "") + "。"
        if kind == "Change":
            names = " → ".join(name for name in (before, after) if name)
            return f"{actor}の場が変化しました" + (f"（{names}）" if names else "") + "。"
        if kind == "Play":
            return f"{actor}が「{card or 'カード'}」を使いました。"
        if kind == "Attach":
            destination = f"「{target}」に" if target else ""
            return f"{actor}が「{card or 'エネルギー'}」を{destination}つけました。"
        if kind == "Evolve":
            names = " → ".join(name for name in (before, after or card) if name)
            return f"{actor}がポケモンを進化させました" + (f"（{names}）" if names else "") + "。"
        if kind == "Devolve":
            return f"{actor}のポケモンが退化しました。"
        if kind == "MoveAttached":
            return f"{actor}がついているカードを移動しました。"
        if kind == "Attack":
            user = f"「{active}」が" if active else ""
            return f"{actor}の{user}ワザ「{attack or '不明なワザ'}」を使いました。"
        if kind == "HpChange":
            subject = target or active or card or "ポケモン"
            value = item.get("value")
            amount = f"{abs(value)}" if type(value) is int else ""
            if item.get("is_recover") is True:
                return f"「{subject}」のHPが{amount}回復しました。"
            return f"「{subject}」が{amount}ダメージを受けました。"
        conditions = {
            "Poisoned": "どく",
            "Burned": "やけど",
            "Asleep": "ねむり",
            "Paralyzed": "マヒ",
            "Confused": "こんらん",
        }
        if kind in conditions:
            return f"「{target or active or card or 'ポケモン'}」が{conditions[kind]}になりました。"
        if kind == "Coin":
            return f"{actor}のコインは" + ("オモテ" if item.get("heads") is True else "ウラ") + "でした。"
        if kind == "Result":
            return "対戦結果が確定しました。"
        return f"{actor}が行動しました。"

    def _localize_public_logs(
        self,
        logs: Any,
        *,
        action_actor_seat: Any,
        revision: int,
    ) -> list[dict[str, Any]]:
        human_seat = self._state.get("human_seat", self._last_human_seat)
        if human_seat not in (0, 1):
            human_seat = self._last_human_seat
        localized: list[dict[str, Any]] = []
        if isinstance(logs, list):
            for raw in logs:
                if not isinstance(raw, dict):
                    continue
                item = copy.deepcopy(raw)
                item["display_text"] = self._format_public_log(item, human_seat)
                localized.append(item)
        descriptions = [str(item.get("display_text")) for item in localized if item.get("display_text")]
        if descriptions:
            self._latest_action_text = "\n".join(descriptions[-2:])
        elif action_actor_seat in (0, 1):
            actor = "あなた" if action_actor_seat == human_seat else "AI"
            self._latest_action_text = f"{actor}が行動しました。"
        if action_actor_seat in (0, 1):
            self._latest_action_title = "あなたの行動" if action_actor_seat == human_seat else "AIの行動"
        elif descriptions:
            self._latest_action_title = "対戦状況"
        self._latest_action_revision = revision
        return localized

    @Slot(int, result=str)
    @Slot(int, bool, result=str)
    def cardImage(self, card_id: int, miniature: bool = False) -> str:
        path = self._catalog.image_path(card_id, miniature=miniature)
        return QUrl.fromLocalFile(str(path)).toString() if path else ""

    @Slot(int, str, result=str)
    def cardName(self, card_id: int, fallback: str = "") -> str:
        return self._catalog.display_name(card_id, fallback)

    @Slot(str, object)
    def _on_background_done(self, operation: str, result: object) -> None:
        self._set_busy(False)
        value = result if isinstance(result, dict) else {"ok": False}
        if not value.get("ok"):
            if operation == "start":
                with self._launch_lock:
                    pending = self._pending_supervisor
                    self._pending_supervisor = None
                    self._pending_match_identity = {}
                if pending is not None:
                    pending.close()
                if value.get("type") == "ArtifactVerificationError":
                    report = value.get("report")
                    self._artifact_report = report if isinstance(report, dict) else self._artifact_report
                    self._artifact_verified = False
                    self._artifact_status = "登録後の変更を検出しました。再登録するまで対戦を開始できません。"
                    self.setupChanged.emit()
                    self._set_error("ローカルエージェントの内容が検証後に変わりました。対戦準備へ戻って再登録してください。")
                    return
            self._set_error("処理を完了できませんでした。" + (f" ({value.get('type')})" if value.get("type") else ""))
            return
        payload = value.get("value")
        if operation == "verify" and isinstance(payload, dict):
            current_context = {
                "artifact_path": self.artifactPath,
                "deck_path": self.deckPath,
                "human_seat": self.humanSeat,
            }
            if payload.get("request_context") != current_context:
                self._artifact_verified = False
                self._artifact_status = "設定変更のため再登録が必要です。"
                self._artifact_report = {}
                self._artifact_manifest = {}
                self._artifact_trust_mode = "unregistered"
                self._deck_status["engine"] = False
                self._human_deck = []
                self._human_deck_source_sha256 = ""
                self.setupChanged.emit()
                self._set_error("検証中にエージェント、デッキ、または座席設定が変更されました。再登録してください。")
                return
            report = payload.get("report", {})
            manifest = payload.get("manifest", {})
            self._artifact_report = report if isinstance(report, dict) else {}
            self._artifact_verified = bool(self._artifact_report.get("verified")) and isinstance(manifest, dict) and bool(manifest)
            self._artifact_manifest = copy.deepcopy(manifest) if self._artifact_verified else {}
            self._artifact_trust_mode = (
                str(self._artifact_report.get("trust_mode")) if self._artifact_verified else "unregistered"
            )
            engine = payload.get("engine") or {}
            self._human_deck = payload.get("deck") or []
            self._human_deck_source_sha256 = payload.get("deck_source_sha256") or ""
            self._deck_status = {
                "structure": bool(payload.get("deck")),
                "known_ids": bool(engine.get("known_ids_verified")),
                "engine": bool(engine.get("engine_accepted")),
                "regulation": False,
                "validated_seats": engine.get("validated_seats", []),
                "cards": engine.get("deck_list", []),
            }
            if not self._artifact_verified:
                issues = self._artifact_report.get("issues") or []
                first_issue = issues[0] if issues and isinstance(issues[0], dict) else {}
                detail = first_issue.get("detail") or "必要なファイル構成を確認できません。"
                self._artifact_status = "取り込みできません: " + str(detail)
            elif not self._deck_status["engine"]:
                self._artifact_status = "登録済みですが、起動互換性を確認できません。"
                if engine.get("compatibility_error"):
                    self._set_error("エージェントの読み込みまたは試合開始確認に失敗しました。")
            elif self.verifiedMatch:
                self._artifact_status = "Verified Submission：submission 55155015 とバイト一致し、起動互換性を確認済みです。"
            else:
                fingerprint = str(self._artifact_report.get("content_sha256") or "")
                short_fingerprint = fingerprint[:16] + ("…" if len(fingerprint) > 16 else "")
                self._artifact_status = "自己管理ローカルエージェントを登録し、起動互換性を確認済みです。指紋: " + short_fingerprint
            if self._artifact_verified and self._deck_status["engine"]:
                save_settings(self._settings)
            self.setupChanged.emit()
        elif operation == "start" and isinstance(payload, MatchSupervisor):
            with self._launch_lock:
                accepted = not self._shutting_down and self._pending_supervisor is payload
                launch_identity = copy.deepcopy(self._pending_match_identity) if accepted else {}
                if accepted:
                    self._pending_supervisor = None
                    self._pending_match_identity = {}
            if not accepted:
                payload.close()
                return
            self._active_match_identity = launch_identity
            self._reset_match_data()
            self.matchChanged.emit()
            self.replayChanged.emit()
            self._supervisor = payload
            self._screen = "board"
            self.screenChanged.emit()

    def _write_diagnostic_log(self) -> None:
        try:
            target_dir = logs_dir()
            target_dir.mkdir(parents=True, exist_ok=True)
            match_id = self._diagnostics.get("match_id") or uuid.uuid4().hex
            target = target_dir / f"match-{match_id}.json"
            payload = {
                "schema_version": 1,
                "written_at_utc": datetime.now(timezone.utc).isoformat(),
                "artifact_manifest_id": self._result.get("artifact_manifest_id"),
                "result": self._result,
                "diagnostics": self._diagnostics,
            }
            encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
            descriptor, temporary_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target_dir)
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, target)
            finally:
                if temporary.exists():
                    temporary.unlink()
        except OSError:
            pass

    def _present_result(self) -> None:
        if not self._supervisor or self._result_presented or self._supervisor.result is None:
            return
        self._result_presented = True
        self._result = self._supervisor.result.to_dict()
        identity = self._active_match_identity
        if not self._result.get("artifact_manifest_id"):
            self._result["artifact_manifest_id"] = identity.get("artifact_manifest_id")
        if self._result.get("human_seat") not in (0, 1):
            self._result["human_seat"] = self._last_human_seat
        self._result["human_deck_name"] = identity.get("human_deck_name")
        self._result["submission_id"] = identity.get("submission_id")
        self._result["artifact_kind"] = identity.get("artifact_kind")
        self._result["artifact_name"] = identity.get("artifact_name")
        self._result["child_exit_code"] = self._supervisor.exit_code
        self._diagnostics = {
            "match_id": self._supervisor.match_id,
            "child_exit_code": self._supervisor.exit_code,
            "last_phase": self._supervisor.last_phase.value,
            "replay_complete": False,
        }
        if self._supervisor.replay_available and self._supervisor.replay_candidate:
            try:
                candidate_path = self._supervisor.replay_candidate["path"]
                replay = self._load_verified_replay(candidate_path)
                if replay.manifest.get("artifact_manifest_id") != identity.get("artifact_manifest_id"):
                    raise ReplayError("replay artifact identity does not match launched agent")
                self._replay_path = candidate_path
                self._replay_frames = list(replay.frames)
                self._replay_public_log = list(replay.public_log)
                self._replay_human_seat = int(replay.settings.get("human_seat", self._last_human_seat))
                try:
                    visualizer_path, visualizer_hash = export_visualizer_json(replay)
                    self._visualizer_json_path = str(visualizer_path)
                    self._visualizer_json_exact = replay.visualizer_exact
                except (OSError, ReplayError):
                    self._visualizer_json_path = ""
                    self._visualizer_json_exact = False
                    visualizer_hash = None
                self._diagnostics.update(replay.diagnostics)
                self._diagnostics["match_id"] = replay.manifest.get("match_id")
                self._diagnostics["child_exit_code"] = self._supervisor.exit_code
                self._diagnostics["replay_complete"] = True
                self._diagnostics["visualizer_json_available"] = bool(self._visualizer_json_path)
                self._diagnostics["visualizer_json_exact"] = self._visualizer_json_exact
                self._diagnostics["visualizer_json_sha256"] = visualizer_hash
                self._result["replay_complete"] = True
                self._result["artifact_manifest_id"] = replay.manifest.get("artifact_manifest_id")
                self._result["submission_id"] = replay.manifest.get("submission_id")
                self._result["first_player"] = replay.manifest.get("first_player")
            except (KeyError, TypeError, ValueError, ReplayError):
                self._replay_path = ""
                self._visualizer_json_path = ""
                self._visualizer_json_exact = False
                self._replay_frames = []
                self._replay_public_log = []
                self._result["replay_complete"] = False
        self._write_diagnostic_log()
        self._screen = "result"
        self.matchChanged.emit()
        self.replayChanged.emit()
        self.screenChanged.emit()

    @Slot()
    def _poll_match(self) -> None:
        if not self._supervisor:
            return
        for event in self._supervisor.poll(0):
            payload = event["payload"]
            message_type = event["message_type"]
            if message_type == "phase.changed":
                if self._state:
                    self._state = {**self._state, "phase": payload.get("phase", self._state.get("phase"))}
                    self.matchChanged.emit()
            elif message_type == "state.update":
                self._state = payload["state"]
                revision = self._state.get("state_revision", self._state.get("revision", -1))
                localized_logs = self._localize_public_logs(
                    payload.get("public_log", []),
                    action_actor_seat=payload.get("action_actor_seat"),
                    revision=revision if type(revision) is int else -1,
                )
                self._public_log.extend(localized_logs)
                if self._decision and self._decision.get("state_revision", -1) < self._state.get("state_revision", self._state.get("revision", -1)):
                    self._decision = {}
                    self._decision_submitting = False
                self.matchChanged.emit()
            elif message_type == "decision.required":
                self._decision = self._localize_decision(payload["decision"])
                self._decision_submitting = False
                self.matchChanged.emit()
            elif message_type == "decision.accepted":
                if self._decision.get("request_id") == payload.get("request_id"):
                    self._decision = {}
                    self._decision_submitting = False
                    self.matchChanged.emit()
            elif message_type == "match.finished":
                self._result = payload["result"]
                self.matchChanged.emit()
            elif message_type == "error":
                if payload.get("code") in {"invalid_decision_payload", "decision_rejected"}:
                    self._decision_submitting = False
                    self.matchChanged.emit()
                self._set_error(payload.get("summary", "対戦エラーが発生しました。"))
        if self._supervisor.result and self._supervisor.finalized:
            self._present_result()

    def shutdown(self) -> None:
        self._timer.stop()
        with self._launch_lock:
            self._shutting_down = True
            pending = self._pending_supervisor
            self._pending_supervisor = None
            self._pending_match_identity = {}
        active = self._supervisor
        self._supervisor = None
        if pending is not None and pending is not active:
            pending.close()
        if active is not None:
            active.close()
