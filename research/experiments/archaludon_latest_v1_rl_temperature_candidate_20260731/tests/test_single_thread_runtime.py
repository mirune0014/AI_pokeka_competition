from __future__ import annotations

from copy import deepcopy
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

from archaludon_rl.collector import validate_duplicate_pair
from archaludon_rl.frozen_sources import find_repo_root, sha256_file
from archaludon_rl.runtime_contract import (
    REQUIRED_THREAD_ENVIRONMENT,
    canonical_preflight_configuration,
    configure_single_thread_runtime,
    create_runtime_receipt,
    run_model_preflight,
    validate_runtime_receipt,
)
from archaludon_rl.trajectory import (
    TRAJECTORY_SCHEMA_VERSION,
    compare_duplicate_traces,
    json_sha256,
    publish_clean_episode,
)

from .helpers import make_runtime_receipt


class _FakeTorch:
    __version__ = "fake-torch"

    def __init__(
        self,
        *,
        intra: int = 8,
        inter: int = 8,
        ignore_intra_set: bool = False,
        ignore_inter_set: bool = False,
    ) -> None:
        self.intra = intra
        self.inter = inter
        self.ignore_intra_set = ignore_intra_set
        self.ignore_inter_set = ignore_inter_set
        self.intra_set_calls: list[int] = []
        self.inter_set_calls: list[int] = []

    def get_num_threads(self) -> int:
        return self.intra

    def set_num_threads(self, value: int) -> None:
        self.intra_set_calls.append(value)
        if not self.ignore_intra_set:
            self.intra = value

    def get_num_interop_threads(self) -> int:
        return self.inter

    def set_num_interop_threads(self, value: int) -> None:
        self.inter_set_calls.append(value)
        if not self.ignore_inter_set:
            self.inter = value


class _PreflightModel:
    config = SimpleNamespace(state_dim=5, action_dim=3)

    def __init__(self, *, residual: float = 0.0, value: float = 0.0) -> None:
        self.residual = residual
        self.value = value

    def predict(self, state, actions):
        return [self.residual] * len(actions), self.value


class _TickClock:
    def __init__(self, delta: float) -> None:
        self.value = 0.0
        self.delta = delta

    def __call__(self) -> float:
        self.value += self.delta
        return self.value


def _episode(*, engine_steps: int = 10, model_failure: bool = False) -> dict:
    reason = (
        "model_failure:TimeoutError:model inference exceeded 0.050000s"
        if model_failure
        else None
    )
    return {
        "run_id": "run",
        "opponent_id": "historical_silver",
        "seat": 0,
        "seed": 7,
        "terminal_result": 0,
        "engine_steps": engine_steps,
        "decisions": [
            {
                "decision_index": 0,
                "public_projection": {"current": {"turn": 1}},
                "legal_semantic_options": [
                    {"engine_index": 0, "identity": "a", "payload": {}},
                    {"engine_index": 1, "identity": "b", "payload": {}},
                ],
                "legal_option_mask": [True, True],
                "actor_option_mask": [True, True],
                "teacher_action": [0],
                "neural_shadow_action": [0],
                "final_action": [0],
                "ppo_eligible": not model_failure,
                "fallback_used": model_failure,
                "protected": model_failure,
                "fallback_reason": reason,
                "model_failure_kind": "TimeoutError" if model_failure else None,
                "model_timeout": model_failure,
                "sampled_stochastically": not model_failure,
                "q_latest": [0.75, 0.25],
                "residuals": [0.0, 0.0],
                "final_probabilities": [0.75, 0.25],
                "behavior_logprob": None if model_failure else math.log(0.75),
            }
        ],
    }


