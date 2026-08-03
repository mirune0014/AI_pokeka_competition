from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASELINE = (
    ROOT
    / "autonomous_gold_20260715/candidates"
    / "archaludon_historical_silver_single_resolver_salvage_v1"
)
CANDIDATE = (
    ROOT
    / "autonomous_gold_20260715/candidates"
    / "archaludon_historical_silver_single_resolver_salvage_rule4_trial_v1"
)
ENGINE = ROOT / "_local_generated/analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine"
CURRENT = ROOT / "autonomous_gold_20260715/live/55155015/analysis_20260802/refresh"
HISTORICAL = (
    ROOT
    / "autonomous_gold_20260715/live/55070349/refresh_20260729_1241"
    / "shadow_corpus_196_prior_plus_11_new"
)
REFERENCE_RAW = (
    ROOT
    / "autonomous_gold_20260715/implementation"
    / "archaludon_historical_silver_single_resolver_salvage_v1/shadow_raw"
)

sys.dont_write_bytecode = True
sys.path[:0] = [str(ENGINE), str(ROOT), str(ROOT / "infrastructure" / "tools")]
from research.rl_ptcg.label_replay_rollout import replay_decisions  # noqa: E402


def load(path: Path, name: str):
    sys.path.insert(0, str(path))
    try:
        spec = importlib.util.spec_from_file_location(name, path / "main.py")
        if spec is None or spec.loader is None:
            raise AssertionError(path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(path))


baseline = load(BASELINE, "rule4_shadow_rule1")
sys.modules.pop("_historical_silver_parent", None)
candidate = load(CANDIDATE, "rule4_shadow_candidate")


def reset(module):
    if hasattr(module, "_setup_ledger"):
        module._setup_ledger = None
    if hasattr(module, "_materialization_owner"):
        module._materialization_owner = None
    parent = getattr(module, "_parent", module)
    if hasattr(parent, "_opp_last_attack_id"):
        parent._opp_last_attack_id = None
    if hasattr(parent, "_cur_turn_logs"):
        parent._cur_turn_logs.clear()


def valid_action(obs, action):
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


def selected_hand_card(obs, action):
    if not isinstance(action, list) or len(action) != 1:
        return None
    options = (obs.get("select") or {}).get("option") or []
    if not 0 <= action[0] < len(options):
        return None
    option = options[action[0]]
    if option.get("type") != 7:
        return None
    seat = option.get("playerIndex")
    if seat is None:
        seat = (obs.get("current") or {}).get("yourIndex")
    index = option.get("index")
    players = (obs.get("current") or {}).get("players") or []
    if not isinstance(seat, int) or seat not in (0, 1) or seat >= len(players):
        return None
    hand = (players[seat] or {}).get("hand")
    if not isinstance(hand, list) or not isinstance(index, int) or not 0 <= index < len(hand):
        return None
    return hand[index]


def materialization_evidence(obs, action):
    current = obs.get("current") or {}
    seat = current.get("yourIndex")
    players = current.get("players") or []
    mine = players[seat] if isinstance(seat, int) and 0 <= seat < len(players) else {}
    opponent = players[1 - seat] if isinstance(seat, int) and len(players) == 2 else {}
    options = (obs.get("select") or {}).get("option") or []
    option = options[action[0]] if isinstance(action, list) and len(action) == 1 else {}
    source = selected_hand_card(obs, action)
    if source is None and option.get("type") in (8, 9):
        source_seat = option.get("playerIndex", seat)
        source_index = option.get("index")
        source_hand = (
            players[source_seat].get("hand")
            if isinstance(source_seat, int) and 0 <= source_seat < len(players)
            else None
        )
        if isinstance(source_hand, list) and isinstance(source_index, int) and 0 <= source_index < len(source_hand):
            source = source_hand[source_index]
    target = None
    target_area = option.get("inPlayArea")
    target_index = option.get("inPlayIndex")
    if target_area == 4:
        zone = mine.get("active") or []
        target = zone[target_index] if isinstance(target_index, int) and 0 <= target_index < len(zone) else None
    elif target_area == 5:
        zone = mine.get("bench") or []
        target = zone[target_index] if isinstance(target_index, int) and 0 <= target_index < len(zone) else None
    active = (mine.get("active") or [None])[0]
    return {
        "selected_card_id": None if source is None else source.get("id"),
        "selected_card_serial": None if source is None else source.get("serial"),
        "target_card_id": None if target is None else target.get("id"),
        "target_serial": None if target is None else target.get("serial"),
        "target_appear_this_turn": None if target is None else target.get("appearThisTurn"),
        "target_energy_ids": [] if target is None else [card.get("id") for card in target.get("energyCards") or []],
        "target_energy_serials": [] if target is None else [card.get("serial") for card in target.get("energyCards") or []],
        "active_card_id": None if active is None else active.get("id"),
        "active_serial": None if active is None else active.get("serial"),
        "opponent_prize_count": len(opponent.get("prize") or []),
        "supporter_played": current.get("supporterPlayed"),
        "energy_attached": current.get("energyAttached"),
        "stadium_count": len(current.get("stadium") or []),
    }


