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
    / "maturity_20260730_0127"
    / "episode_88827776_replay.json"
)
EXPECTED_PARENT_SHA256 = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
EXPECTED_REPLAY_SHA256 = (
    "7B3D23A6F04179A10E6B972033D8D84151FDBD81FB6D6AB47AC3D6129DBADD8A"
)
TARGET_SEAT = 1
PRIMARY_ROW = 134
BOSS_TARGET_ROW = 135
ULTRA_BALL_ROW = 136
SEARCH_ROW = 138
EVOLVE_ROW = 139
ATTACK_ROW = 147
DURALUDON_ID = 169
ARCHALUDON_EX_ID = 190
MEGA_LUCARIO_EX_ID = 678
SOLROCK_ID = 676
ULTRA_BALL_ID = 1121
BOSS_ID = 1182
HERO_CAPE_ID = 1159
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
        "appear_this_turn": card.get("appearThisTurn"),
        "mega_ex": card.get("megaEx"),
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
    parent = load_module("root_search_terminal_parent", PARENT / "main.py")
    parent._opp_last_attack_id = None
    parent._cur_turn_logs.clear()
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))

    target_rows = {
        PRIMARY_ROW,
        BOSS_TARGET_ROW,
        ULTRA_BALL_ROW,
        SEARCH_ROW,
        EVOLVE_ROW,
        ATTACK_ROW,
    }
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
        if row not in target_rows:
            continue
        current = observation["current"]
        own = current["players"][TARGET_SEAT]
        opponent = current["players"][1 - TARGET_SEAT]
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
            "supporter_played": bool(current["supporterPlayed"]),
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

    if set(captured) != target_rows:
        raise AssertionError(sorted(captured))
    primary = captured[PRIMARY_ROW]
    boss_target = captured[BOSS_TARGET_ROW]
    ultra_ball = captured[ULTRA_BALL_ROW]
    search = captured[SEARCH_ROW]
    evolve = captured[EVOLVE_ROW]
    attack = captured[ATTACK_ROW]

    if (
        primary["parent_selected_positions"] != [0]
        or primary["next_recorded_action"] != [0]
        or primary["own_prizes_remaining"] != 3
        or primary["opponent_prizes_remaining"] != 2
    ):
        raise AssertionError(primary)
    own_active = primary["own_active"]
    opponent_active = primary["opponent_active"]
    if (
        len(own_active) != 1
        or own_active[0]["id"] != DURALUDON_ID
        or own_active[0]["serial"] != 66
        or own_active[0]["hp"] != 130
        or own_active[0]["appear_this_turn"] is not False
        or len(own_active[0]["energy_ids"]) != 3
    ):
        raise AssertionError(own_active)
    if (
        len(opponent_active) != 1
        or opponent_active[0]["id"] != MEGA_LUCARIO_EX_ID
        or opponent_active[0]["serial"] != 16
        or opponent_active[0]["hp"] != 220
        or opponent_active[0]["max_hp"] != 440
        or HERO_CAPE_ID not in opponent_active[0]["tool_ids"]
    ):
        raise AssertionError(opponent_active)
    if sum(card["id"] == ULTRA_BALL_ID for card in primary["hand_cards"]) != 2:
        raise AssertionError(primary["hand_cards"])

    boss_options = [
        row for row in primary["options"] if row["card_id"] == BOSS_ID
    ]
    ultra_options = [
        row for row in primary["options"] if row["card_id"] == ULTRA_BALL_ID
    ]
    raging = [
        row for row in primary["options"] if row["attack_id"] == 224
    ]
    hammer = [
        row for row in primary["options"] if row["attack_id"] == 223
    ]
    if (
        not boss_options
        or {row["score"] for row in boss_options} != {4200}
        or len(ultra_options) != 2
        or {row["score"] for row in ultra_options} != {300}
        or len(raging) != 1
        or raging[0]["score"] != 80
        or len(hammer) != 1
        or hammer[0]["score"] != 30
    ):
        raise AssertionError(primary["options"])

    if (
        boss_target["parent_selected_positions"] != [0]
        or boss_target["next_recorded_action"] != [0]
        or boss_target["options"][0]["target_id"] != SOLROCK_ID
    ):
        raise AssertionError(boss_target)
    if (
        ultra_ball["parent_selected_positions"] != [2]
        or ultra_ball["next_recorded_action"] != [2]
        or ultra_ball["options"][2]["card_id"] != ULTRA_BALL_ID
    ):
        raise AssertionError(ultra_ball)
    searchable_archaludon = [
        row for row in search["options"] if row["target_id"] == ARCHALUDON_EX_ID
    ]
    if (
        search["parent_selected_positions"] != [0]
        or search["next_recorded_action"] != [0]
        or len(searchable_archaludon) != 3
    ):
        raise AssertionError(search)
    if (
        evolve["parent_selected_positions"] != [3]
        or evolve["next_recorded_action"] != [3]
        or evolve["options"][3]["card_id"] != ARCHALUDON_EX_ID
        or evolve["options"][3]["target_id"] != DURALUDON_ID
        or evolve["options"][3]["target_serial"] != 66
    ):
        raise AssertionError(evolve)
    if (
        attack["parent_selected_positions"] != [0]
        or attack["next_recorded_action"] != [0]
        or attack["options"][0]["attack_id"] != METAL_DEFENDER_ID
    ):
        raise AssertionError(attack)

    attack_logs = replay["steps"][148][TARGET_SEAT]["observation"]["logs"]
    if not (
        any(log.get("attackId") == METAL_DEFENDER_ID for log in attack_logs)
        and any(log.get("value") == -220 for log in attack_logs)
    ):
        raise AssertionError(attack_logs)

    result = {
        "episode": replay["info"]["EpisodeId"],
        "target_seat": TARGET_SEAT,
        "target_reward": replay["rewards"][TARGET_SEAT],
        "parent_sha256": parent_hash,
        "replay_sha256": replay_hash,
        "captured": captured,
        "verified": {
            "three_prizes_remaining": True,
            "active_mega_ex_worth_three": True,
            "active_exactly_within_metal_defender_220": True,
            "established_duraludon_with_three_metal": True,
            "two_ultra_ball_options_public": True,
            "three_archaludon_ex_search_targets_public": True,
            "active_evolution_executed": True,
            "assemble_alloy_resolution_executed": True,
            "metal_defender_220_executed": True,
            "parent_preempted_active_terminal_with_boss": True,
        },
        "scope_limit": (
            "The actual turn proves the search, discard, evolution, Alloy, "
            "and attack components. A checked no-Boss engine branch must "
            "still prove unchanged option legality and that the 220 damage "
            "lands on the original three-Prize Active before implementation."
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
