from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from ptcg_common import DEFAULT_ENGINE_DIR, ensure_engine_on_path, write_csv


ARCHALUDON_LINE = {169, 190, 840}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text())


def card_id(card: dict[str, Any] | None) -> int | None:
    if not card:
        return None
    value = card.get("id", card.get("cardId"))
    return value if isinstance(value, int) else None


def card_name(card: dict[str, Any] | None, names: dict[int, str]) -> str:
    cid = card_id(card)
    if cid is None:
        return ""
    name = card.get("name") if card else ""
    return str(name or names.get(cid, "") or cid)


def card_label(card: dict[str, Any] | None, names: dict[int, str]) -> str:
    cid = card_id(card)
    if cid is None:
        return ""
    return f"{cid}:{card_name(card, names)}"


def zone_cards(player: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [card for card in (player.get(key) or []) if isinstance(card, dict)]


def active_card(player: dict[str, Any]) -> dict[str, Any] | None:
    active = zone_cards(player, "active")
    return active[0] if active else None


def bench_summary(player: dict[str, Any], names: dict[int, str]) -> str:
    counts = Counter(card_label(card, names) for card in zone_cards(player, "bench"))
    return "; ".join(f"{label} x{count}" for label, count in counts.most_common())


def energy_count(card: dict[str, Any] | None) -> int:
    if not card:
        return 0
    return len(card.get("energyCards") or card.get("energies") or [])


def tool_count(card: dict[str, Any] | None) -> int:
    if not card:
        return 0
    return len(card.get("tools") or [])


def hp(card: dict[str, Any] | None) -> str:
    if not card:
        return ""
    return str(card.get("hp", ""))


def line_count(player: dict[str, Any]) -> int:
    ids = [card_id(card) for card in zone_cards(player, "active") + zone_cards(player, "bench")]
    return sum(1 for cid in ids if cid in ARCHALUDON_LINE)


def last_target_entries(doc: dict[str, Any], target_index: int) -> tuple[dict[str, Any] | None, dict[str, Any] | None, int, int]:
    last_entry = None
    last_select = None
    last_step_index = -1
    last_select_step_index = -1
    for step_index, pair in enumerate(doc.get("steps") or []):
        if target_index >= len(pair or []):
            continue
        entry = pair[target_index]
        if not isinstance(entry, dict):
            continue
        if entry.get("observation"):
            last_entry = entry
            last_step_index = step_index
            if (entry.get("observation") or {}).get("select"):
                last_select = entry
                last_select_step_index = step_index
    return last_entry, last_select, last_step_index, last_select_step_index


def target_index(doc: dict[str, Any], target_team: str) -> int | None:
    teams = (doc.get("info") or {}).get("TeamNames") or []
    try:
        return teams.index(target_team)
    except ValueError:
        return None


def initial_decks_by_episode(decks_csv: Path, target_team: str) -> dict[str, dict[str, str]]:
    rows = read_csv(decks_csv)
    by_episode: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("team") == target_team:
            continue
        by_episode.setdefault(str(row.get("episode_id")), row)
    return by_episode


def endstate_row(
    episode: dict[str, str],
    replay_path: Path,
    deck_lookup: dict[str, dict[str, str]],
    target_team: str,
    names: dict[int, str],
) -> dict[str, Any] | None:
    doc = read_json(replay_path)
    ti = target_index(doc, target_team)
    if ti is None:
        return None
    oi = 1 - ti
    last_entry, last_select, last_step, last_select_step = last_target_entries(doc, ti)
    if not last_entry:
        return None

    current = ((last_entry.get("observation") or {}).get("current") or {})
    players = current.get("players") or []
    if len(players) <= max(ti, oi):
        return None
    mine = players[ti]
    opp = players[oi]
    my_active = active_card(mine)
    opp_active = active_card(opp)
    my_bench = zone_cards(mine, "bench")
    opp_bench = zone_cards(opp, "bench")
    my_line_count = line_count(mine)

    select_obs = (last_select.get("observation") if last_select else {}) or {}
    select = select_obs.get("select") or {}
    select_current = select_obs.get("current") or {}
    select_players = select_current.get("players") or []
    select_mine = select_players[ti] if len(select_players) > ti else {}
    select_hand = zone_cards(select_mine, "hand")

    my_active_id = card_id(my_active)
    pattern_bits = []
    if not my_active:
        pattern_bits.append("no_active")
    if not my_bench:
        pattern_bits.append("empty_bench")
    if my_line_count <= 1:
        pattern_bits.append("thin_archaludon_line")
    if my_active_id in ARCHALUDON_LINE and str(hp(my_active)).isdigit() and int(hp(my_active)) <= 80:
        pattern_bits.append("low_hp_line_active")
    if len(opp_bench) >= 4:
        pattern_bits.append("opp_wide_board")
    if not pattern_bits:
        pattern_bits.append("other")

    deck_row = deck_lookup.get(str(episode.get("episode_id")), {})
    return {
        "episode_id": episode.get("episode_id", ""),
        "create_time": episode.get("create_time", ""),
        "opponent_team": episode.get("opponent_team", ""),
        "opponent_submission_id": episode.get("opponent_submission_id", ""),
        "opponent_initial_score": episode.get("opponent_initial_score", ""),
        "target_initial_score": episode.get("target_initial_score", ""),
        "target_updated_score": episode.get("target_updated_score", ""),
        "opponent_archetype": deck_row.get("archetype", ""),
        "last_step": last_step,
        "last_select_step": last_select_step,
        "turn": current.get("turn", ""),
        "my_deck": mine.get("deckCount", ""),
        "my_hand": mine.get("handCount", ""),
        "my_prizes": len(mine.get("prize") or []),
        "my_active": card_label(my_active, names),
        "my_active_hp": hp(my_active),
        "my_active_energy": energy_count(my_active),
        "my_active_tools": tool_count(my_active),
        "my_bench_count": len(my_bench),
        "my_bench": bench_summary(mine, names),
        "my_archaludon_line_count": my_line_count,
        "opp_deck": opp.get("deckCount", ""),
        "opp_hand": opp.get("handCount", ""),
        "opp_prizes": len(opp.get("prize") or []),
        "opp_active": card_label(opp_active, names),
        "opp_active_hp": hp(opp_active),
        "opp_active_energy": energy_count(opp_active),
        "opp_bench_count": len(opp_bench),
        "opp_bench": bench_summary(opp, names),
        "last_select_context": select.get("context", ""),
        "last_action": " ".join(str(v) for v in (last_select or {}).get("action") or []),
        "last_hand_ids": " ".join(str(card_id(card) or "") for card in select_hand),
        "pattern": ";".join(pattern_bits),
        "replay": str(replay_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize end-state boards for Kaggle public losses.")
    parser.add_argument("--episodes-csv", type=Path, required=True)
    parser.add_argument("--decks-csv", type=Path, required=True)
    parser.add_argument("--replay-dir", type=Path, required=True)
    parser.add_argument("--target-team", default="rurumi")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    args = parser.parse_args()

    ensure_engine_on_path(args.engine_dir)
    from cg.api import all_card_data

    names = {card.cardId: card.name for card in all_card_data()}
    deck_lookup = initial_decks_by_episode(args.decks_csv, args.target_team)
    rows: list[dict[str, Any]] = []

    for episode in read_csv(args.episodes_csv):
        if episode.get("type") != "EPISODE_TYPE_PUBLIC":
            continue
        if episode.get("target_reward") != "-1":
            continue
        episode_id = episode.get("episode_id", "")
        replay = args.replay_dir / f"episode_{episode_id}_replay.json"
        if not replay.exists():
            continue
        row = endstate_row(episode, replay, deck_lookup, args.target_team, names)
        if row:
            rows.append(row)

    fieldnames = [
        "episode_id",
        "create_time",
        "opponent_team",
        "opponent_submission_id",
        "opponent_initial_score",
        "target_initial_score",
        "target_updated_score",
        "opponent_archetype",
        "last_step",
        "last_select_step",
        "turn",
        "my_deck",
        "my_hand",
        "my_prizes",
        "my_active",
        "my_active_hp",
        "my_active_energy",
        "my_active_tools",
        "my_bench_count",
        "my_bench",
        "my_archaludon_line_count",
        "opp_deck",
        "opp_hand",
        "opp_prizes",
        "opp_active",
        "opp_active_hp",
        "opp_active_energy",
        "opp_bench_count",
        "opp_bench",
        "last_select_context",
        "last_action",
        "last_hand_ids",
        "pattern",
        "replay",
    ]
    write_csv(args.out, rows, fieldnames)
    print(json.dumps({"rows": len(rows), "out": str(args.out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
