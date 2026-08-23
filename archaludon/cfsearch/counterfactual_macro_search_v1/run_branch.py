"""Run one counterfactual root in a fresh Python process."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import traceback
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from infrastructure.tools.ptcg_common import dataclass_to_dict, load_agent
from research.rl_ptcg.replay_reconstruction import iter_replay_decisions

from common import (
    canonicalize_prompt_action,
    file_sha256,
    find_replay_decision,
    legal_action,
    observation_hash,
    read_jsonl,
)


# The engine requires legal card IDs for unknown hidden zones.  These values
# are simulation placeholders only; they are never exposed to the parent
# policy.  8 is Basic {M} Energy and 1072 is a Basic Pokémon in the checked
# local card table.
_PLACEHOLDER_CARD_ID = 8
_PLACEHOLDER_BASIC_ID = 1072


def _read_deck(path: Path) -> list[int]:
    cards = [int(line.strip()) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(cards) != 60:
        raise ValueError(f"parent deck must contain 60 cards: {path}")
    return cards


def _lookup_root(manifest: Path, root_id: str) -> dict[str, Any]:
    for row in read_jsonl(manifest):
        if row.get("root_id") == root_id:
            return row
    raise ValueError(f"root_id not found: {root_id}")


def _root_action(root: Mapping[str, Any], branch: str, alternative_index: int) -> tuple[list[int], str]:
    if branch in {"parent_a", "parent_b"}:
        action = list(root["parent_action"])
        return action, str(root["parent_semantic_id"])
    if branch != "alternative":
        raise ValueError(f"unknown branch: {branch}")
    alternatives = list(root.get("alternatives") or [])
    if alternative_index < 0 or alternative_index >= len(alternatives):
        raise ValueError("alternative index is outside the root manifest")
    selected = alternatives[alternative_index]
    return list(selected["action"]), str(selected["semantic_id"])


def _placeholder_world(observation: Mapping[str, Any], parent_deck: Sequence[int]) -> dict[str, list[int]]:
    current = observation.get("current") or {}
    seat = int(current.get("yourIndex", 0))
    players = current.get("players") or []
    if len(players) != 2:
        raise ValueError("root observation has no two-player state")
    mine = players[seat] or {}
    opponent = players[1 - seat] or {}
    opponent_deck_count = int(opponent.get("deckCount") or 0)
    opponent_hand_count = int(opponent.get("handCount") or 0)
    opponent_prize_count = len(opponent.get("prize") or [])
    own_prize_count = len(mine.get("prize") or [])
    active = opponent.get("active") or []
    opponent_active: list[int] = []
    if active:
        first = active[0]
        if isinstance(first, Mapping) and first.get("id") is not None:
            opponent_active = [int(first["id"])]
        else:
            opponent_active = [_PLACEHOLDER_BASIC_ID]
    return {
        "your_deck": list(parent_deck),
        "your_prize": [_PLACEHOLDER_CARD_ID] * own_prize_count,
        "opponent_deck": [_PLACEHOLDER_CARD_ID] * opponent_deck_count,
        "opponent_prize": [_PLACEHOLDER_CARD_ID] * opponent_prize_count,
        "opponent_hand": [_PLACEHOLDER_CARD_ID] * opponent_hand_count,
        "opponent_active": opponent_active,
    }


def _world_from_spec(
    observation: Mapping[str, Any],
    parent_deck: Sequence[int],
    world_spec_path: Path | None,
) -> tuple[dict[str, list[int]], dict[str, Any]]:
    """Load a V2 public-consistent engine world without exposing it to policy."""
    if world_spec_path is None:
        return _placeholder_world(observation, parent_deck), {
            "world_id": "placeholder",
            "world_method": "fixed_public_safe_placeholders_v1",
            "world_valid": True,
            "world_validation_error": None,
        }
    value = json.loads(world_spec_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("world spec must be a JSON object")
    world = {
        key: list(value.get(key) or [])
        for key in (
            "your_deck", "your_prize", "opponent_deck", "opponent_prize",
            "opponent_hand", "opponent_active",
        )
    }
    if len(world["your_deck"]) != len(parent_deck):
        raise ValueError("world spec your_deck does not match parent deck length")
    if any(not isinstance(card, int) or isinstance(card, bool) or card <= 0 for values in world.values() for card in values):
        raise ValueError("world spec contains an invalid card ID")
    return world, {
        "world_id": str(value.get("world_id") or world_spec_path.stem),
        "world_method": str(value.get("method") or "external_world_spec"),
        "world_valid": True,
        "world_validation_error": None,
    }


def _find_target(replay_path: Path, root: Mapping[str, Any]) -> Any:
    if file_sha256(replay_path) != root["replay_sha256"]:
        raise ValueError("source replay hash changed")
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    return find_replay_decision(
        replay,
        replay_step=int(root["replay_step"]),
        acting_seat=int(root["acting_seat"]),
    )


def _validate_target(root: Mapping[str, Any], observation: Mapping[str, Any]) -> None:
    if observation_hash(observation) != root["target_observation_sha256"]:
        raise ValueError("target observation hash mismatch")
    # The manifest stores semantic IDs, while the runner rebinds raw option
    # coordinates from the fresh target observation.
    from common import singleton_action_semantics

    current_semantics = [row["semantic_id"] for row in singleton_action_semantics(observation)]
    if current_semantics != list(root["target_option_semantic_ids"]):
        raise ValueError("target semantic option set mismatch")


def _run(
    root: Mapping[str, Any],
    branch: str,
    alternative_index: int,
    max_steps: int,
    world_spec_path: Path | None = None,
) -> dict[str, Any]:
    parent_dir = Path(str(root["parent_agent_dir"])).resolve()
    replay_path = Path(str(root["root_source_replay"])).resolve()
    selected_action, selected_semantic = _root_action(root, branch, alternative_index)
    result: dict[str, Any] = {
        "schema_version": "archaludon_counterfactual_branch_result.v1",
        "root_id": root["root_id"],
        "branch": branch,
        "alternative_index": alternative_index if branch == "alternative" else None,
        "selected_action": selected_action,
        "selected_semantic_id": selected_semantic,
        "target_option_semantic_ids": list(root["target_option_semantic_ids"]),
        "parent_semantic_id": str(root["parent_semantic_id"]),
        "forced_action_legal": False,
        "parent_main_sha256": root["parent_main_sha256"],
        "parent_deck_sha256": root["parent_deck_sha256"],
        "target_observation_sha256": root["target_observation_sha256"],
        "engine_mode": "target_observation_snapshot_v1",
        "hidden_world_policy": "fixed_public_safe_placeholders_v1",
        "world_id": "placeholder",
        "world_method": "fixed_public_safe_placeholders_v1",
        "world_valid": False,
        "world_validation_error": None,
        "terminal_result": None,
        "steps_after_root": 0,
        "final_turn": None,
        "action_errors": 0,
        "max_step": False,
        "status": "error",
        "error": None,
    }
    search_started = False
    try:
        # Import the parent and its cg module only in this fresh process.  No
        # parent module is modified and no second policy is loaded.
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
        from cg.api import search_begin, search_end, search_step, to_observation_class

        decision = _find_target(replay_path, root)
        observation = dict(decision.observation)
        _validate_target(root, observation)
        if not legal_action(observation, selected_action):
            raise ValueError("selected root action is no longer legal")
        if canonicalize_prompt_action(observation, selected_action).stable_id != selected_semantic:
            raise ValueError("selected root action semantic ID mismatch")
        result["forced_action_legal"] = True

        parent = load_agent(parent_dir, f"cfsearch_parent_{root['root_id']}_{branch}")
        world, world_meta = _world_from_spec(
            observation,
            _read_deck(parent_dir / "deck.csv"),
            world_spec_path,
        )
        result.update(world_meta)
        result["hidden_world_policy"] = (
            "consistent_public_world_bank_v1"
            if world_spec_path is not None
            else "fixed_public_safe_placeholders_v1"
        )
        search_state = search_begin(
            to_observation_class(observation),
            world["your_deck"],
            world["your_prize"],
            world["opponent_deck"],
            world["opponent_prize"],
            world["opponent_hand"],
            world["opponent_active"],
            manual_coin=True,
        )
        search_started = True
        search_state = search_step(search_state.searchId, selected_action)
        steps_after_root = 0
        while steps_after_root < max_steps:
            raw_observation = dataclass_to_dict(search_state.observation)
            current = raw_observation.get("current") or {}
            terminal_result = current.get("result")
            if terminal_result not in (None, -1):
                result["terminal_result"] = int(terminal_result)
                result["final_turn"] = current.get("turn")
                result["steps_after_root"] = steps_after_root
                result["status"] = "complete"
                break
            options = (raw_observation.get("select") or {}).get("option") or []
            if not options:
                raise RuntimeError("engine returned a non-terminal prompt without options")
            action = parent(raw_observation)
            if not legal_action(raw_observation, action):
                result["action_errors"] += 1
                raise RuntimeError(f"parent returned invalid action: {action!r}")
            search_state = search_step(search_state.searchId, action)
            steps_after_root += 1
        else:
            result["steps_after_root"] = steps_after_root
            result["max_step"] = True
            result["status"] = "max_step"
    except Exception as error:  # the JSON result is the machine-readable artifact
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        if search_started:
            try:
                search_end()
            except Exception as error:
                if result["error"] is None:
                    result["error"] = f"search_end {type(error).__name__}: {error}"
                result["status"] = "error"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-manifest", type=Path, required=True)
    parser.add_argument("--root-id", required=True)
    parser.add_argument("--branch", choices=("parent_a", "parent_b", "alternative"), required=True)
    parser.add_argument("--alternative-index", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=160)
    parser.add_argument(
        "--world-spec",
        type=Path,
        default=None,
        help="optional V2 engine-only world JSON; never passed to the parent callback",
    )
    args = parser.parse_args()
    root = _lookup_root(args.root_manifest.resolve(), args.root_id)
    if args.max_steps < 1:
        raise SystemExit("--max-steps must be positive")
    print(json.dumps(
        _run(
            root,
            args.branch,
            args.alternative_index,
            args.max_steps,
            args.world_spec.resolve() if args.world_spec is not None else None,
        ),
        sort_keys=True,
        ensure_ascii=True,
    ))


if __name__ == "__main__":
    main()
