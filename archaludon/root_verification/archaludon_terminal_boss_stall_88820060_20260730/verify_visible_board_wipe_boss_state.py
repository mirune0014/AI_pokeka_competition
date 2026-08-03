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
    / "refresh_20260730_0001"
    / "episode_88820060_replay.json"
)
EXPECTED_PARENT_SHA256 = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
EXPECTED_REPLAY_SHA256 = (
    "A8D809345105B9856C39CB6156655AA4E392C2578C7B73F70F781DCBC6B83985"
)
TARGET_SEAT = 0
TARGET_ROW = 53
TERMINAL_LOG_ROW = 64
BOSS_ID = 1182


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
        "appear_this_turn": card.get("appearThisTurn"),
    }


def main() -> None:
    parent_hash = sha256(PARENT / "main.py")
    replay_hash = sha256(REPLAY)
    if parent_hash != EXPECTED_PARENT_SHA256:
        raise AssertionError(("parent hash", parent_hash))
    if replay_hash != EXPECTED_REPLAY_SHA256:
        raise AssertionError(("replay hash", replay_hash))

    sys.path.insert(0, str(PARENT))
    parent = load_module("root_board_wipe_boss_parent", PARENT / "main.py")
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
            "stadium_id": (
                None
                if not current["stadium"]
                else (
                    current["stadium"][0]["id"]
                    if isinstance(current["stadium"], list)
                    else current["stadium"]["id"]
                )
            ),
            "own_prizes_remaining": len(own["prize"]),
            "opponent_prizes_remaining": len(opponent["prize"]),
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
    if target["parent_selected_positions"] != [1]:
        raise AssertionError(target["parent_selected_positions"])
    if by_position[0]["card_id"] != BOSS_ID:
        raise AssertionError(by_position[0])
    if by_position[0]["score"] >= by_position[1]["score"]:
        raise AssertionError((by_position[0], by_position[1]))

    terminal_logs = replay["steps"][TERMINAL_LOG_ROW][1]["observation"]["logs"]
    attack_logs = [log for log in terminal_logs if log.get("attackId") == 983]
    damage_logs = [
        log
        for log in terminal_logs
        if log.get("playerIndex") == TARGET_SEAT
        and log.get("cardId") == 840
        and log.get("value") == -240
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
            "attack_id": 983,
            "damage_after_public_stadium": 240,
            "board_out": True,
        },
        "verified": {
            "own_board_has_only_active": not target["own_bench"],
            "supporter_unplayed": not target["supporter_played"],
            "full_metal_lab_public": target["stadium_id"] == 1244,
            "parent_selected_end": True,
            "boss_visible_but_scored_negative": by_position[0]["score"] < 0,
            "opponent_active_mega_lucario_two_energy": (
                target["opponent_active"][0]["id"] == 678
                and len(target["opponent_active"][0]["energy_ids"]) == 2
            ),
            "zero_energy_makuhita_public": [
                {
                    "id": card["id"],
                    "serial": card["serial"],
                    "hp": card["hp"],
                }
                for card in target["opponent_bench"]
                if card["id"] == 673 and not card["energy_ids"]
            ],
        },
        "scope_limit": (
            "This proves a visible board-wipe threat and a legal Boss play "
            "that can expose zero-Energy Makuhita. It does not prove absence "
            "of hidden switch, attachment, acceleration, or later recovery, "
            "and does not prove eventual victory."
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
