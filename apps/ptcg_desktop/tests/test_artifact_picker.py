from __future__ import annotations

import unittest
from unittest.mock import patch

try:
    from ptcg_desktop.controller import AGENT_ARCHIVE_FILTER, AppController

    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
class ArtifactPickerTests(unittest.TestCase):
    def test_archive_picker_shows_common_gzip_tar_names(self) -> None:
        controller = AppController()
        try:
            controller._settings["artifact_path"] = r"C:\agents\current.tar.gz"
            with patch(
                "ptcg_desktop.controller.QFileDialog.getOpenFileName",
                return_value=("", ""),
            ) as picker:
                controller.browseArtifactArchive()

            arguments = picker.call_args.args
            self.assertIn("tar.gz", arguments[1])
            self.assertEqual(arguments[2], r"C:\agents\current.tar.gz")
            self.assertEqual(arguments[3], AGENT_ARCHIVE_FILTER)
            self.assertIn("*.tar.gz", arguments[3])
            self.assertIn("*.tgz", arguments[3])
            self.assertIn("*.gz", arguments[3])
            self.assertIn("*.*", arguments[3])
        finally:
            controller.shutdown()

    def test_selected_archive_is_kept_for_registration(self) -> None:
        controller = AppController()
        try:
            selected = r"C:\日本語\my-agent.tar.gz"
            with patch(
                "ptcg_desktop.controller.QFileDialog.getOpenFileName",
                return_value=(selected, AGENT_ARCHIVE_FILTER),
            ):
                controller.browseArtifactArchive()

            self.assertEqual(controller.artifactPath, selected)
            self.assertIn("未登録", controller.artifactStatus)
        finally:
            controller.shutdown()


if __name__ == "__main__":
    unittest.main()
