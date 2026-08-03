"""Build or verify the upper-tier all-roots expansion audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.gold_upper_tier_allroots_audit import (
    verify_allroots_audit,
    write_allroots_audit,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen", type=Path)
    parser.add_argument("--reference-corpus", type=Path)
    parser.add_argument("--expanded-corpus", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--verify-only", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_allroots_audit(args.verify_only, args.workspace_root, Path(__file__))
    else:
        missing = [name for name in ("screen", "reference_corpus", "expanded_corpus", "output") if getattr(args, name) is None]
        if missing:
            parser.error("required arguments: %s" % ", ".join("--" + name.replace("_", "-") for name in missing))
        result = write_allroots_audit(
            args.screen, args.reference_corpus, args.expanded_corpus, args.output,
            args.workspace_root, Path(__file__),
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
