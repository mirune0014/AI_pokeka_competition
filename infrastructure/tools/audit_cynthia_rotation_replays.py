"""Audit damaged-Garchomp rotation opportunities in Kaggle replays.

The audit only uses acting-player observations. It measures where retreat was
legal while a damaged Active Garchomp ex had another Garchomp ex on the Bench,
and records whether the submitted action and a candidate policy chose retreat.
It does not label retreat as correct from the eventual game result.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ptcg_common import ensure_engine_on_path, load_agent, write_csv


GARCHOMP_EX = 381


def enum_name(value: Any) -> str:
    return getattr(value, "name", str(value))


def attached_ids(cards: Any) -> str:
    return " ".join(str(getattr(card, "id", card)) for card in (cards or []))


def selected_type_names(obs_obj: Any, action: Any) -> str:
    names: list[str] = []
    for index in action if isinstance(action, list) else []:
        if isinstance(index, int) and 0 <= index < len(obs_obj.select.option):
            names.append(enum_name(obs_obj.select.option[index].type))
    return " ".join(names)


def replay_rows(replay: Path, agent: Any, target_team: str) -> tuple[list[dict[str, Any]], str | None]:
    data = json.loads(replay.read_text(encoding="utf-8"))
    teams = (data.get("info") or {}).get("TeamNames") or []
    if target_team not in teams:
        return [], f"team {target_team!r} not found in {teams!r}"

    target_index = teams.index(target_team)
    module = agent.module
    rows: list[dict[str, Any]] = []
    final_rewards = data.get("rewards") or []
    reward = final_rewards[target_index] if target_index < len(final_rewards) else ""
    episode_id = (data.get("info") or {}).get("EpisodeId", data.get("id", replay.stem))
    opponent_team = teams[1 - target_index] if len(teams) == 2 else ""

    for step_index, pair in enumerate(data.get("steps") or []):
        if target_index >= len(pair or []):
            continue
        entry = pair[target_index]
        if not isinstance(entry, dict) or entry.get("status") != "ACTIVE":
            continue
        observation = entry.get("observation") or {}
        if not observation.get("select"):
            continue

        obs_obj = module.to_observation_class(observation)
        current = obs_obj.current
        mine = current.players[current.yourIndex]
        active = (getattr(mine, "active", None) or [None])[0]
        if not active or getattr(active, "id", None) != GARCHOMP_EX:
            continue

        retreat_indices = [
            index
            for index, option in enumerate(obs_obj.select.option)
            if option.type == module.OptionType.RETREAT
        ]
        if not retreat_indices:
            continue

        damage = module.damage_on(active)
        if damage <= 0:
            continue

        bench_garchomp = [
            pokemon
            for pokemon in (getattr(mine, "bench", None) or [])
            if pokemon and getattr(pokemon, "id", None) == GARCHOMP_EX
        ]
        if not bench_garchomp:
            continue

        recorded_action = entry.get("action") or []
        candidate_action = agent(observation)
        legal_attacks = [
            getattr(option, "attackId", None)
            for option in obs_obj.select.option
            if option.type == module.OptionType.ATTACK
        ]
        rows.append(
            {
                "episode_id": episode_id,
                "opponent_team": opponent_team,
                "reward": reward,
                "step": step_index,
                "turn": getattr(current, "turn", ""),
                "context": enum_name(obs_obj.select.context),
                "active_hp": module.hp(active),
                "active_max_hp": module.max_hp(active),
                "active_damage": damage,
                "active_energy": module.energy_count(active),
                "active_energy_ids": attached_ids(module.energy_cards(active)),
                "active_tool_ids": attached_ids(getattr(active, "tools", None)),
                "bench_garchomp_count": len(bench_garchomp),
                "ready_bench_garchomp_count": sum(module.energy_count(pokemon) >= 2 for pokemon in bench_garchomp),
                "bench_garchomp_energy": " ".join(str(module.energy_count(pokemon)) for pokemon in bench_garchomp),
                "bench_garchomp_hp": " ".join(str(module.hp(pokemon)) for pokemon in bench_garchomp),
                "legal_attack_ids": " ".join(str(attack_id) for attack_id in legal_attacks if attack_id is not None),
                "recorded_types": selected_type_names(obs_obj, recorded_action),
                "candidate_types": selected_type_names(obs_obj, candidate_action),
                "recorded_retreat": bool(set(recorded_action) & set(retreat_indices)),
                "candidate_retreat": bool(set(candidate_action) & set(retreat_indices)),
            }
        )
    return rows, None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit damaged Cynthia Garchomp rotation opportunities.")
    parser.add_argument("replays", type=Path, nargs="+")
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--agent-dir", type=Path, required=True)
    parser.add_argument("--target-team", default="rurumi")
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_engine_on_path(args.engine_dir)
    agent = load_agent(args.agent_dir, f"rotation_audit_{args.agent_dir.name}")
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for replay in args.replays:
        replay_result, reason = replay_rows(replay, agent, args.target_team)
        rows.extend(replay_result)
        if reason:
            skipped.append({"replay": str(replay), "reason": reason})

    args.output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else [
        "episode_id", "opponent_team", "reward", "step", "turn", "context",
        "active_hp", "active_max_hp", "active_damage", "active_energy",
        "active_energy_ids", "active_tool_ids", "bench_garchomp_count",
        "ready_bench_garchomp_count", "bench_garchomp_energy", "bench_garchomp_hp",
        "legal_attack_ids", "recorded_types", "candidate_types", "recorded_retreat",
        "candidate_retreat",
    ]
    write_csv(args.output_dir / "rotation_states.csv", rows, fields)
    summary = {
        "replays": len(args.replays),
        "skipped": skipped,
        "rotation_states": len(rows),
        "ready_backup_states": sum(int(row["ready_bench_garchomp_count"] > 0) for row in rows),
        "recorded_retreats": sum(int(row["recorded_retreat"]) for row in rows),
        "candidate_retreats": sum(int(row["candidate_retreat"]) for row in rows),
        "wins": sum(int(row["reward"] == 1) for row in rows),
        "losses": sum(int(row["reward"] == -1) for row in rows),
    }
    (args.output_dir / "report.json").write_text(
        json.dumps(summary, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=True))


if __name__ == "__main__":
    main()
