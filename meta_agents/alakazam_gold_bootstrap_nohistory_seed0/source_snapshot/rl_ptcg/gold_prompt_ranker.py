"""Leakage-safe variable-action behavior cloning for Gold prompt decisions.

This module is deliberately a dataset consumer, not a submitted game agent.
It only accepts the non-blind Phase 1 splits and only featurizes the actor's
safe observation, known private information, public history, and canonical
semantic legal options.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from hashlib import blake2b, sha256
import io
import json
from pathlib import Path
import random
import re
from typing import Any, Iterable, Mapping, Sequence

import torch
from torch import Tensor, nn

from .split_manifest import load_split_manifest


ALLOWED_SPLITS = frozenset(("train", "development", "policy_family_holdout"))
UNKNOWN_STYLE = "__unknown_style__"
LEGACY_FEATURE_SCHEMA_VERSION = "gold_prompt_ranker_features.v1"
FEATURE_SCHEMA_VERSION = "gold_prompt_ranker_features.v2"
SUPPORTED_FEATURE_SCHEMAS = frozenset((LEGACY_FEATURE_SCHEMA_VERSION, FEATURE_SCHEMA_VERSION))
FORBIDDEN_FEATURE_KEYS = frozenset((
    "index", "serial", "ordinal", "optionindex", "option_index", "rawoption",
    "raw_option", "raw", "exact_hidden_diagnostics", "terminal_result",
    "result", "future", "future_information", "hidden", "hidden_cards",
    "opponent_hand", "opponent_hands", "opponent_deck", "opponent_decks",
))


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _semantic_id(option: Mapping[str, Any]) -> str:
    return blake2b(_canonical(option).encode("ascii"), digest_size=32).hexdigest()


def _forbidden_key(key: Any) -> bool:
    name = str(key).lower()
    if name in FORBIDDEN_FEATURE_KEYS:
        return True
    return ("raw" in name or "serial" in name or "ordinal" in name or
            name.endswith("index") or name.endswith("_index") or
            ("opponent" in name and ("hand" in name or "deck" in name)) or
            "hidden" in name or "future" in name)


def reject_forbidden_feature_keys(value: Any, *, path: str = "feature") -> None:
    """Reject unsafe fields recursively before they can reach a feature hash."""
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = "%s.%s" % (path, key)
            if _forbidden_key(key):
                raise ValueError("forbidden feature key: %s" % child_path)
            reject_forbidden_feature_keys(child, path=child_path)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            reject_forbidden_feature_keys(child, path="%s[%d]" % (path, index))


def _tokens(value: Any, prefix: str) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key in sorted(value, key=str):
            yield from _tokens(value[key], "%s.%s" % (prefix, key))
    elif isinstance(value, (list, tuple)):
        # Public history, board slots, and actor-visible ordered zones are
        # strategic sequences. Raw legal-option order is never passed here;
        # actions are encoded independently and sorted by semantic ID.
        for index, child in enumerate(value):
            yield from _tokens(child, "%s[%d]" % (prefix, index))
    elif value is not None:
        yield "%s=%s" % (prefix, _canonical(value))


def _hashed_features(value: Any, prefix: str, dimension: int) -> Tensor:
    reject_forbidden_feature_keys(value, path=prefix)
    vector = torch.zeros(dimension, dtype=torch.float32)
    for token in _tokens(value, prefix):
        bucket = int.from_bytes(sha256(token.encode("ascii")).digest()[:8], "big") % dimension
        vector[bucket] += 1.0
    return vector


@dataclass(frozen=True)
class PromptExample:
    decision_id: str
    split: str
    style_id: str
    archetype: str
    state: Tensor
    actions: Tensor
    action_ids: tuple[str, ...]
    target_id: str
    action_type: str


@dataclass(frozen=True)
class RankerConfig:
    feature_dim: int = 256
    hidden_dim: int = 64
    style_dim: int = 8
    learning_rate: float = 0.01
    epochs: int = 8
    batch_size: int = 16
    use_style_embedding: bool = True
    include_known_private: bool = True
    include_public_history: bool = True


def _one_selection_target(record: Mapping[str, Any]) -> Mapping[str, Any] | None:
    action = record.get("chosen_canonical_action")
    if not isinstance(action, Mapping) or set(action) != {"selection_context", "minimum_count", "maximum_count", "selections"}:
        return None
    selections = action.get("selections")
    if not isinstance(selections, list) or len(selections) != 1 or not isinstance(selections[0], Mapping):
        return None
    return selections[0]


def _feature_sources(
    record: Mapping[str, Any], options: Sequence[Mapping[str, Any]], *,
    include_known_private: bool = True,
    include_public_history: bool = True,
) -> dict[str, Any]:
    safe = record.get("safe_observation", {})
    if not isinstance(safe, Mapping):
        raise ValueError("safe_observation must be an object")
    # The engine's in-progress result sentinel is present in every safe state.
    # It is deliberately omitted rather than used as a feature; terminal_result
    # is never admitted to this projection.
    safe_without_result = {key: value for key, value in safe.items() if str(key) != "result"}
    sources = {
        "safe_observation": safe_without_result,
        "legal_semantic_options": list(options),
    }
    if include_known_private:
        sources["known_private_info"] = record.get("known_private_info", {})
    if include_public_history:
        sources["public_history"] = record.get("public_history", {})
    reject_forbidden_feature_keys(sources)
    return sources


def build_examples(records: Iterable[Mapping[str, Any]], split_by_id: Mapping[str, str], *, archetype: str,
                   allowed_splits: Sequence[str] = ("train", "development", "policy_family_holdout"),
                   feature_dim: int = 256, include_known_private: bool = True,
                   include_public_history: bool = True) -> list[PromptExample]:
    requested = {str(split) for split in allowed_splits}
    if "blind" in requested or not requested.issubset(ALLOWED_SPLITS):
        raise ValueError("only explicitly allowed non-blind splits may be used")
    examples: list[PromptExample] = []
    for record in records:
        decision_id = str(record.get("decision_id", ""))
        split = split_by_id.get(decision_id)
        if split not in requested:
            continue
        if str(record.get("own_archetype")) != str(archetype):
            continue
        target = _one_selection_target(record)
        options = record.get("legal_semantic_options")
        if target is None or not isinstance(options, list) or not options or not all(isinstance(x, Mapping) for x in options):
            continue
        # Validate every permitted input before deriving any feature token.
        sources = _feature_sources(
            record,
            options,
            include_known_private=include_known_private,
            include_public_history=include_public_history,
        )
        target_id = _semantic_id(target)
        by_id: dict[str, Mapping[str, Any]] = {}
        for option in options:
            identifier = _semantic_id(option)
            previous = by_id.setdefault(identifier, option)
            if previous != option:
                raise ValueError("semantic action hash collision")
        if target_id not in by_id:
            continue
        ordered = sorted(by_id.items())
        action_ids = tuple(identifier for identifier, _option in ordered)
        state = _hashed_features({key: value for key, value in sources.items() if key != "legal_semantic_options"}, "state", feature_dim)
        actions = torch.stack([_hashed_features(option, "action", feature_dim) for _identifier, option in ordered])
        style = str(record.get("style_id") or UNKNOWN_STYLE)
        action_type_value = target.get("action_type")
        action_type = "unknown" if action_type_value is None else str(action_type_value)
        examples.append(PromptExample(decision_id, str(split), style, str(archetype), state, actions, action_ids, target_id, action_type))
    return examples


_DECISION_ID_PATTERN = re.compile(r'"decision_id":"([^"\\]+)"')


def _verify_dataset_bindings(root: Path) -> dict[str, str]:
    manifest_path = root / "dataset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    if not isinstance(manifest, Mapping) or manifest.get("schema_version") != "gold_replay_dataset.v1":
        raise ValueError("unsupported Phase 1 dataset manifest")
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    expected_self = sha256((json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ) + "\n").encode("ascii")).hexdigest()
    if manifest.get("manifest_sha256") != expected_self:
        raise ValueError("Phase 1 dataset manifest self-hash mismatch")
    outputs = manifest.get("output_sha256")
    if not isinstance(outputs, Mapping):
        raise ValueError("Phase 1 dataset manifest has no output bindings")
    records_path = root / "decision_records.jsonl"
    split_path = root / "split_manifest.json"
    records_hash = _sha256_file(records_path)
    split_hash = _sha256_file(split_path)
    if outputs.get("decision_records.jsonl") != records_hash or outputs.get("split_manifest.json") != split_hash:
        raise ValueError("Phase 1 dataset output hash mismatch")
    return {
        "dataset_manifest_file_sha256": _sha256_file(manifest_path),
        "dataset_manifest_sha256": str(manifest["manifest_sha256"]),
        "decision_records_sha256": records_hash,
        "split_manifest_sha256": split_hash,
    }


def _load_allowed_records(
    path: Path, allowed_ids: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Parse only allowlisted non-blind rows; blind payloads stay opaque."""
    records = []
    seen = set()
    with path.open(encoding="ascii") as handle:
        for line_number, line in enumerate(handle, 1):
            match = _DECISION_ID_PATTERN.search(line)
            if match is None:
                raise ValueError("decision record row %d has no plain decision_id" % line_number)
            decision_id = match.group(1)
            if decision_id not in allowed_ids:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError("invalid allowlisted decision row %d" % line_number) from error
            if record.get("decision_id") != decision_id or decision_id in seen:
                raise ValueError("allowlisted decision IDs are mismatched or duplicated")
            seen.add(decision_id)
            records.append(record)
    if seen != set(allowed_ids):
        raise ValueError("decision records do not contain every allowlisted item")
    return records


