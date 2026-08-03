from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "infrastructure" / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "infrastructure" / "tools"))

from ptcg_common import ensure_engine_on_path, load_agent, read_deck
from research.rl_ptcg.label_replay_rollout import replay_decisions, target_seat_for_deck


ATTACK_OPTION_TYPE = 13
CORKSCREW_DIVE = 531
DRACONIC_BUSTER = 532


def selected_options(observation: dict[str, Any], action: list[int]) -> list[dict[str, Any]]:
    options = (observation.get("select") or {}).get("option") or []
    return [options[index] for index in action if 0 <= index < len(options)]


def attack_id_from_action(observation: dict[str, Any], action: list[int]) -> int | None:
    for option in selected_options(observation, action):
        attack_id = option.get("attackId")
        if attack_id is not None:
            return int(attack_id)
    return None


def action_label(observation: dict[str, Any], action: list[int], option_type: Any) -> str:
    labels: list[str] = []
    for option in selected_options(observation, action):
        attack_id = option.get("attackId")
        if attack_id is not None:
            labels.append(f"ATTACK:{attack_id}")
            continue
        value = option.get("type")
        try:
            name = option_type(value).name
        except (TypeError, ValueError):
            name = str(value)
        labels.append(name)
    return "+".join(labels) if labels else "EMPTY"


def classify_buster_state(
    *,
    buster_ko: bool,
    corkscrew_ko: bool,
    target_prize_value: int,
    remaining_prizes: int,
    opponent_bench_empty: bool,
) -> str:
    if not buster_ko:
        return "non_KO_Buster"
    if corkscrew_ko:
        return "Corkscrew_also_KO"
    if target_prize_value >= remaining_prizes:
        return "game_winning_KO"
    if opponent_bench_empty:
        return "board_clear_KO"
    if target_prize_value >= 2:
        return "Buster_only_multi_prize_KO"
    return "Buster_only_one_prize_KO"


def resolve_target_seat(
    replay: dict[str, Any], deck: list[int], target_team: str | None
) -> int:
    if not target_team:
        return target_seat_for_deck(replay, deck)
    teams = (replay.get("info") or {}).get("TeamNames") or []
    matches = [seat for seat, name in enumerate(teams) if name == target_team]
    if len(matches) != 1:
        raise ValueError("replay does not contain exactly one matching target team")
    return matches[0]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit every replay state where both Cynthia Garchomp attacks are legal."
    )
    parser.add_argument("replays", type=Path, nargs="+")
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--candidate-agent-dir", type=Path, required=True)
    parser.add_argument("--baseline-agent-dir", type=Path)
    parser.add_argument("--target-team")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    ensure_engine_on_path(args.engine_dir)
    candidate = load_agent(args.candidate_agent_dir, "cynthia_buster_candidate")
    baseline = (
        load_agent(args.baseline_agent_dir, "cynthia_buster_baseline")
        if args.baseline_agent_dir
        else None
    )
    module = candidate.module
    deck = read_deck(args.candidate_agent_dir / "deck.csv")

    rows: list[dict[str, Any]] = []
    replay_count = 0
    for replay_path in args.replays:
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        target_seat = resolve_target_seat(replay, deck, args.target_team)
        rewards = replay.get("rewards") or []
        reward = rewards[target_seat] if target_seat < len(rewards) else None
        episode_id = str((replay.get("info") or {}).get("EpisodeId", replay_path.stem))
        replay_count += 1

        for replay_step, observation, recorded_action in replay_decisions(replay, target_seat):
            legal_attack_ids = {
                int(option["attackId"])
                for option in ((observation.get("select") or {}).get("option") or [])
                if option.get("type") == ATTACK_OPTION_TYPE and option.get("attackId") is not None
            }
            if not {CORKSCREW_DIVE, DRACONIC_BUSTER}.issubset(legal_attack_ids):
                continue

            obs = module.to_observation_class(observation)
            target = module.opponent_active(obs)
            if target is None:
                continue
            candidate_action = candidate(observation)
            baseline_action = baseline(observation) if baseline else []
            candidate_attack = attack_id_from_action(observation, candidate_action)
            baseline_attack = attack_id_from_action(observation, baseline_action)
            recorded_attack = attack_id_from_action(observation, recorded_action)
            buster_damage = module.best_damage_for_active(obs, DRACONIC_BUSTER)
            corkscrew_damage = module.best_damage_for_active(obs, CORKSCREW_DIVE)
            target_hp = module.hp(target)
            target_prize_value = module.prize_value(target)
            remaining_prizes = len(getattr(module.me(obs), "prize", []) or [])
            opponent_bench_empty = module.opponent_has_no_bench(obs)
            approved = bool(module.is_approved_buster_conversion(obs))
            class_name = classify_buster_state(
                buster_ko=buster_damage >= target_hp,
                corkscrew_ko=corkscrew_damage >= target_hp,
                target_prize_value=target_prize_value,
                remaining_prizes=remaining_prizes,
                opponent_bench_empty=opponent_bench_empty,
            )
            current = observation.get("current") or {}
            rows.append(
                {
                    "episode_id": episode_id,
                    "replay": str(replay_path),
                    "seat": target_seat,
                    "reward": reward,
                    "step": replay_step,
                    "turn": current.get("turn"),
                    "class": class_name,
                    "approved": approved,
                    "recorded_action": action_label(
                        observation, recorded_action, module.OptionType
                    ),
                    "baseline_action": action_label(
                        observation, baseline_action, module.OptionType
                    )
                    if baseline
                    else "",
                    "candidate_action": action_label(
                        observation, candidate_action, module.OptionType
                    ),
                    "recorded_attack": recorded_attack,
                    "baseline_attack": baseline_attack,
                    "candidate_attack": candidate_attack,
                    "unsafe_candidate_buster": bool(
                        candidate_attack == DRACONIC_BUSTER and not approved
                    ),
                    "target_card_id": getattr(target, "id", None),
                    "target_hp": target_hp,
                    "target_prize_value": target_prize_value,
                    "remaining_prizes": remaining_prizes,
                    "opponent_bench_empty": opponent_bench_empty,
                    "buster_damage": buster_damage,
                    "corkscrew_damage": corkscrew_damage,
                    "loaded_backup": bool(module.has_energized_bench_main_line(obs)),
                    "hand_count": len(getattr(module.me(obs), "hand", []) or []),
                    "deck_count": module.deck_count(obs),
                }
            )

    class_counts = Counter(row["class"] for row in rows)
    recorded_counts = Counter(str(row["recorded_attack"]) for row in rows)
    baseline_counts = Counter(str(row["baseline_attack"]) for row in rows)
    candidate_counts = Counter(str(row["candidate_attack"]) for row in rows)
    unsafe_rows = [row for row in rows if row["unsafe_candidate_buster"]]
    summary = {
        "replays": replay_count,
        "dual_legal_states": len(rows),
        "approved_states": sum(bool(row["approved"]) for row in rows),
        "class_counts": dict(class_counts),
        "recorded_attack_counts": dict(recorded_counts),
        "baseline_attack_counts": dict(baseline_counts) if baseline else {},
        "candidate_attack_counts": dict(candidate_counts),
        "candidate_buster_states": sum(
            row["candidate_attack"] == DRACONIC_BUSTER for row in rows
        ),
        "unsafe_candidate_buster_states": len(unsafe_rows),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "states.csv", rows)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
