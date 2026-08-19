"""Expected terminal-reward model and its fixed listwise loss."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch
from torch import nn
from torch.nn import functional as F

from .semantic_encoder import SemanticEncoder, SemanticVocab


@dataclass(frozen=True)
class ModelConfig:
    vocab: SemanticVocab
    dropout: float = 0.10

    def to_dict(self) -> dict[str, Any]:
        return {"vocab": self.vocab.to_dict(), "dropout": self.dropout}


class ExpectedQModel(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.config = config
        self.encoder = SemanticEncoder(config.vocab)
        self.q_head = nn.Sequential(
            nn.Linear(384, 256),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(self, public_state: Mapping[str, Any], candidate: Mapping[str, Any], *, context: int = 0) -> torch.Tensor:
        state_hidden, candidate_hidden = self.encoder(public_state, candidate, context=context)
        if state_hidden.ndim != 1 or candidate_hidden.ndim != 1:
            raise ValueError("single-group model forward expects rank-1 encodings")
        output = self.q_head(torch.cat((state_hidden, candidate_hidden), dim=-1)).squeeze(-1)
        if not bool(torch.isfinite(output).all()):
            raise FloatingPointError("non-finite expected-Q output")
        return torch.tanh(output)

    def score_group(self, row: Mapping[str, Any]) -> torch.Tensor:
        public_state = row.get("public_state")
        candidates = row.get("candidates")
        if not isinstance(public_state, Mapping) or not isinstance(candidates, list) or not candidates:
            raise ValueError("dataset group is missing public_state/candidates")
        context = int(row.get("context", 0) or 0)
        return torch.stack([self.forward(public_state, candidate, context=context) for candidate in candidates])


def build_model(vocab: SemanticVocab) -> ExpectedQModel:
    return ExpectedQModel(ModelConfig(vocab=vocab))


def group_loss(
    predicted_q: torch.Tensor,
    target_q: torch.Tensor,
    *,
    huber_beta: float,
    temperature: float,
    listwise_weight: float,
) -> torch.Tensor:
    if predicted_q.shape != target_q.shape or predicted_q.ndim != 1:
        raise ValueError("predicted and target Q vectors must have equal rank-1 shape")
    huber = F.smooth_l1_loss(predicted_q, target_q, beta=float(huber_beta))
    teacher_probability = torch.softmax(target_q / float(temperature), dim=0)
    listwise = -(teacher_probability * torch.log_softmax(predicted_q, dim=0)).sum()
    loss = huber + float(listwise_weight) * listwise
    if not bool(torch.isfinite(loss).all()):
        raise FloatingPointError("non-finite expected-Q loss")
    return loss


def mean_regret(predictions: Sequence[torch.Tensor], targets: Sequence[torch.Tensor]) -> float:
    values: list[float] = []
    for predicted, target in zip(predictions, targets):
        if predicted.numel() == 0:
            continue
        selected = int(torch.argmax(predicted).item())
        values.append(float(torch.max(target).item() - target[selected].item()))
    return sum(values) / len(values) if values else float("nan")


def save_checkpoint(path: Path, model: ExpectedQModel, *, seed: int, metrics: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "schema_version": "archaludon-multidet-q-checkpoint-v1",
            "seed": int(seed),
            "model_config": model.config.to_dict(),
            "state_dict": model.state_dict(),
            "metrics": dict(metrics),
        },
        path,
    )


def load_checkpoint(path: Path, *, map_location: str | torch.device = "cpu") -> tuple[ExpectedQModel, dict[str, Any]]:
    payload = torch.load(path, map_location=map_location, weights_only=False)
    if payload.get("schema_version") != "archaludon-multidet-q-checkpoint-v1":
        raise ValueError("unexpected expected-Q checkpoint schema")
    raw_vocab = payload["model_config"]["vocab"]
    vocab = SemanticVocab(max_card_id=int(raw_vocab["max_card_id"]), max_attack_id=int(raw_vocab["max_attack_id"]))
    config = ModelConfig(vocab=vocab, dropout=float(payload["model_config"].get("dropout", 0.10)))
    model = ExpectedQModel(config)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return model, payload


__all__ = [
    "ExpectedQModel",
    "ModelConfig",
    "build_model",
    "group_loss",
    "load_checkpoint",
    "mean_regret",
    "save_checkpoint",
]
