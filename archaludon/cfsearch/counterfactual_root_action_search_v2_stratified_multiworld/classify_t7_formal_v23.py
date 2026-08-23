"""Classify formal T7 branches using public target-role features.

This is a diagnostic classifier only.  It never changes an agent, synthesizes
an action policy, or reads hidden engine state.  It loads card/attack metadata
from the explicitly supplied seeded engine and records the import path.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
V1_DIR = HERE.parent / "counterfactual_macro_search_v1"
for path in (REPO_ROOT, V1_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from infrastructure.tools.ptcg_common import ensure_engine_on_path  # noqa: E402


def _slot(value: Any, index: int) -> Mapping[str, Any] | None:
    if isinstance(value, list):
        if 0 <= index < len(value) and isinstance(value[index], Mapping):
            return value[index]
        return None
    if index == 0 and isinstance(value, Mapping):
        return value
    return None


def _energy_count(pokemon: Mapping[str, Any] | None) -> int:
    if not pokemon:
        return 0
    cards = pokemon.get("energyCards")
    if isinstance(cards, list):
        return len(cards)
    energies = pokemon.get("energies")
    return len(energies) if isinstance(energies, list) else 0


def _options(observation: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    select = observation.get("select") or {}
    options = select.get("option") or []
    return [option for option in options if isinstance(option, Mapping)]


def _target_for_action(observation: Mapping[str, Any], action: list[int]) -> dict[str, Any] | None:
    options = _options(observation)
    if not action or not isinstance(action[0], int) or not (0 <= action[0] < len(options)):
        return None
    option = options[action[0]]
    if option.get("type") == 14:
        return None
    area = option.get("inPlayArea")
    index = option.get("inPlayIndex")
    if area not in (4, 5) or not isinstance(index, int):
        return None
    current = observation.get("current") or {}
    your_index = current.get("yourIndex") if current.get("yourIndex") in (0, 1) else 0
    owner = option.get("inPlayPlayerIndex")
    owner_index = owner if owner in (0, 1) else your_index
    players = current.get("players") or []
    if not (isinstance(players, list) and owner_index < len(players)):
        return None
    player = players[owner_index] or {}
    pokemon = _slot(player.get("active") if area == 4 else player.get("bench"), index)
    return {
        "area": "ACTIVE" if area == 4 else "BENCH",
        "area_code": area,
        "index": index,
        "player_index": owner_index,
        "pokemon": pokemon,
        "option": dict(option),
    }


def _card_lookup(engine_dir: Path) -> tuple[dict[int, Any], dict[int, Any], str]:
    ensure_engine_on_path(engine_dir)
    import cg  # type: ignore  # noqa: PLC0415
    from cg.api import all_attack, all_card_data  # type: ignore  # noqa: PLC0415

    module_path = str(Path(getattr(cg, "__file__", "")).resolve())
    engine_root = str(engine_dir.resolve())
    if not (module_path == engine_root or module_path.startswith(engine_root + "\\") or module_path.startswith(engine_root + "/")):
        raise RuntimeError(f"INVALID_ENGINE_IMPORT_SHADOW: {module_path} not under {engine_root}")
    return (
        {int(item.cardId): item for item in all_card_data()},
        {int(item.attackId): item for item in all_attack()},
        module_path,
    )


def _attacks(card: Any, attacks: Mapping[int, Any]) -> list[Any]:
    if card is None:
        return []
    return [attacks[int(attack_id)] for attack_id in (getattr(card, "attacks", None) or []) if int(attack_id) in attacks]


def _name(card: Any) -> str:
    return str(getattr(card, "name", "")) if card is not None else ""


def _minimum_cost(card: Any, attacks: Mapping[int, Any]) -> int | None:
    costs = [len(getattr(attack, "energies", None) or []) for attack in _attacks(card, attacks)]
    return min(costs) if costs else None


def _hand_flags(player: Mapping[str, Any], cards: Mapping[int, Any]) -> dict[str, Any]:
    hand_cards = []
    for item in player.get("hand") or []:
        if isinstance(item, Mapping) and int(item.get("id", -1)) in cards:
            hand_cards.append(cards[int(item["id"])])
    names = [_name(card) for card in hand_cards]
    return {
        "archaludon_ex_in_hand": any("Archaludon" in _name(card) and bool(getattr(card, "ex", False)) for card in hand_cards),
        "non_ex_archaludon_in_hand": any("Archaludon" in name and "ex" not in name.lower() for name in names),
        "hand_names": sorted(names),
    }


def _attack_state(
    pokemon: Mapping[str, Any] | None,
    attached_count: int,
    opponent_hp: int | None,
    attacks: Mapping[int, Any],
    legal_attack_option: bool,
) -> dict[str, Any]:
    card_id = int(pokemon.get("id", -1)) if pokemon else -1
    # Card metadata is public and immutable; attached count is the only
    # counterfactual change in this diagnostic attach branch.
    return_card = None
    return_card = _CARD_DATA.get(card_id)
    printed = _attacks(return_card, attacks)
    paid = [attack for attack in printed if len(getattr(attack, "energies", None) or []) <= attached_count]
    attack_ids = sorted(int(getattr(attack, "attackId")) for attack in paid)
    known = [attack for attack in paid if int(getattr(attack, "damage", 0) or 0) > 0 and not str(getattr(attack, "text", "") or "").strip()]
    unknown = [attack for attack in paid if attack not in known]
    effective: bool | str
    if known:
        effective = True
    elif paid or legal_attack_option:
        effective = "UNKNOWN"
    else:
        effective = False
    ko_ids = sorted(int(getattr(attack, "attackId")) for attack in known if opponent_hp is not None and int(getattr(attack, "damage", 0) or 0) >= opponent_hp)
    ko_known = not unknown and opponent_hp is not None
    return {
        "card_id": card_id,
        "card_name": _name(return_card),
        "energy_count": attached_count,
        "minimum_printed_attack_cost": _minimum_cost(return_card, attacks),
        "minimum_energy_deficit": max(0, (_minimum_cost(return_card, attacks) or 0) - attached_count),
        "attack_ids_paid": attack_ids,
        "current_active_has_effective_attack": effective,
        "exact_ko_ids": ko_ids if ko_known else "UNKNOWN",
        "exact_ko_known": ko_known,
        "known_max_damage": max((int(getattr(attack, "damage", 0) or 0) for attack in known), default=None),
        "attack_ready_if_promoted": bool(paid),
        "attack_unlocked_by_attach": bool(_minimum_cost(return_card, attacks) is not None and max(0, (_minimum_cost(return_card, attacks) or 0) - (attached_count - 1)) == 1 and max(0, (_minimum_cost(return_card, attacks) or 0) - attached_count) == 0),
        "energy_deficit_after": max(0, (_minimum_cost(return_card, attacks) or 0) - attached_count),
    }


def _retreat_legal(pokemon: Mapping[str, Any] | None, current: Mapping[str, Any], cards: Mapping[int, Any], energy_count: int) -> bool | str:
    if not pokemon:
        return "UNKNOWN"
    if bool(current.get("retreated")):
        return False
    if any(bool(current.get(name)) for name in ("asleep", "paralyzed", "confused")):
        return False
    card = cards.get(int(pokemon.get("id", -1)))
    cost = getattr(card, "retreatCost", None)
    return bool(cost is not None and energy_count >= int(cost))


def _target_features(observation: Mapping[str, Any], target: Mapping[str, Any] | None, cards: Mapping[int, Any], attacks: Mapping[int, Any]) -> dict[str, Any]:
    if not target:
        return {"role": "OTHER", "area": None}
    current = observation.get("current") or {}
    players = current.get("players") or []
    owner_index = int(target["player_index"])
    player = players[owner_index] or {}
    pokemon = target.get("pokemon") or {}
    active = _slot(player.get("active"), 0)
    opponent_index = 1 - int(current.get("yourIndex", 0) or 0)
    opponent = players[opponent_index] if len(players) > opponent_index else {}
    opponent_active = _slot((opponent or {}).get("active"), 0)
    opponent_hp = int(opponent_active.get("hp")) if isinstance(opponent_active, Mapping) and opponent_active.get("hp") is not None else None
    target_before_count = _energy_count(pokemon)
    target_after_count = target_before_count + 1
    # OptionType.ATTACK is 13; 14 is the turn-end option.
    legal_attack_option = any(option.get("type") == 13 for option in _options(observation))
    active_before = _attack_state(active, _energy_count(active), opponent_hp, attacks, legal_attack_option)
    active_after = _attack_state(active, _energy_count(active) + (1 if target.get("area") == "ACTIVE" else 0), opponent_hp, attacks, legal_attack_option)
    target_before = _attack_state(pokemon, target_before_count, opponent_hp, attacks, legal_attack_option)
    target_after = _attack_state(pokemon, target_after_count, opponent_hp, attacks, legal_attack_option)
    card = cards.get(int(pokemon.get("id", -1)))
    target_name = _name(card)
    hand = _hand_flags(player, cards)
    evolution_legal = any(
        isinstance(item, Mapping)
        and int(item.get("id", -1)) in cards
        and getattr(cards[int(item["id"])], "evolvesFrom", None) == target_name
        for item in (player.get("hand") or [])
    )
    if target.get("area") == "ACTIVE":
        if active_before["current_active_has_effective_attack"] is True:
            role = "R2_CURRENT_ACTIVE_ALREADY_READY"
        elif active_before["current_active_has_effective_attack"] == "UNKNOWN":
            role = "R3_CURRENT_ACTIVE_UNKNOWN"
        elif active_after["current_active_has_effective_attack"] is True:
            role = "R1_CURRENT_ACTIVE_UNLOCKS_ATTACK"
        else:
            role = "OTHER"
    elif target_after["attack_unlocked_by_attach"] and target_after["attack_ready_if_promoted"]:
        role = "R4_BENCH_UNLOCKED_ATTACK_READY"
    elif target_before["attack_ready_if_promoted"]:
        role = "R5_BENCH_ALREADY_ATTACK_READY"
    elif target_after["minimum_energy_deficit"] == 1:
        role = "R6_BENCH_ONE_SHORT_AFTER"
    elif evolution_legal or target_name in {"Duraludon", "Archaludon ex", "Archaludon"}:
        role = "R7_BENCH_EVOLUTION_DEPENDENT"
    elif int(pokemon.get("id", -1)) == 666:
        role = "R8_CINDERACE_PIVOT"
    else:
        role = "R9_UNREADY_BENCH"
    target_before["area"] = target.get("area")
    target_after["area"] = target.get("area")
    target_before["role"] = role
    target_after["role"] = role
    return {
        "area": target.get("area"),
        "index": target.get("index"),
        "player_index": owner_index,
        "card_id": int(pokemon.get("id", -1)),
        "card_name": target_name,
        "serial": pokemon.get("serial"),
        "pokemon_hp": pokemon.get("hp"),
        "pokemon_max_hp": pokemon.get("maxHp"),
        "appeared_this_turn": pokemon.get("appearThisTurn"),
        "energy_count_before": target_before_count,
        "energy_count_after": target_after_count,
        "minimum_printed_attack_cost": target_after["minimum_printed_attack_cost"],
        "minimum_energy_deficit_before": target_before["minimum_energy_deficit"],
        "minimum_energy_deficit_after": target_after["minimum_energy_deficit"],
        "current_active_has_legal_attack_before": legal_attack_option,
        "current_active_has_legal_attack_after": bool(active_after["attack_ids_paid"]),
        "current_active_has_effective_attack_before": active_before["current_active_has_effective_attack"],
        "current_active_has_effective_attack_after": active_after["current_active_has_effective_attack"],
        "current_active_exact_ko_before": active_before["exact_ko_ids"],
        "current_active_exact_ko_after": active_after["exact_ko_ids"],
        "retreat_legal_before": _retreat_legal(active, current, cards, _energy_count(active)),
        "retreat_legal_after": _retreat_legal(active, current, cards, _energy_count(active) + (1 if target.get("area") == "ACTIVE" else 0)),
        "evolution_option_legal": evolution_legal,
        "archaludon_ex_in_hand": hand["archaludon_ex_in_hand"],
        "non_ex_archaludon_in_hand": hand["non_ex_archaludon_in_hand"],
        "target_before": target_before,
        "target_after": target_after,
        "role": role,
    }


def _direction(parent: Mapping[str, Any], alternative: Mapping[str, Any]) -> str:
    pa, aa = parent.get("area"), alternative.get("area")
    if pa == "ACTIVE" and aa == "BENCH":
        return "T7A_ACTIVE_TO_BENCH"
    if pa == "BENCH" and aa == "ACTIVE":
        return "T7B_BENCH_TO_ACTIVE"
    if pa == "BENCH" and aa == "BENCH" and parent.get("index") != alternative.get("index"):
        return "T7C_BENCH_TO_OTHER_BENCH"
    if pa == "ACTIVE" and aa == "ACTIVE" and parent.get("index") != alternative.get("index"):
        return "T7D_ACTIVE_TO_DIFFERENT_ACTIVE_ROLE"
    if pa == aa and parent.get("index") == alternative.get("index") and parent.get("card_id") == alternative.get("card_id"):
        return "T7D_SAME_TARGET_DUPLICATE"
    return "T7E_OTHER_ATTACH_CHANGE"


def _outcome(row: Mapping[str, Any], seat: int) -> str:
    if row.get("status") != "complete" or not row.get("root_match") or int(row.get("action_errors") or 0) or row.get("hit_max_steps"):
        return "invalid"
    result = row.get("terminal_result")
    if result == seat:
        return "win"
    if result in (0, 1):
        return "loss"
    if result == 2:
        return "draw"
    return "unknown"


def _delta(parent_outcome: str, alternative_outcome: str) -> int:
    if parent_outcome in {"loss", "draw"} and alternative_outcome == "win":
        return 1
    if parent_outcome == "win" and alternative_outcome in {"loss", "draw"}:
        return -1
    return 0


def _families(row: Mapping[str, Any]) -> list[str]:
    direction = row["direction"]
    parent = row["parent_target"]
    alternative = row["alternative_target"]
    same_attack = (
        parent.get("current_active_has_effective_attack_before") == parent.get("current_active_has_effective_attack_after")
        and alternative.get("current_active_has_effective_attack_before") == alternative.get("current_active_has_effective_attack_after")
        and parent.get("current_active_has_effective_attack_before") == alternative.get("current_active_has_effective_attack_before")
    )
    same_ko = (
        parent.get("current_active_exact_ko_before") == parent.get("current_active_exact_ko_after")
        and alternative.get("current_active_exact_ko_before") == alternative.get("current_active_exact_ko_after")
        and parent.get("current_active_exact_ko_before") == alternative.get("current_active_exact_ko_before")
        and parent.get("current_active_exact_ko_before") != "UNKNOWN"
    )
    same_retreat = (
        parent.get("retreat_legal_before") == parent.get("retreat_legal_after")
        and alternative.get("retreat_legal_before") == alternative.get("retreat_legal_after")
        and parent.get("retreat_legal_before") == alternative.get("retreat_legal_before")
    )
    parent_active_value = parent.get("target_after", {}).get("known_max_damage")
    parent_role = parent.get("role")
    alt_role = alternative.get("role")
    result: list[str] = []
    if direction == "T7A_ACTIVE_TO_BENCH" and parent_role == "R2_CURRENT_ACTIVE_ALREADY_READY" and alt_role == "R4_BENCH_UNLOCKED_ATTACK_READY" and same_attack and same_ko and same_retreat and parent_active_value is not None:
        result.append("P1_ACTIVE_SURPLUS_TO_BENCH_UNLOCK")
    if direction == "T7B_BENCH_TO_ACTIVE" and parent_role in {"R6_BENCH_ONE_SHORT_AFTER", "R7_BENCH_EVOLUTION_DEPENDENT", "R8_CINDERACE_PIVOT", "R9_UNREADY_BENCH"} and alt_role == "R1_CURRENT_ACTIVE_UNLOCKS_ATTACK":
        result.append("P2_BENCH_TO_ACTIVE_UNLOCK_ATTACK")
    if direction == "T7C_BENCH_TO_OTHER_BENCH" and parent_role in {"R6_BENCH_ONE_SHORT_AFTER", "R7_BENCH_EVOLUTION_DEPENDENT", "R8_CINDERACE_PIVOT", "R9_UNREADY_BENCH"} and alt_role == "R4_BENCH_UNLOCKED_ATTACK_READY":
        result.append("P3_BENCH_UNREADY_TO_BENCH_UNLOCK")
    if direction == "T7A_ACTIVE_TO_BENCH" and parent_role == "R2_CURRENT_ACTIVE_ALREADY_READY" and alt_role == "R6_BENCH_ONE_SHORT_AFTER" and same_attack and same_ko and same_retreat:
        result.append("P4_ACTIVE_SURPLUS_TO_BENCH_ONE_SHORT")
    if parent.get("area") == "BENCH" and alternative.get("area") == "BENCH" and alternative.get("minimum_energy_deficit_after", 99) < parent.get("minimum_energy_deficit_after", 99):
        result.append("P5_ATTACH_TO_MINIMUM_DEFICIT")
    return result


def _summarize(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    comparable = [row for row in rows if row.get("valid")]
    groups: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in comparable:
        groups[row.get(key)].append(row)
    output: dict[str, Any] = {}
    for value, values in sorted(groups.items(), key=lambda item: str(item[0])):
        game_groups: dict[tuple[Any, ...], list[int]] = defaultdict(list)
        for row in values:
            game_groups[(row.get("opponent_family"), row.get("seed"), row.get("policy_seat"))].append(int(row["delta"]))
        game_delta = [statistics.mean(deltas) for deltas in game_groups.values()]
        output[str(value)] = {
            "branches": len(values),
            "distinct_roots": len({row["root_id"] for row in values}),
            "distinct_games": len(game_groups),
            "opponent_families": sorted({str(row.get("opponent_family")) for row in values}),
            "seats": sorted({int(row.get("policy_seat")) for row in values}),
            "root_gains": sum(row["delta"] == 1 for row in values),
            "root_regressions": sum(row["delta"] == -1 for row in values),
            "root_ties": sum(row["delta"] == 0 for row in values),
            "root_net": sum(int(row["delta"]) for row in values),
            "game_gains": sum(value >= 0.25 for value in game_delta),
            "game_regressions": sum(value <= -0.25 for value in game_delta),
            "game_ties": sum(-0.25 < value < 0.25 for value in game_delta),
            "game_net": sum(value >= 0.25 for value in game_delta) - sum(value <= -0.25 for value in game_delta),
            "game_delta_mean": statistics.mean(game_delta) if game_delta else 0.0,
            "unknown_role_count": sum("UNKNOWN" in str(row.get("parent_target")) or "UNKNOWN" in str(row.get("alternative_target")) for row in values),
            "catastrophic_regressions": sum(row["delta"] == -1 and row.get("alternative_role") == "R3_CURRENT_ACTIVE_UNKNOWN" for row in values),
        }
    return output


def classify(roots_path: Path, branches_path: Path, output: Path, engine_dir: Path) -> dict[str, Any]:
    global _CARD_DATA
    _CARD_DATA, attack_data, cg_module_path = _card_lookup(engine_dir)
    roots = {str(row["root_id"]): row for row in (json.loads(line) for line in roots_path.read_text(encoding="utf-8").splitlines() if line.strip())}
    branches = [json.loads(line) for line in branches_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    parents = {str(row["root_id"]): row for row in branches if row.get("branch") == "parent"}
    observations: dict[str, Mapping[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    import_shadow_rows = 0
    for branch in branches:
        if branch.get("branch") != "alternative":
            continue
        root = roots.get(str(branch.get("root_id")))
        parent_row = parents.get(str(branch.get("root_id")))
        if not root or not parent_row:
            continue
        trace_key = str(root["trace_path"])
        if trace_key not in observations:
            trace = Path(trace_key)
            target_callback = int(root["callback_index"])
            hit = next(json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines() if line.strip() and int(json.loads(line).get("callback_index", -1)) == target_callback)
            observations[trace_key] = hit.get("observation") or {}
        observation = observations[trace_key]
        parent_target = _target_for_action(observation, list(root.get("parent_action") or []))
        alternative = next((item for item in root.get("alternative_semantics") or [] if str(item.get("semantic_id")) == str(branch.get("alternative_semantic_id"))), None)
        if alternative is None:
            continue
        alternative_target = _target_for_action(observation, list(alternative.get("action") or []))
        parent_features = _target_features(observation, parent_target, _CARD_DATA, attack_data)
        alternative_features = _target_features(observation, alternative_target, _CARD_DATA, attack_data)
        seat = int(branch.get("policy_seat"))
        parent_outcome = _outcome(parent_row, seat)
        alternative_outcome = _outcome(branch, seat)
        valid = parent_outcome in {"win", "loss", "draw"} and alternative_outcome in {"win", "loss", "draw"}
        row = {
            "root_id": root["root_id"],
            "schedule_key": root.get("schedule_key"),
            "opponent_family": root.get("opponent_family"),
            "policy_seat": seat,
            "seed": root.get("seed"),
            "turn": root.get("turn"),
            "parent_outcome": parent_outcome,
            "alternative_outcome": alternative_outcome,
            "delta": _delta(parent_outcome, alternative_outcome),
            "valid": valid,
            "direction": _direction(parent_features, alternative_features),
            "parent_role": parent_features.get("role"),
            "alternative_role": alternative_features.get("role"),
            "parent_target": parent_features,
            "alternative_target": alternative_features,
            "predicate_families": [],
            "engine_import_ok": bool(branch.get("engine_import_ok") and parent_row.get("engine_import_ok")),
            "cg_module_path": branch.get("cg_module_path"),
        }
        row["predicate_families"] = _families(row)
        if not row["engine_import_ok"]:
            import_shadow_rows += 1
        rows.append(row)
    for row in rows:
        row["valid"] = bool(row["valid"] and row["engine_import_ok"])
    family_rows: list[dict[str, Any]] = []
    for row in rows:
        for family in row["predicate_families"]:
            family_rows.append({**row, "predicate_family": family})
    report = {
        "schema_version": "archaludon_formal_t7_public_feature_classification.v1",
        "source_kind": "FORMAL_REALIZED_SEEDED_WORLD",
        "engine_root": str(engine_dir.resolve()),
        "cg_module_path": cg_module_path,
        "roots": len(roots),
        "alternative_rows": len(rows),
        "valid_rows": sum(bool(row.get("valid")) for row in rows),
        "engine_import_shadow_rows": import_shadow_rows,
        "directions": _summarize(rows, "direction"),
        "target_roles": {
            "parent": _summarize(rows, "parent_role"),
            "alternative": _summarize(rows, "alternative_role"),
        },
        "predicate_families": _summarize(family_rows, "predicate_family"),
        "unknown_role_count": sum("UNKNOWN" in json.dumps(row.get("parent_target")) or "UNKNOWN" in json.dumps(row.get("alternative_target")) for row in rows),
        "candidate_status": "NO_CANDIDATE_DISCOVERY_GATE_NOT_APPLIED",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "classified_rows.jsonl").write_text("".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows), encoding="utf-8", newline="\n")
    (output / "predicate_rows.jsonl").write_text("".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in family_rows), encoding="utf-8", newline="\n")
    (output / "REPORT.json").write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report


_CARD_DATA: dict[int, Any] = {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--roots", type=Path, required=True)
    parser.add_argument("--branches", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = classify(args.roots.resolve(), args.branches.resolve(), args.output.resolve(), args.engine_dir.resolve())
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
