"""C4 action-identical wrapper over the adopted C2 FIX4B parent."""

from __future__ import annotations

import _c4_action_parent as _action_parent
import planner_wall_shadow_fix6 as _c4_shadow


# Compatibility aliases expose the exact adopted parent's test seams.  They
# reference the same module objects used by _c4_action_parent and do not create
# a second action path.
_parent = _action_parent._parent
_final_policy = _action_parent._final_policy
_deck_v1 = _action_parent._deck_v1


LAST_V0_PORT_TRACE: dict | None = None
LAST_V1_PACKAGE_TRACE: dict | None = None
LAST_C2_STAGED_POLICY_TRACE: dict | None = None
LAST_STAGED_POLICY_TRACE: dict | None = None


def _absolute_emergency_trace(action, error):
    """Last-resort trace independent of every planner callable."""
    rows = [
        {
            "kind": kind,
            "decision_point": None,
            "wall_class": "REJECTED",
            "certification": "UNAVAILABLE",
            "legality": "UNAVAILABLE",
            "option_index": None,
            "semantic_action_key": None,
            "wall": None,
            "rejection_codes": [],
            "unsupported_reasons": [],
            "structural_reasons": [],
            "metrics": {},
            "pareto_vector": None,
        }
        for kind in (
            "RUN_AWAY_ACCELERATION",
            "CERTIFIED_REUSABLE_WALL",
            "CERTIFIED_SACRIFICE_WALL",
            "NO_WALL_OR_UNKNOWN",
        )
    ]
    return {
        "schema_version": 6,
        "rule_version": "V4_WALL_SHADOW_FIX6",
        "parent_closure_sha256": (
            "29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157"
        ),
        "candidate_closure_sha256": None,
        "analyzer_component_sha256": (
            "AD14F84C80FC92B95ACB7C585D492910BD46883528CE2F99158AF046EDDAE201"
        ),
        "state_machine": [
            "CAPTURE",
            "EMIT_REJECTION",
            "RETURN_EXACT_PARENT_ACTION",
        ],
        "decision_point": None,
        "pair_id": None,
        "decision_id": None,
        "raw_parent_action": action,
        "parent_action": action,
        "proposed_action": action,
        "applied_action": action,
        "action_python_type": (
            f"{type(action).__module__}.{type(action).__qualname__}"
        ),
        "action_identity": {
            "value_equal": True,
            "type_equal": True,
            "order_equal": True,
            "returned_parent_object_unchanged": True,
        },
        "semantic_option_keys": None,
        "semantic_parent_action_keys": None,
        "semantic_proposed_action_keys": None,
        "public_state_material": None,
        "public_state_fingerprint": None,
        "pair_material": None,
        "game_boundary_fingerprint": None,
        "parent_post_fingerprint": None,
        "candidate_post_fingerprint": None,
        "expose_state_fingerprint": None,
        "wall_state_fingerprint": None,
        "expose_projection": None,
        "wall_projection": None,
        "protected_line": None,
        "importance": "UNKNOWN_IMPORTANCE",
        "distance_before": None,
        "distance_without_line": None,
        "threat": None,
        "damage_floor": None,
        "damage_cap": None,
        "continuity": "UNKNOWN",
        "wall_candidates": [],
        "candidate_rows": rows,
        "run_away_value": None,
        "reusable_wall_value": None,
        "sacrifice_wall_value": None,
        "bypass": "UNKNOWN",
        "refusal_progress": "UNKNOWN",
        "safe_release": None,
        "gust_exposure_turns": 0,
        "wall_class": "REJECTED",
        "arbitration_reason": "ABSOLUTE_EMERGENCY_REJECTION",
        "outcome_status": "COUNTERFACTUAL_UNOBSERVED",
        "outcome_events": [],
        "certified_draw_count": 0,
        "certified_draw_damage_delta": 0,
        "premium_power_pro_multiplicity": None,
        "evidenced_policy_cap": None,
        "safety_cap": None,
        "hold_entry_turn": None,
        "hold_deadline": None,
        "distance_progress_by_turn": [],
        "rejection_codes": ["METRIC_EXCEPTION"],
        "unsupported_reasons": [],
        "structural_reasons": [],
        "parser_source": (
            "_cumulative_parent._bridge_retaliation_attack_damage"
        ),
        "metric_exception": (
            error if isinstance(error, str) else type(error).__name__
        ),
        "c2_trace_rule_version": None,
    }


def agent(obs_dict: dict):
    """Return the exact C2 parent action object after read-only C4 analysis."""
    global LAST_V0_PORT_TRACE, LAST_V1_PACKAGE_TRACE
    global LAST_C2_STAGED_POLICY_TRACE, LAST_STAGED_POLICY_TRACE

    action = _action_parent.agent(obs_dict)
    LAST_V0_PORT_TRACE = _action_parent.LAST_V0_PORT_TRACE
    LAST_V1_PACKAGE_TRACE = _action_parent.LAST_V1_PACKAGE_TRACE
    LAST_C2_STAGED_POLICY_TRACE = _action_parent.LAST_STAGED_POLICY_TRACE
    try:
        LAST_STAGED_POLICY_TRACE = _c4_shadow.analyze(
            obs_dict,
            action,
            c2_trace=LAST_C2_STAGED_POLICY_TRACE,
        )
    except Exception as error:
        try:
            LAST_STAGED_POLICY_TRACE = _c4_shadow.rejection_trace(
                obs_dict,
                action,
                error,
                c2_trace=LAST_C2_STAGED_POLICY_TRACE,
            )
        except Exception:
            try:
                LAST_STAGED_POLICY_TRACE = _c4_shadow.emergency_trace(
                    action,
                    error,
                )
            except Exception as emergency_error:
                LAST_STAGED_POLICY_TRACE = _absolute_emergency_trace(
                    action,
                    emergency_error,
                )
    return action


def reset_shadow_state() -> None:
    _c4_shadow.reset()


__all__ = ["agent", "reset_shadow_state"]
