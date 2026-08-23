"""Run one parent/Active-attach branch for the final public diagnostic."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
V1_DIR = HERE.parent / "counterfactual_macro_search_v1"
for path in (REPO_ROOT, V1_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from infrastructure.tools.ptcg_common import ensure_engine_on_path, load_agent, read_deck  # noqa: E402
from common import legal_action, singleton_action_semantics  # noqa: E402
from common_v2 import normalized_public_hash  # noqa: E402
from research.rl_ptcg.canonical_actions import canonicalize_prompt_action  # noqa: E402


def _semantic(observation: Mapping[str, Any], action: list[int]) -> str:
    try:
        return str(canonicalize_prompt_action(observation, action).stable_id)
    except Exception as exc:
        return f"UNRESOLVED:{type(exc).__name__}"


def _options(observation: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    options = ((observation.get("select") or {}).get("option") or [])
    return [option for option in options if isinstance(option, Mapping)]


def _attack_ids(observation: Mapping[str, Any]) -> list[int]:
    ids = []
    for option in _options(observation):
        if option.get("type") == 13 and option.get("attackId") is not None:
            ids.append(int(option["attackId"]))
    return sorted(set(ids))


def _chosen_option(observation: Mapping[str, Any], action: list[int]) -> dict[str, Any]:
    options = _options(observation)
    if not action or not isinstance(action[0], int) or not (0 <= action[0] < len(options)):
        return {"type": None, "attackId": None}
    option = options[action[0]]
    return {"type": option.get("type"), "attackId": option.get("attackId")}


def _active(observation: Mapping[str, Any]) -> Mapping[str, Any] | None:
    current = observation.get("current") or {}
    players = current.get("players") or []
    seat = current.get("yourIndex")
    if seat not in (0, 1) or not isinstance(players, list) or seat >= len(players):
        return None
    active = (players[seat] or {}).get("active")
    if isinstance(active, list):
        return active[0] if active and isinstance(active[0], Mapping) else None
    return active if isinstance(active, Mapping) else None


def _opponent_active(observation: Mapping[str, Any]) -> Mapping[str, Any] | None:
    current = observation.get("current") or {}
    players = current.get("players") or []
    seat = current.get("yourIndex")
    if seat not in (0, 1) or not isinstance(players, list):
        return None
    opponent_seat = 1 - int(seat)
    if opponent_seat >= len(players):
        return None
    active = (players[opponent_seat] or {}).get("active")
    if isinstance(active, list):
        return active[0] if active and isinstance(active[0], Mapping) else None
    return active if isinstance(active, Mapping) else None


def _energy_count(active: Mapping[str, Any] | None) -> int | None:
    if not active:
        return None
    energies = active.get("energyCards")
    if energies is None:
        energies = active.get("energies")
    return len(energies) if isinstance(energies, list) else None


def _import_result(root: Mapping[str, Any], branch: str, alternative_semantic: str, engine_dir: Path) -> dict[str, Any]:
    import cg  # type: ignore  # noqa: PLC0415
    path = str(Path(getattr(cg, "__file__", "")).resolve())
    engine_root = str(engine_dir.resolve())
    ok = bool(path) and (path == engine_root or path.startswith(engine_root + "\\") or path.startswith(engine_root + "/"))
    return {
        "cg_module_path": path,
        "engine_root": engine_root,
        "engine_import_ok": ok,
        "root_id": root["root_id"],
        "branch": branch,
        "alternative_semantic_id": alternative_semantic,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    roots = {str(row["root_id"]): row for row in (json.loads(line) for line in args.roots.read_text(encoding="utf-8").splitlines() if line.strip())}
    root = roots[str(args.root_id)]
    policy_seat = int(root["policy_seat"])
    opponent_dir = Path(str(root["opponent_path"])).resolve()
    parent_dir = args.parent_agent.resolve()
    seed = int(root["seed"])
    random.seed(seed)
    if policy_seat == 0:
        agent_a_dir, agent_b_dir = parent_dir, opponent_dir
    else:
        agent_a_dir, agent_b_dir = opponent_dir, parent_dir

    # The engine import must occur before loading either packaged agent.
    try:
        from cg.game import battle_finish, battle_select, battle_start  # type: ignore  # noqa: PLC0415
        import_result = _import_result(root, args.branch, str(root.get("active_semantic_action", "")), args.engine_dir)
    except Exception as exc:
        return {
            "schema_version": "archaludon_current_turn_attack_unlock_branch.v1",
            "root_id": root["root_id"],
            "branch": args.branch,
            "alternative_semantic_id": str(root.get("active_semantic_action", "")),
            "status": "INVALID_ENGINE_IMPORT_SHADOW",
            "started": False,
            "engine_import_error": f"{type(exc).__name__}: {exc}",
            "engine_import_ok": False,
        }
    if not import_result["engine_import_ok"]:
        return {"schema_version": "archaludon_current_turn_attack_unlock_branch.v1", **import_result, "status": "INVALID_ENGINE_IMPORT_SHADOW", "started": False}

    deck_a = read_deck(agent_a_dir / "deck.csv")
    deck_b = read_deck(agent_b_dir / "deck.csv")
    agent_a = load_agent(agent_a_dir, f"attack_unlock_a_{root['root_id']}")
    agent_b = load_agent(agent_b_dir, f"attack_unlock_b_{root['root_id']}")
    agents = [agent_a, agent_b]
    for agent in agents:
        module_random = getattr(getattr(agent, "module", None), "random", None)
        if hasattr(module_random, "seed"):
            module_random.seed(seed)

    obs, start_data = battle_start(deck_a, deck_b, seed=seed)
    if not obs:
        return {"schema_version": "archaludon_current_turn_attack_unlock_branch.v1", **import_result, "status": "start_fault", "started": False, "start_error_type": getattr(start_data, "errorType", None)}

    target_callback = int(root["callback_index"])
    root_turn = int(root.get("turn") or 0)
    root_active_serial = None
    root_active_id = None
    steps = 0
    action_errors = 0
    root_match = False
    prefix_match = True
    chosen_root_action: list[int] | None = None
    post_attach_seen = False
    post_attach_comparable = False
    post_attach_invalid_reason: str | None = None
    post_attach_observation: dict[str, Any] | None = None
    post_attach_active_serial: Any = None
    post_attach_active_id: Any = None
    same_turn_rows: list[dict[str, Any]] = []
    first_attack_id: int | None = None
    final_obs = obs
    status = "max_step"
    try:
        while obs and obs.get("select") and steps < args.max_steps:
            current = obs.get("current") or {}
            if current.get("result") not in (None, -1):
                status = "complete"
                break
            player = int(current.get("yourIndex", 0))
            try:
                parent_action = list(agents[player](obs))
            except Exception as exc:
                action_errors += 1
                status = f"agent_error:{type(exc).__name__}"
                break
            if not legal_action(obs, parent_action):
                action_errors += 1
                status = "parent_action_illegal"
                break
            action = parent_action
            if steps == target_callback and player == policy_seat:
                expected_hash = str(root.get("public_hash"))
                expected_semantic = str(root.get("parent_semantic_action"))
                actual_hash = normalized_public_hash(obs)
                actual_semantic = _semantic(obs, parent_action)
                actual_legal = sorted(str(item["semantic_id"]) for item in singleton_action_semantics(obs))
                expected_legal = sorted(str(item.get("semantic_id")) for item in root.get("legal_semantic_action_set") or [])
                root_match = actual_hash == expected_hash and actual_semantic == expected_semantic and actual_legal == expected_legal
                prefix_match = root_match
                if not root_match:
                    status = "root_mismatch"
                    break
                root_active = _active(obs)
                root_active_serial = root_active.get("serial") if root_active else None
                root_active_id = root_active.get("id") if root_active else None
                if args.branch == "active":
                    action = list(root["active_action"])
                    if not legal_action(obs, action) or _semantic(obs, action) != str(root["active_semantic_action"]):
                        action_errors += 1
                        status = "invalid_forced_action"
                        break
                chosen_root_action = list(action)
            elif steps > target_callback and player == policy_seat and int(current.get("turn") or 0) == root_turn:
                chosen = _chosen_option(obs, parent_action)
                row = {
                    "step": steps,
                    "turn": current.get("turn"),
                    "turnActionCount": current.get("turnActionCount"),
                    "attack_option_ids": _attack_ids(obs),
                    "chosen_action": parent_action,
                    "chosen_option": chosen,
                }
                same_turn_rows.append(row)
                if chosen.get("type") == 13 and chosen.get("attackId") is not None and first_attack_id is None:
                    first_attack_id = int(chosen["attackId"])
            # After the forced attach, inspect the first callback owned by the
            # same player in the same turn.  No hidden state is used here.
            if steps > target_callback and not post_attach_seen and player == policy_seat:
                post_attach_seen = True
                active = _active(obs)
                select = obs.get("select") or {}
                post_attach_active_serial = active.get("serial") if active else None
                post_attach_active_id = active.get("id") if active else None
                same_active = bool(active and active.get("serial") == root_active_serial and active.get("id") == root_active_id)
                post_attach_comparable = bool(
                    int(current.get("turn") or 0) == root_turn
                    and select.get("context") == 0
                    and bool(current.get("energyAttached"))
                    and same_active
                    and not bool(current.get("retreated"))
                )
                if not post_attach_comparable:
                    if int(current.get("turn") or 0) != root_turn:
                        post_attach_invalid_reason = "TURN_ADVANCED"
                    elif select.get("context") != 0:
                        post_attach_invalid_reason = "EFFECT_PROMPT_INTERRUPTED"
                    elif not bool(current.get("energyAttached")):
                        post_attach_invalid_reason = "ENERGY_STATE_NOT_VISIBLE"
                    elif not same_active:
                        post_attach_invalid_reason = "ACTIVE_CHANGED"
                    elif bool(current.get("retreated")):
                        post_attach_invalid_reason = "RETREATED"
                    else:
                        post_attach_invalid_reason = "POST_ATTACH_STATE_NOT_COMPARABLE"
                else:
                    opponent_active = _opponent_active(obs)
                    post_attach_observation = {
                        "turn": current.get("turn"),
                        "turnActionCount": current.get("turnActionCount"),
                        "public_hash": normalized_public_hash(obs),
                        "attack_option_ids": _attack_ids(obs),
                        "energy_attached": current.get("energyAttached"),
                        "active_serial": active.get("serial") if active else None,
                        "active_id": active.get("id") if active else None,
                        "active_energy_count": _energy_count(active),
                        "opponent_active_id": opponent_active.get("id") if opponent_active else None,
                        "opponent_active_hp": opponent_active.get("hp") if opponent_active else None,
                    }
            obs = battle_select(action)
            final_obs = obs
            steps += 1
        else:
            if steps >= args.max_steps:
                status = "max_step"
    finally:
        battle_finish()

    final_current = (final_obs or {}).get("current") or {}
    if status == "max_step" and final_current.get("result") not in (None, -1):
        status = "complete"
    parent_result = final_current.get("result")
    return {
        "schema_version": "archaludon_current_turn_attack_unlock_branch.v1",
        **import_result,
        "status": status,
        "started": True,
        "root_match": root_match,
        "prefix_match": prefix_match,
        "root_id": root["root_id"],
        "policy_seat": policy_seat,
        "acting_seat": root.get("acting_seat"),
        "seed": seed,
        "opponent_family": root.get("opponent_family"),
        "parent_result": parent_result,
        "terminal_result": parent_result,
        "steps": steps,
        "turn": final_current.get("turn"),
        "action_errors": action_errors,
        "hit_max_steps": steps >= args.max_steps and final_current.get("result") in (None, -1),
        "chosen_root_action": chosen_root_action,
        "post_attach_seen": post_attach_seen,
        "post_attach_comparable": post_attach_comparable,
        "post_attach_invalid_reason": post_attach_invalid_reason,
        "post_attach_observation": post_attach_observation,
        "root_active_serial": root_active_serial,
        "root_active_id": root_active_id,
        "post_attach_active_serial": post_attach_active_serial,
        "post_attach_active_id": post_attach_active_id,
        "same_turn_rows": same_turn_rows,
        "same_turn_attack": first_attack_id is not None,
        "first_attack_id": first_attack_id,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--parent-agent", type=Path, required=True)
    parser.add_argument("--roots", type=Path, required=True)
    parser.add_argument("--root-id", required=True)
    parser.add_argument("--branch", choices=("parent", "active"), required=True)
    parser.add_argument("--max-steps", type=int, default=1000)
    args = parser.parse_args()
    ensure_engine_on_path(args.engine_dir.resolve())
    result = run(args)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True), flush=True)
    if result.get("status") != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
