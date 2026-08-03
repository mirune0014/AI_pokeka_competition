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
H5V2 = (
    ROOT
    / "archaludon"
    / "candidates"
    / "archaludon_public_lethal_active_no_ready_successor_nonex_120_ko_v2"
)
REPLAY = (
    ROOT
    / "archaludon"
    / "live"
    / "55083165"
    / "refresh_20260730_0052"
    / "episode_88825590_replay.json"
)
EXPECTED_PARENT_SHA256 = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
EXPECTED_REPLAY_SHA256 = (
    "E80A121C57B0CCA51C6ABBCD5070B6437145185AE41FC502C64709269280F4AC"
)
EXPECTED_H5V2_SHA256 = (
    "E493C692198FE3699269F3CAFECD3010815DDE5EA2B3002321DDE109F9566798"
)
TARGET_SEAT = 0
TARGET_ROW = 59
DURALUDON_ID = 169
NONEX_ARCHALUDON_ID = 840
ALAKAZAM_ID = 743
HERO_CAPE_ID = 1159
RAGING_HAMMER_ID = 224
COATED_ATTACK_ID = 1212


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
    score, reason = module.score_option(parsed, option)
    return {
        "position": position,
        "type": int(option.type),
        "attack_id": getattr(option, "attackId", None),
        "card_id": getattr(card, "id", None),
        "card_serial": getattr(card, "serial", None),
        "target_id": getattr(target, "id", None),
        "target_serial": getattr(target, "serial", None),
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
    h5v2_hash = sha256(H5V2 / "main.py")
    if parent_hash != EXPECTED_PARENT_SHA256:
        raise AssertionError(("parent hash", parent_hash))
    if replay_hash != EXPECTED_REPLAY_SHA256:
        raise AssertionError(("replay hash", replay_hash))
    if h5v2_hash != EXPECTED_H5V2_SHA256:
        raise AssertionError(("H5 v2 hash", h5v2_hash))

    sys.path.insert(0, str(PARENT))
    parent = load_module("root_cape_nonex_parent", PARENT / "main.py")
    sys.path.insert(0, str(H5V2))
    h5v2 = load_module("root_cape_nonex_h5v2", H5V2 / "main.py")
    parent._opp_last_attack_id = None
    parent._cur_turn_logs.clear()
    h5v2._h5v2_reset()
    h5v2._opp_last_attack_id = None
    h5v2._cur_turn_logs.clear()
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
        h5v2_parsed = h5v2.to_observation_class(copy.deepcopy(observation))
        h5v2._update_opp_attack_tracking(h5v2_parsed)
        if row != TARGET_ROW:
            if parsed.select.option:
                parent.choose_options(parsed)
                h5v2.choose_options(h5v2_parsed)
            continue

        current = observation["current"]
        own = current["players"][TARGET_SEAT]
        opponent = current["players"][1 - TARGET_SEAT]
        target = {
            "row": row,
            "turn": current["turn"],
            "turn_action_count": current["turnActionCount"],
            "energy_attached": bool(current["energyAttached"]),
            "context": int(parsed.select.context),
            "parent_selected_positions": parent.choose_options(parsed),
            "h5v2_selected_positions": h5v2.choose_options(h5v2_parsed),
            "next_recorded_action": replay["steps"][row + 1][TARGET_SEAT].get(
                "action"
            ),
            "own_prizes_remaining": len(own["prize"]),
            "opponent_prizes_remaining": len(opponent["prize"]),
            "own_active": [raw_card(card) for card in own["active"]],
            "opponent_active": [raw_card(card) for card in opponent["active"]],
            "hand_cards": [
                {"id": card.get("id"), "serial": card.get("serial")}
                for card in own["hand"]
            ],
            "options": [
                describe_option(parent, parsed, position)
                for position in range(len(parsed.select.option))
            ],
        }
        break

    if target is None:
        raise AssertionError("target row not found")
    if target["parent_selected_positions"] != [3]:
        raise AssertionError(target["parent_selected_positions"])
    if target["next_recorded_action"] != [3]:
        raise AssertionError(target["next_recorded_action"])
    if target["h5v2_selected_positions"] != [3]:
        raise AssertionError(target["h5v2_selected_positions"])
    active = target["own_active"]
    if len(active) != 1 or active[0]["id"] != DURALUDON_ID:
        raise AssertionError(active)
    if len(active[0]["energy_ids"]) != 3:
        raise AssertionError(active)
    if HERO_CAPE_ID not in active[0]["tool_ids"]:
        raise AssertionError(active)
    if not any(
        card["id"] == NONEX_ARCHALUDON_ID and card["serial"] == 32
        for card in target["hand_cards"]
    ):
        raise AssertionError(target["hand_cards"])
    opponent_active = target["opponent_active"]
    if (
        len(opponent_active) != 1
        or opponent_active[0]["id"] != ALAKAZAM_ID
        or opponent_active[0]["hp"] != 110
    ):
        raise AssertionError(opponent_active)

    evolution = target["options"][1]
    raging_hammer = target["options"][3]
    if evolution["card_id"] != NONEX_ARCHALUDON_ID:
        raise AssertionError(evolution)
    if raging_hammer["attack_id"] != RAGING_HAMMER_ID:
        raise AssertionError(raging_hammer)

    next_logs = replay["steps"][TARGET_ROW + 1][1]["observation"]["logs"]
    attack_logs = [
        log for log in next_logs if log.get("attackId") == RAGING_HAMMER_ID
    ]
    damage_logs = [
        log
        for log in next_logs
        if log.get("cardId") == ALAKAZAM_ID
        and log.get("serial") == 86
        and log.get("value") == -80
    ]
    if not attack_logs or not damage_logs:
        raise AssertionError(next_logs)

    result = {
        "episode": replay["info"]["EpisodeId"],
        "target_seat": TARGET_SEAT,
        "target_reward": replay["rewards"][TARGET_SEAT],
        "parent_sha256": parent_hash,
        "h5v2_sha256": h5v2_hash,
        "replay_sha256": replay_hash,
        "target": target,
        "verified": {
            "public_current_attack_damage": 80,
            "public_current_attack_non_ko": True,
            "legal_nonex_evolution_position": 1,
            "existing_h5v2_remains_parent_identical": True,
            "existing_h5v2_energy_attached_guard_applies": (
                target["energy_attached"]
            ),
            "three_metal_pay_coated_attack": True,
            "coated_attack_id": COATED_ATTACK_ID,
            "coated_attack_damage": 120,
            "visible_alakazam_hp": 110,
            "coated_attack_visible_ko": True,
            "same_one_prize_liability": True,
            "cape_max_hp_projection_after_evolution": 280,
        },
        "scope_limit": (
            "This proves the legal evolution, current non-KO, and immediate "
            "public 120-damage KO conversion. It does not prove the changed "
            "promotion, draw, or later match result, and it does not permit "
            "a general non-ex Archaludon evolution rule."
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
