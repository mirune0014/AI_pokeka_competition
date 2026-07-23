"""Write-once audit for a generic upper-tier corpus extension."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .gold_oracle_states import canonical_sha256, file_sha256, write_once
from .gold_upper_tier_allroots_audit import (
    _assert_state_policy,
    _corpus_binding,
    _read_object,
    _read_state_rows,
    _resolve,
    _state_index,
)
from .gold_upper_tier_states import verify_gold_upper_tier_states


SCHEMA_VERSION = "gold_upper_tier_corpus_extension_audit.v1"


def _self_hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _normalize_specs(values: Iterable[Iterable[Any]]) -> list[tuple[str, int, int]]:
    result = []
    for value in values:
        try:
            episode, seat, step = value
            spec = str(episode), int(seat), int(step)
        except (TypeError, ValueError) as error:
            raise ValueError("added-state specs must be EPISODE,SEAT,STEP triples") from error
        if not spec[0] or spec[1] < 0 or spec[2] < 0:
            raise ValueError("added-state specs must have non-empty episodes and non-negative indexes")
        result.append(spec)
    if not result or len(result) != len(set(result)):
        raise ValueError("added-state specs must be non-empty and unique")
    return sorted(result)


def build_corpus_extension_audit(
    reference_corpus_dir: str | Path,
    expanded_corpus_dir: str | Path,
    expected_added_specs: Iterable[Iterable[Any]],
    workspace_root: str | Path,
    cli_path: str | Path,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    reference_dir = _resolve(reference_corpus_dir, workspace)
    expanded_dir = _resolve(expanded_corpus_dir, workspace)
    reference_verified = verify_gold_upper_tier_states(reference_dir, workspace)
    expanded_verified = verify_gold_upper_tier_states(expanded_dir, workspace)
    reference_rows = _read_state_rows(reference_dir / "states.jsonl")
    expanded_rows = _read_state_rows(expanded_dir / "states.jsonl")
    reference = _state_index(reference_rows, "reference corpus")
    expanded = _state_index(expanded_rows, "expanded corpus")
    expected = _normalize_specs(expected_added_specs)
    expected_set = set(expected)

    if not set(reference) <= set(expanded):
        raise ValueError("reference corpus specs are missing from expanded corpus")
    actual_added = set(expanded) - set(reference)
    if actual_added != expected_set:
        raise ValueError("expanded-minus-reference specs do not match expected added specs")
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
        path = path.resolve()
        implementation[name] = {
            "path": str(path.relative_to(workspace)).replace("\\", "/"),
            "sha256": file_sha256(path),
        }
    value = {
        "schema_version": SCHEMA_VERSION,
        "reference_corpus": _corpus_binding(reference_dir, workspace, reference_verified),
        "expanded_corpus": _corpus_binding(expanded_dir, workspace, expanded_verified),
        "expected_added_specs": [list(spec) for spec in expected],
        "counts": {
            "reference_states": len(reference),
            "expanded_states": len(expanded),
            "added_states": len(actual_added),
            "shared_reference_payloads": len(reference),
        },
        "policy": {
            "shared_payload_comparison": "byte_exact",
            "direct_gold_candidates": False,
            "recorded_action_role": "provenance_only",
            "rule_plus_gold_equals_rule_diverse": True,
            "forbidden_gold_source_tags": True,
        },
        "implementation": implementation,
    }
    value["manifest_sha256"] = _self_hash(value)
    return value


def write_corpus_extension_audit(
    reference_corpus_dir: str | Path,
    expanded_corpus_dir: str | Path,
    expected_added_specs: Iterable[Iterable[Any]],
    output_path: str | Path,
    workspace_root: str | Path,
    cli_path: str | Path,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    output = _resolve(output_path, workspace)
    value = build_corpus_extension_audit(
        reference_corpus_dir,
        expanded_corpus_dir,
        expected_added_specs,
        workspace,
        cli_path,
    )
    write_once(output, value)
    return verify_corpus_extension_audit(output, workspace, cli_path)


def verify_corpus_extension_audit(
    output_path: str | Path,
    workspace_root: str | Path,
    cli_path: str | Path,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    output = _resolve(output_path, workspace)
    value = _read_object(output)
    if value.get("schema_version") != SCHEMA_VERSION or value.get("manifest_sha256") != _self_hash(value):
        raise ValueError("corpus extension audit self-hash mismatch")
    expected = build_corpus_extension_audit(
        workspace / value["reference_corpus"]["path"],
        workspace / value["expanded_corpus"]["path"],
        value.get("expected_added_specs", []),
        workspace,
        cli_path,
    )
    if value != expected:
        raise ValueError("corpus extension audit does not reproduce")
    return {
        "verified": True,
        "reference_states": value["counts"]["reference_states"],
        "expanded_states": value["counts"]["expanded_states"],
        "added_states": value["counts"]["added_states"],
        "manifest_sha256": value["manifest_sha256"],
        "output_path": str(output),
    }
