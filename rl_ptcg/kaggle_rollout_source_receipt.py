"""Cross-platform receipt for a Kaggle-side rollout source verification event."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from .kaggle_rollout_assets import canonical_sha256
from .kaggle_rollout_execution import verify_kaggle_rollout_execution


SCHEMA_VERSION = "ptcg_kaggle_rollout_source_receipt.v1"


def _json(value: Any, *, pretty: bool = False) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2 if pretty else None,
                       separators=None if pretty else (",", ":")) + "\n").encode("ascii")


def _hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("could not read %s: %s" % (path, error)) from error
    if not isinstance(value, dict):
        raise ValueError("%s must contain a JSON object" % path)
    return value


def _resolve(path: str | Path, workspace: Path) -> Path:
    candidate = Path(path)
    resolved = (candidate if candidate.is_absolute() else workspace / candidate).resolve()
    try:
        resolved.relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("path escapes workspace: %s" % path) from error
    return resolved


def _write_once(path: Path, value: Mapping[str, Any]) -> None:
    data = _json(value, pretty=True)
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError("refusing to replace non-identical source receipt: %s" % path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _source_event(log_path: Path, execution: Mapping[str, Any]) -> dict[str, Any]:
    try:
        entries = json.loads(log_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("could not parse Kaggle JSON-array log: %s" % log_path) from error
    if not isinstance(entries, list):
        raise ValueError("Kaggle log must be a JSON array")
    events = []
    for entry in entries:
        if not isinstance(entry, Mapping) or entry.get("stream_name") != "stdout" or not isinstance(entry.get("data"), str):
            continue
        try:
            value = json.loads(entry["data"].strip())
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict) or "execution_manifest_sha256" not in value:
            continue
        if entry["data"].strip() != json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True):
            raise ValueError("Kaggle source event must be compact canonical JSON")
        if "schema_version" in value and value["schema_version"] != execution.get("schema_version"):
            raise ValueError("Kaggle source event execution schema mismatch")
        events.append(value)
    if len(events) != 1:
        raise ValueError("Kaggle log must contain exactly one execution stdout source event")
    if events[0].get("verified") is not True:
        raise ValueError("Kaggle source event is not verified")
    return events[0]


def _execution(path: Path) -> dict[str, Any]:
    value = _read_object(path)
    if value.get("manifest_sha256") != _hash(value):
        raise ValueError("execution manifest self-hash mismatch")
    return value


def _validate(execution_path: Path, log_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    workspace = execution_path.parent.resolve()
    execution = _execution(execution_path)
    local = verify_kaggle_rollout_execution(execution_path, workspace)
    if not local.get("verified") or local.get("implementation_drift") != []:
        raise ValueError("local execution verification is not implementation-clean")
    event = _source_event(log_path, execution)
    required = {
        "verified": True, "report_recomputed": True, "runtime_drift": [],
        "implementation_drift": [], "execution_manifest_sha256": execution["manifest_sha256"],
        "run_manifest_sha256": execution.get("run_manifest_sha256"),
        "report_manifest_sha256": execution.get("report_manifest_sha256"),
        "rows": execution.get("rows"), "shards": execution.get("shards"),
    }
    for key, expected in required.items():
        if event.get(key) != expected:
            raise ValueError("Kaggle source event mismatch: %s" % key)
        if local.get(key) != expected and key not in {"runtime_drift", "implementation_drift", "verified", "report_recomputed"}:
            raise ValueError("local execution verification mismatch: %s" % key)
    return execution, local, event


def build_kaggle_rollout_source_receipt(
    execution_manifest_path: str | Path, kaggle_log_path: str | Path, output_path: str | Path,
    *, workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve() if workspace_root else Path(__file__).resolve().parents[1]
    execution_path = _resolve(execution_manifest_path, workspace)
    log_path, output = _resolve(kaggle_log_path, workspace), _resolve(output_path, workspace)
    execution, local, event = _validate(execution_path, log_path)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "inputs": {
            "execution_manifest": {"path": str(execution_path.relative_to(workspace)), "sha256": sha256(execution_path.read_bytes()).hexdigest()},
            "kaggle_log": {"path": str(log_path.relative_to(workspace)), "sha256": sha256(log_path.read_bytes()).hexdigest()},
        },
        "execution_manifest_sha256": execution["manifest_sha256"],
        "run_output": execution.get("run_output"),
        "run_manifest_sha256": local["run_manifest_sha256"],
        "report_manifest_sha256": local["report_manifest_sha256"],
        "rows": local["rows"], "shards": local["shards"],
        "source_event": event,
    }
    manifest["manifest_sha256"] = _hash(manifest)
    _write_once(output, manifest)
    return verify_kaggle_rollout_source_receipt(output, workspace_root=workspace)


def verify_kaggle_rollout_source_receipt(
    receipt_path: str | Path, *, workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve() if workspace_root else Path(__file__).resolve().parents[1]
    receipt = _resolve(receipt_path, workspace)
    manifest = _read_object(receipt)
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("manifest_sha256") != _hash(manifest):
        raise ValueError("source receipt self-hash mismatch")
    inputs = manifest.get("inputs")
    if not isinstance(inputs, Mapping) or set(inputs) != {"execution_manifest", "kaggle_log"}:
        raise ValueError("invalid source receipt input bindings")
    paths = {}
    for name, binding in inputs.items():
        if not isinstance(binding, Mapping) or set(binding) != {"path", "sha256"}:
            raise ValueError("invalid source receipt input binding: %s" % name)
        path = _resolve(str(binding["path"]), workspace)
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != binding["sha256"]:
            raise ValueError("source receipt input hash drift: %s" % name)
        paths[name] = path
    execution, local, event = _validate(paths["execution_manifest"], paths["kaggle_log"])
    expected = {
        "execution_manifest_sha256": execution["manifest_sha256"], "run_output": execution.get("run_output"),
        "run_manifest_sha256": local["run_manifest_sha256"], "report_manifest_sha256": local["report_manifest_sha256"],
        "rows": local["rows"], "shards": local["shards"], "source_event": event,
    }
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError("source receipt extracted verification binding drift")
    run_output = _resolve(str(execution["run_output"]), paths["execution_manifest"].parent)
    return {"verified": True, "manifest_sha256": manifest["manifest_sha256"],
            "execution_manifest_sha256": execution["manifest_sha256"], "run_output": str(run_output),
            "run_manifest_sha256": local["run_manifest_sha256"], "report_manifest_sha256": local["report_manifest_sha256"],
            "rows": local["rows"], "shards": local["shards"]}
