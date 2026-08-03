from __future__ import annotations

import json
from pathlib import Path


class CardCatalog:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root).expanduser().resolve() if root else None
        self.data_root: Path | None = None
        self.names: dict[int, str] = {}
        self.english_names: dict[str, str] = {}
        self.attack_names: dict[str, str] = {}
        self._text_replacements: tuple[tuple[str, str], ...] = ()
        if self.root is not None:
            self._load_names()

    def _translation_candidates(self) -> list[Path]:
        if self.root is None:
            return []
        roots: list[Path] = []
        current = self.root
        for _ in range(4):
            if current not in roots:
                roots.append(current)
            if current.parent == current:
                break
            current = current.parent
        return [base / name for base in roots for name in ("translations.json", "translations.js")]

    def _load_names(self) -> None:
        assert self.root is not None
        for path in self._translation_candidates():
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8-sig", errors="strict")
                if path.suffix.lower() == ".js":
                    marker = "globalThis.PTCG_JA_TRANSLATIONS = Object.freeze("
                    start = text.find(marker)
                    end = text.rfind(");")
                    if start < 0 or end < 0:
                        continue
                    text = text[start + len(marker) : end]
                value = json.loads(text)
                raw_names = value.get("cardNames", value) if isinstance(value, dict) else {}
                if not isinstance(raw_names, dict):
                    continue
                self.names = {
                    int(card_id): name
                    for card_id, name in raw_names.items()
                    if str(card_id).isdigit() and isinstance(name, str) and name
                }
                raw_english = value.get("englishCardNames", {}) if isinstance(value, dict) else {}
                raw_attacks = value.get("attackNames", {}) if isinstance(value, dict) else {}
                self.english_names = (
                    {
                        name: translated
                        for name, translated in raw_english.items()
                        if isinstance(name, str) and name and isinstance(translated, str) and translated
                    }
                    if isinstance(raw_english, dict)
                    else {}
                )
                self.attack_names = (
                    {
                        name: translated
                        for name, translated in raw_attacks.items()
                        if isinstance(name, str) and name and isinstance(translated, str) and translated
                    }
                    if isinstance(raw_attacks, dict)
                    else {}
                )
                replacements = {**self.english_names, **self.attack_names}
                self._text_replacements = tuple(
                    sorted(replacements.items(), key=lambda item: (-len(item[0]), item[0]))
                )
                self.data_root = path.parent.resolve()
                return
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
                continue

    def display_name(self, card_id: int, fallback: str = "") -> str:
        return self.names.get(card_id) or self.english_names.get(fallback) or fallback or f"カード {card_id}"

    def display_attack(self, fallback: str = "") -> str:
        return self.attack_names.get(fallback) or fallback

    def translate_text(self, text: str) -> str:
        if not isinstance(text, str) or not text:
            return ""
        direct = self.english_names.get(text) or self.attack_names.get(text)
        if direct:
            return direct
        translated = text
        for source, target in self._text_replacements:
            if source in translated:
                translated = translated.replace(source, target)
        return translated

    def _image_roots(self, *, miniature: bool) -> list[Path]:
        if self.root is None:
            return []
        bases = [self.root]
        if self.data_root is not None and self.data_root not in bases:
            bases.append(self.data_root)
        roots: list[Path] = []
        preferred = "cards_jp_m" if miniature else "cards_jp"
        secondary = "cards_jp" if miniature else "cards_jp_m"
        for base in bases:
            candidates = [
                base.parent / preferred if base.name in {"cards_jp", "cards_jp_m"} else base / "assets" / preferred,
                base,
                base / preferred,
                base / "assets" / secondary,
                base / secondary,
            ]
            for candidate in candidates:
                if candidate not in roots:
                    roots.append(candidate)
        return roots

    def image_path(self, card_id: int, *, miniature: bool = False) -> Path | None:
        if self.root is None or type(card_id) is not int or card_id <= 0:
            return None
        for folder in self._image_roots(miniature=miniature):
            for suffix in (".jpg", ".jpeg", ".png", ".webp"):
                candidate = folder / f"{card_id}{suffix}"
                if candidate.is_file():
                    return candidate.resolve()
        return None
