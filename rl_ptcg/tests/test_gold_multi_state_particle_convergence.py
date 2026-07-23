import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rl_ptcg.gold_multi_state_particle_convergence import (
    SCHEMA_VERSION,
    verify_multi_state_particle_convergence,
    write_multi_state_particle_convergence,
)


class GoldMultiStateParticleConvergenceTests(unittest.TestCase):
    state_ids = ["state-a", "state-b"]
    actions = {"state-a": "action-a", "state-b": "action-b"}
    statistics_path = "rl_ptcg/gold_oracle_statistics.py"

    def _write_json(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True), encoding="ascii")

    def _selection(self, root):
        path = root / "selection.json"
        states = [{
            "state_id": state_id,
            "episode_id": "episode-" + state_id,
            "selected": True,
            "batch_ids": [0, 1],
            "best_nonbaseline": {"action": self.actions[state_id]},
        } for state_id in self.state_ids]
        self._write_json(path, {
            "manifest_sha256": "selection-manifest",
            "selected_count": len(states),
            "next_run": {"state_ids": list(self.state_ids)},
            "states": states,
        })
        return path

    def _level(self, root, label, particles, *, common_hash="common", utility_mismatch=False):
        workspace = root / (label + "-workspace")
        run = workspace / "run"
        manifest = {
            "manifest_sha256": "manifest-" + label,
            "config": {
                "particles_per_scenario": particles,
                "seed": "seed",
                "candidate_set": "rule_diverse",
                "max_rollout_steps": 1000,
                "bootstrap_repetitions": 10,
                "opponent_population_mode": "structural_unique_v1",
                "rollout_seed_mode": "common_stream_v1",
            },
            "batch_ids": [0, 1],
            "state_ids": list(self.state_ids) + (["screen-only"] if particles == 8 else []),
            "baseline": {"policy_id": "baseline"},
            "continuation_policies": [{"policy_id": "continuation"}],
            "opponent_policies": {"marnie": [{"policy_id": "opponent"}]},
            "corpus": {"manifest_sha256": "corpus"},
            "engine": {"binary_sha256": "engine"},
            "implementation": {
                "common.py": {"source_sha256": common_hash},
                self.statistics_path: {
                    "source_sha256": "statistics-old" if particles == 8 else "statistics-new"
                },
            },
        }
        units = []
        for state_id in self.state_ids:
            action = self.actions[state_id]
            for batch_id in [0, 1]:
                units.append({
                    "state_id": state_id,
                    "batch_id": batch_id,
                    "oracle_action": action,
                    "actions": {action: {
                        "advantage_win_probability": 0.1 + particles / 100.0,
                        "one_sided_lcb90_win_probability": 0.01,
                    }},
                })
                rows = []
                for particle in range(particles):
                    utility = float((particle + batch_id) % 2)
                    if utility_mismatch and particles == 16 and particle == 0:
                        utility = 1.0 - utility
                    rows.append({
                        "state_id": state_id,
                        "batch_id": batch_id,
                        "particle": particle,
                        "candidate_id": action,
                        "terminal_utility": utility,
                    })
                self._write_json(run / "shards" / state_id / ("batch_%03d.json" % batch_id), {
                    "candidate_ids": ["baseline", action],
                    "rows": rows,
                })
        report = {
            "manifest_sha256": "report-" + label,
            "posterior_weighted_teacher_statistics": {"per_state_batch": units},
        }
        self._write_json(run / "run_manifest.json", manifest)
        self._write_json(run / "report.json", report)
        return run, workspace

    @staticmethod
    def _verified(run, _workspace):
        manifest = json.loads((Path(run) / "run_manifest.json").read_text(encoding="ascii"))
        return {
            "complete": True,
            "rows": int(manifest["config"]["particles_per_scenario"]) * 4,
            "shards": 4,
        }

    @staticmethod
    def _selection_verified(_path, _workspace):
        return {"manifest_sha256": "selection-manifest"}

    def test_builds_and_reproduces_two_state_nested_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p8, p8_workspace = self._level(root, "p8", 8)
            p16, p16_workspace = self._level(root, "p16", 16)
            selection = self._selection(root)
            output = root / "audit.json"
            with patch(
                "rl_ptcg.gold_multi_state_particle_convergence.verify_oracle_output",
                self._verified,
            ), patch(
                "rl_ptcg.gold_multi_state_particle_convergence.verify_refinement_selection",
                self._selection_verified,
            ):
                value = write_multi_state_particle_convergence(
                    [("p8", p8, p8_workspace), ("p16", p16, p16_workspace)],
                    selection,
                    output,
                    root,
                    allowed_implementation_drift=[self.statistics_path],
                )
                verified = verify_multi_state_particle_convergence(output, root)
        self.assertEqual(SCHEMA_VERSION, value["schema_version"])
        self.assertEqual(2, value["selected_state_count"])
        self.assertTrue(value["all_lower_rows_reused_exactly"])
        self.assertEqual(32, value["adjacent_row_reuse"][0]["shared_rows"])
        self.assertEqual([8, 16], [item["particles_per_scenario"] for item in value["runs"]])
        self.assertEqual({self.statistics_path}, set(value["allowed_implementation_drift"]))
        self.assertTrue(verified["verified"])

    def test_rejects_unlisted_or_unused_implementation_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p8, p8_workspace = self._level(root, "p8", 8)
            p16, p16_workspace = self._level(root, "p16", 16, common_hash="changed")
            selection = self._selection(root)
            with patch(
                "rl_ptcg.gold_multi_state_particle_convergence.verify_oracle_output",
                self._verified,
            ), patch(
                "rl_ptcg.gold_multi_state_particle_convergence.verify_refinement_selection",
                self._selection_verified,
            ):
                with self.assertRaisesRegex(ValueError, "allowlist"):
                    write_multi_state_particle_convergence(
                        [("p8", p8, p8_workspace), ("p16", p16, p16_workspace)],
                        selection,
                        root / "unexpected.json",
                        root,
                        allowed_implementation_drift=[self.statistics_path],
                    )
                with self.assertRaisesRegex(ValueError, "allowlist"):
                    write_multi_state_particle_convergence(
                        [("p8", p8, p8_workspace), ("p16", p16, p16_workspace)],
                        selection,
                        root / "unused.json",
                        root,
                        allowed_implementation_drift=[self.statistics_path, "unused.py", "common.py"],
                    )

    def test_records_utility_mismatch_as_failed_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            p8, p8_workspace = self._level(root, "p8", 8)
            p16, p16_workspace = self._level(root, "p16", 16, utility_mismatch=True)
            selection = self._selection(root)
            with patch(
                "rl_ptcg.gold_multi_state_particle_convergence.verify_oracle_output",
                self._verified,
            ), patch(
                "rl_ptcg.gold_multi_state_particle_convergence.verify_refinement_selection",
                self._selection_verified,
            ):
                value = write_multi_state_particle_convergence(
                    [("p8", p8, p8_workspace), ("p16", p16, p16_workspace)],
                    selection,
                    root / "mismatch.json",
                    root,
                    allowed_implementation_drift=[self.statistics_path],
                )
        self.assertFalse(value["all_lower_rows_reused_exactly"])
        self.assertEqual(4, value["adjacent_row_reuse"][0]["shared_utility_mismatches"])


if __name__ == "__main__":
    unittest.main()
