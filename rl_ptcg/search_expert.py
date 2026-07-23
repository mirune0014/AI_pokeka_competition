"""Belief-sampled one-action search guided by a learned public-state value."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import math
import random
from typing import Any, Sequence

try:
    from .belief import sample_search_guess
    from .encoding import encode_state
except ImportError:
    from belief import sample_search_guess
    from encoding import encode_state


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def candidate_actions(
    observation: Any,
    rule_scores: Sequence[float],
    rule_action: Sequence[int],
    top_options: int = 6,
    max_actions: int = 24,
    mode: str = "ranked",
    max_complete_actions: int = 4096,
) -> list[list[int]]:
    select = _get(observation, "select", {}) or {}
    options = list(_get(select, "option", []) or [])
    if len(options) != len(rule_scores):
        raise ValueError("rule score count does not match legal options")
    minimum = int(_get(select, "minCount", 0) or 0)
    maximum = int(_get(select, "maxCount", minimum) or minimum)
    baseline = [int(index) for index in rule_action]
    if mode == "complete":
        minimum = max(0, minimum)
        maximum = min(len(options), maximum)
        complete_count = sum(math.comb(len(options), count) for count in range(minimum, maximum + 1))
        baseline_is_combination = (
            minimum <= len(baseline) <= maximum
            and baseline == sorted(set(baseline))
            and all(0 <= index < len(options) for index in baseline)
        )
        if not baseline_is_combination:
            complete_count += 1
        if complete_count > int(max_complete_actions):
            raise ValueError(
                "complete candidate count %d exceeds max_complete_actions %d"
                % (complete_count, int(max_complete_actions))
            )
        actions = [baseline]
        for count in range(minimum, maximum + 1):
            for action in combinations(range(len(options)), count):
                candidate = list(action)
                if candidate != baseline:
                    actions.append(candidate)
        return actions
    if mode != "ranked":
        raise ValueError("unknown candidate action mode: %s" % mode)
    ranked = sorted(range(len(options)), key=lambda index: (-float(rule_scores[index]), index))
    pool = ranked[:max(1, int(top_options))]
    for index in baseline:
        if index not in pool:
            pool.append(index)
    count_candidates = {len(baseline), minimum, min(maximum, len(pool))}
    actions = {tuple(baseline)}
    for count in sorted(count_candidates):
        if count < minimum or count > maximum or count > len(pool):
            continue
        for action in combinations(pool, count):
            if count > minimum and any(float(rule_scores[index]) < 0.0 for index in action):
                continue
            actions.add(tuple(action))
    ordered = sorted(
        actions,
        key=lambda action: (
            action != tuple(baseline),
            -sum(float(rule_scores[index]) for index in action),
            action,
        ),
    )
    return [list(action) for action in ordered[:max(1, int(max_actions))]]


def load_value_model(checkpoint_path, device="cpu"):
    import torch
    try:
        from .policy_value import ModelConfig, PolicyValueNet
    except ImportError:
        from policy_value import ModelConfig, PolicyValueNet
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model = PolicyValueNet(ModelConfig.from_dict(checkpoint["model_config"])).to(device)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model


def predict_public_value(
    model, observation: Any, perspective_seat: int, matchup="unknown",
    opponent_decklist: Sequence[int] | None = None, device="cpu",
) -> float:
    import torch
    try:
        from .train_policy_value import matchup_index
    except ImportError:
        from train_policy_value import matchup_index
    vector = torch.tensor([encode_state(observation, perspective_seat)], dtype=torch.float32, device=device)
    matchup_ids = torch.tensor([matchup_index(matchup, model.config.matchup_names)], dtype=torch.long, device=device)
    opponent_deck = None
    if opponent_decklist is not None:
        opponent_deck = torch.tensor([list(opponent_decklist)], dtype=torch.long, device=device)
    with torch.inference_mode():
        return float(model.predict_value(vector, matchup_ids, opponent_deck)[0])


@dataclass(frozen=True)
class ActionEvaluation:
    action: list[int]
    values: list[float]
    mean: float
    stddev: float
    downside: float


@dataclass(frozen=True)
class SearchDecision:
    selected: list[int]
    baseline: list[int]
    changed: bool
    reason: str
    evaluations: list[ActionEvaluation]
    determinizations: int
    errors: int
    scenario_values: list[dict[str, Any]] | None = None
    scenario_errors: list[str] | None = None


def _terminal_value(result: Any, perspective_seat: int) -> float | None:
    if result == perspective_seat:
        return 1.0
    if result in (0, 1):
        return -1.0
    if result == 2:
        return 0.0
    return None


def _finish_prompt_chain(module: Any, state: Any, perspective_seat: int, max_prompt_steps: int):
    from cg.api import search_step
    current_state = state
    for _ in range(max_prompt_steps):
        observation = current_state.observation
        current = observation.current
        if current.result is not None and current.result >= 0:
            break
        if current.yourIndex != perspective_seat:
            break
        select = observation.select
        if select is None or not select.option:
            break
        if int(select.context) == 0:
            break
        action = module.choose_options(observation)
        current_state = search_step(current_state.searchId, action)
    return current_state


def choose_with_search(
    raw_observation: dict,
    module: Any,
    model: Any,
    your_decklist: Sequence[int],
    opponent_decklist: Sequence[int],
    rule_scores: Sequence[float],
    rule_action: Sequence[int],
    rng: random.Random,
    determinizations: int = 4,
    top_options: int = 6,
    max_actions: int = 24,
    max_prompt_steps: int = 12,
    improvement_margin: float = 0.08,
    risk_penalty: float = 0.25,
    device: str = "cpu",
    basic_pokemon_ids: set[int] | None = None,
    matchup: str = "unknown",
) -> SearchDecision:
    from cg.api import search_begin, search_end, search_step, to_observation_class

    observation = to_observation_class(raw_observation)
    perspective = int(observation.current.yourIndex)
    actions = candidate_actions(observation, rule_scores, rule_action, top_options, max_actions)
    if len(actions) <= 1:
        return SearchDecision(list(rule_action), list(rule_action), False, "one candidate", [], 0, 0)
    collected = {tuple(action): [] for action in actions}
    errors = 0
    successful = 0
    for _ in range(max(1, int(determinizations))):
        try:
            guess = sample_search_guess(
                observation, your_decklist, opponent_decklist, rng, basic_pokemon_ids
            )
            root = search_begin(
                observation, guess.your_deck, guess.your_prize, guess.opponent_deck,
                guess.opponent_prize, guess.opponent_hand, guess.opponent_active,
                manual_coin=True,
            )
            try:
                for action in actions:
                    child = search_step(root.searchId, action)
                    leaf = _finish_prompt_chain(module, child, perspective, max_prompt_steps)
                    result = leaf.observation.current.result
                    value = _terminal_value(result, perspective)
                    if value is None:
                        value = predict_public_value(
                            model, leaf.observation, perspective, matchup, opponent_decklist, device
                        )
                    collected[tuple(action)].append(value)
                successful += 1
            finally:
                search_end()
        except Exception:
            errors += 1
    if successful == 0:
        return SearchDecision(list(rule_action), list(rule_action), False, "all searches failed", [], 0, errors)
    evaluations = []
    for action in actions:
        values = collected[tuple(action)]
        if not values:
            continue
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        stddev = math.sqrt(max(0.0, variance))
        evaluations.append(ActionEvaluation(action, values, mean, stddev, mean - risk_penalty * stddev))
    baseline_eval = next((value for value in evaluations if value.action == list(rule_action)), None)
    if baseline_eval is None:
        return SearchDecision(list(rule_action), list(rule_action), False, "baseline missing", evaluations, successful, errors)
    best = max(evaluations, key=lambda value: (value.downside, value.mean, value.action == list(rule_action)))
    improves = (
        best.action != list(rule_action)
        and best.mean >= baseline_eval.mean + float(improvement_margin)
        and best.downside >= baseline_eval.downside
    )
    return SearchDecision(
        best.action if improves else list(rule_action), list(rule_action), improves,
        "accepted improvement" if improves else "margin or risk gate",
        evaluations, successful, errors,
    )
