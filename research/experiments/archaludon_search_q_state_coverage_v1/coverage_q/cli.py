"""Command-line entry point for the bounded Coverage-Q experiment."""

from __future__ import annotations

import argparse
import json
import sys

from .calibrate import calibrate
from .config import ensure_output, load_config
from .dataset import build_datasets
from .final_evaluate import final_evaluate
from .merge import merge_all, merge_stage
from .offline_test import offline_test
from .search_plan import build_plan
from .search_worker import run_stage
from .source import collect_source
from .supervisor import run_full, run_pilot
from .train_milestones import train


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="coverage_q")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pilot")
    sub.add_parser("supervise")
    for name in ("source", "build-plan", "build-dataset", "train", "calibrate", "offline-test", "final-evaluate"):
        command = sub.add_parser(name)
        if name == "source":
            command.add_argument("--pilot", action="store_true")
        if name == "build-plan":
            command.add_argument("--pilot", action="store_true")
    search = sub.add_parser("search")
    search.add_argument("stage")
    search.add_argument("--shard-count", type=int, default=6)
    search.add_argument("--shard-index", type=int, default=0)
    merge = sub.add_parser("merge")
    merge.add_argument("stage", nargs="?")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = load_config()
    if args.command == "pilot":
        result = run_pilot(config)
    elif args.command == "supervise":
        if config.output_dir.exists() and any(config.output_dir.iterdir()):
            raise FileExistsError(f"full output exists and is non-empty: {config.output_dir}")
        ensure_output(config)
        result = run_full(config)
    elif args.command == "source":
        config.output_dir.mkdir(parents=True, exist_ok=True)
        result = collect_source(config, pilot=bool(args.pilot))
    elif args.command == "build-plan":
        result = build_plan(config, pilot=bool(args.pilot))
    elif args.command == "search":
        result = run_stage(config, args.stage, shard_count=args.shard_count, shard_index=args.shard_index)
    elif args.command == "merge":
        result = merge_all(config, shard_count=config.worker_count) if args.stage is None else merge_stage(config, args.stage, shard_count=config.worker_count)
    elif args.command == "build-dataset":
        result = build_datasets(config)
    elif args.command == "train":
        result = train(config)
    elif args.command == "calibrate":
        result = calibrate(config)
    elif args.command == "offline-test":
        result = offline_test(config)
    elif args.command == "final-evaluate":
        result = final_evaluate(config)
    else:  # pragma: no cover
        raise AssertionError(args.command)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise
