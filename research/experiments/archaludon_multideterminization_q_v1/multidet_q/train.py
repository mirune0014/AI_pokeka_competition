"""Train three fixed-seed expected-Q models with regret early stopping."""

from __future__ import annotations

import copy
import random
from typing import Any, Mapping, Sequence

import torch

from .config import MultiDetConfig, output_path, write_json
from .dataset import load_dataset
from .model import ExpectedQModel, ModelConfig, build_model, group_loss, load_checkpoint, save_checkpoint
from .search_runtime import _load_api
from .semantic_encoder import build_vocab


def _seed_everything(seed: int) -> None:
    random.seed(int(seed))
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))


def _targets(row: Mapping[str, Any]) -> torch.Tensor:
    return torch.tensor([float(candidate["target_q"]) for candidate in row["candidates"]], dtype=torch.float32)


def _validation(model: ExpectedQModel, rows: Sequence[Mapping[str, Any]], config: MultiDetConfig) -> tuple[float, float, list[torch.Tensor], list[torch.Tensor], float, float]:
    model.eval()
    predictions: list[torch.Tensor] = []
    targets: list[torch.Tensor] = []
    total_huber = 0.0
    selected_rewards: list[float] = []
    oracle_rewards: list[float] = []
    with torch.no_grad():
        for row in rows:
            predicted = model.score_group(row)
            target = _targets(row)
            if not bool(torch.isfinite(predicted).all()):
                raise FloatingPointError("non-finite validation prediction")
            predictions.append(predicted)
            targets.append(target)
            total_huber += float(torch.nn.functional.smooth_l1_loss(predicted, target, beta=config.huber_beta).item())
            selected = int(torch.argmax(predicted).item())
            selected_rewards.append(float(target[selected].item()))
            oracle_rewards.append(float(torch.max(target).item()))
    regrets = [float(torch.max(target).item() - target[int(torch.argmax(predicted).item())].item()) for predicted, target in zip(predictions, targets)]
    mean_regret = sum(regrets) / len(regrets) if regrets else float("nan")
    mean_huber = total_huber / len(rows) if rows else float("nan")
    selected_mean = sum(selected_rewards) / len(selected_rewards) if selected_rewards else float("nan")
    oracle_mean = sum(oracle_rewards) / len(oracle_rewards) if oracle_rewards else float("nan")
    return mean_regret, mean_huber, predictions, targets, selected_mean, oracle_mean


def _train_seed(config: MultiDetConfig, rows: list[Mapping[str, Any]], seed: int, vocab: Any) -> dict[str, Any]:
    training = [row for row in rows if row.get("split") == "training"]
    validation = [row for row in rows if row.get("split") == "validation"]
    if not training or not validation:
        raise ValueError("dataset must contain training and validation groups")
    _seed_everything(seed)
    model = build_model(vocab)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    best_regret = float("inf")
    best_huber = float("inf")
    best_state: dict[str, torch.Tensor] | None = None
    stale = 0
    history: list[dict[str, Any]] = []
    for epoch in range(1, config.maximum_epochs + 1):
        model.train()
        order = list(range(len(training)))
        random.Random(int(seed) + epoch).shuffle(order)
        total_loss = 0.0
        batch_count = 0
        for start in range(0, len(order), config.batch_groups):
            batch_indices = order[start:start + config.batch_groups]
            optimizer.zero_grad(set_to_none=True)
            losses = []
            for index in batch_indices:
                row = training[index]
                predicted = model.score_group(row)
                target = _targets(row)
                losses.append(
                    group_loss(
                        predicted,
                        target,
                        huber_beta=config.huber_beta,
                        temperature=config.listwise_temperature,
                        listwise_weight=config.listwise_loss_weight,
                    )
                )
            loss = torch.stack(losses).mean()
            if not bool(torch.isfinite(loss).all()):
                raise FloatingPointError("non-finite training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += float(loss.item())
            batch_count += 1
        val_regret, val_huber, _, _, selected_mean, oracle_mean = _validation(model, validation, config)
        history.append(
            {
                "epoch": epoch,
                "train_loss": total_loss / max(1, batch_count),
                "validation_mean_regret": val_regret,
                "validation_huber": val_huber,
                "selected_actual_mean_reward": selected_mean,
                "oracle_actual_mean_reward": oracle_mean,
            }
        )
        better = val_regret < best_regret - 1e-12 or (abs(val_regret - best_regret) <= 1e-12 and val_huber < best_huber - 1e-12)
        if better:
            best_regret = val_regret
            best_huber = val_huber
            best_state = {name: value.detach().clone() for name, value in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= config.early_stopping_patience:
                break
    if best_state is None:
        raise RuntimeError("no validation checkpoint was produced")
    model.load_state_dict(best_state)
    val_regret, val_huber, predictions, targets, selected_mean, oracle_mean = _validation(model, validation, config)
    checkpoint = output_path(config, "checkpoints", f"multidet_q_seed{int(seed)}.pt")
    metrics = {
        "seed": int(seed),
        "epochs_completed": len(history),
        "validation_mean_regret": val_regret,
        "validation_huber": val_huber,
        "selected_actual_mean_reward": selected_mean,
        "oracle_actual_mean_reward": oracle_mean,
        "training_groups": len(training),
        "validation_groups": len(validation),
        "history": history,
    }
    save_checkpoint(checkpoint, model, seed=seed, metrics=metrics)
    reloaded, _ = load_checkpoint(checkpoint)
    for name, value in model.state_dict().items():
        if not torch.equal(value, reloaded.state_dict()[name]):
            raise RuntimeError(f"checkpoint tensor mismatch: {name}")
    metrics["checkpoint_path"] = str(checkpoint)
    return metrics


def train(config: MultiDetConfig) -> dict[str, Any]:
    dataset = load_dataset(config)
    rows = dataset.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("expected-Q dataset has no rows")
    api = _load_api()
    vocab = build_vocab(api)
    results = [_train_seed(config, rows, seed, vocab) for seed in config.training_seeds]
    summary = {
        "schema_version": "archaludon-multidet-training-summary-v1",
        "training_seeds": list(config.training_seeds),
        "model_vocab": vocab.to_dict(),
        "seed_results": results,
    }
    write_json(output_path(config, "training_summary.json"), summary)
    return summary


__all__ = ["train"]
