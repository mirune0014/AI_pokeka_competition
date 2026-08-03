"""Build or verify the seeded Linux PTCG engine in a private environment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.seeded_engine_linux import (
    build_seeded_engine_linux,
    verify_seeded_engine_linux,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-source-dir", type=Path)
    parser.add_argument("--wrapper-source-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--compiler", default="g++")
    parser.add_argument("--verify-only", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_seeded_engine_linux(args.verify_only)
    else:
        missing = [
            name for name in ("engine_source_dir", "wrapper_source_dir", "output_dir")
            if getattr(args, name) is None
        ]
        if missing:
            parser.error("required arguments: %s" % ", ".join("--" + name.replace("_", "-") for name in missing))
        result = build_seeded_engine_linux(
            args.engine_source_dir, args.wrapper_source_dir, args.output_dir,
            compiler=args.compiler,
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
