"""Summarize staged Alakazam sidecars and verify checked-runner identity.

No win-rate aggregate is produced here.  Outcome authority remains the checked
paired-results CSV supplied with ``--checked``.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from alakazam_staged_metrics import (
    ADDED_ONLY_IDS,
    SCHEMA_VERSION,
    as_int,
    game_metrics,
    nearest_rank_p95,
    pair_callback_events,
    read_jsonl,
    sha256_file,
    stable_json,
)


def parse_checked(value: str) -> tuple[str, str, Path]:
    label, separator, raw_path = value.partition("=")
    version, role_separator, role = label.rpartition("@")
    if not separator or not role_separator or not version or role not in {
        "baseline",
        "candidate",
    }:
        raise argparse.ArgumentTypeError(
            "--checked must be VERSION@baseline=PATH or VERSION@candidate=PATH"
        )
    return version, role, Path(raw_path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    field: (
                        stable_json(value)
                        if isinstance((value := row.get(field)), (dict, list, tuple))
                        else "" if value is None else value
                    )
                    for field in fields
                }
            )


def load_checked(
    specs: Iterable[tuple[str, str, Path]]
) -> tuple[dict[tuple[str, str, int, int], dict[str, Any]], list[dict[str, Any]]]:
    evidence: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    diagnostics: list[dict[str, Any]] = []
    for version, role, raw_path in specs:
        path = raw_path.resolve()
        rows = read_csv(path)
        result_field, steps_field = f"{role}_result", f"{role}_steps"
        required = {"opponent", "seat", "seed", result_field, steps_field}
        if rows and not required.issubset(rows[0]):
            raise ValueError(f"{path} lacks checked fields {sorted(required)}")
        for line_offset, row in enumerate(rows, 2):
            opponent = row.get("opponent", "")
            seat, seed = as_int(row.get("seat")), as_int(row.get("seed"))
            result, steps = as_int(row.get(result_field)), as_int(row.get(steps_field))
            if seat not in (0, 1) or seed is None:
                diagnostics.append(
                    {
                        "kind": "CHECKED_KEY_INVALID",
                        "path": str(path),
                        "line": line_offset,
                    }
                )
                continue
            key = (version, opponent, seat, seed)
            value = {
                "version": version,
                "opponent": opponent,
                "seat": seat,
                "seed": seed,
                "result": result,
                "steps": steps,
                "role": role,
                "path": str(path),
                "sha256": sha256_file(path),
                "line": line_offset,
            }
            previous = evidence.get(key)
            if previous is not None:
                if (previous["result"], previous["steps"]) != (result, steps):
                    diagnostics.append(
                        {
                            "kind": "CHECKED_DUPLICATE_CONFLICT",
                            "key": key,
                            "left": previous,
                            "right": value,
                        }
                    )
                else:
                    diagnostics.append(
                        {
                            "kind": "CHECKED_DUPLICATE_IDENTICAL",
                            "key": key,
                            "left_path": previous["path"],
                            "right_path": str(path),
                        }
                    )
            else:
                evidence[key] = value
    return evidence, diagnostics


def block_rows(suite_dir: Path) -> list[dict[str, Any]]:
    ledger = suite_dir / "block_ledger.jsonl"
    if not ledger.is_file():
        raise FileNotFoundError(ledger)
    return read_jsonl(ledger)


def local_summaries(
    block: Mapping[str, Any],
) -> dict[int, dict[str, Any]]:
    path = Path(str(block["summary"]))
    if not path.is_file():
        return {}
    rows = read_jsonl(path)
    return {
        as_int(row.get("game")): row
        for row in rows
        if as_int(row.get("game")) is not None
    }


def sidecar_callbacks(
    block: Mapping[str, Any],
) -> tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]]]:
    root = Path(str(block["block_dir"])) / "sidecars"
    by_game: dict[int, list[dict[str, Any]]] = defaultdict(list)
    diagnostics: list[dict[str, Any]] = []
    if not root.is_dir():
        diagnostics.append(
            {"kind": "SIDECAR_DIR_MISSING", "block_dir": block["block_dir"]}
        )
        return by_game, diagnostics
    for path in sorted(root.glob("game_*.jsonl")):
        complete, pairing = pair_callback_events(read_jsonl(path))
        for row in complete:
            game = as_int(row["start"].get("game"))
            if game is not None:
                by_game[game].append(row)
        diagnostics.extend(
            {**row, "path": str(path)}
            for row in pairing
        )
    return by_game, diagnostics


def callback_flat_rows(
    callbacks: Iterable[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for callback in callbacks:
        start, end = callback["start"], callback["end"]
        obs = start.get("observation") or {}
        output.append(
            {
                "version": start.get("version"),
                "opponent": start.get("opponent"),
                "seat": start.get("policy_seat"),
                "seed": start.get("seed"),
                "game": start.get("game"),
                "callback_ordinal": start.get("callback_ordinal"),
                "turn": obs.get("turn"),
                "turn_action_count": obs.get("turn_action_count"),
                "context": obs.get("context"),
                "option_count": obs.get("option_count"),
                "selected_action": end.get("selected_action"),
                "selected_options": end.get("selected_options"),
                "decision_ns": end.get("decision_ns"),
                "structurally_valid": end.get("structurally_valid"),
                "exception": end.get("exception"),
                "integrated_trace_prefix_reset": end.get(
                    "integrated_trace_prefix_reset"
                ),
                "integrated_trace_suffix": end.get("integrated_trace_suffix"),
                "version_trace_name": end.get("version_trace_name"),
                "reason_tags": end.get("reason_tags"),
                "generic_handler_hits": end.get("generic_handler_hits"),
                "generic_fallback_status": end.get("generic_fallback_status"),
                "generic_fallback_selected": end.get(
                    "generic_fallback_selected"
                ),
                "parent_fallback_selected": end.get(
                    "parent_fallback_selected"
                ),
                "first_legal_fallback_selected": end.get(
                    "first_legal_fallback_selected"
                ),
                "removed_rule_hit_status": end.get("removed_rule_hit_status"),
                "removed_rule_hits": end.get("removed_rule_hits"),
                "added_rule_hits": end.get("added_rule_hits"),
                "continuity_rule_hits": end.get("continuity_rule_hits"),
            }
        )
    return output


def ratio(numerator: int | float | None, denominator: int | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def aggregate_rows(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for game in games:
        groups[(game["version"], game["opponent"], game["seat"])].append(game)
        groups[(game["version"], game["opponent"], "ALL")].append(game)
        groups[(game["version"], "ALL", game["seat"])].append(game)
        groups[(game["version"], "ALL", "ALL")].append(game)
    rows: list[dict[str, Any]] = []
    for (version, opponent, seat), values in sorted(
        groups.items(), key=lambda item: tuple(map(str, item[0]))
    ):
        formal = [row for row in values if row["formal_rate_eligible"]]
        callbacks = sum(as_int(row.get("callback_count")) or 0 for row in values)
        started_games = sum(bool(row.get("started")) for row in values)
        first_attack_turns = [
            as_int(row.get("first_attack_turn"))
            for row in formal
            if as_int(row.get("first_attack_turn")) is not None
        ]
        max_consecutive = [
            as_int(row.get("max_consecutive_attack_turns")) or 0 for row in formal
        ]
        tail_n = sum(
            as_int(row.get("attack_gap_tail_count")) or 0
            for row in formal
            if row.get("attack_gap_tail_count") is not None
        )
        tail_d = sum(
            as_int(row.get("attack_gap_tail_denominator")) or 0
            for row in formal
            if row.get("attack_gap_tail_denominator") is not None
        )
        between_n = sum(
            as_int(row.get("attack_gap_between_count")) or 0
            for row in formal
            if row.get("attack_gap_between_count") is not None
        )
        between_d = sum(
            as_int(row.get("attack_gap_between_denominator")) or 0
            for row in formal
            if row.get("attack_gap_between_denominator") is not None
        )
        attack_hands = [
            as_int(hand)
            for row in formal
            for hand in (row.get("attack_hand_sizes") or [])
            if as_int(hand) is not None
        ]
        hand_power = [
            item
            for row in formal
            for item in (row.get("hand_power_attacks") or [])
            if isinstance(item, Mapping)
        ]
        hand_power_counters = [
            as_int(item.get("damage_counters"))
            for item in hand_power
            if as_int(item.get("damage_counters")) is not None
        ]
        hand_power_damage = [
            as_int(item.get("damage"))
            for item in hand_power
            if as_int(item.get("damage")) is not None
        ]
        post_n_values = [
            as_int(row.get("post_ko_continuity_count"))
            for row in formal
            if row.get("post_ko_continuity_count") is not None
        ]
        post_d = sum(
            as_int(row.get("post_ko_continuity_denominator")) or 0
            for row in formal
        )
        second_known = [
            row
            for row in formal
            if row.get("second_alakazam_line_before_first_hand_power") is not None
        ]
        second_n = (
            sum(
                bool(row["second_alakazam_line_before_first_hand_power"])
                for row in second_known
            )
            if second_known
            else None
        )
        ko_n_values = [
            as_int(row.get("certified_clear_ko_miss_count"))
            for row in formal
            if row.get("certified_clear_ko_miss_count") is not None
        ]
        ko_d = sum(
            as_int(row.get("certified_clear_ko_miss_denominator")) or 0
            for row in formal
        )
        new_only_exposed = [
            item
            for row in formal
            for item in (row.get("added_slot_exposed_serials") or [])
            if isinstance(item, Mapping) and as_int(item.get("card_id")) in ADDED_ONLY_IDS
        ]
        new_only_played = [
            item
            for row in formal
            for item in (row.get("added_slot_played_serials") or [])
            if isinstance(item, Mapping) and as_int(item.get("card_id")) in ADDED_ONLY_IDS
        ]
        new_only_unused = [
            item
            for row in formal
            for item in (row.get("added_new_only_unused_serials") or [])
            if isinstance(item, Mapping) and as_int(item.get("card_id")) in ADDED_ONLY_IDS
        ]
        generic_known = sum(
            as_int(row.get("generic_fallback_known_callbacks")) or 0 for row in values
        )
        generic_selected_values = [
            as_int(row.get("generic_fallback_selected_count"))
            for row in values
            if row.get("generic_fallback_selected_count") is not None
        ]
        generic_selected = (
            sum(value or 0 for value in generic_selected_values)
            if generic_known
            else None
        )
        generic_handler = sum(
            as_int(row.get("generic_handler_callback_count")) or 0 for row in values
        )
        parent_fallback = sum(
            as_int(row.get("parent_fallback_selected_count")) or 0 for row in values
        )
        first_legal = sum(
            as_int(row.get("first_legal_fallback_selected_count")) or 0
            for row in values
        )
        removed_known = sum(
            as_int(row.get("removed_rule_hit_known_callbacks")) or 0 for row in values
        )
        removed_label_values = [
            as_int(row.get("removed_rule_hit_count"))
            for row in values
            if row.get("removed_rule_hit_count") is not None
        ]
        removed_callback_values = [
            as_int(row.get("removed_rule_hit_callback_count"))
            for row in values
            if row.get("removed_rule_hit_callback_count") is not None
        ]
        removed_labels = (
            sum(value or 0 for value in removed_label_values) if removed_known else None
        )
        removed_callbacks = (
            sum(value or 0 for value in removed_callback_values)
            if removed_known
            else None
        )
        removed_status = (
            "KNOWN" if callbacks and removed_known == callbacks
            else "PARTIAL" if removed_known
            else "UNKNOWN"
        )
        invalid_callbacks = sum(
            as_int(row.get("invalid_callback_count")) or 0 for row in values
        )
        exception_callbacks = sum(
            as_int(row.get("exception_callback_count")) or 0 for row in values
        )
        exception_games = sum(
            (as_int(row.get("exception_callback_count")) or 0) > 0 for row in values
        )
        timeout_games = sum(bool(row.get("timed_out")) for row in values)
        not_executed_timeout_games = sum(
            bool(row.get("not_executed_due_block_timeout")) for row in values
        )
        max_step_games = sum(bool(row.get("hit_max_steps")) for row in values)
        decisions: list[int] = []
        for row in values:
            decisions.extend(row.get("_decision_values") or [])
        rows.append(
            {
                "version": version,
                "opponent": opponent,
                "seat": seat,
                "scheduled_games": len(values),
                "started_games": started_games,
                "formal_games": len(formal),
                "partial_diagnostic_games": len(values) - len(formal),
                "checked_join_match_games": sum(
                    row.get("checked_join_status") == "MATCH" for row in values
                ),
                "first_attack_games": len(first_attack_turns),
                "first_attack_denominator": len(formal),
                "first_attack_rate": ratio(len(first_attack_turns), len(formal)),
                "first_attack_turn_mean": (
                    sum(first_attack_turns) / len(first_attack_turns)
                    if first_attack_turns
                    else None
                ),
                "max_consecutive_attack_turns_mean": (
                    sum(max_consecutive) / len(max_consecutive)
                    if max_consecutive
                    else None
                ),
                "max_consecutive_attack_turns_denominator": len(max_consecutive),
                "attack_gap_tail_count": tail_n,
                "attack_gap_tail_denominator": tail_d,
                "attack_gap_tail_rate": ratio(tail_n, tail_d),
                "attack_gap_between_count": between_n,
                "attack_gap_between_denominator": between_d,
                "attack_gap_between_rate": ratio(between_n, between_d),
                "attack_hand_observations": len(attack_hands),
                "hand_size_at_attack_mean": (
                    sum(attack_hands) / len(attack_hands) if attack_hands else None
                ),
                "hand_power_attack_count": len(hand_power),
                "hand_power_counter_total": sum(hand_power_counters),
                "hand_power_counter_mean": (
                    sum(hand_power_counters) / len(hand_power_counters)
                    if hand_power_counters
                    else None
                ),
                "hand_power_damage_total": sum(hand_power_damage),
                "hand_power_damage_mean": (
                    sum(hand_power_damage) / len(hand_power_damage)
                    if hand_power_damage
                    else None
                ),
                "hand_power_counter_unit": "2_COUNTERS_PER_HAND_CARD",
                "hand_power_damage_unit": "20_DAMAGE_PER_HAND_CARD",
                "post_ko_continuity_count": (
                    sum(value or 0 for value in post_n_values)
                    if post_n_values
                    else None
                ),
                "post_ko_continuity_denominator": post_d,
                "post_ko_continuity_rate": ratio(
                    sum(value or 0 for value in post_n_values)
                    if post_n_values
                    else None,
                    post_d,
                ),
                "second_line_games": second_n,
                "second_line_denominator": len(second_known),
                "second_line_rate": ratio(second_n, len(second_known)),
                "second_line_definition": "CURRENT_BOARD_BEFORE_FIRST_HAND_POWER",
                "certified_clear_ko_miss_count": (
                    sum(value or 0 for value in ko_n_values)
                    if ko_n_values
                    else None
                ),
                "certified_clear_ko_miss_denominator": ko_d,
                "certified_clear_ko_miss_rate": ratio(
                    sum(value or 0 for value in ko_n_values)
                    if ko_n_values
                    else None,
                    ko_d,
                ),
                "added_new_only_exposed_serial_count": len(new_only_exposed),
                "added_new_only_played_serial_count": len(new_only_played),
                "added_new_only_unused_serial_count": len(new_only_unused),
                "added_card_play_rate": ratio(len(new_only_played), len(new_only_exposed)),
                "unused_added_card_rate": ratio(len(new_only_unused), len(new_only_exposed)),
                "increased_copy_attribution_status": "UNKNOWN_IDENTICAL_CARD_ID",
                "callback_count": callbacks,
                "generic_handler_callback_count": generic_handler,
                "generic_handler_rate": ratio(generic_handler, callbacks),
                "generic_fallback_selected_count": generic_selected,
                "generic_fallback_known_callbacks": generic_known,
                "generic_fallback_selected_rate": ratio(generic_selected, generic_known),
                "parent_fallback_selected_count": parent_fallback,
                "parent_fallback_rate": ratio(parent_fallback, callbacks),
                "first_legal_fallback_selected_count": first_legal,
                "first_legal_fallback_rate": ratio(first_legal, callbacks),
                "removed_rule_hit_count": removed_labels,
                "removed_rule_hit_callback_count": removed_callbacks,
                "removed_rule_hit_known_callbacks": removed_known,
                "removed_rule_hit_status": removed_status,
                "removed_rule_hit_rate": ratio(removed_callbacks, removed_known),
                "invalid_callback_count": invalid_callbacks,
                "invalid_action_rate": ratio(invalid_callbacks, callbacks),
                "exception_callback_count": exception_callbacks,
                "exception_callback_rate": ratio(exception_callbacks, callbacks),
                "exception_game_count": exception_games,
                "exception_game_denominator_scheduled": len(values),
                "exception_game_rate": ratio(exception_games, len(values)),
                "timeout_games": timeout_games,
                "timeout_game_denominator_scheduled": len(values),
                "timeout_rate": ratio(timeout_games, len(values)),
                "max_step_games": max_step_games,
                "not_executed_due_timeout_games": not_executed_timeout_games,
                "not_executed_due_timeout_denominator_scheduled": len(values),
                "not_executed_due_timeout_rate": ratio(not_executed_timeout_games, len(values)),
                "max_step_game_denominator_started": started_games,
                "max_step_hit_rate_started_games": ratio(max_step_games, started_games),
                "decision_count": len(decisions),
                "avg_decision_ns": (
                    sum(decisions) / len(decisions) if decisions else None
                ),
                "p95_decision_ns_nearest_rank": nearest_rank_p95(decisions),
                "outcome_aggregate_authority": "CHECKED_PAIRED_RUNNER_NOT_THIS_FILE",
            }
        )
    return rows


def summarize(args: argparse.Namespace) -> dict[str, Any]:
    suite = args.suite_dir.resolve()
    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError(f"fresh --output-dir required: {output}")
    output.mkdir(parents=True)
    manifest_path = suite / "suite_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checked, checked_diagnostics = load_checked(args.checked)
    expected_keys: set[tuple[str, str, int, int]] = set()
    used_checked: set[tuple[str, str, int, int]] = set()
    game_rows: list[dict[str, Any]] = []
    all_callbacks: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = list(checked_diagnostics)
    for block in block_rows(suite):
        summaries = local_summaries(block)
        callbacks_by_game, callback_diagnostics = sidecar_callbacks(block)
        diagnostics.extend(callback_diagnostics)
        expected_games = int(manifest["games_per_block"])
        diagnostic_games = {
            as_int(row.get("key")[4])
            for row in callback_diagnostics
            if isinstance(row.get("key"), (list, tuple))
            and len(row.get("key")) > 4
            and as_int(row.get("key")[4]) is not None
        }
        for game_index in range(expected_games):
            version = str(block["version"])
            opponent = str(block["opponent"])
            seat = int(block["seat"])
            seed = int(block["seed_base"]) + game_index
            key = (version, opponent, seat, seed)
            expected_keys.add(key)
            callbacks = callbacks_by_game.get(game_index, [])
            all_callbacks.extend(callbacks)
            local_summary = summaries.get(game_index)
            block_timed_out = bool(block.get("timed_out"))
            has_sidecar_evidence = game_index in callbacks_by_game or game_index in diagnostic_games
            game_timed_out = block_timed_out and local_summary is None and has_sidecar_evidence
            not_executed_due_timeout = (
                block_timed_out and local_summary is None and not has_sidecar_evidence
            )
            metrics = game_metrics(
                callbacks,
                local_summary,
                timed_out=game_timed_out,
            )
            checked_row = checked.get(key)
            if checked_row is None:
                join_status = "CHECKED_MISSING"
            else:
                used_checked.add(key)
                local_result = as_int(local_summary.get("result")) if local_summary else None
                local_steps = as_int(local_summary.get("steps")) if local_summary else None
                join_status = (
                    "MATCH"
                    if (local_result, local_steps)
                    == (checked_row["result"], checked_row["steps"])
                    else "RESULT_OR_STEPS_MISMATCH"
                )
            if join_status != "MATCH":
                metrics["formal_rate_eligible"] = False
                metrics["partial_diagnostic_only"] = True
            decision_values = [
                as_int(callback["end"].get("decision_ns"))
                for callback in callbacks
                if as_int(callback["end"].get("decision_ns")) is not None
            ]
            game_rows.append(
                {
                    "version": version,
                    "opponent": opponent,
                    "seat": seat,
                    "seed_base": int(block["seed_base"]),
                    "game": game_index,
                    "seed": seed,
                    "run_id": block["run_id"],
                    "block_complete": block.get("block_complete"),
                    "block_timed_out": block_timed_out,
                    "not_executed_due_block_timeout": not_executed_due_timeout,
                    "checked_join_status": join_status,
                    "checked_role": checked_row.get("role") if checked_row else None,
                    "checked_result": checked_row.get("result") if checked_row else None,
                    "checked_steps": checked_row.get("steps") if checked_row else None,
                    "local_result": local_summary.get("result") if local_summary else None,
                    "local_steps": local_summary.get("steps") if local_summary else None,
                    "sidecar_pairing_diagnostic_count": sum(
                        isinstance(row.get("key"), (list, tuple))
                        and len(row.get("key")) > 4
                        and as_int(row.get("key")[4]) == game_index
                        for row in callback_diagnostics
                    ),
                    **metrics,
                    "_decision_values": decision_values,
                }
            )
    for key in sorted(set(checked) - used_checked):
        diagnostics.append({"kind": "CHECKED_EXTRA_SCHEDULE_KEY", "key": key})
    join_audit = [
        {
            "version": row["version"],
            "opponent": row["opponent"],
            "seat": row["seat"],
            "seed": row["seed"],
            "local_result": row["local_result"],
            "local_steps": row["local_steps"],
            "checked_result": row["checked_result"],
            "checked_steps": row["checked_steps"],
            "status": row["checked_join_status"],
        }
        for row in game_rows
    ]
    aggregate = aggregate_rows(game_rows)
    callback_rows = callback_flat_rows(all_callbacks)
    game_fields = [
        key
        for key in game_rows[0]
        if not key.startswith("_")
    ] if game_rows else ["version", "opponent", "seat", "seed"]
    write_csv(output / "callback_metrics.csv", callback_rows, list(callback_rows[0]) if callback_rows else ["version", "opponent", "seat", "seed"])
    write_csv(output / "game_metrics.csv", game_rows, game_fields)
    write_csv(output / "metric_aggregates.csv", aggregate, list(aggregate[0]) if aggregate else ["version", "opponent", "seat"])
    write_csv(output / "checked_join_audit.csv", join_audit, list(join_audit[0]) if join_audit else ["version", "opponent", "seat", "seed", "status"])
    exact_join = (
        bool(game_rows)
        and all(row["checked_join_status"] == "MATCH" for row in game_rows)
        and not any(
            row.get("kind")
            in {
                "CHECKED_DUPLICATE_CONFLICT",
                "CHECKED_KEY_INVALID",
                "CHECKED_EXTRA_SCHEDULE_KEY",
                "CALL_START_WITHOUT_END",
                "ORPHAN_CALL_END",
                "DUPLICATE_CALL_START",
            }
            for row in diagnostics
        )
        and expected_keys == used_checked
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "summarizer": str(Path(__file__).resolve()),
        "summarizer_sha256": sha256_file(Path(__file__).resolve()),
        "suite_dir": str(suite),
        "suite_manifest": str(manifest_path),
        "suite_manifest_sha256": sha256_file(manifest_path),
        "checked_inputs": [
            {
                "version": version,
                "role": role,
                "path": str(path.resolve()),
                "sha256": sha256_file(path.resolve()),
            }
            for version, role, path in args.checked
        ],
        "scheduled_games": len(game_rows),
        "formal_rate_games": sum(
            bool(row["formal_rate_eligible"]) for row in game_rows
        ),
        "partial_diagnostic_games": sum(
            bool(row["partial_diagnostic_only"]) for row in game_rows
        ),
        "callbacks": len(callback_rows),
        "checked_schedule_result_steps_exact": exact_join,
        "diagnostics": diagnostics,
        "outputs": {
            name: {
                "path": str(output / name),
                "sha256": sha256_file(output / name),
            }
            for name in (
                "callback_metrics.csv",
                "game_metrics.csv",
                "metric_aggregates.csv",
                "checked_join_audit.csv",
            )
        },
        "outcome_authority": "CHECKED_PAIRED_RUNNER",
        "unknown_rules": {
            "ko_miss": "UNKNOWN unless counter prevention is explicitly certified clear",
            "removed_rule_hit": "UNKNOWN unless explicit trace owner/hit is instrumented",
            "increased_copy_serial": "UNKNOWN_IDENTICAL_CARD_ID",
            "zero_denominator_rate": "N/A represented as blank CSV / null JSON",
            "partial_or_timeout_game": "diagnostic only; never loss-filled",
        },
    }
    (output / "metric_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite-dir", type=Path, required=True)
    parser.add_argument(
        "--checked",
        action="append",
        type=parse_checked,
        required=True,
        metavar="VERSION@ROLE=PATH",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    result = summarize(parse_args())
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    if not result["checked_schedule_result_steps_exact"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
