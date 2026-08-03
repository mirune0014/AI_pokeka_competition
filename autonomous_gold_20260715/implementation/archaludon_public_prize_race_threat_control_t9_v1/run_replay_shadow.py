"""Current plus historical first-difference shadow for Task 9."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
AUTO = ROOT / "autonomous_gold_20260715"
PARENT = AUTO / "candidates/archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1"
CANDIDATE = AUTO / "candidates/archaludon_public_prize_race_threat_control_t9_v1"
CURRENT = AUTO / "live/55155015/analysis_20260802/refresh"
HISTORICAL = AUTO / "live/55070349/refresh_20260729_1241/shadow_corpus_196_prior_plus_11_new"
OUTPUT = Path(__file__).with_name("replay_shadow_results.json")
sys.path[:0] = [str(CANDIDATE), str(ROOT), str(ROOT / "infrastructure" / "tools")]

from ptcg_common import read_deck  # noqa: E402
from research.rl_ptcg.label_replay_rollout import replay_decisions, target_seat_for_deck  # noqa: E402


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path / "main.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def reset(module):
    if hasattr(module, "_t9_transaction"):
        module._t9_transaction = None
    if hasattr(module, "_t8_is_transaction") and module._t8_is_transaction():
        module._t8_abort([], "task9_shadow_reset")
    if hasattr(module, "_t7_transaction"):
        module._t7_transaction = None
    if hasattr(module, "_pfgear_reset_active"):
        module._pfgear_reset_active("task9_shadow_reset")
    if hasattr(module, "_pcrd_clear"):
        module._pcrd_clear("task9_shadow_reset")
    if hasattr(module, "_pfc_clear"):
        module._pfc_clear("task9_shadow_reset")
    if hasattr(module, "_cum_reset_runtime"):
        module._cum_reset_runtime("task9_shadow_reset")
    if hasattr(module, "_dper_reset_runtime"):
        module._dper_reset_runtime("task9_shadow_reset")


parent = load(PARENT, "task9_shadow_parent")
candidate = load(CANDIDATE, "task9_shadow_candidate")
deck = read_deck(CANDIDATE / "deck.csv")


def target_seat(replay):
    names = tuple(replay.get("info", {}).get("TeamNames", ()))
    named = tuple(seat for seat, name in enumerate(names) if name == "rurumi")
    return named[0] if named else target_seat_for_deck(replay, deck)


current_paths = tuple(sorted(CURRENT.glob("episode_*_replay.json")))
historical_all = tuple(sorted(HISTORICAL.glob("episode_*_replay.json")))
historical_paths = tuple(sorted(
    sorted(
        historical_all,
        key=lambda path: hashlib.sha256(path.name.encode("utf-8")).hexdigest(),
    )[:32]
))
corpora = (("current", current_paths), ("historical_sample", historical_paths))
snapshot = hashlib.sha256()
episodes = []
unreadable = []
first_differences = []
invalid = []
for corpus_name, replay_paths in corpora:
    for replay_path in replay_paths:
        data = replay_path.read_bytes()
        snapshot.update(corpus_name.encode())
        snapshot.update(replay_path.name.encode())
        snapshot.update(hashlib.sha256(data).digest())
        try:
            raw = json.loads(data)
        except json.JSONDecodeError as error:
            unreadable.append({"corpus": corpus_name, "path": str(replay_path), "error": str(error)})
            continue
        seat = target_seat(raw)
        reset(parent)
        reset(candidate)
        decisions = 0
        first = None
        for step, obs, recorded in replay_decisions(raw, seat):
            decisions += 1
            left = parent.agent(copy.deepcopy(obs))
            captured = {}
            embedded = candidate._t9_parent_agent

            def capture(value):
                action = embedded(value)
                captured["action"] = copy.deepcopy(action)
                return action

            candidate._t9_parent_agent = capture
            try:
                right = candidate.agent(copy.deepcopy(obs))
            finally:
                candidate._t9_parent_agent = embedded
            parsed = candidate.to_observation_class(copy.deepcopy(obs))
            inner = captured.get("action")
            for label, action in (("parent", left), ("embedded_parent", inner), ("candidate", right)):
                if not candidate._cum_valid_action(parsed, action):
                    invalid.append({"episode": replay_path.stem, "step": step, "label": label, "action": action})
            left_semantic = candidate._cum_action_semantic(parsed, left)
            right_semantic = candidate._cum_action_semantic(parsed, right)
            inner_semantic = candidate._cum_action_semantic(parsed, inner)
            if left_semantic != right_semantic:
                telemetry = copy.deepcopy(candidate._t9_last_telemetry or {})
                first = {
                    "corpus": corpus_name,
                    "episode": replay_path.stem,
                    "step": step,
                    "turn": obs["current"]["turn"],
                    "recorded": recorded,
                    "parent_action": left,
                    "candidate_action": right,
                    "parent_semantic": candidate._cum_jsonable(left_semantic),
                    "embedded_parent_semantic": candidate._cum_jsonable(inner_semantic),
                    "candidate_semantic": candidate._cum_jsonable(right_semantic),
                    "purpose": telemetry.get("purpose"),
                    "selected_source": telemetry.get("selected_source"),
                    "reason": telemetry.get("rejection_reason"),
                    "winner": telemetry.get("winner"),
                    "compared_plans": telemetry.get("compared_plans"),
                    "counters": telemetry.get("counters"),
                    "conservation": telemetry.get("conservation"),
                }
                first_differences.append(first)
                # Recorded suffix is counterfactual after the first change.
                break
        episodes.append({
            "corpus": corpus_name,
            "episode": replay_path.stem,
            "seat": seat,
            "decisions_until_boundary": decisions,
            "first_difference": first,
        })

result = {
    "parent_main_sha256": hashlib.sha256((PARENT / "main.py").read_bytes()).hexdigest().upper(),
    "candidate_main_sha256": hashlib.sha256((CANDIDATE / "main.py").read_bytes()).hexdigest().upper(),
    "corpus_snapshot_sha256": snapshot.hexdigest().upper(),
    "corpus_counts": {name: len(paths) for name, paths in corpora},
    "coverage_contract": {
        "current": "ALL_CURRENT_PATHS",
        "historical": "FIRST_32_BY_SHA256_OF_FILENAME",
        "historical_available": len(historical_all),
        "historical_selected_names": tuple(path.name for path in historical_paths),
    },
    "readable_episodes": len(episodes),
    "unreadable": unreadable,
    "first_difference_count": len(first_differences),
    "first_differences": first_differences,
    "invalid_actions": invalid,
    "episodes": episodes,
}
OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps({
    "readable": len(episodes),
    "unreadable": len(unreadable),
    "first_differences": len(first_differences),
    "invalid": len(invalid),
    "purposes": {
        purpose: sum(row.get("purpose") == purpose for row in first_differences)
        for purpose in candidate._T9_PURPOSES
    },
}, indent=2))
