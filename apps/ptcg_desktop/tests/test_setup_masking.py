from __future__ import annotations

import unittest

from helpers import full_frame, normal_observation
from ptcg_desktop.human_view import HumanViewProjector
from ptcg_desktop.models import MatchPhase


class SetupMaskingTests(unittest.TestCase):
    def test_opponent_interim_setup_counts_are_not_exposed(self) -> None:
        projector = HumanViewProjector("match-1", 0, b"x" * 32, {})
        view = projector.project(
            full_frame(turn=0),
            normal_observation(acting=0),
            revision=1,
            phase=MatchPhase.WAITING_FOR_HUMAN,
        )

        self.assertEqual(view["opponent"]["active"], [])
        self.assertEqual(view["opponent"]["bench"], [])


if __name__ == "__main__":
    unittest.main()
