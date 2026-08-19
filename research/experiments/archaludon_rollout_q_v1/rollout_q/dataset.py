'''Construct paired candidate-vs-baseline learning rows.'''

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from research.rl_ptcg.encoding import OPTION_FEATURE_NAMES

from .branch_task_builder import read_tasks
from .config import RolloutQConfig, round_dir, write_json
from .merge_results import read_merged_results
from .trace_schema import BranchPoint, BranchResult, BranchTask, SourceTrace, read_json as read_record


def episode_split(source_episode_id: str) -> str:
    bucket = int(hashlib.sha256(source_episode_id.encode('utf-8')).hexdigest()[:8], 16) % 10
    return 'validation' if bucket in (0, 1) else 'training'


def complete_action_feature(
    option_vectors: Sequence[Sequence[float]],
    action: Sequence[int],
) -> list[float]:
    width = len(option_vectors[0]) if option_vectors else len(OPTION_FEATURE_NAMES)
    selected = [list(map(float, option_vectors[index])) for index in action if 0 <= int(index) < len(option_vectors)]
    if not selected:
        zeros = [0.0] * width
        return zeros + zeros + zeros + [0.0]
    sum_pool = [sum(row[col] for row in selected) for col in range(width)]
    mean_pool = [value / len(selected) for value in sum_pool]
    max_pool = [max(row[col] for row in selected) for col in range(width)]
    return sum_pool + mean_pool + max_pool + [len(selected) / 6.0]


def _candidate_by_index(point: BranchPoint, index: int) -> dict[str, Any]:
    for candidate in point.candidates:
        if int(candidate['candidate_index']) == int(index):
            return dict(candidate)
    raise KeyError(index)


def _family(candidate: Mapping[str, Any]) -> str:
    types: list[str] = []
    for option in candidate.get('selected_options', ()):
        payload = option.get('semantic_payload') or option.get('payload') or {}
        value = payload.get('option_type', payload.get('type', 'empty')) if isinstance(payload, Mapping) else 'empty'
        types.append(str(value))
    return 'empty' if not types else '+'.join(sorted(types))


def _load_round_data(config: RolloutQConfig, round_index: int) -> tuple[dict[str, BranchTask], dict[str, SourceTrace], list[BranchResult]]:
    tasks_path = round_dir(config, round_index) / 'tasks' / 'all_tasks.jsonl'
    tasks = {task.task_id: task for task in read_tasks(tasks_path)}
    traces: dict[str, SourceTrace] = {}
    trace_dir = round_dir(config, round_index) / 'source_traces'
    for path in sorted(trace_dir.glob('*.json')):
        trace = SourceTrace.from_dict(read_record(path))
        traces[trace.episode_id] = trace
    return tasks, traces, read_merged_results(config, round_index)


