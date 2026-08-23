"""Decompose diagnostic T13 rows without promoting a rule hypothesis.

The V2.1 world bank is synthetic and therefore remains diagnostic only.  This
script reports the public action/context pattern behind its T13 gains so that
GPT PRO can decide whether a formal realized-world search is worthwhile.  It
never edits an agent and never treats synthetic gains as adoption evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
V1_DIR = HERE.parent / "counterfactual_macro_search_v1"
for path in (REPO_ROOT, V1_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from common import read_json, read_jsonl, write_json  # noqa: E402
from common_v2 import action_family  # noqa: E402
from research.rl_ptcg.replay_reconstruction import iter_replay_decisions  # noqa: E402


def _option_descriptor(observation: Mapping[str, Any], action: list[int]) -> dict[str, Any]:
    options = (observation.get("select") or {}).get("option") or []
    selected = [options[index] for index in action if isinstance(index, int) and 0 <= index < len(options)]
    if not selected:
        return {"category": "end", "card_or_attack_id": None, "option_types": []}
    types = []
    ids = []
    for option in selected:
        if not isinstance(option, Mapping):
            continue
        types.append(option.get("type"))
        for key in ("attackId", "cardId", "effectCardId", "contextCardId"):
            if option.get(key) is not None:
                ids.append(option.get(key))
    return {
        "category": action_family(observation, action),
        "card_or_attack_id": ids[0] if ids else None,
        "option_types": types,
        "raw_options": selected,
    }


def _active_id(player: Mapping[str, Any]) -> int | None:
    active = player.get("active") or []
    if active and isinstance(active[0], Mapping):
        return active[0].get("id")
    return None


def _context(observation: Mapping[str, Any]) -> dict[str, Any]:
    current = observation.get("current") or {}
    players = current.get("players") or []
    seat = current.get("yourIndex")
    if not isinstance(seat, int) or seat not in (0, 1) or len(players) != 2:
        return {"valid": False}
    mine = players[seat] or {}
    opp = players[1 - seat] or {}
    options = (observation.get("select") or {}).get("option") or []
    option_types = {option.get("type") for option in options if isinstance(option, Mapping)}
    bench = [card for card in (mine.get("bench") or []) if card]
    ready_successor = any(
        isinstance(card, Mapping)
        and bool(card.get("energies"))
        and int(card.get("hp") or 0) == int(card.get("maxHp") or 0)
        for card in bench
    )
    return {
        "valid": True,
        "own_active_id": _active_id(mine),
        "opponent_active_id": _active_id(opp),
        "current_attack_legal": 14 in option_types,
        "current_ko_available": any(
            isinstance(option, Mapping)
            and bool(option.get("ko") or option.get("isKo") or option.get("knockout"))
            for option in options
            if option.get("type") == 14 if isinstance(option, Mapping)
        ),
        "own_bench_count": len(bench),
        "ready_successor": ready_successor,
        "remaining_prize_bucket": (
            "opening" if len(mine.get("prize") or []) >= 5
            else "middle" if len(mine.get("prize") or []) >= 3
            else "closing"
        ),
        "turn_bucket": "early" if int(current.get("turn") or 0) <= 3 else "mid" if int(current.get("turn") or 0) <= 7 else "late",
        "supporterPlayed": bool(current.get("supporterPlayed")),
        "energyAttached": bool(current.get("energyAttached")),
        "retreated": bool(current.get("retreated")),
    }


def _decision_cache(path: Path) -> dict[tuple[int, int], Any]:
    replay = read_json(path)
    return {(int(row.replay_step), int(row.acting_seat)): row for row in iter_replay_decisions(replay)}


def decompose(branch_path: Path, manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    roots = {str(row["root_id"]): row for row in read_jsonl(manifest_path)}
    branches = read_jsonl(branch_path)
    summary_path = branch_path.parent / "root_summary.json"
    summary_value = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else []
    summaries = summary_value.get("rows", []) if isinstance(summary_value, dict) else summary_value
    summary_index = {
        (str(summary.get("root_id")), str(summary.get("world_id")), str(alt.get("semantic_id"))): bool(alt.get("gain"))
        for summary in summaries
        for alt in summary.get("alternative_rows") or []
    }
    rows: list[dict[str, Any]] = []
    cache: dict[str, dict[tuple[int, int], Any]] = {}
    for branch in branches:
        if branch.get("branch") != "alternative" or branch.get("status") != "complete":
            continue
        root = roots.get(str(branch.get("root_id")))
        if not root:
            continue
        # The world summary marks a comparable alternative as gain.  Join by
        # semantic ID and world ID, keeping only the six diagnostic gains.
        world_id = str(branch["world_id"])
        gain = summary_index.get((str(root.get("root_id")), world_id, str(branch.get("selected_semantic_id"))), False)
        if not gain:
            continue
        replay_path = Path(root["root_source_replay"])
        cache_key = str(replay_path)
        if cache_key not in cache:
            cache[cache_key] = _decision_cache(replay_path)
        decision = cache[cache_key].get((int(root["replay_step"]), int(root["acting_seat"])))
        if decision is None:
            continue
        observation = decision.observation
        parent_action = list(root.get("parent_action") or [])
        alternative_action = list(branch.get("selected_action") or [])
        rows.append({
            "root_id": root["root_id"],
            "world_id": world_id,
            "episode_id": root.get("episode_id"),
            "replay_step": root.get("replay_step"),
            "acting_seat": root.get("acting_seat"),
            "opponent_family": root.get("opponent_family"),
            "parent_action": parent_action,
            "alternative_action": alternative_action,
            "parent": _option_descriptor(observation, parent_action),
            "alternative": _option_descriptor(observation, alternative_action),
            "action_transformation": next(
                (item.get("action_transformation") for item in root.get("alternatives", []) if item.get("semantic_id") == branch.get("selected_semantic_id")),
                "T13_OTHER",
            ),
            "context": _context(observation),
        })

    pair_counts = Counter(
        (
            row["parent"]["category"],
            row["alternative"]["category"],
            row["parent"].get("card_or_attack_id"),
            row["alternative"].get("card_or_attack_id"),
        )
        for row in rows
    )
    pair_root_counts: Counter[tuple[Any, ...]] = Counter(
        (
            row["parent"]["category"],
            row["alternative"]["category"],
            row["parent"].get("card_or_attack_id"),
            row["alternative"].get("card_or_attack_id"),
            row["root_id"],
        )
        for row in rows
    )
    distinct_roots_by_pair: Counter[tuple[Any, ...]] = Counter()
    for key in pair_root_counts:
        distinct_roots_by_pair[key[:-1]] += 1
    root_ids = sorted({row["root_id"] for row in rows})
    games = sorted({str(row.get("episode_id")) for row in rows})
    families = sorted({str(row.get("opponent_family")) for row in rows if row.get("opponent_family")})
    seats = sorted({int(row["acting_seat"]) for row in rows if row.get("acting_seat") in (0, 1)})
    pattern_status = "CONCRETE_T13_PATTERN_FOUND" if any(count >= 3 for count in distinct_roots_by_pair.values()) else "T13_MIXED_NO_HYPOTHESIS"
    report = {
        "schema_version": "archaludon_t13_diagnostic_decomposition.v1",
        "source_kind": "DIAGNOSTIC_SYNTHETIC_WORLD",
        "source_branch_results": str(branch_path.resolve()),
        "source_root_manifest": str(manifest_path.resolve()),
        "gain_rows": len(rows),
        "distinct_roots": len(root_ids),
        "distinct_games": len(games),
        "opponent_families": families,
        "seats": seats,
        "semantic_pair_counts": [
            {"parent_category": key[0], "alternative_category": key[1], "parent_id": key[2], "alternative_id": key[3], "count": count, "distinct_roots": distinct_roots_by_pair[key]}
            for key, count in sorted(pair_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "pattern_status": pattern_status,
        "adoption_status": "HOLD_DIAGNOSTIC_ONLY",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "gain_rows.jsonl").write_text("".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows), encoding="utf-8", newline="\n")
    write_json(output_dir / "REPORT.json", report)
    with (output_dir / "gain_rows.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = ["root_id", "world_id", "episode_id", "replay_step", "acting_seat", "action_transformation", "parent", "alternative", "context"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: json.dumps(row[field], ensure_ascii=True, sort_keys=True) if isinstance(row[field], (dict, list)) else row[field] for field in fields})
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch-results", type=Path, required=True)
    parser.add_argument("--root-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = decompose(args.branch_results.resolve(), args.root_manifest.resolve(), args.output.resolve())
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
