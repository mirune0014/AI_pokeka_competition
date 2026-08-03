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
    / "archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1"
)
CANDIDATE = (
    ROOT
    / "autonomous_gold_20260715/candidates"
    / "archaludon_historical_silver_single_resolver_salvage_rule9_trial_v1"
)
ENGINE = ROOT / "analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/seeded_engine"
CURRENT = ROOT / "autonomous_gold_20260715/live/55155015/analysis_20260802/refresh"
HISTORICAL = (
    ROOT
    / "autonomous_gold_20260715/live/55070349/refresh_20260729_1241"
    / "shadow_corpus_196_prior_plus_11_new"
)

sys.dont_write_bytecode = True
sys.path[:0] = [str(ENGINE), str(ROOT), str(ROOT / "tools")]
from rl_ptcg.label_replay_rollout import replay_decisions  # noqa: E402


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


baseline = load(BASELINE, "rule9_shadow_rule5")
sys.modules.pop("_historical_silver_parent", None)
candidate = load(CANDIDATE, "rule9_shadow_candidate")


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


def option_semantic(obs, position):
    select = obs.get("select") or {}
    options = select.get("option") or []
    if not isinstance(position, int) or not 0 <= position < len(options):
        return {"kind": "INVALID", "position": position}
    option = options[position]
    option_type = option.get("type")
    current = obs.get("current") or {}
    players = current.get("players") or []
    seat = current.get("yourIndex")
    result = {
        "kind": option_type,
        "position": position,
        "card_id": None,
        "serial": None,
        "owner": option.get("playerIndex", seat),
        "attack_id": option.get("attackId"),
        "area": option.get("area"),
    }
    if option_type == 7 and seat in (0, 1) and len(players) == 2:
        hand = (players[seat] or {}).get("hand") or []
        index = option.get("index")
        if isinstance(index, int) and 0 <= index < len(hand):
            result.update(card_id=hand[index].get("id"), serial=hand[index].get("serial"))
    elif option_type == 3:
        owner = option.get("playerIndex")
        index = option.get("index")
        if option.get("area") == 12:
            zone = current.get("looking") or []
        elif option.get("area") == 5 and owner in (0, 1) and len(players) == 2:
            zone = (players[owner] or {}).get("bench") or []
        elif option.get("area") == 4 and owner in (0, 1) and len(players) == 2:
            zone = (players[owner] or {}).get("active") or []
        else:
            zone = []
        if isinstance(index, int) and 0 <= index < len(zone):
            result.update(card_id=zone[index].get("id"), serial=zone[index].get("serial"))
    return result


def action_semantic(obs, action):
    if not isinstance(action, list):
        return {"action": action, "items": None}
    return {"action": action, "items": [option_semantic(obs, value) for value in action]}


def owner_evidence(owner):
    if not isinstance(owner, dict):
        return None
    return {
        "stage": owner.get("stage"),
        "seat": owner.get("seat"),
        "turn": owner.get("turn"),
        "entry_action_count": owner.get("action_count"),
        "gear_ref": owner.get("gear_ref"),
        "boss_ref": owner.get("boss_ref"),
        "attack_id": owner.get("attack_id"),
        "attacker": owner.get("attacker"),
        "current_target": owner.get("current_target"),
        "current_damage": owner.get("current_damage"),
        "current_take": owner.get("current_take"),
        "target": owner.get("target"),
        "target_damage": owner.get("target_damage"),
        "target_take": owner.get("target_take"),
        "remaining_prize": owner.get("remaining_prize"),
        "entry_deck_count": owner.get("entry_deck_count"),
        "reveal_refs": owner.get("reveal_refs"),
        "reveal_supporters": owner.get("reveal_supporters"),
    }


def allowed_difference(purpose, candidate_semantic, owner):
    items = candidate_semantic.get("items")
    if not isinstance(owner, dict):
        return False
    if purpose == "RULE9_REVEAL_BOUND_BOSS":
        return bool(
            isinstance(items, list)
            and len(items) == 1
            and items[0].get("kind") == 3
            and items[0].get("card_id") == candidate._BOSS
            and items[0].get("serial") == (owner.get("boss_ref") or (None, None))[1]
        )
    if purpose == "RULE9_REVEAL_UNSUPPORTED_EMPTY":
        return bool(items == [] and owner.get("boss_ref") is None)
    if purpose == "RULE9_POST_ACQUISITION_BOSS_PLAY":
        return bool(
            isinstance(items, list)
            and len(items) == 1
            and items[0].get("kind") == 7
            and items[0].get("card_id") == candidate._BOSS
            and items[0].get("serial") == (owner.get("boss_ref") or (None, None))[1]
        )
    if purpose == "RULE9_BOUND_BOSS_TARGET":
        return bool(
            isinstance(items, list)
            and len(items) == 1
            and items[0].get("kind") == 3
            and items[0].get("serial") == owner.get("target_serial")
        )
    if purpose == "RULE9_BOUND_SAME_ATTACK":
        return bool(
            isinstance(items, list)
            and len(items) == 1
            and items[0].get("kind") == 13
            and items[0].get("attack_id") == owner.get("attack_id")
            and owner.get("target_take") == owner.get("remaining_prize")
        )
    return False


