'''Replay source prefixes and execute complete-action branch groups.'''

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .agent_loader import load_baseline, load_opponent
from .branch_task_builder import read_tasks
from .complete_action import observation_complete_actions, observation_option_rows
from .config import RolloutQConfig, round_dir, terminal_reward, write_json
from .source_collector import (
    _battle_start,
    _load_engine,
    _opponent_rows,
    build_source_policy,
    resolve_opponent_dir,
    trace_observation_hash,
)
from .trace_schema import (
    BRANCH_RESULT_SCHEMA,
    BranchResult,
    BranchTask,
    SourceTrace,
    read_json,
)


class PrefixReplayMismatch(RuntimeError):
    pass


class ContinuationUnsafe(RuntimeError):
    pass


@dataclass
class _EpisodeReplay:
    result: int | None
    reward: float | None
    engine_steps: int
    action_errors: int
    max_step_hit: bool
    clean_terminal: bool
    action_sequence: list[tuple[int, ...]]
    error: str | None = None


def _trace_path(config: RolloutQConfig, task: BranchTask) -> Path:
    return round_dir(config, _round_from_task(task)) / 'source_traces' / f'{task.source_episode_id}.json'


def _round_from_task(task: BranchTask) -> int:
    prefix = task.source_episode_id.split('_', 2)
    if len(prefix) < 2 or not prefix[1].isdigit():
        raise ValueError(f'cannot infer source round from {task.source_episode_id}')
    return int(prefix[1])


def _resolve_task_opponent(config: RolloutQConfig, task: BranchTask) -> Path:
    for row in _opponent_rows():
        if str(row.get('id')) == task.opponent_id:
            return resolve_opponent_dir(row, config)
    raise KeyError(task.opponent_id)


def _terminal(observation: Any) -> int | None:
    current = observation.get('current', {}) if isinstance(observation, Mapping) else getattr(observation, 'current', {})
    value = current.get('result') if isinstance(current, Mapping) else getattr(current, 'result', None)
    if value is None:
        return None
    raw = getattr(value, 'value', value)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value in (0, 1, 2) else None


def _player(observation: Any) -> int:
    current = observation.get('current', {}) if isinstance(observation, Mapping) else getattr(observation, 'current', {})
    value = current.get('yourIndex', 0) if isinstance(current, Mapping) else getattr(current, 'yourIndex', 0)
    return int(getattr(value, 'value', value))


def _policy_owner(policy: Any) -> Any:
    baseline = getattr(policy, 'baseline', policy)
    return getattr(baseline, 'owner', None)


