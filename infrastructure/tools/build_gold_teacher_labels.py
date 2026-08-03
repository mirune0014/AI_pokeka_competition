"""Build or verify canonical, hash-bound stable Gold teacher labels."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.gold_teacher_labels import build_teacher_labels, verify_teacher_labels


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path)
    parser.add_argument("--oracle-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--target-deck", type=Path)
    parser.add_argument("--target-archetype")
    parser.add_argument("--source-receipt", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--source-workspace-root", type=Path)
    parser.add_argument("--teacher-split", type=Path)
    parser.add_argument("--verify-only", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_teacher_labels(args.verify_only, args.workspace_root)
    else:
        missing = [name for name, value in (
            ("--corpus-dir", args.corpus_dir), ("--oracle-dir", args.oracle_dir),
            ("--output-dir", args.output_dir),
        ) if value is None]
        if missing:
            parser.error("required arguments: %s" % ", ".join(missing))
        result = build_teacher_labels(
            args.corpus_dir, args.oracle_dir, args.output_dir,
            workspace_root=args.workspace_root, target_deck_path=args.target_deck,
            target_archetype=args.target_archetype, source_receipt_path=args.source_receipt,
            source_workspace_root=args.source_workspace_root,
            teacher_split_path=args.teacher_split,
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
