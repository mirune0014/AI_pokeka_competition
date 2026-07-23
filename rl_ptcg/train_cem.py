"""Cross-entropy search over a small public-matchup residual policy."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import math
from pathlib import Path
import random
from types import SimpleNamespace


MATCHUPS = ("marnie", "alakazam", "archaludon", "lucario")
OPTION_TYPES = (7, 8, 9, 10, 12, 13, 14)
TURN_BUCKETS = ("4", "6", "10", "16", "24", "plus")


def parse_opponent(value):
    name, separator, directory = value.partition("=")
    if not separator or not name or not directory:
        raise argparse.ArgumentTypeError("opponent must be name=directory")
    return name, Path(directory)


def dimensions(matchups=MATCHUPS, feature_family="type", turn_buckets=TURN_BUCKETS):
    if feature_family == "turn_type":
        return [
            "public_matchup_turn_type=%s:%s:%d" % (matchup, turn_bucket, option_type)
            for matchup in matchups for turn_bucket in turn_buckets for option_type in OPTION_TYPES
        ]
    return [
        "public_matchup_type=%s:%d" % (matchup, option_type)
        for matchup in matchups for option_type in OPTION_TYPES
    ]


def vector_to_weights(names, vector):
    return {
        name: float(value) for name, value in zip(names, vector)
        if abs(float(value)) >= 1e-12
    }


def evaluate_worker(payload):
    from .train_reinforce import ensure_engine_on_path, play_game, scheduled_opponent_and_seat

    ensure_engine_on_path(Path(payload["engine_dir"]))
    opponents = [(name, Path(path)) for name, path in payload["opponents"]]
    args = SimpleNamespace(
        baseline=Path(payload["baseline"]), seed=int(payload["seed"]),
        max_steps=int(payload["max_steps"]), top_n=int(payload["top_n"]),
        evaluate=True, temperature=1.0, residual_cap=float(payload["residual_cap"]),
    )
    names = payload["dimensions"]
    weights = vector_to_weights(names, payload["vector"])
    rows = []
    for game_id in range(int(payload["games"])):
        (name, opponent), seat = scheduled_opponent_and_seat(opponents, game_id)
        reward, _gradient, info = play_game(args, weights, opponent, game_id, seat)
        rows.append({"opponent": name, "seat": seat, "reward": reward, **info})
    by_opponent = {}
    for name, _path in opponents:
        selected = [row for row in rows if row["opponent"] == name]
        by_opponent[name] = {
            "games": len(selected),
            "mean_reward": sum(row["reward"] for row in selected) / len(selected),
            "wins": sum(row.get("result") == row["seat"] for row in selected),
            "losses": sum(row.get("result") in (0, 1) and row.get("result") != row["seat"] for row in selected),
            "errors": sum(not row.get("started") for row in selected),
        }
    return {
        "candidate": int(payload["candidate"]),
        "mean_reward": sum(row["reward"] for row in rows) / len(rows),
        "wins": sum(row.get("result") == row["seat"] for row in rows),
        "losses": sum(row.get("result") in (0, 1) and row.get("result") != row["seat"] for row in rows),
        "errors": sum(not row.get("started") for row in rows),
        "by_opponent": by_opponent,
    }


def sample_vector(rng, mean, sigma, clamp):
    return [
        max(-clamp, min(clamp, rng.gauss(center, spread)))
        for center, spread in zip(mean, sigma)
    ]


def add_relative_scores(results, zero_candidate=1, worst_bucket_weight=0.25):
    """Annotate paired candidates with gains over the zero-weight policy."""
    zero = next(row for row in results if row["candidate"] == zero_candidate)
    zero_buckets = zero["by_opponent"]
    scored = []
    for source in results:
        row = dict(source)
        bucket_gains = {
            name: row["by_opponent"][name]["mean_reward"] - baseline["mean_reward"]
            for name, baseline in zero_buckets.items()
        }
        mean_gain = row["mean_reward"] - zero["mean_reward"]
        worst_bucket_gain = min(bucket_gains.values()) if bucket_gains else mean_gain
        row.update({
            "mean_gain": mean_gain,
            "worst_bucket_gain": worst_bucket_gain,
            "robust_gain": mean_gain + worst_bucket_weight * worst_bucket_gain,
            "bucket_gains": bucket_gains,
        })
        scored.append(row)
    return scored


def assert_duplicate_results(results, left_candidate=0, right_candidate=1):
    """Fail fast when identical control vectors see different game randomness."""
    rows = {row["candidate"]: row for row in results}
    left, right = rows[left_candidate], rows[right_candidate]
    fields = ("mean_reward", "wins", "losses", "errors", "by_opponent")
    if any(left[field] != right[field] for field in fields):
        raise RuntimeError(
            "Identical CEM control vectors produced different results. "
            "Use the seeded local engine; stock BattleStart uses random_device."
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--opponent", action="append", type=parse_opponent, required=True)
    parser.add_argument(
        "--matchup", action="append", choices=MATCHUPS,
        help="Restrict optimized dimensions to one or more public matchups.",
    )
    parser.add_argument(
        "--feature-family", choices=("type", "turn_type"), default="type",
        help="Optimize matchup option types globally or separately by turn bucket.",
    )
    parser.add_argument(
        "--turn-bucket", action="append", choices=TURN_BUCKETS,
        help="Restrict turn_type optimization to selected public turn buckets.",
    )
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--population", type=int, default=12)
    parser.add_argument("--elite", type=int, default=4)
    parser.add_argument("--games-per-candidate", type=int, default=32)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=2600000)
    parser.add_argument("--initial-sigma", type=float, default=0.2)
    parser.add_argument(
        "--initial-weights", type=Path,
        help="Optional sparse JSON used as the initial CEM distribution mean.",
    )
    parser.add_argument("--min-sigma", type=float, default=0.025)
    parser.add_argument("--clamp", type=float, default=0.6)
    parser.add_argument("--top-n", type=int, default=4)
    parser.add_argument("--residual-cap", type=float, default=0.35)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument(
        "--worst-bucket-weight", type=float, default=0.25,
        help="Penalty multiplier for the worst paired opponent-bucket gain.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.elite < 1 or args.elite > args.population:
        parser.error("elite must be within the population")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    names = dimensions(
        tuple(args.matchup or MATCHUPS), args.feature_family,
        tuple(args.turn_bucket or TURN_BUCKETS),
    )
    initial_weights = {}
    if args.initial_weights:
        initial_weights = json.loads(args.initial_weights.read_text(encoding="ascii"))
        if not isinstance(initial_weights, dict):
            parser.error("initial weights must be a JSON object")
    mean = [float(initial_weights.get(name, 0.0)) for name in names]
    sigma = [float(args.initial_sigma)] * len(names)
    rng = random.Random(args.seed)
    history = []
    best = None
    for iteration in range(args.iterations):
        vectors = [list(mean), [0.0] * len(names)]
        while len(vectors) < args.population:
            vectors.append(sample_vector(rng, mean, sigma, args.clamp))
        payloads = [{
            "candidate": index, "vector": vector, "dimensions": names,
            "engine_dir": str(args.engine_dir.resolve()),
            "baseline": str(args.baseline.resolve()),
            "opponents": [(name, str(path.resolve())) for name, path in args.opponent],
            "games": args.games_per_candidate,
            "seed": args.seed + iteration * 100000,
            "max_steps": args.max_steps, "top_n": args.top_n,
            "residual_cap": args.residual_cap,
        } for index, vector in enumerate(vectors)]
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            results = list(executor.map(evaluate_worker, payloads))
        if vectors[0] == vectors[1]:
            assert_duplicate_results(results)
        results = add_relative_scores(results, worst_bucket_weight=args.worst_bucket_weight)
        ranked = sorted(
            results,
            key=lambda row: (
                row["robust_gain"], row["mean_gain"], row["mean_reward"],
                row["wins"], -row["candidate"],
            ),
            reverse=True,
        )
        elites = ranked[:args.elite]
        elite_vectors = [vectors[row["candidate"]] for row in elites]
        mean = [sum(vector[index] for vector in elite_vectors) / len(elite_vectors) for index in range(len(names))]
        sigma = [
            max(args.min_sigma, math.sqrt(sum((vector[index] - mean[index]) ** 2 for vector in elite_vectors) / len(elite_vectors)))
            for index in range(len(names))
        ]
        iteration_best = ranked[0]
        candidate = {
            **iteration_best,
            "iteration": iteration + 1,
            "vector": vectors[iteration_best["candidate"]],
        }
        if best is None or (
            candidate["robust_gain"], candidate["mean_gain"], candidate["wins"]
        ) > (
            best["robust_gain"], best["mean_gain"], best["wins"]
        ):
            best = candidate
            (args.output_dir / "best_weights.json").write_text(
                json.dumps(vector_to_weights(names, best["vector"]), indent=2, sort_keys=True) + "\n",
                encoding="ascii",
            )
        record = {
            "iteration": iteration + 1,
            "best": candidate,
            "zero": results[1],
            "elite_candidates": [row["candidate"] for row in elites],
            "mean": mean,
            "sigma": sigma,
            "population": results,
        }
        history.append(record)
        (args.output_dir / "history.json").write_text(
            json.dumps(history, indent=2, sort_keys=True) + "\n", encoding="ascii"
        )
        (args.output_dir / ("mean_%04d.json" % (iteration + 1))).write_text(
            json.dumps(vector_to_weights(names, mean), indent=2, sort_keys=True) + "\n",
            encoding="ascii",
        )
        print(json.dumps({
            "iteration": iteration + 1,
            "best_reward": candidate["mean_reward"], "best_wins": candidate["wins"],
            "best_robust_gain": candidate["robust_gain"],
            "best_worst_bucket_gain": candidate["worst_bucket_gain"],
            "zero_reward": results[1]["mean_reward"], "zero_wins": results[1]["wins"],
            "mean_sigma": sum(sigma) / len(sigma),
        }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
