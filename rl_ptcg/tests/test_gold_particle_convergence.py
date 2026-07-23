import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rl_ptcg.gold_oracle_runner import stable_seed
from rl_ptcg.gold_oracle_statistics import summarize_gold_oracle
from rl_ptcg.gold_particle_convergence import (
    PROJECTED_SCHEMA_VERSION,
    compare_row_reuse,
    verify_particle_convergence,
    write_particle_convergence,
)


class GoldParticleConvergenceTests(unittest.TestCase):
    def row(self, particle, utility):
        return {
            "state_id": "state", "batch_id": 0, "action": "action",
            "particle_index": particle, "hidden_world_id": "world-%d" % particle,
            "scenario_weight": 1.0, "terminal_utility": utility,
        }

    def test_lower_particles_are_exact_subset(self):
        lower = [self.row(0, -1.0), self.row(1, 1.0)]
        higher = lower + [self.row(2, 1.0), self.row(3, -1.0)]
        result = compare_row_reuse(lower, higher)
        self.assertTrue(result["lower_is_subset"])
        self.assertEqual(2, result["shared_rows"])
        self.assertEqual(0, result["shared_utility_mismatches"])

    def test_shared_utility_change_is_detected(self):
        lower = [self.row(0, -1.0)]
        higher = [copy.deepcopy(lower[0])]
        higher[0]["terminal_utility"] = 1.0
        result = compare_row_reuse(lower, higher)
        self.assertTrue(result["lower_is_subset"])
        self.assertEqual(1, result["shared_utility_mismatches"])


