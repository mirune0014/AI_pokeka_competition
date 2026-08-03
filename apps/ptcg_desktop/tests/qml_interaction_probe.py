from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def card(card_id: int, token: str) -> dict[str, object]:
    return {
        "card_id": card_id,
        "state_token": token,
        "fallback_name": f"Card {card_id}",
        "hp": 100,
        "max_hp": 120,
        "appear_this_turn": False,
        "energies": [],
        "energy_cards": [],
        "tools": [],
        "pre_evolution": [],
    }


class RecordingSupervisor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, list[str]]] = []
        self.result = None
        self.running = True

    def poll(self, timeout: float = 0.0) -> list[dict[str, object]]:
        del timeout
        return []

    def submit_decision(self, request_id: str, revision: int, tokens: list[str]) -> None:
        self.calls.append((request_id, revision, list(tokens)))

    def close(self) -> None:
        self.running = False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale", type=float, required=True)
    args = parser.parse_args()
    if args.scale not in (1.5, 2.0):
        raise SystemExit("scale must be 1.5 or 2.0")

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ["QT_SCALE_FACTOR"] = str(args.scale)

    from PySide6.QtCore import QObject, Qt, QUrl
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickItem  # noqa: F401 - registers QQuickItem pointer conversion
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from ptcg_desktop.controller import AppController

    app = QApplication.instance() or QApplication([])
    controller = AppController()
    player = {
        "seat": 0,
        "active": [card(100, "active")],
        "bench": [card(101, "bench")],
        "bench_max": 5,
        "deck_count": 40,
        "discard": [],
        "prize_count": 6,
        "hand_count": 2,
        "conditions": {},
        "hand": [card(102, "hand-1"), card(103, "hand-2")],
    }
    opponent = {**player, "seat": 1, "hand_count": 5}
    opponent.pop("hand")
    controller._state = {
        "state_revision": 2,
        "human_seat": 0,
        "acting_seat": 0,
        "turn_player": 0,
        "turn": 3,
        "first_player": 0,
        "phase": "WAITING_FOR_HUMAN",
        "human": player,
        "opponent": opponent,
        "stadium": None,
    }
    controller._decision = {
        "request_id": "request",
        "state_revision": 2,
        "prompt": "選択してください",
        "min_count": 1,
        "max_count": 2,
        "ordered": True,
        "options": [
            {"token": "one", "kind": "card", "choice_number": 1, "label": "Option one", "detail": "", "target_token": "hand-1"},
            {"token": "two", "kind": "card", "choice_number": 2, "label": "Option two", "detail": "", "target_token": "bench"},
        ],
    }
    recorder = RecordingSupervisor()
    controller._supervisor = recorder  # type: ignore[assignment]
    controller._screen = "board"

    engine = QQmlApplicationEngine()
    warnings: list[str] = []
    engine.warnings.connect(lambda values: warnings.extend(error.toString() for error in values))
    engine.rootContext().setContextProperty("controller", controller)
    qml = Path(__file__).resolve().parents[1] / "src" / "ptcg_desktop" / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml)))
    if not engine.rootObjects():
        raise RuntimeError("QML root did not load")
    window = engine.rootObjects()[0]
    window.setWidth(round(1280 / args.scale))
    window.setHeight(round(720 / args.scale))
    window.show()
    window.requestActivate()
    app.processEvents()

    board = window.findChild(QObject, "boardScreen")
    scroll = window.findChild(QObject, "boardScroll")
    legal = window.findChild(QObject, "legalList")
    confirm = window.findChild(QObject, "confirmDecisionButton")
    if any(item is None for item in (board, scroll, legal, confirm)):
        raise RuntimeError("critical board control is missing")
    if window.width() > round(1280 / args.scale) or window.height() > round(720 / args.scale):
        raise RuntimeError("minimum window size exceeds the scaled 1280x720 viewport")
    if float(scroll.property("contentWidth")) <= float(scroll.property("width")):
        raise RuntimeError("horizontal access path is missing")
    if float(scroll.property("contentHeight")) <= float(scroll.property("height")):
        raise RuntimeError("vertical access path is missing")
    if bool(confirm.property("enabled")):
        raise RuntimeError("confirm must be disabled before the required selection")
    QTest.keyClick(window, Qt.Key_F6)
    app.processEvents()
    if not bool(legal.property("activeFocus")):
        raise RuntimeError("F6 did not focus the legal-action panel")
    first_option = legal.property("currentItem")
    if first_option is None or "1\u3000Option one" not in str(first_option.property("text")):
        raise RuntimeError("choice 1 is not numbered in the legal list")
    legal.setProperty("currentIndex", 1)
    app.processEvents()
    second_option = legal.property("currentItem")
    if second_option is None or "2\u3000Option two" not in str(second_option.property("text")):
        raise RuntimeError("choice 2 is not numbered in the legal list")
    legal.setProperty("currentIndex", 0)
    app.processEvents()

    def visual_descendants(item):
        values = []
        for child in item.childItems():
            values.append(child)
            values.extend(visual_descendants(child))
        return values

    card_tiles = [
        item for item in visual_descendants(window.contentItem())
        if item.objectName() == "cardTile"
    ]
    numbered_cards = {
        str(tile.property("targetToken")): tile
        for tile in card_tiles
        if str(tile.property("choiceLabel"))
    }
    if "hand-1" not in numbered_cards or str(numbered_cards["hand-1"].property("choiceLabel")) != "1":
        raise RuntimeError("hand choice 1 is not marked on its card")
    if "bench" not in numbered_cards or str(numbered_cards["bench"].property("choiceLabel")) != "2":
        raise RuntimeError("Pokemon choice 2 is not marked on its card")
    interaction_started = time.perf_counter()
    QTest.keyClick(window, Qt.Key_Space)
    app.processEvents()
    interaction_ms = (time.perf_counter() - interaction_started) * 1000
    if interaction_ms >= 100:
        raise RuntimeError(f"local keyboard interaction took {interaction_ms:.1f} ms")
    if not bool(confirm.property("enabled")):
        raise RuntimeError("keyboard selection did not enable confirmation")
    if int(numbered_cards["hand-1"].property("selectedOrder")) != 1:
        raise RuntimeError("selected card did not keep its visual selection state")
    QTest.keyClick(window, Qt.Key_Return, Qt.ControlModifier)
    app.processEvents()
    if recorder.calls != [("request", 2, ["one"])]:
        raise RuntimeError(f"keyboard confirmation mismatch: {recorder.calls!r}")
    if warnings:
        raise RuntimeError("QML warnings: " + " | ".join(warnings))

    result = {
        "scale_factor": args.scale,
        "device_pixel_ratio": window.devicePixelRatio(),
        "logical_viewport": [window.width(), window.height()],
        "scroll_extent": [scroll.property("contentWidth"), scroll.property("contentHeight")],
        "keyboard_submission": recorder.calls[0],
        "numbered_card_choices": [
            numbered_cards["hand-1"].property("choiceLabel"),
            numbered_cards["bench"].property("choiceLabel"),
        ],
        "local_interaction_ms": round(interaction_ms, 3),
        "warnings": 0,
    }
    sys.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True))
    controller.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
