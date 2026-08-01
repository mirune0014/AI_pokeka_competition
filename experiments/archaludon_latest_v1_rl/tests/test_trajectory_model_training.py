from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import random
import shutil
import tempfile
import unittest

import torch

from archaludon_rl.collect_rollouts import build_parser as build_collection_parser
from archaludon_rl.encoders import ACTION_DIM, STATE_DIM, encoder_metadata
from archaludon_rl.frozen_sources import (
    checkpoint_source_hashes,
    find_repo_root,
    seeded_engine_dir,
    sha256_file,
    verify_frozen_sources,
)
from archaludon_rl.model import (
    MODEL_SCHEMA_VERSION,
    ResidualActorCritic,
    checkpoint_metadata,
    load_checkpoint,
    save_checkpoint,
    sha256_checkpoint,
)
from archaludon_rl.policy import PolicyConfig, ResidualPolicy
from archaludon_rl.reference_policy import (
    REFERENCE_PRIOR_SCHEMA_VERSION,
    canonical_reference_prior_receipt,
    reference_prior_sha256,
)
from archaludon_rl.train_ppo import PPOConfig, train
from archaludon_rl.trajectory import (
    COLLECTION_SPEC_SCHEMA_VERSION,
    DATASET_SCHEMA_VERSION,
    MANIFEST_SCHEMA_VERSION,
    TRAJECTORY_SCHEMA_VERSION,
    EpisodeBuilder,
    RunManifest,
    collection_spec_sha256,
    compare_duplicate_traces,
    dataset_sha256,
    json_sha256,
    load_opponent_population_spec,
    publish_clean_episode,
)

from .helpers import FakeModel, StubTeacher, make_runtime_receipt, observation


