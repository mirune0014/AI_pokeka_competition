"""Merge the fixed BC dataset with train-only DAgger round-one additions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import torch

from .complete_bc_dataset_ops import merge_complete_bc_payloads
from .frozen_sources import sha256_file
from .train_complete_bc import _load_dataset


def merge(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    report_path = args.report.resolve()
    if output.exists() or report_path.exists():
        raise FileExistsError("merged DAgger dataset output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    base_path = args.base.resolve()
    addition_paths = [path.resolve() for path in args.addition]
    base = _load_dataset(base_path)
    additions = [_load_dataset(path) for path in addition_paths]
    receipts = {
        "base": {
            "path": str(base_path),
            "sha256": sha256_file(base_path),
        },
        "additions": [
            {"path": str(path), "sha256": sha256_file(path)}
            for path in addition_paths
        ],
    }
    payload = merge_complete_bc_payloads(
        base=base,
        additions=additions,
        source={
            "kind": "complete-action-bc-dagger-round-1",
            **receipts,
        },
    )
    torch.save(payload, output)
    report = {
        "schema_version": "complete-action-bc-dagger-merge-report-v1",
        "dataset": str(output),
        "dataset_sha256": sha256_file(output),
        "dataset_bytes": output.stat().st_size,
        "inputs": receipts,
        "counts": payload["counts"],
        "split_algorithm": payload["split_algorithm"],
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--addition", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    merge(build_parser().parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
