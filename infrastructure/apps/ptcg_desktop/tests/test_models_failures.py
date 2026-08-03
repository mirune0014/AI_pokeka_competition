from __future__ import annotations

import unittest

from ptcg_desktop.failures import classify_failure, human_forfeit, normal_result
from ptcg_desktop.models import InvalidTransition, MatchPhase, MatchStateMachine


class ModelFailureTests(unittest.TestCase):
    def test_state_machine_happy_path(self) -> None:
        machine = MatchStateMachine()
        for phase in (
            MatchPhase.STARTING,
            MatchPhase.WAITING_FOR_HUMAN,
            MatchPhase.ENGINE_PROCESSING,
            MatchPhase.FINISHING,
            MatchPhase.FINISHED,
            MatchPhase.REPLAY_SEALED,
        ):
            machine.move(phase)
        self.assertEqual(machine.phase, MatchPhase.REPLAY_SEALED)

    def test_invalid_transition(self) -> None:
        with self.assertRaises(InvalidTransition):
            MatchStateMachine().move(MatchPhase.REPLAY_SEALED)

    def test_agent_exception_is_human_technical_win(self) -> None:
        result = classify_failure("agent_exception", 1, phase=MatchPhase.AGENT_THINKING)
        self.assertEqual(result.classification, "technical_forfeit")
        self.assertEqual(result.winner_seat, 1)

    def test_timeout_at_engine_is_system_error(self) -> None:
        result = classify_failure("timeout", 0, phase=MatchPhase.ENGINE_PROCESSING)
        self.assertEqual(result.classification, "system_error")
        self.assertIsNone(result.winner_seat)

    def test_human_forfeit(self) -> None:
        self.assertEqual(human_forfeit(0).winner_seat, 1)

    def test_draw(self) -> None:
        self.assertIsNone(normal_result(2).winner_seat)


if __name__ == "__main__":
    unittest.main()
