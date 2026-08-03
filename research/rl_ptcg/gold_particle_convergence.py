"""Audit particle-count convergence across verified Gold teacher runs."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .gold_oracle_runner import stable_seed, verify_oracle_output
from .gold_oracle_statistics import summarize_gold_oracle
from .gold_oracle_states import canonical_sha256, write_once
from .gold_teacher_refinement_selection import verify_refinement_selection


SCHEMA_VERSION = "gold_particle_convergence.v1"
PROJECTED_SCHEMA_VERSION = "gold_particle_convergence.v2"


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
        raise ValueError("%s escapes audit workspace" % label) from error
    value = str(relative).replace("\\", "/")
    return value or "."


def _row_key(row: Mapping[str, Any]) -> str:
    return canonical_sha256({key: value for key, value in row.items() if key != "terminal_utility"})


def compare_row_reuse(
    lower_rows: Sequence[Mapping[str, Any]], higher_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    lower = {_row_key(row): float(row["terminal_utility"]) for row in lower_rows}
    higher = {_row_key(row): float(row["terminal_utility"]) for row in higher_rows}
    if len(lower) != len(lower_rows) or len(higher) != len(higher_rows):
        raise ValueError("rollout row identity is not unique")
    shared = set(lower) & set(higher)
    return {
        "lower_rows": len(lower),
        "higher_rows": len(higher),
        "lower_is_subset": set(lower) <= set(higher),
        "shared_rows": len(shared),
        "shared_utility_mismatches": sum(lower[key] != higher[key] for key in shared),
    }


def _load_states(workspace: Path, manifest: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    corpus = workspace / str(manifest["corpus"]["path"])
    result = {}
    for line in (corpus / "states.jsonl").read_text(encoding="ascii").splitlines():
        if line.strip():
            state = json.loads(line)
            result[str(state["state_id"])] = state
    return result


def _report_units(report: Mapping[str, Any]) -> dict[tuple[str, int], Mapping[str, Any]]:
    return {
        (str(unit["state_id"]), int(unit["batch_id"])): unit
        for unit in report["posterior_weighted_teacher_statistics"]["per_state_batch"]
    }


def _target_level(
    label: str,
    manifest: Mapping[str, Any],
    report: Mapping[str, Any],
    state_id: str,
    action: str,
) -> dict[str, Any]:
    units_by_key = _report_units(report)
    units = [units_by_key[(state_id, int(batch))] for batch in manifest["batch_ids"]]
    values = [unit["actions"][action] for unit in units]
    head_values = [
        float(advantage) / 2.0
        for value in values
        for advantage in value["opponent_group_advantages_utility"].values()
    ]
    stable = any(
        str(item["state_id"]) == state_id and str(item["action"]) == action
        for item in report["posterior_weighted_teacher_statistics"]["stable_labels"]
    )
    return {
        "label": label,
        "particles_per_scenario": int(manifest["config"]["particles_per_scenario"]),
        "target_top_count": sum(str(unit["oracle_action"]) == action for unit in units),
        "target_mean_advantage_win_probability": sum(
            float(value["advantage_win_probability"]) for value in values
        ) / len(values),
        "target_minimum_batch_advantage_win_probability": min(
            float(value["advantage_win_probability"]) for value in values
        ),
        "target_positive_lcb90_batches": sum(
            float(value["one_sided_lcb90_win_probability"]) > 0 for value in values
        ),
        "target_minimum_opponent_head_advantage_win_probability": min(head_values),
        "target_is_stable_label": stable,
        "batches": [{
            "batch_id": int(unit["batch_id"]),
            "oracle_action": str(unit["oracle_action"]),
            "target_advantage_win_probability": float(value["advantage_win_probability"]),
            "target_lcb90_win_probability": float(value["one_sided_lcb90_win_probability"]),
        } for unit, value in zip(units, values)],
    }


def _build_value_v1(
    levels: Sequence[tuple[str, Path, Path]],
    selection_manifest: Path,
    audit_workspace: Path,
) -> dict[str, Any]:
    selection_verified = verify_refinement_selection(selection_manifest, audit_workspace)
    selection = _read_object(selection_manifest)
    selected = [item for item in selection["states"] if item["selected"]]
    if len(selected) != 1:
        raise ValueError("particle convergence requires exactly one selected state")
    state_id = str(selected[0]["state_id"])
    action = str(selected[0]["best_nonbaseline"]["action"])

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
        if state_id not in manifest["state_ids"]:
            raise ValueError("selected state is absent from a source run")
        loaded.append((label, run, workspace, verified, manifest, report))
    if len(loaded) < 2:
        raise ValueError("at least two particle levels are required")

    first_manifest = loaded[0][4]
    states = _load_states(loaded[0][2], first_manifest)
    archetype = str(states[state_id]["belief"]["archetype"])
    shared_config = {
        "seed": first_manifest["config"]["seed"],
        "candidate_set": first_manifest["config"]["candidate_set"],
        "max_rollout_steps": first_manifest["config"]["max_rollout_steps"],
        "batch_ids": first_manifest["batch_ids"],
        "baseline_policy_id": first_manifest["baseline"]["policy_id"],
        "continuation_policy_ids": [
            item["policy_id"] for item in first_manifest["continuation_policies"]
        ],
        "opponent_policy_ids": [
            item["policy_id"] for item in first_manifest["opponent_policies"][archetype]
        ],
        "corpus_manifest_sha256": first_manifest["corpus"]["manifest_sha256"],
        "engine_binary_sha256": first_manifest["engine"]["binary_sha256"],
        "implementation_source_sha256": {
            name: item["source_sha256"]
            for name, item in sorted(first_manifest["implementation"].items())
        },
    }
    for _label, _run, _workspace, _verified, manifest, _report in loaded[1:]:
        comparable = {
            "seed": manifest["config"]["seed"],
            "candidate_set": manifest["config"]["candidate_set"],
            "max_rollout_steps": manifest["config"]["max_rollout_steps"],
            "batch_ids": manifest["batch_ids"],
            "baseline_policy_id": manifest["baseline"]["policy_id"],
            "continuation_policy_ids": [
                item["policy_id"] for item in manifest["continuation_policies"]
            ],
            "opponent_policy_ids": [
                item["policy_id"] for item in manifest["opponent_policies"][archetype]
            ],
            "corpus_manifest_sha256": manifest["corpus"]["manifest_sha256"],
            "engine_binary_sha256": manifest["engine"]["binary_sha256"],
            "implementation_source_sha256": {
                name: item["source_sha256"]
                for name, item in sorted(manifest["implementation"].items())
            },
        }
        if comparable != shared_config:
            raise ValueError("particle source runs do not share semantic configuration")

    run_bindings = []
    target_levels = []
    for label, run, workspace, verified, manifest, report in loaded:
        run_bindings.append({
            "label": label,
            "workspace_path": _relative_inside(workspace, audit_workspace, "source workspace"),
            "run_path": _relative_inside(run, workspace, "source run"),
            "run_manifest_file_sha256": file_sha256(run / "run_manifest.json"),
            "run_manifest_sha256": manifest["manifest_sha256"],
            "report_file_sha256": file_sha256(run / "report.json"),
            "report_manifest_sha256": report["manifest_sha256"],
            "rows": verified["rows"],
            "shards": verified["shards"],
        })
        target_levels.append(_target_level(label, manifest, report, state_id, action))

    reuse = []
    for lower, higher in zip(loaded, loaded[1:]):
        units = []
        for batch_id in first_manifest["batch_ids"]:
            lower_shard = _read_object(
                lower[1] / "shards" / state_id / ("batch_%03d.json" % batch_id)
            )
            higher_shard = _read_object(
                higher[1] / "shards" / state_id / ("batch_%03d.json" % batch_id)
            )
            if lower_shard["candidate_ids"] != higher_shard["candidate_ids"]:
                raise ValueError("candidate set changed between particle levels")
            comparison = compare_row_reuse(lower_shard["rows"], higher_shard["rows"])
            comparison["batch_id"] = int(batch_id)
            units.append(comparison)
        reuse.append({
            "lower_label": lower[0],
            "higher_label": higher[0],
            "lower_is_subset_all_batches": all(item["lower_is_subset"] for item in units),
            "shared_rows": sum(item["shared_rows"] for item in units),
            "shared_utility_mismatches": sum(
                item["shared_utility_mismatches"] for item in units
            ),
            "batches": units,
        })

    highest = target_levels[-1]
    value = {
        "schema_version": SCHEMA_VERSION,
        "selection": {
            "path": _relative_inside(selection_manifest, audit_workspace, "selection manifest"),
            "file_sha256": file_sha256(selection_manifest),
            "manifest_sha256": selection_verified["manifest_sha256"],
        },
        "target": {
            "state_id": state_id,
            "episode_id": str(selected[0]["episode_id"]),
            "archetype": archetype,
            "action": action,
        },
        "shared_config": shared_config,
        "runs": run_bindings,
        "target_levels": target_levels,
        "adjacent_row_reuse": reuse,
        "all_lower_rows_reused_exactly": all(
            item["lower_is_subset_all_batches"]
            and item["shared_utility_mismatches"] == 0
            for item in reuse
        ),
        "highest_level_stable_label": highest["target_is_stable_label"],
    }
    value["manifest_sha256"] = _self_hash(value)
    return value


def _projected_rows_and_audit(
    run: Path,
    manifest: Mapping[str, Any],
    state_id: str,
    archetype: str,
    opponent_policy_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    policies = manifest["opponent_policies"].get(archetype)
    if not isinstance(policies, list):
        raise ValueError("source run has no effective opponent population for target archetype")
    policy_ids = [str(item.get("policy_id")) for item in policies if isinstance(item, Mapping)]
    if len(policy_ids) != len(policies) or policy_ids.count(opponent_policy_id) != 1:
        raise ValueError("projected opponent policy must occur exactly once in each effective population")
    continuations = manifest.get("continuation_policies")
    if not isinstance(continuations, list) or not continuations:
        raise ValueError("source run has no continuation policies")
    effective_policy_count = len(policy_ids)
    continuation_count = len(continuations)
    expected_denominator = effective_policy_count * continuation_count
    projected = []
    source_rows = 0
    for batch_id in manifest["batch_ids"]:
        shard = _read_object(run / "shards" / state_id / ("batch_%03d.json" % batch_id))
        for row in shard.get("rows", []):
            source_rows += 1
            try:
                expected_weight = float(row["posterior_mass"]) / expected_denominator
                actual_weight = float(row["scenario_weight"])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError("source rollout row has invalid projection weight fields") from error
            if abs(actual_weight - expected_weight) > 1e-12:
                raise ValueError("source scenario weights do not match effective opponent population")
            if str(row.get("opponent_policy_index")) == opponent_policy_id:
                normalized = dict(row)
                normalized["scenario_weight"] = float(row["posterior_mass"]) / continuation_count
                projected.append(normalized)
    if not projected:
        raise ValueError("projected opponent policy has no rollout rows")
    return projected, {
        "archetype": archetype,
        "selected_opponent_policy_id": opponent_policy_id,
        "effective_policy_ids": policy_ids,
        "effective_policy_count": effective_policy_count,
        "continuation_count": continuation_count,
        "selected_policy_count": policy_ids.count(opponent_policy_id),
        "expected_original_scenario_weight_denominator": expected_denominator,
        "source_rows_checked": source_rows,
        "projected_rows": len(projected),
    }


def _projected_report(
    rows: Sequence[Mapping[str, Any]],
    states: Mapping[str, Mapping[str, Any]],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    return {"posterior_weighted_teacher_statistics": summarize_gold_oracle(
        rows,
        states,
        bootstrap_repetitions=int(manifest["config"]["bootstrap_repetitions"]),
        bootstrap_seed=stable_seed(manifest["config"]["seed"], "posterior-bootstrap"),
    )}


def _build_projected_value(
    levels: Sequence[tuple[str, Path, Path]],
    selection_manifest: Path,
    audit_workspace: Path,
    opponent_policy_id: str,
) -> dict[str, Any]:
    selection_verified = verify_refinement_selection(selection_manifest, audit_workspace)
    selection = _read_object(selection_manifest)
    selected = [item for item in selection["states"] if item["selected"]]
    if len(selected) != 1:
        raise ValueError("particle convergence requires exactly one selected state")
    state_id = str(selected[0]["state_id"])
    action = str(selected[0]["best_nonbaseline"]["action"])

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
        if state_id not in manifest["state_ids"]:
            raise ValueError("selected state is absent from a source run")
        loaded.append((label, run, workspace, verified, manifest, report))
    if len(loaded) < 2:
        raise ValueError("at least two particle levels are required")

    first_manifest = loaded[0][4]
    states = _load_states(loaded[0][2], first_manifest)
    archetype = str(states[state_id]["belief"]["archetype"])
    shared_config = {
        "seed": first_manifest["config"]["seed"],
        "candidate_set": first_manifest["config"]["candidate_set"],
        "max_rollout_steps": first_manifest["config"]["max_rollout_steps"],
        "batch_ids": first_manifest["batch_ids"],
        "baseline_policy_id": first_manifest["baseline"]["policy_id"],
        "continuation_policy_ids": [item["policy_id"] for item in first_manifest["continuation_policies"]],
        "projected_opponent_policy_id": opponent_policy_id,
        "opponent_population_mode": first_manifest["config"].get("opponent_population_mode", "path_distinct_v1"),
        "rollout_seed_mode": first_manifest["config"].get("rollout_seed_mode", "policy_id_v1"),
        "corpus_manifest_sha256": first_manifest["corpus"]["manifest_sha256"],
        "engine_binary_sha256": first_manifest["engine"]["binary_sha256"],
        "implementation_source_sha256": {name: item["source_sha256"] for name, item in sorted(first_manifest["implementation"].items())},
    }
    for _label, _run, _workspace, _verified, manifest, _report in loaded[1:]:
        comparable = dict(shared_config)
        comparable.update({
            "seed": manifest["config"]["seed"], "candidate_set": manifest["config"]["candidate_set"],
            "max_rollout_steps": manifest["config"]["max_rollout_steps"], "batch_ids": manifest["batch_ids"],
            "baseline_policy_id": manifest["baseline"]["policy_id"],
            "continuation_policy_ids": [item["policy_id"] for item in manifest["continuation_policies"]],
            "projected_opponent_policy_id": opponent_policy_id,
            "opponent_population_mode": manifest["config"].get("opponent_population_mode", "path_distinct_v1"),
            "rollout_seed_mode": manifest["config"].get("rollout_seed_mode", "policy_id_v1"),
            "corpus_manifest_sha256": manifest["corpus"]["manifest_sha256"], "engine_binary_sha256": manifest["engine"]["binary_sha256"],
            "implementation_source_sha256": {name: item["source_sha256"] for name, item in sorted(manifest["implementation"].items())},
        })
        if comparable != shared_config:
            raise ValueError("particle source runs do not share semantic configuration")

    run_bindings, target_levels, population_audit, projected_by_level = [], [], [], []
    for label, run, workspace, verified, manifest, report in loaded:
        projected_rows, audit = _projected_rows_and_audit(run, manifest, state_id, archetype, opponent_policy_id)
        projected_by_level.append(projected_rows)
        audit["label"] = label
        population_audit.append(audit)
        run_bindings.append({
            "label": label, "workspace_path": _relative_inside(workspace, audit_workspace, "source workspace"),
            "run_path": _relative_inside(run, workspace, "source run"),
            "run_manifest_file_sha256": file_sha256(run / "run_manifest.json"), "run_manifest_sha256": manifest["manifest_sha256"],
            "report_file_sha256": file_sha256(run / "report.json"), "report_manifest_sha256": report["manifest_sha256"],
            "rows": verified["rows"], "shards": verified["shards"],
        })
        target_levels.append(_target_level(label, manifest, _projected_report(projected_rows, states, manifest), state_id, action))

    reuse = []
    for lower, higher, lower_rows, higher_rows in zip(loaded, loaded[1:], projected_by_level, projected_by_level[1:]):
        units = []
        for batch_id in first_manifest["batch_ids"]:
            lower_batch = [row for row in lower_rows if int(row["batch_id"]) == int(batch_id)]
            higher_batch = [row for row in higher_rows if int(row["batch_id"]) == int(batch_id)]
            comparison = compare_row_reuse(lower_batch, higher_batch)
            comparison["batch_id"] = int(batch_id)
            units.append(comparison)
        reuse.append({"lower_label": lower[0], "higher_label": higher[0],
            "lower_is_subset_all_batches": all(item["lower_is_subset"] for item in units),
            "shared_rows": sum(item["shared_rows"] for item in units),
            "shared_utility_mismatches": sum(item["shared_utility_mismatches"] for item in units), "batches": units})

    highest = target_levels[-1]
    value = {
        "schema_version": PROJECTED_SCHEMA_VERSION,
        "selection": {"path": _relative_inside(selection_manifest, audit_workspace, "selection manifest"), "file_sha256": file_sha256(selection_manifest), "manifest_sha256": selection_verified["manifest_sha256"]},
        "target": {"state_id": state_id, "episode_id": str(selected[0]["episode_id"]), "archetype": archetype, "action": action},
        "projection": {"opponent_policy_id": opponent_policy_id},
        "source_population_audit": population_audit,
        "opponent_population_mode": shared_config["opponent_population_mode"],
        "rollout_seed_mode": shared_config["rollout_seed_mode"],
        "shared_config": shared_config, "runs": run_bindings, "target_levels": target_levels, "adjacent_row_reuse": reuse,
        "all_lower_rows_reused_exactly": all(item["lower_is_subset_all_batches"] and item["shared_utility_mismatches"] == 0 for item in reuse),
        "highest_level_stable_label": highest["target_is_stable_label"],
    }
    value["manifest_sha256"] = _self_hash(value)
    return value


def write_particle_convergence(
    levels: Sequence[tuple[str, str | Path, str | Path]],
    selection_manifest: str | Path,
    output_path: str | Path,
    workspace_root: str | Path,
    *,
    project_opponent_policy_id: str | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    resolved_levels = [
        (label, Path(run).resolve(), Path(source_workspace).resolve())
        for label, run, source_workspace in levels
    ]
    output = Path(output_path).resolve()
    _relative_inside(output, workspace, "convergence output")
    if project_opponent_policy_id is None:
        value = _build_value_v1(
            resolved_levels, Path(selection_manifest).resolve(), workspace,
        )
    else:
        if not project_opponent_policy_id:
            raise ValueError("projected opponent policy ID must be nonempty")
        value = _build_projected_value(
            resolved_levels, Path(selection_manifest).resolve(), workspace,
            str(project_opponent_policy_id),
        )
    write_once(output, value)
    return value


def verify_particle_convergence(
    output_path: str | Path, workspace_root: str | Path,
) -> dict[str, Any]:
    output = Path(output_path).resolve()
    workspace = Path(workspace_root).resolve()
    value = _read_object(output)
    schema = value.get("schema_version")
    if schema not in {SCHEMA_VERSION, PROJECTED_SCHEMA_VERSION} or value.get("manifest_sha256") != _self_hash(value):
        raise ValueError("particle convergence self-hash mismatch")
    levels = [(
        str(item["label"]),
        workspace / str(item["workspace_path"]) / str(item["run_path"]),
        workspace / str(item["workspace_path"]),
    ) for item in value["runs"]]
    if schema == SCHEMA_VERSION:
        expected = _build_value_v1(
            levels, workspace / value["selection"]["path"], workspace,
        )
    else:
        projection = value.get("projection")
        if not isinstance(projection, Mapping) or not isinstance(projection.get("opponent_policy_id"), str):
            raise ValueError("projected particle convergence artifact has no opponent policy binding")
        expected = _build_projected_value(
            levels, workspace / value["selection"]["path"], workspace,
            projection["opponent_policy_id"],
        )
    if value != expected:
        raise ValueError("particle convergence audit does not reproduce")
    return {
        "verified": True,
        "manifest_sha256": value["manifest_sha256"],
        "levels": len(value["target_levels"]),
        "all_lower_rows_reused_exactly": value["all_lower_rows_reused_exactly"],
        "highest_level_stable_label": value["highest_level_stable_label"],
        "output_path": str(output),
    }
