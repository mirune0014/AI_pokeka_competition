from __future__ import annotations

import copy
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock
import uuid

import torch

from archaludon_rl import mass_preserving_pcgrad_pilot as pilot


def gradient_map(vector: list[float], *, dtype: torch.dtype = torch.float32):
    tensor = torch.tensor(vector, dtype=dtype)
    return {
        "residual_head.0.weight": tensor[:1].reshape(1, 1),
        "residual_head.0.bias": tensor[1:],
    }


def task_gradients(vectors):
    return {name: gradient_map(list(vectors.get(name, [0.0, 0.0]))) for name in pilot.TASK_ORDER}


def predecessor_stop_binding():
    return {
        "execution_spec_path": (
            pilot.PREDECESSOR_EXECUTION_SPEC_RELATIVE_PATH.as_posix()
        ),
        "execution_spec_sha256": pilot.PREDECESSOR_EXECUTION_SPEC_SHA256,
        "manifest_path": pilot.PREDECESSOR_STOP_MANIFEST_RELATIVE_PATH.as_posix(),
        "manifest_file_sha256": pilot.PREDECESSOR_STOP_MANIFEST_FILE_SHA256,
        "manifest_core_sha256": pilot.PREDECESSOR_STOP_MANIFEST_CORE_SHA256,
        "completed_optimizer_steps_per_arm": {
            "control_vanilla": 1, "treatment_pcgrad": 1,
        },
        "completed_stage2_updates": 0,
        "games_run": 0,
        "immutable_implementation_stop": True,
        "resume_permitted": False,
    }


def attach_control_legacy_evidence(
    item, pre_step_parameters, pre_step_optimizer_state, layout
):
    authoritative = item["combined_preclip_gradient"].detach().clone()
    independent = authoritative.clone()
    split = (
        item["direct_policy_gradient"].to(torch.float32)
        + item["anchor_kl_gradient"]
    )
    independent_parts = pilot._split_flat_by_layout(independent, layout)
    guard = {
        "model_state": "A" * 64,
        "optimizer_state": "B" * 64,
        "grad_state": "C" * 64,
        "cpu_rng_state": "D" * 64,
    }
    item.update({
        "authoritative_legacy_preclip_gradient": authoritative,
        "authoritative_legacy_preclip_sha256": pilot._tensor_sha256_v2(
            authoritative
        ),
        "independent_rowwise_joint_vjp": independent,
        "independent_rowwise_joint_vjp_sha256": pilot._tensor_sha256_v2(
            independent
        ),
        "independent_rowwise_joint_vjp_parameter_sha256": {
            name: pilot._tensor_sha256_v2(independent_parts[name])
            for name in pilot.PARAMETER_NAMES
        },
        "split_direct_plus_anchor_gradient": split,
        "control_decomposition": pilot.validate_control_decomposition(
            authoritative, split
        ),
        "pre_step_policy_parameter_state": copy.deepcopy(pre_step_parameters),
        "pre_step_optimizer_state": copy.deepcopy(pre_step_optimizer_state),
        "pre_step_identity": pilot._control_pre_step_identity_v5(
            pre_step_parameters, pre_step_optimizer_state
        ),
        "isolated_audit_guard_hashes_before": copy.deepcopy(guard),
        "isolated_audit_guard_hashes_after": copy.deepcopy(guard),
        "capture_hook_counts": {name: 1 for name in pilot.PARAMETER_NAMES},
    })


class ToyModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.residual_head = torch.nn.Sequential(
            torch.nn.Linear(1, 1),
            torch.nn.ReLU(),
            torch.nn.Linear(1, 1),
        )


