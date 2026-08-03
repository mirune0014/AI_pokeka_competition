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
    / "refresh_20260730_0059"
    / "episode_88826681_replay.json"
)
EXPECTED_PARENT_SHA256 = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
EXPECTED_REPLAY_SHA256 = (
    "ED58D8FB1B7E8D7E0C4603AB5DC86DAC569185D66C192FD5CB39E98765A46282"
)
TARGET_SEAT = 1
BOSS_ROW = 135
TARGET_ROW = 136
ARCHALUDON_EX_ID = 190
CINDERACE_ID = 666
DURALUDON_ID = 169
BOSS_ID = 1182
FULL_METAL_LAB_ID = 1244
METAL_DEFENDER_ID = 253


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_module(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def raw_card(card: dict) -> dict:
    return {
        "id": card.get("id"),
        "serial": card.get("serial"),
        "hp": card.get("hp"),
        "max_hp": card.get("maxHp"),
        "energy_ids": list(card.get("energies") or []),
        "tool_ids": [item.get("id") for item in card.get("tools") or []],
    }


def describe_option(module, parsed, position: int) -> dict:
    option = parsed.select.option[position]
    card = module.option_card(parsed, option)
    target = module.option_target(parsed, option)
    effective_target = target if target is not None else card
    score, reason = module.score_option(parsed, option)
    return {
        "position": position,
        "type": int(option.type),
        "attack_id": getattr(option, "attackId", None),
        "card_id": getattr(card, "id", None),
        "card_serial": getattr(card, "serial", None),
        "target_id": getattr(effective_target, "id", None),
        "target_serial": getattr(effective_target, "serial", None),
        "target_hp": getattr(effective_target, "hp", None),
        "score": score,
        "reason": reason,
    }


def main() -> None:
    parent_hash = sha256(PARENT / "main.py")
    replay_hash = sha256(REPLAY)
    if parent_hash != EXPECTED_PARENT_SHA256:
        raise AssertionError(("parent hash", parent_hash))
    if replay_hash != EXPECTED_REPLAY_SHA256:
        raise AssertionError(("replay hash", replay_hash))

    sys.path.insert(0, str(PARENT))
    parent = load_module("root_nonterminal_boss_parent", PARENT / "main.py")
    parent._opp_last_attack_id = None
    parent._cur_turn_logs.clear()
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))

    captured: dict[int, dict] = {}
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
        if not parsed.select.option:
            continue
        selected = parent.choose_options(parsed)
        if row not in {BOSS_ROW, TARGET_ROW}:
            continue
        current = observation["current"]
        own = current["players"][TARGET_SEAT]
        opponent = current["players"][1 - TARGET_SEAT]
        stadium = current["stadium"]
        captured[row] = {
            "row": row,
            "turn": current["turn"],
            "turn_action_count": current["turnActionCount"],
            "context": int(parsed.select.context),
            "parent_selected_positions": selected,
            "next_recorded_action": replay["steps"][row + 1][TARGET_SEAT].get(
                "action"
            ),
            "own_prizes_remaining": len(own["prize"]),
            "opponent_prizes_remaining": len(opponent["prize"]),
            "stadium_id": (
                None
                if not stadium
                else (
                    stadium[0]["id"]
                    if isinstance(stadium, list)
                    else stadium["id"]
                )
            ),
            "own_active": [raw_card(card) for card in own["active"]],
            "own_bench": [raw_card(card) for card in own["bench"]],
            "opponent_active": [raw_card(card) for card in opponent["active"]],
            "opponent_bench": [raw_card(card) for card in opponent["bench"]],
            "options": [
                describe_option(parent, parsed, position)
                for position in range(len(parsed.select.option))
            ],
        }

    if set(captured) != {BOSS_ROW, TARGET_ROW}:
        raise AssertionError(sorted(captured))
    boss = captured[BOSS_ROW]
    target = captured[TARGET_ROW]
    if (
        boss["parent_selected_positions"] != [1]
        or boss["next_recorded_action"] != [1]
        or boss["own_prizes_remaining"] != 2
        or boss["opponent_prizes_remaining"] != 2
        or boss["stadium_id"] != FULL_METAL_LAB_ID
    ):
        raise AssertionError(boss)
    if (
        boss["options"][1]["card_id"] != BOSS_ID
        or boss["options"][1]["score"] != 4300
        or boss["options"][2]["attack_id"] != METAL_DEFENDER_ID
        or boss["options"][2]["score"] != 220
    ):
        raise AssertionError(boss["options"])
    if (
        len(boss["own_active"]) != 1
        or boss["own_active"][0]["id"] != ARCHALUDON_EX_ID
        or boss["own_active"][0]["hp"] != 300
        or len(boss["own_active"][0]["energy_ids"]) != 3
        or len(boss["opponent_active"]) != 1
        or boss["opponent_active"][0]["id"] != ARCHALUDON_EX_ID
        or boss["opponent_active"][0]["hp"] != 300
        or len(boss["opponent_active"][0]["energy_ids"]) != 3
    ):
        raise AssertionError((boss["own_active"], boss["opponent_active"]))

    if (
        target["parent_selected_positions"] != [0]
        or target["next_recorded_action"] != [0]
        or [row["target_id"] for row in target["options"]]
        != [CINDERACE_ID, DURALUDON_ID]
        or len({row["score"] for row in target["options"]}) != 1
        or target["options"][0]["score"] != 23100
    ):
        raise AssertionError(target)

    ko_logs = replay["steps"][138][TARGET_SEAT]["observation"]["logs"]
    if not (
        any(log.get("attackId") == METAL_DEFENDER_ID for log in ko_logs)
        and any(
            log.get("cardId") == CINDERACE_ID
            and log.get("serial") == 23
            and log.get("value") == -220
            for log in ko_logs
        )
    ):
        raise AssertionError(ko_logs)

    mirror_return_logs = replay["steps"][153][TARGET_SEAT]["observation"]["logs"]
    if not (
        any(log.get("attackId") == METAL_DEFENDER_ID for log in mirror_return_logs)
        and any(
            log.get("cardId") == ARCHALUDON_EX_ID
            and log.get("serial") == 67
            and log.get("value") == -190
            for log in mirror_return_logs
        )
    ):
        raise AssertionError(mirror_return_logs)

    result = {
        "episode": replay["info"]["EpisodeId"],
        "target_seat": TARGET_SEAT,
        "target_reward": replay["rewards"][TARGET_SEAT],
        "parent_sha256": parent_hash,
        "replay_sha256": replay_hash,
        "captured": captured,
        "verified": {
            "two_prizes_each_at_decision": True,
            "both_active_archaludon_full_300_three_metal": True,
            "full_metal_lab_public": True,
            "visible_mirror_damage": 190,
            "current_active_survives_visible_return_at": 110,
            "boss_only_one_prize_targets": True,
            "parent_bossed_cinderace": True,
            "observed_one_prize_ko_damage": 220,
            "observed_later_return_damage": 190,
            "retaining_boss_and_attacking_active_was_legal": True,
        },
        "scope_limit": (
            "This proves the public two-hit race, same-Prize Boss targets, "
            "and the parent's non-terminal one-Prize diversion. It does not "
            "prove the alternate wins because healing, protection, retreat, "
            "draw, and disruption can change after the branch."
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
