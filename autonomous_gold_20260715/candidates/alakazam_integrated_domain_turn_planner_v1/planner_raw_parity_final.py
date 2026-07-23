"""Complete planner-critical raw/parsed observation parity gate."""

from dataclasses import asdict
from typing import Any

import planner_runtime_model as runtime_model


CURRENT_SCALARS = (
    "turn",
    "yourIndex",
    "firstPlayer",
    "turnActionCount",
    "result",
    "energyAttached",
    "supporterPlayed",
    "stadiumPlayed",
    "retreated",
)
PLAYER_SCALARS = (
    "handCount",
    "deckCount",
    "benchMax",
    "poisoned",
    "burned",
    "asleep",
    "paralyzed",
    "confused",
)
POKEMON_SCALARS = (
    "id",
    "serial",
    "hp",
    "maxHp",
    "appearThisTurn",
)
CARD_FIELDS = ("id", "serial", "playerIndex")
SELECT_SCALARS = (
    "type",
    "context",
    "minCount",
    "maxCount",
    "remainDamageCounter",
    "remainEnergyCost",
)


def _value(value: Any):
    try:
        return int(value) if type(value).__module__ == "enum" or hasattr(value, "__int__") and not isinstance(value, bool) else value
    except (TypeError, ValueError):
        return value


def _scalars(raw: dict, parsed: dict, fields: tuple[str, ...]) -> bool:
    return all(field in raw and field in parsed and _value(raw[field]) == _value(parsed[field]) for field in fields)


def _card(raw: dict, parsed: dict, owner: int | None = None) -> bool:
    if not isinstance(raw, dict) or not isinstance(parsed, dict):
        return False
    if owner is not None and raw.get("playerIndex") != owner:
        return False
    return _scalars(raw, parsed, CARD_FIELDS)


def _cards(raw: list, parsed: list, owner: int | None = None) -> bool:
    return isinstance(raw, list) and isinstance(parsed, list) and len(raw) == len(parsed) and all(
        _card(left, right, owner) for left, right in zip(raw, parsed)
    )


def _pokemon(raw: dict, parsed: dict, owner: int) -> bool:
    return (
        isinstance(raw, dict)
        and isinstance(parsed, dict)
        and raw.get("playerIndex", owner) == owner
        and _scalars(raw, parsed, POKEMON_SCALARS)
        and raw.get("energies") == parsed.get("energies")
        and _cards(raw.get("energyCards", []), parsed.get("energyCards", []), owner)
        and _cards(raw.get("tools", []), parsed.get("tools", []), owner)
        and _cards(raw.get("preEvolution", []), parsed.get("preEvolution", []), owner)
    )


def _pokemon_zone(raw: list, parsed: list, owner: int) -> bool:
    return isinstance(raw, list) and isinstance(parsed, list) and len(raw) == len(parsed) and all(
        _pokemon(left, right, owner) for left, right in zip(raw, parsed)
    )


def _optional_card(raw: Any, parsed: Any) -> bool:
    if raw is None or parsed is None:
        return raw is None and parsed is None
    return _card(raw, parsed)


def raw_parsed_agree(raw: dict, obs: Any) -> bool:
    try:
        parsed = asdict(obs)
        raw_current = raw["current"]
        parsed_current = parsed["current"]
        if not _scalars(raw_current, parsed_current, CURRENT_SCALARS):
            return False
        raw_players = raw_current["players"]
        parsed_players = parsed_current["players"]
        if len(raw_players) != len(parsed_players) or len(raw_players) != 2:
            return False
        owner = raw_current["yourIndex"]
        for index, (raw_player, parsed_player) in enumerate(zip(raw_players, parsed_players)):
            if not _scalars(raw_player, parsed_player, PLAYER_SCALARS):
                return False
            if len(raw_player["prize"]) != len(parsed_player["prize"]):
                return False
            if not _pokemon_zone(raw_player["active"], parsed_player["active"], index):
                return False
            if not _pokemon_zone(raw_player["bench"], parsed_player["bench"], index):
                return False
            if not _cards(raw_player.get("discard", []), parsed_player.get("discard", []), index):
                return False
            if not _cards(raw_player.get("lost", []), parsed_player.get("lost", []), index):
                return False
            if index == owner and not _cards(raw_player["hand"], parsed_player["hand"], index):
                return False
        if not _cards(raw_current.get("stadium", []), parsed_current.get("stadium", [])):
            return False
        raw_select = raw["select"]
        parsed_select = parsed["select"]
        if not _scalars(raw_select, parsed_select, SELECT_SCALARS):
            return False
        if not _optional_card(raw_select.get("effect"), parsed_select.get("effect")):
            return False
        if not _optional_card(raw_select.get("contextCard"), parsed_select.get("contextCard")):
            return False
        raw_options = raw_select["option"]
        parsed_options = parsed_select["option"]
        if len(raw_options) != len(parsed_options):
            return False
        for left, right in zip(raw_options, parsed_options):
            for field in runtime_model.model.OPTION_FIELDS:
                if _value(left.get(field)) != _value(right.get(field)):
                    return False
        raw_deck = raw_select.get("deck")
        parsed_deck = parsed_select.get("deck")
        if raw_deck is None or parsed_deck is None:
            if raw_deck is not None or parsed_deck is not None:
                return False
        elif not _cards(raw_deck, parsed_deck):
            return False
        return True
    except (KeyError, TypeError, AttributeError, IndexError):
        return False


runtime_model.raw_parsed_agree = raw_parsed_agree

