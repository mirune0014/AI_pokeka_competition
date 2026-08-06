'''Merge fixed shard result files without changing their task order.'''

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .branch_task_builder import read_tasks
from .config import RolloutQConfig, round_dir, write_json
from .trace_schema import BRANCH_RESULT_SCHEMA, BranchResult, BranchTask


def _read_shard(path: Path) -> list[BranchResult]:
    rows: list[BranchResult] = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            rows.append(BranchResult.from_dict(json.loads(line)))
    return rows


def merge_results_round(config: RolloutQConfig, round_index: int, *, shard_count: int) -> dict[str, Any]:
    if shard_count <= 0:
        raise ValueError('shard_count must be positive')
    tasks_path = round_dir(config, round_index) / 'tasks' / 'all_tasks.jsonl'
    expected_tasks = read_tasks(tasks_path)
    expected_task_ids = {task.task_id for task in expected_tasks}
    if len(expected_task_ids) != len(expected_tasks):
        raise ValueError('duplicate task_id in all_tasks.jsonl')
    expected_by_id = {task.task_id: task for task in expected_tasks}
    result_dir = round_dir(config, round_index) / 'branch_results'
    all_rows: list[BranchResult] = []
    for shard_index in range(shard_count):
        path = result_dir / f'shard_{shard_index:03d}_of_{shard_count:03d}.jsonl'
        if not path.is_file():
            raise FileNotFoundError(path)
        all_rows.extend(_read_shard(path))
    task_ids = [row.task_id for row in all_rows]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError('duplicate branch result task_id')
    result_task_ids = set(task_ids)
    if result_task_ids != expected_task_ids:
        missing = sorted(expected_task_ids - result_task_ids)
        extra = sorted(result_task_ids - expected_task_ids)
        raise ValueError(f'branch result completeness mismatch: missing={missing[:3]} extra={extra[:3]}')
    if len(result_task_ids) != len(expected_task_ids):
        raise ValueError('branch result count does not match all_tasks.jsonl')
    for row in all_rows:
        expected = expected_by_id[row.task_id]
        if row.branch_group_id != expected.branch_group_id:
            raise ValueError(f'branch result group mismatch for task {row.task_id}')
    result_groups: dict[str, list[BranchResult]] = {}
    for row in all_rows:
        result_groups.setdefault(row.branch_group_id, []).append(row)
    expected_groups: dict[str, list[BranchTask]] = {}
    for task in expected_tasks:
        expected_groups.setdefault(task.branch_group_id, []).append(task)
    if set(result_groups) != set(expected_groups):
        raise ValueError('branch result group set does not match all_tasks.jsonl')
    for group_id, group_rows in result_groups.items():
        baseline_count = sum(int(row.is_baseline_candidate) for row in group_rows)
        if baseline_count != 1:
            raise ValueError(f'branch group {group_id} must contain exactly one baseline candidate')
    all_rows.sort(key=lambda row: row.task_id)
    output = result_dir / 'all_results.jsonl'
    with output.open('w', encoding='utf-8', newline='\n') as handle:
        for row in all_rows:
            handle.write(
                json.dumps(
                    {'schema_version': BRANCH_RESULT_SCHEMA, **row.to_dict()},
                    sort_keys=True,
                    separators=(',', ':'),
                    ensure_ascii=True,
                    allow_nan=False,
                )
            )
            handle.write('\n')
    summary = {
        'schema_version': 'archaludon-branch-merge-summary-v1',
        'round': int(round_index),
        'shard_count': int(shard_count),
        'task_count': len(all_rows),
        'ok_count': sum(int(row.status == 'OK') for row in all_rows),
        'continuation_unsafe_count': sum(int(row.status == 'CONTINUATION_UNSAFE') for row in all_rows),
        'error_count': sum(int(row.status == 'ERROR') for row in all_rows),
    }
    write_json(result_dir / 'merge_summary.json', summary)
    return summary


def read_merged_results(config: RolloutQConfig, round_index: int) -> list[BranchResult]:
    path = round_dir(config, round_index) / 'branch_results' / 'all_results.jsonl'
    if not path.is_file():
        raise FileNotFoundError(path)
    rows: list[BranchResult] = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            rows.append(BranchResult.from_dict(json.loads(line)))
    return rows


__all__ = ['merge_results_round', 'read_merged_results']
