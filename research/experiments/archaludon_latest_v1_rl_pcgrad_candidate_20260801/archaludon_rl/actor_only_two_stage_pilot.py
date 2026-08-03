"""Audited iteration-006 actor-only, two-stage PPO prepare/execute boundary.

The implementation plan authorizes ``prepare`` only.  ``execute`` is present for
a later, separately hashed execution specification; this module never executes
training at import time and prepare never constructs an optimizer.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, dataclass
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import statistics
from typing import Any, Iterable, Mapping, Sequence

import torch

from . import conservative_ppo_pilot as inherited
from .frozen_sources import find_repo_root, sha256_file
from .model import ModelConfig, ResidualActorCritic, _validate_metadata, checkpoint_metadata
from .train_ppo import PPOConfig, _torch_behavior_anchor_kl, _torch_behavior_distribution


PLAN_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_006_actor_only_two_stage_bootstrap_implementation_plan.json"
)
PLAN_SHA256 = "372B713B41649B42553953E3857C33258DBDD85F0DB460785525D8A0FE02C1B3"
PLAN_SCHEMA_VERSION = "archaludon-rl-actor-only-two-stage-implementation-plan-v1"
PLAN_ID = "phase1-iteration-006-actor-only-two-stage-bootstrap-20260801"
CORRECTION_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_006_actor_only_two_stage_bootstrap_plan_correction_v1.json"
)
CORRECTION_SHA256 = "4A7F3EDE454603F843D874E05DBE4808C5AF0FA641F77750DB22867AD9CB90AA"
CORRECTION_SCHEMA_VERSION = "archaludon-rl-actor-only-two-stage-plan-correction-v1"
CORRECTION_ID = "phase1-iteration-006-actor-only-two-stage-plan-correction-20260801"
REMEDIATION_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_006_actor_only_two_stage_bootstrap_prepare_audit_remediation_v1.json"
)
REMEDIATION_SHA256 = "41F8A68EEE551CCF4139D2F3F905ADE807D48CFF3D1858BEFE7ED86E090F2C6D"
REMEDIATION_SCHEMA_VERSION = (
    "archaludon-rl-actor-only-two-stage-prepare-audit-remediation-v1"
)
REMEDIATION_ID = (
    "phase1-iteration-006-actor-only-two-stage-prepare-audit-remediation-20260801"
)
REMEDIATION_CORRECTION_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_006_actor_only_two_stage_bootstrap_prepare_audit_"
    "remediation_correction_v1.json"
)
REMEDIATION_CORRECTION_SHA256 = (
    "B173C031D77305DEA85A4DA29DA0CC02C39C92100DEBB04815BD95E9A9D2897C"
)
REMEDIATION_CORRECTION_SCHEMA_VERSION = (
    "archaludon-rl-actor-only-two-stage-prepare-audit-remediation-correction-v1"
)
REMEDIATION_CORRECTION_ID = (
    "phase1-iteration-006-prepare-audit-remediation-correction-20260801"
)

IMPLEMENTATION_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl_actor_bootstrap_candidate_20260801"
)
SOURCE_IMPLEMENTATION_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl_ppo_candidate_20260731"
)
SOURCE_IMPLEMENTATION_FILE_COUNT = 49
SOURCE_IMPLEMENTATION_SHA256 = (
    "2197C82DF499EE3026F960C6A1690094A2EF5D4FB4863E07267E025BE2BDF940"
)
SOURCE_CONSERVATIVE_PILOT_SHA256 = (
    "5C1B3AD60E69894B19C5F92CBBD9A42AF7C4BD7546BE4360D51B4D8866B23930"
)
SOURCE_MODEL_SHA256 = (
    "B15665C47746A01C75AF8D79019D2AF13CCBF499A47213F0F8EF8461516536EC"
)

INPUT_CHECKPOINT_RELATIVE_PATH = inherited.INPUT_CHECKPOINT_RELATIVE_PATH
INPUT_CHECKPOINT_SHA256 = inherited.INPUT_CHECKPOINT_SHA256
MANIFEST_RELATIVE_PATH = inherited.MANIFEST_RELATIVE_PATH
MANIFEST_SHA256 = inherited.MANIFEST_SHA256
DATASET_SHA256 = inherited.DATASET_SHA256
BEHAVIOR_POLICY_SCHEMA_SHA256 = inherited.BEHAVIOR_POLICY_SCHEMA_SHA256
EXPECTED_ON_POLICY_ROWS = 830

V4_PROBE_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl_ppo_candidate_20260731/test_outputs/"
    "phase1_iteration_005_prepare_v4/pretraining_probe_receipt.json"
)
V4_PROBE_FILE_SHA256 = (
    "63E8599248E62FFD80D548A65109EBCE05E164463FA218C41B33F335D76DC322"
)
V4_PROBE_RECEIPT_SHA256 = (
    "CD7D8A8E8CA037E0A9D8036C2221AB336CB7F8BEDDA43D765F33F0EEEDD2D0E9"
)

PARENT_RESULT_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/PHASE1_ITERATION_005_RESULT.md"
)
PARENT_RESULT_SHA256 = "F092A1D58316ADB61CAADC0732D01C37B163607539EBA9E2677BD7B434FEBBA2"
PARENT_EXECUTION_SPEC_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_005_conservative_ppo_execution.json"
)
PARENT_EXECUTION_SPEC_SHA256 = (
    "D6A67C3A8791BA2A4B6002446E915D2484E32483984FF4C7FF4E8F34FAC72BCB"
)
PARENT_REJECTED_RECEIPT_RELATIVE_PATH = PurePosixPath(
    "_local_generated/analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_005_"
    "conservative_ppo_20260731/rejected_receipt.json"
)
PARENT_REJECTED_RECEIPT_FILE_SHA256 = (
    "9E3EEE5F64FD7B38B9A9BBF0C1CD7A3C7C959CC4FA6C4D652B859EE77E44FC93"
)
PARENT_REJECTED_RECEIPT_SHA256 = (
    "DAE29284F5DA13C5A330A539A0E218B88F698E835EC2D57EFC5FE9DF505AEE39"
)
REJECTED_CHECKPOINT_RELATIVE_PATH = PurePosixPath(
    "_local_generated/analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_005_"
    "conservative_ppo_20260731/candidate.pt"
)
REJECTED_CHECKPOINT_SHA256 = (
    "E7D0CA4DCEEBE33C8043D3C8A45DD9119CFE0E06ACC58F343E9A60BB7F787088"
)

PREPARE_OUTPUT_DIRECTORY_PREFIX = "phase1_iteration_006_prepare"
PREPARE_OUTPUT_FILENAME = "pretraining_probe_receipt.json"
PREPARE_RECEIPT_SCHEMA_VERSION = "actor-only-two-stage-pretraining-probe-v3"
EXECUTION_SPEC_SCHEMA_VERSION = "actor-only-two-stage-execution-spec-v3"
EXECUTION_RECEIPT_SCHEMA_VERSION = "actor-only-two-stage-execution-receipt-v3"
APPROVED_OUTPUT_RELATIVE_PATH = PurePosixPath(
    "_local_generated/analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_006_"
    "actor_only_two_stage_20260801"
)

ROW_MAP_SCHEMA_VERSION = "sampled-option-type-row-map-v1"
MEMBERSHIP_SCHEMA_VERSION = "sampled-option-type-membership-v1"
ROW_MAP_SHA256 = "F0BEBA7DAF76FC07E72B2830EE51D6216367FC517B91AE61795C61A41FD5E8BE"
DEADBAND_TAU = 1e-7
STAGE1_TRAINABLE_NAMES = (
    "residual_head.2.weight",
    "residual_head.2.bias",
)
ACTOR_PREFIXES = ("state_encoder.", "action_encoder.", "residual_head.")
VALUE_PREFIX = "value_head."
EXPECTED_ACTOR_NAMES = (
    "state_encoder.0.weight",
    "state_encoder.0.bias",
    "state_encoder.2.weight",
    "state_encoder.2.bias",
    "action_encoder.0.weight",
    "action_encoder.0.bias",
    "residual_head.0.weight",
    "residual_head.0.bias",
    "residual_head.2.weight",
    "residual_head.2.bias",
)
EXPECTED_VALUE_NAMES = (
    "value_head.0.weight",
    "value_head.0.bias",
    "value_head.2.weight",
    "value_head.2.bias",
)

TWO_STAGE_PPO_CONFIG = PPOConfig(
    gamma=0.99,
    gae_lambda=0.95,
    clip_ratio=0.1,
    value_coef=0.0,
    entropy_coef=0.0,
    anchor_kl_target=0.0005,
    anchor_kl_initial_coef=0.1,
    anchor_kl_hard_stop=0.002,
    gradient_clip=0.25,
    learning_rate=0.0001,
    epochs=2,
)
ADAM_CONFIG: dict[str, Any] = {
    "name": "Adam",
    "fresh_state": True,
    "single_object_across_stages": True,
    "parameter_universe": (
        "all state_encoder, action_encoder, and residual_head parameters; "
        "value_head is excluded"
    ),
    "betas": [0.9, 0.999],
    "eps": 1e-8,
    "weight_decay": 0.0,
    "amsgrad": False,
    "foreach": None,
    "maximize": False,
    "capturable": False,
    "differentiable": False,
    "fused": None,
    "decoupled_weight_decay": False,
}

_PLAN_TOP_KEYS = {
    "schema_version",
    "plan_id",
    "purpose",
    "strength_claim_allowed",
    "parent_result",
    "selected_hypothesis",
    "immutable_inputs",
    "isolated_implementation",
    "training_contract",
    "sampled_action_family_contract",
    "inherited_directional_gates",
    "global_stage_gates",
    "prepare_receipt_must_bind",
    "implementation_tests",
    "forbidden_changes",
    "output_semantics",
    "execution_stop_rule",
}


def canonical_json_bytes(value: Any, *, newline: bool = False) -> bytes:
    return inherited.canonical_json_bytes(value, newline=newline)


def canonical_sha256(value: Any) -> str:
    return inherited.canonical_sha256(value)


def _repo_path(relative: PurePosixPath) -> Path:
    return find_repo_root() / Path(*relative.parts)


def _strict_sha256(value: Any, *, label: str) -> str:
    return inherited._strict_sha256(value, label=label)


def _exact_keys(value: Any, expected: set[str], *, label: str) -> Mapping[str, Any]:
    return inherited._require_exact_keys(value, expected, label=label)


def _load_plan() -> dict[str, Any]:
    plan = inherited._load_hashed_json(
        _repo_path(PLAN_RELATIVE_PATH), PLAN_SHA256, label="iteration-006 plan"
    )
    top = _exact_keys(plan, _PLAN_TOP_KEYS, label="iteration-006 plan")
    if top["schema_version"] != PLAN_SCHEMA_VERSION or top["plan_id"] != PLAN_ID:
        raise ValueError("iteration-006 plan identity mismatch")
    if top["strength_claim_allowed"] is not False:
        raise ValueError("iteration-006 plan must forbid a strength claim")
    expected_training = {
        "gamma": 0.99,
        "gae_lambda": 0.95,
        "clip_ratio": 0.1,
        "value_coef": 0.0,
        "entropy_coef": 0.0,
        "anchor_kl_target": 0.0005,
        "anchor_kl_initial_coef": 0.1,
        "anchor_kl_hard_stop": 0.002,
        "gradient_clip": 0.25,
        "learning_rate": 0.0001,
        "epochs": 2,
        "optimizer_steps": 2,
    }
    if top["training_contract"]["ppo_config"] != expected_training:
        raise ValueError("iteration-006 PPO contract mismatch")
    if top["training_contract"]["optimizer"] != ADAM_CONFIG:
        raise ValueError("iteration-006 Adam contract mismatch")
    if top["sampled_action_family_contract"]["row_map_sha256"] != ROW_MAP_SHA256:
        raise ValueError("iteration-006 row-map contract mismatch")
    return dict(top)


def _load_correction() -> dict[str, Any]:
    correction = inherited._load_hashed_json(
        _repo_path(CORRECTION_RELATIVE_PATH),
        CORRECTION_SHA256,
        label="iteration-006 plan correction",
    )
    top = _exact_keys(
        correction,
        {
            "schema_version", "correction_id", "purpose", "base_plan",
            "corrections", "invariants", "execution_stop_rule",
        },
        label="iteration-006 plan correction",
    )
    if (
        top["schema_version"] != CORRECTION_SCHEMA_VERSION
        or top["correction_id"] != CORRECTION_ID
        or top["base_plan"] != {
            "path": PLAN_RELATIVE_PATH.as_posix(),
            "sha256": PLAN_SHA256,
            "plan_id": PLAN_ID,
        }
    ):
        raise ValueError("iteration-006 correction identity mismatch")
    corrections = _exact_keys(
        top["corrections"],
        {
            "anchor_kl_coefficient", "family_gate_staging",
            "global_gate_semantics", "value_loss_reporting",
        },
        label="iteration-006 correction fields",
    )
    anchor = corrections["anchor_kl_coefficient"]
    if (
        anchor.get("stage_1") != 0.1
        or anchor.get("stage_2") != 0.1
        or anchor.get("adaptive_adjustment_between_stages") is not False
    ):
        raise ValueError("fixed anchor-KL correction mismatch")
    required_value_fields = corrections["value_loss_reporting"].get("required_fields")
    if required_value_fields != [
        "raw_value_mse_initial", "raw_value_mse_stage_1", "raw_value_mse_stage_2",
        "weighted_value_loss_stage_1", "weighted_value_loss_stage_2",
    ]:
        raise ValueError("value diagnostic correction mismatch")
    return dict(top)


def _load_remediation() -> dict[str, Any]:
    remediation = inherited._load_hashed_json(
        _repo_path(REMEDIATION_RELATIVE_PATH),
        REMEDIATION_SHA256,
        label="iteration-006 prepare audit remediation",
    )
    top = _exact_keys(
        remediation,
        {
            "schema_version", "remediation_id", "purpose", "immutable_contracts",
            "blocked_prepare", "required_repairs", "required_tests",
            "replacement_prepare", "execution_stop_rule",
        },
        label="iteration-006 prepare audit remediation",
    )
    if (
        top["schema_version"] != REMEDIATION_SCHEMA_VERSION
        or top["remediation_id"] != REMEDIATION_ID
        or top["immutable_contracts"] != {
            "base_plan": {
                "path": PLAN_RELATIVE_PATH.as_posix(), "sha256": PLAN_SHA256,
            },
            "plan_correction": {
                "path": CORRECTION_RELATIVE_PATH.as_posix(),
                "sha256": CORRECTION_SHA256,
            },
        }
    ):
        raise ValueError("iteration-006 remediation identity mismatch")
    blocked = top["blocked_prepare"]
    if (
        blocked.get("implementation_path") != IMPLEMENTATION_RELATIVE_PATH.as_posix()
        or blocked.get("implementation_file_count") != 51
        or blocked.get("implementation_snapshot_sha256")
        != "EC02811118D76CC3CBB2AB2A9429F63028A32B713045946C5B581461D0B03283"
        or blocked.get("receipt_file_sha256")
        != "E7B9145B9AFE843E41EF0598468D898DD8ACEB9A732583D6E3C818F466748A94"
        or blocked.get("receipt_sha256")
        != "B43FA5917CB6416CCEF051F80DB09EE9465EB25898A1E04BB1E84EACFE606354"
        or blocked.get("execution_authorized") is not False
    ):
        raise ValueError("iteration-006 blocked prepare identity mismatch")
    replacement = top["replacement_prepare"]
    if (
        replacement.get("output_path")
        != (
            IMPLEMENTATION_RELATIVE_PATH
            / "test_outputs/phase1_iteration_006_prepare_v2/pretraining_probe_receipt.json"
        ).as_posix()
        or replacement.get("must_bind_this_remediation_path")
        != REMEDIATION_RELATIVE_PATH.as_posix()
        or replacement.get("optimizer_constructed") is not False
        or replacement.get("optimizer_steps") != 0
        or replacement.get("checkpoint_written") is not False
        or replacement.get("old_prepare_v1_remains_rejected_for_execution") is not True
    ):
        raise ValueError("iteration-006 replacement prepare contract mismatch")
    return dict(top)


def _load_remediation_correction() -> dict[str, Any]:
    correction = inherited._load_hashed_json(
        _repo_path(REMEDIATION_CORRECTION_RELATIVE_PATH),
        REMEDIATION_CORRECTION_SHA256,
        label="iteration-006 prepare audit remediation correction",
    )
    top = _exact_keys(
        correction,
        {
            "schema_version", "correction_id", "purpose", "base_remediation",
            "blocked_prepare", "corrections", "required_tests",
            "replacement_prepare", "execution_stop_rule",
        },
        label="iteration-006 prepare audit remediation correction",
    )
    if (
        top["schema_version"] != REMEDIATION_CORRECTION_SCHEMA_VERSION
        or top["correction_id"] != REMEDIATION_CORRECTION_ID
        or top["base_remediation"] != {
            "path": REMEDIATION_RELATIVE_PATH.as_posix(),
            "sha256": REMEDIATION_SHA256,
            "remediation_id": REMEDIATION_ID,
        }
    ):
        raise ValueError("iteration-006 remediation correction identity mismatch")
    blocked = top["blocked_prepare"]
    if blocked != {
        "implementation_path": IMPLEMENTATION_RELATIVE_PATH.as_posix(),
        "implementation_file_count": 51,
        "implementation_snapshot_sha256": (
            "CECA81E4BA6B583F4811CC3C20BD5518693867D8834D3FAFC568209FF1EFEBE9"
        ),
        "receipt_path": (
            IMPLEMENTATION_RELATIVE_PATH
            / "test_outputs/phase1_iteration_006_prepare_v2/"
            "pretraining_probe_receipt.json"
        ).as_posix(),
        "receipt_file_sha256": (
            "A1D88A9CACB00ADDF4D5DB43DFC9AA2A69DABEB7CCA481B1747B2E0DF9866F00"
        ),
        "receipt_sha256": (
            "49BD1E0D2300CAAB995B42E2BD6EFAC238D4F12F84F3B1692DB9679F76ECED73"
        ),
        "numerical_provenance_audit": "PASS",
        "code_audit": "BLOCK",
        "execution_authorized": False,
    }:
        raise ValueError("iteration-006 blocked prepare v2 identity mismatch")
    repairs = _exact_keys(
        top["corrections"],
        {"rejected_optimizer_contract_evidence", "owned_hardlink_handoff"},
        label="iteration-006 remediation correction repairs",
    )
    optimizer_evidence = repairs["rejected_optimizer_contract_evidence"]
    if (
        optimizer_evidence.get("progress_authority")
        != (
            "optimizer_steps_completed is the count recorded immediately after "
            "successful optimizer.step returns. A malformed optimizer state must "
            "not rewrite that historical count."
        )
        or optimizer_evidence.get("receipt_fields")
        != [
            "optimizer_contract_pass", "optimizer_contract_failures",
            "optimizer_steps_expected", "optimizer_steps_observed",
            "optimizer_steps_completed",
        ]
    ):
        raise ValueError("iteration-006 optimizer evidence correction mismatch")
    handoff = repairs["owned_hardlink_handoff"]
    if handoff.get("single_checkpoint") is not True:
        raise ValueError("iteration-006 hardlink handoff correction mismatch")
    replacement = top["replacement_prepare"]
    if (
        replacement.get("output_path")
        != (
            IMPLEMENTATION_RELATIVE_PATH
            / "test_outputs/phase1_iteration_006_prepare_v3/"
            "pretraining_probe_receipt.json"
        ).as_posix()
        or replacement.get("must_bind_this_correction_path")
        != REMEDIATION_CORRECTION_RELATIVE_PATH.as_posix()
        or replacement.get("must_bind_the_exact_external_file_sha256") is not True
        or replacement.get("optimizer_constructed") is not False
        or replacement.get("optimizer_steps") != 0
        or replacement.get("checkpoint_written") is not False
        or replacement.get("old_prepare_v2_remains_rejected_for_execution") is not True
    ):
        raise ValueError("iteration-006 replacement prepare v3 contract mismatch")
    return dict(top)


def _validate_parent_rejection(plan: Mapping[str, Any]) -> dict[str, Any]:
    parent = plan["parent_result"]
    if parent != {
        "path": PARENT_RESULT_RELATIVE_PATH.as_posix(),
        "sha256": PARENT_RESULT_SHA256,
        "decision": "REJECT",
        "execution_spec_path": PARENT_EXECUTION_SPEC_RELATIVE_PATH.as_posix(),
        "execution_spec_sha256": PARENT_EXECUTION_SPEC_SHA256,
        "rejected_receipt_path": PARENT_REJECTED_RECEIPT_RELATIVE_PATH.as_posix(),
        "rejected_receipt_file_sha256": PARENT_REJECTED_RECEIPT_FILE_SHA256,
        "rejected_receipt_sha256": PARENT_REJECTED_RECEIPT_SHA256,
        "rejected_checkpoint_path": REJECTED_CHECKPOINT_RELATIVE_PATH.as_posix(),
        "rejected_checkpoint_sha256": REJECTED_CHECKPOINT_SHA256,
        "rejected_checkpoint_must_not_be_loaded": True,
        "runtime_smoke_skipped": True,
    }:
        raise ValueError("parent rejection plan fields mismatch")
    if sha256_file(_repo_path(PARENT_RESULT_RELATIVE_PATH)) != PARENT_RESULT_SHA256:
        raise ValueError("parent result hash mismatch")
    parent_spec = inherited._load_hashed_json(
        _repo_path(PARENT_EXECUTION_SPEC_RELATIVE_PATH),
        PARENT_EXECUTION_SPEC_SHA256,
        label="parent execution spec",
    )
    if parent_spec.get("schema_version") != inherited.EXECUTION_SPEC_SCHEMA_VERSION:
        raise ValueError("parent execution spec schema mismatch")
    rejected = inherited._load_hashed_json(
        _repo_path(PARENT_REJECTED_RECEIPT_RELATIVE_PATH),
        PARENT_REJECTED_RECEIPT_FILE_SHA256,
        label="parent rejected receipt",
    )
    rejected_core = dict(rejected)
    rejected_self = _strict_sha256(
        rejected_core.pop("receipt_sha256", None), label="parent receipt self-hash"
    )
    if canonical_sha256(rejected_core) != rejected_self:
        raise ValueError("parent rejected receipt self-hash mismatch")
    if (
        rejected_self != PARENT_REJECTED_RECEIPT_SHA256
        or rejected.get("status") != "rejected"
        or rejected.get("input_checkpoint_sha256") != INPUT_CHECKPOINT_SHA256
        or rejected.get("output_checkpoint_sha256") != REJECTED_CHECKPOINT_SHA256
    ):
        raise ValueError("parent rejection evidence mismatch")
    rejected_path = _repo_path(REJECTED_CHECKPOINT_RELATIVE_PATH)
    if sha256_file(rejected_path) != REJECTED_CHECKPOINT_SHA256:
        raise ValueError("parent rejected checkpoint hash mismatch")
    input_path = _repo_path(INPUT_CHECKPOINT_RELATIVE_PATH).resolve(strict=True)
    if (
        input_path == rejected_path.resolve(strict=True)
        or INPUT_CHECKPOINT_SHA256 == REJECTED_CHECKPOINT_SHA256
    ):
        raise ValueError("rejected checkpoint selected as the iteration-006 input")
    return {
        "result_path": PARENT_RESULT_RELATIVE_PATH.as_posix(),
        "result_sha256": PARENT_RESULT_SHA256,
        "decision": "REJECT",
        "execution_spec_path": PARENT_EXECUTION_SPEC_RELATIVE_PATH.as_posix(),
        "execution_spec_sha256": PARENT_EXECUTION_SPEC_SHA256,
        "rejected_receipt_path": PARENT_REJECTED_RECEIPT_RELATIVE_PATH.as_posix(),
        "rejected_receipt_file_sha256": PARENT_REJECTED_RECEIPT_FILE_SHA256,
        "rejected_receipt_sha256": rejected_self,
        "rejected_checkpoint_path": REJECTED_CHECKPOINT_RELATIVE_PATH.as_posix(),
        "rejected_checkpoint_sha256": REJECTED_CHECKPOINT_SHA256,
        "rejected_checkpoint_loaded": False,
    }


def _validate_source_implementation(plan: Mapping[str, Any]) -> dict[str, Any]:
    source = plan["immutable_inputs"]["source_implementation"]
    expected = {
        "path": SOURCE_IMPLEMENTATION_RELATIVE_PATH.as_posix(),
        "snapshot_definition": inherited.STRICT_IMPLEMENTATION_SNAPSHOT_DEFINITION,
        "file_count": SOURCE_IMPLEMENTATION_FILE_COUNT,
        "snapshot_sha256": SOURCE_IMPLEMENTATION_SHA256,
        "conservative_ppo_pilot_py_sha256": SOURCE_CONSERVATIVE_PILOT_SHA256,
        "model_py_sha256": SOURCE_MODEL_SHA256,
    }
    if source != expected:
        raise ValueError("source implementation plan fields mismatch")
    root = _repo_path(SOURCE_IMPLEMENTATION_RELATIVE_PATH)
    snapshot = inherited.implementation_snapshot(root)
    if snapshot["file_count"] != SOURCE_IMPLEMENTATION_FILE_COUNT:
        raise ValueError("source implementation file count mismatch")
    if snapshot["sha256"] != SOURCE_IMPLEMENTATION_SHA256:
        raise ValueError("source implementation snapshot mismatch")
    if snapshot["definition"] != inherited.STRICT_IMPLEMENTATION_SNAPSHOT_DEFINITION:
        raise ValueError("source implementation snapshot definition mismatch")
    critical = {
        "archaludon_rl/conservative_ppo_pilot.py": SOURCE_CONSERVATIVE_PILOT_SHA256,
        "archaludon_rl/model.py": SOURCE_MODEL_SHA256,
    }
    for relative, expected_hash in critical.items():
        if sha256_file(root / Path(relative)) != expected_hash:
            raise ValueError(f"source implementation critical hash mismatch: {relative}")
    return {
        "path": SOURCE_IMPLEMENTATION_RELATIVE_PATH.as_posix(),
        **snapshot,
        "critical_files": critical,
    }


def _load_and_reproduce_v4_probe(runtime: Mapping[str, Any]) -> dict[str, Any]:
    pinned = inherited._load_hashed_json(
        _repo_path(V4_PROBE_RELATIVE_PATH),
        V4_PROBE_FILE_SHA256,
        label="iteration-005 v4 probe",
    )
    inherited.validate_prepare_receipt(pinned)
    if pinned["receipt_sha256"] != V4_PROBE_RECEIPT_SHA256:
        raise ValueError("iteration-005 v4 probe self-hash mismatch")
    rebuilt = inherited._build_probe_receipt(runtime)
    pinned_comparable = copy.deepcopy(pinned)
    rebuilt_comparable = copy.deepcopy(rebuilt)
    for value in (pinned_comparable, rebuilt_comparable):
        value.pop("implementation", None)
        value.pop("receipt_sha256", None)
    if rebuilt_comparable != pinned_comparable:
        raise ValueError("iteration-005 v4 rows or probes were not reproduced exactly")
    return dict(pinned)


def _tensor_bytes(tensor: torch.Tensor) -> bytes:
    value = tensor.detach().cpu().contiguous()
    if value.ndim == 0:
        value = value.reshape(1)
    return value.view(torch.uint8).numpy().tobytes(order="C")


def _tensor_sha256(tensor: torch.Tensor) -> str:
    return hashlib.sha256(_tensor_bytes(tensor)).hexdigest().upper()


def _nested_byte_exact(left: Any, right: Any) -> bool:
    if torch.is_tensor(left) or torch.is_tensor(right):
        return bool(
            torch.is_tensor(left)
            and torch.is_tensor(right)
            and left.dtype == right.dtype
            and left.shape == right.shape
            and _tensor_bytes(left) == _tensor_bytes(right)
        )
    if isinstance(left, Mapping) or isinstance(right, Mapping):
        return bool(
            isinstance(left, Mapping)
            and isinstance(right, Mapping)
            and set(left) == set(right)
            and all(_nested_byte_exact(left[key], right[key]) for key in left)
        )
    if isinstance(left, (list, tuple)) or isinstance(right, (list, tuple)):
        return bool(
            isinstance(left, (list, tuple))
            and isinstance(right, (list, tuple))
            and len(left) == len(right)
            and all(_nested_byte_exact(a, b) for a, b in zip(left, right))
        )
    if isinstance(left, float) and isinstance(right, float) and math.isnan(left) and math.isnan(right):
        return True
    return left == right


def _nested_nonfinite_count(value: Any) -> int:
    if torch.is_tensor(value):
        if value.is_floating_point() or value.is_complex():
            return int((~torch.isfinite(value.detach().cpu())).sum().item())
        return 0
    if isinstance(value, Mapping):
        return sum(_nested_nonfinite_count(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_nested_nonfinite_count(item) for item in value)
    if isinstance(value, float):
        return 0 if math.isfinite(value) else 1
    return 0


def _parameter_records(model: torch.nn.Module) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    names = tuple(name for name, _ in model.named_parameters())
    if names != (*EXPECTED_ACTOR_NAMES, *EXPECTED_VALUE_NAMES):
        raise ValueError("initial model parameter names mismatch")
    for name, parameter in model.named_parameters():
        payload = _tensor_bytes(parameter)
        records.append(
            {
                "name": name,
                "dtype": str(parameter.dtype),
                "shape": list(parameter.shape),
                "numel": parameter.numel(),
                "byte_count": len(payload),
                "byte_sha256": hashlib.sha256(payload).hexdigest().upper(),
                "stage_1_trainable": name in STAGE1_TRAINABLE_NAMES,
                "stage_2_trainable": name in EXPECTED_ACTOR_NAMES,
                "optimizer_parameter_universe": name in EXPECTED_ACTOR_NAMES,
            }
        )
    return records


def _build_family_receipt(
    plan: Mapping[str, Any],
    loaded_rows: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
    probe_rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    row_map: list[dict[str, Any]] = []
    memberships: dict[int, list[int]] = {}
    positive: dict[int, list[int]] = {}
    negative: dict[int, list[int]] = {}
    training_rows: list[dict[str, Any]] = []
    if len(loaded_rows) != EXPECTED_ON_POLICY_ROWS or len(probe_rows) != len(loaded_rows):
        raise ValueError("family construction row count mismatch")
    for ordinal, ((episode, row), probe) in enumerate(zip(loaded_rows, probe_rows)):
        if probe["ppo_row_ordinal"] != ordinal:
            raise ValueError("probe row ordinal mismatch")
        sampled_index = int(row["final_action"][0])
        if sampled_index != int(probe["sampled_index"]):
            raise ValueError("sampled index mismatch")
        semantic = row["legal_semantic_options"][sampled_index]
        if set(semantic) != {"engine_index", "identity", "payload"}:
            raise ValueError("sampled semantic option schema mismatch")
        payload = semantic["payload"]
        if not isinstance(payload, Mapping) or "option_type" not in payload:
            raise ValueError("sampled semantic option type missing")
        option_type = int(payload["option_type"])
        identity = str(semantic["identity"])
        normalized = float(probe["trainer_normalized_advantage_float32"])
        if not math.isfinite(normalized) or normalized == 0.0:
            raise ValueError("family row has zero or non-finite normalized advantage")
        row_map.append(
            {
                "ppo_row_ordinal": ordinal,
                "sampled_index": sampled_index,
                "option_type": option_type,
                "semantic_identity": identity,
                "trainer_normalized_advantage_float32": normalized,
            }
        )
        memberships.setdefault(option_type, []).append(ordinal)
        (positive if normalized > 0.0 else negative).setdefault(option_type, []).append(ordinal)
        training_rows.append(
            {
                "ppo_row_ordinal": ordinal,
                "episode_id": str(episode["episode_id"]),
                "decision_index": int(row["decision_index"]),
                "raw_observation_sha256": str(row["raw_observation_sha256"]),
                "public_state_sha256": str(probe["public_state_sha256"]),
                "behavior_action_order_sha256": str(probe["behavior_action_order_sha256"]),
                "teacher_index": int(row["teacher_action"][0]),
                "sampled_index": sampled_index,
                "sampled_semantic_identity": identity,
                "sampled_option_type": option_type,
                "end_index": int(probe["end_index"]),
                "legal_option_count": int(row["legal_option_count"]),
                "behavior_logprob_float64": float(row["behavior_logprob"]),
                "raw_advantage_float64": float(probe["raw_advantage"]),
                "fixed_value_target_float64": float(probe["value_target"]),
                "fixed_normalized_advantage_float32": normalized,
                "initial_probabilities_float32": list(probe["pre_update_probabilities_float32"]),
                "initial_value_float32": float(probe["pre_update_value_float32"]),
            }
        )
    row_map_value = {"schema_version": ROW_MAP_SCHEMA_VERSION, "rows": row_map}
    row_map_hash = canonical_sha256(row_map_value)
    if row_map_hash != ROW_MAP_SHA256:
        raise ValueError("sampled option-type row-map hash mismatch")
    family_contract = plan["sampled_action_family_contract"]
    expected_families = family_contract["families"]
    family_rows: list[dict[str, Any]] = []
    for expected in expected_families:
        option_type = int(expected["option_type"])
        ordinals = memberships.get(option_type, [])
        membership_value = {
            "schema_version": MEMBERSHIP_SCHEMA_VERSION,
            "option_type": option_type,
            "ppo_row_ordinals": sorted(ordinals),
        }
        membership_hash = canonical_sha256(membership_value)
        positives = positive.get(option_type, [])
        negatives = negative.get(option_type, [])
        reproduced = {
            "option_type": option_type,
            "name": expected["name"],
            "rows": len(ordinals),
            "normalized_positive": len(positives),
            "normalized_negative": len(negatives),
            "membership_sha256": membership_hash,
            "qualifying": len(positives) >= 5 and len(negatives) >= 5,
        }
        if reproduced != expected:
            raise ValueError(f"sampled option-type family mismatch: {option_type}")
        family_rows.append(
            {
                **reproduced,
                "ppo_row_ordinals": sorted(ordinals),
                "positive_ordinals": sorted(positives),
                "negative_ordinals": sorted(negatives),
            }
        )
    if sorted(memberships) != [7, 8, 9, 10, 12, 13, 14]:
        raise ValueError("sampled option-type family universe mismatch")
    qualifying = [row["option_type"] for row in family_rows if row["qualifying"]]
    if qualifying != [7, 8, 9, 12, 13, 14]:
        raise ValueError("qualifying family universe mismatch")
    return (
        {
            "schema_version": family_contract["schema_version"],
            "family_definition": family_contract["family_definition"],
            "row_map_definition": family_contract["row_map_definition"],
            "row_map_sha256": row_map_hash,
            "membership_hash_definition": family_contract["membership_hash_definition"],
            "qualifying_rule": family_contract["qualifying_rule"],
            "gate_definition": copy.deepcopy(family_contract["gate_definition"]),
            "qualifying_option_types": qualifying,
            "families": family_rows,
        },
        training_rows,
    )


def _build_prepare_receipt(runtime: Mapping[str, Any]) -> dict[str, Any]:
    plan = _load_plan()
    correction = _load_correction()
    remediation = _load_remediation()
    remediation_correction = _load_remediation_correction()
    parent = _validate_parent_rejection(plan)
    source = _validate_source_implementation(plan)
    immutable = plan["immutable_inputs"]
    if immutable["input_checkpoint"] != {
        "path": INPUT_CHECKPOINT_RELATIVE_PATH.as_posix(),
        "sha256": INPUT_CHECKPOINT_SHA256,
        "optimizer_state_must_be_none": True,
    }:
        raise ValueError("input checkpoint plan fields mismatch")
    if immutable["manifest"] != {
        "path": MANIFEST_RELATIVE_PATH.as_posix(),
        "sha256": MANIFEST_SHA256,
    }:
        raise ValueError("manifest plan fields mismatch")
    if (
        immutable["dataset_sha256"] != DATASET_SHA256
        or immutable["on_policy_rows"] != EXPECTED_ON_POLICY_ROWS
        or immutable["behavior_policy_schema_sha256"] != BEHAVIOR_POLICY_SCHEMA_SHA256
    ):
        raise ValueError("immutable dataset plan fields mismatch")
    probe_plan = immutable["pretraining_probe"]
    if probe_plan != {
        "path": V4_PROBE_RELATIVE_PATH.as_posix(),
        "file_sha256": V4_PROBE_FILE_SHA256,
        "receipt_sha256": V4_PROBE_RECEIPT_SHA256,
    }:
        raise ValueError("v4 probe plan fields mismatch")
    pinned_probe = _load_and_reproduce_v4_probe(runtime)
    loaded = inherited._load_validated_inputs()
    if loaded["checkpoint_path"].resolve(strict=True) == _repo_path(
        REJECTED_CHECKPOINT_RELATIVE_PATH
    ).resolve(strict=True):
        raise ValueError("rejected checkpoint was loaded")
    if len(loaded["rows"]) != EXPECTED_ON_POLICY_ROWS:
        raise ValueError("loaded PPO row count mismatch")
    families, training_rows = _build_family_receipt(
        plan, loaded["rows"], pinned_probe["rows"]
    )
    parameters = _parameter_records(loaded["model"])
    before_hashes = {row["name"]: row["byte_sha256"] for row in parameters}
    after_hashes = {
        name: _tensor_sha256(parameter)
        for name, parameter in loaded["model"].named_parameters()
    }
    if before_hashes != after_hashes:
        raise ValueError("prepare changed initial model parameters")
    memberships = pinned_probe["probe_memberships"]
    directional = {
        "negative_target_ordinals": list(memberships["negative_target_ordinals"]),
        "positive_normalized_teacher_and_sampled_end_ordinals": list(
            memberships["positive_normalized_advantage_sampled_end_ordinals"]
        ),
        "positive_raw_teacher_and_sampled_end_ordinals": list(
            memberships["positive_raw_advantage_sampled_end_ordinals"]
        ),
        "teacher_end_ordinals": list(memberships["teacher_end_ordinals"]),
        "teacher_end_and_sampled_end_ordinals": list(
            memberships["teacher_end_and_sampled_end_ordinals"]
        ),
    }
    if [len(directional[name]) for name in (
        "negative_target_ordinals",
        "positive_normalized_teacher_and_sampled_end_ordinals",
        "positive_raw_teacher_and_sampled_end_ordinals",
        "teacher_end_ordinals",
    )] != [4, 20, 31, 43]:
        raise ValueError("inherited directional membership counts mismatch")
    snapshot = inherited.implementation_snapshot(_repo_path(IMPLEMENTATION_RELATIVE_PATH))
    core = {
        "schema_version": PREPARE_RECEIPT_SCHEMA_VERSION,
        "plan": {
            "path": PLAN_RELATIVE_PATH.as_posix(),
            "file_sha256": PLAN_SHA256,
            "canonical_sha256": canonical_sha256(plan),
            "schema_version": PLAN_SCHEMA_VERSION,
            "plan_id": PLAN_ID,
        },
        "plan_correction": {
            "path": CORRECTION_RELATIVE_PATH.as_posix(),
            "file_sha256": CORRECTION_SHA256,
            "canonical_sha256": canonical_sha256(correction),
            "schema_version": CORRECTION_SCHEMA_VERSION,
            "correction_id": CORRECTION_ID,
            "corrections": copy.deepcopy(correction["corrections"]),
        },
        "prepare_audit_remediation": {
            "path": REMEDIATION_RELATIVE_PATH.as_posix(),
            "file_sha256": REMEDIATION_SHA256,
            "canonical_sha256": canonical_sha256(remediation),
            "schema_version": REMEDIATION_SCHEMA_VERSION,
            "remediation_id": REMEDIATION_ID,
            "required_repairs": copy.deepcopy(remediation["required_repairs"]),
            "blocked_prepare": copy.deepcopy(remediation["blocked_prepare"]),
        },
        "prepare_audit_remediation_correction": {
            "path": REMEDIATION_CORRECTION_RELATIVE_PATH.as_posix(),
            "file_sha256": REMEDIATION_CORRECTION_SHA256,
            "canonical_sha256": canonical_sha256(remediation_correction),
            "schema_version": REMEDIATION_CORRECTION_SCHEMA_VERSION,
            "correction_id": REMEDIATION_CORRECTION_ID,
            "base_remediation": copy.deepcopy(
                remediation_correction["base_remediation"]
            ),
            "blocked_prepare": copy.deepcopy(
                remediation_correction["blocked_prepare"]
            ),
            "corrections": copy.deepcopy(remediation_correction["corrections"]),
        },
        "parent_rejection": parent,
        "source_implementation": source,
        "implementation": {
            "path": IMPLEMENTATION_RELATIVE_PATH.as_posix(),
            **snapshot,
        },
        "runtime_thread_receipt": dict(runtime),
        "immutable_inputs": {
            "input_checkpoint_path": INPUT_CHECKPOINT_RELATIVE_PATH.as_posix(),
            "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
            "input_optimizer_state_is_none": True,
            "rejected_checkpoint_sha256": REJECTED_CHECKPOINT_SHA256,
            "rejected_checkpoint_loaded": False,
            "manifest_path": MANIFEST_RELATIVE_PATH.as_posix(),
            "manifest_sha256": MANIFEST_SHA256,
            "dataset_sha256": DATASET_SHA256,
            "behavior_policy_schema_sha256": BEHAVIOR_POLICY_SCHEMA_SHA256,
            "v4_probe_path": V4_PROBE_RELATIVE_PATH.as_posix(),
            "v4_probe_file_sha256": V4_PROBE_FILE_SHA256,
            "v4_probe_receipt_sha256": V4_PROBE_RECEIPT_SHA256,
            "v4_probe_exact_reproduction": True,
        },
        "training_contract": copy.deepcopy(plan["training_contract"]),
        "row_count": len(training_rows),
        "unique_decision_key_count": len(
            {(row["episode_id"], row["decision_index"]) for row in training_rows}
        ),
        "ordered_training_rows_sha256": canonical_sha256(training_rows),
        "rows": training_rows,
        "action_families": families,
        "directional_memberships": directional,
        "directional_gate_contract": copy.deepcopy(plan["inherited_directional_gates"]),
        "global_gate_contract": copy.deepcopy(plan["global_stage_gates"]),
        "model_parameters": {
            "records": parameters,
            "records_sha256": canonical_sha256(parameters),
            "actor_parameter_names": list(EXPECTED_ACTOR_NAMES),
            "value_head_parameter_names": list(EXPECTED_VALUE_NAMES),
            "stage_1_trainable_names": list(STAGE1_TRAINABLE_NAMES),
            "stage_2_trainable_names": list(EXPECTED_ACTOR_NAMES),
            "value_head_baseline_sha256": canonical_sha256(
                [row for row in parameters if row["name"].startswith(VALUE_PREFIX)]
            ),
        },
        "prepare_proof": {
            "optimizer_constructed": False,
            "optimizer_steps": 0,
            "checkpoint_written": False,
            "parameters_changed": False,
            "rejected_checkpoint_loaded": False,
        },
    }
    return {**core, "receipt_sha256": canonical_sha256(core)}


_PREPARE_RECEIPT_KEYS = {
    "schema_version", "plan", "plan_correction", "prepare_audit_remediation",
    "prepare_audit_remediation_correction",
    "parent_rejection", "source_implementation",
    "implementation", "runtime_thread_receipt", "immutable_inputs",
    "training_contract", "row_count", "unique_decision_key_count",
    "ordered_training_rows_sha256", "rows", "action_families",
    "directional_memberships", "directional_gate_contract",
    "global_gate_contract", "model_parameters", "prepare_proof", "receipt_sha256",
}


def validate_prepare_receipt(receipt: Mapping[str, Any]) -> None:
    row = dict(_exact_keys(receipt, _PREPARE_RECEIPT_KEYS, label="prepare receipt"))
    receipt_hash = _strict_sha256(
        row.pop("receipt_sha256", None), label="prepare receipt self-hash"
    )
    if row["schema_version"] != PREPARE_RECEIPT_SCHEMA_VERSION:
        raise ValueError("prepare receipt schema mismatch")
    if canonical_sha256(row) != receipt_hash:
        raise ValueError("prepare receipt self-hash mismatch")
    plan = _load_plan()
    plan_correction = _load_correction()
    remediation = _load_remediation()
    remediation_correction = _load_remediation_correction()
    expected_plan = {
        "path": PLAN_RELATIVE_PATH.as_posix(),
        "file_sha256": PLAN_SHA256,
        "canonical_sha256": canonical_sha256(plan),
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_id": PLAN_ID,
    }
    if row["plan"] != expected_plan:
        raise ValueError("prepare receipt base-plan binding mismatch")
    expected_correction = {
        "path": CORRECTION_RELATIVE_PATH.as_posix(),
        "file_sha256": CORRECTION_SHA256,
        "canonical_sha256": canonical_sha256(plan_correction),
        "schema_version": CORRECTION_SCHEMA_VERSION,
        "correction_id": CORRECTION_ID,
        "corrections": plan_correction["corrections"],
    }
    if row["plan_correction"] != expected_correction:
        raise ValueError("prepare receipt correction binding mismatch")
    expected_remediation = {
        "path": REMEDIATION_RELATIVE_PATH.as_posix(),
        "file_sha256": REMEDIATION_SHA256,
        "canonical_sha256": canonical_sha256(remediation),
        "schema_version": REMEDIATION_SCHEMA_VERSION,
        "remediation_id": REMEDIATION_ID,
        "required_repairs": remediation["required_repairs"],
        "blocked_prepare": remediation["blocked_prepare"],
    }
    if row["prepare_audit_remediation"] != expected_remediation:
        raise ValueError("prepare receipt remediation binding mismatch")
    expected_remediation_correction = {
        "path": REMEDIATION_CORRECTION_RELATIVE_PATH.as_posix(),
        "file_sha256": REMEDIATION_CORRECTION_SHA256,
        "canonical_sha256": canonical_sha256(remediation_correction),
        "schema_version": REMEDIATION_CORRECTION_SCHEMA_VERSION,
        "correction_id": REMEDIATION_CORRECTION_ID,
        "base_remediation": remediation_correction["base_remediation"],
        "blocked_prepare": remediation_correction["blocked_prepare"],
        "corrections": remediation_correction["corrections"],
    }
    if (
        row["prepare_audit_remediation_correction"]
        != expected_remediation_correction
    ):
        raise ValueError("prepare receipt remediation correction binding mismatch")
    expected_parent = _validate_parent_rejection(plan)
    if row["parent_rejection"] != expected_parent:
        raise ValueError("prepare receipt parent rejection mismatch")
    expected_source = _validate_source_implementation(plan)
    if row["source_implementation"] != expected_source:
        raise ValueError("prepare receipt source implementation mismatch")
    current_implementation = inherited.implementation_snapshot(
        _repo_path(IMPLEMENTATION_RELATIVE_PATH)
    )
    if row["implementation"] != {
        "path": IMPLEMENTATION_RELATIVE_PATH.as_posix(),
        **current_implementation,
    }:
        raise ValueError("prepare receipt candidate implementation mismatch")
    expected_runtime = {
        "requested_thread_counts": {
            "torch_num_threads": 1, "torch_num_interop_threads": 1,
        },
        "observed_thread_counts": {
            "torch_num_threads": int(torch.get_num_threads()),
            "torch_num_interop_threads": int(torch.get_num_interop_threads()),
        },
        "required_environment": dict(inherited.REQUIRED_THREAD_ENVIRONMENT),
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "torch_version": str(torch.__version__),
        "platform": platform.platform(),
    }
    if (
        expected_runtime["observed_thread_counts"]
        != expected_runtime["requested_thread_counts"]
        or {name: os.environ.get(name) for name in inherited.REQUIRED_THREAD_ENVIRONMENT}
        != inherited.REQUIRED_THREAD_ENVIRONMENT
        or row["runtime_thread_receipt"] != expected_runtime
    ):
        raise ValueError("prepare receipt runtime identity mismatch")
    expected_inputs = {
        "input_checkpoint_path": INPUT_CHECKPOINT_RELATIVE_PATH.as_posix(),
        "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
        "input_optimizer_state_is_none": True,
        "rejected_checkpoint_sha256": REJECTED_CHECKPOINT_SHA256,
        "rejected_checkpoint_loaded": False,
        "manifest_path": MANIFEST_RELATIVE_PATH.as_posix(),
        "manifest_sha256": MANIFEST_SHA256,
        "dataset_sha256": DATASET_SHA256,
        "behavior_policy_schema_sha256": BEHAVIOR_POLICY_SCHEMA_SHA256,
        "v4_probe_path": V4_PROBE_RELATIVE_PATH.as_posix(),
        "v4_probe_file_sha256": V4_PROBE_FILE_SHA256,
        "v4_probe_receipt_sha256": V4_PROBE_RECEIPT_SHA256,
        "v4_probe_exact_reproduction": True,
    }
    if row["immutable_inputs"] != expected_inputs:
        raise ValueError("prepare receipt immutable inputs mismatch")
    if (
        sha256_file(_repo_path(INPUT_CHECKPOINT_RELATIVE_PATH)) != INPUT_CHECKPOINT_SHA256
        or sha256_file(_repo_path(MANIFEST_RELATIVE_PATH)) != MANIFEST_SHA256
        or sha256_file(_repo_path(V4_PROBE_RELATIVE_PATH)) != V4_PROBE_FILE_SHA256
    ):
        raise ValueError("prepare receipt immutable input file changed")
    if row["training_contract"] != plan["training_contract"]:
        raise ValueError("prepare receipt training contract mismatch")
    if row["directional_gate_contract"] != plan["inherited_directional_gates"]:
        raise ValueError("prepare receipt directional gate contract mismatch")
    if row["global_gate_contract"] != plan["global_stage_gates"]:
        raise ValueError("prepare receipt global gate contract mismatch")
    rows = row["rows"]
    if (
        row["row_count"] != EXPECTED_ON_POLICY_ROWS
        or row["unique_decision_key_count"] != EXPECTED_ON_POLICY_ROWS
        or not isinstance(rows, list)
        or len(rows) != EXPECTED_ON_POLICY_ROWS
    ):
        raise ValueError("prepare receipt row count mismatch")
    if [item.get("ppo_row_ordinal") for item in rows] != list(range(EXPECTED_ON_POLICY_ROWS)):
        raise ValueError("prepare receipt row order mismatch")
    if canonical_sha256(rows) != row["ordered_training_rows_sha256"]:
        raise ValueError("prepare receipt ordered-row hash mismatch")
    row_keys = {
        "ppo_row_ordinal", "episode_id", "decision_index", "raw_observation_sha256",
        "public_state_sha256", "behavior_action_order_sha256", "teacher_index",
        "sampled_index", "sampled_semantic_identity", "sampled_option_type",
        "end_index", "legal_option_count", "behavior_logprob_float64",
        "raw_advantage_float64", "fixed_value_target_float64",
        "fixed_normalized_advantage_float32", "initial_probabilities_float32",
        "initial_value_float32",
    }
    for ordinal, item in enumerate(rows):
        _exact_keys(item, row_keys, label=f"prepare training row {ordinal}")
        if item["ppo_row_ordinal"] != ordinal:
            raise ValueError("prepare training row ordinal mismatch")
        if (
            not isinstance(item["initial_probabilities_float32"], list)
            or len(item["initial_probabilities_float32"]) != item["legal_option_count"]
        ):
            raise ValueError("prepare training row probability dimension mismatch")
    proof = row["prepare_proof"]
    if proof != {
        "optimizer_constructed": False,
        "optimizer_steps": 0,
        "checkpoint_written": False,
        "parameters_changed": False,
        "rejected_checkpoint_loaded": False,
    }:
        raise ValueError("prepare receipt no-training proof mismatch")
    families = row["action_families"]
    _exact_keys(
        families,
        {
            "schema_version", "family_definition", "row_map_definition",
            "row_map_sha256", "membership_hash_definition", "qualifying_rule",
            "gate_definition", "qualifying_option_types", "families",
        },
        label="prepare action-family receipt",
    )
    if families.get("row_map_sha256") != ROW_MAP_SHA256:
        raise ValueError("prepare receipt row-map hash mismatch")
    family_rows = families.get("families", [])
    if [item.get("option_type") for item in family_rows] != [7, 8, 9, 10, 12, 13, 14]:
        raise ValueError("prepare receipt family schema mismatch")
    row_map = {
        "schema_version": ROW_MAP_SCHEMA_VERSION,
        "rows": [
            {
                "ppo_row_ordinal": item["ppo_row_ordinal"],
                "sampled_index": item["sampled_index"],
                "option_type": item["sampled_option_type"],
                "semantic_identity": item["sampled_semantic_identity"],
                "trainer_normalized_advantage_float32": item[
                    "fixed_normalized_advantage_float32"
                ],
            }
            for item in rows
        ],
    }
    if canonical_sha256(row_map) != ROW_MAP_SHA256:
        raise ValueError("prepare receipt reconstructed row-map hash mismatch")
    family_keys = {
        "option_type", "name", "rows", "normalized_positive", "normalized_negative",
        "membership_sha256", "qualifying", "ppo_row_ordinals", "positive_ordinals",
        "negative_ordinals",
    }
    plan_families = plan["sampled_action_family_contract"]["families"]
    for family, expected in zip(family_rows, plan_families):
        _exact_keys(family, family_keys, label="prepare action family")
        ordinals = family["ppo_row_ordinals"]
        positives = family["positive_ordinals"]
        negatives = family["negative_ordinals"]
        membership_hash = canonical_sha256(
            {
                "schema_version": MEMBERSHIP_SCHEMA_VERSION,
                "option_type": family["option_type"],
                "ppo_row_ordinals": ordinals,
            }
        )
        summary = {
            name: family[name]
            for name in (
                "option_type", "name", "rows", "normalized_positive",
                "normalized_negative", "membership_sha256", "qualifying",
            )
        }
        if (
            summary != expected
            or membership_hash != family["membership_sha256"]
            or len(ordinals) != family["rows"]
            or len(positives) != family["normalized_positive"]
            or len(negatives) != family["normalized_negative"]
            or sorted((*positives, *negatives)) != ordinals
            or any(rows[index]["sampled_option_type"] != family["option_type"] for index in ordinals)
            or any(rows[index]["fixed_normalized_advantage_float32"] <= 0.0 for index in positives)
            or any(rows[index]["fixed_normalized_advantage_float32"] >= 0.0 for index in negatives)
        ):
            raise ValueError("prepare receipt action family membership mismatch")
    model_parameters = _exact_keys(
        row["model_parameters"],
        {
            "records", "records_sha256", "actor_parameter_names",
            "value_head_parameter_names", "stage_1_trainable_names",
            "stage_2_trainable_names", "value_head_baseline_sha256",
        },
        label="prepare model parameters",
    )
    parameter_records = model_parameters["records"]
    if model_parameters["records_sha256"] != canonical_sha256(parameter_records):
        raise ValueError("prepare receipt parameter-record hash mismatch")
    if [item.get("name") for item in parameter_records] != [
        *EXPECTED_ACTOR_NAMES, *EXPECTED_VALUE_NAMES
    ]:
        raise ValueError("prepare receipt parameter names mismatch")
    if (
        model_parameters["actor_parameter_names"] != list(EXPECTED_ACTOR_NAMES)
        or model_parameters["value_head_parameter_names"] != list(EXPECTED_VALUE_NAMES)
        or model_parameters["stage_1_trainable_names"] != list(STAGE1_TRAINABLE_NAMES)
        or model_parameters["stage_2_trainable_names"] != list(EXPECTED_ACTOR_NAMES)
    ):
        raise ValueError("prepare receipt parameter trainability mismatch")
    parameter_keys = {
        "name", "dtype", "shape", "numel", "byte_count", "byte_sha256",
        "stage_1_trainable", "stage_2_trainable", "optimizer_parameter_universe",
    }
    for item in parameter_records:
        _exact_keys(item, parameter_keys, label="prepare parameter record")
    directional = _exact_keys(
        row["directional_memberships"],
        {
            "negative_target_ordinals",
            "positive_normalized_teacher_and_sampled_end_ordinals",
            "positive_raw_teacher_and_sampled_end_ordinals",
            "teacher_end_ordinals", "teacher_end_and_sampled_end_ordinals",
        },
        label="prepare directional memberships",
    )
    if [len(directional.get(name, [])) for name in (
        "negative_target_ordinals",
        "positive_normalized_teacher_and_sampled_end_ordinals",
        "positive_raw_teacher_and_sampled_end_ordinals",
        "teacher_end_ordinals",
    )] != [4, 20, 31, 43]:
        raise ValueError("prepare receipt directional membership mismatch")
    pinned_v4 = inherited._load_hashed_json(
        _repo_path(V4_PROBE_RELATIVE_PATH), V4_PROBE_FILE_SHA256,
        label="prepare validation v4 probe",
    )
    expected_directional = {
        "negative_target_ordinals": pinned_v4["probe_memberships"]["negative_target_ordinals"],
        "positive_normalized_teacher_and_sampled_end_ordinals": pinned_v4[
            "probe_memberships"
        ]["positive_normalized_advantage_sampled_end_ordinals"],
        "positive_raw_teacher_and_sampled_end_ordinals": pinned_v4[
            "probe_memberships"
        ]["positive_raw_advantage_sampled_end_ordinals"],
        "teacher_end_ordinals": pinned_v4["probe_memberships"]["teacher_end_ordinals"],
        "teacher_end_and_sampled_end_ordinals": pinned_v4["probe_memberships"][
            "teacher_end_and_sampled_end_ordinals"
        ],
    }
    if dict(directional) != expected_directional:
        raise ValueError("prepare receipt directional ordinal set mismatch")


def _absolute_prepare_candidate(path: Path) -> Path:
    if ".." in path.parts or "." in path.parts:
        raise ValueError("prepare receipt path must not contain aliases")
    return (path if path.is_absolute() else Path.cwd() / path).absolute()


def _validate_prepare_output_path(path: Path, *, must_exist: bool = False) -> Path:
    candidate = _absolute_prepare_candidate(path)
    implementation_root = _repo_path(IMPLEMENTATION_RELATIVE_PATH).resolve(strict=True)
    approved_root = implementation_root / "test_outputs"
    try:
        lexical = candidate.relative_to(implementation_root)
    except ValueError as error:
        raise ValueError("prepare receipt must be inside candidate test_outputs") from error
    cursor = implementation_root
    for part in lexical.parts:
        cursor = cursor / part
        if cursor.exists() or cursor.is_symlink():
            if inherited._is_link_or_reparse(cursor):
                raise ValueError("prepare receipt path traverses a reparse point")
        else:
            break
    resolved = candidate.resolve(strict=False)
    try:
        relative = resolved.relative_to(approved_root)
    except ValueError as error:
        raise ValueError("prepare receipt must be inside candidate test_outputs") from error
    if (
        len(relative.parts) != 2
        or not (
            relative.parts[0] == PREPARE_OUTPUT_DIRECTORY_PREFIX
            or relative.parts[0].startswith(PREPARE_OUTPUT_DIRECTORY_PREFIX + "_")
        )
        or relative.name != PREPARE_OUTPUT_FILENAME
    ):
        raise ValueError("prepare receipt is outside the approved prepare subtree")
    if must_exist:
        if not resolved.is_file() or inherited._is_link_or_reparse(resolved):
            raise ValueError("prepare receipt must be an existing regular non-link file")
    elif resolved.exists() or resolved.is_symlink():
        raise FileExistsError("prepare receipt already exists")
    elif not resolved.parent.is_dir() or inherited._is_link_or_reparse(resolved.parent):
        raise ValueError("prepare receipt requires an existing regular parent")
    return resolved


def prepare(*, output_receipt: Path) -> dict[str, Any]:
    """Write one canonical no-training receipt using CREATE_NEW semantics."""

    output = _validate_prepare_output_path(output_receipt)
    guard = inherited._StableDirectoryGuard(output.parent)
    guard.__enter__()
    try:
        runtime = inherited._runtime_identity()
        receipt = _build_prepare_receipt(runtime)
        validate_prepare_receipt(receipt)
        file_hash = inherited._write_new_canonical_json(
            output, receipt, directory_guard=guard
        )
        return {
            "mode": "prepare",
            "receipt_path": str(output.absolute()),
            "receipt_file_sha256": file_hash,
            "receipt_sha256": receipt["receipt_sha256"],
            "row_count": receipt["row_count"],
            "optimizer_constructed": False,
            "checkpoint_written": False,
        }
    finally:
        guard.close()


def lower_empirical_median(values: Sequence[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered or any(not math.isfinite(value) for value in ordered):
        raise ValueError("lower empirical median requires finite nonempty values")
    return ordered[(len(ordered) - 1) // 2]


def orientation_class(value: float, *, tau: float = DEADBAND_TAU) -> str:
    value = float(value)
    if not math.isfinite(value) or not math.isfinite(tau) or tau < 0.0:
        raise ValueError("orientation classification requires finite values")
    if value > tau:
        return "aligned"
    if value < -tau:
        return "anti_aligned"
    return "neutral"


def alignment_summary(values: Sequence[float], *, tau: float = DEADBAND_TAU) -> dict[str, Any]:
    classes = [orientation_class(value, tau=tau) for value in values]
    aligned = classes.count("aligned")
    anti = classes.count("anti_aligned")
    neutral = classes.count("neutral")
    if not classes:
        raise ValueError("alignment summary requires at least one row")
    return {
        "row_count": len(classes),
        "aligned_count": aligned,
        "anti_aligned_count": anti,
        "neutral_count": neutral,
        "score": (aligned - anti) / len(classes),
        "lower_empirical_median": lower_empirical_median(values),
    }


def evaluate_stage2_improvement(
    stage_1: Mapping[str, Any], stage_2: Mapping[str, Any]
) -> dict[str, Any]:
    score_1 = float(stage_1["score"])
    score_2 = float(stage_2["score"])
    median_1 = float(stage_1["lower_empirical_median"])
    median_2 = float(stage_2["lower_empirical_median"])
    failures: list[str] = []
    if score_2 < score_1 - 0.01:
        failures.append("global_alignment_score")
    if median_2 <= median_1 + DEADBAND_TAU:
        failures.append("global_lower_median")
    return {
        "accepted": not failures,
        "failures": failures,
        "score_stage_1": score_1,
        "score_stage_2": score_2,
        "score_minimum": score_1 - 0.01,
        "median_stage_1": median_1,
        "median_stage_2": median_2,
        "median_strict_minimum": median_1 + DEADBAND_TAU,
    }


def _named_parameters(model: torch.nn.Module) -> dict[str, torch.nn.Parameter]:
    named = dict(model.named_parameters())
    if tuple(named) != (*EXPECTED_ACTOR_NAMES, *EXPECTED_VALUE_NAMES):
        raise ValueError("model parameter universe mismatch")
    return named


@dataclass
class ExecutionProgress:
    """Outer-handler-visible state; step count changes immediately after step return."""

    model: torch.nn.Module | None = None
    optimizer: torch.optim.Adam | None = None
    optimizer_steps_completed: int = 0
    stage_2_entered: bool = False
    failure_phase: str = "pre_step"


def _optimizer_step_and_record(
    optimizer: torch.optim.Adam, progress: ExecutionProgress, *, stage: int
) -> None:
    if stage not in (1, 2):
        raise ValueError("optimizer progress stage must be 1 or 2")
    if progress.optimizer_steps_completed != stage - 1:
        raise ValueError("optimizer progress ordinal mismatch before step")
    optimizer.step()
    # Remediation invariant: this is the first operation after successful return.
    progress.optimizer_steps_completed = stage


def _set_trainability(model: torch.nn.Module, *, stage: int) -> None:
    named = _named_parameters(model)
    trainable = set(STAGE1_TRAINABLE_NAMES if stage == 1 else EXPECTED_ACTOR_NAMES)
    for name, parameter in named.items():
        parameter.requires_grad_(name in trainable)
    actual = {name for name, parameter in named.items() if parameter.requires_grad}
    if actual != trainable:
        raise ValueError(f"stage-{stage} trainability mismatch")


def _new_actor_adam(model: torch.nn.Module) -> torch.optim.Adam:
    named = _named_parameters(model)
    optimizer = torch.optim.Adam(
        [named[name] for name in EXPECTED_ACTOR_NAMES],
        lr=TWO_STAGE_PPO_CONFIG.learning_rate,
        betas=(0.9, 0.999),
        eps=1e-8,
        weight_decay=0.0,
        amsgrad=False,
        foreach=None,
        maximize=False,
        capturable=False,
        differentiable=False,
        fused=None,
        decoupled_weight_decay=False,
    )
    if optimizer.state_dict()["state"]:
        raise ValueError("fresh actor Adam unexpectedly has state")
    if len(optimizer.param_groups) != 1:
        raise ValueError("actor Adam parameter-group mismatch")
    if tuple(id(value) for value in optimizer.param_groups[0]["params"]) != tuple(
        id(named[name]) for name in EXPECTED_ACTOR_NAMES
    ):
        raise ValueError("actor Adam parameter order mismatch")
    return optimizer


def _optimizer_step_states(
    optimizer: torch.optim.Adam, model: torch.nn.Module
) -> dict[str, int]:
    named = _named_parameters(model)
    reverse = {id(parameter): name for name, parameter in named.items()}
    result: dict[str, int] = {}
    for parameter, state in optimizer.state.items():
        name = reverse.get(id(parameter))
        if name is None or name.startswith(VALUE_PREFIX):
            raise ValueError("optimizer state contains an unapproved parameter")
        step = state.get("step")
        step_value = float(step.detach().cpu()) if torch.is_tensor(step) else float(step)
        if not step_value.is_integer():
            raise ValueError("optimizer step state is not integral")
        inherited._finite_tensors_or_raise(
            (value for value in state.values() if torch.is_tensor(value)),
            label="optimizer state",
        )
        result[name] = int(step_value)
    return result


def audit_optimizer_contract(
    optimizer: torch.optim.Adam, model: torch.nn.Module, *, stage: int
) -> dict[str, int]:
    """Validate the exact mixed Adam step state after a synthetic or real stage."""

    if stage not in (1, 2):
        raise ValueError("optimizer contract stage must be 1 or 2")
    steps = _optimizer_step_states(optimizer, model)
    expected = (
        {name: 1 for name in STAGE1_TRAINABLE_NAMES}
        if stage == 1
        else {
            name: (2 if name in STAGE1_TRAINABLE_NAMES else 1)
            for name in EXPECTED_ACTOR_NAMES
        }
    )
    if steps != expected:
        raise ValueError(f"stage-{stage} optimizer step-state mismatch")
    named = _named_parameters(model)
    if any(named[name] in optimizer.state for name in EXPECTED_VALUE_NAMES):
        raise ValueError("value head unexpectedly has optimizer state")
    return steps


def _parameter_hash_map(model: torch.nn.Module) -> dict[str, str]:
    return {name: _tensor_sha256(parameter) for name, parameter in model.named_parameters()}


def _parameter_diff_records(
    model: torch.nn.Module,
    before: Mapping[str, torch.Tensor],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    current = model.state_dict()
    for name in before:
        delta = current[name].detach().cpu() - before[name].detach().cpu()
        result.append(
            {
                "name": name,
                "before_byte_sha256": _tensor_sha256(before[name]),
                "after_byte_sha256": _tensor_sha256(current[name]),
                "changed": not torch.equal(before[name].cpu(), current[name].cpu()),
                "maximum_absolute_change": float(delta.abs().max()) if delta.numel() else 0.0,
            }
        )
    return result


def _stage_full_batch_step(
    *,
    stage: int,
    loaded: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    optimizer: torch.optim.Adam,
    initial_parameters: Mapping[str, torch.Tensor],
    progress: ExecutionProgress,
) -> dict[str, Any]:
    if stage not in (1, 2):
        raise ValueError("stage must be 1 or 2")
    model = loaded["model"]
    rows = loaded["rows"]
    fixed_rows = prepare_receipt["rows"]
    reference_config = loaded["reference_config"]
    _set_trainability(model, stage=stage)
    stage_before = {
        name: value.detach().clone() for name, value in model.state_dict().items()
    }
    value_before = {
        name: value.detach().clone()
        for name, value in model.state_dict().items()
        if name.startswith(VALUE_PREFIX)
    }
    optimizer.zero_grad(set_to_none=True)
    losses: list[torch.Tensor] = []
    policy_losses: list[torch.Tensor] = []
    anchor_kls: list[torch.Tensor] = []
    entropies: list[torch.Tensor] = []
    fixed_advantages: list[float] = []
    fixed_logprobs: list[float] = []
    for ordinal, ((episode, row), fixed) in enumerate(zip(rows, fixed_rows)):
        if (
            fixed["ppo_row_ordinal"] != ordinal
            or fixed["episode_id"] != str(episode["episode_id"])
            or fixed["decision_index"] != int(row["decision_index"])
            or fixed["sampled_index"] != int(row["final_action"][0])
        ):
            raise ValueError("fixed training row identity mismatch")
        normalized_value = float(fixed["fixed_normalized_advantage_float32"])
        old_logprob_value = float(fixed["behavior_logprob_float64"])
        fixed_advantages.append(normalized_value)
        fixed_logprobs.append(old_logprob_value)
        state = torch.tensor(row["state_vector"], dtype=torch.float32, device="cpu")
        actions = torch.tensor(row["action_vectors"], dtype=torch.float32, device="cpu")
        residuals, value = model(state, actions)
        probabilities, log_probabilities = _torch_behavior_distribution(
            residuals,
            teacher_index=int(row["teacher_action"][0]),
            reference_config=reference_config,
        )
        anchor_kl = _torch_behavior_anchor_kl(
            residuals,
            teacher_index=int(row["teacher_action"][0]),
            reference_config=reference_config,
        )
        selected = int(row["final_action"][0])
        old_logprob = torch.tensor(old_logprob_value, dtype=torch.float32)
        advantage = torch.tensor(normalized_value, dtype=torch.float32)
        ratio = torch.exp(log_probabilities[selected] - old_logprob)
        unclipped = ratio * advantage
        clipped = torch.clamp(
            ratio,
            1.0 - TWO_STAGE_PPO_CONFIG.clip_ratio,
            1.0 + TWO_STAGE_PPO_CONFIG.clip_ratio,
        ) * advantage
        policy_loss = -torch.minimum(unclipped, clipped)
        entropy = -(probabilities * log_probabilities).sum()
        loss = policy_loss + TWO_STAGE_PPO_CONFIG.anchor_kl_initial_coef * anchor_kl
        inherited._finite_tensors_or_raise(
            (residuals, value, probabilities, log_probabilities, anchor_kl, policy_loss, loss),
            label=f"stage-{stage} row-{ordinal}",
        )
        losses.append(loss)
        policy_losses.append(policy_loss)
        anchor_kls.append(anchor_kl)
        entropies.append(entropy)
    if len(losses) != EXPECTED_ON_POLICY_ROWS:
        raise ValueError("full batch did not contain exactly 830 rows")
    total_loss = torch.stack(losses).mean()
    total_loss.backward()
    named = _named_parameters(model)
    gradients = {
        name: parameter.grad
        for name, parameter in named.items()
        if parameter.grad is not None
    }
    expected_gradient_names = set(
        STAGE1_TRAINABLE_NAMES if stage == 1 else EXPECTED_ACTOR_NAMES
    )
    if set(gradients) != expected_gradient_names:
        raise ValueError(f"stage-{stage} gradient parameter set mismatch")
    inherited._finite_tensors_or_raise(gradients.values(), label=f"stage-{stage} gradient")
    gradient_before = {
        name: float(torch.linalg.vector_norm(value.detach()).cpu())
        for name, value in gradients.items()
    }
    gradient_norm = torch.nn.utils.clip_grad_norm_(
        [named[name] for name in EXPECTED_ACTOR_NAMES],
        TWO_STAGE_PPO_CONFIG.gradient_clip,
        error_if_nonfinite=True,
    )
    inherited._finite_tensors_or_raise((gradient_norm,), label=f"stage-{stage} gradient norm")
    gradient_after = {
        name: float(torch.linalg.vector_norm(value.detach()).cpu())
        for name, value in gradients.items()
    }
    _optimizer_step_and_record(optimizer, progress, stage=stage)
    inherited._finite_tensors_or_raise(model.parameters(), label=f"stage-{stage} parameter")
    if any(
        not torch.equal(value, model.state_dict()[name])
        for name, value in value_before.items()
    ):
        raise ValueError(f"stage-{stage} changed a value-head parameter")
    changed_from_stage_start = [
        name
        for name, value in stage_before.items()
        if not torch.equal(value, model.state_dict()[name])
    ]
    changed_from_initial = [
        name
        for name, value in initial_parameters.items()
        if not torch.equal(value, model.state_dict()[name])
    ]
    expected_initial = list(STAGE1_TRAINABLE_NAMES if stage == 1 else EXPECTED_ACTOR_NAMES)
    if changed_from_initial != expected_initial:
        raise ValueError(f"stage-{stage} changed-parameter contract mismatch")
    if stage == 1 and changed_from_stage_start != list(STAGE1_TRAINABLE_NAMES):
        raise ValueError("stage-1 changed-parameter set mismatch")
    optimizer_steps = audit_optimizer_contract(optimizer, model, stage=stage)
    return {
        "stage": stage,
        "optimizer_step_ordinal": stage,
        "optimizer_state_steps": optimizer_steps,
        "trainable_parameter_names": sorted(expected_gradient_names),
        "gradient_parameter_names": sorted(gradients),
        "gradient_norm_before_clipping": float(gradient_norm.detach().cpu()),
        "per_parameter_gradient_norm_before_clipping": gradient_before,
        "per_parameter_gradient_norm_after_clipping": gradient_after,
        "changed_parameter_names_from_stage_start": changed_from_stage_start,
        "changed_parameter_names_from_initial": changed_from_initial,
        "parameter_diffs_from_stage_start": _parameter_diff_records(model, stage_before),
        "parameter_diffs_from_initial": _parameter_diff_records(model, initial_parameters),
        "loss": float(total_loss.detach().cpu()),
        "policy_loss": float(torch.stack(policy_losses).mean().detach().cpu()),
        "value_loss": 0.0,
        "entropy": float(torch.stack(entropies).mean().detach().cpu()),
        "pre_step_mean_anchor_kl": float(torch.stack(anchor_kls).mean().detach().cpu()),
        "fixed_advantages_sha256": canonical_sha256(fixed_advantages),
        "fixed_behavior_logprobabilities_sha256": canonical_sha256(fixed_logprobs),
        "value_head_parameter_hashes": {
            name: _tensor_sha256(named[name]) for name in EXPECTED_VALUE_NAMES
        },
        "nonfinite_value_gradient_optimizer_or_parameter_count": 0,
    }


def _measure_stage(
    loaded: Mapping[str, Any], prepare_receipt: Mapping[str, Any], *, stage: int
) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    model = loaded["model"]
    reference_config = loaded["reference_config"]
    with torch.no_grad():
        for ordinal, ((_, row), fixed) in enumerate(zip(loaded["rows"], prepare_receipt["rows"])):
            state = torch.tensor(row["state_vector"], dtype=torch.float32)
            actions = torch.tensor(row["action_vectors"], dtype=torch.float32)
            residuals, value = model(state, actions)
            probabilities, _ = _torch_behavior_distribution(
                residuals,
                teacher_index=int(row["teacher_action"][0]),
                reference_config=reference_config,
            )
            anchor, _ = _torch_behavior_distribution(
                torch.zeros_like(residuals),
                teacher_index=int(row["teacher_action"][0]),
                reference_config=reference_config,
            )
            inherited._finite_tensors_or_raise(
                (residuals, value, probabilities, anchor), label=f"stage-{stage} measurement"
            )
            post = [float(item) for item in probabilities.detach().cpu().tolist()]
            initial = [float(item) for item in fixed["initial_probabilities_float32"]]
            sampled = int(fixed["sampled_index"])
            delta = post[sampled] - initial[sampled]
            normalized = float(fixed["fixed_normalized_advantage_float32"])
            oriented = (1.0 if normalized > 0.0 else -1.0) * delta
            maximum = max(post)
            winners = [index for index, item in enumerate(post) if item == maximum]
            metrics.append(
                {
                    "stage": stage,
                    "ppo_row_ordinal": ordinal,
                    "public_state_sha256": fixed["public_state_sha256"],
                    "behavior_action_order_sha256": fixed["behavior_action_order_sha256"],
                    "sampled_index": sampled,
                    "sampled_option_type": int(fixed["sampled_option_type"]),
                    "probabilities_float32": post,
                    "value_float32": float(value.detach().cpu()),
                    "unique_argmax_index": winners[0] if len(winners) == 1 else None,
                    "sampled_probability_delta_from_initial": delta,
                    "oriented_sampled_probability_delta": oriented,
                    "orientation": orientation_class(oriented),
                    "anchor_kl_post_to_zero": inherited.per_row_anchor_kl(
                        post, anchor.detach().cpu().tolist()
                    ),
                    "total_variation_from_initial": inherited.per_row_total_variation(post, initial),
                }
            )
    if len(metrics) != EXPECTED_ON_POLICY_ROWS:
        raise ValueError("stage measurement row count mismatch")
    return metrics


def _validated_metric_rows(
    prepare_receipt: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], list[str], int]:
    fixed_rows = prepare_receipt["rows"]
    values = [dict(item) for item in metrics]
    failures: list[str] = []
    nonfinite_count = 0
    if len(values) != EXPECTED_ON_POLICY_ROWS or len(fixed_rows) != EXPECTED_ON_POLICY_ROWS:
        return values, ["global:row_count"], 1
    for ordinal, (fixed, metric) in enumerate(zip(fixed_rows, values)):
        if metric.get("ppo_row_ordinal") != ordinal:
            failures.append(f"row:{ordinal}:order")
        probabilities = metric.get("probabilities_float32")
        if not isinstance(probabilities, list) or len(probabilities) != fixed["legal_option_count"]:
            failures.append(f"row:{ordinal}:probability_dimension")
            nonfinite_count += 1
            continue
        numeric = [
            *probabilities,
            metric.get("value_float32"),
            metric.get("anchor_kl_post_to_zero"),
            metric.get("total_variation_from_initial"),
            metric.get("oriented_sampled_probability_delta"),
        ]
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in numeric
        ):
            failures.append(f"row:{ordinal}:nonfinite")
            nonfinite_count += 1
            continue
        maximum = max(float(value) for value in probabilities)
        winners = [
            index for index, value in enumerate(probabilities)
            if float(value) == maximum
        ]
        if len(winners) != 1:
            failures.append(f"row:{ordinal}:unique_argmax")
        sampled = int(fixed["sampled_index"])
        delta = float(probabilities[sampled]) - float(
            fixed["initial_probabilities_float32"][sampled]
        )
        normalized = float(fixed["fixed_normalized_advantage_float32"])
        oriented = (1.0 if normalized > 0.0 else -1.0) * delta
        if float(metric["oriented_sampled_probability_delta"]) != oriented:
            failures.append(f"row:{ordinal}:oriented_delta")
    return values, failures, nonfinite_count


def _family_diagnostics(
    prepare_receipt: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for family in prepare_receipt["action_families"]["families"]:
        if not family["qualifying"]:
            continue
        polarity_rows = (
            ("positive", family["positive_ordinals"]),
            ("negative", family["negative_ordinals"]),
        )
        for polarity, ordinals in polarity_rows:
            values = [
                float(metrics[ordinal]["oriented_sampled_probability_delta"])
                for ordinal in ordinals
            ]
            summary = alignment_summary(values)
            passed = summary["lower_empirical_median"] > DEADBAND_TAU
            if not passed:
                failures.append(f"family:{family['option_type']}:{polarity}:median")
            results.append(
                {
                    "option_type": family["option_type"],
                    "name": family["name"],
                    "polarity": polarity,
                    "row_count": len(ordinals),
                    "lower_empirical_median": summary["lower_empirical_median"],
                    "aligned_count": summary["aligned_count"],
                    "anti_aligned_count": summary["anti_aligned_count"],
                    "neutral_count": summary["neutral_count"],
                    "strictly_greater_than_tau": passed,
                }
            )
    if len(results) != 12:
        raise ValueError("qualifying family/polarity diagnostic count mismatch")
    return {"groups": results, "failures": failures, "all_pass": not failures}


def evaluate_stage_gates(
    prepare_receipt: Mapping[str, Any],
    metrics: Sequence[Mapping[str, Any]],
    *,
    stage: int,
    training_nonfinite_count: int = 0,
) -> dict[str, Any]:
    """Apply corrected global gates; Stage-1 family results are diagnostic only."""

    if stage not in (1, 2):
        raise ValueError("gate stage must be 1 or 2")
    rows, failures, measured_nonfinite = _validated_metric_rows(
        prepare_receipt, metrics
    )
    kls = [float(row.get("anchor_kl_post_to_zero", math.inf)) for row in rows]
    tvs = [float(row.get("total_variation_from_initial", math.inf)) for row in rows]
    finite_kls = [value for value in kls if math.isfinite(value)]
    finite_tvs = [value for value in tvs if math.isfinite(value)]
    mean_kl = (
        math.fsum(finite_kls) / EXPECTED_ON_POLICY_ROWS
        if len(finite_kls) == EXPECTED_ON_POLICY_ROWS else math.inf
    )
    maximum_kl = max(finite_kls) if len(finite_kls) == EXPECTED_ON_POLICY_ROWS else math.inf
    maximum_tv = max(finite_tvs) if len(finite_tvs) == EXPECTED_ON_POLICY_ROWS else math.inf
    if mean_kl > 0.002:
        failures.append("global:mean_anchor_kl")
    if maximum_kl > 0.01:
        failures.append("global:per_row_anchor_kl")
    if maximum_tv > 0.02:
        failures.append("global:per_row_total_variation")
    total_nonfinite = measured_nonfinite + int(training_nonfinite_count)
    if total_nonfinite:
        failures.append("global:nonfinite")
    family = _family_diagnostics(prepare_receipt, rows)
    global_alignment = alignment_summary(
        [float(row["oriented_sampled_probability_delta"]) for row in rows]
    )
    global_failures = list(dict.fromkeys(failures))
    acceptance_failures = list(global_failures)
    family_required = stage == 2
    if family_required:
        acceptance_failures.extend(family["failures"])
    return {
        "stage": stage,
        "global_pass": not global_failures,
        "global_failures": global_failures,
        "hard_stop_before_stage_2": stage == 1 and bool(global_failures),
        "family_required_for_acceptance": family_required,
        "family_diagnostics": family,
        "global_alignment": global_alignment,
        "mean_anchor_kl": mean_kl,
        "maximum_anchor_kl": maximum_kl,
        "maximum_total_variation": maximum_tv,
        "nonfinite_count": total_nonfinite,
        "accepted_at_stage": not acceptance_failures,
        "acceptance_failures": acceptance_failures,
    }


def evaluate_directional_gates(
    prepare_receipt: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]], *, stage: int
) -> dict[str, Any]:
    fixed = prepare_receipt["rows"]
    memberships = prepare_receipt["directional_memberships"]
    failures: list[str] = []
    for ordinal in memberships["negative_target_ordinals"]:
        row = fixed[ordinal]
        probabilities = metrics[ordinal]["probabilities_float32"]
        initial = row["initial_probabilities_float32"]
        end_delta = float(probabilities[row["end_index"]]) - float(initial[row["end_index"]])
        teacher_delta = float(probabilities[row["teacher_index"]]) - float(initial[row["teacher_index"]])
        if end_delta > -1e-6:
            failures.append(f"negative:{ordinal}:end_decrease")
        if teacher_delta < 1e-6:
            failures.append(f"negative:{ordinal}:teacher_increase")
        try:
            inherited._unique_argmax(probabilities, int(row["teacher_index"]))
        except ValueError:
            failures.append(f"negative:{ordinal}:teacher_unique_argmax")
    for ordinal in memberships["teacher_end_ordinals"]:
        try:
            inherited._unique_argmax(
                metrics[ordinal]["probabilities_float32"], int(fixed[ordinal]["end_index"])
            )
        except ValueError:
            failures.append(f"legitimate_end:{ordinal}:unique_argmax")
    for ordinal in memberships["positive_normalized_teacher_and_sampled_end_ordinals"]:
        end = int(fixed[ordinal]["end_index"])
        delta = float(metrics[ordinal]["probabilities_float32"][end]) - float(
            fixed[ordinal]["initial_probabilities_float32"][end]
        )
        if delta < 1e-6:
            failures.append(f"legitimate_end:{ordinal}:normalized_increase")
    raw_deltas: list[float] = []
    for ordinal in memberships["positive_raw_teacher_and_sampled_end_ordinals"]:
        end = int(fixed[ordinal]["end_index"])
        raw_deltas.append(
            float(metrics[ordinal]["probabilities_float32"][end])
            - float(fixed[ordinal]["initial_probabilities_float32"][end])
        )
    raw_lower_median = lower_empirical_median(raw_deltas)
    maximum_decrease = max(max(0.0, -value) for value in raw_deltas)
    if raw_lower_median <= 0.0:
        failures.append("legitimate_end:positive_raw_lower_median")
    if maximum_decrease > 0.0025:
        failures.append("legitimate_end:positive_raw_maximum_decrease")
    return {
        "stage": stage,
        "required_for_acceptance": stage == 2,
        "passed": not failures,
        "failures": failures,
        "negative_target_count": len(memberships["negative_target_ordinals"]),
        "teacher_end_count": len(memberships["teacher_end_ordinals"]),
        "positive_normalized_teacher_and_sampled_end_count": len(
            memberships["positive_normalized_teacher_and_sampled_end_ordinals"]
        ),
        "positive_raw_teacher_and_sampled_end_count": len(
            memberships["positive_raw_teacher_and_sampled_end_ordinals"]
        ),
        "positive_raw_lower_empirical_median_delta": raw_lower_median,
        "positive_raw_maximum_individual_decrease": maximum_decrease,
    }


def raw_value_mse(
    prepare_receipt: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]] | None = None
) -> float:
    """No-grad diagnostic only; callers must never insert this into autograd."""

    with torch.no_grad():
        if metrics is None:
            predicted = [float(row["initial_value_float32"]) for row in prepare_receipt["rows"]]
        else:
            if len(metrics) != EXPECTED_ON_POLICY_ROWS:
                raise ValueError("raw value MSE metric count mismatch")
            predicted = [float(row["value_float32"]) for row in metrics]
        targets = [float(row["fixed_value_target_float64"]) for row in prepare_receipt["rows"]]
        values = [(left - right) ** 2 for left, right in zip(predicted, targets)]
        if len(values) != EXPECTED_ON_POLICY_ROWS or any(not math.isfinite(value) for value in values):
            raise ValueError("raw value MSE contains non-finite data")
        return math.fsum(values) / EXPECTED_ON_POLICY_ROWS


def value_change_summary(
    prepare_receipt: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    changes = [
        float(metric["value_float32"]) - float(fixed["initial_value_float32"])
        for fixed, metric in zip(prepare_receipt["rows"], metrics)
    ]
    nonfinite = sum(not math.isfinite(value) for value in changes)
    finite = [value for value in changes if math.isfinite(value)]
    return {
        "mean_change_from_initial": math.fsum(finite) / len(finite) if finite else math.nan,
        "median_change_from_initial": statistics.median(finite) if finite else math.nan,
        "maximum_absolute_change_from_initial": max(map(abs, finite)) if finite else math.nan,
        "nonfinite_count": nonfinite,
    }


def _load_execution_spec(path: Path, expected_file_sha256: str) -> dict[str, Any]:
    spec = inherited._load_hashed_json(
        path, expected_file_sha256, label="iteration-006 execution spec"
    )
    required = {
        "schema_version", "plan_path", "plan_sha256", "correction_path",
        "correction_sha256", "remediation_path", "remediation_sha256",
        "remediation_correction_path", "remediation_correction_sha256",
        "prepare_receipt_path", "prepare_receipt_file_sha256",
        "prepare_receipt_sha256", "implementation_snapshot_sha256",
        "input_checkpoint_path", "input_checkpoint_sha256", "rejected_checkpoint_sha256",
        "manifest_path", "manifest_sha256", "dataset_sha256",
        "runtime_thread_receipt", "training_contract", "output_directory",
    }
    row = dict(_exact_keys(spec, required, label="iteration-006 execution spec"))
    if row["schema_version"] != EXECUTION_SPEC_SCHEMA_VERSION:
        raise ValueError("iteration-006 execution spec schema mismatch")
    expected = {
        "plan_path": PLAN_RELATIVE_PATH.as_posix(),
        "plan_sha256": PLAN_SHA256,
        "correction_path": CORRECTION_RELATIVE_PATH.as_posix(),
        "correction_sha256": CORRECTION_SHA256,
        "remediation_path": REMEDIATION_RELATIVE_PATH.as_posix(),
        "remediation_sha256": REMEDIATION_SHA256,
        "remediation_correction_path": (
            REMEDIATION_CORRECTION_RELATIVE_PATH.as_posix()
        ),
        "remediation_correction_sha256": REMEDIATION_CORRECTION_SHA256,
        "input_checkpoint_path": INPUT_CHECKPOINT_RELATIVE_PATH.as_posix(),
        "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
        "rejected_checkpoint_sha256": REJECTED_CHECKPOINT_SHA256,
        "manifest_path": MANIFEST_RELATIVE_PATH.as_posix(),
        "manifest_sha256": MANIFEST_SHA256,
        "dataset_sha256": DATASET_SHA256,
        "output_directory": APPROVED_OUTPUT_RELATIVE_PATH.as_posix(),
    }
    for name, value in expected.items():
        if row.get(name) != value:
            raise ValueError(f"iteration-006 execution spec {name} mismatch")
    if row["input_checkpoint_sha256"] == row["rejected_checkpoint_sha256"]:
        raise ValueError("execution spec selects rejected checkpoint")
    return row


def _validate_execution_output(
    value: Any, *, receipt_path: Path, execution_spec_path: Path
) -> Path:
    if not isinstance(value, str) or value != APPROVED_OUTPUT_RELATIVE_PATH.as_posix():
        raise ValueError("execution output directory is not the one approved destination")
    relative = PurePosixPath(value)
    if any(part in (".", "..") for part in relative.parts):
        raise ValueError("execution output directory contains aliases")
    output = _repo_path(relative).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError("execution requires a new absent output directory")
    parent = output.parent
    if not parent.is_dir() or inherited._is_link_or_reparse(parent):
        raise ValueError("execution output parent must be a regular non-reparse directory")
    protected = (
        _repo_path(PLAN_RELATIVE_PATH), _repo_path(CORRECTION_RELATIVE_PATH),
        _repo_path(REMEDIATION_RELATIVE_PATH),
        _repo_path(REMEDIATION_CORRECTION_RELATIVE_PATH),
        _repo_path(IMPLEMENTATION_RELATIVE_PATH), _repo_path(SOURCE_IMPLEMENTATION_RELATIVE_PATH),
        _repo_path(INPUT_CHECKPOINT_RELATIVE_PATH), _repo_path(MANIFEST_RELATIVE_PATH),
        _repo_path(V4_PROBE_RELATIVE_PATH), _repo_path(PARENT_REJECTED_RECEIPT_RELATIVE_PATH),
        _repo_path(REJECTED_CHECKPOINT_RELATIVE_PATH), receipt_path, execution_spec_path,
    )
    if any(inherited._paths_overlap(output, item) for item in protected):
        raise ValueError("execution output overlaps a protected input")
    return output


def _validate_execution_boundary(
    spec: Mapping[str, Any], runtime: Mapping[str, Any], *, execution_spec_path: Path
) -> tuple[dict[str, Any], Path]:
    receipt_path = inherited._resolve_pinned_path(
        spec["prepare_receipt_path"], label="iteration-006 prepare receipt path"
    )
    receipt_path = _validate_prepare_output_path(receipt_path, must_exist=True)
    receipt = inherited._load_hashed_json(
        receipt_path,
        _strict_sha256(
            spec["prepare_receipt_file_sha256"], label="prepare receipt file hash"
        ),
        label="pinned iteration-006 prepare receipt",
    )
    validate_prepare_receipt(receipt)
    if receipt["receipt_sha256"] != spec["prepare_receipt_sha256"]:
        raise ValueError("execution spec prepare self-hash mismatch")
    if receipt["implementation"]["sha256"] != spec["implementation_snapshot_sha256"]:
        raise ValueError("execution spec implementation snapshot mismatch")
    current = inherited.implementation_snapshot(_repo_path(IMPLEMENTATION_RELATIVE_PATH))
    if current != {
        name: receipt["implementation"][name]
        for name in ("definition", "file_count", "sha256", "files")
    }:
        raise ValueError("implementation changed after prepare")
    if dict(runtime) != dict(spec["runtime_thread_receipt"]):
        raise ValueError("execution runtime differs from spec")
    if dict(runtime) != dict(receipt["runtime_thread_receipt"]):
        raise ValueError("execution runtime differs from prepare")
    if spec["training_contract"] != receipt["training_contract"]:
        raise ValueError("execution training contract differs from prepare")
    rebuilt = _build_prepare_receipt(runtime)
    if rebuilt != receipt:
        raise ValueError("prepare evidence did not reproduce at execution boundary")
    output = _validate_execution_output(
        spec["output_directory"],
        receipt_path=receipt_path,
        execution_spec_path=execution_spec_path,
    )
    return receipt, output


def _run_two_stage(
    loaded: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    progress: ExecutionProgress,
) -> dict[str, Any]:
    model = loaded["model"]
    progress.model = model
    initial_parameters = {
        name: value.detach().clone() for name, value in model.state_dict().items()
    }
    initial_value_hashes = {
        name: _tensor_sha256(initial_parameters[name]) for name in EXPECTED_VALUE_NAMES
    }
    raw_initial = raw_value_mse(prepare_receipt)
    _set_trainability(model, stage=1)
    optimizer = _new_actor_adam(model)
    progress.optimizer = optimizer
    optimizer_identity = optimizer
    progress.failure_phase = "stage_1_full_batch_step"
    stage_1 = _stage_full_batch_step(
        stage=1,
        loaded=loaded,
        prepare_receipt=prepare_receipt,
        optimizer=optimizer,
        initial_parameters=initial_parameters,
        progress=progress,
    )
    metrics_1 = _measure_stage(loaded, prepare_receipt, stage=1)
    gates_1 = evaluate_stage_gates(
        prepare_receipt,
        metrics_1,
        stage=1,
        training_nonfinite_count=stage_1[
            "nonfinite_value_gradient_optimizer_or_parameter_count"
        ],
    )
    directional_1 = evaluate_directional_gates(
        prepare_receipt, metrics_1, stage=1
    )
    raw_stage_1 = raw_value_mse(prepare_receipt, metrics_1)
    common = {
        "model": model,
        "optimizer": optimizer,
        "initial_parameters": initial_parameters,
        "initial_value_head_parameter_hashes": initial_value_hashes,
        "stage_1_report": stage_1,
        "stage_1_metrics": metrics_1,
        "stage_1_gates": gates_1,
        "stage_1_directional_diagnostics": directional_1,
        "raw_value_mse_initial": raw_initial,
        "raw_value_mse_stage_1": raw_stage_1,
        "weighted_value_loss_stage_1": 0.0,
        "stage_1_value_change_summary": value_change_summary(
            prepare_receipt, metrics_1
        ),
        "fixed_anchor_kl_coefficient_stage_1": 0.1,
        "fixed_anchor_kl_coefficient_stage_2": 0.1,
        "adaptive_anchor_kl_adjustment_between_stages": False,
    }
    if gates_1["hard_stop_before_stage_2"]:
        return {
            **common,
            "stopped_before_stage_2": True,
            "optimizer_steps_completed": progress.optimizer_steps_completed,
            "same_optimizer_object_across_stages": False,
            "stage_2_report": None,
            "stage_2_metrics": None,
            "stage_2_gates": None,
            "stage_2_directional_gates": None,
            "stage_2_improvement": None,
            "raw_value_mse_stage_2": None,
            "weighted_value_loss_stage_2": None,
            "stage_2_value_change_summary": None,
            "final_value_head_parameter_hashes": initial_value_hashes,
        }
    progress.stage_2_entered = True
    progress.failure_phase = "stage_2_full_batch_step"
    stage_2 = _stage_full_batch_step(
        stage=2,
        loaded=loaded,
        prepare_receipt=prepare_receipt,
        optimizer=optimizer,
        initial_parameters=initial_parameters,
        progress=progress,
    )
    if optimizer is not optimizer_identity:
        raise ValueError("optimizer object changed between stages")
    metrics_2 = _measure_stage(loaded, prepare_receipt, stage=2)
    gates_2 = evaluate_stage_gates(
        prepare_receipt,
        metrics_2,
        stage=2,
        training_nonfinite_count=stage_2[
            "nonfinite_value_gradient_optimizer_or_parameter_count"
        ],
    )
    directional_2 = evaluate_directional_gates(
        prepare_receipt, metrics_2, stage=2
    )
    improvement = evaluate_stage2_improvement(
        gates_1["global_alignment"], gates_2["global_alignment"]
    )
    raw_stage_2 = raw_value_mse(prepare_receipt, metrics_2)
    if stage_1["fixed_advantages_sha256"] != stage_2["fixed_advantages_sha256"]:
        raise ValueError("fixed advantages changed between stages")
    if stage_1["fixed_behavior_logprobabilities_sha256"] != stage_2[
        "fixed_behavior_logprobabilities_sha256"
    ]:
        raise ValueError("behavior log-probabilities changed between stages")
    final_value_hashes = {
        name: _tensor_sha256(dict(model.named_parameters())[name])
        for name in EXPECTED_VALUE_NAMES
    }
    if final_value_hashes != initial_value_hashes:
        raise ValueError("value-head parameter bytes changed")
    return {
        **common,
        "stopped_before_stage_2": False,
        "optimizer_steps_completed": progress.optimizer_steps_completed,
        "same_optimizer_object_across_stages": True,
        "stage_2_report": stage_2,
        "stage_2_metrics": metrics_2,
        "stage_2_gates": gates_2,
        "stage_2_directional_gates": directional_2,
        "stage_2_improvement": improvement,
        "raw_value_mse_stage_2": raw_stage_2,
        "weighted_value_loss_stage_2": 0.0,
        "stage_2_value_change_summary": value_change_summary(prepare_receipt, metrics_2),
        "final_value_head_parameter_hashes": final_value_hashes,
    }


def _audit_serialized_optimizer(
    optimizer_state: Mapping[str, Any], *, completed_stage: int, allow_nonfinite: bool = False
) -> dict[str, int]:
    state = optimizer_state.get("state")
    groups = optimizer_state.get("param_groups")
    if not isinstance(state, dict) or not isinstance(groups, list) or len(groups) != 1:
        raise ValueError("serialized actor Adam layout mismatch")
    group = groups[0]
    expected_config = {
        "lr": 0.0001, "betas": (0.9, 0.999), "eps": 1e-8,
        "weight_decay": 0.0, "amsgrad": False, "foreach": None,
        "maximize": False, "capturable": False, "differentiable": False,
        "fused": None, "decoupled_weight_decay": False,
    }
    for name, value in expected_config.items():
        if group.get(name) != value:
            raise ValueError(f"serialized actor Adam {name} mismatch")
    parameter_ids = list(group.get("params") or ())
    if len(parameter_ids) != len(EXPECTED_ACTOR_NAMES):
        raise ValueError("serialized actor Adam parameter universe mismatch")
    result: dict[str, int] = {}
    for name, identifier in zip(EXPECTED_ACTOR_NAMES, parameter_ids):
        parameter_state = state.get(identifier)
        if parameter_state is None:
            if completed_stage == 1 and name not in STAGE1_TRAINABLE_NAMES:
                continue
            raise ValueError("serialized actor Adam state is missing")
        step = parameter_state.get("step")
        value = float(step.detach().cpu()) if torch.is_tensor(step) else float(step)
        if not value.is_integer():
            raise ValueError("serialized actor Adam step is not integral")
        if not allow_nonfinite:
            inherited._finite_tensors_or_raise(
                (item for item in parameter_state.values() if torch.is_tensor(item)),
                label="serialized actor optimizer state",
            )
        result[name] = int(value)
    expected = (
        {name: 1 for name in STAGE1_TRAINABLE_NAMES}
        if completed_stage == 1
        else {
            name: (2 if name in STAGE1_TRAINABLE_NAMES else 1)
            for name in EXPECTED_ACTOR_NAMES
        }
    )
    if result != expected or set(state) != {
        identifier for name, identifier in zip(EXPECTED_ACTOR_NAMES, parameter_ids)
        if name in expected
    }:
        raise ValueError("serialized actor Adam mixed-step contract mismatch")
    return result


def _expected_optimizer_steps(completed_stage: int) -> dict[str, int]:
    if completed_stage == 1:
        return {name: 1 for name in STAGE1_TRAINABLE_NAMES}
    if completed_stage == 2:
        return {
            name: (2 if name in STAGE1_TRAINABLE_NAMES else 1)
            for name in EXPECTED_ACTOR_NAMES
        }
    raise ValueError("optimizer contract requires completed stage 1 or 2")


def _json_safe_optimizer_step(value: Any) -> int | str | None:
    if value is None:
        return None
    try:
        if torch.is_tensor(value):
            if value.numel() != 1:
                return "non_scalar"
            numeric = float(value.detach().cpu().reshape(()))
        else:
            if isinstance(value, bool):
                return "boolean"
            numeric = float(value)
    except (TypeError, ValueError, RuntimeError):
        return "invalid"
    if not math.isfinite(numeric):
        return "nonfinite"
    if not numeric.is_integer():
        return "nonintegral"
    return int(numeric)


def _rejected_optimizer_contract_report(
    optimizer_state: Any, *, completed_stage: int
) -> dict[str, Any]:
    """Audit semantic Adam state without discarding byte-exact rejection evidence."""

    expected = _expected_optimizer_steps(completed_stage)
    observed: dict[str, int | str | None] = {
        name: None for name in expected
    }
    failures: list[str] = []
    if not isinstance(optimizer_state, Mapping):
        failures.append("optimizer_state:layout")
        return {
            "optimizer_contract_pass": False,
            "optimizer_contract_failures": failures,
            "optimizer_steps_expected": expected,
            "optimizer_steps_observed": observed,
        }
    state = optimizer_state.get("state")
    groups = optimizer_state.get("param_groups")
    if not isinstance(state, Mapping):
        failures.append("optimizer_state:missing_state_map")
        state = {}
    if not isinstance(groups, list) or len(groups) != 1 or not isinstance(groups[0], Mapping):
        failures.append("optimizer_state:param_group_layout")
        group: Mapping[str, Any] = {}
    else:
        group = groups[0]
    expected_config = {
        "lr": 0.0001, "betas": (0.9, 0.999), "eps": 1e-8,
        "weight_decay": 0.0, "amsgrad": False, "foreach": None,
        "maximize": False, "capturable": False, "differentiable": False,
        "fused": None, "decoupled_weight_decay": False,
    }
    for name, value in expected_config.items():
        if group.get(name) != value:
            failures.append(f"optimizer_config:{name}")
    raw_parameter_ids = group.get("params")
    parameter_ids = list(raw_parameter_ids) if isinstance(raw_parameter_ids, list) else []
    if len(parameter_ids) != len(EXPECTED_ACTOR_NAMES):
        failures.append("optimizer_state:parameter_universe")
    known_ids = {
        identifier: name
        for name, identifier in zip(EXPECTED_ACTOR_NAMES, parameter_ids)
    }
    expected_ids = {
        identifier for identifier, name in known_ids.items() if name in expected
    }
    for name, wanted_step in expected.items():
        if name not in known_ids.values():
            failures.append(f"optimizer_state:missing_parameter:{name}")
            continue
        identifier = next(
            identifier for identifier, candidate in known_ids.items() if candidate == name
        )
        parameter_state = state.get(identifier)
        if not isinstance(parameter_state, Mapping):
            failures.append(f"optimizer_state:missing:{name}")
            continue
        step = _json_safe_optimizer_step(parameter_state.get("step"))
        observed[name] = step
        if step != wanted_step:
            failures.append(f"optimizer_step:wrong:{name}")
        if _nested_nonfinite_count(parameter_state):
            failures.append(f"optimizer_state:nonfinite:{name}")
    for identifier, parameter_state in state.items():
        if identifier in expected_ids:
            continue
        label = known_ids.get(identifier)
        if label is None:
            label = f"unknown_{str(identifier)}"
        failure_label = f"optimizer_state:extra:{label}"
        failures.append(failure_label)
        observed[f"extra:{label}"] = (
            _json_safe_optimizer_step(parameter_state.get("step"))
            if isinstance(parameter_state, Mapping)
            else "invalid"
        )
        if _nested_nonfinite_count(parameter_state):
            failures.append(f"optimizer_state:nonfinite:{label}")
    unique_failures = list(dict.fromkeys(failures))
    return {
        "optimizer_contract_pass": not unique_failures,
        "optimizer_contract_failures": unique_failures,
        "optimizer_steps_expected": expected,
        "optimizer_steps_observed": observed,
    }


def _validate_serialized_checkpoint(
    serialized: bytes,
    *,
    claimed_sha256: str,
    model: ResidualActorCritic,
    metadata: Mapping[str, Any],
    optimizer: torch.optim.Adam,
    source_hashes: Mapping[str, str],
    completed_stage: int,
) -> dict[str, Any]:
    actual_hash = hashlib.sha256(serialized).hexdigest().upper()
    if actual_hash != claimed_sha256:
        raise ValueError("serialized checkpoint hash mismatch")
    payload = torch.load(io.BytesIO(serialized), map_location="cpu", weights_only=False)
    if not isinstance(payload, dict) or set(payload) != {
        "model_config", "model_state", "metadata", "optimizer_state"
    }:
        raise ValueError("serialized checkpoint payload schema mismatch")
    _validate_metadata(payload["metadata"], expected_source_hashes=source_hashes)
    if payload["metadata"] != dict(metadata):
        raise ValueError("serialized checkpoint metadata mismatch")
    if ModelConfig(**payload["model_config"]) != model.config:
        raise ValueError("serialized checkpoint model config mismatch")
    reloaded = ResidualActorCritic(model.config)
    reloaded.load_state_dict(payload["model_state"], strict=True)
    if not inherited._nested_tensor_exact(reloaded.state_dict(), model.state_dict()):
        raise ValueError("serialized checkpoint model state mismatch")
    expected_optimizer = optimizer.state_dict()
    if not inherited._nested_tensor_exact(payload["optimizer_state"], expected_optimizer):
        raise ValueError("serialized checkpoint optimizer state mismatch")
    steps = _audit_serialized_optimizer(
        payload["optimizer_state"], completed_stage=completed_stage
    )
    return {
        "status": "pass",
        "checkpoint_sha256": actual_hash,
        "metadata_exact": True,
        "model_state_exact": True,
        "optimizer_state_exact": True,
        "optimizer_state_steps": steps,
        "completed_stage": completed_stage,
        "parameters_finite": True,
    }


def _validate_rejected_checkpoint_readback(
    serialized: bytes,
    *,
    claimed_sha256: str,
    model: ResidualActorCritic,
    metadata: Mapping[str, Any],
    optimizer: torch.optim.Adam,
    source_hashes: Mapping[str, str],
    completed_stage: int,
) -> dict[str, Any]:
    actual_hash = hashlib.sha256(serialized).hexdigest().upper()
    if actual_hash != claimed_sha256:
        raise ValueError("rejected checkpoint readback hash mismatch")
    payload = torch.load(io.BytesIO(serialized), map_location="cpu", weights_only=False)
    if not isinstance(payload, dict) or set(payload) != {
        "model_config", "model_state", "metadata", "optimizer_state"
    }:
        raise ValueError("rejected checkpoint payload schema mismatch")
    _validate_metadata(payload["metadata"], expected_source_hashes=source_hashes)
    if payload["metadata"] != dict(metadata):
        raise ValueError("rejected checkpoint metadata mismatch")
    if ModelConfig(**payload["model_config"]) != model.config:
        raise ValueError("rejected checkpoint model config mismatch")
    if not _nested_byte_exact(payload["model_state"], model.state_dict()):
        raise ValueError("rejected checkpoint model byte round-trip mismatch")
    expected_optimizer = optimizer.state_dict()
    if not _nested_byte_exact(payload["optimizer_state"], expected_optimizer):
        raise ValueError("rejected checkpoint optimizer byte round-trip mismatch")
    optimizer_contract = _rejected_optimizer_contract_report(
        payload["optimizer_state"], completed_stage=completed_stage
    )
    model_nonfinite = _nested_nonfinite_count(model.state_dict())
    optimizer_nonfinite = _nested_nonfinite_count(expected_optimizer)
    if (
        _nested_nonfinite_count(payload["model_state"]) != model_nonfinite
        or _nested_nonfinite_count(payload["optimizer_state"]) != optimizer_nonfinite
    ):
        raise ValueError("rejected checkpoint nonfinite counts changed on readback")
    return {
        "status": "pass",
        "checkpoint_sha256": actual_hash,
        "checkpoint_readback_exact": True,
        "model_state_byte_exact": True,
        "optimizer_state_byte_exact": True,
        "metadata_exact": True,
        "optimizer_state_steps": optimizer_contract["optimizer_steps_observed"],
        **optimizer_contract,
        "completed_stage": completed_stage,
        "model_nonfinite_count": model_nonfinite,
        "optimizer_nonfinite_count": optimizer_nonfinite,
        "total_nonfinite_count": model_nonfinite + optimizer_nonfinite,
    }


def _final_gate_report(
    run: Mapping[str, Any], *, serialized_validation: Mapping[str, Any]
) -> dict[str, Any]:
    failures: list[str] = []
    if run["stopped_before_stage_2"]:
        failures.append("execution:stage_1_hard_stop")
    if run["optimizer_steps_completed"] != 2:
        failures.append("execution:optimizer_steps")
    if not run["stage_1_gates"]["global_pass"]:
        failures.extend(run["stage_1_gates"]["global_failures"])
    stage_2 = run.get("stage_2_gates")
    if stage_2 is None:
        failures.append("execution:stage_2_missing")
    else:
        failures.extend(stage_2["acceptance_failures"])
    directional = run.get("stage_2_directional_gates")
    if directional is None or not directional["passed"]:
        failures.extend(
            ["directional:stage_2_missing"] if directional is None else directional["failures"]
        )
    improvement = run.get("stage_2_improvement")
    if improvement is None or not improvement["accepted"]:
        failures.extend(
            ["alignment:stage_2_missing"] if improvement is None else improvement["failures"]
        )
    if run.get("same_optimizer_object_across_stages") is not True:
        failures.append("optimizer:object_identity")
    stage_1_report = run["stage_1_report"]
    stage_2_report = run.get("stage_2_report")
    parameter_optimizer_contract = bool(
        stage_1_report["changed_parameter_names_from_initial"]
        == list(STAGE1_TRAINABLE_NAMES)
        and stage_1_report["optimizer_state_steps"]
        == {name: 1 for name in STAGE1_TRAINABLE_NAMES}
        and stage_2_report is not None
        and stage_2_report["changed_parameter_names_from_initial"]
        == list(EXPECTED_ACTOR_NAMES)
        and stage_2_report["optimizer_state_steps"]
        == {
            name: (2 if name in STAGE1_TRAINABLE_NAMES else 1)
            for name in EXPECTED_ACTOR_NAMES
        }
    )
    if not parameter_optimizer_contract:
        failures.append("parameter_optimizer:contract")
    if run["weighted_value_loss_stage_1"] != 0.0 or run.get("weighted_value_loss_stage_2") != 0.0:
        failures.append("value:weighted_loss")
    value_contract = bool(
        run.get("final_value_head_parameter_hashes")
        == run.get("initial_value_head_parameter_hashes")
        and (run.get("stage_1_value_change_summary") or {}).get("nonfinite_count") == 0
        and (run.get("stage_2_value_change_summary") or {}).get("nonfinite_count") == 0
        and all(
            isinstance(run.get(name), (int, float))
            and not isinstance(run.get(name), bool)
            and math.isfinite(float(run[name]))
            for name in (
                "raw_value_mse_initial", "raw_value_mse_stage_1", "raw_value_mse_stage_2"
            )
        )
    )
    if not value_contract:
        failures.append("value:contract")
    fixed_inputs_contract = bool(
        stage_2_report is not None
        and stage_1_report["fixed_advantages_sha256"]
        == stage_2_report["fixed_advantages_sha256"]
        and stage_1_report["fixed_behavior_logprobabilities_sha256"]
        == stage_2_report["fixed_behavior_logprobabilities_sha256"]
    )
    if not fixed_inputs_contract:
        failures.append("fixed_training_inputs:contract")
    anchor_contract = bool(
        run.get("fixed_anchor_kl_coefficient_stage_1") == 0.1
        and run.get("fixed_anchor_kl_coefficient_stage_2") == 0.1
        and run.get("adaptive_anchor_kl_adjustment_between_stages") is False
    )
    if not anchor_contract:
        failures.append("anchor_kl:coefficient_contract")
    if serialized_validation.get("status") != "pass":
        failures.append("checkpoint:serialized_validation")
    return {
        "accepted": not failures,
        "failures": list(dict.fromkeys(failures)),
        "stage_1_global": run["stage_1_gates"],
        "stage_1_family_diagnostic_only": run["stage_1_gates"]["family_diagnostics"],
        "stage_2_global_and_family": stage_2,
        "stage_2_improvement": improvement,
        "stage_2_directional": directional,
        "parameter_optimizer_contract_pass": parameter_optimizer_contract,
        "value_contract_pass": value_contract,
        "fixed_training_inputs_contract_pass": fixed_inputs_contract,
        "fixed_anchor_kl_contract_pass": anchor_contract,
        "serialized_checkpoint_validation": dict(serialized_validation),
    }


def _publish_failure_status(
    output_directory: Path,
    *,
    execution_spec_path: Path,
    execution_spec_sha256: str,
    phase: str,
    error: Exception,
    directory_guard: inherited._StableDirectoryGuard,
    checkpoint_path: Path | None = None,
    checkpoint_sha256: str | None = None,
    optimizer_steps_completed: int = 0,
) -> dict[str, Any]:
    core = {
        "schema_version": EXECUTION_RECEIPT_SCHEMA_VERSION,
        "status": "rejected",
        "base_plan_sha256": PLAN_SHA256,
        "correction_sha256": CORRECTION_SHA256,
        "remediation_sha256": REMEDIATION_SHA256,
        "remediation_correction_path": REMEDIATION_CORRECTION_RELATIVE_PATH.as_posix(),
        "remediation_correction_sha256": REMEDIATION_CORRECTION_SHA256,
        "failure_phase": phase,
        "failure_kind": type(error).__name__,
        "failure_message": str(error),
        "execution_spec_path": str(execution_spec_path.absolute()),
        "execution_spec_sha256": execution_spec_sha256,
        "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
        "rejected_checkpoint_sha256": REJECTED_CHECKPOINT_SHA256,
        "output_checkpoint_path": (
            str(checkpoint_path.absolute()) if checkpoint_path is not None else None
        ),
        "output_checkpoint_sha256": checkpoint_sha256,
        "optimizer_steps_completed": optimizer_steps_completed,
        "checkpoint_readback_exact": None,
        "model_nonfinite_count": None,
        "optimizer_nonfinite_count": None,
        "accepted_marker_written": False,
    }
    receipt = {**core, "receipt_sha256": canonical_sha256(core)}
    path, file_hash = inherited._publish_status(
        output_directory,
        status="rejected",
        receipt=receipt,
        directory_guard=directory_guard,
    )
    return {
        "mode": "execute",
        "status": "rejected",
        "failure_phase": phase,
        "failure_kind": type(error).__name__,
        "optimizer_steps_completed": optimizer_steps_completed,
        "checkpoint_path": core["output_checkpoint_path"],
        "checkpoint_sha256": checkpoint_sha256,
        "checkpoint_readback_exact": None,
        "receipt_path": str(path.absolute()),
        "receipt_file_sha256": file_hash,
        "receipt_sha256": receipt["receipt_sha256"],
        "accepted_marker_written": False,
    }


def _publish_post_step_rejection(
    output_directory: Path,
    *,
    progress: ExecutionProgress,
    source_hashes: Mapping[str, str],
    execution_spec_path: Path,
    execution_spec_sha256: str,
    phase: str,
    error: Exception,
    directory_guard: inherited._StableDirectoryGuard,
    existing_checkpoint_path: Path | None = None,
    existing_checkpoint_sha256: str | None = None,
    existing_checkpoint_guard: inherited._StableFileGuard | None = None,
    existing_checkpoint_readback: bytes | None = None,
    existing_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if progress.optimizer_steps_completed not in (1, 2):
        raise ValueError("post-step rejection requires completed step count 1 or 2")
    if progress.model is None or progress.optimizer is None:
        raise ValueError("post-step rejection lost model or optimizer state")
    completed_stage = progress.optimizer_steps_completed
    metadata = (
        dict(existing_metadata)
        if existing_metadata is not None
        else checkpoint_metadata(
            source_hashes=source_hashes,
            training={
                "pilot": PLAN_ID,
                "base_plan_sha256": PLAN_SHA256,
                "correction_sha256": CORRECTION_SHA256,
                "remediation_sha256": REMEDIATION_SHA256,
                "remediation_correction_path": (
                    REMEDIATION_CORRECTION_RELATIVE_PATH.as_posix()
                ),
                "remediation_correction_sha256": REMEDIATION_CORRECTION_SHA256,
                "execution_spec_path": str(execution_spec_path),
                "execution_spec_sha256": execution_spec_sha256,
                "status": "rejected_post_step_exception",
                "failure_phase": phase,
                "failure_kind": type(error).__name__,
                "failure_message": str(error),
                "optimizer_steps_completed": completed_stage,
                "checkpoint_readback_validation": "required_after_save",
            },
        )
    )
    owned_checkpoint_guard: inherited._StableFileGuard | None = None
    checkpoint_path = existing_checkpoint_path
    checkpoint_hash = existing_checkpoint_sha256
    readback = existing_checkpoint_readback
    checkpoint_guard = existing_checkpoint_guard
    checkpoint_evidence_transferred = existing_checkpoint_guard is not None
    try:
        if checkpoint_path is None:
            if any(
                value is not None
                for value in (
                    existing_checkpoint_sha256,
                    existing_checkpoint_guard,
                    existing_checkpoint_readback,
                    existing_metadata,
                )
            ):
                raise ValueError("partial existing checkpoint evidence")
            try:
                (
                    checkpoint_path,
                    checkpoint_hash,
                    owned_checkpoint_guard,
                    readback,
                ) = inherited._publish_checkpoint_exclusive(
                    output_directory,
                    model=progress.model,
                    metadata=metadata,
                    optimizer=progress.optimizer,
                    directory_guard=directory_guard,
                )
            except inherited._CheckpointPublicationHandoffError as handoff:
                checkpoint_path = handoff.checkpoint_path
                checkpoint_hash = handoff.checkpoint_sha256
                owned_checkpoint_guard = handoff.checkpoint_guard
                readback = handoff.checkpoint_readback
                checkpoint_evidence_transferred = True
            checkpoint_guard = owned_checkpoint_guard
        if (
            checkpoint_path is None
            or checkpoint_hash is None
            or checkpoint_guard is None
            or readback is None
        ):
            raise ValueError("post-step rejection checkpoint evidence is incomplete")
        checkpoint_guard.ensure_bound_to(directory_guard)
        held_readback = inherited._win_read_all(checkpoint_guard.handle)
        if held_readback != readback:
            raise ValueError("post-step rejected checkpoint changed through held handle")
        retention = _validate_rejected_checkpoint_readback(
            held_readback,
            claimed_sha256=checkpoint_hash,
            model=progress.model,
            metadata=metadata,
            optimizer=progress.optimizer,
            source_hashes=source_hashes,
            completed_stage=completed_stage,
        )
        core = {
            "schema_version": EXECUTION_RECEIPT_SCHEMA_VERSION,
            "status": "rejected",
            "base_plan_sha256": PLAN_SHA256,
            "correction_sha256": CORRECTION_SHA256,
            "remediation_sha256": REMEDIATION_SHA256,
            "remediation_correction_path": (
                REMEDIATION_CORRECTION_RELATIVE_PATH.as_posix()
            ),
            "remediation_correction_sha256": REMEDIATION_CORRECTION_SHA256,
            "execution_spec_path": str(execution_spec_path.absolute()),
            "execution_spec_sha256": execution_spec_sha256,
            "failure_phase": phase,
            "failure_kind": type(error).__name__,
            "failure_message": str(error),
            "optimizer_steps_completed": completed_stage,
            "stage_2_entered": progress.stage_2_entered,
            "output_checkpoint_path": str(checkpoint_path.absolute()),
            "output_checkpoint_sha256": checkpoint_hash,
            "checkpoint_readback_exact": retention["checkpoint_readback_exact"],
            "optimizer_contract_pass": retention["optimizer_contract_pass"],
            "optimizer_contract_failures": retention[
                "optimizer_contract_failures"
            ],
            "optimizer_steps_expected": retention["optimizer_steps_expected"],
            "optimizer_steps_observed": retention["optimizer_steps_observed"],
            "model_nonfinite_count": retention["model_nonfinite_count"],
            "optimizer_nonfinite_count": retention["optimizer_nonfinite_count"],
            "retention_validation": retention,
            "checkpoint_evidence_transferred": checkpoint_evidence_transferred,
            "accepted_marker_written": False,
            "same_iteration_retry": False,
        }
        receipt = {**core, "receipt_sha256": canonical_sha256(core)}
        receipt_path, receipt_file_hash = inherited._publish_status(
            output_directory,
            status="rejected",
            receipt=receipt,
            directory_guard=directory_guard,
        )
        if (
            (output_directory / "ACCEPTED").exists()
            or (output_directory / "accepted_receipt.json").exists()
            or not (output_directory / "REJECTED").is_file()
        ):
            raise ValueError("post-step rejection status artifacts are inconsistent")
        return {
            "mode": "execute",
            "status": "rejected",
            "failure_phase": phase,
            "failure_kind": type(error).__name__,
            "optimizer_steps_completed": completed_stage,
            "checkpoint_path": str(checkpoint_path.absolute()),
            "checkpoint_sha256": checkpoint_hash,
            "checkpoint_readback_exact": True,
            "optimizer_contract_pass": retention["optimizer_contract_pass"],
            "receipt_path": str(receipt_path.absolute()),
            "receipt_file_sha256": receipt_file_hash,
            "receipt_sha256": receipt["receipt_sha256"],
            "accepted_marker_written": False,
        }
    finally:
        if owned_checkpoint_guard is not None:
            owned_checkpoint_guard.close()


def execute(*, execution_spec: Path, execution_spec_sha256: str) -> dict[str, Any]:
    """Run only when a later exact execution spec separately authorizes it."""

    execution_spec_path = execution_spec.absolute()
    runtime = inherited._runtime_identity()
    spec = _load_execution_spec(execution_spec_path, execution_spec_sha256)
    probe, output_directory = _validate_execution_boundary(
        spec, runtime, execution_spec_path=execution_spec_path
    )
    loaded = inherited._load_validated_inputs()
    if loaded["checkpoint_path"].resolve(strict=True) != _repo_path(
        INPUT_CHECKPOINT_RELATIVE_PATH
    ).resolve(strict=True):
        raise ValueError("execution did not load the immutable initial checkpoint")
    output_guard = inherited._create_and_guard_output_directory(output_directory)
    progress = ExecutionProgress()
    checkpoint_guard: inherited._StableFileGuard | None = None
    checkpoint_path: Path | None = None
    checkpoint_hash: str | None = None
    checkpoint_readback: bytes | None = None
    metadata: Mapping[str, Any] | None = None
    phase = "two_stage_actor_only_updates"
    try:
        run = _run_two_stage(loaded, probe, progress)
        completed_stage = 1 if run["stopped_before_stage_2"] else 2
        metadata = checkpoint_metadata(
            source_hashes=loaded["source_hashes"],
            training={
                "pilot": PLAN_ID,
                "base_plan_path": PLAN_RELATIVE_PATH.as_posix(),
                "base_plan_sha256": PLAN_SHA256,
                "correction_path": CORRECTION_RELATIVE_PATH.as_posix(),
                "correction_sha256": CORRECTION_SHA256,
                "remediation_path": REMEDIATION_RELATIVE_PATH.as_posix(),
                "remediation_sha256": REMEDIATION_SHA256,
                "remediation_correction_path": (
                    REMEDIATION_CORRECTION_RELATIVE_PATH.as_posix()
                ),
                "remediation_correction_sha256": REMEDIATION_CORRECTION_SHA256,
                "execution_spec_path": str(execution_spec_path),
                "execution_spec_sha256": execution_spec_sha256,
                "prepare_receipt_sha256": probe["receipt_sha256"],
                "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
                "manifest_sha256": MANIFEST_SHA256,
                "dataset_sha256": DATASET_SHA256,
                "ppo_config": asdict(TWO_STAGE_PPO_CONFIG),
                "adam": copy.deepcopy(ADAM_CONFIG),
                "fixed_anchor_kl_coefficients": [0.1, 0.1],
                "adaptive_anchor_kl_adjustment": False,
                "optimizer_steps_completed": run["optimizer_steps_completed"],
                "completed_stage": completed_stage,
                "weighted_value_loss_stage_1": run["weighted_value_loss_stage_1"],
                "weighted_value_loss_stage_2": run["weighted_value_loss_stage_2"],
                "raw_value_mse_initial": run["raw_value_mse_initial"],
                "raw_value_mse_stage_1": run["raw_value_mse_stage_1"],
                "raw_value_mse_stage_2": run["raw_value_mse_stage_2"],
                "checkpoint_provenance_validation": "required_after_save",
            },
        )
        phase = "checkpoint_exclusive_publication"
        (
            checkpoint_path,
            checkpoint_hash,
            checkpoint_guard,
            checkpoint_readback,
        ) = inherited._publish_checkpoint_exclusive(
            output_directory,
            model=run["model"],
            metadata=metadata,
            optimizer=run["optimizer"],
            directory_guard=output_guard,
        )
        phase = "checkpoint_reload_provenance_validation"
        checkpoint_guard.ensure_bound_to(output_guard)
        if inherited._win_read_all(checkpoint_guard.handle) != checkpoint_readback:
            raise ValueError("published checkpoint changed before validation")
        serialized = _validate_serialized_checkpoint(
            checkpoint_readback,
            claimed_sha256=checkpoint_hash,
            model=run["model"],
            metadata=metadata,
            optimizer=run["optimizer"],
            source_hashes=loaded["source_hashes"],
            completed_stage=completed_stage,
        )
        gates = _final_gate_report(run, serialized_validation=serialized)
        status = "accepted" if gates["accepted"] else "rejected"
        stage_keys = (
            "stage_1_report", "stage_1_metrics", "stage_1_gates",
            "stage_1_directional_diagnostics", "stage_2_report", "stage_2_metrics",
            "stage_2_gates", "stage_2_directional_gates", "stage_2_improvement",
            "stopped_before_stage_2", "optimizer_steps_completed",
            "same_optimizer_object_across_stages", "raw_value_mse_initial",
            "raw_value_mse_stage_1", "raw_value_mse_stage_2",
            "weighted_value_loss_stage_1", "weighted_value_loss_stage_2",
            "stage_1_value_change_summary", "stage_2_value_change_summary",
            "initial_value_head_parameter_hashes", "final_value_head_parameter_hashes",
            "fixed_anchor_kl_coefficient_stage_1", "fixed_anchor_kl_coefficient_stage_2",
            "adaptive_anchor_kl_adjustment_between_stages",
        )
        run_receipt = {name: run.get(name) for name in stage_keys}
        core = {
            "schema_version": EXECUTION_RECEIPT_SCHEMA_VERSION,
            "status": status,
            "base_plan_sha256": PLAN_SHA256,
            "correction_sha256": CORRECTION_SHA256,
            "remediation_sha256": REMEDIATION_SHA256,
            "remediation_correction_path": (
                REMEDIATION_CORRECTION_RELATIVE_PATH.as_posix()
            ),
            "remediation_correction_sha256": REMEDIATION_CORRECTION_SHA256,
            "execution_spec_path": str(execution_spec_path),
            "execution_spec_sha256": execution_spec_sha256,
            "prepare_receipt_sha256": probe["receipt_sha256"],
            "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
            "rejected_checkpoint_sha256": REJECTED_CHECKPOINT_SHA256,
            "manifest_sha256": MANIFEST_SHA256,
            "dataset_sha256": DATASET_SHA256,
            "output_checkpoint_path": str(checkpoint_path.absolute()),
            "output_checkpoint_sha256": checkpoint_hash,
            "training": run_receipt,
            "serialized_checkpoint_validation": serialized,
            "gates": gates,
            "accepted_marker_written": status == "accepted",
        }
        receipt = {**core, "receipt_sha256": canonical_sha256(core)}
        phase = f"{status}_status_publication"
        receipt_path, receipt_file_hash = inherited._publish_status(
            output_directory,
            status=status,
            receipt=receipt,
            directory_guard=output_guard,
        )
        return {
            "mode": "execute",
            "status": status,
            "checkpoint_path": str(checkpoint_path.absolute()),
            "checkpoint_sha256": checkpoint_hash,
            "receipt_path": str(receipt_path.absolute()),
            "receipt_file_sha256": receipt_file_hash,
            "receipt_sha256": receipt["receipt_sha256"],
            "gates": gates,
        }
    except Exception as error:
        if isinstance(error, inherited._CheckpointPublicationHandoffError):
            checkpoint_path = error.checkpoint_path
            checkpoint_hash = error.checkpoint_sha256
            checkpoint_guard = error.checkpoint_guard
            checkpoint_readback = error.checkpoint_readback
            error = error.cause
        exception_phase = (
            progress.failure_phase
            if phase == "two_stage_actor_only_updates"
            else phase
        )
        if progress.optimizer_steps_completed >= 1:
            if (
                phase == "checkpoint_exclusive_publication"
                and checkpoint_guard is None
            ):
                return _publish_failure_status(
                    output_directory,
                    execution_spec_path=execution_spec_path,
                    execution_spec_sha256=execution_spec_sha256,
                    phase=exception_phase,
                    error=error,
                    directory_guard=output_guard,
                    optimizer_steps_completed=progress.optimizer_steps_completed,
                )
            return _publish_post_step_rejection(
                output_directory,
                progress=progress,
                source_hashes=loaded["source_hashes"],
                execution_spec_path=execution_spec_path,
                execution_spec_sha256=execution_spec_sha256,
                phase=exception_phase,
                error=error,
                directory_guard=output_guard,
                existing_checkpoint_path=checkpoint_path,
                existing_checkpoint_sha256=checkpoint_hash,
                existing_checkpoint_guard=checkpoint_guard,
                existing_checkpoint_readback=checkpoint_readback,
                existing_metadata=(metadata if checkpoint_path is not None else None),
            )
        return _publish_failure_status(
            output_directory,
            execution_spec_path=execution_spec_path,
            execution_spec_sha256=execution_spec_sha256,
            phase=exception_phase,
            error=error,
            directory_guard=output_guard,
            checkpoint_path=checkpoint_path,
            checkpoint_sha256=checkpoint_hash,
            optimizer_steps_completed=progress.optimizer_steps_completed,
        )
    finally:
        if checkpoint_guard is not None:
            checkpoint_guard.close()
        output_guard.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--output-receipt", type=Path, required=True)
    execute_parser = commands.add_parser("execute")
    execute_parser.add_argument("--execution-spec", type=Path, required=True)
    execute_parser.add_argument("--execution-spec-sha256", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = (
        prepare(output_receipt=args.output_receipt)
        if args.mode == "prepare"
        else execute(
            execution_spec=args.execution_spec,
            execution_spec_sha256=args.execution_spec_sha256,
        )
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False))
    if args.mode == "prepare":
        return 0
    status = result.get("status")
    if status == "accepted":
        return 0
    if status == "rejected":
        return 2
    raise RuntimeError("execute returned no publishable terminal status")


if __name__ == "__main__":
    raise SystemExit(main())
