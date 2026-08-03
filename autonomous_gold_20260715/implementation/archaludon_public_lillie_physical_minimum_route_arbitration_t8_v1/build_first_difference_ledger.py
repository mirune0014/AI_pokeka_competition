"""Build the authoritative Task 8 first-difference certificate ledger."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
AUTO = ROOT / "autonomous_gold_20260715"
CANDIDATE = AUTO / "candidates" / (
    "archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1"
)
CURRENT = AUTO / "live/55155015/analysis_20260802/refresh"
HISTORICAL = AUTO / (
    "live/55070349/refresh_20260729_1241/"
    "shadow_corpus_196_prior_plus_11_new"
)
SHADOW = HERE / "replay_shadow_results.json"
OUTPUT = HERE / "first_difference_ledger.json"
sys.path[:0] = [str(CANDIDATE), str(ROOT), str(ROOT / "infrastructure" / "tools")]

from research.rl_ptcg.label_replay_rollout import replay_decisions  # noqa: E402


def load_candidate():
    spec = importlib.util.spec_from_file_location(
        "task8_first_difference_ledger_candidate", CANDIDATE / "main.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def reset(module):
    if module._t8_is_transaction():
        module._t8_abort([], "first_difference_ledger_reset")
    module._t7_transaction = None
    module._pfgear_reset_active("first_difference_ledger_reset")
    module._pcrd_clear("first_difference_ledger_reset")
    module._pfc_clear("first_difference_ledger_reset")
    module._cum_reset_runtime("first_difference_ledger_reset")
    module._dper_reset_runtime("first_difference_ledger_reset")


def route_summary(route):
    keys = (
        "reason",
        "card_id",
        "serial",
        "minimum_count",
        "required_ref",
        "available_copy_count",
        "destination_serial",
        "successor_serial",
        "target_serial",
        "materializable_now",
        "owner_handoff_required",
    )
    return {key: route.get(key) for key in keys if key in route}


shadow_bytes = SHADOW.read_bytes()
shadow = json.loads(shadow_bytes)
expected_rows = {
    (row["corpus"], row["episode"]): row
    for row in shadow["episodes"]
    if row["first_difference"] is not None
}
assert len(expected_rows) == shadow["difference_count"]

paths = {}
for corpus, directory in (("current", CURRENT), ("historical", HISTORICAL)):
    paths.update({
        (corpus, path.stem): path
        for path in directory.glob("episode_*_replay.json")
    })

candidate = load_candidate()
ledger = []
for key in sorted(expected_rows):
    expected_episode = expected_rows[key]
    expected = expected_episode["first_difference"]
    replay_path = paths[key]
    replay_bytes = replay_path.read_bytes()
    raw = json.loads(replay_bytes)
    reset(candidate)
    found = False
    for step, obs, _recorded in replay_decisions(
        raw, expected_episode["target_seat"]
    ):
        action = candidate.agent(copy.deepcopy(obs))
        if step != expected["step"]:
            continue
        found = True
        parsed = candidate.to_observation_class(obs)
        actual_semantic = candidate._cum_action_semantic(parsed, action)
        expected_semantic = candidate._cum_action_semantic(
            parsed, expected["candidate_action"]
        )
        assert actual_semantic == expected_semantic, (key, step, action, expected)
        telemetry = copy.deepcopy(candidate._t8_last_telemetry or {})
        certificate = None
        if candidate._t8_is_transaction():
            certificate = copy.deepcopy(
                candidate._pfgear_transaction.get("certificate")
            )
        if certificate is None:
            certificate = copy.deepcopy(candidate._t8_last_certificate)
        assert isinstance(certificate, dict), (key, step, telemetry)
        assert certificate.get("rule") == candidate._T8_RULE_ID
        direction = expected["direction"]
        assert certificate.get("direction") == direction
        transform = certificate.get("transform", {})
        physical = certificate.get("physical_routes", {})
        benefits = list(transform.get("benefits", ()))
        negatives = list(transform.get("negatives", ()))
        purpose = certificate.get("purpose")
        outer_wrapper_rejection = telemetry.get("rejection_reason")
        rollback_rejection = certificate.get("rollback_reason")
        supporter_rejections = list(
            certificate.get("per_supporter_rejection") or ()
        )
        stage = certificate.get("stage")
        if direction == "HOLD_LILLIE":
            assert stage == "HOLD_COMPLETE"
            settlement = {
                "status": "SETTLED_AT_FIRST_DIFFERENCE",
                "stage": stage,
                "completion_reason": certificate.get("completion_reason"),
                "transaction_live": False,
            }
        elif stage == "INHERITED_ROUTE_HANDOFF_COMPLETE":
            assert not candidate._t8_is_transaction()
            settlement = {
                "status": "SETTLED_AT_FIRST_DIFFERENCE",
                "stage": stage,
                "completion_reason": certificate.get("completion_reason"),
                "transaction_live": False,
            }
        else:
            assert candidate._t8_is_transaction()
            settlement = {
                "status": "COUNTERFACTUAL_SUFFIX_NOT_INTERPRETABLE",
                "stage": stage,
                "completion_reason": certificate.get("completion_reason"),
                "transaction_live": True,
            }
        if stage == "INHERITED_ROUTE_HANDOFF_COMPLETE":
            obvious_bad = not bool(physical.get("required_refs"))
        elif direction == "MATERIALIZE_THEN_REEVALUATE":
            obvious_bad = not any(
                route.get("materializable_now")
                and not route.get("owner_handoff_required")
                for route in physical.get("routes", ())
            )
        elif direction in {"PLAY_LILLIE", "GEAR_LILLIE"}:
            obvious_bad = bool(not benefits or negatives)
        else:
            obvious_bad = False
        no_purpose = purpose != candidate._T8_PURPOSE
        ledger.append({
            "corpus": key[0],
            "episode": key[1],
            "replay_sha256": hashlib.sha256(replay_bytes).hexdigest().upper(),
            "seat": expected_episode["target_seat"],
            "step": step,
            "turn": expected["turn"],
            "direction": direction,
            "classification": expected["classification"],
            "parent_action": expected["parent_action"],
            "candidate_action": expected["candidate_action"],
            "protected_routes": [
                route_summary(route)
                for route in physical.get("routes", ())
            ],
            "benefits": benefits,
            "negatives": negatives,
            "required_refs": list(physical.get("required_refs", ())),
            "minimum_counts": physical.get("minimum_counts", {}),
            "rejection": {
                "rollback": rollback_rejection,
                "per_supporter": supporter_rejections,
            },
            "outer_wrapper_rejection": outer_wrapper_rejection,
            "purpose": purpose,
            "certificate_hash": certificate.get("certificate_hash"),
            "settlement": settlement,
            "obvious_bad": obvious_bad,
            "no_purpose": no_purpose,
        })
        break
    assert found, key

directions = (
    "PLAY_LILLIE",
    "MATERIALIZE_THEN_REEVALUATE",
    "HOLD_LILLIE",
    "GEAR_LILLIE",
)
by_direction = {
    direction: [row for row in ledger if row["direction"] == direction]
    for direction in directions
}
direction_counts = {
    direction: len(rows) for direction, rows in by_direction.items()
}
assert direction_counts == shadow["authoritative_direction_counts"]
summary = {
    "ledger_count": len(ledger),
    "direction_counts": direction_counts,
    "obvious_bad_count": sum(row["obvious_bad"] for row in ledger),
    "no_purpose_count": sum(row["no_purpose"] for row in ledger),
    "rollback_rejection_count": sum(
        row["rejection"]["rollback"] is not None for row in ledger
    ),
    "supporter_rejection_episode_count": sum(
        bool(row["rejection"]["per_supporter"]) for row in ledger
    ),
    "outer_wrapper_rejection_count": sum(
        row["outer_wrapper_rejection"] is not None for row in ledger
    ),
    "settled_hold_count": sum(
        row["direction"] == "HOLD_LILLIE"
        and row["settlement"]["status"] == "SETTLED_AT_FIRST_DIFFERENCE"
        for row in ledger
    ),
    "settled_inherited_route_count": sum(
        row["settlement"]["stage"] == "INHERITED_ROUTE_HANDOFF_COMPLETE"
        for row in ledger
    ),
    "counterfactual_suffix_not_interpretable_count": sum(
        row["settlement"]["status"]
        == "COUNTERFACTUAL_SUFFIX_NOT_INTERPRETABLE"
        for row in ledger
    ),
    "shadow_results_sha256": hashlib.sha256(shadow_bytes).hexdigest().upper(),
}
assert summary["ledger_count"] == shadow["difference_count"]
assert summary["obvious_bad_count"] == 0
assert summary["no_purpose_count"] == 0
assert summary["rollback_rejection_count"] == 0

OUTPUT.write_text(
    json.dumps(
        {
            "summary": summary,
            "samples_by_direction": {
                direction: rows[:3]
                for direction, rows in by_direction.items()
            },
            "ledger_by_direction": by_direction,
        },
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
print(json.dumps(summary, sort_keys=True))
