from __future__ import annotations

import argparse
import csv
from pathlib import Path
from types import SimpleNamespace

from ptcg_common import DEFAULT_ENGINE_DIR, ensure_engine_on_path
from run_local_battle import run_game


def parse_agent(value: str) -> tuple[str, Path]:
    if "=" in value:
        name, path = value.split("=", 1)
        return name, Path(path)
    path = Path(value)
    return path.name, path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a small local matchup matrix between imported agents.")
    parser.add_argument(
        "--agent",
        action="append",
        required=True,
        help="Agent spec. Use name=path or just path. Repeat for multiple agents.",
    )
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    parser.add_argument("--games", type=int, default=2, help="Games per ordered matchup.")
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--out", type=Path, default=Path("analysis_outputs/matchup_matrix.csv"))
    parser.add_argument("--trace-root", type=Path, default=Path("analysis_outputs/matchup_traces"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_engine_on_path(args.engine_dir)
    agents = [parse_agent(value) for value in args.agent]
    rows = []
    game_id = 0
    for name_a, path_a in agents:
        for name_b, path_b in agents:
            wins_a = 0
            wins_b = 0
            draws_or_unknown = 0
            errors = 0
            total_steps = 0
            for local_game in range(args.games):
                trace_dir = args.trace_root / f"{name_a}_vs_{name_b}"
                ns = SimpleNamespace(
                    engine_dir=args.engine_dir,
                    agent_a=path_a,
                    agent_b=path_b,
                    deck_a=None,
                    deck_b=None,
                    games=1,
                    max_steps=args.max_steps,
                    trace_dir=trace_dir,
                    summary=None,
                )
                try:
                    result = run_game(ns, game_id)
                except Exception as exc:
                    errors += 1
                    print(f"ERROR {name_a} vs {name_b} game {local_game}: {exc}")
                    game_id += 1
                    continue

                total_steps += int(result.get("steps") or 0)
                winner = result.get("result")
                if winner == 0:
                    wins_a += 1
                elif winner == 1:
                    wins_b += 1
                else:
                    draws_or_unknown += 1
                game_id += 1

            played = wins_a + wins_b + draws_or_unknown
            rows.append(
                {
                    "agent_a": name_a,
                    "agent_b": name_b,
                    "games": played,
                    "agent_a_wins": wins_a,
                    "agent_b_wins": wins_b,
                    "draws_or_unknown": draws_or_unknown,
                    "errors": errors,
                    "agent_a_win_rate": round(wins_a / played, 4) if played else "",
                    "avg_steps": round(total_steps / played, 2) if played else "",
                }
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "agent_a",
            "agent_b",
            "games",
            "agent_a_wins",
            "agent_b_wins",
            "draws_or_unknown",
            "errors",
            "agent_a_win_rate",
            "avg_steps",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