def _rows_for_round(config: RolloutQConfig, round_index: int) -> list[dict[str, Any]]:
    tasks, traces, results = _load_round_data(config, round_index)
    group_meta: dict[str, BranchTask] = {}
    for task in tasks.values():
        existing = group_meta.get(task.branch_group_id)
        if existing is None:
            group_meta[task.branch_group_id] = task
            continue
        expected = (
            existing.source_episode_id,
            existing.opponent_id,
            int(existing.seat),
            int(existing.seed),
            int(existing.branch_step_index),
        )
        actual = (
            task.source_episode_id,
            task.opponent_id,
            int(task.seat),
            int(task.seed),
            int(task.branch_step_index),
        )
        if actual != expected:
            raise ValueError(f'branch group metadata mismatch: {task.branch_group_id}')
    points: dict[str, BranchPoint] = {}
    for trace in traces.values():
        for point in trace.branch_points:
            points[point.branch_group_id] = point
    grouped: dict[str, list[BranchResult]] = {}
    for result in results:
        grouped.setdefault(result.branch_group_id, []).append(result)
    rows: list[dict[str, Any]] = []
    for group_id in sorted(grouped):
        group_results = grouped[group_id]
        baseline = next((item for item in group_results if item.is_baseline_candidate and item.status == 'OK'), None)
        if baseline is None or baseline.reward is None:
            continue
        point = points.get(group_id)
        if point is None:
            continue
        meta = group_meta.get(group_id)
        if meta is None:
            raise ValueError(f'branch result group has no task metadata: {group_id}')
        base_candidate = _candidate_by_index(point, baseline.candidate_index)
        base_feature = complete_action_feature(point.option_vectors, base_candidate['action'])
        for candidate_result in group_results:
            if candidate_result.is_baseline_candidate or candidate_result.status != 'OK' or candidate_result.reward is None:
                continue
            candidate = _candidate_by_index(point, candidate_result.candidate_index)
            candidate_feature = complete_action_feature(point.option_vectors, candidate['action'])
            reward_delta = float(candidate_result.reward) - float(baseline.reward)
            if reward_delta > 0.0:
                label = 1.0
                outcome_class = 'IMPROVED'
            elif reward_delta < 0.0:
                label = 0.0
                outcome_class = 'WORSE'
            else:
                label = 0.0
                outcome_class = 'EQUAL'
            select = point.public_state.get('select') or {}
            rows.append(
                {
                    'source_round': int(round_index),
                    'source_episode_id': meta.source_episode_id,
                    'branch_group_id': group_id,
                    'opponent_id': meta.opponent_id,
                    'seat': int(meta.seat),
                    'context': int(select.get('context', 0) or 0),
                    'family': _family(candidate),
                    'state': list(point.state_vector),
                    'candidate_action': [float(value) for value in candidate_feature],
                    'baseline_action': [float(value) for value in base_feature],
                    'label': label,
                    'weight': 1.0,
                    'candidate_reward': float(candidate_result.reward),
                    'baseline_reward': float(baseline.reward),
                    'reward_delta': reward_delta,
                    'outcome_class': outcome_class,
                    'split': episode_split(meta.source_episode_id),
                }
            )
    return rows


def build_dataset(config: RolloutQConfig, through_round: int) -> dict[str, Any]:
    if not 0 <= int(through_round) < config.rounds:
        raise ValueError('through_round is outside the fixed specification')
    rows: list[dict[str, Any]] = []
    for round_index in range(int(through_round) + 1):
        rows.extend(_rows_for_round(config, round_index))
    output = config.output_dir / f'dataset_through_round_{int(through_round):02d}.json'
    if output.exists():
        raise FileExistsError(output)
    state_dim = len(rows[0]['state']) if rows else None
    action_dim = len(rows[0]['candidate_action']) if rows else None
    payload = {
        'schema_version': 'archaludon-rollout-q-dataset-v1',
        'through_round': int(through_round),
        'rows': rows,
        'state_dim': state_dim,
        'action_feature_dim': action_dim,
    }
    write_json(output, payload)
    improved_rows = sum(int(row.get('outcome_class') == 'IMPROVED') for row in rows)
    equal_rows = sum(int(row.get('outcome_class') == 'EQUAL') for row in rows)
    worse_rows = sum(int(row.get('outcome_class') == 'WORSE') for row in rows)
    summary = {
        'schema_version': 'archaludon-dataset-summary-v1',
        'through_round': int(through_round),
        'row_count': len(rows),
        'training_rows': sum(int(row['split'] == 'training') for row in rows),
        'validation_rows': sum(int(row['split'] == 'validation') for row in rows),
        'positive_rows': sum(int(row['label'] == 1.0) for row in rows),
        'negative_rows': sum(int(row['label'] == 0.0) for row in rows),
        'improved_rows': improved_rows,
        'equal_rows': equal_rows,
        'worse_rows': worse_rows,
        'strict_improvement_rate': (improved_rows / len(rows)) if rows else None,
        'state_dim': state_dim,
        'action_feature_dim': action_dim,
        'dataset_path': str(output),
    }
    write_json(config.output_dir / f'dataset_through_round_{int(through_round):02d}_summary.json', summary)
    return summary


def load_dataset(config: RolloutQConfig, through_round: int) -> dict[str, Any]:
    path = config.output_dir / f'dataset_through_round_{int(through_round):02d}.json'
    if not path.is_file():
        raise FileNotFoundError(path)
    return read_record(path)


__all__ = ['build_dataset', 'complete_action_feature', 'episode_split', 'load_dataset']
