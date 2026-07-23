"""Build or verify a higher-particle Gold teacher refinement selection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rl_ptcg.gold_teacher_refinement_selection import (
    verify_refinement_selection,
    write_refinement_selection,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--source-workspace-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--minimum-top-count", type=int, default=2)
    parser.add_argument("--minimum-mean-advantage", type=float, default=0.05)
    parser.add_argument("--minimum-batch-advantage-exclusive", type=float)
    parser.add_argument("--next-particles", type=int, default=4)
    parser.add_argument("--verify-only", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_refinement_selection(args.verify_only, args.workspace_root)
    else:
        missing = [
            name for name in ("run_dir", "source_workspace_root", "output")
            if getattr(args, name) is None
        ]
        if missing:
            parser.error("required arguments: %s" % ", ".join(
                "--" + name.replace("_", "-") for name in missing
            ))
        result = write_refinement_selection(
            args.run_dir,
            args.source_workspace_root,
            args.output,
            args.workspace_root,
            minimum_top_count=args.minimum_top_count,
            minimum_mean_advantage_win_probability=args.minimum_mean_advantage,
            minimum_batch_advantage_win_probability_exclusive=(
                args.minimum_batch_advantage_exclusive
            ),
            next_particles_per_scenario=args.next_particles,
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
