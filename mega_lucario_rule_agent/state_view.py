"""Engine-independent public-state normalization and semantic option binding.

The competition engine passes plain dictionaries to ``agent`` while local
tools often convert the same payload to ``cg.api`` dataclasses.  This module
accepts both representations and deliberately does not import ``cg`` so the
submission can be imported in a clean process before the native engine is
loaded.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field as dataclass_field
from enum import IntEnum
import hashlib
import json
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple


class AreaType(IntEnum):
    DECK = 1
    HAND = 2
    DISCARD = 3
    ACTIVE = 4
    BENCH = 5
    PRIZE = 6
    STADIUM = 7
    ENERGY = 8
    TOOL = 9
    PRE_EVOLUTION = 10
    PLAYER = 11
    LOOKING = 12


class OptionType(IntEnum):
    NUMBER = 0
    YES = 1
    NO = 2
    CARD = 3
    TOOL_CARD = 4
    ENERGY_CARD = 5
    ENERGY = 6
    PLAY = 7
    ATTACH = 8
    EVOLVE = 9
    ABILITY = 10
    DISCARD = 11
    RETREAT = 12
    ATTACK = 13
    END = 14
    SKILL = 15
    SPECIAL_CONDITION = 16


class SelectType(IntEnum):
    MAIN = 0
    CARD = 1
    ATTACHED_CARD = 2
    CARD_OR_ATTACHED_CARD = 3
    ENERGY = 4
    SKILL = 5
    ATTACK = 6
    EVOLVE = 7
    COUNT = 8
    YES_NO = 9
    SPECIAL_CONDITION = 10


class SelectContext(IntEnum):
    MAIN = 0
    SETUP_ACTIVE_POKEMON = 1
    SETUP_BENCH_POKEMON = 2
    SWITCH = 3
    TO_ACTIVE = 4
    TO_BENCH = 5
    TO_FIELD = 6
    TO_HAND = 7
    DISCARD = 8
    TO_DECK = 9
    TO_DECK_BOTTOM = 10
    TO_PRIZE = 11
    NOT_MOVE = 12
    DAMAGE_COUNTER = 13
    DAMAGE_COUNTER_ANY = 14
    DAMAGE = 15
    REMOVE_DAMAGE_COUNTER = 16
    HEAL = 17
    EVOLVES_FROM = 18
    EVOLVES_TO = 19
    DEVOLVE = 20
    ATTACH_FROM = 21
    ATTACH_TO = 22
    DETACH_FROM = 23
    LOOK = 24
    EFFECT_TARGET = 25
    DISCARD_ENERGY_CARD = 26
    DISCARD_TOOL_CARD = 27
    SWITCH_ENERGY_CARD = 28
    DISCARD_CARD_OR_ATTACHED_CARD = 29
    DISCARD_ENERGY = 30
    TO_HAND_ENERGY = 31
    TO_DECK_ENERGY = 32
    SWITCH_ENERGY = 33
    SKILL_ORDER = 34
    ATTACK = 35
    DISABLE_ATTACK = 36
    EVOLVE = 37
    DRAW_COUNT = 38
    DAMAGE_COUNTER_COUNT = 39
    REMOVE_DAMAGE_COUNTER_COUNT = 40
    IS_FIRST = 41
    MULLIGAN = 42
    ACTIVATE = 43
    FIRST_EFFECT = 44
    MORE_DEVOLVE = 45
    COIN_HEAD = 46
    AFFECT_SPECIAL_CONDITION = 47
    RECOVER_SPECIAL_CONDITION = 48


class LogType(IntEnum):
    TURN_START = 2
    TURN_END = 3
    CHANGE = 9
    PLAY = 10
    EVOLVE = 12
    ATTACK = 15


def read_field(value: Any, name: str, default: Any = None) -> Any:
    """Read a field from either a mapping or a dataclass-like object."""

    if value is None:
        return default
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def as_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("public engine integer fields require an exact int")
    return int(value)


def as_bool(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError("public engine boolean fields require an exact bool")
    return value


def as_tuple(value: Any) -> Tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(value)
    return ()


def _optional_sort_int(value: Optional[int]) -> int:
    return -1 if value is None else int(value)


@dataclass(frozen=True)
class PhysicalRef:
    card_id: Optional[int]
    serial: Optional[int]
    owner: Optional[int]
    zone: Optional[int]
    lineage_serial: Optional[int] = None

    def sort_key(self) -> Tuple[int, int, int, int, int]:
        return (
            _optional_sort_int(self.owner),
            _optional_sort_int(self.zone),
            _optional_sort_int(self.card_id),
            _optional_sort_int(self.serial),
            _optional_sort_int(self.lineage_serial),
        )


@dataclass(frozen=True)
class PokemonView:
    ref: PhysicalRef
    hp: int
    max_hp: int
    appear_this_turn: bool
    energy_types: Tuple[int, ...]
    energy_refs: Tuple[PhysicalRef, ...]
    tool_refs: Tuple[PhysicalRef, ...]
    pre_evolution_refs: Tuple[PhysicalRef, ...]

    @property
    def remaining_hp(self) -> int:
        return max(0, self.hp)

    @property
    def damage(self) -> int:
        return max(0, self.max_hp - self.hp)

    @property
    def lineage_serial(self) -> Optional[int]:
        return self.ref.lineage_serial


@dataclass(frozen=True)
class PlayerView:
    index: int
    active: Tuple[PokemonView, ...]
    active_slot_count: int
    hidden_active_count: int
    bench: Tuple[PokemonView, ...]
    hand_refs: Tuple[PhysicalRef, ...]
    discard_refs: Tuple[PhysicalRef, ...]
    prize_refs: Tuple[PhysicalRef, ...]
    prize_count: int
    deck_count: int
    hand_count: int
    bench_max: int
    poisoned: bool
    burned: bool
    asleep: bool
    paralyzed: bool
    confused: bool


@dataclass(frozen=True)
class AttackHistoryEntry:
    owner: int
    lineage_serial: int
    attack_id: int
    turn: int

    def canonical(self) -> Tuple[int, int, int, int]:
        return self.owner, self.lineage_serial, self.attack_id, self.turn


@dataclass(frozen=True)
class PublicHistoryView:
    game_epoch: int
    last_attack_by_lineage: Tuple[AttackHistoryEntry, ...]
    attacked_this_turn: bool
    ppp_count: Optional[int]
    complete: bool


@dataclass(frozen=True)
class PublicState:
    game_epoch: int
    seat: int
    turn: int
    turn_action_count: int
    first_player: int
    supporter_played: bool
    stadium_played: bool
    energy_attached: bool
    retreated: bool
    result: int
    own: PlayerView
    opponent: PlayerView
    stadium_refs: Tuple[PhysicalRef, ...]
    looking_refs: Tuple[PhysicalRef, ...]
    select_context: Optional[int]
    min_count: int
    max_count: int
    effect_ref: Optional[PhysicalRef]
    context_ref: Optional[PhysicalRef]
    select_type: Optional[int] = None
    looking_open: bool = False
    select_deck_open: bool = False
    remaining_damage_counter: Optional[int] = None
    remaining_energy_cost: Optional[int] = None
    last_attack_by_lineage: Tuple[AttackHistoryEntry, ...] = ()
    attacked_this_turn: bool = False
    ppp_count: Optional[int] = None
    history_complete: bool = False

    @property
    def own_active(self) -> Optional[PokemonView]:
        return self.own.active[0] if self.own.active else None

    @property
    def opponent_active(self) -> Optional[PokemonView]:
        return self.opponent.active[0] if self.opponent.active else None


@dataclass(frozen=True)
class SemanticOptionKey:
    option_type: int
    player_index: Optional[int] = None
    card_id: Optional[int] = None
    card_serial: Optional[int] = None
    source_zone: Optional[int] = None
    source_index: Optional[int] = None
    source_lineage_serial: Optional[int] = None
    target_zone: Optional[int] = None
    target_lineage_serial: Optional[int] = None
    attack_id: Optional[int] = None
    energy_count: Optional[int] = None
    number: Optional[int] = None
    special_condition: Optional[int] = None
    relation: Optional[int] = None

    def sort_key(self) -> Tuple[int, ...]:
        return (
            int(self.option_type),
            _optional_sort_int(self.player_index),
            _optional_sort_int(self.card_id),
            _optional_sort_int(self.card_serial),
            _optional_sort_int(self.source_zone),
            _optional_sort_int(self.source_index),
            _optional_sort_int(self.source_lineage_serial),
            _optional_sort_int(self.target_zone),
            _optional_sort_int(self.target_lineage_serial),
            _optional_sort_int(self.attack_id),
            _optional_sort_int(self.energy_count),
            _optional_sort_int(self.number),
            _optional_sort_int(self.special_condition),
            _optional_sort_int(self.relation),
        )

    def canonical(self) -> Tuple[Optional[int], ...]:
        return (
            self.option_type,
            self.player_index,
            self.card_id,
            self.card_serial,
            self.source_zone,
            self.source_index,
            self.source_lineage_serial,
            self.target_zone,
            self.target_lineage_serial,
            self.attack_id,
            self.energy_count,
            self.number,
            self.special_condition,
            self.relation,
        )


@dataclass(frozen=True)
class SemanticOption:
    index: int
    key: SemanticOptionKey
    raw_option: Any = dataclass_field(compare=False, repr=False, default=None)


class SemanticBindError(ValueError):
    """Raised when a persisted semantic action does not bind uniquely."""


@dataclass(frozen=True)
class ActionSpec:
    choices: Tuple[SemanticOptionKey, ...]
    order_sensitive: bool = False

    @classmethod
    def single(cls, key: SemanticOptionKey) -> "ActionSpec":
        return cls((key,))

    @classmethod
    def empty(cls) -> "ActionSpec":
        return cls(())

    def canonical_choices(self) -> Tuple[Tuple[Optional[int], ...], ...]:
        ordered = (
            self.choices
            if self.order_sensitive
            else tuple(sorted(self.choices, key=lambda choice: choice.sort_key()))
        )
        return tuple(choice.canonical() for choice in ordered)

    def canonical(self) -> Tuple[Any, ...]:
        return bool(self.order_sensitive), self.canonical_choices()

    def bind(
        self,
        options: Sequence[SemanticOption],
        min_count: Optional[int] = None,
        max_count: Optional[int] = None,
    ) -> list[int]:
        by_key: Dict[SemanticOptionKey, list[int]] = {}
        for option in options:
            by_key.setdefault(option.key, []).append(option.index)

        rebound: list[int] = []
        for choice in self.choices:
            hits = by_key.get(choice, [])
            if len(hits) != 1:
                raise SemanticBindError(
                    "expected exactly one option for {0!r}; found {1}".format(choice, len(hits))
                )
            rebound.append(hits[0])

        if len(set(rebound)) != len(rebound):
            raise SemanticBindError("multiple semantic choices rebound to one option")
        if min_count is not None and len(rebound) < min_count:
            raise SemanticBindError("selection is below minCount")
        if max_count is not None and len(rebound) > max_count:
            raise SemanticBindError("selection exceeds maxCount")
        if not self.order_sensitive:
            rebound.sort()
        return rebound


@dataclass(frozen=True)
class PromptFingerprint:
    game_epoch: int
    owner_kind: str
    stage: str
    seat: int
    turn: int
    turn_action_count: int
    select_type: Optional[int]
    context: Optional[int]
    effect_ref: Optional[PhysicalRef]
    context_ref: Optional[PhysicalRef]
    effect_or_attack_id: Optional[int]
    min_count: int
    max_count: int
    semantic_option_multiset: Tuple[Tuple[SemanticOptionKey, int], ...]
    relevant_zone_fingerprint: str
    looking_open: bool
    select_deck_open: bool
    remaining_damage_counter: Optional[int]
    remaining_energy_cost: Optional[int]

    def digest(self) -> str:
        payload = {
            "game_epoch": self.game_epoch,
            "owner_kind": self.owner_kind,
            "stage": self.stage,
            "seat": self.seat,
            "turn": self.turn,
            "turn_action_count": self.turn_action_count,
            "select_type": self.select_type,
            "context": self.context,
            "effect_ref": None if self.effect_ref is None else self.effect_ref.sort_key(),
            "context_ref": None if self.context_ref is None else self.context_ref.sort_key(),
            "effect_or_attack_id": self.effect_or_attack_id,
            "min_count": self.min_count,
            "max_count": self.max_count,
            "semantic_option_multiset": [
                (key.canonical(), count) for key, count in self.semantic_option_multiset
            ],
            "relevant_zone_fingerprint": self.relevant_zone_fingerprint,
            "looking_open": self.looking_open,
            "select_deck_open": self.select_deck_open,
            "remaining_damage_counter": self.remaining_damage_counter,
            "remaining_energy_cost": self.remaining_energy_cost,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


def _card_ref(card: Any, owner: Optional[int], zone: Optional[int]) -> Optional[PhysicalRef]:
    if card is None:
        return None
    card_id = as_int(read_field(card, "id"))
    if card_id is None:
        card_id = as_int(read_field(card, "cardId"))
    serial = as_int(read_field(card, "serial"))
    actual_owner = as_int(read_field(card, "playerIndex"), owner)
    return PhysicalRef(card_id, serial, actual_owner, zone, serial)


def pokemon_lineage_serial(pokemon: Any) -> Optional[int]:
    pre_evolution = as_tuple(read_field(pokemon, "preEvolution", ()))
    if pre_evolution:
        base_serial = as_int(read_field(pre_evolution[0], "serial"))
        if base_serial is not None:
            return base_serial
    return as_int(read_field(pokemon, "serial"))


def _pokemon_view(pokemon: Any, owner: int, zone: int) -> Optional[PokemonView]:
    if pokemon is None:
        return None
    card_id = as_int(read_field(pokemon, "id"))
    serial = as_int(read_field(pokemon, "serial"))
    lineage = pokemon_lineage_serial(pokemon)
    ref = PhysicalRef(card_id, serial, owner, zone, lineage)
    energy_cards = as_tuple(read_field(pokemon, "energyCards", ()))
    tools = as_tuple(read_field(pokemon, "tools", ()))
    pre_evolution = as_tuple(read_field(pokemon, "preEvolution", ()))
    energy_refs = tuple(
        ref_value
        for ref_value in (_card_ref(card, owner, int(AreaType.ENERGY)) for card in energy_cards)
        if ref_value is not None
    )
    tool_refs = tuple(
        ref_value
        for ref_value in (_card_ref(card, owner, int(AreaType.TOOL)) for card in tools)
        if ref_value is not None
    )
    pre_refs = tuple(
        ref_value
        for ref_value in (
            _card_ref(card, owner, int(AreaType.PRE_EVOLUTION)) for card in pre_evolution
        )
        if ref_value is not None
    )
    return PokemonView(
        ref=ref,
        hp=as_int(read_field(pokemon, "hp"), 0) or 0,
        max_hp=as_int(read_field(pokemon, "maxHp"), 0) or 0,
        appear_this_turn=as_bool(read_field(pokemon, "appearThisTurn", False)),
        energy_types=tuple(
            as_int(value)
            for value in as_tuple(read_field(pokemon, "energies", ()))
        ),
        energy_refs=energy_refs,
        tool_refs=tool_refs,
        pre_evolution_refs=pre_refs,
    )


def _player_view(player: Any, index: int, include_private_hand: bool) -> PlayerView:
    active_slots = as_tuple(read_field(player, "active", ()))
    active = tuple(
        pokemon_view
        for pokemon_view in (
            _pokemon_view(pokemon, index, int(AreaType.ACTIVE))
            for pokemon in active_slots
        )
        if pokemon_view is not None
    )
    bench = tuple(
        pokemon_view
        for pokemon_view in (
            _pokemon_view(pokemon, index, int(AreaType.BENCH))
            for pokemon in as_tuple(read_field(player, "bench", ()))
        )
        if pokemon_view is not None
    )
    hand = as_tuple(read_field(player, "hand", ())) if include_private_hand else ()
    discard = as_tuple(read_field(player, "discard", ()))
    prize = as_tuple(read_field(player, "prize", ()))

    def refs(cards: Iterable[Any], zone: AreaType) -> Tuple[PhysicalRef, ...]:
        return tuple(
            sorted(
                (
                    ref_value
                    for ref_value in (_card_ref(card, index, int(zone)) for card in cards)
                    if ref_value is not None
                ),
                key=lambda value: value.sort_key(),
            )
        )

    prize_count = as_int(read_field(player, "prizeCount"), len(prize))
    bench_max = as_int(read_field(player, "benchMax"), 5)
    return PlayerView(
        index=index,
        active=active,
        active_slot_count=len(active_slots),
        hidden_active_count=sum(pokemon is None for pokemon in active_slots),
        bench=bench,
        hand_refs=refs(hand, AreaType.HAND),
        discard_refs=refs(discard, AreaType.DISCARD),
        prize_refs=refs(prize, AreaType.PRIZE),
        prize_count=len(prize) if prize_count is None else prize_count,
        deck_count=as_int(read_field(player, "deckCount"), 0) or 0,
        hand_count=as_int(
            read_field(player, "handCount"), len(hand) if include_private_hand else 0
        )
        or 0,
        bench_max=5 if bench_max is None else bench_max,
        poisoned=as_bool(read_field(player, "poisoned", False)),
        burned=as_bool(read_field(player, "burned", False)),
        asleep=as_bool(read_field(player, "asleep", False)),
        paralyzed=as_bool(read_field(player, "paralyzed", False)),
        confused=as_bool(read_field(player, "confused", False)),
    )


def _select_from_observation(observation: Any) -> Any:
    return read_field(observation, "select")


def _current_from_observation(observation: Any) -> Any:
    return read_field(observation, "current")


class PublicHistoryTracker:
    """Bounded public-log ledger for turn-scoped cards and lineage attack locks."""

    def __init__(self) -> None:
        self._game_epoch: Optional[int] = None
        self._complete = False
        self._seen_events: set[Tuple[int, ...]] = set()
        self._top_to_lineage: Dict[Tuple[int, int], int] = {}
        self._last_attack: Dict[Tuple[int, int], AttackHistoryEntry] = {}
        self._ppp_plays: Dict[Tuple[int, int], set[int]] = {}
        self._last_current_turn: Optional[int] = None

    def begin_game(self, game_epoch: int) -> None:
        epoch = as_int(game_epoch)
        if epoch is None or epoch < 0:
            raise ValueError("history game_epoch must be a nonnegative exact int")
        self._game_epoch = epoch
        self._complete = True
        self._seen_events = set()
        self._top_to_lineage = {}
        self._last_attack = {}
        self._ppp_plays = {}
        self._last_current_turn = None

    @staticmethod
    def _turn_actor(turn: int, first_player: int) -> Optional[int]:
        if turn < 1 or first_player not in (0, 1):
            return None
        return first_player if turn % 2 == 1 else 1 - first_player

    def _remember_board_lineages(self, current: Any) -> None:
        players = as_tuple(read_field(current, "players", ()))
        if len(players) != 2:
            self._complete = False
            return
        try:
            for owner, player in enumerate(players):
                for pokemon in (
                    as_tuple(read_field(player, "active", ()))
                    + as_tuple(read_field(player, "bench", ()))
                ):
                    if pokemon is None:
                        continue
                    serial = as_int(read_field(pokemon, "serial"))
                    lineage = pokemon_lineage_serial(pokemon)
                    if serial is None or lineage is None:
                        self._complete = False
                        continue
                    key = (owner, serial)
                    previous = self._top_to_lineage.get(key)
                    if previous is not None and previous != lineage:
                        self._complete = False
                        continue
                    self._top_to_lineage[key] = lineage
        except ValueError:
            self._complete = False

    def _event_turns(
        self,
        logs: Tuple[Any, ...],
        current_turn: int,
        first_player: int,
    ) -> Tuple[Tuple[Any, int], ...]:
        cursor = current_turn
        reversed_rows = []
        try:
            for entry in reversed(logs):
                log_type = as_int(read_field(entry, "type"))
                if log_type is None:
                    self._complete = False
                    continue
                event_turn = cursor
                if log_type in (int(LogType.TURN_START), int(LogType.TURN_END)):
                    actor = as_int(read_field(entry, "playerIndex"))
                    expected = self._turn_actor(cursor, first_player)
                    if actor != expected:
                        self._complete = False
                    if log_type == int(LogType.TURN_START):
                        if cursor <= 0:
                            self._complete = False
                        else:
                            cursor -= 1
                reversed_rows.append((entry, event_turn))
        except ValueError:
            self._complete = False
            return ()
        reversed_rows.reverse()
        return tuple(reversed_rows)

    def _ingest_event(self, entry: Any, event_turn: int) -> None:
        try:
            log_type = as_int(read_field(entry, "type"))
            owner = as_int(read_field(entry, "playerIndex"))
            if log_type is None or owner not in (0, 1) or event_turn < 0:
                return
            card_id = as_int(read_field(entry, "cardId"))
            serial = as_int(read_field(entry, "serial"))
            attack_id = as_int(read_field(entry, "attackId"))
            serial_target = as_int(read_field(entry, "serialTarget"))
        except ValueError:
            self._complete = False
            return

        if log_type == int(LogType.EVOLVE):
            if serial is None or serial_target is None:
                self._complete = False
                return
            lineage = self._top_to_lineage.get((owner, serial_target), serial_target)
            self._top_to_lineage[(owner, serial)] = lineage
            return

        if log_type == int(LogType.PLAY) and card_id == 1141:
            if serial is None:
                self._complete = False
                return
            event_key = (
                int(self._game_epoch or 0),
                event_turn,
                log_type,
                owner,
                card_id,
                serial,
            )
            if event_key in self._seen_events:
                return
            self._seen_events.add(event_key)
            self._ppp_plays.setdefault((event_turn, owner), set()).add(serial)
            return

        if log_type == int(LogType.ATTACK):
            if serial is None or attack_id is None or attack_id <= 0:
                self._complete = False
                return
            lineage = self._top_to_lineage.get((owner, serial))
            if lineage is None:
                self._complete = False
                return
            event_key = (
                int(self._game_epoch or 0),
                event_turn,
                log_type,
                owner,
                serial,
                attack_id,
            )
            if event_key in self._seen_events:
                return
            self._seen_events.add(event_key)
            self._last_attack[(owner, lineage)] = AttackHistoryEntry(
                owner=owner,
                lineage_serial=lineage,
                attack_id=attack_id,
                turn=event_turn,
            )

    def update(self, observation: Any, game_epoch: int) -> PublicHistoryView:
        epoch = as_int(game_epoch)
        if epoch is None or epoch < 0:
            raise ValueError("history game_epoch must be a nonnegative exact int")
        if self._game_epoch != epoch:
            self.begin_game(epoch)
        current = _current_from_observation(observation)
        if current is None:
            self._complete = False
            return self.snapshot(0, 0)
        try:
            turn = as_int(read_field(current, "turn"))
            seat = as_int(read_field(current, "yourIndex"))
            first_player = as_int(read_field(current, "firstPlayer"))
        except ValueError:
            self._complete = False
            return self.snapshot(0, 0)
        if turn is None or turn < 0 or seat not in (0, 1):
            self._complete = False
            return self.snapshot(0, 0)
        if self._last_current_turn is None and turn > 2:
            self._complete = False
        if self._last_current_turn is not None and turn < self._last_current_turn:
            self._complete = False
        self._last_current_turn = turn
        self._remember_board_lineages(current)
        raw_logs = read_field(observation, "logs", ())
        if not isinstance(raw_logs, Sequence) or isinstance(
            raw_logs,
            (str, bytes, bytearray),
        ):
            self._complete = False
            logs = ()
        else:
            logs = tuple(raw_logs)
        if logs and first_player not in (0, 1):
            self._complete = False
        else:
            for entry, event_turn in self._event_turns(logs, turn, first_player):
                self._ingest_event(entry, event_turn)
        return self.snapshot(seat, turn)

    def record_emitted_attack(self, state: PublicState, attack_id: int) -> None:
        if not isinstance(state, PublicState):
            raise ValueError("emitted attack requires a PublicState")
        if self._game_epoch != state.game_epoch:
            self.begin_game(state.game_epoch)
        attack = as_int(attack_id)
        active = state.own_active
        if attack is None or attack <= 0 or active is None:
            self._complete = False
            raise ValueError("emitted attack requires an active lineage and attack ID")
        lineage = active.lineage_serial
        if (
            lineage is None
            or not isinstance(active.ref.serial, int)
            or isinstance(active.ref.serial, bool)
            or active.ref.serial < 0
        ):
            self._complete = False
            raise ValueError("emitted attack active lineage is unknown")
        self._top_to_lineage[(state.seat, active.ref.serial)] = lineage
        self._last_attack[(state.seat, lineage)] = AttackHistoryEntry(
            owner=state.seat,
            lineage_serial=lineage,
            attack_id=attack,
            turn=state.turn,
        )

    def snapshot(self, seat: int, turn: int) -> PublicHistoryView:
        seat_value = as_int(seat)
        turn_value = as_int(turn)
        if seat_value not in (0, 1) or turn_value is None or turn_value < 0:
            raise ValueError("history snapshot requires exact seat and turn")
        entries = tuple(
            sorted(
                self._last_attack.values(),
                key=lambda entry: entry.canonical(),
            )
        )
        attacked = any(
            entry.owner == seat_value and entry.turn == turn_value
            for entry in entries
        )
        ppp_count = len(self._ppp_plays.get((turn_value, seat_value), set()))
        return PublicHistoryView(
            game_epoch=int(self._game_epoch or 0),
            last_attack_by_lineage=entries,
            attacked_this_turn=attacked,
            ppp_count=ppp_count if self._complete else None,
            complete=self._complete,
        )


def build_public_state(
    observation: Any,
    game_epoch: int = 0,
    history_tracker: Optional[PublicHistoryTracker] = None,
) -> PublicState:
    current = _current_from_observation(observation)
    if current is None:
        raise ValueError("observation.current is required for a decision")
    epoch_value = as_int(game_epoch)
    if epoch_value is None or epoch_value < 0:
        raise ValueError("game_epoch must be a nonnegative exact int")
    select = _select_from_observation(observation)
    seat_value = as_int(read_field(current, "yourIndex"), 0)
    seat = 0 if seat_value is None else seat_value
    if seat not in (0, 1):
        raise ValueError("observation.current.yourIndex must be 0 or 1")
    players = as_tuple(read_field(current, "players", ()))
    if len(players) != 2:
        raise ValueError("observation.current.players must contain exactly two players")
    own_hand_raw = read_field(players[seat], "hand")
    own_hand_count = as_int(read_field(players[seat], "handCount"))
    if (
        own_hand_raw is None
        or not isinstance(own_hand_raw, Sequence)
        or isinstance(own_hand_raw, (str, bytes, bytearray))
        or own_hand_count is None
        or own_hand_count != len(own_hand_raw)
    ):
        raise ValueError("own hand must be complete and match handCount")
    own = _player_view(players[seat], seat, include_private_hand=True)
    if len(own.hand_refs) != own.hand_count or any(
        ref_value.card_id is None
        or ref_value.serial is None
        or ref_value.owner != seat
        for ref_value in own.hand_refs
    ):
        raise ValueError("own hand cards require exact id, serial, and owner")
    opponent_index = 1 - seat
    opponent = _player_view(
        players[opponent_index], opponent_index, include_private_hand=False
    )
    stadium_refs = tuple(
        ref_value
        for ref_value in (
            _card_ref(card, None, int(AreaType.STADIUM))
            for card in as_tuple(read_field(current, "stadium", ()))
        )
        if ref_value is not None
    )
    raw_looking = read_field(current, "looking")
    looking_open = raw_looking is not None
    looking = as_tuple(raw_looking)
    looking_refs = tuple(
        ref_value
        for ref_value in (
            _card_ref(card, seat, int(AreaType.LOOKING)) for card in looking
        )
        if ref_value is not None
    )
    effect_ref = _card_ref(read_field(select, "effect"), seat, None)
    context_ref = _card_ref(read_field(select, "contextCard"), seat, None)
    first_player = as_int(read_field(current, "firstPlayer"), -1)
    result = as_int(read_field(current, "result"), -1)
    history = (
        PublicHistoryView(epoch_value, (), False, None, False)
        if history_tracker is None
        else history_tracker.update(observation, epoch_value)
    )
    return PublicState(
        game_epoch=epoch_value,
        seat=seat,
        turn=as_int(read_field(current, "turn"), 0) or 0,
        turn_action_count=as_int(read_field(current, "turnActionCount"), 0) or 0,
        first_player=-1 if first_player is None else first_player,
        supporter_played=as_bool(read_field(current, "supporterPlayed", False)),
        stadium_played=as_bool(read_field(current, "stadiumPlayed", False)),
        energy_attached=as_bool(read_field(current, "energyAttached", False)),
        retreated=as_bool(read_field(current, "retreated", False)),
        result=-1 if result is None else result,
        own=own,
        opponent=opponent,
        stadium_refs=stadium_refs,
        looking_refs=looking_refs,
        select_context=as_int(read_field(select, "context")),
        min_count=as_int(read_field(select, "minCount"), 0) or 0,
        max_count=as_int(read_field(select, "maxCount"), 0) or 0,
        effect_ref=effect_ref,
        context_ref=context_ref,
        select_type=as_int(read_field(select, "type")),
        looking_open=looking_open,
        select_deck_open=read_field(select, "deck") is not None,
        remaining_damage_counter=as_int(
            read_field(select, "remainDamageCounter")
        ),
        remaining_energy_cost=as_int(read_field(select, "remainEnergyCost")),
        last_attack_by_lineage=history.last_attack_by_lineage,
        attacked_this_turn=history.attacked_this_turn,
        ppp_count=history.ppp_count,
        history_complete=history.complete,
    )


def _raw_player(observation: Any, player_index: int) -> Any:
    current = _current_from_observation(observation)
    players = as_tuple(read_field(current, "players", ()))
    if player_index < 0 or player_index >= len(players):
        return None
    return players[player_index]


def _pokemon_at(observation: Any, player_index: int, area: Optional[int], index: int) -> Any:
    player = _raw_player(observation, player_index)
    if player is None:
        return None
    if area == int(AreaType.ACTIVE):
        zone = as_tuple(read_field(player, "active", ()))
    elif area == int(AreaType.BENCH):
        zone = as_tuple(read_field(player, "bench", ()))
    else:
        return None
    if index < 0 or index >= len(zone):
        return None
    return zone[index]


def _card_at(
    observation: Any,
    player_index: int,
    area: Optional[int],
    index: int,
) -> Any:
    select = _select_from_observation(observation)
    current = _current_from_observation(observation)
    player = _raw_player(observation, player_index)
    if area == int(AreaType.DECK):
        zone = as_tuple(read_field(select, "deck", ()))
    elif area == int(AreaType.LOOKING):
        zone = as_tuple(read_field(current, "looking", ()))
    elif area == int(AreaType.STADIUM):
        zone = as_tuple(read_field(current, "stadium", ()))
    elif player is None:
        return None
    elif area == int(AreaType.HAND):
        zone = as_tuple(read_field(player, "hand", ()))
    elif area == int(AreaType.DISCARD):
        zone = as_tuple(read_field(player, "discard", ()))
    elif area == int(AreaType.PRIZE):
        zone = as_tuple(read_field(player, "prize", ()))
    elif area in (int(AreaType.ACTIVE), int(AreaType.BENCH)):
        return _pokemon_at(observation, player_index, area, index)
    else:
        return None
    if index < 0 or index >= len(zone):
        return None
    return zone[index]


def _option_source_ref(observation: Any, option: Any, seat: int) -> Optional[PhysicalRef]:
    option_type = as_int(read_field(option, "type"), -1)
    player_index = as_int(read_field(option, "playerIndex"), seat)
    if player_index is None:
        player_index = seat
    area = as_int(read_field(option, "area"))
    if option_type == int(OptionType.PLAY) and area is None:
        area = int(AreaType.HAND)
    index = as_int(read_field(option, "index"), -1)
    if index is None:
        index = -1

    if option_type == int(OptionType.SKILL):
        expected_card_id = as_int(read_field(option, "cardId"))
        expected_serial = as_int(read_field(option, "serial"))
        if expected_serial is None or player_index not in (0, 1):
            return None
        player = _raw_player(observation, player_index)
        if player is None:
            return None
        matches = []
        for zone, pokemon_values in (
            (AreaType.ACTIVE, as_tuple(read_field(player, "active", ()))),
            (AreaType.BENCH, as_tuple(read_field(player, "bench", ()))),
        ):
            for pokemon in pokemon_values:
                if pokemon is None:
                    continue
                card_id = as_int(read_field(pokemon, "id"))
                serial = as_int(read_field(pokemon, "serial"))
                if serial != expected_serial:
                    continue
                if expected_card_id is not None and card_id != expected_card_id:
                    continue
                matches.append(
                    PhysicalRef(
                        card_id,
                        serial,
                        player_index,
                        int(zone),
                        pokemon_lineage_serial(pokemon),
                    )
                )
        return matches[0] if len(matches) == 1 else None
    if option_type in (int(OptionType.ENERGY_CARD), int(OptionType.ENERGY), int(OptionType.TOOL_CARD)):
        pokemon = _pokemon_at(observation, player_index, area, index)
        if pokemon is None:
            return None
        if option_type == int(OptionType.TOOL_CARD):
            attached = as_tuple(read_field(pokemon, "tools", ()))
            attached_index = as_int(read_field(option, "toolIndex"), -1)
            attached_zone = int(AreaType.TOOL)
        else:
            attached = as_tuple(read_field(pokemon, "energyCards", ()))
            attached_index = as_int(read_field(option, "energyIndex"), -1)
            attached_zone = int(AreaType.ENERGY)
        if attached_index is None or attached_index < 0 or attached_index >= len(attached):
            return None
        return _card_ref(attached[attached_index], player_index, attached_zone)

    card = _card_at(observation, player_index, area, index)
    ref_value = _card_ref(card, player_index, area)
    if card is not None and area in (int(AreaType.ACTIVE), int(AreaType.BENCH)):
        return PhysicalRef(
            as_int(read_field(card, "id")),
            as_int(read_field(card, "serial")),
            player_index,
            area,
            pokemon_lineage_serial(card),
        )
    return ref_value


def _option_target_ref(observation: Any, option: Any, seat: int) -> Optional[PhysicalRef]:
    target_area = as_int(read_field(option, "inPlayArea"))
    target_index = as_int(read_field(option, "inPlayIndex"), -1)
    if target_area is None or target_index is None or target_index < 0:
        return None
    target = _pokemon_at(observation, seat, target_area, target_index)
    if target is None:
        return None
    return PhysicalRef(
        as_int(read_field(target, "id")),
        as_int(read_field(target, "serial")),
        seat,
        target_area,
        pokemon_lineage_serial(target),
    )


def semantic_key_for_option(observation: Any, option: Any) -> SemanticOptionKey:
    current = _current_from_observation(observation)
    seat = as_int(read_field(current, "yourIndex"), 0) or 0
    option_type = as_int(read_field(option, "type"), -1)
    if option_type is None:
        option_type = -1
    source_ref = _option_source_ref(observation, option, seat)
    target_ref = _option_target_ref(observation, option, seat)
    player_index = as_int(read_field(option, "playerIndex"), seat)
    raw_source_zone = as_int(read_field(option, "area"))
    if option_type == int(OptionType.PLAY) and raw_source_zone is None:
        raw_source_zone = int(AreaType.HAND)
    if option_type == int(OptionType.SKILL) and source_ref is None:
        raise ValueError(
            "SKILL source must resolve to exactly one public in-play card"
        )
    source_zone = (
        source_ref.zone
        if source_ref is not None
        else raw_source_zone
    )
    raw_source_index = as_int(read_field(option, "index"))
    source_index = raw_source_index if source_ref is None and source_zone is not None else None
    source_lineage_serial = (
        source_ref.lineage_serial
        if source_ref is not None
        and source_zone in (int(AreaType.ACTIVE), int(AreaType.BENCH))
        else None
    )
    target_zone = as_int(read_field(option, "inPlayArea"))
    raw_relation = as_int(read_field(option, "inPlayIndex"))
    relation = raw_relation if target_ref is None else None
    return SemanticOptionKey(
        option_type=option_type,
        player_index=player_index,
        card_id=None if source_ref is None else source_ref.card_id,
        card_serial=None if source_ref is None else source_ref.serial,
        source_zone=source_zone,
        source_index=source_index,
        source_lineage_serial=source_lineage_serial,
        target_zone=target_zone,
        target_lineage_serial=None if target_ref is None else target_ref.lineage_serial,
        attack_id=as_int(read_field(option, "attackId")),
        energy_count=as_int(read_field(option, "count")),
        number=as_int(read_field(option, "number")),
        special_condition=as_int(read_field(option, "specialConditionType")),
        relation=relation,
    )


def build_semantic_options(observation: Any) -> Tuple[SemanticOption, ...]:
    select = _select_from_observation(observation)
    raw_options = as_tuple(read_field(select, "option", read_field(select, "options", ())))
    return tuple(
        SemanticOption(index=index, key=semantic_key_for_option(observation, option), raw_option=option)
        for index, option in enumerate(raw_options)
    )


def semantic_option_multiset(
    options: Sequence[SemanticOption],
) -> Tuple[Tuple[SemanticOptionKey, int], ...]:
    counts = Counter(option.key for option in options)
    return tuple(sorted(counts.items(), key=lambda item: item[0].sort_key()))


def _canonical_ref_list(refs: Iterable[PhysicalRef]) -> list[Tuple[int, int, int, int, int]]:
    return [ref_value.sort_key() for ref_value in sorted(refs, key=lambda item: item.sort_key())]


def _pokemon_public_payload(pokemon: PokemonView) -> Tuple[Any, ...]:
    return (
        pokemon.ref.sort_key(),
        pokemon.hp,
        pokemon.max_hp,
        pokemon.appear_this_turn,
        tuple(sorted(pokemon.energy_types)),
        tuple(_canonical_ref_list(pokemon.energy_refs)),
        tuple(_canonical_ref_list(pokemon.tool_refs)),
        tuple(_canonical_ref_list(pokemon.pre_evolution_refs)),
    )


def _player_public_payload(player: PlayerView) -> Dict[str, Any]:
    return {
        "index": player.index,
        "active_slot_count": player.active_slot_count,
        "hidden_active_count": player.hidden_active_count,
        "active": sorted(_pokemon_public_payload(pokemon) for pokemon in player.active),
        "bench": sorted(_pokemon_public_payload(pokemon) for pokemon in player.bench),
        "hand_refs": _canonical_ref_list(player.hand_refs),
        "discard_refs": _canonical_ref_list(player.discard_refs),
        "prize_refs": _canonical_ref_list(player.prize_refs),
        "counts": (
            player.deck_count,
            player.hand_count,
            player.prize_count,
            player.bench_max,
        ),
        "conditions": (
            player.poisoned,
            player.burned,
            player.asleep,
            player.paralyzed,
            player.confused,
        ),
    }


def _public_board_payload(state: PublicState) -> Dict[str, Any]:
    """Agent-visible board payload, including the acting player's hidden refs."""

    return {
        "own": _player_public_payload(state.own),
        "opponent": _player_public_payload(state.opponent),
        "stadium": _canonical_ref_list(state.stadium_refs),
        "looking": _canonical_ref_list(state.looking_refs),
        "flags": (
            state.supporter_played,
            state.stadium_played,
            state.energy_attached,
            state.retreated,
        ),
        "first_player": state.first_player,
        "result": state.result,
    }


