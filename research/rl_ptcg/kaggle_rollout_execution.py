"""Verify a self-contained Kaggle Gold rollout execution artifact."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .gold_oracle_runner import verify_oracle_output
from .kaggle_rollout_assets import canonical_sha256, verify_rollout_payload
from .seeded_engine_linux import verify_seeded_engine_linux


SCHEMA_VERSION = "ptcg_kaggle_rollout_execution.v2"
LEGACY_SCHEMA_VERSION = "ptcg_kaggle_rollout_execution.v1"


def _self_hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="ascii"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object: %s" % path)
    return value


def _resolve_inside(path: str | Path, workspace: Path, label: str) -> Path:
    candidate = Path(path)
    resolved = candidate.resolve() if candidate.is_absolute() else (workspace / candidate).resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError as error:
        raise ValueError("%s escapes execution workspace" % label) from error
    return resolved


def verify_kaggle_rollout_execution(
    execution_manifest_path: str | Path,
    workspace_root: str | Path,
    *,
    legacy_asset_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    execution_path = Path(execution_manifest_path).resolve()
    try:
        execution_path.relative_to(workspace)
    except ValueError as error:
        raise ValueError("execution manifest escapes workspace") from error
    execution = _read_object(execution_path)
    schema_version = execution.get("schema_version")
    if (
        schema_version not in {SCHEMA_VERSION, LEGACY_SCHEMA_VERSION}
        or execution.get("manifest_sha256") != _self_hash(execution)
    ):
        raise ValueError("Kaggle execution manifest self-hash mismatch")

    if schema_version == SCHEMA_VERSION:
        asset_manifest = _resolve_inside(
            execution["asset_manifest_path"], workspace, "asset manifest",
        )
        engine_output = _resolve_inside(execution["engine_output"], workspace, "engine output")
    else:
        if legacy_asset_manifest_path is None:
            raise ValueError("legacy execution verification requires an asset manifest")
        asset_manifest = Path(legacy_asset_manifest_path).resolve()
        engine_output = workspace / "runtime_engine"

    asset_result = verify_rollout_payload(workspace, asset_manifest)
    if asset_result["manifest_sha256"] != execution.get("asset_manifest_sha256"):
        raise ValueError("execution asset manifest binding mismatch")
    engine_result = verify_seeded_engine_linux(engine_output)
    if engine_result["manifest_sha256"] != execution.get("engine_manifest_sha256"):
        raise ValueError("execution engine manifest binding mismatch")

    run_output = _resolve_inside(execution["run_output"], workspace, "run output")
    run_result = verify_oracle_output(run_output, workspace)
    expected = {
        "run_manifest_sha256": execution.get("run_manifest_sha256"),
        "report_manifest_sha256": execution.get("report_manifest_sha256"),
        "rows": execution.get("rows"),
        "shards": execution.get("shards"),
    }
    actual = {key: run_result.get(key) for key in expected}
    if not run_result.get("complete") or actual != expected:
        raise ValueError("execution rollout binding mismatch")
    return {
        "verified": True,
        "schema_version": schema_version,
        "execution_manifest_sha256": execution["manifest_sha256"],
        "asset_manifest_sha256": asset_result["manifest_sha256"],
        "engine_manifest_sha256": engine_result["manifest_sha256"],
        "run_manifest_sha256": run_result["run_manifest_sha256"],
        "report_manifest_sha256": run_result["report_manifest_sha256"],
        "rows": run_result["rows"],
        "shards": run_result["shards"],
        "report_recomputed": run_result["report_recomputed"],
        "implementation_drift": run_result["current_implementation_drift"],
        "runtime_drift": run_result["current_runtime_drift"],
        "workspace_root": str(workspace),
    }
