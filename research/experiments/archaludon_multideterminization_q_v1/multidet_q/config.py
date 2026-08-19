"""Fixed paths and configuration for Multi-Determinization Search-Q v1."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[4]
EXPERIMENT_ROOT = REPO_ROOT / "research" / "experiments" / "archaludon_multideterminization_q_v1"
SPEC_PATH = EXPERIMENT_ROOT / "specs" / "multideterminization_q_v1.json"
ENGINE_ROOT = (
    REPO_ROOT
    / "_local_generated"
    / "analysis_outputs"
    / "cynthia_v9_vs_v11_poffin_role_selection_20260713"
    / "seeded_engine"
)


@dataclass(frozen=True)
class MultiDetConfig:
    schema_version: str
    input_round_root: str
    output_root: str
    baseline_policy_path: str
    historical_silver_path: str
    pilot_determinizations: int
    full_determinizations: int
    pilot_groups_per_opponent_seat: int
    manual_coin: bool
    maximum_search_steps: int
    lcb_z_value: float
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
    evaluation_games: int

    @property
    def input_dir(self) -> Path:
        return REPO_ROOT / self.input_round_root

    @property
    def output_dir(self) -> Path:
        return REPO_ROOT / self.output_root

    @property
    def baseline_dir(self) -> Path:
        return REPO_ROOT / self.baseline_policy_path

    @property
    def historical_silver_dir(self) -> Path:
        return REPO_ROOT / self.historical_silver_path


def _ints(value: Any, name: str) -> tuple[int, ...]:
    if not isinstance(value, list) or any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise ValueError(f"{name} must be a list of integers")
    return tuple(int(item) for item in value)


def _floats(value: Any, name: str) -> tuple[float, ...]:
    if not isinstance(value, list) or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        raise ValueError(f"{name} must be a list of numbers")
    return tuple(float(item) for item in value)


def load_config(path: Path | None = None) -> MultiDetConfig:
    spec_path = (path or SPEC_PATH).resolve()
    raw = json.loads(spec_path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValueError("Multi-Determinization spec must be an object")
    if raw.get("schema_version") != "archaludon-multideterminization-q-v1":
        raise ValueError("unexpected multideterminization schema_version")
    config = MultiDetConfig(
        schema_version=str(raw["schema_version"]),
        input_round_root=str(raw["input_round_root"]),
        output_root=str(raw["output_root"]),
        baseline_policy_path=str(raw["baseline_policy_path"]),
        historical_silver_path=str(raw["historical_silver_path"]),
        pilot_determinizations=int(raw["pilot_determinizations"]),
        full_determinizations=int(raw["full_determinizations"]),
        pilot_groups_per_opponent_seat=int(raw["pilot_groups_per_opponent_seat"]),
        manual_coin=bool(raw["manual_coin"]),
        maximum_search_steps=int(raw["maximum_search_steps"]),
        lcb_z_value=float(raw["lcb_z_value"]),
        training_seeds=_ints(raw["training_seeds"], "training_seeds"),
        batch_groups=int(raw["batch_groups"]),
        maximum_epochs=int(raw["maximum_epochs"]),
        early_stopping_patience=int(raw["early_stopping_patience"]),
        learning_rate=float(raw["learning_rate"]),
        weight_decay=float(raw["weight_decay"]),
        huber_beta=float(raw["huber_beta"]),
        listwise_temperature=float(raw["listwise_temperature"]),
        listwise_loss_weight=float(raw["listwise_loss_weight"]),
        margin_thresholds=_floats(raw["margin_thresholds"], "margin_thresholds"),
        evaluation_games=int(raw["evaluation_games"]),
    )
    if config.training_seeds != (2026080501, 2026080502, 2026080503):
        raise ValueError("training seeds are frozen")
    if len(config.margin_thresholds) != 7:
        raise ValueError("margin threshold count is frozen")
    if config.pilot_determinizations != 8 or config.full_determinizations != 16:
        raise ValueError("determinization counts are frozen")
    return config


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_output(config: MultiDetConfig) -> None:
    """Create the new output root without overwriting an existing artifact."""

    if config.output_dir.exists() and any(config.output_dir.iterdir()):
        raise FileExistsError(f"output already exists and is not empty: {config.output_dir}")
    config.output_dir.mkdir(parents=True, exist_ok=True)


def input_path(config: MultiDetConfig, *parts: str) -> Path:
    return config.input_dir.joinpath(*parts)


def output_path(config: MultiDetConfig, *parts: str) -> Path:
    return config.output_dir.joinpath(*parts)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


__all__ = [
    "ENGINE_ROOT",
    "EXPERIMENT_ROOT",
    "MultiDetConfig",
    "REPO_ROOT",
    "SPEC_PATH",
    "canonical_json",
    "ensure_output",
    "input_path",
    "load_config",
    "output_path",
    "read_json",
    "write_json",
]
