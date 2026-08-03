"""Build or verify split-bound complete-action advantage targets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.gold_teacher_advantages import (
    build_teacher_advantages,
    verify_teacher_advantages,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path)
    parser.add_argument("--oracle-dir", type=Path)
    parser.add_argument("--refinement-selection", type=Path)
    parser.add_argument("--teacher-split", type=Path)
    parser.add_argument("--source-receipt", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--source-workspace-root", type=Path)
    parser.add_argument("--target-archetype")
    parser.add_argument("--target-deck", type=Path)
    parser.add_argument("--verify-only", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_teacher_advantages(args.verify_only, args.workspace_root)
    else:
        required = {
            "corpus_dir": args.corpus_dir,
            "oracle_dir": args.oracle_dir,
            "refinement_selection": args.refinement_selection,
            "teacher_split": args.teacher_split,
            "source_receipt": args.source_receipt,
            "output_dir": args.output_dir,
        }
        missing = ["--" + name.replace("_", "-") for name, value in required.items() if value is None]
        if missing:
            parser.error("required arguments: %s" % ", ".join(missing))
        result = build_teacher_advantages(
            args.corpus_dir,
            args.oracle_dir,
            args.refinement_selection,
            args.teacher_split,
            args.source_receipt,
            args.output_dir,
            workspace_root=args.workspace_root,
            source_workspace_root=args.source_workspace_root,
            target_archetype=args.target_archetype,
            target_deck_path=args.target_deck,
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()

