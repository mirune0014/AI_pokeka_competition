#!/usr/bin/env python3
"""Strict multi-suite C4 sidecar integrity and reach collector."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable


RULE_VERSION = "V4_WALL_SHADOW_FIX6"
SCHEMA_VERSION = 6
PARENT_CLOSURE_SHA256 = (
    "29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157"
)
ANALYZER_SHA256 = (
    "AD14F84C80FC92B95ACB7C585D492910BD46883528CE2F99158AF046EDDAE201"
)
SIDECAR_GLOB = "runs/*/*/seed_*/seat_*/sidecars/game_*.jsonl"
CANDIDATE_KINDS = (
    "RUN_AWAY_ACCELERATION",
    "CERTIFIED_REUSABLE_WALL",
    "CERTIFIED_SACRIFICE_WALL",
    "NO_WALL_OR_UNKNOWN",
)
STRICT = "STRICT_CERTIFIED_WALL"
CHANCE = "PRESERVE_CHANCE_WALL"
HEX64 = re.compile(r"^[0-9A-F]{64}$")

TRACE_REQUIRED = frozenset(
    {
        "schema_version",
        "rule_version",
        "parent_closure_sha256",
        "candidate_closure_sha256",
        "analyzer_component_sha256",
        "state_machine",
        "decision_point",
        "pair_id",
        "decision_id",
        "raw_parent_action",
        "parent_action",
        "proposed_action",
        "applied_action",
        "action_python_type",
        "action_identity",
        "semantic_option_keys",
        "semantic_parent_action_keys",
        "semantic_proposed_action_keys",
        "public_state_material",
        "public_state_fingerprint",
        "pair_material",
        "game_boundary_fingerprint",
        "parent_post_fingerprint",
        "candidate_post_fingerprint",
        "expose_state_fingerprint",
        "wall_state_fingerprint",
        "expose_projection",
        "wall_projection",
        "protected_line",
        "importance",
        "distance_before",
        "distance_without_line",
        "threat",
        "damage_floor",
        "damage_cap",
        "continuity",
        "wall_candidates",
        "candidate_rows",
        "run_away_value",
        "reusable_wall_value",
        "sacrifice_wall_value",
        "bypass",
        "refusal_progress",
        "safe_release",
        "gust_exposure_turns",
        "wall_class",
        "arbitration_reason",
        "outcome_status",
        "outcome_events",
        "certified_draw_count",
        "certified_draw_damage_delta",
        "premium_power_pro_multiplicity",
        "evidenced_policy_cap",
        "safety_cap",
        "hold_entry_turn",
        "hold_deadline",
        "distance_progress_by_turn",
        "rejection_codes",
        "unsupported_reasons",
        "structural_reasons",
        "parser_source",
        "metric_exception",
        "c2_trace_rule_version",
    }
)
ROW_REQUIRED = frozenset(
    {
        "kind",
        "decision_point",
        "wall_class",
        "certification",
        "legality",
        "option_index",
        "semantic_action_key",
        "wall",
        "rejection_codes",
        "unsupported_reasons",
        "structural_reasons",
        "metrics",
        "pareto_vector",
    }
)
WALL_METRICS = frozenset(
    {
        "protected_readiness",
        "hold_turns",
        "own_prize_loss",
        "gust_exposure",
        "resource_loss",
        "lost_draw3",
        "safe_release",
        "final_prize_outcome",
        "remaining_hp",
        "final_safety_cap",
        "survival_margin",
        "hold_entry_turn",
        "hold_deadline",
    }
)
RUN_METRICS = frozenset(
    {
        "certified_draw_count",
        "certified_draw_damage_delta",
        "drawn_card_identities",
        "conversion",
    }
)
OUTCOME_EVENT_TYPES = frozenset(
    {
        "PARENT_AGREEMENT",
        "WALL_ACTIVE",
        "WALL_ATTACKED",
        "WALL_SURVIVED",
        "WALL_KO",
        "OPPONENT_REFUSED",
        "PROTECTED_LINE_PROGRESS",
        "DISTANCE_IMPROVED",
        "GUST_OR_SNIPE_BYPASS",
        "RUN_AWAY_RELEASED",
        "TRADING_PLACES_RELEASED",
        "PROMOTION_DESTINATION",
        "PROTECTED_ATTACKER_ATTACKED",
        "OPPONENT_CONTINUITY_OBSERVED",
        "PRIZE_DELTA",
        "GAME_END",
        "TRUNCATION",
    }
)
PUBLIC_OBSERVATION_KEYS = frozenset(
    {
        "turn",
        "turn_action_count",
        "your_index",
        "first_player",
        "result",
        "context",
        "select_type",
        "min_count",
        "max_count",
        "option_count",
        "options",
        "own_hand",
        "own_active",
        "own_active_hp",
        "own_active_energy",
        "own_bench",
        "own_discard",
        "opponent_active",
        "opponent_active_hp",
        "opponent_active_energy",
        "logs_raw",
        "log_serial_fields",
    }
)
PUBLIC_OPTION_KEYS = frozenset(
    {
        "option_index",
        "type",
        "area",
        "index",
        "player_index",
        "card_id",
        "serial",
        "attack_id",
        "in_play_area",
        "in_play_index",
        "raw",
    }
)
PUBLIC_LOG_SERIAL_FIELDS = (
    "type",
    "playerIndex",
    "cardId",
    "cardIdActive",
    "cardIdBench",
    "cardIdBefore",
    "cardIdAfter",
    "cardIdTarget",
    "attackId",
    "serial",
    "serialActive",
    "serialBench",
    "serialBefore",
    "serialAfter",
    "serialTarget",
    "fromArea",
    "toArea",
    "value",
    "putDamageCounter",
)
PUBLIC_SERIAL_KEYS = frozenset(
    {
        "serial",
        "serialActive",
        "serialBench",
        "serialBefore",
        "serialAfter",
        "serialTarget",
    }
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest().upper()


def _finite_json(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool)):
        return True
    if type(value) is int:
        return True
    if type(value) is float:
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_finite_json(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _finite_json(item)
            for key, item in value.items()
        )
    return False


def _public_pair(value: Any) -> bool:
    return bool(
        isinstance(value, list)
        and len(value) == 2
        and all(item is None or _is_int(item) for item in value)
    )


def _canonical_public_state_material(
    observation: Any,
) -> dict[str, Any] | None:
    if (
        not isinstance(observation, dict)
        or set(observation) != PUBLIC_OBSERVATION_KEYS
        or not _finite_json(observation)
    ):
        return None
    integer_or_none = (
        "turn",
        "turn_action_count",
        "your_index",
        "first_player",
        "result",
        "context",
        "select_type",
        "min_count",
        "max_count",
        "own_active_hp",
        "opponent_active_hp",
    )
    if any(
        observation.get(field) is not None
        and not _is_int(observation.get(field))
        for field in integer_or_none
    ):
        return None
    options = observation.get("options")
    if (
        not _is_int(observation.get("option_count"))
        or observation["option_count"] < 0
        or not isinstance(options, list)
        or observation["option_count"] != len(options)
    ):
        return None
    canonical_options = []
    option_scalar_fields = (
        "type",
        "area",
        "index",
        "player_index",
        "card_id",
        "serial",
        "attack_id",
        "in_play_area",
        "in_play_index",
    )
    for expected_index, option in enumerate(options):
        if (
            not isinstance(option, dict)
            or set(option) != PUBLIC_OPTION_KEYS
            or option.get("option_index") != expected_index
            or any(
                option.get(field) is not None
                and not _is_int(option.get(field))
                for field in option_scalar_fields
            )
            or not isinstance(option.get("raw"), dict)
        ):
            return None
        canonical_options.append(
            {field: option.get(field) for field in option_scalar_fields}
        )
    canonical_options.sort(key=_canonical)
    for field in ("own_active", "opponent_active"):
        value = observation.get(field)
        if value is not None and not _public_pair(value):
            return None
    for field in (
        "own_hand",
        "own_active_energy",
        "own_bench",
        "own_discard",
        "opponent_active_energy",
    ):
        value = observation.get(field)
        if not isinstance(value, list) or any(
            not _public_pair(pair) for pair in value
        ):
            return None
    logs = observation.get("logs_raw")
    serial_rows = observation.get("log_serial_fields")
    if (
        not isinstance(logs, list)
        or not all(isinstance(row, dict) for row in logs)
        or not isinstance(serial_rows, list)
        or not all(
            isinstance(row, dict)
            and bool(row)
            and set(row).issubset(PUBLIC_LOG_SERIAL_FIELDS)
            for row in serial_rows
        )
    ):
        return None
    expected_serial_rows = [
        {
            field: log[field]
            for field in PUBLIC_LOG_SERIAL_FIELDS
            if field in log
        }
        for log in logs
        if any(field in log for field in PUBLIC_SERIAL_KEYS)
    ]
    if serial_rows != expected_serial_rows:
        return None
    return {
        **{
            key: json.loads(_canonical(value))
            for key, value in observation.items()
            if key != "options"
        },
        "options": canonical_options,
    }


def _is_int(value: Any) -> bool:
    return type(value) is int


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and HEX64.fullmatch(value) is not None


def _string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) and item for item in value)
        and len(value) == len(set(value))
    )


def _json_lines(path: Path) -> list[tuple[int, dict[str, Any]]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(
                    f"{path}:{line_number}: JSONL row is not an object"
                )
            rows.append((line_number, value))
    return rows


def _path_identity(suite: Path, path: Path) -> dict[str, Any]:
    relative = path.relative_to(suite)
    parts = relative.parts
    if (
        len(parts) != 7
        or parts[0] != "runs"
        or parts[5] != "sidecars"
        or not parts[1]
        or not parts[2]
        or re.fullmatch(r"seed_(\d+)", parts[3]) is None
        or re.fullmatch(r"seat_([01])", parts[4]) is None
        or re.fullmatch(r"game_(\d+)\.jsonl", parts[6]) is None
    ):
        raise ValueError(f"Unexpected C4 sidecar path: {relative.as_posix()}")
    return {
        "version": parts[1],
        "opponent": parts[2],
        "seed_base": int(parts[3].removeprefix("seed_")),
        "seat": int(parts[4].removeprefix("seat_")),
        "game": int(parts[6][5:-6]),
    }


def _event_identity(
    event: dict[str, Any],
    path_identity: dict[str, Any],
) -> tuple[bool, tuple[Any, ...] | None]:
    required = (
        "version",
        "opponent",
        "policy_seat",
        "seed_base",
        "seed",
        "game",
        "callback_ordinal",
    )
    if any(field not in event for field in required):
        return False, None
    if (
        not isinstance(event["version"], str)
        or not event["version"]
        or not isinstance(event["opponent"], str)
        or not event["opponent"]
        or not all(
            _is_int(event[field])
            for field in (
                "policy_seat",
                "seed_base",
                "seed",
                "game",
                "callback_ordinal",
            )
        )
        or event["policy_seat"] not in (0, 1)
        or event["callback_ordinal"] < 0
    ):
        return False, None
    matches_path = (
        event["version"] == path_identity["version"]
        and event["opponent"] == path_identity["opponent"]
        and event["policy_seat"] == path_identity["seat"]
        and event["seed_base"] == path_identity["seed_base"]
        and event["game"] == path_identity["game"]
    )
    seed_ok = event["seed"] == event["seed_base"] + event["game"]
    key = (
        event["version"],
        event["opponent"],
        event["policy_seat"],
        event["seed_base"],
        event["seed"],
        event["game"],
        event["callback_ordinal"],
    )
    return matches_path and seed_ok, key


def _game_key(callback_key: tuple[Any, ...]) -> tuple[Any, ...]:
    return callback_key[:-1]


def _action_value_valid(value: Any) -> bool:
    return isinstance(value, list) and all(_is_int(item) for item in value)


def _action_faults(
    end: dict[str, Any], trace: dict[str, Any]
) -> dict[str, bool]:
    raw = trace.get("raw_parent_action")
    parent = trace.get("parent_action")
    applied = trace.get("applied_action")
    selected = end.get("selected_action")
    flags = trace.get("action_identity")
    value_ok = (
        all(_action_value_valid(value) for value in (raw, parent, applied, selected))
        and raw == parent == applied == selected
    )
    type_ok = (
        trace.get("action_python_type") == "builtins.list"
        and all(type(value) is list for value in (raw, parent, applied, selected))
    )
    order_ok = (
        isinstance(flags, dict)
        and flags.get("order_equal") is True
        and raw == selected
    )
    self_identity_ok = (
        isinstance(flags, dict)
        and flags.get("value_equal") is True
        and flags.get("type_equal") is True
        and flags.get("returned_parent_object_unchanged") is True
    )
    return {
        "value": value_ok,
        "type": type_ok,
        "order": order_ok,
        "self_identity": self_identity_ok,
    }


def _numeric_vector(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and bool(value)
        and all(
            (type(item) in (int, float)) for item in value.values()
        )
    )


def _supported_envelope(value: Any) -> bool:
    return bool(
        isinstance(value, dict)
        and value.get("status") == "SUPPORTED"
        and value.get("continuity")
        in ("REPEATABLE_READY", "NO_READY_ATTACK")
        and _is_int(value.get("final_safety_cap"))
        and value["final_safety_cap"] >= 0
        and value.get("unsupported_reasons") == []
        and isinstance(value.get("promotion_threats"), list)
    )


def _strict_release_ok(value: Any, *, sacrifice: bool) -> bool:
    if (
        not isinstance(value, dict)
        or value.get("class") != "CERTIFIED"
        or value.get("backup_certified") is not True
        or value.get("prize_exchange_non_worsening") is not True
        or value.get("opponent_continuation")
        not in ("REPEATABLE_READY", "NO_READY_ATTACK")
        or not _is_int(value.get("opponent_safety_cap"))
        or value["opponent_safety_cap"] < 0
    ):
        return False
    target = value.get("release_target")
    envelope = value.get("post_release_opponent_envelope")
    if (
        not isinstance(target, dict)
        or target.get("certified") is not True
        or not _is_int(target.get("attacker_serial"))
        or not _is_int(target.get("attacker_card_id"))
        or not _is_int(target.get("attacker_current_hp"))
        or target["attacker_current_hp"] <= 0
        or not _is_int(target.get("attack_id"))
        or not isinstance(target.get("attack_binding"), str)
        or not target["attack_binding"]
        or not _is_int(target.get("target_prize_value"))
        or target["target_prize_value"] < 0
        or not _supported_envelope(envelope)
    ):
        return False
    if sacrifice:
        immediate = value.get("immediate_opponent_threat")
        return bool(
            value.get("release_mode") == "TRADING_PLACES_POST_ATTACK"
            and value.get("reason")
            == "EXACT_TRADING_POST_ATTACK_SAFE_EXCHANGE"
            and _is_int(value.get("backup_serial"))
            and isinstance(immediate, dict)
            and immediate.get("status") == "SUPPORTED"
            and immediate.get("continuity") == "REPEATABLE_READY"
            and immediate.get("unsupported_reasons") == []
            and _is_int(immediate.get("final_safety_cap"))
            and immediate["final_safety_cap"] >= 0
            and _is_int(target.get("combined_safety_cap"))
            and target["combined_safety_cap"]
            == immediate["final_safety_cap"]
            + envelope["final_safety_cap"]
            == value["opponent_safety_cap"]
            and _is_int(target.get("own_prize_value"))
            and target["target_prize_value"]
            >= target["own_prize_value"]
        )
    return bool(
        value.get("reason") == "EXACT_SAFE_RELEASE_AND_EXCHANGE"
        and value["opponent_safety_cap"] == envelope["final_safety_cap"]
    )


def _strict_run_metrics_ok(metrics: dict[str, Any]) -> bool:
    count = metrics.get("certified_draw_count")
    delta = metrics.get("certified_draw_damage_delta")
    conversion = metrics.get("conversion")
    if (
        not _is_int(count)
        or count < 1
        or count > 3
        or not _is_int(delta)
        or delta != 20 * count
        or metrics.get("drawn_card_identities") != "POSSIBLE"
        or not isinstance(conversion, dict)
        or not _is_int(conversion.get("promotion_serial"))
        or not _is_int(conversion.get("damage"))
        or conversion["damage"] < 0
        or conversion.get("ko") is not True
        or type(conversion.get("terminal_win")) is not bool
        or type(conversion.get("safe_prize_exchange")) is not bool
        or not _is_int(conversion.get("attack_id"))
        or not isinstance(conversion.get("attack_binding"), str)
        or not _is_int(conversion.get("target_serial"))
        or not _is_int(conversion.get("target_prize_value"))
    ):
        return False
    label = conversion.get("conversion")
    if label == "TERMINAL_WIN":
        return conversion["terminal_win"] is True
    if label == "CURRENT_REPEATABLE_THREAT_KO":
        return conversion["terminal_win"] is False
    if label == "EXACT_SAFE_PRIZE_EXCHANGE":
        return bool(
            conversion["safe_prize_exchange"] is True
            and _is_int(conversion.get("distinct_backup_serial"))
            and _supported_envelope(
                conversion.get("post_release_opponent_envelope")
            )
        )
    return False


def _strict_wall_metrics_ok(
    row: dict[str, Any], expected_kind: str
) -> bool:
    metrics = row.get("metrics")
    wall = row.get("wall")
    if not isinstance(metrics, dict) or not isinstance(wall, dict):
        return False
    if expected_kind == "RUN_AWAY_ACCELERATION":
        return (
            wall.get("card_id") == 66
            and _strict_run_metrics_ok(metrics)
        )
    hold_turns = metrics.get("hold_turns")
    entry = metrics.get("hold_entry_turn")
    deadline = metrics.get("hold_deadline")
    remaining = metrics.get("remaining_hp")
    cap = metrics.get("final_safety_cap")
    margin = metrics.get("survival_margin")
    reusable = expected_kind == "CERTIFIED_REUSABLE_WALL"
    if (
        metrics.get("protected_readiness") != "CERTIFIED"
        or not _is_int(hold_turns)
        or hold_turns <= 0
        or not _is_int(entry)
        or not _is_int(deadline)
        or deadline != entry + hold_turns
        or not _is_int(metrics.get("gust_exposure"))
        or metrics["gust_exposure"] != hold_turns
        or not _is_int(metrics.get("resource_loss"))
        or metrics["resource_loss"] < 0
        or not _is_int(metrics.get("lost_draw3"))
        or metrics.get("final_prize_outcome") is not False
        or not _is_int(remaining)
        or remaining <= 0
        or not _is_int(cap)
        or cap < 0
        or not _is_int(margin)
        or margin != remaining - cap
        or not _strict_release_ok(
            metrics.get("safe_release"), sacrifice=not reusable
        )
    ):
        return False
    if reusable:
        return bool(
            wall.get("card_id") == 66
            and metrics.get("own_prize_loss") == 0
            and metrics.get("lost_draw3") == 3
            and remaining > cap
        )
    return bool(
        wall.get("card_id") == 305
        and metrics.get("own_prize_loss") == 1
        and metrics.get("lost_draw3") == 0
    )


def _row_schema_ok(
    row: Any,
    expected_kind: str,
    decision_point: Any,
) -> bool:
    if (
        not isinstance(row, dict)
        or not ROW_REQUIRED.issubset(row)
        or row.get("kind") != expected_kind
        or not _string_list(row.get("rejection_codes"))
        or not _string_list(row.get("unsupported_reasons"))
        or not _string_list(row.get("structural_reasons"))
        or not isinstance(row.get("metrics"), dict)
    ):
        return False
    certification = row.get("certification")
    wall_class = row.get("wall_class")
    if certification not in (
        "STRICT",
        "PRESERVE_CHANCE",
        "REJECTED",
        "UNAVAILABLE",
        "AVAILABLE",
    ):
        return False
    if expected_kind == "NO_WALL_OR_UNKNOWN":
        if decision_point is None:
            return (
                certification == "UNAVAILABLE"
                and wall_class == "REJECTED"
                and row.get("legality") == "UNAVAILABLE"
                and row.get("option_index") is None
                and row.get("semantic_action_key") is None
                and row.get("wall") is None
                and row.get("rejection_codes") == []
                and row.get("unsupported_reasons") == []
                and row.get("structural_reasons") == []
                and row.get("metrics") == {}
                and row.get("pareto_vector") is None
            )
        return (
            certification == "AVAILABLE"
            and wall_class == "PARENT_FALLBACK"
            and row.get("option_index") is None
            and row.get("wall") is None
        )
    if certification in ("STRICT", "PRESERVE_CHANCE"):
        if (
            row.get("decision_point") != decision_point
            or row.get("legality") != "EXACT"
            or not _is_int(row.get("option_index"))
            or not isinstance(row.get("semantic_action_key"), dict)
            or not isinstance(row.get("wall"), dict)
            or not _is_int(row["wall"].get("serial"))
            or not _is_int(row["wall"].get("card_id"))
        ):
            return False
        if certification == "STRICT" and (
            wall_class != STRICT
            or row["rejection_codes"]
            or row["unsupported_reasons"]
            or row["structural_reasons"]
            or not _strict_wall_metrics_ok(row, expected_kind)
        ):
            return False
        if certification == "PRESERVE_CHANCE" and wall_class != CHANCE:
            return False
        required_metrics = (
            RUN_METRICS
            if expected_kind == "RUN_AWAY_ACCELERATION"
            else WALL_METRICS
        )
        if not required_metrics.issubset(row["metrics"]):
            return False
        if (
            expected_kind != "RUN_AWAY_ACCELERATION"
            and not _numeric_vector(row.get("pareto_vector"))
        ):
            return False
    elif certification == "REJECTED":
        if wall_class != "REJECTED" or not row["rejection_codes"]:
            return False
    elif certification == "UNAVAILABLE":
        if row.get("legality") != "UNAVAILABLE":
            return False
    else:
        return False
    return True


def _pair_and_projection_ok(trace: dict[str, Any]) -> bool:
    public_material = trace.get("public_state_material")
    option_keys = trace.get("semantic_option_keys")
    pair_material = trace.get("pair_material")
    wall_projection = trace.get("wall_projection")
    expose_projection = trace.get("expose_projection")
    protected = trace.get("protected_line")
    if (
        not isinstance(public_material, dict)
        or not isinstance(option_keys, list)
        or any(not isinstance(key, dict) for key in option_keys)
        or option_keys
        != sorted(option_keys, key=_canonical)
        or len({_canonical(key) for key in option_keys}) != len(option_keys)
        or trace.get("public_state_fingerprint")
        != _fingerprint(public_material)
        or not isinstance(expose_projection, dict)
        or trace.get("expose_state_fingerprint")
        != _fingerprint(expose_projection)
        or not isinstance(wall_projection, dict)
        or trace.get("wall_state_fingerprint")
        != _fingerprint(wall_projection)
        or not isinstance(protected, dict)
        or not isinstance(pair_material, dict)
    ):
        return False
    alternatives = wall_projection.get("alternatives")
    if not isinstance(alternatives, list):
        return False
    wall_serials = sorted(
        alternative.get("wall", {}).get("serial")
        for alternative in alternatives
        if isinstance(alternative, dict)
        and isinstance(alternative.get("wall"), dict)
        and _is_int(alternative["wall"].get("serial"))
    )
    expected = {
        "public_state_fingerprint": trace["public_state_fingerprint"],
        "decision_point": trace.get("decision_point"),
        "semantic_action_keys": option_keys,
        "protected_serial": protected.get("top_serial"),
        "wall_serials": wall_serials,
    }
    chosen = wall_projection.get("chosen")
    if chosen is not None and (
        not isinstance(chosen, dict)
        or trace.get("bypass") != chosen.get("bypass")
    ):
        return False
    return bool(
        pair_material == expected
        and trace.get("pair_id") == _fingerprint(expected)
        and trace.get("parent_post_fingerprint")
        == trace.get("expose_state_fingerprint")
        and trace.get("candidate_post_fingerprint")
        == trace.get("wall_state_fingerprint")
    )


def _chosen_trace_semantics_ok(trace: dict[str, Any]) -> bool:
    if trace.get("outcome_status") != "PARENT_AGREEMENT":
        return True
    parent = trace.get("semantic_parent_action_keys")
    proposed = trace.get("semantic_proposed_action_keys")
    chosen = _chosen_mechanism(trace)
    if (
        not isinstance(parent, list)
        or len(parent) != 1
        or proposed != parent
        or chosen is None
        or chosen.get("semantic_action_key") != parent[0]
        or trace.get("wall_class") != chosen.get("wall_class")
    ):
        return False
    metrics = chosen.get("metrics") or {}
    if chosen.get("kind") == "RUN_AWAY_ACCELERATION":
        return bool(
            trace.get("certified_draw_count")
            == metrics.get("certified_draw_count")
            and trace.get("certified_draw_damage_delta")
            == metrics.get("certified_draw_damage_delta")
        )
    return bool(
        trace.get("safe_release") == metrics.get("safe_release")
        and trace.get("hold_entry_turn")
        == metrics.get("hold_entry_turn")
        and trace.get("hold_deadline") == metrics.get("hold_deadline")
        and trace.get("gust_exposure_turns")
        == metrics.get("gust_exposure")
        and trace.get("refusal_progress") == "CERTIFIED"
    )


def _trace_schema_faults(
    trace: Any,
    expected_candidate_closure: str,
    raw_public_material: dict[str, Any] | None,
) -> dict[str, bool]:
    faults = {
        "schema": False,
        "rule": False,
        "parent_closure": False,
        "candidate_closure": False,
        "analyzer": False,
        "sparse": False,
        "raw_state": False,
    }
    if not isinstance(trace, dict):
        faults["schema"] = True
        faults["sparse"] = True
        return faults
    faults["sparse"] = not TRACE_REQUIRED.issubset(trace)
    faults["schema"] = (
        trace.get("schema_version") != SCHEMA_VERSION
        or not isinstance(trace.get("state_machine"), list)
        or not _string_list(trace.get("rejection_codes"))
        or not _string_list(trace.get("unsupported_reasons"))
        or not _string_list(trace.get("structural_reasons"))
        or trace.get("outcome_status")
        not in ("PARENT_AGREEMENT", "COUNTERFACTUAL_UNOBSERVED")
        or not isinstance(trace.get("outcome_events"), list)
    )
    faults["rule"] = trace.get("rule_version") != RULE_VERSION
    faults["parent_closure"] = (
        trace.get("parent_closure_sha256") != PARENT_CLOSURE_SHA256
    )
    faults["candidate_closure"] = (
        trace.get("candidate_closure_sha256")
        != expected_candidate_closure
    )
    faults["analyzer"] = (
        trace.get("analyzer_component_sha256") != ANALYZER_SHA256
    )
    faults["raw_state"] = bool(
        raw_public_material is None
        or trace.get("public_state_material") != raw_public_material
        or trace.get("public_state_fingerprint")
        != _fingerprint(raw_public_material)
    )
    rows = trace.get("candidate_rows")
    if (
        not isinstance(rows, list)
        or len(rows) != 4
        or any(
            not _row_schema_ok(row, kind, trace.get("decision_point"))
            for row, kind in zip(rows, CANDIDATE_KINDS)
        )
    ):
        faults["sparse"] = True
    is_decision = trace.get("decision_point") is not None
    if is_decision and (
        not _is_hex64(trace.get("pair_id"))
        or not _is_hex64(trace.get("decision_id"))
        or not _is_hex64(trace.get("public_state_fingerprint"))
        or not _is_hex64(trace.get("game_boundary_fingerprint"))
        or not _is_hex64(trace.get("expose_state_fingerprint"))
        or not _is_hex64(trace.get("wall_state_fingerprint"))
        or not isinstance(trace.get("protected_line"), dict)
        or trace.get("importance")
        not in ("UNIQUE", "IMPORTANT", "REDUNDANT", "UNKNOWN_IMPORTANCE")
        or not _pair_and_projection_ok(trace)
        or not _chosen_trace_semantics_ok(trace)
    ):
        faults["sparse"] = True
    return faults


def _decision_class(trace: dict[str, Any]) -> str | None:
    rows = trace.get("candidate_rows")
    if not isinstance(rows, list):
        return None
    if any(
        isinstance(row, dict) and row.get("certification") == "STRICT"
        for row in rows
    ):
        return "STRICT"
    if any(
        isinstance(row, dict)
        and row.get("certification") == "PRESERVE_CHANCE"
        for row in rows
    ):
        return "PRESERVE_CHANCE"
    return None


def _state_evidence(trace: dict[str, Any]) -> str:
    return _canonical(
        {
            "decision_point": trace.get("decision_point"),
            "public_state_fingerprint": trace.get("public_state_fingerprint"),
            "semantic_parent_action_keys": trace.get(
                "semantic_parent_action_keys"
            ),
            "protected_line": trace.get("protected_line"),
            "importance": trace.get("importance"),
            "expose_state_fingerprint": trace.get(
                "expose_state_fingerprint"
            ),
            "wall_state_fingerprint": trace.get("wall_state_fingerprint"),
            "candidate_rows": trace.get("candidate_rows"),
            "arbitration_reason": trace.get("arbitration_reason"),
        }
    )


def _chosen_mechanism(trace: dict[str, Any]) -> dict[str, Any] | None:
    proposed = trace.get("semantic_proposed_action_keys")
    if not isinstance(proposed, list) or len(proposed) != 1:
        return None
    matches = [
        row
        for row in (trace.get("candidate_rows") or [])
        if isinstance(row, dict)
        and row.get("kind") != "NO_WALL_OR_UNKNOWN"
        and row.get("semantic_action_key") == proposed[0]
        and row.get("certification") == "STRICT"
    ]
    return matches[0] if len(matches) == 1 else None


def _complete_outcome(
    decision: dict[str, Any],
    events: list[dict[str, Any]],
) -> bool:
    kinds = {
        event.get("event") for event in events if isinstance(event, dict)
    }
    if (
        "PARENT_AGREEMENT" not in kinds
        or kinds & {"GUST_OR_SNIPE_BYPASS", "CANDIDATE_APPLIED"}
    ):
        return False
    mechanism = decision.get("mechanism")
    row = decision.get("row")
    if mechanism not in CANDIDATE_KINDS[:3] or not isinstance(row, dict):
        return False
    terminal = any(
        event.get("event") == "GAME_END"
        and _is_int(event.get("result"))
        and event["result"] in (0, 1)
        for event in events
        if isinstance(event, dict)
    )
    progress = bool(
        kinds & {"PROTECTED_LINE_PROGRESS", "DISTANCE_IMPROVED"}
    )
    protected_promotion = any(
        event.get("event") == "PROMOTION_DESTINATION"
        and event.get("protected_destination") is True
        for event in events
        if isinstance(event, dict)
    )
    if mechanism == "RUN_AWAY_ACCELERATION":
        conversion = (row.get("metrics") or {}).get("conversion")
        ready = (
            isinstance(conversion, dict)
            and conversion.get("attack_binding") is not None
            and conversion.get("ko") is True
        )
        return (
            "RUN_AWAY_RELEASED" in kinds
            and protected_promotion
            and (progress or ready)
            and "PROTECTED_ATTACKER_ATTACKED" in kinds
            and (terminal or "OPPONENT_CONTINUITY_OBSERVED" in kinds)
        )
    safe_release = (row.get("metrics") or {}).get("safe_release")
    if (
        not isinstance(safe_release, dict)
        or safe_release.get("class") != "CERTIFIED"
        or safe_release.get("prize_exchange_non_worsening") is not True
    ):
        return False
    release_kind = (
        "RUN_AWAY_RELEASED"
        if mechanism == "CERTIFIED_REUSABLE_WALL"
        else "TRADING_PLACES_RELEASED"
    )
    wall_path = (
        "WALL_ACTIVE" in kinds
        and bool(kinds & {"WALL_ATTACKED", "OPPONENT_REFUSED"})
        and bool(kinds & {"WALL_SURVIVED", "WALL_KO"})
    )
    post_release = (
        release_kind in kinds
        and protected_promotion
        and "PROTECTED_ATTACKER_ATTACKED" in kinds
        and (terminal or "OPPONENT_CONTINUITY_OBSERVED" in kinds)
    )
    return wall_path and progress and post_release


def _outcome_semantics(
    decision: dict[str, Any],
    events: list[dict[str, Any]],
) -> tuple[bool, set[str]]:
    row = decision.get("row")
    if not isinstance(row, dict):
        return False, set()
    wall = row.get("wall")
    wall_serial = (
        wall.get("serial") if isinstance(wall, dict) else None
    )
    if not _is_int(wall_serial):
        return False, set()
    decision_ids = {
        event.get("decision_id")
        for event in events
        if isinstance(event, dict)
    }
    if (
        len(decision_ids) != 1
        or any(
            not isinstance(event, dict)
            or event.get("event") not in OUTCOME_EVENT_TYPES
            or not _is_int(event.get("turn"))
            or event["turn"] < 0
            for event in events
        )
    ):
        return False, set()
    wall_events = {
        "WALL_ACTIVE",
        "WALL_ATTACKED",
        "WALL_SURVIVED",
        "WALL_KO",
        "OPPONENT_REFUSED",
    }
    release_events = {"RUN_AWAY_RELEASED", "TRADING_PLACES_RELEASED"}
    for event in events:
        kind = event["event"]
        if kind in wall_events and event.get("wall_serial") != wall_serial:
            return False, set()
        if kind in release_events and event.get("source_serial") != wall_serial:
            return False, set()
        if kind == "PROMOTION_DESTINATION" and (
            not _is_int(event.get("destination_serial"))
            or not _is_int(event.get("destination_card_id"))
            or type(event.get("protected_destination")) is not bool
        ):
            return False, set()
        if kind == "PROTECTED_ATTACKER_ATTACKED" and (
            not _is_int(event.get("attacker_serial"))
            or not _is_int(event.get("attack_id"))
        ):
            return False, set()
        if kind == "OPPONENT_CONTINUITY_OBSERVED" and not _is_int(
            event.get("attacker_serial")
        ):
            return False, set()
        if kind == "GAME_END" and (
            not _is_int(event.get("result"))
            or event["result"] not in (0, 1)
        ):
            return False, set()
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_kind[event["event"]].append(event)
    if len(by_kind["PARENT_AGREEMENT"]) != 1:
        return False, set()
    entry_turn = by_kind["PARENT_AGREEMENT"][0]["turn"]
    if any(event["turn"] < entry_turn for event in events):
        return False, set()
    release_turns = sorted(
        event["turn"]
        for kind in release_events
        for event in by_kind[kind]
    )
    promotion_turns = sorted(
        event["turn"] for event in by_kind["PROMOTION_DESTINATION"]
    )
    attack_turns = sorted(
        event["turn"] for event in by_kind["PROTECTED_ATTACKER_ATTACKED"]
    )
    continuity_turns = sorted(
        event["turn"] for event in by_kind["OPPONENT_CONTINUITY_OBSERVED"]
    )
    if (
        promotion_turns
        and (not release_turns or promotion_turns[0] < release_turns[0])
    ) or (
        attack_turns
        and (not promotion_turns or attack_turns[0] < promotion_turns[0])
    ) or (
        continuity_turns
        and (not attack_turns or continuity_turns[0] < attack_turns[0])
    ):
        return False, set()

    counterexamples = set()
    if by_kind["GUST_OR_SNIPE_BYPASS"]:
        counterexamples.add("GUST_OR_SNIPE_BYPASS")
    progress_turns = sorted(
        event["turn"]
        for kind in ("PROTECTED_LINE_PROGRESS", "DISTANCE_IMPROVED")
        for event in by_kind[kind]
    )
    if any(
        not any(turn >= refusal["turn"] for turn in progress_turns)
        for refusal in by_kind["OPPONENT_REFUSED"]
    ):
        counterexamples.add("REFUSAL_WITHOUT_PROGRESS")
    if any(
        event.get("protected_destination") is False
        for event in by_kind["PROMOTION_DESTINATION"]
    ):
        counterexamples.add("UNSAFE_RELEASE_DESTINATION")
    closed_turns = sorted(
        event["turn"]
        for kind in ("GAME_END", "TRUNCATION")
        for event in by_kind[kind]
    )
    if (
        release_turns
        and promotion_turns
        and closed_turns
        and closed_turns[-1] >= promotion_turns[0]
        and not any(turn >= promotion_turns[0] for turn in attack_turns)
    ):
        counterexamples.add("PROTECTED_NOT_READY_AFTER_RELEASE")
    safe_release = (row.get("metrics") or {}).get("safe_release")
    expected_continuity = (
        safe_release.get("opponent_continuation")
        if isinstance(safe_release, dict)
        else None
    )
    if (
        expected_continuity == "REPEATABLE_READY"
        and attack_turns
        and closed_turns
        and closed_turns[-1] >= attack_turns[0]
        and not any(turn >= attack_turns[0] for turn in continuity_turns)
    ):
        counterexamples.add("OPPONENT_CONTINUITY_FAILURE")
    return True, counterexamples


def _normalize_suites(
    suite_dirs: Path | Iterable[Path],
) -> list[Path]:
    if isinstance(suite_dirs, (str, Path)):
        values = [Path(suite_dirs)]
    else:
        values = [Path(path) for path in suite_dirs]
    if not values:
        raise ValueError("At least one suite directory is required")
    resolved = [path.resolve() for path in values]
    if len(resolved) != len(set(resolved)):
        raise ValueError("Duplicate suite directory input")
    return sorted(resolved, key=lambda path: (path.name, str(path)))


def collect_suite(
    suite_dirs: Path | Iterable[Path],
    *,
    expected_candidate_closure: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not _is_hex64(expected_candidate_closure):
        raise ValueError("A required uppercase 64-hex candidate closure is invalid")
    suites = _normalize_suites(suite_dirs)
    callback_rows = []
    manifest = []
    counts: Counter[str] = Counter()
    global_starts: Counter[tuple[Any, ...]] = Counter()
    global_ends: Counter[tuple[Any, ...]] = Counter()
    pair_evidence: dict[str, set[str]] = defaultdict(set)
    evidence_pairs: dict[str, set[str]] = defaultdict(set)
    raw_state_pairs: dict[str, set[str]] = defaultdict(set)
    pair_classes: dict[str, set[str]] = defaultdict(set)
    pair_games: dict[str, set[tuple[Any, ...]]] = defaultdict(set)
    pair_opponents: dict[str, set[str]] = defaultdict(set)
    pair_seats: dict[str, set[int]] = defaultdict(set)
    decision_bindings: dict[
        tuple[tuple[Any, ...], str], set[tuple[str, str]]
    ] = defaultdict(set)
    decisions: dict[tuple[tuple[Any, ...], str], dict[str, Any]] = {}
    outcome_events: dict[
        tuple[tuple[Any, ...], str], dict[str, dict[str, Any]]
    ] = defaultdict(dict)
    candidate_closures = set()
    observed_counterexamples: set[
        tuple[tuple[tuple[Any, ...], str], str]
    ] = set()
    callbacks_by_opponent: Counter[str] = Counter()
    callbacks_by_seat: Counter[int] = Counter()
    suite_file_counts = {}

    for suite_index, suite in enumerate(suites):
        suite_alias = f"suite_{suite_index:03d}_{suite.name}"
        sidecars = sorted(suite.glob(SIDECAR_GLOB))
        suite_file_counts[suite_alias] = len(sidecars)
        if not sidecars:
            counts["empty_suite"] += 1
            continue
        for sidecar in sidecars:
            try:
                identity = _path_identity(suite, sidecar)
                source_rows = _json_lines(sidecar)
            except (ValueError, json.JSONDecodeError):
                counts["sidecar_parse_or_path"] += 1
                continue
            portable_path = f"{suite_alias}/{sidecar.relative_to(suite).as_posix()}"
            file_hash = _sha256(sidecar)
            manifest.append(
                {
                    "path": portable_path,
                    "sha256": file_hash,
                    "bytes": sidecar.stat().st_size,
                    "jsonl_rows": len(source_rows),
                }
            )
            if not source_rows:
                counts["empty_sidecar"] += 1
                continue
            open_local: dict[
                tuple[Any, ...], tuple[int, dict[str, Any] | None]
            ] = {}
            ended_local = set()
            current_open: tuple[Any, ...] | None = None
            expected_ordinal = 0
            for line_number, event in source_rows:
                kind = event.get("event")
                if kind not in ("CALL_START", "CALL_END"):
                    counts["unknown_event"] += 1
                    continue
                identity_ok, callback_key = _event_identity(event, identity)
                if not identity_ok or callback_key is None:
                    counts["identity"] += 1
                    continue
                game_key = _game_key(callback_key)
                if kind == "CALL_START":
                    global_starts[callback_key] += 1
                    if (
                        callback_key in open_local
                        or callback_key in ended_local
                        or current_open is not None
                        or event["callback_ordinal"] != expected_ordinal
                    ):
                        counts["end_order"] += 1
                    else:
                        raw_public_material = (
                            _canonical_public_state_material(
                                event.get("observation")
                            )
                        )
                        if (
                            raw_public_material is not None
                            and raw_public_material.get("your_index")
                            != event["policy_seat"]
                        ):
                            raw_public_material = None
                        open_local[callback_key] = (
                            line_number,
                            raw_public_material,
                        )
                        current_open = callback_key
                    continue

                global_ends[callback_key] += 1
                raw_public_material = None
                if (
                    callback_key not in open_local
                    or current_open != callback_key
                ):
                    counts["end_order"] += 1
                else:
                    start_line, raw_public_material = open_local[callback_key]
                    if start_line >= line_number:
                        counts["end_order"] += 1
                    open_local.pop(callback_key, None)
                    ended_local.add(callback_key)
                    current_open = None
                    expected_ordinal += 1
                callbacks_by_opponent[event["opponent"]] += 1
                callbacks_by_seat[event["policy_seat"]] += 1
                if event.get("structurally_valid") is not True:
                    counts["structural"] += 1
                if event.get("exception") is not None:
                    counts["wrapper"] += 1
                trace = event.get("version_trace")
                if (
                    event.get("version_trace_name")
                    != "LAST_STAGED_POLICY_TRACE"
                    or not isinstance(trace, dict)
                ):
                    counts["schema"] += 1
                    continue
                schema_faults = _trace_schema_faults(
                    trace,
                    expected_candidate_closure,
                    raw_public_material,
                )
                for fault, present in schema_faults.items():
                    if present:
                        counts[fault] += 1
                closure = trace.get("candidate_closure_sha256")
                if isinstance(closure, str):
                    candidate_closures.add(closure)
                action_faults = _action_faults(event, trace)
                for fault, passed in action_faults.items():
                    if not passed:
                        counts[f"action_{fault}"] += 1
                if trace.get("metric_exception") is not None:
                    counts["metric"] += 1
                events = trace.get("outcome_events")
                if not isinstance(events, list):
                    events = []
                if (
                    trace.get("outcome_status") == "CANDIDATE_APPLIED"
                    or any(
                        isinstance(row, dict)
                        and row.get("event") == "CANDIDATE_APPLIED"
                        for row in events
                    )
                ):
                    counts["candidate_applied"] += 1

                trace_valid = not any(schema_faults.values()) and all(
                    action_faults.values()
                )
                pair_id = trace.get("pair_id")
                decision_id = trace.get("decision_id")
                decision_class = _decision_class(trace)
                if (
                    trace_valid
                    and _is_hex64(pair_id)
                    and _is_hex64(decision_id)
                    and decision_class is not None
                ):
                    evidence = _state_evidence(trace)
                    pair_evidence[pair_id].add(evidence)
                    evidence_pairs[evidence].add(pair_id)
                    raw_state_pairs[_canonical(raw_public_material)].add(
                        pair_id
                    )
                    pair_classes[pair_id].add(decision_class)
                    pair_games[pair_id].add(game_key)
                    pair_opponents[pair_id].add(event["opponent"])
                    pair_seats[pair_id].add(event["policy_seat"])
                    decision_key = (game_key, decision_id)
                    decision_bindings[decision_key].add(
                        (pair_id, evidence)
                    )
                    chosen = _chosen_mechanism(trace)
                    if (
                        trace.get("outcome_status") == "PARENT_AGREEMENT"
                        and chosen is not None
                    ):
                        decisions[decision_key] = {
                            "pair_id": pair_id,
                            "mechanism": chosen["kind"],
                            "row": chosen,
                            "opponent": event["opponent"],
                            "seat": event["policy_seat"],
                        }
                for outcome in events:
                    if not isinstance(outcome, dict):
                        counts["outcome_identity"] += 1
                        continue
                    outcome_id = outcome.get("decision_id")
                    if not _is_hex64(outcome_id):
                        counts["outcome_identity"] += 1
                        continue
                    outcome_key = (game_key, outcome_id)
                    outcome_events[outcome_key][_canonical(outcome)] = outcome
                callback_rows.append(
                    {
                        "source_file": portable_path,
                        "source_sha256": file_hash,
                        "source_line": line_number,
                        "version": event["version"],
                        "opponent": event["opponent"],
                        "seat": event["policy_seat"],
                        "seed_base": event["seed_base"],
                        "seed": event["seed"],
                        "game": event["game"],
                        "callback_ordinal": event["callback_ordinal"],
                        "pair_id": pair_id,
                        "decision_id": decision_id,
                        "decision_class": decision_class,
                        "action_identity_ok": all(action_faults.values()),
                        "metric_exception": trace.get("metric_exception"),
                    }
                )
            if open_local:
                counts["unmatched_start_local"] += len(open_local)
            local_start_count = sum(
                1 for _, row in source_rows if row.get("event") == "CALL_START"
            )
            local_end_count = sum(
                1 for _, row in source_rows if row.get("event") == "CALL_END"
            )
            if local_start_count == 0 or local_end_count == 0:
                counts["empty_call_sidecar"] += 1
            if local_start_count != local_end_count:
                counts["local_pair_count"] += abs(
                    local_start_count - local_end_count
                )

    all_callback_keys = set(global_starts) | set(global_ends)
    unmatched_starts = sum(
        max(0, global_starts[key] - global_ends[key])
        for key in all_callback_keys
    )
    unmatched_ends = sum(
        max(0, global_ends[key] - global_starts[key])
        for key in all_callback_keys
    )
    global_duplicates = sum(
        max(0, global_starts[key] - 1)
        + max(0, global_ends[key] - 1)
        for key in all_callback_keys
    )
    pair_conflicts = sum(
        1
        for pair_id in pair_evidence
        if len(pair_evidence[pair_id]) != 1
        or len(pair_classes[pair_id]) != 1
    )
    reverse_pair_conflicts = sum(
        1 for pair_ids in evidence_pairs.values() if len(pair_ids) != 1
    )
    raw_pair_conflicts = sum(
        1 for pair_ids in raw_state_pairs.values() if len(pair_ids) != 1
    )
    decision_conflicts = sum(
        1 for bindings in decision_bindings.values() if len(bindings) != 1
    )
    counts["state_conflict"] += (
        pair_conflicts
        + reverse_pair_conflicts
        + raw_pair_conflicts
        + decision_conflicts
    )

    natural_agreements = set()
    complete_outcomes = set()
    for outcome_key, event_map in outcome_events.items():
        decision = decisions.get(outcome_key)
        if decision is None:
            counts["orphan_outcome"] += 1
            continue
        events = list(event_map.values())
        outcome_valid, counterexamples = _outcome_semantics(
            decision, events
        )
        if not outcome_valid:
            counts["outcome_semantic"] += 1
            continue
        observed_counterexamples.update(
            (outcome_key, counterexample)
            for counterexample in counterexamples
        )
        if any(row.get("event") == "PARENT_AGREEMENT" for row in events):
            natural_agreements.add(outcome_key)
        if _complete_outcome(decision, events):
            complete_outcomes.add(outcome_key)

    valid_pairs = {
        pair_id
        for pair_id in pair_classes
        if len(pair_classes[pair_id]) == 1
        and len(pair_evidence[pair_id]) == 1
    }
    strict_pairs = {
        pair_id
        for pair_id in valid_pairs
        if pair_classes[pair_id] == {"STRICT"}
    }
    chance_pairs = {
        pair_id
        for pair_id in valid_pairs
        if pair_classes[pair_id] == {"PRESERVE_CHANCE"}
    }
    decision_opponents = {
        opponent
        for pair_id in valid_pairs
        for opponent in pair_opponents[pair_id]
    }
    decision_seats = {
        seat
        for pair_id in valid_pairs
        for seat in pair_seats[pair_id]
    }
    non_mirror = {
        opponent
        for opponent in decision_opponents
        if "mirror" not in opponent.lower()
        and "alakazam" not in opponent.lower()
    }
    strict_buckets = {
        opponent
        for pair_id in strict_pairs
        for opponent in pair_opponents[pair_id]
    }
    reach_checks = {
        "strict_states": len(strict_pairs) >= 24,
        "chance_states": len(chance_pairs) >= 40,
        "both_seats": len(decision_seats) >= 2,
        "three_opponents": len(decision_opponents) >= 3,
        "two_non_mirror": len(non_mirror) >= 2,
        "two_strict_buckets": len(strict_buckets) >= 2,
        "natural_agreements": len(natural_agreements) >= 12,
        "complete_outcomes": len(complete_outcomes) >= 8,
        "no_counterexamples": not observed_counterexamples,
    }
    integrity_fault_keys = (
        "empty_suite",
        "sidecar_parse_or_path",
        "empty_sidecar",
        "unknown_event",
        "identity",
        "end_order",
        "structural",
        "wrapper",
        "schema",
        "rule",
        "parent_closure",
        "candidate_closure",
        "analyzer",
        "sparse",
        "raw_state",
        "action_value",
        "action_type",
        "action_order",
        "action_self_identity",
        "metric",
        "candidate_applied",
        "outcome_identity",
        "unmatched_start_local",
        "empty_call_sidecar",
        "local_pair_count",
        "state_conflict",
        "orphan_outcome",
        "outcome_semantic",
    )
    integrity_ok = (
        all(counts[key] == 0 for key in integrity_fault_keys)
        and unmatched_starts == 0
        and unmatched_ends == 0
        and global_duplicates == 0
        and candidate_closures == {expected_candidate_closure}
    )
    reach_ok = all(reach_checks.values())
    overall = (
        "FAIL"
        if not integrity_ok
        else "PASS"
        if reach_ok
        else "INSUFFICIENT_EVIDENCE"
    )
    manifest.sort(key=lambda row: row["path"])
    manifest_material = "".join(
        f"{row['path']}\0{row['sha256']}\0{row['bytes']}\n"
        for row in manifest
    ).encode("utf-8")
    callback_rows.sort(
        key=lambda row: (
            row["version"],
            row["opponent"],
            row["seat"],
            row["seed"],
            row["game"],
            row["callback_ordinal"],
            row["source_file"],
        )
    )
    summary = {
        "schema_version": "c4-wall-shadow-sidecar-coverage-v2",
        "rule_version": RULE_VERSION,
        "suite_count": len(suites),
        "suite_file_counts": suite_file_counts,
        "input_file_count": len(manifest),
        "input_manifest_sha256": hashlib.sha256(
            manifest_material
        ).hexdigest().upper(),
        "input_files": manifest,
        "callback_start_count": sum(global_starts.values()),
        "callback_end_count": sum(global_ends.values()),
        "unique_callback_key_count": len(all_callback_keys),
        "unmatched_callback_start_count": unmatched_starts,
        "unmatched_callback_end_count": unmatched_ends,
        "duplicate_callback_key_count": global_duplicates,
        "callback_game_identity_fault_count": counts["identity"],
        "callback_end_order_fault_count": counts["end_order"],
        "schema_fault_count": counts["schema"],
        "rule_fault_count": counts["rule"],
        "parent_closure_fault_count": counts["parent_closure"],
        "candidate_closure_fault_count": counts["candidate_closure"],
        "analyzer_hash_fault_count": counts["analyzer"],
        "sparse_trace_or_row_fault_count": counts["sparse"],
        "raw_public_state_binding_fault_count": counts["raw_state"],
        "schema_rule_closure_fault_count": sum(
            counts[key]
            for key in (
                "schema",
                "rule",
                "parent_closure",
                "candidate_closure",
                "analyzer",
                "sparse",
                "raw_state",
            )
        ),
        "candidate_closures": sorted(candidate_closures),
        "action_value_failure_count": counts["action_value"],
        "action_type_failure_count": counts["action_type"],
        "action_order_failure_count": counts["action_order"],
        "action_self_identity_claim_failure_count": counts[
            "action_self_identity"
        ],
        "action_identity_failure_count": sum(
            counts[key]
            for key in (
                "action_value",
                "action_type",
                "action_order",
                "action_self_identity",
            )
        ),
        "candidate_applied_count": counts["candidate_applied"],
        "metric_exception_count": counts["metric"],
        "structural_invalid_count": counts["structural"],
        "wrapper_exception_count": counts["wrapper"],
        "state_evidence_conflict_count": counts["state_conflict"],
        "outcome_identity_fault_count": counts["outcome_identity"],
        "orphan_outcome_event_group_count": counts["orphan_outcome"],
        "outcome_semantic_fault_count": counts["outcome_semantic"],
        "observed_counterexample_count": len(observed_counterexamples),
        "observed_counterexamples": sorted(
            {
                label
                for _, label in observed_counterexamples
            }
        ),
        "unique_pair_state_count": len(valid_pairs),
        "unique_decision_count": len(decision_bindings),
        "same_pair_additional_game_count": sum(
            max(0, len(games) - 1) for games in pair_games.values()
        ),
        "strict_unique_state_count": len(strict_pairs),
        "preserve_chance_unique_state_count": len(chance_pairs),
        "natural_parent_agreement_count": len(natural_agreements),
        "trace_complete_observed_wall_outcome_count": len(complete_outcomes),
        "seat_count": len(decision_seats),
        "seats": sorted(decision_seats),
        "opponent_count": len(decision_opponents),
        "opponents": sorted(decision_opponents),
        "non_mirror_opponent_count": len(non_mirror),
        "non_mirror_opponents": sorted(non_mirror),
        "strict_opponent_bucket_count": len(strict_buckets),
        "strict_opponent_buckets": sorted(strict_buckets),
        "callbacks_by_seat": dict(sorted(callbacks_by_seat.items())),
        "callbacks_by_opponent": dict(sorted(callbacks_by_opponent.items())),
        "reach_checks": {
            key: "PASS" if passed else "INSUFFICIENT_EVIDENCE"
            for key, passed in reach_checks.items()
        },
        "integrity_gate": "PASS" if integrity_ok else "FAIL",
        "reach_gate": "PASS" if reach_ok else "INSUFFICIENT_EVIDENCE",
        "overall_gate": overall,
        "counterfactual_counted_as_success": False,
        "win_rate_aggregated": False,
        "json_object_identity_independently_reconstructable": False,
        "object_identity_limit": (
            "JSON preserves selected value/order and runtime self-certification "
            "flags; Python object identity is proved only by runtime/static "
            "and fixture checks."
        ),
    }
    return callback_rows, summary


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(_canonical(row) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite_dirs", type=Path, nargs="+")
    parser.add_argument("--rows-out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path, required=True)
    parser.add_argument("--candidate-closure", required=True)
    args = parser.parse_args()
    rows, summary = collect_suite(
        args.suite_dirs,
        expected_candidate_closure=args.candidate_closure,
    )
    _write_jsonl(args.rows_out, rows)
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        _canonical(
            {
                "rows": len(rows),
                "input_manifest_sha256": summary[
                    "input_manifest_sha256"
                ],
                "overall_gate": summary["overall_gate"],
            }
        )
    )
    return 2 if summary["overall_gate"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
