"""Final reconciliation layer for the integrated-domain planner.

The core policy owns callback transactions.  This module installs the two
semantic corrections discovered during independent audit, certifies every
candidate plan against the remaining domain principles, and enriches every
override trace with the evidence needed to reproduce the arbitration.
"""

from __future__ import annotations

from dataclasses import replace
from math import ceil
from typing import Any

import planner_policy as core
import planner_semantics as semantics
from planner_model import (
    BaseRole,
    IntegratedTurnPlan,
    Outcome,
    OutcomeKind,
    PrizeLane,
    PrizeLaneStep,
    action_is_valid,
    build_turn_budget,
    lineage_key,
    stable_option_key,
)


DEPENDENCY_ORDER = (
    "terminal_or_forced_loss",
    "exact_prerequisites",
    "necessary_search_or_recovery",
    "role_assignment_attach_evolve",
    "strictly_improving_optional_information_or_draw",
    "attack",
)

_ORIGINAL_OUTCOME_FOR_ATTACK = semantics.outcome_for_attack
_ORIGINAL_NEW_PLAN = core._new_plan
_PATCHED = False


def outcome_components(outcome: Outcome) -> tuple[OutcomeKind, ...]:
    """Return all typed components while retaining one primary outcome kind."""
    rows = dict(outcome.details).get("components")
    if rows is None:
        return (outcome.kind,)
    parsed = []
    for row in rows:
        try:
            parsed.append(OutcomeKind(row))
        except (TypeError, ValueError):
            return (OutcomeKind.UNKNOWN,)
    return tuple(parsed) if parsed else (outcome.kind,)


def _corrected_outcome_for_attack(
    parent: Any,
    attacker: Any,
    attack: Any,
    target: Any,
    *,
    hand_count: int,
) -> Outcome:
    """Represent damage-plus-switch attacks as an explicit composite.

    Attack damage remains the primary kind so weakness, resistance, damage
    prevention, Lucky Helmet and Handheld Fan see only the damage component.
    The SelfSwitch component is separately typed for atomic post-attack
    promotion planning.
    """
    outcome = _ORIGINAL_OUTCOME_FOR_ATTACK(
        parent, attacker, attack, target, hand_count=hand_count
    )
    text = semantics._normalized(getattr(attack, "text", ""))
    if outcome.kind is OutcomeKind.ATTACK_DAMAGE and "switch this pokemon" in text:
        details = tuple(row for row in outcome.details if row[0] != "components")
        return replace(
            outcome,
            details=details
            + (("components", (OutcomeKind.ATTACK_DAMAGE.value, OutcomeKind.SELF_SWITCH.value)),),
        )
    return outcome


def _target_outcome(parent: Any, obs: Any, attacker: Any, target: Any, attack_id: int):
    data = parent.card_table.get(getattr(attacker, "id", None))
    attack = parent.attack_table.get(attack_id)
    if data is None or attack is None:
        return None
    raw = _corrected_outcome_for_attack(
        parent,
        attacker,
        attack,
        target,
        hand_count=obs.current.players[obs.current.yourIndex].handCount,
    )
    return semantics.resolve_public_outcome(
        parent,
        obs.current,
        attacker,
        target,
        raw,
        target_is_bench=target in obs.current.players[1 - obs.current.yourIndex].bench,
    )


def _hits_to_ko(outcome: Outcome, hp: int) -> int | None:
    if outcome.prevented:
        return None
    if outcome.kind is OutcomeKind.DIRECT_KO:
        return 1
    if outcome.kind in (OutcomeKind.ATTACK_DAMAGE, OutcomeKind.PLACE_COUNTERS) and outcome.amount > 0:
        return ceil(max(1, hp) / outcome.amount)
    return None


