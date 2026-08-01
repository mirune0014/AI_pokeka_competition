from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from ptcg_common import (
    DEFAULT_AGENT_DIR,
    DEFAULT_ENGINE_DIR,
    ensure_engine_on_path,
    load_agent,
    pushd,
    read_deck,
)


def compact_logs(logs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact = []
    for entry in logs:
        item = {"type": entry.get("type"), "playerIndex": entry.get("playerIndex")}
        for key in (
            "cardId",
            "attackId",
            "area",
            "index",
            "result",
            "reason",
            "value",
            "putDamageCounter",
            "cardIdTarget",
            "cardIdActive",
            "cardIdBench",
            "fromArea",
            "toArea",
        ):
            if key in entry:
                item[key] = entry[key]
        compact.append(item)
    return compact


def attached_card_ids(pokemon: dict[str, Any] | None, cards_key: str, ids_key: str) -> list[int]:
    if not pokemon:
        return []
    attached = pokemon.get(cards_key) or pokemon.get(ids_key) or []
    return [
        int(card.get("id")) if isinstance(card, dict) else int(card)
        for card in attached
        if card is not None and (not isinstance(card, dict) or card.get("id") is not None)
    ]


def player_snapshot(obs: dict[str, Any]) -> dict[str, Any]:
    current = obs.get("current") or {}
    players = current.get("players") or []
    output = {
        "turn": current.get("turn"),
        "turn_action_count": current.get("turnActionCount"),
        "your_index": current.get("yourIndex"),
        "first_player": current.get("firstPlayer"),
        "result": current.get("result"),
    }
    for i, player in enumerate(players):
        output[f"p{i}_deck"] = player.get("deckCount")
        output[f"p{i}_hand"] = player.get("handCount")
        output[f"p{i}_prizes"] = len(player.get("prize") or [])
        output[f"p{i}_bench_max"] = player.get("benchMax")
        active = player.get("active") or []
        active_pokemon = active[0] if active and active[0] else None
        output[f"p{i}_active"] = active_pokemon.get("id") if active_pokemon else None
        output[f"p{i}_active_hp"] = active_pokemon.get("hp") if active_pokemon else None
        output[f"p{i}_active_max_hp"] = active_pokemon.get("maxHp") if active_pokemon else None
        output[f"p{i}_active_appear_this_turn"] = (
            active_pokemon.get("appearThisTurn") if active_pokemon else None
        )
        active_energy_ids = attached_card_ids(active_pokemon, "energyCards", "energies")
        output[f"p{i}_active_energy"] = len(active_energy_ids)
        output[f"p{i}_active_energy_ids"] = active_energy_ids
        output[f"p{i}_active_tool_ids"] = attached_card_ids(active_pokemon, "tools", "toolIds")

        bench = [pokemon for pokemon in (player.get("bench") or []) if pokemon]
        output[f"p{i}_bench"] = [pokemon.get("id") for pokemon in bench]
        output[f"p{i}_bench_hp"] = [pokemon.get("hp") for pokemon in bench]
        output[f"p{i}_bench_max_hp"] = [pokemon.get("maxHp") for pokemon in bench]
        output[f"p{i}_bench_appear_this_turn"] = [
            pokemon.get("appearThisTurn") for pokemon in bench
        ]
        bench_energy_ids = [
            attached_card_ids(pokemon, "energyCards", "energies") for pokemon in bench
        ]
        output[f"p{i}_bench_energy"] = [len(ids) for ids in bench_energy_ids]
        output[f"p{i}_bench_energy_ids"] = bench_energy_ids
        output[f"p{i}_bench_tool_ids"] = [
            attached_card_ids(pokemon, "tools", "toolIds") for pokemon in bench
        ]
    return output


def compact_option(option: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "type",
        "area",
        "index",
        "playerIndex",
        "cardId",
        "attackId",
        "inPlayArea",
        "inPlayIndex",
        "inPlayPlayerIndex",
        "targetArea",
        "targetIndex",
        "targetPlayerIndex",
        "energyIndex",
        "toolIndex",
        "number",
    )
    return {key: option.get(key) for key in keys if key in option}


def card_id(card: dict[str, Any] | None) -> int | None:
    if not isinstance(card, dict) or card.get("id") is None:
        return None
    return int(card["id"])


def visible_card_ids(cards: list[dict[str, Any] | None] | None) -> list[int | None]:
    return [card_id(card) for card in (cards or [])]


def acting_hand_ids(obs: dict[str, Any]) -> list[int]:
    current = obs.get("current") or {}
    players = current.get("players") or []
    player = int(current.get("yourIndex", 0))
    if player < 0 or player >= len(players):
        return []
    hand = (players[player] or {}).get("hand") or []
    return [cid for card in hand if (cid := card_id(card)) is not None]


def score_trace(agent: Any, obs: dict[str, Any], action: list[int], limit: int) -> list[dict[str, Any]]:
    module = getattr(agent, "module", None)
    agent_dir = getattr(agent, "agent_dir", None)
    score_option = getattr(module, "score_option", None)
    to_observation_class = getattr(module, "to_observation_class", None)
    if not callable(score_option) or not callable(to_observation_class) or agent_dir is None:
        return []

    select = obs.get("select") or {}
    raw_options = select.get("option") or []
    selected = set(action)
    rows: list[dict[str, Any]] = []
    try:
        obs_obj = to_observation_class(obs)
        with pushd(agent_dir):
            for i, opt in enumerate(obs_obj.select.option):
                try:
                    score, reason = score_option(obs_obj, opt)
                except Exception as exc:
                    score, reason = -999999, f"error {type(exc).__name__}: {exc}"
                raw = raw_options[i] if i < len(raw_options) and isinstance(raw_options[i], dict) else {}
                rows.append(
                    {
                        "index": i,
                        "selected": i in selected,
                        "score": score,
                        "reason": reason,
                        "option": compact_option(raw),
                    }
                )
    except Exception as exc:
        return [{"index": -1, "selected": False, "score": -999999, "reason": f"trace error {type(exc).__name__}: {exc}", "option": {}}]

    rows.sort(key=lambda row: (row["score"], -row["index"]), reverse=True)
    if limit <= 0 or len(rows) <= limit:
        return rows
    top = rows[:limit]
    included = {row["index"] for row in top}
    top.extend(row for row in rows[limit:] if row["selected"] and row["index"] not in included)
    return top


def run_game(args: argparse.Namespace, game_index: int) -> dict[str, Any]:
    from cg.game import battle_finish, battle_select, battle_start

    seed_base = getattr(args, "seed_base", None)
    seed = None if seed_base is None else int(seed_base) + int(game_index)
    if seed is not None:
        random.seed(seed)

    agent_a_dir = args.agent_a.resolve()
    agent_b_dir = args.agent_b.resolve()
    deck_a = read_deck(args.deck_a or (agent_a_dir / "deck.csv"))
    deck_b = read_deck(args.deck_b or (agent_b_dir / "deck.csv"))
    agent_a = load_agent(agent_a_dir, f"agent_a_{game_index}")
    agent_b = load_agent(agent_b_dir, f"agent_b_{game_index}")
    agents = [agent_a, agent_b]
    if seed is not None:
        for agent in agents:
            module_random = getattr(getattr(agent, "module", None), "random", None)
            if hasattr(module_random, "seed"):
                module_random.seed(seed)

    if getattr(args, "engine_seed", False):
        if seed is None:
            raise ValueError("--engine-seed requires --seed-base")
        obs, start_data = battle_start(deck_a, deck_b, seed=seed)
    else:
        obs, start_data = battle_start(deck_a, deck_b)
    if not obs:
        return {
            "game": game_index,
            "seed": seed if seed is not None else "",
            "started": False,
            "error_player": start_data.errorPlayer,
            "error_type": start_data.errorType,
        }

    trace_path = None
    trace_file = None
    if args.trace_dir:
        args.trace_dir.mkdir(parents=True, exist_ok=True)
        trace_path = args.trace_dir / f"game_{game_index:04d}.jsonl"
        trace_file = trace_path.open("w", encoding="utf-8")

    steps = 0
    action_errors = 0
    context_counts: Counter[int] = Counter()
    final_obs = obs
    try:
        while obs and obs.get("select") and steps < args.max_steps:
            current = obs.get("current") or {}
            if current.get("result") not in (None, -1):
                break
            player = int(current.get("yourIndex", 0))
            select = obs.get("select") or {}
            if not select.get("option"):
                break
            context = select.get("context")
            if context is not None:
                context_counts[int(context)] += 1

            try:
                action = agents[player](obs)
            except Exception as exc:
                action_errors += 1
                raise RuntimeError(f"agent {player} failed at step {steps}: {exc}") from exc

            if trace_file:
                scored_options = (
                    score_trace(agents[player], obs, action, getattr(args, "trace_score_limit", 8))
                    if getattr(args, "trace_scores", False)
                    else []
                )
                trace_file.write(
                    json.dumps(
                        {
                            "game": game_index,
                            "step": steps,
                            "player": player,
                            "context": context,
                            "context_card_id": card_id(select.get("contextCard")),
                            "effect_card_id": card_id(select.get("effect")),
                            "select_type": select.get("type"),
                            "min_count": select.get("minCount"),
                            "max_count": select.get("maxCount"),
                            "option_count": len(select.get("option") or []),
                            "selection_deck_ids": visible_card_ids(select.get("deck")),
                            "options": [
                                compact_option(option)
                                for option in (select.get("option") or [])
                            ] if getattr(args, "trace_options", False) else [],
                            "action": action,
                            "own_hand_ids": acting_hand_ids(obs),
                            "snapshot": player_snapshot(obs),
                            "logs": compact_logs(obs.get("logs") or []),
                            "scores": scored_options,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

            obs = battle_select(action)
            final_obs = obs
            steps += 1
    finally:
        if trace_file:
            trace_file.close()
        battle_finish()

    final_current = (final_obs or {}).get("current") or {}
    return {
        "game": game_index,
        "seed": seed if seed is not None else "",
        "started": True,
        "steps": steps,
        "hit_max_steps": steps >= args.max_steps,
        "result": final_current.get("result"),
        "turn": final_current.get("turn"),
        "action_errors": action_errors,
        "trace": str(trace_path) if trace_path else "",
        "context_counts": dict(sorted(context_counts.items())),
        **player_snapshot(final_obs or {}),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local Pokemon TCG AI Battle games through the packaged cg engine."
    )
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    parser.add_argument("--agent-a", type=Path, default=DEFAULT_AGENT_DIR)
    parser.add_argument("--agent-b", type=Path, default=DEFAULT_AGENT_DIR)
    parser.add_argument("--deck-a", type=Path)
    parser.add_argument("--deck-b", type=Path)
    parser.add_argument("--games", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--trace-dir", type=Path, default=Path("analysis_outputs/traces"))
    parser.add_argument(
        "--no-trace",
        action="store_true",
        help="Do not create per-game trace files.",
    )
    parser.add_argument("--trace-scores", action="store_true", help="Include candidate score/reason data in traces when available.")
    parser.add_argument("--trace-score-limit", type=int, default=8, help="Number of top scored options to store per step.")
    parser.add_argument("--trace-options", action="store_true", help="Include compact identities for every legal option in traces.")
    parser.add_argument("--seed-base", type=int, help="Seed Python-side randomness as seed_base + game_index.")
    parser.add_argument(
        "--engine-seed", action="store_true",
        help="Pass the per-game seed to the local BattleStartSeeded API.",
    )
    parser.add_argument("--summary", type=Path, default=Path("analysis_outputs/local_battle_summary.jsonl"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.no_trace:
        args.trace_dir = None
    ensure_engine_on_path(args.engine_dir)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    with args.summary.open("w", encoding="utf-8") as summary_file:
        for game_index in range(args.games):
            result = run_game(args, game_index)
            summary_file.write(json.dumps(result, ensure_ascii=False) + "\n")
            print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
