"""Run accepted-parent games while preserving callback-level public traces.

This is a diagnostic runner for the V2.2 formal-realized-world work.  It does
not alter the accepted agent or the checked runners.  The engine's hidden state
is retained only inside the running process; the trace contains the callback
observation that the public agent received, plus deterministic semantic
metadata derived from that observation.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
V1_DIR = HERE.parent / "counterfactual_macro_search_v1"
for path in (REPO_ROOT, V1_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from infrastructure.tools.ptcg_common import (  # noqa: E402
    ensure_engine_on_path,
    load_agent,
    read_deck,
)
from infrastructure.tools.run_local_battle import player_snapshot  # noqa: E402
from common import (  # noqa: E402
    canonical_sha256,
    legal_action,
    observation_hash,
    singleton_action_semantics,
)
from common_v2 import action_transformation, normalized_public_hash, public_context_tags  # noqa: E402
from research.rl_ptcg.canonical_actions import canonicalize_prompt_action  # noqa: E402


def _card_id(card: Any) -> int | None:
    if not isinstance(card, Mapping) or card.get("id") is None:
        return None
    try:
        return int(card["id"])
    except (TypeError, ValueError):
        return None


def _semantic_action(observation: Mapping[str, Any], action: Sequence[int]) -> str:
    try:
        return str(canonicalize_prompt_action(observation, list(action)).stable_id)
    except Exception as exc:  # pragma: no cover - diagnostic fail-closed path
        return f"UNRESOLVED:{type(exc).__name__}"


def _legal_semantic_actions(observation: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return visible singleton semantic actions, retaining raw indexes.

    The formal root corpus only accepts singleton alternatives.  For other
    prompts we still retain the parent action and any unambiguous singleton
    choices as diagnostics; no hidden-state or effect simulator is used.
    """

    select = observation.get("select") or {}
    options = select.get("option") or []
    rows: list[dict[str, Any]] = []
    for index, option in enumerate(options):
        action = [index]
        if not legal_action(observation, action):
            continue
        try:
            semantic_id = str(canonicalize_prompt_action(observation, action).stable_id)
        except Exception:
            continue
        rows.append({"semantic_id": semantic_id, "action": action, "option_index": index})
    # Empty is a legal action on END/optional prompts and is useful for parity.
    if legal_action(observation, []):
        rows.append({"semantic_id": _semantic_action(observation, []), "action": [], "option_index": None})
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        unique.setdefault(str(row["semantic_id"]), row)
    return [unique[key] for key in sorted(unique)]


