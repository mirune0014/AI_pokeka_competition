"""Report obsolete root references that remain in executable/config files."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATOR = ROOT / "infrastructure" / "scripts" / "rewrite_repository_paths.py"
REPORT = ROOT / "docs" / "repository_path_residual_report.json"


def load_migrator():
    spec = importlib.util.spec_from_file_location("repository_path_migrator", MIGRATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load migration map")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    migrator = load_migrator()
    hits: list[dict[str, object]] = []
    for path in migrator.candidate_files():
        data = path.read_bytes()
        if b"\0" in data[:8192]:
            continue
        for old, new in migrator.DIRECTORY_MOVES:
            if old.encode("ascii") not in data:
                continue
            pattern = re.compile(
                rb"(?<![A-Za-z0-9_.\\/-])"
                + re.escape(old.encode("ascii"))
                + rb"(?=[\\/])"
            )
            count = len(pattern.findall(data))
            if count:
                hits.append(
                    {
                        "path": path.relative_to(ROOT).as_posix(),
                        "old_root": old,
                        "new_root": new,
                        "count": count,
                    }
                )
        if path.suffix.lower() == ".py":
            for old, components in migrator.PYTHON_JOIN_MOVES:
                old_join = f'/ "{old}"'.encode("ascii")
                new_join = b" / " + b" / ".join(
                    f'"{component}"'.encode("ascii") for component in components
                )
                count = sum(
                    line.count(old_join)
                    for line in data.splitlines()
                    if new_join not in line
                )
                if count:
                    hits.append(
                        {
                            "path": path.relative_to(ROOT).as_posix(),
                            "old_root": old,
                            "new_root": "/".join(components),
                            "count": count,
                        }
                    )
    payload = {
        "scope": "executable code and active configuration only",
        "obsolete_path_hits": sum(int(item["count"]) for item in hits),
        "affected_files": len({str(item["path"]) for item in hits}),
        "hits": hits,
    }
    REPORT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("obsolete_path_hits", "affected_files")}))


if __name__ == "__main__":
    main()
