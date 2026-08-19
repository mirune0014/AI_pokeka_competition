'''Fixed configuration and path helpers for Rollout-Q v1.'''

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[4]
EXPERIMENT_ROOT = REPO_ROOT / 'research' / 'experiments' / 'archaludon_rollout_q_v1'
DEFAULT_SPEC_PATH = EXPERIMENT_ROOT / 'specs' / 'rollout_q_v1.json'
BASELINE_POLICY_ID = 'archaludon_historical_silver_single_resolver_salvage_v1'
BASELINE_POLICY_PATH = REPO_ROOT / 'archaludon' / 'final' / BASELINE_POLICY_ID
HISTORICAL_SILVER_PATH = REPO_ROOT / 'archaludon' / 'baseline' / 'historical_silver_archaludon_54495224'
OUTPUT_ROOT = REPO_ROOT / '_local_generated' / 'archaludon_rollout_q_v1'
MAIN_CONTEXT = 0
REQUIRED_SCHEMA_VERSION = 'archaludon-rollout-q-v1'


@dataclass(frozen=True)
class RolloutQConfig:
    schema_version: str
    baseline_policy_path: str
    historical_silver_path: str
    output_root: str
    rounds: int
    source_games_per_round: int
    maximum_branch_points_per_source_game: int
    branch_contexts: tuple[int, ...]
    minimum_candidate_count: int
    maximum_candidate_count: int
    branch_all_candidates: bool
    training_seeds: tuple[int, ...]
    validation_episode_fraction: float
    batch_size: int
    maximum_epochs: int
    early_stopping_patience: int
    learning_rate: float
    weight_decay: float
    override_mean_probability_threshold: float
    override_minimum_model_probability: float
    override_minimum_support: int
    evaluation_games: int
    evaluation_seed_base: int
    worker_max_steps: int

    @property
    def baseline_dir(self) -> Path:
        return REPO_ROOT / self.baseline_policy_path

    @property
    def historical_silver_dir(self) -> Path:
        return REPO_ROOT / self.historical_silver_path

    @property
    def output_dir(self) -> Path:
        return REPO_ROOT / self.output_root


def _tuple_ints(value: Any, name: str) -> tuple[int, ...]:
    if not isinstance(value, list) or any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        raise ValueError(f'{name} must be a list of integers')
    return tuple(int(item) for item in value)


def load_spec(path: Path | None = None) -> RolloutQConfig:
    spec_path = (path or DEFAULT_SPEC_PATH).resolve()
    raw = json.loads(spec_path.read_text(encoding='utf-8'))
    if not isinstance(raw, Mapping):
        raise ValueError('Rollout-Q spec must be a JSON object')
    if raw.get('schema_version') != REQUIRED_SCHEMA_VERSION:
        raise ValueError('unexpected Rollout-Q schema_version')
    config = RolloutQConfig(
        schema_version=str(raw['schema_version']),
        baseline_policy_path=str(raw['baseline_policy_path']),
        historical_silver_path=str(raw['historical_silver_path']),
        output_root=str(raw['output_root']),
        rounds=int(raw['rounds']),
        source_games_per_round=int(raw['source_games_per_round']),
        maximum_branch_points_per_source_game=int(raw['maximum_branch_points_per_source_game']),
        branch_contexts=_tuple_ints(raw['branch_contexts'], 'branch_contexts'),
        minimum_candidate_count=int(raw['minimum_candidate_count']),
        maximum_candidate_count=int(raw['maximum_candidate_count']),
        branch_all_candidates=bool(raw['branch_all_candidates']),
        training_seeds=_tuple_ints(raw['training_seeds'], 'training_seeds'),
        validation_episode_fraction=float(raw['validation_episode_fraction']),
        batch_size=int(raw['batch_size']),
        maximum_epochs=int(raw['maximum_epochs']),
        early_stopping_patience=int(raw['early_stopping_patience']),
        learning_rate=float(raw['learning_rate']),
        weight_decay=float(raw['weight_decay']),
        override_mean_probability_threshold=float(raw['override_mean_probability_threshold']),
        override_minimum_model_probability=float(raw['override_minimum_model_probability']),
        override_minimum_support=int(raw['override_minimum_support']),
        evaluation_games=int(raw['evaluation_games']),
        evaluation_seed_base=int(raw['evaluation_seed_base']),
        worker_max_steps=int(raw['worker_max_steps']),
    )
    if config.branch_contexts != (MAIN_CONTEXT,):
        raise ValueError('v1 branch_contexts must contain SelectContext.MAIN only')
    if config.minimum_candidate_count < 2 or config.maximum_candidate_count > 25:
        raise ValueError('v1 candidate bounds must be within 2..25')
    if len(config.training_seeds) != 3:
        raise ValueError('v1 requires exactly three training seeds')
    if not 0.0 < config.validation_episode_fraction < 1.0:
        raise ValueError('validation_episode_fraction must be between zero and one')
    return config


def round_dir(config: RolloutQConfig, round_index: int) -> Path:
    if not 0 <= int(round_index) < config.rounds:
        raise ValueError('round index is outside the fixed specification')
    return config.output_dir / f'round_{int(round_index):02d}'


def ensure_empty_or_missing(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f'output already exists and is not empty: {path}')
    path.mkdir(parents=True, exist_ok=True)


def ensure_input_layout(config: RolloutQConfig) -> None:
    for directory in (config.baseline_dir, config.historical_silver_dir):
        if not (directory / 'main.py').is_file() or not (directory / 'deck.csv').is_file():
            raise FileNotFoundError(f'baseline input is incomplete: {directory}')


def terminal_reward(result: Any, policy_seat: int) -> float:
    if result == 2:
        return 0.0
    if result == policy_seat:
        return 1.0
    if result in (0, 1):
        return -1.0
    raise ValueError(f'unknown terminal result: {result!r}')


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n', encoding='utf-8')
