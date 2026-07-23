"""Build the Phase 3a leakage-safe Gold oracle state corpus."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rl_ptcg.gold_oracle_states import run_collector, verify_gold_oracle_states


def parse_extra_decks(values: Sequence[str]) -> dict[str, list[Path]]:
    result: dict[str, list[Path]] = defaultdict(list)
    for value in values:
        if "=" not in value:
            raise ValueError("--extra-deck must be ARCHETYPE=PATH")
        archetype, path = value.split("=", 1)
        if not archetype or not path:
            raise ValueError("--extra-deck must be ARCHETYPE=PATH")
        result[archetype].append(Path(path))
    return dict(result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "dataset-dir", "audit-output-dir", "baseline-dir", "engine-dir",
        "inventory-csv", "output-dir",
    ):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--decision-id", action="append")
    parser.add_argument("--extra-deck", action="append", default=[])
    parser.add_argument("--rule-top-k", type=int, default=6)
    parser.add_argument("--max-diverse-actions", type=int, default=12)
    parser.add_argument("--max-known-hypotheses", type=int, default=3)
    parser.add_argument("--unknown-mass", type=float, default=0.15)
    parser.add_argument("--seed")
    parser.add_argument("--verify-only", type=Path)
    parser.add_argument("--workspace-root", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_gold_oracle_states(
            args.verify_only, args.workspace_root, allow_implementation_drift=True,
        )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return
    required = (
        "dataset_dir", "audit_output_dir", "baseline_dir", "engine_dir",
        "inventory_csv", "output_dir", "decision_id", "seed",
    )
    missing = ["--" + name.replace("_", "-") for name in required if not getattr(args, name)]
    if missing:
        parser.error("required arguments: %s" % ", ".join(missing))
    if (
        args.rule_top_k < 1
        or args.max_diverse_actions < args.rule_top_k + 1
        or args.max_known_hypotheses < 1
        or not 0 <= args.unknown_mass < 1
    ):
        parser.error(
            "limits require top-k >= 1, max-diverse >= top-k + 1, "
            "max-known >= 1, and 0 <= unknown-mass < 1",
        )
    try:
        extra_decks = parse_extra_decks(args.extra_deck)
    except ValueError as error:
        parser.error(str(error))
    result = run_collector(
        args.dataset_dir,
        args.audit_output_dir,
        args.baseline_dir,
        args.engine_dir,
        args.inventory_csv,
        args.output_dir,
        args.decision_id,
        extra_decks,
        rule_top_k=args.rule_top_k,
        max_diverse_actions=args.max_diverse_actions,
        max_known_hypotheses=args.max_known_hypotheses,
        unknown_mass=args.unknown_mass,
        seed=args.seed,
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
