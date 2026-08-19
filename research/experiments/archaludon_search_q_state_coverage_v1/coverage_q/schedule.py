"""Deterministic 16-cell source schedule for the coverage experiment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from research.experiments.archaludon_rollout_q_v1.rollout_q.source_collector import _opponent_rows

from .config import CoverageConfig


OPPONENTS = tuple(str(row["id"]) for row in _opponent_rows())
SPLITS = ("training", "calibration", "offline_test")


@dataclass(frozen=True)
class SourceEpisodePlan:
    split: str
    opponent_id: str
    opponent_index: int
    seat: int
    cell_index: int
    local_index: int
    seed: int
    episode_id: str
    training_milestones: tuple[str, ...]


def cell_counts(total: int, *, remainder_first: bool = True) -> tuple[int, ...]:
    base, remainder = divmod(int(total), 16)
    return tuple(base + (1 if (index < remainder if remainder_first else index >= 16 - remainder) else 0) for index in range(16))


def _milestones(local_index: int, cell_index: int) -> tuple[str, ...]:
    if cell_index < 4:
        m05_count = 282
    else:
        m05_count = 281
    m10_count = 563 if cell_index < 8 else 562
    values: list[str] = []
    if local_index < m05_count:
        values.append("m05")
    if local_index < m10_count:
        values.append("m10")
    values.append("m20")
    return tuple(values)


def plans_for_split(config: CoverageConfig, split: str, *, pilot: bool = False) -> list[SourceEpisodePlan]:
    if split not in SPLITS:
        raise ValueError(f"unsupported split: {split}")
    total = int(config.source_games[split])
    if pilot:
        total = {"training": 64, "calibration": 16, "offline_test": 16}[split]
    counts = cell_counts(total, remainder_first=split != "offline_test")
    plans: list[SourceEpisodePlan] = []
    for cell_index, count in enumerate(counts):
        opponent_index, seat = divmod(cell_index, 2)
        opponent_id = OPPONENTS[opponent_index]
        for local_index in range(count):
            seed = int(config.source_seed_bases[split]) + cell_index * 100000 + local_index
            episode_id = f"coverage_v1_{split}_{opponent_id}_seat{seat}_seed{seed}"
            milestones = _milestones(local_index, cell_index) if split == "training" else ()
            plans.append(SourceEpisodePlan(split, opponent_id, opponent_index, seat, cell_index, local_index, seed, episode_id, milestones))
    return plans


def all_plans(config: CoverageConfig, *, pilot: bool = False) -> list[SourceEpisodePlan]:
    return [plan for split in SPLITS for plan in plans_for_split(config, split, pilot=pilot)]


def expected_counts(config: CoverageConfig) -> dict[str, int]:
    return {split: sum(1 for _ in plans_for_split(config, split)) for split in SPLITS}


def plans_by_episode(plans: Iterable[SourceEpisodePlan]) -> dict[str, SourceEpisodePlan]:
    result: dict[str, SourceEpisodePlan] = {}
    for plan in plans:
        if plan.episode_id in result:
            raise ValueError(f"duplicate episode id: {plan.episode_id}")
        result[plan.episode_id] = plan
    return result


__all__ = ["OPPONENTS", "SPLITS", "SourceEpisodePlan", "all_plans", "cell_counts", "expected_counts", "plans_by_episode", "plans_for_split"]
