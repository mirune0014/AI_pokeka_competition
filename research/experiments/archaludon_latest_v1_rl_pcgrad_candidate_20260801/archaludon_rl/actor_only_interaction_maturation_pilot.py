"""Audited iteration-007 frozen-readout interaction-maturation boundary.

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
import stat
import statistics
import struct
from typing import Any, Iterable, Mapping, Sequence

import torch

from . import conservative_ppo_pilot as inherited
from . import actor_only_two_stage_pilot as predecessor
from .frozen_sources import find_repo_root, sha256_file
from .model import ModelConfig, ResidualActorCritic, _validate_metadata, checkpoint_metadata
from .train_ppo import PPOConfig, _torch_behavior_anchor_kl, _torch_behavior_distribution


PLAN_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_007_frozen_readout_interaction_maturation_implementation_plan.json"
)
PLAN_SHA256 = "6214B61FBA4D702A2C1FBFCBFA7912288B621DF0EAF21183AA0AFAAD809F99DF"
PLAN_SCHEMA_VERSION = (
    "archaludon-rl-frozen-readout-interaction-maturation-implementation-plan-v1"
)
PLAN_ID = "phase1-iteration-007-frozen-readout-interaction-maturation-20260801"
CORRECTION_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_007_frozen_readout_interaction_maturation_plan_correction_v1.json"
)
CORRECTION_SHA256 = "C848D59B999F56FB184259180CA4B1AC98D63EA317D90D0F790BEC4271F41D09"
CORRECTION_SCHEMA_VERSION = (
    "archaludon-rl-frozen-readout-interaction-maturation-plan-correction-v1"
)
CORRECTION_ID = "phase1-iteration-007-contract-clarification-20260801"
CORRECTION_V2_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_007_frozen_readout_interaction_maturation_plan_correction_v2.json"
)
CORRECTION_V2_SHA256 = "20FBE4B674FABBF4A9B0317C9F2ACF6612677566383532E0101A00D33CCB9184"
CORRECTION_V2_SCHEMA_VERSION = (
    "archaludon-rl-frozen-readout-interaction-maturation-plan-correction-v2"
)
CORRECTION_V2_ID = "phase1-iteration-007-post-audit-clarification-20260801"
PREPARE_AUDIT_REMEDIATION_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_007_prepare_audit_remediation_v1.json"
)
PREPARE_AUDIT_REMEDIATION_SHA256 = (
    "98D01B79F02AD7C01AFCE2DE05E177362D635734156A490F84DFBB8660CE726E"
)
PREPARE_AUDIT_REMEDIATION_SCHEMA_VERSION = (
    "archaludon-rl-iteration-007-prepare-audit-remediation-v1"
)
PREPARE_AUDIT_REMEDIATION_ID = (
    "phase1-iteration-007-prepare-code-audit-remediation-20260801"
)
PREPARE_AUDIT_REMEDIATION_V2_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_007_prepare_audit_remediation_v2.json"
)
PREPARE_AUDIT_REMEDIATION_V2_SHA256 = (
    "BD675A1DF53587A0E62270EBED46F1EA3D3531918F22B7F82C9063A3DCB612C0"
)
PREPARE_AUDIT_REMEDIATION_V2_SCHEMA_VERSION = (
    "archaludon-rl-iteration-007-prepare-audit-remediation-v2"
)
PREPARE_AUDIT_REMEDIATION_V2_ID = (
    "phase1-iteration-007-production-path-test-remediation-20260801"
)
PREPARE_AUDIT_REMEDIATION_V3_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_007_prepare_audit_remediation_v3.json"
)
PREPARE_AUDIT_REMEDIATION_V3_SHA256 = (
    "5D437C38386C7293E1EA6D9F3EE72766635EEB3E381BB982CAE3E6409C0E509E"
)
PREPARE_AUDIT_REMEDIATION_V3_SCHEMA_VERSION = (
    "archaludon-rl-iteration-007-prepare-audit-remediation-v3"
)
PREPARE_AUDIT_REMEDIATION_V3_ID = (
    "phase1-iteration-007-directional-membership-binding-fix-20260801"
)
PREPARE_AUDIT_REMEDIATION_V4_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_007_prepare_audit_remediation_v4.json"
)
PREPARE_AUDIT_REMEDIATION_V4_SHA256 = (
    "B92D03A1715BC1FF4DBB98EEBE28F8065D4A9E40CD977A6A6DA261A89295A39F"
)
PREPARE_AUDIT_REMEDIATION_V4_SCHEMA_VERSION = (
    "archaludon-rl-iteration-007-prepare-audit-remediation-v4"
)
PREPARE_AUDIT_REMEDIATION_V4_ID = (
    "phase1-iteration-007-terminal-artifact-allowlist-fix-20260801"
)
PREPARE_AUDIT_REMEDIATION_V5_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_007_prepare_audit_remediation_v5.json"
)
PREPARE_AUDIT_REMEDIATION_V5_SHA256 = (
    "79832D0DE952FA8B7F31AF203AAD71492982ADF89F675E707D0AEA0B3FB691BE"
)
PREPARE_AUDIT_REMEDIATION_V5_SCHEMA_VERSION = (
    "archaludon-rl-iteration-007-prepare-audit-remediation-v5"
)
PREPARE_AUDIT_REMEDIATION_V5_ID = (
    "phase1-iteration-007-measurement-timing-semantic-validation-fix-20260801"
)
PREPARE_AUDIT_REMEDIATION_V6_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_007_prepare_audit_remediation_v6.json"
)
PREPARE_AUDIT_REMEDIATION_V6_SHA256 = (
    "7488ED2364A72EBD67AC09CB3A762B025FDBC3874F09EB150C4010AA9AE82050"
)
PREPARE_AUDIT_REMEDIATION_V6_SCHEMA_VERSION = (
    "archaludon-rl-iteration-007-prepare-audit-remediation-v6"
)
PREPARE_AUDIT_REMEDIATION_V6_ID = (
    "phase1-iteration-007-windows-held-checkpoint-inventory-fix-20260801"
)
PREPARE_AUDIT_REMEDIATION_V7_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_007_prepare_audit_remediation_v7.json"
)
PREPARE_AUDIT_REMEDIATION_V7_SHA256 = (
    "708EBF2320AE6F9850151C6A0AF93453AE7695A0C99240905557A5FE257CFACB"
)
PREPARE_AUDIT_REMEDIATION_V7_SCHEMA_VERSION = (
    "archaludon-rl-iteration-007-prepare-audit-remediation-v7"
)
PREPARE_AUDIT_REMEDIATION_V7_ID = (
    "phase1-iteration-007-held-private-staging-alias-fix-20260801"
)
PREPARE_AUDIT_REMEDIATION_V8_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_007_prepare_audit_remediation_v8.json"
)
PREPARE_AUDIT_REMEDIATION_V8_SHA256 = (
    "C945E85A725493C2708DB58E26CFF45CF16A6B45A98B13119812280B63E3DA04"
)
PREPARE_AUDIT_REMEDIATION_V8_SCHEMA_VERSION = (
    "archaludon-rl-iteration-007-prepare-audit-remediation-v8"
)
PREPARE_AUDIT_REMEDIATION_V8_ID = (
    "phase1-iteration-007-cleanup-share-and-entry-type-test-fix-20260801"
)

IMPLEMENTATION_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl_interaction_maturation_candidate_20260801"
)
SOURCE_IMPLEMENTATION_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl_actor_bootstrap_candidate_20260801"
)
SOURCE_IMPLEMENTATION_FILE_COUNT = 51
SOURCE_IMPLEMENTATION_SHA256 = (
    "2E6F7D1F134F9571C0064910BD6C0A56F8D39AC0965F8F36F4C9938D4D29DF35"
)
SOURCE_CONSERVATIVE_PILOT_SHA256 = (
    "43CEC751457ED0329D4A8E10CF6491A13BF78BC28F89154A3BC8056371FD1DCC"
)
SOURCE_TWO_STAGE_PILOT_SHA256 = (
    "9FD277200591C3485072EBED346135456D99206DDEB2BF046D1E09BC93C4AA0F"
)

INPUT_CHECKPOINT_RELATIVE_PATH = inherited.INPUT_CHECKPOINT_RELATIVE_PATH
INPUT_CHECKPOINT_SHA256 = inherited.INPUT_CHECKPOINT_SHA256
MANIFEST_RELATIVE_PATH = inherited.MANIFEST_RELATIVE_PATH
MANIFEST_SHA256 = inherited.MANIFEST_SHA256
DATASET_SHA256 = inherited.DATASET_SHA256
EXPECTED_ON_POLICY_ROWS = 830
FIXED_ADVANTAGES_SHA256 = (
    "B7F77DEBE545FDD5B7767C909E185904A52F161B6253D821950E6FDE6A79E53B"
)
FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256 = (
    "BF402ED36ECD78905597F562E8987927C2D74FD5AEE390F1D1E1426CE3D1DA98"
)

PREPARE_SOURCE_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl_actor_bootstrap_candidate_20260801/"
    "test_outputs/phase1_iteration_006_prepare_v3/pretraining_probe_receipt.json"
)
PREPARE_SOURCE_FILE_SHA256 = (
    "1DE8718F771BBBDB08712666EA1BFBFA52B34260EC76178B5D0B59C232B14B52"
)
PREPARE_SOURCE_RECEIPT_SHA256 = (
    "B2758162F79F6CDF892576DF963ED375FBA372F0919FE226A69510907BC3E385"
)

PARENT_RESULT_RELATIVE_PATH = PurePosixPath(
    "research/experiments/archaludon_latest_v1_rl/PHASE1_ITERATION_006_RESULT.md"
)
PARENT_RESULT_SHA256 = "F26BDF73AE3AE9ADBD19BCCCB8D06A36B62277C14153D8895274B92E8CB4CF77"
PARENT_REJECTED_RECEIPT_RELATIVE_PATH = PurePosixPath(
    "_local_generated/analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_006_"
    "actor_only_two_stage_20260801/rejected_receipt.json"
)
PARENT_REJECTED_RECEIPT_FILE_SHA256 = (
    "FF97079BB4CD071A3548A830AC516FE2E30FC70CCCF09EBFC57F1605421A950B"
)
PARENT_REJECTED_RECEIPT_SHA256 = (
    "9F61AC21FABF231FB3B4D5BF37BC1BB0CCFBFF0F15A5342708F91AB8D29019C0"
)
REJECTED_CHECKPOINT_RELATIVE_PATH = PurePosixPath(
    "_local_generated/analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_006_"
    "actor_only_two_stage_20260801/candidate.pt"
)
REJECTED_CHECKPOINT_SHA256 = (
    "C1F9B0D4CEAFD0B481F9E1C517F5B56A2490DF9AF2EEA1DD8B8E5412596FA12B"
)

PREPARE_OUTPUT_DIRECTORY_PREFIX = "phase1_iteration_007_prepare"
PREPARE_OUTPUT_FILENAME = "pretraining_probe_receipt.json"
PREPARE_RECEIPT_SCHEMA_VERSION = "frozen-readout-interaction-maturation-prepare-v4"
EXECUTION_SPEC_SCHEMA_VERSION = "actor-only-interaction-maturation-execution-spec-v10"
EXECUTION_RECEIPT_SCHEMA_VERSION = "frozen-readout-interaction-maturation-execution-receipt-v1"
EXECUTION_SPEC_TOP_LEVEL_KEYS = (
    "schema_version",
    "implementation_plan_path", "implementation_plan_sha256",
    "plan_correction_path", "plan_correction_sha256",
    "plan_correction_v2_path", "plan_correction_v2_sha256",
    "prepare_audit_remediation_path", "prepare_audit_remediation_sha256",
    "prepare_audit_remediation_v2_path", "prepare_audit_remediation_v2_sha256",
    "prepare_audit_remediation_v3_path", "prepare_audit_remediation_v3_sha256",
    "prepare_audit_remediation_v4_path", "prepare_audit_remediation_v4_sha256",
    "prepare_audit_remediation_v5_path", "prepare_audit_remediation_v5_sha256",
    "prepare_audit_remediation_v6_path", "prepare_audit_remediation_v6_sha256",
    "prepare_audit_remediation_v7_path", "prepare_audit_remediation_v7_sha256",
    "prepare_audit_remediation_v8_path", "prepare_audit_remediation_v8_sha256",
    "parent_result_path", "parent_result_sha256",
    "prepare_receipt_path", "prepare_receipt_file_sha256",
    "prepare_receipt_sha256", "implementation_path",
    "implementation_snapshot_sha256", "input_checkpoint_path",
    "input_checkpoint_sha256", "forbidden_rejected_checkpoint_sha256s",
    "manifest_path", "manifest_sha256", "dataset_sha256",
    "fixed_advantages_sha256", "fixed_behavior_logprobabilities_sha256",
    "runtime_thread_receipt", "training_contract", "diagnostic_contract",
    "safety_gates", "terminal_offline_acceptance", "output_directory",
)
EXECUTION_SPEC_V9_TOP_LEVEL_KEYS = tuple(
    name
    for name in EXECUTION_SPEC_TOP_LEVEL_KEYS
    if name not in {
        "prepare_audit_remediation_v8_path",
        "prepare_audit_remediation_v8_sha256",
    }
)
EXECUTION_SPEC_V8_TOP_LEVEL_KEYS = tuple(
    name
    for name in EXECUTION_SPEC_V9_TOP_LEVEL_KEYS
    if name not in {
        "prepare_audit_remediation_v7_path",
        "prepare_audit_remediation_v7_sha256",
    }
)
EXECUTION_SPEC_V7_TOP_LEVEL_KEYS = tuple(
    name
    for name in EXECUTION_SPEC_V8_TOP_LEVEL_KEYS
    if name not in {
        "prepare_audit_remediation_v6_path",
        "prepare_audit_remediation_v6_sha256",
    }
)
EXECUTION_SPEC_V6_TOP_LEVEL_KEYS = tuple(
    name
    for name in EXECUTION_SPEC_V7_TOP_LEVEL_KEYS
    if name not in {
        "prepare_audit_remediation_v5_path",
        "prepare_audit_remediation_v5_sha256",
    }
)
EXECUTION_SPEC_V5_TOP_LEVEL_KEYS = tuple(
    name
    for name in EXECUTION_SPEC_V6_TOP_LEVEL_KEYS
    if name not in {
        "prepare_audit_remediation_v4_path",
        "prepare_audit_remediation_v4_sha256",
    }
)
EXECUTION_SPEC_V4_TOP_LEVEL_KEYS = tuple(
    name
    for name in EXECUTION_SPEC_V5_TOP_LEVEL_KEYS
    if name not in {
        "prepare_audit_remediation_v3_path",
        "prepare_audit_remediation_v3_sha256",
    }
)
EXECUTION_SPEC_V3_TOP_LEVEL_KEYS = tuple(
    name
    for name in EXECUTION_SPEC_V4_TOP_LEVEL_KEYS
    if name not in {
        "prepare_audit_remediation_v2_path",
        "prepare_audit_remediation_v2_sha256",
    }
)
APPROVED_OUTPUT_RELATIVE_PATH = PurePosixPath(
    "_local_generated/analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_007_"
    "frozen_readout_interaction_maturation_20260801"
)
APPROVED_PREPARE_RELATIVE_PATH = (
    IMPLEMENTATION_RELATIVE_PATH
    / "test_outputs/phase1_iteration_007_prepare_v4/pretraining_probe_receipt.json"
)
AUDIT_BLOCKED_PREPARE_V1_RELATIVE_PATH = (
    IMPLEMENTATION_RELATIVE_PATH
    / "test_outputs/phase1_iteration_007_prepare_v1/pretraining_probe_receipt.json"
)
AUDIT_BLOCKED_PREPARE_V1_FILE_SHA256 = (
    "4C47DC2921A9BBB3018FFAE950BD1ED9F874FF32EBFE5425B5364C9837F888F2"
)
AUDIT_BLOCKED_PREPARE_V1_RECEIPT_SHA256 = (
    "60D20EF6EE8B3725349347E4ED255C9CF2CF8744C390AF5A925504FED24D3ACA"
)
AUDIT_BLOCKED_PREPARE_V2_RELATIVE_PATH = (
    IMPLEMENTATION_RELATIVE_PATH
    / "test_outputs/phase1_iteration_007_prepare_v2/pretraining_probe_receipt.json"
)
AUDIT_BLOCKED_PREPARE_V2_FILE_SHA256 = (
    "7320BC7C57A7B344F2A250135F30DBC93205C6ADFB7F25912A8B482F7B7F6E09"
)
AUDIT_BLOCKED_PREPARE_V2_RECEIPT_SHA256 = (
    "1E0D192794CCF2B524E7694DCA24B959644111C2E28D8A4BDF2CFFFAA7F151FB"
)
AUDIT_BLOCKED_PREPARE_V3_RELATIVE_PATH = (
    IMPLEMENTATION_RELATIVE_PATH
    / "test_outputs/phase1_iteration_007_prepare_v3/pretraining_probe_receipt.json"
)
AUDIT_BLOCKED_PREPARE_V3_FILE_SHA256 = (
    "8D89BC1EF26345DE567623B76F9070DB43FB971770818DE7632D94C66D306AB1"
)
AUDIT_BLOCKED_PREPARE_V3_RECEIPT_SHA256 = (
    "A9202B2A5F0DCD06FAA0679BDBB00B7CF5A1FBC78C1D801AB67F718E19E2E9C2"
)
ITERATION005_REJECTED_CHECKPOINT_SHA256 = (
    "E7D0CA4DCEEBE33C8043D3C8A45DD9119CFE0E06ACC58F343E9A60BB7F787088"
)
FORBIDDEN_REJECTED_CHECKPOINT_SHA256S = (
    ITERATION005_REJECTED_CHECKPOINT_SHA256,
    REJECTED_CHECKPOINT_SHA256,
)
NONFINITE_SENTINEL_SCHEMA_VERSION = "nonfinite-float-sentinel-v1"

ROW_MAP_SCHEMA_VERSION = "sampled-option-type-row-map-v1"
MEMBERSHIP_SCHEMA_VERSION = "sampled-option-type-membership-v1"
ROW_MAP_SHA256 = "F0BEBA7DAF76FC07E72B2830EE51D6216367FC517B91AE61795C61A41FD5E8BE"
DEADBAND_TAU = 1e-7
STAGE1_TRAINABLE_NAMES = (
    "residual_head.2.weight",
    "residual_head.2.bias",
)
STAGE2_TRAINABLE_NAMES = (
    "residual_head.0.weight",
    "residual_head.0.bias",
)
OPTIMIZER_PARAMETER_NAMES = (
    "residual_head.0.weight",
    "residual_head.0.bias",
    "residual_head.2.weight",
    "residual_head.2.bias",
)
STAGE2_UPDATES = 32
TOTAL_OPTIMIZER_STEPS = 33
DIAGNOSTIC_UPDATE_ORDINALS = (1, 2, 4, 8, 16, 32)
DIRECTIONAL_MEMBERSHIP_KEYS = (
    "negative_target_ordinals",
    "positive_normalized_teacher_and_sampled_end_ordinals",
    "positive_raw_teacher_and_sampled_end_ordinals",
    "teacher_end_and_sampled_end_ordinals",
    "teacher_end_ordinals",
)
DIRECTIONAL_MEMBERSHIP_COUNTS = {
    "negative_target_ordinals": 4,
    "positive_normalized_teacher_and_sampled_end_ordinals": 20,
    "positive_raw_teacher_and_sampled_end_ordinals": 31,
    "teacher_end_and_sampled_end_ordinals": 41,
    "teacher_end_ordinals": 43,
}
NEGATIVE_TARGET_ORDINALS = (158, 260, 547, 812)
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
    epochs=33,
)
ADAM_CONFIG: dict[str, Any] = {
    "name": "Adam",
    "fresh_state": True,
    "single_object_across_stages": True,
    "reset_between_stages": False,
    "parameter_names_exact": list(OPTIMIZER_PARAMETER_NAMES),
    "learning_rate": 0.0001,
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
    "selected_hypothesis", "hypothesis_falsifier",
    "immutable_inputs",
    "isolated_implementation",
    "training_contract",
    "diagnostic_contract", "safety_gates", "terminal_offline_acceptance",
    "prepare_receipt_must_bind",
    "implementation_tests",
    "forbidden_changes",
    "output_semantics",
    "post_rejection_action_if_falsified", "execution_stop_rule",
}


def canonical_json_bytes(value: Any, *, newline: bool = False) -> bytes:
    return inherited.canonical_json_bytes(value, newline=newline)


def canonical_sha256(value: Any) -> str:
    return inherited.canonical_sha256(value)


def _contract_bindings() -> dict[str, str]:
    """The eleven execution-authoritative path/hash pairs."""

    return {
        "implementation_plan_path": PLAN_RELATIVE_PATH.as_posix(),
        "implementation_plan_sha256": PLAN_SHA256,
        "plan_correction_path": CORRECTION_RELATIVE_PATH.as_posix(),
        "plan_correction_sha256": CORRECTION_SHA256,
        "plan_correction_v2_path": CORRECTION_V2_RELATIVE_PATH.as_posix(),
        "plan_correction_v2_sha256": CORRECTION_V2_SHA256,
        "prepare_audit_remediation_path": (
            PREPARE_AUDIT_REMEDIATION_RELATIVE_PATH.as_posix()
        ),
        "prepare_audit_remediation_sha256": PREPARE_AUDIT_REMEDIATION_SHA256,
        "prepare_audit_remediation_v2_path": (
            PREPARE_AUDIT_REMEDIATION_V2_RELATIVE_PATH.as_posix()
        ),
        "prepare_audit_remediation_v2_sha256": (
            PREPARE_AUDIT_REMEDIATION_V2_SHA256
        ),
        "prepare_audit_remediation_v3_path": (
            PREPARE_AUDIT_REMEDIATION_V3_RELATIVE_PATH.as_posix()
        ),
        "prepare_audit_remediation_v3_sha256": (
            PREPARE_AUDIT_REMEDIATION_V3_SHA256
        ),
        "prepare_audit_remediation_v4_path": (
            PREPARE_AUDIT_REMEDIATION_V4_RELATIVE_PATH.as_posix()
        ),
        "prepare_audit_remediation_v4_sha256": (
            PREPARE_AUDIT_REMEDIATION_V4_SHA256
        ),
        "prepare_audit_remediation_v5_path": (
            PREPARE_AUDIT_REMEDIATION_V5_RELATIVE_PATH.as_posix()
        ),
        "prepare_audit_remediation_v5_sha256": (
            PREPARE_AUDIT_REMEDIATION_V5_SHA256
        ),
        "prepare_audit_remediation_v6_path": (
            PREPARE_AUDIT_REMEDIATION_V6_RELATIVE_PATH.as_posix()
        ),
        "prepare_audit_remediation_v6_sha256": (
            PREPARE_AUDIT_REMEDIATION_V6_SHA256
        ),
        "prepare_audit_remediation_v7_path": (
            PREPARE_AUDIT_REMEDIATION_V7_RELATIVE_PATH.as_posix()
        ),
        "prepare_audit_remediation_v7_sha256": (
            PREPARE_AUDIT_REMEDIATION_V7_SHA256
        ),
        "prepare_audit_remediation_v8_path": (
            PREPARE_AUDIT_REMEDIATION_V8_RELATIVE_PATH.as_posix()
        ),
        "prepare_audit_remediation_v8_sha256": (
            PREPARE_AUDIT_REMEDIATION_V8_SHA256
        ),
    }


def _authoritative_float32_probability_vector(
    values: Sequence[Any], *, label: str
) -> tuple[list[float], bytes]:
    """Return the sole metric domain and its exact contiguous CPU bytes.

    JSON numbers with precision not preserved by float32 are rejected even
    when they would produce the same bytes as an otherwise valid vector.
    """

    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError(f"{label} must be a nonempty probability vector")
    supplied: list[float] = []
    for index, value in enumerate(values):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise ValueError(f"{label}[{index}] is not a finite number")
        supplied.append(float(value))
    tensor = torch.tensor(supplied, dtype=torch.float32, device="cpu").contiguous()
    round_tripped = [float(value) for value in tensor.tolist()]
    if any(original != rounded for original, rounded in zip(supplied, round_tripped)):
        raise ValueError(f"{label} is not exactly representable in float32")
    return round_tripped, _tensor_bytes(tensor)


def _nonfinite_sentinel(value: float, *, dtype: str = "float64") -> dict[str, str]:
    numeric = float(value)
    if math.isnan(numeric):
        classification = "nan"
    elif numeric > 0.0 and math.isinf(numeric):
        classification = "positive_infinity"
    elif numeric < 0.0 and math.isinf(numeric):
        classification = "negative_infinity"
    else:
        raise ValueError("nonfinite sentinel requires NaN or Infinity")
    if dtype == "float32":
        raw = struct.pack("<f", numeric)
    elif dtype == "float64":
        raw = struct.pack("<d", numeric)
    else:
        raise ValueError("nonfinite sentinel dtype mismatch")
    return {
        "schema_version": NONFINITE_SENTINEL_SCHEMA_VERSION,
        "classification": classification,
        "dtype": dtype,
        "raw_bytes_hex": raw.hex().upper(),
    }


def encode_nonfinite_for_canonical_json(
    value: Any, *, path: str = "$"
) -> tuple[Any, dict[str, Any] | None]:
    locations: list[dict[str, Any]] = []

    def visit(item: Any, current_path: str) -> Any:
        if isinstance(item, float) and not math.isfinite(item):
            sentinel = _nonfinite_sentinel(item)
            raw = bytes.fromhex(sentinel["raw_bytes_hex"])
            locations.append(
                {
                    "path": current_path,
                    "count": 1,
                    "classification": sentinel["classification"],
                    "dtype": sentinel["dtype"],
                    "collection_byte_sha256": hashlib.sha256(raw).hexdigest().upper(),
                }
            )
            return sentinel
        if isinstance(item, Mapping):
            return {
                str(key): visit(child, f"{current_path}/{str(key).replace('~', '~0').replace('/', '~1')}")
                for key, child in item.items()
            }
        if isinstance(item, (list, tuple)):
            return [visit(child, f"{current_path}/{index}") for index, child in enumerate(item)]
        return item

    encoded = visit(value, path)
    evidence = None
    if locations:
        evidence = {
            "schema_version": "nonfinite-location-evidence-v1",
            "count": len(locations),
            "locations": locations,
        }
    return encoded, evidence


def validate_nonfinite_encoding(
    value: Any,
    *,
    evidence: Mapping[str, Any] | None,
    accepted_receipt: bool,
) -> None:
    _, rebuilt = encode_nonfinite_for_canonical_json(value)
    if rebuilt is not None:
        raise ValueError("untagged NaN or Infinity is forbidden")
    found: list[tuple[str, Mapping[str, Any]]] = []

    def visit(item: Any, current_path: str) -> None:
        if isinstance(item, Mapping) and item.get("schema_version") == NONFINITE_SENTINEL_SCHEMA_VERSION:
            if set(item) != {"schema_version", "classification", "dtype", "raw_bytes_hex"}:
                raise ValueError("malformed nonfinite sentinel keys")
            if item["classification"] not in {"nan", "positive_infinity", "negative_infinity"}:
                raise ValueError("malformed nonfinite sentinel classification")
            if item["dtype"] not in {"float32", "float64"}:
                raise ValueError("malformed nonfinite sentinel dtype")
            raw = bytes.fromhex(str(item["raw_bytes_hex"]))
            if len(raw) != (4 if item["dtype"] == "float32" else 8):
                raise ValueError("malformed nonfinite sentinel byte length")
            numeric = struct.unpack("<f" if item["dtype"] == "float32" else "<d", raw)[0]
            expected = _nonfinite_sentinel(numeric, dtype=str(item["dtype"]))
            if dict(item) != expected:
                raise ValueError("nonfinite sentinel raw bytes disagree")
            found.append((current_path, item))
            return
        if isinstance(item, Mapping):
            for key, child in item.items():
                visit(child, f"{current_path}/{str(key).replace('~', '~0').replace('/', '~1')}")
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, f"{current_path}/{index}")

    visit(value, "$")
    if accepted_receipt and found:
        raise ValueError("accepted receipt must not contain nonfinite sentinels")
    if not found:
        if evidence is not None:
            raise ValueError("nonfinite evidence exists without a sentinel")
        return
    expected_locations = []
    for found_path, sentinel in found:
        raw = bytes.fromhex(str(sentinel["raw_bytes_hex"]))
        expected_locations.append(
            {
                "path": found_path,
                "count": 1,
                "classification": sentinel["classification"],
                "dtype": sentinel["dtype"],
                "collection_byte_sha256": hashlib.sha256(raw).hexdigest().upper(),
            }
        )
    expected_evidence = {
        "schema_version": "nonfinite-location-evidence-v1",
        "count": len(expected_locations),
        "locations": expected_locations,
    }
    if dict(evidence or {}) != expected_evidence:
        raise ValueError("nonfinite sentinel path/count/hash evidence mismatch")


def _receipt_core_with_nonfinite_evidence(
    core: Mapping[str, Any], *, status: str
) -> dict[str, Any]:
    encoded, evidence = encode_nonfinite_for_canonical_json(dict(core))
    validate_nonfinite_encoding(
        encoded,
        evidence=evidence,
        accepted_receipt=status == "accepted",
    )
    if evidence is not None:
        encoded = {**encoded, "nonfinite_evidence": evidence}
    return encoded


def _repo_path(relative: PurePosixPath) -> Path:
    return find_repo_root() / Path(*relative.parts)


def _strict_sha256(value: Any, *, label: str) -> str:
    return inherited._strict_sha256(value, label=label)


def _exact_keys(value: Any, expected: set[str], *, label: str) -> Mapping[str, Any]:
    return inherited._require_exact_keys(value, expected, label=label)


def _load_plan() -> dict[str, Any]:
    plan = inherited._load_hashed_json(
        _repo_path(PLAN_RELATIVE_PATH), PLAN_SHA256, label="iteration-007 plan"
    )
    top = _exact_keys(plan, _PLAN_TOP_KEYS, label="iteration-007 plan")
    if top["schema_version"] != PLAN_SCHEMA_VERSION or top["plan_id"] != PLAN_ID:
        raise ValueError("iteration-007 plan identity mismatch")
    if top["strength_claim_allowed"] is not False:
        raise ValueError("iteration-007 plan must forbid a strength claim")
    training = top["training_contract"]
    expected_ppo = {
        "gamma": 0.99,
        "gae_lambda": 0.95,
        "clip_ratio": 0.1,
        "value_coef": 0.0,
        "entropy_coef": 0.0,
        "anchor_kl_coefficient": 0.1,
        "anchor_kl_adaptation": False,
        "gradient_clip": 0.25,
        "full_batch_rows": 830,
        "total_optimizer_steps": 33,
    }
    if training["ppo_config"] != expected_ppo:
        raise ValueError("iteration-007 PPO contract mismatch")
    if top["training_contract"]["optimizer"] != ADAM_CONFIG:
        raise ValueError("iteration-007 Adam contract mismatch")
    if training["stage_1"]["trainable_parameter_names_exact"] != list(
        STAGE1_TRAINABLE_NAMES
    ):
        raise ValueError("iteration-007 Stage-1 trainability mismatch")
    if training["stage_2"]["trainable_parameter_names_exact"] != list(
        STAGE2_TRAINABLE_NAMES
    ):
        raise ValueError("iteration-007 Stage-2 trainability mismatch")
    if (
        training["stage_1"]["optimizer_step_count"] != 1
        or training["stage_2"]["optimizer_step_count"] != STAGE2_UPDATES
        or training["stage_2"]["diagnostic_update_ordinals"]
        != list(DIAGNOSTIC_UPDATE_ORDINALS)
        or training["stage_2"]["no_directional_or_futility_early_stop_before_terminal"]
        is not True
    ):
        raise ValueError("iteration-007 update schedule mismatch")
    if top["output_semantics"]["same_iteration_retry"] is not False:
        raise ValueError("iteration-007 must forbid same-iteration retry")
    return dict(top)


def _load_correction_iteration006_legacy() -> dict[str, Any]:
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


def _load_correction() -> dict[str, Any]:
    correction = inherited._load_hashed_json(
        _repo_path(CORRECTION_RELATIVE_PATH),
        CORRECTION_SHA256,
        label="iteration-007 plan correction",
    )
    top = _exact_keys(
        correction,
        {
            "schema_version", "correction_id", "base_plan", "authority",
            "hypothesis_change", "training_data_or_objective_change",
            "clarifications", "required_new_tests",
        },
        label="iteration-007 plan correction",
    )
    if (
        top["schema_version"] != CORRECTION_SCHEMA_VERSION
        or top["correction_id"] != CORRECTION_ID
        or top["base_plan"] != {
            "path": PLAN_RELATIVE_PATH.as_posix(),
            "sha256": PLAN_SHA256,
        }
        or top["hypothesis_change"] is not False
        or top["training_data_or_objective_change"] is not False
    ):
        raise ValueError("iteration-007 correction identity mismatch")
    clarifications = top["clarifications"]
    expected_names = {
        "optimizer_execution_scope", "single_adam_structure",
        "gate_phase_separation", "derived_metric_recomputation",
        "exception_and_checkpoint_contract", "canonical_nonfinite_encoding",
        "execution_spec_contract", "value_identity_contract",
        "inherited_end_gate_exact", "gae_recomputation_scope",
    }
    if set(clarifications) != expected_names:
        raise ValueError("iteration-007 correction clarification set mismatch")
    spec_contract = clarifications["execution_spec_contract"]
    if (
        spec_contract["schema_version"]
        != "actor-only-interaction-maturation-execution-spec-v1"
        or spec_contract["output_directory_exact"]
        != APPROVED_OUTPUT_RELATIVE_PATH.as_posix()
        or spec_contract["prepare_output_path_exact"]
        != AUDIT_BLOCKED_PREPARE_V1_RELATIVE_PATH.as_posix()
        or spec_contract["forbidden_rejected_checkpoint_sha256s_exact"]
        != list(FORBIDDEN_REJECTED_CHECKPOINT_SHA256S)
    ):
        raise ValueError("iteration-007 corrected execution contract mismatch")
    adam = clarifications["single_adam_structure"]
    if (
        adam["parameter_group_count_exact"] != 1
        or adam["parameter_order_exact"] != list(OPTIMIZER_PARAMETER_NAMES)
        or adam["all_four_parameters_present_from_construction"] is not True
    ):
        raise ValueError("iteration-007 corrected Adam structure mismatch")
    nonfinite = clarifications["canonical_nonfinite_encoding"]
    if (
        nonfinite["canonical_json_allow_nan"] is not False
        or nonfinite["sentinel_schema_version"] != NONFINITE_SENTINEL_SCHEMA_VERSION
    ):
        raise ValueError("iteration-007 nonfinite encoding mismatch")
    end_gate = clarifications["inherited_end_gate_exact"]
    if (
        end_gate["negative_target_ordinals"] != [158, 260, 547, 812]
        or end_gate["positive_normalized_teacher_and_sampled_end_count"] != 20
        or end_gate["positive_raw_teacher_and_sampled_end_count"] != 31
        or end_gate["teacher_end_unique_argmax_count"] != 43
    ):
        raise ValueError("iteration-007 inherited END membership mismatch")
    return dict(top)


def _load_correction_v2() -> dict[str, Any]:
    correction = inherited._load_hashed_json(
        _repo_path(CORRECTION_V2_RELATIVE_PATH),
        CORRECTION_V2_SHA256,
        label="iteration-007 plan correction v2",
    )
    top = _exact_keys(
        correction,
        {
            "schema_version", "correction_id", "base_plan", "prior_correction",
            "authority", "hypothesis_change", "training_data_or_objective_change",
            "clarifications", "required_new_tests",
        },
        label="iteration-007 plan correction v2",
    )
    if (
        top["schema_version"] != CORRECTION_V2_SCHEMA_VERSION
        or top["correction_id"] != CORRECTION_V2_ID
        or top["base_plan"] != {
            "path": PLAN_RELATIVE_PATH.as_posix(), "sha256": PLAN_SHA256,
        }
        or top["prior_correction"] != {
            "path": CORRECTION_RELATIVE_PATH.as_posix(),
            "sha256": CORRECTION_SHA256,
        }
        or top["hypothesis_change"] is not False
        or top["training_data_or_objective_change"] is not False
    ):
        raise ValueError("iteration-007 correction v2 identity mismatch")
    if set(top["clarifications"]) != {
        "nonmilestone_recomputation_scope", "execution_spec_subobjects",
        "execution_spec_correction_chain",
        "probability_vector_validation", "stage_and_measurement_timing",
        "publication_identity_failure",
    }:
        raise ValueError("iteration-007 correction v2 clarification set mismatch")
    return dict(top)


def _validate_audit_blocked_prepare_v1() -> dict[str, Any]:
    path = _repo_path(AUDIT_BLOCKED_PREPARE_V1_RELATIVE_PATH)
    if sha256_file(path) != AUDIT_BLOCKED_PREPARE_V1_FILE_SHA256:
        raise ValueError("audit-blocked prepare v1 changed")
    blocked = inherited._load_hashed_json(
        path,
        AUDIT_BLOCKED_PREPARE_V1_FILE_SHA256,
        label="audit-blocked iteration-007 prepare v1",
    )
    core = dict(blocked)
    self_hash = _strict_sha256(
        core.pop("receipt_sha256", None), label="audit-blocked prepare v1 self-hash"
    )
    if (
        self_hash != AUDIT_BLOCKED_PREPARE_V1_RECEIPT_SHA256
        or canonical_sha256(core) != self_hash
        or blocked.get("schema_version")
        != "frozen-readout-interaction-maturation-prepare-v1"
    ):
        raise ValueError("audit-blocked prepare v1 identity mismatch")
    return dict(blocked)


def _validate_audit_blocked_prepare_v2() -> dict[str, Any]:
    path = _repo_path(AUDIT_BLOCKED_PREPARE_V2_RELATIVE_PATH)
    if sha256_file(path) != AUDIT_BLOCKED_PREPARE_V2_FILE_SHA256:
        raise ValueError("audit-blocked prepare v2 changed")
    blocked = inherited._load_hashed_json(
        path,
        AUDIT_BLOCKED_PREPARE_V2_FILE_SHA256,
        label="audit-blocked iteration-007 prepare v2",
    )
    core = dict(blocked)
    self_hash = _strict_sha256(
        core.pop("receipt_sha256", None), label="audit-blocked prepare v2 self-hash"
    )
    if (
        self_hash != AUDIT_BLOCKED_PREPARE_V2_RECEIPT_SHA256
        or canonical_sha256(core) != self_hash
        or blocked.get("schema_version")
        != "frozen-readout-interaction-maturation-prepare-v2"
    ):
        raise ValueError("audit-blocked prepare v2 identity mismatch")
    return dict(blocked)


def _validate_audit_blocked_prepare_v3() -> dict[str, Any]:
    path = _repo_path(AUDIT_BLOCKED_PREPARE_V3_RELATIVE_PATH)
    if sha256_file(path) != AUDIT_BLOCKED_PREPARE_V3_FILE_SHA256:
        raise ValueError("audit-blocked prepare v3 changed")
    blocked = inherited._load_hashed_json(
        path,
        AUDIT_BLOCKED_PREPARE_V3_FILE_SHA256,
        label="audit-blocked iteration-007 prepare v3",
    )
    core = dict(blocked)
    self_hash = _strict_sha256(
        core.pop("receipt_sha256", None), label="audit-blocked prepare v3 self-hash"
    )
    if (
        self_hash != AUDIT_BLOCKED_PREPARE_V3_RECEIPT_SHA256
        or canonical_sha256(core) != self_hash
        or blocked.get("schema_version")
        != "frozen-readout-interaction-maturation-prepare-v3"
        or blocked.get("implementation", {}).get("sha256")
        != "B8B51A5B7FA54A542CE32B56019F92018E2D734BC33C3FCB570DC0C938CA18CB"
    ):
        raise ValueError("audit-blocked prepare v3 identity mismatch")
    return dict(blocked)


def _load_prepare_audit_remediation() -> dict[str, Any]:
    remediation = inherited._load_hashed_json(
        _repo_path(PREPARE_AUDIT_REMEDIATION_RELATIVE_PATH),
        PREPARE_AUDIT_REMEDIATION_SHA256,
        label="iteration-007 prepare audit remediation",
    )
    top = _exact_keys(
        remediation,
        {
            "schema_version", "remediation_id", "base_plan",
            "plan_correction_v1", "plan_correction_v2", "authority",
            "hypothesis_change", "training_data_or_objective_change",
            "real_optimizer_execution_authorized", "audited_blocked_candidate",
            "required_code_changes", "replacement_prepare",
            "execution_spec_override", "verification_before_replacement_prepare",
            "forbidden", "stop_rule",
        },
        label="iteration-007 prepare audit remediation",
    )
    if (
        top["schema_version"] != PREPARE_AUDIT_REMEDIATION_SCHEMA_VERSION
        or top["remediation_id"] != PREPARE_AUDIT_REMEDIATION_ID
        or top["base_plan"]
        != {"path": PLAN_RELATIVE_PATH.as_posix(), "sha256": PLAN_SHA256}
        or top["plan_correction_v1"]
        != {"path": CORRECTION_RELATIVE_PATH.as_posix(), "sha256": CORRECTION_SHA256}
        or top["plan_correction_v2"]
        != {
            "path": CORRECTION_V2_RELATIVE_PATH.as_posix(),
            "sha256": CORRECTION_V2_SHA256,
        }
        or top["hypothesis_change"] is not False
        or top["training_data_or_objective_change"] is not False
        or top["real_optimizer_execution_authorized"] is not False
    ):
        raise ValueError("iteration-007 prepare remediation identity mismatch")
    blocked = top["audited_blocked_candidate"]
    if (
        blocked.get("path") != IMPLEMENTATION_RELATIVE_PATH.as_posix()
        or blocked.get("snapshot_file_count") != 53
        or blocked.get("snapshot_sha256")
        != "0BF5140E9759D8635F0B41DC1C7CEC20958F2B28E7F0BA5CF971A047A57EFFF6"
        or blocked.get("prepare_v1_path")
        != AUDIT_BLOCKED_PREPARE_V1_RELATIVE_PATH.as_posix()
        or blocked.get("prepare_v1_file_sha256")
        != AUDIT_BLOCKED_PREPARE_V1_FILE_SHA256
        or blocked.get("prepare_v1_receipt_sha256")
        != AUDIT_BLOCKED_PREPARE_V1_RECEIPT_SHA256
        or blocked.get("prepare_v1_status")
        != "AUDIT_BLOCKED_NOT_EXECUTION_AUTHORIZATION"
        or blocked.get("prepare_v1_must_remain_byte_exact") is not True
    ):
        raise ValueError("iteration-007 blocked prepare identity mismatch")
    required_paths = top["required_code_changes"]["exact_test_module_path"]
    if (
        required_paths.get("required")
        != (
            IMPLEMENTATION_RELATIVE_PATH
            / "tests/test_actor_only_interaction_maturation_pilot.py"
        ).as_posix()
        or required_paths.get("forbidden_after_remediation")
        != (
            IMPLEMENTATION_RELATIVE_PATH
            / "tests/test_actor_only_z_interaction_maturation_pilot.py"
        ).as_posix()
    ):
        raise ValueError("iteration-007 remediated test path mismatch")
    replacement = top["replacement_prepare"]
    if (
        replacement.get("schema_version")
        != "frozen-readout-interaction-maturation-prepare-v2"
        or replacement.get("path")
        != AUDIT_BLOCKED_PREPARE_V2_RELATIVE_PATH.as_posix()
        or replacement.get("must_bind_remediation") is not True
        or replacement.get("same_no_training_proof_required") is not True
    ):
        raise ValueError("iteration-007 replacement prepare mismatch")
    override = top["execution_spec_override"]
    if (
        override.get("schema_version")
        != "actor-only-interaction-maturation-execution-spec-v3"
        or override.get("exact_top_level_keys")
        != list(EXECUTION_SPEC_V3_TOP_LEVEL_KEYS)
        or override.get("key_count_exact") != 30
        or override.get("output_directory_exact")
        != APPROVED_OUTPUT_RELATIVE_PATH.as_posix()
    ):
        raise ValueError("iteration-007 execution-spec v3 remediation mismatch")
    _validate_audit_blocked_prepare_v1()
    return dict(top)


def _load_prepare_audit_remediation_v2() -> dict[str, Any]:
    remediation = inherited._load_hashed_json(
        _repo_path(PREPARE_AUDIT_REMEDIATION_V2_RELATIVE_PATH),
        PREPARE_AUDIT_REMEDIATION_V2_SHA256,
        label="iteration-007 prepare audit remediation v2",
    )
    top = _exact_keys(
        remediation,
        {
            "schema_version", "remediation_id", "base_plan",
            "plan_correction_v1", "plan_correction_v2",
            "prepare_audit_remediation_v1", "authority", "hypothesis_change",
            "training_data_or_objective_change", "intended_production_behavior_change",
            "real_optimizer_execution_authorized", "audited_blocked_candidate",
            "production_path_test_requirements", "implementation_rule",
            "replacement_prepare", "execution_spec_override",
            "verification_before_replacement_prepare", "forbidden", "stop_rule",
        },
        label="iteration-007 prepare audit remediation v2",
    )
    if (
        top["schema_version"] != PREPARE_AUDIT_REMEDIATION_V2_SCHEMA_VERSION
        or top["remediation_id"] != PREPARE_AUDIT_REMEDIATION_V2_ID
        or top["base_plan"]
        != {"path": PLAN_RELATIVE_PATH.as_posix(), "sha256": PLAN_SHA256}
        or top["plan_correction_v1"]
        != {"path": CORRECTION_RELATIVE_PATH.as_posix(), "sha256": CORRECTION_SHA256}
        or top["plan_correction_v2"]
        != {
            "path": CORRECTION_V2_RELATIVE_PATH.as_posix(),
            "sha256": CORRECTION_V2_SHA256,
        }
        or top["prepare_audit_remediation_v1"]
        != {
            "path": PREPARE_AUDIT_REMEDIATION_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_SHA256,
        }
        or top["hypothesis_change"] is not False
        or top["training_data_or_objective_change"] is not False
        or top["intended_production_behavior_change"] is not False
        or top["real_optimizer_execution_authorized"] is not False
    ):
        raise ValueError("iteration-007 prepare remediation v2 identity mismatch")
    blocked = top["audited_blocked_candidate"]
    if (
        blocked.get("path") != IMPLEMENTATION_RELATIVE_PATH.as_posix()
        or blocked.get("snapshot_file_count") != 53
        or blocked.get("snapshot_sha256")
        != "7B8849CCEDADA9D05063E02E7CB1FCBE268BD77112F33355B5D80A27500D50A3"
        or blocked.get("primary_module_sha256")
        != "C322ED77FEB68C7BEC01A12D8CCEF635D3DD7E39255D8E6AD09EE82DC886F4CE"
        or blocked.get("test_module_sha256")
        != "D5106BD6A2D300214659EFDBB4B9F36C17DE6B8C7AC0E40CA41B4AF36894A2E5"
        or blocked.get("prepare_v2_path")
        != AUDIT_BLOCKED_PREPARE_V2_RELATIVE_PATH.as_posix()
        or blocked.get("prepare_v2_file_sha256")
        != AUDIT_BLOCKED_PREPARE_V2_FILE_SHA256
        or blocked.get("prepare_v2_receipt_sha256")
        != AUDIT_BLOCKED_PREPARE_V2_RECEIPT_SHA256
        or blocked.get("prepare_v2_must_remain_byte_exact") is not True
    ):
        raise ValueError("iteration-007 blocked prepare v2 identity mismatch")
    implementation_rule = top["implementation_rule"]
    if (
        implementation_rule.get("test_only_expected") is not True
        or implementation_rule.get("inherited_files_must_remain_byte_exact") is not True
        or implementation_rule.get("test_module_path_exact")
        != (
            IMPLEMENTATION_RELATIVE_PATH
            / "tests/test_actor_only_interaction_maturation_pilot.py"
        ).as_posix()
    ):
        raise ValueError("iteration-007 remediation v2 implementation rule mismatch")
    replacement = top["replacement_prepare"]
    if (
        replacement.get("schema_version")
        != "frozen-readout-interaction-maturation-prepare-v3"
        or replacement.get("path")
        != AUDIT_BLOCKED_PREPARE_V3_RELATIVE_PATH.as_posix()
        or replacement.get("must_bind_all_five_contracts") is not True
        or replacement.get("same_no_training_proof_required") is not True
        or replacement.get("standalone_validation_with_adam_patched_to_raise")
        is not True
    ):
        raise ValueError("iteration-007 remediation v2 replacement prepare mismatch")
    override = top["execution_spec_override"]
    if (
        override.get("schema_version")
        != "actor-only-interaction-maturation-execution-spec-v4"
        or override.get("exact_top_level_keys")
        != list(EXECUTION_SPEC_V4_TOP_LEVEL_KEYS)
        or override.get("key_count_exact") != 32
        or override.get("output_directory_exact")
        != APPROVED_OUTPUT_RELATIVE_PATH.as_posix()
    ):
        raise ValueError("iteration-007 execution-spec v4 remediation mismatch")
    _load_prepare_audit_remediation()
    _validate_audit_blocked_prepare_v2()
    return dict(top)


def _load_prepare_audit_remediation_v3() -> dict[str, Any]:
    remediation = inherited._load_hashed_json(
        _repo_path(PREPARE_AUDIT_REMEDIATION_V3_RELATIVE_PATH),
        PREPARE_AUDIT_REMEDIATION_V3_SHA256,
        label="iteration-007 prepare audit remediation v3",
    )
    top = _exact_keys(
        remediation,
        {
            "schema_version", "remediation_id", "base_plan",
            "plan_correction_v1", "plan_correction_v2",
            "prepare_audit_remediation_v1", "prepare_audit_remediation_v2",
            "authority", "hypothesis_change", "training_data_or_objective_change",
            "real_optimizer_execution_authorized", "confirmed_defect",
            "authorized_production_fix", "required_fix_tests",
            "all_remediation_v2_tests_remain_required", "replacement_prepare",
            "execution_spec_override", "verification_before_replacement_prepare",
            "stop_rule",
        },
        label="iteration-007 prepare audit remediation v3",
    )
    if (
        top["schema_version"] != PREPARE_AUDIT_REMEDIATION_V3_SCHEMA_VERSION
        or top["remediation_id"] != PREPARE_AUDIT_REMEDIATION_V3_ID
        or top["base_plan"]
        != {"path": PLAN_RELATIVE_PATH.as_posix(), "sha256": PLAN_SHA256}
        or top["plan_correction_v1"]
        != {"path": CORRECTION_RELATIVE_PATH.as_posix(), "sha256": CORRECTION_SHA256}
        or top["plan_correction_v2"]
        != {
            "path": CORRECTION_V2_RELATIVE_PATH.as_posix(),
            "sha256": CORRECTION_V2_SHA256,
        }
        or top["prepare_audit_remediation_v1"]
        != {
            "path": PREPARE_AUDIT_REMEDIATION_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_SHA256,
        }
        or top["prepare_audit_remediation_v2"]
        != {
            "path": PREPARE_AUDIT_REMEDIATION_V2_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V2_SHA256,
        }
        or top["hypothesis_change"] is not False
        or top["training_data_or_objective_change"] is not False
        or top["real_optimizer_execution_authorized"] is not False
        or top["all_remediation_v2_tests_remain_required"] is not True
    ):
        raise ValueError("iteration-007 prepare remediation v3 identity mismatch")
    confirmed = top["confirmed_defect"]
    if (
        confirmed.get("production_entrypoint")
        != "actor_only_interaction_maturation_pilot.evaluate_directional_gates"
        or confirmed.get("candidate_snapshot_before_fix")
        != "7B8849CCEDADA9D05063E02E7CB1FCBE268BD77112F33355B5D80A27500D50A3"
        or confirmed.get("primary_module_sha256_before_fix")
        != "C322ED77FEB68C7BEC01A12D8CCEF635D3DD7E39255D8E6AD09EE82DC886F4CE"
        or confirmed.get("test_module_sha256_before_fix")
        != "D5106BD6A2D300214659EFDBB4B9F36C17DE6B8C7AC0E40CA41B4AF36894A2E5"
        or confirmed.get("files_changed_during_confirmation") is not False
        or confirmed.get("prepare_v3_created") is not False
    ):
        raise ValueError("iteration-007 confirmed directional defect mismatch")
    fix = top["authorized_production_fix"]
    if fix.get("required_counts_exact") != {
        "negative_target_ordinals": 4,
        "positive_normalized_teacher_and_sampled_end_ordinals": 20,
        "positive_raw_teacher_and_sampled_end_ordinals": 31,
        "teacher_end_and_sampled_end_ordinals": 41,
        "teacher_end_ordinals": 43,
    }:
        raise ValueError("iteration-007 directional fix counts mismatch")
    replacement = top["replacement_prepare"]
    if (
        replacement.get("schema_version")
        != "frozen-readout-interaction-maturation-prepare-v3"
        or replacement.get("path")
        != AUDIT_BLOCKED_PREPARE_V3_RELATIVE_PATH.as_posix()
        or replacement.get("must_bind_all_six_contracts") is not True
        or replacement.get("same_no_training_proof_required") is not True
        or replacement.get("standalone_validation_with_adam_patched_to_raise")
        is not True
    ):
        raise ValueError("iteration-007 remediation v3 replacement prepare mismatch")
    override = top["execution_spec_override"]
    if (
        override.get("schema_version")
        != "actor-only-interaction-maturation-execution-spec-v5"
        or override.get("exact_top_level_keys")
        != list(EXECUTION_SPEC_V5_TOP_LEVEL_KEYS)
        or override.get("key_count_exact") != 34
        or override.get("output_directory_exact")
        != APPROVED_OUTPUT_RELATIVE_PATH.as_posix()
    ):
        raise ValueError("iteration-007 execution-spec v5 remediation mismatch")
    _load_prepare_audit_remediation_v2()
    return dict(top)


def _load_prepare_audit_remediation_v4() -> dict[str, Any]:
    remediation = inherited._load_hashed_json(
        _repo_path(PREPARE_AUDIT_REMEDIATION_V4_RELATIVE_PATH),
        PREPARE_AUDIT_REMEDIATION_V4_SHA256,
        label="iteration-007 prepare audit remediation v4",
    )
    top = _exact_keys(
        remediation,
        {
            "schema_version", "remediation_id", "contract_chain", "authority",
            "hypothesis_change", "training_data_or_objective_change",
            "real_optimizer_execution_authorized", "confirmed_defect",
            "authorized_production_fix", "required_fix_tests",
            "all_remediation_v2_and_v3_tests_remain_required",
            "replacement_prepare", "execution_spec_override",
            "verification_before_replacement_prepare", "stop_rule",
        },
        label="iteration-007 prepare audit remediation v4",
    )
    expected_chain = [
        {"path": PLAN_RELATIVE_PATH.as_posix(), "sha256": PLAN_SHA256},
        {"path": CORRECTION_RELATIVE_PATH.as_posix(), "sha256": CORRECTION_SHA256},
        {"path": CORRECTION_V2_RELATIVE_PATH.as_posix(), "sha256": CORRECTION_V2_SHA256},
        {
            "path": PREPARE_AUDIT_REMEDIATION_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V2_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V2_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V3_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V3_SHA256,
        },
    ]
    if (
        top["schema_version"] != PREPARE_AUDIT_REMEDIATION_V4_SCHEMA_VERSION
        or top["remediation_id"] != PREPARE_AUDIT_REMEDIATION_V4_ID
        or top["contract_chain"] != expected_chain
        or top["hypothesis_change"] is not False
        or top["training_data_or_objective_change"] is not False
        or top["real_optimizer_execution_authorized"] is not False
        or top["all_remediation_v2_and_v3_tests_remain_required"] is not True
    ):
        raise ValueError("iteration-007 prepare remediation v4 identity mismatch")
    confirmed = top["confirmed_defect"]
    if (
        confirmed.get("candidate_snapshot_after_authorized_v3_partial_edits")
        != "9A61CB48E276597D868614D52B1113899DF7F8957AC2E619867156887C06985B"
        or confirmed.get("primary_module_sha256_after_authorized_v3_partial_edits")
        != "7230545E3F9B1CA21F65C0283D02410A6B58A9678FC0B5E66935AFD5A941BF87"
        or confirmed.get("test_module_sha256_unchanged")
        != "D5106BD6A2D300214659EFDBB4B9F36C17DE6B8C7AC0E40CA41B4AF36894A2E5"
        or confirmed.get("publisher_behavior_changed_during_confirmation") is not False
        or confirmed.get("tests_changed_during_confirmation") is not False
        or confirmed.get("prepare_v3_created") is not False
    ):
        raise ValueError("iteration-007 confirmed artifact defect mismatch")
    exact_sets = top["authorized_production_fix"].get("exact_sets_by_phase")
    if exact_sets != {
        "after_output_directory_creation_before_any_publication": [],
        "before_checkpoint_publication": [],
        "after_checkpoint_publication_before_status": ["candidate.pt"],
        "before_zero_step_rejected_status": [],
        "after_zero_step_rejected_status": ["rejected_receipt.json", "REJECTED"],
        "after_accepted_terminal": [
            "candidate.pt", "accepted_receipt.json", "ACCEPTED"
        ],
        "after_rejected_terminal_or_post_step_rejection": [
            "candidate.pt", "rejected_receipt.json", "REJECTED"
        ],
    }:
        raise ValueError("iteration-007 artifact allowlists mismatch")
    replacement = top["replacement_prepare"]
    if (
        replacement.get("schema_version")
        != "frozen-readout-interaction-maturation-prepare-v3"
        or replacement.get("path")
        != AUDIT_BLOCKED_PREPARE_V3_RELATIVE_PATH.as_posix()
        or replacement.get("must_bind_all_seven_contracts") is not True
        or replacement.get("same_no_training_proof_required") is not True
        or replacement.get("standalone_validation_with_adam_patched_to_raise")
        is not True
    ):
        raise ValueError("iteration-007 remediation v4 replacement prepare mismatch")
    override = top["execution_spec_override"]
    if (
        override.get("schema_version")
        != "actor-only-interaction-maturation-execution-spec-v6"
        or override.get("exact_top_level_keys")
        != list(EXECUTION_SPEC_V6_TOP_LEVEL_KEYS)
        or override.get("key_count_exact") != 36
        or override.get("output_directory_exact")
        != APPROVED_OUTPUT_RELATIVE_PATH.as_posix()
    ):
        raise ValueError("iteration-007 execution-spec v6 remediation mismatch")
    _load_prepare_audit_remediation_v3()
    return dict(top)


def _load_prepare_audit_remediation_v5() -> dict[str, Any]:
    remediation = inherited._load_hashed_json(
        _repo_path(PREPARE_AUDIT_REMEDIATION_V5_RELATIVE_PATH),
        PREPARE_AUDIT_REMEDIATION_V5_SHA256,
        label="iteration-007 prepare audit remediation v5",
    )
    top = _exact_keys(
        remediation,
        {
            "schema_version", "remediation_id", "contract_chain", "authority",
            "hypothesis_change", "training_data_or_objective_change",
            "model_optimizer_schedule_or_threshold_change",
            "real_optimizer_execution_authorized", "confirmed_defect",
            "authorized_production_fix", "required_fix_tests",
            "replacement_prepare", "execution_spec_override",
            "verification_before_replacement_prepare", "stop_rule",
        },
        label="iteration-007 prepare audit remediation v5",
    )
    expected_chain = [
        {"path": PLAN_RELATIVE_PATH.as_posix(), "sha256": PLAN_SHA256},
        {"path": CORRECTION_RELATIVE_PATH.as_posix(), "sha256": CORRECTION_SHA256},
        {"path": CORRECTION_V2_RELATIVE_PATH.as_posix(), "sha256": CORRECTION_V2_SHA256},
        {
            "path": PREPARE_AUDIT_REMEDIATION_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V2_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V2_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V3_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V3_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V4_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V4_SHA256,
        },
    ]
    if (
        top["schema_version"] != PREPARE_AUDIT_REMEDIATION_V5_SCHEMA_VERSION
        or top["remediation_id"] != PREPARE_AUDIT_REMEDIATION_V5_ID
        or top["contract_chain"] != expected_chain
        or top["hypothesis_change"] is not False
        or top["training_data_or_objective_change"] is not False
        or top["model_optimizer_schedule_or_threshold_change"] is not False
        or top["real_optimizer_execution_authorized"] is not False
    ):
        raise ValueError("iteration-007 prepare remediation v5 identity mismatch")
    fix = top["authorized_production_fix"]
    if (
        fix.get("required_entrypoint") != "validate_compact_update_chain"
        or len(fix.get("exact_compact_record_keys", [])) != 22
        or len(fix.get("exact_measurement_timing_keys", [])) != 2
        or len(fix.get("exact_pre_step_keys", [])) != 7
        or len(fix.get("exact_post_step_keys", [])) != 7
        or len(fix.get("exact_semantic_bindings", {})) != 14
    ):
        raise ValueError("iteration-007 timing validation contract mismatch")
    replacement = top["replacement_prepare"]
    if (
        replacement.get("schema_version")
        != "frozen-readout-interaction-maturation-prepare-v3"
        or replacement.get("path")
        != AUDIT_BLOCKED_PREPARE_V3_RELATIVE_PATH.as_posix()
        or replacement.get("must_bind_all_eight_contracts") is not True
        or replacement.get("contract_binding_field_count") != 16
        or replacement.get("top_level_key_count_exact") != 45
    ):
        raise ValueError("iteration-007 remediation v5 replacement prepare mismatch")
    override = top["execution_spec_override"]
    if (
        override.get("schema_version")
        != "actor-only-interaction-maturation-execution-spec-v7"
        or override.get("exact_top_level_keys")
        != list(EXECUTION_SPEC_V7_TOP_LEVEL_KEYS)
        or override.get("key_count_exact") != 38
        or override.get("output_directory_exact")
        != APPROVED_OUTPUT_RELATIVE_PATH.as_posix()
    ):
        raise ValueError("iteration-007 execution-spec v7 remediation mismatch")
    _load_prepare_audit_remediation_v4()
    return dict(top)


def _load_prepare_audit_remediation_v6() -> dict[str, Any]:
    remediation = inherited._load_hashed_json(
        _repo_path(PREPARE_AUDIT_REMEDIATION_V6_RELATIVE_PATH),
        PREPARE_AUDIT_REMEDIATION_V6_SHA256,
        label="iteration-007 prepare audit remediation v6",
    )
    top = _exact_keys(
        remediation,
        {
            "schema_version", "remediation_id", "contract_chain", "authority",
            "hypothesis_change", "training_data_or_objective_change",
            "model_optimizer_schedule_or_threshold_change",
            "real_optimizer_execution_authorized", "confirmed_defect",
            "required_restoration", "authorized_production_fix",
            "required_fix_tests", "replacement_prepare",
            "execution_spec_override", "verification_before_replacement_prepare",
            "stop_rule",
        },
        label="iteration-007 prepare audit remediation v6",
    )
    expected_chain = [
        {"path": PLAN_RELATIVE_PATH.as_posix(), "sha256": PLAN_SHA256},
        {"path": CORRECTION_RELATIVE_PATH.as_posix(), "sha256": CORRECTION_SHA256},
        {"path": CORRECTION_V2_RELATIVE_PATH.as_posix(), "sha256": CORRECTION_V2_SHA256},
        {
            "path": PREPARE_AUDIT_REMEDIATION_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V2_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V2_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V3_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V3_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V4_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V4_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V5_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V5_SHA256,
        },
    ]
    if (
        top["schema_version"] != PREPARE_AUDIT_REMEDIATION_V6_SCHEMA_VERSION
        or top["remediation_id"] != PREPARE_AUDIT_REMEDIATION_V6_ID
        or top["contract_chain"] != expected_chain
        or top["hypothesis_change"] is not False
        or top["training_data_or_objective_change"] is not False
        or top["model_optimizer_schedule_or_threshold_change"] is not False
        or top["real_optimizer_execution_authorized"] is not False
    ):
        raise ValueError("iteration-007 prepare remediation v6 identity mismatch")
    confirmed = top["confirmed_defect"]
    if (
        confirmed.get("windows_error")
        != "PermissionError: [WinError 5] Access is denied"
        or confirmed.get("prepare_v3_created") is not False
        or confirmed.get("candidate_snapshot_after_ineffective_unapproved_edit")
        != "C5154368C674EEEDF2C8875C3724EA01D072166A744FF19C75EA06BD13141385"
        or confirmed.get("primary_module_sha256_after_ineffective_unapproved_edit")
        != "53A64B69140C80C2172EEA9ADBA9E9AD9EDDFBC1DE2D98896989473E6A491D5A"
        or confirmed.get("test_module_sha256")
        != "CAF58FB9699AE92C7446691970C195910322B36C27FB8CB536D0540A146144A5"
        or confirmed.get("primary_module_sha256_before_ineffective_unapproved_edit")
        != "E1AA56A17F44FAF858647485889AAE6B6A463F3DEC1ACC244CFF053A181E38C2"
    ):
        raise ValueError("iteration-007 confirmed Windows defect mismatch")
    held = top["authorized_production_fix"].get("held_candidate_evidence", {})
    if (
        top["required_restoration"].get("no_other_reversion_or_inherited_file_change")
        is not True
        or held.get("canonical_name") != "candidate.pt"
        or held.get("required_fields")
        != [
            "exact public checkpoint path",
            "expected uppercase SHA-256",
            "transferred live StableFileGuard",
            "exact serialized checkpoint readback bytes",
        ]
    ):
        raise ValueError("iteration-007 held-checkpoint contract mismatch")
    replacement = top["replacement_prepare"]
    if (
        replacement.get("schema_version")
        != "frozen-readout-interaction-maturation-prepare-v3"
        or replacement.get("path")
        != AUDIT_BLOCKED_PREPARE_V3_RELATIVE_PATH.as_posix()
        or replacement.get("must_bind_all_nine_contracts") is not True
        or replacement.get("contract_binding_field_count") != 18
        or replacement.get("top_level_key_count_exact") != 48
    ):
        raise ValueError("iteration-007 remediation v6 replacement prepare mismatch")
    override = top["execution_spec_override"]
    if (
        override.get("schema_version")
        != "actor-only-interaction-maturation-execution-spec-v8"
        or override.get("exact_top_level_keys")
        != list(EXECUTION_SPEC_V8_TOP_LEVEL_KEYS)
        or override.get("key_count_exact") != 40
        or override.get("output_directory_exact")
        != APPROVED_OUTPUT_RELATIVE_PATH.as_posix()
    ):
        raise ValueError("iteration-007 execution-spec v8 remediation mismatch")
    _load_prepare_audit_remediation_v5()
    return dict(top)


def _load_prepare_audit_remediation_v7() -> dict[str, Any]:
    remediation = inherited._load_hashed_json(
        _repo_path(PREPARE_AUDIT_REMEDIATION_V7_RELATIVE_PATH),
        PREPARE_AUDIT_REMEDIATION_V7_SHA256,
        label="iteration-007 prepare audit remediation v7",
    )
    top = _exact_keys(
        remediation,
        {
            "schema_version", "remediation_id", "contract_chain", "authority",
            "hypothesis_change", "training_data_or_objective_change",
            "model_optimizer_schedule_or_threshold_change",
            "real_optimizer_execution_authorized", "confirmed_defect",
            "authorized_production_fix", "required_fix_tests",
            "replacement_prepare", "execution_spec_override",
            "verification_before_replacement_prepare", "stop_rule",
        },
        label="iteration-007 prepare audit remediation v7",
    )
    expected_chain = [
        {"path": PLAN_RELATIVE_PATH.as_posix(), "sha256": PLAN_SHA256},
        {"path": CORRECTION_RELATIVE_PATH.as_posix(), "sha256": CORRECTION_SHA256},
        {"path": CORRECTION_V2_RELATIVE_PATH.as_posix(), "sha256": CORRECTION_V2_SHA256},
        {
            "path": PREPARE_AUDIT_REMEDIATION_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V2_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V2_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V3_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V3_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V4_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V4_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V5_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V5_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V6_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V6_SHA256,
        },
    ]
    if (
        top["schema_version"] != PREPARE_AUDIT_REMEDIATION_V7_SCHEMA_VERSION
        or top["remediation_id"] != PREPARE_AUDIT_REMEDIATION_V7_ID
        or top["contract_chain"] != expected_chain
        or top["hypothesis_change"] is not False
        or top["training_data_or_objective_change"] is not False
        or top["model_optimizer_schedule_or_threshold_change"] is not False
        or top["real_optimizer_execution_authorized"] is not False
    ):
        raise ValueError("iteration-007 prepare remediation v7 identity mismatch")
    confirmed = top["confirmed_defect"]
    if (
        confirmed.get("failure") != "ValueError: output artifact set mismatch"
        or confirmed.get("prepare_v3_created") is not False
        or confirmed.get("candidate_snapshot")
        != "A394DB07B61F0D8216842AD6C46CC8FCDB4BF7FD6B8F6669BDD40F8E2CEDE62D"
        or confirmed.get("primary_module_sha256")
        != "B6E57315B36DE23CC87DF0F8EFEB635B941EEBB7E0B12C115A8FB4BD12A95BE6"
        or confirmed.get("test_module_sha256")
        != "7DF9E28F01E2EA4B3C3A376EF58583CFB764EF9C7C8F0BD5C56BE9C6073F8AFB"
        or confirmed.get("v6_real_windows_artifact_tests")
        != {
            "tests_run": 10,
            "passes": 2,
            "errors": 8,
            "assertion_failures": 0,
        }
    ):
        raise ValueError("iteration-007 confirmed private-alias defect mismatch")
    fix = top["authorized_production_fix"]
    alias = fix.get("exact_internal_alias", {})
    semantics = fix.get("set_semantics", {})
    if (
        alias.get("source_of_name")
        != "checkpoint_guard.path.name only; never discover an allowed alias by scanning or prefix matching"
        or alias.get("canonical_pattern")
        != ".candidate-<exactly 32 lowercase hexadecimal characters>.staging.pt"
        or semantics.get("internal_set_without_checkpoint") != []
        or semantics.get("internal_set_with_live_checkpoint")
        != ["the single exact checkpoint_guard.path.name"]
    ):
        raise ValueError("iteration-007 private-alias projection mismatch")
    replacement = top["replacement_prepare"]
    if (
        replacement.get("schema_version")
        != "frozen-readout-interaction-maturation-prepare-v3"
        or replacement.get("path")
        != AUDIT_BLOCKED_PREPARE_V3_RELATIVE_PATH.as_posix()
        or replacement.get("must_bind_all_ten_contracts") is not True
        or replacement.get("contract_binding_field_count") != 20
        or replacement.get("top_level_key_count_exact") != 51
    ):
        raise ValueError("iteration-007 remediation v7 replacement prepare mismatch")
    override = top["execution_spec_override"]
    if (
        override.get("schema_version")
        != "actor-only-interaction-maturation-execution-spec-v9"
        or override.get("exact_top_level_keys")
        != list(EXECUTION_SPEC_V9_TOP_LEVEL_KEYS)
        or override.get("key_count_exact") != 42
        or override.get("output_directory_exact")
        != APPROVED_OUTPUT_RELATIVE_PATH.as_posix()
    ):
        raise ValueError("iteration-007 execution-spec v9 remediation mismatch")
    _load_prepare_audit_remediation_v6()
    return dict(top)


def _load_prepare_audit_remediation_v8() -> dict[str, Any]:
    remediation = inherited._load_hashed_json(
        _repo_path(PREPARE_AUDIT_REMEDIATION_V8_RELATIVE_PATH),
        PREPARE_AUDIT_REMEDIATION_V8_SHA256,
        label="iteration-007 prepare audit remediation v8",
    )
    top = _exact_keys(
        remediation,
        {
            "schema_version", "remediation_id", "contract_chain", "authority",
            "hypothesis_change", "training_data_or_objective_change",
            "model_optimizer_schedule_or_threshold_change",
            "real_optimizer_execution_authorized", "blocked_prepare_v3",
            "confirmed_findings", "authorized_production_fix",
            "required_test_corrections", "replacement_prepare",
            "execution_spec_override", "verification_before_replacement_prepare",
            "stop_rule",
        },
        label="iteration-007 prepare audit remediation v8",
    )
    expected_chain = [
        {"path": PLAN_RELATIVE_PATH.as_posix(), "sha256": PLAN_SHA256},
        {"path": CORRECTION_RELATIVE_PATH.as_posix(), "sha256": CORRECTION_SHA256},
        {"path": CORRECTION_V2_RELATIVE_PATH.as_posix(), "sha256": CORRECTION_V2_SHA256},
        {
            "path": PREPARE_AUDIT_REMEDIATION_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V2_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V2_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V3_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V3_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V4_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V4_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V5_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V5_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V6_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V6_SHA256,
        },
        {
            "path": PREPARE_AUDIT_REMEDIATION_V7_RELATIVE_PATH.as_posix(),
            "sha256": PREPARE_AUDIT_REMEDIATION_V7_SHA256,
        },
    ]
    if (
        top["schema_version"] != PREPARE_AUDIT_REMEDIATION_V8_SCHEMA_VERSION
        or top["remediation_id"] != PREPARE_AUDIT_REMEDIATION_V8_ID
        or top["contract_chain"] != expected_chain
        or top["hypothesis_change"] is not False
        or top["training_data_or_objective_change"] is not False
        or top["model_optimizer_schedule_or_threshold_change"] is not False
        or top["real_optimizer_execution_authorized"] is not False
    ):
        raise ValueError("iteration-007 prepare remediation v8 identity mismatch")
    blocked = top["blocked_prepare_v3"]
    if blocked != {
        "path": AUDIT_BLOCKED_PREPARE_V3_RELATIVE_PATH.as_posix(),
        "file_sha256": AUDIT_BLOCKED_PREPARE_V3_FILE_SHA256,
        "receipt_sha256": AUDIT_BLOCKED_PREPARE_V3_RECEIPT_SHA256,
        "candidate_snapshot_sha256": (
            "B8B51A5B7FA54A542CE32B56019F92018E2D734BC33C3FCB570DC0C938CA18CB"
        ),
        "primary_module_sha256": (
            "D024773EB606359633C4DACAC7C1B0E7F6BE77EF20F13961C20A3C8E75608B91"
        ),
        "test_module_sha256": (
            "E603C654FE6A65E5B43E33560EE93326CD6E7822EB392FAE5B4BE6B9FF2E55A9"
        ),
        "numerical_status": "PASS_ZERO_DISCREPANCIES",
        "code_status": "AUDIT_BLOCKED_NOT_EXECUTION_AUTHORIZATION",
        "must_remain_byte_exact": True,
        "must_not_be_bound_by_execution_spec": True,
    }:
        raise ValueError("iteration-007 blocked prepare v3 mismatch")
    finding = top["confirmed_findings"].get("production_defect", {})
    fix = top["authorized_production_fix"]
    if (
        finding.get("function") != "_delete_owned_status_artifact"
        or fix.get("exact_change")
        != (
            "In _delete_owned_status_artifact, set the cleanup OPEN_EXISTING "
            "share_mode to inherited._FILE_SHARE_READ | "
            "inherited._FILE_SHARE_WRITE | inherited._FILE_SHARE_DELETE."
        )
        or top["required_test_corrections"].get("all_prior_tests_remain_required")
        is not True
    ):
        raise ValueError("iteration-007 cleanup-share contract mismatch")
    replacement = top["replacement_prepare"]
    if (
        replacement.get("schema_version") != PREPARE_RECEIPT_SCHEMA_VERSION
        or replacement.get("path") != APPROVED_PREPARE_RELATIVE_PATH.as_posix()
        or replacement.get("must_bind_all_eleven_contracts") is not True
        or replacement.get("contract_binding_field_count") != 22
        or replacement.get("top_level_key_count_exact") != 54
    ):
        raise ValueError("iteration-007 remediation v8 replacement prepare mismatch")
    override = top["execution_spec_override"]
    if (
        override.get("schema_version") != EXECUTION_SPEC_SCHEMA_VERSION
        or override.get("exact_top_level_keys")
        != list(EXECUTION_SPEC_TOP_LEVEL_KEYS)
        or override.get("key_count_exact") != 44
        or override.get("output_directory_exact")
        != APPROVED_OUTPUT_RELATIVE_PATH.as_posix()
    ):
        raise ValueError("iteration-007 execution-spec v10 remediation mismatch")
    _load_prepare_audit_remediation_v7()
    _validate_audit_blocked_prepare_v3()
    return dict(top)


def _validate_parent_rejection(plan: Mapping[str, Any]) -> dict[str, Any]:
    parent = plan["parent_result"]
    if parent != {
        "path": PARENT_RESULT_RELATIVE_PATH.as_posix(),
        "sha256": PARENT_RESULT_SHA256,
        "decision": "REJECT_CHECKPOINT_CONTINUE_RL_PATH",
        "rejected_receipt_path": PARENT_REJECTED_RECEIPT_RELATIVE_PATH.as_posix(),
        "rejected_receipt_file_sha256": PARENT_REJECTED_RECEIPT_FILE_SHA256,
        "rejected_receipt_sha256": PARENT_REJECTED_RECEIPT_SHA256,
        "rejected_checkpoint_path": REJECTED_CHECKPOINT_RELATIVE_PATH.as_posix(),
        "rejected_checkpoint_sha256": REJECTED_CHECKPOINT_SHA256,
        "rejected_checkpoint_must_not_be_loaded": True,
        "runtime_smoke_skipped": True,
        "games_run": 0,
    }:
        raise ValueError("parent rejection plan fields mismatch")
    if sha256_file(_repo_path(PARENT_RESULT_RELATIVE_PATH)) != PARENT_RESULT_SHA256:
        raise ValueError("parent result hash mismatch")
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
        or rejected.get("accepted_marker_written") is not False
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
        "decision": "REJECT_CHECKPOINT_CONTINUE_RL_PATH",
        "rejected_receipt_path": PARENT_REJECTED_RECEIPT_RELATIVE_PATH.as_posix(),
        "rejected_receipt_file_sha256": PARENT_REJECTED_RECEIPT_FILE_SHA256,
        "rejected_receipt_sha256": rejected_self,
        "rejected_checkpoint_path": REJECTED_CHECKPOINT_RELATIVE_PATH.as_posix(),
        "rejected_checkpoint_sha256": REJECTED_CHECKPOINT_SHA256,
        "rejected_checkpoint_loaded": False,
        "runtime_smoke_skipped": True,
        "games_run": 0,
    }


def _validate_source_implementation(plan: Mapping[str, Any]) -> dict[str, Any]:
    source = plan["immutable_inputs"]["source_implementation"]
    expected = {
        "path": SOURCE_IMPLEMENTATION_RELATIVE_PATH.as_posix(),
        "snapshot_definition": inherited.STRICT_IMPLEMENTATION_SNAPSHOT_DEFINITION,
        "file_count": SOURCE_IMPLEMENTATION_FILE_COUNT,
        "snapshot_sha256": SOURCE_IMPLEMENTATION_SHA256,
        "actor_only_two_stage_pilot_py_sha256": SOURCE_TWO_STAGE_PILOT_SHA256,
        "conservative_ppo_pilot_py_sha256": SOURCE_CONSERVATIVE_PILOT_SHA256,
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
        "archaludon_rl/actor_only_two_stage_pilot.py": SOURCE_TWO_STAGE_PILOT_SHA256,
        "archaludon_rl/conservative_ppo_pilot.py": SOURCE_CONSERVATIVE_PILOT_SHA256,
    }
    for relative, expected_hash in critical.items():
        if sha256_file(root / Path(relative)) != expected_hash:
            raise ValueError(f"source implementation critical hash mismatch: {relative}")
    return {
        "path": SOURCE_IMPLEMENTATION_RELATIVE_PATH.as_posix(),
        **snapshot,
        "critical_files": critical,
    }


def _load_and_reproduce_prepare_source(runtime: Mapping[str, Any]) -> dict[str, Any]:
    pinned = inherited._load_hashed_json(
        _repo_path(PREPARE_SOURCE_RELATIVE_PATH),
        PREPARE_SOURCE_FILE_SHA256,
        label="iteration-006 prepare source",
    )
    predecessor.validate_prepare_receipt(pinned)
    if pinned["receipt_sha256"] != PREPARE_SOURCE_RECEIPT_SHA256:
        raise ValueError("iteration-006 prepare source self-hash mismatch")
    rebuilt = predecessor._build_prepare_receipt(runtime)
    if rebuilt != pinned:
        raise ValueError("iteration-006 prepare source did not reproduce exactly")
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
                "stage_2_trainable": name in STAGE2_TRAINABLE_NAMES,
                "optimizer_parameter_universe": name in OPTIMIZER_PARAMETER_NAMES,
            }
        )
    return records


def _build_family_receipt(
    prepare_source: Mapping[str, Any],
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
        normalized = float(probe["fixed_normalized_advantage_float32"])
        if not math.isfinite(normalized) or normalized == 0.0:
            raise ValueError("family row has zero or non-finite normalized advantage")
        initial_probabilities, _ = _authoritative_float32_probability_vector(
            probe["initial_probabilities_float32"],
            label=f"prepare initial probabilities row {ordinal}",
        )
        if len(initial_probabilities) != int(row["legal_option_count"]):
            raise ValueError("prepare initial probability dimension mismatch")
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
                "raw_advantage_float64": float(probe["raw_advantage_float64"]),
                "fixed_value_target_float64": float(
                    probe["fixed_value_target_float64"]
                ),
                "fixed_normalized_advantage_float32": normalized,
                "initial_probabilities_float32": initial_probabilities,
                "initial_value_float32": float(probe["initial_value_float32"]),
                "initial_value_raw_bytes_hex": _tensor_bytes(
                    torch.tensor(
                        float(probe["initial_value_float32"]), dtype=torch.float32
                    )
                ).hex().upper(),
                "initial_value_byte_sha256": _tensor_sha256(
                    torch.tensor(
                        float(probe["initial_value_float32"]), dtype=torch.float32
                    )
                ),
            }
        )
    row_map_value = {"schema_version": ROW_MAP_SCHEMA_VERSION, "rows": row_map}
    row_map_hash = canonical_sha256(row_map_value)
    if row_map_hash != ROW_MAP_SHA256:
        raise ValueError("sampled option-type row-map hash mismatch")
    family_contract = prepare_source["action_families"]
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
        expected_summary = {
            name: expected[name]
            for name in (
                "option_type", "name", "rows", "normalized_positive",
                "normalized_negative", "membership_sha256", "qualifying",
            )
        }
        if reproduced != expected_summary:
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
            "gate_definition": {
                "metric": "oriented_sampled_probability_delta_from_immutable_initial",
                "aggregation": "lower_empirical_median",
                "threshold": DEADBAND_TAU,
                "comparison": "strictly_greater_than",
                "required_groups_at_terminal": 12,
            },
            "qualifying_option_types": qualifying,
            "families": family_rows,
        },
        training_rows,
    )


def _build_prepare_receipt(runtime: Mapping[str, Any]) -> dict[str, Any]:
    plan = _load_plan()
    correction = _load_correction()
    correction_v2 = _load_correction_v2()
    remediation = _load_prepare_audit_remediation()
    remediation_v2 = _load_prepare_audit_remediation_v2()
    remediation_v3 = _load_prepare_audit_remediation_v3()
    remediation_v4 = _load_prepare_audit_remediation_v4()
    remediation_v5 = _load_prepare_audit_remediation_v5()
    remediation_v6 = _load_prepare_audit_remediation_v6()
    remediation_v7 = _load_prepare_audit_remediation_v7()
    remediation_v8 = _load_prepare_audit_remediation_v8()
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
    if immutable["dataset_sha256"] != DATASET_SHA256 or immutable["on_policy_rows"] != EXPECTED_ON_POLICY_ROWS:
        raise ValueError("immutable dataset plan fields mismatch")
    if immutable["fixed_advantages_sha256"] != FIXED_ADVANTAGES_SHA256:
        raise ValueError("fixed advantages plan hash mismatch")
    if immutable["fixed_behavior_logprobabilities_sha256"] != FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256:
        raise ValueError("fixed behavior log-probabilities plan hash mismatch")
    source_plan = immutable["prepare_source"]
    if source_plan != {
        "path": PREPARE_SOURCE_RELATIVE_PATH.as_posix(),
        "file_sha256": PREPARE_SOURCE_FILE_SHA256,
        "receipt_sha256": PREPARE_SOURCE_RECEIPT_SHA256,
    }:
        raise ValueError("prepare source plan fields mismatch")
    pinned_probe = _load_and_reproduce_prepare_source(runtime)
    loaded = inherited._load_validated_inputs()
    if loaded["checkpoint_path"].resolve(strict=True) == _repo_path(
        REJECTED_CHECKPOINT_RELATIVE_PATH
    ).resolve(strict=True):
        raise ValueError("rejected checkpoint was loaded")
    if len(loaded["rows"]) != EXPECTED_ON_POLICY_ROWS:
        raise ValueError("loaded PPO row count mismatch")
    families, training_rows = _build_family_receipt(
        pinned_probe, loaded["rows"], pinned_probe["rows"]
    )
    parameters = _parameter_records(loaded["model"])
    before_hashes = {row["name"]: row["byte_sha256"] for row in parameters}
    after_hashes = {
        name: _tensor_sha256(parameter)
        for name, parameter in loaded["model"].named_parameters()
    }
    if before_hashes != after_hashes:
        raise ValueError("prepare changed initial model parameters")
    fixed_advantages = [
        float(row["fixed_normalized_advantage_float32"]) for row in training_rows
    ]
    fixed_logprobs = [float(row["behavior_logprob_float64"]) for row in training_rows]
    if canonical_sha256(fixed_advantages) != FIXED_ADVANTAGES_SHA256:
        raise ValueError("fixed advantage reproduction hash mismatch")
    if canonical_sha256(fixed_logprobs) != FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256:
        raise ValueError("fixed behavior log-probability reproduction hash mismatch")
    directional = _validated_directional_memberships(
        training_rows, pinned_probe["directional_memberships"]
    )
    snapshot = inherited.implementation_snapshot(_repo_path(IMPLEMENTATION_RELATIVE_PATH))
    initial_value_bytes = b"".join(
        bytes.fromhex(row["initial_value_raw_bytes_hex"]) for row in training_rows
    )
    initial_raw_value_mse = math.fsum(
        (
            float(row["initial_value_float32"])
            - float(row["fixed_value_target_float64"])
        ) ** 2
        for row in training_rows
    ) / EXPECTED_ON_POLICY_ROWS
    core = {
        "schema_version": PREPARE_RECEIPT_SCHEMA_VERSION,
        **_contract_bindings(),
        "plan": {
            "path": PLAN_RELATIVE_PATH.as_posix(),
            "file_sha256": PLAN_SHA256,
            "canonical_sha256": canonical_sha256(plan),
            "schema_version": PLAN_SCHEMA_VERSION,
            "plan_id": PLAN_ID,
            "contract": copy.deepcopy(plan),
        },
        "plan_correction": {
            "path": CORRECTION_RELATIVE_PATH.as_posix(),
            "file_sha256": CORRECTION_SHA256,
            "canonical_sha256": canonical_sha256(correction),
            "schema_version": CORRECTION_SCHEMA_VERSION,
            "correction_id": CORRECTION_ID,
            "contract": copy.deepcopy(correction),
        },
        "plan_correction_v2": {
            "path": CORRECTION_V2_RELATIVE_PATH.as_posix(),
            "file_sha256": CORRECTION_V2_SHA256,
            "canonical_sha256": canonical_sha256(correction_v2),
            "schema_version": CORRECTION_V2_SCHEMA_VERSION,
            "correction_id": CORRECTION_V2_ID,
            "contract": copy.deepcopy(correction_v2),
        },
        "prepare_audit_remediation": {
            "path": PREPARE_AUDIT_REMEDIATION_RELATIVE_PATH.as_posix(),
            "file_sha256": PREPARE_AUDIT_REMEDIATION_SHA256,
            "canonical_sha256": canonical_sha256(remediation),
            "schema_version": PREPARE_AUDIT_REMEDIATION_SCHEMA_VERSION,
            "remediation_id": PREPARE_AUDIT_REMEDIATION_ID,
            "contract": copy.deepcopy(remediation),
        },
        "prepare_audit_remediation_v2": {
            "path": PREPARE_AUDIT_REMEDIATION_V2_RELATIVE_PATH.as_posix(),
            "file_sha256": PREPARE_AUDIT_REMEDIATION_V2_SHA256,
            "canonical_sha256": canonical_sha256(remediation_v2),
            "schema_version": PREPARE_AUDIT_REMEDIATION_V2_SCHEMA_VERSION,
            "remediation_id": PREPARE_AUDIT_REMEDIATION_V2_ID,
            "contract": copy.deepcopy(remediation_v2),
        },
        "prepare_audit_remediation_v3": {
            "path": PREPARE_AUDIT_REMEDIATION_V3_RELATIVE_PATH.as_posix(),
            "file_sha256": PREPARE_AUDIT_REMEDIATION_V3_SHA256,
            "canonical_sha256": canonical_sha256(remediation_v3),
            "schema_version": PREPARE_AUDIT_REMEDIATION_V3_SCHEMA_VERSION,
            "remediation_id": PREPARE_AUDIT_REMEDIATION_V3_ID,
            "contract": copy.deepcopy(remediation_v3),
        },
        "prepare_audit_remediation_v4": {
            "path": PREPARE_AUDIT_REMEDIATION_V4_RELATIVE_PATH.as_posix(),
            "file_sha256": PREPARE_AUDIT_REMEDIATION_V4_SHA256,
            "canonical_sha256": canonical_sha256(remediation_v4),
            "schema_version": PREPARE_AUDIT_REMEDIATION_V4_SCHEMA_VERSION,
            "remediation_id": PREPARE_AUDIT_REMEDIATION_V4_ID,
            "contract": copy.deepcopy(remediation_v4),
        },
        "prepare_audit_remediation_v5": {
            "path": PREPARE_AUDIT_REMEDIATION_V5_RELATIVE_PATH.as_posix(),
            "file_sha256": PREPARE_AUDIT_REMEDIATION_V5_SHA256,
            "canonical_sha256": canonical_sha256(remediation_v5),
            "schema_version": PREPARE_AUDIT_REMEDIATION_V5_SCHEMA_VERSION,
            "remediation_id": PREPARE_AUDIT_REMEDIATION_V5_ID,
            "contract": copy.deepcopy(remediation_v5),
        },
        "prepare_audit_remediation_v6": {
            "path": PREPARE_AUDIT_REMEDIATION_V6_RELATIVE_PATH.as_posix(),
            "file_sha256": PREPARE_AUDIT_REMEDIATION_V6_SHA256,
            "canonical_sha256": canonical_sha256(remediation_v6),
            "schema_version": PREPARE_AUDIT_REMEDIATION_V6_SCHEMA_VERSION,
            "remediation_id": PREPARE_AUDIT_REMEDIATION_V6_ID,
            "contract": copy.deepcopy(remediation_v6),
        },
        "prepare_audit_remediation_v7": {
            "path": PREPARE_AUDIT_REMEDIATION_V7_RELATIVE_PATH.as_posix(),
            "file_sha256": PREPARE_AUDIT_REMEDIATION_V7_SHA256,
            "canonical_sha256": canonical_sha256(remediation_v7),
            "schema_version": PREPARE_AUDIT_REMEDIATION_V7_SCHEMA_VERSION,
            "remediation_id": PREPARE_AUDIT_REMEDIATION_V7_ID,
            "contract": copy.deepcopy(remediation_v7),
        },
        "prepare_audit_remediation_v8": {
            "path": PREPARE_AUDIT_REMEDIATION_V8_RELATIVE_PATH.as_posix(),
            "file_sha256": PREPARE_AUDIT_REMEDIATION_V8_SHA256,
            "canonical_sha256": canonical_sha256(remediation_v8),
            "schema_version": PREPARE_AUDIT_REMEDIATION_V8_SCHEMA_VERSION,
            "remediation_id": PREPARE_AUDIT_REMEDIATION_V8_ID,
            "contract": copy.deepcopy(remediation_v8),
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
            "on_policy_rows": EXPECTED_ON_POLICY_ROWS,
            "fixed_advantages_sha256": FIXED_ADVANTAGES_SHA256,
            "fixed_behavior_logprobabilities_sha256": (
                FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256
            ),
            "prepare_source_path": PREPARE_SOURCE_RELATIVE_PATH.as_posix(),
            "prepare_source_file_sha256": PREPARE_SOURCE_FILE_SHA256,
            "prepare_source_receipt_sha256": PREPARE_SOURCE_RECEIPT_SHA256,
            "prepare_source_exact_reproduction": True,
        },
        "training_contract": copy.deepcopy(plan["training_contract"]),
        "diagnostic_contract": copy.deepcopy(plan["diagnostic_contract"]),
        "safety_gates": copy.deepcopy(plan["safety_gates"]),
        "terminal_offline_acceptance": copy.deepcopy(
            plan["terminal_offline_acceptance"]
        ),
        "stop_contract": {
            "forbidden_changes": copy.deepcopy(plan["forbidden_changes"]),
            "output_semantics": copy.deepcopy(plan["output_semantics"]),
            "post_rejection_action_if_falsified": plan[
                "post_rejection_action_if_falsified"
            ],
            "execution_stop_rule": plan["execution_stop_rule"],
        },
        "row_count": len(training_rows),
        "unique_decision_key_count": len(
            {(row["episode_id"], row["decision_index"]) for row in training_rows}
        ),
        "ordered_training_rows_sha256": canonical_sha256(training_rows),
        "rows": training_rows,
        "action_families": families,
        "directional_memberships": directional,
        "initial_value_identity": {
            "row_count": EXPECTED_ON_POLICY_ROWS,
            "per_row_byte_sha256": [
                row["initial_value_byte_sha256"] for row in training_rows
            ],
            "ordered_raw_bytes_sha256": hashlib.sha256(
                initial_value_bytes
            ).hexdigest().upper(),
            "raw_value_mse": initial_raw_value_mse,
        },
        "model_parameters": {
            "records": parameters,
            "records_sha256": canonical_sha256(parameters),
            "actor_parameter_names": list(EXPECTED_ACTOR_NAMES),
            "value_head_parameter_names": list(EXPECTED_VALUE_NAMES),
            "optimizer_parameter_names": list(OPTIMIZER_PARAMETER_NAMES),
            "stage_1_trainable_names": list(STAGE1_TRAINABLE_NAMES),
            "stage_2_trainable_names": list(STAGE2_TRAINABLE_NAMES),
            "initial_parameter_hashes": before_hashes,
            "initial_value_outputs_sha256": canonical_sha256(
                [row["initial_value_float32"] for row in training_rows]
            ),
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
            "training_executed": False,
            "runtime_smoke_executed": False,
            "games_run": 0,
        },
    }
    return {**core, "receipt_sha256": canonical_sha256(core)}


_PREPARE_RECEIPT_KEYS = {
    "schema_version", "plan", "plan_correction", "plan_correction_v2",
    "prepare_audit_remediation", "prepare_audit_remediation_v2",
    "prepare_audit_remediation_v3", "prepare_audit_remediation_v4",
    "prepare_audit_remediation_v5", "prepare_audit_remediation_v6",
    "prepare_audit_remediation_v7", "prepare_audit_remediation_v8",
    "implementation_plan_path", "implementation_plan_sha256",
    "plan_correction_path", "plan_correction_sha256",
    "plan_correction_v2_path", "plan_correction_v2_sha256",
    "prepare_audit_remediation_path", "prepare_audit_remediation_sha256",
    "prepare_audit_remediation_v2_path", "prepare_audit_remediation_v2_sha256",
    "prepare_audit_remediation_v3_path", "prepare_audit_remediation_v3_sha256",
    "prepare_audit_remediation_v4_path", "prepare_audit_remediation_v4_sha256",
    "prepare_audit_remediation_v5_path", "prepare_audit_remediation_v5_sha256",
    "prepare_audit_remediation_v6_path", "prepare_audit_remediation_v6_sha256",
    "prepare_audit_remediation_v7_path", "prepare_audit_remediation_v7_sha256",
    "prepare_audit_remediation_v8_path", "prepare_audit_remediation_v8_sha256",
    "parent_rejection", "source_implementation",
    "implementation", "runtime_thread_receipt", "immutable_inputs",
    "training_contract", "diagnostic_contract", "safety_gates",
    "terminal_offline_acceptance", "stop_contract",
    "row_count", "unique_decision_key_count",
    "ordered_training_rows_sha256", "rows", "action_families",
    "directional_memberships", "initial_value_identity", "model_parameters",
    "prepare_proof", "receipt_sha256",
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
    correction = _load_correction()
    correction_v2 = _load_correction_v2()
    remediation = _load_prepare_audit_remediation()
    remediation_v2 = _load_prepare_audit_remediation_v2()
    remediation_v3 = _load_prepare_audit_remediation_v3()
    remediation_v4 = _load_prepare_audit_remediation_v4()
    remediation_v5 = _load_prepare_audit_remediation_v5()
    remediation_v6 = _load_prepare_audit_remediation_v6()
    remediation_v7 = _load_prepare_audit_remediation_v7()
    remediation_v8 = _load_prepare_audit_remediation_v8()
    for name, value in _contract_bindings().items():
        if row[name] != value:
            raise ValueError(f"prepare receipt contract binding mismatch: {name}")
    expected_plan = {
        "path": PLAN_RELATIVE_PATH.as_posix(),
        "file_sha256": PLAN_SHA256,
        "canonical_sha256": canonical_sha256(plan),
        "schema_version": PLAN_SCHEMA_VERSION,
        "plan_id": PLAN_ID,
        "contract": plan,
    }
    if row["plan"] != expected_plan:
        raise ValueError("prepare receipt base-plan binding mismatch")
    if row["plan_correction"] != {
        "path": CORRECTION_RELATIVE_PATH.as_posix(),
        "file_sha256": CORRECTION_SHA256,
        "canonical_sha256": canonical_sha256(correction),
        "schema_version": CORRECTION_SCHEMA_VERSION,
        "correction_id": CORRECTION_ID,
        "contract": correction,
    }:
        raise ValueError("prepare receipt correction binding mismatch")
    if row["plan_correction_v2"] != {
        "path": CORRECTION_V2_RELATIVE_PATH.as_posix(),
        "file_sha256": CORRECTION_V2_SHA256,
        "canonical_sha256": canonical_sha256(correction_v2),
        "schema_version": CORRECTION_V2_SCHEMA_VERSION,
        "correction_id": CORRECTION_V2_ID,
        "contract": correction_v2,
    }:
        raise ValueError("prepare receipt post-audit correction binding mismatch")
    if row["prepare_audit_remediation"] != {
        "path": PREPARE_AUDIT_REMEDIATION_RELATIVE_PATH.as_posix(),
        "file_sha256": PREPARE_AUDIT_REMEDIATION_SHA256,
        "canonical_sha256": canonical_sha256(remediation),
        "schema_version": PREPARE_AUDIT_REMEDIATION_SCHEMA_VERSION,
        "remediation_id": PREPARE_AUDIT_REMEDIATION_ID,
        "contract": remediation,
    }:
        raise ValueError("prepare receipt remediation binding mismatch")
    if row["prepare_audit_remediation_v2"] != {
        "path": PREPARE_AUDIT_REMEDIATION_V2_RELATIVE_PATH.as_posix(),
        "file_sha256": PREPARE_AUDIT_REMEDIATION_V2_SHA256,
        "canonical_sha256": canonical_sha256(remediation_v2),
        "schema_version": PREPARE_AUDIT_REMEDIATION_V2_SCHEMA_VERSION,
        "remediation_id": PREPARE_AUDIT_REMEDIATION_V2_ID,
        "contract": remediation_v2,
    }:
        raise ValueError("prepare receipt remediation v2 binding mismatch")
    if row["prepare_audit_remediation_v3"] != {
        "path": PREPARE_AUDIT_REMEDIATION_V3_RELATIVE_PATH.as_posix(),
        "file_sha256": PREPARE_AUDIT_REMEDIATION_V3_SHA256,
        "canonical_sha256": canonical_sha256(remediation_v3),
        "schema_version": PREPARE_AUDIT_REMEDIATION_V3_SCHEMA_VERSION,
        "remediation_id": PREPARE_AUDIT_REMEDIATION_V3_ID,
        "contract": remediation_v3,
    }:
        raise ValueError("prepare receipt remediation v3 binding mismatch")
    if row["prepare_audit_remediation_v4"] != {
        "path": PREPARE_AUDIT_REMEDIATION_V4_RELATIVE_PATH.as_posix(),
        "file_sha256": PREPARE_AUDIT_REMEDIATION_V4_SHA256,
        "canonical_sha256": canonical_sha256(remediation_v4),
        "schema_version": PREPARE_AUDIT_REMEDIATION_V4_SCHEMA_VERSION,
        "remediation_id": PREPARE_AUDIT_REMEDIATION_V4_ID,
        "contract": remediation_v4,
    }:
        raise ValueError("prepare receipt remediation v4 binding mismatch")
    if row["prepare_audit_remediation_v5"] != {
        "path": PREPARE_AUDIT_REMEDIATION_V5_RELATIVE_PATH.as_posix(),
        "file_sha256": PREPARE_AUDIT_REMEDIATION_V5_SHA256,
        "canonical_sha256": canonical_sha256(remediation_v5),
        "schema_version": PREPARE_AUDIT_REMEDIATION_V5_SCHEMA_VERSION,
        "remediation_id": PREPARE_AUDIT_REMEDIATION_V5_ID,
        "contract": remediation_v5,
    }:
        raise ValueError("prepare receipt remediation v5 binding mismatch")
    if row["prepare_audit_remediation_v6"] != {
        "path": PREPARE_AUDIT_REMEDIATION_V6_RELATIVE_PATH.as_posix(),
        "file_sha256": PREPARE_AUDIT_REMEDIATION_V6_SHA256,
        "canonical_sha256": canonical_sha256(remediation_v6),
        "schema_version": PREPARE_AUDIT_REMEDIATION_V6_SCHEMA_VERSION,
        "remediation_id": PREPARE_AUDIT_REMEDIATION_V6_ID,
        "contract": remediation_v6,
    }:
        raise ValueError("prepare receipt remediation v6 binding mismatch")
    if row["prepare_audit_remediation_v7"] != {
        "path": PREPARE_AUDIT_REMEDIATION_V7_RELATIVE_PATH.as_posix(),
        "file_sha256": PREPARE_AUDIT_REMEDIATION_V7_SHA256,
        "canonical_sha256": canonical_sha256(remediation_v7),
        "schema_version": PREPARE_AUDIT_REMEDIATION_V7_SCHEMA_VERSION,
        "remediation_id": PREPARE_AUDIT_REMEDIATION_V7_ID,
        "contract": remediation_v7,
    }:
        raise ValueError("prepare receipt remediation v7 binding mismatch")
    if row["prepare_audit_remediation_v8"] != {
        "path": PREPARE_AUDIT_REMEDIATION_V8_RELATIVE_PATH.as_posix(),
        "file_sha256": PREPARE_AUDIT_REMEDIATION_V8_SHA256,
        "canonical_sha256": canonical_sha256(remediation_v8),
        "schema_version": PREPARE_AUDIT_REMEDIATION_V8_SCHEMA_VERSION,
        "remediation_id": PREPARE_AUDIT_REMEDIATION_V8_ID,
        "contract": remediation_v8,
    }:
        raise ValueError("prepare receipt remediation v8 binding mismatch")
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
        "on_policy_rows": EXPECTED_ON_POLICY_ROWS,
        "fixed_advantages_sha256": FIXED_ADVANTAGES_SHA256,
        "fixed_behavior_logprobabilities_sha256": (
            FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256
        ),
        "prepare_source_path": PREPARE_SOURCE_RELATIVE_PATH.as_posix(),
        "prepare_source_file_sha256": PREPARE_SOURCE_FILE_SHA256,
        "prepare_source_receipt_sha256": PREPARE_SOURCE_RECEIPT_SHA256,
        "prepare_source_exact_reproduction": True,
    }
    if row["immutable_inputs"] != expected_inputs:
        raise ValueError("prepare receipt immutable inputs mismatch")
    if (
        sha256_file(_repo_path(INPUT_CHECKPOINT_RELATIVE_PATH)) != INPUT_CHECKPOINT_SHA256
        or sha256_file(_repo_path(MANIFEST_RELATIVE_PATH)) != MANIFEST_SHA256
        or sha256_file(_repo_path(PREPARE_SOURCE_RELATIVE_PATH))
        != PREPARE_SOURCE_FILE_SHA256
    ):
        raise ValueError("prepare receipt immutable input file changed")
    if row["training_contract"] != plan["training_contract"]:
        raise ValueError("prepare receipt training contract mismatch")
    if row["diagnostic_contract"] != plan["diagnostic_contract"]:
        raise ValueError("prepare receipt diagnostic contract mismatch")
    if row["safety_gates"] != plan["safety_gates"]:
        raise ValueError("prepare receipt safety-gate contract mismatch")
    if row["terminal_offline_acceptance"] != plan["terminal_offline_acceptance"]:
        raise ValueError("prepare receipt terminal-gate contract mismatch")
    if row["stop_contract"] != {
        "forbidden_changes": plan["forbidden_changes"],
        "output_semantics": plan["output_semantics"],
        "post_rejection_action_if_falsified": plan[
            "post_rejection_action_if_falsified"
        ],
        "execution_stop_rule": plan["execution_stop_rule"],
    }:
        raise ValueError("prepare receipt stop contract mismatch")
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
    if canonical_sha256(
        [float(item["fixed_normalized_advantage_float32"]) for item in rows]
    ) != FIXED_ADVANTAGES_SHA256:
        raise ValueError("prepare receipt fixed-advantage hash mismatch")
    if canonical_sha256(
        [float(item["behavior_logprob_float64"]) for item in rows]
    ) != FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256:
        raise ValueError("prepare receipt behavior-logprobability hash mismatch")
    row_keys = {
        "ppo_row_ordinal", "episode_id", "decision_index", "raw_observation_sha256",
        "public_state_sha256", "behavior_action_order_sha256", "teacher_index",
        "sampled_index", "sampled_semantic_identity", "sampled_option_type",
        "end_index", "legal_option_count", "behavior_logprob_float64",
        "raw_advantage_float64", "fixed_value_target_float64",
        "fixed_normalized_advantage_float32", "initial_probabilities_float32",
        "initial_value_float32", "initial_value_raw_bytes_hex",
        "initial_value_byte_sha256",
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
        initial_probabilities, _ = _authoritative_float32_probability_vector(
            item["initial_probabilities_float32"],
            label=f"prepare training row {ordinal} initial probabilities",
        )
        if (
            any(not (0.0 < value <= 1.0) for value in initial_probabilities)
            or abs(math.fsum(initial_probabilities) - 1.0) > 1e-6
        ):
            raise ValueError("prepare training row probability domain mismatch")
        value_tensor = torch.tensor(item["initial_value_float32"], dtype=torch.float32)
        if (
            item["initial_value_raw_bytes_hex"] != _tensor_bytes(value_tensor).hex().upper()
            or item["initial_value_byte_sha256"] != _tensor_sha256(value_tensor)
        ):
            raise ValueError("prepare training row value-byte identity mismatch")
    ordered_value_bytes = b"".join(
        bytes.fromhex(item["initial_value_raw_bytes_hex"]) for item in rows
    )
    expected_raw_value_mse = math.fsum(
        (float(item["initial_value_float32"]) - float(item["fixed_value_target_float64"])) ** 2
        for item in rows
    ) / EXPECTED_ON_POLICY_ROWS
    if row["initial_value_identity"] != {
        "row_count": EXPECTED_ON_POLICY_ROWS,
        "per_row_byte_sha256": [item["initial_value_byte_sha256"] for item in rows],
        "ordered_raw_bytes_sha256": hashlib.sha256(ordered_value_bytes).hexdigest().upper(),
        "raw_value_mse": expected_raw_value_mse,
    }:
        raise ValueError("prepare receipt initial value identity mismatch")
    proof = row["prepare_proof"]
    if proof != {
        "optimizer_constructed": False,
        "optimizer_steps": 0,
        "checkpoint_written": False,
        "parameters_changed": False,
        "rejected_checkpoint_loaded": False,
        "training_executed": False,
        "runtime_smoke_executed": False,
        "games_run": 0,
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
    if [item["name"] for item in family_rows if item["qualifying"]] != plan[
        "terminal_offline_acceptance"
    ]["qualifying_action_families"]:
        raise ValueError("prepare receipt qualifying family names mismatch")
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
    prepare_source = inherited._load_hashed_json(
        _repo_path(PREPARE_SOURCE_RELATIVE_PATH), PREPARE_SOURCE_FILE_SHA256,
        label="prepare validation source receipt",
    )
    predecessor.validate_prepare_receipt(prepare_source)
    plan_families = prepare_source["action_families"]["families"]
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
        expected_summary = {
            name: expected[name]
            for name in (
                "option_type", "name", "rows", "normalized_positive",
                "normalized_negative", "membership_sha256", "qualifying",
            )
        }
        if (
            summary != expected_summary
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
            "value_head_parameter_names", "optimizer_parameter_names",
            "stage_1_trainable_names", "stage_2_trainable_names",
            "initial_parameter_hashes", "initial_value_outputs_sha256",
            "value_head_baseline_sha256",
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
        or model_parameters["optimizer_parameter_names"] != list(OPTIMIZER_PARAMETER_NAMES)
        or model_parameters["stage_1_trainable_names"] != list(STAGE1_TRAINABLE_NAMES)
        or model_parameters["stage_2_trainable_names"] != list(STAGE2_TRAINABLE_NAMES)
        or model_parameters["initial_parameter_hashes"]
        != {item["name"]: item["byte_sha256"] for item in parameter_records}
        or model_parameters["initial_value_outputs_sha256"]
        != canonical_sha256([item["initial_value_float32"] for item in rows])
    ):
        raise ValueError("prepare receipt parameter trainability mismatch")
    parameter_keys = {
        "name", "dtype", "shape", "numel", "byte_count", "byte_sha256",
        "stage_1_trainable", "stage_2_trainable", "optimizer_parameter_universe",
    }
    for item in parameter_records:
        _exact_keys(item, parameter_keys, label="prepare parameter record")
    directional = _validated_directional_memberships(
        rows, row["directional_memberships"]
    )
    expected_directional = prepare_source["directional_memberships"]
    if directional != expected_directional:
        raise ValueError("prepare receipt directional ordinal set mismatch")


def _absolute_prepare_candidate(path: Path) -> Path:
    if ".." in path.parts or "." in path.parts:
        raise ValueError("prepare receipt path must not contain aliases")
    return (path if path.is_absolute() else Path.cwd() / path).absolute()


def _validate_prepare_output_path(path: Path, *, must_exist: bool = False) -> Path:
    candidate = _absolute_prepare_candidate(path)
    implementation_root = _repo_path(IMPLEMENTATION_RELATIVE_PATH).resolve(strict=True)
    approved_root = implementation_root / "test_outputs"
    expected = _repo_path(APPROVED_PREPARE_RELATIVE_PATH).absolute()
    if candidate != expected:
        raise ValueError("prepare receipt path is not the corrected exact path")
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
    if relative.as_posix() != "phase1_iteration_007_prepare_v4/pretraining_probe_receipt.json":
        raise ValueError("prepare receipt is outside the approved prepare subtree")
    if must_exist:
        if not resolved.is_file() or inherited._is_link_or_reparse(resolved):
            raise ValueError("prepare receipt must be an existing regular non-link file")
    elif resolved.exists() or resolved.is_symlink():
        raise FileExistsError("prepare receipt already exists")
    elif resolved.parent.exists() and (
        not resolved.parent.is_dir() or inherited._is_link_or_reparse(resolved.parent)
    ):
        raise ValueError("prepare receipt parent is not a regular directory")
    return resolved


def prepare(*, output_receipt: Path) -> dict[str, Any]:
    """Write one canonical no-training receipt using CREATE_NEW semantics."""

    output = _validate_prepare_output_path(output_receipt)
    test_outputs = output.parent.parent
    if not test_outputs.exists():
        test_outputs.mkdir()
    if not test_outputs.is_dir() or inherited._is_link_or_reparse(test_outputs):
        raise ValueError("prepare test_outputs is not a regular directory")
    if not output.parent.exists():
        output.parent.mkdir()
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
    stage_2_updates_completed: int = 0
    stage_2_entered: bool = False
    failure_phase: str = "pre_step"


def _optimizer_step_and_record(
    optimizer: torch.optim.Adam,
    progress: ExecutionProgress,
    *,
    stage: int,
    stage_2_update_ordinal: int | None = None,
) -> None:
    if stage not in (1, 2):
        raise ValueError("optimizer progress stage must be 1 or 2")
    expected_ordinal = 1 if stage == 1 else 1 + int(stage_2_update_ordinal or 0)
    if stage == 1 and stage_2_update_ordinal is not None:
        raise ValueError("Stage 1 must not have a Stage-2 update ordinal")
    if stage == 2 and not (1 <= int(stage_2_update_ordinal or 0) <= STAGE2_UPDATES):
        raise ValueError("Stage-2 update ordinal mismatch")
    if progress.optimizer_steps_completed != expected_ordinal - 1:
        raise ValueError("optimizer progress ordinal mismatch before step")
    optimizer.step()
    progress.optimizer_steps_completed = expected_ordinal
    if stage == 2:
        progress.stage_2_updates_completed = int(stage_2_update_ordinal)


def _set_trainability(model: torch.nn.Module, *, stage: int) -> None:
    named = _named_parameters(model)
    trainable = set(STAGE1_TRAINABLE_NAMES if stage == 1 else STAGE2_TRAINABLE_NAMES)
    for name, parameter in named.items():
        parameter.requires_grad_(name in trainable)
    actual = {name for name, parameter in named.items() if parameter.requires_grad}
    if actual != trainable:
        raise ValueError(f"stage-{stage} trainability mismatch")


def _new_actor_adam(model: torch.nn.Module) -> torch.optim.Adam:
    named = _named_parameters(model)
    optimizer = torch.optim.Adam(
        [named[name] for name in OPTIMIZER_PARAMETER_NAMES],
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
        id(named[name]) for name in OPTIMIZER_PARAMETER_NAMES
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
        if name is None or name not in OPTIMIZER_PARAMETER_NAMES:
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
    optimizer: torch.optim.Adam,
    model: torch.nn.Module,
    *,
    stage: int,
    stage_2_update_ordinal: int | None = None,
) -> dict[str, int]:
    """Validate the exact mixed Adam step state after a synthetic or real stage."""

    if stage not in (1, 2):
        raise ValueError("optimizer contract stage must be 1 or 2")
    named = _named_parameters(model)
    if len(optimizer.param_groups) != 1 or tuple(
        id(parameter) for parameter in optimizer.param_groups[0]["params"]
    ) != tuple(id(named[name]) for name in OPTIMIZER_PARAMETER_NAMES):
        raise ValueError("optimizer four-parameter group changed")
    steps = _optimizer_step_states(optimizer, model)
    if stage == 1:
        if stage_2_update_ordinal is not None:
            raise ValueError("Stage 1 has no Stage-2 update ordinal")
        expected = {name: 1 for name in STAGE1_TRAINABLE_NAMES}
    else:
        ordinal = int(stage_2_update_ordinal or 0)
        if not 1 <= ordinal <= STAGE2_UPDATES:
            raise ValueError("Stage-2 optimizer audit ordinal mismatch")
        expected = {
            **{name: ordinal for name in STAGE2_TRAINABLE_NAMES},
            **{name: 1 for name in STAGE1_TRAINABLE_NAMES},
        }
    if steps != expected:
        raise ValueError(f"stage-{stage} optimizer step-state mismatch")
    if any(
        named[name] in optimizer.state
        for name in (*EXPECTED_VALUE_NAMES, *[n for n in EXPECTED_ACTOR_NAMES if n not in OPTIMIZER_PARAMETER_NAMES])
    ):
        raise ValueError("frozen parameter unexpectedly has optimizer state")
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
    stage_2_update_ordinal: int | None = None,
    stage_2_start_parameters: Mapping[str, torch.Tensor] | None = None,
) -> dict[str, Any]:
    if stage not in (1, 2):
        raise ValueError("stage must be 1 or 2")
    model = loaded["model"]
    rows = loaded["rows"]
    fixed_rows = prepare_receipt["rows"]
    execution_fixed = loaded.get("execution_fixed_inputs")
    if not isinstance(execution_fixed, Mapping) or execution_fixed.get(
        "gae_recomputation_count"
    ) != 1:
        raise ValueError("authorized execution fixed inputs are missing")
    reference_config = loaded["reference_config"]
    _set_trainability(model, stage=stage)
    stage_before = {
        name: value.detach().clone() for name, value in model.state_dict().items()
    }
    if stage == 2:
        if stage_2_start_parameters is None:
            raise ValueError("Stage-2 fixed start snapshot is missing")
        fixed_stage_start = stage_2_start_parameters
    else:
        if stage_2_start_parameters is not None:
            raise ValueError("Stage 1 must not receive a Stage-2 start snapshot")
        fixed_stage_start = stage_before
    value_before = {
        name: value.detach().clone()
        for name, value in model.state_dict().items()
        if name.startswith(VALUE_PREFIX)
    }
    frozen_before = {
        name: value.detach().clone()
        for name, value in model.state_dict().items()
        if name not in (STAGE1_TRAINABLE_NAMES if stage == 1 else STAGE2_TRAINABLE_NAMES)
    }
    readout_optimizer_before = {
        name: copy.deepcopy(optimizer.state.get(dict(model.named_parameters())[name]))
        for name in STAGE1_TRAINABLE_NAMES
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
        normalized_value = float(
            execution_fixed["normalized_advantages_float32"][ordinal]
        )
        old_logprob_value = float(
            execution_fixed["behavior_logprobabilities_float64"][ordinal]
        )
        if (
            normalized_value != float(fixed["fixed_normalized_advantage_float32"])
            or old_logprob_value != float(fixed["behavior_logprob_float64"])
            or int(execution_fixed["sampled_indices"][ordinal])
            != int(fixed["sampled_index"])
        ):
            raise ValueError("authorized execution fixed row changed")
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
        STAGE1_TRAINABLE_NAMES if stage == 1 else STAGE2_TRAINABLE_NAMES
    )
    if set(gradients) != expected_gradient_names:
        raise ValueError(f"stage-{stage} gradient parameter set mismatch")
    inherited._finite_tensors_or_raise(gradients.values(), label=f"stage-{stage} gradient")
    gradient_before = {
        name: float(torch.linalg.vector_norm(value.detach()).cpu())
        for name, value in gradients.items()
    }
    gradient_norm = torch.nn.utils.clip_grad_norm_(
        [named[name] for name in sorted(expected_gradient_names)],
        TWO_STAGE_PPO_CONFIG.gradient_clip,
        error_if_nonfinite=True,
    )
    inherited._finite_tensors_or_raise((gradient_norm,), label=f"stage-{stage} gradient norm")
    gradient_after = {
        name: float(torch.linalg.vector_norm(value.detach()).cpu())
        for name, value in gradients.items()
    }
    if stage == 2 and any(value == 0.0 for value in gradient_before.values()):
        raise ValueError("Stage-2 interaction gradient must be finite and nonzero")
    _optimizer_step_and_record(
        optimizer,
        progress,
        stage=stage,
        stage_2_update_ordinal=stage_2_update_ordinal,
    )
    inherited._finite_tensors_or_raise(model.parameters(), label=f"stage-{stage} parameter")
    if any(
        not torch.equal(value, model.state_dict()[name])
        for name, value in value_before.items()
    ):
        raise ValueError(f"stage-{stage} changed a value-head parameter")
    if any(
        not torch.equal(value, model.state_dict()[name])
        for name, value in frozen_before.items()
    ):
        raise ValueError(f"stage-{stage} changed a frozen parameter")
    changed_from_stage_start = [
        name
        for name, value in fixed_stage_start.items()
        if not torch.equal(value, model.state_dict()[name])
    ]
    changed_from_initial = [
        name
        for name, value in initial_parameters.items()
        if not torch.equal(value, model.state_dict()[name])
    ]
    expected_initial = list(
        STAGE1_TRAINABLE_NAMES
        if stage == 1
        else (*STAGE2_TRAINABLE_NAMES, *STAGE1_TRAINABLE_NAMES)
    )
    if changed_from_initial != expected_initial:
        raise ValueError(f"stage-{stage} changed-parameter contract mismatch")
    if stage == 1 and changed_from_stage_start != list(STAGE1_TRAINABLE_NAMES):
        raise ValueError("stage-1 changed-parameter set mismatch")
    if stage == 2 and changed_from_stage_start != list(STAGE2_TRAINABLE_NAMES):
        raise ValueError("stage-2 changed-parameter set mismatch")
    if stage == 2 and any(
        not _nested_byte_exact(
            readout_optimizer_before[name], optimizer.state[dict(model.named_parameters())[name]]
        )
        for name in STAGE1_TRAINABLE_NAMES
    ):
        raise ValueError("Stage-2 changed frozen readout Adam moments")
    optimizer_steps = audit_optimizer_contract(
        optimizer,
        model,
        stage=stage,
        stage_2_update_ordinal=stage_2_update_ordinal,
    )
    optimizer_step_ordinal = 1 if stage == 1 else 1 + int(stage_2_update_ordinal)
    return {
        "stage": stage,
        "optimizer_step_ordinal": optimizer_step_ordinal,
        "stage_2_update_ordinal": stage_2_update_ordinal,
        "optimizer_state_steps": optimizer_steps,
        "trainable_parameter_names": sorted(expected_gradient_names),
        "gradient_parameter_names": sorted(gradients),
        "gradient_norm_before_clipping": float(gradient_norm.detach().cpu()),
        "per_parameter_gradient_norm_before_clipping": gradient_before,
        "per_parameter_gradient_norm_after_clipping": gradient_after,
        "changed_parameter_names_from_stage_start": changed_from_stage_start,
        "changed_parameter_names_from_initial": changed_from_initial,
        "parameter_diffs_from_previous_step": _parameter_diff_records(model, stage_before),
        "parameter_diffs_from_stage_start": _parameter_diff_records(
            model, fixed_stage_start
        ),
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
        "frozen_readout_optimizer_state_unchanged": None if stage == 1 else True,
        "nonfinite_value_gradient_optimizer_or_parameter_count": 0,
    }


def _measure_stage(
    loaded: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    *,
    stage: int,
    stage_2_update_ordinal: int | None = None,
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
            inherited._finite_tensors_or_raise(
                (residuals, value, probabilities), label=f"stage-{stage} measurement"
            )
            post, probability_raw = _authoritative_float32_probability_vector(
                probabilities.detach().cpu().tolist(),
                label=f"stage-{stage} row {ordinal} measured probabilities",
            )
            initial, _ = _authoritative_float32_probability_vector(
                fixed["initial_probabilities_float32"],
                label=f"stage-{stage} row {ordinal} initial probabilities",
            )
            sampled = int(fixed["sampled_index"])
            delta = post[sampled] - initial[sampled]
            normalized = float(fixed["fixed_normalized_advantage_float32"])
            oriented = (1.0 if normalized > 0.0 else -1.0) * delta
            maximum = max(post)
            winners = [index for index, item in enumerate(post) if item == maximum]
            initial_value_tensor = torch.tensor(
                float(fixed["initial_value_float32"]), dtype=torch.float32
            )
            value_exact = _tensor_bytes(value.reshape(())) == _tensor_bytes(
                initial_value_tensor.reshape(())
            )
            value_raw = _tensor_bytes(value.reshape(()))
            metrics.append(
                {
                    "stage": stage,
                    "stage_2_update_ordinal": stage_2_update_ordinal,
                    "ppo_row_ordinal": ordinal,
                    "public_state_sha256": fixed["public_state_sha256"],
                    "behavior_action_order_sha256": fixed["behavior_action_order_sha256"],
                    "sampled_index": sampled,
                    "teacher_index": int(fixed["teacher_index"]),
                    "end_index": int(fixed["end_index"]),
                    "legal_option_count": int(fixed["legal_option_count"]),
                    "sampled_option_type": int(fixed["sampled_option_type"]),
                    "sampled_semantic_identity": fixed["sampled_semantic_identity"],
                    "probabilities_float32": post,
                    "probabilities_raw_bytes_hex": probability_raw.hex().upper(),
                    "probabilities_byte_sha256": hashlib.sha256(
                        probability_raw
                    ).hexdigest().upper(),
                    "value_float32": float(value.detach().cpu()),
                    "value_raw_bytes_hex": value_raw.hex().upper(),
                    "value_byte_sha256": hashlib.sha256(value_raw).hexdigest().upper(),
                    "value_output_byte_exact_to_initial": value_exact,
                    "unique_argmax_index": winners[0] if len(winners) == 1 else None,
                    "sampled_probability_delta_from_initial": delta,
                    "oriented_sampled_probability_delta": oriented,
                    "orientation": orientation_class(oriented),
                    "anchor_kl_post_to_zero": inherited.per_row_anchor_kl(
                        post, initial
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
        if (
            metric.get("public_state_sha256") != fixed["public_state_sha256"]
            or metric.get("behavior_action_order_sha256")
            != fixed["behavior_action_order_sha256"]
            or metric.get("sampled_index") != fixed["sampled_index"]
            or metric.get("teacher_index") != fixed["teacher_index"]
            or metric.get("end_index") != fixed["end_index"]
            or metric.get("legal_option_count") != fixed["legal_option_count"]
            or metric.get("sampled_option_type") != fixed["sampled_option_type"]
            or metric.get("sampled_semantic_identity")
            != fixed["sampled_semantic_identity"]
        ):
            failures.append(f"row:{ordinal}:identity")
        probabilities = metric.get("probabilities_float32")
        if not isinstance(probabilities, list) or len(probabilities) != fixed["legal_option_count"]:
            failures.append(f"row:{ordinal}:probability_dimension")
            nonfinite_count += 1
            continue
        try:
            probabilities, probability_raw = _authoritative_float32_probability_vector(
                probabilities, label=f"metric row {ordinal} probabilities"
            )
            initial, _ = _authoritative_float32_probability_vector(
                fixed["initial_probabilities_float32"],
                label=f"metric row {ordinal} initial probabilities",
            )
        except ValueError:
            failures.append(f"row:{ordinal}:probability_float32_roundtrip")
            nonfinite_count += 1
            continue
        metric["probabilities_float32"] = probabilities
        if (
            metric.get("probabilities_raw_bytes_hex") != probability_raw.hex().upper()
            or metric.get("probabilities_byte_sha256")
            != hashlib.sha256(probability_raw).hexdigest().upper()
        ):
            failures.append(f"row:{ordinal}:probability_raw_bytes")
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
        probability_sum = math.fsum(probabilities)
        if any(not (0.0 < value <= 1.0) for value in probabilities):
            failures.append(f"row:{ordinal}:probability_domain")
        if abs(probability_sum - 1.0) > 1e-6:
            failures.append(f"row:{ordinal}:probability_normalization")
        maximum = max(probabilities)
        winners = [
            index for index, value in enumerate(probabilities)
            if value == maximum
        ]
        if len(winners) != 1:
            failures.append(f"row:{ordinal}:unique_argmax")
        elif metric.get("unique_argmax_index") != winners[0]:
            failures.append(f"row:{ordinal}:unique_argmax_identity")
        sampled = int(fixed["sampled_index"])
        delta = probabilities[sampled] - initial[sampled]
        normalized = float(fixed["fixed_normalized_advantage_float32"])
        oriented = (1.0 if normalized > 0.0 else -1.0) * delta
        try:
            recomputed_kl = inherited.per_row_anchor_kl(
                probabilities,
                initial,
            )
            recomputed_tv = inherited.per_row_total_variation(
                probabilities,
                initial,
            )
        except ValueError:
            failures.append(f"row:{ordinal}:derived_recomputation")
        else:
            if float(metric["anchor_kl_post_to_zero"]) != recomputed_kl:
                failures.append(f"row:{ordinal}:anchor_kl_recomputation")
            if float(metric["total_variation_from_initial"]) != recomputed_tv:
                failures.append(f"row:{ordinal}:total_variation_recomputation")
        if float(metric.get("sampled_probability_delta_from_initial", math.nan)) != delta:
            failures.append(f"row:{ordinal}:sampled_delta")
        if float(metric["oriented_sampled_probability_delta"]) != oriented:
            failures.append(f"row:{ordinal}:oriented_delta")
        if metric.get("orientation") != orientation_class(oriented):
            failures.append(f"row:{ordinal}:orientation")
        if (
            metric.get("value_output_byte_exact_to_initial") is not True
            or float(metric["value_float32"]) != float(fixed["initial_value_float32"])
            or metric.get("value_raw_bytes_hex")
            != fixed["initial_value_raw_bytes_hex"]
            or metric.get("value_byte_sha256")
            != fixed["initial_value_byte_sha256"]
        ):
            failures.append(f"row:{ordinal}:value_identity")
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
    stage_2_update_ordinal: int | None = None,
    parameter_optimizer_contract_pass: bool = True,
    value_contract_pass: bool = True,
) -> dict[str, Any]:
    """Apply only the mandatory post-update safety gates."""

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
    if not parameter_optimizer_contract_pass:
        failures.append("global:parameter_optimizer_contract")
    if not value_contract_pass:
        failures.append("global:value_contract")
    family = _family_diagnostics(prepare_receipt, rows)
    global_alignment = alignment_summary(
        [float(row["oriented_sampled_probability_delta"]) for row in rows]
    )
    global_failures = list(dict.fromkeys(failures))
    return {
        "stage": stage,
        "stage_2_update_ordinal": stage_2_update_ordinal,
        "global_pass": not global_failures,
        "global_failures": global_failures,
        "safety_pass": not global_failures,
        "hard_stop": bool(global_failures),
        "hard_stop_before_stage_2": stage == 1 and bool(global_failures),
        "family_required_for_acceptance": False,
        "family_diagnostics": family,
        "global_alignment": global_alignment,
        "mean_anchor_kl": mean_kl,
        "maximum_anchor_kl": maximum_kl,
        "maximum_total_variation": maximum_tv,
        "nonfinite_count": total_nonfinite,
        "accepted_at_stage": not global_failures,
        "acceptance_failures": global_failures,
        "parameter_optimizer_contract_pass": parameter_optimizer_contract_pass,
        "value_contract_pass": value_contract_pass,
    }


def _validated_directional_memberships(
    fixed_rows: Sequence[Mapping[str, Any]], supplied: Any
) -> dict[str, list[int]]:
    """Bind every directional population to the immutable prepare rows."""

    if not isinstance(fixed_rows, list) or len(fixed_rows) != EXPECTED_ON_POLICY_ROWS:
        raise ValueError("directional membership derivation requires exactly 830 rows")
    if not isinstance(supplied, Mapping) or set(supplied) != set(
        DIRECTIONAL_MEMBERSHIP_KEYS
    ):
        raise ValueError("directional memberships require exactly five keys")
    normalized_supplied: dict[str, list[int]] = {}
    for name in DIRECTIONAL_MEMBERSHIP_KEYS:
        values = supplied[name]
        if not isinstance(values, list):
            raise ValueError(f"directional membership {name} must be a list")
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value < EXPECTED_ON_POLICY_ROWS
            for value in values
        ):
            raise ValueError(f"directional membership {name} has an invalid ordinal")
        if values != sorted(values) or len(values) != len(set(values)):
            raise ValueError(
                f"directional membership {name} must be sorted and duplicate-free"
            )
        if len(values) != DIRECTIONAL_MEMBERSHIP_COUNTS[name]:
            raise ValueError(f"directional membership {name} count mismatch")
        normalized_supplied[name] = list(values)

    teacher_end: list[int] = []
    teacher_and_sampled_end: list[int] = []
    positive_normalized: list[int] = []
    positive_raw: list[int] = []
    for ordinal, row in enumerate(fixed_rows):
        if not isinstance(row, Mapping):
            raise ValueError(f"directional prepare row {ordinal} is not an object")
        teacher_is_end = row.get("teacher_index") == row.get("end_index")
        if teacher_is_end:
            teacher_end.append(ordinal)
            sampled_is_end = row.get("sampled_index") == row.get("end_index")
            if sampled_is_end:
                teacher_and_sampled_end.append(ordinal)
                normalized = row.get("fixed_normalized_advantage_float32")
                raw = row.get("raw_advantage_float64")
                if (
                    isinstance(normalized, bool)
                    or not isinstance(normalized, (int, float))
                    or not math.isfinite(float(normalized))
                    or isinstance(raw, bool)
                    or not isinstance(raw, (int, float))
                    or not math.isfinite(float(raw))
                ):
                    raise ValueError(
                        f"directional prepare row {ordinal} has invalid advantages"
                    )
                if float(normalized) > 0.0:
                    positive_normalized.append(ordinal)
                if float(raw) > 0.0:
                    positive_raw.append(ordinal)
    authoritative = {
        "negative_target_ordinals": list(NEGATIVE_TARGET_ORDINALS),
        "positive_normalized_teacher_and_sampled_end_ordinals": (
            positive_normalized
        ),
        "positive_raw_teacher_and_sampled_end_ordinals": positive_raw,
        "teacher_end_and_sampled_end_ordinals": teacher_and_sampled_end,
        "teacher_end_ordinals": teacher_end,
    }
    if any(
        len(authoritative[name]) != DIRECTIONAL_MEMBERSHIP_COUNTS[name]
        for name in DIRECTIONAL_MEMBERSHIP_KEYS
    ):
        raise ValueError("derived directional membership count mismatch")
    if canonical_json_bytes(normalized_supplied) != canonical_json_bytes(authoritative):
        raise ValueError("directional memberships differ from immutable prepare rows")
    return authoritative


def evaluate_directional_gates(
    prepare_receipt: Mapping[str, Any], metrics: Sequence[Mapping[str, Any]], *, stage: int
) -> dict[str, Any]:
    fixed = prepare_receipt["rows"]
    memberships = _validated_directional_memberships(
        fixed, prepare_receipt["directional_memberships"]
    )
    failures: list[str] = []

    def vectors(ordinal: int) -> tuple[list[float], list[float]]:
        post, _ = _authoritative_float32_probability_vector(
            metrics[ordinal]["probabilities_float32"],
            label=f"directional row {ordinal} probabilities",
        )
        initial, _ = _authoritative_float32_probability_vector(
            fixed[ordinal]["initial_probabilities_float32"],
            label=f"directional row {ordinal} initial probabilities",
        )
        return post, initial

    for ordinal in memberships["negative_target_ordinals"]:
        row = fixed[ordinal]
        probabilities, initial = vectors(ordinal)
        end_delta = probabilities[row["end_index"]] - initial[row["end_index"]]
        teacher_delta = probabilities[row["teacher_index"]] - initial[row["teacher_index"]]
        if not _negative_end_decrease_passes(end_delta):
            failures.append(f"negative:{ordinal}:end_decrease")
        if not _teacher_probability_increase_passes(teacher_delta):
            failures.append(f"negative:{ordinal}:teacher_increase")
        try:
            inherited._unique_argmax(probabilities, int(row["teacher_index"]))
        except ValueError:
            failures.append(f"negative:{ordinal}:teacher_unique_argmax")
    for ordinal in memberships["teacher_end_ordinals"]:
        probabilities, _ = vectors(ordinal)
        try:
            inherited._unique_argmax(
                probabilities, int(fixed[ordinal]["end_index"])
            )
        except ValueError:
            failures.append(f"legitimate_end:{ordinal}:unique_argmax")
    for ordinal in memberships["positive_normalized_teacher_and_sampled_end_ordinals"]:
        end = int(fixed[ordinal]["end_index"])
        probabilities, initial = vectors(ordinal)
        delta = probabilities[end] - initial[end]
        if not _positive_normalized_end_increase_passes(delta):
            failures.append(f"legitimate_end:{ordinal}:normalized_increase")
    raw_deltas: list[float] = []
    for ordinal in memberships["positive_raw_teacher_and_sampled_end_ordinals"]:
        end = int(fixed[ordinal]["end_index"])
        probabilities, initial = vectors(ordinal)
        raw_deltas.append(probabilities[end] - initial[end])
    raw_lower_median = lower_empirical_median(raw_deltas)
    maximum_decrease = max(max(0.0, -value) for value in raw_deltas)
    if not _positive_raw_lower_median_passes(raw_lower_median):
        failures.append("legitimate_end:positive_raw_lower_median")
    if not _positive_raw_maximum_decrease_passes(maximum_decrease):
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


def _negative_end_decrease_passes(delta: float) -> bool:
    return float(delta) <= -1e-6


def _teacher_probability_increase_passes(delta: float) -> bool:
    return float(delta) >= 1e-6


def _positive_normalized_end_increase_passes(delta: float) -> bool:
    return float(delta) >= 1e-6


def _positive_raw_lower_median_passes(value: float) -> bool:
    return float(value) > 0.0


def _positive_raw_maximum_decrease_passes(value: float) -> bool:
    return float(value) <= 0.0025


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
    byte_exact_count = sum(
        metric.get("value_output_byte_exact_to_initial") is True
        for metric in metrics
    )
    initial_mse = raw_value_mse(prepare_receipt)
    measured_mse = raw_value_mse(prepare_receipt, metrics)
    first_mismatch = next(
        (
            int(fixed["ppo_row_ordinal"])
            for fixed, metric in zip(prepare_receipt["rows"], metrics)
            if (
                metric.get("value_raw_bytes_hex")
                != fixed["initial_value_raw_bytes_hex"]
                or metric.get("value_byte_sha256")
                != fixed["initial_value_byte_sha256"]
            )
        ),
        None,
    )
    current_raw_bytes = b"".join(
        bytes.fromhex(str(metric["value_raw_bytes_hex"])) for metric in metrics
    )
    current_aggregate = hashlib.sha256(current_raw_bytes).hexdigest().upper()
    initial_aggregate = prepare_receipt["initial_value_identity"][
        "ordered_raw_bytes_sha256"
    ]
    return {
        "mean_change_from_initial": math.fsum(finite) / len(finite) if finite else math.nan,
        "median_change_from_initial": statistics.median(finite) if finite else math.nan,
        "maximum_absolute_change_from_initial": max(map(abs, finite)) if finite else math.nan,
        "nonfinite_count": nonfinite,
        "byte_exact_count": byte_exact_count,
        "all_rows_byte_exact_to_initial": byte_exact_count == EXPECTED_ON_POLICY_ROWS,
        "raw_value_mse_initial": initial_mse,
        "raw_value_mse_measured": measured_mse,
        "raw_value_mse_exact_to_initial": measured_mse == initial_mse,
        "first_mismatch_ppo_row_ordinal": first_mismatch,
        "current_ordered_raw_bytes_sha256": current_aggregate,
        "initial_ordered_raw_bytes_sha256": initial_aggregate,
        "aggregate_hash_exact_to_initial": current_aggregate == initial_aggregate,
    }


def _load_execution_spec(path: Path, expected_file_sha256: str) -> dict[str, Any]:
    spec = inherited._load_hashed_json(
        path, expected_file_sha256, label="iteration-007 execution spec"
    )
    required = set(EXECUTION_SPEC_TOP_LEVEL_KEYS)
    row = dict(_exact_keys(spec, required, label="iteration-007 execution spec"))
    if row["schema_version"] != EXECUTION_SPEC_SCHEMA_VERSION:
        raise ValueError("iteration-007 execution spec schema mismatch")
    expected = {
        **_contract_bindings(),
        "parent_result_path": PARENT_RESULT_RELATIVE_PATH.as_posix(),
        "parent_result_sha256": PARENT_RESULT_SHA256,
        "implementation_path": IMPLEMENTATION_RELATIVE_PATH.as_posix(),
        "input_checkpoint_path": INPUT_CHECKPOINT_RELATIVE_PATH.as_posix(),
        "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
        "forbidden_rejected_checkpoint_sha256s": list(
            FORBIDDEN_REJECTED_CHECKPOINT_SHA256S
        ),
        "manifest_path": MANIFEST_RELATIVE_PATH.as_posix(),
        "manifest_sha256": MANIFEST_SHA256,
        "dataset_sha256": DATASET_SHA256,
        "fixed_advantages_sha256": FIXED_ADVANTAGES_SHA256,
        "fixed_behavior_logprobabilities_sha256": (
            FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256
        ),
        "output_directory": APPROVED_OUTPUT_RELATIVE_PATH.as_posix(),
    }
    for name, value in expected.items():
        if row.get(name) != value:
            raise ValueError(f"iteration-007 execution spec {name} mismatch")
    if row["input_checkpoint_sha256"] in row["forbidden_rejected_checkpoint_sha256s"]:
        raise ValueError("execution spec selects rejected checkpoint")
    plan = _load_plan()
    _load_correction()
    _load_correction_v2()
    _load_prepare_audit_remediation()
    _load_prepare_audit_remediation_v2()
    _load_prepare_audit_remediation_v3()
    _load_prepare_audit_remediation_v4()
    _load_prepare_audit_remediation_v5()
    _load_prepare_audit_remediation_v6()
    _load_prepare_audit_remediation_v7()
    remediation_v8 = _load_prepare_audit_remediation_v8()
    override = remediation_v8["execution_spec_override"]
    if len(required) != 44 or list(EXECUTION_SPEC_TOP_LEVEL_KEYS) != override[
        "exact_top_level_keys"
    ]:
        raise ValueError("iteration-007 execution-spec v10 key set mismatch")
    for name in (
        "training_contract", "diagnostic_contract", "safety_gates",
        "terminal_offline_acceptance",
    ):
        if row[name] != plan[name]:
            raise ValueError(f"iteration-007 execution spec {name} mismatch")
    return row


def _validate_execution_output(
    value: Any, *, receipt_path: Path, execution_spec_path: Path
) -> Path:
    if not isinstance(value, str) or value != APPROVED_OUTPUT_RELATIVE_PATH.as_posix():
        raise ValueError("execution output directory must be a relative POSIX path")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or any(part in (".", "..") for part in relative.parts)
        or len(relative.parts) != 2
        or relative.parts[0] != "analysis_outputs"
    ):
        raise ValueError("execution output directory contains aliases")
    output = _repo_path(relative).absolute()
    repo_root = find_repo_root().resolve(strict=True)
    cursor = repo_root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.exists() or cursor.is_symlink():
            if inherited._is_link_or_reparse(cursor):
                raise ValueError("execution output path traverses a reparse point")
        else:
            break
    analysis_root = (repo_root  / "_local_generated" / "analysis_outputs").resolve(strict=True)
    try:
        output.resolve(strict=False).relative_to(analysis_root)
    except ValueError as error:
        raise ValueError("execution output escapes analysis_outputs") from error
    if output.exists() or output.is_symlink():
        raise FileExistsError("execution requires a new absent output directory")
    parent = output.parent
    if not parent.is_dir() or inherited._is_link_or_reparse(parent):
        raise ValueError("execution output parent must be a regular non-reparse directory")
    protected = (
        _repo_path(PLAN_RELATIVE_PATH), _repo_path(CORRECTION_RELATIVE_PATH),
        _repo_path(CORRECTION_V2_RELATIVE_PATH),
        _repo_path(PREPARE_AUDIT_REMEDIATION_RELATIVE_PATH),
        _repo_path(PREPARE_AUDIT_REMEDIATION_V2_RELATIVE_PATH),
        _repo_path(PREPARE_AUDIT_REMEDIATION_V3_RELATIVE_PATH),
        _repo_path(PREPARE_AUDIT_REMEDIATION_V4_RELATIVE_PATH),
        _repo_path(PREPARE_AUDIT_REMEDIATION_V5_RELATIVE_PATH),
        _repo_path(PREPARE_AUDIT_REMEDIATION_V6_RELATIVE_PATH),
        _repo_path(PREPARE_AUDIT_REMEDIATION_V7_RELATIVE_PATH),
        _repo_path(PREPARE_AUDIT_REMEDIATION_V8_RELATIVE_PATH),
        _repo_path(PARENT_RESULT_RELATIVE_PATH),
        _repo_path(IMPLEMENTATION_RELATIVE_PATH), _repo_path(SOURCE_IMPLEMENTATION_RELATIVE_PATH),
        _repo_path(INPUT_CHECKPOINT_RELATIVE_PATH), _repo_path(MANIFEST_RELATIVE_PATH),
        _repo_path(PREPARE_SOURCE_RELATIVE_PATH), _repo_path(PARENT_REJECTED_RECEIPT_RELATIVE_PATH),
        _repo_path(REJECTED_CHECKPOINT_RELATIVE_PATH), receipt_path, execution_spec_path,
    )
    if any(inherited._paths_overlap(output, item) for item in protected):
        raise ValueError("execution output overlaps a protected input")
    return output


def _validate_execution_boundary(
    spec: Mapping[str, Any], runtime: Mapping[str, Any], *, execution_spec_path: Path
) -> tuple[dict[str, Any], Path]:
    receipt_path = inherited._resolve_pinned_path(
        spec["prepare_receipt_path"], label="iteration-007 prepare receipt path"
    )
    receipt_path = _validate_prepare_output_path(receipt_path, must_exist=True)
    receipt = inherited._load_hashed_json(
        receipt_path,
        _strict_sha256(
            spec["prepare_receipt_file_sha256"], label="prepare receipt file hash"
        ),
        label="pinned iteration-007 prepare receipt",
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
    for name in (
        "diagnostic_contract", "safety_gates", "terminal_offline_acceptance",
    ):
        if spec[name] != receipt[name]:
            raise ValueError(f"execution {name} differs from prepare")
    rebuilt = _build_prepare_receipt(runtime)
    if rebuilt != receipt:
        raise ValueError("prepare evidence did not reproduce at execution boundary")
    output = _validate_execution_output(
        spec["output_directory"],
        receipt_path=receipt_path,
        execution_spec_path=execution_spec_path,
    )
    return receipt, output


def _build_authorized_execution_fixed_inputs(
    loaded: Mapping[str, Any], prepare_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    """Recompute GAE/normalization exactly once after preflight and freeze arrays."""

    episodes = list(loaded["dataset"].episodes)
    rows = loaded["rows"]
    gae = inherited._gae(episodes, TWO_STAGE_PPO_CONFIG)
    raw_advantages = [
        float(gae[(str(episode["episode_id"]), int(row["decision_index"]))][0])
        for episode, row in rows
    ]
    value_targets = [
        float(gae[(str(episode["episode_id"]), int(row["decision_index"]))][1])
        for episode, row in rows
    ]
    tensor = torch.tensor(raw_advantages, dtype=torch.float32)
    normalized_tensor = (tensor - tensor.mean()) / tensor.std(unbiased=False)
    normalized = [float(value) for value in normalized_tensor.tolist()]
    behavior_logprobs = [float(row["behavior_logprob"]) for _, row in rows]
    sampled_indices = [int(row["final_action"][0]) for _, row in rows]
    fixed_rows = prepare_receipt["rows"]
    if (
        normalized
        != [float(row["fixed_normalized_advantage_float32"]) for row in fixed_rows]
        or behavior_logprobs
        != [float(row["behavior_logprob_float64"]) for row in fixed_rows]
        or value_targets
        != [float(row["fixed_value_target_float64"]) for row in fixed_rows]
        or sampled_indices != [int(row["sampled_index"]) for row in fixed_rows]
        or canonical_sha256(normalized) != FIXED_ADVANTAGES_SHA256
        or canonical_sha256(behavior_logprobs)
        != FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256
    ):
        raise ValueError("authorized execution fixed-input recomputation mismatch")
    return {
        "normalized_advantages_float32": normalized,
        "behavior_logprobabilities_float64": behavior_logprobs,
        "value_targets_float64": value_targets,
        "sampled_indices": sampled_indices,
        "gae_recomputation_count": 1,
        "fixed_advantages_sha256": FIXED_ADVANTAGES_SHA256,
        "fixed_behavior_logprobabilities_sha256": (
            FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256
        ),
    }


def _run_two_stage_iteration006_legacy(
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


def _family_median_map(family: Mapping[str, Any]) -> dict[str, float]:
    return {
        f"{row['name']}:{row['polarity']}": float(row["lower_empirical_median"])
        for row in family["groups"]
    }


def evaluate_terminal_offline_gates(
    *,
    run: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate the exact update-32 practical and inherited END gates."""

    failures: list[str] = []
    if run.get("optimizer_steps_completed") != TOTAL_OPTIMIZER_STEPS:
        failures.append("terminal:optimizer_steps")
    if run.get("safety_stop"):
        failures.append("terminal:safety_stop")
    safety_history = [run["stage_1_safety"], *run.get("stage_2_update_summaries", [])]
    if not safety_history or any(
        not (item.get("safety", item)).get("safety_pass", False)
        for item in safety_history
    ):
        failures.append("terminal:safety_history")
    family_stage_1 = _family_median_map(
        run["stage_1_safety"]["family_diagnostics"]
    )
    family_16 = _family_median_map(
        run["stage_2_milestone_summaries"]["16"]["family_diagnostics"]
    )
    family_32_report = run["stage_2_milestone_summaries"]["32"][
        "family_diagnostics"
    ]
    family_32 = _family_median_map(family_32_report)
    if len(family_32) != 12:
        failures.append("terminal:family_group_count")
    for name, value in family_32.items():
        if value <= DEADBAND_TAU:
            failures.append(f"terminal:family:{name}:lower_median")
    formerly_failing = (
        "PLAY:positive", "ATTACH:negative", "EVOLVE:negative",
        "RETREAT:positive", "ATTACK:negative", "END:positive",
    )
    formerly_reports: list[dict[str, Any]] = []
    for name in formerly_failing:
        value_1 = family_stage_1[name]
        value_16 = family_16[name]
        value_32 = family_32[name]
        passed_16 = value_16 > value_1
        passed_32 = value_32 > value_1
        passed_minimum = value_32 >= 1e-6
        if not passed_16:
            failures.append(f"terminal:formerly_failing:{name}:update16")
        if not passed_32:
            failures.append(f"terminal:formerly_failing:{name}:update32")
        if not passed_minimum:
            failures.append(f"terminal:formerly_failing:{name}:minimum")
        formerly_reports.append(
            {
                "group": name,
                "stage_1_lower_median": value_1,
                "update_16_lower_median": value_16,
                "update_32_lower_median": value_32,
                "update_16_strictly_greater_than_stage_1": passed_16,
                "update_32_strictly_greater_than_stage_1": passed_32,
                "update_32_minimum_1e_6": passed_minimum,
            }
        )
    global_alignment = run["stage_2_milestone_summaries"]["32"][
        "global_alignment"
    ]
    if float(global_alignment["score"]) < 0.1:
        failures.append("terminal:global_alignment_score")
    if float(global_alignment["lower_empirical_median"]) < 1e-5:
        failures.append("terminal:global_lower_median")
    end_gates = run["terminal_end_gates"]
    if not end_gates["passed"]:
        failures.extend(f"terminal:end:{item}" for item in end_gates["failures"])
    if run.get("parameter_optimizer_contract_pass") is not True:
        failures.append("terminal:parameter_optimizer_contract")
    if run.get("value_contract_pass") is not True:
        failures.append("terminal:value_contract")
    return {
        "accepted_before_checkpoint_validation": not failures,
        "failures": list(dict.fromkeys(failures)),
        "completed_optimizer_steps_exact": run.get("optimizer_steps_completed")
        == TOTAL_OPTIMIZER_STEPS,
        "all_safety_gates_pass": not any(
            not (item.get("safety", item)).get("safety_pass", False)
            for item in safety_history
        ),
        "family_update_32": family_32_report,
        "formerly_failing_groups": formerly_reports,
        "terminal_global_alignment": global_alignment,
        "inherited_end_gates": end_gates,
        "parameter_optimizer_contract_pass": run.get(
            "parameter_optimizer_contract_pass"
        ),
        "value_contract_pass": run.get("value_contract_pass"),
    }


