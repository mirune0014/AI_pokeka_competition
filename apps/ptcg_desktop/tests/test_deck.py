from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ptcg_desktop.deck import DeckValidationError, parse_deck_text, read_deck_csv, validate_deck


class DeckTests(unittest.TestCase):
    def test_flat_sixty(self) -> None:
        deck = parse_deck_text("\n".join(str(index + 1) for index in range(60)))
        self.assertEqual(validate_deck(deck).total, 60)

    def test_counted_csv_with_bom_and_japanese_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "空白 デッキ.csv"
            path.write_text("\ufeffcard_id,count\n1,30\n2,30\n", encoding="utf-8")
            result = validate_deck(read_deck_csv(path), {1, 2})
            self.assertEqual(result.counts, {1: 30, 2: 30})

    def test_headerless_two_columns(self) -> None:
        self.assertEqual(len(parse_deck_text("1,20\n2,40\n")), 60)

    def test_59_cards_is_rejected(self) -> None:
        with self.assertRaisesRegex(DeckValidationError, "60"):
            validate_deck([1] * 59)

    def test_unknown_id_is_rejected(self) -> None:
        with self.assertRaises(DeckValidationError) as context:
            validate_deck([9] * 60, {1, 2})
        self.assertEqual(context.exception.code, "unknown_card_id")

    def test_zero_count_is_rejected(self) -> None:
        with self.assertRaises(DeckValidationError):
            parse_deck_text("card_id,count\n1,0\n")

    def test_malformed_columns_are_rejected(self) -> None:
        with self.assertRaises(DeckValidationError):
            parse_deck_text("1,2,3\n")


if __name__ == "__main__":
    unittest.main()
