"""Keep only explicitly approved matchup namespaces in residual weights."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


MATCHUP_PREFIXES = ("matchup_", "public_matchup_")


def matchup_from_key(key):
    if not key.startswith(MATCHUP_PREFIXES) or "=" not in key:
        return None
    return key.split("=", 1)[1].split(":", 1)[0]


def filter_weights(weights, matchups, prefixes=MATCHUP_PREFIXES, min_abs=0.0, scale=1.0):
    approved = set(matchups)
    prefixes = tuple(prefixes)
    return {
        key: float(value) * float(scale) for key, value in weights.items()
        if key.startswith(prefixes)
        and matchup_from_key(key) in approved
        and abs(float(value)) >= float(min_abs)
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--matchup", action="append", required=True)
    parser.add_argument(
        "--feature-prefix", action="append", choices=MATCHUP_PREFIXES,
        help="Restrict output to baseline or public matchup features; defaults to both.",
    )
    parser.add_argument("--min-abs", type=float, default=0.0)
    parser.add_argument("--scale", type=float, default=1.0)
    args = parser.parse_args()
    weights = json.loads(args.input.read_text(encoding="ascii"))
    if not isinstance(weights, dict):
        parser.error("input weights must be a JSON object")
    filtered = filter_weights(
        weights, args.matchup, args.feature_prefix or MATCHUP_PREFIXES,
        args.min_abs, args.scale,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(filtered, sort_keys=True, indent=2), encoding="ascii")
    print("kept %d of %d weights" % (len(filtered), len(weights)))


if __name__ == "__main__":
    main()
