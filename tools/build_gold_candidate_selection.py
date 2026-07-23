"""Build or verify a high-particle Gold upper-bound candidate selection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rl_ptcg.gold_candidate_selection import (
    build_candidate_selection,
    verify_candidate_selection,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path)
    parser.add_argument("--source-report-dir", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--state-id", action="append")
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--verify-only", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_candidate_selection(args.verify_only, args.workspace_root)
        result.pop("payload")
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return
    if args.corpus_dir is None or args.output is None or not args.source_report_dir:
        parser.error("--corpus-dir, --source-report-dir, and --output are required")
    result = build_candidate_selection(
        args.corpus_dir, args.source_report_dir, args.output,
        state_ids=args.state_id, workspace_root=args.workspace_root,
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
