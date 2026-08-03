"""Deterministic, resumable public-state teacher pilot."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import blake2b, sha256
from itertools import combinations
import json
import math
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "infrastructure" / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "infrastructure" / "tools"))

from ptcg_common import ensure_engine_on_path, load_agent, pushd, read_deck
from extract_episode_decks import classify as classify_deck

try:
    from .label_replay_rollout import replay_decisions, replay_decks, replay_paths, target_seat_for_deck, nearest_agent_dirs
    from .probe_rollout import AgentChooser
    from .probe_search import score_options
    from .public_state import canonical_public_state, public_state_hash
    from .rollout_expert import choose_with_rollout
    from .teacher_statistics import summarize_teacher_batches
    from .belief import visible_player_cards
except ImportError:
    from label_replay_rollout import replay_decisions, replay_decks, replay_paths, target_seat_for_deck, nearest_agent_dirs
    from probe_rollout import AgentChooser
    from probe_search import score_options
    from public_state import canonical_public_state, public_state_hash
    from rollout_expert import choose_with_rollout
    from teacher_statistics import summarize_teacher_batches
    from belief import visible_player_cards

SCHEMA_VERSION = 1


def stable_seed(*parts):
    """Return a process-independent seed for frozen pilot work."""
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return int.from_bytes(blake2b(payload, digest_size=8).digest(), "big")


def complete_action_count(observation, baseline_action):
    select = (observation.get("select") or {})
    count = len(select.get("option") or [])
    minimum = max(0, int(select.get("minCount", 0) or 0))
    maximum = min(count, int(select.get("maxCount", minimum) or minimum))
    total = sum(math.comb(count, size) for size in range(minimum, maximum + 1))
    baseline = [int(item) for item in baseline_action]
    valid = minimum <= len(baseline) <= maximum and baseline == sorted(set(baseline)) and all(0 <= item < count for item in baseline)
    return total if valid else total + 1


def complete_actions(observation, baseline_action):
    select = (observation.get("select") or {})
    option_count = len(select.get("option") or [])
    minimum = max(0, int(select.get("minCount", 0) or 0))
    maximum = min(option_count, int(select.get("maxCount", minimum) or minimum))
    baseline = [int(item) for item in baseline_action]
    actions = [baseline]
    for size in range(minimum, maximum + 1):
        for action in combinations(range(option_count), size):
            candidate = list(action)
            if candidate != baseline:
                actions.append(candidate)
    return actions


def _stratum(matchup, weak, strong):
    if matchup in weak:
        return "weak"
    if matchup in strong:
        return "strong"
    return "neutral"


def _quotas(count):
    # Largest remainders make the specified 50/25/25 distribution exact.
    raw = {"weak": count * .5, "strong": count * .25, "neutral": count * .25}
    quotas = {name: int(value) for name, value in raw.items()}
    for name in sorted(raw, key=lambda key: (-(raw[key] - quotas[key]), key))[:count - sum(quotas.values())]:
        quotas[name] += 1
    return quotas


def _ordered(rows, seed):
    return sorted(rows, key=lambda row: (stable_seed(seed, row["public_state_hash"], row["replay_path"], row["step"]), row["public_state_hash"]))


def select_states(candidates, state_count, pilot_seed):
    """Select deterministic 50/25/25 strata and fill unavailable quotas."""
    unique = {}
    for row in candidates:
        unique.setdefault(row["public_state_hash"], row)
    buckets = defaultdict(list)
    for row in unique.values():
        buckets[row["sampling_stratum"]].append(row)
    chosen = []
    for name, quota in _quotas(state_count).items():
        chosen.extend(_ordered(buckets[name], pilot_seed)[:quota])
    chosen_ids = {row["public_state_hash"] for row in chosen}
    if len(chosen) < state_count:
        remaining = [row for row in unique.values() if row["public_state_hash"] not in chosen_ids]
        chosen.extend(_ordered(remaining, pilot_seed)[:state_count - len(chosen)])
    if len(chosen) != state_count:
        raise ValueError("insufficient eligible public states: requested %d, found %d" % (state_count, len(unique)))
    chosen = _ordered(chosen, pilot_seed)
    for index, row in enumerate(chosen):
        row["state_id"] = "state-%04d-%s" % (index, row["public_state_hash"][:12])
    return chosen


def collect_teacher_states(replay_source, baseline, contexts, state_count, max_complete_actions, pilot_seed, weak_matchups=(), strong_matchups=()):
    """Collect replay states without mutating engine state or replay ordering."""
    baseline = Path(baseline).resolve()
    target_deck = read_deck(baseline / "deck.csv")
    weak, strong = set(weak_matchups), set(strong_matchups)
    candidates = []
    for replay_path in replay_paths(Path(replay_source)):
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        try:
            seat = target_seat_for_deck(replay, target_deck)
        except ValueError:
            continue
        decks = replay_decks(replay)
        opponent_deck = decks.get(1 - seat)
        if opponent_deck is None:
            continue
        opponent_archetype = classify_deck(opponent_deck)
        episode = str((replay.get("info") or {}).get("EpisodeId") or replay_path.stem)
        agent = load_agent(baseline, "teacher_collect_%s" % sha256(str(replay_path).encode("utf-8")).hexdigest()[:16])
        # Do not reorder: some policy modules maintain per-replay scoring state.
        for step, observation, baseline_action in replay_decisions(replay, seat):
            context = int((observation.get("select") or {}).get("context", -1))
            if context not in contexts:
                continue
            converted, scores, _ = score_options(agent, observation)
            with pushd(agent.agent_dir):
                matchup = str(agent.module.detect_matchup(converted))
            action_count = complete_action_count(observation, baseline_action)
            if action_count < 2 or action_count > max_complete_actions:
                continue
            state_hash = public_state_hash(observation, seat)
            candidates.append({
                "episode_id": episode, "replay_path": str(replay_path.resolve()), "step": step,
                "seat": seat, "matchup": matchup, "context": context,
                "opponent_archetype": opponent_archetype,
                "baseline_action": list(baseline_action), "baseline_scores": list(scores),
                "candidate_actions": complete_actions(observation, baseline_action),
                "complete_action_count": action_count,
                "public_state_hash": state_hash, "public_state": canonical_public_state(observation, seat),
                "observation": observation, "target_deck": target_deck, "opponent_deck": opponent_deck,
                "sampling_stratum": _stratum(opponent_archetype, weak, strong),
            })
    return select_states(candidates, state_count, pilot_seed)


def _jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n" for row in rows), encoding="ascii")


def _read_jsonl(path):
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="ascii").splitlines() if line]


def parse_opponent_agents(values):
    result = defaultdict(list)
    for value in values:
        if "=" not in value:
            raise ValueError("--opponent-agent must be MATCHUP=PATH")
        matchup, path = value.split("=", 1)
        if not matchup or not path:
            raise ValueError("--opponent-agent must be MATCHUP=PATH")
        result[matchup].append(Path(path).resolve())
    return dict(result)


def policy_paths_for_state(state, opponent_agents, opponent_catalog, catalog_policy_count=1):
    paths = opponent_agents.get(state.get("opponent_archetype"), [])
    if not paths:
        paths = opponent_agents.get(state["matchup"], [])
    if paths:
        return paths
    if opponent_catalog:
        return [
            path for path, _metrics in nearest_agent_dirs(
                Path(opponent_catalog).resolve(), state["opponent_deck"], catalog_policy_count
            )
        ]
    raise ValueError("no opponent policy for matchup %s" % state["matchup"])


def public_catalog_policy_paths(state, opponent_catalog, catalog_policy_count=1):
    """Select a deterministic policy/deck population from public cards only."""
    current = (state["observation"].get("current") or {})
    players = current.get("players") or []
    seat = int(state["seat"])
    if len(players) != 2:
        raise ValueError("public deck belief requires two players")
    visible, known_prize = visible_player_cards(players[1 - seat], include_hand=False)
    visible_cards = [int(card_id) for card_id in visible + known_prize]
    visible_archetype = classify_deck(visible_cards)
    required = Counter(visible_cards)
    ranked = []
    for directory in sorted(Path(opponent_catalog).resolve().iterdir()):
        if not directory.is_dir() or not (directory / "main.py").is_file() or not (directory / "deck.csv").is_file():
            continue
        try:
            deck = read_deck(directory / "deck.csv")
        except (OSError, ValueError):
            continue
        counts = Counter(int(card_id) for card_id in deck)
        deficit = sum(max(0, count - counts[card_id]) for card_id, count in required.items())
        overlap = sum(min(count, counts[card_id]) for card_id, count in required.items())
        archetype = classify_deck(deck)
        archetype_match = visible_archetype != "unknown" and archetype == visible_archetype
        ranked.append({
            "path": directory, "deck": deck, "archetype": archetype,
            "compatible": deficit == 0, "archetype_match": archetype_match,
            "deficit": deficit, "overlap": overlap,
            "tie": stable_seed(state["public_state_hash"], directory.name),
        })
    if not ranked:
        raise ValueError("opponent catalog has no loadable agents")
    ranked.sort(key=lambda row: (
        row["compatible"], row["archetype_match"], -row["deficit"],
        row["overlap"], row["tie"],
    ), reverse=True)
    selected = []
    if visible_archetype == "unknown":
        seen_archetypes = set()
        for row in ranked:
            if row["archetype"] not in seen_archetypes:
                selected.append(row)
                seen_archetypes.add(row["archetype"])
                if len(selected) >= catalog_policy_count:
                    break
    for row in ranked:
        if row not in selected:
            selected.append(row)
            if len(selected) >= catalog_policy_count:
                break
    result = []
    for source in selected[:catalog_policy_count]:
        row = dict(source)
        if not row["compatible"]:
            counts = Counter(int(card_id) for card_id in row["deck"])
            for card_id, required_count in sorted(required.items()):
                while counts[card_id] < required_count:
                    removable = max(
                        (candidate for candidate in counts if counts[candidate] > required[candidate]),
                        key=lambda candidate: (counts[candidate] - required[candidate], candidate),
                    )
                    counts[removable] -= 1
                    counts[card_id] += 1
            row["deck"] = [
                card_id for card_id in sorted(counts)
                for _ in range(counts[card_id])
            ]
            row["synthetic_unknown_variant"] = True
        else:
            row["synthetic_unknown_variant"] = False
        result.append(row)
    return result


def run_state(state, batch, args, basic_ids, opponent_agents):
    seed = stable_seed(args.pilot_seed, state["state_id"], batch)
    baseline = load_agent(args.baseline.resolve(), "teacher_baseline_%s_%d" % (state["state_id"], batch))
    if args.deck_belief == "public-catalog":
        if not args.opponent_catalog:
            raise ValueError("public-catalog deck belief requires --opponent-catalog")
        population = public_catalog_policy_paths(
            state, args.opponent_catalog, args.catalog_policy_count
        )
        paths = [row["path"] for row in population]
        deck_hypotheses = [row["deck"] for row in population]
    else:
        paths = policy_paths_for_state(
            state, opponent_agents, args.opponent_catalog, args.catalog_policy_count
        )
        deck_hypotheses = [state["opponent_deck"]]
    unique_hypotheses = {}
    for deck in deck_hypotheses:
        unique_hypotheses.setdefault(tuple(sorted(int(card_id) for card_id in deck)), deck)
    deck_hypotheses = list(unique_hypotheses.values())
    policies = [load_agent(path, "teacher_opponent_%s_%d_%d" % (state["state_id"], batch, index)) for index, path in enumerate(paths)]
    continuation_paths = [args.baseline.resolve()]
    for path in args.continuation_agent:
        resolved = path.resolve()
        if resolved not in continuation_paths:
            continuation_paths.append(resolved)
    continuations = [
        baseline if path == args.baseline.resolve() else load_agent(
            path, "teacher_continuation_%s_%d_%d" % (state["state_id"], batch, index)
        )
        for index, path in enumerate(continuation_paths)
    ]
    modules = {int(state["seat"]): AgentChooser(baseline), 1 - int(state["seat"]): AgentChooser(policies[0])}
    particles = (
        int(args.particles_per_scenario) * len(policies)
        * len(deck_hypotheses) * len(continuations)
    )
    decision = choose_with_rollout(
        state["observation"], modules, state["target_deck"], deck_hypotheses[0], state["baseline_scores"], state["baseline_action"], random.Random(seed),
        determinizations=particles, max_steps=args.max_rollout_steps, top_options=args.max_complete_actions,
        max_actions=args.max_complete_actions, basic_pokemon_ids=basic_ids, opponent_policy_modules=[AgentChooser(agent) for agent in policies],
        your_policy_modules=[AgentChooser(agent) for agent in continuations],
        opponent_deck_hypotheses=deck_hypotheses[1:], candidate_mode="complete",
        max_complete_actions=args.max_complete_actions, return_scenario_values=True,
    )
    rows = []
    ranked = sorted(
        range(len(state["baseline_scores"])),
        key=lambda index: (-float(state["baseline_scores"][index]), index),
    )
    rule_top3_pool = set(ranked[:3]) | set(int(index) for index in state["baseline_action"])
    for value in decision.scenario_values or []:
        rows.append({**value, "state_id": state["state_id"], "episode_id": state["episode_id"], "batch_id": batch,
                     "baseline_action": state["baseline_action"], "pilot_seed": args.pilot_seed, "rollout_seed": seed,
                     "matchup": state["matchup"], "opponent_archetype": state.get("opponent_archetype"),
                     "sampling_stratum": state["sampling_stratum"],
                     "outside_rule_top3": any(
                         int(index) not in rule_top3_pool for index in value["action"]
                     ),
                     "opponent_policy_path": str(paths[int(value["opponent_policy_index"])])})
    status = {
        "state_id": state["state_id"], "batch_id": batch,
        "status": "complete" if rows else "failed",
        "reason": decision.reason, "determinizations": decision.determinizations,
        "errors": decision.errors, "scenario_row_count": len(rows),
        "scenario_errors": getattr(decision, "scenario_errors", None) or [],
        "opponent_policy_paths": [str(path) for path in paths],
        "continuation_policy_paths": [str(path) for path in continuation_paths],
        "deck_hypothesis_count": len(deck_hypotheses),
        "synthetic_deck_hypotheses": sum(
            bool(row.get("synthetic_unknown_variant")) for row in population
        ) if args.deck_belief == "public-catalog" else 0,
        "rollout_seed": seed,
    }
    return rows, status


def _sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replays", type=Path)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--state-count", type=int, default=512)
    parser.add_argument("--pilot-seed", type=int, default=0)
    parser.add_argument("--context", action="append", type=int, default=[])
    parser.add_argument("--weak-matchup", action="append", default=[])
    parser.add_argument("--strong-matchup", action="append", default=[])
    parser.add_argument("--max-complete-actions", type=int, default=64)
    parser.add_argument("--batches", type=int, default=1)
    parser.add_argument("--particles-per-scenario", type=int, default=2)
    parser.add_argument("--max-rollout-steps", type=int, default=1000)
    parser.add_argument("--opponent-agent", action="append", default=[])
    parser.add_argument("--opponent-catalog", type=Path)
    parser.add_argument("--catalog-policy-count", type=int, default=1)
    parser.add_argument("--deck-belief", choices=("exact", "public-catalog"), default="exact")
    parser.add_argument("--continuation-agent", action="append", type=Path, default=[])
    parser.add_argument("--collect-only", action="store_true")
    parser.add_argument("--bootstrap-repetitions", type=int, default=1000)
    args = parser.parse_args(argv)
    args.context = args.context or [0]
    if args.state_count < 1 or args.batches < 1 or args.particles_per_scenario < 1 or args.catalog_policy_count < 1:
        parser.error("state-count, batches, particles-per-scenario, and catalog-policy-count must be positive")
    output = args.output_dir.resolve()
    states_path, outcomes_path = output / "states.jsonl", output / "particle_outcomes.jsonl"
    statuses_path = output / "state_batches.jsonl"
    manifest_path, report_path = output / "manifest.json", output / "report.json"
    ensure_engine_on_path(args.engine_dir)
    states = _read_jsonl(states_path)
    if not states:
        states = collect_teacher_states(args.replays, args.baseline, set(args.context), args.state_count, args.max_complete_actions, args.pilot_seed, args.weak_matchup, args.strong_matchup)
        _jsonl(states_path, states)
    parameter_exclusions = (
        "replays", "engine_dir", "baseline", "output_dir", "opponent_agent",
        "opponent_catalog", "continuation_agent",
    )
    manifest = {"schema_version": SCHEMA_VERSION, "pilot_seed": args.pilot_seed, "contexts": args.context,
                "state_ids": [state["state_id"] for state in states], "replay_sha256": {state["replay_path"]: _sha(state["replay_path"]) for state in states},
                "baseline": str(args.baseline.resolve()), "policy_paths": {matchup: [str(path.resolve()) for path in paths] for matchup, paths in parse_opponent_agents(args.opponent_agent).items()}, "opponent_catalog": str(args.opponent_catalog.resolve()) if args.opponent_catalog else None,
                "continuation_policy_paths": [str(path.resolve()) for path in args.continuation_agent],
                "parameters": {key: value for key, value in vars(args).items() if key not in parameter_exclusions}}
    output.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="ascii")
    if args.collect_only:
        return
    from cg.api import all_card_data
    basic_ids = {card.cardId for card in all_card_data() if card.basic}
    opponent_agents = parse_opponent_agents(args.opponent_agent)
    outcomes = _read_jsonl(outcomes_path)
    statuses = _read_jsonl(statuses_path)
    completed = {(row["state_id"], row["batch_id"]) for row in statuses}
    for batch in range(args.batches):
        for state in states:
            if (state["state_id"], batch) not in completed:
                rows, status = run_state(state, batch, args, basic_ids, opponent_agents)
                outcomes.extend(rows)
                statuses.append(status)
                _jsonl(outcomes_path, outcomes)
                _jsonl(statuses_path, statuses)
    failures = [row for row in statuses if row.get("status") != "complete"]
    expected = {(state["state_id"], batch) for state in states for batch in range(args.batches)}
    observed = {(row["state_id"], row["batch_id"]) for row in statuses}
    missing = sorted(expected - observed)
    if failures or missing:
        report = {
            "valid": False,
            "selected_state_count": len(states),
            "batch_count": args.batches,
            "failed_state_batches": failures,
            "missing_state_batches": [
                {"state_id": state_id, "batch_id": batch_id}
                for state_id, batch_id in missing
            ],
        }
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="ascii")
        return
    report = summarize_teacher_batches(outcomes, args.bootstrap_repetitions, stable_seed(args.pilot_seed, "bootstrap"))
    report["valid"] = True
    report["selected_state_count"] = len(states)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="ascii")


if __name__ == "__main__":
    main()
