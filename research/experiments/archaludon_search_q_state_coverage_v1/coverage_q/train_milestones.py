"""Independent m05/m10/m20 Expected-Q training and the fixed pilot step."""

from __future__ import annotations

import copy
import json
import random
from typing import Any, Mapping, Sequence

import torch

from research.experiments.archaludon_multideterminization_q_v1.multidet_q.search_runtime import _load_api

from .config import CoverageConfig, output_path, write_json
from .dataset import load_dataset
from .model_bridge import build_model, build_vocab, group_loss, load_checkpoint


MILESTONES = ("m05", "m10", "m20")


def _seed_everything(seed: int) -> None:
    random.seed(int(seed))
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))


def _targets(row: Mapping[str, Any]) -> torch.Tensor:
    return torch.tensor([float(candidate["target_q"]) for candidate in row["candidates"]], dtype=torch.float32)


def _validation(model: Any, rows: Sequence[Mapping[str, Any]], config: CoverageConfig, device: torch.device) -> tuple[float, float]:
    model.eval()
    regrets: list[float] = []
    hubers: list[float] = []
    with torch.no_grad():
        for row in rows:
            predicted = model.score_group(row).to(device)
            target = _targets(row).to(device)
            selected = int(torch.argmax(predicted).item())
            regrets.append(float(torch.max(target).item() - target[selected].item()))
            hubers.append(float(torch.nn.functional.smooth_l1_loss(predicted, target, beta=config.huber_beta).item()))
    return (sum(regrets) / len(regrets) if regrets else float("nan"), sum(hubers) / len(hubers) if hubers else float("nan"))


