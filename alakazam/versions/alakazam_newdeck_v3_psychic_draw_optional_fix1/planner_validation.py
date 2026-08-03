"""Structural validation for reservations and complete integrated plans."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any, Iterable

import planner_model as model
from planner_model import BaseRole, IntegratedTurnPlan, PlanStep, ResourceLedger
import planner_runtime_model as runtime_model


VALID_BRANCHES = frozenset(
    {
        "main",
        "H0_survives",
        "H0_KO",
        "opponent_attack",
        "response",
        "recovery",
    }
)
RESOURCE_PATTERN = re.compile(
    r"^(?:card|energy|tool|budget|retreat|boss|bench|evolution|recovery|stadium|ability|attack):[A-Za-z0-9_.-]+$"
)


def reserve(
    self: ResourceLedger,
    token: str,
    role: BaseRole,
    purpose: str,
    branches: Iterable[str] = ("main",),
):
    if (
        not isinstance(token, str)
        or RESOURCE_PATTERN.fullmatch(token) is None
        or not isinstance(role, BaseRole)
        or not isinstance(purpose, str)
        or not purpose.strip()
        or isinstance(branches, (str, bytes))
    ):
        return None
    try:
        branch_set = frozenset(branches)
    except TypeError:
        return None
    if not branch_set or not branch_set <= VALID_BRANCHES:
        return None
    for existing in self.reservations:
        if existing.token == token and existing.branches & branch_set:
            return None
    return replace(
        self,
        reservations=self.reservations
        + (model.Reservation(token, role, purpose.strip(), branch_set),),
    )


def _valid_ledger(plan: IntegratedTurnPlan) -> bool:
    role_map = dict(plan.resource_ledger.roles)
    if len(role_map) != len(plan.resource_ledger.roles):
        return False
    requested = [line for line in (plan.H0, plan.H1, plan.H2) if line is not None]
    if len(set(requested)) != len(requested):
        return False
    for role, line in ((BaseRole.H0, plan.H0), (BaseRole.H1, plan.H1), (BaseRole.H2, plan.H2)):
        if line is not None and role_map.get(line) is not role:
            return False
    for reservation in plan.resource_ledger.reservations:
        if (
            RESOURCE_PATTERN.fullmatch(reservation.token) is None
            or not reservation.branches
            or not reservation.branches <= VALID_BRANCHES
            or reservation.role not in role_map.values()
        ):
            return False
    for left, reservation in enumerate(plan.resource_ledger.reservations):
        for other in plan.resource_ledger.reservations[left + 1 :]:
            if reservation.token == other.token and reservation.branches & other.branches:
                return False
    return True


def _valid_budget(plan: IntegratedTurnPlan) -> bool:
    budget = plan.turn_budget
    if not isinstance(budget.bench_slots, int) or isinstance(budget.bench_slots, bool) or budget.bench_slots < 0:
        return False
    if any(slots < 0 for _, slots in budget.tool_slots):
        return False
    if len(dict(budget.tool_slots)) != len(budget.tool_slots):
        return False
    if len(dict(budget.abilities)) != len(budget.abilities):
        return False
    return all(isinstance(value, bool) for value in (
        budget.manual_attachment,
        budget.supporter,
        budget.stadium,
        budget.retreat,
        budget.attack,
    ))


def _valid_clocks(plan: IntegratedTurnPlan) -> bool:
    for clock in (plan.draw_clock.own, plan.draw_clock.opponent):
        if not isinstance(clock.deck_count, int) or isinstance(clock.deck_count, bool) or clock.deck_count < 0:
            return False
        for name, count, optional in clock.ordered_draws:
            if name not in runtime_model._DRAW_EVENTS or not isinstance(count, int) or count < 0 or not isinstance(optional, bool):
                return False
    return True


def _valid_objective(plan: IntegratedTurnPlan) -> bool:
    objective = plan.objective
    if (
        objective.shorter_certified_prize_lane > 0
        or objective.fewer_abandoned_reservations > 0
        or objective.lower_bench_prize_liability > 0
    ):
        return False
    normalized = tuple(repr(value) for value in objective.stable_semantic_tie_break)
    return normalized == tuple(objective.stable_semantic_tie_break)


def validate_plan(
    parent: Any,
    obs: Any,
    plan: IntegratedTurnPlan,
    action: list[int],
    *,
    current_stage: str | None = None,
) -> tuple[bool, str]:
    if not isinstance(plan, IntegratedTurnPlan) or not plan.plan_id or not plan.snapshot_hash:
        return False, "invalid plan identity"
    if not _valid_ledger(plan):
        return False, "role/resource ledger conflict"
    if not _valid_budget(plan):
        return False, "TurnBudget invalid"
    if not _valid_clocks(plan):
        return False, "DrawClock invalid"
    if not _valid_objective(plan):
        return False, "objective sign/tie schema invalid"
    if len(plan.prize_lane.steps) > 3:
        return False, "PrizeLane exceeds three KOs"
    keys = tuple(
        runtime_model.stable_option_key(parent, obs, obs.select.option[index])
        for index in action
    ) if model.action_is_valid(obs, action) else ()
    if not keys or any(key is None for key in keys):
        return False, "action semantic mapping invalid"
    if tuple(plan.allowed_option_keys) != keys:
        return False, "allowed keys differ from current action"
    if not plan.ordered_plan_steps:
        return False, "ordered plan is empty"
    step = plan.ordered_plan_steps[-1]
    if step.option_keys != keys or step.expected_context != int(obs.select.context):
        return False, "current PlanStep differs from callback"
    if current_stage is not None and plan.expected_stage != current_stage:
        return False, "transaction stage mismatch"
    if not runtime_model.action_is_certified(
        parent,
        obs,
        action,
        expected_context=obs.select.context,
        allowed_keys=keys,
    ):
        return False, "Select obligation not satisfied"
    return True, "certified"


def advance_plan_step(
    parent: Any,
    obs: Any,
    plan: IntegratedTurnPlan,
    action: list[int],
    stage: str,
) -> IntegratedTurnPlan | None:
    if not model.action_is_valid(obs, action):
        return None
    keys = tuple(runtime_model.stable_option_key(parent, obs, obs.select.option[index]) for index in action)
    if any(key is None for key in keys):
        return None
    step = PlanStep(stage, keys, int(obs.select.context))
    return replace(
        plan,
        ordered_plan_steps=plan.ordered_plan_steps + (step,),
        expected_stage=stage,
        allowed_option_keys=keys,
    )


def install() -> None:
    model.ResourceLedger.reserve = reserve

