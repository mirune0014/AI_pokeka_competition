from __future__ import annotations

import argparse
import codecs
import gzip
import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath


KAGGLE_ENTRYPOINT = """\
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys


try:
    _ROOT = Path(__file__).resolve().parent
except NameError:
    _ROOT = Path(sys.path[-1])
_SOURCE = _ROOT / "_policy_main.py"
_root_text = str(_ROOT)
if _root_text not in sys.path:
    sys.path.insert(0, _root_text)

_previous_cwd = Path.cwd()
try:
    os.chdir(_ROOT)
    _spec = importlib.util.spec_from_file_location(
        "_alakazam_v1_fix5_policy_source",
        _SOURCE,
    )
    if _spec is None or _spec.loader is None:
        raise ImportError(f"Could not load {_SOURCE}")
    _source_module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_source_module)
finally:
    os.chdir(_previous_cwd)

_DECK = tuple(int(card_id) for card_id in _source_module._parent.my_deck)
if len(_DECK) != 60:
    raise ValueError(f"Packaged policy deck has {len(_DECK)} cards, expected 60")


def agent(obs):
    select = (
        obs.get("select")
        if isinstance(obs, dict)
        else getattr(obs, "select", None)
    )
    if select is None:
        return list(_DECK)
    previous_cwd = Path.cwd()
    try:
        os.chdir(_ROOT)
        return _source_module.agent(obs)
    finally:
        os.chdir(previous_cwd)


__all__ = ["agent"]
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def safe_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or member.issym() or member.islnk():
            raise ValueError(f"unsafe template member: {member.name}")
    return members


def source_files(source: Path) -> list[Path]:
    files = sorted(
        path
        for path in source.glob("*.py")
        if not path.name.startswith("test")
    )
    files.append(source / "deck.csv")
    missing = [path for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError(", ".join(str(path) for path in missing))
    return files


def copy_source_file(source: Path, destination: Path) -> bool:
    """Copy one source file, removing a UTF-8 BOM from Python source.

    Kaggle reads ``main.py`` as text and passes that string directly to
    ``compile()``.  Unlike Python's byte-oriented import loader, that path does
    not consume a leading U+FEFF, so a UTF-8 BOM causes validation to fail
    before the agent is imported.
    """

    payload = source.read_bytes()
    removed_bom = source.suffix == ".py" and payload.startswith(codecs.BOM_UTF8)
    if removed_bom:
        payload = payload[len(codecs.BOM_UTF8) :]
    destination.write_bytes(payload)
    return removed_bom


def normalized_tarinfo(path: Path, arcname: str) -> tarfile.TarInfo:
    info = tarfile.TarInfo(arcname)
    stat = path.stat()
    info.size = stat.st_size
    info.mode = 0o644
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    return info


def build_archive(stage: Path, archive_path: Path) -> None:
    paths = sorted(
        (path for path in stage.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(stage).as_posix(),
    )
    with archive_path.open("wb") as raw:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw,
            mtime=0,
        ) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                directories = sorted(
                    {
                        parent
                        for path in paths
                        for parent in path.relative_to(stage).parents
                        if parent != Path(".")
                    },
                    key=lambda path: path.as_posix(),
                )
                for directory in directories:
                    info = tarfile.TarInfo(directory.as_posix().rstrip("/") + "/")
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    archive.addfile(info)
                for path in paths:
                    arcname = path.relative_to(stage).as_posix()
                    with path.open("rb") as handle:
                        archive.addfile(normalized_tarinfo(path, arcname), handle)


def verify_archive(archive_path: Path, expected: dict[str, dict[str, object]]) -> None:
    with tempfile.TemporaryDirectory(prefix="alakazam-package-verify-") as temp_name:
        extracted = Path(temp_name)
        with tarfile.open(archive_path, "r:gz") as archive:
            members = safe_members(archive)
            archive.extractall(extracted, members=members)
        actual = {
            path.relative_to(extracted).as_posix(): {
                "sha256": sha256(path),
                "size": path.stat().st_size,
            }
            for path in extracted.rglob("*")
            if path.is_file()
        }
        if actual != expected:
            raise AssertionError("re-extracted archive does not match staged files")
        deck_rows = [
            row
            for row in (extracted / "deck.csv").read_text(
                encoding="utf-8-sig"
            ).splitlines()
            if row.strip()
        ]
        if len(deck_rows) != 60:
            raise AssertionError(f"deck row count is {len(deck_rows)}, expected 60")
        if not (extracted / "planner_deck_adaptation_v1.py").is_file():
            raise AssertionError("runtime-certified v1 planner is missing")
        if not (extracted / "_policy_main.py").is_file():
            raise AssertionError("packaged policy source is missing")
        for path in extracted.glob("*.py"):
            payload = path.read_bytes()
            if payload.startswith(codecs.BOM_UTF8):
                raise AssertionError(f"UTF-8 BOM remains in Python source: {path}")
            compile(payload.decode("utf-8"), str(path), "exec")
        entrypoint_path = extracted / "main.py"
        entrypoint_check = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from pathlib import Path\n"
                    "import sys\n"
                    "path = Path(sys.argv[1]).resolve()\n"
                    "raw = path.read_text(encoding='utf-8')\n"
                    "env = {}\n"
                    "sys.path.append(str(path.parent))\n"
                    "try:\n"
                    "    exec(compile(raw, '/kaggle_simulations/agent/main.py',"
                    " 'exec'), env)\n"
                    "finally:\n"
                    "    sys.path.pop()\n"
                    "callables = [v for v in env.values() if callable(v)]\n"
                    "entrypoint = env.get('agent')\n"
                    "assert callable(entrypoint)\n"
                    "assert callables and callables[-1] is entrypoint\n"
                    "expected_deck = [int(row) for row in"
                    " (path.parent / 'deck.csv').read_text("
                    "encoding='utf-8-sig').splitlines() if row.strip()]\n"
                    "assert len(expected_deck) == 60\n"
                    "assert entrypoint({'select': None}) == expected_deck\n"
                ),
                str(entrypoint_path),
            ],
            cwd=extracted,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if entrypoint_check.returncode != 0:
            raise AssertionError(
                "Kaggle-style entrypoint validation failed:\n"
                + entrypoint_check.stdout
                + entrypoint_check.stderr
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic clean package for a staged Alakazam source."
    )
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--template-archive", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--archive-name", required=True)
    parser.add_argument("--source-closure-sha256", required=True)
    args = parser.parse_args()

    source = args.source_dir.resolve()
    template = args.template_archive.resolve()
    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError(f"output directory already exists: {output}")
    if not template.is_file():
        raise FileNotFoundError(template)
    output.mkdir(parents=True)

    with tempfile.TemporaryDirectory(
        prefix="alakazam-package-stage-", dir=output
    ) as temp_name:
        stage = Path(temp_name)
        with tarfile.open(template, "r:*") as archive:
            members = safe_members(archive)
            archive.extractall(stage, members=members)
        for path in stage.glob("*.py"):
            path.unlink()
        bom_normalized = []
        for path in source_files(source):
            destination_name = (
                "_policy_main.py" if path.name == "main.py" else path.name
            )
            if copy_source_file(path, stage / destination_name):
                bom_normalized.append(path.name)
        (stage / "main.py").write_text(
            KAGGLE_ENTRYPOINT,
            encoding="utf-8",
            newline="\n",
        )
        for path in stage.rglob("*"):
            if path.is_file() and (
                "__pycache__" in path.parts or path.suffix == ".pyc"
            ):
                raise AssertionError(f"cache artifact in stage: {path}")
        staged = {
            path.relative_to(stage).as_posix(): {
                "sha256": sha256(path),
                "size": path.stat().st_size,
            }
            for path in sorted(stage.rglob("*"))
            if path.is_file()
        }
        archive_path = output / args.archive_name
        build_archive(stage, archive_path)

    verify_archive(archive_path, staged)
    manifest = {
        "schema_version": "alakazam-staged-clean-package-v1",
        "source_dir": str(source),
        "source_closure_sha256": args.source_closure_sha256.upper(),
        "template_archive": str(template),
        "template_archive_sha256": sha256(template),
        "archive": str(archive_path),
        "archive_sha256": sha256(archive_path),
        "archive_size": archive_path.stat().st_size,
        "file_count": len(staged),
        "members": staged,
        "verification": {
            "safe_paths": True,
            "no_links": True,
            "reextract_hashes_match": True,
            "top_level_python_compiles": True,
            "top_level_python_bom_free": True,
            "deck_rows": 60,
            "runtime_certified_v1_planner_present": True,
        },
        "transforms": {
            "utf8_bom_removed_from_python": bom_normalized,
            "kaggle_entrypoint_wrapper": {
                "entrypoint": "main.py",
                "policy_source": "_policy_main.py",
                "deck_callback_rows": 60,
                "deck_callback_matches_deck_csv": True,
            },
        },
    }
    manifest_path = output / "package_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "archive": str(archive_path),
                "archive_sha256": manifest["archive_sha256"],
                "file_count": manifest["file_count"],
                "manifest": str(manifest_path),
                "manifest_sha256": sha256(manifest_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
