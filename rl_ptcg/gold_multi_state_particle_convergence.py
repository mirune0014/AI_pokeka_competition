"""Audit nested particle reuse for multiple selected Gold teacher states."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .gold_oracle_runner import verify_oracle_output
from .gold_oracle_states import canonical_sha256, write_once
from .gold_particle_convergence import compare_row_reuse
from .gold_teacher_refinement_selection import verify_refinement_selection


SCHEMA_VERSION = "gold_multi_state_particle_convergence.v1"


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
    if not selected:
        raise ValueError("multi-state convergence requires selected states")
    if int(selection.get("selected_count", -1)) != len(selected):
        raise ValueError("refinement selected_count does not match states")
    state_ids = [str(item.get("state_id")) for item in selected]
    if len(set(state_ids)) != len(state_ids) or any(not value for value in state_ids):
        raise ValueError("selected state IDs are not unique")
    next_run = selection.get("next_run")
    if not isinstance(next_run, Mapping) or sorted(map(str, next_run.get("state_ids", []))) != sorted(state_ids):
        raise ValueError("refinement next_run does not bind selected states")
    for item in selected:
        best = item.get("best_nonbaseline")
        if not isinstance(best, Mapping) or not isinstance(best.get("action"), str):
            raise ValueError("selected state has no target action")
    return selected


def _implementation_hashes(manifest: Mapping[str, Any]) -> dict[str, str]:
    implementation = manifest.get("implementation")
    if not isinstance(implementation, Mapping):
        raise ValueError("run manifest has no implementation binding")
    result = {}
    for name, item in implementation.items():
        if not isinstance(item, Mapping) or not isinstance(item.get("source_sha256"), str):
            raise ValueError("run manifest has invalid implementation binding")
        result[str(name)] = str(item["source_sha256"])
    return result


def _semantic_config(manifest: Mapping[str, Any], ignored_implementation: set[str]) -> dict[str, Any]:
    config = dict(manifest.get("config", {}))
    config.pop("particles_per_scenario", None)
    implementation = _implementation_hashes(manifest)
    return {
        "config_without_particles": config,
        "batch_ids": [int(item) for item in manifest.get("batch_ids", [])],
        "baseline_policy_id": str(manifest.get("baseline", {}).get("policy_id")),
        "continuation_policy_ids": [
            str(item.get("policy_id")) for item in manifest.get("continuation_policies", [])
        ],
        "opponent_policy_ids": {
            str(archetype): [str(item.get("policy_id")) for item in policies]
            for archetype, policies in sorted(manifest.get("opponent_policies", {}).items())
        },
        "corpus_manifest_sha256": str(manifest.get("corpus", {}).get("manifest_sha256")),
        "engine_binary_sha256": str(manifest.get("engine", {}).get("binary_sha256")),
        "implementation_source_sha256": {
            name: value for name, value in sorted(implementation.items())
            if name not in ignored_implementation
        },
    }


def _report_units(report: Mapping[str, Any]) -> dict[tuple[str, int], Mapping[str, Any]]:
    units = report.get("posterior_weighted_teacher_statistics", {}).get("per_state_batch")
    if not isinstance(units, list):
        raise ValueError("oracle report has no per-state batch statistics")
    result = {}
    for unit in units:
        if not isinstance(unit, Mapping):
            raise ValueError("oracle report has invalid per-state batch unit")
        key = (str(unit.get("state_id")), int(unit.get("batch_id")))
        if key in result:
            raise ValueError("oracle report repeats a per-state batch unit")
        result[key] = unit
    return result


def _target_level(
    label: str,
    manifest: Mapping[str, Any],
    report: Mapping[str, Any],
    state_id: str,
    action: str,
) -> dict[str, Any]:
    units_by_key = _report_units(report)
    units = [units_by_key[(state_id, int(batch))] for batch in manifest["batch_ids"]]
    values = []
    for unit in units:
        actions = unit.get("actions")
        if not isinstance(actions, Mapping) or action not in actions:
            raise ValueError("selected action is absent from a report batch")
        values.append(actions[action])
    return {
        "label": label,
        "particles_per_scenario": int(manifest["config"]["particles_per_scenario"]),
        "target_top_count": sum(str(unit.get("oracle_action")) == action for unit in units),
        "target_mean_advantage_win_probability": sum(
            float(value["advantage_win_probability"]) for value in values
        ) / len(values),
        "target_minimum_batch_advantage_win_probability": min(
            float(value["advantage_win_probability"]) for value in values
        ),
        "target_positive_lcb90_batches": sum(
            float(value["one_sided_lcb90_win_probability"]) > 0 for value in values
        ),
        "batches": [{
            "batch_id": int(unit["batch_id"]),
            "oracle_action": str(unit["oracle_action"]),
            "target_advantage_win_probability": float(value["advantage_win_probability"]),
            "target_lcb90_win_probability": float(value["one_sided_lcb90_win_probability"]),
        } for unit, value in zip(units, values)],
    }


def _build_value(
    levels: Sequence[tuple[str, Path, Path]],
    selection_manifest: Path,
    audit_workspace: Path,
    allowed_implementation_drift: Sequence[str],
) -> dict[str, Any]:
    selection_verified = verify_refinement_selection(selection_manifest, audit_workspace)
    selection = _read_object(selection_manifest)
    selected = _selected_states(selection)
    selected_ids = [str(item["state_id"]) for item in selected]
    allowed_drift = set(map(str, allowed_implementation_drift))

    loaded = []
    previous_particles = 0
    for label, run, workspace in levels:
        verified = verify_oracle_output(run, workspace)
        if not verified.get("complete"):
            raise ValueError("particle convergence source run is incomplete")
        manifest = _read_object(run / "run_manifest.json")
        report = _read_object(run / "report.json")
        particles = int(manifest["config"]["particles_per_scenario"])
        if particles <= previous_particles:
            raise ValueError("particle levels must be strictly increasing")
        previous_particles = particles
        if not set(selected_ids) <= set(map(str, manifest.get("state_ids", []))):
            raise ValueError("selected state is absent from a source run")
        loaded.append((str(label), run, workspace, verified, manifest, report))
    if len(loaded) < 2:
        raise ValueError("at least two particle levels are required")

    implementation_by_level = {
        label: _implementation_hashes(manifest)
        for label, _run, _workspace, _verified, manifest, _report in loaded
    }
    implementation_names = set().union(*(set(value) for value in implementation_by_level.values()))
    actual_drift = {
        name for name in implementation_names
        if len({value.get(name) for value in implementation_by_level.values()}) != 1
    }
    if actual_drift != allowed_drift:
        raise ValueError("implementation drift does not match the explicit allowlist")

    shared_config = _semantic_config(loaded[0][4], allowed_drift)
    for _label, _run, _workspace, _verified, manifest, _report in loaded[1:]:
        if _semantic_config(manifest, allowed_drift) != shared_config:
            raise ValueError("particle source runs do not share semantic configuration")
    selection_batches = {
        tuple(map(int, item.get("batch_ids", []))) for item in selected
    }
    if selection_batches != {tuple(shared_config["batch_ids"])}:
        raise ValueError("selection and source batch IDs differ")

    run_bindings = []
    for label, run, workspace, verified, manifest, _report in loaded:
        run_bindings.append({
            "label": label,
            "workspace_path": _relative_inside(workspace, audit_workspace, "source workspace"),
            "run_path": _relative_inside(run, workspace, "source run"),
            "run_manifest_file_sha256": _file_sha256(run / "run_manifest.json"),
            "run_manifest_sha256": manifest["manifest_sha256"],
            "report_file_sha256": _file_sha256(run / "report.json"),
            "report_manifest_sha256": _report["manifest_sha256"],
            "particles_per_scenario": int(manifest["config"]["particles_per_scenario"]),
            "rows": int(verified["rows"]),
            "shards": int(verified["shards"]),
        })

    targets = []
    for item in selected:
        state_id = str(item["state_id"])
        action = str(item["best_nonbaseline"]["action"])
        targets.append({
            "state_id": state_id,
            "episode_id": str(item["episode_id"]),
            "action": action,
            "levels": [
                _target_level(label, manifest, report, state_id, action)
                for label, _run, _workspace, _verified, manifest, report in loaded
            ],
        })

    reuse = []
    for lower, higher in zip(loaded, loaded[1:]):
        states = []
        for state_id in selected_ids:
            batches = []
            for batch_id in shared_config["batch_ids"]:
                lower_shard = _read_object(
                    lower[1] / "shards" / state_id / ("batch_%03d.json" % batch_id)
                )
                higher_shard = _read_object(
                    higher[1] / "shards" / state_id / ("batch_%03d.json" % batch_id)
                )
                if lower_shard.get("candidate_ids") != higher_shard.get("candidate_ids"):
                    raise ValueError("candidate set changed between particle levels")
                comparison = compare_row_reuse(lower_shard["rows"], higher_shard["rows"])
                comparison["batch_id"] = int(batch_id)
                batches.append(comparison)
            states.append({
                "state_id": state_id,
                "lower_is_subset_all_batches": all(item["lower_is_subset"] for item in batches),
                "shared_rows": sum(item["shared_rows"] for item in batches),
                "shared_utility_mismatches": sum(item["shared_utility_mismatches"] for item in batches),
                "batches": batches,
            })
        reuse.append({
            "lower_label": lower[0],
            "higher_label": higher[0],
            "lower_is_subset_all_states": all(item["lower_is_subset_all_batches"] for item in states),
            "shared_rows": sum(item["shared_rows"] for item in states),
            "shared_utility_mismatches": sum(item["shared_utility_mismatches"] for item in states),
            "states": states,
        })

    value = {
        "schema_version": SCHEMA_VERSION,
        "audit_implementation_sha256": _file_sha256(Path(__file__)),
        "selection": {
            "path": _relative_inside(selection_manifest, audit_workspace, "selection manifest"),
            "file_sha256": _file_sha256(selection_manifest),
            "manifest_sha256": selection_verified["manifest_sha256"],
        },
        "selected_state_count": len(selected),
        "shared_config": shared_config,
        "allowed_implementation_drift": {
            name: {
                label: implementation_by_level[label].get(name)
                for label, _run, _workspace, _verified, _manifest, _report in loaded
            }
            for name in sorted(actual_drift)
        },
        "runs": run_bindings,
        "targets": targets,
        "adjacent_row_reuse": reuse,
        "all_lower_rows_reused_exactly": all(
            item["lower_is_subset_all_states"] and item["shared_utility_mismatches"] == 0
            for item in reuse
        ),
    }
    value["manifest_sha256"] = _self_hash(value)
    return value


def write_multi_state_particle_convergence(
    levels: Sequence[tuple[str, str | Path, str | Path]],
    selection_manifest: str | Path,
    output_path: str | Path,
    workspace_root: str | Path,
    *,
    allowed_implementation_drift: Sequence[str] = (),
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    resolved_levels = [
        (str(label), Path(run).resolve(), Path(source_workspace).resolve())
        for label, run, source_workspace in levels
    ]
    output = Path(output_path).resolve()
    _relative_inside(output, workspace, "convergence output")
    value = _build_value(
        resolved_levels, Path(selection_manifest).resolve(), workspace,
        allowed_implementation_drift,
    )
    write_once(output, value)
    return value


def verify_multi_state_particle_convergence(
    output_path: str | Path, workspace_root: str | Path,
) -> dict[str, Any]:
    output = Path(output_path).resolve()
    workspace = Path(workspace_root).resolve()
    value = _read_object(output)
    if (
        value.get("schema_version") != SCHEMA_VERSION
        or value.get("manifest_sha256") != _self_hash(value)
        or value.get("audit_implementation_sha256") != _file_sha256(Path(__file__))
    ):
        raise ValueError("multi-state particle convergence self-hash mismatch")
    levels = [(
        str(item["label"]),
        workspace / str(item["workspace_path"]) / str(item["run_path"]),
        workspace / str(item["workspace_path"]),
    ) for item in value["runs"]]
    expected = _build_value(
        levels,
        workspace / str(value["selection"]["path"]),
        workspace,
        list(value.get("allowed_implementation_drift", {})),
    )
    if value != expected:
        raise ValueError("multi-state particle convergence audit does not reproduce")
    return {
        "verified": True,
        "manifest_sha256": value["manifest_sha256"],
        "levels": len(value["runs"]),
        "states": value["selected_state_count"],
        "all_lower_rows_reused_exactly": value["all_lower_rows_reused_exactly"],
        "output_path": str(output),
    }
