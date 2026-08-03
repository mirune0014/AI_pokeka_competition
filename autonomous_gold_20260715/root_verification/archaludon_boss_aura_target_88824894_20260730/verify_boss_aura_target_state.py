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
    / "analysis_outputs"
    / "reference_agents"
    / "historical_silver_archaludon_54495224"
)
REPLAY = (
    ROOT
    / "autonomous_gold_20260715"
    / "live"
    / "55083165"
    / "refresh_20260730_0037"
    / "episode_88824894_replay.json"
)
EXPECTED_PARENT_SHA256 = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
EXPECTED_REPLAY_SHA256 = (
    "330650CEE9D1BE07F759245325982E8810777775F56A336622D721697F5FF6A0"
)
TARGET_SEAT = 0
TARGET_ROW = 79
TERMINAL_LOG_ROW = 142
GABITE_ID = 380
ROSERADE_ID = 342
DRACONIC_BUSTER_ID = 532


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
    target = module.option_target(parsed, option)
    effective_target = target if target is not None else card
    score, reason = module.score_option(parsed, option)
    return {
        "position": position,
        "type": int(option.type),
        "card_id": getattr(card, "id", None),
        "card_serial": getattr(card, "serial", None),
        "target_id": getattr(effective_target, "id", None),
        "target_serial": getattr(effective_target, "serial", None),
        "target_hp": getattr(effective_target, "hp", None),
        "target_max_hp": getattr(effective_target, "maxHp", None),
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
    parent = load_module("root_boss_aura_parent", PARENT / "main.py")
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
        stadium = current["stadium"]
        target = {
            "row": row,
            "turn": current["turn"],
            "turn_action_count": current["turnActionCount"],
            "context": int(parsed.select.context),
            "parent_selected_positions": selected,
            "next_recorded_action": replay["steps"][row + 1][TARGET_SEAT].get(
                "action"
            ),
            "stadium_id": (
                None
                if not stadium
                else (
                    stadium[0]["id"]
                    if isinstance(stadium, list)
                    else stadium["id"]
                )
            ),
            "own_prizes_remaining": len(own["prize"]),
            "opponent_prizes_remaining": len(opponent["prize"]),
            "own_active": [raw_card(card) for card in own["active"]],
            "opponent_active": [raw_card(card) for card in opponent["active"]],
            "opponent_bench": [raw_card(card) for card in opponent["bench"]],
            "options": options,
        }
        break

    if target is None:
        raise AssertionError("target row not found")
    if target["parent_selected_positions"] != [0]:
        raise AssertionError(target["parent_selected_positions"])
    if len(target["options"]) != 4:
        raise AssertionError(target["options"])
    if target["options"][0]["target_id"] != GABITE_ID:
        raise AssertionError(target["options"][0])
    if [row["target_id"] for row in target["options"][1:]] != [
        ROSERADE_ID,
        ROSERADE_ID,
        ROSERADE_ID,
    ]:
        raise AssertionError(target["options"])
    if len({row["score"] for row in target["options"]}) != 1:
        raise AssertionError(target["options"])

    terminal_logs = replay["steps"][TERMINAL_LOG_ROW][1]["observation"]["logs"]
    attack_logs = [
        log
        for log in terminal_logs
        if log.get("attackId") == DRACONIC_BUSTER_ID
    ]
    damage_logs = [
        log
        for log in terminal_logs
        if log.get("playerIndex") == TARGET_SEAT
        and log.get("cardId") == 190
        and log.get("value") == -320
    ]
    if not attack_logs or not damage_logs:
        raise AssertionError(terminal_logs)

    result = {
        "episode": replay["info"]["EpisodeId"],
        "target_seat": TARGET_SEAT,
        "target_reward": replay["rewards"][TARGET_SEAT],
        "parent_sha256": parent_hash,
        "replay_sha256": replay_hash,
        "target": target,
        "observed_terminal": {
            "row": TERMINAL_LOG_ROW,
            "attack_id": DRACONIC_BUSTER_ID,
            "damage": 320,
            "three_roserade_public_at_target_row": True,
            "public_damage_formula": {
                "base": 260,
                "three_roserade": 90,
                "full_metal_lab": -30,
                "total": 320,
            },
            "one_roserade_removed_projection": 290,
        },
        "verified": {
            "all_targets_same_parent_score": target["options"][0]["score"],
            "parent_tie_broke_to_gabite": True,
            "three_legal_roserade_alternates": True,
            "all_four_targets_within_metal_defender_220": all(
                row["target_hp"] <= 220 for row in target["options"]
            ),
            "all_targets_one_prize": True,
        },
        "scope_limit": (
            "This proves a public tied Boss target choice and the observed "
            "three-Roserade 320-damage terminal. The fresh 300-HP Archaludon "
            "at the terminal row was not public at the Boss row, and removing "
            "Roserade may leave a future Gabite/Garchomp route. This supports "
            "future-board target valuation, not a certified match win."
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
