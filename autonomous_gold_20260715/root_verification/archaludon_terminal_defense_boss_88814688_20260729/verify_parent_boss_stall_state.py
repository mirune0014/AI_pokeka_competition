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
    / "refresh_20260729_2325"
    / "episode_88814688_replay.json"
)
EXPECTED_PARENT_SHA256 = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
EXPECTED_REPLAY_SHA256 = (
    "859A887084258D61DCAF372658FA2A20FC1D3A36B537DC004215CEBF24823F80"
)
TARGET_SEAT = 1
TARGET_ROW = 88


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
        "card_id": getattr(card, "id", None),
        "card_serial": getattr(card, "serial", None),
        "target_id": getattr(target, "id", None),
        "target_serial": getattr(target, "serial", None),
        "attack_id": option.attackId,
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
    parent = load_module("root_terminal_defense_parent", PARENT / "main.py")
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
            "parent_selected_positions": selected,
            "next_recorded_action": replay["steps"][row + 1][TARGET_SEAT].get(
                "action"
            ),
            "supporter_played": current["supporterPlayed"],
            "own_prizes_remaining": len(own["prize"]),
            "opponent_prizes_remaining": len(opponent["prize"]),
            "own_active": [raw_card(card) for card in own["active"]],
            "own_bench": [raw_card(card) for card in own["bench"]],
            "opponent_active": [raw_card(card) for card in opponent["active"]],
            "opponent_bench": [raw_card(card) for card in opponent["bench"]],
            "opponent_hand_count": opponent["handCount"],
            "options": options,
        }
        break

    if target is None:
        raise AssertionError("target row not found")
    by_position = {row["position"]: row for row in target["options"]}
    if target["parent_selected_positions"] != [1]:
        raise AssertionError(target["parent_selected_positions"])
    if by_position[0]["card_id"] != 1182:
        raise AssertionError(by_position[0])
    if by_position[1]["card_id"] != 1227:
        raise AssertionError(by_position[1])
    if by_position[0]["score"] >= by_position[1]["score"]:
        raise AssertionError((by_position[0], by_position[1]))

    result = {
        "episode": replay["info"]["EpisodeId"],
        "target_seat": TARGET_SEAT,
        "target_reward": replay["rewards"][TARGET_SEAT],
        "parent_sha256": parent_hash,
        "replay_sha256": replay_hash,
        "target": target,
        "verified": {
            "opponent_one_prize_remaining": (
                target["opponent_prizes_remaining"] == 1
            ),
            "our_board_has_no_bench": not target["own_bench"],
            "supporter_unplayed": not target["supporter_played"],
            "parent_selected_lillie": True,
            "boss_visible_in_hand_but_scored_negative": (
                by_position[0]["score"] < 0
            ),
            "opponent_active_alakazam_ready": (
                target["opponent_active"][0]["id"] == 743
                and len(target["opponent_active"][0]["energy_ids"]) >= 1
            ),
            "opponent_bench_abra_unenergized": (
                len(target["opponent_bench"]) == 1
                and target["opponent_bench"][0]["id"] == 741
                and not target["opponent_bench"][0]["energy_ids"]
            ),
        },
        "scope_limit": (
            "Boss would move the public lethal attacker, but this replay does "
            "not prove that hidden attachment or switch access is absent. "
            "This is a defensive-access hypothesis, not a certified win."
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
