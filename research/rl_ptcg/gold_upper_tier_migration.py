"""Semantic migration audit for portable upper-tier state corpora."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from .gold_oracle_states import canonical_sha256, file_sha256, write_once
from .gold_upper_tier_states import (
    LEGACY_SCHEMA_VERSION,
    SCHEMA_VERSION,
    verify_gold_upper_tier_states,
)


REPORT_SCHEMA_VERSION = "gold_upper_tier_migration_audit.v1"


def _self_hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _read_states(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="ascii").splitlines():
        if not line:
            raise ValueError("blank upper-tier state row")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError("upper-tier state row must be an object")
        rows.append(value)
    return rows


def normalize_migrated_state(state: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(state))
    result["schema_version"] = "gold_upper_tier_states.semantic_normalized"
    try:
        source = result["own_deck"]["inventory_source"]
        source["source_path"] = "<bound-inventory-source>"
    except (KeyError, TypeError) as error:
        raise ValueError("state has no inventory provenance") from error
    return result


def compare_upper_tier_corpora(
    legacy_dir: str | Path, portable_dir: str | Path, workspace_root: str | Path,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    legacy, portable = Path(legacy_dir).resolve(), Path(portable_dir).resolve()
    for path in (legacy, portable):
        try:
            path.relative_to(workspace)
        except ValueError as error:
            raise ValueError("corpus path escapes workspace") from error
    legacy_verified = verify_gold_upper_tier_states(legacy, workspace)
    portable_verified = verify_gold_upper_tier_states(portable, workspace)
    if legacy_verified["schema_version"] != LEGACY_SCHEMA_VERSION:
        raise ValueError("legacy corpus schema mismatch")
    if portable_verified["schema_version"] != SCHEMA_VERSION:
        raise ValueError("portable corpus schema mismatch")
    legacy_rows = {row["decision_id"]: row for row in _read_states(legacy / "states.jsonl")}
    portable_rows = {row["decision_id"]: row for row in _read_states(portable / "states.jsonl")}
    if set(legacy_rows) != set(portable_rows):
        raise ValueError("migration changed decision membership")
    comparisons = []
    for decision_id in sorted(legacy_rows):
        old = normalize_migrated_state(legacy_rows[decision_id])
        new = normalize_migrated_state(portable_rows[decision_id])
        old_hash, new_hash = canonical_sha256(old), canonical_sha256(new)
        comparisons.append({
            "decision_id": decision_id,
            "state_id": legacy_rows[decision_id]["state_id"],
            "legacy_normalized_sha256": old_hash,
            "portable_normalized_sha256": new_hash,
            "semantic_equal": old_hash == new_hash,
        })
    result = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "legacy": {
            "path": str(legacy.relative_to(workspace)).replace("\\", "/"),
            "manifest_sha256": file_sha256(legacy / "manifest.json"),
            "states_sha256": file_sha256(legacy / "states.jsonl"),
            "verified_schema": legacy_verified["schema_version"],
            "implementation_drift": legacy_verified["implementation_drift"],
        },
        "portable": {
            "path": str(portable.relative_to(workspace)).replace("\\", "/"),
            "manifest_sha256": file_sha256(portable / "manifest.json"),
            "states_sha256": file_sha256(portable / "states.jsonl"),
            "verified_schema": portable_verified["schema_version"],
            "implementation_drift": portable_verified["implementation_drift"],
        },
        "normalizations": [
            "schema_version",
            "own_deck.inventory_source.source_path",
        ],
        "state_count": len(comparisons),
        "semantic_equal_count": sum(item["semantic_equal"] for item in comparisons),
        "all_semantically_equal": all(item["semantic_equal"] for item in comparisons),
        "comparisons": comparisons,
    }
    result["manifest_sha256"] = _self_hash(result)
    return result


def write_migration_audit(
    legacy_dir: str | Path,
    portable_dir: str | Path,
    output_path: str | Path,
    workspace_root: str | Path,
) -> dict[str, Any]:
    result = compare_upper_tier_corpora(legacy_dir, portable_dir, workspace_root)
    write_once(Path(output_path), result)
    return result


def verify_migration_audit(
    output_path: str | Path, workspace_root: str | Path,
) -> dict[str, Any]:
    path = Path(output_path).resolve()
    value = json.loads(path.read_text(encoding="ascii"))
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != REPORT_SCHEMA_VERSION
        or value.get("manifest_sha256") != _self_hash(value)
    ):
        raise ValueError("migration audit self-hash mismatch")
    workspace = Path(workspace_root).resolve()
    expected = compare_upper_tier_corpora(
        workspace / value["legacy"]["path"],
        workspace / value["portable"]["path"],
        workspace,
    )
    if value != expected:
        raise ValueError("migration audit does not reproduce")
    return {
        "verified": True,
        "state_count": value["state_count"],
        "all_semantically_equal": value["all_semantically_equal"],
        "manifest_sha256": value["manifest_sha256"],
        "output_path": str(path),
    }
