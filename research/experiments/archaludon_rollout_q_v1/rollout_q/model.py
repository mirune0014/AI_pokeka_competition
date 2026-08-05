'''Rollout-Q candidate-versus-baseline network and checkpoint helpers.'''

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import torch
from torch import Tensor, nn
from torch.nn import functional as F


MODEL_SCHEMA = 'archaludon-rollout-q-checkpoint-v1'


@dataclass(frozen=True)
class ModelConfig:
    state_dim: int
    action_feature_dim: int
    state_hidden_dim: int = 256
    action_hidden_dim: int = 128

    def to_dict(self) -> dict[str, int]:
        return {key: int(value) for key, value in asdict(self).items()}


class RolloutQNetwork(nn.Module):
    def __init__(self, state_dim: int, action_feature_dim: int):
        super().__init__()
        self.state_encoder = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
        )
        self.action_encoder = nn.Sequential(
            nn.Linear(action_feature_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU(),
        )
        self.head = nn.Sequential(
            nn.Linear(256 + 128 + 128 + 128, 256),
            nn.ReLU(),
            nn.Dropout(0.10),
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(
        self,
        state: Tensor,
        candidate_action: Tensor,
        baseline_action: Tensor,
    ) -> Tensor:
        state_hidden = self.state_encoder(state)
        candidate_hidden = self.action_encoder(candidate_action)
        baseline_hidden = self.action_encoder(baseline_action)
        features = torch.cat(
            [state_hidden, candidate_hidden, baseline_hidden, candidate_hidden - baseline_hidden],
            dim=-1,
        )
        return self.head(features).squeeze(-1)


def build_model(model_config: ModelConfig) -> RolloutQNetwork:
    return RolloutQNetwork(model_config.state_dim, model_config.action_feature_dim)


def _safe_torch_load(path: Path, device: str | torch.device) -> Mapping[str, Any]:
    try:
        value = torch.load(path, map_location=device, weights_only=False)
    except TypeError:
        value = torch.load(path, map_location=device)
    if not isinstance(value, Mapping):
        raise ValueError('Rollout-Q checkpoint must be a mapping')
    return value


def save_checkpoint(
    path: Path,
    model: RolloutQNetwork,
    model_config: ModelConfig,
    *,
    seed: int,
    metrics: Mapping[str, Any],
    source_rounds: Iterable[int],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    payload = {
        'schema_version': MODEL_SCHEMA,
        'model_state': {key: value.detach().cpu() for key, value in model.state_dict().items()},
        'model_config': model_config.to_dict(),
        'training_seed': int(seed),
        'training_metrics': dict(metrics),
        'source_rounds': [int(value) for value in source_rounds],
    }
    torch.save(payload, path)


def load_checkpoint(path: Path, *, device: str | torch.device = 'cpu') -> tuple[RolloutQNetwork, ModelConfig, Mapping[str, Any]]:
    payload = _safe_torch_load(path, device)
    if payload.get('schema_version') != MODEL_SCHEMA:
        raise ValueError('unexpected Rollout-Q checkpoint schema')
    raw_config = payload.get('model_config')
    if not isinstance(raw_config, Mapping):
        raise ValueError('checkpoint model_config is missing')
    config = ModelConfig(
        state_dim=int(raw_config['state_dim']),
        action_feature_dim=int(raw_config['action_feature_dim']),
        state_hidden_dim=int(raw_config.get('state_hidden_dim', 256)),
        action_hidden_dim=int(raw_config.get('action_hidden_dim', 128)),
    )
    model = build_model(config)
    state = payload.get('model_state')
    if not isinstance(state, Mapping):
        raise ValueError('checkpoint model_state is missing')
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    return model, config, payload


def binary_roc_auc(logits: Tensor, labels: Tensor) -> float | None:
    labels = labels.detach().cpu().float()
    scores = logits.detach().cpu().float()
    positives = [float(scores[index]) for index in range(len(labels)) if float(labels[index]) >= 0.5]
    negatives = [float(scores[index]) for index in range(len(labels)) if float(labels[index]) < 0.5]
    if not positives or not negatives:
        return None
    wins = sum(1.0 if positive > negative else 0.5 if positive == negative else 0.0 for positive in positives for negative in negatives)
    return wins / (len(positives) * len(negatives))


def compute_pair_metrics(logits: Tensor, labels: Tensor, loss: float | None = None) -> dict[str, Any]:
    labels = labels.detach().cpu().float()
    logits = logits.detach().cpu().float()
    predictions = (logits >= 0.0).float()
    metrics: dict[str, Any] = {
        'pair_count': int(labels.numel()),
        'positive_pair_count': int((labels >= 0.5).sum().item()),
        'negative_pair_count': int((labels < 0.5).sum().item()),
        'pair_accuracy': float((predictions == labels).float().mean().item()) if labels.numel() else None,
        'roc_auc': binary_roc_auc(logits, labels),
    }
    if loss is not None:
        metrics['loss'] = float(loss)
    return metrics


__all__ = [
    'MODEL_SCHEMA',
    'ModelConfig',
    'RolloutQNetwork',
    'binary_roc_auc',
    'build_model',
    'compute_pair_metrics',
    'load_checkpoint',
    'save_checkpoint',
]
