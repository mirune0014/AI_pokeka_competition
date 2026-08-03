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
    / "archaludon/candidates"
    / "archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1"
)
CANDIDATE = (
    ROOT
    / "archaludon/candidates"
    / "archaludon_historical_silver_single_resolver_salvage_rule10_trial_v1"
)
ENGINE = ROOT / "_local_generated/analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine"
CURRENT = ROOT / "archaludon/live/55155015/analysis_20260802/refresh"
HISTORICAL = (
    ROOT
    / "archaludon/live/55070349/refresh_20260729_1241"
    / "shadow_corpus_196_prior_plus_11_new"
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


baseline = load(BASELINE, "rule10_shadow_rule5")
sys.modules.pop("_historical_silver_parent", None)
candidate = load(CANDIDATE, "rule10_shadow_candidate")


def reset(module):
    if hasattr(module, "_setup_ledger"):
        module._setup_ledger = None
    if hasattr(module, "_materialization_owner"):
        module._materialization_owner = None
    if hasattr(module, "_rule10_activity"):
        module._rule10_activity.update(
            starts=0,
            completions=0,
            aborts=0,
            faults=0,
            last_event="not_started",
            last_fault=None,
        )
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


def option_at(obs, action):
    options = (obs.get("select") or {}).get("option") or []
    if not isinstance(action, list) or len(action) != 1:
        return None
    position = action[0]
    return options[position] if isinstance(position, int) and 0 <= position < len(options) else None


def allowed_first_difference(obs, left, right, proposal, owner):
    parent_option = option_at(obs, left)
    candidate_option = option_at(obs, right)
    proof = {} if proposal is None else proposal.get("exact_proof") or {}
    keep = proof.get("keep_world") or {}
    play = proof.get("play_fml_world") or {}
    selected = selected_hand_card(obs, right)
    comparable = (
        "damage",
        "ko",
        "prize_take",
        "terminal",
        "board_out",
        "attacker",
        "target",
        "reply_active",
        "attack_id",
        "own_active_ready",
        "own_ready_backups",
    )
    return bool(
        proposal is not None
        and proposal.get("rule_id") == candidate._RULE10_ID
        and proposal.get("purpose") == "EXACT_FML_PUBLIC_RETURN_KO_OR_BOARDOUT_PREVENTION"
        and isinstance(owner, dict)
        and owner.get("stage") == "FML_EMITTED"
        and isinstance(parent_option, dict)
        and parent_option.get("type") == 13
        and parent_option.get("attackId") == owner.get("attack_id")
        and isinstance(candidate_option, dict)
        and candidate_option.get("type") == 7
        and selected is not None
        and selected.get("id") == candidate._FULL_METAL_LAB
        and selected.get("serial") == (owner.get("fml_ref") or (None, None))[1]
        and all(keep.get(key) == play.get(key) for key in comparable)
        and keep.get("terminal") is False
        and keep.get("board_out") is False
        and bool(proof.get("threshold_changes"))
        and proof.get("no_opponent_protection") is True
    )


sources = [
    ("current", path) for path in sorted(CURRENT.glob("episode_*_replay.json"))
] + [
    ("historical", path) for path in sorted(HISTORICAL.glob("episode_*_replay.json"))
]
manifest = []
snapshot = hashlib.sha256()
for corpus, replay_path in sources:
    digest = hashlib.sha256(replay_path.read_bytes()).hexdigest().upper()
    manifest.append(
        {
            "corpus": corpus,
            "name": replay_path.name,
            "path": str(replay_path),
            "sha256": digest,
            "size": replay_path.stat().st_size,
        }
    )
    snapshot.update(corpus.encode("utf-8"))
    snapshot.update(replay_path.name.encode("utf-8"))
    snapshot.update(bytes.fromhex(digest))
manifest_hash = snapshot.hexdigest().upper()
(HERE / "shadow_source_manifest.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
)

differences = []
activity_events = []
invalid_actions = []
exceptions = []
malformed = []
callbacks = 0
activity = {"starts": 0, "completions": 0, "aborts": 0, "faults": 0}

for corpus, replay_path in sources:
    try:
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
    except Exception as exc:
        malformed.append(
            {
                "corpus": corpus,
                "replay": str(replay_path),
                "exception": type(exc).__name__,
                "message": str(exc),
            }
        )
        continue
    for seat in (0, 1):
        reset(baseline)
        reset(candidate)
        previous = dict(candidate._rule10_activity)
        first_difference_seen = False
        try:
            for step, obs, _recorded in replay_decisions(replay, seat):
                callbacks += 1
                left = baseline.agent(copy.deepcopy(obs))
                right = candidate.agent(copy.deepcopy(obs))
                telemetry = copy.deepcopy(candidate._last_telemetry)
                proposal = copy.deepcopy(candidate._last_proposal)
                owner = copy.deepcopy(candidate._materialization_owner)
                current_activity = dict(candidate._rule10_activity)
                delta = {
                    key: current_activity[key] - previous[key]
                    for key in activity
                }
                if any(delta.values()):
                    activity_events.append(
                        {
                            "corpus": corpus,
                            "replay": replay_path.name,
                            "seat": seat,
                            "step": step,
                            "delta": delta,
                            "last_event": current_activity["last_event"],
                            "last_fault": current_activity["last_fault"],
                            "owner": owner,
                            "telemetry": telemetry,
                        }
                    )
                    for key in activity:
                        activity[key] += delta[key]
                previous = current_activity
                if not valid_action(obs, left):
                    invalid_actions.append(
                        {"corpus": corpus, "replay": replay_path.name, "seat": seat, "step": step, "side": "rule5", "action": left}
                    )
                if not valid_action(obs, right):
                    invalid_actions.append(
                        {"corpus": corpus, "replay": replay_path.name, "seat": seat, "step": step, "side": "rule10", "action": right}
                    )
                if str(telemetry.get("rejection_reason", "")).startswith("wrapper_exception:"):
                    exceptions.append(
                        {"corpus": corpus, "replay": replay_path.name, "seat": seat, "step": step, "telemetry": telemetry}
                    )
                if left == right:
                    continue
                allowed = allowed_first_difference(obs, left, right, proposal, owner)
                differences.append(
                    {
                        "corpus": corpus,
                        "replay": replay_path.name,
                        "seat": seat,
                        "step": step,
                        "turn": (obs.get("current") or {}).get("turn"),
                        "action_count": (obs.get("current") or {}).get("turnActionCount"),
                        "context": (obs.get("select") or {}).get("context"),
                        "first_for_replay_seat": not first_difference_seen,
                        "classification": None if proposal is None else proposal.get("purpose"),
                        "allowed": allowed,
                        "rule5_action": left,
                        "rule10_action": right,
                        "rule5_option": option_at(obs, left),
                        "rule10_option": option_at(obs, right),
                        "exact_proof": None if proposal is None else proposal.get("exact_proof"),
                        "owner": owner,
                        "telemetry": telemetry,
                    }
                )
                first_difference_seen = True
        except Exception as exc:
            exceptions.append(
                {"corpus": corpus, "replay": replay_path.name, "seat": seat, "step": None, "exception": type(exc).__name__, "message": str(exc)}
            )

summary = {
    "source_path_count": len(sources),
    "current_path_count": sum(corpus == "current" for corpus, _path in sources),
    "historical_path_count": sum(corpus == "historical" for corpus, _path in sources),
    "ordered_corpus_sha256": manifest_hash,
    "readable_replays": len(sources) - len(malformed),
    "seats_per_replay": 2,
    "malformed_replays": malformed,
    "callbacks": callbacks,
    "activity": activity,
    "activity_event_count": len(activity_events),
    "action_differences": len(differences),
    "first_differences": sum(row["first_for_replay_seat"] for row in differences),
    "allowed_differences": sum(row["allowed"] for row in differences),
    "all_differences_allowed": all(row["allowed"] for row in differences),
    "invalid_actions": invalid_actions,
    "exceptions": exceptions,
}
(HERE / "shadow_differences.json").write_text(
    json.dumps(differences, indent=2, sort_keys=True), encoding="utf-8"
)
(HERE / "shadow_summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
)
(HERE / "shadow_activity_events.json").write_text(
    json.dumps(activity_events, indent=2, sort_keys=True), encoding="utf-8"
)
print(json.dumps(summary, indent=2, sort_keys=True))
