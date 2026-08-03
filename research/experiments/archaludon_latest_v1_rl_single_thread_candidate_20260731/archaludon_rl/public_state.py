"""Whitelist-only canonical public observation projection."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import hashlib
import json
from typing import Any, Mapping


SCHEMA_VERSION = "public-state-v1"
_MISSING = object()


def get_field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def enum_int(value: Any) -> int | None:
    if value is None:
        return None
    raw = getattr(value, "value", value)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _relative_player(player_index: Any, your_index: int) -> int | None:
    candidate = enum_int(player_index)
    if candidate not in (0, 1):
        return None
    return 0 if candidate == your_index else 1


def _card(card: Any, your_index: int) -> dict[str, Any] | None:
    if card is None:
        return None
    card_id = enum_int(get_field(card, "id"))
    if card_id is None:
        return None
    result: dict[str, Any] = {"id": card_id}
    owner = _relative_player(get_field(card, "playerIndex"), your_index)
    if owner is not None:
        result["owner"] = owner
    return result


def _pokemon(pokemon: Any, your_index: int) -> dict[str, Any] | None:
    if pokemon is None:
        return None
    result: dict[str, Any] = {
        "id": enum_int(get_field(pokemon, "id")),
        "hp": enum_int(get_field(pokemon, "hp")),
        "max_hp": enum_int(get_field(pokemon, "maxHp")),
        "appeared_this_turn": bool(get_field(pokemon, "appearThisTurn", False)),
        "energies": sorted(
            value
            for value in (
                enum_int(item) for item in (get_field(pokemon, "energies", ()) or ())
            )
            if value is not None
        ),
        "energy_cards": sorted(
            (item for item in (
                _card(card, your_index)
                for card in (get_field(pokemon, "energyCards", ()) or ())
            ) if item is not None),
            key=lambda item: (item["id"], item.get("owner", -1)),
        ),
        "tools": sorted(
            (item for item in (
                _card(card, your_index)
                for card in (get_field(pokemon, "tools", ()) or ())
            ) if item is not None),
            key=lambda item: (item["id"], item.get("owner", -1)),
        ),
        "pre_evolution": sorted(
            (item for item in (
                _card(card, your_index)
                for card in (get_field(pokemon, "preEvolution", ()) or ())
            ) if item is not None),
            key=lambda item: (item["id"], item.get("owner", -1)),
        ),
    }
    return result


def _player(player: Any, *, own: bool, your_index: int) -> dict[str, Any]:
    active = [
        _pokemon(item, your_index)
        for item in (get_field(player, "active", ()) or ())
    ]
    bench = [
        item
        for item in (
            _pokemon(card, your_index)
            for card in (get_field(player, "bench", ()) or ())
        )
        if item is not None
    ]
    discard = sorted(
        (
            item
            for item in (
                _card(card, your_index)
                for card in (get_field(player, "discard", ()) or ())
            )
            if item is not None
        ),
        key=lambda item: (item["id"], item.get("owner", -1)),
    )
    result: dict[str, Any] = {
        "active": active,
        "bench": bench,
        "bench_max": enum_int(get_field(player, "benchMax")),
        "deck_count": enum_int(get_field(player, "deckCount")),
        "discard": discard,
        # Prize identities are never projected, even when a fixture exposes them.
        "prize_count": len(get_field(player, "prize", ()) or ()),
        "hand_count": enum_int(get_field(player, "handCount")),
        "status": {
            name: bool(get_field(player, name, False))
            for name in ("poisoned", "burned", "asleep", "paralyzed", "confused")
        },
    }
    if own:
        hand = [
            item
            for item in (
                _card(card, your_index)
                for card in (get_field(player, "hand", ()) or ())
            )
            if item is not None
        ]
        # Hand order is not strategic state; option semantics identify acted cards.
        result["hand"] = sorted(
            hand, key=lambda item: (item["id"], item.get("owner", -1))
        )
    return result


_LOG_FIELDS = (
    "type",
    "cardId",
    "fromArea",
    "toArea",
    "cardIdActive",
    "cardIdBench",
    "cardIdBefore",
    "cardIdAfter",
    "cardIdTarget",
    "attackId",
    "value",
    "putDamageCounter",
    "isRecover",
    "head",
    "result",
    "reason",
)


def _log(entry: Any, your_index: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    owner = _relative_player(get_field(entry, "playerIndex"), your_index)
    if owner is not None:
        result["actor"] = owner
    for name in _LOG_FIELDS:
        value = get_field(entry, name, _MISSING)
        if value is _MISSING or value is None:
            continue
        key = {
            "cardId": "card_id",
            "fromArea": "from_area",
            "toArea": "to_area",
            "cardIdActive": "card_id_active",
            "cardIdBench": "card_id_bench",
            "cardIdBefore": "card_id_before",
            "cardIdAfter": "card_id_after",
            "cardIdTarget": "card_id_target",
            "attackId": "attack_id",
            "putDamageCounter": "put_damage_counter",
            "isRecover": "is_recover",
        }.get(name, name)
        result[key] = value if isinstance(value, bool) else enum_int(value)
    return result


def project_public_state(observation: Any) -> dict[str, Any]:
    current = get_field(observation, "current")
    select = get_field(observation, "select")
    if current is None:
        return {
            "schema_version": SCHEMA_VERSION,
            "deck_request": select is None,
            "logs": [],
        }
    your_index = enum_int(get_field(current, "yourIndex"))
    if your_index not in (0, 1):
        raise ValueError("current.yourIndex must be 0 or 1")
    players = list(get_field(current, "players", ()) or ())
    if len(players) != 2:
        raise ValueError("current.players must contain exactly two players")
    option_types: dict[str, int] = {}
    for option in (get_field(select, "option", ()) or ()):
        key = str(enum_int(get_field(option, "type")))
        option_types[key] = option_types.get(key, 0) + 1
    stadium = sorted(
        (
            item
            for item in (
                _card(card, your_index)
                for card in (get_field(current, "stadium", ()) or ())
            )
            if item is not None
        ),
        key=lambda item: (item["id"], item.get("owner", -1)),
    )
    looking = sorted(
        (
            item
            for item in (
                _card(card, your_index)
                for card in (get_field(current, "looking", ()) or ())
            )
            if item is not None
        ),
        key=lambda item: (item["id"], item.get("owner", -1)),
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "deck_request": False,
        "turn": enum_int(get_field(current, "turn")),
        "turn_action_count": enum_int(get_field(current, "turnActionCount")),
        "first_player_relative": _relative_player(
            get_field(current, "firstPlayer"), your_index
        ),
        "supporter_played": bool(get_field(current, "supporterPlayed", False)),
        "stadium_played": bool(get_field(current, "stadiumPlayed", False)),
        "energy_attached": bool(get_field(current, "energyAttached", False)),
        "retreated": bool(get_field(current, "retreated", False)),
        "result_relative": (
            -1
            if enum_int(get_field(current, "result")) == -1
            else _relative_player(get_field(current, "result"), your_index)
        ),
        "stadium": stadium,
        "looking_visible": looking,
        "players": [
            _player(players[your_index], own=True, your_index=your_index),
            _player(players[1 - your_index], own=False, your_index=your_index),
        ],
        "select": (
            None
            if select is None
            else {
                "type": enum_int(get_field(select, "type")),
                "context": enum_int(get_field(select, "context")),
                "min_count": enum_int(get_field(select, "minCount")),
                "max_count": enum_int(get_field(select, "maxCount")),
                "remain_damage_counter": enum_int(
                    get_field(select, "remainDamageCounter")
                ),
                "remain_energy_cost": enum_int(
                    get_field(select, "remainEnergyCost")
                ),
                "option_type_counts": dict(sorted(option_types.items())),
                "option_count": len(get_field(select, "option", ()) or ()),
                "context_card": _card(
                    get_field(select, "contextCard"), your_index
                ),
                "effect": _card(get_field(select, "effect"), your_index),
            }
        ),
        "logs": [
            _log(entry, your_index)
            for entry in (get_field(observation, "logs", ()) or ())
        ],
    }


def canonical_public_bytes(observation_or_projection: Any) -> bytes:
    if (
        isinstance(observation_or_projection, Mapping)
        and observation_or_projection.get("schema_version") == SCHEMA_VERSION
    ):
        projection = observation_or_projection
    else:
        projection = project_public_state(observation_or_projection)
    return json.dumps(
        projection,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def public_state_hash(observation_or_projection: Any) -> str:
    return hashlib.sha256(canonical_public_bytes(observation_or_projection)).hexdigest()


def raw_observation_hash(observation: Any) -> str:
    """Hash the full caller payload without retaining it in trajectory data."""

    if is_dataclass(observation):
        value = asdict(observation)
    elif isinstance(observation, Mapping):
        value = observation
    else:
        value = vars(observation)

    def normalize(item: Any) -> Any:
        if is_dataclass(item):
            return normalize(asdict(item))
        if isinstance(item, Mapping):
            return {str(key): normalize(val) for key, val in item.items()}
        if isinstance(item, (list, tuple)):
            return [normalize(val) for val in item]
        raw = getattr(item, "value", item)
        if isinstance(raw, (str, int, float, bool)) or raw is None:
            return raw
        return repr(raw)

    payload = json.dumps(
        normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
