"""Run one exact-seed parent/Boss/front-attack route branch.

Only the first policy-seat action at the selected public callback is replaced.
Every later callback is delegated to the accepted Historical-Silver parent.  No
Boss target, attack sequence, macro, hidden-zone value, or opponent action is
chosen by this runner.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
V2_DIR = HERE.parent / "counterfactual_root_action_search_v2_stratified_multiworld"
V1_DIR = HERE.parent / "counterfactual_macro_search_v1"
for path in (REPO_ROOT, V2_DIR, V1_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from infrastructure.tools.ptcg_common import ensure_engine_on_path, load_agent, read_deck  # noqa: E402
from common import legal_action, singleton_action_semantics  # noqa: E402
from common_v2 import normalized_public_hash  # noqa: E402
from research.rl_ptcg.canonical_actions import canonicalize_prompt_action  # noqa: E402


ATTACK_TYPE = 13
BOSS_ID = 1182
FULL_METAL_LAB_ID = 1244


def _integer(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _semantic(observation: Mapping[str, Any], action: list[int]) -> str:
    try:
        return str(canonicalize_prompt_action(observation, action).stable_id)
    except Exception as exc:
        return f"UNRESOLVED:{type(exc).__name__}"


def _options(observation: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    values = (observation.get("select") or {}).get("option") or []
    return [value for value in values if isinstance(value, Mapping)]


def _chosen_option(observation: Mapping[str, Any], action: list[int]) -> Mapping[str, Any] | None:
    options = _options(observation)
    if len(action) != 1 or not isinstance(action[0], int) or not (0 <= action[0] < len(options)):
        return None
    return options[action[0]]


def _players(observation: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    players = (observation.get("current") or {}).get("players") or []
    return [value if isinstance(value, Mapping) else {} for value in players]


def _active(observation: Mapping[str, Any], seat: int) -> Mapping[str, Any] | None:
    players = _players(observation)
    if seat not in (0, 1) or seat >= len(players):
        return None
    values = players[seat].get("active") or []
    return values[0] if values and isinstance(values[0], Mapping) else None


def _bench(observation: Mapping[str, Any], seat: int) -> list[Mapping[str, Any]]:
    players = _players(observation)
    if seat not in (0, 1) or seat >= len(players):
        return []
    return [value for value in (players[seat].get("bench") or []) if isinstance(value, Mapping)]


def _card_copy(card: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if card is None:
        return None
    keys = ("id", "serial", "hp", "maxHp", "playerIndex", "energies", "energyCards", "tools", "appearThisTurn")
    return {key: card.get(key) for key in keys if key in card}


def _prizes(observation: Mapping[str, Any], seat: int) -> int | None:
    players = _players(observation)
    if seat not in (0, 1) or seat >= len(players):
        return None
    value = players[seat].get("prize")
    # A nonterminal opponent often exposes an empty list rather than the
    # hidden prize count.  Treat that as UNKNOWN instead of manufacturing a
    # zero-prize state or a false prize delta.
    if not isinstance(value, list) or (not value and _integer((observation.get("current") or {}).get("result")) in (None, -1)):
        return None
    return len(value)


def _lookup_metadata():
    try:
        from cg.api import all_attack, all_card_data  # type: ignore
        return {int(card.cardId): card for card in all_card_data()}, {int(attack.attackId): attack for attack in all_attack()}
    except Exception:
        return {}, {}


def _enum_int(value: Any) -> int | None:
    raw = getattr(value, "value", value)
    return _integer(raw)


def _public_damage(attack_id: int | None, attacker: Mapping[str, Any] | None, target: Mapping[str, Any] | None, observation: Mapping[str, Any], card_db: Mapping[int, Any], attack_db: Mapping[int, Any]) -> tuple[bool, int | None, str]:
    """Conservative printed damage proof at one public callback."""
    if attack_id is None or attacker is None or target is None:
        return False, None, "MISSING_ATTACKER_TARGET"
    attack = attack_db.get(int(attack_id))
    if attack is None:
        return False, None, "ATTACK_METADATA_MISSING"
    text = str(getattr(attack, "text", "") or "")
    base = _integer(getattr(attack, "damage", None))
    if base is None:
        return False, None, "ATTACK_DAMAGE_MISSING"
    if text:
        if int(attack_id) == 224 and "damage counter" in text:
            hp = _integer(attacker.get("hp")); max_hp = _integer(attacker.get("maxHp"))
            if hp is None or max_hp is None or max_hp < hp:
                return False, None, "RAGING_HAMMER_DAMAGE_NOT_VISIBLE"
            base += ((max_hp - hp) // 10) * 10
        else:
            return False, None, "NONTRIVIAL_ATTACK_TEXT"
    target_id = _integer(target.get("id"))
    attacker_id = _integer(attacker.get("id"))
    target_data = card_db.get(target_id) if target_id is not None else None
    attacker_data = card_db.get(attacker_id) if attacker_id is not None else None
    if target_data is None or attacker_data is None:
        return False, None, "CARD_METADATA_MISSING"
    tools = target.get("tools") or []
    if tools:
        return False, None, "TARGET_TOOL_MODIFIER"
    stadium = ((observation.get("current") or {}).get("stadium") or [])
    stadium_ids = {_integer(item.get("id")) for item in stadium if isinstance(item, Mapping)}
    # Only the visible Full Metal Lab reduction is proved; an unknown stadium
    # leaves damage unknown rather than guessing a score.
    if stadium_ids and stadium_ids != {None} and stadium_ids != {FULL_METAL_LAB_ID}:
        return False, None, "UNKNOWN_STADIUM_MODIFIER"
    attacker_type = _enum_int(getattr(attacker_data, "energyType", None))
    weakness = _enum_int(getattr(target_data, "weakness", None))
    resistance = _enum_int(getattr(target_data, "resistance", None))
    if weakness is not None and attacker_type == weakness:
        base *= 2
    if resistance is not None and attacker_type == resistance:
        base = max(0, base - 30)
    target_energy = _enum_int(getattr(target_data, "energyType", None))
    if FULL_METAL_LAB_ID in stadium_ids and target_energy == 8:
        base = max(0, base - 30)
    return True, int(base), "PUBLIC_PRINTED_DAMAGE_PROOF"


def _target_from_option(observation: Mapping[str, Any], option: Mapping[str, Any], opponent_seat: int) -> Mapping[str, Any] | None:
    players = _players(observation)
    player_index = _integer(option.get("playerIndex"))
    area = _integer(option.get("area"))
    index = _integer(option.get("index"))
    if player_index != opponent_seat or index is None or player_index >= len(players):
        return None
    # Engine traces use area 2 for the opponent bench.  If the area field is
    # absent, the public playerIndex plus a valid bench index is still enough.
    bench = players[opponent_seat].get("bench") or []
    if area not in (None, 2):
        return None
    if 0 <= index < len(bench) and isinstance(bench[index], Mapping):
        return bench[index]
    return None


def _same_serial(a: Mapping[str, Any] | None, b: Mapping[str, Any] | None) -> bool:
    if not a or not b:
        return False
    return a.get("serial") is not None and a.get("serial") == b.get("serial")


def run(args: argparse.Namespace) -> dict[str, Any]:
    roots = [json.loads(line) for line in args.roots.read_text(encoding="utf-8").splitlines() if line.strip()]
    root = next((item for item in roots if str(item.get("root_id")) == str(args.root_id)), None)
    if root is None:
        raise SystemExit(f"root not found: {args.root_id}")
    seat = int(root["policy_seat"])
    opponent_seat = 1 - seat
    parent_dir = args.parent_agent.resolve()
    opponent_dir = Path(str(root["opponent_path"])).resolve()
    engine_root = args.engine_dir.resolve()
    seed = int(root["seed"])
    if seat == 0:
        deck_a_dir, deck_b_dir = parent_dir, opponent_dir
    else:
        deck_a_dir, deck_b_dir = opponent_dir, parent_dir
    # Import seeded engine before either packaged agent to prevent local cg
    # compatibility directories from shadowing the requested engine.
    try:
        from cg.game import battle_finish, battle_select, battle_start  # type: ignore
        import cg  # type: ignore
        cg_path = str(Path(getattr(cg, "__file__", "")).resolve())
    except Exception as exc:
        return {"schema_version": "archaludon_boss_vs_front_attack_branch.v1", "root_id": root["root_id"], "branch": args.branch, "status": "INVALID_ENGINE_IMPORT_SHADOW", "started": False, "engine_import_ok": False, "error": f"{type(exc).__name__}: {exc}"}
    engine_import_ok = cg_path == str(engine_root) or cg_path.startswith(str(engine_root) + "\\") or cg_path.startswith(str(engine_root) + "/")
    if not engine_import_ok:
        return {"schema_version": "archaludon_boss_vs_front_attack_branch.v1", "root_id": root["root_id"], "branch": args.branch, "status": "INVALID_ENGINE_IMPORT_SHADOW", "started": False, "engine_import_ok": False, "cg_module_path": cg_path, "engine_root": str(engine_root)}
    deck_a = read_deck(deck_a_dir / "deck.csv")
    deck_b = read_deck(deck_b_dir / "deck.csv")
    agent_a = load_agent(deck_a_dir, f"boss_front_a_{root['root_id']}_{args.branch}")
    agent_b = load_agent(deck_b_dir, f"boss_front_b_{root['root_id']}_{args.branch}")
    agents = [agent_a, agent_b]
    random.seed(seed)
    for agent in agents:
        module_random = getattr(getattr(agent, "module", None), "random", None)
        if hasattr(module_random, "seed"):
            module_random.seed(seed)
    obs, start_data = battle_start(deck_a, deck_b, seed=seed)
    if not obs:
        return {"schema_version": "archaludon_boss_vs_front_attack_branch.v1", "root_id": root["root_id"], "branch": args.branch, "status": "start_fault", "started": False, "engine_import_ok": True, "start_error_type": getattr(start_data, "errorType", None)}

    target_callback = int(root["callback_index"])
    root_turn = int(root.get("turn") or 0)
    steps = 0
    action_errors = 0
    root_match = False
    forced_legal = False
    chosen_root_action: list[int] | None = None
    same_turn_rows: list[dict[str, Any]] = []
    target_card: Mapping[str, Any] | None = None
    target_kind = "FRONT_ACTIVE" if args.branch.startswith("front_") else "BOSS_BENCH" if args.branch == "boss" else "NONE"
    attack_id: int | None = int(args.attack_id) if args.branch.startswith("front_") and args.attack_id else None
    route_attack_id: int | None = attack_id
    attack_before: dict[str, Any] | None = None
    attack_after: dict[str, Any] | None = None
    final_obs = obs
    status = "max_step"
    terminal_same_turn = False
    target_seen = False
    card_db, attack_db = _lookup_metadata()
    root_prizes = _prizes(obs, opponent_seat)
    try:
        while obs and obs.get("select") and steps < args.max_steps:
            current = obs.get("current") or {}
            result = _integer(current.get("result"))
            if result not in (None, -1):
                status = "complete"
                break
            player = _integer(current.get("yourIndex"))
            if player not in (0, 1):
                action_errors += 1; status = "invalid_acting_seat"; break
            try:
                parent_action = list(agents[player](obs))
            except Exception as exc:
                action_errors += 1; status = f"agent_error:{type(exc).__name__}"; break
            if not legal_action(obs, parent_action):
                action_errors += 1; status = "parent_action_illegal"; break
            action = parent_action
            option = _chosen_option(obs, parent_action)
            if steps == target_callback and player == seat:
                actual_hash = normalized_public_hash(obs)
                actual_parent_semantic = _semantic(obs, parent_action)
                actual_legal = sorted(str(item["semantic_id"]) for item in singleton_action_semantics(obs))
                expected_legal = sorted(str(item.get("semantic_id")) for item in root.get("legal_semantic_action_set") or [])
                root_match = actual_hash == str(root["public_hash"]) and actual_parent_semantic == str(root["parent_semantic_action"]) and actual_legal == expected_legal
                if not root_match:
                    status = "root_mismatch"; break
                if args.branch == "boss":
                    forced = list(root["boss_action"])
                    expected_semantic = str(root["boss_semantic_action"])
                elif args.branch.startswith("front_"):
                    forced_row = next((item for item in root.get("front_attacks") or [] if int(item.get("attack_id")) == int(args.attack_id)), None)
                    if forced_row is None:
                        status = "forced_attack_not_in_root"; break
                    forced = list(forced_row["action"])
                    expected_semantic = str(forced_row["semantic_id"])
                else:
                    forced = parent_action; expected_semantic = actual_parent_semantic
                forced_legal = legal_action(obs, forced) and _semantic(obs, forced) == expected_semantic
                if not forced_legal:
                    action_errors += 1; status = "forced_action_illegal"; break
                action = forced
                chosen_root_action = list(action)
                if args.branch.startswith("front_"):
                    target_card = _active(obs, opponent_seat)
            elif steps > target_callback and player == seat and int(current.get("turn") or 0) == root_turn:
                selected = _chosen_option(obs, parent_action)
                if selected is not None and not target_seen:
                    maybe = _target_from_option(obs, selected, opponent_seat)
                    if maybe is not None:
                        target_card = maybe; target_seen = True
                row = {
                    "step": steps,
                    "turn": current.get("turn"),
                    "turnActionCount": current.get("turnActionCount"),
                    "select_context": (obs.get("select") or {}).get("context"),
                    "select_type": (obs.get("select") or {}).get("type"),
                    "chosen_action": parent_action,
                    "chosen_option": dict(selected) if selected is not None else None,
                    "opponent_prizes": _prizes(obs, opponent_seat),
                    "opponent_active": _card_copy(_active(obs, opponent_seat)),
                }
                same_turn_rows.append(row)
                if selected is not None and _integer(selected.get("type")) == ATTACK_TYPE and selected.get("attackId") is not None and route_attack_id is None:
                    route_attack_id = _integer(selected.get("attackId"))
                    attacker = _active(obs, seat)
                    if target_card is None:
                        target_card = _active(obs, opponent_seat)
                    known, damage, reason = _public_damage(route_attack_id, attacker, target_card, obs, card_db, attack_db)
                    attack_before = {"attack_id": route_attack_id, "known": known, "damage": damage, "reason": reason, "attacker": _card_copy(attacker), "target": _card_copy(target_card), "target_kind": target_kind, "opponent_prizes_before": _prizes(obs, opponent_seat)}
            # For a forced front attack the attack occurs at the root callback.
            if steps == target_callback and player == seat and args.branch.startswith("front_"):
                attacker = _active(obs, seat)
                known, damage, reason = _public_damage(route_attack_id, attacker, target_card, obs, card_db, attack_db)
                attack_before = {"attack_id": route_attack_id, "known": known, "damage": damage, "reason": reason, "attacker": _card_copy(attacker), "target": _card_copy(target_card), "target_kind": target_kind, "opponent_prizes_before": _prizes(obs, opponent_seat)}
            obs = battle_select(action)
            final_obs = obs
            steps += 1
            if attack_before is not None and attack_after is None:
                after_result = _integer((obs.get("current") or {}).get("result")) if obs else None
                after_prizes = _prizes(obs, opponent_seat) if obs else None
                if after_result == seat or (after_prizes is not None and root_prizes is not None and after_prizes < root_prizes) or int(steps) > target_callback + 1:
                    attack_after = {"opponent_prizes_after": after_prizes, "terminal_result_after": after_result, "target_still_active": _same_serial(target_card, _active(obs, opponent_seat)) if obs else False, "target_still_bench": any(_same_serial(target_card, card) for card in _bench(obs, opponent_seat)) if obs else False}
            if obs:
                now = (obs.get("current") or {})
                if _integer(now.get("result")) == seat and int(now.get("turn") or 0) == root_turn:
                    terminal_same_turn = True
    finally:
        battle_finish()
    final_current = (final_obs or {}).get("current") or {}
    if status == "max_step" and _integer(final_current.get("result")) not in (None, -1):
        status = "complete"
    if attack_after is None and attack_before is not None:
        attack_after = {"opponent_prizes_after": _prizes(final_obs, opponent_seat) if final_obs else None, "terminal_result_after": _integer(final_current.get("result")), "target_still_active": _same_serial(target_card, _active(final_obs, opponent_seat)) if final_obs else False, "target_still_bench": any(_same_serial(target_card, card) for card in _bench(final_obs, opponent_seat)) if final_obs else False}
    prizes_after = attack_after.get("opponent_prizes_after") if attack_after else None
    prizes_taken = None if root_prizes is None or prizes_after is None else max(0, root_prizes - prizes_after)
    target_present = None
    if attack_after is not None and target_card is not None:
        target_present = bool(attack_after.get("target_still_active") or attack_after.get("target_still_bench"))
    if attack_before is None or attack_after is None or target_card is None:
        actual_ko = None
    elif target_present is False:
        # The public target serial disappeared from both active and bench in
        # the same-turn attack route.  This is a board-state KO proof; it does
        # not use hidden discard/prize contents.
        actual_ko = True
    elif prizes_taken is not None and prizes_taken > 0:
        actual_ko = True
    elif target_present is True:
        actual_ko = False
    else:
        actual_ko = None
    target_prize_value = None
    if target_card is not None:
        data = card_db.get(_integer(target_card.get("id")))
        if data is not None:
            target_prize_value = 3 if bool(getattr(data, "megaEx", False)) else 2 if bool(getattr(data, "ex", False)) else 1
    if actual_ko is True and target_prize_value is not None:
        prizes_taken = target_prize_value
    return {
        "schema_version": "archaludon_boss_vs_front_attack_branch.v1",
        "root_id": root["root_id"],
        "branch": args.branch,
        "forced_attack_id": attack_id,
        "status": status,
        "started": True,
        "root_match": root_match,
        "prefix_match": root_match,
        "forced_legal": forced_legal,
        "chosen_root_action": chosen_root_action,
        "terminal_result": _integer(final_current.get("result")),
        "steps": steps,
        "action_errors": action_errors,
        "hit_max_steps": steps >= args.max_steps and _integer(final_current.get("result")) in (None, -1),
        "engine_import_ok": engine_import_ok,
        "cg_module_path": cg_path,
        "engine_root": str(engine_root),
        "policy_seat": seat,
        "opponent_family": root.get("opponent_family"),
        "opponent_policy_id": root.get("opponent_policy_id"),
        "game": root.get("game"),
        "seed": seed,
        "turn": root_turn,
        "root_parent_category": root.get("parent_action_category"),
        "root_prizes_opponent": root_prizes,
        "target_kind": target_kind,
        "target": _card_copy(target_card),
        "target_prize_value": target_prize_value,
        "route_attack_id": route_attack_id,
        "attack_before": attack_before,
        "attack_after": attack_after,
        "damage_known": attack_before.get("known") if attack_before else False,
        "exact_damage": attack_before.get("damage") if attack_before else None,
        "damage_unknown_reason": attack_before.get("reason") if attack_before and not attack_before.get("known") else None,
        "actual_ko": actual_ko,
        "prizes_taken_same_turn": prizes_taken,
        "terminal_win_same_turn": terminal_same_turn,
        "same_turn_rows": same_turn_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--parent-agent", type=Path, required=True)
    parser.add_argument("--roots", type=Path, required=True)
    parser.add_argument("--root-id", required=True)
    parser.add_argument("--branch", choices=("parent", "boss", "front"), required=True)
    parser.add_argument("--attack-id", type=int)
    parser.add_argument("--max-steps", type=int, default=1000)
    args = parser.parse_args()
    if args.branch == "front" and args.attack_id is None:
        parser.error("--attack-id is required for front branch")
    args.branch = f"front_{args.attack_id}" if args.branch == "front" else args.branch
    ensure_engine_on_path(args.engine_dir.resolve())
    result = run(args)
    print(json.dumps(result, sort_keys=True, ensure_ascii=True), flush=True)
    if result.get("status") != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
