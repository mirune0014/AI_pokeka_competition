#!/usr/bin/env python3
"""Independent mechanical audit for the frozen v4 C4 metric schedule."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
CANDIDATE_CLOSURE = (
    "FA46897E4762CB1B55C9DED36EC3A06CA9CF4F9FE7C4233BE8414CC25D86DF4E"
)
RULE_VERSION = "V4_WALL_SHADOW_FIX6"
BASE_SEEDS = (202608500, 202608510, 202608520, 202608530, 202608540)
MEGA_SEEDS = (202609500, 202609510, 202609520, 202609530, 202609540)

SUITES = (
    (
        "alakazam_staged_20260729/metrics/"
        "formal_v4_c4_wall_shadow_fix6_trace_a",
        ("marnie", "cynthia", "alakazam_mirror"),
        BASE_SEEDS,
    ),
    (
        "alakazam_staged_20260729/metrics/"
        "formal_v4_c4_wall_shadow_fix6_trace_b_rocket_retry2",
        ("rocket_mewtwo_spidops_proxy",),
        BASE_SEEDS,
    ),
    (
        "alakazam_staged_20260729/metrics/"
        "formal_v4_c4_wall_shadow_fix6_trace_b_kangaskhan_retry2",
        ("kangaskhan_crustle",),
        BASE_SEEDS,
    ),
    (
        "alakazam_staged_20260729/metrics/"
        "formal_v4_c4_wall_shadow_fix6_trace_c",
        ("historical_silver", "direct_frozen"),
        BASE_SEEDS,
    ),
    (
        "alakazam_staged_20260729/metrics/"
        "formal_v4_c4_wall_shadow_fix6_megalucario_reach1",
        ("mega_lucario_aib4", "mega_lucario_fujiborozoukin"),
        MEGA_SEEDS,
    ),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def json_file(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{number}: expected a JSON object")
            rows.append(value)
    return rows


def expected_blocks(
    opponents: tuple[str, ...], seeds: tuple[int, ...]
) -> set[tuple[str, int, int]]:
    return {
        (opponent, seat, seed)
        for opponent in opponents
        for seed in seeds
        for seat in (0, 1)
    }


def selected_class(trace: dict[str, Any]) -> str | None:
    rows = trace.get("candidate_rows")
    if not isinstance(rows, list):
        return None
    classes = {
        row.get("certification")
        for row in rows
        if isinstance(row, dict)
        and row.get("certification") in ("STRICT", "PRESERVE_CHANCE")
    }
    if classes == {"STRICT"}:
        return "STRICT"
    if classes == {"PRESERVE_CHANCE"}:
        return "PRESERVE_CHANCE"
    if not classes:
        return None
    return "CONFLICT"


def duplicate_values(values: Any) -> set[str]:
    if not isinstance(values, list):
        return {"__INVALID_LIST__"}
    return {
        value
        for value in values
        if isinstance(value, str) and values.count(value) > 1
    }


def no_live_non_evidence(trace: dict[str, Any]) -> bool:
    if (
        trace.get("decision_point") is None
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
    if any(not isinstance(row, dict) for row in rows):
        return False
    run, reusable, sacrifice, fallback = rows
    if (
        run.get("kind") != "RUN_AWAY_ACCELERATION"
        or run.get("certification")
        not in ("PRESERVE_CHANCE", "REJECTED", "UNAVAILABLE")
        or reusable.get("kind") != "CERTIFIED_REUSABLE_WALL"
        or reusable.get("certification") not in ("REJECTED", "UNAVAILABLE")
        or sacrifice.get("kind") != "CERTIFIED_SACRIFICE_WALL"
        or sacrifice.get("certification") not in ("REJECTED", "UNAVAILABLE")
        or fallback.get("kind") != "NO_WALL_OR_UNKNOWN"
        or fallback.get("certification") != "AVAILABLE"
        or fallback.get("wall_class") != "PARENT_FALLBACK"
        or fallback.get("semantic_action_key")
        != trace.get("semantic_parent_action_keys")
        or any(row.get("certification") == "STRICT" for row in rows)
    ):
        return False
    trace_codes = set(trace.get("rejection_codes") or [])
    trace_unsupported = set(trace.get("unsupported_reasons") or [])
    if (
        "NO_LIVE_PROTECTED_LINE" not in trace_codes
        or "NO_LIVE_PROTECTED_LINE" not in trace_unsupported
    ):
        return False
    pair = trace.get("pair_material")
    expose = trace.get("expose_projection")
    wall = trace.get("wall_projection")
    if (
        not isinstance(pair, dict)
        or pair.get("protected_serial") is not None
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
        duplicates = duplicate_values(row.get("rejection_codes"))
        if duplicates not in (set(), {"NO_LIVE_PROTECTED_LINE"}):
            return False
        if duplicates and (
            row["rejection_codes"].count("NO_LIVE_PROTECTED_LINE") != 2
        ):
            return False
    return not duplicate_values(run.get("rejection_codes")) and not (
        duplicate_values(fallback.get("rejection_codes"))
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collector-summary", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    errors: list[str] = []
    suite_rows = []
    observed_blocks: set[tuple[str, int, int]] = set()
    expected_all_blocks: set[tuple[str, int, int]] = set()
    game_keys: set[tuple[str, int, int, int, int]] = set()
    callback_keys: set[tuple[str, int, int, int, int]] = set()
    strict_pairs: set[str] = set()
    chance_pairs: set[str] = set()
    raw_declared_chance_pairs: set[str] = set()
    pair_conflicts: set[str] = set()
    negative_pair_evidence: dict[str, set[str]] = {}
    counts: Counter[str] = Counter()
    opponent_classes: dict[str, Counter[str]] = {}

    for relative, opponents, seeds in SUITES:
        root = REPO / relative
        expected = expected_blocks(opponents, seeds)
        expected_all_blocks.update(expected)
        manifest_path = root / "suite_manifest.json"
        execution_path = root / "suite_execution_summary.json"
        ledger_path = root / "block_ledger.jsonl"
        manifest = json_file(manifest_path)
        execution = json_file(execution_path)
        ledger = jsonl(ledger_path)

        manifest_opponents = {
            row.get("name")
            for row in manifest.get("opponents", [])
            if isinstance(row, dict)
        }
        if manifest.get("schema_version") != "alakazam-staged-metrics-v1":
            errors.append(f"{relative}: manifest schema")
        if manifest.get("games_per_block") != 10:
            errors.append(f"{relative}: games_per_block")
        if manifest.get("max_steps") != 1000:
            errors.append(f"{relative}: max_steps")
        if tuple(manifest.get("seats", [])) != (0, 1):
            errors.append(f"{relative}: seats")
        if set(manifest.get("seed_bases", [])) != set(seeds):
            errors.append(f"{relative}: seed bases")
        if manifest_opponents != set(opponents):
            errors.append(f"{relative}: opponents")
        versions = manifest.get("versions")
        if (
            not isinstance(versions, list)
            or len(versions) != 1
            or versions[0].get("name") != "c4"
        ):
            errors.append(f"{relative}: versions")
        if execution.get("all_blocks_complete") is not True:
            errors.append(f"{relative}: all_blocks_complete")
        if execution.get("blocks") != len(expected):
            errors.append(f"{relative}: execution block count")
        if execution.get("complete_blocks") != len(expected):
            errors.append(f"{relative}: complete block count")
        if execution.get("failed_or_partial_blocks") != 0:
            errors.append(f"{relative}: failed or partial blocks")
        if len(ledger) != len(expected):
            errors.append(f"{relative}: ledger rows")

        local_blocks: set[tuple[str, int, int]] = set()
        local_games = 0
        local_callbacks = 0
        for block in ledger:
            block_key = (
                block.get("opponent"),
                block.get("seat"),
                block.get("seed_base"),
            )
            if block_key in local_blocks:
                errors.append(f"{relative}: duplicate block {block_key}")
            local_blocks.add(block_key)
            observed_blocks.add(block_key)
            if block.get("block_complete") is not True:
                errors.append(f"{relative}: incomplete block {block_key}")
            if block.get("return_code") != 0:
                errors.append(f"{relative}: nonzero block {block_key}")
            if block.get("timed_out") is not False:
                errors.append(f"{relative}: timeout block {block_key}")
            status = block.get("summary_status")
            if (
                not isinstance(status, dict)
                or status.get("rows") != 10
                or status.get("expected_rows") != 10
                or status.get("complete_game_index_set") is not True
                or status.get("parse_errors") != []
                or status.get("game_indices") != list(range(10))
            ):
                errors.append(f"{relative}: summary status {block_key}")

            summary_path = Path(str(block.get("summary")))
            stderr_path = Path(str(block.get("stderr")))
            stdout_path = Path(str(block.get("stdout")))
            for path, field in (
                (summary_path, "summary_sha256"),
                (stderr_path, "stderr_sha256"),
                (stdout_path, "stdout_sha256"),
            ):
                if not path.is_file():
                    errors.append(f"{relative}: missing {path}")
                elif sha256(path) != str(block.get(field, "")).upper():
                    errors.append(f"{relative}: hash mismatch {path}")
            if stderr_path.is_file() and stderr_path.stat().st_size != 0:
                errors.append(f"{relative}: nonempty stderr {block_key}")

            summaries = jsonl(summary_path)
            if len(summaries) != 10:
                errors.append(f"{relative}: summary row count {block_key}")
                continue
            for row in summaries:
                game = row.get("game")
                seed = row.get("seed")
                game_key = (*block_key, game, seed)
                if game_key in game_keys:
                    errors.append(f"duplicate game {game_key}")
                game_keys.add(game_key)
                local_games += 1
                if (
                    type(game) is not int
                    or game not in range(10)
                    or seed != block_key[2] + game
                    or row.get("started") is not True
                    or row.get("hit_max_steps") is not False
                    or row.get("action_errors") != 0
                    or type(row.get("steps")) is not int
                    or row["steps"] > 1000
                ):
                    errors.append(f"{relative}: invalid game {game_key}")
                counts["action_errors"] += int(row.get("action_errors") or 0)
                counts["max_step_hits"] += int(row.get("hit_max_steps") is True)

                sidecar = (
                    root
                    / "runs"
                    / "c4"
                    / str(block_key[0])
                    / f"seed_{block_key[2]}"
                    / f"seat_{block_key[1]}"
                    / "sidecars"
                    / f"game_{game:04d}.jsonl"
                )
                if not sidecar.is_file():
                    errors.append(f"{relative}: missing sidecar {game_key}")
                    continue
                events = jsonl(sidecar)
                starts: dict[int, dict[str, Any]] = {}
                ends: dict[int, dict[str, Any]] = {}
                for event in events:
                    ordinal = event.get("callback_ordinal")
                    identity = (
                        event.get("opponent") == block_key[0]
                        and event.get("policy_seat") == block_key[1]
                        and event.get("seed_base") == block_key[2]
                        and event.get("seed") == seed
                        and event.get("game") == game
                        and event.get("version") == "c4"
                        and type(ordinal) is int
                    )
                    if not identity:
                        counts["sidecar_identity_faults"] += 1
                    if event.get("event") == "CALL_START":
                        if ordinal in starts:
                            counts["duplicate_callback_starts"] += 1
                        starts[ordinal] = event
                    elif event.get("event") == "CALL_END":
                        if ordinal in ends:
                            counts["duplicate_callback_ends"] += 1
                        ends[ordinal] = event
                    else:
                        counts["unknown_sidecar_events"] += 1
                if set(starts) != set(ends) or set(starts) != set(range(len(starts))):
                    counts["callback_pair_faults"] += 1
                counts["callback_starts"] += len(starts)
                counts["callback_ends"] += len(ends)
                local_callbacks += len(ends)

                for ordinal, end in ends.items():
                    callback_key = (
                        block_key[0],
                        block_key[1],
                        seed,
                        game,
                        ordinal,
                    )
                    if callback_key in callback_keys:
                        counts["duplicate_global_callback_keys"] += 1
                    callback_keys.add(callback_key)
                    trace = end.get("version_trace")
                    if not isinstance(trace, dict):
                        counts["missing_traces"] += 1
                        continue
                    if trace.get("rule_version") != RULE_VERSION:
                        counts["rule_faults"] += 1
                    if trace.get("candidate_closure_sha256") != CANDIDATE_CLOSURE:
                        counts["closure_faults"] += 1
                    if trace.get("metric_exception") is not None:
                        counts["metric_exceptions"] += 1
                    if trace.get("outcome_status") == "CANDIDATE_APPLIED":
                        counts["candidate_applied"] += 1
                    if trace.get("outcome_status") == "PARENT_AGREEMENT":
                        counts["parent_agreements"] += 1
                    action = end.get("selected_action")
                    action_values = (
                        trace.get("raw_parent_action"),
                        trace.get("parent_action"),
                        trace.get("applied_action"),
                        action,
                    )
                    flags = trace.get("action_identity")
                    if (
                        any(type(value) is not list for value in action_values)
                        or not all(value == action for value in action_values)
                        or not isinstance(flags, dict)
                        or flags.get("value_equal") is not True
                        or flags.get("type_equal") is not True
                        or flags.get("order_equal") is not True
                        or flags.get("returned_parent_object_unchanged") is not True
                    ):
                        counts["action_identity_faults"] += 1

                    decision_class = selected_class(trace)
                    pair_id = trace.get("pair_id")
                    if (
                        decision_class == "PRESERVE_CHANCE"
                        and isinstance(pair_id, str)
                    ):
                        raw_declared_chance_pairs.add(pair_id)
                    negative = no_live_non_evidence(trace)
                    if negative:
                        counts["no_live_non_evidence_callbacks"] += 1
                        if isinstance(pair_id, str):
                            evidence = json.dumps(
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
                                    "decision_point": trace.get(
                                        "decision_point"
                                    ),
                                    "semantic_parent_action_keys": trace.get(
                                        "semantic_parent_action_keys"
                                    ),
                                },
                                sort_keys=True,
                                separators=(",", ":"),
                            )
                            negative_pair_evidence.setdefault(
                                pair_id, set()
                            ).add(evidence)
                    elif (
                        decision_class == "STRICT"
                        and isinstance(pair_id, str)
                    ):
                        strict_pairs.add(pair_id)
                    elif (
                        decision_class == "PRESERVE_CHANCE"
                        and isinstance(pair_id, str)
                    ):
                        chance_pairs.add(pair_id)
                    elif decision_class == "CONFLICT":
                        if isinstance(pair_id, str):
                            pair_conflicts.add(pair_id)
                        counts["decision_class_conflicts"] += 1
                    if trace.get("protected_line") is None:
                        if (
                            not negative
                            and trace.get("decision_point") is not None
                        ):
                            counts["unexpected_null_protected_line"] += 1
                    for candidate in trace.get("candidate_rows", []):
                        if not isinstance(candidate, dict):
                            continue
                        codes = candidate.get("rejection_codes")
                        if isinstance(codes, list) and len(codes) != len(set(codes)):
                            counts["rows_with_duplicate_rejection_codes"] += 1

                    bucket = opponent_classes.setdefault(
                        str(block_key[0]), Counter()
                    )
                    bucket[str(decision_class)] += 1

        if local_blocks != expected:
            errors.append(f"{relative}: exact block schedule mismatch")
        suite_rows.append(
            {
                "suite": relative,
                "block_count": len(local_blocks),
                "game_count": local_games,
                "callback_end_count": local_callbacks,
                "ledger_sha256": sha256(ledger_path),
                "manifest_sha256": sha256(manifest_path),
                "execution_summary_sha256": sha256(execution_path),
            }
        )

    if observed_blocks != expected_all_blocks:
        errors.append("union block schedule mismatch")
    if len(game_keys) != 900:
        errors.append(f"union game count {len(game_keys)}")
    fatal_counter_keys = (
        "action_errors",
        "max_step_hits",
        "sidecar_identity_faults",
        "duplicate_callback_starts",
        "duplicate_callback_ends",
        "unknown_sidecar_events",
        "callback_pair_faults",
        "duplicate_global_callback_keys",
        "missing_traces",
        "rule_faults",
        "closure_faults",
        "metric_exceptions",
        "candidate_applied",
        "action_identity_faults",
        "decision_class_conflicts",
        "unexpected_null_protected_line",
    )
    for key in fatal_counter_keys:
        if counts[key]:
            errors.append(f"{key}={counts[key]}")
    negative_internal_collisions = {
        pair_id
        for pair_id, evidence in negative_pair_evidence.items()
        if len(evidence) != 1
    }
    negative_valid_collisions = set(negative_pair_evidence) & (
        strict_pairs | chance_pairs
    )
    if negative_internal_collisions:
        errors.append(
            "negative_internal_collisions="
            f"{len(negative_internal_collisions)}"
        )
    if negative_valid_collisions:
        errors.append(
            "negative_valid_collisions="
            f"{len(negative_valid_collisions)}"
        )

    collector_comparison = None
    if args.collector_summary is not None:
        collector = json_file(args.collector_summary)
        collector_comparison = {
            "path": str(args.collector_summary.resolve()),
            "sha256": sha256(args.collector_summary),
            "matches": {
                "input_file_count": collector.get("input_file_count") == 900,
                "callback_start_count": collector.get("callback_start_count")
                == counts["callback_starts"],
                "callback_end_count": collector.get("callback_end_count")
                == counts["callback_ends"],
                "strict_unique_state_count": collector.get(
                    "strict_unique_state_count"
                )
                == len(strict_pairs),
                "preserve_chance_unique_state_count": collector.get(
                    "preserve_chance_unique_state_count"
                )
                == len(chance_pairs),
                "natural_parent_agreement_count": collector.get(
                    "natural_parent_agreement_count"
                )
                == counts["parent_agreements"],
                "action_identity_failure_count": collector.get(
                    "action_identity_failure_count"
                )
                == counts["action_identity_faults"],
                "metric_exception_count": collector.get(
                    "metric_exception_count"
                )
                == counts["metric_exceptions"],
                "candidate_applied_count": collector.get(
                    "candidate_applied_count"
                )
                == counts["candidate_applied"],
                "negative_only_no_live_exclusion_count": collector.get(
                    "negative_only_no_live_exclusion_count"
                )
                == counts["no_live_non_evidence_callbacks"],
                "negative_only_duplicate_diagnostic_row_count": collector.get(
                    "negative_only_duplicate_diagnostic_row_count"
                )
                == counts["rows_with_duplicate_rejection_codes"],
                "negative_only_internal_collision_count": collector.get(
                    "negative_only_internal_collision_count"
                )
                == len(negative_internal_collisions),
                "negative_only_valid_pair_collision_count": collector.get(
                    "negative_only_valid_pair_collision_count"
                )
                == len(negative_valid_collisions),
            },
        }
        if not all(collector_comparison["matches"].values()):
            errors.append("collector comparison mismatch")

    report = {
        "schema_version": "v4-c4-root-metric-audit-v1",
        "status": "PASS" if not errors else "FAIL",
        "candidate_closure_sha256": CANDIDATE_CLOSURE,
        "expected_games": 900,
        "observed_games": len(game_keys),
        "expected_blocks": 90,
        "observed_blocks": len(observed_blocks),
        "callback_start_count": counts["callback_starts"],
        "callback_end_count": counts["callback_ends"],
        "strict_unique_pair_count": len(strict_pairs),
        "preserve_chance_unique_pair_count": len(chance_pairs),
        "raw_declared_preserve_chance_unique_pair_count": len(
            raw_declared_chance_pairs
        ),
        "parent_agreement_callback_count": counts["parent_agreements"],
        "no_live_non_evidence_callback_count": counts[
            "no_live_non_evidence_callbacks"
        ],
        "rows_with_duplicate_rejection_codes": counts[
            "rows_with_duplicate_rejection_codes"
        ],
        "negative_only_internal_collision_count": len(
            negative_internal_collisions
        ),
        "negative_only_valid_pair_collision_count": len(
            negative_valid_collisions
        ),
        "counts": dict(sorted(counts.items())),
        "opponent_decision_class_callbacks": {
            opponent: dict(sorted(bucket.items()))
            for opponent, bucket in sorted(opponent_classes.items())
        },
        "suites": suite_rows,
        "collector_comparison": collector_comparison,
        "errors": errors,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "games": report["observed_games"],
                "blocks": report["observed_blocks"],
                "callbacks": report["callback_end_count"],
                "strict": report["strict_unique_pair_count"],
                "chance": report["preserve_chance_unique_pair_count"],
                "errors": len(errors),
            },
            sort_keys=True,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
