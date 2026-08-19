'''Conservative ensemble override around the formal Archaludon policy.'''

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import torch

from .complete_action import (
    observation_complete_actions,
    observation_option_rows,
)
from research.experiments.archaludon_latest_v1_rl_pcgrad_candidate_20260801.archaludon_rl.public_state import (
    enum_int,
    get_field,
)
from research.rl_ptcg.encoding import encode_observation

from .agent_loader import LoadedPolicy
from .config import RolloutQConfig, round_dir
from .dataset import complete_action_feature, load_dataset
from .model import load_checkpoint


def _candidate_family(candidate: Any) -> str:
    types: list[str] = []
    for option in candidate.selected_options:
        payload = option.get('semantic_payload') or option.get('payload') or {}
        value = payload.get('option_type', payload.get('type', 'empty')) if isinstance(payload, Mapping) else 'empty'
        types.append(str(value))
    return 'empty' if not types else '+'.join(sorted(types))


def support_from_rows(rows: Sequence[Mapping[str, Any]]) -> dict[tuple[int, str], int]:
    support: dict[tuple[int, str], int] = {}
    for row in rows:
        if row.get('split') != 'training':
            continue
        key = (int(row.get('context', 0)), str(row.get('family', 'empty')))
        support[key] = support.get(key, 0) + 1
    return support


@dataclass
class OverrideTelemetry:
    override_count: int = 0
    fallback_count: int = 0
    model_failure_count: int = 0
    action_error_count: int = 0
    reasons: dict[str, int] = field(default_factory=dict)

    def fallback(self, reason: str) -> None:
        self.fallback_count += 1
        self.reasons[reason] = self.reasons.get(reason, 0) + 1


@dataclass(frozen=True)
class RoundPolicyResources:
    checkpoint_round: int
    models: tuple[torch.nn.Module, torch.nn.Module, torch.nn.Module]
    support: dict[tuple[int, str], int]

    @classmethod
    def load(cls, config: RolloutQConfig, checkpoint_round: int) -> 'RoundPolicyResources':
        checkpoint_round = int(checkpoint_round)
        checkpoint_dir = round_dir(config, checkpoint_round) / 'checkpoints'
        dataset = load_dataset(config, checkpoint_round)
        support = support_from_rows(dataset.get('rows', []))
        models: list[torch.nn.Module] = []
        for seed in config.training_seeds:
            path = checkpoint_dir / f'rollout_q_seed{int(seed)}.pt'
            if not path.is_file():
                raise FileNotFoundError(path)
            model, _, _ = load_checkpoint(path)
            model.eval()
            models.append(model)
        if len(models) != 3:
            raise ValueError('exactly three Rollout-Q models are required')
        return cls(checkpoint_round=checkpoint_round, models=tuple(models), support=dict(support))

    def bind(self, baseline: LoadedPolicy, config: RolloutQConfig) -> 'RolloutQOverridePolicy':
        return RolloutQOverridePolicy(
            baseline=baseline,
            models=self.models,
            config=config,
            support=self.support,
        )