def load_phase1_examples(dataset_dir: str | Path, *, archetype: str, allowed_splits: Sequence[str],
                         feature_dim: int = 256, include_known_private: bool = True,
                         include_public_history: bool = True) -> tuple[list[PromptExample], dict[str, str]]:
    root = Path(dataset_dir)
    requested = {str(split) for split in allowed_splits}
    if "blind" in requested or not requested.issubset(ALLOWED_SPLITS):
        raise ValueError("blind split is never available to this ranker")
    manifest = load_split_manifest(root / "split_manifest.json")
    split_by_id = {str(item["item_id"]): str(item["split"]) for item in manifest["items"]}
    allowed_ids = {
        str(item["item_id"]): str(item["split"])
        for item in manifest["items"]
        if str(item["split"]) in requested and str(item.get("archetype")) == str(archetype)
    }
    records = _load_allowed_records(root / "decision_records.jsonl", allowed_ids)
    hashes = _verify_dataset_bindings(root)
    return build_examples(
        records,
        split_by_id,
        archetype=archetype,
        allowed_splits=allowed_splits,
        feature_dim=feature_dim,
        include_known_private=include_known_private,
        include_public_history=include_public_history,
    ), hashes


class PromptRanker(nn.Module):
    def __init__(self, config: RankerConfig, style_vocab: Mapping[str, int]) -> None:
        super().__init__()
        self.config = config
        self.style_vocab = dict(style_vocab)
        self.state_encoder = nn.Sequential(nn.Linear(config.feature_dim, config.hidden_dim), nn.ReLU())
        self.action_encoder = nn.Sequential(nn.Linear(config.feature_dim, config.hidden_dim), nn.ReLU())
        style_width = config.style_dim if config.use_style_embedding else 0
        self.style_embedding = nn.Embedding(max(self.style_vocab.values(), default=0) + 1, config.style_dim) if config.use_style_embedding else None
        self.scorer = nn.Sequential(nn.Linear(config.hidden_dim * 2 + style_width, config.hidden_dim), nn.ReLU(), nn.Linear(config.hidden_dim, 1))

    def style_index(self, style_id: str) -> int:
        return self.style_vocab.get(style_id, self.style_vocab[UNKNOWN_STYLE])

    def score(self, state: Tensor, actions: Tensor, style_id: str) -> Tensor:
        state_embedding = self.state_encoder(state.unsqueeze(0)).expand(actions.shape[0], -1)
        action_embedding = self.action_encoder(actions)
        parts = [state_embedding, action_embedding]
        if self.style_embedding is not None:
            style = torch.tensor([self.style_index(style_id)], dtype=torch.long, device=actions.device)
            parts.append(self.style_embedding(style).expand(actions.shape[0], -1))
        return self.scorer(torch.cat(parts, dim=1)).squeeze(1)


