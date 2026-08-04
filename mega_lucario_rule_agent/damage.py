"""Strict target-damage evaluation from public information for the fixed deck.

This module certifies only damage dealt to the defending Active Pokemon.  An
attack proposal must separately prove legality, attack locks, Special
Conditions, costs, recoil, Energy discard, and other post-attack effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional, Tuple

try:  # Package import in tests.
    from .card_meta import ATTACK_META_BY_ID
except ImportError:  # Flat submission import from main.py.
    from card_meta import ATTACK_META_BY_ID


FIGHTING_ENERGY_TYPE = 6
RESISTANCE_REDUCTION = 30
PPP_DAMAGE_BONUS = 30


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

    if attack_id not in ATTACK_META_BY_ID:
        return _unknown_result(
            attack_id,
            0,
            max(0, int(ppp_count)),
            int(stadium_modifier or 0),
            target_remaining_hp,
            ("UNKNOWN_ATTACK",),
        )
    attack = ATTACK_META_BY_ID[attack_id]
    if not isinstance(attack.printed_damage, int):
        return _unknown_result(
            attack_id,
            0,
            max(0, int(ppp_count)),
            int(stadium_modifier or 0),
            target_remaining_hp,
            ("UNKNOWN_PRINTED_DAMAGE",),
        )
    base_damage = int(attack.printed_damage)
    ppp_count = max(0, min(4, int(ppp_count)))
    unknown_reasons = list(unsupported_effects)
    if stadium_modifier is None:
        unknown_reasons.append("UNKNOWN_STADIUM_MODIFIER")
        stadium_value = 0
    else:
        stadium_value = int(stadium_modifier)
    if target_remaining_hp is not None and target_remaining_hp < 0:
        unknown_reasons.append("INVALID_TARGET_HP")

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
    return {
        int(attack_id): evaluate_attack_damage(
            int(attack_id), target_remaining_hp=target_remaining_hp, **kwargs
        )
        for attack_id in sorted(set(int(value) for value in attack_ids))
    }


__all__ = [
    "DamageResult",
    "FIGHTING_ENERGY_TYPE",
    "PPP_DAMAGE_BONUS",
    "RESISTANCE_REDUCTION",
    "build_damage_table",
    "evaluate_attack_damage",
]
