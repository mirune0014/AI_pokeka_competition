from __future__ import annotations

import unittest

from ptcg_desktop.failures import normal_result
from ptcg_desktop.supervisor import MatchSupervisor


class _ExitedProcess:
    exitcode = 137

    @staticmethod
    def is_alive() -> bool:
        return False

    @staticmethod
    def join(timeout: float = 0) -> None:
        del timeout


class SupervisorFinalizationTests(unittest.TestCase):
    def test_finished_match_without_sealed_replay_becomes_system_error(self) -> None:
        supervisor = MatchSupervisor()
        supervisor.process = _ExitedProcess()  # type: ignore[assignment]
        supervisor.result = normal_result(0)
        supervisor.match_finished_received = True

        supervisor._finalize_if_exited()

        self.assertIsNotNone(supervisor.result)
        self.assertEqual(supervisor.result.classification, "system_error")
        self.assertEqual(supervisor.result.reason_code, "replay_missing")
        self.assertFalse(supervisor.replay_available)
        self.assertEqual(supervisor.exit_code, 137)


if __name__ == "__main__":
    unittest.main()
