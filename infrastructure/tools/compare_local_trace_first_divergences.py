#!/usr/bin/env python3
"""Report the first action divergence for matching deterministic local traces."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


KNOWN_STADIUMS = {1244, 1261}


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def selected_score(row: dict) -> dict:
    return next((score for score in row.get("scores", []) if score.get("selected")), {})


def stadium_before(rows: list[dict], index: int) -> int | None:
    stadium = None
    for row in rows[: index + 1]:
        for log in row.get("logs", []):
            if log.get("type") == 10 and log.get("cardId") in KNOWN_STADIUMS:
                stadium = int(log["cardId"])
    return stadium


def first_divergence(baseline: list[dict], candidate: list[dict]) -> dict | None:
    for index, (before, after) in enumerate(zip(baseline, candidate)):
        identity_before = (before.get("step"), before.get("player"), before.get("context"))
        identity_after = (after.get("step"), after.get("player"), after.get("context"))
        if identity_before != identity_after:
            return {"row": index, "kind": "state_alignment", "before": before, "after": after}
        if before.get("action") != after.get("action"):
            return {"row": index, "kind": "action", "before": before, "after": after}
    if len(baseline) != len(candidate):
        return {
            "row": min(len(baseline), len(candidate)),
            "kind": "length",
            "before": baseline[-1] if baseline else {},
            "after": candidate[-1] if candidate else {},
        }
    return None


def summarize_pair(baseline_path: Path, candidate_path: Path, seat: int) -> dict:
    baseline = read_rows(baseline_path)
    candidate = read_rows(candidate_path)
    difference = first_divergence(baseline, candidate)
    if difference is None:
        return {
            "seat": seat,
            "game": baseline_path.stem,
            "diverged": False,
            "kind": "",
            "row": "",
            "step": "",
            "player": "",
            "stadium_id": "",
            "target_id": "",
            "target_hp": "",
            "baseline_action": "",
            "candidate_action": "",
            "baseline_reason": "",
            "candidate_reason": "",
            "baseline_option": "",
            "candidate_option": "",
        }

    index = difference["row"]
    before = difference["before"]
    after = difference["after"]
    snapshot = before.get("snapshot", {})
    player = before.get("player")
    target_prefix = f"p{1 - int(player)}" if player in {0, 1} else ""
    before_score = selected_score(before)
    after_score = selected_score(after)
    return {
        "seat": seat,
        "game": baseline_path.stem,
        "diverged": True,
        "kind": difference["kind"],
        "row": index,
        "step": before.get("step"),
        "player": player,
        "stadium_id": stadium_before(baseline, index),
        "target_id": snapshot.get(f"{target_prefix}_active") if target_prefix else None,
        "target_hp": snapshot.get(f"{target_prefix}_active_hp") if target_prefix else None,
        "baseline_action": json.dumps(before.get("action"), separators=(",", ":")),
        "candidate_action": json.dumps(after.get("action"), separators=(",", ":")),
        "baseline_reason": before_score.get("reason", ""),
        "candidate_reason": after_score.get("reason", ""),
        "baseline_option": json.dumps(before_score.get("option", {}), sort_keys=True, separators=(",", ":")),
        "candidate_option": json.dumps(after_score.get("option", {}), sort_keys=True, separators=(",", ":")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", nargs=3, action="append", metavar=("BASELINE_DIR", "CANDIDATE_DIR", "SEAT"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows = []
    for baseline_text, candidate_text, seat_text in args.pair:
        baseline_dir = Path(baseline_text)
        candidate_dir = Path(candidate_text)
        seat = int(seat_text)
        for baseline_path in sorted(baseline_dir.glob("game_*.jsonl")):
            candidate_path = candidate_dir / baseline_path.name
            if not candidate_path.exists():
                raise FileNotFoundError(candidate_path)
            rows.append(summarize_pair(baseline_path, candidate_path, seat))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(json.dumps({
        "games": len(rows),
        "diverged": sum(bool(row["diverged"]) for row in rows),
        "output": str(args.out),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
