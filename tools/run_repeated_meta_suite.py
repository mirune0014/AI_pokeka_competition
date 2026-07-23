from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

from ptcg_common import DEFAULT_ENGINE_DIR, ensure_engine_on_path, write_csv
from run_meta_suite import (
    META_OPPONENTS,
    build_summary,
    check_agent_dir,
    parse_agent,
    run_ordered_matchup,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the meta suite over repeated independent batches. "
            "This is meant for the native engine, whose shuffles are not fully controlled "
            "by Python's random seed."
        )
    )
    parser.add_argument(
        "--candidate",
        action="append",
        required=True,
        help="Candidate spec. Use name=path or just path. Repeat for multiple candidates.",
    )
    parser.add_argument(
        "--opponent",
        action="append",
        choices=sorted(META_OPPONENTS),
        help="Limit to specific public-meta bucket(s). Defaults to all buckets.",
    )
    parser.add_argument("--engine-dir", type=Path, default=DEFAULT_ENGINE_DIR)
    parser.add_argument("--games", type=int, default=40, help="Games per seat, matchup, and repeat.")
    parser.add_argument("--repeats", type=int, default=3, help="Independent batches to run.")
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--seed-base", type=int, help="Python-side seed base; native shuffles may still vary.")
    parser.add_argument("--trace-root", type=Path, default=Path("analysis_outputs/repeated_meta_traces"))
    parser.add_argument("--no-traces", action="store_true", help="Do not write per-game JSONL traces.")
    parser.add_argument("--out", type=Path, default=Path("analysis_outputs/repeated_meta_results.csv"))
    parser.add_argument("--summary-out", type=Path, default=Path("analysis_outputs/repeated_meta_summary.csv"))
    parser.add_argument("--diff-out", type=Path, default=Path("analysis_outputs/repeated_meta_diff.csv"))
    parser.add_argument("--game-out", type=Path, help="Optional per-game result CSV.")
    return parser.parse_args()