def _corrected_prize_lanes(parent: Any, obs: Any, roles: Any) -> tuple[PrizeLane, ...]:
    """Certify only target-specific access with exact single-use resources.

    The current Active is public access.  A current-turn Bench target is
    certified only when exactly one physical Boss is visible, the supporter
    budget is unspent, and its outcome is recomputed for that target.  No
    second Boss or unknown post-KO promotion is inferred.  Such future lanes
    remain deliberately uncertified until the next public callback.
    """
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    theirs = obs.current.players[1 - owner]
    if roles.H0 is None or len(mine.active) != 1 or len(theirs.active) != 1:
        return ()
    attacker = mine.active[0]
    lanes = []
    active = theirs.active[0]
    active_outcome = _target_outcome(parent, obs, attacker, active, roles.H0.attack_id)
    active_prizes = semantics.prize_value(parent, active)
    active_hits = _hits_to_ko(active_outcome, active.hp) if active_outcome is not None else None
    active_line = lineage_key(active, 1 - owner)
    if active_prizes is not None and active_hits is not None and active_line is not None:
        lanes.append(
            PrizeLane(
                (
                    PrizeLaneStep(
                        active_line,
                        active.serial,
                        active_prizes,
                        BaseRole.H0,
                        active_outcome,
                        active_hits,
                        mine.handCount,
                        False,
                        False,
                        (roles.H1 is not None, roles.H2 is not None),
                        ("current_active_access",),
                        None,
                    ),
                ),
                True,
            )
        )
    bosses = [card for card in (mine.hand or []) if card.id == semantics.BOSS_ORDERS]
    supporter_budget = build_turn_budget(
        parent,
        obs,
        {
            "dudunsparce": bool(parent.ability_used_dudunsparce),
            "fezandipiti": bool(parent.ability_used_fezandipiti),
        },
    ).supporter
    if len(bosses) != 1 or not supporter_budget:
        return tuple(lanes)
    for target in theirs.bench:
        target_line = lineage_key(target, 1 - owner)
        target_prizes = semantics.prize_value(parent, target)
        outcome = _target_outcome(parent, obs, attacker, target, roles.H0.attack_id)
        hits = _hits_to_ko(outcome, target.hp) if outcome is not None else None
        if target_line is None or target_prizes is None or hits is None:
            continue
        lanes.append(
            PrizeLane(
                (
                    PrizeLaneStep(
                        target_line,
                        target.serial,
                        target_prizes,
                        BaseRole.H0,
                        outcome,
                        hits,
                        mine.handCount - 1,
                        True,
                        True,
                        (roles.H1 is not None, roles.H2 is not None),
                        ("exact_boss_serial", bosses[0].serial),
                        None,
                    ),
                ),
                True,
            )
        )
    return tuple(lanes)


def _option_source(parent: Any, obs: Any, action: list[int]):
    if len(action) != 1 or not 0 <= action[0] < len(obs.select.option):
        return None, None
    option = obs.select.option[action[0]]
    return option, core._option_card(parent, obs, option)


def _one_attack(parent: Any, obs: Any, roles: Any):
    if roles.H0 is None:
        return None
    matches = [
        index
        for index, option in enumerate(obs.select.option)
        if option.type == parent.OptionType.ATTACK and option.attackId == roles.H0.attack_id
    ]
    return [matches[0]] if len(matches) == 1 else None


def _boss_gate(parent: Any, obs: Any, option: Any, source: Any, roles: Any, lanes: tuple[PrizeLane, ...]):
    if source is None or source.id != semantics.BOSS_ORDERS:
        return True, "not_boss"
    certified_boss = [lane for lane in lanes if lane.certified and lane.steps and lane.steps[0].boss_required]
    if len(certified_boss) != 1:
        return False, "Boss target/continuation is not uniquely certified"
    active_lane = next((lane for lane in lanes if lane.steps and not lane.steps[0].boss_required), None)
    boss_lane = certified_boss[0]
    active_step = active_lane.steps[0] if active_lane else None
    boss_step = boss_lane.steps[0]
    immediate_win = boss_step.prizes >= len(obs.current.players[obs.current.yourIndex].prize)
    active_lethal = bool(active_step and active_step.hits == 1)
    eligible = semantics.boss_is_eligible(
        immediate_win=immediate_win,
        active_lethal=active_lethal,
        active_prizes=active_step.prizes if active_step else 0,
        target_prizes=boss_step.prizes,
        strictly_fewer_attacks=bool(active_step and boss_step.hits < active_step.hits),
        exact_damaged_recovery=False,
        sole_public_engine_denial=False,
        certifies_continuity=roles.H1 is not None,
    )
    return eligible, "certified Boss gate" if eligible else "Boss eligibility predicate failed"


