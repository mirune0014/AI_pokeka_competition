"""Run the bounded non-blind Gold replay disagreement audit."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from rl_ptcg.gold_disagreement_audit import run_gold_disagreement_audit

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--baseline-map", type=Path, required=True, help="JSON object mapping own archetype to rule-agent directory")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", default="0")
    parser.add_argument("--target-count", type=int, default=512)
    parser.add_argument("--max-complete-actions", type=int, default=4096)
    args = parser.parse_args()
    mapping = json.loads(args.baseline_map.read_text(encoding="utf-8"))
    if not isinstance(mapping, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
        raise ValueError("baseline map must be a JSON object of string archetypes to string directories")
    print(json.dumps(run_gold_disagreement_audit(args.dataset_dir, args.engine_dir, mapping, args.output_dir, seed=args.seed, target_count=args.target_count, max_complete_actions=args.max_complete_actions), sort_keys=True, separators=(",", ":")))

if __name__ == "__main__": main()
