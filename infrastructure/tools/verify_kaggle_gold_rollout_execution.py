"""Verify a downloaded private Kaggle Gold rollout execution."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.kaggle_rollout_execution import verify_kaggle_rollout_execution


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-manifest", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--legacy-asset-manifest", type=Path)
    args = parser.parse_args()
    result = verify_kaggle_rollout_execution(
        args.execution_manifest,
        args.workspace_root,
        legacy_asset_manifest_path=args.legacy_asset_manifest,
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
