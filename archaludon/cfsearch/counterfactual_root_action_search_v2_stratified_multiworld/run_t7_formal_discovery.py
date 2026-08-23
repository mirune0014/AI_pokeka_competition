"""Run formal realized-world T7 branches for a selected root set."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
BRANCH_RUNNER = HERE / "run_realized_counterfactual.py"


def _parse_last(stdout: str) -> dict[str, Any]:
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        return {"status": "subprocess_no_json"}
    try:
        value = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        return {"status": "subprocess_bad_json", "error": str(exc), "stdout_tail": lines[-1][-2000:]}
    return value if isinstance(value, dict) else {"status": "subprocess_bad_json"}


def _outcome(result: dict[str, Any], seat: int) -> str:
    if result.get("status") != "complete" or not result.get("root_match"):
        return "invalid"
    terminal = result.get("terminal_result")
    if terminal == seat:
        return "win"
    if terminal in (0, 1):
        return "loss"
    if terminal == 2:
        return "draw"
    return "unknown"


def _run_branch(args: argparse.Namespace, root: dict[str, Any], branch: str, semantic: str, output_dir: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        str(BRANCH_RUNNER),
        "--engine-dir", str(args.engine_dir.resolve()),
        "--parent-agent", str(args.parent_agent.resolve()),
        "--roots-file", str(args.roots.resolve()),
        "--root-id", str(root["root_id"]),
        "--branch", branch,
        "--max-steps", str(args.max_steps),
    ]
    if branch == "alternative":
        command.extend(("--alternative-semantic", semantic))
    started = time.monotonic()
    completed = subprocess.run(command, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
    result = _parse_last(completed.stdout)
    result.update({
        "process_exit_code": int(completed.returncode),
        "command": command,
        "runtime_seconds": time.monotonic() - started,
        "branch": branch,
        "alternative_semantic_id": semantic,
    })
    stem = f"{root['root_id']}_{branch}_{semantic[:12] if semantic else 'parent'}"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{stem}.stdout.txt").write_text(completed.stdout or "", encoding="utf-8", newline="\n")
    (output_dir / f"{stem}.stderr.txt").write_text(completed.stderr or "", encoding="utf-8", newline="\n")
    return result


def run(args: argparse.Namespace) -> dict[str, Any]:
    roots = [json.loads(line) for line in args.roots.read_text(encoding="utf-8").splitlines() if line.strip()]
    output_dir = args.output.resolve()
    logs_dir = output_dir / "logs"
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for index, root in enumerate(roots):
        parent = _run_branch(args, root, "parent", "", logs_dir)
        parent["root_id"] = root["root_id"]
        parent["opponent_family"] = root.get("opponent_family")
        parent["policy_seat"] = root.get("policy_seat")
        rows.append(parent)
        if parent.get("status") != "complete" or not parent.get("root_match"):
            failures.append(f"parent branch invalid: {root['root_id']}")
            if args.stop_on_failure:
                break
        for alternative in root.get("alternative_semantics") or []:
            semantic = str(alternative.get("semantic_id"))
            result = _run_branch(args, root, "alternative", semantic, logs_dir)
            result["root_id"] = root["root_id"]
            result["opponent_family"] = root.get("opponent_family")
            result["policy_seat"] = root.get("policy_seat")
            result["transformation"] = alternative.get("transformation")
            result["selected_action_expected"] = alternative.get("action")
            rows.append(result)
            if result.get("status") != "complete" or not result.get("root_match"):
                failures.append(f"alternative branch invalid: {root['root_id']} {semantic}")
                if args.stop_on_failure:
                    break
        if failures and args.stop_on_failure:
            break
        if index and index % 8 == 0:
            print(json.dumps({"progress_roots": index + 1, "rows": len(rows), "failures": len(failures)}, ensure_ascii=True), flush=True)

    rows_path = output_dir / "branch_results.jsonl"
    rows_path.write_text("".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows), encoding="utf-8", newline="\n")
    parent_by_root = {str(row.get("root_id")): row for row in rows if row.get("branch") == "parent"}
    comparable: list[dict[str, Any]] = []
    for row in rows:
        if row.get("branch") != "alternative":
            continue
        parent = parent_by_root.get(str(row.get("root_id")))
        if not parent:
            continue
        seat = int(row.get("policy_seat"))
        parent_outcome = _outcome(parent, seat)
        alt_outcome = _outcome(row, seat)
        comparable.append({
            "root_id": row.get("root_id"),
            "opponent_family": row.get("opponent_family"),
            "policy_seat": seat,
            "semantic_id": row.get("alternative_semantic_id"),
            "transformation": row.get("transformation"),
            "parent_outcome": parent_outcome,
            "alternative_outcome": alt_outcome,
            "gain": parent_outcome != "win" and alt_outcome == "win",
            "regression": parent_outcome == "win" and alt_outcome != "win",
            "comparable": parent_outcome in {"win", "loss", "draw"} and alt_outcome in {"win", "loss", "draw"},
            "root_match": bool(row.get("root_match") and parent.get("root_match")),
            "action_errors": int(row.get("action_errors") or 0) + int(parent.get("action_errors") or 0),
            "hit_max_steps": bool(row.get("hit_max_steps") or parent.get("hit_max_steps")),
        })
    valid_comparable = [row for row in comparable if row["comparable"] and row["root_match"] and not row["action_errors"] and not row["hit_max_steps"]]
    report = {
        "schema_version": "archaludon_formal_realized_t7_discovery_report.v1",
        "source_kind": "FORMAL_REALIZED_SEEDED_WORLD",
        "roots_requested": len(roots),
        "rows": len(rows),
        "parent_rows": sum(row.get("branch") == "parent" for row in rows),
        "alternative_rows": sum(row.get("branch") == "alternative" for row in rows),
        "valid_root_matches": sum(bool(row.get("root_match")) for row in rows),
        "action_errors": sum(int(row.get("action_errors") or 0) for row in rows),
        "max_step_hits": sum(bool(row.get("hit_max_steps")) for row in rows),
        "failures": failures,
        "comparable_alternatives": len(valid_comparable),
        "gains": sum(bool(row["gain"]) for row in valid_comparable),
        "regressions": sum(bool(row["regression"]) for row in valid_comparable),
        "net": sum(bool(row["gain"]) for row in valid_comparable) - sum(bool(row["regression"]) for row in valid_comparable),
        "distinct_roots_with_gain": len({row["root_id"] for row in valid_comparable if row["gain"]}),
        "distinct_games_not_inferred": None,
        "opponent_families": sorted({str(row.get("opponent_family")) for row in valid_comparable}),
        "seats": sorted({int(row.get("policy_seat")) for row in valid_comparable}),
        "adoption_status": "DISCOVERY_ONLY_NO_HYPOTHESIS",
    }
    (output_dir / "comparable_rows.jsonl").write_text("".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in comparable), encoding="utf-8", newline="\n")
    (output_dir / "REPORT.json").write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--parent-agent", type=Path, required=True)
    parser.add_argument("--roots", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--stop-on-failure", action="store_true")
    args = parser.parse_args()
    report = run(args)
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    if report["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
