"""Fail-closed single-thread collection runtime and preflight receipts."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import time
from typing import Any, Callable, Mapping, Sequence


RUNTIME_RECEIPT_SCHEMA_VERSION = "collection-runtime-receipt-v1"
PREFLIGHT_SCHEMA_VERSION = "collection-runtime-preflight-v1"
TORCH_NUM_THREADS_REQUESTED = 1
TORCH_NUM_INTEROP_THREADS_REQUESTED = 1
REQUIRED_THREAD_ENVIRONMENT = {
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}
PREFLIGHT_PREDICTION_CALLS = 600
PREFLIGHT_OPTION_COUNTS = (2, 3, 4, 7, 10, 19)
PREFLIGHT_CALLS_PER_OPTION_COUNT = 100
PREFLIGHT_TIMEOUT_SECONDS = 0.050
PREFLIGHT_MAXIMUM_LATENCY_SECONDS = 0.025
_SHA256_PATTERN = re.compile(r"[A-F0-9]{64}")


def _json_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def _canonical_copy(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a detached JSON-domain copy with canonical scalar types."""

    return json.loads(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    )


def canonical_preflight_configuration(
    *, require_zero_residuals: bool
) -> dict[str, Any]:
    if not isinstance(require_zero_residuals, bool):
        raise ValueError("require_zero_residuals must be boolean")
    return {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "prediction_calls": PREFLIGHT_PREDICTION_CALLS,
        "option_counts": list(PREFLIGHT_OPTION_COUNTS),
        "calls_per_option_count": PREFLIGHT_CALLS_PER_OPTION_COUNT,
        "timeout_seconds": PREFLIGHT_TIMEOUT_SECONDS,
        "maximum_latency_seconds": PREFLIGHT_MAXIMUM_LATENCY_SECONDS,
        "finite_outputs_required": True,
        "require_zero_residuals": require_zero_residuals,
    }


