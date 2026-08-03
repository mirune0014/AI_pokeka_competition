"""Static correct-seat parent/candidate shadow for the available Task 5 anchor."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
AUTO = ROOT / "archaludon"
PARENT_DIR = (
    AUTO / "candidates"
    / "archaludon_public_pre_attack_executable_successor_bench_zero_continuity_gate_v1"
)
CANDIDATE_DIR = (
    AUTO / "candidates"
    / "archaludon_public_poke_pad_declared_executable_role_transaction_v1"
)
REPLAYS = (Path(r"C:\Users\amuam\Downloads\89347400.json"),)
sys.path[:0] = [str(CANDIDATE_DIR), str(ROOT), str(ROOT / "infrastructure" / "tools")]

from ptcg_common import read_deck  # noqa: E402
from research.rl_ptcg.label_replay_rollout import (  # noqa: E402
    replay_decisions,
    target_seat_for_deck,
)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def reset(module):
    if hasattr(module, "_pfc_clear"):
        module._pfc_clear("shadow_reset")
    if hasattr(module, "_pcrd_clear"):
        module._pcrd_clear("shadow_reset")
    if hasattr(module, "_cum_reset_runtime"):
        module._cum_reset_runtime("shadow_reset")
    for name in getattr(module, "_PRACTICE_OWNER_GLOBALS", ()):
        if hasattr(module, name):
            setattr(module, name, None)
    ledger = getattr(module, "_public_boss_ledger", None)
    if isinstance(ledger, dict):
        ledger["transaction"] = None


PARENT = load("task5_shadow_parent", PARENT_DIR / "main.py")
CANDIDATE = load("task5_shadow_candidate", CANDIDATE_DIR / "main.py")
output = {
    "parent_main_sha256": sha(PARENT_DIR / "main.py"),
    "candidate_main_sha256": sha(CANDIDATE_DIR / "main.py"),
    "episodes": {},
    "limitations": (
        "Static replay snapshots establish only recorded-callback shadow behavior; "
        "they cannot establish Task 5 multi-callback counterfactual continuity. "
        "That property is checked by run_focused_fixtures.py."
    ),
    "unavailable_requested_episodes": [89285518, 89282820],
}

for path in REPLAYS:
    replay = json.loads(path.read_text(encoding="utf-8"))
    seat = target_seat_for_deck(replay, read_deck(CANDIDATE_DIR / "deck.csv"))
    reset(PARENT)
    reset(CANDIDATE)
    rows = []
    invalid = []
    for step, obs, recorded in replay_decisions(replay, seat):
        left = PARENT.agent(copy.deepcopy(obs))
        right = CANDIDATE.agent(copy.deepcopy(obs))
        left_obs = PARENT.to_observation_class(obs)
        right_obs = CANDIDATE.to_observation_class(obs)
        if not PARENT._cum_valid_action(left_obs, left):
            invalid.append({"step": step, "side": "parent", "action": left})
        if not CANDIDATE._cum_valid_action(right_obs, right):
            invalid.append({"step": step, "side": "candidate", "action": right})
        left_semantic = PARENT._cum_jsonable(PARENT._cum_action_semantic(left_obs, left))
        right_semantic = CANDIDATE._cum_jsonable(CANDIDATE._cum_action_semantic(right_obs, right))
        if left_semantic != right_semantic:
            rows.append({
                "step": step,
                "parent_action": left,
                "candidate_action": right,
                "recorded_action": list(recorded),
                "parent_semantic": left_semantic,
                "candidate_semantic": right_semantic,
                "classification": "non_task5_parent_candidate_difference",
                "task5_stage": (
                    None if CANDIDATE._pfc_transaction is None
                    else CANDIDATE._pfc_transaction.get("stage")
                ),
            })
    episode_id = int(path.stem)
    output["episodes"][str(episode_id)] = {
        "path": str(path),
        "replay_sha256": sha(path),
        "correct_seat": seat,
        "decision_count": sum(1 for _ in replay_decisions(replay, seat)),
        "difference_count": len(rows),
        "differences": rows,
        "invalid_action_count": len(invalid),
        "invalid_actions": invalid,
        "task5_specific_difference_count": sum(
            row["task5_stage"] is not None for row in rows
        ),
    }

target = Path(__file__).with_name("replay_shadow_results.json")
target.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(output["episodes"], sort_keys=True))
