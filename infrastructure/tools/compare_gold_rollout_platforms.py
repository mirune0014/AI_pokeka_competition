"""Build or verify a Windows/Linux paired-rollout parity audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.gold_rollout_platform_audit import (
    verify_platform_audit,
    write_platform_audit,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left-dir", type=Path)
    parser.add_argument("--right-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--left-workspace-root", type=Path)
    parser.add_argument("--right-workspace-root", type=Path)
    parser.add_argument("--verify-only", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_platform_audit(args.verify_only, args.workspace_root)
    else:
        missing = [name for name in ("left_dir", "right_dir", "output") if getattr(args, name) is None]
        if missing:
            parser.error("required arguments: %s" % ", ".join("--" + name.replace("_", "-") for name in missing))
        result = write_platform_audit(
            args.left_dir,
            args.right_dir,
            args.output,
            args.workspace_root,
            args.left_workspace_root,
            args.right_workspace_root,
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
