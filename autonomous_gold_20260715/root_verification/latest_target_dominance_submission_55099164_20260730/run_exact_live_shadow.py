from __future__ import annotations

import copy
import collections
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from rl_ptcg.label_replay_rollout import replay_decisions


HERE = Path(__file__).resolve().parent
EVIDENCE = (
    ROOT
    / "autonomous_gold_20260715"
    / "evidence"
    / "latest_target_dominance_submission_refresh_20260730"
)
CANDIDATE_DIR = (
    ROOT
    / "autonomous_gold_20260715"
    / "candidates"
    / "archaludon_cumulative_public_one_turn_target_dominance_v1"
)
PARENT_DIR = (
    ROOT
    / "autonomous_gold_20260715"
    / "candidates"
    / "archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2"
)
EPISODES_CSV = EVIDENCE / "submission_55099164_20260730_episodes.csv"
HASH_INVENTORY = EVIDENCE / "sha256_inventory.csv"

EXPECTED_EPISODES_SHA = (
    "5F568156AE4F77F6D0F75ABA210B1202C92FD2E42512A46B5FA760453690A0DB"
)
EXPECTED_CANDIDATE_SHA = (
    "6504E0E3EA69D59EAB5F9A73E306D70695A0E76ECA8D347C97F1EB43AEE31B7A"
)
EXPECTED_PARENT_SHA = (
    "DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8"
)
NEW_RULE_ID = "PUBLIC_ONE_TURN_TARGET_DOMINANCE_WITH_EPHEMERAL_CHIP_VETO_V1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reset_module(module, module_dir: Path) -> None:
    old_cwd = Path.cwd()
    try:
        os.chdir(module_dir)
        deck = module.agent(
            {
                "select": None,
                "logs": [],
                "current": None,
                "search_begin_input": None,
            }
        )
    finally:
        os.chdir(old_cwd)
    if not isinstance(deck, list) or len(deck) != 60:
        raise AssertionError(("deck request", module_dir, len(deck)))
    if hasattr(module, "drain_cumulative_telemetry"):
        module.drain_cumulative_telemetry()


def valid(observation, selected) -> bool:
    return (
        isinstance(selected, list)
        and observation.select.minCount <= len(selected) <= observation.select.maxCount
        and len(selected) == len(set(selected))
        and all(
            isinstance(position, int)
            and 0 <= position < len(observation.select.option)
            for position in selected
        )
    )


