from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class MatchPhase(str, Enum):
    PREPARING = "PREPARING"
    STARTING = "STARTING"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    AGENT_THINKING = "AGENT_THINKING"
    ENGINE_PROCESSING = "ENGINE_PROCESSING"
    FINISHING = "FINISHING"
    FINISHED = "FINISHED"
    REPLAY_SEALED = "REPLAY_SEALED"
    ABORTED = "ABORTED"


ALLOWED_TRANSITIONS: dict[MatchPhase, set[MatchPhase]] = {
    MatchPhase.PREPARING: {MatchPhase.STARTING, MatchPhase.ABORTED},
    MatchPhase.STARTING: {MatchPhase.WAITING_FOR_HUMAN, MatchPhase.AGENT_THINKING, MatchPhase.FINISHING, MatchPhase.ABORTED},
    MatchPhase.WAITING_FOR_HUMAN: {MatchPhase.ENGINE_PROCESSING, MatchPhase.FINISHING, MatchPhase.ABORTED},
    MatchPhase.AGENT_THINKING: {MatchPhase.ENGINE_PROCESSING, MatchPhase.FINISHING, MatchPhase.ABORTED},
    MatchPhase.ENGINE_PROCESSING: {MatchPhase.WAITING_FOR_HUMAN, MatchPhase.AGENT_THINKING, MatchPhase.FINISHING, MatchPhase.ABORTED},
    MatchPhase.FINISHING: {MatchPhase.FINISHED, MatchPhase.ABORTED},
    MatchPhase.FINISHED: {MatchPhase.REPLAY_SEALED, MatchPhase.ABORTED},
    MatchPhase.REPLAY_SEALED: set(),
    MatchPhase.ABORTED: set(),
}


class InvalidTransition(RuntimeError):
    pass


@dataclass
class MatchStateMachine:
    phase: MatchPhase = MatchPhase.PREPARING

    def move(self, target: MatchPhase) -> MatchPhase:
        if target == self.phase:
            return self.phase
        if target not in ALLOWED_TRANSITIONS[self.phase]:
            raise InvalidTransition(f"{self.phase.value} -> {target.value}")
        self.phase = target
        return target


@dataclass(frozen=True)
class MatchResult:
    classification: str
    winner_seat: int | None
    engine_result: int | None
    reason_code: str
    summary_ja: str
    attributable_seat: int | None = None
    artifact_manifest_id: str | None = None
    human_seat: int | None = None
    first_player: int | None = None
    turn_count: int = 0
    battle_select_count: int = 0
    replay_complete: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
