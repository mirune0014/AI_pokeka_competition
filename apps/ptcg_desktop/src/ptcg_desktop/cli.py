from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .artifacts import register_local_artifact, trusted_manifest, verify_artifact
from .deck import DeckValidationError, read_deck_csv, validate_deck


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PTCG Human Client maintenance commands")
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify", help="verify submission 55155015 artifact")
    verify.add_argument("--artifact", type=Path, required=True)
    inspect_local = sub.add_parser("inspect-local", help="fingerprint a user-managed local agent without importing it")
    inspect_local.add_argument("--artifact", type=Path, required=True)
    deck = sub.add_parser("deck", help="validate a deck CSV shape")
    deck.add_argument("--csv", type=Path, required=True)
    sub.add_parser("manifest", help="print the embedded trusted manifest")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "verify":
        report = verify_artifact(args.artifact)
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return 0 if report.verified else 2
    if args.command == "inspect-local":
        manifest, report = register_local_artifact(args.artifact)
        print(json.dumps({"report": report.to_dict(), "manifest": manifest}, ensure_ascii=False, indent=2))
        return 0 if report.verified else 2
    if args.command == "deck":
        try:
            result = validate_deck(read_deck_csv(args.csv))
        except DeckValidationError as exc:
            print(json.dumps({"valid": False, "code": exc.code, "message": str(exc), "row": exc.row}, ensure_ascii=False, indent=2))
            return 2
        print(json.dumps({"valid": True, "total": result.total, "counts": result.counts}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(trusted_manifest(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
