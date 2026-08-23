"""Select public, replay-trace-preserving Boss versus front-attack roots.

Selection is deliberately outcome-blind.  It reads only the normalized public
trace, applies the frozen eligibility contract, and writes a deterministic
eligible/selected root ledger.  No candidate policy is created here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
V2_DIR = HERE.parent / "counterfactual_root_action_search_v2_stratified_multiworld"
V1_DIR = HERE.parent / "counterfactual_macro_search_v1"
for path in (REPO_ROOT, V2_DIR, V1_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from common import singleton_action_semantics  # noqa: E402
from common_v2 import canonical_sha256, normalized_public_hash, public_context_tags  # noqa: E402
from infrastructure.tools.ptcg_common import ensure_engine_on_path  # noqa: E402


MAIN_CONTEXT = 0
BOSS_ID = 1182
LILLIE_ID = 1227
ALAKAZAM_ID = 743
ATTACK_TYPE = 13
PLAY_TYPE = 7
CARD_DB: dict[int, Any] = {}
ATTACK_DB: dict[int, Any] = {}


def _json_rows(path: Path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def _options(observation: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    values = (observation.get("select") or {}).get("option") or []
    return [item for item in values if isinstance(item, Mapping)]


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _card_ids(cards: Any) -> list[int]:
    if not isinstance(cards, list):
        return []
    out: list[int] = []
    for card in cards:
        if isinstance(card, Mapping) and _int(card.get("id")) is not None:
            out.append(int(card["id"]))
    return out


def _public_prize_count(player: Mapping[str, Any], result: Any) -> int | None:
    value = player.get("prize")
    if not isinstance(value, list):
        return None
    if not value and _int(result) in (None, -1):
        return None
    return len(value)


def _printed_prize(card: Mapping[str, Any] | None) -> int | None:
    if card is None:
        return None
    data = CARD_DB.get(_int(card.get("id")))
    if data is None:
        return None
    return 3 if bool(getattr(data, "megaEx", False)) else 2 if bool(getattr(data, "ex", False)) else 1


def _enum_int(value: Any) -> int | None:
    return _int(getattr(value, "value", value))


def _ready_bench_count(bench: list[Mapping[str, Any]]) -> int | None:
    if not CARD_DB or not ATTACK_DB:
        return None
    count = 0
    for pokemon in bench:
        card_id = _int(pokemon.get("id"))
        data = CARD_DB.get(card_id)
        energies = pokemon.get("energyCards") or pokemon.get("energies") or []
        available = [_enum_int(getattr(CARD_DB.get(_int(card.get("id"))), "energyType", None)) if isinstance(card, Mapping) else _enum_int(card) for card in energies]
        available = [energy for energy in available if energy is not None]
        if data is None:
            return None
        ready = False
        for attack_id in getattr(data, "attacks", []) or []:
            attack = ATTACK_DB.get(_int(attack_id))
            if attack is None:
                continue
            cost = [_enum_int(value) for value in (getattr(attack, "energies", []) or [])]
            cost = [value for value in cost if value is not None]
            pool = list(available)
            ok = True
            for required in cost:
                if required == 0:
                    if not pool:
                        ok = False; break
                    pool.pop()
                elif required in pool:
                    pool.remove(required)
                else:
                    ok = False; break
            if ok:
                ready = True; break
        if ready:
            count += 1
    return count


def _active_attack_proof(active: Mapping[str, Any] | None, opponent_active: Mapping[str, Any] | None, options: list[Mapping[str, Any]]) -> bool | None:
    if active is None or opponent_active is None:
        return None
    target_hp = _int(opponent_active.get("hp"))
    attacker_id = _int(active.get("id"))
    attacker_data = CARD_DB.get(attacker_id)
    target_data = CARD_DB.get(_int(opponent_active.get("id")))
    if target_hp is None or attacker_data is None or target_data is None:
        return None
    legal = [option for option in options if _int(option.get("type")) == ATTACK_TYPE and option.get("attackId") is not None]
    if not legal:
        return False
    known_results: list[bool] = []
    for option in legal:
        attack = ATTACK_DB.get(_int(option.get("attackId")))
        if attack is None or str(getattr(attack, "text", "") or ""):
            continue
        damage = _int(getattr(attack, "damage", None))
        if damage is None:
            continue
        if _enum_int(getattr(target_data, "weakness", None)) == _enum_int(getattr(attacker_data, "energyType", None)):
            damage *= 2
        if _enum_int(getattr(target_data, "resistance", None)) == _enum_int(getattr(attacker_data, "energyType", None)):
            damage = max(0, damage - 30)
        known_results.append(damage >= target_hp)
    if not known_results:
        return None
    if any(known_results):
        return True
    if len(known_results) == len(legal):
        return False
    return None


def _selected_option_index(row: Mapping[str, Any], semantic_id: str) -> int | None:
    for item in row.get("legal_semantic_action_set") or []:
        if str(item.get("semantic_id")) == semantic_id:
            value = item.get("option_index")
            return _int(value)
    return None


def _option_semantic_map(row: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for item in row.get("legal_semantic_action_set") or []:
        idx = _int(item.get("option_index"))
        if idx is not None:
            result[idx] = item
    return result


def _parent_category(row: Mapping[str, Any], options: list[Mapping[str, Any]]) -> str:
    semantic = str(row.get("parent_semantic_action"))
    index = _selected_option_index(row, semantic)
    if index is None or not (0 <= index < len(options)):
        return "UNKNOWN"
    option = options[index]
    typ = _int(option.get("type"))
    if typ == ATTACK_TYPE:
        return "ATTACK"
    if typ == PLAY_TYPE:
        current = row.get("observation", {}).get("current", {})
        seat = _int(row.get("policy_seat"))
        players = current.get("players") or []
        hand = players[seat].get("hand") if seat in (0, 1) and seat < len(players) else []
        hand_index = _int(option.get("index"))
        if hand_index is not None and isinstance(hand, list) and 0 <= hand_index < len(hand):
            if _int((hand[hand_index] or {}).get("id")) == BOSS_ID:
                return "BOSS"
        return "PLAY"
    return "OTHER"


def _safety_exclusion(row: Mapping[str, Any], options: list[Mapping[str, Any]]) -> str | None:
    """Public conservative exclusion for the parent's Alakazam/Lillie helper."""
    observation = row.get("observation") or {}
    current = observation.get("current") or {}
    seat = _int(row.get("policy_seat"))
    players = current.get("players") or []
    if seat not in (0, 1) or not isinstance(players, list) or seat >= len(players):
        return "invalid_seat_or_players"
    mine = players[seat] or {}
    hand = mine.get("hand") or []
    lillie_indices = [i for i, card in enumerate(hand) if isinstance(card, Mapping) and _int(card.get("id")) == LILLIE_ID]
    lillie_options = [
        option for option in options
        if _int(option.get("type")) == PLAY_TYPE and _int(option.get("index")) in lillie_indices
    ]
    active = mine.get("active") or []
    bench = mine.get("bench") or []
    has_alakazam = any(_int(card.get("id")) == ALAKAZAM_ID for card in list(active) + list(bench) if isinstance(card, Mapping))
    parent_is_lillie = False
    parent_idx = _selected_option_index(row, str(row.get("parent_semantic_action")))
    if parent_idx is not None and 0 <= parent_idx < len(options):
        parent_is_lillie = _int(options[parent_idx].get("type")) == PLAY_TYPE and _int(options[parent_idx].get("index")) in lillie_indices
    if lillie_options and (parent_is_lillie or has_alakazam):
        return "PUBLIC_ALAKAZAM_LILLIE_HELPER_SURFACE"
    return None


