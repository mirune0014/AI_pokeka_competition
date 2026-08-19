"""Frozen configuration and safe output helpers for Coverage-Q v1."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[4]
EXPERIMENT_ROOT = REPO_ROOT / "research" / "experiments" / "archaludon_search_q_state_coverage_v1"
SPEC_PATH = EXPERIMENT_ROOT / "specs" / "state_coverage_v1.json"
PILOT_OUTPUT_ROOT = "_local_generated/archaludon_search_q_state_coverage_v1_pilot"


@dataclass(frozen=True)
class CoverageConfig:
    schema_version: str
    baseline_policy_path: str
    historical_silver_path: str
    output_root: str
    source_games: dict[str, int]
    source_seed_bases: dict[str, int]
    maximum_branch_points_per_source_game: int
    determinizations: dict[str, int]
    milestone_training_games: dict[str, int]
    worker_count: int
    maximum_search_steps: int
    training_seeds: tuple[int, ...]
    batch_groups: int
    maximum_epochs: int
    early_stopping_patience: int
    learning_rate: float
    weight_decay: float
    huber_beta: float
    listwise_temperature: float
    listwise_loss_weight: float
    margin_thresholds: tuple[float, ...]
    maximum_overrides_per_game: int
    offline_test_minimum_override_episodes: int
    final_evaluation_games: int
    final_evaluation_required_paired_net: int
    final_evaluation_required_p_value: float
    maximum_projected_search_hours: int

    @property
    def baseline_dir(self) -> Path:
        return REPO_ROOT / self.baseline_policy_path

    @property
    def historical_silver_dir(self) -> Path:
        return REPO_ROOT / self.historical_silver_path

    @property
    def output_dir(self) -> Path:
        return REPO_ROOT / self.output_root

    @property
    def lcb_z_value(self) -> float:
        # Normal approximation z for a two-sided 90% interval, matching the
        # existing Multi-Determinization Search-Q implementation.
        return 1.281551565545

    @property
    def manual_coin(self) -> bool:
        return True

    @property
    def worker_max_steps(self) -> int:
        return self.maximum_search_steps

    def with_output_root(self, output_root: str) -> "CoverageConfig":
        values = dict(self.__dict__)
        values["output_root"] = output_root
        return CoverageConfig(**values)


def _mapping(raw: Any, name: str) -> dict[str, int]:
    if not isinstance(raw, Mapping):
        raise ValueError(f"{name} must be an object")
    result = {str(key): int(value) for key, value in raw.items()}
    return result


def load_config(path: Path | None = None) -> CoverageConfig:
    raw = json.loads((path or SPEC_PATH).read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping) or raw.get("schema_version") != "archaludon-search-q-state-coverage-v1":
        raise ValueError("unexpected state coverage schema_version")
    config = CoverageConfig(
        schema_version=str(raw["schema_version"]),
        baseline_policy_path=str(raw["baseline_policy_path"]),
        historical_silver_path=str(raw["historical_silver_path"]),
        output_root=str(raw["output_root"]),
        source_games=_mapping(raw["source_games"], "source_games"),
        source_seed_bases=_mapping(raw["source_seed_bases"], "source_seed_bases"),
        maximum_branch_points_per_source_game=int(raw["maximum_branch_points_per_source_game"]),
        determinizations=_mapping(raw["determinizations"], "determinizations"),
        milestone_training_games=_mapping(raw["milestone_training_games"], "milestone_training_games"),
        worker_count=int(raw["worker_count"]),
        maximum_search_steps=int(raw["maximum_search_steps"]),
        training_seeds=tuple(int(value) for value in raw["training_seeds"]),
        batch_groups=int(raw["batch_groups"]),
        maximum_epochs=int(raw["maximum_epochs"]),
        early_stopping_patience=int(raw["early_stopping_patience"]),
        learning_rate=float(raw["learning_rate"]),
        weight_decay=float(raw["weight_decay"]),
        huber_beta=float(raw["huber_beta"]),
        listwise_temperature=float(raw["listwise_temperature"]),
        listwise_loss_weight=float(raw["listwise_loss_weight"]),
        margin_thresholds=tuple(float(value) for value in raw["margin_thresholds"]),
        maximum_overrides_per_game=int(raw["maximum_overrides_per_game"]),
        offline_test_minimum_override_episodes=int(raw["offline_test_minimum_override_episodes"]),
        final_evaluation_games=int(raw["final_evaluation_games"]),
        final_evaluation_required_paired_net=int(raw["final_evaluation_required_paired_net"]),
        final_evaluation_required_p_value=float(raw["final_evaluation_required_p_value"]),
        maximum_projected_search_hours=int(raw["maximum_projected_search_hours"]),
    )
    if config.worker_count != 6 or config.maximum_overrides_per_game != 1:
        raise ValueError("worker count and override count are frozen")
    if config.training_seeds != (2026080501, 2026080502, 2026080503):
        raise ValueError("training seeds are frozen")
    if tuple(config.margin_thresholds) != (0.0, 0.02, 0.05, 0.10, 0.20, 0.30, 0.40):
        raise ValueError("margin thresholds are frozen")
    return config


def output_path(config: CoverageConfig, *parts: str) -> Path:
    return config.output_dir.joinpath(*parts)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def ensure_output(config: CoverageConfig) -> None:
    if config.output_dir.exists() and any(config.output_dir.iterdir()):
        raise FileExistsError(f"output already exists and is not empty: {config.output_dir}")
    config.output_dir.mkdir(parents=True, exist_ok=True)


__all__ = ["CoverageConfig", "EXPERIMENT_ROOT", "PILOT_OUTPUT_ROOT", "REPO_ROOT", "SPEC_PATH", "canonical_json", "ensure_output", "load_config", "output_path", "read_json", "write_json"]
