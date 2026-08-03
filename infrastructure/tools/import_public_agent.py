from __future__ import annotations

import argparse
import shutil
import tarfile
import tempfile
from pathlib import Path


REQUIRED_FILES = ("main.py", "deck.csv")
OPTIONAL_FILES = ("requirements.txt",)


def copy_agent_files(source_dir: Path, target_dir: Path, overwrite: bool) -> None:
    missing = [name for name in REQUIRED_FILES if not (source_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"{source_dir} is missing required files: {', '.join(missing)}")

    if target_dir.exists() and not overwrite:
        raise FileExistsError(f"{target_dir} already exists. Pass --overwrite to replace files.")
    target_dir.mkdir(parents=True, exist_ok=True)

    for name in REQUIRED_FILES + OPTIONAL_FILES:
        source = source_dir / name
        if source.exists():
            shutil.copy2(source, target_dir / name)


def import_from_tar(source: Path, target_dir: Path, overwrite: bool) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        with tarfile.open(source, "r:*") as archive:
            archive.extractall(tmp_dir)
        copy_agent_files(tmp_dir, target_dir, overwrite)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a public notebook output directory or submission tarball as a local meta agent."
    )
    parser.add_argument("source", type=Path, help="Directory or .tar/.tar.gz containing main.py and deck.csv.")
    parser.add_argument("--name", required=True, help="Local agent name under opponents/meta_agents/.")
    parser.add_argument("--out-dir", type=Path, default=Path("meta_agents"))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target_dir = args.out_dir / args.name
    if args.source.is_dir():
        copy_agent_files(args.source, target_dir, args.overwrite)
    else:
        import_from_tar(args.source, target_dir, args.overwrite)
    print(f"Imported {args.source} -> {target_dir}")


if __name__ == "__main__":
    main()
