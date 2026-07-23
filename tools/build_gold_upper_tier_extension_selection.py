"""Build or verify an expanded-only upper-tier archetype selection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rl_ptcg.gold_upper_tier_extension_selection import (
    verify_upper_tier_extension_selection,
    write_upper_tier_extension_selection,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--archetype")
    parser.add_argument("--opponent-heads", type=int, default=3)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--verify-only", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_upper_tier_extension_selection(args.verify_only, args.workspace_root)
    else:
        missing = [name for name in ("audit", "archetype", "output") if getattr(args, name) is None]
        if missing:
            parser.error("required arguments: %s" % ", ".join("--" + name.replace("_", "-") for name in missing))
        result = write_upper_tier_extension_selection(
            args.audit, args.archetype, args.output, args.workspace_root,
            opponent_heads=args.opponent_heads,
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
