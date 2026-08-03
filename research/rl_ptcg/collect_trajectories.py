"""Collect public behavior-cloning and terminal-value trajectories locally.

The native ``cg`` engine is process-global.  Workers therefore never share a
battle process, and each worker writes only its own JSONL shard.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
import multiprocessing as mp
from pathlib import Path
import random
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "infrastructure" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ptcg_common import ensure_engine_on_path, load_agent, pushd, read_deck

try:
    from .encoding import SCHEMA
    from .trajectory import TrajectoryRecord, make_record, write_jsonl
except ImportError:
    from research.rl_ptcg.encoding import SCHEMA
    from research.rl_ptcg.trajectory import TrajectoryRecord, make_record, write_jsonl


def parse_opponent(value: str) -> tuple[str, Path]:
    """Parse a public label and the local directory of an opponent."""
    name, separator, directory = value.partition("=")
    if not separator or not name or not directory:
        raise argparse.ArgumentTypeError("opponent must be name=directory")
    return name, Path(directory)


def build_episode_specs(
    opponents: Iterable[tuple[str, Path]], games_per_opponent: int, seed: int
) -> list[dict[str, Any]]:
    """Create a stable, seat-balanced episode schedule.

    Each opponent's games alternate trainee seats independently, so an odd
    count differs by at most one game for that opponent.
    """
    specs: list[dict[str, Any]] = []
    for name, directory in opponents:
        for game_number in range(games_per_opponent):
            episode_number = len(specs)
            specs.append({
                "episode_id": "episode-%06d" % episode_number,
                "episode_number": episode_number,
                "opponent": str(name),
                "opponent_dir": str(Path(directory).resolve()),
                "trainee_seat": game_number % 2,
                "seed": int(seed) + episode_number,
            })
    return specs


def partition_episode_specs(specs: list[dict[str, Any]], workers: int) -> list[list[dict[str, Any]]]:
    """Assign deterministic episode specs to one shard per worker."""
    if workers < 1:
        raise ValueError("workers must be positive")
    return [list(specs[index::workers]) for index in range(workers)]


def terminal_reward(result: Any, trainee_seat: int) -> tuple[int, float]:
    """Return the winner result and unshaped value target for a completed game."""
    winner = int(result) if result in (0, 1) else -1
    reward = 1.0 if winner == trainee_seat else -1.0 if winner in (0, 1) else 0.0
    return winner, reward


def label_terminal_records(
    records: Iterable[TrajectoryRecord], result: Any, trainee_seat: int
) -> list[TrajectoryRecord]:
    """Attach one terminal value and equal episode mass to every public state."""
    values = list(records)
    if not values:
        return values
    winner, reward = terminal_reward(result, trainee_seat)
    value_weight = 1.0 / len(values)
    return [replace(record, terminal=index == len(values) - 1, result=winner,
                    reward=reward, value_weight=value_weight)
            for index, record in enumerate(values)]


def _error(stage: str, exc: BaseException) -> dict[str, str]:
    return {"stage": stage, "type": type(exc).__name__, "message": str(exc).encode("ascii", "backslashreplace").decode("ascii")}


def _seed_module(agent: Any, seed: int) -> None:
    module_random = getattr(getattr(agent, "module", None), "random", None)
    if hasattr(module_random, "seed"):
        module_random.seed(seed)


def _rule_scores(agent: Any, observation: dict[str, Any]) -> list[float]:
    """Score the converted legal options in exactly the raw option order."""
    module = getattr(agent, "module", None)
    agent_dir = getattr(agent, "agent_dir", None)
    convert = getattr(module, "to_observation_class", None)
    score_option = getattr(module, "score_option", None)
    if not callable(convert) or not callable(score_option) or agent_dir is None:
        raise AttributeError("baseline module requires to_observation_class and score_option")
    raw_options = (observation.get("select") or {}).get("option") or []
    converted = convert(observation)
    options = list(getattr(getattr(converted, "select", None), "option", []) or [])
    if len(options) != len(raw_options):
        raise ValueError("converted option count does not match raw public observation")
    scores: list[float] = []
    with pushd(agent_dir):
        for option in options:
            value = score_option(converted, option)
            score = value[0] if isinstance(value, tuple) else value
            score = float(score)
            if score != score or score in (float("inf"), -float("inf")):
                raise ValueError("score_option returned a non-finite score")
            scores.append(score)
    return scores


def collect_episode(spec: dict[str, Any], baseline_dir: str, max_steps: int) -> tuple[list[TrajectoryRecord], dict[str, Any]]:
    """Run one episode and encode trainee decisions plus public opponent-turn states."""
    from cg.game import battle_finish, battle_select, battle_start

    episode_id = str(spec["episode_id"])
    seed = int(spec["seed"])
    trainee_seat = int(spec["trainee_seat"])
    opponent_dir = Path(str(spec["opponent_dir"])).resolve()
    trainee_dir = Path(baseline_dir).resolve()
    try:
        random.seed(seed)
        trainee = load_agent(trainee_dir, "collector_trainee_%s" % episode_id.replace("-", "_"))
        opponent = load_agent(opponent_dir, "collector_opponent_%s" % episode_id.replace("-", "_"))
        _seed_module(trainee, seed)
        _seed_module(opponent, seed)
        trainee_deck = read_deck(trainee_dir / "deck.csv")
        opponent_deck = read_deck(opponent_dir / "deck.csv")
        decks = [trainee_deck, opponent_deck] if trainee_seat == 0 else [opponent_deck, trainee_deck]
        observation, start_data = battle_start(decks[0], decks[1])
    except Exception as exc:
        return [], {"episode_id": episode_id, "status": "error", "error": _error("start", exc)}
    if not observation:
        return [], {"episode_id": episode_id, "status": "error", "error": {
            "stage": "start", "type": str(getattr(start_data, "errorType", "StartError")),
            "message": "engine rejected battle start",
        }}

    records: list[TrajectoryRecord] = []
    final_observation = observation
    status = "truncated"
    error: dict[str, str] | None = None
    try:
        for step in range(max_steps):
            current = observation.get("current") or {}
            select = observation.get("select") or {}
            if current.get("result") not in (None, -1):
                status = "complete"
                break
            if not select.get("option"):
                status = "stopped"
                break
            player = int(current.get("yourIndex", 0))
            try:
                if player == trainee_seat:
                    # This call is intentionally first: baseline tracking globals update here.
                    action = trainee(observation)
                    scores = _rule_scores(trainee, observation)
                    records.append(make_record(
                        observation, episode_id, len(records), scores, action, action,
                        matchup=str(spec["opponent"]), opponent=str(spec["opponent"]),
                        opponent_deck=opponent_deck, seed=seed,
                    ))
                else:
                    action = opponent(observation)
                    records.append(make_record(
                        observation, episode_id, len(records), (), None, None,
                        matchup=str(spec["opponent"]), opponent=str(spec["opponent"]),
                        opponent_deck=opponent_deck, seed=seed,
                        perspective_seat=trainee_seat, policy_target=False,
                    ))
                observation = battle_select(action)
                final_observation = observation
            except Exception as exc:
                error = _error("action", exc)
                status = "error"
                records = []  # Never publish a partial episode after an action failure.
                break
        else:
            status = "truncated"
    finally:
        battle_finish()

    result = ((final_observation or {}).get("current") or {}).get("result")
    if result not in (None, -1) and status == "truncated":
        status = "complete"
    if status == "complete":
        records = label_terminal_records(records, result, trainee_seat)
    summary: dict[str, Any] = {
        "episode_id": episode_id, "opponent": str(spec["opponent"]), "seed": seed,
        "trainee_seat": trainee_seat, "status": status, "records": len(records), "result": result,
    }
    if error is not None:
        summary["error"] = error
    return records, summary


def _worker(worker_id: int, specs: list[dict[str, Any]], config: dict[str, Any], queue: Any) -> None:
    ensure_engine_on_path(Path(config["engine_dir"]))
    shard_records: list[TrajectoryRecord] = []
    summaries: list[dict[str, Any]] = []
    for spec in specs:
        try:
            records, summary = collect_episode(spec, config["baseline"], int(config["max_steps"]))
        except Exception as exc:
            records, summary = [], {"episode_id": spec["episode_id"], "status": "error", "records": 0,
                                    "error": _error("worker", exc)}
        shard_records.extend(records)
        summaries.append(summary)
    shard_name = "shard-%03d.jsonl" % worker_id
    write_jsonl(Path(config["output_dir"]) / shard_name, shard_records)
    queue.put({"worker": worker_id, "shard": shard_name, "episodes": summaries, "records": len(shard_records)})


def build_manifest(config: dict[str, Any], worker_results: list[dict[str, Any]], episode_count: int) -> dict[str, Any]:
    """Combine worker reports into a deterministic, public metadata manifest."""
    results = sorted(worker_results, key=lambda item: item["worker"])
    episodes = sorted(
        (episode for result in results for episode in result["episodes"]),
        key=lambda episode: str(episode.get("episode_id", "")),
    )
    counts: dict[str, int] = {}
    for episode in episodes:
        status = str(episode["status"])
        counts[status] = counts.get(status, 0) + 1
    return {
        "format": "ptcg-public-trajectory-v2-deck-hypothesis",
        "engine_dir": str(config["engine_dir"]), "baseline": str(config["baseline"]),
        "opponents": list(config["opponents"]), "seed": int(config["seed"]),
        "max_steps": int(config["max_steps"]), "workers": int(config["workers"]),
        "episode_count": episode_count, "record_count": sum(result["records"] for result in results),
        "status_counts": counts, "shards": [{"worker": result["worker"], "path": result["shard"], "records": result["records"]} for result in results],
        "episodes": episodes,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--opponent", action="append", type=parse_opponent)
    parser.add_argument("--opponent-json", type=Path,
                        help="JSON object mapping opponent names to local directories.")
    parser.add_argument("--games-per-opponent", type=int, required=True)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    opponents = list(args.opponent or [])
    if args.opponent_json:
        payload = json.loads(args.opponent_json.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise SystemExit("opponent-json must contain a name-to-directory object")
        opponents.extend((str(name), Path(path)) for name, path in payload.items())
    if not opponents:
        raise SystemExit("at least one --opponent or --opponent-json entry is required")
    if args.games_per_opponent < 1 or args.workers < 1 or args.max_steps < 1:
        raise SystemExit("games-per-opponent, workers, and max-steps must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    specs = build_episode_specs(opponents, args.games_per_opponent, args.seed)
    partitions = partition_episode_specs(specs, args.workers)
    config = {"engine_dir": str(args.engine_dir.resolve()), "baseline": str(args.baseline.resolve()),
              "opponents": [name for name, _ in opponents], "seed": args.seed, "max_steps": args.max_steps,
              "workers": args.workers, "output_dir": str(args.output_dir.resolve())}
    (args.output_dir / "schema.json").write_text(json.dumps(SCHEMA.to_dict(), sort_keys=True, indent=2) + "\n", encoding="ascii")
    context = mp.get_context("spawn")
    queue = context.Queue()
    processes = [context.Process(target=_worker, args=(worker_id, partition, config, queue))
                 for worker_id, partition in enumerate(partitions)]
    for process in processes:
        process.start()
    results = [queue.get() for _ in processes]
    for process in processes:
        process.join()
        if process.exitcode != 0:
            raise RuntimeError("worker %s exited with code %s" % (process.pid, process.exitcode))
    manifest = build_manifest(config, results, len(specs))
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="ascii")
    print(json.dumps({"episodes": len(specs), "records": manifest["record_count"], "status_counts": manifest["status_counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