def _run_replay(
    *,
    config: RolloutQConfig,
    task: BranchTask,
    trace: SourceTrace,
    max_steps: int,
) -> _EpisodeReplay:
    """Replay one branch with one fixed round source-policy object.

    The source policy is called for every own decision before and after the
    branch.  At the branch point the recorded source action is replaced by
    the task candidate, but the same source-policy object continues afterward.
    """

    opponent_dir = _resolve_task_opponent(config, task)
    battle_start, battle_select, battle_finish, _ = _load_engine()
    baseline = load_baseline(config.baseline_dir, config.baseline_dir.name)
    source_policy = build_source_policy(config, _round_from_task(task), baseline)
    opponent = load_opponent(opponent_dir, task.opponent_id)
    baseline.seed(task.seed)
    opponent.seed(task.seed)
    baseline_deck = baseline.deck
    opponent_deck = opponent.deck
    decks = (baseline_deck, opponent_deck) if task.seat == 0 else (opponent_deck, baseline_deck)
    observation: Any = None
    started = False
    actions: list[tuple[int, ...]] = []
    action_errors = 0
    terminal_result: int | None = None
    max_step_hit = False
    branch_done = False
    try:
        observation, start_data = _battle_start(battle_start, decks, task.seed)
        if not observation:
            error_player = getattr(start_data, 'errorPlayer', None)
            error_type = getattr(start_data, 'errorType', None)
            raise RuntimeError(f'engine start failed: {error_player}/{error_type}')
        started = True
        trace_steps = {step.step_index: step for step in trace.steps}
        for step_index in range(int(max_steps)):
            terminal_result = _terminal(observation)
            if terminal_result is not None:
                break
            if not isinstance(observation, Mapping) or not observation.get('select'):
                break
            expected = trace_steps.get(step_index) if not branch_done else None
            if not branch_done and expected is None:
                raise PrefixReplayMismatch(f'missing trace step {step_index}')
            if expected is not None:
                observed_hash = trace_observation_hash(observation)
                if observed_hash != expected.raw_observation_sha256:
                    raise PrefixReplayMismatch(f'raw observation mismatch at step {step_index}')
            current_player = _player(observation)
            if expected is not None and current_player != expected.current_player:
                raise PrefixReplayMismatch(f'current player mismatch at step {step_index}')
            is_branch = step_index == task.branch_step_index
            if current_player == task.seat:
                owner_before = _policy_owner(source_policy)
                predicted = tuple(source_policy(observation))
                owner_after = _policy_owner(source_policy)
                if expected is not None and predicted != expected.action:
                    raise PrefixReplayMismatch(f'source policy action mismatch at step {step_index}')
                if is_branch:
                    if owner_before is not None or owner_after is not None:
                        raise ContinuationUnsafe(f'branch owner is not empty at step {step_index}')
                    candidates = observation_complete_actions(observation)
                    option_rows = observation_option_rows(observation)
                    baseline_index = candidates.candidate_index_for(option_rows, predicted)
                    selected_index = candidates.candidate_index_for(option_rows, task.candidate_action)
                    if baseline_index != task.baseline_candidate_index:
                        raise ContinuationUnsafe(f'baseline candidate mismatch at step {step_index}')
                    if tuple(predicted) != tuple(task.baseline_action):
                        raise ContinuationUnsafe(f'baseline action mismatch at step {step_index}')
                    if selected_index != task.candidate_index:
                        raise ContinuationUnsafe(f'candidate identity mismatch at step {step_index}')
                    action = tuple(task.candidate_action)
                    branch_done = True
                else:
                    action = expected.action if expected is not None else predicted
            else:
                predicted = tuple(opponent(observation))
                if expected is not None and predicted != expected.action:
                    raise PrefixReplayMismatch(f'opponent action mismatch at step {step_index}')
                action = expected.action if expected is not None else predicted
            try:
                observation = battle_select(list(action))
            except Exception:
                action_errors += 1
                raise
            actions.append(action)
        else:
            max_step_hit = True
        terminal_result = _terminal(observation)
        if not branch_done:
            raise ContinuationUnsafe('branch step was not reached')
        clean_terminal = terminal_result in (0, 1, 2) and not max_step_hit and action_errors == 0
        if not clean_terminal:
            raise RuntimeError('branch replay did not reach a clean terminal result')
        return _EpisodeReplay(
            result=terminal_result,
            reward=terminal_reward(int(terminal_result), task.seat),
            engine_steps=len(actions),
            action_errors=action_errors,
            max_step_hit=max_step_hit,
            clean_terminal=True,
            action_sequence=actions,
        )
    finally:
        if started:
            battle_finish()


def _result_from_replay(task: BranchTask, replay: _EpisodeReplay, *, status: str = 'OK', error: str | None = None) -> BranchResult:
    return BranchResult(
        task_id=task.task_id,
        branch_group_id=task.branch_group_id,
        candidate_index=task.candidate_index,
        candidate_identity=task.candidate_identity,
        is_baseline_candidate=task.candidate_index == task.baseline_candidate_index,
        status=status,
        terminal_result=replay.result,
        reward=replay.reward,
        engine_steps=replay.engine_steps,
        clean_terminal=replay.clean_terminal,
        action_errors=replay.action_errors,
        max_step_hit=replay.max_step_hit,
        error=error or replay.error,
    )


def _error_result(task: BranchTask, status: str, error: Exception | str) -> BranchResult:
    message = error if isinstance(error, str) else f'{type(error).__name__}: {error}'
    return BranchResult(
        task_id=task.task_id,
        branch_group_id=task.branch_group_id,
        candidate_index=task.candidate_index,
        candidate_identity=task.candidate_identity,
        is_baseline_candidate=task.candidate_index == task.baseline_candidate_index,
        status=status,
        terminal_result=None,
        reward=None,
        engine_steps=0,
        clean_terminal=False,
        action_errors=0,
        max_step_hit=False,
        error=message,
    )


def _identity_matches(trace: SourceTrace, replay: _EpisodeReplay) -> bool:
    expected_actions = [tuple(step.action) for step in trace.steps]
    return (
        replay.action_sequence == expected_actions
        and replay.result == trace.terminal_result
        and replay.engine_steps == trace.engine_steps
        and replay.action_errors == 0
        and not replay.max_step_hit
    )


