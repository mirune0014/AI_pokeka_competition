"""Versioned, acting-player-safe records for Gold replay distillation."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from hashlib import blake2b
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .canonical_actions import CanonicalPromptAction, canonicalize_option, canonicalize_prompt_action, resolve_prompt_action
from .public_state import canonical_public_state


SCHEMA_VERSION = "gold_replay_decision.v1"
LABEL_SOURCES = frozenset({"observed_replay", "belief_teacher", "exact_hidden_diagnostic"})
POLICY_LABEL_SOURCES = frozenset({"observed_replay", "belief_teacher"})
_RAW_KEYS = frozenset({"index", "serial", "ordinal", "optionIndex", "option_index", "rawOption", "raw_option"})


def _get(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, Mapping) else getattr(value, name, default)


def _items(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if value == value and abs(value) != float("inf") else str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    enum_value = getattr(value, "value", None)
    if enum_value is not None and enum_value is not value:
        return _json_value(enum_value)
    attributes = getattr(value, "__dict__", None)
    if isinstance(attributes, dict):
        return _json_value(attributes)
    return str(value)


def _canonical_json(value: Any) -> str:
    return json.dumps(_json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _stable_id(value: Any) -> str:
    return blake2b(_canonical_json(value).encode("ascii"), digest_size=32).hexdigest()


def _seat(observation: Any) -> int:
    current = _get(observation, "current", observation) or {}
    value = _get(current, "yourIndex", _get(current, "your_index", 0))
    try:
        return int(getattr(value, "value", value))
    except (TypeError, ValueError):
        raise ValueError("observation must expose an integer acting yourIndex") from None


def _remove_raw(value: Any) -> Any:
    """Recursively remove engine coordinates from a public payload."""
    if isinstance(value, Mapping):
        return {str(key): _remove_raw(item) for key, item in value.items() if str(key) not in _RAW_KEYS}
    if isinstance(value, (list, tuple)):
        return [_remove_raw(item) for item in value]
    return _json_value(value)


def _normalize_history(value: Any, acting_seat: int) -> Any:
    """Keep caller-provided history public and stable, without engine coordinates."""
    def normalize(item: Any, key: str | None = None) -> Any:
        if isinstance(item, Mapping) or isinstance(getattr(item, "__dict__", None), dict):
            source = item if isinstance(item, Mapping) else item.__dict__
            result: dict[str, Any] = {}
            for raw_key, raw_value in source.items():
                name = str(raw_key)
                lowered = name.lower()
                if lowered in {"player", "playerid", "player_id", "playerindex", "player_index", "seat", "owner"}:
                    try:
                        result[name] = "self" if int(getattr(raw_value, "value", raw_value)) == acting_seat else "opponent"
                    except (TypeError, ValueError):
                        result[name] = normalize(raw_value, name)
                elif name in _RAW_KEYS or "serial" in lowered or "index" in lowered or lowered.startswith("raw"):
                    continue
                else:
                    result[name] = normalize(raw_value, name)
            return result
        if isinstance(item, (list, tuple)):
            return [normalize(part, key) for part in item]
        return _json_value(item)
    return normalize(value)


def _known_card_ids(cards: Any, *, preserve_order: bool) -> list[Any]:
    values = []
    for card in _items(cards):
        identifier = _get(card, "id", _get(card, "cardId", _get(card, "card_id", None)))
        if identifier is not None:
            values.append(_json_value(identifier))
    return values if preserve_order else sorted(values, key=_canonical_json)


def _safe_observation(
    observation: Any,
    acting_seat: int,
    private_action_history: Iterable[CanonicalPromptAction | Mapping[str, Any]] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split public state from the actor's permitted private hand information."""
    state = canonical_public_state(observation, acting_seat)
    # Absolute seat numbers are replay coordinates, not strategic information.
    # Preserve first-player meaning relative to the actor before removing them.
    first_player = state.pop("firstPlayer", state.pop("first_player", None))
    state.pop("yourIndex", None)
    state.pop("your_index", None)
    state.pop("perspectiveSeat", None)
    if first_player is not None:
        try:
            state["firstPlayerRelation"] = "self" if int(first_player) == acting_seat else "opponent"
        except (TypeError, ValueError):
            state["firstPlayerRelation"] = _json_value(first_player)
    players = state.pop("players", [])
    own = players[acting_seat] if 0 <= acting_seat < len(players) else {}
    opponents = [player for index, player in enumerate(players) if index != acting_seat]
    own_hand = own.pop("hand", [])
    # The public_state module deliberately exposes the actor hand; place it in the
    # explicit private field so training callers cannot accidentally treat it as public.
    state["self"] = own
    state["opponents"] = opponents
    state.pop("select", None)  # semantic legal options are a separate schema field.
    known_private: dict[str, Any] = {"hand": _remove_raw(own_hand)}
    current = _get(observation, "current", observation) or {}
    select = _get(observation, "select", {}) or {}
    searchable_deck = _known_card_ids(_get(select, "deck", []), preserve_order=False)
    if searchable_deck:
        # A deck-search view reveals a multiset, not the hidden deck order.
        known_private["searchable_deck_multiset"] = searchable_deck
    looking = _known_card_ids(_get(current, "looking", []), preserve_order=True)
    if looking:
        # The acting player sees this ordered temporary zone directly.
        known_private["looking_order"] = looking
    history = tuple(_canonical_action(item).to_dict() for item in private_action_history)
    if history:
        known_private["private_action_history"] = list(history)
    return _remove_raw(state), known_private


