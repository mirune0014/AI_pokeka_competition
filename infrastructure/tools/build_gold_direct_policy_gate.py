"""Build or verify the Gold direct-policy deck applicability gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.gold_direct_policy_gate import (
    DEFAULT_MAX_REPLACEMENTS,
    DEFAULT_SENSITIVITY_THRESHOLDS,
    run_gate,
    verify_gate_output,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path)
    parser.add_argument("--target-deck", type=Path)
    parser.add_argument("--target-archetype")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--max-replacements", type=int, default=DEFAULT_MAX_REPLACEMENTS)
    parser.add_argument(
        "--sensitivity-threshold", action="append", type=int,
        dest="sensitivity_thresholds",
    )
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--verify-only", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_gate_output(args.verify_only, args.workspace_root)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return
    missing = [
        name for name, value in (
            ("--corpus-dir", args.corpus_dir),
            ("--target-deck", args.target_deck),
            ("--target-archetype", args.target_archetype),
            ("--output-dir", args.output_dir),
        ) if not value
    ]
    if missing:
        parser.error("required arguments: %s" % ", ".join(missing))
    thresholds = (
        args.sensitivity_thresholds
        if args.sensitivity_thresholds is not None
        else DEFAULT_SENSITIVITY_THRESHOLDS
    )
    if args.max_replacements < 0 or any(value < 0 for value in thresholds):
        parser.error("replacement limits must be non-negative")
    result = run_gate(
        args.corpus_dir,
        args.target_deck,
        args.output_dir,
        target_archetype=args.target_archetype,
        max_replacements=args.max_replacements,
        sensitivity_thresholds=thresholds,
        workspace_root=args.workspace_root,
        cli_path=Path(__file__),
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
