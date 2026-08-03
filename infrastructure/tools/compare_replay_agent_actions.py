"""Compare two stateful agents on the same Kaggle replay observations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "infrastructure" / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "infrastructure" / "tools"))

from ptcg_common import ensure_engine_on_path, load_agent, read_deck
from research.rl_ptcg.label_replay_rollout import replay_decisions, target_seat_for_deck


def target_seat_for_team(replay, team_name: str) -> int:
    teams = (replay.get("info") or {}).get("TeamNames") or []
    matches = [seat for seat, name in enumerate(teams) if name == team_name]
    if len(matches) != 1:
        raise ValueError("replay does not contain exactly one matching target team")
    return matches[0]


def resolve_target_seat(
    replay: dict,
    deck: list[int],
    *,
    target_team: str | None = None,
    target_seat: int | None = None,
) -> int:
    if target_seat is not None:
        return target_seat
    if target_team:
        return target_seat_for_team(replay, target_team)
    return target_seat_for_deck(replay, deck)


def selected_options(observation: dict, action: list[int]) -> list[dict]:
    options = (observation.get("select") or {}).get("option") or []
    return [options[index] for index in action if 0 <= index < len(options)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--left", type=Path, required=True)
    parser.add_argument("--right", type=Path, required=True)
    parser.add_argument("--target-team")
    parser.add_argument("--target-seat", type=int, choices=(0, 1))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    ensure_engine_on_path(args.engine_dir)
    replay = json.loads(args.replay.read_text(encoding="utf-8"))
    target_seat = resolve_target_seat(
        replay,
        read_deck(args.left / "deck.csv"),
        target_team=args.target_team,
        target_seat=args.target_seat,
    )

    left = load_agent(args.left, "replay_compare_left")
    right = load_agent(args.right, "replay_compare_right")
    differences = []
    left_recorded_differences = []
    right_recorded_differences = []
    decisions = 0
    for replay_step, observation, recorded in replay_decisions(replay, target_seat):
        left_action = left(observation)
        right_action = right(observation)
        decisions += 1
        current = observation.get("current") or {}
        select = observation.get("select") or {}
        shared = {
            "step": replay_step,
            "turn": current.get("turn"),
            "context": select.get("context"),
            "recorded": recorded,
            "recorded_options": selected_options(observation, recorded),
        }
        if left_action != recorded:
            left_recorded_differences.append({
                **shared,
                "agent": left_action,
                "agent_options": selected_options(observation, left_action),
            })
        if right_action != recorded:
            right_recorded_differences.append({
                **shared,
                "agent": right_action,
                "agent_options": selected_options(observation, right_action),
            })
        if left_action == right_action:
            continue
        differences.append({
            **shared,
            "left": left_action,
            "right": right_action,
            "left_options": selected_options(observation, left_action),
            "right_options": selected_options(observation, right_action),
        })

    report = {
        "replay": str(args.replay),
        "target_seat": target_seat,
        "decisions": decisions,
        "differences": differences,
        "difference_count": len(differences),
        "left_recorded_differences": left_recorded_differences,
        "left_recorded_difference_count": len(left_recorded_differences),
        "right_recorded_differences": right_recorded_differences,
        "right_recorded_difference_count": len(right_recorded_differences),
    }
    output = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
