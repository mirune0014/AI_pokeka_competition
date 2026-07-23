"""Variable-complete-action ranker trained from paired rollout advantages."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import random
from typing import Any, Iterable, Mapping, Sequence

import torch
from torch import Tensor, nn
import torch.nn.functional as F

from .gold_prompt_ranker import (
    ALLOWED_SPLITS,
    _hashed_features,
    _semantic_id,
    predict_action_id,
    reject_forbidden_feature_keys,
    set_deterministic_seed,
)
from .gold_teacher_advantages import verify_teacher_advantages
from .gold_upper_tier_states import verify_gold_upper_tier_states


FEATURE_SCHEMA_VERSION = "gold_advantage_ranker_features.v1"


@dataclass(frozen=True)
class AdvantageExample:
    state_id: str
    decision_id: str
    split: str
    source_deck_sha256: str
    opponent_archetype: str
    state: Tensor
    actions: Tensor
    action_ids: tuple[str, ...]
    baseline_id: str
    selected_id: str
    advantage_targets: Tensor
    lcb_targets: Tensor
    minimum_head_targets: Tensor
    standard_errors: Tensor
    rule_scores: Tensor


@dataclass(frozen=True)
class AdvantageRankerConfig:
    feature_dim: int = 512
    hidden_dim: int = 128
    learning_rate: float = 0.003
    epochs: int = 40
    batch_size: int = 8
    pairwise_weight: float = 1.0
    regression_weight: float = 1.0
    filtered_bc_weight: float = 0.10
    pairwise_margin: float = 0.025
    pairwise_temperature: float = 0.10
    include_known_private: bool = True
    include_public_history: bool = False
    include_belief: bool = True
    include_own_deck: bool = True


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric" % label)
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("%s must be finite" % label)
    return result


def _card_counts(values: Any, label: str) -> list[dict[str, int]]:
    if (
        not isinstance(values, list)
        or not all(isinstance(card_id, int) and not isinstance(card_id, bool) for card_id in values)
    ):
        raise ValueError("%s must be an integer card list" % label)
    return [
        {"card_id": int(card_id), "count": int(count)}
        for card_id, count in sorted(Counter(values).items())
    ]


def safe_belief_projection(value: Any) -> dict[str, Any]:
    """Keep posterior content while dropping catalog identity and provenance."""
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("belief must be an object")
    hypotheses = value.get("hypotheses", [])
    if not isinstance(hypotheses, list):
        raise ValueError("belief hypotheses must be a list")
    safe_hypotheses = []
    for hypothesis in hypotheses:
        if not isinstance(hypothesis, Mapping):
            raise ValueError("belief hypothesis must be an object")
        item = {
            "archetype": str(hypothesis.get("archetype", "")),
            "kind": str(hypothesis.get("kind", "")),
            "posterior_mass": _finite(hypothesis.get("posterior_mass"), "posterior_mass"),
            "card_counts": _card_counts(hypothesis.get("decklist"), "belief decklist"),
        }
        if "swap_count" in hypothesis:
            swap_count = hypothesis["swap_count"]
            if isinstance(swap_count, bool) or not isinstance(swap_count, int) or swap_count < 0:
                raise ValueError("belief swap_count must be a non-negative integer")
            item["swap_count"] = int(swap_count)
        safe_hypotheses.append(item)
    safe_hypotheses.sort(key=lambda item: json.dumps(
        item, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ))
    counts = value.get("counts", {})
    if not isinstance(counts, Mapping):
        raise ValueError("belief counts must be an object")
    safe_counts = {
        str(key): _finite(item, "belief count")
        for key, item in sorted(counts.items())
        if isinstance(item, (int, float)) and not isinstance(item, bool)
    }
    visible = value.get("visible_requirements", {})
    if not isinstance(visible, Mapping):
        raise ValueError("belief visible requirements must be an object")
    safe_visible = []
    for card_id, count in sorted(visible.items(), key=lambda item: int(item[0])):
        try:
            card = int(card_id)
        except (TypeError, ValueError) as error:
            raise ValueError("belief visible card ID must be numeric") from error
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("belief visible card count must be a non-negative integer")
        safe_visible.append({"card_id": card, "count": int(count)})
    result = {
        "archetype": str(value.get("archetype", "")),
        "entropy": _finite(value.get("entropy", 0.0), "belief entropy"),
        "top1_mass": _finite(value.get("top1_mass", 0.0), "belief top1_mass"),
        "unknown_mass": _finite(value.get("unknown_mass", 0.0), "belief unknown_mass"),
        "synthetic_status": str(value.get("synthetic_status", "")),
        "counts": safe_counts,
        "visible_requirements": safe_visible,
        "hypotheses": safe_hypotheses,
    }
    reject_forbidden_feature_keys(result, path="belief")
    return result


def _state_sources(record: Mapping[str, Any], config: AdvantageRankerConfig) -> dict[str, Any]:
    safe = record.get("safe_observation")
    if not isinstance(safe, Mapping):
        raise ValueError("safe_observation must be an object")
    sources: dict[str, Any] = {
        "safe_observation": {
            key: value for key, value in safe.items() if str(key) != "result"
        },
    }
    if config.include_known_private:
        sources["known_private_info"] = record.get("known_private_info", {})
    if config.include_public_history:
        sources["public_history"] = record.get("public_history", {})
    if config.include_belief:
        sources["belief"] = safe_belief_projection(record.get("belief"))
    if config.include_own_deck:
        own = record.get("own_deck")
        if not isinstance(own, Mapping):
            raise ValueError("own_deck must be an object")
        sources["own_deck_card_counts"] = _card_counts(
            own.get("decklist"), "own decklist",
        )
    metadata = record.get("current_metadata")
    if isinstance(metadata, Mapping):
        sources["matchup"] = {
            "own_archetype": str(metadata.get("own_archetype", "")),
            "opponent_archetype": str(metadata.get("opponent_archetype", "")),
        }
    reject_forbidden_feature_keys(sources)
    return sources


def _records_by_state(corpus: Path) -> dict[str, Mapping[str, Any]]:
    result = {}
    decisions = set()
    with (corpus / "states.jsonl").open(encoding="ascii") as handle:
        for line in handle:
            value = json.loads(line)
            state_id, decision_id = value.get("state_id"), value.get("decision_id")
            if (
                not isinstance(state_id, str)
                or not isinstance(decision_id, str)
                or state_id in result
                or decision_id in decisions
            ):
                raise ValueError("advantage corpus states are not one-to-one")
            result[state_id] = value
            decisions.add(decision_id)
    return result


def _candidate_map(record: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result = {}
    candidates = record.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("advantage corpus has no candidates")
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise ValueError("advantage candidate must be an object")
        semantic_id, canonical = candidate.get("semantic_id"), candidate.get("canonical")
        if (
            not isinstance(semantic_id, str)
            or not isinstance(canonical, Mapping)
            or _semantic_id(canonical) != semantic_id
            or semantic_id in result
        ):
            raise ValueError("advantage candidate semantic binding drift")
        result[semantic_id] = candidate
    return result


def build_advantage_examples(
    records_by_state: Mapping[str, Mapping[str, Any]],
    advantage_rows: Iterable[Mapping[str, Any]],
    *,
    allowed_splits: Sequence[str],
    config: AdvantageRankerConfig = AdvantageRankerConfig(),
) -> list[AdvantageExample]:
    requested = {str(split) for split in allowed_splits}
    if "blind" in requested or not requested or not requested.issubset(ALLOWED_SPLITS):
        raise ValueError("advantage examples require explicit non-blind splits")
    examples = []
    seen = set()
    for row in advantage_rows:
        if not isinstance(row, Mapping):
            raise ValueError("advantage row must be an object")
        state_id, decision_id, split = row.get("state_id"), row.get("decision_id"), row.get("split")
        if not isinstance(state_id, str) or not isinstance(decision_id, str) or state_id in seen:
            raise ValueError("advantage rows must map states one-to-one")
        seen.add(state_id)
        if split not in ALLOWED_SPLITS:
            raise ValueError("advantage row contains a blind or unknown split")
        if split not in requested:
            continue
        record = records_by_state.get(state_id)
        if record is None or record.get("decision_id") != decision_id:
            raise ValueError("advantage row/corpus decision binding drift")
        metadata = record.get("current_metadata")
        opponent = str(metadata.get("opponent_archetype", "")) if isinstance(metadata, Mapping) else ""
        own = record.get("own_deck")
        source_deck = own.get("sha256") if isinstance(own, Mapping) else None
        if not isinstance(source_deck, str) or row.get("source_actor_deck_sha256") != source_deck:
            raise ValueError("advantage row actor deck binding drift")
        if isinstance(metadata, Mapping) and row.get("source_actor_archetype") != metadata.get("own_archetype"):
            raise ValueError("advantage row actor archetype binding drift")
        action_rows = row.get("actions")
        if not isinstance(action_rows, list) or not action_rows:
            raise ValueError("advantage row has no action targets")
        corpus_candidates = _candidate_map(record)
        by_id = {}
        for item in action_rows:
            if not isinstance(item, Mapping) or not isinstance(item.get("semantic_id"), str):
                raise ValueError("advantage action target is invalid")
            action_id = str(item["semantic_id"])
            if action_id in by_id or action_id not in corpus_candidates:
                raise ValueError("advantage action target is duplicated or absent from corpus")
            if item.get("canonical_complete_action") != corpus_candidates[action_id]["canonical"]:
                raise ValueError("advantage complete action binding drift")
            by_id[action_id] = item
        baseline, selected = row.get("baseline_action"), row.get("selected_teacher_action")
        if baseline not in by_id or selected not in by_id or baseline == selected:
            raise ValueError("advantage baseline/teacher action binding drift")
        ordered = sorted(by_id.items())
        action_ids = tuple(action_id for action_id, _item in ordered)
        state_vector = _hashed_features(
            _state_sources(record, config), "state", config.feature_dim,
        )
        action_vectors = torch.stack([
            _hashed_features(item["canonical_complete_action"], "complete_action", config.feature_dim)
            for _action_id, item in ordered
        ])
        advantages = torch.tensor([
            _finite(item.get("mean_advantage_win_probability"), "mean advantage")
            for _action_id, item in ordered
        ], dtype=torch.float32)
        lcbs = torch.tensor([
            _finite(item.get("minimum_batch_lcb90_win_probability"), "minimum LCB")
            for _action_id, item in ordered
        ], dtype=torch.float32)
        heads = torch.tensor([
            _finite(item.get("minimum_opponent_head_advantage_win_probability"), "minimum head advantage")
            for _action_id, item in ordered
        ], dtype=torch.float32)
        errors = []
        for _action_id, item in ordered:
            batches = item.get("batches")
            if not isinstance(batches, list) or not batches:
                raise ValueError("advantage action has no batch uncertainty")
            errors.append(math.sqrt(sum(
                _finite(batch.get("cluster_standard_error_win_probability"), "standard error") ** 2
                for batch in batches
            ) / len(batches)))
        rule_scores = torch.tensor([
            _finite(item.get("additive_rule_score"), "rule score")
            for _action_id, item in ordered
        ], dtype=torch.float32)
        examples.append(AdvantageExample(
            state_id=state_id,
            decision_id=decision_id,
            split=str(split),
            source_deck_sha256=source_deck,
            opponent_archetype=opponent,
            state=state_vector,
            actions=action_vectors,
            action_ids=action_ids,
            baseline_id=str(baseline),
            selected_id=str(selected),
            advantage_targets=advantages,
            lcb_targets=lcbs,
            minimum_head_targets=heads,
            standard_errors=torch.tensor(errors, dtype=torch.float32),
            rule_scores=rule_scores,
        ))
    return examples


def load_advantage_examples(
    corpus_dir: str | Path,
    advantage_dir: str | Path,
    *,
    workspace_root: str | Path,
    allowed_splits: Sequence[str],
    config: AdvantageRankerConfig = AdvantageRankerConfig(),
) -> tuple[list[AdvantageExample], dict[str, str]]:
    workspace = Path(workspace_root).resolve()
    corpus = Path(corpus_dir)
    corpus = (corpus if corpus.is_absolute() else workspace / corpus).resolve()
    advantage = Path(advantage_dir)
    advantage = (advantage if advantage.is_absolute() else workspace / advantage).resolve()
    for path in (corpus, advantage):
        try:
            path.relative_to(workspace)
        except ValueError as error:
            raise ValueError("advantage ranker input escapes workspace") from error
    verify_gold_upper_tier_states(corpus, workspace)
    verified = verify_teacher_advantages(advantage, workspace)
    manifest = json.loads((advantage / "manifest.json").read_text(encoding="ascii"))
    corpus_binding = manifest["inputs"]["corpus_states"]
    manifest_binding = manifest["inputs"]["corpus_manifest"]
    if (
        sha256((corpus / "states.jsonl").read_bytes()).hexdigest() != corpus_binding["sha256"]
        or sha256((corpus / "manifest.json").read_bytes()).hexdigest() != manifest_binding["sha256"]
    ):
        raise ValueError("advantage artifact is bound to different corpus content")
    rows = []
    with (advantage / "advantages.jsonl").open(encoding="ascii") as handle:
        for line in handle:
            rows.append(json.loads(line))
    examples = build_advantage_examples(
        _records_by_state(corpus), rows, allowed_splits=allowed_splits, config=config,
    )
    hashes = {
        "advantage_manifest_sha256": str(verified["manifest_sha256"]),
        "advantage_manifest_file_sha256": sha256((advantage / "manifest.json").read_bytes()).hexdigest(),
        "advantage_rows_sha256": sha256((advantage / "advantages.jsonl").read_bytes()).hexdigest(),
        "corpus_manifest_file_sha256": sha256((corpus / "manifest.json").read_bytes()).hexdigest(),
        "corpus_states_sha256": sha256((corpus / "states.jsonl").read_bytes()).hexdigest(),
        "feature_schema": FEATURE_SCHEMA_VERSION,
    }
    return examples, hashes


class AdvantageRanker(nn.Module):
    def __init__(self, config: AdvantageRankerConfig) -> None:
        super().__init__()
        self.config = config
        self.state_encoder = nn.Sequential(
            nn.Linear(config.feature_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, config.hidden_dim),
            nn.ReLU(),
        )
        self.action_encoder = nn.Sequential(
            nn.Linear(config.feature_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, config.hidden_dim),
            nn.ReLU(),
        )
        self.scorer = nn.Sequential(
            nn.Linear(config.hidden_dim * 3, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, 1),
        )

    def score(self, state: Tensor, actions: Tensor) -> Tensor:
        state_embedding = self.state_encoder(state.unsqueeze(0)).expand(actions.shape[0], -1)
        action_embedding = self.action_encoder(actions)
        interaction = state_embedding * action_embedding
        return self.scorer(torch.cat((state_embedding, action_embedding, interaction), dim=1)).squeeze(1)


def advantage_loss(
    scores: Tensor,
    example: AdvantageExample,
    config: AdvantageRankerConfig,
) -> tuple[Tensor, dict[str, Tensor]]:
    if scores.ndim != 1 or scores.shape != example.advantage_targets.shape:
        raise ValueError("ranker scores and advantage targets are not aligned")
    regression = F.smooth_l1_loss(scores, example.advantage_targets)
    target_delta = example.advantage_targets.unsqueeze(1) - example.advantage_targets.unsqueeze(0)
    score_delta = scores.unsqueeze(1) - scores.unsqueeze(0)
    pair_mask = target_delta > config.pairwise_margin
    if pair_mask.any():
        pair_weights = torch.clamp(target_delta[pair_mask] / 0.25, max=1.0)
        pairwise = (
            F.softplus(-score_delta[pair_mask] / config.pairwise_temperature) * pair_weights
        ).sum() / pair_weights.sum()
    else:
        pairwise = scores.sum() * 0.0
    selected_index = example.action_ids.index(example.selected_id)
    filtered_bc = torch.logsumexp(scores, 0) - scores[selected_index]
    total = (
        config.regression_weight * regression
        + config.pairwise_weight * pairwise
        + config.filtered_bc_weight * filtered_bc
    )
    return total, {
        "regression": regression,
        "pairwise": pairwise,
        "filtered_bc": filtered_bc,
    }


def train_advantage_ranker(
    examples: Sequence[AdvantageExample],
    *,
    config: AdvantageRankerConfig = AdvantageRankerConfig(),
    seed: int = 0,
    fit_splits: Sequence[str] = ("train",),
) -> tuple[AdvantageRanker, list[dict[str, float]]]:
    if not examples:
        raise ValueError("no advantage examples after leakage-safe filtering")
    allowed = {str(split) for split in fit_splits}
    if "blind" in allowed or not allowed or not allowed.issubset(ALLOWED_SPLITS):
        raise ValueError("fit_splits must be explicitly non-blind")
    if any(example.split not in allowed for example in examples):
        raise ValueError("fit examples include a split outside fit_splits")
    set_deterministic_seed(seed)
    model = AdvantageRanker(config).cpu()
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    history = []
    order = list(range(len(examples)))
    for epoch in range(config.epochs):
        random.Random(seed + epoch).shuffle(order)
        for start in range(0, len(order), config.batch_size):
            batch = [examples[index] for index in order[start:start + config.batch_size]]
            optimizer.zero_grad()
            parts = [advantage_loss(model.score(item.state, item.actions), item, config) for item in batch]
            loss = torch.stack([item[0] for item in parts]).mean()
            loss.backward()
            optimizer.step()
            history.append({
                "total": float(loss.detach()),
                **{
                    name: sum(float(item[1][name].detach()) for item in parts) / len(parts)
                    for name in ("regression", "pairwise", "filtered_bc")
                },
            })
    return model, history


def evaluate_advantage_ranker(
    model: AdvantageRanker,
    examples: Iterable[AdvantageExample],
) -> dict[str, dict[str, float]]:
    groups: dict[str, list[dict[str, float]]] = defaultdict(list)
    model.eval()
    with torch.no_grad():
        for example in examples:
            scores = model.score(example.state, example.actions)
            predicted = predict_action_id(scores, example.action_ids)
            target = predict_action_id(example.advantage_targets, example.action_ids)
            selected_index = example.action_ids.index(example.selected_id)
            baseline_index = example.action_ids.index(example.baseline_id)
            comparable = 0
            correct = 0
            for left in range(len(example.action_ids)):
                for right in range(left + 1, len(example.action_ids)):
                    delta = float(example.advantage_targets[left] - example.advantage_targets[right])
                    if abs(delta) <= model.config.pairwise_margin:
                        continue
                    comparable += 1
                    predicted_delta = float(scores[left] - scores[right])
                    correct += (predicted_delta > 0) == (delta > 0)
            row = {
                "top1": float(predicted == target),
                "selected_top1": float(predicted == example.selected_id),
                "mae": float(torch.mean(torch.abs(scores - example.advantage_targets))),
                "pairwise_correct": float(correct),
                "pairwise_total": float(comparable),
                "predicted_selected_advantage": float(scores[selected_index] - scores[baseline_index]),
                "true_selected_advantage": float(example.advantage_targets[selected_index]),
            }
            for key in (
                "overall:overall",
                "split:%s" % example.split,
                "opponent:%s" % example.opponent_archetype,
                "deck:%s" % example.source_deck_sha256,
            ):
                groups[key].append(row)
    result = {}
    for key, rows in sorted(groups.items()):
        pair_total = sum(row["pairwise_total"] for row in rows)
        result[key] = {
            "count": float(len(rows)),
            "top1_accuracy": sum(row["top1"] for row in rows) / len(rows),
            "selected_top1_accuracy": sum(row["selected_top1"] for row in rows) / len(rows),
            "mae": sum(row["mae"] for row in rows) / len(rows),
            "pairwise_accuracy": (
                sum(row["pairwise_correct"] for row in rows) / pair_total
                if pair_total else 0.0
            ),
            "mean_predicted_selected_advantage": sum(
                row["predicted_selected_advantage"] for row in rows
            ) / len(rows),
            "mean_true_selected_advantage": sum(
                row["true_selected_advantage"] for row in rows
            ) / len(rows),
        }
    return result
