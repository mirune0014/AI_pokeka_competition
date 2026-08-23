"""Evaluate one formal realized-seeded-world root branch.

The game is restarted with the same engine seed and opponent/policy paths.  We
run the accepted parent through the exact public prefix, verify the root hash,
semantic action, acting seat, and legal singleton set, replace exactly one
root action when requested, then resume the accepted parent to termination.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
V1_DIR = HERE.parent / "counterfactual_macro_search_v1"
for path in (REPO_ROOT, V1_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from infrastructure.tools.ptcg_common import ensure_engine_on_path, load_agent, read_deck  # noqa: E402
from common import legal_action, observation_hash, read_jsonl, singleton_action_semantics  # noqa: E402
from common_v2 import normalized_public_hash, public_context_tags  # noqa: E402
from research.rl_ptcg.canonical_actions import canonicalize_prompt_action  # noqa: E402


def _semantic(observation: dict[str, Any], action: list[int]) -> str:
    try:
        return str(canonicalize_prompt_action(observation, action).stable_id)
    except Exception as exc:
        return f"UNRESOLVED:{type(exc).__name__}"


def _root(args: argparse.Namespace) -> dict[str, Any]:
    rows = {str(row["root_id"]): row for row in read_jsonl(args.roots_file.resolve())}
    try:
        return rows[str(args.root_id)]
    except KeyError as exc:
        raise SystemExit(f"root id not found: {args.root_id}") from exc


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = _root(args)
    policy_seat = int(root["policy_seat"])
    opponent_dir = Path(root["opponent_path"]).resolve()
    parent_dir = args.parent_agent.resolve()
    seed = int(root["seed"])
    random.seed(seed)
    if policy_seat == 0:
        agent_a_dir, agent_b_dir = parent_dir, opponent_dir
    else:
        agent_a_dir, agent_b_dir = opponent_dir, parent_dir
    # Import the seeded engine before loading either agent.  Some packaged
    # agents carry a local ``cg`` compatibility directory; loading them first
    # would shadow the requested engine and silently remove the seed API.
    try:
        from cg.game import battle_finish, battle_select, battle_start
        cg_module = sys.modules.get("cg")
        cg_module_path = str(Path(getattr(cg_module, "__file__", "")).resolve())
        engine_root = str(args.engine_dir.resolve())
        engine_import_ok = bool(cg_module_path) and (
            cg_module_path == engine_root
            or cg_module_path.startswith(engine_root + str(Path("/")))
            or cg_module_path.startswith(engine_root + "\\")
        )
    except Exception as exc:
        return {
            "schema_version": "archaludon_formal_realized_counterfactual_result.v1",
            "root_id": root["root_id"],
            "branch": args.branch,
            "alternative_semantic_id": args.alternative_semantic,
            "status": "invalid_engine_import_shadow",
            "started": False,
            "engine_import_error": f"{type(exc).__name__}: {exc}",
            "cg_module_path": None,
            "engine_import_ok": False,
        }
    if not engine_import_ok:
        return {
            "schema_version": "archaludon_formal_realized_counterfactual_result.v1",
            "root_id": root["root_id"],
            "branch": args.branch,
            "alternative_semantic_id": args.alternative_semantic,
            "status": "invalid_engine_import_shadow",
            "started": False,
            "cg_module_path": cg_module_path,
            "engine_root": engine_root,
            "engine_import_ok": False,
        }

    deck_a = read_deck(agent_a_dir / "deck.csv")
    deck_b = read_deck(agent_b_dir / "deck.csv")
    agent_a = load_agent(agent_a_dir, f"realized_a_{root['root_id']}")
    agent_b = load_agent(agent_b_dir, f"realized_b_{root['root_id']}")
    agents = [agent_a, agent_b]
    for agent in agents:
        module_random = getattr(getattr(agent, "module", None), "random", None)
        if hasattr(module_random, "seed"):
            module_random.seed(seed)

    obs, start_data = battle_start(deck_a, deck_b, seed=seed)
    if not obs:
        return {
            "schema_version": "archaludon_formal_realized_counterfactual_result.v1",
            "root_id": root["root_id"],
            "branch": args.branch,
            "alternative_semantic_id": args.alternative_semantic,
            "status": "start_fault",
            "started": False,
            "start_error_player": getattr(start_data, "errorPlayer", None),
            "start_error_type": getattr(start_data, "errorType", None),
            "cg_module_path": cg_module_path,
            "engine_root": engine_root,
            "engine_import_ok": engine_import_ok,
        }

    target_callback = int(root["callback_index"])
    steps = 0
    action_errors = 0
    root_match = False
    prefix_match = True
    chosen_root_action: list[int] | None = None
    root_observation_hash = None
    root_parent_semantic = None
    root_legal_semantics: list[str] = []
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
                root_observation_hash = normalized_public_hash(obs)
                root_parent_semantic = _semantic(obs, parent_action)
                root_legal = singleton_action_semantics(obs)
                root_legal_semantics = sorted(str(row["semantic_id"]) for row in root_legal)
                expected_legal = sorted(
                    str(row.get("semantic_id")) for row in root.get("legal_semantic_action_set") or []
                )
                root_match = (
                    root_observation_hash == str(root["public_hash"])
                    and root_parent_semantic == str(root["parent_semantic_action"])
                    and root_legal_semantics == expected_legal
                )
                if not root_match:
                    prefix_match = False
                    status = "root_mismatch"
                    break
                if args.branch == "alternative":
                    selected = next(
                        (row for row in root_legal if str(row["semantic_id"]) == str(args.alternative_semantic)),
                        None,
                    )
                    if selected is None:
                        prefix_match = False
                        status = "alternative_not_legal"
                        break
                    action = list(selected["action"])
                chosen_root_action = list(action)
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
    return {
        "schema_version": "archaludon_formal_realized_counterfactual_result.v1",
        "root_id": root["root_id"],
        "branch": args.branch,
        "alternative_semantic_id": args.alternative_semantic,
        "root_match": root_match,
        "prefix_match": prefix_match,
        "root_observation_hash": root_observation_hash,
        "root_parent_semantic": root_parent_semantic,
        "root_legal_semantics": root_legal_semantics,
        "expected_public_hash": root.get("public_hash"),
        "expected_parent_semantic": root.get("parent_semantic_action"),
        "chosen_root_action": chosen_root_action,
        "status": status,
        "started": True,
        "terminal_result": final_current.get("result"),
        "steps": steps,
        "turn": final_current.get("turn"),
        "action_errors": action_errors,
        "hit_max_steps": steps >= args.max_steps and final_current.get("result") in (None, -1),
        "policy_seat": policy_seat,
        "acting_seat": root.get("acting_seat"),
        "seed": seed,
        "opponent_family": root.get("opponent_family"),
        "context_tags": list(root.get("context_tags") or []),
        "cg_module_path": cg_module_path,
        "engine_root": engine_root,
        "engine_import_ok": engine_import_ok,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--parent-agent", type=Path, required=True)
    parser.add_argument("--roots-file", type=Path, required=True)
    parser.add_argument("--root-id", required=True)
    parser.add_argument("--branch", choices=("parent", "alternative"), required=True)
    parser.add_argument("--alternative-semantic", default="")
    parser.add_argument("--max-steps", type=int, default=1000)
    args = parser.parse_args()
    if args.branch == "alternative" and not args.alternative_semantic:
        parser.error("--alternative-semantic is required for alternative branch")
    ensure_engine_on_path(args.engine_dir)
    result = run(args)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True), flush=True)
    if result.get("status") not in {"complete"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
