"""Physical-card semantic option keys independent of hidden zone order."""

from __future__ import annotations

from typing import Any

import planner_model as model


def _source_identity(parent: Any, obs: Any, option: Any):
    owner = getattr(option, "playerIndex", None)
    if owner not in (0, 1):
        owner = obs.current.yourIndex
    source = model._option_card(parent, obs, option)
    card = model.card_row(source)
    if card is not None:
        return ("card", card)
    if source is not None:
        card_id = getattr(source, "id", None)
        serial = getattr(source, "serial", None)
        if (
            isinstance(card_id, int)
            and not isinstance(card_id, bool)
            and card_id > 0
            and isinstance(serial, int)
            and not isinstance(serial, bool)
            and serial > 0
        ):
            return ("pokemon", (card_id, serial, owner))
    return None


def stable_option_key(parent: Any, obs: Any, option: Any) -> tuple[Any, ...]:
    """Canonical option identity with physical serials replacing zone indices."""
    owner = getattr(option, "playerIndex", None)
    if owner not in (0, 1):
        owner = obs.current.yourIndex
    source = _source_identity(parent, obs, option)
    target = model._pokemon_for_area(
        parent,
        obs,
        getattr(option, "inPlayArea", None),
        getattr(option, "inPlayIndex", None),
        owner,
    )
    target_line = model.lineage_key(target, owner)
    target_serial = getattr(target, "serial", None) if target is not None else None
    attached_serial = None
    attached_pokemon = model._pokemon_for_area(
        parent,
        obs,
        getattr(option, "area", None),
        getattr(option, "index", None),
        owner,
    )
    if attached_pokemon is not None:
        energy_index = getattr(option, "energyIndex", None)
        tool_index = getattr(option, "toolIndex", None)
        if isinstance(energy_index, int) and not isinstance(energy_index, bool):
            cards = getattr(attached_pokemon, "energyCards", None) or []
            if 0 <= energy_index < len(cards):
                attached_serial = getattr(cards[energy_index], "serial", None)
        elif isinstance(tool_index, int) and not isinstance(tool_index, bool):
            cards = getattr(attached_pokemon, "tools", None) or []
            if 0 <= tool_index < len(cards):
                attached_serial = getattr(cards[tool_index], "serial", None)

    normalized = []
    for field in model.OPTION_FIELDS:
        value = model.enum_int(getattr(option, field, None))
        if field == "index" and (source is not None or attached_pokemon is not None):
            value = None
        elif field == "inPlayIndex" and target is not None:
            value = None
        elif field == "energyIndex" and attached_serial is not None:
            value = None
        elif field == "toolIndex" and attached_serial is not None:
            value = None
        normalized.append(value)
    return tuple(normalized) + (source, target_line, target_serial, attached_serial)


def install() -> None:
    model.stable_option_key = stable_option_key

