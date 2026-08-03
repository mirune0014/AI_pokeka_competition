from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import stat
import struct
import tarfile
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .config import staging_root


SUBMISSION_ID = "55155015"
MANIFEST_ID = "submission-55155015-v1"
ARCHIVE_SHA256 = "32A7F1F4D469FA2FBAD01E57F0B8284E0CEB51F88253824A8518644D9613E50C"
ENTRY_POINT = "main:agent"
MAX_ARTIFACT_FILES = 512
MAX_ARTIFACT_MEMBERS = 1_024
MAX_ARTIFACT_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_ARTIFACT_MEMBER_BYTES = 256 * 1024 * 1024
MAX_ARTIFACT_TOTAL_BYTES = 512 * 1024 * 1024
REQUIRED_RUNTIME_FILES = frozenset(
    {
        "main.py",
        "deck.csv",
        "cg/__init__.py",
        "cg/api.py",
        "cg/sim.py",
        "cg/utils.py",
        "cg/game.py",
        "cg/cg.dll",
    }
)


@dataclass(frozen=True)
class ManifestFile:
    path: str
    size: int
    sha256: str


TRUSTED_FILES = (
    ManifestFile("main.py", 1_049_690, "6D890336EB50CAA0E26CBD75BE5A2FA94FEB09AC131DCE2AF57200858888AFF8"),
    ManifestFile("deck.csv", 250, "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A"),
    ManifestFile("requirements.txt", 60, "9FF390983B30F2A020B68B5B9F62BB79D253074BD79D677C57D77EC71B951D47"),
    ManifestFile("cg/__init__.py", 0, "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855"),
    ManifestFile("cg/api.py", 26_933, "593F1298E52A635F90F8F505A52113E9AF114F444C293404E37906F18EE06CED"),
    ManifestFile("cg/sim.py", 2_273, "1555F57F5D22BF4C09D70E0E667A916E575E68C9DD1DE9EAD34BA5E7E4968655"),
    ManifestFile("cg/utils.py", 1_970, "60F29665CEE0A88525D6F0383BC45959A6262D16FE35EF380AECE1E0EA13C49B"),
    ManifestFile("cg/game.py", 2_225, "3BD3D4F4A369A11E6D2F5DA9094CF15EBC410A2221835E6417B7CFF4883F1FC2"),
    ManifestFile("cg/cg.dll", 1_525_248, "9EA2B0A751029689BFF3DDCCB5F29A98EDD46961DAD264490ED121EF704FB500"),
    ManifestFile("cg/libcg.so", 1_342_400, "FFD89BF923525A3E6FEB5E6201E96A866C0F456895499ED5C4A566303CAAE67C"),
    ManifestFile("cg/libcg-arm64.so", 1_300_584, "030B4728CE9FB9E90B75830B7CF7236F71859732A05EC4A377078EEE0421BBE5"),
    ManifestFile("cg/libcg.dylib", 1_245_544, "77BB978A8129B094452679E0DAF0DA69593AFDA7331685F4642C0D4A94D39D82"),
)


@dataclass(frozen=True)
class VerificationIssue:
    code: str
    detail: str
    path: str | None = None


@dataclass(frozen=True)
class VerificationReport:
    verified: bool
    submission_id: str | None
    manifest_id: str
    source: str
    source_kind: str
    archive_sha256: str | None
    environment_supported: bool
    environment_fingerprint: dict[str, str]
    issues: tuple[VerificationIssue, ...]
    trust_mode: str = "verified_submission"
    content_sha256: str | None = None
    file_count: int = 0
    total_size: int = 0
    display_name: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ArtifactVerificationError(RuntimeError):
    def __init__(self, report: VerificationReport):
        self.report = report
        super().__init__("artifact verification failed")


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def trusted_manifest() -> dict[str, object]:
    payload = {
        "manifest_version": 1,
        "manifest_id": MANIFEST_ID,
        "submission_id": SUBMISSION_ID,
        "archive_sha256": ARCHIVE_SHA256,
        "entry_point": ENTRY_POINT,
        "required_cwd": ".",
        "python": {"implementation": "CPython", "minimum": "3.10", "bits": 64},
        "files": [asdict(item) for item in TRUSTED_FILES],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return {**payload, "manifest_sha256": sha256_bytes(canonical)}


def environment_fingerprint() -> dict[str, str]:
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_bits": str(struct.calcsize("P") * 8),
    }


