from __future__ import annotations

import gzip
import importlib.util
import io
import tarfile
from pathlib import Path

import pytest


_BUILDER_PATH = (
    Path(__file__).resolve().parents[2]
    / "infrastructure/tools/build_mega_lucario_package.py"
)
_SPEC = importlib.util.spec_from_file_location("mega_lucario_package_builder", _BUILDER_PATH)
assert _SPEC is not None and _SPEC.loader is not None
builder = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(builder)


def _unsafe_tar(*members: tarfile.TarInfo) -> bytes:
    raw = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            for member in members:
                payload = b"x" if member.isfile() else b""
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))
    return raw.getvalue()


def test_deterministic_tar_contains_only_exact_regular_files() -> None:
    files = {"main.py": b"entry\n", "cg/api.py": b"api\n"}

    first = builder._build_tar_gz(files)
    second = builder._build_tar_gz(files)

    assert first == second
    assert builder._read_safe_regular_archive(first) == files
    with tarfile.open(fileobj=io.BytesIO(first), mode="r:gz") as archive:
        members = archive.getmembers()
    assert [member.name for member in members] == sorted(files)
    assert all(member.isfile() for member in members)
    assert all(member.mtime == 0 and member.uid == 0 and member.gid == 0 for member in members)


def test_safe_tar_validation_rejects_unsafe_duplicate_and_link_members() -> None:
    for name in ("/absolute", "../traversal", "C:/drive", "bad\\separator"):
        with pytest.raises(ValueError):
            builder._validate_member_name(name)

    duplicate_a = tarfile.TarInfo("same.py")
    duplicate_b = tarfile.TarInfo("same.py")
    with pytest.raises(ValueError, match="duplicate"):
        builder._read_safe_regular_archive(_unsafe_tar(duplicate_a, duplicate_b))

    link = tarfile.TarInfo("link.py")
    link.type = tarfile.SYMTYPE
    link.linkname = "main.py"
    with pytest.raises(ValueError, match="links are forbidden"):
        builder._read_safe_regular_archive(_unsafe_tar(link))
