import unittest
import json
from pathlib import Path
import tempfile

from rl_ptcg.kaggle_rollout_assets import _forbidden, _policy_sources


class KaggleRolloutAssetsTests(unittest.TestCase):
    def test_engine_and_secret_paths_are_forbidden(self):
        for path in (
            "baseline/cg/cg.dll", "engine/libcg.so", "external/ptcg_engine/Api.h",
            "secrets/kaggle.json", ".env", "build/Export.cpp", "x/__pycache__/a.pyc",
        ):
            self.assertTrue(_forbidden(path), path)

    def test_runtime_python_and_policy_files_are_allowed(self):
        for path in (
            "rl_ptcg/gold_oracle_runner.py", "tools/ptcg_common.py",
            "meta_agents/alakazam/main.py", "meta_agents/alakazam/deck.csv",
        ):
            self.assertFalse(_forbidden(path), path)

    def test_policy_sources_include_manifest_bound_model_files(self):
        with tempfile.TemporaryDirectory() as directory:
            policy = Path(directory)
            snapshot = policy / "source_snapshot" / "model.py"
            snapshot.parent.mkdir()
            for path in (policy / "main.py", policy / "deck.csv", policy / "model.pt", policy / "report.json", snapshot):
                path.write_bytes(b"x")
            (policy / "gold_prompt_ranker_manifest.json").write_text(json.dumps({
                "checkpoint": "model.pt",
                "evaluation_report": "report.json",
                "implementation": {"model": {"snapshot": "source_snapshot/model.py"}},
            }), encoding="ascii")
            self.assertEqual(
                {
                    "main.py", "deck.csv", "model.pt", "report.json",
                    "gold_prompt_ranker_manifest.json", "source_snapshot/model.py",
                },
                {str(path.relative_to(policy)).replace("\\", "/") for path in _policy_sources(policy)},
            )


if __name__ == "__main__":
    unittest.main()
