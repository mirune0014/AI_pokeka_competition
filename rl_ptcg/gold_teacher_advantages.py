"""Split-bound paired-advantage targets for complete semantic actions.

The hard-label artifact intentionally keeps only exceptionally stable actions.
This companion artifact preserves the full paired action surface for those
states so a downstream model can use pairwise ranking and advantage regression
without treating a replay winner as an unconditional label.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .gold_oracle_runner import verify_oracle_output
from .gold_teacher_labels import (
    ALLOWED_SPLITS,
    _read_jsonl,
    _read_object,
    _relative,
    _require_target_actor_deck,
    _resolve,
    _semantic_id,
    _state_index,
    _target_deck,
    _teacher_split_mapping,
    _verify_source_receipt,
    _verify_state_corpus,
)
from .gold_teacher_refinement_selection import verify_refinement_selection


SCHEMA_VERSION = "gold_teacher_advantages.v1"


def _json(value: Any, *, pretty: bool = False) -> bytes:
    return (json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=True,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    ) + "\n").encode("ascii")


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write_bytes_once(path: Path, data: bytes) -> None:
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError("refusing to replace non-identical teacher advantage artifact: %s" % path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _manifest_hash(value: Mapping[str, Any]) -> str:
    unsigned = {key: item for key, item in value.items() if key != "manifest_sha256"}
    return sha256(_json(unsigned)).hexdigest()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric" % label)
    result = float(value)
    if result != result or result in {float("inf"), float("-inf")}:
        raise ValueError("%s must be finite" % label)
    return result


def _candidate_index(state: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    candidates = state.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("teacher advantage state has no complete candidates")
    indexed: dict[str, Mapping[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise ValueError("teacher advantage candidate must be an object")
        semantic_id, canonical = candidate.get("semantic_id"), candidate.get("canonical")
        if (
            not isinstance(semantic_id, str)
            or not isinstance(canonical, Mapping)
            or _semantic_id(canonical) != semantic_id
            or semantic_id in indexed
        ):
            raise ValueError("complete candidate semantic binding drift")
        indexed[semantic_id] = candidate
    return indexed


def _selected_states(selection: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    states = selection.get("states")
    next_run = selection.get("next_run")
    selected_ids = next_run.get("state_ids") if isinstance(next_run, Mapping) else None
    if (
        not isinstance(states, list)
        or not isinstance(selected_ids, list)
        or not selected_ids
        or len(selected_ids) != len(set(selected_ids))
    ):
        raise ValueError("refinement selection has no unique selected states")
    by_id = {}
    for row in states:
        if not isinstance(row, Mapping) or not isinstance(row.get("state_id"), str):
            raise ValueError("refinement selection state is invalid")
        state_id = str(row["state_id"])
        if state_id in by_id:
            raise ValueError("refinement selection contains duplicate states")
        by_id[state_id] = row
    selected = {}
    for state_id in selected_ids:
        row = by_id.get(str(state_id))
        if row is None or row.get("selected") is not True:
            raise ValueError("refinement next run includes an unselected state")
        best = row.get("best_nonbaseline")
        if not isinstance(best, Mapping) or not isinstance(best.get("action"), str):
            raise ValueError("selected refinement state has no teacher action")
        selected[str(state_id)] = row
    if {state_id for state_id, row in by_id.items() if row.get("selected") is True} != set(selected):
        raise ValueError("refinement selected flags disagree with next run")
    return selected


def _aggregate_state(
    state: Mapping[str, Any],
    units: Sequence[Mapping[str, Any]],
    selection: Mapping[str, Any],
    *,
    split: str,
) -> dict[str, Any]:
    if split not in ALLOWED_SPLITS:
        raise ValueError("teacher advantage state has blind or unknown split")
    if not units:
        raise ValueError("teacher advantage state has no rollout units")
    ordered = sorted(units, key=lambda item: int(item.get("batch_id", -1)))
    batch_ids = [int(unit.get("batch_id", -1)) for unit in ordered]
    if batch_ids != sorted(set(batch_ids)):
        raise ValueError("teacher advantage batches are duplicated or unordered")
    baseline = str(ordered[0].get("baseline_action", ""))
    action_ids = set(ordered[0].get("actions", {}))
    candidates = _candidate_index(state)
    expected = set(state.get("candidate_sets", {}).get("rule_diverse", []))
    if not baseline or baseline not in action_ids or action_ids != expected:
        raise ValueError("teacher advantage candidate set does not match rule_diverse")
    if not action_ids <= set(candidates):
        raise ValueError("teacher advantage rollout action is absent from corpus candidates")
    for unit in ordered:
        if (
            str(unit.get("state_id")) != str(state.get("state_id"))
            or str(unit.get("decision_id")) != str(state.get("decision_id"))
            or str(unit.get("baseline_action")) != baseline
            or set(unit.get("actions", {})) != action_ids
        ):
            raise ValueError("teacher advantage unit/state binding drift")
    selected = selection.get("best_nonbaseline")
    teacher_action = str(selected.get("action", "")) if isinstance(selected, Mapping) else ""
    if not teacher_action or teacher_action == baseline or teacher_action not in action_ids:
        raise ValueError("teacher advantage selection is not a legal non-baseline action")
    if sum(str(unit.get("oracle_action")) == teacher_action for unit in ordered) != int(selected.get("top_count", -1)):
        raise ValueError("teacher advantage top-count drift")

    actions = []
    for action_id in sorted(action_ids):
        corpus_candidate = candidates[action_id]
        values = []
        for unit in ordered:
            value = unit["actions"][action_id]
            if not isinstance(value, Mapping):
                raise ValueError("teacher advantage action statistic must be an object")
            heads = value.get("opponent_group_advantages_utility")
            if not isinstance(heads, Mapping) or not heads:
                raise ValueError("teacher advantage action has no opponent-head statistics")
            values.append({
                "batch_id": int(unit["batch_id"]),
                "advantage_win_probability": _number(
                    value.get("advantage_win_probability"), "advantage_win_probability",
                ),
                "one_sided_lcb90_win_probability": _number(
                    value.get("one_sided_lcb90_win_probability"),
                    "one_sided_lcb90_win_probability",
                ),
                "cluster_standard_error_win_probability": _number(
                    value.get("cluster_standard_error_utility"),
                    "cluster_standard_error_utility",
                ) / 2.0,
                "probability_advantage_positive": _number(
                    value.get("probability_advantage_positive"),
                    "probability_advantage_positive",
                ),
                "opponent_head_advantage_win_probability": {
                    str(key): _number(head, "opponent head advantage") / 2.0
                    for key, head in sorted(heads.items())
                },
            })
        advantages = [item["advantage_win_probability"] for item in values]
        lcbs = [item["one_sided_lcb90_win_probability"] for item in values]
        head_advantages = [
            head
            for item in values
            for head in item["opponent_head_advantage_win_probability"].values()
        ]
        source_tags = corpus_candidate.get("source_tags")
        if not isinstance(source_tags, list) or not all(isinstance(tag, str) for tag in source_tags):
            raise ValueError("complete candidate source tags are invalid")
        actions.append({
            "semantic_id": action_id,
            "canonical_complete_action": corpus_candidate["canonical"],
            "source_tags": sorted(set(source_tags)),
            "additive_rule_score": _number(
                corpus_candidate.get("additive_rule_score"), "additive_rule_score",
            ),
            "is_baseline": action_id == baseline,
            "is_selected_teacher_action": action_id == teacher_action,
            "top1_batch_count": sum(str(unit.get("oracle_action")) == action_id for unit in ordered),
            "mean_advantage_win_probability": sum(advantages) / len(advantages),
            "minimum_batch_advantage_win_probability": min(advantages),
            "minimum_batch_lcb90_win_probability": min(lcbs),
            "minimum_opponent_head_advantage_win_probability": min(head_advantages),
            "batches": values,
        })
    metadata = state.get("current_metadata")
    own_deck = state.get("own_deck")
    return {
        "state_id": str(state["state_id"]),
        "decision_id": str(state["decision_id"]),
        "episode_id": str(state.get("episode_id", "")),
        "split": split,
        "source_actor_archetype": (
            metadata.get("own_archetype") if isinstance(metadata, Mapping) else None
        ),
        "source_actor_deck_sha256": (
            own_deck.get("sha256") if isinstance(own_deck, Mapping) else None
        ),
        "baseline_action": baseline,
        "selected_teacher_action": teacher_action,
        "batch_ids": batch_ids,
        "selection_evidence": dict(selected),
        "actions": actions,
    }


def _build_artifact(
    *,
    corpus: Path,
    oracle: Path,
    selection_path: Path,
    split_path: Path,
    receipt_path: Path,
    source_workspace: Path,
    workspace: Path,
    target_archetype: str | None,
    target_deck_path: Path | None,
) -> tuple[bytes, dict[str, Any]]:
    verified_oracle = verify_oracle_output(oracle, source_workspace)
    if not verified_oracle.get("complete"):
        raise ValueError("teacher advantages require a complete oracle output")
    _verify_state_corpus(corpus, source_workspace)
    run = _read_object(oracle / "run_manifest.json")
    report = _read_object(oracle / "report.json")
    receipt = _verify_source_receipt(receipt_path, oracle, run, report, workspace)
    verify_refinement_selection(selection_path, workspace)
    selection = _read_object(selection_path)
    selection_source = selection.get("source")
    if not isinstance(selection_source, Mapping):
        raise ValueError("refinement selection has no source binding")
    selection_workspace = _resolve(str(selection_source.get("workspace_path")), workspace)
    selection_run = _resolve(str(selection_source.get("run_path")), selection_workspace)
    if (
        selection_workspace != source_workspace
        or selection_run != oracle
        or selection_source.get("run_manifest_sha256") != run.get("manifest_sha256")
        or selection_source.get("report_manifest_sha256") != report.get("manifest_sha256")
    ):
        raise ValueError("refinement selection does not bind the oracle source")
    selected = _selected_states(selection)
    split_mapping, split_manifest_sha256 = _teacher_split_mapping(split_path, workspace)
    states = _state_index(_read_jsonl(corpus / "states.jsonl"))
    units = report.get("posterior_weighted_teacher_statistics", {}).get("per_state_batch")
    if not isinstance(units, list):
        raise ValueError("oracle report has no per-state batch statistics")
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for unit in units:
        if not isinstance(unit, Mapping) or not isinstance(unit.get("state_id"), str):
            raise ValueError("oracle report contains an invalid per-state unit")
        grouped[str(unit["state_id"])].append(unit)
    selection_rows = selection.get("states")
    all_selection_state_ids = {
        str(item.get("state_id"))
        for item in selection_rows
        if isinstance(item, Mapping) and isinstance(item.get("state_id"), str)
    } if isinstance(selection_rows, list) else set()
    if set(grouped) != all_selection_state_ids or not set(selected) <= set(grouped):
        raise ValueError("oracle states do not exactly match refinement source states")
    deck, deck_binding = _target_deck(target_deck_path)
    rows = []
    for state_id in sorted(selected):
        state = states.get(state_id)
        if state is None:
            raise ValueError("refinement selection references an unknown corpus state")
        decision_id = state.get("decision_id")
        split_item = split_mapping.get(str(decision_id))
        if split_item is None or split_item[0] != state_id:
            raise ValueError("teacher split does not bind selected state and decision")
        metadata = state.get("current_metadata")
        source_archetype = metadata.get("own_archetype") if isinstance(metadata, Mapping) else None
        if target_archetype is not None and source_archetype != target_archetype:
            raise ValueError("target archetype/actor applicability drift")
        if deck is not None:
            _require_target_actor_deck(state, deck)
        rows.append(_aggregate_state(
            state, grouped[state_id], selected[state_id], split=split_item[1],
        ))
    rows_bytes = b"".join(_json(row) for row in rows)
    inputs: dict[str, Any] = {
        "corpus_manifest": {
            "path": _relative(corpus / "manifest.json", workspace),
            "sha256": _file_sha256(corpus / "manifest.json"),
        },
        "corpus_states": {
            "path": _relative(corpus / "states.jsonl", workspace),
            "sha256": _file_sha256(corpus / "states.jsonl"),
        },
        "oracle_run_manifest": {
            "path": _relative(oracle / "run_manifest.json", workspace),
            "sha256": _file_sha256(oracle / "run_manifest.json"),
        },
        "oracle_report": {
            "path": _relative(oracle / "report.json", workspace),
            "sha256": _file_sha256(oracle / "report.json"),
        },
        "refinement_selection": {
            "path": _relative(selection_path, workspace),
            "sha256": _file_sha256(selection_path),
            "manifest_sha256": selection["manifest_sha256"],
        },
        "source_receipt": {
            "path": _relative(receipt_path, workspace),
            "sha256": _file_sha256(receipt_path),
            "manifest_sha256": receipt["manifest_sha256"],
        },
        "teacher_split": {
            "path": _relative(split_path, workspace),
            "sha256": _file_sha256(split_path),
            "manifest_sha256": split_manifest_sha256,
        },
    }
    if deck_binding is not None:
        inputs["target_deck"] = {
            **deck_binding,
            "path": _relative(target_deck_path, workspace),
        }
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "inputs": inputs,
        "source_workspace_path": _relative(source_workspace, workspace),
        "oracle_run_manifest_sha256": run["manifest_sha256"],
        "oracle_report_manifest_sha256": report["manifest_sha256"],
        "target_archetype": target_archetype,
        "rows_sha256": sha256(rows_bytes).hexdigest(),
        "counts": {
            "states": len(rows),
            "actions": sum(len(row["actions"]) for row in rows),
            "splits": {
                split: sum(row["split"] == split for row in rows)
                for split in sorted(ALLOWED_SPLITS)
            },
        },
    }
    manifest["manifest_sha256"] = _manifest_hash(manifest)
    return rows_bytes, manifest


def build_teacher_advantages(
    corpus_dir: str | Path,
    oracle_dir: str | Path,
    refinement_selection_path: str | Path,
    teacher_split_path: str | Path,
    source_receipt_path: str | Path,
    output_dir: str | Path,
    *,
    workspace_root: str | Path | None = None,
    source_workspace_root: str | Path | None = None,
    target_archetype: str | None = None,
    target_deck_path: str | Path | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve() if workspace_root else Path(__file__).resolve().parents[1]
    source_workspace = workspace if source_workspace_root is None else _resolve(source_workspace_root, workspace)
    corpus = _resolve(corpus_dir, source_workspace)
    oracle = _resolve(oracle_dir, source_workspace)
    selection_path = _resolve(refinement_selection_path, workspace)
    split_path = _resolve(teacher_split_path, workspace)
    receipt_path = _resolve(source_receipt_path, workspace)
    output = _resolve(output_dir, workspace)
    target_deck = None if target_deck_path is None else _resolve(target_deck_path, workspace)
    rows_bytes, manifest = _build_artifact(
        corpus=corpus,
        oracle=oracle,
        selection_path=selection_path,
        split_path=split_path,
        receipt_path=receipt_path,
        source_workspace=source_workspace,
        workspace=workspace,
        target_archetype=target_archetype,
        target_deck_path=target_deck,
    )
    output.mkdir(parents=True, exist_ok=True)
    _write_bytes_once(output / "advantages.jsonl", rows_bytes)
    _write_bytes_once(output / "manifest.json", _json(manifest, pretty=True))
    return verify_teacher_advantages(output, workspace)


def verify_teacher_advantages(
    output_dir: str | Path,
    workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve() if workspace_root else Path(__file__).resolve().parents[1]
    output = _resolve(output_dir, workspace)
    manifest = _read_object(output / "manifest.json")
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("manifest_sha256") != _manifest_hash(manifest):
        raise ValueError("teacher advantage manifest self-hash mismatch")
    inputs = manifest.get("inputs")
    required = {
        "corpus_manifest", "corpus_states", "oracle_run_manifest", "oracle_report",
        "refinement_selection", "source_receipt", "teacher_split",
    }
    if not isinstance(inputs, Mapping) or not required <= set(inputs) or not set(inputs) <= required | {"target_deck"}:
        raise ValueError("invalid teacher advantage input bindings")
    resolved = {}
    for name, binding in inputs.items():
        if not isinstance(binding, Mapping) or not isinstance(binding.get("path"), str) or not isinstance(binding.get("sha256"), str):
            raise ValueError("invalid teacher advantage input binding: %s" % name)
        path = _resolve(binding["path"], workspace)
        if not path.is_file() or _file_sha256(path) != binding["sha256"]:
            raise ValueError("teacher advantage input hash mismatch: %s" % name)
        resolved[name] = path
    source_workspace = _resolve(str(manifest.get("source_workspace_path")), workspace)
    corpus = resolved["corpus_states"].parent
    oracle = resolved["oracle_run_manifest"].parent
    if resolved["corpus_manifest"] != corpus / "manifest.json" or resolved["oracle_report"] != oracle / "report.json":
        raise ValueError("teacher advantage source layout drift")
    rows_bytes, expected = _build_artifact(
        corpus=corpus,
        oracle=oracle,
        selection_path=resolved["refinement_selection"],
        split_path=resolved["teacher_split"],
        receipt_path=resolved["source_receipt"],
        source_workspace=source_workspace,
        workspace=workspace,
        target_archetype=manifest.get("target_archetype"),
        target_deck_path=resolved.get("target_deck"),
    )
    if manifest != expected:
        raise ValueError("teacher advantage manifest does not reproduce")
    rows_path = output / "advantages.jsonl"
    if not rows_path.is_file() or rows_path.read_bytes() != rows_bytes:
        raise ValueError("teacher advantage rows do not reproduce")
    rows = _read_jsonl(rows_path)
    return {
        "verified": True,
        "manifest_sha256": manifest["manifest_sha256"],
        "states": len(rows),
        "actions": sum(len(row["actions"]) for row in rows),
        "splits": dict(manifest["counts"]["splits"]),
        "output_dir": str(output),
    }
