"""Blend sparse residual-policy weight files with explicit coefficients."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_weighted_path(value):
    coefficient, separator, path = value.partition("=")
    if not separator or not path:
        raise argparse.ArgumentTypeError("input must be coefficient=path")
    try:
        coefficient = float(coefficient)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("coefficient must be numeric") from exc
    return coefficient, Path(path)


def blend_weights(weighted, min_abs=0.0):
    result = {}
    for coefficient, weights in weighted:
        for key, value in weights.items():
            result[str(key)] = result.get(str(key), 0.0) + float(coefficient) * float(value)
    return {
        key: value for key, value in result.items()
        if abs(value) >= float(min_abs)
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=parse_weighted_path, required=True)
    parser.add_argument("--min-abs", type=float, default=0.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    weighted = []
    for coefficient, path in args.input:
        weights = json.loads(path.read_text(encoding="ascii"))
        if not isinstance(weights, dict):
            parser.error("input weights must be JSON objects")
        weighted.append((coefficient, weights))
    result = blend_weights(weighted, args.min_abs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="ascii")
    print("wrote %d blended weights" % len(result))


if __name__ == "__main__":
    main()
