"""Current plus historical static replay shadow for Task 8."""
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
    "archaludon_public_complete_supporter_purpose_arbitration_t7_v1"
)
CANDIDATE = AUTO / "candidates" / (
    "archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1"
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
    if hasattr(module, "_t8_is_transaction") and module._t8_is_transaction():
        module._t8_abort([], "replay_shadow_reset")
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


parent = load(PARENT, "task8_shadow_parent")
candidate = load(CANDIDATE, "task8_shadow_candidate")
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
        safety_before = {
            "t8_invalid": candidate._t8_counters["invalid_fallbacks"],
            "t8_exceptions": candidate._t8_counters["exceptions"],
            "t7_invalid": candidate._t7_counters["invalid_fallbacks"],
            "t7_owner_collisions_candidate": candidate._t7_counters[
                "owner_collisions"
            ],
            "t7_owner_collisions_parent": parent._t7_counters[
                "owner_collisions"
            ],
            "pfgear_invalid": candidate._pfgear_counters["invalid_actions"],
            "pfgear_owner_collisions": candidate._pfgear_counters["owner_collisions"],
        }
        decisions = 0
        differences = []
        activations = []
        parent_control_differences = []
        for step, obs, recorded in replay_decisions(raw, seat):
            decisions += 1
            left = parent.agent(copy.deepcopy(obs))
            captured = {}
            exact_candidate_parent = candidate._t8_parent_agent

            def capture_candidate_parent(value):
                action = exact_candidate_parent(value)
                captured["action"] = copy.deepcopy(action)
                return action

            candidate._t8_parent_agent = capture_candidate_parent
            try:
                right = candidate.agent(copy.deepcopy(obs))
            finally:
                candidate._t8_parent_agent = exact_candidate_parent
            inner_parent = captured["action"]
            parsed = candidate.to_observation_class(obs)
            assert candidate._cum_valid_action(parsed, left)
            assert candidate._cum_valid_action(parsed, right)
            assert candidate._cum_valid_action(parsed, inner_parent)
            left_semantic = candidate._cum_action_semantic(parsed, left)
            right_semantic = candidate._cum_action_semantic(parsed, right)
            inner_parent_semantic = candidate._cum_action_semantic(
                parsed, inner_parent
            )
            direct = copy.deepcopy(candidate._t8_last_telemetry or {})
            task7_direct = copy.deepcopy(candidate._t7_last_telemetry or {})
            gear_transaction = copy.deepcopy(candidate._pfgear_transaction)
            certificate = None
            if isinstance(gear_transaction, dict):
                certificate = gear_transaction.get("certificate")
            if certificate is None and candidate._t7_transaction is not None:
                certificate = candidate._t7_transaction.get("certificate")
            if (
                certificate is None
                and direct.get("selected_source") == candidate._T8_RULE_ID
                and isinstance(candidate._t8_last_certificate, dict)
                and candidate._t8_last_certificate.get("rule")
                == candidate._T8_RULE_ID
            ):
                certificate = copy.deepcopy(candidate._t8_last_certificate)
            task8_owned = bool(
                direct.get("selected_source") == candidate._T8_RULE_ID
                or (
                    isinstance(certificate, dict)
                    and certificate.get("rule") == candidate._T8_RULE_ID
                )
            )
            direction = direct.get("direction")
            if direction is None and isinstance(certificate, dict):
                direction = certificate.get("direction")
            if task8_owned:
                activations.append({
                    "step": step,
                    "turn": obs["current"]["turn"],
                    "source_kind": None if certificate is None else certificate.get("source_kind"),
                    "purpose": None if certificate is None else certificate.get("purpose"),
                    "direction": direction,
                    "stage": (
                        None if certificate is None else certificate.get("stage")
                    ),
                })
            if left_semantic != right_semantic:
                if not task8_owned:
                    if (
                        task7_direct.get("selected_source")
                        == candidate._T7_RULE_ID
                    ):
                        row = {
                            "step": step,
                            "turn": obs["current"]["turn"],
                            "classification": "UNEXPECTED_TASK7_TERMINAL_DIFFERENCE",
                            "parent_semantic": candidate._cum_jsonable(left_semantic),
                            "candidate_parent_semantic": candidate._cum_jsonable(
                                inner_parent_semantic
                            ),
                        }
                        differences.append(row)
                        unexpected.append({
                            "corpus": corpus_name,
                            "episode": replay_path.stem,
                            **row,
                        })
                        break
                    if inner_parent_semantic == right_semantic:
                        parent_control_differences.append({
                            "step": step,
                            "turn": obs["current"]["turn"],
                            "status": "BASELINE_MODULE_DUPLICATE_CONTROL_DIFFERENCE",
                            "external_parent_semantic": candidate._cum_jsonable(
                                left_semantic
                            ),
                            "candidate_embedded_parent_semantic": candidate._cum_jsonable(
                                inner_parent_semantic
                            ),
                        })
                        continue
                classification = {
                    "PLAY_LILLIE": "T8_PLAY_LILLIE",
                    "MATERIALIZE_THEN_REEVALUATE": "T8_MATERIALIZE",
                    "HOLD_LILLIE": "T8_HOLD",
                    "GEAR_LILLIE": "T8_GEAR_LILLIE",
                }.get(direction, "UNEXPECTED_NON_T8_DIFFERENCE")
                parent_option = candidate._t8_parent_option(parsed, left)
                parent_card = (
                    None if parent_option is None
                    else candidate.option_card(parsed, parent_option)
                )
                parent_card_id = candidate._pcrd_get(parent_card, "id")
                row = {
                    "step": step,
                    "turn": obs["current"]["turn"],
                    "recorded": recorded,
                    "parent_action": left,
                    "parent_card_id": parent_card_id,
                    "candidate_action": right,
                    "parent_semantic": candidate._cum_jsonable(left_semantic),
                    "candidate_semantic": candidate._cum_jsonable(right_semantic),
                    "candidate_embedded_parent_semantic": candidate._cum_jsonable(
                        inner_parent_semantic
                    ),
                    "classification": classification,
                    "task8_source": direct.get("selected_source"),
                    "task8_reason": direct.get("rejection_reason"),
                    "direction": direction,
                    "first_difference_is_current_task8_activation": task8_owned,
                    "certificate_hash": (
                        None if certificate is None else certificate.get("certificate_hash")
                    ),
                    "purpose": None if certificate is None else certificate.get("purpose"),
                    "target_serial": None if certificate is None else certificate.get("target_serial"),
                    "attack_id": None if certificate is None else certificate.get("attack_id"),
                }
                differences.append(row)
                if classification.startswith("UNEXPECTED") or not task8_owned:
                    unexpected.append({
                        "corpus": corpus_name,
                        "episode": replay_path.stem,
                        **row,
                    })
                if (
                    direction == "GEAR_LILLIE"
                    and parent_card_id
                    in {candidate.BOSS, candidate.EXPLORER}
                ):
                    unexpected.append({
                        "corpus": corpus_name,
                        "episode": replay_path.stem,
                        **row,
                        "classification": (
                            "UNEXPECTED_GEAR_PARENT_SUPPORTER_DIFFERENCE"
                        ),
                    })
                # The recorded suffix belongs to the historical action, not
                # the counterfactual Task 8 action.  It is deliberately not
                # executed, classified, or counted as an additional delta.
                break
        safety_after = {
            "t8_invalid": candidate._t8_counters["invalid_fallbacks"],
            "t8_exceptions": candidate._t8_counters["exceptions"],
            "t7_invalid": candidate._t7_counters["invalid_fallbacks"],
            "t7_owner_collisions_candidate": candidate._t7_counters[
                "owner_collisions"
            ],
            "t7_owner_collisions_parent": parent._t7_counters[
                "owner_collisions"
            ],
            "pfgear_invalid": candidate._pfgear_counters["invalid_actions"],
            "pfgear_owner_collisions": candidate._pfgear_counters["owner_collisions"],
        }
        safety_delta = {
            key: safety_after[key] - safety_before[key]
            for key in safety_before
        }
        safety_delta["t7_owner_collision_excess"] = (
            safety_delta["t7_owner_collisions_candidate"]
            - safety_delta["t7_owner_collisions_parent"]
        )
        submission_safety = {
            key: value for key, value in safety_delta.items()
            if key not in {
                "t7_owner_collisions_candidate",
                "t7_owner_collisions_parent",
            }
        }
        if any(submission_safety.values()):
            unexpected.append({
                "corpus": corpus_name,
                "episode": replay_path.stem,
                "classification": "UNEXPECTED_PREFIX_SAFETY_DELTA",
                "safety_delta": safety_delta,
                "submission_safety_delta": submission_safety,
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
            "authoritative_prefix_only": bool(differences),
            "counterfactual_suffix": (
                {
                    "status": "COUNTERFACTUAL_SUFFIX_NOT_INTERPRETABLE",
                    "after_step": differences[0]["step"],
                }
                if differences else None
            ),
            "task8_activation_count": len(activations),
            "task8_activations": activations,
            "authoritative_prefix_safety_delta": safety_delta,
            "parent_duplicate_control_difference_count": len(
                parent_control_differences
            ),
            "parent_duplicate_control_differences": parent_control_differences,
        })

reset(candidate)
shadow_conservation = candidate._t8_conservation()
assert shadow_conservation["holds"], shadow_conservation
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
    "task8_activation_count": sum(
        row["task8_activation_count"] for row in episodes
    ),
    "activation_direction_counts": {
        direction: sum(
            activation.get("direction") == direction
            for row in episodes
            for activation in row["task8_activations"]
        )
        for direction in (
            "PLAY_LILLIE", "MATERIALIZE_THEN_REEVALUATE",
            "HOLD_LILLIE", "GEAR_LILLIE",
        )
    },
    "authoritative_direction_counts": {
        direction: sum(
            row["first_difference"] is not None
            and row["first_difference"].get("direction") == direction
            for row in episodes
        )
        for direction in (
            "PLAY_LILLIE", "MATERIALIZE_THEN_REEVALUATE",
            "HOLD_LILLIE", "GEAR_LILLIE",
        )
    },
    "counterfactual_suffix_not_interpretable_count": sum(
        row["counterfactual_suffix"] is not None for row in episodes
    ),
    "parent_duplicate_control_difference_count": sum(
        row["parent_duplicate_control_difference_count"] for row in episodes
    ),
    "task7_terminal_difference_count": sum(
        difference.get("classification") == "T7_EXACT_TERMINAL_BOSS"
        for row in episodes
        for difference in row["all_differences"]
    ),
    "gear_parent_supporter_difference_count": sum(
        difference.get("direction") == "GEAR_LILLIE"
        and difference.get("parent_card_id")
        in {candidate.BOSS, candidate.EXPLORER}
        for row in episodes
        for difference in row["all_differences"]
    ),
    "unexpected_first_differences": unexpected,
    "t8_conservation_after_settlement": shadow_conservation,
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
        "task8_activation_count",
        "activation_direction_counts",
        "authoritative_direction_counts",
        "counterfactual_suffix_not_interpretable_count",
        "parent_duplicate_control_difference_count",
        "task7_terminal_difference_count",
        "gear_parent_supporter_difference_count",
    )
}, sort_keys=True))
