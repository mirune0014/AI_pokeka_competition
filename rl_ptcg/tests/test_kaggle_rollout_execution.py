import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rl_ptcg.kaggle_rollout_assets import canonical_sha256
from rl_ptcg.kaggle_rollout_execution import verify_kaggle_rollout_execution


class KaggleRolloutExecutionTests(unittest.TestCase):
    def write_execution(self, workspace: Path, **overrides) -> Path:
        execution = {
            "schema_version": "ptcg_kaggle_rollout_execution.v2",
            "smoke_only": False,
            "asset_manifest_path": "input_asset_manifest.json",
            "asset_manifest_sha256": "asset",
            "engine_output": "runtime_engine",
            "engine_manifest_sha256": "engine",
            "run_manifest_sha256": "run",
            "report_manifest_sha256": "report",
            "rows": 48,
            "shards": 1,
            "run_output": "outputs/run",
        }
        execution.update(overrides)
        execution["manifest_sha256"] = canonical_sha256(execution)
        path = workspace / "kaggle_execution_manifest.json"
        path.write_text(json.dumps(execution), encoding="ascii")
        return path

    def test_verifies_all_bound_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            (workspace / "runtime_engine").mkdir()
            (workspace / "outputs" / "run").mkdir(parents=True)
            path = self.write_execution(workspace)
            with (
                patch(
                    "rl_ptcg.kaggle_rollout_execution.verify_rollout_payload",
                    return_value={"manifest_sha256": "asset"},
                ),
                patch(
                    "rl_ptcg.kaggle_rollout_execution.verify_seeded_engine_linux",
                    return_value={"manifest_sha256": "engine"},
                ),
                patch(
                    "rl_ptcg.kaggle_rollout_execution.verify_oracle_output",
                    return_value={
                        "complete": True, "run_manifest_sha256": "run",
                        "report_manifest_sha256": "report", "rows": 48, "shards": 1,
                        "report_recomputed": True, "current_implementation_drift": [],
                        "current_runtime_drift": [],
                    },
                ),
            ):
                result = verify_kaggle_rollout_execution(path, workspace)
            self.assertTrue(result["verified"])
            self.assertTrue(result["report_recomputed"])

    def test_rejects_run_output_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            path = self.write_execution(workspace, run_output="../outside")
            with (
                patch(
                    "rl_ptcg.kaggle_rollout_execution.verify_rollout_payload",
                    return_value={"manifest_sha256": "asset"},
                ),
                patch(
                    "rl_ptcg.kaggle_rollout_execution.verify_seeded_engine_linux",
                    return_value={"manifest_sha256": "engine"},
                ),
            ):
                with self.assertRaisesRegex(ValueError, "run output escapes"):
                    verify_kaggle_rollout_execution(path, workspace)


if __name__ == "__main__":
    unittest.main()
