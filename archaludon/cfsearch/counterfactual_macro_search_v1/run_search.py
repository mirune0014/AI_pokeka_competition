"""Run the root-action counterfactual MVP and aggregate mechanical outcomes."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable, Mapping


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from common import canonical_sha256, file_sha256, read_jsonl, write_json


ROOT_VALID_FIELDS = (
    "target_observation_sha256",
    "target_option_semantic_ids",
    "selected_action",
    "selected_semantic_id",
)


def _parse_branch_output(stdout: str) -> dict[str, Any]:
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise ValueError("branch process produced no JSON")
    value = json.loads(lines[-1])
    if not isinstance(value, dict):
        raise ValueError("branch output is not an object")
    return value


def _run_branch(
    root_manifest: Path,
    root: Mapping[str, Any],
    branch: str,
    output_dir: Path,
    *,
    alternative_index: int | None = None,
    max_steps: int,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(HERE / "run_branch.py"),
        "--root-manifest", str(root_manifest),
        "--root-id", str(root["root_id"]),
        "--branch", branch,
        "--max-steps", str(max_steps),
    ]
    if alternative_index is not None:
        command.extend(("--alternative-index", str(alternative_index)))
    env = os.environ.copy()
    old_pythonpath = env.get("PYTHONPATH", "")
    paths = [str(REPO_ROOT), str(HERE), str(root["parent_agent_dir"])]
    if old_pythonpath:
        paths.append(old_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    stem = f"{root['root_id']}_{branch}"
    if alternative_index is not None:
        stem += f"_{alternative_index:02d}"
    (output_dir / "logs" / f"{stem}.stdout.txt").write_text(
        completed.stdout,
        encoding="utf-8",
        newline="\n",
    )
    (output_dir / "logs" / f"{stem}.stderr.txt").write_text(
        completed.stderr,
        encoding="utf-8",
        newline="\n",
    )
    try:
        result = _parse_branch_output(completed.stdout)
    except Exception as error:
        result = {
            "schema_version": "archaludon_counterfactual_branch_result.v1",
            "root_id": root["root_id"],
            "branch": branch,
            "alternative_index": alternative_index,
            "status": "subprocess_error",
            "terminal_result": None,
            "action_errors": 0,
            "max_step": False,
            "steps_after_root": 0,
            "final_turn": None,
            "error": f"{type(error).__name__}: {error}",
        }
    result["process_exit_code"] = completed.returncode
    result["command"] = command
    return result


def _parity(
    root: Mapping[str, Any],
    parent_a: Mapping[str, Any],
    parent_b: Mapping[str, Any],
) -> dict[str, Any]:
    differences = {
        field: [parent_a.get(field), parent_b.get(field)]
        for field in ROOT_VALID_FIELDS
        if parent_a.get(field) != parent_b.get(field)
    }
    expected_parent = {
        "selected_action": list(root["parent_action"]),
        "selected_semantic_id": str(root["parent_semantic_id"]),
    }
    # The branch result carries the manifest's expected parent action only as
    # selected_action/selected_semantic_id; compare it with the root contract
    # below rather than treating a stochastic terminal rollout as parity.
    contract_mismatches = {
        field: [parent_a.get(field), expected]
        for field, expected in expected_parent.items()
        if parent_a.get(field) != expected
    }
    for field, expected in expected_parent.items():
        if parent_b.get(field) != expected:
            contract_mismatches[f"parent_b_{field}"] = [parent_b.get(field), expected]
    controls_ok = all(
        result.get("process_exit_code") == 0
        and result.get("forced_action_legal") is True
        and int(result.get("action_errors") or 0) == 0
        and result.get("status") in {"complete", "max_step"}
        and result.get("error") is None
        for result in (parent_a, parent_b)
    )
    mechanically_ok = (
        controls_ok
        and not differences
        and not contract_mismatches
    )
    return {
        "root_id": parent_a.get("root_id"),
        "parent_a_status": parent_a.get("status"),
        "parent_b_status": parent_b.get("status"),
        "fields_checked": list(ROOT_VALID_FIELDS),
        "differences": differences,
        "contract_mismatches": contract_mismatches,
        "execution_controls_ok": controls_ok,
        "root_valid": mechanically_ok,
    }


def _outcome(result: Mapping[str, Any], acting_seat: int) -> str:
    if result.get("status") != "complete":
        return "invalid"
    terminal = result.get("terminal_result")
    if terminal == acting_seat:
        return "win"
    if terminal in (0, 1):
        return "loss"
    if terminal == 2:
        return "draw"
    return "unknown"


def _root_summary(
    root: Mapping[str, Any],
    parent_a: Mapping[str, Any],
    parent_b: Mapping[str, Any],
    alternatives: list[Mapping[str, Any]],
    parity: Mapping[str, Any],
) -> dict[str, Any]:
    acting_seat = int(root["acting_seat"])
    parent_a_outcome = _outcome(parent_a, acting_seat)
    parent_b_outcome = _outcome(parent_b, acting_seat)
    baseline_stable = (
        parent_a_outcome in {"win", "loss", "draw"}
        and parent_b_outcome == parent_a_outcome
    )
    parent_outcome = parent_a_outcome
    rows = []
    for alternative in alternatives:
        alternative_outcome = _outcome(alternative, acting_seat)
        comparable = baseline_stable and alternative_outcome in {"win", "loss", "draw"}
        rows.append({
            "branch": alternative.get("branch"),
            "alternative_index": alternative.get("alternative_index"),
            "semantic_id": alternative.get("selected_semantic_id"),
            "parent_outcome": parent_outcome,
            "alternative_outcome": alternative_outcome,
            "comparison": "comparable" if comparable else "unstable_or_invalid",
            "gain": comparable and parent_outcome != "win" and alternative_outcome == "win",
            "regression": comparable and parent_outcome == "win" and alternative_outcome != "win",
            "status": alternative.get("status"),
        })
    return {
        "root_id": root["root_id"],
        "episode_id": root["episode_id"],
        "replay_step": root["replay_step"],
        "acting_seat": acting_seat,
        "turn": root.get("turn"),
        "root_valid": bool(parity.get("root_valid")),
        "parent_a_outcome": parent_a_outcome,
        "parent_b_outcome": parent_b_outcome,
        "baseline_outcome_stable": baseline_stable,
        "parent_outcome": parent_outcome,
        "alternatives_attempted": len(alternatives),
        "alternatives_completed": sum(row.get("status") == "complete" for row in alternatives),
        "gains": sum(bool(row["gain"]) for row in rows),
        "regressions": sum(bool(row["regression"]) for row in rows),
        "alternative_rows": rows,
        "parity": dict(parity),
    }


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    rows = [dict(row) for row in rows]
    fields = sorted({key for row in rows for key in row}) if rows else ["root_id"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _report(
    output_dir: Path,
    *,
    roots: list[Mapping[str, Any]],
    branch_results: list[Mapping[str, Any]],
    parity_rows: list[Mapping[str, Any]],
    summaries: list[Mapping[str, Any]],
    comparison_spec: Mapping[str, Any],
) -> None:
    gains = sum(int(summary.get("gains", 0)) for summary in summaries)
    regressions = sum(int(summary.get("regressions", 0)) for summary in summaries)
    valid_roots = sum(bool(row.get("root_valid")) for row in parity_rows)
    report = f"""# Counterfactual root-action search MVP report

