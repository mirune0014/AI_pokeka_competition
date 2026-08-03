"""Deterministic public-state domain semantics for the integrated planner."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from math import ceil
from typing import Any

from planner_model import (
    BaseRole,
    BoardClock,
    DeckClock,
    DrawClock,
    Outcome,
    OutcomeKind,
    PlanObjective,
    PrizeClock,
    PrizeLane,
    PrizeLaneStep,
    ResourceLedger,
    lineage_key,
)


HANDHELD_FAN = 1161
LUCKY_HELMET = 1156
MIST_ENERGY = 11
ENRICHING_ENERGY = 13
TELEPATH_PSYCHIC = 19
BASIC_PSYCHIC = 5
LEGACY_ENERGY = 12
SHAYMIN = 343
BATTLE_CAGE = 1264
FEZANDIPITI_EX = 140
GENESECT = 142
ENHANCED_HAMMER = 1081
NIGHT_STRETCHER = 1097
SACRED_ASH = 1129
BOSS_ORDERS = 1182
POWERFUL_HAND = 1072
RUN_AWAY_DRAW_CARD = 66


@dataclass(frozen=True)
class AttackCertificate:
    line: tuple[int, int]
    serial: int
    attack_id: int
    outcome: Outcome
    missing: tuple[int, ...]
    legal_now: bool


@dataclass(frozen=True)
class RoleCertificate:
    H0: AttackCertificate | None
    H1: AttackCertificate | None
    H2: AttackCertificate | None
    ledger: ResourceLedger


def _int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def prize_value(parent: Any, pokemon: Any) -> int | None:
    data = parent.card_table.get(getattr(pokemon, "id", None))
    if data is None:
        return None
    prizes = 3 if data.megaEx else 2 if data.ex else 1
    for card in getattr(pokemon, "energyCards", None) or []:
        if card.id == LEGACY_ENERGY:
            prizes -= 1
    for card in getattr(pokemon, "tools", None) or []:
        if card.id == 1172 and "Lillie" in (data.name or ""):
            prizes -= 1
    return max(0, prizes)


def energy_units(parent: Any, pokemon: Any) -> tuple[int, ...] | None:
    units = tuple(_int(value) for value in (getattr(pokemon, "energies", None) or []))
    cards = list(getattr(pokemon, "energyCards", None) or [])
    if any(value is None for value in units) or len(cards) != len(units):
        return None
    for value, card in zip(units, cards):
        data = parent.card_table.get(getattr(card, "id", None))
        if data is None:
            return None
        declared = _int(getattr(data, "energyType", None))
        if card.id == ENRICHING_ENERGY:
            # Enriching is Colorless and can never fill a Psychic reservation.
            if value != _int(parent.EnergyType.COLORLESS):
                return None
        elif declared is not None and value != declared:
            return None
    return units


def missing_energy(parent: Any, available: tuple[int, ...], required: Any) -> tuple[int, ...]:
    pool = list(available)
    needs = [_int(value) for value in (required or [])]
    colorless = _int(parent.EnergyType.COLORLESS)
    missing = []
    for need in [value for value in needs if value != colorless]:
        if need in pool:
            pool.remove(need)
        else:
            missing.append(need)
    for _ in [value for value in needs if value == colorless]:
        if pool:
            pool.pop(0)
        else:
            missing.append(colorless)
    return tuple(missing)


def _normalized(text: str) -> str:
    return " ".join((text or "").lower().replace("pokémon", "pokemon").split())


def outcome_for_attack(
    parent: Any,
    attacker: Any,
    attack: Any,
    target: Any,
    *,
    hand_count: int,
) -> Outcome:
    line = lineage_key(target, getattr(target, "playerIndex", 0))
    if attack.attackId == POWERFUL_HAND:
        return Outcome(
            OutcomeKind.PLACE_COUNTERS,
            amount=max(0, 20 * hand_count),
            target_line=line,
            source_serial=getattr(attacker, "serial", None),
            details=(("required_hand", ceil(max(0, target.hp) / 20)),),
        )
    text = _normalized(getattr(attack, "text", ""))
    if "knock out" in text and "damage" not in text:
        return Outcome(
            OutcomeKind.DIRECT_KO,
            target_line=line,
            source_serial=getattr(attacker, "serial", None),
        )
    damage = getattr(attack, "damage", None)
    if isinstance(damage, int) and damage > 0:
        return Outcome(
            OutcomeKind.ATTACK_DAMAGE,
            amount=damage,
            target_line=line,
            source_serial=getattr(attacker, "serial", None),
        )
    if "damage counter" in text:
        return Outcome(
            OutcomeKind.PLACE_COUNTERS,
            target_line=line,
            source_serial=getattr(attacker, "serial", None),
            details=(("dynamic", True),),
        )
    if "switch this pokemon" in text:
        return Outcome(OutcomeKind.SELF_SWITCH, source_serial=attacker.serial)
    if "switch your opponent" in text:
        return Outcome(OutcomeKind.OPPONENT_SWITCH, source_serial=attacker.serial)
    if "draw " in text or "search your deck" in text:
        return Outcome(OutcomeKind.DRAW_SEARCH, source_serial=attacker.serial)
    if "heal" in text:
        return Outcome(OutcomeKind.HEAL, source_serial=attacker.serial)
    if "special condition" in text or any(word in text for word in ("poisoned", "burned", "confused", "asleep", "paralyzed")):
        return Outcome(OutcomeKind.STATUS, source_serial=attacker.serial)
    return Outcome(OutcomeKind.UNKNOWN, source_serial=attacker.serial)


def resolve_public_outcome(
    parent: Any,
    state: Any,
    attacker: Any,
    target: Any,
    outcome: Outcome,
    *,
    target_is_bench: bool = False,
) -> Outcome:
    """Resolve only the prevention layers belonging to the typed outcome."""
    target_data = parent.card_table.get(getattr(target, "id", None))
    attacker_data = parent.card_table.get(getattr(attacker, "id", None))
    if target_data is None or attacker_data is None:
        return Outcome(OutcomeKind.UNKNOWN, target_line=outcome.target_line)
    if outcome.kind is OutcomeKind.PLACE_COUNTERS:
        if any(card.id == MIST_ENERGY for card in (target.energyCards or [])):
            return Outcome(**{**outcome.__dict__, "prevented": True})
        if target_is_bench and any(card.id == BATTLE_CAGE for card in state.stadium):
            return Outcome(**{**outcome.__dict__, "prevented": True})
        return outcome
    if outcome.kind is not OutcomeKind.ATTACK_DAMAGE:
        return outcome
    amount = outcome.amount
    attack_type = _int(attacker_data.energyType)
    if _int(target_data.weakness) == attack_type:
        amount *= 2
    if _int(target_data.resistance) == attack_type:
        amount = max(0, amount - 30)
    if target_is_bench:
        owner = getattr(target, "playerIndex", None)
        field = state.players[owner] if owner in (0, 1) else None
        if field is not None and any(p.id == SHAYMIN for p in list(field.active) + list(field.bench)):
            if not target_data.ex and not target_data.megaEx:
                return Outcome(**{**outcome.__dict__, "amount": 0, "prevented": True})
    if target_data.energyType == parent.EnergyType.METAL and any(card.id == 1244 for card in state.stadium):
        amount = max(0, amount - 30)
    return Outcome(**{**outcome.__dict__, "amount": amount})


def attack_certificates(parent: Any, obs: Any, pokemon: Any, target: Any) -> tuple[AttackCertificate, ...]:
    owner = getattr(pokemon, "playerIndex", obs.current.yourIndex)
    line = lineage_key(pokemon, owner)
    data = parent.card_table.get(getattr(pokemon, "id", None))
    available = energy_units(parent, pokemon)
    if line is None or data is None or available is None:
        return ()
    certificates = []
    hand_count = obs.current.players[owner].handCount
    for attack_id in data.attacks or []:
        attack = parent.attack_table.get(attack_id)
        if attack is None:
            continue
        missing = missing_energy(parent, available, attack.energies)
        outcome = outcome_for_attack(parent, pokemon, attack, target, hand_count=hand_count)
        outcome = resolve_public_outcome(parent, obs.current, pokemon, target, outcome)
        certificates.append(
            AttackCertificate(line, pokemon.serial, attack_id, outcome, missing, not missing)
        )
    return tuple(certificates)


def best_ready_attack(parent: Any, obs: Any, pokemon: Any, target: Any) -> AttackCertificate | None:
    ready = [certificate for certificate in attack_certificates(parent, obs, pokemon, target) if certificate.legal_now]
    if not ready:
        return None
    kind_order = {
        OutcomeKind.DIRECT_KO: 3,
        OutcomeKind.PLACE_COUNTERS: 2,
        OutcomeKind.ATTACK_DAMAGE: 1,
    }
    return max(
        ready,
        key=lambda certificate: (
            kind_order.get(certificate.outcome.kind, 0),
            certificate.outcome.amount,
            -certificate.attack_id,
        ),
    )


def public_roles(parent: Any, obs: Any) -> RoleCertificate:
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    theirs = obs.current.players[1 - owner]
    target = theirs.active[0] if theirs.active else None
    if target is None:
        return RoleCertificate(None, None, None, ResourceLedger())
    ledger = ResourceLedger()
    candidates = []
    for position, pokemon in enumerate(list(mine.active) + list(mine.bench)):
        certificate = best_ready_attack(parent, obs, pokemon, target)
        if certificate is not None:
            candidates.append((position, certificate, pokemon))
    H0 = candidates[0][1] if candidates and candidates[0][0] == 0 else None
    successors = [row for row in candidates if H0 is None or row[1].line != H0.line]
    H1 = successors[0][1] if successors else None
    H2 = successors[1][1] if len(successors) > 1 else None
    for role, certificate in ((BaseRole.H0, H0), (BaseRole.H1, H1), (BaseRole.H2, H2)):
        if certificate is None:
            continue
        updated = ledger.assign_role(certificate.line, role)
        if updated is None:
            return RoleCertificate(None, None, None, ResourceLedger())
        ledger = updated
        pokemon = next(
            p for p in list(mine.active) + list(mine.bench)
            if lineage_key(p, owner) == certificate.line
        )
        for card in pokemon.energyCards or []:
            updated = ledger.reserve(f"energy:{card.serial}", role, f"pay attack {certificate.attack_id}")
            if updated is None:
                return RoleCertificate(None, None, None, ResourceLedger())
            ledger = updated
    return RoleCertificate(H0, H1, H2, ledger)


def has_psychic_telepath_target(parent: Any, obs: Any) -> bool:
    owner = obs.current.yourIndex
    for pokemon in list(obs.current.players[owner].active) + list(obs.current.players[owner].bench):
        data = parent.card_table.get(pokemon.id)
        if data is not None and data.energyType == parent.EnergyType.PSYCHIC:
            return True
    return False


def public_positive_attack_response(parent: Any, obs: Any) -> bool:
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    theirs = obs.current.players[1 - owner]
    if not mine.active:
        return False
    target = mine.active[0]
    for pokemon in theirs.active:
        for certificate in attack_certificates(parent, obs, pokemon, target):
            if certificate.legal_now and certificate.outcome.positive_attack_damage:
                return True
    return False


def ordered_draw_clock(parent: Any, obs: Any) -> DrawClock:
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    theirs = obs.current.players[1 - owner]
    own = DeckClock(mine.deckCount)
    opponent = DeckClock(theirs.deckCount)
    # The ordering is explicit even when a branch has zero currently selected draws.
    for name, count, optional in (
        ("current_optional_draw_or_search", 0, True),
        ("opponent_turn_helmet_or_fan", 0, True),
        ("next_mandatory_draw", 1, False),
        ("H1_or_recovery", 0, True),
        ("next_opponent_turn", 0, False),
        ("H2_mandatory_draw", 1, False),
    ):
        own = own.after(name, count, optional) or own
    return DrawClock(own, opponent)


def enriching_four_draw_is_safe(parent: Any, obs: Any, *, search_removes: int = 1) -> bool:
    deck = obs.current.players[obs.current.yourIndex].deckCount
    clock = DeckClock(deck)
    after_search = clock.after("Hilda search", search_removes, False)
    after_enriching = after_search.after("Enriching mandatory four", 4, False) if after_search else None
    after_next = after_enriching.after("next mandatory draw", 1, False) if after_enriching else None
    after_h2 = after_next.after("H2 mandatory draw", 1, False) if after_next else None
    return after_h2 is not None and after_h2.deck_count >= 0


def run_away_draw_is_safe(obs: Any) -> bool:
    deck = obs.current.players[obs.current.yourIndex].deckCount
    # Draw first; shuffling the source occurs only if at least one card resolves.
    return deck >= 1 and deck - min(3, deck) >= 1


def public_clocks(parent: Any, obs: Any, roles: RoleCertificate):
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    theirs = obs.current.players[1 - owner]
    own_attacks = sum(certificate is not None for certificate in (roles.H0, roles.H1, roles.H2))
    return {
        "own_prize": PrizeClock(len(mine.prize), own_attacks or None),
        "opponent_prize": PrizeClock(len(theirs.prize), None),
        "own_board": BoardClock(len(mine.active) + len(mine.bench), len(mine.active) + len(mine.bench)),
        "opponent_board": BoardClock(len(theirs.active) + len(theirs.bench), len(theirs.active) + len(theirs.bench)),
        "draw": ordered_draw_clock(parent, obs),
    }


def bench_liability(parent: Any, obs: Any, pokemon: Any, role: BaseRole) -> tuple[int, int, int, int, int]:
    prizes = prize_value(parent, pokemon)
    if prizes is None:
        return (999, 999, 999, 999, 999)
    owner = obs.current.yourIndex
    theirs = obs.current.players[1 - owner]
    visible_spread = 0
    visible_snipe = 0
    for attacker in list(theirs.active) + list(theirs.bench):
        data = parent.card_table.get(attacker.id)
        for attack_id in (data.attacks if data is not None else []):
            attack = parent.attack_table.get(attack_id)
            text = _normalized(getattr(attack, "text", "")) if attack is not None else ""
            visible_spread += int("benched pokemon" in text and "damage" in text)
            visible_snipe += int("1 of your opponent's pokemon" in text)
    escape = getattr(parent.card_table.get(pokemon.id), "retreatCost", 99)
    effect = 1 if role in (BaseRole.H0, BaseRole.H1, BaseRole.H2, BaseRole.ENGINE, BaseRole.PIVOT) else 0
    return (prizes, visible_spread, visible_snipe, escape, -effect)


def recovery_restores_named_route(parent: Any, obs: Any, card_id: int) -> bool:
    roles = public_roles(parent, obs)
    if roles.H1 is not None and roles.H2 is not None:
        return False
    mine = obs.current.players[obs.current.yourIndex]
    discard_ids = [card.id for card in mine.discard]
    if card_id == NIGHT_STRETCHER:
        return any(card_id in {parent.Abra, parent.Kadabra, parent.Alakazam, BASIC_PSYCHIC} for card_id in discard_ids)
    if card_id == SACRED_ASH:
        return any(card_id in {parent.Abra, parent.Kadabra, parent.Alakazam} for card_id in discard_ids)
    return False


def enhanced_hammer_changes_response(parent: Any, obs: Any) -> bool:
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    theirs = obs.current.players[1 - owner]
    target = mine.active[0] if mine.active else None
    if target is None:
        return False
    for opponent in list(theirs.active) + list(theirs.bench):
        before = best_ready_attack(parent, obs, opponent, target)
        if before is None:
            continue
        for index, card in enumerate(opponent.energyCards or []):
            data = parent.card_table.get(card.id)
            if data is None or data.cardType != parent.CardType.SPECIAL_ENERGY:
                continue
            available = list(energy_units(parent, opponent) or ())
            if index < len(available):
                del available[index]
            attack = parent.attack_table.get(before.attack_id)
            if attack is not None and missing_energy(parent, tuple(available), attack.energies):
                return True
            if card.id in (MIST_ENERGY,):
                return True
    return False


def boss_is_eligible(
    *,
    immediate_win: bool,
    active_prizes: int,
    target_prizes: int,
    active_lethal: bool,
    strictly_fewer_attacks: bool,
    exact_damaged_recovery: bool,
    sole_public_engine_denial: bool,
    certifies_continuity: bool,
) -> bool:
    if immediate_win:
        return True
    if active_lethal and active_prizes > target_prizes:
        return False
    return any((strictly_fewer_attacks, exact_damaged_recovery, sole_public_engine_denial, certifies_continuity))


def enumerate_prize_lanes(parent: Any, obs: Any, roles: RoleCertificate) -> tuple[PrizeLane, ...]:
    """Enumerate visible routes through at most three KOs; hidden access is never assumed."""
    owner = obs.current.yourIndex
    theirs = obs.current.players[1 - owner]
    attackers = [certificate for certificate in (roles.H0, roles.H1, roles.H2) if certificate is not None]
    if not attackers or not theirs.active:
        return ()
    visible = list(theirs.active) + list(theirs.bench)
    lanes = []
    for length in range(1, min(3, len(visible), len(attackers)) + 1):
        for targets in permutations(visible, length):
            steps = []
            certified = True
            for index, (target, attacker) in enumerate(zip(targets, attackers)):
                prizes = prize_value(parent, target)
                if prizes is None:
                    certified = False
                    break
                outcome = attacker.outcome
                amount = outcome.amount
                if outcome.kind is OutcomeKind.DIRECT_KO:
                    hits = 1
                elif amount > 0:
                    hits = ceil(max(1, target.hp) / amount)
                else:
                    certified = False
                    break
                boss = index > 0 or target is not theirs.active[0]
                # Future access is certified only by an exact visible Boss copy.
                if boss and not any(card.id == BOSS_ORDERS for card in (obs.current.players[owner].hand or [])):
                    certified = False
                    break
                role = (BaseRole.H0, BaseRole.H1, BaseRole.H2)[index]
                steps.append(
                    PrizeLaneStep(
                        lineage_key(target, 1 - owner), target.serial, prizes, role,
                        outcome, hits, obs.current.players[owner].handCount - int(boss),
                        boss, boss, (roles.H1 is not None, roles.H2 is not None),
                        (), None,
                    )
                )
            if steps:
                lanes.append(PrizeLane(tuple(steps), certified))
    return tuple(lanes)


def objective_for_state(parent: Any, obs: Any, roles: RoleCertificate, *, tie: tuple[Any, ...] = ()) -> PlanObjective:
    clocks = public_clocks(parent, obs, roles)
    mine = obs.current.players[obs.current.yourIndex]
    target = obs.current.players[1 - obs.current.yourIndex].active
    prizes_now = 0
    lethal = False
    if roles.H0 is not None and target:
        target_prizes = prize_value(parent, target[0]) or 0
        lethal = roles.H0.outcome.kind is OutcomeKind.DIRECT_KO or roles.H0.outcome.amount >= target[0].hp
        prizes_now = target_prizes if lethal else 0
    lanes = [lane for lane in enumerate_prize_lanes(parent, obs, roles) if lane.certified]
    shortest = min((lane.attacks for lane in lanes), default=999)
    return PlanObjective(
        win_now=lethal and prizes_now >= len(mine.prize),
        avoid_public_forced_loss=(clocks["own_board"].bodies > 1 or roles.H0 is not None),
        preserve_H0_lethal=lethal,
        prizes_now=prizes_now,
        preserve_H1_attack=roles.H1 is not None,
        preserve_H2_route=roles.H2 is not None,
        shorter_certified_prize_lane=-shortest,
        fewer_abandoned_reservations=-len(roles.ledger.reservations),
        safer_deck_clock=mine.deckCount,
        lower_bench_prize_liability=-sum(prize_value(parent, p) or 3 for p in mine.bench),
        stable_semantic_tie_break=tie,
    )