def toy_optimizer(model: ToyModel) -> torch.optim.Adam:
    named = dict(model.named_parameters())
    return torch.optim.Adam(
        [named[name] for name in pilot.OPTIMIZER_PARAMETER_NAMES],
        lr=1e-4,
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


class StaticOptimizerState:
    """Checkpoint-only holder that cannot construct or step an optimizer."""

    def __init__(self, state):
        self._state = copy.deepcopy(state)

    def state_dict(self):
        return copy.deepcopy(self._state)


class PartitionTests(unittest.TestCase):
    def rows(self):
        result = []
        tasks = list(pilot.PRIORITY_TASKS)
        for ordinal in range(pilot.EXPECTED_ROWS):
            task = tasks[ordinal % len(tasks)] if ordinal < 600 else "REMAINING_ROWS"
            if task == "REMAINING_ROWS":
                option_type, advantage = 10, 1.0
            else:
                family, polarity = task.split(":")
                option_type = pilot.OPTION_TYPE_BY_FAMILY[family]
                advantage = 1.0 if polarity == "positive" else -1.0
            result.append({
                "ppo_row_ordinal": ordinal,
                "sampled_option_type": option_type,
                "fixed_normalized_advantage_float32": advantage,
            })
        return result

    def test_partition_is_disjoint_and_covers_exactly_830(self):
        partition = pilot.build_task_partition(self.rows())
        pilot.validate_task_partition(partition)
        all_rows = [value for name in pilot.TASK_ORDER for value in partition[name]]
        self.assertEqual(sorted(all_rows), list(range(830)))
        self.assertEqual(len(all_rows), len(set(all_rows)))
        self.assertTrue(partition["REMAINING_ROWS"])

    def test_partition_rejects_duplicate_gap_and_wrong_key_order(self):
        partition = pilot.build_task_partition(self.rows())
        broken = copy.deepcopy(partition)
        broken["PLAY:positive"].append(broken["ATTACH:negative"][0])
        with self.assertRaisesRegex(ValueError, "sorted and unique"):
            pilot.validate_task_partition(broken)
        reversed_keys = dict(reversed(list(partition.items())))
        with self.assertRaisesRegex(ValueError, "key order"):
            pilot.validate_task_partition(reversed_keys)

    def test_task_receipt_binds_common_denominator_not_equal_task_mass(self):
        receipt = pilot.task_membership_receipt(pilot.build_task_partition(self.rows()))
        self.assertEqual(receipt["common_denominator"], 830)
        self.assertFalse(receipt["equal_task_weighting"])
        self.assertTrue(all(row["common_denominator"] == 830 for row in receipt["tasks"]))


class PcgradTests(unittest.TestCase):
    def test_autograd_task_losses_preserve_one_over_830_row_mass(self):
        parameter = torch.tensor(0.25, dtype=torch.float32, requires_grad=True)
        coefficients = torch.linspace(0.1, 2.0, pilot.EXPECTED_ROWS)
        memberships = {
            name: list(range(index, pilot.EXPECTED_ROWS, len(pilot.TASK_ORDER)))
            for index, name in enumerate(pilot.TASK_ORDER)
        }
        task_values = []
        for name in pilot.TASK_ORDER:
            loss = torch.stack(
                [parameter * coefficients[index] for index in memberships[name]]
            ).sum() / pilot.COMMON_DENOMINATOR
            task_values.append(torch.autograd.grad(loss, parameter, retain_graph=True)[0])
        direct = torch.autograd.grad(
            torch.stack([parameter * value for value in coefficients]).mean(),
            parameter,
        )[0]
        self.assertTrue(torch.allclose(torch.stack(task_values).sum(), direct))
        self.assertNotAlmostEqual(
            float(torch.stack(task_values).mean()), float(direct), places=7
        )

    def test_cyclic_orders_are_exact_and_repeat_after_seven(self):
        for update in range(1, 8):
            offset = update - 1
            self.assertEqual(
                pilot.cyclic_task_order(update),
                pilot.TASK_ORDER[offset:] + pilot.TASK_ORDER[:offset],
            )
        self.assertEqual(pilot.cyclic_task_order(1), pilot.cyclic_task_order(8))

    def test_negative_dot_projection_uses_original_other_gradient(self):
        vectors = {
            "PLAY:positive": [1.0, 1.0],
            "ATTACH:negative": [-1.0, 0.0],
            "EVOLVE:negative": [0.0, -1.0],
        }
        # Sum all tasks exactly to the direct gradient.
        direct = [0.0, 0.0]
        result, evidence = pilot.pcgrad_project(
            task_gradients(vectors), gradient_map(direct), update_ordinal=1
        )
        events = evidence["projection_events"]
        first = next(row for row in events if row["task"] == "PLAY:positive" and row["other"] == "ATTACH:negative")
        second = next(row for row in events if row["task"] == "PLAY:positive" and row["other"] == "EVOLVE:negative")
        self.assertEqual(first["coefficient"], -1.0)
        self.assertEqual(second["coefficient"], -1.0)
        self.assertEqual(tuple(result), pilot.PARAMETER_NAMES)

    def test_zero_norm_is_skipped_and_recorded(self):
        vectors = {"PLAY:positive": [1.0, 0.0], "ATTACH:negative": [-1.0, 0.0]}
        _, evidence = pilot.pcgrad_project(
            task_gradients(vectors), gradient_map([0.0, 0.0]), update_ordinal=1
        )
        self.assertTrue(evidence["zero_norm_skips"])

    def test_nonfinite_task_and_projection_fail_hard(self):
        gradients = task_gradients({})
        gradients["PLAY:positive"]["residual_head.0.weight"][0, 0] = math.nan
        with self.assertRaises(FloatingPointError):
            pilot.pcgrad_project(gradients, gradient_map([0.0, 0.0]), update_ordinal=1)

    def test_float64_surgery_then_one_float32_cast(self):
        vectors = {"PLAY:positive": [1.0, 0.0], "ATTACH:negative": [-0.25, 1.0]}
        direct = [0.75, 1.0]
        result, evidence = pilot.pcgrad_project(
            task_gradients(vectors), gradient_map(direct), update_ordinal=3
        )
        self.assertEqual(evidence["projection_numeric_domain"], "cpu_float64")
        self.assertEqual(evidence["float32_cast_count_per_parameter"], 1)
        self.assertTrue(all(value.dtype == torch.float32 for value in result.values()))

    def test_unsurgeried_sum_tolerance_boundaries(self):
        direct = torch.ones(2, dtype=torch.float64)
        tasks = {name: torch.zeros(2, dtype=torch.float64) for name in pilot.TASK_ORDER}
        tasks[pilot.TASK_ORDER[0]] = direct.clone()
        evidence = pilot.validate_unsurgeried_sum(tasks, direct)
        self.assertEqual(evidence["maximum_absolute_difference"], 0.0)
        boundary = torch.tensor(1.0 + pilot.MAX_ABSOLUTE_SUM_DIFFERENCE, dtype=torch.float64)
        below = torch.nextafter(boundary, torch.tensor(1.0, dtype=torch.float64))
        above = torch.nextafter(boundary, torch.tensor(math.inf, dtype=torch.float64))
        tasks[pilot.TASK_ORDER[0]] = torch.tensor([float(below), 1.0], dtype=torch.float64)
        pilot.validate_unsurgeried_sum(tasks, direct)
        tasks[pilot.TASK_ORDER[0]] = torch.tensor([float(above), 1.0], dtype=torch.float64)
        with self.assertRaisesRegex(ValueError, "unsurgeried"):
            pilot.validate_unsurgeried_sum(tasks, direct)

    def test_relative_tolerance_boundary_is_enforced_independently(self):
        direct = torch.tensor([1e-8, 0.0], dtype=torch.float64)
        tasks = {name: torch.zeros(2, dtype=torch.float64) for name in pilot.TASK_ORDER}
        tasks[pilot.TASK_ORDER[0]] = direct + torch.tensor([2e-13, 0.0], dtype=torch.float64)
        with self.assertRaisesRegex(ValueError, "unsurgeried"):
            pilot.validate_unsurgeried_sum(tasks, direct)


class OptimizerOrderingTests(unittest.TestCase):
    def test_policy_then_kl_then_clip_then_adam(self):
        model = ToyModel()
        optimizer = toy_optimizer(model)
        policy = gradient_map([3.0, 4.0])
        anchor = gradient_map([1.0, 0.0])
        report = pilot.apply_policy_kl_clip_adam(
            model=model,
            optimizer=optimizer,
            policy_gradient=policy,
            kl_gradient=anchor,
        )
        self.assertEqual(
            report["ordering"],
            ["policy_gradient", "anchor_kl_gradient", "global_norm_clip", "adam_step"],
        )
        self.assertAlmostEqual(report["global_gradient_norm_before_clip"], math.sqrt(32.0), places=5)
        self.assertEqual(
            pilot.optimizer_step_states(optimizer, model),
            {"residual_head.0.weight": 1, "residual_head.0.bias": 1},
        )

    def test_nonfinite_kl_fails_before_adam(self):
        model = ToyModel()
        optimizer = toy_optimizer(model)
        anchor = gradient_map([math.inf, 0.0])
        with self.assertRaises(FloatingPointError):
            pilot.apply_policy_kl_clip_adam(
                model=model,
                optimizer=optimizer,
                policy_gradient=gradient_map([0.0, 0.0]),
                kl_gradient=anchor,
            )
        self.assertFalse(optimizer.state)

    def test_optimizer_canonicalization_is_deterministic(self):
        model = ToyModel()
        optimizer = toy_optimizer(model)
        pilot.apply_policy_kl_clip_adam(
            model=model,
            optimizer=optimizer,
            policy_gradient=gradient_map([1.0, -1.0]),
            kl_gradient=gradient_map([0.0, 0.0]),
        )
        left = pilot.optimizer_canonical_record(optimizer, model)
        right = pilot.optimizer_canonical_record(optimizer, model)
        self.assertEqual(left, right)
        self.assertEqual(len(left["canonical_sha256"]), 64)


class LegacyControlV5UnitTests(unittest.TestCase):
    def test_control_decomposition_known_rounding_and_independent_bounds(self):
        actual = torch.full((18528,), 4e-7, dtype=torch.float32)
        split = actual.clone()
        split[:100] += torch.tensor(4.8e-12, dtype=torch.float32)
        evidence = pilot.validate_control_decomposition(actual, split)
        self.assertTrue(evidence["passed"])
        self.assertLessEqual(
            evidence["maximum_absolute_error"],
            evidence["maximum_absolute_error_bound_inclusive"],
        )
        self.assertLessEqual(
            evidence["difference_l2"], evidence["l2_error_bound_inclusive"]
        )

        just_above = torch.nextafter(
            torch.tensor(
                pilot.CONTROL_DECOMPOSITION_MAX_ABSOLUTE_ERROR,
                dtype=torch.float32,
            ),
            torch.tensor(math.inf, dtype=torch.float32),
        )
        with self.assertRaisesRegex(ValueError, "v5 tolerance"):
            pilot.validate_control_decomposition(
                torch.zeros(1, dtype=torch.float32), just_above.reshape(1)
            )

        l2_only = torch.full((36,), 1.9e-11, dtype=torch.float32)
        self.assertLessEqual(
            float(l2_only.abs().max()),
            pilot.CONTROL_DECOMPOSITION_MAX_ABSOLUTE_ERROR,
        )
        self.assertGreater(float(torch.linalg.vector_norm(l2_only.to(torch.float64))), 1e-10)
        with self.assertRaisesRegex(ValueError, "v5 tolerance"):
            pilot.validate_control_decomposition(
                torch.zeros_like(l2_only), l2_only
            )

    def test_dispatcher_uses_legacy_control_64_and_treatment_pcgrad_64(self):
        with (
            mock.patch.object(
                pilot, "_control_reference_step", return_value={"legacy": True}
            ) as legacy,
            mock.patch.object(
                pilot, "_custom_stage2_step", return_value={"pcgrad": True}
            ) as custom,
        ):
            for update in range(1, 65):
                pilot._dispatch_stage2_step(
                    arm="control_vanilla", loaded={}, prepare_receipt={},
                    partition={}, state={}, update_ordinal=update,
                )
                pilot._dispatch_stage2_step(
                    arm="treatment_pcgrad", loaded={}, prepare_receipt={},
                    partition={}, state={
                        "optimizer": object(), "stage2_start_parameters": {}
                    }, update_ordinal=update,
                )
        self.assertEqual(legacy.call_count, 64)
        self.assertEqual(custom.call_count, 64)
        self.assertTrue(all(
            call.kwargs["arm"] == "treatment_pcgrad"
            for call in custom.call_args_list
        ))


class LegacyControlV5RealPathTests(unittest.TestCase):
    def test_real_830_row_stage1_retained_control_matches_inherited_base(self):
        runtime = pilot.inherited._runtime_identity()
        receipt = pilot._corrected_prepare_receipt(runtime)
        pilot.validate_prepare_receipt(receipt)
        self.assertEqual(
            receipt["correction_v5"]["file_sha256"],
            pilot.CORRECTION_V5_SHA256,
        )
        self.assertEqual(
            receipt["predecessor_execution_stop"], predecessor_stop_binding()
        )
        self.assertEqual(receipt["prepare_proof"]["optimizer_steps"], 0)
        self.assertFalse(receipt["prepare_proof"]["training_executed"])
        self.assertFalse(receipt["prepare_proof"]["runtime_smoke_executed"])
        self.assertEqual(receipt["prepare_proof"]["games_run"], 0)
        partition = pilot._fixed_partition_from_receipt(receipt)
        loaded = pilot._load_execution_arms(receipt)["control_vanilla"]
        candidate_state = pilot._new_stage1_state(loaded)
        pilot._transactional_stage1_step(candidate_state, loaded, receipt)

        direct_model = copy.deepcopy(candidate_state["model"])
        for parameter in direct_model.parameters():
            parameter.grad = None
        direct_loaded = dict(loaded)
        direct_loaded["model"] = direct_model
        direct_optimizer = pilot.base._new_actor_adam(direct_model)
        direct_optimizer.load_state_dict(copy.deepcopy(
            candidate_state["stage2_start_optimizer_state"]
        ))
        direct_progress = pilot.base.ExecutionProgress(
            model=direct_model,
            optimizer=direct_optimizer,
            optimizer_steps_completed=1,
        )
        rng_before = torch.get_rng_state().clone()
        candidate_step = pilot._control_reference_step(
            loaded=loaded,
            prepare_receipt=receipt,
            partition=partition,
            state=candidate_state,
            update_ordinal=1,
        )
        direct_report = pilot.base._stage_full_batch_step(
            stage=2,
            stage_2_update_ordinal=1,
            loaded=direct_loaded,
            prepare_receipt=receipt,
            optimizer=direct_optimizer,
            initial_parameters=candidate_state["initial_parameters"],
            progress=direct_progress,
            stage_2_start_parameters=candidate_state[
                "stage2_start_parameters"
            ],
        )
        candidate_metrics = pilot.base._measure_stage(
            loaded, receipt, stage=2, stage_2_update_ordinal=1
        )
        direct_metrics = pilot.base._measure_stage(
            direct_loaded, receipt, stage=2, stage_2_update_ordinal=1
        )
        self.assertTrue(torch.equal(rng_before, torch.get_rng_state()))
        self.assertTrue(pilot._nested_byte_exact_v2(
            candidate_state["model"].state_dict(), direct_model.state_dict()
        ))
        self.assertTrue(pilot._nested_byte_exact_v2(
            candidate_state["optimizer"].state_dict(),
            direct_optimizer.state_dict(),
        ))
        self.assertEqual(
            candidate_step["legacy_step_report"], direct_report
        )
        self.assertEqual(
            pilot.base._ordered_output_hashes(candidate_metrics),
            pilot.base._ordered_output_hashes(direct_metrics),
        )
        candidate_named = dict(candidate_state["model"].named_parameters())
        direct_named = dict(direct_model.named_parameters())
        for name in pilot.PARAMETER_NAMES:
            self.assertTrue(torch.equal(
                candidate_named[name].grad, direct_named[name].grad
            ))
            self.assertFalse(candidate_named[name]._backward_hooks)
        evidence = candidate_step["tensor_evidence"]
        self.assertEqual(
            evidence["capture_hook_counts"],
            {name: 1 for name in pilot.PARAMETER_NAMES},
        )
        self.assertEqual(
            evidence["isolated_audit_guard_hashes_before"],
            evidence["isolated_audit_guard_hashes_after"],
        )
        self.assertEqual(
            evidence["authoritative_legacy_preclip_sha256"],
            evidence["independent_rowwise_joint_vjp_sha256"],
        )
        self.assertTrue(evidence["control_decomposition"]["passed"])


class RawRecomputationV2Tests(unittest.TestCase):
    @staticmethod
    def synthetic_prepare_and_output():
        zero = torch.tensor(0.0, dtype=torch.float32).numpy().tobytes(order="C")
        rows = []
        for ordinal in range(pilot.EXPECTED_ROWS):
            rows.append({
                "ppo_row_ordinal": ordinal,
                "public_state_sha256": f"{ordinal:064X}",
                "behavior_action_order_sha256": f"{ordinal + 1:064X}",
                "sampled_index": 0,
                "teacher_index": 0,
                "end_index": 1,
                "legal_option_count": 2,
                "sampled_option_type": 7,
                "sampled_semantic_identity": ["PLAY", ordinal],
                "initial_probabilities_float32": [0.5, 0.5],
                "initial_value_float32": 0.0,
                "initial_value_raw_bytes_hex": zero.hex().upper(),
                "initial_value_byte_sha256": hashlib.sha256(zero).hexdigest().upper(),
                "fixed_normalized_advantage_float32": 1.0,
                "behavior_logprob_float64": math.log(0.5),
            })
        output = {
            "probabilities": torch.full(
                (2 * pilot.EXPECTED_ROWS,), 0.5, dtype=torch.float32
            ),
            "probability_offsets": torch.arange(
                0, 2 * pilot.EXPECTED_ROWS + 1, 2, dtype=torch.int64
            ),
            "values": torch.zeros(pilot.EXPECTED_ROWS, dtype=torch.float32),
        }
        return {"rows": rows}, output

    def synthetic_one_update_bundle(self, arm):
        prepare, output = self.synthetic_prepare_and_output()
        model_state = {
            "residual_head.0.weight": torch.tensor([[0.25]], dtype=torch.float32),
            "residual_head.0.bias": torch.tensor([-0.5], dtype=torch.float32),
        }
        optimizer_state = self.adam_state()
        optimizer_state["state"] = {
            2: {
                "step": torch.tensor(1.0, dtype=torch.float32),
                "exp_avg": torch.zeros(1, dtype=torch.float32),
                "exp_avg_sq": torch.zeros(1, dtype=torch.float32),
            },
            3: {
                "step": torch.tensor(1.0, dtype=torch.float32),
                "exp_avg": torch.zeros(1, dtype=torch.float32),
                "exp_avg_sq": torch.zeros(1, dtype=torch.float32),
            },
        }
        raw = {
            task: torch.zeros(2, dtype=torch.float64)
            for task in pilot.TASK_ORDER
        }
        raw["PLAY:positive"] = torch.tensor([1.0, 1.0], dtype=torch.float64)
        raw["ATTACH:negative"] = torch.tensor([-1.0, 0.0], dtype=torch.float64)
        raw["EVOLVE:negative"] = torch.tensor([0.0, -1.0], dtype=torch.float64)
        direct = sum(
            (raw[task] for task in pilot.TASK_ORDER),
            torch.zeros(2, dtype=torch.float64),
        )
        item = {
            "raw_task_gradients": copy.deepcopy(raw),
            "direct_policy_gradient": direct.clone(),
        }
        if arm == "treatment_pcgrad":
            projected, policy = pilot._recompute_pcgrad_flat(raw, update_ordinal=1)
            item["projected_task_gradients"] = projected
        else:
            policy = direct
        anchor = torch.tensor([0.01, -0.02], dtype=torch.float32)
        preclip = policy.to(torch.float32) + anchor
        layout = [
            {
                "name": "residual_head.0.weight", "shape": [1, 1],
                "numel": 1, "dtype": "torch.float32",
            },
            {
                "name": "residual_head.0.bias", "shape": [1],
                "numel": 1, "dtype": "torch.float32",
            },
        ]
        postclip, _total_norm, coefficient = pilot._exact_postclip_flat(
            preclip, layout
        )
        parameters = copy.deepcopy(model_state)
        replay_state = copy.deepcopy(optimizer_state)
        pre_step_parameters = copy.deepcopy(parameters)
        pre_step_optimizer_state = copy.deepcopy(replay_state)
        actual_by_name = pilot._manual_adam_step(
            parameters, replay_state,
            pilot._split_flat_by_layout(postclip, layout),
        )
        actual = torch.cat([
            actual_by_name[name].reshape(-1) for name in pilot.PARAMETER_NAMES
        ])
        cumulative = torch.cat([
            (parameters[name] - model_state[name]).reshape(-1)
            for name in pilot.PARAMETER_NAMES
        ])
        item.update({
            "anchor_kl_gradient": anchor,
            "combined_preclip_gradient": preclip,
            "combined_postclip_gradient": postclip,
            "postclip_coefficient": float(coefficient),
            "actual_parameter_delta": actual,
            "cumulative_parameter_delta": cumulative,
            "policy_parameter_state_after": copy.deepcopy(parameters),
            "optimizer_state_after": copy.deepcopy(replay_state),
            "optimizer_step_counters": {
                "residual_head.0.weight": 1,
                "residual_head.0.bias": 1,
                "residual_head.2.weight": 1,
                "residual_head.2.bias": 1,
            },
            "ordered_outputs": copy.deepcopy(output),
        })
        if arm == "control_vanilla":
            attach_control_legacy_evidence(
                item, pre_step_parameters, pre_step_optimizer_state, layout
            )
        gradients = {
            "parameter_names": list(pilot.PARAMETER_NAMES),
            "parameter_layout": layout,
            "completed_synchronized_stage2_updates": 1,
            "stage2_start_states": {
                arm: {
                    "model_state": model_state,
                    "optimizer_state": optimizer_state,
                    "stage1_outputs": copy.deepcopy(output),
                }
            },
            "series": {f"updates/01/{arm}": item},
        }
        return prepare, gradients

    def test_v2_correction_is_exactly_pinned(self):
        correction = pilot._load_correction_v2()
        self.assertEqual(correction["schema_version"], pilot.CORRECTION_V2_SCHEMA_VERSION)
        self.assertEqual(correction["correction_id"], pilot.CORRECTION_V2_ID)
        self.assertEqual(
            pilot.sha256_file(pilot._repo_path(pilot.CORRECTION_V2_RELATIVE_PATH)),
            pilot.CORRECTION_V2_SHA256,
        )

    def test_v3_correction_is_exactly_pinned(self):
        correction = pilot._load_correction_v3()
        self.assertEqual(correction["schema_version"], pilot.CORRECTION_V3_SCHEMA_VERSION)
        self.assertEqual(correction["correction_id"], pilot.CORRECTION_V3_ID)
        self.assertEqual(
            pilot.sha256_file(pilot._repo_path(pilot.CORRECTION_V3_RELATIVE_PATH)),
            pilot.CORRECTION_V3_SHA256,
        )

    def test_v4_correction_is_exactly_pinned(self):
        correction = pilot._load_correction_v4()
        self.assertEqual(correction["schema_version"], pilot.CORRECTION_V4_SCHEMA_VERSION)
        self.assertEqual(correction["correction_id"], pilot.CORRECTION_V4_ID)
        self.assertEqual(
            pilot.sha256_file(pilot._repo_path(pilot.CORRECTION_V4_RELATIVE_PATH)),
            pilot.CORRECTION_V4_SHA256,
        )

    def test_v5_correction_and_predecessor_stop_are_exactly_pinned(self):
        correction = pilot._load_correction_v5()
        self.assertEqual(
            correction["schema_version"], pilot.CORRECTION_V5_SCHEMA_VERSION
        )
        self.assertEqual(correction["correction_id"], pilot.CORRECTION_V5_ID)
        self.assertEqual(
            pilot.sha256_file(
                pilot._repo_path(pilot.CORRECTION_V5_RELATIVE_PATH)
            ),
            pilot.CORRECTION_V5_SHA256,
        )
        self.assertEqual(
            pilot.sha256_file(
                pilot._repo_path(pilot.PREDECESSOR_STOP_MANIFEST_RELATIVE_PATH)
            ),
            pilot.PREDECESSOR_STOP_MANIFEST_FILE_SHA256,
        )

    def test_each_gradient_chain_tensor_mutation_fails_replay(self):
        prepare, control = self.synthetic_one_update_bundle("control_vanilla")
        baseline = pilot._replay_gradient_arm(
            control, prepare, arm="control_vanilla"
        )
        self.assertTrue(baseline["passed"], baseline["failures"])
        item_path = "updates/01/control_vanilla"
        mutations = {
            "raw": lambda item: item["raw_task_gradients"][
                "PLAY:positive"
            ].add_(torch.tensor([1e-3, 0.0], dtype=torch.float64)),
            "direct": lambda item: item["direct_policy_gradient"].add_(1e-3),
            "KL": lambda item: item["anchor_kl_gradient"].add_(1e-3),
            "preclip": lambda item: item["combined_preclip_gradient"].add_(1e-3),
            "authoritative_preclip": lambda item: item[
                "authoritative_legacy_preclip_gradient"
            ].add_(1e-3),
            "independent_vjp": lambda item: item[
                "independent_rowwise_joint_vjp"
            ].add_(1e-3),
            "independent_vjp_hash": lambda item: item.update(
                independent_rowwise_joint_vjp_sha256="F" * 64
            ),
            "decomposition_metric": lambda item: item[
                "control_decomposition"
            ].update(maximum_absolute_error=1e-3),
            "postclip": lambda item: item["combined_postclip_gradient"].add_(1e-3),
            "actual": lambda item: item["actual_parameter_delta"].add_(1e-3),
            "cumulative": lambda item: item["cumulative_parameter_delta"].add_(1e-3),
            "optimizer_exp_avg": lambda item: item["optimizer_state_after"][
                "state"
            ][0]["exp_avg"].add_(1e-3),
        }
        for label, mutate in mutations.items():
            broken = copy.deepcopy(control)
            mutate(broken["series"][item_path])
            replay = pilot._replay_gradient_arm(
                broken, prepare, arm="control_vanilla"
            )
            self.assertFalse(replay["passed"], label)
        prepare, treatment = self.synthetic_one_update_bundle("treatment_pcgrad")
        self.assertTrue(pilot._replay_gradient_arm(
            treatment, prepare, arm="treatment_pcgrad"
        )["passed"])
        treatment["series"]["updates/01/treatment_pcgrad"][
            "projected_task_gradients"
        ]["PLAY:positive"].add_(1e-3)
        self.assertFalse(pilot._replay_gradient_arm(
            treatment, prepare, arm="treatment_pcgrad"
        )["passed"])

    def test_output_probability_and_value_mutations_change_raw_identity(self):
        prepare, output = self.synthetic_prepare_and_output()
        metrics = pilot._metrics_from_ordered_output(
            output, prepare, update_ordinal=1
        )
        identity = pilot.base._ordered_output_hashes(metrics)
        changed_probability = copy.deepcopy(output)
        changed_probability["probabilities"][0] = torch.nextafter(
            changed_probability["probabilities"][0],
            torch.tensor(math.inf, dtype=torch.float32),
        )
        probability_metrics = pilot._metrics_from_ordered_output(
            changed_probability, prepare, update_ordinal=1
        )
        self.assertNotEqual(
            identity["ordered_probability_bytes_sha256"],
            pilot.base._ordered_output_hashes(probability_metrics)[
                "ordered_probability_bytes_sha256"
            ],
        )
        changed_value = copy.deepcopy(output)
        changed_value["values"][0] = torch.nextafter(
            changed_value["values"][0],
            torch.tensor(math.inf, dtype=torch.float32),
        )
        value_metrics = pilot._metrics_from_ordered_output(
            changed_value, prepare, update_ordinal=1
        )
        self.assertFalse(value_metrics[0]["value_output_byte_exact_to_initial"])
        self.assertNotEqual(
            identity["ordered_value_bytes_sha256"],
            pilot.base._ordered_output_hashes(value_metrics)[
                "ordered_value_bytes_sha256"
            ],
        )

    def test_checkpoint_metadata_and_state_contracts_are_exact(self):
        expected = {
            "status": "PENDING_AUDIT", "arm": "control_vanilla",
            "plan_path": pilot.PLAN_RELATIVE_PATH.as_posix(),
            "plan_sha256": pilot.PLAN_SHA256,
            "correction_path": pilot.CORRECTION_RELATIVE_PATH.as_posix(),
            "correction_sha256": pilot.CORRECTION_SHA256,
            "correction_v2_path": pilot.CORRECTION_V2_RELATIVE_PATH.as_posix(),
            "correction_v2_sha256": pilot.CORRECTION_V2_SHA256,
            "correction_v3_path": pilot.CORRECTION_V3_RELATIVE_PATH.as_posix(),
            "correction_v3_sha256": pilot.CORRECTION_V3_SHA256,
            "correction_v4_path": pilot.CORRECTION_V4_RELATIVE_PATH.as_posix(),
            "correction_v4_sha256": pilot.CORRECTION_V4_SHA256,
            "correction_v5_path": pilot.CORRECTION_V5_RELATIVE_PATH.as_posix(),
            "correction_v5_sha256": pilot.CORRECTION_V5_SHA256,
            "predecessor_execution_stop": predecessor_stop_binding(),
            "implementation_path": pilot.IMPLEMENTATION_RELATIVE_PATH.as_posix(),
            "implementation_snapshot_file_count": 55,
            "implementation_snapshot_sha256": "A" * 64,
            "execution_spec_sha256": "B" * 64,
            "prepare_receipt_sha256": "C" * 64,
            "synchronized_optimizer_steps": 65,
            "source_hashes": {"x": "D" * 64},
            "terminal_output_hashes": {"probability": "E" * 64},
            "games_run": 0,
        }
        self.assertEqual(
            pilot._checkpoint_publication_failures_v2(expected, expected), []
        )
        for mutation in ("missing", "extra", "wrong"):
            value = copy.deepcopy(expected)
            if mutation == "missing":
                value.pop("plan_path")
            elif mutation == "extra":
                value["forged"] = True
            else:
                value["games_run"] = 1
            self.assertTrue(
                pilot._checkpoint_publication_failures_v2(value, expected),
                mutation,
            )
        model = {"x": torch.tensor([1.0], dtype=torch.float32)}
        optimizer = {"state": {0: {"step": torch.tensor(65.0)}}}
        self.assertEqual(pilot._checkpoint_state_failures_v2(
            model, optimizer, copy.deepcopy(model), copy.deepcopy(optimizer)
        ), [])
        different_model = {"x": torch.tensor([2.0], dtype=torch.float32)}
        self.assertTrue(pilot._checkpoint_state_failures_v2(
            different_model, optimizer, model, optimizer
        ))
        different_optimizer = copy.deepcopy(optimizer)
        different_optimizer["state"][0]["step"] = torch.tensor(64.0)
        self.assertTrue(pilot._checkpoint_state_failures_v2(
            model, different_optimizer, model, optimizer
        ))
        prepare, output = self.synthetic_prepare_and_output()
        expected_metrics = pilot._metrics_from_ordered_output(
            output, prepare, update_ordinal=64
        )
        changed_output = copy.deepcopy(output)
        changed_output["probabilities"][0] = torch.nextafter(
            changed_output["probabilities"][0],
            torch.tensor(math.inf, dtype=torch.float32),
        )
        changed_metrics = pilot._metrics_from_ordered_output(
            changed_output, prepare, update_ordinal=64
        )
        changed_hashes = pilot.base._ordered_output_hashes(changed_metrics)
        _actual_hashes, output_failures = pilot._checkpoint_output_failures_v2(
            checkpoint_metrics=changed_metrics,
            expected_output_metrics=expected_metrics,
            publication_terminal_hashes=changed_hashes,
        )
        self.assertIn("update64_outputs", output_failures)
        self.assertIn("recomputed_terminal_output_hashes", output_failures)
        self.assertNotIn("metadata_terminal_output_hashes", output_failures)
        _actual_hashes, metadata_failures = pilot._checkpoint_output_failures_v2(
            checkpoint_metrics=changed_metrics,
            expected_output_metrics=expected_metrics,
            publication_terminal_hashes={"forged": "0" * 64},
        )
        self.assertIn("metadata_terminal_output_hashes", metadata_failures)

    def test_exact_postclip_matches_torch_epsilon_and_old_formula_does_not(self):
        preclip = torch.tensor([3.0, 4.0], dtype=torch.float32)
        layout = [
            {"name": "residual_head.0.weight", "shape": [1], "numel": 1},
            {"name": "residual_head.0.bias", "shape": [1], "numel": 1},
        ]
        expected, total, coefficient = pilot._exact_postclip_flat(preclip, layout)
        parameters = {
            "residual_head.0.weight": torch.nn.Parameter(torch.zeros(1)),
            "residual_head.0.bias": torch.nn.Parameter(torch.zeros(1)),
        }
        parameters["residual_head.0.weight"].grad = preclip[:1].clone()
        parameters["residual_head.0.bias"].grad = preclip[1:].clone()
        torch_total = torch.nn.utils.clip_grad_norm_(
            [parameters[name] for name in sorted(parameters)],
            pilot.GRADIENT_CLIP,
            error_if_nonfinite=True,
        )
        actual = torch.cat([
            parameters["residual_head.0.weight"].grad,
            parameters["residual_head.0.bias"].grad,
        ])
        self.assertTrue(torch.equal(total, torch_total))
        self.assertTrue(torch.equal(expected, actual))
        old = preclip * min(1.0, pilot.GRADIENT_CLIP / float(total))
        self.assertFalse(torch.equal(old, actual))
        self.assertLess(float(coefficient), 1.0)

    def test_production_shaped_native_clip_is_exact_for_both_coefficients(self):
        layout = [
            {
                "name": "residual_head.0.weight", "shape": [96, 192],
                "numel": 96 * 192, "dtype": "torch.float32",
            },
            {
                "name": "residual_head.0.bias", "shape": [96],
                "numel": 96, "dtype": "torch.float32",
            },
        ]
        base_vector = torch.linspace(-1.0, 1.0, 96 * 193, dtype=torch.float32)
        real_clip = torch.nn.utils.clip_grad_norm_
        for scale, expect_clipped in ((1e-8, False), (1.0, True)):
            preclip = base_vector * scale
            with mock.patch.object(
                pilot.torch.nn.utils,
                "clip_grad_norm_",
                wraps=real_clip,
            ) as pinned:
                postclip, total, coefficient = pilot._exact_postclip_flat(
                    preclip, layout
                )
            self.assertEqual(pinned.call_count, 1)
            self.assertIsNone(pinned.call_args.kwargs["foreach"])
            self.assertTrue(pinned.call_args.kwargs["error_if_nonfinite"])
            oracle = {
                row["name"]: torch.nn.Parameter(
                    torch.zeros(tuple(row["shape"]), dtype=torch.float32)
                )
                for row in layout
            }
            offset = 0
            for row in layout:
                count = row["numel"]
                oracle[row["name"]].grad = preclip[
                    offset: offset + count
                ].reshape(row["shape"]).clone()
                offset += count
            oracle_total = real_clip(
                [oracle[name] for name in sorted(oracle)],
                pilot.GRADIENT_CLIP,
                norm_type=2.0,
                error_if_nonfinite=True,
                foreach=None,
            )
            oracle_postclip = torch.cat([
                oracle[name].grad.reshape(-1) for name in pilot.PARAMETER_NAMES
            ])
            self.assertTrue(torch.equal(total, oracle_total))
            self.assertTrue(torch.equal(postclip, oracle_postclip))
            if expect_clipped:
                self.assertLess(float(coefficient), 1.0)
                self.assertFalse(torch.equal(postclip, preclip))
            else:
                self.assertEqual(float(coefficient), 1.0)
                self.assertTrue(torch.equal(postclip, preclip))

    def test_raw_step_identity_and_replay_bind_outputs_and_coefficient(self):
        prepare, gradients = self.synthetic_one_update_bundle("control_vanilla")
        key = "updates/01/control_vanilla"
        item = gradients["series"][key]
        baseline = pilot._raw_step_record_sha256_v2(
            item, arm="control_vanilla", update_ordinal=1
        )
        changed_output = copy.deepcopy(item)
        changed_output["ordered_outputs"]["probabilities"][0] = torch.nextafter(
            changed_output["ordered_outputs"]["probabilities"][0],
            torch.tensor(math.inf, dtype=torch.float32),
        )
        self.assertNotEqual(
            baseline,
            pilot._raw_step_record_sha256_v2(
                changed_output, arm="control_vanilla", update_ordinal=1
            ),
        )
        changed_coefficient = copy.deepcopy(item)
        changed_coefficient["postclip_coefficient"] = float(
            torch.nextafter(
                torch.tensor(item["postclip_coefficient"], dtype=torch.float32),
                torch.tensor(-math.inf, dtype=torch.float32),
            )
        )
        self.assertNotEqual(
            baseline,
            pilot._raw_step_record_sha256_v2(
                changed_coefficient, arm="control_vanilla", update_ordinal=1
            ),
        )
        broken = copy.deepcopy(gradients)
        broken["series"][key] = changed_coefficient
        replay = pilot._replay_gradient_arm(
            broken, prepare, arm="control_vanilla"
        )
        self.assertFalse(replay["passed"])
        self.assertEqual(
            replay["failures"], ["update:1:ValueError:postclip coefficient"]
        )

    def test_every_non_hash_run_summary_field_is_exactly_cross_bound(self):
        fields = pilot.RUN_SUMMARY_KEYS_V2 - {"run_summary_sha256"}
        expected = {
            field: {"authoritative_field": field} for field in fields
        }
        summary = {
            **copy.deepcopy(expected), "run_summary_sha256": "A" * 64
        }
        self.assertEqual(
            pilot._run_summary_exact_discrepancies_v3(summary, expected), []
        )
        for field in sorted(fields):
            mutated = copy.deepcopy(summary)
            mutated[field] = {"authoritative_field": field, "mutation": True}
            self.assertIn(
                f"run_summary:{field}",
                pilot._run_summary_exact_discrepancies_v3(mutated, expected),
                field,
            )
        nested = copy.deepcopy(summary)
        nested["checkpoint_reload_evidence"]["unexpected_nested_key"] = True
        self.assertIn(
            "run_summary:checkpoint_reload_evidence",
            pilot._run_summary_exact_discrepancies_v3(nested, expected),
        )

    @staticmethod
    def adam_state():
        return {
            "state": {},
            "param_groups": [{
                "lr": 1e-4, "betas": (0.9, 0.999), "eps": 1e-8,
                "weight_decay": 0.0, "amsgrad": False, "maximize": False,
                "foreach": None, "capturable": False, "differentiable": False,
                "fused": None, "decoupled_weight_decay": False,
                "params": [0, 1, 2, 3],
            }],
        }

    @classmethod
    def nonempty_stage1_like_adam_state(cls):
        state = cls.adam_state()
        state["state"] = {
            0: {
                "step": torch.tensor(0.0, dtype=torch.float32),
                "exp_avg": torch.tensor([[0.002]], dtype=torch.float32),
                "exp_avg_sq": torch.tensor([[4e-6]], dtype=torch.float32),
            },
            1: {
                "step": torch.tensor(0.0, dtype=torch.float32),
                "exp_avg": torch.tensor([-0.003], dtype=torch.float32),
                "exp_avg_sq": torch.tensor([9e-6], dtype=torch.float32),
            },
            2: {
                "step": torch.tensor(1.0, dtype=torch.float32),
                "exp_avg": torch.tensor([[0.004]], dtype=torch.float32),
                "exp_avg_sq": torch.tensor([[16e-6]], dtype=torch.float32),
            },
            3: {
                "step": torch.tensor(1.0, dtype=torch.float32),
                "exp_avg": torch.tensor([-0.005], dtype=torch.float32),
                "exp_avg_sq": torch.tensor([25e-6], dtype=torch.float32),
            },
        }
        return state

    @staticmethod
    def conflicting_seven_task_gradients():
        vectors = (
            (1.0, 1.0), (-0.7, 0.1), (0.2, -0.8), (-0.1, 0.4),
            (0.3, -0.2), (-0.4, 0.6), (0.05, -0.15),
        )
        return {
            task: torch.tensor(vector, dtype=torch.float64)
            for task, vector in zip(pilot.TASK_ORDER, vectors)
        }

    @staticmethod
    def independent_original_gj_pcgrad(raw, update):
        originals = {
            task: raw[task].detach().cpu().contiguous().clone().to(torch.float64)
            for task in pilot.TASK_ORDER
        }
        offset = (update - 1) % len(pilot.TASK_ORDER)
        order = pilot.TASK_ORDER[offset:] + pilot.TASK_ORDER[:offset]
        projected = {}
        for task in order:
            current = originals[task].clone()
            for other in order:
                if task == other:
                    continue
                original_g_j = originals[other]
                denominator = torch.dot(original_g_j, original_g_j)
                if float(denominator) == 0.0:
                    continue
                numerator = torch.dot(current, original_g_j)
                if float(numerator) < 0.0:
                    current = current - numerator / denominator * original_g_j
            projected[task] = current
        combined = torch.zeros_like(next(iter(originals.values())))
        for task in order:
            combined = combined + projected[task]
        return {task: projected[task] for task in pilot.TASK_ORDER}, combined

    def synthetic_64_step_bundle(self, arm):
        prepare, output = self.synthetic_prepare_and_output()
        layout = [
            {
                "name": "residual_head.0.weight", "shape": [1, 1],
                "numel": 1, "dtype": "torch.float32",
            },
            {
                "name": "residual_head.0.bias", "shape": [1],
                "numel": 1, "dtype": "torch.float32",
            },
        ]
        initial_parameters = {
            "residual_head.0.weight": torch.tensor([[0.25]], dtype=torch.float32),
            "residual_head.0.bias": torch.tensor([-0.5], dtype=torch.float32),
        }
        start_optimizer = self.nonempty_stage1_like_adam_state()
        parameters = copy.deepcopy(initial_parameters)
        optimizer_state = copy.deepcopy(start_optimizer)
        raw = self.conflicting_seven_task_gradients()
        direct = sum(
            (raw[task] for task in pilot.TASK_ORDER),
            torch.zeros(2, dtype=torch.float64),
        )
        series = {}
        for update in range(1, 65):
            item = {
                "raw_task_gradients": copy.deepcopy(raw),
                "direct_policy_gradient": direct.clone(),
            }
            if arm == "treatment_pcgrad":
                projected, policy = pilot._recompute_pcgrad_flat(
                    raw, update_ordinal=update
                )
                item["projected_task_gradients"] = projected
            else:
                policy = direct
            anchor = torch.tensor(
                [0.0001 * update, -0.0002 * update], dtype=torch.float32
            )
            preclip = policy.to(torch.float32) + anchor
            postclip, _total, coefficient = pilot._exact_postclip_flat(
                preclip, layout
            )
            pre_step_parameters = copy.deepcopy(parameters)
            pre_step_optimizer_state = copy.deepcopy(optimizer_state)
            actual_by_name = pilot._manual_adam_step(
                parameters, optimizer_state,
                pilot._split_flat_by_layout(postclip, layout),
            )
            item.update({
                "anchor_kl_gradient": anchor,
                "combined_preclip_gradient": preclip,
                "combined_postclip_gradient": postclip,
                "postclip_coefficient": float(coefficient),
                "actual_parameter_delta": torch.cat([
                    actual_by_name[name].reshape(-1)
                    for name in pilot.PARAMETER_NAMES
                ]),
                "cumulative_parameter_delta": torch.cat([
                    (parameters[name] - initial_parameters[name]).reshape(-1)
                    for name in pilot.PARAMETER_NAMES
                ]),
                "policy_parameter_state_after": copy.deepcopy(parameters),
                "optimizer_state_after": copy.deepcopy(optimizer_state),
                "optimizer_step_counters": {
                    "residual_head.0.weight": update,
                    "residual_head.0.bias": update,
                    "residual_head.2.weight": 1,
                    "residual_head.2.bias": 1,
                },
                "ordered_outputs": copy.deepcopy(output),
            })
            if arm == "control_vanilla":
                attach_control_legacy_evidence(
                    item, pre_step_parameters, pre_step_optimizer_state, layout
                )
            series[f"updates/{update:02d}/{arm}"] = item
        gradients = {
            "parameter_names": list(pilot.PARAMETER_NAMES),
            "parameter_layout": layout,
            "completed_synchronized_stage2_updates": 64,
            "stage2_start_states": {
                arm: {
                    "model_state": copy.deepcopy(initial_parameters),
                    "optimizer_state": copy.deepcopy(start_optimizer),
                    "stage1_outputs": copy.deepcopy(output),
                }
            },
            "series": series,
        }
        return prepare, gradients

    @staticmethod
    def one_bit_mutate(tensor):
        byte_view = tensor.detach().view(torch.uint8).reshape(-1)
        byte_view[0] ^= 1

    def test_all_64_pcgrad_oracles_and_validator_mutations_are_isolated(self):
        prepare, gradients = self.synthetic_64_step_bundle("treatment_pcgrad")
        baseline = pilot._replay_gradient_arm(
            gradients, prepare, arm="treatment_pcgrad"
        )
        self.assertTrue(baseline["passed"], baseline["failures"])
        for update in range(1, 65):
            key = f"updates/{update:02d}/treatment_pcgrad"
            item = gradients["series"][key]
            oracle, oracle_combined = self.independent_original_gj_pcgrad(
                item["raw_task_gradients"], update
            )
            retained = item["projected_task_gradients"]
            self.assertTrue(
                all(torch.equal(oracle[task], retained[task]) for task in pilot.TASK_ORDER),
                update,
            )
            retained_combined = sum(
                (retained[task] for task in pilot.cyclic_task_order(update)),
                torch.zeros_like(oracle_combined),
            )
            self.assertTrue(torch.equal(oracle_combined, retained_combined), update)
            broken = copy.deepcopy(gradients)
            projected = broken["series"][key]["projected_task_gradients"]
            task = pilot.TASK_ORDER[(update - 1) % len(pilot.TASK_ORDER)]
            self.one_bit_mutate(projected[task][0:1])
            replay = pilot._replay_gradient_arm(
                broken, prepare, arm="treatment_pcgrad"
            )
            self.assertFalse(replay["passed"], update)
            self.assertEqual(
                replay["failures"][0],
                f"update:{update}:ValueError:projected PCGrad evidence",
            )

    def _assert_manual_adam_matches_real_oracle(self, manual_step):
        initial = {
            "residual_head.0.weight": torch.tensor([[0.25]], dtype=torch.float32),
            "residual_head.0.bias": torch.tensor([-0.5], dtype=torch.float32),
            "residual_head.2.weight": torch.tensor([[0.75]], dtype=torch.float32),
            "residual_head.2.bias": torch.tensor([0.125], dtype=torch.float32),
        }
        retained = self.nonempty_stage1_like_adam_state()
        model = ToyModel()
        named = dict(model.named_parameters())
        with torch.no_grad():
            for name in pilot.OPTIMIZER_PARAMETER_NAMES:
                named[name].copy_(initial[name])
        oracle = toy_optimizer(model)
        oracle.load_state_dict(copy.deepcopy(retained))
        manual_parameters = {
            name: initial[name].clone() for name in pilot.PARAMETER_NAMES
        }
        manual_state = copy.deepcopy(retained)
        for update in range(1, 65):
            gradients = {
                "residual_head.0.weight": torch.tensor(
                    [[0.001 * update]], dtype=torch.float32
                ),
                "residual_head.0.bias": torch.tensor(
                    [-0.0015 * update], dtype=torch.float32
                ),
            }
            manual_deltas = manual_step(
                manual_parameters, manual_state, gradients
            )
            before = {
                name: named[name].detach().clone() for name in pilot.PARAMETER_NAMES
            }
            oracle.zero_grad(set_to_none=True)
            for name in pilot.PARAMETER_NAMES:
                named[name].grad = gradients[name].clone()
            oracle.step()
            oracle_state = oracle.state_dict()
            for name in pilot.PARAMETER_NAMES:
                self.assertTrue(
                    torch.equal(manual_parameters[name], named[name].detach()),
                    (update, name, "parameter"),
                )
                self.assertTrue(
                    torch.equal(
                        manual_deltas[name], named[name].detach() - before[name]
                    ),
                    (update, name, "delta"),
                )
            self.assertEqual(
                pilot._optimizer_step_counters_from_state(manual_state),
                pilot._optimizer_step_counters_from_state(oracle_state),
                update,
            )
            for parameter_id, name in enumerate(pilot.OPTIMIZER_PARAMETER_NAMES):
                for field in ("step", "exp_avg", "exp_avg_sq"):
                    self.assertTrue(
                        torch.equal(
                            manual_state["state"][parameter_id][field],
                            oracle_state["state"][parameter_id][field],
                        ),
                        (update, name, field),
                    )
        self.assertTrue(pilot._nested_byte_exact_v2(manual_state, oracle.state_dict()))

    def test_64_step_manual_adam_matches_real_torch_adam_at_every_step(self):
        self._assert_manual_adam_matches_real_oracle(pilot._manual_adam_step)

    def test_real_adam_oracle_detects_deliberately_perturbed_manual_update(self):
        production = pilot._manual_adam_step

        def perturbed(parameters, optimizer_state, gradients):
            deltas = production(parameters, optimizer_state, gradients)
            value = parameters["residual_head.0.weight"].reshape(-1)
            value[0] = torch.nextafter(
                value[0], torch.tensor(math.inf, dtype=value.dtype)
            )
            return deltas

        with self.assertRaises(AssertionError):
            self._assert_manual_adam_matches_real_oracle(perturbed)

    def test_one_bit_starting_adam_moments_are_rejected_by_production_replay(self):
        prepare, gradients = self.synthetic_64_step_bundle("control_vanilla")
        baseline = pilot._replay_gradient_arm(
            gradients, prepare, arm="control_vanilla"
        )
        self.assertTrue(baseline["passed"], baseline["failures"])
        for field in ("exp_avg", "exp_avg_sq"):
            broken = copy.deepcopy(gradients)
            self.one_bit_mutate(
                broken["stage2_start_states"]["control_vanilla"]
                ["optimizer_state"]["state"][2][field]
            )
            replay = pilot._replay_gradient_arm(
                broken, prepare, arm="control_vanilla"
            )
            self.assertFalse(replay["passed"], field)
            self.assertEqual(
                replay["failures"][0],
                "update:1:ValueError:control pre-step optimizer state",
            )

    @staticmethod
    def alignment_summaries():
        weighted = {
            "ordinary_absolute_normalized_advantage": 1e-6,
            "equal_exact_public_state": 1e-6,
            "equal_source_trajectory": 1e-6,
        }
        priority = {
            task: {
                "lower_empirical_median": 1e-6,
                "weighted_lower_medians": copy.deepcopy(weighted),
            }
            for task in pilot.PRIORITY_TASKS
        }
        control = {"priority": copy.deepcopy(priority)}
        control["priority"][pilot.PRIORITY_TASKS[0]]["lower_empirical_median"] = 0.0
        treatment = {
            "priority": copy.deepcopy(priority),
            "all_12_family_polarity_lower_medians": {
                f"{family}:{polarity}": math.nextafter(1e-7, math.inf)
                for family in pilot.OPTION_TYPE_BY_FAMILY
                for polarity in ("positive", "negative")
            },
            "global": {
                "lower_empirical_median": 1e-5,
                "alignment_score": 0.10,
                "weighted_lower_medians": {
                    "raw_GAE_absolute_target": 0.0,
                    "Monte_Carlo_absolute_target": 0.0,
                },
            },
            "sign_stable_611_lower_empirical_median": 0.0,
        }
        return control, treatment, {"priority": copy.deepcopy(priority)}

    def test_each_terminal_numeric_threshold_rejects_just_below(self):
        control, treatment, difference = self.alignment_summaries()
        self.assertEqual(
            pilot._strict_alignment_threshold_failures_v2(
                update=64, control_summary=control,
                treatment_summary=treatment, difference=difference,
            ),
            [],
        )
        mutations = [
            lambda c, t, d: t["priority"][pilot.PRIORITY_TASKS[0]].update(
                lower_empirical_median=math.nextafter(1e-6, -math.inf)
            ),
            lambda c, t, d: d["priority"][pilot.PRIORITY_TASKS[0]].update(
                lower_empirical_median=math.nextafter(1e-6, -math.inf)
            ),
            lambda c, t, d: t["priority"][pilot.PRIORITY_TASKS[0]][
                "weighted_lower_medians"
            ].update(ordinary_absolute_normalized_advantage=math.nextafter(1e-6, -math.inf)),
            lambda c, t, d: t["all_12_family_polarity_lower_medians"].update(
                {next(iter(t["all_12_family_polarity_lower_medians"])): 1e-7}
            ),
            lambda c, t, d: t["global"].update(
                lower_empirical_median=math.nextafter(1e-5, -math.inf)
            ),
            lambda c, t, d: t["global"].update(
                alignment_score=math.nextafter(0.10, -math.inf)
            ),
            lambda c, t, d: t["global"]["weighted_lower_medians"].update(
                raw_GAE_absolute_target=math.nextafter(0.0, -math.inf)
            ),
            lambda c, t, d: t.update(
                sign_stable_611_lower_empirical_median=math.nextafter(0.0, -math.inf)
            ),
            lambda c, t, d: [
                c["priority"][task].update(lower_empirical_median=1e-6)
                for task in pilot.PRIORITY_TASKS
            ],
        ]
        for mutate in mutations:
            control, treatment, difference = self.alignment_summaries()
            mutate(control, treatment, difference)
            self.assertTrue(pilot._strict_alignment_threshold_failures_v2(
                update=64, control_summary=control,
                treatment_summary=treatment, difference=difference,
            ))
        control, treatment, difference = self.alignment_summaries()
        treatment["global"]["weighted_lower_medians"].update(
            raw_GAE_absolute_target=-1.0,
            Monte_Carlo_absolute_target=-1.0,
        )
        treatment["sign_stable_611_lower_empirical_median"] = -1.0
        update48 = pilot._strict_alignment_threshold_failures_v2(
            update=48, control_summary=control,
            treatment_summary=treatment, difference=difference,
        )
        self.assertFalse(any(
            token in failure
            for failure in update48
            for token in ("raw_GAE", "Monte_Carlo", "sign_stable_611")
        ))


class PreparePathV2Tests(unittest.TestCase):
    def test_canonical_candidate_receipt_path_and_malicious_variants(self):
        valid = (
            pilot.IMPLEMENTATION_RELATIVE_PATH
            / "test_outputs" / "phase1_iteration_009_prepare_v1"
            / pilot.PREPARE_OUTPUT_FILENAME
        ).as_posix()
        self.assertTrue(pilot._canonical_prepare_receipt_spec_path(valid).is_file())
        bad = [
            str(pilot._repo_path(
                pilot.IMPLEMENTATION_RELATIVE_PATH
                / "test_outputs" / "phase1_iteration_009_prepare_v1"
                / pilot.PREPARE_OUTPUT_FILENAME
            ).absolute()),
            valid.replace("/", "\\"),
            valid.replace("/test_outputs/", "/test_outputs/./"),
            valid.replace("/test_outputs/", "/test_outputs/x/../"),
            "../" + valid,
            (pilot.IMPLEMENTATION_RELATIVE_PATH / "test_outputs" / pilot.PREPARE_OUTPUT_FILENAME).as_posix(),
            (pilot.IMPLEMENTATION_RELATIVE_PATH / "test_outputs" / "x" / "extra" / pilot.PREPARE_OUTPUT_FILENAME).as_posix(),
            (pilot.IMPLEMENTATION_RELATIVE_PATH / "test_outputs" / "x" / "wrong.json").as_posix(),
            (pilot.SOURCE_IMPLEMENTATION_RELATIVE_PATH / "test_outputs" / "x" / pilot.PREPARE_OUTPUT_FILENAME).as_posix(),
        ]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                pilot._canonical_prepare_receipt_spec_path(value, must_exist=False)
        with mock.patch.object(
            pilot.inherited, "_is_link_or_reparse",
            side_effect=lambda path: path.name == "phase1_iteration_009_prepare_v1",
        ):
            with self.assertRaisesRegex(ValueError, "link"):
                pilot._canonical_prepare_receipt_spec_path(valid)

    def test_path_rejection_constructs_no_optimizer(self):
        malicious = str(
            pilot._repo_path(pilot.IMPLEMENTATION_RELATIVE_PATH).absolute()
            / "test_outputs" / "x" / pilot.PREPARE_OUTPUT_FILENAME
        )
        with mock.patch.object(
            pilot.torch.optim, "Adam", side_effect=AssertionError("optimizer reached")
        ):
            with self.assertRaises(ValueError):
                pilot._canonical_prepare_receipt_spec_path(malicious, must_exist=False)


class NonAuthorityV2Tests(unittest.TestCase):
    def test_malicious_caller_booleans_create_discrepancies(self):
        arms = ("control_vanilla", "treatment_pcgrad")
        step_by_key = {}
        safety = {}
        dummy_output = {
            "probabilities": torch.tensor([], dtype=torch.float32),
            "probability_offsets": torch.tensor([0], dtype=torch.int64),
            "values": torch.tensor([], dtype=torch.float32),
        }
        series = {}
        for arm in arms:
            for update in range(1, 65):
                step_by_key[(arm, update)] = {
                    "safety": {"safety_pass": True, "hard_stop": False},
                    "step": {
                        "gradient_diagnostics": {
                            "surgery_nonzero": False,
                            "task_changed_by_surgery": [],
                        }
                    },
                }
                safety[f"{arm}:{update}"] = {"pass": True, "hard_stop": False}
                series[f"updates/{update:02d}/{arm}"] = {
                    "ordered_outputs": dummy_output
                }
        gradients = {
            "stage2_start_states": {
                arm: {"stage1_outputs": dummy_output} for arm in arms
            },
            "series": series,
        }
        raw_mechanism = {
            "surgery_nonzero": False,
            "tasks_touched_first_16": [],
            "cumulative_delta_projections": {},
        }
        numeric = {
            "details": {
                "safety": safety,
                "mechanism": raw_mechanism,
                "END": {"passed": True},
            }
        }
        summary = {
            "all_safety_gates_pass": True,
            "mechanism": copy.deepcopy(raw_mechanism),
            "control_update32_reference": {"passed": True},
            "duplicate_treatment_canonical_outputs_identical": True,
            "terminal_END_controls": {"passed": True},
            "strict_offline_gates": {"offline_pass": True},
        }
        # Per-step caller compacts are no longer part of the public schema;
        # flip every remaining aggregate caller claim instead.
        summary["all_safety_gates_pass"] = False
        summary["mechanism"] = {
            "surgery_nonzero": True,
            "tasks_touched_first_16": ["PLAY:positive"],
            "cumulative_delta_projections": {"64": {}},
        }
        summary["control_update32_reference"]["passed"] = False
        summary["duplicate_treatment_canonical_outputs_identical"] = False
        summary["terminal_END_controls"]["passed"] = False
        summary["strict_offline_gates"]["offline_pass"] = False
        discrepancies = pilot._caller_summary_discrepancies_v2(
            summary=summary, step_by_key=step_by_key, gradients=gradients,
            prepare_receipt={"rows": []}, numeric=numeric,
            control_replay={},
            treatment_replay={"surgery_by_update": {}},
            control32={"passed": True}, duplicate={"passed": True},
            raw_pass_before_discrepancies=True,
        )
        expected = {
            "all_safety_gates_pass",
            "mechanism.surgery_nonzero",
            "mechanism.tasks_touched_first_16",
            "mechanism.cumulative_delta_projections",
            "control_update32_reference.passed",
            "duplicate_treatment_canonical_outputs_identical",
            "terminal_END_controls.passed",
            "strict_offline_gates.offline_pass",
        }
        self.assertTrue(expected.issubset(discrepancies))

    def test_public_step_schema_rejects_any_compact_field_injection(self):
        raw = {
            task: torch.zeros(2, dtype=torch.float64)
            for task in pilot.TASK_ORDER
        }
        item = {
            "raw_task_gradients": raw,
            "direct_policy_gradient": torch.zeros(2, dtype=torch.float64),
            "anchor_kl_gradient": torch.zeros(2, dtype=torch.float32),
            "combined_preclip_gradient": torch.zeros(2, dtype=torch.float32),
            "combined_postclip_gradient": torch.zeros(2, dtype=torch.float32),
            "postclip_coefficient": 1.0,
            "ordered_outputs": {
                "probabilities": torch.tensor([0.5, 0.5], dtype=torch.float32),
                "probability_offsets": torch.tensor([0, 2], dtype=torch.int64),
                "values": torch.tensor([0.0], dtype=torch.float32),
            },
            "actual_parameter_delta": torch.zeros(2, dtype=torch.float32),
            "cumulative_parameter_delta": torch.zeros(2, dtype=torch.float32),
            "policy_parameter_state_after": {},
            "optimizer_state_after": {},
            "optimizer_step_counters": {},
        }
        guard = {
            "model_state": "A" * 64, "optimizer_state": "B" * 64,
            "grad_state": "C" * 64, "cpu_rng_state": "D" * 64,
        }
        item.update({
            "authoritative_legacy_preclip_gradient": torch.zeros(
                2, dtype=torch.float32
            ),
            "authoritative_legacy_preclip_sha256": pilot._tensor_sha256_v2(
                torch.zeros(2, dtype=torch.float32)
            ),
            "independent_rowwise_joint_vjp": torch.zeros(
                2, dtype=torch.float32
            ),
            "independent_rowwise_joint_vjp_sha256": pilot._tensor_sha256_v2(
                torch.zeros(2, dtype=torch.float32)
            ),
            "independent_rowwise_joint_vjp_parameter_sha256": {},
            "split_direct_plus_anchor_gradient": torch.zeros(
                2, dtype=torch.float32
            ),
            "control_decomposition": pilot.validate_control_decomposition(
                torch.zeros(2, dtype=torch.float32),
                torch.zeros(2, dtype=torch.float32),
            ),
            "pre_step_policy_parameter_state": {},
            "pre_step_optimizer_state": {},
            "pre_step_identity": {},
            "isolated_audit_guard_hashes_before": guard,
            "isolated_audit_guard_hashes_after": copy.deepcopy(guard),
            "capture_hook_counts": {
                name: 1 for name in pilot.PARAMETER_NAMES
            },
        })
        row = {
            "schema_version": "mass-preserving-pcgrad-public-step-reference-v2",
            "arm": "control_vanilla", "stage_2_update_ordinal": 1,
            "gradient_tensor_references": (
                pilot._public_step_tensor_references_v2("control_vanilla", 1)
            ),
            "gradient_tensor_evidence_present": True,
            "step_record_sha256": pilot._raw_step_record_sha256_v2(
                item, arm="control_vanilla", update_ordinal=1
            ),
        }
        self.assertEqual(pilot._public_step_reference_failures_v2(
            row, item, arm="control_vanilla", update=1
        ), [])
        for field in (
            "safety", "gradient_diagnostics", "optimizer_step",
            "parameter_diffs", "output_hashes", "record_hash",
        ):
            malicious = copy.deepcopy(row)
            malicious[field] = {"forged": True}
            failures = pilot._public_step_reference_failures_v2(
                malicious, item, arm="control_vanilla", update=1
            )
            self.assertTrue(any("step_schema" in value for value in failures))

    def test_missing_raw_tensor_contract_fails_closed(self):
        result = pilot._replay_gradient_arm(
            {
                "parameter_names": list(pilot.PARAMETER_NAMES),
                "parameter_layout": [],
            },
            {},
            arm="control_vanilla",
        )
        self.assertFalse(result["passed"])
        self.assertIn("parameter_layout", result["failures"])

    def test_recomputation_exception_boundary_has_stable_false_schema(self):
        with mock.patch.object(
            pilot, "_recompute_pending_gates_v2_impl",
            side_effect=KeyError("nested raw missing"),
        ):
            result = pilot.recompute_pending_gates(
                spec={}, prepare_receipt={}, manifest_path=Path("missing"),
                manifest_sha256="A" * 64,
            )
        self.assertEqual(set(result), pilot.RECOMPUTATION_RESULT_KEYS_V2)
        self.assertIs(result["offline_pass"], False)
        self.assertIs(result["bundle_integrity_pass"], False)
        self.assertTrue(result["failures"])

    def test_duplicate_requires_underlying_state_outputs_and_record_chain(self):
        model_state = {"x": torch.tensor([1.0], dtype=torch.float32)}
        optimizer_state = {
            "state": {0: {"step": torch.tensor(64.0)}},
            "param_groups": [{"params": [0]}],
        }
        outputs = {
            "probabilities": torch.tensor([0.25, 0.75], dtype=torch.float32),
            "probability_offsets": torch.tensor([0, 2], dtype=torch.int64),
            "values": torch.tensor([0.0], dtype=torch.float32),
        }
        chain = [f"{index:064X}" for index in range(64)]
        gradients = {
            "duplicate_treatment_state": {
                "model_state": copy.deepcopy(model_state),
                "optimizer_state": copy.deepcopy(optimizer_state),
                "ordered_outputs": copy.deepcopy(outputs),
                "per_update_record_hashes": list(chain),
            },
            "series": {
                "updates/64/treatment_pcgrad": {
                    "ordered_outputs": copy.deepcopy(outputs)
                }
            },
        }
        replay = {
            "final_model_state": copy.deepcopy(model_state),
            "final_optimizer_state": copy.deepcopy(optimizer_state),
        }
        checkpoint = {
            "model_state": copy.deepcopy(model_state),
            "optimizer_state": copy.deepcopy(optimizer_state),
        }
        steps = [{"step_record_sha256": value} for value in chain]
        gate, failures = pilot._duplicate_cross_binding_v2(
            gradients, replay, checkpoint, steps
        )
        self.assertTrue(gate["passed"], failures)
        for field in ("model_state", "optimizer_state", "ordered_outputs"):
            broken = copy.deepcopy(gradients)
            target = broken["duplicate_treatment_state"][field]
            tensor = next(
                value for value in (
                    target.values() if isinstance(target, dict) else ()
                ) if torch.is_tensor(value)
            ) if field != "optimizer_state" else target["state"][0]["step"]
            tensor.reshape(-1).numpy().view("uint8").reshape(-1)[0] ^= 1
            gate, _ = pilot._duplicate_cross_binding_v2(
                broken, replay, checkpoint, steps
            )
            self.assertFalse(gate["passed"], field)
        broken = copy.deepcopy(gradients)
        broken["duplicate_treatment_state"]["per_update_record_hashes"][0] = "F" * 64
        gate, _ = pilot._duplicate_cross_binding_v2(
            broken, replay, checkpoint, steps
        )
        self.assertFalse(gate["passed"])


class ReferenceAndStopTests(unittest.TestCase):
    def stage1_arm(self):
        return {
            "stage1_report": {},
            "stage1_safety": {},
            "stage1_value_identity": {},
            "model_parameter_hashes": {"x": "A"},
            "model_state_hashes": {"x": "A"},
            "model_state": {"x": torch.tensor([1.0])},
            "optimizer_canonical": {"x": "B"},
            "optimizer_state": {"state": {}},
            "output_hashes": {
                "ordered_probability_bytes_sha256": pilot.REFERENCE_CONTROL["stage1_ordered_probability_bytes_sha256"],
                "ordered_value_bytes_sha256": pilot.REFERENCE_CONTROL["ordered_value_bytes_sha256"],
            },
            "losses": {"loss": 1.0},
            "fixed_input_identities": {"rows": 830},
            "complete_830_diagnostics": [],
            "stage1_record_sha256": pilot.REFERENCE_CONTROL["stage1_record_sha256"],
        }

    def test_stage1_arms_must_be_byte_equal_and_reference_equal(self):
        left = self.stage1_arm()
        pilot.validate_stage1_arm_equality(left, copy.deepcopy(left))
        right = copy.deepcopy(left)
        right["losses"]["loss"] = 1.0001
        with self.assertRaisesRegex(ValueError, "arm equality"):
            pilot.validate_stage1_arm_equality(left, right)

    def test_control_update32_requires_every_reference(self):
        evidence = {
            "record_sha256": pilot.REFERENCE_CONTROL["stage32_record_sha256"],
            "ordered_probability_bytes_sha256": pilot.REFERENCE_CONTROL["stage32_ordered_probability_bytes_sha256"],
            "ordered_value_bytes_sha256": pilot.REFERENCE_CONTROL["ordered_value_bytes_sha256"],
            "parameter_bytes_sha256": pilot.REFERENCE_CONTROL["stage32_parameter_bytes_sha256"],
            "optimizer_canonical_sha256": pilot.REFERENCE_CONTROL["optimizer_canonical_sha256"],
            "optimizer_param_group_canonical_sha256": pilot.REFERENCE_CONTROL["optimizer_param_group_canonical_sha256"],
            "optimizer_state_steps": {
                "residual_head.0.weight": 32,
                "residual_head.0.bias": 32,
                "residual_head.2.weight": 1,
                "residual_head.2.bias": 1,
            },
        }
        pilot.validate_control_update32(evidence)
        for key in evidence:
            broken = copy.deepcopy(evidence)
            broken[key] = None
            with self.assertRaisesRegex(ValueError, "reference mismatch"):
                pilot.validate_control_update32(broken)

    def test_directional_failure_never_early_stops(self):
        for update in range(1, 65):
            self.assertFalse(pilot.should_stop_for_directional_failure(update_ordinal=update, directional_pass=False))

    def test_any_arm_safety_failure_stops_both(self):
        passed = {"hard_stop": False, "safety_pass": True, "global_failures": []}
        failed = {"hard_stop": True, "safety_pass": False, "global_failures": ["KL"]}
        self.assertFalse(pilot.evaluate_safety_stop({"control": passed, "treatment": passed})["stop_both_arms"])
        result = pilot.evaluate_safety_stop({"control": passed, "treatment": failed})
        self.assertTrue(result["stop_both_arms"])
        self.assertIn("treatment", result["arm_failures"])

    def test_clip_activity_hard_stops_only_at_bound_milestones(self):
        safe = {
            "global_failures": [],
            "safety_pass": True,
            "hard_stop": False,
            "accepted_at_stage": True,
        }
        active = {"clip_active_row_count": 1}
        nonmilestone = pilot._apply_clip_milestone_gate(
            safe, active, update_ordinal=3
        )
        self.assertFalse(nonmilestone["hard_stop"])
        milestone = pilot._apply_clip_milestone_gate(
            safe, active, update_ordinal=4
        )
        self.assertTrue(milestone["hard_stop"])
        self.assertIn("global:PPO_clip_active_rows", milestone["global_failures"])


def passing_terminal_run():
    priority = {
        task: {
            "lower_empirical_median": 1e-6,
            "weighted_lower_medians": {
                "ordinary_absolute_normalized_advantage": 1e-6,
                "equal_exact_public_state": 1e-6,
                "equal_source_trajectory": 1e-6,
            },
        }
        for task in pilot.PRIORITY_TASKS
    }
    control_priority = copy.deepcopy(priority)
    control_priority[pilot.PRIORITY_TASKS[0]]["lower_empirical_median"] = 0.0
    treatment = {
        "priority": priority,
        "global": {
            "lower_empirical_median": 1e-5,
            "alignment_score": 0.1,
            "weighted_lower_medians": {
                "raw_GAE_absolute_target": 0.0,
                "Monte_Carlo_absolute_target": 0.0,
            },
        },
        "all_12_family_polarity_lower_medians": {str(index): 1.0001e-7 for index in range(12)},
        "sign_stable_611_lower_empirical_median": 0.0,
    }
    return {
        "completed_optimizer_steps_per_arm": {"control_vanilla": 65, "treatment_pcgrad": 65},
        "all_safety_gates_pass": True,
        "mechanism": {
            "surgery_nonzero": True,
            "tasks_touched_first_16": list(pilot.AUDIT_ADVERSE_TASKS),
            "cumulative_delta_projections": {
                "48": {task: 1e-12 for task in pilot.PRIORITY_TASKS},
                "64": {task: 1e-12 for task in pilot.PRIORITY_TASKS},
            },
        },
        "alignment_summaries": {
            "control_vanilla": {"48": {"priority": control_priority}, "64": {"priority": control_priority}},
            "treatment_pcgrad": {"48": copy.deepcopy(treatment), "64": copy.deepcopy(treatment)},
            "treatment_minus_control": {"48": {"priority": priority}, "64": {"priority": priority}},
        },
        "terminal_END_controls": {"passed": True, "failures": []},
        "duplicate_treatment_canonical_outputs_identical": True,
        "checkpoint_reload_exact": True,
        "independent_numeric_audit_pass": True,
        "root_recomputation_pass": True,
    }


class TerminalGateTests(unittest.TestCase):
    def test_all_terminal_boundaries_pass_exactly_where_inclusive(self):
        result = pilot.evaluate_terminal_gates(passing_terminal_run(), {})
        self.assertTrue(result["accepted"], result["failures"])

    def test_each_terminal_gate_is_required(self):
        mutations = (
            lambda run: run.update(completed_optimizer_steps_per_arm={"control_vanilla": 64, "treatment_pcgrad": 65}),
            lambda run: run.update(all_safety_gates_pass=False),
            lambda run: run["mechanism"].update(surgery_nonzero=False),
            lambda run: run["mechanism"].update(tasks_touched_first_16=[]),
            lambda run: run.update(duplicate_treatment_canonical_outputs_identical=False),
            lambda run: run.update(checkpoint_reload_exact=False),
            lambda run: run.update(independent_numeric_audit_pass=False),
            lambda run: run.update(root_recomputation_pass=False),
        )
        for mutate in mutations:
            run = passing_terminal_run()
            mutate(run)
            self.assertFalse(pilot.evaluate_terminal_gates(run, {})["accepted"])

    def test_strict_family_floor_and_projection_fail_at_equality(self):
        run = passing_terminal_run()
        run["alignment_summaries"]["treatment_pcgrad"]["64"]["all_12_family_polarity_lower_medians"]["0"] = 1e-7
        self.assertFalse(pilot.evaluate_terminal_gates(run, {})["accepted"])
        run = passing_terminal_run()
        run["mechanism"]["cumulative_delta_projections"]["48"][pilot.PRIORITY_TASKS[0]] = 0.0
        self.assertFalse(pilot.evaluate_terminal_gates(run, {})["accepted"])


class CorrectedPrepareAndTransactionTests(unittest.TestCase):
    def make_state(self):
        model = ToyModel()
        optimizer = toy_optimizer(model)
        progress = pilot.base.ExecutionProgress(model=model, optimizer=optimizer)
        return {"model": model, "optimizer": optimizer, "progress": progress}

    @staticmethod
    def one_step(_phase, state):
        state["optimizer"].zero_grad(set_to_none=True)
        for parameter in state["model"].parameters():
            parameter.grad = torch.ones_like(parameter)
        state["optimizer"].step()
        state["progress"].optimizer_steps_completed += 1

    def test_prepare_parser_is_execution_spec_independent(self):
        args = pilot.build_parser().parse_args(
            ["prepare", "--output-receipt", "receipt.json"]
        )
        self.assertEqual(args.mode, "prepare")
        self.assertFalse(hasattr(args, "execution_spec"))

    def test_complete_prepare_builder_constructs_no_optimizer(self):
        plan = pilot._load_plan()
        correction = pilot._load_correction()
        correction_v2 = pilot._load_correction_v2()
        correction_v3 = pilot._load_correction_v3()
        correction_v4 = pilot._load_correction_v4()
        correction_v5 = pilot._load_correction_v5()
        rows = PartitionTests().rows()
        inherited_prepare = {
            "rows": rows, "action_families": {}, "directional_memberships": {},
            "initial_value_identity": {}, "model_parameters": {},
        }
        loaded = {
            "checkpoint_path": pilot._repo_path(pilot.INPUT_CHECKPOINT_RELATIVE_PATH),
            "rows": [(None, None)] * 830, "model": ToyModel(),
        }
        snapshot = {
            "definition": "test", "file_count": 55, "sha256": "B" * 64,
            "files": [
                {
                    "path": "archaludon_rl/mass_preserving_pcgrad_pilot.py",
                    "bytes": 1, "sha256": "C" * 64,
                },
                {
                    "path": "tests/test_mass_preserving_pcgrad_pilot.py",
                    "bytes": 1, "sha256": "D" * 64,
                },
            ],
        }
        with (
            mock.patch.object(pilot, "_load_plan", return_value=plan),
            mock.patch.object(pilot, "_load_correction", return_value=correction),
            mock.patch.object(
                pilot, "_load_correction_v2", return_value=correction_v2
            ),
            mock.patch.object(
                pilot, "_load_correction_v3", return_value=correction_v3
            ),
            mock.patch.object(
                pilot, "_load_correction_v4", return_value=correction_v4
            ),
            mock.patch.object(
                pilot, "_load_correction_v5", return_value=correction_v5
            ),
            mock.patch.object(pilot, "_validate_provenance", return_value={}),
            mock.patch.object(pilot.inherited, "implementation_snapshot", return_value=snapshot),
            mock.patch.object(pilot, "_validate_reference_receipt", return_value={"checkpoint_loaded": False}),
            mock.patch.object(pilot.base, "_build_prepare_receipt", return_value=inherited_prepare),
            mock.patch.object(pilot.inherited, "_load_validated_inputs", return_value=loaded),
            mock.patch.object(pilot, "_monte_carlo_advantages", return_value=[1.0] * 830),
            mock.patch.object(pilot, "_sign_stable_ordinals", return_value=list(range(611))),
            mock.patch.object(pilot.torch.optim, "Adam", side_effect=AssertionError("optimizer constructed")),
        ):
            receipt = pilot._build_prepare_receipt(runtime={})
        pilot.validate_prepare_receipt(receipt)
        self.assertFalse(receipt["prepare_proof"]["execution_spec_read"])
        self.assertEqual(receipt["prepare_proof"]["optimizer_steps"], 0)
        self.assertIn("correction", receipt)
        self.assertIn("correction_v2", receipt)
        self.assertIn("correction_v3", receipt)
        self.assertIn("correction_v4", receipt)
        self.assertIn("correction_v5", receipt)
        self.assertEqual(
            receipt["predecessor_execution_stop"], predecessor_stop_binding()
        )
        self.assertEqual(receipt["implementation"]["module_sha256"], "C" * 64)
        self.assertEqual(receipt["implementation"]["focused_test_sha256"], "D" * 64)

    def test_replaced_self_consistent_prepare_fails_rebuild(self):
        stored = {"schema_version": pilot.PREPARE_RECEIPT_SCHEMA_VERSION, "fake": True}
        stored["receipt_sha256"] = pilot.canonical_sha256(stored)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            path.write_bytes(pilot.canonical_json_bytes(stored, newline=True))
            with mock.patch.object(
                pilot, "_corrected_prepare_receipt", return_value={"complete": True}
            ):
                with self.assertRaises(ValueError):
                    pilot._require_prepare_rebuild(path, stored, {})

    def test_treatment_exception_rolls_back_control(self):
        arms = {name: self.make_state() for name in ("control_vanilla", "treatment_pcgrad")}
        snapshots = {}

        def step(update, arm, state):
            if update == 2 and arm == "treatment_pcgrad":
                raise RuntimeError("treatment fault")
            self.one_step("stage2", state)
            if update == 1:
                snapshots[arm] = copy.deepcopy(state["model"].state_dict())
            return {"ok": True}

        result = pilot.run_lightweight_transaction_schedule(
            arms,
            stage1_step=lambda arm, state: self.one_step("stage1", state),
            stage2_step=step,
            diagnose=lambda *args: {"ok": True},
            safety=lambda *args: True,
            duplicate=lambda state: {"ok": True},
        )
        self.assertEqual(result["completed_steps_per_arm"], {"control_vanilla": 2, "treatment_pcgrad": 2})
        self.assertEqual(result["failure"]["exception_type"], "RuntimeError")
        for arm in arms:
            self.assertTrue(pilot.base._nested_byte_exact(arms[arm]["model"].state_dict(), snapshots[arm]))

    def test_stage1_exception_restores_zero_and_safety_retains_one(self):
        arms = {name: self.make_state() for name in ("control_vanilla", "treatment_pcgrad")}
        result = pilot.run_lightweight_transaction_schedule(
            arms,
            stage1_step=lambda arm, state: (_ for _ in ()).throw(RuntimeError("fault")) if arm == "treatment_pcgrad" else self.one_step("stage1", state),
            stage2_step=lambda *args: None,
            diagnose=lambda *args: {}, safety=lambda *args: True,
            duplicate=lambda state: None,
        )
        self.assertEqual(result["completed_steps_per_arm"], {"control_vanilla": 0, "treatment_pcgrad": 0})
        arms = {name: self.make_state() for name in ("control_vanilla", "treatment_pcgrad")}
        result = pilot.run_lightweight_transaction_schedule(
            arms, stage1_step=lambda arm, state: self.one_step("stage1", state),
            stage2_step=lambda *args: None, diagnose=lambda *args: {},
            safety=lambda phase, update, arm, diag: arm == "control_vanilla",
            duplicate=lambda state: None,
        )
        self.assertEqual(result["completed_steps_per_arm"], {"control_vanilla": 1, "treatment_pcgrad": 1})

    def test_fake_full_64_schedule_has_all_milestones_and_duplicate(self):
        arms = {name: self.make_state() for name in ("control_vanilla", "treatment_pcgrad")}
        result = pilot.run_lightweight_transaction_schedule(
            arms, stage1_step=lambda arm, state: self.one_step("stage1", state),
            stage2_step=lambda update, arm, state: (self.one_step("stage2", state) or {"update": update}),
            diagnose=lambda *args: {"ok": True}, safety=lambda *args: True,
            duplicate=lambda state: {"identical": True},
        )
        self.assertEqual(result["completed_steps_per_arm"], {"control_vanilla": 65, "treatment_pcgrad": 65})
        self.assertEqual(result["milestones"], list(pilot.DIAGNOSTIC_UPDATES))
        self.assertEqual(len(result["records"]), 64)
        self.assertEqual(result["duplicate"], {"identical": True})


class SerializedPendingV3Tests(unittest.TestCase):
    @staticmethod
    def prepare_receipt():
        path = (
            pilot._repo_path(pilot.IMPLEMENTATION_RELATIVE_PATH)
            / "test_outputs" / "phase1_iteration_009_prepare_v2"
            / pilot.PREPARE_OUTPUT_FILENAME
        )
        receipt = json.loads(path.read_text("utf-8"))
        receipt["predecessor_execution_stop"] = predecessor_stop_binding()
        return receipt

    @staticmethod
    def ordered_initial_outputs(receipt):
        offsets = [0]
        probabilities = []
        values = []
        for row in receipt["rows"]:
            probabilities.extend(row["initial_probabilities_float32"])
            offsets.append(len(probabilities))
            values.append(row["initial_value_float32"])
        return {
            "probabilities": torch.tensor(probabilities, dtype=torch.float32),
            "probability_offsets": torch.tensor(offsets, dtype=torch.int64),
            "values": torch.tensor(values, dtype=torch.float32),
        }

    @staticmethod
    def optimizer_state():
        return {
            "state": {
                2: {
                    "step": torch.tensor(1.0, dtype=torch.float32),
                    "exp_avg": torch.zeros(1, dtype=torch.float32),
                    "exp_avg_sq": torch.zeros(1, dtype=torch.float32),
                },
                3: {
                    "step": torch.tensor(1.0, dtype=torch.float32),
                    "exp_avg": torch.zeros(1, dtype=torch.float32),
                    "exp_avg_sq": torch.zeros(1, dtype=torch.float32),
                },
            },
            "param_groups": [{
                "lr": 1e-4, "betas": (0.9, 0.999), "eps": 1e-8,
                "weight_decay": 0.0, "amsgrad": False, "maximize": False,
                "foreach": None, "capturable": False, "differentiable": False,
                "fused": None, "decoupled_weight_decay": False,
                "params": [0, 1, 2, 3],
            }],
        }

    @staticmethod
    def production_shaped_optimizer_state(model):
        named = dict(model.named_parameters())
        state = {}
        for identifier, name in enumerate(pilot.OPTIMIZER_PARAMETER_NAMES):
            parameter = named[name].detach().cpu()
            state[identifier] = {
                "step": torch.tensor(
                    64.0 if name in pilot.PARAMETER_NAMES else 1.0,
                    dtype=torch.float32,
                ),
                "exp_avg": torch.zeros_like(parameter),
                "exp_avg_sq": torch.zeros_like(parameter),
            }
        return {
            "state": state,
            "param_groups": [{
                "lr": 1e-4, "betas": (0.9, 0.999), "eps": 1e-8,
                "weight_decay": 0.0, "amsgrad": False, "maximize": False,
                "foreach": None, "capturable": False,
                "differentiable": False, "fused": None,
                "decoupled_weight_decay": False,
                "params": list(range(len(pilot.OPTIMIZER_PARAMETER_NAMES))),
            }],
        }

    def valid_checkpoint_fixture(
        self, receipt, spec, *, arm="control_vanilla", mutate_model=None,
        terminal_metrics=None,
    ):
        source_hashes = pilot.inherited.checkpoint_source_hashes()
        model, metadata, _optimizer_state = pilot.load_checkpoint(
            pilot._repo_path(pilot.INPUT_CHECKPOINT_RELATIVE_PATH),
            expected_source_hashes=source_hashes, device="cpu",
        )
        if mutate_model is not None:
            mutate_model(model)
        loaded = pilot.inherited._load_validated_inputs()
        loaded["model"] = model
        measured = pilot.base._measure_stage(
            loaded, receipt, stage=2, stage_2_update_ordinal=64
        )
        if terminal_metrics is None:
            terminal_metrics = measured
        publication = {
            "status": "PENDING_AUDIT", "arm": arm,
            "plan_path": pilot.PLAN_RELATIVE_PATH.as_posix(),
            "plan_sha256": pilot.PLAN_SHA256,
            "correction_path": pilot.CORRECTION_RELATIVE_PATH.as_posix(),
            "correction_sha256": pilot.CORRECTION_SHA256,
            "correction_v2_path": pilot.CORRECTION_V2_RELATIVE_PATH.as_posix(),
            "correction_v2_sha256": pilot.CORRECTION_V2_SHA256,
            "correction_v3_path": pilot.CORRECTION_V3_RELATIVE_PATH.as_posix(),
            "correction_v3_sha256": pilot.CORRECTION_V3_SHA256,
            "correction_v4_path": pilot.CORRECTION_V4_RELATIVE_PATH.as_posix(),
            "correction_v4_sha256": pilot.CORRECTION_V4_SHA256,
            "correction_v5_path": pilot.CORRECTION_V5_RELATIVE_PATH.as_posix(),
            "correction_v5_sha256": pilot.CORRECTION_V5_SHA256,
            "predecessor_execution_stop": predecessor_stop_binding(),
            "implementation_path": pilot.IMPLEMENTATION_RELATIVE_PATH.as_posix(),
            "implementation_snapshot_file_count": spec[
                "implementation_snapshot_file_count"
            ],
            "implementation_snapshot_sha256": spec[
                "implementation_snapshot_sha256"
            ],
            "execution_spec_sha256": spec["_file_sha256"],
            "prepare_receipt_sha256": receipt["receipt_sha256"],
            "synchronized_optimizer_steps": 65,
            "source_hashes": source_hashes,
            "terminal_output_hashes": pilot.base._ordered_output_hashes(
                terminal_metrics
            ),
            "games_run": 0,
        }
        metadata = copy.deepcopy(metadata)
        metadata["pcgrad_publication"] = publication
        raw = {
            "model_config": copy.deepcopy(vars(model.config)),
            "model_state": {
                name: tensor.detach().cpu().clone()
                for name, tensor in model.state_dict().items()
            },
            "metadata": metadata,
            "optimizer_state": self.production_shaped_optimizer_state(model),
        }
        replay = {
            "final_model_state": copy.deepcopy(raw["model_state"]),
            "final_optimizer_state": copy.deepcopy(raw["optimizer_state"]),
        }
        return raw, replay, measured

    @staticmethod
    def save_checkpoint(path, raw):
        buffer = io.BytesIO()
        torch.save(raw, buffer)
        path.write_bytes(buffer.getvalue())

    def raw_bundle(self, receipt):
        output = self.ordered_initial_outputs(receipt)
        layout = [
            {
                "name": "residual_head.0.weight", "shape": [1, 1],
                "numel": 1, "dtype": "torch.float32",
            },
            {
                "name": "residual_head.0.bias", "shape": [1],
                "numel": 1, "dtype": "torch.float32",
            },
        ]
        start_model = {
            "residual_head.0.weight": torch.tensor([[0.25]], dtype=torch.float32),
            "residual_head.0.bias": torch.tensor([-0.5], dtype=torch.float32),
        }
        stage1_report = {
            "loss": 0.0, "policy_loss": 0.0,
            "pre_step_mean_anchor_kl": 0.0, "entropy": 0.0,
            "fixed_advantages_sha256": pilot.FIXED_ADVANTAGES_SHA256,
            "fixed_behavior_logprobabilities_sha256": (
                pilot.FIXED_BEHAVIOR_LOGPROBABILITIES_SHA256
            ),
        }
        starts = {
            arm: {
                "model_state": copy.deepcopy(start_model),
                "optimizer_state": copy.deepcopy(self.optimizer_state()),
                "stage1_report": copy.deepcopy(stage1_report),
                "stage1_safety": {}, "stage1_value_identity": {},
                "stage1_record_sha256": pilot.REFERENCE_CONTROL[
                    "stage1_record_sha256"
                ],
                "stage1_outputs": copy.deepcopy(output),
            }
            for arm in ("control_vanilla", "treatment_pcgrad")
        }
        series = {}
        step_rows = []
        for arm in ("control_vanilla", "treatment_pcgrad"):
            parameters = copy.deepcopy(start_model)
            optimizer_state = copy.deepcopy(self.optimizer_state())
            for update in range(1, 65):
                raw = {
                    task: torch.zeros(2, dtype=torch.float64)
                    for task in pilot.TASK_ORDER
                }
                direct = torch.zeros(2, dtype=torch.float64)
                anchor = torch.zeros(2, dtype=torch.float32)
                preclip = torch.zeros(2, dtype=torch.float32)
                postclip = torch.zeros(2, dtype=torch.float32)
                gradients = pilot._split_flat_by_layout(postclip, layout)
                pre_step_parameters = copy.deepcopy(parameters)
                pre_step_optimizer_state = copy.deepcopy(optimizer_state)
                actual_by_name = pilot._manual_adam_step(
                    parameters, optimizer_state, gradients
                )
                item = {
                    "raw_task_gradients": raw,
                    "direct_policy_gradient": direct,
                    "anchor_kl_gradient": anchor,
                    "combined_preclip_gradient": preclip,
                    "combined_postclip_gradient": postclip,
                    "postclip_coefficient": 1.0,
                    "actual_parameter_delta": torch.cat([
                        actual_by_name[name].reshape(-1)
                        for name in pilot.PARAMETER_NAMES
                    ]),
                    "cumulative_parameter_delta": torch.cat([
                        (parameters[name] - start_model[name]).reshape(-1)
                        for name in pilot.PARAMETER_NAMES
                    ]),
                    "policy_parameter_state_after": copy.deepcopy(parameters),
                    "optimizer_state_after": copy.deepcopy(optimizer_state),
                    "optimizer_step_counters": {
                        "residual_head.0.weight": update,
                        "residual_head.0.bias": update,
                        "residual_head.2.weight": 1,
                        "residual_head.2.bias": 1,
                    },
                    "ordered_outputs": copy.deepcopy(output),
                }
                if arm == "treatment_pcgrad":
                    item["projected_task_gradients"] = copy.deepcopy(raw)
                else:
                    attach_control_legacy_evidence(
                        item, pre_step_parameters, pre_step_optimizer_state,
                        layout,
                    )
                key = f"updates/{update:02d}/{arm}"
                series[key] = item
                step_rows.append({
                    "schema_version": (
                        "mass-preserving-pcgrad-public-step-reference-v2"
                    ),
                    "arm": arm, "stage_2_update_ordinal": update,
                    "gradient_tensor_references": (
                        pilot._public_step_tensor_references_v2(arm, update)
                    ),
                    "gradient_tensor_evidence_present": True,
                    "step_record_sha256": pilot._raw_step_record_sha256_v2(
                        item, arm=arm, update_ordinal=update
                    ),
                })
        gradients = {
            "schema_version": "mass-preserving-pcgrad-gradient-tensors-v2",
            "task_order": list(pilot.TASK_ORDER),
            "parameter_names": list(pilot.PARAMETER_NAMES),
            "parameter_layout": layout,
            "completed_synchronized_stage2_updates": 64,
            "stage2_start_states": starts,
            "control_update32_state": {},
            "duplicate_treatment_state": {},
            "series": series,
        }
        return gradients, step_rows

    def test_valid_loadable_65_step_checkpoint_cross_binding_and_mutations(self):
        receipt = self.prepare_receipt()
        spec = {
            "_file_sha256": "A" * 64,
            "implementation_snapshot_file_count": 55,
            "implementation_snapshot_sha256": "C" * 64,
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "control_pending.pt"
            raw, replay, metrics = self.valid_checkpoint_fixture(receipt, spec)
            self.save_checkpoint(path, raw)
            gate, failures, _loaded = pilot._checkpoint_cross_binding_v2(
                path, arm="control_vanilla", spec=spec,
                prepare_receipt=receipt, replay=replay,
                expected_output_metrics=metrics,
            )
            self.assertTrue(gate["passed"], failures)
            self.assertEqual(failures, [])
            self.assertEqual(
                gate["optimizer_state_steps"],
                {
                    "residual_head.0.weight": 64,
                    "residual_head.0.bias": 64,
                    "residual_head.2.weight": 1,
                    "residual_head.2.bias": 1,
                },
            )

            def mutate_valid_model(model):
                named = dict(model.named_parameters())
                with torch.no_grad():
                    named["residual_head.2.weight"][0, 0] = 10.0

            different_raw, _different_replay, _different_metrics = (
                self.valid_checkpoint_fixture(
                    receipt, spec, mutate_model=mutate_valid_model
                )
            )
            self.save_checkpoint(path, different_raw)
            _gate, different_failures, _loaded = (
                pilot._checkpoint_cross_binding_v2(
                    path, arm="control_vanilla", spec=spec,
                    prepare_receipt=receipt, replay=replay,
                    expected_output_metrics=metrics,
                )
            )
            self.assertIn(
                "metadata:terminal_output_hashes", different_failures
            )
            self.assertIn(
                "final_model:residual_head.2.weight", different_failures
            )

            tensor_mutation = copy.deepcopy(raw)
            tensor_mutation["model_state"]["residual_head.2.weight"][0, 0] = 10.0
            self.save_checkpoint(path, tensor_mutation)
            _gate, tensor_failures, _loaded = pilot._checkpoint_cross_binding_v2(
                path, arm="control_vanilla", spec=spec,
                prepare_receipt=receipt, replay=replay,
                expected_output_metrics=metrics,
            )
            self.assertIn(
                "final_model:residual_head.2.weight", tensor_failures
            )
            self.assertIn("update64_outputs", tensor_failures)

            output = pilot._ordered_output_tensor_evidence(metrics)
            output["probabilities"][0] = torch.nextafter(
                output["probabilities"][0],
                torch.tensor(math.inf, dtype=torch.float32),
            )
            changed_metrics = pilot._metrics_from_ordered_output(
                output, receipt, update_ordinal=64
            )
            self.save_checkpoint(path, raw)
            _gate, output_failures, _loaded = pilot._checkpoint_cross_binding_v2(
                path, arm="control_vanilla", spec=spec,
                prepare_receipt=receipt, replay=replay,
                expected_output_metrics=changed_metrics,
            )
            self.assertIn("update64_outputs", output_failures)
            self.assertIn("recomputed_terminal_output_hashes", output_failures)
            self.assertIn("metadata:terminal_output_hashes", output_failures)

    @staticmethod
    def refresh_manifest(directory, summary):
        evidence_names = (
            "stage1_diagnostics.jsonl", "milestone_diagnostics.jsonl",
            "step_summaries.jsonl", "gradient_tensors.pt",
        )
        summary["evidence"] = {
            name: {
                "bytes": (directory / name).stat().st_size,
                "sha256": pilot.sha256_file(directory / name),
            }
            for name in evidence_names
        }
        summary_core = dict(summary)
        summary_core.pop("run_summary_sha256", None)
        summary["run_summary_sha256"] = pilot.canonical_sha256(summary_core)
        (directory / "run_summary.json").write_bytes(
            pilot.canonical_json_bytes(summary, newline=True)
        )
        files = {}
        for name in set(pilot.PENDING_FILES) - {"manifest.json"}:
            payload = (directory / name).read_bytes()
            files[name] = {
                "bytes": len(payload), "sha256": pilot._sha256_bytes(payload)
            }
        manifest_core = {
            "schema_version": pilot.PENDING_MANIFEST_SCHEMA_VERSION,
            "status": "PENDING_AUDIT",
            "execution_spec_path": "spec.json",
            "execution_spec_sha256": "A" * 64,
            "prepare_receipt_path": "synthetic",
            "prepare_receipt_file_sha256": "B" * 64,
            "prepare_receipt_sha256": summary["prepare_receipt_sha256"],
            "implementation_snapshot_file_count": 0,
            "implementation_snapshot_sha256": "C" * 64,
            "files": files,
            "completed_optimizer_steps_per_arm": {
                "control_vanilla": 65, "treatment_pcgrad": 65,
            },
            "completed_synchronized_stage2_updates": 64,
            "failure": None, "games_run": 0,
            "runtime_smoke_executed": False,
        }
        manifest = {
            **manifest_core,
            "manifest_core_sha256": pilot.canonical_sha256(manifest_core),
        }
        payload = pilot.canonical_json_bytes(manifest, newline=True)
        (directory / "manifest.json").write_bytes(payload)
        return pilot._sha256_bytes(payload)

    def write_complete_bundle(self, directory):
        receipt = self.prepare_receipt()
        spec = {
            "_file_sha256": "A" * 64,
            "implementation_snapshot_file_count": 0,
            "implementation_snapshot_sha256": "C" * 64,
        }
        gradients, step_rows = self.raw_bundle(receipt)
        stage1_rows = [
            {
                "arm": arm, "row_ordinal": ordinal,
                "stage1_record_sha256": pilot.REFERENCE_CONTROL[
                    "stage1_record_sha256"
                ],
                "stage1_equality": {"passed": True},
                "complete_stage1_evidence": {} if ordinal == 0 else None,
                "optimizer_state_reference": (
                    f"stage2_start_states/{arm}/optimizer_state"
                    if ordinal == 0 else None
                ),
                "diagnostic": {"ppo_row_ordinal": ordinal},
            }
            for arm in ("control_vanilla", "treatment_pcgrad")
            for ordinal in range(pilot.EXPECTED_ROWS)
        ]
        milestone_rows = [
            {
                "arm": arm, "stage2_update_ordinal": update,
                "row_ordinal": ordinal,
                "diagnostic": {"ppo_row_ordinal": ordinal},
            }
            for arm in ("control_vanilla", "treatment_pcgrad")
            for update in pilot.DIAGNOSTIC_UPDATES
            for ordinal in range(pilot.EXPECTED_ROWS)
        ]
        (directory / "stage1_diagnostics.jsonl").write_bytes(
            pilot._jsonl_bytes(stage1_rows)
        )
        (directory / "milestone_diagnostics.jsonl").write_bytes(
            pilot._jsonl_bytes(milestone_rows)
        )
        (directory / "step_summaries.jsonl").write_bytes(
            pilot._jsonl_bytes(step_rows)
        )
        buffer = io.BytesIO()
        torch.save(gradients, buffer)
        (directory / "gradient_tensors.pt").write_bytes(buffer.getvalue())
        for arm, name in (
            ("control_vanilla", "control_pending.pt"),
            ("treatment_pcgrad", "treatment_pending.pt"),
        ):
            checkpoint, _replay, _metrics = self.valid_checkpoint_fixture(
                receipt, spec, arm=arm
            )
            self.save_checkpoint(directory / name, checkpoint)
        marker = {
            "status": "PENDING_AUDIT", "execution_spec_sha256": "A" * 64,
            "prepare_receipt_sha256": receipt["receipt_sha256"],
            "games_run": 0, "runtime_smoke_executed": False,
        }
        (directory / "PENDING_AUDIT").write_bytes(
            pilot.canonical_json_bytes(marker, newline=True)
        )
        summary = {
            "schema_version": pilot.RUN_SUMMARY_SCHEMA_VERSION,
            "status": "PENDING_AUDIT",
            "caller_summaries_informational_only": True,
            "execution_spec_path": "spec.json",
            "execution_spec_sha256": "A" * 64,
            "prepare_receipt_sha256": receipt["receipt_sha256"],
            "completed_optimizer_steps_per_arm": {
                "control_vanilla": 65, "treatment_pcgrad": 65,
            },
            "completed_synchronized_stage2_updates": 64,
            "failure": None, "safety_stop": None,
            "all_safety_gates_pass": False,
            "stage1_equality": {"passed": True},
            "stage1_record_hashes": {
                arm: pilot.REFERENCE_CONTROL["stage1_record_sha256"]
                for arm in ("control_vanilla", "treatment_pcgrad")
            },
            "stage1_complete_evidence": {
                "control_vanilla": {}, "treatment_pcgrad": {},
            },
            "control_update32_reference": {"passed": False},
            "mechanism": {
                "surgery_nonzero": False, "tasks_touched_first_16": [],
                "cumulative_delta_projections": {},
            },
            "alignment_summaries": {}, "terminal_END_controls": {"passed": False},
            "duplicate_treatment_identity": None,
            "duplicate_treatment_canonical_outputs_identical": False,
            "checkpoint_reload_evidence": {},
            "strict_offline_gates": {"offline_pass": False, "failures": []},
            "evidence": {}, "expected_task_order": list(pilot.TASK_ORDER),
            "expected_diagnostic_updates": list(pilot.DIAGNOSTIC_UPDATES),
            "stage1_diagnostic_row_count": len(stage1_rows),
            "milestone_diagnostic_row_count": len(milestone_rows),
            "step_summary_row_count": len(step_rows),
            "games_run": 0, "runtime_smoke_executed": False,
        }
        manifest_hash = self.refresh_manifest(directory, summary)
        return receipt, spec, summary, manifest_hash

    def test_complete_serialized_bundle_and_nested_missing_are_total(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            receipt, spec, summary, manifest_hash = self.write_complete_bundle(
                directory
            )
            result = pilot.recompute_pending_gates(
                spec=spec, prepare_receipt=receipt,
                manifest_path=directory / "manifest.json",
                manifest_sha256=manifest_hash,
            )
            self.assertEqual(set(result), pilot.RECOMPUTATION_RESULT_KEYS_V2)
            self.assertIs(type(result["offline_pass"]), bool)
            self.assertFalse(result["offline_pass"])
            self.assertFalse(any(
                failure.startswith("fail_closed:")
                for failure in result["failures"]
            ))
            replay = result["recomputed"]["gradient_replay"]
            self.assertTrue(
                replay["control_vanilla"]["passed"],
                replay["control_vanilla"]["failures"],
            )
            self.assertTrue(
                replay["treatment_pcgrad"]["passed"],
                replay["treatment_pcgrad"]["failures"],
            )
            self.assertEqual(
                result["recomputed"]["counts"]["gradient_series"], 128
            )
            self.assertEqual(result["recomputed"]["counts"]["step_rows"], 128)
            step_binding_prefixes = (
                "step_schema:", "step_tensor_reference:",
                "step_record_binding:", "step_raw_binding:",
            )
            self.assertEqual(
                [
                    failure for failure in result["failures"]
                    if failure.startswith(step_binding_prefixes)
                ],
                [],
            )
            self.assertTrue(any(
                failure.startswith(("stage1", "numerical:", "checkpoint:"))
                for failure in result["failures"]
            ))
            step_rows = pilot._read_jsonl(directory / "step_summaries.jsonl")
            self.assertEqual(len(step_rows), 128)
            self.assertEqual(
                {
                    (row["arm"], row["stage_2_update_ordinal"])
                    for row in step_rows
                },
                {
                    (arm, update)
                    for arm in ("control_vanilla", "treatment_pcgrad")
                    for update in range(1, 65)
                },
            )
            original_gradient_bytes = (directory / "gradient_tensors.pt").read_bytes()
            original_summary = copy.deepcopy(summary)
            gradients = torch.load(
                directory / "gradient_tensors.pt", map_location="cpu",
                weights_only=True,
            )
            all_outputs = [
                gradients["stage2_start_states"][arm]["stage1_outputs"]
                for arm in ("control_vanilla", "treatment_pcgrad")
            ] + [
                gradients["series"][f"updates/{update:02d}/{arm}"][
                    "ordered_outputs"
                ]
                for arm in ("control_vanilla", "treatment_pcgrad")
                for update in range(1, 65)
            ]
            self.assertEqual(len(all_outputs), 130)
            self.assertEqual(len({id(output) for output in all_outputs}), 130)
            for tensor_name in ("probabilities", "probability_offsets", "values"):
                self.assertEqual(
                    len({output[tensor_name].data_ptr() for output in all_outputs}),
                    130,
                )
            baseline_step_identities = {
                f"updates/{update:02d}/{arm}": pilot._raw_step_record_sha256_v2(
                    gradients["series"][f"updates/{update:02d}/{arm}"],
                    arm=arm, update_ordinal=update,
                )
                for arm in ("control_vanilla", "treatment_pcgrad")
                for update in range(1, 65)
            }
            baseline_stage1_outputs = copy.deepcopy(
                gradients["stage2_start_states"]
            )
            del gradients["series"]["updates/17/treatment_pcgrad"][
                "anchor_kl_gradient"
            ]
            buffer = io.BytesIO()
            torch.save(gradients, buffer)
            (directory / "gradient_tensors.pt").write_bytes(buffer.getvalue())
            manifest_hash = self.refresh_manifest(directory, summary)
            malformed = pilot.recompute_pending_gates(
                spec=spec, prepare_receipt=receipt,
                manifest_path=directory / "manifest.json",
                manifest_sha256=manifest_hash,
            )
            self.assertEqual(set(malformed), pilot.RECOMPUTATION_RESULT_KEYS_V2)
            self.assertFalse(malformed["offline_pass"])
            self.assertFalse(any(
                failure.startswith("fail_closed:")
                for failure in malformed["failures"]
            ))
            self.assertIn(
                "step_raw_binding:treatment_pcgrad:17:ValueError:"
                "raw step identity key set mismatch",
                malformed["failures"],
            )
            self.assertIn(
                "treatment_replay:update:17:ValueError:series item key set",
                malformed["failures"],
            )

            for field, expected_failure in (
                (
                    "ordered_outputs",
                    "step_record_binding:treatment_pcgrad:64",
                ),
                (
                    "postclip_coefficient",
                    "step_record_binding:treatment_pcgrad:64",
                ),
            ):
                (directory / "gradient_tensors.pt").write_bytes(
                    original_gradient_bytes
                )
                summary = copy.deepcopy(original_summary)
                gradients = torch.load(
                    directory / "gradient_tensors.pt", map_location="cpu",
                    weights_only=True,
                )
                item = gradients["series"][
                    "updates/64/treatment_pcgrad"
                ]
                if field == "ordered_outputs":
                    tensor = item[field]["probabilities"]
                    tensor[0] = torch.nextafter(
                        tensor[0], torch.tensor(math.inf, dtype=torch.float32)
                    )
                else:
                    item[field] = float(torch.nextafter(
                        torch.tensor(item[field], dtype=torch.float32),
                        torch.tensor(-math.inf, dtype=torch.float32),
                    ))
                changed_identities = [
                    key for key, original in baseline_step_identities.items()
                    if pilot._raw_step_record_sha256_v2(
                        gradients["series"][key],
                        arm=key.rsplit("/", 1)[1],
                        update_ordinal=int(key.split("/")[1]),
                    ) != original
                ]
                self.assertEqual(
                    changed_identities, ["updates/64/treatment_pcgrad"]
                )
                for arm in ("control_vanilla", "treatment_pcgrad"):
                    self.assertTrue(pilot._nested_byte_exact_v2(
                        gradients["stage2_start_states"][arm]["stage1_outputs"],
                        baseline_stage1_outputs[arm]["stage1_outputs"],
                    ))
                buffer = io.BytesIO()
                torch.save(gradients, buffer)
                (directory / "gradient_tensors.pt").write_bytes(
                    buffer.getvalue()
                )
                manifest_hash = self.refresh_manifest(directory, summary)
                mutated = pilot.recompute_pending_gates(
                    spec=spec, prepare_receipt=receipt,
                    manifest_path=directory / "manifest.json",
                    manifest_sha256=manifest_hash,
                )
                self.assertFalse(mutated["offline_pass"])
                self.assertFalse(any(
                    failure.startswith("fail_closed:")
                    for failure in mutated["failures"]
                ))
                binding_failures = {
                    failure for failure in mutated["failures"]
                    if failure.startswith(step_binding_prefixes)
                }
                self.assertEqual(binding_failures, {expected_failure})
                new_failures = set(mutated["failures"]) - set(result["failures"])
                checkpoint_output_failures = {
                    "checkpoint:treatment_pcgrad:metadata:terminal_output_hashes",
                    "checkpoint:treatment_pcgrad:recomputed_terminal_output_hashes",
                    "checkpoint:treatment_pcgrad:update64_outputs",
                }
                if field == "ordered_outputs":
                    permitted = checkpoint_output_failures | {expected_failure}
                else:
                    permitted = checkpoint_output_failures | {
                        expected_failure,
                        "treatment_replay:update:64:ValueError:postclip coefficient",
                        "numerical:treatment_replay:update:64:ValueError:"
                        "postclip coefficient",
                        "numerical:END:missing",
                        "numerical:missing_outputs:treatment_pcgrad:64",
                        "numerical:numerical_outputs:64",
                        "summary_discrepancy:run_summary:safety_stop",
                        *{
                            f"numerical:safety:treatment_pcgrad:{update}"
                            for update in range(1, 64)
                        },
                    }
                self.assertEqual(new_failures, permitted)
                if field == "postclip_coefficient":
                    self.assertIn(
                        "treatment_replay:update:64:ValueError:"
                        "postclip coefficient",
                        mutated["failures"],
                    )

    def test_finalize_unmocked_recompute_publishes_exact_four_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pending = root / "pending"
            final = root / "final"
            pending.mkdir()
            receipt, spec, _summary, manifest_hash = self.write_complete_bundle(
                pending
            )
            spec_without_hash = dict(spec)
            spec_without_hash.pop("_file_sha256")
            with (
                mock.patch.object(
                    pilot, "_validate_execution_spec",
                    return_value=(spec_without_hash, receipt, pending, final),
                ),
                mock.patch.object(
                    pilot, "_authority_receipt",
                    side_effect=[(None, ["missing numerical"]), (None, ["missing root"])],
                ),
            ):
                result = pilot.finalize(
                    execution_spec=root / "spec.json",
                    execution_spec_sha256="A" * 64,
                    pending_manifest=pending / "manifest.json",
                    pending_manifest_sha256=manifest_hash,
                    numerical_audit_receipt=root / "numerical.json",
                    numerical_audit_receipt_sha256="D" * 64,
                    root_recomputation_receipt=root / "root.json",
                    root_recomputation_receipt_sha256="E" * 64,
                )
            self.assertEqual(result["status"], "REJECTED")
            self.assertEqual(
                {path.name for path in final.iterdir()},
                set(pilot.FINAL_REJECTED_FILES),
            )

    def test_serialized_summary_mutations_fail_after_hash_refresh(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            receipt, spec, summary, _manifest_hash = self.write_complete_bundle(
                directory
            )
            for field, mutate, expected in (
                (
                    "execution_spec_path",
                    lambda value: value.update(execution_spec_path="forged.json"),
                    "run_summary:execution_spec_path",
                ),
                (
                    "checkpoint_reload_evidence",
                    lambda value: value["checkpoint_reload_evidence"].update(
                        unexpected_nested_key=True
                    ),
                    "run_summary:checkpoint_reload_evidence",
                ),
            ):
                candidate = copy.deepcopy(summary)
                mutate(candidate)
                manifest_hash = self.refresh_manifest(directory, candidate)
                result = pilot.recompute_pending_gates(
                    spec=spec, prepare_receipt=receipt,
                    manifest_path=directory / "manifest.json",
                    manifest_sha256=manifest_hash,
                )
                self.assertFalse(result["offline_pass"], field)
                self.assertIn(
                    f"summary_discrepancy:{expected}", result["failures"], field
                )
                self.assertNotIn("run_summary_self_hash", result["failures"])
                self.assertFalse(any(
                    failure.startswith(("sha256:run_summary", "size:run_summary"))
                    for failure in result["failures"]
                ))


class CorrectedPublicationTests(unittest.TestCase):
    def setUp(self):
        self.allowed = pilot._repo_path(pilot.IMPLEMENTATION_RELATIVE_PATH) / "test_outputs"
        self.allowed.mkdir(exist_ok=True)
        self.paths = []

    def tearDown(self):
        for path in self.paths:
            shutil.rmtree(path, ignore_errors=True)

    def output(self, prefix):
        path = self.allowed / f"{prefix}_{uuid.uuid4().hex}"
        self.paths.append(path)
        return path

    def runtime_state(self):
        source_hashes = pilot.inherited.checkpoint_source_hashes()
        model, metadata, _ = pilot.load_checkpoint(
            pilot._repo_path(pilot.INPUT_CHECKPOINT_RELATIVE_PATH),
            expected_source_hashes=source_hashes, device="cpu",
        )
        pilot.base._set_trainability(model, stage=1)
        optimizer = StaticOptimizerState({
            "state": {},
            "param_groups": [{
                "lr": 1e-4, "betas": (0.9, 0.999), "eps": 1e-8,
                "weight_decay": 0.0, "amsgrad": False, "maximize": False,
                "foreach": None, "capturable": False,
                "differentiable": False, "fused": None,
                "decoupled_weight_decay": False,
                "params": list(range(len(pilot.OPTIMIZER_PARAMETER_NAMES))),
            }],
        })
        progress = pilot.base.ExecutionProgress(model=model, optimizer=optimizer)
        return {
            "model": model, "optimizer": optimizer, "progress": progress,
            "input_metadata": metadata, "source_hashes": source_hashes,
        }

    def pending_run(self, phase="control_step"):
        control = self.runtime_state()
        treatment = self.runtime_state()
        arms = {"control_vanilla": control, "treatment_pcgrad": treatment}
        run = pilot._empty_run(arms, {}, failure={"phase": phase})
        return run

    def test_runtime_checkpoint_schema_loads_checked_loader(self):
        state = self.runtime_state()
        payload = pilot._serialize_checkpoint(
            state, arm="control_vanilla",
            spec={"implementation_snapshot_file_count": 57, "implementation_snapshot_sha256": "A" * 64},
            execution_spec_sha256="B" * 64,
            prepare_receipt={
                "receipt_sha256": "C" * 64,
                "predecessor_execution_stop": predecessor_stop_binding(),
            },
            synchronized_steps=0, output_hashes=None,
        )
        evidence = pilot._validate_runtime_checkpoint_bytes(
            payload, state, expected_arm="control_vanilla", expected_steps=0
        )
        self.assertTrue(evidence["runtime_loader_pass"])
        self.assertEqual(set(torch.load(io.BytesIO(payload), weights_only=False)), {"model_config", "model_state", "metadata", "optimizer_state"})

    def test_each_failure_phase_can_publish_complete_pending_only(self):
        for phase in ("control_step", "treatment_step", "post_step_diagnostics", "stage2_safety"):
            output = self.output("pending")
            result = pilot.publish_pending_bundle(
                pending_directory=output, run=self.pending_run(phase),
                prepare_receipt={
                    "receipt_sha256": "C" * 64,
                    "predecessor_execution_stop": predecessor_stop_binding(),
                },
                spec={
                    "prepare_receipt_path": "x", "prepare_receipt_file_sha256": "D" * 64,
                    "prepare_receipt_sha256": "C" * 64,
                    "implementation_snapshot_file_count": 57,
                    "implementation_snapshot_sha256": "A" * 64,
                },
                execution_spec_path=Path("spec.json"), execution_spec_sha256="B" * 64,
            )
            self.assertEqual(result["status"], "PENDING_AUDIT")
            self.assertEqual({path.name for path in output.iterdir()}, set(pilot.PENDING_FILES))
            self.assertFalse((output / "ACCEPTED").exists())
            self.assertFalse((output / "REJECTED").exists())

    def test_strict_shape_rejects_missing_family_priority_update_and_steps(self):
        run = {
            "completed_optimizer_steps_per_arm": {"control_vanilla": 65, "treatment_pcgrad": 65},
            "update_records": {"control_vanilla": [{}] * 64, "treatment_pcgrad": [{}] * 64},
            "full_830_row_diagnostics": {"control_vanilla": {}, "treatment_pcgrad": {}},
            "alignment_summaries": {}, "all_safety_gates_pass": True,
            "failure": None, "stage1_equality": {"passed": True},
            "control_update32_reference": {"passed": True},
            "mechanism": {"surgery_nonzero": True, "tasks_touched_first_16": list(pilot.AUDIT_ADVERSE_TASKS), "cumulative_delta_projections": {}},
            "terminal_END_controls": {"passed": True},
            "duplicate_treatment_canonical_outputs_identical": True,
        }
        gates = pilot._strict_gate_shape_from_run(run)
        self.assertFalse(gates["offline_pass"])
        self.assertTrue(any("milestone_rows" in failure for failure in gates["failures"]))
        self.assertTrue(any("alignment_updates" in failure for failure in gates["failures"]))

    def test_execute_publishes_pending_and_never_final(self):
        pending = self.output("pending")
        final = self.output("final")
        self.paths.remove(final)
        receipt = {"runtime_thread_receipt": {}, "receipt_sha256": "C" * 64}
        spec = {"prepare_receipt_path": "x"}
        with (
            mock.patch.object(pilot, "_validate_execution_spec", return_value=(spec, receipt, pending, final)),
            mock.patch.object(pilot.inherited, "_runtime_identity", return_value={}),
            mock.patch.object(pilot, "_require_prepare_rebuild"),
            mock.patch.object(pilot, "run_matched_arms", return_value={"completed_optimizer_steps_per_arm": {"control_vanilla": 0, "treatment_pcgrad": 0}}),
            mock.patch.object(pilot, "publish_pending_bundle", return_value={"status": "PENDING_AUDIT", "games_run": 0}) as publish,
        ):
            result = pilot.execute(execution_spec=Path("spec.json"), execution_spec_sha256="A" * 64)
        self.assertEqual(result["status"], "PENDING_AUDIT")
        publish.assert_called_once()
        self.assertFalse(final.exists())

    def test_finalize_is_load_only_rejects_without_authorities_and_writes_four(self):
        pending = self.output("pending")
        final = self.output("final")
        pending.mkdir()
        (pending / "manifest.json").write_bytes(b"{}\n")
        (pending / "control_pending.pt").write_bytes(b"control")
        (pending / "treatment_pending.pt").write_bytes(b"treatment")
        manifest = {
            "manifest_core_sha256": "E" * 64,
            "files": {
                "control_pending.pt": {"sha256": pilot.sha256_file(pending / "control_pending.pt")},
                "treatment_pending.pt": {"sha256": pilot.sha256_file(pending / "treatment_pending.pt")},
            },
            "completed_optimizer_steps_per_arm": {"control_vanilla": 65, "treatment_pcgrad": 65},
        }
        strict = {"offline_pass": True, "bundle_integrity_pass": True, "failures": [], "recomputed": {}}
        with (
            mock.patch.object(
                pilot, "_validate_execution_spec",
                return_value=({}, {"receipt_sha256": "C" * 64}, pending, final),
            ),
            mock.patch.object(pilot, "_load_pending_manifest", return_value=(manifest, [])),
            mock.patch.object(pilot, "recompute_pending_gates", return_value=strict),
            mock.patch.object(
                pilot, "_authority_receipt",
                side_effect=[(None, ["missing numerical"]), (None, ["missing root"])],
            ),
            mock.patch.object(
                pilot, "run_matched_arms", side_effect=AssertionError("training reached")
            ),
        ):
            result = pilot.finalize(
                execution_spec=Path("spec.json"), execution_spec_sha256="A" * 64,
                pending_manifest=pending / "manifest.json",
                pending_manifest_sha256="B" * 64,
                numerical_audit_receipt=Path("missing_numerical.json"),
                numerical_audit_receipt_sha256="D" * 64,
                root_recomputation_receipt=Path("missing_root.json"),
                root_recomputation_receipt_sha256="F" * 64,
            )
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(
            {path.name for path in final.iterdir()}, set(pilot.FINAL_REJECTED_FILES)
        )


if __name__ == "__main__":
    unittest.main()
