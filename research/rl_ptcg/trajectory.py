"""Canonical JSONL records for public PTCG policy/value trajectories."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Union

try:
    from .encoding import EncodedObservation, SCHEMA, encode_observation
except ImportError:
    from encoding import EncodedObservation, SCHEMA, encode_observation


JsonAction = Union[int, list[int], dict[str, Any], None]


@dataclass(frozen=True)
class TrajectoryRecord:
    episode_id: str
    step: int
    seat: int
    state_vector: list[float]
    option_vectors: list[list[float]]
    rule_scores: list[float]
    rule_action: JsonAction
    selected_action: JsonAction
    policy_target: bool = True
    value_weight: float = 1.0
    terminal: bool = False
    result: int | None = None
    reward: float | None = None
    matchup: str | None = None
    opponent: str | None = None
    opponent_deck: list[int] | None = None
    seed: int | None = None
    schema_version: str = SCHEMA.version

    def __post_init__(self) -> None:
        if self.step < 0:
            raise ValueError("step must be non-negative")
        if len(self.rule_scores) not in (0, len(self.option_vectors)):
            raise ValueError("rule_scores must be empty or match option_vectors")
        expected = len(SCHEMA.state_feature_names)
        if len(self.state_vector) != expected:
            raise ValueError("state_vector does not match the public encoding schema")
        option_size = len(SCHEMA.option_feature_names)
        if any(len(vector) != option_size for vector in self.option_vectors):
            raise ValueError("option vector does not match the public encoding schema")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TrajectoryRecord":
        return cls(**value)

    @classmethod
    def from_json(cls, value: str) -> "TrajectoryRecord":
        return cls.from_dict(json.loads(value))


def make_record(
    observation: Any,
    episode_id: str,
    step: int,
    rule_scores: Iterable[float] = (),
    rule_action: JsonAction = None,
    selected_action: JsonAction = None,
    terminal: bool = False,
    result: int | None = None,
    reward: float | None = None,
    matchup: str | None = None,
    opponent: str | None = None,
    opponent_deck: Iterable[int] | None = None,
    seed: int | None = None,
    perspective_seat: int | None = None,
    policy_target: bool = True,
) -> TrajectoryRecord:
    encoded: EncodedObservation = encode_observation(observation, perspective_seat)
    current = observation.get("current", {}) if isinstance(observation, dict) else getattr(observation, "current", {})
    current = current or {}
    acting_seat = current.get("yourIndex", 0) if isinstance(current, dict) else getattr(current, "yourIndex", 0)
    seat = acting_seat if perspective_seat is None else perspective_seat
    return TrajectoryRecord(
        episode_id=str(episode_id), step=int(step), seat=int(seat or 0),
        state_vector=encoded.state_vector, option_vectors=encoded.option_vectors,
        rule_scores=[float(score) for score in rule_scores], rule_action=rule_action,
        selected_action=selected_action, policy_target=bool(policy_target),
        terminal=bool(terminal), result=result,
        reward=None if reward is None else float(reward), matchup=matchup,
        opponent=opponent,
        opponent_deck=None if opponent_deck is None else [int(card_id) for card_id in opponent_deck],
        seed=seed, schema_version=encoded.schema_version,
    )


def write_jsonl(path: str | Path, records: Iterable[TrajectoryRecord]) -> None:
    with Path(path).open("w", encoding="ascii", newline="\n") as handle:
        for record in records:
            handle.write(record.to_json())
            handle.write("\n")


def read_jsonl(path: str | Path) -> list[TrajectoryRecord]:
    with Path(path).open("r", encoding="ascii") as handle:
        return [TrajectoryRecord.from_json(line) for line in handle if line.strip()]
