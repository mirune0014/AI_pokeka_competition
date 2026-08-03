from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

from ptcg_desktop.engine_runtime import read_flat_deck
from ptcg_desktop.supervisor import MatchLaunch, MatchSupervisor


SOURCE = os.environ.get("PTCG_SUBMISSION_ARTIFACT")
RUN_LONG = os.environ.get("PTCG_RUN_LONG_INTEGRATION") == "1"


def choose_safe_tokens(decision: dict[str, object]) -> list[str]:
    options = list(decision.get("options") or [])
    minimum = int(decision.get("min_count", 0))
    maximum = int(decision.get("max_count", 0))
    context = decision.get("context")
    select_type = decision.get("select_type")

    if select_type == "main" and options:
        priority = ("ability", "evolve", "attach", "play", "attack", "retreat", "end")
        for kind in priority:
            for option in options:
                if option.get("kind") == kind:
                    return [str(option["token"])]

    if context == "context_2" and minimum == 0 and maximum > 0:
        count = min(maximum, 3, len(options))
        return [str(option["token"]) for option in options[:count]]

    if minimum == 0:
        return []
    return [str(option["token"]) for option in options[:minimum]]


@unittest.skipUnless(
    SOURCE and RUN_LONG,
    "set PTCG_SUBMISSION_ARTIFACT and PTCG_RUN_LONG_INTEGRATION=1 for full matches",
)
class EngineFullMatchTests(unittest.TestCase):
    def test_both_human_seats_reach_normal_completion(self) -> None:
        assert SOURCE is not None
        source = Path(SOURCE).resolve()
        deck = read_flat_deck(source / "deck.csv")
        for human_seat in (0, 1):
            with self.subTest(human_seat=human_seat), tempfile.TemporaryDirectory(
                prefix=f"ptcg-full-seat-{human_seat}-"
            ) as temporary:
                supervisor = MatchSupervisor()
                try:
                    supervisor.start(
                        MatchLaunch(
                            source,
                            deck,
                            human_seat,
                            Path(temporary) / "completed.ptcgmatch",
                            max_steps=1000,
                        )
                    )
                    handled: set[str] = set()
                    deadline = time.monotonic() + 300
                    while time.monotonic() < deadline:
                        for event in supervisor.poll(0.05):
                            if event["message_type"] != "decision.required":
                                continue
                            decision = event["payload"]["decision"]
                            request_id = decision["request_id"]
                            if request_id in handled:
                                continue
                            handled.add(request_id)
                            supervisor.submit_decision(
                                request_id,
                                decision["state_revision"],
                                choose_safe_tokens(decision),
                            )
                        if supervisor.result is not None and supervisor.finalized:
                            break
                    self.assertIsNotNone(supervisor.result)
                    self.assertFalse(supervisor.running)
                    self.assertEqual(supervisor.result.classification, "normal")
                    self.assertIn(supervisor.result.winner_seat, (0, 1, None))
                    self.assertGreater(supervisor.result.battle_select_count, 0)
                    self.assertIn(supervisor.result.first_player, (0, 1))
                    self.assertTrue(supervisor.replay_available)
                finally:
                    supervisor.close()


if __name__ == "__main__":
    unittest.main()
