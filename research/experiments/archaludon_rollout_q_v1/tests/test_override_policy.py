from __future__ import annotations

from dataclasses import replace
import torch

from research.experiments.archaludon_rollout_q_v1.rollout_q import override_policy
from research.experiments.archaludon_rollout_q_v1.rollout_q.config import load_spec


class _Candidate:
    def __init__(self, index: int, action: tuple[int, ...], identity: str):
        self.candidate_index = index
        self.action = action
        self.canonical_identity = identity
        self.selected_options = ({'semantic_payload': {'option_type': 3}},)


class _Candidates:
    def __init__(self):
        self.candidates = (_Candidate(0, (0,), 'baseline'), _Candidate(1, (1,), 'alternative'))

    def candidate_index_for(self, options, action):
        return 0 if tuple(action) == (0,) else 1 if tuple(action) == (1,) else None


class _Baseline:
    owner = None

    def __call__(self, observation):
        return [0]


class _Model(torch.nn.Module):
    def __init__(self, value: float):
        super().__init__()
        self.value = value

    def forward(self, state, candidate, baseline):
        return torch.full((candidate.shape[0],), self.value, dtype=candidate.dtype)


def _patch_surface(monkeypatch):
    monkeypatch.setattr(override_policy, 'observation_complete_actions', lambda observation: _Candidates())
    monkeypatch.setattr(override_policy, 'observation_option_rows', lambda observation: ({}, {}))
    monkeypatch.setattr(override_policy, 'encode_observation', lambda observation: type('Encoded', (), {'state_vector': [0.0] * 4, 'option_vectors': [[0.0] * 17, [1.0] * 17]})())


def test_threshold_not_met_falls_back(monkeypatch):
    _patch_surface(monkeypatch)
    policy = override_policy.RolloutQOverridePolicy(
        baseline=_Baseline(),
        models=[_Model(1.0), _Model(1.0), _Model(1.0)],
        config=load_spec(),
        support={(0, '3'): 100},
    )
    assert policy.choose_action({'select': {'context': 0}}) == [0]


def test_unanimous_supported_winner_overrides(monkeypatch):
    _patch_surface(monkeypatch)
    policy = override_policy.RolloutQOverridePolicy(
        baseline=_Baseline(),
        models=[_Model(4.0), _Model(4.0), _Model(4.0)],
        config=load_spec(),
        support={(0, '3'): 100},
    )
    assert policy.choose_action({'select': {'context': 0}}) == [1]


def test_ensemble_disagreement_falls_back(monkeypatch):
    _patch_surface(monkeypatch)
    policy = override_policy.RolloutQOverridePolicy(
        baseline=_Baseline(),
        models=[_Model(4.0), _Model(-4.0), _Model(4.0)],
        config=load_spec(),
        support={(0, '3'): 100},
    )
    assert policy.choose_action({'select': {'context': 0}}) == [0]


def test_support_counts_training_rows_only():
    rows = [
        {'split': 'validation', 'context': 0, 'family': '3'},
        {'split': 'training', 'context': 0, 'family': '3'},
        {'split': 'training', 'context': 0, 'family': '3'},
    ]
    assert override_policy.support_from_rows(rows) == {(0, '3'): 2}


def test_shared_round_resources_bind_models_but_isolate_telemetry():
    models = (_Model(1.0), _Model(1.0), _Model(1.0))
    resources = override_policy.RoundPolicyResources(
        checkpoint_round=0,
        models=models,
        support={(0, '3'): 100},
    )
    first = resources.bind(_Baseline(), load_spec())
    second = resources.bind(_Baseline(), load_spec())
    assert tuple(id(model) for model in first.models) == tuple(id(model) for model in resources.models)
    assert tuple(id(model) for model in second.models) == tuple(id(model) for model in resources.models)
    assert first.telemetry is not second.telemetry
    first.telemetry.override_count += 1
    assert second.telemetry.override_count == 0


def test_no_alternative_falls_back_without_model_scoring(monkeypatch):
    class OnlyBaseline(_Candidates):
        def __init__(self):
            self.candidates = (_Candidate(0, (0,), 'baseline'),)

        def candidate_index_for(self, options, action):
            return 0 if tuple(action) == (0,) else None

    _patch_surface(monkeypatch)
    monkeypatch.setattr(override_policy, 'observation_complete_actions', lambda observation: OnlyBaseline())
    policy = override_policy.RolloutQOverridePolicy(
        baseline=_Baseline(),
        models=[_Model(10.0), _Model(10.0), _Model(10.0)],
        config=replace(load_spec(), minimum_candidate_count=1),
        support={(0, '3'): 100},
    )
    assert policy.choose_action({'select': {'context': 0}}) == [0]
    assert policy.telemetry.reasons['no_alternative'] == 1
