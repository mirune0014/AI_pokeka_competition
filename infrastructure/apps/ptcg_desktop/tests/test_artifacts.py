from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from ptcg_desktop.artifacts import MANIFEST_ID, TRUSTED_FILES, cleanup_stale_staging, verify_artifact


class ArtifactTests(unittest.TestCase):
    def test_stale_staging_cleanup_only_removes_old_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            old_stage = root / "old-match"
            fresh_stage = root / "fresh-match"
            old_stage.mkdir()
            fresh_stage.mkdir()
            (old_stage / "marker").write_text("old", encoding="utf-8")
            (fresh_stage / "marker").write_text("fresh", encoding="utf-8")
            os.utime(old_stage, (100.0, 100.0))
            os.utime(fresh_stage, (900.0, 900.0))
            removed = cleanup_stale_staging(root=root, max_age_seconds=200.0, now=1000.0)
            self.assertEqual(removed, (old_stage,))
            self.assertFalse(old_stage.exists())
            self.assertTrue(fresh_stage.exists())

    @unittest.skipUnless(os.environ.get("PTCG_SUBMISSION_ARTIFACT"), "set PTCG_SUBMISSION_ARTIFACT for exact artifact tests")
    def test_exact_artifact_verifies(self) -> None:
        report = verify_artifact(os.environ["PTCG_SUBMISSION_ARTIFACT"])
        self.assertTrue(report.verified, report.issues)
        self.assertEqual(report.manifest_id, MANIFEST_ID)

    @unittest.skipUnless(os.environ.get("PTCG_SUBMISSION_ARTIFACT"), "set PTCG_SUBMISSION_ARTIFACT for exact artifact tests")
    def test_one_byte_change_is_rejected(self) -> None:
        source = Path(os.environ["PTCG_SUBMISSION_ARTIFACT"])
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact"
            shutil.copytree(source, target)
            main = target / "main.py"
            data = main.read_bytes()
            main.write_bytes(bytes([data[0] ^ 1]) + data[1:])
            report = verify_artifact(target)
            self.assertFalse(report.verified)
            self.assertTrue(any(issue.code == "hash_mismatch" for issue in report.issues))

    @unittest.skipUnless(os.environ.get("PTCG_SUBMISSION_ARTIFACT"), "set PTCG_SUBMISSION_ARTIFACT for exact artifact tests")
    def test_extra_file_is_rejected(self) -> None:
        source = Path(os.environ["PTCG_SUBMISSION_ARTIFACT"])
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "artifact"
            shutil.copytree(source, target)
            (target / "extra.txt").write_text("unexpected", encoding="utf-8")
            report = verify_artifact(target)
            self.assertTrue(any(issue.code == "unexpected_file" for issue in report.issues))


if __name__ == "__main__":
    unittest.main()