def _transformation_candidates(
    observation: Mapping[str, Any],
    parent_action: Sequence[int],
    legal_actions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    parent_semantic = _semantic_action(observation, parent_action)
    rows: list[dict[str, Any]] = []
    for row in legal_actions:
        semantic_id = str(row.get("semantic_id"))
        action = row.get("action")
        if semantic_id == parent_semantic or not isinstance(action, list):
            continue
        try:
            transformation = action_transformation(observation, parent_action, action)
        except Exception as exc:  # pragma: no cover
            transformation = f"UNRESOLVED:{type(exc).__name__}"
        rows.append({
            "semantic_id": semantic_id,
            "action": action,
            "transformation": transformation,
        })
    return rows


def _trace_row(
    *,
    observation: Mapping[str, Any],
    action: Sequence[int],
    schedule_key: str,
    panel: str,
    opponent_family: str,
    opponent_policy_id: str,
    opponent_path: str,
    opponent_deck_path: str,
    policy_seat: int,
    seed: int,
    game_index: int,
    callback_index: int,
) -> dict[str, Any]:
    current = observation.get("current") or {}
    select = observation.get("select") or {}
    legal_actions = _legal_semantic_actions(observation)
    parent_semantic = _semantic_action(observation, action)
    return {
        "schema_version": "archaludon_formal_realized_seeded_world_callback.v1",
        "schedule_key": schedule_key,
        "panel": panel,
        "opponent_family": opponent_family,
        "opponent_policy_id": opponent_policy_id,
        "opponent_path": opponent_path,
        "opponent_deck_path": opponent_deck_path,
        "policy_seat": policy_seat,
        "acting_seat": current.get("yourIndex"),
        "seed": seed,
        "game": game_index,
        "callback_index": callback_index,
        "turn": current.get("turn"),
        "turnActionCount": current.get("turnActionCount"),
        "context": select.get("context"),
        "select_type": select.get("type"),
        "public_hash": normalized_public_hash(observation),
        "raw_action": list(action),
        "parent_semantic_action": parent_semantic,
        "legal_semantic_action_set": legal_actions,
        "transformation_candidates": _transformation_candidates(observation, action, legal_actions),
        "context_tags": public_context_tags(observation),
        "observation": observation,
    }


def run_game(args: argparse.Namespace, game_index: int) -> dict[str, Any]:
    from cg.game import battle_finish, battle_select, battle_start

    seed = int(args.seed_base) + int(game_index)
    random.seed(seed)
    agent_a_dir = args.agent_a.resolve()
    agent_b_dir = args.agent_b.resolve()
    deck_a = read_deck(args.deck_a or (agent_a_dir / "deck.csv"))
    deck_b = read_deck(args.deck_b or (agent_b_dir / "deck.csv"))
    agent_a = load_agent(agent_a_dir, f"trace_agent_a_{game_index}")
    agent_b = load_agent(agent_b_dir, f"trace_agent_b_{game_index}")
    agents = [agent_a, agent_b]
    for agent in agents:
        module_random = getattr(getattr(agent, "module", None), "random", None)
        if hasattr(module_random, "seed"):
            module_random.seed(seed)

    obs, start_data = battle_start(deck_a, deck_b, seed=seed)
    if not obs:
        return {
            "game": game_index,
            "seed": seed,
            "started": False,
            "start_error_player": getattr(start_data, "errorPlayer", None),
            "start_error_type": getattr(start_data, "errorType", None),
            "trace": "",
        }

    args.trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = args.trace_dir / f"game_{game_index:04d}.jsonl"
    steps = 0
    action_errors = 0
    final_obs = obs
    try:
        with trace_path.open("w", encoding="utf-8", newline="\n") as trace_file:
            while obs and obs.get("select") and steps < args.max_steps:
                current = obs.get("current") or {}
                if current.get("result") not in (None, -1):
                    break
                player = int(current.get("yourIndex", 0))
                select = obs.get("select") or {}
                if not select.get("option") and not legal_action(obs, []):
                    break
                try:
                    action = list(agents[player](obs))
                except Exception as exc:
                    action_errors += 1
                    raise RuntimeError(f"agent {player} failed at callback {steps}: {exc}") from exc
                if not legal_action(obs, action):
                    action_errors += 1
                    raise RuntimeError(f"agent {player} returned illegal action at callback {steps}: {action}")
                row = _trace_row(
                    observation=obs,
                    action=action,
                    schedule_key=args.schedule_key,
                    panel=args.panel,
                    opponent_family=args.opponent_family,
                    opponent_policy_id=args.opponent_policy_id,
                    opponent_path=str(args.opponent_path),
                    opponent_deck_path=str(args.opponent_deck_path),
                    policy_seat=args.policy_seat,
                    seed=seed,
                    game_index=game_index,
                    callback_index=steps,
                )
                trace_file.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")
                obs = battle_select(action)
                final_obs = obs
                steps += 1
    finally:
        battle_finish()

    final_current = (final_obs or {}).get("current") or {}
    return {
        "schema_version": "archaludon_formal_realized_seeded_world_game.v1",
        "game": game_index,
        "seed": seed,
        "started": True,
        "terminal": final_current.get("result") not in (None, -1),
        "result": final_current.get("result"),
        "steps": steps,
        "turn": final_current.get("turn"),
        "action_errors": action_errors,
        "hit_max_steps": steps >= args.max_steps,
        "trace": str(trace_path.resolve()),
        "policy_seat": args.policy_seat,
        "panel": args.panel,
        "opponent_family": args.opponent_family,
        "opponent_policy_id": args.opponent_policy_id,
        "seed_schedule_key": f"{args.schedule_key}|{args.panel}|{args.opponent_family}|{args.policy_seat}|{seed}",
        **player_snapshot(final_obs or {}),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--agent-a", type=Path, required=True)
    parser.add_argument("--agent-b", type=Path, required=True)
    parser.add_argument("--deck-a", type=Path)
    parser.add_argument("--deck-b", type=Path)
    parser.add_argument("--games", type=int, required=True)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--trace-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--seed-base", type=int, required=True)
    parser.add_argument("--schedule-key", required=True)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--opponent-family", required=True)
    parser.add_argument("--opponent-policy-id", required=True)
    parser.add_argument("--opponent-path", type=Path, required=True)
    parser.add_argument("--opponent-deck-path", type=Path, required=True)
    parser.add_argument("--policy-seat", type=int, choices=(0, 1), required=True)
    args = parser.parse_args()
    if args.games <= 0 or args.max_steps <= 0:
        parser.error("--games and --max-steps must be positive")
    if args.policy_seat == 0:
        # The policy is expected to be agent A in seat 0.
        pass
    return args


def main() -> None:
    args = parse_args()
    ensure_engine_on_path(args.engine_dir)
    args.trace_dir.mkdir(parents=True, exist_ok=True)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for game_index in range(args.games):
        record = run_game(args, game_index)
        records.append(record)
        print(json.dumps(record, ensure_ascii=True, sort_keys=True), flush=True)
    args.summary.write_text(
        "".join(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
        newline="\n",
    )
    if any(not row.get("started") or row.get("action_errors") or row.get("hit_max_steps") for row in records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
