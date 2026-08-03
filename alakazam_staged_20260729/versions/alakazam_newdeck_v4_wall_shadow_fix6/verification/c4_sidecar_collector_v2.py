#!/usr/bin/env python3
"""C4 collector erratum: exclude certified no-live-line negative records.

The frozen v1 collector required ``protected_line`` to be a dictionary at
every recognized decision prompt.  The analyzer deliberately emits a complete
fail-closed record with ``protected_line=null`` when no unique live Alakazam
line can be certified.  This version accepts only the exact negative shape
defined below, keeps all universal integrity checks, and removes the record
from every reach/outcome count.
"""

from __future__ import annotations

import argparse
import copy
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

try:
    from . import c4_sidecar_collector as _v1
except ImportError:
    import c4_sidecar_collector as _v1


AMENDMENT = "C4_NO_LIVE_LINE_NEGATIVE_ONLY_V1"
FROZEN_COLLECTOR_SHA256 = (
    "770EA508AF3CCFEC549C1C543EB8D04041553236B11C6D5C3CBBA8FF30344BEE"
)


def _duplicates(values: Any) -> set[str]:
    if not isinstance(values, list) or any(
        not isinstance(value, str) or not value for value in values
    ):
        return {"__INVALID_LIST__"}
    return {
        value for value in values if values.count(value) > 1
    }


def _negative_shape(trace: Any) -> bool:
    """Return true only for the monotone, non-evidence rejection shape."""
    if (
        not isinstance(trace, dict)
        or trace.get("decision_point") is None
        or trace.get("protected_line") is not None
        or trace.get("importance") != "UNKNOWN_IMPORTANCE"
        or trace.get("distance_before") is not None
        or trace.get("distance_without_line") is not None
        or trace.get("outcome_status") != "COUNTERFACTUAL_UNOBSERVED"
        or trace.get("wall_class") != "PARENT_FALLBACK"
        or trace.get("semantic_parent_action_keys")
        != trace.get("semantic_proposed_action_keys")
        or trace.get("parent_action") != trace.get("proposed_action")
        or trace.get("parent_action") != trace.get("applied_action")
    ):
        return False

    rows = trace.get("candidate_rows")
    if not isinstance(rows, list) or len(rows) != 4:
        return False
    run, reusable, sacrifice, fallback = rows
    if any(not isinstance(row, dict) for row in rows):
        return False
    if (
        run.get("kind") != "RUN_AWAY_ACCELERATION"
        or reusable.get("kind") != "CERTIFIED_REUSABLE_WALL"
        or sacrifice.get("kind") != "CERTIFIED_SACRIFICE_WALL"
        or fallback.get("kind") != "NO_WALL_OR_UNKNOWN"
        or fallback.get("certification") != "AVAILABLE"
        or fallback.get("wall_class") != "PARENT_FALLBACK"
        or fallback.get("semantic_action_key")
        != trace.get("semantic_parent_action_keys")
    ):
        return False
    if run.get("certification") not in (
        "PRESERVE_CHANCE",
        "REJECTED",
        "UNAVAILABLE",
    ):
        return False
    if reusable.get("certification") not in ("REJECTED", "UNAVAILABLE"):
        return False
    if sacrifice.get("certification") not in ("REJECTED", "UNAVAILABLE"):
        return False
    if any(row.get("certification") == "STRICT" for row in rows):
        return False
    if any(
        row.get("certification") == "PRESERVE_CHANCE"
        for row in (reusable, sacrifice)
    ):
        return False

    trace_codes = set(trace.get("rejection_codes") or [])
    trace_unsupported = set(trace.get("unsupported_reasons") or [])
    row_codes = {
        code
        for row in rows[:3]
        for code in (row.get("rejection_codes") or [])
        if isinstance(code, str)
    }
    if "NO_LIVE_PROTECTED_LINE" not in (
        trace_codes | trace_unsupported | row_codes
    ):
        return False
    if "NO_LIVE_PROTECTED_LINE" not in trace_codes:
        return False
    if "NO_LIVE_PROTECTED_LINE" not in trace_unsupported:
        return False

    pair_material = trace.get("pair_material")
    expose = trace.get("expose_projection")
    wall = trace.get("wall_projection")
    if (
        not isinstance(pair_material, dict)
        or pair_material.get("protected_serial") is not None
        or not isinstance(expose, dict)
        or expose.get("protected_line") is not None
        or not isinstance(wall, dict)
        or wall.get("chosen") is not None
        or wall.get("chosen_kind") != "NO_WALL_OR_UNKNOWN"
        or wall.get("chosen_semantic_action_key")
        != trace.get("semantic_parent_action_keys")
    ):
        return False

    for row in (reusable, sacrifice):
        duplicate_codes = _duplicates(row.get("rejection_codes"))
        if duplicate_codes not in (set(), {"NO_LIVE_PROTECTED_LINE"}):
            return False
        if duplicate_codes == {"NO_LIVE_PROTECTED_LINE"} and (
            row["rejection_codes"].count("NO_LIVE_PROTECTED_LINE") != 2
        ):
            return False
    for row in (run, fallback):
        if _duplicates(row.get("rejection_codes")):
            return False
    return True


