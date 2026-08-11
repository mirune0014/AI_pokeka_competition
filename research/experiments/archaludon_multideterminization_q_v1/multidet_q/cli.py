"""Command line entry point for the fixed experiment sequence."""

from __future__ import annotations

import argparse
import json
import sys

from .calibrate import calibrate
from .config import ensure_output, load_config
from .dataset import build_dataset
from .evaluate import evaluate
from .merge import merge_full
from .evaluate import report
from .search_runtime import check_api_surface
from .train import train
from .worker import pilot_gate, run_full_shard, run_pilot


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="multidet_q")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pilot")
    full = sub.add_parser("run-full")
    full.add_argument("--shard-count", type=int, required=True)
    full.add_argument("--shard-index", type=int, required=True)
    merge = sub.add_parser("merge-full")
    merge.add_argument("--shard-count", type=int, required=True)
    for name in ("build-dataset", "train", "calibrate", "evaluate", "report"):
        sub.add_parser(name)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = load_config()
    if args.command == "pilot":
        ensure_output(config)
        surface = check_api_surface()
        if surface["missing"]:
            raise RuntimeError(f"BLOCKED: seeded engine cg.api missing {surface['missing']}")
        result = run_pilot(config)
        gate = pilot_gate(config)
        print(json.dumps({"worker": result, "pilot": gate}, sort_keys=True))
        if not gate["technical_gate_passed"]:
            return 2
        return 0
    config.output_dir.mkdir(parents=True, exist_ok=True)
    if args.command == "run-full":
        result = run_full_shard(config, shard_count=args.shard_count, shard_index=args.shard_index)
    elif args.command == "merge-full":
        result = merge_full(config, shard_count=args.shard_count)
    elif args.command == "build-dataset":
        result = build_dataset(config)
    elif args.command == "train":
        result = train(config)
    elif args.command == "calibrate":
        result = calibrate(config)
    elif args.command == "evaluate":
        result = evaluate(config)
    elif args.command == "report":
        result = report(config)
    else:  # pragma: no cover
        raise AssertionError(args.command)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise
