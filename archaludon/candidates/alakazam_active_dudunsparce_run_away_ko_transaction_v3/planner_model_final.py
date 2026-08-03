"""Final Pokemon row: preserve physical Energy-card/unit pairing."""

from __future__ import annotations

from typing import Any

import planner_model as base
import planner_model_corrected as corrected


def pokemon_row(pokemon: Any, owner: int) -> tuple[Any, ...] | None:
    if owner not in (0, 1) or pokemon is None:
        return None
    card_id = getattr(pokemon, "id", None)
    serial = getattr(pokemon, "serial", None)
    if not corrected._valid_int(card_id, positive=True) or not corrected._valid_int(serial, positive=True):
        return None
    line = base.lineage_key(pokemon, owner)
    if line is None:
        return None
    energy_source = list(getattr(pokemon, "energyCards", None) or [])
    energy_units_source = list(getattr(pokemon, "energies", None) or [])
    if len(energy_source) != len(energy_units_source):
        return None
    energy_cards = tuple(corrected._owned_card_row(card, owner) for card in energy_source)
    energy_units = tuple(base.enum_int(value) for value in energy_units_source)
    tools = tuple(
        corrected._owned_card_row(card, owner)
        for card in (getattr(pokemon, "tools", None) or [])
    )
    lineage = tuple(
        corrected._owned_card_row(card, owner)
        for card in (getattr(pokemon, "preEvolution", None) or [])
    )
    if any(row is None for row in energy_cards + tools + lineage) or any(value is None for value in energy_units):
        return None
    energy_pairs = tuple(
        sorted(zip(energy_cards, energy_units), key=lambda row: row[0][1])
    )
    hp = getattr(pokemon, "hp", None)
    max_hp = getattr(pokemon, "maxHp", None)
    if not corrected._valid_int(hp) or not corrected._valid_int(max_hp, positive=True) or hp < 0 or hp > max_hp:
        return None
    return (
        line,
        (card_id, serial, owner),
        hp,
        max_hp,
        bool(getattr(pokemon, "appearThisTurn", False)),
        energy_pairs,
        tuple(row[0] for row in energy_pairs),
        tuple(sorted(tools, key=lambda row: row[1])),
        lineage,
    )


def install() -> None:
    corrected.pokemon_row = pokemon_row
    base.pokemon_row = pokemon_row
    base.public_snapshot = corrected.public_snapshot