def _bench_gate(parent: Any, obs: Any, option: Any, source: Any, roles: Any):
    if option is None or source is None or option.type != parent.OptionType.PLAY:
        return True, "not_bench_play", None
    data = parent.card_table.get(source.id)
    if data is None or data.cardType != parent.CardType.POKEMON:
        return True, "not_bench_play", None
    # Exact named contribution.  A Pokemon that cannot satisfy one of these
    # roles is an optional liability, never a planner override.
    named = {
        getattr(parent, "Abra", -1): BaseRole.H1,
        getattr(parent, "Dunsparce", -1): BaseRole.ENGINE,
        semantics.SHAYMIN: BaseRole.ENGINE,
        getattr(parent, "Psyduck", -1): BaseRole.PIVOT,
        semantics.GENESECT: BaseRole.ENGINE,
        semantics.FEZANDIPITI_EX: BaseRole.ENGINE,
    }.get(source.id)
    if named is None:
        return False, "Bench body has no named H1/H2/engine/pivot route", None
    proxy = type("BenchProxy", (), {
        "id": source.id,
        "serial": source.serial,
        "energyCards": [],
        "tools": [],
    })()
    liability = semantics.bench_liability(parent, obs, proxy, named)
    if source.id == semantics.FEZANDIPITI_EX and not (
        roles.H0 is None or roles.H1 is None or semantics.recovery_restores_named_route(parent, obs, semantics.NIGHT_STRETCHER)
    ):
        return False, "Fezandipiti two-Prize shortcut is not needed for a named route", liability
    return True, "named Bench role", liability


def _domain_certificate(
    parent: Any,
    obs: Any,
    parent_action: list[int],
    candidate: tuple[IntegratedTurnPlan, list[int], Any] | None,
):
    roles = semantics.public_roles(parent, obs)
    lanes = _corrected_prize_lanes(parent, obs, roles)
    option, source = _option_source(parent, obs, candidate[1] if candidate else parent_action)
    boss_ok, boss_reason = _boss_gate(parent, obs, option, source, roles, lanes)
    bench_ok, bench_reason, liability = _bench_gate(parent, obs, option, source, roles)
    recovery = True
    if source is not None and source.id in (semantics.NIGHT_STRETCHER, semantics.SACRED_ASH):
        recovery = semantics.recovery_restores_named_route(parent, obs, source.id)
    hammer = semantics.enhanced_hammer_changes_response(parent, obs)
    # An Enhanced Hammer is actionable only through a complete, exact child
    # selection. v1 has no such transaction; record the response and fail
    # closed instead of initiating an incomplete item prompt.
    hammer_complete = not hammer or (source is not None and source.id != semantics.ENHANCED_HAMMER)
    return {
        "roles": roles,
        "lanes": lanes,
        "boss_ok": boss_ok,
        "boss_reason": boss_reason,
        "bench_ok": bench_ok,
        "bench_reason": bench_reason,
        "bench_liability": liability,
        "recovery_named": recovery,
        "hammer_changes_response": hammer,
        "hammer_transaction_complete": hammer_complete,
        "dependency_order": DEPENDENCY_ORDER,
        "eligible": boss_ok and bench_ok and recovery and hammer_complete,
    }


