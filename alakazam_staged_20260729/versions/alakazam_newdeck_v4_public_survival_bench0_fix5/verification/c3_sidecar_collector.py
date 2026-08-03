#!/usr/bin/env python3
"""Collect C3 mechanism/integrity evidence from checked raw sidecar JSONL.

This collector intentionally does not aggregate wins, scores, or paired
deltas.  It validates callback pairing, trace identity, closure identity,
allowed C3 action substitutions, transaction faults, and mechanism reach.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


RULE = "V4_PUBLIC_SURVIVAL_BENCH0_FIX5"
PARENT_CLOSURE = (
    "29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157"
)
ALLOWED_GUARDS = frozenset(
    {
        "FLOOR_BOARDOUT_AVOIDANCE",
        "CAP_LOW_COST_BOARDOUT_AVOIDANCE",
    }
)
ALLOWED_BASICS = frozenset({343, 741, 305})
FAULT_STAGES = frozenset({"ABORTED", "ABORTED_AFTER_REENTRY"})
CONTINUITY_CLASSES = frozenset(
    {
        "REPEATABLE_READY",
        "RECHARGE_REQUIRED",
        "NO_READY_ATTACK",
        "UNKNOWN",
    }
)
SIDECAR_GLOB = "runs/*/*/seed_*/seat_*/sidecars/game_*.jsonl"
ORIGIN_STAGES = frozenset({"PROPOSED", "ARMED", "DUPLICATE_REBIND"})


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
            "seed_base": int(parts[runs + 3].removeprefix("seed_")),
            "seat": int(parts[runs + 4].removeprefix("seat_")),
            "game": int(path.stem.removeprefix("game_")),
        }
    except (IndexError, ValueError) as error:
        raise ValueError(
            f"Unexpected checked-suite sidecar path: {path}"
        ) from error


def _callback_key(
    row: dict[str, Any], identity: dict[str, Any]
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


def _game_key(
    row: dict[str, Any], identity: dict[str, Any]
) -> tuple[Any, ...]:
    return (
        row.get("version", identity["version"]),
        row.get("opponent", identity["opponent"]),
        row.get("policy_seat", identity["seat"]),
        row.get("seed_base", identity["seed_base"]),
        row.get("seed"),
        row.get("game"),
    )


def _event_identity_valid(
    row: dict[str, Any], identity: dict[str, Any]
) -> bool:
    version = row.get("version")
    opponent = row.get("opponent")
    seat = row.get("policy_seat")
    seed_base = row.get("seed_base")
    seed = row.get("seed")
    game = row.get("game")
    return (
        isinstance(version, str)
        and bool(version)
        and version == identity["version"]
        and isinstance(opponent, str)
        and bool(opponent)
        and opponent == identity["opponent"]
        and type(seat) is int
        and seat == identity["seat"]
        and type(seed_base) is int
        and seed_base == identity["seed_base"]
        and type(seed) is int
        and type(game) is int
        and game == identity["game"]
        and seed == seed_base + game
    )


def _state_evidence(trace: dict[str, Any]) -> dict[str, Any]:
    selected = trace.get("selected_basic")
    selected_evidence = None
    if isinstance(selected, dict):
        selected_evidence = {
            key: selected.get(key)
            for key in (
                "card_id",
                "serial",
                "canonical_option_key",
            )
        }
    continuities = sorted(
        str(row.get("continuity"))
        for row in (trace.get("damage_rows") or [])
        if isinstance(row, dict)
        and isinstance(row.get("continuity"), str)
    )
    return {
        "guard_class": trace.get("guard_class"),
        "guard_failure": trace.get("guard_failure"),
        "selected_basic": selected_evidence,
        "parent_post_fingerprint": trace.get("parent_post_fingerprint"),
        "candidate_post_fingerprint": trace.get(
            "candidate_post_fingerprint"
        ),
        "continuities": continuities,
        "promotion_removal_context": trace.get(
            "promotion_removal_context"
        ),
        "premium_power_pro_multiplicity": trace.get(
            "premium_power_pro_multiplicity"
        ),
        "evidenced_policy_cap": trace.get("evidenced_policy_cap"),
        "safety_cap": trace.get("safety_cap"),
        "outcome_linkage": trace.get("outcome_linkage"),
    }


def _required_trace(trace: dict[str, Any], candidate_closure: str) -> bool:
    if (
        trace.get("rule_version") != RULE
        or trace.get("parent_closure_sha256") != PARENT_CLOSURE
        or trace.get("candidate_closure_sha256") != candidate_closure
    ):
        return False
    required = (
        "raw_parent_action",
        "proposed_action",
        "applied_action",
        "damage_rows",
        "modifier_ledger",
        "basic_candidates",
        "guard_class",
        "transaction_stage",
        "parent_post_fingerprint",
        "candidate_post_fingerprint",
        "premium_power_pro_multiplicity",
        "evidenced_policy_cap",
        "safety_cap",
        "promotion_removal_context",
        "route_rows",
        "line_importance_rows",
    )
    return all(field in trace for field in required)


def _allowed_action_change(
    event: dict[str, Any], trace: dict[str, Any]
) -> bool:
    if event.get("selected_action") != trace.get("applied_action"):
        return False
    raw = trace.get("raw_parent_action")
    applied = trace.get("applied_action")
    stage = trace.get("transaction_stage")
    if stage in ("NO_ACTION", "ABORTED"):
        return raw == applied
    if stage in ("ARMED", "DUPLICATE_REBIND"):
        selected = trace.get("selected_basic")
        linkage = trace.get("outcome_linkage")
        return (
            trace.get("guard_class") in ALLOWED_GUARDS
            and isinstance(selected, dict)
            and selected.get("card_id") in ALLOWED_BASICS
            and isinstance(selected.get("serial"), int)
            and isinstance(linkage, dict)
            and linkage.get("same_threat_in_both_projections") is True
            and linkage.get("parent_boardout") is True
            and linkage.get("candidate_boardout_prevented") is True
            and linkage.get("tactical_outcome_equal") is True
            and trace.get("parent_post_fingerprint")
            and trace.get("candidate_post_fingerprint")
            and trace.get("parent_post_fingerprint")
            != trace.get("candidate_post_fingerprint")
        )
    if stage == "COMPLETED":
        linkage = trace.get("outcome_linkage")
        semantic = (
            linkage.get("semantic_parent_action")
            if isinstance(linkage, dict)
            else None
        )
        return (
            isinstance(semantic, list)
            and len(semantic) == 2
            and semantic[0] in ("ATTACK", "END")
            and trace.get("guard_failure") is None
        )
    if stage == "ABORTED_AFTER_REENTRY":
        return False
    return False


def collect_suites(
    suite_dirs: Iterable[Path],
    *,
    candidate_closure: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    resolved_suite_dirs = tuple(
        Path(suite_dir).resolve() for suite_dir in suite_dirs
    )
    if not resolved_suite_dirs:
        raise ValueError("At least one suite_dir is required")
    if len(set(resolved_suite_dirs)) != len(resolved_suite_dirs):
        raise ValueError("Duplicate suite_dir inputs are not allowed")
    candidate_closure = candidate_closure.upper()
    if (
        len(candidate_closure) != 64
        or any(
            character not in "0123456789ABCDEF"
            for character in candidate_closure
        )
    ):
        raise ValueError("candidate_closure must be a SHA-256")
    sidecars = []
    for suite_index, suite_dir in enumerate(resolved_suite_dirs):
        suite_sidecars = sorted(suite_dir.glob(SIDECAR_GLOB))
        if not suite_sidecars:
            raise ValueError(
                f"No raw sidecars found below requested suite {suite_dir}"
            )
        sidecars.extend(
            (suite_index, suite_dir, sidecar)
            for sidecar in suite_sidecars
        )

    starts: Counter[tuple[Any, ...]] = Counter()
    ends: Counter[tuple[Any, ...]] = Counter()
    logical_starts: Counter[tuple[Any, ...]] = Counter()
    logical_ends: Counter[tuple[Any, ...]] = Counter()
    start_results: dict[tuple[Any, ...], set[Any]] = defaultdict(set)
    start_identity_validity: dict[
        tuple[Any, ...], set[bool]
    ] = defaultdict(set)
    callback_keys: Counter[tuple[Any, ...]] = Counter()
    guard_counts: Counter[str] = Counter()
    stage_counts: Counter[str] = Counter()
    basic_counts: Counter[int] = Counter()
    callback_continuity_counts: Counter[str] = Counter()
    callback_promotion_removal_counts: Counter[str] = Counter()
    transaction_records: dict[tuple[Any, ...], dict[str, Any]] = {}
    callbacks_by_opponent: Counter[str] = Counter()
    callbacks_by_seat: Counter[int] = Counter()
    decision_instances: dict[tuple[Any, ...], set[str]] = defaultdict(set)
    rows = []
    manifest = []
    missing_or_wrong_trace = 0
    closure_mismatches = 0
    unsupported_action_changes = 0
    transaction_faults = 0
    metric_exceptions = 0
    wrapper_exceptions = 0
    structural_invalid = 0
    non_live_reach_exclusions = 0
    identity_invalid = 0
    sidecars_without_local_pairs = 0

    for suite_index, suite_dir, sidecar in sidecars:
        identity = _path_identity(sidecar)
        source_file = str(sidecar.relative_to(suite_dir))
        source_id = (suite_index, source_file)
        source_keys: set[tuple[Any, ...]] = set()
        file_hash = _sha256(sidecar)
        line_count = 0
        for line_number, event in _json_lines(sidecar):
            line_count += 1
            event_kind = event.get("event")
            if event_kind not in ("CALL_START", "CALL_END"):
                continue
            if (
                type(event.get("callback_ordinal")) is not int
                or event["callback_ordinal"] < 0
            ):
                raise ValueError(
                    f"{sidecar}:{line_number}: invalid callback ordinal"
                )
            logical_key = _callback_key(event, identity)
            key = (*source_id, *logical_key)
            source_keys.add(key)
            event_identity_valid = _event_identity_valid(event, identity)
            identity_invalid += not event_identity_valid
            if event_kind == "CALL_START":
                starts[key] += 1
                logical_starts[logical_key] += 1
                start_identity_validity[key].add(event_identity_valid)
                observation = event.get("observation")
                start_results[key].add(
                    observation.get("result")
                    if isinstance(observation, dict)
                    else None
                )
                continue
            ends[key] += 1
            logical_ends[logical_key] += 1
            callback_keys[key] += 1
            opponent = (
                event["opponent"]
                if event_identity_valid
                else identity["opponent"]
            )
            seat = (
                event["policy_seat"]
                if event_identity_valid
                else identity["seat"]
            )
            if event_identity_valid:
                callbacks_by_opponent[opponent] += 1
                callbacks_by_seat[seat] += 1
            structural_invalid += event.get("structurally_valid") is not True
            wrapper_exceptions += event.get("exception") is not None
            trace = event.get("version_trace")
            if (
                event.get("version_trace_name")
                != "LAST_STAGED_POLICY_TRACE"
                or not isinstance(trace, dict)
            ):
                missing_or_wrong_trace += 1
                continue
            if not _required_trace(trace, candidate_closure):
                if (
                    trace.get("rule_version") == RULE
                    and trace.get("candidate_closure_sha256")
                    != candidate_closure
                ):
                    closure_mismatches += 1
                else:
                    missing_or_wrong_trace += 1
                continue
            if trace.get("metric_exception") is not None:
                metric_exceptions += 1
            guard = str(trace.get("guard_class"))
            stage = str(trace.get("transaction_stage"))
            guard_counts[guard] += 1
            stage_counts[stage] += 1
            if stage in FAULT_STAGES:
                transaction_faults += 1
            if not _allowed_action_change(event, trace):
                unsupported_action_changes += 1
            selected = trace.get("selected_basic")
            if isinstance(selected, dict) and isinstance(
                selected.get("card_id"), int
            ):
                basic_counts[selected["card_id"]] += 1
            for damage_row in trace.get("damage_rows") or []:
                if isinstance(damage_row, dict) and isinstance(
                    damage_row.get("continuity"), str
                ):
                    callback_continuity_counts[
                        damage_row["continuity"]
                    ] += 1
            promotion_removal = trace.get(
                "promotion_removal_context"
            )
            if isinstance(promotion_removal, str) and promotion_removal:
                callback_promotion_removal_counts[
                    promotion_removal
                ] += 1
            decision_id = trace.get("decision_id")
            observation = trace.get("observation_fingerprint")
            game_key = _game_key(event, identity)
            origin_stage = stage in ORIGIN_STAGES
            live_callback = (
                event_identity_valid
                and start_identity_validity.get(key) == {True}
                and start_results.get(key) == {-1}
            )
            # A completed or aborted transaction is observed after the Basic
            # move, so its observation fingerprint is expected to differ from
            # the originating decision.  Conflict detection therefore compares
            # only origin-state callbacks (including an exact duplicate rebind)
            # within one fully-qualified game transaction.
            if (
                origin_stage
                and live_callback
                and isinstance(decision_id, str)
                and bool(decision_id)
                and isinstance(observation, str)
            ):
                decision_instances[
                    (*game_key, decision_id)
                ].add(observation)
            transaction_key = None
            has_decision_id = (
                isinstance(decision_id, str) and bool(decision_id)
            )
            if origin_stage and live_callback and has_decision_id:
                transaction_key = (
                    "decision_instance",
                    *game_key,
                    decision_id,
                )
            elif (
                origin_stage
                and live_callback
                and isinstance(observation, str)
                and observation
            ):
                transaction_key = (
                    "observation",
                    *game_key,
                    observation,
                )
            elif origin_stage and not live_callback:
                non_live_reach_exclusions += 1
            if transaction_key is not None:
                stage_priority = (
                    0
                    if stage == "ARMED"
                    else 1
                    if stage == "PROPOSED"
                    else 2
                    if stage == "DUPLICATE_REBIND"
                    else 3
                )
                existing = transaction_records.get(transaction_key)
                if (
                    existing is None
                    or stage_priority < existing["stage_priority"]
                ):
                    transaction_records[transaction_key] = {
                        "trace": trace,
                        "stage": stage,
                        "stage_priority": stage_priority,
                        "has_decision_id": has_decision_id,
                        "decision_id": decision_id,
                        "observation": observation,
                        "game_key": game_key,
                        "opponent": opponent,
                        "seat": seat,
                    }
            rows.append(
                {
                    "source_suite_index": suite_index,
                    "source_suite": str(suite_dir),
                    "source_file": source_file,
                    "source_sha256": file_hash,
                    "source_line": line_number,
                    "version": event.get("version", identity["version"]),
                    "opponent": opponent,
                    "seat": seat,
                    "seed_base": event.get(
                        "seed_base", identity["seed_base"]
                    ),
                    "seed": event.get("seed"),
                    "game": event.get("game"),
                    "callback_ordinal": event.get("callback_ordinal"),
                    "guard_class": guard,
                    "transaction_stage": stage,
                    "decision_id": decision_id,
                    "observation_fingerprint": observation,
                    "live_callback": live_callback,
                    "selected_basic_id": (
                        selected.get("card_id")
                        if isinstance(selected, dict)
                        else None
                    ),
                    "guard_failure": trace.get("guard_failure"),
                    "promotion_removal_context": promotion_removal,
                }
            )
        if not any(
            starts[key] > 0 and ends[key] > 0 for key in source_keys
        ):
            sidecars_without_local_pairs += 1
        manifest.append(
            {
                "suite_index": suite_index,
                "suite_dir": str(suite_dir),
                "path": source_file,
                "sha256": file_hash,
                "bytes": sidecar.stat().st_size,
                "jsonl_rows": line_count,
            }
        )

    keys = set(starts) | set(ends)
    unmatched_starts = sum(
        max(0, starts[key] - ends[key]) for key in keys
    )
    unmatched_ends = sum(
        max(0, ends[key] - starts[key]) for key in keys
    )
    duplicate_callbacks = sum(
        max(0, count - 1) for count in callback_keys.values()
    ) + sum(max(0, count - 1) for count in starts.values())
    cross_source_duplicate_callbacks = sum(
        max(0, count - 1) for count in logical_starts.values()
    ) + sum(max(0, count - 1) for count in logical_ends.values())
    duplicate_callbacks += cross_source_duplicate_callbacks
    decision_conflicts = sum(
        len(observations) > 1
        for observations in decision_instances.values()
    )
    opponents = sorted(callbacks_by_opponent)
    seats = sorted(callbacks_by_seat)
    non_mirror = [
        value
        for value in opponents
        if "mirror" not in value.lower()
        and "alakazam" not in value.lower()
    ]
    manifest_material = "".join(
        sorted(
            f"{row['path']}\0{row['sha256']}\0{row['bytes']}\n"
            for row in manifest
        )
    ).encode("utf-8")
    manifest_hash = hashlib.sha256(manifest_material).hexdigest().upper()
    unique_state_records: dict[tuple[Any, ...], dict[str, Any]] = {}
    state_evidence: dict[
        tuple[Any, ...], set[str]
    ] = defaultdict(set)
    for record in transaction_records.values():
        if record["has_decision_id"]:
            state_key = ("decision", record["decision_id"])
        else:
            state_key = (
                "observation_instance",
                *record["game_key"],
                record["observation"],
            )
        state_evidence[state_key].add(
            _canonical(_state_evidence(record["trace"]))
        )
        existing = unique_state_records.get(state_key)
        if existing is None:
            unique_state_records[state_key] = {
                "trace": record["trace"],
                "occurrences": {
                    (
                        record["opponent"],
                        record["seat"],
                        record["game_key"],
                    )
                },
            }
        else:
            existing["occurrences"].add(
                (
                    record["opponent"],
                    record["seat"],
                    record["game_key"],
                )
            )
    state_evidence_conflicts = sum(
        len(evidence_rows) > 1
        for evidence_rows in state_evidence.values()
    )
    reach_guard_counts: Counter[str] = Counter()
    continuity_counts: Counter[str] = Counter()
    promotion_removal_counts: Counter[str] = Counter()
    reach_opponents: set[str] = set()
    reach_seats: set[int] = set()
    for record in unique_state_records.values():
        trace = record["trace"]
        guard = str(trace.get("guard_class"))
        reach_guard_counts[guard] += 1
        if guard not in ALLOWED_GUARDS:
            continue
        for occurrence in record["occurrences"]:
            reach_opponents.add(str(occurrence[0]))
            reach_seats.add(int(occurrence[1]))
        for damage_row in trace.get("damage_rows") or []:
            if isinstance(damage_row, dict) and isinstance(
                damage_row.get("continuity"), str
            ):
                continuity_counts[damage_row["continuity"]] += 1
        promotion_removal = trace.get("promotion_removal_context")
        if isinstance(promotion_removal, str) and promotion_removal:
            promotion_removal_counts[promotion_removal] += 1
    integrity_gate = (
        unmatched_starts == 0
        and unmatched_ends == 0
        and duplicate_callbacks == 0
        and missing_or_wrong_trace == 0
        and closure_mismatches == 0
        and unsupported_action_changes == 0
        and transaction_faults == 0
        and metric_exceptions == 0
        and wrapper_exceptions == 0
        and structural_invalid == 0
        and decision_conflicts == 0
        and state_evidence_conflicts == 0
        and identity_invalid == 0
        and sidecars_without_local_pairs == 0
    )
    reach_gate = (
        reach_guard_counts["FLOOR_BOARDOUT_AVOIDANCE"] > 0
        and reach_guard_counts["CAP_LOW_COST_BOARDOUT_AVOIDANCE"] > 0
        and sum(
            reach_guard_counts[name]
            for name in ALLOWED_GUARDS
        )
        >= 30
        and all(continuity_counts[name] > 0 for name in CONTINUITY_CLASSES)
        and sum(promotion_removal_counts.values()) >= 10
        and len(reach_seats) >= 2
        and len(reach_opponents) >= 3
        and len(
            [
                value
                for value in reach_opponents
                if "mirror" not in value.lower()
                and "alakazam" not in value.lower()
            ]
        )
        >= 2
    )
    summary = {
        "schema_version": "c3-raw-sidecar-mechanism-v4",
        "rule_version": RULE,
        "parent_closure_sha256": PARENT_CLOSURE,
        "candidate_closure_sha256": candidate_closure,
        "suite_dir": (
            str(resolved_suite_dirs[0])
            if len(resolved_suite_dirs) == 1
            else None
        ),
        "suite_dirs": [str(path) for path in resolved_suite_dirs],
        "input_suite_count": len(resolved_suite_dirs),
        "input_file_count": len(manifest),
        "input_manifest_sha256": manifest_hash,
        "input_files": manifest,
        "callback_start_count": sum(starts.values()),
        "callback_end_count": sum(ends.values()),
        "duplicate_callback_key_count": duplicate_callbacks,
        "cross_source_duplicate_callback_key_count": (
            cross_source_duplicate_callbacks
        ),
        "unmatched_callback_start_count": unmatched_starts,
        "unmatched_callback_end_count": unmatched_ends,
        "missing_or_wrong_trace_count": missing_or_wrong_trace,
        "closure_mismatch_count": closure_mismatches,
        "unsupported_action_change_count": unsupported_action_changes,
        "transaction_fault_count": transaction_faults,
        "metric_exception_count": metric_exceptions,
        "wrapper_exception_count": wrapper_exceptions,
        "structural_invalid_count": structural_invalid,
        "decision_conflict_count": decision_conflicts,
        "state_evidence_conflict_count": state_evidence_conflicts,
        "identity_invalid_count": identity_invalid,
        "sidecar_without_local_pair_count": (
            sidecars_without_local_pairs
        ),
        "non_live_reach_exclusion_count": non_live_reach_exclusions,
        "guard_class_counts": dict(sorted(guard_counts.items())),
        "reach_guard_class_counts": dict(
            sorted(reach_guard_counts.items())
        ),
        "transaction_stage_counts": dict(sorted(stage_counts.items())),
        "selected_basic_counts": dict(sorted(basic_counts.items())),
        "continuity_counts": dict(sorted(continuity_counts.items())),
        "callback_continuity_counts": dict(
            sorted(callback_continuity_counts.items())
        ),
        "promotion_removal_context_counts": dict(
            sorted(promotion_removal_counts.items())
        ),
        "callback_promotion_removal_context_counts": dict(
            sorted(callback_promotion_removal_counts.items())
        ),
        "reach_transaction_instance_count": len(transaction_records),
        "reach_decision_count": len(unique_state_records),
        "supported_threat_count": sum(
            reach_guard_counts[name] for name in ALLOWED_GUARDS
        ),
        "promotion_removal_context_count": sum(
            promotion_removal_counts.values()
        ),
        "seats": seats,
        "opponents": opponents,
        "non_mirror_opponents": non_mirror,
        "reach_seats": sorted(reach_seats),
        "reach_opponents": sorted(reach_opponents),
        "reach_non_mirror_opponents": sorted(
            value
            for value in reach_opponents
            if "mirror" not in value.lower()
            and "alakazam" not in value.lower()
        ),
        "integrity_gate": "PASS" if integrity_gate else "FAIL",
        "reach_gate": "PASS"
        if reach_gate
        else "INSUFFICIENT_EVIDENCE",
        "overall_gate": "PASS"
        if integrity_gate and reach_gate
        else "FAIL"
        if not integrity_gate
        else "INSUFFICIENT_EVIDENCE",
        "win_rate_aggregated": False,
    }
    rows.sort(
        key=lambda row: (
            row["version"],
            row["opponent"],
            row["seat"],
            -1 if row["seed"] is None else row["seed"],
            -1 if row["game"] is None else row["game"],
            row["callback_ordinal"],
        )
    )
    return rows, summary


def collect_suite(
    suite_dir: Path,
    *,
    candidate_closure: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return collect_suites(
        [suite_dir],
        candidate_closure=candidate_closure,
    )


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(_canonical(row) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite_dirs", type=Path, nargs="+")
    parser.add_argument("--candidate-closure", required=True)
    parser.add_argument("--rows-out", type=Path, required=True)
    parser.add_argument("--summary-out", type=Path, required=True)
    args = parser.parse_args()
    if args.rows_out.resolve() == args.summary_out.resolve():
        parser.error("--rows-out and --summary-out must be different files")
    rows, summary = collect_suites(
        args.suite_dirs,
        candidate_closure=args.candidate_closure,
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
    return 0 if summary["integrity_gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
