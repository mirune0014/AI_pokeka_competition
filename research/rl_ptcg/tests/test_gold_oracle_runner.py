import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from research.rl_ptcg.canonical_actions import canonicalize_prompt_action
from research.rl_ptcg.gold_oracle_runner import (
    GOLD_ORACLE_STATES_SCHEMA_VERSION,
    GOLD_UPPER_TIER_STATES_SCHEMA_VERSION,
    SHARD_SCHEMA_VERSION,
    _engine_descriptor,
    _effective_opponent_policies,
    _policy_descriptor,
    _rollout_scenario_seed,
    _self_hash,
    _semantic_only,
    _write_json_once,
    _weighted_candidate_set_report,
    assert_order_parity,
    canonical_action_from_dict,
    collect_rollout_shards,
    resolve_semantic_candidates,
    semanticize_scenario_values,
    validate_reconstruction_provenance,
    verify_shard,
    verify_state_corpus,
)
from research.rl_ptcg.gold_oracle_states import canonical_sha256


def observation(option_types=(1, 2)):
    return {
        "current": {"yourIndex": 0, "players": [{}, {}]},
        "select": {
            "context": 7,
            "minCount": 1,
            "maxCount": 1,
            "option": [{"type": value} for value in option_types],
        },
    }


def candidate_state():
    original = observation()
    left = canonicalize_prompt_action(original, [0])
    right = canonicalize_prompt_action(original, [1])
    candidates = [
        {
            "semantic_id": left.stable_id,
            "canonical": left.to_dict(),
            "additive_rule_score": 2.0,
            "source_tags": ["baseline"],
        },
        {
            "semantic_id": right.stable_id,
            "canonical": right.to_dict(),
            "additive_rule_score": 1.0,
            "source_tags": ["gold"],
        },
    ]
    sets = {
        "baseline": [left.stable_id],
        "rule_top3": [left.stable_id],
        "rule_topK": [left.stable_id],
        "rule_diverse": [left.stable_id],
        "rule_plus_gold": [left.stable_id, right.stable_id],
    }
    return {
        "state_id": "state",
        "decision_id": "decision",
        "episode_id": "episode",
        "candidates": candidates,
        "candidate_sets": sets,
    }


def upper_tier_state():
    state = candidate_state()
    left, right = state["candidate_sets"]["rule_plus_gold"]
    state["schema_version"] = GOLD_UPPER_TIER_STATES_SCHEMA_VERSION
    state["candidates"][1]["source_tags"] = ["rule_diverse"]
    state["candidate_sets"]["rule_diverse"] = [left, right]
    state["candidate_sets"]["rule_plus_gold"] = [left, right]
    state["gold_incremental"] = False
    state["current_metadata"] = {
        "corpus_role": "upper_tier_state_distribution",
        "recorded_action_role": "provenance_only",
    }
    return state


