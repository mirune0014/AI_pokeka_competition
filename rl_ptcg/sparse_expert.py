"""Dependency-free supervised fitting for sparse Search-rollout labels.

Examples are ordinary dictionaries and can be written directly as JSON.  This
module scores only the supplied options; legality and option filtering belong
to the caller.
"""
from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping

try:
    from .residual_policy import option_features
except ImportError:
    from residual_policy import option_features


def make_example(options, baseline_action, expert_action, *, matchup=None,
                 opponent=None, metadata=None):
    """Build a JSON-serializable training example.

    ``options`` is a sequence of ``{"features": {...}, "baseline_score": x}``
    records.  Scores may also be supplied as ``normalized_score``.
    Actions are option indices, in selection order for multi-select decisions.
    """
    result = {
        "options": [dict(option) for option in options],
        "baseline_action": [int(x) for x in baseline_action],
        "expert_action": [int(x) for x in expert_action],
        "matchup": matchup,
        "opponent": opponent,
        "metadata": dict(metadata or {}),
    }
    for option in result["options"]:
        option["features"] = {str(k): float(v) for k, v in option.get("features", {}).items()}
        if "normalized_score" not in option:
            option["normalized_score"] = float(option.get("baseline_score", 0.0))
    return result


def make_observation_example(
    observation, scores, baseline_action, expert_action, *, score_option,
    option_card, option_target, detect_matchup, top_n=6, opponent=None, metadata=None,
    include_all_options=False, pool_indices=None,
):
    """Build the same safe top-N sparse option pool used by the residual policy."""
    legal = list(getattr(getattr(observation, "select", None), "option", []) or [])
    if len(legal) != len(scores):
        raise ValueError("score count does not match legal options")
    baseline = [int(index) for index in baseline_action]
    expert = [int(index) for index in expert_action]
    required = set(baseline) | set(expert)
    scored = sorted(
        ((float(score), index, legal[index]) for index, score in enumerate(scores)),
        key=lambda item: (-item[0], item[1]),
    )
    if pool_indices is not None:
        wanted_indices = {int(index) for index in pool_indices}
        safe = [item for item in scored if item[1] in wanted_indices]
    else:
        safe = list(scored) if include_all_options else [
            item for item in scored if item[0] >= 0.0 or item[1] in required
        ]
    if not safe or any(index not in {item[1] for item in safe} for index in required):
        raise ValueError("expert action is outside the safe option pool")
    values = [item[0] for item in safe]
    mean = sum(values) / len(values)
    spread = max(max(values) - min(values), 1.0)
    ranks = {index: rank for rank, (_score, index, _option) in enumerate(safe)}
    normalized = {index: (score - mean) / spread for score, index, _option in safe}
    wanted = max(len(baseline), len(expert), 1)
    pool_size = len(safe) if include_all_options or pool_indices is not None else max(
        wanted, min(len(safe), max(1, int(top_n)))
    )
    pool = list(safe[:pool_size])
    present = {index for _score, index, _option in pool}
    pool.extend(item for item in safe if item[1] in required and item[1] not in present)
    global_indices = [index for _score, index, _option in pool]
    local_index = {global_index: index for index, global_index in enumerate(global_indices)}
    matchup = str(detect_matchup(observation))
    options = []
    for score, index, option in pool:
        features = option_features(
            observation, option, score, ranks[index], len(legal),
            option_card, option_target, detect_matchup, normalized[index],
        )
        options.append({
            "option_index": index,
            "features": features,
            "normalized_score": normalized[index],
        })
    return make_example(
        options,
        [local_index[index] for index in baseline],
        [local_index[index] for index in expert],
        matchup=matchup, opponent=opponent,
        metadata={
            **dict(metadata or {}),
            "global_option_indices": global_indices,
            "global_baseline_action": baseline,
            "global_expert_action": expert,
        },
    )


def _options(example):
    return example.get("options", []) if isinstance(example, Mapping) else []


def _logits(example, weights, residual_cap):
    values = []
    for option in _options(example):
        base = float(option.get("normalized_score", option.get("baseline_score", 0.0)))
        features = option.get("features", {})
        residual = sum(float(weights.get(str(k), 0.0)) * float(v) for k, v in features.items())
        residual = max(-residual_cap, min(residual_cap, residual))
        values.append(base + residual)
    return values


