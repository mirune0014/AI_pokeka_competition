from __future__ import annotations

import unittest

from ptcg_desktop.failures import classify_failure
from ptcg_desktop.supervisor import MatchSupervisor


class _AliveThenExitedProcess:
    exitcode = 0

    def __init__(self) -> None:
        self._checks = 0

    def is_alive(self) -> bool:
        self._checks += 1
        return self._checks == 1

    @staticmethod
    def join(timeout: float = 0) -> None:
        del timeout


class SupervisorExitGateTests(unittest.TestCase):
    def test_stopped_process_is_not_finalized_until_exit_handling_runs(self) -> None:
        supervisor = MatchSupervisor()
        supervisor.process = _AliveThenExitedProcess()  # type: ignore[assignment]
        supervisor.result = classify_failure("max_steps", 0)

        # The poll-side check can still see a live child immediately before the
        # caller observes that it stopped.  That must not expose the replay yet.
        supervisor._finalize_if_exited()
        self.assertFalse(supervisor.finalized)
        self.assertFalse(supervisor.running)

        supervisor._finalize_if_exited()

        self.assertTrue(supervisor.finalized)
        self.assertEqual(supervisor.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
