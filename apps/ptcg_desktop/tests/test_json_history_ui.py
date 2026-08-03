from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    from ptcg_desktop.controller import AppController
    from ptcg_desktop.models import MatchPhase, MatchResult
    from ptcg_desktop.replay import ReplayBuilder

    from helpers import full_frame

    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed")
class JsonHistoryControllerTests(unittest.TestCase):
    def test_verified_result_automatically_writes_visualizer_json(self) -> None:
        controller = AppController()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                replay_path = Path(temporary) / "match.ptcgmatch"
                builder = ReplayBuilder("match-json-export")
                first = full_frame()
                second = full_frame(acting=1, turn=2, result=0)
                builder.ingest_visualizer([first], revision=0, captured_after="battle_start")
                builder.ingest_visualizer([first, second], revision=1, captured_after="battle_select")
                result = MatchResult(
                    classification="normal",
                    winner_seat=0,
                    engine_result=0,
                    reason_code="engine_result",
                    summary_ja="Player 0 の勝利です。",
                    artifact_manifest_id="test-artifact",
                    human_seat=0,
                    first_player=0,
                    turn_count=2,
                    battle_select_count=1,
                    replay_complete=True,
                )
                builder.seal(
                    replay_path,
                    artifact={"artifact_manifest_id": "test-artifact"},
                    settings={"human_seat": 0},
                    decks={"human": [1] * 60, "agent": [2] * 60},
                    public_log=[],
                    result=result.to_dict(),
                    diagnostics={"steps": 1, "complete": True},
                )
                controller._active_match_identity = {"artifact_manifest_id": "test-artifact"}
                controller._supervisor = SimpleNamespace(
                    result=result,
                    exit_code=0,
                    match_id="match-json-export",
                    last_phase=MatchPhase.REPLAY_SEALED,
                    replay_available=True,
                    replay_candidate={"path": str(replay_path)},
                    close=lambda: None,
                )
                with patch.object(controller, "_write_diagnostic_log"):
                    controller._present_result()
                exported = replay_path.with_suffix(".visualizer.json")
                self.assertTrue(exported.is_file())
                self.assertTrue(controller.visualizerJsonAvailable)
                self.assertTrue(controller.visualizerJsonExact)
                self.assertEqual(controller.visualizerJsonFileName, exported.name)
                self.assertEqual(controller.diagnosticsData["visualizer_json_available"], True)
        finally:
            controller.shutdown()

    def test_current_visualizer_json_opens_through_desktop_services(self) -> None:
        controller = AppController()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary) / "対戦 履歴.visualizer.json"
                target.write_text("[]", encoding="utf-8")
                controller._visualizer_json_path = str(target)
                with patch("ptcg_desktop.controller.QDesktopServices") as desktop:
                    desktop.openUrl.return_value = True
                    controller.openVisualizerJson()
                    opened_url = desktop.openUrl.call_args.args[0]
                    self.assertEqual(Path(opened_url.toLocalFile()), target.resolve())
                self.assertEqual(controller.errorText, "")
        finally:
            controller.shutdown()

    def test_missing_visualizer_json_is_not_opened(self) -> None:
        controller = AppController()
        try:
            controller._visualizer_json_path = str(Path(tempfile.gettempdir()) / "missing-ptcg-visualizer.json")
            with patch("ptcg_desktop.controller.QDesktopServices") as desktop:
                controller.openVisualizerJson()
                desktop.openUrl.assert_not_called()
            self.assertIn("見つかりません", controller.errorText)
        finally:
            controller.shutdown()

    def test_official_visualizer_launcher_requires_an_explicit_browser_confirmation(self) -> None:
        controller = AppController()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary) / "match.visualizer.json"
                target.write_text("[]", encoding="utf-8")
                controller._visualizer_json_path = str(target)
                launcher = controller._official_visualizer_launcher_path()
                source = launcher.read_text(encoding="utf-8")
                self.assertIn('form.action = "https://ptcgvis.heroz.jp/Visualizer/Replay/0"', source)
                self.assertIn("確認ボタンを押すまでは", source)
                with patch("ptcg_desktop.controller.QDesktopServices") as desktop:
                    desktop.openUrl.return_value = True
                    controller.openOfficialVisualizerLauncher()
                    opened_url = desktop.openUrl.call_args.args[0]
                    self.assertEqual(Path(opened_url.toLocalFile()), launcher.resolve())
        finally:
            controller.shutdown()

    def test_replay_folder_is_opened_and_new_match_clears_json(self) -> None:
        controller = AppController()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                replay = Path(temporary) / "match.ptcgmatch"
                controller._replay_path = str(replay)
                controller._visualizer_json_path = str(Path(temporary) / "match.visualizer.json")
                controller._visualizer_json_exact = True
                with patch("ptcg_desktop.controller.QDesktopServices") as desktop:
                    desktop.openUrl.return_value = True
                    controller.openReplayFolder()
                    opened_url = desktop.openUrl.call_args.args[0]
                    self.assertEqual(Path(opened_url.toLocalFile()), Path(temporary).resolve())
                controller._reset_match_data()
                self.assertEqual(controller._visualizer_json_path, "")
                self.assertFalse(controller._visualizer_json_exact)
        finally:
            controller.shutdown()


if __name__ == "__main__":
    unittest.main()
