from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import torch

from research.experiments.archaludon_rollout_q_v1.rollout_q.config import load_spec
from research.experiments.archaludon_rollout_q_v1.rollout_q.model import ModelConfig, build_model, load_checkpoint, save_checkpoint
from research.experiments.archaludon_rollout_q_v1.rollout_q.train import _threshold_metrics, _train_seed


def _training_row(
    *,
    split: str,
    label: float,
) -> dict:
    improved = float(label) == 1.0

    return {
        "split": split,
        "state": [0.0, 0.0, 0.0, 0.0],
        "candidate_action": [0.0] * 6,
        "baseline_action": [0.0] * 6,
        "label": float(label),
        "outcome_class": (
            "IMPROVED"
            if improved
            else "EQUAL"
        ),
        "baseline_reward": -1.0,
        "candidate_reward": (
            1.0
            if improved
            else -1.0
        ),
    }


def test_forward_backward_save_reload(tmp_path: Path):
    config = ModelConfig(state_dim=4, action_feature_dim=6)
    model = build_model(config)
    state = torch.randn(8, 4)
    candidate = torch.randn(8, 6)
    baseline = torch.randn(8, 6)
    labels = torch.zeros(8)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
    before = float(torch.nn.functional.binary_cross_entropy_with_logits(model(state, candidate, baseline), labels))
    optimizer.zero_grad()
    loss = torch.nn.functional.binary_cross_entropy_with_logits(model(state, candidate, baseline), labels)
    loss.backward()
    optimizer.step()
    after = float(torch.nn.functional.binary_cross_entropy_with_logits(model(state, candidate, baseline), labels))
    assert torch.isfinite(torch.tensor(after))
    path = tmp_path / 'checkpoint.pt'
    save_checkpoint(path, model, config, seed=1, metrics={'loss': after}, source_rounds=[0])
    reloaded, loaded_config, _ = load_checkpoint(path)
    assert loaded_config == config
    for name, expected in model.state_dict().items():
        assert name in reloaded.state_dict()
        assert torch.equal(reloaded.state_dict()[name], expected)
    assert set(reloaded.state_dict()) == set(model.state_dict())


def test_threshold_metrics_zero_recall_when_no_positive_is_predicted():
    logits = torch.tensor([-10.0, -10.0], dtype=torch.float32)
    labels = torch.tensor([1.0, 0.0], dtype=torch.float32)

    metrics = _threshold_metrics(
        logits,
        labels,
        threshold=0.80,
    )

    assert (
        metrics[
            "validation_predicted_positive_count_at_0_80"
        ]
        == 0
    )
    assert metrics["validation_precision_at_0_80"] is None
    assert metrics["validation_recall_at_0_80"] == 0.0
    assert metrics["validation_positive_rate"] == 0.5


@pytest.mark.parametrize(
    "validation_label",
    [0.0, 1.0],
)
def test_train_seed_rejects_single_class_validation(
    tmp_path: Path,
    validation_label: float,
):
    config = replace(
        load_spec(),
        output_root=str(tmp_path),
        maximum_epochs=1,
        early_stopping_patience=1,
        batch_size=2,
    )

    rows = [
        _training_row(
            split="training",
            label=0.0,
        ),
        _training_row(
            split="training",
            label=1.0,
        ),
        _training_row(
            split="validation",
            label=validation_label,
        ),
        _training_row(
            split="validation",
            label=validation_label,
        ),
    ]

    model_config = ModelConfig(
        state_dim=4,
        action_feature_dim=6,
    )

    with pytest.raises(
        ValueError,
        match=(
            "validation must contain both "
            "strict-improvement and non-improvement rows"
        ),
    ):
        _train_seed(
            config,
            through_round=0,
            seed=2026080501,
            rows=rows,
            model_config=model_config,
        )
