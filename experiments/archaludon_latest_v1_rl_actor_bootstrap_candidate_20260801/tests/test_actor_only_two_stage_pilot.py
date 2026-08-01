"""Focused iteration-006 tests.  Optimizer steps here use only synthetic losses."""

from __future__ import annotations

from copy import deepcopy
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import torch

from archaludon_rl import actor_only_two_stage_pilot as pilot
from archaludon_rl.model import ModelConfig, ResidualActorCritic


class ActorOnlyTwoStageMathTests(unittest.TestCase):
    def test_lower_empirical_median_never_averages(self) -> None:
        self.assertEqual(pilot.lower_empirical_median([4.0, 1.0, 3.0, 2.0]), 2.0)
        self.assertEqual(pilot.lower_empirical_median([3.0, 1.0, 2.0]), 2.0)
        with self.assertRaises(ValueError):
            pilot.lower_empirical_median([])

    def test_deadband_boundaries_are_neutral_and_strict(self) -> None:
        tau = pilot.DEADBAND_TAU
        self.assertEqual(pilot.orientation_class(tau), "neutral")
        self.assertEqual(pilot.orientation_class(-tau), "neutral")
        self.assertEqual(pilot.orientation_class(math.nextafter(tau, math.inf)), "aligned")
        self.assertEqual(
            pilot.orientation_class(math.nextafter(-tau, -math.inf)), "anti_aligned"
        )

    def test_global_alignment_counts_every_row_once(self) -> None:
        summary = pilot.alignment_summary([2e-7, -2e-7, 0.0, 1e-7, -1e-7])
        self.assertEqual(summary["aligned_count"], 1)
        self.assertEqual(summary["anti_aligned_count"], 1)
        self.assertEqual(summary["neutral_count"], 3)
        self.assertEqual(summary["score"], 0.0)
        self.assertEqual(summary["row_count"], 5)

    def test_stage2_score_boundary_is_inclusive_but_median_is_strict(self) -> None:
        stage_1 = {"score": 0.25, "lower_empirical_median": 2e-7}
        at_boundary = {
            "score": 0.24,
            "lower_empirical_median": 2e-7 + pilot.DEADBAND_TAU,
        }
        result = pilot.evaluate_stage2_improvement(stage_1, at_boundary)
        self.assertEqual(result["failures"], ["global_lower_median"])
        beyond = dict(at_boundary)
        beyond["lower_empirical_median"] = math.nextafter(
            at_boundary["lower_empirical_median"], math.inf
        )
        self.assertTrue(pilot.evaluate_stage2_improvement(stage_1, beyond)["accepted"])
        below_score = dict(beyond)
        below_score["score"] = math.nextafter(0.24, -math.inf)
        self.assertEqual(
            pilot.evaluate_stage2_improvement(stage_1, below_score)["failures"],
            ["global_alignment_score"],
        )

    def test_anchor_correction_is_fixed_and_nonadaptive(self) -> None:
        correction = pilot._load_correction()
        anchor = correction["corrections"]["anchor_kl_coefficient"]
        self.assertEqual((anchor["stage_1"], anchor["stage_2"]), (0.1, 0.1))
        self.assertFalse(anchor["adaptive_adjustment_between_stages"])


class ActorOnlyTwoStageSyntheticOptimizerTests(unittest.TestCase):
    def test_same_adam_object_mixed_step_state_and_value_exclusion(self) -> None:
        # These are synthetic tensor losses, not PPO rows and not real training.
        torch.manual_seed(1234)
        model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
        initial = {name: value.detach().clone() for name, value in model.state_dict().items()}
        pilot._set_trainability(model, stage=1)
        optimizer = pilot._new_actor_adam(model)
        optimizer_identity = optimizer
        optimizer.zero_grad(set_to_none=True)
        sum(dict(model.named_parameters())[name].sum() for name in pilot.STAGE1_TRAINABLE_NAMES).backward()
        optimizer.step()
        self.assertEqual(
            pilot.audit_optimizer_contract(optimizer, model, stage=1),
            {name: 1 for name in pilot.STAGE1_TRAINABLE_NAMES},
        )
        changed_stage_1 = [
            name for name, before in initial.items()
            if not torch.equal(before, model.state_dict()[name])
        ]
        self.assertEqual(changed_stage_1, list(pilot.STAGE1_TRAINABLE_NAMES))

        pilot._set_trainability(model, stage=2)
        optimizer.zero_grad(set_to_none=True)
        named = dict(model.named_parameters())
        sum((index + 1) * named[name].sum() for index, name in enumerate(pilot.EXPECTED_ACTOR_NAMES)).backward()
        optimizer.step()
        self.assertIs(optimizer, optimizer_identity)
        expected_steps = {
            name: (2 if name in pilot.STAGE1_TRAINABLE_NAMES else 1)
            for name in pilot.EXPECTED_ACTOR_NAMES
        }
        self.assertEqual(
            pilot.audit_optimizer_contract(optimizer, model, stage=2), expected_steps
        )
        changed_final = [
            name for name, before in initial.items()
            if not torch.equal(before, model.state_dict()[name])
        ]
        self.assertEqual(changed_final, list(pilot.EXPECTED_ACTOR_NAMES))
        for name in pilot.EXPECTED_VALUE_NAMES:
            self.assertTrue(torch.equal(initial[name], model.state_dict()[name]))

    def test_serialized_mixed_step_state_round_trip(self) -> None:
        # Synthetic tensor updates only; no dataset, PPO row, or real checkpoint input.
        torch.manual_seed(99)
        model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
        pilot._set_trainability(model, stage=1)
        optimizer = pilot._new_actor_adam(model)
        optimizer.zero_grad(set_to_none=True)
        named = dict(model.named_parameters())
        sum(named[name].sum() for name in pilot.STAGE1_TRAINABLE_NAMES).backward()
        optimizer.step()
        pilot._set_trainability(model, stage=2)
        optimizer.zero_grad(set_to_none=True)
        sum((index + 1) * named[name].sum() for index, name in enumerate(pilot.EXPECTED_ACTOR_NAMES)).backward()
        optimizer.step()
        source_hashes = pilot.inherited.checkpoint_source_hashes()
        metadata = pilot.checkpoint_metadata(source_hashes=source_hashes, training={"synthetic_test": True})
        payload = pilot.inherited._serialize_checkpoint_payload(model, metadata, optimizer)
        digest = pilot.hashlib.sha256(payload).hexdigest().upper()
        result = pilot._validate_serialized_checkpoint(
            payload,
            claimed_sha256=digest,
            model=model,
            metadata=metadata,
            optimizer=optimizer,
            source_hashes=source_hashes,
            completed_stage=2,
        )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["optimizer_state_steps"]["residual_head.2.weight"], 2)


