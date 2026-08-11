"""Compatibility bridge to the unchanged Multi-Determinization model."""

from __future__ import annotations

from typing import Any

from research.experiments.archaludon_multideterminization_q_v1.multidet_q.model import (
    ExpectedQModel,
    ModelConfig,
    build_model,
    group_loss,
    load_checkpoint,
    mean_regret,
    save_checkpoint,
)
from research.experiments.archaludon_multideterminization_q_v1.multidet_q.semantic_encoder import SemanticEncoder, SemanticVocab, build_vocab


def parameter_signature(model: Any) -> tuple[tuple[str, tuple[int, ...]], ...]:
    return tuple((str(name), tuple(int(dim) for dim in value.shape)) for name, value in model.named_parameters())


def parameter_count(model: Any) -> int:
    return sum(int(value.numel()) for value in model.parameters())


def assert_model_structure_equal(left: Any, right: Any) -> None:
    if parameter_signature(left) != parameter_signature(right):
        raise AssertionError("expected-Q parameter names/shapes differ")
    if parameter_count(left) != parameter_count(right):
        raise AssertionError("expected-Q parameter count differs")


__all__ = ["ExpectedQModel", "ModelConfig", "SemanticEncoder", "SemanticVocab", "assert_model_structure_equal", "build_model", "build_vocab", "group_loss", "load_checkpoint", "mean_regret", "parameter_count", "parameter_signature", "save_checkpoint"]
