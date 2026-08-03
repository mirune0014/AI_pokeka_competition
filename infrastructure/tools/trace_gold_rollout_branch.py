"""Replay selected paired-rollout root branches with actor-view action traces."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import random
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.canonical_actions import canonicalize_prompt_action
from research.rl_ptcg.gold_oracle_runner import (
    _guess_from_payload,
    _load_tools,
    _resolve_inside,
    _rollout_scenario_seed,
    _seed_agent_randomness,
    reconstruct_rollout_input,
    sample_world_payloads,
    stable_seed,
    verify_oracle_output,
)


def _summary(observation, action, dataclass_to_dict):
    raw = dataclass_to_dict(observation)
    current = raw.get("current") or {}
    players = current.get("players") or []
    seat = int(current.get("yourIndex", 0))
    actor = players[seat] if seat < len(players) else {}
    active = (actor.get("active") or [{}])[0]
    return {
        "turn": current.get("turn"),
        "seat": seat,
        "active_card_id": active.get("id"),
        "active_hp": active.get("hp"),
        "hand_count": len(actor.get("hand") or []),
        "action": canonicalize_prompt_action(raw, action).to_dict(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--state-id", required=True)
    parser.add_argument("--batch-id", type=int, required=True)
    parser.add_argument("--hypothesis-signature", required=True)
    parser.add_argument("--opponent-policy-index", type=int, default=0)
    parser.add_argument("--action-id", action="append", required=True)
    parser.add_argument("--max-trace-steps", type=int, default=80)
    args = parser.parse_args()
    workspace = args.workspace_root.resolve()
    run = args.run_dir.resolve()
    verified = verify_oracle_output(run, workspace)
    manifest = json.loads((run / "run_manifest.json").read_text(encoding="ascii"))
    from infrastructure.tools.ptcg_common import ensure_engine_on_path
    ensure_engine_on_path(_resolve_inside(manifest["engine"]["path"], workspace))
    corpus = _resolve_inside(manifest["corpus"]["path"], workspace)
    states = [json.loads(line) for line in (corpus / "states.jsonl").read_text(encoding="ascii").splitlines()]
    state = next(item for item in states if item["state_id"] == args.state_id)
    working = dict(state)
    working["runner_baseline_path"] = manifest["baseline"]["path"]
    observation, scores, baseline_action, raw_actions, raw_to_semantic, _baseline_id = reconstruct_rollout_input(
        working, _resolve_inside(manifest["baseline"]["path"], workspace), workspace,
        "trace_reconstruct_%s" % args.state_id[:12],
    )
    semantic_to_raw = {identifier: list(raw) for raw, identifier in raw_to_semantic.items()}
    hypothesis = next(
        item for item in state["belief"]["hypotheses"]
        if item["signature"] == args.hypothesis_signature
    )
    policies = manifest["opponent_policies"][state["belief"]["archetype"]]
    policy = policies[args.opponent_policy_index]
    continuation = manifest["continuation_policies"][0]
    from cg.api import (
        all_card_data, search_begin, search_end, search_seed, search_step,
        to_observation_class,
    )
    basic_ids = {int(card.cardId) for card in all_card_data() if card.basic}
    worlds = sample_world_payloads(
        observation, state["own_deck"]["decklist"], hypothesis["decklist"], basic_ids,
        count=int(manifest["config"]["particles_per_scenario"]),
        seed_parts=(
            manifest["config"]["seed"], state["state_id"], args.batch_id,
            hypothesis["signature"], "world",
        ),
    )
    guess = _guess_from_payload(deepcopy(worlds[0]))
    scenario_seed = _rollout_scenario_seed(
        manifest["config"], state["state_id"], args.batch_id,
        hypothesis["signature"], policy, continuation,
    )
    native_seed = random.Random(scenario_seed).getrandbits(64)
    load_agent, AgentChooser = _load_tools()
    dataclass_to_dict = __import__("infrastructure.tools.ptcg_common", fromlist=["dataclass_to_dict"]).dataclass_to_dict
    traces = []
    for branch_number, action_id in enumerate(args.action_id):
        raw_root = semantic_to_raw[action_id]
        opponent = load_agent(
            _resolve_inside(policy["path"], workspace),
            "trace_opp_%d" % branch_number,
        )
        actor = load_agent(
            _resolve_inside(continuation["path"], workspace),
            "trace_actor_%d" % branch_number,
        )
        _seed_agent_randomness(
            (opponent, actor), stable_seed(scenario_seed, 0, "policy"),
        )
        modules = {
            int(state["acting_seat"]): AgentChooser(actor),
            1 - int(state["acting_seat"]): AgentChooser(opponent),
        }
        search_seed(int(native_seed) & 0xFFFFFFFF)
        root = search_begin(
            to_observation_class(deepcopy(observation)),
            list(guess.your_deck), list(guess.your_prize),
            list(guess.opponent_deck), list(guess.opponent_prize),
            list(guess.opponent_hand), list(guess.opponent_active), manual_coin=True,
        )
        branch = {"action_id": action_id, "steps": []}
        try:
            branch["steps"].append({"root": True, **_summary(root.observation, raw_root, dataclass_to_dict)})
            current = search_step(root.searchId, raw_root)
            for _ in range(args.max_trace_steps):
                raw_observation = dataclass_to_dict(current.observation)
                status = raw_observation.get("current") or {}
                result = status.get("result")
                if result not in (None, -1):
                    branch["terminal_result"] = result
                    break
                select = raw_observation.get("select") or {}
                options = select.get("option") or []
                if not options:
                    branch["stopped"] = "no options"
                    break
                seat = int(status.get("yourIndex", state["acting_seat"]))
                action = modules[seat].choose_options(current.observation)
                branch["steps"].append(_summary(current.observation, action, dataclass_to_dict))
                current = search_step(current.searchId, action)
            else:
                branch["stopped"] = "trace step limit"
        finally:
            search_end()
        traces.append(branch)
    print(json.dumps({
        "verified_run": verified,
        "state_id": state["state_id"],
        "batch_id": args.batch_id,
        "hypothesis_signature": hypothesis["signature"],
        "opponent_policy_id": policy["policy_id"],
        "scenario_seed": scenario_seed,
        "native_seed": native_seed,
        "world_id_input_index": 0,
        "traces": traces,
    }, sort_keys=True, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