def _make_root(row: Mapping[str, Any], source_path: Path, line_number: int) -> tuple[dict[str, Any] | None, str | None]:
    observation = row.get("observation") or {}
    current = observation.get("current") or {}
    select = observation.get("select") or {}
    seat = _int(row.get("policy_seat"))
    if seat not in (0, 1):
        return None, "invalid_policy_seat"
    if _int(current.get("yourIndex")) != seat:
        return None, "not_own_callback"
    if _int(select.get("context")) != MAIN_CONTEXT:
        return None, "not_main_context"
    if _int(current.get("result")) != -1:
        return None, "nonterminal_result"
    if bool(current.get("supporterPlayed")):
        return None, "supporter_already_played"
    players = current.get("players") or []
    if not isinstance(players, list) or len(players) != 2:
        return None, "invalid_players"
    mine = players[seat] or {}
    opponent = players[1 - seat] or {}
    hand = mine.get("hand") or []
    hand_ids = [_int(card.get("id")) for card in hand if isinstance(card, Mapping)]
    boss_hand_indices = [index for index, card_id in enumerate(hand_ids) if card_id == BOSS_ID]
    if not boss_hand_indices:
        return None, "boss_not_publicly_in_hand"
    opponent_bench = [card for card in (opponent.get("bench") or []) if isinstance(card, Mapping)]
    if not opponent_bench:
        return None, "opponent_bench_empty"
    options = _options(observation)
    legal_map = _option_semantic_map(row)
    boss_options = [
        (index, option) for index, option in enumerate(options)
        if _int(option.get("type")) == PLAY_TYPE and _int(option.get("index")) in boss_hand_indices
    ]
    if len(boss_options) != 1:
        return None, "boss_play_not_unique"
    attack_options: dict[int, tuple[int, Mapping[str, Any]]] = {}
    duplicate_attack_ids: dict[str, list[int]] = defaultdict(list)
    for index, option in enumerate(options):
        if _int(option.get("type")) != ATTACK_TYPE or option.get("attackId") is None:
            continue
        attack_id = _int(option.get("attackId"))
        if attack_id is None:
            continue
        duplicate_attack_ids[str(attack_id)].append(index)
        attack_options.setdefault(attack_id, (index, option))
    if not attack_options:
        return None, "front_attack_not_legal"
    boss_index = boss_options[0][0]
    boss_semantic = legal_map.get(boss_index, {}).get("semantic_id")
    if not boss_semantic:
        return None, "boss_semantic_not_rebindable"
    front: list[dict[str, Any]] = []
    for attack_id, (index, option) in sorted(attack_options.items()):
        semantic = legal_map.get(index, {}).get("semantic_id")
        if not semantic:
            continue
        front.append({
            "attack_id": attack_id,
            "option_index": index,
            "action": [index],
            "semantic_id": str(semantic),
            "duplicate_option_indices": duplicate_attack_ids[str(attack_id)],
        })
    if not front:
        return None, "front_attack_semantic_not_rebindable"
    safety_reason = _safety_exclusion(row, options)
    if safety_reason:
        return None, safety_reason
    parent_category = _parent_category(row, options)
    if parent_category not in {"BOSS", "ATTACK"}:
        return None, "parent_not_boss_or_attack"
    schedule_key = str(row.get("schedule_key"))
    public_hash = normalized_public_hash(observation)
    root_key = "|".join([
        str(row.get("panel")), str(row.get("opponent_policy_id")), str(seat),
        str(row.get("game")), str(row.get("seed")), str(row.get("callback_index")),
    ])
    prize_count = len(mine.get("prize") or [])
    front_active = (opponent.get("active") or [None])[0] if isinstance((opponent.get("active") or [None])[0], Mapping) else None
    front_prize = _printed_prize(front_active)
    bench_prizes = [_printed_prize(card) for card in opponent_bench]
    if front_prize is None or any(value is None for value in bench_prizes):
        boss_higher: bool | None = None
        boss_unique_highest: bool | None = None
    else:
        boss_higher = any(int(value) > int(front_prize) for value in bench_prizes)
        highest = max([int(front_prize), *(int(value) for value in bench_prizes)])
        highest_targets = [value for value in bench_prizes if int(value) == highest]
        boss_unique_highest = bool(highest > int(front_prize) and len(highest_targets) == 1)
    ready_bench = _ready_bench_count([card for card in mine.get("bench") or [] if isinstance(card, Mapping)])
    has_front_attack = bool([option for option in options if _int(option.get("type")) == ATTACK_TYPE and option.get("attackId") is not None])
    current_only_attacker = None if ready_bench is None else bool(has_front_attack and ready_bench == 0)
    root_id = hashlib.sha256(root_key.encode("utf-8")).hexdigest()[:20]
    selection_hash = hashlib.sha256(f"{schedule_key}|{row.get('callback_index')}|{public_hash}".encode("utf-8")).hexdigest()
    return {
        "schema_version": "archaludon_boss_vs_front_attack_root.v1",
        "root_id": root_id,
        "source_trace": str(source_path),
        "source_line": line_number,
        "panel": row.get("panel"),
        "opponent_family": row.get("opponent_family"),
        "opponent_policy_id": row.get("opponent_policy_id"),
        "opponent_path": row.get("opponent_path"),
        "policy_seat": seat,
        "acting_seat": _int(row.get("acting_seat")),
        "schedule_key": schedule_key,
        "game": _int(row.get("game")),
        "seed": _int(row.get("seed")),
        "callback_index": _int(row.get("callback_index")),
        "turn": _int(row.get("turn")),
        "turn_action_count": _int(row.get("turnActionCount")),
        "public_hash": public_hash,
        "trace_public_hash": row.get("public_hash"),
        "parent_semantic_action": row.get("parent_semantic_action"),
        "parent_action_category": parent_category,
        "legal_semantic_action_set": row.get("legal_semantic_action_set") or [],
        "boss_action": [boss_index],
        "boss_semantic_action": str(boss_semantic),
        "boss_card_id": BOSS_ID,
        "front_attacks": front,
        "duplicate_attack_ids": {key: value for key, value in duplicate_attack_ids.items() if len(value) > 1},
        "own_prizes_remaining": prize_count,
        "own_remaining_prizes": prize_count,
        "opponent_remaining_prizes": _public_prize_count(opponent, current.get("result")),
        "own_board_count": len([card for card in list(mine.get("active") or []) + list(mine.get("bench") or []) if isinstance(card, Mapping)]),
        "opponent_board_count": len([card for card in list(opponent.get("active") or []) + list(opponent.get("bench") or []) if isinstance(card, Mapping)]),
        "own_active": (mine.get("active") or [None])[0],
        "opponent_active": (opponent.get("active") or [None])[0],
        "opponent_bench": opponent_bench,
        "own_bench_count": len([card for card in mine.get("bench") or [] if isinstance(card, Mapping)]),
        "opponent_bench_count": len(opponent_bench),
        "own_active_card_id": _int(((mine.get("active") or [None])[0] or {}).get("id")) if isinstance((mine.get("active") or [None])[0], Mapping) else None,
        "own_active_hp": _int(((mine.get("active") or [None])[0] or {}).get("hp")) if isinstance((mine.get("active") or [None])[0], Mapping) else None,
        "opponent_active_card_id": _int(((opponent.get("active") or [None])[0] or {}).get("id")) if isinstance((opponent.get("active") or [None])[0], Mapping) else None,
        "opponent_active_hp": _int(((opponent.get("active") or [None])[0] or {}).get("hp")) if isinstance((opponent.get("active") or [None])[0], Mapping) else None,
        "current_front_exact_ko": _active_attack_proof((mine.get("active") or [None])[0] if isinstance((mine.get("active") or [None])[0], Mapping) else None, (opponent.get("active") or [None])[0] if isinstance((opponent.get("active") or [None])[0], Mapping) else None, options),
        "current_front_printed_prize": _printed_prize((opponent.get("active") or [None])[0] if isinstance((opponent.get("active") or [None])[0], Mapping) else None),
        "boss_has_higher_printed_prize_target": boss_higher,
        "boss_unique_highest_prize_target": boss_unique_highest,
        "current_active_is_only_attacker": current_only_attacker,
        "own_ready_bench_attacker_count": ready_bench,
        "turn_bucket": "EARLY" if (_int(row.get("turn")) or 0) <= 3 else "MID" if (_int(row.get("turn")) or 0) <= 6 else "LATE",
        "prize_bucket": "OPENING" if prize_count >= 5 else "MIDDLE" if prize_count >= 3 else "CLOSING",
        "context_tags": list(row.get("context_tags") or public_context_tags(observation)),
        "selection_hash": selection_hash,
        "selection_bucket": int(selection_hash[:16], 16) % 100,
        "game_bucket": int(hashlib.sha256(schedule_key.encode("utf-8")).hexdigest(), 16) % 100,
    }, None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path)
    parser.add_argument("--max-roots", type=int, default=192)
    args = parser.parse_args()
    if args.engine_dir:
        ensure_engine_on_path(args.engine_dir.resolve())
        try:
            from cg.api import all_attack, all_card_data  # type: ignore
            global CARD_DB, ATTACK_DB
            CARD_DB = {int(card.cardId): card for card in all_card_data()}
            ATTACK_DB = {int(attack.attackId): attack for attack in all_attack()}
        except Exception:
            CARD_DB = {}; ATTACK_DB = {}
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    eligible: list[dict[str, Any]] = []
    excluded = Counter()
    seen_roots: set[str] = set()
    trace_files = sorted(args.trace_root.glob("**/traces/**/*.jsonl"))
    for trace in trace_files:
        for line_number, row in enumerate(_json_rows(trace), 1):
            root, reason = _make_root(row, trace, line_number)
            if root is None:
                excluded[reason or "unknown"] += 1
                continue
            if root["game_bucket"] >= 65:
                excluded["non_discovery_game_bucket"] += 1
                continue
            if root["root_id"] in seen_roots:
                excluded["duplicate_root"] += 1
                continue
            seen_roots.add(root["root_id"])
            eligible.append(root)
    eligible.sort(key=lambda row: (str(row["selection_hash"]), str(row["root_id"])))
    # Outcome-blind caps: at most two roots per game and one root per own turn.
    selected: list[dict[str, Any]] = []
    game_counts: Counter[tuple[Any, ...]] = Counter()
    turn_used: set[tuple[Any, ...]] = set()
    for root in eligible:
        game_key = (root["schedule_key"], root["opponent_policy_id"], root["game"], root["seed"])
        turn_key = game_key + (root["policy_seat"], root["turn"])
        if game_counts[game_key] >= 2 or turn_key in turn_used:
            excluded["selection_cap"] += 1
            continue
        selected.append(root)
        game_counts[game_key] += 1
        turn_used.add(turn_key)
        if len(selected) >= args.max_roots:
            break
    # A compact selection audit makes imbalance explicit without using results.
    count = lambda rows, key: dict(sorted(Counter(str(row.get(key)) for row in rows).items()))
    summary = {
        "schema_version": "archaludon_boss_vs_front_attack_selection.v1",
        "trace_root": str(args.trace_root.resolve()),
        "trace_file_count": len(trace_files),
        "eligible_root_count": len(eligible),
        "selected_root_count": len(selected),
        "selected_distinct_games": len({(r["schedule_key"], r["opponent_policy_id"], r["game"], r["seed"]) for r in selected}),
        "selected_families": count(selected, "opponent_family"),
        "selected_seats": count(selected, "policy_seat"),
        "selected_parent_categories": count(selected, "parent_action_category"),
        "selected_game_buckets": count(selected, "game_bucket"),
        "excluded_reasons": dict(sorted(excluded.items())),
        "holdout_opened": False,
        "reserve_opened": False,
        "outcome_blind": True,
    }
    (out / "eligible_roots.jsonl").write_text("".join(json.dumps(r, sort_keys=True, ensure_ascii=True) + "\n" for r in eligible), encoding="utf-8")
    (out / "selected_roots.jsonl").write_text("".join(json.dumps(r, sort_keys=True, ensure_ascii=True) + "\n" for r in selected), encoding="utf-8")
    (out / "selection_summary.json").write_text(json.dumps(summary, sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True, ensure_ascii=True))
    if len({r["opponent_family"] for r in selected}) < 4 or len({r["policy_seat"] for r in selected}) < 2 or len({(r["opponent_policy_id"], r["game"], r["seed"]) for r in selected}) < 32:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
