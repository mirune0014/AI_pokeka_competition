"""Deck-count-consistent hidden-zone sampling for Search API determinizations."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import random
from typing import Any, Iterable


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _items(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _card_id(card: Any) -> int | None:
    if card is None:
        return None
    value = _get(card, "id", _get(card, "cardId", None))
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _pokemon_cards(pokemon: Any) -> list[int]:
    if pokemon is None:
        return []
    result = []
    own_id = _card_id(pokemon)
    if own_id is not None:
        result.append(own_id)
    for name in ("tools", "energyCards", "energy_cards", "preEvolution", "pre_evolution"):
        value = _get(pokemon, name, [])
        values = value if isinstance(value, (list, tuple)) else [value]
        result.extend(card_id for card_id in (_card_id(card) for card in values) if card_id is not None)
    return result


def visible_player_cards(player: Any, include_hand: bool) -> tuple[list[int], list[int]]:
    """Return visible non-prize IDs and separately known prize IDs."""
    visible = []
    for pokemon in _items(_get(player, "active", [])) + _items(_get(player, "bench", [])):
        visible.extend(_pokemon_cards(pokemon))
    for zone in ("discard", "lostZone", "lost_zone"):
        visible.extend(card_id for card_id in (_card_id(card) for card in _items(_get(player, zone, [])))
                       if card_id is not None)
    if include_hand:
        visible.extend(card_id for card_id in (_card_id(card) for card in _items(_get(player, "hand", [])))
                       if card_id is not None)
    known_prize = [card_id for card_id in (_card_id(card) for card in _items(_get(player, "prize", [])))
                   if card_id is not None]
    return visible, known_prize


def _count(player: Any, count_name: str, zone_name: str) -> int:
    value = _get(player, count_name, None)
    if value is None:
        value = len(_items(_get(player, zone_name, [])))
    return int(value)


@dataclass(frozen=True)
class HiddenZones:
    deck: list[int]
    prize: list[int]
    hand: list[int]
    unused: list[int]


@dataclass(frozen=True)
class SearchGuess:
    your_deck: list[int]
    your_prize: list[int]
    opponent_deck: list[int]
    opponent_prize: list[int]
    opponent_hand: list[int]
    opponent_active: list[int]
    unused_your_cards: list[int]
    unused_opponent_cards: list[int]


def sample_hidden_zones(
    decklist: Iterable[int],
    visible: Iterable[int],
    known_prize: Iterable[int],
    deck_count: int,
    prize_count: int,
    hand_count: int,
    rng: random.Random,
) -> HiddenZones:
    known_prize = list(known_prize)
    remaining = Counter(int(card_id) for card_id in decklist)
    for card_id in list(visible) + known_prize:
        if remaining[int(card_id)] <= 0:
            raise ValueError("visible card count exceeds deck hypothesis: %s" % card_id)
        remaining[int(card_id)] -= 1
    pool = [card_id for card_id, count in remaining.items() for _ in range(count)]
    required = int(deck_count) + max(0, int(prize_count) - len(known_prize)) + int(hand_count)
    if len(pool) < required:
        raise ValueError("deck hypothesis has %d hidden cards; %d required" % (len(pool), required))
    rng.shuffle(pool)
    cursor = 0
    deck = pool[cursor:cursor + int(deck_count)]
    cursor += int(deck_count)
    hidden_prize_count = max(0, int(prize_count) - len(known_prize))
    prize = known_prize + pool[cursor:cursor + hidden_prize_count]
    cursor += hidden_prize_count
    hand = pool[cursor:cursor + int(hand_count)]
    cursor += int(hand_count)
    return HiddenZones(deck, prize, hand, pool[cursor:])


def compatible_deck_hypotheses(observation: Any, decklists: Iterable[Iterable[int]]) -> list[list[int]]:
    """Keep deck hypotheses that contain every publicly visible opponent card."""
    current = _get(observation, "current", {}) or {}
    players = _items(_get(current, "players", []))
    your_index = int(_get(current, "yourIndex", 0) or 0)
    if len(players) != 2:
        return []
    visible, known_prize = visible_player_cards(players[1 - your_index], include_hand=False)
    required = Counter(visible + known_prize)
    output = []
    seen = set()
    for decklist in decklists:
        deck = [int(card_id) for card_id in decklist]
        signature = tuple(sorted(deck))
        if signature in seen:
            continue
        seen.add(signature)
        counts = Counter(deck)
        if len(deck) == 60 and all(counts[card_id] >= count for card_id, count in required.items()):
            output.append(deck)
    return output


def sample_search_guess(
    observation: Any,
    your_decklist: Iterable[int],
    opponent_decklist: Iterable[int],
    rng: random.Random,
    basic_pokemon_ids: set[int] | None = None,
) -> SearchGuess:
    current = _get(observation, "current", {}) or {}
    players = _items(_get(current, "players", []))
    your_index = int(_get(current, "yourIndex", 0) or 0)
    if len(players) != 2:
        raise ValueError("search observation must have two players")
    yours = players[your_index]
    opponent = players[1 - your_index]
    your_visible, your_known_prize = visible_player_cards(yours, include_hand=True)
    opp_visible, opp_known_prize = visible_player_cards(opponent, include_hand=False)
    looking = [_card_id(card) for card in _items(_get(current, "looking", []))]
    your_visible.extend(card_id for card_id in looking if card_id is not None)
    stadium = _items(_get(current, "stadium", []))
    stadium_id = _card_id(stadium[0]) if stadium else None
    if stadium_id is not None:
        owner = None
        for log in reversed(_items(_get(observation, "logs", []))):
            if _card_id(log) == stadium_id and _get(log, "playerIndex", None) in (0, 1):
                owner = int(_get(log, "playerIndex"))
                break
        if owner is None:
            in_yours = stadium_id in set(int(card_id) for card_id in your_decklist)
            in_opponent = stadium_id in set(int(card_id) for card_id in opponent_decklist)
            if in_yours != in_opponent:
                owner = your_index if in_yours else 1 - your_index
        if owner == your_index:
            your_visible.append(stadium_id)
        elif owner == 1 - your_index:
            opp_visible.append(stadium_id)
    your_hidden = sample_hidden_zones(
        your_decklist, your_visible, your_known_prize,
        _count(yours, "deckCount", "deck"), len(_items(_get(yours, "prize", []))), 0, rng,
    )
    opp_hidden = sample_hidden_zones(
        opponent_decklist, opp_visible, opp_known_prize,
        _count(opponent, "deckCount", "deck"), len(_items(_get(opponent, "prize", []))),
        _count(opponent, "handCount", "hand"), rng,
    )
    active = _items(_get(opponent, "active", []))
    opponent_active: list[int] = []
    if active and active[0] is None:
        unused_candidates = [card_id for card_id in opp_hidden.unused
                             if not basic_pokemon_ids or card_id in basic_pokemon_ids]
        candidates = unused_candidates or [
            card_id for card_id in opp_hidden.hand + opp_hidden.deck
            if not basic_pokemon_ids or card_id in basic_pokemon_ids
        ]
        if not candidates:
            raise ValueError("no basic Pokemon candidate for face-down active")
        opponent_active = [rng.choice(candidates)]
    return SearchGuess(
        your_hidden.deck, your_hidden.prize, opp_hidden.deck, opp_hidden.prize,
        opp_hidden.hand, opponent_active, your_hidden.unused, opp_hidden.unused,
    )
