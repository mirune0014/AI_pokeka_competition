'''Train the fixed Rollout-Q network independently for three seeds.'''

from __future__ import annotations

import random
from typing import Any, Mapping

import torch
from torch.nn import functional as F

from .config import RolloutQConfig, round_dir, write_json
from .dataset import load_dataset
from .model import ModelConfig, build_model, compute_pair_metrics, load_checkpoint, save_checkpoint


def _tensors(rows: list[Mapping[str, Any]]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    states = torch.tensor([row['state'] for row in rows], dtype=torch.float32)
    candidates = torch.tensor([row['candidate_action'] for row in rows], dtype=torch.float32)
    baselines = torch.tensor([row['baseline_action'] for row in rows], dtype=torch.float32)
    labels = torch.tensor([row['label'] for row in rows], dtype=torch.float32)
    return states, candidates, baselines, labels


def _evaluate(model: Any, rows: list[Mapping[str, Any]], batch_size: int) -> tuple[torch.Tensor, torch.Tensor, float]:
    model.eval()
    if not rows:
        return torch.empty(0), torch.empty(0), float('nan')
    states, candidates, baselines, labels = _tensors(rows)
    logits_parts: list[torch.Tensor] = []
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            logits_parts.append(model(states[start:start + batch_size], candidates[start:start + batch_size], baselines[start:start + batch_size]))
    logits = torch.cat(logits_parts)
    loss = F.binary_cross_entropy_with_logits(logits, labels)
    return logits, labels, float(loss.item())


def _outcome_counts(rows: list[Mapping[str, Any]]) -> dict[str, int]:
    return {
        'improved': sum(int(row.get('outcome_class') == 'IMPROVED') for row in rows),
        'equal': sum(int(row.get('outcome_class') == 'EQUAL') for row in rows),
        'worse': sum(int(row.get('outcome_class') == 'WORSE') for row in rows),
    }


def _threshold_metrics(logits: torch.Tensor, labels: torch.Tensor, threshold: float = 0.80) -> dict[str, Any]:
    probabilities = torch.sigmoid(logits.detach().cpu().float())
    labels = labels.detach().cpu().float()
    predicted = probabilities >= float(threshold)
    actual = labels >= 0.5
    predicted_count = int(predicted.sum().item())
    true_positive = int((predicted & actual).sum().item())
    actual_positive = int(actual.sum().item())
    return {
        'validation_positive_rate': (actual_positive / int(labels.numel())) if labels.numel() else None,
        'validation_precision_at_0_80': (true_positive / predicted_count) if predicted_count else None,
        'validation_recall_at_0_80': (
            (true_positive / actual_positive)
            if actual_positive
            else None
        ),
        'validation_predicted_positive_count_at_0_80': predicted_count,
    }


def _seed_everything(seed: int) -> None:
    random.seed(int(seed))
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))


