from __future__ import annotations

from pathlib import Path

import torch

from research.experiments.archaludon_rollout_q_v1.rollout_q.model import ModelConfig, build_model, load_checkpoint, save_checkpoint


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
    model.eval()
    assert torch.allclose(model(state, candidate, baseline), reloaded(state, candidate, baseline))
