"""Classify and gate the final current-turn Active-attack unlock diagnostic."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for path in (REPO_ROOT, REPO_ROOT / "infrastructure"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.ptcg_common import dataclass_to_dict, ensure_engine_on_path  # noqa: E402


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _outcome(result: Any, seat: int) -> str:
    if result == seat:
        return "win"
    if result in (0, 1):
        return "loss"
    return "draw_or_unknown"


def _attack_catalog(engine_dir: Path) -> dict[int, dict[str, Any]]:
    ensure_engine_on_path(engine_dir.resolve())
    from cg.api import all_attack  # type: ignore  # noqa: PLC0415

    return {int(row["attackId"]): row for row in (dataclass_to_dict(item) for item in all_attack())}


def _classify_unlock(
    active_ids: list[int],
    parent_ids: list[int],
    opponent_hp: Any,
    attacks: Mapping[int, Mapping[str, Any]],
) -> tuple[str, list[int], list[dict[str, Any]]]:
    new_ids = sorted(set(active_ids) - set(parent_ids))
    if not new_ids:
        return "NO_UNLOCK", [], []
    details: list[dict[str, Any]] = []
    unknown = False
    positive = False
    ko = False
    hp = opponent_hp if isinstance(opponent_hp, (int, float)) and opponent_hp > 0 else None
    for attack_id in new_ids:
        attack = attacks.get(attack_id)
        if not attack:
            unknown = True
            details.append({"attack_id": attack_id, "known": False, "damage": None, "text": None})
            continue
        damage = attack.get("damage")
        text = str(attack.get("text") or "")
        known_damage = isinstance(damage, (int, float))
        # A non-empty effect text can alter damage/cost/targeting, so it is not
        # treated as an exact U1/U2 proof in this diagnostic.
        is_known_simple = known_damage and not text
        if not is_known_simple:
            unknown = True
        if isinstance(damage, (int, float)) and damage > 0:
            positive = True
            if hp is not None and damage >= hp and is_known_simple:
                ko = True
        details.append(
            {
                "attack_id": attack_id,
                "name": attack.get("name"),
                "known": is_known_simple,
                "damage": damage,
                "text": text,
                "energies": attack.get("energies"),
            }
        )
    if unknown:
        return "U4_UNKNOWN", new_ids, details
    if ko:
        return "U1_EXACT_KO", new_ids, details
    if positive:
        return "U2_POSITIVE_DAMAGE", new_ids, details
    return "U3_EXACT_ZERO_DAMAGE", new_ids, details


def _behavior(parent: Mapping[str, Any], active: Mapping[str, Any]) -> str:
    p = bool(parent.get("same_turn_attack"))
    a = bool(active.get("same_turn_attack"))
    if a and not p:
        return "B1_ACTIVE_ONLY"
    if a and p:
        return "B2_BOTH"
    if not a and not p:
        return "B3_NEITHER"
    return "B4_PARENT_ONLY"


def _valid(row: Mapping[str, Any]) -> bool:
    return bool(
        row.get("status") == "complete"
        and row.get("runner_exit_code") == 0
        and row.get("engine_import_ok") is True
        and row.get("root_match") is True
        and row.get("post_attach_comparable") is True
        and int(row.get("action_errors") or 0) == 0
        and not row.get("hit_max_steps")
    )


def aggregate(roots_path: Path, branches_path: Path, engine_dir: Path, output: Path) -> dict[str, Any]:
    roots = {str(row["root_id"]): row for row in _load_jsonl(roots_path)}
    branches = _load_jsonl(branches_path)
    by_root: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in branches:
        by_root[str(row.get("root_id"))][str(row.get("branch"))] = row
    attacks = _attack_catalog(engine_dir)
    classified: list[dict[str, Any]] = []
    for root_id, root in roots.items():
        pair = by_root.get(root_id, {})
        parent = pair.get("parent", {})
        active = pair.get("active", {})
        parent_post = parent.get("post_attach_observation") or {}
        active_post = active.get("post_attach_observation") or {}
        unlock_class, new_attack_ids, attack_details = _classify_unlock(
            [int(x) for x in active_post.get("attack_option_ids") or []],
            [int(x) for x in parent_post.get("attack_option_ids") or []],
            active_post.get("opponent_active_hp"),
            attacks,
        )
        comparable = _valid(parent) and _valid(active)
        current_turn_unlock = bool(
            comparable
            and int(root.get("root_attack_option_count") or 0) == 0
            and len(parent_post.get("attack_option_ids") or []) == 0
            and len(active_post.get("attack_option_ids") or []) >= 1
        )
        behavior = _behavior(parent, active) if comparable else "INVALID"
        seat = int(root.get("policy_seat"))
        parent_outcome = _outcome(parent.get("terminal_result"), seat) if comparable else "INVALID"
        active_outcome = _outcome(active.get("terminal_result"), seat) if comparable else "INVALID"
        gain = parent_outcome == "loss" and active_outcome == "win"
        regression = parent_outcome == "win" and active_outcome == "loss"
        catastrophic = bool(regression and behavior == "B1_ACTIVE_ONLY" and unlock_class in {"U1_EXACT_KO", "U2_POSITIVE_DAMAGE"})
        classified.append(
            {
                "root_id": root_id,
                "panel": root.get("panel"),
                "opponent_family": root.get("opponent_family"),
                "opponent_policy_id": root.get("opponent_policy_id"),
                "game": root.get("game"),
                "seed": root.get("seed"),
                "policy_seat": seat,
                "turn": root.get("turn"),
                "callback_index": root.get("callback_index"),
                "energy_serial": root.get("energy_serial"),
                "root_attack_option_count": root.get("root_attack_option_count"),
                "parent_status": parent.get("status"),
                "active_status": active.get("status"),
                "parent_post_attach_comparable": parent.get("post_attach_comparable"),
                "active_post_attach_comparable": active.get("post_attach_comparable"),
                "comparable": comparable,
                "parent_terminal_result": parent.get("terminal_result"),
                "active_terminal_result": active.get("terminal_result"),
                "parent_outcome": parent_outcome,
                "active_outcome": active_outcome,
                "gain": gain,
                "regression": regression,
                "catastrophic": catastrophic,
                "behavior": behavior,
                "parent_same_turn_attack": parent.get("same_turn_attack"),
                "active_same_turn_attack": active.get("same_turn_attack"),
                "parent_post_attack_ids": sorted(int(x) for x in parent_post.get("attack_option_ids") or []),
                "active_post_attack_ids": sorted(int(x) for x in active_post.get("attack_option_ids") or []),
                "new_attack_ids": new_attack_ids,
                "opponent_active_hp": active_post.get("opponent_active_hp"),
                "unlock_class": unlock_class if current_turn_unlock else "NOT_CURRENT_TURN_UNLOCK",
                "current_turn_unlock": current_turn_unlock,
                "attack_details": attack_details,
                "parent_first_attack_id": parent.get("first_attack_id"),
                "active_first_attack_id": active.get("first_attack_id"),
                "engine_import_ok": bool(parent.get("engine_import_ok") and active.get("engine_import_ok")),
                "root_match": bool(parent.get("root_match") and active.get("root_match")),
                "action_errors": int(parent.get("action_errors") or 0) + int(active.get("action_errors") or 0),
                "max_step": bool(parent.get("hit_max_steps") or active.get("hit_max_steps")),
            }
        )

    valid = [row for row in classified if row["comparable"]]
    unlock = [row for row in valid if row["current_turn_unlock"]]
    u12_b1 = [row for row in unlock if row["unlock_class"] in {"U1_EXACT_KO", "U2_POSITIVE_DAMAGE"} and row["behavior"] == "B1_ACTIVE_ONLY"]
    games: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in valid:
        key = (row["panel"], row["opponent_family"], row["opponent_policy_id"], row["game"], row["seed"], row["policy_seat"])
        games[key].append(row)
    game_rows: list[dict[str, Any]] = []
    for key, values in sorted(games.items(), key=lambda item: tuple(str(x) for x in item[0])):
        game_rows.append(
            {
                "panel": key[0],
                "opponent_family": key[1],
                "opponent_policy_id": key[2],
                "game": key[3],
                "seed": key[4],
                "policy_seat": key[5],
                "root_count": len(values),
                "gain": any(row["gain"] for row in values),
                "regression": any(row["regression"] for row in values),
                "net": int(any(row["gain"] for row in values)) - int(any(row["regression"] for row in values)),
                "root_ids": [row["root_id"] for row in values],
            }
        )
    game_gains = sum(bool(row["gain"]) for row in game_rows)
    game_regressions = sum(bool(row["regression"]) for row in game_rows)
    unlock_gains = sum(bool(row["gain"]) for row in unlock)
    unlock_regressions = sum(bool(row["regression"]) for row in unlock)
    u12_b1_gains = sum(bool(row["gain"]) for row in u12_b1)
    u12_b1_regressions = sum(bool(row["regression"]) for row in u12_b1)
    families = sorted({str(row["opponent_family"]) for row in unlock})
    seats = sorted({int(row["policy_seat"]) for row in unlock})
    unlock_games = {(
        row["panel"], row["opponent_family"], row["opponent_policy_id"], row["game"], row["seed"]
    ) for row in unlock}
    catastrophic_rows = [row for row in unlock if row["catastrophic"]]
    if len(unlock) < 12 or len(unlock_games) < 8 or len(families) < 3 or seats != [0, 1]:
        gate = "STRUCTURALLY_SPARSE"
    elif (
        len(u12_b1) >= 8
        and len({row["root_id"] for row in u12_b1}) >= 8
        and len({(row["panel"], row["opponent_family"], row["opponent_policy_id"], row["game"], row["seed"]) for row in u12_b1}) >= 6
        and len({row["opponent_family"] for row in u12_b1}) >= 3
        and {int(row["policy_seat"]) for row in u12_b1} == {0, 1}
        and game_gains >= 4
        and game_regressions <= 1
        and game_gains - game_regressions >= 3
        and unlock_gains >= unlock_regressions
        and not catastrophic_rows
        and u12_b1_gains - u12_b1_regressions > 0
    ):
        gate = "HYPOTHESIS_ELIGIBLE_NO_CANDIDATE"
    elif (
        game_regressions > game_gains
        or unlock_gains < unlock_regressions
        or catastrophic_rows
        or sum(row["behavior"] == "B4_PARENT_ONLY" for row in unlock) >= 2
        or u12_b1_gains - u12_b1_regressions <= 0
    ):
        gate = "REJECTED"
    else:
        gate = "INCONCLUSIVE"

    summary = {
        "schema_version": "archaludon_current_turn_attack_unlock_summary.v1",
        "diagnostic": "T7_CURRENT_TURN_ATTACK_UNLOCK_BY_ATTACH_DIAGNOSTIC_V1",
        "root_count": len(roots),
        "branch_rows": len(branches),
        "comparable_roots": len(valid),
        "unlock_roots": len(unlock),
        "unlock_games": len(unlock_games),
        "opponent_families": families,
        "seats": seats,
        "behavior_counts": {name: sum(row["behavior"] == name for row in unlock) for name in ("B1_ACTIVE_ONLY", "B2_BOTH", "B3_NEITHER", "B4_PARENT_ONLY")},
        "unlock_class_counts": {name: sum(row["unlock_class"] == name for row in unlock) for name in ("U1_EXACT_KO", "U2_POSITIVE_DAMAGE", "U3_EXACT_ZERO_DAMAGE", "U4_UNKNOWN")},
        "game_gain": game_gains,
        "game_regression": game_regressions,
        "game_net": game_gains - game_regressions,
        "unlock_gain": unlock_gains,
        "unlock_regression": unlock_regressions,
        "unlock_net": unlock_gains - unlock_regressions,
        "u12_b1_roots": len(u12_b1),
        "u12_b1_gain": u12_b1_gains,
        "u12_b1_regression": u12_b1_regressions,
        "u12_b1_net": u12_b1_gains - u12_b1_regressions,
        "catastrophic_regressions": len(catastrophic_rows),
        "all_engine_import_ok": all(bool(row.get("engine_import_ok")) for row in branches),
        "all_root_matches": all(bool(row.get("root_match")) for row in branches),
        "action_errors": sum(int(row.get("action_errors") or 0) for row in branches),
        "max_step": sum(bool(row.get("hit_max_steps")) for row in branches),
        "holdout_opened": False,
        "candidate_created": False,
        "gate": gate,
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "unlock_classification.csv").write_text("", encoding="utf-8")
    class_fields = [key for key in classified[0].keys() if key != "attack_details"] if classified else []
    class_rows = []
    for row in classified:
        flat = dict(row)
        flat["new_attack_ids"] = json.dumps(flat["new_attack_ids"], separators=(",", ":"))
        flat["parent_post_attack_ids"] = json.dumps(flat["parent_post_attack_ids"], separators=(",", ":"))
        flat["active_post_attack_ids"] = json.dumps(flat["active_post_attack_ids"], separators=(",", ":"))
        flat["attack_details"] = json.dumps(flat["attack_details"], ensure_ascii=True, separators=(",", ":"))
        class_rows.append(flat)
    _write_csv(output / "unlock_classification.csv", class_rows, [key for key in class_rows[0].keys()] if class_rows else ["root_id"])
    _write_csv(output / "root_results.csv", class_rows, [key for key in class_rows[0].keys()] if class_rows else ["root_id"])
    game_flat = []
    for row in game_rows:
        flat = dict(row)
        flat["root_ids"] = json.dumps(flat["root_ids"], ensure_ascii=True, separators=(",", ":"))
        game_flat.append(flat)
    _write_csv(output / "game_results.csv", game_flat, list(game_flat[0].keys()) if game_flat else ["game"])
    _write_csv(output / "catastrophic_regressions.csv", [dict(row, attack_details=json.dumps(row["attack_details"], ensure_ascii=True, separators=(",", ":"))) for row in catastrophic_rows], list(class_rows[0].keys()) if class_rows else ["root_id"])
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", type=Path, required=True)
    parser.add_argument("--branches", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = aggregate(args.roots.resolve(), args.branches.resolve(), args.engine_dir.resolve(), args.output.resolve())
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
