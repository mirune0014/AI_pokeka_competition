"""Select higher-particle teacher refinements from a verified pilot run."""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .gold_oracle_runner import verify_oracle_output
from .gold_oracle_states import canonical_sha256, write_once


SCHEMA_VERSION = "gold_teacher_refinement_selection.v1"


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _self_hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="ascii"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object: %s" % path)
    return value


def _relative_inside(path: Path, root: Path, label: str) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("%s escapes workspace" % label) from error
    value = str(relative).replace("\\", "/")
    return value or "."


def select_refinement_states(
    units: Sequence[Mapping[str, Any]],
    *,
    minimum_top_count: int,
    minimum_mean_advantage_win_probability: float,
    minimum_batch_advantage_win_probability_exclusive: float | None = None,
) -> list[dict[str, Any]]:
    if minimum_top_count <= 0:
        raise ValueError("minimum_top_count must be positive")
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for unit in units:
        grouped[str(unit["state_id"])].append(unit)
    result = []
    for state_id, state_units in sorted(grouped.items()):
        ordered = sorted(state_units, key=lambda item: int(item["batch_id"]))
        baseline = str(ordered[0]["baseline_action"])
        if any(str(unit["baseline_action"]) != baseline for unit in ordered):
            raise ValueError("baseline action changed across batches")
        action_ids = set(ordered[0]["actions"])
        if any(set(unit["actions"]) != action_ids for unit in ordered):
            raise ValueError("candidate action set changed across batches")
        candidates = []
        for action in sorted(action_ids - {baseline}):
            values = [unit["actions"][action] for unit in ordered]
            head_advantages = [
                float(advantage) / 2.0
                for value in values
                for advantage in value["opponent_group_advantages_utility"].values()
            ]
            candidates.append({
                "action": action,
                "top_count": sum(str(unit["oracle_action"]) == action for unit in ordered),
                "mean_advantage_win_probability": sum(
                    float(value["advantage_win_probability"]) for value in values
                ) / len(values),
                "minimum_batch_advantage_win_probability": min(
                    float(value["advantage_win_probability"]) for value in values
                ),
                "positive_lcb90_batches": sum(
                    float(value["one_sided_lcb90_win_probability"]) > 0 for value in values
                ),
                "minimum_opponent_head_advantage_win_probability": min(head_advantages),
            })
        candidates.sort(key=lambda item: (-item["mean_advantage_win_probability"], item["action"]))
        best = candidates[0] if candidates else None
        selected = bool(
            best
            and int(best["top_count"]) >= minimum_top_count
            and float(best["mean_advantage_win_probability"])
            >= minimum_mean_advantage_win_probability
            and (
                minimum_batch_advantage_win_probability_exclusive is None
                or float(best["minimum_batch_advantage_win_probability"])
                > minimum_batch_advantage_win_probability_exclusive
            )
        )
        result.append({
            "state_id": state_id,
            "episode_id": str(ordered[0]["episode_id"]),
            "baseline_action": baseline,
            "batch_ids": [int(unit["batch_id"]) for unit in ordered],
            "best_nonbaseline": best,
            "selected": selected,
        })
    return result


