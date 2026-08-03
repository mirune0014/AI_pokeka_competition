#!/usr/bin/env python3
"""Audit v63 outcome-flip traces for the exact Crustle counter sequence."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
from typing import Any


GARCHOMP_EX = 381
ROSERADE = 342
SPIRITOMB = 387
CRUSTLE = 345
RAGING_CURSE = 540
CORKSCREW_DIVE = 531

MAIN_CONTEXT = 0
SWITCH_CONTEXT = 3
PLAY_OPTION = 7
ATTACH_OPTION = 8
ATTACK_OPTION = 13
RETREAT_OPTION = 12
BENCH_AREA = 5


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def selected_options(event: dict[str, Any]) -> list[dict[str, Any]]:
    options = event.get("options") or []
    return [options[index] for index in event.get("action") or [] if 0 <= index < len(options)]


def selected_option(event: dict[str, Any]) -> dict[str, Any] | None:
    options = selected_options(event)
    return options[0] if len(options) == 1 else None


def side(snapshot: dict[str, Any], seat: int) -> dict[str, Any]:
    prefix = f"p{seat}_"
    return {
        "active": snapshot.get(prefix + "active"),
        "active_hp": snapshot.get(prefix + "active_hp"),
        "active_max_hp": snapshot.get(prefix + "active_max_hp"),
        "active_energy": snapshot.get(prefix + "active_energy", 0),
        "bench": snapshot.get(prefix + "bench") or [],
        "bench_hp": snapshot.get(prefix + "bench_hp") or [],
        "bench_max_hp": snapshot.get(prefix + "bench_max_hp") or [],
        "bench_energy": snapshot.get(prefix + "bench_energy") or [],
    }


def damage(hp: Any, max_hp: Any) -> int:
    return max(0, int(max_hp or 0) - int(hp or 0))


def bench_damage(player: dict[str, Any]) -> int:
    return sum(
        damage(hp, max_hp)
        for hp, max_hp in zip(player["bench_hp"], player["bench_max_hp"])
    )


def roserade_bonus(player: dict[str, Any]) -> int:
    return 30 * (
        int(player["active"] == ROSERADE)
        + sum(card_id == ROSERADE for card_id in player["bench"])
    )


def option_card_id(event: dict[str, Any], option: dict[str, Any]) -> int | None:
    index = option.get("index")
    hand = event.get("own_hand_ids") or []
    if option.get("area", 2) == 2 and isinstance(index, int) and 0 <= index < len(hand):
        return int(hand[index])
    return None


def option_target_id(event: dict[str, Any], option: dict[str, Any], seat: int) -> int | None:
    if option.get("inPlayArea") != BENCH_AREA:
        return None
    index = option.get("inPlayIndex")
    bench = side(event.get("snapshot") or {}, seat)["bench"]
    if isinstance(index, int) and 0 <= index < len(bench):
        return int(bench[index])
    return None


def decision_state_key(event: dict[str, Any]) -> tuple[Any, ...]:
    return (
        event.get("player"),
        event.get("context"),
        event.get("context_card_id"),
        event.get("effect_card_id"),
        event.get("select_type"),
        event.get("min_count"),
        event.get("max_count"),
        event.get("options"),
        event.get("own_hand_ids"),
        event.get("snapshot"),
    )


def first_divergence(
    baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]
) -> tuple[int | None, bool]:
    for index, (base_event, cand_event) in enumerate(zip(baseline, candidate)):
        if decision_state_key(base_event) != decision_state_key(cand_event):
            return index, False
        if base_event.get("action") != cand_event.get("action"):
            return index, True
    if len(baseline) != len(candidate):
        return min(len(baseline), len(candidate)), False
    return None, True


def approved_first_action(event: dict[str, Any], seat: int) -> tuple[bool, str, int]:
    snapshot = event.get("snapshot") or {}
    own = side(snapshot, seat)
    opp = side(snapshot, 1 - seat)
    option = selected_option(event)
    if (
        event.get("player") != seat
        or event.get("context") != MAIN_CONTEXT
        or own["active"] != GARCHOMP_EX
        or damage(own["active_hp"], own["active_max_hp"]) <= 0
        or opp["active"] != CRUSTLE
        or option is None
    ):
        return False, "outside_predicate", 0

    active_damage = damage(own["active_hp"], own["active_max_hp"])
    projected_base = bench_damage(own) + active_damage + roserade_bonus(own)
    option_type = option.get("type")
    action_kind = ""
    projected = 0
    if option_type == PLAY_OPTION and option_card_id(event, option) == SPIRITOMB:
        action_kind = "play_spiritomb"
        projected = projected_base
    elif (
        option_type == ATTACH_OPTION
        and option_target_id(event, option, seat) == SPIRITOMB
    ):
        action_kind = "attach_spiritomb"
        target_index = int(option["inPlayIndex"])
        projected = projected_base - damage(
            own["bench_hp"][target_index], own["bench_max_hp"][target_index]
        )
    elif option_type == RETREAT_OPTION:
        action_kind = "retreat"
        projected_values = []
        for index, card_id in enumerate(own["bench"]):
            if card_id == SPIRITOMB and int(own["bench_energy"][index] or 0) >= 1:
                projected_values.append(
                    projected_base
                    - damage(own["bench_hp"][index], own["bench_max_hp"][index])
                )
        projected = max(projected_values, default=0)
    else:
        return False, "wrong_first_action", 0

    return projected >= int(opp["active_hp"] or 0), action_kind, projected


def route_completion(
    events: list[dict[str, Any]], start: int, seat: int
) -> dict[str, Any]:
    start_event = events[start]
    turn = (start_event.get("snapshot") or {}).get("turn")
    saw_play = False
    saw_attach = False
    saw_retreat = False
    saw_promote = False
    saw_attack = False
    corkscrew_before_attack = False
    attack_damage = 0
    target_hp = 0
    phase_order: list[str] = []

    for event in events[start:]:
        snapshot = event.get("snapshot") or {}
        if snapshot.get("turn") != turn:
            break
        if event.get("player") != seat:
            continue
        option = selected_option(event)
        if option is None:
            continue
        option_type = option.get("type")
        if event.get("context") == MAIN_CONTEXT:
            if option_type == PLAY_OPTION and option_card_id(event, option) == SPIRITOMB:
                saw_play = True
                phase_order.append("play")
            elif option_type == ATTACH_OPTION and option_target_id(event, option, seat) == SPIRITOMB:
                saw_attach = True
                phase_order.append("attach")
            elif option_type == RETREAT_OPTION:
                saw_retreat = True
                phase_order.append("retreat")
            elif option_type == ATTACK_OPTION and option.get("attackId") == CORKSCREW_DIVE:
                corkscrew_before_attack = True
                phase_order.append("corkscrew")
            elif option_type == ATTACK_OPTION and option.get("attackId") == RAGING_CURSE:
                own = side(snapshot, seat)
                opp = side(snapshot, 1 - seat)
                attack_damage = bench_damage(own) + roserade_bonus(own)
                target_hp = int(opp["active_hp"] or 0)
                saw_attack = own["active"] == SPIRITOMB and opp["active"] == CRUSTLE
                phase_order.append("raging_curse")
                break
        elif event.get("context") == SWITCH_CONTEXT and option_type == 3:
            index = option.get("index")
            own = side(snapshot, seat)
            if isinstance(index, int) and 0 <= index < len(own["bench"]):
                saw_promote = own["bench"][index] == SPIRITOMB
                if saw_promote:
                    phase_order.append("promote")

    initial_option = selected_option(start_event) or {}
    initial_kind = initial_option.get("type")
    required_play = initial_kind == PLAY_OPTION
    own_at_start = side(start_event.get("snapshot") or {}, seat)
    had_energized_spiritomb = any(
        card_id == SPIRITOMB and int(own_at_start["bench_energy"][index] or 0) >= 1
        for index, card_id in enumerate(own_at_start["bench"])
    )
    required_attach = not had_energized_spiritomb
    complete = (
        (saw_play or not required_play)
        and (saw_attach or not required_attach)
        and saw_retreat
        and saw_promote
        and saw_attack
        and attack_damage >= target_hp
        and not corkscrew_before_attack
    )
    return {
        "complete": complete,
        "saw_play": saw_play,
        "saw_attach": saw_attach,
        "saw_retreat": saw_retreat,
        "saw_promote": saw_promote,
        "saw_attack": saw_attack,
        "corkscrew_before_attack": corkscrew_before_attack,
        "attack_damage": attack_damage,
        "target_hp": target_hp,
        "phase_order": ">".join(phase_order),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--panel",
        action="append",
        required=True,
        help="Panel name and trace directory as NAME=PATH.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    for value in args.panel:
        name, raw_path = value.split("=", 1)
        trace_root = Path(raw_path)
        manifest_rows = read_jsonl(trace_root / "manifest.jsonl")
        grouped: dict[tuple[int, int], dict[str, dict[str, Any]]] = {}
        for row in manifest_rows:
            grouped.setdefault((int(row["seed"]), int(row["seat"])), {})[row["role"]] = row

        for (seed, seat), pair in sorted(grouped.items()):
            baseline_meta = pair["baseline"]
            candidate_meta = pair["candidate"]
            baseline_path = Path(baseline_meta["trace_dir"]) / "game_0000.jsonl"
            candidate_path = Path(candidate_meta["trace_dir"]) / "game_0000.jsonl"
            baseline_events = read_jsonl(baseline_path)
            candidate_events = read_jsonl(candidate_path)
            divergence, aligned = first_divergence(baseline_events, candidate_events)
            approved = False
            action_kind = ""
            projected = 0
            route = {
                "complete": False,
                "saw_play": False,
                "saw_attach": False,
                "saw_retreat": False,
                "saw_promote": False,
                "saw_attack": False,
                "corkscrew_before_attack": False,
                "attack_damage": 0,
                "target_hp": 0,
                "phase_order": "",
            }
            if divergence is not None and divergence < len(candidate_events):
                approved, action_kind, projected = approved_first_action(
                    candidate_events[divergence], seat
                )
                route = route_completion(candidate_events, divergence, seat)
            rows.append(
                {
                    "panel": name,
                    "seed": seed,
                    "seat": seat,
                    "baseline_expected_win": int(baseline_meta["expected_win"]),
                    "candidate_expected_win": int(candidate_meta["expected_win"]),
                    "baseline_exit_code": int(baseline_meta["exit_code"]),
                    "candidate_exit_code": int(candidate_meta["exit_code"]),
                    "divergence_index": divergence,
                    "state_aligned_at_divergence": aligned,
                    "approved_first_action": approved,
                    "first_action_kind": action_kind,
                    "projected_damage": projected,
                    **route,
                }
            )

    if not rows:
        raise ValueError("no trace pairs found")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "routes.csv", rows)
    summary = {
        "games": len(rows),
        "panels": dict(Counter(row["panel"] for row in rows)),
        "all_exit_zero": all(
            row["baseline_exit_code"] == 0 and row["candidate_exit_code"] == 0
            for row in rows
        ),
        "all_expected_flips": all(
            row["baseline_expected_win"] == 0 and row["candidate_expected_win"] == 1
            for row in rows
        ),
        "state_aligned_at_divergence": sum(
            bool(row["state_aligned_at_divergence"]) for row in rows
        ),
        "approved_first_actions": sum(bool(row["approved_first_action"]) for row in rows),
        "complete_routes": sum(bool(row["complete"]) for row in rows),
        "corkscrew_before_route": sum(bool(row["corkscrew_before_attack"]) for row in rows),
        "first_action_kinds": dict(Counter(row["first_action_kind"] for row in rows)),
        "per_panel": {
            panel: {
                "games": len(panel_rows),
                "approved_first_actions": sum(bool(row["approved_first_action"]) for row in panel_rows),
                "complete_routes": sum(bool(row["complete"]) for row in panel_rows),
            }
            for panel in sorted({row["panel"] for row in rows})
            for panel_rows in [[row for row in rows if row["panel"] == panel]]
        },
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
