'''JSON schemas and immutable records for Rollout-Q traces and branches.'''

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


SOURCE_TRACE_SCHEMA = 'archaludon-source-trace-v1'
BRANCH_TASK_SCHEMA = 'archaludon-branch-task-v1'
BRANCH_RESULT_SCHEMA = 'archaludon-branch-result-v1'


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def _tuple_action(value: Any) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)) or any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise ValueError('action must be a sequence of plain integers')
    return tuple(int(item) for item in value)


def _task_id(source_episode_id: str, branch_step_index: int, candidate_identity: str) -> str:
    payload = f'{source_episode_id}|{branch_step_index}|{candidate_identity}'.encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def branch_group_id(source_episode_id: str, branch_step_index: int) -> str:
    return hashlib.sha256(f'{source_episode_id}|{branch_step_index}'.encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class TraceStep:
    step_index: int
    current_player: int
    raw_observation_sha256: str
    public_state: dict[str, Any]
    action: tuple[int, ...]
    action_source: str
    select_context: int | None = None

    def __post_init__(self) -> None:
        if self.action_source not in ('BASELINE', 'OPPONENT'):
            raise ValueError('action_source must be BASELINE or OPPONENT')
        if self.current_player not in (0, 1):
            raise ValueError('current_player must be 0 or 1')

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result['action'] = list(self.action)
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> 'TraceStep':
        return cls(
            step_index=int(value['step_index']),
            current_player=int(value['current_player']),
            raw_observation_sha256=str(value['raw_observation_sha256']),
            public_state=dict(value['public_state']),
            action=_tuple_action(value['action']),
            action_source=str(value['action_source']),
            select_context=None if value.get('select_context') is None else int(value['select_context']),
        )


@dataclass(frozen=True)
class BranchPoint:
    branch_group_id: str
    step_index: int
    raw_observation_sha256: str
    public_state: dict[str, Any]
    baseline_action: tuple[int, ...]
    baseline_candidate_index: int
    candidates: tuple[dict[str, Any], ...]
    state_vector: tuple[float, ...] = ()
    option_vectors: tuple[tuple[float, ...], ...] = ()
    owner_before: Any = None
    owner_after: Any = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result['baseline_action'] = list(self.baseline_action)
        result['candidates'] = [dict(candidate) for candidate in self.candidates]
        for candidate in result['candidates']:
            candidate['action'] = list(candidate['action'])
        result['state_vector'] = list(self.state_vector)
        result['option_vectors'] = [list(vector) for vector in self.option_vectors]
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> 'BranchPoint':
        candidates = []
        for raw in value.get('candidates', ()):
            candidate = dict(raw)
            candidate['action'] = list(_tuple_action(candidate['action']))
            candidates.append(candidate)
        return cls(
            branch_group_id=str(value['branch_group_id']),
            step_index=int(value['step_index']),
            raw_observation_sha256=str(value['raw_observation_sha256']),
            public_state=dict(value['public_state']),
            baseline_action=_tuple_action(value['baseline_action']),
            baseline_candidate_index=int(value['baseline_candidate_index']),
            candidates=tuple(candidates),
            state_vector=tuple(float(item) for item in value.get('state_vector', ())),
            option_vectors=tuple(
                tuple(float(item) for item in vector)
                for vector in value.get('option_vectors', ())
            ),
            owner_before=value.get('owner_before'),
            owner_after=value.get('owner_after'),
        )


@dataclass(frozen=True)
class SourceTrace:
    episode_id: str
    opponent_id: str
    seat: int
    seed: int
    terminal_result: int
    terminal_reward: float
    clean_terminal: bool
    steps: tuple[TraceStep, ...]
    branch_points: tuple[BranchPoint, ...]
    engine_steps: int = 0
    action_errors: int = 0
    max_step_hit: bool = False
    error: str | None = None
    schema_version: str = SOURCE_TRACE_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'episode_id': self.episode_id,
            'opponent_id': self.opponent_id,
            'seat': self.seat,
            'seed': self.seed,
            'terminal_result': self.terminal_result,
            'terminal_reward': self.terminal_reward,
            'clean_terminal': self.clean_terminal,
            'engine_steps': self.engine_steps,
            'action_errors': self.action_errors,
            'max_step_hit': self.max_step_hit,
            'error': self.error,
            'steps': [step.to_dict() for step in self.steps],
            'branch_points': [point.to_dict() for point in self.branch_points],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> 'SourceTrace':
        if value.get('schema_version') != SOURCE_TRACE_SCHEMA:
            raise ValueError('unexpected source trace schema')
        return cls(
            episode_id=str(value['episode_id']),
            opponent_id=str(value['opponent_id']),
            seat=int(value['seat']),
            seed=int(value['seed']),
            terminal_result=int(value.get('terminal_result', -1)),
            terminal_reward=float(value.get('terminal_reward', 0.0)),
            clean_terminal=bool(value.get('clean_terminal', False)),
            steps=tuple(TraceStep.from_dict(row) for row in value.get('steps', ())),
            branch_points=tuple(BranchPoint.from_dict(row) for row in value.get('branch_points', ())),
            engine_steps=int(value.get('engine_steps', 0)),
            action_errors=int(value.get('action_errors', 0)),
            max_step_hit=bool(value.get('max_step_hit', False)),
            error=None if value.get('error') is None else str(value['error']),
        )


@dataclass(frozen=True)
class BranchTask:
    task_id: str
    source_episode_id: str
    opponent_id: str
    seat: int
    seed: int
    branch_step_index: int
    candidate_index: int
    candidate_action: tuple[int, ...]
    candidate_identity: str
    baseline_candidate_index: int
    baseline_action: tuple[int, ...]
    branch_group_id: str
    public_state: dict[str, Any]
    candidates: tuple[dict[str, Any], ...]

    @classmethod
    def create(
        cls,
        *,
        source_episode_id: str,
        opponent_id: str,
        seat: int,
        seed: int,
        branch_step_index: int,
        candidate_index: int,
        candidate_action: Sequence[int],
        candidate_identity: str,
        baseline_candidate_index: int,
        baseline_action: Sequence[int],
        branch_group: str,
        public_state: Mapping[str, Any],
        candidates: Sequence[Mapping[str, Any]],
    ) -> 'BranchTask':
        return cls(
            task_id=_task_id(source_episode_id, branch_step_index, candidate_identity),
            source_episode_id=source_episode_id,
            opponent_id=opponent_id,
            seat=int(seat),
            seed=int(seed),
            branch_step_index=int(branch_step_index),
            candidate_index=int(candidate_index),
            candidate_action=tuple(int(item) for item in candidate_action),
            candidate_identity=str(candidate_identity),
            baseline_candidate_index=int(baseline_candidate_index),
            baseline_action=tuple(int(item) for item in baseline_action),
            branch_group_id=str(branch_group),
            public_state=dict(public_state),
            candidates=tuple(dict(item) for item in candidates),
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key in ('candidate_action', 'baseline_action'):
            result[key] = list(result[key])
        result['candidates'] = [dict(item) for item in result['candidates']]
        for item in result['candidates']:
            item['action'] = list(item['action'])
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> 'BranchTask':
        if value.get('schema_version') not in (None, BRANCH_TASK_SCHEMA):
            raise ValueError('unexpected branch task schema')
        raw = dict(value)
        raw.pop('schema_version', None)
        raw['candidate_action'] = _tuple_action(raw['candidate_action'])
        raw['baseline_action'] = _tuple_action(raw['baseline_action'])
        raw['candidates'] = tuple(dict(item) for item in raw.get('candidates', ()))
        return cls(**raw)


@dataclass(frozen=True)
class BranchResult:
    task_id: str
    branch_group_id: str
    candidate_index: int
    candidate_identity: str
    is_baseline_candidate: bool
    status: str
    terminal_result: int | None
    reward: float | None
    engine_steps: int
    clean_terminal: bool
    action_errors: int
    max_step_hit: bool
    error: str | None = None
    schema_version: str = BRANCH_RESULT_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> 'BranchResult':
        if value.get('schema_version') != BRANCH_RESULT_SCHEMA:
            raise ValueError('unexpected branch result schema')
        return cls(
            task_id=str(value['task_id']),
            branch_group_id=str(value['branch_group_id']),
            candidate_index=int(value['candidate_index']),
            candidate_identity=str(value['candidate_identity']),
            is_baseline_candidate=bool(value['is_baseline_candidate']),
            status=str(value['status']),
            terminal_result=None if value.get('terminal_result') is None else int(value['terminal_result']),
            reward=None if value.get('reward') is None else float(value['reward']),
            engine_steps=int(value.get('engine_steps', 0)),
            clean_terminal=bool(value.get('clean_terminal', False)),
            action_errors=int(value.get('action_errors', 0)),
            max_step_hit=bool(value.get('max_step_hit', False)),
            error=None if value.get('error') is None else str(value['error']),
        )


def write_record(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json(dict(value)) + '\n', encoding='utf-8')


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))