class GoldOracleRunnerTests(unittest.TestCase):
    def test_structural_population_deduplicates_only_identical_bound_policy(self):
        first = {
            "path": "first", "main_sha256": "main-a", "deck_sha256": "deck-a",
            "auxiliary_files_sha256": {"model.pt": "model-a"},
            "policy_id": "policy-a",
        }
        duplicate = {**first, "path": "duplicate", "policy_id": "policy-b"}
        different_deck = {**first, "path": "other", "deck_sha256": "deck-b", "policy_id": "policy-c"}
        different_model = {
            **first,
            "path": "learned-variant",
            "auxiliary_files_sha256": {"model.pt": "model-b"},
            "policy_id": "policy-d",
        }
        values = [first, duplicate, different_deck, different_model]
        self.assertEqual(values, _effective_opponent_policies(values, "path_distinct_v1"))
        self.assertEqual(
            [first, different_deck, different_model],
            _effective_opponent_policies(values, "structural_unique_v1"),
        )

    def test_common_rollout_stream_excludes_opponent_policy_identity(self):
        continuation = {"policy_id": "continuation"}
        left, right = {"policy_id": "left"}, {"policy_id": "right"}
        common = {"seed": "seed", "rollout_seed_mode": "common_stream_v1"}
        legacy = {"seed": "seed", "rollout_seed_mode": "policy_id_v1"}
        self.assertEqual(
            _rollout_scenario_seed(common, "state", 2, "hyp", left, continuation),
            _rollout_scenario_seed(common, "state", 2, "hyp", right, continuation),
        )
        self.assertNotEqual(
            _rollout_scenario_seed(legacy, "state", 2, "hyp", left, continuation),
            _rollout_scenario_seed(legacy, "state", 2, "hyp", right, continuation),
        )

    def test_common_population_stream_excludes_both_policy_identities(self):
        left, right = {"policy_id": "left"}, {"policy_id": "right"}
        continuation_a = {"policy_id": "continuation-a"}
        continuation_b = {"policy_id": "continuation-b"}
        common = {"seed": "seed", "rollout_seed_mode": "common_population_v2"}
        legacy = {"seed": "seed", "rollout_seed_mode": "common_stream_v1"}
        self.assertEqual(
            _rollout_scenario_seed(common, "state", 2, "hyp", left, continuation_a),
            _rollout_scenario_seed(common, "state", 2, "hyp", right, continuation_b),
        )
        self.assertNotEqual(
            _rollout_scenario_seed(legacy, "state", 2, "hyp", left, continuation_a),
            _rollout_scenario_seed(legacy, "state", 2, "hyp", right, continuation_b),
        )

    def test_policy_descriptor_binds_prompt_ranker_auxiliary_files(self):
        workspace = Path.cwd().resolve()
        with tempfile.TemporaryDirectory(dir=workspace) as directory:
            policy = Path(directory) / "policy"
            snapshot = policy / "source_snapshot" / "model.py"
            snapshot.parent.mkdir(parents=True)
            (policy / "main.py").write_text("def agent(obs): return []\n", encoding="ascii")
            (policy / "deck.csv").write_text("1\n", encoding="ascii")
            (policy / "model.pt").write_bytes(b"model")
            (policy / "report.json").write_text("{}\n", encoding="ascii")
            snapshot.write_text("model source\n", encoding="ascii")
            (policy / "gold_prompt_ranker_manifest.json").write_text(json.dumps({
                "checkpoint": "model.pt",
                "evaluation_report": "report.json",
                "implementation": {"model": {"snapshot": "source_snapshot/model.py"}},
            }), encoding="ascii")
            descriptor = _policy_descriptor(policy, workspace)
            self.assertEqual(
                {
                    "gold_prompt_ranker_manifest.json", "model.pt", "report.json",
                    "source_snapshot/model.py",
                },
                set(descriptor["auxiliary_files_sha256"]),
            )

    def test_canonical_action_dict_round_trip(self):
        action = canonicalize_prompt_action(observation(), [1])
        self.assertEqual(action, canonical_action_from_dict(action.to_dict()))

    def test_semantic_candidates_resolve_after_option_permutation(self):
        state = candidate_state()
        raw, mapping, baseline = resolve_semantic_candidates(
            observation((2, 1)), state, "rule_plus_gold",
        )
        self.assertEqual([[1], [0]], raw)
        self.assertEqual(state["candidate_sets"]["baseline"][0], baseline)
        self.assertEqual(
            set(state["candidate_sets"]["rule_plus_gold"]), set(mapping.values()),
        )

    def test_semanticize_discards_raw_action_coordinates(self):
        state = candidate_state()
        left, right = state["candidate_sets"]["rule_plus_gold"]
        rows = semanticize_scenario_values(
            [
                {"particle_index": 0, "hidden_world_id": "world", "action": [0], "terminal_utility": 1},
                {"particle_index": 0, "hidden_world_id": "world", "action": [1], "terminal_utility": -1},
            ],
            {(0,): left, (1,): right},
            state=state,
            batch_id=0,
            hypothesis={"signature": "hyp", "kind": "known", "posterior_mass": 1.0},
            policy_index=0,
            policy_id="policy",
            continuation_index=0,
            continuation_id="continuation",
            scenario_weight=1.0,
        )
        self.assertEqual([left, right], [row["action"] for row in rows])
        _semantic_only(rows)
        self.assertNotIn("raw_action", repr(rows))

    def test_order_parity_is_fail_closed(self):
        rows = [{
            "hypothesis_signature": "hyp",
            "opponent_policy_index": 0,
            "continuation_policy_index": 0,
            "particle_index": 0,
            "action": "a",
            "terminal_utility": 1.0,
        }]
        assert_order_parity(rows, list(reversed(rows)))
        changed = copy.deepcopy(rows)
        changed[0]["terminal_utility"] = -1.0
        with self.assertRaisesRegex(ValueError, "terminal_utility"):
            assert_order_parity(rows, changed)

    def test_gold_reconstruction_requires_recorded_action_as_gold_candidate(self):
        state = candidate_state()
        state["schema_version"] = GOLD_ORACLE_STATES_SCHEMA_VERSION
        left, right = state["candidate_sets"]["rule_plus_gold"]
        validate_reconstruction_provenance(state, right)
        with self.assertRaisesRegex(ValueError, "recorded Gold action"):
            validate_reconstruction_provenance(state, left)

    def test_upper_tier_reconstruction_never_promotes_recorded_action(self):
        state = upper_tier_state()
        validate_reconstruction_provenance(state, "recorded-action-not-in-candidates")
        state["candidates"][1]["source_tags"] = ["gold"]
        with self.assertRaisesRegex(ValueError, "forbidden Gold"):
            validate_reconstruction_provenance(state, "recorded-action-not-in-candidates")

    def test_state_corpus_verifier_dispatches_by_manifest_schema(self):
        workspace = Path.cwd().resolve()
        with tempfile.TemporaryDirectory(dir=workspace) as directory:
            corpus = Path(directory)
            (corpus / "manifest.json").write_text(json.dumps({
                "schema_version": GOLD_UPPER_TIER_STATES_SCHEMA_VERSION,
            }), encoding="ascii")
            with mock.patch(
                "research.rl_ptcg.gold_oracle_runner.verify_gold_upper_tier_states",
                return_value={"verified": True, "states": 3},
            ) as verifier:
                result = verify_state_corpus(corpus, workspace)
            verifier.assert_called_once_with(corpus.resolve(), workspace)
            self.assertEqual(GOLD_UPPER_TIER_STATES_SCHEMA_VERSION, result["schema_version"])
            self.assertEqual(str(corpus.resolve()), result["output_dir"])

    def test_state_corpus_verifier_rejects_unknown_schema(self):
        workspace = Path.cwd().resolve()
        with tempfile.TemporaryDirectory(dir=workspace) as directory:
            corpus = Path(directory)
            (corpus / "manifest.json").write_text(
                '{"schema_version":"unknown"}', encoding="ascii",
            )
            with self.assertRaisesRegex(ValueError, "unsupported state corpus"):
                verify_state_corpus(corpus, workspace)

    def test_atomic_json_write_is_idempotent_and_write_once(self):
        workspace = Path.cwd().resolve()
        with tempfile.TemporaryDirectory(dir=workspace) as directory:
            path = Path(directory) / "artifact.json"
            _write_json_once(path, {"second": 2, "first": 1})
            original = path.read_bytes()
            self.assertTrue(original.endswith(b"\n"))
            _write_json_once(path, {"first": 1, "second": 2})
            self.assertEqual(original, path.read_bytes())
            self.assertFalse(list(path.parent.glob(".*.tmp")))
            with self.assertRaisesRegex(FileExistsError, "non-identical"):
                _write_json_once(path, {"first": 99, "second": 2})

    def test_collect_rollout_shards_verifies_present_and_reports_missing(self):
        state, manifest, shard = self.make_shard()
        manifest["state_ids"] = ["state"]
        manifest["batch_ids"] = [0, 1]
        workspace = Path.cwd().resolve()
        with tempfile.TemporaryDirectory(dir=workspace) as directory:
            output = Path(directory)
            path = output / "shards" / "state" / "batch_000.json"
            _write_json_once(path, shard)
            shards, missing = collect_rollout_shards(
                output, {"state": state}, manifest,
            )
            self.assertEqual(1, len(shards))
            self.assertEqual([("state", 1)], missing)
            path.write_text("{}\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "self-hash"):
                collect_rollout_shards(output, {"state": state}, manifest)

    def test_engine_descriptor_binds_linux_binary_and_python_wrappers(self):
        workspace = Path.cwd().resolve()
        with tempfile.TemporaryDirectory(dir=workspace) as directory:
            engine = Path(directory) / "engine"
            cg = engine / "cg"
            cg.mkdir(parents=True)
            for name, data in {
                "__init__.py": b"",
                "api.py": b"api\n",
                "sim.py": b"sim\n",
                "game.py": b"game\n",
                "utils.py": b"utils\n",
                "libcg.so": b"linux-binary",
                "cg.dll": b"windows-binary",
            }.items():
                (cg / name).write_bytes(data)
            with mock.patch("research.rl_ptcg.gold_oracle_runner.platform.system", return_value="Linux"):
                descriptor = _engine_descriptor(engine, workspace)
            self.assertEqual("libcg.so", descriptor["binary_name"])
            self.assertEqual(
                {"__init__.py", "api.py", "sim.py", "game.py", "utils.py"},
                set(descriptor["python_files_sha256"]),
            )
            self.assertEqual(
                descriptor,
                _engine_descriptor(engine, workspace, expected=descriptor),
            )

    def test_engine_descriptor_preserves_legacy_dll_binding(self):
        workspace = Path.cwd().resolve()
        with tempfile.TemporaryDirectory(dir=workspace) as directory:
            engine = Path(directory) / "engine"
            cg = engine / "cg"
            cg.mkdir(parents=True)
            (cg / "api.py").write_text("api\n", encoding="ascii")
            (cg / "cg.dll").write_bytes(b"windows-binary")
            expected = _engine_descriptor(engine, workspace)
            legacy = {
                "path": expected["path"],
                "api_sha256": expected["api_sha256"],
                "dll_sha256": expected["binary_sha256"],
            }
            self.assertEqual(
                legacy, _engine_descriptor(engine, workspace, expected=legacy),
            )

    def make_shard(self):
        state = candidate_state()
        left, right = state["candidate_sets"]["rule_plus_gold"]
        rows = []
        for action, utility in ((left, -1.0), (right, 1.0)):
            rows.append({
                "state_id": "state",
                "decision_id": "decision",
                "episode_id": "episode",
                "batch_id": 0,
                "baseline_action": left,
                "particle_index": 0,
                "opponent_policy_index": "policy",
                "continuation_policy_index": "continuation",
                "hypothesis_signature": "hyp",
                "hypothesis_kind": "known",
                "posterior_mass": 1.0,
                "scenario_weight": 1.0,
                "hidden_world_id": "world",
                "action": action,
                "outside_rule_top3": action == right,
                "terminal_utility": utility,
            })
        manifest = {
            "manifest_sha256": "run",
            "config": {
                "candidate_mode": "named_set",
                "candidate_set": "rule_plus_gold",
                "candidate_selection": None,
                "particles_per_scenario": 1,
            },
        }
        shard = {
            "schema_version": SHARD_SCHEMA_VERSION,
            "run_manifest_sha256": "run",
            "state_id": "state",
            "decision_id": "decision",
            "episode_id": "episode",
            "batch_id": 0,
            "candidate_set": "rule_plus_gold",
            "candidate_ids": [left, right],
            "candidate_memberships": {
                left: ["baseline", "rule_top3", "rule_topK", "rule_diverse", "rule_plus_gold"],
                right: ["rule_plus_gold"],
            },
            "baseline_action": left,
            "scenario_count": 1,
            "particles_per_scenario": 1,
            "forward_reverse_parity": True,
            "rows_sha256": canonical_sha256(rows),
            "rows": rows,
        }
        shard["manifest_sha256"] = _self_hash(shard)
        return state, manifest, shard

    def test_shard_verifier_checks_pairing_and_weights(self):
        state, manifest, shard = self.make_shard()
        verify_shard(shard, state, manifest)
        broken = copy.deepcopy(shard)
        broken["rows"][1]["scenario_weight"] = 0.5
        broken["rows_sha256"] = canonical_sha256(broken["rows"])
        broken["manifest_sha256"] = _self_hash(broken)
        with self.assertRaisesRegex(ValueError, "scenario weight"):
            verify_shard(broken, state, manifest)

    def test_shard_verifier_accepts_explicit_candidate_selection(self):
        state, manifest, shard = self.make_shard()
        left, right = shard["candidate_ids"]
        manifest["config"] = {
            "candidate_mode": "explicit_selection",
            "candidate_set": "explicit_selection",
            "particles_per_scenario": 1,
            "candidate_selection": {
                "states": {
                    "state": {
                        "candidate_ids": [left, right],
                        "baseline_action": left,
                        "rule_comparator_action": left,
                        "gold_action": right,
                    },
                },
            },
        }
        shard["candidate_set"] = "explicit_selection"
        shard["manifest_sha256"] = _self_hash(shard)
        verify_shard(shard, state, manifest)

    def test_weighted_candidate_set_report_finds_gold_increment(self):
        state, _manifest, shard = self.make_shard()
        report = _weighted_candidate_set_report(shard["rows"], {"state": state})
        self.assertEqual(1, report["positive_gap_units"])
        self.assertEqual(2.0, report["mean_rule_plus_gold_gap_vs_rule_diverse"])


if __name__ == "__main__":
    unittest.main()
