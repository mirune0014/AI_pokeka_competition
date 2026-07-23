"""Exact lexicographic arbitration and pre-override structural gate."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import planner_integrated as integrated
import planner_model as model
import planner_policy as core
import planner_runtime_model as runtime_model
import planner_semantics as semantics
import planner_validation as validation
from planner_model import BaseRole, PlanObjective, PrizeLane


_INSTALLED = False
_BASE_BUILD_TURN_BUDGET = runtime_model.build_turn_budget
_BASE_ADVANCE_TRANSACTION = core._advance_transaction


def _build_turn_budget(parent: Any, obs: Any, ability_flags: dict[str, bool]):
    budget = _BASE_BUILD_TURN_BUDGET(parent, obs, ability_flags)
    effect_id = getattr(getattr(obs.select, "effect", None), "id", None)
    # Hilda's second child prompt explicitly reserves the future manual attach;
    # no attack/Ability opportunity is exposed at this child callback.
    if (
        obs.select.context == parent.SelectContext.TO_HAND
        and effect_id == parent.Hilda
        and not bool(obs.current.energyAttached)
    ):
        budget = replace(budget, manual_attachment=True)
    return budget


def _ordered_draw_clock(parent: Any, obs: Any):
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    theirs = obs.current.players[1 - owner]
    own = model.DeckClock(mine.deckCount)
    opponent = model.DeckClock(theirs.deckCount)
    helmet_forced = 0
    if mine.active and any(card.id == semantics.LUCKY_HELMET for card in mine.active[0].tools):
        if semantics.public_positive_attack_response(parent, obs):
            helmet_forced = 2
    events = (
        ("current_optional_draw_or_search", 0, True),
        ("opponent_turn_helmet_or_fan", helmet_forced, helmet_forced == 0),
        ("next_mandatory_draw", 1, False),
        ("H1_or_recovery", 0, True),
        ("next_opponent_turn", 0, False),
        ("H2_mandatory_draw", 1, False),
    )
    for name, count, optional in events:
        advanced = own.after(name, count, optional)
        if advanced is None:
            return model.DrawClock(model.DeckClock(-1, own.ordered_draws + ((name, count, optional),)), opponent)
        own = advanced
    return model.DrawClock(own, opponent)


def _normalize_tie(*values: Any) -> tuple[str, ...]:
    return tuple(repr(value) for value in values)


def _action_source(parent: Any, obs: Any, action: list[int]):
    if len(action) != 1 or not 0 <= action[0] < len(obs.select.option):
        return None, None
    option = obs.select.option[action[0]]
    return option, core._option_card(parent, obs, option)


def _parent_objective(parent: Any, obs: Any, action: list[int], roles: Any) -> PlanObjective:
    base = semantics.objective_for_state(parent, obs, roles, tie=())
    option, source = _action_source(parent, obs, action)
    abandoned = 0
    preserve_h0 = base.preserve_H0_lethal
    preserve_h1 = base.preserve_H1_attack
    preserve_h2 = base.preserve_H2_route
    if source is not None and source.id == semantics.TELEPATH_PSYCHIC and not semantics.has_psychic_telepath_target(parent, obs):
        abandoned += 1
    if option is not None and option.type == parent.OptionType.END and roles.H0 is None and roles.H1 is None:
        preserve_h2 = False
    lethal = core._h0_lethal_powerful_hand(parent, obs)
    if lethal is not None and option is not None and option.type != parent.OptionType.ATTACK:
        required = lethal[1]
        if not core._parent_step_retains_h0_and_successor(parent, obs, option, required):
            preserve_h0 = False
    keys = tuple(
        runtime_model.stable_option_key(parent, obs, obs.select.option[index])
        for index in action
    ) if model.action_is_valid(obs, action) else ()
    return replace(
        base,
        preserve_H0_lethal=preserve_h0,
        preserve_H1_attack=preserve_h1,
        preserve_H2_route=preserve_h2,
        fewer_abandoned_reservations=-abandoned,
        stable_semantic_tie_break=_normalize_tie("parent_fallback", keys),
    )


def _candidate_objective(parent: Any, obs: Any, plan: Any, roles: Any) -> PlanObjective:
    kind = dict(plan.metadata).get("kind", "")
    base = semantics.objective_for_state(parent, obs, roles, tie=())
    win_now = base.win_now
    avoid_loss = base.avoid_public_forced_loss
    preserve_h0 = base.preserve_H0_lethal
    preserve_h1 = base.preserve_H1_attack
    preserve_h2 = base.preserve_H2_route
    prizes_now = base.prizes_now
    deck = obs.current.players[obs.current.yourIndex].deckCount
    if kind == "TERMINAL_PSYCHIC_ATTACH_V5":
        win_now = True
        preserve_h0 = True
        prizes_now = len(obs.current.players[obs.current.yourIndex].prize)
    elif kind == "POWERFUL_HAND_FLOOR":
        preserve_h0 = True
    elif kind == "HILDA_ENRICHING_SETUP":
        preserve_h2 = True
        deck -= 5
    elif kind == "RUN_AWAY_SETUP_CLOCK":
        preserve_h2 = True
        deck -= min(3, deck)
    elif kind == "HANDHELD_FAN_RESPONSE":
        preserve_h2 = True
        avoid_loss = True
    elif kind == "INTEGRATED_SETUP_STOP_ATTACK":
        preserve_h0 = True
    lane_attacks = plan.prize_lane.attacks if plan.prize_lane.certified else 999
    return replace(
        base,
        win_now=win_now,
        avoid_public_forced_loss=avoid_loss,
        preserve_H0_lethal=preserve_h0,
        prizes_now=prizes_now,
        preserve_H1_attack=preserve_h1,
        preserve_H2_route=preserve_h2,
        shorter_certified_prize_lane=-lane_attacks,
        # All surviving plan reservations are named and consumed; required
        # reservations are not "abandoned" and receive no penalty.
        fewer_abandoned_reservations=0,
        safer_deck_clock=max(0, deck),
        stable_semantic_tie_break=_normalize_tie("integrated", kind, plan.plan_id),
    )


def _add_missing_role_for_reservations(parent: Any, obs: Any, plan: Any):
    ledger = plan.resource_ledger
    assigned = set(role for _, role in ledger.roles)
    missing = {reservation.role for reservation in ledger.reservations} - assigned
    if not missing:
        return plan
    owner = obs.current.yourIndex
    public = list(obs.current.players[owner].active) + list(obs.current.players[owner].bench)
    for role in sorted(missing, key=lambda row: row.value):
        free = None
        occupied = dict(ledger.roles)
        for pokemon in public:
            line = model.lineage_key(pokemon, owner)
            if line is not None and line not in occupied:
                free = line
                break
        if free is None:
            return None
        ledger = ledger.assign_role(free, role)
        if ledger is None:
            return None
    return replace(plan, resource_ledger=ledger)


def _restore_lost_named_reservation(parent: Any, obs: Any, plan: Any):
    metadata = dict(plan.metadata)
    kind = metadata.get("kind")
    ledger = plan.resource_ledger
    if kind == "HANDHELD_FAN_RESPONSE":
        token = f"tool:{metadata.get('fan_serial')}"
        if not any(row.token == token for row in ledger.reservations):
            role_map = dict(ledger.roles)
            line = model.lineage_key(obs.current.players[obs.current.yourIndex].active[0], obs.current.yourIndex)
            role = role_map.get(line)
            if role is None:
                return None
            ledger = ledger.reserve(token, role, "Handheld Fan public response")
            if ledger is None:
                return None
    return replace(plan, resource_ledger=ledger)


def _certify_candidate(parent: Any, obs: Any, candidate: Any):
    plan, action, commit = candidate
    certificate = integrated._domain_certificate(parent, obs, list(plan.fallback), candidate)
    if not certificate["eligible"]:
        return None
    integrated._replace_plan_evidence.parent = parent
    integrated._replace_plan_evidence.obs = obs
    plan = integrated._replace_plan_evidence(plan, certificate)
    plan = _restore_lost_named_reservation(parent, obs, plan)
    plan = _add_missing_role_for_reservations(parent, obs, plan) if plan is not None else None
    if plan is None:
        return None
    roles = certificate["roles"]
    plan = replace(plan, objective=_candidate_objective(parent, obs, plan, roles))
    ok, _ = validation.validate_plan(parent, obs, plan, action, current_stage=plan.expected_stage)
    if not ok:
        return None
    if commit and commit.get("transaction"):
        commit["transaction"]["plan"] = plan
    return plan, action, commit


def _setup_stop_candidate(parent: Any, obs: Any, snap: Any, parent_action: list[int], roles: Any):
    attack = integrated._one_attack(parent, obs, roles)
    option, source = _action_source(parent, obs, parent_action)
    if attack is None or option is None or option.type == parent.OptionType.ATTACK:
        return None
    if option.type not in (parent.OptionType.PLAY, parent.OptionType.ABILITY, parent.OptionType.END):
        return None
    protected = {
        semantics.BOSS_ORDERS,
        semantics.ENHANCED_HAMMER,
        semantics.NIGHT_STRETCHER,
        semantics.SACRED_ASH,
        semantics.BATTLE_CAGE,
    }
    if source is not None and source.id in protected:
        return None
    plan = core._make_plan(
        parent,
        obs,
        snap.sha256,
        parent_action,
        "INTEGRATED_SETUP_STOP_ATTACK",
        attack,
        stage="single_attack",
        H0=roles.H0.line if roles.H0 else None,
        H1=roles.H1.line if roles.H1 else None,
        H2=roles.H2.line if roles.H2 else None,
        ledger=roles.ledger,
        aborts=("H0 no longer ready", "optional step gains certified continuity"),
        metadata={"dependency_order": integrated.DEPENDENCY_ORDER},
    )
    return plan, attack, None


def _arbitrate_new_plan(parent: Any, obs: Any, snap: Any, parent_action: list[int], parent_pre: dict[str, Any], parent_post: dict[str, Any]):
    raw_candidates = []
    hilda = core._build_hilda_enriching(parent, obs, snap, parent_action, parent_pre)
    if hilda is not None:
        raw_candidates.append(hilda)
    owners = core.parent_owner_active(parent_pre) or core.parent_owner_active(parent_post)
    if not owners:
        for builder in (
            core._build_powerful_hand_floor,
            core._build_run_away,
            core._terminal_attach_candidate,
            core._build_fan_attach,
        ):
            result = builder(parent, obs, snap, parent_action)
            if result is not None:
                raw_candidates.append(result)
        roles = semantics.public_roles(parent, obs)
        stopped = _setup_stop_candidate(parent, obs, snap, parent_action, roles)
        if stopped is not None:
            raw_candidates.append(stopped)
    certified = []
    for candidate in raw_candidates:
        result = _certify_candidate(parent, obs, candidate)
        if result is not None:
            certified.append(result)
    roles = semantics.public_roles(parent, obs)
    parent_objective = _parent_objective(parent, obs, parent_action, roles)
    if not certified:
        return None
    winner = max(certified, key=lambda row: row[0].objective.vector())
    if winner[0].objective.vector() <= parent_objective.vector():
        return None
    return winner


def _advance_transaction(parent: Any, obs: Any):
    transaction = core.INTEGRATED_TRANSACTION
    result = _BASE_ADVANCE_TRANSACTION(parent, obs)
    outcome, action, reason = result
    if outcome != "override" or action is None or transaction is None:
        return result
    stage = transaction.get("stage", "unknown")
    plan = validation.advance_plan_step(parent, obs, transaction["plan"], action, stage)
    if plan is None:
        return "abort", None, "continuation action could not be rebound"
    ok, why = validation.validate_plan(parent, obs, plan, action, current_stage=stage)
    if not ok:
        return "abort", None, f"continuation plan invalid: {why}"
    transaction["plan"] = plan
    return outcome, action, reason


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    core.build_turn_budget = _build_turn_budget
    core.ordered_draw_clock = _ordered_draw_clock
    semantics.ordered_draw_clock = _ordered_draw_clock
    core._new_plan = _arbitrate_new_plan
    core._advance_transaction = _advance_transaction
    _INSTALLED = True


def agent(parent: Any, parent_agent: Any, obs_dict: dict) -> list[int]:
    install()
    if not isinstance(obs_dict, dict) or obs_dict.get("select") is None:
        core.reset_integrated_state()
        return parent_agent(obs_dict)
    try:
        obs = parent.to_observation_class(obs_dict)
    except Exception:
        return parent_agent(obs_dict)
    if not runtime_model.raw_parsed_agree(obs_dict, obs):
        core.reset_integrated_state()
        return parent_agent(obs_dict)
    return integrated.agent(parent, parent_agent, obs_dict)


install()
