"""Leakage-safe selective model override for Gold prompt rule priors."""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import torch

from .gold_prompt_ranker import PromptExample, PromptRanker, predict_action_id


SCHEMA_VERSION = "gold_prompt_safety_gate.v1"
DEFAULT_THRESHOLD_GRID = (0.0, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0)
DEFAULT_CONFIDENCE_Z = 1.2815515655446004


def canonical_bytes(value: Any, *, pretty: bool = False) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True,
                       indent=2 if pretty else None,
                       separators=None if pretty else (",", ":")) + "\n").encode("ascii")


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_once(path: Path, data: bytes) -> None:
    """Create an artifact once, allowing only byte-identical reruns."""
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError("refusing to replace non-identical gate artifact: %s" % path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def write_json_once(path: Path, value: Mapping[str, Any]) -> None:
    write_once(path, canonical_bytes(value, pretty=True))


def validate_thresholds(values: Sequence[float]) -> tuple[float, ...]:
    if not values:
        raise ValueError("threshold grid must be non-empty")
    result = []
    seen = set()
    for raw in values:
        if isinstance(raw, bool):
            raise ValueError("thresholds must be finite non-negative numbers")
        value = float(raw)
        if not math.isfinite(value) or value < 0:
            raise ValueError("thresholds must be finite non-negative numbers")
        if value in seen:
            raise ValueError("thresholds must not contain duplicates")
        seen.add(value)
        result.append(value)
    return tuple(sorted(result))


def validate_wilson_settings(min_discordant: int, confidence_z: float,
                            min_improvement_probability: float) -> None:
    if (isinstance(min_discordant, bool) or not isinstance(min_discordant, int)
            or min_discordant < 1):
        raise ValueError("min_discordant must be a positive integer")
    if not math.isfinite(float(confidence_z)) or float(confidence_z) <= 0:
        raise ValueError("confidence_z must be finite and positive")
    if (not math.isfinite(float(min_improvement_probability)) or
            not 0.0 <= float(min_improvement_probability) < 1.0):
        raise ValueError("min_improvement_probability must be finite in [0, 1)")


def wilson_lower_bound(successes: int, trials: int, z: float = DEFAULT_CONFIDENCE_Z) -> float:
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("invalid Wilson counts")
    if trials == 0:
        return 0.0
    if not math.isfinite(float(z)) or z <= 0:
        raise ValueError("Wilson z must be finite and positive")
    proportion = successes / trials
    z2 = z * z
    return ((proportion + z2 / (2 * trials) - z * math.sqrt(
        (proportion * (1 - proportion) + z2 / (4 * trials)) / trials
    )) / (1 + z2 / trials))


def validate_ranker_evaluation_report(path: Path) -> dict[str, Any]:
    try:
        report = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("could not read ranker evaluation report") from error
    if not isinstance(report, dict) or not isinstance(report.get("fit_splits"), list):
        raise ValueError("ranker evaluation report has no fit_splits")
    fit_splits = {str(value) for value in report["fit_splits"]}
    if "development" in fit_splits:
        raise ValueError("ranker was fit on development; gate selection would be in-sample")
    if fit_splits != {"train"}:
        raise ValueError("ranker fit_splits must be exactly train for frozen holdout evaluation")
    return report


def _entropy(scores: torch.Tensor) -> float:
    if len(scores) <= 1:
        return 0.0
    probabilities = torch.softmax(scores, dim=0)
    # x*log(x) tends to zero, but float32 softmax can underflow to an exact
    # zero. Clamp only for the diagnostic so an otherwise valid score vector
    # cannot serialize a NaN entropy.
    safe = probabilities.clamp_min(torch.finfo(probabilities.dtype).tiny)
    entropy = -float(torch.sum(probabilities * torch.log(safe)).detach().cpu())
    return entropy / math.log(len(scores))


def decision_diagnostics(model: PromptRanker, examples: Iterable[PromptExample],
                         priors: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    examples = list(examples)
    expected = {item.decision_id for item in examples}
    if len(expected) != len(examples):
        raise ValueError("prompt examples have duplicate decision IDs")
    if set(priors) != expected:
        raise ValueError("rule priors and prompt examples have mismatched IDs")
    rows = []
    model.eval()
    with torch.no_grad():
        for item in sorted(examples, key=lambda value: value.decision_id):
            prior = priors[item.decision_id]
            if not isinstance(prior, Mapping) or "baseline_correct" not in prior:
                raise ValueError("rule prior is malformed for decision %s" % item.decision_id)
            scores = model.score(item.state, item.actions, item.style_id)
            if scores.ndim != 1 or len(scores) != len(item.action_ids) or not torch.isfinite(scores).all():
                raise ValueError("ranker produced invalid scores for decision %s" % item.decision_id)
            model_id = predict_action_id(scores, item.action_ids)
            rule_id = prior.get("rule_action_id")
            mapped = isinstance(rule_id, str) and rule_id in item.action_ids
            rule_correct = bool(prior["baseline_correct"])
            if mapped:
                rule_score = float(scores[item.action_ids.index(rule_id)].detach().cpu())
                model_score = float(scores[item.action_ids.index(model_id)].detach().cpu())
                score_delta: float | None = model_score - rule_score
            else:
                score_delta = None
            ordered_scores = sorted((float(value) for value in scores.detach().cpu()), reverse=True)
            rows.append({
                "decision_id": item.decision_id,
                "split": item.split,
                "style_id": item.style_id,
                "action_type": item.action_type,
                "mapped": mapped,
                "baseline_correct": rule_correct,
                "model_correct": model_id == item.target_id,
                "model_differs_from_mapped_rule": bool(mapped and model_id != rule_id),
                "model_vs_rule_score_delta": score_delta,
                "model_top_vs_second_margin": ordered_scores[0] - ordered_scores[1] if len(ordered_scores) > 1 else 0.0,
                "normalized_entropy": _entropy(scores),
            })
    return rows


def _threshold_summary(rows: Sequence[Mapping[str, Any]], threshold: float, z: float) -> dict[str, Any]:
    eligible = [row for row in rows if row["mapped"] and row["model_differs_from_mapped_rule"]
                and float(row["model_vs_rule_score_delta"]) >= threshold]
    improvements = sum(bool(row["model_correct"]) and not bool(row["baseline_correct"]) for row in eligible)
    regressions = sum(bool(row["baseline_correct"]) and not bool(row["model_correct"]) for row in eligible)
    discordants = improvements + regressions
    return {"threshold": threshold, "override_count": len(eligible), "improvements": improvements,
            "regressions": regressions, "net_gain": improvements - regressions,
            "discordants": discordants,
            "wilson_lower_bound": wilson_lower_bound(improvements, discordants, z)}


def select_rules(rows: Sequence[Mapping[str, Any]], *, thresholds: Sequence[float] = DEFAULT_THRESHOLD_GRID,
                 min_discordant: int = 10, confidence_z: float = DEFAULT_CONFIDENCE_Z,
                 min_improvement_probability: float = 0.5) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    values = validate_thresholds(thresholds)
    validate_wilson_settings(min_discordant, confidence_z, min_improvement_probability)
    by_type: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("split") != "development":
            raise ValueError("rule selection accepts development rows only")
        by_type[str(row["action_type"])].append(row)
    selected, sweep = {}, []
    for action_type in sorted(by_type):
        candidates = []
        for threshold in values:
            result = _threshold_summary(by_type[action_type], threshold, confidence_z)
            result["action_type"] = action_type
            result["passes"] = (result["discordants"] >= min_discordant and
                                result["wilson_lower_bound"] > min_improvement_probability)
            sweep.append(result)
            if result["passes"]:
                candidates.append(result)
        if candidates:
            chosen = min(candidates, key=lambda value: (-value["net_gain"], -value["wilson_lower_bound"],
                                                          value["override_count"], -value["threshold"]))
            selected[action_type] = dict(chosen)
        else:
            selected[action_type] = {"action_type": action_type, "threshold": None,
                                     "mode": "rule_fallback"}
    return selected, sweep


def apply_gate(rows: Sequence[Mapping[str, Any]], rules: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        rule = rules.get(str(row["action_type"]))
        threshold = None if rule is None else rule.get("threshold")
        override = (threshold is not None and bool(row["mapped"]) and
                    bool(row["model_differs_from_mapped_rule"]) and
                    float(row["model_vs_rule_score_delta"]) >= float(threshold))
        enriched = dict(row)
        enriched["override"] = override
        enriched["gated_correct"] = bool(row["model_correct"]) if override else bool(row["baseline_correct"])
        result.append(enriched)
    return result


def evaluate_gate(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        for key in ("overall:overall", "style:" + str(row["style_id"]),
                    "action_type:" + str(row["action_type"])):
            groups[key].append(row)
    report = {}
    for key, values in sorted(groups.items()):
        count = len(values)
        improvements = sum(bool(row["override"]) and bool(row["model_correct"]) and not bool(row["baseline_correct"]) for row in values)
        regressions = sum(bool(row["override"]) and bool(row["baseline_correct"]) and not bool(row["model_correct"]) for row in values)
        report[key] = {"count": count,
                       "baseline_accuracy": sum(bool(row["baseline_correct"]) for row in values) / count,
                       "model_accuracy": sum(bool(row["model_correct"]) for row in values) / count,
                       "gated_accuracy": sum(bool(row["gated_correct"]) for row in values) / count,
                       "override_count": sum(bool(row["override"]) for row in values),
                       "override_rate": sum(bool(row["override"]) for row in values) / count,
                       "improvements": improvements, "regressions": regressions,
                       "net_gain": improvements - regressions}
    return report
