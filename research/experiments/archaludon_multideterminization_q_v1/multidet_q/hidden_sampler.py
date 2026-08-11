"""Deterministic, counter-checked hidden-zone sampling for search roots."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import random
from typing import Any, Mapping, Sequence


class DeterminizationError(RuntimeError):
    """The sampled hidden state cannot represent the supplied decks."""


class UnsupportedRootSurface(RuntimeError):
    """The branch root is outside the supported MAIN public surface."""


@dataclass(frozen=True)
class HiddenZones:
    your_deck: tuple[int, ...]
    your_prize: tuple[int, ...]
    opponent_deck: tuple[int, ...]
    opponent_prize: tuple[int, ...]
    opponent_hand: tuple[int, ...]
    opponent_active: tuple[int, ...]
    determinization_seed: int
    fingerprint: str


def determinization_seed(branch_group_id: str, rollout_index: int) -> int:
    payload = f"{branch_group_id}|{int(rollout_index)}|public-determinization-v1"
    return int(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16], 16)


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    raw = getattr(value, "value", value)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _card_id(card: Any) -> int | None:
    return _int(_get(card, "id")) if card is not None else None


def _player_index(card: Any) -> int | None:
    return _int(_get(card, "playerIndex")) if card is not None else None


def _add_card(counter: Counter[int], card: Any, seen: set[int], *, owner: int, label: str) -> None:
    if card is None:
        return
    serial = _int(_get(card, "serial"))
    if serial is not None:
        if serial in seen:
            return
        seen.add(serial)
    card_id = _card_id(card)
    if card_id is None:
        raise DeterminizationError(f"visible card has no id in {label}")
    counter[int(card_id)] += 1


def _add_pokemon(counter: Counter[int], pokemon: Any, seen: set[int], *, owner: int, label: str) -> None:
    if pokemon is None:
        return
    _add_card(counter, pokemon, seen, owner=owner, label=f"{label}.pokemon")
    for field in ("preEvolution", "energyCards", "tools"):
        for card in (_get(pokemon, field, ()) or ()):
            _add_card(counter, card, seen, owner=owner, label=f"{label}.{field}")


def _visible_counters(observation: Any, your_index: int) -> tuple[list[Counter[int]], list[set[tuple[str, int]]]]:
    current = _get(observation, "current")
    players = list(_get(current, "players", ()) or ())
    if len(players) != 2:
        raise DeterminizationError("current.players must contain two players")
    counters = [Counter(), Counter()]
    seen: list[set[int]] = [set(), set()]
    for owner, player in enumerate(players):
        for pokemon in (_get(player, "active", ()) or ()):
            _add_pokemon(counters[owner], pokemon, seen[owner], owner=owner, label=f"player{owner}.active")
        for index, pokemon in enumerate(_get(player, "bench", ()) or ()):
            _add_pokemon(counters[owner], pokemon, seen[owner], owner=owner, label=f"player{owner}.bench{index}")
        for card in (_get(player, "discard", ()) or ()):
            _add_card(counters[owner], card, seen[owner], owner=owner, label=f"player{owner}.discard")
        hand = _get(player, "hand", None)
        if hand is not None:
            for card in hand:
                _add_card(counters[owner], card, seen[owner], owner=owner, label=f"player{owner}.hand")
        for card in (_get(player, "prize", ()) or ()):
            if card is not None:
                _add_card(counters[owner], card, seen[owner], owner=owner, label=f"player{owner}.prize")
    for card in (_get(current, "stadium", ()) or ()):
        owner = _player_index(card)
        if owner not in (0, 1):
            raise DeterminizationError("stadium card has no owner")
        _add_card(counters[owner], card, seen[owner], owner=owner, label="stadium")
    looking = _get(current, "looking", None)
    if looking not in (None, ()) and list(looking or ()):
        raise UnsupportedRootSurface("current.looking is not empty")
    return counters, seen


def _basic_card_ids(api_module: Any) -> set[int]:
    try:
        return {
            int(_get(card, "cardId"))
            for card in api_module.all_card_data()
            if bool(_get(card, "basic", False))
        }
    except Exception as exc:  # pragma: no cover - exercised by integration gate
        raise DeterminizationError(f"cannot read all_card_data: {exc}") from exc


def _fill_prize(known: Sequence[Any], sampled: list[int]) -> tuple[int, ...]:
    result: list[int | None] = [None if card is None else _card_id(card) for card in known]
    positions = [index for index, card in enumerate(result) if card is None]
    if len(positions) > len(sampled):
        raise DeterminizationError("not enough sampled cards for prize")
    for index, card_id in zip(positions, sampled):
        result[index] = int(card_id)
    if any(card is None for card in result):
        raise DeterminizationError("prize remains unresolved")
    return tuple(int(card) for card in result)


def _fingerprint(zones: Mapping[str, Sequence[int]]) -> str:
    payload = {name: [int(item) for item in values] for name, values in zones.items()}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def sample_hidden_zones(
    observation: Any,
    *,
    branch_group_id: str,
    rollout_index: int,
    your_deck: Sequence[int],
    opponent_deck: Sequence[int],
    api_module: Any,
) -> HiddenZones:
    """Sample all six hidden zones while preserving every 60-card Counter."""

    current = _get(observation, "current")
    select = _get(observation, "select")
    if current is None or select is None:
        raise UnsupportedRootSurface("branch root has no MAIN current/select")
    if _get(select, "deck", None) is not None:
        raise UnsupportedRootSurface("observation.select.deck is not None")
    looking = _get(current, "looking", None)
    if looking not in (None, ()) and list(looking or ()):
        raise UnsupportedRootSurface("observation.current.looking is not empty")
    your_index = _int(_get(current, "yourIndex"))
    if your_index not in (0, 1):
        raise DeterminizationError("current.yourIndex must be 0 or 1")
    players = list(_get(current, "players", ()) or ())
    if len(players) != 2:
        raise DeterminizationError("current.players must contain two players")
    your_player = players[your_index]
    opponent_player = players[1 - your_index]
    counters, _ = _visible_counters(observation, your_index)
    source_decks = [list(map(int, your_deck)), list(map(int, opponent_deck))]
    original = [Counter(source_decks[your_index]), Counter(source_decks[1 - your_index])]
    if any(sum(counter.values()) != 60 for counter in original):
        raise DeterminizationError("each supplied deck must contain 60 cards")

    seed = determinization_seed(branch_group_id, rollout_index)
    rng = random.Random(seed)
    remaining: list[list[int]] = [[], []]
    for owner in (your_index, 1 - your_index):
        remainder = original[owner] - counters[owner]
        if counters[owner] - original[owner]:
            raise DeterminizationError(f"visible cards exceed deck for player {owner}")
        values: list[int] = []
        for card_id, count in sorted(remainder.items()):
            values.extend([int(card_id)] * int(count))
        rng.shuffle(values)
        remaining[owner] = values

    your_prize_known = list(_get(your_player, "prize", ()) or ())
    opponent_prize_known = list(_get(opponent_player, "prize", ()) or ())
    your_hidden_prize = sum(card is None for card in your_prize_known)
    opponent_hidden_prize = sum(card is None for card in opponent_prize_known)
    opponent_active_known = list(_get(opponent_player, "active", ()) or ())
    opponent_hidden_active = sum(card is None for card in opponent_active_known)
    if opponent_hidden_active > 1:
        raise DeterminizationError("more than one face-down opponent active")

    your_deck_count = _int(_get(your_player, "deckCount"), -1)
    opponent_deck_count = _int(_get(opponent_player, "deckCount"), -1)
    your_hand = list(_get(your_player, "hand", ()) or ())
    opponent_hand_count = _int(_get(opponent_player, "handCount"), -1)
    if your_deck_count < 0 or opponent_deck_count < 0 or opponent_hand_count < 0:
        raise DeterminizationError("invalid zone count")

    your_unknown_count = int(your_deck_count) + your_hidden_prize
    if len(remaining[your_index]) != your_unknown_count:
        raise DeterminizationError(
            f"your hidden count mismatch: remaining={len(remaining[your_index])} expected={your_unknown_count}"
        )
    your_prize_values = remaining[your_index][:your_hidden_prize]
    your_deck_values = remaining[your_index][your_hidden_prize:]

    opponent_unknown_count = int(opponent_hand_count) + int(opponent_deck_count) + opponent_hidden_prize + opponent_hidden_active
    if len(remaining[1 - your_index]) != opponent_unknown_count:
        raise DeterminizationError(
            f"opponent hidden count mismatch: remaining={len(remaining[1 - your_index])} expected={opponent_unknown_count}"
        )
    opponent_values = remaining[1 - your_index]
    cursor = 0
    opponent_active_values: list[int] = []
    if opponent_hidden_active:
        basics = _basic_card_ids(api_module)
        basic_positions = [index for index, card_id in enumerate(opponent_values[cursor:]) if card_id in basics]
        if not basic_positions:
            raise DeterminizationError("no Basic Pokémon available for face-down active")
        selected = basic_positions[0] + cursor
        opponent_active_values = [opponent_values.pop(selected)]
        cursor = 0
    opponent_hand_values = opponent_values[cursor:cursor + int(opponent_hand_count)]
    cursor += int(opponent_hand_count)
    opponent_prize_values = opponent_values[cursor:cursor + opponent_hidden_prize]
    cursor += opponent_hidden_prize
    opponent_deck_values = opponent_values[cursor:]
    if len(opponent_hand_values) != opponent_hand_count or len(opponent_deck_values) != opponent_deck_count:
        raise DeterminizationError("opponent hidden zone allocation count mismatch")

    your_prize = _fill_prize(your_prize_known, your_prize_values)
    opponent_prize = _fill_prize(opponent_prize_known, opponent_prize_values)
    if len(your_hand) != _int(_get(your_player, "handCount"), -1):
        raise DeterminizationError("your hand count mismatch")
    zones = {
        "your_deck": tuple(your_deck_values),
        "your_prize": your_prize,
        "opponent_deck": tuple(opponent_deck_values),
        "opponent_prize": opponent_prize,
        "opponent_hand": tuple(opponent_hand_values),
        "opponent_active": tuple(opponent_active_values),
    }
    for owner, zone_values in (
        (your_index, zones["your_deck"] + zones["your_prize"]),
        (1 - your_index, zones["opponent_deck"] + zones["opponent_prize"] + zones["opponent_hand"] + zones["opponent_active"]),
    ):
        if counters[owner] + Counter(zone_values) != original[owner]:
            raise DeterminizationError(f"deck Counter mismatch for player {owner}")
    return HiddenZones(
        your_deck=tuple(zones["your_deck"]),
        your_prize=tuple(zones["your_prize"]),
        opponent_deck=tuple(zones["opponent_deck"]),
        opponent_prize=tuple(zones["opponent_prize"]),
        opponent_hand=tuple(zones["opponent_hand"]),
        opponent_active=tuple(zones["opponent_active"]),
        determinization_seed=int(seed),
        fingerprint=_fingerprint(zones),
    )


__all__ = [
    "DeterminizationError",
    "HiddenZones",
    "UnsupportedRootSurface",
    "determinization_seed",
    "sample_hidden_zones",
]
