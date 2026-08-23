"""Execute the final current-turn Active-attack unlock diagnostic.

This is an execution-only wrapper. It does not select roots, infer a winner,
or create a candidate. Each selected root is replayed once with the accepted
parent action and once with the same Energy serial attached to Active.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_roots(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_one(
    python: Path,
    branch_script: Path,
    engine_dir: Path,
    parent_agent: Path,
    roots_path: Path,
    root_id: str,
    branch: str,
    max_steps: int,
    log_dir: Path,
) -> dict[str, Any]:
    command = [
        str(python),
        str(branch_script),
        "--engine-dir",
        str(engine_dir),
        "--parent-agent",
        str(parent_agent),
        "--roots",
        str(roots_path),
        "--root-id",
        root_id,
        "--branch",
        branch,
        "--max-steps",
        str(max_steps),
    ]
    proc = subprocess.run(
        command,
        cwd=str(parent_agent.parents[2]),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    stem = f"{root_id}__{branch}"
    (log_dir / f"{stem}.stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (log_dir / f"{stem}.stderr.txt").write_text(proc.stderr, encoding="utf-8")
    payload: dict[str, Any]
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    try:
        payload = json.loads(lines[-1])
    except Exception as exc:
        payload = {
            "schema_version": "archaludon_current_turn_attack_unlock_branch.v1",
            "root_id": root_id,
            "branch": branch,
            "status": "runner_json_error",
            "runner_json_error": f"{type(exc).__name__}: {exc}",
        }
    payload["runner_exit_code"] = proc.returncode
    payload["runner_stdout_sha256"] = sha256_file(log_dir / f"{stem}.stdout.txt")
    payload["runner_stderr_sha256"] = sha256_file(log_dir / f"{stem}.stderr.txt")
    payload["command"] = command
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--branch-script", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--parent-agent", type=Path, required=True)
    parser.add_argument("--roots", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-steps", type=int, default=1000)
    args = parser.parse_args()

    output = args.output / args.run_id
    output.mkdir(parents=True, exist_ok=False)
    logs = output / "logs"
    logs.mkdir()
    roots = load_roots(args.roots)
    selected_copy = output / "selected_roots.jsonl"
    selected_copy.write_text(
        "".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in roots),
        encoding="utf-8",
    )
    spec = {
        "schema_version": "archaludon_current_turn_attack_unlock_comparison_spec.v1",
        "diagnostic": "T7_CURRENT_TURN_ATTACK_UNLOCK_BY_ATTACH_DIAGNOSTIC_V1",
        "accepted_parent": str(args.parent_agent.resolve()),
        "parent_main_sha256": sha256_file(args.parent_agent / "main.py"),
        "parent_deck_sha256": sha256_file(args.parent_agent / "deck.csv"),
        "engine_dir": str(args.engine_dir.resolve()),
        "roots_source": str(args.roots.resolve()),
        "roots_sha256": sha256_file(args.roots),
        "root_count": len(roots),
        "branches": ["parent", "active"],
        "same_seed_both_branches": True,
        "public_boundary": "root hash/legal semantic set/parent parity; post-attach same-player MAIN callback",
        "holdout_opened": False,
        "candidate_created": False,
        "max_steps": args.max_steps,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    (output / "comparison_spec.json").write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    rows: list[dict[str, Any]] = []
    for root in roots:
        root_id = str(root["root_id"])
        for branch in ("parent", "active"):
            rows.append(
                run_one(
                    args.python,
                    args.branch_script,
                    args.engine_dir,
                    args.parent_agent,
                    args.roots,
                    root_id,
                    branch,
                    args.max_steps,
                    logs,
                )
            )
    branch_path = output / "branch_results.jsonl"
    branch_path.write_text(
        "".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    execution_summary = {
        "schema_version": "archaludon_current_turn_attack_unlock_execution.v1",
        "roots": len(roots),
        "branches": len(rows),
        "complete": sum(row.get("status") == "complete" for row in rows),
        "invalid_or_failed": sum(row.get("status") != "complete" for row in rows),
        "engine_import_ok": sum(row.get("engine_import_ok") is True for row in rows),
        "action_errors": sum(int(row.get("action_errors") or 0) for row in rows),
        "max_step": sum(bool(row.get("hit_max_steps")) for row in rows),
        "duplicate_control": "root pair identity is keyed by selected root_id and branch",
        "candidate_created": False,
    }
    (output / "execution_summary.json").write_text(json.dumps(execution_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **execution_summary}, ensure_ascii=True, sort_keys=True))
    if execution_summary["invalid_or_failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
