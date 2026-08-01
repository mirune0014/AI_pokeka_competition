"""Audited prepare/execute boundary for the iteration-005 one-step PPO pilot.

The immutable implementation plan authorizes probe preparation only.  The
``execute`` command additionally requires a separately hashed execution spec
that pins the exact probe receipt, implementation, inputs, runtime, and output
directory.  This module deliberately does not call :func:`train_ppo.train`.
"""

from __future__ import annotations

import argparse
import copy
import ctypes
from ctypes import wintypes
from dataclasses import asdict
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import stat
import statistics
from typing import Any, Iterable, Mapping, Sequence
import uuid

import torch

from .frozen_sources import (
    checkpoint_source_hashes,
    find_repo_root,
    latest_source_dir,
    seeded_engine_dir,
    sha256_file,
)
from .model import (
    ModelConfig,
    ResidualActorCritic,
    _validate_metadata,
    checkpoint_metadata,
    load_checkpoint,
    save_checkpoint,
    sha256_checkpoint,
)
from .public_state import public_state_hash
from .reference_policy import behavior_action_order_sha256
from .reference_policy import validate_reference_prior_identity
from .runtime_contract import (
    REQUIRED_THREAD_ENVIRONMENT,
    configure_single_thread_runtime,
)
from .train_ppo import (
    PPOConfig,
    _gae,
    _torch_behavior_anchor_kl,
    _torch_behavior_distribution,
    _validate_rows,
    load_manifest_dataset,
)


PLAN_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_005_conservative_ppo_implementation_plan.json"
)
PLAN_SHA256 = "E47800D5842FDEB0E49B9C0CBC6A4F55D334091DF6D79C253941DCFC28047577"
PLAN_CANONICAL_SHA256 = (
    "F4A8BD8EC92849175272379898D43A6D1E0263519E5E9F5FFCC7C3CCAD19959E"
)
CORRECTION_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl/specs/"
    "phase1_iteration_005_conservative_ppo_provenance_correction_v1.json"
)
CORRECTION_SHA256 = (
    "C18C2985EF114746A794A3EB0F9C13058A7266C7C240CF28A2B4A3736BAB4FD8"
)
CORRECTION_SCHEMA_VERSION = (
    "archaludon-rl-conservative-ppo-provenance-correction-v1"
)
CORRECTION_ID = (
    "phase1-iteration-005-conservative-ppo-provenance-correction-20260801"
)
BASE_PLAN_ID = "phase1-iteration-005-conservative-ppo-implementation-20260731"
BASE_PLAN_SCHEMA_VERSION = "archaludon-rl-conservative-ppo-implementation-plan-v1"
SUPERSEDED_SOURCE_SNAPSHOT_SHA256 = (
    "2B4E0795439843A69ED78EA3EA1567C791271EFEFBF2E4662940CB93F2E5F1BB"
)
CORRECTED_SOURCE_SNAPSHOT_SHA256 = (
    "FA6BE7FB76977C60D89F5D0505AC7CDE9656442F96905666E6F7605A8EDC2985"
)
CORRECTED_SOURCE_SNAPSHOT_FILE_COUNT = 46
STRICT_IMPLEMENTATION_SNAPSHOT_DEFINITION = (
    "Enumerate regular files recursively, excluding every path with a __pycache__ "
    "or test_outputs component and every .pyc suffix. Sort by the unsigned UTF-8 "
    "bytes of each relative POSIX path in ascending lexicographic order. Hash the "
    "concatenation, for each file, of relative_path UTF-8 bytes, NUL, decimal "
    "byte_size ASCII, NUL, uppercase_file_sha256 ASCII, and LF."
)
IMPLEMENTATION_RELATIVE_PATH = PurePosixPath(
    "experiments/archaludon_latest_v1_rl_ppo_candidate_20260731"
)
APPROVED_OUTPUT_RELATIVE_PATH = PurePosixPath(
    "analysis_outputs/"
    "archaludon_latest_v1_rl_phase1_iteration_005_conservative_ppo_20260731"
)
PREPARE_OUTPUT_DIRECTORY_PREFIX = "phase1_iteration_005_prepare"
PREPARE_OUTPUT_FILENAME = "pretraining_probe_receipt.json"
INPUT_CHECKPOINT_RELATIVE_PATH = PurePosixPath(
    "analysis_outputs/"
    "archaludon_latest_v1_rl_phase1_iteration_004_temperature065_checkpoint_"
    "deterministic_20260731/initial_zero_temperature065.pt"
)
INPUT_CHECKPOINT_SHA256 = (
    "24D8A4EACD9D7B699D327D3F2436F4DA21AC79433038E6FA96F9AE0E50F8FB04"
)
MANIFEST_RELATIVE_PATH = PurePosixPath(
    "analysis_outputs/"
    "archaludon_latest_v1_rl_phase1_iteration_004_temperature065_single_"
    "thread_20260731/rollouts/run_manifest.json"
)
MANIFEST_SHA256 = "30BF22BE56E73E8790A40135DD78080217FFAB7598D9646887FD8742D0FCF393"
DATASET_SHA256 = "3D714FC248B597ADD412B1D9B4BAD60DDF6BDEB3DFA652264D763D7A843AC41B"
BEHAVIOR_POLICY_SCHEMA_SHA256 = (
    "11049A88FB535D7496A2B3C9F7A1A48DB71FD20EFAD3EA39FD9E35CD79819F22"
)
EXPECTED_ON_POLICY_ROWS = 830
EXPECTED_TORCH_VERSION = "2.11.0+cu128"
PREPARE_RECEIPT_SCHEMA_VERSION = "conservative-ppo-pretraining-probe-v1"
EXECUTION_SPEC_SCHEMA_VERSION = "conservative-ppo-execution-spec-v1"
EXECUTION_RECEIPT_SCHEMA_VERSION = "conservative-ppo-execution-receipt-v1"
END_SEMANTIC_IDENTITY = (
    "1da3a7c010534db001ac9c799ad23f4396e92348eb5ed72264326af8d66fbb34"
)


if os.name == "nt":
    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    _GENERIC_READ = 0x80000000
    _GENERIC_WRITE = 0x40000000
    _DELETE = 0x00010000
    _FILE_READ_ATTRIBUTES = 0x00000080
    _FILE_SHARE_READ = 0x00000001
    _FILE_SHARE_WRITE = 0x00000002
    _FILE_SHARE_DELETE = 0x00000004
    _OPEN_EXISTING = 3
    _CREATE_NEW = 1
    _FILE_ATTRIBUTE_NORMAL = 0x00000080
    _FILE_ATTRIBUTE_DIRECTORY = 0x00000010
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
    _FILE_FLAG_WRITE_THROUGH = 0x80000000
    _FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _FILE_DISPOSITION_INFO_CLASS = 4
    _SYNCHRONIZE = 0x00100000
    _OBJ_CASE_INSENSITIVE = 0x00000040
    _FILE_CREATE = 0x00000002
    _FILE_DIRECTORY_FILE = 0x00000001
    _FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
    _FILE_OPEN_REPARSE_POINT = 0x00200000

    class _UnicodeString(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.USHORT),
            ("maximum_length", wintypes.USHORT),
            ("buffer", wintypes.LPWSTR),
        ]

    class _ObjectAttributes(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.ULONG),
            ("root_directory", wintypes.HANDLE),
            ("object_name", ctypes.POINTER(_UnicodeString)),
            ("attributes", wintypes.ULONG),
            ("security_descriptor", wintypes.LPVOID),
            ("security_quality_of_service", wintypes.LPVOID),
        ]

    class _IoStatusBlockUnion(ctypes.Union):
        _fields_ = [("status", wintypes.LONG), ("pointer", wintypes.LPVOID)]

    class _IoStatusBlock(ctypes.Structure):
        _anonymous_ = ("value",)
        _fields_ = [("value", _IoStatusBlockUnion), ("information", ctypes.c_size_t)]

    class _ByHandleFileInformation(ctypes.Structure):
        _fields_ = [
            ("file_attributes", wintypes.DWORD),
            ("creation_time", wintypes.FILETIME),
            ("last_access_time", wintypes.FILETIME),
            ("last_write_time", wintypes.FILETIME),
            ("volume_serial_number", wintypes.DWORD),
            ("file_size_high", wintypes.DWORD),
            ("file_size_low", wintypes.DWORD),
            ("number_of_links", wintypes.DWORD),
            ("file_index_high", wintypes.DWORD),
            ("file_index_low", wintypes.DWORD),
        ]

    class _FileDispositionInformation(ctypes.Structure):
        _fields_ = [("delete_file", wintypes.BOOL)]

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.CreateFileW.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    _kernel32.CreateFileW.restype = wintypes.HANDLE
    _kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    _kernel32.CloseHandle.restype = wintypes.BOOL
    _kernel32.FlushFileBuffers.argtypes = (wintypes.HANDLE,)
    _kernel32.FlushFileBuffers.restype = wintypes.BOOL
    _kernel32.GetFileInformationByHandle.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_ByHandleFileInformation),
    )
    _kernel32.GetFileInformationByHandle.restype = wintypes.BOOL
    _kernel32.GetFileSizeEx.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_longlong),
    )
    _kernel32.GetFileSizeEx.restype = wintypes.BOOL
    _kernel32.GetFinalPathNameByHandleW.argtypes = (
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    _kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    _kernel32.SetFileInformationByHandle.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
    )
    _kernel32.SetFileInformationByHandle.restype = wintypes.BOOL
    _kernel32.SetFilePointerEx.argtypes = (
        wintypes.HANDLE,
        ctypes.c_longlong,
        ctypes.POINTER(ctypes.c_longlong),
        wintypes.DWORD,
    )
    _kernel32.SetFilePointerEx.restype = wintypes.BOOL
    _kernel32.ReadFile.argtypes = (
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    )
    _kernel32.ReadFile.restype = wintypes.BOOL
    _kernel32.WriteFile.argtypes = (
        wintypes.HANDLE,
        wintypes.LPCVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    )
    _kernel32.WriteFile.restype = wintypes.BOOL
    _ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
    _ntdll.NtCreateFile.argtypes = (
        ctypes.POINTER(wintypes.HANDLE),
        wintypes.DWORD,
        ctypes.POINTER(_ObjectAttributes),
        ctypes.POINTER(_IoStatusBlock),
        ctypes.POINTER(ctypes.c_longlong),
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.ULONG,
        wintypes.LPVOID,
        wintypes.ULONG,
    )
    _ntdll.NtCreateFile.restype = wintypes.LONG
    _ntdll.RtlNtStatusToDosError.argtypes = (wintypes.LONG,)
    _ntdll.RtlNtStatusToDosError.restype = wintypes.ULONG


