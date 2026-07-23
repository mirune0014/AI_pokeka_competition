"""Rebuild all-legal-option examples from saved replay rollout labels."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from ptcg_common import ensure_engine_on_path, load_agent, pushd, read_deck

try:
    from .label_replay_rollout import replay_decisions, replay_decks, target_seat_for_deck
    from .belief import compatible_deck_hypotheses, visible_player_cards
    from .probe_search import score_options
    from .sparse_expert import make_observation_example
except ImportError:
    from label_replay_rollout import replay_decisions, replay_decks, target_seat_for_deck
    from belief import compatible_deck_hypotheses, visible_player_cards
    from probe_search import score_options
    from sparse_expert import make_observation_example


PUBLIC_MATCHUP_MARKERS = [
    ("marnie", {646, 647, 648, 1259}),
    ("starmie", {1030, 1031, 860, 861}),
    ("archaludon", {169, 190, 666, 1244}),
    ("crustle", {58, 344, 345, 607}),
    ("abomasnow", {721, 722, 723}),
    ("lucario", {677, 678}),
    ("hop", {288, 289, 299, 304, 307, 308, 309, 310, 878, 879}),
    ("chandelure", {97, 98, 164, 494}),
    ("alakazam", {245, 743}),
    ("mewtwo", {400, 401, 431, 434}),
    ("okidogi", {116, 675, 676, 1051, 1052}),
    ("iono", {265, 266, 268, 269, 270, 271}),
    ("ogerpon", {95, 96, 99, 108, 117, 349, 358, 370, 386}),
    ("dragapult", {120, 121}),
    ("cynthia", {341, 342, 379, 380, 381}),
]


def label_paths(directories, files):
    paths = list(files or [])
    for directory in directories or []:
        paths.extend(directory.glob("live_catalog_*.json"))
        paths.extend(directory.glob("live_exactopp_*.json"))
    return sorted(set(path.resolve() for path in paths))


def label_reports(paths):
    for path in paths:
        payload = json.loads(path.read_text(encoding="ascii"))
        reports = payload if isinstance(payload, list) else [payload]
        for report in reports:
            if not isinstance(report, dict):
                raise ValueError("invalid replay label in %s" % path)
            yield path, report


def replay_index(directories):
    output = {}
    for directory in directories:
        for path in directory.glob("episode_*_replay.json"):
            episode_id = path.name[len("episode_"):-len("_replay.json")]
            previous = output.get(episode_id)
            if previous is not None and previous.resolve() != path.resolve():
                raise ValueError("duplicate replay file: " + episode_id)
            output[episode_id] = path
    return output


def load_deck_catalog(directory):
    if directory is None:
        return []
    output = []
    seen = set()
    for child in sorted(directory.iterdir()):
        deck_path = child / "deck.csv"
        if not child.is_dir() or not deck_path.is_file():
            continue
        try:
            deck = read_deck(deck_path)
        except (OSError, ValueError):
            continue
        signature = tuple(sorted(map(int, deck)))
        if len(signature) != 60 or signature in seen:
            continue
        seen.add(signature)
        output.append(list(map(int, deck)))
    return output


def load_replay_deck_catalog(directories, target_deck):
    output = []
    seen = set()
    for directory in directories or []:
        for path in sorted(directory.glob("episode_*_replay.json")):
            replay = json.loads(path.read_text(encoding="utf-8"))
            try:
                target_seat = target_seat_for_deck(replay, target_deck)
            except ValueError:
                continue
            deck = replay_decks(replay).get(1 - target_seat)
            signature = tuple(sorted(map(int, deck or [])))
            if len(signature) != 60 or signature in seen:
                continue
            seen.add(signature)
            output.append(list(map(int, deck)))
    return output


def unique_decks(decks):
    output = []
    seen = set()
    for deck in decks:
        signature = tuple(sorted(map(int, deck)))
        if len(signature) == 60 and signature not in seen:
            seen.add(signature)
            output.append(list(map(int, deck)))
    return output


def public_belief_features(observation, deck_catalog):
    if not deck_catalog:
        return {}
    hypotheses = compatible_deck_hypotheses(observation, deck_catalog)
    count = len(hypotheses)
    features = {
        "belief_hypothesis_count=%s" % (count if count <= 10 else "plus"): 1.0,
        "belief_unique": 1.0 if count == 1 else 0.0,
    }
    if count:
        mass = 1.0 / count
        for deck in hypotheses:
            payload = ",".join(map(str, sorted(deck))).encode("ascii")
            signature = hashlib.sha1(payload).hexdigest()[:12]
            features["belief_signature=" + signature] = mass
    return features


def public_matchup(observation, fallback="generic"):
    current = getattr(observation, "current", None)
    players = list(getattr(current, "players", []) or [])
    your_index = int(getattr(current, "yourIndex", 0) or 0)
    if len(players) != 2:
        return fallback
    visible, known_prize = visible_player_cards(players[1 - your_index], include_hand=False)
    ids = set(visible + known_prize)
    matches = [
        (len(ids & markers), -order, name)
        for order, (name, markers) in enumerate(PUBLIC_MATCHUP_MARKERS)
        if ids & markers
    ]
    return max(matches)[2] if matches else fallback


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels-dir", action="append", type=Path, default=[])
    parser.add_argument("--label-file", action="append", type=Path, default=[])
    parser.add_argument("--replay-dir", action="append", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--opponent-catalog", type=Path)
    parser.add_argument("--opponent-replay-catalog", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pool-mode", choices=["evaluated", "all"], default="evaluated")
    args = parser.parse_args()
    ensure_engine_on_path(args.engine_dir)
    examples = []
    episodes = set()
    target_deck = read_deck(args.baseline.resolve() / "deck.csv")
    deck_catalog = unique_decks(
        load_deck_catalog(args.opponent_catalog)
        + load_replay_deck_catalog(args.opponent_replay_catalog, target_deck)
    )
    replays = replay_index(args.replay_dir)
    paths = label_paths(args.labels_dir, args.label_file)
    if not paths:
        raise ValueError("no label files found")
    for label_path, report in label_reports(paths):
        if report.get("status") != "complete":
            continue
        episode_id = str(report["episode_id"])
        if episode_id in episodes:
            raise ValueError("duplicate episode label: " + episode_id)
        episodes.add(episode_id)
        replay_path = replays.get(episode_id)
        if replay_path is None:
            raise ValueError("missing replay file: " + episode_id)
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        seat = int(report["target_seat"])
        decisions = {
            int(row["step"]): row for row in report.get("decisions", [])
            if int(row.get("determinizations", 0)) > 0
        }
        agent = load_agent(args.baseline.resolve(), "rebuild_replay_%s" % episode_id)
        for replay_step, observation, recorded_action in replay_decisions(replay, seat):
            label = decisions.get(replay_step)
            if label is None:
                continue
            evaluated_indices = []
            if args.pool_mode == "evaluated":
                evaluated_actions = [
                    list(map(int, value.get("action", [])))
                    for value in label.get("evaluations", [])
                ]
                if not evaluated_actions or any(len(action) != 1 for action in evaluated_actions):
                    continue
                evaluated_indices = list(dict.fromkeys(action[0] for action in evaluated_actions))
            converted, scores, _reasons = score_options(agent, observation)
            with pushd(agent.agent_dir):
                example = make_observation_example(
                    converted, scores, recorded_action, label["selected"],
                    score_option=agent.module.score_option,
                    option_card=agent.module.option_card,
                    option_target=agent.module.option_target,
                    detect_matchup=agent.module.detect_matchup,
                    include_all_options=args.pool_mode == "all",
                    pool_indices=evaluated_indices if args.pool_mode == "evaluated" else None,
                    opponent=report.get("opponent"),
                    metadata={
                        "episode_id": episode_id,
                        "replay_step": replay_step,
                        "target_won": report.get("result") == seat,
                        "exact_hidden": bool(label.get("exact_hidden")),
                        "pool_mode": args.pool_mode,
                    },
                )
            belief = public_belief_features(converted, deck_catalog)
            matchup = public_matchup(converted, example.get("matchup") or "generic")
            example["matchup"] = matchup
            for option in example["options"]:
                option["features"].update(belief)
                option["features"]["public_matchup=" + matchup] = 1.0
            evaluations = {
                int(value["action"][0]): value
                for value in label.get("evaluations", [])
                if len(value.get("action", [])) == 1
            }
            baseline_evaluation = (
                evaluations.get(int(recorded_action[0]))
                if len(recorded_action) == 1 else None
            )
            baseline_values = list((baseline_evaluation or {}).get("values", []))
            for option in example["options"]:
                evaluation = evaluations.get(int(option["option_index"]))
                values = list((evaluation or {}).get("values", []))
                if not values or len(values) != len(baseline_values):
                    continue
                deltas = [float(value) - float(reference) for value, reference in zip(values, baseline_values)]
                mean = sum(deltas) / len(deltas)
                if len(deltas) > 1:
                    variance = sum((value - mean) ** 2 for value in deltas) / (len(deltas) - 1)
                    lower = mean - 1.64 * math.sqrt(max(0.0, variance) / len(deltas))
                else:
                    lower = mean
                option["rollout_delta_mean"] = mean
                option["rollout_delta_lower"] = lower
                option["rollout_samples"] = len(deltas)
            examples.append(example)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in examples),
        encoding="ascii",
    )
    print(json.dumps({
        "episodes": len(episodes), "examples": len(examples),
        "changes": sum(set(row["expert_action"]) != set(row["baseline_action"]) for row in examples),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
