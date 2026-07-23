"""Canonical public-information states for the public-belief teacher."""
from __future__ import annotations

from hashlib import blake2b
import json
import math
from typing import Any


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _items(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _value(value: Any) -> Any:
    """Return a JSON value without relying on object identity or repr()."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, dict):
        return {str(key): _value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_value(item) for item in value]
    enum_value = getattr(value, "value", None)
    if enum_value is not None and enum_value is not value:
        return _value(enum_value)
    attributes = getattr(value, "__dict__", None)
    if isinstance(attributes, dict):
        return {str(key): _value(attributes[key]) for key in sorted(attributes)}
    return str(value)


def _fields(value: Any, names: tuple[str, ...]) -> dict[str, Any]:
    return {name: _value(_get(value, name)) for name in names if _get(value, name) is not None}


def _sorted_cards(cards: Any) -> list[dict[str, Any] | None]:
    values = [_card(card) for card in _items(cards)]
    return sorted(values, key=lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")))


CARD_FIELDS = (
    "id", "cardId", "name", "hp", "currentHp", "maxHp", "damage", "damageCounter",
    "poisoned", "burned", "asleep", "paralyzed", "confused",
)
OPTION_FIELDS = (
    "type", "context", "area", "index", "playerIndex", "inPlayArea", "inPlayIndex",
    "toolIndex", "energyIndex", "number", "count", "attackId", "fromArea", "toArea",
    "specialConditionType",
)


def _card(card: Any) -> dict[str, Any] | None:
    if card is None:
        return None
    result = _fields(card, CARD_FIELDS)
    for name in ("energyCards", "energy_cards", "tools", "preEvolution", "pre_evolution"):
        attached = _get(card, name, None)
        if attached is not None:
            result[name] = _sorted_cards(attached)
    return result


def _player(player: Any, include_hand: bool) -> dict[str, Any]:
    result = _fields(player, (
        "deckCount", "deck_count", "handCount", "hand_count", "prizeCount", "prize_count",
        "benchMax", "bench_max", "poisoned", "burned", "asleep", "paralyzed", "confused",
    ))
    result["active"] = [_card(card) for card in _items(_get(player, "active", []))]
    result["bench"] = [_card(card) for card in _items(_get(player, "bench", []))]
    if include_hand:
        result["hand"] = _sorted_cards(_get(player, "hand", []))
    result["discard"] = _sorted_cards(_get(player, "discard", []))
    lost_zone = _get(player, "lostZone", _get(player, "lost_zone", []))
    result["lostZone"] = _sorted_cards(lost_zone)
    return result


def canonical_public_state(observation: Any, perspective_seat: int) -> dict[str, Any]:
    """Project an observation onto stable, public state and legal-option data."""
    current = _get(observation, "current", observation) or {}
    select = _get(observation, "select", {}) or {}
    players = _items(_get(current, "players", []))
    state = _fields(current, (
        "turn", "turnActionCount", "turn_action_count", "yourIndex", "your_index", "firstPlayer",
        "first_player", "supporterPlayed", "supporter_played", "stadiumPlayed", "stadium_played",
        "energyAttached", "energy_attached", "retreated", "result",
    ))
    state["perspectiveSeat"] = int(perspective_seat)
    state["players"] = [
        _player(player, include_hand=index == int(perspective_seat))
        for index, player in enumerate(players)
    ]
    state["stadium"] = [_card(card) for card in _items(_get(current, "stadium", []))]
    state["select"] = _fields(select, (
        "type", "context", "minCount", "min_count", "maxCount", "max_count",
        "remainDamageCounter", "remain_damage_counter", "remainEnergyCost", "remain_energy_cost",
    ))
    state["select"]["option"] = [_fields(option, OPTION_FIELDS) for option in _items(_get(select, "option", []))]
    return state


def public_state_hash(observation: Any, perspective_seat: int) -> str:
    """Return a stable BLAKE2b hash of canonical_public_state."""
    encoded = json.dumps(
        canonical_public_state(observation, perspective_seat),
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")
    return blake2b(encoded, digest_size=32).hexdigest()