# Every field is explicit; changing a dataclass default cannot alter this pilot.
PILOT_PPO_CONFIG = PPOConfig(
    gamma=0.99,
    gae_lambda=0.95,
    clip_ratio=0.1,
    value_coef=0.5,
    entropy_coef=0.0,
    anchor_kl_target=0.0005,
    anchor_kl_initial_coef=0.1,
    anchor_kl_hard_stop=0.002,
    gradient_clip=0.25,
    learning_rate=0.0001,
    epochs=1,
)
PILOT_ADAM_CONFIG: dict[str, Any] = {
    "name": "Adam",
    "fresh_state": True,
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

_CORRECTION_PURPOSE = (
    "Correct only the implementation-tree ordering definition and source snapshot "
    "binding used by the iteration-005 conservative PPO plan. This correction does "
    "not authorize training, games, packaging, promotion, or submission."
)
_SUPERSEDED_ORDERING_ACTUAL = (
    "Python 3.11 WindowsPath native ordering. On this frozen 46-path set it is "
    "reproduced by sorting relative POSIX paths case-insensitively before hashing "
    "records."
)
_CORRECTION_INVARIANTS = (
    "The base plan remains immutable and is still required at its exact path and "
    "SHA-256.",
    "Every base-plan field other than immutable_inputs.source_implementation."
    "snapshot_sha256 remains unchanged.",
    "The source implementation remains unchanged; this correction changes only its "
    "snapshot ordering definition and derived hash.",
    "Every candidate prepare receipt and execution spec after this correction must "
    "use the corrected case-sensitive UTF-8 byte ordering.",
    "All v1, v2, and v3 prepare receipts remain historical rejected evidence and "
    "must not be used for execution.",
)
_CORRECTION_EXECUTION_STOP_RULE = (
    "Regenerate a no-training v4 prepare receipt and obtain independent code and "
    "numerical provenance audits before authoring a separate immutable execution spec."
)


def canonical_json_bytes(value: Any, *, newline: bool = False) -> bytes:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return encoded + (b"\n" if newline else b"")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest().upper()


def _strict_sha256(value: Any, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789ABCDEF" for character in value)
    ):
        raise ValueError(f"{label} must be an uppercase SHA-256")
    return value


def _repo_path(relative: PurePosixPath) -> Path:
    return find_repo_root() / Path(*relative.parts)


def _read_regular_nonlink_bytes(path: Path, *, label: str) -> bytes:
    """Read one regular, non-link path handle into the sole authoritative buffer."""

    path = path.absolute()
    if _is_link_or_reparse(path):
        raise ValueError(f"{label} must not be a symlink or reparse point")
    try:
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            if not stat.S_ISREG(opened.st_mode):
                raise ValueError(f"{label} must be a regular file")
            payload = stream.read()
    except (FileNotFoundError, IsADirectoryError, PermissionError) as error:
        raise ValueError(f"{label} must be a readable regular file") from error
    if _is_link_or_reparse(path):
        raise ValueError(f"{label} changed to a symlink or reparse point")
    current = path.stat()
    if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
        raise ValueError(f"{label} path changed during read")
    return payload


def _load_hashed_json(
    path: Path, expected_file_sha256: str, *, label: str
) -> Any:
    """Hash and parse the exact same single-read byte buffer."""

    expected = _strict_sha256(expected_file_sha256, label=f"{label} file hash")
    payload = _read_regular_nonlink_bytes(path, label=label)
    if hashlib.sha256(payload).hexdigest().upper() != expected:
        raise ValueError(f"{label} file SHA-256 mismatch")
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains a duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(
            payload.decode("utf-8"), object_pairs_hook=reject_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not valid UTF-8 JSON") from error


def _require_exact_keys(
    value: Any, expected: set[str], *, label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{label} has missing or extra keys")
    return value


def _validate_base_plan(plan: Any) -> dict[str, Any]:
    top = _require_exact_keys(
        plan,
        {
            "schema_version",
            "plan_id",
            "purpose",
            "strength_claim_allowed",
            "parent_result",
            "selected_hypothesis",
            "immutable_inputs",
            "isolated_implementation",
            "training_contract",
            "pretraining_probe_contract",
            "post_update_gates",
            "runtime_smoke_instrumentation",
            "implementation_tests",
            "forbidden_changes",
            "execution_stop_rule",
        },
        label="immutable implementation plan",
    )
    if top["schema_version"] != BASE_PLAN_SCHEMA_VERSION:
        raise ValueError("immutable implementation plan schema mismatch")
    if top["plan_id"] != BASE_PLAN_ID:
        raise ValueError("immutable implementation plan identity mismatch")
    if canonical_sha256(top) != PLAN_CANONICAL_SHA256:
        raise ValueError("immutable implementation plan content mismatch")
    return dict(top)


def _expected_correction_spec() -> dict[str, Any]:
    return {
        "schema_version": CORRECTION_SCHEMA_VERSION,
        "correction_id": CORRECTION_ID,
        "purpose": _CORRECTION_PURPOSE,
        "base_plan": {
            "path": PLAN_RELATIVE_PATH.as_posix(),
            "sha256": PLAN_SHA256,
            "plan_id": BASE_PLAN_ID,
        },
        "source_implementation_snapshot": {
            "path": (
                "experiments/archaludon_latest_v1_rl_temperature_candidate_20260731"
            ),
            "file_count": CORRECTED_SOURCE_SNAPSHOT_FILE_COUNT,
            "superseded_sha256": SUPERSEDED_SOURCE_SNAPSHOT_SHA256,
            "superseded_ordering_actual": _SUPERSEDED_ORDERING_ACTUAL,
            "corrected_sha256": CORRECTED_SOURCE_SNAPSHOT_SHA256,
            "corrected_definition": STRICT_IMPLEMENTATION_SNAPSHOT_DEFINITION,
        },
        "invariants": list(_CORRECTION_INVARIANTS),
        "execution_stop_rule": _CORRECTION_EXECUTION_STOP_RULE,
    }


def _validate_correction_spec(correction: Any) -> dict[str, Any]:
    expected = _expected_correction_spec()
    if not isinstance(correction, Mapping) or dict(correction) != expected:
        raise ValueError(
            "provenance correction has missing, extra, or mismatched fields"
        )
    return dict(correction)


def _load_plan() -> dict[str, Any]:
    path = _repo_path(PLAN_RELATIVE_PATH)
    plan = _load_hashed_json(
        path, PLAN_SHA256, label="immutable implementation plan"
    )
    return _validate_base_plan(plan)


def _load_correction() -> dict[str, Any]:
    correction = _load_hashed_json(
        _repo_path(CORRECTION_RELATIVE_PATH),
        CORRECTION_SHA256,
        label="immutable provenance correction",
    )
    return _validate_correction_spec(correction)


def _load_corrected_plan() -> tuple[dict[str, Any], dict[str, Any]]:
    """Load both immutable documents once and apply the one authorized field change."""

    base_plan = _load_plan()
    correction = _load_correction()
    source = base_plan["immutable_inputs"]["source_implementation"]
    corrected_source = correction["source_implementation_snapshot"]
    if source["path"] != corrected_source["path"]:
        raise ValueError("base plan/correction source path mismatch")
    if source["snapshot_sha256"] != corrected_source["superseded_sha256"]:
        raise ValueError("base plan/correction superseded hash mismatch")
    merged = copy.deepcopy(base_plan)
    merged["immutable_inputs"]["source_implementation"][
        "snapshot_sha256"
    ] = corrected_source["corrected_sha256"]
    comparison = copy.deepcopy(merged)
    comparison["immutable_inputs"]["source_implementation"][
        "snapshot_sha256"
    ] = corrected_source["superseded_sha256"]
    if comparison != base_plan:
        raise ValueError("provenance correction changed more than the source snapshot")
    provenance = {
        "base_plan": {
            "path": PLAN_RELATIVE_PATH.as_posix(),
            "sha256": PLAN_SHA256,
            "schema_version": BASE_PLAN_SCHEMA_VERSION,
            "plan_id": BASE_PLAN_ID,
        },
        "provenance_correction": {
            "path": CORRECTION_RELATIVE_PATH.as_posix(),
            "sha256": CORRECTION_SHA256,
            "schema_version": CORRECTION_SCHEMA_VERSION,
            "correction_id": CORRECTION_ID,
        },
    }
    return merged, provenance


def _verify_plan_immutable_files(plan: Mapping[str, Any]) -> dict[str, Any]:
    parent = plan["parent_result"]
    for path_name, hash_name in (
        ("collection_evaluation_spec_path", "collection_evaluation_spec_sha256"),
        ("sol_ultra_evaluation_path", "sol_ultra_evaluation_sha256"),
    ):
        path = find_repo_root() / Path(str(parent[path_name]))
        if sha256_file(path) != parent[hash_name]:
            raise ValueError(f"immutable parent input {path_name} SHA-256 mismatch")
    source = plan["immutable_inputs"]["source_implementation"]
    source_root = find_repo_root() / Path(str(source["path"]))
    snapshot = implementation_snapshot(source_root)
    if snapshot["sha256"] != source["snapshot_sha256"]:
        raise ValueError("immutable source implementation snapshot mismatch")
    if snapshot["file_count"] != CORRECTED_SOURCE_SNAPSHOT_FILE_COUNT:
        raise ValueError("immutable source implementation file count mismatch")
    if snapshot["definition"] != STRICT_IMPLEMENTATION_SNAPSHOT_DEFINITION:
        raise ValueError("immutable source implementation definition mismatch")
    critical = {
        "archaludon_rl/model.py": source["model_py_sha256"],
        "archaludon_rl/reference_policy.py": source["reference_policy_py_sha256"],
        "archaludon_rl/train_ppo.py": source["train_ppo_py_sha256"],
        "archaludon_rl/trajectory.py": source["trajectory_py_sha256"],
    }
    for relative, expected in critical.items():
        if sha256_file(source_root / Path(relative)) != expected:
            raise ValueError(f"immutable source implementation {relative} mismatch")
    return {
        "path": str(source["path"]),
        "snapshot_sha256": snapshot["sha256"],
        "snapshot_file_count": snapshot["file_count"],
        "snapshot_definition": snapshot["definition"],
        "superseded_windows_order_snapshot_sha256": (
            SUPERSEDED_SOURCE_SNAPSHOT_SHA256
        ),
        "corrected_by": {
            "path": CORRECTION_RELATIVE_PATH.as_posix(),
            "sha256": CORRECTION_SHA256,
            "correction_id": CORRECTION_ID,
        },
        "critical_files": critical,
        "parent_collection_evaluation_spec_sha256": parent[
            "collection_evaluation_spec_sha256"
        ],
        "parent_sol_ultra_evaluation_sha256": parent[
            "sol_ultra_evaluation_sha256"
        ],
    }


def _snapshot_inventory(
    implementation_root: Path,
) -> tuple[
    tuple[int, int, int, int, int],
    dict[str, tuple[int, int, int, int, int]],
    dict[str, tuple[int, int, int, int, int]],
]:
    """Capture a non-link tree inventory for before/after stability checks."""

    def signature(result: os.stat_result) -> tuple[int, int, int, int, int]:
        return (
            int(result.st_dev),
            int(result.st_ino),
            int(result.st_mode),
            int(result.st_size),
            int(result.st_mtime_ns),
        )

    if _is_link_or_reparse(implementation_root):
        raise ValueError("implementation root must not be a symlink or reparse point")
    root_stat = implementation_root.stat()
    if not stat.S_ISDIR(root_stat.st_mode):
        raise ValueError("implementation root must be a directory")
    directories: dict[str, tuple[int, int, int, int, int]] = {}
    files: dict[str, tuple[int, int, int, int, int]] = {}

    def visit(directory: Path, relative_parts: tuple[str, ...]) -> None:
        try:
            entries = list(os.scandir(directory))
        except OSError as error:
            raise ValueError("implementation tree changed during enumeration") from error
        for entry in entries:
            parts = (*relative_parts, entry.name)
            if "__pycache__" in parts or "test_outputs" in parts:
                continue
            relative = PurePosixPath(*parts).as_posix()
            path = directory / entry.name
            if _is_link_or_reparse(path):
                raise ValueError(
                    f"implementation tree contains a symlink or reparse point: {relative}"
                )
            try:
                entry_stat = entry.stat(follow_symlinks=False)
            except OSError as error:
                raise ValueError(
                    "implementation tree changed during enumeration"
                ) from error
            if stat.S_ISDIR(entry_stat.st_mode):
                directories[relative] = signature(entry_stat)
                visit(path, parts)
            elif stat.S_ISREG(entry_stat.st_mode):
                if path.suffix.lower() != ".pyc":
                    files[relative] = signature(entry_stat)
            elif path.suffix.lower() != ".pyc":
                raise ValueError(
                    f"implementation tree contains a non-regular entry: {relative}"
                )

    visit(implementation_root, ())
    return signature(root_stat), directories, files


def implementation_snapshot(root: Path | None = None) -> dict[str, Any]:
    requested_root = (
        _repo_path(IMPLEMENTATION_RELATIVE_PATH) if root is None else root
    ).absolute()
    if _is_link_or_reparse(requested_root):
        raise ValueError("implementation root must not be a symlink or reparse point")
    implementation_root = requested_root.resolve(strict=True)
    before = _snapshot_inventory(implementation_root)
    relative_paths = sorted(before[2], key=lambda value: value.encode("utf-8"))
    rows: list[dict[str, Any]] = []
    preimage: list[bytes] = []
    for relative in relative_paths:
        path = implementation_root.joinpath(*PurePosixPath(relative).parts)
        payload = _read_regular_nonlink_bytes(
            path, label=f"implementation snapshot file {relative}"
        )
        digest = hashlib.sha256(payload).hexdigest().upper()
        size = len(payload)
        if size != before[2][relative][3]:
            raise ValueError("implementation file changed during snapshot")
        rows.append({"path": relative, "bytes": size, "sha256": digest})
        preimage.append(
            relative.encode("utf-8")
            + b"\0"
            + str(size).encode("ascii")
            + b"\0"
            + digest.encode("ascii")
            + b"\n"
        )
    after = _snapshot_inventory(implementation_root)
    if after != before:
        raise ValueError("implementation tree changed during snapshot")
    return {
        "definition": STRICT_IMPLEMENTATION_SNAPSHOT_DEFINITION,
        "file_count": len(rows),
        "sha256": hashlib.sha256(b"".join(preimage)).hexdigest().upper(),
        "files": rows,
    }


def _runtime_identity() -> dict[str, Any]:
    configured = configure_single_thread_runtime(
        torch_module=torch,
        environment=os.environ,
    )
    if configured["torch_version"] != EXPECTED_TORCH_VERSION:
        raise ValueError("pinned Torch version mismatch")
    return configured


def _unique_argmax(probabilities: Sequence[float], required: int | None = None) -> int:
    values = tuple(float(value) for value in probabilities)
    if not values or any(not math.isfinite(value) for value in values):
        raise ValueError("unique argmax requires a finite nonempty distribution")
    maximum = max(values)
    winners = tuple(index for index, value in enumerate(values) if value == maximum)
    if len(winners) != 1:
        raise ValueError("distribution has no unique argmax")
    winner = winners[0]
    if required is not None and winner != required:
        raise ValueError("required action is not the unique argmax")
    return winner


def per_row_anchor_kl(
    post: Sequence[float], anchor: Sequence[float]
) -> float:
    post_values = tuple(float(value) for value in post)
    anchor_values = tuple(float(value) for value in anchor)
    if len(post_values) != len(anchor_values) or not post_values:
        raise ValueError("KL distributions have different or empty supports")
    if any(
        not math.isfinite(value) or value <= 0.0
        for value in (*post_values, *anchor_values)
    ):
        raise ValueError("KL distributions must be finite and positive")
    return sum(
        value * (math.log(value) - math.log(anchor_values[index]))
        for index, value in enumerate(post_values)
    )


def per_row_total_variation(
    post: Sequence[float], pre: Sequence[float]
) -> float:
    post_values = tuple(float(value) for value in post)
    pre_values = tuple(float(value) for value in pre)
    if len(post_values) != len(pre_values) or not post_values:
        raise ValueError("TV distributions have different or empty supports")
    if any(not math.isfinite(value) for value in (*post_values, *pre_values)):
        raise ValueError("TV distributions must be finite")
    return 0.5 * sum(
        abs(left - right) for left, right in zip(post_values, pre_values)
    )


def _model_probabilities(
    model: Any,
    row: Mapping[str, Any],
    *,
    reference_config: Any,
) -> tuple[list[float], float]:
    state = torch.tensor(row["state_vector"], dtype=torch.float32, device="cpu")
    actions = torch.tensor(row["action_vectors"], dtype=torch.float32, device="cpu")
    residuals, value = model(state, actions)
    probabilities, _ = _torch_behavior_distribution(
        residuals,
        teacher_index=int(row["teacher_action"][0]),
        reference_config=reference_config,
    )
    if not torch.isfinite(residuals).all() or not torch.isfinite(value):
        raise ValueError("model probe contains a non-finite output")
    if not torch.isfinite(probabilities).all():
        raise ValueError("model probe contains a non-finite distribution")
    return probabilities.detach().cpu().tolist(), float(value.detach().cpu())


def _load_validated_inputs() -> dict[str, Any]:
    plan, provenance = _load_corrected_plan()
    immutable_file_receipt = _verify_plan_immutable_files(plan)
    checkpoint_path = _repo_path(INPUT_CHECKPOINT_RELATIVE_PATH)
    manifest_path = _repo_path(MANIFEST_RELATIVE_PATH)
    if sha256_checkpoint(checkpoint_path) != INPUT_CHECKPOINT_SHA256:
        raise ValueError("input checkpoint SHA-256 mismatch")
    if sha256_file(manifest_path) != MANIFEST_SHA256:
        raise ValueError("input manifest SHA-256 mismatch")
    source_hashes = checkpoint_source_hashes()
    model, metadata, optimizer_state = load_checkpoint(
        checkpoint_path,
        expected_source_hashes=source_hashes,
        device="cpu",
    )
    require_empty_input_optimizer_state(optimizer_state)
    if any(not torch.isfinite(parameter).all() for parameter in model.parameters()):
        raise ValueError("input checkpoint contains a non-finite parameter")
    prior_receipt = metadata.get("reference_prior_receipt")
    prior_hash = metadata.get("reference_prior_schema_sha256")
    behavior_receipt = metadata.get("behavior_policy_receipt")
    behavior_hash = metadata.get("behavior_policy_schema_sha256")
    if not isinstance(prior_receipt, dict) or not isinstance(prior_hash, str):
        raise ValueError("checkpoint reference-prior identity is missing")
    if not isinstance(behavior_receipt, dict) or behavior_hash != (
        BEHAVIOR_POLICY_SCHEMA_SHA256
    ):
        raise ValueError("checkpoint behavior-policy identity mismatch")
    dataset = load_manifest_dataset(
        manifest_path,
        input_checkpoint_sha256=INPUT_CHECKPOINT_SHA256,
        expected_source_hashes=source_hashes,
        expected_reference_prior_receipt=prior_receipt,
        expected_reference_prior_schema_sha256=prior_hash,
        expected_behavior_policy_receipt=behavior_receipt,
        expected_behavior_policy_schema_sha256=behavior_hash,
    )
    if dataset.manifest.get("dataset_sha256") != DATASET_SHA256:
        raise ValueError("pinned dataset SHA-256 mismatch")
    rows = _validate_rows(
        list(dataset.episodes),
        checkpoint_sha256=INPUT_CHECKPOINT_SHA256,
        source_hashes=source_hashes,
        expected_encoder=metadata.get("encoder") or {},
        behavior_model=model,
        reference_prior_receipt=prior_receipt,
        reference_prior_schema_sha256=prior_hash,
        behavior_policy_receipt=behavior_receipt,
        behavior_policy_schema_sha256=behavior_hash,
    )
    if len(rows) != EXPECTED_ON_POLICY_ROWS:
        raise ValueError("pinned on-policy row count mismatch")
    keys = [
        (str(episode["episode_id"]), int(row["decision_index"]))
        for episode, row in rows
    ]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate episode_id/decision_index key")
    return {
        "plan": plan,
        "plan_provenance": provenance,
        "immutable_file_receipt": immutable_file_receipt,
        "checkpoint_path": checkpoint_path,
        "manifest_path": manifest_path,
        "source_hashes": source_hashes,
        "model": model,
        "metadata": metadata,
        "dataset": dataset,
        "rows": rows,
        "reference_config": validate_reference_prior_identity(
            prior_receipt, prior_hash
        ),
    }


def require_empty_input_optimizer_state(optimizer_state: Any) -> None:
    if optimizer_state is not None:
        raise ValueError("input checkpoint optimizer state must be None")


def require_exact_probe_match(
    pinned: Mapping[str, Any], rebuilt: Mapping[str, Any]
) -> None:
    if dict(pinned) != dict(rebuilt):
        raise ValueError("inputs, rows, probes, or identities changed after prepare")


def _assert_close(actual: float, expected: float, tolerance: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance):
        raise ValueError(f"{label} mismatch: expected {expected!r}, got {actual!r}")


def _build_probe_receipt(runtime: Mapping[str, Any]) -> dict[str, Any]:
    loaded = _load_validated_inputs()
    plan = loaded["plan"]
    model = loaded["model"]
    rows = loaded["rows"]
    episodes = list(loaded["dataset"].episodes)
    reference_config = loaded["reference_config"]
    before_parameters = {
        name: value.detach().clone() for name, value in model.state_dict().items()
    }
    advantages = _gae(episodes, PILOT_PPO_CONFIG)
    raw_advantages = [
        advantages[(str(episode["episode_id"]), int(row["decision_index"]))][0]
        for episode, row in rows
    ]
    independent_mean = sum(raw_advantages) / len(raw_advantages)
    independent_sd = math.sqrt(
        sum((value - independent_mean) ** 2 for value in raw_advantages)
        / len(raw_advantages)
    )
    trainer_advantages = torch.tensor(raw_advantages, dtype=torch.float32)
    trainer_mean_tensor = trainer_advantages.mean()
    trainer_sd_tensor = trainer_advantages.std(unbiased=False)
    trainer_normalized = (
        trainer_advantages - trainer_mean_tensor
    ) / trainer_sd_tensor
    independent_contract = plan["pretraining_probe_contract"][
        "advantage_domains"
    ]["independent_float64"]
    trainer_contract = plan["pretraining_probe_contract"]["advantage_domains"][
        "trainer_float32"
    ]
    _assert_close(
        independent_mean,
        float(independent_contract["advantage_mean"]),
        float(independent_contract["numeric_absolute_tolerance"]),
        "independent advantage mean",
    )
    _assert_close(
        independent_sd,
        float(independent_contract["advantage_population_sd"]),
        float(independent_contract["numeric_absolute_tolerance"]),
        "independent advantage population SD",
    )
    _assert_close(
        float(trainer_mean_tensor),
        float(trainer_contract["advantage_mean"]),
        float(trainer_contract["numeric_absolute_tolerance"]),
        "trainer advantage mean",
    )
    _assert_close(
        float(trainer_sd_tensor),
        float(trainer_contract["advantage_population_sd"]),
        float(trainer_contract["numeric_absolute_tolerance"]),
        "trainer advantage population SD",
    )

    probe_rows: list[dict[str, Any]] = []
    naive_stochastic_end: list[int] = []
    teacher_end: list[int] = []
    teacher_and_sampled_end: list[int] = []
    positive_raw_sampled_end: list[int] = []
    positive_normalized_sampled_end: list[int] = []
    positive_raw_teacher_end: list[int] = []
    positive_normalized_teacher_end: list[int] = []
    with torch.no_grad():
        for ordinal, (episode, row) in enumerate(rows):
            key = (str(episode["episode_id"]), int(row["decision_index"]))
            raw_advantage, value_target = advantages[key]
            independent_normalized = (
                raw_advantage - independent_mean
            ) / independent_sd
            trainer_normalized_value = float(trainer_normalized[ordinal])
            probabilities, probed_value = _model_probabilities(
                model,
                row,
                reference_config=reference_config,
            )
            semantic_rows = tuple(row["legal_semantic_options"])
            identities = tuple(str(item["identity"]) for item in semantic_rows)
            end_indices = tuple(
                index
                for index, identity in enumerate(identities)
                if identity == END_SEMANTIC_IDENTITY
            )
            if len(end_indices) != 1:
                raise ValueError("eligible row does not have exactly one canonical END")
            end_index = end_indices[0]
            teacher_index = int(row["teacher_action"][0])
            sampled_index = int(row["final_action"][0])
            teacher_is_end = teacher_index == end_index
            sampled_is_end = sampled_index == end_index
            if sampled_is_end and not teacher_is_end:
                naive_stochastic_end.append(ordinal)
            if teacher_is_end:
                teacher_end.append(ordinal)
                if raw_advantage > 0.0:
                    positive_raw_teacher_end.append(ordinal)
                if trainer_normalized_value > 0.0:
                    positive_normalized_teacher_end.append(ordinal)
                if sampled_is_end:
                    teacher_and_sampled_end.append(ordinal)
                    if raw_advantage > 0.0:
                        positive_raw_sampled_end.append(ordinal)
                    if trainer_normalized_value > 0.0:
                        positive_normalized_sampled_end.append(ordinal)
            unique_argmax = _unique_argmax(probabilities, teacher_index)
            state_sha = canonical_sha256(row["state_vector"])
            action_sha = canonical_sha256(row["action_vectors"])
            semantic_sha = behavior_action_order_sha256(semantic_rows)
            if semantic_sha != row["behavior_action_order_sha256"]:
                raise ValueError("probe semantic action order mismatch")
            public_sha = public_state_hash(row["public_projection"])
            stored_probabilities = [
                float(value) for value in row["final_probabilities"]
            ]
            probe_rows.append(
                {
                    "ppo_row_ordinal": ordinal,
                    "episode_id": key[0],
                    "opponent_id": str(episode["opponent_id"]),
                    "seat": int(episode["seat"]),
                    "seed": int(episode["seed"]),
                    "decision_index": key[1],
                    "raw_observation_sha256": str(row["raw_observation_sha256"]),
                    "public_state_sha256": public_sha,
                    "state_vector_sha256": state_sha,
                    "action_vectors_sha256": action_sha,
                    "behavior_action_order_sha256": semantic_sha,
                    "legal_semantic_identities": list(identities),
                    "legal_option_count": int(row["legal_option_count"]),
                    "teacher_index": teacher_index,
                    "sampled_index": sampled_index,
                    "end_index": end_index,
                    "teacher_semantic_identity": identities[teacher_index],
                    "sampled_semantic_identity": identities[sampled_index],
                    "raw_advantage": raw_advantage,
                    "value_target": value_target,
                    "independent_normalized_advantage_float64": independent_normalized,
                    "trainer_normalized_advantage_float32": trainer_normalized_value,
                    "stored_behavior_probabilities_float64": stored_probabilities,
                    "pre_update_probabilities_float32": probabilities,
                    "stored_behavior_end_probability_float64": stored_probabilities[
                        end_index
                    ],
                    "pre_update_end_probability_float32": probabilities[end_index],
                    "pre_update_value_float32": probed_value,
                    "pre_update_unique_argmax_index": unique_argmax,
                    "teacher_is_end": teacher_is_end,
                    "sampled_is_end": sampled_is_end,
                }
            )

    memberships = {
        "naive_teacher_not_end_sampled_end_ordinals": naive_stochastic_end,
        "negative_target_ordinals": [
            int(item["ppo_row_ordinal"])
            for item in plan["pretraining_probe_contract"]["negative_targets"]
        ],
        "teacher_end_ordinals": teacher_end,
        "teacher_end_and_sampled_end_ordinals": teacher_and_sampled_end,
        "positive_raw_advantage_sampled_end_ordinals": positive_raw_sampled_end,
        "positive_normalized_advantage_sampled_end_ordinals": (
            positive_normalized_sampled_end
        ),
        "positive_raw_advantage_teacher_end_ordinals": positive_raw_teacher_end,
        "positive_normalized_advantage_teacher_end_ordinals": (
            positive_normalized_teacher_end
        ),
    }
    expected_counts = {
        "naive_teacher_not_end_sampled_end_ordinals": 17,
        "negative_target_ordinals": 4,
        "teacher_end_ordinals": 43,
        "teacher_end_and_sampled_end_ordinals": 41,
        "positive_raw_advantage_sampled_end_ordinals": 31,
        "positive_normalized_advantage_sampled_end_ordinals": 20,
        "positive_raw_advantage_teacher_end_ordinals": 32,
        "positive_normalized_advantage_teacher_end_ordinals": 21,
    }
    for name, expected in expected_counts.items():
        if len(memberships[name]) != expected:
            raise ValueError(f"probe membership count mismatch for {name}")
    clarification_sha = (
        "e6c6536440effe5f49105110a3aaff38772582dc1dc701ec4e5ba940b5e21a76"
    )
    clarification_rows = [
        row
        for row in probe_rows
        if row["raw_observation_sha256"] == clarification_sha
    ]
    if (
        len(clarification_rows) != 1
        or not clarification_rows[0]["teacher_is_end"]
        or clarification_rows[0]["sampled_is_end"]
        or clarification_rows[0]["raw_advantage"] <= 0.0
        or clarification_rows[0]["trainer_normalized_advantage_float32"] <= 0.0
    ):
        raise ValueError("teacher-END sampled-non-END clarification row mismatch")

    for target in plan["pretraining_probe_contract"]["negative_targets"]:
        ordinal = int(target["ppo_row_ordinal"])
        probe = probe_rows[ordinal]
        exact_fields = (
            "ppo_row_ordinal",
            "episode_id",
            "opponent_id",
            "seat",
            "seed",
            "decision_index",
            "legal_option_count",
            "raw_observation_sha256",
            "public_state_sha256",
            "behavior_action_order_sha256",
            "teacher_semantic_identity",
            "sampled_end_semantic_identity",
        )
        translated = dict(probe)
        translated["sampled_end_semantic_identity"] = probe[
            "sampled_semantic_identity"
        ]
        for field in exact_fields:
            if translated.get(field) != target.get(field):
                raise ValueError(f"negative target {ordinal} {field} mismatch")
        if probe["teacher_index"] != int(target["teacher_index"]):
            raise ValueError(f"negative target {ordinal} teacher index mismatch")
        if probe["end_index"] != int(target["sampled_end_index"]):
            raise ValueError(f"negative target {ordinal} END index mismatch")
        numeric_fields = {
            "raw_advantage": "raw_advantage",
            "independent_normalized_advantage_float64": (
                "independent_normalized_advantage_float64"
            ),
            "trainer_normalized_advantage_float32": (
                "trainer_normalized_advantage_float32"
            ),
            "stored_behavior_end_probability_float64": (
                "stored_behavior_end_probability_float64"
            ),
            "trainer_model_pre_update_end_probability_float32": (
                "pre_update_end_probability_float32"
            ),
        }
        for target_name, probe_name in numeric_fields.items():
            tolerance = 1e-12 if "float32" not in target_name else 1e-7
            _assert_close(
                float(probe[probe_name]),
                float(target[target_name]),
                tolerance,
                f"negative target {ordinal} {target_name}",
            )

    if any(
        not torch.equal(value, model.state_dict()[name])
        for name, value in before_parameters.items()
    ):
        raise ValueError("prepare mode changed model parameters")
    snapshot = implementation_snapshot()
    core = {
        "schema_version": PREPARE_RECEIPT_SCHEMA_VERSION,
        "plan": copy.deepcopy(loaded["plan_provenance"]),
        "source_implementation_input": loaded["immutable_file_receipt"],
        "implementation": {
            "path": IMPLEMENTATION_RELATIVE_PATH.as_posix(),
            **snapshot,
        },
        "runtime_thread_receipt": dict(runtime),
        "input_checkpoint": {
            "path": INPUT_CHECKPOINT_RELATIVE_PATH.as_posix(),
            "sha256": INPUT_CHECKPOINT_SHA256,
            "optimizer_state_is_none": True,
        },
        "manifest": {
            "path": MANIFEST_RELATIVE_PATH.as_posix(),
            "sha256": MANIFEST_SHA256,
            "dataset_sha256": DATASET_SHA256,
            "runtime_receipt": copy.deepcopy(
                loaded["dataset"].manifest["runtime_receipt"]
            ),
            "runtime_receipt_sha256": loaded["dataset"].manifest[
                "runtime_receipt_sha256"
            ],
            "behavior_policy_schema_sha256": BEHAVIOR_POLICY_SCHEMA_SHA256,
        },
        "training_contract": {
            "ppo_config": asdict(PILOT_PPO_CONFIG),
            "adam": copy.deepcopy(PILOT_ADAM_CONFIG),
            "row_order": "manifest order",
            "shuffle": False,
            "minibatches": False,
            "epochs": 1,
            "optimizer_steps": 1,
            "device": "cpu",
        },
        "advantage_domains": {
            "independent_float64": {
                "mean": independent_mean,
                "population_sd": independent_sd,
            },
            "trainer_float32": {
                "mean": float(trainer_mean_tensor),
                "population_sd": float(trainer_sd_tensor),
            },
        },
        "row_count": len(probe_rows),
        "unique_decision_key_count": len(
            {(row["episode_id"], row["decision_index"]) for row in probe_rows}
        ),
        "ordered_row_identities_sha256": canonical_sha256(
            [
                {
                    "ordinal": row["ppo_row_ordinal"],
                    "episode_id": row["episode_id"],
                    "decision_index": row["decision_index"],
                    "raw_observation_sha256": row["raw_observation_sha256"],
                    "public_state_sha256": row["public_state_sha256"],
                    "behavior_action_order_sha256": row[
                        "behavior_action_order_sha256"
                    ],
                }
                for row in probe_rows
            ]
        ),
        "probe_memberships": memberships,
        "protected_action_validation": "pass",
        "checkpoint_provenance_validation": "pass",
        "rows": probe_rows,
    }
    return {**core, "receipt_sha256": canonical_sha256(core)}


def validate_prepare_receipt(receipt: Mapping[str, Any]) -> None:
    row = dict(receipt)
    receipt_hash = _strict_sha256(
        row.pop("receipt_sha256", None), label="prepare receipt self-hash"
    )
    if row.get("schema_version") != PREPARE_RECEIPT_SCHEMA_VERSION:
        raise ValueError("prepare receipt schema mismatch")
    if canonical_sha256(row) != receipt_hash:
        raise ValueError("prepare receipt self-hash mismatch")
    if row.get("row_count") != EXPECTED_ON_POLICY_ROWS:
        raise ValueError("prepare receipt row count mismatch")
    rows = row.get("rows")
    if not isinstance(rows, list) or len(rows) != EXPECTED_ON_POLICY_ROWS:
        raise ValueError("prepare receipt ordered rows are missing")
    keys = [(item.get("episode_id"), item.get("decision_index")) for item in rows]
    if len(set(keys)) != EXPECTED_ON_POLICY_ROWS:
        raise ValueError("prepare receipt contains duplicate decision keys")
    if [item.get("ppo_row_ordinal") for item in rows] != list(
        range(EXPECTED_ON_POLICY_ROWS)
    ):
        raise ValueError("prepare receipt row order mismatch")


def _write_new_canonical_json(
    path: Path,
    value: Mapping[str, Any],
    *,
    directory_guard: _StableDirectoryGuard | None = None,
) -> str:
    payload = canonical_json_bytes(value, newline=True)
    guard, owned_guard = _with_directory_guard(path, directory_guard)
    artifact: _StableFileGuard | None = None
    try:
        artifact = _create_new_file_guarded(path, payload, guard)
        readback = _win_read_all(artifact.handle)
        expected = hashlib.sha256(payload).hexdigest().upper()
        actual = hashlib.sha256(readback).hexdigest().upper()
        if readback != payload or actual != expected:
            raise ValueError("new canonical JSON hash mismatch")
        return actual
    except Exception:
        if artifact is not None:
            artifact.delete_on_close()
        raise
    finally:
        if artifact is not None:
            artifact.close()
        if owned_guard:
            guard.close()


def _absolute_prepare_output_candidate(output_receipt: Path) -> Path:
    raw_parts = output_receipt.parts
    if ".." in raw_parts or "." in raw_parts:
        raise ValueError("prepare receipt path must not contain aliases")
    candidate = (
        output_receipt
        if output_receipt.is_absolute()
        else Path.cwd() / output_receipt
    )
    return candidate.absolute()


def _validate_prepare_output_path(
    output_receipt: Path,
    *,
    must_exist: bool = False,
    directory_guard: _StableDirectoryGuard | None = None,
) -> Path:
    candidate = _absolute_prepare_output_candidate(output_receipt)
    if directory_guard is not None:
        if candidate.parent != directory_guard.path:
            raise ValueError("prepare receipt parent differs from guarded directory")
        directory_guard.ensure_current()
    implementation_root = _repo_path(IMPLEMENTATION_RELATIVE_PATH).resolve(strict=True)
    approved_root = implementation_root / "test_outputs"
    try:
        lexical_relative = candidate.relative_to(implementation_root)
    except ValueError as error:
        raise ValueError(
            "prepare receipt must be inside the isolated test_outputs subtree"
        ) from error
    cursor = implementation_root
    for part in lexical_relative.parts:
        cursor = cursor / part
        if cursor.exists() or cursor.is_symlink():
            if _is_link_or_reparse(cursor):
                raise ValueError(
                    "prepare receipt path traverses a symlink or reparse point"
                )
        else:
            break
    candidate_resolved = candidate.resolve(strict=False)
    try:
        relative = candidate_resolved.relative_to(approved_root)
    except ValueError as error:
        raise ValueError(
            "prepare receipt must be inside the isolated test_outputs subtree"
        ) from error
    if (
        len(relative.parts) < 2
        or not (
            relative.parts[0] == PREPARE_OUTPUT_DIRECTORY_PREFIX
            or relative.parts[0].startswith(PREPARE_OUTPUT_DIRECTORY_PREFIX + "_")
        )
        or relative.name != PREPARE_OUTPUT_FILENAME
    ):
        raise ValueError("prepare receipt path is outside the approved prepare subtree")
    if must_exist:
        if (
            not candidate_resolved.is_file()
            or candidate_resolved.is_symlink()
            or _is_link_or_reparse(candidate_resolved)
        ):
            raise ValueError("prepare receipt must be an existing regular non-link file")
    elif candidate_resolved.exists() or candidate_resolved.is_symlink():
        raise FileExistsError("prepare receipt already exists")
    elif (
        not candidate_resolved.parent.is_dir()
        or _is_link_or_reparse(candidate_resolved.parent)
    ):
        raise ValueError(
            "prepare receipt requires an existing regular non-reparse parent"
        )
    return candidate_resolved


def prepare(*, output_receipt: Path) -> dict[str, Any]:
    """Validate and write the deterministic probe without any optimizer/checkpoint."""

    output_candidate = _absolute_prepare_output_candidate(output_receipt)
    directory_guard = _StableDirectoryGuard(output_candidate.parent)
    directory_guard.__enter__()
    try:
        output_receipt = _validate_prepare_output_path(
            output_candidate, directory_guard=directory_guard
        )
        runtime = _runtime_identity()
        receipt = _build_probe_receipt(runtime)
        validate_prepare_receipt(receipt)
        file_hash = _write_new_canonical_json(
            output_receipt, receipt, directory_guard=directory_guard
        )
        return {
            "mode": "prepare",
            "receipt_path": str(output_receipt.absolute()),
            "receipt_file_sha256": file_hash,
            "receipt_sha256": receipt["receipt_sha256"],
            "row_count": receipt["row_count"],
            "optimizer_constructed": False,
            "checkpoint_written": False,
        }
    finally:
        directory_guard.close()


def evaluate_post_update_gates(
    probe: Mapping[str, Any],
    row_metrics: Sequence[Mapping[str, Any]],
    *,
    optimizer_steps: int,
    nonfinite_count: int,
    stopped_early: bool = False,
    rolled_back: bool = False,
    checkpoint_provenance_validation: str = "pass",
) -> dict[str, Any]:
    """Evaluate every plan gate using already measured float32 row metrics."""

    rows = list(probe["rows"])
    metrics = [dict(item) for item in row_metrics]
    failures: list[str] = []
    if len(rows) != EXPECTED_ON_POLICY_ROWS or len(metrics) != len(rows):
        failures.append("global:row_count")
        return {"accepted": False, "failures": failures}
    for ordinal, metric in enumerate(metrics):
        if metric.get("ppo_row_ordinal") != ordinal:
            failures.append(f"row:{ordinal}:order")
            continue
        probabilities = metric.get("post_update_probabilities_float32") or ()
        if len(probabilities) != rows[ordinal]["legal_option_count"]:
            failures.append(f"row:{ordinal}:probability_dimension")
            continue
        try:
            _unique_argmax(probabilities)
        except ValueError:
            failures.append(f"row:{ordinal}:unique_argmax")
        for name in ("anchor_kl_post_to_zero", "total_variation_post_to_pre"):
            value = metric.get(name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                failures.append(f"row:{ordinal}:{name}_nonfinite")
    memberships = probe["probe_memberships"]
    for ordinal in memberships["negative_target_ordinals"]:
        pre = rows[ordinal]
        post = metrics[ordinal]
        probabilities = post.get("post_update_probabilities_float32") or ()
        if len(probabilities) != pre["legal_option_count"]:
            continue
        end_index = pre["end_index"]
        teacher_index = pre["teacher_index"]
        if pre["pre_update_probabilities_float32"][end_index] - float(
            probabilities[end_index]
        ) < 1e-6:
            failures.append(f"negative:{ordinal}:end_decrease")
        if float(probabilities[teacher_index]) - pre[
            "pre_update_probabilities_float32"
        ][teacher_index] < 1e-6:
            failures.append(f"negative:{ordinal}:teacher_increase")
        try:
            _unique_argmax(probabilities, teacher_index)
        except ValueError:
            failures.append(f"negative:{ordinal}:teacher_unique_argmax")
        if (
            post.get("public_state_sha256") != pre["public_state_sha256"]
            or post.get("behavior_action_order_sha256")
            != pre["behavior_action_order_sha256"]
        ):
            failures.append(f"negative:{ordinal}:identity_or_action_order")
    for ordinal in memberships["teacher_end_ordinals"]:
        probabilities = metrics[ordinal].get(
            "post_update_probabilities_float32"
        ) or ()
        try:
            _unique_argmax(probabilities, rows[ordinal]["end_index"])
        except ValueError:
            failures.append(f"legitimate_end:{ordinal}:unique_argmax")
    for ordinal in memberships[
        "positive_normalized_advantage_sampled_end_ordinals"
    ]:
        end_index = rows[ordinal]["end_index"]
        delta = float(metrics[ordinal]["post_update_probabilities_float32"][end_index]) - rows[
            ordinal
        ]["pre_update_probabilities_float32"][end_index]
        if delta < 1e-6:
            failures.append(f"legitimate_end:{ordinal}:normalized_increase")
    positive_raw_deltas = []
    for ordinal in memberships["positive_raw_advantage_sampled_end_ordinals"]:
        end_index = rows[ordinal]["end_index"]
        positive_raw_deltas.append(
            float(metrics[ordinal]["post_update_probabilities_float32"][end_index])
            - rows[ordinal]["pre_update_probabilities_float32"][end_index]
        )
    median_delta = statistics.median(positive_raw_deltas)
    maximum_decrease = max(max(0.0, -value) for value in positive_raw_deltas)
    if median_delta < 0.0:
        failures.append("legitimate_end:positive_raw_median")
    if maximum_decrease > 0.0025:
        failures.append("legitimate_end:positive_raw_maximum_decrease")
    finite_kls = [
        float(item["anchor_kl_post_to_zero"])
        for item in metrics
        if isinstance(item.get("anchor_kl_post_to_zero"), (int, float))
        and not isinstance(item.get("anchor_kl_post_to_zero"), bool)
        and math.isfinite(float(item["anchor_kl_post_to_zero"]))
    ]
    mean_kl = (
        math.fsum(finite_kls) / len(finite_kls)
        if len(finite_kls) == len(metrics)
        else math.inf
    )
    max_kl = max(finite_kls) if finite_kls else math.inf
    finite_tvs = [
        float(item["total_variation_post_to_pre"])
        for item in metrics
        if isinstance(item.get("total_variation_post_to_pre"), (int, float))
        and not isinstance(item.get("total_variation_post_to_pre"), bool)
        and math.isfinite(float(item["total_variation_post_to_pre"]))
    ]
    max_tv = max(finite_tvs) if len(finite_tvs) == len(metrics) else math.inf
    if mean_kl > 0.002:
        failures.append("global:mean_anchor_kl")
    if max_kl > 0.01:
        failures.append("global:per_row_anchor_kl")
    if max_tv > 0.02:
        failures.append("global:per_row_total_variation")
    if nonfinite_count != 0:
        failures.append("global:nonfinite")
    if optimizer_steps != 1:
        failures.append("global:optimizer_steps")
    if stopped_early:
        failures.append("global:stopped_early")
    if rolled_back:
        failures.append("global:rolled_back")
    if probe.get("protected_action_validation") != "pass":
        failures.append("global:protected_action_validation")
    if checkpoint_provenance_validation != "pass":
        failures.append("global:checkpoint_provenance_validation")
    return {
        "accepted": not failures,
        "failures": failures,
        "negative_target_count": len(memberships["negative_target_ordinals"]),
        "teacher_end_count": len(memberships["teacher_end_ordinals"]),
        "teacher_end_and_sampled_end_count": len(
            memberships["teacher_end_and_sampled_end_ordinals"]
        ),
        "positive_raw_sampled_end_count": len(
            memberships["positive_raw_advantage_sampled_end_ordinals"]
        ),
        "positive_normalized_sampled_end_count": len(
            memberships["positive_normalized_advantage_sampled_end_ordinals"]
        ),
        "positive_raw_sampled_end_median_delta": median_delta,
        "positive_raw_sampled_end_maximum_decrease": maximum_decrease,
        "mean_anchor_kl": mean_kl,
        "maximum_anchor_kl": max_kl,
        "maximum_total_variation": max_tv,
        "optimizer_steps": optimizer_steps,
        "nonfinite_count": nonfinite_count,
        "stopped_early": stopped_early,
        "rolled_back": rolled_back,
        "checkpoint_provenance_validation": checkpoint_provenance_validation,
    }


def _load_execution_spec(
    path: Path, expected_file_sha256: str
) -> dict[str, Any]:
    spec = _load_hashed_json(
        path, expected_file_sha256, label="execution spec"
    )
    required = {
        "schema_version",
        "plan_path",
        "plan_sha256",
        "prepare_receipt_path",
        "prepare_receipt_file_sha256",
        "prepare_receipt_sha256",
        "implementation_snapshot_sha256",
        "input_checkpoint_path",
        "input_checkpoint_sha256",
        "manifest_path",
        "manifest_sha256",
        "dataset_sha256",
        "runtime_thread_receipt",
        "training_contract",
        "output_directory",
    }
    if not isinstance(spec, dict) or set(spec) != required:
        raise ValueError("execution spec schema mismatch")
    if spec["schema_version"] != EXECUTION_SPEC_SCHEMA_VERSION:
        raise ValueError("execution spec version mismatch")
    expected_scalars = {
        "plan_path": PLAN_RELATIVE_PATH.as_posix(),
        "plan_sha256": PLAN_SHA256,
        "input_checkpoint_path": INPUT_CHECKPOINT_RELATIVE_PATH.as_posix(),
        "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
        "manifest_path": MANIFEST_RELATIVE_PATH.as_posix(),
        "manifest_sha256": MANIFEST_SHA256,
        "dataset_sha256": DATASET_SHA256,
    }
    for name, expected in expected_scalars.items():
        if spec.get(name) != expected:
            raise ValueError(f"execution spec {name} mismatch")
    return spec


def _resolve_pinned_path(value: Any, *, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(value)
    return path if path.is_absolute() else find_repo_root() / path


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return bool(
        attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _require_windows_publication_primitives() -> None:
    if os.name != "nt":
        raise RuntimeError(
            "race-safe publication requires Windows handle-based confinement"
        )


def _normalized_windows_path(value: str | Path) -> str:
    text = str(value)
    if text.startswith("\\\\?\\UNC\\"):
        text = "\\\\" + text[8:]
    elif text.startswith("\\\\?\\"):
        text = text[4:]
    return os.path.normcase(os.path.normpath(text))


def _win_error() -> OSError:
    return ctypes.WinError(ctypes.get_last_error())


def _win_ntstatus_error(status: int, *, path: Path) -> OSError:
    error = int(_ntdll.RtlNtStatusToDosError(status))
    if error in (80, 183):
        return FileExistsError(error, "directory already exists", str(path))
    return ctypes.WinError(error)


def _win_close_handle(handle: int | None) -> None:
    if handle is not None and handle != _INVALID_HANDLE_VALUE:
        if not _kernel32.CloseHandle(handle):
            raise _win_error()


def _win_open_handle(
    path: Path,
    *,
    desired_access: int,
    share_mode: int,
    creation_disposition: int,
    flags: int,
) -> int:
    _require_windows_publication_primitives()
    handle = _kernel32.CreateFileW(
        str(path),
        desired_access,
        share_mode,
        None,
        creation_disposition,
        flags,
        None,
    )
    if handle == _INVALID_HANDLE_VALUE:
        raise _win_error()
    return int(handle)


def _win_create_directory_relative(parent_handle: int, path: Path) -> int:
    """Atomically create a directory and return the creating kernel handle."""

    _require_windows_publication_primitives()
    path = path.absolute()
    leaf = path.name
    if not leaf or leaf in (".", "..") or any(mark in leaf for mark in ("/", "\\")):
        raise ValueError("new directory must have one canonical leaf name")
    name_buffer = ctypes.create_unicode_buffer(leaf)
    name = _UnicodeString(
        len(leaf.encode("utf-16-le")),
        len(leaf.encode("utf-16-le")) + 2,
        ctypes.cast(name_buffer, wintypes.LPWSTR),
    )
    attributes = _ObjectAttributes(
        ctypes.sizeof(_ObjectAttributes),
        wintypes.HANDLE(parent_handle),
        ctypes.pointer(name),
        _OBJ_CASE_INSENSITIVE,
        None,
        None,
    )
    io_status = _IoStatusBlock()
    created = wintypes.HANDLE()
    status = int(
        _ntdll.NtCreateFile(
            ctypes.byref(created),
            _FILE_READ_ATTRIBUTES | _DELETE | _SYNCHRONIZE,
            ctypes.byref(attributes),
            ctypes.byref(io_status),
            None,
            _FILE_ATTRIBUTE_DIRECTORY,
            _FILE_SHARE_READ | _FILE_SHARE_WRITE,
            _FILE_CREATE,
            (
                _FILE_DIRECTORY_FILE
                | _FILE_SYNCHRONOUS_IO_NONALERT
                | _FILE_OPEN_REPARSE_POINT
            ),
            None,
            0,
        )
    )
    if status < 0:
        raise _win_ntstatus_error(status, path=path)
    if not created.value or created.value == _INVALID_HANDLE_VALUE:
        raise OSError("NtCreateFile returned an invalid directory handle")
    return int(created.value)


def _win_handle_information(handle: int) -> tuple[int, tuple[int, int], str]:
    information = _ByHandleFileInformation()
    if not _kernel32.GetFileInformationByHandle(
        handle, ctypes.byref(information)
    ):
        raise _win_error()
    size = _kernel32.GetFinalPathNameByHandleW(handle, None, 0, 0)
    if size == 0:
        raise _win_error()
    buffer = ctypes.create_unicode_buffer(size + 1)
    written = _kernel32.GetFinalPathNameByHandleW(
        handle, buffer, len(buffer), 0
    )
    if written == 0 or written >= len(buffer):
        raise _win_error()
    identity = (
        int(information.volume_serial_number),
        (int(information.file_index_high) << 32)
        | int(information.file_index_low),
    )
    return (
        int(information.file_attributes),
        identity,
        _normalized_windows_path(buffer.value),
    )


def _win_write_all(handle: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        chunk = payload[offset : offset + 1024 * 1024]
        buffer = ctypes.create_string_buffer(chunk)
        written = wintypes.DWORD()
        if not _kernel32.WriteFile(
            handle,
            buffer,
            len(chunk),
            ctypes.byref(written),
            None,
        ):
            raise _win_error()
        if written.value != len(chunk):
            raise OSError("short checkpoint/artifact write")
        offset += written.value
    if not _kernel32.FlushFileBuffers(handle):
        raise _win_error()


def _win_read_all(handle: int) -> bytes:
    size = ctypes.c_longlong()
    if not _kernel32.GetFileSizeEx(handle, ctypes.byref(size)):
        raise _win_error()
    if not _kernel32.SetFilePointerEx(handle, 0, None, 0):
        raise _win_error()
    output = bytearray()
    remaining = int(size.value)
    while remaining:
        requested = min(remaining, 1024 * 1024)
        buffer = ctypes.create_string_buffer(requested)
        read = wintypes.DWORD()
        if not _kernel32.ReadFile(
            handle,
            buffer,
            requested,
            ctypes.byref(read),
            None,
        ):
            raise _win_error()
        if read.value == 0:
            raise OSError("short checkpoint/artifact readback")
        output.extend(buffer.raw[: read.value])
        remaining -= read.value
    return bytes(output)


def _win_delete_on_close(handle: int) -> None:
    disposition = _FileDispositionInformation(True)
    if not _kernel32.SetFileInformationByHandle(
        handle,
        _FILE_DISPOSITION_INFO_CLASS,
        ctypes.byref(disposition),
        ctypes.sizeof(disposition),
    ):
        raise _win_error()


class _StableDirectoryGuard:
    """Pin a non-reparse directory chain and deny rename/delete while held."""

    def __init__(self, path: Path):
        self.path = path.absolute()
        self._entries: list[tuple[Path, int, tuple[int, int], str]] = []
        self._held_only_paths: set[Path] = set()

    def __enter__(self) -> "_StableDirectoryGuard":
        _require_windows_publication_primitives()
        if not self.path.is_dir() or _is_link_or_reparse(self.path):
            raise ValueError(
                "publication parent must be an existing regular non-reparse directory"
            )
        anchor = Path(self.path.anchor)
        try:
            relative = self.path.relative_to(anchor)
        except ValueError as error:
            raise ValueError("publication parent must have an absolute anchor") from error
        chain = [anchor]
        cursor = anchor
        for part in relative.parts:
            cursor = cursor / part
            chain.append(cursor)
        try:
            for component in chain:
                if _is_link_or_reparse(component):
                    raise ValueError(
                        "publication path traverses a symlink or reparse point"
                    )
                handle = _win_open_handle(
                    component,
                    desired_access=(
                        _FILE_READ_ATTRIBUTES
                        | (_DELETE if component == self.path else 0)
                    ),
                    share_mode=_FILE_SHARE_READ | _FILE_SHARE_WRITE,
                    creation_disposition=_OPEN_EXISTING,
                    flags=(
                        _FILE_FLAG_BACKUP_SEMANTICS
                        | _FILE_FLAG_OPEN_REPARSE_POINT
                    ),
                )
                try:
                    attributes, identity, final_path = _win_handle_information(handle)
                    if not attributes & _FILE_ATTRIBUTE_DIRECTORY:
                        raise ValueError("publication path component is not a directory")
                    if attributes & _FILE_ATTRIBUTE_REPARSE_POINT:
                        raise ValueError(
                            "publication path traverses a symlink or reparse point"
                        )
                    if final_path != _normalized_windows_path(component.absolute()):
                        raise ValueError("publication path component aliases another path")
                    self._entries.append((component, handle, identity, final_path))
                except Exception:
                    _win_close_handle(handle)
                    raise
            self.ensure_current()
            return self
        except Exception:
            self.close()
            raise

    def ensure_current(self) -> None:
        if not self._entries:
            raise RuntimeError("publication directory guard is not active")
        for component, held, expected_identity, expected_final in self._entries:
            held_attributes, held_identity, held_final = _win_handle_information(held)
            if (
                not held_attributes & _FILE_ATTRIBUTE_DIRECTORY
                or held_attributes & _FILE_ATTRIBUTE_REPARSE_POINT
                or held_identity != expected_identity
                or held_final != expected_final
            ):
                raise ValueError("held publication directory identity changed")
            if component in self._held_only_paths:
                continue
            if _is_link_or_reparse(component):
                raise ValueError("publication directory identity changed")
            current = _win_open_handle(
                component,
                desired_access=_FILE_READ_ATTRIBUTES,
                share_mode=_FILE_SHARE_READ | _FILE_SHARE_WRITE,
                creation_disposition=_OPEN_EXISTING,
                flags=(
                    _FILE_FLAG_BACKUP_SEMANTICS
                    | _FILE_FLAG_OPEN_REPARSE_POINT
                ),
            )
            try:
                attributes, identity, final_path = _win_handle_information(current)
                if (
                    not attributes & _FILE_ATTRIBUTE_DIRECTORY
                    or attributes & _FILE_ATTRIBUTE_REPARSE_POINT
                    or identity != expected_identity
                    or final_path != expected_final
                ):
                    raise ValueError("publication directory identity changed")
            finally:
                _win_close_handle(current)

    @property
    def leaf_handle(self) -> int:
        if not self._entries:
            raise RuntimeError("publication directory guard is not active")
        return self._entries[-1][1]

    def adopt_created_child(self, path: Path, handle: int) -> None:
        """Extend this parent guard with an already-created, already-held child."""

        path = path.absolute()
        if path.parent != self.path:
            raise ValueError("created directory parent differs from guarded directory")
        self.ensure_current()
        attributes, identity, final_path = _win_handle_information(handle)
        if (
            not attributes & _FILE_ATTRIBUTE_DIRECTORY
            or attributes & _FILE_ATTRIBUTE_REPARSE_POINT
            or final_path != _normalized_windows_path(path)
        ):
            raise ValueError("atomically created directory has invalid identity")
        self._entries.append((path, handle, identity, final_path))
        self._held_only_paths.add(path)
        self.path = path

    def close(self) -> None:
        first_error: Exception | None = None
        for _path, handle, _identity, _final in reversed(self._entries):
            try:
                _win_close_handle(handle)
            except Exception as error:  # pragma: no cover - OS close failure
                if first_error is None:
                    first_error = error
        self._entries.clear()
        self._held_only_paths.clear()
        if first_error is not None:
            raise first_error

    def __exit__(self, _kind: Any, _error: Any, _traceback: Any) -> None:
        self.close()


class _StableFileGuard:
    """Hold one exact regular file name against write/delete substitution."""

    def __init__(self, path: Path, handle: int, identity: tuple[int, int]):
        self.path = path.absolute()
        self.handle: int | None = handle
        self.identity = identity
        self._delete = False

    def ensure_bound_to(self, directory_guard: _StableDirectoryGuard) -> None:
        if self.handle is None:
            raise RuntimeError("publication file guard is closed")
        directory_guard.ensure_current()
        if self.path.parent.absolute() != directory_guard.path:
            raise ValueError("artifact parent differs from guarded directory")
        attributes, identity, final_path = _win_handle_information(self.handle)
        if (
            attributes & (_FILE_ATTRIBUTE_DIRECTORY | _FILE_ATTRIBUTE_REPARSE_POINT)
            or identity != self.identity
            or final_path != _normalized_windows_path(self.path)
        ):
            raise ValueError("artifact handle is outside the guarded parent")

    def delete_on_close(self) -> None:
        if self.handle is None:
            return
        _win_delete_on_close(self.handle)
        self._delete = True

    def close(self) -> None:
        handle, self.handle = self.handle, None
        if handle is not None:
            _win_close_handle(handle)


def _create_new_file_guarded(
    path: Path, payload: bytes, directory_guard: _StableDirectoryGuard
) -> _StableFileGuard:
    path = path.absolute()
    if path.parent != directory_guard.path:
        raise ValueError("artifact parent differs from guarded directory")
    directory_guard.ensure_current()
    handle = _win_open_handle(
        path,
        desired_access=_GENERIC_READ | _GENERIC_WRITE | _DELETE,
        share_mode=_FILE_SHARE_READ,
        creation_disposition=_CREATE_NEW,
        flags=(
            _FILE_ATTRIBUTE_NORMAL
            | _FILE_FLAG_OPEN_REPARSE_POINT
            | _FILE_FLAG_WRITE_THROUGH
        ),
    )
    artifact: _StableFileGuard | None = None
    try:
        attributes, identity, final_path = _win_handle_information(handle)
        if (
            attributes & (_FILE_ATTRIBUTE_DIRECTORY | _FILE_ATTRIBUTE_REPARSE_POINT)
            or final_path != _normalized_windows_path(path)
        ):
            raise ValueError("new artifact is outside the guarded parent")
        artifact = _StableFileGuard(path, handle, identity)
        _win_write_all(handle, payload)
        artifact.ensure_bound_to(directory_guard)
        return artifact
    except Exception:
        try:
            if artifact is not None:
                artifact.delete_on_close()
                artifact.close()
            else:
                _win_delete_on_close(handle)
                _win_close_handle(handle)
        except Exception:
            pass
        raise


def _verify_existing_file_identity(
    path: Path,
    directory_guard: _StableDirectoryGuard,
    *,
    expected_identity: tuple[int, int],
) -> None:
    """Bind a public name to an already-held inode without weakening its lock."""

    path = path.absolute()
    if path.parent != directory_guard.path:
        raise ValueError("artifact parent differs from guarded directory")
    directory_guard.ensure_current()
    handle = _win_open_handle(
        path,
        desired_access=0,
        share_mode=(
            _FILE_SHARE_READ | _FILE_SHARE_WRITE | _FILE_SHARE_DELETE
        ),
        creation_disposition=_OPEN_EXISTING,
        flags=_FILE_ATTRIBUTE_NORMAL | _FILE_FLAG_OPEN_REPARSE_POINT,
    )
    try:
        attributes, identity, final_path = _win_handle_information(handle)
        if (
            attributes & (_FILE_ATTRIBUTE_DIRECTORY | _FILE_ATTRIBUTE_REPARSE_POINT)
            or identity != expected_identity
            or final_path != _normalized_windows_path(path)
        ):
            raise ValueError("published artifact name has the wrong identity")
    finally:
        _win_close_handle(handle)


def _with_directory_guard(
    path: Path, guard: _StableDirectoryGuard | None
) -> tuple[_StableDirectoryGuard, bool]:
    parent = path.absolute().parent
    if guard is not None:
        if parent != guard.path:
            raise ValueError("artifact parent differs from guarded directory")
        guard.ensure_current()
        return guard, False
    acquired = _StableDirectoryGuard(parent)
    acquired.__enter__()
    return acquired, True


def _paths_overlap(left: Path, right: Path) -> bool:
    left_resolved = left.resolve(strict=False)
    right_resolved = right.resolve(strict=False)
    return bool(
        left_resolved == right_resolved
        or left_resolved in right_resolved.parents
        or right_resolved in left_resolved.parents
    )


def _protected_output_paths(
    *, receipt_path: Path, execution_spec: Path
) -> tuple[Path, ...]:
    repo = find_repo_root().resolve(strict=True)
    manifest_path = _repo_path(MANIFEST_RELATIVE_PATH)
    manifest = _load_hashed_json(
        manifest_path,
        MANIFEST_SHA256,
        label="input manifest path authorization",
    )
    opponent_roots = tuple(
        repo / Path(str(row["path"]))
        for row in manifest.get("opponent_table") or ()
    )
    return (
        repo / "experiments",
        _repo_path(PLAN_RELATIVE_PATH),
        _repo_path(CORRECTION_RELATIVE_PATH),
        _repo_path(PLAN_RELATIVE_PATH).parent,
        repo / Path(
            "experiments/archaludon_latest_v1_rl_temperature_candidate_20260731"
        ),
        _repo_path(IMPLEMENTATION_RELATIVE_PATH),
        manifest_path,
        manifest_path.parent,
        _repo_path(INPUT_CHECKPOINT_RELATIVE_PATH),
        _repo_path(INPUT_CHECKPOINT_RELATIVE_PATH).parent,
        receipt_path,
        execution_spec,
        latest_source_dir(repo),
        seeded_engine_dir(repo),
        *opponent_roots,
    )


def _validate_output_directory(
    value: Any,
    *,
    repo_root: Path | None = None,
    approved_relative: PurePosixPath = APPROVED_OUTPUT_RELATIVE_PATH,
    protected_paths: Sequence[Path] | None = None,
) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("output directory must be a nonempty canonical path")
    if "\\" in value or ":" in value:
        raise ValueError("output directory must be a canonical repo-relative POSIX path")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or pure.as_posix() != value
        or any(part in ("", ".", "..") for part in pure.parts)
        or not (
            pure == approved_relative
            or approved_relative in pure.parents
        )
        or not approved_relative.parts
        or approved_relative.parts[0] != "analysis_outputs"
    ):
        raise ValueError("output directory is outside the approved analysis_outputs subtree")
    repo = (
        find_repo_root().resolve(strict=True)
        if repo_root is None
        else repo_root.resolve(strict=True)
    )
    candidate = repo.joinpath(*pure.parts)
    approved = repo.joinpath(*approved_relative.parts)
    candidate_resolved = candidate.resolve(strict=False)
    approved_resolved = approved.resolve(strict=False)
    if not (
        candidate_resolved == approved_resolved
        or approved_resolved in candidate_resolved.parents
    ):
        raise ValueError("output directory aliases outside the approved subtree")
    relative = candidate.relative_to(repo)
    cursor = repo
    for part in relative.parts:
        cursor = cursor / part
        if cursor.exists() or cursor.is_symlink():
            if _is_link_or_reparse(cursor):
                raise ValueError("output directory traverses a symlink or reparse point")
        else:
            break
    if candidate.exists() or candidate.is_symlink():
        raise FileExistsError("execution requires a new absent output directory")
    if (
        not candidate.parent.is_dir()
        or candidate.parent.is_symlink()
        or _is_link_or_reparse(candidate.parent)
    ):
        raise ValueError(
            "output directory requires an existing regular non-link parent"
        )
    for protected in protected_paths or ():
        if _paths_overlap(candidate, Path(protected)):
            raise ValueError("output directory overlaps an immutable input or source tree")
    return candidate_resolved


def _create_and_guard_output_directory(path: Path) -> _StableDirectoryGuard:
    """Atomically create and pin a directory under an already-pinned parent."""

    path = path.absolute()
    parent_guard = _StableDirectoryGuard(path.parent)
    parent_guard.__enter__()
    child_handle: int | None = None
    try:
        parent_guard.ensure_current()
        child_handle = _win_create_directory_relative(
            parent_guard.leaf_handle, path
        )
        try:
            attributes, _identity, final_path = _win_handle_information(child_handle)
            if (
                not attributes & _FILE_ATTRIBUTE_DIRECTORY
                or attributes & _FILE_ATTRIBUTE_REPARSE_POINT
                or final_path != _normalized_windows_path(path)
            ):
                raise ValueError("atomically created output directory is invalid")
            parent_guard.adopt_created_child(path, child_handle)
            child_handle = None
            return parent_guard
        except Exception:
            if child_handle is not None:
                try:
                    _win_delete_on_close(child_handle)
                finally:
                    _win_close_handle(child_handle)
                    child_handle = None
            raise
    except Exception:
        parent_guard.close()
        raise


def _validate_execution_boundary(
    spec: Mapping[str, Any], runtime: Mapping[str, Any], *, execution_spec_path: Path
) -> tuple[dict[str, Any], Path]:
    receipt_path = _resolve_pinned_path(
        spec["prepare_receipt_path"], label="prepare receipt path"
    )
    receipt_path = _validate_prepare_output_path(receipt_path, must_exist=True)
    expected_file_hash = _strict_sha256(
        spec["prepare_receipt_file_sha256"],
        label="prepare receipt file hash",
    )
    receipt = _load_hashed_json(
        receipt_path, expected_file_hash, label="pinned prepare receipt"
    )
    validate_prepare_receipt(receipt)
    if receipt["receipt_sha256"] != spec["prepare_receipt_sha256"]:
        raise ValueError("pinned prepare receipt self-hash mismatch")
    if receipt["implementation"]["sha256"] != spec[
        "implementation_snapshot_sha256"
    ]:
        raise ValueError("execution spec/prepare implementation mismatch")
    current_snapshot = implementation_snapshot()
    if current_snapshot != {
        key: receipt["implementation"][key]
        for key in ("definition", "file_count", "sha256", "files")
    }:
        raise ValueError("implementation changed after probe preparation")
    if dict(runtime) != dict(spec["runtime_thread_receipt"]):
        raise ValueError("execution runtime differs from pinned runtime")
    if dict(runtime) != dict(receipt["runtime_thread_receipt"]):
        raise ValueError("execution runtime differs from prepare runtime")
    if spec["training_contract"] != receipt["training_contract"]:
        raise ValueError("execution training contract mismatch")
    rebuilt = _build_probe_receipt(runtime)
    require_exact_probe_match(receipt, rebuilt)
    output_directory = _validate_output_directory(
        spec["output_directory"],
        protected_paths=_protected_output_paths(
            receipt_path=receipt_path,
            execution_spec=execution_spec_path,
        ),
    )
    return receipt, output_directory


def _new_adam(model: Any) -> torch.optim.Adam:
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=PILOT_PPO_CONFIG.learning_rate,
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
        raise ValueError("fresh Adam unexpectedly has nonempty state")
    return optimizer


def _finite_tensors_or_raise(
    values: Iterable[torch.Tensor], *, label: str
) -> None:
    for value in values:
        if not torch.isfinite(value).all():
            raise ValueError(f"non-finite {label}")


def _audit_optimizer_after_one_step(optimizer: torch.optim.Adam) -> None:
    state = optimizer.state_dict()["state"]
    if not state:
        raise ValueError("Adam has no state after its required step")
    for parameter_state in state.values():
        step = parameter_state.get("step")
        step_value = float(step.detach().cpu()) if torch.is_tensor(step) else float(step)
        if step_value != 1.0:
            raise ValueError("Adam state does not prove exactly one fresh step")
        _finite_tensors_or_raise(
            (value for value in parameter_state.values() if torch.is_tensor(value)),
            label="optimizer state",
        )


def _audit_optimizer_state_dict_after_one_step(
    optimizer_state: Mapping[str, Any]
) -> None:
    state = optimizer_state.get("state")
    groups = optimizer_state.get("param_groups")
    if not isinstance(state, dict) or not state:
        raise ValueError("serialized Adam state is empty")
    if not isinstance(groups, list) or len(groups) != 1:
        raise ValueError("serialized Adam parameter-group layout mismatch")
    group = groups[0]
    expected = {
        "lr": PILOT_PPO_CONFIG.learning_rate,
        "betas": (0.9, 0.999),
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
    for name, value in expected.items():
        if group.get(name) != value:
            raise ValueError(f"serialized Adam {name} mismatch")
    if len(group.get("params") or ()) != len(state):
        raise ValueError("serialized Adam parameter/state count mismatch")
    for parameter_state in state.values():
        if not isinstance(parameter_state, dict):
            raise ValueError("serialized Adam parameter state is invalid")
        step = parameter_state.get("step")
        step_value = float(step.detach().cpu()) if torch.is_tensor(step) else float(step)
        if step_value != 1.0:
            raise ValueError("serialized Adam does not prove one fresh step")
        _finite_tensors_or_raise(
            (value for value in parameter_state.values() if torch.is_tensor(value)),
            label="serialized optimizer state",
        )


def _nested_tensor_exact(left: Any, right: Any) -> bool:
    if torch.is_tensor(left) or torch.is_tensor(right):
        return bool(
            torch.is_tensor(left)
            and torch.is_tensor(right)
            and left.dtype == right.dtype
            and left.shape == right.shape
            and torch.equal(left.cpu(), right.cpu())
        )
    if isinstance(left, Mapping) or isinstance(right, Mapping):
        return bool(
            isinstance(left, Mapping)
            and isinstance(right, Mapping)
            and set(left) == set(right)
            and all(_nested_tensor_exact(left[key], right[key]) for key in left)
        )
    if isinstance(left, (list, tuple)) or isinstance(right, (list, tuple)):
        return bool(
            isinstance(left, (list, tuple))
            and isinstance(right, (list, tuple))
            and len(left) == len(right)
            and all(_nested_tensor_exact(a, b) for a, b in zip(left, right))
        )
    return left == right


def _validate_serialized_candidate(
    path: Path,
    *,
    claimed_sha256: str,
    expected_model: Any,
    expected_metadata: Mapping[str, Any],
    expected_optimizer_state: Mapping[str, Any],
    expected_source_hashes: Mapping[str, str],
    directory_guard: _StableDirectoryGuard | None = None,
    file_guard: _StableFileGuard | None = None,
    serialized_readback: bytes | None = None,
) -> dict[str, Any]:
    if directory_guard is not None:
        directory_guard.ensure_current()
    if file_guard is not None:
        if directory_guard is None:
            raise ValueError("serialized file guard requires a directory guard")
        file_guard.ensure_bound_to(directory_guard)
    if serialized_readback is None:
        if not path.is_file() or path.is_symlink():
            raise ValueError("serialized candidate checkpoint is missing or linked")
        actual_hash = sha256_checkpoint(path)
        reloaded_model, reloaded_metadata, reloaded_optimizer_state = load_checkpoint(
            path,
            expected_source_hashes=expected_source_hashes,
            device="cpu",
        )
    else:
        actual_hash = hashlib.sha256(serialized_readback).hexdigest().upper()
        payload = torch.load(
            io.BytesIO(serialized_readback),
            map_location="cpu",
            weights_only=False,
        )
        if not isinstance(payload, dict):
            raise ValueError("checkpoint payload must be a mapping")
        reloaded_metadata = payload.get("metadata")
        if not isinstance(reloaded_metadata, dict):
            raise ValueError("checkpoint metadata missing")
        _validate_metadata(
            reloaded_metadata,
            expected_source_hashes=expected_source_hashes,
        )
        reloaded_config = ModelConfig(**payload.get("model_config", {}))
        if reloaded_config != expected_model.config:
            raise ValueError("serialized candidate model config mismatch")
        reloaded_model = ResidualActorCritic(reloaded_config).to("cpu")
        reloaded_model.load_state_dict(payload["model_state"], strict=True)
        reloaded_optimizer_state = payload.get("optimizer_state")
    if actual_hash != claimed_sha256:
        raise ValueError("serialized candidate checkpoint hash mismatch")
    if reloaded_metadata != dict(expected_metadata):
        raise ValueError("serialized candidate metadata mismatch")
    if not _nested_tensor_exact(
        reloaded_model.state_dict(), expected_model.state_dict()
    ):
        raise ValueError("serialized candidate model state mismatch")
    _finite_tensors_or_raise(
        reloaded_model.parameters(), label="reloaded candidate parameter"
    )
    if not isinstance(reloaded_optimizer_state, dict):
        raise ValueError("serialized candidate optimizer state is missing")
    if not _nested_tensor_exact(
        reloaded_optimizer_state, expected_optimizer_state
    ):
        raise ValueError("serialized candidate optimizer state mismatch")
    _audit_optimizer_state_dict_after_one_step(reloaded_optimizer_state)
    if file_guard is not None:
        file_guard.ensure_bound_to(directory_guard)
    return {
        "status": "pass",
        "checkpoint_sha256": actual_hash,
        "metadata_exact": True,
        "model_state_exact": True,
        "optimizer_state_exact": True,
        "optimizer_step_state": 1,
        "parameters_finite": True,
    }


def _serialize_checkpoint_payload(
    model: Any,
    metadata: Mapping[str, Any],
    optimizer: torch.optim.Optimizer,
) -> bytes:
    payload = {
        "model_config": asdict(model.config),
        "model_state": model.state_dict(),
        "metadata": dict(metadata),
        "optimizer_state": optimizer.state_dict(),
    }
    serialized = io.BytesIO()
    torch.save(payload, serialized)
    return serialized.getvalue()


def _publish_checkpoint_exclusive(
    output_directory: Path,
    *,
    model: Any,
    metadata: Mapping[str, Any],
    optimizer: torch.optim.Optimizer,
    directory_guard: _StableDirectoryGuard | None = None,
) -> tuple[Path, str, _StableFileGuard, bytes]:
    """CREATE_NEW private bytes, then CREATE_NEW-link the exact held inode."""

    checkpoint_path = (output_directory / "candidate.pt").absolute()
    staging_path = (
        output_directory / f".candidate-{uuid.uuid4().hex}.staging.pt"
    ).absolute()
    guard, owned_guard = _with_directory_guard(checkpoint_path, directory_guard)
    staging: _StableFileGuard | None = None
    try:
        checkpoint_bytes = _serialize_checkpoint_payload(model, metadata, optimizer)
        staging = _create_new_file_guarded(staging_path, checkpoint_bytes, guard)
        serialized_readback = _win_read_all(staging.handle)
        staging_hash = hashlib.sha256(serialized_readback).hexdigest().upper()
        if serialized_readback != checkpoint_bytes:
            raise ValueError("staging checkpoint hash mismatch")
        staging.ensure_bound_to(guard)
        # CreateHardLinkW, used by os.link on Windows, fails if candidate.pt
        # already exists.  The held staging handle prevents source substitution.
        os.link(staging_path, checkpoint_path)
        _verify_existing_file_identity(
            checkpoint_path,
            guard,
            expected_identity=staging.identity,
        )
        published_hash = staging_hash
        # Delete only the private name when its held handle eventually closes;
        # the candidate.pt hard link remains the published checkpoint.
        staging.delete_on_close()
        protection = staging
        staging = None
        return checkpoint_path, published_hash, protection, serialized_readback
    finally:
        if staging is not None:
            staging.delete_on_close()
            staging.close()
        if owned_guard:
            guard.close()


def _one_full_batch_step(loaded: Mapping[str, Any]) -> dict[str, Any]:
    model = loaded["model"]
    rows = loaded["rows"]
    episodes = list(loaded["dataset"].episodes)
    reference_config = loaded["reference_config"]
    advantages = _gae(episodes, PILOT_PPO_CONFIG)
    raw_advantages = torch.tensor(
        [
            advantages[(str(episode["episode_id"]), int(row["decision_index"]))][0]
            for episode, row in rows
        ],
        dtype=torch.float32,
        device="cpu",
    )
    normalized = (raw_advantages - raw_advantages.mean()) / raw_advantages.std(
        unbiased=False
    )
    before_parameters = {
        name: value.detach().clone() for name, value in model.state_dict().items()
    }
    optimizer = _new_adam(model)
    optimizer.zero_grad(set_to_none=True)
    losses: list[torch.Tensor] = []
    policy_losses: list[torch.Tensor] = []
    value_losses: list[torch.Tensor] = []
    entropies: list[torch.Tensor] = []
    anchor_kls: list[torch.Tensor] = []
    for ordinal, (episode, row) in enumerate(rows):
        state = torch.tensor(row["state_vector"], dtype=torch.float32)
        actions = torch.tensor(row["action_vectors"], dtype=torch.float32)
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
        old_logprob = torch.tensor(float(row["behavior_logprob"]), dtype=torch.float32)
        ratio = torch.exp(log_probabilities[selected] - old_logprob)
        unclipped = ratio * normalized[ordinal]
        clipped = torch.clamp(
            ratio,
            1.0 - PILOT_PPO_CONFIG.clip_ratio,
            1.0 + PILOT_PPO_CONFIG.clip_ratio,
        ) * normalized[ordinal]
        policy_loss = -torch.minimum(unclipped, clipped)
        target = advantages[
            (str(episode["episode_id"]), int(row["decision_index"]))
        ][1]
        value_loss = (value - float(target)).pow(2)
        entropy = -(probabilities * log_probabilities).sum()
        loss = (
            policy_loss
            + PILOT_PPO_CONFIG.value_coef * value_loss
            - PILOT_PPO_CONFIG.entropy_coef * entropy
            + PILOT_PPO_CONFIG.anchor_kl_initial_coef * anchor_kl
        )
        _finite_tensors_or_raise(
            (residuals, value, probabilities, anchor_kl, policy_loss, value_loss, loss),
            label=f"row {ordinal} objective/value",
        )
        losses.append(loss)
        policy_losses.append(policy_loss)
        value_losses.append(value_loss)
        entropies.append(entropy)
        anchor_kls.append(anchor_kl)
    total_loss = torch.stack(losses).mean()
    _finite_tensors_or_raise((total_loss,), label="full-batch objective")
    total_loss.backward()
    gradients = [
        parameter.grad for parameter in model.parameters() if parameter.grad is not None
    ]
    if not gradients:
        raise ValueError("PPO full batch produced no gradients")
    _finite_tensors_or_raise(gradients, label="gradient")
    gradient_norm = torch.nn.utils.clip_grad_norm_(
        model.parameters(),
        PILOT_PPO_CONFIG.gradient_clip,
        error_if_nonfinite=True,
    )
    _finite_tensors_or_raise((gradient_norm,), label="gradient norm")
    _finite_tensors_or_raise(gradients, label="clipped gradient")
    optimizer_steps = 0
    optimizer.step()
    optimizer_steps += 1
    if optimizer_steps != 1:
        raise ValueError("audited loop did not take exactly one optimizer step")
    _audit_optimizer_after_one_step(optimizer)
    _finite_tensors_or_raise(model.parameters(), label="post-update parameter")
    changed = [
        name
        for name, before in before_parameters.items()
        if not torch.equal(before, model.state_dict()[name])
    ]
    if not changed:
        raise ValueError("one-step PPO did not change any parameter")
    return {
        "model": model,
        "optimizer": optimizer,
        "optimizer_steps": optimizer_steps,
        "gradient_norm_before_clipping": float(gradient_norm.detach().cpu()),
        "changed_parameter_names": changed,
        "loss": float(total_loss.detach().cpu()),
        "policy_loss": float(torch.stack(policy_losses).mean().detach().cpu()),
        "value_loss": float(torch.stack(value_losses).mean().detach().cpu()),
        "entropy": float(torch.stack(entropies).mean().detach().cpu()),
        "pre_step_mean_anchor_kl": float(
            torch.stack(anchor_kls).mean().detach().cpu()
        ),
    }


def _measure_post_update(
    loaded: Mapping[str, Any], probe: Mapping[str, Any]
) -> list[dict[str, Any]]:
    model = loaded["model"]
    reference_config = loaded["reference_config"]
    metrics: list[dict[str, Any]] = []
    with torch.no_grad():
        for ordinal, (_, row) in enumerate(loaded["rows"]):
            state = torch.tensor(row["state_vector"], dtype=torch.float32)
            actions = torch.tensor(row["action_vectors"], dtype=torch.float32)
            residuals, value = model(state, actions)
            post, _ = _torch_behavior_distribution(
                residuals,
                teacher_index=int(row["teacher_action"][0]),
                reference_config=reference_config,
            )
            anchor, _ = _torch_behavior_distribution(
                torch.zeros_like(residuals),
                teacher_index=int(row["teacher_action"][0]),
                reference_config=reference_config,
            )
            _finite_tensors_or_raise(
                (residuals, value, post, anchor), label=f"post-update row {ordinal}"
            )
            post_values = post.detach().cpu().tolist()
            anchor_values = anchor.detach().cpu().tolist()
            pre_values = probe["rows"][ordinal][
                "pre_update_probabilities_float32"
            ]
            metrics.append(
                {
                    "ppo_row_ordinal": ordinal,
                    "public_state_sha256": probe["rows"][ordinal][
                        "public_state_sha256"
                    ],
                    "behavior_action_order_sha256": probe["rows"][ordinal][
                        "behavior_action_order_sha256"
                    ],
                    "post_update_probabilities_float32": post_values,
                    "post_update_value_float32": float(value.detach().cpu()),
                    "post_update_unique_argmax_index": _unique_argmax(post_values),
                    "anchor_kl_post_to_zero": per_row_anchor_kl(
                        post_values, anchor_values
                    ),
                    "total_variation_post_to_pre": per_row_total_variation(
                        post_values, pre_values
                    ),
                }
            )
    return metrics


def _status_artifact_paths(output_directory: Path) -> tuple[Path, ...]:
    return (
        output_directory / "accepted_receipt.json",
        output_directory / "rejected_receipt.json",
        output_directory / "ACCEPTED",
        output_directory / "REJECTED",
    )


def _publish_status(
    output_directory: Path,
    *,
    status: str,
    receipt: Mapping[str, Any],
    directory_guard: _StableDirectoryGuard | None = None,
) -> tuple[Path, str]:
    if status not in ("accepted", "rejected"):
        raise ValueError("execution status must be accepted or rejected")
    output_directory = output_directory.absolute()
    receipt_path = (output_directory / f"{status}_receipt.json").absolute()
    marker_path = (output_directory / status.upper()).absolute()
    lock_path = (output_directory / ".status-publication.lock").absolute()
    guard, owned_guard = _with_directory_guard(receipt_path, directory_guard)
    lock: _StableFileGuard | None = None
    receipt_public: _StableFileGuard | None = None
    marker_public: _StableFileGuard | None = None
    try:
        lock = _create_new_file_guarded(
            lock_path, b"exclusive status publication\n", guard
        )
        existing = [
            path
            for path in _status_artifact_paths(output_directory)
            if path.exists() or path.is_symlink()
        ]
        if existing:
            raise FileExistsError("execution status artifact collision")
        receipt_payload = canonical_json_bytes(receipt, newline=True)
        receipt_file_hash = hashlib.sha256(receipt_payload).hexdigest().upper()
        receipt_public = _create_new_file_guarded(
            receipt_path, receipt_payload, guard
        )
        if _win_read_all(receipt_public.handle) != receipt_payload:
            raise ValueError("status receipt staging hash mismatch")
        marker = {
            "receipt_file_sha256": receipt_file_hash,
            "receipt_sha256": str(receipt["receipt_sha256"]),
            "status": status,
        }
        marker_payload = canonical_json_bytes(marker, newline=True)
        marker_file_hash = hashlib.sha256(marker_payload).hexdigest().upper()
        marker_public = _create_new_file_guarded(
            marker_path, marker_payload, guard
        )
        if _win_read_all(marker_public.handle) != marker_payload:
            raise ValueError("status marker staging hash mismatch")
        opposite = "rejected" if status == "accepted" else "accepted"
        if (
            (output_directory / f"{opposite}_receipt.json").exists()
            or (output_directory / opposite.upper()).exists()
        ):
            raise ValueError("conflicting execution status artifacts")
        receipt_public.ensure_bound_to(guard)
        marker_public.ensure_bound_to(guard)
        return receipt_path, receipt_file_hash
    except Exception:
        # Delete only links whose exact handles were opened from this attempt.
        for artifact in (marker_public, receipt_public):
            if artifact is not None:
                artifact.delete_on_close()
        raise
    finally:
        for artifact in (marker_public, receipt_public):
            if artifact is not None:
                artifact.close()
        for artifact in (lock,):
            if artifact is not None:
                artifact.delete_on_close()
                artifact.close()
        if owned_guard:
            guard.close()


def _write_failed_execution(
    output_directory: Path,
    *,
    execution_spec: Path,
    execution_spec_sha256: str,
    phase: str,
    error: Exception,
    directory_guard: _StableDirectoryGuard | None = None,
    checkpoint_guard: _StableFileGuard | None = None,
    checkpoint_readback: bytes | None = None,
) -> dict[str, Any]:
    checkpoint_path = output_directory / "candidate.pt"
    checkpoint_hash = None
    if checkpoint_guard is not None:
        if directory_guard is None:
            raise ValueError("checkpoint guard requires an output directory guard")
        if checkpoint_readback is None:
            raise ValueError("checkpoint guard requires serialized readback bytes")
        checkpoint_guard.ensure_bound_to(directory_guard)
        if _win_read_all(checkpoint_guard.handle) != checkpoint_readback:
            raise ValueError("checkpoint changed after serialized validation")
        checkpoint_hash = hashlib.sha256(checkpoint_readback).hexdigest().upper()
    core = {
        "schema_version": EXECUTION_RECEIPT_SCHEMA_VERSION,
        "status": "rejected",
        "failure_phase": phase,
        "failure_kind": type(error).__name__,
        "failure_message": str(error),
        "execution_spec_path": str(execution_spec.absolute()),
        "execution_spec_sha256": execution_spec_sha256,
        "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
        "manifest_sha256": MANIFEST_SHA256,
        "dataset_sha256": DATASET_SHA256,
        "output_checkpoint_path": (
            str(checkpoint_path.absolute()) if checkpoint_hash is not None else None
        ),
        "output_checkpoint_sha256": checkpoint_hash,
        "checkpoint_provenance_validation": "fail",
        "accepted_marker_written": False,
    }
    receipt = {**core, "receipt_sha256": canonical_sha256(core)}
    receipt_path, receipt_file_hash = _publish_status(
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
        "checkpoint_path": core["output_checkpoint_path"],
        "checkpoint_sha256": checkpoint_hash,
        "receipt_path": str(receipt_path.absolute()),
        "receipt_file_sha256": receipt_file_hash,
        "receipt_sha256": receipt["receipt_sha256"],
    }


def execute(*, execution_spec: Path, execution_spec_sha256: str) -> dict[str, Any]:
    """Run the separately authorized, pinned, exactly-one-step execution."""

    execution_spec_path = execution_spec.absolute()
    runtime = _runtime_identity()
    spec = _load_execution_spec(execution_spec_path, execution_spec_sha256)
    probe, output_directory = _validate_execution_boundary(
        spec, runtime, execution_spec_path=execution_spec_path
    )
    loaded = _load_validated_inputs()
    # Create the directory under a pinned parent, then retain a full locked
    # component chain for the entire training/publication transaction.
    output_guard = _create_and_guard_output_directory(output_directory)
    checkpoint_guard: _StableFileGuard | None = None
    checkpoint_readback: bytes | None = None
    phase = "one_full_batch_step"
    try:
        step = _one_full_batch_step(loaded)
        phase = "post_update_measurement"
        row_metrics = _measure_post_update(loaded, probe)
        offline_gates = evaluate_post_update_gates(
            probe,
            row_metrics,
            optimizer_steps=step["optimizer_steps"],
            nonfinite_count=0,
            stopped_early=False,
            rolled_back=False,
            checkpoint_provenance_validation="deferred_until_reload",
        )
        metadata = checkpoint_metadata(
            source_hashes=loaded["source_hashes"],
            training={
                "pilot": "phase1-iteration-005-conservative-ppo",
                "execution_spec_path": str(execution_spec_path),
                "execution_spec_sha256": execution_spec_sha256,
                "prepare_receipt_sha256": probe["receipt_sha256"],
                "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
                "manifest_sha256": MANIFEST_SHA256,
                "dataset_sha256": DATASET_SHA256,
                "ppo_config": asdict(PILOT_PPO_CONFIG),
                "adam": copy.deepcopy(PILOT_ADAM_CONFIG),
                "optimizer_steps": step["optimizer_steps"],
                "gradient_norm_before_clipping": step[
                    "gradient_norm_before_clipping"
                ],
                "offline_gates_before_serialized_provenance": offline_gates,
                "checkpoint_provenance_validation": "required_after_save",
            },
        )
        phase = "checkpoint_exclusive_publication"
        (
            checkpoint_path,
            checkpoint_hash,
            checkpoint_guard,
            checkpoint_readback,
        ) = (
            _publish_checkpoint_exclusive(
            output_directory,
            model=step["model"],
            metadata=metadata,
            optimizer=step["optimizer"],
            directory_guard=output_guard,
        ))
        phase = "checkpoint_reload_provenance_validation"
        serialized_validation = _validate_serialized_candidate(
            checkpoint_path,
            claimed_sha256=checkpoint_hash,
            expected_model=step["model"],
            expected_metadata=metadata,
            expected_optimizer_state=step["optimizer"].state_dict(),
            expected_source_hashes=loaded["source_hashes"],
            directory_guard=output_guard,
            file_guard=checkpoint_guard,
            serialized_readback=checkpoint_readback,
        )
        gates = evaluate_post_update_gates(
            probe,
            row_metrics,
            optimizer_steps=step["optimizer_steps"],
            nonfinite_count=0,
            stopped_early=False,
            rolled_back=False,
            checkpoint_provenance_validation=serialized_validation["status"],
        )
        status = "accepted" if gates["accepted"] else "rejected"
        core = {
            "schema_version": EXECUTION_RECEIPT_SCHEMA_VERSION,
            "status": status,
            "execution_spec_path": str(execution_spec_path),
            "execution_spec_sha256": execution_spec_sha256,
            "prepare_receipt_sha256": probe["receipt_sha256"],
            "input_checkpoint_sha256": INPUT_CHECKPOINT_SHA256,
            "manifest_sha256": MANIFEST_SHA256,
            "dataset_sha256": DATASET_SHA256,
            "output_checkpoint_path": str(checkpoint_path.absolute()),
            "output_checkpoint_sha256": checkpoint_hash,
            "optimizer": copy.deepcopy(PILOT_ADAM_CONFIG),
            "ppo_config": asdict(PILOT_PPO_CONFIG),
            "step_report": {
                name: step[name]
                for name in (
                    "optimizer_steps",
                    "gradient_norm_before_clipping",
                    "changed_parameter_names",
                    "loss",
                    "policy_loss",
                    "value_loss",
                    "entropy",
                    "pre_step_mean_anchor_kl",
                )
            },
            "serialized_checkpoint_validation": serialized_validation,
            "gates": gates,
            "row_metrics": row_metrics,
        }
        receipt = {**core, "receipt_sha256": canonical_sha256(core)}
        phase = f"{status}_status_publication"
        receipt_path, receipt_file_hash = _publish_status(
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
        return _write_failed_execution(
            output_directory,
            execution_spec=execution_spec_path,
            execution_spec_sha256=execution_spec_sha256,
            phase=phase,
            error=error,
            directory_guard=output_guard,
            checkpoint_guard=checkpoint_guard,
            checkpoint_readback=checkpoint_readback,
        )
    finally:
        if checkpoint_guard is not None:
            checkpoint_guard.close()
        output_guard.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--output-receipt", type=Path, required=True)
    execute_parser = subparsers.add_parser("execute")
    execute_parser.add_argument("--execution-spec", type=Path, required=True)
    execute_parser.add_argument(
        "--execution-spec-sha256",
        required=True,
        help="Externally pinned uppercase SHA-256 of the immutable spec file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "prepare":
        report = prepare(output_receipt=args.output_receipt)
    else:
        report = execute(
            execution_spec=args.execution_spec,
            execution_spec_sha256=args.execution_spec_sha256,
        )
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0 if report.get("status") != "rejected" else 2


if __name__ == "__main__":
    raise SystemExit(main())
