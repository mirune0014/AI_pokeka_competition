from __future__ import annotations

import planner_bootstrap_final as _bootstrap
import planner_validation_final as _validation_final
import planner_raw_parity_v3 as _raw_parity
import planner_energy_aggregate_final as _energy_aggregate

import _cumulative_parent as _parent
import planner_integrated as _integrated
import planner_final_policy as _final_policy
import planner_option_resolution_final as _option_resolution
import planner_prize_option_final as _prize_option
import planner_ability_options_final as _ability_options
import planner_ability_options_v2 as _ability_options_v2
import planner_semantics_final as _semantics_final
import planner_outcome_failclosed_final as _outcome_failclosed
import planner_snapshot_serial_final as _snapshot_serial
import planner_placeholder_final as _placeholder
import planner_transaction_fixes as _transaction_fixes
import planner_duplicate_final as _duplicate_final
import planner_placeholder_gate_final as _placeholder_gate
import planner_deck_adaptation_v1 as _deck_v1
import planner_next_attacker_distance_shadow as _c2_shadow


V0_ADDED_CARD_IDS = frozenset(_parent.V0_GENERIC_HOLD)
LAST_V0_PORT_TRACE: dict | None = None
LAST_V1_PACKAGE_TRACE: dict | None = None
LAST_STAGED_POLICY_TRACE: dict | None = None


def _v0_int(value):
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _v0_raw_card_id(card):
    if not isinstance(card, dict):
        return None
    return _v0_int(card.get('id', card.get('cardId')))


def _v0_option_card_id(obs_dict, option):
    if not isinstance(option, dict):
        return None
    card_id = _v0_int(option.get('cardId'))
    if card_id is not None and card_id > 0:
        return card_id
    option_type = _v0_int(option.get('type'))
    area = _v0_int(option.get('area'))
    if (
        option_type != int(_parent.OptionType.PLAY)
        and area != int(_parent.AreaType.HAND)
    ):
        return None
    index = _v0_int(option.get('index'))
    current = obs_dict.get('current') if isinstance(obs_dict, dict) else None
    if index is None or index < 0 or not isinstance(current, dict):
        return None
    players = current.get('players')
    if not isinstance(players, list):
        return None
    current_player = _v0_int(current.get('yourIndex'))
    player_index = (
        current_player
        if option_type == int(_parent.OptionType.PLAY)
        else _v0_int(option.get('playerIndex'))
    )
    if player_index is None or not 0 <= player_index < len(players):
        player_index = current_player
    if player_index is None or not 0 <= player_index < len(players):
        return None
    player = players[player_index]
    hand = player.get('hand') if isinstance(player, dict) else None
    if not isinstance(hand, list) or not 0 <= index < len(hand):
        return None
    return _v0_raw_card_id(hand[index])


def _v0_port_trace(obs_dict, action):
    select = obs_dict.get('select') if isinstance(obs_dict, dict) else None
    select = select if isinstance(select, dict) else {}
    context = _v0_int(select.get('context'))
    options = select.get('option')
    options = options if isinstance(options, list) else []
    selected_action = list(action) if isinstance(action, (list, tuple)) else []
    hold_ids = set()
    if context == int(_parent.SelectContext.MAIN):
        for option in options:
            if (
                isinstance(option, dict)
                and _v0_int(option.get('type')) == int(_parent.OptionType.PLAY)
            ):
                card_id = _v0_option_card_id(obs_dict, option)
                if card_id in V0_ADDED_CARD_IDS:
                    hold_ids.add(card_id)
    forced_discard_ids = set()
    if context == int(_parent.SelectContext.DISCARD):
        for index in selected_action:
            if (
                isinstance(index, int)
                and not isinstance(index, bool)
                and 0 <= index < len(options)
            ):
                card_id = _v0_option_card_id(obs_dict, options[index])
                if card_id in V0_ADDED_CARD_IDS:
                    forced_discard_ids.add(card_id)
    reasons = []
    if hold_ids:
        reasons.append('V0_GENERIC_HOLD')
    if forced_discard_ids:
        reasons.append('V0_GENERIC_FORCED_DISCARD')
    return {
        'context': context,
        'selected_action': selected_action,
        'reason_tags': reasons,
        'main_play_hold_card_ids': sorted(hold_ids),
        'forced_discard_selected_card_ids': sorted(forced_discard_ids),
        'relevant_added_card_ids': sorted(hold_ids | forced_discard_ids),
    }


