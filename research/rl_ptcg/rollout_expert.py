"""Common-random-number, full-rollout Search API expert.

This module deliberately keeps the Search API boundary small so it can be used
with either the local engine or lightweight test doubles.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import random
import sys
from typing import Any, Callable, Mapping, Sequence

from .belief import compatible_deck_hypotheses, sample_search_guess
from .search_expert import ActionEvaluation, SearchDecision, candidate_actions


def _get(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)


def _terminal(result: Any, seat: int) -> float | None:
    if result == seat:
        return 1.0
    if result in (0, 1):
        return -1.0
    if result == 2:
        return 0.0
    return None


def _module_action(module: Any, observation: Any, rng: random.Random) -> Sequence[int]:
    chooser = getattr(module, "choose_options")
    try:
        return chooser(observation, rng=rng)
    except TypeError:
        return chooser(observation)


def _coin_action(select: Any, rng: random.Random) -> list[int]:
    options = list(_get(select, "option", []) or [])
    binary = [
        index for index, option in enumerate(options)
        if int(_get(option, "type", -1)) in (1, 2)
    ]
    choices = binary if len(binary) == 2 else list(range(len(options)))
    if not choices:
        return []
    return [choices[rng.randrange(len(choices))]]


def _rollout(state: Any, modules: Mapping[int, Any], root_seat: int,
             max_steps: int, rng: random.Random, coin_context: int) -> float | None:
    from cg.api import search_step
    for _ in range(max(0, int(max_steps))):
        observation = state.observation
        current = observation.current
        value = _terminal(_get(current, "result"), root_seat)
        if value is not None:
            return value
        seat = int(_get(current, "yourIndex", root_seat))
        select = _get(observation, "select", None)
        if select is None or not _get(select, "option", []):
            break
        # Search API's coin-head context is a binary manual decision.  Draw
        # independently per branch, but with the same seed across branches.
        if int(_get(select, "context", -1)) == coin_context:
            action = _coin_action(select, rng)
        else:
            module = modules.get(seat)
            if module is None:
                break
            action = _module_action(module, observation, rng)
        state = search_step(state.searchId, action)
    value = _terminal(_get(state.observation.current, "result"), root_seat)
    return value


def _paired_delta(candidate: Sequence[float], baseline: Sequence[float], confidence_z: float) -> tuple[float, float]:
    deltas = [float(value) - float(reference) for value, reference in zip(candidate, baseline)]
    if not deltas:
        return -math.inf, -math.inf
    mean = sum(deltas) / len(deltas)
    if len(deltas) == 1:
        return mean, mean
    variance = sum((value - mean) ** 2 for value in deltas) / (len(deltas) - 1)
    lower = mean - float(confidence_z) * math.sqrt(max(0.0, variance) / len(deltas))
    return mean, lower


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("ascii")
    return hashlib.blake2b(encoded, digest_size=16).hexdigest()


def _deck_hypothesis_signature(hypothesis: Sequence[int]) -> str:
    return "deck:" + _stable_digest([int(card_id) for card_id in sorted(hypothesis)])


def _hidden_world_id(guess: Any) -> str:
    zones = {
        name: [int(card_id) for card_id in getattr(guess, name)]
        for name in (
            "your_deck", "your_prize", "opponent_deck", "opponent_prize",
            "opponent_hand", "opponent_active", "unused_your_cards", "unused_opponent_cards",
        )
    }
    return "world:" + _stable_digest(zones)


def _explicit_actions(observation: Any, candidates: Sequence[Sequence[int]],
                      rule_action: Sequence[int]) -> tuple[list[list[int]], list[int]]:
    """Validate and canonically order complete root actions."""
    select = _get(observation, "select", None)
    options = list(_get(select, "option", []) or [])
    minimum = _get(select, "minCount", None)
    maximum = _get(select, "maxCount", None)
    if (isinstance(minimum, bool) or not isinstance(minimum, int)
            or isinstance(maximum, bool) or not isinstance(maximum, int)
            or minimum < 0 or maximum < minimum or maximum > len(options)):
        raise ValueError("invalid observation select bounds")

    def normalize(action: Sequence[int], label: str) -> tuple[int, ...]:
        if isinstance(action, (str, bytes)) or not isinstance(action, Sequence):
            raise ValueError("%s must be an action sequence" % label)
        indices = list(action)
        if not minimum <= len(indices) <= maximum:
            raise ValueError("%s has an invalid action size" % label)
        if any(isinstance(index, bool) or not isinstance(index, int) for index in indices):
            raise ValueError("%s contains a non-integer index" % label)
        if any(index < 0 or index >= len(options) for index in indices):
            raise ValueError("%s contains an out-of-range index" % label)
        if len(set(indices)) != len(indices):
            raise ValueError("%s contains a duplicate index" % label)
        return tuple(sorted(indices))

    if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Sequence) or not candidates:
        raise ValueError("explicit candidate actions must be a non-empty sequence")
    actions = []
    seen = set()
    for candidate in candidates:
        action = normalize(candidate, "explicit candidate action")
        if action not in seen:
            seen.add(action)
            actions.append(list(action))
    baseline = list(normalize(rule_action, "rule action"))
    if tuple(baseline) not in seen:
        raise ValueError("explicit candidate actions must include rule action")
    return actions, baseline


def choose_with_rollout(
    raw_observation: Any, modules_by_seat: Mapping[int, Any],
    your_decklist: Sequence[int], opponent_decklist: Sequence[int],
    rule_scores: Sequence[float], rule_action: Sequence[int], rng: random.Random,
    determinizations: int = 8, max_steps: int = 1000, top_options: int = 6,
    max_actions: int = 24, improvement_margin: float = 0.08,
    risk_penalty: float = 0.25, basic_pokemon_ids: set[int] | None = None,
    coin_context: int = 46, confidence_z: float = 1.0,
    min_successful_determinizations: int | None = None,
    opponent_deck_hypotheses: Sequence[Sequence[int]] | None = None,
    opponent_policy_modules: Sequence[Any] | None = None,
    your_policy_modules: Sequence[Any] | None = None,
    require_unique_hypothesis: bool = False,
    hypothesis_strategy: str = "robust",
    search_guesses: Sequence[Any] | None = None,
    candidate_mode: str = "ranked",
    max_complete_actions: int = 4096,
    return_scenario_values: bool = False,
    explicit_candidate_actions: Sequence[Sequence[int]] | None = None,
    branch_order: str = "forward",
    fresh_root_per_branch: bool = False,
    rollout_modules_factory: Callable[[int, int, int, Sequence[int]], Mapping[int, Any]] | None = None,
    seed_native_search: bool = False,
) -> SearchDecision:
    """Evaluate every candidate under every sampled root determinization.

    Explicit candidates are complete, unordered root actions.
    """
    from cg.api import search_begin, search_end, search_step, to_observation_class
    cg_api = sys.modules["cg.api"]
    search_seed = getattr(cg_api, "search_seed", None)
    if seed_native_search and not callable(search_seed):
        raise RuntimeError("seed_native_search requires an AgentSeed-enabled engine")
    observation = to_observation_class(raw_observation)
    perspective = int(observation.current.yourIndex)
    scenario_values = [] if return_scenario_values else None
    scenario_errors = [] if return_scenario_values else None
    if branch_order not in ("forward", "reverse"):
        raise ValueError("unknown branch order: %s" % branch_order)
    if explicit_candidate_actions is None:
        actions = candidate_actions(
            observation, rule_scores, rule_action, top_options, max_actions,
            mode=candidate_mode, max_complete_actions=max_complete_actions,
        )
    else:
        actions, rule_action = _explicit_actions(
            observation, explicit_candidate_actions, rule_action
        )
    if len(actions) <= 1 and explicit_candidate_actions is None:
        return SearchDecision(list(rule_action), list(rule_action), False, "one candidate", [], 0, 0, scenario_values, scenario_errors)
    collected = {tuple(a): [] for a in actions}
    hypotheses = compatible_deck_hypotheses(
        observation, [opponent_decklist, *(opponent_deck_hypotheses or [])]
    )
    if not hypotheses:
        return SearchDecision(
            list(rule_action), list(rule_action), False, "no compatible deck hypothesis", [], 0, 0, scenario_values, scenario_errors
        )
    if (require_unique_hypothesis or hypothesis_strategy == "unique") and len(hypotheses) != 1:
        return SearchDecision(
            list(rule_action), list(rule_action), False, "deck hypothesis is not unique", [], 0, 0, scenario_values, scenario_errors
        )
    if hypothesis_strategy == "first":
        hypotheses = hypotheses[:1]
    elif hypothesis_strategy not in ("robust", "unique"):
        raise ValueError("unknown hypothesis strategy: %s" % hypothesis_strategy)
    opponent_seat = 1 - perspective
    policy_modules = list(opponent_policy_modules or [modules_by_seat.get(opponent_seat)])
    if not policy_modules:
        policy_modules = [None]
    continuation_modules = list(your_policy_modules or [modules_by_seat.get(perspective)])
    if not continuation_modules:
        continuation_modules = [None]
    scenarios = [
        (
            _deck_hypothesis_signature(hypothesis), hypothesis,
            policy_index, policy_module, continuation_index, continuation_module,
        )
        for hypothesis in hypotheses
        for policy_index, policy_module in enumerate(policy_modules)
        for continuation_index, continuation_module in enumerate(continuation_modules)
    ]
    scenario_collected = {
        (signature, policy_index, continuation_index): {tuple(action): [] for action in actions}
        for signature, _, policy_index, _, continuation_index, _ in scenarios
    }
    errors = successful = 0

    def begin_search(guess: Any, isolate: bool, native_seed: int) -> Any:
        if seed_native_search:
            search_seed(int(native_seed) & 0xFFFFFFFF)
        source_observation = deepcopy(observation) if isolate else observation
        zones = [
            list(guess.your_deck), list(guess.your_prize),
            list(guess.opponent_deck), list(guess.opponent_prize),
            list(guess.opponent_hand), list(guess.opponent_active),
        ]
        return search_begin(source_observation, *zones, manual_coin=True)

    for determination_index in range(max(1, int(determinizations))):
        try:
            (
                hypothesis_signature, opponent_hypothesis, policy_index,
                policy_module, continuation_index, continuation_module,
            ) = (
                scenarios[determination_index % len(scenarios)]
            )
            if search_guesses:
                guess = search_guesses[determination_index % len(search_guesses)]
            else:
                guess = sample_search_guess(
                    observation, your_decklist, opponent_hypothesis, rng, basic_pokemon_ids
                )
            seed = rng.getrandbits(64)
            staged = {}
            rollout_modules = dict(modules_by_seat)
            if policy_module is not None:
                rollout_modules[opponent_seat] = policy_module
            if continuation_module is not None:
                rollout_modules[perspective] = continuation_module
            branch_actions = actions if branch_order == "forward" else list(reversed(actions))
            shared_root = None
            try:
                if not fresh_root_per_branch:
                    shared_root = begin_search(guess, False, seed)
                for action in branch_actions:
                    root = shared_root
                    if fresh_root_per_branch:
                        root = begin_search(guess, True, seed)
                    try:
                        branch_rng = random.Random(seed)
                        child = search_step(root.searchId, list(action))
                        branch_modules = (
                            dict(rollout_modules_factory(
                                determination_index, policy_index,
                                continuation_index, action,
                            ))
                            if rollout_modules_factory is not None
                            else rollout_modules
                        )
                        value = _rollout(
                            child, branch_modules, perspective, max_steps, branch_rng, coin_context
                        )
                        if value is None:
                            raise RuntimeError("rollout did not reach a terminal state")
                        staged[tuple(action)] = value
                    finally:
                        if fresh_root_per_branch:
                            search_end()
                for action in actions:
                    key = tuple(action)
                    value = staged[key]
                    collected[key].append(value)
                    scenario_collected[(hypothesis_signature, policy_index, continuation_index)][key].append(value)
                if scenario_values is not None:
                    hidden_world_id = _hidden_world_id(guess)
                    scenario_values.extend({
                        "particle_index": determination_index,
                        "determination_index": determination_index,
                        "opponent_policy_index": policy_index,
                        "continuation_policy_index": continuation_index,
                        "hypothesis_signature": hypothesis_signature,
                        "deck_hypothesis_signature": hypothesis_signature,
                        "hidden_world_id": hidden_world_id,
                        "action": list(action),
                        "terminal_utility": value,
                    } for action in actions for value in [staged[tuple(action)]])
                successful += 1
            finally:
                if shared_root is not None:
                    search_end()
        except Exception as exc:
            errors += 1
            if scenario_errors is not None:
                scenario_errors.append("%s: %s" % (type(exc).__name__, exc))
    evaluations = []
    for action in actions:
        values = collected[tuple(action)]
        if values:
            mean = sum(values) / len(values)
            stddev = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
            evaluations.append(ActionEvaluation(action, values, mean, stddev, mean - risk_penalty * stddev))
    baseline = next((e for e in evaluations if e.action == list(rule_action)), None)
    if not evaluations or baseline is None:
        return SearchDecision(list(rule_action), list(rule_action), False, "all searches failed", evaluations, successful, errors, scenario_values, scenario_errors)
    required = (
        max(2, math.ceil(max(1, int(determinizations)) * 0.6))
        if min_successful_determinizations is None else max(1, int(min_successful_determinizations))
    )
    if successful < required:
        return SearchDecision(
            list(rule_action), list(rule_action), False, "insufficient complete determinizations",
            evaluations, successful, errors, scenario_values, scenario_errors,
        )
    if any(
        not any(values.values())
        for values in scenario_collected.values()
    ):
        return SearchDecision(
            list(rule_action), list(rule_action), False, "incomplete scenario coverage",
            evaluations, successful, errors, scenario_values, scenario_errors,
        )
    paired = {
        tuple(evaluation.action): _paired_delta(evaluation.values, baseline.values, confidence_z)
        for evaluation in evaluations
    }
    per_scenario_mean = {}
    for evaluation in evaluations:
        action = tuple(evaluation.action)
        means = []
        for values in scenario_collected.values():
            candidate_values = values[action]
            baseline_values = values[tuple(rule_action)]
            if candidate_values and baseline_values:
                means.append(_paired_delta(candidate_values, baseline_values, 0.0)[0])
        per_scenario_mean[action] = min(means) if means else -math.inf
    best = max(
        evaluations,
        key=lambda evaluation: (
            per_scenario_mean[tuple(evaluation.action)],
            paired[tuple(evaluation.action)][1], paired[tuple(evaluation.action)][0],
            evaluation.downside, evaluation.action == list(rule_action),
        ),
    )
    delta_mean, delta_lower = paired[tuple(best.action)]
    changed = (
        best.action != list(rule_action)
        and delta_mean >= float(improvement_margin)
        and delta_lower >= 0.0
        and per_scenario_mean[tuple(best.action)] >= 0.0
    )
    return SearchDecision(best.action if changed else list(rule_action), list(rule_action), changed,
                          "accepted improvement" if changed else "margin or risk gate",
                          evaluations, successful, errors, scenario_values, scenario_errors)


choose_with_search = choose_with_rollout
