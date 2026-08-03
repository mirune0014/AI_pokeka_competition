from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from infrastructure.tools.audit_alakazam_v2_h1_transactions import RULE, audit_suite


def _end(ordinal: int, **trace):
    version_trace = {
        "stage": "BASELINE_FALLBACK",
        "transaction_outcome": "NONE",
        "reason_tags": ["V2_BASELINE_FALLBACK"],
        "selected_rule": None,
        "transaction_started": False,
        "attach_verified": False,
        "attack_dispatched": False,
        "KO_resolved": False,
        "irreversible_abort_fault": False,
        "transaction_abort_reason": None,
    }
    version_trace.update(trace)
    return {
        "event": "CALL_END",
        "callback_ordinal": ordinal,
        "structurally_valid": True,
        "exception": None,
        "first_legal_fallback_selected": False,
        "generic_fallback_selected": False,
        "version_trace": version_trace,
    }


class V2H1AuditTests(unittest.TestCase):
    def _suite(self, rows):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        sidecar = (
            root
            / "runs"
            / "v2"
            / "historical_silver"
            / "seed_500"
            / "seat_0"
            / "sidecars"
            / "game_0000.jsonl"
        )
        sidecar.parent.mkdir(parents=True)
        sidecar.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )
        return temp, root

    def test_complete_transaction_and_pairing(self):
        rows = []
        for ordinal, end in enumerate(
            (
                _end(
                    0,
                    stage="ATTACH_DISPATCHED",
                    transaction_outcome="ACTIVE",
                    selected_rule=RULE,
                    transaction_started=True,
                ),
                _end(
                    1,
                    stage="ATTACK_DISPATCHED",
                    transaction_outcome="ACTIVE",
                    selected_rule=RULE,
                    attach_verified=True,
                    attack_dispatched=True,
                ),
                _end(
                    2,
                    stage="KO_RESOLVED",
                    transaction_outcome="COMPLETE",
                    selected_rule=RULE,
                    KO_resolved=True,
                ),
            )
        ):
            rows.append({"event": "CALL_START", "callback_ordinal": ordinal})
            rows.append(end)
        temp, root = self._suite(rows)
        try:
            audit = audit_suite(root)
        finally:
            temp.cleanup()
        self.assertEqual(audit["callback_starts"], 3)
        self.assertEqual(audit["callback_ends"], 3)
        self.assertEqual(audit["transaction_starts"], 1)
        self.assertEqual(audit["attach_verified"], 1)
        self.assertEqual(audit["attacks_dispatched"], 1)
        self.assertEqual(audit["ko_resolved"], 1)
        self.assertEqual(audit["historical_silver_completes"], 1)
        self.assertEqual(audit["hard_fault_count"], 0)

    def test_pending_and_fault_rows_are_counted(self):
        rows = [
            {"event": "CALL_START", "callback_ordinal": 0},
            _end(
                0,
                stage="ATTACH_DISPATCHED",
                transaction_outcome="ACTIVE",
                selected_rule=RULE,
                transaction_started=True,
            ),
        ]
        temp, root = self._suite(rows)
        try:
            audit = audit_suite(root)
        finally:
            temp.cleanup()
        self.assertEqual(audit["pending_transactions"], 1)
        self.assertEqual(audit["hard_fault_count"], 1)


if __name__ == "__main__":
    unittest.main()
