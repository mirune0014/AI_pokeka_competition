from __future__ import annotations

import argparse
import json
from pathlib import Path

from ptcg_common import DEFAULT_ENGINE_DIR, dataclass_to_dict, ensure_engine_on_path, write_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dump card and attack metadata from the cg engine.")
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    parser.add_argument("--out-dir", type=Path, default=Path("analysis_outputs/catalog"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_engine_on_path(args.engine_dir)
    from cg.api import all_attack, all_card_data

    args.out_dir.mkdir(parents=True, exist_ok=True)
    cards = [dataclass_to_dict(card) for card in all_card_data()]
    attacks = [dataclass_to_dict(attack) for attack in all_attack()]

    (args.out_dir / "cards.json").write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out_dir / "attacks.json").write_text(
        json.dumps(attacks, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    write_csv(
        args.out_dir / "cards.csv",
        cards,
        [
            "cardId",
            "name",
            "cardType",
            "hp",
            "energyType",
            "basic",
            "stage1",
            "stage2",
            "ex",
            "megaEx",
            "tera",
            "aceSpec",
            "evolvesFrom",
            "attacks",
        ],
    )
    write_csv(args.out_dir / "attacks.csv", attacks, ["attackId", "name", "damage", "energies", "text"])
    print(f"Wrote {len(cards)} cards and {len(attacks)} attacks to {args.out_dir}")


if __name__ == "__main__":
    main()
