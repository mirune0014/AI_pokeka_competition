'''Build one deterministic task for every complete candidate at each branch.'''

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .config import RolloutQConfig, round_dir, write_json
from .trace_schema import BRANCH_TASK_SCHEMA, BranchTask, SourceTrace, read_json


def _source_files(config: RolloutQConfig, round_index: int) -> list[Path]:
    directory = round_dir(config, round_index) / 'source_traces'
    if not directory.is_dir():
        raise FileNotFoundError(directory)
    return sorted(directory.glob('*.json'))


def load_source_traces(config: RolloutQConfig, round_index: int) -> list[SourceTrace]:
    return [SourceTrace.from_dict(read_json(path)) for path in _source_files(config, round_index)]


def tasks_for_trace(trace: SourceTrace) -> list[BranchTask]:
    if not trace.clean_terminal:
        return []
    result: list[BranchTask] = []
    for point in trace.branch_points:
        for candidate in point.candidates:
            candidate_index = int(candidate['candidate_index'])
            result.append(
                BranchTask.create(
                    source_episode_id=trace.episode_id,
                    opponent_id=trace.opponent_id,
                    seat=trace.seat,
                    seed=trace.seed,
                    branch_step_index=point.step_index,
                    candidate_index=candidate_index,
                    candidate_action=tuple(int(value) for value in candidate['action']),
                    candidate_identity=str(candidate['canonical_identity']),
                    baseline_candidate_index=point.baseline_candidate_index,
                    baseline_action=point.baseline_action,
                    branch_group=point.branch_group_id,
                    public_state=point.public_state,
                    candidates=point.candidates,
                )
            )
    return result


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False))
            handle.write('\n')
            count += 1
    return count


def read_tasks(path: Path) -> list[BranchTask]:
    tasks: list[BranchTask] = []
    if not path.is_file():
        raise FileNotFoundError(path)
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            tasks.append(BranchTask.from_dict(json.loads(line)))
    return tasks


def build_tasks_round(config: RolloutQConfig, round_index: int) -> dict[str, Any]:
    destination = round_dir(config, round_index) / 'tasks'
    path = destination / 'all_tasks.jsonl'
    if path.exists():
        raise FileExistsError(path)
    traces = load_source_traces(config, round_index)
    tasks: list[BranchTask] = []
    for trace in traces:
        tasks.extend(tasks_for_trace(trace))
    tasks.sort(key=lambda item: item.task_id)
    count = _write_jsonl(
        path,
        ({'schema_version': BRANCH_TASK_SCHEMA, **task.to_dict()} for task in tasks),
    )
    groups = {task.branch_group_id for task in tasks}
    summary = {
        'schema_version': 'archaludon-task-build-summary-v1',
        'round': int(round_index),
        'source_trace_count': len(traces),
        'task_count': count,
        'branch_group_count': len(groups),
        'candidate_count': count,
    }
    write_json(destination / 'tasks_summary.json', summary)
    return summary


__all__ = ['build_tasks_round', 'load_source_traces', 'read_tasks', 'tasks_for_trace']
