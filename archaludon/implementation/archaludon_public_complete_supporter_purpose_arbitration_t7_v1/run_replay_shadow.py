"""Current plus historical static replay shadow for Task 7."""
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
PARENT = AUTO / "candidates" / (
    "archaludon_public_ultra_ball_declared_complete_route_transaction_v1"
)
CANDIDATE = AUTO / "candidates" / (
    "archaludon_public_complete_supporter_purpose_arbitration_t7_v1"
)
CURRENT = AUTO / "live/55155015/analysis_20260802/refresh"
HISTORICAL = AUTO / (
    "live/55070349/refresh_20260729_1241/"
    "shadow_corpus_196_prior_plus_11_new"
)
sys.path[:0] = [str(CANDIDATE), str(ROOT), str(ROOT / "infrastructure" / "tools")]

from ptcg_common import read_deck  # noqa: E402
from research.rl_ptcg.label_replay_rollout import (  # noqa: E402
    replay_decisions,
    target_seat_for_deck,
)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path / "main.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def reset(module):
    if hasattr(module, "_t7_transaction"):
        module._t7_transaction = None
    if hasattr(module, "_pfgear_reset_active"):
        module._pfgear_reset_active("replay_shadow_reset")
    if hasattr(module, "_pcrd_clear"):
        module._pcrd_clear("replay_shadow_reset")
    if hasattr(module, "_pfc_clear"):
        module._pfc_clear("replay_shadow_reset")
    if hasattr(module, "_cum_reset_runtime"):
        module._cum_reset_runtime("replay_shadow_reset")
    if hasattr(module, "_dper_reset_runtime"):
        module._dper_reset_runtime("replay_shadow_reset")


parent = load(PARENT, "task7_shadow_parent")
candidate = load(CANDIDATE, "task7_shadow_candidate")
deck = read_deck(CANDIDATE / "deck.csv")


def target_seat(replay):
    names = tuple(replay.get("info", {}).get("TeamNames", ()))
    named = tuple(
        seat for seat, name in enumerate(names) if name == "rurumi"
    )
    if named:
        # A self-play replay can expose the target team on both seats.  The
        # first seat is deterministic; both seat mechanics are covered by the
        # focused fixtures and extracted smoke.
        return named[0]
    return target_seat_for_deck(replay, deck)


corpora = (
    ("current", tuple(sorted(CURRENT.glob("episode_*_replay.json")))),
    ("historical", tuple(sorted(HISTORICAL.glob("episode_*_replay.json")))),
)
assert len(corpora[0][1]) == 46
assert len(corpora[1][1]) == 207

episodes = []
unexpected = []
unreadable = []
snapshot = hashlib.sha256()
for corpus_name, replay_paths in corpora:
    for replay_path in replay_paths:
        replay_bytes = replay_path.read_bytes()
        snapshot.update(corpus_name.encode("utf-8"))
        snapshot.update(replay_path.name.encode("utf-8"))
        snapshot.update(hashlib.sha256(replay_bytes).digest())
        try:
            raw = json.loads(replay_bytes)
        except json.JSONDecodeError as error:
            unreadable.append({
                "corpus": corpus_name,
                "episode": replay_path.stem,
                "replay_sha256": hashlib.sha256(replay_bytes).hexdigest().upper(),
                "byte_count": len(replay_bytes),
                "error": str(error),
            })
            continue
        seat = target_seat(raw)
        reset(parent)
        reset(candidate)
        decisions = 0
        differences = []
        activations = []
        for step, obs, recorded in replay_decisions(raw, seat):
            decisions += 1
            left = parent.agent(copy.deepcopy(obs))
            right = candidate.agent(copy.deepcopy(obs))
            parsed = candidate.to_observation_class(obs)
            assert candidate._cum_valid_action(parsed, left)
            assert candidate._cum_valid_action(parsed, right)
            left_semantic = candidate._cum_action_semantic(parsed, left)
            right_semantic = candidate._cum_action_semantic(parsed, right)
            direct = copy.deepcopy(candidate._t7_last_telemetry or {})
            gear_transaction = copy.deepcopy(candidate._pfgear_transaction)
            certificate = None
            if isinstance(gear_transaction, dict):
                certificate = gear_transaction.get("certificate")
            if certificate is None and candidate._t7_transaction is not None:
                certificate = candidate._t7_transaction.get("certificate")
            task7_owned = bool(
                direct.get("selected_source") == candidate._T7_RULE_ID
                or (
                    isinstance(certificate, dict)
                    and certificate.get("rule") == candidate._T7_RULE_ID
                )
            )
            if task7_owned:
                activations.append({
                    "step": step,
                    "turn": obs["current"]["turn"],
                    "source_kind": None if certificate is None else certificate.get("source_kind"),
                    "purpose": None if certificate is None else certificate.get("purpose"),
                    "stage": (
                        None if certificate is None else certificate.get("stage")
                    ),
                })
            if left_semantic != right_semantic:
                classification = (
                    "T7_EXACT_TERMINAL_BOSS"
                    if task7_owned
                    else "UNEXPECTED_NON_T7_DIFFERENCE"
                )
                row = {
                    "step": step,
                    "turn": obs["current"]["turn"],
                    "recorded": recorded,
                    "parent_action": left,
                    "candidate_action": right,
                    "parent_semantic": candidate._cum_jsonable(left_semantic),
                    "candidate_semantic": candidate._cum_jsonable(right_semantic),
                    "classification": classification,
                    "task7_source": direct.get("selected_source"),
                    "task7_reason": direct.get("rejection_reason"),
                    "certificate_hash": (
                        None if certificate is None else certificate.get("certificate_hash")
                    ),
                    "purpose": None if certificate is None else certificate.get("purpose"),
                    "target_serial": None if certificate is None else certificate.get("target_serial"),
                    "attack_id": None if certificate is None else certificate.get("attack_id"),
                }
                differences.append(row)
                if classification.startswith("UNEXPECTED"):
                    unexpected.append({
                        "corpus": corpus_name,
                        "episode": replay_path.stem,
                        **row,
                    })
        episodes.append({
            "corpus": corpus_name,
            "episode": replay_path.stem,
            "replay_sha256": hashlib.sha256(replay_bytes).hexdigest().upper(),
            "target_seat": seat,
            "decision_count": decisions,
            "difference_count": len(differences),
            "first_difference": differences[0] if differences else None,
            "all_differences": differences,
            "task7_activation_count": len(activations),
            "task7_activations": activations,
        })

assert not unexpected, unexpected[:3]
payload = {
    "snapshot_sha256": snapshot.hexdigest().upper(),
    "corpus_episode_counts": {
        name: len(paths) for name, paths in corpora
    },
    "episode_count": len(episodes),
    "decision_count": sum(row["decision_count"] for row in episodes),
    "difference_count": sum(row["difference_count"] for row in episodes),
    "episodes_with_differences": sum(
        bool(row["difference_count"]) for row in episodes
    ),
    "task7_activation_count": sum(
        row["task7_activation_count"] for row in episodes
    ),
    "unexpected_first_differences": unexpected,
    "unreadable_replays": unreadable,
    "episodes": episodes,
}
Path(__file__).with_name("replay_shadow_results.json").write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps({
    key: payload[key]
    for key in (
        "corpus_episode_counts",
        "episode_count",
        "decision_count",
        "difference_count",
        "episodes_with_differences",
        "task7_activation_count",
    )
}, sort_keys=True))