def _frozen_value_contract_evidence(
    model: torch.nn.Module,
    optimizer: torch.optim.Adam,
    initial_hashes: Mapping[str, str],
) -> dict[str, Any]:
    named = dict(model.named_parameters())
    current = {name: _tensor_sha256(named[name]) for name in initial_hashes}
    reverse = {id(parameter): name for name, parameter in named.items()}
    frozen_state_names = sorted(
        reverse.get(id(parameter), "unknown")
        for parameter in optimizer.state
        if reverse.get(id(parameter), "unknown") in initial_hashes
    )
    return {
        "initial_parameter_hashes": dict(initial_hashes),
        "current_parameter_hashes": current,
        "parameter_hashes_exact": current == dict(initial_hashes),
        "optimizer_state_names": frozen_state_names,
        "optimizer_state_absent": not frozen_state_names,
    }


def _ordered_output_hashes(metrics: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    probability_bytes = b"".join(
        bytes.fromhex(str(metric["probabilities_raw_bytes_hex"]))
        for metric in metrics
    )
    value_bytes = b"".join(
        bytes.fromhex(str(metric["value_raw_bytes_hex"])) for metric in metrics
    )
    return {
        "ordered_probability_bytes_sha256": hashlib.sha256(
            probability_bytes
        ).hexdigest().upper(),
        "ordered_value_bytes_sha256": hashlib.sha256(value_bytes).hexdigest().upper(),
    }


STAGE2_COMPACT_RECORD_KEYS = {
    "stage_2_update_ordinal", "optimizer_step_ordinal", "optimizer_state_steps",
    "loss", "policy_loss", "anchor_kl_loss", "entropy",
    "gradient_norm_before_clipping",
    "per_parameter_gradient_norm_before_clipping",
    "per_parameter_gradient_norm_after_clipping", "parameter_diffs_from_initial",
    "parameter_diffs_from_previous_step", "parameter_diffs_from_stage_start",
    "safety", "value_identity", "frozen_encoder_value_contract",
    "ordered_probability_bytes_sha256", "ordered_value_bytes_sha256",
    "raw_rows_persisted", "previous_record_hash", "measurement_timing",
    "record_hash",
}
STAGE2_PRE_STEP_KEYS = {
    "loss", "policy_loss", "anchor_kl_contribution", "entropy",
    "gradient_norm_before_clipping",
    "per_parameter_gradient_norm_before_clipping",
    "per_parameter_gradient_norm_after_clipping",
}
STAGE2_POST_STEP_KEYS = {
    "optimizer_state_steps", "parameter_diffs_from_initial",
    "parameter_diffs_from_fixed_stage_2_start",
    "parameter_diffs_from_previous_step", "safety",
    "ordered_probability_bytes_sha256", "ordered_value_bytes_sha256",
}
STAGE2_TIMING_BINDINGS = (
    ("pre_step", "loss", "loss"),
    ("pre_step", "policy_loss", "policy_loss"),
    ("pre_step", "anchor_kl_contribution", "anchor_kl_loss"),
    ("pre_step", "entropy", "entropy"),
    (
        "pre_step", "gradient_norm_before_clipping",
        "gradient_norm_before_clipping",
    ),
    (
        "pre_step", "per_parameter_gradient_norm_before_clipping",
        "per_parameter_gradient_norm_before_clipping",
    ),
    (
        "pre_step", "per_parameter_gradient_norm_after_clipping",
        "per_parameter_gradient_norm_after_clipping",
    ),
    ("post_step", "optimizer_state_steps", "optimizer_state_steps"),
    (
        "post_step", "parameter_diffs_from_initial",
        "parameter_diffs_from_initial",
    ),
    (
        "post_step", "parameter_diffs_from_fixed_stage_2_start",
        "parameter_diffs_from_stage_start",
    ),
    (
        "post_step", "parameter_diffs_from_previous_step",
        "parameter_diffs_from_previous_step",
    ),
    ("post_step", "safety", "safety"),
    (
        "post_step", "ordered_probability_bytes_sha256",
        "ordered_probability_bytes_sha256",
    ),
    (
        "post_step", "ordered_value_bytes_sha256",
        "ordered_value_bytes_sha256",
    ),
)


def _validate_stage_2_measurement_timing(summary: Mapping[str, Any]) -> None:
    row = _exact_keys(
        summary, STAGE2_COMPACT_RECORD_KEYS, label="Stage-2 compact record"
    )
    timing = _exact_keys(
        row["measurement_timing"], {"pre_step", "post_step"},
        label="Stage-2 measurement timing",
    )
    pre = _exact_keys(
        timing["pre_step"], STAGE2_PRE_STEP_KEYS,
        label="Stage-2 pre-step timing",
    )
    post = _exact_keys(
        timing["post_step"], STAGE2_POST_STEP_KEYS,
        label="Stage-2 post-step timing",
    )
    phases = {"pre_step": pre, "post_step": post}
    for phase, alias, authoritative in STAGE2_TIMING_BINDINGS:
        if canonical_json_bytes(phases[phase][alias]) != canonical_json_bytes(
            row[authoritative]
        ):
            raise ValueError(
                f"Stage-2 measurement timing alias mismatch: {phase}.{alias}"
            )


def validate_compact_update_chain(
    training_receipt: Mapping[str, Any],
    *,
    independent_reconstruction: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    summaries = training_receipt.get("stage_2_update_summaries")
    if not isinstance(summaries, list) or len(summaries) != STAGE2_UPDATES:
        raise ValueError("compact Stage-2 summary count mismatch")
    previous = _strict_sha256(
        training_receipt.get("stage_1_record_hash"), label="Stage-1 record hash"
    )
    for update, summary in enumerate(summaries, start=1):
        _validate_stage_2_measurement_timing(summary)
        if summary.get("stage_2_update_ordinal") != update:
            raise ValueError("compact Stage-2 chronological order mismatch")
        if summary.get("previous_record_hash") != previous:
            raise ValueError("compact Stage-2 previous-record hash mismatch")
        core = dict(summary)
        claimed = _strict_sha256(
            core.pop("record_hash", None), label="compact update record hash"
        )
        if canonical_sha256(core) != claimed:
            raise ValueError("compact Stage-2 record self-hash mismatch")
        previous = claimed
    if independent_reconstruction is not None:
        if [dict(item) for item in independent_reconstruction] != [
            dict(item) for item in summaries
        ]:
            raise ValueError("independent compact reconstruction mismatch")
    return {
        "status": "pass",
        "full_raw_rows_claimed_for_nonmilestones": False,
        "summary_count": len(summaries),
        "terminal_record_hash": previous,
        "independent_reconstruction_compared": independent_reconstruction is not None,
    }


def validate_execution_training_receipt(
    training: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    *,
    independent_reconstruction: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    chain = validate_compact_update_chain(
        training, independent_reconstruction=independent_reconstruction
    )
    stage_1_recomputed = evaluate_stage_gates(
        prepare_receipt,
        training["stage_1_metrics"],
        stage=1,
        parameter_optimizer_contract_pass=True,
        value_contract_pass=True,
    )
    if stage_1_recomputed != training["stage_1_safety"]:
        raise ValueError("Stage-1 full diagnostic summary mismatch")
    full = training.get("stage_2_full_diagnostics")
    if not isinstance(full, Mapping) or sorted(map(int, full)) != list(
        DIAGNOSTIC_UPDATE_ORDINALS
    ):
        raise ValueError("full diagnostic milestone set mismatch")
    summaries = training["stage_2_update_summaries"]
    milestones = training.get("stage_2_milestone_summaries")
    for update in DIAGNOSTIC_UPDATE_ORDINALS:
        metrics = full[str(update)]
        recomputed = evaluate_stage_gates(
            prepare_receipt,
            metrics,
            stage=2,
            stage_2_update_ordinal=update,
            parameter_optimizer_contract_pass=True,
            value_contract_pass=True,
        )
        expected = {
            "global_alignment": recomputed["global_alignment"],
            "family_diagnostics": recomputed["family_diagnostics"],
            "mean_anchor_kl": recomputed["mean_anchor_kl"],
            "maximum_anchor_kl": recomputed["maximum_anchor_kl"],
            "maximum_total_variation": recomputed["maximum_total_variation"],
            "value_identity": summaries[update - 1]["value_identity"],
        }
        if milestones[str(update)] != expected:
            raise ValueError("full diagnostic milestone summary mismatch")
        hashes = _ordered_output_hashes(metrics)
        if any(summaries[update - 1].get(name) != value for name, value in hashes.items()):
            raise ValueError("full diagnostic milestone output hash mismatch")
    return {
        "status": "pass",
        "full_milestones_recomputed": list(DIAGNOSTIC_UPDATE_ORDINALS),
        "nonmilestone_raw_rows_recomputed": False,
        "compact_chain": chain,
    }


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
    initial_frozen_hashes = {
        name: _tensor_sha256(value)
        for name, value in initial_parameters.items()
        if name.startswith(("state_encoder.", "action_encoder.", VALUE_PREFIX))
    }
    raw_initial = raw_value_mse(prepare_receipt)
    _set_trainability(model, stage=1)
    optimizer = _new_actor_adam(model)
    progress.optimizer = optimizer
    optimizer_identity = id(optimizer)
    progress.failure_phase = "stage_1_full_batch_step"
    stage_1_report = _stage_full_batch_step(
        stage=1,
        loaded=loaded,
        prepare_receipt=prepare_receipt,
        optimizer=optimizer,
        initial_parameters=initial_parameters,
        progress=progress,
    )
    stage_1_metrics = _measure_stage(loaded, prepare_receipt, stage=1)
    stage_1_value = value_change_summary(prepare_receipt, stage_1_metrics)
    stage_1_safety = evaluate_stage_gates(
        prepare_receipt,
        stage_1_metrics,
        stage=1,
        training_nonfinite_count=stage_1_report[
            "nonfinite_value_gradient_optimizer_or_parameter_count"
        ],
        parameter_optimizer_contract_pass=True,
        value_contract_pass=(
            stage_1_value["all_rows_byte_exact_to_initial"]
            and stage_1_value["raw_value_mse_exact_to_initial"]
            and stage_1_value.get("aggregate_hash_exact_to_initial", True)
            and stage_1_value.get("first_mismatch_ppo_row_ordinal") is None
        ),
    )
    readout_after_stage_1 = {
        name: dict(model.named_parameters())[name].detach().clone()
        for name in STAGE1_TRAINABLE_NAMES
    }
    readout_moments_after_stage_1 = {
        name: copy.deepcopy(optimizer.state[dict(model.named_parameters())[name]])
        for name in STAGE1_TRAINABLE_NAMES
    }
    stage_2_start_parameters = {
        name: value.detach().clone() for name, value in model.state_dict().items()
    }
    stage_1_output_hashes = _ordered_output_hashes(stage_1_metrics)
    stage_1_record_hash = canonical_sha256(
        {
            "stage_1_report": stage_1_report,
            "stage_1_safety": stage_1_safety,
            "stage_1_value_identity": stage_1_value,
            **stage_1_output_hashes,
        }
    )
    common: dict[str, Any] = {
        "model": model,
        "optimizer": optimizer,
        "initial_parameters": initial_parameters,
        "stage_1_report": stage_1_report,
        "stage_1_metrics": stage_1_metrics,
        "stage_1_safety": stage_1_safety,
        "stage_1_value_identity": stage_1_value,
        "stage_1_record_hash": stage_1_record_hash,
        "raw_value_mse_initial": raw_initial,
        "stage_2_update_summaries": [],
        "stage_2_full_diagnostics": {},
        "stage_2_milestone_summaries": {},
        "same_optimizer_object_across_all_updates": True,
        "optimizer_identity_count": 1,
        "optimizer_steps_completed": progress.optimizer_steps_completed,
        "safety_stop": stage_1_safety["hard_stop"],
        "safety_stop_after_stage_2_update": None,
        "terminal_end_gates": None,
        "parameter_optimizer_contract_pass": True,
        "value_contract_pass": (
            stage_1_value["all_rows_byte_exact_to_initial"]
            and stage_1_value["raw_value_mse_exact_to_initial"]
            and stage_1_value.get("aggregate_hash_exact_to_initial", True)
            and stage_1_value.get("first_mismatch_ppo_row_ordinal") is None
        ),
        "frozen_encoder_value_contract": _frozen_value_contract_evidence(
            model, optimizer, initial_frozen_hashes
        ),
    }
    if stage_1_safety["hard_stop"]:
        return common
    progress.stage_2_entered = True
    previous_record_hash = stage_1_record_hash
    for update in range(1, STAGE2_UPDATES + 1):
        progress.failure_phase = f"stage_2_update_{update}_full_batch_step"
        step_report = _stage_full_batch_step(
            stage=2,
            stage_2_update_ordinal=update,
            loaded=loaded,
            prepare_receipt=prepare_receipt,
            optimizer=optimizer,
            initial_parameters=initial_parameters,
            progress=progress,
            stage_2_start_parameters=stage_2_start_parameters,
        )
        if id(optimizer) != optimizer_identity:
            raise ValueError("optimizer object changed across updates")
        metrics = _measure_stage(
            loaded,
            prepare_receipt,
            stage=2,
            stage_2_update_ordinal=update,
        )
        value_identity = value_change_summary(prepare_receipt, metrics)
        parameter_contract = bool(
            all(
                torch.equal(
                    readout_after_stage_1[name], dict(model.named_parameters())[name]
                )
                for name in STAGE1_TRAINABLE_NAMES
            )
            and all(
                _nested_byte_exact(
                    readout_moments_after_stage_1[name],
                    optimizer.state[dict(model.named_parameters())[name]],
                )
                for name in STAGE1_TRAINABLE_NAMES
            )
        )
        value_contract = bool(
            value_identity["all_rows_byte_exact_to_initial"]
            and value_identity["raw_value_mse_exact_to_initial"]
            and value_identity.get("aggregate_hash_exact_to_initial", True)
            and value_identity.get("first_mismatch_ppo_row_ordinal") is None
        )
        frozen_evidence = _frozen_value_contract_evidence(
            model, optimizer, initial_frozen_hashes
        )
        value_contract = bool(
            value_contract
            and frozen_evidence["parameter_hashes_exact"]
            and frozen_evidence["optimizer_state_absent"]
        )
        safety = evaluate_stage_gates(
            prepare_receipt,
            metrics,
            stage=2,
            stage_2_update_ordinal=update,
            training_nonfinite_count=step_report[
                "nonfinite_value_gradient_optimizer_or_parameter_count"
            ],
            parameter_optimizer_contract_pass=parameter_contract,
            value_contract_pass=value_contract,
        )
        output_hashes = _ordered_output_hashes(metrics)
        compact = {
            "stage_2_update_ordinal": update,
            "optimizer_step_ordinal": step_report["optimizer_step_ordinal"],
            "optimizer_state_steps": step_report["optimizer_state_steps"],
            "loss": step_report["loss"],
            "policy_loss": step_report["policy_loss"],
            "anchor_kl_loss": 0.1 * step_report["pre_step_mean_anchor_kl"],
            "entropy": step_report["entropy"],
            "gradient_norm_before_clipping": step_report[
                "gradient_norm_before_clipping"
            ],
            "per_parameter_gradient_norm_before_clipping": step_report[
                "per_parameter_gradient_norm_before_clipping"
            ],
            "per_parameter_gradient_norm_after_clipping": step_report[
                "per_parameter_gradient_norm_after_clipping"
            ],
            "parameter_diffs_from_initial": step_report[
                "parameter_diffs_from_initial"
            ],
            "parameter_diffs_from_previous_step": step_report[
                "parameter_diffs_from_previous_step"
            ],
            "parameter_diffs_from_stage_start": step_report[
                "parameter_diffs_from_stage_start"
            ],
            "safety": safety,
            "value_identity": value_identity,
            "frozen_encoder_value_contract": frozen_evidence,
            **output_hashes,
            "raw_rows_persisted": update in DIAGNOSTIC_UPDATE_ORDINALS,
            "previous_record_hash": previous_record_hash,
            "measurement_timing": {
                "pre_step": {
                    "loss": step_report["loss"],
                    "policy_loss": step_report["policy_loss"],
                    "anchor_kl_contribution": 0.1
                    * step_report["pre_step_mean_anchor_kl"],
                    "entropy": step_report["entropy"],
                    "gradient_norm_before_clipping": step_report[
                        "gradient_norm_before_clipping"
                    ],
                    "per_parameter_gradient_norm_before_clipping": step_report[
                        "per_parameter_gradient_norm_before_clipping"
                    ],
                    "per_parameter_gradient_norm_after_clipping": step_report[
                        "per_parameter_gradient_norm_after_clipping"
                    ],
                },
                "post_step": {
                    "optimizer_state_steps": step_report[
                        "optimizer_state_steps"
                    ],
                    "parameter_diffs_from_initial": step_report[
                        "parameter_diffs_from_initial"
                    ],
                    "parameter_diffs_from_fixed_stage_2_start": step_report[
                        "parameter_diffs_from_stage_start"
                    ],
                    "parameter_diffs_from_previous_step": step_report[
                        "parameter_diffs_from_previous_step"
                    ],
                    "safety": safety,
                    **output_hashes,
                },
            },
        }
        compact["record_hash"] = canonical_sha256(compact)
        previous_record_hash = compact["record_hash"]
        common["stage_2_update_summaries"].append(compact)
        if update in DIAGNOSTIC_UPDATE_ORDINALS:
            common["stage_2_full_diagnostics"][str(update)] = metrics
            common["stage_2_milestone_summaries"][str(update)] = {
                "global_alignment": safety["global_alignment"],
                "family_diagnostics": safety["family_diagnostics"],
                "mean_anchor_kl": safety["mean_anchor_kl"],
                "maximum_anchor_kl": safety["maximum_anchor_kl"],
                "maximum_total_variation": safety["maximum_total_variation"],
                "value_identity": value_identity,
            }
        common["optimizer_steps_completed"] = progress.optimizer_steps_completed
        common["parameter_optimizer_contract_pass"] = parameter_contract
        common["value_contract_pass"] = value_contract
        common["frozen_encoder_value_contract"] = frozen_evidence
        if safety["hard_stop"]:
            common["safety_stop"] = True
            common["safety_stop_after_stage_2_update"] = update
            return common
    final_frozen_hashes = {
        name: _tensor_sha256(dict(model.state_dict())[name])
        for name in initial_frozen_hashes
    }
    common["parameter_optimizer_contract_pass"] = bool(
        common["parameter_optimizer_contract_pass"]
        and final_frozen_hashes == initial_frozen_hashes
        and audit_optimizer_contract(
            optimizer,
            model,
            stage=2,
            stage_2_update_ordinal=STAGE2_UPDATES,
        )
        == {
            **{name: STAGE2_UPDATES for name in STAGE2_TRAINABLE_NAMES},
            **{name: 1 for name in STAGE1_TRAINABLE_NAMES},
        }
    )
    terminal_metrics = common["stage_2_full_diagnostics"]["32"]
    common["terminal_end_gates"] = evaluate_directional_gates(
        prepare_receipt, terminal_metrics, stage=2
    )
    common["terminal_offline_gates"] = evaluate_terminal_offline_gates(run=common)
    return common


def _independent_replay_validation(
    reference_run: Mapping[str, Any],
    prepare_receipt: Mapping[str, Any],
    fixed_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    loaded = inherited._load_validated_inputs()
    loaded["execution_fixed_inputs"] = copy.deepcopy(fixed_inputs)
    replay = _run_two_stage(loaded, prepare_receipt, ExecutionProgress())
    chain = validate_compact_update_chain(
        reference_run,
        independent_reconstruction=replay["stage_2_update_summaries"],
    )
    if (
        replay["stage_1_metrics"] != reference_run["stage_1_metrics"]
        or replay["stage_2_full_diagnostics"]
        != reference_run["stage_2_full_diagnostics"]
        or replay["terminal_offline_gates"]
        != reference_run["terminal_offline_gates"]
        or not _nested_byte_exact(
            replay["model"].state_dict(), reference_run["model"].state_dict()
        )
        or not _nested_byte_exact(
            replay["optimizer"].state_dict(),
            reference_run["optimizer"].state_dict(),
        )
    ):
        raise ValueError("independent deterministic replay mismatch")
    return {
        "status": "pass",
        "all_33_updates_replayed": True,
        "milestone_rows_exact": True,
        "compact_summaries_exact": True,
        "terminal_model_exact": True,
        "terminal_optimizer_exact": True,
        "chain_validation": chain,
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
    if len(parameter_ids) != len(OPTIMIZER_PARAMETER_NAMES):
        raise ValueError("serialized actor Adam parameter universe mismatch")
    result: dict[str, int] = {}
    for name, identifier in zip(OPTIMIZER_PARAMETER_NAMES, parameter_ids):
        parameter_state = state.get(identifier)
        if parameter_state is None:
            if completed_stage == 1 and name in STAGE2_TRAINABLE_NAMES:
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
    expected = _expected_optimizer_steps(completed_stage)
    if result != expected or set(state) != {
        identifier for name, identifier in zip(OPTIMIZER_PARAMETER_NAMES, parameter_ids)
        if name in expected
    }:
        raise ValueError("serialized actor Adam mixed-step contract mismatch")
    return result


def _expected_optimizer_steps(completed_stage: int) -> dict[str, int]:
    if completed_stage == 1:
        return {name: 1 for name in STAGE1_TRAINABLE_NAMES}
    if 2 <= completed_stage <= TOTAL_OPTIMIZER_STEPS:
        return {
            **{name: completed_stage - 1 for name in STAGE2_TRAINABLE_NAMES},
            **{name: 1 for name in STAGE1_TRAINABLE_NAMES},
        }
    raise ValueError("optimizer contract requires 1 through 33 completed steps")


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
    if len(parameter_ids) != len(OPTIMIZER_PARAMETER_NAMES):
        failures.append("optimizer_state:parameter_universe")
    known_ids = {
        identifier: name
        for name, identifier in zip(OPTIMIZER_PARAMETER_NAMES, parameter_ids)
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
    loaded: Mapping[str, Any] | None = None,
    terminal_metrics: Sequence[Mapping[str, Any]] | None = None,
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
    terminal_output_count = 0
    if terminal_metrics is not None:
        if loaded is None or len(terminal_metrics) != EXPECTED_ON_POLICY_ROWS:
            raise ValueError("terminal checkpoint output validation inputs missing")
        reference_config = loaded["reference_config"]
        with torch.no_grad():
            for ordinal, ((_, row), expected) in enumerate(
                zip(loaded["rows"], terminal_metrics)
            ):
                state = torch.tensor(row["state_vector"], dtype=torch.float32)
                actions = torch.tensor(row["action_vectors"], dtype=torch.float32)
                residuals, value = reloaded(state, actions)
                probabilities, _ = _torch_behavior_distribution(
                    residuals,
                    teacher_index=int(row["teacher_action"][0]),
                    reference_config=reference_config,
                )
                if (
                    _tensor_bytes(probabilities).hex().upper()
                    != expected["probabilities_raw_bytes_hex"]
                    or _tensor_bytes(value.reshape(())).hex().upper()
                    != expected["value_raw_bytes_hex"]
                ):
                    raise ValueError(
                        f"terminal checkpoint output byte mismatch at row {ordinal}"
                    )
                terminal_output_count += 1
    return {
        "status": "pass",
        "checkpoint_sha256": actual_hash,
        "metadata_exact": True,
        "model_state_exact": True,
        "optimizer_state_exact": True,
        "optimizer_state_steps": steps,
        "completed_stage": completed_stage,
        "parameters_finite": True,
        "terminal_probability_and_value_byte_exact_count": terminal_output_count,
        "terminal_all_830_outputs_byte_exact": (
            terminal_metrics is not None
            and terminal_output_count == EXPECTED_ON_POLICY_ROWS
        ),
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


def _final_gate_report_iteration006_legacy(
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


def _final_gate_report(
    run: Mapping[str, Any], *, serialized_validation: Mapping[str, Any]
) -> dict[str, Any]:
    failures: list[str] = []
    offline = run.get("terminal_offline_gates")
    if offline is None:
        failures.append("terminal:offline_gates_missing")
    else:
        failures.extend(offline["failures"])
    if serialized_validation.get("status") != "pass":
        failures.append("checkpoint:serialized_validation")
    if serialized_validation.get("optimizer_state_steps") != _expected_optimizer_steps(
        int(run.get("optimizer_steps_completed", 0))
    ):
        failures.append("checkpoint:optimizer_steps")
    if serialized_validation.get("metadata_exact") is not True:
        failures.append("checkpoint:metadata")
    if run.get("same_optimizer_object_across_all_updates") is not True:
        failures.append("optimizer:object_identity")
    if run.get("optimizer_identity_count") != 1:
        failures.append("optimizer:object_count")
    if offline is not None and offline.get("accepted_before_checkpoint_validation"):
        if (run.get("independent_replay_validation") or {}).get("status") != "pass":
            failures.append("independent_replay:validation")
        if serialized_validation.get("terminal_all_830_outputs_byte_exact") is not True:
            failures.append("checkpoint:terminal_output_identity")
    return {
        "accepted": not failures,
        "failures": list(dict.fromkeys(failures)),
        "terminal_offline_acceptance": offline,
        "stage_1_safety": run.get("stage_1_safety"),
        "stage_2_update_safety_count": len(
            run.get("stage_2_update_summaries", [])
        ),
        "full_diagnostic_update_ordinals": sorted(
            int(value) for value in run.get("stage_2_full_diagnostics", {})
        ),
        "parameter_optimizer_contract_pass": run.get(
            "parameter_optimizer_contract_pass"
        ),
        "value_contract_pass": run.get("value_contract_pass"),
        "serialized_checkpoint_validation": dict(serialized_validation),
    }


def _output_artifact_inventory(
    output_directory: Path,
    directory_guard: inherited._StableDirectoryGuard,
    *,
    held_checkpoint_names: frozenset[str] = frozenset(),
) -> list[dict[str, Any]]:
    """Enumerate guarded direct-child names and types without hashing files."""

    output = output_directory.absolute()
    if directory_guard.path != output:
        raise ValueError("artifact inventory guard path mismatch")
    directory_guard.ensure_current()
    records: list[dict[str, Any]] = []
    with os.scandir(output) as entries:
        for entry in entries:
            path = output / entry.name
            if entry.name in held_checkpoint_names:
                # DirEntry classification uses the metadata returned by the
                # directory enumeration.  Do not reacquire either held hard-link
                # name while the transferred delete-pending guard is live.
                entry_stat = entry.stat(follow_symlinks=False)
                link_or_reparse = bool(
                    entry.is_symlink()
                    or getattr(entry_stat, "st_file_attributes", 0)
                    & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
                )
            else:
                link_or_reparse = bool(
                    entry.is_symlink() or inherited._is_link_or_reparse(path)
                )
            if link_or_reparse:
                entry_type = "link_or_reparse"
            elif entry.is_dir(follow_symlinks=False):
                entry_type = "directory"
            elif entry.is_file(follow_symlinks=False):
                entry_type = "regular_file"
            else:
                entry_type = "other"
            records.append(
                {
                    "name": entry.name,
                    "type": entry_type,
                    "link_or_reparse": link_or_reparse,
                    "byte_size": None,
                    "sha256": None,
                    "projection": None,
                }
            )
    directory_guard.ensure_current()
    return sorted(records, key=lambda row: row["name"])


def _held_checkpoint_alias_name(
    checkpoint_guard: inherited._StableFileGuard,
    directory_guard: inherited._StableDirectoryGuard,
) -> str:
    """Authenticate the one exact private alias name from the live guard only."""

    if not isinstance(checkpoint_guard, inherited._StableFileGuard):
        raise ValueError("held checkpoint guard type mismatch")
    prefix = ".candidate-"
    suffix = ".staging.pt"
    name = checkpoint_guard.path.name
    token = name[len(prefix) : -len(suffix)] if (
        name.startswith(prefix) and name.endswith(suffix)
    ) else ""
    if (
        checkpoint_guard.path.parent != directory_guard.path
        or len(token) != 32
        or any(character not in "0123456789abcdef" for character in token)
        or checkpoint_guard._delete is not True
    ):
        raise ValueError("held checkpoint private alias provenance mismatch")
    checkpoint_guard.ensure_bound_to(directory_guard)
    return name


def _require_exact_output_artifacts(
    output_directory: Path,
    directory_guard: inherited._StableDirectoryGuard,
    expected_hashes: Mapping[str, str | None],
    *,
    checkpoint_path: Path | None = None,
    checkpoint_sha256: str | None = None,
    checkpoint_guard: inherited._StableFileGuard | None = None,
    checkpoint_readback: bytes | None = None,
) -> list[dict[str, Any]]:
    evidence_values = (
        checkpoint_path,
        checkpoint_sha256,
        checkpoint_guard,
        checkpoint_readback,
    )
    evidence_present = tuple(value is not None for value in evidence_values)
    if any(evidence_present) and not all(evidence_present):
        raise ValueError("partial held checkpoint evidence")
    held = all(evidence_present)
    if held != ("candidate.pt" in expected_hashes):
        raise ValueError("held checkpoint evidence and allowlist disagree")
    internal_alias: str | None = None
    held_names: frozenset[str] = frozenset()
    if held:
        assert checkpoint_guard is not None
        internal_alias = _held_checkpoint_alias_name(
            checkpoint_guard, directory_guard
        )
        if internal_alias == "candidate.pt" or internal_alias in expected_hashes:
            raise ValueError("held checkpoint public and internal sets overlap")
        held_names = frozenset(("candidate.pt", internal_alias))
    records = _output_artifact_inventory(
        output_directory,
        directory_guard,
        held_checkpoint_names=held_names,
    )
    expected_physical_names = sorted((*expected_hashes, *((internal_alias,) if held else ())))
    if [row["name"] for row in records] != expected_physical_names:
        raise ValueError("output artifact set mismatch")
    for record in records:
        if record["type"] != "regular_file" or record["link_or_reparse"]:
            raise ValueError("output artifact is not a direct regular file")
        record["projection"] = (
            "internal_held_checkpoint_alias"
            if record["name"] == internal_alias
            else "public_artifact"
        )
    directory_guard.ensure_current()
    by_name = {record["name"]: record for record in records}
    if held:
        assert checkpoint_path is not None
        assert checkpoint_sha256 is not None
        assert checkpoint_guard is not None
        assert checkpoint_readback is not None
        output = output_directory.absolute()
        expected_path = output / "candidate.pt"
        if not isinstance(checkpoint_path, Path) or checkpoint_path != expected_path:
            raise ValueError("held checkpoint public path mismatch")
        if checkpoint_path.parent != directory_guard.path:
            raise ValueError("held checkpoint public parent mismatch")
        expected_checkpoint_hash = _strict_sha256(
            checkpoint_sha256, label="held checkpoint SHA-256"
        )
        if expected_hashes.get("candidate.pt") != expected_checkpoint_hash:
            raise ValueError("held checkpoint allowlist hash mismatch")
        if type(checkpoint_readback) is not bytes:
            raise ValueError("held checkpoint readback must be exact bytes")
        if (
            checkpoint_guard.path.parent != directory_guard.path
            or checkpoint_guard.path == expected_path
            or checkpoint_guard.path.name != internal_alias
            or checkpoint_guard._delete is not True
        ):
            raise ValueError("held checkpoint guard provenance mismatch")
        checkpoint_guard.ensure_bound_to(directory_guard)
        held_readback = inherited._win_read_all(checkpoint_guard.handle)
        held_hash = hashlib.sha256(checkpoint_readback).hexdigest().upper()
        if held_readback != checkpoint_readback or held_hash != expected_checkpoint_hash:
            raise ValueError("held checkpoint readback mismatch")
        by_name["candidate.pt"]["byte_size"] = len(checkpoint_readback)
        by_name["candidate.pt"]["sha256"] = held_hash
        assert internal_alias is not None
        by_name[internal_alias]["byte_size"] = len(checkpoint_readback)
        by_name[internal_alias]["sha256"] = held_hash
        checkpoint_guard.ensure_bound_to(directory_guard)
    for record in records:
        if record["name"] in held_names:
            continue
        path = output_directory.absolute() / record["name"]
        handle = inherited._win_open_handle(
            path,
            desired_access=inherited._GENERIC_READ,
            share_mode=(
                inherited._FILE_SHARE_READ
                | inherited._FILE_SHARE_WRITE
                | inherited._FILE_SHARE_DELETE
            ),
            creation_disposition=inherited._OPEN_EXISTING,
            flags=(
                inherited._FILE_ATTRIBUTE_NORMAL
                | inherited._FILE_FLAG_OPEN_REPARSE_POINT
            ),
        )
        try:
            attributes, _identity, final_path = inherited._win_handle_information(handle)
            if (
                attributes
                & (
                    inherited._FILE_ATTRIBUTE_DIRECTORY
                    | inherited._FILE_ATTRIBUTE_REPARSE_POINT
                )
                or final_path
                != inherited._normalized_windows_path(path.absolute())
            ):
                raise ValueError("artifact inventory file identity mismatch")
            payload = inherited._win_read_all(handle)
        finally:
            inherited._win_close_handle(handle)
        record["byte_size"] = len(payload)
        record["sha256"] = hashlib.sha256(payload).hexdigest().upper()
        expected_hash = expected_hashes[record["name"]]
        if expected_hash is not None and record["sha256"] != expected_hash:
            raise ValueError(f"output artifact hash mismatch: {record['name']}")
    directory_guard.ensure_current()
    return records


def _delete_owned_status_artifact(
    path: Path,
    *,
    expected_sha256: str,
    directory_guard: inherited._StableDirectoryGuard,
) -> None:
    absolute = path.absolute()
    if absolute.parent != directory_guard.path:
        raise ValueError("owned status artifact parent mismatch")
    directory_guard.ensure_current()
    handle = inherited._win_open_handle(
        absolute,
        desired_access=inherited._GENERIC_READ | inherited._DELETE,
        share_mode=(
            inherited._FILE_SHARE_READ
            | inherited._FILE_SHARE_WRITE
            | inherited._FILE_SHARE_DELETE
        ),
        creation_disposition=inherited._OPEN_EXISTING,
        flags=(
            inherited._FILE_ATTRIBUTE_NORMAL
            | inherited._FILE_FLAG_OPEN_REPARSE_POINT
        ),
    )
    try:
        attributes, _identity, final_path = inherited._win_handle_information(handle)
        payload = inherited._win_read_all(handle)
        if (
            attributes
            & (
                inherited._FILE_ATTRIBUTE_DIRECTORY
                | inherited._FILE_ATTRIBUTE_REPARSE_POINT
            )
            or final_path != inherited._normalized_windows_path(absolute)
            or hashlib.sha256(payload).hexdigest().upper() != expected_sha256
        ):
            raise ValueError("owned status artifact identity mismatch during cleanup")
        inherited._win_delete_on_close(handle)
    finally:
        inherited._win_close_handle(handle)
    directory_guard.ensure_current()


def _after_status_publication_before_artifact_check() -> None:
    """No-op fault-injection seam after both owned status files exist."""


def _after_checkpoint_publication_before_artifact_check() -> None:
    """No-op fault-injection seam after the public checkpoint identity exists."""


def _publish_status_exact(
    output_directory: Path,
    *,
    status: str,
    receipt: Mapping[str, Any],
    directory_guard: inherited._StableDirectoryGuard,
    checkpoint_path: Path | None = None,
    checkpoint_sha256: str | None = None,
    checkpoint_guard: inherited._StableFileGuard | None = None,
    checkpoint_readback: bytes | None = None,
) -> tuple[Path, str]:
    """Wrap the real publisher with phase-exact artifact allowlists."""

    evidence = (
        checkpoint_path,
        checkpoint_sha256,
        checkpoint_guard,
        checkpoint_readback,
    )
    if any(value is not None for value in evidence) and not all(
        value is not None for value in evidence
    ):
        raise ValueError("partial checkpoint evidence for status publication")
    expected_pre: dict[str, str | None] = {}
    if checkpoint_guard is not None:
        checkpoint_guard.ensure_bound_to(directory_guard)
        expected_pre["candidate.pt"] = checkpoint_sha256
    held_arguments = {
        "checkpoint_path": checkpoint_path,
        "checkpoint_sha256": checkpoint_sha256,
        "checkpoint_guard": checkpoint_guard,
        "checkpoint_readback": checkpoint_readback,
    }
    _require_exact_output_artifacts(
        output_directory, directory_guard, expected_pre, **held_arguments
    )
    published = False
    receipt_path: Path | None = None
    receipt_file_hash: str | None = None
    marker_path = output_directory.absolute() / status.upper()
    marker_hash: str | None = None
    try:
        receipt_path, receipt_file_hash = inherited._publish_status(
            output_directory,
            status=status,
            receipt=receipt,
            directory_guard=directory_guard,
        )
        published = True
        marker = {
            "receipt_file_sha256": receipt_file_hash,
            "receipt_sha256": str(receipt["receipt_sha256"]),
            "status": status,
        }
        marker_hash = hashlib.sha256(
            canonical_json_bytes(marker, newline=True)
        ).hexdigest().upper()
        _after_status_publication_before_artifact_check()
        expected_post = {
            **expected_pre,
            receipt_path.name: receipt_file_hash,
            marker_path.name: marker_hash,
        }
        _require_exact_output_artifacts(
            output_directory,
            directory_guard,
            expected_post,
            **held_arguments,
        )
        return receipt_path, receipt_file_hash
    except Exception:
        if published:
            assert receipt_path is not None
            assert receipt_file_hash is not None
            assert marker_hash is not None
            _delete_owned_status_artifact(
                marker_path,
                expected_sha256=marker_hash,
                directory_guard=directory_guard,
            )
            _delete_owned_status_artifact(
                receipt_path,
                expected_sha256=receipt_file_hash,
                directory_guard=directory_guard,
            )
        raise


def _publish_checkpoint_exact(
    output_directory: Path,
    *,
    model: Any,
    metadata: Mapping[str, Any],
    optimizer: torch.optim.Optimizer,
    directory_guard: inherited._StableDirectoryGuard,
) -> tuple[Path, str, inherited._StableFileGuard, bytes]:
    """Wrap the real checkpoint publisher with empty/candidate-only checks."""

    _require_exact_output_artifacts(output_directory, directory_guard, {})
    try:
        result = inherited._publish_checkpoint_exclusive(
            output_directory,
            model=model,
            metadata=metadata,
            optimizer=optimizer,
            directory_guard=directory_guard,
        )
    except inherited._CheckpointPublicationHandoffError as handoff:
        try:
            handoff.checkpoint_guard.ensure_bound_to(directory_guard)
            _require_exact_output_artifacts(
                output_directory,
                directory_guard,
                {"candidate.pt": handoff.checkpoint_sha256},
                checkpoint_path=handoff.checkpoint_path,
                checkpoint_sha256=handoff.checkpoint_sha256,
                checkpoint_guard=handoff.checkpoint_guard,
                checkpoint_readback=handoff.checkpoint_readback,
            )
        except Exception:
            handoff.checkpoint_guard.close()
            raise
        raise
    checkpoint_path, checkpoint_hash, checkpoint_guard, readback = result
    try:
        checkpoint_guard.ensure_bound_to(directory_guard)
        _after_checkpoint_publication_before_artifact_check()
        _require_exact_output_artifacts(
            output_directory,
            directory_guard,
            {"candidate.pt": checkpoint_hash},
            checkpoint_path=checkpoint_path,
            checkpoint_sha256=checkpoint_hash,
            checkpoint_guard=checkpoint_guard,
            checkpoint_readback=readback,
        )
        return checkpoint_path, checkpoint_hash, checkpoint_guard, readback
    except Exception:
        checkpoint_guard.close()
        raise


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
        **_contract_bindings(),
        "status": "rejected",
        "base_plan_sha256": PLAN_SHA256,
        "base_plan_path": PLAN_RELATIVE_PATH.as_posix(),
        "plan_correction_path": CORRECTION_RELATIVE_PATH.as_posix(),
        "plan_correction_sha256": CORRECTION_SHA256,
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
        "same_iteration_retry": False,
    }
    core = _receipt_core_with_nonfinite_evidence(core, status="rejected")
    receipt = {**core, "receipt_sha256": canonical_sha256(core)}
    path, file_hash = _publish_status_exact(
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
    if not 1 <= progress.optimizer_steps_completed <= TOTAL_OPTIMIZER_STEPS:
        raise ValueError("post-step rejection requires completed step count 1 through 33")
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
                **_contract_bindings(),
                "base_plan_sha256": PLAN_SHA256,
                "plan_correction_path": CORRECTION_RELATIVE_PATH.as_posix(),
                "plan_correction_sha256": CORRECTION_SHA256,
                "plan_correction_v2_path": CORRECTION_V2_RELATIVE_PATH.as_posix(),
                "plan_correction_v2_sha256": CORRECTION_V2_SHA256,
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
                ) = _publish_checkpoint_exact(
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
            **_contract_bindings(),
            "status": "rejected",
            "base_plan_sha256": PLAN_SHA256,
            "base_plan_path": PLAN_RELATIVE_PATH.as_posix(),
            "plan_correction_path": CORRECTION_RELATIVE_PATH.as_posix(),
            "plan_correction_sha256": CORRECTION_SHA256,
            "plan_correction_v2_path": CORRECTION_V2_RELATIVE_PATH.as_posix(),
            "plan_correction_v2_sha256": CORRECTION_V2_SHA256,
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
        core = _receipt_core_with_nonfinite_evidence(core, status="rejected")
        receipt = {**core, "receipt_sha256": canonical_sha256(core)}
        receipt_path, receipt_file_hash = _publish_status_exact(
            output_directory,
            status="rejected",
            receipt=receipt,
            directory_guard=directory_guard,
            checkpoint_path=checkpoint_path,
            checkpoint_sha256=checkpoint_hash,
            checkpoint_guard=checkpoint_guard,
            checkpoint_readback=readback,
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
    loaded["execution_fixed_inputs"] = _build_authorized_execution_fixed_inputs(
        loaded, probe
    )
    output_guard = inherited._create_and_guard_output_directory(output_directory)
    progress = ExecutionProgress()
    checkpoint_guard: inherited._StableFileGuard | None = None
    checkpoint_path: Path | None = None
    checkpoint_hash: str | None = None
    checkpoint_readback: bytes | None = None
    metadata: Mapping[str, Any] | None = None
    phase = "frozen_readout_interaction_maturation_updates"
    try:
        run = _run_two_stage(loaded, probe, progress)
        if (run.get("terminal_offline_gates") or {}).get(
            "accepted_before_checkpoint_validation"
        ):
            run["independent_replay_validation"] = _independent_replay_validation(
                run, probe, loaded["execution_fixed_inputs"]
            )
        else:
            run["independent_replay_validation"] = None
        completed_stage = int(run["optimizer_steps_completed"])
        metadata = checkpoint_metadata(
            source_hashes=loaded["source_hashes"],
            training={
                "pilot": PLAN_ID,
                **_contract_bindings(),
                "base_plan_path": PLAN_RELATIVE_PATH.as_posix(),
                "base_plan_sha256": PLAN_SHA256,
                "plan_correction_path": CORRECTION_RELATIVE_PATH.as_posix(),
                "plan_correction_sha256": CORRECTION_SHA256,
                "plan_correction_v2_path": CORRECTION_V2_RELATIVE_PATH.as_posix(),
                "plan_correction_v2_sha256": CORRECTION_V2_SHA256,
                "execution_spec_path": str(execution_spec_path),
                "execution_spec_sha256": execution_spec_sha256,
                "prepare_receipt_sha256": probe["receipt_sha256"],
                "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
                "manifest_sha256": MANIFEST_SHA256,
                "dataset_sha256": DATASET_SHA256,
                "training_contract": probe["training_contract"],
                "adam": copy.deepcopy(ADAM_CONFIG),
                "stage_1_optimizer_steps": 1,
                "stage_2_optimizer_steps": progress.stage_2_updates_completed,
                "diagnostic_update_ordinals": list(DIAGNOSTIC_UPDATE_ORDINALS),
                "fixed_anchor_kl_coefficients": [0.1] * completed_stage,
                "adaptive_anchor_kl_adjustment": False,
                "optimizer_steps_completed": run["optimizer_steps_completed"],
                "completed_stage_2_updates": progress.stage_2_updates_completed,
                "weighted_value_loss": 0.0,
                "raw_value_mse_initial": run["raw_value_mse_initial"],
                "safety_stop": run["safety_stop"],
                "same_iteration_retry": False,
                "checkpoint_provenance_validation": "required_after_save",
            },
        )
        phase = "checkpoint_exclusive_publication"
        (
            checkpoint_path,
            checkpoint_hash,
            checkpoint_guard,
            checkpoint_readback,
        ) = _publish_checkpoint_exact(
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
            loaded=loaded,
            terminal_metrics=(
                run["stage_2_full_diagnostics"]["32"]
                if completed_stage == TOTAL_OPTIMIZER_STEPS else None
            ),
        )
        gates = _final_gate_report(run, serialized_validation=serialized)
        status = "accepted" if gates["accepted"] else "rejected"
        stage_keys = (
            "stage_1_report", "stage_1_metrics", "stage_1_safety",
            "stage_1_value_identity", "stage_2_update_summaries",
            "stage_2_full_diagnostics", "stage_2_milestone_summaries",
            "optimizer_steps_completed", "same_optimizer_object_across_all_updates",
            "optimizer_identity_count", "raw_value_mse_initial", "safety_stop",
            "safety_stop_after_stage_2_update", "terminal_end_gates",
            "terminal_offline_gates", "parameter_optimizer_contract_pass",
            "value_contract_pass", "frozen_encoder_value_contract",
            "stage_1_record_hash", "independent_replay_validation",
        )
        run_receipt = {name: run.get(name) for name in stage_keys}
        core = {
            "schema_version": EXECUTION_RECEIPT_SCHEMA_VERSION,
            **_contract_bindings(),
            "status": status,
            "base_plan_sha256": PLAN_SHA256,
            "base_plan_path": PLAN_RELATIVE_PATH.as_posix(),
            "plan_correction_path": CORRECTION_RELATIVE_PATH.as_posix(),
            "plan_correction_sha256": CORRECTION_SHA256,
            "plan_correction_v2_path": CORRECTION_V2_RELATIVE_PATH.as_posix(),
            "plan_correction_v2_sha256": CORRECTION_V2_SHA256,
            "execution_spec_path": str(execution_spec_path),
            "execution_spec_sha256": execution_spec_sha256,
            "prepare_receipt_sha256": probe["receipt_sha256"],
            "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
            "rejected_checkpoint_sha256": REJECTED_CHECKPOINT_SHA256,
            "manifest_sha256": MANIFEST_SHA256,
            "dataset_sha256": DATASET_SHA256,
            "fixed_advantages_sha256": FIXED_ADVANTAGES_SHA256,
            "fixed_behavior_logprobabilities_sha256": (
                FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256
            ),
            "output_checkpoint_path": str(checkpoint_path.absolute()),
            "output_checkpoint_sha256": checkpoint_hash,
            "training": run_receipt,
            "serialized_checkpoint_validation": serialized,
            "gates": gates,
            "accepted_marker_written": status == "accepted",
            "same_iteration_retry": False,
        }
        core = _receipt_core_with_nonfinite_evidence(core, status=status)
        receipt = {**core, "receipt_sha256": canonical_sha256(core)}
        phase = f"{status}_status_publication"
        receipt_path, receipt_file_hash = _publish_status_exact(
            output_directory,
            status=status,
            receipt=receipt,
            directory_guard=output_guard,
            checkpoint_path=checkpoint_path,
            checkpoint_sha256=checkpoint_hash,
            checkpoint_guard=checkpoint_guard,
            checkpoint_readback=checkpoint_readback,
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
            if phase == "frozen_readout_interaction_maturation_updates"
            else phase
        )
        if progress.optimizer_steps_completed >= 1:
            if (
                phase == "checkpoint_exclusive_publication"
                and checkpoint_guard is None
            ):
                raise error
            if phase.endswith("_status_publication"):
                raise error
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
