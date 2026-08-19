"""Independent groupwise conservative policy-selection experiment.

This module deliberately reads the frozen Round 0 traces, tasks, and merged
branch results and writes only under ``_local_generated/archaludon_rollout_q_groupwise_v1``.
It reuses the existing Rollout-Q state/action encoder and hidden dimensions,
but trains a groupwise scalar scorer with a within-group cross-entropy loss.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import random
from typing import Any, Iterable, Mapping, Sequence

import torch
from torch.nn import functional as F

from .branch_task_builder import read_tasks
from .config import REPO_ROOT, RolloutQConfig, load_spec, round_dir
from .dataset import complete_action_feature, episode_split
from .merge_results import read_merged_results
from .model import ModelConfig, build_model
from .trace_schema import SourceTrace, read_json


GROUPWISE_ROOT = REPO_ROOT / '_local_generated' / 'archaludon_rollout_q_groupwise_v1'
GROUPWISE_DATASET_SCHEMA = 'archaludon-rollout-q-groupwise-dataset-v1'
GROUPWISE_CHECKPOINT_SCHEMA = 'archaludon-rollout-q-groupwise-checkpoint-v1'
GROUPWISE_TRAINING_SCHEMA = 'archaludon-rollout-q-groupwise-training-summary-v1'
GROUPWISE_CALIBRATION_SCHEMA = 'archaludon-rollout-q-groupwise-calibration-v1'


@dataclass(frozen=True)
class GroupwisePaths:
    root: Path
    dataset: Path
    dataset_summary: Path
    checkpoint_dir: Path
    training_summary: Path
    calibration_json: Path
    calibration_markdown: Path


def paths() -> GroupwisePaths:
    return GroupwisePaths(
        root=GROUPWISE_ROOT,
        dataset=GROUPWISE_ROOT / 'groupwise_dataset_round_00.json',
        dataset_summary=GROUPWISE_ROOT / 'groupwise_dataset_round_00_summary.json',
        checkpoint_dir=GROUPWISE_ROOT / 'checkpoints',
        training_summary=GROUPWISE_ROOT / 'groupwise_training_round_00_summary.json',
        calibration_json=GROUPWISE_ROOT / 'groupwise_validation_calibration.json',
        calibration_markdown=GROUPWISE_ROOT / 'groupwise_validation_calibration.md',
    )


def _write_json_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n',
        encoding='utf-8',
    )


def _candidate_family(candidate: Mapping[str, Any]) -> str:
    types: list[str] = []
    for option in candidate.get('selected_options', ()):
        payload = option.get('semantic_payload') or option.get('payload') or {}
        value = payload.get('option_type', payload.get('type', 'empty')) if isinstance(payload, Mapping) else 'empty'
        types.append(str(value))
    return 'empty' if not types else '+'.join(sorted(types))


def _candidate_by_index(point: Any, index: int) -> dict[str, Any]:
    for candidate in point.candidates:
        if int(candidate['candidate_index']) == int(index):
            return dict(candidate)
    raise KeyError(index)


def _context(point: Any) -> int:
    select = point.public_state.get('select') or {}
    return int(select.get('context', 0) or 0)


def _load_round_inputs(config: RolloutQConfig, round_index: int) -> tuple[dict[str, Any], dict[str, Any], list[Any]]:
    round_path = round_dir(config, round_index)
    tasks_path = round_path / 'tasks' / 'all_tasks.jsonl'
    tasks = {task.task_id: task for task in read_tasks(tasks_path)}
    traces: dict[str, SourceTrace] = {}
    for trace_path in sorted((round_path / 'source_traces').glob('*.json')):
        trace = SourceTrace.from_dict(read_json(trace_path))
        traces[trace.episode_id] = trace
    results = read_merged_results(config, round_index)
    return tasks, traces, results


def _build_group_rows(config: RolloutQConfig, round_index: int) -> list[dict[str, Any]]:
    tasks, traces, results = _load_round_inputs(config, round_index)
    task_by_group: dict[str, list[Any]] = defaultdict(list)
    for task in tasks.values():
        task_by_group[task.branch_group_id].append(task)
    result_by_group: dict[str, list[Any]] = defaultdict(list)
    for result in results:
        result_by_group[result.branch_group_id].append(result)
    point_by_group: dict[str, tuple[SourceTrace, Any]] = {}
    for trace in traces.values():
        for point in trace.branch_points:
            if point.branch_group_id in point_by_group:
                raise ValueError(f'duplicate branch point group: {point.branch_group_id}')
            point_by_group[point.branch_group_id] = (trace, point)

    if set(task_by_group) != set(result_by_group) or set(task_by_group) != set(point_by_group):
        raise ValueError('group sets do not match across tasks, results, and traces')

    group_rows: list[dict[str, Any]] = []
    for group_id in sorted(task_by_group):
        group_tasks = task_by_group[group_id]
        group_results = result_by_group[group_id]
        trace, point = point_by_group[group_id]
        if len(group_tasks) != len(group_results) or not group_results:
            raise ValueError(f'group candidate count mismatch: {group_id}')
        if any(result.status != 'OK' or result.reward is None for result in group_results):
            raise ValueError(f'group contains non-OK result: {group_id}')
        baseline_results = [result for result in group_results if result.is_baseline_candidate]
        if len(baseline_results) != 1:
            raise ValueError(f'group must contain exactly one baseline result: {group_id}')
        baseline_result = baseline_results[0]
        baseline_candidate = _candidate_by_index(point, point.baseline_candidate_index)
        baseline_reward = float(baseline_result.reward)
        baseline_feature = complete_action_feature(point.option_vectors, baseline_candidate['action'])
        result_by_index = {int(result.candidate_index): result for result in group_results}
        if set(result_by_index) != {int(candidate['candidate_index']) for candidate in point.candidates}:
            raise ValueError(f'candidate index set mismatch: {group_id}')

        alternatives = [
            candidate for candidate in point.candidates
            if int(candidate['candidate_index']) != int(point.baseline_candidate_index)
        ]
        alternatives.sort(key=lambda candidate: str(candidate['canonical_identity']))
        ordered_candidates = [baseline_candidate] + alternatives
        candidate_rows: list[dict[str, Any]] = []
        for ordered_index, candidate in enumerate(ordered_candidates):
            candidate_index = int(candidate['candidate_index'])
            result = result_by_index[candidate_index]
            reward = float(result.reward)
            reward_delta = reward - baseline_reward
            if reward_delta > 0.0:
                outcome_class = 'IMPROVED'
            elif reward_delta < 0.0:
                outcome_class = 'WORSE'
            else:
                outcome_class = 'EQUAL'
            candidate_rows.append(
                {
                    'index': ordered_index,
                    'original_candidate_index': candidate_index,
                    'canonical_identity': str(candidate['canonical_identity']),
                    'action': [int(value) for value in candidate['action']],
                    'feature': [float(value) for value in complete_action_feature(point.option_vectors, candidate['action'])],
                    'family': _candidate_family(candidate),
                    'reward': reward,
                    'reward_delta': reward_delta,
                    'outcome_class': outcome_class,
                }
            )
        best_alternatives = [
            candidate for candidate in candidate_rows[1:]
            if float(candidate['reward']) > baseline_reward
        ]
        if best_alternatives:
            best_reward = max(float(candidate['reward']) for candidate in best_alternatives)
            teacher = min(
                (candidate for candidate in best_alternatives if float(candidate['reward']) == best_reward),
                key=lambda candidate: str(candidate['canonical_identity']),
            )
            teacher_index = int(teacher['index'])
        else:
            teacher_index = 0
        category = 'OVERRIDE_BENEFICIAL' if teacher_index != 0 else 'BASELINE_PREFERRED'
        group_rows.append(
            {
                'branch_group_id': group_id,
                'source_episode_id': trace.episode_id,
                'opponent_id': trace.opponent_id,
                'seat': int(trace.seat),
                'seed': int(trace.seed),
                'branch_step_index': int(point.step_index),
                'context': _context(point),
                'split': episode_split(trace.episode_id),
                'state_vector': [float(value) for value in point.state_vector],
                'baseline_candidate_feature': [float(value) for value in baseline_feature],
                'baseline_reward': baseline_reward,
                'baseline_identity': str(baseline_candidate['canonical_identity']),
                'teacher_index': teacher_index,
                'group_category': category,
                'baseline_family': str(candidate_rows[0]['family']),
                'candidate_families': sorted({str(candidate['family']) for candidate in candidate_rows}),
                'candidates': candidate_rows,
            }
        )
    return group_rows


def build_groupwise_dataset(config: RolloutQConfig, round_index: int = 0) -> dict[str, Any]:
    if int(round_index) != 0:
        raise ValueError('groupwise v1 is fixed to Round 0 inputs')
    output_paths = paths()
    if output_paths.root.exists() and any(output_paths.root.iterdir()):
        raise FileExistsError(f'groupwise output already exists and is not empty: {output_paths.root}')
    rows = _build_group_rows(config, int(round_index))
    training = [row for row in rows if row['split'] == 'training']
    validation = [row for row in rows if row['split'] == 'validation']
    beneficial = [row for row in rows if row['group_category'] == 'OVERRIDE_BENEFICIAL']
    baseline_preferred = [row for row in rows if row['group_category'] == 'BASELINE_PREFERRED']
    state_dim = len(rows[0]['state_vector']) if rows else None
    action_dim = len(rows[0]['candidates'][0]['feature']) if rows else None
    payload = {
        'schema_version': GROUPWISE_DATASET_SCHEMA,
        'source_round': 0,
        'source_inputs': {
            'source_traces': str(round_dir(config, 0) / 'source_traces'),
            'tasks': str(round_dir(config, 0) / 'tasks' / 'all_tasks.jsonl'),
            'branch_results': str(round_dir(config, 0) / 'branch_results' / 'all_results.jsonl'),
        },
        'state_dim': state_dim,
        'action_feature_dim': action_dim,
        'group_count': len(rows),
        'training_groups': len(training),
        'validation_groups': len(validation),
        'OVERRIDE_BENEFICIAL_groups': len(beneficial),
        'BASELINE_PREFERRED_groups': len(baseline_preferred),
        'rows': rows,
    }
    summary = {
        'schema_version': 'archaludon-groupwise-dataset-summary-v1',
        'source_round': 0,
        'dataset_path': str(output_paths.dataset),
        'group_count': len(rows),
        'training_groups': len(training),
        'validation_groups': len(validation),
        'OVERRIDE_BENEFICIAL_groups': len(beneficial),
        'BASELINE_PREFERRED_groups': len(baseline_preferred),
        'state_dim': state_dim,
        'action_feature_dim': action_dim,
    }
    _write_json_new(output_paths.dataset, payload)
    _write_json_new(output_paths.dataset_summary, summary)
    return summary


def load_groupwise_dataset() -> dict[str, Any]:
    path = paths().dataset
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema_version') != GROUPWISE_DATASET_SCHEMA:
        raise ValueError('unexpected groupwise dataset schema')
    return value


def _seed_everything(seed: int) -> None:
    random.seed(int(seed))
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))


def _group_tensors(group: Mapping[str, Any]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    candidates = group['candidates']
    states = torch.tensor([group['state_vector']] * len(candidates), dtype=torch.float32)
    candidate_features = torch.tensor([candidate['feature'] for candidate in candidates], dtype=torch.float32)
    baseline_features = torch.tensor([group['baseline_candidate_feature']] * len(candidates), dtype=torch.float32)
    return states, candidate_features, baseline_features


def _batch_tensors(groups: Sequence[Mapping[str, Any]]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, list[int]]:
    states: list[torch.Tensor] = []
    candidates: list[torch.Tensor] = []
    baselines: list[torch.Tensor] = []
    lengths: list[int] = []
    for group in groups:
        group_state, group_candidates, group_baseline = _group_tensors(group)
        states.append(group_state)
        candidates.append(group_candidates)
        baselines.append(group_baseline)
        lengths.append(len(group['candidates']))
    return torch.cat(states), torch.cat(candidates), torch.cat(baselines), lengths


def _groupwise_batch_loss(model: Any, groups: Sequence[Mapping[str, Any]]) -> torch.Tensor:
    states, candidates, baselines, lengths = _batch_tensors(groups)
    logits = model(states, candidates, baselines)
    losses: list[torch.Tensor] = []
    start = 0
    for group, length in zip(groups, lengths):
        group_logits = logits[start:start + length].unsqueeze(0)
        target = torch.tensor([int(group['teacher_index'])], dtype=torch.long)
        losses.append(F.cross_entropy(group_logits, target))
        start += length
    return torch.stack(losses).mean()


def _balanced_order(groups: Sequence[Mapping[str, Any]], seed: int, epoch: int) -> list[int]:
    beneficial = [index for index, group in enumerate(groups) if group['group_category'] == 'OVERRIDE_BENEFICIAL']
    baseline = [index for index, group in enumerate(groups) if group['group_category'] == 'BASELINE_PREFERRED']
    if not beneficial or not baseline:
        raise ValueError('training groups must contain both group categories')
    rng = random.Random(int(seed) + int(epoch))
    target = max(len(beneficial), len(baseline))
    beneficial_sample = [beneficial[index % len(beneficial)] for index in range(target)]
    baseline_sample = [baseline[index % len(baseline)] for index in range(target)]
    rng.shuffle(beneficial_sample)
    rng.shuffle(baseline_sample)
    order: list[int] = []
    for left, right in zip(beneficial_sample, baseline_sample):
        order.extend((left, right))
    rng.shuffle(order)
    return order


def _evaluate_groups(model: Any, groups: Sequence[Mapping[str, Any]], batch_size: int) -> tuple[float, list[dict[str, Any]]]:
    model.eval()
    losses: list[float] = []
    predictions: list[dict[str, Any]] = []
    for start in range(0, len(groups), int(batch_size)):
        batch = list(groups[start:start + int(batch_size)])
        with torch.no_grad():
            loss = _groupwise_batch_loss(model, batch)
            states, candidates, baselines, lengths = _batch_tensors(batch)
            logits = model(states, candidates, baselines).detach().cpu()
        losses.append(float(loss.item()) * len(batch))
        offset = 0
        for group, length in zip(batch, lengths):
            values = [float(value) for value in logits[offset:offset + length].tolist()]
            selected_index = max(range(length), key=lambda index: (values[index], str(group['candidates'][index]['canonical_identity'])))
            predictions.append(
                {
                    'branch_group_id': str(group['branch_group_id']),
                    'selected_index': int(selected_index),
                    'teacher_index': int(group['teacher_index']),
                    'scores': values,
                }
            )
            offset += length
    return sum(losses) / len(groups) if groups else float('nan'), predictions


def _save_groupwise_checkpoint(path: Path, model: Any, model_config: ModelConfig, *, seed: int, metrics: Mapping[str, Any]) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            'schema_version': GROUPWISE_CHECKPOINT_SCHEMA,
            'model_state': {key: value.detach().cpu() for key, value in model.state_dict().items()},
            'model_config': model_config.to_dict(),
            'training_seed': int(seed),
            'training_metrics': dict(metrics),
            'source_rounds': [0],
        },
        path,
    )


def _load_groupwise_checkpoint(path: Path) -> tuple[Any, ModelConfig, Mapping[str, Any]]:
    value = torch.load(path, map_location='cpu', weights_only=False)
    if value.get('schema_version') != GROUPWISE_CHECKPOINT_SCHEMA:
        raise ValueError(f'unexpected groupwise checkpoint schema: {path}')
    raw_config = value.get('model_config')
    config = ModelConfig(
        state_dim=int(raw_config['state_dim']),
        action_feature_dim=int(raw_config['action_feature_dim']),
        state_hidden_dim=int(raw_config.get('state_hidden_dim', 256)),
        action_hidden_dim=int(raw_config.get('action_hidden_dim', 128)),
    )
    model = build_model(config)
    model.load_state_dict(value['model_state'])
    model.eval()
    return model, config, value


def _outcome_counts(groups: Sequence[Mapping[str, Any]], predictions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_id = {str(prediction['branch_group_id']): prediction for prediction in predictions}
    selected = [group['candidates'][int(by_id[str(group['branch_group_id'])]['selected_index'])] for group in groups]
    counts = Counter(str(candidate['outcome_class']) for candidate in selected)
    reward_total = sum(float(candidate['reward_delta']) for candidate in selected)
    selected_alternatives = [candidate for candidate in selected if int(candidate['index']) != 0]
    alt_counts = Counter(str(candidate['outcome_class']) for candidate in selected_alternatives)
    alt_reward_total = sum(float(candidate['reward_delta']) for candidate in selected_alternatives)
    return {
        'selected_group_count': len(selected),
        'selected_IMPROVED': int(counts.get('IMPROVED', 0)),
        'selected_EQUAL': int(counts.get('EQUAL', 0)),
        'selected_WORSE': int(counts.get('WORSE', 0)),
        'selected_reward_delta_total': reward_total,
        'selected_reward_delta_mean': reward_total / len(selected) if selected else None,
        'selected_alternative_group_count': len(selected_alternatives),
        'selected_alternative_IMPROVED': int(alt_counts.get('IMPROVED', 0)),
        'selected_alternative_EQUAL': int(alt_counts.get('EQUAL', 0)),
        'selected_alternative_WORSE': int(alt_counts.get('WORSE', 0)),
        'selected_alternative_reward_delta_total': alt_reward_total,
        'selected_alternative_reward_delta_mean': alt_reward_total / len(selected_alternatives) if selected_alternatives else None,
    }


def _train_one_seed(
    config: RolloutQConfig,
    groups: Sequence[Mapping[str, Any]],
    *,
    seed: int,
    model_config: ModelConfig,
) -> dict[str, Any]:
    train_groups = [group for group in groups if group['split'] == 'training']
    validation_groups = [group for group in groups if group['split'] == 'validation']
    _seed_everything(seed)
    model = build_model(model_config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    best_loss = float('inf')
    best_state: dict[str, torch.Tensor] | None = None
    stale = 0
    history: list[dict[str, Any]] = []
    for epoch in range(config.maximum_epochs):
        model.train()
        order = _balanced_order(train_groups, seed, epoch)
        total_loss = 0.0
        total_groups = 0
        for start in range(0, len(order), int(config.batch_size)):
            batch = [train_groups[index] for index in order[start:start + int(config.batch_size)]]
            optimizer.zero_grad(set_to_none=True)
            loss = _groupwise_batch_loss(model, batch)
            if not torch.isfinite(loss):
                raise FloatingPointError('non-finite groupwise training loss')
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += float(loss.item()) * len(batch)
            total_groups += len(batch)
        validation_loss, validation_predictions = _evaluate_groups(model, validation_groups, config.batch_size)
        history.append({
            'epoch': epoch + 1,
            'train_loss': total_loss / max(1, total_groups),
            'validation_loss': validation_loss,
        })
        if validation_loss < best_loss:
            best_loss = validation_loss
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= config.early_stopping_patience:
                break
    if best_state is None:
        raise RuntimeError('groupwise training did not produce a validation checkpoint')
    model.load_state_dict(best_state)
    validation_loss, predictions = _evaluate_groups(model, validation_groups, config.batch_size)
    prediction_by_id = {str(prediction['branch_group_id']): prediction for prediction in predictions}
    top1 = sum(int(prediction['selected_index'] == prediction['teacher_index']) for prediction in predictions)
    beneficial_groups = [group for group in validation_groups if group['group_category'] == 'OVERRIDE_BENEFICIAL']
    baseline_groups = [group for group in validation_groups if group['group_category'] == 'BASELINE_PREFERRED']
    beneficial_recall = sum(
        int(prediction_by_id[str(group['branch_group_id'])]['selected_index'] != 0)
        for group in beneficial_groups
    ) / len(beneficial_groups) if beneficial_groups else None
    baseline_accuracy = sum(
        int(prediction_by_id[str(group['branch_group_id'])]['selected_index'] == 0)
        for group in baseline_groups
    ) / len(baseline_groups) if baseline_groups else None
    metrics = {
        'seed': int(seed),
        'epochs_completed': len(history),
        'validation_loss': validation_loss,
        'group_top1_accuracy': top1 / len(predictions) if predictions else None,
        'OVERRIDE_BENEFICIAL_recall': beneficial_recall,
        'BASELINE_PREFERRED_accuracy': baseline_accuracy,
        **_outcome_counts(validation_groups, predictions),
        'training_group_count': len(train_groups),
        'validation_group_count': len(validation_groups),
        'training_balanced_sampling': {
            'OVERRIDE_BENEFICIAL_fraction': 0.5,
            'BASELINE_PREFERRED_fraction': 0.5,
            'sampling': 'with_replacement_to_equal_class_epoch_size',
        },
        'history': history,
    }
    checkpoint = paths().checkpoint_dir / f'groupwise_seed{int(seed)}.pt'
    _save_groupwise_checkpoint(checkpoint, model, model_config, seed=seed, metrics=metrics)
    metrics['checkpoint'] = str(checkpoint)
    return metrics


def train_groupwise(config: RolloutQConfig) -> dict[str, Any]:
    dataset = load_groupwise_dataset()
    groups = dataset['rows']
    if not groups:
        raise ValueError('groupwise dataset is empty')
    model_config = ModelConfig(
        state_dim=int(dataset['state_dim']),
        action_feature_dim=int(dataset['action_feature_dim']),
    )
    if paths().training_summary.exists():
        raise FileExistsError(paths().training_summary)
    seed_results = [
        _train_one_seed(config, groups, seed=seed, model_config=model_config)
        for seed in config.training_seeds
    ]
    summary = {
        'schema_version': GROUPWISE_TRAINING_SCHEMA,
        'source_round': 0,
        'model_config': model_config.to_dict(),
        'seed_results': seed_results,
    }
    _write_json_new(paths().training_summary, summary)
    return summary


def _aggregate_selected(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(record['outcome_class']) for record in records)
    total = len(records)
    reward_total = sum(float(record['reward_delta']) for record in records)
    return {
        'selected_group_count': total,
        'IMPROVED': int(counts.get('IMPROVED', 0)),
        'EQUAL': int(counts.get('EQUAL', 0)),
        'WORSE': int(counts.get('WORSE', 0)),
        'reward_delta_total': reward_total,
        'reward_delta_mean': reward_total / total if total else None,
    }


def _format_number(value: Any) -> str:
    if value is None:
        return 'null'
    if isinstance(value, float):
        return f'{value:.6f}'
    return str(value)


def calibrate_groupwise(config: RolloutQConfig) -> dict[str, Any]:
    dataset = load_groupwise_dataset()
    validation_groups = [group for group in dataset['rows'] if group['split'] == 'validation']
    checkpoint_paths = [paths().checkpoint_dir / f'groupwise_seed{int(seed)}.pt' for seed in config.training_seeds]
    models = [_load_groupwise_checkpoint(path)[0] for path in checkpoint_paths]
    predictions_by_model: list[dict[str, dict[str, Any]]] = []
    for model in models:
        _, predictions = _evaluate_groups(model, validation_groups, config.batch_size)
        predictions_by_model.append({str(prediction['branch_group_id']): prediction for prediction in predictions})

    seed_metrics: list[dict[str, Any]] = []
    for seed, model_predictions in zip(config.training_seeds, predictions_by_model):
        top1 = sum(int(prediction['selected_index'] == prediction['teacher_index']) for prediction in model_predictions.values())
        beneficial = [group for group in validation_groups if group['group_category'] == 'OVERRIDE_BENEFICIAL']
        baseline = [group for group in validation_groups if group['group_category'] == 'BASELINE_PREFERRED']
        beneficial_recall = sum(int(model_predictions[str(group['branch_group_id'])]['selected_index'] != 0) for group in beneficial) / len(beneficial) if beneficial else None
        baseline_accuracy = sum(int(model_predictions[str(group['branch_group_id'])]['selected_index'] == 0) for group in baseline) / len(baseline) if baseline else None
        selected_records = []
        for group in validation_groups:
            selected_index = int(model_predictions[str(group['branch_group_id'])]['selected_index'])
            selected_records.append(group['candidates'][selected_index])
        counts = Counter(str(candidate['outcome_class']) for candidate in selected_records)
        reward_total = sum(float(candidate['reward_delta']) for candidate in selected_records)
        seed_metrics.append({
            'seed': int(seed),
            'group_top1_accuracy': top1 / len(validation_groups) if validation_groups else None,
            'OVERRIDE_BENEFICIAL_recall': beneficial_recall,
            'BASELINE_PREFERRED_accuracy': baseline_accuracy,
            'selected_alternative_group_count': sum(int(int(candidate['index']) != 0) for candidate in selected_records),
            'selected_IMPROVED': int(counts.get('IMPROVED', 0)),
            'selected_EQUAL': int(counts.get('EQUAL', 0)),
            'selected_WORSE': int(counts.get('WORSE', 0)),
            'selected_reward_delta_total': reward_total,
            'selected_reward_delta_mean': reward_total / len(selected_records) if selected_records else None,
        })

    agreement_records: list[dict[str, Any]] = []
    baseline_agreement = 0
    alternative_agreement = 0
    for group in validation_groups:
        group_id = str(group['branch_group_id'])
        predictions = [prediction_map[group_id] for prediction_map in predictions_by_model]
        selected_indices = [int(prediction['selected_index']) for prediction in predictions]
        if len(set(selected_indices)) != 1:
            continue
        selected_index = selected_indices[0]
        if selected_index == 0:
            baseline_agreement += 1
            continue
        alternative_agreement += 1
        selected = group['candidates'][selected_index]
        margins = [
            float(prediction['scores'][selected_index]) - float(prediction['scores'][0])
            for prediction in predictions
        ]
        agreement_records.append({
            'branch_group_id': group_id,
            'selected_index': selected_index,
            'selected_canonical_identity': str(selected['canonical_identity']),
            'model_selected_indices': selected_indices,
            'model_margins': margins,
            'ensemble_margin': sum(margins) / len(margins),
            'outcome_class': str(selected['outcome_class']),
            'reward_delta': float(selected['reward_delta']),
            'context': int(group['context']),
            'family': str(selected['family']),
        })

    threshold_summary = []
    for threshold in (0.0, 0.1, 0.2, 0.5, 1.0, 2.0):
        selected = [record for record in agreement_records if float(record['ensemble_margin']) >= threshold]
        threshold_summary.append({'threshold': threshold, **_aggregate_selected(selected)})

    ensemble_summary = {
        'three_model_agreement_group_count': baseline_agreement + alternative_agreement,
        'baseline_agreement_count': baseline_agreement,
        'alternative_agreement_count': alternative_agreement,
        'alternative_agreement_outcomes': _aggregate_selected(agreement_records),
        'alternative_agreement_records': agreement_records,
    }
    output = {
        'schema_version': GROUPWISE_CALIBRATION_SCHEMA,
        'source_round': 0,
        'dataset_path': str(paths().dataset),
        'validation_group_count': len(validation_groups),
        'checkpoint_paths': [str(path) for path in checkpoint_paths],
        'score_margin_definition': 'mean over the three model margins: selected alternative score minus baseline score',
        'seed_metrics': seed_metrics,
        'ensemble': ensemble_summary,
        'score_margin_thresholds': threshold_summary,
    }
    _write_json_new(paths().calibration_json, output)

    lines = [
        '# Groupwise conservative policy selection v1: Round 0 validation',
        '',
        f"- Validation groups: `{len(validation_groups)}`",
        f"- 3-model agreement groups: `{ensemble_summary['three_model_agreement_group_count']}`",
        f"- Baseline agreement: `{baseline_agreement}`; alternative agreement: `{alternative_agreement}`",
        '- Score margin: mean of three `(selected alternative score - baseline score)` values.',
        '',
        '## Per-seed validation',
        '',
        '| seed | top-1 accuracy | beneficial recall | baseline-preferred accuracy | selected alternatives | IMPROVED | EQUAL | WORSE | reward delta total | reward delta mean |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for item in seed_metrics:
        lines.append('| ' + ' | '.join([
            str(item['seed']), _format_number(item['group_top1_accuracy']), _format_number(item['OVERRIDE_BENEFICIAL_recall']),
            _format_number(item['BASELINE_PREFERRED_accuracy']), str(item['selected_alternative_group_count']),
            str(item['selected_IMPROVED']), str(item['selected_EQUAL']), str(item['selected_WORSE']),
            _format_number(item['selected_reward_delta_total']), _format_number(item['selected_reward_delta_mean']),
        ]) + ' |')
    lines += [
        '',
        '## 3-model alternative agreement',
        '',
        '| agreement groups | IMPROVED | EQUAL | WORSE | reward delta total | reward delta mean |',
        '|---:|---:|---:|---:|---:|---:|',
        '| ' + ' | '.join([
            str(alternative_agreement),
            str(ensemble_summary['alternative_agreement_outcomes']['IMPROVED']),
            str(ensemble_summary['alternative_agreement_outcomes']['EQUAL']),
            str(ensemble_summary['alternative_agreement_outcomes']['WORSE']),
            _format_number(ensemble_summary['alternative_agreement_outcomes']['reward_delta_total']),
            _format_number(ensemble_summary['alternative_agreement_outcomes']['reward_delta_mean']),
        ]) + ' |',
        '',
        '## Score-margin thresholds',
        '',
        '| threshold | selected | IMPROVED | EQUAL | WORSE | reward delta total | reward delta mean |',
        '|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for item in threshold_summary:
        lines.append('| ' + ' | '.join([
            _format_number(item['threshold']), str(item['selected_group_count']), str(item['IMPROVED']),
            str(item['EQUAL']), str(item['WORSE']), _format_number(item['reward_delta_total']),
            _format_number(item['reward_delta_mean']),
        ]) + ' |')
    lines += ['', 'No Round 1, new battle, branch rerun, threshold change, or formal policy change was performed.']
    if paths().calibration_markdown.exists():
        raise FileExistsError(paths().calibration_markdown)
    paths().calibration_markdown.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return output


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('build-dataset', 'train', 'calibrate'))
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = load_spec()
    if args.command == 'build-dataset':
        print(json.dumps(build_groupwise_dataset(config), ensure_ascii=False, sort_keys=True))
    elif args.command == 'train':
        print(json.dumps(train_groupwise(config), ensure_ascii=False, sort_keys=True))
    elif args.command == 'calibrate':
        result = calibrate_groupwise(config)
        print(json.dumps({
            'json_path': str(paths().calibration_json),
            'markdown_path': str(paths().calibration_markdown),
            'validation_group_count': result['validation_group_count'],
            'agreement_group_count': result['ensemble']['three_model_agreement_group_count'],
            'alternative_agreement_count': result['ensemble']['alternative_agreement_count'],
        }, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
