"""Small PyTorch residual actor-critic with strict checkpoint metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence

import torch
from torch import nn

from .encoders import ACTION_DIM, ENCODER_SCHEMA_VERSION, STATE_DIM, encoder_metadata
from .reference_policy import (
    canonical_reference_prior_receipt,
    reference_prior_sha256,
    validate_reference_prior_identity,
)


MODEL_SCHEMA_VERSION = "residual-actor-critic-v2"


@dataclass(frozen=True)
class ModelConfig:
    state_dim: int = STATE_DIM
    action_dim: int = ACTION_DIM
    hidden_dim: int = 96


class ResidualActorCritic(nn.Module):
    def __init__(self, config: ModelConfig | None = None) -> None:
        super().__init__()
        self.config = config or ModelConfig()
        self.state_encoder = nn.Sequential(
            nn.Linear(self.config.state_dim, self.config.hidden_dim),
            nn.Tanh(),
            nn.Linear(self.config.hidden_dim, self.config.hidden_dim),
            nn.Tanh(),
        )
        self.action_encoder = nn.Sequential(
            nn.Linear(self.config.action_dim, self.config.hidden_dim),
            nn.Tanh(),
        )
        self.residual_head = nn.Sequential(
            nn.Linear(self.config.hidden_dim * 2, self.config.hidden_dim),
            nn.Tanh(),
            nn.Linear(self.config.hidden_dim, 1),
        )
        self.value_head = nn.Sequential(
            nn.Linear(self.config.hidden_dim, self.config.hidden_dim),
            nn.Tanh(),
            nn.Linear(self.config.hidden_dim, 1),
        )
        final = self.residual_head[-1]
        nn.init.zeros_(final.weight)
        nn.init.zeros_(final.bias)

    def forward(
        self, state_vectors: torch.Tensor, action_vectors: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Evaluate batched states and padded/flat variable action sets.

        ``state_vectors`` may be ``[S]`` or ``[A,S]``.  For one state and A
        actions, it is expanded without copying.
        """

        if state_vectors.ndim == 1:
            state_vectors = state_vectors.unsqueeze(0)
        if action_vectors.ndim == 1:
            action_vectors = action_vectors.unsqueeze(0)
        if state_vectors.shape[0] == 1 and action_vectors.shape[0] != 1:
            state_vectors = state_vectors.expand(action_vectors.shape[0], -1)
        if state_vectors.shape[0] != action_vectors.shape[0]:
            raise ValueError("state/action batch mismatch")
        state_hidden = self.state_encoder(state_vectors)
        action_hidden = self.action_encoder(action_vectors)
        residuals = self.residual_head(
            torch.cat((state_hidden, action_hidden), dim=-1)
        ).squeeze(-1)
        # A decision has one state value, even when the state was expanded.
        value = self.value_head(state_hidden[:1]).squeeze(-1).squeeze(0)
        return residuals, value

    def predict(
        self, state_vector: Sequence[float], action_vectors: Sequence[Sequence[float]]
    ) -> tuple[list[float], float]:
        device = next(self.parameters()).device
        with torch.no_grad():
            state = torch.tensor(state_vector, dtype=torch.float32, device=device)
            actions = torch.tensor(action_vectors, dtype=torch.float32, device=device)
            residuals, value = self(state, actions)
        return residuals.detach().cpu().tolist(), float(value.detach().cpu())


def checkpoint_metadata(
    *,
    source_hashes: Mapping[str, str],
    training: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    prior_receipt = canonical_reference_prior_receipt()
    return {
        "model_schema_version": MODEL_SCHEMA_VERSION,
        "encoder": encoder_metadata(),
        "reference_prior_receipt": prior_receipt,
        "reference_prior_schema_sha256": reference_prior_sha256(prior_receipt),
        "source_hashes": dict(source_hashes),
        "training": dict(training or {}),
    }


def save_checkpoint(
    path: Path | str,
    model: ResidualActorCritic,
    metadata: Mapping[str, Any],
    *,
    optimizer: torch.optim.Optimizer | None = None,
) -> str:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model_config": asdict(model.config),
        "model_state": model.state_dict(),
        "metadata": dict(metadata),
        "optimizer_state": None if optimizer is None else optimizer.state_dict(),
    }
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        torch.save(payload, temporary)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return sha256_checkpoint(destination)


def sha256_checkpoint(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _validate_metadata(
    metadata: Mapping[str, Any],
    *,
    expected_source_hashes: Mapping[str, str] | None,
) -> None:
    if metadata.get("model_schema_version") != MODEL_SCHEMA_VERSION:
        raise ValueError("checkpoint model schema mismatch")
    encoder = metadata.get("encoder") or {}
    if (
        encoder.get("schema_version") != ENCODER_SCHEMA_VERSION
        or encoder.get("state_dim") != STATE_DIM
        or encoder.get("action_dim") != ACTION_DIM
    ):
        raise ValueError("checkpoint encoder schema/dimension mismatch")
    receipt = metadata.get("reference_prior_receipt")
    if not isinstance(receipt, Mapping):
        raise ValueError("checkpoint reference-prior receipt missing")
    validate_reference_prior_identity(
        receipt,
        metadata.get("reference_prior_schema_sha256"),
    )
    if expected_source_hashes is not None:
        actual = metadata.get("source_hashes") or {}
        if dict(actual) != dict(expected_source_hashes):
            raise ValueError("checkpoint frozen-source hashes mismatch")


def load_checkpoint(
    path: Path | str,
    *,
    expected_source_hashes: Mapping[str, str] | None = None,
    device: str | torch.device = "cpu",
) -> tuple[ResidualActorCritic, dict[str, Any], dict[str, Any] | None]:
    payload = torch.load(Path(path), map_location=device, weights_only=False)
    if not isinstance(payload, dict):
        raise ValueError("checkpoint payload must be a mapping")
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("checkpoint metadata missing")
    _validate_metadata(metadata, expected_source_hashes=expected_source_hashes)
    config = ModelConfig(**payload.get("model_config", {}))
    if config.state_dim != STATE_DIM or config.action_dim != ACTION_DIM:
        raise ValueError("checkpoint model dimensions mismatch")
    model = ResidualActorCritic(config).to(device)
    model.load_state_dict(payload["model_state"], strict=True)
    return model, metadata, payload.get("optimizer_state")
