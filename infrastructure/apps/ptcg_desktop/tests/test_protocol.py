from __future__ import annotations

import unittest

from ptcg_desktop.protocol import (
    DuplicateMessage,
    FrameTooLarge,
    MessageTracker,
    ProtocolError,
    decode_json,
    encode_json,
    make_envelope,
    validate_envelope,
)


class ProtocolTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        value = make_envelope("match.start", "match-1", {"text": "日本語", "value": 3})
        self.assertEqual(decode_json(encode_json(value)), value)

    def test_duplicate_json_key_is_rejected(self) -> None:
        with self.assertRaises(ProtocolError):
            decode_json(b'{"a":1,"a":2}')

    def test_nan_is_rejected(self) -> None:
        with self.assertRaises(ProtocolError):
            decode_json(b'{"value":NaN}')

    def test_non_object_is_rejected(self) -> None:
        with self.assertRaises(ProtocolError):
            decode_json(b'[]')

    def test_oversize_encode_is_rejected(self) -> None:
        with self.assertRaises(FrameTooLarge):
            encode_json({"large": "x" * 100}, max_bytes=20)

    def test_envelope_unknown_key_is_rejected(self) -> None:
        value = make_envelope("match.start", "match-1", {})
        value["extra"] = True
        with self.assertRaises(ProtocolError):
            validate_envelope(value)

    def test_duplicate_message_id_is_rejected(self) -> None:
        tracker = MessageTracker()
        value = make_envelope("match.start", "match-1", {}, message_id="same")
        tracker.accept(value)
        with self.assertRaises(DuplicateMessage):
            tracker.accept(value)


if __name__ == "__main__":
    unittest.main()
