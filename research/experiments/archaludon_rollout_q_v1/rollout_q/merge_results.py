'''Merge fixed shard result files without changing their task order.'''

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import RolloutQConfig, round_dir, write_json
from .trace_schema import BRANCH_RESULT_SCHEMA, BranchResult


def _read_shard(path: Path) -> list[BranchResult]:
    rows: list[BranchResult] = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            rows.append(BranchResult.from_dict(json.loads(line)))
    return rows


def merge_results_round(config: RolloutQConfig, round_index: int, *, shard_count: int) -> dict[str, Any]:
    if shard_count <= 0:
        raise ValueError('shard_count must be positive')
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
