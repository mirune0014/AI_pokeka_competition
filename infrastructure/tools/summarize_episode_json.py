from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from ptcg_common import DEFAULT_ENGINE_DIR, ensure_engine_on_path, write_csv


CARD_HINT_KEYS = {
    "hp",
    "cardType",
    "energyCards",
    "tools",
    "attacks",
    "damage",
    "preEvolution",
    "specialConditions",
}


def iter_json_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
    else:
        yield from sorted(path.rglob("*.json"))


def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def collect_counts(doc: Any) -> tuple[Counter[int], Counter[int]]:
    card_counts: Counter[int] = Counter()
    attack_counts: Counter[int] = Counter()
    for item in walk(doc):
        card_id = item.get("cardId")
        if isinstance(card_id, int):
            card_counts[card_id] += 1
        generic_id = item.get("id")
        if isinstance(generic_id, int) and CARD_HINT_KEYS.intersection(item.keys()):
            card_counts[generic_id] += 1
        attack_id = item.get("attackId")
        if isinstance(attack_id, int):
            attack_counts[attack_id] += 1
    return card_counts, attack_counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize visible card and attack IDs in public episode JSON files."
    )
    parser.add_argument("path", type=Path, help="A JSON file or directory containing public episode JSON files.")
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    parser.add_argument("--out-dir", type=Path, default=Path("_local_generated/analysis_outputs/episode_meta"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_engine_on_path(args.engine_dir)
    from cg.api import all_attack, all_card_data

    card_names = {card.cardId: card.name for card in all_card_data()}
    attack_names = {attack.attackId: attack.name for attack in all_attack()}

    total_cards: Counter[int] = Counter()
    total_attacks: Counter[int] = Counter()
    file_rows = []
    for path in iter_json_files(args.path):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            doc = json.loads(path.read_text())
        cards, attacks = collect_counts(doc)
        total_cards.update(cards)
        total_attacks.update(attacks)
        file_rows.append(
            {
                "file": str(path),
                "visible_card_mentions": sum(cards.values()),
                "unique_visible_cards": len(cards),
                "attack_mentions": sum(attacks.values()),
                "unique_attacks": len(attacks),
            }
        )

    card_rows = [
        {"card_id": card_id, "name": card_names.get(card_id, ""), "mentions": count}
        for card_id, count in total_cards.most_common()
    ]
    attack_rows = [
        {"attack_id": attack_id, "name": attack_names.get(attack_id, ""), "mentions": count}
        for attack_id, count in total_attacks.most_common()
    ]

    write_csv(
        args.out_dir / "files.csv",
        file_rows,
        ["file", "visible_card_mentions", "unique_visible_cards", "attack_mentions", "unique_attacks"],
    )
    write_csv(args.out_dir / "card_counts.csv", card_rows, ["card_id", "name", "mentions"])
    write_csv(args.out_dir / "attack_counts.csv", attack_rows, ["attack_id", "name", "mentions"])
    print(f"Processed {len(file_rows)} files into {args.out_dir}")


if __name__ == "__main__":
    main()
