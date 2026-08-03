from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.rl_ptcg.kaggle_rollout_assets import canonical_sha256
from research.rl_ptcg.kaggle_rollout_source_receipt import (
    build_kaggle_rollout_source_receipt, verify_kaggle_rollout_source_receipt,
)


class KaggleRolloutSourceReceiptTests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path, Path, dict]:
        execution = {"schema_version": "ptcg_kaggle_rollout_execution.v2", "run_output": "oracle",
                     "run_manifest_sha256": "run", "report_manifest_sha256": "report", "rows": 12, "shards": 2}
        execution["manifest_sha256"] = canonical_sha256(execution)
        execution_path = root / "ptcg_gold_workspace" / "execution.json"
        execution_path.parent.mkdir()
        execution_path.write_text(json.dumps(execution, sort_keys=True) + "\n", encoding="ascii")
        event = {"verified": True, "report_recomputed": True, "runtime_drift": [], "implementation_drift": [],
                 "execution_manifest_sha256": execution["manifest_sha256"], "run_manifest_sha256": "run",
                 "report_manifest_sha256": "report", "rows": 12, "shards": 2}
        log = root / "kaggle.log"
        asset = {"verified": True, "asset_manifest_sha256": "asset", "note": "not canonical on purpose"}
        engine = {"verified": True, "engine_manifest_sha256": "engine"}
        corpus = {"verified": True, "corpus_manifest_sha256": "corpus"}
        log.write_text(json.dumps([
            {"stream_name": "stdout", "data": json.dumps(asset)},
            {"stream_name": "stdout", "data": json.dumps(engine, sort_keys=True, separators=(",", ":"))},
            {"stream_name": "stdout", "data": json.dumps(corpus, sort_keys=True, separators=(",", ":"))},
            {"stream_name": "stdout", "data": json.dumps(event, sort_keys=True, separators=(",", ":"))},
        ]), encoding="utf-8")
        receipt = root  / "_local_generated" / "analysis_outputs" / "gold_replay_phase3" / "receipt.json"
        return execution_path, log, receipt, event

    def _local(self, execution: dict, *, runtime_drift: list[str] | None = None) -> dict:
        return {"verified": True, "execution_manifest_sha256": execution["manifest_sha256"],
                "run_manifest_sha256": "run", "report_manifest_sha256": "report", "rows": 12, "shards": 2,
                "report_recomputed": not bool(runtime_drift), "runtime_drift": runtime_drift or [],
                "implementation_drift": []}

    def _build(self, execution_path: Path, log: Path, receipt: Path, local: dict) -> dict:
        with patch("research.rl_ptcg.kaggle_rollout_source_receipt.verify_kaggle_rollout_execution", return_value=local):
            return build_kaggle_rollout_source_receipt(execution_path, log, receipt, workspace_root=execution_path.parents[1])

    def test_success_and_local_runtime_drift_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            execution_path, log, receipt, _event = self._fixture(Path(directory))
            execution = json.loads(execution_path.read_text(encoding="ascii"))
            result = self._build(execution_path, log, receipt, self._local(execution, runtime_drift=["platform"]))
            self.assertTrue(result["verified"])

    def test_rejects_forged_multiple_and_mismatched_event(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); execution_path, log, receipt, event = self._fixture(root)
            execution = json.loads(execution_path.read_text(encoding="ascii"))
            forged = dict(event); forged["report_recomputed"] = False
            log.write_text(json.dumps([{"stream_name": "stdout", "data": json.dumps(forged, sort_keys=True, separators=(",", ":"))}]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                self._build(execution_path, log, receipt, self._local(execution))
            log.write_text(json.dumps([{"stream_name": "stdout", "data": json.dumps(event, sort_keys=True, separators=(",", ":"))}, {"stream_name": "stdout", "data": json.dumps(event, sort_keys=True, separators=(",", ":"))}]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly one"):
                self._build(execution_path, log, receipt, self._local(execution))
            wrong = dict(event); wrong["rows"] = 99
            log.write_text(json.dumps([{"stream_name": "stdout", "data": json.dumps(wrong, sort_keys=True, separators=(",", ":"))}]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "rows"):
                self._build(execution_path, log, receipt, self._local(execution))

    def test_rejects_receipt_input_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            execution_path, log, receipt, _event = self._fixture(Path(directory))
            execution = json.loads(execution_path.read_text(encoding="ascii"))
            self._build(execution_path, log, receipt, self._local(execution))
            log.write_text("[]", encoding="utf-8")
            with patch("research.rl_ptcg.kaggle_rollout_source_receipt.verify_kaggle_rollout_execution", return_value=self._local(execution)):
                with self.assertRaisesRegex(ValueError, "input hash drift"):
                    verify_kaggle_rollout_source_receipt(receipt, workspace_root=execution_path.parents[1])


if __name__ == "__main__":
    unittest.main()
