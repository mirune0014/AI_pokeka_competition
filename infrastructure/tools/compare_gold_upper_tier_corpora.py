"""Build or verify the upper-tier v1-to-v2 semantic migration audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.gold_upper_tier_migration import (
    verify_migration_audit,
    write_migration_audit,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-dir", type=Path)
    parser.add_argument("--portable-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--verify-only", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_migration_audit(args.verify_only, args.workspace_root)
    else:
        missing = [name for name in ("legacy_dir", "portable_dir", "output") if getattr(args, name) is None]
        if missing:
            parser.error("required arguments: %s" % ", ".join("--" + name.replace("_", "-") for name in missing))
        result = write_migration_audit(
            args.legacy_dir, args.portable_dir, args.output, args.workspace_root,
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
