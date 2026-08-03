"""Build and verify a private, engine-free Kaggle rollout asset dataset."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "ptcg_kaggle_rollout_assets.v1"
RUNTIME_TOOLS = (
    "infrastructure/tools/run_gold_oracle_teacher.py",
    "infrastructure/tools/build_seeded_engine_linux.py",
    "infrastructure/tools/verify_kaggle_gold_rollout_assets.py",
    "infrastructure/tools/verify_kaggle_gold_rollout_execution.py",
    "infrastructure/tools/ptcg_common.py",
    "infrastructure/tools/build_gold_candidate_selection.py",
    "infrastructure/tools/build_gold_upper_tier_states.py",
)
FORBIDDEN_NAMES = frozenset((
    "cg.dll", "libcg.so", "libcg.dylib", "libcg-arm64.so", "kaggle.json",
    ".env", "credentials.json",
))
FORBIDDEN_SUFFIXES = frozenset((".h", ".hpp", ".cpp", ".cc", ".cxx", ".pdb", ".lib"))


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = (json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":"),
    ) + "\n").encode("ascii")
    return sha256(encoded).hexdigest()


def _self_hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="ascii"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object: %s" % path)
    return value


def _relative(path: Path, workspace: Path) -> str:
    try:
        value = path.resolve().relative_to(workspace.resolve())
    except ValueError as error:
        raise ValueError("asset source escapes workspace: %s" % path) from error
    return str(value).replace("\\", "/")


def _forbidden(relative: str) -> bool:
    path = Path(relative)
    lowered = [part.lower() for part in path.parts]
    return (
        path.name.lower() in FORBIDDEN_NAMES
        or path.suffix.lower() in FORBIDDEN_SUFFIXES
        or "__pycache__" in lowered
        or ".git" in lowered
        or ("external" in lowered and "ptcg_engine" in lowered)
    )


def verify_rollout_payload(
    payload_root: str | Path, asset_manifest_path: str | Path,
) -> dict[str, Any]:
    payload = Path(payload_root).resolve()
    manifest_path = Path(asset_manifest_path).resolve()
    manifest = _read_object(manifest_path)
    if (
        manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("manifest_sha256") != _self_hash(manifest)
    ):
        raise ValueError("asset manifest self-hash mismatch")
    expected = manifest.get("payload_files_sha256")
    if not isinstance(expected, Mapping) or not expected:
        raise ValueError("asset manifest has no payload files")
    for relative, digest in expected.items():
        if _forbidden(str(relative)):
            raise ValueError("forbidden file in asset payload: %s" % relative)
        path = payload / str(relative)
        if not path.is_file() or file_sha256(path) != digest:
            raise ValueError("asset payload hash mismatch: %s" % relative)
    return {
        "verified": True,
        "dataset_id": manifest["dataset_id"],
        "files": len(expected),
        "payload_bytes": sum((payload / relative).stat().st_size for relative in expected),
        "manifest_sha256": manifest["manifest_sha256"],
        "payload_root": str(payload),
    }


def _copy_allowlisted(
    sources: Iterable[Path], workspace: Path, payload: Path,
) -> dict[str, str]:
    files: dict[str, str] = {}
    for source in sorted({path.resolve() for path in sources}, key=str):
        if not source.is_file():
            raise FileNotFoundError("asset source is not a file: %s" % source)
        relative = _relative(source, workspace)
        if _forbidden(relative):
            raise ValueError("forbidden asset source: %s" % relative)
        digest = file_sha256(source)
        previous = files.get(relative)
        if previous is not None and previous != digest:
            raise ValueError("asset destination has conflicting sources: %s" % relative)
        destination = payload / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if file_sha256(destination) != digest:
            raise ValueError("asset copy hash mismatch: %s" % relative)
        files[relative] = digest
    return dict(sorted(files.items()))


def _corpus_sources(corpus: Path, workspace: Path) -> set[Path]:
    selection = _read_object(corpus / "selection_manifest.json")
    manifest = _read_object(corpus / "manifest.json")
    if selection.get("schema_version") != "gold_upper_tier_states.v2":
        raise ValueError("Kaggle assets require the portable upper-tier v2 corpus")
    sources = {path for path in corpus.rglob("*") if path.is_file()}
    for binding in selection.get("inputs", {}).values():
        path = workspace / str(binding["path"])
        sources.add(path.resolve())
    for binding in manifest.get("source_replays", []):
        sources.add((workspace / str(binding["source_replay_path"])).resolve())
    return sources


def _policy_sources(directory: Path) -> set[Path]:
    sources = {
        path for name in ("main.py", "deck.csv", "requirements.txt")
        if (path := directory / name).is_file()
    }
    manifest_path = directory / "gold_prompt_ranker_manifest.json"
    if not manifest_path.is_file():
        return sources
    manifest = _read_object(manifest_path)
    sources.add(manifest_path)
    for key in ("checkpoint", "evaluation_report"):
        path = (directory / str(manifest[key])).resolve()
        try:
            path.relative_to(directory.resolve())
        except ValueError as error:
            raise ValueError("policy model file escapes its directory") from error
        sources.add(path)
    for binding in manifest.get("implementation", {}).values():
        path = (directory / str(binding["snapshot"])).resolve()
        try:
            path.relative_to(directory.resolve())
        except ValueError as error:
            raise ValueError("policy model snapshot escapes its directory") from error
        sources.add(path)
    return sources


def verify_rollout_assets(
    asset_root: str | Path, *, allow_missing_dataset_metadata: bool = False,
) -> dict[str, Any]:
    root = Path(asset_root).resolve()
    manifest = _read_object(root / "asset_manifest.json")
    payload_result = verify_rollout_payload(root / "payload", root / "asset_manifest.json")
    metadata_path = root / "dataset-metadata.json"
    metadata_present = metadata_path.is_file()
    if metadata_present:
        metadata = _read_object(metadata_path)
        if file_sha256(metadata_path) != manifest.get("dataset_metadata_sha256"):
            raise ValueError("dataset metadata hash mismatch")
        if metadata.get("id") != manifest.get("dataset_id"):
            raise ValueError("dataset id mismatch")
    elif not allow_missing_dataset_metadata:
        raise ValueError("dataset metadata is missing")
    expected = manifest["payload_files_sha256"]
    payload = root / "payload"
    actual_paths = {
        str(path.relative_to(payload)).replace("\\", "/")
        for path in payload.rglob("*") if path.is_file()
    }
    if actual_paths != set(expected):
        raise ValueError("asset payload file membership mismatch")
    required = {
        "research/rl_ptcg/gold_oracle_runner.py",
        "research/rl_ptcg/seeded_engine_linux.py",
        *RUNTIME_TOOLS,
        str(manifest["corpus_path"]) + "/manifest.json",
        str(manifest["corpus_path"]) + "/states.jsonl",
    }
    if not required <= actual_paths:
        raise ValueError("asset payload is missing runtime files")
    if manifest.get("engine_files_included") is not False:
        raise ValueError("asset manifest does not prohibit engine files")
    return {
        "verified": True,
        "dataset_id": manifest["dataset_id"],
        "dataset_metadata_present": metadata_present,
        "files": payload_result["files"],
        "payload_bytes": payload_result["payload_bytes"],
        "manifest_sha256": manifest["manifest_sha256"],
        "asset_root": str(root),
    }


def build_rollout_assets(
    *,
    workspace_root: str | Path,
    corpus_dir: str | Path,
    baseline_dir: str | Path,
    policy_dirs: Sequence[str | Path],
    output_dir: str | Path,
    dataset_id: str,
    title: str,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    corpus = (workspace / corpus_dir).resolve() if not Path(corpus_dir).is_absolute() else Path(corpus_dir).resolve()
    baseline = (workspace / baseline_dir).resolve() if not Path(baseline_dir).is_absolute() else Path(baseline_dir).resolve()
    policies = [
        (workspace / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
        for path in policy_dirs
    ]
    output = (workspace / output_dir).resolve() if not Path(output_dir).is_absolute() else Path(output_dir).resolve()
    for path in (corpus, baseline, *policies, output.parent):
        try:
            path.resolve().relative_to(workspace)
        except ValueError as error:
            raise ValueError("asset path escapes workspace: %s" % path) from error
    if output.exists():
        raise FileExistsError("refusing to replace asset directory: %s" % output)
    if not dataset_id or "/" not in dataset_id or not title:
        raise ValueError("dataset id and title are required")
    sources = _corpus_sources(corpus, workspace)
    sources.update(path for path in (workspace / "research" / "rl_ptcg").glob("*.py") if path.is_file())
    sources.update((workspace / relative).resolve() for relative in RUNTIME_TOOLS)
    for directory in (baseline, *policies):
        sources.update(path.resolve() for path in _policy_sources(directory))
    metadata = {
        "title": title,
        "id": dataset_id,
        "licenses": [{"name": "other"}],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ptcg_kaggle_assets_", dir=output.parent) as directory:
        temporary = Path(directory)
        stage = temporary / "stage"
        payload = stage / "payload"
        payload.mkdir(parents=True)
        files = _copy_allowlisted(sources, workspace, payload)
        (stage / "dataset-metadata.json").write_text(
            json.dumps(metadata, sort_keys=True, ensure_ascii=True, indent=2) + "\n",
            encoding="ascii", newline="\n",
        )
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "dataset_id": dataset_id,
            "corpus_path": _relative(corpus, workspace),
            "corpus_manifest_sha256": file_sha256(corpus / "manifest.json"),
            "corpus_states_sha256": file_sha256(corpus / "states.jsonl"),
            "baseline_path": _relative(baseline, workspace),
            "policy_paths": sorted(_relative(path, workspace) for path in policies),
            "dataset_metadata_sha256": file_sha256(stage / "dataset-metadata.json"),
            "payload_files_sha256": files,
            "engine_files_included": False,
        }
        manifest["manifest_sha256"] = _self_hash(manifest)
        (stage / "asset_manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, ensure_ascii=True, indent=2) + "\n",
            encoding="ascii", newline="\n",
        )
        try:
            os.replace(stage, output)
        except PermissionError:
            if output.exists():
                raise
            shutil.copytree(stage, output)
    return verify_rollout_assets(output)
