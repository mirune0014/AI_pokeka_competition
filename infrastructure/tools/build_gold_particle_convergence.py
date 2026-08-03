"""Build or verify a Gold teacher particle-count convergence audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.gold_particle_convergence import (
    verify_particle_convergence,
    write_particle_convergence,
)


def _mapping(values: list[str], option: str) -> dict[str, Path]:
    result = {}
    for value in values:
        if "=" not in value:
            raise ValueError("%s must be LABEL=PATH" % option)
        label, path = value.split("=", 1)
        if not label or not path or label in result:
            raise ValueError("%s must use unique LABEL=PATH values" % option)
        result[label] = Path(path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", default=[])
    parser.add_argument("--source-workspace", action="append", default=[])
    parser.add_argument("--selection-manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    parser.add_argument("--verify-only", type=Path)
    parser.add_argument("--project-opponent-policy-id")
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_particle_convergence(args.verify_only, args.workspace_root)
    else:
        try:
            runs = _mapping(args.run, "--run")
            workspaces = _mapping(args.source_workspace, "--source-workspace")
        except ValueError as error:
            parser.error(str(error))
        if not runs or set(runs) != set(workspaces) or args.selection_manifest is None or args.output is None:
            parser.error("matching --run/--source-workspace labels, --selection-manifest, and --output are required")
        levels = [(label, runs[label], workspaces[label]) for label in runs]
        result = write_particle_convergence(
            levels, args.selection_manifest, args.output, args.workspace_root,
            project_opponent_policy_id=args.project_opponent_policy_id,
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
