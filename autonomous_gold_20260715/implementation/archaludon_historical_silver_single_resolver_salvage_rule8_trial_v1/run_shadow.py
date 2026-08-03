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
    / "archaludon_historical_silver_single_resolver_salvage_rule8_trial_v1"
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


baseline = load(BASELINE, "rule8_shadow_rule5")
sys.modules.pop("_historical_silver_parent", None)
candidate = load(CANDIDATE, "rule8_shadow_candidate")


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


def selected_attack(obs, action):
    if not isinstance(action, list) or len(action) != 1:
        return None
    options = (obs.get("select") or {}).get("option") or []
    if not 0 <= action[0] < len(options):
        return None
    option = options[action[0]]
    return option.get("attackId") if option.get("type") == 13 else None


def active_ref(obs, seat):
    players = (obs.get("current") or {}).get("players") or []
    if seat not in (0, 1) or len(players) != 2:
        return None
    active = (players[seat].get("active") or [None])[0]
    if active is None:
        return None
    return (active.get("id"), active.get("serial"), seat)


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
natural_starts = 0

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
        try:
            for step, obs, _recorded in replay_decisions(replay, seat):
                callbacks += 1
                left = baseline.agent(copy.deepcopy(obs))
                right = candidate.agent(copy.deepcopy(obs))
                telemetry = copy.deepcopy(candidate._last_telemetry)
                proposal = copy.deepcopy(candidate._last_proposal)
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
                            "side": "rule8",
                            "action": right,
                        }
                    )
                if str(telemetry.get("rejection_reason", "")).startswith("wrapper_exception:"):
                    exceptions.append(
                        {
                            "corpus": corpus,
                            "replay": replay_path.name,
                            "seat": seat,
                            "step": step,
                            "telemetry": telemetry,
                        }
                    )
                if proposal is not None and proposal.get("rule_id") == candidate._RULE8_ID:
                    natural_starts += 1
                if left == right:
                    continue
                proof = {} if proposal is None else proposal.get("exact_proof") or {}
                row = {
                    "corpus": corpus,
                    "replay": replay_path.name,
                    "seat": seat,
                    "step": step,
                    "turn": (obs.get("current") or {}).get("turn"),
                    "action_count": (obs.get("current") or {}).get("turnActionCount"),
                    "context": (obs.get("select") or {}).get("context"),
                    "rule5_action": left,
                    "rule8_action": right,
                    "rule5_attack_id": selected_attack(obs, left),
                    "rule8_attack_id": selected_attack(obs, right),
                    "attacker": active_ref(obs, seat),
                    "target": active_ref(obs, 1 - seat),
                    "classification": None if proposal is None else proposal.get("purpose"),
                    "exact_proof": proof,
                    "telemetry": telemetry,
                }
                row["allowed"] = bool(
                    proposal is not None
                    and proposal.get("rule_id") == candidate._RULE8_ID
                    and proposal.get("transaction") is None
                    and row["classification"] == "SAME_ACTIVE_EXACT_PARETO_ATTACK_DOMINANCE"
                    and row["rule5_attack_id"] == 223
                    and row["rule8_attack_id"] == 224
                    and tuple(proof.get("attacker") or ())[:2]
                    == tuple(row["attacker"] or ())[:2]
                    and tuple(proof.get("target") or ())[:2]
                    == tuple(row["target"] or ())[:2]
                    and bool((proof.get("outcomes") or {}).get("strict_dimensions"))
                )
                differences.append(row)
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

summary = {
    "source_path_count": len(sources),
    "current_path_count": sum(corpus == "current" for corpus, _path in sources),
    "historical_path_count": sum(corpus == "historical" for corpus, _path in sources),
    "ordered_corpus_sha256": manifest_hash,
    "readable_replays": len(sources) - len(malformed),
    "seats_per_replay": 2,
    "malformed_replays": malformed,
    "callbacks": callbacks,
    "natural_starts": natural_starts,
    "action_differences": len(differences),
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
