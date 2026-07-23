"""Verify that a zero-weight residual build matches baseline actions exactly."""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from ptcg_common import ensure_engine_on_path, load_agent, read_deck


def play(args, game_id):
    from cg.game import battle_finish, battle_select, battle_start

    seat = game_id % 2
    baseline_dir = args.baseline.resolve()
    residual_dir = args.residual.resolve()
    opponent_dir = args.opponent.resolve()
    trainee_deck = read_deck(baseline_dir / "deck.csv")
    opponent_deck = read_deck(opponent_dir / "deck.csv")
    decks = [trainee_deck, opponent_deck] if seat == 0 else [opponent_deck, trainee_deck]
    baseline = load_agent(baseline_dir, "zero_baseline_%d" % game_id)
    residual = load_agent(residual_dir, "zero_residual_%d" % game_id)
    opponent = load_agent(opponent_dir, "zero_opponent_%d" % game_id)
    seed = args.seed + game_id
    random.seed(seed)
    for agent in (baseline, residual, opponent):
        module_random = getattr(getattr(agent, "module", None), "random", None)
        if hasattr(module_random, "seed"):
            module_random.seed(seed)

    obs, start = battle_start(*decks)
    if not obs:
        return {"game": game_id, "started": False, "error": str(getattr(start, "errorType", "start"))}

    checked = 0
    mismatch = None
    final_obs = obs
    try:
        for step in range(args.max_steps):
            current = obs.get("current") or {}
            select = obs.get("select") or {}
            if current.get("result") not in (None, -1) or not select.get("option"):
                break
            player = int(current.get("yourIndex", 0))
            if player == seat:
                expected = baseline(obs)
                actual = residual(obs)
                checked += 1
                if expected != actual:
                    mismatch = {
                        "step": step,
                        "context": select.get("context"),
                        "expected": expected,
                        "actual": actual,
                    }
                    break
                action = expected
            else:
                action = opponent(obs)
            obs = battle_select(action)
            final_obs = obs
    finally:
        battle_finish()

    return {
        "game": game_id,
        "started": True,
        "seat": seat,
        "checked": checked,
        "mismatch": mismatch,
        "result": (final_obs or {}).get("current", {}).get("result"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--residual", type=Path, required=True)
    parser.add_argument("--opponent", type=Path, required=True)
    parser.add_argument("--games", type=int, default=4)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=1000)
    args = parser.parse_args()
    ensure_engine_on_path(args.engine_dir)
    rows = [play(args, game_id) for game_id in range(args.games)]
    print(json.dumps(rows, indent=2))
    mismatches = [row for row in rows if not row.get("started") or row.get("mismatch")]
    if mismatches:
        raise SystemExit(1)
    print("PASS: %d actions matched across %d games" %
          (sum(row["checked"] for row in rows), len(rows)))


if __name__ == "__main__":
    main()
