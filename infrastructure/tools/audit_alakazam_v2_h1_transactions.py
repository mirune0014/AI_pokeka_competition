#!/usr/bin/env python3
"""Audit callback pairing and the certified Alakazam v2 H1 transaction chain."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


RULE = "V2_H1_UNIQUE_BENCH_ALAKAZAM_ATTACH_THEN_KO"


def _json_lines(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: row is not an object")
            yield line_number, row


def _sidecar_identity(path: Path) -> dict[str, Any]:
    parts = path.parts
    try:
        runs_index = parts.index("runs")
        return {
            "version": parts[runs_index + 1],
            "opponent": parts[runs_index + 2],
            "seed_base": int(parts[runs_index + 3].removeprefix("seed_")),
            "seat": int(parts[runs_index + 4].removeprefix("seat_")),
            "game_file": path.stem,
        }
    except (IndexError, ValueError) as error:
        raise ValueError(f"Unexpected sidecar path: {path}") from error


def audit_suite(suite_dir: Path) -> dict[str, Any]:
    sidecars = sorted(suite_dir.glob("runs/*/*/seed_*/seat_*/sidecars/game_*.jsonl"))
    if not sidecars:
        raise ValueError(f"No sidecars found below {suite_dir}")

    callback_starts = 0
    callback_ends = 0
    duplicate_callback_keys = 0
    unmatched_callback_starts = 0
    unmatched_callback_ends = 0
    structural_invalid = 0
    exception_rows = 0
    first_legal_fallback = 0
    generic_fallback = 0
    irreversible_aborts = 0
    transaction_starts = 0
    attach_verified = 0
    attacks_dispatched = 0
    ko_resolved = 0
    sequence_faults = 0
    pending_transactions = 0
    selected_rule_callbacks = 0
    defer_with_rule = 0
    active_owner_conflict_tags = 0
    stage_counts: Counter[str] = Counter()
    outcome_counts: Counter[str] = Counter()
    abort_reasons: Counter[str] = Counter()
    reason_tags: Counter[str] = Counter()
    starts_by_opponent: Counter[str] = Counter()
    starts_by_seat: Counter[str] = Counter()
    starts_by_seed_base: Counter[str] = Counter()
    completes_by_opponent: Counter[str] = Counter()
    completes_by_seat: Counter[str] = Counter()
    completes_by_seed_base: Counter[str] = Counter()
    complete_transaction_keys: list[dict[str, Any]] = []

    for sidecar in sidecars:
        identity = _sidecar_identity(sidecar)
        seen_starts: set[int] = set()
        seen_ends: set[int] = set()
        active = False

        for line_number, row in _json_lines(sidecar):
            event = row.get("event")
            ordinal = row.get("callback_ordinal")
            if type(ordinal) is not int:
                raise ValueError(
                    f"{sidecar}:{line_number}: callback_ordinal is not int"
                )
            if event == "CALL_START":
                callback_starts += 1
                if ordinal in seen_starts:
                    duplicate_callback_keys += 1
                seen_starts.add(ordinal)
                continue
            if event != "CALL_END":
                continue

            callback_ends += 1
            if ordinal in seen_ends:
                duplicate_callback_keys += 1
            seen_ends.add(ordinal)
            if row.get("structurally_valid") is not True:
                structural_invalid += 1
            if row.get("exception") is not None:
                exception_rows += 1
            if row.get("first_legal_fallback_selected") is True:
                first_legal_fallback += 1
            if row.get("generic_fallback_selected") is True:
                generic_fallback += 1

            trace = row.get("version_trace")
            if not isinstance(trace, dict):
                continue
            stage = str(trace.get("stage"))
            outcome = str(trace.get("transaction_outcome"))
            stage_counts[stage] += 1
            outcome_counts[outcome] += 1
            tags = trace.get("reason_tags")
            if not isinstance(tags, list):
                tags = []
            for tag in tags:
                reason_tags[str(tag)] += 1
            selected_rule = trace.get("selected_rule")
            if selected_rule is not None:
                selected_rule_callbacks += 1
            if "V2_DEFER_V1_OWNER" in tags and selected_rule is not None:
                defer_with_rule += 1
            if any(
                tag in {
                    "V2_H1_NEW_OWNER_DURING_TRANSACTION",
                    "V2_H1_V1_ATTACK_OWNER_OR_ACTION_MISMATCH",
                }
                for tag in tags
            ):
                active_owner_conflict_tags += 1

            started = trace.get("transaction_started") is True
            attached = trace.get("attach_verified") is True
            attacked = trace.get("attack_dispatched") is True
            completed = trace.get("KO_resolved") is True
            aborted = trace.get("irreversible_abort_fault") is True

            if started:
                transaction_starts += 1
                starts_by_opponent[identity["opponent"]] += 1
                starts_by_seat[str(identity["seat"])] += 1
                starts_by_seed_base[str(identity["seed_base"])] += 1
                if active:
                    sequence_faults += 1
                active = True
            if attached:
                attach_verified += 1
                if not active:
                    sequence_faults += 1
            if attacked:
                attacks_dispatched += 1
                if not active:
                    sequence_faults += 1
            if completed:
                ko_resolved += 1
                if not active:
                    sequence_faults += 1
                else:
                    active = False
                completes_by_opponent[identity["opponent"]] += 1
                completes_by_seat[str(identity["seat"])] += 1
                completes_by_seed_base[str(identity["seed_base"])] += 1
                complete_transaction_keys.append(
                    {
                        **identity,
                        "callback_ordinal": ordinal,
                        "energy_id": trace.get("energy_id"),
                        "H0_attacker_serial": trace.get("H0_attacker_serial"),
                        "H1_alakazam_serial": trace.get("H1_alakazam_serial"),
                        "target_serial": trace.get("target_serial"),
                    }
                )
            if aborted:
                irreversible_aborts += 1
                abort_reasons[str(trace.get("transaction_abort_reason"))] += 1
                active = False

        unmatched_callback_starts += len(seen_starts - seen_ends)
        unmatched_callback_ends += len(seen_ends - seen_starts)
        if active:
            pending_transactions += 1

    complete_opponents = sorted(
        opponent for opponent, count in completes_by_opponent.items() if count
    )
    complete_seats = sorted(
        int(seat) for seat, count in completes_by_seat.items() if count
    )
    complete_seed_bases = sorted(
        int(seed) for seed, count in completes_by_seed_base.items() if count
    )
    hard_fault_count = sum(
        (
            duplicate_callback_keys,
            unmatched_callback_starts,
            unmatched_callback_ends,
            structural_invalid,
            exception_rows,
            first_legal_fallback,
            generic_fallback,
            irreversible_aborts,
            sequence_faults,
            pending_transactions,
            defer_with_rule,
            active_owner_conflict_tags,
        )
    )
    return {
        "schema_version": "alakazam-v2-h1-transaction-audit-v1",
        "suite_dir": str(suite_dir.resolve()),
        "sidecar_files": len(sidecars),
        "callback_starts": callback_starts,
        "callback_ends": callback_ends,
        "duplicate_callback_keys": duplicate_callback_keys,
        "unmatched_callback_starts": unmatched_callback_starts,
        "unmatched_callback_ends": unmatched_callback_ends,
        "structural_invalid": structural_invalid,
        "exception_rows": exception_rows,
        "first_legal_fallback": first_legal_fallback,
        "generic_fallback": generic_fallback,
        "transaction_starts": transaction_starts,
        "attach_verified": attach_verified,
        "attacks_dispatched": attacks_dispatched,
        "ko_resolved": ko_resolved,
        "irreversible_aborts": irreversible_aborts,
        "sequence_faults": sequence_faults,
        "pending_transactions": pending_transactions,
        "selected_rule_callbacks": selected_rule_callbacks,
        "defer_with_rule": defer_with_rule,
        "active_owner_conflict_tags": active_owner_conflict_tags,
        "hard_fault_count": hard_fault_count,
        "complete_opponent_count": len(complete_opponents),
        "complete_opponents": complete_opponents,
        "complete_seat_count": len(complete_seats),
        "complete_seats": complete_seats,
        "complete_seed_base_count": len(complete_seed_bases),
        "complete_seed_bases": complete_seed_bases,
        "historical_silver_completes": completes_by_opponent.get(
            "historical_silver", 0
        ),
        "starts_by_opponent": dict(sorted(starts_by_opponent.items())),
        "starts_by_seat": dict(sorted(starts_by_seat.items())),
        "starts_by_seed_base": dict(sorted(starts_by_seed_base.items())),
        "completes_by_opponent": dict(sorted(completes_by_opponent.items())),
        "completes_by_seat": dict(sorted(completes_by_seat.items())),
        "completes_by_seed_base": dict(sorted(completes_by_seed_base.items())),
        "stage_counts": dict(sorted(stage_counts.items())),
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "abort_reasons": dict(sorted(abort_reasons.items())),
        "reason_tags": dict(sorted(reason_tags.items())),
        "complete_transaction_keys": complete_transaction_keys,
    }


def write_audit(audit: dict[str, Any], output: Path) -> str:
    payload = json.dumps(
        audit, ensure_ascii=False, indent=2, sort_keys=True
    ) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8", newline="\n")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = audit_suite(args.suite_dir)
    digest = write_audit(audit, args.output)
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "sha256": digest,
                "hard_fault_count": audit["hard_fault_count"],
                "transaction_starts": audit["transaction_starts"],
                "ko_resolved": audit["ko_resolved"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