def _normalized_negative(trace: dict[str, Any]) -> dict[str, Any]:
    """Create an in-memory validation view without mutating raw evidence."""
    normalized = copy.deepcopy(trace)
    normalized["protected_line"] = {}
    for row in normalized["candidate_rows"][1:3]:
        codes = row.get("rejection_codes")
        if (
            isinstance(codes, list)
            and codes.count("NO_LIVE_PROTECTED_LINE") == 2
            and _duplicates(codes) == {"NO_LIVE_PROTECTED_LINE"}
        ):
            deduplicated = []
            seen_no_live = False
            for code in codes:
                if code == "NO_LIVE_PROTECTED_LINE":
                    if seen_no_live:
                        continue
                    seen_no_live = True
                deduplicated.append(code)
            row["rejection_codes"] = deduplicated
    return normalized


_ORIGINAL_TRACE_SCHEMA_FAULTS = _v1._trace_schema_faults
_ORIGINAL_DECISION_CLASS = _v1._decision_class


def amended_trace_schema_faults(
    trace: Any,
    expected_candidate_closure: str,
    raw_public_material: dict[str, Any] | None,
) -> dict[str, bool]:
    if not _negative_shape(trace):
        return _ORIGINAL_TRACE_SCHEMA_FAULTS(
            trace,
            expected_candidate_closure,
            raw_public_material,
        )
    normalized = _normalized_negative(trace)
    return _ORIGINAL_TRACE_SCHEMA_FAULTS(
        normalized,
        expected_candidate_closure,
        raw_public_material,
    )


def amended_decision_class(trace: dict[str, Any]) -> str | None:
    if _negative_shape(trace):
        return None
    return _ORIGINAL_DECISION_CLASS(trace)


