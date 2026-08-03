from __future__ import annotations

import os
import time
import unittest


try:
    from PySide6.QtWidgets import QApplication

    from ptcg_desktop.controller import AppController

    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
@unittest.skipUnless(
    os.environ.get("PTCG_LOCAL_AGENT_ARTIFACT") and os.environ.get("PTCG_LOCAL_HUMAN_DECK"),
    "set PTCG_LOCAL_AGENT_ARTIFACT and PTCG_LOCAL_HUMAN_DECK",
)
class LocalControllerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
        cls.app = QApplication.instance() or QApplication([])

    def test_local_agent_registers_as_local_and_becomes_runnable(self) -> None:
        controller = AppController()
        controller._settings["artifact_path"] = os.environ["PTCG_LOCAL_AGENT_ARTIFACT"]
        controller._settings["deck_path"] = os.environ["PTCG_LOCAL_HUMAN_DECK"]
        controller._settings["human_seat"] = 0
        try:
            controller.verifySetup()
            deadline = time.monotonic() + 60
            while controller.busy and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.01)
            self.app.processEvents()

            self.assertFalse(controller.busy)
            self.assertTrue(controller.artifactReady, controller.artifactDetails)
            self.assertTrue(controller.localAgentRegistered)
            self.assertFalse(controller.verifiedMatch)
            self.assertTrue(controller.deckStatus.get("engine"), controller.deckStatus)
            self.assertTrue(controller.canStart)
        finally:
            controller.shutdown()


if __name__ == "__main__":
    unittest.main()
