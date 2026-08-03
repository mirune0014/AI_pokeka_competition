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
    / "autonomous_gold_20260715"
    / "live"
    / "55083165"
    / "refresh_20260730_0001"
    / "episode_88819392_replay.json"
)
EXPECTED_PARENT_SHA256 = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
EXPECTED_REPLAY_SHA256 = (
    "4D625ADF892F1D0DC1453E31219025A96C4474D509E5B1E36819225A22F22698"
)
TARGET_SEAT = 0
TARGET_ROW = 120
BOSS_ID = 1182
NONEX_ARCHALUDON_ID = 840
METAL_ID = 8
ARCHALUDON_EX_ID = 190


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
    parent = load_module("root_last_boss_parent", PARENT / "main.py")
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
            "context": int(parsed.select.context),
            "min_count": parsed.select.minCount,
            "max_count": parsed.select.maxCount,
            "parent_selected_positions": selected,
            "next_recorded_action": replay["steps"][row + 1][TARGET_SEAT].get(
                "action"
            ),
            "own_prizes_remaining": len(own["prize"]),
            "opponent_prizes_remaining": len(opponent["prize"]),
            "own_active": [raw_card(card) for card in own["active"]],
            "own_bench": [raw_card(card) for card in own["bench"]],
            "opponent_active": [raw_card(card) for card in opponent["active"]],
            "opponent_bench": [raw_card(card) for card in opponent["bench"]],
            "public_boss_in_discard": [
                {"id": card["id"], "serial": card["serial"]}
                for card in own["discard"]
                if card["id"] == BOSS_ID
            ],
            "public_boss_in_hand": [
                {"id": card["id"], "serial": card["serial"]}
                for card in own["hand"]
                if card["id"] == BOSS_ID
            ],
            "options": options,
        }
        break

    if target is None:
        raise AssertionError("target row not found")
    by_position = {row["position"]: row for row in target["options"]}
    expected_ids = {
        0: BOSS_ID,
        1: NONEX_ARCHALUDON_ID,
        2: METAL_ID,
        3: ARCHALUDON_EX_ID,
    }
    for position, card_id in expected_ids.items():
        if by_position[position]["card_id"] != card_id:
            raise AssertionError((position, by_position[position]))
    if set(target["parent_selected_positions"]) != {0, 2}:
        raise AssertionError(target["parent_selected_positions"])
    if len(target["public_boss_in_discard"]) != 3:
        raise AssertionError(target["public_boss_in_discard"])
    if len(target["public_boss_in_hand"]) != 1:
        raise AssertionError(target["public_boss_in_hand"])

    result = {
        "episode": replay["info"]["EpisodeId"],
        "target_seat": TARGET_SEAT,
        "target_reward": replay["rewards"][TARGET_SEAT],
        "parent_sha256": parent_hash,
        "replay_sha256": replay_hash,
        "target": target,
        "verified": {
            "mandatory_two_card_discard": (
                target["min_count"] == 2 and target["max_count"] == 2
            ),
            "three_boss_already_public_discard": True,
            "last_public_boss_is_option_zero": True,
            "parent_discarded_last_public_boss_and_metal": True,
            "legal_structural_alternate_nonex_and_metal": [1, 2],
            "visible_one_prize_bench_targets": [
                {
                    "id": card["id"],
                    "serial": card["serial"],
                    "hp": card["hp"],
                }
                for card in target["opponent_bench"]
                if card["id"] in (104, 112)
            ],
        },
        "scope_limit": (
            "This proves a public last-Boss access transition and a legal "
            "alternative discard pair. It does not prove later Boss draw or "
            "match conversion; the replay later used Unfair Stamp."
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