def _negative_diagnostics(
    suites: Iterable[Path],
    expected_candidate_closure: str,
    callback_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    negative_pairs: dict[str, set[str]] = defaultdict(set)
    exclusions = 0
    duplicate_rows = 0
    parse_faults = 0

    for suite in suites:
        for sidecar in sorted(suite.glob(_v1.SIDECAR_GLOB)):
            try:
                source_rows = _v1._json_lines(sidecar)
            except (ValueError, json.JSONDecodeError):
                parse_faults += 1
                continue
            open_material: dict[tuple[Any, ...], dict[str, Any] | None] = {}
            identity = _v1._path_identity(suite, sidecar)
            for _, event in source_rows:
                identity_ok, callback_key = _v1._event_identity(event, identity)
                if not identity_ok or callback_key is None:
                    continue
                if event.get("event") == "CALL_START":
                    open_material[callback_key] = (
                        _v1._canonical_public_state_material(
                            event.get("observation")
                        )
                    )
                    continue
                if event.get("event") != "CALL_END":
                    continue
                trace = event.get("version_trace")
                raw_material = open_material.pop(callback_key, None)
                if not _negative_shape(trace):
                    continue
                faults = amended_trace_schema_faults(
                    trace,
                    expected_candidate_closure,
                    raw_material,
                )
                action_faults = _v1._action_faults(event, trace)
                if any(faults.values()) or not all(action_faults.values()):
                    continue
                exclusions += 1
                duplicate_rows += sum(
                    _duplicates(row.get("rejection_codes"))
                    == {"NO_LIVE_PROTECTED_LINE"}
                    for row in trace["candidate_rows"][1:3]
                )
                pair_id = trace.get("pair_id")
                if isinstance(pair_id, str):
                    evidence = _v1._canonical(
                        {
                            "pair_material": trace.get("pair_material"),
                            "public_state_fingerprint": trace.get(
                                "public_state_fingerprint"
                            ),
                            "expose_state_fingerprint": trace.get(
                                "expose_state_fingerprint"
                            ),
                            "wall_state_fingerprint": trace.get(
                                "wall_state_fingerprint"
                            ),
                            "decision_point": trace.get("decision_point"),
                            "semantic_parent_action_keys": trace.get(
                                "semantic_parent_action_keys"
                            ),
                        }
                    )
                    negative_pairs[pair_id].add(evidence)

    valid_pair_ids = {
        row.get("pair_id")
        for row in callback_rows
        if row.get("decision_class") in ("STRICT", "PRESERVE_CHANCE")
        and isinstance(row.get("pair_id"), str)
    }
    internal_collisions = {
        pair_id
        for pair_id, evidence in negative_pairs.items()
        if len(evidence) != 1
    }
    cross_collisions = set(negative_pairs) & valid_pair_ids
    return {
        "negative_only_no_live_exclusion_count": exclusions,
        "negative_only_duplicate_diagnostic_row_count": duplicate_rows,
        "negative_only_pair_id_count": len(negative_pairs),
        "negative_only_internal_collision_count": len(internal_collisions),
        "negative_only_valid_pair_collision_count": len(cross_collisions),
        "negative_only_parse_fault_count": parse_faults,
        "negative_only_collision_pair_ids": sorted(
            internal_collisions | cross_collisions
        ),
    }


def collect_suite(
    suite_dirs: Iterable[Path],
    *,
    expected_candidate_closure: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    suites = [Path(path).resolve() for path in suite_dirs]
    original_schema = _v1._trace_schema_faults
    original_class = _v1._decision_class
    _v1._trace_schema_faults = amended_trace_schema_faults
    _v1._decision_class = amended_decision_class
    try:
        rows, summary = _v1.collect_suite(
            suites,
            expected_candidate_closure=expected_candidate_closure,
        )
    finally:
        _v1._trace_schema_faults = original_schema
        _v1._decision_class = original_class

    diagnostics = _negative_diagnostics(
        suites,
        expected_candidate_closure,
        rows,
    )
    summary.update(diagnostics)
    summary["schema_version"] = "c4-wall-shadow-sidecar-coverage-v3"
    summary["collector_amendment"] = AMENDMENT
    summary["frozen_collector_sha256"] = FROZEN_COLLECTOR_SHA256
    summary["monotonic_evidence_removal"] = True
    amendment_faults = (
        diagnostics["negative_only_internal_collision_count"]
        + diagnostics["negative_only_valid_pair_collision_count"]
        + diagnostics["negative_only_parse_fault_count"]
    )
    summary["negative_only_amendment_fault_count"] = amendment_faults
    if amendment_faults:
        summary["integrity_gate"] = "FAIL"
        summary["overall_gate"] = "FAIL"
    return rows, summary


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
    _v1._write_jsonl(args.rows_out, rows)
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        _v1._canonical(
            {
                "rows": len(rows),
                "negative_only_exclusions": summary[
                    "negative_only_no_live_exclusion_count"
                ],
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
