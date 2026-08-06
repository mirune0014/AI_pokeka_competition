'''Command line entry points for the fixed Rollout-Q v1 experiment.'''

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .branch_runner import run_branches_shard
from .branch_task_builder import build_tasks_round
from .config import DEFAULT_SPEC_PATH, load_spec
from .dataset import build_dataset
from .evaluate import evaluate_round
from .merge_results import merge_results_round
from .report import report_round
from .source_collector import collect_source_round
from .train import train_through_round


def _require_round_inputs(config: Any, round_index: int, shard_count: int) -> None:
    round_root = config.output_dir / f'round_{int(round_index):02d}'
    source_dir = round_root / 'source_traces'
    if not source_dir.is_dir() or not any(source_dir.glob('*.json')):
        raise FileNotFoundError(f'source traces are required before run-round: {source_dir}')
    tasks_path = round_root / 'tasks' / 'all_tasks.jsonl'
    if not tasks_path.is_file():
        raise FileNotFoundError(f'all_tasks.jsonl is required before run-round: {tasks_path}')
    result_dir = round_root / 'branch_results'
    for shard_index in range(int(shard_count)):
        path = result_dir / f'shard_{shard_index:03d}_of_{int(shard_count):03d}.jsonl'
        if not path.is_file():
            raise FileNotFoundError(f'branch shard result is required before run-round: {path}')


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='archaludon-rollout-q-v1')
    parser.add_argument('--spec', type=Path, default=DEFAULT_SPEC_PATH)
    commands = parser.add_subparsers(dest='command', required=True)

    collect = commands.add_parser('collect-source')
    collect.add_argument('--round', type=int, required=True)
    collect.add_argument('--games', type=int)
    collect.add_argument('--max-steps', type=int)

    tasks = commands.add_parser('build-tasks')
    tasks.add_argument('--round', type=int, required=True)

    branches = commands.add_parser('run-branches')
    branches.add_argument('--round', type=int, required=True)
    branches.add_argument('--shard-count', type=int, required=True)
    branches.add_argument('--shard-index', type=int, required=True)
    branches.add_argument('--max-steps', type=int)

    merge = commands.add_parser('merge-results')
    merge.add_argument('--round', type=int, required=True)
    merge.add_argument('--shard-count', type=int, required=True)

    dataset = commands.add_parser('build-dataset')
    dataset.add_argument('--through-round', type=int, required=True)

    train = commands.add_parser('train')
    train.add_argument('--through-round', type=int, required=True)

    evaluate = commands.add_parser('evaluate')
    evaluate.add_argument('--round', type=int, required=True)

    report = commands.add_parser('report')
    report.add_argument('--round', type=int, required=True)

    run_round = commands.add_parser('run-round')
    run_round.add_argument('--round', type=int, required=True)
    run_round.add_argument('--shard-count', type=int, default=16)

    return parser


def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = _parser().parse_args(argv)
    config = load_spec(args.spec)
    if args.command == 'collect-source':
        return collect_source_round(config, args.round, games=args.games, max_steps=args.max_steps)
    if args.command == 'build-tasks':
        return build_tasks_round(config, args.round)
    if args.command == 'run-branches':
        return run_branches_shard(
            config,
            args.round,
            shard_count=args.shard_count,
            shard_index=args.shard_index,
            max_steps=args.max_steps,
        )
    if args.command == 'merge-results':
        return merge_results_round(config, args.round, shard_count=args.shard_count)
    if args.command == 'build-dataset':
        return build_dataset(config, args.through_round)
    if args.command == 'train':
        return train_through_round(config, args.through_round)
    if args.command == 'evaluate':
        return evaluate_round(config, args.round)
    if args.command == 'report':
        return report_round(config, args.round)
    if args.command == 'run-round':
        _require_round_inputs(config, args.round, args.shard_count)
        summary: dict[str, Any] = {}
        summary['merge'] = merge_results_round(config, args.round, shard_count=args.shard_count)
        summary['dataset'] = build_dataset(config, args.round)
        summary['training'] = train_through_round(config, args.round)
        summary['evaluation'] = evaluate_round(config, args.round)
        summary['report'] = report_round(config, args.round)
        return summary
    raise AssertionError(args.command)


if __name__ == '__main__':
    print(json.dumps(main(), ensure_ascii=False, indent=2, sort_keys=True))
