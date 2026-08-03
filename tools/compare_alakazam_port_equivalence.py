"""Compare the frozen Alakazam policy and the new-deck v0 port on saved replays.

This is a behavioral callback comparison, not a counterfactual engine rollout.
Every saved ACTIVE callback is evaluated, including callbacks whose following
record does not contain a usable recorded action.  The immediate following
saved observation is reported only as recorded-state evidence.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from ptcg_common import ensure_engine_on_path, load_agent, read_deck
from rl_ptcg.label_replay_rollout import target_seat_for_deck


REMOVED_ONLY = {142, 858, 1156, 1161, 1264}
ADDED_ONLY = {1184, 1197, 1266}
OLD_MAX = {743: 3, 1081: 3, 1182: 2}
FALLBACK_CLASSES = {
    "ADMISSIBILITY_REJECT",
    "PLACEHOLDER_PARENT_FALLBACK",
    "EMERGENCY_LOWEST_LEGAL",
}
CARD_ID_KEYS = {
    "id",
    "cardId",
    "cardIdActive",
    "cardIdBench",
}


def stable_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def card_rows(value: Any, rows: list[tuple[int, int | None]]) -> None:
    if isinstance(value, dict):
        card_id = None
        for key in CARD_ID_KEYS:
            raw = value.get(key)
            if isinstance(raw, int) and not isinstance(raw, bool):
                card_id = raw
                break
        if card_id is not None:
            serial = value.get("serial")
            rows.append(
                (
                    card_id,
                    serial
                    if isinstance(serial, int) and not isinstance(serial, bool)
                    else None,
                )
            )
        for child in value.values():
            card_rows(child, rows)
    elif isinstance(value, list):
        for child in value:
            card_rows(child, rows)


def comparability(observation: dict[str, Any]) -> tuple[str, str]:
    rows: list[tuple[int, int | None]] = []
    card_rows(observation, rows)
    ids = {card_id for card_id, _ in rows}
    exclusive = sorted(ids & (REMOVED_ONLY | ADDED_ONLY))
    if exclusive:
        return (
            "NON_COMPARABLE",
            "VISIBLE_EXCLUSIVE_CARD_IDS=" + "|".join(map(str, exclusive)),
        )

    unique_cards: set[tuple[int, Any]] = set()
    anonymous_counter = 0
    for card_id, serial in rows:
        if serial is None:
            anonymous_counter += 1
            unique_cards.add((card_id, f"anon:{anonymous_counter}"))
        else:
            unique_cards.add((card_id, serial))
    excess = []
    for card_id, maximum in OLD_MAX.items():
        observed = sum(row[0] == card_id for row in unique_cards)
        if observed > maximum:
            excess.append(f"{card_id}:{observed}>{maximum}")
    if excess:
        return "NON_COMPARABLE", "VISIBLE_COUNT_EXCESS=" + "|".join(excess)
    return "COMPARABLE_SHARED_51", ""


def is_valid(observation: dict[str, Any], action: Any) -> bool:
    select = observation.get("select") or {}
    options = select.get("option") or []
    minimum = int(select.get("minCount", 0))
    maximum = int(select.get("maxCount", 0))
    return (
        isinstance(action, list)
        and minimum <= len(action) <= maximum
        and len(action) == len(set(action))
        and all(
            isinstance(index, int)
            and not isinstance(index, bool)
            and 0 <= index < len(options)
            for index in action
        )
    )


def trace_after(agent: Any) -> dict[str, Any]:
    adapter = getattr(agent, "module", None)
    source = getattr(adapter, "_module", adapter)
    integrated = getattr(source, "_integrated", None)
    core = getattr(integrated, "core", None)
    trace = getattr(core, "INTEGRATED_LATEST_TRACE", None)
    return copy.deepcopy(trace) if isinstance(trace, dict) else {}


def v0_trace_after(agent: Any) -> dict[str, Any]:
    adapter = getattr(agent, "module", None)
    source = getattr(adapter, "_module", adapter)
    trace = getattr(source, "LAST_V0_PORT_TRACE", None)
    return copy.deepcopy(trace) if isinstance(trace, dict) else {}


def trace_field(trace: dict[str, Any], name: str) -> str:
    value = trace.get(name)
    if value is None:
        return ""
    return stable_json(value) if isinstance(value, (dict, list, tuple)) else str(value)


def selected_semantic(observation: dict[str, Any], action: list[int]) -> str:
    options = (observation.get("select") or {}).get("option") or []
    selected = [options[index] for index in action if 0 <= index < len(options)]
    return stable_json(selected)


def active_callbacks(
    replay: dict[str, Any], seat: int
) -> list[tuple[int, dict[str, Any], Any, str, dict[str, Any] | None]]:
    """Return every saved ACTIVE callback and its immediate following record."""
    callbacks = []
    steps = replay.get("steps") or []
    for step, pair in enumerate(steps):
        if not isinstance(pair, list) or seat >= len(pair):
            continue
        entry = pair[seat]
        observation = entry.get("observation") if isinstance(entry, dict) else None
        if (
            not isinstance(entry, dict)
            or entry.get("status") != "ACTIVE"
            or not isinstance(observation, dict)
            or not isinstance(observation.get("select"), dict)
        ):
            continue

        recorded: Any = None
        recorded_status = "MISSING_FOLLOWING_STEP"
        next_observation = None
        if step + 1 < len(steps):
            following_pair = steps[step + 1]
            if not isinstance(following_pair, list) or seat >= len(following_pair):
                recorded_status = "MISSING_FOLLOWING_SEAT_RECORD"
            else:
                following = following_pair[seat]
                if not isinstance(following, dict):
                    recorded_status = "FOLLOWING_RECORD_NOT_OBJECT"
                else:
                    candidate = following.get("observation")
                    if isinstance(candidate, dict):
                        next_observation = candidate
                    if "action" not in following:
                        recorded_status = "MISSING_FOLLOWING_ACTION"
                    else:
                        recorded = following.get("action")
                        if not isinstance(recorded, list):
                            recorded_status = "FOLLOWING_ACTION_NOT_LIST"
                        elif not recorded:
                            recorded_status = "FOLLOWING_ACTION_EMPTY"
                        else:
                            recorded = list(recorded)
                            recorded_status = "PRESENT"

        callbacks.append(
            (
                step,
                observation,
                recorded,
                recorded_status,
                next_observation,
            )
        )
    return callbacks


def load_pair(left_dir: Path, right_dir: Path, suffix: str) -> tuple[Any, Any]:
    left = load_agent(left_dir, f"alakazam_equiv_left_{suffix}")
    right = load_agent(right_dir, f"alakazam_equiv_right_{suffix}")
    return left, right


def replay_result(replay: dict[str, Any], target_seat: int) -> str:
    rewards = replay.get("rewards")
    if isinstance(rewards, list) and target_seat < len(rewards):
        value = rewards[target_seat]
        if value == 1:
            return "WIN"
        if value == -1:
            return "LOSS"
        if value == 0:
            return "DRAW"
    return "UNKNOWN"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--episode-csv", type=Path, required=True)
    parser.add_argument("--left", type=Path, required=True)
    parser.add_argument("--right", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-episode-csv-sha256")
    args = parser.parse_args()

    ensure_engine_on_path(args.engine_dir)
    left_dir = args.left.resolve()
    right_dir = args.right.resolve()
    episode_csv = args.episode_csv.resolve()
    replay_root = args.replay_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.expected_episode_csv_sha256:
        actual = sha256(episode_csv)
        if actual.lower() != args.expected_episode_csv_sha256.lower():
            raise ValueError(
                f"episode CSV hash mismatch: {actual} != "
                f"{args.expected_episode_csv_sha256}"
            )

    with episode_csv.open(newline="", encoding="utf-8-sig") as handle:
        episode_rows = [
            row
            for row in csv.DictReader(handle)
            if row.get("type") == "EPISODE_TYPE_PUBLIC"
        ]
    episode_rows.sort(key=lambda row: int(row["episode_id"]))
    left_deck = read_deck(left_dir / "deck.csv")

    detail_rows: list[dict[str, Any]] = []
    replay_manifest: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []
    for replay_index, episode_row in enumerate(episode_rows):
        episode_id = int(episode_row["episode_id"])
        replay_path = replay_root / f"episode_{episode_id}_replay.json"
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        replay_sha = sha256(replay_path)
        target_seat = target_seat_for_deck(replay, left_deck)
        replay_manifest.append(
            {
                "episode_id": episode_id,
                "target_seat": target_seat,
                "opponent_team": episode_row.get("opponent_team", ""),
                "replay": str(replay_path),
                "sha256": replay_sha,
            }
        )
        decisions = active_callbacks(replay, target_seat)
        left, right = load_pair(left_dir, right_dir, str(replay_index))
        result = replay_result(replay, target_seat)

        for decision_index, (
            step,
            observation,
            recorded,
            recorded_action_status,
            next_observation,
        ) in enumerate(decisions):
            next_hash = (
                canonical_hash(next_observation)
                if next_observation is not None
                else ""
            )
            comparison_status, non_comparable_reason = comparability(observation)
            legal_options = (observation.get("select") or {}).get("option") or []
            left_action: list[int] | None = None
            right_action: list[int] | None = None
            left_exception = ""
            right_exception = ""

            started = time.perf_counter_ns()
            try:
                left_action = left(copy.deepcopy(observation))
            except Exception as exc:  # evidence collection must retain the failure row
                left_exception = f"{type(exc).__name__}: {exc}"
            left_ns = time.perf_counter_ns() - started
            left_trace = trace_after(left)

            started = time.perf_counter_ns()
            try:
                right_action = right(copy.deepcopy(observation))
            except Exception as exc:  # evidence collection must retain the failure row
                right_exception = f"{type(exc).__name__}: {exc}"
            right_ns = time.perf_counter_ns() - started
            right_trace = trace_after(right)
            port_trace = v0_trace_after(right)

            if left_exception or right_exception:
                exceptions.append(
                    {
                        "episode_id": episode_id,
                        "step": step,
                        "left_exception": left_exception,
                        "right_exception": right_exception,
                    }
                )
            actions_equal = (
                left_action is not None
                and right_action is not None
                and left_action == right_action
            )
            recorded_action_present = recorded_action_status == "PRESENT"
            current = observation.get("current") or {}
            select = observation.get("select") or {}
            detail_rows.append(
                {
                    "episode_id": episode_id,
                    "opponent_team": episode_row.get("opponent_team", ""),
                    "target_seat": target_seat,
                    "recorded_result": result,
                    "replay_step": step,
                    "decision_index": decision_index,
                    "turn": current.get("turn", ""),
                    "context": select.get("context", ""),
                    "comparability": comparison_status,
                    "non_comparable_reason": non_comparable_reason,
                    "legal_option_count": len(legal_options),
                    "legal_action_set_hash": canonical_hash(legal_options),
                    "recorded_action": stable_json(recorded),
                    "recorded_action_status": recorded_action_status,
                    "left_matches_recorded_action": (
                        int(left_action == recorded)
                        if recorded_action_present
                        else ""
                    ),
                    "right_matches_recorded_action": (
                        int(right_action == recorded)
                        if recorded_action_present
                        else ""
                    ),
                    "left_action": stable_json(left_action),
                    "right_action": stable_json(right_action),
                    "actions_equal": int(actions_equal),
                    "left_selected_semantic": (
                        selected_semantic(observation, left_action)
                        if left_action is not None
                        else ""
                    ),
                    "right_selected_semantic": (
                        selected_semantic(observation, right_action)
                        if right_action is not None
                        else ""
                    ),
                    "next_state_status": (
                        "RECORDED_NEXT_STATE_SHARED"
                        if actions_equal
                        else "COUNTERFACTUAL_NOT_AVAILABLE"
                    ),
                    "next_recorded_observation_hash": next_hash,
                    "left_trace_classification": trace_field(
                        left_trace, "classification"
                    ),
                    "left_trace_kind": trace_field(left_trace, "kind"),
                    "left_reason": trace_field(left_trace, "reason"),
                    "right_trace_classification": trace_field(
                        right_trace, "classification"
                    ),
                    "right_trace_kind": trace_field(right_trace, "kind"),
                    "right_reason": trace_field(right_trace, "reason"),
                    "right_port_reason_tags": trace_field(
                        port_trace, "reason_tags"
                    ),
                    "left_fallback": int(
                        left_trace.get("classification") in FALLBACK_CLASSES
                    ),
                    "right_fallback": int(
                        right_trace.get("classification") in FALLBACK_CLASSES
                    ),
                    "left_valid": int(
                        left_action is not None
                        and is_valid(observation, left_action)
                    ),
                    "right_valid": int(
                        right_action is not None
                        and is_valid(observation, right_action)
                    ),
                    "left_exception": left_exception,
                    "right_exception": right_exception,
                    "left_decision_ns": left_ns,
                    "right_decision_ns": right_ns,
                }
            )

    fields = list(detail_rows[0]) if detail_rows else []
    detail_path = output_dir / "callback_comparison.csv"
    with detail_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(detail_rows)
    manifest_path = output_dir / "replay_manifest.csv"
    manifest_fields = list(replay_manifest[0]) if replay_manifest else []
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=manifest_fields)
        writer.writeheader()
        writer.writerows(replay_manifest)

    comparable = [
        row for row in detail_rows if row["comparability"] == "COMPARABLE_SHARED_51"
    ]
    summary = {
        "schema_version": "alakazam-v0-port-equivalence-v2",
        "left": str(left_dir),
        "right": str(right_dir),
        "episode_csv": str(episode_csv),
        "episode_csv_sha256": sha256(episode_csv),
        "replays": len(replay_manifest),
        "callbacks": len(detail_rows),
        "recorded_action_status_counts": {
            status: sum(
                row["recorded_action_status"] == status for row in detail_rows
            )
            for status in sorted(
                {row["recorded_action_status"] for row in detail_rows}
            )
        },
        "left_recorded_action_match_count": sum(
            row["left_matches_recorded_action"] == 1 for row in detail_rows
        ),
        "right_recorded_action_match_count": sum(
            row["right_matches_recorded_action"] == 1 for row in detail_rows
        ),
        "comparable_callbacks": len(comparable),
        "non_comparable_callbacks": len(detail_rows) - len(comparable),
        "all_action_difference_count": sum(
            not bool(row["actions_equal"]) for row in detail_rows
        ),
        "comparable_action_difference_count": sum(
            not bool(row["actions_equal"]) for row in comparable
        ),
        "left_invalid_count": sum(not bool(row["left_valid"]) for row in detail_rows),
        "right_invalid_count": sum(
            not bool(row["right_valid"]) for row in detail_rows
        ),
        "exception_count": len(exceptions),
        "left_fallback_count": sum(row["left_fallback"] for row in detail_rows),
        "right_fallback_count": sum(row["right_fallback"] for row in detail_rows),
        "left_mean_decision_ns": (
            sum(row["left_decision_ns"] for row in detail_rows) / len(detail_rows)
            if detail_rows
            else None
        ),
        "right_mean_decision_ns": (
            sum(row["right_decision_ns"] for row in detail_rows) / len(detail_rows)
            if detail_rows
            else None
        ),
        "left_p95_decision_ns": (
            sorted(row["left_decision_ns"] for row in detail_rows)[
                max(0, (95 * len(detail_rows) + 99) // 100 - 1)
            ]
            if detail_rows
            else None
        ),
        "right_p95_decision_ns": (
            sorted(row["right_decision_ns"] for row in detail_rows)[
                max(0, (95 * len(detail_rows) + 99) // 100 - 1)
            ]
            if detail_rows
            else None
        ),
        "detail_csv": str(detail_path),
        "detail_csv_sha256": sha256(detail_path),
        "replay_manifest_csv": str(manifest_path),
        "replay_manifest_csv_sha256": sha256(manifest_path),
        "exceptions": exceptions,
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
