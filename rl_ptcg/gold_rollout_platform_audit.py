"""Audit paired-rollout structural and utility parity across platforms."""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .gold_oracle_runner import verify_oracle_output
from .gold_oracle_states import canonical_sha256, file_sha256, write_once


SCHEMA_VERSION = "gold_rollout_platform_audit.v2"
LEGACY_SCHEMA_VERSION = "gold_rollout_platform_audit.v1"


def _self_hash(value: Mapping[str, Any]) -> str:
    return canonical_sha256({key: item for key, item in value.items() if key != "manifest_sha256"})


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="ascii"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object: %s" % path)
    return value


def _row_key(row: Mapping[str, Any]) -> str:
    return canonical_sha256({key: value for key, value in row.items() if key != "terminal_utility"})


def compare_rows(
    left_rows: Sequence[Mapping[str, Any]], right_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    left = {_row_key(row): row for row in left_rows}
    right = {_row_key(row): row for row in right_rows}
    if len(left) != len(left_rows) or len(right) != len(right_rows):
        raise ValueError("platform audit row key is not unique")
    structural_equal = set(left) == set(right)
    common = sorted(set(left) & set(right))
    utility_equal = 0
    left_better = 0
    right_better = 0
    discordances = []
    weighted: dict[str, dict[str, list[float]]] = {
        "left": defaultdict(lambda: [0.0, 0.0]),
        "right": defaultdict(lambda: [0.0, 0.0]),
    }
    for key in common:
        left_row, right_row = left[key], right[key]
        left_utility = float(left_row["terminal_utility"])
        right_utility = float(right_row["terminal_utility"])
        if left_utility == right_utility:
            utility_equal += 1
        else:
            left_better += int(left_utility > right_utility)
            right_better += int(right_utility > left_utility)
            discordances.append({
                "row_key": key,
                "state_id": left_row["state_id"],
                "batch_id": left_row["batch_id"],
                "action": left_row["action"],
                "hypothesis_signature": left_row["hypothesis_signature"],
                "opponent_policy_id": left_row["opponent_policy_index"],
                "continuation_policy_id": left_row["continuation_policy_index"],
                "particle_index": left_row["particle_index"],
                "hidden_world_id": left_row["hidden_world_id"],
                "left_terminal_utility": left_utility,
                "right_terminal_utility": right_utility,
            })
        for side, row, utility in (
            ("left", left_row, left_utility),
            ("right", right_row, right_utility),
        ):
            action = str(row["action"])
            weight = float(row["scenario_weight"])
            weighted[side][action][0] += weight * utility
            weighted[side][action][1] += weight
    action_means = []
    for action in sorted(set(weighted["left"]) | set(weighted["right"])):
        left_sum, left_weight = weighted["left"][action]
        right_sum, right_weight = weighted["right"][action]
        if left_weight <= 0 or right_weight <= 0:
            raise ValueError("platform audit action has no positive weight")
        left_mean, right_mean = left_sum / left_weight, right_sum / right_weight
        action_means.append({
            "action": action,
            "left_mean_terminal_utility": left_mean,
            "right_mean_terminal_utility": right_mean,
            "absolute_delta": abs(left_mean - right_mean),
        })
    return {
        "left_rows": len(left_rows),
        "right_rows": len(right_rows),
        "common_rows": len(common),
        "structural_rows_equal": structural_equal,
        "utility_equal_rows": utility_equal,
        "utility_discordant_rows": len(discordances),
        "left_better_rows": left_better,
        "right_better_rows": right_better,
        "max_abs_action_mean_utility_delta": max(
            (item["absolute_delta"] for item in action_means), default=0.0,
        ),
        "action_means": action_means,
        "discordances": discordances,
    }


def _shards(root: Path, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = []
    for state_id in manifest["state_ids"]:
        for batch_id in manifest["batch_ids"]:
            result.append(_read_object(
                root / "shards" / state_id / ("batch_%03d.json" % batch_id)
            ))
    return result


def _report_ranks(report: Mapping[str, Any]) -> dict[tuple[str, int], list[str]]:
    result = {}
    for item in report["posterior_weighted_teacher_statistics"]["per_state_batch"]:
        result[(str(item["state_id"]), int(item["batch_id"]))] = list(item["action_rank"])
    return result


def _relative_inside(path: Path, workspace: Path, label: str) -> str:
    try:
        relative = path.relative_to(workspace)
    except ValueError as error:
        raise ValueError("%s escapes audit workspace" % label) from error
    value = str(relative).replace("\\", "/")
    return value or "."


def _compare_platform_outputs(
    left_dir: str | Path,
    right_dir: str | Path,
    workspace_root: str | Path,
    left_workspace_root: str | Path,
    right_workspace_root: str | Path,
    *,
    schema_version: str,
    include_verification_workspaces: bool,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    left, right = Path(left_dir).resolve(), Path(right_dir).resolve()
    left_workspace = Path(left_workspace_root).resolve()
    right_workspace = Path(right_workspace_root).resolve()
    left_path = _relative_inside(left, workspace, "left rollout output")
    right_path = _relative_inside(right, workspace, "right rollout output")
    left_workspace_path = _relative_inside(
        left_workspace, workspace, "left verification workspace",
    )
    right_workspace_path = _relative_inside(
        right_workspace, workspace, "right verification workspace",
    )
    left_verified = verify_oracle_output(left, left_workspace)
    right_verified = verify_oracle_output(right, right_workspace)
    left_manifest = _read_object(left / "run_manifest.json")
    right_manifest = _read_object(right / "run_manifest.json")
    comparable_left = {
        key: value for key, value in left_manifest.items()
        if key not in {"engine", "implementation", "runtime", "manifest_sha256"}
    }
    comparable_right = {
        key: value for key, value in right_manifest.items()
        if key not in {"engine", "implementation", "runtime", "manifest_sha256"}
    }
    config_equal = comparable_left == comparable_right
    left_shards, right_shards = _shards(left, left_manifest), _shards(right, right_manifest)
    if len(left_shards) != len(right_shards):
        raise ValueError("platform outputs have different shard counts")
    shard_results = []
    for left_shard, right_shard in zip(left_shards, right_shards):
        if (
            left_shard["state_id"] != right_shard["state_id"]
            or left_shard["batch_id"] != right_shard["batch_id"]
            or left_shard["candidate_ids"] != right_shard["candidate_ids"]
        ):
            raise ValueError("platform shard identity or candidates differ")
        comparison = compare_rows(left_shard["rows"], right_shard["rows"])
        comparison.update({
            "state_id": left_shard["state_id"],
            "batch_id": left_shard["batch_id"],
            "left_rows_sha256": left_shard["rows_sha256"],
            "right_rows_sha256": right_shard["rows_sha256"],
        })
        shard_results.append(comparison)
    left_report, right_report = _read_object(left / "report.json"), _read_object(right / "report.json")
    rank_equal = _report_ranks(left_report) == _report_ranks(right_report)
    total_discordant = sum(item["utility_discordant_rows"] for item in shard_results)
    max_action_delta = max(
        (item["max_abs_action_mean_utility_delta"] for item in shard_results), default=0.0,
    )
    result = {
        "schema_version": schema_version,
        "left": {
            "path": left_path,
            "platform": left_manifest["runtime"]["platform"],
            "engine": left_manifest["engine"],
            "run_manifest_file_sha256": file_sha256(left / "run_manifest.json"),
            "report_file_sha256": file_sha256(left / "report.json"),
            "verified_rows": left_verified["rows"],
        },
        "right": {
            "path": right_path,
            "platform": right_manifest["runtime"]["platform"],
            "engine": right_manifest["engine"],
            "run_manifest_file_sha256": file_sha256(right / "run_manifest.json"),
            "report_file_sha256": file_sha256(right / "report.json"),
            "verified_rows": right_verified["rows"],
        },
        "semantic_run_config_equal": config_equal,
        "action_rank_equal": rank_equal,
        "shard_count": len(shard_results),
        "row_count": sum(item["common_rows"] for item in shard_results),
        "utility_discordant_rows": total_discordant,
        "max_abs_action_mean_utility_delta": max_action_delta,
        "aggregate_action_means_equal_within_1e_12": max_action_delta <= 1e-12,
        "safe_to_merge_cross_platform_shards": False,
        "authoritative_teacher_platform": "Linux",
        "shards": shard_results,
    }
    if include_verification_workspaces:
        result["left"]["verification_workspace"] = left_workspace_path
        result["right"]["verification_workspace"] = right_workspace_path
    result["manifest_sha256"] = _self_hash(result)
    return result


def compare_platform_outputs(
    left_dir: str | Path,
    right_dir: str | Path,
    workspace_root: str | Path,
    left_workspace_root: str | Path | None = None,
    right_workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    workspace = Path(workspace_root).resolve()
    return _compare_platform_outputs(
        left_dir,
        right_dir,
        workspace,
        workspace if left_workspace_root is None else left_workspace_root,
        workspace if right_workspace_root is None else right_workspace_root,
        schema_version=SCHEMA_VERSION,
        include_verification_workspaces=True,
    )


def write_platform_audit(
    left_dir: str | Path,
    right_dir: str | Path,
    output_path: str | Path,
    workspace_root: str | Path,
    left_workspace_root: str | Path | None = None,
    right_workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    result = compare_platform_outputs(
        left_dir,
        right_dir,
        workspace_root,
        left_workspace_root,
        right_workspace_root,
    )
    write_once(Path(output_path), result)
    return result


def verify_platform_audit(
    output_path: str | Path, workspace_root: str | Path,
) -> dict[str, Any]:
    path = Path(output_path).resolve()
    value = _read_object(path)
    schema_version = value.get("schema_version")
    if (
        schema_version not in {SCHEMA_VERSION, LEGACY_SCHEMA_VERSION}
        or value.get("manifest_sha256") != _self_hash(value)
    ):
        raise ValueError("platform audit self-hash mismatch")
    workspace = Path(workspace_root).resolve()
    if schema_version == LEGACY_SCHEMA_VERSION:
        expected = _compare_platform_outputs(
            workspace / value["left"]["path"],
            workspace / value["right"]["path"],
            workspace,
            workspace,
            workspace,
            schema_version=LEGACY_SCHEMA_VERSION,
            include_verification_workspaces=False,
        )
    else:
        expected = compare_platform_outputs(
            workspace / value["left"]["path"],
            workspace / value["right"]["path"],
            workspace,
            workspace / value["left"]["verification_workspace"],
            workspace / value["right"]["verification_workspace"],
        )
    if value != expected:
        raise ValueError("platform audit does not reproduce")
    return {
        "verified": True,
        "manifest_sha256": value["manifest_sha256"],
        "row_count": value["row_count"],
        "utility_discordant_rows": value["utility_discordant_rows"],
        "action_rank_equal": value["action_rank_equal"],
        "output_path": str(path),
    }