def _aligned_metrics(receipt: dict, *, delta: float = 2e-6) -> list[dict]:
    metrics = []
    for fixed in receipt["rows"]:
        probabilities = list(fixed["initial_probabilities_float32"])
        sampled = fixed["sampled_index"]
        normalized = fixed["fixed_normalized_advantage_float32"]
        other = next(index for index in range(len(probabilities)) if index != sampled)
        if normalized > 0.0:
            probabilities[sampled] += delta
            probabilities[other] -= delta
        else:
            probabilities[sampled] -= delta
            receiver = fixed["teacher_index"] if fixed["teacher_index"] != sampled else other
            probabilities[receiver] += delta
        oriented = (1.0 if normalized > 0.0 else -1.0) * (
            probabilities[sampled] - fixed["initial_probabilities_float32"][sampled]
        )
        maximum = max(probabilities)
        winners = [index for index, value in enumerate(probabilities) if value == maximum]
        metrics.append(
            {
                "stage": 1,
                "ppo_row_ordinal": fixed["ppo_row_ordinal"],
                "public_state_sha256": fixed["public_state_sha256"],
                "behavior_action_order_sha256": fixed["behavior_action_order_sha256"],
                "sampled_index": sampled,
                "sampled_option_type": fixed["sampled_option_type"],
                "probabilities_float32": probabilities,
                "value_float32": fixed["initial_value_float32"],
                "unique_argmax_index": winners[0] if len(winners) == 1 else None,
                "sampled_probability_delta_from_initial": (
                    probabilities[sampled] - fixed["initial_probabilities_float32"][sampled]
                ),
                "oriented_sampled_probability_delta": oriented,
                "orientation": "aligned",
                "anchor_kl_post_to_zero": 0.0,
                "total_variation_from_initial": 0.0,
            }
        )
    return metrics


def _synthetic_progress(completed_stage: int, *, inject_nan: bool = False):
    """Take synthetic tensor-only Adam steps; never touches the 830-row dataset."""

    torch.manual_seed(20260801 + completed_stage)
    model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
    pilot._set_trainability(model, stage=1)
    optimizer = pilot._new_actor_adam(model)
    progress = pilot.ExecutionProgress(model=model, optimizer=optimizer)
    named = dict(model.named_parameters())
    optimizer.zero_grad(set_to_none=True)
    sum(named[name].sum() for name in pilot.STAGE1_TRAINABLE_NAMES).backward()
    pilot._optimizer_step_and_record(optimizer, progress, stage=1)
    progress.failure_phase = "stage_1_post_step_injected"
    if completed_stage == 2:
        progress.stage_2_entered = True
        pilot._set_trainability(model, stage=2)
        optimizer.zero_grad(set_to_none=True)
        sum(
            (index + 1) * named[name].sum()
            for index, name in enumerate(pilot.EXPECTED_ACTOR_NAMES)
        ).backward()
        pilot._optimizer_step_and_record(optimizer, progress, stage=2)
        progress.failure_phase = "stage_2_post_step_injected"
    if inject_nan:
        with torch.no_grad():
            named["residual_head.2.weight"].view(-1)[0] = float("nan")
    return model, optimizer, progress


def _mutate_synthetic_optimizer_contract(
    model: ResidualActorCritic,
    optimizer: torch.optim.Adam,
    *,
    completed_stage: int,
    mutation: str,
) -> None:
    expected = pilot._expected_optimizer_steps(completed_stage)
    target_name = next(iter(expected))
    target = dict(model.named_parameters())[target_name]
    if mutation == "missing":
        optimizer.state.pop(target)
    elif mutation == "wrong_step":
        optimizer.state[target]["step"].fill_(expected[target_name] + 7)
    elif mutation == "nonfinite":
        optimizer.state[target]["exp_avg"].view(-1)[0] = float("nan")
    elif mutation == "extra":
        extra = torch.nn.Parameter(torch.zeros(1, dtype=target.dtype))
        optimizer.param_groups[0]["params"].append(extra)
        optimizer.state[extra] = {
            "step": optimizer.state[target]["step"].detach().clone(),
            "exp_avg": torch.zeros_like(extra),
            "exp_avg_sq": torch.zeros_like(extra),
        }
    else:  # pragma: no cover - test helper misuse
        raise AssertionError(f"unknown mutation: {mutation}")


