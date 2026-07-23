"""Probe full-game Search API rollout decisions inside local battles."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from ptcg_common import dataclass_to_dict, ensure_engine_on_path, load_agent, pushd, read_deck

try:
    from .probe_search import compact_options, evaluation_dict, score_options
    from .rollout_expert import choose_with_rollout
    from .sparse_expert import make_observation_example
    from .trajectory import make_record, write_jsonl
    from .collect_trajectories import label_terminal_records
except ImportError:
    from probe_search import compact_options, evaluation_dict, score_options
    from rollout_expert import choose_with_rollout
    from sparse_expert import make_observation_example
    from trajectory import make_record, write_jsonl
    from collect_trajectories import label_terminal_records


class AgentChooser:
    def __init__(self, agent):
        self.agent = agent

    def choose_options(self, observation):
        chooser = getattr(self.agent.module, "choose_options", None)
        if not callable(chooser):
            return self.agent(dataclass_to_dict(observation))
        with pushd(self.agent.agent_dir):
            return chooser(observation)


def run_game(args, game_index, basic_ids):
    from cg.game import battle_finish, battle_select, battle_start

    trainee_seat = game_index % 2
    trainee_dir = args.baseline.resolve()
    opponent_dir = args.opponent.resolve()
    trainee_deck = read_deck(trainee_dir / "deck.csv")
    opponent_deck = read_deck(opponent_dir / "deck.csv")
    opponent_hypotheses = [
        read_deck(path.resolve() / "deck.csv") for path in (args.opponent_deck_hypothesis or [])
    ]
    opponent_deck_hypothesis = opponent_hypotheses[0] if opponent_hypotheses else opponent_deck
    decks = [trainee_deck, opponent_deck] if trainee_seat == 0 else [opponent_deck, trainee_deck]
    trainee = load_agent(trainee_dir, "rollout_trainee_%d" % game_index)
    opponent = load_agent(opponent_dir, "rollout_opponent_%d" % game_index)
    if args.rollout_opponent_agent:
        opponent_rollout_agent = load_agent(
            args.rollout_opponent_agent.resolve(), "rollout_policy_%d" % game_index
        )
    else:
        opponent_rollout_agent = trainee if args.rollout_opponent_policy == "self" else opponent
    modules = {trainee_seat: AgentChooser(trainee), 1 - trainee_seat: AgentChooser(opponent_rollout_agent)}
    seed = args.seed + game_index
    random.seed(seed)
    rng = random.Random(seed)
    for agent in {trainee, opponent, opponent_rollout_agent}:
        module_random = getattr(agent.module, "random", None)
        if hasattr(module_random, "seed"):
            module_random.seed(seed)
    observation, start = battle_start(*decks)
    if not observation:
        return {"game": game_index, "status": "start_error", "error": str(start.errorType)}
    decisions = []
    expert_examples = []
    expert_trajectories = []
    final = observation
    try:
        for step in range(args.max_battle_steps):
            current = observation.get("current") or {}
            select = observation.get("select") or {}
            if current.get("result") not in (None, -1) or not select.get("option"):
                break
            player = int(current.get("yourIndex", 0))
            if player == trainee_seat:
                baseline_action = trainee(observation)
                action = baseline_action
                context = int(select.get("context", -1))
                if context in args.context and len(decisions) < args.max_decisions:
                    converted, scores, reasons = score_options(trainee, observation)
                    with pushd(trainee.agent_dir):
                        matchup = str(trainee.module.detect_matchup(converted))
                    if args.only_matchup and matchup not in args.only_matchup:
                        observation = battle_select(action)
                        final = observation
                        continue
                    decision = choose_with_rollout(
                        observation, modules, trainee_deck, opponent_deck_hypothesis,
                        scores, baseline_action, rng,
                        determinizations=args.determinizations,
                        max_steps=args.max_rollout_steps,
                        top_options=args.top_options,
                        max_actions=args.max_actions,
                        improvement_margin=args.improvement_margin,
                        risk_penalty=args.risk_penalty,
                        confidence_z=args.confidence_z,
                        min_successful_determinizations=args.min_successful_determinizations,
                        basic_pokemon_ids=basic_ids,
                        opponent_deck_hypotheses=opponent_hypotheses[1:],
                        require_unique_hypothesis=args.require_unique_hypothesis,
                        hypothesis_strategy=args.hypothesis_strategy,
                    )
                    decisions.append({
                        "step": step, "turn": current.get("turn"), "context": context,
                        "matchup": matchup,
                        "baseline": baseline_action, "selected": decision.selected,
                        "changed": decision.changed, "reason": decision.reason,
                        "determinizations": decision.determinizations, "errors": decision.errors,
                        "options": compact_options(observation, scores, reasons),
                        "evaluations": [evaluation_dict(value) for value in decision.evaluations],
                    })
                    if decision.evaluations and decision.determinizations > 0:
                        with pushd(trainee.agent_dir):
                            expert_examples.append(make_observation_example(
                                converted, scores, baseline_action, decision.selected,
                                score_option=trainee.module.score_option,
                                option_card=trainee.module.option_card,
                                option_target=trainee.module.option_target,
                                detect_matchup=trainee.module.detect_matchup,
                                top_n=args.top_options,
                                opponent=args.opponent.name,
                                metadata={
                                    "game": game_index, "step": step, "turn": current.get("turn"),
                                    "seed": seed, "determinizations": decision.determinizations,
                                    "errors": decision.errors,
                                },
                            ))
                        expert_trajectories.append(make_record(
                            observation, "rollout-%06d" % (args.seed + game_index),
                            len(expert_trajectories), scores, baseline_action, decision.selected,
                            matchup="archaludon", opponent=args.opponent.name,
                            opponent_deck=opponent_deck_hypothesis, seed=seed,
                        ))
                    if args.apply_rollout and decision.changed:
                        action = decision.selected
                observation = battle_select(action)
            else:
                observation = battle_select(opponent(observation))
            final = observation
    finally:
        battle_finish()
    result = ((final or {}).get("current") or {}).get("result")
    expert_trajectories = label_terminal_records(expert_trajectories, result, trainee_seat)
    return {
        "game": game_index, "status": "complete", "seed": seed,
        "trainee_seat": trainee_seat, "result": result, "won": result == trainee_seat,
        "decisions": decisions,
    }, expert_examples, expert_trajectories


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--opponent", type=Path, required=True)
    parser.add_argument("--opponent-deck-hypothesis", action="append", type=Path)
    parser.add_argument("--rollout-opponent-policy", choices=("exact", "self"), default="exact")
    parser.add_argument("--rollout-opponent-agent", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expert-output", type=Path)
    parser.add_argument("--trajectory-output", type=Path)
    parser.add_argument("--games", type=int, default=2)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--determinizations", type=int, default=8)
    parser.add_argument("--top-options", type=int, default=4)
    parser.add_argument("--max-actions", type=int, default=8)
    parser.add_argument("--max-decisions", type=int, default=8)
    parser.add_argument("--max-rollout-steps", type=int, default=1000)
    parser.add_argument("--max-battle-steps", type=int, default=1000)
    parser.add_argument("--improvement-margin", type=float, default=0.15)
    parser.add_argument("--risk-penalty", type=float, default=0.35)
    parser.add_argument("--confidence-z", type=float, default=1.0)
    parser.add_argument("--min-successful-determinizations", type=int)
    parser.add_argument("--context", action="append", type=int, default=[])
    parser.add_argument("--only-matchup", action="append", default=[])
    parser.add_argument("--apply-rollout", action="store_true")
    parser.add_argument("--require-unique-hypothesis", action="store_true")
    parser.add_argument("--hypothesis-strategy", choices=("robust", "first", "unique"), default="robust")
    args = parser.parse_args()
    if not args.context:
        args.context = [0]
    ensure_engine_on_path(args.engine_dir)
    from cg.api import all_card_data
    basic_ids = {card.cardId for card in all_card_data() if card.basic}
    results = [run_game(args, game_index, basic_ids) for game_index in range(args.games)]
    rows = [result[0] if isinstance(result, tuple) else result for result in results]
    examples = [example for result in results if isinstance(result, tuple) for example in result[1]]
    trajectories = [record for result in results if isinstance(result, tuple) for record in result[2]]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="ascii")
    if args.expert_output:
        args.expert_output.parent.mkdir(parents=True, exist_ok=True)
        args.expert_output.write_text(
            "".join(json.dumps(example, sort_keys=True, separators=(",", ":")) + "\n" for example in examples),
            encoding="ascii",
        )
    if args.trajectory_output:
        args.trajectory_output.parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(args.trajectory_output, trajectories)
    print(json.dumps({
        "games": len(rows), "wins": sum(bool(row.get("won")) for row in rows),
        "decisions": sum(len(row.get("decisions", [])) for row in rows),
        "changes": sum(sum(bool(value.get("changed")) for value in row.get("decisions", [])) for row in rows),
        "successful_determinizations": sum(sum(int(value.get("determinizations", 0)) for value in row.get("decisions", [])) for row in rows),
        "search_errors": sum(sum(int(value.get("errors", 0)) for value in row.get("decisions", [])) for row in rows),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