def _style_vocab(examples: Iterable[PromptExample]) -> dict[str, int]:
    return {style: index for index, style in enumerate([UNKNOWN_STYLE] + sorted({example.style_id for example in examples if example.style_id != UNKNOWN_STYLE}))}


def set_deterministic_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    deterministic = getattr(torch, "use_deterministic_algorithms", None)
    if deterministic is not None:
        deterministic(True)
    torch.set_num_threads(1)


def _loss(scores: Tensor, example: PromptExample) -> Tensor:
    positive = torch.tensor([action_id == example.target_id for action_id in example.action_ids], dtype=torch.bool)
    return torch.logsumexp(scores, 0) - torch.logsumexp(scores[positive], 0)


def predict_action_id(scores: Tensor, action_ids: Sequence[str]) -> str:
    if scores.ndim != 1 or len(scores) != len(action_ids) or not action_ids:
        raise ValueError("scores and semantic action IDs must be aligned and non-empty")
    values = [float(value) for value in scores.detach().cpu()]
    return min(zip(action_ids, values), key=lambda item: (-item[1], item[0]))[0]


def train_ranker(
    train_examples: Sequence[PromptExample],
    *,
    config: RankerConfig = RankerConfig(),
    seed: int = 0,
    fit_splits: Sequence[str] = ("train",),
) -> tuple[PromptRanker, list[float]]:
    if not train_examples:
        raise ValueError("no train examples after leakage-safe filtering")
    allowed = set(str(value) for value in fit_splits)
    if "blind" in allowed or not allowed or not allowed.issubset(ALLOWED_SPLITS):
        raise ValueError("fit_splits must be explicitly non-blind")
    if any(item.split not in allowed for item in train_examples):
        raise ValueError("fit examples include a split outside fit_splits")
    set_deterministic_seed(seed)
    model = PromptRanker(config, _style_vocab(train_examples)).cpu()
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    losses: list[float] = []
    order = list(range(len(train_examples)))
    for _ in range(config.epochs):
        random.Random(seed + _).shuffle(order)
        for start in range(0, len(order), config.batch_size):
            batch = [train_examples[index] for index in order[start:start + config.batch_size]]
            optimizer.zero_grad()
            loss = torch.stack([_loss(model.score(item.state, item.actions, item.style_id), item) for item in batch]).mean()
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
    return model, losses


