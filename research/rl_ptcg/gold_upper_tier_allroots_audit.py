"""Write-once audit for the all-roots upper-tier corpus expansion."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .gold_oracle_states import canonical_sha256, file_sha256, write_once
from .gold_upper_tier_screen import verify_screen
from .gold_upper_tier_states import verify_gold_upper_tier_states


SCHEMA_VERSION = "gold_upper_tier_allroots_audit.v1"
REFERENCE_STATE_COUNT = 23
EXPANDED_STATE_COUNT = 86


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


def _read_state_rows(path: Path) -> list[tuple[bytes, dict[str, Any]]]:
    rows = []
    for raw in path.read_bytes().splitlines():
        if not raw:
            raise ValueError("blank state row")
        try:
            value = json.loads(raw.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("invalid state row") from error
        if not isinstance(value, dict):
            raise ValueError("state row must be an object")
        rows.append((raw, value))
    return rows


def _spec(state: Mapping[str, Any]) -> tuple[str, int, int]:
    try:
        return str(state["episode_id"]), int(state["acting_seat"]), int(state["replay_step"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("state has no valid episode/seat/replay-step spec") from error


def _specs_from_screen(screen: Mapping[str, Any]) -> set[tuple[str, int, int]]:
    try:
        values = list(screen["base_state_specs"]) + list(screen["candidate_pool"])
    except (KeyError, TypeError) as error:
        raise ValueError("screen lacks base specs or candidate pool") from error
    specs = set()
    for value in values:
        if isinstance(value, Mapping):
            specs.add(_spec(value))
        elif isinstance(value, (list, tuple)) and len(value) == 3:
            specs.add((str(value[0]), int(value[1]), int(value[2])))
        else:
            raise ValueError("invalid screen state spec")
    return specs


def _state_index(rows: list[tuple[bytes, dict[str, Any]]], label: str) -> dict[tuple[str, int, int], tuple[bytes, dict[str, Any]]]:
    index = {}
    state_ids = set()
    for raw, state in rows:
        spec = _spec(state)
        if spec in index:
            raise ValueError("%s has duplicate state spec" % label)
        state_id = state.get("state_id")
        if not isinstance(state_id, str) or not state_id or state_id in state_ids:
            raise ValueError("%s has duplicate or invalid state ID" % label)
        index[spec] = (raw, state)
        state_ids.add(state_id)
    return index


def _assert_state_policy(state: Mapping[str, Any]) -> None:
    if state.get("gold_incremental") is not False:
        raise ValueError("state permits direct Gold candidates")
    metadata = state.get("current_metadata")
    if not isinstance(metadata, Mapping) or metadata.get("recorded_action_role") != "provenance_only":
        raise ValueError("state recorded-action provenance is not provenance_only")
    sets = state.get("candidate_sets")
    if not isinstance(sets, Mapping) or sets.get("rule_plus_gold") != sets.get("rule_diverse"):
        raise ValueError("rule_plus_gold differs from rule_diverse")
    candidates = state.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("state candidates are invalid")
    for candidate in candidates:
        if not isinstance(candidate, Mapping) or not isinstance(candidate.get("source_tags"), list):
            raise ValueError("candidate source tags are invalid")
        for tag in candidate["source_tags"]:
            lowered = str(tag).lower()
            if lowered in {"gold", "direct_gold"} or lowered.startswith("gold_"):
                raise ValueError("candidate has forbidden Gold source tag")


def _corpus_binding(path: Path, workspace: Path, verified: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _read_object(path / "manifest.json")
    return {
        "path": _portable_path(path, workspace),
        "manifest_file_sha256": file_sha256(path / "manifest.json"),
        "manifest_sha256": manifest.get("manifest_sha256"),
        "selection_manifest_file_sha256": file_sha256(path / "selection_manifest.json"),
        "states_file_sha256": file_sha256(path / "states.jsonl"),
        "verified": dict(verified),
    }


def build_allroots_audit(
    screen_path: str | Path, reference_corpus_dir: str | Path, expanded_corpus_dir: str | Path,
    workspace_root: str | Path, cli_path: str | Path,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    screen_file = _resolve(screen_path, workspace)
    reference_dir = _resolve(reference_corpus_dir, workspace)
    expanded_dir = _resolve(expanded_corpus_dir, workspace)
    screen_cli = (workspace / "infrastructure" / "tools" / "build_gold_upper_tier_screen.py").resolve()
    screen_verified = verify_screen(screen_file, workspace, screen_cli)
    reference_verified = verify_gold_upper_tier_states(reference_dir, workspace)
    expanded_verified = verify_gold_upper_tier_states(expanded_dir, workspace)
    screen = _read_object(screen_file)
    reference_rows = _read_state_rows(reference_dir / "states.jsonl")
    expanded_rows = _read_state_rows(expanded_dir / "states.jsonl")
    if len(reference_rows) != REFERENCE_STATE_COUNT or len(expanded_rows) != EXPANDED_STATE_COUNT:
        raise ValueError("expected exactly 23 reference and 86 expanded states")
    reference = _state_index(reference_rows, "reference corpus")
    expanded = _state_index(expanded_rows, "expanded corpus")
    expected_specs = _specs_from_screen(screen)
    if set(expanded) != expected_specs:
        raise ValueError("expanded corpus specs do not exactly match screen base-plus-pool union")
    if not set(reference) <= set(expanded):
        raise ValueError("reference corpus specs are missing from expanded corpus")
    for spec, (reference_raw, _) in reference.items():
        if reference_raw != expanded[spec][0]:
            raise ValueError("shared reference state payload drift: %s" % (spec,))
    for _, state in expanded_rows:
        _assert_state_policy(state)
    implementation = {}
    for name, path in {
        "audit_module": Path(__file__).resolve(),
        "audit_cli": Path(cli_path).resolve(),
    }.items():
        implementation[name] = {"path": _portable_path(path, workspace), "sha256": file_sha256(path)}
    result = {
        "schema_version": SCHEMA_VERSION,
        "screen": {
            "path": _portable_path(screen_file, workspace),
            "file_sha256": file_sha256(screen_file),
            "manifest_sha256": screen.get("manifest_sha256"),
            "verified": dict(screen_verified),
        },
        "reference_corpus": _corpus_binding(reference_dir, workspace, reference_verified),
        "expanded_corpus": _corpus_binding(expanded_dir, workspace, expanded_verified),
        "expected_expanded_specs": [list(spec) for spec in sorted(expected_specs)],
        "counts": {
            "reference_states": len(reference),
            "expanded_states": len(expanded),
            "expected_expanded_states": len(expected_specs),
            "shared_reference_payloads": len(reference),
        },
        "policy": {
            "direct_gold_candidates": False,
            "recorded_action_role": "provenance_only",
            "rule_plus_gold_equals_rule_diverse": True,
            "forbidden_gold_source_tags": True,
        },
        "implementation": implementation,
    }
    result["manifest_sha256"] = _self_hash(result)
    return result


def write_allroots_audit(
    screen_path: str | Path, reference_corpus_dir: str | Path, expanded_corpus_dir: str | Path,
    output_path: str | Path, workspace_root: str | Path, cli_path: str | Path,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    output = _resolve(output_path, workspace)
    result = build_allroots_audit(screen_path, reference_corpus_dir, expanded_corpus_dir, workspace, cli_path)
    write_once(output, result)
    return verify_allroots_audit(output, workspace, cli_path)


def verify_allroots_audit(output_path: str | Path, workspace_root: str | Path, cli_path: str | Path) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    output = _resolve(output_path, workspace)
    value = _read_object(output)
    if value.get("schema_version") != SCHEMA_VERSION or value.get("manifest_sha256") != _self_hash(value):
        raise ValueError("all-roots audit self-hash mismatch")
    expected = build_allroots_audit(
        workspace / value["screen"]["path"],
        workspace / value["reference_corpus"]["path"],
        workspace / value["expanded_corpus"]["path"],
        workspace,
        cli_path,
    )
    if value != expected:
        raise ValueError("all-roots audit does not reproduce")
    return {
        "verified": True,
        "reference_states": value["counts"]["reference_states"],
        "expanded_states": value["counts"]["expanded_states"],
        "manifest_sha256": value["manifest_sha256"],
        "output_path": str(output),
    }