def _save_cpu_checkpoint(path: Any, model: Any, *, seed: int, metrics: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {name: value.detach().cpu() for name, value in model.state_dict().items()}
    torch.save({"schema_version": "archaludon-multidet-q-checkpoint-v1", "seed": int(seed), "model_config": model.config.to_dict(), "state_dict": state, "metrics": dict(metrics)}, path)


def _train_seed(config: CoverageConfig, milestone: str, rows: list[Mapping[str, Any]], validation: list[Mapping[str, Any]], seed: int, vocab: Any) -> dict[str, Any]:
    _seed_everything(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # The frozen semantic encoder creates tensors internally without an
    # explicit device.  Set PyTorch's default device for this isolated
    # training call so the unchanged model remains CUDA-compatible.
    torch.set_default_device(device)
    model = build_model(vocab).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    best_state = None
    best_regret = float("inf")
    best_huber = float("inf")
    stale = 0
    history: list[dict[str, Any]] = []
    for epoch in range(1, config.maximum_epochs + 1):
        model.train()
        order = list(range(len(rows)))
        random.Random(seed + epoch).shuffle(order)
        losses: list[torch.Tensor] = []
        for start in range(0, len(order), config.batch_groups):
            optimizer.zero_grad(set_to_none=True)
            batch = []
            for index in order[start:start + config.batch_groups]:
                row = rows[index]
                predicted = model.score_group(row)
                target = _targets(row).to(predicted.device)
                batch.append(group_loss(predicted, target, huber_beta=config.huber_beta, temperature=config.listwise_temperature, listwise_weight=config.listwise_loss_weight))
            if not batch:
                continue
            loss = torch.stack(batch).mean()
            if not bool(torch.isfinite(loss).all()):
                raise FloatingPointError("non-finite training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            losses.append(loss.detach().cpu())
        regret, huber = _validation(model, validation, config, device)
        history.append({"epoch": epoch, "train_loss": float(torch.stack(losses).mean().item()) if losses else None, "validation_mean_regret": regret, "validation_huber": huber})
        better = regret < best_regret - 1e-12 or abs(regret - best_regret) <= 1e-12 and huber < best_huber - 1e-12
        if better:
            best_regret, best_huber = regret, huber
            best_state = {name: value.detach().clone() for name, value in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= config.early_stopping_patience:
                break
    if best_state is None:
        raise RuntimeError("no validation checkpoint was produced")
    model.load_state_dict(best_state)
    checkpoint = output_path(config, "checkpoints", milestone, f"seed_{int(seed)}.pt")
    metrics = {"milestone": milestone, "seed": int(seed), "epochs_completed": len(history), "validation_mean_regret": best_regret, "validation_huber": best_huber, "training_groups": len(rows), "validation_groups": len(validation), "history": history}
    _save_cpu_checkpoint(checkpoint, model, seed=seed, metrics=metrics)
    reloaded, _ = load_checkpoint(checkpoint)
    for name, value in model.state_dict().items():
        if not torch.equal(value.detach().cpu(), reloaded.state_dict()[name].detach().cpu()):
            raise RuntimeError(f"checkpoint tensor mismatch: {name}")
    torch.set_default_device("cpu")
    return {**metrics, "checkpoint_path": str(checkpoint)}


def train(config: CoverageConfig) -> dict[str, Any]:
    api = _load_api()
    vocab = build_vocab(api)
    results: dict[str, Any] = {}
    calibration = load_dataset(config, "calibration")["rows"]
    for milestone in MILESTONES:
        training = load_dataset(config, f"training_{milestone}")["rows"]
        if not training or not calibration:
            raise ValueError(f"missing rows for {milestone} training/calibration")
        results[milestone] = [_train_seed(config, milestone, training, calibration, seed, vocab) for seed in config.training_seeds]
        write_json(output_path(config, "training", f"{milestone}_summary.json"), {"schema_version": "archaludon-search-q-training-summary-v1", "milestone": milestone, "model_vocab": vocab.to_dict(), "seed_results": results[milestone]})
    summary = {"schema_version": "archaludon-search-q-training-summary-v1", "training_seeds": list(config.training_seeds), "model_vocab": vocab.to_dict(), "milestones": results}
    write_json(output_path(config, "training", "training_summary.json"), summary)
    return summary


def pilot_optimizer_steps(config: CoverageConfig) -> dict[str, Any]:
    """Perform exactly one finite optimizer step for each frozen training seed."""
    api = _load_api()
    vocab = build_vocab(api)
    rows = load_dataset(config, "training_m05")["rows"]
    if not rows:
        raise ValueError("pilot training_m05 dataset is empty")
    result_rows: list[dict[str, Any]] = []
    for seed in config.training_seeds:
        _seed_everything(seed)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        torch.set_default_device(device)
        model = build_model(vocab).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
        predicted = model.score_group(rows[0])
        target = _targets(rows[0]).to(predicted.device)
        loss = group_loss(predicted, target, huber_beta=config.huber_beta, temperature=config.listwise_temperature, listwise_weight=config.listwise_loss_weight)
        loss.backward()
        finite_gradients = all(parameter.grad is None or bool(torch.isfinite(parameter.grad).all()) for parameter in model.parameters())
        if not finite_gradients or not bool(torch.isfinite(loss).all()):
            raise FloatingPointError("pilot loss or gradient is non-finite")
        optimizer.step()
        checkpoint = output_path(config, "pilot", "checkpoints", f"seed_{int(seed)}.pt")
        _save_cpu_checkpoint(checkpoint, model, seed=seed, metrics={"pilot_optimizer_steps": 1, "loss": float(loss.item())})
        reloaded, _ = load_checkpoint(checkpoint)
        if tuple(reloaded.state_dict()) != tuple(model.state_dict()):
            raise RuntimeError("checkpoint tensor mismatch")
        result_rows.append({"seed": int(seed), "optimizer_steps": 1, "loss_finite": True, "gradient_finite": True, "checkpoint": str(checkpoint)})
    torch.set_default_device("cpu")
    result = {"schema_version": "archaludon-search-q-pilot-model-v1", "results": result_rows, "success": len(result_rows) == 3}
    write_json(output_path(config, "pilot", "model_summary.json"), result)
    return result


__all__ = ["MILESTONES", "pilot_optimizer_steps", "train"]
