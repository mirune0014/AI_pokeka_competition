from __future__ import annotations

import argparse
import csv
import hashlib
import re
from pathlib import Path


REQUIRED_COLUMNS = {
    "order",
    "style",
    "source_deck_sha256",
    "local_agent_path",
    "card_count",
    "deck_copy_status",
}


def read_card_ids(path: Path) -> list[int]:
    return [int(token) for token in re.findall(r"\d+", path.read_text(encoding="utf-8"))]


def canonical_sha256(card_ids: list[int]) -> str:
    payload = " ".join(str(card_id) for card_id in sorted(card_ids)).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def verify_manifest(repo_root: Path, manifest_path: Path) -> list[str]:
    errors: list[str] = []
    with manifest_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames or [])
        if missing:
            return [f"manifest is missing columns: {', '.join(sorted(missing))}"]

        rows = list(reader)

    if len(rows) != 16:
        errors.append(f"expected 16 policy tracks, found {len(rows)}")

    orders = [row["order"] for row in rows]
    if orders != [str(index) for index in range(1, len(rows) + 1)]:
        errors.append("track order must be contiguous and sorted from 1")

    for row in rows:
        label = f"track {row['order']} ({row['style']})"
        deck_path = repo_root / row["local_agent_path"] / "deck.csv"
        if not deck_path.is_file():
            errors.append(f"{label}: missing {deck_path}")
            continue

        card_ids = read_card_ids(deck_path)
        expected_count = int(row["card_count"])
        if len(card_ids) != expected_count:
            errors.append(
                f"{label}: expected {expected_count} cards, found {len(card_ids)}"
            )

        actual_sha = canonical_sha256(card_ids)
        expected_sha = row["source_deck_sha256"].lower()
        if actual_sha != expected_sha:
            errors.append(
                f"{label}: deck SHA mismatch, expected {expected_sha}, found {actual_sha}"
            )

        if row["deck_copy_status"] != "exact":
            errors.append(f"{label}: deck_copy_status is not exact")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify exact local copies for Gold policy tracks.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("docs/gold_meta_rulebase_local_agents.csv"),
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = args.manifest
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path

    errors = verify_manifest(repo_root, manifest_path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"OK: verified 16 exact Gold policy-track deck copies from {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