def _action_from_dict(value: Mapping[str, Any]) -> CanonicalPromptAction:
    selections = value.get("selections")
    if not isinstance(selections, list):
        raise ValueError("canonical action selections must be a list")
    from .canonical_actions import CanonicalOption
    allowed = set(CanonicalOption.__dataclass_fields__)
    parsed = []
    for selection in selections:
        if not isinstance(selection, Mapping) or set(selection) != allowed:
            raise ValueError("canonical action selection has an invalid schema")
        parsed.append(CanonicalOption(**dict(selection)))
    expected = {"selection_context", "minimum_count", "maximum_count", "selections"}
    if set(value) != expected:
        raise ValueError("canonical action has an invalid schema")
    return CanonicalPromptAction(value["selection_context"], value["minimum_count"], value["maximum_count"], tuple(parsed))


def _canonical_action(value: Any) -> CanonicalPromptAction:
    if isinstance(value, CanonicalPromptAction):
        return value
    if isinstance(value, Mapping):
        return _action_from_dict(value)
    raise TypeError("canonical complete actions must be CanonicalPromptAction values or their dictionaries")


@dataclass(frozen=True)
class ReplayDecisionRecord:
    schema_version: str
    episode_id: str
    submission_id: str
    style_id: str
    decision_step: int
    replay_step: int
    turn: int | None
    acting_seat: int
    own_archetype: str | None
    opponent_archetype: str | None
    state_id: str
    decision_id: str
    safe_observation: dict[str, Any]
    known_private_info: dict[str, Any]
    public_history: Any
    legal_semantic_options: tuple[dict[str, Any], ...]
    canonical_complete_actions: tuple[dict[str, Any], ...] | None
    chosen_canonical_action: dict[str, Any]
    rule_scores: Any
    rule_ranks: Any
    terminal_result: Any
    timestamp: str
    source_metadata: dict[str, Any]
    label_source: str
    exact_hidden_diagnostics: Any = None

    @classmethod
    def from_observation(
        cls, observation: Any, raw_legal_action: Sequence[int], *, episode_id: str,
        submission_id: str, style_id: str, decision_step: int, replay_step: int,
        acting_seat: int | None = None, own_archetype: str | None = None,
        opponent_archetype: str | None = None, public_history: Any = (),
        private_action_history: Iterable[CanonicalPromptAction | Mapping[str, Any]] = (),
        canonical_complete_actions: Iterable[CanonicalPromptAction | Mapping[str, Any]] | None = None,
        rule_scores: Any = None, rule_ranks: Any = None, terminal_result: Any = None,
        timestamp: str | None = None, source_metadata: Mapping[str, Any] | None = None,
        label_source: str = "observed_replay", exact_hidden_diagnostics: Any = None,
    ) -> "ReplayDecisionRecord":
        observed_seat = _seat(observation)
        if acting_seat is not None and int(acting_seat) != observed_seat:
            raise ValueError("acting_seat must match observation yourIndex")
        if label_source not in LABEL_SOURCES:
            raise ValueError(f"unknown label_source: {label_source}")
        action = canonicalize_prompt_action(observation, raw_legal_action)
        safe_observation, known_private_info = _safe_observation(
            observation, observed_seat, private_action_history,
        )
        select = _get(observation, "select", {}) or {}
        options = _items(_get(select, "option", _get(select, "options", [])))
        # Legal choices form a multiset. Engine option order is an ephemeral
        # coordinate and must not affect a public state ID or model input.
        legal_options = tuple(sorted(
            (canonicalize_option(observation, option).to_dict() for option in options),
            key=_canonical_json,
        ))
        complete = None
        if canonical_complete_actions is not None:
            complete_actions = tuple(_canonical_action(item) for item in canonical_complete_actions)
            for candidate in complete_actions:
                resolve_prompt_action(observation, candidate)
            complete = tuple(item.to_dict() for item in complete_actions)
        history = _normalize_history(public_history, observed_seat)
        state_id = _stable_id({"safe_observation": safe_observation, "known_private_info": known_private_info,
                               "public_history": history, "legal_semantic_options": legal_options})
        decision_id = _stable_id({"episode_id": str(episode_id), "replay_step": int(replay_step),
                                  "state_id": state_id, "chosen_canonical_action": action.to_dict()})
        current = _get(observation, "current", observation) or {}
        return cls(
            SCHEMA_VERSION, str(episode_id), str(submission_id), str(style_id), int(decision_step), int(replay_step),
            _get(current, "turn", None), observed_seat, own_archetype, opponent_archetype, state_id, decision_id,
            safe_observation, known_private_info, history, legal_options, complete, action.to_dict(),
            _json_value(rule_scores), _json_value(rule_ranks), _json_value(terminal_result),
            timestamp or datetime.now(timezone.utc).isoformat(), _remove_raw(source_metadata or {}), label_source,
            _json_value(exact_hidden_diagnostics),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["legal_semantic_options"] = list(self.legal_semantic_options)
        if self.canonical_complete_actions is not None:
            data["canonical_complete_actions"] = list(self.canonical_complete_actions)
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReplayDecisionRecord":
        expected = {field.name for field in fields(cls)}
        if not isinstance(data, Mapping) or set(data) != expected:
            raise ValueError("invalid replay decision record schema")
        if data.get("schema_version") != SCHEMA_VERSION or data.get("label_source") not in LABEL_SOURCES:
            raise ValueError("unsupported replay decision record version or label source")
        normalized = dict(data)
        normalized["legal_semantic_options"] = tuple(normalized["legal_semantic_options"])
        if normalized["canonical_complete_actions"] is not None:
            normalized["canonical_complete_actions"] = tuple(normalized["canonical_complete_actions"])
        record = cls(**normalized)
        if not isinstance(record.legal_semantic_options, (list, tuple)) or not isinstance(record.chosen_canonical_action, Mapping):
            raise ValueError("invalid canonical action payload")
        _canonical_action(record.chosen_canonical_action)
        if record.canonical_complete_actions is not None:
            for action in record.canonical_complete_actions:
                _canonical_action(action)
        computed_state = _stable_id({"safe_observation": record.safe_observation, "known_private_info": record.known_private_info,
                                     "public_history": record.public_history, "legal_semantic_options": record.legal_semantic_options})
        computed_decision = _stable_id({"episode_id": record.episode_id, "replay_step": record.replay_step,
                                        "state_id": computed_state, "chosen_canonical_action": record.chosen_canonical_action})
        if record.state_id != computed_state or record.decision_id != computed_decision:
            raise ValueError("replay decision record IDs do not validate")
        return record


def write_jsonl(path: str | Path, records: Iterable[ReplayDecisionRecord]) -> None:
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            if not isinstance(record, ReplayDecisionRecord):
                raise TypeError("JSONL records must be ReplayDecisionRecord instances")
            handle.write(_canonical_json(record.to_dict()) + "\n")


def read_jsonl(path: str | Path) -> list[ReplayDecisionRecord]:
    records = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                records.append(ReplayDecisionRecord.from_dict(json.loads(line)))
            except (TypeError, ValueError, json.JSONDecodeError) as error:
                raise ValueError(f"invalid replay JSONL at line {line_number}: {error}") from error
    return records


def _policy_columns(record: ReplayDecisionRecord, include_terminal_result: bool) -> dict[str, Any]:
    if record.label_source not in POLICY_LABEL_SOURCES:
        raise ValueError("exact-hidden diagnostic labels are not valid policy training data")
    result = {
        "schema_version": record.schema_version, "episode_id": record.episode_id,
        "submission_id": record.submission_id, "style_id": record.style_id,
        "decision_step": record.decision_step, "replay_step": record.replay_step, "turn": record.turn,
        "acting_seat": record.acting_seat, "own_archetype": record.own_archetype,
        "opponent_archetype": record.opponent_archetype, "state_id": record.state_id,
        "decision_id": record.decision_id, "safe_observation": record.safe_observation,
        "known_private_info": record.known_private_info, "public_history": record.public_history,
        "legal_semantic_options": list(record.legal_semantic_options),
        "canonical_complete_actions": None if record.canonical_complete_actions is None else list(record.canonical_complete_actions),
        "chosen_canonical_action": record.chosen_canonical_action, "rule_scores": record.rule_scores,
        "rule_ranks": record.rule_ranks, "label_source": record.label_source,
    }
    if include_terminal_result:
        result["terminal_result"] = record.terminal_result
    return result


def load_policy_records(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    return [_policy_columns(record, False) for path in paths for record in read_jsonl(path)]


def load_value_records(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    return [_policy_columns(record, True) for path in paths for record in read_jsonl(path)]


def load_exact_hidden_diagnostics(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    return [record.to_dict() for path in paths for record in read_jsonl(path) if record.label_source == "exact_hidden_diagnostic"]


# Explicit aliases make intended consumers clear without coupling Phase 1 to trajectory.py.
load_policy_training_records = load_policy_records
load_value_training_records = load_value_records
load_diagnostic_records = load_exact_hidden_diagnostics
