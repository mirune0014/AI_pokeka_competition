from __future__ import annotations

import os
import unittest
from pathlib import Path


try:
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtWidgets import QApplication

    from ptcg_desktop.controller import AppController

    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
class QmlSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
        cls.app = QApplication.instance() or QApplication([])

    def test_main_qml_loads_all_four_screens(self) -> None:
        controller = AppController()
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("controller", controller)
        qml = Path(__file__).resolve().parents[1] / "src" / "ptcg_desktop" / "qml" / "Main.qml"
        engine.load(QUrl.fromLocalFile(str(qml)))
        self.assertEqual(len(engine.rootObjects()), 1)
        root = engine.rootObjects()[0]
        self.assertGreaterEqual(root.width(), 640)
        self.assertLessEqual(root.width(), 1440)
        self.assertGreaterEqual(root.height(), 360)
        self.assertLessEqual(root.height(), 900)
        controller.shutdown()


if __name__ == "__main__":
    unittest.main()