def predict(example, weights=None, residual_cap=0.35):
    """Greedily predict the expert action count, preserving PL order."""
    weights = weights or {}
    remaining = list(range(len(_options(example))))
    wanted = len(example.get("expert_action", example.get("baseline_action", [])))
    chosen = []
    logits = _logits(example, weights, max(0.0, float(residual_cap)))
    for _ in range(min(wanted, len(remaining))):
        picked = max(remaining, key=lambda index: (logits[index], -index))
        chosen.append(picked)
        remaining.remove(picked)
    return chosen


def _pl_loss_gradient(example, weights, residual_cap):
    labels = [int(x) for x in example.get("expert_action", [])]
    logits = _logits(example, weights, residual_cap)
    remaining = list(range(len(logits)))
    loss = 0.0
    gradient = {}
    for picked in labels:
        if picked not in remaining:
            continue
        top = max(logits[index] for index in remaining)
        raw = {index: math.exp(max(-60.0, min(60.0, logits[index] - top))) for index in remaining}
        total = sum(raw.values())
        loss += math.log(total) + top - logits[picked]
        for index in remaining:
            coefficient = raw[index] / total - (1.0 if index == picked else 0.0)
            for key, value in _options(example)[index].get("features", {}).items():
                gradient[str(key)] = gradient.get(str(key), 0.0) + coefficient * float(value)
        remaining.remove(picked)
    return loss, gradient


def evaluate(examples: Iterable[Mapping], weights=None, residual_cap=0.35):
    """Return loss, exact set agreement, and agreement on changed labels."""
    weights = weights or {}
    rows = list(examples or [])
    total_loss = total_weight = 0.0
    exact = changed = changed_total = 0
    for example in rows:
        weight = float(example.get("weight", 1.0))
        if weight <= 0:
            continue
        loss, _ = _pl_loss_gradient(example, weights, max(0.0, float(residual_cap)))
        predicted = predict(example, weights, residual_cap)
        target = list(map(int, example.get("expert_action", [])))
        if set(predicted) == set(target):
            exact += 1
        baseline = list(map(int, example.get("baseline_action", [])))
        if set(target) != set(baseline):
            changed_total += 1
            changed += set(predicted) == set(target)
        total_loss += weight * loss
        total_weight += weight
    return {"loss": total_loss / total_weight if total_weight else 0.0,
            "exact_agreement": exact / len(rows) if rows else 0.0,
            "changed_label_agreement": changed / changed_total if changed_total else 0.0,
            "examples": len(rows), "changed_examples": changed_total}


def train(examples: Iterable[Mapping], *, epochs=25, learning_rate=0.1,
          l2=0.001, weight_clip=2.0, residual_cap=0.35, changed_weight=2.0):
    """Fit sparse weights with deterministic full-batch PL cross-entropy."""
    rows = list(examples or [])
    weights = {}
    for _ in range(max(0, int(epochs))):
        gradient, total = {}, 0.0
        for example in rows:
            factor = float(example.get("weight", 1.0))
            if set(example.get("expert_action", [])) != set(example.get("baseline_action", [])):
                factor *= float(changed_weight)
            if factor <= 0:
                continue
            loss, local = _pl_loss_gradient(example, weights, max(0.0, float(residual_cap)))
            total += factor
            for key, value in local.items():
                gradient[key] = gradient.get(key, 0.0) + factor * value
        if not total:
            break
        for key in set(weights) | set(gradient):
            update = gradient.get(key, 0.0) / total + float(l2) * weights.get(key, 0.0)
            weights[key] = max(-weight_clip, min(weight_clip, weights.get(key, 0.0) - float(learning_rate) * update))
    return {"weights": weights, "metrics": evaluate(rows, weights, residual_cap)}


def save_weights(weights, path):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"weights": {str(k): float(v) for k, v in weights.items()}}, handle, sort_keys=True)


def load_weights(path):
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    return {str(k): float(v) for k, v in payload.get("weights", payload).items()}
