"""Fixed-size, public-information encodings for PTCG learning data."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from typing import Any, Iterable


MISSING = -1.0
MAX_BENCH = 5
MAX_HAND_IDS = 20
MAX_DISCARD_IDS = 12
MAX_LOST_ZONE_IDS = 12
MAX_ENERGIES = 4
MAX_TOOLS = 2


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _first(value: Any, names: Iterable[str], default: Any = None) -> Any:
    for name in names:
        found = _get(value, name, None)
        if found is not None:
            return found
    return default


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _number(value: Any, default: float = MISSING) -> float:
    if value is None:
        return default
    try:
        return float(value.value if hasattr(value, "value") else value)
    except (TypeError, ValueError):
        return default


def _category(value: Any) -> float:
    """Encode enums directly and strings with a stable, process-independent hash."""
    numeric = _number(value, MISSING)
    if numeric != MISSING:
        return numeric
    if value is None:
        return MISSING
    digest = blake2b(str(value).encode("ascii", "backslashreplace"), digest_size=4).digest()
    return float(int.from_bytes(digest, "big"))


def _card_id(card: Any) -> float:
    return _number(_first(card, ("id", "cardId"))) if card is not None else MISSING


def _count(player: Any, count_names: Iterable[str], list_names: Iterable[str]) -> float:
    value = _first(player, count_names)
    if value is not None:
        return _number(value, 0.0)
    items = _first(player, list_names, [])
    return float(len(_list(items)))


def _card_ids(cards: Any, size: int) -> list[float]:
    values = [_card_id(card) for card in _list(cards)[:size]]
    return values + [MISSING] * (size - len(values))


def _sorted_card_ids(cards: Any, size: int) -> list[float]:
    values = sorted(value for value in (_card_id(card) for card in _list(cards)) if value != MISSING)
    return values[:size] + [MISSING] * max(0, size - len(values))


def _pokemon_values(pokemon: Any) -> list[float]:
    if pokemon is None:
        return [MISSING] * len(POKEMON_FEATURE_NAMES)
    hp = _number(_first(pokemon, ("hp", "currentHp")))
    max_hp = _number(_first(pokemon, ("maxHp", "max_hp")))
    damage = _number(_first(pokemon, ("damage", "damageCounter", "damage_counter")))
    if damage == MISSING and hp != MISSING and max_hp != MISSING:
        damage = max(0.0, max_hp - hp)
    energy_cards = _first(pokemon, ("energyCards", "energy_cards"), None)
    energies = _list(energy_cards if energy_cards is not None else _get(pokemon, "energies", []))
    tools = _list(_get(pokemon, "tools", []))
    return [_card_id(pokemon), hp, max_hp, damage, float(len(energies))] + _card_ids(energies, MAX_ENERGIES) + [float(len(tools))] + _card_ids(tools, MAX_TOOLS)


POKEMON_FEATURE_NAMES = (
    "card_id", "hp", "max_hp", "damage", "energy_count",
    "energy_0_id", "energy_1_id", "energy_2_id", "energy_3_id",
    "tool_count", "tool_0_id", "tool_1_id",
)


def _build_state_feature_names() -> tuple[str, ...]:
    names = [
        "turn", "turn_action_count", "seat", "acting_is_self", "first_player", "supporter_played",
        "stadium_played", "energy_attached", "retreated", "result", "stadium_id",
        "select_type", "select_context", "select_min_count", "select_max_count",
        "select_remain_damage_counter", "select_remain_energy_cost", "legal_option_count",
    ]
    for seat in ("self", "opponent"):
        names += [
            seat + "_deck_count", seat + "_hand_count", seat + "_prize_count",
            seat + "_bench_count", seat + "_bench_max", seat + "_discard_count",
            seat + "_lost_zone_count", seat + "_poisoned", seat + "_burned", seat + "_asleep",
            seat + "_paralyzed", seat + "_confused",
        ]
        names += [seat + "_active_" + name for name in POKEMON_FEATURE_NAMES]
        for index in range(MAX_BENCH):
            names += [seat + "_bench_" + str(index) + "_" + name for name in POKEMON_FEATURE_NAMES]
        names += [seat + "_discard_" + str(index) + "_id" for index in range(MAX_DISCARD_IDS)]
        names += [seat + "_lost_zone_" + str(index) + "_id" for index in range(MAX_LOST_ZONE_IDS)]
    names += ["self_hand_" + str(index) + "_id" for index in range(MAX_HAND_IDS)]
    return tuple(names)


STATE_FEATURE_NAMES = _build_state_feature_names()
OPTION_FEATURE_NAMES = (
    "option_ordinal", "type", "context", "card_id", "attack_id", "target_card_id",
    "area", "index", "player", "in_play_area", "in_play_index", "tool_index",
    "energy_index", "number", "count", "special_condition_type", "serial",
)


@dataclass(frozen=True)
class EncodingSchema:
    version: str = "ptcg-public-v4"
    missing_value: float = MISSING
    state_feature_names: tuple[str, ...] = STATE_FEATURE_NAMES
    option_feature_names: tuple[str, ...] = OPTION_FEATURE_NAMES

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "missing_value": self.missing_value,
            "state_feature_names": list(self.state_feature_names),
            "option_feature_names": list(self.option_feature_names),
        }


SCHEMA = EncodingSchema()


@dataclass(frozen=True)
class EncodedObservation:
    state_vector: list[float]
    option_vectors: list[list[float]]
    schema_version: str = SCHEMA.version


def _player_values(player: Any) -> list[float]:
    active = _list(_get(player, "active", []))
    bench = _list(_get(player, "bench", []))
    discard = _first(player, ("discard", "discardPile", "discard_pile"), [])
    lost_zone = _first(player, ("lostZone", "lost_zone", "lostzone"), [])
    values = [
        _count(player, ("deckCount", "deck_count"), ("deck",)),
        _count(player, ("handCount", "hand_count"), ("hand",)),
        _count(player, ("prizeCount", "prize_count"), ("prize", "prizes")),
        float(len(bench)), _number(_first(player, ("benchMax", "bench_max")), 0.0),
        float(len(_list(discard))), float(len(_list(lost_zone))),
    ]
    values += [_number(_get(player, name), 0.0) for name in ("poisoned", "burned", "asleep", "paralyzed", "confused")]
    values += _pokemon_values(active[0] if active else None)
    for index in range(MAX_BENCH):
        values += _pokemon_values(bench[index] if index < len(bench) else None)
    values += _card_ids(discard, MAX_DISCARD_IDS)
    values += _card_ids(lost_zone, MAX_LOST_ZONE_IDS)
    return values


def encode_state(observation: Any, perspective_seat: int | None = None) -> list[float]:
    """Encode public board state without hidden card identities from either seat."""
    current = _get(observation, "current", observation) or {}
    select = _get(observation, "select", {}) or {}
    players = _list(_get(current, "players", []))
    acting_seat = int(_number(_first(current, ("yourIndex", "your_index")), 0.0))
    seat = acting_seat if perspective_seat is None else int(perspective_seat)
    own = players[seat] if 0 <= seat < len(players) else {}
    opponent_seat = 1 - seat
    opponent = players[opponent_seat] if 0 <= opponent_seat < len(players) else {}
    stadium = _list(_get(current, "stadium", []))
    values = [
        _number(_get(current, "turn"), 0.0), _number(_first(current, ("turnActionCount", "turn_action_count")), 0.0),
        float(seat), float(acting_seat == seat), _number(_first(current, ("firstPlayer", "first_player")), MISSING),
        _number(_first(current, ("supporterPlayed", "supporter_played")), 0.0),
        _number(_first(current, ("stadiumPlayed", "stadium_played")), 0.0),
        _number(_first(current, ("energyAttached", "energy_attached")), 0.0),
        _number(_get(current, "retreated"), 0.0), _number(_get(current, "result"), MISSING),
        _card_id(stadium[0]) if stadium else MISSING,
        _category(_get(select, "type")), _category(_get(select, "context")),
        _number(_first(select, ("minCount", "min_count")), 0.0), _number(_first(select, ("maxCount", "max_count")), 0.0),
        _number(_first(select, ("remainDamageCounter", "remain_damage_counter")), 0.0),
        _number(_first(select, ("remainEnergyCost", "remain_energy_cost")), 0.0),
        float(len(_list(_first(select, ("option", "options"), [])))),
    ]
    values += _player_values(own) + _player_values(opponent)
    visible_own_hand = _get(own, "hand", []) if seat == acting_seat else []
    values += _sorted_card_ids(visible_own_hand, MAX_HAND_IDS)
    assert len(values) == len(STATE_FEATURE_NAMES)
    return values


def _area_card(observation: Any, area: Any, index: Any, player_index: Any) -> Any:
    current = _get(observation, "current", {}) or {}
    select = _get(observation, "select", {}) or {}
    players = _list(_get(current, "players", []))
    acting = int(_number(_first(current, ("yourIndex", "your_index")), 0.0))
    owner = int(_number(player_index, acting))
    area_value = int(_number(area, -1.0))
    item_index = int(_number(index, -1.0))
    if item_index < 0:
        return None
    if area_value == 1:
        cards = _list(_get(select, "deck", []))
    elif area_value == 7:
        cards = _list(_get(current, "stadium", []))
    elif area_value == 12:
        cards = _list(_get(current, "looking", []))
    elif 0 <= owner < len(players):
        player = players[owner]
        if area_value == 2:
            if owner != acting:
                return None
            cards = _list(_get(player, "hand", []))
        elif area_value == 3:
            cards = _list(_get(player, "discard", []))
        elif area_value == 4:
            cards = _list(_get(player, "active", []))
        elif area_value == 5:
            cards = _list(_get(player, "bench", []))
        else:
            cards = []
    else:
        cards = []
    return cards[item_index] if item_index < len(cards) else None


def _resolved_option_cards(observation: Any, option: Any) -> tuple[Any, Any]:
    current = _get(observation, "current", {}) or {}
    acting = int(_number(_first(current, ("yourIndex", "your_index")), 0.0))
    option_type = int(_number(_get(option, "type"), -1.0))
    owner = _first(option, ("playerIndex", "player_index"), acting)
    area = _get(option, "area")
    index = _get(option, "index")
    if option_type == 7 and area is None:
        area = 2
    source = _area_card(observation, area, index, owner)
    target = _area_card(
        observation,
        _first(option, ("inPlayArea", "in_play_area")),
        _first(option, ("inPlayIndex", "in_play_index")),
        acting,
    )
    if option_type in (4, 5, 6) and source is not None:
        attached_name = "tools" if option_type == 4 else "energyCards"
        attached_index_name = ("toolIndex", "tool_index") if option_type == 4 else ("energyIndex", "energy_index")
        attached = _list(_get(source, attached_name, []))
        attached_index = int(_number(_first(option, attached_index_name), -1.0))
        source = attached[attached_index] if 0 <= attached_index < len(attached) else None
    return source, target


def encode_option(option: Any, select: Any = None, ordinal: int = 0, observation: Any = None) -> list[float]:
    """Encode one legal option and its selection context in a fixed order."""
    target = _first(option, ("targetCardId", "target_card_id", "targetId", "target_id"))
    if target is None:
        target = _first(option, ("targetCard", "target_card", "target"))
    target_id = _number(target)
    if target_id == MISSING and target is not None:
        target_id = _card_id(target)
    source_card = target_card = None
    if observation is not None:
        source_card, target_card = _resolved_option_cards(observation, option)
    card_id = _number(_first(option, ("cardId", "card_id")))
    if card_id == MISSING:
        card_id = _card_id(source_card)
    if target_id == MISSING:
        target_id = _card_id(target_card)
    values = [
        float(ordinal), _category(_get(option, "type")), _category(_get(select or {}, "context")),
        card_id, _number(_first(option, ("attackId", "attack_id"))),
        target_id, _category(_get(option, "area")), _number(_get(option, "index")),
        _number(_first(option, ("playerIndex", "player_index"))), _category(_first(option, ("inPlayArea", "in_play_area"))),
        _number(_first(option, ("inPlayIndex", "in_play_index"))), _number(_first(option, ("toolIndex", "tool_index"))),
        _number(_first(option, ("energyIndex", "energy_index"))), _number(_get(option, "number")),
        _number(_get(option, "count")), _category(_first(option, ("specialConditionType", "special_condition_type"))),
        _number(_get(option, "serial")),
    ]
    assert len(values) == len(OPTION_FEATURE_NAMES)
    return values


def encode_legal_options(observation: Any) -> list[list[float]]:
    select = _get(observation, "select", {}) or {}
    options = _list(_first(select, ("option", "options"), []))
    return [encode_option(option, select, ordinal, observation) for ordinal, option in enumerate(options)]


def encode_observation(observation: Any, perspective_seat: int | None = None) -> EncodedObservation:
    return EncodedObservation(encode_state(observation, perspective_seat), encode_legal_options(observation))
