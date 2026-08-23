"""Select a deterministic, family/seat-balanced formal T7 discovery set."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def select(rows: list[dict[str, Any]], count: int, per_group: int | None) -> list[dict[str, Any]]:
    candidates = [
        row for row in rows
        if row.get("split") == "discovery" and row.get("alternative_semantics")
    ]
    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    seen_games: set[tuple[str, int, int]] = set()
    for row in sorted(candidates, key=lambda item: (str(item.get("opponent_family")), int(item.get("policy_seat", -1)), int(item.get("seed", 0)), int(item.get("callback_index", 0)))):
        key = (str(row.get("opponent_family")), int(row.get("policy_seat")))
        # Prefer at most one root per family/seat/game to make coverage game-
        # distinct; a later root in the same game is still available if a
        # group cannot fill its quota.
        game_key = (key[0], key[1], int(row.get("seed", 0)))
        if game_key in seen_games:
            continue
        groups[key].append(row)
        seen_games.add(game_key)
    selected: list[dict[str, Any]] = []
    group_keys = sorted(groups)
    cursors = {key: 0 for key in group_keys}
    while len(selected) < count and group_keys:
        progressed = False
        for key in group_keys:
            rows_for_group = groups[key]
            if cursors[key] >= len(rows_for_group):
                continue
            if per_group is not None and sum(1 for row in selected if (str(row.get("opponent_family")), int(row.get("policy_seat", -1))) == key) >= per_group:
                continue
            selected.append(dict(rows_for_group[cursors[key]]))
            cursors[key] += 1
            progressed = True
            if len(selected) >= count:
                break
        if not progressed:
            break
    for index, row in enumerate(selected):
        row["selected_index"] = index
        row["formal_root_id"] = f"t7_discovery_{index:04d}_{row.get('opponent_family')}_p{row.get('policy_seat')}_g{row.get('game')}_c{row.get('callback_index')}"
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=64)
    parser.add_argument("--per-group", type=int, default=4)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.roots.read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = select(rows, args.count, args.per_group)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in selected), encoding="utf-8", newline="\n")
    report = {
        "schema_version": "archaludon_formal_t7_selection.v1",
        "requested_count": args.count,
        "selected_count": len(selected),
        "distinct_games": len({(str(row.get("opponent_family")), int(row.get("seed", 0))) for row in selected}),
        "opponent_families": sorted({str(row.get("opponent_family")) for row in selected}),
        "seats": sorted({int(row.get("policy_seat")) for row in selected}),
        "per_group": args.per_group,
        "source_kind": "FORMAL_REALIZED_SEEDED_WORLD",
    }
    report_path = args.output.with_name("SELECTION_REPORT.json")
    report_path.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
