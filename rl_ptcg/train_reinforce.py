"""Local sparse REINFORCE training against one or more baseline opponents."""
from __future__ import annotations

import argparse
import importlib
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
from ptcg_common import ensure_engine_on_path, load_agent, pushd, read_deck

try:
    from .residual_policy import choose_residual
except ImportError:
    from residual_policy import choose_residual


def parse_opponent(value):
    name, separator, directory = value.partition("=")
    if not separator or not name or not directory:
        raise argparse.ArgumentTypeError("opponent must be name=directory")
    return name, Path(directory)


def terminal_reward(final_obs, trainee_seat):
    current = (final_obs or {}).get("current") or {}
    result = current.get("result")
    reward = 1.0 if result == trainee_seat else -1.0 if result in (0, 1) else 0.0
    players = current.get("players") or []
    if len(players) >= 2:
        def prizes(player):
            return len((player or {}).get("prize") or [])
        differential = prizes(players[1 - trainee_seat]) - prizes(players[trainee_seat])
        reward += max(-0.2, min(0.2, differential * 0.03))
    return reward


def apply_update(weights, gradient, scale, learning_rate, l2, clamp):
    for key in list(weights):
        weights[key] *= max(0.0, 1.0 - learning_rate * l2)
    for key, value in gradient.items():
        weights[key] = max(-clamp, min(clamp, weights.get(key, 0.0) + learning_rate * scale * value))
        if abs(weights[key]) < 1e-12:
            weights.pop(key, None)


def load_weights(path):
    if path is None:
        return {}
    payload = json.loads(Path(path).read_text(encoding="ascii"))
    if not isinstance(payload, dict):
        raise ValueError("weights JSON must be an object")
    result = {}
    for key, value in payload.items():
        number = float(value)
        if not (-float("inf") < number < float("inf")):
            raise ValueError("weight must be finite: " + str(key))
        result[str(key)] = number
    return result


def select_gradient_features(gradient, scope):
    if scope == "all":
        return gradient
    prefixes = ("matchup_", "public_matchup_")
    return {key: value for key, value in gradient.items() if key.startswith(prefixes)}


def scheduled_opponent_and_seat(opponents, game_id):
    """Pair both trainee seats for each opponent before moving to the next."""
    if not opponents:
        raise ValueError("at least one opponent is required")
    return opponents[(int(game_id) // 2) % len(opponents)], int(game_id) % 2


def play_game(args, weights, opponent_dir, game_id, trainee_seat):
    from cg.game import battle_finish, battle_select, battle_start
    trainee_dir = args.baseline.resolve()
    opponent_dir = opponent_dir.resolve()
    deck0 = read_deck((trainee_dir if trainee_seat == 0 else opponent_dir) / "deck.csv")
    deck1 = read_deck((opponent_dir if trainee_seat == 0 else trainee_dir) / "deck.csv")
    trainee = load_agent(trainee_dir, "residual_trainee_%d" % game_id)
    opponent = load_agent(opponent_dir, "residual_opponent_%d" % game_id)
    agents = [trainee, opponent] if trainee_seat == 0 else [opponent, trainee]
    rng = random.Random(args.seed + game_id)
    for agent in agents:
        module_rng = getattr(getattr(agent, "module", None), "random", None)
        if hasattr(module_rng, "seed"):
            module_rng.seed(args.seed + game_id)
    obs, start = battle_start(deck0, deck1, seed=args.seed + game_id)
    if not obs:
        return 0.0, {}, {"started": False, "error": str(getattr(start, "errorType", "start"))}
    total_gradient = defaultdict(float)
    decisions = 0
    final_obs = obs
    try:
        for _ in range(args.max_steps):
            current, select = obs.get("current") or {}, obs.get("select") or {}
            if current.get("result") not in (None, -1) or not select.get("option"):
                break
            player = int(current.get("yourIndex", 0))
            if player == trainee_seat:
                module = trainee.module
                # Use the real agent entry point so stateful observation
                # bookkeeping matches the packaged Kaggle runtime.
                rule_selected = trainee(obs)
                with pushd(trainee_dir):
                    converted = module.to_observation_class(obs)
                    action, gradient = choose_residual(
                        converted, module.score_option, module.option_card, module.option_target,
                        module.detect_matchup, rule_selected, weights, rng, args.top_n,
                        training=not args.evaluate, temperature=args.temperature,
                        residual_cap=args.residual_cap)
                for key, value in gradient.items():
                    total_gradient[key] += value
                decisions += 1
            else:
                action = agents[player](obs)
            obs = battle_select(action)
            final_obs = obs
    finally:
        battle_finish()
    return terminal_reward(final_obs, trainee_seat), total_gradient, {
        "started": True, "decisions": decisions, "result": (final_obs or {}).get("current", {}).get("result")
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--opponent", action="append", type=parse_opponent, required=True)
    parser.add_argument("--epochs", type=int, required=True)
    parser.add_argument("--games-per-epoch", type=int, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--top-n", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    parser.add_argument("--entropy-coef", type=float, default=0.0)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--l2", type=float, default=1e-4)
    parser.add_argument("--clamp", type=float, default=3.0)
    parser.add_argument("--residual-cap", type=float, default=0.35,
                        help="Maximum learned logit correction per option.")
    parser.add_argument("--weights", type=Path,
                        help="Optional weights JSON to evaluate or resume training from.")
    parser.add_argument("--feature-scope", choices=("matchup", "all"), default="matchup",
                        help="Limit updates to matchup-conditioned features by default.")
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--evaluate", action="store_true", help="Use deterministic residual argmax and do not update weights.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.epochs < 1 or args.games_per_epoch < 1 or args.top_n < 1:
        parser.error("epochs, games-per-epoch, and top-n must be positive")
    ensure_engine_on_path(args.engine_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    weights, history, baselines = load_weights(args.weights), [], defaultdict(float)
    game_id = 0
    for epoch in range(args.epochs):
        rows = []
        for game in range(args.games_per_epoch):
            (name, opponent), trainee_seat = scheduled_opponent_and_seat(args.opponent, game_id)
            reward, gradient, info = play_game(args, weights, opponent, game_id, trainee_seat)
            game_id += 1
            advantage = reward - baselines[name]
            baselines[name] = 0.9 * baselines[name] + 0.1 * reward
            # Entropy coefficient dampens confident updates; temperature remains
            # the explicit exploration control used by sampling.
            scale = advantage / max(1, info.get("decisions", 0))
            scale -= args.entropy_coef * max(-1.0, min(1.0, scale))
            if not args.evaluate:
                gradient = select_gradient_features(gradient, args.feature_scope)
                apply_update(weights, gradient, scale, args.learning_rate, args.l2, args.clamp)
            rows.append({"opponent": name, "seat": trainee_seat, "reward": reward, **info})
        record = {"epoch": epoch + 1, "mean_reward": sum(r["reward"] for r in rows) / len(rows),
                  "games": rows, "weights": len(weights), "baselines": dict(baselines)}
        history.append(record)
        (args.output_dir / "weights.json").write_text(json.dumps(weights, sort_keys=True, indent=2), encoding="ascii")
        (args.output_dir / "history.json").write_text(json.dumps(history, indent=2), encoding="ascii")
        (args.output_dir / ("checkpoint_%04d.json" % (epoch + 1))).write_text(json.dumps(weights, sort_keys=True), encoding="ascii")
        print(json.dumps(record, sort_keys=True))


if __name__ == "__main__":
    main()
