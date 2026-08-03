from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from helpers import full_frame
from ptcg_desktop.failures import normal_result
from ptcg_desktop.replay import ReplayBuilder
from ptcg_desktop.supervisor import MatchSupervisor


class _ExitedProcess:
    exitcode = 0

    @staticmethod
    def is_alive() -> bool:
        return False

    @staticmethod
    def join(timeout: float = 0) -> None:
        del timeout


def _sealed_replay(path: Path) -> tuple[Path, str, object]:
    result = replace(
        normal_result(0),
        artifact_manifest_id="test-manifest",
        human_seat=0,
        first_player=0,
        turn_count=1,
        battle_select_count=0,
        replay_complete=True,
    )
    builder = ReplayBuilder("match-1")
    builder.ingest_visualizer([full_frame()], revision=0, captured_after="battle_start")
    replay_path, replay_hash = builder.seal(
        path,
        artifact={"submission_id": "55155015", "artifact_manifest_id": "test-manifest", "files": {}},
        settings={"human_seat": 0, "human_deck_source_sha256": "A", "started_at_utc": "start"},
        decks={"human_sha256": "B"},
        public_log=[],
        result=result.to_dict(),
        diagnostics={"steps": 0, "complete": True, "started_at_utc": "start", "finished_at_utc": "finish"},
    )
    return replay_path, replay_hash, result


class SupervisorTerminalTransactionTests(unittest.TestCase):
    def test_verified_replay_recovers_result_when_final_event_is_lost(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path, digest, expected = _sealed_replay(Path(temporary) / "match.ptcgmatch")
            supervisor = MatchSupervisor()
            supervisor.process = _ExitedProcess()  # type: ignore[assignment]
            supervisor.replay_candidate = {"path": str(path), "sha256": digest, "complete": True}

            supervisor._finalize_if_exited()

            self.assertTrue(supervisor.finalized)
            self.assertTrue(supervisor.replay_available)
            self.assertEqual(supervisor.result, expected)

    def test_disagreement_between_event_and_replay_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path, digest, _ = _sealed_replay(Path(temporary) / "match.ptcgmatch")
            supervisor = MatchSupervisor()
            supervisor.process = _ExitedProcess()  # type: ignore[assignment]
            supervisor.result = normal_result(1)
            supervisor.match_finished_received = True
            supervisor.replay_candidate = {"path": str(path), "sha256": digest, "complete": True}

            supervisor._finalize_if_exited()

            self.assertFalse(supervisor.replay_available)
            self.assertIsNotNone(supervisor.result)
            self.assertEqual(supervisor.result.reason_code, "replay_verification_failed")


if __name__ == "__main__":
    unittest.main()
