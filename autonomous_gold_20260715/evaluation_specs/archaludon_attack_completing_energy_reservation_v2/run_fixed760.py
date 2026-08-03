from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
SPEC_PATH = HERE / "fixed760_spec.json"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def checked_file(relative: str, expected: str) -> pathlib.Path:
    path = ROOT / relative
    if not path.is_file():
        raise AssertionError(f"missing frozen file: {relative}")
    actual = sha256(path)
    if actual != expected:
        raise AssertionError(
            f"hash mismatch: {relative}: expected {expected}, got {actual}"
        )
    return path


def validate_frozen_inputs(spec: dict) -> None:
    checked_file(spec["strategy"]["path"], spec["strategy"]["sha256"])
    checked_file(
        spec["verification"]["path"],
        spec["verification"]["sha256"],
    )
    for policy_name in ("baseline", "candidate"):
        policy = spec[policy_name]
        checked_file(
            f"{policy['path']}/main.py",
            policy["main_sha256"],
        )
        checked_file(
            f"{policy['path']}/deck.csv",
            policy["deck_sha256"],
        )
    for runner in spec["runners"].values():
        checked_file(runner["path"], runner["sha256"])
    for relative, expected in spec["engine"]["files"].items():
        checked_file(f"{spec['engine']['path']}/{relative}", expected)
    for opponent in spec["opponents"]:
        checked_file(
            f"{opponent['path']}/main.py",
            opponent["main_sha256"],
        )
        checked_file(
            f"{opponent['path']}/deck.csv",
            opponent["deck_sha256"],
        )
    python = ROOT / spec["python"]
    if not python.is_file():
        raise AssertionError(f"missing frozen Python: {python}")


def panel_command(spec: dict, panel: dict) -> list[str]:
    python = ROOT / spec["python"]
    wrapper = ROOT / spec["runners"]["trace_preservation_wrapper"]["path"]
    output = ROOT / spec["output_root"] / panel["output"]
    command = [
        str(python),
        str(wrapper),
        "--engine-dir",
        str(ROOT / spec["engine"]["path"]),
        "--baseline",
        str(ROOT / spec["baseline"]["path"]),
        "--candidate",
        str(ROOT / spec["candidate"]["path"]),
    ]
    for opponent in panel["opponents"]:
        command.extend(
            [
                "--opponent",
                f"{opponent['label']}={ROOT / opponent['path']}",
            ]
        )
    command.extend(
        [
            "--games-per-seat",
            str(panel["games_per_seat"]),
            "--seed-base",
            str(panel["seed_base"]),
            "--max-steps",
            str(spec["max_steps"]),
            "--output-dir",
            str(output),
        ]
    )
    return command


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Frozen trace-retained H6 v2 fixed-760 executor."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run the expensive frozen schedule after successful preflight.",
    )
    args = parser.parse_args()
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    validate_frozen_inputs(spec)

    output_root = ROOT / spec["output_root"]
    if output_root.exists():
        raise AssertionError(f"refusing existing destination: {output_root}")

    commands = [panel_command(spec, panel) for panel in spec["panels"]]
    preflight = {
        "spec_sha256": sha256(SPEC_PATH),
        "output_root": str(output_root),
        "expected_rows": spec["expected_total_rows"],
        "commands": commands,
        "execute": args.execute,
    }
    print(json.dumps(preflight, indent=2))
    if not args.execute:
        return

    output_root.mkdir(parents=True)
    for command in commands:
        completed = subprocess.run(command, cwd=ROOT, check=False)
        if completed.returncode:
            raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
