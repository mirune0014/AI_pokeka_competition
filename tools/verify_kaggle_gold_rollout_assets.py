"""Verify a private engine-free Kaggle Gold rollout asset dataset."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rl_ptcg.kaggle_rollout_assets import verify_rollout_assets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--allow-missing-dataset-metadata", action="store_true")
    args = parser.parse_args()
    print(json.dumps(
        verify_rollout_assets(
            args.asset_root,
            allow_missing_dataset_metadata=args.allow_missing_dataset_metadata,
        ),
        sort_keys=True, separators=(",", ":"),
    ))


if __name__ == "__main__":
    main()