def _train_seed(
    config: RolloutQConfig,
    *,
    through_round: int,
    seed: int,
    rows: list[Mapping[str, Any]],
    model_config: ModelConfig,
) -> dict[str, Any]:
    train_rows = [row for row in rows if row.get('split') == 'training']
    validation_rows = [row for row in rows if row.get('split') == 'validation']
    if not train_rows or not validation_rows:
        raise ValueError('dataset does not contain both train and validation episodes')
    validation_labels = {
        float(row["label"])
        for row in validation_rows
    }
    if validation_labels != {0.0, 1.0}:
        raise ValueError(
            "validation must contain both strict-improvement "
            "and non-improvement rows"
        )
    _seed_everything(seed)
    model = build_model(model_config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    best_loss = float('inf')
    best_state: dict[str, torch.Tensor] | None = None
    stale = 0
    history: list[dict[str, Any]] = []
    for epoch in range(config.maximum_epochs):
        model.train()
        order = list(range(len(train_rows)))
        random.Random(seed + epoch).shuffle(order)
        total_loss = 0.0
        total_count = 0
        for start in range(0, len(order), config.batch_size):
            indices = order[start:start + config.batch_size]
            batch = [train_rows[index] for index in indices]
            states, candidates, baselines, labels = _tensors(batch)
            optimizer.zero_grad(set_to_none=True)
            logits = model(states, candidates, baselines)
            loss = F.binary_cross_entropy_with_logits(logits, labels)
            if not torch.isfinite(loss):
                raise FloatingPointError('non-finite Rollout-Q training loss')
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += float(loss.item()) * len(batch)
            total_count += len(batch)
        val_logits, val_labels, val_loss = _evaluate(model, validation_rows, config.batch_size)
        history.append({'epoch': epoch + 1, 'train_loss': total_loss / max(1, total_count), 'validation_loss': val_loss})
        if val_loss < best_loss:
            best_loss = val_loss
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= config.early_stopping_patience:
                break
    if best_state is None:
        raise RuntimeError('training did not produce a validation checkpoint')
    model.load_state_dict(best_state)
    val_logits, val_labels, val_loss = _evaluate(model, validation_rows, config.batch_size)
    metrics = compute_pair_metrics(val_logits, val_labels, val_loss)
    train_counts = _outcome_counts(train_rows)
    validation_counts = _outcome_counts(validation_rows)
    metrics.update(
        {
            'training_rows': len(train_rows),
            'validation_rows': len(validation_rows),
            'epochs_completed': len(history),
            'history': history,
            'loss_to_win_pair_count': sum(int(row['baseline_reward'] == -1.0 and row['candidate_reward'] == 1.0) for row in validation_rows),
            'win_to_loss_pair_count': sum(int(row['baseline_reward'] == 1.0 and row['candidate_reward'] == -1.0) for row in validation_rows),
            'improved_training_rows': train_counts['improved'],
            'equal_training_rows': train_counts['equal'],
            'worse_training_rows': train_counts['worse'],
            'improved_validation_rows': validation_counts['improved'],
            'equal_validation_rows': validation_counts['equal'],
            'worse_validation_rows': validation_counts['worse'],
            **_threshold_metrics(val_logits, val_labels, 0.80),
        }
    )
    checkpoint = round_dir(config, through_round) / 'checkpoints' / f'rollout_q_seed{int(seed)}.pt'
    save_checkpoint(
        checkpoint,
        model,
        model_config,
        seed=seed,
        metrics=metrics,
        source_rounds=range(through_round + 1),
    )
    # A direct save/reload check is intentionally ordinary and local; the
    # deployment checkpoint itself contains no optimizer state.
    reloaded, _, _ = load_checkpoint(checkpoint)
    for name, expected in model.state_dict().items():
        actual = reloaded.state_dict()[name]
        if not torch.equal(actual, expected):
            raise RuntimeError(f'checkpoint reload tensor mismatch: {name}')
    if set(reloaded.state_dict()) != set(model.state_dict()):
        raise RuntimeError('checkpoint reload parameter set differs')
    return {'seed': int(seed), 'checkpoint': str(checkpoint), **metrics}


def train_through_round(config: RolloutQConfig, through_round: int) -> dict[str, Any]:
    dataset = load_dataset(config, through_round)
    rows = dataset.get('rows')
    if not isinstance(rows, list):
        raise ValueError('dataset rows are missing')
    if not rows:
        raise ValueError('dataset has no candidate rows')
    state_dim = int(dataset.get('state_dim') or len(rows[0]['state']))
    action_dim = int(dataset.get('action_feature_dim') or len(rows[0]['candidate_action']))
    model_config = ModelConfig(state_dim=state_dim, action_feature_dim=action_dim)
    seed_results = [
        _train_seed(
            config,
            through_round=int(through_round),
            seed=seed,
            rows=rows,
            model_config=model_config,
        )
        for seed in config.training_seeds
    ]
    summary = {
        'schema_version': 'archaludon-training-summary-v1',
        'through_round': int(through_round),
        'model_config': model_config.to_dict(),
        'seed_results': seed_results,
    }
    write_json(config.output_dir / f'training_through_round_{int(through_round):02d}_summary.json', summary)
    return summary


__all__ = ['train_through_round']
