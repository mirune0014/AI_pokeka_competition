"""Eligibility guard separating learnable decisions from protected callbacks."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from .public_state import enum_int, get_field
from .semantic_action import validate_engine_action
from .teacher_adapter import TeacherDecision


class GuardCategory(str, Enum):
    ENGINE_ILLEGAL = "ENGINE_ILLEGAL"
    EXECUTION_INVARIANT = "EXECUTION_INVARIANT"
    LATEST_CERTIFIED_OWNER = "LATEST_CERTIFIED_OWNER"
    HEURISTIC_STRATEGIC = "HEURISTIC_STRATEGIC"
    UNKNOWN_EFFECT = "UNKNOWN_EFFECT"
    SURFACE_EXCLUDED = "SURFACE_EXCLUDED"


@dataclass(frozen=True)
class ProtectedFallback:
    action: tuple[int, ...]
    hard: bool
    reason: str


@dataclass(frozen=True)
class GuardResult:
    actor_learnable: bool
    ppo_eligible: bool
    legal_option_mask: tuple[bool, ...]
    actor_option_mask: tuple[bool, ...]
    counts: dict[str, int]
    reasons: tuple[str, ...]
    categories: tuple[GuardCategory, ...]
    protected_fallback: ProtectedFallback


_BAD_RESET_MARKERS = (
    "retry",
    "reset",
    "rollback",
    "exception",
    "emergency",
    "binding_fail",
    "binding fail",
)


class DecisionContract:
    def evaluate(
        self,
        observation: Any,
        teacher: TeacherDecision,
        *,
        unknown_effect_fields: Iterable[str] = (),
    ) -> GuardResult:
        select = get_field(observation, "select")
        options = list(get_field(select, "option", ()) or ())
        legal_mask = tuple(True for _ in options)
        reasons: list[str] = []
        categories: list[GuardCategory] = []
        counts: Counter[str] = Counter()

        def add(category: GuardCategory, reason: str) -> None:
            categories.append(category)
            reasons.append(reason)
            counts[category.value] += 1

        try:
            validate_engine_action(observation, teacher.action_list())
        except (TypeError, ValueError) as exc:
            add(GuardCategory.ENGINE_ILLEGAL, f"teacher_action:{exc}")

        if teacher.call_count != 1:
            add(
                GuardCategory.EXECUTION_INVARIANT,
                f"teacher_call_count:{teacher.call_count}",
            )
        if not teacher.telemetry:
            add(GuardCategory.EXECUTION_INVARIANT, "missing_telemetry")
            final: dict[str, Any] = {}
        else:
            final = teacher.telemetry[-1]
            if len(teacher.telemetry) != 1:
                add(
                    GuardCategory.EXECUTION_INVARIANT,
                    f"telemetry_row_count:{len(teacher.telemetry)}",
                )
        select_type = enum_int(get_field(select, "type"))
        select_context = enum_int(get_field(select, "context"))
        minimum = enum_int(get_field(select, "minCount"))
        maximum = enum_int(get_field(select, "maxCount"))
        if select_type != 0:
            add(GuardCategory.SURFACE_EXCLUDED, f"select_type:{select_type}")
        if select_context != 0:
            add(
                GuardCategory.SURFACE_EXCLUDED,
                f"select_context:{select_context}",
            )
        if minimum != 1 or maximum != 1:
            add(
                GuardCategory.SURFACE_EXCLUDED,
                f"selection_cardinality:{minimum}:{maximum}",
            )
        if len(options) < 2:
            add(GuardCategory.SURFACE_EXCLUDED, f"option_count:{len(options)}")

        owner_before = final.get("active_owner_before")
        owner_after = final.get("active_owner_after")
        active_owner = final.get("active_transaction_owner")
        if (
            owner_before is not None
            or owner_after is not None
            or active_owner is not None
        ):
            add(
                GuardCategory.LATEST_CERTIFIED_OWNER,
                f"owner:{owner_before}->{owner_after}:{active_owner}",
            )
        eligible = tuple(final.get("eligible_rule_ids") or ())
        if eligible:
            add(
                GuardCategory.HEURISTIC_STRATEGIC,
                "eligible_rules:" + ",".join(map(str, eligible)),
            )
        if final.get("precedence_reason") != "rank17_exact_parent":
            add(
                GuardCategory.HEURISTIC_STRATEGIC,
                f"precedence_reason:{final.get('precedence_reason')}",
            )
        if final.get("winning_rule_id") != "exact_historical_silver":
            add(
                GuardCategory.HEURISTIC_STRATEGIC,
                f"winning_rule:{final.get('winning_rule_id')}",
            )
        if final.get("rollback_reason"):
            add(
                GuardCategory.EXECUTION_INVARIANT,
                f"rollback:{final.get('rollback_reason')}",
            )
        if final.get("caught_exceptions"):
            add(GuardCategory.EXECUTION_INVARIANT, "caught_exception")
        if final.get("invalid_or_emergency_fallback"):
            add(GuardCategory.EXECUTION_INVARIANT, "emergency_fallback")
        if final.get("option_binding_result") not in (None, "BOUND"):
            add(
                GuardCategory.EXECUTION_INVARIANT,
                f"option_binding:{final.get('option_binding_result')}",
            )
        duplicate = final.get("duplicate_or_reset_state")
        if duplicate is not None:
            add(
                GuardCategory.EXECUTION_INVARIANT,
                f"duplicate_or_reset:{duplicate}",
            )
        telemetry_text = " ".join(
            str(final.get(key, ""))
            for key in (
                "precedence_reason",
                "rollback_reason",
                "duplicate_or_reset_state",
            )
        ).lower()
        if any(marker in telemetry_text for marker in _BAD_RESET_MARKERS):
            if GuardCategory.EXECUTION_INVARIANT not in categories:
                add(GuardCategory.EXECUTION_INVARIANT, "forbidden_execution_marker")

        unknown = tuple(sorted(set(unknown_effect_fields)))
        if unknown:
            add(
                GuardCategory.UNKNOWN_EFFECT,
                "unknown_effects:" + ",".join(unknown),
            )

        blocking = {
            GuardCategory.ENGINE_ILLEGAL,
            GuardCategory.EXECUTION_INVARIANT,
            GuardCategory.LATEST_CERTIFIED_OWNER,
            GuardCategory.HEURISTIC_STRATEGIC,
            GuardCategory.SURFACE_EXCLUDED,
        }
        learnable = not any(category in blocking for category in categories)
        # Unknown effects and novel cards are recorded, never converted into a
        # fallback or legal-action mask.
        actor_mask = legal_mask if learnable else tuple(False for _ in options)
        reason = "learnable" if learnable else ";".join(reasons)
        return GuardResult(
            actor_learnable=learnable,
            ppo_eligible=learnable,
            legal_option_mask=legal_mask,
            actor_option_mask=actor_mask,
            counts=dict(counts),
            reasons=tuple(reasons),
            categories=tuple(dict.fromkeys(categories)),
            protected_fallback=ProtectedFallback(
                action=teacher.action,
                hard=not learnable,
                reason=reason,
            ),
        )
