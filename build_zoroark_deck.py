from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
ENGINE_DIR = REPO_ROOT / "submission_archaludon"
OUT_DIR = REPO_ROOT / "submission_zoroark"
LOG_DIR = REPO_ROOT / "logs"


@dataclass(frozen=True)
class DeckEntry:
    name: str
    count: int
    replacement: str | None = None
    note: str = ""


DECK_LIST = [
    DeckEntry("N's Zorua", 4),
    DeckEntry("N's Zoroark ex", 4),
    DeckEntry("N's Zekrom", 2),
    DeckEntry("N's Darumaka", 1),
    DeckEntry("N's Darmanitan", 1),
    DeckEntry("Tatsugiri", 1),
    DeckEntry("Budew", 1),
    DeckEntry("Yveltal", 1),
    DeckEntry("Munkidori", 1),
    DeckEntry("Pecharunt ex", 1),
    DeckEntry("Fezandipiti ex", 1),
    DeckEntry("Meowth ex", 1),
    DeckEntry("Lillie's Determination", 4),
    DeckEntry("Boss's Orders", 3),
    DeckEntry("Cyrano", 2),
    DeckEntry("Black Belt's Training", 1),
    DeckEntry("Ruffian", 1),
    DeckEntry("Buddy-Buddy Poffin", 4),
    DeckEntry(
        "Transformation Tome",
        4,
        replacement="Dusk Ball",
        note="Transformation Tome is not in this simulator card pool; Dusk Ball keeps Pokemon-search consistency.",
    ),
    DeckEntry("Ultra Ball", 3),
    DeckEntry("N's PP Up", 3),
    DeckEntry("Night Stretcher", 2),
    DeckEntry("Poke Pad", 1),
    DeckEntry(
        "Special Red Card",
        1,
        replacement="Meddling Memo",
        note="Special Red Card is not in this simulator card pool; Meddling Memo is the closest non-ACE hand disruption item.",
    ),
    DeckEntry("Secret Box", 1),
    DeckEntry("Binding Mochi", 2),
    DeckEntry("N's Castle", 2),
    DeckEntry("Darkness Energy", 7, replacement="Basic {D} Energy"),
]


def normalize(name: str) -> str:
    return (
        name.lower()
        .replace("’", "'")
        .replace("`", "'")
        .replace("´", "'")
        .replace("é", "e")
        .replace("pokémon", "pokemon")
        .replace("poké", "poke")
        .strip()
    )


def load_cards():
    sys.path.insert(0, str(ENGINE_DIR.resolve()))
    from cg.api import all_card_data

    return all_card_data()


def resolve_name(cards, name: str):
    target = normalize(name)
    exact = [card for card in cards if normalize(card.name) == target]
    if exact:
        return exact, []
    contains = [card for card in cards if target in normalize(card.name)]
    return [], contains


def main() -> None:
    cards = load_cards()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    deck: list[int] = []
    resolved_rows = []
    issue_lines = ["# Zoroark Deck Resolution Issues", ""]

    for entry in DECK_LIST:
        requested_name = entry.name
        exact, candidates = resolve_name(cards, requested_name)
        used_name = requested_name
        issue = ""

        if len(exact) != 1:
            if entry.replacement:
                repl_exact, repl_candidates = resolve_name(cards, entry.replacement)
                if len(repl_exact) != 1:
                    issue = (
                        f"Replacement failed for `{requested_name}` -> `{entry.replacement}`. "
                        f"Candidates: {[c.name for c in repl_candidates[:10]]}"
                    )
                    issue_lines.append(f"- {issue}")
                    continue
                exact = repl_exact
                used_name = entry.replacement
                issue = f"`{requested_name}` not found; used `{used_name}`. {entry.note}"
                issue_lines.append(f"- {issue}")
            elif len(exact) == 0:
                issue = f"`{requested_name}` not found. Candidates: {[c.name for c in candidates[:10]]}"
                issue_lines.append(f"- {issue}")
                continue
            else:
                issue = f"`{requested_name}` is ambiguous: {[c.name for c in exact]}"
                issue_lines.append(f"- {issue}")
                continue

        card = exact[0]
        deck.extend([card.cardId] * entry.count)
        resolved_rows.append(
            {
                "requested_name": requested_name,
                "used_name": card.name,
                "card_id": card.cardId,
                "count": entry.count,
                "issue": issue,
            }
        )

    if len(deck) != 60:
        issue_lines.append("")
        issue_lines.append(f"- Generated deck has {len(deck)} cards, expected 60. deck.csv was not written.")
    else:
        (OUT_DIR / "deck.csv").write_text("\n".join(str(card_id) for card_id in deck) + "\n", encoding="utf-8")

    with (LOG_DIR / "zoroark_deck_resolved.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["requested_name", "used_name", "card_id", "count", "issue"])
        writer.writeheader()
        writer.writerows(resolved_rows)

    if len(issue_lines) == 2:
        issue_lines.append("- No unresolved cards.")
    (LOG_DIR / "zoroark_deck_issues.md").write_text("\n".join(issue_lines) + "\n", encoding="utf-8")

    print(f"resolved entries: {len(resolved_rows)}")
    print(f"deck cards: {len(deck)}")
    print(f"wrote: {OUT_DIR / 'deck.csv'}" if len(deck) == 60 else "deck.csv not written")
    print(f"wrote: {LOG_DIR / 'zoroark_deck_resolved.csv'}")
    print(f"wrote: {LOG_DIR / 'zoroark_deck_issues.md'}")


if __name__ == "__main__":
    main()