def _replace_plan_evidence(plan: IntegratedTurnPlan, certificate: dict[str, Any]) -> IntegratedTurnPlan:
    roles = certificate["roles"]
    lanes = [lane for lane in certificate["lanes"] if lane.certified]
    lane = min(lanes, key=lambda row: (row.attacks, repr(row.steps))) if lanes else PrizeLane()
    metadata = dict(plan.metadata)
    metadata.update(
        domain_boss=certificate["boss_reason"],
        domain_bench=certificate["bench_reason"],
        domain_recovery=certificate["recovery_named"],
        domain_hammer=(certificate["hammer_changes_response"], certificate["hammer_transaction_complete"]),
        dependency_order=DEPENDENCY_ORDER,
        future_prize_access="fail_closed_after_current_certified_access",
    )
    return replace(
        plan,
        H0=roles.H0.line if roles.H0 else plan.H0,
        H1=roles.H1.line if roles.H1 else plan.H1,
        H2=roles.H2.line if roles.H2 else plan.H2,
        resource_ledger=roles.ledger if roles.ledger.reservations else plan.resource_ledger,
        prize_lane=lane,
        draw_clock=semantics.ordered_draw_clock(parent=_replace_plan_evidence.parent, obs=_replace_plan_evidence.obs),
        metadata=tuple(sorted(metadata.items(), key=lambda row: row[0])),
    )


def _domain_new_plan(parent: Any, obs: Any, snap: Any, parent_action: list[int], parent_pre: dict[str, Any], parent_post: dict[str, Any]):
    candidate = _ORIGINAL_NEW_PLAN(parent, obs, snap, parent_action, parent_pre, parent_post)
    certificate = _domain_certificate(parent, obs, parent_action, candidate)
    if candidate is not None:
        if not certificate["eligible"]:
            return None
        plan, action, commit = candidate
        _replace_plan_evidence.parent = parent
        _replace_plan_evidence.obs = obs
        plan = _replace_plan_evidence(plan, certificate)
        if commit and commit.get("transaction"):
            commit["transaction"]["plan"] = plan
        return plan, action, commit

    # Setup stopping: a certified H0 attack beats an optional PLAY/ABILITY/END
    # only when the parent has no owning transaction and the candidate action
    # does not preserve a named H1/H2, recovery, protection, or continuity line.
    if core.parent_owner_active(parent_pre) or core.parent_owner_active(parent_post):
        return None
    roles = certificate["roles"]
    attack = _one_attack(parent, obs, roles)
    option, source = _option_source(parent, obs, parent_action)
    if attack is None or option is None or option.type == parent.OptionType.ATTACK:
        return None
    optional = option.type in (parent.OptionType.PLAY, parent.OptionType.ABILITY, parent.OptionType.END)
    if not optional or source is None and option.type != parent.OptionType.END:
        return None
    protected_ids = {
        semantics.BOSS_ORDERS,
        semantics.ENHANCED_HAMMER,
        semantics.NIGHT_STRETCHER,
        semantics.SACRED_ASH,
        semantics.BATTLE_CAGE,
    }
    if source is not None and source.id in protected_ids:
        return None
    if not certificate["eligible"]:
        return None
    action = attack
    plan = core._make_plan(
        parent,
        obs,
        snap.sha256,
        parent_action,
        "INTEGRATED_SETUP_STOP_ATTACK",
        action,
        stage="single_attack",
        H0=roles.H0.line if roles.H0 else None,
        H1=roles.H1.line if roles.H1 else None,
        H2=roles.H2.line if roles.H2 else None,
        ledger=roles.ledger,
        aborts=("H0 no longer ready", "optional step gains certified continuity"),
        metadata={"dependency_order": DEPENDENCY_ORDER, "domain_stop": "optional step did not strictly improve route"},
    )
    _replace_plan_evidence.parent = parent
    _replace_plan_evidence.obs = obs
    plan = _replace_plan_evidence(plan, certificate)
    return plan, action, None


def _clock_row(clock: Any):
    return {
        "deck_count": clock.deck_count,
        "ordered_draws": tuple(clock.ordered_draws),
    }


def _outcome_row(outcome: Outcome):
    return {
        "primary": outcome.kind.value,
        "components": tuple(kind.value for kind in outcome_components(outcome)),
        "amount": outcome.amount,
        "prevented": outcome.prevented,
        "details": outcome.details,
    }


