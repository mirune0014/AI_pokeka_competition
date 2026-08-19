from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


OFFICIAL_ARCHIVE_SHA256 = (
    "6fc2e64adac2a308b19b3b3791a307106b3c84621bd3b4f4dfb099838abbd907"
)
EXPECTED_CG_TREE_SHA256 = (
    "4a8df9388d9bc6b6d3d29833d20f4361ebea9c364a3bf0da20e60897bfec1b54"
)
EXPECTED_REGISTRY_DIGEST = (
    "319cdc86b309648169f9fdbb3a17b369b8e77df865d6a99537c36edebea72427"
)
EXPECTED_CATALOG_SHA256 = (
    "35499c8fefcd1152b20eb3618c33b8361c5589a2554eab9d33c003a08b0e03fc"
)
EXPECTED_ATTACK_CATALOG_SHA256 = (
    "3c73310134657165c0633895f99a52b2a8dcf99c7c22659e9e6687e82a4df271"
)

CG_ALLOWLIST = (
    "cg/__init__.py",
    "cg/api.py",
    "cg/cg.dll",
    "cg/game.py",
    "cg/libcg-arm64.so",
    "cg/libcg.dylib",
    "cg/libcg.so",
    "cg/sim.py",
    "cg/utils.py",
)

RUNTIME_SOURCE_NAMES = (
    "__init__.py",
    "attack_outcomes.py",
    "card_meta.py",
    "certificates.py",
    "damage.py",
    "fallback.py",
    "features.py",
    "main.py",
    "public_effects.py",
    "resolver.py",
    "resource_ledger.py",
    "routes.py",
    "state_view.py",
    "telemetry.py",
    "transactions.py",
)

INNER_ARCHIVE_NAME = "submission_mega_lucario_rule_agent_20260805.tar.gz"
OUTER_ARCHIVE_NAME = "mega_lucario_audit_20260805.zip"

ROOT_WRAPPER = """\
from __future__ import annotations

from pathlib import Path
import sys


_candidates = []
try:
    _candidates.append(Path(__file__).resolve().parent)
except NameError:
    pass
_candidates.append(Path("/kaggle_simulations/agent"))
_candidates.extend(Path(value) for value in sys.path if value)
_ROOT = next(
    (
        candidate.resolve()
        for candidate in _candidates
        if (candidate / "mega_lucario_agent" / "main.py").is_file()
        and (candidate / "cg" / "api.py").is_file()
    ),
    None,
)
if _ROOT is None:
    raise ImportError("packaged Mega Lucario runtime root was not found")
_root_text = str(_ROOT)
while _root_text in sys.path:
    sys.path.remove(_root_text)
sys.path.insert(0, _root_text)

from mega_lucario_agent import main as _policy

_DECK = tuple(
    int(row)
    for row in (_ROOT / "deck.csv").read_text(encoding="utf-8-sig").splitlines()
    if row.strip()
)
if len(_DECK) != 60:
    raise RuntimeError("packaged deck.csv must contain exactly 60 cards")
if _DECK != tuple(_policy._FIXED_DECK):
    raise RuntimeError("packaged deck.csv differs from policy _FIXED_DECK")
agent = _policy.agent
if not callable(agent):
    raise RuntimeError("packaged policy agent is not callable")

__all__ = ["agent"]
"""


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_bytes(value: Any, *, pretty: bool = False) -> bytes:
    if pretty:
        text = json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    else:
        text = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    return (text + "\n").encode("utf-8")


def _tree_rows(files: Mapping[str, bytes]) -> list[dict[str, Any]]:
    return [
        {
            "bytes": len(files[path]),
            "path": path,
            "sha256": _sha256_bytes(files[path]),
        }
        for path in sorted(files)
    ]


