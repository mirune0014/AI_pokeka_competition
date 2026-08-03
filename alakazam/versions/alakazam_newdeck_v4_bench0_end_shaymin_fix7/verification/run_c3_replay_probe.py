#!/usr/bin/env python3
"""Deterministic checked probe for the frozen 88843743 C3 mechanism."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys


EXPECTED_REPLAY_SHA256 = (
    "B0B8752CA10D9319C667A5482323BF8A780A3038FFDD50AF7DCF588EDA882948"
)


def _canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _post_basic(observation):
    obs = copy.deepcopy(observation)
    mine = obs["current"]["players"][1]
    selected = mine["hand"].pop(5)
    if (selected["id"], selected["serial"]) != (343, 81):
        raise AssertionError("frozen Shaymin identity changed")
    mine["handCount"] -= 1
    mine["bench"] = [
        {
            "appearThisTurn": True,
            "energies": [],
            "energyCards": [],
            "hp": 80,
            "id": 343,
            "maxHp": 80,
            "playerIndex": 1,
            "preEvolution": [],
            "serial": 81,
            "tools": [],
        }
    ]
    obs["current"]["turnActionCount"] += 1
    obs["logs"] = [
        {"cardId": 343, "playerIndex": 1, "serial": 81, "type": 10}
    ]
    obs["select"]["option"] = [
        {"type": 14},
        {"attackId": 1071, "type": 13},
    ]
    return obs


def run(replay_path: Path):
    payload = replay_path.read_bytes()
    replay_hash = hashlib.sha256(payload).hexdigest().upper()
    if replay_hash != EXPECTED_REPLAY_SHA256:
        raise AssertionError(
            f"replay hash mismatch: {replay_hash}"
        )
    replay = json.loads(payload)

    # Import only after validation so the checked candidate is the sole source.
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    import main
    import planner_public_damage_continuity as damage
    import planner_public_survival_bench0 as survival

    deck = main.agent({"select": None, "current": None})
    if len(deck) != 60:
        raise AssertionError("deck callback did not return 60 cards")
    observations = {
        index: replay["steps"][index][1]["observation"]
        for index in (22, 23, 24, 27)
    }
    actions = {}
    for index in (22, 23, 24, 27):
        actions[index] = main.agent(copy.deepcopy(observations[index]))
    if actions != {22: [2], 23: [0], 24: [3], 27: [2]}:
        raise AssertionError(f"frozen action mismatch: {actions}")
    armed = copy.deepcopy(main.LAST_STAGED_POLICY_TRACE)
    if (
        armed.get("rule_version") != damage.RULE_VERSION
        or armed.get("transaction_stage") != "ARMED"
        or armed.get("raw_parent_action") != [3]
        or armed.get("applied_action") != [2]
        or (
            armed.get("selected_basic", {}).get("card_id"),
            armed.get("selected_basic", {}).get("serial"),
        )
        != (343, 81)
    ):
        raise AssertionError("armed trace mismatch")
    cosmic = next(
        row
        for row in armed["damage_rows"]
        if row.get("attack_id") == 980
    )
    if cosmic.get("damage_cap") != 160:
        raise AssertionError("Solrock supported cap is not 160")

    duplicate = copy.deepcopy(observations[27])
    duplicate["select"]["option"] = list(
        reversed(duplicate["select"]["option"])
    )
    duplicate_action = main.agent(duplicate)
    duplicate_option = duplicate["select"]["option"][duplicate_action[0]]
    duplicate_card = duplicate["current"]["players"][1]["hand"][
        duplicate_option["index"]
    ]
    if (
        duplicate_option["type"],
        duplicate_card["id"],
        duplicate_card["serial"],
    ) != (7, 343, 81):
        raise AssertionError("duplicate semantic rebind mismatch")

    post = _post_basic(observations[27])
    final_action = main.agent(post)
    if damage.semantic_action(post, final_action) != ("ATTACK", 1071):
        raise AssertionError("full-policy semantic re-entry mismatch")
    if survival.C3_TRANSACTION is not None:
        raise AssertionError("C3 transaction did not clear")
    completed = main.LAST_STAGED_POLICY_TRACE
    if completed.get("transaction_stage") != "COMPLETED":
        raise AssertionError("completed trace mismatch")
    return {
        "pass": True,
        "replay_sha256": replay_hash,
        "deck_count": len(deck),
        "actions": {str(key): value for key, value in actions.items()},
        "duplicate_action": duplicate_action,
        "post_basic_action": final_action,
        "post_basic_semantic": ["ATTACK", 1071],
        "rule_version": completed["rule_version"],
        "candidate_closure_sha256": completed[
            "candidate_closure_sha256"
        ],
        "guard_class": armed["guard_class"],
        "selected_basic": {
            "card_id": armed["selected_basic"]["card_id"],
            "serial": armed["selected_basic"]["serial"],
        },
        "solrock_cap": cosmic["damage_cap"],
    }


def main_cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--replay",
        type=Path,
        default=Path(r"C:\Users\amuam\Downloads\88843743.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.replay)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(_canonical(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