sources = [
    ("current", path) for path in sorted(CURRENT.glob("episode_*_replay.json"))
] + [
    ("historical", path)
    for path in sorted(HISTORICAL.glob("episode_*_replay.json"))
]
manifest = []
snapshot = hashlib.sha256()
for corpus, replay_path in sources:
    digest = hashlib.sha256(replay_path.read_bytes()).hexdigest().upper()
    row = {
        "corpus": corpus,
        "name": replay_path.name,
        "path": str(replay_path),
        "sha256": digest,
        "size": replay_path.stat().st_size,
    }
    manifest.append(row)
    snapshot.update(corpus.encode("utf-8"))
    snapshot.update(replay_path.name.encode("utf-8"))
    snapshot.update(bytes.fromhex(digest))
manifest_hash = snapshot.hexdigest().upper()
(HERE / "shadow_source_manifest.json").write_text(
    json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
)

differences = []
invalid_actions = []
exceptions = []
malformed = []
callbacks = 0
activity = {
    "starts": 0,
    "boss_hits": 0,
    "misses": 0,
    "boss_plays": 0,
    "boss_targets": 0,
    "terminal_attacks_emitted": 0,
    "attack_confirmations": 0,
    "irreversible_aborts": 0,
}

for corpus, replay_path in sources:
    try:
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
    except Exception as exc:
        malformed.append(
            {
                "corpus": corpus,
                "replay": replay_path.name,
                "exception": type(exc).__name__,
                "message": str(exc),
            }
        )
        continue
    for seat in (0, 1):
        reset(baseline)
        reset(candidate)
        first_difference_seen = False
        try:
            for step, obs, _recorded in replay_decisions(replay, seat):
                callbacks += 1
                left = baseline.agent(copy.deepcopy(obs))
                right = candidate.agent(copy.deepcopy(obs))
                telemetry = copy.deepcopy(candidate._last_telemetry)
                proposal = copy.deepcopy(candidate._last_proposal)
                owner = copy.deepcopy(candidate._materialization_owner)
                if not valid_action(obs, left):
                    invalid_actions.append(
                        {
                            "corpus": corpus,
                            "replay": replay_path.name,
                            "seat": seat,
                            "step": step,
                            "side": "rule5",
                            "action": left,
                        }
                    )
                if not valid_action(obs, right):
                    invalid_actions.append(
                        {
                            "corpus": corpus,
                            "replay": replay_path.name,
                            "seat": seat,
                            "step": step,
                            "side": "rule9",
                            "action": right,
                        }
                    )
                reason = str(telemetry.get("rejection_reason", ""))
                if reason.startswith("wrapper_exception:"):
                    exceptions.append(
                        {
                            "corpus": corpus,
                            "replay": replay_path.name,
                            "seat": seat,
                            "step": step,
                            "telemetry": telemetry,
                        }
                    )
                if reason.startswith("rule9_irreversible_abort:"):
                    activity["irreversible_aborts"] += 1
                if reason == "rule9_attack_dispatched":
                    activity["attack_confirmations"] += 1
                purpose = None if proposal is None else proposal.get("purpose")
                if (
                    proposal is not None
                    and proposal.get("rule_id") == candidate._RULE9_ID
                    and not telemetry.get("duplicate_retry")
                ):
                    key = {
                        "RULE9_PARENT_GEAR_ENTRY_SAME_ACTION": "starts",
                        "RULE9_REVEAL_BOUND_BOSS": "boss_hits",
                        "RULE9_REVEAL_UNSUPPORTED_EMPTY": "misses",
                        "RULE9_POST_ACQUISITION_BOSS_PLAY": "boss_plays",
                        "RULE9_BOUND_BOSS_TARGET": "boss_targets",
                        "RULE9_BOUND_SAME_ATTACK": "terminal_attacks_emitted",
                    }.get(purpose)
                    if key is not None:
                        activity[key] += 1
                if left == right:
                    continue
                parent_semantic = action_semantic(obs, left)
                candidate_semantic = action_semantic(obs, right)
                row = {
                    "corpus": corpus,
                    "replay": replay_path.name,
                    "seat": seat,
                    "step": step,
                    "turn": (obs.get("current") or {}).get("turn"),
                    "action_count": (obs.get("current") or {}).get("turnActionCount"),
                    "context": (obs.get("select") or {}).get("context"),
                    "first_for_replay_seat": not first_difference_seen,
                    "classification": purpose,
                    "rule5_semantic": parent_semantic,
                    "rule9_semantic": candidate_semantic,
                    "exact_proof": None if proposal is None else proposal.get("exact_proof"),
                    "stage_ledger": owner_evidence(owner),
                    "telemetry": telemetry,
                }
                row["allowed"] = bool(
                    proposal is not None
                    and proposal.get("rule_id") == candidate._RULE9_ID
                    and allowed_difference(purpose, candidate_semantic, owner)
                )
                differences.append(row)
                first_difference_seen = True
        except Exception as exc:
            exceptions.append(
                {
                    "corpus": corpus,
                    "replay": replay_path.name,
                    "seat": seat,
                    "step": None,
                    "exception": type(exc).__name__,
                    "message": str(exc),
                }
            )

classes = sorted(
    {
        "RULE9_REVEAL_BOUND_BOSS",
        "RULE9_REVEAL_UNSUPPORTED_EMPTY",
        "RULE9_POST_ACQUISITION_BOSS_PLAY",
        "RULE9_BOUND_BOSS_TARGET",
        "RULE9_BOUND_SAME_ATTACK",
    }
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
    "action_differences": len(differences),
    "first_differences": sum(row["first_for_replay_seat"] for row in differences),
    "difference_class_counts": {
        value: sum(row["classification"] == value for row in differences)
        for value in classes
    },
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
print(json.dumps(summary, indent=2, sort_keys=True))