def _public_only_player_payload(player: PlayerView) -> Dict[str, Any]:
    """Board information visible to both players; never include hidden refs."""

    return {
        "index": player.index,
        "active_slot_count": player.active_slot_count,
        "hidden_active_count": player.hidden_active_count,
        "active": sorted(_pokemon_public_payload(pokemon) for pokemon in player.active),
        "bench": sorted(_pokemon_public_payload(pokemon) for pokemon in player.bench),
        "discard_refs": _canonical_ref_list(player.discard_refs),
        "counts": (
            player.deck_count,
            player.hand_count,
            player.prize_count,
            player.bench_max,
        ),
        "conditions": (
            player.poisoned,
            player.burned,
            player.asleep,
            player.paralyzed,
            player.confused,
        ),
    }


def public_board_payload(state: PublicState) -> Dict[str, Any]:
    """Return an absolute-seat board snapshot with both hidden zones redacted."""

    if not isinstance(state, PublicState):
        raise ValueError("public board payload requires a PublicState")
    players = {
        state.own.index: _public_only_player_payload(state.own),
        state.opponent.index: _public_only_player_payload(state.opponent),
    }
    if set(players) != {0, 1}:
        raise ValueError("public board requires exactly one player for each seat")
    return {
        "turn": state.turn,
        "turn_action_count": state.turn_action_count,
        "players": {
            "p0": players[0],
            "p1": players[1],
        },
        "stadium": _canonical_ref_list(state.stadium_refs),
        "flags": (
            state.supporter_played,
            state.stadium_played,
            state.energy_attached,
            state.retreated,
        ),
        "first_player": state.first_player,
        "result": state.result,
    }