def _write_rows(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _summary_lookup(rows: list[dict[str, object]]) -> dict[tuple[str, str], dict[str, object]]:
    return {(str(row["candidate"]), str(row["scenario"])): row for row in rows}


def _rate(row: dict[str, object]) -> tuple[float | None, int | None, int | None]:
    raw_rate = row.get("win_rate", "")
    try:
        rate = float(raw_rate)
    except (TypeError, ValueError):
        return None, None, None
    raw_wins = row.get("wins", "")
    raw_games = row.get("games", "")
    try:
        wins = int(raw_wins)
        games = int(raw_games)
    except (TypeError, ValueError):
        wins = None
        try:
            games = int(raw_games)
        except (TypeError, ValueError):
            games = None
    return rate, wins, games


def build_diff_rows(summary_rows: list[dict[str, object]], candidate_names: list[str]) -> list[dict[str, object]]:
    if len(candidate_names) < 2:
        return []
    baseline = candidate_names[0]
    lookup = _summary_lookup(summary_rows)
    scenarios = sorted({str(row["scenario"]) for row in summary_rows})
    rows: list[dict[str, object]] = []
    for candidate in candidate_names[1:]:
        for scenario in scenarios:
            base_row = lookup.get((baseline, scenario))
            cand_row = lookup.get((candidate, scenario))
            if not base_row or not cand_row:
                continue
            base_rate, base_wins, base_games = _rate(base_row)
            cand_rate, cand_wins, cand_games = _rate(cand_row)
            if base_rate is None or cand_rate is None:
                continue
            diff = cand_rate - base_rate
            z = ""
            if None not in (base_wins, base_games, cand_wins, cand_games) and base_games and cand_games:
                pooled = (base_wins + cand_wins) / (base_games + cand_games)
                se = math.sqrt(max(1e-12, pooled * (1 - pooled) * (1 / base_games + 1 / cand_games)))
                z = round(diff / se, 3)
            rows.append(
                {
                    "baseline": baseline,
                    "candidate": candidate,
                    "scenario": scenario,
                    "baseline_rate": base_rate,
                    "candidate_rate": cand_rate,
                    "diff": round(diff, 4),
                    "baseline_wins": "" if base_wins is None else base_wins,
                    "candidate_wins": "" if cand_wins is None else cand_wins,
                    "baseline_games": "" if base_games is None else base_games,
                    "candidate_games": "" if cand_games is None else cand_games,
                    "approx_z": z,
                }
            )
    return rows


def main() -> None:
    args = parse_args()
    ensure_engine_on_path(args.engine_dir)

    candidates = [parse_agent(value) for value in args.candidate]
    candidate_names = [name for name, _ in candidates]
    duplicate_names = sorted({name for name in candidate_names if candidate_names.count(name) > 1})
    if duplicate_names:
        raise ValueError(f"Duplicate candidate name(s): {', '.join(duplicate_names)}")
    bucket_name_collisions = sorted(set(candidate_names) & set(META_OPPONENTS))
    if bucket_name_collisions:
        raise ValueError(
            "Candidate names must not match public-meta bucket names: "
            + ", ".join(bucket_name_collisions)
            + ". Use an alias such as cand_marnie=path."
        )

    opponents = {
        name: path
        for name, path in META_OPPONENTS.items()
        if not args.opponent or name in set(args.opponent)
    }
    for _, path in [*candidates, *opponents.items()]:
        check_agent_dir(path)

    rows: list[dict[str, object]] = []
    game_rows: list[dict[str, object]] = []
    game_id = 0
    for repeat in range(args.repeats):
        candidate_order = candidates if repeat % 2 == 0 else list(reversed(candidates))
        for candidate_name, candidate_path in candidate_order:
            for bucket_name, bucket_path in opponents.items():
                trace_root = None if args.no_traces else args.trace_root / f"repeat_{repeat:03d}"
                row, next_game_id, matchup_game_rows = run_ordered_matchup(
                    engine_dir=args.engine_dir,
                    name_a=candidate_name,
                    path_a=candidate_path,
                    name_b=bucket_name,
                    path_b=bucket_path,
                    games=args.games,
                    max_steps=args.max_steps,
                    trace_root=trace_root,
                    game_id_start=game_id,
                    seed_base=args.seed_base,
                )
                row["repeat"] = repeat
                rows.append(row)
                for game_row in matchup_game_rows:
                    game_row["repeat"] = repeat
                game_rows.extend(matchup_game_rows)
                game_id = next_game_id

                row, next_game_id, matchup_game_rows = run_ordered_matchup(
                    engine_dir=args.engine_dir,
                    name_a=bucket_name,
                    path_a=bucket_path,
                    name_b=candidate_name,
                    path_b=candidate_path,
                    games=args.games,
                    max_steps=args.max_steps,
                    trace_root=trace_root,
                    game_id_start=game_id,
                    seed_base=args.seed_base,
                )
                row["repeat"] = repeat
                rows.append(row)
                for game_row in matchup_game_rows:
                    game_row["repeat"] = repeat
                game_rows.extend(matchup_game_rows)
                game_id = next_game_id

    _write_rows(
        args.out,
        rows,
        [
            "repeat",
            "agent_a",
            "agent_b",
            "games",
            "agent_a_wins",
            "agent_b_wins",
            "draws_or_unknown",
            "errors",
            "agent_a_win_rate",
            "avg_steps",
        ],
    )

    aggregate_rows = [
        {key: value for key, value in row.items() if key != "repeat"}
        for row in rows
    ]
    summary_rows = build_summary(aggregate_rows, candidate_names)
    write_csv(args.summary_out, summary_rows, ["candidate", "scenario", "wins", "games", "win_rate", "errors"])

    diff_rows = build_diff_rows(summary_rows, candidate_names)
    write_csv(
        args.diff_out,
        diff_rows,
        [
            "baseline",
            "candidate",
            "scenario",
            "baseline_rate",
            "candidate_rate",
            "diff",
            "baseline_wins",
            "candidate_wins",
            "baseline_games",
            "candidate_games",
            "approx_z",
        ],
    )

    if args.game_out:
        write_csv(
            args.game_out,
            game_rows,
            [
                "repeat",
                "agent_a",
                "agent_b",
                "local_game",
                "game_id",
                "seed",
                "result",
                "winner",
                "error",
                "steps",
                "turn",
                "trace",
                "p0_prizes",
                "p1_prizes",
                "p0_active",
                "p1_active",
            ],
        )

    print(f"Wrote {args.out}")
    print(f"Wrote {args.summary_out}")
    print(f"Wrote {args.diff_out}")
    if args.game_out:
        print(f"Wrote {args.game_out}")


if __name__ == "__main__":
    main()