## Classification

This is a diagnostic harness result only.  It does not promote or modify the
accepted Archaludon agent and it has not accessed Kaggle.

## Method

- accepted parent: `{comparison_spec['parent_agent_dir']}`
- parent main SHA-256: `{comparison_spec['parent_main_sha256']}`
- parent deck SHA-256: `{comparison_spec['parent_deck_sha256']}`
- root method: `target_observation_snapshot_v1`
- branch continuation: unchanged parent policy after one root action
- hidden-world input: fixed safe placeholders, never passed to policy logic
- roots attempted: `{len(roots)}`
- roots ROOT_VALID: `{valid_roots}`
- branch rows: `{len(branch_results)}`
- gains vs parent: `{gains}`
- regressions vs parent: `{regressions}`

## Mechanical controls

    Each root runs parent A and parent B in fresh processes.  `ROOT_VALID` is
the intentionally small root contract: normalized public observation hash,
semantic singleton option set, parent action, and forced-action legality.  The
two terminal rollouts are not required to have identical wins, turns, or step
counts because the local engine has no reproducible RNG seed.  Process exit and
action-error controls are still recorded; alternatives are diagnostic rows and
are not adopted automatically.

## Limitations

This MVP intentionally uses a small root corpus and one-action interventions.
It is not a fixed760 evaluation and does not justify a rule change.  The next
step is to inspect the branch rows and expand the root corpus using diverse
replays before considering any rule hypothesis.
"""
    (output_dir / "REPORT.md").write_text(report, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-steps", type=int, default=160)
    args = parser.parse_args()
    if args.max_steps < 1:
        raise SystemExit("--max-steps must be positive")
    root_manifest = args.root_manifest.resolve()
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "logs").mkdir(parents=True, exist_ok=True)
    roots = read_jsonl(root_manifest)
    if not roots:
        raise SystemExit("root manifest is empty")

    first = roots[0]
    comparison_spec = {
        "schema_version": "archaludon_counterfactual_comparison_spec.v1",
        "root_manifest": str(root_manifest),
        "root_manifest_sha256": file_sha256(root_manifest),
        "parent_agent_dir": first["parent_agent_dir"],
        "parent_main_sha256": first["parent_main_sha256"],
        "parent_deck_sha256": first["parent_deck_sha256"],
        "root_ids": [root["root_id"] for root in roots],
        "branches": ["parent_a", "parent_b", "alternative"],
        "max_steps": args.max_steps,
        "hidden_world_policy": "fixed_public_safe_placeholders_v1",
        "root_valid_fields": list(ROOT_VALID_FIELDS),
        "outcome_comparison": "only classify gain/regression when parent A/B outcomes agree",
    }
    write_json(output_dir / "comparison_spec.json", comparison_spec)

    branch_results: list[dict[str, Any]] = []
    parity_rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for root in roots:
        parent_a = _run_branch(root_manifest, root, "parent_a", output_dir, max_steps=args.max_steps)
        parent_b = _run_branch(root_manifest, root, "parent_b", output_dir, max_steps=args.max_steps)
        branch_results.extend((parent_a, parent_b))
        parity = _parity(root, parent_a, parent_b)
        parity_rows.append(parity)
        alternatives: list[dict[str, Any]] = []
        if parity["root_valid"]:
            for alternative_index, _alternative in enumerate(root.get("alternatives") or []):
                result = _run_branch(
                    root_manifest,
                    root,
                    "alternative",
                    output_dir,
                    alternative_index=alternative_index,
                    max_steps=args.max_steps,
                )
                alternatives.append(result)
                branch_results.append(result)
        else:
            alternatives.append({
                "root_id": root["root_id"],
                "branch": "alternative",
                "status": "skipped_parent_parity_failed",
                "error": "ROOT_VALID failed; alternatives were not executed",
            })
        summaries.append(_root_summary(root, parent_a, parent_b, alternatives, parity))

    write_json(output_dir / "parity_report.json", {"rows": parity_rows})
    write_json(output_dir / "root_summary.json", {"rows": summaries})
    (output_dir / "branch_results.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in branch_results),
        encoding="utf-8",
        newline="\n",
    )
    _write_csv(output_dir / "branch_results.csv", branch_results)
    _report(
        output_dir,
        roots=roots,
        branch_results=branch_results,
        parity_rows=parity_rows,
        summaries=summaries,
        comparison_spec=comparison_spec,
    )
    print(json.dumps({
        "output": str(output_dir),
        "roots": len(roots),
        "root_valid": sum(bool(row["root_valid"]) for row in parity_rows),
        "branch_rows": len(branch_results),
        "gains": sum(int(row.get("gains", 0)) for row in summaries),
        "regressions": sum(int(row.get("regressions", 0)) for row in summaries),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