def public_board_fingerprint(state: PublicState) -> str:
    """Hash only information jointly observable on the public board."""

    return hashlib.sha256(
        json.dumps(
            public_board_payload(state),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def relevant_zone_fingerprint(state: PublicState) -> str:
    """Fingerprint only zones relevant to the current selection context."""

    context = state.select_context
    payload: Dict[str, Any] = {
        "select_type": state.select_type,
        "context": context,
        "looking_open": state.looking_open,
        "select_deck_open": state.select_deck_open,
        "remaining_damage_counter": state.remaining_damage_counter,
        "remaining_energy_cost": state.remaining_energy_cost,
    }
    if context == int(SelectContext.MAIN):
        payload["board"] = _public_board_payload(state)
    elif context in (
        int(SelectContext.DISCARD),
        int(SelectContext.DISCARD_CARD_OR_ATTACHED_CARD),
        int(SelectContext.TO_HAND),
        int(SelectContext.LOOK),
    ):
        payload["hand"] = _canonical_ref_list(state.own.hand_refs)
        payload["discard"] = _canonical_ref_list(state.own.discard_refs)
        payload["looking"] = _canonical_ref_list(state.looking_refs)
    elif context in (
        int(SelectContext.ATTACH_FROM),
        int(SelectContext.ATTACH_TO),
        int(SelectContext.SWITCH),
        int(SelectContext.TO_ACTIVE),
        int(SelectContext.HEAL),
    ):
        payload["active"] = [
            (pokemon.ref.sort_key(), pokemon.hp, _canonical_ref_list(pokemon.energy_refs))
            for pokemon in state.own.active
        ]
        payload["bench"] = [
            (pokemon.ref.sort_key(), pokemon.hp, _canonical_ref_list(pokemon.energy_refs))
            for pokemon in state.own.bench
        ]
        payload["discard"] = _canonical_ref_list(state.own.discard_refs)
    else:
        payload["hand"] = _canonical_ref_list(state.own.hand_refs)
        payload["active"] = [pokemon.ref.sort_key() for pokemon in state.own.active]
        payload["bench"] = [pokemon.ref.sort_key() for pokemon in state.own.bench]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def make_prompt_fingerprint(
    state: PublicState,
    options: Sequence[SemanticOption],
    owner_kind: str = "NONE",
    stage: str = "NONE",
    effect_or_attack_id: Optional[int] = None,
) -> PromptFingerprint:
    return PromptFingerprint(
        game_epoch=state.game_epoch,
        owner_kind=owner_kind,
        stage=stage,
        seat=state.seat,
        turn=state.turn,
        turn_action_count=state.turn_action_count,
        select_type=state.select_type,
        context=state.select_context,
        effect_ref=state.effect_ref,
        context_ref=state.context_ref,
        effect_or_attack_id=effect_or_attack_id,
        min_count=state.min_count,
        max_count=state.max_count,
        semantic_option_multiset=semantic_option_multiset(options),
        relevant_zone_fingerprint=relevant_zone_fingerprint(state),
        looking_open=state.looking_open,
        select_deck_open=state.select_deck_open,
        remaining_damage_counter=state.remaining_damage_counter,
        remaining_energy_cost=state.remaining_energy_cost,
    )


def public_state_fingerprint(state: PublicState) -> str:
    payload = {
        "game_epoch": state.game_epoch,
        "seat": state.seat,
        "turn": state.turn,
        "turn_action_count": state.turn_action_count,
        "board": _public_board_payload(state),
        "select": (
            state.select_type,
            state.select_context,
            state.min_count,
            state.max_count,
            state.looking_open,
            state.select_deck_open,
            state.remaining_damage_counter,
            state.remaining_energy_cost,
        ),
        "effect_ref": None if state.effect_ref is None else state.effect_ref.sort_key(),
        "context_ref": None if state.context_ref is None else state.context_ref.sort_key(),
        "history": {
            "complete": state.history_complete,
            "attacked_this_turn": state.attacked_this_turn,
            "ppp_count": state.ppp_count,
            "last_attack_by_lineage": tuple(
                entry.canonical() for entry in state.last_attack_by_lineage
            ),
        },
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def is_stable_main_state(state: PublicState) -> bool:
    """Return true only for a closed, ordinary MAIN action surface."""

    return (
        state.select_type == int(SelectType.MAIN)
        and state.select_context == int(SelectContext.MAIN)
        and state.min_count == 1
        and state.max_count == 1
        and state.effect_ref is None
        and state.context_ref is None
        and not state.looking_refs
        and not state.looking_open
        and not state.select_deck_open
        and state.remaining_damage_counter == 0
        and state.remaining_energy_cost == 0
        and state.turn > 0
        and state.turn_action_count >= 0
        and state.result == -1
    )


__all__ = [
    "as_bool",
    "ActionSpec",
    "AttackHistoryEntry",
    "AreaType",
    "LogType",
    "OptionType",
    "PhysicalRef",
    "PlayerView",
    "PokemonView",
    "PromptFingerprint",
    "PublicState",
    "PublicHistoryTracker",
    "PublicHistoryView",
    "SelectContext",
    "SelectType",
    "SemanticBindError",
    "SemanticOption",
    "SemanticOptionKey",
    "as_int",
    "as_tuple",
    "build_public_state",
    "build_semantic_options",
    "is_stable_main_state",
    "make_prompt_fingerprint",
    "pokemon_lineage_serial",
    "public_board_fingerprint",
    "public_board_payload",
    "public_state_fingerprint",
    "read_field",
    "relevant_zone_fingerprint",
    "semantic_key_for_option",
    "semantic_option_multiset",
]
