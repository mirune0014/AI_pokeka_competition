"""Build or verify a generic upper-tier corpus-extension audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rl_ptcg.gold_upper_tier_corpus_extension_audit import (
    verify_corpus_extension_audit,
    write_corpus_extension_audit,
)


def _spec(value: str) -> tuple[str, int, int]:
    parts = value.split(",")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("state spec must be EPISODE,SEAT,STEP")
    try:
        return parts[0], int(parts[1]), int(parts[2])
    except ValueError as error:
        raise argparse.ArgumentTypeError("SEAT and STEP must be integers") from error


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-dir", type=Path)
    parser.add_argument("--expanded-dir", type=Path)
    parser.add_argument("--added-state", type=_spec, action="append", default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--verify-only", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_corpus_extension_audit(args.verify_only, args.workspace_root, Path(__file__))
    else:
        if args.reference_dir is None or args.expanded_dir is None or args.output is None or not args.added_state:
            parser.error("--reference-dir, --expanded-dir, --added-state, and --output are required")
        result = write_corpus_extension_audit(
            args.reference_dir,
            args.expanded_dir,
            args.added_state,
            args.output,
            args.workspace_root,
            Path(__file__),
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
