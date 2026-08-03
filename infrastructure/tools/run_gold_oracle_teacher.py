"""Run or verify the Phase 3 paired Gold belief-rollout teacher."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.gold_oracle_runner import run_oracle, verify_oracle_output


def parse_policies(values: Sequence[str]) -> dict[str, list[Path]]:
    result: dict[str, list[Path]] = defaultdict(list)
    for value in values:
        if "=" not in value:
            raise ValueError("--opponent-policy must be ARCHETYPE=PATH")
        archetype, path = value.split("=", 1)
        if not archetype or not path:
            raise ValueError("--opponent-policy must be ARCHETYPE=PATH")
        result[archetype].append(Path(path))
    return dict(result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-dir", type=Path)
    parser.add_argument("--baseline-dir", type=Path)
    parser.add_argument("--engine-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--opponent-policy", action="append", default=[])
    parser.add_argument("--continuation-policy", action="append", type=Path, default=[])
    parser.add_argument("--state-id", action="append")
    parser.add_argument("--batches", type=int, default=2)
    parser.add_argument("--particles-per-scenario", type=int, default=2)
    parser.add_argument("--max-rollout-steps", type=int, default=1000)
    parser.add_argument("--candidate-set", choices=(
        "baseline", "rule_top3", "rule_topK", "rule_diverse", "rule_plus_gold",
    ), default="rule_plus_gold")
    parser.add_argument("--candidate-selection", type=Path)
    parser.add_argument("--seed", default="gold-oracle-teacher-v1")
    parser.add_argument("--bootstrap-repetitions", type=int, default=1000)
    parser.add_argument(
        "--opponent-population-mode",
        choices=("path_distinct_v1", "structural_unique_v1"),
        default="path_distinct_v1",
    )
    parser.add_argument(
        "--rollout-seed-mode",
        choices=("policy_id_v1", "common_stream_v1", "common_population_v2"),
        default="policy_id_v1",
    )
    parser.add_argument("--max-new-shards", type=int)
    parser.add_argument("--workspace-root", type=Path, default=ROOT)
    verification = parser.add_mutually_exclusive_group()
    verification.add_argument("--verify-only", type=Path)
    verification.add_argument("--verify-partial", type=Path)
    args = parser.parse_args()
    if args.verify_only is not None:
        result = verify_oracle_output(args.verify_only, args.workspace_root)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return
    if args.verify_partial is not None:
        result = verify_oracle_output(
            args.verify_partial, args.workspace_root, allow_incomplete=True,
        )
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return
    required = ("corpus_dir", "baseline_dir", "engine_dir", "output_dir")
    missing = ["--" + name.replace("_", "-") for name in required if getattr(args, name) is None]
    if missing:
        parser.error("required arguments: %s" % ", ".join(missing))
    try:
        policies = parse_policies(args.opponent_policy)
    except ValueError as error:
        parser.error(str(error))
    if not policies:
        parser.error("at least one --opponent-policy is required")
    result = run_oracle(
        args.corpus_dir, args.baseline_dir, args.engine_dir, args.output_dir,
        policies, args.continuation_policy,
        state_ids=args.state_id, batches=args.batches,
        particles_per_scenario=args.particles_per_scenario,
        max_rollout_steps=args.max_rollout_steps, candidate_set=args.candidate_set,
        seed=args.seed, bootstrap_repetitions=args.bootstrap_repetitions,
        workspace_root=args.workspace_root, cli_path=Path(__file__),
        candidate_selection_path=args.candidate_selection,
        max_new_shards=args.max_new_shards,
        opponent_population_mode=args.opponent_population_mode,
        rollout_seed_mode=args.rollout_seed_mode,
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
