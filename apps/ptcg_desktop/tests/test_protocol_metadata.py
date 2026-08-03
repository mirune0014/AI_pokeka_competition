from __future__ import annotations

import unittest

from ptcg_desktop.protocol import ENVELOPE_KEYS, make_envelope


class ProtocolMetadataTests(unittest.TestCase):
    def test_every_message_has_required_common_metadata(self) -> None:
        envelope = make_envelope(
            "decision.submit",
            "match-1",
            {"request_id": "request-1", "state_revision": 7, "tokens": []},
        )

        self.assertEqual(set(envelope), ENVELOPE_KEYS)
        self.assertEqual(envelope["protocol_version"], 1)
        self.assertEqual(envelope["message_type"], "decision.submit")
        self.assertEqual(envelope["request_id"], "request-1")
        self.assertEqual(envelope["state_revision"], 7)
        self.assertEqual(envelope["step_id"], 7)


if __name__ == "__main__":
    unittest.main()
