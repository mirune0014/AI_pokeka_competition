"""Read-only verification for Gold disagreement audit artifacts."""
from __future__ import annotations

from hashlib import blake2b, sha256
import json
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "gold_disagreement_audit.v1"


def _json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n").encode("ascii")


def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _file_hash(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    return _sha256_bytes(path.read_bytes())


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid JSON object: %s" % path) from error
    if not isinstance(value, dict):
        raise ValueError("expected JSON object: %s" % path)
    return value


def _require_hash(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError("invalid %s" % name)
    return value


def _verify_equal(actual: str, expected: Any, name: str) -> None:
    if actual != _require_hash(expected, name):
        raise ValueError("%s mismatch" % name)


def _canonical_sha256(value: Any) -> str:
    return _sha256_bytes(_json(value))


def _validate_sample_manifest(manifest: Mapping[str, Any]) -> list[str]:
    required = {
        "schema_version", "source_splits", "seed", "target_count", "dataset_sha256",
        "split_manifest_sha256", "baseline_map_canonical_sha256", "strata", "quotas",
        "decision_ids", "manifest_blake2b", "manifest_sha256",
    }
    if set(manifest) != required or manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("invalid sample_manifest schema")
    sources = manifest["source_splits"]
    identifiers = manifest["decision_ids"]
    if (not isinstance(sources, list) or not all(isinstance(item, str) for item in sources)
            or "blind" in sources or not isinstance(manifest["seed"], str)
            or not isinstance(manifest["target_count"], int) or manifest["target_count"] < 0
            or not isinstance(manifest["strata"], list) or not all(isinstance(item, str) for item in manifest["strata"])
            or not isinstance(manifest["quotas"], dict) or not isinstance(identifiers, list)
            or not all(isinstance(item, str) and item for item in identifiers) or len(identifiers) != len(set(identifiers))):
        raise ValueError("invalid sample_manifest values")
    for name in ("dataset_sha256", "split_manifest_sha256", "baseline_map_canonical_sha256"):
        _require_hash(manifest[name], name)
    unsigned = {key: value for key, value in manifest.items() if key not in {"manifest_blake2b", "manifest_sha256"}}
    _verify_equal(blake2b(_json(unsigned), digest_size=32).hexdigest(), manifest["manifest_blake2b"], "sample manifest_blake2b")
    sha_payload = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    _verify_equal(_canonical_sha256(sha_payload), manifest["manifest_sha256"], "sample manifest_sha256")
    return identifiers


def _load_rows(path: Path, expected_ids: list[str]) -> tuple[list[dict[str, Any]], bytes]:
    data = path.read_bytes()
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise ValueError("invalid rows.jsonl encoding") from error
    if any(not line for line in lines):
        raise ValueError("rows.jsonl contains blank line")
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError("invalid rows.jsonl line %d" % number) from error
        if not isinstance(row, dict) or not isinstance(row.get("decision_id"), str) or not row["decision_id"]:
            raise ValueError("invalid rows.jsonl line %d" % number)
        rows.append(row)
    row_ids = [row["decision_id"] for row in rows]
    if len(row_ids) != len(set(row_ids)) or len(row_ids) != len(expected_ids) or set(row_ids) != set(expected_ids):
        raise ValueError("rows decision IDs do not match sample manifest")
    return rows, data


def _workspace_file(
    workspace: Path, relative: str, label: str = "implementation", *, allow_absolute: bool = False,
) -> Path:
    path = Path(relative)
    if path.is_absolute():
        if not allow_absolute:
            raise ValueError("%s path must be workspace relative: %s" % (label, relative))
        resolved = path.resolve()
    else:
        resolved = (workspace / path).resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError as error:
        raise ValueError("%s path escapes workspace: %s" % (label, relative)) from error
    return resolved


def verify_gold_disagreement_audit(
    audit_output_dir: str | Path, dataset_dir: str | Path, baseline_map: Mapping[str, str], workspace_root: str | Path,
) -> dict[str, Any]:
    """Verify audit bindings without changing or interpreting dataset decision data."""
    output = Path(audit_output_dir).resolve()
    dataset = Path(dataset_dir).resolve()
    workspace = Path(workspace_root).resolve()
    if not output.is_dir() or not dataset.is_dir() or not workspace.is_dir():
        raise FileNotFoundError("audit output, dataset, and workspace must be directories")
    if not isinstance(baseline_map, Mapping) or not all(isinstance(key, str) and isinstance(value, str) for key, value in baseline_map.items()):
        raise ValueError("baseline map must be a string-to-string mapping")
    normalized_map = {str(key): str(value) for key, value in baseline_map.items()}
    sample = _load_object(output / "sample_manifest.json")
    identifiers = _validate_sample_manifest(sample)
    rows, rows_bytes = _load_rows(output / "rows.jsonl", identifiers)
    report = _load_object(output / "report.json")
    if report.get("schema_version") != SCHEMA_VERSION or report.get("rows") != len(rows):
        raise ValueError("invalid report schema or row count")
    _verify_equal(_sha256_bytes(rows_bytes), report.get("rows_sha256"), "report rows_sha256")
    if report.get("sample_manifest_blake2b") != sample["manifest_blake2b"]:
        raise ValueError("report sample manifest mismatch")

    binding = _load_object(output / "checksum_manifest.json")
    required = {
        "schema_version", "sample_manifest_sha256", "rows_sha256", "report_sha256",
        "dataset_manifest_sha256", "split_manifest_sha256", "baseline_map_canonical_sha256",
        "baseline_files", "implementation_files_sha256", "python", "platform", "command",
        "config", "manifest_blake2b",
    }
    if set(binding) != required or binding.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("invalid checksum_manifest schema")
    unsigned = {key: value for key, value in binding.items() if key != "manifest_blake2b"}
    _verify_equal(blake2b(_json(unsigned), digest_size=32).hexdigest(), binding["manifest_blake2b"], "checksum manifest_blake2b")
    for name, path in (("sample_manifest_sha256", output / "sample_manifest.json"), ("rows_sha256", output / "rows.jsonl"),
                       ("report_sha256", output / "report.json"), ("dataset_manifest_sha256", dataset / "dataset_manifest.json"),
                       ("split_manifest_sha256", dataset / "split_manifest.json")):
        _verify_equal(_file_hash(path), binding.get(name), name)
    _verify_equal(_canonical_sha256(normalized_map), binding.get("baseline_map_canonical_sha256"), "baseline map canonical SHA256")
    if sample["baseline_map_canonical_sha256"] != binding["baseline_map_canonical_sha256"]:
        raise ValueError("sample baseline map mismatch")
    if not isinstance(binding["baseline_files"], dict) or not isinstance(binding["implementation_files_sha256"], dict):
        raise ValueError("invalid checksum manifest file mappings")
    if set(binding["baseline_files"]) != set(normalized_map):
        raise ValueError("baseline file bindings do not match baseline map")
    for key, files in binding["baseline_files"].items():
        if key not in normalized_map or not isinstance(files, dict):
            raise ValueError("invalid baseline file binding")
        if set(files) != {"main.py", "deck.csv"}:
            raise ValueError("baseline binding must include main.py and deck.csv")
        directory = _workspace_file(workspace, normalized_map[key], "baseline", allow_absolute=True)
        for name, expected in files.items():
            if name not in {"main.py", "deck.csv"}:
                raise ValueError("invalid baseline file name")
            _verify_equal(_file_hash(directory / name), expected, "baseline %s/%s" % (key, name))
    for relative, expected in binding["implementation_files_sha256"].items():
        if not isinstance(relative, str):
            raise ValueError("invalid implementation path")
        _verify_equal(_file_hash(_workspace_file(workspace, relative)), expected, "implementation %s" % relative)
    overall = report.get("overall", {})
    if not isinstance(overall, dict):
        raise ValueError("invalid report overall")
    errors = overall.get("errors", report.get("errors", {}))
    if isinstance(errors, dict):
        errors = sum(value for value in errors.values() if isinstance(value, int))
    if not isinstance(errors, int) or not isinstance(overall.get("unranked_count", 0), int):
        raise ValueError("invalid report summary")
    return {"sampled": len(identifiers), "rows": len(rows), "errors": errors,
            "unranked": overall.get("unranked_count", 0), "truncated": report.get("truncated", 0), "output_dir": str(output)}
