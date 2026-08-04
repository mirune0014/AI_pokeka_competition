"""Strict target-damage evaluation from public information for the fixed deck.

This module certifies only damage dealt to the defending Active Pokemon.  An
attack proposal must separately prove legality, attack locks, Special
Conditions, costs, recoil, Energy discard, and other post-attack effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from typing import Dict, Iterable, Mapping, Optional, Tuple

try:  # Package import in tests.
    from .card_meta import ATTACK_META_BY_ID
    from .state_view import PhysicalRef, PublicState, public_state_fingerprint
except ImportError:  # Flat submission import from main.py.
    from card_meta import ATTACK_META_BY_ID
    from state_view import PhysicalRef, PublicState, public_state_fingerprint


FIGHTING_ENERGY_TYPE = 6
RESISTANCE_REDUCTION = 30
PPP_DAMAGE_BONUS = 30


def _is_exact_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


@dataclass(frozen=True)
class DamageResult:
    """Exactness of target damage, not exactness of the whole attack outcome."""

    attack_id: int
    exact_damage: bool
    base_damage: int
    ppp_count: int
    ppp_bonus: int
    stadium_modifier: int
    before_weakness: Optional[int]
    weakness_multiplier: Optional[int]
    resistance_reduction: Optional[int]
    final_damage: Optional[int]
    target_remaining_hp: Optional[int]
    knockout: Optional[bool]
    prevention_applied: bool
    unknown_reasons: Tuple[str, ...]

    @property
    def exact(self) -> bool:
        """Compatibility alias for callers that explicitly consume damage only."""

        return self.exact_damage

    @property
    def damage_margin(self) -> Optional[int]:
        if self.final_damage is None or self.target_remaining_hp is None:
            return None
        return self.final_damage - self.target_remaining_hp


_BOUND_DAMAGE_ISSUER_TOKEN = object()


@dataclass(frozen=True)
class BoundDamageTable:
    """Damage rows bound to one exact agent-visible state and Active target."""

    state_fingerprint: str
    target_ref: Optional[PhysicalRef]
    results: Tuple[Tuple[int, DamageResult], ...]
    _issuer_token: object = dataclass_field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._issuer_token is not _BOUND_DAMAGE_ISSUER_TOKEN:
            raise ValueError("BoundDamageTable values require the checked builder")
        if (
            not isinstance(self.state_fingerprint, str)
            or len(self.state_fingerprint) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.state_fingerprint
            )
        ):
            raise ValueError("bound damage table requires a lowercase SHA-256")
        if self.target_ref is not None and not isinstance(self.target_ref, PhysicalRef):
            raise ValueError("bound damage target must be a PhysicalRef")
        normalized = tuple(sorted(self.results, key=lambda item: item[0]))
        attack_ids = tuple(attack_id for attack_id, _ in normalized)
        if len(set(attack_ids)) != len(attack_ids):
            raise ValueError("bound damage table cannot repeat an attack ID")
        for attack_id, result in normalized:
            if (
                isinstance(attack_id, bool)
                or not isinstance(attack_id, int)
                or attack_id <= 0
                or not isinstance(result, DamageResult)
                or result.attack_id != attack_id
            ):
                raise ValueError("bound damage rows must match positive attack IDs")
        object.__setattr__(self, "results", normalized)

    def as_dict(self) -> Dict[int, DamageResult]:
        return dict(self.results)

    def get(self, attack_id: int) -> Optional[DamageResult]:
        return next(
            (result for key, result in self.results if key == attack_id),
            None,
        )


def _unknown_result(
    attack_id: int,
    base_damage: int,
    ppp_count: int,
    stadium_modifier: int,
    target_remaining_hp: Optional[int],
    reasons: Iterable[str],
) -> DamageResult:
    return DamageResult(
        attack_id=attack_id,
        exact_damage=False,
        base_damage=base_damage,
        ppp_count=ppp_count,
        ppp_bonus=PPP_DAMAGE_BONUS * ppp_count,
        stadium_modifier=stadium_modifier,
        before_weakness=None,
        weakness_multiplier=None,
        resistance_reduction=None,
        final_damage=None,
        target_remaining_hp=target_remaining_hp,
        knockout=None,
        prevention_applied=False,
        unknown_reasons=tuple(sorted(set(reasons))),
    )


def evaluate_attack_damage(
    attack_id: int,
    target_remaining_hp: Optional[int],
    target_weakness: Optional[int] = None,
    target_resistance: Optional[int] = None,
    ppp_count: int = 0,
    stadium_modifier: Optional[int] = 0,
    attacker_is_rule_box: bool = False,
    public_rule_box_damage_prevention: bool = False,
    conditions: Optional[Mapping[str, Optional[bool]]] = None,
    unsupported_effects: Iterable[str] = (),
) -> DamageResult:
    """Evaluate damage only when every required public modifier is known.

    Unknown public damage modifiers return exact_damage=False and never infer a
    knockout.  This function does not certify that the attack is legal or model
    its post-attack effects.
    ``conditions`` currently supports ``lunatone_on_bench`` for Cosmic Beam.
    """

    if not _is_exact_int(attack_id) or attack_id <= 0:
        raise ValueError("attack_id must be a positive exact int")
    raw_unknown_reasons = list(unsupported_effects)
    if not _is_exact_int(ppp_count) or not 0 <= ppp_count <= 4:
        raw_unknown_reasons.append("INVALID_PPP_COUNT")
        ppp_value = 0
    else:
        ppp_value = ppp_count
    if stadium_modifier is None:
        raw_unknown_reasons.append("UNKNOWN_STADIUM_MODIFIER")
        stadium_value = 0
    elif not _is_exact_int(stadium_modifier):
        raw_unknown_reasons.append("INVALID_STADIUM_MODIFIER")
        stadium_value = 0
    else:
        stadium_value = stadium_modifier
    if target_remaining_hp is not None and (
        not _is_exact_int(target_remaining_hp) or target_remaining_hp < 0
    ):
        raw_unknown_reasons.append("INVALID_TARGET_HP")
        target_value = None
    else:
        target_value = target_remaining_hp
    if target_weakness is not None and not _is_exact_int(target_weakness):
        raw_unknown_reasons.append("INVALID_TARGET_WEAKNESS")
    if target_resistance is not None and not _is_exact_int(target_resistance):
        raw_unknown_reasons.append("INVALID_TARGET_RESISTANCE")
    if not isinstance(attacker_is_rule_box, bool):
        raw_unknown_reasons.append("INVALID_ATTACKER_RULE_BOX_FLAG")
    if not isinstance(public_rule_box_damage_prevention, bool):
        raw_unknown_reasons.append("INVALID_PREVENTION_FLAG")

    if attack_id not in ATTACK_META_BY_ID:
        return _unknown_result(
            attack_id,
            0,
            ppp_value,
            stadium_value,
            target_value,
            tuple(raw_unknown_reasons) + ("UNKNOWN_ATTACK",),
        )
    attack = ATTACK_META_BY_ID[attack_id]
    if not isinstance(attack.printed_damage, int):
        return _unknown_result(
            attack_id,
            0,
            ppp_value,
            stadium_value,
            target_value,
            tuple(raw_unknown_reasons) + ("UNKNOWN_PRINTED_DAMAGE",),
        )
    base_damage = int(attack.printed_damage)
    ppp_count = ppp_value
    target_remaining_hp = target_value
    unknown_reasons = raw_unknown_reasons

    conditions = conditions or {}
    ignores_weakness_resistance = attack_id == 980
    if attack_id == 980:
        lunatone = conditions.get("lunatone_on_bench")
        if lunatone is None:
            unknown_reasons.append("UNKNOWN_LUNATONE_BENCH_CONDITION")
        elif not lunatone:
            final_damage = 0
            return DamageResult(
                attack_id=attack_id,
                exact_damage=not unknown_reasons,
                base_damage=base_damage,
                ppp_count=ppp_count,
                ppp_bonus=PPP_DAMAGE_BONUS * ppp_count,
                stadium_modifier=stadium_value,
                before_weakness=0 if not unknown_reasons else None,
                weakness_multiplier=1 if not unknown_reasons else None,
                resistance_reduction=0 if not unknown_reasons else None,
                final_damage=final_damage if not unknown_reasons else None,
                target_remaining_hp=target_remaining_hp,
                knockout=(
                    final_damage >= target_remaining_hp
                    if not unknown_reasons and target_remaining_hp is not None
                    else None
                ),
                prevention_applied=False,
                unknown_reasons=tuple(sorted(set(unknown_reasons))),
            )

    if unknown_reasons:
        return _unknown_result(
            attack_id,
            base_damage,
            ppp_count,
            stadium_value,
            target_remaining_hp,
            unknown_reasons,
        )

    ppp_bonus = PPP_DAMAGE_BONUS * ppp_count
    before_weakness = max(0, base_damage + ppp_bonus + stadium_value)
    if public_rule_box_damage_prevention and attacker_is_rule_box:
        final_damage = 0
        weakness_multiplier = 1
        resistance_reduction = 0
        prevention_applied = True
    else:
        prevention_applied = False
        if ignores_weakness_resistance:
            weakness_multiplier = 1
            resistance_reduction = 0
        else:
            weakness_multiplier = 2 if target_weakness == FIGHTING_ENERGY_TYPE else 1
            resistance_reduction = (
                RESISTANCE_REDUCTION if target_resistance == FIGHTING_ENERGY_TYPE else 0
            )
        final_damage = max(0, before_weakness * weakness_multiplier - resistance_reduction)
    knockout = None if target_remaining_hp is None else final_damage >= target_remaining_hp
    return DamageResult(
        attack_id=attack_id,
        exact_damage=True,
        base_damage=base_damage,
        ppp_count=ppp_count,
        ppp_bonus=ppp_bonus,
        stadium_modifier=stadium_value,
        before_weakness=before_weakness,
        weakness_multiplier=weakness_multiplier,
        resistance_reduction=resistance_reduction,
        final_damage=final_damage,
        target_remaining_hp=target_remaining_hp,
        knockout=knockout,
        prevention_applied=prevention_applied,
        unknown_reasons=(),
    )


def build_damage_table(
    attack_ids: Iterable[int],
    target_remaining_hp: Optional[int],
    **kwargs: object,
) -> Dict[int, DamageResult]:
    normalized = tuple(attack_ids)
    if any(
        not _is_exact_int(attack_id) or attack_id <= 0
        for attack_id in normalized
    ):
        raise ValueError("attack IDs must be positive exact ints")
    return {
        attack_id: evaluate_attack_damage(
            attack_id, target_remaining_hp=target_remaining_hp, **kwargs
        )
        for attack_id in sorted(set(normalized))
    }


def build_bound_damage_table(
    state: PublicState,
    attack_ids: Iterable[int],
    **kwargs: object,
) -> BoundDamageTable:
    """Evaluate current opposing Active damage and bind it to this state."""

    if not isinstance(state, PublicState):
        raise ValueError("bound damage evaluation requires a PublicState")
    target = state.opponent_active
    target_remaining_hp = None if target is None else target.remaining_hp
    results = build_damage_table(
        attack_ids,
        target_remaining_hp=target_remaining_hp,
        **kwargs,
    )
    return BoundDamageTable(
        state_fingerprint=public_state_fingerprint(state),
        target_ref=None if target is None else target.ref,
        results=tuple(results.items()),
        _issuer_token=_BOUND_DAMAGE_ISSUER_TOKEN,
    )


__all__ = [
    "BoundDamageTable",
    "DamageResult",
    "FIGHTING_ENERGY_TYPE",
    "PPP_DAMAGE_BONUS",
    "RESISTANCE_REDUCTION",
    "build_damage_table",
    "build_bound_damage_table",
    "evaluate_attack_damage",
]

# Strict whole-outcome APIs live in a separate module so legacy callers cannot
# accidentally treat target-only DamageResult.exact as a complete certificate.
try:  # Package import in tests.
    from .attack_outcomes import (
        AttackCallbackPreview,
        AttackOutcome,
        BoundAttackOutcomeTable,
        build_attack_outcome_table,
        semantic_options_fingerprint,
    )
except ImportError:  # Flat submission import from main.py.
    from attack_outcomes import (  # type: ignore[no-redef]
        AttackCallbackPreview,
        AttackOutcome,
        BoundAttackOutcomeTable,
        build_attack_outcome_table,
        semantic_options_fingerprint,
    )

__all__ += [
    "AttackCallbackPreview",
    "AttackOutcome",
    "BoundAttackOutcomeTable",
    "build_attack_outcome_table",
    "semantic_options_fingerprint",
]
