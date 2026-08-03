"""Restore ignored native PTCG runtime files from the tracked canonical copy.

Candidate directories keep their policy source, deck, and Python ``cg`` API in
Git.  The four platform-native libraries are byte-identical copies and are
ignored to avoid hundreds of redundant working-tree entries.  A clean clone
can restore them with either of these commands::

    python infrastructure/tools/hydrate_candidate_native_runtime.py
    python infrastructure/tools/hydrate_candidate_native_runtime.py <candidate-name>

Use ``--check`` to verify an already hydrated tree without writing files.
The script refuses to overwrite a runtime whose hash differs from the frozen
canonical runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


CANONICAL_RELATIVE = Path(
    "archaludon/final/"
    "archaludon_historical_silver_single_resolver_salvage_v1/cg"
)
CANDIDATES_RELATIVE = Path("archaludon/candidates")
EXPECTED_SHA256 = {
    "cg.dll": "9EA2B0A751029689BFF3DDCCB5F29A98EDD46961DAD264490ED121EF704FB500",
    "libcg.so": "FFD89BF923525A3E6FEB5E6201E96A866C0F456895499ED5C4A566303CAAE67C",
    "libcg-arm64.so": "030B4728CE9FB9E90B75830B7CF7236F71859732A05EC4A377078EEE0421BBE5",
    "libcg.dylib": "77BB978A8129B094452679E0DAF0DA69593AFDA7331685F4642C0D4A94D39D82",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def verify_canonical(canonical: Path) -> None:
    for name, expected in EXPECTED_SHA256.items():
        path = canonical / name
        if not path.is_file():
            raise FileNotFoundError(f"canonical runtime is missing: {path}")
        actual = sha256(path)
        if actual != expected:
            raise ValueError(
                f"canonical runtime hash mismatch: {path} "
                f"expected={expected} actual={actual}"
            )


def resolve_targets(repo: Path, names: list[str]) -> list[Path]:
    candidates_root = (repo / CANDIDATES_RELATIVE).resolve()
    if not names:
        return sorted(
            path
            for path in candidates_root.iterdir()
            if path.is_dir() and (path / "main.py").is_file()
            and (path / "cg" / "sim.py").is_file()
        )

    targets: list[Path] = []
    for name in names:
        supplied = Path(name)
        path = supplied if supplied.is_absolute() else candidates_root / supplied
        path = path.resolve()
        try:
            path.relative_to(candidates_root)
        except ValueError as error:
            raise ValueError(f"candidate is outside {candidates_root}: {path}") from error
        if not (path / "main.py").is_file() or not (path / "cg" / "sim.py").is_file():
            raise FileNotFoundError(f"candidate source/runtime API is incomplete: {path}")
        targets.append(path)
    return sorted(set(targets))


def hydrate_one(canonical: Path, candidate: Path, check_only: bool) -> dict[str, object]:
    destination = candidate / "cg"
    copied: list[str] = []
    present: list[str] = []
    missing: list[str] = []

    for name, expected in EXPECTED_SHA256.items():
        target = destination / name
        if target.exists():
            actual = sha256(target)
            if actual != expected:
                raise ValueError(
                    f"refusing to overwrite noncanonical runtime: {target} "
                    f"expected={expected} actual={actual}"
                )
            present.append(name)
            continue

        if check_only:
            missing.append(name)
            continue

        destination.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(canonical / name, target)
        actual = sha256(target)
        if actual != expected:
            target.unlink(missing_ok=True)
            raise ValueError(
                f"copied runtime failed verification: {target} "
                f"expected={expected} actual={actual}"
            )
        copied.append(name)

    return {
        "candidate": candidate.name,
        "copied": copied,
        "present": present,
        "missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "candidates",
        nargs="*",
        help="candidate directory name(s); omit to process every runnable candidate",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify only; report missing files without copying",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    canonical = repo / CANONICAL_RELATIVE
    verify_canonical(canonical)
    targets = resolve_targets(repo, args.candidates)
    results = [hydrate_one(canonical, target, args.check) for target in targets]
    missing = sum(len(row["missing"]) for row in results)
    copied = sum(len(row["copied"]) for row in results)
    print(
        json.dumps(
            {
                "canonical": canonical.relative_to(repo).as_posix(),
                "candidates": len(results),
                "copied": copied,
                "missing": missing,
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if args.check and missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
