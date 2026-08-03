"""Fail closed on unmodeled damage modifiers without weakening Fan triggers."""

from dataclasses import replace

import planner_integrated as integrated
import planner_policy as core
import planner_semantics as semantics
from planner_model import Outcome, OutcomeKind


_SUPPORTED_EFFECT_DAMAGE = frozenset({1070})  # Teleportation Attack composite
_BASE_OUTCOME_FOR_ATTACK = semantics.outcome_for_attack


def outcome_for_attack(parent, attacker, attack, target, *, hand_count):
    outcome = _BASE_OUTCOME_FOR_ATTACK(
        parent,
        attacker,
        attack,
        target,
        hand_count=hand_count,
    )
    text = semantics._normalized(getattr(attack, "text", ""))
    if (
        outcome.kind is OutcomeKind.ATTACK_DAMAGE
        and text
        and attack.attackId not in _SUPPORTED_EFFECT_DAMAGE
    ):
        return Outcome(
            OutcomeKind.UNKNOWN,
            target_line=outcome.target_line,
            source_serial=outcome.source_serial,
            details=(("unsupported_attack_id", attack.attackId), ("reason", "unmodeled damage modifier/effect")),
        )
    return outcome


def best_ready_attack(parent, obs, pokemon, target):
    supported = [
        certificate
        for certificate in semantics.attack_certificates(parent, obs, pokemon, target)
        if certificate.legal_now
        and not certificate.outcome.prevented
        and certificate.outcome.kind in (
            OutcomeKind.DIRECT_KO,
            OutcomeKind.PLACE_COUNTERS,
            OutcomeKind.ATTACK_DAMAGE,
        )
    ]
    if not supported:
        return None
    order = {
        OutcomeKind.DIRECT_KO: 3,
        OutcomeKind.PLACE_COUNTERS: 2,
        OutcomeKind.ATTACK_DAMAGE: 1,
    }
    return max(
        supported,
        key=lambda certificate: (
            order[certificate.outcome.kind],
            certificate.outcome.amount,
            -certificate.attack_id,
        ),
    )


def public_positive_attack_response(parent, obs):
    """Conservative trigger possibility; not an exact damage certificate."""
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    theirs = obs.current.players[1 - owner]
    if len(mine.active) != 1 or len(theirs.active) != 1:
        return False
    attacker = theirs.active[0]
    data = parent.card_table.get(attacker.id)
    available = semantics.energy_units(parent, attacker)
    if data is None or available is None:
        return False
    for attack_id in data.attacks or []:
        attack = parent.attack_table.get(attack_id)
        if attack is None or not isinstance(attack.damage, int) or attack.damage <= 0:
            continue
        if not semantics.missing_energy(parent, available, attack.energies):
            return True
    return False


semantics.outcome_for_attack = outcome_for_attack
semantics.best_ready_attack = best_ready_attack
semantics.public_positive_attack_response = public_positive_attack_response
core.best_ready_attack = best_ready_attack
core.public_positive_attack_response = public_positive_attack_response

