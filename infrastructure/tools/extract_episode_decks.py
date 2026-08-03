from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from ptcg_common import DEFAULT_ENGINE_DIR, ensure_engine_on_path


ARCHETYPE_MARKERS: list[tuple[str, set[int]]] = [
    ("marnie_grimmsnarl", {646, 647, 648, 1259}),
    ("starmie_froslass", {1030, 1031, 860, 861}),
    ("archaludon_metal", {169, 190, 666, 1244}),
    ("kangaskhan_crustle", {756}),
    ("great_tusk_crustle", {58}),
    ("mega_abomasnow_kyogre", {721, 722, 723}),
    ("mega_lucario", {677, 678}),
    ("hop_trevenant", {288, 289, 299, 304, 307, 308, 309, 310, 878, 879}),
    ("chandelure_psychic_control", {97, 98, 164, 494}),
    ("alakazam_psychic", {245, 743}),
    ("rocket_mewtwo_spidops", {400, 401, 431, 434}),
    ("okidogi_barbaracle", {116, 675, 676, 1051, 1052}),
    ("iono_bellibolt", {265, 266, 268, 269, 270, 271}),
    ("ogerpon_toolbox", {95, 96, 99, 108, 117, 349, 358, 370, 386}),
    ("dragapult", {120, 121}),
    ("cynthia_garchomp", {341, 342, 379, 380, 381}),
    ("gardevoir", {747}),
    ("charizard", {790, 928}),
]


def iter_json_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
    else:
        yield from (candidate for candidate in sorted(path.rglob("*.json")) if candidate.is_file())


def read_doc(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        try:
            return json.loads(path.read_text())
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None


def initial_decks(doc: dict[str, Any]) -> list[list[int]]:
    steps = doc.get("steps") or []
    for step_group in steps[:5]:
        for agent_step in step_group or []:
            for vis in agent_step.get("visualize") or []:
                action = vis.get("action")
                if (
                    isinstance(action, list)
                    and len(action) == 2
                    and all(isinstance(deck, list) and len(deck) == 60 for deck in action)
                ):
                    return [[int(card_id) for card_id in deck] for deck in action]
    return []


def classify(deck_ids: list[int]) -> str:
    ids = set(deck_ids)
    if 756 in ids:
        return "kangaskhan_crustle"
    if 58 in ids:
        return "great_tusk_crustle"
    if {96, 272, 344, 345}.issubset(ids):
        return "teal_ogerpon_clefairy_crustle"
    if {112, 344, 345}.issubset(ids):
        return "crustle_munkidori_control"
    if {414, 506}.issubset(ids):
        return "cubchoo_articuno_control"
    if {344, 345}.issubset(ids):
        return "crustle_control"
    scored = []
    for order, (name, markers) in enumerate(ARCHETYPE_MARKERS):
        hit = len(ids & markers)
        if hit:
            scored.append((hit, -order, name))
    if not scored:
        return "unknown"
    scored.sort(reverse=True)
    return scored[0][2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract and classify deck lists from public episode JSON files.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("_local_generated/analysis_outputs/episode_decks"))
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    args = parser.parse_args()

    ensure_engine_on_path(args.engine_dir)
    from cg.api import all_card_data

    card_names = {card.cardId: card.name for card in all_card_data()}
    args.out_dir.mkdir(parents=True, exist_ok=True)

    deck_rows: list[dict[str, Any]] = []
    card_rows: list[dict[str, Any]] = []
    archetype_counts: Counter[str] = Counter()

    skipped_documents = 0
    for path in iter_json_files(args.path):
        doc = read_doc(path)
        if not isinstance(doc, dict):
            skipped_documents += 1
            continue
        teams = ((doc.get("info") or {}).get("TeamNames")) or ["player0", "player1"]
        episode_id = (doc.get("info") or {}).get("EpisodeId") or path.stem
        rewards = doc.get("rewards") or []
        for player_index, deck in enumerate(initial_decks(doc)):
            counts = Counter(deck)
            archetype = classify(deck)
            archetype_counts[archetype] += 1
            team_name = teams[player_index] if player_index < len(teams) else f"player{player_index}"
            deck_id = f"{episode_id}_p{player_index}"
            deck_rows.append(
                {
                    "episode_id": episode_id,
                    "file": str(path),
                    "player_index": player_index,
                    "team": team_name,
                    "reward": rewards[player_index] if player_index < len(rewards) else "",
                    "archetype": archetype,
                    "deck_id": deck_id,
                    "deck": " ".join(str(card_id) for card_id in deck),
                }
            )
            for card_id, count in counts.most_common():
                card_rows.append(
                    {
                        "episode_id": episode_id,
                        "player_index": player_index,
                        "team": team_name,
                        "archetype": archetype,
                        "card_id": card_id,
                        "name": card_names.get(card_id, ""),
                        "count": count,
                    }
                )

    with (args.out_dir / "decks.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["episode_id", "file", "player_index", "team", "reward", "archetype", "deck_id", "deck"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deck_rows)

    with (args.out_dir / "deck_cards.csv").open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["episode_id", "player_index", "team", "archetype", "card_id", "name", "count"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(card_rows)

    with (args.out_dir / "archetypes.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["archetype", "decks"])
        writer.writeheader()
        for archetype, count in archetype_counts.most_common():
            writer.writerow({"archetype": archetype, "decks": count})

    print(f"Wrote {args.out_dir}; skipped {skipped_documents} non-object or invalid JSON files")


if __name__ == "__main__":
    main()
