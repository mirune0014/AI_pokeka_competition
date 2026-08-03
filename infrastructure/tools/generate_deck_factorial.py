#!/usr/bin/env python3
"""Generate one-card deck swap candidates from a submission directory."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


MANIFEST_NAME = "deck_factorial_manifest.json"


@dataclass(frozen=True)
class Change:
    label: str
    card_id: str


def parse_change(value: str) -> Change:
    if value.count("=") != 1:
        raise argparse.ArgumentTypeError("changes must be LABEL=CARD_ID")
    label, card_id = (part.strip() for part in value.split("=", 1))
    if not label or not card_id:
        raise argparse.ArgumentTypeError("changes must have nonempty label and card ID")
    if any(not (character.isalnum() or character in "-_") for character in label):
        raise argparse.ArgumentTypeError("labels may contain only letters, numbers, '-' and '_'")
    return Change(label, card_id)


def read_deck(deck_path: Path) -> list[str]:
    with deck_path.open("r", encoding="utf-8", newline="") as deck_file:
        return [row[0].strip() for row in csv.reader(deck_file) if row and row[0].strip()]


def write_deck(deck_path: Path, cards: Iterable[str]) -> None:
    with deck_path.open("w", encoding="utf-8", newline="") as deck_file:
        writer = csv.writer(deck_file, lineterminator="\n")
        writer.writerows((card_id,) for card_id in cards)


def deck_hash(deck_path: Path) -> str:
    return hashlib.sha256(deck_path.read_bytes()).hexdigest()


def validate_deck(cards: Sequence[str], unlimited_cards: set[str], description: str) -> None:
    if len(cards) != 60:
        raise ValueError(f"{description} must contain exactly 60 cards; found {len(cards)}")
    over_limit = sorted(
        card_id for card_id, count in Counter(cards).items()
        if card_id not in unlimited_cards and count > 4
    )
    if over_limit:
        raise ValueError(f"{description} has more than four copies of: {', '.join(over_limit)}")


def candidate_name(add: Change, cut: Change) -> str:
    return f"add_{add.label}_{add.card_id}__cut_{cut.label}_{cut.card_id}"


def candidate_specs(adds: Sequence[Change], cuts: Sequence[Change]) -> list[tuple[Change, Change]]:
    return [(add, cut) for add in adds for cut in cuts if add.card_id != cut.card_id]


def validate_unique_labels(changes: Sequence[Change], kind: str) -> None:
    labels = [change.label for change in changes]
    if len(labels) != len(set(labels)):
        raise ValueError(f"{kind} labels must be unique")


def load_manifest(manifest_path: Path) -> dict:
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"could not read resume manifest {manifest_path}: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("candidates"), list):
        raise ValueError(f"resume manifest {manifest_path} has an invalid format")
    return data


def verify_resume(output_root: Path, manifest: dict) -> dict[str, dict]:
    entries: dict[str, dict] = {}
    for entry in manifest["candidates"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("directory"), str):
            raise ValueError("resume manifest contains an invalid candidate entry")
        directory = output_root / entry["directory"]
        deck_path = directory / "deck.csv"
        expected_hash = entry.get("deck_sha256")
        if not isinstance(expected_hash, str) or not deck_path.is_file():
            raise ValueError(f"resume candidate is incomplete: {entry['directory']}")
        actual_hash = deck_hash(deck_path)
        if actual_hash != expected_hash:
            raise ValueError(f"resume deck hash mismatch for {entry['directory']}")
        entries[entry["directory"]] = entry
    return entries


def generate(
    baseline_dir: Path,
    output_root: Path,
    adds: Sequence[Change],
    cuts: Sequence[Change],
    unlimited_cards: set[str],
    resume: bool = False,
) -> dict:
    baseline_dir = baseline_dir.resolve()
    output_root = output_root.resolve()
    source_deck_path = baseline_dir / "deck.csv"
    if not baseline_dir.is_dir() or not source_deck_path.is_file():
        raise ValueError(f"baseline directory must contain deck.csv: {baseline_dir}")
    if baseline_dir == output_root or baseline_dir in output_root.parents:
        raise ValueError("output root must not be the baseline directory or its parent")
    if not adds or not cuts:
        raise ValueError("at least one --add and one --cut are required")
    validate_unique_labels(adds, "add")
    validate_unique_labels(cuts, "cut")

    source_cards = read_deck(source_deck_path)
    validate_deck(source_cards, unlimited_cards, "source deck")
    specs = candidate_specs(adds, cuts)

    existing_entries: dict[str, dict] = {}
    manifest_path = output_root / MANIFEST_NAME
    if output_root.exists() and any(output_root.iterdir()):
        if not resume:
            raise ValueError(f"output root is nonempty; use --resume to continue: {output_root}")
        existing_entries = verify_resume(output_root, load_manifest(manifest_path))
    elif output_root.exists() and not output_root.is_dir():
        raise ValueError(f"output root is not a directory: {output_root}")
    else:
        output_root.mkdir(parents=True, exist_ok=True)

    candidates = []
    for add, cut in specs:
        directory_name = candidate_name(add, cut)
        candidate_dir = output_root / directory_name
        previous = existing_entries.get(directory_name)
        if previous is not None:
            candidates.append(previous)
            continue
        if candidate_dir.exists():
            raise ValueError(f"candidate directory exists but is not in resume manifest: {candidate_dir}")
        if cut.card_id not in source_cards:
            raise ValueError(f"cut card ID is absent from source deck: {cut.card_id}")
        result_cards = list(source_cards)
        result_cards.remove(cut.card_id)
        result_cards.append(add.card_id)
        validate_deck(result_cards, unlimited_cards, f"candidate {directory_name}")
        shutil.copytree(baseline_dir, candidate_dir)
        write_deck(candidate_dir / "deck.csv", result_cards)
        candidates.append({
            "add_label": add.label,
            "add_card_id": add.card_id,
            "cut_label": cut.label,
            "cut_card_id": cut.card_id,
            "source_count": len(source_cards),
            "result_count": len(result_cards),
            "directory": directory_name,
            "deck_sha256": deck_hash(candidate_dir / "deck.csv"),
        })

    manifest = {
        "baseline_dir": str(baseline_dir),
        "source_count": len(source_cards),
        "candidates": candidates,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-dir", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--add", action="append", required=True, type=parse_change, metavar="LABEL=CARD_ID")
    parser.add_argument("--cut", action="append", required=True, type=parse_change, metavar="LABEL=CARD_ID")
    parser.add_argument("--unlimited-card", action="append", default=[], metavar="CARD_ID")
    parser.add_argument("--resume", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        generate(args.baseline_dir, args.output_root, args.add, args.cut, set(args.unlimited_card), args.resume)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