class TrajectoryModelTrainingTests(unittest.TestCase):
    def _decision(self, protected: bool = False):
        teacher = StubTeacher()
        if protected:
            teacher.telemetry = (
                {
                    **teacher.telemetry[0],
                    "active_owner_before": "owner",
                    "active_owner_after": "owner",
                    "precedence_reason": "rank2_active_transaction_owner",
                    "winning_rule_id": "owner",
                },
            )
        return ResidualPolicy(
            teacher,
            model=FakeModel([0.0, 0.0]),
            checkpoint_sha256="E" * 64,
            config=PolicyConfig(mode="training", model_timeout_seconds=1.0),
        ).decide(observation())

    def _engine_receipt(self) -> dict[str, str]:
        verified = verify_frozen_sources()
        api_path = (seeded_engine_dir() / "cg" / "api.py").resolve()
        return {
            "runtime_manifest_sha256": str(
                verified["engine_runtime_manifest_sha256"]
            ),
            "cg_api_path": str(api_path),
            "cg_api_sha256": sha256_file(api_path),
        }

    def _make_run(
        self,
        root: Path,
        *,
        run_id: str,
        behavior: str = "checkpoint",
        protected: bool = False,
        mode: str = "training",
        seed: int = 7,
        opponent_ids: tuple[str, ...] = ("historical_silver",),
        population_spec: Path | None = None,
        policy_rng_seed: int | None = None,
        duplicate_mode: bool = False,
    ) -> dict[str, object]:
        sources = checkpoint_source_hashes()
        checkpoint = root / "initial.pt"
        checkpoint_meta = checkpoint_metadata(source_hashes=sources)
        save_checkpoint(
            checkpoint,
            ResidualActorCritic(),
            checkpoint_meta,
        )
        checkpoint_hash = sha256_checkpoint(checkpoint)
        runtime_receipt, runtime_hash = make_runtime_receipt(checkpoint_hash)
        prior_receipt = dict(checkpoint_meta["reference_prior_receipt"])
        prior_hash = str(checkpoint_meta["reference_prior_schema_sha256"])
        population_path = population_spec or (
            Path(__file__).resolve().parents[1]
            / "specs"
            / "phase1_iteration_002_population.json"
        )
        population_receipt, opponent_table = load_opponent_population_spec(
            population_path,
            repo_root=find_repo_root(),
        )
        known_ids = {row["id"] for row in opponent_table}
        if not opponent_ids or not set(opponent_ids).issubset(known_ids):
            raise ValueError("fixture opponent IDs must exist in the population")
        schedule = tuple(
            {
                "episode_id": (
                    f"{run_id}_opponent_{opponent_id}_seat0_seed{seed}"
                ),
                "opponent_id": opponent_id,
                "seat": 0,
                "seed": seed,
                "game": 0,
                "replicas": 2 if duplicate_mode else 1,
            }
            for opponent_id in opponent_ids
        )
        manifest = RunManifest.create(
            run_id=run_id,
            source_hashes=sources,
            checkpoint_sha256=checkpoint_hash,
            reference_prior_receipt=prior_receipt,
            reference_prior_schema_sha256=prior_hash,
            engine_receipt=self._engine_receipt(),
            runtime_receipt=runtime_receipt,
            runtime_receipt_sha256=runtime_hash,
            mode=mode,
            duplicate_mode=duplicate_mode,
            schedule=schedule,
            opponent_population_receipt=population_receipt,
            opponent_table=opponent_table,
            command=("unit-test-collector",),
        )
        if behavior == "checkpoint":
            behavior_model, _, _ = load_checkpoint(
                checkpoint,
                expected_source_hashes=sources,
            )
        elif behavior == "fake":
            behavior_model = FakeModel([0.5, -0.5], value=0.25)
        else:
            raise ValueError(f"unsupported behavior fixture: {behavior}")
        episode_paths: list[Path] = []
        receipts: list[dict[str, object]] = []
        for episode_index, schedule_row in enumerate(schedule):
            teacher = StubTeacher()
            if protected:
                teacher.telemetry = (
                    {
                        **teacher.telemetry[0],
                        "active_owner_before": "owner",
                        "active_owner_after": "owner",
                        "precedence_reason": "rank2_active_transaction_owner",
                        "winning_rule_id": "owner",
                    },
                )
            decision = ResidualPolicy(
                teacher,
                model=behavior_model,
                checkpoint_sha256=checkpoint_hash,
                config=PolicyConfig(mode=mode, model_timeout_seconds=1.0),
                rng=(
                    random.Random(policy_rng_seed + episode_index)
                    if policy_rng_seed is not None
                    else None
                ),
            ).decide(observation())
            episode_id = str(schedule_row["episode_id"])
            opponent_id = str(schedule_row["opponent_id"])
            builder = EpisodeBuilder(
                run_id=run_id,
                episode_id=episode_id,
                opponent_id=opponent_id,
                seat=0,
                seed=seed,
                source_hashes=sources,
                checkpoint_sha256=checkpoint_hash,
                reference_prior_receipt=prior_receipt,
                reference_prior_schema_sha256=prior_hash,
                runtime_receipt=runtime_receipt,
                runtime_receipt_sha256=runtime_hash,
                collection_spec_sha256=manifest.collection_spec_sha256,
                schedule_sha256=manifest.schedule_sha256,
                mode=mode,
            )
            builder.append(observation(), decision)
            terminal = observation()
            terminal["current"]["result"] = 0
            episode_path = root / "episodes" / f"{episode_id}.json"
            built_episode = builder.finish(
                terminal_result=0,
                clean_terminal=True,
                terminal_observation=terminal,
                engine_steps=1,
            )
            if duplicate_mode:
                audit_paths = [
                    root / "audit" / f"{episode_id}_{replica}.json"
                    for replica in ("a", "b")
                ]
                replica_episodes = []
                for replica, audit_path in zip(("a", "b"), audit_paths):
                    replica_episode = deepcopy(built_episode)
                    replica_episode["episode_id"] = (
                        f"{episode_id}_audit_{replica}"
                    )
                    publish_clean_episode(audit_path, replica_episode)
                    replica_episodes.append(replica_episode)
                duplicate = compare_duplicate_traces(
                    replica_episodes[0], replica_episodes[1]
                )
                duplicate["replica_receipts"] = [
                    {
                        "replica": replica,
                        "path": f"audit/{episode_id}_{replica}.json",
                        "bytes": audit_path.stat().st_size,
                        "sha256": sha256_file(audit_path),
                        "clean_terminal": True,
                        "terminal_result": replica_episode["terminal_result"],
                        "engine_steps": replica_episode["engine_steps"],
                        "fallback_count": sum(
                            row["fallback_used"]
                            for row in replica_episode["decisions"]
                        ),
                        "model_failure_count": sum(
                            row["model_failure_kind"] is not None
                            for row in replica_episode["decisions"]
                        ),
                        "model_timeout_count": sum(
                            row["model_timeout"]
                            for row in replica_episode["decisions"]
                        ),
                    }
                    for replica, audit_path, replica_episode in zip(
                        ("a", "b"), audit_paths, replica_episodes
                    )
                ]
                built_episode["duplicate_audit"] = duplicate
            publish_clean_episode(episode_path, built_episode)
            episode_paths.append(episode_path)
            receipts.append(
                {
                    "run_id": run_id,
                    "episode_id": episode_id,
                    "opponent_id": opponent_id,
                    "path": f"episodes/{episode_id}.json",
                    "bytes": episode_path.stat().st_size,
                    "sha256": sha256_file(episode_path),
                    "seat": 0,
                    "seed": seed,
                }
            )
        final_manifest = manifest.finalize(tuple(receipts))
        manifest_path = root / "run_manifest.json"
        final_manifest.write(manifest_path)
        return {
            "checkpoint": checkpoint,
            "checkpoint_hash": checkpoint_hash,
            "episode_path": episode_paths[0],
            "episode_paths": tuple(episode_paths),
            "population_spec": population_path,
            "manifest": final_manifest,
            "manifest_path": manifest_path,
            "output": root / "trained.pt",
        }

    def _refresh_manifest_episode(
        self,
        fixture: dict[str, object],
    ) -> None:
        manifest = fixture["manifest"]
        self.assertIsInstance(manifest, RunManifest)
        episode_path = fixture["episode_path"]
        self.assertIsInstance(episode_path, Path)
        receipt = dict(manifest.episode_receipts[0])
        receipt["bytes"] = episode_path.stat().st_size
        receipt["sha256"] = sha256_file(episode_path)
        receipts = (receipt,)
        refreshed = replace(
            manifest,
            episode_receipts=receipts,
            dataset_sha256=dataset_sha256(
                manifest.collection_spec_sha256,
                receipts,
                reference_prior_receipt=manifest.reference_prior_receipt,
                reference_prior_schema_sha256=(
                    manifest.reference_prior_schema_sha256
                ),
                runtime_receipt=manifest.runtime_receipt,
                runtime_receipt_sha256=manifest.runtime_receipt_sha256,
            ),
        )
        manifest_path = fixture["manifest_path"]
        self.assertIsInstance(manifest_path, Path)
        refreshed.write(manifest_path)
        fixture["manifest"] = refreshed

    def _refresh_manifest_contract_hashes(
        self,
        fixture: dict[str, object],
        payload: dict[str, object],
    ) -> None:
        schedule = tuple(dict(row) for row in payload["schedule"])
        schedule_hash = json_sha256({"schedule": schedule})
        payload["schedule_sha256"] = schedule_hash
        spec_hash = collection_spec_sha256(
            run_id=str(payload["run_id"]),
            source_hashes=dict(payload["source_hashes"]),
            checkpoint_sha256=str(payload["checkpoint_sha256"]),
            reference_prior_receipt=dict(payload["reference_prior_receipt"]),
            reference_prior_schema_sha256=str(
                payload["reference_prior_schema_sha256"]
            ),
            engine_receipt=dict(payload["engine_receipt"]),
            runtime_receipt=dict(payload["runtime_receipt"]),
            runtime_receipt_sha256=str(payload["runtime_receipt_sha256"]),
            mode=str(payload["mode"]),
            duplicate_mode=bool(payload["duplicate_mode"]),
            schedule=schedule,
            schedule_sha256=schedule_hash,
            opponent_population_receipt=dict(
                payload["opponent_population_receipt"]
            ),
            opponent_table=tuple(
                dict(row) for row in payload["opponent_table"]
            ),
            command=tuple(str(value) for value in payload["command"]),
            episode_directory=str(payload["episode_directory"]),
        )
        payload["collection_spec_sha256"] = spec_hash
        receipts = tuple(dict(row) for row in payload["episode_receipts"])
        payload["dataset_sha256"] = dataset_sha256(
            spec_hash,
            receipts,
            reference_prior_receipt=dict(payload["reference_prior_receipt"]),
            reference_prior_schema_sha256=str(
                payload["reference_prior_schema_sha256"]
            ),
            runtime_receipt=dict(payload["runtime_receipt"]),
            runtime_receipt_sha256=str(payload["runtime_receipt_sha256"]),
        )
        fixture["manifest_path"].write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

    def _write_fixture_population(
        self,
        root: Path,
        *,
        opponent_id: str = "fixture_opponent",
    ) -> tuple[Path, Path]:
        repo = find_repo_root()
        source = (
            repo
            / "analysis_outputs"
            / "reference_agents"
            / "historical_silver_archaludon_54495224"
        )
        opponent_dir = root / "opponent"
        opponent_dir.mkdir()
        shutil.copyfile(source / "main.py", opponent_dir / "main.py")
        shutil.copyfile(source / "deck.csv", opponent_dir / "deck.csv")
        population_path = root / "population.json"
        payload = {
            "schema_version": "archaludon-rl-opponent-population-v1",
            "population_id": "unit-test-population",
            "opponents": [
                {
                    "id": opponent_id,
                    "path": opponent_dir.relative_to(repo).as_posix(),
                    "main_sha256": sha256_file(opponent_dir / "main.py"),
                    "deck_sha256": sha256_file(opponent_dir / "deck.csv"),
                }
            ],
        }
        population_path.write_text(json.dumps(payload), encoding="utf-8")
        return population_path, opponent_dir

    def _write_semantically_tampered_runtime_with_all_hashes_refreshed(
        self,
        fixture: dict[str, object],
        mutate,
    ) -> None:
        manifest_path = fixture["manifest_path"]
        episode_path = fixture["episode_path"]
        self.assertIsInstance(manifest_path, Path)
        self.assertIsInstance(episode_path, Path)
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        episode = json.loads(episode_path.read_text(encoding="utf-8"))
        runtime_receipt = deepcopy(payload["runtime_receipt"])
        mutate(runtime_receipt)
        runtime_hash = json_sha256(runtime_receipt)
        payload["runtime_receipt"] = runtime_receipt
        payload["runtime_receipt_sha256"] = runtime_hash
        episode["runtime_receipt"] = runtime_receipt
        episode["runtime_receipt_sha256"] = runtime_hash
        schedule = tuple(dict(row) for row in payload["schedule"])
        schedule_hash = json_sha256({"schedule": schedule})
        spec_hash = json_sha256(
            {
                "schema_version": COLLECTION_SPEC_SCHEMA_VERSION,
                "run_id": str(payload["run_id"]),
                "source_hashes": dict(payload["source_hashes"]),
                "checkpoint_sha256": str(payload["checkpoint_sha256"]),
                "reference_prior_receipt": dict(
                    payload["reference_prior_receipt"]
                ),
                "reference_prior_schema_sha256": str(
                    payload["reference_prior_schema_sha256"]
                ),
                "engine_receipt": dict(payload["engine_receipt"]),
                "runtime_receipt": runtime_receipt,
                "runtime_receipt_sha256": runtime_hash,
                "mode": str(payload["mode"]),
                "duplicate_mode": bool(payload["duplicate_mode"]),
                "schedule": schedule,
                "schedule_sha256": schedule_hash,
                "opponent_population_receipt": dict(
                    payload["opponent_population_receipt"]
                ),
                "opponent_table": tuple(
                    dict(row) for row in payload["opponent_table"]
                ),
                "command": tuple(str(value) for value in payload["command"]),
                "episode_directory": str(payload["episode_directory"]),
            }
        )
        payload["collection_spec_sha256"] = spec_hash
        episode["collection_spec_sha256"] = spec_hash
        episode_path.write_text(json.dumps(episode), encoding="utf-8")
        receipts = [dict(row) for row in payload["episode_receipts"]]
        receipts[0]["bytes"] = episode_path.stat().st_size
        receipts[0]["sha256"] = sha256_file(episode_path)
        payload["episode_receipts"] = receipts
        payload["dataset_sha256"] = json_sha256(
            {
                "schema_version": DATASET_SCHEMA_VERSION,
                "collection_spec_sha256": spec_hash,
                "reference_prior_schema_version": payload[
                    "reference_prior_receipt"
                ]["schema_version"],
                "reference_prior_schema_sha256": str(
                    payload["reference_prior_schema_sha256"]
                ),
                "runtime_receipt": runtime_receipt,
                "runtime_receipt_sha256": runtime_hash,
                "episode_receipts": tuple(receipts),
            }
        )
        manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    def _train_fixture(
        self,
        fixture: dict[str, object],
        *,
        config: PPOConfig | None = None,
    ) -> dict[str, object]:
        return train(
            input_checkpoint=fixture["checkpoint"],
            manifest_path=fixture["manifest_path"],
            output_checkpoint=fixture["output"],
            config=config or PPOConfig(epochs=1),
        )

    def test_terminal_reward_attaches_to_last_eligible_not_protected(self):
        prior_receipt = canonical_reference_prior_receipt()
        runtime_receipt, runtime_hash = make_runtime_receipt("E" * 64)
        builder = EpisodeBuilder(
            run_id="run",
            episode_id="episode",
            opponent_id="historical_silver",
            seat=0,
            seed=1,
            source_hashes={"main": "hash"},
            checkpoint_sha256="E" * 64,
            reference_prior_receipt=prior_receipt,
            reference_prior_schema_sha256=reference_prior_sha256(prior_receipt),
            runtime_receipt=runtime_receipt,
            runtime_receipt_sha256=runtime_hash,
            collection_spec_sha256="C" * 64,
            schedule_sha256="S" * 64,
        )
        builder.append(observation(), self._decision(protected=False))
        builder.append(observation(), self._decision(protected=True))
        terminal = observation()
        terminal["current"]["result"] = 0
        episode = builder.finish(
            terminal_result=0,
            clean_terminal=True,
            terminal_observation=terminal,
            engine_steps=2,
        )
        self.assertEqual(episode["decisions"][0]["reward"], 1.0)
        self.assertTrue(episode["decisions"][0]["ppo_eligible"])
        self.assertTrue(episode["decisions"][0]["terminated"])
        self.assertTrue(episode["decisions"][0]["done"])
        self.assertIsNotNone(
            episode["decisions"][0]["next_public_state_sha256"]
        )
        self.assertEqual(episode["decisions"][1]["reward"], 0.0)
        self.assertFalse(episode["decisions"][1]["ppo_eligible"])
        duplicate = json.loads(json.dumps(episode))
        self.assertTrue(compare_duplicate_traces(episode, duplicate)["equal"])
        duplicate["decisions"][0]["final_action"] = [
            1 - int(episode["decisions"][0]["final_action"][0])
        ]
        compared = compare_duplicate_traces(episode, duplicate)
        self.assertFalse(compared["equal"])
        self.assertEqual(compared["mismatch_indices"], [0])
        identity_mismatch = json.loads(json.dumps(episode))
        identity_mismatch["opponent_id"] = "alakazam_public"
        compared = compare_duplicate_traces(episode, identity_mismatch)
        self.assertFalse(compared["equal"])
        self.assertFalse(compared["identity_equal"])

    def test_episode_builder_rejects_decision_prior_header_mismatch(self):
        prior_receipt = canonical_reference_prior_receipt()
        runtime_receipt, runtime_hash = make_runtime_receipt("E" * 64)
        builder = EpisodeBuilder(
            run_id="run",
            episode_id="episode",
            opponent_id="historical_silver",
            seat=0,
            seed=1,
            source_hashes={"main": "hash"},
            checkpoint_sha256="E" * 64,
            reference_prior_receipt=prior_receipt,
            reference_prior_schema_sha256=reference_prior_sha256(prior_receipt),
            runtime_receipt=runtime_receipt,
            runtime_receipt_sha256=runtime_hash,
            collection_spec_sha256="C" * 64,
            schedule_sha256="S" * 64,
        )
        builder.header["reference_prior_schema_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "reference-prior identity"):
            builder.append(observation(), self._decision())

    def test_collection_cli_requires_population_not_single_opponent(self):
        parser = build_collection_parser()
        actions = {
            action.dest: action
            for action in parser._actions
        }
        self.assertIn("opponent_population", actions)
        self.assertTrue(actions["opponent_population"].required)
        self.assertNotIn("opponent", actions)

    def test_incomplete_manifest_cannot_be_published(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary), run_id="incomplete-manifest"
            )
            incomplete = replace(
                fixture["manifest"],
                complete=False,
                dataset_sha256=None,
                completed_at_utc=None,
            )
            with self.assertRaisesRegex(ValueError, "incomplete run manifests"):
                incomplete.write(Path(temporary) / "incomplete.json")

    def test_trainer_rejects_runtime_and_preflight_tampering_after_all_hash_refreshes(self):
        def disable_zero_residual_gate(receipt):
            receipt["preflight_configuration"][
                "require_zero_residuals"
            ] = False
            option_rows = receipt["preflight_results"][
                "option_count_results"
            ]
            for row in option_rows:
                row["nonzero_residual_count"] = 1
            receipt["preflight_results"]["nonzero_residual_count"] = len(
                option_rows
            )
            receipt["preflight_results"]["zero_residuals"] = False

        mutations = (
            (
                "observed-thread",
                lambda receipt: receipt["observed_thread_counts"].__setitem__(
                    "torch_num_threads", 2
                ),
                "thread-count contract",
            ),
            (
                "preflight-timeout",
                lambda receipt: (
                    receipt["preflight_results"].__setitem__(
                        "calls_above_timeout", 1
                    ),
                    receipt["preflight_results"]["option_count_results"][0].__setitem__(
                        "calls_above_timeout", 1
                    ),
                ),
                "gate failed",
            ),
            (
                "disabled-zero-residual-gate",
                disable_zero_residual_gate,
                "preflight configuration mismatch",
            ),
        )
        for label, mutate, expected_error in mutations:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temporary:
                    fixture = self._make_run(
                        Path(temporary), run_id=f"runtime-tamper-{label}"
                    )
                    self._write_semantically_tampered_runtime_with_all_hashes_refreshed(
                        fixture,
                        mutate,
                    )
                    with self.assertRaisesRegex(ValueError, expected_error):
                        self._train_fixture(fixture)

    def test_checkpoint_zero_residual_roundtrip(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "initial.pt"
            model = ResidualActorCritic()
            metadata = checkpoint_metadata(source_hashes={"main": "hash"})
            save_checkpoint(path, model, metadata)
            loaded, loaded_metadata, _ = load_checkpoint(
                path,
                expected_source_hashes={"main": "hash"},
            )
            residuals, _ = loaded.predict(
                [0.0] * STATE_DIM,
                [[0.0] * ACTION_DIM] * 3,
            )
            self.assertEqual(residuals, [0.0, 0.0, 0.0])
            self.assertEqual(
                loaded_metadata["encoder"]["schema_version"],
                encoder_metadata()["schema_version"],
            )
            self.assertEqual(
                loaded_metadata["model_schema_version"],
                MODEL_SCHEMA_VERSION,
            )
            self.assertEqual(
                loaded_metadata["reference_prior_receipt"],
                canonical_reference_prior_receipt(),
            )
            self.assertEqual(
                loaded_metadata["reference_prior_schema_sha256"],
                reference_prior_sha256(),
            )
            with self.assertRaises(ValueError):
                load_checkpoint(path, expected_source_hashes={"main": "wrong"})

    def test_checkpoint_rejects_legacy_and_tampered_margin1_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for label, mutate, expected in (
                (
                    "legacy",
                    lambda metadata: metadata.update(
                        {
                            "model_schema_version": "residual-actor-critic-v1",
                            "reference_policy": {
                                "teacher_margin": 1.0,
                                "residual_cap": 3.0,
                                "residual_scale": 2.0,
                                "exploration_epsilon": 0.02,
                            },
                        }
                    ),
                    "model schema",
                ),
                (
                    "tampered-margin",
                    lambda metadata: (
                        metadata["reference_prior_receipt"].update(
                            {"teacher_margin": 1.0}
                        ),
                        metadata.update(
                            {
                                "reference_prior_schema_sha256": (
                                    reference_prior_sha256(
                                        metadata["reference_prior_receipt"]
                                    )
                                )
                            }
                        ),
                    ),
                    "canonical configuration",
                ),
            ):
                with self.subTest(label=label):
                    metadata = checkpoint_metadata(
                        source_hashes={"main": "hash"}
                    )
                    mutate(metadata)
                    path = root / f"{label}.pt"
                    save_checkpoint(path, ResidualActorCritic(), metadata)
                    with self.assertRaisesRegex(ValueError, expected):
                        load_checkpoint(
                            path,
                            expected_source_hashes={"main": "hash"},
                        )

    def test_invalid_ppo_configuration_is_rejected_before_training(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(Path(temporary), run_id="bad-config")
            with self.assertRaisesRegex(ValueError, "epochs"):
                self._train_fixture(
                    fixture,
                    config=PPOConfig(epochs=0),
                )

    def test_ppo_rejects_teacher_only_dataset(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="teacher-only",
                protected=True,
            )
            with self.assertRaisesRegex(ValueError, "teacher-only"):
                self._train_fixture(fixture)

        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="teacher-only-empty-prior-fallback",
            )
            episode = json.loads(
                fixture["episode_path"].read_text(encoding="utf-8")
            )
            row = episode["decisions"][0]
            row.update(
                {
                    "ppo_eligible": False,
                    "protected": True,
                    "fallback_reason": "test_exact_teacher_fallback",
                    "sampled_stochastically": False,
                    "behavior_logprob": None,
                    "final_action": list(row["teacher_action"]),
                    "q_latest": [],
                    "teacher_probability": None,
                    "residuals": [],
                    "final_probabilities": [],
                }
            )
            publish_clean_episode(fixture["episode_path"], episode)
            self._refresh_manifest_episode(fixture)
            with self.assertRaisesRegex(ValueError, "teacher-only"):
                self._train_fixture(fixture)

    def test_one_row_on_policy_ppo_smoke_and_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(Path(temporary), run_id="ppo-smoke")
            audit_dir = fixture["manifest_path"].parent / "audit"
            audit_dir.mkdir()
            (audit_dir / "replica.json").write_text("{}", encoding="utf-8")
            report = self._train_fixture(fixture)
            self.assertEqual(report["on_policy_rows"], 1)
            self.assertTrue(fixture["output"].is_file())
            _, metadata, _ = load_checkpoint(
                fixture["output"],
                expected_source_hashes=checkpoint_source_hashes(),
            )
            training = metadata["training"]
            self.assertEqual(
                training["manifest_sha256"],
                report["manifest_sha256"],
            )
            self.assertEqual(
                training["dataset_sha256"],
                report["dataset_sha256"],
            )
            self.assertEqual(
                training["ppo_config"],
                PPOConfig(epochs=1).__dict__,
            )
            self.assertEqual(
                training["reference_prior_receipt"],
                canonical_reference_prior_receipt(),
            )
            self.assertEqual(
                training["reference_prior_schema_sha256"],
                reference_prior_sha256(),
            )

    def test_duplicate_audit_replica_receipts_are_reproducible_and_tamper_evident(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="duplicate-receipts-valid",
                duplicate_mode=True,
            )
            episode = json.loads(
                fixture["episode_path"].read_text(encoding="utf-8")
            )
            replica_receipts = episode["duplicate_audit"]["replica_receipts"]
            self.assertEqual([row["replica"] for row in replica_receipts], ["a", "b"])
            self.assertTrue(all(row["model_failure_count"] == 0 for row in replica_receipts))
            self.assertTrue(all(row["model_timeout_count"] == 0 for row in replica_receipts))
            self.assertEqual(self._train_fixture(fixture)["on_policy_rows"], 1)

        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="duplicate-receipts-tampered",
                duplicate_mode=True,
            )
            episode = json.loads(
                fixture["episode_path"].read_text(encoding="utf-8")
            )
            audit_relative = episode["duplicate_audit"]["replica_receipts"][0][
                "path"
            ]
            audit_path = fixture["manifest_path"].parent.joinpath(
                *Path(audit_relative).parts
            )
            audit_path.write_text(
                audit_path.read_text(encoding="utf-8") + " ",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "replica file receipt"):
                self._train_fixture(fixture)
            manifest = json.loads(
                fixture["manifest_path"].read_text(encoding="utf-8")
            )
            episode = json.loads(
                fixture["episode_path"].read_text(encoding="utf-8")
            )
            row = episode["decisions"][0]
            self.assertEqual(manifest["schema_version"], MANIFEST_SCHEMA_VERSION)
            self.assertEqual(episode["schema_version"], TRAJECTORY_SCHEMA_VERSION)
            self.assertEqual(
                manifest["reference_prior_receipt"],
                episode["reference_prior_receipt"],
            )
            self.assertEqual(
                manifest["reference_prior_schema_sha256"],
                row["prior_schema_sha256"],
            )
            self.assertEqual(row["legal_option_count"], len(row["q_latest"]))
            self.assertEqual(
                row["teacher_probability"],
                row["q_latest"][row["teacher_action"][0]],
            )

    def test_duplicate_audit_rejects_self_consistent_wrong_pair_after_hash_refresh(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="duplicate-wrong-pair",
                duplicate_mode=True,
            )
            retained = json.loads(
                fixture["episode_path"].read_text(encoding="utf-8")
            )
            replica_receipts = retained["duplicate_audit"][
                "replica_receipts"
            ]
            replica_episodes = []
            for receipt in replica_receipts:
                audit_path = fixture["manifest_path"].parent.joinpath(
                    *Path(receipt["path"]).parts
                )
                replica_episode = json.loads(
                    audit_path.read_text(encoding="utf-8")
                )
                replica_episode["opponent_id"] = "alakazam_public"
                publish_clean_episode(audit_path, replica_episode)
                receipt["bytes"] = audit_path.stat().st_size
                receipt["sha256"] = sha256_file(audit_path)
                replica_episodes.append(replica_episode)
            recomputed = compare_duplicate_traces(
                replica_episodes[0], replica_episodes[1]
            )
            self.assertTrue(recomputed["equal"])
            retained["duplicate_audit"] = {
                **recomputed,
                "replica_receipts": replica_receipts,
            }
            publish_clean_episode(fixture["episode_path"], retained)
            self._refresh_manifest_episode(fixture)
            with self.assertRaisesRegex(
                ValueError, "duplicate audit replica episode mismatch"
            ):
                self._train_fixture(fixture)

    def test_manifest_rejects_unsafe_episode_paths(self):
        unsafe_paths = (
            "../episode.json",
            "episodes/../episode.json",
            "episodes\\episode.json",
            "/episodes/episode.json",
            "C:/episodes/episode.json",
            "audit/episode.json",
            "episodes/nested/episode.json",
        )
        for index, unsafe_path in enumerate(unsafe_paths):
            with self.subTest(path=unsafe_path):
                with tempfile.TemporaryDirectory() as temporary:
                    fixture = self._make_run(
                        Path(temporary),
                        run_id=f"unsafe-{index}",
                    )
                    manifest = fixture["manifest"]
                    receipt = dict(manifest.episode_receipts[0])
                    receipt["path"] = unsafe_path
                    receipts = (receipt,)
                    changed = replace(
                        manifest,
                        episode_receipts=receipts,
                        dataset_sha256=dataset_sha256(
                            manifest.collection_spec_sha256,
                            receipts,
                            reference_prior_receipt=(
                                manifest.reference_prior_receipt
                            ),
                            reference_prior_schema_sha256=(
                                manifest.reference_prior_schema_sha256
                            ),
                            runtime_receipt=manifest.runtime_receipt,
                            runtime_receipt_sha256=(
                                manifest.runtime_receipt_sha256
                            ),
                        ),
                    )
                    changed.write(fixture["manifest_path"])
                    with self.assertRaisesRegex(
                        ValueError,
                        "unsafe|flat JSON",
                    ):
                        self._train_fixture(fixture)

    def test_manifest_rejects_missing_and_extra_non_episode_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(Path(temporary), run_id="missing")
            fixture["episode_path"].unlink()
            with self.assertRaisesRegex(ValueError, "missing"):
                self._train_fixture(fixture)

        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(Path(temporary), run_id="extra-entry")
            stray = fixture["episode_path"].parent / "stray.tmp"
            stray.write_text("not an episode", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "extra non-episode"):
                self._train_fixture(fixture)

    def test_ppo_rejects_rows_from_a_different_behavior_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="false-label",
                behavior="fake",
            )
            with self.assertRaisesRegex(ValueError, "claimed checkpoint"):
                self._train_fixture(fixture)

    def test_ppo_rejects_deployment_run_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="deployment",
                mode="deployment",
            )
            with self.assertRaisesRegex(ValueError, "training-mode"):
                self._train_fixture(fixture)

    def test_manifest_rejects_engine_schedule_and_episode_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = self._make_run(root, run_id="tamper")
            manifest_path = fixture["manifest_path"]
            original_manifest = manifest_path.read_text(encoding="utf-8")

            payload = json.loads(original_manifest)
            payload["engine_receipt"]["cg_api_sha256"] = "0" * 64
            manifest_path.write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "checked-engine"):
                self._train_fixture(fixture)

            manifest_path.write_text(original_manifest, encoding="utf-8")
            payload = json.loads(original_manifest)
            payload["schedule"][0]["seed"] += 1
            manifest_path.write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "schedule hash"):
                self._train_fixture(fixture)

            manifest_path.write_text(original_manifest, encoding="utf-8")
            episode_path = fixture["episode_path"]
            with episode_path.open("a", encoding="utf-8") as stream:
                stream.write(" ")
            with self.assertRaisesRegex(ValueError, "size mismatch"):
                self._train_fixture(fixture)

    def test_manifest_rejects_extra_mixed_and_duplicate_episodes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = self._make_run(root, run_id="closure")
            episode_path = fixture["episode_path"]
            extra = episode_path.parent / "extra.json"
            shutil.copyfile(episode_path, extra)
            with self.assertRaisesRegex(ValueError, "extra JSON"):
                self._train_fixture(fixture)
            extra.unlink()

            episode = json.loads(episode_path.read_text(encoding="utf-8"))
            episode["run_id"] = "mixed-run"
            publish_clean_episode(episode_path, episode)
            self._refresh_manifest_episode(fixture)
            with self.assertRaisesRegex(ValueError, "episode header"):
                self._train_fixture(fixture)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = self._make_run(root, run_id="duplicate")
            manifest = fixture["manifest"]
            duplicate_schedule = (
                dict(manifest.schedule[0]),
                dict(manifest.schedule[0]),
            )
            schedule_hash = json_sha256({"schedule": duplicate_schedule})
            spec_hash = collection_spec_sha256(
                run_id=manifest.run_id,
                source_hashes=manifest.source_hashes,
                checkpoint_sha256=manifest.checkpoint_sha256,
                reference_prior_receipt=manifest.reference_prior_receipt,
                reference_prior_schema_sha256=(
                    manifest.reference_prior_schema_sha256
                ),
                engine_receipt=manifest.engine_receipt,
                runtime_receipt=manifest.runtime_receipt,
                runtime_receipt_sha256=manifest.runtime_receipt_sha256,
                mode=manifest.mode,
                duplicate_mode=manifest.duplicate_mode,
                schedule=duplicate_schedule,
                schedule_sha256=schedule_hash,
                opponent_population_receipt=manifest.opponent_population_receipt,
                opponent_table=manifest.opponent_table,
                command=manifest.command,
                episode_directory=manifest.episode_directory,
            )
            duplicate_manifest = replace(
                manifest,
                schedule=duplicate_schedule,
                schedule_sha256=schedule_hash,
                collection_spec_sha256=spec_hash,
            )
            duplicate_manifest = replace(
                duplicate_manifest,
                dataset_sha256=dataset_sha256(
                    spec_hash,
                    duplicate_manifest.episode_receipts,
                    reference_prior_receipt=(
                        duplicate_manifest.reference_prior_receipt
                    ),
                    reference_prior_schema_sha256=(
                        duplicate_manifest.reference_prior_schema_sha256
                    ),
                    runtime_receipt=duplicate_manifest.runtime_receipt,
                    runtime_receipt_sha256=(
                        duplicate_manifest.runtime_receipt_sha256
                    ),
                ),
            )
            duplicate_manifest.write(fixture["manifest_path"])
            with self.assertRaisesRegex(ValueError, "duplicate schedule"):
                self._train_fixture(fixture)

    def test_valid_multi_opponent_bundle_trains_from_one_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="multi",
                opponent_ids=("historical_silver", "alakazam_public"),
            )
            report = self._train_fixture(fixture)
            self.assertEqual(report["on_policy_rows"], 2)
            manifest = json.loads(
                fixture["manifest_path"].read_text(encoding="utf-8")
            )
            self.assertEqual(
                [row["opponent_id"] for row in manifest["schedule"]],
                ["historical_silver", "alakazam_public"],
            )
            self.assertEqual(
                {
                    (
                        row["opponent_id"],
                        row["seat"],
                        row["seed"],
                    )
                    for row in manifest["episode_receipts"]
                },
                {
                    ("historical_silver", 0, 7),
                    ("alakazam_public", 0, 7),
                },
            )
            self.assertEqual(
                list(fixture["manifest_path"].parent.glob("run_manifest*.json")),
                [fixture["manifest_path"]],
            )

    def test_population_rejects_duplicate_and_missing_opponent_ids(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "specs"
            / "phase1_iteration_002_population.json"
        )
        original = json.loads(source.read_text(encoding="utf-8"))
        tests_root = Path(__file__).resolve().parent
        for mutation, expected in (("duplicate", "duplicate opponent ID"), ("missing", "invalid opponent row")):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory(dir=tests_root) as temporary:
                    path = Path(temporary) / "population.json"
                    payload = json.loads(json.dumps(original))
                    if mutation == "duplicate":
                        payload["opponents"].append(
                            dict(payload["opponents"][0])
                        )
                    else:
                        del payload["opponents"][0]["id"]
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, expected):
                        load_opponent_population_spec(
                            path,
                            repo_root=find_repo_root(),
                        )

    def test_population_rejects_unsafe_or_external_paths(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "specs"
            / "phase1_iteration_002_population.json"
        )
        payload = json.loads(source.read_text(encoding="utf-8"))
        tests_root = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(dir=tests_root) as temporary:
            path = Path(temporary) / "population.json"
            payload["opponents"][0]["path"] = "../outside"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "canonical repository-relative"):
                load_opponent_population_spec(path, repo_root=find_repo_root())
        with tempfile.TemporaryDirectory() as temporary:
            outside = Path(temporary) / "population.json"
            outside.write_text(
                source.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "contained in the repository"):
                load_opponent_population_spec(
                    outside,
                    repo_root=find_repo_root(),
                )

    def test_trainer_rejects_population_spec_and_opponent_file_mutation(self):
        tests_root = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(dir=tests_root) as temporary:
            root = Path(temporary)
            population_path, opponent_dir = self._write_fixture_population(root)
            fixture = self._make_run(
                root / "run",
                run_id="opponent-file-mutation",
                opponent_ids=("fixture_opponent",),
                population_spec=population_path,
            )
            with (opponent_dir / "main.py").open("a", encoding="utf-8") as stream:
                stream.write("\n# mutation\n")
            with self.assertRaisesRegex(ValueError, "main.py SHA256 mismatch"):
                self._train_fixture(fixture)

        with tempfile.TemporaryDirectory(dir=tests_root) as temporary:
            root = Path(temporary)
            population_path, _ = self._write_fixture_population(root)
            fixture = self._make_run(
                root / "run",
                run_id="population-spec-mutation",
                opponent_ids=("fixture_opponent",),
                population_spec=population_path,
            )
            payload = json.loads(population_path.read_text(encoding="utf-8"))
            payload["population_id"] = "unit-test-population-mutated"
            population_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "spec receipt mismatch"):
                self._train_fixture(fixture)

    def test_trainer_rejects_population_path_and_manifest_hash_mutation(self):
        tests_root = Path(__file__).resolve().parent
        repo = find_repo_root()
        with tempfile.TemporaryDirectory(dir=tests_root) as temporary:
            root = Path(temporary)
            population_path, _ = self._write_fixture_population(root)
            fixture = self._make_run(
                root / "run",
                run_id="population-path-mutation",
                opponent_ids=("fixture_opponent",),
                population_spec=population_path,
            )
            payload = json.loads(population_path.read_text(encoding="utf-8"))
            replacement = repo / "meta_agents" / "alakazam_psychic_public_simple"
            payload["opponents"][0].update(
                {
                    "path": replacement.relative_to(repo).as_posix(),
                    "main_sha256": sha256_file(replacement / "main.py"),
                    "deck_sha256": sha256_file(replacement / "deck.csv"),
                }
            )
            population_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "spec receipt mismatch"):
                self._train_fixture(fixture)

        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="opponent-hash-mutation",
            )
            payload = json.loads(
                fixture["manifest_path"].read_text(encoding="utf-8")
            )
            payload["opponent_table"][0]["main_sha256"] = "0" * 64
            self._refresh_manifest_contract_hashes(fixture, payload)
            with self.assertRaisesRegex(ValueError, "opponent table"):
                self._train_fixture(fixture)

    def test_trainer_rejects_missing_and_unknown_schedule_opponent_ids(self):
        for mutation in ("missing", "unknown"):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as temporary:
                    fixture = self._make_run(
                        Path(temporary),
                        run_id=f"schedule-{mutation}",
                    )
                    payload = json.loads(
                        fixture["manifest_path"].read_text(encoding="utf-8")
                    )
                    if mutation == "missing":
                        del payload["schedule"][0]["opponent_id"]
                    else:
                        payload["schedule"][0]["opponent_id"] = "unknown_opponent"
                    self._refresh_manifest_contract_hashes(fixture, payload)
                    with self.assertRaisesRegex(ValueError, "invalid schedule row"):
                        self._train_fixture(fixture)

    def test_trainer_rejects_mismatched_opponent_id_across_contract_layers(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="schedule-opponent-mismatch",
            )
            payload = json.loads(
                fixture["manifest_path"].read_text(encoding="utf-8")
            )
            payload["schedule"][0]["opponent_id"] = "alakazam_public"
            payload["schedule"][0]["episode_id"] = (
                "schedule-opponent-mismatch_opponent_"
                "alakazam_public_seat0_seed7"
            )
            self._refresh_manifest_contract_hashes(fixture, payload)
            with self.assertRaisesRegex(ValueError, "episode header"):
                self._train_fixture(fixture)

        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="receipt-opponent-mismatch",
            )
            payload = json.loads(
                fixture["manifest_path"].read_text(encoding="utf-8")
            )
            payload["episode_receipts"][0]["opponent_id"] = "alakazam_public"
            receipts = tuple(
                dict(row) for row in payload["episode_receipts"]
            )
            payload["dataset_sha256"] = dataset_sha256(
                payload["collection_spec_sha256"],
                receipts,
                reference_prior_receipt=dict(payload["reference_prior_receipt"]),
                reference_prior_schema_sha256=str(
                    payload["reference_prior_schema_sha256"]
                ),
                runtime_receipt=dict(payload["runtime_receipt"]),
                runtime_receipt_sha256=str(payload["runtime_receipt_sha256"]),
            )
            fixture["manifest_path"].write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "opponent ID"):
                self._train_fixture(fixture)

        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="episode-opponent-mismatch",
            )
            episode = json.loads(
                fixture["episode_path"].read_text(encoding="utf-8")
            )
            episode["opponent_id"] = "alakazam_public"
            fixture["episode_path"].write_text(
                json.dumps(episode),
                encoding="utf-8",
            )
            self._refresh_manifest_episode(fixture)
            with self.assertRaisesRegex(ValueError, "episode header"):
                self._train_fixture(fixture)

    def test_trainer_rejects_bool_identity_scalars_in_receipt_and_episode(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="bool-receipt-seat",
            )
            episode = json.loads(
                fixture["episode_path"].read_text(encoding="utf-8")
            )
            episode["seat"] = False
            fixture["episode_path"].write_text(
                json.dumps(episode),
                encoding="utf-8",
            )
            payload = json.loads(
                fixture["manifest_path"].read_text(encoding="utf-8")
            )
            receipt = payload["episode_receipts"][0]
            receipt["seat"] = False
            receipt["bytes"] = fixture["episode_path"].stat().st_size
            receipt["sha256"] = sha256_file(fixture["episode_path"])
            receipts = tuple(
                dict(row) for row in payload["episode_receipts"]
            )
            payload["dataset_sha256"] = dataset_sha256(
                payload["collection_spec_sha256"],
                receipts,
                reference_prior_receipt=dict(payload["reference_prior_receipt"]),
                reference_prior_schema_sha256=str(
                    payload["reference_prior_schema_sha256"]
                ),
                runtime_receipt=dict(payload["runtime_receipt"]),
                runtime_receipt_sha256=str(payload["runtime_receipt_sha256"]),
            )
            fixture["manifest_path"].write_text(
                json.dumps(payload),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "receipt identity.*scalar"):
                self._train_fixture(fixture)

        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="bool-episode-seat",
            )
            episode = json.loads(
                fixture["episode_path"].read_text(encoding="utf-8")
            )
            episode["seat"] = False
            fixture["episode_path"].write_text(
                json.dumps(episode),
                encoding="utf-8",
            )
            self._refresh_manifest_episode(fixture)
            with self.assertRaisesRegex(ValueError, "header identity.*scalar"):
                self._train_fixture(fixture)

    def test_trainer_recomputes_and_rejects_independent_row_prior_tampering(self):
        mutations = (
            (
                "prior-hash",
                lambda row: row.update({"prior_schema_sha256": "0" * 64}),
                "reference-prior",
            ),
            (
                "legal-count",
                lambda row: row.update(
                    {"legal_option_count": row["legal_option_count"] + 1}
                ),
                "legal option count",
            ),
            (
                "legal-count-bool",
                lambda row: row.update({"legal_option_count": True}),
                "strict nonnegative integer",
            ),
            (
                "teacher-probability",
                lambda row: row.update(
                    {
                        "teacher_probability": (
                            row["teacher_probability"] + 0.001
                        )
                    }
                ),
                "teacher probability",
            ),
            (
                "teacher-probability-sub-tolerance",
                lambda row: row.update(
                    {
                        "teacher_probability": (
                            row["teacher_probability"] + 5e-13
                        )
                    }
                ),
                "teacher probability",
            ),
            (
                "eligible-empty-prior",
                lambda row: row.update(
                    {
                        "q_latest": [],
                        "teacher_probability": None,
                    }
                ),
                "complete reference-prior provenance",
            ),
        )
        for label, mutate, expected in mutations:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as temporary:
                    fixture = self._make_run(
                        Path(temporary),
                        run_id=f"row-{label}",
                    )
                    episode = json.loads(
                        fixture["episode_path"].read_text(encoding="utf-8")
                    )
                    mutate(episode["decisions"][0])
                    publish_clean_episode(fixture["episode_path"], episode)
                    self._refresh_manifest_episode(fixture)
                    with self.assertRaisesRegex(ValueError, expected):
                        self._train_fixture(fixture)

        for changed_index in (0, 1):
            with self.subTest(q_latest_index=changed_index):
                with tempfile.TemporaryDirectory() as temporary:
                    fixture = self._make_run(
                        Path(temporary),
                        run_id=f"row-q-{changed_index}",
                    )
                    episode = json.loads(
                        fixture["episode_path"].read_text(encoding="utf-8")
                    )
                    row = episode["decisions"][0]
                    other_index = 1 - changed_index
                    row["q_latest"][changed_index] += 0.001
                    row["q_latest"][other_index] -= 0.001
                    teacher_index = row["teacher_action"][0]
                    row["teacher_probability"] = row["q_latest"][teacher_index]
                    publish_clean_episode(fixture["episode_path"], episode)
                    self._refresh_manifest_episode(fixture)
                    with self.assertRaisesRegex(
                        ValueError,
                        "latest prior cannot be reproduced",
                    ):
                        self._train_fixture(fixture)

        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="row-q-sub-tolerance",
            )
            episode = json.loads(
                fixture["episode_path"].read_text(encoding="utf-8")
            )
            row = episode["decisions"][0]
            row["q_latest"][0] += 5e-13
            row["q_latest"][1] -= 5e-13
            teacher_index = row["teacher_action"][0]
            row["teacher_probability"] = row["q_latest"][teacher_index]
            expected_q = list(row["q_latest"])
            expected_teacher_probability = row["teacher_probability"]
            publish_clean_episode(fixture["episode_path"], episode)
            roundtripped = json.loads(
                fixture["episode_path"].read_text(encoding="utf-8")
            )["decisions"][0]
            self.assertEqual(roundtripped["q_latest"], expected_q)
            self.assertEqual(
                roundtripped["teacher_probability"],
                expected_teacher_probability,
            )
            self._refresh_manifest_episode(fixture)
            with self.assertRaisesRegex(
                ValueError,
                "latest prior cannot be reproduced",
            ):
                self._train_fixture(fixture)

    def test_trainer_rejects_legacy_ambiguous_manifest_and_trajectory(self):
        for legacy_version in (1, 2, 3, 4):
            with self.subTest(manifest_version=legacy_version):
                with tempfile.TemporaryDirectory() as temporary:
                    fixture = self._make_run(
                        Path(temporary),
                        run_id=f"legacy-manifest-{legacy_version}",
                    )
                    payload = json.loads(
                        fixture["manifest_path"].read_text(encoding="utf-8")
                    )
                    payload["schema_version"] = (
                        f"run-manifest-v{legacy_version}"
                    )
                    fixture["manifest_path"].write_text(
                        json.dumps(payload),
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(
                        ValueError,
                        "unsafe prior run manifest",
                    ):
                        self._train_fixture(fixture)

            with self.subTest(trajectory_version=legacy_version):
                with tempfile.TemporaryDirectory() as temporary:
                    fixture = self._make_run(
                        Path(temporary),
                        run_id=f"legacy-trajectory-{legacy_version}",
                    )
                    episode = json.loads(
                        fixture["episode_path"].read_text(encoding="utf-8")
                    )
                    episode["schema_version"] = (
                        f"trajectory-v{legacy_version}"
                    )
                    publish_clean_episode(
                        fixture["episode_path"],
                        {
                            **episode,
                            "schema_version": TRAJECTORY_SCHEMA_VERSION,
                        },
                    )
                    rewritten = json.loads(
                        fixture["episode_path"].read_text(encoding="utf-8")
                    )
                    rewritten["schema_version"] = (
                        f"trajectory-v{legacy_version}"
                    )
                    fixture["episode_path"].write_text(
                        json.dumps(rewritten),
                        encoding="utf-8",
                    )
                    self._refresh_manifest_episode(fixture)
                    with self.assertRaisesRegex(
                        ValueError,
                        "unsafe prior trajectory",
                    ):
                        self._train_fixture(fixture)

        for legacy_policy_version in (1, 2):
            with self.subTest(policy_version=legacy_policy_version):
                with tempfile.TemporaryDirectory() as temporary:
                    fixture = self._make_run(
                        Path(temporary),
                        run_id=f"legacy-policy-{legacy_policy_version}",
                    )
                    episode = json.loads(
                        fixture["episode_path"].read_text(encoding="utf-8")
                    )
                    episode["decisions"][0]["policy_schema_version"] = (
                        f"residual-policy-v{legacy_policy_version}"
                    )
                    publish_clean_episode(fixture["episode_path"], episode)
                    self._refresh_manifest_episode(fixture)
                    with self.assertRaisesRegex(ValueError, "policy schema"):
                        self._train_fixture(fixture)

    def test_trainer_requires_exactly_one_atomic_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = self._make_run(
                Path(temporary),
                run_id="one-manifest",
            )
            pending = fixture["manifest_path"].parent / "run_manifest.pending.json"
            pending.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly one run manifest"):
                self._train_fixture(fixture)

    def test_post_update_kl_hard_stop_rolls_model_back(self):
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(0)
            with tempfile.TemporaryDirectory() as temporary:
                fixture = self._make_run(
                    Path(temporary),
                    run_id="kl-rollback",
                    seed=10,
                    policy_rng_seed=0,
                )
                report = self._train_fixture(
                    fixture,
                    config=PPOConfig(
                        epochs=1,
                        learning_rate=1.0,
                        entropy_coef=1.0,
                        anchor_kl_target=1e-5,
                        anchor_kl_hard_stop=1e-4,
                    ),
                )
                self.assertTrue(report["stopped_early"])
                self.assertEqual(
                    report["epoch_reports"][-1].get("rolled_back"),
                    1.0,
                )
                original_model, _, _ = load_checkpoint(fixture["checkpoint"])
                output_model, _, _ = load_checkpoint(fixture["output"])
                for name, value in original_model.state_dict().items():
                    self.assertTrue(
                        torch.equal(value, output_model.state_dict()[name]),
                        name,
                    )


if __name__ == "__main__":
    unittest.main()
