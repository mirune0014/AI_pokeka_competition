from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


try:
    from PySide6.QtCore import QMetaObject, QObject, QUrl
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtWidgets import QApplication

    from ptcg_desktop.controller import AppController

    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False


def view_card(card_id: int, token: str) -> dict[str, object]:
    return {
        "card_id": card_id,
        "state_token": token,
        "fallback_name": f"Card {card_id}",
        "hp": 100,
        "max_hp": 120,
        "appear_this_turn": False,
        "energies": [8],
        "energy_cards": [{"card_id": 8, "state_token": token + "-energy", "fallback_name": "Metal Energy"}],
        "tools": [],
        "pre_evolution": [],
    }


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
class QmlScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
        cls.app = QApplication.instance() or QApplication([])

    def test_setup_distinguishes_archive_and_folder_pickers(self) -> None:
        controller = AppController()
        engine = QQmlApplicationEngine()
        warnings: list[str] = []
        engine.warnings.connect(lambda values: warnings.extend(error.toString() for error in values))
        engine.rootContext().setContextProperty("controller", controller)
        qml = Path(__file__).resolve().parents[1] / "src" / "ptcg_desktop" / "qml" / "Main.qml"
        engine.load(QUrl.fromLocalFile(str(qml)))
        self.app.processEvents()
        window = engine.rootObjects()[0]
        archive_button = window.findChild(QObject, "browseArtifactArchiveButton")
        folder_button = window.findChild(QObject, "browseArtifactFolderButton")
        help_text = window.findChild(QObject, "artifactPickerHelp")
        self.assertIsNotNone(archive_button)
        self.assertIn("tar.gz", archive_button.property("text"))
        self.assertIsNotNone(folder_button)
        self.assertIn("フォルダー", folder_button.property("text"))
        self.assertIsNotNone(help_text)
        self.assertIn("ファイルは表示されません", help_text.property("text"))
        self.assertEqual(warnings, [])
        controller.shutdown()

    def test_board_result_and_replay_dummy_models_render(self) -> None:
        controller = AppController()
        engine = QQmlApplicationEngine()
        warnings: list[str] = []
        engine.warnings.connect(lambda values: warnings.extend(error.toString() for error in values))
        engine.rootContext().setContextProperty("controller", controller)
        qml = Path(__file__).resolve().parents[1] / "src" / "ptcg_desktop" / "qml" / "Main.qml"
        engine.load(QUrl.fromLocalFile(str(qml)))
        player = {
            "seat": 0,
            "active": [view_card(100, "active")],
            "bench": [view_card(101, "bench")],
            "bench_max": 5,
            "deck_count": 40,
            "discard": [{"card_id": 300, "state_token": "discard", "fallback_name": "Discarded Card"}],
            "prize_count": 6,
            "hand_count": 2,
            "conditions": {},
            "hand": [view_card(102, "hand-1"), view_card(103, "hand-2")],
        }
        opponent = {**player, "seat": 1, "hand_count": 5}
        opponent.pop("hand")
        controller._state = {
            "human_seat": 0,
            "acting_seat": 0,
            "turn": 3,
            "first_player": 0,
            "human": player,
            "opponent": opponent,
            "stadium": None,
        }
        controller._decision = {
            "request_id": "request",
            "state_revision": 2,
            "prompt": "Choose options",
            "min_count": 0,
            "max_count": 2,
            "options": [
                {"token": "one", "choice_number": 1, "label": "Option one", "detail": "", "target_token": "hand-1"},
                {"token": "two", "choice_number": 2, "label": "Option two", "detail": "", "target_token": "bench"},
            ],
        }
        controller._screen = "board"
        controller.matchChanged.emit()
        controller.screenChanged.emit()
        self.app.processEvents()
        window = engine.rootObjects()[0]
        self.assertIsNotNone(window.findChild(QObject, "cardPreview"))
        hp_badges = window.findChildren(QObject, "hpNumericBadge")
        energy_badges = window.findChildren(QObject, "energyBadge")
        self.assertGreater(len(hp_badges), 0)
        self.assertGreater(len(energy_badges), 0)
        self.assertGreaterEqual(len(window.findChildren(QObject, "discardPile")), 2)
        discard_popups = window.findChildren(QObject, "discardPopup")
        self.assertGreaterEqual(len(discard_popups), 2)
        QMetaObject.invokeMethod(discard_popups[0], "open")
        self.app.processEvents()
        QMetaObject.invokeMethod(discard_popups[0], "close")
        self.app.processEvents()
        controller._result = {"classification": "normal", "winner_seat": 0, "summary_ja": "Done", "reason_code": "engine_result"}
        visualizer_dir = tempfile.TemporaryDirectory()
        self.addCleanup(visualizer_dir.cleanup)
        visualizer_path = Path(visualizer_dir.name) / "match.visualizer.json"
        visualizer_path.write_text("[]", encoding="utf-8")
        controller._visualizer_json_path = str(visualizer_path)
        controller._visualizer_json_exact = True
        controller._screen = "result"
        controller.matchChanged.emit()
        controller.screenChanged.emit()
        self.app.processEvents()
        json_button = window.findChild(QObject, "openVisualizerJsonButton")
        official_button = window.findChild(QObject, "openOfficialVisualizerButton")
        folder_button = window.findChild(QObject, "openReplayFolderButton")
        notice = window.findChild(QObject, "visualizerJsonNotice")
        self.assertIsNotNone(json_button)
        self.assertTrue(json_button.property("enabled"))
        self.assertIsNotNone(official_button)
        self.assertTrue(official_button.property("enabled"))
        self.assertIsNotNone(folder_button)
        self.assertTrue(folder_button.property("enabled"))
        self.assertIsNotNone(notice)
        self.assertTrue(notice.property("visible"))
        self.assertIn("match.visualizer.json", notice.property("text"))
        controller._replay_frames = [
            {
                "frame_index": 0,
                "payload": {
                    "current": {
                        "turn": 3,
                        "players": [
                            {"hand_count": 1, "deck_count": 1, "hand": [{"id": 1, "name": "A"}], "deck": [{"id": 2, "name": "B"}], "prize": [{"id": 3, "name": "C"}]},
                            {"hand_count": 1, "deck_count": 1, "hand": [{"id": 4, "name": "D"}], "deck": [{"id": 5, "name": "E"}], "prize": [{"id": 6, "name": "F"}]},
                        ],
                    }
                },
            }
        ]
        controller._screen = "replay"
        controller.replayChanged.emit()
        controller.screenChanged.emit()
        self.app.processEvents()
        self.assertEqual(warnings, [])
        controller.shutdown()

    def test_card_choice_number_and_selected_tint_render(self) -> None:
        controller = AppController()
        engine = QQmlApplicationEngine()
        warnings: list[str] = []
        engine.warnings.connect(lambda values: warnings.extend(error.toString() for error in values))
        engine.rootContext().setContextProperty("controller", controller)
        harness = Path(__file__).with_name("CardChoiceHarness.qml")
        engine.load(QUrl.fromLocalFile(str(harness)))
        self.app.processEvents()
        root = engine.rootObjects()[0]
        cards = root.findChildren(QObject, "cardTile")
        self.assertEqual([card.property("choiceLabel") for card in cards], ["1", "2"])
        selected = [card for card in cards if card.property("selectedOrder") > 0]
        self.assertEqual(len(selected), 1)
        tints = root.findChildren(QObject, "selectionTint")
        self.assertEqual(len([tint for tint in tints if tint.property("visible")]), 1)
        number_texts = root.findChildren(QObject, "choiceNumberText")
        self.assertIn("✓ 2", [item.property("text") for item in number_texts])
        self.assertEqual(warnings, [])
        controller.shutdown()


if __name__ == "__main__":
    unittest.main()
