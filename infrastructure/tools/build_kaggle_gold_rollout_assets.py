"""Build the private engine-free Kaggle Gold rollout asset dataset."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.kaggle_rollout_assets import build_rollout_assets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--policy-dir", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = build_rollout_assets(
        workspace_root=args.workspace_root,
        corpus_dir=args.corpus_dir,
        baseline_dir=args.baseline_dir,
        policy_dirs=args.policy_dir,
        output_dir=args.output_dir,
        dataset_id=args.dataset_id,
        title=args.title,
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
