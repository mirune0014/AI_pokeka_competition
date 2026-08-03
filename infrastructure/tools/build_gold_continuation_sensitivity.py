"""Build or verify a Gold continuation-policy sensitivity audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.gold_continuation_sensitivity import (
    verify_continuation_sensitivity,
    write_continuation_sensitivity,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-receipt", type=Path)
    parser.add_argument("--selection-manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--verify-only", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_continuation_sensitivity(args.verify_only, args.workspace_root)
    else:
        if args.source_receipt is None or args.selection_manifest is None or args.output is None:
            parser.error("--source-receipt, --selection-manifest, and --output are required")
        result = write_continuation_sensitivity(
            args.source_receipt,
            args.selection_manifest,
            args.output,
            args.workspace_root,
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
