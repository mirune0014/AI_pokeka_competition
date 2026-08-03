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
    / "refresh_20260730_0054"
    / "episode_88826155_replay.json"
)
EXPECTED_PARENT_SHA256 = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
EXPECTED_REPLAY_SHA256 = (
    "3E294511D4AB0AE0E443EF7D14D33BF115D1C7AB072E433D57A53370B32F6935"
)
TARGET_SEAT = 1
SEARCH_ROW = 132
BENCH_ROW = 135
SECOND_SEARCH_ROW = 146
SECOND_BENCH_ROW = 148
ARCHALUDON_EX_ID = 190
DURALUDON_ID = 169
ULTRA_BALL_ID = 1121
POKE_PAD_ID = 1152
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


def main() -> None:
    parent_hash = sha256(PARENT / "main.py")
    replay_hash = sha256(REPLAY)
    if parent_hash != EXPECTED_PARENT_SHA256:
        raise AssertionError(("parent hash", parent_hash))
    if replay_hash != EXPECTED_REPLAY_SHA256:
        raise AssertionError(("replay hash", replay_hash))

    sys.path.insert(0, str(PARENT))
    parent = load_module("root_mirror_gust_parent", PARENT / "main.py")
    parent._opp_last_attack_id = None
    parent._cur_turn_logs.clear()
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))

    captured: dict[int, dict] = {}
    target_rows = {SEARCH_ROW, BENCH_ROW, SECOND_SEARCH_ROW, SECOND_BENCH_ROW}
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

    if set(captured) != target_rows:
        raise AssertionError(sorted(captured))
    search = captured[SEARCH_ROW]
    bench = captured[BENCH_ROW]
    second_search = captured[SECOND_SEARCH_ROW]
    second_bench = captured[SECOND_BENCH_ROW]

    if search["parent_selected_positions"] != [0]:
        raise AssertionError(search)
    if search["next_recorded_action"] != [0]:
        raise AssertionError(search)
    if search["options"][0]["card_id"] != ULTRA_BALL_ID:
        raise AssertionError(search["options"])
    if search["options"][2]["attack_id"] != METAL_DEFENDER_ID:
        raise AssertionError(search["options"])
    if search["options"][0]["score"] != 300:
        raise AssertionError(search["options"][0])
    if search["options"][2]["score"] != 220:
        raise AssertionError(search["options"][2])
    if (
        search["opponent_prizes_remaining"] != 1
        or search["own_prizes_remaining"] != 2
        or search["stadium_id"] != FULL_METAL_LAB_ID
        or search["own_bench"]
    ):
        raise AssertionError(search)
    if (
        len(search["own_active"]) != 1
        or search["own_active"][0]["id"] != ARCHALUDON_EX_ID
        or search["own_active"][0]["hp"] != 300
        or len(search["own_active"][0]["energy_ids"]) != 3
    ):
        raise AssertionError(search["own_active"])
    ready_mirror = [
        card
        for card in search["opponent_bench"]
        if card["id"] == ARCHALUDON_EX_ID
        and len(card["energy_ids"]) >= 3
    ]
    if len(ready_mirror) != 1:
        raise AssertionError(search["opponent_bench"])

    if (
        bench["parent_selected_positions"] != [0]
        or bench["next_recorded_action"] != [0]
        or bench["options"][0]["card_id"] != DURALUDON_ID
    ):
        raise AssertionError(bench)
    if (
        second_search["parent_selected_positions"] != [2]
        or second_search["next_recorded_action"] != [2]
        or second_search["options"][2]["card_id"] != POKE_PAD_ID
    ):
        raise AssertionError(second_search)
    if (
        second_bench["parent_selected_positions"] != [4]
        or second_bench["next_recorded_action"] != [4]
        or second_bench["options"][4]["card_id"] != DURALUDON_ID
    ):
        raise AssertionError(second_bench)

    opponent_boss_logs = replay["steps"][156][0]["observation"]["logs"]
    switch_logs = replay["steps"][157][0]["observation"]["logs"]
    terminal_logs = replay["steps"][159][0]["observation"]["logs"]
    if not any(
        log.get("cardId") == BOSS_ID and log.get("serial") == 47
        for log in (
            opponent_boss_logs
            if isinstance(opponent_boss_logs, list)
            else [opponent_boss_logs]
        )
    ):
        raise AssertionError(opponent_boss_logs)
    if not any(
        log.get("cardIdBench") == DURALUDON_ID
        and log.get("serialBench") == 64
        for log in (switch_logs if isinstance(switch_logs, list) else [switch_logs])
    ):
        raise AssertionError(switch_logs)
    if not (
        any(log.get("attackId") == METAL_DEFENDER_ID for log in terminal_logs)
        and any(
            log.get("cardId") == DURALUDON_ID
            and log.get("serial") == 64
            and log.get("value") == -190
            for log in terminal_logs
        )
    ):
        raise AssertionError(terminal_logs)

    result = {
        "episode": replay["info"]["EpisodeId"],
        "target_seat": TARGET_SEAT,
        "target_reward": replay["rewards"][TARGET_SEAT],
        "parent_sha256": parent_hash,
        "replay_sha256": replay_hash,
        "captured": captured,
        "verified": {
            "opponent_one_prize_at_first_search": True,
            "own_bench_empty_at_first_search": True,
            "own_active_300_with_three_metal": True,
            "visible_ready_mirror_archaludon": ready_mirror[0],
            "full_metal_lab_public": True,
            "visible_mirror_metal_defender_damage": 190,
            "visible_active_survival_hp_before_later_actions": 110,
            "parent_prioritized_ultra_ball_over_attack": True,
            "parent_benched_first_duraludon": True,
            "parent_searched_and_benched_second_duraludon": True,
            "observed_hidden_boss_gusted_first_duraludon": True,
            "observed_terminal_damage": 190,
        },
        "scope_limit": (
            "The public row proves a one-Prize Bench liability and a ready "
            "mirror attacker while the sole 300-HP Active survives the "
            "visible 190-damage attack. Boss access was hidden at the search "
            "row, and the no-Bench branch was not simulated, so this is a "
            "risk/mode hypothesis rather than a deterministic-win rule."
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
