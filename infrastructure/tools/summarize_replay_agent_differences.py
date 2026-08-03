"""Summarize action differences with the public replay state that caused them."""
from __future__ import annotations

import argparse
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

from ptcg_common import ensure_engine_on_path, load_agent, pushd
from research.rl_ptcg.label_replay_rollout import replay_decisions


def enum_name(value: Any) -> str:
    return getattr(value, "name", str(value))


def card_id(card: Any) -> int | None:
    return getattr(card, "id", None) if card is not None else None


def card_ids(cards: Any) -> list[int]:
    return [value for card in (cards or []) if (value := card_id(card)) is not None]


def pokemon_row(pokemon: Any) -> dict[str, Any] | None:
    if pokemon is None:
        return None
    return {
        "id": card_id(pokemon),
        "hp": getattr(pokemon, "hp", None),
        "max_hp": getattr(pokemon, "maxHp", None),
        "energies": card_ids(getattr(pokemon, "energyCards", None)),
        "tools": card_ids(getattr(pokemon, "tools", None)),
        "appeared_this_turn": getattr(pokemon, "appearThisTurn", None),
    }


def active_row(player: Any) -> dict[str, Any] | None:
    active = getattr(player, "active", None) or []
    return pokemon_row(active[0]) if active else None


def option_row(module: Any, obs: Any, index: int) -> dict[str, Any]:
    option = obs.select.option[index]
    card = module.option_card(obs, option)
    target = module.option_target(obs, option)
    try:
        score, reason = module.score_option_with_champions_call_order(obs, option)
    except Exception as exc:  # pragma: no cover - diagnostic output
        score, reason = None, f"{type(exc).__name__}: {exc}"
    return {
        "index": index,
        "type": enum_name(getattr(option, "type", None)),
        "card_id": card_id(card),
        "card_name": getattr(card, "name", None) if card is not None else None,
        "target_id": card_id(target),
        "target_name": getattr(target, "name", None) if target is not None else None,
        "attack_id": getattr(option, "attackId", None),
        "area": enum_name(getattr(option, "inPlayArea", getattr(option, "area", None))),
        "score": score,
        "reason": reason,
    }


def selected_rows(module: Any, obs: Any, action: list[int]) -> list[dict[str, Any]]:
    return [option_row(module, obs, index) for index in action]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--episode-csv", type=Path, required=True)
    parser.add_argument("--replay-dir", type=Path, required=True)
    parser.add_argument("--comparison-dir", type=Path, required=True)
    parser.add_argument("--agent-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    ensure_engine_on_path(args.engine_dir)
    agent = load_agent(args.agent_dir, "replay_difference_summary")
    module = agent.module

    with args.episode_csv.open(newline="", encoding="utf-8-sig") as handle:
        episodes = [
            row for row in csv.DictReader(handle)
            if row.get("type") == "EPISODE_TYPE_PUBLIC"
        ]

    output: list[dict[str, Any]] = []
    for episode in episodes:
        episode_id = int(episode["episode_id"])
        comparison_path = args.comparison_dir / f"episode_{episode_id}_v75_vs_v80.json"
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        if not comparison.get("differences"):
            continue

        replay_path = args.replay_dir / f"episode_{episode_id}_replay.json"
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        target_seat = int(comparison["target_seat"])
        observations = {
            step: observation
            for step, observation, _recorded in replay_decisions(replay, target_seat)
        }

        for difference in comparison["differences"]:
            step = int(difference["step"])
            observation = observations[step]
            with pushd(args.agent_dir):
                obs = module.to_observation_class(observation)
                current = obs.current
                mine = current.players[current.yourIndex]
                opponent = current.players[1 - current.yourIndex]
                deficit = module.role_complete_deficit(obs)
                continuation = module.ordinary_attack_continuation_id(obs)
                output.append({
                    "episode_id": episode_id,
                    "reward": int(episode["target_reward"]),
                    "opponent": episode.get("opponent_team"),
                    "target_seat": target_seat,
                    "step": step,
                    "turn": getattr(current, "turn", None),
                    "context": enum_name(getattr(obs.select, "context", None)),
                    "role_deficit": list(deficit) if deficit is not None else None,
                    "ordinary_attack_id": continuation,
                    "my_prizes": len(getattr(mine, "prize", None) or []),
                    "opponent_prizes": len(getattr(opponent, "prize", None) or []),
                    "my_deck_count": getattr(mine, "deckCount", None),
                    "my_active": active_row(mine),
                    "my_bench": [pokemon_row(card) for card in (getattr(mine, "bench", None) or [])],
                    "my_hand": card_ids(getattr(mine, "hand", None)),
                    "my_discard": card_ids(getattr(mine, "discard", None)),
                    "opponent_active": active_row(opponent),
                    "opponent_bench": [pokemon_row(card) for card in (getattr(opponent, "bench", None) or [])],
                    "v75": selected_rows(module, obs, difference["left"]),
                    "v80": selected_rows(module, obs, difference["right"]),
                    "recorded": selected_rows(module, obs, difference["recorded"]),
                })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"public_episodes": len(episodes), "difference_rows": len(output), "output": str(args.output)}))


if __name__ == "__main__":
    main()
