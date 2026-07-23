"""Label real Kaggle replay states with the full-rollout Search API expert."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from ptcg_common import ensure_engine_on_path, load_agent, pushd, read_deck

try:
    from .belief import SearchGuess
    from .collect_trajectories import label_terminal_records
    from .probe_rollout import AgentChooser
    from .probe_search import compact_options, evaluation_dict, score_options
    from .rollout_expert import choose_with_rollout
    from .sparse_expert import make_observation_example
    from .trajectory import make_record, write_jsonl
except ImportError:
    from belief import SearchGuess
    from collect_trajectories import label_terminal_records
    from probe_rollout import AgentChooser
    from probe_search import compact_options, evaluation_dict, score_options
    from rollout_expert import choose_with_rollout
    from sparse_expert import make_observation_example
    from trajectory import make_record, write_jsonl


def replay_decks(replay):
    """Return the submitted 60-card action for each replay seat."""
    decks = {}
    for step in replay.get("steps", []):
        for seat, record in enumerate(step):
            action = record.get("action") if isinstance(record, dict) else None
            if isinstance(action, list) and len(action) == 60 and all(isinstance(x, int) for x in action):
                decks.setdefault(seat, list(action))
        if len(decks) == 2:
            break
    return decks


def target_seat_for_deck(replay, target_deck):
    signature = Counter(int(card_id) for card_id in target_deck)
    matches = [seat for seat, deck in replay_decks(replay).items() if Counter(deck) == signature]
    if len(matches) != 1:
        raise ValueError("replay does not contain exactly one matching target deck")
    return matches[0]


def replay_decisions(replay, seat):
    """Yield observations paired with the action stored on the following step."""
    steps = replay.get("steps", [])
    for index in range(max(0, len(steps) - 1)):
        if seat >= len(steps[index]) or seat >= len(steps[index + 1]):
            continue
        record = steps[index][seat]
        following = steps[index + 1][seat]
        observation = record.get("observation") if isinstance(record, dict) else None
        action = following.get("action") if isinstance(following, dict) else None
        if not isinstance(observation, dict) or not isinstance(action, list) or not action:
            continue
        current = observation.get("current") or {}
        select = observation.get("select") or {}
        options = select.get("option") or []
        if current.get("result") not in (None, -1) or current.get("yourIndex") != seat or not options:
            continue
        if not all(isinstance(value, int) and 0 <= value < len(options) for value in action):
            continue
        if not (int(select.get("minCount", 0)) <= len(action) <= int(select.get("maxCount", len(options)))):
            continue
        yield index, observation, list(action)


def replay_result(replay):
    rewards = replay.get("rewards") or []
    winners = [seat for seat, reward in enumerate(rewards) if reward == 1]
    return winners[0] if len(winners) == 1 else 2


def should_label_decision(replay_step, context, replay_steps, contexts):
    """Apply optional exact-step and selection-context filters."""
    return (
        (not replay_steps or int(replay_step) in replay_steps)
        and int(context) in contexts
    )


def _zone_ids(player, name):
    values = player.get(name) or []
    output = []
    for card in values:
        if not isinstance(card, dict) or card.get("id") is None:
            raise ValueError("full replay zone %s contains an unknown card" % name)
        output.append(int(card["id"]))
    return output


def exact_search_guess(replay, replay_step, target_seat, public_observation):
    """Recover exact pre-action hidden zones from the visualizer state."""
    steps = replay.get("steps") or []
    if not steps or not steps[0] or replay_step <= 0:
        return None
    visual = steps[0][0].get("visualize") or []
    if replay_step >= len(visual):
        return None
    previous = visual[replay_step - 1].get("current") or {}
    players = previous.get("players") or []
    if len(players) != 2:
        return None
    yours = players[target_seat]
    opponent = players[1 - target_seat]
    public_players = (public_observation.get("current") or {}).get("players") or []
    if len(public_players) != 2:
        return None
    public_opponent = public_players[1 - target_seat]
    opponent_active = []
    active = public_opponent.get("active") or []
    if active and active[0] is None:
        full_active = opponent.get("active") or []
        if not full_active or not isinstance(full_active[0], dict) or full_active[0].get("id") is None:
            return None
        opponent_active = [int(full_active[0]["id"])]
    guess = SearchGuess(
        your_deck=_zone_ids(yours, "deck"),
        your_prize=_zone_ids(yours, "prize"),
        opponent_deck=_zone_ids(opponent, "deck"),
        opponent_prize=_zone_ids(opponent, "prize"),
        opponent_hand=_zone_ids(opponent, "hand"),
        opponent_active=opponent_active,
        unused_your_cards=[],
        unused_opponent_cards=[],
    )
    expected = (
        int(public_players[target_seat].get("deckCount", 0)),
        len(public_players[target_seat].get("prize") or []),
        int(public_opponent.get("deckCount", 0)),
        len(public_opponent.get("prize") or []),
        int(public_opponent.get("handCount", 0)),
    )
    actual = (
        len(guess.your_deck), len(guess.your_prize), len(guess.opponent_deck),
        len(guess.opponent_prize), len(guess.opponent_hand),
    )
    return guess if actual == expected else None


def replay_paths(path):
    if path.is_file():
        return [path]
    return sorted(path.glob("episode_*_replay.json"))


def nearest_agent_dirs(catalog, deck, limit=1):
    """Return the closest available policies by 60-card multiset distance."""
    if limit < 1:
        raise ValueError("limit must be positive")
    target = Counter(int(card_id) for card_id in deck)
    ranked = []
    for directory in sorted(catalog.iterdir()):
        deck_path = directory / "deck.csv"
        if not directory.is_dir() or not deck_path.is_file() or not (directory / "main.py").is_file():
            continue
        try:
            candidate = Counter(read_deck(deck_path))
        except (OSError, ValueError):
            continue
        overlap = sum((target & candidate).values())
        distance = sum((target - candidate).values()) + sum((candidate - target).values())
        ranked.append((overlap, -distance, directory.name, directory))
    if not ranked:
        raise ValueError("opponent catalog has no loadable agents")
    ranked.sort(key=lambda value: value[:3], reverse=True)
    return [
        (value[3], {"overlap": value[0], "distance": -value[1]})
        for value in ranked[:limit]
    ]


def nearest_agent_dir(catalog, deck):
    """Choose the closest available policy by 60-card multiset distance."""
    return nearest_agent_dirs(catalog, deck, 1)[0]


def label_replay(args, replay_path, basic_ids):
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    target_deck = read_deck(args.baseline.resolve() / "deck.csv")
    try:
        target_seat = target_seat_for_deck(replay, target_deck)
    except ValueError as exc:
        return {"replay": str(replay_path), "status": "skipped", "reason": str(exc)}, [], []
    decks = replay_decks(replay)
    opponent_deck = decks.get(1 - target_seat)
    if opponent_deck is None:
        return {"replay": str(replay_path), "status": "skipped", "reason": "missing opponent deck"}, [], []
    result = replay_result(replay)
    if args.losses_only and result == target_seat:
        return {"replay": str(replay_path), "status": "skipped", "reason": "target won"}, [], []

    episode_id = str(replay.get("info", {}).get("EpisodeId") or replay_path.stem)
    teams = replay.get("info", {}).get("TeamNames") or []
    opponent = str(teams[1 - target_seat]) if len(teams) > 1 else "unknown"
    agent = load_agent(args.baseline.resolve(), "replay_label_%s" % episode_id)
    opponent_agent_dirs = [path.resolve() for path in args.opponent_agent]
    opponent_match = None
    if not opponent_agent_dirs and args.opponent_catalog:
        opponent_agent_dir, opponent_match = nearest_agent_dir(args.opponent_catalog.resolve(), opponent_deck)
        opponent_agent_dirs = [opponent_agent_dir]
    opponent_agents = [
        load_agent(path, "replay_opponent_%s_%d" % (episode_id, index))
        for index, path in enumerate(opponent_agent_dirs)
    ] or [agent]
    opponent_choosers = [AgentChooser(value) for value in opponent_agents]
    modules = {
        target_seat: AgentChooser(agent),
        1 - target_seat: opponent_choosers[0],
    }
    decisions = []
    examples = []
    trajectories = []
    seen = 0
    for replay_step, observation, recorded_action in replay_decisions(replay, target_seat):
        context = int((observation.get("select") or {}).get("context", -1))
        if not should_label_decision(replay_step, context, args.replay_step, args.context):
            continue
        if seen >= args.max_decisions:
            break
        seen += 1
        converted, scores, reasons = score_options(agent, observation)
        with pushd(agent.agent_dir):
            matchup = str(agent.module.detect_matchup(converted))
        rng = random.Random(args.seed + int(episode_id) * 1009 + replay_step)
        guess = (
            None if args.disable_exact_hidden
            else exact_search_guess(replay, replay_step, target_seat, observation)
        )
        decision = choose_with_rollout(
            observation, modules, target_deck, opponent_deck, scores, recorded_action, rng,
            determinizations=args.determinizations,
            max_steps=args.max_rollout_steps,
            top_options=args.top_options,
            max_actions=args.max_actions,
            improvement_margin=args.improvement_margin,
            risk_penalty=args.risk_penalty,
            confidence_z=args.confidence_z,
            min_successful_determinizations=args.min_successful_determinizations,
            basic_pokemon_ids=basic_ids,
            search_guesses=[guess] if guess is not None else None,
            opponent_policy_modules=opponent_choosers,
        )
        decisions.append({
            "step": replay_step, "turn": (observation.get("current") or {}).get("turn"),
            "context": context, "matchup": matchup, "recorded": recorded_action,
            "selected": decision.selected, "changed": decision.changed,
            "reason": decision.reason, "determinizations": decision.determinizations,
            "errors": decision.errors, "options": compact_options(observation, scores, reasons),
            "exact_hidden": guess is not None,
            "evaluations": [evaluation_dict(value) for value in decision.evaluations],
        })
        if decision.evaluations and decision.determinizations > 0:
            with pushd(agent.agent_dir):
                examples.append(make_observation_example(
                    converted, scores, recorded_action, decision.selected,
                    score_option=agent.module.score_option,
                    option_card=agent.module.option_card,
                    option_target=agent.module.option_target,
                    detect_matchup=agent.module.detect_matchup,
                    top_n=args.top_options,
                    opponent=opponent,
                    metadata={"episode_id": episode_id, "replay_step": replay_step},
                ))
            trajectories.append(make_record(
                observation, episode_id, replay_step, scores, recorded_action, decision.selected,
                matchup=matchup, opponent=opponent, opponent_deck=opponent_deck,
                seed=args.seed, perspective_seat=target_seat,
            ))
    trajectories = label_terminal_records(trajectories, result, target_seat)
    return {
        "replay": str(replay_path), "episode_id": episode_id, "status": "complete",
        "target_seat": target_seat, "result": result, "opponent": opponent,
        "opponent_agent": str(opponent_agent_dirs[0]) if opponent_agent_dirs else None,
        "opponent_agents": [str(path) for path in opponent_agent_dirs],
        "opponent_agent_match": opponent_match,
        "decisions": decisions,
    }, examples, trajectories


def write_labeled_outputs(args, labeled):
    reports = [row[0] for row in labeled]
    examples = [example for row in labeled for example in row[1]]
    trajectories = [record for row in labeled for record in row[2]]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reports, indent=2, sort_keys=True) + "\n", encoding="ascii")
    if args.expert_output:
        args.expert_output.write_text(
            "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in examples),
            encoding="ascii",
        )
    if args.trajectory_output:
        write_jsonl(args.trajectory_output, trajectories)
    return reports, examples, trajectories


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--opponent-agent", type=Path, action="append", default=[])
    parser.add_argument("--opponent-catalog", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expert-output", type=Path)
    parser.add_argument("--trajectory-output", type=Path)
    parser.add_argument("--losses-only", action="store_true")
    parser.add_argument("--disable-exact-hidden", action="store_true")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--determinizations", type=int, default=15)
    parser.add_argument("--top-options", type=int, default=4)
    parser.add_argument("--max-actions", type=int, default=6)
    parser.add_argument("--max-decisions", type=int, default=8)
    parser.add_argument("--max-rollout-steps", type=int, default=1000)
    parser.add_argument("--improvement-margin", type=float, default=0.2)
    parser.add_argument("--risk-penalty", type=float, default=0.35)
    parser.add_argument("--confidence-z", type=float, default=1.64)
    parser.add_argument("--min-successful-determinizations", type=int)
    parser.add_argument("--context", action="append", type=int, default=[])
    parser.add_argument(
        "--replay-step", action="append", type=int, default=[],
        help="label only these zero-based replay step indices; may be repeated",
    )
    parser.add_argument("--checkpoint-every", type=int, default=1)
    args = parser.parse_args()
    if not args.context:
        args.context = [0]
    ensure_engine_on_path(args.engine_dir)
    from cg.api import all_card_data
    basic_ids = {card.cardId for card in all_card_data() if card.basic}
    paths = replay_paths(args.path)
    labeled = []
    for index, path in enumerate(paths, start=1):
        labeled.append(label_replay(args, path, basic_ids))
        if args.checkpoint_every > 0 and (
            index % args.checkpoint_every == 0 or index == len(paths)
        ):
            reports, examples, trajectories = write_labeled_outputs(args, labeled)
            print(json.dumps({
                "progress": index, "replays": len(paths),
                "completed": sum(row.get("status") == "complete" for row in reports),
                "examples": len(examples),
            }, sort_keys=True), flush=True)
    reports, examples, trajectories = write_labeled_outputs(args, labeled)
    print(json.dumps({
        "replays": len(reports),
        "completed": sum(row.get("status") == "complete" for row in reports),
        "decisions": sum(len(row.get("decisions", [])) for row in reports),
        "changes": sum(sum(bool(value.get("changed")) for value in row.get("decisions", [])) for row in reports),
        "examples": len(examples),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
