"""Aggregate formal T7 branches by public target roles and context."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
import sys
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for path in (REPO_ROOT,):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _trace_observation(root: Mapping[str, Any]) -> dict[str, Any]:
    trace_path = Path(str(root["trace_path"]))
    target = int(root["callback_index"])
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if int(row.get("callback_index", -1)) == target:
            return row.get("observation") or {}
    raise ValueError(f"trace callback not found: {trace_path} {target}")


def _target(observation: Mapping[str, Any], action: list[int]) -> dict[str, Any]:
    options = (observation.get("select") or {}).get("option") or []
    if not action or not isinstance(action[0], int) or action[0] >= len(options):
        return {"area": None, "index": None, "card_id": None, "energy_count": 0, "role": "OTHER"}
    option = options[action[0]] if isinstance(options[action[0]], Mapping) else {}
    area = option.get("inPlayArea")
    index = option.get("inPlayIndex")
    player_index = option.get("inPlayPlayerIndex")
    current = observation.get("current") or {}
    seat = int(current.get("yourIndex", 0)) if current.get("yourIndex") in (0, 1) else 0
    players = current.get("players") or []
    owner = players[player_index if player_index in (0, 1) else seat] if len(players) == 2 else {}
    pokemon = None
    if area == 4:
        active = owner.get("active") or []
        pokemon = active[index or 0] if active and (index or 0) < len(active) else None
    elif area == 5:
        bench = owner.get("bench") or []
        pokemon = bench[index or 0] if index is not None and index < len(bench) else None
    card_id = pokemon.get("id") if isinstance(pokemon, Mapping) else None
    energy_count = len((pokemon or {}).get("energyCards") or (pokemon or {}).get("energies") or []) if isinstance(pokemon, Mapping) else 0
    role = "OTHER"
    attacks = []
    if isinstance(pokemon, Mapping):
        # Card-level attack lists are public metadata.  The engine exposes
        # exact attack costs; we load them below when available.
        attacks = pokemon.get("attacks") or []
    if area == 4:
        role = "CURRENT_ATTACKER" if any(option.get("type") == 14 for option in options if isinstance(option, Mapping)) else "OTHER"
    elif area == 5:
        name = str(pokemon.get("name", "")) if isinstance(pokemon, Mapping) else ""
        if "Cinderace" in name:
            role = "CINDERACE_PIVOT"
        elif energy_count > 0:
            role = "READY_SUCCESSOR"
        elif "Duraludon" in name or "Archaludon" in name:
            role = "UNREADY_DURALUDON" if "Duraludon" in name else "UNREADY_ARCHALUDON"
        else:
            role = "UNREADY"
    return {"area": area, "index": index, "player_index": player_index, "card_id": card_id, "energy_count": energy_count, "role": role}


def _classification(parent: Mapping[str, Any], alternative: Mapping[str, Any]) -> str:
    if parent.get("area") == 4 and alternative.get("area") == 5:
        return "T7A_ACTIVE_TO_BENCH"
    if parent.get("area") == 5 and alternative.get("area") == 4:
        return "T7B_BENCH_TO_ACTIVE"
    if parent.get("area") == 5 and alternative.get("area") == 5 and parent.get("index") != alternative.get("index"):
        return "T7C_BENCH_TO_OTHER_BENCH"
    if parent.get("area") == 4 and alternative.get("area") == 4 and parent.get("index") != alternative.get("index"):
        return "T7D_ACTIVE_TO_DIFFERENT_ACTIVE_ROLE"
    return "T7E_OTHER_ATTACH_CHANGE"


def aggregate(roots_path: Path, branch_path: Path, output: Path) -> dict[str, Any]:
    roots = {str(row["root_id"]): row for row in (json.loads(line) for line in roots_path.read_text(encoding="utf-8").splitlines() if line)}
    branch_rows = [json.loads(line) for line in branch_path.read_text(encoding="utf-8").splitlines() if line]
    parent_rows = {str(row.get("root_id")): row for row in branch_rows if row.get("branch") == "parent"}
    obs_cache: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for branch in branch_rows:
        if branch.get("branch") != "alternative":
            continue
        root = roots.get(str(branch.get("root_id")))
        parent = parent_rows.get(str(branch.get("root_id")))
        if not root or not parent:
            continue
        trace_key = str(root["trace_path"])
        if trace_key not in obs_cache:
            obs_cache[trace_key] = _trace_observation(root)
        observation = obs_cache[trace_key]
        parent_target = _target(observation, list(root.get("parent_action") or []))
        alt_expected = next((item for item in root.get("alternative_semantics") or [] if str(item.get("semantic_id")) == str(branch.get("alternative_semantic_id"))), {})
        alt_target = _target(observation, list(alt_expected.get("action") or []))
        rows.append({
            **branch,
            "t7_class": _classification(parent_target, alt_target),
            "parent_target": parent_target,
            "alternative_target": alt_target,
            "parent_role": parent_target.get("role"),
            "alternative_role": alt_target.get("role"),
            "turn_bucket": "early" if int(root.get("turn") or 0) <= 3 else "mid" if int(root.get("turn") or 0) <= 7 else "late",
            "prize_bucket": "opening" if "C_PRIZE_OPENING" in (root.get("context_tags") or []) else "middle" if "C_PRIZE_MIDDLE" in (root.get("context_tags") or []) else "closing",
        })
    def group(key_fields: tuple[str, ...]) -> list[dict[str, Any]]:
        grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[tuple(row.get(field) for field in key_fields)].append(row)
        output_rows = []
        for key, values in sorted(grouped.items(), key=lambda item: tuple(str(x) for x in item[0])):
            comparable = [row for row in values if row.get("status") == "complete" and row.get("root_match") and not row.get("action_errors") and not row.get("hit_max_steps")]
            output_rows.append({
                **{field: value for field, value in zip(key_fields, key)},
                "rows": len(values),
                "comparable": len(comparable),
                "gains": sum(_gain(row) for row in comparable),
                "regressions": sum(_regression(row) for row in comparable),
                "net": sum(_gain(row) for row in comparable) - sum(_regression(row) for row in comparable),
                "distinct_roots": len({str(row.get("root_id")) for row in comparable}),
            })
        return output_rows
    comparable = [row for row in rows if row.get("status") == "complete" and row.get("root_match") and not row.get("action_errors") and not row.get("hit_max_steps")]
    parent_result = {str(row.get("root_id")): row.get("terminal_result") for row in parent_rows.values()}
    for row in rows:
        seat = int(row.get("policy_seat"))
        p_result = parent_result.get(str(row.get("root_id")))
        a_result = row.get("terminal_result")
        row["parent_result"] = p_result
        row["parent_outcome"] = "win" if p_result == seat else "loss" if p_result in (0, 1) else "draw"
        row["alternative_outcome"] = "win" if a_result == seat else "loss" if a_result in (0, 1) else "draw"
    # Recompute comparable after outcome fields are attached.
    comparable = [row for row in rows if row.get("status") == "complete" and row.get("root_match") and not row.get("action_errors") and not row.get("hit_max_steps")]
    report = {
        "schema_version": "archaludon_formal_t7_aggregate.v1",
        "source_kind": "FORMAL_REALIZED_SEEDED_WORLD",
        "roots": len(roots),
        "alternative_rows": len(rows),
        "comparable_rows": len(comparable),
        "gains": sum(_gain(row) for row in comparable),
        "regressions": sum(_regression(row) for row in comparable),
        "net": sum(_gain(row) for row in comparable) - sum(_regression(row) for row in comparable),
        "distinct_gain_roots": len({str(row.get("root_id")) for row in comparable if _gain(row)}),
        "distinct_regression_roots": len({str(row.get("root_id")) for row in comparable if _regression(row)}),
        "opponent_families": sorted({str(row.get("opponent_family")) for row in comparable}),
        "seats": sorted({int(row.get("policy_seat")) for row in comparable}),
        "by_t7_class": group(("t7_class",)),
        "by_target_role": group(("parent_role", "alternative_role")),
        "by_opponent": group(("opponent_family",)),
        "by_seat": group(("policy_seat",)),
        "by_turn_prize": group(("turn_bucket", "prize_bucket")),
        "adoption_status": "DISCOVERY_GATE_REJECTED_OR_HOLD_UNTIL_ROOT_LEVEL_REVIEW",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "classified_rows.jsonl").write_text("".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows), encoding="utf-8", newline="\n")
    (output / "REPORT.json").write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report


def _gain(row: Mapping[str, Any]) -> bool:
    return row.get("parent_outcome") in {"loss", "draw"} and row.get("alternative_outcome") == "win"


def _regression(row: Mapping[str, Any]) -> bool:
    return row.get("parent_outcome") == "win" and row.get("alternative_outcome") in {"loss", "draw"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", type=Path, required=True)
    parser.add_argument("--branches", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = aggregate(args.roots.resolve(), args.branches.resolve(), args.output.resolve())
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
