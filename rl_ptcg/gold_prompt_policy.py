"""Inference adapter for a Gold prompt ranker with a rule-policy fallback."""
from __future__ import annotations

from typing import Any, Callable, Mapping

import torch

from .canonical_actions import canonicalize_option
from .gold_prompt_ranker import (
    UNKNOWN_STYLE,
    PromptRanker,
    _feature_sources,
    _hashed_features,
    _semantic_id,
    predict_action_id,
)
from .replay_records import ReplayDecisionRecord


class UnsupportedPrompt(ValueError):
    pass


def rank_single_selection(
    model: PromptRanker, observation: Mapping[str, Any],
    *, style_id: str = UNKNOWN_STYLE,
) -> list[int]:
    """Rank a one-of-N engine prompt using only reproducible actor-view inputs."""
    select = observation.get("select") or {}
    options = select.get("option", select.get("options", []))
    minimum = int(select.get("minCount", select.get("min_count", 0)))
    maximum = int(select.get("maxCount", select.get("max_count", len(options))))
    if not isinstance(options, list) or not options or minimum != 1 or maximum != 1:
        raise UnsupportedPrompt("Gold prompt ranker supports exactly-one prompts only")
    if model.config.include_public_history:
        raise UnsupportedPrompt("ranker requires public history unavailable to this adapter")
    record = ReplayDecisionRecord.from_observation(
        observation, [0], episode_id="runtime", submission_id="runtime",
        style_id="runtime", decision_step=0, replay_step=0,
        public_history=(), private_action_history=(),
        timestamp="1970-01-01T00:00:00+00:00",
    )
    payload = record.to_dict()
    semantic_options = [canonicalize_option(observation, option).to_dict() for option in options]
    sources = _feature_sources(
        payload, semantic_options,
        include_known_private=model.config.include_known_private,
        include_public_history=False,
    )
    state = _hashed_features(
        {key: value for key, value in sources.items() if key != "legal_semantic_options"},
        "state", model.config.feature_dim,
    )
    by_id: dict[str, tuple[dict[str, Any], list[int]]] = {}
    for index, option in enumerate(semantic_options):
        identifier = _semantic_id(option)
        if identifier not in by_id:
            by_id[identifier] = (option, [])
        elif by_id[identifier][0] != option:
            raise ValueError("semantic option hash collision")
        by_id[identifier][1].append(index)
    ordered = sorted(by_id.items())
    action_ids = tuple(identifier for identifier, _value in ordered)
    actions = torch.stack([
        _hashed_features(value[0], "action", model.config.feature_dim)
        for _identifier, value in ordered
    ])
    model.eval()
    with torch.no_grad():
        predicted = predict_action_id(model.score(state, actions, style_id), action_ids)
    return [min(by_id[predicted][1])]


class GoldPromptHybridPolicy:
    def __init__(
        self, model: PromptRanker,
        fallback: Callable[[dict[str, Any]], list[int]],
        *, style_id: str = UNKNOWN_STYLE,
    ) -> None:
        self.model = model
        self.fallback = fallback
        self.style_id = style_id

    def __call__(self, observation: dict[str, Any]) -> list[int]:
        if observation.get("select") is None:
            return self.fallback(observation)
        try:
            return rank_single_selection(
                self.model, observation, style_id=self.style_id,
            )
        except (UnsupportedPrompt, KeyError, TypeError, ValueError, RuntimeError):
            return self.fallback(observation)
