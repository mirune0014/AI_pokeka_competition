"""Fail-closed ingestion of stable Gold-oracle labels for prompt ranking.

The artifact intentionally contains only labels whose targets can be resolved
against the actor-view legal options in a verified, non-blind state corpus.
"""
from __future__ import annotations

from hashlib import blake2b, sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .gold_oracle_runner import verify_oracle_output
from .gold_oracle_states import (
    SCHEMA_VERSION as ORACLE_STATES_SCHEMA_VERSION,
    canonical_sha256,
    file_sha256,
    verify_gold_oracle_states,
    write_once,
)
from .gold_upper_tier_states import (
    SUPPORTED_SCHEMA_VERSIONS as UPPER_TIER_SCHEMA_VERSIONS,
    verify_gold_upper_tier_states,
)
from .gold_teacher_state_split import verify_teacher_state_split
from .kaggle_rollout_source_receipt import verify_kaggle_rollout_source_receipt


SCHEMA_VERSION = "gold_teacher_labels.v2"
ALLOWED_SPLITS = frozenset(("train", "development", "policy_family_holdout"))


def _json(value: Any, *, pretty: bool = False) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True,
                       indent=2 if pretty else None,
                       separators=None if pretty else (",", ":")) + "\n").encode("ascii")


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("could not read %s: %s" % (path, error)) from error
    if not isinstance(value, dict):
        raise ValueError("%s must contain a JSON object" % path)
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError("could not read %s: %s" % (path, error)) from error
    if not lines or any(not line for line in lines):
        raise ValueError("%s must be non-empty JSONL without blank rows" % path)
    result = []
    for number, line in enumerate(lines, 1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError("invalid JSONL row %d in %s" % (number, path)) from error
        if not isinstance(value, dict):
            raise ValueError("JSONL row %d is not an object" % number)
        result.append(value)
    return result


def _resolve(path: str | Path, workspace: Path) -> Path:
    value = Path(path)
    resolved = (value if value.is_absolute() else workspace / value).resolve()
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("path escapes workspace: %s" % path) from error
    return resolved


def _relative(path: Path, workspace: Path) -> str:
    try:
        relative = path.resolve().relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("path escapes workspace: %s" % path) from error
    value = str(relative).replace("\\", "/")
    return value or "."


def _semantic_id(option: Mapping[str, Any]) -> str:
    return blake2b(_json(option).rstrip(b"\n"), digest_size=32).hexdigest()


def _manifest_hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _verify_state_corpus(corpus: Path, workspace: Path) -> dict[str, Any]:
    schema = _read_object(corpus / "manifest.json").get("schema_version")
    if schema == ORACLE_STATES_SCHEMA_VERSION:
        return verify_gold_oracle_states(corpus, workspace)
    if schema in UPPER_TIER_SCHEMA_VERSIONS:
        return verify_gold_upper_tier_states(corpus, workspace)
    raise ValueError("unsupported teacher state corpus schema: %s" % schema)


def _target_deck(deck_path: Path | None) -> tuple[list[int] | None, dict[str, str] | None]:
    if deck_path is None:
        return None, None
    try:
        deck = [int(line.strip()) for line in deck_path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise ValueError("could not read target deck %s: %s" % (deck_path, error)) from error
    if len(deck) != 60:
        raise ValueError("target deck must contain exactly 60 integer card IDs")
    return deck, {"path": str(deck_path), "sha256": file_sha256(deck_path),
                  "canonical_sha256": canonical_sha256(deck)}


def _state_index(states: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    decisions = set()
    for state in states:
        state_id, decision_id = state.get("state_id"), state.get("decision_id")
        if not isinstance(state_id, str) or not state_id or not isinstance(decision_id, str) or not decision_id:
            raise ValueError("corpus state IDs and decision IDs must be non-empty strings")
        if state_id in indexed or decision_id in decisions:
            raise ValueError("corpus state IDs and decision IDs must join one-to-one")
        indexed[state_id] = state
        decisions.add(decision_id)
    return indexed


def _stable_labels(report: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    statistics = report.get("posterior_weighted_teacher_statistics")
    labels = statistics.get("stable_labels") if isinstance(statistics, Mapping) else None
    if not isinstance(labels, list):
        raise ValueError("oracle report has no stable_labels")
    if not labels:
        raise ValueError("oracle report stable_labels must be non-empty")
    return labels


def _require_target_actor_deck(state: Mapping[str, Any], target_deck: Sequence[int]) -> str:
    """Require an exact canonical deck binding when target-deck use is requested."""
    own = state.get("own_deck")
    if not isinstance(own, Mapping):
        raise ValueError("target deck requires a corpus actor deck mapping")
    deck, declared = own.get("decklist"), own.get("sha256")
    if (
        not isinstance(deck, list) or len(deck) != 60
        or not all(isinstance(card_id, int) and not isinstance(card_id, bool) for card_id in deck)
        or not isinstance(declared, str)
    ):
        raise ValueError("target deck requires a valid corpus actor deck binding")
    actual = canonical_sha256(deck)
    if declared != actual:
        raise ValueError("corpus actor deck canonical hash drift")
    if actual != canonical_sha256(list(target_deck)):
        raise ValueError("target deck/actor deck applicability drift")
    return actual


def _legal_target_for_oracle_action(state: Mapping[str, Any], action: str) -> tuple[Mapping[str, Any], str]:
    """Resolve an oracle candidate ID to its one-option actor-view target."""
    options = state.get("legal_semantic_options")
    if not isinstance(options, list) or not options or not all(isinstance(option, Mapping) for option in options):
        raise ValueError("state has no actor-view legal canonical options")
    candidates = state.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("state has no oracle candidate list")
    matches = [candidate for candidate in candidates if isinstance(candidate, Mapping) and candidate.get("semantic_id") == action]
    if len(matches) != 1 or not isinstance(matches[0].get("canonical"), Mapping):
        raise ValueError("stable label does not identify exactly one corpus canonical candidate")
    selections = matches[0]["canonical"].get("selections")
    if not isinstance(selections, list) or len(selections) != 1 or not isinstance(selections[0], Mapping):
        raise ValueError("stable label is not a one-option ranker target")
    target = selections[0]
    target_id = _semantic_id(target)
    legal = {_semantic_id(option): option for option in options}
    if target_id not in legal or legal[target_id] != target:
        raise ValueError("stable label target is not an actor-view legal action")
    return target, target_id


def _verify_source_receipt(receipt_path: Path, oracle: Path, run: Mapping[str, Any], report: Mapping[str, Any], workspace: Path) -> dict[str, Any]:
    receipt = verify_kaggle_rollout_source_receipt(receipt_path, workspace_root=workspace)
    if (
        Path(receipt["run_output"]).resolve() != oracle.resolve()
        or receipt.get("run_manifest_sha256") != run.get("manifest_sha256")
        or receipt.get("report_manifest_sha256") != report.get("manifest_sha256")
    ):
        raise ValueError("source receipt does not bind this oracle output")
    return receipt


def _teacher_split_mapping(path: Path, workspace: Path) -> tuple[dict[str, tuple[str, str]], str]:
    verified = verify_teacher_state_split(path, workspace)
    value = _read_object(path)
    items = value.get("items")
    if not isinstance(items, list):
        raise ValueError("teacher split has no items")
    mapping = {}
    for item in items:
        if not isinstance(item, Mapping):
            raise ValueError("teacher split item must be an object")
        decision_id, state_id, split = item.get("decision_id"), item.get("state_id"), item.get("split")
        if (
            not isinstance(decision_id, str) or not isinstance(state_id, str)
            or split not in ALLOWED_SPLITS or decision_id in mapping
        ):
            raise ValueError("teacher split items must map decisions one-to-one")
        mapping[decision_id] = (state_id, str(split))
    if len(mapping) != verified.get("states"):
        raise ValueError("teacher split verification count drift")
    return mapping, str(verified["manifest_sha256"])


def build_teacher_labels(
    corpus_dir: str | Path, oracle_dir: str | Path, output_dir: str | Path, *,
    workspace_root: str | Path | None = None, target_deck_path: str | Path | None = None,
    target_archetype: str | None = None, source_receipt_path: str | Path | None = None,
    source_workspace_root: str | Path | None = None,
    teacher_split_path: str | Path | None = None,
) -> dict[str, Any]:
    """Create a write-once teacher target artifact from a complete oracle run."""
    workspace = Path(workspace_root).resolve() if workspace_root else Path(__file__).resolve().parents[2]
    source_workspace = (
        workspace if source_workspace_root is None
        else _resolve(source_workspace_root, workspace)
    )
    corpus, oracle = (_resolve(value, source_workspace) for value in (corpus_dir, oracle_dir))
    output = _resolve(output_dir, workspace)
    target_path = None if target_deck_path is None else _resolve(target_deck_path, workspace)
    receipt_path = None if source_receipt_path is None else _resolve(source_receipt_path, workspace)
    split_path = None if teacher_split_path is None else _resolve(teacher_split_path, workspace)
    verified_oracle = verify_oracle_output(oracle, source_workspace)
    if not verified_oracle.get("complete"):
        raise ValueError("teacher labels require a complete oracle output")
    _verify_state_corpus(corpus, source_workspace)
    run = _read_object(oracle / "run_manifest.json")
    expected_corpus = run.get("corpus")
    actual_corpus = {
        "path": _relative(corpus, source_workspace),
        "selection_manifest_sha256": file_sha256(corpus / "selection_manifest.json"),
        "states_sha256": file_sha256(corpus / "states.jsonl"),
        "manifest_sha256": file_sha256(corpus / "manifest.json"),
    }
    if isinstance(expected_corpus, Mapping) and "schema_version" in expected_corpus:
        actual_corpus["schema_version"] = _read_object(corpus / "manifest.json").get("schema_version")
    if expected_corpus != actual_corpus:
        raise ValueError("oracle/corpus hash binding drift")
    report = _read_object(oracle / "report.json")
    if report.get("run_manifest_sha256") != run.get("manifest_sha256"):
        raise ValueError("oracle report/run manifest binding drift")
    if not verified_oracle.get("report_recomputed") and receipt_path is None:
        raise ValueError("teacher labels require a source receipt when local report recomputation drifts")
    receipt = None if receipt_path is None else _verify_source_receipt(receipt_path, oracle, run, report, workspace)
    split_mapping, split_manifest_sha256 = ({}, None)
    if split_path is not None:
        split_mapping, split_manifest_sha256 = _teacher_split_mapping(split_path, workspace)
    states = _state_index(_read_jsonl(corpus / "states.jsonl"))
    deck, deck_binding = _target_deck(target_path)
    if target_archetype is not None and not target_archetype:
        raise ValueError("target_archetype must be non-empty when supplied")
    labels = []
    seen_states: dict[str, str] = {}
    seen_decisions: dict[str, str] = {}
    for item in _stable_labels(report):
        if not isinstance(item, Mapping):
            raise ValueError("stable label must be an object")
        state_id, action = item.get("state_id"), item.get("action")
        if not isinstance(state_id, str) or not state_id or not isinstance(action, str) or not action:
            raise ValueError("stable label state_id and action must be non-empty strings")
        if state_id in seen_states:
            raise ValueError("duplicate or conflicting stable label for state_id: %s" % state_id)
        state = states.get(state_id)
        if state is None:
            raise ValueError("stable label references an unknown corpus state")
        decision_id, source_split = state.get("decision_id"), state.get("split")
        if not isinstance(decision_id, str) or decision_id in seen_decisions:
            raise ValueError("stable labels do not map one-to-one to decision IDs")
        if source_split not in ALLOWED_SPLITS:
            raise ValueError("stable label has blind or unknown source split: %s" % source_split)
        split = str(source_split)
        if split_path is not None:
            split_item = split_mapping.get(decision_id)
            if split_item is None or split_item[0] != state_id:
                raise ValueError("teacher split does not bind this state and decision")
            split = split_item[1]
        target, target_id = _legal_target_for_oracle_action(state, action)
        metadata = state.get("current_metadata")
        source_archetype = metadata.get("own_archetype") if isinstance(metadata, Mapping) else None
        own_deck = state.get("own_deck")
        source_deck_hash = own_deck.get("sha256") if isinstance(own_deck, Mapping) else None
        if target_archetype is not None and source_archetype != target_archetype:
            raise ValueError("target archetype/actor applicability drift")
        if deck is not None:
            source_deck_hash = _require_target_actor_deck(state, deck)
        labels.append({
            "state_id": state_id, "decision_id": decision_id, "split": split,
            "oracle_candidate_semantic_id": action,
            "target_semantic_id": target_id, "target_canonical_option": target,
            "source_actor_archetype": source_archetype, "source_actor_deck_sha256": source_deck_hash,
        })
        seen_states[state_id] = action
        seen_decisions[decision_id] = state_id
    labels.sort(key=lambda row: (row["decision_id"], row["state_id"]))
    labels_bytes = b"".join(_json(row) for row in labels)
    labels_path = output / "labels.jsonl"
    if labels_path.exists() and labels_path.read_bytes() != labels_bytes:
        raise FileExistsError("refusing to replace non-identical teacher labels: %s" % labels_path)
    output.mkdir(parents=True, exist_ok=True)
    if not labels_path.exists():
        labels_path.write_bytes(labels_bytes)
    inputs = {
        "corpus_manifest": {"path": _relative(corpus / "manifest.json", workspace), "sha256": file_sha256(corpus / "manifest.json")},
        "corpus_states": {"path": _relative(corpus / "states.jsonl", workspace), "sha256": file_sha256(corpus / "states.jsonl")},
        "oracle_run_manifest": {"path": _relative(oracle / "run_manifest.json", workspace), "sha256": file_sha256(oracle / "run_manifest.json")},
        "oracle_report": {"path": _relative(oracle / "report.json", workspace), "sha256": file_sha256(oracle / "report.json")},
    }
    if deck_binding is not None:
        deck_binding["path"] = _relative(target_path, workspace)
        inputs["target_deck"] = deck_binding
    if receipt_path is not None:
        inputs["source_receipt"] = {"path": _relative(receipt_path, workspace), "sha256": file_sha256(receipt_path),
                                    "manifest_sha256": receipt["manifest_sha256"]}
    if split_path is not None:
        inputs["teacher_split"] = {
            "path": _relative(split_path, workspace),
            "sha256": file_sha256(split_path),
            "manifest_sha256": split_manifest_sha256,
        }
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION, "inputs": inputs,
        "source_workspace_path": _relative(source_workspace, workspace),
        "oracle_run_manifest_sha256": run["manifest_sha256"],
        "oracle_report_manifest_sha256": report.get("manifest_sha256"),
        "labels_sha256": sha256(labels_bytes).hexdigest(),
        "target_archetype": target_archetype,
        "counts": {"labels": len(labels), "splits": {split: sum(row["split"] == split for row in labels) for split in sorted(ALLOWED_SPLITS)}},
    }
    manifest["manifest_sha256"] = _manifest_hash(manifest)
    write_once(output / "manifest.json", manifest)
    return verify_teacher_labels(output, workspace)


def verify_teacher_labels(output_dir: str | Path, workspace_root: str | Path | None = None) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve() if workspace_root else Path(__file__).resolve().parents[2]
    output = _resolve(output_dir, workspace)
    manifest = _read_object(output / "manifest.json")
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("manifest_sha256") != _manifest_hash(manifest):
        raise ValueError("teacher label manifest self-hash mismatch")
    inputs = manifest.get("inputs")
    source_workspace_path = manifest.get("source_workspace_path")
    if not isinstance(source_workspace_path, str) or not source_workspace_path:
        raise ValueError("teacher label manifest has no source workspace binding")
    source_workspace = _resolve(source_workspace_path, workspace)
    required_inputs = {"corpus_manifest", "corpus_states", "oracle_run_manifest", "oracle_report"}
    if not isinstance(inputs, Mapping) or not required_inputs <= set(inputs) or not set(inputs) <= required_inputs | {"target_deck", "source_receipt", "teacher_split"}:
        raise ValueError("invalid teacher label input bindings")
    resolved = {}
    for name, binding in inputs.items():
        if not isinstance(binding, Mapping) or not isinstance(binding.get("path"), str) or not isinstance(binding.get("sha256"), str):
            raise ValueError("invalid teacher label input binding: %s" % name)
        path = _resolve(binding["path"], workspace)
        if not path.is_file() or file_sha256(path) != binding["sha256"]:
            raise ValueError("teacher label input hash mismatch: %s" % name)
        resolved[name] = path
    if "target_deck" in inputs:
        binding = inputs["target_deck"]
        try:
            deck = [int(line.strip()) for line in resolved["target_deck"].read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        except (UnicodeDecodeError, ValueError) as error:
            raise ValueError("invalid target deck binding") from error
        if len(deck) != 60 or binding.get("canonical_sha256") != canonical_sha256(deck):
            raise ValueError("target deck canonical binding drift")
    corpus = resolved["corpus_states"].parent
    _relative(corpus, source_workspace)
    _verify_state_corpus(corpus, source_workspace)
    oracle = resolved["oracle_run_manifest"].parent
    _relative(oracle, source_workspace)
    verified_oracle = verify_oracle_output(oracle, source_workspace)
    if not verified_oracle.get("complete"):
        raise ValueError("teacher labels require complete oracle output")
    if resolved["oracle_report"] != oracle / "report.json":
        raise ValueError("teacher label oracle report path mismatch")
    run, report = _read_object(resolved["oracle_run_manifest"]), _read_object(resolved["oracle_report"])
    if run.get("manifest_sha256") != manifest.get("oracle_run_manifest_sha256") or report.get("manifest_sha256") != manifest.get("oracle_report_manifest_sha256"):
        raise ValueError("teacher label oracle manifest binding drift")
    receipt_binding = inputs.get("source_receipt")
    if not verified_oracle.get("report_recomputed") and receipt_binding is None:
        raise ValueError("teacher labels require a source receipt when local report recomputation drifts")
    if receipt_binding is not None:
        if set(receipt_binding) != {"path", "sha256", "manifest_sha256"}:
            raise ValueError("invalid source receipt binding")
        receipt = _verify_source_receipt(resolved["source_receipt"], oracle, run, report, workspace)
        if receipt["manifest_sha256"] != receipt_binding["manifest_sha256"]:
            raise ValueError("teacher label source receipt manifest drift")
    split_binding = inputs.get("teacher_split")
    split_mapping = {}
    if split_binding is not None:
        if set(split_binding) != {"path", "sha256", "manifest_sha256"}:
            raise ValueError("invalid teacher split binding")
        split_mapping, split_manifest_sha256 = _teacher_split_mapping(
            resolved["teacher_split"], workspace,
        )
        if split_manifest_sha256 != split_binding["manifest_sha256"]:
            raise ValueError("teacher label split manifest drift")
    expected_corpus = {
        "path": _relative(corpus, source_workspace),
        "selection_manifest_sha256": file_sha256(corpus / "selection_manifest.json"),
        "states_sha256": file_sha256(corpus / "states.jsonl"),
        "manifest_sha256": file_sha256(corpus / "manifest.json"),
    }
    oracle_corpus = run.get("corpus")
    if isinstance(oracle_corpus, Mapping) and "schema_version" in oracle_corpus:
        expected_corpus["schema_version"] = _read_object(corpus / "manifest.json").get("schema_version")
    if oracle_corpus != expected_corpus:
        raise ValueError("teacher label oracle/corpus hash binding drift")
    states = _state_index(_read_jsonl(corpus / "states.jsonl"))
    labels_path = output / "labels.jsonl"
    labels = _read_jsonl(labels_path)
    raw = labels_path.read_bytes()
    if manifest.get("labels_sha256") != sha256(raw).hexdigest():
        raise ValueError("teacher label rows hash mismatch")
    expected = {str(item.get("state_id")): str(item.get("action")) for item in _stable_labels(report)}
    if len(expected) != len(_stable_labels(report)):
        raise ValueError("oracle stable_labels contain duplicate or conflicting states")
    actual = {}
    decisions = set()
    overrides: dict[str, Mapping[str, Any]] = {}
    for row in labels:
        if not isinstance(row, Mapping):
            raise ValueError("teacher label row must be an object")
        state_id, decision_id, split = row.get("state_id"), row.get("decision_id"), row.get("split")
        target, target_id = row.get("target_canonical_option"), row.get("target_semantic_id")
        oracle_action = row.get("oracle_candidate_semantic_id")
        if not isinstance(state_id, str) or state_id in actual or not isinstance(decision_id, str) or decision_id in decisions:
            raise ValueError("teacher labels must map states one-to-one to decisions")
        state = states.get(state_id)
        if state is None or state.get("decision_id") != decision_id or split not in ALLOWED_SPLITS:
            raise ValueError("teacher label state/split binding mismatch")
        if split_binding is None:
            if state.get("split") != split:
                raise ValueError("teacher label source split binding mismatch")
        elif split_mapping.get(decision_id) != (state_id, split):
            raise ValueError("teacher label split does not bind this state and decision")
        metadata = state.get("current_metadata")
        source_archetype = metadata.get("own_archetype") if isinstance(metadata, Mapping) else None
        own_deck = state.get("own_deck")
        source_deck_hash = own_deck.get("sha256") if isinstance(own_deck, Mapping) else None
        if row.get("source_actor_archetype") != source_archetype or row.get("source_actor_deck_sha256") != source_deck_hash:
            raise ValueError("teacher label actor applicability binding drift")
        target_archetype = manifest.get("target_archetype")
        if target_archetype is not None and source_archetype != target_archetype:
            raise ValueError("target archetype/actor applicability drift")
        if "target_deck" in inputs:
            if _require_target_actor_deck(state, deck) != source_deck_hash:
                raise ValueError("teacher label actor deck applicability binding drift")
        if not isinstance(target, Mapping) or not isinstance(target_id, str) or not isinstance(oracle_action, str) or _semantic_id(target) != target_id:
            raise ValueError("teacher label target canonical binding mismatch")
        expected_target, expected_target_id = _legal_target_for_oracle_action(state, oracle_action)
        if expected_target != target or expected_target_id != target_id:
            raise ValueError("teacher label target is not actor-view legal")
        actual[state_id] = oracle_action
        decisions.add(decision_id)
        overrides[decision_id] = target
    if actual != expected:
        raise ValueError("teacher labels do not exactly consume oracle stable_labels")
    return {"labels": len(labels), "manifest_sha256": manifest["manifest_sha256"],
            "target_overrides": overrides, "output_dir": str(output)}


def load_teacher_target_overrides(output_dir: str | Path, workspace_root: str | Path | None = None) -> dict[str, Mapping[str, Any]]:
    """Return verified decision-ID keyed target overrides for ``build_examples``."""
    return dict(verify_teacher_labels(output_dir, workspace_root)["target_overrides"])
