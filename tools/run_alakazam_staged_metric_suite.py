"""Run deterministic sidecar instrumentation over staged Alakazam versions.

The checked paired runner remains the authority for wins.  This launcher only
collects independent diagnostic evidence with the same seeds and seats.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Sequence

from alakazam_staged_metrics import SCHEMA_VERSION, sha256_file


ROOT = Path(__file__).resolve().parents[1]
RUN_LOCAL_BATTLE = ROOT / "tools" / "run_local_battle.py"
DEFAULT_SEED_BASES = (202608500, 202608510, 202608520, 202608530, 202608540)
ADAPTER_SOURCE = """\
from alakazam_staged_metrics import build_metric_entrypoint

agent, _module = build_metric_entrypoint(
    adapter_file=__file__,
    module_name=__name__,
    version={version!r},
    target_dir={target!r},
)
__all__ = ["agent"]
"""


def named_path(value: str) -> tuple[str, Path]:
    name, separator, raw_path = value.partition("=")
    if not separator or not name or not raw_path:
        raise argparse.ArgumentTypeError("expected NAME=PATH")
    if any(char in name for char in "\\/:"):
        raise argparse.ArgumentTypeError(f"unsafe name: {name!r}")
    return name, Path(raw_path)


def require_fresh(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"fresh --output-dir required; already exists: {path}")


def json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_adapter(
    output_dir: Path, version: str, target: Path, deck: Path | None
) -> Path:
    adapter = output_dir / "metric_adapters" / version
    adapter.mkdir(parents=True, exist_ok=False)
    target = target.resolve()
    source_deck = (deck or (target / "deck.csv")).resolve()
    if not (target / "main.py").is_file():
        raise FileNotFoundError(target / "main.py")
    if not source_deck.is_file():
        raise FileNotFoundError(source_deck)
    (adapter / "main.py").write_text(
        ADAPTER_SOURCE.format(version=version, target=str(target)),
        encoding="utf-8",
        newline="\n",
    )
    shutil.copyfile(source_deck, adapter / "deck.csv")
    json_dump(
        adapter / "adapter_manifest.json",
        {
            "schema_version": SCHEMA_VERSION,
            "version": version,
            "target": str(target),
            "target_main_sha256": sha256_file(target / "main.py"),
            "source_deck": str(source_deck),
            "source_deck_sha256": sha256_file(source_deck),
            "generated_main_sha256": sha256_file(adapter / "main.py"),
        },
    )
    return adapter


def build_command(
    *,
    python_executable: str,
    engine_dir: Path,
    adapter_dir: Path,
    opponent_dir: Path,
    policy_seat: int,
    games: int,
    max_steps: int,
    seed_base: int,
    summary: Path,
    trace_dir: Path,
) -> list[str]:
    if policy_seat == 0:
        agent_a, deck_a = adapter_dir, adapter_dir / "deck.csv"
        agent_b, deck_b = opponent_dir, opponent_dir / "deck.csv"
    else:
        agent_a, deck_a = opponent_dir, opponent_dir / "deck.csv"
        agent_b, deck_b = adapter_dir, adapter_dir / "deck.csv"
    return [
        python_executable,
        str(RUN_LOCAL_BATTLE),
        "--engine-dir",
        str(engine_dir),
        "--agent-a",
        str(agent_a),
        "--deck-a",
        str(deck_a),
        "--agent-b",
        str(agent_b),
        "--deck-b",
        str(deck_b),
        "--games",
        str(games),
        "--max-steps",
        str(max_steps),
        "--seed-base",
        str(seed_base),
        "--engine-seed",
        "--summary",
        str(summary),
        "--trace-dir",
        str(trace_dir),
    ]


def write_bytes(path: Path, value: str | bytes | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(value or "", encoding="utf-8", newline="\n")


def summary_status(path: Path, expected: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if path.is_file():
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"INVALID_JSON_LINE_{line_number}")
                continue
            if isinstance(value, dict):
                rows.append(value)
            else:
                errors.append(f"NON_OBJECT_LINE_{line_number}")
    else:
        errors.append("SUMMARY_MISSING")
    actual_games = sorted(
        value
        for row in rows
        if (value := row.get("game")) is not None
    )
    expected_games = list(range(expected))
    if actual_games != expected_games:
        errors.append("GAME_INDEX_SET_MISMATCH")
    return {
        "rows": len(rows),
        "expected_rows": expected,
        "game_indices": actual_games,
        "complete_game_index_set": actual_games == expected_games,
        "parse_errors": errors,
    }


def execute_block(
    *,
    command: Sequence[str],
    environment: dict[str, str],
    timeout_seconds: float,
    block_dir: Path,
    expected_games: int,
) -> dict[str, Any]:
    started_ns = time.time_ns()
    timed_out = False
    return_code: int | None = None
    stdout: str | bytes | None = ""
    stderr: str | bytes | None = ""
    try:
        completed = subprocess.run(
            list(command),
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return_code = completed.returncode
        stdout, stderr = completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout, stderr = exc.stdout, exc.stderr
    ended_ns = time.time_ns()
    stdout_path = block_dir / "stdout.txt"
    stderr_path = block_dir / "stderr.txt"
    write_bytes(stdout_path, stdout)
    write_bytes(stderr_path, stderr)
    summary_path = block_dir / "summary.jsonl"
    status = summary_status(summary_path, expected_games)
    record = {
        "started_ns": started_ns,
        "ended_ns": ended_ns,
        "elapsed_ns": ended_ns - started_ns,
        "timeout_seconds": timeout_seconds,
        "timed_out": timed_out,
        "return_code": return_code,
        "command": list(command),
        "summary_status": status,
        "stdout": str(stdout_path),
        "stdout_sha256": sha256_file(stdout_path),
        "stderr": str(stderr_path),
        "stderr_sha256": sha256_file(stderr_path),
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path) if summary_path.is_file() else None,
        "block_complete": (
            not timed_out
            and return_code == 0
            and status["complete_game_index_set"]
            and not status["parse_errors"]
        ),
    }
    json_dump(block_dir / "block_execution.json", record)
    return record


def run_suite(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output_dir.resolve()
    require_fresh(output)
    output.mkdir(parents=True)
    engine = args.engine_dir.resolve()
    if not (engine / "cg" / "game.py").is_file():
        raise FileNotFoundError(engine / "cg" / "game.py")
    versions: list[tuple[str, Path, Path | None]] = [
        (name, path.resolve(), None) for name, path in args.version
    ]
    version_names = [name for name, _, _ in versions]
    if len(version_names) != len(set(version_names)):
        raise ValueError("duplicate --version name")
    opponents = [(name, path.resolve()) for name, path in args.opponent]
    opponent_names = [name for name, _ in opponents]
    if len(opponent_names) != len(set(opponent_names)):
        raise ValueError("duplicate --opponent name")
    for _, path in opponents:
        if not (path / "main.py").is_file() or not (path / "deck.csv").is_file():
            raise FileNotFoundError(f"opponent package incomplete: {path}")
    adapters = {
        name: write_adapter(output, name, target, deck)
        for name, target, deck in versions
    }
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "launcher": str(Path(__file__).resolve()),
        "launcher_sha256": sha256_file(Path(__file__).resolve()),
        "common_module_sha256": sha256_file(
            Path(__file__).with_name("alakazam_staged_metrics.py")
        ),
        "run_local_battle": str(RUN_LOCAL_BATTLE),
        "run_local_battle_sha256": sha256_file(RUN_LOCAL_BATTLE),
        "engine_dir": str(engine),
        "versions": [
            {"name": name, "target": str(target), "adapter": str(adapters[name])}
            for name, target, _ in versions
        ],
        "opponents": [
            {
                "name": name,
                "path": str(path),
                "main_sha256": sha256_file(path / "main.py"),
                "deck_sha256": sha256_file(path / "deck.csv"),
            }
            for name, path in opponents
        ],
        "seed_bases": list(args.seed_base),
        "games_per_block": args.games_per_block,
        "seats": [0, 1],
        "max_steps": args.max_steps,
        "watchdog_seconds": args.watchdog_seconds,
        "python_executable": str(Path(sys.executable).resolve()),
    }
    json_dump(output / "suite_manifest.json", manifest)
    blocks: list[dict[str, Any]] = []
    for version, _, _ in versions:
        for opponent, opponent_path in opponents:
            for seed_base in args.seed_base:
                for seat in (0, 1):
                    run_id = f"{version}__{opponent}__{seed_base}__p{seat}"
                    block_dir = (
                        output
                        / "runs"
                        / version
                        / opponent
                        / f"seed_{seed_base}"
                        / f"seat_{seat}"
                    )
                    block_dir.mkdir(parents=True, exist_ok=False)
                    sidecar_dir = block_dir / "sidecars"
                    summary_path = block_dir / "summary.jsonl"
                    trace_dir = block_dir / "battle_traces"
                    command = build_command(
                        python_executable=sys.executable,
                        engine_dir=engine,
                        adapter_dir=adapters[version],
                        opponent_dir=opponent_path,
                        policy_seat=seat,
                        games=args.games_per_block,
                        max_steps=args.max_steps,
                        seed_base=seed_base,
                        summary=summary_path,
                        trace_dir=trace_dir,
                    )
                    environment = dict(os.environ)
                    environment.update(
                        {
                            "ALAKAZAM_METRIC_RUN_ID": run_id,
                            "ALAKAZAM_METRIC_VERSION": version,
                            "ALAKAZAM_METRIC_OPPONENT": opponent,
                            "ALAKAZAM_METRIC_POLICY_SEAT": str(seat),
                            "ALAKAZAM_METRIC_SEED_BASE": str(seed_base),
                            "ALAKAZAM_METRIC_SIDECAR_DIR": str(sidecar_dir),
                        }
                    )
                    execution = execute_block(
                        command=command,
                        environment=environment,
                        timeout_seconds=args.watchdog_seconds,
                        block_dir=block_dir,
                        expected_games=args.games_per_block,
                    )
                    block = {
                        "run_id": run_id,
                        "version": version,
                        "opponent": opponent,
                        "seed_base": seed_base,
                        "seat": seat,
                        "block_dir": str(block_dir),
                        **execution,
                    }
                    blocks.append(block)
                    with (output / "block_ledger.jsonl").open(
                        "a", encoding="utf-8", newline="\n"
                    ) as handle:
                        handle.write(
                            json.dumps(
                                block, ensure_ascii=False, sort_keys=True
                            )
                            + "\n"
                        )
                        handle.flush()
                        os.fsync(handle.fileno())
    result = {
        "schema_version": SCHEMA_VERSION,
        "output_dir": str(output),
        "blocks": len(blocks),
        "complete_blocks": sum(bool(row["block_complete"]) for row in blocks),
        "failed_or_partial_blocks": sum(
            not bool(row["block_complete"]) for row in blocks
        ),
        "all_blocks_complete": all(bool(row["block_complete"]) for row in blocks),
    }
    json_dump(output / "suite_execution_summary.json", result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument(
        "--version", action="append", type=named_path, required=True, metavar="NAME=PATH"
    )
    parser.add_argument(
        "--opponent", action="append", type=named_path, required=True, metavar="NAME=PATH"
    )
    parser.add_argument(
        "--seed-base",
        action="append",
        type=int,
        default=None,
        help="Repeat for each fixed 10-game seed block.",
    )
    parser.add_argument("--games-per-block", type=int, default=10)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--watchdog-seconds", type=float, default=180.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.seed_base is None:
        args.seed_base = list(DEFAULT_SEED_BASES)
    if args.games_per_block <= 0:
        parser.error("--games-per-block must be positive")
    if args.max_steps <= 0:
        parser.error("--max-steps must be positive")
    if args.watchdog_seconds <= 0:
        parser.error("--watchdog-seconds must be positive")
    return args


def main() -> None:
    result = run_suite(parse_args())
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    if not result["all_blocks_complete"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
