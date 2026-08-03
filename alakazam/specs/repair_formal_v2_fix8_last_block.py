"""Recover the one formal-v2 block interrupted by the 30-minute host limit.

This script calls the frozen metric launcher's own ``build_command`` and
``execute_block`` helpers.  It appends exactly one checked ledger row only
after the ten-game block is complete.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY))
sys.path.insert(0, str(REPOSITORY / "infrastructure" / "tools"))

from infrastructure.tools.run_alakazam_staged_metric_suite import (
    SCHEMA_VERSION,
    build_command,
    execute_block,
    json_dump,
)


SUITE = (
    REPOSITORY
    / "alakazam"
    / "metrics"
    / "formal_v2_fix8_aligned_7opp_50seed"
)
VERSION = "v2"
OPPONENT = "direct_frozen"
SEED_BASE = 202608540
SEAT = 1
EXPECTED_GAMES = 10


def main() -> None:
    manifest = json.loads((SUITE / "suite_manifest.json").read_text(encoding="utf-8"))
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise RuntimeError("suite schema changed")
    if manifest["seed_bases"] != [
        202608500,
        202608510,
        202608520,
        202608530,
        202608540,
    ]:
        raise RuntimeError("unexpected seed schedule")

    version_entry = next(
        row for row in manifest["versions"] if row["name"] == VERSION
    )
    opponent_entry = next(
        row for row in manifest["opponents"] if row["name"] == OPPONENT
    )
    adapter = Path(version_entry["adapter"]).resolve()
    opponent = Path(opponent_entry["path"]).resolve()
    engine = Path(manifest["engine_dir"]).resolve()

    block_dir = (
        SUITE
        / "runs"
        / VERSION
        / OPPONENT
        / f"seed_{SEED_BASE}"
        / f"seat_{SEAT}"
    )
    block_dir.mkdir(parents=True, exist_ok=False)
    sidecar_dir = block_dir / "sidecars"
    summary_path = block_dir / "summary.jsonl"
    trace_dir = block_dir / "battle_traces"
    run_id = f"{VERSION}__{OPPONENT}__{SEED_BASE}__p{SEAT}"

    command = build_command(
        python_executable=str(Path(manifest["python_executable"]).resolve()),
        engine_dir=engine,
        adapter_dir=adapter,
        opponent_dir=opponent,
        policy_seat=SEAT,
        games=EXPECTED_GAMES,
        max_steps=int(manifest["max_steps"]),
        seed_base=SEED_BASE,
        summary=summary_path,
        trace_dir=trace_dir,
    )
    environment = dict(os.environ)
    environment.update(
        {
            "ALAKAZAM_METRIC_RUN_ID": run_id,
            "ALAKAZAM_METRIC_VERSION": VERSION,
            "ALAKAZAM_METRIC_OPPONENT": OPPONENT,
            "ALAKAZAM_METRIC_POLICY_SEAT": str(SEAT),
            "ALAKAZAM_METRIC_SEED_BASE": str(SEED_BASE),
            "ALAKAZAM_METRIC_SIDECAR_DIR": str(sidecar_dir),
        }
    )
    execution = execute_block(
        command=command,
        environment=environment,
        timeout_seconds=float(manifest["watchdog_seconds"]),
        block_dir=block_dir,
        expected_games=EXPECTED_GAMES,
    )
    block = {
        "run_id": run_id,
        "version": VERSION,
        "opponent": OPPONENT,
        "seed_base": SEED_BASE,
        "seat": SEAT,
        "block_dir": str(block_dir),
        **execution,
    }
    if not block["block_complete"]:
        raise RuntimeError(f"recovery block incomplete: {block}")

    ledger_path = SUITE / "block_ledger.jsonl"
    existing = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(existing) != 69:
        raise RuntimeError(f"expected 69 preserved rows, found {len(existing)}")
    if any(row["run_id"] == run_id for row in existing):
        raise RuntimeError(f"duplicate ledger run_id: {run_id}")

    with ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(block, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())

    completed = existing + [block]
    result = {
        "schema_version": SCHEMA_VERSION,
        "output_dir": str(SUITE.resolve()),
        "blocks": len(completed),
        "complete_blocks": sum(bool(row["block_complete"]) for row in completed),
        "failed_or_partial_blocks": sum(
            not bool(row["block_complete"]) for row in completed
        ),
        "all_blocks_complete": all(
            bool(row["block_complete"]) for row in completed
        ),
        "recovery": {
            "reason": "host process limit interrupted the original final block",
            "recovered_run_id": run_id,
            "launcher_helpers": [
                "build_command",
                "execute_block",
                "json_dump",
            ],
            "quarantined_partial": str(
                SUITE
                / "quarantine_timeout_partial"
                / "direct_frozen_seed_202608540_seat_1"
            ),
        },
    }
    json_dump(SUITE / "suite_execution_summary.json", result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