class SingleThreadRuntimeTests(unittest.TestCase):
    def test_environment_mismatch_is_rejected_before_configuration(self):
        environment = dict(REQUIRED_THREAD_ENVIRONMENT)
        environment["OPENBLAS_NUM_THREADS"] = "2"
        fake = _FakeTorch()
        with self.assertRaisesRegex(ValueError, "environment mismatch"):
            configure_single_thread_runtime(
                torch_module=fake,
                environment=environment,
            )
        self.assertEqual(fake.intra, 8)
        self.assertEqual(fake.inter, 8)

    def test_observed_thread_mismatch_is_rejected(self):
        fake = _FakeTorch(ignore_inter_set=True)
        with self.assertRaisesRegex(ValueError, "observed Torch thread counts"):
            configure_single_thread_runtime(
                torch_module=fake,
                environment=REQUIRED_THREAD_ENVIRONMENT,
            )

    def test_configuration_sets_and_verifies_both_torch_thread_counts(self):
        configured = configure_single_thread_runtime(
            torch_module=_FakeTorch(),
            environment=REQUIRED_THREAD_ENVIRONMENT,
        )
        self.assertEqual(
            configured["observed_thread_counts"],
            {"torch_num_threads": 1, "torch_num_interop_threads": 1},
        )

    def test_both_setters_are_called_even_when_counts_are_already_one(self):
        fake = _FakeTorch(intra=1, inter=1)
        configured = configure_single_thread_runtime(
            torch_module=fake,
            environment=REQUIRED_THREAD_ENVIRONMENT,
        )
        self.assertEqual(fake.intra_set_calls, [1])
        self.assertEqual(fake.inter_set_calls, [1])
        self.assertEqual(
            configured["observed_thread_counts"],
            {"torch_num_threads": 1, "torch_num_interop_threads": 1},
        )

    def test_collector_module_import_does_not_import_torch(self):
        candidate_root = str(Path(__file__).resolve().parents[1])
        environment = dict(os.environ)
        environment["PYTHONPATH"] = candidate_root
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; import archaludon_rl.collect_rollouts; "
                    "print('torch' in sys.modules)"
                ),
            ],
            cwd=candidate_root,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.stdout.strip(), "False")

    def test_runtime_receipt_is_a_deep_canonical_copy(self):
        source_receipt, _ = make_runtime_receipt("C" * 64)
        configured = {
            key: deepcopy(source_receipt[key])
            for key in (
                "requested_thread_counts",
                "observed_thread_counts",
                "required_environment",
                "python",
                "torch_version",
                "platform",
            )
        }
        configuration = deepcopy(source_receipt["preflight_configuration"])
        results = deepcopy(source_receipt["preflight_results"])
        receipt = create_runtime_receipt(
            configured,
            device="cpu",
            timeout_seconds=0.05,
            checkpoint_sha256="C" * 64,
            preflight_configuration=configuration,
            preflight_results=results,
        )
        configured["observed_thread_counts"]["torch_num_threads"] = 99
        configuration["option_counts"][0] = 99
        results["option_count_results"][0]["prediction_calls"] = 99
        self.assertEqual(
            receipt["observed_thread_counts"]["torch_num_threads"], 1
        )
        self.assertEqual(receipt["preflight_configuration"]["option_counts"][0], 2)
        self.assertEqual(
            receipt["preflight_results"]["option_count_results"][0][
                "prediction_calls"
            ],
            100,
        )

    def test_preflight_exact_coverage_and_passing_gates(self):
        configuration = canonical_preflight_configuration(
            require_zero_residuals=True
        )
        results = run_model_preflight(
            _PreflightModel(),
            configuration=configuration,
            clock=_TickClock(0.001),
        )
        self.assertEqual(results["prediction_calls"], 600)
        self.assertEqual(
            [row["option_count"] for row in results["option_count_results"]],
            [2, 3, 4, 7, 10, 19],
        )
        self.assertEqual(results["calls_above_timeout"], 0)
        self.assertLessEqual(results["maximum_latency_seconds"], 0.025)

    def test_v1_preflight_cannot_disable_exact_zero_residuals(self):
        with self.assertRaisesRegex(ValueError, "requires exact zero residuals"):
            canonical_preflight_configuration(require_zero_residuals=False)
        configuration = canonical_preflight_configuration(
            require_zero_residuals=True
        )
        configuration["require_zero_residuals"] = False
        with self.assertRaisesRegex(ValueError, "configuration is not canonical"):
            run_model_preflight(
                _PreflightModel(residual=1.0),
                configuration=configuration,
                clock=_TickClock(0.001),
            )

    def test_preflight_latency_finite_and_zero_residual_gates(self):
        configuration = canonical_preflight_configuration(
            require_zero_residuals=True
        )
        cases = (
            ("latency", _PreflightModel(), _TickClock(0.026), "gate failed"),
            (
                "finite",
                _PreflightModel(value=float("nan")),
                _TickClock(0.001),
                "gate failed",
            ),
            (
                "zero",
                _PreflightModel(residual=1e-12),
                _TickClock(0.001),
                "gate failed",
            ),
        )
        for label, model, clock, error in cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, error):
                    run_model_preflight(
                        model,
                        configuration=configuration,
                        clock=clock,
                    )

    def test_runtime_receipt_tampering_fails_with_receipt_hash_refreshed(self):
        receipt, _ = make_runtime_receipt("A" * 64)
        tampered = deepcopy(receipt)
        tampered["observed_thread_counts"]["torch_num_threads"] = 2
        refreshed_hash = json_sha256(tampered)
        with self.assertRaisesRegex(ValueError, "thread-count contract"):
            validate_runtime_receipt(tampered, refreshed_hash)

    def test_preflight_tampering_fails_with_receipt_hash_refreshed(self):
        receipt, _ = make_runtime_receipt("B" * 64)
        tampered = deepcopy(receipt)
        tampered["preflight_results"]["calls_above_timeout"] = 1
        tampered["preflight_results"]["option_count_results"][0][
            "calls_above_timeout"
        ] = 1
        refreshed_hash = json_sha256(tampered)
        with self.assertRaisesRegex(ValueError, "gate failed"):
            validate_runtime_receipt(tampered, refreshed_hash)

    def test_model_timeout_fallback_in_either_replica_rejects_no_manifest(self):
        for failed_replica in (0, 1):
            with self.subTest(failed_replica=failed_replica):
                pair = [_episode(), _episode()]
                pair[failed_replica] = _episode(model_failure=True)
                with tempfile.TemporaryDirectory() as temporary:
                    manifest = Path(temporary) / "run_manifest.json"
                    with self.assertRaisesRegex(
                        ValueError, "model timeout/fallback"
                    ):
                        validate_duplicate_pair(pair[0], pair[1])
                    self.assertFalse(manifest.exists())

    def test_duplicate_rejection_uses_structured_status_not_reason_text(self):
        structured = _episode()
        structured_row = structured["decisions"][0]
        structured_row.update(
            {
                "fallback_used": True,
                "protected": True,
                "fallback_reason": "opaque diagnostic text",
                "model_failure_kind": "TimeoutError",
                "model_timeout": True,
                "ppo_eligible": False,
                "sampled_stochastically": False,
                "behavior_logprob": None,
            }
        )
        with self.assertRaisesRegex(ValueError, "model timeout/fallback"):
            validate_duplicate_pair(structured, _episode())

        diagnostic_only = _episode()
        diagnostic_only["decisions"][0]["fallback_reason"] = (
            "model_failure:TimeoutError:untrusted text"
        )
        self.assertTrue(
            validate_duplicate_pair(diagnostic_only, diagnostic_only)["equal"]
        )

    def test_engine_step_mismatch_is_part_of_duplicate_contract(self):
        compared = compare_duplicate_traces(
            _episode(engine_steps=10),
            _episode(engine_steps=11),
        )
        self.assertFalse(compared["equal"])
        self.assertFalse(compared["engine_steps_equal"])
        with self.assertRaisesRegex(ValueError, "canonical decision traces"):
            validate_duplicate_pair(
                _episode(engine_steps=10),
                _episode(engine_steps=11),
            )

    def test_legacy_episode_without_engine_steps_fails_closed(self):
        legacy = {
            "schema_version": TRAJECTORY_SCHEMA_VERSION,
            "terminal": True,
            "clean_terminal": True,
        }
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "only clean terminal"):
                publish_clean_episode(Path(temporary) / "episode.json", legacy)

    def test_recorded_default_vs_single_thread_policy_parity(self):
        checkpoint = (
            Path(__file__).resolve().parents[1]
            / "test_outputs"
            / "initial_zero_margin3_iteration004.pt"
        )
        self.assertTrue(checkpoint.is_file())
        probe = Path(__file__).with_name("_runtime_parity_probe.py")
        base_environment = dict(os.environ)
        for name in REQUIRED_THREAD_ENVIRONMENT:
            base_environment.pop(name, None)
        candidate_root = str(Path(__file__).resolve().parents[1])
        existing_pythonpath = base_environment.get("PYTHONPATH")
        base_environment["PYTHONPATH"] = (
            candidate_root
            if not existing_pythonpath
            else candidate_root + os.pathsep + existing_pythonpath
        )
        default = subprocess.run(
            [sys.executable, str(probe), "--checkpoint", str(checkpoint)],
            cwd=Path(__file__).resolve().parents[1],
            env=base_environment,
            check=True,
            capture_output=True,
            text=True,
        )
        single = subprocess.run(
            [
                sys.executable,
                str(probe),
                "--checkpoint",
                str(checkpoint),
                "--single-thread",
            ],
            cwd=Path(__file__).resolve().parents[1],
            env=base_environment,
            check=True,
            capture_output=True,
            text=True,
        )
        default_payload = json.loads(default.stdout.strip().splitlines()[-1])
        single_payload = json.loads(single.stdout.strip().splitlines()[-1])
        self.assertEqual(
            single_payload["observed_thread_counts"],
            {"torch_num_threads": 1, "torch_num_interop_threads": 1},
        )
        for default_row, single_row in zip(
            default_payload["rows"], single_payload["rows"]
        ):
            self.assertEqual(
                default_row["option_count"], single_row["option_count"]
            )
            self.assertEqual(default_row["argmax"], single_row["argmax"])
            self.assertEqual(
                default_row["seeded_samples"], single_row["seeded_samples"]
            )
            self.assertTrue(
                all(
                    math.isclose(left, right, rel_tol=0.0, abs_tol=1e-6)
                    for left, right in zip(
                        default_row["residuals"], single_row["residuals"]
                    )
                )
            )
            self.assertTrue(
                math.isclose(
                    default_row["value"],
                    single_row["value"],
                    rel_tol=0.0,
                    abs_tol=1e-6,
                )
            )
            self.assertTrue(
                all(
                    math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12)
                    for left, right in zip(
                        default_row["probabilities"],
                        single_row["probabilities"],
                    )
                )
            )


if __name__ == "__main__":
    unittest.main()
