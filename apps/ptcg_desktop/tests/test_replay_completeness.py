from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from helpers import full_frame
from ptcg_desktop.replay import ReplayBuilder, ReplayError


class ReplayCompletenessTests(unittest.TestCase):
    def test_battle_select_without_a_new_frame_is_rejected(self) -> None:
        builder = ReplayBuilder("match-1")
        initial = full_frame()
        builder.ingest_visualizer([initial], revision=0, captured_after="battle_start")

        with self.assertRaisesRegex(ReplayError, "exactly one"):
            builder.ingest_visualizer([initial], revision=1, captured_after="battle_select")

    def test_battle_select_with_two_new_frames_is_rejected(self) -> None:
        builder = ReplayBuilder("match-1")
        initial = full_frame()
        second = full_frame(turn=2)
        third = full_frame(turn=3)
        builder.ingest_visualizer([initial], revision=0, captured_after="battle_start")

        with self.assertRaisesRegex(ReplayError, "exactly one"):
            builder.ingest_visualizer([initial, second, third], revision=1, captured_after="battle_select")

    def test_complete_seal_requires_initial_plus_one_frame_per_step(self) -> None:
        builder = ReplayBuilder("match-1")
        initial = full_frame()
        builder.ingest_visualizer([initial], revision=0, captured_after="battle_start")

        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ReplayError, "frame count"):
                builder.seal(
                    Path(temporary) / "missing.ptcgmatch",
                    artifact={},
                    settings={"human_seat": 0},
                    decks={},
                    public_log=[],
                    result={"classification": "system_error"},
                    diagnostics={"steps": 1, "complete": True},
                )


if __name__ == "__main__":
    unittest.main()
