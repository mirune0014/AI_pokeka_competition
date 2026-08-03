from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def split_semicolon(value: str) -> list[str]:
    return [part for part in (value or "").split(";") if part]


def norm_trace(value: str) -> str:
    return value.replace("/", "\\")


def is_candidate_loss(row: dict[str, str], candidate: str) -> bool:
    if row.get("error"):
        return False
    if candidate not in {row.get("agent_a"), row.get("agent_b")}:
        return False
    return row.get("winner") != candidate


def candidate_side(row: dict[str, str], candidate: str) -> str:
    if row.get("agent_a") == candidate:
        return "p0"
    if row.get("agent_b") == candidate:
        return "p1"
    raise ValueError(f"{candidate!r} is not in row {row}")


def opponent_name(row: dict[str, str], candidate: str) -> str:
    return row["agent_b"] if row.get("agent_a") == candidate else row["agent_a"]


def summarize_losses(games: list[dict[str, str]], traces: dict[str, dict[str, str]], candidate: str) -> list[dict[str, object]]:
    counters: dict[str, Counter[str]] = defaultdict(Counter)
    example_by_key: dict[tuple[str, str], str] = {}
    total_losses = 0

    for game in games:
        if not is_candidate_loss(game, candidate):
            continue
        total_losses += 1
        side = candidate_side(game, candidate)
        opp_side = "p1" if side == "p0" else "p0"
        opponent = opponent_name(game, candidate)
        trace = norm_trace(game.get("trace", ""))
        summary = traces.get(trace, {})

        active = summary.get(f"{side}_active", "") or game.get(f"{side}_active", "")
        bench = split_semicolon(summary.get(f"{side}_bench", ""))
        opp_active = summary.get(f"{opp_side}_active", "") or game.get(f"{opp_side}_active", "")
        opp_bench = split_semicolon(summary.get(f"{opp_side}_bench", ""))

        facts = {
            "opponent": opponent,
            "turn_bucket": f"turn_{int(game.get('turn') or 0) // 5 * 5:02d}",
            "candidate_no_active": str(not active),
            "candidate_empty_bench": str(len(bench) == 0),
            "candidate_active": active or "<none>",
            "opponent_active": opp_active or "<none>",
            "opponent_bench_has_relicanth": str(any("Relicanth" in x for x in opp_bench)),
            "opponent_bench_has_alakazam": str(any("Alakazam" in x or "Kadabra" in x or "Abra" in x for x in opp_bench)),
        }

        board_to_trash = summary.get("board_to_trash", "")
        top_attacks = summary.get("top_attacks", "")
        if "Relicanth" in board_to_trash:
            facts["candidate_relicanth_lost"] = "True"
        if "Archaludon ex" in board_to_trash:
            facts["candidate_arch_ex_lost"] = "True"
        if "Powerful Hand" in top_attacks:
            facts["opponent_powerful_hand"] = "True"
        if "Raging Hammer" in top_attacks:
            facts["raging_hammer_seen"] = "True"

        for key, value in facts.items():
            counters[key][value] += 1
            example_by_key.setdefault((key, value), trace)

    rows: list[dict[str, object]] = []
    for category, counter in sorted(counters.items()):
        for value, count in counter.most_common():
            rows.append(
                {
                    "candidate": candidate,
                    "losses": total_losses,
                    "category": category,
                    "value": value,
                    "count": count,
                    "share": round(count / total_losses, 4) if total_losses else "",
                    "example_trace": example_by_key.get((category, value), ""),
                }
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize candidate loss patterns from local meta-suite outputs.")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--games", type=Path, required=True)
    parser.add_argument("--trace-summary", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    games = read_csv(args.games)
    trace_rows = read_csv(args.trace_summary)
    traces = {norm_trace(row["trace"]): row for row in trace_rows if row.get("trace")}
    rows = summarize_losses(games, traces, args.candidate)

    fieldnames = ["candidate", "losses", "category", "value", "count", "share", "example_trace"]
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {args.out}")

    writer = csv.DictWriter(__import__("sys").stdout, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)


if __name__ == "__main__":
    main()