def semantic(module, observation, selected):
    result = []
    for position in selected:
        option = observation.select.option[position]
        card = module.option_card(observation, option)
        target = module.option_target(observation, option)
        result.append(
            {
                "type": int(option.type),
                "context": int(observation.select.context),
                "card_id": getattr(card, "id", None),
                "serial": getattr(card, "serial", None),
                "target_id": getattr(target, "id", None),
                "target_serial": getattr(target, "serial", None),
                "attack_id": getattr(option, "attackId", None),
            }
        )
    return result


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if sha256(EPISODES_CSV) != EXPECTED_EPISODES_SHA:
        raise AssertionError("episode CSV changed")
    if sha256(CANDIDATE_DIR / "main.py") != EXPECTED_CANDIDATE_SHA:
        raise AssertionError("candidate changed")
    if sha256(PARENT_DIR / "main.py") != EXPECTED_PARENT_SHA:
        raise AssertionError("parent changed")

    with HASH_INVENTORY.open(newline="", encoding="utf-8-sig") as handle:
        inventory = {row["file"]: row for row in csv.DictReader(handle)}
    with EPISODES_CSV.open(newline="", encoding="utf-8-sig") as handle:
        episode_rows = list(csv.DictReader(handle))
    public_rows = [
        row for row in episode_rows if row["type"] == "EPISODE_TYPE_PUBLIC"
    ]
    if len(public_rows) != 54:
        raise AssertionError(("public episode count", len(public_rows)))
    episode_ids = [int(row["episode_id"]) for row in public_rows]
    if len(episode_ids) != len(set(episode_ids)):
        raise AssertionError("duplicate episode ID")

    candidate = load_module("live_shadow_candidate", CANDIDATE_DIR / "main.py")
    parent = load_module("live_shadow_parent", PARENT_DIR / "main.py")

    callback_rows: list[dict] = []
    difference_rows: list[dict] = []
    event_rows: list[dict] = []
    mismatch_rows: list[dict] = []
    per_episode_rows: list[dict] = []
    action_errors = 0
    outer_exceptions = 0
    rejection_counts = collections.Counter()

    for episode_id in sorted(episode_ids):
        filename = f"episode_{episode_id}_replay.json"
        replay_path = EVIDENCE / filename
        if filename not in inventory:
            raise AssertionError(("inventory missing", filename))
        if (
            not replay_path.is_file()
            or int(inventory[filename]["bytes"]) != replay_path.stat().st_size
            or inventory[filename]["sha256"].upper() != sha256(replay_path)
        ):
            raise AssertionError(("replay mismatch", filename))
        replay = json.loads(replay_path.read_text(encoding="utf-8-sig"))
        if int((replay.get("info") or {}).get("EpisodeId")) != episode_id:
            raise AssertionError(("episode identity", episode_id))
        teams = (replay.get("info") or {}).get("TeamNames") or []
        seats = [index for index, team in enumerate(teams) if team == "rurumi"]
        if len(seats) != 1:
            raise AssertionError(("target seat", episode_id, teams))
        seat = seats[0]
        reward = replay["rewards"][seat]
        reset_module(candidate, CANDIDATE_DIR)
        reset_module(parent, PARENT_DIR)

        file_callbacks = 0
        file_differences = 0
        file_events = 0
        file_mismatches = 0
        file_first_difference = None
        file_first_event = None
        for step_index, raw, recorded_action in replay_decisions(replay, seat):
            file_callbacks += 1
            owner_before = candidate._cum_active_transaction_owner
            try:
                parent_action = parent.agent(copy.deepcopy(raw))
                candidate_action = candidate.agent(copy.deepcopy(raw))
            except Exception:
                outer_exceptions += 1
                raise
            owner_after = candidate._cum_active_transaction_owner
            telemetry = copy.deepcopy(candidate._cum_last_telemetry)
            pending = candidate.drain_cumulative_telemetry()
            if len(pending) != 1 or telemetry != pending[0]:
                raise AssertionError(
                    ("candidate telemetry", episode_id, step_index, len(pending))
                )
            if hasattr(parent, "drain_cumulative_telemetry"):
                parent.drain_cumulative_telemetry()

            candidate_obs = candidate.to_observation_class(copy.deepcopy(raw))
            parent_obs = parent.to_observation_class(copy.deepcopy(raw))
            if (
                not valid(candidate_obs, recorded_action)
                or not valid(candidate_obs, candidate_action)
                or not valid(parent_obs, parent_action)
            ):
                action_errors += 1
                raise AssertionError(
                    (
                        "invalid",
                        episode_id,
                        step_index,
                        recorded_action,
                        parent_action,
                        candidate_action,
                    )
                )

            recorded_semantic = semantic(candidate, candidate_obs, recorded_action)
            candidate_semantic = semantic(candidate, candidate_obs, candidate_action)
            parent_semantic = semantic(parent, parent_obs, parent_action)
            matched_recorded = candidate_semantic == recorded_semantic
            differs_parent = candidate_semantic != parent_semantic
            if not matched_recorded:
                file_mismatches += 1
                mismatch_rows.append(
                    {
                        "episode_id": episode_id,
                        "step": step_index,
                        "seat": seat,
                        "turn": raw["current"]["turn"],
                        "turn_action_count": raw["current"]["turnActionCount"],
                        "recorded": json.dumps(recorded_semantic, sort_keys=True),
                        "candidate": json.dumps(candidate_semantic, sort_keys=True),
                    }
                )

            proposal = next(
                (
                    row
                    for row in telemetry.get("proposals", [])
                    if row.get("rule_id") == NEW_RULE_ID
                ),
                None,
            )
            new_rule_event = (
                (proposal is not None and proposal.get("eligible"))
                or telemetry.get("winning_rule_id") == NEW_RULE_ID
                or telemetry.get("attribution_owner") == NEW_RULE_ID
                or owner_before == NEW_RULE_ID
                or owner_after == NEW_RULE_ID
            )
            if new_rule_event:
                file_events += 1
                if file_first_event is None:
                    file_first_event = step_index
                event_rows.append(
                    {
                        "episode_id": episode_id,
                        "step": step_index,
                        "seat": seat,
                        "reward": reward,
                        "turn": raw["current"]["turn"],
                        "turn_action_count": raw["current"]["turnActionCount"],
                        "proposal_eligible": (
                            None if proposal is None else proposal.get("eligible")
                        ),
                        "winning_rule_id": telemetry.get("winning_rule_id"),
                        "attribution_owner": telemetry.get("attribution_owner"),
                        "owner_before": owner_before,
                        "owner_after": owner_after,
                        "rollback_reason": telemetry.get("rollback_reason"),
                        "parent": json.dumps(parent_semantic, sort_keys=True),
                        "candidate": json.dumps(candidate_semantic, sort_keys=True),
                    }
                )
            if differs_parent:
                file_differences += 1
                if file_first_difference is None:
                    file_first_difference = step_index
                difference_rows.append(
                    {
                        "episode_id": episode_id,
                        "step": step_index,
                        "seat": seat,
                        "reward": reward,
                        "turn": raw["current"]["turn"],
                        "turn_action_count": raw["current"]["turnActionCount"],
                        "winning_rule_id": telemetry.get("winning_rule_id"),
                        "attribution_owner": telemetry.get("attribution_owner"),
                        "owner_before": owner_before,
                        "owner_after": owner_after,
                        "rollback_reason": telemetry.get("rollback_reason"),
                        "parent": json.dumps(parent_semantic, sort_keys=True),
                        "candidate": json.dumps(candidate_semantic, sort_keys=True),
                        "recorded": json.dumps(recorded_semantic, sort_keys=True),
                    }
                )

            callback_rows.append(
                {
                    "episode_id": episode_id,
                    "step": step_index,
                    "seat": seat,
                    "reward": reward,
                    "turn": raw["current"]["turn"],
                    "turn_action_count": raw["current"]["turnActionCount"],
                    "matched_recorded": matched_recorded,
                    "differs_parent": differs_parent,
                    "winning_rule_id": telemetry.get("winning_rule_id"),
                    "attribution_owner": telemetry.get("attribution_owner"),
                    "new_rule_event": bool(new_rule_event),
                    "new_rule_rejection": (
                        None if proposal is None else proposal.get("rejection_reason")
                    ),
                }
            )
            rejection_counts[
                str(None if proposal is None else proposal.get("rejection_reason"))
            ] += 1
        per_episode_rows.append(
            {
                "episode_id": episode_id,
                "seat": seat,
                "reward": reward,
                "callbacks": file_callbacks,
                "candidate_parent_differences": file_differences,
                "new_rule_events": file_events,
                "candidate_recorded_mismatches": file_mismatches,
                "first_difference_step": file_first_difference,
                "first_new_rule_event_step": file_first_event,
            }
        )

    callback_fields = [
        "episode_id",
        "step",
        "seat",
        "reward",
        "turn",
        "turn_action_count",
        "matched_recorded",
        "differs_parent",
        "winning_rule_id",
        "attribution_owner",
        "new_rule_event",
        "new_rule_rejection",
    ]
    change_fields = [
        "episode_id",
        "step",
        "seat",
        "reward",
        "turn",
        "turn_action_count",
        "winning_rule_id",
        "attribution_owner",
        "owner_before",
        "owner_after",
        "rollback_reason",
        "parent",
        "candidate",
        "recorded",
    ]
    event_fields = [
        "episode_id",
        "step",
        "seat",
        "reward",
        "turn",
        "turn_action_count",
        "proposal_eligible",
        "winning_rule_id",
        "attribution_owner",
        "owner_before",
        "owner_after",
        "rollback_reason",
        "parent",
        "candidate",
    ]
    per_episode_fields = [
        "episode_id",
        "seat",
        "reward",
        "callbacks",
        "candidate_parent_differences",
        "new_rule_events",
        "candidate_recorded_mismatches",
        "first_difference_step",
        "first_new_rule_event_step",
    ]
    mismatch_fields = [
        "episode_id",
        "step",
        "seat",
        "turn",
        "turn_action_count",
        "recorded",
        "candidate",
    ]
    write_csv(HERE / "callbacks.csv", callback_rows, callback_fields)
    write_csv(HERE / "candidate_parent_differences.csv", difference_rows, change_fields)
    write_csv(HERE / "new_rule_events.csv", event_rows, event_fields)
    write_csv(HERE / "candidate_recorded_mismatches.csv", mismatch_rows, mismatch_fields)
    write_csv(HERE / "per_episode.csv", per_episode_rows, per_episode_fields)

    report = {
        "episodes": len(per_episode_rows),
        "wins": sum(row["reward"] == 1 for row in per_episode_rows),
        "losses": sum(row["reward"] == -1 for row in per_episode_rows),
        "callbacks": len(callback_rows),
        "candidate_parent_differences": len(difference_rows),
        "episodes_with_differences": sum(
            row["candidate_parent_differences"] > 0 for row in per_episode_rows
        ),
        "new_rule_events": len(event_rows),
        "episodes_with_new_rule_events": sum(
            row["new_rule_events"] > 0 for row in per_episode_rows
        ),
        "candidate_recorded_mismatches": len(mismatch_rows),
        "action_errors": action_errors,
        "outer_exceptions": outer_exceptions,
        "new_rule_rejection_counts": dict(rejection_counts.most_common()),
        "candidate_sha256": EXPECTED_CANDIDATE_SHA,
        "parent_sha256": EXPECTED_PARENT_SHA,
        "episodes_csv_sha256": EXPECTED_EPISODES_SHA,
    }
    (HERE / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
