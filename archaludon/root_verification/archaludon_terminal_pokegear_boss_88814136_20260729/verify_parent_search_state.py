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
    / "refresh_20260729_2325"
    / "episode_88814136_replay.json"
)
EXPECTED_PARENT_SHA256 = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
EXPECTED_REPLAY_SHA256 = (
    "147B531CC74A14C1809CA1A762E8A9E739D7BB1F48E8F7CCCBFF5F787770770B"
)
TARGET_SEAT = 0
MAIN_ROW = 151
TO_HAND_ROW = 152


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
    parent = load_module("root_terminal_search_parent", PARENT / "main.py")
    parent._opp_last_attack_id = None
    parent._cur_turn_logs.clear()

    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    rows: dict[int, dict] = {}
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
        if row not in (MAIN_ROW, TO_HAND_ROW):
            if parsed.select.option:
                parent.choose_options(parsed)
            continue

        raw_current = observation["current"]
        own = raw_current["players"][TARGET_SEAT]
        opponent = raw_current["players"][1 - TARGET_SEAT]
        options = [
            describe_option(parent, parsed, position)
            for position in range(len(parsed.select.option))
        ]
        selected = parent.choose_options(parsed)
        rows[row] = {
            "turn": raw_current["turn"],
            "turn_action_count": raw_current["turnActionCount"],
            "context": int(parsed.select.context),
            "recorded_action": record.get("action"),
            "parent_selected_positions": selected,
            "supporter_played": raw_current["supporterPlayed"],
            "own_prizes_remaining": len(own["prize"]),
            "opponent_prizes_remaining": len(opponent["prize"]),
            "own_active": [raw_card(card) for card in own["active"]],
            "opponent_active": [raw_card(card) for card in opponent["active"]],
            "opponent_bench": [raw_card(card) for card in opponent["bench"]],
            "looking": [
                {
                    "index": index,
                    "id": card.get("id"),
                    "serial": card.get("serial"),
                }
                for index, card in enumerate(raw_current.get("looking") or [])
            ],
            "options": options,
        }

    if sorted(rows) != [MAIN_ROW, TO_HAND_ROW]:
        raise AssertionError(sorted(rows))

    to_hand = rows[TO_HAND_ROW]
    by_position = {row["position"]: row for row in to_hand["options"]}
    if to_hand["parent_selected_positions"] != [0]:
        raise AssertionError(to_hand["parent_selected_positions"])
    if by_position[0]["card_id"] != 1227:
        raise AssertionError(by_position[0])
    if by_position[1]["card_id"] != 1182:
        raise AssertionError(by_position[1])
    if by_position[2]["card_id"] != 1182:
        raise AssertionError(by_position[2])
    if by_position[0]["score"] <= by_position[1]["score"]:
        raise AssertionError((by_position[0], by_position[1]))

    result = {
        "episode": replay["info"]["EpisodeId"],
        "target_seat": TARGET_SEAT,
        "target_reward": replay["rewards"][TARGET_SEAT],
        "parent_sha256": parent_hash,
        "replay_sha256": replay_hash,
        "rows": rows,
        "verified": {
            "one_prize_each": (
                rows[TO_HAND_ROW]["own_prizes_remaining"] == 1
                and rows[TO_HAND_ROW]["opponent_prizes_remaining"] == 1
            ),
            "supporter_unplayed": not rows[TO_HAND_ROW]["supporter_played"],
            "parent_selected_lillie": True,
            "boss_visible_twice": True,
            "boss_scored_below_lillie": True,
            "opponent_bench_contains_public_one_prize_targets": [
                {
                    "id": card["id"],
                    "serial": card["serial"],
                    "hp": card["hp"],
                }
                for card in rows[TO_HAND_ROW]["opponent_bench"]
                if card["id"] in (104, 112)
            ],
        },
        "scope_limit": (
            "This verifies the public search-state miss. It does not execute "
            "the Boss counterfactual; exact Boss-target-attack conversion "
            "must be proved in a checked engine before implementation."
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
