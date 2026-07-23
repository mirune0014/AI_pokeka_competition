"""Leakage-safe acting-player reconstruction for public Kaggle replays."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
import json
from typing import Any, Iterable, Iterator, Mapping, Sequence

from .canonical_actions import CanonicalPromptAction, CanonicalTransaction, canonicalize_prompt_action


_PUBLIC_EVENT_TYPES = {
    "TurnStart",
    "TurnEnd",
    "Shuffle",
    "HasBasicPokemon",
    "Play",
    "Attack",
    "Attach",
    "Evolve",
    "Switch",
    "HpChange",
    "Result",
}
_PUBLIC_ZONE_CODES = frozenset({3, 4, 5, 7})
_ZONE_NAMES = {
    1: "deck",
    2: "hand",
    3: "discard",
    4: "active",
    5: "bench",
    6: "prize",
    7: "stadium",
    12: "looking",
}


def _get(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, Mapping) else getattr(value, name, default)


def _items(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _integer(value: Any, default: int | None = None) -> int | None:
    try:
        raw = value.value if hasattr(value, "value") else value
        if isinstance(raw, bool):
            return default
        return int(raw)
    except (TypeError, ValueError):
        return default


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if value == value and abs(value) != float("inf") else str(value)
    enum_value = getattr(value, "value", None)
    if enum_value is not None and enum_value is not value:
        return _json_value(enum_value)
    return str(value)


def _stable_id(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return blake2b(encoded, digest_size=32).hexdigest()


def _relation(value: Any, actor_seat: int) -> str | None:
    seat = _integer(value)
    if seat is None:
        return None
    if seat == actor_seat:
        return "self"
    if seat >= 0:
        return "opponent"
    return None


def _zone(value: Any) -> str:
    code = _integer(value)
    return _ZONE_NAMES.get(code, f"area:{code}" if code is not None else "area:unknown")


def project_public_event(log: Any, actor_seat: int) -> dict[str, Any] | None:
    """Project one visualizer log onto information public before a decision.

    Exact draw identities, private-only moves, serials, and internal coordinates
    are deliberately omitted. Unknown event types fail closed.
    """
    if not isinstance(log, Mapping):
        return None
    kind = str(log.get("type", ""))
    player = _relation(log.get("playerIndex"), actor_seat)
    if kind == "Draw":
        return {"type": "Draw", "player": player} if player is not None else None
    if kind == "MoveCard":
        from_code, to_code = _integer(log.get("fromArea")), _integer(log.get("toArea"))
        if from_code not in _PUBLIC_ZONE_CODES and to_code not in _PUBLIC_ZONE_CODES:
            return None
        result = {
            "type": kind,
            "player": player,
            "card_id": _json_value(log.get("cardId")),
            "from_zone": _zone(from_code),
            "to_zone": _zone(to_code),
        }
        return {key: value for key, value in result.items() if value is not None}
    if kind not in _PUBLIC_EVENT_TYPES:
        return None

    result: dict[str, Any] = {"type": kind}
    if player is not None:
        result["player"] = player
    allowed_fields = {
        "HasBasicPokemon": ("hasBasicPokemon",),
        "Play": ("cardId",),
        "Attack": ("cardId", "attackId"),
        "Attach": ("cardId", "cardIdTarget"),
        "Evolve": ("cardId", "cardIdTarget"),
        "Switch": ("cardIdActive", "cardIdBench"),
        "HpChange": ("cardId", "value", "putDamageCounter"),
        "Result": ("reason",),
    }
    aliases = {
        "hasBasicPokemon": "has_basic_pokemon",
        "cardId": "card_id",
        "attackId": "attack_id",
        "cardIdTarget": "target_card_id",
        "cardIdActive": "active_card_id",
        "cardIdBench": "bench_card_id",
        "putDamageCounter": "put_damage_counter",
    }
    for name in allowed_fields.get(kind, ()):
        value = log.get(name)
        if value is not None:
            result[aliases.get(name, name)] = _json_value(value)
    if kind == "Result":
        result["winner"] = _relation(log.get("result"), actor_seat) or "draw"
    return result


def _visual_frames(replay: Mapping[str, Any]) -> list[Any]:
    steps = _items(replay.get("steps"))
    if not steps:
        return []
    first_step = _items(steps[0])
    if not first_step or not isinstance(first_step[0], Mapping):
        return []
    return _items(first_step[0].get("visualize"))


def public_history_before(replay: Mapping[str, Any], replay_step: int, actor_seat: int) -> tuple[dict[str, Any], ...]:
    """Return only projected log events from frames strictly before a decision."""
    if replay_step < 0:
        raise ValueError("replay_step must be non-negative")
    history: list[dict[str, Any]] = []
    for frame in _visual_frames(replay)[:replay_step]:
        if not isinstance(frame, Mapping):
            continue
        # Never inspect frame.current/obs/select/selected: they are exact-hidden
        # visualizer state, not the acting player's information set.
        for log in _items(frame.get("logs")):
            event = project_public_event(log, actor_seat)
            if event is not None:
                history.append(event)
    return tuple(history)


@dataclass(frozen=True)
class ReplayDecision:
    episode_id: str
    replay_step: int
    action_step: int
    acting_seat: int
    turn: int | None
    observation: Mapping[str, Any]
    raw_action: tuple[int, ...]
    canonical_action: CanonicalPromptAction
    public_history: tuple[dict[str, Any], ...]
    private_action_history: tuple[CanonicalPromptAction, ...]


def _valid_decision(observation: Any, action: Any, seat: int) -> bool:
    if not isinstance(observation, Mapping) or not isinstance(action, list) or not action:
        return False
    current = observation.get("current") or {}
    select = observation.get("select") or {}
    options = _items(select.get("option", select.get("options", [])))
    if current.get("result") not in (None, -1) or _integer(current.get("yourIndex")) != seat or not options:
        return False
    if any(_integer(value) != value or isinstance(value, bool) or not 0 <= value < len(options) for value in action):
        return False
    if len(set(action)) != len(action):
        return False
    minimum = _integer(select.get("minCount", select.get("min_count", 0)), 0)
    maximum = _integer(select.get("maxCount", select.get("max_count", len(options))), len(options))
    return bool(minimum is not None and maximum is not None and minimum <= len(action) <= maximum)


def iter_replay_decisions(
    replay: Mapping[str, Any],
    seats: Sequence[int] | None = None,
) -> Iterator[ReplayDecision]:
    """Yield acting-player decisions using the replay's one-step action lag."""
    steps = _items(replay.get("steps"))
    episode_id = str((replay.get("info") or {}).get("EpisodeId") or "unknown")
    allowed = None if seats is None else {int(seat) for seat in seats}
    private_history: dict[int, list[CanonicalPromptAction]] = {}
    for replay_step in range(max(0, len(steps) - 1)):
        current_step, action_step = _items(steps[replay_step]), _items(steps[replay_step + 1])
        for seat in range(min(len(current_step), len(action_step))):
            if allowed is not None and seat not in allowed:
                continue
            current_record, following_record = current_step[seat], action_step[seat]
            observation = current_record.get("observation") if isinstance(current_record, Mapping) else None
            action = following_record.get("action") if isinstance(following_record, Mapping) else None
            if not _valid_decision(observation, action, seat):
                continue
            current = observation.get("current") or {}
            canonical = canonicalize_prompt_action(observation, action)
            yield ReplayDecision(
                episode_id=episode_id,
                replay_step=replay_step,
                action_step=replay_step + 1,
                acting_seat=seat,
                turn=_integer(current.get("turn")),
                observation=observation,
                raw_action=tuple(action),
                canonical_action=canonical,
                public_history=public_history_before(replay, replay_step, seat),
                private_action_history=tuple(private_history.get(seat, ())),
            )
            private_history.setdefault(seat, []).append(canonical)