def is_supported_environment(fingerprint: dict[str, str] | None = None) -> bool:
    value = fingerprint or environment_fingerprint()
    try:
        major, minor, *_ = (int(part) for part in value["python_version"].split("."))
    except (KeyError, ValueError):
        return False
    machine = value.get("machine", "").lower()
    return (
        value.get("os") == "Windows"
        and value.get("python_implementation") == "CPython"
        and value.get("python_bits") == "64"
        and (major, minor) >= (3, 10)
        and machine in {"amd64", "x86_64"}
    )


def _normal_member_name(name: str) -> str:
    clean = name.replace("\\", "/")
    while clean.startswith("./"):
        clean = clean[2:]
    pure = PurePosixPath(clean)
    if not clean or pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"unsafe archive member: {name!r}")
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    for part in pure.parts:
        base = part.split(".", 1)[0].upper()
        if (
            any(ord(character) < 32 or character in '<>:"|?*' for character in part)
            or part.endswith((" ", "."))
            or base in reserved
        ):
            raise ValueError(f"Windowsで安全に扱えないパスです: {name!r}")
    normalized = pure.as_posix().rstrip("/")
    if not normalized or len(normalized) > 240:
        raise ValueError(f"invalid artifact member path: {name!r}")
    return normalized


def _content_sha256(entries: Iterable[ManifestFile]) -> str:
    payload = {
        "entry_point": ENTRY_POINT,
        "required_cwd": ".",
        "files": [asdict(item) for item in sorted(entries, key=lambda item: item.path)],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return sha256_bytes(canonical)


def _validated_entries(manifest: dict[str, Any]) -> tuple[ManifestFile, ...]:
    if not isinstance(manifest, dict):
        raise ValueError("artifact manifest must be an object")
    if manifest.get("manifest_version") != 1 or manifest.get("entry_point") != ENTRY_POINT:
        raise ValueError("unsupported artifact manifest")
    if manifest.get("required_cwd") != ".":
        raise ValueError("unsupported artifact working directory")
    raw_files = manifest.get("files")
    if not isinstance(raw_files, list) or not 1 <= len(raw_files) <= MAX_ARTIFACT_FILES:
        raise ValueError("artifact manifest file count is invalid")
    entries: list[ManifestFile] = []
    seen: set[str] = set()
    seen_windows: set[str] = set()
    total = 0
    for raw in raw_files:
        if not isinstance(raw, dict) or set(raw) != {"path", "size", "sha256"}:
            raise ValueError("artifact manifest file entry is invalid")
        path = raw.get("path")
        size = raw.get("size")
        digest = raw.get("sha256")
        if (
            not isinstance(path, str)
            or _normal_member_name(path) != path
            or path in seen
            or path.casefold() in seen_windows
        ):
            raise ValueError("artifact manifest path is invalid")
        if type(size) is not int or not 0 <= size <= MAX_ARTIFACT_MEMBER_BYTES:
            raise ValueError("artifact manifest size is invalid")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789ABCDEF" for c in digest):
            raise ValueError("artifact manifest SHA-256 is invalid")
        entries.append(ManifestFile(path, size, digest))
        seen.add(path)
        seen_windows.add(path.casefold())
        total += size
    if total > MAX_ARTIFACT_TOTAL_BYTES:
        raise ValueError("artifact manifest expanded size is too large")
    entries.sort(key=lambda item: item.path)
    manifest_id = manifest.get("manifest_id")
    if manifest_id == MANIFEST_ID:
        if manifest != trusted_manifest():
            raise ValueError("built-in manifest was modified")
    else:
        local_keys = {
            "manifest_version",
            "manifest_id",
            "submission_id",
            "archive_sha256",
            "entry_point",
            "required_cwd",
            "trust_mode",
            "content_sha256",
            "files",
        }
        if set(manifest) != local_keys or manifest.get("submission_id") is not None:
            raise ValueError("local artifact manifest schema is invalid")
        content_hash = _content_sha256(entries)
        if manifest.get("trust_mode") != "local_registered":
            raise ValueError("local artifact trust mode is invalid")
        if manifest.get("content_sha256") != content_hash:
            raise ValueError("local artifact content fingerprint is invalid")
        if manifest_id != f"local-{content_hash[:24]}":
            raise ValueError("local artifact manifest id is invalid")
        archive_hash = manifest.get("archive_sha256")
        if archive_hash is not None and (
            not isinstance(archive_hash, str)
            or len(archive_hash) != 64
            or any(c not in "0123456789ABCDEF" for c in archive_hash)
        ):
            raise ValueError("local artifact archive fingerprint is invalid")
    return tuple(entries)


def manifest_files(manifest: dict[str, Any]) -> tuple[ManifestFile, ...]:
    return _validated_entries(manifest)


def manifest_file_hashes(manifest: dict[str, Any]) -> dict[str, str]:
    return {item.path: item.sha256 for item in _validated_entries(manifest)}


def manifest_trust_mode(manifest: dict[str, Any]) -> str:
    return "verified_submission" if manifest.get("manifest_id") == MANIFEST_ID else "local_registered"


def _is_link_like(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction) and is_junction():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _regular_files(root: Path) -> set[str]:
    result: set[str] = set()
    windows_names: set[str] = set()
    resolved_root = root.resolve()
    total = 0
    member_count = 0
    for path in root.rglob("*"):
        member_count += 1
        if member_count > MAX_ARTIFACT_MEMBERS:
            raise ValueError("artifact contains too many filesystem entries")
        if _is_link_like(path):
            raise ValueError(f"links are not allowed: {path}")
        if not path.is_file():
            continue
        resolved = path.resolve()
        if resolved_root not in resolved.parents:
            raise ValueError(f"artifact file escaped its root: {path}")
        relative = _normal_member_name(path.relative_to(root).as_posix())
        size = path.stat().st_size
        if size > MAX_ARTIFACT_MEMBER_BYTES:
            raise ValueError(f"artifact file is too large: {relative}")
        if relative.casefold() in windows_names:
            raise ValueError(f"Windows上で名前が衝突します: {relative}")
        result.add(relative)
        windows_names.add(relative.casefold())
        total += size
        if len(result) > MAX_ARTIFACT_FILES or total > MAX_ARTIFACT_TOTAL_BYTES:
            raise ValueError("artifact expanded size or file count is too large")
    return result


def _snapshot_directory(root: Path) -> tuple[ManifestFile, ...]:
    names = _regular_files(root)
    entries: list[ManifestFile] = []
    for relative in sorted(names):
        path = root.joinpath(*PurePosixPath(relative).parts)
        size_before = path.stat().st_size
        digest = sha256_file(path)
        size_after = path.stat().st_size
        if size_before != size_after:
            raise ValueError(f"artifact changed while being read: {relative}")
        entries.append(ManifestFile(relative, size_after, digest))
    return tuple(entries)


def _snapshot_archive(archive: Path) -> tuple[tuple[ManifestFile, ...], str]:
    if archive.stat().st_size > MAX_ARTIFACT_ARCHIVE_BYTES:
        raise ValueError("artifact archive is too large")
    archive_digest = sha256_file(archive)
    entries: list[ManifestFile] = []
    seen: set[str] = set()
    seen_windows: set[str] = set()
    total = 0
    member_count = 0
    with tarfile.open(archive, mode="r:gz") as bundle:
        for member in bundle:
            member_count += 1
            if member_count > MAX_ARTIFACT_MEMBERS:
                raise ValueError("archive contains too many members")
            name = _normal_member_name(member.name)
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(f"unsupported archive member type: {member.name!r}")
            if name in seen or name.casefold() in seen_windows:
                raise ValueError(f"duplicate or Windows-colliding archive member: {name!r}")
            if member.size < 0 or member.size > MAX_ARTIFACT_MEMBER_BYTES:
                raise ValueError(f"archive member is too large: {name!r}")
            total += member.size
            if len(seen) + 1 > MAX_ARTIFACT_FILES or total > MAX_ARTIFACT_TOTAL_BYTES:
                raise ValueError("archive expanded size or file count is too large")
            source = bundle.extractfile(member)
            if source is None:
                raise ValueError(f"could not read archive member: {name!r}")
            digest = hashlib.sha256()
            actual_size = 0
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                actual_size += len(chunk)
                digest.update(chunk)
            if actual_size != member.size:
                raise ValueError(f"archive member size changed while reading: {name!r}")
            entries.append(ManifestFile(name, actual_size, digest.hexdigest().upper()))
            seen.add(name)
            seen_windows.add(name.casefold())
    entries.sort(key=lambda item: item.path)
    if sha256_file(archive) != archive_digest:
        raise ValueError("archive changed while being read")
    return tuple(entries), archive_digest


def _extract_safe(archive: Path, destination: Path, entries: Iterable[ManifestFile]) -> None:
    expected_entries = {item.path: item for item in entries}
    expected = set(expected_entries)
    seen: set[str] = set()
    total = 0
    member_count = 0
    with tarfile.open(archive, mode="r:gz") as bundle:
        for member in bundle:
            member_count += 1
            if member_count > MAX_ARTIFACT_MEMBERS:
                raise ValueError("archive contains too many members")
            name = _normal_member_name(member.name)
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(f"unsupported archive member type: {member.name!r}")
            if name not in expected or name in seen:
                raise ValueError(f"unexpected or duplicate archive member: {name!r}")
            expected_item = expected_entries[name]
            if member.size != expected_item.size:
                raise ValueError(f"archive member size mismatch: {name!r}")
            total += member.size
            if total > MAX_ARTIFACT_TOTAL_BYTES:
                raise ValueError("archive expanded size is too large")
            source = bundle.extractfile(member)
            if source is None:
                raise ValueError(f"could not read archive member: {name!r}")
            target = destination.joinpath(*PurePosixPath(name).parts)
            resolved_parent = target.parent.resolve()
            resolved_root = destination.resolve()
            if resolved_root != resolved_parent and resolved_root not in resolved_parent.parents:
                raise ValueError(f"archive member escaped destination: {name!r}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as output:
                shutil.copyfileobj(source, output)
            seen.add(name)
    if seen != expected:
        missing = sorted(expected - seen)
        raise ValueError(f"archive members missing: {missing}")


def _verify_directory(root: Path, entries: Iterable[ManifestFile]) -> list[VerificationIssue]:
    issues: list[VerificationIssue] = []
    expected_entries = {item.path: item for item in entries}
    expected = set(expected_entries)
    try:
        actual = _regular_files(root)
    except (OSError, ValueError) as exc:
        return [VerificationIssue("unsafe_source", str(exc))]
    for extra in sorted(actual - expected):
        issues.append(VerificationIssue("unexpected_file", "登録時になかったファイルです。", extra))
    for missing in sorted(expected - actual):
        issues.append(VerificationIssue("missing_file", "必要なファイルがありません。", missing))
    for relative in sorted(expected & actual):
        item = expected_entries[relative]
        path = root.joinpath(*PurePosixPath(relative).parts)
        try:
            size = path.stat().st_size
            if size != item.size:
                issues.append(VerificationIssue("size_mismatch", f"expected {item.size}, got {size}", relative))
                continue
            digest = sha256_file(path)
        except OSError as exc:
            issues.append(VerificationIssue("read_error", str(exc), relative))
            continue
        if digest != item.sha256:
            issues.append(VerificationIssue("hash_mismatch", f"expected {item.sha256}, got {digest}", relative))
    return issues


def _make_local_manifest(entries: tuple[ManifestFile, ...], archive_sha256: str | None) -> dict[str, Any]:
    content_hash = _content_sha256(entries)
    return {
        "manifest_version": 1,
        "manifest_id": f"local-{content_hash[:24]}",
        "submission_id": None,
        "archive_sha256": archive_sha256,
        "entry_point": ENTRY_POINT,
        "required_cwd": ".",
        "trust_mode": "local_registered",
        "content_sha256": content_hash,
        "files": [asdict(item) for item in entries],
    }


def verify_artifact(
    source: str | os.PathLike[str], manifest: dict[str, Any] | None = None
) -> VerificationReport:
    source_path = Path(source).expanduser().resolve()
    selected = trusted_manifest() if manifest is None else manifest
    fingerprint = environment_fingerprint()
    supported = is_supported_environment(fingerprint)
    issues: list[VerificationIssue] = []
    kind = "missing"
    archive_digest: str | None = None
    try:
        entries = _validated_entries(selected)
    except ValueError as exc:
        entries = ()
        issues.append(VerificationIssue("invalid_manifest", str(exc)))
    expected_names = {item.path for item in entries}
    for missing in sorted(REQUIRED_RUNTIME_FILES - expected_names):
        issues.append(VerificationIssue("missing_runtime_file", "実行に必要なファイルが登録されていません。", missing))
    if not source_path.exists():
        issues.append(VerificationIssue("source_missing", "エージェントが見つかりません。", str(source_path)))
    elif source_path.is_dir():
        kind = "directory"
        if entries:
            issues.extend(_verify_directory(source_path, entries))
    elif source_path.is_file():
        kind = "archive"
        try:
            if source_path.stat().st_size > MAX_ARTIFACT_ARCHIVE_BYTES:
                raise ValueError("artifact archive is too large")
            archive_digest = sha256_file(source_path)
            expected_archive = selected.get("archive_sha256") if isinstance(selected, dict) else None
            if expected_archive is not None and archive_digest != expected_archive:
                issues.append(
                    VerificationIssue(
                        "archive_hash_mismatch",
                        f"expected {expected_archive}, got {archive_digest}",
                        str(source_path),
                    )
                )
            elif entries:
                with tempfile.TemporaryDirectory(prefix="ptcg-verify-") as temporary:
                    root = Path(temporary)
                    _extract_safe(source_path, root, entries)
                    issues.extend(_verify_directory(root, entries))
                if sha256_file(source_path) != archive_digest:
                    issues.append(
                        VerificationIssue(
                            "source_changed",
                            "アーカイブが検証中に変更されました。",
                            str(source_path),
                        )
                    )
        except (OSError, tarfile.TarError, ValueError) as exc:
            issues.append(VerificationIssue("archive_invalid", str(exc), str(source_path)))
    else:
        issues.append(VerificationIssue("source_type", "通常ファイルまたはディレクトリではありません。", str(source_path)))
    if not supported:
        issues.append(VerificationIssue("unsupported_environment", "Windows x64 / CPython 3.10 以上が必要です。"))
    manifest_id = selected.get("manifest_id", "") if isinstance(selected, dict) else ""
    submission_id = selected.get("submission_id") if isinstance(selected, dict) else None
    content_hash = _content_sha256(entries) if entries else None
    return VerificationReport(
        verified=not issues,
        submission_id=submission_id if isinstance(submission_id, str) else None,
        manifest_id=manifest_id if isinstance(manifest_id, str) else "",
        source=str(source_path),
        source_kind=kind,
        archive_sha256=archive_digest,
        environment_supported=supported,
        environment_fingerprint=fingerprint,
        issues=tuple(issues),
        trust_mode=manifest_trust_mode(selected) if entries else "unregistered",
        content_sha256=content_hash,
        file_count=len(entries),
        total_size=sum(item.size for item in entries),
        display_name=source_path.name,
    )


def register_local_artifact(
    source: str | os.PathLike[str],
) -> tuple[dict[str, Any], VerificationReport]:
    source_path = Path(source).expanduser().resolve()
    fingerprint = environment_fingerprint()
    supported = is_supported_environment(fingerprint)
    try:
        if not source_path.exists():
            raise FileNotFoundError("エージェントが見つかりません。")
        if source_path.is_dir():
            kind = "directory"
            entries = _snapshot_directory(source_path)
            archive_digest = None
        elif source_path.is_file():
            kind = "archive"
            entries, archive_digest = _snapshot_archive(source_path)
        else:
            raise ValueError("通常ファイルまたはディレクトリではありません。")
        if entries == tuple(sorted(TRUSTED_FILES, key=lambda item: item.path)) and (
            kind == "directory" or archive_digest == ARCHIVE_SHA256
        ):
            manifest = trusted_manifest()
        else:
            manifest = _make_local_manifest(entries, archive_digest)
        return manifest, verify_artifact(source_path, manifest)
    except (OSError, tarfile.TarError, ValueError) as exc:
        report = VerificationReport(
            verified=False,
            submission_id=None,
            manifest_id="",
            source=str(source_path),
            source_kind="missing" if not source_path.exists() else "invalid",
            archive_sha256=None,
            environment_supported=supported,
            environment_fingerprint=fingerprint,
            issues=(VerificationIssue("registration_failed", str(exc), str(source_path)),),
            trust_mode="unregistered",
            display_name=source_path.name,
        )
        return {}, report


def stage_artifact(
    source: str | os.PathLike[str],
    match_id: str,
    *,
    root: Path | None = None,
    manifest: dict[str, Any] | None = None,
) -> Path:
    selected = trusted_manifest() if manifest is None else manifest
    report = verify_artifact(source, selected)
    if not report.verified:
        raise ArtifactVerificationError(report)
    entries = _validated_entries(selected)
    stage_base = (root or staging_root()).resolve()
    stage_base.mkdir(parents=True, exist_ok=True)
    destination = (stage_base / match_id).resolve()
    if destination.parent != stage_base:
        raise ValueError("invalid match id")
    if destination.exists():
        raise FileExistsError(destination)
    destination.mkdir(parents=False)
    source_path = Path(source).expanduser().resolve()
    try:
        if source_path.is_dir():
            for item in entries:
                src = source_path.joinpath(*PurePosixPath(item.path).parts)
                dst = destination.joinpath(*PurePosixPath(item.path).parts)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
        else:
            _extract_safe(source_path, destination, entries)
        staged_report = verify_artifact(destination, selected)
        if not staged_report.verified:
            raise ArtifactVerificationError(staged_report)
        return destination
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def cleanup_stage(path: Path, *, root: Path | None = None) -> None:
    stage_base = (root or staging_root()).resolve()
    target = path.resolve()
    if target.parent != stage_base or target == stage_base:
        raise ValueError("refusing to remove path outside staging root")
    shutil.rmtree(target, ignore_errors=False)


def cleanup_stale_staging(
    *,
    root: Path | None = None,
    max_age_seconds: float = 24 * 60 * 60,
    now: float | None = None,
) -> tuple[Path, ...]:
    if max_age_seconds < 0:
        raise ValueError("max_age_seconds must be non-negative")
    stage_base = (root or staging_root()).resolve()
    if not stage_base.exists():
        return ()
    current_time = time.time() if now is None else now
    removed: list[Path] = []
    try:
        children = tuple(stage_base.iterdir())
    except OSError:
        return ()
    for child in children:
        try:
            if _is_link_like(child) or not child.is_dir():
                continue
            target = child.resolve()
            if target.parent != stage_base or target == stage_base:
                continue
            age = current_time - child.stat().st_mtime
            if age < max_age_seconds:
                continue
            shutil.rmtree(target, ignore_errors=False)
            removed.append(target)
        except OSError:
            continue
    return tuple(removed)


def deck_hash(deck: Iterable[int]) -> str:
    payload = "".join(f"{int(card)}\n" for card in deck).encode("ascii")
    return sha256_bytes(payload)
