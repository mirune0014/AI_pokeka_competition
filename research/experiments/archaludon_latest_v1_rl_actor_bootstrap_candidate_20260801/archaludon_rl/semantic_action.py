"""Stable semantic option identities and strict engine-action validation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from .public_state import enum_int, get_field


OPTION_FIELDS = (
    "number",
    "area",
    "playerIndex",
    "toolIndex",
    "energyIndex",
    "count",
    "inPlayArea",
    "inPlayIndex",
    "attackId",
    "cardId",
    "specialConditionType",
)


def _card_id(card: Any) -> int | None:
    return enum_int(get_field(card, "id"))


def _zone_card(
    observation: Any, area: int | None, index: int | None, player_index: int | None
) -> Any:
    current = get_field(observation, "current")
    select = get_field(observation, "select")
    if current is None or index is None or index < 0:
        return None
    your_index = enum_int(get_field(current, "yourIndex"))
    owner = your_index if player_index not in (0, 1) else player_index
    players = list(get_field(current, "players", ()) or ())
    if owner not in (0, 1) or len(players) != 2:
        return None
    player = players[owner]
    # AreaType values: deck=1, hand=2, discard=3, active=4, bench=5,
    # prize=6, stadium=7, looking=12.  Prize identity is never resolved.
    if area == 1:
        visible = get_field(select, "deck")
        values = list(visible or ())
    elif area == 2:
        values = list(get_field(player, "hand", ()) or ())
    elif area == 3:
        values = list(get_field(player, "discard", ()) or ())
    elif area == 4:
        values = list(get_field(player, "active", ()) or ())
    elif area == 5:
        values = list(get_field(player, "bench", ()) or ())
    elif area == 7:
        values = list(get_field(current, "stadium", ()) or ())
    elif area == 12:
        values = list(get_field(current, "looking", ()) or ())
    else:
        return None
    return values[index] if index < len(values) else None


def _pokemon_at(
    observation: Any, area: int | None, index: int | None, player_index: int | None
) -> Any:
    return _zone_card(observation, area, index, player_index)


def resolve_option_cards(observation: Any, option: Any) -> tuple[int | None, int | None]:
    option_type = enum_int(get_field(option, "type"))
    area = enum_int(get_field(option, "area"))
    index = enum_int(get_field(option, "index"))
    player_index = enum_int(get_field(option, "playerIndex"))
    current = get_field(observation, "current")
    your_index = enum_int(get_field(current, "yourIndex")) if current else None
    source: Any = None
    target: Any = None
    if option_type == 7:  # PLAY
        source = _zone_card(observation, 2, index, your_index)
    elif option_type in (8, 9):  # ATTACH / EVOLVE
        source = _zone_card(observation, area or 2, index, your_index)
        target = _zone_card(
            observation,
            enum_int(get_field(option, "inPlayArea")),
            enum_int(get_field(option, "inPlayIndex")),
            your_index,
        )
    elif option_type in (3, 10, 11):  # CARD / ABILITY / DISCARD
        source = _zone_card(observation, area, index, player_index)
    elif option_type in (4, 5, 6):  # attached tool/energy
        pokemon = _pokemon_at(observation, area, index, player_index)
        field = "tools" if option_type == 4 else "energyCards"
        attached_index = enum_int(
            get_field(option, "toolIndex" if option_type == 4 else "energyIndex")
        )
        attached = list(get_field(pokemon, field, ()) or ())
        if attached_index is not None and 0 <= attached_index < len(attached):
            source = attached[attached_index]
        target = pokemon
    elif option_type == 13:  # ATTACK
        players = list(get_field(current, "players", ()) or ()) if current else []
        if your_index in (0, 1) and len(players) == 2:
            active = list(get_field(players[your_index], "active", ()) or ())
            source = active[0] if active else None
            opposing = list(
                get_field(players[1 - your_index], "active", ()) or ()
            )
            target = opposing[0] if opposing else None
    elif option_type == 15:  # SKILL
        source = {"id": get_field(option, "cardId")}
    return _card_id(source), _card_id(target)


@dataclass(frozen=True)
class SemanticOption:
    engine_index: int
    option_type: int
    fields: tuple[tuple[str, int | None], ...]
    source_card_id: int | None
    target_card_id: int | None

    @property
    def identity_payload(self) -> dict[str, Any]:
        return {
            "option_type": self.option_type,
            "fields": dict(self.fields),
            "source_card_id": self.source_card_id,
            "target_card_id": self.target_card_id,
        }

    @property
    def identity(self) -> str:
        payload = json.dumps(
            self.identity_payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def semantic_options(observation: Any) -> tuple[SemanticOption, ...]:
    select = get_field(observation, "select")
    options = list(get_field(select, "option", ()) or ())
    current = get_field(observation, "current")
    your_index = enum_int(get_field(current, "yourIndex")) if current else None
    result: list[SemanticOption] = []
    for engine_index, option in enumerate(options):
        option_type = enum_int(get_field(option, "type"))
        if option_type is None:
            raise ValueError(f"option {engine_index} has no integer type")
        normalized_fields: list[tuple[str, int | None]] = []
        for name in OPTION_FIELDS:
            if name == "playerIndex" and get_field(option, name) is None:
                continue
            value = enum_int(get_field(option, name))
            if name == "playerIndex" and value in (0, 1) and your_index in (0, 1):
                value = 0 if value == your_index else 1
            normalized_fields.append((name, value))
        fields = tuple(normalized_fields)
        source, target = resolve_option_cards(observation, option)
        result.append(
            SemanticOption(
                engine_index=engine_index,
                option_type=option_type,
                fields=fields,
                source_card_id=source,
                target_card_id=target,
            )
        )
    return tuple(result)


def validate_engine_action(observation: Any, action: Any) -> list[int]:
    if not isinstance(action, list):
        raise TypeError("action must be list[int]")
    if any(not isinstance(index, int) or isinstance(index, bool) for index in action):
        raise TypeError("action must contain plain int indices")
    select = get_field(observation, "select")
    if select is None:
        # Deck requests return a 60-card list rather than option indices.
        if len(action) != 60:
            raise ValueError("deck request must return exactly 60 card IDs")
        return list(action)
    if len(set(action)) != len(action):
        raise ValueError("action indices must be unique")
    options = list(get_field(select, "option", ()) or ())
    minimum = enum_int(get_field(select, "minCount"))
    maximum = enum_int(get_field(select, "maxCount"))
    if minimum is None or maximum is None or not (0 <= minimum <= maximum):
        raise ValueError("invalid minCount/maxCount selection contract")
    if not minimum <= len(action) <= maximum:
        raise ValueError(
            f"action count {len(action)} outside [{minimum}, {maximum}]"
        )
    if any(index < 0 or index >= len(options) for index in action):
        raise ValueError("action index outside current option range")
    return list(action)


def semantic_action_identity(
    observation: Any, action: Any, *, option_cache: tuple[SemanticOption, ...] | None = None
) -> str:
    validated = validate_engine_action(observation, action)
    if get_field(observation, "select") is None:
        payload: Any = {"deck_sha_ids": validated}
    else:
        options = option_cache or semantic_options(observation)
        payload = [options[index].identity_payload for index in validated]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
