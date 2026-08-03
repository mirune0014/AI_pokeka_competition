from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path, PurePosixPath
import json
import math
import os
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import torch

from archaludon_rl import conservative_ppo_pilot as pilot
from archaludon_rl.deployment_audit import (
    AUDIT_DIRECTORY_ENVIRONMENT,
    DeploymentAudit,
    _reset_process_registry_for_tests,
    load_and_validate_deployment_audit,
    validate_deployment_audit_rows,
)
from archaludon_rl.model import ResidualActorCritic, checkpoint_metadata, save_checkpoint
from archaludon_rl.reference_policy import ReferencePolicy


RUNTIME_FIXTURE = {
    "requested_thread_counts": {
        "torch_num_threads": 1,
        "torch_num_interop_threads": 1,
    },
    "observed_thread_counts": {
        "torch_num_threads": 1,
        "torch_num_interop_threads": 1,
    },
    "required_environment": {
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
    },
    "python": {"implementation": "CPython", "version": "fixture"},
    "torch_version": "2.11.0+cu128",
    "platform": "fixture",
}


def _replace_directory_with_alias(original: Path, target: Path) -> tuple[Path, str]:
    backup = original.with_name(original.name + "-original")
    original.rename(backup)
    try:
        original.symlink_to(target, target_is_directory=True)
        return backup, "symlink"
    except OSError:
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(original), str(target)],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0:
            return backup, "junction"
        backup.rename(original)
        raise AssertionError(
            "could not create deterministic directory alias: "
            + completed.stdout
            + completed.stderr
        )


def _restore_aliased_directory(
    original: Path, backup: Path, alias_kind: str
) -> None:
    if alias_kind == "symlink":
        original.unlink()
    else:
        os.rmdir(original)
    backup.rename(original)


def _rehash_receipt(receipt: dict) -> dict:
    core = deepcopy(receipt)
    core.pop("receipt_sha256", None)
    return {**core, "receipt_sha256": pilot.canonical_sha256(core)}


def _passing_metrics(probe: dict) -> list[dict]:
    metrics = []
    for row in probe["rows"]:
        metrics.append(
            {
                "ppo_row_ordinal": row["ppo_row_ordinal"],
                "public_state_sha256": row["public_state_sha256"],
                "behavior_action_order_sha256": row[
                    "behavior_action_order_sha256"
                ],
                "post_update_probabilities_float32": list(
                    row["pre_update_probabilities_float32"]
                ),
                "anchor_kl_post_to_zero": 0.0,
                "total_variation_post_to_pre": 0.0,
            }
        )
    for ordinal in probe["probe_memberships"]["negative_target_ordinals"]:
        row = probe["rows"][ordinal]
        probabilities = metrics[ordinal]["post_update_probabilities_float32"]
        probabilities[row["end_index"]] -= 2e-6
        probabilities[row["teacher_index"]] += 2e-6
    for ordinal in probe["probe_memberships"][
        "positive_normalized_advantage_sampled_end_ordinals"
    ]:
        row = probe["rows"][ordinal]
        probabilities = metrics[ordinal]["post_update_probabilities_float32"]
        end_index = row["end_index"]
        donor = next(index for index in range(len(probabilities)) if index != end_index)
        probabilities[end_index] += 2e-6
        probabilities[donor] -= 2e-6
    return metrics


def _decision(
    *,
    protected: bool = False,
    failure_kind: str | None = None,
    action: tuple[int, ...] = (0,),
    teacher_action: tuple[int, ...] = (0,),
) -> SimpleNamespace:
    fallback = protected or failure_kind is not None
    return SimpleNamespace(
        action=action,
        teacher_action=teacher_action,
        neural_shadow_action=(1,),
        ppo_eligible=False,
        fallback_used=fallback,
        fallback_reason="fixture" if fallback else None,
        guard=SimpleNamespace(
            protected_fallback=SimpleNamespace(hard=protected or fallback)
        ),
        residuals=() if failure_kind else (0.0, 0.0),
        checkpoint_sha256="A" * 64,
        collection_mode="deployment",
        sampled_stochastically=False,
        model_failure_kind=failure_kind,
        model_timeout=failure_kind == "TimeoutError",
        legal_option_count=2,
        behavior_schema_sha256="B" * 64,
        teacher_call_count=1,
    )


class _TinyModel(torch.nn.Module):
    def __init__(self, *, nonfinite_value: bool = False) -> None:
        super().__init__()
        self.residual_scale = torch.nn.Parameter(torch.tensor(0.0))
        self.value_bias = torch.nn.Parameter(torch.tensor(0.0))
        self.nonfinite_value = nonfinite_value
        self.observed_states: list[float] = []

    def forward(self, state, actions):
        self.observed_states.append(float(state.flatten()[0]))
        residuals = self.residual_scale * actions[:, 0]
        value = self.value_bias
        if self.nonfinite_value:
            value = value * torch.tensor(float("nan"))
        return residuals, value


def _tiny_loaded(*, nonfinite_value: bool = False) -> dict:
    model = _TinyModel(nonfinite_value=nonfinite_value)
    reference = ReferencePolicy()
    base = reference.distribution(2, 0, (0.0, 0.0)).probabilities
    row0 = {
        "decision_index": 0,
        "ppo_eligible": True,
        "reward": 0.0,
        "value": 0.0,
        "state_vector": [1.0],
        "action_vectors": [[1.0], [0.0]],
        "teacher_action": [0],
        "final_action": [0],
        "behavior_logprob": math.log(base[0]),
    }
    row1 = {
        "decision_index": 1,
        "ppo_eligible": True,
        "reward": 1.0,
        "value": 0.0,
        "state_vector": [2.0],
        "action_vectors": [[0.0], [1.0]],
        "teacher_action": [0],
        "final_action": [1],
        "behavior_logprob": math.log(base[1]),
    }
    episode = {"episode_id": "fixture", "decisions": [row0, row1]}
    return {
        "model": model,
        "rows": [(episode, row0), (episode, row1)],
        "dataset": SimpleNamespace(episodes=(episode,)),
        "reference_config": reference.config,
    }


class ConservativePPOProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe = pilot._build_probe_receipt(RUNTIME_FIXTURE)
        cls.loaded = pilot._load_validated_inputs()

    def test_real_probe_binds_both_advantage_domains(self):
        domains = self.probe["advantage_domains"]
        self.assertEqual(
            domains["independent_float64"],
            {
                "mean": 0.242822610287225,
                "population_sd": 0.4569847026613282,
            },
        )
        self.assertEqual(
            domains["trainer_float32"],
            {
                "mean": 0.24282261729240417,
                "population_sd": 0.4569846987724304,
            },
        )

    def test_explicit_targets_are_four_not_naive_seventeen(self):
        memberships = self.probe["probe_memberships"]
        self.assertEqual(
            memberships["negative_target_ordinals"], [158, 260, 547, 812]
        )
        self.assertEqual(
            len(memberships["naive_teacher_not_end_sampled_end_ordinals"]), 17
        )

    def test_legitimate_end_membership_is_43_41_31_20(self):
        memberships = self.probe["probe_memberships"]
        self.assertEqual(len(memberships["teacher_end_ordinals"]), 43)
        self.assertEqual(
            len(memberships["teacher_end_and_sampled_end_ordinals"]), 41
        )
        self.assertEqual(
            len(memberships["positive_raw_advantage_sampled_end_ordinals"]), 31
        )
        self.assertEqual(
            len(
                memberships[
                    "positive_normalized_advantage_sampled_end_ordinals"
                ]
            ),
            20,
        )

    def test_positive_teacher_end_sampled_non_end_clarification(self):
        rows = [
            row
            for row in self.probe["rows"]
            if row["raw_observation_sha256"]
            == "e6c6536440effe5f49105110a3aaff38772582dc1dc701ec4e5ba940b5e21a76"
        ]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertTrue(row["teacher_is_end"])
        self.assertFalse(row["sampled_is_end"])
        self.assertGreater(row["raw_advantage"], 0.0)
        self.assertGreater(row["trainer_normalized_advantage_float32"], 0.0)

    def test_state_action_semantic_and_public_hashes_are_bound(self):
        episode, source = self.loaded["rows"][158]
        probe = self.probe["rows"][158]
        self.assertEqual(
            probe["state_vector_sha256"],
            pilot.canonical_sha256(source["state_vector"]),
        )
        self.assertEqual(
            probe["action_vectors_sha256"],
            pilot.canonical_sha256(source["action_vectors"]),
        )
        self.assertEqual(
            probe["behavior_action_order_sha256"],
            source["behavior_action_order_sha256"],
        )
        self.assertEqual(probe["episode_id"], episode["episode_id"])
        self.assertEqual(
            probe["public_state_sha256"],
            "5ad8ab5e5b859cc25d031688aed228497471dced9fb0a6fbd93274c3f07cc16f",
        )

    def test_duplicate_decision_key_rejected_even_with_refreshed_self_hash(self):
        tampered = deepcopy(self.probe)
        tampered["rows"][-1]["episode_id"] = tampered["rows"][0]["episode_id"]
        tampered["rows"][-1]["decision_index"] = tampered["rows"][0][
            "decision_index"
        ]
        tampered = _rehash_receipt(tampered)
        with self.assertRaisesRegex(ValueError, "duplicate decision keys"):
            pilot.validate_prepare_receipt(tampered)

    def test_missing_extra_reordered_modified_rows_and_probes_rejected(self):
        mutations = []
        missing = deepcopy(self.probe)
        missing["rows"].pop()
        mutations.append(missing)
        extra = deepcopy(self.probe)
        extra["rows"].append(deepcopy(extra["rows"][-1]))
        mutations.append(extra)
        reordered = deepcopy(self.probe)
        reordered["rows"][0], reordered["rows"][1] = (
            reordered["rows"][1],
            reordered["rows"][0],
        )
        mutations.append(reordered)
        modified = deepcopy(self.probe)
        modified["rows"][0]["raw_advantage"] += 1e-9
        mutations.append(modified)
        probe_modified = deepcopy(self.probe)
        probe_modified["probe_memberships"]["negative_target_ordinals"] = [158]
        mutations.append(probe_modified)
        for mutation in mutations:
            with self.subTest(kind=len(mutation.get("rows", []))):
                with self.assertRaisesRegex(ValueError, "changed after prepare"):
                    pilot.require_exact_probe_match(self.probe, mutation)

    def test_input_checkpoint_manifest_and_raw_episode_are_unchanged(self):
        self.assertEqual(
            pilot.sha256_file(pilot._repo_path(pilot.INPUT_CHECKPOINT_RELATIVE_PATH)),
            pilot.INPUT_CHECKPOINT_SHA256,
        )
        self.assertEqual(
            pilot.sha256_file(pilot._repo_path(pilot.MANIFEST_RELATIVE_PATH)),
            pilot.MANIFEST_SHA256,
        )
        first_receipt = self.loaded["dataset"].manifest["episode_receipts"][0]
        episode_path = pilot._repo_path(pilot.MANIFEST_RELATIVE_PATH).parent / first_receipt[
            "path"
        ]
        self.assertEqual(pilot.sha256_file(episode_path), first_receipt["sha256"])

    def test_prepare_constructs_no_optimizer_and_writes_no_checkpoint(self):
        candidate_root = Path(__file__).resolve().parents[1]
        excluded_root = candidate_root / "test_outputs"
        excluded_root.mkdir(exist_ok=True)
        script = r'''
import json
from pathlib import Path
import sys
import torch
from archaludon_rl import conservative_ppo_pilot as pilot

output = Path(sys.argv[1])
real_load = pilot.load_checkpoint
captured = {}
def audited_load(*args, **kwargs):
    model, metadata, optimizer_state = real_load(*args, **kwargs)
    captured["model"] = model
    captured["before"] = {
        name: value.detach().clone()
        for name, value in model.state_dict().items()
    }
    return model, metadata, optimizer_state
def forbidden(*args, **kwargs):
    raise AssertionError("prepare attempted optimizer/checkpoint publication")
pilot.load_checkpoint = audited_load
pilot.torch.optim.Adam = forbidden
pilot.save_checkpoint = forbidden
pilot._publish_checkpoint_exclusive = forbidden
report = pilot.prepare(output_receipt=output)
after = captured["model"].state_dict()
assert all(torch.equal(value, after[name]) for name, value in captured["before"].items())
assert not list(output.parent.rglob("*.pt"))
print(json.dumps(report, sort_keys=True))
'''
        with tempfile.TemporaryDirectory(
            dir=excluded_root, prefix="phase1_iteration_005_prepare_real_fixture_"
        ) as temporary:
            output = Path(temporary) / "pretraining_probe_receipt.json"
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(candidate_root)
            environment.update(
                {
                    "OMP_NUM_THREADS": "1",
                    "MKL_NUM_THREADS": "1",
                    "OPENBLAS_NUM_THREADS": "1",
                    "NUMEXPR_NUM_THREADS": "1",
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
            )
            completed = subprocess.run(
                [sys.executable, "-B", "-c", script, str(output)],
                cwd=candidate_root,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(
                completed.returncode, 0, completed.stdout + completed.stderr
            )
            report = json.loads(completed.stdout.strip().splitlines()[-1])
            self.assertFalse(report["optimizer_constructed"])
            self.assertFalse(report["checkpoint_written"])
            self.assertEqual(report["row_count"], 830)
            self.assertTrue(output.is_file())
            self.assertFalse(list(Path(temporary).rglob("*.pt")))

    def test_prepare_and_checkpoint_output_collisions_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "exists.json"
            original = b"keep"
            output.write_bytes(original)
            with self.assertRaises(FileExistsError):
                pilot._write_new_canonical_json(output, {"value": 1})
            self.assertEqual(output.read_bytes(), original)

    def test_prepare_path_is_exclusively_confined_to_isolated_test_outputs(self):
        candidate_root = Path(__file__).resolve().parents[1]
        excluded_root = candidate_root / "test_outputs"
        excluded_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=excluded_root,
            prefix=pilot.PREPARE_OUTPUT_DIRECTORY_PREFIX + "_path_fixture_",
        ) as temporary:
            allowed = Path(temporary) / pilot.PREPARE_OUTPUT_FILENAME
            self.assertEqual(
                pilot._validate_prepare_output_path(allowed), allowed.resolve()
            )
            repo = pilot.find_repo_root()
            forbidden = (
                candidate_root / "archaludon_rl" / pilot.PREPARE_OUTPUT_FILENAME,
                candidate_root / "specs" / pilot.PREPARE_OUTPUT_FILENAME,
                pilot._repo_path(pilot.PLAN_RELATIVE_PATH),
                pilot._repo_path(pilot.MANIFEST_RELATIVE_PATH),
                pilot._repo_path(pilot.INPUT_CHECKPOINT_RELATIVE_PATH),
                repo
                / "research" / "experiments"
                / "archaludon_latest_v1_rl_temperature_candidate_20260731"
                / pilot.PREPARE_OUTPUT_FILENAME,
            )
            for path in forbidden:
                with self.subTest(path=path):
                    with self.assertRaisesRegex(ValueError, "isolated test_outputs"):
                        pilot._validate_prepare_output_path(path)

            alias = Path(temporary) / "source-alias"
            try:
                alias.symlink_to(candidate_root / "archaludon_rl", target_is_directory=True)
            except OSError:
                alias = None
            if alias is not None:
                with self.assertRaisesRegex(
                    ValueError, "isolated test_outputs|symlink|reparse"
                ):
                    pilot._validate_prepare_output_path(
                        alias / pilot.PREPARE_OUTPUT_FILENAME
                    )

            original = b"concurrent"
            real_open = pilot._win_open_handle

            def collide(path, **kwargs):
                if (
                    Path(path).absolute() == allowed.absolute()
                    and kwargs["creation_disposition"] == pilot._CREATE_NEW
                ):
                    Path(path).write_bytes(original)
                return real_open(path, **kwargs)

            with mock.patch.object(
                pilot, "_win_open_handle", side_effect=collide
            ):
                with self.assertRaises(FileExistsError):
                    pilot._write_new_canonical_json(allowed, {"value": 1})
            self.assertEqual(allowed.read_bytes(), original)

    def test_nonempty_input_optimizer_state_is_rejected(self):
        for value in ({}, {"state": {}}, {"state": {1: {"step": 1}}}):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "must be None"):
                    pilot.require_empty_input_optimizer_state(value)
        pilot.require_empty_input_optimizer_state(None)

    def test_prepare_parent_swap_fails_closed_without_outside_artifact(self):
        candidate_root = Path(__file__).resolve().parents[1]
        excluded_root = candidate_root / "test_outputs"
        excluded_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=excluded_root,
            prefix=pilot.PREPARE_OUTPUT_DIRECTORY_PREFIX + "_swap_fixture_",
        ) as protected_text, tempfile.TemporaryDirectory() as outside_text:
            protected = Path(protected_text)
            outside = Path(outside_text)
            receipt = protected / pilot.PREPARE_OUTPUT_FILENAME
            self.assertEqual(
                pilot._validate_prepare_output_path(receipt), receipt.resolve()
            )
            backup, alias_kind = _replace_directory_with_alias(protected, outside)
            try:
                with self.assertRaisesRegex(ValueError, "reparse|alias|publication"):
                    pilot._write_new_canonical_json(receipt, {"fixture": True})
                self.assertFalse((outside / pilot.PREPARE_OUTPUT_FILENAME).exists())
            finally:
                _restore_aliased_directory(protected, backup, alias_kind)

    def test_prepare_holds_same_parent_guard_through_probe_and_receipt_create(self):
        candidate_root = Path(__file__).resolve().parents[1]
        excluded_root = candidate_root / "test_outputs"
        excluded_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=excluded_root,
            prefix=pilot.PREPARE_OUTPUT_DIRECTORY_PREFIX + "_held_probe_fixture_",
        ) as protected_text, tempfile.TemporaryDirectory() as outside_text:
            protected = Path(protected_text)
            outside = Path(outside_text)
            receipt = protected / pilot.PREPARE_OUTPUT_FILENAME
            backup = protected.with_name(protected.name + "-renamed")
            attempted = {"probe": False}

            def adversarial_probe(_runtime):
                attempted["probe"] = True
                with self.assertRaises(OSError):
                    protected.rename(backup)
                with self.assertRaises(OSError):
                    protected.symlink_to(outside, target_is_directory=True)
                self.assertFalse(backup.exists())
                return self.probe

            with (
                mock.patch.object(
                    pilot, "_runtime_identity", return_value=RUNTIME_FIXTURE
                ),
                mock.patch.object(
                    pilot, "_build_probe_receipt", side_effect=adversarial_probe
                ),
            ):
                report = pilot.prepare(output_receipt=receipt)
            self.assertTrue(attempted["probe"])
            self.assertEqual(report["receipt_path"], str(receipt.absolute()))
            self.assertTrue(receipt.is_file())
            self.assertEqual(list(outside.iterdir()), [])

    def test_non_windows_publication_fails_closed_before_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "receipt.json"
            with mock.patch.object(pilot.os, "name", "posix"):
                with self.assertRaisesRegex(RuntimeError, "Windows handle-based"):
                    pilot._write_new_canonical_json(output, {"fixture": True})
            self.assertFalse(output.exists())

    def test_all_ppo_and_adam_fields_are_explicit_and_recorded(self):
        plan = pilot._load_plan()["training_contract"]
        self.assertEqual(self.probe["training_contract"]["ppo_config"], plan["ppo_config"])
        self.assertEqual(self.probe["training_contract"]["adam"], plan["optimizer"])
        self.assertEqual(set(self.probe["training_contract"]["ppo_config"]), {
            "gamma", "gae_lambda", "clip_ratio", "value_coef", "entropy_coef",
            "anchor_kl_target", "anchor_kl_initial_coef", "anchor_kl_hard_stop",
            "gradient_clip", "learning_rate", "epochs",
        })
        self.assertEqual(set(self.probe["training_contract"]["adam"]), {
            "name", "fresh_state", "betas", "eps", "weight_decay", "amsgrad",
            "foreach", "maximize", "capturable", "differentiable", "fused",
            "decoupled_weight_decay",
        })

    def test_corrected_provenance_is_strict_and_bound_in_probe(self):
        plan, provenance = pilot._load_corrected_plan()
        self.assertEqual(
            plan["immutable_inputs"]["source_implementation"][
                "snapshot_sha256"
            ],
            pilot.CORRECTED_SOURCE_SNAPSHOT_SHA256,
        )
        self.assertEqual(self.probe["plan"], provenance)
        source_receipt = self.probe["source_implementation_input"]
        self.assertEqual(
            source_receipt["snapshot_sha256"],
            pilot.CORRECTED_SOURCE_SNAPSHOT_SHA256,
        )
        self.assertEqual(
            source_receipt["snapshot_definition"],
            pilot.STRICT_IMPLEMENTATION_SNAPSHOT_DEFINITION,
        )
        self.assertEqual(source_receipt["snapshot_file_count"], 46)
        self.assertEqual(
            source_receipt["superseded_windows_order_snapshot_sha256"],
            pilot.SUPERSEDED_SOURCE_SNAPSHOT_SHA256,
        )

        correction = pilot._load_correction()
        for mutation in (
            {**correction, "extra": True},
            {key: value for key, value in correction.items() if key != "invariants"},
            {
                **correction,
                "source_implementation_snapshot": {
                    **correction["source_implementation_snapshot"],
                    "corrected_sha256": "0" * 64,
                },
            },
        ):
            with self.subTest(keys=set(mutation)):
                with self.assertRaisesRegex(
                    ValueError, "missing, extra, or mismatched"
                ):
                    pilot._validate_correction_spec(mutation)
        base = pilot._load_plan()
        with self.assertRaisesRegex(ValueError, "missing or extra keys"):
            pilot._validate_base_plan({**base, "extra": True})
        changed = deepcopy(base)
        changed["purpose"] += " changed"
        with self.assertRaisesRegex(ValueError, "content mismatch"):
            pilot._validate_base_plan(changed)

    def test_snapshot_uses_unsigned_utf8_path_order_and_one_buffer_sizes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payloads = {
                "a.txt": b"lower",
                "Z.txt": b"upper",
                "b.txt": b"last",
            }
            for name, payload in payloads.items():
                (root / name).write_bytes(payload)
            with mock.patch.object(
                pilot,
                "sha256_file",
                side_effect=AssertionError("snapshot must hash its read buffer"),
            ):
                snapshot = pilot.implementation_snapshot(root)
            ordered = sorted(payloads, key=lambda name: name.encode("utf-8"))
            self.assertEqual([row["path"] for row in snapshot["files"]], ordered)
            preimage = b"".join(
                name.encode("utf-8")
                + b"\0"
                + str(len(payloads[name])).encode("ascii")
                + b"\0"
                + hashlib.sha256(payloads[name])
                .hexdigest()
                .upper()
                .encode("ascii")
                + b"\n"
                for name in ordered
            )
            self.assertEqual(
                snapshot["sha256"], hashlib.sha256(preimage).hexdigest().upper()
            )
            self.assertEqual(
                snapshot["definition"],
                pilot.STRICT_IMPLEMENTATION_SNAPSHOT_DEFINITION,
            )

            link = root / "link.txt"
            try:
                link.symlink_to(root / "a.txt")
            except OSError:
                link = None
            if link is not None:
                with self.assertRaisesRegex(ValueError, "symlink|reparse"):
                    pilot.implementation_snapshot(root)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "stable.txt").write_bytes(b"stable")
            real_inventory = pilot._snapshot_inventory
            calls = 0

            def add_file_after_first_inventory(candidate):
                nonlocal calls
                result = real_inventory(candidate)
                calls += 1
                if calls == 1:
                    (candidate / "concurrent.txt").write_bytes(b"new")
                return result

            with mock.patch.object(
                pilot,
                "_snapshot_inventory",
                side_effect=add_file_after_first_inventory,
            ):
                with self.assertRaisesRegex(ValueError, "changed during snapshot"):
                    pilot.implementation_snapshot(root)

    def test_unique_argmax_rejects_ties(self):
        with self.assertRaisesRegex(ValueError, "no unique argmax"):
            pilot._unique_argmax([0.5, 0.5])
        self.assertEqual(pilot._unique_argmax([0.5, 0.5000001]), 1)

    def test_kl_direction_is_post_to_zero(self):
        post = [0.8, 0.2]
        zero = [0.6, 0.4]
        expected = sum(p * math.log(p / q) for p, q in zip(post, zero))
        reverse = sum(q * math.log(q / p) for p, q in zip(post, zero))
        measured = pilot.per_row_anchor_kl(post, zero)
        self.assertAlmostEqual(measured, expected)
        self.assertNotAlmostEqual(measured, reverse)

    def test_total_variation_has_one_half_factor(self):
        self.assertAlmostEqual(
            pilot.per_row_total_variation([0.75, 0.25], [0.5, 0.5]), 0.25
        )


class ConservativePPOGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe = pilot._build_probe_receipt(RUNTIME_FIXTURE)

    def _evaluate(self, metrics, **overrides):
        kwargs = {
            "optimizer_steps": 1,
            "nonfinite_count": 0,
            "stopped_early": False,
            "rolled_back": False,
        }
        kwargs.update(overrides)
        return pilot.evaluate_post_update_gates(self.probe, metrics, **kwargs)

    def test_passing_fixture_exercises_every_gate(self):
        report = self._evaluate(_passing_metrics(self.probe))
        self.assertTrue(report["accepted"], report["failures"])
        self.assertEqual(
            (
                report["negative_target_count"],
                report["teacher_end_count"],
                report["positive_raw_sampled_end_count"],
                report["positive_normalized_sampled_end_count"],
            ),
            (4, 43, 31, 20),
        )

    def test_negative_targets_reject_reversed_and_insufficient_movement(self):
        for delta in (-2e-6, 0.5e-6):
            metrics = _passing_metrics(self.probe)
            ordinal = self.probe["probe_memberships"]["negative_target_ordinals"][0]
            row = self.probe["rows"][ordinal]
            probabilities = list(row["pre_update_probabilities_float32"])
            probabilities[row["end_index"]] -= delta
            probabilities[row["teacher_index"]] += delta
            metrics[ordinal]["post_update_probabilities_float32"] = probabilities
            with self.subTest(delta=delta):
                report = self._evaluate(metrics)
                self.assertFalse(report["accepted"])
                self.assertTrue(
                    any(item.startswith(f"negative:{ordinal}:") for item in report["failures"])
                )

    def test_negative_target_identity_and_action_order_are_immutable(self):
        metrics = _passing_metrics(self.probe)
        ordinal = self.probe["probe_memberships"]["negative_target_ordinals"][0]
        metrics[ordinal]["public_state_sha256"] = "0" * 64
        metrics[ordinal]["behavior_action_order_sha256"] = "1" * 64
        report = self._evaluate(metrics)
        self.assertIn(
            f"negative:{ordinal}:identity_or_action_order", report["failures"]
        )

    def test_all_43_teacher_end_unique_argmax_controls_are_enforced(self):
        metrics = _passing_metrics(self.probe)
        ordinal = self.probe["probe_memberships"]["teacher_end_ordinals"][0]
        probabilities = metrics[ordinal]["post_update_probabilities_float32"]
        end_index = self.probe["rows"][ordinal]["end_index"]
        other = next(index for index in range(len(probabilities)) if index != end_index)
        probabilities[other] = probabilities[end_index]
        report = self._evaluate(metrics)
        self.assertIn(
            f"legitimate_end:{ordinal}:unique_argmax", report["failures"]
        )

    def test_positive_normalized_end_each_requires_minimum_increase(self):
        metrics = _passing_metrics(self.probe)
        ordinal = self.probe["probe_memberships"][
            "positive_normalized_advantage_sampled_end_ordinals"
        ][0]
        metrics[ordinal]["post_update_probabilities_float32"] = list(
            self.probe["rows"][ordinal]["pre_update_probabilities_float32"]
        )
        report = self._evaluate(metrics)
        self.assertIn(
            f"legitimate_end:{ordinal}:normalized_increase", report["failures"]
        )

    def test_positive_raw_end_median_and_individual_decrease_gates(self):
        ordinals = self.probe["probe_memberships"][
            "positive_raw_advantage_sampled_end_ordinals"
        ]
        metrics = _passing_metrics(self.probe)
        for ordinal in ordinals[:16]:
            end_index = self.probe["rows"][ordinal]["end_index"]
            metrics[ordinal]["post_update_probabilities_float32"][end_index] = (
                self.probe["rows"][ordinal]["pre_update_probabilities_float32"][
                    end_index
                ]
                - 1e-6
            )
        self.assertIn(
            "legitimate_end:positive_raw_median", self._evaluate(metrics)["failures"]
        )
        metrics = _passing_metrics(self.probe)
        ordinal = next(
            item
            for item in ordinals
            if item
            not in self.probe["probe_memberships"][
                "positive_normalized_advantage_sampled_end_ordinals"
            ]
        )
        end_index = self.probe["rows"][ordinal]["end_index"]
        metrics[ordinal]["post_update_probabilities_float32"][end_index] -= 0.0025001
        self.assertIn(
            "legitimate_end:positive_raw_maximum_decrease",
            self._evaluate(metrics)["failures"],
        )

    def test_kl_and_tv_boundaries_are_inclusive_and_beyond_rejects(self):
        boundary_cases = (
            ("anchor_kl_post_to_zero", 0.01, None),
            ("total_variation_post_to_pre", 0.02, None),
        )
        for field, boundary, _ in boundary_cases:
            metrics = _passing_metrics(self.probe)
            metrics[0][field] = boundary
            self.assertTrue(self._evaluate(metrics)["accepted"], field)
            metrics[0][field] = math.nextafter(boundary, math.inf)
            self.assertFalse(self._evaluate(metrics)["accepted"], field)
        metrics = _passing_metrics(self.probe)
        for row in metrics:
            row["anchor_kl_post_to_zero"] = 0.002
        self.assertTrue(self._evaluate(metrics)["accepted"])
        for row in metrics:
            row["anchor_kl_post_to_zero"] = math.nextafter(0.002, math.inf)
        self.assertFalse(self._evaluate(metrics)["accepted"])

    def test_nonfinite_step_count_early_stop_and_rollback_reject(self):
        metrics = _passing_metrics(self.probe)
        cases = (
            {"nonfinite_count": 1},
            {"optimizer_steps": 0},
            {"optimizer_steps": 2},
            {"stopped_early": True},
            {"rolled_back": True},
        )
        for case in cases:
            with self.subTest(case=case):
                self.assertFalse(self._evaluate(metrics, **case)["accepted"])

    def test_checkpoint_provenance_must_be_post_save_pass(self):
        metrics = _passing_metrics(self.probe)
        report = pilot.evaluate_post_update_gates(
            self.probe,
            metrics,
            optimizer_steps=1,
            nonfinite_count=0,
            checkpoint_provenance_validation="deferred_until_reload",
        )
        self.assertFalse(report["accepted"])
        self.assertIn("global:checkpoint_provenance_validation", report["failures"])


