"""Iteration-009 matched vanilla/PCGrad actor-only pilot.

The implementation plan authorizes :func:`prepare` only.  Training is exposed
solely behind a separately authored, byte-hashed execution specification.  No
optimizer is constructed at import time or by ``prepare``.

The module deliberately reuses the checked iteration-007 data, Stage-1, model,
measurement, and safety implementation.  Its new policy is limited to the
seven-way mass-preserving partition and deterministic cyclic PCGrad applied to
``residual_head.0`` during Stage 2.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import time
from typing import Any, Mapping, Sequence

import torch

from . import actor_only_interaction_maturation_pilot as base
from . import conservative_ppo_pilot as inherited
from .frozen_sources import sha256_file
from .model import ModelConfig, ResidualActorCritic, load_checkpoint
from .train_ppo import _torch_behavior_anchor_kl, _torch_behavior_distribution


PLAN_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_009_mass_preserving_pcgrad_implementation_plan.json"
)
PLAN_SHA256 = "6797A6D884B7B69D5C78A6BD964ACC8425B64063FA9F201905146E1B2D1FB9B8"
PLAN_SCHEMA_VERSION = "archaludon-rl-mass-preserving-pcgrad-implementation-plan-v1"
PLAN_ID = "phase1-iteration-009-mass-preserving-pcgrad-20260801"

CORRECTION_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_009_mass_preserving_pcgrad_plan_correction_v1.json"
)
CORRECTION_SHA256 = "B08661C5F2905D6316D33066AC72D1A96CECE42EB8FB2C40EA29894E9AF8BB5B"
CORRECTION_SCHEMA_VERSION = (
    "archaludon-rl-mass-preserving-pcgrad-plan-correction-v1"
)
CORRECTION_ID = (
    "phase1-iteration-009-mass-preserving-pcgrad-publication-remediation-20260801"
)
CORRECTION_V2_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_009_mass_preserving_pcgrad_plan_correction_v2.json"
)
CORRECTION_V2_SHA256 = (
    "FAA5975575923F2C3F1CEE2D7DE75698B3F644D47B6112ADF3E517539298BE8E"
)
CORRECTION_V2_SCHEMA_VERSION = (
    "archaludon-rl-mass-preserving-pcgrad-plan-correction-v2"
)
CORRECTION_V2_ID = (
    "phase1-iteration-009-mass-preserving-pcgrad-raw-recomputation-"
    "remediation-20260801"
)
CORRECTION_V3_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_009_mass_preserving_pcgrad_plan_correction_v3.json"
)
CORRECTION_V3_SHA256 = (
    "0E91C620996122E50E2F83DCCDD636EDEF97142AE42FDB3754DD30DE1138ECA4"
)
CORRECTION_V3_SCHEMA_VERSION = (
    "archaludon-rl-mass-preserving-pcgrad-plan-correction-v3"
)
CORRECTION_V3_ID = (
    "phase1-iteration-009-mass-preserving-pcgrad-final-preexecution-"
    "remediation-20260801"
)
CORRECTION_V4_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_009_mass_preserving_pcgrad_plan_correction_v4.json"
)
CORRECTION_V4_SHA256 = (
    "BD9B12F9B8D525398BCED16CFB2730DD64C441B4DD4BDE1D0F38B690CB9FDDAF"
)
CORRECTION_V4_SCHEMA_VERSION = (
    "archaludon-rl-mass-preserving-pcgrad-plan-correction-v4"
)
CORRECTION_V4_ID = (
    "phase1-iteration-009-mass-preserving-pcgrad-noncyclic-test-"
    "remediation-20260801"
)
CORRECTION_V5_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_009_mass_preserving_pcgrad_plan_correction_v5.json"
)
CORRECTION_V5_SHA256 = (
    "57BC4F70DC54473D89D8DEC0D54C724E06603CD0A52E916690F1B320F7253C01"
)
CORRECTION_V5_SCHEMA_VERSION = (
    "archaludon-rl-mass-preserving-pcgrad-plan-correction-v5"
)
CORRECTION_V5_ID = (
    "phase1-iteration-009-legacy-control-gradient-authority-"
    "remediation-20260801"
)

PREDECESSOR_EXECUTION_SPEC_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_009_mass_preserving_pcgrad_execution_spec_v1.json"
)
PREDECESSOR_EXECUTION_SPEC_SHA256 = (
    "F11295F8DB3E4DB7C33D19225D5145EEF1DFBA087F82E67A798851DC7B2987F9"
)
PREDECESSOR_STOP_MANIFEST_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801/"
    "test_outputs/phase1_iteration_009_pending_audit_v1/manifest.json"
)
PREDECESSOR_STOP_MANIFEST_FILE_SHA256 = (
    "2D684F5E9ADDFEB4E0F9A33C83AAE799D909FCED9BFFB32E8AB3A677B01E36C7"
)
PREDECESSOR_STOP_MANIFEST_CORE_SHA256 = (
    "F5E76699DE578E9349C5ABFC9D94D812EEF46C977D0F9ED27B10FCA355E7CF95"
)

IMPLEMENTATION_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl_pcgrad_candidate_20260801"
)
SOURCE_IMPLEMENTATION_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl_interaction_maturation_candidate_20260801"
)
SOURCE_IMPLEMENTATION_FILE_COUNT = 53
SOURCE_IMPLEMENTATION_SHA256 = (
    "6B95C5B6DEB354293E2DC08077DAEC5FE6A77D013832DD70DECC485C91EB87CA"
)

PARENT_RESULT_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl/PHASE1_ITERATION_008_RESULT.md"
)
PARENT_RESULT_SHA256 = "6AAEA02E37D5C9AD91745D4ABCED11ED6CAADE3EC049816903142DFF7ED3B2AA"
AUDIT_PLAN_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_008_identifiability_audit_plan.json"
)
AUDIT_PLAN_SHA256 = "8FAE5B736C4C1E269AC5FCD1EA1D0146EBC35B78BDA6A454AF452D6920D7E701"
AUDIT_EXECUTION_SPEC_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_008_identifiability_audit_execution_spec_v1.json"
)
AUDIT_EXECUTION_SPEC_SHA256 = (
    "55B2F8D928F787C9B99821D556448D5F4761CAE1D46DC3E6861AE7D5ABF9F479"
)
AUDIT_MANIFEST_RELATIVE_PATH = PurePosixPath(
    "analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_007_"
    "identifiability_audit_20260801/manifest.json"
)
AUDIT_MANIFEST_FILE_SHA256 = (
    "537FF791D51A562A8DC2280461E973F4E849539DB069E3E3D1EAFA770D2A5526"
)
AUDIT_MANIFEST_CORE_SHA256 = (
    "0FB981A19C01B068E77210E06E074A94064641DFA8BA758D741CECE82449DF4C"
)

REJECTED_CHECKPOINT_RELATIVE_PATH = PurePosixPath(
    "analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_007_"
    "frozen_readout_interaction_maturation_20260801/candidate.pt"
)
REJECTED_CHECKPOINT_SHA256 = (
    "5547AFD90CF039390CDA8E70E3DA5868C12B0277AA670636573F7BC0FE7715B3"
)
REJECTED_RECEIPT_RELATIVE_PATH = PurePosixPath(
    "analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_007_"
    "frozen_readout_interaction_maturation_20260801/rejected_receipt.json"
)
REJECTED_RECEIPT_FILE_SHA256 = (
    "C2AF5C7BCA142296CAF1407F3FFA498A4FD2E4F71FB7C9E6B68C5D2C2AC0B796"
)
REJECTED_RECEIPT_SELF_SHA256 = (
    "07E8D544F5544779A5488C9072238317FDE238E7BCEE13EE69E9A87B2EBBFC3D"
)

INPUT_CHECKPOINT_RELATIVE_PATH = base.INPUT_CHECKPOINT_RELATIVE_PATH
INPUT_CHECKPOINT_SHA256 = base.INPUT_CHECKPOINT_SHA256
MANIFEST_RELATIVE_PATH = base.MANIFEST_RELATIVE_PATH
MANIFEST_SHA256 = base.MANIFEST_SHA256
DATASET_SHA256 = base.DATASET_SHA256
FIXED_ADVANTAGES_SHA256 = base.FIXED_ADVANTAGES_SHA256
FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256 = (
    base.FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256
)

EXPECTED_ROWS = 830
EXPECTED_TRAJECTORIES = 32
STAGE2_UPDATES = 64
TOTAL_STEPS_PER_ARM = 65
DIAGNOSTIC_UPDATES = (1, 2, 4, 8, 16, 24, 32, 48, 64)
PARAMETER_NAMES = ("residual_head.0.weight", "residual_head.0.bias")
OPTIMIZER_PARAMETER_NAMES = base.OPTIMIZER_PARAMETER_NAMES
TASK_ORDER = (
    "PLAY:positive",
    "ATTACH:negative",
    "EVOLVE:negative",
    "RETREAT:positive",
    "ATTACK:negative",
    "END:positive",
    "REMAINING_ROWS",
)
PRIORITY_TASKS = TASK_ORDER[:-1]
AUDIT_ADVERSE_TASKS = (
    "PLAY:positive",
    "RETREAT:positive",
    "ATTACK:negative",
    "END:positive",
)
OPTION_TYPE_BY_FAMILY = {
    "PLAY": 7,
    "ATTACH": 8,
    "EVOLVE": 9,
    "RETREAT": 12,
    "ATTACK": 13,
    "END": 14,
}
COMMON_DENOMINATOR = 830
MAX_ABSOLUTE_SUM_DIFFERENCE = 5e-10
RELATIVE_L2_SUM_DIFFERENCE = 1e-5
CONTROL_DECOMPOSITION_MAX_ABSOLUTE_ERROR = 2e-11
CONTROL_DECOMPOSITION_RELATIVE_L2_ERROR = 2e-6
CONTROL_DECOMPOSITION_MINIMUM_L2_ERROR = 1e-10
ORIENTATION_DEADBAND = 1e-7
ROBUST_SIGN_EPSILON = 1e-6
GRADIENT_CLIP = 0.25
ANCHOR_KL_COEFFICIENT = 0.1

PREPARE_RECEIPT_SCHEMA_VERSION = "mass-preserving-pcgrad-prepare-v4"
EXECUTION_SPEC_SCHEMA_VERSION = "mass-preserving-pcgrad-execution-spec-v4"
PENDING_MANIFEST_SCHEMA_VERSION = "mass-preserving-pcgrad-pending-manifest-v2"
RUN_SUMMARY_SCHEMA_VERSION = "mass-preserving-pcgrad-run-summary-v2"
FINAL_RECEIPT_SCHEMA_VERSION = "mass-preserving-pcgrad-final-receipt-v2"
NUMERICAL_AUDIT_SCHEMA_VERSION = "mass-preserving-pcgrad-numerical-audit-v2"
ROOT_RECOMPUTATION_SCHEMA_VERSION = "mass-preserving-pcgrad-root-recomputation-v2"
PREPARE_OUTPUT_FILENAME = "pretraining_probe_receipt.json"
TASK_MEMBERSHIP_SCHEMA_VERSION = "mass-preserving-pcgrad-task-membership-v1"
PENDING_FILES = (
    "manifest.json",
    "run_summary.json",
    "stage1_diagnostics.jsonl",
    "milestone_diagnostics.jsonl",
    "step_summaries.jsonl",
    "gradient_tensors.pt",
    "control_pending.pt",
    "treatment_pending.pt",
    "PENDING_AUDIT",
)
PENDING_DIRECTORY_REPLACE_RETRY_DELAYS_SECONDS = (
    0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64,
)
FINAL_ACCEPTED_FILES = (
    "control.pt", "treatment.pt", "accepted_receipt.json", "ACCEPTED"
)
FINAL_REJECTED_FILES = (
    "control.pt", "treatment.pt", "rejected_receipt.json", "REJECTED"
)
RUN_SUMMARY_KEYS_V2 = {
    "schema_version", "status", "caller_summaries_informational_only",
    "execution_spec_path", "execution_spec_sha256", "prepare_receipt_sha256",
    "completed_optimizer_steps_per_arm",
    "completed_synchronized_stage2_updates", "failure", "safety_stop",
    "all_safety_gates_pass", "stage1_equality", "stage1_record_hashes",
    "stage1_complete_evidence", "control_update32_reference", "mechanism",
    "alignment_summaries", "terminal_END_controls",
    "duplicate_treatment_identity",
    "duplicate_treatment_canonical_outputs_identical",
    "checkpoint_reload_evidence", "strict_offline_gates", "evidence",
    "expected_task_order", "expected_diagnostic_updates",
    "stage1_diagnostic_row_count", "milestone_diagnostic_row_count",
    "step_summary_row_count", "games_run", "runtime_smoke_executed",
    "run_summary_sha256",
}
STAGE1_COMPARED_FIELDS = (
    "stage1_record_sha256", "stage1_report", "stage1_safety",
    "stage1_value_identity", "model_parameter_hashes", "model_state_hashes",
    "optimizer_canonical", "output_hashes", "complete_830_diagnostics",
    "losses", "fixed_input_identities",
)

REFERENCE_CONTROL = {
    "stage1_record_sha256": "E4059D36B9B549F290B1652D51654DB7DED5B5906D809FB21517FD21DBDC6177",
    "stage1_ordered_probability_bytes_sha256": (
        "F1CB32B1FC474A940710860E9DDF16D71FB8C35CE726D211794D9544BD064454"
    ),
    "stage32_record_sha256": "58EA0E4F4CD8C3351D922BF0D03C637A1F379402F8DC51EE7453FEC1940C5984",
    "stage32_ordered_probability_bytes_sha256": (
        "BBC78682CCE797D0E1D0A90329643DCC06BC0A356CB4033FB522244F0FE6B832"
    ),
    "ordered_value_bytes_sha256": (
        "3F61B19DAAA108D58E57700E2226BEABDBF551D23AA024CC9EBF14AD7AE131B7"
    ),
    "stage32_parameter_bytes_sha256": {
        "residual_head.0.weight": (
            "7F155F7909959A89CBD1B67F35A35295D20C178AD0590CDD24CF49472895F1B4"
        ),
        "residual_head.0.bias": (
            "8CE0B6702427014004AC58BF10AB47EEA411042F416F11B43455E1B1E88C709F"
        ),
        "residual_head.2.weight": (
            "BC23EAC75269414FC67EEBA9A0B8B0172AEFB59B5C4CB090C97ED1D16748CBF4"
        ),
        "residual_head.2.bias": (
            "CC9EE0D468FA74EBCF8C5934E4A48EB8CE9B538E79A744E4B0B7862329F5F71C"
        ),
    },
    "optimizer_canonical_sha256": (
        "3E3E26BAB7B555590A14CD59D802D21FDB873CBEDB54DDDB481BE9870754598B"
    ),
    "optimizer_param_group_canonical_sha256": (
        "CCD077FF186B2F0855C7D7362B44A22B97FF8C134FDD057B0A5102DC8494E4AA"
    ),
}


def canonical_json_bytes(value: Any, *, newline: bool = False) -> bytes:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return payload + (b"\n" if newline else b"")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest().upper()


def _vector_norm(value: torch.Tensor, ord: float | int = 2.0) -> torch.Tensor:
    vector_norm = getattr(torch.linalg, "vector_norm", None)
    if vector_norm is not None:
        return vector_norm(value, ord)
    return torch.norm(value, p=ord)


def _tensor_bytes_v2(value: torch.Tensor) -> bytes:
    return value.detach().cpu().contiguous().numpy().tobytes(order="C")


def _tensor_sha256_v2(value: torch.Tensor) -> str:
    return hashlib.sha256(_tensor_bytes_v2(value)).hexdigest().upper()


def _nested_byte_exact_v2(left: Any, right: Any) -> bool:
    if torch.is_tensor(left) or torch.is_tensor(right):
        return bool(
            torch.is_tensor(left)
            and torch.is_tensor(right)
            and left.dtype == right.dtype
            and left.shape == right.shape
            and _tensor_bytes_v2(left) == _tensor_bytes_v2(right)
        )
    if isinstance(left, Mapping) or isinstance(right, Mapping):
        return bool(
            isinstance(left, Mapping)
            and isinstance(right, Mapping)
            and tuple(left) == tuple(right)
            and all(_nested_byte_exact_v2(left[key], right[key]) for key in left)
        )
    if isinstance(left, (list, tuple)) or isinstance(right, (list, tuple)):
        return bool(
            type(left) is type(right)
            and len(left) == len(right)
            and all(_nested_byte_exact_v2(a, b) for a, b in zip(left, right))
        )
    return type(left) is type(right) and left == right


def _optimizer_state_mismatch_v4(
    expected: Mapping[str, Any], retained: Any
) -> str:
    """Name the first optimizer-state field that differs byte-for-byte."""

    if not isinstance(retained, Mapping):
        return "root"
    expected_groups = expected.get("param_groups") or ()
    retained_groups = retained.get("param_groups") or ()
    if not _nested_byte_exact_v2(expected_groups, retained_groups):
        return "param_groups"
    expected_state = expected.get("state") or {}
    retained_state = retained.get("state") or {}
    parameter_ids = (
        tuple(expected_groups[0].get("params") or ()) if expected_groups else ()
    )
    for index, name in enumerate(OPTIMIZER_PARAMETER_NAMES):
        parameter_id = parameter_ids[index] if index < len(parameter_ids) else index
        left = expected_state.get(parameter_id)
        right = retained_state.get(parameter_id)
        if not isinstance(left, Mapping) or not isinstance(right, Mapping):
            if not _nested_byte_exact_v2(left, right):
                return f"{name}:state"
            continue
        for field in ("step", "exp_avg", "exp_avg_sq", "max_exp_avg_sq"):
            if field in left or field in right:
                if not _nested_byte_exact_v2(left.get(field), right.get(field)):
                    return f"{name}:{field}"
        if not _nested_byte_exact_v2(left, right):
            return f"{name}:state"
    return "root"


def _step_without_tensor_evidence(step: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(step))
    value.pop("tensor_evidence", None)
    return value


def _compact_without_tensor_evidence(compact: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(compact))
    if isinstance(value.get("step"), Mapping):
        value["step"] = _step_without_tensor_evidence(value["step"])
    return value


def _repo_path(relative: PurePosixPath) -> Path:
    return inherited.find_repo_root(Path(__file__)) / Path(relative.as_posix())


def _strict_sha256(value: Any, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789ABCDEF" for character in value)
    ):
        raise ValueError(f"{label} must be an uppercase SHA-256")
    return value


def _load_hashed_json(path: Path, expected_hash: str, *, label: str) -> dict[str, Any]:
    return inherited._load_hashed_json(path, expected_hash, label=label)


def _file_reference(relative: PurePosixPath, expected_hash: str, *, label: str) -> dict[str, Any]:
    path = _repo_path(relative)
    actual = sha256_file(path)
    if actual != expected_hash:
        raise ValueError(f"{label} hash mismatch")
    return {"path": relative.as_posix(), "sha256": actual}


def _load_plan() -> dict[str, Any]:
    plan = _load_hashed_json(_repo_path(PLAN_RELATIVE_PATH), PLAN_SHA256, label="iteration-009 plan")
    if plan.get("schema_version") != PLAN_SCHEMA_VERSION or plan.get("plan_id") != PLAN_ID:
        raise ValueError("iteration-009 plan identity mismatch")
    immutable = plan.get("immutable_inputs") or {}
    source = immutable.get("source_implementation") or {}
    required = {
        "path": SOURCE_IMPLEMENTATION_RELATIVE_PATH.as_posix(),
        "snapshot_sha256": SOURCE_IMPLEMENTATION_SHA256,
        "snapshot_file_count": SOURCE_IMPLEMENTATION_FILE_COUNT,
        "copy_exclusions": ["__pycache__", "test_outputs", "*.pyc"],
    }
    if source != required:
        raise ValueError("source implementation contract mismatch")
    if immutable.get("on_policy_rows") != EXPECTED_ROWS or immutable.get("source_trajectories") != EXPECTED_TRAJECTORIES:
        raise ValueError("immutable row or trajectory count mismatch")
    if immutable.get("dataset_sha256") != DATASET_SHA256:
        raise ValueError("dataset contract mismatch")
    if immutable.get("fixed_advantages_sha256") != FIXED_ADVANTAGES_SHA256:
        raise ValueError("fixed advantage contract mismatch")
    if immutable.get("fixed_behavior_logprobabilities_sha256") != FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256:
        raise ValueError("fixed behavior log-probability contract mismatch")
    training = plan.get("training_contract") or {}
    treatment = training.get("treatment") or {}
    if tuple(treatment.get("task_order") or ()) != TASK_ORDER:
        raise ValueError("task order contract mismatch")
    if training.get("stage2_common", {}).get("optimizer_steps_per_arm") != STAGE2_UPDATES:
        raise ValueError("Stage-2 update contract mismatch")
    if training.get("ppo_config", {}).get("full_batch_rows") != COMMON_DENOMINATOR:
        raise ValueError("common denominator contract mismatch")
    return plan


def _load_correction() -> dict[str, Any]:
    correction = _load_hashed_json(
        _repo_path(CORRECTION_RELATIVE_PATH),
        CORRECTION_SHA256,
        label="iteration-009 plan correction",
    )
    if (
        correction.get("schema_version") != CORRECTION_SCHEMA_VERSION
        or correction.get("correction_id") != CORRECTION_ID
        or correction.get("base_plan_path") != PLAN_RELATIVE_PATH.as_posix()
        or correction.get("base_plan_sha256") != PLAN_SHA256
    ):
        raise ValueError("iteration-009 correction identity mismatch")
    if correction.get("prepare_contract_correction", {}).get(
        "execution_spec_independent"
    ) is not True:
        raise ValueError("correction does not authorize specification-independent prepare")
    return correction


def _load_correction_v2() -> dict[str, Any]:
    correction = _load_hashed_json(
        _repo_path(CORRECTION_V2_RELATIVE_PATH),
        CORRECTION_V2_SHA256,
        label="iteration-009 raw-recomputation correction",
    )
    if (
        correction.get("schema_version") != CORRECTION_V2_SCHEMA_VERSION
        or correction.get("correction_id") != CORRECTION_V2_ID
        or correction.get("base_plan_path") != PLAN_RELATIVE_PATH.as_posix()
        or correction.get("base_plan_sha256") != PLAN_SHA256
        or correction.get("superseded_correction_path")
        != CORRECTION_RELATIVE_PATH.as_posix()
        or correction.get("superseded_correction_sha256") != CORRECTION_SHA256
    ):
        raise ValueError("iteration-009 v2 correction identity mismatch")
    return correction


def _load_correction_v3() -> dict[str, Any]:
    correction = _load_hashed_json(
        _repo_path(CORRECTION_V3_RELATIVE_PATH), CORRECTION_V3_SHA256,
        label="v3 correction",
    )
    if (
        correction.get("schema_version") != CORRECTION_V3_SCHEMA_VERSION
        or correction.get("correction_id") != CORRECTION_V3_ID
        or correction.get("base_plan_sha256") != PLAN_SHA256
        or correction.get("v1_correction_sha256") != CORRECTION_SHA256
        or correction.get("v2_correction_sha256") != CORRECTION_V2_SHA256
    ):
        raise ValueError("v3 correction identity mismatch")
    return correction


def _load_correction_v4() -> dict[str, Any]:
    correction = _load_hashed_json(
        _repo_path(CORRECTION_V4_RELATIVE_PATH), CORRECTION_V4_SHA256,
        label="v4 correction",
    )
    if (
        correction.get("schema_version") != CORRECTION_V4_SCHEMA_VERSION
        or correction.get("correction_id") != CORRECTION_V4_ID
        or correction.get("base_plan_sha256") != PLAN_SHA256
        or correction.get("v1_correction_sha256") != CORRECTION_SHA256
        or correction.get("v2_correction_sha256") != CORRECTION_V2_SHA256
        or correction.get("v3_correction_sha256") != CORRECTION_V3_SHA256
    ):
        raise ValueError("v4 correction identity mismatch")
    return correction


def _load_correction_v5() -> dict[str, Any]:
    correction = _load_hashed_json(
        _repo_path(CORRECTION_V5_RELATIVE_PATH), CORRECTION_V5_SHA256,
        label="v5 correction",
    )
    expected_prior = (
        (CORRECTION_RELATIVE_PATH.as_posix(), CORRECTION_SHA256),
        (CORRECTION_V2_RELATIVE_PATH.as_posix(), CORRECTION_V2_SHA256),
        (CORRECTION_V3_RELATIVE_PATH.as_posix(), CORRECTION_V3_SHA256),
        (CORRECTION_V4_RELATIVE_PATH.as_posix(), CORRECTION_V4_SHA256),
    )
    actual_prior = tuple(
        (row.get("path"), row.get("sha256"))
        for row in correction.get("prior_corrections") or ()
    )
    predecessor = correction.get("predecessor_execution_stop") or {}
    if (
        correction.get("schema_version") != CORRECTION_V5_SCHEMA_VERSION
        or correction.get("correction_id") != CORRECTION_V5_ID
        or correction.get("base_plan_path") != PLAN_RELATIVE_PATH.as_posix()
        or correction.get("base_plan_sha256") != PLAN_SHA256
        or actual_prior != expected_prior
        or predecessor.get("execution_spec_path")
        != PREDECESSOR_EXECUTION_SPEC_RELATIVE_PATH.as_posix()
        or predecessor.get("execution_spec_sha256")
        != PREDECESSOR_EXECUTION_SPEC_SHA256
        or predecessor.get("manifest_path")
        != PREDECESSOR_STOP_MANIFEST_RELATIVE_PATH.as_posix()
        or predecessor.get("manifest_file_sha256")
        != PREDECESSOR_STOP_MANIFEST_FILE_SHA256
        or predecessor.get("manifest_core_sha256")
        != PREDECESSOR_STOP_MANIFEST_CORE_SHA256
        or predecessor.get("completed_optimizer_steps_per_arm")
        != {"control_vanilla": 1, "treatment_pcgrad": 1}
        or predecessor.get("completed_stage2_updates") != 0
        or predecessor.get("games_run") != 0
        or predecessor.get("disposition")
        != (
            "Retain immutably as fail-closed implementation evidence only. "
            "Never resume, overwrite, delete, finalize, use as a performance "
            "observation, count as a candidate rejection, or use to falsify RL "
            "or PCGrad. A corrected run must restart from iteration004 in new "
            "pending and terminal directories."
        )
    ):
        raise ValueError("v5 correction identity or predecessor stop mismatch")
    manifest = _load_hashed_json(
        _repo_path(PREDECESSOR_STOP_MANIFEST_RELATIVE_PATH),
        PREDECESSOR_STOP_MANIFEST_FILE_SHA256,
        label="predecessor implementation-stop manifest",
    )
    if (
        manifest.get("manifest_core_sha256")
        != PREDECESSOR_STOP_MANIFEST_CORE_SHA256
        or manifest.get("completed_optimizer_steps_per_arm")
        != {"control_vanilla": 1, "treatment_pcgrad": 1}
        or manifest.get("completed_synchronized_stage2_updates") != 0
        or manifest.get("games_run") != 0
        or manifest.get("runtime_smoke_executed") is not False
        or (manifest.get("failure") or {}).get("message")
        != "control post-clip gradient differs from PyTorch contract"
    ):
        raise ValueError("predecessor implementation-stop manifest changed")
    return correction


def cyclic_task_order(update_ordinal: int) -> tuple[str, ...]:
    if isinstance(update_ordinal, bool) or not isinstance(update_ordinal, int) or not 1 <= update_ordinal <= STAGE2_UPDATES:
        raise ValueError("Stage-2 update ordinal must be 1..64")
    offset = (update_ordinal - 1) % len(TASK_ORDER)
    return TASK_ORDER[offset:] + TASK_ORDER[:offset]


def build_task_partition(rows: Sequence[Mapping[str, Any]]) -> dict[str, list[int]]:
    """Build the exact disjoint six-priority-plus-remainder partition."""

    if len(rows) != EXPECTED_ROWS:
        raise ValueError("task partition requires exactly 830 rows")
    result = {name: [] for name in TASK_ORDER}
    priority_lookup = {
        (OPTION_TYPE_BY_FAMILY[name.split(":", 1)[0]], name.split(":", 1)[1]): name
        for name in PRIORITY_TASKS
    }
    for ordinal, row in enumerate(rows):
        if row.get("ppo_row_ordinal") != ordinal:
            raise ValueError("task partition row order mismatch")
        advantage = row.get("fixed_normalized_advantage_float32")
        option_type = row.get("sampled_option_type")
        if (
            isinstance(advantage, bool)
            or not isinstance(advantage, (int, float))
            or not math.isfinite(float(advantage))
            or isinstance(option_type, bool)
            or not isinstance(option_type, int)
        ):
            raise ValueError("task partition row is malformed")
        polarity = "positive" if float(advantage) > 0.0 else "negative"
        task = priority_lookup.get((option_type, polarity), "REMAINING_ROWS")
        result[task].append(ordinal)
    validate_task_partition(result, row_count=len(rows))
    return result


def validate_task_partition(partition: Mapping[str, Sequence[int]], *, row_count: int = EXPECTED_ROWS) -> None:
    if tuple(partition) != TASK_ORDER:
        raise ValueError("task partition key order mismatch")
    flattened: list[int] = []
    for name in TASK_ORDER:
        ordinals = list(partition[name])
        if ordinals != sorted(ordinals) or len(ordinals) != len(set(ordinals)):
            raise ValueError(f"task membership is not sorted and unique: {name}")
        if any(isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < row_count for value in ordinals):
            raise ValueError(f"task membership contains an invalid ordinal: {name}")
        flattened.extend(ordinals)
    if sorted(flattened) != list(range(row_count)) or len(flattened) != row_count:
        raise ValueError("seven tasks must cover each row exactly once")


def task_membership_receipt(partition: Mapping[str, Sequence[int]]) -> dict[str, Any]:
    validate_task_partition(partition)
    tasks = []
    for name in TASK_ORDER:
        core = {
            "schema_version": TASK_MEMBERSHIP_SCHEMA_VERSION,
            "task": name,
            "common_denominator": COMMON_DENOMINATOR,
            "ordinals": list(partition[name]),
        }
        tasks.append({**core, "membership_sha256": canonical_sha256(core)})
    return {
        "schema_version": TASK_MEMBERSHIP_SCHEMA_VERSION,
        "task_order": list(TASK_ORDER),
        "row_count": EXPECTED_ROWS,
        "common_denominator": COMMON_DENOMINATOR,
        "tasks": tasks,
        "all_rows_covered_exactly_once": True,
        "equal_task_weighting": False,
    }


def _flatten_gradient_map(gradients: Mapping[str, torch.Tensor]) -> tuple[torch.Tensor, list[dict[str, Any]]]:
    if tuple(gradients) != PARAMETER_NAMES:
        raise ValueError("gradient parameter order mismatch")
    pieces: list[torch.Tensor] = []
    layout: list[dict[str, Any]] = []
    offset = 0
    for name in PARAMETER_NAMES:
        value = gradients[name]
        if not torch.is_tensor(value) or value.device.type != "cpu" or not value.dtype.is_floating_point:
            raise ValueError("gradient must be a floating CPU tensor")
        if not bool(torch.isfinite(value).all()):
            raise FloatingPointError("nonfinite task gradient")
        count = value.numel()
        pieces.append(value.detach().contiguous().reshape(-1).to(dtype=torch.float64))
        layout.append({
            "name": name,
            "shape": list(value.shape),
            "dtype": str(value.dtype),
            "start": offset,
            "stop": offset + count,
        })
        offset += count
    return torch.cat(pieces), layout


def _unflatten_one_cast(vector: torch.Tensor, layout: Sequence[Mapping[str, Any]]) -> dict[str, torch.Tensor]:
    if vector.device.type != "cpu" or vector.dtype != torch.float64 or not bool(torch.isfinite(vector).all()):
        raise ValueError("projected vector must be finite CPU float64")
    result: dict[str, torch.Tensor] = {}
    for record in layout:
        name = str(record["name"])
        dtype_name = str(record["dtype"]).split(".")[-1]
        dtype = getattr(torch, dtype_name)
        # This is the sole float64->parameter-dtype cast in policy surgery.
        result[name] = vector[int(record["start"]):int(record["stop"])].reshape(tuple(record["shape"])).to(dtype=dtype)
    return result


def validate_unsurgeried_sum(
    task_vectors: Mapping[str, torch.Tensor], direct_vector: torch.Tensor
) -> dict[str, float]:
    if tuple(task_vectors) != TASK_ORDER:
        raise ValueError("unsurgeried task vector order mismatch")
    if direct_vector.dtype != torch.float64 or direct_vector.device.type != "cpu":
        raise ValueError("direct gradient must be CPU float64")
    if not bool(torch.isfinite(direct_vector).all()):
        raise FloatingPointError("direct gradient is nonfinite")
    unsurgeried = torch.zeros_like(direct_vector)
    for name in TASK_ORDER:
        value = task_vectors[name]
        if value.dtype != torch.float64 or value.device.type != "cpu" or value.shape != direct_vector.shape:
            raise ValueError("task vector domain mismatch")
        if not bool(torch.isfinite(value).all()):
            raise FloatingPointError("task gradient is nonfinite")
        unsurgeried = unsurgeried + value
    difference = unsurgeried - direct_vector
    maximum = float(difference.abs().max()) if difference.numel() else 0.0
    difference_norm = float(_vector_norm(difference))
    direct_norm = float(_vector_norm(direct_vector))
    relative = difference_norm / max(direct_norm, torch.finfo(torch.float64).tiny)
    if maximum > MAX_ABSOLUTE_SUM_DIFFERENCE or relative > RELATIVE_L2_SUM_DIFFERENCE:
        raise ValueError("unsurgeried task sum does not reproduce direct full-batch gradient")
    return {
        "maximum_absolute_difference": maximum,
        "relative_l2_difference": relative,
        "difference_l2_norm": difference_norm,
        "direct_l2_norm": direct_norm,
    }


def pcgrad_project(
    task_gradients: Mapping[str, Mapping[str, torch.Tensor]],
    direct_gradient: Mapping[str, torch.Tensor],
    *,
    update_ordinal: int,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    """Apply the plan's exact original-gradient, cyclic, float64 PCGrad."""

    if tuple(task_gradients) != TASK_ORDER:
        raise ValueError("PCGrad task order mismatch")
    direct_vector, layout = _flatten_gradient_map(direct_gradient)
    originals: dict[str, torch.Tensor] = {}
    for task in TASK_ORDER:
        vector, task_layout = _flatten_gradient_map(task_gradients[task])
        if task_layout != layout or vector.shape != direct_vector.shape:
            raise ValueError("task gradient layout mismatch")
        originals[task] = vector
    sum_evidence = validate_unsurgeried_sum(originals, direct_vector)
    order = cyclic_task_order(update_ordinal)
    pairwise: list[dict[str, Any]] = []
    norms = {name: float(_vector_norm(originals[name])) for name in TASK_ORDER}
    dot_matrix: dict[str, dict[str, float]] = {name: {} for name in TASK_ORDER}
    cosine_matrix: dict[str, dict[str, float | None]] = {
        name: {} for name in TASK_ORDER
    }
    for left in TASK_ORDER:
        for right in TASK_ORDER:
            dot = float(torch.dot(originals[left], originals[right]))
            denominator = norms[left] * norms[right]
            dot_matrix[left][right] = dot
            cosine_matrix[left][right] = (
                None if denominator == 0.0 else dot / denominator
            )
    for left_index, left in enumerate(TASK_ORDER):
        for right in TASK_ORDER[left_index + 1:]:
            dot = float(torch.dot(originals[left], originals[right]))
            denominator = norms[left] * norms[right]
            pairwise.append({
                "left": left,
                "right": right,
                "dot": dot,
                "cosine": None if denominator == 0.0 else dot / denominator,
            })
    projected: dict[str, torch.Tensor] = {}
    projection_events: list[dict[str, Any]] = []
    zero_norm_skips: list[dict[str, str]] = []
    for task in order:
        current = originals[task].clone()
        for other in order:
            if other == task:
                continue
            other_gradient = originals[other]  # never use a projected g_j
            squared_norm = float(torch.dot(other_gradient, other_gradient))
            dot = float(torch.dot(current, other_gradient))
            if not math.isfinite(squared_norm) or not math.isfinite(dot):
                raise FloatingPointError("nonfinite PCGrad projection input")
            if squared_norm == 0.0:
                zero_norm_skips.append({"task": task, "other": other})
                continue
            if dot < 0.0:
                coefficient = dot / squared_norm
                before_norm = float(_vector_norm(current))
                current = current - coefficient * other_gradient
                if not bool(torch.isfinite(current).all()):
                    raise FloatingPointError("nonfinite PCGrad projection result")
                projection_events.append({
                    "task": task,
                    "other": other,
                    "dot_before": dot,
                    "other_squared_norm": squared_norm,
                    "coefficient": coefficient,
                    "task_norm_before": before_norm,
                    "task_norm_after": float(_vector_norm(current)),
                })
        projected[task] = current
    combined = torch.zeros_like(direct_vector)
    for task in order:
        combined = combined + projected[task]
    if not bool(torch.isfinite(combined).all()):
        raise FloatingPointError("nonfinite combined PCGrad gradient")
    result = _unflatten_one_cast(combined, layout)
    surgery_delta = combined - direct_vector
    touched = [
        name for name in TASK_ORDER
        if not torch.equal(projected[name], originals[name])
    ]
    diagnostics = {
        "update_ordinal": update_ordinal,
        "projection_numeric_domain": "cpu_float64",
        "float32_cast_count_per_parameter": 1,
        "projection_order": list(order),
        "raw_task_gradient_norms": norms,
        "raw_task_gradients_float64": {
            name: originals[name].tolist() for name in TASK_ORDER
        },
        "pairwise_raw_task_dots_and_cosines": pairwise,
        "pairwise_raw_task_dot_matrix": dot_matrix,
        "pairwise_raw_task_cosine_matrix": cosine_matrix,
        "projection_events": projection_events,
        "zero_norm_skips": zero_norm_skips,
        "projected_task_gradient_norms": {
            name: float(_vector_norm(projected[name])) for name in TASK_ORDER
        },
        "projected_task_gradients_float64": {
            name: projected[name].tolist() for name in TASK_ORDER
        },
        "task_changed_by_surgery": touched,
        "surgery_nonzero": bool(touched),
        "surgery_delta_l2_norm": float(_vector_norm(surgery_delta)),
        "combined_policy_gradient_l2_norm_float64": float(_vector_norm(combined)),
        "combined_policy_gradient_sha256_float64": hashlib.sha256(
            combined.contiguous().numpy().tobytes(order="C")
        ).hexdigest().upper(),
        "unsurgeried_sum": sum_evidence,
    }
    return result, diagnostics


def apply_policy_kl_clip_adam(
    *,
    model: torch.nn.Module,
    optimizer: torch.optim.Adam,
    policy_gradient: Mapping[str, torch.Tensor],
    kl_gradient: Mapping[str, torch.Tensor],
    gradient_clip: float = GRADIENT_CLIP,
) -> dict[str, Any]:
    """Assign policy, add unchanged KL, clip the common gradient, then Adam."""

    named = dict(model.named_parameters())
    if tuple(policy_gradient) != PARAMETER_NAMES or tuple(kl_gradient) != PARAMETER_NAMES:
        raise ValueError("policy/KL gradient order mismatch")
    before = {name: named[name].detach().clone() for name in PARAMETER_NAMES}
    optimizer.zero_grad(set_to_none=True)
    policy_norms: dict[str, float] = {}
    kl_norms: dict[str, float] = {}
    combined_norms: dict[str, float] = {}
    for name in PARAMETER_NAMES:
        policy = policy_gradient[name]
        anchor = kl_gradient[name]
        parameter = named[name]
        if policy.dtype != parameter.dtype or anchor.dtype != parameter.dtype:
            raise ValueError("policy and KL gradients must match parameter dtype")
        if policy.shape != parameter.shape or anchor.shape != parameter.shape:
            raise ValueError("policy and KL gradient shape mismatch")
        if not bool(torch.isfinite(policy).all()) or not bool(torch.isfinite(anchor).all()):
            raise FloatingPointError("nonfinite policy or KL gradient")
        parameter.grad = policy.detach().clone()
        policy_norms[name] = float(_vector_norm(parameter.grad))
        parameter.grad.add_(anchor)  # unchanged KL is added after the one policy cast
        kl_norms[name] = float(_vector_norm(anchor))
        combined_norms[name] = float(_vector_norm(parameter.grad))
    preclip = torch.nn.utils.clip_grad_norm_(
        [named[name] for name in sorted(PARAMETER_NAMES)],
        gradient_clip,
        error_if_nonfinite=True,
    )
    postclip = {
        name: float(_vector_norm(named[name].grad)) for name in PARAMETER_NAMES
    }
    postclip_vector = torch.cat(
        [
            named[name].grad.detach().cpu().contiguous().reshape(-1)
            for name in PARAMETER_NAMES
        ]
    ).to(torch.float32)
    combined_preclip_vector = torch.cat(
        [
            (policy_gradient[name] + kl_gradient[name])
            .detach()
            .cpu()
            .contiguous()
            .reshape(-1)
            for name in PARAMETER_NAMES
        ]
    )
    optimizer.step()
    for value in model.parameters():
        if not bool(torch.isfinite(value).all()):
            raise FloatingPointError("nonfinite parameter after Adam")
    delta = {name: named[name].detach() - before[name] for name in PARAMETER_NAMES}
    return {
        "ordering": ["policy_gradient", "anchor_kl_gradient", "global_norm_clip", "adam_step"],
        "policy_gradient_norms": policy_norms,
        "anchor_kl_gradient_norms": kl_norms,
        "combined_preclip_gradient_norms": combined_norms,
        "combined_preclip_gradient_values_float32": (
            combined_preclip_vector.tolist()
        ),
        "combined_preclip_gradient_sha256_float32": hashlib.sha256(
            combined_preclip_vector.numpy().tobytes(order="C")
        ).hexdigest().upper(),
        "global_gradient_norm_before_clip": float(preclip),
        "combined_postclip_gradient_norms": postclip,
        "combined_postclip_gradient_values_float32": postclip_vector.tolist(),
        "parameter_delta": delta,
    }


def optimizer_canonical_record(
    optimizer: torch.optim.Optimizer, model: torch.nn.Module
) -> dict[str, Any]:
    named = dict(model.named_parameters())
    reverse = {id(parameter): name for name, parameter in named.items()}
    if len(optimizer.param_groups) != 1:
        raise ValueError("optimizer must contain one parameter group")
    group = dict(optimizer.param_groups[0])
    parameters = group.pop("params")
    names = [reverse.get(id(parameter)) for parameter in parameters]
    if tuple(names) != OPTIMIZER_PARAMETER_NAMES:
        raise ValueError("optimizer parameter order mismatch")
    group["params"] = names
    state: dict[str, Any] = {}
    for parameter in parameters:
        name = reverse[id(parameter)]
        values: dict[str, Any] = {}
        for key, value in sorted(optimizer.state.get(parameter, {}).items()):
            if torch.is_tensor(value):
                raw = value.detach().cpu().contiguous().numpy().tobytes(order="C")
                values[key] = {
                    "dtype": str(value.dtype),
                    "shape": list(value.shape),
                    "sha256": hashlib.sha256(raw).hexdigest().upper(),
                }
            else:
                values[key] = value
        if values:
            state[name] = values
    record = {"param_group": group, "state": state}
    return {
        "record": record,
        "canonical_sha256": canonical_sha256(record),
        "param_group_canonical_sha256": canonical_sha256(group),
    }


def optimizer_step_states(optimizer: torch.optim.Optimizer, model: torch.nn.Module) -> dict[str, int]:
    named = dict(model.named_parameters())
    result: dict[str, int] = {}
    for name in OPTIMIZER_PARAMETER_NAMES:
        state = optimizer.state.get(named[name])
        if not state:
            continue
        step = state.get("step")
        value = float(step.detach().cpu()) if torch.is_tensor(step) else float(step)
        if not value.is_integer():
            raise ValueError("optimizer step is not integral")
        result[name] = int(value)
    return result


def validate_stage1_arm_equality(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    required = STAGE1_COMPARED_FIELDS
    failures = [name for name in required if canonical_json_bytes(left.get(name)) != canonical_json_bytes(right.get(name))]
    if failures:
        raise ValueError("Stage-1 arm equality failed: " + ",".join(failures))
    if not _nested_byte_exact_v2(
        left.get("optimizer_state"), right.get("optimizer_state")
    ):
        raise ValueError("Stage-1 arm equality failed: optimizer_state")
    if not _nested_byte_exact_v2(
        left.get("model_state"), right.get("model_state")
    ):
        raise ValueError("Stage-1 arm equality failed: model_state")
    if (
        left.get("stage1_record_sha256") != REFERENCE_CONTROL["stage1_record_sha256"]
        or right.get("stage1_record_sha256")
        != REFERENCE_CONTROL["stage1_record_sha256"]
    ):
        raise ValueError("both Stage-1 records must match the immutable reference")
    if left.get("output_hashes", {}).get("ordered_probability_bytes_sha256") != REFERENCE_CONTROL["stage1_ordered_probability_bytes_sha256"]:
        raise ValueError("Stage-1 probability bytes do not match reference")
    return {"passed": True, "compared_fields": list(required)}


def validate_control_update32(evidence: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "record_sha256": REFERENCE_CONTROL["stage32_record_sha256"],
        "ordered_probability_bytes_sha256": REFERENCE_CONTROL["stage32_ordered_probability_bytes_sha256"],
        "ordered_value_bytes_sha256": REFERENCE_CONTROL["ordered_value_bytes_sha256"],
        "parameter_bytes_sha256": REFERENCE_CONTROL["stage32_parameter_bytes_sha256"],
        "optimizer_canonical_sha256": REFERENCE_CONTROL["optimizer_canonical_sha256"],
        "optimizer_param_group_canonical_sha256": REFERENCE_CONTROL["optimizer_param_group_canonical_sha256"],
        "optimizer_state_steps": {
            "residual_head.0.weight": 32,
            "residual_head.0.bias": 32,
            "residual_head.2.weight": 1,
            "residual_head.2.bias": 1,
        },
    }
    if canonical_json_bytes(evidence) != canonical_json_bytes(expected):
        differing = sorted(name for name in expected if evidence.get(name) != expected[name])
        raise ValueError("control update32 reference mismatch: " + ",".join(differing))
    return {"passed": True, "evidence": copy.deepcopy(expected)}


def lower_empirical_median(values: Sequence[float]) -> float:
    numbers = sorted(float(value) for value in values)
    if not numbers or any(not math.isfinite(value) for value in numbers):
        raise ValueError("lower empirical median requires finite values")
    return numbers[(len(numbers) - 1) // 2]


def weighted_lower_median(values: Sequence[float], weights: Sequence[float]) -> float:
    if len(values) != len(weights) or not values:
        raise ValueError("weighted median inputs mismatch")
    rows = sorted((float(value), float(weight), index) for index, (value, weight) in enumerate(zip(values, weights)))
    if any(not math.isfinite(value) or not math.isfinite(weight) or weight < 0.0 for value, weight, _ in rows):
        raise ValueError("weighted median requires finite nonnegative inputs")
    total = math.fsum(weight for _, weight, _ in rows)
    if total <= 0.0:
        raise ValueError("weighted median has zero total mass")
    threshold = total / 2.0
    cumulative = 0.0
    for value, weight, _ in rows:
        cumulative += weight
        if cumulative >= threshold:
            return value
    raise AssertionError("weighted median accumulation failed")


def robust_sign(value: float) -> str:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("robust sign requires a finite value")
    if number >= ROBUST_SIGN_EPSILON:
        return "positive"
    if number <= -ROBUST_SIGN_EPSILON:
        return "negative"
    return "neutral"


def gae_decomposition_for_episode(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, float]]:
    rewards = [float(row.get("reward", 0.0)) for row in rows]
    values = [float(row["value"]) for row in rows]
    if any(not math.isfinite(value) for value in (*rewards, *values)):
        raise ValueError("GAE decomposition input is nonfinite")
    returns = [0.0] * len(rows)
    running = 0.0
    for index in reversed(range(len(rows))):
        running = rewards[index] + 0.99 * running
        returns[index] = running
    return [
        {
            "decision_index": int(row["decision_index"]),
            "monte_carlo_advantage": returns[index] - values[index],
        }
        for index, row in enumerate(rows)
    ]


def _monte_carlo_advantages(loaded: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> list[float]:
    by_key: dict[tuple[str, int], float] = {}
    episodes = list(loaded["dataset"].episodes)
    if len(episodes) != EXPECTED_TRAJECTORIES:
        raise ValueError("source trajectory count mismatch")
    for episode in episodes:
        eligible = [row for row in episode.get("decisions", []) if row.get("ppo_eligible")]
        for result in gae_decomposition_for_episode(eligible):
            key = (str(episode["episode_id"]), int(result["decision_index"]))
            if key in by_key:
                raise ValueError("duplicate Monte-Carlo row identity")
            by_key[key] = float(result["monte_carlo_advantage"])
    result = [by_key[(str(row["episode_id"]), int(row["decision_index"]))] for row in rows]
    if len(result) != EXPECTED_ROWS:
        raise ValueError("Monte-Carlo advantage count mismatch")
    return result


def _sign_stable_ordinals(rows: Sequence[Mapping[str, Any]], monte_carlo: Sequence[float]) -> list[int]:
    result = []
    for ordinal, (row, mc) in enumerate(zip(rows, monte_carlo)):
        signs = {
            robust_sign(float(row["fixed_normalized_advantage_float32"])),
            robust_sign(float(row["raw_advantage_float64"])),
            robust_sign(float(mc)),
        }
        if len(signs) == 1 and "neutral" not in signs:
            result.append(ordinal)
    if len(result) != 611:
        raise ValueError("sign-stable membership must contain exactly 611 rows")
    return result


def weighting_views(
    rows: Sequence[Mapping[str, Any]], monte_carlo: Sequence[float]
) -> dict[str, list[float]]:
    if len(rows) != EXPECTED_ROWS or len(monte_carlo) != EXPECTED_ROWS:
        raise ValueError("weighting views require 830 rows")
    ordinary = [abs(float(row["fixed_normalized_advantage_float32"])) for row in rows]
    state_totals: dict[str, float] = {}
    trajectory_totals: dict[str, float] = {}
    for row, weight in zip(rows, ordinary):
        state_totals[str(row["public_state_sha256"])] = state_totals.get(str(row["public_state_sha256"]), 0.0) + weight
        trajectory_totals[str(row["episode_id"])] = trajectory_totals.get(str(row["episode_id"]), 0.0) + weight
    equal_state = [weight / state_totals[str(row["public_state_sha256"])] if weight else 0.0 for row, weight in zip(rows, ordinary)]
    equal_trajectory = [weight / trajectory_totals[str(row["episode_id"])] if weight else 0.0 for row, weight in zip(rows, ordinary)]
    return {
        "ordinary_absolute_normalized_advantage": ordinary,
        "equal_exact_public_state": equal_state,
        "equal_source_trajectory": equal_trajectory,
        "raw_GAE_absolute_target": [abs(float(row["raw_advantage_float64"])) for row in rows],
        "Monte_Carlo_absolute_target": [abs(float(value)) for value in monte_carlo],
    }


def alignment_weighting_summary(
    movements: Sequence[float],
    rows: Sequence[Mapping[str, Any]],
    monte_carlo: Sequence[float],
    *,
    ordinals: Sequence[int] | None = None,
) -> dict[str, Any]:
    selected = list(range(EXPECTED_ROWS)) if ordinals is None else list(ordinals)
    if len(movements) != EXPECTED_ROWS:
        raise ValueError("alignment movement count mismatch")
    views = weighting_views(rows, monte_carlo)
    values = [float(movements[index]) for index in selected]
    result = {"row_count": len(selected), "lower_empirical_median": lower_empirical_median(values)}
    result["weighted_lower_medians"] = {
        name: weighted_lower_median(values, [weights[index] for index in selected])
        for name, weights in views.items()
    }
    aligned = sum(value > ORIENTATION_DEADBAND for value in values)
    anti = sum(value < -ORIENTATION_DEADBAND for value in values)
    result["alignment_score"] = (aligned - anti) / len(values)
    return result


def evaluate_safety_stop(arm_safety: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    failures = {
        arm: list(report.get("global_failures") or [])
        for arm, report in arm_safety.items()
        if report.get("hard_stop") is True or report.get("safety_pass") is not True
    }
    return {"stop_both_arms": bool(failures), "arm_failures": failures}


def should_stop_for_directional_failure(*, update_ordinal: int, directional_pass: bool) -> bool:
    if not 1 <= update_ordinal <= STAGE2_UPDATES:
        raise ValueError("directional stop check update mismatch")
    _ = directional_pass
    return False


def evaluate_terminal_gates(run: Mapping[str, Any], prepare_receipt: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    if run.get("completed_optimizer_steps_per_arm") != {"control_vanilla": 65, "treatment_pcgrad": 65}:
        failures.append("completed_optimizer_steps")
    if run.get("all_safety_gates_pass") is not True:
        failures.append("safety")
    mechanism = run.get("mechanism") or {}
    if mechanism.get("surgery_nonzero") is not True:
        failures.append("mechanism:surgery_nonzero")
    touched = set(mechanism.get("tasks_touched_first_16") or [])
    if not set(AUDIT_ADVERSE_TASKS).issubset(touched):
        failures.append("mechanism:adverse_groups_first16")
    projection = mechanism.get("cumulative_delta_projections") or {}
    for update in (48, 64):
        if any(float((projection.get(str(update)) or {}).get(task, -math.inf)) <= 0.0 for task in PRIORITY_TASKS):
            failures.append(f"mechanism:cumulative_projection:{update}")
    summaries = run.get("alignment_summaries") or {}
    for update in (48, 64):
        control = (summaries.get("control_vanilla") or {}).get(str(update)) or {}
        treatment = (summaries.get("treatment_pcgrad") or {}).get(str(update)) or {}
        differences = (summaries.get("treatment_minus_control") or {}).get(str(update)) or {}
        for task in PRIORITY_TASKS:
            if float((treatment.get("priority") or {}).get(task, {}).get("lower_empirical_median", -math.inf)) < 1e-6:
                failures.append(f"priority:treatment:{task}:{update}")
            if float((differences.get("priority") or {}).get(task, {}).get("lower_empirical_median", -math.inf)) < 1e-6:
                failures.append(f"priority:difference:{task}:{update}")
        if float((treatment.get("global") or {}).get("lower_empirical_median", -math.inf)) < 1e-5:
            failures.append(f"global:median:{update}")
        if float((treatment.get("global") or {}).get("alignment_score", -math.inf)) < 0.1:
            failures.append(f"global:score:{update}")
        if any(float(value) <= 1e-7 for value in (treatment.get("all_12_family_polarity_lower_medians") or {}).values()):
            failures.append(f"global:family_floor:{update}")
        if update == 64:
            for task in PRIORITY_TASKS:
                weighted = (treatment.get("priority") or {}).get(task, {}).get("weighted_lower_medians") or {}
                for view in (
                    "ordinary_absolute_normalized_advantage",
                    "equal_exact_public_state",
                    "equal_source_trajectory",
                ):
                    if float(weighted.get(view, -math.inf)) < 1e-6:
                        failures.append(f"priority:weighted:{task}:{view}")
            if all(float((control.get("priority") or {}).get(task, {}).get("lower_empirical_median", -math.inf)) >= 1e-6 for task in PRIORITY_TASKS):
                failures.append("control_must_fail_one_priority_group")
            global_weighted = (treatment.get("global") or {}).get("weighted_lower_medians") or {}
            if float(global_weighted.get("raw_GAE_absolute_target", -math.inf)) < 0.0:
                failures.append("global:raw_GAE")
            if float(global_weighted.get("Monte_Carlo_absolute_target", -math.inf)) < 0.0:
                failures.append("global:Monte_Carlo")
            if float(treatment.get("sign_stable_611_lower_empirical_median", -math.inf)) < 0.0:
                failures.append("global:sign_stable_611")
    end = run.get("terminal_END_controls") or {}
    if end.get("passed") is not True:
        failures.extend(f"END:{value}" for value in end.get("failures") or ["missing"])
    if run.get("duplicate_treatment_canonical_outputs_identical") is not True:
        failures.append("duplicate_treatment")
    if run.get("checkpoint_reload_exact") is not True:
        failures.append("checkpoint_reload")
    if run.get("independent_numeric_audit_pass") is not True:
        failures.append("independent_numeric_audit")
    if run.get("root_recomputation_pass") is not True:
        failures.append("root_recomputation")
    return {"accepted": not failures, "failures": failures}


def terminal_end_controls(
    prepare_receipt: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    rows = prepare_receipt["rows"]
    memberships = base._validated_directional_memberships(rows, prepare_receipt["directional_memberships"])
    failures: list[str] = []
    for ordinal in memberships["positive_normalized_teacher_and_sampled_end_ordinals"]:
        fixed = rows[ordinal]
        end = int(fixed["end_index"])
        delta = float(metrics[ordinal]["probabilities_float32"][end]) - float(fixed["initial_probabilities_float32"][end])
        if delta < 1e-6:
            failures.append(f"positive_normalized:{ordinal}")
    for ordinal in memberships["negative_target_ordinals"]:
        fixed = rows[ordinal]
        sampled = int(fixed["sampled_index"])
        delta = float(metrics[ordinal]["probabilities_float32"][sampled]) - float(fixed["initial_probabilities_float32"][sampled])
        if -delta <= ORIENTATION_DEADBAND:
            failures.append(f"negative_control:{ordinal}")
    for ordinal in memberships["teacher_end_ordinals"]:
        fixed = rows[ordinal]
        probabilities = list(map(float, metrics[ordinal]["probabilities_float32"]))
        maximum = max(probabilities)
        if [index for index, value in enumerate(probabilities) if value == maximum] != [int(fixed["end_index"])]:
            failures.append(f"teacher_END_argmax:{ordinal}")
    raw_deltas = []
    for ordinal in memberships["positive_raw_teacher_and_sampled_end_ordinals"]:
        fixed = rows[ordinal]
        end = int(fixed["end_index"])
        raw_deltas.append(float(metrics[ordinal]["probabilities_float32"][end]) - float(fixed["initial_probabilities_float32"][end]))
    lower = lower_empirical_median(raw_deltas)
    maximum_decrease = max(max(0.0, -value) for value in raw_deltas)
    if lower <= 0.0:
        failures.append("raw_positive_lower_median")
    if maximum_decrease > 0.0025:
        failures.append("raw_positive_maximum_decrease")
    return {
        "passed": not failures,
        "failures": failures,
        "positive_normalized_count": 20,
        "negative_control_count": 4,
        "teacher_END_count": 43,
        "positive_raw_count": 31,
        "positive_raw_lower_empirical_median": lower,
        "maximum_individual_raw_positive_END_probability_decrease": maximum_decrease,
    }


def _validate_reference_receipt() -> dict[str, Any]:
    receipt = _load_hashed_json(
        _repo_path(REJECTED_RECEIPT_RELATIVE_PATH),
        REJECTED_RECEIPT_FILE_SHA256,
        label="iteration-007 rejected receipt reference",
    )
    if receipt.get("receipt_sha256") != REJECTED_RECEIPT_SELF_SHA256:
        raise ValueError("rejected receipt self-hash mismatch")
    if receipt.get("output_checkpoint_sha256") != REJECTED_CHECKPOINT_SHA256:
        raise ValueError("rejected checkpoint reference mismatch")
    training = receipt.get("training") or {}
    if training.get("stage_1_record_hash") != REFERENCE_CONTROL["stage1_record_sha256"]:
        raise ValueError("Stage-1 reference record mismatch")
    stage1_outputs = base._ordered_output_hashes(training["stage_1_metrics"])
    if stage1_outputs["ordered_probability_bytes_sha256"] != REFERENCE_CONTROL["stage1_ordered_probability_bytes_sha256"]:
        raise ValueError("Stage-1 reference probability mismatch")
    stage32 = training["stage_2_update_summaries"][31]
    if stage32.get("record_hash") != REFERENCE_CONTROL["stage32_record_sha256"]:
        raise ValueError("Stage-32 reference record mismatch")
    stage32_outputs = base._ordered_output_hashes(training["stage_2_full_diagnostics"]["32"])
    if stage32_outputs["ordered_probability_bytes_sha256"] != REFERENCE_CONTROL["stage32_ordered_probability_bytes_sha256"]:
        raise ValueError("Stage-32 reference probability mismatch")
    if stage32_outputs["ordered_value_bytes_sha256"] != REFERENCE_CONTROL["ordered_value_bytes_sha256"]:
        raise ValueError("reference value bytes mismatch")
    parameter_hashes = {
        row["name"]: row["after_byte_sha256"]
        for row in stage32["parameter_diffs_from_initial"]
        if row["name"] in REFERENCE_CONTROL["stage32_parameter_bytes_sha256"]
    }
    if parameter_hashes != REFERENCE_CONTROL["stage32_parameter_bytes_sha256"]:
        raise ValueError("Stage-32 reference parameter mismatch")
    return {
        "receipt_path": REJECTED_RECEIPT_RELATIVE_PATH.as_posix(),
        "receipt_file_sha256": REJECTED_RECEIPT_FILE_SHA256,
        "receipt_self_sha256": REJECTED_RECEIPT_SELF_SHA256,
        "checkpoint_path": REJECTED_CHECKPOINT_RELATIVE_PATH.as_posix(),
        "checkpoint_sha256": REJECTED_CHECKPOINT_SHA256,
        "checkpoint_loaded": False,
        **copy.deepcopy(REFERENCE_CONTROL),
    }


EXECUTION_SPEC_KEYS = {
    "schema_version",
    "implementation_plan_path",
    "implementation_plan_sha256",
    "implementation_path",
    "implementation_snapshot_sha256",
    "source_implementation_path",
    "source_implementation_snapshot_sha256",
    "input_checkpoint_path",
    "input_checkpoint_sha256",
    "manifest_path",
    "manifest_sha256",
    "dataset_sha256",
    "fixed_advantages_sha256",
    "fixed_behavior_logprobabilities_sha256",
    "prepare_receipt_path",
    "training_contract",
    "diagnostic_contract",
    "safety_gates",
    "terminal_offline_acceptance",
    "control_reference",
    "output_directory",
}


def _validate_execution_spec(
    path: Path,
    expected_hash: str,
    *,
    plan: Mapping[str, Any],
    implementation_snapshot: Mapping[str, Any],
    require_prepare_receipt: bool,
) -> dict[str, Any]:
    expected_hash = _strict_sha256(expected_hash, label="execution spec hash")
    spec = _load_hashed_json(path, expected_hash, label="iteration-009 execution spec")
    if set(spec) != EXECUTION_SPEC_KEYS or spec.get("schema_version") != EXECUTION_SPEC_SCHEMA_VERSION:
        raise ValueError("execution spec schema or key set mismatch")
    exact = {
        "implementation_plan_path": PLAN_RELATIVE_PATH.as_posix(),
        "implementation_plan_sha256": PLAN_SHA256,
        "implementation_path": IMPLEMENTATION_RELATIVE_PATH.as_posix(),
        "implementation_snapshot_sha256": implementation_snapshot["sha256"],
        "source_implementation_path": SOURCE_IMPLEMENTATION_RELATIVE_PATH.as_posix(),
        "source_implementation_snapshot_sha256": SOURCE_IMPLEMENTATION_SHA256,
        "input_checkpoint_path": INPUT_CHECKPOINT_RELATIVE_PATH.as_posix(),
        "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
        "manifest_path": MANIFEST_RELATIVE_PATH.as_posix(),
        "manifest_sha256": MANIFEST_SHA256,
        "dataset_sha256": DATASET_SHA256,
        "fixed_advantages_sha256": FIXED_ADVANTAGES_SHA256,
        "fixed_behavior_logprobabilities_sha256": FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256,
        "training_contract": plan["training_contract"],
        "diagnostic_contract": plan["diagnostic_contract"],
        "safety_gates": plan["safety_gates"],
        "terminal_offline_acceptance": plan["terminal_offline_acceptance"],
        "control_reference": REFERENCE_CONTROL,
    }
    for name, value in exact.items():
        if canonical_json_bytes(spec.get(name)) != canonical_json_bytes(value):
            raise ValueError(f"execution spec binding mismatch: {name}")
    prepare_path = _repo_path(PurePosixPath(str(spec["prepare_receipt_path"])))
    if require_prepare_receipt and not prepare_path.is_file():
        raise ValueError("execution spec prepare receipt is absent")
    return spec


def _validate_execution_output_path(relative: Any) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError("execution output path must be a repository-relative string")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError("execution output path must be confined and relative")
    output = _repo_path(pure).absolute()
    candidate = _repo_path(IMPLEMENTATION_RELATIVE_PATH).resolve(strict=True)
    allowed = candidate / "test_outputs"
    if output.parent != allowed or output.exists():
        raise ValueError("execution output must be an absent direct child of candidate test_outputs")
    if not allowed.exists() or allowed.resolve(strict=True) != allowed:
        raise ValueError("execution output parent is absent or changed")
    return output


def _validate_provenance(plan: Mapping[str, Any]) -> dict[str, Any]:
    source_snapshot = inherited.implementation_snapshot(_repo_path(SOURCE_IMPLEMENTATION_RELATIVE_PATH))
    if source_snapshot["file_count"] != SOURCE_IMPLEMENTATION_FILE_COUNT or source_snapshot["sha256"] != SOURCE_IMPLEMENTATION_SHA256:
        raise ValueError("source implementation snapshot mismatch")
    parent = _file_reference(PARENT_RESULT_RELATIVE_PATH, PARENT_RESULT_SHA256, label="parent result")
    audit_plan = _file_reference(AUDIT_PLAN_RELATIVE_PATH, AUDIT_PLAN_SHA256, label="audit plan")
    audit_spec = _file_reference(AUDIT_EXECUTION_SPEC_RELATIVE_PATH, AUDIT_EXECUTION_SPEC_SHA256, label="audit execution spec")
    audit_manifest = _load_hashed_json(
        _repo_path(AUDIT_MANIFEST_RELATIVE_PATH),
        AUDIT_MANIFEST_FILE_SHA256,
        label="audit manifest",
    )
    manifest_core = dict(audit_manifest)
    manifest_core_claim = manifest_core.pop("manifest_core_sha256", None)
    if (
        manifest_core_claim != AUDIT_MANIFEST_CORE_SHA256
        or canonical_sha256(manifest_core) != AUDIT_MANIFEST_CORE_SHA256
    ):
        raise ValueError("audit manifest self binding mismatch")
    immutable = plan["immutable_inputs"]
    for relative, expected, label in (
        (INPUT_CHECKPOINT_RELATIVE_PATH, INPUT_CHECKPOINT_SHA256, "input checkpoint"),
        (MANIFEST_RELATIVE_PATH, MANIFEST_SHA256, "rollout manifest"),
        (REJECTED_CHECKPOINT_RELATIVE_PATH, REJECTED_CHECKPOINT_SHA256, "rejected checkpoint"),
    ):
        _file_reference(relative, expected, label=label)
    return {
        "parent_result": parent,
        "audit_plan": audit_plan,
        "audit_execution_spec": audit_spec,
        "audit_manifest": {
            "path": AUDIT_MANIFEST_RELATIVE_PATH.as_posix(),
            "file_sha256": AUDIT_MANIFEST_FILE_SHA256,
            "core_sha256": AUDIT_MANIFEST_CORE_SHA256,
        },
        "source_implementation": {
            "path": SOURCE_IMPLEMENTATION_RELATIVE_PATH.as_posix(),
            **source_snapshot,
        },
    }


def _build_prepare_receipt(
    *,
    runtime: Mapping[str, Any],
    execution_spec_path: Path,
    execution_spec_sha256: str,
) -> dict[str, Any]:
    plan = _load_plan()
    provenance = _validate_provenance(plan)
    implementation = inherited.implementation_snapshot(_repo_path(IMPLEMENTATION_RELATIVE_PATH))
    spec = _validate_execution_spec(
        execution_spec_path,
        execution_spec_sha256,
        plan=plan,
        implementation_snapshot=implementation,
        require_prepare_receipt=False,
    )
    reference = _validate_reference_receipt()
    inherited_prepare = base._build_prepare_receipt(runtime)
    loaded = inherited._load_validated_inputs()
    rejected_absolute = _repo_path(REJECTED_CHECKPOINT_RELATIVE_PATH).resolve(strict=True)
    if loaded["checkpoint_path"].resolve(strict=True) == rejected_absolute:
        raise ValueError("rejected checkpoint was loaded")
    rows = copy.deepcopy(inherited_prepare["rows"])
    if len(rows) != EXPECTED_ROWS or len(loaded["rows"]) != EXPECTED_ROWS:
        raise ValueError("prepare did not reproduce exactly 830 rows")
    partition = build_task_partition(rows)
    monte_carlo = _monte_carlo_advantages(loaded, rows)
    sign_stable = _sign_stable_ordinals(rows, monte_carlo)
    before = {name: _tensor_sha256_v2(parameter) for name, parameter in loaded["model"].named_parameters()}
    after = {name: _tensor_sha256_v2(parameter) for name, parameter in loaded["model"].named_parameters()}
    if before != after:
        raise ValueError("prepare changed a model parameter")
    core = {
        "schema_version": PREPARE_RECEIPT_SCHEMA_VERSION,
        "plan": {
            "path": PLAN_RELATIVE_PATH.as_posix(),
            "file_sha256": PLAN_SHA256,
            "canonical_sha256": canonical_sha256(plan),
            "contract": copy.deepcopy(plan),
        },
        "provenance": provenance,
        "implementation": {"path": IMPLEMENTATION_RELATIVE_PATH.as_posix(), **implementation},
        "execution_spec_binding": {
            "path": str(execution_spec_path.absolute()),
            "sha256": execution_spec_sha256,
            "schema_version": spec["schema_version"],
            "validated_file_exists": True,
        },
        "runtime_thread_receipt": dict(runtime),
        "immutable_inputs": {
            "input_checkpoint_path": INPUT_CHECKPOINT_RELATIVE_PATH.as_posix(),
            "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
            "manifest_path": MANIFEST_RELATIVE_PATH.as_posix(),
            "manifest_sha256": MANIFEST_SHA256,
            "dataset_sha256": DATASET_SHA256,
            "row_count": EXPECTED_ROWS,
            "trajectory_count": EXPECTED_TRAJECTORIES,
            "fixed_advantages_sha256": FIXED_ADVANTAGES_SHA256,
            "fixed_behavior_logprobabilities_sha256": FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256,
            "rejected_checkpoint_path": REJECTED_CHECKPOINT_RELATIVE_PATH.as_posix(),
            "rejected_checkpoint_sha256": REJECTED_CHECKPOINT_SHA256,
            "rejected_checkpoint_loaded": False,
        },
        "control_reference": reference,
        "rows": rows,
        "ordered_training_rows_sha256": canonical_sha256(rows),
        "action_families": copy.deepcopy(inherited_prepare["action_families"]),
        "directional_memberships": copy.deepcopy(inherited_prepare["directional_memberships"]),
        "task_partition": task_membership_receipt(partition),
        "monte_carlo_advantages_float64": monte_carlo,
        "monte_carlo_advantages_sha256": canonical_sha256(monte_carlo),
        "sign_stable_611_ordinals": sign_stable,
        "sign_stable_611_sha256": canonical_sha256(sign_stable),
        "initial_value_identity": copy.deepcopy(inherited_prepare["initial_value_identity"]),
        "model_parameters": copy.deepcopy(inherited_prepare["model_parameters"]),
        "prepare_proof": {
            "optimizer_constructed": False,
            "optimizer_steps": 0,
            "parameters_changed": False,
            "checkpoint_written": False,
            "rejected_checkpoint_loaded": False,
            "training_executed": False,
            "runtime_smoke_executed": False,
            "games_run": 0,
        },
    }
    return {**core, "receipt_sha256": canonical_sha256(core)}


def validate_prepare_receipt(receipt: Mapping[str, Any]) -> None:
    core = dict(receipt)
    claimed = _strict_sha256(core.pop("receipt_sha256", None), label="prepare receipt self-hash")
    if canonical_sha256(core) != claimed:
        raise ValueError("prepare receipt self-hash mismatch")
    if receipt.get("schema_version") != PREPARE_RECEIPT_SCHEMA_VERSION:
        raise ValueError("prepare receipt schema mismatch")
    proof = receipt.get("prepare_proof") or {}
    expected_proof = {
        "optimizer_constructed": False,
        "optimizer_steps": 0,
        "parameters_changed": False,
        "checkpoint_written": False,
        "rejected_checkpoint_loaded": False,
        "training_executed": False,
        "runtime_smoke_executed": False,
        "games_run": 0,
    }
    if proof != expected_proof:
        raise ValueError("prepare proof mismatch")
    partition = {
        task["task"]: task["ordinals"] for task in receipt["task_partition"]["tasks"]
    }
    validate_task_partition(partition)
    if len(receipt.get("rows") or []) != EXPECTED_ROWS:
        raise ValueError("prepare receipt row count mismatch")
    if len(receipt.get("sign_stable_611_ordinals") or []) != 611:
        raise ValueError("prepare receipt sign-stable count mismatch")


def _validate_prepare_output_path(path: Path) -> Path:
    absolute = path.absolute()
    candidate_root = _repo_path(IMPLEMENTATION_RELATIVE_PATH).resolve(strict=True)
    allowed_root = candidate_root / "test_outputs"
    if absolute.name != PREPARE_OUTPUT_FILENAME or absolute.parent.parent != allowed_root:
        raise ValueError("prepare receipt must be a direct child of a new test_outputs subdirectory")
    if absolute.exists() or absolute.parent.exists():
        raise FileExistsError("prepare output destination already exists")
    if absolute.parent.parent.exists() and absolute.parent.parent.resolve(strict=True) != allowed_root.resolve(strict=True):
        raise ValueError("prepare output root identity mismatch")
    return absolute


def _atomic_publish_receipt(path: Path, receipt: Mapping[str, Any]) -> str:
    payload = canonical_json_bytes(receipt, newline=True)
    path.parent.mkdir(parents=False, exist_ok=False)
    temporary = path.parent / ("." + path.name + ".tmp")
    try:
        descriptor = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            handle = os.fdopen(descriptor, "wb")
        except Exception:
            os.close(descriptor)
            raise
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        if path.parent.exists() and not any(path.parent.iterdir()):
            path.parent.rmdir()
        raise
    return hashlib.sha256(payload).hexdigest().upper()


def prepare(
    *,
    output_receipt: Path,
    execution_spec: Path,
    execution_spec_sha256: str,
) -> dict[str, Any]:
    """Validate all inputs and publish one no-training receipt."""

    output = _validate_prepare_output_path(output_receipt)
    runtime = inherited._runtime_identity()
    receipt = _build_prepare_receipt(
        runtime=runtime,
        execution_spec_path=execution_spec.absolute(),
        execution_spec_sha256=_strict_sha256(execution_spec_sha256, label="execution spec hash"),
    )
    validate_prepare_receipt(receipt)
    file_hash = _atomic_publish_receipt(output, receipt)
    return {
        "mode": "prepare",
        "receipt_path": str(output),
        "receipt_file_sha256": file_hash,
        "receipt_sha256": receipt["receipt_sha256"],
        "implementation_snapshot_sha256": receipt["implementation"]["sha256"],
        "implementation_snapshot_file_count": receipt["implementation"]["file_count"],
        "optimizer_steps": 0,
        "games_run": 0,
    }


def _checkpoint_payload(
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    *,
    arm: str,
    execution_spec_sha256: str,
    receipt_sha256: str,
) -> bytes:
    value = {
        "schema_version": "mass-preserving-pcgrad-checkpoint-v1",
        "arm": arm,
        "execution_spec_sha256": execution_spec_sha256,
        "execution_receipt_sha256": receipt_sha256,
        "model_state_dict": {name: tensor.detach().cpu() for name, tensor in model.state_dict().items()},
        "optimizer_state_dict": optimizer.state_dict(),
    }
    buffer = io.BytesIO()
    torch.save(value, buffer)
    return buffer.getvalue()


def _validate_checkpoint_payload(
    payload: bytes,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    *,
    arm: str,
    execution_spec_sha256: str,
    receipt_sha256: str,
) -> None:
    loaded = torch.load(io.BytesIO(payload), map_location="cpu", weights_only=True)
    if loaded.get("schema_version") != "mass-preserving-pcgrad-checkpoint-v1" or loaded.get("arm") != arm:
        raise ValueError("checkpoint metadata mismatch")
    if loaded.get("execution_spec_sha256") != execution_spec_sha256 or loaded.get("execution_receipt_sha256") != receipt_sha256:
        raise ValueError("checkpoint execution binding mismatch")
    expected_model = model.state_dict()
    actual_model = loaded.get("model_state_dict") or {}
    if tuple(actual_model) != tuple(expected_model) or any(not torch.equal(actual_model[name], expected_model[name].detach().cpu()) for name in expected_model):
        raise ValueError("checkpoint model reload mismatch")
    expected_optimizer = optimizer.state_dict()
    if not _nested_byte_exact_v2(loaded.get("optimizer_state_dict"), expected_optimizer):
        raise ValueError("checkpoint optimizer reload mismatch")


def _superseded_atomic_publish_terminal(
    *,
    output_directory: Path,
    control_model: torch.nn.Module,
    control_optimizer: torch.optim.Optimizer,
    treatment_model: torch.nn.Module,
    treatment_optimizer: torch.optim.Optimizer,
    receipt_core: Mapping[str, Any],
    execution_spec_sha256: str,
    allow_accepted: bool,
) -> dict[str, Any]:
    """Historical review evidence; corrected finalization must use ``finalize``."""

    raise RuntimeError(
        "direct terminal publication is superseded by immutable pending-audit finalization"
    )

    output = output_directory.absolute()
    candidate = _repo_path(IMPLEMENTATION_RELATIVE_PATH).resolve(strict=True)
    allowed = candidate / "test_outputs"
    if output.parent.resolve(strict=True) != allowed or output.exists():
        raise ValueError("terminal output must be a new direct child of candidate test_outputs")
    gates = receipt_core.get("gates") or {}
    status = "accepted" if gates.get("accepted") is True else "rejected"
    if status == "accepted" and not allow_accepted:
        raise PermissionError("ACCEPTED publication requires independent audit and root recomputation authorization")
    if status == "accepted" and (
        receipt_core.get("independent_numeric_audit_pass") is not True
        or receipt_core.get("root_recomputation_pass") is not True
    ):
        raise PermissionError("ACCEPTED gates are incomplete")
    core = dict(receipt_core)
    core["schema_version"] = EXECUTION_RECEIPT_SCHEMA_VERSION
    core["status"] = status
    receipt_sha = canonical_sha256(core)
    receipt = {**core, "receipt_sha256": receipt_sha}
    checkpoint_payloads = {
        "control.pt": _checkpoint_payload(
            control_model, control_optimizer, arm="control_vanilla",
            execution_spec_sha256=execution_spec_sha256, receipt_sha256=receipt_sha,
        ),
        "treatment.pt": _checkpoint_payload(
            treatment_model, treatment_optimizer, arm="treatment_pcgrad",
            execution_spec_sha256=execution_spec_sha256, receipt_sha256=receipt_sha,
        ),
    }
    _validate_checkpoint_payload(
        checkpoint_payloads["control.pt"], control_model, control_optimizer,
        arm="control_vanilla", execution_spec_sha256=execution_spec_sha256,
        receipt_sha256=receipt_sha,
    )
    _validate_checkpoint_payload(
        checkpoint_payloads["treatment.pt"], treatment_model, treatment_optimizer,
        arm="treatment_pcgrad", execution_spec_sha256=execution_spec_sha256,
        receipt_sha256=receipt_sha,
    )
    staging = Path(tempfile.mkdtemp(prefix=".pcgrad-stage-", dir=str(allowed)))
    try:
        for name, payload in checkpoint_payloads.items():
            with (staging / name).open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        receipt_name = f"{status}_receipt.json"
        receipt_payload = canonical_json_bytes(receipt, newline=True)
        with (staging / receipt_name).open("xb") as handle:
            handle.write(receipt_payload)
            handle.flush()
            os.fsync(handle.fileno())
        marker = {
            "status": status,
            "receipt_file_sha256": hashlib.sha256(receipt_payload).hexdigest().upper(),
            "receipt_sha256": receipt_sha,
        }
        with (staging / status.upper()).open("xb") as handle:
            handle.write(canonical_json_bytes(marker, newline=True))
            handle.flush()
            os.fsync(handle.fileno())
        expected = {"control.pt", "treatment.pt", receipt_name, status.upper()}
        if {item.name for item in staging.iterdir()} != expected:
            raise ValueError("terminal staging artifact set mismatch")
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {
        "status": status,
        "output_directory": str(output),
        "receipt_path": str(output / f"{status}_receipt.json"),
        "receipt_sha256": receipt_sha,
        "checkpoint_sha256s": {
            name: hashlib.sha256(payload).hexdigest().upper()
            for name, payload in checkpoint_payloads.items()
        },
    }


def _model_parameter_hashes(model: torch.nn.Module) -> dict[str, str]:
    return {
        name: _tensor_sha256_v2(parameter)
        for name, parameter in model.named_parameters()
    }


def _load_execution_arms(
    prepare_receipt: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Load two independent initial models while recomputing GAE only once."""

    control = inherited._load_validated_inputs()
    treatment = inherited._load_validated_inputs()
    rejected = _repo_path(REJECTED_CHECKPOINT_RELATIVE_PATH).resolve(strict=True)
    for arm in (control, treatment):
        if arm["checkpoint_path"].resolve(strict=True) == rejected:
            raise ValueError("rejected checkpoint was loaded")
        if len(arm["rows"]) != EXPECTED_ROWS:
            raise ValueError("execution arm row count mismatch")
    fixed = base._build_authorized_execution_fixed_inputs(control, prepare_receipt)
    control["execution_fixed_inputs"] = fixed
    treatment["execution_fixed_inputs"] = copy.deepcopy(fixed)
    if _model_parameter_hashes(control["model"]) != _model_parameter_hashes(treatment["model"]):
        raise ValueError("independent arm initialization mismatch")
    return {"control_vanilla": control, "treatment_pcgrad": treatment}


def _stage1_arm(loaded: Mapping[str, Any], prepare_receipt: Mapping[str, Any]) -> dict[str, Any]:
    model = loaded["model"]
    progress = base.ExecutionProgress(model=model)
    initial_parameters = {
        name: value.detach().clone() for name, value in model.state_dict().items()
    }
    base._set_trainability(model, stage=1)
    optimizer = base._new_actor_adam(model)
    progress.optimizer = optimizer
    report = base._stage_full_batch_step(
        stage=1,
        loaded=loaded,
        prepare_receipt=prepare_receipt,
        optimizer=optimizer,
        initial_parameters=initial_parameters,
        progress=progress,
    )
    metrics = base._measure_stage(loaded, prepare_receipt, stage=1)
    value = base.value_change_summary(prepare_receipt, metrics)
    safety = base.evaluate_stage_gates(
        prepare_receipt,
        metrics,
        stage=1,
        training_nonfinite_count=report[
            "nonfinite_value_gradient_optimizer_or_parameter_count"
        ],
        parameter_optimizer_contract_pass=True,
        value_contract_pass=(
            value["all_rows_byte_exact_to_initial"]
            and value["raw_value_mse_exact_to_initial"]
            and value["aggregate_hash_exact_to_initial"]
        ),
    )
    output_hashes = base._ordered_output_hashes(metrics)
    record_hash = canonical_sha256(
        {
            "stage_1_report": report,
            "stage_1_safety": safety,
            "stage_1_value_identity": value,
            **output_hashes,
        }
    )
    evidence = {
        "model_parameter_hashes": _model_parameter_hashes(model),
        "optimizer_canonical": optimizer_canonical_record(optimizer, model),
        "output_hashes": output_hashes,
        "losses": {
            "loss": report["loss"],
            "policy_loss": report["policy_loss"],
            "anchor_kl": report["pre_step_mean_anchor_kl"],
            "entropy": report["entropy"],
        },
        "fixed_input_identities": {
            "fixed_advantages_sha256": report["fixed_advantages_sha256"],
            "fixed_behavior_logprobabilities_sha256": report[
                "fixed_behavior_logprobabilities_sha256"
            ],
            "row_count": len(metrics),
        },
        "stage1_record_sha256": record_hash,
    }
    return {
        "model": model,
        "optimizer": optimizer,
        "progress": progress,
        "initial_parameters": initial_parameters,
        "stage2_start_parameters": {
            name: value.detach().clone() for name, value in model.state_dict().items()
        },
        "stage1_report": report,
        "stage1_metrics": metrics,
        "stage1_safety": safety,
        "stage1_value_identity": value,
        "stage1_record_sha256": record_hash,
        "stage1_equality_evidence": evidence,
    }


def _fixed_partition_from_receipt(receipt: Mapping[str, Any]) -> dict[str, list[int]]:
    partition = {
        row["task"]: list(row["ordinals"])
        for row in receipt["task_partition"]["tasks"]
    }
    validate_task_partition(partition)
    if partition != build_task_partition(receipt["rows"]):
        raise ValueError("execution task partition differs from prepare")
    return partition


def _stage2_loss_terms(
    loaded: Mapping[str, Any], prepare_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    model = loaded["model"]
    base._set_trainability(model, stage=2)
    fixed_inputs = loaded["execution_fixed_inputs"]
    policy_terms: list[torch.Tensor] = []
    anchor_terms: list[torch.Tensor] = []
    entropy_terms: list[torch.Tensor] = []
    clip_active: list[int] = []
    ratios: list[float] = []
    for ordinal, ((episode, row), fixed) in enumerate(
        zip(loaded["rows"], prepare_receipt["rows"])
    ):
        if (
            fixed["ppo_row_ordinal"] != ordinal
            or fixed["episode_id"] != str(episode["episode_id"])
            or fixed["decision_index"] != int(row["decision_index"])
            or int(fixed_inputs["sampled_indices"][ordinal])
            != int(fixed["sampled_index"])
        ):
            raise ValueError("Stage-2 fixed row identity mismatch")
        state = torch.tensor(row["state_vector"], dtype=torch.float32, device="cpu")
        actions = torch.tensor(row["action_vectors"], dtype=torch.float32, device="cpu")
        residuals, value = model(state, actions)
        probabilities, log_probabilities = _torch_behavior_distribution(
            residuals,
            teacher_index=int(row["teacher_action"][0]),
            reference_config=loaded["reference_config"],
        )
        anchor = _torch_behavior_anchor_kl(
            residuals,
            teacher_index=int(row["teacher_action"][0]),
            reference_config=loaded["reference_config"],
        )
        selected = int(fixed["sampled_index"])
        old_logprob = torch.tensor(
            float(fixed_inputs["behavior_logprobabilities_float64"][ordinal]),
            dtype=torch.float32,
        )
        advantage = torch.tensor(
            float(fixed_inputs["normalized_advantages_float32"][ordinal]),
            dtype=torch.float32,
        )
        ratio = torch.exp(log_probabilities[selected] - old_logprob)
        unclipped = ratio * advantage
        clipped = torch.clamp(ratio, 0.9, 1.1) * advantage
        policy = -torch.minimum(unclipped, clipped)
        entropy = -(probabilities * log_probabilities).sum()
        inherited._finite_tensors_or_raise(
            (residuals, value, probabilities, log_probabilities, anchor, policy),
            label=f"Stage-2 row {ordinal}",
        )
        if float(clipped.detach()) < float(unclipped.detach()):
            clip_active.append(ordinal)
        ratios.append(float(ratio.detach()))
        policy_terms.append(policy)
        anchor_terms.append(anchor)
        entropy_terms.append(entropy)
    if len(policy_terms) != EXPECTED_ROWS:
        raise ValueError("Stage-2 full batch row count mismatch")
    return {
        "policy_terms": policy_terms,
        "anchor_terms": anchor_terms,
        "entropy_terms": entropy_terms,
        "clip_active_ordinals": clip_active,
        "ratios": ratios,
    }


def _autograd_map(
    loss: torch.Tensor,
    model: torch.nn.Module,
    *,
    retain_graph: bool,
) -> dict[str, torch.Tensor]:
    named = dict(model.named_parameters())
    values = torch.autograd.grad(
        loss,
        [named[name] for name in PARAMETER_NAMES],
        retain_graph=retain_graph,
        create_graph=False,
        allow_unused=False,
    )
    result = {
        name: value.detach().clone() for name, value in zip(PARAMETER_NAMES, values)
    }
    inherited._finite_tensors_or_raise(result.values(), label="Stage-2 autograd map")
    return result


def _gradient_bundle(
    loaded: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    partition: Mapping[str, Sequence[int]],
) -> dict[str, Any]:
    model = loaded["model"]
    terms = _stage2_loss_terms(loaded, prepare_receipt)
    policies = terms["policy_terms"]
    tasks: dict[str, dict[str, torch.Tensor]] = {}
    for task in TASK_ORDER:
        loss = torch.stack([policies[index] for index in partition[task]]).sum() / COMMON_DENOMINATOR
        tasks[task] = _autograd_map(loss, model, retain_graph=True)
    direct_loss = torch.stack(policies).mean()
    direct = _autograd_map(direct_loss, model, retain_graph=True)
    anchor_loss = ANCHOR_KL_COEFFICIENT * torch.stack(terms["anchor_terms"]).mean()
    anchor = _autograd_map(anchor_loss, model, retain_graph=True)
    return {
        **terms,
        "task_gradients": tasks,
        "direct_policy_gradient": direct,
        "anchor_kl_gradient": anchor,
        "direct_policy_loss": direct_loss,
        "anchor_kl_contribution": anchor_loss,
        "total_loss": direct_loss + anchor_loss,
        "entropy": torch.stack(terms["entropy_terms"]).mean(),
    }


def _raw_gradient_diagnostics(
    tasks: Mapping[str, Mapping[str, torch.Tensor]],
    direct: Mapping[str, torch.Tensor],
) -> dict[str, Any]:
    direct_vector, _ = _flatten_gradient_map(direct)
    vectors = {
        task: _flatten_gradient_map(tasks[task])[0] for task in TASK_ORDER
    }
    sum_evidence = validate_unsurgeried_sum(vectors, direct_vector)
    norms = {task: float(_vector_norm(vector)) for task, vector in vectors.items()}
    pairs = []
    dot_matrix: dict[str, dict[str, float]] = {name: {} for name in TASK_ORDER}
    cosine_matrix: dict[str, dict[str, float | None]] = {
        name: {} for name in TASK_ORDER
    }
    for left in TASK_ORDER:
        for right in TASK_ORDER:
            dot = float(torch.dot(vectors[left], vectors[right]))
            denominator = norms[left] * norms[right]
            dot_matrix[left][right] = dot
            cosine_matrix[left][right] = (
                None if denominator == 0.0 else dot / denominator
            )
    for left_index, left in enumerate(TASK_ORDER):
        for right in TASK_ORDER[left_index + 1:]:
            dot = float(torch.dot(vectors[left], vectors[right]))
            denominator = norms[left] * norms[right]
            pairs.append({
                "left": left,
                "right": right,
                "dot": dot,
                "cosine": None if denominator == 0.0 else dot / denominator,
            })
    return {
        "raw_task_gradient_norms": norms,
        "raw_task_gradients_float64": {
            name: vectors[name].tolist() for name in TASK_ORDER
        },
        "pairwise_raw_task_dots_and_cosines": pairs,
        "pairwise_raw_task_dot_matrix": dot_matrix,
        "pairwise_raw_task_cosine_matrix": cosine_matrix,
        "unsurgeried_sum": sum_evidence,
    }


def _parameter_vector_from_state(
    state: Mapping[str, torch.Tensor],
) -> torch.Tensor:
    return torch.cat(
        [state[name].detach().cpu().contiguous().reshape(-1).to(torch.float64) for name in PARAMETER_NAMES]
    )


def _task_delta_projections(
    tasks: Mapping[str, Mapping[str, torch.Tensor]],
    delta: Mapping[str, torch.Tensor],
) -> dict[str, float]:
    delta_vector, _ = _flatten_gradient_map(delta)
    result = {}
    for task in TASK_ORDER:
        gradient, _ = _flatten_gradient_map(tasks[task])
        # Gradients are loss gradients; favorable policy ascent is -g dot delta.
        result[task] = float(torch.dot(-gradient, delta_vector))
    return result


def _custom_stage2_step(
    *,
    arm: str,
    loaded: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    partition: Mapping[str, Sequence[int]],
    optimizer: torch.optim.Adam,
    update_ordinal: int,
    stage2_start: Mapping[str, torch.Tensor],
) -> dict[str, Any]:
    model = loaded["model"]
    named = dict(model.named_parameters())
    before_state = {
        name: value.detach().clone() for name, value in model.state_dict().items()
    }
    frozen_before = {
        name: value.detach().clone()
        for name, value in model.state_dict().items()
        if name not in PARAMETER_NAMES
    }
    bundle = _gradient_bundle(loaded, prepare_receipt, partition)
    raw = _raw_gradient_diagnostics(
        bundle["task_gradients"], bundle["direct_policy_gradient"]
    )
    if arm == "treatment_pcgrad":
        policy_gradient, surgery = pcgrad_project(
            bundle["task_gradients"],
            bundle["direct_policy_gradient"],
            update_ordinal=update_ordinal,
        )
    elif arm == "control_vanilla":
        policy_gradient = {
            name: value.detach().clone()
            for name, value in bundle["direct_policy_gradient"].items()
        }
        surgery = {
            "update_ordinal": update_ordinal,
            "projection_order": None,
            "projection_events": [],
            "task_changed_by_surgery": [],
            "surgery_nonzero": False,
            **raw,
        }
    else:
        raise ValueError("unknown Stage-2 arm")
    step = apply_policy_kl_clip_adam(
        model=model,
        optimizer=optimizer,
        policy_gradient=policy_gradient,
        kl_gradient=bundle["anchor_kl_gradient"],
    )
    if any(
        not torch.equal(value, model.state_dict()[name])
        for name, value in frozen_before.items()
    ):
        raise ValueError("Stage-2 changed a frozen parameter")
    expected_steps = {
        **{name: update_ordinal for name in PARAMETER_NAMES},
        **{name: 1 for name in base.STAGE1_TRAINABLE_NAMES},
    }
    steps = optimizer_step_states(optimizer, model)
    if steps != expected_steps:
        raise ValueError("Stage-2 optimizer step state mismatch")
    actual_delta = {
        name: named[name].detach() - before_state[name] for name in PARAMETER_NAMES
    }
    cumulative_delta = {
        name: named[name].detach() - stage2_start[name] for name in PARAMETER_NAMES
    }
    combined_preclip = torch.cat(
        [
            (policy_gradient[name] + bundle["anchor_kl_gradient"][name])
            .detach().cpu().contiguous().reshape(-1)
            for name in PARAMETER_NAMES
        ]
    ).to(torch.float32)
    clip_layout = [
        {
            "name": name, "shape": list(named[name].shape),
            "numel": named[name].numel(), "dtype": str(named[name].dtype),
        }
        for name in PARAMETER_NAMES
    ]
    _expected_postclip, _preclip_norm, clip_coefficient_tensor = (
        _exact_postclip_flat(combined_preclip, clip_layout)
    )
    if not torch.equal(
        _expected_postclip,
        torch.tensor(
            step["combined_postclip_gradient_values_float32"],
            dtype=torch.float32, device="cpu",
        ),
    ):
        raise ValueError("production post-clip gradient differs from PyTorch contract")
    clip_coefficient = float(clip_coefficient_tensor)
    actual_vector = torch.cat(
        [actual_delta[name].detach().cpu().contiguous().reshape(-1) for name in PARAMETER_NAMES]
    ).to(torch.float32)
    cumulative_vector = torch.cat(
        [cumulative_delta[name].detach().cpu().contiguous().reshape(-1) for name in PARAMETER_NAMES]
    ).to(torch.float32)
    direct_vector, _ = _flatten_gradient_map(bundle["direct_policy_gradient"])
    anchor_vector = torch.cat(
        [
            bundle["anchor_kl_gradient"][name]
            .detach().cpu().contiguous().reshape(-1)
            for name in PARAMETER_NAMES
        ]
    ).to(torch.float32)
    return {
        "arm": arm,
        "stage_2_update_ordinal": update_ordinal,
        "optimizer_step_ordinal": 1 + update_ordinal,
        "optimizer_state_steps": steps,
        "loss": float(bundle["total_loss"].detach()),
        "policy_loss": float(bundle["direct_policy_loss"].detach()),
        "anchor_kl_loss": float(bundle["anchor_kl_contribution"].detach()),
        "entropy": float(bundle["entropy"].detach()),
        "clip_active_row_count": len(bundle["clip_active_ordinals"]),
        "clip_active_row_ordinals": list(bundle["clip_active_ordinals"]),
        "PPO_ratio_minimum": min(bundle["ratios"]),
        "PPO_ratio_maximum": max(bundle["ratios"]),
        "optimizer_step": {key: value for key, value in step.items() if key != "parameter_delta"},
        "tensor_evidence": {
            "raw_task_gradients_float64": copy.deepcopy(
                surgery["raw_task_gradients_float64"]
            ),
            "projected_task_gradients_float64": copy.deepcopy(
                surgery.get("projected_task_gradients_float64")
                or surgery["raw_task_gradients_float64"]
            ),
            "direct_policy_gradient_float64": direct_vector.tolist(),
            "anchor_kl_gradient_float32": anchor_vector.tolist(),
            "combined_preclip_gradient_float32": combined_preclip.tolist(),
            "combined_postclip_gradient_float32": copy.deepcopy(
                step["combined_postclip_gradient_values_float32"]
            ),
            "postclip_coefficient_float32": float(clip_coefficient),
            "actual_parameter_delta_float32": actual_vector.tolist(),
            "cumulative_parameter_delta_float32": cumulative_vector.tolist(),
            "policy_parameter_state_after": {
                name: named[name].detach().cpu().clone() for name in PARAMETER_NAMES
            },
            "optimizer_state_after": copy.deepcopy(optimizer.state_dict()),
            "optimizer_step_counters": copy.deepcopy(steps),
        },
        "gradient_diagnostics": surgery,
        "actual_adam_step_task_projections": _task_delta_projections(
            bundle["task_gradients"], actual_delta
        ),
        "cumulative_delta_task_projections": _task_delta_projections(
            bundle["task_gradients"], cumulative_delta
        ),
        "parameter_hashes": _model_parameter_hashes(model),
        "parameter_diffs_from_previous_step": base._parameter_diff_records(model, before_state),
        "parameter_diffs_from_stage2_start": base._parameter_diff_records(model, stage2_start),
        "nonfinite_count": 0,
    }


def validate_control_decomposition(
    actual_legacy_preclip: torch.Tensor,
    split_direct_plus_anchor: torch.Tensor,
) -> dict[str, Any]:
    """Validate the v5 diagnostic split against the authoritative legacy VJP."""

    if (
        not torch.is_tensor(actual_legacy_preclip)
        or not torch.is_tensor(split_direct_plus_anchor)
        or actual_legacy_preclip.dtype != torch.float32
        or split_direct_plus_anchor.dtype != torch.float32
        or actual_legacy_preclip.device.type != "cpu"
        or split_direct_plus_anchor.device.type != "cpu"
        or actual_legacy_preclip.shape != split_direct_plus_anchor.shape
    ):
        raise ValueError("control decomposition tensors must be shape-equal CPU float32")
    nonfinite = int((~torch.isfinite(actual_legacy_preclip)).sum()) + int(
        (~torch.isfinite(split_direct_plus_anchor)).sum()
    )
    if nonfinite:
        raise FloatingPointError("control decomposition is nonfinite")
    difference = (
        split_direct_plus_anchor.to(torch.float64)
        - actual_legacy_preclip.to(torch.float64)
    )
    maximum = float(difference.abs().max()) if difference.numel() else 0.0
    difference_l2 = float(_vector_norm(difference))
    actual_l2 = float(_vector_norm(actual_legacy_preclip.to(torch.float64)))
    l2_bound = max(
        CONTROL_DECOMPOSITION_RELATIVE_L2_ERROR * actual_l2,
        CONTROL_DECOMPOSITION_MINIMUM_L2_ERROR,
    )
    passed = (
        maximum <= CONTROL_DECOMPOSITION_MAX_ABSOLUTE_ERROR
        and difference_l2 <= l2_bound
        and nonfinite == 0
    )
    evidence = {
        "maximum_absolute_error": maximum,
        "maximum_absolute_error_bound_inclusive": (
            CONTROL_DECOMPOSITION_MAX_ABSOLUTE_ERROR
        ),
        "difference_l2": difference_l2,
        "actual_legacy_preclip_l2": actual_l2,
        "l2_error_bound_inclusive": l2_bound,
        "nonfinite_count": nonfinite,
        "both_bounds_required": True,
        "passed": passed,
    }
    if not passed:
        raise ValueError("control split decomposition exceeds v5 tolerance")
    return evidence


def _control_pre_step_identity_v5(
    parameters: Mapping[str, torch.Tensor], optimizer_state: Mapping[str, Any]
) -> dict[str, Any]:
    if tuple(parameters) != PARAMETER_NAMES:
        raise ValueError("control pre-step parameter order mismatch")
    layout = []
    hashes = {}
    for name in PARAMETER_NAMES:
        value = parameters[name]
        if (
            not torch.is_tensor(value)
            or value.device.type != "cpu"
            or value.dtype != torch.float32
            or not torch.isfinite(value).all()
        ):
            raise ValueError("control pre-step parameter domain mismatch")
        layout.append({
            "name": name,
            "shape": list(value.shape),
            "dtype": str(value.dtype),
            "raw_byte_sha256": _tensor_sha256_v2(value),
        })
        hashes[name] = _tensor_sha256_v2(value)
    optimizer_digest = _tensor_digest_record_v2(optimizer_state)
    return {
        "parameter_order": list(PARAMETER_NAMES),
        "parameter_layout": layout,
        "parameter_raw_byte_sha256": hashes,
        "parameter_state_sha256": canonical_sha256(
            _tensor_digest_record_v2(parameters)
        ),
        "optimizer_state_sha256": canonical_sha256(optimizer_digest),
    }


def _audit_guard_snapshot_v5(
    model: torch.nn.Module, optimizer: torch.optim.Optimizer
) -> dict[str, Any]:
    return {
        "model_state": {
            name: value.detach().cpu().clone()
            for name, value in model.state_dict().items()
        },
        "optimizer_state": copy.deepcopy(optimizer.state_dict()),
        "grad_state": {
            name: (
                None if parameter.grad is None
                else parameter.grad.detach().cpu().clone()
            )
            for name, parameter in model.named_parameters()
        },
        "cpu_rng_state": torch.get_rng_state().clone(),
    }


def _audit_guard_hashes_v5(snapshot: Mapping[str, Any]) -> dict[str, str]:
    return {
        name: canonical_sha256(_tensor_digest_record_v2(value))
        for name, value in snapshot.items()
    }


def _isolated_loaded_v5(
    loaded: Mapping[str, Any], pre_step_model_state: Mapping[str, torch.Tensor]
) -> dict[str, Any]:
    isolated = dict(loaded)
    isolated_model = copy.deepcopy(loaded["model"])
    isolated_model.load_state_dict(pre_step_model_state)
    for parameter in isolated_model.parameters():
        parameter.grad = None
    isolated["model"] = isolated_model
    return isolated


def _isolated_rowwise_joint_vjp_v5(
    loaded: Mapping[str, Any], prepare_receipt: Mapping[str, Any]
) -> dict[str, torch.Tensor]:
    """Rebuild the inherited rowwise joint loss on an isolated model."""

    model = loaded["model"]
    base._set_trainability(model, stage=2)
    execution_fixed = loaded.get("execution_fixed_inputs")
    if not isinstance(execution_fixed, Mapping) or execution_fixed.get(
        "gae_recomputation_count"
    ) != 1:
        raise ValueError("isolated VJP fixed inputs are missing")
    losses: list[torch.Tensor] = []
    for ordinal, ((episode, row), fixed) in enumerate(
        zip(loaded["rows"], prepare_receipt["rows"])
    ):
        if (
            fixed["ppo_row_ordinal"] != ordinal
            or fixed["episode_id"] != str(episode["episode_id"])
            or fixed["decision_index"] != int(row["decision_index"])
            or fixed["sampled_index"] != int(row["final_action"][0])
            or int(execution_fixed["sampled_indices"][ordinal])
            != int(fixed["sampled_index"])
        ):
            raise ValueError("isolated rowwise VJP row identity mismatch")
        normalized_value = float(
            execution_fixed["normalized_advantages_float32"][ordinal]
        )
        old_logprob_value = float(
            execution_fixed["behavior_logprobabilities_float64"][ordinal]
        )
        if (
            normalized_value
            != float(fixed["fixed_normalized_advantage_float32"])
            or old_logprob_value != float(fixed["behavior_logprob_float64"])
        ):
            raise ValueError("isolated rowwise VJP fixed row changed")
        state = torch.tensor(row["state_vector"], dtype=torch.float32, device="cpu")
        actions = torch.tensor(
            row["action_vectors"], dtype=torch.float32, device="cpu"
        )
        residuals, value = model(state, actions)
        probabilities, log_probabilities = _torch_behavior_distribution(
            residuals,
            teacher_index=int(row["teacher_action"][0]),
            reference_config=loaded["reference_config"],
        )
        anchor_kl = _torch_behavior_anchor_kl(
            residuals,
            teacher_index=int(row["teacher_action"][0]),
            reference_config=loaded["reference_config"],
        )
        selected = int(row["final_action"][0])
        old_logprob = torch.tensor(old_logprob_value, dtype=torch.float32)
        advantage = torch.tensor(normalized_value, dtype=torch.float32)
        ratio = torch.exp(log_probabilities[selected] - old_logprob)
        unclipped = ratio * advantage
        clipped = torch.clamp(
            ratio,
            1.0 - base.TWO_STAGE_PPO_CONFIG.clip_ratio,
            1.0 + base.TWO_STAGE_PPO_CONFIG.clip_ratio,
        ) * advantage
        policy_loss = -torch.minimum(unclipped, clipped)
        loss = (
            policy_loss
            + base.TWO_STAGE_PPO_CONFIG.anchor_kl_initial_coef * anchor_kl
        )
        inherited._finite_tensors_or_raise(
            (
                residuals, value, probabilities, log_probabilities,
                anchor_kl, policy_loss, loss,
            ),
            label=f"isolated Stage-2 row {ordinal}",
        )
        losses.append(loss)
    if len(losses) != EXPECTED_ROWS:
        raise ValueError("isolated rowwise VJP did not contain exactly 830 rows")
    total_loss = torch.stack(losses).mean()
    named = dict(model.named_parameters())
    values = torch.autograd.grad(
        total_loss,
        [named[name] for name in PARAMETER_NAMES],
        retain_graph=False,
        create_graph=False,
        allow_unused=False,
    )
    result = {
        name: value.detach().cpu().clone()
        for name, value in zip(PARAMETER_NAMES, values)
    }
    if any(
        result[name].dtype != named[name].dtype
        or result[name].shape != named[name].shape
        or not torch.isfinite(result[name]).all()
        for name in PARAMETER_NAMES
    ):
        raise ValueError("isolated rowwise VJP has an invalid gradient")
    return result


def _isolated_control_diagnostics_v5(
    *,
    loaded: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    partition: Mapping[str, Sequence[int]],
    optimizer: torch.optim.Optimizer,
) -> dict[str, Any]:
    model = loaded["model"]
    pre_step_model_state = {
        name: value.detach().cpu().clone()
        for name, value in model.state_dict().items()
    }
    guard_before = _audit_guard_snapshot_v5(model, optimizer)
    rowwise_loaded = _isolated_loaded_v5(loaded, pre_step_model_state)
    rowwise = _isolated_rowwise_joint_vjp_v5(
        rowwise_loaded, prepare_receipt
    )
    split_loaded = _isolated_loaded_v5(loaded, pre_step_model_state)
    bundle = _gradient_bundle(split_loaded, prepare_receipt, partition)
    raw = _raw_gradient_diagnostics(
        bundle["task_gradients"], bundle["direct_policy_gradient"]
    )
    guard_after = _audit_guard_snapshot_v5(model, optimizer)
    if not _nested_byte_exact_v2(guard_before, guard_after):
        raise ValueError("isolated control audit mutated live training state or RNG")
    rowwise_vector = torch.cat([
        rowwise[name].contiguous().reshape(-1) for name in PARAMETER_NAMES
    ]).to(torch.float32)
    direct_vector, _ = _flatten_gradient_map(bundle["direct_policy_gradient"])
    anchor_vector = torch.cat([
        bundle["anchor_kl_gradient"][name].detach().cpu().contiguous().reshape(-1)
        for name in PARAMETER_NAMES
    ]).to(torch.float32)
    split_vector = direct_vector.to(torch.float32) + anchor_vector
    decomposition = validate_control_decomposition(
        rowwise_vector, split_vector
    )
    before_hashes = _audit_guard_hashes_v5(guard_before)
    after_hashes = _audit_guard_hashes_v5(guard_after)
    if before_hashes != after_hashes:
        raise ValueError("isolated control audit guard hashes differ")
    return {
        "bundle": bundle,
        "raw": raw,
        "rowwise_gradient": rowwise,
        "rowwise_vector": rowwise_vector,
        "direct_vector": direct_vector,
        "anchor_vector": anchor_vector,
        "split_vector": split_vector,
        "decomposition": decomposition,
        "audit_guard_hashes_before": before_hashes,
        "audit_guard_hashes_after": after_hashes,
    }


def _control_reference_step(
    *,
    loaded: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    partition: Mapping[str, Sequence[int]],
    state: Mapping[str, Any],
    update_ordinal: int,
) -> dict[str, Any]:
    """Run one authoritative inherited rowwise legacy control update."""

    model = loaded["model"]
    base._set_trainability(model, stage=2)
    named_before = dict(model.named_parameters())
    before = {
        name: value.detach().clone() for name, value in model.state_dict().items()
    }
    pre_step_policy_state = {
        name: named_before[name].detach().cpu().clone() for name in PARAMETER_NAMES
    }
    pre_step_optimizer_state = copy.deepcopy(state["optimizer"].state_dict())
    pre_step_identity = _control_pre_step_identity_v5(
        pre_step_policy_state, pre_step_optimizer_state
    )
    diagnostics = _isolated_control_diagnostics_v5(
        loaded=loaded,
        prepare_receipt=prepare_receipt,
        partition=partition,
        optimizer=state["optimizer"],
    )
    expected = diagnostics["rowwise_gradient"]
    captured: dict[str, torch.Tensor] = {}
    hook_counts = {name: 0 for name in PARAMETER_NAMES}
    handles = []

    def capture(name: str):
        def hook(gradient: torch.Tensor) -> None:
            hook_counts[name] += 1
            if hook_counts[name] != 1:
                raise ValueError(f"control capture hook repeated: {name}")
            parameter = named_before[name]
            if (
                gradient.shape != parameter.shape
                or gradient.dtype != parameter.dtype
                or gradient.device.type != "cpu"
                or not torch.isfinite(gradient).all()
            ):
                raise ValueError(f"control capture hook gradient invalid: {name}")
            value = gradient.detach().cpu().clone()
            if not torch.equal(value, expected[name]):
                raise ValueError(
                    f"control actual preclip differs from isolated rowwise VJP: {name}"
                )
            captured[name] = value
            if len(captured) == len(PARAMETER_NAMES):
                actual = torch.cat([
                    captured[item].contiguous().reshape(-1)
                    for item in PARAMETER_NAMES
                ]).to(torch.float32)
                current = validate_control_decomposition(
                    actual, diagnostics["split_vector"]
                )
                if current != diagnostics["decomposition"]:
                    raise ValueError("control decomposition changed at live backward")
            return None

        return hook

    inherited_stage2_limit = base.STAGE2_UPDATES
    try:
        if update_ordinal > inherited_stage2_limit:
            base.STAGE2_UPDATES = STAGE2_UPDATES
        for name in PARAMETER_NAMES:
            handles.append(named_before[name].register_hook(capture(name)))
        report = base._stage_full_batch_step(
            stage=2,
            stage_2_update_ordinal=update_ordinal,
            loaded=loaded,
            prepare_receipt=prepare_receipt,
            optimizer=state["optimizer"],
            initial_parameters=state["initial_parameters"],
            progress=state["progress"],
            stage_2_start_parameters=state["stage2_start_parameters"],
        )
    finally:
        base.STAGE2_UPDATES = inherited_stage2_limit
        for handle in handles:
            handle.remove()
    if set(captured) != set(PARAMETER_NAMES) or any(
        hook_counts[name] != 1 for name in PARAMETER_NAMES
    ):
        raise ValueError("control capture hooks did not fire exactly once")
    actual_delta = {
        name: dict(model.named_parameters())[name].detach() - before[name]
        for name in PARAMETER_NAMES
    }
    cumulative = {
        name: dict(model.named_parameters())[name].detach()
        - state["stage2_start_parameters"][name]
        for name in PARAMETER_NAMES
    }
    bundle = diagnostics["bundle"]
    raw = diagnostics["raw"]
    direct_vector = diagnostics["direct_vector"]
    anchor_vector = diagnostics["anchor_vector"]
    split_vector = diagnostics["split_vector"]
    combined_preclip = torch.cat([
        captured[name].contiguous().reshape(-1) for name in PARAMETER_NAMES
    ]).to(torch.float32)
    if not torch.equal(combined_preclip, diagnostics["rowwise_vector"]):
        raise ValueError("captured control preclip is not the isolated rowwise VJP")
    decomposition = validate_control_decomposition(
        combined_preclip, split_vector
    )
    named = dict(model.named_parameters())
    if any(named[name].grad is None for name in PARAMETER_NAMES):
        raise ValueError("control post-clip gradient was not retained by Adam")
    postclip_vector = torch.cat(
        [
            named[name].grad.detach().cpu().contiguous().reshape(-1)
            for name in PARAMETER_NAMES
        ]
    ).to(torch.float32)
    clip_layout = [
        {
            "name": name, "shape": list(named[name].shape),
            "numel": named[name].numel(), "dtype": str(named[name].dtype),
        }
        for name in PARAMETER_NAMES
    ]
    _expected_postclip, _preclip_norm, clip_coefficient_tensor = (
        _exact_postclip_flat(combined_preclip, clip_layout)
    )
    if float(_preclip_norm) != report["gradient_norm_before_clipping"]:
        raise ValueError("control native preclip norm replay differs from inherited step")
    if not torch.equal(_expected_postclip, postclip_vector):
        raise ValueError("control post-clip gradient differs from PyTorch contract")
    clip_coefficient = float(clip_coefficient_tensor)
    actual_vector = torch.cat(
        [actual_delta[name].detach().cpu().contiguous().reshape(-1) for name in PARAMETER_NAMES]
    ).to(torch.float32)
    cumulative_vector = torch.cat(
        [cumulative[name].detach().cpu().contiguous().reshape(-1) for name in PARAMETER_NAMES]
    ).to(torch.float32)
    return {
        "arm": "control_vanilla",
        "stage_2_update_ordinal": update_ordinal,
        "optimizer_step_ordinal": report["optimizer_step_ordinal"],
        "optimizer_state_steps": report["optimizer_state_steps"],
        "loss": report["loss"],
        "policy_loss": report["policy_loss"],
        "anchor_kl_loss": ANCHOR_KL_COEFFICIENT * report["pre_step_mean_anchor_kl"],
        "entropy": report["entropy"],
        "clip_active_row_count": len(bundle["clip_active_ordinals"]),
        "clip_active_row_ordinals": list(bundle["clip_active_ordinals"]),
        "PPO_ratio_minimum": min(bundle["ratios"]),
        "PPO_ratio_maximum": max(bundle["ratios"]),
        "optimizer_step": {
            "ordering": ["ordinary_total_loss_backward", "global_norm_clip", "adam_step"],
            "global_gradient_norm_before_clip": report["gradient_norm_before_clipping"],
            "per_parameter_gradient_norm_before_clipping": report[
                "per_parameter_gradient_norm_before_clipping"
            ],
            "per_parameter_gradient_norm_after_clipping": report[
                "per_parameter_gradient_norm_after_clipping"
            ],
        },
        "tensor_evidence": {
            "raw_task_gradients_float64": copy.deepcopy(
                raw["raw_task_gradients_float64"]
            ),
            "direct_policy_gradient_float64": direct_vector.tolist(),
            "anchor_kl_gradient_float32": anchor_vector.tolist(),
            "combined_preclip_gradient_float32": combined_preclip.tolist(),
            "authoritative_legacy_preclip_gradient_float32": (
                combined_preclip.tolist()
            ),
            "authoritative_legacy_preclip_sha256": _tensor_sha256_v2(
                combined_preclip
            ),
            "independent_rowwise_joint_vjp_float32": diagnostics[
                "rowwise_vector"
            ].tolist(),
            "independent_rowwise_joint_vjp_sha256": _tensor_sha256_v2(
                diagnostics["rowwise_vector"]
            ),
            "independent_rowwise_joint_vjp_parameter_sha256": {
                name: _tensor_sha256_v2(diagnostics["rowwise_gradient"][name])
                for name in PARAMETER_NAMES
            },
            "split_direct_plus_anchor_gradient_float32": split_vector.tolist(),
            "control_decomposition": copy.deepcopy(decomposition),
            "pre_step_policy_parameter_state": pre_step_policy_state,
            "pre_step_optimizer_state": pre_step_optimizer_state,
            "pre_step_identity": pre_step_identity,
            "isolated_audit_guard_hashes_before": diagnostics[
                "audit_guard_hashes_before"
            ],
            "isolated_audit_guard_hashes_after": diagnostics[
                "audit_guard_hashes_after"
            ],
            "capture_hook_counts": copy.deepcopy(hook_counts),
            "combined_postclip_gradient_float32": postclip_vector.tolist(),
            "postclip_coefficient_float32": float(clip_coefficient),
            "actual_parameter_delta_float32": actual_vector.tolist(),
            "cumulative_parameter_delta_float32": cumulative_vector.tolist(),
            "policy_parameter_state_after": {
                name: named[name].detach().cpu().clone() for name in PARAMETER_NAMES
            },
            "optimizer_state_after": copy.deepcopy(state["optimizer"].state_dict()),
            "optimizer_step_counters": copy.deepcopy(
                report["optimizer_state_steps"]
            ),
        },
        "gradient_diagnostics": {
            "update_ordinal": update_ordinal,
            "projection_order": None,
            "projection_events": [],
            "task_changed_by_surgery": [],
            "surgery_nonzero": False,
            **raw,
        },
        "actual_adam_step_task_projections": _task_delta_projections(
            bundle["task_gradients"], actual_delta
        ),
        "cumulative_delta_task_projections": _task_delta_projections(
            bundle["task_gradients"], cumulative
        ),
        "parameter_hashes": _model_parameter_hashes(model),
        "parameter_diffs_from_previous_step": report[
            "parameter_diffs_from_previous_step"
        ],
        "parameter_diffs_from_stage2_start": report[
            "parameter_diffs_from_stage_start"
        ],
        "legacy_step_report": report,
        "nonfinite_count": report[
            "nonfinite_value_gradient_optimizer_or_parameter_count"
        ],
    }


def _apply_clip_milestone_gate(
    safety: Mapping[str, Any], step: Mapping[str, Any], *, update_ordinal: int
) -> dict[str, Any]:
    result = copy.deepcopy(dict(safety))
    if update_ordinal in DIAGNOSTIC_UPDATES and step["clip_active_row_count"] != 0:
        failures = list(result.get("global_failures") or [])
        failures.append("global:PPO_clip_active_rows")
        result["global_failures"] = failures
        result["safety_pass"] = False
        result["hard_stop"] = True
        result["accepted_at_stage"] = False
    result["PPO_clip_active_row_count"] = step["clip_active_row_count"]
    result["PPO_clip_required_zero"] = update_ordinal in DIAGNOSTIC_UPDATES
    return result


def _family_alignment_summaries(
    prepare_receipt: Mapping[str, Any],
    movements: Sequence[float],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for family in prepare_receipt["action_families"]["families"]:
        if not family["qualifying"]:
            continue
        for polarity, ordinals in (
            ("positive", family["positive_ordinals"]),
            ("negative", family["negative_ordinals"]),
        ):
            result[f"{family['name']}:{polarity}"] = lower_empirical_median(
                [movements[index] for index in ordinals]
            )
    if len(result) != 12:
        raise ValueError("family alignment summary count mismatch")
    return result


def _alignment_summary_for_metrics(
    prepare_receipt: Mapping[str, Any],
    metrics: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    movements = [float(row["oriented_sampled_probability_delta"]) for row in metrics]
    rows = prepare_receipt["rows"]
    monte_carlo = prepare_receipt["monte_carlo_advantages_float64"]
    partition = _fixed_partition_from_receipt(prepare_receipt)
    priority = {
        task: alignment_weighting_summary(
            movements, rows, monte_carlo, ordinals=partition[task]
        )
        for task in PRIORITY_TASKS
    }
    stable = prepare_receipt["sign_stable_611_ordinals"]
    return {
        "priority": priority,
        "global": alignment_weighting_summary(movements, rows, monte_carlo),
        "all_12_family_polarity_lower_medians": _family_alignment_summaries(
            prepare_receipt, movements
        ),
        "sign_stable_611_lower_empirical_median": lower_empirical_median(
            [movements[index] for index in stable]
        ),
    }


def _difference_alignment_summary(
    prepare_receipt: Mapping[str, Any],
    control: Sequence[Mapping[str, Any]],
    treatment: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    differences = [
        float(right["oriented_sampled_probability_delta"])
        - float(left["oriented_sampled_probability_delta"])
        for left, right in zip(control, treatment)
    ]
    rows = prepare_receipt["rows"]
    monte_carlo = prepare_receipt["monte_carlo_advantages_float64"]
    partition = _fixed_partition_from_receipt(prepare_receipt)
    return {
        "priority": {
            task: alignment_weighting_summary(
                differences, rows, monte_carlo, ordinals=partition[task]
            )
            for task in PRIORITY_TASKS
        }
    }


def _control_legacy_compact(
    *,
    step: Mapping[str, Any],
    metrics: Sequence[Mapping[str, Any]],
    safety: Mapping[str, Any],
    value_identity: Mapping[str, Any],
    frozen_evidence: Mapping[str, Any],
    previous_record_hash: str,
    update_ordinal: int,
) -> dict[str, Any]:
    report = step["legacy_step_report"]
    outputs = base._ordered_output_hashes(metrics)
    compact = {
        "stage_2_update_ordinal": update_ordinal,
        "optimizer_step_ordinal": report["optimizer_step_ordinal"],
        "optimizer_state_steps": report["optimizer_state_steps"],
        "loss": report["loss"],
        "policy_loss": report["policy_loss"],
        "anchor_kl_loss": ANCHOR_KL_COEFFICIENT * report["pre_step_mean_anchor_kl"],
        "entropy": report["entropy"],
        "gradient_norm_before_clipping": report[
            "gradient_norm_before_clipping"
        ],
        "per_parameter_gradient_norm_before_clipping": report[
            "per_parameter_gradient_norm_before_clipping"
        ],
        "per_parameter_gradient_norm_after_clipping": report[
            "per_parameter_gradient_norm_after_clipping"
        ],
        "parameter_diffs_from_initial": report["parameter_diffs_from_initial"],
        "parameter_diffs_from_previous_step": report[
            "parameter_diffs_from_previous_step"
        ],
        "parameter_diffs_from_stage_start": report[
            "parameter_diffs_from_stage_start"
        ],
        "safety": safety,
        "value_identity": value_identity,
        "frozen_encoder_value_contract": frozen_evidence,
        **outputs,
        "raw_rows_persisted": update_ordinal in base.DIAGNOSTIC_UPDATE_ORDINALS,
        "previous_record_hash": previous_record_hash,
        "measurement_timing": {
            "pre_step": {
                "loss": report["loss"],
                "policy_loss": report["policy_loss"],
                "anchor_kl_contribution": ANCHOR_KL_COEFFICIENT
                * report["pre_step_mean_anchor_kl"],
                "entropy": report["entropy"],
                "gradient_norm_before_clipping": report[
                    "gradient_norm_before_clipping"
                ],
                "per_parameter_gradient_norm_before_clipping": report[
                    "per_parameter_gradient_norm_before_clipping"
                ],
                "per_parameter_gradient_norm_after_clipping": report[
                    "per_parameter_gradient_norm_after_clipping"
                ],
            },
            "post_step": {
                "optimizer_state_steps": report["optimizer_state_steps"],
                "parameter_diffs_from_initial": report[
                    "parameter_diffs_from_initial"
                ],
                "parameter_diffs_from_fixed_stage_2_start": report[
                    "parameter_diffs_from_stage_start"
                ],
                "parameter_diffs_from_previous_step": report[
                    "parameter_diffs_from_previous_step"
                ],
                "safety": safety,
                **outputs,
            },
        },
    }
    compact["record_hash"] = canonical_sha256(compact)
    return compact


def _run_duplicate_treatment(
    *,
    loaded_template: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    stage1_state: Mapping[str, Any],
    partition: Mapping[str, Sequence[int]],
) -> dict[str, Any]:
    loaded = inherited._load_validated_inputs()
    loaded["execution_fixed_inputs"] = copy.deepcopy(
        loaded_template["execution_fixed_inputs"]
    )
    loaded["model"].load_state_dict(stage1_state["model_state"])
    optimizer = base._new_actor_adam(loaded["model"])
    optimizer.load_state_dict(copy.deepcopy(stage1_state["optimizer_state"]))
    start = {
        name: value.detach().clone()
        for name, value in loaded["model"].state_dict().items()
    }
    terminal_step = None
    metrics = None
    record_chain: list[str] = []
    for update in range(1, STAGE2_UPDATES + 1):
        terminal_step = _custom_stage2_step(
            arm="treatment_pcgrad",
            loaded=loaded,
            prepare_receipt=prepare_receipt,
            partition=partition,
            optimizer=optimizer,
            update_ordinal=update,
            stage2_start=start,
        )
        metrics = base._measure_stage(
            loaded, prepare_receipt, stage=2,
            stage_2_update_ordinal=update,
        )
        terminal_step["tensor_evidence"]["ordered_outputs"] = (
            _ordered_output_tensor_evidence(metrics)
        )
        record_chain.append(_raw_step_record_sha256_v2(
            _runtime_raw_step_item_v2(
                terminal_step["tensor_evidence"], arm="treatment_pcgrad"
            ),
            arm="treatment_pcgrad", update_ordinal=update,
        ))
    if metrics is None:
        raise AssertionError("duplicate treatment retained no terminal outputs")
    identity = {
        "parameter_hashes": _model_parameter_hashes(loaded["model"]),
        "optimizer_canonical": optimizer_canonical_record(
            optimizer, loaded["model"]
        ),
        "output_hashes": base._ordered_output_hashes(metrics),
        "terminal_step_sha256": record_chain[-1],
        "per_update_record_chain_sha256": canonical_sha256(record_chain),
    }
    return {
        "identity": identity,
        "tensor_evidence": {
            "model_state": {
                name: value.detach().cpu().clone()
                for name, value in loaded["model"].state_dict().items()
            },
            "optimizer_state": copy.deepcopy(optimizer.state_dict()),
            "ordered_outputs": _ordered_output_tensor_evidence(metrics),
            "per_update_record_hashes": record_chain,
        },
    }


def run_matched_arms(
    prepare_receipt: Mapping[str, Any],
    *,
    duplicate_treatment: bool = True,
) -> dict[str, Any]:
    """Execute the complete matched Stage1 + 64-update two-arm schedule."""

    validate_prepare_receipt(prepare_receipt)
    partition = _fixed_partition_from_receipt(prepare_receipt)
    loaded_arms = _load_execution_arms(prepare_receipt)
    arms = {
        name: _stage1_arm(loaded, prepare_receipt)
        for name, loaded in loaded_arms.items()
    }
    stage1_equality = validate_stage1_arm_equality(
        arms["control_vanilla"]["stage1_equality_evidence"],
        arms["treatment_pcgrad"]["stage1_equality_evidence"],
    )
    stage1_duplicate_state = {
        "model_state": copy.deepcopy(arms["treatment_pcgrad"]["model"].state_dict()),
        "optimizer_state": copy.deepcopy(
            arms["treatment_pcgrad"]["optimizer"].state_dict()
        ),
    }
    if any(arm["stage1_safety"]["hard_stop"] for arm in arms.values()):
        return {
            "arms": arms,
            "stage1_equality": stage1_equality,
            "completed_optimizer_steps_per_arm": {
                "control_vanilla": 1,
                "treatment_pcgrad": 1,
            },
            "all_safety_gates_pass": False,
            "safety_stop": {"after_stage1": True},
        }
    initial_frozen_hashes = {
        name: _tensor_sha256_v2(value)
        for name, value in arms["control_vanilla"]["initial_parameters"].items()
        if name.startswith(("state_encoder.", "action_encoder.", base.VALUE_PREFIX))
    }
    update_records = {name: [] for name in arms}
    full_diagnostics = {name: {} for name in arms}
    alignment = {
        "control_vanilla": {},
        "treatment_pcgrad": {},
        "treatment_minus_control": {},
    }
    control_previous_hash = arms["control_vanilla"]["stage1_record_sha256"]
    control_reference_gate = None
    all_safety = True
    safety_stop = None
    touched_first16: set[str] = set()
    surgery_nonzero = False
    cumulative_projections: dict[str, dict[str, float]] = {}
    for update in range(1, STAGE2_UPDATES + 1):
        steps: dict[str, dict[str, Any]] = {}
        control_state = arms["control_vanilla"]
        if update <= 32:
            steps["control_vanilla"] = _control_reference_step(
                loaded=loaded_arms["control_vanilla"],
                prepare_receipt=prepare_receipt,
                partition=partition,
                state=control_state,
                update_ordinal=update,
            )
        else:
            steps["control_vanilla"] = _custom_stage2_step(
                arm="control_vanilla",
                loaded=loaded_arms["control_vanilla"],
                prepare_receipt=prepare_receipt,
                partition=partition,
                optimizer=control_state["optimizer"],
                update_ordinal=update,
                stage2_start=control_state["stage2_start_parameters"],
            )
        treatment_state = arms["treatment_pcgrad"]
        steps["treatment_pcgrad"] = _custom_stage2_step(
            arm="treatment_pcgrad",
            loaded=loaded_arms["treatment_pcgrad"],
            prepare_receipt=prepare_receipt,
            partition=partition,
            optimizer=treatment_state["optimizer"],
            update_ordinal=update,
            stage2_start=treatment_state["stage2_start_parameters"],
        )
        surgery = steps["treatment_pcgrad"]["gradient_diagnostics"]
        surgery_nonzero = surgery_nonzero or surgery["surgery_nonzero"]
        if update <= 16:
            touched_first16.update(surgery["task_changed_by_surgery"])
        if update in (48, 64):
            cumulative_projections[str(update)] = {
                task: steps["treatment_pcgrad"][
                    "cumulative_delta_task_projections"
                ][task]
                for task in PRIORITY_TASKS
            }
        metrics_by_arm: dict[str, list[dict[str, Any]]] = {}
        safety_by_arm: dict[str, dict[str, Any]] = {}
        raw_safety_by_arm: dict[str, dict[str, Any]] = {}
        for name in ("control_vanilla", "treatment_pcgrad"):
            state = arms[name]
            loaded = loaded_arms[name]
            metrics = base._measure_stage(
                loaded,
                prepare_receipt,
                stage=2,
                stage_2_update_ordinal=update,
            )
            metrics_by_arm[name] = metrics
            value = base.value_change_summary(prepare_receipt, metrics)
            frozen = base._frozen_value_contract_evidence(
                state["model"], state["optimizer"], initial_frozen_hashes
            )
            safety = base.evaluate_stage_gates(
                prepare_receipt,
                metrics,
                stage=2,
                stage_2_update_ordinal=update,
                training_nonfinite_count=steps[name]["nonfinite_count"],
                parameter_optimizer_contract_pass=True,
                value_contract_pass=(
                    value["all_rows_byte_exact_to_initial"]
                    and value["raw_value_mse_exact_to_initial"]
                    and value["aggregate_hash_exact_to_initial"]
                    and frozen["parameter_hashes_exact"]
                    and frozen["optimizer_state_absent"]
                ),
            )
            raw_safety_by_arm[name] = safety
            safety = _apply_clip_milestone_gate(
                safety, steps[name], update_ordinal=update
            )
            safety_by_arm[name] = safety
            compact = {
                "stage_2_update_ordinal": update,
                "step": steps[name],
                "safety": safety,
                "compact_830_row_alignment_summary": (
                    _alignment_summary_for_metrics(prepare_receipt, metrics)
                ),
                "value_identity": value,
                "frozen_encoder_value_contract": frozen,
                "output_hashes": base._ordered_output_hashes(metrics),
                "raw_rows_persisted": update in DIAGNOSTIC_UPDATES,
            }
            compact["record_sha256"] = canonical_sha256(
                _compact_without_tensor_evidence(compact)
            )
            update_records[name].append(compact)
            if update in DIAGNOSTIC_UPDATES:
                full_diagnostics[name][str(update)] = metrics
        if update <= 32:
            legacy = _control_legacy_compact(
                step=steps["control_vanilla"],
                metrics=metrics_by_arm["control_vanilla"],
                safety=raw_safety_by_arm["control_vanilla"],
                value_identity=update_records["control_vanilla"][-1][
                    "value_identity"
                ],
                frozen_evidence=update_records["control_vanilla"][-1][
                    "frozen_encoder_value_contract"
                ],
                previous_record_hash=control_previous_hash,
                update_ordinal=update,
            )
            control_previous_hash = legacy["record_hash"]
            if update == 32:
                optimizer_reference = optimizer_canonical_record(
                    control_state["optimizer"], control_state["model"]
                )
                outputs = base._ordered_output_hashes(
                    metrics_by_arm["control_vanilla"]
                )
                control_reference_gate = validate_control_update32(
                    {
                        "record_sha256": legacy["record_hash"],
                        **outputs,
                        "parameter_bytes_sha256": {
                            name: _model_parameter_hashes(control_state["model"])[name]
                            for name in REFERENCE_CONTROL[
                                "stage32_parameter_bytes_sha256"
                            ]
                        },
                        "optimizer_canonical_sha256": optimizer_reference[
                            "canonical_sha256"
                        ],
                        "optimizer_param_group_canonical_sha256": optimizer_reference[
                            "param_group_canonical_sha256"
                        ],
                        "optimizer_state_steps": optimizer_step_states(
                            control_state["optimizer"], control_state["model"]
                        ),
                    }
                )
        if update in (48, 64):
            for name in ("control_vanilla", "treatment_pcgrad"):
                alignment[name][str(update)] = _alignment_summary_for_metrics(
                    prepare_receipt, metrics_by_arm[name]
                )
            alignment["treatment_minus_control"][str(update)] = (
                _difference_alignment_summary(
                    prepare_receipt,
                    metrics_by_arm["control_vanilla"],
                    metrics_by_arm["treatment_pcgrad"],
                )
            )
        stop = evaluate_safety_stop(safety_by_arm)
        if stop["stop_both_arms"]:
            all_safety = False
            safety_stop = {"after_stage2_update": update, **stop}
            break
    completed = {
        name: 1 + len(update_records[name]) for name in update_records
    }
    run: dict[str, Any] = {
        "arms": arms,
        "stage1_equality": stage1_equality,
        "update_records": update_records,
        "full_830_row_diagnostics": full_diagnostics,
        "completed_optimizer_steps_per_arm": completed,
        "all_safety_gates_pass": all_safety and completed == {
            "control_vanilla": 65,
            "treatment_pcgrad": 65,
        },
        "safety_stop": safety_stop,
        "control_update32_reference": control_reference_gate,
        "mechanism": {
            "surgery_nonzero": surgery_nonzero,
            "tasks_touched_first_16": sorted(touched_first16),
            "cumulative_delta_projections": cumulative_projections,
        },
        "alignment_summaries": alignment,
        "terminal_END_controls": None,
        "duplicate_treatment_canonical_outputs_identical": False,
        "checkpoint_reload_exact": False,
        "independent_numeric_audit_pass": False,
        "root_recomputation_pass": False,
    }
    if completed == {"control_vanilla": 65, "treatment_pcgrad": 65}:
        terminal_metrics = full_diagnostics["treatment_pcgrad"]["64"]
        run["terminal_END_controls"] = terminal_end_controls(
            prepare_receipt, terminal_metrics
        )
        primary_identity = {
            "parameter_hashes": _model_parameter_hashes(
                arms["treatment_pcgrad"]["model"]
            ),
            "optimizer_canonical": optimizer_canonical_record(
                arms["treatment_pcgrad"]["optimizer"],
                arms["treatment_pcgrad"]["model"],
            ),
            "output_hashes": base._ordered_output_hashes(terminal_metrics),
            "terminal_step_sha256": _runtime_step_record_sha256_v2(
                update_records["treatment_pcgrad"][-1]["step"]
            ),
            "per_update_record_chain_sha256": canonical_sha256([
                _runtime_step_record_sha256_v2(row["step"])
                for row in update_records["treatment_pcgrad"]
            ]),
        }
        if duplicate_treatment:
            duplicate_result = _run_duplicate_treatment(
                loaded_template=loaded_arms["treatment_pcgrad"],
                prepare_receipt=prepare_receipt,
                stage1_state=stage1_duplicate_state,
                partition=partition,
            )
            duplicate = duplicate_result["identity"]
            run["duplicate_treatment_identity"] = duplicate
            run["duplicate_treatment_evidence"] = duplicate_result[
                "tensor_evidence"
            ]
            run["duplicate_treatment_canonical_outputs_identical"] = (
                canonical_json_bytes(primary_identity)
                == canonical_json_bytes(duplicate)
            )
        else:
            run["duplicate_treatment_identity"] = None
        placeholder_receipt = "0" * 64
        for name in ("control_vanilla", "treatment_pcgrad"):
            state = arms[name]
            payload = _checkpoint_payload(
                state["model"],
                state["optimizer"],
                arm=name,
                execution_spec_sha256="0" * 64,
                receipt_sha256=placeholder_receipt,
            )
            _validate_checkpoint_payload(
                payload,
                state["model"],
                state["optimizer"],
                arm=name,
                execution_spec_sha256="0" * 64,
                receipt_sha256=placeholder_receipt,
            )
        run["checkpoint_reload_exact"] = True
    run["gates"] = evaluate_terminal_gates(run, prepare_receipt)
    return run


def _jsonl_bytes(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row, newline=True) for row in rows)


def _tensor_digest_record_v2(value: Any) -> Any:
    if torch.is_tensor(value):
        return {
            "kind": "tensor", "dtype": str(value.dtype),
            "shape": list(value.shape), "sha256": _tensor_sha256_v2(value),
        }
    if isinstance(value, Mapping):
        rows = [
            {
                "key_type": type(key).__name__, "key": repr(key),
                "value": _tensor_digest_record_v2(item),
            }
            for key, item in value.items()
        ]
        rows.sort(key=lambda row: (row["key_type"], row["key"]))
        return {"kind": "mapping", "items": rows}
    if isinstance(value, (list, tuple)):
        return {
            "kind": type(value).__name__,
            "items": [_tensor_digest_record_v2(item) for item in value],
        }
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite primitive in raw step identity")
    if value is None or isinstance(value, (bool, int, float, str)):
        return {"kind": type(value).__name__, "value": value}
    raise TypeError(f"unsupported raw step identity value: {type(value).__name__}")


RAW_STEP_CHAIN_FIELDS = (
    "raw_task_gradients", "direct_policy_gradient", "anchor_kl_gradient",
    "combined_preclip_gradient", "combined_postclip_gradient",
    "postclip_coefficient", "ordered_outputs",
    "actual_parameter_delta", "cumulative_parameter_delta",
    "policy_parameter_state_after", "optimizer_state_after",
    "optimizer_step_counters",
)
CONTROL_LEGACY_RAW_STEP_CHAIN_FIELDS = (
    "authoritative_legacy_preclip_gradient",
    "authoritative_legacy_preclip_sha256",
    "independent_rowwise_joint_vjp",
    "independent_rowwise_joint_vjp_sha256",
    "independent_rowwise_joint_vjp_parameter_sha256",
    "split_direct_plus_anchor_gradient",
    "control_decomposition",
    "pre_step_policy_parameter_state",
    "pre_step_optimizer_state",
    "pre_step_identity",
    "isolated_audit_guard_hashes_before",
    "isolated_audit_guard_hashes_after",
    "capture_hook_counts",
)


def _raw_step_record_sha256_v2(
    item: Mapping[str, Any], *, arm: str, update_ordinal: int
) -> str:
    required = list(RAW_STEP_CHAIN_FIELDS)
    if arm == "treatment_pcgrad":
        required.append("projected_task_gradients")
    elif arm == "control_vanilla":
        required.extend(CONTROL_LEGACY_RAW_STEP_CHAIN_FIELDS)
    else:
        raise ValueError("raw step identity arm mismatch")
    if set(item) != set(required):
        raise ValueError("raw step identity key set mismatch")
    payload = {
        "schema_version": "mass-preserving-pcgrad-raw-step-identity-v2",
        "arm": arm, "stage_2_update_ordinal": update_ordinal,
        "evidence": {
            field: _tensor_digest_record_v2(item[field]) for field in required
        },
    }
    return canonical_sha256(payload)


def _runtime_raw_step_item_v2(
    evidence: Mapping[str, Any], *, arm: str
) -> dict[str, Any]:
    raw = evidence.get("raw_task_gradients_float64") or {}
    item: dict[str, Any] = {
        "raw_task_gradients": {
            task: torch.tensor(raw[task], dtype=torch.float64, device="cpu")
            for task in TASK_ORDER
        },
        "direct_policy_gradient": torch.tensor(
            evidence["direct_policy_gradient_float64"], dtype=torch.float64
        ),
        "anchor_kl_gradient": torch.tensor(
            evidence["anchor_kl_gradient_float32"], dtype=torch.float32
        ),
        "combined_preclip_gradient": torch.tensor(
            evidence["combined_preclip_gradient_float32"], dtype=torch.float32
        ),
        "combined_postclip_gradient": torch.tensor(
            evidence["combined_postclip_gradient_float32"], dtype=torch.float32
        ),
        "postclip_coefficient": float(
            evidence["postclip_coefficient_float32"]
        ),
        "actual_parameter_delta": torch.tensor(
            evidence["actual_parameter_delta_float32"], dtype=torch.float32
        ),
        "cumulative_parameter_delta": torch.tensor(
            evidence["cumulative_parameter_delta_float32"], dtype=torch.float32
        ),
        "policy_parameter_state_after": evidence["policy_parameter_state_after"],
        "optimizer_state_after": evidence["optimizer_state_after"],
        "optimizer_step_counters": evidence["optimizer_step_counters"],
        "ordered_outputs": evidence["ordered_outputs"],
    }
    if arm == "treatment_pcgrad":
        projected = evidence.get("projected_task_gradients_float64") or {}
        item["projected_task_gradients"] = {
            task: torch.tensor(projected[task], dtype=torch.float64, device="cpu")
            for task in TASK_ORDER
        }
    elif arm == "control_vanilla":
        item.update({
            "authoritative_legacy_preclip_gradient": torch.tensor(
                evidence["authoritative_legacy_preclip_gradient_float32"],
                dtype=torch.float32,
            ),
            "authoritative_legacy_preclip_sha256": str(
                evidence["authoritative_legacy_preclip_sha256"]
            ),
            "independent_rowwise_joint_vjp": torch.tensor(
                evidence["independent_rowwise_joint_vjp_float32"],
                dtype=torch.float32,
            ),
            "independent_rowwise_joint_vjp_sha256": str(
                evidence["independent_rowwise_joint_vjp_sha256"]
            ),
            "independent_rowwise_joint_vjp_parameter_sha256": copy.deepcopy(
                evidence["independent_rowwise_joint_vjp_parameter_sha256"]
            ),
            "split_direct_plus_anchor_gradient": torch.tensor(
                evidence["split_direct_plus_anchor_gradient_float32"],
                dtype=torch.float32,
            ),
            "control_decomposition": copy.deepcopy(
                evidence["control_decomposition"]
            ),
            "pre_step_policy_parameter_state": copy.deepcopy(
                evidence["pre_step_policy_parameter_state"]
            ),
            "pre_step_optimizer_state": copy.deepcopy(
                evidence["pre_step_optimizer_state"]
            ),
            "pre_step_identity": copy.deepcopy(evidence["pre_step_identity"]),
            "isolated_audit_guard_hashes_before": copy.deepcopy(
                evidence["isolated_audit_guard_hashes_before"]
            ),
            "isolated_audit_guard_hashes_after": copy.deepcopy(
                evidence["isolated_audit_guard_hashes_after"]
            ),
            "capture_hook_counts": copy.deepcopy(
                evidence["capture_hook_counts"]
            ),
        })
    return item


def _public_step_tensor_references_v2(arm: str, update: int) -> dict[str, str]:
    prefix = f"updates/{update:02d}/{arm}"
    refs = {
        "raw_task_gradients": f"{prefix}/raw_task_gradients",
        "direct_policy_gradient": f"{prefix}/direct_policy_gradient",
        "anchor_kl_gradient": f"{prefix}/anchor_kl_gradient",
        "combined_preclip_gradient": f"{prefix}/combined_preclip_gradient",
        "combined_postclip_gradient": f"{prefix}/combined_postclip_gradient",
        "postclip_coefficient": f"{prefix}/postclip_coefficient",
        "actual_parameter_delta": f"{prefix}/actual_parameter_delta",
        "cumulative_parameter_delta": f"{prefix}/cumulative_parameter_delta",
        "ordered_outputs": f"{prefix}/ordered_outputs",
        "parameter_state_after": f"{prefix}/policy_parameter_state_after",
        "optimizer_state_after": f"{prefix}/optimizer_state_after",
    }
    if arm == "treatment_pcgrad":
        refs["projected_task_gradients"] = f"{prefix}/projected_task_gradients"
    elif arm == "control_vanilla":
        for field in CONTROL_LEGACY_RAW_STEP_CHAIN_FIELDS:
            refs[field] = f"{prefix}/{field}"
    return refs


def _runtime_step_record_sha256_v2(step: Mapping[str, Any]) -> str:
    arm = str(step["arm"])
    update = int(step["stage_2_update_ordinal"])
    evidence = step.get("tensor_evidence")
    if not isinstance(evidence, Mapping):
        raise ValueError("runtime step lacks raw tensor evidence")
    return _raw_step_record_sha256_v2(
        _runtime_raw_step_item_v2(evidence, arm=arm),
        arm=arm, update_ordinal=update,
    )


def _public_step_record(record: Mapping[str, Any]) -> dict[str, Any]:
    step = record.get("step") or {}
    evidence = step.get("tensor_evidence")
    update = int(record["stage_2_update_ordinal"])
    arm = str(step["arm"])
    if not isinstance(evidence, Mapping):
        raise ValueError("public step record lacks raw tensor evidence")
    raw_item = _runtime_raw_step_item_v2(evidence, arm=arm)
    return {
        "schema_version": "mass-preserving-pcgrad-public-step-reference-v2",
        "arm": arm, "stage_2_update_ordinal": update,
        "gradient_tensor_references": _public_step_tensor_references_v2(
            arm, update
        ),
        "gradient_tensor_evidence_present": True,
        "step_record_sha256": _raw_step_record_sha256_v2(
            raw_item, arm=arm, update_ordinal=update
        ),
    }


def _public_step_reference_failures_v2(
    row: Any, raw_item: Any, *, arm: str, update: int
) -> list[str]:
    expected_keys = {
        "schema_version", "arm", "stage_2_update_ordinal",
        "gradient_tensor_references", "gradient_tensor_evidence_present",
        "step_record_sha256",
    }
    if not isinstance(row, Mapping):
        return [f"step_schema:{arm}:{update}"]
    failures: list[str] = []
    if (
        set(row) != expected_keys
        or row.get("schema_version")
        != "mass-preserving-pcgrad-public-step-reference-v2"
        or row.get("arm") != arm
        or row.get("stage_2_update_ordinal") != update
        or row.get("gradient_tensor_evidence_present") is not True
    ):
        failures.append(f"step_schema:{arm}:{update}")
    if row.get("gradient_tensor_references") != (
        _public_step_tensor_references_v2(arm, update)
    ):
        failures.append(f"step_tensor_reference:{arm}:{update}")
    try:
        expected_hash = _raw_step_record_sha256_v2(
            raw_item, arm=arm, update_ordinal=update
        )
        if row.get("step_record_sha256") != expected_hash:
            failures.append(f"step_record_binding:{arm}:{update}")
    except Exception as error:
        failures.append(
            f"step_raw_binding:{arm}:{update}:{type(error).__name__}:{error}"
        )
    return failures


def _ordered_output_tensor_evidence(
    metrics: Sequence[Mapping[str, Any]],
) -> dict[str, torch.Tensor]:
    if len(metrics) != EXPECTED_ROWS:
        raise ValueError("ordered output evidence requires exactly 830 rows")
    offsets = [0]
    probabilities: list[float] = []
    values: list[float] = []
    for ordinal, row in enumerate(metrics):
        if row.get("ppo_row_ordinal") != ordinal:
            raise ValueError("ordered output evidence row order mismatch")
        current = list(row.get("probabilities_float32") or ())
        if not current:
            raise ValueError("ordered output evidence has an empty probability row")
        probabilities.extend(float(value) for value in current)
        offsets.append(len(probabilities))
        values.append(float(row["value_float32"]))
    return {
        "probabilities": torch.tensor(probabilities, dtype=torch.float32),
        "probability_offsets": torch.tensor(offsets, dtype=torch.int64),
        "values": torch.tensor(values, dtype=torch.float32),
    }


def _gradient_tensor_bundle(run: Mapping[str, Any]) -> dict[str, Any]:
    series: dict[str, Any] = {}
    completed = int(run["completed_synchronized_stage2_updates"])
    for update in range(1, completed + 1):
        for arm in ("control_vanilla", "treatment_pcgrad"):
            record = run["update_records"][arm][update - 1]
            step = record["step"]
            evidence = step.get("tensor_evidence")
            if not isinstance(evidence, Mapping):
                raise ValueError("completed step lacks tensor evidence")
            raw = evidence.get("raw_task_gradients_float64") or {}
            if tuple(raw) != TASK_ORDER:
                raise ValueError("raw tensor task key order mismatch")
            item: dict[str, Any] = {
                "raw_task_gradients": {
                    task: torch.tensor(raw[task], dtype=torch.float64, device="cpu")
                    for task in TASK_ORDER
                },
                "direct_policy_gradient": torch.tensor(
                    evidence["direct_policy_gradient_float64"],
                    dtype=torch.float64, device="cpu",
                ),
                "anchor_kl_gradient": torch.tensor(
                    evidence["anchor_kl_gradient_float32"],
                    dtype=torch.float32, device="cpu",
                ),
                "combined_preclip_gradient": torch.tensor(
                    evidence["combined_preclip_gradient_float32"],
                    dtype=torch.float32, device="cpu",
                ),
                "combined_postclip_gradient": torch.tensor(
                    evidence["combined_postclip_gradient_float32"],
                    dtype=torch.float32, device="cpu",
                ),
                "postclip_coefficient": float(
                    evidence["postclip_coefficient_float32"]
                ),
                "actual_parameter_delta": torch.tensor(
                    evidence["actual_parameter_delta_float32"],
                    dtype=torch.float32, device="cpu",
                ),
                "cumulative_parameter_delta": torch.tensor(
                    evidence["cumulative_parameter_delta_float32"],
                    dtype=torch.float32, device="cpu",
                ),
                "policy_parameter_state_after": copy.deepcopy(
                    evidence["policy_parameter_state_after"]
                ),
                "optimizer_state_after": copy.deepcopy(
                    evidence["optimizer_state_after"]
                ),
                "optimizer_step_counters": copy.deepcopy(
                    evidence["optimizer_step_counters"]
                ),
                "ordered_outputs": copy.deepcopy(evidence["ordered_outputs"]),
            }
            if arm == "treatment_pcgrad":
                projected = evidence.get("projected_task_gradients_float64") or {}
                if tuple(projected) != TASK_ORDER:
                    raise ValueError("projected tensor task key order mismatch")
                item["projected_task_gradients"] = {
                    task: torch.tensor(
                        projected[task], dtype=torch.float64, device="cpu"
                    )
                    for task in TASK_ORDER
                }
            else:
                item.update(
                    _runtime_raw_step_item_v2(evidence, arm=arm)
                )
            series[f"updates/{update:02d}/{arm}"] = item
    stage2_start_states = {}
    for arm in ("control_vanilla", "treatment_pcgrad"):
        state = run["arms"][arm]
        stage2_start_states[arm] = {
            "model_state": {
                name: value.detach().cpu().clone()
                for name, value in (state.get("stage2_start_parameters") or {}).items()
            },
            "optimizer_state": copy.deepcopy(
                state.get("stage2_start_optimizer_state")
            ),
            "stage1_report": copy.deepcopy(state.get("stage1_report")),
            "stage1_safety": copy.deepcopy(state.get("stage1_safety")),
            "stage1_value_identity": copy.deepcopy(
                state.get("stage1_value_identity")
            ),
            "stage1_record_sha256": state.get("stage1_record_sha256"),
            "stage1_outputs": (
                None if state.get("stage1_metrics") is None
                else _ordered_output_tensor_evidence(state["stage1_metrics"])
            ),
        }
    layout = []
    control_start = stage2_start_states["control_vanilla"]["model_state"]
    for name in PARAMETER_NAMES:
        tensor = control_start.get(name)
        if tensor is None:
            continue
        layout.append({
            "name": name, "shape": list(tensor.shape),
            "numel": tensor.numel(), "dtype": str(tensor.dtype),
        })
    return {
        "schema_version": "mass-preserving-pcgrad-gradient-tensors-v2",
        "task_order": list(TASK_ORDER),
        "parameter_names": list(PARAMETER_NAMES),
        "parameter_layout": layout,
        "completed_synchronized_stage2_updates": completed,
        "stage2_start_states": stage2_start_states,
        "control_update32_state": copy.deepcopy(
            run.get("control_update32_state")
        ),
        "duplicate_treatment_state": copy.deepcopy(
            run.get("duplicate_treatment_evidence")
        ),
        "series": series,
    }


def _serialize_checkpoint(
    state: Mapping[str, Any],
    *,
    arm: str,
    spec: Mapping[str, Any],
    execution_spec_sha256: str,
    prepare_receipt: Mapping[str, Any],
    synchronized_steps: int,
    output_hashes: Mapping[str, Any] | None,
) -> bytes:
    metadata = copy.deepcopy(state["input_metadata"])
    metadata["pcgrad_publication"] = {
        "status": "PENDING_AUDIT", "arm": arm,
        "plan_path": PLAN_RELATIVE_PATH.as_posix(), "plan_sha256": PLAN_SHA256,
        "correction_path": CORRECTION_RELATIVE_PATH.as_posix(),
        "correction_sha256": CORRECTION_SHA256,
        "correction_v2_path": CORRECTION_V2_RELATIVE_PATH.as_posix(),
        "correction_v2_sha256": CORRECTION_V2_SHA256,
        "correction_v3_path": CORRECTION_V3_RELATIVE_PATH.as_posix(),
        "correction_v3_sha256": CORRECTION_V3_SHA256,
        "correction_v4_path": CORRECTION_V4_RELATIVE_PATH.as_posix(),
        "correction_v4_sha256": CORRECTION_V4_SHA256,
        "correction_v5_path": CORRECTION_V5_RELATIVE_PATH.as_posix(),
        "correction_v5_sha256": CORRECTION_V5_SHA256,
        "predecessor_execution_stop": copy.deepcopy(
            prepare_receipt["predecessor_execution_stop"]
        ),
        "implementation_path": IMPLEMENTATION_RELATIVE_PATH.as_posix(),
        "implementation_snapshot_file_count": spec[
            "implementation_snapshot_file_count"
        ],
        "implementation_snapshot_sha256": spec["implementation_snapshot_sha256"],
        "execution_spec_sha256": execution_spec_sha256,
        "prepare_receipt_sha256": prepare_receipt["receipt_sha256"],
        "synchronized_optimizer_steps": synchronized_steps,
        "source_hashes": copy.deepcopy(state["source_hashes"]),
        "terminal_output_hashes": copy.deepcopy(output_hashes),
        "games_run": 0,
    }
    payload = {
        "model_config": copy.deepcopy(vars(state["model"].config)),
        "model_state": {
            name: value.detach().cpu().clone()
            for name, value in state["model"].state_dict().items()
        },
        "metadata": metadata,
        "optimizer_state": copy.deepcopy(state["optimizer"].state_dict()),
    }
    buffer = io.BytesIO()
    torch.save(payload, buffer)
    return buffer.getvalue()


def _validate_runtime_checkpoint_bytes(
    payload: bytes,
    state: Mapping[str, Any],
    *,
    expected_arm: str,
    expected_steps: int,
) -> dict[str, Any]:
    raw = torch.load(io.BytesIO(payload), map_location="cpu", weights_only=False)
    if set(raw) != {"model_config", "model_state", "metadata", "optimizer_state"}:
        raise ValueError("runtime checkpoint key set mismatch")
    binding = raw["metadata"].get("pcgrad_publication") or {}
    if (
        binding.get("arm") != expected_arm
        or binding.get("status") != "PENDING_AUDIT"
        or binding.get("synchronized_optimizer_steps") != expected_steps
        or binding.get("games_run") != 0
    ):
        raise ValueError("runtime checkpoint publication metadata mismatch")
    with tempfile.TemporaryDirectory(prefix="pcgrad-checkpoint-reload-") as directory:
        path = Path(directory) / "candidate.pt"
        path.write_bytes(payload)
        model, metadata, optimizer_state = load_checkpoint(
            path,
            expected_source_hashes=state["source_hashes"],
            device="cpu",
        )
    if not _nested_byte_exact_v2(model.state_dict(), state["model"].state_dict()):
        raise ValueError("runtime checkpoint model state mismatch")
    if not _nested_byte_exact_v2(
        optimizer_state, state["optimizer"].state_dict()
    ):
        raise ValueError("runtime checkpoint optimizer state mismatch")
    actual_steps = _optimizer_step_counters_from_state(optimizer_state)
    expected_optimizer_steps = _optimizer_step_counters_from_state(
        state["optimizer"].state_dict()
    )
    if actual_steps != expected_optimizer_steps:
        raise ValueError("checkpoint optimizer step count mismatch")
    if expected_steps == 0 and actual_steps:
        raise ValueError("zero-step checkpoint has optimizer state")
    return {
        "runtime_loader_pass": True, "model_state_byte_exact": True,
        "optimizer_state_byte_exact": True,
        "metadata_exact": metadata == raw["metadata"],
        "optimizer_state_steps": actual_steps,
    }


def _terminal_metrics_for_arm(
    run: Mapping[str, Any], receipt: Mapping[str, Any], arm: str
) -> list[dict[str, Any]] | None:
    completed = int(run["completed_synchronized_stage2_updates"])
    if completed:
        if str(completed) in run["full_830_row_diagnostics"][arm]:
            return run["full_830_row_diagnostics"][arm][str(completed)]
        return base._measure_stage(
            run["loaded_arms"][arm], receipt, stage=2,
            stage_2_update_ordinal=completed,
        )
    if run["completed_optimizer_steps_per_arm"][arm] == 1:
        return run["arms"][arm].get("stage1_metrics")
    return None


def _strict_gate_shape_from_run(run: Mapping[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    completed = run.get("completed_optimizer_steps_per_arm")
    if completed != {"control_vanilla": 65, "treatment_pcgrad": 65}:
        failures.append("completed_optimizer_steps")
    updates = run.get("update_records") or {}
    if set(updates) != {"control_vanilla", "treatment_pcgrad"} or any(
        len(updates.get(arm) or []) != 64
        for arm in ("control_vanilla", "treatment_pcgrad")
    ):
        failures.append("step_records")
    milestones = run.get("full_830_row_diagnostics") or {}
    required_milestones = {str(value) for value in DIAGNOSTIC_UPDATES}
    for arm in ("control_vanilla", "treatment_pcgrad"):
        values = milestones.get(arm) or {}
        if set(values) != required_milestones or any(
            len(values[key]) != EXPECTED_ROWS for key in values
        ):
            failures.append(f"milestone_rows:{arm}")
    summaries = run.get("alignment_summaries") or {}
    expected_updates = {"48", "64"}
    expected_priority = set(PRIORITY_TASKS)
    expected_families = {
        f"{family}:{polarity}"
        for family in OPTION_TYPE_BY_FAMILY for polarity in ("positive", "negative")
    }
    for arm in ("control_vanilla", "treatment_pcgrad"):
        by_update = summaries.get(arm) or {}
        if set(by_update) != expected_updates:
            failures.append(f"alignment_updates:{arm}")
            continue
        for update in expected_updates:
            summary = by_update[update]
            if set(summary.get("priority") or {}) != expected_priority:
                failures.append(f"priority_keys:{arm}:{update}")
            if set(summary.get("all_12_family_polarity_lower_medians") or {}) != expected_families:
                failures.append(f"family_keys:{arm}:{update}")
    if run.get("all_safety_gates_pass") is not True:
        failures.append("safety")
    if run.get("failure") is not None:
        failures.append("transaction_failure")
    if (run.get("stage1_equality") or {}).get("passed") is not True:
        failures.append("stage1_equality")
    if (run.get("control_update32_reference") or {}).get("passed") is not True:
        failures.append("control_update32")
    mechanism = run.get("mechanism") or {}
    if mechanism.get("surgery_nonzero") is not True:
        failures.append("mechanism:surgery_nonzero")
    if not set(AUDIT_ADVERSE_TASKS).issubset(
        set(mechanism.get("tasks_touched_first_16") or ())
    ):
        failures.append("mechanism:adverse_groups_first16")
    projection = mechanism.get("cumulative_delta_projections") or {}
    for update in (48, 64):
        values = projection.get(str(update)) or {}
        if set(values) != expected_priority or any(
            float(values[task]) <= 0.0 for task in PRIORITY_TASKS
        ):
            failures.append(f"mechanism:cumulative_projection:{update}")
    if (run.get("terminal_END_controls") or {}).get("passed") is not True:
        failures.append("END")
    if run.get("duplicate_treatment_canonical_outputs_identical") is not True:
        failures.append("duplicate_treatment")
    return {"offline_pass": not failures, "failures": failures}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _write_new_bytes(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _replace_new_pending_directory(
    staging: Path, pending_directory: Path
) -> int:
    """Atomically publish a new directory with bounded Windows lock retries."""

    for attempt in range(
        len(PENDING_DIRECTORY_REPLACE_RETRY_DELAYS_SECONDS) + 1
    ):
        if os.path.lexists(pending_directory):
            raise FileExistsError("pending audit destination already exists")
        if (
            not staging.is_dir()
            or inherited._is_link_or_reparse(staging)
        ):
            raise FileNotFoundError("pending staging directory is not intact")
        try:
            os.replace(staging, pending_directory)
        except PermissionError:
            # Retry only the transient Windows lock shape.  Any collision or
            # staging mutation remains fail-closed and is never overwritten.
            if (
                os.path.lexists(pending_directory)
                or not staging.is_dir()
                or inherited._is_link_or_reparse(staging)
                or attempt
                == len(PENDING_DIRECTORY_REPLACE_RETRY_DELAYS_SECONDS)
            ):
                raise
            time.sleep(
                PENDING_DIRECTORY_REPLACE_RETRY_DELAYS_SECONDS[attempt]
            )
            continue
        if staging.exists() or not pending_directory.is_dir():
            raise OSError("pending atomic publication postcondition failed")
        return attempt
    raise AssertionError("pending publication retry loop did not terminate")


def publish_pending_bundle(
    *,
    pending_directory: Path,
    run: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    spec: Mapping[str, Any],
    execution_spec_path: Path,
    execution_spec_sha256: str,
) -> dict[str, Any]:
    """Atomically retain both synchronized arm states for external audit."""

    if pending_directory.exists():
        raise FileExistsError("pending audit destination already exists")
    if set(run.get("arms") or {}) != {"control_vanilla", "treatment_pcgrad"}:
        raise ValueError("pending publication requires both recoverable arm states")
    completed_steps = dict(run["completed_optimizer_steps_per_arm"])
    if len(set(completed_steps.values())) != 1:
        raise ValueError("pending arm states are not synchronized")
    synchronized_steps = next(iter(completed_steps.values()))
    stage1_rows: list[dict[str, Any]] = []
    for arm in ("control_vanilla", "treatment_pcgrad"):
        metrics = run["arms"][arm].get("stage1_metrics")
        if metrics is None:
            metrics = [None] * EXPECTED_ROWS
        if len(metrics) != EXPECTED_ROWS:
            raise ValueError("Stage1 diagnostics row count mismatch")
        record_hash = run["arms"][arm].get("stage1_record_sha256")
        for ordinal, row in enumerate(metrics):
            evidence = run["arms"][arm].get("stage1_equality_evidence") or {}
            stage1_rows.append({
                "arm": arm, "row_ordinal": ordinal,
                "stage1_record_sha256": record_hash,
                "stage1_equality": copy.deepcopy(run.get("stage1_equality")),
                "complete_stage1_evidence": (
                    {
                        key: copy.deepcopy(value)
                        for key, value in evidence.items()
                        if key not in (
                            "model_state", "optimizer_state",
                            "complete_830_diagnostics",
                        )
                    }
                    if ordinal == 0 else None
                ),
                "optimizer_state_reference": (
                    f"stage2_start_states/{arm}/optimizer_state"
                    if ordinal == 0 else None
                ),
                "diagnostic": copy.deepcopy(row),
            })
    milestone_rows: list[dict[str, Any]] = []
    for arm in ("control_vanilla", "treatment_pcgrad"):
        for update_text, rows in sorted(
            (run["full_830_row_diagnostics"].get(arm) or {}).items(),
            key=lambda item: int(item[0]),
        ):
            if int(update_text) not in DIAGNOSTIC_UPDATES or len(rows) != EXPECTED_ROWS:
                raise ValueError("milestone diagnostic shape mismatch")
            for ordinal, row in enumerate(rows):
                milestone_rows.append({
                    "arm": arm, "stage2_update_ordinal": int(update_text),
                    "row_ordinal": ordinal, "diagnostic": copy.deepcopy(row),
                })
    step_rows: list[dict[str, Any]] = []
    for update in range(1, int(run["completed_synchronized_stage2_updates"]) + 1):
        for arm in ("control_vanilla", "treatment_pcgrad"):
            step_rows.append(_public_step_record(run["update_records"][arm][update - 1]))
    gradient_bundle = _gradient_tensor_bundle(run)
    gradient_buffer = io.BytesIO()
    torch.save(gradient_bundle, gradient_buffer)
    evidence_payloads = {
        "stage1_diagnostics.jsonl": _jsonl_bytes(stage1_rows),
        "milestone_diagnostics.jsonl": _jsonl_bytes(milestone_rows),
        "step_summaries.jsonl": _jsonl_bytes(step_rows),
        "gradient_tensors.pt": gradient_buffer.getvalue(),
    }
    checkpoint_evidence: dict[str, Any] = {}
    checkpoint_payloads: dict[str, bytes] = {}
    terminal_hashes: dict[str, Any] = {}
    for arm, filename in (
        ("control_vanilla", "control_pending.pt"),
        ("treatment_pcgrad", "treatment_pending.pt"),
    ):
        terminal_metrics = _terminal_metrics_for_arm(run, prepare_receipt, arm)
        if terminal_metrics is not None:
            if len(terminal_metrics) != EXPECTED_ROWS:
                raise ValueError("terminal output row count mismatch")
            terminal_hashes[arm] = base._ordered_output_hashes(terminal_metrics)
        else:
            terminal_hashes[arm] = None
        payload = _serialize_checkpoint(
            run["arms"][arm], arm=arm, spec=spec,
            execution_spec_sha256=execution_spec_sha256,
            prepare_receipt=prepare_receipt,
            synchronized_steps=synchronized_steps,
            output_hashes=terminal_hashes[arm],
        )
        checkpoint_evidence[arm] = _validate_runtime_checkpoint_bytes(
            payload, run["arms"][arm], expected_arm=arm,
            expected_steps=synchronized_steps,
        )
        checkpoint_evidence[arm]["terminal_output_row_count"] = (
            0 if terminal_metrics is None else len(terminal_metrics)
        )
        checkpoint_evidence[arm]["terminal_output_hashes"] = terminal_hashes[arm]
        checkpoint_payloads[filename] = payload
    offline_gates = _strict_gate_shape_from_run(run)
    run_summary_core = {
        "schema_version": RUN_SUMMARY_SCHEMA_VERSION,
        "status": "PENDING_AUDIT",
        "caller_summaries_informational_only": True,
        "execution_spec_path": str(execution_spec_path.absolute()),
        "execution_spec_sha256": execution_spec_sha256,
        "prepare_receipt_sha256": prepare_receipt["receipt_sha256"],
        "completed_optimizer_steps_per_arm": completed_steps,
        "completed_synchronized_stage2_updates": run[
            "completed_synchronized_stage2_updates"
        ],
        "failure": copy.deepcopy(run.get("failure")),
        "safety_stop": copy.deepcopy(run.get("safety_stop")),
        "all_safety_gates_pass": run.get("all_safety_gates_pass") is True,
        "stage1_equality": copy.deepcopy(run.get("stage1_equality")),
        "stage1_record_hashes": {
            arm: run["arms"][arm].get("stage1_record_sha256")
            for arm in ("control_vanilla", "treatment_pcgrad")
        },
        "stage1_complete_evidence": {
            arm: {
                key: copy.deepcopy(value)
                for key, value in (
                    run["arms"][arm].get("stage1_equality_evidence") or {}
                ).items()
                if key not in (
                    "model_state", "optimizer_state",
                    "complete_830_diagnostics",
                )
            }
            for arm in ("control_vanilla", "treatment_pcgrad")
        },
        "control_update32_reference": copy.deepcopy(
            run.get("control_update32_reference")
        ),
        "mechanism": copy.deepcopy(run.get("mechanism")),
        "alignment_summaries": copy.deepcopy(run.get("alignment_summaries")),
        "terminal_END_controls": copy.deepcopy(run.get("terminal_END_controls")),
        "duplicate_treatment_identity": copy.deepcopy(
            run.get("duplicate_treatment_identity")
        ),
        "duplicate_treatment_canonical_outputs_identical": (
            run.get("duplicate_treatment_canonical_outputs_identical") is True
        ),
        "checkpoint_reload_evidence": checkpoint_evidence,
        "strict_offline_gates": offline_gates,
        "evidence": {
            name: {"bytes": len(payload), "sha256": _sha256_bytes(payload)}
            for name, payload in evidence_payloads.items()
        },
        "expected_task_order": list(TASK_ORDER),
        "expected_diagnostic_updates": list(DIAGNOSTIC_UPDATES),
        "stage1_diagnostic_row_count": len(stage1_rows),
        "milestone_diagnostic_row_count": len(milestone_rows),
        "step_summary_row_count": len(step_rows),
        "games_run": 0,
        "runtime_smoke_executed": False,
    }
    run_summary = {
        **run_summary_core, "run_summary_sha256": canonical_sha256(run_summary_core)
    }
    evidence_payloads["run_summary.json"] = canonical_json_bytes(
        run_summary, newline=True
    )
    evidence_payloads.update(checkpoint_payloads)
    marker = {
        "status": "PENDING_AUDIT",
        "execution_spec_sha256": execution_spec_sha256,
        "prepare_receipt_sha256": prepare_receipt["receipt_sha256"],
        "games_run": 0,
        "runtime_smoke_executed": False,
    }
    evidence_payloads["PENDING_AUDIT"] = canonical_json_bytes(marker, newline=True)
    manifest_core = {
        "schema_version": PENDING_MANIFEST_SCHEMA_VERSION,
        "status": "PENDING_AUDIT",
        "execution_spec_path": str(execution_spec_path.absolute()),
        "execution_spec_sha256": execution_spec_sha256,
        "prepare_receipt_path": spec["prepare_receipt_path"],
        "prepare_receipt_file_sha256": spec["prepare_receipt_file_sha256"],
        "prepare_receipt_sha256": spec["prepare_receipt_sha256"],
        "implementation_snapshot_file_count": spec[
            "implementation_snapshot_file_count"
        ],
        "implementation_snapshot_sha256": spec["implementation_snapshot_sha256"],
        "files": {
            name: {"bytes": len(payload), "sha256": _sha256_bytes(payload)}
            for name, payload in sorted(evidence_payloads.items())
        },
        "completed_optimizer_steps_per_arm": completed_steps,
        "completed_synchronized_stage2_updates": run[
            "completed_synchronized_stage2_updates"
        ],
        "failure": copy.deepcopy(run.get("failure")),
        "games_run": 0,
        "runtime_smoke_executed": False,
    }
    manifest = {
        **manifest_core, "manifest_core_sha256": canonical_sha256(manifest_core)
    }
    manifest_payload = canonical_json_bytes(manifest, newline=True)
    staging = Path(tempfile.mkdtemp(
        prefix=".pcgrad-pending-", dir=str(pending_directory.parent)
    ))
    try:
        for name, payload in evidence_payloads.items():
            _write_new_bytes(staging / name, payload)
        _write_new_bytes(staging / "manifest.json", manifest_payload)
        if {item.name for item in staging.iterdir()} != set(PENDING_FILES):
            raise ValueError("pending staging artifact set mismatch")
        _replace_new_pending_directory(staging, pending_directory)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {
        "status": "PENDING_AUDIT",
        "pending_directory": str(pending_directory),
        "manifest_path": str(pending_directory / "manifest.json"),
        "manifest_file_sha256": _sha256_bytes(manifest_payload),
        "manifest_core_sha256": manifest["manifest_core_sha256"],
        "completed_optimizer_steps_per_arm": completed_steps,
        "games_run": 0,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ordinal, line in enumerate(path.read_bytes().splitlines()):
        if not line:
            raise ValueError(f"blank JSONL line at {ordinal}")
        value = json.loads(line.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSONL record is not a mapping")
        rows.append(value)
    return rows


def _load_pending_manifest(
    path: Path, expected_hash: str
) -> tuple[dict[str, Any], list[str]]:
    manifest = _load_hashed_json(
        path, _strict_sha256(expected_hash, label="pending manifest hash"),
        label="pending manifest",
    )
    core = dict(manifest)
    claim = _strict_sha256(
        core.pop("manifest_core_sha256", None), label="pending manifest core hash"
    )
    if canonical_sha256(core) != claim:
        raise ValueError("pending manifest core hash mismatch")
    if manifest.get("schema_version") != PENDING_MANIFEST_SCHEMA_VERSION:
        raise ValueError("pending manifest schema mismatch")
    if set(manifest.get("files") or {}) != set(PENDING_FILES) - {"manifest.json"}:
        raise ValueError("pending manifest file inventory mismatch")
    actual_names = {item.name for item in path.parent.iterdir()}
    errors: list[str] = []
    if actual_names != set(PENDING_FILES):
        errors.append("pending_file_set")
    for name, evidence in manifest["files"].items():
        file_path = path.parent / name
        if not file_path.is_file():
            errors.append(f"missing:{name}")
            continue
        payload = file_path.read_bytes()
        if len(payload) != evidence.get("bytes"):
            errors.append(f"size:{name}")
        if _sha256_bytes(payload) != evidence.get("sha256"):
            errors.append(f"sha256:{name}")
    if (path.parent / "ACCEPTED").exists() or (path.parent / "REJECTED").exists():
        errors.append("final_marker_in_pending")
    return manifest, errors


def _recompute_pcgrad_flat(
    raw: Mapping[str, torch.Tensor], *, update_ordinal: int
) -> tuple[dict[str, torch.Tensor], torch.Tensor]:
    if tuple(raw) != TASK_ORDER:
        raise ValueError("raw PCGrad task key order mismatch")
    values = {
        task: raw[task].detach().cpu().contiguous().to(torch.float64)
        for task in TASK_ORDER
    }
    if any(not torch.isfinite(value).all() for value in values.values()):
        raise ValueError("raw PCGrad evidence is nonfinite")
    order = cyclic_task_order(update_ordinal)
    projected: dict[str, torch.Tensor] = {}
    for task in order:
        current = values[task].clone()
        for other in order:
            if other == task:
                continue
            original_other = values[other]
            squared_norm = torch.dot(original_other, original_other)
            if float(squared_norm) == 0.0:
                continue
            dot = torch.dot(current, original_other)
            if float(dot) < 0.0:
                current = current - (dot / squared_norm) * original_other
        projected[task] = current
    combined = torch.zeros_like(next(iter(values.values())))
    for task in order:
        combined = combined + projected[task]
    return {task: projected[task] for task in TASK_ORDER}, combined


def _exact_postclip_flat(
    preclip: torch.Tensor,
    layout: Sequence[Mapping[str, Any]],
    *,
    max_norm: float = GRADIENT_CLIP,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    if preclip.dtype != torch.float32 or preclip.device.type != "cpu":
        raise ValueError("preclip evidence must be CPU float32")
    if tuple(str(row.get("name")) for row in layout) != PARAMETER_NAMES:
        raise ValueError("preclip parameter layout order mismatch")
    offset = 0
    parameters: dict[str, torch.nn.Parameter] = {}
    for row in layout:
        count = int(row["numel"])
        shape = tuple(int(value) for value in row.get("shape") or ())
        part = preclip[offset: offset + count].reshape(shape)
        if part.numel() != count:
            raise ValueError("preclip parameter layout mismatch")
        parameter = torch.nn.Parameter(torch.zeros_like(part), requires_grad=True)
        parameter.grad = part.detach().clone()
        parameters[str(row["name"])] = parameter
        offset += count
    if offset != preclip.numel() or not parameters:
        raise ValueError("preclip flattened length mismatch")
    # Pin the production API, reduction order, and foreach default explicitly.
    total = torch.nn.utils.clip_grad_norm_(
        [parameters[name] for name in sorted(parameters)],
        max_norm,
        norm_type=2.0,
        error_if_nonfinite=True,
        foreach=None,
    )
    coefficient = torch.clamp(
        torch.tensor(max_norm, dtype=total.dtype) / (total + 1e-6),
        max=1.0,
    )
    postclip = torch.cat([
        parameters[name].grad.detach().cpu().contiguous().reshape(-1)
        for name in PARAMETER_NAMES
    ])
    return postclip, total.detach().cpu(), coefficient.detach().cpu()


def _optimizer_parameter_ids(
    optimizer_state: Mapping[str, Any],
) -> dict[str, int]:
    groups = optimizer_state.get("param_groups") or []
    if len(groups) != 1:
        raise ValueError("retained Adam must contain one parameter group")
    ids = list(groups[0].get("params") or ())
    if len(ids) != len(OPTIMIZER_PARAMETER_NAMES):
        raise ValueError("retained Adam parameter count mismatch")
    return dict(zip(OPTIMIZER_PARAMETER_NAMES, ids))


def _optimizer_step_counters_from_state(
    optimizer_state: Mapping[str, Any],
) -> dict[str, int]:
    identifiers = _optimizer_parameter_ids(optimizer_state)
    state = optimizer_state.get("state") or {}
    result: dict[str, int] = {}
    for name in OPTIMIZER_PARAMETER_NAMES:
        values = state.get(identifiers[name])
        if not values:
            continue
        step = values.get("step")
        numeric = float(step) if torch.is_tensor(step) else float(step)
        if not math.isfinite(numeric) or not numeric.is_integer():
            raise ValueError("retained optimizer step is not a finite integer")
        result[name] = int(numeric)
    return result


def _optimizer_canonical_record_from_state_v3(
    optimizer_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Canonicalize retained Adam state without constructing an optimizer."""

    identifiers = _optimizer_parameter_ids(optimizer_state)
    groups = optimizer_state.get("param_groups") or []
    group = copy.deepcopy(groups[0])
    group["params"] = list(OPTIMIZER_PARAMETER_NAMES)
    raw_state = optimizer_state.get("state") or {}
    state: dict[str, Any] = {}
    for name in OPTIMIZER_PARAMETER_NAMES:
        values: dict[str, Any] = {}
        for key, value in sorted((raw_state.get(identifiers[name]) or {}).items()):
            if torch.is_tensor(value):
                if value.device.type != "cpu" or not torch.isfinite(value).all():
                    raise ValueError("retained optimizer tensor domain")
                raw = value.detach().contiguous().numpy().tobytes(order="C")
                values[key] = {
                    "dtype": str(value.dtype), "shape": list(value.shape),
                    "sha256": _sha256_bytes(raw),
                }
            elif isinstance(value, float) and not math.isfinite(value):
                raise ValueError("retained optimizer scalar is nonfinite")
            else:
                values[key] = value
        if values:
            state[name] = values
    record = {"param_group": group, "state": state}
    return {
        "record": record,
        "canonical_sha256": canonical_sha256(record),
        "param_group_canonical_sha256": canonical_sha256(group),
    }


def _manual_adam_step(
    parameters: dict[str, torch.Tensor],
    optimizer_state: dict[str, Any],
    gradients: Mapping[str, torch.Tensor],
) -> dict[str, torch.Tensor]:
    identifiers = _optimizer_parameter_ids(optimizer_state)
    group = optimizer_state["param_groups"][0]
    beta1, beta2 = (float(value) for value in group["betas"])
    learning_rate = float(group["lr"])
    epsilon = float(group["eps"])
    if (
        float(group.get("weight_decay", 0.0)) != 0.0
        or group.get("amsgrad") is True
        or group.get("maximize") is True
    ):
        raise ValueError("retained Adam hyperparameters differ from the fixed contract")
    deltas: dict[str, torch.Tensor] = {}
    state_map = optimizer_state["state"]
    for name in PARAMETER_NAMES:
        parameter = parameters[name]
        gradient = gradients[name].to(dtype=parameter.dtype, device="cpu")
        identifier = identifiers[name]
        state = state_map.setdefault(identifier, {})
        if not state:
            state["step"] = torch.tensor(0.0, dtype=torch.float32)
            state["exp_avg"] = torch.zeros_like(parameter)
            state["exp_avg_sq"] = torch.zeros_like(parameter)
        step = state["step"]
        exp_avg = state["exp_avg"]
        exp_avg_sq = state["exp_avg_sq"]
        before = parameter.clone()
        step.add_(1)
        exp_avg.lerp_(gradient, 1.0 - beta1)
        exp_avg_sq.mul_(beta2).addcmul_(gradient, gradient, value=1.0 - beta2)
        step_value = float(step)
        bias_correction1 = 1.0 - beta1 ** step_value
        bias_correction2 = 1.0 - beta2 ** step_value
        step_size = learning_rate / bias_correction1
        denominator = exp_avg_sq.sqrt().div_(math.sqrt(bias_correction2)).add_(epsilon)
        parameter.addcdiv_(exp_avg, denominator, value=-step_size)
        deltas[name] = parameter - before
    return deltas


def _metrics_from_ordered_output(
    output: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    *,
    update_ordinal: int,
) -> list[dict[str, Any]]:
    probabilities = output.get("probabilities")
    offsets = output.get("probability_offsets")
    values = output.get("values")
    if set(output) != {"probabilities", "probability_offsets", "values"}:
        raise ValueError("ordered output key set mismatch")
    if (
        not torch.is_tensor(probabilities)
        or probabilities.dtype != torch.float32
        or probabilities.device.type != "cpu"
        or probabilities.ndim != 1
        or not torch.is_tensor(offsets)
        or offsets.dtype != torch.int64
        or offsets.device.type != "cpu"
        or offsets.ndim != 1
        or not torch.is_tensor(values)
        or values.dtype != torch.float32
        or values.device.type != "cpu"
        or values.ndim != 1
        or offsets.numel() != EXPECTED_ROWS + 1
        or values.numel() != EXPECTED_ROWS
        or not torch.isfinite(probabilities).all()
        or not torch.isfinite(values).all()
    ):
        raise ValueError("ordered output tensor shape or dtype mismatch")
    if int(offsets[0]) != 0 or int(offsets[-1]) != probabilities.numel():
        raise ValueError("ordered output offsets do not span probabilities")
    metrics: list[dict[str, Any]] = []
    for ordinal, fixed in enumerate(prepare_receipt["rows"]):
        begin, end = int(offsets[ordinal]), int(offsets[ordinal + 1])
        if begin >= end or end - begin != int(fixed["legal_option_count"]):
            raise ValueError("ordered output row offset mismatch")
        post_tensor = probabilities[begin:end].contiguous()
        if not torch.isfinite(post_tensor).all() or not torch.isfinite(values[ordinal]):
            raise ValueError("ordered output is nonfinite")
        post = post_tensor.tolist()
        initial = [float(value) for value in fixed["initial_probabilities_float32"]]
        sampled = int(fixed["sampled_index"])
        delta = post[sampled] - initial[sampled]
        normalized = float(fixed["fixed_normalized_advantage_float32"])
        oriented = (1.0 if normalized > 0.0 else -1.0) * delta
        winners = [index for index, value in enumerate(post) if value == max(post)]
        probability_raw = post_tensor.numpy().tobytes(order="C")
        value_tensor = values[ordinal].reshape(()).contiguous()
        value_raw = value_tensor.numpy().tobytes(order="C")
        metrics.append({
            "stage": 2, "stage_2_update_ordinal": update_ordinal,
            "ppo_row_ordinal": ordinal,
            "public_state_sha256": fixed["public_state_sha256"],
            "behavior_action_order_sha256": fixed["behavior_action_order_sha256"],
            "sampled_index": sampled, "teacher_index": int(fixed["teacher_index"]),
            "end_index": int(fixed["end_index"]),
            "legal_option_count": int(fixed["legal_option_count"]),
            "sampled_option_type": int(fixed["sampled_option_type"]),
            "sampled_semantic_identity": fixed["sampled_semantic_identity"],
            "probabilities_float32": post,
            "probabilities_raw_bytes_hex": probability_raw.hex().upper(),
            "probabilities_byte_sha256": _sha256_bytes(probability_raw),
            "value_float32": float(value_tensor),
            "value_raw_bytes_hex": value_raw.hex().upper(),
            "value_byte_sha256": _sha256_bytes(value_raw),
            "value_output_byte_exact_to_initial": (
                value_raw.hex().upper() == fixed["initial_value_raw_bytes_hex"]
            ),
            "unique_argmax_index": winners[0] if len(winners) == 1 else None,
            "sampled_probability_delta_from_initial": delta,
            "oriented_sampled_probability_delta": oriented,
            "orientation": base.orientation_class(oriented),
            "anchor_kl_post_to_zero": inherited.per_row_anchor_kl(post, initial),
            "total_variation_from_initial": inherited.per_row_total_variation(
                post, initial
            ),
        })
    return metrics


def _split_flat_by_layout(
    vector: torch.Tensor, layout: Sequence[Mapping[str, Any]]
) -> dict[str, torch.Tensor]:
    result: dict[str, torch.Tensor] = {}
    offset = 0
    for row in layout:
        count = int(row["numel"])
        shape = tuple(int(value) for value in row["shape"])
        result[str(row["name"])] = vector[offset: offset + count].reshape(shape)
        offset += count
    if offset != vector.numel():
        raise ValueError("flat vector and parameter layout differ")
    return result


def _replay_gradient_arm(
    gradients: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    *,
    arm: str,
) -> dict[str, Any]:
    failures: list[str] = []
    layout = gradients.get("parameter_layout") or []
    if (
        tuple(gradients.get("parameter_names") or ()) != PARAMETER_NAMES
        or tuple(row.get("name") for row in layout) != PARAMETER_NAMES
    ):
        return {"passed": False, "failures": ["parameter_layout"]}
    start = (gradients.get("stage2_start_states") or {}).get(arm) or {}
    model_state = start.get("model_state") or {}
    if any(
        name not in model_state
        or not torch.is_tensor(model_state[name])
        or model_state[name].device.type != "cpu"
        or not torch.isfinite(model_state[name]).all()
        for name in PARAMETER_NAMES
    ):
        return {"passed": False, "failures": ["stage2_start_model_state"]}
    for row in layout:
        tensor = model_state[row["name"]]
        if (
            list(tensor.shape) != list(row.get("shape") or ())
            or tensor.numel() != row.get("numel")
            or str(tensor.dtype) != row.get("dtype")
        ):
            return {"passed": False, "failures": ["parameter_layout_binding"]}
    parameters = {
        name: model_state[name].detach().cpu().clone() for name in PARAMETER_NAMES
    }
    optimizer_state = copy.deepcopy(start.get("optimizer_state"))
    if not isinstance(optimizer_state, dict):
        return {"passed": False, "failures": ["stage2_start_optimizer_state"]}
    start_flat = torch.cat([
        parameters[name].contiguous().reshape(-1) for name in PARAMETER_NAMES
    ])
    outputs: dict[int, list[dict[str, Any]]] = {}
    surgery_tasks: set[str] = set()
    surgery_by_update: dict[str, list[str]] = {}
    projections: dict[str, dict[str, float]] = {}
    completed = int(gradients.get("completed_synchronized_stage2_updates", -1))
    common_item_keys = {
        "raw_task_gradients", "direct_policy_gradient", "anchor_kl_gradient",
        "combined_preclip_gradient", "combined_postclip_gradient",
        "postclip_coefficient", "actual_parameter_delta",
        "cumulative_parameter_delta", "policy_parameter_state_after",
        "optimizer_state_after", "optimizer_step_counters", "ordered_outputs",
    }
    for update in range(1, completed + 1):
        key = f"updates/{update:02d}/{arm}"
        item = (gradients.get("series") or {}).get(key)
        if not isinstance(item, Mapping):
            failures.append(f"missing_series:{update}")
            continue
        raw = item.get("raw_task_gradients") or {}
        direct = item.get("direct_policy_gradient")
        try:
            expected_item_keys = set(common_item_keys)
            if arm == "treatment_pcgrad":
                expected_item_keys.add("projected_task_gradients")
            elif arm == "control_vanilla":
                expected_item_keys.update(CONTROL_LEGACY_RAW_STEP_CHAIN_FIELDS)
            else:
                raise ValueError("unknown replay arm")
            if set(item) != expected_item_keys:
                raise ValueError("series item key set")
            if tuple(raw) != TASK_ORDER or not torch.is_tensor(direct):
                raise ValueError("raw/direct key set")
            if direct.dtype != torch.float64 or any(
                raw[task].dtype != torch.float64
                or raw[task].device.type != "cpu"
                or raw[task].shape != direct.shape
                or not torch.isfinite(raw[task]).all()
                for task in TASK_ORDER
            ):
                raise ValueError("raw/direct dtype")
            if (
                direct.device.type != "cpu"
                or direct.numel() != sum(int(row["numel"]) for row in layout)
                or not torch.isfinite(direct).all()
            ):
                raise ValueError("direct gradient domain")
            sum_evidence = validate_unsurgeried_sum(raw, direct)
            if (
                sum_evidence["maximum_absolute_difference"]
                > MAX_ABSOLUTE_SUM_DIFFERENCE
                or sum_evidence["relative_l2_difference"]
                > RELATIVE_L2_SUM_DIFFERENCE
            ):
                raise ValueError("seven-task sum tolerance")
            if arm == "treatment_pcgrad":
                recomputed_projected, policy_float64 = _recompute_pcgrad_flat(
                    raw, update_ordinal=update
                )
                retained_projected = item.get("projected_task_gradients") or {}
                if tuple(retained_projected) != TASK_ORDER or any(
                    retained_projected[task].dtype != torch.float64
                    or retained_projected[task].device.type != "cpu"
                    or retained_projected[task].shape != direct.shape
                    or not torch.isfinite(retained_projected[task]).all()
                    or
                    not torch.equal(
                        recomputed_projected[task], retained_projected[task]
                    ) for task in TASK_ORDER
                ):
                    raise ValueError("projected PCGrad evidence")
                if update <= 16:
                    surgery_tasks.update(
                        task for task in TASK_ORDER
                        if not torch.equal(raw[task], recomputed_projected[task])
                    )
                surgery_by_update[str(update)] = [
                    task for task in TASK_ORDER
                    if not torch.equal(raw[task], recomputed_projected[task])
                ]
            anchor = item.get("anchor_kl_gradient")
            preclip = item.get("combined_preclip_gradient")
            postclip = item.get("combined_postclip_gradient")
            if (
                not torch.is_tensor(anchor) or anchor.dtype != torch.float32
                or anchor.device.type != "cpu" or anchor.shape != direct.shape
                or not torch.isfinite(anchor).all()
                or not torch.is_tensor(preclip) or preclip.dtype != torch.float32
                or preclip.device.type != "cpu" or preclip.shape != direct.shape
                or not torch.isfinite(preclip).all()
                or not torch.is_tensor(postclip) or postclip.dtype != torch.float32
                or postclip.device.type != "cpu" or postclip.shape != direct.shape
                or not torch.isfinite(postclip).all()
            ):
                raise ValueError("KL/preclip/postclip dtype")
            if arm == "treatment_pcgrad":
                recomputed_preclip = policy_float64.to(torch.float32) + anchor
                if not torch.equal(recomputed_preclip, preclip):
                    raise ValueError("preclip gradient")
            else:
                retained_pre_parameters = item.get(
                    "pre_step_policy_parameter_state"
                ) or {}
                retained_pre_optimizer = item.get("pre_step_optimizer_state")
                if (
                    tuple(retained_pre_parameters) != PARAMETER_NAMES
                    or not _nested_byte_exact_v2(
                        parameters, retained_pre_parameters
                    )
                ):
                    raise ValueError("control pre-step parameter state")
                if not _nested_byte_exact_v2(
                    optimizer_state, retained_pre_optimizer
                ):
                    raise ValueError("control pre-step optimizer state")
                expected_pre_identity = _control_pre_step_identity_v5(
                    parameters, optimizer_state
                )
                if item.get("pre_step_identity") != expected_pre_identity:
                    raise ValueError("control pre-step identity")
                authoritative = item.get(
                    "authoritative_legacy_preclip_gradient"
                )
                independent = item.get("independent_rowwise_joint_vjp")
                split = item.get("split_direct_plus_anchor_gradient")
                if any(
                    not torch.is_tensor(value)
                    or value.dtype != torch.float32
                    or value.device.type != "cpu"
                    or value.shape != direct.shape
                    or not torch.isfinite(value).all()
                    for value in (authoritative, independent, split)
                ):
                    raise ValueError("control legacy gradient evidence domain")
                if (
                    not torch.equal(authoritative, preclip)
                    or not torch.equal(independent, authoritative)
                ):
                    raise ValueError("control authoritative legacy preclip")
                if not torch.equal(
                    direct.to(torch.float32) + anchor, split
                ):
                    raise ValueError("control diagnostic split gradient")
                if item.get("authoritative_legacy_preclip_sha256") != (
                    _tensor_sha256_v2(authoritative)
                ):
                    raise ValueError("control authoritative preclip hash")
                if item.get("independent_rowwise_joint_vjp_sha256") != (
                    _tensor_sha256_v2(independent)
                ):
                    raise ValueError("control independent VJP hash")
                independent_parts = _split_flat_by_layout(independent, layout)
                expected_vjp_hashes = {
                    name: _tensor_sha256_v2(independent_parts[name])
                    for name in PARAMETER_NAMES
                }
                if item.get(
                    "independent_rowwise_joint_vjp_parameter_sha256"
                ) != expected_vjp_hashes:
                    raise ValueError("control independent VJP parameter hashes")
                decomposition = validate_control_decomposition(
                    authoritative, split
                )
                if item.get("control_decomposition") != decomposition:
                    raise ValueError("control decomposition metrics")
                audit_before = item.get("isolated_audit_guard_hashes_before")
                audit_after = item.get("isolated_audit_guard_hashes_after")
                if (
                    not isinstance(audit_before, Mapping)
                    or audit_before != audit_after
                    or set(audit_before)
                    != {"model_state", "optimizer_state", "grad_state", "cpu_rng_state"}
                    or any(
                        _strict_sha256(value, label="control audit guard hash")
                        != value
                        for value in audit_before.values()
                    )
                ):
                    raise ValueError("control isolated audit guard hashes")
                if item.get("capture_hook_counts") != {
                    name: 1 for name in PARAMETER_NAMES
                }:
                    raise ValueError("control capture hook counts")
            recomputed_postclip, total_norm, coefficient = _exact_postclip_flat(
                preclip, layout
            )
            retained_coefficient = item.get("postclip_coefficient")
            if (
                type(retained_coefficient) is not float
                or not math.isfinite(retained_coefficient)
                or retained_coefficient != float(coefficient)
            ):
                raise ValueError("postclip coefficient")
            retained_coefficient_tensor = torch.tensor(
                retained_coefficient, dtype=preclip.dtype, device="cpu"
            )
            if not torch.equal(
                preclip * retained_coefficient_tensor, postclip
            ):
                raise ValueError("postclip coefficient tensor application")
            if not torch.equal(recomputed_postclip, postclip):
                raise ValueError("exact postclip gradient")
            gradients_by_name = _split_flat_by_layout(postclip, layout)
            actual_by_name = _manual_adam_step(
                parameters, optimizer_state, gradients_by_name
            )
            actual = torch.cat([
                actual_by_name[name].contiguous().reshape(-1)
                for name in PARAMETER_NAMES
            ])
            cumulative = torch.cat([
                (parameters[name] - model_state[name]).contiguous().reshape(-1)
                for name in PARAMETER_NAMES
            ])
            retained_actual = item.get("actual_parameter_delta")
            retained_cumulative = item.get("cumulative_parameter_delta")
            if (
                not torch.is_tensor(retained_actual)
                or retained_actual.dtype != torch.float32
                or retained_actual.device.type != "cpu"
                or not torch.isfinite(retained_actual).all()
                or not torch.equal(actual, retained_actual)
            ):
                raise ValueError("actual Adam delta")
            if (
                not torch.is_tensor(retained_cumulative)
                or retained_cumulative.dtype != torch.float32
                or retained_cumulative.device.type != "cpu"
                or not torch.isfinite(retained_cumulative).all()
                or not torch.equal(cumulative, retained_cumulative)
            ):
                raise ValueError("cumulative parameter delta")
            retained_parameters = item.get("policy_parameter_state_after") or {}
            if tuple(retained_parameters) != PARAMETER_NAMES or any(
                not torch.equal(parameters[name], retained_parameters[name])
                for name in PARAMETER_NAMES
            ):
                raise ValueError("per-update parameter state")
            if not _nested_byte_exact_v2(
                optimizer_state, item.get("optimizer_state_after")
            ):
                mismatch = _optimizer_state_mismatch_v4(
                    optimizer_state, item.get("optimizer_state_after")
                )
                raise ValueError(f"per-update optimizer state:{mismatch}")
            expected_counters = {
                **{name: update for name in PARAMETER_NAMES},
                **{name: 1 for name in base.STAGE1_TRAINABLE_NAMES},
            }
            if (
                item.get("optimizer_step_counters") != expected_counters
                or _optimizer_step_counters_from_state(optimizer_state)
                != expected_counters
            ):
                raise ValueError("optimizer step counters")
            outputs[update] = _metrics_from_ordered_output(
                item.get("ordered_outputs") or {},
                prepare_receipt,
                update_ordinal=update,
            )
            if update in (48, 64):
                projections[str(update)] = {
                    task: float(torch.dot(-raw[task], cumulative.to(torch.float64)))
                    for task in PRIORITY_TASKS
                }
            _ = total_norm, coefficient
        except Exception as error:
            failures.append(f"update:{update}:{type(error).__name__}:{error}")
    return {
        "passed": not failures, "failures": failures,
        "final_parameters": parameters,
        "final_model_state": {
            name: (
                parameters[name].clone()
                if name in parameters else value.detach().cpu().clone()
            )
            for name, value in model_state.items()
        },
        "final_optimizer_state": optimizer_state,
        "outputs": outputs,
        "surgery_tasks_first16": sorted(surgery_tasks),
        "surgery_by_update": surgery_by_update,
        "cumulative_projections": projections,
        "start_flat_sha256": _tensor_sha256_v2(start_flat),
    }


def _ppo_clip_active_count_from_outputs(
    output: Mapping[str, Any], prepare_receipt: Mapping[str, Any]
) -> int:
    probabilities = output["probabilities"]
    offsets = output["probability_offsets"]
    active = 0
    for ordinal, fixed in enumerate(prepare_receipt["rows"]):
        selected = int(fixed["sampled_index"])
        probability = float(probabilities[int(offsets[ordinal]) + selected])
        old = float(fixed["behavior_logprob_float64"])
        ratio = math.exp(math.log(probability) - old)
        advantage = float(fixed["fixed_normalized_advantage_float32"])
        unclipped = ratio * advantage
        clipped = min(1.1, max(0.9, ratio)) * advantage
        if clipped < unclipped:
            active += 1
    return active


def _strict_alignment_threshold_failures_v2(
    *,
    update: int,
    control_summary: Mapping[str, Any],
    treatment_summary: Mapping[str, Any],
    difference: Mapping[str, Any],
) -> list[str]:
    failures: list[str] = []
    expected_priority = set(PRIORITY_TASKS)
    expected_families = {
        f"{family}:{polarity}"
        for family in OPTION_TYPE_BY_FAMILY
        for polarity in ("positive", "negative")
    }
    if set(treatment_summary.get("priority") or {}) != expected_priority:
        return [f"priority_key_set:{update}"]
    if set(difference.get("priority") or {}) != expected_priority:
        return [f"difference_priority_key_set:{update}"]
    for task in PRIORITY_TASKS:
        if treatment_summary["priority"][task]["lower_empirical_median"] < 1e-6:
            failures.append(f"treatment_priority:{task}:{update}")
        if difference["priority"][task]["lower_empirical_median"] < 1e-6:
            failures.append(f"difference_priority:{task}:{update}")
    families = treatment_summary.get("all_12_family_polarity_lower_medians") or {}
    if set(families) != expected_families:
        failures.append(f"family_key_set:{update}")
    elif any(float(families[key]) <= 1e-7 for key in expected_families):
        failures.append(f"family_floor:{update}")
    global_summary = treatment_summary.get("global") or {}
    if global_summary.get("lower_empirical_median", -math.inf) < 1e-5:
        failures.append(f"global_median:{update}")
    if global_summary.get("alignment_score", -math.inf) < 0.10:
        failures.append(f"global_alignment:{update}")
    weighted = global_summary.get("weighted_lower_medians") or {}
    if update == 64:
        if weighted.get("raw_GAE_absolute_target", -math.inf) < 0.0:
            failures.append(f"raw_GAE:{update}")
        if weighted.get("Monte_Carlo_absolute_target", -math.inf) < 0.0:
            failures.append(f"Monte_Carlo:{update}")
        if treatment_summary.get(
            "sign_stable_611_lower_empirical_median", -math.inf
        ) < 0.0:
            failures.append(f"sign_stable_611:{update}")
        for task in PRIORITY_TASKS:
            priority_weighted = treatment_summary["priority"][task].get(
                "weighted_lower_medians"
            ) or {}
            for view in (
                "ordinary_absolute_normalized_advantage",
                "equal_exact_public_state",
                "equal_source_trajectory",
            ):
                if priority_weighted.get(view, -math.inf) < 1e-6:
                    failures.append(f"priority_weighted:{task}:{view}")
        control_priority = control_summary.get("priority") or {}
        if set(control_priority) != expected_priority or all(
            control_priority[task]["lower_empirical_median"] >= 1e-6
            for task in PRIORITY_TASKS
        ):
            failures.append("control_must_fail_one_priority_group")
    return failures


def _strict_numerical_gates_from_replay(
    gradients: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    control_replay: Mapping[str, Any],
    treatment_replay: Mapping[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    details: dict[str, Any] = {
        "updates": {}, "safety": {}, "step_scalars": {},
        "mechanism": {}, "END": None,
    }
    if control_replay.get("passed") is not True:
        failures.extend(f"control_replay:{value}" for value in control_replay.get("failures") or ())
    if treatment_replay.get("passed") is not True:
        failures.extend(f"treatment_replay:{value}" for value in treatment_replay.get("failures") or ())
    completed = int(gradients.get("completed_synchronized_stage2_updates", -1))
    if completed != STAGE2_UPDATES:
        failures.append("completed_updates")
    start_treatment = (
        (gradients.get("stage2_start_states") or {})
        .get("treatment_pcgrad", {}).get("stage1_outputs")
    )
    for update in range(1, min(completed, STAGE2_UPDATES) + 1):
        for arm, replay in (
            ("control_vanilla", control_replay),
            ("treatment_pcgrad", treatment_replay),
        ):
            metrics = (replay.get("outputs") or {}).get(update)
            if metrics is None:
                failures.append(f"missing_outputs:{arm}:{update}")
                continue
            value_identity = base.value_change_summary(prepare_receipt, metrics)
            value_contract_pass = (
                value_identity["all_rows_byte_exact_to_initial"]
                and value_identity["raw_value_mse_exact_to_initial"]
                and value_identity["aggregate_hash_exact_to_initial"]
            )
            safety = base.evaluate_stage_gates(
                prepare_receipt, metrics, stage=2,
                stage_2_update_ordinal=update,
                training_nonfinite_count=0,
                parameter_optimizer_contract_pass=replay.get("passed") is True,
                value_contract_pass=value_contract_pass,
            )
            try:
                starts = gradients.get("stage2_start_states") or {}
                series = gradients.get("series") or {}
                previous_output = (
                    (starts.get(arm) or {}).get("stage1_outputs")
                    if update == 1 else (
                        series.get(f"updates/{update - 1:02d}/{arm}") or {}
                    ).get("ordered_outputs")
                )
                if not isinstance(previous_output, Mapping):
                    raise ValueError("previous ordered output is missing")
                scalars = _recompute_step_scalars_v2(
                    previous_output, prepare_receipt
                )
                if any(
                    isinstance(value, float) and not math.isfinite(value)
                    for value in scalars.values()
                ):
                    raise ValueError("recomputed step scalar is nonfinite")
                details["step_scalars"][f"{arm}:{update}"] = scalars
                clip_active = int(scalars["clip_active_row_count"])
            except Exception as error:
                failures.append(
                    f"step_scalars:{arm}:{update}:{type(error).__name__}:{error}"
                )
                details["step_scalars"][f"{arm}:{update}"] = None
                clip_active = -1
                safety = copy.deepcopy(safety)
                safety["global_failures"] = [
                    *safety.get("global_failures", []),
                    "global:raw_step_scalar_recomputation",
                ]
                safety["safety_pass"] = False
                safety["hard_stop"] = True
            if update in DIAGNOSTIC_UPDATES and clip_active != 0:
                safety = copy.deepcopy(safety)
                safety["global_failures"] = [
                    *safety.get("global_failures", []),
                    "global:PPO_clip_active_rows",
                ]
                safety["safety_pass"] = False
            details["safety"][f"{arm}:{update}"] = {
                "pass": safety["safety_pass"] is True,
                "hard_stop": safety.get("hard_stop") is True,
                "failures": list(safety.get("global_failures") or ()),
                "clip_active_row_count": clip_active,
                "mean_anchor_kl": safety["mean_anchor_kl"],
                "maximum_anchor_kl": safety["maximum_anchor_kl"],
                "maximum_total_variation": safety["maximum_total_variation"],
                "value_contract_pass": value_contract_pass,
            }
            if safety["safety_pass"] is not True:
                failures.append(f"safety:{arm}:{update}")
    expected_priority = set(PRIORITY_TASKS)
    for update in (48, 64):
        control = (control_replay.get("outputs") or {}).get(update)
        treatment = (treatment_replay.get("outputs") or {}).get(update)
        if control is None or treatment is None:
            failures.append(f"numerical_outputs:{update}")
            continue
        control_summary = _alignment_summary_for_metrics(prepare_receipt, control)
        treatment_summary = _alignment_summary_for_metrics(prepare_receipt, treatment)
        difference = _difference_alignment_summary(
            prepare_receipt, control, treatment
        )
        details["updates"][str(update)] = {
            "control": control_summary,
            "treatment": treatment_summary,
            "treatment_minus_control": difference,
        }
        failures.extend(_strict_alignment_threshold_failures_v2(
            update=update, control_summary=control_summary,
            treatment_summary=treatment_summary, difference=difference,
        ))
    touched = set(treatment_replay.get("surgery_tasks_first16") or ())
    projections = treatment_replay.get("cumulative_projections") or {}
    details["mechanism"] = {
        "surgery_nonzero": bool(touched),
        "tasks_touched_first_16": sorted(touched),
        "cumulative_delta_projections": projections,
    }
    if not touched:
        failures.append("surgery_nonzero")
    if not set(AUDIT_ADVERSE_TASKS).issubset(touched):
        failures.append("adverse_tasks_first16")
    for update in (48, 64):
        values = projections.get(str(update)) or {}
        if set(values) != expected_priority or any(
            float(values[task]) <= 0.0 for task in PRIORITY_TASKS
        ):
            failures.append(f"cumulative_projection:{update}")
    terminal_metrics = (treatment_replay.get("outputs") or {}).get(64)
    if terminal_metrics is None:
        failures.append("END:missing")
    else:
        details["END"] = terminal_end_controls(
            prepare_receipt, terminal_metrics
        )
        if details["END"]["passed"] is not True:
            failures.extend(
                f"END:{value}" for value in details["END"].get("failures") or ()
            )
    _ = start_treatment
    return {
        "passed": not failures,
        "failures": sorted(set(failures)),
        "details": details,
    }


def _checkpoint_cross_binding_v2(
    path: Path,
    *,
    arm: str,
    spec: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    replay: Mapping[str, Any],
    expected_output_metrics: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    failures: list[str] = []
    raw: dict[str, Any] = {}
    try:
        raw = torch.load(path, map_location="cpu", weights_only=False)
        if set(raw) != {"model_config", "model_state", "metadata", "optimizer_state"}:
            raise ValueError("checkpoint key set")
        publication = raw["metadata"].get("pcgrad_publication") or {}
        immutable_source_hashes = inherited.checkpoint_source_hashes()
        expected_terminal_hashes = base._ordered_output_hashes(
            expected_output_metrics
        )
        expected_publication = {
            "status": "PENDING_AUDIT", "arm": arm,
            "plan_path": PLAN_RELATIVE_PATH.as_posix(),
            "plan_sha256": PLAN_SHA256,
            "correction_path": CORRECTION_RELATIVE_PATH.as_posix(),
            "correction_sha256": CORRECTION_SHA256,
            "correction_v2_path": CORRECTION_V2_RELATIVE_PATH.as_posix(),
            "correction_v2_sha256": CORRECTION_V2_SHA256,
            "correction_v3_path": CORRECTION_V3_RELATIVE_PATH.as_posix(),
            "correction_v3_sha256": CORRECTION_V3_SHA256,
            "correction_v4_path": CORRECTION_V4_RELATIVE_PATH.as_posix(),
            "correction_v4_sha256": CORRECTION_V4_SHA256,
            "correction_v5_path": CORRECTION_V5_RELATIVE_PATH.as_posix(),
            "correction_v5_sha256": CORRECTION_V5_SHA256,
            "predecessor_execution_stop": copy.deepcopy(
                prepare_receipt["predecessor_execution_stop"]
            ),
            "implementation_path": IMPLEMENTATION_RELATIVE_PATH.as_posix(),
            "implementation_snapshot_file_count": spec[
                "implementation_snapshot_file_count"
            ],
            "implementation_snapshot_sha256": spec["implementation_snapshot_sha256"],
            "execution_spec_sha256": spec["_file_sha256"],
            "prepare_receipt_sha256": prepare_receipt["receipt_sha256"],
            "synchronized_optimizer_steps": 65,
            "source_hashes": immutable_source_hashes,
            "terminal_output_hashes": expected_terminal_hashes,
            "games_run": 0,
        }
        failures.extend(_checkpoint_publication_failures_v2(
            publication, expected_publication
        ))
        model, _metadata, optimizer_state = load_checkpoint(
            path, expected_source_hashes=immutable_source_hashes, device="cpu"
        )
        failures.extend(_checkpoint_state_failures_v2(
            model.state_dict(), optimizer_state,
            replay.get("final_model_state"),
            replay.get("final_optimizer_state"),
        ))
        loaded = inherited._load_validated_inputs()
        loaded["model"] = model
        checkpoint_metrics = base._measure_stage(
            loaded, prepare_receipt, stage=2, stage_2_update_ordinal=64
        )
        output_hashes, output_failures = _checkpoint_output_failures_v2(
            checkpoint_metrics=checkpoint_metrics,
            expected_output_metrics=expected_output_metrics,
            publication_terminal_hashes=publication.get(
                "terminal_output_hashes"
            ),
        )
        failures.extend(output_failures)
        optimizer_record = _optimizer_canonical_record_from_state_v3(
            optimizer_state
        )
        optimizer_steps = _optimizer_step_counters_from_state(optimizer_state)
        return {
            "passed": not failures,
            "failures": failures,
            "model_parameter_hashes": _model_parameter_hashes(model),
            "optimizer_canonical": optimizer_record,
            "optimizer_state_steps": optimizer_steps,
            "output_hashes": output_hashes,
            "summary_evidence": {
                "runtime_loader_pass": True,
                "model_state_byte_exact": not any(
                    value.startswith("final_model") for value in failures
                ),
                "optimizer_state_byte_exact": "final_optimizer" not in failures,
                "metadata_exact": not any(
                    value.startswith("metadata:") for value in failures
                ),
                "optimizer_state_steps": optimizer_steps,
                "terminal_output_row_count": len(checkpoint_metrics),
                "terminal_output_hashes": output_hashes,
            },
        }, failures, raw
    except Exception as error:
        failures.append(f"load:{type(error).__name__}:{error}")
        return {"passed": False, "failures": failures}, failures, raw


def _checkpoint_publication_failures_v2(
    publication: Any, expected: Mapping[str, Any]
) -> list[str]:
    if not isinstance(publication, Mapping):
        return ["metadata:not_mapping"]
    failures: list[str] = []
    if set(publication) != set(expected):
        failures.append("metadata:key_set")
    for key, value in expected.items():
        if not _nested_byte_exact_v2(publication.get(key), value):
            failures.append(f"metadata:{key}")
    return failures


def _checkpoint_state_failures_v2(
    checkpoint_model_state: Any,
    checkpoint_optimizer_state: Any,
    replay_model_state: Any,
    replay_optimizer_state: Any,
) -> list[str]:
    failures: list[str] = []
    if not isinstance(checkpoint_model_state, Mapping) or not isinstance(
        replay_model_state, Mapping
    ):
        failures.append("final_model_mapping")
    elif set(checkpoint_model_state) != set(replay_model_state):
        failures.append("final_model_key_set")
    else:
        for name in checkpoint_model_state:
            if not _nested_byte_exact_v2(
                checkpoint_model_state[name], replay_model_state[name]
            ):
                failures.append(f"final_model:{name}")
    if not _nested_byte_exact_v2(
        checkpoint_optimizer_state, replay_optimizer_state
    ):
        failures.append("final_optimizer")
    return failures


def _checkpoint_output_failures_v2(
    *,
    checkpoint_metrics: Sequence[Mapping[str, Any]],
    expected_output_metrics: Sequence[Mapping[str, Any]],
    publication_terminal_hashes: Any,
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    expected_hashes = base._ordered_output_hashes(expected_output_metrics)
    checkpoint_hashes = base._ordered_output_hashes(checkpoint_metrics)
    if canonical_json_bytes(checkpoint_metrics) != canonical_json_bytes(
        expected_output_metrics
    ):
        failures.append("update64_outputs")
    if checkpoint_hashes != expected_hashes:
        failures.append("recomputed_terminal_output_hashes")
    if publication_terminal_hashes != checkpoint_hashes:
        failures.append("metadata_terminal_output_hashes")
    return checkpoint_hashes, failures


def _control32_cross_binding_v2(
    gradients: Mapping[str, Any],
    control_replay: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    checkpoint_raw: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    try:
        retained = gradients.get("control_update32_state") or {}
        item = gradients["series"]["updates/32/control_vanilla"]
        for name in PARAMETER_NAMES:
            if not torch.equal(
                retained["model_state"][name],
                item["policy_parameter_state_after"][name],
            ):
                failures.append(f"model_state:{name}")
        if not _nested_byte_exact_v2(
            retained.get("optimizer_state"), item.get("optimizer_state_after")
        ):
            failures.append("optimizer_state")
        metrics = control_replay["outputs"][32]
        if not _nested_byte_exact_v2(
            retained.get("ordered_outputs"), item.get("ordered_outputs")
        ):
            failures.append("ordered_outputs")
        legacy = copy.deepcopy(retained.get("legacy_record") or {})
        legacy_claim = legacy.pop("record_hash", None)
        if legacy_claim != canonical_sha256(legacy):
            failures.append("legacy_record_chain")
        model = ResidualActorCritic(ModelConfig(**checkpoint_raw["model_config"]))
        model.load_state_dict(retained["model_state"], strict=True)
        base._set_trainability(model, stage=2)
        outputs = base._ordered_output_hashes(metrics)
        optimizer_record = _optimizer_canonical_record_from_state_v3(
            retained["optimizer_state"]
        )
        evidence = {
            "record_sha256": (retained.get("legacy_record") or {}).get("record_hash"),
            **outputs,
            "parameter_bytes_sha256": {
                name: _tensor_sha256_v2(model.state_dict()[name])
                for name in REFERENCE_CONTROL["stage32_parameter_bytes_sha256"]
            },
            "optimizer_canonical_sha256": optimizer_record["canonical_sha256"],
            "optimizer_param_group_canonical_sha256": optimizer_record[
                "param_group_canonical_sha256"
            ],
            "optimizer_state_steps": _optimizer_step_counters_from_state(
                retained["optimizer_state"]
            ),
        }
        validated = validate_control_update32(evidence)
        if validated.get("passed") is not True:
            failures.append("immutable_reference")
        return {"passed": not failures, "failures": failures, "evidence": evidence}, failures
    except Exception as error:
        failures.append(f"control32:{type(error).__name__}:{error}")
        return {"passed": False, "failures": failures}, failures


def _duplicate_cross_binding_v2(
    gradients: Mapping[str, Any],
    treatment_replay: Mapping[str, Any],
    treatment_checkpoint_raw: Mapping[str, Any],
    treatment_step_rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    try:
        duplicate = gradients.get("duplicate_treatment_state") or {}
        if not _nested_byte_exact_v2(
            duplicate.get("model_state"), treatment_checkpoint_raw.get("model_state")
        ):
            failures.append("model_state")
        if not _nested_byte_exact_v2(
            duplicate.get("model_state"), treatment_replay.get("final_model_state")
        ):
            failures.append("replayed_model_state")
        if not _nested_byte_exact_v2(
            duplicate.get("optimizer_state"),
            treatment_replay.get("final_optimizer_state"),
        ):
            failures.append("optimizer_state")
        if not _nested_byte_exact_v2(
            duplicate.get("optimizer_state"),
            treatment_checkpoint_raw.get("optimizer_state"),
        ):
            failures.append("checkpoint_optimizer_state")
        primary_output = gradients["series"][
            "updates/64/treatment_pcgrad"
        ]["ordered_outputs"]
        if not _nested_byte_exact_v2(
            duplicate.get("ordered_outputs"), primary_output
        ):
            failures.append("ordered_outputs")
        primary_chain = [row.get("step_record_sha256") for row in treatment_step_rows]
        if duplicate.get("per_update_record_hashes") != primary_chain:
            failures.append("record_chain")
        terminal_hash = primary_chain[-1] if primary_chain else None
        return {
            "passed": not failures, "failures": failures,
            "terminal_step_sha256": terminal_hash,
            "record_chain_sha256": canonical_sha256(primary_chain),
        }, failures
    except Exception as error:
        failures.append(f"duplicate:{type(error).__name__}:{error}")
        return {"passed": False, "failures": failures}, failures


def _stage1_cross_binding_v2(
    gradients: Mapping[str, Any],
    stage1_rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str], list[str]]:
    failures: list[str] = []
    discrepancies: list[str] = []
    arms = ("control_vanilla", "treatment_pcgrad")
    starts = gradients.get("stage2_start_states") or {}
    expected_start_keys = {
        "model_state", "optimizer_state", "stage1_report", "stage1_safety",
        "stage1_value_identity", "stage1_record_sha256", "stage1_outputs",
    }
    if set(starts) != set(arms):
        return ({"passed": False}, ["stage1_start_arm_set"], discrepancies)
    for arm in arms:
        if set(starts[arm]) != expected_start_keys:
            failures.append(f"stage1_start_key_set:{arm}")
    by_arm: dict[str, list[Any]] = {arm: [None] * EXPECTED_ROWS for arm in arms}
    first_evidence: dict[str, Any] = {}
    for row in stage1_rows:
        arm = row.get("arm")
        ordinal = row.get("row_ordinal")
        if arm not in by_arm or not isinstance(ordinal, int) or not 0 <= ordinal < EXPECTED_ROWS:
            failures.append("stage1_row_key")
            continue
        if by_arm[arm][ordinal] is not None:
            failures.append(f"stage1_duplicate:{arm}:{ordinal}")
            continue
        if row.get("stage1_record_sha256") != starts[arm].get("stage1_record_sha256"):
            failures.append(f"stage1_row_record:{arm}:{ordinal}")
        if ordinal == 0:
            first_evidence[arm] = row.get("complete_stage1_evidence")
            if row.get("optimizer_state_reference") != (
                f"stage2_start_states/{arm}/optimizer_state"
            ):
                failures.append(f"stage1_optimizer_reference:{arm}")
        elif (
            row.get("complete_stage1_evidence") is not None
            or row.get("optimizer_state_reference") is not None
        ):
            failures.append(f"stage1_repeated_complete_evidence:{arm}:{ordinal}")
        by_arm[arm][ordinal] = row.get("diagnostic")
    if any(value is None for rows in by_arm.values() for value in rows):
        failures.append("stage1_row_completeness")
    if not _nested_byte_exact_v2(
        starts[arms[0]].get("model_state"), starts[arms[1]].get("model_state")
    ):
        failures.append("stage1_model_state_equality")
    if not _nested_byte_exact_v2(
        starts[arms[0]].get("optimizer_state"),
        starts[arms[1]].get("optimizer_state"),
    ):
        failures.append("stage1_optimizer_state_equality")
    for field in (
        "stage1_report", "stage1_safety", "stage1_value_identity",
        "stage1_record_sha256", "stage1_outputs",
    ):
        if not _nested_byte_exact_v2(starts[arms[0]].get(field), starts[arms[1]].get(field)):
            failures.append(f"stage1_{field}_equality")
    if by_arm[arms[0]][0] is not None and canonical_json_bytes(
        by_arm[arms[0]]
    ) != canonical_json_bytes(by_arm[arms[1]]):
        failures.append("stage1_complete_diagnostic_equality")
    output_hashes: dict[str, Any] = {}
    for arm in arms:
        start = starts[arm]
        if start.get("stage1_record_sha256") != REFERENCE_CONTROL["stage1_record_sha256"]:
            failures.append(f"stage1_immutable_record:{arm}")
        try:
            rebuilt_output = _ordered_output_tensor_evidence(by_arm[arm])
            if not _nested_byte_exact_v2(rebuilt_output, start.get("stage1_outputs")):
                failures.append(f"stage1_output_tensor:{arm}")
            output_hashes[arm] = base._ordered_output_hashes(by_arm[arm])
            if output_hashes[arm]["ordered_probability_bytes_sha256"] != (
                REFERENCE_CONTROL["stage1_ordered_probability_bytes_sha256"]
            ):
                failures.append(f"stage1_probability_reference:{arm}")
            if output_hashes[arm]["ordered_value_bytes_sha256"] != (
                REFERENCE_CONTROL["ordered_value_bytes_sha256"]
            ):
                failures.append(f"stage1_value_reference:{arm}")
            record = canonical_sha256({
                "stage_1_report": start["stage1_report"],
                "stage_1_safety": start["stage1_safety"],
                "stage_1_value_identity": start["stage1_value_identity"],
                **output_hashes[arm],
            })
            if record != start.get("stage1_record_sha256"):
                failures.append(f"stage1_record_recomputation:{arm}")
        except Exception as error:
            failures.append(f"stage1_output:{arm}:{type(error).__name__}:{error}")
        evidence = first_evidence.get(arm)
        if not isinstance(evidence, Mapping):
            failures.append(f"stage1_complete_evidence:{arm}")
            continue
        expected_losses = {
            "loss": start["stage1_report"]["loss"],
            "policy_loss": start["stage1_report"]["policy_loss"],
            "anchor_kl": start["stage1_report"]["pre_step_mean_anchor_kl"],
            "entropy": start["stage1_report"]["entropy"],
        }
        expected_fixed = {
            "fixed_advantages_sha256": start["stage1_report"][
                "fixed_advantages_sha256"
            ],
            "fixed_behavior_logprobabilities_sha256": start["stage1_report"][
                "fixed_behavior_logprobabilities_sha256"
            ],
            "row_count": EXPECTED_ROWS,
        }
        raw_model_hashes = {
            name: _tensor_sha256_v2(value)
            for name, value in start["model_state"].items()
        }
        checks = {
            "stage1_record_sha256": start["stage1_record_sha256"],
            "stage1_report": start["stage1_report"],
            "stage1_safety": start["stage1_safety"],
            "stage1_value_identity": start["stage1_value_identity"],
            "model_parameter_hashes": raw_model_hashes,
            "model_state_hashes": raw_model_hashes,
            "output_hashes": output_hashes.get(arm),
            "losses": expected_losses,
            "fixed_input_identities": expected_fixed,
        }
        for field, expected in checks.items():
            if canonical_json_bytes(evidence.get(field)) != canonical_json_bytes(expected):
                failures.append(f"stage1_complete_evidence:{arm}:{field}")
        summary_evidence = (summary.get("stage1_complete_evidence") or {}).get(arm)
        if canonical_json_bytes(summary_evidence) != canonical_json_bytes(evidence):
            discrepancies.append(f"stage1_complete_evidence:{arm}")
    if canonical_json_bytes(first_evidence.get(arms[0])) != canonical_json_bytes(
        first_evidence.get(arms[1])
    ):
        failures.append("stage1_complete_evidence_arm_equality")
    summary_records = summary.get("stage1_record_hashes") or {}
    expected_records = {
        arm: starts[arm].get("stage1_record_sha256") for arm in arms
    }
    if canonical_json_bytes(summary_records) != canonical_json_bytes(expected_records):
        discrepancies.append("stage1_record_hashes")
    derived_pass = not failures
    expected_stage1_equality = {
        "passed": derived_pass,
        "compared_fields": list(STAGE1_COMPARED_FIELDS),
    }
    if canonical_json_bytes(summary.get("stage1_equality")) != canonical_json_bytes(
        expected_stage1_equality
    ):
        discrepancies.append("stage1_equality")
    return {
        "passed": derived_pass,
        "failures": sorted(set(failures)),
        "row_count": len(stage1_rows),
        "output_hashes": output_hashes,
        "record_hashes": expected_records,
        "summary_stage1_equality": expected_stage1_equality,
        "summary_complete_evidence": copy.deepcopy(first_evidence),
    }, failures, discrepancies


def _recompute_step_scalars_v2(
    output: Mapping[str, Any], prepare_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    probabilities = output.get("probabilities")
    offsets = output.get("probability_offsets")
    if not torch.is_tensor(probabilities) or not torch.is_tensor(offsets):
        raise ValueError("pre-step output tensors are missing")
    policy_terms: list[torch.Tensor] = []
    anchor_terms: list[torch.Tensor] = []
    entropy_terms: list[torch.Tensor] = []
    ratios: list[float] = []
    active: list[int] = []
    for ordinal, fixed in enumerate(prepare_receipt["rows"]):
        begin, end = int(offsets[ordinal]), int(offsets[ordinal + 1])
        current = probabilities[begin:end]
        initial = torch.tensor(
            fixed["initial_probabilities_float32"], dtype=torch.float32
        )
        selected = int(fixed["sampled_index"])
        old = torch.tensor(float(fixed["behavior_logprob_float64"]), dtype=torch.float32)
        advantage = torch.tensor(
            float(fixed["fixed_normalized_advantage_float32"]), dtype=torch.float32
        )
        ratio = torch.exp(torch.log(current[selected]) - old)
        unclipped = ratio * advantage
        clipped = torch.clamp(ratio, 0.9, 1.1) * advantage
        policy_terms.append(-torch.minimum(unclipped, clipped))
        anchor_terms.append((current * (torch.log(current) - torch.log(initial))).sum())
        entropy_terms.append(-(current * torch.log(current)).sum())
        ratios.append(float(ratio))
        if float(clipped) < float(unclipped):
            active.append(ordinal)
    policy = torch.stack(policy_terms).mean()
    anchor = ANCHOR_KL_COEFFICIENT * torch.stack(anchor_terms).mean()
    return {
        "loss": float(policy + anchor),
        "policy_loss": float(policy),
        "anchor_kl_loss": float(anchor),
        "entropy": float(torch.stack(entropy_terms).mean()),
        "clip_active_row_count": len(active),
        "clip_active_row_ordinals": active,
        "PPO_ratio_minimum": min(ratios),
        "PPO_ratio_maximum": max(ratios),
    }


def _caller_summary_discrepancies_v2(
    *,
    summary: Mapping[str, Any],
    step_by_key: Mapping[tuple[str, int], Mapping[str, Any]],
    gradients: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    numeric: Mapping[str, Any],
    control_replay: Mapping[str, Any],
    treatment_replay: Mapping[str, Any],
    control32: Mapping[str, Any],
    duplicate: Mapping[str, Any],
    raw_pass_before_discrepancies: bool,
) -> list[str]:
    discrepancies: list[str] = []
    safety_details = (numeric.get("details") or {}).get("safety") or {}
    expected_safety_keys = {
        f"{arm}:{update}"
        for arm in ("control_vanilla", "treatment_pcgrad")
        for update in range(1, STAGE2_UPDATES + 1)
    }
    all_safety = (
        set(safety_details) == expected_safety_keys
        and all(
            (safety_details.get(key) or {}).get("pass") is True
            and (safety_details.get(key) or {}).get("hard_stop") is not True
            for key in expected_safety_keys
        )
    )
    if summary.get("all_safety_gates_pass") is not all_safety:
        discrepancies.append("all_safety_gates_pass")
    raw_mechanism = (numeric.get("details") or {}).get("mechanism") or {}
    caller_mechanism = summary.get("mechanism") or {}
    for field in (
        "surgery_nonzero", "tasks_touched_first_16",
        "cumulative_delta_projections",
    ):
        if canonical_json_bytes(caller_mechanism.get(field)) != canonical_json_bytes(
            raw_mechanism.get(field)
        ):
            discrepancies.append(f"mechanism.{field}")
    if (summary.get("control_update32_reference") or {}).get("passed") is not (
        control32.get("passed") is True
    ):
        discrepancies.append("control_update32_reference.passed")
    if summary.get("duplicate_treatment_canonical_outputs_identical") is not (
        duplicate.get("passed") is True
    ):
        discrepancies.append("duplicate_treatment_canonical_outputs_identical")
    raw_end = (numeric.get("details") or {}).get("END") or {}
    if (summary.get("terminal_END_controls") or {}).get("passed") is not (
        raw_end.get("passed") is True
    ):
        discrepancies.append("terminal_END_controls.passed")
    if (summary.get("strict_offline_gates") or {}).get("offline_pass") is not (
        raw_pass_before_discrepancies
    ):
        discrepancies.append("strict_offline_gates.offline_pass")
    _ = step_by_key, gradients, prepare_receipt, control_replay, treatment_replay
    return sorted(set(discrepancies))


def _run_summary_exact_discrepancies_v3(
    summary: Mapping[str, Any], expected_non_hash_fields: Mapping[str, Any]
) -> list[str]:
    expected_fields = RUN_SUMMARY_KEYS_V2 - {"run_summary_sha256"}
    if set(expected_non_hash_fields) != expected_fields:
        raise AssertionError("v3 run summary authority field set is incomplete")
    discrepancies: list[str] = []
    if set(summary) != RUN_SUMMARY_KEYS_V2:
        discrepancies.append("run_summary:key_set")
    for field in sorted(expected_fields):
        if not _nested_byte_exact_v2(
            summary.get(field), expected_non_hash_fields[field]
        ):
            discrepancies.append(f"run_summary:{field}")
    return discrepancies


def _pending_checkpoint_gate(
    path: Path,
    *,
    arm: str,
    expected_steps: int,
    expected_spec_sha256: str,
    expected_prepare_sha256: str,
    terminal_output_hashes: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    try:
        raw = torch.load(path, map_location="cpu", weights_only=False)
        if set(raw) != {"model_config", "model_state", "metadata", "optimizer_state"}:
            failures.append("checkpoint_key_set")
        publication = (raw.get("metadata") or {}).get("pcgrad_publication") or {}
        expected_binding = {
            "arm": arm, "status": "PENDING_AUDIT",
            "execution_spec_sha256": expected_spec_sha256,
            "prepare_receipt_sha256": expected_prepare_sha256,
            "synchronized_optimizer_steps": expected_steps,
            "games_run": 0,
        }
        for key, value in expected_binding.items():
            if publication.get(key) != value:
                failures.append(f"checkpoint_metadata:{key}")
        if publication.get("terminal_output_hashes") != terminal_output_hashes:
            failures.append("checkpoint_terminal_outputs")
        source_hashes = publication.get("source_hashes")
        model, _metadata, optimizer_state = load_checkpoint(
            path, expected_source_hashes=source_hashes, device="cpu"
        )
        optimizer = base._new_actor_adam(model)
        optimizer.load_state_dict(copy.deepcopy(optimizer_state))
        steps = optimizer_step_states(optimizer, model)
        if expected_steps == 65:
            expected = {
                **{name: 64 for name in PARAMETER_NAMES},
                **{name: 1 for name in base.STAGE1_TRAINABLE_NAMES},
            }
            if steps != expected:
                failures.append("checkpoint_optimizer_steps")
        elif expected_steps == 0 and steps:
            failures.append("checkpoint_zero_step_optimizer")
        elif expected_steps not in (0, 65) and not steps:
            failures.append("checkpoint_missing_optimizer_steps")
        return {
            "model_parameter_hashes": _model_parameter_hashes(model),
            "optimizer_canonical": optimizer_canonical_record(optimizer, model),
            "optimizer_state_steps": steps,
            "terminal_output_hashes": publication.get("terminal_output_hashes"),
        }, failures
    except Exception as error:
        failures.append(f"checkpoint_load:{type(error).__name__}:{error}")
        return {}, failures


def _recompute_pending_gates_v1_shape_only(
    *,
    spec: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    manifest_path: Path,
    manifest_sha256: str,
) -> dict[str, Any]:
    """Retained v1 shape-only review evidence; not finalization authority."""

    manifest, failures = _load_pending_manifest(manifest_path, manifest_sha256)
    directory = manifest_path.parent
    if manifest.get("execution_spec_sha256") != spec.get("_file_sha256"):
        failures.append("manifest_execution_spec")
    if manifest.get("prepare_receipt_sha256") != prepare_receipt["receipt_sha256"]:
        failures.append("manifest_prepare_receipt")
    required_readable = (
        "run_summary.json", "stage1_diagnostics.jsonl",
        "milestone_diagnostics.jsonl", "step_summaries.jsonl",
        "gradient_tensors.pt", "control_pending.pt", "treatment_pending.pt",
    )
    if any(not (directory / name).is_file() for name in required_readable):
        return {
            "offline_pass": False, "bundle_integrity_pass": False,
            "failures": sorted(set(failures + ["missing_required_evidence"])),
            "recomputed": {},
        }
    summary = json.loads((directory / "run_summary.json").read_text("utf-8"))
    summary_core = dict(summary)
    summary_claim = summary_core.pop("run_summary_sha256", None)
    if summary_claim != canonical_sha256(summary_core):
        failures.append("run_summary_self_hash")
    stage1_rows = _read_jsonl(directory / "stage1_diagnostics.jsonl")
    milestone_rows = _read_jsonl(directory / "milestone_diagnostics.jsonl")
    step_rows = _read_jsonl(directory / "step_summaries.jsonl")
    gradients = torch.load(
        directory / "gradient_tensors.pt", map_location="cpu", weights_only=True
    )
    completed_updates = int(manifest.get("completed_synchronized_stage2_updates", -1))
    completed_steps = manifest.get("completed_optimizer_steps_per_arm")
    if completed_steps != {
        "control_vanilla": 1 + completed_updates,
        "treatment_pcgrad": 1 + completed_updates,
    }:
        failures.append("manifest_synchronized_steps")
    if len(stage1_rows) != 2 * EXPECTED_ROWS:
        failures.append("stage1_row_count")
    stage1_by_arm: dict[str, list[Any]] = {
        "control_vanilla": [None] * EXPECTED_ROWS,
        "treatment_pcgrad": [None] * EXPECTED_ROWS,
    }
    for row in stage1_rows:
        arm = row.get("arm")
        ordinal = row.get("row_ordinal")
        if arm not in stage1_by_arm or not isinstance(ordinal, int) or not 0 <= ordinal < EXPECTED_ROWS:
            failures.append("stage1_key")
            continue
        if stage1_by_arm[arm][ordinal] is not None:
            failures.append("stage1_duplicate")
        stage1_by_arm[arm][ordinal] = row.get("diagnostic")
    stage1_records = summary.get("stage1_record_hashes") or {}
    stage1_equal = (
        all(value is not None for rows in stage1_by_arm.values() for value in rows)
        and canonical_json_bytes(stage1_by_arm["control_vanilla"])
        == canonical_json_bytes(stage1_by_arm["treatment_pcgrad"])
        and stage1_records == {
            "control_vanilla": REFERENCE_CONTROL["stage1_record_sha256"],
            "treatment_pcgrad": REFERENCE_CONTROL["stage1_record_sha256"],
        }
    )
    if not stage1_equal:
        failures.append("stage1_full_equality")
    milestone_by_key: dict[tuple[str, int], list[Any]] = {}
    for row in milestone_rows:
        key = (str(row.get("arm")), int(row.get("stage2_update_ordinal", -1)))
        ordinal = row.get("row_ordinal")
        values = milestone_by_key.setdefault(key, [None] * EXPECTED_ROWS)
        if not isinstance(ordinal, int) or not 0 <= ordinal < EXPECTED_ROWS or values[ordinal] is not None:
            failures.append("milestone_key")
            continue
        values[ordinal] = row.get("diagnostic")
    expected_milestones = [value for value in DIAGNOSTIC_UPDATES if value <= completed_updates]
    expected_keys = {
        (arm, update)
        for arm in ("control_vanilla", "treatment_pcgrad")
        for update in expected_milestones
    }
    if set(milestone_by_key) != expected_keys or any(
        any(value is None for value in rows) for rows in milestone_by_key.values()
    ):
        failures.append("milestone_completeness")
    step_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for row in step_rows:
        key = (
            str((row.get("step") or {}).get("arm")),
            int(row.get("stage_2_update_ordinal", -1)),
        )
        if key in step_by_key:
            failures.append("step_duplicate")
        step_by_key[key] = row
    expected_step_keys = {
        (arm, update)
        for arm in ("control_vanilla", "treatment_pcgrad")
        for update in range(1, completed_updates + 1)
    }
    if set(step_by_key) != expected_step_keys:
        failures.append("step_completeness")
    expected_series = {
        f"updates/{update:02d}/{arm}"
        for arm in ("control_vanilla", "treatment_pcgrad")
        for update in range(1, completed_updates + 1)
    }
    if (
        gradients.get("schema_version")
        != "mass-preserving-pcgrad-gradient-tensors-v1"
        or tuple(gradients.get("task_order") or ()) != TASK_ORDER
        or set(gradients.get("series") or {}) != expected_series
    ):
        failures.append("gradient_series_completeness")
    for key, item in (gradients.get("series") or {}).items():
        raw = item.get("raw_task_gradients") or {}
        if tuple(raw) != TASK_ORDER or any(
            not torch.is_tensor(raw[task]) or raw[task].dtype != torch.float64
            for task in raw
        ):
            failures.append(f"gradient_raw:{key}")
        if key.endswith("treatment_pcgrad"):
            projected = item.get("projected_task_gradients") or {}
            if tuple(projected) != TASK_ORDER or any(
                not torch.is_tensor(projected[task])
                or projected[task].dtype != torch.float64 for task in projected
            ):
                failures.append(f"gradient_projected:{key}")
        for tensor_name in (
            "combined_preclip_gradient", "actual_parameter_delta",
            "cumulative_parameter_delta",
        ):
            tensor = item.get(tensor_name)
            if not torch.is_tensor(tensor) or tensor.dtype != torch.float32:
                failures.append(f"gradient_dtype:{key}:{tensor_name}")
        if not isinstance(item.get("postclip_coefficient"), float):
            failures.append(f"gradient_clip:{key}")
    alignment = {
        "control_vanilla": {}, "treatment_pcgrad": {},
        "treatment_minus_control": {},
    }
    for update in (48, 64):
        if update <= completed_updates and all(
            (arm, update) in milestone_by_key
            for arm in ("control_vanilla", "treatment_pcgrad")
        ):
            for arm in ("control_vanilla", "treatment_pcgrad"):
                alignment[arm][str(update)] = _alignment_summary_for_metrics(
                    prepare_receipt, milestone_by_key[(arm, update)]
                )
            alignment["treatment_minus_control"][str(update)] = (
                _difference_alignment_summary(
                    prepare_receipt,
                    milestone_by_key[("control_vanilla", update)],
                    milestone_by_key[("treatment_pcgrad", update)],
                )
            )
    touched: set[str] = set()
    surgery_nonzero = False
    for update in range(1, min(16, completed_updates) + 1):
        step = (step_by_key.get(("treatment_pcgrad", update)) or {}).get("step") or {}
        diagnostics = step.get("gradient_diagnostics") or {}
        surgery_nonzero = surgery_nonzero or diagnostics.get("surgery_nonzero") is True
        touched.update(diagnostics.get("task_changed_by_surgery") or ())
    projections: dict[str, Any] = {}
    for update in (48, 64):
        item = (gradients.get("series") or {}).get(
            f"updates/{update:02d}/treatment_pcgrad"
        )
        if item:
            cumulative = item["cumulative_parameter_delta"].to(torch.float64)
            projections[str(update)] = {
                task: float(torch.dot(-item["raw_task_gradients"][task], cumulative))
                for task in PRIORITY_TASKS
            }
    terminal_end = None
    if ("treatment_pcgrad", 64) in milestone_by_key:
        terminal_end = terminal_end_controls(
            prepare_receipt, milestone_by_key[("treatment_pcgrad", 64)]
        )
    derived = {
        "completed_optimizer_steps_per_arm": completed_steps,
        "completed_synchronized_stage2_updates": completed_updates,
        "update_records": {
            arm: [step_by_key[(arm, update)] for update in range(1, completed_updates + 1)]
            for arm in ("control_vanilla", "treatment_pcgrad")
        },
        "full_830_row_diagnostics": {
            arm: {
                str(update): milestone_by_key[(arm, update)]
                for update in expected_milestones if (arm, update) in milestone_by_key
            }
            for arm in ("control_vanilla", "treatment_pcgrad")
        },
        "all_safety_gates_pass": (
            completed_updates == 64
            and all(
                (row.get("safety") or {}).get("safety_pass") is True
                and (row.get("safety") or {}).get("hard_stop") is not True
                for row in step_rows
            )
        ),
        "failure": manifest.get("failure"),
        "stage1_equality": {"passed": stage1_equal},
        "control_update32_reference": summary.get("control_update32_reference"),
        "mechanism": {
            "surgery_nonzero": surgery_nonzero,
            "tasks_touched_first_16": sorted(touched),
            "cumulative_delta_projections": projections,
        },
        "alignment_summaries": alignment,
        "terminal_END_controls": terminal_end,
        "duplicate_treatment_canonical_outputs_identical": (
            summary.get("duplicate_treatment_canonical_outputs_identical") is True
        ),
    }
    gates = _strict_gate_shape_from_run(derived)
    terminal_hashes = {
        arm: (
            base._ordered_output_hashes(milestone_by_key[(arm, 64)])
            if (arm, 64) in milestone_by_key else None
        )
        for arm in ("control_vanilla", "treatment_pcgrad")
    }
    checkpoint_gates = {}
    for arm, name in (
        ("control_vanilla", "control_pending.pt"),
        ("treatment_pcgrad", "treatment_pending.pt"),
    ):
        evidence, checkpoint_failures = _pending_checkpoint_gate(
            directory / name, arm=arm,
            expected_steps=int(completed_steps.get(arm, -1)),
            expected_spec_sha256=spec["_file_sha256"],
            expected_prepare_sha256=prepare_receipt["receipt_sha256"],
            terminal_output_hashes=terminal_hashes[arm],
        )
        checkpoint_gates[arm] = evidence
        failures.extend(f"{arm}:{value}" for value in checkpoint_failures)
    failures.extend(gates["failures"])
    return {
        "offline_pass": not failures,
        "bundle_integrity_pass": not any(
            value.startswith(("missing:", "size:", "sha256:", "pending_file_set"))
            for value in failures
        ),
        "failures": sorted(set(failures)),
        "recomputed": {
            "stage1_full_equality": stage1_equal,
            "stage1_rows": len(stage1_rows),
            "milestone_rows": len(milestone_rows),
            "step_rows": len(step_rows),
            "gradient_series": len(gradients.get("series") or {}),
            "alignment_summaries": alignment,
            "mechanism": derived["mechanism"],
            "terminal_END_controls": terminal_end,
            "checkpoint_gates": checkpoint_gates,
            "strict_shape_gates": gates,
        },
    }


def _authority_receipt(
    path: Path,
    expected_hash: str,
    *,
    schema_version: str,
    required_keys: set[str],
    label: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        value = _load_hashed_json(
            path, _strict_sha256(expected_hash, label=f"{label} file hash"),
            label=label,
        )
        if set(value) != required_keys or value.get("schema_version") != schema_version:
            raise ValueError(f"{label} schema or key set mismatch")
        core = dict(value)
        claim = _strict_sha256(
            core.pop("receipt_sha256", None), label=f"{label} self-hash"
        )
        if canonical_sha256(core) != claim:
            raise ValueError(f"{label} self-hash mismatch")
        return value, []
    except Exception as error:
        return None, [f"{label}:{type(error).__name__}:{error}"]


NUMERICAL_AUDIT_KEYS = {
    "schema_version", "pending_manifest_path", "pending_manifest_file_sha256",
    "pending_manifest_core_sha256", "pending_file_hashes", "recomputed_gates",
    "numeric_discrepancy_count", "audit_integrity_pass", "receipt_sha256",
}
ROOT_RECOMPUTATION_KEYS = {
    "schema_version", "pending_manifest_path", "pending_manifest_file_sha256",
    "pending_manifest_core_sha256", "numerical_audit_receipt_path",
    "numerical_audit_receipt_file_sha256", "numerical_audit_receipt_sha256",
    "root_recomputed_critical_gates", "numeric_discrepancy_count",
    "root_integrity_pass", "receipt_sha256",
}


def finalize(
    *,
    execution_spec: Path,
    execution_spec_sha256: str,
    pending_manifest: Path,
    pending_manifest_sha256: str,
    numerical_audit_receipt: Path,
    numerical_audit_receipt_sha256: str,
    root_recomputation_receipt: Path,
    root_recomputation_receipt_sha256: str,
) -> dict[str, Any]:
    """Load-only finalizer; no training callback is reachable from this path."""

    spec_hash = _strict_sha256(execution_spec_sha256, label="execution spec hash")
    spec, prepare_receipt, expected_pending, final_directory = _validate_execution_spec(
        execution_spec.absolute(), spec_hash, require_outputs_absent=False
    )
    spec = dict(spec)
    spec["_file_sha256"] = spec_hash
    if final_directory.exists():
        raise FileExistsError("terminal output destination already exists")
    expected_manifest = expected_pending / "manifest.json"
    if pending_manifest.absolute() != expected_manifest:
        raise ValueError("pending manifest path differs from execution spec")
    manifest_errors: list[str] = []
    try:
        manifest, loaded_manifest_errors = _load_pending_manifest(
            expected_manifest,
            _strict_sha256(pending_manifest_sha256, label="pending manifest hash"),
        )
        manifest_errors.extend(loaded_manifest_errors)
    except BaseException as error:
        manifest = {}
        manifest_errors.append(
            f"manifest_load:{type(error).__name__}:{str(error)[:1000]}"
        )
    try:
        strict = recompute_pending_gates(
            spec=spec,
            prepare_receipt=prepare_receipt,
            manifest_path=expected_manifest,
            manifest_sha256=pending_manifest_sha256,
        )
    except BaseException as error:
        strict = _stable_failed_recomputation_v2(error)
    numerical, numerical_errors = _authority_receipt(
        numerical_audit_receipt.absolute(), numerical_audit_receipt_sha256,
        schema_version=NUMERICAL_AUDIT_SCHEMA_VERSION,
        required_keys=NUMERICAL_AUDIT_KEYS,
        label="numerical audit receipt",
    )
    root, root_errors = _authority_receipt(
        root_recomputation_receipt.absolute(), root_recomputation_receipt_sha256,
        schema_version=ROOT_RECOMPUTATION_SCHEMA_VERSION,
        required_keys=ROOT_RECOMPUTATION_KEYS,
        label="root recomputation receipt",
    )
    authority_errors = [*numerical_errors, *root_errors]
    try:
        manifest_file_hash = sha256_file(expected_manifest)
    except BaseException as error:
        manifest_file_hash = None
        manifest_errors.append(
            f"manifest_hash:{type(error).__name__}:{str(error)[:1000]}"
        )
    manifest_core_hash = manifest.get("manifest_core_sha256")
    manifest_files = manifest.get("files")
    if isinstance(manifest_files, Mapping):
        pending_hashes = {
            str(name): evidence.get("sha256")
            for name, evidence in manifest_files.items()
            if isinstance(evidence, Mapping)
        }
    else:
        pending_hashes = {}
        manifest_errors.append("manifest_files_unavailable")
    if numerical is not None:
        expected_numerical = {
            "pending_manifest_path": str(expected_manifest.absolute()),
            "pending_manifest_file_sha256": manifest_file_hash,
            "pending_manifest_core_sha256": manifest_core_hash,
            "pending_file_hashes": pending_hashes,
            "recomputed_gates": strict,
        }
        for key, value in expected_numerical.items():
            if canonical_json_bytes(numerical.get(key)) != canonical_json_bytes(value):
                authority_errors.append(f"numerical_audit_binding:{key}")
    try:
        numerical_file_hash = (
            sha256_file(numerical_audit_receipt)
            if numerical_audit_receipt.is_file()
            else numerical_audit_receipt_sha256
        )
    except BaseException as error:
        numerical_file_hash = numerical_audit_receipt_sha256
        authority_errors.append(
            f"numerical_audit_hash:{type(error).__name__}:{str(error)[:1000]}"
        )
    if root is not None:
        expected_root = {
            "pending_manifest_path": str(expected_manifest.absolute()),
            "pending_manifest_file_sha256": manifest_file_hash,
            "pending_manifest_core_sha256": manifest_core_hash,
            "numerical_audit_receipt_path": str(numerical_audit_receipt.absolute()),
            "numerical_audit_receipt_file_sha256": numerical_file_hash,
            "numerical_audit_receipt_sha256": (
                None if numerical is None else numerical["receipt_sha256"]
            ),
            "root_recomputed_critical_gates": strict,
        }
        for key, value in expected_root.items():
            if canonical_json_bytes(root.get(key)) != canonical_json_bytes(value):
                authority_errors.append(f"root_recomputation_binding:{key}")
    authorities_pass = (
        not authority_errors
        and numerical is not None and root is not None
        and numerical.get("audit_integrity_pass") is True
        and numerical.get("numeric_discrepancy_count") == 0
        and root.get("root_integrity_pass") is True
        and root.get("numeric_discrepancy_count") == 0
    )
    accepted = (
        strict["offline_pass"] is True
        and strict["bundle_integrity_pass"] is True
        and not manifest_errors
        and authorities_pass
        and manifest.get("completed_optimizer_steps_per_arm")
        == {"control_vanilla": 65, "treatment_pcgrad": 65}
    )
    status = "accepted" if accepted else "rejected"
    checkpoint_sources = {
        "control.pt": expected_pending / "control_pending.pt",
        "treatment.pt": expected_pending / "treatment_pending.pt",
    }
    if any(not path.is_file() for path in checkpoint_sources.values()):
        raise ValueError("pending checkpoints are unavailable for finalization")
    checkpoint_payloads = {
        name: path.read_bytes() for name, path in checkpoint_sources.items()
    }
    receipt_core = {
        "schema_version": FINAL_RECEIPT_SCHEMA_VERSION,
        "status": status.upper(),
        "execution_spec_path": str(execution_spec.absolute()),
        "execution_spec_sha256": spec_hash,
        "pending_manifest_path": str(expected_manifest.absolute()),
        "pending_manifest_file_sha256": manifest_file_hash,
        "pending_manifest_core_sha256": manifest_core_hash,
        "numerical_audit_receipt_path": str(numerical_audit_receipt.absolute()),
        "numerical_audit_receipt_file_sha256": numerical_audit_receipt_sha256,
        "numerical_audit_receipt_sha256": (
            None if numerical is None else numerical["receipt_sha256"]
        ),
        "root_recomputation_receipt_path": str(root_recomputation_receipt.absolute()),
        "root_recomputation_receipt_file_sha256": root_recomputation_receipt_sha256,
        "root_recomputation_receipt_sha256": (
            None if root is None else root["receipt_sha256"]
        ),
        "strict_recomputed_gates": strict,
        "authority_errors": sorted(set(authority_errors)),
        "manifest_errors": manifest_errors,
        "checkpoint_sha256s": {
            name: _sha256_bytes(payload) for name, payload in checkpoint_payloads.items()
        },
        "checkpoint_states_copied_without_tensor_change": True,
        "training_rerun": False,
        "games_run": 0,
        "runtime_smoke_executed": False,
    }
    receipt = {
        **receipt_core, "receipt_sha256": canonical_sha256(receipt_core)
    }
    receipt_name = f"{status}_receipt.json"
    receipt_payload = canonical_json_bytes(receipt, newline=True)
    marker_name = status.upper()
    marker_payload = canonical_json_bytes({
        "status": marker_name,
        "receipt_file_sha256": _sha256_bytes(receipt_payload),
        "receipt_sha256": receipt["receipt_sha256"],
        "games_run": 0,
        "runtime_smoke_executed": False,
    }, newline=True)
    staging = Path(tempfile.mkdtemp(
        prefix=".pcgrad-final-", dir=str(final_directory.parent)
    ))
    try:
        for name, payload in checkpoint_payloads.items():
            _write_new_bytes(staging / name, payload)
        _write_new_bytes(staging / receipt_name, receipt_payload)
        _write_new_bytes(staging / marker_name, marker_payload)
        expected_files = (
            set(FINAL_ACCEPTED_FILES) if accepted else set(FINAL_REJECTED_FILES)
        )
        if {item.name for item in staging.iterdir()} != expected_files:
            raise ValueError("final staging artifact set mismatch")
        os.replace(staging, final_directory)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {
        "mode": "finalize", "status": marker_name,
        "output_directory": str(final_directory),
        "receipt_path": str(final_directory / receipt_name),
        "receipt_file_sha256": _sha256_bytes(receipt_payload),
        "receipt_sha256": receipt["receipt_sha256"],
        "games_run": 0,
    }


def execute(*, execution_spec: Path, execution_spec_sha256: str) -> dict[str, Any]:
    """Validate immutable bindings, train once, and publish PENDING_AUDIT."""

    spec_hash = _strict_sha256(execution_spec_sha256, label="execution spec hash")
    spec, receipt, pending, _final = _validate_execution_spec(
        execution_spec.absolute(), spec_hash, require_outputs_absent=True
    )
    runtime = inherited._runtime_identity()
    receipt_path = _repo_path(PurePosixPath(spec["prepare_receipt_path"]))
    _require_prepare_rebuild(receipt_path, receipt, runtime)
    spec = dict(spec)
    spec["_file_sha256"] = spec_hash
    run = run_matched_arms(receipt, duplicate_treatment=True)
    result = publish_pending_bundle(
        pending_directory=pending, run=run, prepare_receipt=receipt,
        spec=spec, execution_spec_path=execution_spec.absolute(),
        execution_spec_sha256=spec_hash,
    )
    return {
        "mode": "execute", **result,
        "optimizer_steps_executed": sum(
            run["completed_optimizer_steps_per_arm"].values()
        ),
        "runtime_smoke_executed": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--output-receipt", type=Path, required=True)
    execute_parser = commands.add_parser("execute")
    execute_parser.add_argument("--execution-spec", type=Path, required=True)
    execute_parser.add_argument("--execution-spec-sha256", required=True)
    final_parser = commands.add_parser("finalize")
    final_parser.add_argument("--execution-spec", type=Path, required=True)
    final_parser.add_argument("--execution-spec-sha256", required=True)
    final_parser.add_argument("--pending-manifest", type=Path, required=True)
    final_parser.add_argument("--pending-manifest-sha256", required=True)
    final_parser.add_argument("--numerical-audit-receipt", type=Path, required=True)
    final_parser.add_argument("--numerical-audit-receipt-sha256", required=True)
    final_parser.add_argument("--root-recomputation-receipt", type=Path, required=True)
    final_parser.add_argument("--root-recomputation-receipt-sha256", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "prepare":
        result = prepare(output_receipt=args.output_receipt)
    elif args.mode == "execute":
        result = execute(
            execution_spec=args.execution_spec,
            execution_spec_sha256=args.execution_spec_sha256,
        )
    else:
        result = finalize(
            execution_spec=args.execution_spec,
            execution_spec_sha256=args.execution_spec_sha256,
            pending_manifest=args.pending_manifest,
            pending_manifest_sha256=args.pending_manifest_sha256,
            numerical_audit_receipt=args.numerical_audit_receipt,
            numerical_audit_receipt_sha256=args.numerical_audit_receipt_sha256,
            root_recomputation_receipt=args.root_recomputation_receipt,
            root_recomputation_receipt_sha256=args.root_recomputation_receipt_sha256,
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


def _corrected_prepare_receipt(runtime: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild the complete, execution-specification-independent receipt."""

    plan = _load_plan()
    correction = _load_correction()
    correction_v2 = _load_correction_v2()
    correction_v3 = _load_correction_v3()
    correction_v4 = _load_correction_v4()
    correction_v5 = _load_correction_v5()
    provenance = _validate_provenance(plan)
    implementation = inherited.implementation_snapshot(
        _repo_path(IMPLEMENTATION_RELATIVE_PATH)
    )
    implementation_files = {
        row["path"]: row["sha256"] for row in implementation["files"]
    }
    module_path = "archaludon_rl/mass_preserving_pcgrad_pilot.py"
    test_path = "tests/test_mass_preserving_pcgrad_pilot.py"
    if module_path not in implementation_files or test_path not in implementation_files:
        raise ValueError("implementation snapshot omits the v5 implementation files")
    reference = _validate_reference_receipt()
    inherited_prepare = base._build_prepare_receipt(runtime)
    loaded = inherited._load_validated_inputs()
    rejected = _repo_path(REJECTED_CHECKPOINT_RELATIVE_PATH).resolve(strict=True)
    if loaded["checkpoint_path"].resolve(strict=True) == rejected:
        raise ValueError("rejected checkpoint was loaded")
    rows = copy.deepcopy(inherited_prepare["rows"])
    if len(rows) != EXPECTED_ROWS or len(loaded["rows"]) != EXPECTED_ROWS:
        raise ValueError("prepare did not reproduce exactly 830 rows")
    partition = build_task_partition(rows)
    monte_carlo = _monte_carlo_advantages(loaded, rows)
    sign_stable = _sign_stable_ordinals(rows, monte_carlo)
    before = _model_parameter_hashes(loaded["model"])
    after = _model_parameter_hashes(loaded["model"])
    if before != after:
        raise ValueError("prepare changed model parameters")
    core = {
        "schema_version": PREPARE_RECEIPT_SCHEMA_VERSION,
        "plan": {
            "path": PLAN_RELATIVE_PATH.as_posix(),
            "file_sha256": PLAN_SHA256,
            "canonical_sha256": canonical_sha256(plan),
            "contract": copy.deepcopy(plan),
        },
        "correction": {
            "path": CORRECTION_RELATIVE_PATH.as_posix(),
            "file_sha256": CORRECTION_SHA256,
            "canonical_sha256": canonical_sha256(correction),
            "correction_id": CORRECTION_ID,
            "contract": copy.deepcopy(correction),
        },
        "correction_v2": {
            "path": CORRECTION_V2_RELATIVE_PATH.as_posix(),
            "file_sha256": CORRECTION_V2_SHA256,
            "canonical_sha256": canonical_sha256(correction_v2),
            "correction_id": CORRECTION_V2_ID,
            "contract": copy.deepcopy(correction_v2),
        },
        "correction_v3": {
            "path": CORRECTION_V3_RELATIVE_PATH.as_posix(),
            "file_sha256": CORRECTION_V3_SHA256,
            "canonical_sha256": canonical_sha256(correction_v3),
            "correction_id": CORRECTION_V3_ID,
            "contract": copy.deepcopy(correction_v3),
        },
        "correction_v4": {
            "path": CORRECTION_V4_RELATIVE_PATH.as_posix(),
            "file_sha256": CORRECTION_V4_SHA256,
            "canonical_sha256": canonical_sha256(correction_v4),
            "correction_id": CORRECTION_V4_ID,
            "contract": copy.deepcopy(correction_v4),
        },
        "correction_v5": {
            "path": CORRECTION_V5_RELATIVE_PATH.as_posix(),
            "file_sha256": CORRECTION_V5_SHA256,
            "canonical_sha256": canonical_sha256(correction_v5),
            "correction_id": CORRECTION_V5_ID,
            "contract": copy.deepcopy(correction_v5),
        },
        "predecessor_execution_stop": {
            "execution_spec_path": (
                PREDECESSOR_EXECUTION_SPEC_RELATIVE_PATH.as_posix()
            ),
            "execution_spec_sha256": PREDECESSOR_EXECUTION_SPEC_SHA256,
            "manifest_path": PREDECESSOR_STOP_MANIFEST_RELATIVE_PATH.as_posix(),
            "manifest_file_sha256": PREDECESSOR_STOP_MANIFEST_FILE_SHA256,
            "manifest_core_sha256": PREDECESSOR_STOP_MANIFEST_CORE_SHA256,
            "completed_optimizer_steps_per_arm": {
                "control_vanilla": 1, "treatment_pcgrad": 1,
            },
            "completed_stage2_updates": 0,
            "games_run": 0,
            "immutable_implementation_stop": True,
            "resume_permitted": False,
        },
        "provenance": provenance,
        "implementation": {
            "path": IMPLEMENTATION_RELATIVE_PATH.as_posix(),
            "module_sha256": implementation_files[module_path],
            "focused_test_sha256": implementation_files[test_path],
            **implementation,
        },
        "runtime_thread_receipt": dict(runtime),
        "immutable_inputs": {
            "input_checkpoint_path": INPUT_CHECKPOINT_RELATIVE_PATH.as_posix(),
            "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
            "manifest_path": MANIFEST_RELATIVE_PATH.as_posix(),
            "manifest_sha256": MANIFEST_SHA256,
            "dataset_sha256": DATASET_SHA256,
            "row_count": EXPECTED_ROWS,
            "trajectory_count": EXPECTED_TRAJECTORIES,
            "fixed_advantages_sha256": FIXED_ADVANTAGES_SHA256,
            "fixed_behavior_logprobabilities_sha256": (
                FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256
            ),
            "rejected_checkpoint_path": REJECTED_CHECKPOINT_RELATIVE_PATH.as_posix(),
            "rejected_checkpoint_sha256": REJECTED_CHECKPOINT_SHA256,
            "rejected_checkpoint_loaded": False,
        },
        "control_reference": reference,
        "rows": rows,
        "ordered_training_rows_sha256": canonical_sha256(rows),
        "action_families": copy.deepcopy(inherited_prepare["action_families"]),
        "directional_memberships": copy.deepcopy(
            inherited_prepare["directional_memberships"]
        ),
        "task_partition": task_membership_receipt(partition),
        "monte_carlo_advantages_float64": monte_carlo,
        "monte_carlo_advantages_sha256": canonical_sha256(monte_carlo),
        "sign_stable_611_ordinals": sign_stable,
        "sign_stable_611_sha256": canonical_sha256(sign_stable),
        "initial_value_identity": copy.deepcopy(
            inherited_prepare["initial_value_identity"]
        ),
        "model_parameters": copy.deepcopy(inherited_prepare["model_parameters"]),
        "training_contract": copy.deepcopy(plan["training_contract"]),
        "diagnostic_contract": copy.deepcopy(plan["diagnostic_contract"]),
        "safety_gates": copy.deepcopy(plan["safety_gates"]),
        "terminal_offline_acceptance": copy.deepcopy(
            plan["terminal_offline_acceptance"]
        ),
        "prepare_proof": {
            "optimizer_constructed": False,
            "optimizer_steps": 0,
            "parameters_changed": False,
            "checkpoint_written": False,
            "rejected_checkpoint_loaded": False,
            "training_executed": False,
            "runtime_smoke_executed": False,
            "games_run": 0,
            "execution_spec_read": False,
        },
    }
    return {**core, "receipt_sha256": canonical_sha256(core)}


def _build_prepare_receipt(*, runtime: Mapping[str, Any]) -> dict[str, Any]:
    return _corrected_prepare_receipt(runtime)


def validate_prepare_receipt(receipt: Mapping[str, Any]) -> None:
    required = {
        "schema_version", "plan", "correction", "correction_v2",
        "correction_v3", "correction_v4", "correction_v5",
        "predecessor_execution_stop", "provenance",
        "implementation",
        "runtime_thread_receipt", "immutable_inputs", "control_reference", "rows",
        "ordered_training_rows_sha256", "action_families", "directional_memberships",
        "task_partition", "monte_carlo_advantages_float64",
        "monte_carlo_advantages_sha256", "sign_stable_611_ordinals",
        "sign_stable_611_sha256", "initial_value_identity", "model_parameters",
        "training_contract", "diagnostic_contract", "safety_gates",
        "terminal_offline_acceptance", "prepare_proof", "receipt_sha256",
    }
    if set(receipt) != required:
        raise ValueError("prepare receipt key set mismatch")
    if receipt.get("schema_version") != PREPARE_RECEIPT_SCHEMA_VERSION:
        raise ValueError("prepare receipt schema mismatch")
    core = dict(receipt)
    claimed = _strict_sha256(
        core.pop("receipt_sha256", None), label="prepare receipt self-hash"
    )
    if canonical_sha256(core) != claimed:
        raise ValueError("prepare receipt self-hash mismatch")
    if receipt["plan"].get("file_sha256") != PLAN_SHA256:
        raise ValueError("prepare plan binding mismatch")
    if receipt["correction"].get("file_sha256") != CORRECTION_SHA256:
        raise ValueError("prepare correction binding mismatch")
    if receipt["correction_v2"].get("file_sha256") != CORRECTION_V2_SHA256:
        raise ValueError("prepare v2 correction binding mismatch")
    if receipt["correction_v3"].get("file_sha256") != CORRECTION_V3_SHA256:
        raise ValueError("prepare v3 correction binding mismatch")
    if receipt["correction_v4"].get("file_sha256") != CORRECTION_V4_SHA256:
        raise ValueError("prepare v4 correction binding mismatch")
    if receipt["correction_v5"].get("file_sha256") != CORRECTION_V5_SHA256:
        raise ValueError("prepare v5 correction binding mismatch")
    if receipt["predecessor_execution_stop"] != {
        "execution_spec_path": PREDECESSOR_EXECUTION_SPEC_RELATIVE_PATH.as_posix(),
        "execution_spec_sha256": PREDECESSOR_EXECUTION_SPEC_SHA256,
        "manifest_path": PREDECESSOR_STOP_MANIFEST_RELATIVE_PATH.as_posix(),
        "manifest_file_sha256": PREDECESSOR_STOP_MANIFEST_FILE_SHA256,
        "manifest_core_sha256": PREDECESSOR_STOP_MANIFEST_CORE_SHA256,
        "completed_optimizer_steps_per_arm": {
            "control_vanilla": 1, "treatment_pcgrad": 1,
        },
        "completed_stage2_updates": 0,
        "games_run": 0,
        "immutable_implementation_stop": True,
        "resume_permitted": False,
    }:
        raise ValueError("prepare predecessor implementation-stop binding mismatch")
    implementation_files = {
        row["path"]: row["sha256"]
        for row in receipt["implementation"].get("files") or ()
    }
    if receipt["implementation"].get("module_sha256") != implementation_files.get(
        "archaludon_rl/mass_preserving_pcgrad_pilot.py"
    ):
        raise ValueError("prepare implementation module binding mismatch")
    if receipt["implementation"].get("focused_test_sha256") != implementation_files.get(
        "tests/test_mass_preserving_pcgrad_pilot.py"
    ):
        raise ValueError("prepare focused test binding mismatch")
    proof = receipt["prepare_proof"]
    if proof != {
        "optimizer_constructed": False, "optimizer_steps": 0,
        "parameters_changed": False, "checkpoint_written": False,
        "rejected_checkpoint_loaded": False, "training_executed": False,
        "runtime_smoke_executed": False, "games_run": 0,
        "execution_spec_read": False,
    }:
        raise ValueError("prepare proof mismatch")
    if len(receipt["rows"]) != EXPECTED_ROWS:
        raise ValueError("prepare row count mismatch")
    if len(receipt["monte_carlo_advantages_float64"]) != EXPECTED_ROWS:
        raise ValueError("prepare Monte-Carlo row count mismatch")
    if len(receipt["sign_stable_611_ordinals"]) != 611:
        raise ValueError("prepare sign-stable count mismatch")
    partition = {
        row["task"]: row["ordinals"] for row in receipt["task_partition"]["tasks"]
    }
    validate_task_partition(partition)
    if partition != build_task_partition(receipt["rows"]):
        raise ValueError("prepare task memberships are not derived from rows")


def _validate_prepare_output_path(path: Path) -> Path:
    candidate_root = _repo_path(IMPLEMENTATION_RELATIVE_PATH).resolve(strict=True)
    output = path.absolute()
    allowed = candidate_root / "test_outputs"
    if (
        output.name != PREPARE_OUTPUT_FILENAME
        or output.parent.parent != allowed
        or output.exists()
        or output.parent.exists()
    ):
        raise ValueError(
            "prepare output must be a new candidate test_outputs child receipt"
        )
    if allowed.exists() and allowed.resolve(strict=True) != allowed:
        raise ValueError("prepare output root identity mismatch")
    return output


def prepare(*, output_receipt: Path) -> dict[str, Any]:
    output = _validate_prepare_output_path(output_receipt)
    runtime = inherited._runtime_identity()
    receipt = _corrected_prepare_receipt(runtime)
    validate_prepare_receipt(receipt)
    output.parent.parent.mkdir(exist_ok=True)
    file_hash = _atomic_publish_receipt(output, receipt)
    return {
        "mode": "prepare",
        "receipt_path": str(output),
        "receipt_file_sha256": file_hash,
        "receipt_sha256": receipt["receipt_sha256"],
        "implementation_snapshot_definition": receipt["implementation"]["definition"],
        "implementation_snapshot_file_count": receipt["implementation"]["file_count"],
        "implementation_snapshot_sha256": receipt["implementation"]["sha256"],
        "optimizer_steps": 0,
        "games_run": 0,
    }


PENDING_BUNDLE_SCHEMA = {
    "schema_version": PENDING_MANIFEST_SCHEMA_VERSION,
    "exact_files": list(PENDING_FILES),
    "checkpoint_required_keys": [
        "model_config", "model_state", "metadata", "optimizer_state"
    ],
    "gradient_schema_version": "mass-preserving-pcgrad-gradient-tensors-v2",
    "public_step_schema_version": (
        "mass-preserving-pcgrad-public-step-reference-v2"
    ),
    "public_step_compact_fields_removed": True,
    "weights_only_loadable_gradient_evidence": True,
    "caller_summaries_informational_only": True,
    "status_marker": "PENDING_AUDIT",
}
FINAL_ARTIFACT_SCHEMA = {
    "schema_version": FINAL_RECEIPT_SCHEMA_VERSION,
    "accepted_exact_files": list(FINAL_ACCEPTED_FILES),
    "rejected_exact_files": list(FINAL_REJECTED_FILES),
}

EXECUTION_SPEC_KEYS = {
    "schema_version", "implementation_plan_path", "implementation_plan_sha256",
    "correction_path", "correction_sha256", "correction_v2_path",
    "correction_v2_sha256", "correction_v3_path", "correction_v3_sha256",
    "correction_v4_path", "correction_v4_sha256",
    "correction_v5_path", "correction_v5_sha256",
    "predecessor_execution_stop",
    "implementation_path",
    "implementation_snapshot_definition", "implementation_snapshot_file_count",
    "implementation_snapshot_sha256", "source_implementation_path",
    "source_implementation_snapshot_file_count",
    "source_implementation_snapshot_sha256", "input_checkpoint_path",
    "input_checkpoint_sha256", "manifest_path", "manifest_sha256",
    "dataset_sha256", "fixed_advantages_sha256",
    "fixed_behavior_logprobabilities_sha256", "prepare_receipt_path",
    "prepare_receipt_file_sha256", "prepare_receipt_sha256",
    "runtime_thread_receipt", "training_contract", "diagnostic_contract",
    "safety_gates", "terminal_offline_acceptance", "control_reference",
    "pending_audit_directory", "terminal_output_directory",
    "pending_bundle_schema", "final_artifact_schema",
}


def _canonical_prepare_receipt_spec_path(
    value: Any, *, must_exist: bool = True
) -> Path:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("prepare receipt spec path must be canonical repo-relative POSIX")
    pure = PurePosixPath(value)
    expected_prefix = (*IMPLEMENTATION_RELATIVE_PATH.parts, "test_outputs")
    if (
        pure.is_absolute()
        or pure.as_posix() != value
        or any(part in ("", ".", "..") for part in pure.parts)
        or tuple(pure.parts[: len(expected_prefix)]) != expected_prefix
        or len(pure.parts) != len(expected_prefix) + 2
        or pure.parts[-1] != PREPARE_OUTPUT_FILENAME
        or pure.parts[-2].startswith(".")
    ):
        raise ValueError("prepare receipt spec path is outside the exact candidate shape")
    candidate_root = _repo_path(IMPLEMENTATION_RELATIVE_PATH).resolve(strict=True)
    allowed = candidate_root / "test_outputs"
    target = _repo_path(pure).absolute()
    if target.parent.parent != allowed:
        raise ValueError("prepare receipt spec path depth mismatch")
    cursor = candidate_root
    for part in pure.parts[len(IMPLEMENTATION_RELATIVE_PATH.parts):]:
        cursor = cursor / part
        if cursor.exists() and inherited._is_link_or_reparse(cursor):
            raise ValueError("prepare receipt spec path traverses a link")
    if must_exist:
        if not target.is_file() or inherited._is_link_or_reparse(target):
            raise ValueError("prepare receipt spec path is not a regular file")
        if target.resolve(strict=True) != target:
            raise ValueError("prepare receipt spec path aliases its target")
    return target


def build_execution_spec_template(
    *,
    prepare_receipt_path: str,
    prepare_receipt_file_sha256: str,
    prepare_receipt_sha256: str,
    pending_audit_directory: str,
    terminal_output_directory: str,
) -> dict[str, Any]:
    receipt_path = _canonical_prepare_receipt_spec_path(
        prepare_receipt_path, must_exist=True
    )
    receipt = _load_hashed_json(
        receipt_path,
        _strict_sha256(prepare_receipt_file_sha256, label="prepare receipt file hash"),
        label="prepare receipt",
    )
    validate_prepare_receipt(receipt)
    if receipt["receipt_sha256"] != _strict_sha256(
        prepare_receipt_sha256, label="prepare receipt self-hash"
    ):
        raise ValueError("prepare receipt self-hash binding mismatch")
    plan = _load_plan()
    implementation = receipt["implementation"]
    return {
        "schema_version": EXECUTION_SPEC_SCHEMA_VERSION,
        "implementation_plan_path": PLAN_RELATIVE_PATH.as_posix(),
        "implementation_plan_sha256": PLAN_SHA256,
        "correction_path": CORRECTION_RELATIVE_PATH.as_posix(),
        "correction_sha256": CORRECTION_SHA256,
        "correction_v2_path": CORRECTION_V2_RELATIVE_PATH.as_posix(),
        "correction_v2_sha256": CORRECTION_V2_SHA256,
        "correction_v3_path": CORRECTION_V3_RELATIVE_PATH.as_posix(),
        "correction_v3_sha256": CORRECTION_V3_SHA256,
        "correction_v4_path": CORRECTION_V4_RELATIVE_PATH.as_posix(),
        "correction_v4_sha256": CORRECTION_V4_SHA256,
        "correction_v5_path": CORRECTION_V5_RELATIVE_PATH.as_posix(),
        "correction_v5_sha256": CORRECTION_V5_SHA256,
        "predecessor_execution_stop": copy.deepcopy(
            receipt["predecessor_execution_stop"]
        ),
        "implementation_path": IMPLEMENTATION_RELATIVE_PATH.as_posix(),
        "implementation_snapshot_definition": implementation["definition"],
        "implementation_snapshot_file_count": implementation["file_count"],
        "implementation_snapshot_sha256": implementation["sha256"],
        "source_implementation_path": SOURCE_IMPLEMENTATION_RELATIVE_PATH.as_posix(),
        "source_implementation_snapshot_file_count": SOURCE_IMPLEMENTATION_FILE_COUNT,
        "source_implementation_snapshot_sha256": SOURCE_IMPLEMENTATION_SHA256,
        "input_checkpoint_path": INPUT_CHECKPOINT_RELATIVE_PATH.as_posix(),
        "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
        "manifest_path": MANIFEST_RELATIVE_PATH.as_posix(),
        "manifest_sha256": MANIFEST_SHA256,
        "dataset_sha256": DATASET_SHA256,
        "fixed_advantages_sha256": FIXED_ADVANTAGES_SHA256,
        "fixed_behavior_logprobabilities_sha256": FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256,
        "prepare_receipt_path": prepare_receipt_path,
        "prepare_receipt_file_sha256": prepare_receipt_file_sha256,
        "prepare_receipt_sha256": prepare_receipt_sha256,
        "runtime_thread_receipt": copy.deepcopy(receipt["runtime_thread_receipt"]),
        "training_contract": copy.deepcopy(plan["training_contract"]),
        "diagnostic_contract": copy.deepcopy(plan["diagnostic_contract"]),
        "safety_gates": copy.deepcopy(plan["safety_gates"]),
        "terminal_offline_acceptance": copy.deepcopy(
            plan["terminal_offline_acceptance"]
        ),
        "control_reference": copy.deepcopy(REFERENCE_CONTROL),
        "pending_audit_directory": pending_audit_directory,
        "terminal_output_directory": terminal_output_directory,
        "pending_bundle_schema": copy.deepcopy(PENDING_BUNDLE_SCHEMA),
        "final_artifact_schema": copy.deepcopy(FINAL_ARTIFACT_SCHEMA),
    }


def _confined_output_path(value: Any, *, label: str, require_absent: bool) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"{label} must be a canonical repository-relative POSIX path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or pure.as_posix() != value or any(
        part in ("", ".", "..") for part in pure.parts
    ):
        raise ValueError(f"{label} is not canonical and confined")
    candidate_root = _repo_path(IMPLEMENTATION_RELATIVE_PATH).resolve(strict=True)
    allowed = candidate_root / "test_outputs"
    path = _repo_path(pure).absolute()
    if path.parent != allowed:
        raise ValueError(f"{label} must be a direct candidate test_outputs child")
    if require_absent and path.exists():
        raise FileExistsError(f"{label} already exists")
    if allowed.resolve(strict=True) != allowed:
        raise ValueError(f"{label} output root identity mismatch")
    return path


def _validate_execution_spec(
    path: Path,
    expected_hash: str,
    *,
    require_outputs_absent: bool = True,
) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    spec = _load_hashed_json(
        path,
        _strict_sha256(expected_hash, label="execution spec hash"),
        label="iteration-009 execution spec",
    )
    if set(spec) != EXECUTION_SPEC_KEYS or spec.get("schema_version") != EXECUTION_SPEC_SCHEMA_VERSION:
        raise ValueError("execution spec schema or key set mismatch")
    receipt_path = _canonical_prepare_receipt_spec_path(
        spec["prepare_receipt_path"], must_exist=True
    )
    receipt = _load_hashed_json(
        receipt_path,
        _strict_sha256(spec["prepare_receipt_file_sha256"], label="prepare file hash"),
        label="pinned prepare receipt",
    )
    validate_prepare_receipt(receipt)
    if receipt["receipt_sha256"] != spec["prepare_receipt_sha256"]:
        raise ValueError("execution spec prepare self-hash mismatch")
    expected = build_execution_spec_template(
        prepare_receipt_path=spec["prepare_receipt_path"],
        prepare_receipt_file_sha256=spec["prepare_receipt_file_sha256"],
        prepare_receipt_sha256=spec["prepare_receipt_sha256"],
        pending_audit_directory=spec["pending_audit_directory"],
        terminal_output_directory=spec["terminal_output_directory"],
    )
    if canonical_json_bytes(spec) != canonical_json_bytes(expected):
        raise ValueError("execution spec contract mismatch")
    pending = _confined_output_path(
        spec["pending_audit_directory"], label="pending audit directory",
        require_absent=require_outputs_absent,
    )
    final = _confined_output_path(
        spec["terminal_output_directory"], label="terminal output directory",
        require_absent=require_outputs_absent,
    )
    if pending == final:
        raise ValueError("pending and final output directories must be distinct")
    return spec, receipt, pending, final


def _require_prepare_rebuild(
    receipt_path: Path, receipt: Mapping[str, Any], runtime: Mapping[str, Any]
) -> None:
    validate_prepare_receipt(receipt)
    if dict(runtime) != dict(receipt["runtime_thread_receipt"]):
        raise ValueError("execution runtime differs from prepare")
    rebuilt = _corrected_prepare_receipt(runtime)
    validate_prepare_receipt(rebuilt)
    canonical = canonical_json_bytes(rebuilt, newline=True)
    if receipt_path.read_bytes() != canonical:
        raise ValueError("stored prepare receipt is not canonical or current")
    if canonical_json_bytes(receipt) != canonical_json_bytes(rebuilt):
        raise ValueError("stored prepare receipt differs from complete rebuild")


def _snapshot_synchronized_arm(state: Mapping[str, Any]) -> dict[str, Any]:
    progress = state["progress"]
    return {
        "model_state": copy.deepcopy(state["model"].state_dict()),
        "optimizer_state": copy.deepcopy(state["optimizer"].state_dict()),
        "progress": {
            name: copy.deepcopy(getattr(progress, name))
            for name in (
                "optimizer_steps_completed", "stage_2_updates_completed",
                "stage_2_entered", "failure_phase",
            )
        },
    }


def _restore_synchronized_arm(
    state: Mapping[str, Any], snapshot: Mapping[str, Any]
) -> None:
    state["model"].load_state_dict(copy.deepcopy(snapshot["model_state"]), strict=True)
    state["optimizer"].load_state_dict(copy.deepcopy(snapshot["optimizer_state"]))
    progress = state["progress"]
    for name, value in snapshot["progress"].items():
        setattr(progress, name, copy.deepcopy(value))
    progress.model = state["model"]
    progress.optimizer = state["optimizer"]


def _snapshot_synchronized_pair(arms: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    if set(arms) != {"control_vanilla", "treatment_pcgrad"}:
        raise ValueError("transaction requires exactly the two matched arms")
    return {name: _snapshot_synchronized_arm(arms[name]) for name in arms}


def _restore_synchronized_pair(
    arms: Mapping[str, Mapping[str, Any]], snapshots: Mapping[str, Any]
) -> None:
    for name in ("control_vanilla", "treatment_pcgrad"):
        _restore_synchronized_arm(arms[name], snapshots[name])


def run_lightweight_transaction_schedule(
    arms: Mapping[str, Mapping[str, Any]],
    *,
    stage1_step: Any,
    stage2_step: Any,
    diagnose: Any,
    safety: Any,
    duplicate: Any,
    updates: int = STAGE2_UPDATES,
) -> dict[str, Any]:
    """Deterministic transaction harness used by focused integration tests.

    Callbacks mutate only their named arm.  A callback exception before both
    diagnostics complete restores both model and optimizer states.
    """

    snapshots = _snapshot_synchronized_pair(arms)
    records: list[dict[str, Any]] = []
    failure = None
    try:
        for name in ("control_vanilla", "treatment_pcgrad"):
            stage1_step(name, arms[name])
        stage1_diagnostics = {
            name: diagnose("stage1", 0, name, arms[name])
            for name in ("control_vanilla", "treatment_pcgrad")
        }
    except Exception as error:
        _restore_synchronized_pair(arms, snapshots)
        return {
            "completed_steps_per_arm": {name: 0 for name in arms},
            "failure": {
                "phase": "stage1", "exception_type": type(error).__name__,
                "message": str(error),
            },
            "records": [], "milestones": [], "duplicate": None,
        }
    stage1_safety = {
        name: safety("stage1", 0, name, stage1_diagnostics[name])
        for name in ("control_vanilla", "treatment_pcgrad")
    }
    if any(value is not True for value in stage1_safety.values()):
        return {
            "completed_steps_per_arm": {name: 1 for name in arms},
            "failure": {"phase": "stage1_safety", "exception_type": None, "message": None},
            "records": [], "milestones": [], "duplicate": None,
        }
    milestones: list[int] = []
    for update in range(1, updates + 1):
        snapshots = _snapshot_synchronized_pair(arms)
        try:
            arm_records = {}
            for name in ("control_vanilla", "treatment_pcgrad"):
                arm_records[name] = stage2_step(update, name, arms[name])
            diagnostics = {
                name: diagnose("stage2", update, name, arms[name])
                for name in ("control_vanilla", "treatment_pcgrad")
            }
            safety_values = {
                name: safety("stage2", update, name, diagnostics[name])
                for name in ("control_vanilla", "treatment_pcgrad")
            }
        except Exception as error:
            _restore_synchronized_pair(arms, snapshots)
            failure = {
                "phase": f"stage2_update_{update}",
                "exception_type": type(error).__name__, "message": str(error),
            }
            break
        records.append({
            "update": update, "arms": arm_records,
            "diagnostics": diagnostics, "safety": safety_values,
        })
        if update in DIAGNOSTIC_UPDATES:
            milestones.append(update)
        if any(value is not True for value in safety_values.values()):
            failure = {
                "phase": f"stage2_update_{update}_safety",
                "exception_type": None, "message": None,
            }
            break
    completed = 1 + len(records)
    duplicate_result = duplicate(arms["treatment_pcgrad"]) if completed == 65 else None
    return {
        "completed_steps_per_arm": {name: completed for name in arms},
        "failure": failure,
        "records": records,
        "milestones": milestones,
        "duplicate": duplicate_result,
    }


def _new_stage1_state(loaded: Mapping[str, Any]) -> dict[str, Any]:
    model = loaded["model"]
    initial = {name: value.detach().clone() for name, value in model.state_dict().items()}
    base._set_trainability(model, stage=1)
    optimizer = base._new_actor_adam(model)
    progress = base.ExecutionProgress(model=model, optimizer=optimizer)
    return {
        "model": model,
        "optimizer": optimizer,
        "progress": progress,
        "initial_parameters": initial,
        "stage2_start_parameters": None,
        "stage2_start_optimizer_state": None,
        "source_hashes": copy.deepcopy(loaded["source_hashes"]),
        "input_metadata": copy.deepcopy(loaded["metadata"]),
        "reference_config": loaded["reference_config"],
        "rows": loaded["rows"],
    }


def _transactional_stage1_step(
    state: dict[str, Any], loaded: Mapping[str, Any], receipt: Mapping[str, Any]
) -> None:
    report = base._stage_full_batch_step(
        stage=1,
        loaded=loaded,
        prepare_receipt=receipt,
        optimizer=state["optimizer"],
        initial_parameters=state["initial_parameters"],
        progress=state["progress"],
    )
    metrics = base._measure_stage(loaded, receipt, stage=1)
    value = base.value_change_summary(receipt, metrics)
    safety = base.evaluate_stage_gates(
        receipt,
        metrics,
        stage=1,
        training_nonfinite_count=report[
            "nonfinite_value_gradient_optimizer_or_parameter_count"
        ],
        parameter_optimizer_contract_pass=True,
        value_contract_pass=(
            value["all_rows_byte_exact_to_initial"]
            and value["raw_value_mse_exact_to_initial"]
            and value["aggregate_hash_exact_to_initial"]
        ),
    )
    output_hashes = base._ordered_output_hashes(metrics)
    record_hash = canonical_sha256({
        "stage_1_report": report, "stage_1_safety": safety,
        "stage_1_value_identity": value, **output_hashes,
    })
    state.update({
        "stage1_report": report,
        "stage1_metrics": metrics,
        "stage1_safety": safety,
        "stage1_value_identity": value,
        "stage1_record_sha256": record_hash,
        "stage2_start_parameters": {
            name: value.detach().clone()
            for name, value in state["model"].state_dict().items()
        },
        "stage2_start_optimizer_state": copy.deepcopy(
            state["optimizer"].state_dict()
        ),
        "stage1_equality_evidence": {
            "stage1_record_sha256": record_hash,
            "stage1_report": copy.deepcopy(report),
            "stage1_safety": copy.deepcopy(safety),
            "stage1_value_identity": copy.deepcopy(value),
            "model_parameter_hashes": _model_parameter_hashes(state["model"]),
            "model_state_hashes": {
                name: _tensor_sha256_v2(tensor)
                for name, tensor in state["model"].state_dict().items()
            },
            "model_state": {
                name: tensor.detach().cpu().clone()
                for name, tensor in state["model"].state_dict().items()
            },
            "optimizer_canonical": optimizer_canonical_record(
                state["optimizer"], state["model"]
            ),
            "optimizer_state": copy.deepcopy(state["optimizer"].state_dict()),
            "output_hashes": output_hashes,
            "complete_830_diagnostics": copy.deepcopy(metrics),
            "losses": {
                "loss": report["loss"], "policy_loss": report["policy_loss"],
                "anchor_kl": report["pre_step_mean_anchor_kl"],
                "entropy": report["entropy"],
            },
            "fixed_input_identities": {
                "fixed_advantages_sha256": report["fixed_advantages_sha256"],
                "fixed_behavior_logprobabilities_sha256": report[
                    "fixed_behavior_logprobabilities_sha256"
                ],
                "row_count": len(metrics),
            },
        },
    })


def _empty_run(
    arms: Mapping[str, Any], loaded_arms: Mapping[str, Any], *, failure: Any
) -> dict[str, Any]:
    return {
        "arms": arms, "loaded_arms": loaded_arms,
        "stage1_equality": None,
        "update_records": {name: [] for name in arms},
        "full_830_row_diagnostics": {name: {} for name in arms},
        "completed_optimizer_steps_per_arm": {name: 0 for name in arms},
        "completed_synchronized_stage2_updates": 0,
        "all_safety_gates_pass": False,
        "safety_stop": None,
        "failure": failure,
        "control_update32_reference": None,
        "mechanism": {
            "surgery_nonzero": False, "tasks_touched_first_16": [],
            "cumulative_delta_projections": {},
        },
        "alignment_summaries": {
            "control_vanilla": {}, "treatment_pcgrad": {},
            "treatment_minus_control": {},
        },
        "terminal_END_controls": None,
        "duplicate_treatment_identity": None,
        "duplicate_treatment_evidence": None,
        "control_update32_state": None,
        "duplicate_treatment_canonical_outputs_identical": False,
        "checkpoint_reload_exact": False,
        "games_run": 0, "runtime_smoke_executed": False,
    }


def _dispatch_stage2_step(
    *,
    arm: str,
    loaded: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    partition: Mapping[str, Sequence[int]],
    state: Mapping[str, Any],
    update_ordinal: int,
) -> dict[str, Any]:
    """Dispatch v5 control exclusively to legacy and treatment to PCGrad."""

    if arm == "control_vanilla":
        return _control_reference_step(
            loaded=loaded,
            prepare_receipt=prepare_receipt,
            partition=partition,
            state=state,
            update_ordinal=update_ordinal,
        )
    if arm == "treatment_pcgrad":
        return _custom_stage2_step(
            arm=arm,
            loaded=loaded,
            prepare_receipt=prepare_receipt,
            partition=partition,
            optimizer=state["optimizer"],
            update_ordinal=update_ordinal,
            stage2_start=state["stage2_start_parameters"],
        )
    raise ValueError("unknown Stage-2 dispatcher arm")


def run_matched_arms(
    prepare_receipt: Mapping[str, Any], *, duplicate_treatment: bool = True
) -> dict[str, Any]:
    """Run matched arms with rollback to the last synchronized transaction."""

    validate_prepare_receipt(prepare_receipt)
    partition = _fixed_partition_from_receipt(prepare_receipt)
    loaded_arms = _load_execution_arms(prepare_receipt)
    arms = {name: _new_stage1_state(loaded) for name, loaded in loaded_arms.items()}
    zero = _snapshot_synchronized_pair(arms)
    failing_arm = "control_vanilla"
    try:
        for failing_arm in ("control_vanilla", "treatment_pcgrad"):
            _transactional_stage1_step(
                arms[failing_arm], loaded_arms[failing_arm], prepare_receipt
            )
        stage1_equality = validate_stage1_arm_equality(
            arms["control_vanilla"]["stage1_equality_evidence"],
            arms["treatment_pcgrad"]["stage1_equality_evidence"],
        )
    except Exception as error:
        _restore_synchronized_pair(arms, zero)
        run = _empty_run(
            arms,
            loaded_arms,
            failure={
                "failing_arm": failing_arm, "phase": "stage1",
                "exception_type": type(error).__name__, "message": str(error),
                "rolled_back_to_synchronized_steps": 0,
            },
        )
        return run
    run = _empty_run(arms, loaded_arms, failure=None)
    run["stage1_equality"] = stage1_equality
    run["completed_optimizer_steps_per_arm"] = {
        "control_vanilla": 1, "treatment_pcgrad": 1
    }
    stage1_duplicate_state = {
        "model_state": copy.deepcopy(arms["treatment_pcgrad"]["model"].state_dict()),
        "optimizer_state": copy.deepcopy(
            arms["treatment_pcgrad"]["optimizer"].state_dict()
        ),
    }
    if any(arms[name]["stage1_safety"]["hard_stop"] for name in arms):
        run["safety_stop"] = {"after_stage1": True}
        run["failure"] = {
            "failing_arm": None, "phase": "stage1_safety",
            "exception_type": None, "message": None,
            "rolled_back_to_synchronized_steps": 1,
        }
        return run
    initial_frozen_hashes = {
        name: _tensor_sha256_v2(value)
        for name, value in arms["control_vanilla"]["initial_parameters"].items()
        if name.startswith(("state_encoder.", "action_encoder.", base.VALUE_PREFIX))
    }
    control_previous_hash = arms["control_vanilla"]["stage1_record_sha256"]
    touched_first16: set[str] = set()
    surgery_nonzero = False
    cumulative_projections: dict[str, Any] = {}
    safety_stop = None
    for update in range(1, STAGE2_UPDATES + 1):
        synchronized = _snapshot_synchronized_pair(arms)
        phase = "control_step"
        failing_arm = "control_vanilla"
        try:
            control = arms["control_vanilla"]
            control_step = _dispatch_stage2_step(
                arm="control_vanilla",
                loaded=loaded_arms["control_vanilla"],
                prepare_receipt=prepare_receipt,
                partition=partition,
                state=control,
                update_ordinal=update,
            )
            phase = "treatment_step"
            failing_arm = "treatment_pcgrad"
            treatment = arms["treatment_pcgrad"]
            treatment_step = _dispatch_stage2_step(
                arm="treatment_pcgrad",
                loaded=loaded_arms["treatment_pcgrad"],
                prepare_receipt=prepare_receipt,
                partition=partition,
                state=treatment,
                update_ordinal=update,
            )
            steps = {
                "control_vanilla": control_step,
                "treatment_pcgrad": treatment_step,
            }
            metrics_by_arm: dict[str, list[dict[str, Any]]] = {}
            safety_by_arm: dict[str, dict[str, Any]] = {}
            raw_safety: dict[str, dict[str, Any]] = {}
            compacts: dict[str, dict[str, Any]] = {}
            for failing_arm in ("control_vanilla", "treatment_pcgrad"):
                phase = "post_step_diagnostics"
                state = arms[failing_arm]
                loaded = loaded_arms[failing_arm]
                metrics = base._measure_stage(
                    loaded, prepare_receipt, stage=2,
                    stage_2_update_ordinal=update,
                )
                metrics_by_arm[failing_arm] = metrics
                steps[failing_arm]["tensor_evidence"]["ordered_outputs"] = (
                    _ordered_output_tensor_evidence(metrics)
                )
                value = base.value_change_summary(prepare_receipt, metrics)
                frozen = base._frozen_value_contract_evidence(
                    state["model"], state["optimizer"], initial_frozen_hashes
                )
                safety = base.evaluate_stage_gates(
                    prepare_receipt,
                    metrics,
                    stage=2,
                    stage_2_update_ordinal=update,
                    training_nonfinite_count=steps[failing_arm]["nonfinite_count"],
                    parameter_optimizer_contract_pass=True,
                    value_contract_pass=(
                        value["all_rows_byte_exact_to_initial"]
                        and value["raw_value_mse_exact_to_initial"]
                        and value["aggregate_hash_exact_to_initial"]
                        and frozen["parameter_hashes_exact"]
                        and frozen["optimizer_state_absent"]
                    ),
                )
                raw_safety[failing_arm] = safety
                safety = _apply_clip_milestone_gate(
                    safety, steps[failing_arm], update_ordinal=update
                )
                safety_by_arm[failing_arm] = safety
                compact = {
                    "stage_2_update_ordinal": update,
                    "step": steps[failing_arm], "safety": safety,
                    "compact_830_row_alignment_summary": (
                        _alignment_summary_for_metrics(prepare_receipt, metrics)
                    ),
                    "value_identity": value,
                    "frozen_encoder_value_contract": frozen,
                    "output_hashes": base._ordered_output_hashes(metrics),
                    "raw_rows_persisted": update in DIAGNOSTIC_UPDATES,
                }
                compact["record_sha256"] = canonical_sha256(
                    _compact_without_tensor_evidence(compact)
                )
                compacts[failing_arm] = compact
        except Exception as error:
            _restore_synchronized_pair(arms, synchronized)
            run["failure"] = {
                "failing_arm": failing_arm, "phase": phase,
                "stage2_update_ordinal": update,
                "exception_type": type(error).__name__, "message": str(error),
                "rolled_back_to_synchronized_steps": 1 + update - 1,
            }
            break
        previous_control_hash = control_previous_hash
        previous_touched = set(touched_first16)
        previous_surgery = surgery_nonzero
        previous_projections = copy.deepcopy(cumulative_projections)
        previous_control_gate = copy.deepcopy(run["control_update32_reference"])
        previous_control_state = copy.deepcopy(run["control_update32_state"])
        previous_alignment = copy.deepcopy(run["alignment_summaries"])
        try:
            phase = "post_step_evidence_commit"
            failing_arm = None
            for name in ("control_vanilla", "treatment_pcgrad"):
                run["update_records"][name].append(compacts[name])
                if update in DIAGNOSTIC_UPDATES:
                    run["full_830_row_diagnostics"][name][str(update)] = metrics_by_arm[name]
            surgery = treatment_step["gradient_diagnostics"]
            surgery_nonzero = surgery_nonzero or surgery["surgery_nonzero"]
            if update <= 16:
                touched_first16.update(surgery["task_changed_by_surgery"])
            if update in (48, 64):
                cumulative_projections[str(update)] = {
                    task: treatment_step["cumulative_delta_task_projections"][task]
                    for task in PRIORITY_TASKS
                }
            legacy = _control_legacy_compact(
                step=control_step,
                metrics=metrics_by_arm["control_vanilla"],
                safety=raw_safety["control_vanilla"],
                value_identity=compacts["control_vanilla"]["value_identity"],
                frozen_evidence=compacts["control_vanilla"][
                    "frozen_encoder_value_contract"
                ],
                previous_record_hash=control_previous_hash,
                update_ordinal=update,
            )
            control_previous_hash = legacy["record_hash"]
            if update == 32:
                optimizer_reference = optimizer_canonical_record(
                    control["optimizer"], control["model"]
                )
                outputs = base._ordered_output_hashes(
                    metrics_by_arm["control_vanilla"]
                )
                run["control_update32_reference"] = validate_control_update32({
                    "record_sha256": legacy["record_hash"], **outputs,
                    "parameter_bytes_sha256": {
                        name: _model_parameter_hashes(control["model"])[name]
                        for name in REFERENCE_CONTROL["stage32_parameter_bytes_sha256"]
                    },
                    "optimizer_canonical_sha256": optimizer_reference["canonical_sha256"],
                    "optimizer_param_group_canonical_sha256": optimizer_reference[
                        "param_group_canonical_sha256"
                    ],
                    "optimizer_state_steps": optimizer_step_states(
                        control["optimizer"], control["model"]
                    ),
                })
                run["control_update32_state"] = {
                    "model_state": {
                        name: value.detach().cpu().clone()
                        for name, value in control["model"].state_dict().items()
                    },
                    "optimizer_state": copy.deepcopy(
                        control["optimizer"].state_dict()
                    ),
                    "ordered_outputs": _ordered_output_tensor_evidence(
                        metrics_by_arm["control_vanilla"]
                    ),
                    "legacy_record": copy.deepcopy(legacy),
                }
            if update in (48, 64):
                for name in ("control_vanilla", "treatment_pcgrad"):
                    run["alignment_summaries"][name][str(update)] = (
                        _alignment_summary_for_metrics(
                            prepare_receipt, metrics_by_arm[name]
                        )
                    )
                run["alignment_summaries"]["treatment_minus_control"][str(update)] = (
                    _difference_alignment_summary(
                        prepare_receipt,
                        metrics_by_arm["control_vanilla"],
                        metrics_by_arm["treatment_pcgrad"],
                    )
                )
            stop = evaluate_safety_stop(safety_by_arm)
        except Exception as error:
            _restore_synchronized_pair(arms, synchronized)
            for name in ("control_vanilla", "treatment_pcgrad"):
                if len(run["update_records"][name]) == update:
                    run["update_records"][name].pop()
                run["full_830_row_diagnostics"][name].pop(str(update), None)
            control_previous_hash = previous_control_hash
            touched_first16 = previous_touched
            surgery_nonzero = previous_surgery
            cumulative_projections = previous_projections
            run["control_update32_reference"] = previous_control_gate
            run["control_update32_state"] = previous_control_state
            run["alignment_summaries"] = previous_alignment
            run["failure"] = {
                "failing_arm": None, "phase": phase,
                "stage2_update_ordinal": update,
                "exception_type": type(error).__name__, "message": str(error),
                "rolled_back_to_synchronized_steps": update,
            }
            break
        if stop["stop_both_arms"]:
            safety_stop = {"after_stage2_update": update, **stop}
            run["failure"] = {
                "failing_arm": None, "phase": "stage2_safety",
                "stage2_update_ordinal": update,
                "exception_type": None, "message": None,
                "rolled_back_to_synchronized_steps": 1 + update,
            }
            break
    completed_updates = len(run["update_records"]["control_vanilla"])
    if len(run["update_records"]["treatment_pcgrad"]) != completed_updates:
        raise AssertionError("transaction retained unmatched update records")
    run["completed_synchronized_stage2_updates"] = completed_updates
    run["completed_optimizer_steps_per_arm"] = {
        "control_vanilla": 1 + completed_updates,
        "treatment_pcgrad": 1 + completed_updates,
    }
    run["safety_stop"] = safety_stop
    run["all_safety_gates_pass"] = (
        completed_updates == STAGE2_UPDATES and safety_stop is None
        and run["failure"] is None
    )
    run["mechanism"] = {
        "surgery_nonzero": surgery_nonzero,
        "tasks_touched_first_16": sorted(touched_first16),
        "cumulative_delta_projections": cumulative_projections,
    }
    if completed_updates == STAGE2_UPDATES:
        try:
            terminal_metrics = run["full_830_row_diagnostics"]["treatment_pcgrad"]["64"]
            run["terminal_END_controls"] = terminal_end_controls(
                prepare_receipt, terminal_metrics
            )
            primary = {
                "parameter_hashes": _model_parameter_hashes(
                    arms["treatment_pcgrad"]["model"]
                ),
                "optimizer_canonical": optimizer_canonical_record(
                    arms["treatment_pcgrad"]["optimizer"],
                    arms["treatment_pcgrad"]["model"],
                ),
                "output_hashes": base._ordered_output_hashes(terminal_metrics),
                "terminal_step_sha256": _runtime_step_record_sha256_v2(
                    run["update_records"]["treatment_pcgrad"][-1]["step"]
                ),
                "per_update_record_chain_sha256": canonical_sha256([
                    _runtime_step_record_sha256_v2(row["step"])
                    for row in run["update_records"]["treatment_pcgrad"]
                ]),
            }
            if duplicate_treatment:
                duplicate_result = _run_duplicate_treatment(
                    loaded_template=loaded_arms["treatment_pcgrad"],
                    prepare_receipt=prepare_receipt,
                    stage1_state=stage1_duplicate_state,
                    partition=partition,
                )
                duplicate_identity = duplicate_result["identity"]
                run["duplicate_treatment_identity"] = duplicate_identity
                run["duplicate_treatment_evidence"] = duplicate_result[
                    "tensor_evidence"
                ]
                run["duplicate_treatment_canonical_outputs_identical"] = (
                    canonical_json_bytes(primary) == canonical_json_bytes(duplicate_identity)
                )
        except Exception as error:
            run["failure"] = {
                "failing_arm": None, "phase": "terminal_diagnostics",
                "stage2_update_ordinal": 64,
                "exception_type": type(error).__name__, "message": str(error),
                "rolled_back_to_synchronized_steps": 65,
            }
    return run


def _recompute_pending_gates_v2_impl(
    *,
    spec: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    manifest_path: Path,
    manifest_sha256: str,
) -> dict[str, Any]:
    """v2 load-only authority derived from raw tensors and immutable rows."""

    failures: list[str] = []
    discrepancies: list[str] = []
    try:
        manifest, manifest_failures = _load_pending_manifest(
            manifest_path, manifest_sha256
        )
        failures.extend(manifest_failures)
    except Exception as error:
        return {
            "offline_pass": False,
            "bundle_integrity_pass": False,
            "failures": [f"manifest:{type(error).__name__}:{error}"],
            "summary_discrepancies": [],
            "recomputed": {},
        }
    directory = manifest_path.parent
    if manifest.get("execution_spec_sha256") != spec.get("_file_sha256"):
        failures.append("manifest_execution_spec")
    if manifest.get("prepare_receipt_sha256") != prepare_receipt.get("receipt_sha256"):
        failures.append("manifest_prepare_receipt")
    if manifest.get("failure") is not None:
        failures.append("manifest_transaction_failure")
    required = (
        "run_summary.json", "stage1_diagnostics.jsonl",
        "milestone_diagnostics.jsonl", "step_summaries.jsonl",
        "gradient_tensors.pt", "control_pending.pt", "treatment_pending.pt",
        "PENDING_AUDIT",
    )
    if any(not (directory / name).is_file() for name in required):
        failures.append("missing_required_evidence")
        return {
            "offline_pass": False,
            "bundle_integrity_pass": False,
            "failures": sorted(set(failures)),
            "summary_discrepancies": [],
            "recomputed": {},
        }
    try:
        summary = json.loads((directory / "run_summary.json").read_text("utf-8"))
        if not isinstance(summary, Mapping) or set(summary) != RUN_SUMMARY_KEYS_V2:
            raise ValueError("run summary key set mismatch")
        summary_core = dict(summary)
        summary_claim = summary_core.pop("run_summary_sha256", None)
        if summary_claim != canonical_sha256(summary_core):
            failures.append("run_summary_self_hash")
        if (
            summary.get("schema_version") != RUN_SUMMARY_SCHEMA_VERSION
            or summary.get("status") != "PENDING_AUDIT"
            or summary.get("caller_summaries_informational_only") is not True
            or summary.get("execution_spec_sha256") != spec["_file_sha256"]
            or summary.get("prepare_receipt_sha256")
            != prepare_receipt["receipt_sha256"]
            or summary.get("games_run") != 0
            or summary.get("runtime_smoke_executed") is not False
            or summary.get("expected_task_order") != list(TASK_ORDER)
            or summary.get("expected_diagnostic_updates")
            != list(DIAGNOSTIC_UPDATES)
        ):
            failures.append("run_summary_binding")
        marker = json.loads((directory / "PENDING_AUDIT").read_text("utf-8"))
        expected_marker = {
            "status": "PENDING_AUDIT",
            "execution_spec_sha256": spec["_file_sha256"],
            "prepare_receipt_sha256": prepare_receipt["receipt_sha256"],
            "games_run": 0,
            "runtime_smoke_executed": False,
        }
        if canonical_json_bytes(marker) != canonical_json_bytes(expected_marker):
            failures.append("pending_marker")
        stage1_rows = _read_jsonl(directory / "stage1_diagnostics.jsonl")
        milestone_rows = _read_jsonl(directory / "milestone_diagnostics.jsonl")
        step_rows = _read_jsonl(directory / "step_summaries.jsonl")
        gradients = torch.load(
            directory / "gradient_tensors.pt", map_location="cpu",
            weights_only=True,
        )
        expected_summary_evidence = {
            name: {
                "bytes": (directory / name).stat().st_size,
                "sha256": sha256_file(directory / name),
            }
            for name in (
                "stage1_diagnostics.jsonl", "milestone_diagnostics.jsonl",
                "step_summaries.jsonl", "gradient_tensors.pt",
            )
        }
        if summary.get("evidence") != expected_summary_evidence:
            failures.append("run_summary_evidence")
    except Exception as error:
        failures.append(f"evidence_load:{type(error).__name__}:{error}")
        return {
            "offline_pass": False,
            "bundle_integrity_pass": not manifest_failures,
            "failures": sorted(set(failures)),
            "summary_discrepancies": [],
            "recomputed": {},
        }
    expected_gradient_keys = {
        "schema_version", "task_order", "parameter_names", "parameter_layout",
        "completed_synchronized_stage2_updates", "stage2_start_states",
        "control_update32_state", "duplicate_treatment_state", "series",
    }
    if (
        not isinstance(gradients, Mapping)
        or set(gradients) != expected_gradient_keys
        or gradients.get("schema_version")
        != "mass-preserving-pcgrad-gradient-tensors-v2"
        or tuple(gradients.get("task_order") or ()) != TASK_ORDER
        or tuple(gradients.get("parameter_names") or ()) != PARAMETER_NAMES
    ):
        failures.append("gradient_bundle_schema")
    if not isinstance(gradients, Mapping):
        gradients = {}
    completed = gradients.get("completed_synchronized_stage2_updates")
    if completed != STAGE2_UPDATES:
        failures.append("completed_updates")
    completed_steps = {
        "control_vanilla": TOTAL_STEPS_PER_ARM,
        "treatment_pcgrad": TOTAL_STEPS_PER_ARM,
    }
    if manifest.get("completed_synchronized_stage2_updates") != STAGE2_UPDATES:
        failures.append("manifest_completed_updates")
    if manifest.get("completed_optimizer_steps_per_arm") != completed_steps:
        failures.append("manifest_optimizer_steps")
    if summary.get("completed_synchronized_stage2_updates") != STAGE2_UPDATES:
        discrepancies.append("completed_synchronized_stage2_updates")
    if summary.get("completed_optimizer_steps_per_arm") != completed_steps:
        discrepancies.append("completed_optimizer_steps_per_arm")
    if summary.get("failure") is not None:
        discrepancies.append("failure")
    expected_series = {
        f"updates/{update:02d}/{arm}"
        for arm in ("control_vanilla", "treatment_pcgrad")
        for update in range(1, STAGE2_UPDATES + 1)
    }
    if set(gradients.get("series") or {}) != expected_series:
        failures.append("gradient_series_completeness")
    step_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for row in step_rows:
        arm = row.get("arm")
        update = row.get("stage_2_update_ordinal")
        key = (str(arm), int(update) if isinstance(update, int) else -1)
        if key in step_by_key:
            failures.append(f"step_duplicate:{key[0]}:{key[1]}")
        step_by_key[key] = row
        raw_item = (gradients.get("series") or {}).get(
            f"updates/{key[1]:02d}/{key[0]}"
        )
        failures.extend(_public_step_reference_failures_v2(
            row, raw_item, arm=key[0], update=key[1]
        ))
    expected_step_keys = {
        (arm, update)
        for arm in ("control_vanilla", "treatment_pcgrad")
        for update in range(1, STAGE2_UPDATES + 1)
    }
    if set(step_by_key) != expected_step_keys or len(step_rows) != 128:
        failures.append("step_completeness")
    milestone_by_key: dict[tuple[str, int], list[Any]] = {}
    for row in milestone_rows:
        arm = row.get("arm")
        update = row.get("stage2_update_ordinal")
        ordinal = row.get("row_ordinal")
        key = (str(arm), int(update) if isinstance(update, int) else -1)
        values = milestone_by_key.setdefault(key, [None] * EXPECTED_ROWS)
        if (
            not isinstance(ordinal, int) or not 0 <= ordinal < EXPECTED_ROWS
            or values[ordinal] is not None
        ):
            failures.append(f"milestone_row_key:{key[0]}:{key[1]}")
            continue
        values[ordinal] = row.get("diagnostic")
    expected_milestone_keys = {
        (arm, update)
        for arm in ("control_vanilla", "treatment_pcgrad")
        for update in DIAGNOSTIC_UPDATES
    }
    if (
        set(milestone_by_key) != expected_milestone_keys
        or len(milestone_rows) != 2 * len(DIAGNOSTIC_UPDATES) * EXPECTED_ROWS
        or any(value is None for rows in milestone_by_key.values() for value in rows)
    ):
        failures.append("milestone_completeness")
    expected_counts = {
        "stage1_diagnostic_row_count": len(stage1_rows),
        "milestone_diagnostic_row_count": len(milestone_rows),
        "step_summary_row_count": len(step_rows),
    }
    for field, expected in expected_counts.items():
        if summary.get(field) != expected:
            discrepancies.append(field)
    stage1_gate, stage1_failures, stage1_discrepancies = (
        _stage1_cross_binding_v2(gradients, stage1_rows, summary)
    )
    failures.extend(stage1_failures)
    discrepancies.extend(stage1_discrepancies)
    if completed == STAGE2_UPDATES and set(gradients.get("series") or {}) == expected_series:
        control_replay = _replay_gradient_arm(
            gradients, prepare_receipt, arm="control_vanilla"
        )
        treatment_replay = _replay_gradient_arm(
            gradients, prepare_receipt, arm="treatment_pcgrad"
        )
    else:
        control_replay = {"passed": False, "failures": ["series_shape"]}
        treatment_replay = {"passed": False, "failures": ["series_shape"]}
    failures.extend(
        f"control_replay:{value}" for value in control_replay.get("failures") or ()
    )
    failures.extend(
        f"treatment_replay:{value}" for value in treatment_replay.get("failures") or ()
    )
    for key, retained in milestone_by_key.items():
        replay = control_replay if key[0] == "control_vanilla" else treatment_replay
        rebuilt = (replay.get("outputs") or {}).get(key[1])
        if rebuilt is None or canonical_json_bytes(rebuilt) != canonical_json_bytes(retained):
            failures.append(f"milestone_output_binding:{key[0]}:{key[1]}")
    numeric = _strict_numerical_gates_from_replay(
        gradients, prepare_receipt, control_replay, treatment_replay
    )
    failures.extend(f"numerical:{value}" for value in numeric.get("failures") or ())
    checkpoints: dict[str, Any] = {}
    checkpoint_raw: dict[str, Any] = {}
    for arm, filename, replay in (
        ("control_vanilla", "control_pending.pt", control_replay),
        ("treatment_pcgrad", "treatment_pending.pt", treatment_replay),
    ):
        terminal = (replay.get("outputs") or {}).get(64) or []
        gate, gate_failures, raw = _checkpoint_cross_binding_v2(
            directory / filename, arm=arm, spec=spec,
            prepare_receipt=prepare_receipt, replay=replay,
            expected_output_metrics=terminal,
        )
        checkpoints[arm] = gate
        checkpoint_raw[arm] = raw
        failures.extend(f"checkpoint:{arm}:{value}" for value in gate_failures)
    control32, control32_failures = _control32_cross_binding_v2(
        gradients, control_replay, prepare_receipt,
        checkpoint_raw.get("control_vanilla") or {},
    )
    failures.extend(f"control32:{value}" for value in control32_failures)
    treatment_rows = [
        step_by_key[("treatment_pcgrad", update)]
        for update in range(1, STAGE2_UPDATES + 1)
        if ("treatment_pcgrad", update) in step_by_key
    ]
    duplicate, duplicate_failures = _duplicate_cross_binding_v2(
        gradients, treatment_replay,
        checkpoint_raw.get("treatment_pcgrad") or {}, treatment_rows,
    )
    failures.extend(f"duplicate:{value}" for value in duplicate_failures)
    expected_control32_summary = {
        "passed": control32.get("passed") is True,
        "evidence": control32.get("evidence"),
    }
    if canonical_json_bytes(summary.get("control_update32_reference")) != canonical_json_bytes(
        expected_control32_summary
    ):
        discrepancies.append("control_update32_reference")
    treatment_checkpoint = checkpoints.get("treatment_pcgrad") or {}
    expected_duplicate_identity = {
        "parameter_hashes": treatment_checkpoint.get("model_parameter_hashes"),
        "optimizer_canonical": treatment_checkpoint.get("optimizer_canonical"),
        "output_hashes": treatment_checkpoint.get("output_hashes"),
        "terminal_step_sha256": duplicate.get("terminal_step_sha256"),
        "per_update_record_chain_sha256": duplicate.get("record_chain_sha256"),
    }
    if canonical_json_bytes(summary.get("duplicate_treatment_identity")) != canonical_json_bytes(
        expected_duplicate_identity
    ):
        discrepancies.append("duplicate_treatment_identity")
    expected_checkpoint_summary: dict[str, Any] = {}
    for arm in ("control_vanilla", "treatment_pcgrad"):
        derived = checkpoints.get(arm) or {}
        expected_checkpoint_summary[arm] = copy.deepcopy(
            derived.get("summary_evidence") or {
                "runtime_loader_pass": False,
                "model_state_byte_exact": False,
                "optimizer_state_byte_exact": False,
                "metadata_exact": False,
                "optimizer_state_steps": {},
                "terminal_output_row_count": 0,
                "terminal_output_hashes": None,
            }
        )
    if canonical_json_bytes(summary.get("checkpoint_reload_evidence")) != (
        canonical_json_bytes(expected_checkpoint_summary)
    ):
        discrepancies.append("checkpoint_reload_evidence")
    raw_alignment = (numeric.get("details") or {}).get("updates") or {}
    expected_alignment = {
        "control_vanilla": {}, "treatment_pcgrad": {},
        "treatment_minus_control": {},
    }
    for update in (48, 64):
        values = raw_alignment.get(str(update)) or {}
        expected_alignment["control_vanilla"][str(update)] = values.get("control")
        expected_alignment["treatment_pcgrad"][str(update)] = values.get("treatment")
        expected_alignment["treatment_minus_control"][str(update)] = values.get(
            "treatment_minus_control"
        )
    if canonical_json_bytes(summary.get("alignment_summaries")) != canonical_json_bytes(
        expected_alignment
    ):
        discrepancies.append("alignment_summaries")
    if canonical_json_bytes(summary.get("terminal_END_controls")) != canonical_json_bytes(
        (numeric.get("details") or {}).get("END")
    ):
        discrepancies.append("terminal_END_controls")
    structural_pass = not failures and stage1_gate.get("passed") is True
    discrepancies.extend(_caller_summary_discrepancies_v2(
        summary=summary, step_by_key=step_by_key, gradients=gradients,
        prepare_receipt=prepare_receipt, numeric=numeric,
        control_replay=control_replay, treatment_replay=treatment_replay,
        control32=control32, duplicate=duplicate,
        raw_pass_before_discrepancies=structural_pass,
    ))
    safety_details = (numeric.get("details") or {}).get("safety") or {}
    expected_safety_stop = None
    for update in range(1, STAGE2_UPDATES + 1):
        arm_failures = {
            arm: list((safety_details.get(f"{arm}:{update}") or {}).get("failures") or ())
            for arm in ("control_vanilla", "treatment_pcgrad")
            if (safety_details.get(f"{arm}:{update}") or {}).get("pass") is not True
        }
        if arm_failures:
            expected_safety_stop = {
                "after_stage2_update": update,
                "stop_both_arms": True,
                "arm_failures": arm_failures,
            }
            break
    all_safety = expected_safety_stop is None and set(safety_details) == {
        f"{arm}:{update}"
        for arm in ("control_vanilla", "treatment_pcgrad")
        for update in range(1, STAGE2_UPDATES + 1)
    }
    strict_failures = sorted(set(failures))
    expected_summary_fields = {
        "schema_version": RUN_SUMMARY_SCHEMA_VERSION,
        "status": "PENDING_AUDIT",
        "caller_summaries_informational_only": True,
        "execution_spec_path": manifest.get("execution_spec_path"),
        "execution_spec_sha256": spec["_file_sha256"],
        "prepare_receipt_sha256": prepare_receipt["receipt_sha256"],
        "completed_optimizer_steps_per_arm": completed_steps,
        "completed_synchronized_stage2_updates": STAGE2_UPDATES,
        "failure": manifest.get("failure"),
        "safety_stop": expected_safety_stop,
        "all_safety_gates_pass": all_safety,
        "stage1_equality": stage1_gate.get("summary_stage1_equality"),
        "stage1_record_hashes": stage1_gate.get("record_hashes"),
        "stage1_complete_evidence": stage1_gate.get("summary_complete_evidence"),
        "control_update32_reference": expected_control32_summary,
        "mechanism": copy.deepcopy(
            (numeric.get("details") or {}).get("mechanism")
        ),
        "alignment_summaries": expected_alignment,
        "terminal_END_controls": copy.deepcopy(
            (numeric.get("details") or {}).get("END")
        ),
        "duplicate_treatment_identity": expected_duplicate_identity,
        "duplicate_treatment_canonical_outputs_identical": (
            duplicate.get("passed") is True
        ),
        "checkpoint_reload_evidence": expected_checkpoint_summary,
        "strict_offline_gates": {
            "offline_pass": not strict_failures,
            "failures": strict_failures,
        },
        "evidence": expected_summary_evidence,
        "expected_task_order": list(TASK_ORDER),
        "expected_diagnostic_updates": list(DIAGNOSTIC_UPDATES),
        "stage1_diagnostic_row_count": len(stage1_rows),
        "milestone_diagnostic_row_count": len(milestone_rows),
        "step_summary_row_count": len(step_rows),
        "games_run": 0,
        "runtime_smoke_executed": False,
    }
    discrepancies.extend(_run_summary_exact_discrepancies_v3(
        summary, expected_summary_fields
    ))
    if discrepancies:
        failures.extend(f"summary_discrepancy:{value}" for value in discrepancies)
    bundle_integrity_pass = not manifest_failures and not any(
        value.startswith((
            "manifest_", "pending_", "missing_", "evidence_load",
            "gradient_bundle_schema", "gradient_series_completeness",
            "step_completeness", "milestone_completeness",
        ))
        for value in failures
    )
    return {
        "offline_pass": not failures,
        "bundle_integrity_pass": bundle_integrity_pass,
        "failures": sorted(set(failures)),
        "summary_discrepancies": sorted(set(discrepancies)),
        "recomputed": {
            "stage1": stage1_gate,
            "gradient_replay": {
                "control_vanilla": {
                    "passed": control_replay.get("passed") is True,
                    "failures": control_replay.get("failures") or [],
                    "start_flat_sha256": control_replay.get("start_flat_sha256"),
                },
                "treatment_pcgrad": {
                    "passed": treatment_replay.get("passed") is True,
                    "failures": treatment_replay.get("failures") or [],
                    "start_flat_sha256": treatment_replay.get("start_flat_sha256"),
                    "surgery_tasks_first16": treatment_replay.get(
                        "surgery_tasks_first16"
                    ) or [],
                    "cumulative_projections": treatment_replay.get(
                        "cumulative_projections"
                    ) or {},
                },
            },
            "strict_numerical_gates": numeric,
            "control_update32": control32,
            "duplicate_treatment": duplicate,
            "checkpoints": checkpoints,
            "counts": {
                "stage1_rows": len(stage1_rows),
                "milestone_rows": len(milestone_rows),
                "step_rows": len(step_rows),
                "gradient_series": len(gradients.get("series") or {}),
            },
        },
    }


RECOMPUTATION_RESULT_KEYS_V2 = {
    "offline_pass", "bundle_integrity_pass", "failures",
    "summary_discrepancies", "recomputed",
}


def _stable_failed_recomputation_v2(error: BaseException) -> dict[str, Any]:
    return {
        "offline_pass": False,
        "bundle_integrity_pass": False,
        "failures": [
            f"fail_closed:{type(error).__name__}:{str(error)[:1000]}"
        ],
        "summary_discrepancies": [],
        "recomputed": {},
    }


def recompute_pending_gates(
    *,
    spec: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    manifest_path: Path,
    manifest_sha256: str,
) -> dict[str, Any]:
    """Total fail-closed boundary for every serialized pending bundle."""

    try:
        result = _recompute_pending_gates_v2_impl(
            spec=spec, prepare_receipt=prepare_receipt,
            manifest_path=manifest_path, manifest_sha256=manifest_sha256,
        )
        if (
            not isinstance(result, dict)
            or set(result) != RECOMPUTATION_RESULT_KEYS_V2
            or not isinstance(result.get("offline_pass"), bool)
            or not isinstance(result.get("bundle_integrity_pass"), bool)
            or not isinstance(result.get("failures"), list)
            or not isinstance(result.get("summary_discrepancies"), list)
            or not isinstance(result.get("recomputed"), dict)
        ):
            raise ValueError("recomputation returned an unstable schema")
        canonical_json_bytes(result)
        return result
    except BaseException as error:
        return _stable_failed_recomputation_v2(error)


if __name__ == "__main__":
    raise SystemExit(main())
