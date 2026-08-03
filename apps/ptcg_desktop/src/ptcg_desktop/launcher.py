from __future__ import annotations

import json
import multiprocessing
import os
import sys
import time
import uuid
from pathlib import Path


def _qml_main_path() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "ptcg_desktop" / "qml" / "Main.qml"
    return Path(__file__).resolve().parent / "qml" / "Main.qml"


def _run_frozen_self_test(arguments: list[str]) -> int:
    """Exercise frozen spawn/IPC/replay without opening the GUI."""
    import argparse

    from ptcg_desktop.artifacts import cleanup_stage, register_local_artifact, stage_artifact
    from ptcg_desktop.engine_runtime import read_flat_deck
    from ptcg_desktop.supervisor import MatchLaunch, MatchSupervisor

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--self-test", type=Path, required=True)
    parser.add_argument("--self-test-output", type=Path, required=True)
    parser.add_argument("--self-test-seat", type=int, choices=(0, 1), default=0)
    args = parser.parse_args(arguments)
    artifact = args.self_test.resolve()
    output = args.self_test_output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    replay = output.with_suffix(".ptcgmatch")
    manifest, report = register_local_artifact(artifact)
    if not report.verified:
        output.write_text(json.dumps({"completed": False, "reason_code": "artifact_registration_failed"}, ensure_ascii=False, indent=2), encoding="utf-8")
        return 2
    deck_stage = stage_artifact(artifact, f"selftest-deck-{uuid.uuid4()}", manifest=manifest)
    try:
        human_deck = read_flat_deck(deck_stage / "deck.csv")
    finally:
        cleanup_stage(deck_stage)
    supervisor = MatchSupervisor()
    handled: set[str] = set()
    try:
        supervisor.start(
            MatchLaunch(
                artifact,
                human_deck,
                args.self_test_seat,
                replay,
                artifact_manifest=manifest,
                max_steps=6,
            )
        )
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            for event in supervisor.poll(0.05):
                if event["message_type"] != "decision.required":
                    continue
                decision = event["payload"]["decision"]
                request_id = decision["request_id"]
                if request_id in handled:
                    continue
                handled.add(request_id)
                tokens = [option["token"] for option in decision["options"][: decision["min_count"]]]
                supervisor.submit_decision(request_id, decision["state_revision"], tokens)
            if supervisor.result is not None and supervisor.finalized:
                break
        result = {
            "completed": supervisor.result is not None and supervisor.finalized,
            "classification": None if supervisor.result is None else supervisor.result.classification,
            "reason_code": None if supervisor.result is None else supervisor.result.reason_code,
            "replay_available": supervisor.replay_available,
            "event_count": len(supervisor.events),
            "decision_count": len(handled),
        }
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if result["completed"] and result["replay_available"] else 2
    finally:
        supervisor.close()


def main() -> int:
    multiprocessing.freeze_support()
    if "--self-test" in sys.argv:
        return _run_frozen_self_test(sys.argv[1:])
    gui_smoke_output: Path | None = None
    if "--gui-smoke-output" in sys.argv:
        index = sys.argv.index("--gui-smoke-output")
        if index + 1 >= len(sys.argv):
            return 2
        gui_smoke_output = Path(sys.argv[index + 1]).resolve()
        del sys.argv[index : index + 2]
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Fusion")
    from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtQuickControls2, QtWidgets  # noqa: F401
    from PySide6.QtCore import QCoreApplication, QTimer, QUrl
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtWidgets import QApplication

    from ptcg_desktop.artifacts import cleanup_stale_staging
    from ptcg_desktop.controller import AppController

    cleanup_stale_staging()
    QCoreApplication.setOrganizationName("PTCG Human Client")
    QCoreApplication.setApplicationName("PTCG Human Client")
    app = QApplication(sys.argv)
    controller = AppController()
    engine = QQmlApplicationEngine()
    qml_warnings: list[str] = []
    engine.warnings.connect(lambda values: qml_warnings.extend(error.toString() for error in values))
    engine.rootContext().setContextProperty("controller", controller)
    engine.load(QUrl.fromLocalFile(str(_qml_main_path())))
    roots = engine.rootObjects()
    if gui_smoke_output is not None:
        def finish_gui_smoke() -> None:
            current_roots = engine.rootObjects()
            gui_smoke_output.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "qml_loaded": bool(current_roots),
                "root_count": len(current_roots),
                "screen": controller.screen,
                "warnings": qml_warnings,
            }
            gui_smoke_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            controller.shutdown()
            app.exit(0 if current_roots and not qml_warnings else 2)

        # Enter the event loop before declaring the GUI ready.  A living
        # windowed bootloader could otherwise be only an exception dialog.
        QTimer.singleShot(100, finish_gui_smoke)
        return app.exec()
    if not roots:
        return 2
    app.aboutToQuit.connect(controller.shutdown)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