def _lane_row(lane: PrizeLane):
    return {
        "certified": lane.certified,
        "attacks": lane.attacks,
        "steps": tuple(
            {
                "target_serial": step.target_serial,
                "prizes": step.prizes,
                "role": step.attacker_role.value,
                "outcome": _outcome_row(step.outcome),
                "hits": step.hits,
                "post_spend_hand_floor": step.post_spend_hand_floor,
                "boss_required": step.boss_required,
                "supporter_required": step.supporter_required,
                "continuity": step.continuity,
                "visible_response": step.visible_response,
                "opponent_clock": step.opponent_clock,
            }
            for step in lane.steps
        ),
    }


def _enrich_latest_trace(parent: Any, obs: Any) -> None:
    row = core.INTEGRATED_LATEST_TRACE
    if row is None or not row.get("override_action"):
        return
    plan = None
    if core.INTEGRATED_TRANSACTION is not None:
        plan = core.INTEGRATED_TRANSACTION.get("plan")
    if plan is None and row.get("plan_id"):
        # The initiating trace is emitted before the transaction is installed
        # only for single-step plans; reconstruct its public evidence.
        roles = semantics.public_roles(parent, obs)
        lanes = _corrected_prize_lanes(parent, obs, roles)
        draw = semantics.ordered_draw_clock(parent, obs)
        ledger = roles.ledger
        H0 = roles.H0.line if roles.H0 else None
        H1 = roles.H1.line if roles.H1 else None
        H2 = roles.H2.line if roles.H2 else None
    elif plan is not None:
        roles = semantics.public_roles(parent, obs)
        lanes = (plan.prize_lane,)
        draw = plan.draw_clock
        ledger = plan.resource_ledger
        H0, H1, H2 = plan.H0, plan.H1, plan.H2
    else:
        roles = semantics.public_roles(parent, obs)
        lanes = _corrected_prize_lanes(parent, obs, roles)
        draw = semantics.ordered_draw_clock(parent, obs)
        ledger = roles.ledger
        H0 = roles.H0.line if roles.H0 else None
        H1 = roles.H1.line if roles.H1 else None
        H2 = roles.H2.line if roles.H2 else None
    clocks = semantics.public_clocks(parent, obs, roles)
    row.update(
        H0=H0,
        H1=H1,
        H2=H2,
        ledger={
            "roles": tuple((line, role.value) for line, role in ledger.roles),
            "reservations": tuple(
                (reservation.token, reservation.role.value, reservation.purpose, tuple(sorted(reservation.branches)))
                for reservation in ledger.reservations
            ),
        },
        draw_clock={"own": _clock_row(draw.own), "opponent": _clock_row(draw.opponent)},
        clocks={
            key: value.__dict__ if hasattr(value, "__dict__") else repr(value)
            for key, value in clocks.items()
        },
        prize_lane=tuple(_lane_row(lane) for lane in lanes),
        typed_outcomes={
            key: _outcome_row(getattr(roles, key).outcome)
            for key in ("H0", "H1", "H2")
            if getattr(roles, key) is not None
        },
        dependency_order=DEPENDENCY_ORDER,
    )


def install() -> None:
    global _PATCHED
    if _PATCHED:
        return
    semantics.outcome_for_attack = _corrected_outcome_for_attack
    semantics.enumerate_prize_lanes = _corrected_prize_lanes
    core._new_plan = _domain_new_plan
    _PATCHED = True


def reset_integrated_state() -> None:
    core.reset_integrated_state()


def agent(parent: Any, parent_agent: Any, obs_dict: dict) -> list[int]:
    install()
    action = core.agent(parent, parent_agent, obs_dict)
    try:
        if isinstance(obs_dict, dict) and obs_dict.get("select") is not None:
            obs = parent.to_observation_class(obs_dict)
            if action_is_valid(obs, action):
                _enrich_latest_trace(parent, obs)
    except Exception:
        # Trace enrichment never changes an already validated action.  The
        # focused gate treats an unenriched override as a structural failure.
        pass
    return action


install()
