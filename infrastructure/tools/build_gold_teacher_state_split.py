"""Build or verify the leakage-safe upper-tier teacher-state split."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.gold_teacher_state_split import (
    verify_teacher_state_split,
    write_teacher_state_split,
)


def _assignments(values: list[str]) -> dict[str, str]:
    result = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--episode-split must be EPISODE=SPLIT")
        episode, split = value.split("=", 1)
        if not episode or not split or episode in result:
            raise ValueError("--episode-split must use unique EPISODE=SPLIT values")
        result[episode] = split
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path)
    parser.add_argument("--episode-split", action="append", default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--verify-only", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_teacher_state_split(args.verify_only, args.workspace_root)
    else:
        if args.corpus_dir is None or args.output is None or not args.episode_split:
            parser.error("--corpus-dir, --episode-split, and --output are required")
        try:
            assignments = _assignments(args.episode_split)
        except ValueError as error:
            parser.error(str(error))
        result = write_teacher_state_split(
            args.corpus_dir, assignments, args.output, args.workspace_root,
        )
    printable = dict(result)
    printable.pop("split_by_decision_id", None)
    print(json.dumps(printable, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()

