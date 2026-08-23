"""Execute the frozen T3/T4 Boss-versus-front-attack comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_one(python: Path, script: Path, engine: Path, parent: Path, roots: Path, root: dict[str, Any], branch: str, output: Path, attack_id: int | None, max_steps: int) -> dict[str, Any]:
    command = [str(python), str(script), "--engine-dir", str(engine), "--parent-agent", str(parent), "--roots", str(roots), "--root-id", str(root["root_id"]), "--branch", branch, "--max-steps", str(max_steps)]
    if attack_id is not None:
        command.extend(["--attack-id", str(attack_id)])
    proc = subprocess.run(command, cwd=str(parent.parents[2]), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    stem = f"{root['root_id']}__{branch}{'_'+str(attack_id) if attack_id is not None else ''}"
    stdout = output / "logs" / f"{stem}.stdout.txt"
    stderr = output / "logs" / f"{stem}.stderr.txt"
    stdout.write_text(proc.stdout, encoding="utf-8")
    stderr.write_text(proc.stderr, encoding="utf-8")
    payload: dict[str, Any]
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    try:
        payload = json.loads(lines[-1])
    except Exception as exc:
        payload = {"schema_version": "archaludon_boss_vs_front_attack_branch.v1", "root_id": root["root_id"], "branch": branch, "forced_attack_id": attack_id, "status": "runner_json_error", "runner_json_error": f"{type(exc).__name__}: {exc}"}
    payload.update({
        "runner_exit_code": proc.returncode,
        "runner_stdout_sha256": sha256_file(stdout),
        "runner_stderr_sha256": sha256_file(stderr),
        "command": command,
    })
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--branch-script", type=Path, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--parent-agent", type=Path, required=True)
    parser.add_argument("--selected-roots", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-steps", type=int, default=1000)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / "logs").mkdir()
    roots = rows(args.selected_roots)
    (out / "selected_roots.jsonl").write_text("".join(json.dumps(root, ensure_ascii=True, sort_keys=True) + "\n" for root in roots), encoding="utf-8")
    spec = {
        "schema_version": "archaludon_boss_vs_front_attack_comparison_spec.v1",
        "diagnostic": "T3_T4_BOSS_VS_FRONT_ATTACK_FORMAL_ROUTE_DIAGNOSTIC_V1",
        "accepted_parent": str(args.parent_agent.resolve()),
        "parent_main_sha256": sha256_file(args.parent_agent / "main.py"),
        "parent_deck_sha256": sha256_file(args.parent_agent / "deck.csv"),
        "engine_dir": str(args.engine_dir.resolve()),
        "selected_roots": str(args.selected_roots.resolve()),
        "selected_roots_sha256": sha256_file(args.selected_roots),
        "root_count": len(roots),
        "branch_contract": ["PARENT_BASELINE", "FORCE_BOSS", "FORCE_FRONT_ATTACK_<attack_id>"],
        "forced_surface": "only first policy-seat action; all later callbacks accepted parent",
        "root_public_boundary": ["normalized_public_hash", "legal_semantic_action_set", "parent_semantic_action", "forced_legal_semantic_action"],
        "schedule_split": "sha256(schedule_key.encode('utf-8')) % 100; discovery 0-64; holdout 65-89; reserve 90-99",
        "holdout_opened": False,
        "reserve_opened": False,
        "candidate_created": False,
        "kaggle_accessed": False,
        "max_steps": args.max_steps,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    (out / "comparison_spec.json").write_text(json.dumps(spec, sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    results: list[dict[str, Any]] = []
    for number, root in enumerate(roots, 1):
        branches: list[tuple[str, int | None]] = [("parent", None), ("boss", None)]
        branches.extend(("front", int(item["attack_id"])) for item in root.get("front_attacks") or [])
        for branch, attack_id in branches:
            result = run_one(args.python, args.branch_script, args.engine_dir, args.parent_agent, args.selected_roots, root, branch, out, attack_id, args.max_steps)
            result["root_sequence"] = number
            results.append(result)
    (out / "branch_results.jsonl").write_text("".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in results), encoding="utf-8")
    summary = {
        "schema_version": "archaludon_boss_vs_front_attack_execution.v1",
        "root_count": len(roots),
        "branch_count": len(results),
        "complete": sum(row.get("status") == "complete" for row in results),
        "invalid_or_failed": sum(row.get("status") != "complete" for row in results),
        "engine_import_ok": sum(row.get("engine_import_ok") is True for row in results),
        "root_match": sum(row.get("root_match") is True for row in results),
        "forced_legal": sum(row.get("forced_legal") is True for row in results),
        "action_errors": sum(int(row.get("action_errors") or 0) for row in results),
        "max_step": sum(bool(row.get("hit_max_steps")) for row in results),
        "duplicate_control": "root_id plus branch and forced attack id; every branch has exact seed",
        "candidate_created": False,
    }
    (out / "execution_summary.json").write_text(json.dumps(summary, sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), **summary}, sort_keys=True, ensure_ascii=True))
    if summary["invalid_or_failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