def evaluate_ranker(model: PromptRanker, examples: Iterable[PromptExample]) -> dict[str, dict[str, float]]:
    groups: dict[str, list[tuple[bool, float]]] = defaultdict(list)
    model.eval()
    with torch.no_grad():
        for item in examples:
            scores = model.score(item.state, item.actions, item.style_id)
            predicted = predict_action_id(scores, item.action_ids)
            nll = float(_loss(scores, item))
            values = (("overall", "overall"), ("split", item.split), ("style", item.style_id), ("action_type", item.action_type))
            for kind, value in values:
                groups["%s:%s" % (kind, value)].append((predicted == item.target_id, nll))
    return {key: {"count": len(rows), "top1_accuracy": sum(row[0] for row in rows) / len(rows),
                  "nll": sum(row[1] for row in rows) / len(rows)} for key, rows in sorted(groups.items())}


def _write_once(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError("refusing to replace non-identical ranker artifact: %s" % path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def save_ranker(output_dir: str | Path, model: PromptRanker, *, config: RankerConfig, seed: int,
                counts: Mapping[str, int], source_hashes: Mapping[str, str],
                evaluation_report: Mapping[str, Any] | None = None,
                implementation_sources: Mapping[str, str | Path] | None = None) -> tuple[Path, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    checkpoint = root / "gold_prompt_ranker.pt"
    report_path = root / "evaluation_report.json"
    manifest_path = root / "gold_prompt_ranker_manifest.json"
    buffer = io.BytesIO()
    torch.save({"state_dict": model.state_dict(), "config": asdict(config), "style_vocab": model.style_vocab, "seed": seed}, buffer)
    _write_once(checkpoint, buffer.getvalue())
    report = dict(evaluation_report or {})
    report_bytes = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")
    _write_once(report_path, report_bytes)
    implementation = {}
    for relative, raw_path in sorted((implementation_sources or {}).items()):
        source = Path(raw_path)
        snapshot = root / "source_snapshot" / relative
        _write_once(snapshot, source.read_bytes())
        implementation[str(relative)] = {
            "source_sha256": _sha256_file(source),
            "snapshot": str(snapshot.relative_to(root)).replace("\\", "/"),
            "snapshot_sha256": _sha256_file(snapshot),
        }
    manifest = {"schema_version": "gold_prompt_ranker_manifest.v2", "checkpoint": checkpoint.name,
                "checkpoint_sha256": _sha256_file(checkpoint), "feature_schema": FEATURE_SCHEMA_VERSION,
                "config": asdict(config), "seed": seed, "counts": dict(sorted(counts.items())),
                "style_vocab": dict(sorted(model.style_vocab.items())),
                "source_hashes": dict(sorted(source_hashes.items())),
                "evaluation_report": report_path.name,
                "evaluation_report_sha256": _sha256_file(report_path),
                "implementation": implementation}
    manifest["manifest_sha256"] = sha256((json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ) + "\n").encode("ascii")).hexdigest()
    _write_once(
        manifest_path,
        (json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii"),
    )
    return checkpoint, manifest_path


def load_ranker(checkpoint_path: str | Path, manifest_path: str | Path) -> PromptRanker:
    checkpoint = Path(checkpoint_path)
    manifest_file = Path(manifest_path)
    manifest = json.loads(manifest_file.read_text(encoding="ascii"))
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    expected_self = sha256((json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ) + "\n").encode("ascii")).hexdigest()
    report = manifest_file.parent / str(manifest.get("evaluation_report"))
    if (
        manifest.get("schema_version") != "gold_prompt_ranker_manifest.v2"
        or manifest.get("manifest_sha256") != expected_self
        or manifest.get("checkpoint_sha256") != _sha256_file(checkpoint)
        or manifest.get("feature_schema") not in SUPPORTED_FEATURE_SCHEMAS
        or not report.is_file()
        or manifest.get("evaluation_report_sha256") != _sha256_file(report)
    ):
        raise ValueError("ranker checkpoint does not match its manifest")
    for relative, binding in manifest.get("implementation", {}).items():
        snapshot = manifest_file.parent / str(binding.get("snapshot"))
        if (
            not snapshot.is_file()
            or binding.get("snapshot_sha256") != _sha256_file(snapshot)
            or binding.get("source_sha256") != binding.get("snapshot_sha256")
        ):
            raise ValueError("ranker implementation snapshot mismatch: %s" % relative)
    try:
        payload = torch.load(checkpoint, map_location="cpu", weights_only=True)
    except TypeError:  # PyTorch before the weights_only argument.
        payload = torch.load(checkpoint, map_location="cpu")
    feature_schema = manifest.get("feature_schema")
    feature_fields = {"include_known_private", "include_public_history"}
    if feature_schema == LEGACY_FEATURE_SCHEMA_VERSION and feature_fields & set(payload.get("config", {})):
        raise ValueError("legacy feature schema contains v2 component flags")
    if feature_schema == FEATURE_SCHEMA_VERSION and not feature_fields <= set(payload.get("config", {})):
        raise ValueError("v2 feature schema is missing component flags")
    model = PromptRanker(RankerConfig(**payload["config"]), payload["style_vocab"])
    if (
        payload.get("config") != manifest.get("config")
        or payload.get("style_vocab") != manifest.get("style_vocab")
        or payload.get("seed") != manifest.get("seed")
    ):
        raise ValueError("ranker checkpoint payload disagrees with manifest")
    model.load_state_dict(payload["state_dict"])
    return model
