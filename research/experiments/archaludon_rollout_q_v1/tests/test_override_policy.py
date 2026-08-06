from __future__ import annotations

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
        values = torch.zeros(candidate.shape[0])
        values[1] = self.value
        return values


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