def agent(obs_dict: dict) -> list[int]:
    global LAST_V0_PORT_TRACE, LAST_V1_PACKAGE_TRACE
    global LAST_STAGED_POLICY_TRACE
    action = _deck_v1.agent(
        _parent,
        lambda raw: _final_policy.agent(_parent, _parent.agent, raw),
        obs_dict,
    )
    try:
        LAST_V0_PORT_TRACE = _v0_port_trace(obs_dict, action)
    except Exception as error:
        LAST_V0_PORT_TRACE = {
            'context': None,
            'selected_action': (
                list(action) if isinstance(action, (list, tuple)) else []
            ),
            'reason_tags': [],
            'main_play_hold_card_ids': [],
            'forced_discard_selected_card_ids': [],
            'relevant_added_card_ids': [],
            'trace_error': type(error).__name__,
        }
    LAST_V1_PACKAGE_TRACE = dict(_deck_v1.LAST_V1_PACKAGE_TRACE)
    parent_trace = {
        "LAST_V0_PORT_TRACE": LAST_V0_PORT_TRACE,
        "LAST_V1_PACKAGE_TRACE": LAST_V1_PACKAGE_TRACE,
    }
    integrated_transaction = getattr(
        _integrated.core, "INTEGRATED_TRANSACTION", None
    )
    v1_transaction = getattr(_deck_v1, "V1_TRANSACTION", None)
    transaction_state = {
        "integrated_transaction_active": (
            integrated_transaction is not None
        ),
        "integrated_transaction_kind": (
            integrated_transaction.get("kind")
            if isinstance(integrated_transaction, dict)
            else None
        ),
        "integrated_transaction_stage": (
            integrated_transaction.get("stage")
            if isinstance(integrated_transaction, dict)
            else None
        ),
        "v1_transaction_active": v1_transaction is not None,
        "v1_transaction_rule": (
            v1_transaction.get("rule")
            if isinstance(v1_transaction, dict)
            else None
        ),
        "v1_transaction_stage": (
            v1_transaction.get("stage")
            if isinstance(v1_transaction, dict)
            else None
        ),
    }
    try:
        LAST_STAGED_POLICY_TRACE = _c2_shadow.analyze(
            obs_dict,
            action,
            parent_trace=parent_trace,
            transaction_state=transaction_state,
        )
    except Exception as error:
        try:
            LAST_STAGED_POLICY_TRACE = (
                _c2_shadow.metric_exception_trace(
                    obs_dict,
                    action,
                    error,
                    parent_trace=parent_trace,
                    transaction_state=transaction_state,
                )
            )
        except Exception:
            LAST_STAGED_POLICY_TRACE = {
                "schema_version": 4,
                "rule_version": (
                    "V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4B"
                ),
                "parent_closure_sha256": (
                    "DC90205DE06AE3E2E41ADC661577096BB02EE5B42AB9F4366FC1A01154745B47"
                ),
                "candidate_closure_sha256": None,
                "raw_parent_action": action,
                "applied_action": action,
                "action_python_type": (
                    f"{type(action).__module__}."
                    f"{type(action).__qualname__}"
                ),
                "action_identity": {
                    "value_equal": True,
                    "type_equal": True,
                    "order_equal": True,
                    "returned_parent_object_unchanged": True,
                },
                "observation_fingerprint": None,
                "route_rows": [],
                "best_primary_route": None,
                "best_fallback_route": None,
                "line_importance_rows": [],
                "unsupported_reasons": ["METRIC_EXCEPTION"],
                "metric_exception": type(error).__name__,
                "parent_trace": parent_trace,
                "transaction_state": transaction_state,
                "parent_post_fingerprint": None,
                "candidate_post_fingerprint": None,
                "expose_state_fingerprint": None,
                "wall_state_fingerprint": None,
                "certified_draw_count": 0,
                "certified_draw_damage_delta": 0,
                "premium_power_pro_multiplicity": None,
                "evidenced_policy_cap": None,
                "safety_cap": None,
                "hold_entry_turn": None,
                "hold_deadline": None,
                "distance_progress_by_turn": [],
            }
    return action


