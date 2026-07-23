"""Select expanded-only upper-tier states for one opponent archetype."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any, Mapping

from .gold_oracle_states import canonical_sha256, file_sha256, write_once
from .gold_upper_tier_allroots_audit import (
    SCHEMA_VERSION as AUDIT_SCHEMA_VERSION,
    verify_allroots_audit,
)


SCHEMA_VERSION = "gold_upper_tier_extension_selection.v2"


def _self_hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _resolve(path: str | Path, workspace: Path) -> Path:
    resolved = (Path(path) if Path(path).is_absolute() else workspace / path).resolve()
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("path escapes workspace: %s" % path) from error
    return resolved


def _portable_path(path: Path, workspace: Path) -> str:
    return str(path.resolve().relative_to(workspace.resolve())).replace("\\", "/")


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("could not read %s" % path) from error
    if not isinstance(value, dict):
        raise ValueError("%s must contain an object" % path)
    return value


def _read_states(path: Path, label: str) -> list[dict[str, Any]]:
    rows = []
    try:
        lines = path.read_bytes().splitlines()
    except OSError as error:
        raise ValueError("could not read %s states" % label) from error
    for raw in lines:
        if not raw:
            raise ValueError("%s has a blank state row" % label)
        try:
            value = json.loads(raw.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("%s has an invalid state row" % label) from error
        if not isinstance(value, dict):
            raise ValueError("%s state row must be an object" % label)
        rows.append(value)
    return rows


def _state_id(state: Mapping[str, Any]) -> str:
    value = state.get("state_id")
    if not isinstance(value, str) or not value:
        raise ValueError("state has no valid state ID")
    return value


def _spec(state: Mapping[str, Any]) -> tuple[str, int, int]:
    try:
        return str(state["episode_id"]), int(state["acting_seat"]), int(state["replay_step"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("state has no valid episode/seat/replay-step spec") from error


def _index_states(rows: list[dict[str, Any]], label: str) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, int, int], dict[str, Any]]]:
    by_id, by_spec = {}, {}
    for state in rows:
        state_id, spec = _state_id(state), _spec(state)
        if state_id in by_id:
            raise ValueError("%s has duplicate state ID" % label)
        if spec in by_spec:
            raise ValueError("%s has duplicate state spec" % label)
        by_id[state_id], by_spec[spec] = state, state
    return by_id, by_spec


def _corpus_binding(path: Path, workspace: Path) -> dict[str, Any]:
    manifest = _read_object(path / "manifest.json")
    return {
        "path": _portable_path(path, workspace),
        "manifest_file_sha256": file_sha256(path / "manifest.json"),
        "manifest_sha256": manifest.get("manifest_sha256"),
        "selection_manifest_file_sha256": file_sha256(path / "selection_manifest.json"),
        "states_file_sha256": file_sha256(path / "states.jsonl"),
    }


def _validate_audit_corpus_binding(audit: Mapping[str, Any], name: str, path: Path, workspace: Path) -> dict[str, Any]:
    expected = audit.get(name)
    if not isinstance(expected, Mapping):
        raise ValueError("audit lacks %s binding" % name)
    actual = _corpus_binding(path, workspace)
    required = set(actual) | {"verified"}
    if set(expected) != required or any(expected[key] != actual[key] for key in actual):
        raise ValueError("%s corpus binding mismatch" % name)
    return actual


def _distribution(values: list[int]) -> dict[str, int]:
    return {str(key): count for key, count in sorted(Counter(values).items())}


def _build_value(audit_path: Path, workspace: Path, *, archetype: str, opponent_heads: int) -> dict[str, Any]:
    if not isinstance(archetype, str) or not archetype:
        raise ValueError("archetype must be non-empty")
    if opponent_heads <= 0:
        raise ValueError("opponent_heads must be positive")
    audit_cli = (workspace / "tools" / "build_gold_upper_tier_allroots_audit.py").resolve()
    verify_allroots_audit(audit_path, workspace, audit_cli)
    audit = _read_object(audit_path)
    if audit.get("schema_version") != AUDIT_SCHEMA_VERSION:
        raise ValueError("unsupported all-roots audit schema")
    reference_dir = _resolve(str(audit["reference_corpus"]["path"]), workspace)
    expanded_dir = _resolve(str(audit["expanded_corpus"]["path"]), workspace)
    reference_binding = _validate_audit_corpus_binding(audit, "reference_corpus", reference_dir, workspace)
    expanded_binding = _validate_audit_corpus_binding(audit, "expanded_corpus", expanded_dir, workspace)
    reference_by_id, reference_by_spec = _index_states(_read_states(reference_dir / "states.jsonl", "reference corpus"), "reference corpus")
    expanded_by_id, expanded_by_spec = _index_states(_read_states(expanded_dir / "states.jsonl", "expanded corpus"), "expanded corpus")
    if not set(reference_by_id) <= set(expanded_by_id) or not set(reference_by_spec) <= set(expanded_by_spec):
        raise ValueError("reference corpus is not contained in expanded corpus")
    for spec, reference_state in reference_by_spec.items():
        if reference_state != expanded_by_spec[spec]:
            raise ValueError("shared reference state payload drift")

    selected = []
    for state_id, state in expanded_by_id.items():
        belief = state.get("belief")
        if not isinstance(belief, Mapping):
            raise ValueError("expanded state has no belief")
        if state_id not in reference_by_id and belief.get("archetype") == archetype:
            candidate_sets = state.get("candidate_sets")
            if not isinstance(candidate_sets, Mapping):
                raise ValueError("selected state has no candidate sets")
            candidates, hypotheses = candidate_sets.get("rule_diverse"), belief.get("hypotheses")
            if not isinstance(candidates, list) or not isinstance(hypotheses, list):
                raise ValueError("selected state has invalid candidate or hypothesis payload")
            episode, seat, step = _spec(state)
            selected.append({
                "state_id": state_id,
                "episode_id": episode,
                "acting_seat": seat,
                "replay_step": step,
                "candidate_count": len(candidates),
                "hypothesis_count": len(hypotheses),
            })
    selected.sort(key=lambda item: (item["episode_id"], item["acting_seat"], item["replay_step"], item["state_id"]))
    if not selected:
        raise ValueError("selection is empty")
    selected_ids = [item["state_id"] for item in selected]
    selected_specs = [[item["episode_id"], item["acting_seat"], item["replay_step"]] for item in selected]
    if len(selected_ids) != len(set(selected_ids)) or len(selected_specs) != len({tuple(item) for item in selected_specs}):
        raise ValueError("selection has duplicate state IDs or specs")
    value = {
        "schema_version": SCHEMA_VERSION,
        "input_audit": {
            "path": _portable_path(audit_path, workspace),
            "file_sha256": file_sha256(audit_path),
            "manifest_sha256": audit.get("manifest_sha256"),
        },
        "reference_corpus": reference_binding,
        "expanded_corpus": expanded_binding,
        "selection_criteria": {
            "expanded_minus_reference_by": "state_id",
            "belief_archetype": archetype,
            "candidate_set": "rule_diverse",
            "selection_fields": ["state_id", "episode_id", "acting_seat", "replay_step", "belief.archetype"],
            "recorded_action_signals_forbidden": True,
            "candidate_action_signals_forbidden": True,
            "terminal_signals_forbidden": True,
            "post_target_signals_forbidden": True,
        },
        "selected_state_ids": selected_ids,
        "selected_state_specs": selected_specs,
        "counts": {
            "reference_states": len(reference_by_id),
            "expanded_states": len(expanded_by_id),
            "expanded_minus_reference_states": len(expanded_by_id) - len(reference_by_id),
            "selected_states": len(selected),
        },
        "distributions": {
            "candidate_count": _distribution([item["candidate_count"] for item in selected]),
            "hypothesis_count": _distribution([item["hypothesis_count"] for item in selected]),
        },
        "estimated_p1_rows": sum(
            item["candidate_count"] * item["hypothesis_count"] * opponent_heads
            for item in selected
        ),
        "opponent_heads": opponent_heads,
    }
    value["manifest_sha256"] = _self_hash(value)
    return value


def write_upper_tier_extension_selection(audit_path: str | Path, archetype: str, output_path: str | Path, workspace_root: str | Path, *, opponent_heads: int = 3) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    audit = _resolve(audit_path, workspace)
    output = _resolve(output_path, workspace)
    value = _build_value(audit, workspace, archetype=archetype, opponent_heads=opponent_heads)
    write_once(output, value)
    return verify_upper_tier_extension_selection(output, workspace)


def verify_upper_tier_extension_selection(output_path: str | Path, workspace_root: str | Path) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    output = _resolve(output_path, workspace)
    value = _read_object(output)
    if value.get("schema_version") != SCHEMA_VERSION or value.get("manifest_sha256") != _self_hash(value):
        raise ValueError("upper-tier extension selection self-hash mismatch")
    criteria = value.get("selection_criteria")
    if not isinstance(criteria, Mapping):
        raise ValueError("selection criteria are invalid")
    expected = _build_value(
        _resolve(str(value["input_audit"]["path"]), workspace),
        workspace,
        archetype=str(criteria["belief_archetype"]),
        opponent_heads=int(value["opponent_heads"]),
    )
    if value != expected:
        raise ValueError("upper-tier extension selection does not reproduce")
    return {
        "verified": True,
        "selected_states": value["counts"]["selected_states"],
        "state_ids": value["selected_state_ids"],
        "manifest_sha256": value["manifest_sha256"],
        "output_path": str(output),
    }
