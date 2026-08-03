from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from ptcg_desktop.card_catalog import CardCatalog
from ptcg_desktop.worker import ai_delay_segments


try:
    from PySide6.QtWidgets import QApplication

    from ptcg_desktop.controller import AppController

    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False


class AiPresentationTimingTests(unittest.TestCase):
    def test_interval_keeps_a_short_thinking_cue_and_longer_action_dwell(self) -> None:
        self.assertEqual(ai_delay_segments(1000), (150, 850))
        self.assertEqual(ai_delay_segments(100), (100, 0))
        self.assertEqual(ai_delay_segments(0), (0, 0))


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
class ViewerLocalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
        cls.app = QApplication.instance() or QApplication([])

    def test_decision_and_action_feed_use_japanese_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "translations.json").write_text(
                json.dumps(
                    {
                        "cardNames": {"8": "基本【鋼】エネルギー", "190": "ブリジュラスex"},
                        "englishCardNames": {"Archaludon ex": "ブリジュラスex"},
                        "attackNames": {"Metal Defender": "メタルディフェンダー"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            controller = AppController()
            controller._catalog = CardCatalog(root)
            controller._state = {"human_seat": 0}
            try:
                localized = controller._localize_decision(
                    {
                        "options": [
                            {
                                "label": "Archaludon ex",
                                "detail": "付ける → Archaludon ex・識別番号 1",
                                "card_id": 190,
                            },
                            {"label": "Metal Defender", "detail": "識別番号 2", "attack_id": 99},
                            {
                                "option_type": 8,
                                "label": "Metal Energy → Archaludon ex",
                                "detail": "attach",
                                "card_id": 8,
                                "target_card_id": 190,
                            },
                            {
                                "option_type": 6,
                                "label": "Metal Energy（2 個分）",
                                "detail": "energy",
                                "card_id": 8,
                                "energy_count": 2,
                            },
                        ]
                    }
                )
                self.assertEqual(localized["options"][0]["label"], "ブリジュラスex")
                self.assertIn("ブリジュラスex", localized["options"][0]["detail"])
                self.assertEqual(localized["options"][1]["label"], "メタルディフェンダー")
                self.assertEqual(localized["options"][2]["label"], "基本【鋼】エネルギー → ブリジュラスex")
                self.assertEqual(
                    localized["options"][2]["detail"],
                    "「基本【鋼】エネルギー」を「ブリジュラスex」につける",
                )
                self.assertEqual(localized["options"][3]["label"], "基本【鋼】エネルギー（2個分）")

                logs = controller._localize_public_logs(
                    [
                        {
                            "type": "Attack",
                            "player_index": 1,
                            "active_card_id": 190,
                            "active_card_id_fallback_name": "Archaludon ex",
                            "attack_id": 99,
                            "attack_fallback_name": "Metal Defender",
                        }
                    ],
                    action_actor_seat=1,
                    revision=4,
                )
                self.assertEqual(
                    logs[0]["display_text"],
                    "AIの「ブリジュラスex」がワザ「メタルディフェンダー」を使いました。",
                )
                self.assertEqual(controller.latestActionTitle, "AIの行動")
                self.assertIn("メタルディフェンダー", controller.latestActionText)
                self.assertEqual(controller.latestActionRevision, 4)
            finally:
                controller.shutdown()


if __name__ == "__main__":
    unittest.main()
