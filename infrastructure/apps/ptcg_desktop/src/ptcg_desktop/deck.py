from __future__ import annotations

import csv
import io
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


CARD_ID_HEADERS = {"card_id", "cardid", "id", "カードid", "カード_id"}
COUNT_HEADERS = {"count", "quantity", "qty", "copies", "枚数", "数量"}


class DeckValidationError(ValueError):
    def __init__(self, code: str, message: str, *, row: int | None = None):
        self.code = code
        self.row = row
        super().__init__(message)


@dataclass(frozen=True)
class DeckValidationResult:
    cards: tuple[int, ...]
    counts: dict[int, int]
    total: int
    structure_verified: bool
    known_ids_verified: bool
    engine_accepted: bool | None = None
    regulation_verified: bool = False


def _normal_header(value: str) -> str:
    return value.strip().lower().replace(" ", "").replace("-", "_")


def _positive_int(value: str, *, row: int, field: str) -> int:
    text = value.strip()
    if not text:
        raise DeckValidationError("missing_value", f"{field} が空です。", row=row)
    try:
        result = int(text, 10)
    except ValueError as exc:
        raise DeckValidationError("not_integer", f"{field} は整数で指定してください。", row=row) from exc
    if result <= 0:
        raise DeckValidationError("not_positive", f"{field} は正の整数で指定してください。", row=row)
    return result


def parse_deck_text(text: str) -> list[int]:
    if "\x00" in text:
        raise DeckValidationError("nul_byte", "CSV に NUL 文字が含まれています。")
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        rows = [(number, [cell.strip() for cell in row]) for number, row in enumerate(reader, 1)]
    except csv.Error as exc:
        raise DeckValidationError("malformed_csv", f"CSV を読み込めません: {exc}") from exc
    rows = [(number, row) for number, row in rows if any(cell for cell in row)]
    if not rows:
        raise DeckValidationError("empty", "デッキ CSV が空です。")
    first_number, first = rows[0]
    normalized = [_normal_header(value) for value in first]
    id_index = next((index for index, value in enumerate(normalized) if value in CARD_ID_HEADERS), None)
    count_index = next((index for index, value in enumerate(normalized) if value in COUNT_HEADERS), None)
    output: list[int] = []
    if id_index is not None:
        data_rows = rows[1:]
        for row_number, row in data_rows:
            if id_index >= len(row):
                raise DeckValidationError("missing_card_id", "カード ID 列がありません。", row=row_number)
            card_id = _positive_int(row[id_index], row=row_number, field="カード ID")
            count = 1
            if count_index is not None:
                if count_index >= len(row):
                    raise DeckValidationError("missing_count", "枚数列がありません。", row=row_number)
                count = _positive_int(row[count_index], row=row_number, field="枚数")
            output.extend([card_id] * count)
    elif all(len(row) == 1 for _, row in rows):
        for row_number, row in rows:
            output.append(_positive_int(row[0], row=row_number, field="カード ID"))
    elif all(len(row) == 2 for _, row in rows):
        for row_number, row in rows:
            card_id = _positive_int(row[0], row=row_number, field="カード ID")
            count = _positive_int(row[1], row=row_number, field="枚数")
            output.extend([card_id] * count)
    else:
        raise DeckValidationError("columns", "card_id と count 列、または 1 行 1 ID の CSV が必要です。", row=first_number)
    return output


def parse_deck_bytes(data: bytes, *, max_bytes: int = 1024 * 1024) -> list[int]:
    if len(data) > max_bytes:
        raise DeckValidationError("too_large", f"CSV が {max_bytes} バイトを超えています。")
    try:
        text = data.decode("utf-8-sig", errors="strict")
    except UnicodeError as exc:
        raise DeckValidationError("decode_error", "CSV を UTF-8 として読み込めません。") from exc
    return parse_deck_text(text)


def read_deck_csv_snapshot(
    path: str | Path,
    *,
    max_bytes: int = 1024 * 1024,
) -> tuple[list[int], bytes]:
    source = Path(path)
    try:
        data = source.read_bytes()
    except OSError as exc:
        raise DeckValidationError("read_error", str(exc)) from exc
    return parse_deck_bytes(data, max_bytes=max_bytes), data


def read_deck_csv(path: str | Path, *, max_bytes: int = 1024 * 1024) -> list[int]:
    cards, _ = read_deck_csv_snapshot(path, max_bytes=max_bytes)
    return cards


def validate_deck(deck: Iterable[int], known_card_ids: set[int] | None = None) -> DeckValidationResult:
    cards = list(deck)
    if not all(type(card) is int and card > 0 for card in cards):
        raise DeckValidationError("invalid_card_id", "すべてのカード ID は正の整数である必要があります。")
    if len(cards) != 60:
        raise DeckValidationError("card_count", f"デッキは 60 枚必要ですが、{len(cards)} 枚です。")
    known_verified = known_card_ids is not None
    if known_card_ids is not None:
        unknown = sorted(set(cards) - known_card_ids)
        if unknown:
            raise DeckValidationError("unknown_card_id", f"未知のカード ID があります: {unknown}")
    return DeckValidationResult(tuple(cards), dict(Counter(cards)), len(cards), True, known_verified)
