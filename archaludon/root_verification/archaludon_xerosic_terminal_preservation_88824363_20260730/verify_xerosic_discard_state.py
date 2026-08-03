from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
PARENT = (
    ROOT
     / "_local_generated" / "analysis_outputs"
    / "reference_agents"
    / "historical_silver_archaludon_54495224"
)
REPLAY = (
    ROOT
    / "archaludon"
    / "live"
    / "55083165"
    / "refresh_20260730_0037"
    / "episode_88824363_replay.json"
)
EXPECTED_PARENT_SHA256 = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
EXPECTED_REPLAY_SHA256 = (
    "3ED067AE3FF43C3696939E9673DF23C74CE52CD584E3E2272179F4B7E5CC0FF6"
)
TARGET_SEAT = 0
TARGET_ROW = 112
ULTRA_BALL_ID = 1121
ICE_CREAM_ID = 1147
BOSS_ID = 1182
HERO_CAPE_ID = 1159


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def describe_option(module, parsed, position: int) -> dict:
    option = parsed.select.option[position]
    card = module.option_card(parsed, option)
    score, reason = module.score_option(parsed, option)
    return {
        "position": position,
        "type": int(option.type),
        "card_id": getattr(card, "id", None),
        "card_serial": getattr(card, "serial", None),
        "score": score,
        "reason": reason,
    }


def raw_card(card: dict) -> dict:
    return {
        "id": card.get("id"),
        "serial": card.get("serial"),
        "hp": card.get("hp"),
        "max_hp": card.get("maxHp"),
        "energy_ids": list(card.get("energies") or []),
        "tool_ids": [item.get("id") for item in card.get("tools") or []],
    }


def main() -> None:
    parent_hash = sha256(PARENT / "main.py")
    replay_hash = sha256(REPLAY)
    if parent_hash != EXPECTED_PARENT_SHA256:
        raise AssertionError(("parent hash", parent_hash))
    if replay_hash != EXPECTED_REPLAY_SHA256:
        raise AssertionError(("replay hash", replay_hash))

    sys.path.insert(0, str(PARENT))
    parent = load_module("root_xerosic_parent", PARENT / "main.py")
    parent._opp_last_attack_id = None
    parent._cur_turn_logs.clear()
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))

    target: dict | None = None
    for row, step in enumerate(replay["steps"]):
        record = step[TARGET_SEAT]
        observation = record.get("observation")
        if (
            record.get("status") != "ACTIVE"
            or not observation
            or not observation.get("select")
        ):
            continue
        parsed = parent.to_observation_class(copy.deepcopy(observation))
        parent._update_opp_attack_tracking(parsed)
        if row != TARGET_ROW:
            if parsed.select.option:
                parent.choose_options(parsed)
            continue

        current = observation["current"]
        own = current["players"][TARGET_SEAT]
        opponent = current["players"][1 - TARGET_SEAT]
        options = [
            describe_option(parent, parsed, position)
            for position in range(len(parsed.select.option))
        ]
        selected = parent.choose_options(parsed)
        target = {
            "row": row,
            "turn": current["turn"],
            "turn_action_count": current["turnActionCount"],
            "your_index": current["yourIndex"],
            "first_player": current["firstPlayer"],
            "turn_player": (
                current["firstPlayer"]
                if current["turn"] % 2 == 1
                else 1 - current["firstPlayer"]
            ),
            "context": int(parsed.select.context),
            "min_count": parsed.select.minCount,
            "max_count": parsed.select.maxCount,
            "parent_selected_positions": selected,
            "next_recorded_action": replay["steps"][row + 1][TARGET_SEAT].get(
                "action"
            ),
            "own_prizes_remaining": len(own["prize"]),
            "opponent_prizes_remaining": len(opponent["prize"]),
            "opponent_hand_count": opponent["handCount"],
            "own_active": [raw_card(card) for card in own["active"]],
            "own_bench": [raw_card(card) for card in own["bench"]],
            "opponent_active": [raw_card(card) for card in opponent["active"]],
            "opponent_bench": [raw_card(card) for card in opponent["bench"]],
            "options": options,
        }
        break

    if target is None:
        raise AssertionError("target row not found")
    by_position = {row["position"]: row for row in target["options"]}
    expected_ids = {
        0: ULTRA_BALL_ID,
        1: ULTRA_BALL_ID,
        2: ICE_CREAM_ID,
        3: BOSS_ID,
        4: HERO_CAPE_ID,
    }
    for position, card_id in expected_ids.items():
        if by_position[position]["card_id"] != card_id:
            raise AssertionError((position, by_position[position]))
    if set(target["parent_selected_positions"]) != {0, 3}:
        raise AssertionError(target["parent_selected_positions"])

    result = {
        "episode": replay["info"]["EpisodeId"],
        "target_seat": TARGET_SEAT,
        "target_reward": replay["rewards"][TARGET_SEAT],
        "parent_sha256": parent_hash,
        "replay_sha256": replay_hash,
        "target": target,
        "verified": {
            "opponent_turn_forced_discard": (
                target["turn_player"] == 1 - TARGET_SEAT
            ),
            "mandatory_two_card_discard": (
                target["min_count"] == 2 and target["max_count"] == 2
            ),
            "two_prizes_remaining": target["own_prizes_remaining"] == 2,
            "parent_discarded_boss_and_ultra_ball": True,
            "legal_structural_alternate_ice_cream_and_cape": [2, 4],
            "public_two_prize_fez_target": [
                {
                    "id": card["id"],
                    "serial": card["serial"],
                    "hp": card["hp"],
                }
                for card in target["opponent_bench"]
                if card["id"] == 140
            ],
            "opponent_active_alakazam": (
                target["opponent_active"][0]["id"] == 743
            ),
        },
        "scope_limit": (
            "This proves the forced-discard choice, retained-card alternative, "
            "two-Prize Fez target, and public Alakazam threat. It does not "
            "prove the complete post-KO search/evolve/Alloy/retreat/Boss "
            "counterfactual; that requires a checked engine transaction."
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
