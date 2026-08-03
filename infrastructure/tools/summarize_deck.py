from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from ptcg_common import DEFAULT_AGENT_DIR, DEFAULT_ENGINE_DIR, ensure_engine_on_path, read_deck, write_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize a deck.csv using cg card metadata.")
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    parser.add_argument("--deck", type=Path, default=DEFAULT_AGENT_DIR / "deck.csv")
    parser.add_argument("--out", type=Path, default=Path("_local_generated/analysis_outputs/deck_summary.csv"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_engine_on_path(args.engine_dir)
    from cg.api import all_card_data

    catalog = {card.cardId: card for card in all_card_data()}
    counts = Counter(read_deck(args.deck))
    rows = []
    for card_id, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        card = catalog.get(card_id)
        rows.append(
            {
                "card_id": card_id,
                "count": count,
                "name": getattr(card, "name", ""),
                "card_type": getattr(card, "cardType", ""),
                "hp": getattr(card, "hp", ""),
                "attacks": json.dumps(getattr(card, "attacks", []), ensure_ascii=False),
            }
        )
    write_csv(args.out, rows, ["card_id", "count", "name", "card_type", "hp", "attacks"])
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
