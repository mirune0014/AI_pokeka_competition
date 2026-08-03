"""Canonical public Energy facts without inventing card/unit pairings."""

import planner_model as base
import planner_model_corrected as corrected


def _known_bundle(pokemon, card_id):
    """Return only bundles certified by public card metadata and engine enums."""
    if card_id in range(1, 9):
        return (card_id,)
    if card_id in (9, 11, 13, 14):
        return (0,)
    if card_id == 12:
        return (10,)
    if card_id == 15:
        # Team Rocket's Energy supplies two units represented by the engine's
        # public P/D-combination enum.  The corpus exposes one physical card
        # and two unit entries; neither unit is assigned a separate source.
        return (11, 11)
    if card_id == 17:
        # Ignition Energy supplies three Colorless on an Evolution Pokemon and
        # one otherwise.  preEvolution is the public evolution certificate.
        return (0, 0, 0) if (getattr(pokemon, "preEvolution", None) or []) else (0,)
    if card_id == 18:
        return (1,)
    if card_id == 19:
        return (5,)
    if card_id == 20:
        return (6,)
    return None


def pokemon_row(pokemon, owner):
    if owner not in (0, 1) or pokemon is None:
        return None
    card_id = getattr(pokemon, "id", None)
    serial = getattr(pokemon, "serial", None)
    if not corrected._valid_int(card_id, positive=True) or not corrected._valid_int(serial, positive=True):
        return None
    line = base.lineage_key(pokemon, owner)
    if line is None:
        return None
    energy_cards = tuple(corrected._owned_card_row(card, owner) for card in (pokemon.energyCards or []))
    energy_units = tuple(base.enum_int(value) for value in (pokemon.energies or []))
    tools = tuple(corrected._owned_card_row(card, owner) for card in (pokemon.tools or []))
    lineage = tuple(corrected._owned_card_row(card, owner) for card in (pokemon.preEvolution or []))
    if any(row is None for row in energy_cards + tools + lineage) or any(value is None for value in energy_units):
        return None

    sorted_cards = tuple(sorted(energy_cards, key=lambda row: row[1]))
    sorted_units = tuple(sorted(energy_units))
    known_rows = []
    known_complete = True
    for row in sorted_cards:
        bundle = _known_bundle(pokemon, row[0])
        if bundle is None:
            known_complete = False
            continue
        known_rows.append((row, tuple(sorted(bundle))))
    expected_units = tuple(sorted(unit for _, bundle in known_rows for unit in bundle))
    pairing_certified = known_complete and expected_units == sorted_units
    energy_facts = (
        "energy_facts_v1",
        ("physical_cards", sorted_cards),
        ("unit_multiset", sorted_units),
        ("pairing_certified", pairing_certified),
        ("known_card_bundles", tuple(known_rows) if pairing_certified else ()),
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
        energy_facts,
        sorted_cards,
        tuple(sorted(tools, key=lambda row: row[1])),
        lineage,
    )


corrected.pokemon_row = pokemon_row
base.pokemon_row = pokemon_row
