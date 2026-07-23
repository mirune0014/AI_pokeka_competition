"""Verify Gold disagreement audit artifacts without modifying them."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rl_ptcg.gold_disagreement_verify import verify_gold_disagreement_audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-output-dir", type=Path, required=True)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--baseline-map", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    args = parser.parse_args()
    mapping = json.loads(args.baseline_map.read_text(encoding="utf-8"))
    print(json.dumps(verify_gold_disagreement_audit(args.audit_output_dir, args.dataset_dir, mapping, args.workspace_root),
                     sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
