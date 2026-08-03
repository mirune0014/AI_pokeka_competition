"""Extract Majkel1337 public-board policy evidence from a fixed replay snapshot.

The script is descriptive and read-only with respect to Kaggle.
It pairs the next replay record's action with the previous record's observation,
never counts cumulative visualizer logs, and writes reproducible CSV evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from analyze_top_band_episode_history import (
    as_int,
    card_from_state,
    classify_deck,
    deck_hash,
    find_first_player,
    is_main_prompt,
    items,
    own_turn_number,
    resolve_option,
    valid_decision,
)
from extract_episode_decks import initial_decks
from ptcg_common import DEFAULT_ENGINE_DIR, ensure_engine_on_path


TARGET_TEAM = "Majkel1337"
VALIDATION_EPISODE_ID = 89522018

CARD_NAMES = {
    6: "Basic Fighting Energy",
    673: "Makuhita",
    674: "Hariyama",
    675: "Lunatone",
    676: "Solrock",
    677: "Riolu",
    678: "Mega Lucario ex",
    1121: "Ultra Ball",
    1123: "Switch",
    1141: "Premium Power Pro",
    1142: "Fighting Gong",
    1152: "Poke Pad",
    1159: "Hero's Cape",
    1182: "Boss's Orders",
    1213: "Judge",
    1227: "Lillie's Determination",
    1229: "Wally's Compassion",
}

ATTACK_NAMES = {
    976: "Corkscrew Punch",
    977: "Confront",
    978: "Wild Press",
    979: "Power Gem",
    980: "Cosmic Beam",
    981: "Accelerating Stab",
    982: "Aura Jab",
    983: "Mega Brave",
}

ACTION_LABELS = {
    ("ATTACK", 982): "AURA_JAB",
    ("ATTACK", 983): "MEGA_BRAVE",
    ("ATTACK", 980): "COSMIC_BEAM",
    ("ATTACK", 978): "WILD_PRESS",
    ("PLAY", 1141): "PREMIUM_POWER_PRO",
    ("PLAY", 1182): "BOSS_ORDERS",
    ("PLAY", 1229): "WALLY_COMPASSION",
    ("PLAY", 1213): "JUDGE",
    ("PLAY", 1227): "LILLIE_DETERMINATION",
    ("PLAY", 1123): "SWITCH",
    ("ATTACH", 1159): "HERO_CAPE",
    ("EVOLVE", 678): "EVOLVE_MEGA_LUCARIO",
    ("EVOLVE", 674): "EVOLVE_HARIYAMA",
    ("ABILITY", 675): "LUNAR_CYCLE",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def median(values: Iterable[int | float | None]) -> float | str:
    clean = [float(value) for value in values if value is not None and value != ""]
    return statistics.median(clean) if clean else ""


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        return math.nan, math.nan
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def refined_archetype(deck: Sequence[int], cards: Mapping[int, Any]) -> dict[str, str]:
    ids = set(deck)
    refinements: list[tuple[set[int], str, str]] = [
        ({848, 849, 860, 861}, "mega_lopunny_froslass", "REFINED_MEGA_LOPUNNY_FROSLASS"),
        ({666, 1030, 1031}, "mega_starmie_cinderace", "REFINED_MEGA_STARMIE_CINDERACE"),
        ({63, 96}, "raging_bolt_ogerpon", "REFINED_RAGING_BOLT_OGERPON"),
        ({96, 150}, "hydrapple_ogerpon", "REFINED_HYDRAPPLE_OGERPON"),
        ({96, 650, 652, 708, 710, 756}, "mega_kangaskhan_venusaur_meganium", "REFINED_KANGASKHAN_VENUSAUR_MEGANIUM"),
        ({344, 345, 756}, "mega_kangaskhan_crustle", "REFINED_KANGASKHAN_CRUSTLE"),
        ({108, 272, 756, 1071}, "mega_kangaskhan_toolbox", "REFINED_KANGASKHAN_TOOLBOX"),
        ({66, 305, 848, 849}, "mega_lopunny_dudunsparce", "REFINED_MEGA_LOPUNNY_DUDUNSPARCE"),
        ({90, 93, 1245}, "festival_lead_dipplin", "REFINED_FESTIVAL_LEAD"),
        ({157, 158, 317, 330}, "sylveon_drednaw", "REFINED_SYLVEON_DREDNAW"),
        ({144, 162, 163}, "kyurem_slowking_toolbox", "REFINED_KYUREM_SLOWKING"),
        ({184, 506, 858}, "cubchoo_psyduck_control", "REFINED_CUBCHOO_PSYDUCK"),
    ]
    for required, name, rule_id in refinements:
        if required.issubset(ids):
            return {
                "archetype": name,
                "archetype_classification_basis": "FULL_DECK_REFINED",
                "classification_rule_id": rule_id,
                "classification_evidence_card_ids": " ".join(map(str, sorted(required))),
                "classification_notes": "Refined from a complete 60-card conjunction.",
            }
    pokemon_ids = {
        card_id for card_id in ids
        if card_id in cards and as_int(getattr(cards[card_id], "cardType", None)) == 0
    }
    if pokemon_ids == {96}:
        return {
            "archetype": "pure_teal_ogerpon",
            "archetype_classification_basis": "FULL_DECK_REFINED",
            "classification_rule_id": "REFINED_PURE_TEAL_OGERPON",
            "classification_evidence_card_ids": "96",
            "classification_notes": "The complete deck's only Pokemon card ID is Teal Mask Ogerpon ex.",
        }
    base = classify_deck(deck)
    return base


def prize_value(card_id: int | None, cards: Mapping[int, Any]) -> int | None:
    card = cards.get(card_id)
    if card is None:
        return None
    if bool(getattr(card, "megaEx", False)):
        return 3
    if bool(getattr(card, "ex", False)):
        return 2
    return 1


def energy_count(pokemon: Mapping[str, Any] | None) -> int:
    if not isinstance(pokemon, Mapping):
        return 0
    cards = items(pokemon.get("energyCards"))
    return len(cards) if cards else len(items(pokemon.get("energies")))


def attack_payable(pokemon: Mapping[str, Any], attack: Any) -> bool:
    available = list(pokemon.get("energies") or [])
    required = list(getattr(attack, "energies", None) or [])
    for energy_type in [value for value in required if value != 0]:
        if energy_type in available:
            available.remove(energy_type)
        elif 10 in available:
            available.remove(10)
        else:
            return False
    return len(available) >= sum(1 for value in required if value == 0)


def pokemon_ready(pokemon: Mapping[str, Any] | None, cards: Mapping[int, Any], attacks: Mapping[int, Any]) -> bool:
    if not isinstance(pokemon, Mapping):
        return False
    card = cards.get(as_int(pokemon.get("id")))
    if card is None:
        return False
    return any(
        attack_payable(pokemon, attacks[attack_id])
        for attack_id in list(getattr(card, "attacks", None) or [])
        if attack_id in attacks
    )


def pokemon_features(pokemon: Mapping[str, Any] | None, cards: Mapping[int, Any], attacks: Mapping[int, Any]) -> dict[str, Any]:
    if not isinstance(pokemon, Mapping):
        return {
            "id": "",
            "name": "",
            "serial": "",
            "hp": "",
            "max_hp": "",
            "damage": "",
            "energy": "",
            "prize": "",
            "ready": "",
            "rule_box": "",
        }
    card_id = as_int(pokemon.get("id"))
    card = cards.get(card_id)
    hp = as_int(pokemon.get("hp"))
    max_hp = as_int(pokemon.get("maxHp"), as_int(getattr(card, "hp", None)))
    return {
        "id": card_id if card_id is not None else "",
        "name": getattr(card, "name", CARD_NAMES.get(card_id, str(card_id or ""))),
        "serial": as_int(pokemon.get("serial"), ""),
        "hp": hp if hp is not None else "",
        "max_hp": max_hp if max_hp is not None else "",
        "damage": max(0, max_hp - hp) if hp is not None and max_hp is not None else "",
        "energy": energy_count(pokemon),
        "prize": prize_value(card_id, cards) or "",
        "ready": pokemon_ready(pokemon, cards, attacks),
        "rule_box": bool(card and (getattr(card, "ex", False) or getattr(card, "megaEx", False))),
    }


def hp_bucket(hp: Any) -> str:
    value = as_int(hp)
    if value is None:
        return "UNKNOWN"
    if value <= 70:
        return "001_070"
    if value <= 130:
        return "071_130"
    if value <= 190:
        return "131_190"
    if value <= 270:
        return "191_270"
    return "271_PLUS"


def energy_bucket(value: Any) -> str:
    count = as_int(value)
    if count is None:
        return "UNKNOWN"
    return str(count) if count <= 2 else "3_PLUS"


def compact_board(pokemon: Sequence[Mapping[str, Any]], cards: Mapping[int, Any], attacks: Mapping[int, Any]) -> str:
    payload = []
    for item in pokemon:
        feature = pokemon_features(item, cards, attacks)
        payload.append({
            "id": feature["id"],
            "name": feature["name"],
            "serial": feature["serial"],
            "hp": feature["hp"],
            "max_hp": feature["max_hp"],
            "energy": feature["energy"],
            "prize": feature["prize"],
            "ready": feature["ready"],
        })
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def board_features(current: Mapping[str, Any], seat: int, cards: Mapping[int, Any], attacks: Mapping[int, Any]) -> dict[str, Any]:
    players = items(current.get("players"))
    own = players[seat] if seat < len(players) and isinstance(players[seat], Mapping) else {}
    opponent_seat = 1 - seat
    opponent = players[opponent_seat] if opponent_seat < len(players) and isinstance(players[opponent_seat], Mapping) else {}
    own_active_state = items(own.get("active"))
    opponent_active_state = items(opponent.get("active"))
    own_active = pokemon_features(own_active_state[0] if own_active_state else None, cards, attacks)
    opponent_active = pokemon_features(opponent_active_state[0] if opponent_active_state else None, cards, attacks)
    own_bench_state = [item for item in items(own.get("bench")) if isinstance(item, Mapping)]
    opponent_bench_state = [item for item in items(opponent.get("bench")) if isinstance(item, Mapping)]
    opponent_bench = [pokemon_features(item, cards, attacks) for item in opponent_bench_state]
    own_bench = [pokemon_features(item, cards, attacks) for item in own_bench_state]
    stadium_ids = [as_int(item.get("id")) for item in items(current.get("stadium")) if isinstance(item, Mapping)]
    return {
        "own_prize_remaining": len(items(own.get("prize"))),
        "opponent_prize_remaining": len(items(opponent.get("prize"))),
        "own_hand_count": as_int(own.get("handCount"), len(items(own.get("hand")))) or 0,
        "opponent_hand_count": as_int(opponent.get("handCount"), len(items(opponent.get("hand")))) or 0,
        "own_deck_count": as_int(own.get("deckCount"), ""),
        "opponent_deck_count": as_int(opponent.get("deckCount"), ""),
        "own_active_id": own_active["id"],
        "own_active_name": own_active["name"],
        "own_active_serial": own_active["serial"],
        "own_active_hp": own_active["hp"],
        "own_active_max_hp": own_active["max_hp"],
        "own_active_damage": own_active["damage"],
        "own_active_energy": own_active["energy"],
        "own_active_prize": own_active["prize"],
        "own_active_ready": own_active["ready"],
        "opponent_active_id": opponent_active["id"],
        "opponent_active_name": opponent_active["name"],
        "opponent_active_serial": opponent_active["serial"],
        "opponent_active_hp": opponent_active["hp"],
        "opponent_active_max_hp": opponent_active["max_hp"],
        "opponent_active_damage": opponent_active["damage"],
        "opponent_active_energy": opponent_active["energy"],
        "opponent_active_prize": opponent_active["prize"],
        "opponent_active_ready": opponent_active["ready"],
        "opponent_active_hp_bucket": hp_bucket(opponent_active["hp"]),
        "opponent_active_energy_bucket": energy_bucket(opponent_active["energy"]),
        "opponent_bench_count": len(opponent_bench),
        "opponent_bench_max_prize": max((as_int(row["prize"], 0) or 0 for row in opponent_bench), default=0),
        "opponent_bench_min_hp": min((as_int(row["hp"]) for row in opponent_bench if as_int(row["hp"]) is not None), default=""),
        "opponent_bench_max_energy": max((as_int(row["energy"], 0) or 0 for row in opponent_bench), default=0),
        "opponent_bench_ready_count": sum(bool(row["ready"]) for row in opponent_bench),
        "opponent_bench_rule_box_count": sum(bool(row["rule_box"]) for row in opponent_bench),
        "own_bench_count": len(own_bench),
        "own_bench_ready_count": sum(bool(row["ready"]) for row in own_bench),
        "own_bench_max_prize": max((as_int(row["prize"], 0) or 0 for row in own_bench), default=0),
        "opponent_bench_json": compact_board(opponent_bench_state, cards, attacks),
        "own_bench_json": compact_board(own_bench_state, cards, attacks),
        "stadium_ids": " ".join(str(value) for value in stadium_ids if value is not None),
    }


def option_source_entity(observation: Mapping[str, Any], option: Mapping[str, Any]) -> Mapping[str, Any] | None:
    current = observation.get("current") or {}
    select = observation.get("select") or {}
    actor = as_int(current.get("yourIndex"), 0) or 0
    option_type = as_int(option.get("type"), -1)
    area = as_int(option.get("area"))
    if option_type == 7 and area is None:
        area = 2
    owner = as_int(option.get("playerIndex"), actor)
    index = as_int(option.get("index"))
    if area == 1:
        deck = items(select.get("deck"))
        return deck[index] if index is not None and 0 <= index < len(deck) and isinstance(deck[index], Mapping) else None
    if area == 12:
        looking = items(current.get("looking"))
        return looking[index] if index is not None and 0 <= index < len(looking) and isinstance(looking[index], Mapping) else None
    return card_from_state(current, owner if owner is not None else actor, area, index)


def option_target_entity(observation: Mapping[str, Any], option: Mapping[str, Any]) -> Mapping[str, Any] | None:
    current = observation.get("current") or {}
    actor = as_int(current.get("yourIndex"), 0) or 0
    area = as_int(option.get("inPlayArea", option.get("targetArea")))
    owner = as_int(option.get("inPlayPlayerIndex", option.get("targetPlayerIndex")), actor)
    index = as_int(option.get("inPlayIndex", option.get("targetIndex")))
    return card_from_state(current, owner if owner is not None else actor, area, index)


def main_action_kind(resolved: Mapping[str, Any], card_types: Mapping[int, int]) -> str:
    option_type = as_int(resolved.get("option_type"), -1)
    source_id = as_int(resolved.get("source_card_id"))
    if option_type == 7:
        return "PLAY"
    if option_type == 8:
        return "ATTACH"
    if option_type == 9:
        return "EVOLVE"
    if option_type == 10:
        return "ABILITY"
    if option_type == 11:
        return "DISCARD"
    if option_type == 12:
        return "RETREAT"
    if option_type == 13:
        return "ATTACK"
    if option_type == 14:
        return "PASS"
    return f"OPTION_{option_type}_{card_types.get(source_id, -1)}"


def simple_attack_damage(
    attack_id: int,
    source_id: int | None,
    target_id: int | None,
    target_hp: int | None,
    ppp_count: int,
    stadium_ids: set[int],
    cards: Mapping[int, Any],
    attacks: Mapping[int, Any],
) -> tuple[int | None, bool | str, str]:
    attack = attacks.get(attack_id)
    source = cards.get(source_id)
    target = cards.get(target_id)
    if attack is None or source is None or target is None:
        return None, "", "MISSING_CARD_OR_ATTACK"
    damage = as_int(getattr(attack, "damage", None))
    if damage is None:
        return None, "", "NON_NUMERIC_DAMAGE"
    if as_int(getattr(source, "energyType", None)) == 6:
        damage += 30 * ppp_count
    notes: list[str] = []
    if target_id == 345 and bool(getattr(source, "ex", False) or getattr(source, "megaEx", False)):
        damage = 0
        notes.append("CRUSTLE_EX_PREVENTION")
    if attack_id != 980 and damage > 0:
        source_type = as_int(getattr(source, "energyType", None))
        if source_type is not None and as_int(getattr(target, "weakness", None)) == source_type:
            damage *= 2
            notes.append("WEAKNESS_X2")
        if source_type is not None and as_int(getattr(target, "resistance", None)) == source_type:
            damage = max(0, damage - 30)
            notes.append("RESISTANCE_MINUS_30")
    if 1244 in stadium_ids and as_int(getattr(target, "energyType", None)) == 8:
        damage = max(0, damage - 30)
        notes.append("FULL_METAL_LAB_MINUS_30")
    ko = damage >= target_hp if target_hp is not None else ""
    return damage, ko, "|".join(notes) if notes else "PRINTED_PLUS_VISIBLE_MODIFIERS"


def best_simple_damage(
    source_state: Mapping[str, Any] | None,
    target_id: int | None,
    target_hp: int | None,
    ppp_count: int,
    stadium_ids: set[int],
    cards: Mapping[int, Any],
    attacks: Mapping[int, Any],
) -> int | None:
    if not isinstance(source_state, Mapping):
        return None
    source_id = as_int(source_state.get("id"))
    card = cards.get(source_id)
    if card is None:
        return None
    values = []
    for attack_id in list(getattr(card, "attacks", None) or []):
        attack = attacks.get(attack_id)
        if attack is None or not attack_payable(source_state, attack):
            continue
        damage, _, _ = simple_attack_damage(
            attack_id, source_id, target_id, target_hp, ppp_count, stadium_ids, cards, attacks
        )
        if damage is not None:
            values.append(damage)
    return max(values) if values else None


def pokemon_deck_signature(deck: Sequence[int], cards: Mapping[int, Any]) -> str:
    counts = Counter(deck)
    rows = []
    for card_id in sorted(counts):
        card = cards.get(card_id)
        if card is not None and as_int(getattr(card, "cardType", None)) == 0:
            rows.append(f"{getattr(card, 'name', card_id)}({card_id})x{counts[card_id]}")
    return "; ".join(rows)


def summarize_matchups(games: Sequence[Mapping[str, Any]], main_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    games_by_arch: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    actions_by_arch: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in games:
        games_by_arch[str(row["opponent_archetype"])].append(row)
    for row in main_rows:
        actions_by_arch[str(row["opponent_archetype"])].append(row)
    output = []
    for archetype, rows in sorted(games_by_arch.items(), key=lambda item: (-len(item[1]), item[0])):
        actions = actions_by_arch.get(archetype, [])
        wins = sum(row["result"] == "WIN" for row in rows)
        low, high = wilson_interval(wins, len(rows))
        first_attacks = [row for row in rows if row.get("first_attack_id") not in (None, "")]
        attack_rows = [row for row in actions if row["action_kind"] == "ATTACK"]
        episode_actions: dict[str, set[str]] = defaultdict(set)
        for row in actions:
            label = str(row.get("action_label") or "")
            if label:
                episode_actions[str(row["episode_id"])].add(label)
        output.append({
            "opponent_archetype": archetype,
            "games": len(rows),
            "wins": wins,
            "losses": len(rows) - wins,
            "descriptive_win_rate": wins / len(rows),
            "win_rate_wilson_low": low,
            "win_rate_wilson_high": high,
            "target_seat0_games": sum(as_int(row["target_seat"]) == 0 for row in rows),
            "target_seat1_games": sum(as_int(row["target_seat"]) == 1 for row in rows),
            "went_first_games": sum(row["starting_order"] == "FIRST" for row in rows),
            "first_attack_games": len(first_attacks),
            "no_attack_games": len(rows) - len(first_attacks),
            "median_first_attack_own_turn": median(row.get("first_attack_own_turn") for row in first_attacks),
            "first_attack_aura": sum(as_int(row.get("first_attack_id")) == 982 for row in first_attacks),
            "first_attack_cosmic": sum(as_int(row.get("first_attack_id")) == 980 for row in first_attacks),
            "first_attack_mega_brave": sum(as_int(row.get("first_attack_id")) == 983 for row in first_attacks),
            "attack_events": len(attack_rows),
            "aura_events": sum(as_int(row.get("action_attack_id")) == 982 for row in attack_rows),
            "brave_events": sum(as_int(row.get("action_attack_id")) == 983 for row in attack_rows),
            "cosmic_events": sum(as_int(row.get("action_attack_id")) == 980 for row in attack_rows),
            "wild_press_events": sum(as_int(row.get("action_attack_id")) == 978 for row in attack_rows),
            "games_using_ppp": sum("PREMIUM_POWER_PRO" in episode_actions[str(row["episode_id"])] for row in rows),
            "games_using_wally": sum("WALLY_COMPASSION" in episode_actions[str(row["episode_id"])] for row in rows),
            "games_using_boss": sum("BOSS_ORDERS" in episode_actions[str(row["episode_id"])] for row in rows),
            "games_using_judge": sum("JUDGE" in episode_actions[str(row["episode_id"])] for row in rows),
            "games_using_lillie": sum("LILLIE_DETERMINATION" in episode_actions[str(row["episode_id"])] for row in rows),
            "games_using_switch": sum("SWITCH" in episode_actions[str(row["episode_id"])] for row in rows),
            "games_using_cape": sum("HERO_CAPE" in episode_actions[str(row["episode_id"])] for row in rows),
        })
    return output


def summarize_action_rates(games: Sequence[Mapping[str, Any]], main_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    game_count = Counter(str(row["opponent_archetype"]) for row in games)
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in main_rows:
        label = str(row.get("action_label") or "")
        if label:
            grouped[(str(row["opponent_archetype"]), label)].append(row)
    output = []
    for (archetype, label), rows in sorted(grouped.items()):
        episodes = {str(row["episode_id"]) for row in rows}
        total_games = game_count[archetype]
        low, high = wilson_interval(len(episodes), total_games)
        output.append({
            "opponent_archetype": archetype,
            "action_label": label,
            "games": total_games,
            "events": len(rows),
            "games_with_action": len(episodes),
            "game_use_rate": len(episodes) / total_games,
            "game_use_wilson_low": low,
            "game_use_wilson_high": high,
            "events_per_game": len(rows) / total_games,
        })
    return output


def summarize_attack_targets(main_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    attacks = [row for row in main_rows if row["action_kind"] == "ATTACK"]
    totals = Counter(str(row["opponent_archetype"]) for row in attacks)
    grouped: dict[tuple[str, int, str, int, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in attacks:
        key = (
            str(row["opponent_archetype"]),
            as_int(row.get("opponent_active_id"), -1) or -1,
            str(row.get("opponent_active_name") or ""),
            as_int(row.get("action_attack_id"), -1) or -1,
            str(row.get("action_attack_name") or ""),
        )
        grouped[key].append(row)
    output = []
    for key, rows in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        archetype, target_id, target_name, attack_id, attack_name = key
        output.append({
            "opponent_archetype": archetype,
            "opponent_active_id": target_id,
            "opponent_active_name": target_name,
            "attack_id": attack_id,
            "attack_name": attack_name,
            "events": len(rows),
            "share_of_matchup_attacks": len(rows) / totals[archetype],
            "median_target_hp": median(row.get("opponent_active_hp") for row in rows),
            "target_one_prize_events": sum(as_int(row.get("opponent_active_prize")) == 1 for row in rows),
            "target_two_prize_events": sum(as_int(row.get("opponent_active_prize")) == 2 for row in rows),
            "target_three_prize_events": sum(as_int(row.get("opponent_active_prize")) == 3 for row in rows),
            "simple_ko_events": sum(row.get("selected_attack_simple_ko") is True for row in rows),
            "finisher_opportunities": sum(row.get("selected_attack_finisher") is True for row in rows),
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-dir", type=Path, required=True)
    parser.add_argument("--episodes-csv", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--target-team", default=TARGET_TEAM)
    parser.add_argument("--validation-episode-id", type=int, default=VALIDATION_EPISODE_ID)
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    parser.add_argument("--max-files", type=int)
    args = parser.parse_args()

    ensure_engine_on_path(args.engine_dir)
    from cg.api import all_attack, all_card_data

    cards = {card.cardId: card for card in all_card_data()}
    attacks = {attack.attackId: attack for attack in all_attack()}
    card_types = {card_id: as_int(getattr(card, "cardType", None), -1) for card_id, card in cards.items()}
    card_names = {card_id: getattr(card, "name", str(card_id)) for card_id, card in cards.items()}
    attack_names = {attack_id: getattr(attack, "name", str(attack_id)) for attack_id, attack in attacks.items()}

    episode_rows = list(csv.DictReader(args.episodes_csv.open(newline="", encoding="utf-8-sig")))
    public_ids = {
        int(row["episode_id"])
        for row in episode_rows
        if row.get("type") == "EPISODE_TYPE_PUBLIC" and int(row["episode_id"]) != args.validation_episode_id
    }
    replay_paths = [
        path for path in sorted(args.replay_dir.glob("episode_*_replay.json"))
        if int(path.stem.split("_")[1]) in public_ids
    ]
    if args.max_files is not None:
        replay_paths = replay_paths[: args.max_files]

    games: list[dict[str, Any]] = []
    main_rows: list[dict[str, Any]] = []
    effect_rows: list[dict[str, Any]] = []
    source_hashes: list[tuple[str, str]] = []

    for path in replay_paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        episode_id = as_int((document.get("info") or {}).get("EpisodeId"))
        teams = list((document.get("info") or {}).get("TeamNames") or [])
        if episode_id is None or args.target_team not in teams:
            continue
        seat = teams.index(args.target_team)
        opponent_seat = 1 - seat
        decks = initial_decks(document)
        if len(decks) != 2:
            raise ValueError(f"{path}: expected two initial decks")
        opponent_deck = decks[opponent_seat]
        classification = refined_archetype(opponent_deck, cards)
        opponent_hash = deck_hash(opponent_deck)
        first_player = find_first_player(document)
        rewards = list(document.get("rewards") or [])
        reward = as_int(rewards[seat]) if seat < len(rewards) else None
        base = {
            "episode_id": episode_id,
            "target_seat": seat,
            "opponent_team": teams[opponent_seat] if opponent_seat < len(teams) else "",
            "opponent_archetype": classification["archetype"],
            "opponent_deck_hash": opponent_hash,
            "opponent_deck_pokemon": pokemon_deck_signature(opponent_deck, cards),
            "classification_basis": classification["archetype_classification_basis"],
            "classification_rule_id": classification["classification_rule_id"],
            "reward": reward if reward is not None else "",
            "result": "WIN" if reward == 1 else "LOSS" if reward == -1 else "DRAW",
            "starting_order": "FIRST" if first_player == seat else "SECOND" if first_player in (0, 1) else "UNKNOWN",
        }
        steps = items(document.get("steps"))
        ppp_by_turn: Counter[int] = Counter()
        parent_by_turn: dict[int, dict[str, Any]] = {}
        has_attacked = False
        first_attack: dict[str, Any] | None = None

        for replay_step in range(max(0, len(steps) - 1)):
            current_group = items(steps[replay_step])
            next_group = items(steps[replay_step + 1])
            if seat >= len(current_group) or seat >= len(next_group):
                continue
            current_record = current_group[seat]
            next_record = next_group[seat]
            observation = current_record.get("observation") if isinstance(current_record, Mapping) else None
            action = next_record.get("action") if isinstance(next_record, Mapping) else None
            if not valid_decision(observation, action, seat, current_record.get("status")):
                continue
            current = observation.get("current") or {}
            select = observation.get("select") or {}
            options = items(select.get("option"))
            turn = as_int(current.get("turn"), 0) or 0
            own_turn = own_turn_number(turn, seat, first_player)
            board = board_features(current, seat, cards, attacks)
            ppp_before = ppp_by_turn[turn]
            resolved_options = [resolve_option(observation, option) for option in options]
            selected_pairs = [
                (options[index], resolve_option(observation, options[index]))
                for index in action
            ]
            if is_main_prompt(observation):
                legal_attack_ids = sorted({as_int(row.get("attack_id")) for row in resolved_options if as_int(row.get("attack_id")) is not None})
                legal_play_ids = sorted({
                    as_int(row.get("source_card_id"))
                    for row in resolved_options
                    if as_int(row.get("option_type")) == 7 and as_int(row.get("source_card_id")) is not None
                })
                for option, resolved in selected_pairs:
                    action_kind = main_action_kind(resolved, card_types)
                    source_id = as_int(resolved.get("source_card_id"))
                    attack_id = as_int(resolved.get("attack_id"))
                    target_id = as_int(resolved.get("target_card_id"))
                    target_entity = option_target_entity(observation, option)
                    target_feature = pokemon_features(target_entity, cards, attacks)
                    damage: int | None = None
                    simple_ko: bool | str = ""
                    damage_notes = ""
                    selected_finisher: bool | str = ""
                    if action_kind == "ATTACK" and attack_id is not None:
                        stadium_ids = {as_int(value) for value in str(board["stadium_ids"]).split() if str(value).strip()}
                        damage, simple_ko, damage_notes = simple_attack_damage(
                            attack_id,
                            as_int(board["own_active_id"]),
                            as_int(board["opponent_active_id"]),
                            as_int(board["opponent_active_hp"]),
                            ppp_before,
                            {value for value in stadium_ids if value is not None},
                            cards,
                            attacks,
                        )
                        target_prize = as_int(board["opponent_active_prize"])
                        own_prizes = as_int(board["own_prize_remaining"])
                        selected_finisher = bool(
                            simple_ko is True
                            and target_prize is not None
                            and own_prizes is not None
                            and target_prize >= own_prizes
                        )
                    action_label = ACTION_LABELS.get((action_kind, attack_id if action_kind == "ATTACK" else source_id), "")
                    row = {
                        **base,
                        "replay_step": replay_step,
                        "global_turn": turn,
                        "own_turn": own_turn if own_turn is not None else "",
                        "phase": "OPENING_BEFORE_FIRST_ATTACK" if not has_attacked else "POST_FIRST_ATTACK",
                        "action_kind": action_kind,
                        "action_label": action_label,
                        "action_card_id": source_id if source_id is not None else "",
                        "action_card_name": card_names.get(source_id, CARD_NAMES.get(source_id, "")),
                        "action_attack_id": attack_id if attack_id is not None else "",
                        "action_attack_name": attack_names.get(attack_id, ATTACK_NAMES.get(attack_id, "")),
                        "action_target_id": target_id if target_id is not None else "",
                        "action_target_name": target_feature["name"],
                        "legal_attack_ids": " ".join(str(value) for value in legal_attack_ids),
                        "legal_play_card_ids": " ".join(str(value) for value in legal_play_ids),
                        "legal_option_count": len(options),
                        "ppp_played_this_turn_before_action": ppp_before,
                        "selected_attack_simple_damage": damage if damage is not None else "",
                        "selected_attack_simple_ko": simple_ko,
                        "selected_attack_finisher": selected_finisher,
                        "selected_attack_damage_notes": damage_notes,
                        **board,
                    }
                    main_rows.append(row)
                    parent_by_turn[turn] = {
                        "action_kind": action_kind,
                        "card_id": source_id,
                        "attack_id": attack_id,
                        "step": replay_step,
                    }
                    if action_kind == "PLAY" and source_id == 1141:
                        ppp_by_turn[turn] += 1
                    if action_kind == "ATTACK":
                        has_attacked = True
                        if first_attack is None:
                            first_attack = row
            else:
                parent = parent_by_turn.get(turn, {})
                for option, resolved in selected_pairs:
                    source_entity = option_source_entity(observation, option)
                    target_entity = option_target_entity(observation, option)
                    source_feature = pokemon_features(source_entity, cards, attacks)
                    target_feature = pokemon_features(target_entity, cards, attacks)
                    selected_feature = source_feature if source_feature["id"] != "" else target_feature
                    effect_source_id = as_int(resolved.get("effect_source_id"))
                    context = as_int(resolved.get("selection_context"), -1)
                    source_relation = str(resolved.get("source_relation") or "")
                    choice_type = "EFFECT_CHOICE"
                    if context in (3, 4) and source_relation == "OPPONENT":
                        choice_type = "GUST_TARGET"
                    elif context == 17 and effect_source_id == 1229:
                        choice_type = "WALLY_HEAL_TARGET"
                    elif context == 21 and as_int(parent.get("attack_id")) == 982:
                        choice_type = "AURA_ATTACH_TARGET"
                    elif context == 7 and bool(resolved.get("select_deck_present")):
                        choice_type = "SEARCH_TARGET"
                    elif context == 8 and effect_source_id == 1121:
                        choice_type = "ULTRA_BALL_DISCARD"
                    legal_candidates = []
                    for candidate in options:
                        candidate_resolved = resolve_option(observation, candidate)
                        candidate_entity = option_source_entity(observation, candidate)
                        candidate_feature = pokemon_features(candidate_entity, cards, attacks)
                        if candidate_feature["id"] != "":
                            legal_candidates.append({
                                "id": candidate_feature["id"],
                                "name": candidate_feature["name"],
                                "serial": candidate_feature["serial"],
                                "hp": candidate_feature["hp"],
                                "max_hp": candidate_feature["max_hp"],
                                "damage": candidate_feature["damage"],
                                "energy": candidate_feature["energy"],
                                "prize": candidate_feature["prize"],
                                "ready": candidate_feature["ready"],
                                "relation": candidate_resolved.get("source_relation"),
                            })
                    stadium_ids = {as_int(value) for value in str(board["stadium_ids"]).split() if str(value).strip()}
                    own_players = items(current.get("players"))
                    own_state = own_players[seat] if seat < len(own_players) and isinstance(own_players[seat], Mapping) else {}
                    active_state = items(own_state.get("active"))
                    best_damage = best_simple_damage(
                        active_state[0] if active_state else None,
                        as_int(selected_feature["id"]),
                        as_int(selected_feature["hp"]),
                        ppp_before,
                        {value for value in stadium_ids if value is not None},
                        cards,
                        attacks,
                    )
                    selected_immediate_ko = bool(
                        best_damage is not None
                        and as_int(selected_feature["hp"]) is not None
                        and best_damage >= (as_int(selected_feature["hp"]) or 0)
                    )
                    selected_finisher = bool(
                        selected_immediate_ko
                        and as_int(selected_feature["prize"]) is not None
                        and as_int(board["own_prize_remaining"]) is not None
                        and (as_int(selected_feature["prize"]) or 0) >= (as_int(board["own_prize_remaining"]) or 0)
                    )
                    max_legal_prize = max((as_int(row.get("prize"), 0) or 0 for row in legal_candidates), default=0)
                    max_legal_damage = max((as_int(row.get("damage"), 0) or 0 for row in legal_candidates), default=0)
                    effect_rows.append({
                        **base,
                        "replay_step": replay_step,
                        "global_turn": turn,
                        "own_turn": own_turn if own_turn is not None else "",
                        "phase": "OPENING_BEFORE_FIRST_ATTACK" if not has_attacked else "POST_FIRST_ATTACK",
                        "choice_type": choice_type,
                        "selection_context": context,
                        "effect_source_id": effect_source_id if effect_source_id is not None else "",
                        "effect_source_name": card_names.get(effect_source_id, CARD_NAMES.get(effect_source_id, "")),
                        "parent_action_kind": parent.get("action_kind", ""),
                        "parent_card_id": parent.get("card_id", ""),
                        "parent_attack_id": parent.get("attack_id", ""),
                        "selected_source_relation": source_relation,
                        "selected_id": selected_feature["id"],
                        "selected_name": selected_feature["name"],
                        "selected_serial": selected_feature["serial"],
                        "selected_hp": selected_feature["hp"],
                        "selected_max_hp": selected_feature["max_hp"],
                        "selected_damage": selected_feature["damage"],
                        "selected_energy": selected_feature["energy"],
                        "selected_prize": selected_feature["prize"],
                        "selected_ready": selected_feature["ready"],
                        "legal_candidate_count": len(legal_candidates),
                        "legal_candidates_json": json.dumps(legal_candidates, ensure_ascii=False, separators=(",", ":")),
                        "selected_is_max_legal_prize": bool(selected_feature["prize"] != "" and (as_int(selected_feature["prize"]) or 0) == max_legal_prize),
                        "selected_is_max_legal_damage": bool(selected_feature["damage"] != "" and (as_int(selected_feature["damage"]) or 0) == max_legal_damage),
                        "best_simple_damage_to_selected": best_damage if best_damage is not None else "",
                        "selected_immediate_ko": selected_immediate_ko,
                        "selected_finisher": selected_finisher,
                        "ppp_played_this_turn_before_choice": ppp_before,
                        **board,
                    })

        games.append({
            **base,
            "first_attack_step": first_attack["replay_step"] if first_attack else "",
            "first_attack_global_turn": first_attack["global_turn"] if first_attack else "",
            "first_attack_own_turn": first_attack["own_turn"] if first_attack else "",
            "first_attack_id": first_attack["action_attack_id"] if first_attack else "",
            "first_attack_name": first_attack["action_attack_name"] if first_attack else "",
            "first_attack_opponent_active_id": first_attack["opponent_active_id"] if first_attack else "",
            "first_attack_opponent_active_name": first_attack["opponent_active_name"] if first_attack else "",
            "first_attack_opponent_active_hp": first_attack["opponent_active_hp"] if first_attack else "",
        })
        source_hashes.append((path.name, sha256_file(path)))

    expected = len(public_ids) if args.max_files is None else min(len(public_ids), args.max_files)
    if len(games) != expected:
        raise ValueError(f"expected {expected} public games, extracted {len(games)}")

    main_by_turn: dict[tuple[int, int], list[Mapping[str, Any]]] = defaultdict(list)
    for row in main_rows:
        main_by_turn[(int(row["episode_id"]), int(row["global_turn"]))].append(row)
    supporter_turns: list[dict[str, Any]] = []
    for (episode_id, turn), rows in sorted(main_by_turn.items()):
        opportunities = [row for row in rows if {1213, 1227}.issubset({int(value) for value in str(row["legal_play_card_ids"]).split() if value})]
        if not opportunities:
            continue
        actual = next((row for row in rows if row["action_kind"] == "PLAY" and as_int(row["action_card_id"]) in (1213, 1227)), None)
        first = opportunities[0]
        supporter_turns.append({
            "episode_id": episode_id,
            "global_turn": turn,
            "own_turn": first["own_turn"],
            "opponent_archetype": first["opponent_archetype"],
            "result": first["result"],
            "own_hand_count_at_first_both_legal": first["own_hand_count"],
            "opponent_hand_count_at_first_both_legal": first["opponent_hand_count"],
            "own_prize_remaining": first["own_prize_remaining"],
            "opponent_prize_remaining": first["opponent_prize_remaining"],
            "actual_supporter_id": actual["action_card_id"] if actual else "",
            "actual_supporter_name": actual["action_card_name"] if actual else "NONE",
            "played_judge": bool(actual and as_int(actual["action_card_id"]) == 1213),
            "played_lillie": bool(actual and as_int(actual["action_card_id"]) == 1227),
            "played_neither": actual is None,
            "first_opportunity_step": first["replay_step"],
            "actual_play_step": actual["replay_step"] if actual else "",
        })

    matchup_summary = summarize_matchups(games, main_rows)
    matchup_action_rates = summarize_action_rates(games, main_rows)
    attack_target_summary = summarize_attack_targets(main_rows)
    lucario_attack_context = [
        row for row in main_rows
        if row["action_kind"] == "ATTACK" and as_int(row.get("own_active_id")) == 678
    ]
    gust_context = [row for row in effect_rows if row["choice_type"] == "GUST_TARGET"]
    wally_context = [row for row in effect_rows if row["choice_type"] == "WALLY_HEAL_TARGET"]
    aura_attach_context = [row for row in effect_rows if row["choice_type"] == "AURA_ATTACH_TARGET"]

    outputs = {
        "games.csv": games,
        "main_actions.csv": main_rows,
        "effect_choices.csv": effect_rows,
        "matchup_summary.csv": matchup_summary,
        "matchup_action_rates.csv": matchup_action_rates,
        "attack_target_summary.csv": attack_target_summary,
        "lucario_attack_context.csv": lucario_attack_context,
        "gust_context.csv": gust_context,
        "wally_context.csv": wally_context,
        "aura_attach_context.csv": aura_attach_context,
        "supporter_turns.csv": supporter_turns,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in outputs.items():
        write_csv(args.out_dir / name, rows)

    manifest_payload = "".join(f"{name}:{digest}\n" for name, digest in sorted(source_hashes))
    manifest = {
        "schema_version": "majkel_public_board_policy.v1",
        "target_team": args.target_team,
        "validation_episode_excluded": args.validation_episode_id,
        "episodes_csv": str(args.episodes_csv),
        "episodes_csv_sha256": sha256_file(args.episodes_csv),
        "public_games": len(games),
        "main_actions": len(main_rows),
        "effect_choices": len(effect_rows),
        "lucario_attacks": len(lucario_attack_context),
        "gust_targets": len(gust_context),
        "wally_targets": len(wally_context),
        "aura_attach_targets": len(aura_attach_context),
        "supporter_both_legal_turns": len(supporter_turns),
        "replay_filename_hash_manifest_sha256": hashlib.sha256(manifest_payload.encode("utf-8")).hexdigest(),
        "generation_script": str(Path(__file__).resolve()),
        "generation_script_sha256": sha256_file(Path(__file__).resolve()),
        "outputs": {
            name: {
                "rows": len(rows),
                "sha256": sha256_file(args.out_dir / name),
            }
            for name, rows in outputs.items()
        },
    }
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
