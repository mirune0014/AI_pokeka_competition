"""Read-only iteration-008 identifiability audit for the rejected iteration-007 agent.

The production entrypoint is intentionally narrow: it accepts one immutable plan,
one absent destination, and produces canonical evidence without constructing an
optimizer, changing a persisted parameter, running a game, or loading iteration006.
Most helpers are pure so the numerical and canonical contracts can be tested on
small synthetic inputs without executing the real 830-row audit.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import AbstractContextManager, contextmanager
import copy
import hashlib
import importlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tempfile
from typing import Any, Callable, Iterable, Mapping, Sequence

import torch


PLAN_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_008_identifiability_audit_plan.json"
)
PLAN_SHA256 = "8FAE5B736C4C1E269AC5FCD1EA1D0146EBC35B78BDA6A454AF452D6920D7E701"
PLAN_SCHEMA_VERSION = "phase1-iteration-008-identifiability-audit-plan-v1"
PLAN_ID = "phase1_iteration_008_read_only_identifiability_audit"
AUDIT_SCHEMA_VERSION = "phase1-iteration-008-identifiability-audit-v1"
AUDIT_IMPLEMENTATION_RELATIVE_PATHS = (
    PurePosixPath("infrastructure/tools/audit_archaludon_iteration007_identifiability.py"),
    PurePosixPath(
        "research/rl_ptcg/tests/test_audit_archaludon_iteration007_identifiability.py"
    ),
)

EXPECTED_ROWS = 830
EXPECTED_TRAJECTORIES = 32
ROBUST_EPSILON = 0.000001
GAMMA = 0.99
GAE_LAMBDA = 0.95
FAMILY_TAU = 1e-7
REQUIRED_THREAD_ENVIRONMENT = {
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}
EXACT_LEVELS = ("P", "P+L", "P+L+a", "O+L+a", "X+L+a")
PRIORITY_GROUPS = (
    "PLAY:positive",
    "ATTACH:negative",
    "EVOLVE:negative",
    "RETREAT:positive",
    "ATTACK:negative",
    "END:positive",
)
REQUIRED_OUTPUT_FILES = (
    "manifest.json",
    "rows.jsonl",
    "exact_collisions.json",
    "near_neighbors.jsonl",
    "group_end_comparison.json",
    "gae_decomposition.jsonl",
    "balance.json",
    "gradient_projection.json",
    "cause_matrix.json",
    "summary.json",
)
GRADIENT_PARAMETER_NAMES = (
    "residual_head.0.weight",
    "residual_head.0.bias",
)

PINNED_FIXED_INPUTS = {
    "iteration004_checkpoint_path": (
        "analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_004_"
        "temperature065_checkpoint_deterministic_20260731/initial_zero_temperature065.pt"
    ),
    "iteration004_checkpoint_sha256": (
        "24D8A4EACD9D7B699D327D3F2436F4DA21AC79433038E6FA96F9AE0E50F8FB04"
    ),
    "manifest_path": (
        "analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_004_"
        "temperature065_single_thread_20260731/rollouts/run_manifest.json"
    ),
    "manifest_sha256": (
        "30BF22BE56E73E8790A40135DD78080217FFAB7598D9646887FD8742D0FCF393"
    ),
    "dataset_sha256": (
        "3D714FC248B597ADD412B1D9B4BAD60DDF6BDEB3DFA652264D763D7A843AC41B"
    ),
    "prepare_receipt_path": (
        "experiments/archaludon_latest_v1_rl_interaction_maturation_candidate_"
        "20260801/test_outputs/phase1_iteration_007_prepare_v4/"
        "pretraining_probe_receipt.json"
    ),
    "prepare_receipt_file_sha256": (
        "7E8F6238ECEE6444C98D041A12A2478EA6FEAD110A73AA224D071AEC5316F08F"
    ),
    "prepare_receipt_sha256": (
        "B4CA02474685E13A492E82D727AC929E7DEDCD03B15047A8962BF59C71AC6AFE"
    ),
    "iteration007_execution_spec_path": (
        "experiments/archaludon_latest_v1_rl/specs/"
        "phase1_iteration_007_frozen_readout_interaction_maturation_execution_spec_v10.json"
    ),
    "iteration007_execution_spec_sha256": (
        "9CDA1C0B8A7BF5E542C23061349505C5AC80119595060B968BD002B7D06CD1CF"
    ),
    "iteration007_receipt_path": (
        "analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_007_"
        "frozen_readout_interaction_maturation_20260801/rejected_receipt.json"
    ),
    "iteration007_receipt_file_sha256": (
        "C2AF5C7BCA142296CAF1407F3FFA498A4FD2E4F71FB7C9E6B68C5D2C2AC0B796"
    ),
    "iteration007_receipt_sha256": (
        "07E8D544F5544779A5488C9072238317FDE238E7BCEE13EE69E9A87B2EBBFC3D"
    ),
    "iteration007_checkpoint_path": (
        "analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_007_"
        "frozen_readout_interaction_maturation_20260801/candidate.pt"
    ),
    "iteration007_checkpoint_sha256": (
        "5547AFD90CF039390CDA8E70E3DA5868C12B0277AA670636573F7BC0FE7715B3"
    ),
    "candidate_implementation_path": (
        "experiments/archaludon_latest_v1_rl_interaction_maturation_candidate_20260801"
    ),
    "candidate_implementation_snapshot_sha256": (
        "6B95C5B6DEB354293E2DC08077DAEC5FE6A77D013832DD70DECC485C91EB87CA"
    ),
    "fixed_advantages_sha256": (
        "B7F77DEBE545FDD5B7767C909E185904A52F161B6253D821950E6FDE6A79E53B"
    ),
    "fixed_behavior_logprobabilities_sha256": (
        "BF402ED36ECD78905597F562E8987927C2D74FD5AEE390F1D1E1426CE3D1DA98"
    ),
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def canonical_json_bytes(value: Any, *, newline: bool = False) -> bytes:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return payload + (b"\n" if newline else b"")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest().upper()


def canonical_jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(dict(row), newline=True) for row in rows)


def _strict_sha256(value: Any, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789ABCDEF" for character in value)
    ):
        raise ValueError(f"{label} must be an uppercase SHA-256")
    return value


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _read_regular_nonlink_bytes(path: Path, *, label: str) -> bytes:
    path = path.absolute()
    if _is_link_or_reparse(path):
        raise ValueError(f"{label} must not be a link or reparse point")
    try:
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError(f"{label} must be a regular file")
            payload = stream.read()
    except (FileNotFoundError, IsADirectoryError, PermissionError) as error:
        raise ValueError(f"{label} must be a readable regular file") from error
    if _is_link_or_reparse(path):
        raise ValueError(f"{label} changed to a link during read")
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
    ):
        raise ValueError(f"{label} changed during read")
    return payload


def sha256_file(path: Path, *, label: str = "file") -> str:
    return hashlib.sha256(_read_regular_nonlink_bytes(path, label=label)).hexdigest().upper()


def _load_hashed_json_with_payload(
    path: Path, expected_sha256: str, *, label: str
) -> tuple[dict[str, Any], bytes]:
    expected = _strict_sha256(expected_sha256, label=f"{label} expected hash")
    payload = _read_regular_nonlink_bytes(path, label=label)
    actual = hashlib.sha256(payload).hexdigest().upper()
    if actual != expected:
        raise ValueError(f"{label} SHA-256 mismatch")
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not valid JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value, payload


def _load_hashed_json(path: Path, expected_sha256: str, *, label: str) -> dict[str, Any]:
    return _load_hashed_json_with_payload(path, expected_sha256, label=label)[0]


def _exact_keys(value: Any, expected: set[str], *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        actual = sorted(value) if isinstance(value, Mapping) else type(value).__name__
        raise ValueError(f"{label} schema mismatch: {actual!r}")
    return value


_PLAN_KEYS = {
    "schema_version", "plan_id", "purpose", "fixed_inputs",
    "expected_population", "execution_constraints", "canonical_identities",
    "exact_identity_levels", "near_identity_levels", "target_contract",
    "trajectory_credit_decomposition", "balance_contract", "gradient_contract",
    "classification_thresholds", "required_output_files", "decision_rule",
}


def validate_plan_object(plan: Mapping[str, Any]) -> None:
    _exact_keys(plan, _PLAN_KEYS, label="audit plan")
    if plan["schema_version"] != PLAN_SCHEMA_VERSION or plan["plan_id"] != PLAN_ID:
        raise ValueError("audit plan identity mismatch")
    if dict(_exact_keys(
        plan["fixed_inputs"], set(PINNED_FIXED_INPUTS), label="fixed inputs"
    )) != PINNED_FIXED_INPUTS:
        raise ValueError("audit plan fixed inputs mismatch")
    expected_population = _exact_keys(
        plan["expected_population"],
        {
            "ppo_rows", "unique_episode_decision_keys", "source_trajectories",
            "diagnostic_priority_groups", "positive_normalized_end_rows",
            "negative_end_controls", "teacher_end_controls",
        },
        label="expected population",
    )
    if expected_population != {
        "ppo_rows": EXPECTED_ROWS,
        "unique_episode_decision_keys": EXPECTED_ROWS,
        "source_trajectories": EXPECTED_TRAJECTORIES,
        "diagnostic_priority_groups": list(PRIORITY_GROUPS),
        "positive_normalized_end_rows": 20,
        "negative_end_controls": 4,
        "teacher_end_controls": 43,
    }:
        raise ValueError("audit expected population mismatch")
    constraints = _exact_keys(
        plan["execution_constraints"],
        {
            "read_only_inputs", "optimizer_construction_or_step",
            "training_or_parameter_mutation", "games_or_runtime_smoke",
            "iteration006_loading", "kaggle_or_external_write",
            "single_fresh_output_directory", "fail_closed_on_hash_row_or_trajectory_mismatch",
            "required_environment",
        },
        label="execution constraints",
    )
    expected_flags = {
        "read_only_inputs": True,
        "optimizer_construction_or_step": False,
        "training_or_parameter_mutation": False,
        "games_or_runtime_smoke": False,
        "iteration006_loading": False,
        "kaggle_or_external_write": False,
        "single_fresh_output_directory": True,
        "fail_closed_on_hash_row_or_trajectory_mismatch": True,
    }
    if any(constraints[name] is not expected for name, expected in expected_flags.items()):
        raise ValueError("audit execution flags mismatch")
    if constraints["required_environment"] != REQUIRED_THREAD_ENVIRONMENT:
        raise ValueError("audit thread environment contract mismatch")
    if tuple(plan["exact_identity_levels"]) != EXACT_LEVELS:
        raise ValueError("exact identity levels mismatch")
    if tuple(plan["required_output_files"]) != REQUIRED_OUTPUT_FILES:
        raise ValueError("required output file list mismatch")
    _exact_keys(
        plan["canonical_identities"], {"P", "O", "L", "a", "X", "row_id"},
        label="canonical identities",
    )
    near = _exact_keys(
        plan["near_identity_levels"],
        {"public_one_unit", "public_two_units", "legal_multiset_one_or_two", "latent_mutual_knn"},
        label="near identity levels",
    )
    _exact_keys(
        near["latent_mutual_knn"],
        {
            "eligible_rows", "distance", "zero_mad_dimensions_ignored",
            "neighbors_per_row", "retain_lowest_nonzero_distance_fraction",
            "mutual_only", "tie_break",
        },
        label="latent mutual KNN",
    )
    target = _exact_keys(
        plan["target_contract"],
        {
            "robust_positive_minimum", "robust_negative_maximum", "otherwise",
            "domains", "exact_conflict", "strong_conflict",
            "unweighted_irreducible_wrong_sign_mass", "loss_weight",
            "weighted_irreducible_wrong_sign_mass",
        },
        label="target contract",
    )
    if (
        target["robust_positive_minimum"] != ROBUST_EPSILON
        or target["robust_negative_maximum"] != -ROBUST_EPSILON
        or tuple(target["domains"]) != (
            "raw_gae_float64",
            "normalized_training_advantage_float32",
            "discounted_realized_return_minus_initial_value",
        )
    ):
        raise ValueError("target polarity contract mismatch")
    credit = _exact_keys(
        plan["trajectory_credit_decomposition"],
        {
            "gamma", "gae_lambda", "required_terms", "reward_channel_limitation",
            "clipping_or_reweighting",
        },
        label="trajectory credit decomposition",
    )
    if credit["gamma"] != GAMMA or credit["gae_lambda"] != GAE_LAMBDA:
        raise ValueError("GAE constants mismatch")
    _exact_keys(plan["balance_contract"], {"units", "required_statistics"}, label="balance contract")
    gradient = _exact_keys(
        plan["gradient_contract"],
        {
            "operations", "stage1_reconstruction", "stage32", "stage16_limitation",
            "required_outputs", "mere_optimization_failure_may_pass_with_missing_update16_parameters",
        },
        label="gradient contract",
    )
    if gradient["mere_optimization_failure_may_pass_with_missing_update16_parameters"] is not False:
        raise ValueError("missing-update16 eligibility contract mismatch")
    _exact_keys(
        plan["classification_thresholds"],
        {
            "representation_collision", "missing_temporal_information",
            "value_or_credit_conflict", "dataset_imbalance", "mere_optimization_failure",
        },
        label="classification thresholds",
    )


def load_and_validate_plan(
    path: Path,
    supplied_sha256: str,
    *,
    expected_path: Path | None = None,
    expected_sha256: str = PLAN_SHA256,
) -> dict[str, Any]:
    supplied = _strict_sha256(supplied_sha256, label="--plan-sha256")
    expected = _strict_sha256(expected_sha256, label="compiled plan hash")
    if supplied != expected:
        raise ValueError("supplied plan SHA-256 does not equal the compiled immutable hash")
    required_path = (expected_path or (repo_root() / Path(*PLAN_RELATIVE_PATH.parts))).resolve()
    candidate = path.absolute().resolve(strict=False)
    if candidate != required_path:
        raise ValueError("--plan does not resolve to the immutable audit plan")
    plan = _load_hashed_json(candidate, expected, label="iteration008 audit plan")
    validate_plan_object(plan)
    return plan


def _validate_absent_output_directory(output_dir: Path) -> Path:
    candidate = output_dir.absolute()
    if candidate.exists() or candidate.is_symlink():
        raise FileExistsError("audit output directory must be absent")
    parent = candidate.parent.resolve(strict=True)
    if not parent.is_dir() or _is_link_or_reparse(parent):
        raise ValueError("audit output parent must be a regular non-link directory")
    resolved = parent / candidate.name
    if resolved.exists() or resolved.is_symlink():
        raise FileExistsError("audit output directory collided during validation")
    return resolved


def _json_domain_copy(value: Any) -> Any:
    return json.loads(canonical_json_bytes(value))


def robust_sign(value: float, *, epsilon: float = ROBUST_EPSILON) -> str:
    number = float(value)
    if not math.isfinite(number) or not math.isfinite(epsilon) or epsilon < 0.0:
        raise ValueError("robust sign requires finite values and a nonnegative epsilon")
    if number >= epsilon:
        return "positive"
    if number <= -epsilon:
        return "negative"
    return "neutral"


def lower_empirical_median(values: Sequence[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered or any(not math.isfinite(value) for value in ordered):
        raise ValueError("lower empirical median requires finite nonempty values")
    return ordered[(len(ordered) - 1) // 2]


def tensor_bytes(tensor: torch.Tensor) -> bytes:
    value = tensor.detach().cpu().contiguous()
    if value.ndim == 0:
        value = value.reshape(1)
    return value.view(torch.uint8).numpy().tobytes(order="C")


def float32_bytes(value: float) -> bytes:
    return tensor_bytes(torch.tensor(float(value), dtype=torch.float32))


def canonical_semantic_action(option: Mapping[str, Any]) -> dict[str, Any]:
    if set(option) != {"engine_index", "identity", "payload"}:
        raise ValueError("semantic option schema mismatch")
    payload = option["payload"]
    if not isinstance(payload, Mapping):
        raise ValueError("semantic action payload must be a mapping")
    if set(payload) != {"option_type", "source_card_id", "target_card_id", "fields"}:
        raise ValueError("semantic action payload schema mismatch")
    if not isinstance(payload["fields"], Mapping):
        raise ValueError("semantic action public fields must be a mapping")
    canonical = _json_domain_copy(payload)
    encoded = canonical_json_bytes(canonical)
    identity = hashlib.sha256(encoded).hexdigest().lower()
    if option["identity"] != identity:
        raise ValueError("semantic action identity does not match its canonical payload")
    if b"engine_index" in encoded:
        raise ValueError("engine_index leaked into canonical semantic action")
    return {
        "value": canonical,
        "canonical_json_bytes_hex": encoded.hex().upper(),
        "byte_count": len(encoded),
        "sha256": identity.upper(),
    }


def canonical_legal_multiset(options: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    actions = [canonical_semantic_action(option) for option in options]
    identities = sorted(action["sha256"] for action in actions)
    encoded = canonical_json_bytes(identities)
    return {
        "sorted_semantic_identities": identities,
        "canonical_json_bytes_hex": encoded.hex().upper(),
        "byte_count": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest().upper(),
    }


def canonical_public_projection(projection: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(projection, Mapping):
        raise ValueError("public projection must be a mapping")
    value = _json_domain_copy(projection)
    encoded = canonical_json_bytes(value)
    return {
        "value": value,
        "canonical_json_bytes_hex": encoded.hex().upper(),
        "byte_count": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest().upper(),
    }


def selected_frozen_latent(
    model: torch.nn.Module,
    row: Mapping[str, Any],
    *,
    sampled_index: int | None = None,
) -> dict[str, Any]:
    selected = int(row["final_action"][0]) if sampled_index is None else int(sampled_index)
    actions = row["action_vectors"]
    if not 0 <= selected < len(actions):
        raise ValueError("sampled action index is outside the action vector surface")
    with torch.no_grad():
        state = torch.tensor(row["state_vector"], dtype=torch.float32, device="cpu")
        action = torch.tensor(actions[selected], dtype=torch.float32, device="cpu")
        state_hidden = model.state_encoder(state)
        action_hidden = model.action_encoder(action)
        latent = torch.cat((state_hidden, action_hidden), dim=-1).to(torch.float32)
    payload = tensor_bytes(latent)
    return {
        "dtype": "float32",
        "shape": list(latent.shape),
        "values_float32": [float(value) for value in latent.tolist()],
        "raw_bytes_hex": payload.hex().upper(),
        "byte_count": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest().upper(),
    }


def row_id_key(row: Mapping[str, Any]) -> tuple[int, str, int]:
    return (
        int(row["ppo_row_ordinal"]),
        str(row["episode_id"]),
        int(row["decision_index"]),
    )


def row_id_value(row: Mapping[str, Any]) -> dict[str, Any]:
    ordinal, episode, decision = row_id_key(row)
    return {"ppo_row_ordinal": ordinal, "episode_id": episode, "decision_index": decision}


def _escape_json_pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _atomic_value(value: Any) -> dict[str, Any]:
    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, bool):
        return {"type": "boolean", "value": value}
    if isinstance(value, int):
        return {"type": "integer", "value": value}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("public projection contains a non-finite scalar")
        return {"type": "number", "value": value}
    if isinstance(value, str):
        return {"type": "string", "value": value}
    raise ValueError(f"unsupported public projection scalar: {type(value).__name__}")


def flatten_public_state(value: Any, *, path: str = "") -> dict[str, dict[str, Any]]:
    flattened: dict[str, dict[str, Any]] = {}

    def visit(item: Any, pointer: str) -> None:
        if isinstance(item, Mapping):
            for key in sorted(item):
                if not isinstance(key, str):
                    raise ValueError("public projection mapping keys must be strings")
                visit(item[key], pointer + "/" + _escape_json_pointer(key))
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, pointer + f"/{index}")
        else:
            flattened[pointer or "/"] = _atomic_value(item)

    visit(value, path)
    return flattened


def _one_unit_atoms(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if left["type"] == right["type"] == "boolean":
        return bool(left["value"] is not right["value"])
    numeric = {"integer", "number"}
    if left["type"] in numeric and right["type"] in numeric:
        return abs(float(left["value"]) - float(right["value"])) == 1.0
    return False


def atomic_public_diff(left: Any, right: Any) -> list[dict[str, Any]]:
    left_flat = flatten_public_state(left)
    right_flat = flatten_public_state(right)
    missing = {"type": "missing", "value": None}
    differences: list[dict[str, Any]] = []
    for pointer in sorted(set(left_flat) | set(right_flat)):
        left_atom = left_flat.get(pointer, missing)
        right_atom = right_flat.get(pointer, missing)
        if left_atom != right_atom:
            differences.append(
                {
                    "path": pointer,
                    "left": left_atom,
                    "right": right_atom,
                    "one_unit": _one_unit_atoms(left_atom, right_atom),
                }
            )
    return differences


def multiset_symmetric_difference(
    left: Sequence[str], right: Sequence[str]
) -> dict[str, Any]:
    left_counts, right_counts = Counter(left), Counter(right)
    left_only: list[str] = []
    right_only: list[str] = []
    for identity in sorted(set(left_counts) | set(right_counts)):
        delta = left_counts[identity] - right_counts[identity]
        if delta > 0:
            left_only.extend([identity] * delta)
        elif delta < 0:
            right_only.extend([identity] * -delta)
    return {
        "left_only": left_only,
        "right_only": right_only,
        "size": len(left_only) + len(right_only),
    }


def effective_sample_size(weights: Sequence[float]) -> float:
    values = [float(weight) for weight in weights]
    if any(not math.isfinite(weight) or weight < 0.0 for weight in values):
        raise ValueError("ESS weights must be finite and nonnegative")
    total = math.fsum(values)
    square_total = math.fsum(weight * weight for weight in values)
    return 0.0 if square_total == 0.0 else total * total / square_total


def weighted_median(values: Sequence[float], weights: Sequence[float]) -> float | None:
    if len(values) != len(weights):
        raise ValueError("weighted median value/weight length mismatch")
    pairs = sorted((float(value), float(weight), index) for index, (value, weight) in enumerate(zip(values, weights)))
    if any(not math.isfinite(value) or not math.isfinite(weight) or weight < 0.0 for value, weight, _ in pairs):
        raise ValueError("weighted median requires finite values and nonnegative weights")
    total = math.fsum(weight for _, weight, _ in pairs)
    if total == 0.0:
        return None
    cumulative = 0.0
    for value, weight, _ in pairs:
        cumulative += weight
        if cumulative * 2.0 >= total:
            return value
    raise AssertionError("weighted median accumulation failed")


def top_fraction_weight_share(weights: Sequence[float], *, fraction: float = 0.1) -> float:
    values = sorted((float(weight) for weight in weights), reverse=True)
    if not values or not 0.0 < fraction <= 1.0:
        return 0.0
    if any(not math.isfinite(weight) or weight < 0.0 for weight in values):
        raise ValueError("weight share requires finite nonnegative weights")
    total = math.fsum(values)
    if total == 0.0:
        return 0.0
    count = max(1, math.ceil(len(values) * fraction))
    return math.fsum(values[:count]) / total


def leave_one_trajectory_out_range(
    rows: Sequence[Mapping[str, Any]],
    *,
    value_field: str,
    weight_field: str,
    trajectory_field: str = "episode_id",
    trajectory_universe: Sequence[str] | None = None,
) -> dict[str, Any]:
    observed = {str(row[trajectory_field]) for row in rows}
    trajectories = sorted(
        set(str(value) for value in trajectory_universe)
        if trajectory_universe is not None
        else observed
    )
    if not observed.issubset(trajectories):
        raise ValueError("LOTO trajectory universe omits an observed trajectory")
    trajectory_weights = {trajectory: 0.0 for trajectory in trajectories}
    for row in rows:
        trajectory_weights[str(row[trajectory_field])] += float(row[weight_field])
    medians: list[dict[str, Any]] = []
    for omitted in trajectories:
        retained = [row for row in rows if str(row[trajectory_field]) != omitted]
        median = weighted_median(
            [float(row[value_field]) for row in retained],
            [float(row[weight_field]) for row in retained],
        )
        medians.append({"omitted_trajectory": omitted, "weighted_median": median})
    available = [row["weighted_median"] for row in medians if row["weighted_median"] is not None]
    return {
        "trajectory_count": len(trajectories),
        "nonzero_trajectory_count": sum(
            weight > 0.0 for weight in trajectory_weights.values()
        ),
        "minimum": min(available) if available else None,
        "maximum": max(available) if available else None,
        "by_omitted_trajectory": medians,
    }


def vector_cosine(left: torch.Tensor, right: torch.Tensor) -> float | None:
    a = left.detach().to(dtype=torch.float64, device="cpu").reshape(-1)
    b = right.detach().to(dtype=torch.float64, device="cpu").reshape(-1)
    if a.numel() != b.numel():
        raise ValueError("cosine vectors differ in dimension")
    a_norm, b_norm = torch.linalg.vector_norm(a), torch.linalg.vector_norm(b)
    if float(a_norm) == 0.0 or float(b_norm) == 0.0:
        return None
    return float(torch.dot(a, b) / (a_norm * b_norm))


def gradient_delta_projection(gradient: torch.Tensor, delta: torch.Tensor) -> dict[str, Any]:
    grad = gradient.detach().to(dtype=torch.float64, device="cpu").reshape(-1)
    change = delta.detach().to(dtype=torch.float64, device="cpu").reshape(-1)
    if grad.numel() != change.numel():
        raise ValueError("gradient and parameter delta differ in dimension")
    dot = float(torch.dot(grad, change))
    return {
        "gradient_norm": float(torch.linalg.vector_norm(grad)),
        "parameter_delta_norm": float(torch.linalg.vector_norm(change)),
        "dot_product": dot,
        "cosine": vector_cosine(grad, change),
        "favorable_ascent_projection": dot > 0.0,
    }


def clipped_ppo_ascent_term(
    ratio: torch.Tensor,
    advantage: torch.Tensor,
    *,
    clip_ratio: float = 0.1,
) -> tuple[torch.Tensor, bool]:
    if ratio.numel() != 1 or advantage.numel() != 1:
        raise ValueError("PPO ascent helper requires scalar tensors")
    unclipped = ratio * advantage
    clipped = torch.clamp(ratio, 1.0 - clip_ratio, 1.0 + clip_ratio) * advantage
    term = torch.minimum(unclipped, clipped)
    ratio_value = float(ratio.detach().cpu())
    advantage_value = float(advantage.detach().cpu())
    active = (
        advantage_value > 0.0 and ratio_value > 1.0 + clip_ratio
    ) or (
        advantage_value < 0.0 and ratio_value < 1.0 - clip_ratio
    )
    return term, active


def _flatten_optional_gradients(
    gradients: Sequence[torch.Tensor | None], parameters: Sequence[torch.Tensor]
) -> torch.Tensor:
    pieces = [
        torch.zeros_like(parameter).reshape(-1) if gradient is None else gradient.detach().reshape(-1)
        for gradient, parameter in zip(gradients, parameters)
    ]
    return torch.cat(pieces).to(dtype=torch.float64, device="cpu")


def gae_decomposition_for_episode(
    rows: Sequence[Mapping[str, Any]],
    *,
    gamma: float = GAMMA,
    gae_lambda: float = GAE_LAMBDA,
) -> list[dict[str, Any]]:
    if not rows:
        return []
    if not (math.isfinite(gamma) and math.isfinite(gae_lambda)):
        raise ValueError("GAE constants must be finite")
    rewards = [float(row.get("reward", 0.0)) for row in rows]
    values = [float(row["value"]) for row in rows]
    if any(not math.isfinite(value) for value in (*rewards, *values)):
        raise ValueError("GAE inputs must be finite")
    count = len(rows)
    deltas: list[float] = []
    for index in range(count):
        mask = 0.0 if index == count - 1 else 1.0
        next_value = 0.0 if mask == 0.0 else values[index + 1]
        deltas.append(rewards[index] + gamma * mask * next_value - values[index])
    raw = [0.0] * count
    running = 0.0
    for index in reversed(range(count)):
        running = deltas[index] + gamma * gae_lambda * running
        raw[index] = running
    returns = [0.0] * count
    running_return = 0.0
    for index in reversed(range(count)):
        running_return = rewards[index] + gamma * running_return
        returns[index] = running_return
    output: list[dict[str, Any]] = []
    discount = gamma * gae_lambda
    for index, row in enumerate(rows):
        terms = [deltas[future] * discount ** (future - index) for future in range(index, count)]

        def bucket(start: int, stop: int | None) -> float:
            selected = terms[start:] if stop is None else terms[start:stop]
            return math.fsum(selected)

        mask = 0.0 if index == count - 1 else 1.0
        next_value = 0.0 if mask == 0.0 else values[index + 1]
        output.append(
            {
                "decision_index": int(row["decision_index"]),
                "reward": rewards[index],
                "bootstrap_mask": mask,
                "current_value": values[index],
                "next_value": next_value,
                "delta_reward_term": rewards[index],
                "delta_next_value_term": gamma * mask * next_value,
                "delta_current_value_term": -values[index],
                "delta": deltas[index],
                "gae_lag_0": bucket(0, 1),
                "gae_lag_1": bucket(1, 2),
                "gae_lags_2_3": bucket(2, 4),
                "gae_lags_4_7": bucket(4, 8),
                "gae_lags_8_plus": bucket(8, None),
                "raw_gae": raw[index],
                "discounted_realized_return": returns[index],
                "monte_carlo_advantage": returns[index] - values[index],
                "terminal_distance": count - index - 1,
            }
        )
    return output


def normalize_advantages_float32(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        raise ValueError("advantage normalization requires at least one row")
    tensor = torch.tensor([float(value) for value in values], dtype=torch.float32)
    mean = tensor.mean()
    sd = tensor.std(unbiased=False)
    if not torch.isfinite(tensor).all() or not torch.isfinite(sd) or float(sd) == 0.0:
        raise ValueError("advantage normalization is non-finite or degenerate")
    normalized = (tensor - mean) / sd
    return {
        "mean_float32": float(mean),
        "population_sd_float32": float(sd),
        "normalized_values_float32": [float(value) for value in normalized.tolist()],
        "normalized_raw_bytes": tensor_bytes(normalized),
    }


def collision_class_statistics(
    members: Sequence[Mapping[str, Any]],
    *,
    domain_fields: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    fields = domain_fields or {
        "raw_gae": "raw_gae_float64",
        "normalized_training_advantage": "normalized_training_advantage_float32",
        "monte_carlo_advantage": "monte_carlo_advantage",
    }
    domains: dict[str, Any] = {}
    for domain, field in fields.items():
        signs = [robust_sign(float(row[field])) for row in members]
        positive = [row for row, sign in zip(members, signs) if sign == "positive"]
        negative = [row for row, sign in zip(members, signs) if sign == "negative"]
        neutral = [row for row, sign in zip(members, signs) if sign == "neutral"]
        positive_weight = math.fsum(float(row["loss_weight"]) for row in positive)
        negative_weight = math.fsum(float(row["loss_weight"]) for row in negative)
        positive_trajectories = {str(row["episode_id"]) for row in positive}
        negative_trajectories = {str(row["episode_id"]) for row in negative}
        domains[domain] = {
            "positive_rows": len(positive),
            "negative_rows": len(negative),
            "neutral_rows": len(neutral),
            "positive_trajectories": len(positive_trajectories),
            "negative_trajectories": len(negative_trajectories),
            "exact_conflict": bool(positive and negative),
            "strong_cross_trajectory_conflict": (
                len(positive_trajectories) >= 2 and len(negative_trajectories) >= 2
            ),
            "unweighted_irreducible_wrong_sign_mass": min(len(positive), len(negative)),
            "weighted_irreducible_wrong_sign_mass": min(positive_weight, negative_weight),
            "positive_loss_weight": positive_weight,
            "negative_loss_weight": negative_weight,
        }
    return {"row_count": len(members), "domains": domains}


def analyze_collision_level(
    rows: Sequence[Mapping[str, Any]],
    *,
    level: str,
    key_function: Callable[[Mapping[str, Any]], Any],
) -> dict[str, Any]:
    grouped: dict[bytes, list[Mapping[str, Any]]] = defaultdict(list)
    key_values: dict[bytes, Any] = {}
    for row in rows:
        key = key_function(row)
        encoded = canonical_json_bytes(key)
        grouped[encoded].append(row)
        key_values[encoded] = key
    classes: list[dict[str, Any]] = []
    totals = {
        domain: {
            "conflict_classes": 0,
            "strong_conflict_classes": 0,
            "unweighted_irreducible_wrong_sign_mass": 0,
            "weighted_irreducible_wrong_sign_mass": 0.0,
        }
        for domain in ("raw_gae", "normalized_training_advantage", "monte_carlo_advantage")
    }
    for encoded in sorted(grouped):
        members = sorted(grouped[encoded], key=row_id_key)
        if len(members) < 2:
            continue
        statistics = collision_class_statistics(members)
        class_row = {
            "class_id": hashlib.sha256(encoded).hexdigest().upper(),
            "identity_key": key_values[encoded],
            "row_ids": [row_id_value(row) for row in members],
            **statistics,
        }
        classes.append(class_row)
        for domain, evidence in statistics["domains"].items():
            if evidence["exact_conflict"]:
                totals[domain]["conflict_classes"] += 1
            if evidence["strong_cross_trajectory_conflict"]:
                totals[domain]["strong_conflict_classes"] += 1
            totals[domain]["unweighted_irreducible_wrong_sign_mass"] += evidence[
                "unweighted_irreducible_wrong_sign_mass"
            ]
            totals[domain]["weighted_irreducible_wrong_sign_mass"] += evidence[
                "weighted_irreducible_wrong_sign_mass"
            ]
    return {
        "level": level,
        "total_identity_classes": len(grouped),
        "duplicate_classes": len(classes),
        "duplicate_rows": sum(row["row_count"] for row in classes),
        "domain_totals": totals,
        "classes": classes,
    }


def analyze_o_to_x_collapses(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["X_sha256"]), str(row["L_sha256"]), str(row["a_sha256"]))].append(row)
    collapses: list[dict[str, Any]] = []
    collapsed_row_ordinals: set[int] = set()
    evidentiary_row_ordinals: set[int] = set()
    induced_mass_total = 0.0
    threshold_numerator = 0.0
    threshold_denominator = math.fsum(
        float(row["loss_weight"])
        for row in rows
        if bool(row.get("priority_group", False))
        and float(row.get("stage32_oriented_probability_delta", math.inf)) <= FAMILY_TAU
    )
    for key in sorted(grouped):
        members = sorted(grouped[key], key=row_id_key)
        o_identities = sorted({str(row["O_sha256"]) for row in members})
        statistics = collision_class_statistics(members)
        ordinals = {int(row["ppo_row_ordinal"]) for row in members}
        is_collapse = len(o_identities) >= 2
        if is_collapse:
            collapsed_row_ordinals.update(ordinals)
        positive = [
            row for row in members
            if robust_sign(float(row["normalized_training_advantage_float32"])) == "positive"
        ]
        negative = [
            row for row in members
            if robust_sign(float(row["normalized_training_advantage_float32"])) == "negative"
        ]
        positive_weight = math.fsum(float(row["loss_weight"]) for row in positive)
        negative_weight = math.fsum(float(row["loss_weight"]) for row in negative)
        mass_x = min(positive_weight, negative_weight)
        by_o: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for row in members:
            by_o[str(row["O_sha256"])].append(row)
        subclasses: list[dict[str, Any]] = []
        mass_o = 0.0
        for o_identity, subclass_members in sorted(by_o.items()):
            o_positive = math.fsum(
                float(row["loss_weight"])
                for row in subclass_members
                if robust_sign(float(row["normalized_training_advantage_float32"]))
                == "positive"
            )
            o_negative = math.fsum(
                float(row["loss_weight"])
                for row in subclass_members
                if robust_sign(float(row["normalized_training_advantage_float32"]))
                == "negative"
            )
            subclass_mass = min(o_positive, o_negative)
            mass_o += subclass_mass
            subclasses.append(
                {
                    "O_sha256": o_identity,
                    "positive_loss_weight": o_positive,
                    "negative_loss_weight": o_negative,
                    "inherited_O_conflict_mass": subclass_mass,
                    "row_ids": [row_id_value(row) for row in sorted(subclass_members, key=row_id_key)],
                }
            )
        induced = max(0.0, mass_x - mass_o)
        strong_x = statistics["domains"]["normalized_training_advantage"][
            "strong_cross_trajectory_conflict"
        ]
        evidentiary = is_collapse and strong_x and induced > 0.0
        priority_weight = math.fsum(
            float(row["loss_weight"])
            for row in members
            if bool(row.get("priority_group", False))
            and float(row.get("stage32_oriented_probability_delta", math.inf)) <= FAMILY_TAU
        )
        contribution = min(induced, priority_weight) if evidentiary else 0.0
        induced_mass_total += induced if evidentiary else 0.0
        threshold_numerator += contribution
        if evidentiary:
            evidentiary_row_ordinals.update(ordinals)
        collapses.append(
            {
                "class_id": canonical_sha256(list(key)),
                "X_sha256": key[0],
                "L_sha256": key[1],
                "a_sha256": key[2],
                "distinct_O_plus_L_plus_a_classes": len(o_identities),
                "is_O_to_X_collapse": is_collapse,
                "O_sha256_values": o_identities,
                "row_ids": [row_id_value(row) for row in members],
                "O_subclasses": subclasses,
                "mass_X": mass_x,
                "mass_O_inherited": mass_o,
                "representation_induced_mass": induced,
                "strong_X_cross_trajectory_sign_conflict": strong_x,
                "evidentiary_representation_collapse": evidentiary,
                "priority_anti_or_neutral_loss_weight_in_class": priority_weight,
                "threshold_numerator_contribution": contribution,
                **statistics,
            }
        )
    return {
        "X_plus_L_plus_a_classes_audited": len(collapses),
        "collapse_classes": sum(row["is_O_to_X_collapse"] for row in collapses),
        "collapsed_rows": len(collapsed_row_ordinals),
        "evidentiary_rows": sorted(evidentiary_row_ordinals),
        "evidentiary_induced_mass_total": induced_mass_total,
        "threshold_numerator_induced_mass_capped_by_priority_weight": threshold_numerator,
        "threshold_denominator_priority_anti_or_neutral_loss_weight": threshold_denominator,
        "threshold_fraction": _safe_fraction(threshold_numerator, threshold_denominator),
        "classes": collapses,
    }


def analyze_value_credit_attribution(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["O_sha256"]), str(row["L_sha256"]), str(row["a_sha256"]))].append(row)
    classes: list[dict[str, Any]] = []
    baseline_total = 0.0
    mc_total = 0.0
    credited_total = 0.0
    for key in sorted(grouped):
        members = sorted(grouped[key], key=row_id_key)

        def mass(field: str) -> tuple[float, float, float]:
            positive = math.fsum(
                float(row["loss_weight"])
                for row in members
                if robust_sign(float(row[field])) == "positive"
            )
            negative = math.fsum(
                float(row["loss_weight"])
                for row in members
                if robust_sign(float(row[field])) == "negative"
            )
            return positive, negative, min(positive, negative)

        normalized_positive, normalized_negative, baseline_mass = mass(
            "normalized_training_advantage_float32"
        )
        mc_positive, mc_negative, mc_mass = mass("monte_carlo_advantage")
        if baseline_mass <= 0.0:
            continue
        robust_flips = [
            row
            for row in members
            if robust_sign(float(row["normalized_training_advantage_float32"]))
            in {"positive", "negative"}
            and robust_sign(float(row["monte_carlo_advantage"]))
            in {"positive", "negative"}
            and robust_sign(float(row["normalized_training_advantage_float32"]))
            != robust_sign(float(row["monte_carlo_advantage"]))
        ]
        robust_flip_weight = math.fsum(float(row["loss_weight"]) for row in robust_flips)
        mc_resolves = mc_mass == 0.0
        credited = baseline_mass if mc_resolves else min(baseline_mass, robust_flip_weight)
        baseline_total += baseline_mass
        mc_total += mc_mass
        credited_total += credited
        classes.append(
            {
                "class_id": canonical_sha256(list(key)),
                "O_sha256": key[0],
                "L_sha256": key[1],
                "a_sha256": key[2],
                "row_ids": [row_id_value(row) for row in members],
                "normalized_positive_loss_weight": normalized_positive,
                "normalized_negative_loss_weight": normalized_negative,
                "baseline_normalized_irreducible_mass": baseline_mass,
                "MC_positive_loss_weight": mc_positive,
                "MC_negative_loss_weight": mc_negative,
                "MC_irreducible_mass": mc_mass,
                "MC_resolves_class": mc_resolves,
                "robust_sign_flipped_row_ids": [row_id_value(row) for row in robust_flips],
                "robust_sign_flipped_loss_weight": robust_flip_weight,
                "credited_changed_or_resolved_mass": credited,
                "credit_capped_at_baseline_mass": credited <= baseline_mass,
            }
        )
    return {
        "baseline_irreducible_mass_denominator": baseline_total,
        "MC_irreducible_mass_total": mc_total,
        "credited_changed_or_resolved_mass_numerator": credited_total,
        "credited_fraction": _safe_fraction(credited_total, baseline_total),
        "classes": classes,
    }


def _median(values: Sequence[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("median requires values")
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0


def mad_scaled_mutual_knn(
    rows: Sequence[Mapping[str, Any]],
    *,
    neighbors_per_row: int = 5,
    retain_fraction: float = 0.01,
) -> dict[str, Any]:
    if neighbors_per_row <= 0 or not 0.0 < retain_fraction <= 1.0:
        raise ValueError("invalid mutual KNN contract")
    if not rows:
        return {
            "active_dimensions": [], "zero_mad_dimensions": [],
            "nonzero_mutual_pairs_before_fraction_filter": 0,
            "retained_distance_threshold": None, "pairs": [],
        }
    vectors = [[float(value) for value in row["X_values_float32"]] for row in rows]
    dimension = len(vectors[0])
    if dimension == 0 or any(len(vector) != dimension for vector in vectors):
        raise ValueError("latent vectors have inconsistent dimensions")
    medians = [_median([vector[index] for vector in vectors]) for index in range(dimension)]
    mads = [
        _median([abs(vector[index] - medians[index]) for vector in vectors])
        for index in range(dimension)
    ]
    active = [index for index, mad in enumerate(mads) if mad != 0.0]
    zero = [index for index, mad in enumerate(mads) if mad == 0.0]
    scaled = [
        [(vector[index] - medians[index]) / mads[index] for index in active]
        for vector in vectors
    ]
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        groups[(str(row["L_sha256"]), str(row["a_sha256"]))].append(index)
    neighbor_sets: dict[int, set[int]] = {index: set() for index in range(len(rows))}
    distance_lookup: dict[tuple[int, int], float] = {}
    for indices in groups.values():
        for left in indices:
            candidates: list[tuple[float, tuple[int, str, int], int]] = []
            for right in indices:
                if left == right:
                    continue
                distance = math.sqrt(math.fsum(
                    (scaled[left][dim] - scaled[right][dim]) ** 2
                    for dim in range(len(active))
                ))
                if not math.isfinite(distance):
                    raise ValueError("latent KNN distance is non-finite")
                candidates.append((distance, row_id_key(rows[right]), right))
                distance_lookup[(min(left, right), max(left, right))] = distance
            candidates.sort(key=lambda item: (item[0], item[1]))
            neighbor_sets[left].update(item[2] for item in candidates[:neighbors_per_row])
    mutual: list[tuple[float, int, int]] = []
    for left in range(len(rows)):
        for right in sorted(neighbor_sets[left]):
            if left < right and left in neighbor_sets[right]:
                distance = distance_lookup[(left, right)]
                if distance > 0.0:
                    mutual.append((distance, left, right))
    mutual.sort(key=lambda item: (item[0], row_id_key(rows[item[1]]), row_id_key(rows[item[2]])))
    threshold: float | None = None
    retained: list[tuple[float, int, int]] = []
    if mutual:
        rank = max(1, math.ceil(len(mutual) * retain_fraction))
        threshold = mutual[rank - 1][0]
        retained = [item for item in mutual if item[0] <= threshold]
    pairs = [
        {
            "left_row_id": row_id_value(rows[left]),
            "right_row_id": row_id_value(rows[right]),
            "distance": distance,
            "normalized_signs": [
                robust_sign(float(rows[left]["normalized_training_advantage_float32"])),
                robust_sign(float(rows[right]["normalized_training_advantage_float32"])),
            ],
        }
        for distance, left, right in retained
    ]
    return {
        "active_dimensions": active,
        "zero_mad_dimensions": zero,
        "median_values": medians,
        "mad_values": mads,
        "nonzero_mutual_pairs_before_fraction_filter": len(mutual),
        "retained_distance_threshold": threshold,
        "pairs": pairs,
    }


def classify_causes(metrics: Mapping[str, Any]) -> dict[str, Any]:
    def reaches(name: str, threshold: float) -> bool:
        value = metrics.get(name)
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            and float(value) >= threshold
        )

    representation = reaches("representation_collision_fraction", 0.5)
    temporal = (
        reaches("temporal_conflict_reduction_fraction", 0.5)
        and (
            int(metrics.get("temporal_priority_rows_covered", 0)) >= 10
            or int(metrics.get("temporal_failed_groups_covered", 0)) >= 2
        )
    )
    credit = reaches("value_credit_changed_or_resolved_fraction", 0.5)
    imbalance = bool(metrics.get("dataset_imbalance_group_passes", []))
    preceding_material = representation or temporal or credit or imbalance
    mere_checks = {
        "preceding_material_causes_absent": not preceding_material,
        "near_neighbor_target_agreement_at_least_90_percent": (
            metrics.get("near_neighbor_target_agreement") is not None
            and float(metrics["near_neighbor_target_agreement"]) >= 0.9
        ),
        "gae_mc_sign_agreement_at_least_90_percent": (
            metrics.get("gae_mc_sign_agreement") is not None
            and float(metrics["gae_mc_sign_agreement"]) >= 0.9
        ),
        "reweighting_preserves_direction": bool(metrics.get("reweighting_preserves_direction", False)),
        "all_six_group_derivatives_favorable": bool(metrics.get("all_six_group_derivatives_favorable", False)),
        "intermediate_parameter_evidence_complete": bool(
            metrics.get("intermediate_parameter_evidence_complete", False)
        ),
    }
    mere = all(mere_checks.values())
    return {
        "representation_collision": {"evidenced": representation, "threshold": 0.5},
        "missing_temporal_information": {
            "evidenced": temporal,
            "reduction_threshold": 0.5,
            "coverage_threshold": "10 priority rows or 2 failed groups",
        },
        "value_or_credit_conflict": {"evidenced": credit, "threshold": 0.5},
        "dataset_imbalance": {
            "evidenced": imbalance,
            "passing_groups": list(metrics.get("dataset_imbalance_group_passes", [])),
        },
        "mere_optimization_failure": {
            "evidenced": mere,
            "eligibility_checks": mere_checks,
            "ineligible_because_update16_parameters_unavailable": not bool(
                metrics.get("intermediate_parameter_evidence_complete", False)
            ),
        },
    }


def implementation_snapshot_with_buffers(
    root: Path,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Reproduce the clean-room candidate's strict source-tree snapshot."""

    root = root.resolve(strict=True)
    if not root.is_dir() or _is_link_or_reparse(root):
        raise ValueError("candidate implementation must be a regular non-link directory")
    paths: list[tuple[bytes, str, Path]] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or "test_outputs" in relative.parts:
            continue
        if path.suffix == ".pyc":
            continue
        if _is_link_or_reparse(path):
            raise ValueError(f"candidate snapshot contains a link: {relative.as_posix()}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"candidate snapshot contains a non-regular entry: {relative.as_posix()}")
        relative_posix = relative.as_posix()
        paths.append((relative_posix.encode("utf-8"), relative_posix, path))
    paths.sort(key=lambda item: item[0])
    records: list[dict[str, Any]] = []
    buffers: dict[str, bytes] = {}
    preimage: list[bytes] = []
    for relative_bytes, relative, path in paths:
        payload = _read_regular_nonlink_bytes(path, label=f"candidate file {relative}")
        digest = hashlib.sha256(payload).hexdigest().upper()
        records.append({"path": relative, "bytes": len(payload), "sha256": digest})
        buffers[relative] = payload
        preimage.append(
            relative_bytes
            + b"\0"
            + str(len(payload)).encode("ascii")
            + b"\0"
            + digest.encode("ascii")
            + b"\n"
        )
    return ({
        "definition": (
            "Enumerate regular files recursively, excluding every path with a "
            "__pycache__ or test_outputs component and every .pyc suffix. Sort by "
            "the unsigned UTF-8 bytes of each relative POSIX path in ascending "
            "lexicographic order. Hash the concatenation, for each file, of "
            "relative_path UTF-8 bytes, NUL, decimal byte_size ASCII, NUL, "
            "uppercase_file_sha256 ASCII, and LF."
        ),
        "file_count": len(records),
        "sha256": hashlib.sha256(b"".join(preimage)).hexdigest().upper(),
        "files": records,
    }, buffers)


def implementation_snapshot(root: Path) -> dict[str, Any]:
    return implementation_snapshot_with_buffers(root)[0]


def exact_guarded_tree_snapshot_with_buffers(
    tree_root: Path,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Capture an exact, link-free directory closure and its retained bytes."""

    tree_root = tree_root.resolve(strict=True)
    if not tree_root.is_dir() or _is_link_or_reparse(tree_root):
        raise ValueError("guarded tree root must be a regular non-link directory")
    directories: list[str] = []
    paths: list[tuple[bytes, str, Path]] = []
    for path in tree_root.rglob("*"):
        relative = path.relative_to(tree_root)
        relative_posix = relative.as_posix()
        if _is_link_or_reparse(path):
            raise ValueError(f"guarded tree contains a link: {relative_posix}")
        if path.is_dir():
            directories.append(relative_posix)
            continue
        if not path.is_file():
            raise ValueError(f"guarded tree contains a non-regular entry: {relative_posix}")
        if path.suffix == ".pyc" or "__pycache__" in relative.parts:
            raise ValueError(f"guarded tree contains bytecode: {relative_posix}")
        paths.append((relative_posix.encode("utf-8"), relative_posix, path))
    directories.sort(key=lambda value: value.encode("utf-8"))
    paths.sort(key=lambda item: item[0])
    records: list[dict[str, Any]] = []
    buffers: dict[str, bytes] = {}
    preimage = [b"D\0" + value.encode("utf-8") + b"\n" for value in directories]
    for relative_bytes, relative, path in paths:
        payload = _read_regular_nonlink_bytes(path, label=f"guarded tree file {relative}")
        digest = hashlib.sha256(payload).hexdigest().upper()
        records.append({"path": relative, "bytes": len(payload), "sha256": digest})
        buffers[relative] = payload
        preimage.append(
            b"F\0"
            + relative_bytes
            + b"\0"
            + str(len(payload)).encode("ascii")
            + b"\0"
            + digest.encode("ascii")
            + b"\n"
        )
    return (
        {
            "definition": (
                "Enumerate the complete link-free directory closure with no ignored "
                "entries. Sort directory and regular-file relative POSIX paths by "
                "unsigned UTF-8 bytes. Hash D,NUL,path,LF for every directory followed "
                "by F,NUL,path,NUL,decimal byte size,NUL,uppercase file SHA-256,LF for "
                "every file. Python bytecode is forbidden."
            ),
            "directory_count": len(directories),
            "directories": directories,
            "file_count": len(records),
            "total_bytes": sum(record["bytes"] for record in records),
            "sha256": hashlib.sha256(b"".join(preimage)).hexdigest().upper(),
            "files": records,
        },
        buffers,
    )


def audit_implementation_snapshot_with_buffers(
    root: Path,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Bind this audit implementation and its focused test to retained bytes."""

    root = root.resolve(strict=True)
    records: list[dict[str, Any]] = []
    buffers: dict[str, bytes] = {}
    preimage: list[bytes] = []
    for relative in AUDIT_IMPLEMENTATION_RELATIVE_PATHS:
        path = _resolve_fixed_path(root, relative.as_posix(), label="audit implementation")
        payload = _read_regular_nonlink_bytes(
            path, label=f"audit implementation {relative.as_posix()}"
        )
        digest = hashlib.sha256(payload).hexdigest().upper()
        records.append(
            {"path": relative.as_posix(), "bytes": len(payload), "sha256": digest}
        )
        buffers[relative.as_posix()] = payload
        preimage.append(
            relative.as_posix().encode("utf-8")
            + b"\0"
            + str(len(payload)).encode("ascii")
            + b"\0"
            + digest.encode("ascii")
            + b"\n"
        )
    return (
        {
            "definition": (
                "Retain the exact bytes of the production audit script and its focused "
                "test, then hash sorted path,NUL,size,NUL,file-SHA-256,LF records."
            ),
            "file_count": len(records),
            "sha256": hashlib.sha256(b"".join(preimage)).hexdigest().upper(),
            "files": records,
        },
        buffers,
    )


def assert_audit_implementation_unchanged(
    root: Path,
    guarded_buffers: Mapping[str, bytes],
    *,
    phase: str,
) -> None:
    expected_paths = {relative.as_posix() for relative in AUDIT_IMPLEMENTATION_RELATIVE_PATHS}
    if set(guarded_buffers) != expected_paths:
        raise ValueError("guarded audit implementation inventory mismatch")
    for relative in sorted(expected_paths):
        path = _resolve_fixed_path(root, relative, label="audit implementation recheck")
        if _read_regular_nonlink_bytes(path, label=f"audit implementation recheck {relative}") != guarded_buffers[relative]:
            raise RuntimeError(f"audit implementation changed at {phase}: {relative}")


def import_clean_room_candidate(candidate_root: Path) -> Any:
    """Import the frozen package under a private name without editing ``sys.path``."""

    candidate_root = candidate_root.resolve(strict=True)
    package_init = candidate_root / "archaludon_rl" / "__init__.py"
    if not package_init.is_file() or _is_link_or_reparse(package_init):
        raise ValueError("clean-room candidate package is unavailable")
    alias = "_iteration007_identifiability_clean_room_6b95c5b6"
    if any(name == alias or name.startswith(alias + ".") for name in sys.modules):
        raise RuntimeError("private clean-room import alias already exists")
    spec = importlib.util.spec_from_file_location(
        alias,
        package_init,
        submodule_search_locations=[str(package_init.parent)],
    )
    if spec is None or spec.loader is None:
        raise ImportError("could not create clean-room candidate import specification")
    package = importlib.util.module_from_spec(spec)
    sys.modules[alias] = package
    try:
        spec.loader.exec_module(package)
    except BaseException:
        sys.modules.pop(alias, None)
        raise
    return importlib.import_module(f"{alias}.actor_only_interaction_maturation_pilot")


class ReadOnlyOperationGuard(AbstractContextManager["ReadOnlyOperationGuard"]):
    """Measure and reject optimizer, training, game, and runtime-smoke attempts."""

    def __init__(self) -> None:
        self.attempt_records: list[str] = []
        self._optimizer_patches: list[tuple[type[Any], str, Any]] = []
        self._entrypoint_patches: list[tuple[Any, str, Any]] = []

    @property
    def attempts(self) -> int:
        return len(self.attempt_records)

    def _forbidden(self, label: str) -> Callable[..., Any]:
        def fail(*args: Any, **kwargs: Any) -> Any:
            del args, kwargs
            self.attempt_records.append(label)
            raise RuntimeError(f"forbidden read-only audit operation attempted: {label}")

        return fail

    def _install_optimizer_guards(self) -> None:
        optimizer_classes = {torch.optim.Optimizer}
        frontier = [torch.optim.Optimizer]
        while frontier:
            parent = frontier.pop()
            for child in parent.__subclasses__():
                if child not in optimizer_classes:
                    optimizer_classes.add(child)
                    frontier.append(child)
        optimizer_classes.update(
            value
            for value in vars(torch.optim).values()
            if isinstance(value, type) and issubclass(value, torch.optim.Optimizer)
        )
        already_patched = {
            (optimizer_class, attribute)
            for optimizer_class, attribute, _ in self._optimizer_patches
        }
        for optimizer_class in sorted(optimizer_classes, key=lambda value: value.__name__):
            for attribute in ("__init__", "step"):
                if (
                    attribute in optimizer_class.__dict__
                    and (optimizer_class, attribute) not in already_patched
                ):
                    original = optimizer_class.__dict__[attribute]
                    self._optimizer_patches.append((optimizer_class, attribute, original))
                    already_patched.add((optimizer_class, attribute))
                    setattr(
                        optimizer_class,
                        attribute,
                        self._forbidden(
                            f"torch.optim.{optimizer_class.__name__}.{attribute}"
                        ),
                    )

    def __enter__(self) -> "ReadOnlyOperationGuard":
        self._install_optimizer_guards()
        return self

    def install_candidate_entrypoint_guards(self, alias: str) -> None:
        self._install_optimizer_guards()
        forbidden_names = {
            "execute", "train", "collect", "collect_episode", "collect_rollouts",
            "main", "play_game", "run_game", "run_games", "simulate_game",
            "run_model_preflight",
            "_one_full_batch_step", "_stage_full_batch_step",
            "_run_two_stage", "_run_two_stage_iteration006_legacy",
            "_new_adam", "_new_actor_adam", "_optimizer_step_and_record",
        }
        for module_name, module in sorted(sys.modules.items()):
            if module_name != alias and not module_name.startswith(alias + "."):
                continue
            for name in sorted(forbidden_names):
                if hasattr(module, name) and callable(getattr(module, name)):
                    original = getattr(module, name)
                    self._entrypoint_patches.append((module, name, original))
                    setattr(module, name, self._forbidden(f"{module_name}.{name}"))

    def assert_clean(self, *, phase: str) -> None:
        if self.attempt_records:
            raise RuntimeError(
                f"read-only safety verdict failed at {phase}: "
                + ",".join(self.attempt_records)
            )

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        for module, name, original in reversed(self._entrypoint_patches):
            setattr(module, name, original)
        for optimizer_class, attribute, original in reversed(self._optimizer_patches):
            setattr(optimizer_class, attribute, original)
        return None


# Backward-compatible public name used by the focused guard test.
AdamConstructionGuard = ReadOnlyOperationGuard


def _write_verified_mirror_file(root: Path, relative: str, payload: bytes) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError("verified mirror path is unsafe")
    path = root / Path(*pure.parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    if _read_regular_nonlink_bytes(path, label=f"verified mirror {relative}") != payload:
        raise ValueError("verified mirror readback mismatch")
    return path


def _safe_checkpoint_loader(
    clean_room: Any,
    buffers_by_path: Mapping[Path, bytes],
) -> Callable[..., tuple[Any, dict[str, Any], dict[str, Any] | None]]:
    normalized = {path.resolve(strict=True): payload for path, payload in buffers_by_path.items()}

    def load_checkpoint(
        path: Path | str,
        *,
        expected_source_hashes: Mapping[str, str] | None = None,
        device: str | torch.device = "cpu",
    ) -> tuple[Any, dict[str, Any], dict[str, Any] | None]:
        resolved = Path(path).resolve(strict=True)
        if resolved not in normalized:
            raise ValueError("checkpoint deserialization is restricted to guarded mirror buffers")
        payload = torch.load(
            io.BytesIO(normalized[resolved]),
            map_location=device,
            weights_only=True,
        )
        if not isinstance(payload, dict):
            raise ValueError("checkpoint payload must be a mapping")
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError("checkpoint metadata missing")
        clean_room._validate_metadata(
            metadata, expected_source_hashes=expected_source_hashes
        )
        config = clean_room.ModelConfig(**payload.get("model_config", {}))
        model = clean_room.ResidualActorCritic(config).to(device)
        model.load_state_dict(payload["model_state"], strict=True)
        return model, metadata, payload.get("optimizer_state")

    return load_checkpoint


@contextmanager
def verified_clean_room_context(
    *,
    fixed: Mapping[str, Any],
    root: Path,
    guard: ReadOnlyOperationGuard,
) -> Iterable[tuple[Any, dict[str, Any], dict[str, Path], Path, Path]]:
    """Yield a fresh source-only candidate imported from verified mirror bytes."""

    alias = "_iteration007_identifiability_clean_room_6b95c5b6"
    if any(name == alias or name.startswith(alias + ".") for name in sys.modules):
        raise RuntimeError("private clean-room import alias already exists before mirroring")
    mirror_parent = (root / "analysis_outputs").resolve(strict=True)
    if not mirror_parent.is_dir() or _is_link_or_reparse(mirror_parent):
        raise ValueError("verified mirror parent is unavailable")
    mirror_root = Path(
        tempfile.mkdtemp(prefix=".iteration008-verified-mirror-", dir=mirror_parent)
    ).resolve(strict=True)
    source_root = mirror_root / "source_candidate"
    input_root = mirror_root / "guarded_inputs"
    source_root.mkdir()
    input_root.mkdir()
    old_dont_write_bytecode = sys.dont_write_bytecode
    clean_room: Any | None = None
    original_repo_path: Any = None
    original_load_checkpoint: Any = None
    mirror_receipt: dict[str, Any] = {}
    mirrored_paths: dict[str, Path] = {}
    try:
        for relative, payload in sorted(fixed["candidate_source_buffers"].items()):
            _write_verified_mirror_file(source_root, relative, payload)
        mirrored_snapshot = implementation_snapshot(source_root)
        if mirrored_snapshot != fixed["candidate_snapshot"]:
            raise ValueError("verified source mirror snapshot mismatch")
        rollout_mirror_root = input_root / Path(
            *PurePosixPath(fixed["guarded_rollout_root_relative"]).parts
        )
        rollout_mirror_root.mkdir(parents=True)
        for relative in fixed["guarded_rollout_tree_snapshot"]["directories"]:
            directory = rollout_mirror_root / Path(*PurePosixPath(relative).parts)
            directory.mkdir(parents=True, exist_ok=False)
        input_receipts: list[dict[str, Any]] = []
        for relative, payload in sorted(fixed["guarded_input_buffers"].items()):
            path = _write_verified_mirror_file(input_root, relative, payload)
            mirrored_paths[relative] = path
            input_receipts.append(
                {
                    "path": relative,
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest().upper(),
                }
            )
        mirrored_rollout_snapshot, _ = exact_guarded_tree_snapshot_with_buffers(
            rollout_mirror_root
        )
        if mirrored_rollout_snapshot != fixed["guarded_rollout_tree_snapshot"]:
            raise ValueError("verified rollout mirror does not have exact guarded closure")
        sys.dont_write_bytecode = True
        clean_room = import_clean_room_candidate(source_root)
        guard.install_candidate_entrypoint_guards(alias)
        original_repo_path = clean_room.inherited._repo_path
        initial_relative = PINNED_FIXED_INPUTS["iteration004_checkpoint_path"]
        manifest_relative = PINNED_FIXED_INPUTS["manifest_path"]

        def mirror_repo_path(relative: PurePosixPath) -> Path:
            relative_string = PurePosixPath(relative).as_posix()
            if relative_string in {initial_relative, manifest_relative}:
                return mirrored_paths[relative_string]
            return original_repo_path(relative)

        clean_room.inherited._repo_path = mirror_repo_path
        original_load_checkpoint = clean_room.inherited.load_checkpoint
        checkpoint_paths = {
            mirrored_paths[PINNED_FIXED_INPUTS["iteration004_checkpoint_path"]]: fixed[
                "guarded_input_buffers"
            ][PINNED_FIXED_INPUTS["iteration004_checkpoint_path"]],
            mirrored_paths[PINNED_FIXED_INPUTS["iteration007_checkpoint_path"]]: fixed[
                "guarded_input_buffers"
            ][PINNED_FIXED_INPUTS["iteration007_checkpoint_path"]],
        }
        clean_room.inherited.load_checkpoint = _safe_checkpoint_loader(
            clean_room, checkpoint_paths
        )
        if any(path.suffix == ".pyc" or "__pycache__" in path.parts for path in mirror_root.rglob("*")):
            raise ValueError("bytecode appeared in the verified mirror")
        mirror_receipt = {
            "method": (
                "Fresh private source-only mirror from guarded bytes; bytecode "
                "publication disabled; inherited checkpoint/manifest paths redirected "
                "to guarded mirror files; checkpoint deserialization uses the retained "
                "guarded byte buffers with torch.load(weights_only=True)."
            ),
            "source_snapshot": mirrored_snapshot,
            "guarded_input_files": input_receipts,
            "guarded_rollout_tree_snapshot": mirrored_rollout_snapshot,
            "guarded_rollout_tree_exact_closure_verified": True,
            "bytecode_publication_disabled": True,
            "preexisting_private_alias_rejected": True,
            "weights_only_checkpoint_deserialization": True,
        }
        yield clean_room, mirror_receipt, mirrored_paths, source_root, mirror_root
        if any(path.suffix == ".pyc" or "__pycache__" in path.parts for path in mirror_root.rglob("*")):
            raise ValueError("bytecode appeared in the verified mirror during execution")
    finally:
        if clean_room is not None:
            if original_repo_path is not None:
                clean_room.inherited._repo_path = original_repo_path
            if original_load_checkpoint is not None:
                clean_room.inherited.load_checkpoint = original_load_checkpoint
        for module_name in sorted(
            [
                name
                for name in sys.modules
                if name == alias or name.startswith(alias + ".")
            ],
            reverse=True,
        ):
            sys.modules.pop(module_name, None)
        sys.dont_write_bytecode = old_dont_write_bytecode
        if mirror_root.exists():
            if (
                mirror_root.parent != mirror_parent
                or not mirror_root.name.startswith(".iteration008-verified-mirror-")
            ):
                raise RuntimeError("refusing to remove an unverified mirror path")
            shutil.rmtree(mirror_root)


def _validate_json_self_hash(
    value: Mapping[str, Any], expected_self_hash: str, *, label: str
) -> None:
    row = dict(value)
    actual_self_hash = _strict_sha256(row.pop("receipt_sha256", None), label=f"{label} self-hash")
    if actual_self_hash != expected_self_hash:
        raise ValueError(f"{label} pinned self-hash mismatch")
    if canonical_sha256(row) != actual_self_hash:
        raise ValueError(f"{label} canonical self-hash mismatch")


def _resolve_fixed_path(root: Path, relative: str, *, label: str) -> Path:
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"{label} is not a safe repository-relative path")
    migration_roots = {
        "analysis_outputs": ("_local_generated", "analysis_outputs"),
        "experiments": ("research", "experiments"),
        "rl_ptcg": ("research", "rl_ptcg"),
        "tools": ("infrastructure", "tools"),
    }
    if pure.parts and pure.parts[0] in migration_roots:
        pure = PurePosixPath(*migration_roots[pure.parts[0]], *pure.parts[1:])
    candidate = (root / Path(*pure.parts)).resolve(strict=True)
    try:
        candidate.relative_to(root.resolve(strict=True))
    except ValueError as error:
        raise ValueError(f"{label} escapes the repository") from error
    return candidate


def _validate_fixed_inputs(
    plan: Mapping[str, Any], root: Path
) -> dict[str, Any]:
    fixed = plan["fixed_inputs"]
    json_specs = (
        ("manifest_path", "manifest_sha256", "manifest"),
        ("prepare_receipt_path", "prepare_receipt_file_sha256", "prepare receipt"),
        (
            "iteration007_execution_spec_path",
            "iteration007_execution_spec_sha256",
            "iteration007 execution spec",
        ),
        ("iteration007_receipt_path", "iteration007_receipt_file_sha256", "iteration007 receipt"),
    )
    loaded_json: dict[str, Any] = {}
    resolved_paths: dict[str, Path] = {}
    guarded_input_buffers: dict[str, bytes] = {}
    for path_key, hash_key, label in json_specs:
        path = _resolve_fixed_path(root, str(fixed[path_key]), label=label)
        resolved_paths[path_key] = path
        value, payload = _load_hashed_json_with_payload(
            path, str(fixed[hash_key]), label=label
        )
        loaded_json[path_key] = value
        guarded_input_buffers[str(fixed[path_key])] = payload
    binary_specs = (
        ("iteration004_checkpoint_path", "iteration004_checkpoint_sha256", "iteration004 checkpoint"),
        ("iteration007_checkpoint_path", "iteration007_checkpoint_sha256", "iteration007 checkpoint"),
    )
    for path_key, hash_key, label in binary_specs:
        path = _resolve_fixed_path(root, str(fixed[path_key]), label=label)
        resolved_paths[path_key] = path
        payload = _read_regular_nonlink_bytes(path, label=label)
        if hashlib.sha256(payload).hexdigest().upper() != fixed[hash_key]:
            raise ValueError(f"{label} SHA-256 mismatch")
        guarded_input_buffers[str(fixed[path_key])] = payload
    prepare = loaded_json["prepare_receipt_path"]
    rejected = loaded_json["iteration007_receipt_path"]
    _validate_json_self_hash(
        prepare, str(fixed["prepare_receipt_sha256"]), label="prepare receipt"
    )
    _validate_json_self_hash(
        rejected, str(fixed["iteration007_receipt_sha256"]), label="iteration007 receipt"
    )
    execution_spec = loaded_json["iteration007_execution_spec_path"]
    expected_bindings = {
        "input_checkpoint_sha256": fixed["iteration004_checkpoint_sha256"],
        "manifest_sha256": fixed["manifest_sha256"],
        "dataset_sha256": fixed["dataset_sha256"],
        "prepare_receipt_sha256": fixed["prepare_receipt_sha256"],
        "fixed_advantages_sha256": fixed["fixed_advantages_sha256"],
        "fixed_behavior_logprobabilities_sha256": fixed[
            "fixed_behavior_logprobabilities_sha256"
        ],
    }
    for key, expected in expected_bindings.items():
        if execution_spec.get(key) != expected:
            raise ValueError(f"iteration007 execution spec {key} mismatch")
    rejected_bindings = {
        **expected_bindings,
        "output_checkpoint_sha256": fixed["iteration007_checkpoint_sha256"],
        "execution_spec_sha256": fixed["iteration007_execution_spec_sha256"],
    }
    for key, expected in rejected_bindings.items():
        if rejected.get(key) != expected:
            raise ValueError(f"iteration007 receipt {key} mismatch")
    if rejected.get("status") != "rejected" or rejected.get("accepted_marker_written") is not False:
        raise ValueError("iteration007 receipt is not the immutable rejection")
    manifest = loaded_json["manifest_path"]
    if manifest.get("dataset_sha256") != fixed["dataset_sha256"]:
        raise ValueError("manifest dataset identity mismatch")
    if manifest.get("checkpoint_sha256") != fixed["iteration004_checkpoint_sha256"]:
        raise ValueError("manifest checkpoint identity mismatch")
    candidate_root = _resolve_fixed_path(
        root, str(fixed["candidate_implementation_path"]), label="candidate implementation"
    )
    if not candidate_root.is_dir():
        raise ValueError("candidate implementation path is not a directory")
    resolved_paths["candidate_implementation_path"] = candidate_root
    snapshot, candidate_source_buffers = implementation_snapshot_with_buffers(candidate_root)
    if snapshot["sha256"] != fixed["candidate_implementation_snapshot_sha256"]:
        raise ValueError("clean-room candidate snapshot SHA-256 mismatch")
    episode_receipts = manifest.get("episode_receipts")
    if not isinstance(episode_receipts, list) or len(episode_receipts) != EXPECTED_TRAJECTORIES:
        raise ValueError("manifest source trajectory count mismatch")
    episode_root = resolved_paths["manifest_path"].parent
    rollout_root_relative = episode_root.relative_to(root.resolve(strict=True)).as_posix()
    rollout_tree_snapshot, rollout_tree_buffers = exact_guarded_tree_snapshot_with_buffers(
        episode_root
    )
    manifest_tree_relative = resolved_paths["manifest_path"].relative_to(
        episode_root
    ).as_posix()
    if rollout_tree_buffers.get(manifest_tree_relative) != guarded_input_buffers[
        str(fixed["manifest_path"])
    ]:
        raise ValueError("guarded rollout-tree manifest bytes changed during validation")
    for relative, payload in rollout_tree_buffers.items():
        repository_relative = (
            PurePosixPath(rollout_root_relative) / PurePosixPath(relative)
        ).as_posix()
        existing = guarded_input_buffers.get(repository_relative)
        if existing is not None and existing != payload:
            raise ValueError("guarded input path has inconsistent retained bytes")
        guarded_input_buffers[repository_relative] = payload
    trajectory_records: list[dict[str, Any]] = []
    episode_ids: set[str] = set()
    for receipt in episode_receipts:
        if not isinstance(receipt, Mapping):
            raise ValueError("source trajectory receipt must be an object")
        relative = PurePosixPath(str(receipt.get("path")))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("source trajectory path is unsafe")
        expected_hash = _strict_sha256(receipt.get("sha256"), label="source trajectory hash")
        if relative.as_posix() not in rollout_tree_buffers:
            raise ValueError("source trajectory is absent from guarded rollout closure")
        payload = rollout_tree_buffers[relative.as_posix()]
        actual_hash = hashlib.sha256(payload).hexdigest().upper()
        if actual_hash != expected_hash or len(payload) != int(receipt.get("bytes", -1)):
            raise ValueError("source trajectory file identity mismatch")
        episode_id = str(receipt.get("episode_id"))
        if episode_id in episode_ids:
            raise ValueError("duplicate source trajectory episode_id")
        episode_ids.add(episode_id)
        trajectory_records.append(
            {
                "episode_id": episode_id,
                "path": relative.as_posix(),
                "bytes": len(payload),
                "sha256": actual_hash,
            }
        )
    return {
        "paths": resolved_paths,
        "manifest": manifest,
        "prepare_receipt": prepare,
        "execution_spec": execution_spec,
        "iteration007_receipt": rejected,
        "candidate_snapshot": snapshot,
        "candidate_source_buffers": candidate_source_buffers,
        "guarded_input_buffers": guarded_input_buffers,
        "guarded_rollout_root_relative": rollout_root_relative,
        "guarded_rollout_tree_snapshot": rollout_tree_snapshot,
        "source_trajectories": trajectory_records,
    }


def _canonical_selected_actions(decision: Mapping[str, Any]) -> dict[str, Any]:
    options = decision.get("legal_semantic_options") or []
    selected = decision.get("final_action") or []
    by_engine_index = {int(option["engine_index"]): option for option in options}
    values: list[dict[str, Any]] = []
    identities: list[str] = []
    for raw_index in selected:
        index = int(raw_index)
        option: Mapping[str, Any] | None = None
        if 0 <= index < len(options):
            option = options[index]
        if index in by_engine_index:
            engine_option = by_engine_index[index]
            if option is not None and engine_option != option:
                raise ValueError("selected action index/engine-index binding is ambiguous")
            option = engine_option
        if option is None:
            raise ValueError("selected public action is not on the legal semantic surface")
        canonical = canonical_semantic_action(option)
        values.append(canonical["value"])
        identities.append(canonical["sha256"])
    encoded = canonical_json_bytes(values)
    return {
        "semantic_identities": identities,
        "canonical_json_bytes_hex": encoded.hex().upper(),
        "sha256": hashlib.sha256(encoded).hexdigest().upper(),
    }


def public_history_by_decision(episode: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
    # Temporal context uses the immediate recorded decision stream.  The output
    # is consumed only for PPO rows, but protected rows and canonical empty or
    # multi-action sequences are legitimate prior public history.
    decisions = list(episode.get("decisions") or [])
    result: dict[int, dict[str, Any]] = {}
    for index, decision in enumerate(decisions):
        current_index = int(decision["decision_index"])
        history: dict[str, Any] = {}
        for lag in (1, 2):
            previous_index = index - lag
            if previous_index < 0:
                history[f"previous_action_{lag}"] = {"available": False}
                history[f"previous_public_state_delta_{lag}"] = {"available": False}
                continue
            previous = decisions[previous_index]
            action = _canonical_selected_actions(previous)
            if lag == 1:
                before, after = previous["public_projection"], decision["public_projection"]
            else:
                before, after = previous["public_projection"], decisions[index - lag + 1]["public_projection"]
            differences = atomic_public_diff(before, after)
            history[f"previous_action_{lag}"] = {"available": True, **action}
            history[f"previous_public_state_delta_{lag}"] = {
                "available": True,
                "from_decision_index": int(previous["decision_index"]),
                "to_decision_index": int(decisions[index - lag + 1]["decision_index"]),
                "atomic_differences": differences,
                "canonical_sha256": canonical_sha256(differences),
            }
        result[current_index] = history
    return result


def _near_public_and_legal_pairs(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[tuple[int, str, int], tuple[int, str, int]], dict[str, Any]] = {}

    def pair_entry(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
        left_key, right_key = row_id_key(left), row_id_key(right)
        if right_key < left_key:
            left, right = right, left
            left_key, right_key = right_key, left_key
        key = (left_key, right_key)
        return merged.setdefault(
            key,
            {
                "left_row_id": row_id_value(left),
                "right_row_id": row_id_value(right),
                "relations": [],
                "normalized_signs": [
                    robust_sign(float(left["normalized_training_advantage_float32"])),
                    robust_sign(float(right["normalized_training_advantage_float32"])),
                ],
            },
        )

    public_groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        public_groups[(str(row["L_sha256"]), str(row["a_sha256"]))].append(row)
    for members in public_groups.values():
        ordered = sorted(members, key=row_id_key)
        for left_index, left in enumerate(ordered):
            for right in ordered[left_index + 1:]:
                differences = atomic_public_diff(left["P_value"], right["P_value"])
                if differences and len(differences) <= 2 and all(diff["one_unit"] for diff in differences):
                    entry = pair_entry(left, right)
                    if len(differences) == 1:
                        entry["relations"].append("public_one_unit")
                    entry["relations"].append("public_two_units")
                    entry["public_atomic_differences"] = differences
    legal_groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        legal_groups[(str(row["P_sha256"]), str(row["a_sha256"]))].append(row)
    for members in legal_groups.values():
        ordered = sorted(members, key=row_id_key)
        for left_index, left in enumerate(ordered):
            for right in ordered[left_index + 1:]:
                difference = multiset_symmetric_difference(
                    left["L_identities"], right["L_identities"]
                )
                if difference["size"] in (1, 2):
                    entry = pair_entry(left, right)
                    entry["relations"].append("legal_multiset_one_or_two")
                    entry["legal_multiset_symmetric_difference"] = difference
    output = []
    for key in sorted(merged):
        entry = merged[key]
        entry["relations"] = sorted(set(entry["relations"]))
        output.append(entry)
    return output


def _nested_row_id_key(value: Mapping[str, Any]) -> tuple[int, str, int]:
    return (
        int(value["ppo_row_ordinal"]),
        str(value["episode_id"]),
        int(value["decision_index"]),
    )


def merge_near_neighbor_pairs(
    pair_groups: Sequence[Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    merged: dict[
        tuple[tuple[int, str, int], tuple[int, str, int]], dict[str, Any]
    ] = {}
    for group in pair_groups:
        for raw_pair in group:
            pair = _json_domain_copy(raw_pair)
            left = _nested_row_id_key(pair["left_row_id"])
            right = _nested_row_id_key(pair["right_row_id"])
            if left == right:
                raise ValueError("near-neighbor self pair is forbidden")
            if right < left:
                left, right = right, left
                pair["left_row_id"], pair["right_row_id"] = (
                    pair["right_row_id"], pair["left_row_id"]
                )
                if "normalized_signs" in pair:
                    pair["normalized_signs"] = list(reversed(pair["normalized_signs"]))
            key = (left, right)
            if key not in merged:
                pair["relations"] = sorted(set(pair.get("relations") or []))
                merged[key] = pair
                continue
            current = merged[key]
            if current.get("normalized_signs") != pair.get("normalized_signs"):
                raise ValueError("duplicate near pair has inconsistent target signs")
            current["relations"] = sorted(
                set(current.get("relations") or []) | set(pair.get("relations") or [])
            )
            for name, value in pair.items():
                if name in {
                    "left_row_id", "right_row_id", "relations", "normalized_signs"
                }:
                    continue
                if name in current and current[name] != value:
                    raise ValueError(f"duplicate near pair field disagrees: {name}")
                current[name] = value
    return [merged[key] for key in sorted(merged)]


def _sign_counts(rows: Sequence[Mapping[str, Any]], field: str) -> dict[str, int]:
    signs = [robust_sign(float(row[field])) for row in rows]
    return {name: signs.count(name) for name in ("positive", "negative", "neutral")}


def _unit_balance(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    weights = [float(row["loss_weight"]) for row in rows]
    ess = effective_sample_size(weights)
    return {
        "row_count": len(rows),
        "positive_negative_neutral_counts": {
            "raw_gae": _sign_counts(rows, "raw_gae_float64"),
            "normalized_training_advantage": _sign_counts(
                rows, "normalized_training_advantage_float32"
            ),
            "monte_carlo_advantage": _sign_counts(rows, "monte_carlo_advantage"),
        },
        "loss_weight_sum": math.fsum(weights),
        "effective_sample_size": ess,
        "row_weight_effective_sample_size": ess,
    }


def _equal_unit_weights(
    rows: Sequence[Mapping[str, Any]], *, unit_field: str
) -> list[float]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        totals[str(row[unit_field])] += float(row["loss_weight"])
    weights: list[float] = []
    for row in rows:
        total = totals[str(row[unit_field])]
        weights.append(0.0 if total == 0.0 else float(row["loss_weight"]) / total)
    return weights


def group_balance_statistics(
    rows: Sequence[Mapping[str, Any]],
    *,
    trajectory_universe: Sequence[str] | None = None,
) -> dict[str, Any]:
    base = _unit_balance(rows)
    observed = {str(row["episode_id"]) for row in rows}
    universe = sorted(
        set(str(value) for value in trajectory_universe)
        if trajectory_universe is not None
        else observed
    )
    if not observed.issubset(universe):
        raise ValueError("balance trajectory universe omits an observed trajectory")
    trajectory_weights: dict[str, float] = {trajectory: 0.0 for trajectory in universe}
    for row in rows:
        trajectory_weights[str(row["episode_id"])] += float(row["loss_weight"])
    values = [float(row["stage32_oriented_probability_delta"]) for row in rows]
    loss_weights = [float(row["loss_weight"]) for row in rows]
    equal_state = _equal_unit_weights(rows, unit_field="P_sha256")
    equal_trajectory = _equal_unit_weights(rows, unit_field="episode_id")
    trajectory_ess = effective_sample_size(list(trajectory_weights.values()))
    return {
        **base,
        "trajectory_count": len(universe),
        "nominal_trajectory_count": len(universe),
        "nonzero_trajectory_count": sum(weight > 0.0 for weight in trajectory_weights.values()),
        "effective_trajectory_sample_size": trajectory_ess,
        "trajectory_weight_effective_sample_size": trajectory_ess,
        "trajectory_ESS_input_count_including_zero_weights": len(universe),
        "trajectory_loss_weights_including_zeros": [
            {
                "episode_id": trajectory,
                "loss_weight": trajectory_weights[trajectory],
                "nonzero": trajectory_weights[trajectory] > 0.0,
            }
            for trajectory in universe
        ],
        "top_10_percent_trajectory_count": max(1, math.ceil(len(universe) * 0.1)),
        "top_10_percent_trajectory_weight_share": top_fraction_weight_share(
            list(trajectory_weights.values()), fraction=0.1
        ),
        "ordinary_loss_weighted_target_median": weighted_median(values, loss_weights),
        "equal_state_weighted_target_median": weighted_median(values, equal_state),
        "equal_trajectory_weighted_target_median": weighted_median(values, equal_trajectory),
        "leave_one_trajectory_out_target_range": leave_one_trajectory_out_range(
            rows,
            value_field="stage32_oriented_probability_delta",
            weight_field="loss_weight",
            trajectory_universe=universe,
        ),
    }


def _aggregate_signed_gradient(
    model: torch.nn.Module,
    members: Sequence[Mapping[str, Any]],
    *,
    distribution_function: Callable[..., tuple[torch.Tensor, torch.Tensor]],
    reference_config: Any,
) -> tuple[dict[str, Any], torch.Tensor]:
    named = dict(model.named_parameters())
    if any(name not in named for name in GRADIENT_PARAMETER_NAMES):
        raise ValueError("gradient parameter universe mismatch")
    parameters = [named[name] for name in GRADIENT_PARAMETER_NAMES]
    policy_terms: list[torch.Tensor] = []
    probability_terms: list[torch.Tensor] = []
    ratios: list[float] = []
    clipped_rows: list[dict[str, Any]] = []
    ratio_records: list[dict[str, Any]] = []
    total_weight = math.fsum(float(row["loss_weight"]) for row in members)
    if not members or total_weight == 0.0:
        raise ValueError("signed gradient group is empty or weightless")
    for member in members:
        source = member["_source_row"]
        state = torch.tensor(source["state_vector"], dtype=torch.float32, device="cpu")
        actions = torch.tensor(source["action_vectors"], dtype=torch.float32, device="cpu")
        residuals, _ = model(state, actions)
        probabilities, log_probabilities = distribution_function(
            residuals,
            teacher_index=int(source["teacher_action"][0]),
            reference_config=reference_config,
        )
        selected = int(source["final_action"][0])
        advantage = float(member["normalized_training_advantage_float32"])
        fixed_behavior_logprob = float(member["behavior_logprob_float64"])
        old_logprob = torch.tensor(fixed_behavior_logprob, dtype=torch.float32)
        advantage_tensor = torch.tensor(advantage, dtype=torch.float32)
        ratio = torch.exp(log_probabilities[selected] - old_logprob)
        ascent_term, clipped_active = clipped_ppo_ascent_term(
            ratio, advantage_tensor, clip_ratio=0.1
        )
        policy_terms.append(ascent_term / EXPECTED_ROWS)
        ratio_value = float(ratio.detach().cpu())
        current_logprob_value = float(log_probabilities[selected].detach().cpu())
        ratios.append(ratio_value)
        if clipped_active:
            clipped_rows.append(row_id_value(member))
        clamped_ratio_value = min(1.1, max(0.9, ratio_value))
        ratio_records.append(
            {
                "row_id": row_id_value(member),
                "fixed_behavior_logprob_float64": fixed_behavior_logprob,
                "fixed_behavior_logprob_tensor_float32": float(old_logprob),
                "current_selected_logprob_float32": current_logprob_value,
                "PPO_ratio_float32": ratio_value,
                "normalized_advantage_float32": advantage,
                "unclipped_ascent_term_float32": ratio_value * advantage,
                "clipped_ascent_term_float32": clamped_ratio_value * advantage,
                "selected_min_ascent_term_float32": float(ascent_term.detach().cpu()),
                "clipped_active": clipped_active,
            }
        )
        probability_terms.append(
            probabilities[selected] * (1.0 if advantage > 0.0 else -1.0) / len(members)
        )
    policy_objective = torch.stack(policy_terms).sum()
    probability_objective = torch.stack(probability_terms).sum()
    policy_gradients = torch.autograd.grad(
        policy_objective, parameters, retain_graph=True, allow_unused=True
    )
    probability_gradients = torch.autograd.grad(
        probability_objective, parameters, retain_graph=False, allow_unused=True
    )
    policy_vector = _flatten_optional_gradients(policy_gradients, parameters)
    probability_vector = _flatten_optional_gradients(probability_gradients, parameters)
    if not torch.isfinite(policy_vector).all() or not torch.isfinite(probability_vector).all():
        raise ValueError("group gradient contains a non-finite value")
    return (
        {
            "row_count": len(members),
            "loss_weight_sum": total_weight,
            "full_batch_denominator": EXPECTED_ROWS,
            "clip_ratio": 0.1,
            "fixed_behavior_logprobabilities_used": True,
            "PPO_ratio": {
                "minimum": min(ratios),
                "maximum": max(ratios),
                "mean": math.fsum(ratios) / len(ratios),
            },
            "clipped_active_row_count": len(clipped_rows),
            "clipped_active_row_ids": clipped_rows,
            "per_row_PPO_ratio_and_clip_activity": ratio_records,
            "signed_clipped_PPO_policy_ascent_gradient_norm": float(
                torch.linalg.vector_norm(policy_vector)
            ),
            "oriented_probability_jacobian_norm": float(
                torch.linalg.vector_norm(probability_vector)
            ),
            "parameter_names": list(GRADIENT_PARAMETER_NAMES),
        },
        policy_vector,
    )


def _parameter_vector(model: torch.nn.Module) -> torch.Tensor:
    named = dict(model.named_parameters())
    return torch.cat(
        [named[name].detach().cpu().reshape(-1) for name in GRADIENT_PARAMETER_NAMES]
    ).to(dtype=torch.float64)


def _parameter_hashes(model: torch.nn.Module) -> dict[str, str]:
    return {
        name: hashlib.sha256(tensor_bytes(parameter)).hexdigest().upper()
        for name, parameter in model.named_parameters()
    }


def _canonical_probability_metric(metric: Mapping[str, Any], *, ordinal: int) -> list[float]:
    if int(metric.get("ppo_row_ordinal", -1)) != ordinal:
        raise ValueError("stored probability metric ordinal mismatch")
    probabilities = torch.tensor(metric["probabilities_float32"], dtype=torch.float32)
    payload = tensor_bytes(probabilities)
    if payload.hex().upper() != metric.get("probabilities_raw_bytes_hex"):
        raise ValueError("stored probability metric raw bytes mismatch")
    if hashlib.sha256(payload).hexdigest().upper() != metric.get("probabilities_byte_sha256"):
        raise ValueError("stored probability metric hash mismatch")
    return [float(value) for value in probabilities.tolist()]


def _verify_model_metrics(
    model: torch.nn.Module,
    rows: Sequence[Mapping[str, Any]],
    metrics: Sequence[Mapping[str, Any]],
    *,
    distribution_function: Callable[..., tuple[torch.Tensor, torch.Tensor]],
    reference_config: Any,
    label: str,
) -> None:
    if len(rows) != EXPECTED_ROWS or len(metrics) != EXPECTED_ROWS:
        raise ValueError(f"{label} probability metric row count mismatch")
    with torch.no_grad():
        for ordinal, (row, metric) in enumerate(zip(rows, metrics)):
            expected = _canonical_probability_metric(metric, ordinal=ordinal)
            source = row["_source_row"]
            state = torch.tensor(source["state_vector"], dtype=torch.float32, device="cpu")
            actions = torch.tensor(source["action_vectors"], dtype=torch.float32, device="cpu")
            residuals, value = model(state, actions)
            probabilities, _ = distribution_function(
                residuals,
                teacher_index=int(source["teacher_action"][0]),
                reference_config=reference_config,
            )
            if tensor_bytes(probabilities) != bytes.fromhex(metric["probabilities_raw_bytes_hex"]):
                raise ValueError(f"{label} model probability bytes mismatch at row {ordinal}")
            if float(value) != float(metric["value_float32"]):
                raise ValueError(f"{label} model value mismatch at row {ordinal}")
            if expected[int(source["final_action"][0])] - float(
                row["initial_sampled_probability_float32"]
            ) != float(metric["sampled_probability_delta_from_initial"]):
                raise ValueError(f"{label} stored sampled probability delta mismatch")


def _group_summary(
    name: str, members: Sequence[Mapping[str, Any]], *, priority: bool = False
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "group": name,
        "priority": priority,
        **_unit_balance(members),
    }
    for stage in ("stage1", "update16", "stage32"):
        values = [float(row[f"{stage}_oriented_probability_delta"]) for row in members]
        result[stage] = {
            "lower_empirical_median": lower_empirical_median(values),
            "mean": math.fsum(values) / len(values),
            "favorable_rows": sum(value > FAMILY_TAU for value in values),
            "anti_or_neutral_rows": sum(value <= FAMILY_TAU for value in values),
        }
    return result


def _end_control_summary(
    name: str, members: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    result = _group_summary(name, members)
    result["END_metric_definition"] = (
        "END probability change from immutable iteration004, oriented by the "
        "normalized training-advantage sign; teacher-argmax preservation is "
        "reported separately."
    )
    for stage in ("stage1", "update16", "stage32"):
        raw = [float(row[f"{stage}_END_probability_delta"]) for row in members]
        oriented = [
            value
            * (
                1.0
                if float(row["normalized_training_advantage_float32"]) > 0.0
                else -1.0
            )
            for row, value in zip(members, raw)
        ]
        result[f"{stage}_END"] = {
            "raw_lower_empirical_median": lower_empirical_median(raw),
            "oriented_lower_empirical_median": lower_empirical_median(oriented),
            "raw_mean": math.fsum(raw) / len(raw),
            "teacher_unique_argmax_count": sum(
                bool(row[f"{stage}_teacher_unique_argmax"]) for row in members
            ),
        }
    return result


def _collision_row_ordinals(
    level: Mapping[str, Any], *, domain: str, strong: bool = False
) -> set[int]:
    key = "strong_cross_trajectory_conflict" if strong else "exact_conflict"
    result: set[int] = set()
    for collision in level["classes"]:
        if collision["domains"][domain][key]:
            result.update(int(row["ppo_row_ordinal"]) for row in collision["row_ids"])
    return result


def _weighted_row_evidence(
    rows: Sequence[Mapping[str, Any]], ordinals: Iterable[int]
) -> dict[str, Any]:
    selected = sorted(set(int(value) for value in ordinals))
    by_ordinal = {int(row["ppo_row_ordinal"]): row for row in rows}
    if any(ordinal not in by_ordinal for ordinal in selected):
        raise ValueError("weighted row evidence references an unknown ordinal")
    return {
        "row_count": len(selected),
        "ppo_row_ordinals": selected,
        "row_ids": [row_id_value(by_ordinal[ordinal]) for ordinal in selected],
        "loss_weight_sum": math.fsum(
            float(by_ordinal[ordinal]["loss_weight"]) for ordinal in selected
        ),
    }


def _safe_fraction(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0.0 else numerator / denominator


def _build_internal_rows(
    *,
    loaded: Mapping[str, Any],
    prepare: Mapping[str, Any],
    rejected: Mapping[str, Any],
    initial_model: torch.nn.Module,
    clean_room: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    loaded_rows = list(loaded["rows"])
    episodes = list(loaded["dataset"].episodes)
    prepare_rows = list(prepare.get("rows") or [])
    if len(loaded_rows) != EXPECTED_ROWS or len(prepare_rows) != EXPECTED_ROWS:
        raise ValueError("PPO row count mismatch before audit row construction")
    if len(episodes) != EXPECTED_TRAJECTORIES:
        raise ValueError("source trajectory count mismatch after checked load")
    episode_ids = [str(episode["episode_id"]) for episode in episodes]
    if len(set(episode_ids)) != EXPECTED_TRAJECTORIES:
        raise ValueError("source trajectory episode IDs are not unique")
    expected_ordinals = list(range(EXPECTED_ROWS))
    if [int(row.get("ppo_row_ordinal", -1)) for row in prepare_rows] != expected_ordinals:
        raise ValueError("prepare receipt PPO ordinals are not exactly 0..829")

    clean_gae = clean_room.inherited._gae(episodes, clean_room.TWO_STAGE_PPO_CONFIG)
    decomposition_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    history_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for episode in episodes:
        eligible = [
            row for row in (episode.get("decisions") or []) if row.get("ppo_eligible")
        ]
        decomposed = gae_decomposition_for_episode(eligible)
        if len(decomposed) != len(eligible):
            raise AssertionError("GAE decomposition lost a trajectory row")
        history = public_history_by_decision(episode)
        for source, evidence in zip(eligible, decomposed):
            key = (str(episode["episode_id"]), int(source["decision_index"]))
            decomposition_by_key[key] = evidence
            history_by_key[key] = history[int(source["decision_index"])]
    if len(decomposition_by_key) != EXPECTED_ROWS:
        raise ValueError("GAE decomposition does not contain exactly 830 unique rows")

    ordered_raw: list[float] = []
    for ordinal, ((episode, source), pinned) in enumerate(zip(loaded_rows, prepare_rows)):
        key = (str(episode["episode_id"]), int(source["decision_index"]))
        if (
            pinned["ppo_row_ordinal"] != ordinal
            or pinned["episode_id"] != key[0]
            or int(pinned["decision_index"]) != key[1]
        ):
            raise ValueError("prepare row identity differs from checked manifest order")
        if key not in clean_gae or key not in decomposition_by_key:
            raise ValueError("checked GAE row identity is missing")
        raw, value_target = clean_gae[key]
        decomposition = decomposition_by_key[key]
        if raw != decomposition["raw_gae"]:
            raise ValueError("independent GAE decomposition differs byte-for-number")
        if raw != float(pinned["raw_advantage_float64"]):
            raise ValueError("raw GAE differs from the prepare receipt")
        if value_target != float(pinned["fixed_value_target_float64"]):
            raise ValueError("fixed value target differs from the prepare receipt")
        if float(source["value"]) != float(pinned["initial_value_float32"]):
            raise ValueError("initial value differs from the prepare receipt")
        if float32_bytes(float(source["value"])).hex().upper() != pinned[
            "initial_value_raw_bytes_hex"
        ]:
            raise ValueError("initial value raw bytes differ from the prepare receipt")
        ordered_raw.append(raw)
    normalized = normalize_advantages_float32(ordered_raw)
    normalized_values = normalized["normalized_values_float32"]
    for ordinal, (actual, pinned) in enumerate(zip(normalized_values, prepare_rows)):
        expected = float(pinned["fixed_normalized_advantage_float32"])
        if float32_bytes(actual) != float32_bytes(expected):
            raise ValueError(f"normalized training advantage bytes differ at row {ordinal}")
    if canonical_sha256(normalized_values) != PINNED_FIXED_INPUTS["fixed_advantages_sha256"]:
        raise ValueError("fixed normalized advantage canonical identity mismatch")
    logprobabilities = [float(row["behavior_logprob_float64"]) for row in prepare_rows]
    if canonical_sha256(logprobabilities) != PINNED_FIXED_INPUTS[
        "fixed_behavior_logprobabilities_sha256"
    ]:
        raise ValueError("fixed behavior log-probability canonical identity mismatch")

    training = rejected.get("training")
    if not isinstance(training, Mapping):
        raise ValueError("iteration007 training diagnostics are absent")
    stage1_metrics = list(training.get("stage_1_metrics") or [])
    full = training.get("stage_2_full_diagnostics")
    if not isinstance(full, Mapping):
        raise ValueError("iteration007 full diagnostics are absent")
    update16_metrics = list(full.get("16") or [])
    stage32_metrics = list(full.get("32") or [])
    if any(len(metrics) != EXPECTED_ROWS for metrics in (stage1_metrics, update16_metrics, stage32_metrics)):
        raise ValueError("stored probability diagnostic row count mismatch")

    family_name_by_type = {
        int(family["option_type"]): str(family["name"])
        for family in prepare["action_families"]["families"]
    }
    internal_rows: list[dict[str, Any]] = []
    gae_rows: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, int]] = set()
    for ordinal, (((episode, source), pinned), normalized_value) in enumerate(
        zip(zip(loaded_rows, prepare_rows), normalized_values)
    ):
        key = (str(episode["episode_id"]), int(source["decision_index"]))
        if key in seen_keys:
            raise ValueError("duplicate episode/decision key during audit construction")
        seen_keys.add(key)
        if int(source["final_action"][0]) != int(pinned["sampled_index"]):
            raise ValueError("sampled index differs from prepare receipt")
        public = canonical_public_projection(source["public_projection"])
        if public["sha256"].lower() != str(pinned["public_state_sha256"]).lower():
            raise ValueError("canonical P differs from the checked public-state hash")
        legal = canonical_legal_multiset(source["legal_semantic_options"])
        sampled_index = int(pinned["sampled_index"])
        action = canonical_semantic_action(source["legal_semantic_options"][sampled_index])
        if action["sha256"].lower() != str(pinned["sampled_semantic_identity"]).lower():
            raise ValueError("canonical selected action differs from prepare receipt")
        latent = selected_frozen_latent(initial_model, source, sampled_index=sampled_index)
        raw_observation = _strict_sha256(
            str(source["raw_observation_sha256"]).upper(), label="opaque O hash"
        )
        if raw_observation.lower() != str(pinned["raw_observation_sha256"]).lower():
            raise ValueError("opaque O hash differs from prepare receipt")
        history = history_by_key[key]
        temporal_value = {
            "previous_action_1_sha256": history["previous_action_1"].get("sha256"),
            "previous_action_2_sha256": history["previous_action_2"].get("sha256"),
            "previous_public_state_delta_1_sha256": history[
                "previous_public_state_delta_1"
            ].get("canonical_sha256"),
            "previous_public_state_delta_2_sha256": history[
                "previous_public_state_delta_2"
            ].get("canonical_sha256"),
        }
        decomposition = decomposition_by_key[key]
        monte_carlo = float(decomposition["monte_carlo_advantage"])
        family_name = family_name_by_type[int(pinned["sampled_option_type"])]
        polarity = "positive" if normalized_value > 0.0 else "negative"
        family_polarity = f"{family_name}:{polarity}"
        initial_probabilities = torch.tensor(
            pinned["initial_probabilities_float32"], dtype=torch.float32
        )
        initial_sampled = float(initial_probabilities[sampled_index])
        end_index = int(pinned["end_index"])
        initial_end = float(initial_probabilities[end_index])
        movement: dict[str, float] = {}
        end_movement: dict[str, float] = {}
        teacher_argmax: dict[str, bool] = {}
        for stage_name, metric in (
            ("stage1", stage1_metrics[ordinal]),
            ("update16", update16_metrics[ordinal]),
            ("stage32", stage32_metrics[ordinal]),
        ):
            probabilities = _canonical_probability_metric(metric, ordinal=ordinal)
            if (
                int(metric["sampled_index"]) != sampled_index
                or str(metric["sampled_semantic_identity"]).lower()
                != action["sha256"].lower()
                or str(metric["public_state_sha256"]).lower() != public["sha256"].lower()
            ):
                raise ValueError(f"{stage_name} probability diagnostic row binding mismatch")
            delta = probabilities[sampled_index] - initial_sampled
            if delta != float(metric["sampled_probability_delta_from_initial"]):
                raise ValueError(f"{stage_name} sampled movement differs from stored metric")
            movement[stage_name] = delta * (1.0 if normalized_value > 0.0 else -1.0)
            end_movement[stage_name] = probabilities[end_index] - initial_end
            teacher_argmax[stage_name] = int(metric["unique_argmax_index"]) == int(
                pinned["teacher_index"]
            )
        row = {
            "ppo_row_ordinal": ordinal,
            "episode_id": key[0],
            "decision_index": key[1],
            "opponent_id": str(episode["opponent_id"]),
            "seat": int(episode["seat"]),
            "seed": int(episode["seed"]),
            "P_sha256": public["sha256"],
            "P_value": public["value"],
            "P_canonical_json_bytes_hex": public["canonical_json_bytes_hex"],
            "P_byte_count": public["byte_count"],
            "O_sha256": raw_observation,
            "O_raw_bytes_persisted": False,
            "L_sha256": legal["sha256"],
            "L_identities": legal["sorted_semantic_identities"],
            "L_canonical_json_bytes_hex": legal["canonical_json_bytes_hex"],
            "L_byte_count": legal["byte_count"],
            "a_sha256": action["sha256"],
            "a_value": action["value"],
            "a_canonical_json_bytes_hex": action["canonical_json_bytes_hex"],
            "a_byte_count": action["byte_count"],
            "X_sha256": latent["sha256"],
            "X_values_float32": latent["values_float32"],
            "X_raw_bytes_hex": latent["raw_bytes_hex"],
            "X_byte_count": latent["byte_count"],
            "X_shape": latent["shape"],
            "raw_gae_float64": float(decomposition["raw_gae"]),
            "normalized_training_advantage_float32": normalized_value,
            "monte_carlo_advantage": monte_carlo,
            "loss_weight": abs(normalized_value),
            "behavior_logprob_float64": float(pinned["behavior_logprob_float64"]),
            "raw_sign": robust_sign(float(decomposition["raw_gae"])),
            "normalized_sign": robust_sign(normalized_value),
            "monte_carlo_sign": robust_sign(monte_carlo),
            "family": family_name,
            "family_polarity": family_polarity,
            "priority_group": family_polarity in PRIORITY_GROUPS,
            "sampled_index": sampled_index,
            "sampled_option_type": int(pinned["sampled_option_type"]),
            "teacher_index": int(pinned["teacher_index"]),
            "end_index": end_index,
            "initial_sampled_probability_float32": initial_sampled,
            "initial_END_probability_float32": initial_end,
            "stage1_oriented_probability_delta": movement["stage1"],
            "update16_oriented_probability_delta": movement["update16"],
            "stage32_oriented_probability_delta": movement["stage32"],
            "stage1_END_probability_delta": end_movement["stage1"],
            "update16_END_probability_delta": end_movement["update16"],
            "stage32_END_probability_delta": end_movement["stage32"],
            "stage1_teacher_unique_argmax": teacher_argmax["stage1"],
            "update16_teacher_unique_argmax": teacher_argmax["update16"],
            "stage32_teacher_unique_argmax": teacher_argmax["stage32"],
            "temporal_history_sha256": canonical_sha256(temporal_value),
            "temporal_history": history,
            "_source_row": source,
        }
        internal_rows.append(row)
        gae_rows.append(
            {
                "ppo_row_ordinal": ordinal,
                "episode_id": key[0],
                **decomposition,
                "raw_gae_float64_raw_bytes_hex": tensor_bytes(
                    torch.tensor(decomposition["raw_gae"], dtype=torch.float64)
                ).hex().upper(),
                "fixed_value_target_float64": float(pinned["fixed_value_target_float64"]),
                "fixed_value_target_float64_raw_bytes_hex": tensor_bytes(
                    torch.tensor(
                        float(pinned["fixed_value_target_float64"]), dtype=torch.float64
                    )
                ).hex().upper(),
                "normalization_mean_float32": normalized["mean_float32"],
                "normalization_population_sd_float32": normalized[
                    "population_sd_float32"
                ],
                "normalized_training_advantage_float32": normalized_value,
                "normalized_training_advantage_float32_raw_bytes_hex": float32_bytes(
                    normalized_value
                ).hex().upper(),
                "previous_one_and_two_public_actions": {
                    "lag_1": history["previous_action_1"],
                    "lag_2": history["previous_action_2"],
                },
                "previous_one_and_two_public_state_deltas": {
                    "lag_1": history["previous_public_state_delta_1"],
                    "lag_2": history["previous_public_state_delta_2"],
                },
                "prepare_target_exact_validation": {
                    "raw_gae_float64_equal": True,
                    "fixed_value_target_float64_equal": True,
                    "normalized_training_advantage_float32_bytes_equal": True,
                    "initial_value_float32_bytes_equal": True,
                },
            }
        )
    if len(internal_rows) != EXPECTED_ROWS or len(seen_keys) != EXPECTED_ROWS:
        raise ValueError("audit rows are incomplete or non-unique")
    if [row["ppo_row_ordinal"] for row in gae_rows] != expected_ordinals:
        raise ValueError("GAE output ordinals are not exactly 0..829")
    identities = {
        "raw_gae_float64_values_canonical_sha256": canonical_sha256(ordered_raw),
        "normalized_training_advantage_float32_values_canonical_sha256": canonical_sha256(
            normalized_values
        ),
        "normalized_training_advantage_raw_bytes_sha256": hashlib.sha256(
            normalized["normalized_raw_bytes"]
        ).hexdigest().upper(),
        "fixed_behavior_logprobabilities_canonical_sha256": canonical_sha256(logprobabilities),
        "normalization_mean_float32": normalized["mean_float32"],
        "normalization_population_sd_float32": normalized["population_sd_float32"],
    }
    return internal_rows, gae_rows, identities


def _public_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {key: _json_domain_copy(value) for key, value in row.items() if not key.startswith("_")}
        for row in rows
    ]


def _build_exact_and_temporal(
    rows: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    key_functions: dict[str, Callable[[Mapping[str, Any]], Any]] = {
        "P": lambda row: row["P_sha256"],
        "P+L": lambda row: [row["P_sha256"], row["L_sha256"]],
        "P+L+a": lambda row: [row["P_sha256"], row["L_sha256"], row["a_sha256"]],
        "O+L+a": lambda row: [row["O_sha256"], row["L_sha256"], row["a_sha256"]],
        "X+L+a": lambda row: [row["X_sha256"], row["L_sha256"], row["a_sha256"]],
    }
    levels = {
        level: analyze_collision_level(rows, level=level, key_function=key_functions[level])
        for level in EXACT_LEVELS
    }
    augmented = analyze_collision_level(
        rows,
        level="O+L+a+prior_two_recorded_actions_and_public_deltas",
        key_function=lambda row: [
            row["O_sha256"], row["L_sha256"], row["a_sha256"],
            row["temporal_history_sha256"],
        ],
    )
    base = levels["O+L+a"]
    base_mass = float(base["domain_totals"]["normalized_training_advantage"][
        "weighted_irreducible_wrong_sign_mass"
    ])
    augmented_mass = float(augmented["domain_totals"]["normalized_training_advantage"][
        "weighted_irreducible_wrong_sign_mass"
    ])
    base_conflict = _collision_row_ordinals(
        base, domain="normalized_training_advantage"
    )
    augmented_conflict = _collision_row_ordinals(
        augmented, domain="normalized_training_advantage"
    )
    covered = base_conflict - augmented_conflict
    priority_covered = {
        int(row["ppo_row_ordinal"])
        for row in rows
        if int(row["ppo_row_ordinal"]) in covered and row["priority_group"]
    }
    failed_groups = sorted({
        str(row["family_polarity"])
        for row in rows
        if int(row["ppo_row_ordinal"]) in priority_covered
    })
    temporal = {
        "history_convention": (
            "The prior one/two actions and public-state transition diffs use the "
            "immediately preceding recorded decisions in the same source trajectory, "
            "including protected and empty or multi-action decisions."
        ),
        "augmented_collision_level": augmented,
        "baseline_weighted_irreducible_mass": base_mass,
        "augmented_weighted_irreducible_mass": augmented_mass,
        "reduction_fraction": _safe_fraction(max(0.0, base_mass - augmented_mass), base_mass),
        "baseline_conflict_rows": _weighted_row_evidence(rows, base_conflict),
        "augmented_conflict_rows": _weighted_row_evidence(rows, augmented_conflict),
        "resolved_rows": _weighted_row_evidence(rows, covered),
        "priority_rows_covered": _weighted_row_evidence(rows, priority_covered),
        "failed_priority_groups_covered": failed_groups,
    }
    exact = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "identity_levels": levels,
        "O_to_X_collapses": analyze_o_to_x_collapses(rows),
        "temporal_augmentation": temporal,
    }
    return exact, temporal


def _build_near_neighbors(rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    public_and_legal = _near_public_and_legal_pairs(rows)
    latent = mad_scaled_mutual_knn(rows, neighbors_per_row=5, retain_fraction=0.01)
    latent_pairs = [
        {**pair, "relations": ["latent_mutual_5nn_lowest_nonzero_1_percent"]}
        for pair in latent["pairs"]
    ]
    pair_rows = merge_near_neighbor_pairs([public_and_legal, latent_pairs])
    agreeing = [
        pair
        for pair in pair_rows
        if pair["normalized_signs"][0] == pair["normalized_signs"][1]
    ]
    evidence = {
        "MAD_scaled_latent_contract": {key: value for key, value in latent.items() if key != "pairs"},
        "target_agreement": {
            "unique_emitted_pair_count_denominator": len(pair_rows),
            "agreeing_pair_count_numerator": len(agreeing),
            "fraction": None if not pair_rows else len(agreeing) / len(pair_rows),
            "all_unique_emitted_pairs": [
                {
                    "left_row_id": pair["left_row_id"],
                    "right_row_id": pair["right_row_id"],
                    "normalized_signs": pair["normalized_signs"],
                    "relations": pair["relations"],
                }
                for pair in pair_rows
            ],
        },
    }
    return pair_rows, evidence


def _build_group_and_balance(
    rows: Sequence[Mapping[str, Any]], prepare: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    by_group: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    by_state: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    by_trajectory: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_group[str(row["family_polarity"])].append(row)
        by_state[str(row["P_sha256"])].append(row)
        by_trajectory[str(row["episode_id"])].append(row)
    trajectory_universe = sorted(by_trajectory)
    if len(trajectory_universe) != EXPECTED_TRAJECTORIES:
        raise ValueError("balance requires the fixed 32-trajectory universe")
    family_groups = [
        _group_summary(group, by_group[group], priority=group in PRIORITY_GROUPS)
        for group in sorted(by_group)
    ]
    directional = prepare["directional_memberships"]
    by_ordinal = {int(row["ppo_row_ordinal"]): row for row in rows}

    def selected(name: str) -> list[Mapping[str, Any]]:
        ordinals = [int(value) for value in directional[name]]
        return [by_ordinal[ordinal] for ordinal in ordinals]

    controls = [
        _end_control_summary(
            "END:positive_normalized_teacher_and_sampled",
            selected("positive_normalized_teacher_and_sampled_end_ordinals"),
        ),
        _end_control_summary("END:negative_target_controls", selected("negative_target_ordinals")),
        _end_control_summary("END:teacher_controls", selected("teacher_end_ordinals")),
    ]
    if [control["row_count"] for control in controls] != [20, 4, 43]:
        raise ValueError("END control population mismatch")
    group_output = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "priority_groups": list(PRIORITY_GROUPS),
        "family_polarity_groups": family_groups,
        "END_controls": controls,
        "movement_definition": (
            "sign(normalized_training_advantage_float32) multiplied by the sampled "
            "probability change from immutable iteration004"
        ),
    }
    per_group_balance = {
        group: group_balance_statistics(
            members, trajectory_universe=trajectory_universe
        )
        for group, members in sorted(by_group.items())
    }
    per_state_balance = [
        {
            "P_sha256": identity,
            **group_balance_statistics(
                members, trajectory_universe=trajectory_universe
            ),
        }
        for identity, members in sorted(by_state.items())
    ]
    per_trajectory_balance = [
        {
            "episode_id": identity,
            **group_balance_statistics(
                members, trajectory_universe=trajectory_universe
            ),
        }
        for identity, members in sorted(by_trajectory.items())
    ]
    imbalance_passes: list[str] = []
    family_summary_by_name = {row["group"]: row for row in family_groups}
    for group in PRIORITY_GROUPS:
        statistics = per_group_balance[group]
        summary = family_summary_by_name[group]
        failed = summary["stage32"]["lower_empirical_median"] <= FAMILY_TAU
        reverses = (
            statistics["equal_state_weighted_target_median"] is not None
            and statistics["equal_state_weighted_target_median"] > FAMILY_TAU
            and statistics["equal_trajectory_weighted_target_median"] is not None
            and statistics["equal_trajectory_weighted_target_median"] > FAMILY_TAU
        )
        concentrated = (
            statistics["trajectory_weight_effective_sample_size"]
            <= 0.5 * statistics["trajectory_count"]
            or statistics["top_10_percent_trajectory_weight_share"] >= 0.5
        )
        statistics["dataset_imbalance_threshold_evidence"] = {
            "failed_original_direction": failed,
            "reverses_under_equal_state_and_equal_trajectory": reverses,
            "trajectory_concentration_condition": concentrated,
            "passes": failed and reverses and concentrated,
        }
        if failed and reverses and concentrated:
            imbalance_passes.append(group)
    balance_output = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "weight_definition": "absolute normalized training advantage",
        "fixed_trajectory_universe": trajectory_universe,
        "global": group_balance_statistics(
            rows, trajectory_universe=trajectory_universe
        ),
        "exact_public_state": per_state_balance,
        "source_trajectory": per_trajectory_balance,
        "family_polarity": per_group_balance,
        "dataset_imbalance_passing_groups": imbalance_passes,
    }
    return group_output, balance_output, imbalance_passes


def _build_gradient_projection(
    *,
    rows: Sequence[Mapping[str, Any]],
    loaded: Mapping[str, Any],
    rejected: Mapping[str, Any],
    terminal_checkpoint_path: Path,
    clean_room: Any,
) -> tuple[dict[str, Any], bool]:
    initial_model = loaded["model"]
    initial_hashes_before = _parameter_hashes(initial_model)
    terminal_model, _, serialized_optimizer_state = clean_room.inherited.load_checkpoint(
        terminal_checkpoint_path,
        expected_source_hashes=loaded["source_hashes"],
        device="cpu",
    )
    terminal_hashes_before = _parameter_hashes(terminal_model)
    stage1 = type(initial_model)(initial_model.config).to("cpu")
    stage1_state = copy.deepcopy(initial_model.state_dict())
    terminal_state = terminal_model.state_dict()
    for name in ("residual_head.2.weight", "residual_head.2.bias"):
        stage1_state[name] = terminal_state[name].detach().clone()
    stage1.load_state_dict(stage1_state, strict=True)
    stage1.eval()
    terminal_model.eval()
    training = rejected["training"]
    stage1_metrics = training["stage_1_metrics"]
    stage32_metrics = training["stage_2_full_diagnostics"]["32"]
    _verify_model_metrics(
        stage1,
        rows,
        stage1_metrics,
        distribution_function=clean_room._torch_behavior_distribution,
        reference_config=loaded["reference_config"],
        label="Stage1",
    )
    _verify_model_metrics(
        terminal_model,
        rows,
        stage32_metrics,
        distribution_function=clean_room._torch_behavior_distribution,
        reference_config=loaded["reference_config"],
        label="Stage32",
    )
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row["family_polarity"])].append(row)
    stage_records: dict[str, dict[str, Any]] = {"stage1": {}, "stage32": {}}
    vectors: dict[str, dict[str, torch.Tensor]] = {"stage1": {}, "stage32": {}}
    for stage_name, model in (("stage1", stage1), ("stage32", terminal_model)):
        for group in sorted(groups):
            record, vector = _aggregate_signed_gradient(
                model,
                groups[group],
                distribution_function=clean_room._torch_behavior_distribution,
                reference_config=loaded["reference_config"],
            )
            stage_records[stage_name][group] = record
            vectors[stage_name][group] = vector
    cosine_records: dict[str, list[dict[str, Any]]] = {}
    for stage_name in ("stage1", "stage32"):
        names = sorted(vectors[stage_name])
        cosine_records[stage_name] = [
            {
                "left_group": left,
                "right_group": right,
                "cosine": vector_cosine(
                    vectors[stage_name][left], vectors[stage_name][right]
                ),
            }
            for left_index, left in enumerate(names)
            for right in names[left_index + 1:]
        ]
    parameter_delta = _parameter_vector(terminal_model) - _parameter_vector(stage1)
    projections = {
        group: gradient_delta_projection(vector, parameter_delta)
        for group, vector in sorted(vectors["stage1"].items())
    }
    probability_projection = {
        group: {
            stage: {
                "lower_empirical_median": lower_empirical_median(
                    [float(row[f"{stage}_oriented_probability_delta"]) for row in members]
                ),
                "mean": math.fsum(
                    float(row[f"{stage}_oriented_probability_delta"]) for row in members
                ) / len(members),
            }
            for stage in ("stage1", "update16", "stage32")
        }
        for group, members in sorted(groups.items())
    }
    all_priority_favorable = all(
        projections[group]["favorable_ascent_projection"] for group in PRIORITY_GROUPS
    )
    if _parameter_hashes(initial_model) != initial_hashes_before:
        raise ValueError("gradient audit changed the immutable iteration004 model")
    if _parameter_hashes(terminal_model) != terminal_hashes_before:
        raise ValueError("gradient audit changed the immutable terminal model")
    output = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "objective": (
            "For each family-polarity group, sum its exact clipped PPO policy-ascent "
            "terms min(ratio*advantage,clamp(ratio,0.9,1.1)*advantage) using each "
            "fixed behavior log-probability, divide by the common full-batch denominator "
            "830, and differentiate in residual_head.0 space. Positive dot product "
            "with the Stage1-to-Stage32 delta is a favorable ascent projection."
        ),
        "common_parameter_space": {
            "parameter_names": list(GRADIENT_PARAMETER_NAMES),
            "reason": (
                "Only residual_head.0 is common to the Stage2 trainable space and has "
                "a persisted Stage1-to-Stage32 parameter delta."
            ),
            "parameter_count": int(parameter_delta.numel()),
            "stage1_to_stage32_delta_norm": float(torch.linalg.vector_norm(parameter_delta)),
        },
        "per_group_signed_gradient_norm_stage1": stage_records["stage1"],
        "per_group_signed_gradient_norm_stage32": stage_records["stage32"],
        "pairwise_group_gradient_cosines_stage1": cosine_records["stage1"],
        "pairwise_group_gradient_cosines_stage32": cosine_records["stage32"],
        "stage1_to_stage32_parameter_delta_projection": projections,
        "stored_probability_space_projection_stage1_update16_update32": probability_projection,
        "update16_parameter_evidence": {
            "available": False,
            "reason": "No update16 parameter bytes were persisted; optimizer replay is forbidden.",
            "stored_probability_rows_used": EXPECTED_ROWS,
        },
        "serialized_optimizer_state": {
            "present_in_terminal_checkpoint": serialized_optimizer_state is not None,
            "applied_or_replayed": False,
        },
        "all_six_priority_group_delta_projections_favorable": all_priority_favorable,
        "optimizer_constructed": False,
        "optimizer_steps": 0,
        "input_parameter_hashes_unchanged": True,
    }
    return output, all_priority_favorable


def _build_cause_evidence(
    *,
    rows: Sequence[Mapping[str, Any]],
    exact: Mapping[str, Any],
    temporal: Mapping[str, Any],
    near_evidence: Mapping[str, Any],
    balance: Mapping[str, Any],
    imbalance_passes: Sequence[str],
    all_priority_derivatives_favorable: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    collapse = exact["O_to_X_collapses"]
    representation_fraction = collapse["threshold_fraction"]
    value_credit = analyze_value_credit_attribution(rows)
    credit_fraction = value_credit["credited_fraction"]

    comparable_gae_mc = [
        row for row in rows if row["raw_sign"] != "neutral" and row["monte_carlo_sign"] != "neutral"
    ]
    agreeing_gae_mc = [
        row for row in comparable_gae_mc if row["raw_sign"] == row["monte_carlo_sign"]
    ]
    gae_mc_agreement = (
        None if not comparable_gae_mc else len(agreeing_gae_mc) / len(comparable_gae_mc)
    )

    def direction(value: float | None) -> str:
        if value is None:
            return "unavailable"
        if value > FAMILY_TAU:
            return "favorable"
        if value < -FAMILY_TAU:
            return "anti"
        return "neutral"

    reweight_records: list[dict[str, Any]] = []
    for group in PRIORITY_GROUPS:
        statistics = balance["family_polarity"][group]
        ordinary = statistics["ordinary_loss_weighted_target_median"]
        equal_state = statistics["equal_state_weighted_target_median"]
        equal_trajectory = statistics["equal_trajectory_weighted_target_median"]
        directions = [direction(ordinary), direction(equal_state), direction(equal_trajectory)]
        reweight_records.append(
            {
                "group": group,
                "ordinary_direction": directions[0],
                "equal_state_direction": directions[1],
                "equal_trajectory_direction": directions[2],
                "preserved": len(set(directions)) == 1,
            }
        )
    reweighting_preserves = all(record["preserved"] for record in reweight_records)
    metrics = {
        "representation_collision_fraction": representation_fraction,
        "temporal_conflict_reduction_fraction": float(temporal["reduction_fraction"]),
        "temporal_priority_rows_covered": int(temporal["priority_rows_covered"]["row_count"]),
        "temporal_failed_groups_covered": len(temporal["failed_priority_groups_covered"]),
        "value_credit_changed_or_resolved_fraction": credit_fraction,
        "dataset_imbalance_group_passes": list(imbalance_passes),
        "near_neighbor_target_agreement": near_evidence["target_agreement"]["fraction"],
        "gae_mc_sign_agreement": gae_mc_agreement,
        "reweighting_preserves_direction": reweighting_preserves,
        "all_six_group_derivatives_favorable": all_priority_derivatives_favorable,
        "intermediate_parameter_evidence_complete": False,
    }
    matrix = classify_causes(metrics)
    evidence = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "metrics": metrics,
        "threshold_evidence": {
            "representation_collision": {
                "per_X_plus_L_plus_a_classes": collapse["classes"],
                "evidentiary_row_ordinals": collapse["evidentiary_rows"],
                "numerator_representation_induced_mass_capped_by_class_priority_anti_or_neutral_weight": collapse[
                    "threshold_numerator_induced_mass_capped_by_priority_weight"
                ],
                "denominator_global_priority_anti_or_neutral_loss_weight": collapse[
                    "threshold_denominator_priority_anti_or_neutral_loss_weight"
                ],
                "fraction": representation_fraction,
                "definition": (
                    "For each (X,L,a), representation-induced mass is max(0, "
                    "min(W+X,W-X)-sum_O min(W+O,W-O)). A class contributes only "
                    "with at least two O identities, at least two episodes per robust "
                    "normalized sign, and positive induced mass; contribution is capped "
                    "by that class's priority anti-or-neutral loss weight."
                ),
            },
            "missing_temporal_information": {
                "baseline_conflict_rows": temporal["baseline_conflict_rows"],
                "resolved_rows": temporal["resolved_rows"],
                "priority_rows_covered": temporal["priority_rows_covered"],
                "failed_groups_covered": temporal["failed_priority_groups_covered"],
                "weighted_irreducible_mass_denominator": temporal[
                    "baseline_weighted_irreducible_mass"
                ],
                "weighted_irreducible_mass_after_augmentation": temporal[
                    "augmented_weighted_irreducible_mass"
                ],
                "reduction_fraction": temporal["reduction_fraction"],
            },
            "value_or_credit_conflict": {
                "per_O_plus_L_plus_a_classes": value_credit["classes"],
                "numerator_changed_or_resolved_irreducible_mass": value_credit[
                    "credited_changed_or_resolved_mass_numerator"
                ],
                "denominator_baseline_normalized_irreducible_mass": value_credit[
                    "baseline_irreducible_mass_denominator"
                ],
                "monte_carlo_irreducible_mass_total": value_credit[
                    "MC_irreducible_mass_total"
                ],
                "fraction": credit_fraction,
                "attribution_definition": (
                    "A Monte-Carlo-resolved class receives at most its baseline "
                    "normalized irreducible mass. A class still in Monte-Carlo conflict "
                    "receives only robust normalized-to-Monte-Carlo sign-flipped row "
                    "weight, capped by that baseline mass. Only the persisted scalar "
                    "reward channel is available."
                ),
            },
            "dataset_imbalance": {
                "passing_groups": list(imbalance_passes),
                "group_evidence": {
                    group: balance["family_polarity"][group][
                        "dataset_imbalance_threshold_evidence"
                    ]
                    for group in PRIORITY_GROUPS
                },
            },
            "mere_optimization_failure": {
                "near_neighbor_agreement": near_evidence["target_agreement"],
                "GAE_MC_comparable_rows_denominator": [
                    row_id_value(row) for row in comparable_gae_mc
                ],
                "GAE_MC_agreeing_rows_numerator": [
                    row_id_value(row) for row in agreeing_gae_mc
                ],
                "GAE_MC_sign_agreement_fraction": gae_mc_agreement,
                "reweighting_direction_records": reweight_records,
                "update16_parameter_evidence_available": False,
            },
        },
        "classifications": matrix,
    }
    return evidence, metrics


def _canonical_artifact_payloads(
    *,
    rows: Sequence[Mapping[str, Any]],
    gae_rows: Sequence[Mapping[str, Any]],
    near_rows: Sequence[Mapping[str, Any]],
    exact: Mapping[str, Any],
    group_comparison: Mapping[str, Any],
    balance: Mapping[str, Any],
    gradient: Mapping[str, Any],
    cause_matrix: Mapping[str, Any],
    summary: Mapping[str, Any],
) -> dict[str, bytes]:
    payloads = {
        "rows.jsonl": canonical_jsonl_bytes(rows),
        "exact_collisions.json": canonical_json_bytes(exact, newline=True),
        "near_neighbors.jsonl": canonical_jsonl_bytes(near_rows),
        "group_end_comparison.json": canonical_json_bytes(group_comparison, newline=True),
        "gae_decomposition.jsonl": canonical_jsonl_bytes(gae_rows),
        "balance.json": canonical_json_bytes(balance, newline=True),
        "gradient_projection.json": canonical_json_bytes(gradient, newline=True),
        "cause_matrix.json": canonical_json_bytes(cause_matrix, newline=True),
        "summary.json": canonical_json_bytes(summary, newline=True),
    }
    if set(payloads) != set(REQUIRED_OUTPUT_FILES) - {"manifest.json"}:
        raise AssertionError("artifact payload inventory is not exact")
    return payloads


def publish_canonical_artifacts(
    output_dir: Path,
    *,
    payloads: Mapping[str, bytes],
    manifest_core: Mapping[str, Any],
    safety_check: Callable[[], None] | None = None,
) -> dict[str, Any]:
    destination = _validate_absent_output_directory(output_dir)
    expected_nonmanifest = set(REQUIRED_OUTPUT_FILES) - {"manifest.json"}
    if set(payloads) != expected_nonmanifest:
        raise ValueError("publication payload inventory mismatch")
    if any(not isinstance(payload, bytes) for payload in payloads.values()):
        raise TypeError("publication payloads must already be canonical bytes")
    output_hashes = {
        name: {
            "bytes": len(payloads[name]),
            "sha256": hashlib.sha256(payloads[name]).hexdigest().upper(),
        }
        for name in sorted(payloads)
    }
    core = {
        **_json_domain_copy(manifest_core),
        "output_files_excluding_manifest": output_hashes,
        "manifest_self_reference_method": (
            "manifest_core_sha256 hashes this object before adding the "
            "manifest_core_sha256 field; manifest.json is intentionally excluded "
            "from output_files_excluding_manifest."
        ),
    }
    manifest = {**core, "manifest_core_sha256": canonical_sha256(core)}
    manifest_payload = canonical_json_bytes(manifest, newline=True)
    all_payloads = {**dict(payloads), "manifest.json": manifest_payload}
    if set(all_payloads) != set(REQUIRED_OUTPUT_FILES):
        raise AssertionError("final audit artifact inventory mismatch")
    if safety_check is not None:
        safety_check()
    staging_path = Path(tempfile.mkdtemp(prefix=f".{destination.name}.staging-", dir=destination.parent))
    published = False
    try:
        if staging_path.parent.resolve() != destination.parent.resolve():
            raise ValueError("private staging directory escaped the output parent")
        for name in REQUIRED_OUTPUT_FILES:
            target = staging_path / name
            with target.open("xb") as stream:
                stream.write(all_payloads[name])
                stream.flush()
                os.fsync(stream.fileno())
        if sorted(path.name for path in staging_path.iterdir()) != sorted(REQUIRED_OUTPUT_FILES):
            raise ValueError("private staging artifact inventory mismatch")
        for name, expected_payload in all_payloads.items():
            if _read_regular_nonlink_bytes(staging_path / name, label=f"staged {name}") != expected_payload:
                raise ValueError(f"staged {name} failed byte verification")
        if destination.exists() or destination.is_symlink():
            raise FileExistsError("audit output directory collided before publication")
        if safety_check is not None:
            safety_check()
        os.replace(staging_path, destination)
        published = True
    finally:
        if not published and staging_path.exists():
            resolved_staging = staging_path.resolve()
            if resolved_staging.parent != destination.parent.resolve() or not resolved_staging.name.startswith(
                f".{destination.name}.staging-"
            ):
                raise RuntimeError("refusing to clean an unverified staging directory")
            shutil.rmtree(resolved_staging)
    return {
        "output_directory": str(destination),
        "required_file_count": len(REQUIRED_OUTPUT_FILES),
        "manifest_file_sha256": hashlib.sha256(manifest_payload).hexdigest().upper(),
        "manifest_core_sha256": manifest["manifest_core_sha256"],
        "games_run": 0,
        "optimizer_steps": 0,
    }


def _compute_read_only_audit(
    *,
    plan: Mapping[str, Any],
    plan_path: Path,
    fixed: Mapping[str, Any],
    root: Path,
    clean_room: Any,
    mirror_receipt: Mapping[str, Any],
    mirrored_paths: Mapping[str, Path],
    mirror_source_root: Path,
    guard: ReadOnlyOperationGuard,
    audit_implementation_snapshot: Mapping[str, Any],
) -> tuple[dict[str, bytes], dict[str, Any]]:
    del plan_path
    runtime = clean_room.inherited._runtime_identity()
    if runtime["required_environment"] != REQUIRED_THREAD_ENVIRONMENT or runtime[
        "observed_thread_counts"
    ] != {"torch_num_threads": 1, "torch_num_interop_threads": 1}:
        raise ValueError("real audit did not establish the required one-thread runtime")
    prepare = fixed["prepare_receipt"]
    clean_room.validate_prepare_receipt(prepare)
    if prepare.get("prepare_proof") != {
        "optimizer_constructed": False,
        "optimizer_steps": 0,
        "checkpoint_written": False,
        "parameters_changed": False,
        "rejected_checkpoint_loaded": False,
        "training_executed": False,
        "runtime_smoke_executed": False,
        "games_run": 0,
    }:
        raise ValueError("prepare receipt read-only proof mismatch")
    loaded = clean_room.inherited._load_validated_inputs()
    if len(loaded["rows"]) != EXPECTED_ROWS:
        raise ValueError("checked clean-room loader did not return exactly 830 rows")
    clean_snapshot = clean_room.inherited.implementation_snapshot(mirror_source_root)
    if clean_snapshot != fixed["candidate_snapshot"]:
        raise ValueError("clean-room snapshot reproduction disagrees with independent snapshot")
    internal_rows, gae_rows, target_identities = _build_internal_rows(
        loaded=loaded,
        prepare=prepare,
        rejected=fixed["iteration007_receipt"],
        initial_model=loaded["model"],
        clean_room=clean_room,
    )
    if [row["ppo_row_ordinal"] for row in internal_rows] != list(range(EXPECTED_ROWS)):
        raise ValueError("audit rows are not exactly ordered 0..829")
    exact, temporal = _build_exact_and_temporal(internal_rows)
    near_rows, near_evidence = _build_near_neighbors(internal_rows)
    group_comparison, balance, imbalance_passes = _build_group_and_balance(
        internal_rows, prepare
    )
    gradient, all_priority_favorable = _build_gradient_projection(
        rows=internal_rows,
        loaded=loaded,
        rejected=fixed["iteration007_receipt"],
        terminal_checkpoint_path=mirrored_paths[
            PINNED_FIXED_INPUTS["iteration007_checkpoint_path"]
        ],
        clean_room=clean_room,
    )
    cause_matrix, cause_metrics = _build_cause_evidence(
        rows=internal_rows,
        exact=exact,
        temporal=temporal,
        near_evidence=near_evidence,
        balance=balance,
        imbalance_passes=imbalance_passes,
        all_priority_derivatives_favorable=all_priority_favorable,
    )
    public_rows = _public_rows(internal_rows)
    if len(public_rows) != EXPECTED_ROWS or len(gae_rows) != EXPECTED_ROWS:
        raise ValueError("row or GAE output completeness mismatch")
    classified = [
        name
        for name, evidence in cause_matrix["classifications"].items()
        if evidence["evidenced"]
    ]
    guard.assert_clean(phase="zero-operation claims before manifest construction")
    if implementation_snapshot(fixed["paths"]["candidate_implementation_path"]) != fixed[
        "candidate_snapshot"
    ]:
        raise RuntimeError("original candidate implementation changed during mirror use")
    summary = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "audit_scope": "read-only identifiability evidence for rejected iteration007",
        "row_count": EXPECTED_ROWS,
        "unique_episode_decision_keys": EXPECTED_ROWS,
        "source_trajectories": EXPECTED_TRAJECTORIES,
        "classified_causes": classified,
        "cause_metrics": cause_metrics,
        "update16_parameter_evidence_available": False,
        "mere_optimization_failure_eligible": False,
        "architecture_or_training_change_selected": False,
        "game_strength_claim_made": False,
        "games_run": 0,
        "optimizer_constructed": False,
        "optimizer_steps": 0,
        "limitations": [
            "The full raw observation was not persisted; O is an opaque exact hash and field-level O differences are unavailable.",
            "Only one persisted scalar reward channel can be decomposed.",
            "No update16 parameter bytes exist; only stored probability-space movement is reported.",
            "Prior-action history uses the immediate two recorded decisions, including protected and empty or multi-action decisions; only current PPO rows are emitted.",
            "The 1% latent-neighbor cutoff uses ceil(0.01*N) and includes all ties at the cutoff.",
            "No architecture, target, optimizer, or training change is selected by this audit.",
        ],
    }
    payloads = _canonical_artifact_payloads(
        rows=public_rows,
        gae_rows=gae_rows,
        near_rows=near_rows,
        exact=exact,
        group_comparison=group_comparison,
        balance=balance,
        gradient=gradient,
        cause_matrix=cause_matrix,
        summary=summary,
    )
    fixed_input_manifest = {
        key: value for key, value in plan["fixed_inputs"].items()
    }
    manifest_core = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "plan": {
            "path": PLAN_RELATIVE_PATH.as_posix(),
            "file_sha256": PLAN_SHA256,
            "canonical_sha256": canonical_sha256(plan),
            "schema_version": plan["schema_version"],
            "plan_id": plan["plan_id"],
        },
        "fixed_inputs": fixed_input_manifest,
        "fixed_input_self_hashes_validated": {
            "prepare_receipt_sha256": prepare["receipt_sha256"],
            "iteration007_receipt_sha256": fixed["iteration007_receipt"]["receipt_sha256"],
        },
        "candidate_implementation_snapshot": fixed["candidate_snapshot"],
        "audit_implementation_snapshot": audit_implementation_snapshot,
        "verified_clean_room_mirror_receipt": mirror_receipt,
        "original_candidate_snapshot_unchanged_before_manifest": True,
        "source_trajectory_files": fixed["source_trajectories"],
        "runtime_thread_receipt": runtime,
        "target_identities": target_identities,
        "row_completeness": {
            "rows_jsonl": EXPECTED_ROWS,
            "gae_decomposition_jsonl": EXPECTED_ROWS,
            "ppo_row_ordinals_exact": [0, EXPECTED_ROWS - 1],
            "ppo_row_ordinals_contiguous_and_unique": True,
            "unique_episode_decision_keys": EXPECTED_ROWS,
            "source_trajectories": EXPECTED_TRAJECTORIES,
        },
        "read_only_proof": {
            "inputs_modified": False,
            "training_or_parameter_mutation": False,
            "optimizer_constructed": False,
            "optimizer_steps": 0,
            "games_or_runtime_smoke": 0,
            "iteration006_checkpoint_loaded": False,
            "network_access": False,
            "external_writes": False,
            "forbidden_operation_attempt_count_measured": guard.attempts,
            "safety_guard_scope": (
                "torch.optim.Optimizer and all discovered optimizer subclass-owned "
                "constructors/steps plus imported known training/game entrypoints"
            ),
        },
        "limitations_and_conventions": summary["limitations"] + [
            "Collision percentages use unique row sets and absolute normalized-advantage loss weights; numerator and denominator row IDs are persisted in cause_matrix.json.",
            "Gradient cosines and Stage1-to-Stage32 projections use only the common residual_head.0 space and exact clipped PPO ascent with fixed behavior log-probabilities, clip 0.1, and common denominator 830.",
            "Latent MAD scaling is global across the 830 selected X vectors; neighbor eligibility remains same L+a.",
            "Equal-state and equal-trajectory medians normalize absolute-advantage weight to unit total within each state or trajectory.",
        ],
        "required_output_files": list(REQUIRED_OUTPUT_FILES),
        "games_run": 0,
        "optimizer_steps": 0,
    }
    return payloads, manifest_core


def execute_read_only_audit(
    *,
    plan: Mapping[str, Any],
    plan_path: Path,
    output_dir: Path,
    guard: ReadOnlyOperationGuard | None = None,
    audit_implementation_snapshot: Mapping[str, Any] | None = None,
    audit_implementation_buffers: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    root = repo_root().resolve(strict=True)
    if guard is None:
        snapshot, buffers = audit_implementation_snapshot_with_buffers(root)
        with ReadOnlyOperationGuard() as owned_guard:
            result = execute_read_only_audit(
                plan=plan,
                plan_path=plan_path,
                output_dir=output_dir,
                guard=owned_guard,
                audit_implementation_snapshot=snapshot,
                audit_implementation_buffers=buffers,
            )
            owned_guard.assert_clean(phase="end of directly invoked audit guard context")
        owned_guard.assert_clean(phase="after directly invoked audit guard context")
        return result
    if audit_implementation_snapshot is None or audit_implementation_buffers is None:
        raise ValueError("guarded audit implementation bytes are required")
    fixed = _validate_fixed_inputs(plan, root)
    mirror_root: Path | None = None
    mirror_receipt: dict[str, Any]
    with verified_clean_room_context(fixed=fixed, root=root, guard=guard) as (
        clean_room,
        raw_mirror_receipt,
        mirrored_paths,
        mirror_source_root,
        mirror_root,
    ):
        mirror_receipt = dict(raw_mirror_receipt)
        payloads, manifest_core = _compute_read_only_audit(
            plan=plan,
            plan_path=plan_path,
            fixed=fixed,
            root=root,
            clean_room=clean_room,
            mirror_receipt=mirror_receipt,
            mirrored_paths=mirrored_paths,
            mirror_source_root=mirror_source_root,
            guard=guard,
            audit_implementation_snapshot=audit_implementation_snapshot,
        )
    if mirror_root is None or mirror_root.exists():
        raise RuntimeError("verified clean-room mirror was not removed after use")
    alias = "_iteration007_identifiability_clean_room_6b95c5b6"
    if any(name == alias or name.startswith(alias + ".") for name in sys.modules):
        raise RuntimeError("private clean-room modules remained after use")
    if implementation_snapshot(fixed["paths"]["candidate_implementation_path"]) != fixed[
        "candidate_snapshot"
    ]:
        raise RuntimeError("original candidate implementation changed after mirror use")
    assert_audit_implementation_unchanged(
        root, audit_implementation_buffers, phase="after mirror context"
    )
    guard.assert_clean(phase="after verified mirror context and before publication")
    mirror_receipt.update(
        {
            "temporary_mirror_removed_before_publication": True,
            "private_alias_modules_removed_before_publication": True,
            "original_candidate_snapshot_unchanged_after_use": True,
        }
    )
    manifest_core["verified_clean_room_mirror_receipt"] = mirror_receipt
    manifest_core["original_candidate_snapshot_unchanged_after_mirror_context"] = True
    manifest_core["read_only_proof"][
        "forbidden_operation_attempt_count_after_mirror_context"
    ] = guard.attempts

    def final_safety_check() -> None:
        guard.assert_clean(phase="canonical publication boundary")
        assert_audit_implementation_unchanged(
            root, audit_implementation_buffers, phase="canonical publication boundary"
        )
        if implementation_snapshot(
            fixed["paths"]["candidate_implementation_path"]
        ) != fixed["candidate_snapshot"]:
            raise RuntimeError("original candidate changed at canonical publication boundary")

    return publish_canonical_artifacts(
        output_dir,
        payloads=payloads,
        manifest_core=manifest_core,
        safety_check=final_safety_check,
    )


def run_audit(*, plan_path: Path, plan_sha256: str, output_dir: Path) -> dict[str, Any]:
    root = repo_root().resolve(strict=True)
    audit_snapshot, audit_buffers = audit_implementation_snapshot_with_buffers(root)
    plan = load_and_validate_plan(plan_path, plan_sha256)
    destination = _validate_absent_output_directory(output_dir)
    candidate_root = _resolve_fixed_path(
        root,
        str(plan["fixed_inputs"]["candidate_implementation_path"]),
        label="candidate implementation",
    )
    try:
        destination.relative_to(candidate_root)
    except ValueError:
        pass
    else:
        raise ValueError("audit output directory must not be inside the immutable candidate")
    with ReadOnlyOperationGuard() as guard:
        result = execute_read_only_audit(
            plan=plan,
            plan_path=plan_path,
            output_dir=destination,
            guard=guard,
            audit_implementation_snapshot=audit_snapshot,
            audit_implementation_buffers=audit_buffers,
        )
        guard.assert_clean(phase="end of audit safety context")
    guard.assert_clean(phase="after audit safety context")
    assert_audit_implementation_unchanged(
        root, audit_buffers, phase="after audit safety context"
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_audit(
        plan_path=args.plan,
        plan_sha256=args.plan_sha256,
        output_dir=args.output_dir,
    )
    print(canonical_json_bytes(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