class RolloutQOverridePolicy:
    def __init__(
        self,
        *,
        baseline: LoadedPolicy,
        models: Sequence[torch.nn.Module],
        config: RolloutQConfig,
        support: Mapping[tuple[int, str], int],
    ) -> None:
        if len(models) != 3:
            raise ValueError('Rollout-Q deployment requires three models')
        self.baseline = baseline
        self.models = tuple(models)
        self.config = config
        self.support = dict(support)
        self.telemetry = OverrideTelemetry()
        self.last_baseline_action: list[int] | None = None
        for model in self.models:
            model.eval()

    @classmethod
    def from_checkpoints(
        cls,
        *,
        baseline: LoadedPolicy,
        checkpoint_paths: Sequence[Path],
        config: RolloutQConfig,
        support: Mapping[tuple[int, str], int],
    ) -> 'RolloutQOverridePolicy':
        if len(checkpoint_paths) != 3:
            raise ValueError('exactly three checkpoint paths are required')
        models = [load_checkpoint(path)[0] for path in checkpoint_paths]
        return cls(baseline=baseline, models=models, config=config, support=support)

    def _eligible(self, observation: Any, baseline_action: Sequence[int], owner_before: Any, owner_after: Any) -> Any:
        if owner_before is not None or owner_after is not None:
            return None
        select = get_field(observation, 'select')
        if select is None or int(enum_int(get_field(select, 'context'))) not in self.config.branch_contexts:
            return None
        candidates = observation_complete_actions(observation)
        if not self.config.minimum_candidate_count <= len(candidates.candidates) <= self.config.maximum_candidate_count:
            return None
        option_rows = observation_option_rows(observation)
        baseline_index = candidates.candidate_index_for(option_rows, baseline_action)
        if baseline_index is None:
            return None
        return candidates, option_rows, int(baseline_index)

    def choose_action(self, observation: Any) -> list[int]:
        owner_before = self.baseline.owner
        try:
            baseline_action = self.baseline(observation)
            self.last_baseline_action = list(baseline_action)
        except Exception:
            self.telemetry.model_failure_count += 1
            self.telemetry.fallback('baseline_failure')
            raise
        owner_after = self.baseline.owner
        try:
            eligible = self._eligible(observation, baseline_action, owner_before, owner_after)
            if eligible is None:
                self.telemetry.fallback('ineligible')
                return list(baseline_action)
            candidates, _, baseline_index = eligible
            encoded = encode_observation(observation)
            state = torch.tensor(encoded.state_vector, dtype=torch.float32)
            option_vectors = encoded.option_vectors
            baseline_candidate = candidates.candidates[baseline_index]
            alternative_candidates = [
                candidate for index, candidate in enumerate(candidates.candidates)
                if index != baseline_index
            ]
            if not alternative_candidates:
                self.telemetry.fallback('no_alternative')
                return list(baseline_action)
            baseline_feature = torch.tensor(
                complete_action_feature(option_vectors, baseline_candidate.action),
                dtype=torch.float32,
            )
            candidate_features = [
                torch.tensor(complete_action_feature(option_vectors, candidate.action), dtype=torch.float32)
                for candidate in alternative_candidates
            ]
            predictions: list[dict[str, float]] = []
            winners: list[str] = []
            for model in self.models:
                with torch.no_grad():
                    states = state.unsqueeze(0).expand(len(alternative_candidates), -1)
                    candidate_tensor = torch.stack(candidate_features)
                    baseline_tensor = baseline_feature.unsqueeze(0).expand(len(alternative_candidates), -1)
                    logits = model(states, candidate_tensor, baseline_tensor)
                    probabilities = torch.sigmoid(logits).detach().cpu().reshape(-1).tolist()
                if len(probabilities) != len(alternative_candidates):
                    raise ValueError('Rollout-Q model returned an invalid candidate score shape')
                if any(not math.isfinite(float(value)) for value in probabilities):
                    raise FloatingPointError('non-finite Rollout-Q probability')
                by_identity = {
                    candidate.canonical_identity: float(probabilities[index])
                    for index, candidate in enumerate(alternative_candidates)
                }
                best = max(alternative_candidates, key=lambda candidate: (by_identity[candidate.canonical_identity], candidate.canonical_identity))
                winners.append(best.canonical_identity)
                predictions.append(by_identity)
            if len(set(winners)) != 1:
                self.telemetry.fallback('ensemble_disagreement')
                return list(baseline_action)
            selected_identity = winners[0]
            selected = next(candidate for candidate in alternative_candidates if candidate.canonical_identity == selected_identity)
            probabilities = [result[selected_identity] for result in predictions]
            context = int(enum_int(get_field(get_field(observation, 'select'), 'context')))
            family = _candidate_family(selected)
            if sum(probabilities) / len(probabilities) < self.config.override_mean_probability_threshold:
                self.telemetry.fallback('mean_probability')
                return list(baseline_action)
            if min(probabilities) < self.config.override_minimum_model_probability:
                self.telemetry.fallback('minimum_probability')
                return list(baseline_action)
            if self.support.get((context, family), 0) < self.config.override_minimum_support:
                self.telemetry.fallback('support')
                return list(baseline_action)
            if candidates.candidate_index_for(observation_option_rows(observation), selected.action) is None:
                self.telemetry.fallback('nonlegal_candidate')
                return list(baseline_action)
            self.telemetry.override_count += 1
            return list(selected.action)
        except Exception as exc:
            self.telemetry.model_failure_count += 1
            self.telemetry.fallback(type(exc).__name__)
            return list(baseline_action)

    def __call__(self, observation: Any) -> list[int]:
        return self.choose_action(observation)


__all__ = ['OverrideTelemetry', 'RolloutQOverridePolicy', 'RoundPolicyResources', 'support_from_rows']