def configure_single_thread_runtime(
    *,
    torch_module: Any | None = None,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Set and verify Torch's fixed thread counts before model operations."""

    env = os.environ if environment is None else environment
    observed_environment = {
        name: env.get(name) for name in REQUIRED_THREAD_ENVIRONMENT
    }
    if observed_environment != REQUIRED_THREAD_ENVIRONMENT:
        raise ValueError(
            "single-thread runtime environment mismatch: "
            f"expected {REQUIRED_THREAD_ENVIRONMENT}, got {observed_environment}"
        )
    if torch_module is None:
        import torch as torch_module

    torch_module.set_num_threads(TORCH_NUM_THREADS_REQUESTED)
    torch_module.set_num_interop_threads(
        TORCH_NUM_INTEROP_THREADS_REQUESTED
    )
    observed = {
        "torch_num_threads": int(torch_module.get_num_threads()),
        "torch_num_interop_threads": int(
            torch_module.get_num_interop_threads()
        ),
    }
    requested = {
        "torch_num_threads": TORCH_NUM_THREADS_REQUESTED,
        "torch_num_interop_threads": TORCH_NUM_INTEROP_THREADS_REQUESTED,
    }
    if observed != requested:
        raise ValueError(
            "observed Torch thread counts do not match the requested runtime: "
            f"requested {requested}, observed {observed}"
        )
    return {
        "requested_thread_counts": requested,
        "observed_thread_counts": observed,
        "required_environment": dict(REQUIRED_THREAD_ENVIRONMENT),
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "torch_version": str(torch_module.__version__),
        "platform": platform.platform(),
    }


def _fixed_inputs(
    model: Any, option_count: int
) -> tuple[list[float], list[list[float]]]:
    config = getattr(model, "config", None)
    state_dim = int(getattr(config, "state_dim", 0))
    action_dim = int(getattr(config, "action_dim", 0))
    if state_dim <= 0 or action_dim <= 0:
        raise ValueError("preflight model dimensions are unavailable")
    state = [
        (((index + 1) * (option_count + 3)) % 19 - 9) / 9.0
        for index in range(state_dim)
    ]
    actions = [
        [
            (
                ((option_index + 1) * 7 + (feature_index + 1) * 3 + option_count)
                % 23
                - 11
            )
            / 11.0
            for feature_index in range(action_dim)
        ]
        for option_index in range(option_count)
    ]
    return state, actions


def run_model_preflight(
    model: Any,
    *,
    configuration: Mapping[str, Any],
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    """Measure 600 same-process ``model.predict`` calls and enforce all gates."""

    config = dict(configuration)
    expected_config = canonical_preflight_configuration(
        require_zero_residuals=config.get("require_zero_residuals")
    )
    if config != expected_config:
        raise ValueError("preflight configuration is not canonical")

    option_results: list[dict[str, Any]] = []
    total_nonfinite = 0
    total_nonzero = 0
    total_residuals = 0
    total_above_timeout = 0
    total_above_maximum = 0
    overall_maximum = 0.0
    for option_count in PREFLIGHT_OPTION_COUNTS:
        state, actions = _fixed_inputs(model, option_count)
        nonfinite = 0
        nonzero = 0
        calls_above_timeout = 0
        calls_above_maximum = 0
        maximum_latency = 0.0
        for _ in range(PREFLIGHT_CALLS_PER_OPTION_COUNT):
            started = clock()
            raw_residuals, raw_value = model.predict(state, actions)
            elapsed = float(clock() - started)
            if not math.isfinite(elapsed) or elapsed < 0.0:
                raise ValueError("preflight clock produced an invalid latency")
            residuals = tuple(float(value) for value in raw_residuals)
            value = float(raw_value)
            if len(residuals) != option_count:
                raise ValueError("preflight model residual dimension mismatch")
            nonfinite += sum(not math.isfinite(item) for item in residuals)
            nonfinite += int(not math.isfinite(value))
            nonzero += sum(item != 0.0 for item in residuals)
            calls_above_timeout += int(
                elapsed > float(config["timeout_seconds"])
            )
            calls_above_maximum += int(
                elapsed > float(config["maximum_latency_seconds"])
            )
            maximum_latency = max(maximum_latency, elapsed)
        residual_count = option_count * PREFLIGHT_CALLS_PER_OPTION_COUNT
        row = {
            "option_count": option_count,
            "prediction_calls": PREFLIGHT_CALLS_PER_OPTION_COUNT,
            "residual_output_count": residual_count,
            "nonfinite_output_count": nonfinite,
            "nonzero_residual_count": nonzero,
            "calls_above_timeout": calls_above_timeout,
            "calls_above_maximum_latency": calls_above_maximum,
            "maximum_latency_seconds": maximum_latency,
        }
        option_results.append(row)
        total_nonfinite += nonfinite
        total_nonzero += nonzero
        total_residuals += residual_count
        total_above_timeout += calls_above_timeout
        total_above_maximum += calls_above_maximum
        overall_maximum = max(overall_maximum, maximum_latency)
    results = {
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
        "prediction_calls": PREFLIGHT_PREDICTION_CALLS,
        "residual_output_count": total_residuals,
        "finite_outputs": total_nonfinite == 0,
        "zero_residuals": total_nonzero == 0,
        "nonfinite_output_count": total_nonfinite,
        "nonzero_residual_count": total_nonzero,
        "calls_above_timeout": total_above_timeout,
        "calls_above_maximum_latency": total_above_maximum,
        "maximum_latency_seconds": overall_maximum,
        "option_count_results": option_results,
    }
    validate_preflight(config, results)
    return results


def _strict_nonnegative_int(value: Any, *, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a strict nonnegative integer")
    return value


def validate_preflight(
    configuration: Mapping[str, Any], results: Mapping[str, Any]
) -> None:
    config = dict(configuration)
    expected_config = canonical_preflight_configuration(
        require_zero_residuals=config.get("require_zero_residuals")
    )
    if config != expected_config:
        raise ValueError("runtime receipt preflight configuration mismatch")
    required_result_keys = {
        "schema_version",
        "prediction_calls",
        "residual_output_count",
        "finite_outputs",
        "zero_residuals",
        "nonfinite_output_count",
        "nonzero_residual_count",
        "calls_above_timeout",
        "calls_above_maximum_latency",
        "maximum_latency_seconds",
        "option_count_results",
    }
    result = dict(results)
    if set(result) != required_result_keys:
        raise ValueError("runtime receipt preflight result schema mismatch")
    if result.get("schema_version") != PREFLIGHT_SCHEMA_VERSION:
        raise ValueError("runtime receipt preflight result version mismatch")
    if not isinstance(result.get("finite_outputs"), bool) or not isinstance(
        result.get("zero_residuals"), bool
    ):
        raise ValueError("preflight boolean result fields are invalid")
    prediction_calls = _strict_nonnegative_int(
        result.get("prediction_calls"), label="preflight prediction calls"
    )
    residual_outputs = _strict_nonnegative_int(
        result.get("residual_output_count"),
        label="preflight residual output count",
    )
    nonfinite = _strict_nonnegative_int(
        result.get("nonfinite_output_count"),
        label="preflight nonfinite output count",
    )
    nonzero = _strict_nonnegative_int(
        result.get("nonzero_residual_count"),
        label="preflight nonzero residual count",
    )
    above_timeout = _strict_nonnegative_int(
        result.get("calls_above_timeout"),
        label="preflight calls above timeout",
    )
    above_maximum = _strict_nonnegative_int(
        result.get("calls_above_maximum_latency"),
        label="preflight calls above maximum latency",
    )
    maximum_latency = result.get("maximum_latency_seconds")
    if (
        isinstance(maximum_latency, bool)
        or not isinstance(maximum_latency, (int, float))
        or not math.isfinite(float(maximum_latency))
        or float(maximum_latency) < 0.0
    ):
        raise ValueError("preflight maximum latency is invalid")
    raw_rows = result.get("option_count_results")
    if not isinstance(raw_rows, (list, tuple)):
        raise ValueError("preflight option-count results are missing")
    rows = tuple(dict(row) for row in raw_rows)
    if tuple(row.get("option_count") for row in rows) != PREFLIGHT_OPTION_COUNTS:
        raise ValueError("preflight option-count coverage mismatch")
    row_keys = {
        "option_count",
        "prediction_calls",
        "residual_output_count",
        "nonfinite_output_count",
        "nonzero_residual_count",
        "calls_above_timeout",
        "calls_above_maximum_latency",
        "maximum_latency_seconds",
    }
    for row in rows:
        if set(row) != row_keys:
            raise ValueError("preflight option-count result schema mismatch")
        option_count = _strict_nonnegative_int(
            row.get("option_count"), label="preflight option count"
        )
        row_calls = _strict_nonnegative_int(
            row.get("prediction_calls"), label="preflight row calls"
        )
        row_residuals = _strict_nonnegative_int(
            row.get("residual_output_count"),
            label="preflight row residual count",
        )
        row_nonfinite = _strict_nonnegative_int(
            row.get("nonfinite_output_count"),
            label="preflight row nonfinite count",
        )
        row_nonzero = _strict_nonnegative_int(
            row.get("nonzero_residual_count"),
            label="preflight row nonzero count",
        )
        row_above_timeout = _strict_nonnegative_int(
            row.get("calls_above_timeout"),
            label="preflight row calls above timeout",
        )
        row_above_maximum = _strict_nonnegative_int(
            row.get("calls_above_maximum_latency"),
            label="preflight row calls above maximum latency",
        )
        row_maximum = row.get("maximum_latency_seconds")
        if (
            row_calls != PREFLIGHT_CALLS_PER_OPTION_COUNT
            or row_residuals != option_count * row_calls
            or row_nonfinite != 0
            or row_above_timeout != 0
            or row_above_maximum != 0
            or (config["require_zero_residuals"] and row_nonzero != 0)
            or isinstance(row_maximum, bool)
            or not isinstance(row_maximum, (int, float))
            or not math.isfinite(float(row_maximum))
            or not 0.0 <= float(row_maximum) <= float(
                config["maximum_latency_seconds"]
            )
        ):
            raise ValueError("preflight option-count gate failed")
    expected_residual_outputs = PREFLIGHT_CALLS_PER_OPTION_COUNT * sum(
        PREFLIGHT_OPTION_COUNTS
    )
    if (
        prediction_calls != PREFLIGHT_PREDICTION_CALLS
        or prediction_calls != sum(int(row["prediction_calls"]) for row in rows)
        or residual_outputs != expected_residual_outputs
        or residual_outputs
        != sum(int(row["residual_output_count"]) for row in rows)
        or nonfinite != sum(int(row["nonfinite_output_count"]) for row in rows)
        or nonzero != sum(int(row["nonzero_residual_count"]) for row in rows)
        or above_timeout != sum(int(row["calls_above_timeout"]) for row in rows)
        or above_maximum
        != sum(int(row["calls_above_maximum_latency"]) for row in rows)
        or float(maximum_latency)
        != max(float(row["maximum_latency_seconds"]) for row in rows)
        or result.get("finite_outputs") is not True
        or bool(result.get("zero_residuals")) != (nonzero == 0)
        or nonfinite != 0
        or above_timeout != 0
        or above_maximum != 0
        or float(maximum_latency) > float(config["maximum_latency_seconds"])
        or (config["require_zero_residuals"] and nonzero != 0)
    ):
        raise ValueError("runtime preflight aggregate gate failed")


def create_runtime_receipt(
    configured_runtime: Mapping[str, Any],
    *,
    device: str,
    timeout_seconds: float,
    checkpoint_sha256: str,
    preflight_configuration: Mapping[str, Any],
    preflight_results: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = _canonical_copy({
        "schema_version": RUNTIME_RECEIPT_SCHEMA_VERSION,
        "requested_thread_counts": dict(
            configured_runtime["requested_thread_counts"]
        ),
        "observed_thread_counts": dict(
            configured_runtime["observed_thread_counts"]
        ),
        "python": dict(configured_runtime["python"]),
        "torch_version": str(configured_runtime["torch_version"]),
        "platform": str(configured_runtime["platform"]),
        "device": str(device),
        "timeout_seconds": float(timeout_seconds),
        "checkpoint_sha256": str(checkpoint_sha256),
        "required_environment": dict(
            configured_runtime["required_environment"]
        ),
        "preflight_configuration": dict(preflight_configuration),
        "preflight_results": dict(preflight_results),
    })
    validate_runtime_receipt(receipt)
    return receipt


def canonical_runtime_receipt(
    receipt: Mapping[str, Any], expected_sha256: str | None = None
) -> dict[str, Any]:
    """Validate and detach a receipt before binding it into another layer."""

    validate_runtime_receipt(receipt, expected_sha256)
    return _canonical_copy(receipt)


def runtime_receipt_sha256(receipt: Mapping[str, Any]) -> str:
    validate_runtime_receipt(receipt)
    return _json_sha256(dict(receipt))


def validate_runtime_receipt(
    receipt: Mapping[str, Any], expected_sha256: str | None = None
) -> None:
    required_keys = {
        "schema_version",
        "requested_thread_counts",
        "observed_thread_counts",
        "python",
        "torch_version",
        "platform",
        "device",
        "timeout_seconds",
        "checkpoint_sha256",
        "required_environment",
        "preflight_configuration",
        "preflight_results",
    }
    row = dict(receipt)
    if set(row) != required_keys:
        raise ValueError("runtime receipt schema mismatch")
    if row.get("schema_version") != RUNTIME_RECEIPT_SCHEMA_VERSION:
        raise ValueError("runtime receipt version mismatch")
    requested = row.get("requested_thread_counts")
    observed = row.get("observed_thread_counts")
    expected_threads = {
        "torch_num_threads": TORCH_NUM_THREADS_REQUESTED,
        "torch_num_interop_threads": TORCH_NUM_INTEROP_THREADS_REQUESTED,
    }
    if requested != expected_threads or observed != expected_threads:
        raise ValueError("runtime receipt thread-count contract mismatch")
    if row.get("required_environment") != REQUIRED_THREAD_ENVIRONMENT:
        raise ValueError("runtime receipt environment contract mismatch")
    python_row = row.get("python")
    if (
        not isinstance(python_row, dict)
        or set(python_row) != {"implementation", "version"}
        or not all(
            isinstance(python_row.get(name), str) and python_row.get(name)
            for name in ("implementation", "version")
        )
    ):
        raise ValueError("runtime receipt Python identity is invalid")
    if (
        not isinstance(row.get("torch_version"), str)
        or not row.get("torch_version")
        or not isinstance(row.get("platform"), str)
        or not row.get("platform")
        or row.get("device") != "cpu"
        or row.get("timeout_seconds") != PREFLIGHT_TIMEOUT_SECONDS
        or not isinstance(row.get("checkpoint_sha256"), str)
        or not _SHA256_PATTERN.fullmatch(str(row.get("checkpoint_sha256")))
    ):
        raise ValueError("runtime receipt fixed runtime identity is invalid")
    preflight_config = row.get("preflight_configuration")
    preflight_results = row.get("preflight_results")
    if not isinstance(preflight_config, dict) or not isinstance(
        preflight_results, dict
    ):
        raise ValueError("runtime receipt preflight is missing")
    validate_preflight(preflight_config, preflight_results)
    if expected_sha256 is not None:
        if (
            not isinstance(expected_sha256, str)
            or not _SHA256_PATTERN.fullmatch(expected_sha256)
            or _json_sha256(row) != expected_sha256
        ):
            raise ValueError("runtime receipt SHA256 mismatch")
