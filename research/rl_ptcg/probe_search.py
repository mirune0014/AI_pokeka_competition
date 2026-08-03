"""Probe value-guided Search API decisions inside real local battles."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "infrastructure" / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "infrastructure" / "tools"))

from ptcg_common import ensure_engine_on_path, load_agent, pushd, read_deck

try:
    from .search_expert import choose_with_search, load_value_model
except ImportError:
    from search_expert import choose_with_search, load_value_model


def score_options(agent, raw_observation):
    module = agent.module
    converted = module.to_observation_class(raw_observation)
    values = []
    reasons = []
    with pushd(agent.agent_dir):
        for option in converted.select.option:
            result = module.score_option(converted, option)
            values.append(float(result[0] if isinstance(result, tuple) else result))
            reasons.append(str(result[1]) if isinstance(result, tuple) and len(result) > 1 else "")
    return converted, values, reasons


def compact_options(raw_observation, scores, reasons):
    keys = ("type", "area", "index", "playerIndex", "cardId", "attackId",
            "inPlayArea", "inPlayIndex", "number")
    options = (raw_observation.get("select") or {}).get("option") or []
    return [
        {"index": index, "score": scores[index], "reason": reasons[index],
         **{key: option.get(key) for key in keys if key in option}}
        for index, option in enumerate(options)
    ]


def evaluation_dict(value):
    return {
        "action": value.action,
        "values": [round(item, 5) for item in value.values],
        "mean": round(value.mean, 5),
        "stddev": round(value.stddev, 5),
        "downside": round(value.downside, 5),
    }


def run_game(args, game_index, model, basic_ids):
    from cg.game import battle_finish, battle_select, battle_start

    trainee_seat = game_index % 2
    trainee_dir = args.baseline.resolve()
    opponent_dir = args.opponent.resolve()
    trainee_deck = read_deck(trainee_dir / "deck.csv")
    opponent_deck = read_deck(opponent_dir / "deck.csv")
    decks = [trainee_deck, opponent_deck] if trainee_seat == 0 else [opponent_deck, trainee_deck]
    trainee = load_agent(trainee_dir, "probe_trainee_%d" % game_index)
    opponent = load_agent(opponent_dir, "probe_opponent_%d" % game_index)
    seed = args.seed + game_index
    random.seed(seed)
    rng = random.Random(seed)
    for agent in (trainee, opponent):
        module_random = getattr(agent.module, "random", None)
        if hasattr(module_random, "seed"):
            module_random.seed(seed)
    observation, start = battle_start(*decks)
    if not observation:
        return {"game": game_index, "status": "start_error", "error": str(start.errorType)}
    decisions = []
    applied_changes = 0
    final = observation
    try:
        for step in range(args.max_steps):
            current = observation.get("current") or {}
            select = observation.get("select") or {}
            if current.get("result") not in (None, -1) or not select.get("option"):
                break
            player = int(current.get("yourIndex", 0))
            if player == trainee_seat:
                baseline_action = trainee(observation)
                converted, scores, reasons = score_options(trainee, observation)
                with pushd(trainee.agent_dir):
                    matchup = str(trainee.module.detect_matchup(converted))
                action = baseline_action
                if (not args.only_matchup or matchup == args.only_matchup) and len(decisions) < args.max_decisions:
                    with pushd(trainee.agent_dir):
                        decision = choose_with_search(
                            observation, trainee.module, model, trainee_deck, opponent_deck,
                            scores, baseline_action, rng,
                            determinizations=args.determinizations,
                            top_options=args.top_options, max_actions=args.max_actions,
                            max_prompt_steps=args.max_prompt_steps,
                            improvement_margin=args.improvement_margin,
                            risk_penalty=args.risk_penalty, device=args.device,
                            basic_pokemon_ids=basic_ids, matchup=matchup,
                        )
                    decisions.append({
                        "step": step, "turn": current.get("turn"), "context": select.get("context"),
                        "matchup": matchup, "baseline": baseline_action,
                        "selected": decision.selected, "changed": decision.changed,
                        "reason": decision.reason, "determinizations": decision.determinizations,
                        "errors": decision.errors,
                        "options": compact_options(observation, scores, reasons),
                        "evaluations": [evaluation_dict(value) for value in decision.evaluations],
                    })
                    if args.apply_search and decision.changed:
                        action = decision.selected
                        applied_changes += 1
                observation = battle_select(action)
            else:
                observation = battle_select(opponent(observation))
            final = observation
    finally:
        battle_finish()
    result = ((final or {}).get("current") or {}).get("result")
    return {
        "game": game_index, "status": "complete", "seed": seed, "trainee_seat": trainee_seat,
        "result": result, "won": result == trainee_seat, "applied_changes": applied_changes,
        "decisions": decisions,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--opponent", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--games", type=int, default=2)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--determinizations", type=int, default=4)
    parser.add_argument("--top-options", type=int, default=6)
    parser.add_argument("--max-actions", type=int, default=24)
    parser.add_argument("--max-prompt-steps", type=int, default=12)
    parser.add_argument("--max-decisions", type=int, default=12)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--improvement-margin", type=float, default=0.08)
    parser.add_argument("--risk-penalty", type=float, default=0.25)
    parser.add_argument("--only-matchup")
    parser.add_argument("--apply-search", action="store_true")
    args = parser.parse_args()
    ensure_engine_on_path(args.engine_dir)
    from cg.api import all_card_data
    basic_ids = {card.cardId for card in all_card_data() if card.basic}
    model = load_value_model(args.checkpoint, args.device)
    rows = [run_game(args, game_index, model, basic_ids) for game_index in range(args.games)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="ascii")
    summary = {
        "games": len(rows), "wins": sum(bool(row.get("won")) for row in rows),
        "decisions": sum(len(row.get("decisions", [])) for row in rows),
        "changes": sum(sum(bool(value.get("changed")) for value in row.get("decisions", [])) for row in rows),
        "search_errors": sum(sum(int(value.get("errors", 0)) for value in row.get("decisions", [])) for row in rows),
    }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
