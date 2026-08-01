"""Task 6 anchor replay shadow with candidate transaction telemetry."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
AUTO = ROOT / "autonomous_gold_20260715"
PARENT = AUTO / "candidates" / (
    "archaludon_public_poke_pad_declared_executable_role_transaction_v1"
)
CANDIDATE = AUTO / "candidates" / (
    "archaludon_public_ultra_ball_declared_complete_route_transaction_v1"
)
REPLAYS = (
    AUTO / "live/55155015/analysis_20260802/refresh/episode_89280661_replay.json",
    AUTO / "live/55155015/analysis_20260802/refresh/episode_89291523_replay.json",
    Path(r"C:\Users\amuam\Downloads\89347400.json"),
)
sys.path[:0] = [str(CANDIDATE), str(ROOT), str(ROOT / "tools")]

from ptcg_common import read_deck  # noqa: E402
from rl_ptcg.label_replay_rollout import (  # noqa: E402
    replay_decisions,
    target_seat_for_deck,
)


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path / "main.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


parent = load(PARENT, "task6_shadow_parent")
candidate = load(CANDIDATE, "task6_shadow_candidate")
summaries = []
for replay_path in REPLAYS:
    raw = json.loads(replay_path.read_text(encoding="utf-8"))
    seat = target_seat_for_deck(raw, read_deck(CANDIDATE / "deck.csv"))
    differences = []
    rows = []
    for step, obs, recorded in replay_decisions(raw, seat):
        left = parent.agent(copy.deepcopy(obs))
        right = candidate.agent(copy.deepcopy(obs))
        parsed = candidate.to_observation_class(obs)
        left_semantic = candidate._cum_action_semantic(parsed, left)
        right_semantic = candidate._cum_action_semantic(parsed, right)
        telemetry = copy.deepcopy(candidate._pfc_last_telemetry)
        row = {
            "step": step,
            "turn": obs["current"]["turn"],
            "recorded": recorded,
            "left": left,
            "right": right,
            "left_semantic": candidate._cum_jsonable(left_semantic),
            "right_semantic": candidate._cum_jsonable(right_semantic),
            "task6_stage": telemetry.get("stage"),
            "task6_purpose": telemetry.get("purpose"),
            "task6_rejection": telemetry.get("rejection_reason"),
            "task6_transition": telemetry.get("transition_confirmation"),
            "task6_bindings": telemetry.get("bindings"),
        }
        rows.append(row)
        if left_semantic != right_semantic:
            differences.append(row)
    summaries.append({
        "episode": replay_path.stem,
        "replay": str(replay_path),
        "target_seat": seat,
        "decision_count": len(rows),
        "difference_count": len(differences),
        "differences": differences,
        "task6_rows": [
            row for row in rows
            if row["task6_purpose"] in {
                candidate._PFC_TASK6_FINISH_NOW,
                candidate._PFC_TASK6_ATTACK_NOW,
                candidate._PFC_TASK6_TURBO_SUCCESSOR,
                candidate._PFC_TASK6_ARCH_EX_BACKUP,
                candidate._PFC_TASK6_BASIC_SUCCESSOR,
            }
            or (row["task6_rejection"] or "").startswith("task6_")
        ],
    })

output = Path(__file__).with_name("replay_shadow_results.json")
output.write_text(
    json.dumps(summaries, indent=2, sort_keys=True), encoding="utf-8"
)
print(json.dumps([
    {
        "episode": row["episode"],
        "target_seat": row["target_seat"],
        "decision_count": row["decision_count"],
        "difference_count": row["difference_count"],
        "task6_row_count": len(row["task6_rows"]),
    }
    for row in summaries
], sort_keys=True))
