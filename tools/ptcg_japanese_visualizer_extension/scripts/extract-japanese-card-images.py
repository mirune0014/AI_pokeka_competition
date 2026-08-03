"""Extract Japanese card images from the competition-provided PDF.

The PDF index links each card ID to a page that embeds one Japanese card image.
Two sizes are emitted because the official visualizer requests both a full and
a miniature texture for each card.
"""

from __future__ import annotations

import argparse
import io
import re
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError as exc:
        raise SystemExit(
            "PyMuPDF is required. Install it with: python -m pip install pymupdf"
        ) from exc

from PIL import Image


def build_mapping(document: fitz.Document) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for page_number in range(document.page_count):
        page = document[page_number]
        links = page.get_links()
        if not links:
            continue

        id_words = [
            (word[1], word[3], word[4])
            for word in page.get_text("words")
            if word[0] < 150 and re.fullmatch(r"\d+", word[4])
        ]
        if not id_words:
            continue

        for link in links:
            if link["kind"] != fitz.LINK_GOTO:
                continue
            rectangle = link["from"]
            if rectangle.x0 < 400:
                continue

            vertical_center = (rectangle.y0 + rectangle.y1) / 2
            nearest = min(
                id_words,
                key=lambda word: abs((word[0] + word[1]) / 2 - vertical_center),
            )
            distance = abs((nearest[0] + nearest[1]) / 2 - vertical_center)
            if distance < 8:
                mapping[int(nearest[2])] = link["page"]
    return mapping


def embedded_image(document: fitz.Document, page_number: int) -> Image.Image:
    images = document[page_number].get_images(full=True)
    if not images:
        raise ValueError(f"No embedded image found on page {page_number}")

    image_bytes = document.extract_image(images[0][0])["image"]
    with Image.open(io.BytesIO(image_bytes)) as image:
        return image.convert("RGB")


def save_resized(source: Image.Image, size: tuple[int, int], destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    resized = source.resize(size, Image.Resampling.LANCZOS)
    resized.save(destination, "JPEG", quality=82, optimize=True, progressive=True)
    return destination.stat().st_size


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("extension_root", type=Path)
    parser.add_argument("--limit", type=int, default=0)
    arguments = parser.parse_args()

    document = fitz.open(arguments.pdf)
    mapping = build_mapping(document)
    card_ids = sorted(mapping)
    if arguments.limit:
        card_ids = card_ids[: arguments.limit]

    full_root = arguments.extension_root / "assets" / "cards_jp"
    mini_root = arguments.extension_root / "assets" / "cards_jp_m"
    full_bytes = 0
    mini_bytes = 0

    for position, card_id in enumerate(card_ids, start=1):
        image = embedded_image(document, mapping[card_id])
        full_bytes += save_resized(image, (396, 552), full_root / f"{card_id}.jpg")
        mini_bytes += save_resized(image, (76, 106), mini_root / f"{card_id}.jpg")
        if position % 100 == 0:
            print(f"extracted {position}/{len(card_ids)}")

    print(
        f"mapped={len(mapping)} written={len(card_ids)} "
        f"full_mb={full_bytes / 1_000_000:.1f} "
        f"mini_mb={mini_bytes / 1_000_000:.1f}"
    )


if __name__ == "__main__":
    main()
