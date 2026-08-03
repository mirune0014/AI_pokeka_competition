"""Focused iteration-007 tests; no test executes the real 830-row optimizer."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import torch

from archaludon_rl import actor_only_interaction_maturation_pilot as pilot
from archaludon_rl.model import ModelConfig, ResidualActorCritic


class _FakeGuard:
    def __init__(self, payload: bytes = b"") -> None:
        self.payload = payload
        self.handle = object()
        self.closed = False

    def ensure_bound_to(self, _directory_guard) -> None:
        return None

    def close(self) -> None:
        self.closed = True


def _rehash(receipt: dict) -> dict:
    core = dict(receipt)
    core.pop("receipt_sha256", None)
    receipt["receipt_sha256"] = pilot.canonical_sha256(core)
    return receipt


def _pinned_runtime_without_mutation() -> dict:
    return {
        "requested_thread_counts": {
            "torch_num_threads": 1,
            "torch_num_interop_threads": 1,
        },
        "observed_thread_counts": {
            "torch_num_threads": 1,
            "torch_num_interop_threads": 1,
        },
        "required_environment": dict(pilot.inherited.REQUIRED_THREAD_ENVIRONMENT),
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
        },
        "torch_version": str(torch.__version__),
        "platform": platform.platform(),
    }


def _validate_prepare_receipt_without_runtime_mutation(receipt: dict) -> None:
    with (
        mock.patch.object(torch, "get_num_threads", return_value=1),
        mock.patch.object(torch, "get_num_interop_threads", return_value=1),
        mock.patch.object(
            torch.optim, "Adam", side_effect=AssertionError("validator constructed Adam")
        ),
    ):
        pilot.validate_prepare_receipt(receipt)


def _family_report(values: dict[str, float]) -> dict:
    groups = []
    for name in ("PLAY", "ATTACH", "EVOLVE", "RETREAT", "ATTACK", "END"):
        for polarity in ("positive", "negative"):
            value = values[f"{name}:{polarity}"]
            groups.append(
                {
                    "name": name,
                    "polarity": polarity,
                    "lower_empirical_median": value,
                }
            )
    return {"groups": groups, "failures": [], "all_pass": True}


def _terminal_run(
    *,
    family_1: float = -2e-6,
    family_16: float = 2e-6,
    family_32: float = 2e-5,
    score: float = 0.1,
    median: float = 1e-5,
) -> dict:
    names = (
        "PLAY:positive", "PLAY:negative", "ATTACH:positive", "ATTACH:negative",
        "EVOLVE:positive", "EVOLVE:negative", "RETREAT:positive",
        "RETREAT:negative", "ATTACK:positive", "ATTACK:negative",
        "END:positive", "END:negative",
    )
    values_1 = {name: family_1 for name in names}
    values_16 = {name: family_16 for name in names}
    values_32 = {name: family_32 for name in names}
    update_summaries = [
        {"safety": {"safety_pass": True}} for _ in range(pilot.STAGE2_UPDATES)
    ]
    return {
        "optimizer_steps_completed": pilot.TOTAL_OPTIMIZER_STEPS,
        "safety_stop": False,
        "stage_1_safety": {
            "safety_pass": True,
            "family_diagnostics": _family_report(values_1),
        },
        "stage_2_update_summaries": update_summaries,
        "stage_2_milestone_summaries": {
            "16": {
                "family_diagnostics": _family_report(values_16),
                "global_alignment": {"score": score, "lower_empirical_median": median},
            },
            "32": {
                "family_diagnostics": _family_report(values_32),
                "global_alignment": {"score": score, "lower_empirical_median": median},
            },
        },
        "terminal_end_gates": {"passed": True, "failures": []},
        "parameter_optimizer_contract_pass": True,
        "value_contract_pass": True,
    }


def _blocked_prepare_v2() -> dict:
    path = pilot._repo_path(pilot.AUDIT_BLOCKED_PREPARE_V2_RELATIVE_PATH)
    return json.loads(path.read_text(encoding="utf-8"))


def _shift_float32(values, donor: int, receiver: int, amount: float = 0.001):
    result = torch.tensor(values, dtype=torch.float32)
    delta = torch.tensor(amount, dtype=torch.float32)
    result[donor] -= delta
    result[receiver] += delta
    return result.tolist()


def _passing_directional_metrics(receipt: dict) -> list[dict]:
    metrics = [
        {"probabilities_float32": list(row["initial_probabilities_float32"])}
        for row in receipt["rows"]
    ]
    memberships = receipt["directional_memberships"]
    for ordinal in memberships["teacher_end_ordinals"]:
        row = receipt["rows"][ordinal]
        end = int(row["end_index"])
        donor = max(
            (index for index in range(len(metrics[ordinal]["probabilities_float32"])) if index != end),
            key=lambda index: metrics[ordinal]["probabilities_float32"][index],
        )
        metrics[ordinal]["probabilities_float32"] = _shift_float32(
            metrics[ordinal]["probabilities_float32"], donor, end
        )
    for ordinal in memberships["negative_target_ordinals"]:
        row = receipt["rows"][ordinal]
        metrics[ordinal]["probabilities_float32"] = _shift_float32(
            metrics[ordinal]["probabilities_float32"],
            int(row["end_index"]),
            int(row["teacher_index"]),
        )
    return metrics


def _lowest_float32_delta_at_least(initial: float, threshold: float) -> tuple[float, float]:
    base = torch.tensor(initial, dtype=torch.float32)
    candidate = torch.tensor(initial + threshold, dtype=torch.float32)
    positive_infinity = torch.tensor(float("inf"), dtype=torch.float32)
    negative_infinity = torch.tensor(float("-inf"), dtype=torch.float32)
    while float(candidate) - float(base) < threshold:
        candidate = torch.nextafter(candidate, positive_infinity)
    previous = torch.nextafter(candidate, negative_infinity)
    while float(previous) - float(base) >= threshold:
        candidate = previous
        previous = torch.nextafter(candidate, negative_infinity)
    return float(candidate), float(previous)


def _highest_float32_delta_at_most(initial: float, threshold: float) -> tuple[float, float]:
    base = torch.tensor(initial, dtype=torch.float32)
    candidate = torch.tensor(initial + threshold, dtype=torch.float32)
    positive_infinity = torch.tensor(float("inf"), dtype=torch.float32)
    negative_infinity = torch.tensor(float("-inf"), dtype=torch.float32)
    while float(candidate) - float(base) > threshold:
        candidate = torch.nextafter(candidate, negative_infinity)
    following = torch.nextafter(candidate, positive_infinity)
    while float(following) - float(base) <= threshold:
        candidate = following
        following = torch.nextafter(candidate, positive_infinity)
    return float(candidate), float(following)


class _ExplodingMetrics:
    def __getitem__(self, _index):
        raise AssertionError("directional metrics were read before membership rejection")


def _stage1_progress() -> pilot.ExecutionProgress:
    model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
    pilot._set_trainability(model, stage=1)
    optimizer = pilot._new_actor_adam(model)
    optimizer.zero_grad(set_to_none=True)
    sum(
        dict(model.named_parameters())[name].square().sum()
        for name in pilot.STAGE1_TRAINABLE_NAMES
    ).backward()
    progress = pilot.ExecutionProgress(model=model, optimizer=optimizer)
    pilot._optimizer_step_and_record(optimizer, progress, stage=1)
    return progress


def _full_compact_chain() -> dict:
    previous = "A" * 64
    summaries = []
    for update in range(1, pilot.STAGE2_UPDATES + 1):
        top = {
            "stage_2_update_ordinal": update,
            "optimizer_step_ordinal": update + 1,
            "optimizer_state_steps": {"interaction": update, "readout": 1},
            "loss": float(update) + 0.01,
            "policy_loss": float(update) + 0.02,
            "anchor_kl_loss": float(update) + 0.03,
            "entropy": float(update) + 0.04,
            "gradient_norm_before_clipping": float(update) + 0.05,
            "per_parameter_gradient_norm_before_clipping": {"p": float(update) + 0.06},
            "per_parameter_gradient_norm_after_clipping": {"p": float(update) + 0.07},
            "parameter_diffs_from_initial": [{"sentinel": f"initial-{update}"}],
            "parameter_diffs_from_previous_step": [{"sentinel": f"previous-{update}"}],
            "parameter_diffs_from_stage_start": [{"sentinel": "fixed-post-stage1"}],
            "safety": {"sentinel": f"safety-{update}"},
            "value_identity": {"sentinel": f"value-{update}"},
            "frozen_encoder_value_contract": {"sentinel": f"frozen-{update}"},
            "ordered_probability_bytes_sha256": f"{update:064X}",
            "ordered_value_bytes_sha256": f"{update + 100:064X}",
            "raw_rows_persisted": update in pilot.DIAGNOSTIC_UPDATE_ORDINALS,
            "previous_record_hash": previous,
        }
        top["measurement_timing"] = {
            "pre_step": {
                "loss": top["loss"],
                "policy_loss": top["policy_loss"],
                "anchor_kl_contribution": top["anchor_kl_loss"],
                "entropy": top["entropy"],
                "gradient_norm_before_clipping": top["gradient_norm_before_clipping"],
                "per_parameter_gradient_norm_before_clipping": top[
                    "per_parameter_gradient_norm_before_clipping"
                ],
                "per_parameter_gradient_norm_after_clipping": top[
                    "per_parameter_gradient_norm_after_clipping"
                ],
            },
            "post_step": {
                "optimizer_state_steps": top["optimizer_state_steps"],
                "parameter_diffs_from_initial": top["parameter_diffs_from_initial"],
                "parameter_diffs_from_fixed_stage_2_start": top[
                    "parameter_diffs_from_stage_start"
                ],
                "parameter_diffs_from_previous_step": top[
                    "parameter_diffs_from_previous_step"
                ],
                "safety": top["safety"],
                "ordered_probability_bytes_sha256": top[
                    "ordered_probability_bytes_sha256"
                ],
                "ordered_value_bytes_sha256": top["ordered_value_bytes_sha256"],
            },
        }
        record = {**top, "record_hash": pilot.canonical_sha256(top)}
        summaries.append(record)
        previous = record["record_hash"]
    return {"stage_1_record_hash": "A" * 64, "stage_2_update_summaries": summaries}


def _relink_compact_chain(training: dict) -> None:
    previous = training["stage_1_record_hash"]
    for record in training["stage_2_update_summaries"]:
        record["previous_record_hash"] = previous
        core = dict(record)
        core.pop("record_hash", None)
        record["record_hash"] = pilot.canonical_sha256(core)
        previous = record["record_hash"]


class InteractionMaturationMathTests(unittest.TestCase):
    def test_lower_median_and_deadband_boundaries_are_exact(self) -> None:
        self.assertEqual(pilot.lower_empirical_median([4.0, 1.0, 3.0, 2.0]), 2.0)
        self.assertEqual(pilot.orientation_class(pilot.DEADBAND_TAU), "neutral")
        self.assertEqual(pilot.orientation_class(-pilot.DEADBAND_TAU), "neutral")
        self.assertEqual(
            pilot.orientation_class(math.nextafter(pilot.DEADBAND_TAU, math.inf)),
            "aligned",
        )

    def test_terminal_family_threshold_is_strict(self) -> None:
        run = _terminal_run(family_32=pilot.DEADBAND_TAU)
        result = pilot.evaluate_terminal_offline_gates(run=run)
        self.assertTrue(any("lower_median" in value for value in result["failures"]))
        run = _terminal_run(
            family_32=math.nextafter(pilot.DEADBAND_TAU, math.inf),
            family_1=-1.0,
            family_16=0.0,
        )
        # Formerly failing groups still need the separate 1e-6 practical minimum.
        result = pilot.evaluate_terminal_offline_gates(run=run)
        self.assertTrue(any("minimum" in value for value in result["failures"]))

    def test_formerly_failing_improvement_is_strict_and_minimum_is_inclusive(self) -> None:
        run = _terminal_run(family_1=2e-6, family_16=2e-6, family_32=2e-5)
        result = pilot.evaluate_terminal_offline_gates(run=run)
        self.assertTrue(any("update16" in value for value in result["failures"]))
        run = _terminal_run(family_1=-2e-6, family_16=2e-6, family_32=1e-6)
        result = pilot.evaluate_terminal_offline_gates(run=run)
        self.assertFalse(any("minimum" in value for value in result["failures"]))
        run = _terminal_run(
            family_1=-2e-6,
            family_16=2e-6,
            family_32=math.nextafter(1e-6, -math.inf),
        )
        result = pilot.evaluate_terminal_offline_gates(run=run)
        self.assertTrue(any("minimum" in value for value in result["failures"]))

    def test_global_practical_thresholds_are_inclusive(self) -> None:
        self.assertTrue(
            pilot.evaluate_terminal_offline_gates(run=_terminal_run())["accepted_before_checkpoint_validation"]
        )
        below_score = _terminal_run(score=math.nextafter(0.1, -math.inf))
        self.assertIn(
            "terminal:global_alignment_score",
            pilot.evaluate_terminal_offline_gates(run=below_score)["failures"],
        )
        below_median = _terminal_run(median=math.nextafter(1e-5, -math.inf))
        self.assertIn(
            "terminal:global_lower_median",
            pilot.evaluate_terminal_offline_gates(run=below_median)["failures"],
        )


class InteractionMaturationSyntheticOptimizerTests(unittest.TestCase):
    def test_one_adam_has_exact_four_tensor_universe_and_mixed_step_counters(self) -> None:
        torch.manual_seed(7007)
        model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
        initial = {name: value.detach().clone() for name, value in model.state_dict().items()}
        state = torch.randn(3)
        actions = torch.randn(2, 2)
        with torch.no_grad():
            initial_value = model(state, actions)[1].detach().clone()
        progress = pilot.ExecutionProgress(model=model)
        pilot._set_trainability(model, stage=1)
        optimizer = pilot._new_actor_adam(model)
        progress.optimizer = optimizer
        identity = id(optimizer)
        named = dict(model.named_parameters())
        optimizer.zero_grad(set_to_none=True)
        sum(named[name].sum() for name in pilot.STAGE1_TRAINABLE_NAMES).backward()
        pilot._optimizer_step_and_record(optimizer, progress, stage=1)
        self.assertEqual(
            pilot.audit_optimizer_contract(optimizer, model, stage=1),
            {name: 1 for name in pilot.STAGE1_TRAINABLE_NAMES},
        )
        readout = {
            name: named[name].detach().clone() for name in pilot.STAGE1_TRAINABLE_NAMES
        }
        readout_state = {
            name: deepcopy(optimizer.state[named[name]])
            for name in pilot.STAGE1_TRAINABLE_NAMES
        }
        pilot._set_trainability(model, stage=2)
        for update in range(1, pilot.STAGE2_UPDATES + 1):
            optimizer.zero_grad(set_to_none=True)
            sum(
                (index + 1) * named[name].square().sum()
                for index, name in enumerate(pilot.STAGE2_TRAINABLE_NAMES)
            ).backward()
            pilot._optimizer_step_and_record(
                optimizer,
                progress,
                stage=2,
                stage_2_update_ordinal=update,
            )
            self.assertEqual(id(optimizer), identity)
            self.assertEqual(
                pilot.audit_optimizer_contract(
                    optimizer,
                    model,
                    stage=2,
                    stage_2_update_ordinal=update,
                ),
                {
                    **{name: update for name in pilot.STAGE2_TRAINABLE_NAMES},
                    **{name: 1 for name in pilot.STAGE1_TRAINABLE_NAMES},
                },
            )
        self.assertEqual(progress.optimizer_steps_completed, 33)
        self.assertEqual(progress.stage_2_updates_completed, 32)
        for name in pilot.STAGE1_TRAINABLE_NAMES:
            self.assertTrue(torch.equal(readout[name], named[name]))
            self.assertTrue(
                pilot._nested_byte_exact(readout_state[name], optimizer.state[named[name]])
            )
        changed = [
            name for name, before in initial.items()
            if not torch.equal(before, model.state_dict()[name])
        ]
        self.assertEqual(
            changed,
            [*pilot.STAGE2_TRAINABLE_NAMES, *pilot.STAGE1_TRAINABLE_NAMES],
        )
        for name in initial:
            if name not in pilot.OPTIMIZER_PARAMETER_NAMES:
                self.assertTrue(torch.equal(initial[name], model.state_dict()[name]))
        with torch.no_grad():
            final_value = model(state, actions)[1]
        self.assertTrue(torch.equal(initial_value, final_value))

    def test_serialized_terminal_optimizer_state_is_exact(self) -> None:
        torch.manual_seed(7017)
        model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
        progress = pilot.ExecutionProgress(model=model)
        pilot._set_trainability(model, stage=1)
        optimizer = pilot._new_actor_adam(model)
        progress.optimizer = optimizer
        named = dict(model.named_parameters())
        optimizer.zero_grad(set_to_none=True)
        sum(named[name].sum() for name in pilot.STAGE1_TRAINABLE_NAMES).backward()
        pilot._optimizer_step_and_record(optimizer, progress, stage=1)
        pilot._set_trainability(model, stage=2)
        for update in range(1, 33):
            optimizer.zero_grad(set_to_none=True)
            sum(named[name].square().sum() for name in pilot.STAGE2_TRAINABLE_NAMES).backward()
            pilot._optimizer_step_and_record(
                optimizer, progress, stage=2, stage_2_update_ordinal=update
            )
        self.assertEqual(
            pilot._audit_serialized_optimizer(
                optimizer.state_dict(), completed_stage=33
            ),
            pilot._expected_optimizer_steps(33),
        )


class InteractionMaturationScheduleTests(unittest.TestCase):
    def _fake_step(self, *, stage, optimizer, progress, stage_2_update_ordinal=None, **_):
        named = dict(progress.model.named_parameters())
        pilot._set_trainability(progress.model, stage=stage)
        names = pilot.STAGE1_TRAINABLE_NAMES if stage == 1 else pilot.STAGE2_TRAINABLE_NAMES
        optimizer.zero_grad(set_to_none=True)
        sum(named[name].square().sum() for name in names).backward()
        pilot._optimizer_step_and_record(
            optimizer,
            progress,
            stage=stage,
            stage_2_update_ordinal=stage_2_update_ordinal,
        )
        step = progress.optimizer_steps_completed
        return {
            "optimizer_step_ordinal": step,
            "optimizer_state_steps": pilot._expected_optimizer_steps(step),
            "loss": 0.0,
            "policy_loss": 0.0,
            "pre_step_mean_anchor_kl": 0.0,
            "entropy": 0.0,
            "gradient_norm_before_clipping": 1.0,
            "per_parameter_gradient_norm_before_clipping": {name: 1.0 for name in names},
            "per_parameter_gradient_norm_after_clipping": {name: 0.25 for name in names},
            "parameter_diffs_from_initial": [],
            "parameter_diffs_from_stage_start": [],
            "parameter_diffs_from_previous_step": [],
            "nonfinite_value_gradient_optimizer_or_parameter_count": 0,
        }

    @staticmethod
    def _fake_safety(*_, stage, stage_2_update_ordinal=None, **__) -> dict:
        value = 2e-5
        family = _family_report(
            {
                f"{name}:{polarity}": value
                for name in ("PLAY", "ATTACH", "EVOLVE", "RETREAT", "ATTACK", "END")
                for polarity in ("positive", "negative")
            }
        )
        return {
            "safety_pass": True,
            "hard_stop": False,
            "global_alignment": {"score": 0.2, "lower_empirical_median": 2e-5},
            "family_diagnostics": family,
            "mean_anchor_kl": 0.0,
            "maximum_anchor_kl": 0.0,
            "maximum_total_variation": 0.0,
            "stage": stage,
            "stage_2_update_ordinal": stage_2_update_ordinal,
        }

    def test_directional_failure_never_stops_before_update_32(self) -> None:
        model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
        loaded = {"model": model}
        prepare = {"rows": []}
        value_identity = {
            "all_rows_byte_exact_to_initial": True,
            "raw_value_mse_exact_to_initial": True,
        }
        with (
            mock.patch.object(pilot, "raw_value_mse", return_value=0.0),
            mock.patch.object(pilot, "_stage_full_batch_step", side_effect=self._fake_step),
            mock.patch.object(pilot, "_measure_stage", return_value=[]),
            mock.patch.object(pilot, "value_change_summary", return_value=value_identity),
            mock.patch.object(pilot, "evaluate_stage_gates", side_effect=self._fake_safety),
            mock.patch.object(
                pilot,
                "evaluate_directional_gates",
                return_value={"passed": False, "failures": ["directional"]},
            ),
        ):
            run = pilot._run_two_stage(loaded, prepare, pilot.ExecutionProgress())
        self.assertEqual(run["optimizer_steps_completed"], 33)
        self.assertEqual(
            sorted(map(int, run["stage_2_full_diagnostics"])),
            list(pilot.DIAGNOSTIC_UPDATE_ORDINALS),
        )
        self.assertEqual(len(run["stage_2_update_summaries"]), 32)
        self.assertFalse(run["terminal_offline_gates"]["accepted_before_checkpoint_validation"])

    def test_safety_failure_stops_immediately(self) -> None:
        calls = 0

        def safety(*args, **kwargs):
            nonlocal calls
            calls += 1
            result = self._fake_safety(*args, **kwargs)
            if kwargs.get("stage_2_update_ordinal") == 3:
                result.update(
                    {"safety_pass": False, "hard_stop": True, "global_failures": ["safety"]}
                )
            return result

        model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
        value_identity = {
            "all_rows_byte_exact_to_initial": True,
            "raw_value_mse_exact_to_initial": True,
        }
        with (
            mock.patch.object(pilot, "raw_value_mse", return_value=0.0),
            mock.patch.object(pilot, "_stage_full_batch_step", side_effect=self._fake_step),
            mock.patch.object(pilot, "_measure_stage", return_value=[]),
            mock.patch.object(pilot, "value_change_summary", return_value=value_identity),
            mock.patch.object(pilot, "evaluate_stage_gates", side_effect=safety),
        ):
            run = pilot._run_two_stage(
                {"model": model}, {"rows": []}, pilot.ExecutionProgress()
            )
        self.assertEqual(calls, 4)  # Stage 1 plus Stage-2 updates 1, 2, and 3.
        self.assertEqual(run["optimizer_steps_completed"], 4)
        self.assertEqual(run["safety_stop_after_stage_2_update"], 3)
        self.assertEqual(sorted(map(int, run["stage_2_full_diagnostics"])), [1, 2])

    def test_one_post_stage1_snapshot_and_pre_post_measurement_allowlists(self) -> None:
        snapshot_ids: list[int] = []
        snapshot_hashes: list[str] = []

        def step(**kwargs):
            if kwargs["stage"] == 2:
                snapshot = kwargs["stage_2_start_parameters"]
                snapshot_ids.append(id(snapshot))
                snapshot_hashes.append(
                    pilot.canonical_sha256(
                        {
                            name: pilot._tensor_sha256(value)
                            for name, value in snapshot.items()
                        }
                    )
                )
            return self._fake_step(**kwargs)

        model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
        value_identity = {
            "all_rows_byte_exact_to_initial": True,
            "raw_value_mse_exact_to_initial": True,
        }
        with (
            mock.patch.object(pilot, "raw_value_mse", return_value=0.0),
            mock.patch.object(pilot, "_stage_full_batch_step", side_effect=step),
            mock.patch.object(pilot, "_measure_stage", return_value=[]),
            mock.patch.object(pilot, "value_change_summary", return_value=value_identity),
            mock.patch.object(pilot, "evaluate_stage_gates", side_effect=self._fake_safety),
            mock.patch.object(
                pilot,
                "evaluate_directional_gates",
                return_value={"passed": True, "failures": []},
            ),
        ):
            run = pilot._run_two_stage(
                {"model": model}, {"rows": []}, pilot.ExecutionProgress()
            )
        self.assertEqual(len(snapshot_ids), 32)
        self.assertEqual(len(set(snapshot_ids)), 1)
        self.assertEqual(len(set(snapshot_hashes)), 1)
        timing = run["stage_2_update_summaries"][0]["measurement_timing"]
        self.assertEqual(
            set(timing["pre_step"]),
            {
                "loss", "policy_loss", "anchor_kl_contribution", "entropy",
                "gradient_norm_before_clipping",
                "per_parameter_gradient_norm_before_clipping",
                "per_parameter_gradient_norm_after_clipping",
            },
        )
        self.assertEqual(
            set(timing["post_step"]),
            {
                "optimizer_state_steps", "parameter_diffs_from_initial",
                "parameter_diffs_from_fixed_stage_2_start",
                "parameter_diffs_from_previous_step", "safety",
                "ordered_probability_bytes_sha256", "ordered_value_bytes_sha256",
            },
        )

    def test_pre_step_failure_after_prior_steps_preserves_historical_count(self) -> None:
        calls = 0

        def step(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise RuntimeError("before update two optimizer step")
            return self._fake_step(**kwargs)

        model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
        progress = pilot.ExecutionProgress()
        value_identity = {
            "all_rows_byte_exact_to_initial": True,
            "raw_value_mse_exact_to_initial": True,
        }
        with (
            mock.patch.object(pilot, "raw_value_mse", return_value=0.0),
            mock.patch.object(pilot, "_stage_full_batch_step", side_effect=step),
            mock.patch.object(pilot, "_measure_stage", return_value=[]),
            mock.patch.object(pilot, "value_change_summary", return_value=value_identity),
            mock.patch.object(pilot, "evaluate_stage_gates", side_effect=self._fake_safety),
        ):
            with self.assertRaisesRegex(RuntimeError, "before update two"):
                pilot._run_two_stage({"model": model}, {"rows": []}, progress)
        self.assertEqual(progress.optimizer_steps_completed, 2)
        self.assertEqual(progress.stage_2_updates_completed, 1)
        self.assertEqual(progress.failure_phase, "stage_2_update_2_full_batch_step")


class InteractionMaturationDirectionalBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt = _blocked_prepare_v2()
        cls.metrics = _passing_directional_metrics(cls.receipt)
        result = pilot.evaluate_directional_gates(cls.receipt, cls.metrics, stage=2)
        if not result["passed"]:
            raise AssertionError(result)

    def test_production_membership_validator_rejects_every_shape_mutation_before_metrics(self) -> None:
        confirmed = deepcopy(self.receipt)
        for name in pilot.DIRECTIONAL_MEMBERSHIP_KEYS:
            confirmed["directional_memberships"][name] = [
                confirmed["directional_memberships"][name][0]
            ]
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            pilot.evaluate_directional_gates(
                confirmed, _ExplodingMetrics(), stage=2
            )

        for membership_name in pilot.DIRECTIONAL_MEMBERSHIP_KEYS:
            original = self.receipt["directional_memberships"][membership_name]
            outside = next(
                ordinal
                for ordinal in range(pilot.EXPECTED_ON_POLICY_ROWS)
                if ordinal not in original
            )
            mutations = {
                "remove": original[:-1],
                "add": sorted([*original, outside]),
                "reorder": list(reversed(original)),
                "duplicate": sorted([*original[:-1], original[-2]]),
                "type": ["0", *original[1:]],
                "out_of_range": [*original[:-1], pilot.EXPECTED_ON_POLICY_ROWS],
            }
            for mutation_name, values in mutations.items():
                with self.subTest(
                    membership=membership_name, mutation=mutation_name
                ):
                    candidate = deepcopy(self.receipt)
                    candidate["directional_memberships"][membership_name] = values
                    with self.assertRaises(ValueError):
                        pilot.evaluate_directional_gates(
                            candidate, _ExplodingMetrics(), stage=2
                        )
        for mutation_name, mutate in {
            "missing_key": lambda value: value.pop("teacher_end_ordinals"),
            "extra_key": lambda value: value.update({"extra": []}),
        }.items():
            with self.subTest(mutation=mutation_name):
                candidate = deepcopy(self.receipt)
                mutate(candidate["directional_memberships"])
                with self.assertRaisesRegex(ValueError, "exactly five keys"):
                    pilot.evaluate_directional_gates(
                        candidate, _ExplodingMetrics(), stage=2
                    )

    def test_production_membership_validator_recomputes_from_prepare_rows(self) -> None:
        memberships = self.receipt["directional_memberships"]
        mutations = {
            "teacher_index": (
                memberships["teacher_end_ordinals"][0],
                lambda row: row.update(
                    {
                        "teacher_index": next(
                            index
                            for index in range(row["legal_option_count"])
                            if index != row["end_index"]
                        )
                    }
                ),
            ),
            "sampled_index": (
                memberships["teacher_end_and_sampled_end_ordinals"][0],
                lambda row: row.update(
                    {
                        "sampled_index": next(
                            index
                            for index in range(row["legal_option_count"])
                            if index != row["end_index"]
                        )
                    }
                ),
            ),
            "normalized_sign": (
                memberships[
                    "positive_normalized_teacher_and_sampled_end_ordinals"
                ][0],
                lambda row: row.update(
                    {"fixed_normalized_advantage_float32": -1.0}
                ),
            ),
            "raw_sign": (
                memberships["positive_raw_teacher_and_sampled_end_ordinals"][0],
                lambda row: row.update({"raw_advantage_float64": -1.0}),
            ),
        }
        for name, (ordinal, mutate) in mutations.items():
            with self.subTest(name=name, ordinal=ordinal):
                candidate = deepcopy(self.receipt)
                mutate(candidate["rows"][ordinal])
                with self.assertRaises(ValueError):
                    pilot.evaluate_directional_gates(
                        candidate, _ExplodingMetrics(), stage=2
                    )
        authoritative = pilot._validated_directional_memberships(
            self.receipt["rows"], self.receipt["directional_memberships"]
        )
        self.assertEqual(
            [len(authoritative[name]) for name in pilot.DIRECTIONAL_MEMBERSHIP_KEYS],
            [4, 20, 31, 41, 43],
        )

    def test_production_gate_all_four_negative_boundaries_and_argmax(self) -> None:
        for ordinal in self.receipt["directional_memberships"][
            "negative_target_ordinals"
        ]:
            row = self.receipt["rows"][ordinal]
            end = int(row["end_index"])
            teacher = int(row["teacher_index"])
            end_initial = float(row["initial_probabilities_float32"][end])
            teacher_initial = float(row["initial_probabilities_float32"][teacher])
            end_pass, end_fail = _highest_float32_delta_at_most(
                end_initial, -1e-6
            )
            teacher_pass, teacher_fail = _lowest_float32_delta_at_least(
                teacher_initial, 1e-6
            )
            for name, index, passing, failing, failure in (
                ("end", end, end_pass, end_fail, f"negative:{ordinal}:end_decrease"),
                (
                    "teacher", teacher, teacher_pass, teacher_fail,
                    f"negative:{ordinal}:teacher_increase",
                ),
            ):
                with self.subTest(ordinal=ordinal, boundary=name):
                    metrics = deepcopy(self.metrics)
                    metrics[ordinal]["probabilities_float32"][index] = passing
                    passed = pilot.evaluate_directional_gates(
                        self.receipt, metrics, stage=2
                    )
                    self.assertNotIn(failure, passed["failures"])
                    metrics[ordinal]["probabilities_float32"][index] = failing
                    failed = pilot.evaluate_directional_gates(
                        self.receipt, metrics, stage=2
                    )
                    self.assertIn(failure, failed["failures"])
            with self.subTest(ordinal=ordinal, boundary="unique_argmax"):
                metrics = deepcopy(self.metrics)
                competitor = max(
                    (index for index in range(row["legal_option_count"]) if index != teacher),
                    key=lambda index: metrics[ordinal]["probabilities_float32"][index],
                )
                tie = metrics[ordinal]["probabilities_float32"][teacher]
                metrics[ordinal]["probabilities_float32"][competitor] = tie
                failure = f"negative:{ordinal}:teacher_unique_argmax"
                self.assertIn(
                    failure,
                    pilot.evaluate_directional_gates(
                        self.receipt, metrics, stage=2
                    )["failures"],
                )
                metrics[ordinal]["probabilities_float32"][teacher] = float(
                    torch.nextafter(
                        torch.tensor(tie, dtype=torch.float32),
                        torch.tensor(float("inf"), dtype=torch.float32),
                    )
                )
                self.assertNotIn(
                    failure,
                    pilot.evaluate_directional_gates(
                        self.receipt, metrics, stage=2
                    )["failures"],
                )

    def test_production_gate_all_twenty_positive_normalized_boundaries(self) -> None:
        for ordinal in self.receipt["directional_memberships"][
            "positive_normalized_teacher_and_sampled_end_ordinals"
        ]:
            row = self.receipt["rows"][ordinal]
            end = int(row["end_index"])
            passing, failing = _lowest_float32_delta_at_least(
                float(row["initial_probabilities_float32"][end]), 1e-6
            )
            failure = f"legitimate_end:{ordinal}:normalized_increase"
            with self.subTest(ordinal=ordinal):
                metrics = deepcopy(self.metrics)
                metrics[ordinal]["probabilities_float32"][end] = passing
                self.assertNotIn(
                    failure,
                    pilot.evaluate_directional_gates(
                        self.receipt, metrics, stage=2
                    )["failures"],
                )
                metrics[ordinal]["probabilities_float32"][end] = failing
                result = pilot.evaluate_directional_gates(
                    self.receipt, metrics, stage=2
                )
                self.assertIn(failure, result["failures"])

    def test_production_gate_raw_lower_median_and_outsider_poison(self) -> None:
        raw = self.receipt["directional_memberships"][
            "positive_raw_teacher_and_sampled_end_ordinals"
        ]
        metrics = deepcopy(self.metrics)
        for ordinal in raw[:16]:
            row = self.receipt["rows"][ordinal]
            metrics[ordinal]["probabilities_float32"][row["end_index"]] = row[
                "initial_probabilities_float32"
            ][row["end_index"]]
        median_failure = "legitimate_end:positive_raw_lower_median"
        self.assertIn(
            median_failure,
            pilot.evaluate_directional_gates(
                self.receipt, metrics, stage=2
            )["failures"],
        )
        for ordinal in raw[:16]:
            row = self.receipt["rows"][ordinal]
            end = int(row["end_index"])
            metrics[ordinal]["probabilities_float32"][end] = float(
                torch.nextafter(
                    torch.tensor(
                        row["initial_probabilities_float32"][end],
                        dtype=torch.float32,
                    ),
                    torch.tensor(float("inf"), dtype=torch.float32),
                )
            )
        self.assertNotIn(
            median_failure,
            pilot.evaluate_directional_gates(
                self.receipt, metrics, stage=2
            )["failures"],
        )

        all_bound = set().union(
            *(set(self.receipt["directional_memberships"][name]) for name in pilot.DIRECTIONAL_MEMBERSHIP_KEYS)
        )
        outsider = next(
            ordinal
            for ordinal, row in enumerate(self.receipt["rows"])
            if ordinal not in all_bound
            and row["legal_option_count"] > 1
            and row["initial_probabilities_float32"][row["end_index"]] > 0.01
        )
        poisoned = deepcopy(self.metrics)
        outsider_row = self.receipt["rows"][outsider]
        outsider_end = int(outsider_row["end_index"])
        outsider_receiver = next(
            index
            for index in range(outsider_row["legal_option_count"])
            if index != outsider_end
        )
        poisoned[outsider]["probabilities_float32"] = _shift_float32(
            poisoned[outsider]["probabilities_float32"],
            outsider_end,
            outsider_receiver,
            0.005,
        )
        baseline = pilot.evaluate_directional_gates(
            self.receipt, self.metrics, stage=2
        )
        self.assertEqual(
            pilot.evaluate_directional_gates(
                self.receipt, poisoned, stage=2
            ),
            baseline,
        )
        raw_only = next(
            ordinal
            for ordinal in raw
            if ordinal
            not in self.receipt["directional_memberships"][
                "positive_normalized_teacher_and_sampled_end_ordinals"
            ]
        )
        inside = deepcopy(self.metrics)
        inside_row = self.receipt["rows"][raw_only]
        inside_end = int(inside_row["end_index"])
        inside_receiver = next(
            index
            for index in range(inside_row["legal_option_count"])
            if index != inside_end
        )
        inside[raw_only]["probabilities_float32"] = _shift_float32(
            inside[raw_only]["probabilities_float32"],
            inside_end,
            inside_receiver,
            0.0036,
        )
        self.assertIn(
            "legitimate_end:positive_raw_maximum_decrease",
            pilot.evaluate_directional_gates(
                self.receipt, inside, stage=2
            )["failures"],
        )

    def test_production_gate_breaks_each_of_43_teacher_end_argmax_controls(self) -> None:
        for ordinal in self.receipt["directional_memberships"][
            "teacher_end_ordinals"
        ]:
            row = self.receipt["rows"][ordinal]
            end = int(row["end_index"])
            competitor = max(
                (index for index in range(row["legal_option_count"]) if index != end),
                key=lambda index: self.metrics[ordinal]["probabilities_float32"][index],
            )
            metrics = deepcopy(self.metrics)
            metrics[ordinal]["probabilities_float32"][competitor] = metrics[
                ordinal
            ]["probabilities_float32"][end]
            failure = f"legitimate_end:{ordinal}:unique_argmax"
            with self.subTest(ordinal=ordinal):
                self.assertIn(
                    failure,
                    pilot.evaluate_directional_gates(
                        self.receipt, metrics, stage=2
                    )["failures"],
                )

    def test_all_four_negative_target_rows_use_inclusive_boundaries(self) -> None:
        for ordinal in (158, 260, 547, 812):
            with self.subTest(ordinal=ordinal):
                self.assertTrue(pilot._negative_end_decrease_passes(-1e-6))
                self.assertFalse(
                    pilot._negative_end_decrease_passes(-1e-6 + 1e-15)
                )
                self.assertTrue(pilot._teacher_probability_increase_passes(1e-6))
                self.assertFalse(
                    pilot._teacher_probability_increase_passes(1e-6 - 1e-15)
                )

    def test_all_twenty_positive_normalized_end_rows_are_inclusive(self) -> None:
        for ordinal in range(20):
            with self.subTest(ordinal=ordinal):
                self.assertTrue(
                    pilot._positive_normalized_end_increase_passes(1e-6)
                )
                self.assertFalse(
                    pilot._positive_normalized_end_increase_passes(1e-6 - 1e-15)
                )

    def test_positive_raw_median_is_strict_and_maximum_uses_only_31_rows(self) -> None:
        boundary = [0.0] * 16 + [0.01] * 15
        self.assertEqual(len(boundary), 31)
        self.assertFalse(
            pilot._positive_raw_lower_median_passes(
                pilot.lower_empirical_median(boundary)
            )
        )
        passing = [1e-15] * 16 + [0.01] * 15
        self.assertTrue(
            pilot._positive_raw_lower_median_passes(
                pilot.lower_empirical_median(passing)
            )
        )
        same_population = [0.0] * 30 + [-0.0025]
        maximum_decrease = max(max(0.0, -value) for value in same_population)
        self.assertTrue(
            pilot._positive_raw_maximum_decrease_passes(maximum_decrease)
        )
        outside_row_not_in_population = -0.5
        self.assertEqual(
            max(max(0.0, -value) for value in same_population), 0.0025
        )
        self.assertEqual(outside_row_not_in_population, -0.5)
        self.assertFalse(
            pilot._positive_raw_maximum_decrease_passes(0.0025 + 1e-15)
        )

    def test_all_43_teacher_end_rows_require_unique_end_argmax(self) -> None:
        for ordinal in range(43):
            with self.subTest(ordinal=ordinal):
                self.assertEqual(pilot.inherited._unique_argmax([0.25, 0.75], 1), 1)
                with self.assertRaises(ValueError):
                    pilot.inherited._unique_argmax([0.5, 0.5], 1)


class InteractionMaturationTimingSemanticTests(unittest.TestCase):
    def test_full_shaped_32_record_chain_passes_with_and_without_reconstruction(self) -> None:
        training = _full_compact_chain()
        self.assertEqual(
            pilot.validate_compact_update_chain(training)["status"], "pass"
        )
        self.assertTrue(
            pilot.validate_compact_update_chain(
                training,
                independent_reconstruction=deepcopy(
                    training["stage_2_update_summaries"]
                ),
            )["independent_reconstruction_compared"]
        )
        fixed_aliases = [
            record["measurement_timing"]["post_step"][
                "parameter_diffs_from_fixed_stage_2_start"
            ]
            for record in training["stage_2_update_summaries"]
        ]
        self.assertEqual(
            {pilot.canonical_sha256(value) for value in fixed_aliases},
            {pilot.canonical_sha256([{"sentinel": "fixed-post-stage1"}])},
        )

    def test_rehashed_swapped_timing_rejects_with_or_without_reconstruction(self) -> None:
        for independent in (False, True):
            with self.subTest(independent=independent):
                training = _full_compact_chain()
                for record in training["stage_2_update_summaries"]:
                    timing = record["measurement_timing"]
                    timing["pre_step"], timing["post_step"] = (
                        timing["post_step"], timing["pre_step"]
                    )
                _relink_compact_chain(training)
                reconstruction = (
                    deepcopy(training["stage_2_update_summaries"])
                    if independent else None
                )
                with self.assertRaises(ValueError):
                    pilot.validate_compact_update_chain(
                        training, independent_reconstruction=reconstruction
                    )

    def test_all_fourteen_aliases_are_canonical_byte_exact(self) -> None:
        for phase, alias, _top in pilot.STAGE2_TIMING_BINDINGS:
            with self.subTest(phase=phase, alias=alias):
                training = _full_compact_chain()
                training["stage_2_update_summaries"][0]["measurement_timing"][
                    phase
                ][alias] = {"wrong_phase_sentinel": alias}
                _relink_compact_chain(training)
                with self.assertRaisesRegex(ValueError, "alias mismatch"):
                    pilot.validate_compact_update_chain(training)

    def test_timing_missing_extra_wrong_type_and_fixed_start_alias_reject(self) -> None:
        mutations = {
            "missing_timing": lambda record: record.pop("measurement_timing"),
            "extra_timing": lambda record: record["measurement_timing"].update(
                {"extra": {}}
            ),
            "timing_nonmapping": lambda record: record.update(
                {"measurement_timing": []}
            ),
            "pre_nonmapping": lambda record: record["measurement_timing"].update(
                {"pre_step": []}
            ),
            "post_nonmapping": lambda record: record["measurement_timing"].update(
                {"post_step": []}
            ),
            "missing_pre_field": lambda record: record["measurement_timing"][
                "pre_step"
            ].pop("loss"),
            "extra_post_field": lambda record: record["measurement_timing"][
                "post_step"
            ].update({"extra": 1}),
            "fixed_start_previous_delta": lambda record: record[
                "measurement_timing"
            ]["post_step"].update(
                {
                    "parameter_diffs_from_fixed_stage_2_start": record[
                        "parameter_diffs_from_previous_step"
                    ]
                }
            ),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                training = _full_compact_chain()
                mutation(training["stage_2_update_summaries"][1])
                _relink_compact_chain(training)
                with self.assertRaises((ValueError, TypeError)):
                    pilot.validate_compact_update_chain(training)
        for key_name in ("loss", "measurement_timing"):
            for mode in ("missing", "extra"):
                with self.subTest(record_key=key_name, mode=mode):
                    training = _full_compact_chain()
                    record = training["stage_2_update_summaries"][0]
                    if mode == "missing":
                        record.pop(key_name)
                    else:
                        record[f"extra_{key_name}"] = True
                    _relink_compact_chain(training)
                    with self.assertRaises(ValueError):
                        pilot.validate_compact_update_chain(training)


class InteractionMaturationCorrectionTests(unittest.TestCase):
    def test_all_eleven_authoritative_hashes_and_remediated_schema_bind(self) -> None:
        self.assertEqual(pilot._load_plan()["plan_id"], pilot.PLAN_ID)
        self.assertEqual(pilot._load_correction()["correction_id"], pilot.CORRECTION_ID)
        correction_v2 = pilot._load_correction_v2()
        self.assertEqual(correction_v2["correction_id"], pilot.CORRECTION_V2_ID)
        chain = correction_v2["clarifications"]["execution_spec_correction_chain"]
        self.assertEqual(chain["key_count_exact"], 28)
        self.assertEqual(
            chain["schema_version"],
            "actor-only-interaction-maturation-execution-spec-v2",
        )
        remediation = pilot._load_prepare_audit_remediation()
        self.assertEqual(
            remediation["remediation_id"], pilot.PREPARE_AUDIT_REMEDIATION_ID
        )
        override = remediation["execution_spec_override"]
        self.assertEqual(override["key_count_exact"], 30)
        self.assertEqual(
            override["schema_version"],
            "actor-only-interaction-maturation-execution-spec-v3",
        )
        self.assertEqual(
            pilot._load_prepare_audit_remediation_v2()["execution_spec_override"][
                "key_count_exact"
            ],
            32,
        )
        self.assertEqual(
            pilot._load_prepare_audit_remediation_v3()["execution_spec_override"][
                "key_count_exact"
            ],
            34,
        )
        self.assertEqual(
            pilot._load_prepare_audit_remediation_v4()["execution_spec_override"][
                "exact_top_level_keys"
            ],
            list(pilot.EXECUTION_SPEC_V6_TOP_LEVEL_KEYS),
        )
        self.assertEqual(
            pilot._load_prepare_audit_remediation_v5()["execution_spec_override"][
                "exact_top_level_keys"
            ],
            list(pilot.EXECUTION_SPEC_V7_TOP_LEVEL_KEYS),
        )
        self.assertEqual(
            pilot._load_prepare_audit_remediation_v6()["execution_spec_override"][
                "exact_top_level_keys"
            ],
            list(pilot.EXECUTION_SPEC_V8_TOP_LEVEL_KEYS),
        )
        self.assertEqual(
            pilot._load_prepare_audit_remediation_v7()["execution_spec_override"][
                "exact_top_level_keys"
            ],
            list(pilot.EXECUTION_SPEC_V9_TOP_LEVEL_KEYS),
        )
        self.assertEqual(
            pilot._load_prepare_audit_remediation_v8()["execution_spec_override"][
                "exact_top_level_keys"
            ],
            list(pilot.EXECUTION_SPEC_TOP_LEVEL_KEYS),
        )
        self.assertEqual(len(pilot._contract_bindings()), 22)

    def test_tagged_nonfinite_is_canonical_and_malformed_or_accepted_fails(self) -> None:
        raw = {"diagnostic": [float("nan"), float("inf"), -float("inf")]}
        encoded, evidence = pilot.encode_nonfinite_for_canonical_json(raw)
        pilot.validate_nonfinite_encoding(
            encoded, evidence=evidence, accepted_receipt=False
        )
        pilot.canonical_json_bytes(encoded)
        with self.assertRaises(ValueError):
            pilot.validate_nonfinite_encoding(
                raw, evidence=None, accepted_receipt=False
            )
        with self.assertRaises(ValueError):
            pilot.validate_nonfinite_encoding(
                encoded, evidence=evidence, accepted_receipt=True
            )
        malformed = deepcopy(encoded)
        malformed["diagnostic"][0]["dtype"] = "float16"
        with self.assertRaises(ValueError):
            pilot.validate_nonfinite_encoding(
                malformed, evidence=evidence, accepted_receipt=False
            )

    @staticmethod
    def _one_row_metric(probabilities: list[float]) -> tuple[dict, dict]:
        fixed = {
            "ppo_row_ordinal": 0,
            "public_state_sha256": "A" * 64,
            "behavior_action_order_sha256": "B" * 64,
            "sampled_index": 0,
            "teacher_index": 0,
            "end_index": 1,
            "sampled_option_type": 7,
            "sampled_semantic_identity": "synthetic",
            "legal_option_count": 2,
            "initial_probabilities_float32": [0.5, 0.5],
            "fixed_normalized_advantage_float32": 1.0,
            "initial_value_float32": 0.25,
            "initial_value_raw_bytes_hex": pilot._tensor_bytes(
                torch.tensor(0.25, dtype=torch.float32)
            ).hex().upper(),
            "initial_value_byte_sha256": pilot._tensor_sha256(
                torch.tensor(0.25, dtype=torch.float32)
            ),
        }
        probability_tensor = torch.tensor(probabilities, dtype=torch.float32)
        stored = [float(value) for value in probability_tensor.tolist()]
        raw = pilot._tensor_bytes(probability_tensor)
        delta = stored[0] - 0.5
        value_raw = pilot._tensor_bytes(torch.tensor(0.25, dtype=torch.float32))
        metric = {
            "ppo_row_ordinal": 0,
            "public_state_sha256": fixed["public_state_sha256"],
            "behavior_action_order_sha256": fixed["behavior_action_order_sha256"],
            "sampled_index": 0,
            "teacher_index": 0,
            "end_index": 1,
            "legal_option_count": 2,
            "sampled_option_type": 7,
            "sampled_semantic_identity": "synthetic",
            "probabilities_float32": stored,
            "probabilities_raw_bytes_hex": raw.hex().upper(),
            "probabilities_byte_sha256": pilot.hashlib.sha256(raw).hexdigest().upper(),
            "value_float32": 0.25,
            "value_raw_bytes_hex": value_raw.hex().upper(),
            "value_byte_sha256": pilot.hashlib.sha256(value_raw).hexdigest().upper(),
            "value_output_byte_exact_to_initial": True,
            "unique_argmax_index": 0 if stored[0] > stored[1] else 1,
            "sampled_probability_delta_from_initial": delta,
            "oriented_sampled_probability_delta": delta,
            "orientation": pilot.orientation_class(delta),
            "anchor_kl_post_to_zero": (
                pilot.inherited.per_row_anchor_kl(stored, [0.5, 0.5])
                if all(value > 0.0 for value in stored) else 0.0
            ),
            "total_variation_from_initial": 0.5
            * math.fsum(abs(value - initial) for value, initial in zip(stored, [0.5, 0.5])),
        }
        return fixed, metric

    def test_probability_domain_and_normalization_boundaries(self) -> None:
        half_bits = torch.tensor(0.5, dtype=torch.float32).view(torch.int32)
        at_boundary = float((half_bits + 16).view(torch.float32))
        above_boundary = float((half_bits + 17).view(torch.float32))
        fixed, boundary = self._one_row_metric([0.5, at_boundary])
        with mock.patch.object(pilot, "EXPECTED_ON_POLICY_ROWS", 1):
            _, failures, _ = pilot._validated_metric_rows(
                {"rows": [fixed]}, [boundary]
            )
        self.assertNotIn("row:0:probability_normalization", failures)
        _, beyond = self._one_row_metric([0.5, above_boundary])
        with mock.patch.object(pilot, "EXPECTED_ON_POLICY_ROWS", 1):
            _, failures, _ = pilot._validated_metric_rows({"rows": [fixed]}, [beyond])
        self.assertIn("row:0:probability_normalization", failures)
        for probabilities in ([0.0, 1.0], [-0.1, 1.1], [1.1, 0.0]):
            _, metric = self._one_row_metric(list(probabilities))
            with self.subTest(probabilities=probabilities), mock.patch.object(
                pilot, "EXPECTED_ON_POLICY_ROWS", 1
            ):
                _, failures, _ = pilot._validated_metric_rows(
                    {"rows": [fixed]}, [metric]
                )
                self.assertIn("row:0:probability_domain", failures)
        short = deepcopy(boundary)
        short["probabilities_float32"] = [1.0]
        with mock.patch.object(pilot, "EXPECTED_ON_POLICY_ROWS", 1):
            _, failures, _ = pilot._validated_metric_rows({"rows": [fixed]}, [short])
        self.assertIn("row:0:probability_dimension", failures)

    def test_extra_precision_that_collapses_to_float32_tie_is_rejected(self) -> None:
        fixed, metric = self._one_row_metric([0.5, 0.5])
        metric["probabilities_float32"] = [
            0.5000000000000001,
            0.4999999999999999,
        ]
        with mock.patch.object(pilot, "EXPECTED_ON_POLICY_ROWS", 1):
            _, failures, _ = pilot._validated_metric_rows(
                {"rows": [fixed]}, [metric]
            )
        self.assertIn("row:0:probability_float32_roundtrip", failures)

    def test_value_one_bit_difference_fails_identity(self) -> None:
        fixed, metric = self._one_row_metric([0.6, 0.4])
        forged = torch.tensor(0.25, dtype=torch.float32).view(torch.int32)
        forged = (forged + 1).view(torch.float32)
        raw = pilot._tensor_bytes(forged)
        metric["value_float32"] = float(forged)
        metric["value_raw_bytes_hex"] = raw.hex().upper()
        metric["value_byte_sha256"] = pilot.hashlib.sha256(raw).hexdigest().upper()
        metric["value_output_byte_exact_to_initial"] = False
        with mock.patch.object(pilot, "EXPECTED_ON_POLICY_ROWS", 1):
            _, failures, _ = pilot._validated_metric_rows({"rows": [fixed]}, [metric])
        self.assertIn("row:0:value_identity", failures)

    def test_compact_chain_never_claims_absent_nonmilestone_rows(self) -> None:
        training = _full_compact_chain()
        summaries = training["stage_2_update_summaries"]
        result = pilot.validate_compact_update_chain(
            training, independent_reconstruction=deepcopy(summaries)
        )
        self.assertFalse(result["full_raw_rows_claimed_for_nonmilestones"])
        changed = deepcopy(summaries)
        changed[5]["raw_rows_persisted"] = True
        with self.assertRaises(ValueError):
            pilot.validate_compact_update_chain(
                training, independent_reconstruction=changed
            )

    def test_checkpoint_identity_failure_creates_no_canonical_status(self) -> None:
        model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
        pilot._set_trainability(model, stage=1)
        optimizer = pilot._new_actor_adam(model)
        loaded = {
            "checkpoint_path": pilot._repo_path(pilot.INPUT_CHECKPOINT_RELATIVE_PATH),
            "source_hashes": pilot.inherited.checkpoint_source_hashes(),
            "model": model,
        }
        run = {
            "model": model,
            "optimizer": optimizer,
            "optimizer_steps_completed": 1,
            "raw_value_mse_initial": 0.0,
            "safety_stop": True,
            "terminal_offline_gates": None,
        }
        test_root = pilot._repo_path(pilot.IMPLEMENTATION_RELATIVE_PATH) / "test_outputs"
        test_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=test_root) as temporary:
            output = Path(temporary) / "output"

            def fake_run(_loaded, _probe, progress):
                progress.model = model
                progress.optimizer = optimizer
                progress.optimizer_steps_completed = 1
                return run

            with (
                mock.patch.object(pilot.inherited, "_runtime_identity", return_value={}),
                mock.patch.object(pilot, "_load_execution_spec", return_value={}),
                mock.patch.object(
                    pilot, "_validate_execution_boundary", return_value=({"receipt_sha256": "A" * 64, "training_contract": {}}, output)
                ),
                mock.patch.object(pilot.inherited, "_load_validated_inputs", return_value=loaded),
                mock.patch.object(pilot, "_build_authorized_execution_fixed_inputs", return_value={}),
                mock.patch.object(pilot, "_run_two_stage", side_effect=fake_run),
                mock.patch.object(
                    pilot,
                    "_publish_checkpoint_exact",
                    side_effect=OSError("identity establishment failed"),
                ),
            ):
                with self.assertRaisesRegex(OSError, "identity establishment"):
                    pilot.execute(
                        execution_spec=Path(temporary) / "spec.json",
                        execution_spec_sha256="B" * 64,
                    )
            self.assertFalse((output / "candidate.pt").exists())
            self.assertFalse((output / "REJECTED").exists())
            self.assertFalse((output / "rejected_receipt.json").exists())


class InteractionMaturationPublicationContractTests(unittest.TestCase):
    def test_real_execution_output_preflight_confinement_rejects_before_adam(self) -> None:
        runtime = {"runtime": "pinned"}
        implementation = {
            "definition": "test",
            "file_count": 1,
            "sha256": "C" * 64,
            "files": [],
        }
        receipt = {
            "receipt_sha256": "B" * 64,
            "implementation": {"path": "candidate", **implementation},
            "runtime_thread_receipt": runtime,
            "training_contract": {},
            "diagnostic_contract": {},
            "safety_gates": {},
            "terminal_offline_acceptance": {},
        }

        def exercise(value: str, *, existing: str | None = None, reparse=False):
            test_root = pilot._repo_path(pilot.IMPLEMENTATION_RELATIVE_PATH) / "test_outputs"
            test_root.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(dir=test_root) as temporary:
                fake_repo = Path(temporary) / "repo"
                analysis = fake_repo  / "_local_generated" / "analysis_outputs"
                analysis.mkdir(parents=True)
                fixed_output = fake_repo / Path(
                    pilot.APPROVED_OUTPUT_RELATIVE_PATH.as_posix()
                )
                if existing == "file":
                    fixed_output.write_bytes(b"occupied")
                elif existing == "directory":
                    fixed_output.mkdir()
                spec_path = fake_repo / "execution.json"
                prepare_path = fake_repo / "prepare.json"
                spec = {
                    "prepare_receipt_path": "prepare.json",
                    "prepare_receipt_file_sha256": "A" * 64,
                    "prepare_receipt_sha256": receipt["receipt_sha256"],
                    "implementation_snapshot_sha256": implementation["sha256"],
                    "runtime_thread_receipt": runtime,
                    "training_contract": {},
                    "diagnostic_contract": {},
                    "safety_gates": {},
                    "terminal_offline_acceptance": {},
                    "output_directory": value,
                }

                def fake_repo_path(relative):
                    return fake_repo / Path(PurePosixPath(relative).as_posix())

                patches = (
                    mock.patch.object(pilot, "find_repo_root", return_value=fake_repo),
                    mock.patch.object(pilot, "_repo_path", side_effect=fake_repo_path),
                    mock.patch.object(
                        pilot.inherited, "_resolve_pinned_path", return_value=prepare_path
                    ),
                    mock.patch.object(
                        pilot, "_validate_prepare_output_path", return_value=prepare_path
                    ),
                    mock.patch.object(
                        pilot.inherited, "_load_hashed_json", return_value=receipt
                    ),
                    mock.patch.object(pilot, "validate_prepare_receipt"),
                    mock.patch.object(
                        pilot.inherited,
                        "implementation_snapshot",
                        return_value=implementation,
                    ),
                    mock.patch.object(pilot, "_build_prepare_receipt", return_value=receipt),
                )
                with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], mock.patch.object(
                    torch.optim,
                    "Adam",
                    side_effect=AssertionError("optimizer constructed during preflight"),
                ) as adam:
                    if reparse:
                        with mock.patch.object(
                            pilot.inherited,
                            "_is_link_or_reparse",
                            side_effect=lambda path: Path(path).absolute() == analysis.absolute(),
                        ):
                            with self.assertRaises(ValueError):
                                pilot._validate_execution_boundary(
                                    spec, runtime, execution_spec_path=spec_path
                                )
                    elif value == pilot.APPROVED_OUTPUT_RELATIVE_PATH.as_posix() and existing is None:
                        probe, output = pilot._validate_execution_boundary(
                            spec, runtime, execution_spec_path=spec_path
                        )
                        self.assertIs(probe, receipt)
                        self.assertEqual(output, fixed_output.absolute())
                    else:
                        with self.assertRaises((ValueError, FileExistsError)):
                            pilot._validate_execution_boundary(
                                spec, runtime, execution_spec_path=spec_path
                            )
                    self.assertEqual(adam.call_count, 0)

        fixed = pilot.APPROVED_OUTPUT_RELATIVE_PATH.as_posix()
        exercise(fixed)
        for existing in ("file", "directory"):
            with self.subTest(existing=existing):
                exercise(fixed, existing=existing)
        for name, value in {
            "dot": "_local_generated/analysis_outputs/./candidate",
            "dotdot": "_local_generated/analysis_outputs/../candidate",
            "empty_component": "_local_generated/analysis_outputs//candidate",
            "backslash": "_local_generated\analysis_outputs\\candidate",
            "escape": "../analysis_outputs/candidate",
            "wrong_safe": "_local_generated/analysis_outputs/wrong_candidate",
        }.items():
            with self.subTest(name=name):
                exercise(value)
        exercise(fixed, reparse=True)

    def test_preflight_failure_creates_no_artifact_and_no_optimizer(self) -> None:
        test_root = pilot._repo_path(pilot.IMPLEMENTATION_RELATIVE_PATH) / "test_outputs"
        with tempfile.TemporaryDirectory(dir=test_root) as temporary:
            output = Path(temporary) / "never-created"
            with (
                mock.patch.object(pilot.inherited, "_runtime_identity", return_value={}),
                mock.patch.object(
                    pilot,
                    "_load_execution_spec",
                    side_effect=ValueError("preflight rejected"),
                ),
                mock.patch.object(
                    pilot.inherited, "_create_and_guard_output_directory"
                ) as create_output,
                mock.patch.object(
                    torch.optim, "Adam", side_effect=AssertionError("optimizer constructed")
                ),
            ):
                with self.assertRaisesRegex(ValueError, "preflight rejected"):
                    pilot.execute(
                        execution_spec=Path(temporary) / "spec.json",
                        execution_spec_sha256="A" * 64,
                    )
            create_output.assert_not_called()
            self.assertFalse(output.exists())

    def test_zero_step_rejection_binds_all_four_contracts_and_has_no_checkpoint(self) -> None:
        captured: dict = {}

        def publish(output_directory, *, status, receipt, directory_guard):
            captured.update(receipt)
            self.assertEqual(status, "rejected")
            self.assertFalse((output_directory / "candidate.pt").exists())
            return output_directory / "rejected_receipt.json", "C" * 64

        with mock.patch.object(pilot, "_publish_status_exact", side_effect=publish):
            report = pilot._publish_failure_status(
                Path("synthetic-output"),
                execution_spec_path=Path("synthetic-spec.json"),
                execution_spec_sha256="D" * 64,
                phase="pre_step",
                error=RuntimeError("synthetic"),
                directory_guard=_FakeGuard(),
                optimizer_steps_completed=0,
            )
        for name, value in pilot._contract_bindings().items():
            self.assertEqual(captured[name], value)
        self.assertEqual(report["optimizer_steps_completed"], 0)
        self.assertIsNone(report["checkpoint_path"])
        self.assertFalse(report["accepted_marker_written"])

    def test_post_step_rejection_retains_failing_state_without_rollback(self) -> None:
        model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
        progress = pilot.ExecutionProgress(model=model)
        pilot._set_trainability(model, stage=1)
        optimizer = pilot._new_actor_adam(model)
        progress.optimizer = optimizer
        named = dict(model.named_parameters())
        optimizer.zero_grad(set_to_none=True)
        sum(named[name].sum() for name in pilot.STAGE1_TRAINABLE_NAMES).backward()
        pilot._optimizer_step_and_record(optimizer, progress, stage=1)
        failing_hashes = {name: pilot._tensor_sha256(value) for name, value in named.items()}
        readback = b"synthetic-checkpoint"
        guard = _FakeGuard(readback)
        retention = {
            "checkpoint_readback_exact": True,
            "optimizer_contract_pass": True,
            "optimizer_contract_failures": [],
            "optimizer_steps_expected": pilot._expected_optimizer_steps(1),
            "optimizer_steps_observed": pilot._expected_optimizer_steps(1),
            "model_nonfinite_count": 0,
            "optimizer_nonfinite_count": 0,
        }
        captured: dict = {}

        def publish_checkpoint(output_directory, *, model, metadata, optimizer, directory_guard):
            captured["metadata"] = metadata
            return Path("synthetic-output/candidate.pt"), "F" * 64, guard, readback

        def publish_status(output_directory, *, status, receipt, directory_guard, **_):
            captured.update(receipt)
            return output_directory / "rejected_receipt.json", "E" * 64

        with (
            mock.patch.object(
                pilot,
                "_publish_checkpoint_exact",
                side_effect=publish_checkpoint,
            ),
            mock.patch.object(pilot.inherited, "_win_read_all", return_value=readback),
            mock.patch.object(
                pilot, "_validate_rejected_checkpoint_readback", return_value=retention
            ),
            mock.patch.object(pilot, "_publish_status_exact", side_effect=publish_status),
            mock.patch.object(Path, "exists", return_value=False),
            mock.patch.object(Path, "is_file", return_value=True),
        ):
            report = pilot._publish_post_step_rejection(
                Path("synthetic-output"),
                progress=progress,
                source_hashes=pilot.inherited.checkpoint_source_hashes(),
                execution_spec_path=Path("synthetic-spec.json"),
                execution_spec_sha256="1" * 64,
                phase="post_step_safety",
                error=RuntimeError("synthetic safety failure"),
                directory_guard=_FakeGuard(),
            )
        self.assertEqual(report["optimizer_steps_completed"], 1)
        self.assertTrue(report["checkpoint_readback_exact"])
        self.assertEqual(
            failing_hashes,
            {name: pilot._tensor_sha256(value) for name, value in named.items()},
        )
        for name, value in pilot._contract_bindings().items():
            self.assertEqual(captured[name], value)
            self.assertEqual(captured["metadata"]["training"][name], value)

    def test_checkpoint_handoff_after_identity_never_creates_replacement(self) -> None:
        model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
        pilot._set_trainability(model, stage=1)
        optimizer = pilot._new_actor_adam(model)
        loaded = {
            "checkpoint_path": pilot._repo_path(pilot.INPUT_CHECKPOINT_RELATIVE_PATH),
            "source_hashes": pilot.inherited.checkpoint_source_hashes(),
            "model": model,
        }
        run = {
            "model": model,
            "optimizer": optimizer,
            "optimizer_steps_completed": 1,
            "raw_value_mse_initial": 0.0,
            "safety_stop": True,
            "terminal_offline_gates": None,
        }
        checkpoint_guard = _FakeGuard(b"held")
        handoff = pilot.inherited._CheckpointPublicationHandoffError(
            cause=OSError("after identity"),
            checkpoint_path=Path("synthetic-output/candidate.pt"),
            checkpoint_sha256="9" * 64,
            checkpoint_guard=checkpoint_guard,
            checkpoint_readback=b"held",
        )

        def fake_run(_loaded, _probe, progress):
            progress.model = model
            progress.optimizer = optimizer
            progress.optimizer_steps_completed = 1
            return run

        post_result = {"mode": "execute", "status": "rejected"}
        with (
            mock.patch.object(pilot.inherited, "_runtime_identity", return_value={}),
            mock.patch.object(pilot, "_load_execution_spec", return_value={}),
            mock.patch.object(
                pilot,
                "_validate_execution_boundary",
                return_value=({"receipt_sha256": "A" * 64, "training_contract": {}}, Path("synthetic-output")),
            ),
            mock.patch.object(pilot.inherited, "_load_validated_inputs", return_value=loaded),
            mock.patch.object(pilot, "_build_authorized_execution_fixed_inputs", return_value={}),
            mock.patch.object(pilot.inherited, "_create_and_guard_output_directory", return_value=_FakeGuard()),
            mock.patch.object(pilot, "_run_two_stage", side_effect=fake_run),
            mock.patch.object(
                pilot, "_publish_checkpoint_exact", side_effect=handoff
            ) as publish_checkpoint,
            mock.patch.object(
                pilot, "_publish_post_step_rejection", return_value=post_result
            ) as publish_rejection,
        ):
            self.assertEqual(
                pilot.execute(
                    execution_spec=Path("synthetic-spec.json"),
                    execution_spec_sha256="B" * 64,
                ),
                post_result,
            )
        publish_checkpoint.assert_called_once()
        publish_rejection.assert_called_once()
        call = publish_rejection.call_args.kwargs
        self.assertEqual(call["existing_checkpoint_sha256"], "9" * 64)
        self.assertIs(call["existing_checkpoint_guard"], checkpoint_guard)
        self.assertEqual(call["existing_checkpoint_readback"], b"held")

    def test_pre_step_exception_after_prior_steps_routes_to_retained_rejection(self) -> None:
        model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
        optimizer = pilot._new_actor_adam(model)
        loaded = {
            "checkpoint_path": pilot._repo_path(pilot.INPUT_CHECKPOINT_RELATIVE_PATH),
            "source_hashes": pilot.inherited.checkpoint_source_hashes(),
            "model": model,
        }

        def fail_after_prior_steps(_loaded, _probe, progress):
            progress.model = model
            progress.optimizer = optimizer
            progress.optimizer_steps_completed = 2
            progress.stage_2_updates_completed = 1
            progress.failure_phase = "stage_2_update_2_full_batch_step"
            raise RuntimeError("pre-step after prior successful steps")

        post_result = {"mode": "execute", "status": "rejected"}
        with (
            mock.patch.object(pilot.inherited, "_runtime_identity", return_value={}),
            mock.patch.object(pilot, "_load_execution_spec", return_value={}),
            mock.patch.object(
                pilot,
                "_validate_execution_boundary",
                return_value=({"receipt_sha256": "A" * 64, "training_contract": {}}, Path("synthetic-output")),
            ),
            mock.patch.object(pilot.inherited, "_load_validated_inputs", return_value=loaded),
            mock.patch.object(pilot, "_build_authorized_execution_fixed_inputs", return_value={}),
            mock.patch.object(pilot.inherited, "_create_and_guard_output_directory", return_value=_FakeGuard()),
            mock.patch.object(pilot, "_run_two_stage", side_effect=fail_after_prior_steps),
            mock.patch.object(
                pilot, "_publish_post_step_rejection", return_value=post_result
            ) as publish_rejection,
        ):
            self.assertEqual(
                pilot.execute(
                    execution_spec=Path("synthetic-spec.json"),
                    execution_spec_sha256="B" * 64,
                ),
                post_result,
            )
        call = publish_rejection.call_args.kwargs
        self.assertEqual(call["progress"].optimizer_steps_completed, 2)
        self.assertEqual(call["phase"], "stage_2_update_2_full_batch_step")

    def test_normal_terminal_accept_and_reject_allowlists(self) -> None:
        run = {
            "terminal_offline_gates": {
                "failures": [], "accepted_before_checkpoint_validation": True
            },
            "optimizer_steps_completed": 33,
            "same_optimizer_object_across_all_updates": True,
            "optimizer_identity_count": 1,
            "independent_replay_validation": {"status": "pass"},
            "stage_2_update_summaries": [{}] * 32,
            "stage_2_full_diagnostics": {str(value): [] for value in pilot.DIAGNOSTIC_UPDATE_ORDINALS},
            "parameter_optimizer_contract_pass": True,
            "value_contract_pass": True,
        }
        serialized = {
            "status": "pass",
            "optimizer_state_steps": pilot._expected_optimizer_steps(33),
            "metadata_exact": True,
            "terminal_all_830_outputs_byte_exact": True,
        }
        self.assertTrue(
            pilot._final_gate_report(run, serialized_validation=serialized)["accepted"]
        )
        rejected = deepcopy(serialized)
        rejected["terminal_all_830_outputs_byte_exact"] = False
        result = pilot._final_gate_report(run, serialized_validation=rejected)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["failures"], ["checkpoint:terminal_output_identity"])

    def test_normal_receipt_and_checkpoint_metadata_bind_remediation_for_both_statuses(self) -> None:
        model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
        optimizer = pilot._new_actor_adam(model)
        loaded = {
            "checkpoint_path": pilot._repo_path(pilot.INPUT_CHECKPOINT_RELATIVE_PATH),
            "source_hashes": pilot.inherited.checkpoint_source_hashes(),
            "model": model,
        }
        run = {
            "model": model,
            "optimizer": optimizer,
            "optimizer_steps_completed": 0,
            "raw_value_mse_initial": 0.0,
            "safety_stop": False,
            "terminal_offline_gates": None,
        }
        for accepted in (True, False):
            captured: dict = {}
            checkpoint_guard = _FakeGuard(b"checkpoint")

            def publish_checkpoint(output_directory, *, model, metadata, optimizer, directory_guard):
                captured["metadata"] = metadata
                return output_directory / "candidate.pt", "4" * 64, checkpoint_guard, b"checkpoint"

            def publish_status(output_directory, *, status, receipt, directory_guard, **_):
                captured["status"] = status
                captured["receipt"] = receipt
                return output_directory / f"{status}_receipt.json", "5" * 64

            with (
                self.subTest(accepted=accepted),
                mock.patch.object(pilot.inherited, "_runtime_identity", return_value={}),
                mock.patch.object(pilot, "_load_execution_spec", return_value={}),
                mock.patch.object(
                    pilot,
                    "_validate_execution_boundary",
                    return_value=({"receipt_sha256": "A" * 64, "training_contract": {}}, Path("synthetic-output")),
                ),
                mock.patch.object(pilot.inherited, "_load_validated_inputs", return_value=loaded),
                mock.patch.object(pilot, "_build_authorized_execution_fixed_inputs", return_value={}),
                mock.patch.object(pilot.inherited, "_create_and_guard_output_directory", return_value=_FakeGuard()),
                mock.patch.object(pilot, "_run_two_stage", return_value=run),
                mock.patch.object(
                    pilot,
                    "_publish_checkpoint_exact",
                    side_effect=publish_checkpoint,
                ),
                mock.patch.object(pilot.inherited, "_win_read_all", return_value=b"checkpoint"),
                mock.patch.object(pilot, "_validate_serialized_checkpoint", return_value={}),
                mock.patch.object(
                    pilot, "_final_gate_report", return_value={"accepted": accepted, "failures": []}
                ),
                mock.patch.object(pilot, "_publish_status_exact", side_effect=publish_status),
            ):
                result = pilot.execute(
                    execution_spec=Path("synthetic-spec.json"),
                    execution_spec_sha256="B" * 64,
                )
            self.assertEqual(result["status"], "accepted" if accepted else "rejected")
            for name, value in pilot._contract_bindings().items():
                self.assertEqual(captured["receipt"][name], value)
                self.assertEqual(captured["metadata"]["training"][name], value)


class InteractionMaturationRealArtifactPublicationTests(unittest.TestCase):
    @staticmethod
    def _test_root() -> Path:
        root = pilot._repo_path(pilot.IMPLEMENTATION_RELATIVE_PATH) / "test_outputs"
        root.mkdir(exist_ok=True)
        return root

    @staticmethod
    def _receipt(status: str) -> dict:
        core = {"schema_version": "test", "status": status}
        return {**core, "receipt_sha256": pilot.canonical_sha256(core)}

    def test_real_exact_accepted_rejected_and_zero_step_artifact_sets(self) -> None:
        source_hashes = pilot.inherited.checkpoint_source_hashes()
        for status in ("accepted", "rejected"):
            with self.subTest(status=status), tempfile.TemporaryDirectory(
                dir=self._test_root()
            ) as temporary:
                output = Path(temporary) / "output"
                guard = pilot.inherited._create_and_guard_output_directory(output)
                checkpoint_guard = None
                try:
                    progress = _stage1_progress()
                    metadata = pilot.checkpoint_metadata(
                        source_hashes=source_hashes, training={"test": status}
                    )
                    (
                        checkpoint_path,
                        checkpoint_hash,
                        checkpoint_guard,
                        readback,
                    ) = pilot._publish_checkpoint_exact(
                        output,
                        model=progress.model,
                        metadata=metadata,
                        optimizer=progress.optimizer,
                        directory_guard=guard,
                    )
                    self.assertEqual(checkpoint_path.name, "candidate.pt")
                    pilot._publish_status_exact(
                        output,
                        status=status,
                        receipt=self._receipt(status),
                        directory_guard=guard,
                        checkpoint_path=checkpoint_path,
                        checkpoint_sha256=checkpoint_hash,
                        checkpoint_guard=checkpoint_guard,
                        checkpoint_readback=readback,
                    )
                    alias_name = checkpoint_guard.path.name
                    self.assertEqual(
                        sorted(path.name for path in output.iterdir()),
                        sorted(
                            [
                                alias_name,
                                "candidate.pt",
                                f"{status}_receipt.json",
                                status.upper(),
                            ]
                        ),
                    )
                finally:
                    if checkpoint_guard is not None:
                        checkpoint_guard.close()
                    guard.close()
                self.assertEqual(
                    sorted(path.name for path in output.iterdir()),
                    sorted(
                        [
                            "candidate.pt",
                            f"{status}_receipt.json",
                            status.upper(),
                        ]
                    ),
                )

        with tempfile.TemporaryDirectory(dir=self._test_root()) as temporary:
            output = Path(temporary) / "output"
            guard = pilot.inherited._create_and_guard_output_directory(output)
            try:
                pilot._publish_failure_status(
                    output,
                    execution_spec_path=Path(temporary) / "execution.json",
                    execution_spec_sha256="A" * 64,
                    phase="pre_step",
                    error=RuntimeError("zero-step"),
                    directory_guard=guard,
                )
                self.assertEqual(
                    sorted(path.name for path in output.iterdir()),
                    ["REJECTED", "rejected_receipt.json"],
                )
            finally:
                guard.close()

    def test_held_candidate_is_never_reopened_and_nonheld_hashing_restores_share_mode(self) -> None:
        with tempfile.TemporaryDirectory(dir=self._test_root()) as temporary:
            output = Path(temporary) / "output"
            guard = pilot.inherited._create_and_guard_output_directory(output)
            checkpoint_guard = None
            real_open = pilot.inherited._win_open_handle
            armed = False
            private_path = None
            observed: list[tuple[str, int, int]] = []

            def guarded_open(path, *, desired_access, share_mode, creation_disposition, flags):
                nonlocal private_path
                absolute = Path(path).absolute()
                if (
                    not armed
                    and creation_disposition == pilot.inherited._CREATE_NEW
                    and absolute.name.startswith(".candidate-")
                    and absolute.name.endswith(".staging.pt")
                ):
                    private_path = absolute
                if armed and absolute in {
                    (output / "candidate.pt").absolute(), private_path
                }:
                    raise AssertionError("held checkpoint name reopened after guard transfer")
                if armed:
                    observed.append((Path(path).name, share_mode, creation_disposition))
                return real_open(
                    path,
                    desired_access=desired_access,
                    share_mode=share_mode,
                    creation_disposition=creation_disposition,
                    flags=flags,
                )

            def arm_after_identity() -> None:
                nonlocal armed
                armed = True

            try:
                progress = _stage1_progress()
                metadata = pilot.checkpoint_metadata(
                    source_hashes=pilot.inherited.checkpoint_source_hashes(),
                    training={"test": "held-no-reopen"},
                )
                with (
                    mock.patch.object(
                        pilot.inherited, "_win_open_handle", side_effect=guarded_open
                    ),
                    mock.patch.object(
                        pilot.inherited,
                        "_after_checkpoint_public_identity_verified",
                        side_effect=arm_after_identity,
                    ),
                ):
                    (
                        checkpoint_path,
                        checkpoint_hash,
                        checkpoint_guard,
                        readback,
                    ) = pilot._publish_checkpoint_exact(
                        output,
                        model=progress.model,
                        metadata=metadata,
                        optimizer=progress.optimizer,
                        directory_guard=guard,
                    )
                    live_checkpoint_inventory = pilot._require_exact_output_artifacts(
                        output,
                        guard,
                        {"candidate.pt": checkpoint_hash},
                        checkpoint_path=checkpoint_path,
                        checkpoint_sha256=checkpoint_hash,
                        checkpoint_guard=checkpoint_guard,
                        checkpoint_readback=readback,
                    )
                    self.assertEqual(
                        {
                            row["name"]: row["projection"]
                            for row in live_checkpoint_inventory
                        },
                        {
                            "candidate.pt": "public_artifact",
                            checkpoint_guard.path.name: (
                                "internal_held_checkpoint_alias"
                            ),
                        },
                    )
                    pilot._publish_status_exact(
                        output,
                        status="accepted",
                        receipt=self._receipt("accepted"),
                        directory_guard=guard,
                        checkpoint_path=checkpoint_path,
                        checkpoint_sha256=checkpoint_hash,
                        checkpoint_guard=checkpoint_guard,
                        checkpoint_readback=readback,
                    )
                    alias_name = checkpoint_guard.path.name
                    self.assertEqual(
                        sorted(path.name for path in output.iterdir()),
                        sorted(
                            [
                                alias_name,
                                "candidate.pt",
                                "accepted_receipt.json",
                                "ACCEPTED",
                            ]
                        ),
                    )
                restored_share = (
                    pilot.inherited._FILE_SHARE_READ
                    | pilot.inherited._FILE_SHARE_WRITE
                    | pilot.inherited._FILE_SHARE_DELETE
                )
                independently_hashed = {
                    name
                    for name, share_mode, disposition in observed
                    if disposition == pilot.inherited._OPEN_EXISTING
                    and share_mode == restored_share
                }
                self.assertEqual(
                    independently_hashed,
                    {"accepted_receipt.json", "ACCEPTED"},
                )
                checkpoint_guard.close()
                checkpoint_guard = None
                self.assertEqual(
                    sorted(path.name for path in output.iterdir()),
                    ["ACCEPTED", "accepted_receipt.json", "candidate.pt"],
                )
            finally:
                if checkpoint_guard is not None:
                    checkpoint_guard.close()
                guard.close()

    def test_invalid_or_partial_held_checkpoint_evidence_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=self._test_root()) as temporary:
            output = Path(temporary) / "output"
            guard = pilot.inherited._create_and_guard_output_directory(output)
            checkpoint_guard = None
            try:
                progress = _stage1_progress()
                metadata = pilot.checkpoint_metadata(
                    source_hashes=pilot.inherited.checkpoint_source_hashes(),
                    training={"test": "held-invalid"},
                )
                (
                    checkpoint_path,
                    checkpoint_hash,
                    checkpoint_guard,
                    readback,
                ) = pilot._publish_checkpoint_exact(
                    output,
                    model=progress.model,
                    metadata=metadata,
                    optimizer=progress.optimizer,
                    directory_guard=guard,
                )
                base = {
                    "checkpoint_path": checkpoint_path,
                    "checkpoint_sha256": checkpoint_hash,
                    "checkpoint_guard": checkpoint_guard,
                    "checkpoint_readback": readback,
                }
                for missing in tuple(base):
                    with self.subTest(missing=missing):
                        evidence = dict(base)
                        evidence[missing] = None
                        with self.assertRaises(ValueError):
                            pilot._require_exact_output_artifacts(
                                output,
                                guard,
                                {"candidate.pt": checkpoint_hash},
                                **evidence,
                            )
                mutations = {
                    "wrong_path": {
                        **base,
                        "checkpoint_path": output / "renamed.pt",
                    },
                    "wrong_parent": {
                        **base,
                        "checkpoint_path": output.parent / "candidate.pt",
                    },
                    "lowercase_hash": {
                        **base,
                        "checkpoint_sha256": checkpoint_hash.lower(),
                    },
                    "wrong_hash": {
                        **base,
                        "checkpoint_sha256": "0" * 64,
                    },
                    "nonbytes_readback": {
                        **base,
                        "checkpoint_readback": bytearray(readback),
                    },
                    "readback_mismatch": {
                        **base,
                        "checkpoint_readback": readback + b"x",
                    },
                    "foreign_guard_type": {
                        **base,
                        "checkpoint_guard": object(),
                    },
                }
                for name, evidence in mutations.items():
                    with self.subTest(name=name), self.assertRaises(
                        (ValueError, TypeError)
                    ):
                        pilot._require_exact_output_artifacts(
                            output,
                            guard,
                            {"candidate.pt": checkpoint_hash},
                            **evidence,
                        )
                original_path = checkpoint_guard.path
                invalid_aliases = {
                    "wrong_bound_alias": ".candidate-" + "0" * 32 + ".staging.pt",
                    "token_31": ".candidate-" + "0" * 31 + ".staging.pt",
                    "token_33": ".candidate-" + "0" * 33 + ".staging.pt",
                    "uppercase": ".candidate-" + "A" * 32 + ".staging.pt",
                    "nonhex": ".candidate-" + "g" * 32 + ".staging.pt",
                    "wrong_suffix": ".candidate-" + "0" * 32 + ".stage.pt",
                }
                for name, alias_name in invalid_aliases.items():
                    with self.subTest(alias=name):
                        checkpoint_guard.path = output / alias_name
                        try:
                            with self.assertRaises(ValueError):
                                pilot._require_exact_output_artifacts(
                                    output,
                                    guard,
                                    {"candidate.pt": checkpoint_hash},
                                    **base,
                                )
                        finally:
                            checkpoint_guard.path = original_path
                checkpoint_guard.path = output.parent / original_path.name
                try:
                    with self.assertRaises(ValueError):
                        pilot._require_exact_output_artifacts(
                            output,
                            guard,
                            {"candidate.pt": checkpoint_hash},
                            **base,
                        )
                finally:
                    checkpoint_guard.path = original_path
                checkpoint_guard._delete = False
                try:
                    with self.assertRaises(ValueError):
                        pilot._require_exact_output_artifacts(
                            output,
                            guard,
                            {"candidate.pt": checkpoint_hash},
                            **base,
                        )
                finally:
                    checkpoint_guard._delete = True
                checkpoint_guard.close()
                with self.assertRaises(RuntimeError):
                    pilot._require_exact_output_artifacts(
                        output,
                        guard,
                        {"candidate.pt": checkpoint_hash},
                        **base,
                    )
                checkpoint_guard = None
                self.assertEqual(
                    sorted(path.name for path in output.iterdir()),
                    ["candidate.pt"],
                )
            finally:
                if checkpoint_guard is not None:
                    checkpoint_guard.close()
                guard.close()

    def test_real_preexisting_file_directory_and_link_fail_before_status(self) -> None:
        for kind in ("regular", "directory", "link"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(
                dir=self._test_root()
            ) as temporary:
                output = Path(temporary) / "output"
                guard = pilot.inherited._create_and_guard_output_directory(output)
                poison = output / "EXTRA"
                patcher = None
                try:
                    if kind == "regular":
                        poison.write_bytes(b"poison")
                    elif kind == "directory":
                        poison.mkdir()
                    else:
                        target = Path(temporary) / "target"
                        target.write_bytes(b"target")
                        try:
                            poison.symlink_to(target)
                        except OSError:
                            poison.write_bytes(b"reparse seam")
                            real = pilot.inherited._is_link_or_reparse
                            patcher = mock.patch.object(
                                pilot.inherited,
                                "_is_link_or_reparse",
                                side_effect=lambda path: (
                                    Path(path).absolute() == poison.absolute()
                                    or real(path)
                                ),
                            )
                            patcher.start()
                    with self.assertRaises(ValueError):
                        pilot._publish_status_exact(
                            output,
                            status="accepted",
                            receipt=self._receipt("accepted"),
                            directory_guard=guard,
                        )
                    self.assertFalse((output / "ACCEPTED").exists())
                    self.assertFalse((output / "accepted_receipt.json").exists())
                    self.assertTrue(poison.exists() or poison.is_symlink())
                finally:
                    if patcher is not None:
                        patcher.stop()
                    guard.close()

    def test_real_postcheck_contamination_removes_only_owned_status(self) -> None:
        with tempfile.TemporaryDirectory(dir=self._test_root()) as temporary:
            output = Path(temporary) / "output"
            guard = pilot.inherited._create_and_guard_output_directory(output)
            try:
                with mock.patch.object(
                    pilot,
                    "_after_status_publication_before_artifact_check",
                    side_effect=lambda: (output / "EXTRA").write_bytes(b"injected"),
                ):
                    with self.assertRaisesRegex(ValueError, "artifact set"):
                        pilot._publish_status_exact(
                            output,
                            status="accepted",
                            receipt=self._receipt("accepted"),
                            directory_guard=guard,
                        )
                self.assertEqual(
                    sorted(path.name for path in output.iterdir()), ["EXTRA"]
                )
            finally:
                guard.close()

    def test_held_candidate_postcheck_contamination_cleans_only_owned_status(self) -> None:
        for status in ("accepted", "rejected"):
            with self.subTest(status=status), tempfile.TemporaryDirectory(
                dir=self._test_root()
            ) as temporary:
                output = Path(temporary) / "output"
                guard = pilot.inherited._create_and_guard_output_directory(output)
                checkpoint_guard = None
                try:
                    progress = _stage1_progress()
                    metadata = pilot.checkpoint_metadata(
                        source_hashes=pilot.inherited.checkpoint_source_hashes(),
                        training={"test": f"held-contamination-{status}"},
                    )
                    (
                        checkpoint_path,
                        checkpoint_hash,
                        checkpoint_guard,
                        readback,
                    ) = pilot._publish_checkpoint_exact(
                        output,
                        model=progress.model,
                        metadata=metadata,
                        optimizer=progress.optimizer,
                        directory_guard=guard,
                    )
                    real_open = pilot.inherited._win_open_handle
                    private_path = checkpoint_guard.path
                    receipt_path = output / f"{status}_receipt.json"
                    marker_path = output / status.upper()
                    cleanup_calls: list[tuple[Path, dict]] = []

                    def instrumented_open(path, **kwargs):
                        absolute = Path(path).absolute()
                        if absolute in {checkpoint_path, private_path}:
                            raise AssertionError(
                                "held checkpoint name reopened during status postcheck"
                            )
                        if (
                            absolute in {receipt_path, marker_path}
                            and kwargs["desired_access"]
                            == pilot.inherited._GENERIC_READ | pilot.inherited._DELETE
                            and kwargs["creation_disposition"]
                            == pilot.inherited._OPEN_EXISTING
                        ):
                            cleanup_calls.append((absolute, dict(kwargs)))
                        return real_open(path, **kwargs)

                    with (
                        mock.patch.object(
                            pilot,
                            "_after_status_publication_before_artifact_check",
                            side_effect=lambda: (output / "EXTRA").write_bytes(
                                b"injected"
                            ),
                        ),
                        mock.patch.object(
                            pilot.inherited,
                            "_win_open_handle",
                            side_effect=instrumented_open,
                        ),
                    ):
                        with self.assertRaisesRegex(ValueError, "artifact set"):
                            pilot._publish_status_exact(
                                output,
                                status=status,
                                receipt=self._receipt(status),
                                directory_guard=guard,
                                checkpoint_path=checkpoint_path,
                                checkpoint_sha256=checkpoint_hash,
                                checkpoint_guard=checkpoint_guard,
                                checkpoint_readback=readback,
                            )
                    required_share = (
                        pilot.inherited._FILE_SHARE_READ
                        | pilot.inherited._FILE_SHARE_WRITE
                        | pilot.inherited._FILE_SHARE_DELETE
                    )
                    self.assertEqual(
                        {path for path, _kwargs in cleanup_calls},
                        {receipt_path, marker_path},
                    )
                    self.assertEqual(len(cleanup_calls), 2)
                    for path, kwargs in cleanup_calls:
                        with self.subTest(status=status, cleanup=path.name):
                            self.assertEqual(
                                kwargs["desired_access"],
                                pilot.inherited._GENERIC_READ
                                | pilot.inherited._DELETE,
                            )
                            self.assertEqual(kwargs["share_mode"], required_share)
                            self.assertNotEqual(
                                kwargs["share_mode"],
                                pilot.inherited._FILE_SHARE_READ,
                            )
                            self.assertEqual(
                                kwargs["creation_disposition"],
                                pilot.inherited._OPEN_EXISTING,
                            )
                            self.assertEqual(
                                kwargs["flags"],
                                pilot.inherited._FILE_ATTRIBUTE_NORMAL
                                | pilot.inherited._FILE_FLAG_OPEN_REPARSE_POINT,
                            )
                    self.assertEqual(
                        sorted(path.name for path in output.iterdir()),
                        sorted(["EXTRA", private_path.name, "candidate.pt"]),
                    )
                    self.assertFalse(marker_path.exists())
                    self.assertFalse(receipt_path.exists())
                    checkpoint_guard.close()
                    checkpoint_guard = None
                    self.assertEqual(
                        sorted(path.name for path in output.iterdir()),
                        ["EXTRA", "candidate.pt"],
                    )
                finally:
                    if checkpoint_guard is not None:
                        checkpoint_guard.close()
                    guard.close()

    def test_held_candidate_wrong_direct_entry_type_fails_before_guard_use(self) -> None:
        payload = b"same-parent-held-checkpoint"
        checkpoint_hash = hashlib.sha256(payload).hexdigest().upper()

        def create_same_parent_evidence(temporary: str):
            output = Path(temporary) / "output"
            guard = pilot.inherited._create_and_guard_output_directory(output)
            alias = output / (".candidate-" + "a" * 32 + ".staging.pt")
            held = pilot.inherited._create_new_file_guarded(alias, payload, guard)
            return output, guard, alias, held

        for candidate_kind in ("directory", "symlink"):
            with self.subTest(candidate=candidate_kind), tempfile.TemporaryDirectory(
                dir=self._test_root()
            ) as temporary:
                target = Path(temporary) / "target"
                target.write_bytes(b"target")
                output, guard, alias, held = create_same_parent_evidence(temporary)
                candidate = output / "candidate.pt"
                inventory_patch = None
                try:
                    if candidate_kind == "directory":
                        candidate.mkdir()
                    else:
                        try:
                            candidate.symlink_to(target)
                        except OSError:
                            candidate.write_bytes(payload)
                            real_inventory = pilot._output_artifact_inventory

                            def classify_candidate_as_link(*args, **kwargs):
                                records = real_inventory(*args, **kwargs)
                                for record in records:
                                    if record["name"] == "candidate.pt":
                                        record["type"] = "link_or_reparse"
                                        record["link_or_reparse"] = True
                                return records

                            inventory_patch = mock.patch.object(
                                pilot,
                                "_output_artifact_inventory",
                                side_effect=classify_candidate_as_link,
                            )
                            inventory_patch.start()
                    held.delete_on_close()
                    with (
                        mock.patch.object(
                            pilot.inherited,
                            "_win_read_all",
                            side_effect=AssertionError(
                                "held bytes read before candidate type rejection"
                            ),
                        ),
                        mock.patch.object(pilot.inherited, "_publish_status") as publish,
                    ):
                        with self.assertRaisesRegex(
                            ValueError, "direct regular file"
                        ):
                            pilot._require_exact_output_artifacts(
                                output,
                                guard,
                                {"candidate.pt": checkpoint_hash},
                                checkpoint_path=candidate,
                                checkpoint_sha256=checkpoint_hash,
                                checkpoint_guard=held,
                                checkpoint_readback=payload,
                            )
                        publish.assert_not_called()
                    self.assertFalse((output / "ACCEPTED").exists())
                    self.assertFalse((output / "REJECTED").exists())
                finally:
                    if inventory_patch is not None:
                        inventory_patch.stop()
                    held.close()
                    self.assertFalse(alias.exists())
                    guard.close()

        with tempfile.TemporaryDirectory(dir=self._test_root()) as temporary:
            output, guard, alias, held = create_same_parent_evidence(temporary)
            candidate = output / "candidate.pt"
            try:
                os.link(alias, candidate)
                pilot.inherited._verify_existing_file_identity(
                    candidate,
                    guard,
                    expected_identity=held.identity,
                )
                held.delete_on_close()
                records = pilot._require_exact_output_artifacts(
                    output,
                    guard,
                    {"candidate.pt": checkpoint_hash},
                    checkpoint_path=candidate,
                    checkpoint_sha256=checkpoint_hash,
                    checkpoint_guard=held,
                    checkpoint_readback=payload,
                )
                self.assertEqual(
                    {record["type"] for record in records}, {"regular_file"}
                )
                real_inventory = pilot._output_artifact_inventory
                for mutation in ("directory", "link_or_reparse", "other"):
                    with self.subTest(private_alias=mutation):
                        def mutate_private_alias(*args, _mutation=mutation, **kwargs):
                            inventory = real_inventory(*args, **kwargs)
                            for record in inventory:
                                if record["name"] == alias.name:
                                    record["type"] = _mutation
                                    record["link_or_reparse"] = (
                                        _mutation == "link_or_reparse"
                                    )
                            return inventory

                        with (
                            mock.patch.object(
                                pilot,
                                "_output_artifact_inventory",
                                side_effect=mutate_private_alias,
                            ),
                            mock.patch.object(
                                pilot.inherited,
                                "_win_read_all",
                                side_effect=AssertionError(
                                    "held bytes read before private-alias type rejection"
                                ),
                            ),
                            mock.patch.object(
                                pilot.inherited, "_publish_status"
                            ) as publish,
                        ):
                            with self.assertRaisesRegex(
                                ValueError, "direct regular file"
                            ):
                                pilot._require_exact_output_artifacts(
                                    output,
                                    guard,
                                    {"candidate.pt": checkpoint_hash},
                                    checkpoint_path=candidate,
                                    checkpoint_sha256=checkpoint_hash,
                                    checkpoint_guard=held,
                                    checkpoint_readback=payload,
                                )
                            publish.assert_not_called()
            finally:
                held.close()
                self.assertFalse(alias.exists())
                self.assertTrue(candidate.is_file())
                guard.close()

    def test_post_checkpoint_contamination_preserves_candidate_unclaimed(self) -> None:
        with tempfile.TemporaryDirectory(dir=self._test_root()) as temporary:
            output = Path(temporary) / "output"
            guard = pilot.inherited._create_and_guard_output_directory(output)
            progress = _stage1_progress()
            metadata = pilot.checkpoint_metadata(
                source_hashes=pilot.inherited.checkpoint_source_hashes(),
                training={"test": "checkpoint-contamination"},
            )
            real_open = pilot.inherited._win_open_handle
            armed = False
            private_path = None

            def guarded_open(path, **kwargs):
                nonlocal private_path
                absolute = Path(path).absolute()
                if (
                    not armed
                    and kwargs.get("creation_disposition")
                    == pilot.inherited._CREATE_NEW
                    and absolute.name.startswith(".candidate-")
                    and absolute.name.endswith(".staging.pt")
                ):
                    private_path = absolute
                if armed and absolute in {
                    (output / "candidate.pt").absolute(), private_path
                }:
                    raise AssertionError("held checkpoint name reopened after checkpoint contamination")
                return real_open(path, **kwargs)

            def arm_after_identity() -> None:
                nonlocal armed
                armed = True

            try:
                with (
                    mock.patch.object(
                        pilot.inherited,
                        "_win_open_handle",
                        side_effect=guarded_open,
                    ),
                    mock.patch.object(
                        pilot.inherited,
                        "_after_checkpoint_public_identity_verified",
                        side_effect=arm_after_identity,
                    ),
                    mock.patch.object(
                        pilot,
                        "_after_checkpoint_publication_before_artifact_check",
                        side_effect=lambda: (output / "EXTRA").write_bytes(b"injected"),
                    ),
                ):
                    with self.assertRaisesRegex(ValueError, "artifact set"):
                        pilot._publish_checkpoint_exact(
                            output,
                            model=progress.model,
                            metadata=metadata,
                            optimizer=progress.optimizer,
                            directory_guard=guard,
                        )
                self.assertEqual(
                    sorted(path.name for path in output.iterdir()),
                    ["EXTRA", "candidate.pt"],
                )
                self.assertFalse((output / "ACCEPTED").exists())
                self.assertFalse((output / "REJECTED").exists())
            finally:
                guard.close()

    def test_real_checkpoint_handoff_retains_identity_and_finishes_rejected(self) -> None:
        with tempfile.TemporaryDirectory(dir=self._test_root()) as temporary:
            output = Path(temporary) / "output"
            guard = pilot.inherited._create_and_guard_output_directory(output)
            progress = _stage1_progress()
            real_open = pilot.inherited._win_open_handle
            armed = False
            private_path = None

            def no_candidate_open(path, **kwargs):
                nonlocal private_path
                absolute = Path(path).absolute()
                if (
                    not armed
                    and kwargs.get("creation_disposition")
                    == pilot.inherited._CREATE_NEW
                    and absolute.name.startswith(".candidate-")
                    and absolute.name.endswith(".staging.pt")
                ):
                    private_path = absolute
                if armed and absolute in {
                    (output / "candidate.pt").absolute(), private_path
                }:
                    raise AssertionError("held checkpoint name reopened during handoff rejection")
                return real_open(path, **kwargs)

            def fail_after_identity() -> None:
                nonlocal armed
                armed = True
                raise RuntimeError("post-identity fault")

            try:
                with (
                    mock.patch.object(
                        pilot.inherited,
                        "_win_open_handle",
                        side_effect=no_candidate_open,
                    ),
                    mock.patch.object(
                        pilot.inherited,
                        "_after_checkpoint_public_identity_verified",
                        side_effect=fail_after_identity,
                    ),
                ):
                    report = pilot._publish_post_step_rejection(
                        output,
                        progress=progress,
                        source_hashes=pilot.inherited.checkpoint_source_hashes(),
                        execution_spec_path=Path(temporary) / "execution.json",
                        execution_spec_sha256="B" * 64,
                        phase="checkpoint_identity_handoff",
                        error=RuntimeError("synthetic"),
                        directory_guard=guard,
                    )
                self.assertEqual(report["status"], "rejected")
                self.assertEqual(
                    sorted(path.name for path in output.iterdir()),
                    ["REJECTED", "candidate.pt", "rejected_receipt.json"],
                )
                self.assertEqual(
                    pilot.sha256_file(output / "candidate.pt"),
                    report["checkpoint_sha256"],
                )
            finally:
                guard.close()

    def test_real_candidate_plus_extra_and_collisions_fail_closed(self) -> None:
        source_hashes = pilot.inherited.checkpoint_source_hashes()
        with tempfile.TemporaryDirectory(dir=self._test_root()) as temporary:
            output = Path(temporary) / "output"
            guard = pilot.inherited._create_and_guard_output_directory(output)
            checkpoint_guard = None
            try:
                progress = _stage1_progress()
                metadata = pilot.checkpoint_metadata(
                    source_hashes=source_hashes, training={"test": "extra"}
                )
                (
                    checkpoint_path,
                    checkpoint_hash,
                    checkpoint_guard,
                    readback,
                ) = pilot._publish_checkpoint_exact(
                    output,
                    model=progress.model,
                    metadata=metadata,
                    optimizer=progress.optimizer,
                    directory_guard=guard,
                )
                (output / "EXTRA").write_bytes(b"poison")
                real_open = pilot.inherited._win_open_handle
                private_path = checkpoint_guard.path

                def no_candidate_open(path, **kwargs):
                    if Path(path).absolute() in {checkpoint_path, private_path}:
                        raise AssertionError("held checkpoint name reopened before contaminated status")
                    return real_open(path, **kwargs)

                with mock.patch.object(
                    pilot.inherited,
                    "_win_open_handle",
                    side_effect=no_candidate_open,
                ):
                    with self.assertRaisesRegex(ValueError, "artifact set"):
                        pilot._publish_post_step_rejection(
                            output,
                            progress=progress,
                            source_hashes=source_hashes,
                            execution_spec_path=Path(temporary) / "execution.json",
                            execution_spec_sha256="C" * 64,
                            phase="post_step",
                            error=RuntimeError("synthetic"),
                            directory_guard=guard,
                            existing_checkpoint_path=checkpoint_path,
                            existing_checkpoint_sha256=checkpoint_hash,
                            existing_checkpoint_guard=checkpoint_guard,
                            existing_checkpoint_readback=readback,
                            existing_metadata=metadata,
                        )
                self.assertEqual(
                    sorted(path.name for path in output.iterdir()),
                    sorted(["EXTRA", private_path.name, "candidate.pt"]),
                )
                self.assertFalse((output / "REJECTED").exists())
                self.assertFalse((output / "rejected_receipt.json").exists())
                checkpoint_guard.close()
                checkpoint_guard = None
                self.assertEqual(
                    sorted(path.name for path in output.iterdir()),
                    ["EXTRA", "candidate.pt"],
                )
            finally:
                if checkpoint_guard is not None:
                    checkpoint_guard.close()
                guard.close()

        for poison_name in (
            "accepted_receipt.json", "rejected_receipt.json", "ACCEPTED",
            "REJECTED", "candidate.pt", "renamed.pt",
        ):
            with self.subTest(poison=poison_name), tempfile.TemporaryDirectory(
                dir=self._test_root()
            ) as temporary:
                output = Path(temporary) / "output"
                guard = pilot.inherited._create_and_guard_output_directory(output)
                try:
                    (output / poison_name).write_bytes(b"collision")
                    progress = _stage1_progress()
                    metadata = pilot.checkpoint_metadata(
                        source_hashes=source_hashes, training={"test": poison_name}
                    )
                    with self.assertRaises(ValueError):
                        pilot._publish_checkpoint_exact(
                            output,
                            model=progress.model,
                            metadata=metadata,
                            optimizer=progress.optimizer,
                            directory_guard=guard,
                        )
                    self.assertEqual(
                        sorted(path.name for path in output.iterdir()), [poison_name]
                    )
                finally:
                    guard.close()

    def test_second_staging_looking_name_is_not_ignored(self) -> None:
        with tempfile.TemporaryDirectory(dir=self._test_root()) as temporary:
            output = Path(temporary) / "output"
            guard = pilot.inherited._create_and_guard_output_directory(output)
            checkpoint_guard = None
            try:
                progress = _stage1_progress()
                metadata = pilot.checkpoint_metadata(
                    source_hashes=pilot.inherited.checkpoint_source_hashes(),
                    training={"test": "second-staging-name"},
                )
                (
                    checkpoint_path,
                    checkpoint_hash,
                    checkpoint_guard,
                    readback,
                ) = pilot._publish_checkpoint_exact(
                    output,
                    model=progress.model,
                    metadata=metadata,
                    optimizer=progress.optimizer,
                    directory_guard=guard,
                )
                internal_name = checkpoint_guard.path.name
                second_name = ".candidate-" + "0" * 32 + ".staging.pt"
                if second_name == internal_name:
                    second_name = ".candidate-" + "1" * 32 + ".staging.pt"
                (output / second_name).write_bytes(b"unbound")
                with self.assertRaisesRegex(ValueError, "artifact set"):
                    pilot._publish_status_exact(
                        output,
                        status="rejected",
                        receipt=self._receipt("rejected"),
                        directory_guard=guard,
                        checkpoint_path=checkpoint_path,
                        checkpoint_sha256=checkpoint_hash,
                        checkpoint_guard=checkpoint_guard,
                        checkpoint_readback=readback,
                    )
                self.assertEqual(
                    sorted(path.name for path in output.iterdir()),
                    sorted([internal_name, "candidate.pt", second_name]),
                )
                self.assertFalse((output / "REJECTED").exists())
                self.assertFalse((output / "rejected_receipt.json").exists())
                checkpoint_guard.close()
                checkpoint_guard = None
                self.assertEqual(
                    sorted(path.name for path in output.iterdir()),
                    sorted(["candidate.pt", second_name]),
                )
            finally:
                if checkpoint_guard is not None:
                    checkpoint_guard.close()
                guard.close()


class InteractionMaturationRealPrepareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        candidate_root = Path(__file__).resolve().parents[1]
        test_outputs = candidate_root / "test_outputs"
        test_outputs.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=test_outputs, prefix="iteration007_fresh_runtime_"
        ) as temporary:
            output = Path(temporary) / "receipt.json"
            script = r'''from pathlib import Path
import os
from unittest import mock
import torch
from archaludon_rl import actor_only_interaction_maturation_pilot as pilot
runtime = pilot.inherited._runtime_identity()
with mock.patch.object(torch.optim, "Adam", side_effect=AssertionError("prepare constructed Adam")):
    receipt = pilot._build_prepare_receipt(runtime)
    pilot.validate_prepare_receipt(receipt)
Path(os.environ["ITERATION007_TEST_RECEIPT"]).write_bytes(
    pilot.canonical_json_bytes(receipt, newline=True)
)
'''
            environment = os.environ.copy()
            environment.update(pilot.inherited.REQUIRED_THREAD_ENVIRONMENT)
            environment["PYTHONPATH"] = str(candidate_root)
            environment["ITERATION007_TEST_RECEIPT"] = str(output)
            completed = subprocess.run(
                [sys.executable, "-c", script],
                cwd=candidate_root,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                raise AssertionError(completed.stderr)
            cls.receipt = json.loads(output.read_text(encoding="utf-8"))
        cls.runtime = dict(cls.receipt["runtime_thread_receipt"])

    def test_real_prepare_core_binds_all_rows_memberships_and_no_training(self) -> None:
        _validate_prepare_receipt_without_runtime_mutation(self.receipt)
        self.assertEqual(self.receipt["row_count"], 830)
        self.assertEqual(self.receipt["plan"]["contract"], pilot._load_plan())
        self.assertEqual(
            self.receipt["model_parameters"]["optimizer_parameter_names"],
            list(pilot.OPTIMIZER_PARAMETER_NAMES),
        )
        self.assertEqual(
            [len(self.receipt["directional_memberships"][name]) for name in (
                "negative_target_ordinals",
                "positive_normalized_teacher_and_sampled_end_ordinals",
                "positive_raw_teacher_and_sampled_end_ordinals",
                "teacher_end_ordinals",
            )],
            [4, 20, 31, 43],
        )
        self.assertEqual(
            [row["rows"] for row in self.receipt["action_families"]["families"]],
            [417, 130, 69, 1, 22, 133, 58],
        )
        for name, value in pilot._contract_bindings().items():
            self.assertEqual(self.receipt[name], value)
        self.assertEqual(
            self.receipt["prepare_audit_remediation"]["contract"],
            pilot._load_prepare_audit_remediation(),
        )
        for suffix in ("v2", "v3", "v4", "v5", "v6", "v7", "v8"):
            self.assertEqual(
                self.receipt[f"prepare_audit_remediation_{suffix}"]["contract"],
                getattr(pilot, f"_load_prepare_audit_remediation_{suffix}")(),
            )
        self.assertEqual(len(self.receipt), 54)

    def test_prepare_v1_is_byte_exact_blocked_and_exact_test_name_is_restored(self) -> None:
        blocked_path = pilot._repo_path(pilot.AUDIT_BLOCKED_PREPARE_V1_RELATIVE_PATH)
        self.assertEqual(
            pilot.sha256_file(blocked_path),
            pilot.AUDIT_BLOCKED_PREPARE_V1_FILE_SHA256,
        )
        blocked = pilot._validate_audit_blocked_prepare_v1()
        self.assertEqual(
            blocked["receipt_sha256"], pilot.AUDIT_BLOCKED_PREPARE_V1_RECEIPT_SHA256
        )
        blocked_v2_path = pilot._repo_path(
            pilot.AUDIT_BLOCKED_PREPARE_V2_RELATIVE_PATH
        )
        self.assertEqual(
            pilot.sha256_file(blocked_v2_path),
            pilot.AUDIT_BLOCKED_PREPARE_V2_FILE_SHA256,
        )
        blocked_v2 = pilot._validate_audit_blocked_prepare_v2()
        self.assertEqual(
            blocked_v2["receipt_sha256"],
            pilot.AUDIT_BLOCKED_PREPARE_V2_RECEIPT_SHA256,
        )
        blocked_v3_path = pilot._repo_path(
            pilot.AUDIT_BLOCKED_PREPARE_V3_RELATIVE_PATH
        )
        self.assertEqual(
            pilot.sha256_file(blocked_v3_path),
            pilot.AUDIT_BLOCKED_PREPARE_V3_FILE_SHA256,
        )
        blocked_v3 = pilot._validate_audit_blocked_prepare_v3()
        self.assertEqual(
            blocked_v3["receipt_sha256"],
            pilot.AUDIT_BLOCKED_PREPARE_V3_RECEIPT_SHA256,
        )
        tests = Path(__file__).resolve().parent
        self.assertTrue((tests / "test_actor_only_interaction_maturation_pilot.py").is_file())
        self.assertFalse((tests / "test_actor_only_z_interaction_maturation_pilot.py").exists())

    def test_invalid_existing_alias_and_reparse_prepare_paths_fail_before_optimizer(self) -> None:
        candidate_root = pilot._repo_path(pilot.IMPLEMENTATION_RELATIVE_PATH)
        invalid = {
            "existing_v1": pilot._repo_path(pilot.AUDIT_BLOCKED_PREPARE_V1_RELATIVE_PATH),
            "existing_v2": pilot._repo_path(pilot.AUDIT_BLOCKED_PREPARE_V2_RELATIVE_PATH),
            "existing_v3": pilot._repo_path(pilot.AUDIT_BLOCKED_PREPARE_V3_RELATIVE_PATH),
            "traversal": candidate_root / "test_outputs" / ".." / pilot.PREPARE_OUTPUT_FILENAME,
            "outside": candidate_root.parent / pilot.PREPARE_OUTPUT_FILENAME,
        }
        for name, path in invalid.items():
            with self.subTest(name=name), mock.patch.object(
                torch.optim, "Adam", side_effect=AssertionError("optimizer constructed")
            ):
                with self.assertRaises((ValueError, FileExistsError)):
                    pilot.prepare(output_receipt=path)
        approved = pilot._repo_path(pilot.APPROVED_PREPARE_RELATIVE_PATH).absolute()
        real_exists = Path.exists

        def existing_exact(path: Path) -> bool:
            if path.absolute() == approved:
                return True
            return real_exists(path)

        with (
            mock.patch.object(Path, "exists", autospec=True, side_effect=existing_exact),
            mock.patch.object(
                torch.optim, "Adam", side_effect=AssertionError("optimizer constructed")
            ),
        ):
            with self.assertRaises(FileExistsError):
                pilot.prepare(output_receipt=approved)
        for kind in ("symlink", "junction", "reparse"):
            with (
                self.subTest(kind=kind),
                mock.patch.object(
                    pilot.inherited, "_is_link_or_reparse", return_value=True
                ),
                mock.patch.object(
                    torch.optim,
                    "Adam",
                    side_effect=AssertionError("optimizer constructed"),
                ),
            ):
                with self.assertRaises(ValueError):
                    pilot.prepare(
                        output_receipt=pilot._repo_path(
                            pilot.APPROVED_PREPARE_RELATIVE_PATH
                        )
                    )
        self.assertEqual(
            self.receipt["prepare_proof"],
            {
                "optimizer_constructed": False,
                "optimizer_steps": 0,
                "checkpoint_written": False,
                "parameters_changed": False,
                "rejected_checkpoint_loaded": False,
                "training_executed": False,
                "runtime_smoke_executed": False,
                "games_run": 0,
            },
        )

    def test_nested_provenance_failures_are_rejected_without_optimizer(self) -> None:
        mutations = {
            "plan": lambda row: row["plan"].update({"file_sha256": "0" * 64}),
            "remediation": lambda row: row["prepare_audit_remediation"].update(
                {"file_sha256": "9" * 64}
            ),
            "remediation_pair": lambda row: row.update(
                {"prepare_audit_remediation_sha256": "8" * 64}
            ),
            "remediation_v6": lambda row: row[
                "prepare_audit_remediation_v6"
            ].update({"file_sha256": "7" * 64}),
            "remediation_v6_pair": lambda row: row.update(
                {"prepare_audit_remediation_v6_sha256": "6" * 64}
            ),
            "remediation_v7": lambda row: row[
                "prepare_audit_remediation_v7"
            ].update({"file_sha256": "5" * 64}),
            "remediation_v7_pair": lambda row: row.update(
                {"prepare_audit_remediation_v7_sha256": "4" * 64}
            ),
            "remediation_v8": lambda row: row[
                "prepare_audit_remediation_v8"
            ].update({"file_sha256": "3" * 64}),
            "remediation_v8_pair": lambda row: row.update(
                {"prepare_audit_remediation_v8_sha256": "2" * 64}
            ),
            "parent": lambda row: row["parent_rejection"].update({"decision": "ACCEPT"}),
            "rejected_checkpoint": lambda row: row["immutable_inputs"].update(
                {"input_checkpoint_sha256": pilot.REJECTED_CHECKPOINT_SHA256}
            ),
            "input": lambda row: row["immutable_inputs"].update(
                {"input_checkpoint_sha256": "1" * 64}
            ),
            "dataset": lambda row: row["immutable_inputs"].update(
                {"dataset_sha256": "2" * 64}
            ),
            "row": lambda row: row["rows"][0].update({"sampled_index": 999}),
            "family": lambda row: row["action_families"]["families"][0].update(
                {"membership_sha256": "3" * 64}
            ),
            "fixed_input": lambda row: row["rows"][0].update(
                {"fixed_normalized_advantage_float32": 999.0}
            ),
            "source": lambda row: row["source_implementation"].update(
                {"sha256": "4" * 64}
            ),
            "runtime": lambda row: row["runtime_thread_receipt"][
                "observed_thread_counts"
            ].update({"torch_num_threads": 2}),
            "schedule": lambda row: row["training_contract"]["stage_2"].update(
                {"optimizer_step_count": 31}
            ),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name), mock.patch.object(
                torch.optim, "Adam", side_effect=AssertionError("optimizer constructed")
            ):
                candidate = deepcopy(self.receipt)
                mutation(candidate)
                _rehash(candidate)
                with self.assertRaises((ValueError, IndexError)):
                    _validate_prepare_receipt_without_runtime_mutation(candidate)

    def test_raw_probability_recomputation_rejects_claimed_kl_and_tv(self) -> None:
        fixed, metric = InteractionMaturationCorrectionTests._one_row_metric(
            [0.61, 0.39]
        )
        metric["anchor_kl_post_to_zero"] = 0.0
        metric["total_variation_from_initial"] = 0.0
        with mock.patch.object(pilot, "EXPECTED_ON_POLICY_ROWS", 1):
            _, failures, _ = pilot._validated_metric_rows({"rows": [fixed]}, [metric])
        self.assertIn("row:0:anchor_kl_recomputation", failures)
        self.assertIn("row:0:total_variation_recomputation", failures)

    def test_execution_spec_exact_44_keys_and_unmodified_subobjects(self) -> None:
        plan = pilot._load_plan()
        spec = {
            "schema_version": pilot.EXECUTION_SPEC_SCHEMA_VERSION,
            "implementation_plan_path": pilot.PLAN_RELATIVE_PATH.as_posix(),
            "implementation_plan_sha256": pilot.PLAN_SHA256,
            "plan_correction_path": pilot.CORRECTION_RELATIVE_PATH.as_posix(),
            "plan_correction_sha256": pilot.CORRECTION_SHA256,
            "plan_correction_v2_path": pilot.CORRECTION_V2_RELATIVE_PATH.as_posix(),
            "plan_correction_v2_sha256": pilot.CORRECTION_V2_SHA256,
            "prepare_audit_remediation_path": (
                pilot.PREPARE_AUDIT_REMEDIATION_RELATIVE_PATH.as_posix()
            ),
            "prepare_audit_remediation_sha256": (
                pilot.PREPARE_AUDIT_REMEDIATION_SHA256
            ),
            "prepare_audit_remediation_v2_path": (
                pilot.PREPARE_AUDIT_REMEDIATION_V2_RELATIVE_PATH.as_posix()
            ),
            "prepare_audit_remediation_v2_sha256": (
                pilot.PREPARE_AUDIT_REMEDIATION_V2_SHA256
            ),
            "prepare_audit_remediation_v3_path": (
                pilot.PREPARE_AUDIT_REMEDIATION_V3_RELATIVE_PATH.as_posix()
            ),
            "prepare_audit_remediation_v3_sha256": (
                pilot.PREPARE_AUDIT_REMEDIATION_V3_SHA256
            ),
            "prepare_audit_remediation_v4_path": (
                pilot.PREPARE_AUDIT_REMEDIATION_V4_RELATIVE_PATH.as_posix()
            ),
            "prepare_audit_remediation_v4_sha256": (
                pilot.PREPARE_AUDIT_REMEDIATION_V4_SHA256
            ),
            "prepare_audit_remediation_v5_path": (
                pilot.PREPARE_AUDIT_REMEDIATION_V5_RELATIVE_PATH.as_posix()
            ),
            "prepare_audit_remediation_v5_sha256": (
                pilot.PREPARE_AUDIT_REMEDIATION_V5_SHA256
            ),
            "prepare_audit_remediation_v6_path": (
                pilot.PREPARE_AUDIT_REMEDIATION_V6_RELATIVE_PATH.as_posix()
            ),
            "prepare_audit_remediation_v6_sha256": (
                pilot.PREPARE_AUDIT_REMEDIATION_V6_SHA256
            ),
            "prepare_audit_remediation_v7_path": (
                pilot.PREPARE_AUDIT_REMEDIATION_V7_RELATIVE_PATH.as_posix()
            ),
            "prepare_audit_remediation_v7_sha256": (
                pilot.PREPARE_AUDIT_REMEDIATION_V7_SHA256
            ),
            "prepare_audit_remediation_v8_path": (
                pilot.PREPARE_AUDIT_REMEDIATION_V8_RELATIVE_PATH.as_posix()
            ),
            "prepare_audit_remediation_v8_sha256": (
                pilot.PREPARE_AUDIT_REMEDIATION_V8_SHA256
            ),
            "parent_result_path": pilot.PARENT_RESULT_RELATIVE_PATH.as_posix(),
            "parent_result_sha256": pilot.PARENT_RESULT_SHA256,
            "prepare_receipt_path": pilot.APPROVED_PREPARE_RELATIVE_PATH.as_posix(),
            "prepare_receipt_file_sha256": "A" * 64,
            "prepare_receipt_sha256": "B" * 64,
            "implementation_path": pilot.IMPLEMENTATION_RELATIVE_PATH.as_posix(),
            "implementation_snapshot_sha256": self.receipt["implementation"]["sha256"],
            "input_checkpoint_path": pilot.INPUT_CHECKPOINT_RELATIVE_PATH.as_posix(),
            "input_checkpoint_sha256": pilot.INPUT_CHECKPOINT_SHA256,
            "forbidden_rejected_checkpoint_sha256s": list(
                pilot.FORBIDDEN_REJECTED_CHECKPOINT_SHA256S
            ),
            "manifest_path": pilot.MANIFEST_RELATIVE_PATH.as_posix(),
            "manifest_sha256": pilot.MANIFEST_SHA256,
            "dataset_sha256": pilot.DATASET_SHA256,
            "fixed_advantages_sha256": pilot.FIXED_ADVANTAGES_SHA256,
            "fixed_behavior_logprobabilities_sha256": (
                pilot.FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256
            ),
            "runtime_thread_receipt": self.runtime,
            "training_contract": plan["training_contract"],
            "diagnostic_contract": plan["diagnostic_contract"],
            "safety_gates": plan["safety_gates"],
            "terminal_offline_acceptance": plan["terminal_offline_acceptance"],
            "output_directory": pilot.APPROVED_OUTPUT_RELATIVE_PATH.as_posix(),
        }
        self.assertEqual(len(spec), 44)
        test_root = pilot._repo_path(pilot.IMPLEMENTATION_RELATIVE_PATH) / "test_outputs"
        test_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=test_root) as temporary:
            path = Path(temporary) / "execution.json"

            def write_and_load(value: dict):
                payload = pilot.canonical_json_bytes(value, newline=True)
                path.write_bytes(payload)
                return pilot._load_execution_spec(
                    path, pilot.hashlib.sha256(payload).hexdigest().upper()
                )

            self.assertEqual(write_and_load(spec), spec)
            mutations = {
                "missing": lambda row: row.pop("manifest_sha256"),
                "extra": lambda row: row.update({"extra": True}),
                "v1_hash": lambda row: row.update({"plan_correction_sha256": "0" * 64}),
                "v2_hash": lambda row: row.update({"plan_correction_v2_sha256": "1" * 64}),
                "remediation_hash": lambda row: row.update(
                    {"prepare_audit_remediation_sha256": "2" * 64}
                ),
                "remediation_v5_hash": lambda row: row.update(
                    {"prepare_audit_remediation_v5_sha256": "3" * 64}
                ),
                "remediation_v6_hash": lambda row: row.update(
                    {"prepare_audit_remediation_v6_sha256": "4" * 64}
                ),
                "remediation_v7_hash": lambda row: row.update(
                    {"prepare_audit_remediation_v7_sha256": "5" * 64}
                ),
                "remediation_v8_hash": lambda row: row.update(
                    {"prepare_audit_remediation_v8_sha256": "6" * 64}
                ),
                "subobject": lambda row: row["training_contract"]["stage_2"].update(
                    {"optimizer_step_count": 31}
                ),
                "traversal": lambda row: row.update({"output_directory": "_local_generated/analysis_outputs/../escape"}),
            }
            for name, mutation in mutations.items():
                with self.subTest(name=name), mock.patch.object(
                    torch.optim, "Adam", side_effect=AssertionError("optimizer constructed")
                ):
                    candidate = deepcopy(spec)
                    mutation(candidate)
                    with self.assertRaises(ValueError):
                        write_and_load(candidate)


if __name__ == "__main__":
    unittest.main()