class ConservativePPOStepTests(unittest.TestCase):
    def test_one_full_batch_preserves_manifest_order_and_one_fresh_step(self):
        loaded = _tiny_loaded()
        report = pilot._one_full_batch_step(loaded)
        self.assertEqual(report["optimizer_steps"], 1)
        self.assertEqual(loaded["model"].observed_states, [1.0, 2.0])
        self.assertTrue(report["changed_parameter_names"])
        state = report["optimizer"].state_dict()["state"]
        self.assertTrue(state)
        self.assertTrue(
            all(float(value["step"].detach().cpu()) == 1.0 for value in state.values())
        )

    def test_fresh_adam_has_exact_configuration_and_empty_state(self):
        model = _TinyModel()
        optimizer = pilot._new_adam(model)
        self.assertFalse(optimizer.state_dict()["state"])
        defaults = optimizer.defaults
        expected = pilot.PILOT_ADAM_CONFIG
        self.assertEqual(defaults["lr"], pilot.PILOT_PPO_CONFIG.learning_rate)
        self.assertEqual(list(defaults["betas"]), expected["betas"])
        for field in (
            "eps", "weight_decay", "amsgrad", "foreach", "maximize",
            "capturable", "differentiable", "fused", "decoupled_weight_decay",
        ):
            self.assertEqual(defaults[field], expected[field], field)

    def test_nonfinite_objective_or_value_rejects_before_step(self):
        with self.assertRaisesRegex(ValueError, "non-finite"):
            pilot._one_full_batch_step(_tiny_loaded(nonfinite_value=True))

    def test_nonfinite_gradient_norm_parameter_and_optimizer_state_reject(self):
        for label in ("gradient", "gradient norm", "parameter"):
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, "non-finite"):
                    pilot._finite_tensors_or_raise(
                        [torch.tensor(float("nan"))], label=label
                    )
        model = _TinyModel()
        optimizer = pilot._new_adam(model)
        optimizer.state[model.residual_scale]["step"] = torch.tensor(2.0)
        optimizer.state[model.residual_scale]["exp_avg"] = torch.tensor(0.0)
        optimizer.state[model.residual_scale]["exp_avg_sq"] = torch.tensor(0.0)
        with self.assertRaisesRegex(ValueError, "exactly one fresh step"):
            pilot._audit_optimizer_after_one_step(optimizer)

    def test_execution_spec_requires_external_hash_and_exact_schema(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "execution.json"
            spec = {
                "schema_version": pilot.EXECUTION_SPEC_SCHEMA_VERSION,
                "plan_path": pilot.PLAN_RELATIVE_PATH.as_posix(),
                "plan_sha256": pilot.PLAN_SHA256,
                "prepare_receipt_path": "fixture/probe.json",
                "prepare_receipt_file_sha256": "A" * 64,
                "prepare_receipt_sha256": "B" * 64,
                "implementation_snapshot_sha256": "C" * 64,
                "input_checkpoint_path": pilot.INPUT_CHECKPOINT_RELATIVE_PATH.as_posix(),
                "input_checkpoint_sha256": pilot.INPUT_CHECKPOINT_SHA256,
                "manifest_path": pilot.MANIFEST_RELATIVE_PATH.as_posix(),
                "manifest_sha256": pilot.MANIFEST_SHA256,
                "dataset_sha256": pilot.DATASET_SHA256,
                "runtime_thread_receipt": RUNTIME_FIXTURE,
                "training_contract": {},
                "output_directory": "fixture/output",
            }
            path.write_bytes(pilot.canonical_json_bytes(spec, newline=True))
            digest = pilot.sha256_file(path)
            real_open = Path.open
            reads = 0

            def counted_open(self, *args, **kwargs):
                nonlocal reads
                if self.absolute() == path.absolute():
                    reads += 1
                return real_open(self, *args, **kwargs)

            with mock.patch.object(Path, "open", new=counted_open):
                self.assertEqual(pilot._load_execution_spec(path, digest), spec)
            self.assertEqual(reads, 1)
            with self.assertRaisesRegex(ValueError, "file SHA-256 mismatch"):
                pilot._load_execution_spec(path, "0" * 64)
            spec["extra"] = True
            path.write_bytes(pilot.canonical_json_bytes(spec, newline=True))
            with self.assertRaisesRegex(ValueError, "schema mismatch"):
                pilot._load_execution_spec(path, pilot.sha256_file(path))

    def test_hashed_json_authorizers_read_once_and_detect_path_swap(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "authorization.json"
            payload = pilot.canonical_json_bytes({"authorized": True}, newline=True)
            path.write_bytes(payload)
            expected = hashlib.sha256(payload).hexdigest().upper()
            real_open = Path.open
            reads = 0

            def counted_open(self, *args, **kwargs):
                nonlocal reads
                if self.absolute() == path.absolute():
                    reads += 1
                return real_open(self, *args, **kwargs)

            with mock.patch.object(Path, "open", new=counted_open):
                self.assertEqual(
                    pilot._load_hashed_json(path, expected, label="fixture"),
                    {"authorized": True},
                )
            self.assertEqual(reads, 1)

            replacement = Path(temporary) / "replacement.json"
            replacement.write_bytes(
                pilot.canonical_json_bytes({"authorized": False}, newline=True)
            )
            real_link_check = pilot._is_link_or_reparse
            checks = 0

            def swap_after_read(candidate):
                nonlocal checks
                checks += 1
                if checks == 2:
                    path.unlink()
                    replacement.replace(path)
                return real_link_check(candidate)

            with mock.patch.object(
                pilot, "_is_link_or_reparse", side_effect=swap_after_read
            ):
                with self.assertRaisesRegex(ValueError, "changed during read"):
                    pilot._load_hashed_json(path, expected, label="fixture")

            with self.assertRaisesRegex(ValueError, "regular file"):
                pilot._load_hashed_json(
                    Path(temporary), "0" * 64, label="directory fixture"
                )
            symlink = Path(temporary) / "authorization-link.json"
            try:
                symlink.symlink_to(path)
            except OSError:
                symlink = None
            if symlink is not None:
                with self.assertRaisesRegex(ValueError, "symlink|reparse"):
                    pilot._load_hashed_json(
                        symlink,
                        pilot.sha256_file(path),
                        label="symlink fixture",
                    )

    def test_plan_spec_and_prepare_authorization_use_single_buffer_loader(self):
        real_open = Path.open
        plan_path = pilot._repo_path(pilot.PLAN_RELATIVE_PATH).absolute()
        correction_path = pilot._repo_path(pilot.CORRECTION_RELATIVE_PATH).absolute()
        plan_reads = 0
        correction_reads = 0

        def count_plan(self, *args, **kwargs):
            nonlocal plan_reads, correction_reads
            if self.absolute() == plan_path:
                plan_reads += 1
            if self.absolute() == correction_path:
                correction_reads += 1
            return real_open(self, *args, **kwargs)

        with mock.patch.object(Path, "open", new=count_plan):
            corrected, _provenance = pilot._load_corrected_plan()
            self.assertEqual(corrected["plan_id"], pilot.BASE_PLAN_ID)
        self.assertEqual(plan_reads, 1)
        self.assertEqual(correction_reads, 1)

        candidate_root = Path(__file__).resolve().parents[1]
        excluded_root = candidate_root / "test_outputs"
        excluded_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(
            dir=excluded_root,
            prefix=pilot.PREPARE_OUTPUT_DIRECTORY_PREFIX + "_read_fixture_",
        ) as temporary:
            receipt_path = Path(temporary) / pilot.PREPARE_OUTPUT_FILENAME
            snapshot = {
                "definition": "fixture",
                "file_count": 0,
                "sha256": "C" * 64,
                "files": [],
            }
            receipt = {
                "receipt_sha256": "B" * 64,
                "implementation": snapshot,
                "runtime_thread_receipt": RUNTIME_FIXTURE,
                "training_contract": {"fixture": True},
            }
            receipt_path.write_bytes(
                pilot.canonical_json_bytes(receipt, newline=True)
            )
            spec = {
                "prepare_receipt_path": str(receipt_path),
                "prepare_receipt_file_sha256": pilot.sha256_file(receipt_path),
                "prepare_receipt_sha256": receipt["receipt_sha256"],
                "implementation_snapshot_sha256": snapshot["sha256"],
                "runtime_thread_receipt": RUNTIME_FIXTURE,
                "training_contract": receipt["training_contract"],
                "output_directory": "fixture",
            }
            receipt_reads = 0

            def count_receipt(self, *args, **kwargs):
                nonlocal receipt_reads
                if self.absolute() == receipt_path.absolute():
                    receipt_reads += 1
                return real_open(self, *args, **kwargs)

            with (
                mock.patch.object(Path, "open", new=count_receipt),
                mock.patch.object(pilot, "validate_prepare_receipt"),
                mock.patch.object(pilot, "implementation_snapshot", return_value=snapshot),
                mock.patch.object(pilot, "_build_probe_receipt", return_value=receipt),
                mock.patch.object(pilot, "_protected_output_paths", return_value=()),
                mock.patch.object(
                    pilot,
                    "_validate_output_directory",
                    return_value=Path(temporary) / "output",
                ),
            ):
                loaded, _ = pilot._validate_execution_boundary(
                    spec,
                    RUNTIME_FIXTURE,
                    execution_spec_path=Path(temporary) / "execution.json",
                )
            self.assertEqual(loaded, receipt)
            self.assertEqual(receipt_reads, 1)

    def test_execution_output_is_confined_and_cannot_overlap_inputs_or_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary).resolve()
            analysis = repo  / "_local_generated" / "analysis_outputs"
            analysis.mkdir()
            approved_relative = PurePosixPath("_local_generated/analysis_outputs/approved")
            allowed = pilot._validate_output_directory(
                approved_relative.as_posix(),
                repo_root=repo,
                approved_relative=approved_relative,
                protected_paths=(),
            )
            self.assertEqual(allowed, analysis / "approved")

            for value in (
                "analysis_outputs",
                "_local_generated/analysis_outputs/not-approved",
                "_local_generated/analysis_outputs/approved/../source",
                "../analysis_outputs/approved",
            ):
                with self.subTest(value=value):
                    with self.assertRaises(ValueError):
                        pilot._validate_output_directory(
                            value,
                            repo_root=repo,
                            approved_relative=approved_relative,
                            protected_paths=(),
                        )

            approved = analysis / "approved"
            approved.mkdir()
            protected = approved / "protected"
            protected.mkdir()
            with self.assertRaisesRegex(ValueError, "overlaps"):
                pilot._validate_output_directory(
                    "_local_generated/analysis_outputs/approved/protected/run",
                    repo_root=repo,
                    approved_relative=approved_relative,
                    protected_paths=(protected,),
                )
            with self.assertRaisesRegex(ValueError, "overlaps"):
                pilot._validate_output_directory(
                    "_local_generated/analysis_outputs/approved/run",
                    repo_root=repo,
                    approved_relative=approved_relative,
                    protected_paths=(approved / "run" / "raw-episode.json",),
                )

        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary).resolve()
            analysis = repo  / "_local_generated" / "analysis_outputs"
            analysis.mkdir()
            target = repo / "immutable-source"
            target.mkdir()
            approved = analysis / "approved"
            try:
                approved.symlink_to(target, target_is_directory=True)
            except OSError:
                return
            with self.assertRaisesRegex(ValueError, "symlink|reparse|aliases"):
                pilot._validate_output_directory(
                    "_local_generated/analysis_outputs/approved/run",
                    repo_root=repo,
                    approved_relative=PurePosixPath("_local_generated/analysis_outputs/approved"),
                    protected_paths=(target,),
                )

    def test_execute_parent_swap_fails_before_output_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary).resolve()
            analysis = repo  / "_local_generated" / "analysis_outputs"
            analysis.mkdir()
            outside = repo / "outside"
            outside.mkdir()
            approved_relative = PurePosixPath("_local_generated/analysis_outputs/approved")
            output = pilot._validate_output_directory(
                approved_relative.as_posix(),
                repo_root=repo,
                approved_relative=approved_relative,
                protected_paths=(),
            )
            backup, alias_kind = _replace_directory_with_alias(analysis, outside)
            try:
                with self.assertRaisesRegex(ValueError, "reparse|alias|publication"):
                    pilot._create_and_guard_output_directory(output)
                self.assertFalse((outside / "approved").exists())
            finally:
                _restore_aliased_directory(analysis, backup, alias_kind)

    def test_output_directory_create_is_atomic_and_leaf_is_never_reopened(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "atomic-output"
            moved = root / "moved-output"
            replacement = root / "replacement"
            replacement.mkdir()
            real_open = pilot._win_open_handle

            def reject_leaf_reopen(path, **kwargs):
                if Path(path).absolute() == output.absolute():
                    raise AssertionError("atomically created leaf was reopened")
                return real_open(path, **kwargs)

            guard = None
            with (
                mock.patch.object(
                    pilot.os,
                    "mkdir",
                    side_effect=AssertionError("os.mkdir must not be used"),
                ),
                mock.patch.object(
                    pilot, "_win_open_handle", side_effect=reject_leaf_reopen
                ),
            ):
                guard = pilot._create_and_guard_output_directory(output)
                self.assertTrue(output.is_dir())
                self.assertEqual(guard.path, output.absolute())
                with self.assertRaises(OSError):
                    output.rename(moved)
                with self.assertRaises(OSError):
                    os.replace(replacement, output)
                self.assertTrue(output.is_dir())
                self.assertFalse(moved.exists())
            self.assertIsNotNone(guard)
            guard.close()

    def test_checkpoint_and_status_parent_swaps_create_nothing_outside(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "approved-output"
            output.mkdir()
            outside = root / "outside"
            outside.mkdir()
            self.assertFalse(pilot._is_link_or_reparse(output))
            backup, alias_kind = _replace_directory_with_alias(output, outside)
            try:
                with self.assertRaisesRegex(ValueError, "reparse|alias|publication"):
                    pilot._publish_checkpoint_exclusive(
                        output,
                        model=object(),
                        metadata={},
                        optimizer=object(),
                    )
                with self.assertRaisesRegex(ValueError, "reparse|alias|publication"):
                    pilot._publish_status(
                        output,
                        status="accepted",
                        receipt={"receipt_sha256": "A" * 64},
                    )
                self.assertEqual(list(outside.iterdir()), [])
            finally:
                _restore_aliased_directory(output, backup, alias_kind)

    def test_candidate_checkpoint_publication_preserves_concurrent_collision(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            concurrent = b"concurrent checkpoint"
            real_link = os.link

            def collide(source, destination):
                Path(destination).write_bytes(concurrent)
                return real_link(source, destination)

            with (
                mock.patch.object(
                    pilot,
                    "_serialize_checkpoint_payload",
                    return_value=b"private staging checkpoint",
                ),
                mock.patch.object(pilot.os, "link", side_effect=collide),
            ):
                with self.assertRaises(FileExistsError):
                    pilot._publish_checkpoint_exclusive(
                        output, model=object(), metadata={}, optimizer=object()
                    )
            self.assertEqual((output / "candidate.pt").read_bytes(), concurrent)
            self.assertFalse(list(output.glob(".candidate-*.staging.pt")))

    def test_checkpoint_staging_creation_is_exclusive_and_preserves_collision(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            fixed = "1" * 32
            staging = output / f".candidate-{fixed}.staging.pt"
            concurrent = b"precreated staging checkpoint"
            staging.write_bytes(concurrent)
            with (
                mock.patch.object(
                    pilot.uuid, "uuid4", return_value=SimpleNamespace(hex=fixed)
                ),
                mock.patch.object(
                    pilot,
                    "_serialize_checkpoint_payload",
                    return_value=b"this attempt",
                ),
            ):
                with self.assertRaises(FileExistsError):
                    pilot._publish_checkpoint_exclusive(
                        output, model=object(), metadata={}, optimizer=object()
                    )
            self.assertEqual(staging.read_bytes(), concurrent)
            self.assertFalse((output / "candidate.pt").exists())

    def test_status_receipt_and_marker_boundary_failures_roll_back_owned_artifacts(self):
        receipt = {"receipt_sha256": "A" * 64, "status": "accepted"}
        for destination_name in ("accepted_receipt.json", "ACCEPTED"):
            for fail_after_create in (False, True):
                with self.subTest(
                    destination=destination_name, fail_after_create=fail_after_create
                ), tempfile.TemporaryDirectory() as temporary:
                    output = Path(temporary)
                    real_create = pilot._create_new_file_guarded

                    def fail_before(path, payload, guard):
                        if Path(path).name == destination_name:
                            raise OSError("injected commit boundary failure")
                        return real_create(path, payload, guard)

                    read_count = 0
                    real_read = pilot._win_read_all

                    def fail_after(handle):
                        nonlocal read_count
                        read_count += 1
                        target_count = 1 if destination_name.endswith(".json") else 2
                        if read_count == target_count:
                            raise OSError("injected commit boundary failure")
                        return real_read(handle)

                    patcher = (
                        mock.patch.object(
                            pilot, "_win_read_all", side_effect=fail_after
                        )
                        if fail_after_create
                        else mock.patch.object(
                            pilot,
                            "_create_new_file_guarded",
                            side_effect=fail_before,
                        )
                    )
                    with patcher:
                        with self.assertRaisesRegex(OSError, "injected"):
                            pilot._publish_status(
                                output, status="accepted", receipt=receipt
                            )
                    self.assertFalse(
                        any(
                            (output / name).exists()
                            for name in (
                                "accepted_receipt.json",
                                "rejected_receipt.json",
                                "ACCEPTED",
                                "REJECTED",
                            )
                        )
                    )
                    self.assertFalse(list(output.glob(".*.staging.json")))

    def test_serialized_candidate_is_reloaded_and_exactly_validated(self):
        model = ResidualActorCritic()
        source_hashes = pilot.checkpoint_source_hashes()
        optimizer = pilot._new_adam(model)
        optimizer.zero_grad(set_to_none=True)
        sum(parameter.sum() for parameter in model.parameters()).backward()
        optimizer.step()
        metadata = checkpoint_metadata(
            source_hashes=source_hashes,
            training={"fixture": True},
        )
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            directory_guard = pilot._StableDirectoryGuard(output)
            directory_guard.__enter__()
            protection = None
            try:
                path, digest, protection, readback = (
                    pilot._publish_checkpoint_exclusive(
                        output,
                        model=model,
                        metadata=metadata,
                        optimizer=optimizer,
                        directory_guard=directory_guard,
                    )
                )
                report = pilot._validate_serialized_candidate(
                    path,
                    claimed_sha256=digest,
                    expected_model=model,
                    expected_metadata=metadata,
                    expected_optimizer_state=optimizer.state_dict(),
                    expected_source_hashes=source_hashes,
                    directory_guard=directory_guard,
                    file_guard=protection,
                    serialized_readback=readback,
                )
                self.assertEqual(readback, pilot._win_read_all(protection.handle))
            finally:
                if protection is not None:
                    protection.close()
                directory_guard.close()
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["checkpoint_sha256"], digest)
            self.assertEqual(pilot.sha256_checkpoint(path), digest)
            self.assertFalse(list(output.glob(".candidate-*.staging.pt")))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                pilot._validate_serialized_candidate(
                    path,
                    claimed_sha256="0" * 64,
                    expected_model=model,
                    expected_metadata=metadata,
                    expected_optimizer_state=optimizer.state_dict(),
                    expected_source_hashes=source_hashes,
                    serialized_readback=readback,
                )

    def test_post_output_failure_writes_rejected_artifacts_never_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            output.mkdir()
            report = pilot._write_failed_execution(
                output,
                execution_spec=Path(temporary) / "execution.json",
                execution_spec_sha256="A" * 64,
                phase="checkpoint_reload_provenance_validation",
                error=ValueError("fixture failure"),
            )
            self.assertEqual(report["status"], "rejected")
            self.assertTrue((output / "REJECTED").is_file())
            self.assertTrue((output / "rejected_receipt.json").is_file())
            self.assertFalse((output / "ACCEPTED").exists())
            receipt = json.loads(
                (output / "rejected_receipt.json").read_text(encoding="utf-8")
            )
            self.assertEqual(receipt["checkpoint_provenance_validation"], "fail")
            self.assertFalse(receipt["accepted_marker_written"])


class DeploymentAuditTests(unittest.TestCase):
    def setUp(self):
        _reset_process_registry_for_tests()

    def tearDown(self):
        _reset_process_registry_for_tests()

    def test_disabled_audit_is_none_and_does_not_touch_action(self):
        self.assertIsNone(DeploymentAudit.from_environment({}))
        repo = pilot.find_repo_root()
        source_wrapper = (
            repo
            / "research" / "experiments"
            / "archaludon_latest_v1_rl_temperature_candidate_20260731"
            / "runtime_agent"
            / "main.py"
        )
        isolated_wrapper = Path(__file__).resolve().parents[1] / "runtime_agent" / "main.py"
        engine = pilot.seeded_engine_dir()
        script = r'''
import importlib.util
import json
import os
import sys

os.environ.pop("ARCHALUDON_RL_DEPLOYMENT_AUDIT_DIR", None)
os.environ.pop("ARCHALUDON_RL_CHECKPOINT", None)
sys.path.insert(0, sys.argv[2])
import cg.api

spec = importlib.util.spec_from_file_location("runtime_parity_probe", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
observation = {
    "select": None,
    "logs": [],
    "current": None,
    "search_begin_input": "opaque",
}
rows = []
for _ in range(2):
    previous = None if module._controller is None else id(module._controller)
    action = module.agent(observation)
    rows.append({
        "action": action,
        "game_epoch": module._game_epoch,
        "controller_replaced": previous is None or previous != id(module._controller),
        "callback_ordinal": getattr(module, "_callback_ordinal", None),
        "audit_disabled": getattr(module, "_deployment_audit", None) is None,
    })
print(json.dumps(rows, sort_keys=True))
'''
        environment = dict(os.environ)
        environment.pop(AUDIT_DIRECTORY_ENVIRONMENT, None)
        environment.pop("ARCHALUDON_RL_CHECKPOINT", None)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"

        def run(wrapper: Path) -> list[dict]:
            completed = subprocess.run(
                [sys.executable, "-B", "-c", script, str(wrapper), str(engine)],
                cwd=repo,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(
                completed.returncode, 0, completed.stdout + completed.stderr
            )
            return json.loads(completed.stdout.strip().splitlines()[-1])

        source_rows = run(source_wrapper)
        isolated_rows = run(isolated_wrapper)
        self.assertEqual(
            [row["action"] for row in isolated_rows],
            [row["action"] for row in source_rows],
        )
        self.assertEqual(
            [row["game_epoch"] for row in isolated_rows],
            [row["game_epoch"] for row in source_rows],
        )
        self.assertEqual([row["game_epoch"] for row in source_rows], [1, 2])
        self.assertTrue(all(row["controller_replaced"] for row in source_rows))
        self.assertTrue(all(row["controller_replaced"] for row in isolated_rows))
        self.assertEqual(
            [row["callback_ordinal"] for row in isolated_rows], [1, 1]
        )
        self.assertTrue(all(row["audit_disabled"] for row in isolated_rows))

    def test_enabled_audit_records_bounded_unsampled_candidate_decision(self):
        with tempfile.TemporaryDirectory() as temporary:
            audit = DeploymentAudit.from_environment(
                {AUDIT_DIRECTORY_ENVIRONMENT: temporary}
            )
            self.assertIsNotNone(audit)
            audit.record(_decision(action=(1,), teacher_action=(0,)), game_epoch=1, callback_ordinal=1)
            audit.close()
            summary = load_and_validate_deployment_audit(
                Path(temporary), expected_checkpoint_sha256="A" * 64
            )
            self.assertEqual(summary["row_count"], 1)
            self.assertEqual(summary["candidate_decision_count"], 1)
            self.assertEqual(summary["candidate_action_change_count"], 1)

    def test_protected_mismatch_and_fail_closed_failure_are_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            audit = DeploymentAudit(Path(temporary))
            audit.record(
                _decision(protected=True, failure_kind="TimeoutError"),
                game_epoch=1,
                callback_ordinal=1,
            )
            path = audit.path
            audit.close()
            row = json.loads(path.read_text(encoding="utf-8").strip())
            with self.assertRaisesRegex(ValueError, "fail-closed model failures"):
                validate_deployment_audit_rows(
                    [row], expected_checkpoint_sha256="A" * 64
                )
            summary = validate_deployment_audit_rows(
                [row],
                expected_checkpoint_sha256="A" * 64,
                require_no_model_failures=False,
            )
            self.assertEqual(summary["model_failure_count"], 1)
            self.assertEqual(summary["model_timeout_count"], 1)
            row["action"] = [1]
            with self.assertRaisesRegex(ValueError, "protected-action mismatch"):
                validate_deployment_audit_rows(
                    [row],
                    expected_checkpoint_sha256="A" * 64,
                    require_no_model_failures=False,
                )

    def test_writer_rejects_adversarial_protected_action(self):
        with tempfile.TemporaryDirectory() as temporary:
            audit = DeploymentAudit(Path(temporary))
            with self.assertRaisesRegex(ValueError, "not teacher-exact"):
                audit.record(
                    _decision(
                        protected=True, action=(1,), teacher_action=(0,)
                    ),
                    game_epoch=1,
                    callback_ordinal=1,
                )
            audit.close()

    def test_two_objects_in_one_process_share_exactly_one_stream_and_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = DeploymentAudit(Path(temporary))
            second = DeploymentAudit(Path(temporary))
            self.assertEqual(first.path, second.path)
            self.assertEqual(first.process_identity, second.process_identity)
            first.record(_decision(), game_epoch=1, callback_ordinal=1)
            second.record(_decision(), game_epoch=1, callback_ordinal=2)
            first.close()
            second.close()
            summary = load_and_validate_deployment_audit(
                Path(temporary), expected_checkpoint_sha256="A" * 64
            )
            self.assertEqual(summary["process_count"], 1)
            self.assertEqual(summary["row_count"], 2)
            self.assertEqual(len(summary["files"]), 1)

    def test_validator_rejects_duplicate_pid_files_regardless_of_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            audit = DeploymentAudit(Path(temporary))
            audit.record(_decision(), game_epoch=1, callback_ordinal=1)
            original_path = audit.path
            audit.close()
            row = json.loads(original_path.read_text(encoding="utf-8").strip())
            row["process_identity"] = "C" * 64
            duplicate_path = Path(temporary) / (
                f"deployment-audit-{row['process_id']}-{row['process_identity']}.jsonl"
            )
            duplicate_path.write_bytes(
                (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode(
                    "utf-8"
                )
            )
            with self.assertRaisesRegex(ValueError, "multiple files"):
                load_and_validate_deployment_audit(
                    Path(temporary), expected_checkpoint_sha256="A" * 64
                )

    def test_two_processes_use_distinct_append_only_files_without_race(self):
        candidate_root = str(Path(__file__).resolve().parents[1])
        script = r'''
from pathlib import Path
from types import SimpleNamespace
import os
from archaludon_rl.deployment_audit import DeploymentAudit
d=SimpleNamespace(action=(0,),teacher_action=(0,),neural_shadow_action=(0,),ppo_eligible=False,fallback_used=False,fallback_reason=None,guard=SimpleNamespace(protected_fallback=SimpleNamespace(hard=False)),residuals=(0.0,),checkpoint_sha256="A"*64,collection_mode="deployment",sampled_stochastically=False,model_failure_kind=None,model_timeout=False,legal_option_count=1,behavior_schema_sha256="B"*64,teacher_call_count=1)
a=DeploymentAudit(Path(os.environ["AUDIT_FIXTURE_DIR"])); a.record(d,game_epoch=1,callback_ordinal=1); a.close()
'''
        with tempfile.TemporaryDirectory() as temporary:
            environment = dict(os.environ)
            environment["PYTHONPATH"] = candidate_root
            environment["AUDIT_FIXTURE_DIR"] = temporary
            processes = [
                subprocess.Popen(
                    [sys.executable, "-c", script],
                    cwd=candidate_root,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for _ in range(2)
            ]
            for process in processes:
                stdout, stderr = process.communicate(timeout=30)
                self.assertEqual(process.returncode, 0, stdout + stderr)
            summary = load_and_validate_deployment_audit(
                Path(temporary), expected_checkpoint_sha256="A" * 64
            )
            self.assertEqual(summary["process_count"], 2)
            self.assertEqual(summary["row_count"], 2)
            self.assertEqual(len(summary["files"]), 2)


if __name__ == "__main__":
    unittest.main()
