"""Root recomputation for the immutable Rule 1 replay shadow."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
IMPL = Path(__file__).resolve().parent
RAW = IMPL / "shadow_raw"
SILVER = ROOT / "analysis_outputs/reference_agents/historical_silver_archaludon_54495224"
CANDIDATE = ROOT / "autonomous_gold_20260715/candidates/archaludon_historical_silver_single_resolver_salvage_v1"
ENGINE = ROOT / "analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine"

sys.dont_write_bytecode = True
sys.path[:0] = [str(CANDIDATE), str(ENGINE), str(ROOT), str(ROOT / "tools")]
from rl_ptcg.label_replay_rollout import replay_decisions  # noqa: E402


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path / "main.py")
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reset(module) -> None:
    if hasattr(module, "_setup_ledger"):
        module._setup_ledger = None
    parent = getattr(module, "_parent", module)
    if hasattr(parent, "_opp_last_attack_id"):
        parent._opp_last_attack_id = None
    if hasattr(parent, "_cur_turn_logs"):
        parent._cur_turn_logs.clear()


def valid_action(obs: dict, action) -> bool:
    select = obs.get("select") or {}
    options = select.get("option") or []
    minimum = select.get("minCount", 0)
    maximum = select.get("maxCount", 0)
    return bool(
        isinstance(action, list)
        and all(isinstance(value, int) and not isinstance(value, bool) for value in action)
        and len(action) == len(set(action))
        and minimum <= len(action) <= maximum
        and all(0 <= value < len(options) for value in action)
    )


def selected_card(obs: dict, action: list[int]):
    if len(action) != 1:
        return None
    option = obs["select"]["option"][action[0]]
    seat = option.get("playerIndex")
    index = option.get("index")
    players = (obs.get("current") or {}).get("players") or []
    if not isinstance(seat, int) or not isinstance(index, int) or seat >= len(players):
        return None
    hand = (players[seat] or {}).get("hand") or []
    if not 0 <= index < len(hand):
        return None
    return hand[index]


def option_card_rows(obs: dict):
    players = (obs.get("current") or {}).get("players") or []
    rows = []
    for position, option in enumerate((obs.get("select") or {}).get("option") or []):
        seat = option.get("playerIndex")
        index = option.get("index")
        if not isinstance(seat, int) or not isinstance(index, int) or seat >= len(players):
            rows.append((position, None, None))
            continue
        hand = (players[seat] or {}).get("hand") or []
        card = hand[index] if 0 <= index < len(hand) else None
        rows.append((position, None if card is None else card.get("id"), None if card is None else card.get("serial")))
    return rows


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


left = load(SILVER, "rule1_root_left")
right = load(CANDIDATE, "rule1_root_right")
reports = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(RAW.glob("*.json"))]
errors = sorted(RAW.glob("*.txt"))
differences = []
invalid = []
exception_telemetry = []
decision_total = 0

for report in reports:
    replay = json.loads(Path(report["replay"]).read_text(encoding="utf-8"))
    seat = report["target_seat"]
    reset(left)
    reset(right)
    replay_differences = []
    for step, obs, recorded in replay_decisions(replay, seat):
        decision_total += 1
        left_action = left.agent(copy.deepcopy(obs))
        right_action = right.agent(copy.deepcopy(obs))
        if not valid_action(obs, left_action):
            invalid.append((Path(report["replay"]).name, step, "left", left_action))
        if not valid_action(obs, right_action):
            invalid.append((Path(report["replay"]).name, step, "right", right_action))
        telemetry = copy.deepcopy(right._last_telemetry)
        if str(telemetry.get("rejection_reason", "")).startswith("wrapper_exception:"):
            exception_telemetry.append((Path(report["replay"]).name, step, telemetry))
        if left_action == right_action:
            continue
        card = selected_card(obs, right_action)
        option_rows = option_card_rows(obs)
        duraludon_serials = sorted(serial for _, card_id, serial in option_rows if card_id == 169)
        row = {
            "episode": Path(report["replay"]).stem,
            "seat": seat,
            "step": step,
            "turn": (obs.get("current") or {}).get("turn"),
            "context": (obs.get("select") or {}).get("context"),
            "left_action": left_action,
            "right_action": right_action,
            "selected_card_id": None if card is None else card.get("id"),
            "selected_serial": None if card is None else card.get("serial"),
            "minimum_duraludon_serial": duraludon_serials[0] if duraludon_serials else None,
            "telemetry": telemetry,
        }
        replay_differences.append(row)
        differences.append(row)
    if len(replay_differences) != report["difference_count"]:
        raise AssertionError(f"raw/root difference mismatch: {report['replay']}")

checks = {
    "json_reports": len(reports),
    "error_records": len(errors),
    "decisions": decision_total,
    "differences": len(differences),
    "difference_seats": {str(seat): sum(row["seat"] == seat for row in differences) for seat in (0, 1)},
    "invalid_actions": invalid,
    "wrapper_exceptions": exception_telemetry,
    "all_turn_zero": all(row["turn"] == 0 for row in differences),
    "all_setup_bench": all(row["context"] == 2 for row in differences),
    "all_parent_empty": all(row["left_action"] == [] for row in differences),
    "all_candidate_one": all(len(row["right_action"]) == 1 for row in differences),
    "all_duraludon": all(row["selected_card_id"] == 169 for row in differences),
    "all_minimum_serial": all(row["selected_serial"] == row["minimum_duraludon_serial"] for row in differences),
    "all_cinderace_commit": all(row["telemetry"].get("setup_active_card_id") == 666 for row in differences),
    "all_parent_called_once": all(row["telemetry"].get("parent_call_count") == 1 for row in differences),
    "all_no_owner": all(row["telemetry"].get("owner_before") is None and row["telemetry"].get("owner_after") is None for row in differences),
    "candidate_main_sha256": sha256(CANDIDATE / "main.py"),
    "candidate_deck_sha256": sha256(CANDIDATE / "deck.csv"),
    "differences_detail": differences,
}

print(json.dumps(checks, indent=2, sort_keys=True))
