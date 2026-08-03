"""CLI for bounded Phase 1 Gold replay dataset construction."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.gold_replay_dataset import build_gold_replay_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replays", nargs="*", help="Replay JSON files or directories; optional with a frozen Gold catalog")
    parser.add_argument("--seat-metadata-csv", required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--leaderboard-csv")
    selection.add_argument("--gold-selection-csv")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--gold-rank-max", type=int, default=20)
    parser.add_argument("--split-seed", required=True)
    parser.add_argument("--holdout-style-family", action="append", default=[])
    parser.add_argument("--blind-date-period", action="append", default=[])
    parser.add_argument("--development-date-period", action="append", default=[])
    parser.add_argument("--development-fraction", type=float, default=0.15)
    parser.add_argument("--blind-fraction", type=float, default=0.15)
    parser.add_argument(
        "--component-field",
        action="append",
        choices=["episode_id", "submission_version", "style_family", "date_period", "seed", "deck_variant"],
        help="Repeat to override the default atomic component fields.",
    )
    args = parser.parse_args()
    result = build_gold_replay_dataset(args.replays, seat_metadata_csv=args.seat_metadata_csv,
        leaderboard_csv=args.leaderboard_csv, gold_selection_csv=args.gold_selection_csv,
        output_dir=args.output_dir, gold_rank_max=args.gold_rank_max,
        split_seed=args.split_seed, holdout_style_families=args.holdout_style_family,
        blind_date_periods=args.blind_date_period,
        development_date_periods=args.development_date_period,
        development_fraction=args.development_fraction,
        blind_fraction=args.blind_fraction,
        component_fields=args.component_field or ("episode_id", "submission_version", "seed", "deck_variant"))
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
