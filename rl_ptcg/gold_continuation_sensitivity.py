"""Audit selected Gold teacher actions across continuation-policy heads."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .gold_oracle_runner import verify_oracle_output
from .gold_oracle_states import canonical_sha256, write_once
from .gold_teacher_refinement_selection import verify_refinement_selection
from .kaggle_rollout_source_receipt import verify_kaggle_rollout_source_receipt


SCHEMA_VERSION = "gold_continuation_sensitivity.v1"


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="ascii"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object: %s" % path)
    return value


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _self_hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _relative_inside(path: Path, root: Path, label: str) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("%s escapes audit workspace" % label) from error
    return str(relative).replace("\\", "/") or "."


def _selected_states(selection: Mapping[str, Any]) -> list[dict[str, Any]]:
    states = selection.get("states")
    if not isinstance(states, list):
        raise ValueError("refinement selection has no states")
    selected = [dict(item) for item in states if isinstance(item, Mapping) and item.get("selected")]
    if not selected or int(selection.get("selected_count", -1)) != len(selected):
        raise ValueError("invalid selected state count")
    for item in selected:
        best = item.get("best_nonbaseline")
        if not isinstance(best, Mapping) or not isinstance(best.get("action"), str):
            raise ValueError("selected state has no target action")
        if not isinstance(item.get("baseline_action"), str):
            raise ValueError("selected state has no baseline action")
    return selected


def summarize_shard_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    continuation_policy_ids: Sequence[str],
    candidate_ids: Sequence[str],
    target_action: str,
    baseline_action: str,
) -> list[dict[str, Any]]:
    """Return weighted target-versus-baseline results for one state/batch shard."""
    continuation_ids = list(map(str, continuation_policy_ids))
    candidates = list(map(str, candidate_ids))
    if len(set(continuation_ids)) != len(continuation_ids) or len(continuation_ids) < 2:
        raise ValueError("continuation sensitivity requires at least two unique policies")
    if len(set(candidates)) != len(candidates) or target_action not in candidates or baseline_action not in candidates:
        raise ValueError("candidate set does not contain unique target and baseline actions")

    totals: dict[tuple[str, str], list[float]] = {}
    for row in rows:
        continuation = str(row.get("continuation_policy_index"))
        action = str(row.get("action"))
        if continuation not in continuation_ids or action not in candidates:
            raise ValueError("row is outside the bound continuation/candidate set")
        weight = float(row.get("scenario_weight", 0.0))
        utility = float(row.get("terminal_utility"))
        if weight <= 0:
            raise ValueError("scenario weights must be positive")
        aggregate = totals.setdefault((continuation, action), [0.0, 0.0, 0.0])
        aggregate[0] += weight * utility
        aggregate[1] += weight
        aggregate[2] += 1

    results = []
    for continuation in continuation_ids:
        means = {}
        counts = {}
        weights = {}
        for action in candidates:
            weighted_sum, total_weight, row_count = totals.get((continuation, action), [0.0, 0.0, 0.0])
            if total_weight <= 0:
                raise ValueError("continuation/action cell has no rows")
            means[action] = weighted_sum / total_weight
            weights[action] = total_weight
            counts[action] = int(row_count)
        target_mean = means[target_action]
        baseline_mean = means[baseline_action]
        results.append({
            "continuation_policy_id": continuation,
            "target_win_probability": (target_mean + 1.0) / 2.0,
            "baseline_win_probability": (baseline_mean + 1.0) / 2.0,
            "advantage_win_probability": (target_mean - baseline_mean) / 2.0,
            "target_rank": 1 + sum(value > target_mean for value in means.values()),
            "target_rows": counts[target_action],
            "baseline_rows": counts[baseline_action],
            "target_weight": weights[target_action],
            "baseline_weight": weights[baseline_action],
        })
    return results


def _build_value(receipt_path: Path, selection_path: Path, workspace: Path) -> dict[str, Any]:
    receipt_verified = verify_kaggle_rollout_source_receipt(receipt_path, workspace_root=workspace)
    selection_verified = verify_refinement_selection(selection_path, workspace)
    selection = _read_object(selection_path)
    selected = _selected_states(selection)
    run = Path(str(receipt_verified["run_output"])).resolve()
    source_workspace = run.parents[2]
    verified = verify_oracle_output(run, source_workspace)
    if not verified.get("complete"):
        raise ValueError("continuation sensitivity source run is incomplete")
    manifest = _read_object(run / "run_manifest.json")
    report = _read_object(run / "report.json")

    continuation_ids = [str(item.get("policy_id")) for item in manifest.get("continuation_policies", [])]
    if len(set(continuation_ids)) < 2:
        raise ValueError("source run has fewer than two continuation policies")
    batch_ids = list(map(int, manifest.get("batch_ids", [])))
    selected_ids = [str(item["state_id"]) for item in selected]
    if not set(selected_ids) <= set(map(str, manifest.get("state_ids", []))):
        raise ValueError("selected state is absent from the source run")
    if any(list(map(int, item.get("batch_ids", []))) != batch_ids for item in selected):
        raise ValueError("selection and source batch IDs differ")

    states = []
    total_rows = 0
    for item in selected:
        state_id = str(item["state_id"])
        target = str(item["best_nonbaseline"]["action"])
        baseline = str(item["baseline_action"])
        batches = []
        for batch_id in batch_ids:
            shard = _read_object(run / "shards" / state_id / ("batch_%03d.json" % batch_id))
            if str(shard.get("state_id")) != state_id or int(shard.get("batch_id", -1)) != batch_id:
                raise ValueError("shard state or batch binding mismatch")
            candidate_ids = list(map(str, shard.get("candidate_ids", [])))
            summaries = summarize_shard_rows(
                shard.get("rows", []),
                continuation_policy_ids=continuation_ids,
                candidate_ids=candidate_ids,
                target_action=target,
                baseline_action=baseline,
            )
            total_rows += len(shard.get("rows", []))
            batches.append({"batch_id": batch_id, "continuations": summaries})
        continuations = []
        for continuation_id in continuation_ids:
            cells = [
                next(cell for cell in batch["continuations"] if cell["continuation_policy_id"] == continuation_id)
                for batch in batches
            ]
            advantages = [float(cell["advantage_win_probability"]) for cell in cells]
            continuations.append({
                "continuation_policy_id": continuation_id,
                "mean_advantage_win_probability": sum(advantages) / len(advantages),
                "minimum_batch_advantage_win_probability": min(advantages),
                "positive_batches": sum(value > 0.0 for value in advantages),
                "target_top1_batches": sum(int(cell["target_rank"]) == 1 for cell in cells),
            })
        states.append({
            "state_id": state_id,
            "episode_id": str(item["episode_id"]),
            "target_action": target,
            "baseline_action": baseline,
            "continuations": continuations,
            "batches": batches,
            "all_continuation_batches_positive": all(
                int(value["positive_batches"]) == len(batch_ids) for value in continuations
            ),
        })

    if total_rows != int(verified["rows"]):
        raise ValueError("audited shard rows do not match the verified run")
    passed = all(item["all_continuation_batches_positive"] for item in states)
    value = {
        "schema_version": SCHEMA_VERSION,
        "audit_implementation_sha256": _file_sha256(Path(__file__)),
        "criteria": {
            "minimum_continuation_policies": 2,
            "minimum_batch_advantage_win_probability_exclusive": 0.0,
            "require_selected_target_action": True,
            "require_every_batch_and_continuation": True,
        },
        "source_receipt": {
            "path": _relative_inside(receipt_path, workspace, "source receipt"),
            "file_sha256": _file_sha256(receipt_path),
            "manifest_sha256": receipt_verified["manifest_sha256"],
        },
        "selection": {
            "path": _relative_inside(selection_path, workspace, "selection manifest"),
            "file_sha256": _file_sha256(selection_path),
            "manifest_sha256": selection_verified["manifest_sha256"],
        },
        "run": {
            "workspace_path": _relative_inside(source_workspace, workspace, "source workspace"),
            "run_path": _relative_inside(run, source_workspace, "source run"),
            "run_manifest_file_sha256": _file_sha256(run / "run_manifest.json"),
            "run_manifest_sha256": manifest["manifest_sha256"],
            "report_file_sha256": _file_sha256(run / "report.json"),
            "report_manifest_sha256": report["manifest_sha256"],
            "particles_per_scenario": int(manifest["config"]["particles_per_scenario"]),
            "rows": int(verified["rows"]),
            "shards": int(verified["shards"]),
            "batch_ids": batch_ids,
            "continuation_policy_ids": continuation_ids,
        },
        "states": states,
        "all_states_pass": passed,
        "no_continuation_sign_reversal": passed,
    }
    value["manifest_sha256"] = _self_hash(value)
    return value


def write_continuation_sensitivity(
    source_receipt: str | Path,
    selection_manifest: str | Path,
    output_path: str | Path,
    workspace_root: str | Path,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    receipt = Path(source_receipt).resolve()
    selection = Path(selection_manifest).resolve()
    output = Path(output_path).resolve()
    _relative_inside(output, workspace, "audit output")
    value = _build_value(receipt, selection, workspace)
    write_once(output, value)
    return value


def verify_continuation_sensitivity(
    output_path: str | Path, workspace_root: str | Path,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    output = Path(output_path).resolve()
    value = _read_object(output)
    if (
        value.get("schema_version") != SCHEMA_VERSION
        or value.get("manifest_sha256") != _self_hash(value)
        or value.get("audit_implementation_sha256") != _file_sha256(Path(__file__))
    ):
        raise ValueError("continuation sensitivity self-hash mismatch")
    expected = _build_value(
        workspace / str(value["source_receipt"]["path"]),
        workspace / str(value["selection"]["path"]),
        workspace,
    )
    if value != expected:
        raise ValueError("continuation sensitivity audit does not reproduce")
    return {
        "verified": True,
        "manifest_sha256": value["manifest_sha256"],
        "states": len(value["states"]),
        "continuations": len(value["run"]["continuation_policy_ids"]),
        "all_states_pass": value["all_states_pass"],
        "output_path": str(output),
    }
