from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = REPO_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from ptcg_common import DEFAULT_ENGINE_DIR, ensure_engine_on_path
from run_local_battle import run_game

ZOROARK_DIR = REPO_ROOT / "submission_zoroark"
LOG_DIR = REPO_ROOT / "logs"


BASELINES = {
    "archaludon_public": REPO_ROOT / "meta_agents" / "archaludon_public",
    "great_tusk_crustle_public": REPO_ROOT / "meta_agents" / "great_tusk_crustle_public",
    "zoroark_mirror": ZOROARK_DIR,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the N's Zoroark agent locally.")
    parser.add_argument("--n-games", type=int, default=10)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--opponent", action="append", choices=sorted(BASELINES), help="Repeat to choose opponents.")
    parser.add_argument("--summary", type=Path, default=LOG_DIR / "eval_summary.csv")
    parser.add_argument("--games-out", type=Path, default=LOG_DIR / "eval_games.csv")
    parser.add_argument("--trace-root", type=Path, default=LOG_DIR / "traces")
    parser.add_argument("--action-log", type=Path, default=LOG_DIR / "action_log.jsonl")
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_engine_on_path(args.engine_dir)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    action_log_path = args.action_log.resolve()
    action_log_dir = action_log_path.parent
    action_log_dir.mkdir(parents=True, exist_ok=True)
    agent_action_log = action_log_dir / "action_log.jsonl"
    agent_action_log.unlink(missing_ok=True)
    if action_log_path != agent_action_log:
        action_log_path.unlink(missing_ok=True)

    opponents = args.opponent or ["archaludon_public", "great_tusk_crustle_public", "zoroark_mirror"]
    game_rows = []
    summary_rows = []
    game_id = 0
    old_log_dir = os.environ.get("PTCG_AGENT_LOG_DIR")
    old_game_id = os.environ.get("PTCG_GAME_ID")
    os.environ["PTCG_AGENT_LOG_DIR"] = str(action_log_dir)
    try:
        for opponent_name in opponents:
            opponent_dir = BASELINES[opponent_name]
            wins = 0
            losses = 0
            unknown = 0
            errors = 0
            total_steps = 0
            total_turns = 0
            for local_index in range(args.n_games):
                os.environ["PTCG_GAME_ID"] = f"{opponent_name}-{local_index}"
                ns = SimpleNamespace(
                    engine_dir=args.engine_dir,
                    agent_a=ZOROARK_DIR,
                    agent_b=opponent_dir,
                    deck_a=None,
                    deck_b=None,
                    games=1,
                    max_steps=args.max_steps,
                    trace_dir=args.trace_root / opponent_name,
                    summary=None,
                )
                try:
                    result = run_game(ns, game_id)
                    winner = result.get("result")
                    if winner == 0:
                        wins += 1
                    elif winner == 1:
                        losses += 1
                    else:
                        unknown += 1
                    total_steps += int(result.get("steps") or 0)
                    total_turns += int(result.get("turn") or 0)
                    game_rows.append({"opponent": opponent_name, **result})
                except Exception as exc:
                    errors += 1
                    game_rows.append({"opponent": opponent_name, "game": game_id, "error": str(exc)})
                game_id += 1

            played = wins + losses + unknown
            summary_rows.append(
                {
                    "opponent": opponent_name,
                    "games": played,
                    "wins": wins,
                    "losses": losses,
                    "unknown": unknown,
                    "errors": errors,
                    "win_rate": round(wins / played, 4) if played else "",
                    "avg_steps": round(total_steps / played, 2) if played else "",
                    "avg_turn": round(total_turns / played, 2) if played else "",
                }
            )
    finally:
        if old_log_dir is None:
            os.environ.pop("PTCG_AGENT_LOG_DIR", None)
        else:
            os.environ["PTCG_AGENT_LOG_DIR"] = old_log_dir
        if old_game_id is None:
            os.environ.pop("PTCG_GAME_ID", None)
        else:
            os.environ["PTCG_GAME_ID"] = old_game_id

    args.summary.parent.mkdir(parents=True, exist_ok=True)
    with args.summary.open("w", newline="", encoding="utf-8") as f:
        fieldnames = ["opponent", "games", "wins", "losses", "unknown", "errors", "win_rate", "avg_steps", "avg_turn"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    all_keys = sorted({key for row in game_rows for key in row})
    with args.games_out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys)
        writer.writeheader()
        writer.writerows(game_rows)

    if action_log_path != agent_action_log and agent_action_log.exists():
        agent_action_log.replace(action_log_path)

    print(f"Wrote {args.summary}")
    print(f"Wrote {args.games_out}")
    print(f"Wrote {args.action_log}")


if __name__ == "__main__":
    main()