def _passing_final_run() -> dict:
    stage_1_steps = {name: 1 for name in pilot.STAGE1_TRAINABLE_NAMES}
    stage_2_steps = {
        name: (2 if name in pilot.STAGE1_TRAINABLE_NAMES else 1)
        for name in pilot.EXPECTED_ACTOR_NAMES
    }
    return {
        "stopped_before_stage_2": False,
        "optimizer_steps_completed": 2,
        "same_optimizer_object_across_stages": True,
        "stage_1_gates": {
            "global_pass": True,
            "global_failures": [],
            "family_diagnostics": {"all_pass": False, "failures": ["diagnostic"]},
        },
        "stage_2_gates": {"acceptance_failures": [], "accepted_at_stage": True},
        "stage_2_directional_gates": {"passed": True, "failures": []},
        "stage_2_improvement": {"accepted": True, "failures": []},
        "stage_1_report": {
            "changed_parameter_names_from_initial": list(pilot.STAGE1_TRAINABLE_NAMES),
            "optimizer_state_steps": stage_1_steps,
            "fixed_advantages_sha256": "A" * 64,
            "fixed_behavior_logprobabilities_sha256": "B" * 64,
        },
        "stage_2_report": {
            "changed_parameter_names_from_initial": list(pilot.EXPECTED_ACTOR_NAMES),
            "optimizer_state_steps": stage_2_steps,
            "fixed_advantages_sha256": "A" * 64,
            "fixed_behavior_logprobabilities_sha256": "B" * 64,
        },
        "weighted_value_loss_stage_1": 0.0,
        "weighted_value_loss_stage_2": 0.0,
        "initial_value_head_parameter_hashes": {"value": "C" * 64},
        "final_value_head_parameter_hashes": {"value": "C" * 64},
        "stage_1_value_change_summary": {"nonfinite_count": 0},
        "stage_2_value_change_summary": {"nonfinite_count": 0},
        "raw_value_mse_initial": 1.0,
        "raw_value_mse_stage_1": 1.0,
        "raw_value_mse_stage_2": 1.0,
        "fixed_anchor_kl_coefficient_stage_1": 0.1,
        "fixed_anchor_kl_coefficient_stage_2": 0.1,
        "adaptive_anchor_kl_adjustment_between_stages": False,
    }