class ProjectedGoldParticleConvergenceTests(unittest.TestCase):
    policy_ids = ["policy-a", "policy-b", "policy-c"]

    def _write_json(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")), encoding="ascii")

    def _state(self):
        return {
            "state_id": "state", "decision_id": "decision", "episode_id": "episode",
            "belief": {"archetype": "archetype"},
            "candidate_sets": {
                "baseline": ["baseline"], "rule_diverse": ["baseline"],
                "rule_plus_gold": ["baseline", "gold"],
            },
        }

    def _rows(self, particles, *, policy_ids=None, divergent_nonprojected=False, bad_weight=False):
        policies = self.policy_ids if policy_ids is None else policy_ids
        rows = []
        for batch_id in range(2):
            for policy in policies:
                for particle in range(particles):
                    for action, utility in (("baseline", -0.2), ("gold", 0.4)):
                        if divergent_nonprojected and policy != "policy-b" and action == "gold":
                            utility = -0.9
                        weight = 0.6 / len(policies)
                        if bad_weight and policy == policies[0]:
                            weight = 0.1
                        rows.append({
                            "state_id": "state", "batch_id": batch_id, "action": action,
                            "baseline_action": "baseline", "hypothesis_signature": "hypothesis",
                            "opponent_policy_index": policy, "continuation_policy_index": "continuation",
                            "particle_index": particle, "hidden_world_id": "world-%d" % particle,
                            "posterior_mass": 0.6, "scenario_weight": weight,
                            "terminal_utility": utility,
                        })
        return rows

    def _make_level(self, root, label, particles, *, policy_ids=None, **row_options):
        workspace = root / ("source_" + label)
        run = workspace / "runs" / label
        state = self._state()
        self._write_json(workspace / "corpus" / "states.jsonl", state)
        policies = self.policy_ids if policy_ids is None else policy_ids
        rows = self._rows(particles, policy_ids=policies, **row_options)
        config = {
            "particles_per_scenario": particles, "max_rollout_steps": 8,
            "candidate_set": "rule_plus_gold", "seed": "seed", "bootstrap_repetitions": 2,
            "opponent_population_mode": "path_distinct_v1", "rollout_seed_mode": "policy_id_v1",
        }
        manifest = {
            "manifest_sha256": "run-" + label, "corpus": {"path": "corpus", "manifest_sha256": "corpus"},
            "config": config, "state_ids": ["state"], "batch_ids": [0, 1],
            "baseline": {"policy_id": "baseline"}, "continuation_policies": [{"policy_id": "continuation"}],
            "opponent_policies": {"archetype": [{"policy_id": policy} for policy in policies]},
            "engine": {"binary_sha256": "engine"}, "implementation": {"impl": {"source_sha256": "impl"}},
        }
        statistics = summarize_gold_oracle(
            rows, {"state": state}, bootstrap_repetitions=2,
            bootstrap_seed=stable_seed("seed", "posterior-bootstrap"),
        )
        report = {"manifest_sha256": "report-" + label, "posterior_weighted_teacher_statistics": statistics}
        self._write_json(run / "run_manifest.json", manifest)
        self._write_json(run / "report.json", report)
        for batch_id in range(2):
            self._write_json(run / "shards" / "state" / ("batch_%03d.json" % batch_id), {
                "candidate_ids": ["baseline", "gold"],
                "rows": [row for row in rows if row["batch_id"] == batch_id],
            })
        return run, workspace

    def _selection(self, root):
        path = root / "selection.json"
        self._write_json(path, {"states": [{
            "state_id": "state", "episode_id": "episode", "selected": True,
            "best_nonbaseline": {"action": "gold"},
        }]})
        return path

    def _verified(self, _run, _workspace):
        return {"complete": True, "rows": 1, "shards": 2}

    def _selection_verified(self, _path, _workspace):
        return {"manifest_sha256": "selection"}

    def _write_projection(self, root, *, lower_options=None, higher_options=None):
        lower, lower_workspace = self._make_level(root, "p16", 16, **(lower_options or {}))
        higher, higher_workspace = self._make_level(
            root, "p32", 32, policy_ids=["policy-b"], **(higher_options or {}),
        )
        selection = self._selection(root)
        output = root / "projected.json"
        with patch("rl_ptcg.gold_particle_convergence.verify_oracle_output", self._verified), patch(
            "rl_ptcg.gold_particle_convergence.verify_refinement_selection", self._selection_verified,
        ):
            value = write_particle_convergence(
                [("p16", lower, lower_workspace), ("p32", higher, higher_workspace)],
                selection, output, root, project_opponent_policy_id="policy-b",
            )
            verified = verify_particle_convergence(output, root)
        return value, verified

    def test_projects_exact_three_policy_p16_to_one_policy_p32_subset(self):
        with tempfile.TemporaryDirectory() as directory:
            value, verified = self._write_projection(Path(directory))
        self.assertEqual(PROJECTED_SCHEMA_VERSION, value["schema_version"])
        self.assertEqual("policy-b", value["projection"]["opponent_policy_id"])
        self.assertEqual("policy-b", value["shared_config"]["projected_opponent_policy_id"])
        self.assertNotIn("opponent_policy_ids", value["shared_config"])
        self.assertEqual([16, 32], [level["particles_per_scenario"] for level in value["target_levels"]])
        self.assertTrue(value["all_lower_rows_reused_exactly"])
        self.assertEqual(64, value["adjacent_row_reuse"][0]["batches"][0]["lower_rows"] + value["adjacent_row_reuse"][0]["batches"][1]["lower_rows"])
        self.assertEqual(128, value["adjacent_row_reuse"][0]["batches"][0]["higher_rows"] + value["adjacent_row_reuse"][0]["batches"][1]["higher_rows"])
        self.assertEqual(64, value["adjacent_row_reuse"][0]["shared_rows"])
        self.assertEqual(
            [["policy-a", "policy-b", "policy-c"], ["policy-b"]],
            [audit["effective_policy_ids"] for audit in value["source_population_audit"]],
        )
        self.assertEqual([3, 1], [audit["effective_policy_count"] for audit in value["source_population_audit"]])
        self.assertEqual([3, 1], [audit["expected_original_scenario_weight_denominator"] for audit in value["source_population_audit"]])
        self.assertEqual([64, 128], [audit["projected_rows"] for audit in value["source_population_audit"]])
        self.assertTrue(verified["verified"])

    def test_rejects_missing_policy_malformed_weight_and_config_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lower, lower_workspace = self._make_level(root, "p16", 16)
            higher, higher_workspace = self._make_level(root, "p32", 32, bad_weight=True)
            selection = self._selection(root)
            with patch("rl_ptcg.gold_particle_convergence.verify_oracle_output", self._verified), patch(
                "rl_ptcg.gold_particle_convergence.verify_refinement_selection", self._selection_verified,
            ):
                with self.assertRaisesRegex(ValueError, "scenario weights"):
                    write_particle_convergence([("p16", lower, lower_workspace), ("p32", higher, higher_workspace)], selection, root / "bad.json", root, project_opponent_policy_id="policy-b")
                manifest_path = higher / "run_manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="ascii"))
                for path in (lower / "run_manifest.json", manifest_path):
                    population_manifest = json.loads(path.read_text(encoding="ascii"))
                    population_manifest["opponent_policies"]["archetype"] = [{"policy_id": "policy-a"}]
                    self._write_json(path, population_manifest)
                with self.assertRaisesRegex(ValueError, "exactly once"):
                    write_particle_convergence([("p16", lower, lower_workspace), ("p32", higher, higher_workspace)], selection, root / "missing.json", root, project_opponent_policy_id="policy-b")
                lower_manifest_path = lower / "run_manifest.json"
                lower_manifest = json.loads(lower_manifest_path.read_text(encoding="ascii"))
                lower_manifest["opponent_policies"]["archetype"] = [{"policy_id": policy} for policy in self.policy_ids]
                self._write_json(lower_manifest_path, lower_manifest)
                manifest["opponent_policies"]["archetype"] = [{"policy_id": policy} for policy in self.policy_ids]
                manifest["config"]["rollout_seed_mode"] = "common_stream_v1"
                self._write_json(manifest_path, manifest)
                with self.assertRaisesRegex(ValueError, "semantic configuration"):
                    write_particle_convergence([("p16", lower, lower_workspace), ("p32", higher, higher_workspace)], selection, root / "drift.json", root, project_opponent_policy_id="policy-b")

    def test_nonprojected_heads_do_not_change_target_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, _ = self._write_projection(root / "baseline")
            divergent, _ = self._write_projection(root / "divergent", lower_options={"divergent_nonprojected": True})
        self.assertEqual(baseline["target_levels"], divergent["target_levels"])

    def test_v1_artifact_remains_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lower, lower_workspace = self._make_level(root, "p16", 16)
            higher, higher_workspace = self._make_level(root, "p32", 32)
            selection = self._selection(root)
            with patch("rl_ptcg.gold_particle_convergence.verify_oracle_output", self._verified), patch(
                "rl_ptcg.gold_particle_convergence.verify_refinement_selection", self._selection_verified,
            ):
                value = write_particle_convergence([("p16", lower, lower_workspace), ("p32", higher, higher_workspace)], selection, root / "v1.json", root)
                verified = verify_particle_convergence(root / "v1.json", root)
        self.assertEqual("gold_particle_convergence.v1", value["schema_version"])
        self.assertTrue(verified["verified"])


if __name__ == "__main__":
    unittest.main()
