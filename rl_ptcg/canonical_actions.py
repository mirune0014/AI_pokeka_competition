"""Stable semantic representations of legal PTCG prompt actions.

This module deliberately models one selection prompt at a time.  A replay-level
transaction boundary is not known yet; :class:`CanonicalTransaction` only gives
callers an immutable way to retain several independently canonicalized prompts.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import blake2b
import json
import math
from typing import Any, Iterable, Sequence


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _first(value: Any, names: Iterable[str], default: Any = None) -> Any:
    for name in names:
        found = _get(value, name, None)
        if found is not None:
            return found
    return default


def _items(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _json_value(value: Any) -> Any:
    """Convert values to deterministic JSON without object identity or repr()."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, dict):
        return {str(key): _json_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    enum_value = getattr(value, "value", None)
    if enum_value is not None and enum_value is not value:
        return _json_value(enum_value)
    attributes = getattr(value, "__dict__", None)
    if isinstance(attributes, dict):
        return {str(key): _json_value(attributes[key]) for key in sorted(attributes)}
    return str(value)


def _json_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _stable_id(value: Any) -> str:
    return blake2b(_json_key(value).encode("ascii"), digest_size=32).hexdigest()


def _int(value: Any, default: int = -1) -> int:
    try:
        raw = value.value if hasattr(value, "value") else value
        return int(raw)
    except (TypeError, ValueError):
        return default


def _card_id(card: Any) -> Any:
    if card is None:
        return None
    return _json_value(_first(card, ("id", "cardId", "card_id")))


_ZONE_KINDS = {
    1: "select_deck",
    2: "hand",
    3: "discard",
    4: "active",
    5: "bench",
    7: "stadium",
    12: "looking",
}


def _zone_kind(area: Any) -> str | None:
    return _ZONE_KINDS.get(_int(area))


def _acting_seat(observation: Any) -> int:
    current = _get(observation, "current", observation) or {}
    return _int(_first(current, ("yourIndex", "your_index")), 0)


def _relation(owner: Any, acting: int, zone: str | None) -> str | None:
    if zone in ("stadium", "select_deck", "looking"):
        return "shared"
    seat = _int(owner, acting)
    if seat == acting:
        return "self"
    return "opponent" if seat >= 0 else None


def _zone_cards(observation: Any, zone: str | None, owner: Any) -> list[Any]:
    current = _get(observation, "current", observation) or {}
    select = _get(observation, "select", {}) or {}
    acting = _acting_seat(observation)
    if zone == "select_deck":
        return _items(_get(select, "deck", []))
    if zone == "stadium":
        return _items(_get(current, "stadium", []))
    if zone == "looking":
        return _items(_get(current, "looking", []))
    players = _items(_get(current, "players", []))
    seat = _int(owner, acting)
    if not 0 <= seat < len(players):
        return []
    player = players[seat]
    if zone == "hand":
        # Opponent hands are intentionally not resolved from public observations.
        return _items(_get(player, "hand", [])) if seat == acting else []
    if zone == "discard":
        return _items(_first(player, ("discard", "discardPile", "discard_pile"), []))
    if zone == "active":
        return _items(_get(player, "active", []))
    if zone == "bench":
        return _items(_get(player, "bench", []))
    return []


def _card_at(observation: Any, area: Any, index: Any, owner: Any) -> tuple[str | None, str | None, Any]:
    zone = _zone_kind(area)
    acting = _acting_seat(observation)
    relation = _relation(owner, acting, zone)
    position = _int(index)
    cards = _zone_cards(observation, zone, owner)
    return zone, relation, cards[position] if 0 <= position < len(cards) else None


def _option_source(observation: Any, option: Any) -> tuple[str | None, str | None, Any]:
    action_type = _int(_get(option, "type"))
    area = _get(option, "area")
    # The engine represents playing a hand card without an explicit area.
    if action_type == 7 and area is None:
        area = 2
    owner = _first(option, ("playerIndex", "player_index"), _acting_seat(observation))
    zone, relation, card = _card_at(observation, area, _get(option, "index"), owner)
    if action_type in (4, 5, 6) and card is not None:
        attached_name = "tools" if action_type == 4 else "energyCards"
        attached_index_names = ("toolIndex", "tool_index") if action_type == 4 else ("energyIndex", "energy_index")
        attached = _items(_get(card, attached_name, []))
        attached_index = _int(_first(option, attached_index_names))
        card = attached[attached_index] if 0 <= attached_index < len(attached) else None
    return zone, relation, card


def _option_target(observation: Any, option: Any) -> tuple[str | None, str | None, Any]:
    area = _first(option, ("inPlayArea", "in_play_area", "targetArea", "target_area"))
    index = _first(option, ("inPlayIndex", "in_play_index", "targetIndex", "target_index"))
    owner = _first(option, ("inPlayPlayerIndex", "in_play_player_index", "targetPlayerIndex", "target_player_index"), _acting_seat(observation))
    return _card_at(observation, area, index, owner)


def _effect_source_id(select: Any, option: Any) -> Any:
    direct = _first(
        option,
        ("effectSourceId", "effect_source_id", "effectCardId", "effect_card_id", "fromCardId", "from_card_id"),
    )
    if direct is not None:
        return _json_value(direct)
    source = _first(select, ("effect", "contextCard", "context_card", "sourceCard", "source_card"))
    return _card_id(source)


def _remaining_cost(select: Any) -> dict[str, Any]:
    return {
        "damage_counter": _json_value(_first(select, ("remainDamageCounter", "remain_damage_counter"))),
        "energy": _json_value(_first(select, ("remainEnergyCost", "remain_energy_cost"))),
    }


@dataclass(frozen=True)
class CanonicalOption:
    """One legal option with all volatile engine coordinates removed."""

    action_type: Any
    selection_context: Any
    source_zone: str | None = None
    source_relation: str | None = None
    source_card_id: Any = None
    target_zone: str | None = None
    target_relation: str | None = None
    target_card_id: Any = None
    attack_id: Any = None
    effect_source_id: Any = None
    number: Any = None
    count: Any = None
    special_condition: Any = None
    remaining_cost: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    @property
    def stable_id(self) -> str:
        return _stable_id(self.to_dict())


def canonicalize_option(observation: Any, option: Any) -> CanonicalOption:
    """Canonicalize a currently legal option without ordinals, serials, or indices."""
    select = _get(observation, "select", {}) or {}
    source_zone, source_relation, source_card = _option_source(observation, option)
    target_zone, target_relation, target_card = _option_target(observation, option)
    source_id = _card_id(source_card)
    if source_id is None:
        source_id = _json_value(_first(option, ("cardId", "card_id", "sourceCardId", "source_card_id")))
    target_id = _card_id(target_card)
    if target_id is None:
        target = _first(option, ("targetCardId", "target_card_id", "targetId", "target_id", "targetCard", "target_card", "target"))
        target_id = _card_id(target) if not isinstance(target, (str, int, float)) else _json_value(target)
    return CanonicalOption(
        action_type=_json_value(_get(option, "type")),
        selection_context=_json_value(_get(select, "context")),
        source_zone=source_zone,
        source_relation=source_relation,
        source_card_id=source_id,
        target_zone=target_zone,
        target_relation=target_relation,
        target_card_id=target_id,
        attack_id=_json_value(_first(option, ("attackId", "attack_id"))),
        effect_source_id=_effect_source_id(select, option),
        number=_json_value(_get(option, "number")),
        count=_json_value(_get(option, "count")),
        special_condition=_json_value(_first(option, ("specialConditionType", "special_condition_type"))),
        remaining_cost=_remaining_cost(select),
    )


@dataclass(frozen=True)
class CanonicalPromptAction:
    """An order-invariant multiset of selections submitted to one prompt."""

    selection_context: Any
    minimum_count: Any
    maximum_count: Any
    selections: tuple[CanonicalOption, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection_context": self.selection_context,
            "minimum_count": self.minimum_count,
            "maximum_count": self.maximum_count,
            "selections": [item.to_dict() for item in self.selections],
        }

    @property
    def stable_id(self) -> str:
        return _stable_id(self.to_dict())


def _selection_bounds(observation: Any) -> tuple[int, int]:
    select = _get(observation, "select", {}) or {}
    options = _items(_first(select, ("option", "options"), []))
    return (
        _int(_first(select, ("minCount", "min_count")), 0),
        _int(_first(select, ("maxCount", "max_count")), len(options)),
    )


def canonicalize_prompt_action(observation: Any, action: Sequence[int]) -> CanonicalPromptAction:
    """Canonicalize legal-option indices as a deterministic semantic multiset."""
    if not isinstance(action, (list, tuple)):
        raise ValueError("action must be a list or tuple of legal option indices")
    select = _get(observation, "select", {}) or {}
    options = _items(_first(select, ("option", "options"), []))
    minimum, maximum = _selection_bounds(observation)
    if not minimum <= len(action) <= maximum:
        raise ValueError(f"invalid action size {len(action)}; expected {minimum}..{maximum}")
    if any(not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(options) for index in action):
        raise ValueError("action contains an unavailable legal option index")
    if len(set(action)) != len(action):
        raise ValueError("action selects the same legal option index more than once")
    selections = tuple(sorted((canonicalize_option(observation, options[index]) for index in action), key=lambda item: _json_key(item.to_dict())))
    return CanonicalPromptAction(_json_value(_get(select, "context")), minimum, maximum, selections)


def resolve_prompt_action(observation: Any, action: CanonicalPromptAction) -> list[int]:
    """Resolve a canonical prompt action against current legal options.

    Matches are consumed in ascending current option index, so duplicate semantic
    choices are deterministic while retaining their required multiplicity.
    """
    if not isinstance(action, CanonicalPromptAction):
        raise TypeError("action must be a CanonicalPromptAction")
    minimum, maximum = _selection_bounds(observation)
    if not minimum <= len(action.selections) <= maximum:
        raise ValueError(f"invalid action size {len(action.selections)} for current prompt; expected {minimum}..{maximum}")
    select = _get(observation, "select", {}) or {}
    current_context = _json_value(_get(select, "context"))
    if action.selection_context != current_context:
        raise ValueError("canonical action selection context is not currently legal")
    options = _items(_first(select, ("option", "options"), []))
    available: dict[str, list[int]] = defaultdict(list)
    for index, option in enumerate(options):
        available[_json_key(canonicalize_option(observation, option).to_dict())].append(index)
    required = Counter(_json_key(selection.to_dict()) for selection in action.selections)
    resolved: list[int] = []
    for key in sorted(required):
        matches = available.get(key, [])
        count = required[key]
        if len(matches) < count:
            raise ValueError(f"canonical action requires {count} matching legal option(s), but only {len(matches)} are available")
        resolved.extend(matches[:count])
    return resolved


@dataclass(frozen=True)
class CanonicalTransaction:
    """Immutable composition of prompt steps; not a claim about replay grouping."""

    steps: tuple[CanonicalPromptAction, ...] = ()

    def append(self, step: CanonicalPromptAction) -> "CanonicalTransaction":
        if not isinstance(step, CanonicalPromptAction):
            raise TypeError("transaction steps must be CanonicalPromptAction instances")
        return CanonicalTransaction(self.steps + (step,))

    def to_dict(self) -> dict[str, Any]:
        return {"steps": [step.to_dict() for step in self.steps]}

    @property
    def stable_id(self) -> str:
        return _stable_id(self.to_dict())


# Short aliases keep the public API convenient for replay-distillation callers.
canonicalize_action = canonicalize_prompt_action
resolve_action = resolve_prompt_action