current_paths = sorted(CURRENT.glob("episode_*_replay.json"))
historical_all = sorted(HISTORICAL.glob("episode_*_replay.json"))
historical_paths = sorted(
    sorted(
        historical_all,
        key=lambda path: hashlib.sha256(path.name.encode("utf-8")).hexdigest(),
    )[:32]
)
paths = current_paths + historical_paths
snapshot = hashlib.sha256()
for corpus, replay_path in (
    [("current", path) for path in current_paths]
    + [("historical_sample", path) for path in historical_paths]
):
    snapshot.update(corpus.encode())
    snapshot.update(replay_path.name.encode())
    snapshot.update(hashlib.sha256(replay_path.read_bytes()).digest())
manifest_hash = snapshot.hexdigest().upper()
if manifest_hash != "B88C25BC8F26F959F85D00D27FD7B148D22034D71B2588DF73AAF8C8E0B15004":
    raise AssertionError("frozen corpus snapshot mismatch")

differences = []
invalid_actions = []
exceptions = []
malformed = []
callbacks = 0
natural_starts = 0
confirmed_materializations = 0

for replay_path in paths:
    try:
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
    except Exception as exc:
        malformed.append(
            {"replay": str(replay_path), "exception": type(exc).__name__, "message": str(exc)}
        )
        continue
    prefix = "current_" if replay_path.parent == CURRENT else "historical_sample_"
    reference_report = REFERENCE_RAW / (prefix + replay_path.name)
    if not reference_report.exists():
        exceptions.append(
            {"replay": replay_path.name, "seat": None, "step": None, "exception": "MissingReferenceTargetSeat"}
        )
        continue
    seat = json.loads(reference_report.read_text(encoding="utf-8"))["target_seat"]
    for seat in (seat,):
        reset(baseline)
        reset(candidate)
        try:
            decisions = replay_decisions(replay, seat)
            for step, obs, _recorded in decisions:
                callbacks += 1
                left = baseline.agent(copy.deepcopy(obs))
                right = candidate.agent(copy.deepcopy(obs))
                telemetry = copy.deepcopy(candidate._last_telemetry)
                proposal = copy.deepcopy(candidate._last_proposal)
                if not valid_action(obs, left):
                    invalid_actions.append(
                        {"replay": replay_path.name, "seat": seat, "step": step, "side": "rule1", "action": left}
                    )
                if not valid_action(obs, right):
                    invalid_actions.append(
                        {"replay": replay_path.name, "seat": seat, "step": step, "side": "rule4", "action": right}
                    )
                if str(telemetry.get("rejection_reason", "")).startswith("wrapper_exception:"):
                    exceptions.append(
                        {"replay": replay_path.name, "seat": seat, "step": step, "telemetry": telemetry}
                    )
                if proposal is not None and proposal.get("rule_id") == candidate._RULE4_ID:
                    natural_starts += 1
                if str(telemetry.get("rejection_reason", "")).startswith("materialization_confirmed:"):
                    confirmed_materializations += 1
                if left == right:
                    continue
                parent_card = selected_hand_card(obs, left)
                classification = None if proposal is None else proposal.get("purpose")
                differences.append(
                    {
                        "replay": replay_path.name,
                        "seat": seat,
                        "step": step,
                        "turn": (obs.get("current") or {}).get("turn"),
                        "context": (obs.get("select") or {}).get("context"),
                        "rule1_action": left,
                        "rule4_action": right,
                        "parent_card_id": None if parent_card is None else parent_card.get("id"),
                        "parent_card_serial": None if parent_card is None else parent_card.get("serial"),
                        "classification": classification,
                        "materialization_evidence": materialization_evidence(obs, right),
                        "telemetry": telemetry,
                    }
                )
        except Exception as exc:
            exceptions.append(
                {"replay": replay_path.name, "seat": seat, "step": None, "exception": type(exc).__name__, "message": str(exc)}
            )

allowed = {
    candidate._ROUTE_DURALUDON,
    candidate._ROUTE_EVOLUTION,
    candidate._ROUTE_THIRD_METAL,
    candidate._ROUTE_LAB,
}
summary = {
    "source_path_count": len(paths),
    "current_path_count": len(current_paths),
    "historical_path_count": len(historical_paths),
    "ordered_corpus_sha256": manifest_hash,
    "readable_replays": len(paths) - len(malformed),
    "malformed_replays": malformed,
    "callbacks": callbacks,
    "natural_starts": natural_starts,
    "confirmed_materializations": confirmed_materializations,
    "action_differences": len(differences),
    "difference_class_counts": {
        value: sum(row["classification"] == value for row in differences)
        for value in sorted(allowed)
    },
    "all_differences_allowed": all(row["classification"] in allowed for row in differences),
    "all_difference_parents_lillie": all(row["parent_card_id"] == 1227 for row in differences),
    "invalid_actions": invalid_actions,
    "exceptions": exceptions,
}
(HERE / "shadow_differences.json").write_text(
    json.dumps(differences, indent=2, sort_keys=True), encoding="utf-8"
)
(HERE / "shadow_summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
)
print(json.dumps(summary, indent=2, sort_keys=True))