class ActorOnlyTwoStageRemediationTests(unittest.TestCase):
    def _guarded_output(self):
        candidate = pilot._repo_path(pilot.IMPLEMENTATION_RELATIVE_PATH)
        test_root = candidate / "test_outputs"
        test_root.mkdir(exist_ok=True)
        return tempfile.TemporaryDirectory(prefix="iteration006-remediation-", dir=test_root)

    def _assert_rejected_artifacts(self, directory: Path, expected_steps: int) -> dict:
        self.assertEqual([item.name for item in directory.glob("*.pt")], ["candidate.pt"])
        self.assertTrue((directory / "rejected_receipt.json").is_file())
        self.assertTrue((directory / "REJECTED").is_file())
        self.assertFalse((directory / "accepted_receipt.json").exists())
        self.assertFalse((directory / "ACCEPTED").exists())
        receipt = json.loads((directory / "rejected_receipt.json").read_text(encoding="utf-8"))
        core = dict(receipt)
        receipt_hash = core.pop("receipt_sha256")
        self.assertEqual(pilot.canonical_sha256(core), receipt_hash)
        self.assertEqual(receipt["optimizer_steps_completed"], expected_steps)
        self.assertTrue(receipt["checkpoint_readback_exact"])
        self.assertFalse(receipt["accepted_marker_written"])
        return receipt

    def test_stage1_post_step_exception_retains_one_byte_exact_rejected_checkpoint(self) -> None:
        model, optimizer, progress = _synthetic_progress(1, inject_nan=True)
        self.assertEqual(progress.optimizer_steps_completed, 1)
        self.assertFalse(progress.stage_2_entered)
        source_hashes = pilot.inherited.checkpoint_source_hashes()
        with self._guarded_output() as temporary:
            directory = Path(temporary)
            guard = pilot.inherited._StableDirectoryGuard(directory)
            guard.__enter__()
            try:
                result = pilot._publish_post_step_rejection(
                    directory,
                    progress=progress,
                    source_hashes=source_hashes,
                    execution_spec_path=directory / "synthetic-execution.json",
                    execution_spec_sha256="D" * 64,
                    phase=progress.failure_phase,
                    error=RuntimeError("injected after stage 1 step"),
                    directory_guard=guard,
                )
            finally:
                guard.close()
            self.assertEqual(result["status"], "rejected")
            receipt = self._assert_rejected_artifacts(directory, 1)
            self.assertEqual(
                receipt["retention_validation"]["optimizer_state_steps"],
                {name: 1 for name in pilot.STAGE1_TRAINABLE_NAMES},
            )
            self.assertGreater(receipt["model_nonfinite_count"], 0)
            self.assertIs(progress.model, model)
            self.assertIs(progress.optimizer, optimizer)

    def test_stage2_post_step_exception_retains_mixed_same_adam_state(self) -> None:
        model, optimizer, progress = _synthetic_progress(2)
        self.assertEqual(progress.optimizer_steps_completed, 2)
        self.assertTrue(progress.stage_2_entered)
        source_hashes = pilot.inherited.checkpoint_source_hashes()
        with self._guarded_output() as temporary:
            directory = Path(temporary)
            guard = pilot.inherited._StableDirectoryGuard(directory)
            guard.__enter__()
            try:
                pilot._publish_post_step_rejection(
                    directory,
                    progress=progress,
                    source_hashes=source_hashes,
                    execution_spec_path=directory / "synthetic-execution.json",
                    execution_spec_sha256="E" * 64,
                    phase=progress.failure_phase,
                    error=RuntimeError("injected after stage 2 step"),
                    directory_guard=guard,
                )
            finally:
                guard.close()
            receipt = self._assert_rejected_artifacts(directory, 2)
            expected = {
                name: (2 if name in pilot.STAGE1_TRAINABLE_NAMES else 1)
                for name in pilot.EXPECTED_ACTOR_NAMES
            }
            self.assertEqual(
                receipt["retention_validation"]["optimizer_state_steps"], expected
            )
            self.assertIs(progress.model, model)
            self.assertIs(progress.optimizer, optimizer)

    def test_stage1_and_stage2_malformed_optimizer_state_is_retained_as_rejection_evidence(self) -> None:
        source_hashes = pilot.inherited.checkpoint_source_hashes()
        for completed_stage in (1, 2):
            for mutation in ("missing", "extra", "wrong_step", "nonfinite"):
                with self.subTest(completed_stage=completed_stage, mutation=mutation):
                    model, optimizer, progress = _synthetic_progress(completed_stage)
                    _mutate_synthetic_optimizer_contract(
                        model,
                        optimizer,
                        completed_stage=completed_stage,
                        mutation=mutation,
                    )
                    historical_count = progress.optimizer_steps_completed
                    with self._guarded_output() as temporary:
                        directory = Path(temporary)
                        guard = pilot.inherited._StableDirectoryGuard(directory)
                        guard.__enter__()
                        try:
                            pilot._publish_post_step_rejection(
                                directory,
                                progress=progress,
                                source_hashes=source_hashes,
                                execution_spec_path=(
                                    directory / "synthetic-execution.json"
                                ),
                                execution_spec_sha256="7" * 64,
                                phase=progress.failure_phase,
                                error=RuntimeError(
                                    f"injected {mutation} optimizer state"
                                ),
                                directory_guard=guard,
                            )
                        finally:
                            guard.close()
                        receipt = self._assert_rejected_artifacts(
                            directory, historical_count
                        )
                        self.assertEqual(
                            progress.optimizer_steps_completed, historical_count
                        )
                        self.assertFalse(receipt["optimizer_contract_pass"])
                        self.assertTrue(receipt["optimizer_contract_failures"])
                        self.assertEqual(
                            receipt["optimizer_steps_expected"],
                            pilot._expected_optimizer_steps(completed_stage),
                        )
                        self.assertEqual(
                            receipt["retention_validation"][
                                "optimizer_steps_observed"
                            ],
                            receipt["optimizer_steps_observed"],
                        )

    def test_execute_reuses_identity_verified_hardlink_handoff(self) -> None:
        model, optimizer, synthetic_progress = _synthetic_progress(2)
        run = {
            **_passing_final_run(),
            "model": model,
            "optimizer": optimizer,
        }
        source_hashes = pilot.inherited.checkpoint_source_hashes()
        loaded = {
            "checkpoint_path": pilot._repo_path(
                pilot.INPUT_CHECKPOINT_RELATIVE_PATH
            ),
            "source_hashes": source_hashes,
        }

        def fake_run(_loaded, _probe, progress):
            progress.model = model
            progress.optimizer = optimizer
            progress.optimizer_steps_completed = 2
            progress.stage_2_entered = True
            progress.failure_phase = synthetic_progress.failure_phase
            return run

        with self._guarded_output() as temporary:
            output = Path(temporary) / "execution-output"
            real_publisher = pilot.inherited._publish_checkpoint_exclusive
            with (
                mock.patch.object(pilot.inherited, "_runtime_identity", return_value={}),
                mock.patch.object(pilot, "_load_execution_spec", return_value={}),
                mock.patch.object(
                    pilot,
                    "_validate_execution_boundary",
                    return_value=({"receipt_sha256": "6" * 64}, output),
                ),
                mock.patch.object(
                    pilot.inherited, "_load_validated_inputs", return_value=loaded
                ),
                mock.patch.object(pilot, "_run_two_stage", side_effect=fake_run),
                mock.patch.object(
                    pilot.inherited,
                    "_after_checkpoint_public_identity_verified",
                    side_effect=RuntimeError("injected after verified identity"),
                ),
                mock.patch.object(
                    pilot.inherited,
                    "_publish_checkpoint_exclusive",
                    wraps=real_publisher,
                ) as publish,
            ):
                result = pilot.execute(
                    execution_spec=Path(temporary) / "synthetic-execution.json",
                    execution_spec_sha256="8" * 64,
                )
            self.assertEqual(publish.call_count, 1)
            self.assertEqual(result["status"], "rejected")
            receipt = self._assert_rejected_artifacts(output, 2)
            self.assertTrue(receipt["checkpoint_evidence_transferred"])

    def test_unverified_candidate_collision_preserves_unknown_and_never_accepts(self) -> None:
        model, optimizer, synthetic_progress = _synthetic_progress(2)
        run = {
            **_passing_final_run(),
            "model": model,
            "optimizer": optimizer,
        }
        loaded = {
            "checkpoint_path": pilot._repo_path(
                pilot.INPUT_CHECKPOINT_RELATIVE_PATH
            ),
            "source_hashes": pilot.inherited.checkpoint_source_hashes(),
        }

        def fake_run(_loaded, _probe, progress):
            progress.model = model
            progress.optimizer = optimizer
            progress.optimizer_steps_completed = 2
            progress.stage_2_entered = True
            progress.failure_phase = synthetic_progress.failure_phase
            return run

        with self._guarded_output() as temporary:
            output = Path(temporary) / "execution-output"
            output.mkdir()
            unknown = b"unknown-collision-bytes"
            (output / "candidate.pt").write_bytes(unknown)
            guard = pilot.inherited._StableDirectoryGuard(output)
            guard.__enter__()
            real_publisher = pilot.inherited._publish_checkpoint_exclusive
            with (
                mock.patch.object(pilot.inherited, "_runtime_identity", return_value={}),
                mock.patch.object(pilot, "_load_execution_spec", return_value={}),
                mock.patch.object(
                    pilot,
                    "_validate_execution_boundary",
                    return_value=({"receipt_sha256": "6" * 64}, output),
                ),
                mock.patch.object(
                    pilot.inherited, "_load_validated_inputs", return_value=loaded
                ),
                mock.patch.object(
                    pilot.inherited,
                    "_create_and_guard_output_directory",
                    return_value=guard,
                ),
                mock.patch.object(pilot, "_run_two_stage", side_effect=fake_run),
                mock.patch.object(
                    pilot.inherited,
                    "_publish_checkpoint_exclusive",
                    wraps=real_publisher,
                ) as publish,
            ):
                result = pilot.execute(
                    execution_spec=Path(temporary) / "synthetic-execution.json",
                    execution_spec_sha256="9" * 64,
                )
            self.assertEqual(publish.call_count, 1)
            self.assertEqual(result["status"], "rejected")
            self.assertEqual((output / "candidate.pt").read_bytes(), unknown)
            self.assertTrue((output / "REJECTED").is_file())
            self.assertTrue((output / "rejected_receipt.json").is_file())
            self.assertFalse((output / "ACCEPTED").exists())
            self.assertFalse((output / "accepted_receipt.json").exists())

    def test_pre_step_exception_is_zero_and_writes_no_checkpoint(self) -> None:
        model = ResidualActorCritic(ModelConfig(state_dim=3, action_dim=2, hidden_dim=4))
        pilot._set_trainability(model, stage=1)
        optimizer = pilot._new_actor_adam(model)
        progress = pilot.ExecutionProgress(model=model, optimizer=optimizer)
        with self._guarded_output() as temporary:
            directory = Path(temporary)
            guard = pilot.inherited._StableDirectoryGuard(directory)
            guard.__enter__()
            try:
                result = pilot._publish_failure_status(
                    directory,
                    execution_spec_path=directory / "synthetic-execution.json",
                    execution_spec_sha256="F" * 64,
                    phase="stage_1_pre_step_injected",
                    error=RuntimeError("injected before optimizer step"),
                    directory_guard=guard,
                    optimizer_steps_completed=progress.optimizer_steps_completed,
                )
            finally:
                guard.close()
            self.assertEqual(result["optimizer_steps_completed"], 0)
            self.assertEqual(list(directory.glob("*.pt")), [])
            self.assertTrue((directory / "REJECTED").is_file())
            self.assertFalse((directory / "ACCEPTED").exists())

    def test_cli_exit_codes_follow_published_status(self) -> None:
        with (
            mock.patch.object(pilot, "prepare", return_value={"mode": "prepare"}),
            mock.patch("builtins.print"),
        ):
            self.assertEqual(
                pilot.main(["prepare", "--output-receipt", "unused.json"]), 0
            )
        with (
            mock.patch.object(pilot, "execute", return_value={"status": "accepted"}),
            mock.patch("builtins.print"),
        ):
            self.assertEqual(
                pilot.main(
                    ["execute", "--execution-spec", "unused.json", "--execution-spec-sha256", "A" * 64]
                ),
                0,
            )
        with (
            mock.patch.object(pilot, "execute", return_value={"status": "rejected"}),
            mock.patch("builtins.print"),
        ):
            self.assertEqual(
                pilot.main(
                    ["execute", "--execution-spec", "unused.json", "--execution-spec-sha256", "A" * 64]
                ),
                2,
            )
        with mock.patch.object(
            pilot, "execute", side_effect=OSError("publication failed")
        ):
            with self.assertRaises(OSError):
                pilot.main(
                    ["execute", "--execution-spec", "unused.json", "--execution-spec-sha256", "A" * 64]
                )

    def test_final_acceptance_composition_is_complete(self) -> None:
        serialized = {"status": "pass"}
        passing = _passing_final_run()
        result = pilot._final_gate_report(passing, serialized_validation=serialized)
        self.assertTrue(result["accepted"])
        self.assertFalse(passing["stage_1_gates"]["family_diagnostics"]["all_pass"])
        mutations = {
            "stage1_global": lambda row: row["stage_1_gates"].update(
                {"global_pass": False, "global_failures": ["stage1"]}
            ),
            "stage2_global_family": lambda row: row["stage_2_gates"].update(
                {"acceptance_failures": ["stage2"]}
            ),
            "improvement": lambda row: row["stage_2_improvement"].update(
                {"accepted": False, "failures": ["improvement"]}
            ),
            "directional": lambda row: row["stage_2_directional_gates"].update(
                {"passed": False, "failures": ["directional"]}
            ),
            "value": lambda row: row.update(
                {"final_value_head_parameter_hashes": {"value": "X" * 64}}
            ),
            "optimizer": lambda row: row.update(
                {"same_optimizer_object_across_stages": False}
            ),
            "fixed_inputs": lambda row: row["stage_2_report"].update(
                {"fixed_advantages_sha256": "Y" * 64}
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                candidate = deepcopy(passing)
                mutate(candidate)
                self.assertFalse(
                    pilot._final_gate_report(
                        candidate, serialized_validation=serialized
                    )["accepted"]
                )
        self.assertFalse(
            pilot._final_gate_report(
                deepcopy(passing), serialized_validation={"status": "fail"}
            )["accepted"]
        )


class ActorOnlyTwoStageRealPrepareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = pilot.inherited._runtime_identity()
        cls.receipt = pilot._build_prepare_receipt(cls.runtime)

    def test_real_core_reproduces_rows_families_and_parameter_contract(self) -> None:
        receipt = self.receipt
        pilot.validate_prepare_receipt(receipt)
        self.assertEqual((receipt["row_count"], receipt["unique_decision_key_count"]), (830, 830))
        self.assertEqual(receipt["action_families"]["row_map_sha256"], pilot.ROW_MAP_SHA256)
        actual = [
            (
                row["option_type"], row["rows"], row["normalized_positive"],
                row["normalized_negative"], row["membership_sha256"], row["qualifying"],
            )
            for row in receipt["action_families"]["families"]
        ]
        self.assertEqual(
            actual,
            [
                (7, 417, 216, 201, "48ED67F982D8995C2F97FF13E675A04DA8DB6F0BD2923C2EE4277698D96B85E1", True),
                (8, 130, 83, 47, "A4B26D934162A88D987FF36C83EE3D3D4131DE9CAEFA140319AFDB5AC2DDC2D8", True),
                (9, 69, 40, 29, "637F2B2B04D7F037DB3D8121C086F3EEBAEB9337CA59BB6966FE2AC0A9DC403B", True),
                (10, 1, 0, 1, "D930577096D43D4C46B344458EB18754A64BC16488FEAF0E214A27D951F7FB73", False),
                (12, 22, 17, 5, "77179C34377E012125C741AD6A9273FB36AD9111BD1243820E5B18894AE569F0", True),
                (13, 133, 99, 34, "BFF43572DA328BDCB46D263BEFDECFA9F9554E83F02985A4F30DC06E767B7C50", True),
                (14, 58, 22, 36, "95465AC09E2997236C4F058E2B3F9771E6448A3A3838930D8A31DF0E0AAF212F", True),
            ],
        )
        self.assertEqual(
            [len(receipt["directional_memberships"][name]) for name in (
                "negative_target_ordinals",
                "positive_normalized_teacher_and_sampled_end_ordinals",
                "positive_raw_teacher_and_sampled_end_ordinals",
                "teacher_end_ordinals",
            )],
            [4, 20, 31, 43],
        )
        records = receipt["model_parameters"]["records"]
        self.assertEqual([row["name"] for row in records], [*pilot.EXPECTED_ACTOR_NAMES, *pilot.EXPECTED_VALUE_NAMES])
        self.assertEqual(
            [row["name"] for row in records if row["stage_1_trainable"]],
            list(pilot.STAGE1_TRAINABLE_NAMES),
        )
        self.assertEqual(receipt["prepare_proof"]["optimizer_steps"], 0)
        self.assertFalse(receipt["parent_rejection"]["rejected_checkpoint_loaded"])
        self.assertEqual(receipt["plan"]["file_sha256"], pilot.PLAN_SHA256)
        self.assertEqual(
            receipt["plan_correction"]["file_sha256"], pilot.CORRECTION_SHA256
        )

    def test_stage1_family_is_diagnostic_stage2_family_is_mandatory(self) -> None:
        metrics = _aligned_metrics(self.receipt)
        family = next(
            row for row in self.receipt["action_families"]["families"]
            if row["option_type"] == 7
        )
        for ordinal in family["positive_ordinals"]:
            metrics[ordinal]["probabilities_float32"] = list(
                self.receipt["rows"][ordinal]["initial_probabilities_float32"]
            )
            metrics[ordinal]["oriented_sampled_probability_delta"] = 0.0
        stage_1 = pilot.evaluate_stage_gates(self.receipt, metrics, stage=1)
        stage_2 = pilot.evaluate_stage_gates(self.receipt, metrics, stage=2)
        self.assertTrue(stage_1["global_pass"])
        self.assertTrue(stage_1["accepted_at_stage"])
        self.assertFalse(stage_1["family_diagnostics"]["all_pass"])
        self.assertFalse(stage_2["accepted_at_stage"])
        self.assertIn("family:7:positive:median", stage_2["acceptance_failures"])

    def test_family_lower_median_boundary_is_strict(self) -> None:
        metrics = _aligned_metrics(self.receipt)
        family = next(
            row for row in self.receipt["action_families"]["families"]
            if row["option_type"] == 8
        )
        for ordinal in family["negative_ordinals"]:
            metrics[ordinal]["oriented_sampled_probability_delta"] = pilot.DEADBAND_TAU
        at_boundary = pilot._family_diagnostics(self.receipt, metrics)
        self.assertIn("family:8:negative:median", at_boundary["failures"])
        for ordinal in family["negative_ordinals"]:
            metrics[ordinal]["oriented_sampled_probability_delta"] = math.nextafter(
                pilot.DEADBAND_TAU, math.inf
            )
        beyond = pilot._family_diagnostics(self.receipt, metrics)
        self.assertNotIn("family:8:negative:median", beyond["failures"])

    def test_stage_global_bounds_and_unique_argmax_hard_stop(self) -> None:
        metrics = _aligned_metrics(self.receipt)
        for row in metrics:
            row["anchor_kl_post_to_zero"] = 0.002
            row["total_variation_from_initial"] = 0.02
        metrics[0]["anchor_kl_post_to_zero"] = 0.01
        # The one 0.01 row leaves the mean below 0.002 only if other rows are lower.
        for row in metrics[1:]:
            row["anchor_kl_post_to_zero"] = 0.0
        boundary = pilot.evaluate_stage_gates(self.receipt, metrics, stage=1)
        self.assertTrue(boundary["global_pass"])
        for row in metrics:
            row["anchor_kl_post_to_zero"] = 0.002
        mean_boundary = pilot.evaluate_stage_gates(self.receipt, metrics, stage=1)
        self.assertTrue(mean_boundary["global_pass"])
        for row in metrics:
            row["anchor_kl_post_to_zero"] = math.nextafter(0.002, math.inf)
        mean_beyond = pilot.evaluate_stage_gates(self.receipt, metrics, stage=1)
        self.assertIn("global:mean_anchor_kl", mean_beyond["global_failures"])
        for row in metrics:
            row["anchor_kl_post_to_zero"] = 0.0
        metrics[0]["anchor_kl_post_to_zero"] = math.nextafter(0.01, math.inf)
        beyond_kl = pilot.evaluate_stage_gates(self.receipt, metrics, stage=1)
        self.assertIn("global:per_row_anchor_kl", beyond_kl["global_failures"])
        self.assertTrue(beyond_kl["hard_stop_before_stage_2"])
        metrics[0]["anchor_kl_post_to_zero"] = 0.0
        metrics[0]["total_variation_from_initial"] = math.nextafter(0.02, math.inf)
        beyond_tv = pilot.evaluate_stage_gates(self.receipt, metrics, stage=1)
        self.assertIn("global:per_row_total_variation", beyond_tv["global_failures"])
        metrics[0]["total_variation_from_initial"] = 0.0
        probabilities = metrics[0]["probabilities_float32"]
        probabilities[0] = probabilities[1] = max(probabilities)
        tied = pilot.evaluate_stage_gates(self.receipt, metrics, stage=1)
        self.assertIn("row:0:unique_argmax", tied["global_failures"])

    def test_unique_argmax_global_gate_does_not_require_teacher(self) -> None:
        metrics = _aligned_metrics(self.receipt)
        ordinal = next(
            index for index, row in enumerate(self.receipt["rows"])
            if row["legal_option_count"] >= 2 and row["teacher_index"] != 0
        )
        probabilities = [1e-4] * self.receipt["rows"][ordinal]["legal_option_count"]
        probabilities[0] = 1.0 - 1e-4 * (len(probabilities) - 1)
        metrics[ordinal]["probabilities_float32"] = probabilities
        sampled = self.receipt["rows"][ordinal]["sampled_index"]
        delta = probabilities[sampled] - self.receipt["rows"][ordinal]["initial_probabilities_float32"][sampled]
        sign = 1.0 if self.receipt["rows"][ordinal]["fixed_normalized_advantage_float32"] > 0 else -1.0
        metrics[ordinal]["oriented_sampled_probability_delta"] = sign * delta
        result = pilot.evaluate_stage_gates(self.receipt, metrics, stage=1)
        self.assertFalse(any(value == f"row:{ordinal}:unique_argmax" for value in result["global_failures"]))

    def test_value_mse_is_diagnostic_and_weighted_loss_contract_is_zero(self) -> None:
        metrics = _aligned_metrics(self.receipt)
        for fixed, metric in zip(self.receipt["rows"], metrics):
            metric["value_float32"] = fixed["fixed_value_target_float64"]
        self.assertEqual(pilot.raw_value_mse(self.receipt, metrics), 0.0)
        self.assertGreaterEqual(pilot.raw_value_mse(self.receipt), 0.0)
        self.assertEqual(pilot.TWO_STAGE_PPO_CONFIG.value_coef, 0.0)

    def test_receipt_schema_self_hash_and_family_tampering_fail(self) -> None:
        extra = deepcopy(self.receipt)
        extra["unexpected"] = True
        with self.assertRaises(ValueError):
            pilot.validate_prepare_receipt(extra)
        tampered = deepcopy(self.receipt)
        tampered["rows"][0]["sampled_option_type"] = 999
        with self.assertRaises(ValueError):
            pilot.validate_prepare_receipt(tampered)
        family = deepcopy(self.receipt)
        family["action_families"]["row_map_sha256"] = "A" * 64
        core = dict(family)
        core.pop("receipt_sha256")
        family["receipt_sha256"] = pilot.canonical_sha256(core)
        with self.assertRaises(ValueError):
            pilot.validate_prepare_receipt(family)

    def test_nested_provenance_tampering_fails_after_outer_self_rehash(self) -> None:
        def rehash(value: dict) -> dict:
            core = dict(value)
            core.pop("receipt_sha256", None)
            value["receipt_sha256"] = pilot.canonical_sha256(core)
            return value

        mutations = {
            "parent_rejection": lambda row: row["parent_rejection"].update(
                {"decision": "ACCEPT"}
            ),
            "input_checkpoint_path": lambda row: row["immutable_inputs"].update(
                {"input_checkpoint_path": pilot.REJECTED_CHECKPOINT_RELATIVE_PATH.as_posix()}
            ),
            "input_checkpoint_hash": lambda row: row["immutable_inputs"].update(
                {"input_checkpoint_sha256": "0" * 64}
            ),
            "manifest": lambda row: row["immutable_inputs"].update(
                {"manifest_sha256": "1" * 64}
            ),
            "dataset": lambda row: row["immutable_inputs"].update(
                {"dataset_sha256": "2" * 64}
            ),
            "runtime": lambda row: row["runtime_thread_receipt"][
                "observed_thread_counts"
            ].update({"torch_num_threads": 2}),
            "source_snapshot": lambda row: row["source_implementation"].update(
                {"sha256": "3" * 64}
            ),
            "candidate_snapshot": lambda row: row["implementation"].update(
                {"sha256": "4" * 64}
            ),
            "directional_contract": lambda row: row["directional_gate_contract"][
                "negative_targets"
            ].update({"final_end_probability_delta_maximum": -0.5}),
            "global_contract": lambda row: row["global_gate_contract"][
                "apply_after_each_stage"
            ].update({"mean_anchor_kl_maximum": 0.5}),
            "correction": lambda row: row["plan_correction"]["corrections"][
                "anchor_kl_coefficient"
            ].update({"stage_1": 0.5}),
            "remediation": lambda row: row["prepare_audit_remediation"].update(
                {"file_sha256": "5" * 64}
            ),
            "remediation_correction": lambda row: row[
                "prepare_audit_remediation_correction"
            ]["corrections"]["owned_hardlink_handoff"].update(
                {"single_checkpoint": False}
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                candidate = deepcopy(self.receipt)
                mutate(candidate)
                rehash(candidate)
                with self.assertRaises(ValueError):
                    pilot.validate_prepare_receipt(candidate)

    def test_rejected_checkpoint_input_tampering_fails_before_optimizer(self) -> None:
        plan = pilot._load_plan()
        plan["immutable_inputs"]["input_checkpoint"] = {
            "path": pilot.REJECTED_CHECKPOINT_RELATIVE_PATH.as_posix(),
            "sha256": pilot.REJECTED_CHECKPOINT_SHA256,
            "optimizer_state_must_be_none": True,
        }
        with (
            mock.patch.object(pilot, "_load_plan", return_value=plan),
            mock.patch.object(torch.optim, "Adam", side_effect=AssertionError("optimizer constructed")),
        ):
            with self.assertRaisesRegex(ValueError, "input checkpoint plan fields"):
                pilot._build_prepare_receipt(self.runtime)

    def test_real_prepare_constructs_no_optimizer_and_writes_no_checkpoint(self) -> None:
        candidate = pilot._repo_path(pilot.IMPLEMENTATION_RELATIVE_PATH)
        test_root = candidate / "test_outputs"
        test_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=pilot.PREPARE_OUTPUT_DIRECTORY_PREFIX + "_unit_", dir=test_root
        ) as temporary:
            receipt_path = Path(temporary) / pilot.PREPARE_OUTPUT_FILENAME
            with (
                mock.patch.object(
                    pilot.inherited, "_runtime_identity", return_value=self.runtime
                ),
                mock.patch.object(torch.optim, "Adam", side_effect=AssertionError("optimizer constructed")),
                mock.patch.object(
                    pilot.inherited,
                    "_publish_checkpoint_exclusive",
                    side_effect=AssertionError("checkpoint publication attempted"),
                ),
            ):
                report = pilot.prepare(output_receipt=receipt_path)
            self.assertFalse(report["optimizer_constructed"])
            self.assertFalse(report["checkpoint_written"])
            self.assertTrue(receipt_path.is_file())
            self.assertEqual(list(Path(temporary).glob("*.pt")), [])
            stored = json.loads(receipt_path.read_text(encoding="utf-8"))
            pilot.validate_prepare_receipt(stored)
            with self.assertRaises(FileExistsError):
                pilot.prepare(output_receipt=receipt_path)

    def test_prepare_rejects_outside_and_alias_paths_before_core(self) -> None:
        outside = pilot._repo_path(pilot.IMPLEMENTATION_RELATIVE_PATH) / "outside.json"
        with mock.patch.object(
            pilot, "_build_prepare_receipt", side_effect=AssertionError("core called")
        ):
            with self.assertRaises(ValueError):
                pilot.prepare(output_receipt=outside)
            with self.assertRaises(ValueError):
                pilot.prepare(output_receipt=Path("..") / pilot.PREPARE_OUTPUT_FILENAME)

    def test_execution_spec_exact_schema_hash_and_output_collision(self) -> None:
        spec = {
            "schema_version": pilot.EXECUTION_SPEC_SCHEMA_VERSION,
            "plan_path": pilot.PLAN_RELATIVE_PATH.as_posix(),
            "plan_sha256": pilot.PLAN_SHA256,
            "correction_path": pilot.CORRECTION_RELATIVE_PATH.as_posix(),
            "correction_sha256": pilot.CORRECTION_SHA256,
            "remediation_path": pilot.REMEDIATION_RELATIVE_PATH.as_posix(),
            "remediation_sha256": pilot.REMEDIATION_SHA256,
            "remediation_correction_path": (
                pilot.REMEDIATION_CORRECTION_RELATIVE_PATH.as_posix()
            ),
            "remediation_correction_sha256": pilot.REMEDIATION_CORRECTION_SHA256,
            "prepare_receipt_path": "fixture.json",
            "prepare_receipt_file_sha256": "A" * 64,
            "prepare_receipt_sha256": "B" * 64,
            "implementation_snapshot_sha256": self.receipt["implementation"]["sha256"],
            "input_checkpoint_path": pilot.INPUT_CHECKPOINT_RELATIVE_PATH.as_posix(),
            "input_checkpoint_sha256": pilot.INPUT_CHECKPOINT_SHA256,
            "rejected_checkpoint_sha256": pilot.REJECTED_CHECKPOINT_SHA256,
            "manifest_path": pilot.MANIFEST_RELATIVE_PATH.as_posix(),
            "manifest_sha256": pilot.MANIFEST_SHA256,
            "dataset_sha256": pilot.DATASET_SHA256,
            "runtime_thread_receipt": self.runtime,
            "training_contract": self.receipt["training_contract"],
            "output_directory": pilot.APPROVED_OUTPUT_RELATIVE_PATH.as_posix(),
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "execution.json"
            payload = pilot.canonical_json_bytes(spec, newline=True)
            path.write_bytes(payload)
            digest = pilot.hashlib.sha256(payload).hexdigest().upper()
            self.assertEqual(pilot._load_execution_spec(path, digest), spec)
            with self.assertRaises(ValueError):
                pilot._load_execution_spec(path, "0" * 64)
            extra = dict(spec)
            extra["unexpected"] = True
            extra_path = Path(temporary) / "extra.json"
            extra_payload = pilot.canonical_json_bytes(extra, newline=True)
            extra_path.write_bytes(extra_payload)
            with self.assertRaises(ValueError):
                pilot._load_execution_spec(
                    extra_path, pilot.hashlib.sha256(extra_payload).hexdigest().upper()
                )
        analysis_root = pilot.find_repo_root() / "analysis_outputs"
        with tempfile.TemporaryDirectory(prefix="iteration006-collision-", dir=analysis_root) as existing:
            relative = Path(existing).relative_to(pilot.find_repo_root()).as_posix()
            with mock.patch.object(pilot, "APPROVED_OUTPUT_RELATIVE_PATH", pilot.PurePosixPath(relative)):
                with self.assertRaises(FileExistsError):
                    pilot._validate_execution_output(
                        relative,
                        receipt_path=pilot._repo_path(pilot.V4_PROBE_RELATIVE_PATH),
                        execution_spec_path=pilot._repo_path(pilot.PARENT_EXECUTION_SPEC_RELATIVE_PATH),
                    )


if __name__ == "__main__":
    unittest.main()