def _tree_hash(files: Mapping[str, bytes]) -> str:
    rows = _tree_rows(files)
    payload = json.dumps(
        rows,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return _sha256_bytes(payload)


def _validate_member_name(name: str) -> str:
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("archive member name is invalid")
    if len(name) >= 2 and name[1] == ":":
        raise ValueError("absolute archive member is forbidden: {0}".format(name))
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError("unsafe archive member: {0}".format(name))
    normalized = path.as_posix()
    if normalized != name.rstrip("/"):
        raise ValueError("non-canonical archive member: {0}".format(name))
    return normalized


def _validated_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    seen: set[str] = set()
    for member in members:
        normalized = _validate_member_name(member.name)
        if normalized in seen:
            raise ValueError("duplicate archive member: {0}".format(normalized))
        seen.add(normalized)
        if member.issym() or member.islnk():
            raise ValueError("archive links are forbidden: {0}".format(normalized))
        if not member.isfile() and not member.isdir():
            raise ValueError("archive special member is forbidden: {0}".format(normalized))
    return members


def _extract_official_cg(archive_path: Path) -> dict[str, bytes]:
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    actual_archive_hash = _sha256_file(archive_path)
    if actual_archive_hash != OFFICIAL_ARCHIVE_SHA256:
        raise ValueError(
            "official cg archive SHA-256 mismatch: {0}".format(actual_archive_hash)
        )
    extracted: dict[str, bytes] = {}
    with tarfile.open(archive_path, "r:gz") as archive:
        members = _validated_members(archive)
        by_name = {
            _validate_member_name(member.name): member
            for member in members
        }
        for path in CG_ALLOWLIST:
            member = by_name.get(path)
            if member is None or not member.isfile():
                raise ValueError("official cg member missing or non-regular: {0}".format(path))
            handle = archive.extractfile(member)
            if handle is None:
                raise ValueError("official cg member unreadable: {0}".format(path))
            payload = handle.read()
            if len(payload) != member.size:
                raise ValueError("official cg member size mismatch: {0}".format(path))
            extracted[path] = payload
    if tuple(sorted(extracted)) != tuple(sorted(CG_ALLOWLIST)):
        raise AssertionError("official cg extraction left the exact allowlist")
    actual_tree_hash = _tree_hash(extracted)
    if actual_tree_hash != EXPECTED_CG_TREE_SHA256:
        raise ValueError("official cg tree hash mismatch: {0}".format(actual_tree_hash))
    return extracted


def _source_files(source_dir: Path) -> dict[str, bytes]:
    if not source_dir.is_dir():
        raise FileNotFoundError(source_dir)
    files: dict[str, bytes] = {}
    for name in RUNTIME_SOURCE_NAMES:
        path = source_dir / name
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(path)
        files["mega_lucario_agent/{0}".format(name)] = path.read_bytes()
    deck_path = source_dir / "deck.csv"
    if not deck_path.is_file() or deck_path.is_symlink():
        raise FileNotFoundError(deck_path)
    deck_payload = deck_path.read_bytes()
    deck_rows = [row for row in deck_payload.decode("utf-8-sig").splitlines() if row.strip()]
    if len(deck_rows) != 60 or any(not row.isdigit() for row in deck_rows):
        raise ValueError("source deck.csv must contain 60 integer rows")
    files["deck.csv"] = deck_payload
    return files


def _tar_info(path: str, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(path)
    info.size = size
    info.mode = 0o644
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    return info


def _build_tar_gz(files: Mapping[str, bytes]) -> bytes:
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
        with tarfile.open(
            fileobj=compressed,
            mode="w",
            format=tarfile.USTAR_FORMAT,
        ) as archive:
            for path in sorted(files):
                _validate_member_name(path)
                payload = files[path]
                archive.addfile(_tar_info(path, len(payload)), io.BytesIO(payload))
    return raw.getvalue()


def _read_safe_regular_archive(payload: bytes) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        members = _validated_members(archive)
        if any(not member.isfile() for member in members):
            raise ValueError("submission archive may contain regular files only")
        for member in members:
            path = _validate_member_name(member.name)
            handle = archive.extractfile(member)
            if handle is None:
                raise ValueError("submission member unreadable: {0}".format(path))
            files[path] = handle.read()
    return files


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _build_zip(entries: Mapping[str, bytes]) -> bytes:
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(entries):
            archive.writestr(
                _zip_info(path),
                entries[path],
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
    return raw.getvalue()


def _verify_zip(payload: bytes, expected_entries: Mapping[str, bytes]) -> None:
    with zipfile.ZipFile(io.BytesIO(payload), mode="r") as archive:
        infos = archive.infolist()
        if len(infos) != 4 or [info.filename for info in infos] != sorted(expected_entries):
            raise AssertionError("outer zip must contain exactly four sorted entries")
        if any(info.is_dir() for info in infos):
            raise AssertionError("outer zip may not contain directories")
        actual = {info.filename: archive.read(info) for info in infos}
    if actual != dict(expected_entries):
        raise AssertionError("outer zip bytes differ from expected sidecars")


def _git_value(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def _clean_env() -> dict[str, str]:
    allowed = ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")
    return {name: os.environ[name] for name in allowed if name in os.environ}


IMPORT_VERIFICATION = r"""
import hashlib
import importlib.util
import json
import platform
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
assert importlib.util.find_spec("cg") is None
sys.path.insert(0, str(root))
entry_path = root / "main.py"
spec = importlib.util.spec_from_file_location("submission_entrypoint", entry_path)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert callable(module.agent)
deck = [int(row) for row in (root / "deck.csv").read_text(encoding="utf-8-sig").splitlines() if row.strip()]
assert len(deck) == 60
assert module.agent({"select": None}) == deck
from mega_lucario_agent import main as policy
registry = policy._RUNTIME._get_registry()
import cg
import cg.api
import cg.sim
lib_path = Path(cg.sim.lib_path).resolve()
assert lib_path.is_file()
for loaded in (Path(cg.__file__).resolve(), Path(cg.api.__file__).resolve(), Path(policy.__file__).resolve(), lib_path):
    loaded.relative_to(root)
print(json.dumps({
    "python_implementation": platform.python_implementation(),
    "python_version": platform.python_version(),
    "sys_version": sys.version.replace("\r", " ").replace("\n", " "),
    "platform": platform.platform(),
    "registry_digest": registry.digest,
    "catalog_sha256": registry.catalog_sha256,
    "attack_catalog_sha256": registry.attack_catalog_sha256,
    "cg_module_path": Path(cg.__file__).resolve().relative_to(root).as_posix(),
    "cg_api_path": Path(cg.api.__file__).resolve().relative_to(root).as_posix(),
    "policy_module_path": Path(policy.__file__).resolve().relative_to(root).as_posix(),
    "selected_cg_lib_path": lib_path.relative_to(root).as_posix(),
    "selected_cg_binary_sha256": hashlib.sha256(lib_path.read_bytes()).hexdigest(),
}, sort_keys=True))
"""


RAW_EXEC_VERIFICATION = r"""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
source = (root / "main.py").read_text(encoding="utf-8")
scope = {"__name__": "submission_raw_exec"}
exec(compile(source, "/kaggle_simulations/agent/main.py", "exec"), scope)
callables = [value for value in scope.values() if callable(value)]
assert callable(scope.get("agent"))
assert callables[-1] is scope["agent"]
deck = [int(row) for row in (root / "deck.csv").read_text(encoding="utf-8-sig").splitlines() if row.strip()]
assert scope["agent"]({"select": None}) == deck
"""


def _run_checked(
    command: list[str],
    *,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=_clean_env(),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(
            "verification subprocess failed:\n{0}{1}".format(
                result.stdout,
                result.stderr,
            )
        )
    return result


def _verify_inner_archive(
    payload: bytes,
    expected_files: Mapping[str, bytes],
    verification_python: Path,
) -> dict[str, Any]:
    actual = _read_safe_regular_archive(payload)
    if actual != dict(expected_files):
        raise AssertionError("clean re-extraction hashes differ from packaged bytes")
    if len(actual) != 26 or set(actual) != set(expected_files):
        raise AssertionError("submission archive must contain exactly 26 files")
    if any("__pycache__" in PurePosixPath(path).parts or path.endswith(".pyc") for path in actual):
        raise AssertionError("cache artifact entered submission archive")
    with tempfile.TemporaryDirectory(prefix="mega-lucario-gate-c-") as temp_name:
        temp_root = Path(temp_name)
        unpack = temp_root / "unpack"
        empty_cwd = temp_root / "empty-cwd"
        unpack.mkdir()
        empty_cwd.mkdir()
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
            members = _validated_members(archive)
            archive.extractall(unpack, members=members, filter="data")
        if any(path.is_symlink() for path in unpack.rglob("*")):
            raise AssertionError("symlink appeared after clean extraction")
        imported = _run_checked(
            [
                str(verification_python),
                "-I",
                "-c",
                IMPORT_VERIFICATION,
                str(unpack),
            ],
            cwd=empty_cwd,
        )
        raw_exec = _run_checked(
            [
                str(verification_python),
                "-I",
                "-c",
                RAW_EXEC_VERIFICATION,
                str(unpack),
            ],
            cwd=empty_cwd,
        )
        if raw_exec.stdout.strip():
            raise AssertionError("raw exec verification emitted unexpected output")
        result = json.loads(imported.stdout.strip())
    expected = {
        "registry_digest": EXPECTED_REGISTRY_DIGEST,
        "catalog_sha256": EXPECTED_CATALOG_SHA256,
        "attack_catalog_sha256": EXPECTED_ATTACK_CATALOG_SHA256,
        "python_implementation": "CPython",
        "python_version": "3.11.6",
    }
    for name, value in expected.items():
        if result.get(name) != value:
            raise AssertionError(
                "Gate C {0} mismatch: {1!r}".format(name, result.get(name))
            )
    return result


def _parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Build the deterministic self-contained Mega Lucario package."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=repo_root / "mega_lucario_rule_agent",
    )
    parser.add_argument("--official-cg-archive", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--verification-python",
        type=Path,
        default=Path(sys.executable),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if sys.version_info < (3, 10):
        raise RuntimeError("package builder requires Python 3.10 or newer")
    repo_root = Path(__file__).resolve().parents[2]
    source_dir = args.source_dir.resolve()
    official_archive = args.official_cg_archive.resolve()
    output_dir = args.output_dir.resolve()
    verification_python = args.verification_python.resolve()
    if output_dir.exists():
        raise FileExistsError("output directory already exists: {0}".format(output_dir))
    if not verification_python.is_file():
        raise FileNotFoundError(verification_python)

    cg_files = _extract_official_cg(official_archive)
    source_files = _source_files(source_dir)
    final_files = {
        "main.py": ROOT_WRAPPER.encode("utf-8"),
        **cg_files,
        **source_files,
    }
    if len(final_files) != 26:
        raise AssertionError("runtime closure must contain exactly 26 files")
    inner_payload = _build_tar_gz(final_files)
    gate_c = _verify_inner_archive(
        inner_payload,
        final_files,
        verification_python,
    )

    source_commit = _git_value(repo_root, "rev-parse", "HEAD")
    source_branch = _git_value(repo_root, "branch", "--show-current")
    worktree_clean = not bool(_git_value(repo_root, "status", "--porcelain"))
    inner_hash = _sha256_bytes(inner_payload)
    manifest = {
        "schema_version": "mega_lucario_self_contained_package_v1",
        "source": {
            "branch": source_branch,
            "commit": source_commit,
            "builder_commit": source_commit,
            "worktree_clean": worktree_clean,
            "runtime_directory": "mega_lucario_rule_agent",
            "tree_sha256": _tree_hash(source_files),
            "files": _tree_rows(source_files),
        },
        "official_cg": {
            "archive_name": official_archive.name,
            "archive_sha256": _sha256_file(official_archive),
            "tree_sha256": _tree_hash(cg_files),
            "files": _tree_rows(cg_files),
        },
        "runtime": {
            "file_count": len(final_files),
            "tree_sha256": _tree_hash(final_files),
            "files": _tree_rows(final_files),
            "inner_archive_name": INNER_ARCHIVE_NAME,
            "inner_archive_sha256": inner_hash,
            "inner_archive_bytes": len(inner_payload),
        },
        "engine": {
            "semantic_version": None,
            "semantic_version_reason": "NOT_EXPOSED_BY_OFFICIAL_CG",
            "selected_cg_lib_path": gate_c["selected_cg_lib_path"],
            "selected_cg_binary_sha256": gate_c["selected_cg_binary_sha256"],
        },
    }
    verification = {
        "schema_version": "mega_lucario_package_verification_v1",
        "passed": True,
        "checks": {
            "official_archive_sha256": True,
            "official_cg_exact_allowlist": True,
            "official_cg_tree_sha256": True,
            "safe_paths_no_duplicates_links_or_specials": True,
            "inner_regular_file_count": 26,
            "clean_reextract_hashes_match": True,
            "no_cache_or_symlink": True,
            "arbitrary_empty_cwd": True,
            "ambient_cg_absent": True,
            "root_import": True,
            "raw_exec_without_file": True,
            "agent_callable": True,
            "deck_rows": 60,
            "deck_callback_matches": True,
            "registry_initialized": True,
            "loaded_paths_within_unpack": True,
            "outer_entry_count": 4,
        },
        "environment": gate_c,
        "expected": {
            "registry_digest": EXPECTED_REGISTRY_DIGEST,
            "catalog_sha256": EXPECTED_CATALOG_SHA256,
            "attack_catalog_sha256": EXPECTED_ATTACK_CATALOG_SHA256,
            "cg_tree_sha256": EXPECTED_CG_TREE_SHA256,
        },
        "actual": {
            "registry_digest": gate_c["registry_digest"],
            "catalog_sha256": gate_c["catalog_sha256"],
            "attack_catalog_sha256": gate_c["attack_catalog_sha256"],
            "cg_tree_sha256": _tree_hash(cg_files),
            "source_tree_sha256": _tree_hash(source_files),
            "final_tree_sha256": _tree_hash(final_files),
            "inner_archive_sha256": inner_hash,
        },
    }
    manifest_payload = _json_bytes(manifest, pretty=True)
    verification_payload = _json_bytes(verification, pretty=True)
    sums = {
        INNER_ARCHIVE_NAME: inner_hash,
        "PACKAGE_MANIFEST.json": _sha256_bytes(manifest_payload),
        "PACKAGE_VERIFICATION.json": _sha256_bytes(verification_payload),
    }
    sums_payload = "".join(
        "{0}  {1}\n".format(sums[path], path)
        for path in sorted(sums)
    ).encode("utf-8")
    outer_entries = {
        INNER_ARCHIVE_NAME: inner_payload,
        "PACKAGE_MANIFEST.json": manifest_payload,
        "PACKAGE_VERIFICATION.json": verification_payload,
        "SHA256SUMS.txt": sums_payload,
    }
    outer_payload = _build_zip(outer_entries)
    _verify_zip(outer_payload, outer_entries)

    output_dir.mkdir(parents=True)
    paths = {
        INNER_ARCHIVE_NAME: output_dir / INNER_ARCHIVE_NAME,
        "PACKAGE_MANIFEST.json": output_dir / "PACKAGE_MANIFEST.json",
        "PACKAGE_VERIFICATION.json": output_dir / "PACKAGE_VERIFICATION.json",
        "SHA256SUMS.txt": output_dir / "SHA256SUMS.txt",
        OUTER_ARCHIVE_NAME: output_dir / OUTER_ARCHIVE_NAME,
    }
    for name, payload in {
        INNER_ARCHIVE_NAME: inner_payload,
        "PACKAGE_MANIFEST.json": manifest_payload,
        "PACKAGE_VERIFICATION.json": verification_payload,
        "SHA256SUMS.txt": sums_payload,
        OUTER_ARCHIVE_NAME: outer_payload,
    }.items():
        paths[name].write_bytes(payload)
    outer_hash = _sha256_bytes(outer_payload)
    outer_hash_path = output_dir / "OUTER_ZIP_SHA256.txt"
    outer_hash_path.write_text(
        "{0}  {1}\n".format(outer_hash, OUTER_ARCHIVE_NAME),
        encoding="utf-8",
        newline="\n",
    )
    result = {
        "output_dir": str(output_dir),
        "outer_zip": str(paths[OUTER_ARCHIVE_NAME]),
        "outer_zip_sha256": outer_hash,
        "inner_archive": str(paths[INNER_ARCHIVE_NAME]),
        "inner_archive_sha256": inner_hash,
        "manifest": str(paths["PACKAGE_MANIFEST.json"]),
        "manifest_sha256": sums["PACKAGE_MANIFEST.json"],
        "verification": str(paths["PACKAGE_VERIFICATION.json"]),
        "verification_sha256": sums["PACKAGE_VERIFICATION.json"],
        "sha256sums": str(paths["SHA256SUMS.txt"]),
        "outer_hash_sidecar": str(outer_hash_path),
        "file_count": len(final_files),
        "final_tree_sha256": _tree_hash(final_files),
        "cg_tree_sha256": _tree_hash(cg_files),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
