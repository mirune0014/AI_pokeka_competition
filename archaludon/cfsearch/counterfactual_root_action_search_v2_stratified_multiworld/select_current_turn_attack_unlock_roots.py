"""Select the final public-state current-turn attack-unlock diagnostic roots."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping


def _trace_observation(root: Mapping[str, Any]) -> Mapping[str, Any]:
    trace = Path(str(root["trace_path"]))
    callback = int(root["callback_index"])
    for line in trace.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if int(row.get("callback_index", -1)) == callback:
            return row.get("observation") or {}
    raise ValueError(f"missing callback {trace} {callback}")


def _options(observation: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    options = ((observation.get("select") or {}).get("option") or [])
    return [option for option in options if isinstance(option, Mapping)]


def _semantic_for_index(root: Mapping[str, Any], index: int) -> dict[str, Any] | None:
    for item in root.get("legal_semantic_action_set") or []:
        if int(item.get("option_index", -1)) == index:
            return item
    return None


def _predicate(root: Mapping[str, Any], observation: Mapping[str, Any]) -> dict[str, Any] | None:
    select = observation.get("select") or {}
    current = observation.get("current") or {}
    if select.get("context") != 0 or select.get("type") != 0:
        return None
    if bool(current.get("energyAttached")):
        return None
    options = _options(observation)
    parent_action = list(root.get("parent_action") or [])
    if len(parent_action) != 1 or not isinstance(parent_action[0], int) or parent_action[0] >= len(options):
        return None
    parent_option = options[parent_action[0]]
    if parent_option.get("type") != 8 or parent_option.get("inPlayArea") != 5:
        return None
    energy_serial = parent_option.get("index")
    if energy_serial is None:
        return None
    same_serial = [
        (index, option)
        for index, option in enumerate(options)
        if option.get("type") == 8 and option.get("index") == energy_serial
    ]
    active_alternatives = [
        (index, option)
        for index, option in same_serial
        if option.get("inPlayArea") == 4
    ]
    if not active_alternatives:
        return None
    active_semantics = [_semantic_for_index(root, index) for index, _ in active_alternatives]
    active_semantics = [item for item in active_semantics if item is not None]
    unique_active = {(tuple(item.get("action") or []), str(item.get("semantic_id"))) for item in active_semantics}
    if len(unique_active) != 1:
        return None
    parent_semantic = str(root.get("parent_semantic_action"))
    active_item = active_semantics[0]
    if str(active_item.get("semantic_id")) == parent_semantic:
        return None
    attack_option_count = sum(option.get("type") == 13 for option in options)
    if attack_option_count != 0:
        return None
    if not root.get("public_hash") or not root.get("legal_semantic_action_set"):
        return None
    # The exact post-attach process checks import path, root parity, and
    # same-seed prefix again.  Keep this extractor public-state-only.
    return {
        "diagnostic_schema_version": "archaludon_current_turn_attack_unlock_root.v1",
        "root_id": root["root_id"],
        "schedule_key": root.get("schedule_key"),
        "trace_path": root.get("trace_path"),
        "callback_index": int(root["callback_index"]),
        "game": int(root["game"]),
        "seed": int(root["seed"]),
        "panel": root.get("panel"),
        "opponent_family": root.get("opponent_family"),
        "opponent_policy_id": root.get("opponent_policy_id"),
        "opponent_path": root.get("opponent_path"),
        "opponent_deck_path": root.get("opponent_deck_path"),
        "policy_seat": int(root["policy_seat"]),
        "turn": root.get("turn"),
        "turnActionCount": root.get("turnActionCount"),
        "public_hash": root.get("public_hash"),
        "parent_action": parent_action,
        "parent_semantic_action": parent_semantic,
        "active_action": list(active_item.get("action") or []),
        "active_semantic_action": active_item.get("semantic_id"),
        "energy_serial": str(energy_serial),
        "root_attack_option_count": attack_option_count,
        "legal_semantic_action_set": root.get("legal_semantic_action_set") or [],
        "context_tags": root.get("context_tags") or [],
    }


def select(roots_path: Path, output: Path, max_roots: int) -> dict[str, Any]:
    discovery = [
        json.loads(line)
        for line in roots_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
        and json.loads(line).get("split") == "discovery"
    ]
    matches: list[dict[str, Any]] = []
    for root in discovery:
        observation = _trace_observation(root)
        selected = _predicate(root, observation)
        if selected is not None:
            matches.append(selected)
    # The precommitted selection is independent of outcome: hash order first,
    # then at most two roots per game and one root per turn.
    matches.sort(key=lambda row: hashlib.sha256(
        f"{row['schedule_key']}|{row['callback_index']}|{row['public_hash']}".encode("utf-8")
    ).hexdigest())
    selected: list[dict[str, Any]] = []
    game_counts: defaultdict[tuple[str, int], int] = defaultdict(int)
    turn_keys: set[tuple[str, int, int]] = set()
    for row in matches:
        game_key = (str(row["opponent_family"]), int(row["seed"]))
        turn_key = (str(row["opponent_family"]), int(row["seed"]), int(row["turn"] or 0))
        if game_counts[game_key] >= 2 or turn_key in turn_keys:
            continue
        selected.append(row)
        game_counts[game_key] += 1
        turn_keys.add(turn_key)
        if len(selected) >= max_roots:
            break
    output.mkdir(parents=True, exist_ok=True)
    (output / "selected_roots.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in selected),
        encoding="utf-8",
        newline="\n",
    )
    report = {
        "schema_version": "archaludon_current_turn_attack_unlock_root_selection.v1",
        "source_kind": "FORMAL_REALIZED_SEEDED_WORLD_DISCOVERY_ONLY",
        "discovery_roots_scanned": len(discovery),
        "predicate_matches": len(matches),
        "selected_roots": len(selected),
        "distinct_games": len({(str(row["opponent_family"]), int(row["seed"])) for row in selected}),
        "opponent_families": sorted({str(row["opponent_family"]) for row in selected}),
        "seats": sorted({int(row["policy_seat"]) for row in selected}),
        "max_roots": max_roots,
        "selection": "sha256(schedule_key|callback_index|public_hash) ascending; max2 per game; max1 per turn",
        "holdout_opened": False,
        "candidate_created": False,
    }
    (output / "REPORT.json").write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-roots", type=int, default=256)
    args = parser.parse_args()
    print(json.dumps(select(args.roots.resolve(), args.output.resolve(), args.max_roots), ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
