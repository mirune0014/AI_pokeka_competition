"""Owner-correct typed semantics for cg Pokemon without playerIndex."""

from dataclasses import replace

import planner_policy as core
import planner_semantics as semantics
from planner_model import OutcomeKind, lineage_key


_ORIGINAL_RESOLVE = semantics.resolve_public_outcome


def pokemon_owner(state, pokemon):
    serial = getattr(pokemon, "serial", None)
    if not isinstance(serial, int) or isinstance(serial, bool) or serial <= 0:
        return None
    matches = []
    for owner, player in enumerate(state.players):
        for public in list(player.active) + list(player.bench):
            if getattr(public, "serial", None) == serial:
                matches.append(owner)
    return matches[0] if len(matches) == 1 else None


def resolve_public_outcome(
    parent,
    state,
    attacker,
    target,
    outcome,
    *,
    target_is_bench=False,
):
    target_owner = pokemon_owner(state, target)
    attacker_owner = pokemon_owner(state, attacker)
    if target_owner is None or attacker_owner is None:
        return replace(outcome, kind=OutcomeKind.UNKNOWN, amount=0, prevented=True, target_line=None)
    line = lineage_key(target, target_owner)
    if line is None:
        return replace(outcome, kind=OutcomeKind.UNKNOWN, amount=0, prevented=True, target_line=None)
    corrected = replace(outcome, target_line=line)
    corrected = _ORIGINAL_RESOLVE(
        parent,
        state,
        attacker,
        target,
        corrected,
        target_is_bench=target_is_bench,
    )
    if corrected.kind is OutcomeKind.ATTACK_DAMAGE and target_is_bench:
        target_data = parent.card_table.get(target.id)
        field = state.players[target_owner]
        if (
            target_data is None
            or any(public.id == semantics.SHAYMIN for public in list(field.active) + list(field.bench))
            and not target_data.ex
            and not target_data.megaEx
        ):
            return replace(corrected, amount=0, prevented=True)
    return corrected


def attack_certificates(parent, obs, pokemon, target):
    state = obs.current
    owner = pokemon_owner(state, pokemon)
    target_owner = pokemon_owner(state, target)
    if owner is None or target_owner is None:
        return ()
    line = lineage_key(pokemon, owner)
    data = parent.card_table.get(getattr(pokemon, "id", None))
    available = semantics.energy_units(parent, pokemon)
    if line is None or data is None or available is None:
        return ()
    certificates = []
    hand_count = state.players[owner].handCount
    for attack_id in data.attacks or []:
        attack = parent.attack_table.get(attack_id)
        if attack is None:
            return ()
        missing = semantics.missing_energy(parent, available, attack.energies)
        outcome = semantics.outcome_for_attack(
            parent,
            pokemon,
            attack,
            target,
            hand_count=hand_count,
        )
        target_line = lineage_key(target, target_owner)
        if target_line is None:
            return ()
        outcome = replace(outcome, target_line=target_line)
        outcome = resolve_public_outcome(
            parent,
            state,
            pokemon,
            target,
            outcome,
            target_is_bench=target in state.players[target_owner].bench,
        )
        certificates.append(
            semantics.AttackCertificate(
                line,
                pokemon.serial,
                attack_id,
                outcome,
                missing,
                not missing,
            )
        )
    return tuple(certificates)


semantics.resolve_public_outcome = resolve_public_outcome
semantics.attack_certificates = attack_certificates
core.attack_certificates = attack_certificates

