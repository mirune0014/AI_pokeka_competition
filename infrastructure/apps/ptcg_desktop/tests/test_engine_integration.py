from __future__ import annotations

import os
import tempfile
import time
import unittest
import uuid
from pathlib import Path

from ptcg_desktop.artifacts import cleanup_stage, stage_artifact, verify_artifact
from ptcg_desktop.engine_runtime import read_flat_deck
from ptcg_desktop.supervisor import MatchLaunch, MatchSupervisor, validate_deck_in_worker


SOURCE = os.environ.get("PTCG_SUBMISSION_ARTIFACT")


@unittest.skipUnless(SOURCE, "set PTCG_SUBMISSION_ARTIFACT for engine integration tests")
class EngineIntegrationTests(unittest.TestCase):
    def source(self) -> Path:
        assert SOURCE is not None
        return Path(SOURCE).resolve()

    def test_disposable_deck_validation_accepts_both_seats(self) -> None:
        deck = read_flat_deck(self.source() / "deck.csv")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage = stage_artifact(self.source(), f"integration-{uuid.uuid4()}", root=root)
            try:
                for seat in (0, 1):
                    result = validate_deck_in_worker(stage, deck, seat, timeout=30)
                    self.assertTrue(result["structure_verified"])
                    self.assertTrue(result["known_ids_verified"])
                    self.assertTrue(result["engine_accepted"])
                    self.assertFalse(result["regulation_verified"])
                self.assertTrue(verify_artifact(stage).verified)
            finally:
                cleanup_stage(stage, root=root)

    def _drive(self, human_seat: int, *, forfeit: bool = False) -> MatchSupervisor:
        deck = read_flat_deck(self.source() / "deck.csv")
        replay_root = Path(tempfile.mkdtemp(prefix="ptcg-integration-replay-"))
        supervisor = MatchSupervisor()
        supervisor.start(
            MatchLaunch(
                self.source(),
                deck,
                human_seat,
                replay_root / f"seat-{human_seat}.ptcgmatch",
                max_steps=8,
            )
        )
        deadline = time.monotonic() + 180
        forfeited = False
        handled_requests: set[str] = set()
        while time.monotonic() < deadline:
            events = supervisor.poll(0.05)
            for event in events:
                if event["message_type"] != "decision.required":
                    continue
                decision = event["payload"]["decision"]
                if decision["request_id"] in handled_requests:
                    continue
                handled_requests.add(decision["request_id"])
                if forfeit and not forfeited:
                    supervisor.forfeit()
                    forfeited = True
                else:
                    count = decision["min_count"]
                    tokens = [option["token"] for option in decision["options"][:count]]
                    supervisor.submit_decision(decision["request_id"], decision["state_revision"], tokens)
            if supervisor.result is not None and supervisor.finalized:
                break
        self.assertIsNotNone(supervisor.result)
        self.assertFalse(supervisor.running)
        return supervisor

    def test_forfeit_during_agent_thinking_stops_before_agent_selection(self) -> None:
        deck = read_flat_deck(self.source() / "deck.csv")
        with tempfile.TemporaryDirectory(prefix="ptcg-agent-forfeit-") as temporary:
            supervisor = MatchSupervisor()
            try:
                supervisor.start(
                    MatchLaunch(
                        self.source(),
                        deck,
                        1,
                        Path(temporary) / "agent-forfeit.ptcgmatch",
                        max_steps=20,
                        ai_display_delay_ms=750,
                    )
                )
                latest_revision = 0
                sent_forfeit = False
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    for event in supervisor.poll(0.05):
                        if event["message_type"] == "state.update":
                            latest_revision = event["payload"]["state"]["state_revision"]
                        elif event["message_type"] == "phase.changed" and event["payload"]["phase"] == "AGENT_THINKING":
                            if not sent_forfeit:
                                supervisor.forfeit()
                                sent_forfeit = True
                    if supervisor.result is not None and supervisor.finalized:
                        break
                self.assertTrue(sent_forfeit)
                self.assertIsNotNone(supervisor.result)
                self.assertEqual(supervisor.result.classification, "human_forfeit")
                self.assertEqual(supervisor.result.battle_select_count, latest_revision)
                self.assertTrue(supervisor.replay_available)
            finally:
                supervisor.close()

    def test_spawn_match_player_zero_reaches_bounded_system_result_and_seals(self) -> None:
        supervisor = self._drive(0)
        try:
            self.assertEqual(supervisor.result.classification, "system_error")
            self.assertEqual(supervisor.result.reason_code, "max_steps")
            self.assertTrue(supervisor.replay_available)
        finally:
            supervisor.close()

    def test_spawn_match_player_one_can_forfeit_and_seals(self) -> None:
        supervisor = self._drive(1, forfeit=True)
        try:
            self.assertEqual(supervisor.result.classification, "human_forfeit")
            self.assertEqual(supervisor.result.winner_seat, 0)
            self.assertTrue(supervisor.replay_available)
        finally:
            supervisor.close()


if __name__ == "__main__":
    unittest.main()
