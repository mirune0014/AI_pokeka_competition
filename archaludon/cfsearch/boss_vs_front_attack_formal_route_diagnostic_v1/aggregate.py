"""Independently recompute T3/T4 route pairs and frozen gates from raw rows."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(value, sort_keys=True, ensure_ascii=True) + "\n" for value in values), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=True, sort_keys=True) if isinstance(value, (dict, list)) else value for key, value in row.items()})


def _bool_or_none(value: Any) -> bool | None:
    if value is True or value is False:
        return value
    return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def route_class(boss: dict[str, Any], front: dict[str, Any]) -> str:
    boss_win_turn = boss.get("terminal_win_same_turn") is True
    front_win_turn = front.get("terminal_win_same_turn") is True
    if boss_win_turn and not front_win_turn:
        return "R1_BOSS_TERMINAL_WIN"
    if front_win_turn and not boss_win_turn:
        return "R2_FRONT_TERMINAL_WIN"
    bko = _bool_or_none(boss.get("actual_ko"))
    fko = _bool_or_none(front.get("actual_ko"))
    bp = _int_or_none(boss.get("target_prize_value"))
    fp = _int_or_none(front.get("target_prize_value"))
    boss_attacked = boss.get("route_attack_id") is not None
    if bko is None or fko is None or bp is None or fp is None:
        return "R9_DAMAGE_OR_ROUTE_UNKNOWN"
    if bko and bp > fp:
        return "R3_BOSS_HIGHER_PRIZE_KO"
    if fko and not boss_attacked:
        return "R4_FRONT_KO_BOSS_NO_ATTACK"
    if fko and boss_attacked and not bko:
        return "R5_FRONT_KO_BOSS_NON_KO"
    if bko and not fko:
        return "R6_BOSS_KO_FRONT_NON_KO"
    if bko and fko and bp == fp:
        return "R7_BOTH_KO_SAME_PRIZE"
    if not bko and not fko:
        return "R8_BOTH_NON_KO"
    return "R9_DAMAGE_OR_ROUTE_UNKNOWN"


def orientation(route: str) -> str:
    if route in {"R1_BOSS_TERMINAL_WIN", "R3_BOSS_HIGHER_PRIZE_KO", "R6_BOSS_KO_FRONT_NON_KO"}:
        return "BOSS"
    if route in {"R2_FRONT_TERMINAL_WIN", "R4_FRONT_KO_BOSS_NO_ATTACK", "R5_FRONT_KO_BOSS_NON_KO"}:
        return "FRONT"
    return "NEUTRAL" if route == "R7_BOTH_KO_SAME_PRIZE" or route == "R8_BOTH_NON_KO" else "UNKNOWN"


def pair_outcome(boss: dict[str, Any], front: dict[str, Any], seat: int) -> tuple[str, int]:
    bw = _int_or_none(boss.get("terminal_result")) == seat
    fw = _int_or_none(front.get("terminal_result")) == seat
    if bw and not fw:
        return "BOSS_GAIN", 1
    if fw and not bw:
        return "FRONT_GAIN", -1
    return "TIE", 0


def game_key(row: dict[str, Any]) -> str:
    return "|".join(str(row.get(key)) for key in ("opponent_policy_id", "game", "seed"))


def bootstrap_by_schedule(game_rows: list[dict[str, Any]], schedule_field: str = "schedule_key") -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in game_rows:
        groups[str(row.get(schedule_field))].append(row)
    keys = sorted(groups)
    if not keys:
        return {"replicates": 0, "schedule_key_count": 0, "mean_delta_p05": None, "mean_delta_median": None, "mean_delta_p95": None, "unit": "schedule_key"}
    values: list[float] = []
    rng = random.Random(20260816)
    for _ in range(2000):
        sampled = [rng.choice(keys) for _ in keys]
        selected = [row for key in sampled for row in groups[key]]
        values.append(sum(float(row.get("game_delta") or 0.0) for row in selected) / max(1, len(selected)))
    values.sort()
    percentile = lambda q: values[min(len(values) - 1, max(0, int(q * (len(values) - 1))))]
    return {"replicates": len(values), "schedule_key_count": len(keys), "mean_delta_p05": percentile(0.05), "mean_delta_median": percentile(0.50), "mean_delta_p95": percentile(0.95), "unit": "schedule_key", "schedule_keys": keys}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run = args.run_dir.resolve()
    roots = read_jsonl(run / "selected_roots.jsonl")
    branch_rows = read_jsonl(run / "branch_results.jsonl")
    by_root: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in branch_rows:
        branch = str(row.get("branch"))
        key = str(row.get("root_id"))
        by_root[key][branch] = row
    pair_rows: list[dict[str, Any]] = []
    root_rows: list[dict[str, Any]] = []
    for root in roots:
        rid = str(root["root_id"])
        branches = by_root.get(rid, {})
        boss = branches.get("boss")
        parent = branches.get("parent")
        if boss is None:
            continue
        front_rows = [row for branch, row in branches.items() if branch.startswith("front_")]
        for front in sorted(front_rows, key=lambda row: str(row.get("branch"))):
            route = route_class(boss, front)
            orientation_value = orientation(route)
            outcome, delta = pair_outcome(boss, front, int(root["policy_seat"]))
            boss_damage_known = boss.get("damage_known") is True
            front_damage_known = front.get("damage_known") is True
            superior_prize = boss.get("target_prize_value") if orientation_value == "BOSS" else front.get("target_prize_value") if orientation_value == "FRONT" else None
            catastrophic = bool(
                (orientation_value == "BOSS" and outcome == "FRONT_GAIN" and boss.get("prizes_taken_same_turn") not in (None, 0))
                or (orientation_value == "FRONT" and outcome == "BOSS_GAIN" and front.get("prizes_taken_same_turn") not in (None, 0))
            )
            pair_rows.append({
                "root_id": rid,
                "game_key": game_key(root),
                "opponent_family": root.get("opponent_family"),
                "opponent_policy_id": root.get("opponent_policy_id"),
                "policy_seat": root.get("policy_seat"),
                "game": root.get("game"),
                "seed": root.get("seed"),
                "schedule_key": root.get("schedule_key"),
                "turn": root.get("turn"),
                "parent_action_category": root.get("parent_action_category"),
                "front_attack_id": front.get("forced_attack_id"),
                "boss_terminal_result": boss.get("terminal_result"),
                "front_terminal_result": front.get("terminal_result"),
                "boss_win": _int_or_none(boss.get("terminal_result")) == int(root["policy_seat"]),
                "front_win": _int_or_none(front.get("terminal_result")) == int(root["policy_seat"]),
                "route_class": route,
                "orientation": orientation_value,
                "pair_outcome": outcome,
                "pair_delta": delta,
                "boss_actual_ko": boss.get("actual_ko"),
                "front_actual_ko": front.get("actual_ko"),
                "boss_prize_value": boss.get("target_prize_value"),
                "front_prize_value": front.get("target_prize_value"),
                "boss_attacked_same_turn": boss.get("route_attack_id") is not None,
                "front_attacked_same_turn": front.get("route_attack_id") is not None,
                "boss_terminal_win_same_turn": boss.get("terminal_win_same_turn"),
                "front_terminal_win_same_turn": front.get("terminal_win_same_turn"),
                "boss_damage_known": boss_damage_known,
                "front_damage_known": front_damage_known,
                "damage_known_pair": boss_damage_known and front_damage_known,
                "boss_high_prize_target": None if boss.get("target_prize_value") is None else int(boss["target_prize_value"]) >= 2,
                "front_high_prize_target": None if front.get("target_prize_value") is None else int(front["target_prize_value"]) >= 2,
                "superior_prize_value": superior_prize,
                "catastrophic_regression": catastrophic,
                "boss_damage_unknown_reason": boss.get("damage_unknown_reason"),
                "front_damage_unknown_reason": front.get("damage_unknown_reason"),
            })
        root_rows.append({
            "root_id": rid,
            "opponent_family": root.get("opponent_family"),
            "opponent_policy_id": root.get("opponent_policy_id"),
            "policy_seat": root.get("policy_seat"),
            "game": root.get("game"),
            "seed": root.get("seed"),
            "turn": root.get("turn"),
            "parent_action_category": root.get("parent_action_category"),
            "front_attack_count": len(front_rows),
            "boss_status": boss.get("status"),
            "parent_status": parent.get("status") if parent else None,
            "root_match_all": all(branch.get("root_match") is True for branch in [boss, *(front_rows), *([parent] if parent else [])]),
            "engine_import_all": all(branch.get("engine_import_ok") is True for branch in [boss, *(front_rows), *([parent] if parent else [])]),
        })
    write_csv(run / "route_pairs.csv", pair_rows)
    write_csv(run / "root_results.csv", root_rows)
    games: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pair_rows:
        games[game_key(row)].append(row)
    game_rows: list[dict[str, Any]] = []
    for key, rows_for_game in sorted(games.items()):
        delta = sum(int(row["pair_delta"]) for row in rows_for_game) / max(1, len(rows_for_game))
        game_rows.append({
            "game_key": key,
            "schedule_key": rows_for_game[0].get("schedule_key"),
            "opponent_family": rows_for_game[0].get("opponent_family"),
            "policy_seat": rows_for_game[0].get("policy_seat"),
            "pair_count": len(rows_for_game),
            "game_delta": delta,
            "game_class": "GAME_GAIN" if delta >= 0.25 else "GAME_REGRESSION" if delta <= -0.25 else "TIE",
            "boss_gains": sum(row["pair_outcome"] == "BOSS_GAIN" for row in rows_for_game),
            "front_gains": sum(row["pair_outcome"] == "FRONT_GAIN" for row in rows_for_game),
            "ties": sum(row["pair_outcome"] == "TIE" for row in rows_for_game),
        })
    write_csv(run / "game_results.csv", game_rows)
    route_names = ["R1_BOSS_TERMINAL_WIN", "R2_FRONT_TERMINAL_WIN", "R3_BOSS_HIGHER_PRIZE_KO", "R4_FRONT_KO_BOSS_NO_ATTACK", "R5_FRONT_KO_BOSS_NON_KO", "R6_BOSS_KO_FRONT_NON_KO", "R7_BOTH_KO_SAME_PRIZE", "R8_BOTH_NON_KO", "R9_DAMAGE_OR_ROUTE_UNKNOWN"]
    family_rows: list[dict[str, Any]] = []
    family_gate: dict[str, Any] = {}
    for route in route_names:
        selected = [row for row in pair_rows if row["route_class"] == route]
        games_for = {row["game_key"] for row in selected}
        families = {str(row.get("opponent_family")) for row in selected}
        seats = {int(row["policy_seat"]) for row in selected}
        selected_games = [row for row in game_rows if row["game_key"] in games_for]
        orient = orientation(route)
        boss_gain = sum(row["pair_outcome"] == "BOSS_GAIN" for row in selected)
        front_gain = sum(row["pair_outcome"] == "FRONT_GAIN" for row in selected)
        net = boss_gain - front_gain
        game_gain_boss = sum(row["game_class"] == "GAME_GAIN" for row in selected_games)
        game_reg_boss = sum(row["game_class"] == "GAME_REGRESSION" for row in selected_games)
        if orient == "FRONT":
            game_gain = game_reg_boss
            game_reg = game_gain_boss
            oriented_net = -net
        elif orient == "BOSS":
            game_gain = game_gain_boss
            game_reg = game_reg_boss
            oriented_net = net
        else:
            game_gain = game_gain_boss; game_reg = game_reg_boss; oriented_net = 0
        unknown = sum(not row["damage_known_pair"] for row in selected)
        catastrophic = sum(bool(row["catastrophic_regression"]) for row in selected)
        evidence = bool(len(games_for) >= 8 and len(families) >= 3 and len(seats) == 2 and game_gain >= 5 and game_reg <= 2 and oriented_net >= 3 and catastrophic == 0 and unknown == 0)
        exploratory = bool(len(games_for) >= 5 and game_gain > game_reg and oriented_net >= 2 and catastrophic <= 1)
        family_gate[route] = {"evidence_candidate": evidence, "exploratory_candidate": exploratory, "orientation": orient}
        family_rows.append({
            "route_class": route,
            "orientation": orient,
            "pair_count": len(selected),
            "distinct_games": len(games_for),
            "families": len(families),
            "family_names": sorted(families),
            "seats": sorted(seats),
            "boss_gains": boss_gain,
            "front_gains": front_gain,
            "net_boss_delta": net,
            "oriented_net": oriented_net,
            "game_gain": game_gain,
            "game_regression": game_reg,
            "unknown_count": unknown,
            "catastrophic_count": catastrophic,
            "evidence_candidate": evidence,
            "exploratory_candidate": exploratory,
        })
    write_csv(run / "family_summary.csv", family_rows)
    catastrophic_rows = [row for row in pair_rows if row["catastrophic_regression"]]
    write_csv(run / "catastrophic_regressions.csv", catastrophic_rows)
    bootstrap = {route: bootstrap_by_schedule([game for game in game_rows if any(pair["route_class"] == route and pair["game_key"] == game["game_key"] for pair in pair_rows)]) for route in route_names}
    write_json(run / "bootstrap.json", {"schema_version": "archaludon_boss_vs_front_attack_bootstrap.v1", "unit": "schedule_key", "families": bootstrap})
    selection = json.loads((run.parent / "selection_20260816_1046_v1" / "selection_summary.json").read_text(encoding="utf-8")) if (run.parent / "selection_20260816_1046_v1" / "selection_summary.json").exists() else {}
    summary = {
        "schema_version": "archaludon_boss_vs_front_attack_formal_route_summary.v1",
        "diagnostic": "T3_T4_BOSS_VS_FRONT_ATTACK_FORMAL_ROUTE_DIAGNOSTIC_V1",
        "root_count": len(roots),
        "branch_count": len(branch_rows),
        "route_pair_count": len(pair_rows),
        "distinct_games": len(games),
        "families": sorted({str(row.get("opponent_family")) for row in pair_rows}),
        "seats": sorted({int(row["policy_seat"]) for row in pair_rows}),
        "route_counts": dict(sorted(Counter(str(row["route_class"]) for row in pair_rows).items())),
        "boss_gain_pairs": sum(row["pair_outcome"] == "BOSS_GAIN" for row in pair_rows),
        "front_gain_pairs": sum(row["pair_outcome"] == "FRONT_GAIN" for row in pair_rows),
        "tie_pairs": sum(row["pair_outcome"] == "TIE" for row in pair_rows),
        "catastrophic_count": len(catastrophic_rows),
        "engine_complete": sum(row.get("status") == "complete" for row in branch_rows) == len(branch_rows),
        "engine_import_all": all(row.get("engine_import_ok") is True for row in branch_rows),
        "root_match_all": all(row.get("root_match") is True for row in branch_rows),
        "action_errors": sum(int(row.get("action_errors") or 0) for row in branch_rows),
        "max_step": sum(bool(row.get("hit_max_steps")) for row in branch_rows),
        "holdout_opened": False,
        "reserve_opened": False,
        "candidate_created": False,
        "kaggle_accessed": False,
        "family_gates": family_gate,
        "classification": "NO_BOSS_ROUTE_SIGNAL",
        "selection_summary": selection,
    }
    boss_signal = any(family_gate[route]["evidence_candidate"] or family_gate[route]["exploratory_candidate"] for route in ("R1_BOSS_TERMINAL_WIN", "R3_BOSS_HIGHER_PRIZE_KO", "R6_BOSS_KO_FRONT_NON_KO"))
    front_signal = any(family_gate[route]["evidence_candidate"] or family_gate[route]["exploratory_candidate"] for route in ("R2_FRONT_TERMINAL_WIN", "R4_FRONT_KO_BOSS_NO_ATTACK", "R5_FRONT_KO_BOSS_NON_KO"))
    if boss_signal and front_signal:
        summary["classification"] = "MIXED_ROUTE_SIGNAL"
    elif boss_signal:
        summary["classification"] = "BOSS_ROUTE_HYPOTHESIS_FOUND"
    elif front_signal:
        summary["classification"] = "FRONT_ATTACK_HYPOTHESIS_FOUND"
    elif len(games) < 32 or len(summary["families"]) < 4 or len(summary["seats"]) < 2:
        summary["classification"] = "STRUCTURALLY_SPARSE"
    write_json(run / "summary.json", summary)
    lines = [
        "# T3/T4 Boss-versus-front-attack formal route diagnostic",
        "",
        f"- Classification: **{summary['classification']}**",
        f"- Roots: {len(roots)}; branches: {len(branch_rows)}; route pairs: {len(pair_rows)}; distinct games: {len(games)}.",
        f"- Route counts: `{summary['route_counts']}`.",
        f"- Pair outcomes: Boss gain {summary['boss_gain_pairs']}, front gain {summary['front_gain_pairs']}, ties {summary['tie_pairs']}; catastrophic {summary['catastrophic_count']}.",
        "- Public boundary: only normalized public hash, legal semantic action set, parent parity, forced legal first action, and visible board/route state were used.",
        "- The accepted parent was not modified; no candidate, holdout, reserve, Kaggle access, or policy promotion was performed.",
        "",
        "## H1-H5 gate table",
        "",
        "| Route family | Evidence candidate | Exploratory candidate |",
        "|---|---:|---:|",
    ]
    for route in route_names:
        gate = family_gate[route]
        lines.append(f"| {route} | {gate['evidence_candidate']} | {gate['exploratory_candidate']} |")
    lines.extend(["", "Unknown damage is retained as UNKNOWN and never converted to zero. Any passing family is diagnostic evidence only; GPT PRO must decide whether a hypothesis is worth formalizing."])
    (run / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for route in route_names:
        if family_gate[route]["evidence_candidate"] or family_gate[route]["exploratory_candidate"]:
            (run / f"HYPOTHESIS_DRAFT_{route}.md").write_text(
                f"# Diagnostic hypothesis draft: {route}\n\nThis is a public counterfactual signal only. No candidate implementation or promotion is authorized. Await GPT PRO direction.\n",
                encoding="utf-8",
            )
    print(json.dumps(summary, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    main()
