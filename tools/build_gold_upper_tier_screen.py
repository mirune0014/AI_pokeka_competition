"""Build or verify the leakage-resistant upper-tier state expansion screen."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rl_ptcg.gold_upper_tier_screen import verify_screen, write_screen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-corpus", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--minimum-legal-options", type=int, default=4)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--verify-only", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_screen(args.verify_only, args.workspace_root, Path(__file__))
    else:
        if args.base_corpus is None or args.output is None:
            parser.error("--base-corpus and --output are required")
        result = write_screen(
            args.base_corpus, args.output, args.workspace_root, Path(__file__),
            minimum_legal_options=args.minimum_legal_options,
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
