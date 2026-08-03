"""Build or verify a cross-platform Kaggle rollout source receipt."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.kaggle_rollout_source_receipt import (
    build_kaggle_rollout_source_receipt, verify_kaggle_rollout_source_receipt,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-manifest", type=Path)
    parser.add_argument("--kaggle-log", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-only", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_kaggle_rollout_source_receipt(args.verify_only, workspace_root=args.workspace_root)
    else:
        missing = [name for name, value in (("--execution-manifest", args.execution_manifest),
                                             ("--kaggle-log", args.kaggle_log), ("--output", args.output)) if value is None]
        if missing:
            parser.error("required arguments: %s" % ", ".join(missing))
        result = build_kaggle_rollout_source_receipt(
            args.execution_manifest, args.kaggle_log, args.output, workspace_root=args.workspace_root,
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
