from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ptcg_desktop.card_catalog import CardCatalog


class CardCatalogTests(unittest.TestCase):
    def test_json_names_translations_and_local_images(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = {
                "cardNames": {"42": "テストカード"},
                "englishCardNames": {"Test Card": "テストカード"},
                "attackNames": {"Metal Test": "メタルテスト"},
            }
            (root / "translations.json").write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )
            full = root / "assets" / "cards_jp" / "42.jpg"
            miniature = root / "assets" / "cards_jp_m" / "42.jpg"
            full.parent.mkdir(parents=True)
            miniature.parent.mkdir(parents=True)
            full.write_bytes(b"full")
            miniature.write_bytes(b"miniature")

            catalog = CardCatalog(root)

            self.assertEqual(catalog.display_name(42), "テストカード")
            self.assertEqual(catalog.display_name(999, "Test Card"), "テストカード")
            self.assertEqual(catalog.display_attack("Metal Test"), "メタルテスト")
            self.assertEqual(
                catalog.translate_text("使う → Test Card / Metal Test"),
                "使う → テストカード / メタルテスト",
            )
            self.assertEqual(catalog.image_path(42), full.resolve())
            self.assertEqual(catalog.image_path(42, miniature=True), miniature.resolve())

    def test_selecting_cards_folder_discovers_parent_translation_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "translations.json").write_text(
                json.dumps({"cardNames": {"42": "親辞書のカード"}}, ensure_ascii=False),
                encoding="utf-8",
            )
            cards = root / "assets" / "cards_jp"
            cards.mkdir(parents=True)
            image = cards / "42.jpg"
            image.write_bytes(b"image")

            catalog = CardCatalog(cards)

            self.assertEqual(catalog.display_name(42), "親辞書のカード")
            self.assertEqual(catalog.image_path(42), image.resolve())

    def test_missing_image_has_no_network_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            catalog = CardCatalog(temporary)
            self.assertIsNone(catalog.image_path(999))


if __name__ == "__main__":
    unittest.main()
