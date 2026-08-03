"""Fail-closed public snapshot corrections for cg.api Pokemon objects."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import planner_model as base


def _valid_int(value: Any, *, positive: bool = False) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and (value > 0 if positive else True)
    )


def _owned_card_row(card: Any, owner: int) -> tuple[int, int, int] | None:
    row = base.card_row(card)
    return row if row is not None and row[2] == owner else None


def pokemon_row(pokemon: Any, owner: int) -> tuple[Any, ...] | None:
    """Canonicalize a Pokemon whose API object has no ``playerIndex`` field."""
    if owner not in (0, 1) or pokemon is None:
        return None
    card_id = getattr(pokemon, "id", None)
    serial = getattr(pokemon, "serial", None)
    if not _valid_int(card_id, positive=True) or not _valid_int(serial, positive=True):
        return None
    line = base.lineage_key(pokemon, owner)
    if line is None:
        return None
    energy_source = list(getattr(pokemon, "energyCards", None) or [])
    energy_units = list(getattr(pokemon, "energies", None) or [])
    tool_source = list(getattr(pokemon, "tools", None) or [])
    lineage_source = list(getattr(pokemon, "preEvolution", None) or [])
    if len(energy_source) != len(energy_units):
        return None
    energy_cards = tuple(_owned_card_row(card, owner) for card in energy_source)
    tools = tuple(_owned_card_row(card, owner) for card in tool_source)
    lineage = tuple(_owned_card_row(card, owner) for card in lineage_source)
    if any(row is None for row in energy_cards + tools + lineage):
        return None
    normalized_units = tuple(base.enum_int(value) for value in energy_units)
    if any(value is None for value in normalized_units):
        return None
    hp = getattr(pokemon, "hp", None)
    max_hp = getattr(pokemon, "maxHp", None)
    if not _valid_int(hp) or not _valid_int(max_hp, positive=True) or hp < 0 or hp > max_hp:
        return None
    return (
        line,
        (card_id, serial, owner),
        hp,
        max_hp,
        bool(getattr(pokemon, "appearThisTurn", False)),
        normalized_units,
        tuple(sorted(energy_cards, key=lambda row: row[1])),
        tuple(sorted(tools, key=lambda row: row[1])),
        lineage,
    )


def _register_serials(seen: dict[int, str], rows: Any, location: str) -> bool:
    """Register every physical serial nested in a canonical public row."""
    physical = []
    if rows is None:
        return False
    if isinstance(rows, tuple) and len(rows) == 3 and all(isinstance(value, int) for value in rows):
        physical.append(rows)
    elif isinstance(rows, tuple):
        for index, row in enumerate(rows):
            if not _register_serials(seen, row, f"{location}/{index}"):
                return False
        return True
    else:
        return True
    for _, serial, _ in physical:
        if serial in seen:
            return False
        seen[serial] = location
    return True


def _register_pokemon(seen: dict[int, str], row: tuple[Any, ...], location: str) -> bool:
    # top, attached Energy, Tools and lineage are physical cards.  The lineage
    # key repeats a root serial by design and is not separately registered.
    for suffix, value in (
        ("top", row[1]),
        ("energy", row[6]),
        ("tools", row[7]),
        ("lineage", row[8]),
    ):
        if not _register_serials(seen, value, f"{location}/{suffix}"):
            return False
    return True


def public_snapshot(parent: Any, obs: Any):
    state = getattr(obs, "current", None)
    select = getattr(obs, "select", None)
    if state is None or select is None or len(getattr(state, "players", ())) != 2:
        return None
    owner = getattr(state, "yourIndex", None)
    if owner not in (0, 1):
        return None
    players = []
    seen: dict[int, str] = {}
    for index, player in enumerate(state.players):
        active = tuple(pokemon_row(pokemon, index) for pokemon in (player.active or []))
        bench = tuple(pokemon_row(pokemon, index) for pokemon in (player.bench or []))
        discard = base._zone_rows(player.discard)
        lost = base._zone_rows(getattr(player, "lost", None) or [])
        if any(row is None for row in active + bench) or discard is None or lost is None:
            return None
        if any(not _register_pokemon(seen, row, f"p{index}/active/{pos}") for pos, row in enumerate(active)):
            return None
        if any(not _register_pokemon(seen, row, f"p{index}/bench/{pos}") for pos, row in enumerate(bench)):
            return None
        if not _register_serials(seen, discard, f"p{index}/discard"):
            return None
        if not _register_serials(seen, lost, f"p{index}/lost"):
            return None
        hand_count = getattr(player, "handCount", None)
        deck_count = getattr(player, "deckCount", None)
        if not _valid_int(hand_count) or hand_count < 0 or not _valid_int(deck_count) or deck_count < 0:
            return None
        row = {
            "index": index,
            "active": active,
            "bench": bench,
            "discard": discard,
            "lost": lost,
            "prize_count": len(player.prize),
            "hand_count": hand_count,
            "deck_count": deck_count,
            "bench_max": player.benchMax,
            "status": (
                bool(player.poisoned),
                bool(player.burned),
                bool(player.asleep),
                bool(player.paralyzed),
                bool(player.confused),
            ),
        }
        if index == owner:
            hand = base._zone_rows(player.hand)
            if hand is None or len(hand) != hand_count or not _register_serials(seen, hand, f"p{index}/hand"):
                return None
            row["hand"] = hand
        players.append(row)
    stadium = base._zone_rows(state.stadium)
    if stadium is None or not _register_serials(seen, stadium, "stadium"):
        return None
    effect = base.card_row(select.effect)
    context_card = base.card_row(select.contextCard)
    # Effect/context cards are prompt references and may alias a registered
    # physical card; they are canonicalized but intentionally not registered.
    option_keys = tuple(
        sorted(
            (base.stable_option_key(parent, obs, option) for option in select.option),
            key=repr,
        )
    )
    payload = {
        "version": base.INTEGRATED_VERSION,
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
            "type": base.enum_int(select.type),
            "context": base.enum_int(select.context),
            "min": select.minCount,
            "max": select.maxCount,
            "remaining_damage": select.remainDamageCounter,
            "remaining_energy": select.remainEnergyCost,
            "effect": effect,
            "context_card": context_card,
            "options": option_keys,
        },
        "logs": tuple(base._log_row(log) for log in obs.logs),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest().upper()
    return base.PublicSnapshot(payload, canonical, digest)


def install() -> None:
    base.pokemon_row = pokemon_row
    base.public_snapshot = public_snapshot