def is_main_menu_prompt(observation: Mapping[str, Any]) -> bool:
    select = observation.get("select") or {}
    if _integer(select.get("context")) != 0 or _integer(select.get("type")) != 0:
        return False
    if select.get("effect") or select.get("contextCard") or select.get("context_card"):
        return False
    return any(_integer(option.get("type")) == 14 for option in _items(select.get("option")) if isinstance(option, Mapping))


@dataclass(frozen=True)
class ReplayTransaction:
    transaction_id: str
    episode_id: str
    acting_seat: int
    turn: int | None
    root_replay_step: int
    replay_steps: tuple[int, ...]
    orphan_prompt_transaction: bool
    canonical_transaction: CanonicalTransaction

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "episode_id": self.episode_id,
            "acting_seat": self.acting_seat,
            "turn": self.turn,
            "root_replay_step": self.root_replay_step,
            "replay_steps": list(self.replay_steps),
            "orphan_prompt_transaction": self.orphan_prompt_transaction,
            "canonical_transaction": self.canonical_transaction.to_dict(),
        }


def _make_transaction(decisions: list[ReplayDecision], orphan: bool) -> ReplayTransaction:
    transaction = CanonicalTransaction(tuple(decision.canonical_action for decision in decisions))
    payload = {
        "episode_id": decisions[0].episode_id,
        "acting_seat": decisions[0].acting_seat,
        "turn": decisions[0].turn,
        "root_replay_step": decisions[0].replay_step,
        "replay_steps": [decision.replay_step for decision in decisions],
        "orphan": orphan,
        "canonical_transaction_id": transaction.stable_id,
    }
    return ReplayTransaction(
        transaction_id=_stable_id(payload),
        episode_id=decisions[0].episode_id,
        acting_seat=decisions[0].acting_seat,
        turn=decisions[0].turn,
        root_replay_step=decisions[0].replay_step,
        replay_steps=tuple(decision.replay_step for decision in decisions),
        orphan_prompt_transaction=orphan,
        canonical_transaction=transaction,
    )


def group_replay_transactions(decisions: Iterable[ReplayDecision]) -> tuple[ReplayTransaction, ...]:
    """Group causally adjacent prompts without exposing child prompts to roots."""
    output: list[ReplayTransaction] = []
    current: list[ReplayDecision] = []
    orphan = False
    for decision in decisions:
        root = is_main_menu_prompt(decision.observation)
        contiguous = bool(current) and (
            decision.episode_id == current[-1].episode_id
            and decision.acting_seat == current[-1].acting_seat
            and decision.turn == current[-1].turn
            and decision.replay_step == current[-1].replay_step + 1
        )
        if current and (root or not contiguous):
            output.append(_make_transaction(current, orphan))
            current = []
        if not current:
            orphan = not root
        current.append(decision)
    if current:
        output.append(_make_transaction(current, orphan))
    return tuple(output)
