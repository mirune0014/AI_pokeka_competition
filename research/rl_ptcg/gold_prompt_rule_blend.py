"""Rule-prior safety blend for the Gold prompt behavior ranker."""
from __future__ import annotations

from collections import defaultdict
from hashlib import blake2b, sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import torch

from .gold_prompt_ranker import (
    PromptExample,
    PromptRanker,
    _canonical,
    _load_allowed_records,
    _one_selection_target,
    _semantic_id,
    predict_action_id,
)
from .split_manifest import load_split_manifest


SCHEMA_VERSION = "gold_prompt_rule_blend.v1"
DEFAULT_ALPHA_GRID = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _complete_action_id(action: Mapping[str, Any]) -> str:
    return blake2b(_canonical(action).encode("ascii"), digest_size=32).hexdigest()


def _single_action(option: Mapping[str, Any], chosen: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "selection_context": chosen["selection_context"],
        "minimum_count": chosen["minimum_count"],
        "maximum_count": chosen["maximum_count"],
        "selections": [dict(option)],
    }


def load_audit_rows(audit_dir: str | Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    root = Path(audit_dir)
    checksum_path = root / "checksum_manifest.json"
    rows_path = root / "rows.jsonl"
    checksum = json.loads(checksum_path.read_text(encoding="ascii"))
    if checksum.get("schema_version") != "gold_disagreement_audit.v1":
        raise ValueError("unsupported disagreement audit")
    if checksum.get("rows_sha256") != file_sha256(rows_path):
        raise ValueError("disagreement audit rows hash mismatch")
    rows = {}
    for number, line in enumerate(rows_path.read_text(encoding="ascii").splitlines(), 1):
        value = json.loads(line)
        decision_id = value.get("decision_id")
        if not isinstance(decision_id, str) or not decision_id or decision_id in rows:
            raise ValueError("audit decision IDs are missing or duplicated at row %d" % number)
        if "error" in value:
            raise ValueError("audit contains invalid row for decision %s" % decision_id)
        rows[decision_id] = value
    return rows, {
        "audit_checksum_manifest_sha256": file_sha256(checksum_path),
        "audit_rows_sha256": file_sha256(rows_path),
        "audit_report_sha256": file_sha256(root / "report.json"),
        "audit_sample_manifest_sha256": file_sha256(root / "sample_manifest.json"),
    }


def load_rule_prior_records(
    dataset_dir: str | Path,
    *,
    archetype: str,
    allowed_splits: Sequence[str],
) -> list[dict[str, Any]]:
    root = Path(dataset_dir)
    requested = set(str(value) for value in allowed_splits)
    if "blind" in requested:
        raise ValueError("blind split is not available to rule-prior blending")
    split = load_split_manifest(root / "split_manifest.json")
    allowed = {
        str(item["item_id"]): str(item["split"])
        for item in split["items"]
        if str(item["split"]) in requested and str(item.get("archetype")) == str(archetype)
    }
    return _load_allowed_records(root / "decision_records.jsonl", allowed)


def build_rule_prior_map(
    records: Iterable[Mapping[str, Any]],
    audit_rows: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    result = {}
    for record in records:
        decision_id = str(record.get("decision_id", ""))
        audit = audit_rows.get(decision_id)
        if audit is None:
            raise ValueError("audit is missing allowlisted decision %s" % decision_id)
        chosen = record.get("chosen_canonical_action")
        target = _one_selection_target(record)
        options = record.get("legal_semantic_options")
        if target is None or not isinstance(chosen, Mapping) or not isinstance(options, list):
            continue
        target_complete_id = _complete_action_id(chosen)
        if target_complete_id != audit.get("gold_semantic_id"):
            raise ValueError("audit Gold action does not match dataset decision %s" % decision_id)
        baseline_complete_id = str(audit.get("baseline_semantic_id"))
        mapped = []
        for option in options:
            if not isinstance(option, Mapping):
                raise ValueError("legal semantic option is not an object")
            if _complete_action_id(_single_action(option, chosen)) == baseline_complete_id:
                mapped.append(_semantic_id(option))
        mapped = sorted(set(mapped))
        if len(mapped) > 1:
            raise ValueError("baseline action maps to multiple semantic options")
        if bool(audit.get("semantic_equal")) and mapped != [_semantic_id(target)]:
            raise ValueError("equal baseline action failed one-step semantic mapping")
        result[decision_id] = {
            "baseline_correct": bool(audit.get("semantic_equal")),
            "rule_action_id": mapped[0] if mapped else None,
        }
    return result


def evaluate_blend(
    model: PromptRanker,
    examples: Iterable[PromptExample],
    rule_prior: Mapping[str, Mapping[str, Any]],
    *,
    alpha: float,
) -> dict[str, Any]:
    if alpha < 0:
        raise ValueError("rule alpha must be non-negative")
    groups: dict[str, list[dict[str, bool]]] = defaultdict(list)
    model.eval()
    with torch.no_grad():
        for item in examples:
            prior = rule_prior.get(item.decision_id)
            if prior is None:
                raise ValueError("missing rule prior for decision %s" % item.decision_id)
            scores = model.score(item.state, item.actions, item.style_id)
            model_choice = predict_action_id(scores, item.action_ids)
            rule_id = prior.get("rule_action_id")
            if rule_id in item.action_ids:
                adjusted = scores.clone()
                adjusted[item.action_ids.index(str(rule_id))] += float(alpha)
                blend_correct = predict_action_id(adjusted, item.action_ids) == item.target_id
                mapped = True
            else:
                # A multi-selection rule action cannot be represented by this
                # one-step ranker, so the safety policy executes the rule path.
                blend_correct = bool(prior["baseline_correct"])
                mapped = False
            row = {
                "baseline_correct": bool(prior["baseline_correct"]),
                "model_correct": model_choice == item.target_id,
                "blend_correct": blend_correct,
                "mapped": mapped,
            }
            for key in (
                "overall:overall",
                "split:" + item.split,
                "style:" + item.style_id,
                "action_type:" + item.action_type,
            ):
                groups[key].append(row)
    return {
        key: {
            "count": len(rows),
            "mapped_rule_prior": sum(row["mapped"] for row in rows),
            "baseline_top1_accuracy": sum(row["baseline_correct"] for row in rows) / len(rows),
            "model_top1_accuracy": sum(row["model_correct"] for row in rows) / len(rows),
            "blend_top1_accuracy": sum(row["blend_correct"] for row in rows) / len(rows),
        }
        for key, rows in sorted(groups.items())
    }


def select_alpha(
    model: PromptRanker,
    development: Sequence[PromptExample],
    rule_prior: Mapping[str, Mapping[str, Any]],
    grid: Sequence[float] = DEFAULT_ALPHA_GRID,
) -> tuple[float, list[dict[str, float]]]:
    if not development:
        raise ValueError("development examples are required to select rule alpha")
    values = sorted(set(float(value) for value in grid))
    if not values or values[0] < 0:
        raise ValueError("alpha grid must contain non-negative values")
    sweep = []
    for alpha in values:
        overall = evaluate_blend(model, development, rule_prior, alpha=alpha)["overall:overall"]
        sweep.append({
            "alpha": alpha,
            "blend_top1_accuracy": float(overall["blend_top1_accuracy"]),
            "baseline_top1_accuracy": float(overall["baseline_top1_accuracy"]),
            "model_top1_accuracy": float(overall["model_top1_accuracy"]),
        })
    selected = min(sweep, key=lambda row: (-row["blend_top1_accuracy"], row["alpha"]))
    return float(selected["alpha"]), sweep
