"""Public-state model for the integrated Alakazam turn planner.

This module is deliberately independent from the cumulative policy.  It owns
the typed semantics, copy-on-write turn budget, exclusive resource ledger,
public snapshot and lexicographic plan records used by the final wrapper.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import json
from typing import Any, Iterable


INTEGRATED_VERSION = "integrated-domain-turn-planner-v1-20260722"


class OutcomeKind(str, Enum):
    ATTACK_DAMAGE = "AttackDamage"
    PLACE_COUNTERS = "PlaceCounters"
    DIRECT_KO = "DirectKO"
    DRAW_SEARCH = "Draw/Search"
    HEAL = "Heal"
    SELF_SWITCH = "SelfSwitch"
    OPPONENT_SWITCH = "OpponentSwitch"
    PROMOTION = "Promotion"
    MOVE_ENERGY = "MoveEnergy"
    RECOVERY = "Recovery"
    STATUS = "Status"
    UNKNOWN = "Unknown"


class BaseRole(str, Enum):
    H0 = "H0"
    H1 = "H1"
    H2 = "H2"
    PIVOT = "PIVOT"
    ENGINE = "ENGINE"
    RECOVERY = "RECOVERY"
    SACRIFICE = "SACRIFICE"
    LIABILITY = "LIABILITY"


@dataclass(frozen=True)
class Outcome:
    kind: OutcomeKind
    amount: int = 0
    target_line: tuple[int, int] | None = None
    source_serial: int | None = None
    prevented: bool = False
    details: tuple[tuple[str, Any], ...] = ()

    @property
    def positive_attack_damage(self) -> bool:
        return (
            self.kind is OutcomeKind.ATTACK_DAMAGE
            and self.amount > 0
            and not self.prevented
        )

    @property
    def triggers_attack_damage_tools(self) -> bool:
        """Lucky Helmet and Handheld Fan share this exact trigger gate."""
        return self.positive_attack_damage


@dataclass(frozen=True)
class TurnBudget:
    manual_attachment: bool
    supporter: bool
    stadium: bool
    retreat: bool
    attack: bool
    bench_slots: int
    tool_slots: tuple[tuple[tuple[int, int], int], ...]
    abilities: tuple[tuple[tuple[int, int], bool], ...]

    def spend(self, token: str, key: tuple[int, int] | None = None):
        """Return a spent child budget, or None on an overspend."""
        scalar = {
            "manual_attachment": "manual_attachment",
            "supporter": "supporter",
            "stadium": "stadium",
            "retreat": "retreat",
            "attack": "attack",
        }
        if token in scalar:
            field = scalar[token]
            if not getattr(self, field):
                return None
            return replace(self, **{field: False})
        if token == "bench_slot":
            if self.bench_slots <= 0:
                return None
            return replace(self, bench_slots=self.bench_slots - 1)
        if token == "tool_slot":
            slots = dict(self.tool_slots)
            if key is None or slots.get(key, 0) <= 0:
                return None
            slots[key] -= 1
            return replace(self, tool_slots=tuple(sorted(slots.items())))
        if token == "ability":
            abilities = dict(self.abilities)
            if key is None or abilities.get(key) is not True:
                return None
            abilities[key] = False
            return replace(self, abilities=tuple(sorted(abilities.items())))
        return None


@dataclass(frozen=True)
class Reservation:
    token: str
    role: BaseRole
    purpose: str
    branches: frozenset[str]


@dataclass(frozen=True)
class ResourceLedger:
    reservations: tuple[Reservation, ...] = ()
    roles: tuple[tuple[tuple[int, int], BaseRole], ...] = ()

    def assign_role(self, line: tuple[int, int], role: BaseRole):
        roles = dict(self.roles)
        if line in roles and roles[line] is not role:
            return None
        roles[line] = role
        return replace(self, roles=tuple(sorted(roles.items())))

    def reserve(
        self,
        token: str,
        role: BaseRole,
        purpose: str,
        branches: Iterable[str] = ("main",),
    ):
        branch_set = frozenset(branches)
        if not branch_set:
            return None
        for existing in self.reservations:
            if existing.token != token:
                continue
            # Physical reuse is legal only across provably disjoint branches.
            if existing.branches & branch_set:
                return None
        return replace(
            self,
            reservations=self.reservations
            + (Reservation(token, role, purpose, branch_set),),
        )


@dataclass(frozen=True)
class PrizeClock:
    remaining: int
    certified_attacks: int | None


@dataclass(frozen=True)
class BoardClock:
    bodies: int
    public_knockouts_to_loss: int | None


@dataclass(frozen=True)
class DeckClock:
    deck_count: int
    ordered_draws: tuple[tuple[str, int, bool], ...] = ()

    def after(self, name: str, count: int, optional: bool = False):
        if count < 0:
            return None
        return replace(
            self,
            deck_count=self.deck_count - count,
            ordered_draws=self.ordered_draws + ((name, count, optional),),
        )

    def can_resolve(self, count: int) -> bool:
        return count >= 0 and self.deck_count >= count

    def safe_before_next_mandatory(self, count: int) -> bool:
        # Deck zero is legal until the next mandatory draw cannot resolve.
        return count >= 0 and self.deck_count - count >= 1


@dataclass(frozen=True)
class DrawClock:
    own: DeckClock
    opponent: DeckClock


@dataclass(frozen=True)
class PrizeLaneStep:
    target_line: tuple[int, int]
    target_serial: int
    prizes: int
    attacker_role: BaseRole
    outcome: Outcome
    hits: int
    post_spend_hand_floor: int
    boss_required: bool
    supporter_required: bool
    continuity: tuple[bool, bool]
    visible_response: tuple[Any, ...]
    opponent_clock: int | None


@dataclass(frozen=True)
class PrizeLane:
    steps: tuple[PrizeLaneStep, ...] = ()
    certified: bool = False

    @property
    def attacks(self) -> int:
        return sum(step.hits for step in self.steps)


@dataclass(frozen=True)
class PlanObjective:
    win_now: bool = False
    avoid_public_forced_loss: bool = False
    preserve_H0_lethal: bool = False
    prizes_now: int = 0
    preserve_H1_attack: bool = False
    preserve_H2_route: bool = False
    shorter_certified_prize_lane: int = 0
    fewer_abandoned_reservations: int = 0
    safer_deck_clock: int = 0
    lower_bench_prize_liability: int = 0
    stable_semantic_tie_break: tuple[Any, ...] = ()

    def vector(self) -> tuple[Any, ...]:
        """The frozen objective order; no weighted sum is permitted."""
        return (
            self.win_now,
            self.avoid_public_forced_loss,
            self.preserve_H0_lethal,
            self.prizes_now,
            self.preserve_H1_attack,
            self.preserve_H2_route,
            self.shorter_certified_prize_lane,
            self.fewer_abandoned_reservations,
            self.safer_deck_clock,
            self.lower_bench_prize_liability,
            self.stable_semantic_tie_break,
        )


@dataclass(frozen=True)
class PlanStep:
    stage: str
    option_keys: tuple[tuple[Any, ...], ...]
    expected_context: int | None
    expected_delta: tuple[tuple[str, Any], ...] = ()


@dataclass(frozen=True)
class IntegratedTurnPlan:
    plan_id: str
    snapshot_hash: str
    objective: PlanObjective
    fallback: tuple[int, ...]
    H0: tuple[int, int] | None
    H1: tuple[int, int] | None
    H2: tuple[int, int] | None
    turn_budget: TurnBudget
    resource_ledger: ResourceLedger
    prize_lane: PrizeLane
    draw_clock: DrawClock
    ordered_plan_steps: tuple[PlanStep, ...]
    expected_stage: str
    allowed_option_keys: tuple[tuple[Any, ...], ...]
    abort_predicates: tuple[str, ...]
    metadata: tuple[tuple[str, Any], ...] = ()


@dataclass(frozen=True)
class PublicSnapshot:
    payload: dict[str, Any]
    canonical_json: str
    sha256: str


OPTION_FIELDS = (
    "type",
    "number",
    "area",
    "index",
    "playerIndex",
    "toolIndex",
    "energyIndex",
    "count",
    "inPlayArea",
    "inPlayIndex",
    "attackId",
    "cardId",
    "serial",
    "specialConditionType",
)


def enum_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def card_row(card: Any) -> tuple[int, int, int] | None:
    if card is None:
        return None
    card_id = getattr(card, "id", None)
    serial = getattr(card, "serial", None)
    owner = getattr(card, "playerIndex", None)
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in (card_id, serial, owner)):
        return None
    if card_id <= 0 or serial <= 0 or owner not in (0, 1):
        return None
    return (card_id, serial, owner)


def lineage_key(pokemon: Any, owner: int) -> tuple[int, int] | None:
    if pokemon is None or getattr(pokemon, "playerIndex", owner) != owner:
        return None
    lineage = list(getattr(pokemon, "preEvolution", None) or [])
    root = lineage[0] if lineage else pokemon
    root_serial = getattr(root, "serial", None)
    top_serial = getattr(pokemon, "serial", None)
    if not isinstance(root_serial, int) or root_serial <= 0:
        return None
    if not isinstance(top_serial, int) or top_serial <= 0:
        return None
    return (owner, root_serial)


def pokemon_row(pokemon: Any, owner: int) -> tuple[Any, ...] | None:
    line = lineage_key(pokemon, owner)
    top = card_row(pokemon)
    if line is None or top is None:
        return None
    energy_cards = tuple(sorted(filter(None, (card_row(c) for c in (getattr(pokemon, "energyCards", None) or []))), key=lambda row: row[1]))
    tools = tuple(sorted(filter(None, (card_row(c) for c in (getattr(pokemon, "tools", None) or []))), key=lambda row: row[1]))
    lineage = tuple(card_row(c) for c in (getattr(pokemon, "preEvolution", None) or []))
    if any(row is None for row in lineage):
        return None
    return (
        line,
        top,
        getattr(pokemon, "hp", None),
        getattr(pokemon, "maxHp", None),
        bool(getattr(pokemon, "appearThisTurn", False)),
        tuple(sorted(enum_int(v) for v in (getattr(pokemon, "energies", None) or []))),
        energy_cards,
        tools,
        lineage,
    )


def _zone_rows(cards: Iterable[Any] | None) -> tuple[tuple[int, int, int], ...] | None:
    rows = tuple(card_row(card) for card in (cards or []))
    if any(row is None for row in rows):
        return None
    return tuple(sorted(rows, key=lambda row: row[1]))


def _pokemon_for_area(parent: Any, obs: Any, area: Any, index: Any, player: int):
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        return None
    state = obs.current.players[player]
    if area == parent.AreaType.ACTIVE:
        zone = state.active
    elif area == parent.AreaType.BENCH:
        zone = state.bench
    else:
        return None
    return zone[index] if index < len(zone) else None


def _option_card(parent: Any, obs: Any, option: Any):
    area = getattr(option, "area", None)
    index = getattr(option, "index", None)
    player = getattr(option, "playerIndex", None)
    if player not in (0, 1):
        player = obs.current.yourIndex
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        return None
    if area == parent.AreaType.DECK:
        zone = obs.select.deck or []
    elif area == parent.AreaType.LOOKING:
        zone = obs.current.looking or []
    else:
        state = obs.current.players[player]
        zones = {
            parent.AreaType.HAND: state.hand or [],
            parent.AreaType.DISCARD: state.discard,
            parent.AreaType.ACTIVE: state.active,
            parent.AreaType.BENCH: state.bench,
            parent.AreaType.PRIZE: state.prize,
            parent.AreaType.STADIUM: obs.current.stadium,
        }
        zone = zones.get(area, [])
    return zone[index] if index < len(zone) else None


def stable_option_key(parent: Any, obs: Any, option: Any) -> tuple[Any, ...]:
    """Full public semantic option identity, including attached-card indices."""
    raw = tuple(enum_int(getattr(option, field, None)) for field in OPTION_FIELDS)
    source = card_row(_option_card(parent, obs, option))
    owner = getattr(option, "playerIndex", None)
    if owner not in (0, 1):
        owner = obs.current.yourIndex
    target = _pokemon_for_area(
        parent,
        obs,
        getattr(option, "inPlayArea", None),
        getattr(option, "inPlayIndex", None),
        owner,
    )
    target_line = lineage_key(target, owner)
    attached_serial = None
    attached_area = getattr(option, "area", None)
    attached_index = getattr(option, "index", None)
    attached_pokemon = _pokemon_for_area(parent, obs, attached_area, attached_index, owner)
    if attached_pokemon is not None:
        if getattr(option, "energyIndex", None) is not None:
            cards = getattr(attached_pokemon, "energyCards", None) or []
            idx = getattr(option, "energyIndex", None)
            if isinstance(idx, int) and 0 <= idx < len(cards):
                attached_serial = getattr(cards[idx], "serial", None)
        elif getattr(option, "toolIndex", None) is not None:
            cards = getattr(attached_pokemon, "tools", None) or []
            idx = getattr(option, "toolIndex", None)
            if isinstance(idx, int) and 0 <= idx < len(cards):
                attached_serial = getattr(cards[idx], "serial", None)
    return raw + (source, target_line, attached_serial)


def option_map(parent: Any, obs: Any) -> dict[tuple[Any, ...], list[int]]:
    result: dict[tuple[Any, ...], list[int]] = {}
    for index, option in enumerate(obs.select.option):
        result.setdefault(stable_option_key(parent, obs, option), []).append(index)
    return result


def rebind_option_keys(parent: Any, obs: Any, keys: Iterable[tuple[Any, ...]]):
    mapping = option_map(parent, obs)
    action = []
    for key in keys:
        matches = mapping.get(key, [])
        if len(matches) != 1:
            return None
        action.append(matches[0])
    return action


def action_is_valid(obs: Any, action: Any) -> bool:
    if not isinstance(action, list):
        return False
    if len(action) < obs.select.minCount or len(action) > obs.select.maxCount:
        return False
    if len(set(action)) != len(action):
        return False
    return all(
        isinstance(index, int)
        and not isinstance(index, bool)
        and 0 <= index < len(obs.select.option)
        for index in action
    )


def _log_row(log: Any) -> tuple[tuple[str, Any], ...]:
    fields = []
    for key, value in sorted(vars(log).items()):
        if value is None:
            continue
        fields.append((key, enum_int(value) if isinstance(value, Enum) else value))
    return tuple(fields)


def public_snapshot(parent: Any, obs: Any) -> PublicSnapshot | None:
    state = obs.current
    if state is None or obs.select is None or len(state.players) != 2:
        return None
    owner = state.yourIndex
    if owner not in (0, 1):
        return None
    players = []
    for index, player in enumerate(state.players):
        active = tuple(pokemon_row(p, index) for p in player.active)
        bench = tuple(pokemon_row(p, index) for p in player.bench)
        discard = _zone_rows(player.discard)
        lost = _zone_rows(getattr(player, "lost", None) or [])
        if any(row is None for row in active + bench) or discard is None or lost is None:
            return None
        row = {
            "index": index,
            "active": active,
            "bench": bench,
            "discard": discard,
            "lost": lost,
            "prize_count": len(player.prize),
            "hand_count": player.handCount,
            "deck_count": player.deckCount,
            "bench_max": player.benchMax,
            "status": (
                bool(player.poisoned), bool(player.burned), bool(player.asleep),
                bool(player.paralyzed), bool(player.confused),
            ),
        }
        # Exact own hand is public to the agent; opponent contents never enter.
        if index == owner:
            hand = _zone_rows(player.hand)
            if hand is None or len(hand) != player.handCount:
                return None
            row["hand"] = hand
        players.append(row)
    stadium = _zone_rows(state.stadium)
    if stadium is None:
        return None
    effect = card_row(obs.select.effect)
    context_card = card_row(obs.select.contextCard)
    option_keys = tuple(sorted((stable_option_key(parent, obs, option) for option in obs.select.option), key=repr))
    payload = {
        "version": INTEGRATED_VERSION,
        "turn": state.turn,
        "player": owner,
        "first_player": state.firstPlayer,
        "action_count": state.turnActionCount,
        "result": state.result,
        "energy_attached": bool(state.energyAttached),
        "supporter_played": bool(state.supporterPlayed),
        "stadium_played": bool(state.stadiumPlayed),
        "retreated": bool(state.retreated),
        "players": players,
        "stadium": stadium,
        "looking_count": len(state.looking or []),
        "select": {
            "type": enum_int(obs.select.type),
            "context": enum_int(obs.select.context),
            "min": obs.select.minCount,
            "max": obs.select.maxCount,
            "remaining_damage": obs.select.remainDamageCounter,
            "remaining_energy": obs.select.remainEnergyCost,
            "effect": effect,
            "context_card": context_card,
            "options": option_keys,
        },
        "logs": tuple(_log_row(log) for log in obs.logs),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest().upper()
    return PublicSnapshot(payload, canonical, digest)


def build_turn_budget(parent: Any, obs: Any, ability_flags: dict[str, bool]) -> TurnBudget:
    owner = obs.current.yourIndex
    mine = obs.current.players[owner]
    tool_slots = []
    abilities = []
    for pokemon in list(mine.active) + list(mine.bench):
        line = lineage_key(pokemon, owner)
        if line is None:
            continue
        tool_slots.append((line, 0 if getattr(pokemon, "tools", None) else 1))
        data = parent.card_table.get(pokemon.id)
        exposed = bool(data is not None and (data.skills or []))
        used = False
        if pokemon.id == getattr(parent, "Dudunsparce", -1):
            used = ability_flags.get("dudunsparce", False)
        elif pokemon.id == getattr(parent, "Fezandipiti_ex", -1):
            used = ability_flags.get("fezandipiti", False)
        abilities.append((line, exposed and not used))
    return TurnBudget(
        manual_attachment=not bool(obs.current.energyAttached),
        supporter=not bool(obs.current.supporterPlayed),
        stadium=not bool(obs.current.stadiumPlayed),
        retreat=not bool(obs.current.retreated),
        attack=obs.current.result == -1,
        bench_slots=max(0, mine.benchMax - len(mine.bench)),
        tool_slots=tuple(sorted(tool_slots)),
        abilities=tuple(sorted(abilities)),
    )