def _build_value(
    run_dir: Path,
    source_workspace: Path,
    audit_workspace: Path,
    *,
    minimum_top_count: int,
    minimum_mean_advantage_win_probability: float,
    minimum_batch_advantage_win_probability_exclusive: float | None,
    next_particles_per_scenario: int,
) -> dict[str, Any]:
    verified = verify_oracle_output(run_dir, source_workspace)
    if not verified.get("complete"):
        raise ValueError("source rollout run is incomplete")
    report = _read_object(run_dir / "report.json")
    run_manifest = _read_object(run_dir / "run_manifest.json")
    states = select_refinement_states(
        report["posterior_weighted_teacher_statistics"]["per_state_batch"],
        minimum_top_count=minimum_top_count,
        minimum_mean_advantage_win_probability=minimum_mean_advantage_win_probability,
        minimum_batch_advantage_win_probability_exclusive=(
            minimum_batch_advantage_win_probability_exclusive
        ),
    )
    selected = [item for item in states if item["selected"]]
    value = {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "workspace_path": _relative_inside(
                source_workspace, audit_workspace, "source workspace",
            ),
            "run_path": _relative_inside(run_dir, source_workspace, "source run"),
            "run_manifest_file_sha256": file_sha256(run_dir / "run_manifest.json"),
            "run_manifest_sha256": run_manifest["manifest_sha256"],
            "report_file_sha256": file_sha256(run_dir / "report.json"),
            "report_manifest_sha256": report["manifest_sha256"],
            "rows": verified["rows"],
            "shards": verified["shards"],
        },
        "selection_config": {
            "minimum_top_count": int(minimum_top_count),
            "minimum_mean_advantage_win_probability": float(
                minimum_mean_advantage_win_probability
            ),
            "require_nonbaseline": True,
        },
        "next_run": {
            "state_ids": [item["state_id"] for item in selected],
            "particles_per_scenario": int(next_particles_per_scenario),
            "batches": len(run_manifest["batch_ids"]),
            "seed": str(run_manifest["config"]["seed"]),
            "candidate_set": str(run_manifest["config"]["candidate_set"]),
        },
        "states": states,
        "selected_count": len(selected),
    }
    if minimum_batch_advantage_win_probability_exclusive is not None:
        value["selection_config"][
            "minimum_batch_advantage_win_probability_exclusive"
        ] = float(minimum_batch_advantage_win_probability_exclusive)
    value["manifest_sha256"] = _self_hash(value)
    return value


def write_refinement_selection(
    run_dir: str | Path,
    source_workspace_root: str | Path,
    output_path: str | Path,
    workspace_root: str | Path,
    *,
    minimum_top_count: int = 2,
    minimum_mean_advantage_win_probability: float = 0.05,
    minimum_batch_advantage_win_probability_exclusive: float | None = None,
    next_particles_per_scenario: int = 4,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    source_workspace = Path(source_workspace_root).resolve()
    run = Path(run_dir).resolve()
    output = Path(output_path).resolve()
    _relative_inside(output, workspace, "selection output")
    value = _build_value(
        run,
        source_workspace,
        workspace,
        minimum_top_count=minimum_top_count,
        minimum_mean_advantage_win_probability=minimum_mean_advantage_win_probability,
        minimum_batch_advantage_win_probability_exclusive=(
            minimum_batch_advantage_win_probability_exclusive
        ),
        next_particles_per_scenario=next_particles_per_scenario,
    )
    write_once(output, value)
    return value


def verify_refinement_selection(
    output_path: str | Path, workspace_root: str | Path,
) -> dict[str, Any]:
    output = Path(output_path).resolve()
    workspace = Path(workspace_root).resolve()
    value = _read_object(output)
    if (
        value.get("schema_version") != SCHEMA_VERSION
        or value.get("manifest_sha256") != _self_hash(value)
    ):
        raise ValueError("refinement selection self-hash mismatch")
    source_workspace = workspace / value["source"]["workspace_path"]
    run = source_workspace / value["source"]["run_path"]
    config = value["selection_config"]
    expected = _build_value(
        run,
        source_workspace,
        workspace,
        minimum_top_count=int(config["minimum_top_count"]),
        minimum_mean_advantage_win_probability=float(
            config["minimum_mean_advantage_win_probability"]
        ),
        minimum_batch_advantage_win_probability_exclusive=(
            None
            if "minimum_batch_advantage_win_probability_exclusive" not in config
            else float(config["minimum_batch_advantage_win_probability_exclusive"])
        ),
        next_particles_per_scenario=int(value["next_run"]["particles_per_scenario"]),
    )
    if value != expected:
        raise ValueError("refinement selection does not reproduce")
    return {
        "verified": True,
        "selected_count": value["selected_count"],
        "state_ids": value["next_run"]["state_ids"],
        "manifest_sha256": value["manifest_sha256"],
        "output_path": str(output),
    }
