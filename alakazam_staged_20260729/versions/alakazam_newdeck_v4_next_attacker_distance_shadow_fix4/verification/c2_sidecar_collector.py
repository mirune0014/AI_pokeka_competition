#!/usr/bin/env python3
"""Collect C2 coverage evidence directly from checked raw sidecar JSONL.

The collector is read-only with respect to its inputs.  It intentionally
reports no game result, score, or win-rate aggregate.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


RULE = "V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4"
ROUTE_CLASSES = ("CERTIFIED", "POSSIBLE", "IMPOSSIBLE", "UNKNOWN")
SIDECAR_GLOB = "runs/*/*/seed_*/seat_*/sidecars/game_*.jsonl"


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _json_lines(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(
                    f"{path}:{line_number}: JSONL row is not an object"
                )
            yield line_number, value


def _path_identity(path: Path) -> dict[str, Any]:
    parts = path.parts
    try:
        runs = parts.index("runs")
        return {
            "version": parts[runs + 1],
            "opponent": parts[runs + 2],
            "seed_base": int(
                parts[runs + 3].removeprefix("seed_")
            ),
            "seat": int(parts[runs + 4].removeprefix("seat_")),
            "game_file": path.stem,
        }
    except (IndexError, ValueError) as error:
        raise ValueError(
            f"Unexpected checked-suite sidecar path: {path}"
        ) from error


def _callback_key(
    row: dict[str, Any],
    identity: dict[str, Any],
) -> tuple[Any, ...]:
    return (
        row.get("version", identity["version"]),
        row.get("opponent", identity["opponent"]),
        row.get("policy_seat", identity["seat"]),
        row.get("seed_base", identity["seed_base"]),
        row.get("seed"),
        row.get("game"),
        row.get("callback_ordinal"),
    )


def _action_identity_ok(
    end: dict[str, Any],
    trace: dict[str, Any],
) -> bool:
    identity = trace.get("action_identity")
    if not isinstance(identity, dict):
        return False
    flags = (
        "value_equal",
        "type_equal",
        "order_equal",
        "returned_parent_object_unchanged",
    )
    if not all(identity.get(key) is True for key in flags):
        return False
    if not isinstance(trace.get("action_python_type"), str):
        return False
    return (
        trace.get("raw_parent_action")
        == trace.get("applied_action")
        == end.get("selected_action")
    )


def _route_rows(
    trace: dict[str, Any],
) -> Iterable[tuple[Any, str, dict[str, Any]]]:
    for row in trace.get("route_rows") or []:
        if not isinstance(row, dict):
            continue
        for kind, field in (
            ("primary", "primary_distance"),
            ("fallback", "fallback_attack_distance"),
        ):
            distance = row.get(field)
            if isinstance(distance, dict):
                yield row.get("line_id"), kind, distance


def collect_suite(
    suite_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    suite_dir = suite_dir.resolve()
    sidecars = sorted(suite_dir.glob(SIDECAR_GLOB))
    if not sidecars:
        raise ValueError(f"No raw sidecars found below {suite_dir}")

    output_rows: list[dict[str, Any]] = []
    file_manifest: list[dict[str, Any]] = []
    starts: dict[tuple[Any, ...], int] = defaultdict(int)
    ends: dict[tuple[Any, ...], int] = defaultdict(int)
    callback_keys: Counter[tuple[Any, ...]] = Counter()
    observation_callbacks: Counter[str] = Counter()
    observation_classes: dict[str, set[str]] = defaultdict(set)
    fingerprint_payloads: dict[str, set[str]] = defaultdict(set)
    callbacks_by_opponent: Counter[str] = Counter()
    callbacks_by_seat: Counter[int] = Counter()
    action_identity_failures = 0
    metric_exceptions = 0
    missing_or_wrong_trace = 0
    structural_invalid = 0
    wrapper_exceptions = 0

    for sidecar in sidecars:
        identity = _path_identity(sidecar)
        file_sha = _sha256(sidecar)
        line_count = 0
        call_end_count = 0
        for line_number, event in _json_lines(sidecar):
            line_count += 1
            event_kind = event.get("event")
            key = _callback_key(event, identity)
            if type(event.get("callback_ordinal")) is not int:
                raise ValueError(
                    f"{sidecar}:{line_number}: callback_ordinal is not int"
                )
            if event_kind == "CALL_START":
                starts[key] += 1
                continue
            if event_kind != "CALL_END":
                continue
            call_end_count += 1
            ends[key] += 1
            callback_keys[key] += 1
            opponent = str(
                event.get("opponent", identity["opponent"])
            )
            seat = event.get("policy_seat", identity["seat"])
            if type(seat) is not int:
                raise ValueError(
                    f"{sidecar}:{line_number}: policy_seat is not int"
                )
            callbacks_by_opponent[opponent] += 1
            callbacks_by_seat[seat] += 1
            if event.get("structurally_valid") is not True:
                structural_invalid += 1
            if event.get("exception") is not None:
                wrapper_exceptions += 1

            trace = event.get("version_trace")
            if (
                event.get("version_trace_name")
                != "LAST_STAGED_POLICY_TRACE"
                or not isinstance(trace, dict)
                or trace.get("rule_version") != RULE
            ):
                missing_or_wrong_trace += 1
                continue
            fingerprint = trace.get("observation_fingerprint")
            if not isinstance(fingerprint, str) or not fingerprint:
                missing_or_wrong_trace += 1
                continue
            observation_callbacks[fingerprint] += 1
            fingerprint_payloads[fingerprint].add(
                _canonical(
                    {
                        "route_rows": trace.get("route_rows"),
                        "best_primary_route": trace.get(
                            "best_primary_route"
                        ),
                        "best_fallback_route": trace.get(
                            "best_fallback_route"
                        ),
                        "unsupported_reasons": trace.get(
                            "unsupported_reasons"
                        ),
                    }
                )
            )
            identity_ok = _action_identity_ok(event, trace)
            if not identity_ok:
                action_identity_failures += 1
            if trace.get("metric_exception") is not None:
                metric_exceptions += 1

            emitted = False
            for line_id, distance_kind, distance in _route_rows(trace):
                route_class = distance.get("route_class")
                if route_class not in ROUTE_CLASSES:
                    route_class = "UNKNOWN"
                observation_classes[fingerprint].add(route_class)
                output_rows.append(
                    {
                        "source_file": str(
                            sidecar.relative_to(suite_dir)
                        ),
                        "source_sha256": file_sha,
                        "source_line": line_number,
                        "version": event.get(
                            "version", identity["version"]
                        ),
                        "opponent": opponent,
                        "seat": seat,
                        "seed_base": event.get(
                            "seed_base", identity["seed_base"]
                        ),
                        "seed": event.get("seed"),
                        "game": event.get("game"),
                        "callback_ordinal": event.get(
                            "callback_ordinal"
                        ),
                        "trace_rule_version": trace.get(
                            "rule_version"
                        ),
                        "action_identity": trace.get(
                            "action_identity"
                        ),
                        "action_identity_ok": identity_ok,
                        "metric_exception": trace.get(
                            "metric_exception"
                        ),
                        "observation_fingerprint": fingerprint,
                        "line_id": line_id,
                        "distance_kind": distance_kind,
                        "route_class": route_class,
                        "turn_delay": distance.get("turn_delay"),
                        "main_actions": distance.get(
                            "main_actions"
                        ),
                        "forced_prompts": distance.get(
                            "forced_prompts"
                        ),
                    }
                )
                emitted = True
            if not emitted:
                observation_classes[fingerprint].add("UNKNOWN")
                output_rows.append(
                    {
                        "source_file": str(
                            sidecar.relative_to(suite_dir)
                        ),
                        "source_sha256": file_sha,
                        "source_line": line_number,
                        "version": event.get(
                            "version", identity["version"]
                        ),
                        "opponent": opponent,
                        "seat": seat,
                        "seed_base": event.get(
                            "seed_base", identity["seed_base"]
                        ),
                        "seed": event.get("seed"),
                        "game": event.get("game"),
                        "callback_ordinal": event.get(
                            "callback_ordinal"
                        ),
                        "trace_rule_version": trace.get(
                            "rule_version"
                        ),
                        "action_identity": trace.get(
                            "action_identity"
                        ),
                        "action_identity_ok": identity_ok,
                        "metric_exception": trace.get(
                            "metric_exception"
                        ),
                        "observation_fingerprint": fingerprint,
                        "line_id": None,
                        "distance_kind": "none",
                        "route_class": "UNKNOWN",
                        "turn_delay": None,
                        "main_actions": None,
                        "forced_prompts": None,
                    }
                )
        file_manifest.append(
            {
                "path": str(sidecar.relative_to(suite_dir)),
                "sha256": file_sha,
                "bytes": sidecar.stat().st_size,
                "jsonl_rows": line_count,
                "call_end_rows": call_end_count,
            }
        )

    manifest_material = "".join(
        (
            f"{row['path']}\0{row['sha256']}\0"
            f"{row['bytes']}\n"
        )
        for row in file_manifest
    ).encode("utf-8")
    input_manifest_sha = hashlib.sha256(
        manifest_material
    ).hexdigest().upper()

    all_keys = set(starts) | set(ends)
    unmatched_starts = sum(
        max(0, starts[key] - ends[key]) for key in all_keys
    )
    unmatched_ends = sum(
        max(0, ends[key] - starts[key]) for key in all_keys
    )
    duplicate_callback_keys = sum(
        max(0, count - 1) for count in callback_keys.values()
    ) + sum(max(0, count - 1) for count in starts.values())
    unique_state_count = len(observation_callbacks)
    duplicate_decision_count = sum(
        max(0, count - 1)
        for count in observation_callbacks.values()
    )
    route_class_unique_state_counts = {
        route_class: sum(
            route_class in classes
            for classes in observation_classes.values()
        )
        for route_class in ROUTE_CLASSES
    }
    opponents = sorted(callbacks_by_opponent)
    seats = sorted(callbacks_by_seat)
    non_mirror_opponents = [
        opponent
        for opponent in opponents
        if "mirror" not in opponent.lower()
        and "alakazam" not in opponent.lower()
    ]
    fingerprint_trace_conflicts = sum(
        len(payloads) > 1
        for payloads in fingerprint_payloads.values()
    )
    pairing_faults = (
        unmatched_starts
        + unmatched_ends
        + duplicate_callback_keys
    )
    identity_gate = (
        action_identity_failures == 0
        and structural_invalid == 0
        and wrapper_exceptions == 0
        and pairing_faults == 0
    )
    metric_gate = metric_exceptions == 0
    trace_gate = (
        missing_or_wrong_trace == 0
        and fingerprint_trace_conflicts == 0
    )
    coverage_gate = (
        unique_state_count >= 50
        and len(seats) >= 2
        and len(opponents) >= 3
        and len(non_mirror_opponents) >= 2
        and all(
            route_class_unique_state_counts[route_class] >= 5
            for route_class in ROUTE_CLASSES
        )
    )
    if not identity_gate or not metric_gate or not trace_gate:
        overall = "FAIL"
    elif coverage_gate:
        overall = "PASS"
    else:
        overall = "INSUFFICIENT_EVIDENCE"

    output_rows.sort(
        key=lambda row: (
            str(row["version"]),
            str(row["opponent"]),
            row["seat"],
            -1 if row["seed"] is None else row["seed"],
            -1 if row["game"] is None else row["game"],
            row["callback_ordinal"],
            str(row["line_id"]),
            row["distance_kind"],
        )
    )
    summary = {
        "schema_version": "c2-raw-sidecar-coverage-v1",
        "rule_version": RULE,
        "suite_dir": str(suite_dir),
        "input_file_count": len(file_manifest),
        "input_manifest_sha256": input_manifest_sha,
        "input_files": file_manifest,
        "callback_start_count": sum(starts.values()),
        "callback_end_count": sum(ends.values()),
        "unique_callback_key_count": len(callback_keys),
        "duplicate_callback_key_count": duplicate_callback_keys,
        "unmatched_callback_start_count": unmatched_starts,
        "unmatched_callback_end_count": unmatched_ends,
        "unique_state_count": unique_state_count,
        "duplicate_decision_count": duplicate_decision_count,
        "duplicate_decisions_excluded_from_unique_states": True,
        "fingerprint_trace_conflict_count": (
            fingerprint_trace_conflicts
        ),
        "route_class_unique_state_counts": (
            route_class_unique_state_counts
        ),
        "seat_count": len(seats),
        "seats": seats,
        "opponent_count": len(opponents),
        "opponents": opponents,
        "non_mirror_opponent_count": len(non_mirror_opponents),
        "non_mirror_opponents": non_mirror_opponents,
        "callbacks_by_seat": dict(sorted(callbacks_by_seat.items())),
        "callbacks_by_opponent": dict(
            sorted(callbacks_by_opponent.items())
        ),
        "action_identity_failure_count": action_identity_failures,
        "metric_exception_count": metric_exceptions,
        "missing_or_wrong_trace_count": missing_or_wrong_trace,
        "structural_invalid_count": structural_invalid,
        "wrapper_exception_count": wrapper_exceptions,
        "action_identity_gate": (
            "PASS" if identity_gate else "FAIL"
        ),
        "metric_exception_gate": (
            "PASS" if metric_gate else "FAIL"
        ),
        "trace_integrity_gate": (
            "PASS" if trace_gate else "FAIL"
        ),
        "coverage_gate": (
            "PASS" if coverage_gate else "INSUFFICIENT_EVIDENCE"
        ),
        "overall_gate": overall,
        "win_rate_aggregated": False,
    }
    return output_rows, summary


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(_canonical(row) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite_dir", type=Path)
    parser.add_argument("--rows-out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path, required=True)
    args = parser.parse_args()
    rows, summary = collect_suite(args.suite_dir)
    _write_jsonl(args.rows_out, rows)
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(
        json.dumps(
            summary,
            sort_keys=True,
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