def run_branch_group(
    config: RolloutQConfig,
    tasks: Sequence[BranchTask],
    *,
    max_steps: int | None = None,
) -> list[BranchResult]:
    """Run one branch group with one baseline identity replay.

    All tasks in the group are returned.  A baseline failure marks every
    candidate CONTINUATION_UNSAFE and no alternative replay is attempted.
    """

    if not tasks:
        return []
    group_ids = {task.branch_group_id for task in tasks}
    if len(group_ids) != 1:
        raise ValueError('run_branch_group requires one branch_group_id')
    ordered = sorted(tasks, key=lambda task: (task.candidate_index, task.task_id))
    baseline_tasks = [task for task in ordered if task.candidate_index == task.baseline_candidate_index]
    if len(baseline_tasks) != 1:
        return [_error_result(task, 'CONTINUATION_UNSAFE', 'group must contain exactly one baseline candidate') for task in ordered]
    baseline_task = baseline_tasks[0]
    trace = SourceTrace.from_dict(read_json(_trace_path(config, baseline_task)))
    limit = max_steps or config.worker_max_steps
    try:
        identity = _run_replay(config=config, task=baseline_task, trace=trace, max_steps=limit)
        if not _identity_matches(trace, identity):
            raise ContinuationUnsafe('baseline identity gate mismatch')
    except Exception as exc:
        return [_error_result(task, 'CONTINUATION_UNSAFE', exc) for task in ordered]

    results: list[BranchResult] = [_result_from_replay(baseline_task, identity)]
    for task in ordered:
        if task.task_id == baseline_task.task_id:
            continue
        try:
            alternative = _run_replay(config=config, task=task, trace=trace, max_steps=limit)
            results.append(_result_from_replay(task, alternative))
        except (ContinuationUnsafe, PrefixReplayMismatch) as exc:
            results.append(_error_result(task, 'CONTINUATION_UNSAFE', exc))
        except Exception as exc:
            results.append(_error_result(task, 'ERROR', exc))
    return results


def run_branch_task(config: RolloutQConfig, task: BranchTask, *, max_steps: int | None = None) -> BranchResult:
    """Compatibility wrapper for a single task; shard execution is group-based."""

    results = run_branch_group(config, [task], max_steps=max_steps)
    return results[0]


def _assigned(task: BranchTask, shard_count: int, shard_index: int) -> bool:
    return int(task.branch_group_id[:16], 16) % int(shard_count) == int(shard_index)


def run_branches_shard(
    config: RolloutQConfig,
    round_index: int,
    *,
    shard_count: int,
    shard_index: int,
    max_steps: int | None = None,
) -> dict[str, Any]:
    if shard_count <= 0 or not 0 <= shard_index < shard_count:
        raise ValueError('invalid shard specification')
    tasks_path = round_dir(config, round_index) / 'tasks' / 'all_tasks.jsonl'
    tasks = [task for task in read_tasks(tasks_path) if _assigned(task, shard_count, shard_index)]
    groups: dict[str, list[BranchTask]] = defaultdict(list)
    for task in tasks:
        groups[task.branch_group_id].append(task)
    result_path = round_dir(config, round_index) / 'branch_results' / f'shard_{shard_index:03d}_of_{shard_count:03d}.jsonl'
    result_path.parent.mkdir(parents=True, exist_ok=True)
    completed: set[str] = set()
    if result_path.is_file():
        for line in result_path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                completed.add(str(read_json_line(line)['task_id']))
    pending_groups: list[list[BranchTask]] = []
    skipped_groups = 0
    for group_id in sorted(groups):
        group = sorted(groups[group_id], key=lambda task: (task.candidate_index, task.task_id))
        task_ids = {task.task_id for task in group}
        overlap = task_ids & completed
        if overlap and overlap != task_ids:
            raise ValueError(f'partial completed branch group: {group_id}')
        if overlap == task_ids:
            skipped_groups += 1
        else:
            pending_groups.append(group)
    written = 0
    with result_path.open('a', encoding='utf-8', newline='\n') as handle:
        for group in pending_groups:
            for result in run_branch_group(config, group, max_steps=max_steps):
                handle.write(json_line({'schema_version': BRANCH_RESULT_SCHEMA, **result.to_dict()}))
                handle.write('\n')
                written += 1
    summary = {
        'schema_version': 'archaludon-branch-shard-summary-v1',
        'round': int(round_index),
        'shard_count': int(shard_count),
        'shard_index': int(shard_index),
        'assigned_tasks': len(tasks),
        'assigned_groups': len(groups),
        'skipped_groups': skipped_groups,
        'written_tasks': written,
        'result_path': str(result_path),
    }
    write_json(round_dir(config, round_index) / 'branch_results' / f'shard_{shard_index:03d}_summary.json', summary)
    return summary


def json_line(value: Mapping[str, Any]) -> str:
    return json.dumps(dict(value), sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def read_json_line(line: str) -> dict[str, Any]:
    value = json.loads(line)
    if not isinstance(value, dict):
        raise ValueError('result line must be an object')
    return value


__all__ = [
    'ContinuationUnsafe',
    'PrefixReplayMismatch',
    '_assigned',
    'run_branch_group',
    'run_branch_task',
    'run_branches_shard',
]
