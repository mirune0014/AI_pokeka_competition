"""Build or verify the non-blind upper-tier paired-rollout state corpus."""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from rl_ptcg.gold_upper_tier_states import parse_state_spec, run_collector, verify_gold_upper_tier_states

def _extras(values: list[str]) -> dict[str, list[Path]]:
    result: dict[str, list[Path]] = defaultdict(list)
    for value in values:
        if "=" not in value: raise ValueError("--extra-deck must be ARCHETYPE=PATH")
        archetype, path = value.split("=", 1)
        if not archetype or not path: raise ValueError("--extra-deck must be ARCHETYPE=PATH")
        result[archetype].append(Path(path))
    return dict(result)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline-dir", "engine-dir", "inventory-csv", "gold-candidates-csv", "gold-catalog-manifest", "split-manifest", "output-dir", "workspace-root"): parser.add_argument("--" + name, type=Path)
    parser.add_argument("--state", action="append", default=[]); parser.add_argument("--extra-deck", action="append", default=[])
    parser.add_argument("--seed"); parser.add_argument("--rule-top-k", type=int, default=6); parser.add_argument("--max-diverse-actions", type=int, default=12); parser.add_argument("--max-known-hypotheses", type=int, default=3); parser.add_argument("--unknown-mass", type=float, default=0.15); parser.add_argument("--max-deck-replacements", type=int, default=4); parser.add_argument("--verify-only", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        print(json.dumps(verify_gold_upper_tier_states(args.verify_only, args.workspace_root), sort_keys=True)); return
    required = ("baseline_dir", "engine_dir", "inventory_csv", "gold_candidates_csv", "gold_catalog_manifest", "split_manifest", "output_dir", "workspace_root", "seed")
    missing = ["--" + name.replace("_", "-") for name in required if getattr(args, name) is None]
    if missing or not args.state: parser.error("required arguments: %s" % ", ".join(missing + ([] if args.state else ["--state"])))
    try: specs = [parse_state_spec(value) for value in args.state]; extras = _extras(args.extra_deck)
    except ValueError as error: parser.error(str(error))
    print(json.dumps(run_collector(baseline_dir=args.baseline_dir, engine_dir=args.engine_dir, inventory_csv=args.inventory_csv, gold_candidates_csv=args.gold_candidates_csv, gold_catalog_manifest=args.gold_catalog_manifest, split_manifest=args.split_manifest, output_dir=args.output_dir, workspace_root=args.workspace_root or ROOT, state_specs=specs, extra_decks=extras, rule_top_k=args.rule_top_k, max_diverse_actions=args.max_diverse_actions, max_known_hypotheses=args.max_known_hypotheses, unknown_mass=args.unknown_mass, max_deck_replacements=args.max_deck_replacements, seed=args.seed), sort_keys=True))
if __name__ == "__main__": main()
