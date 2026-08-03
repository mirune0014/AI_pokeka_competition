from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ptcg_desktop.deck import DeckValidationError, read_deck_csv


class DeckEncodingTests(unittest.TestCase):
    def test_invalid_utf8_is_rejected_with_decode_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "文字コード異常 デッキ.csv"
            path.write_bytes(b"card_id,count\n1,59\n\xff,1\n")

            with self.assertRaises(DeckValidationError) as context:
                read_deck_csv(path)

            self.assertEqual(context.exception.code, "decode_error")


if __name__ == "__main__":
    unittest.main()
