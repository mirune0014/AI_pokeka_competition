from __future__ import annotations

import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path

from ptcg_desktop.artifacts import (
    REQUIRED_RUNTIME_FILES,
    cleanup_stage,
    register_local_artifact,
    stage_artifact,
    verify_artifact,
)


class LocalArtifactTests(unittest.TestCase):
    def _package(self, root: Path, *, marker: Path | None = None) -> None:
        for relative in sorted(REQUIRED_RUNTIME_FILES):
            target = root.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            if relative == "main.py":
                text = "def agent(obs):\n    return [0]\n"
                if marker is not None:
                    text = f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n" + text
                target.write_text(text, encoding="utf-8")
            elif relative == "deck.csv":
                target.write_text("1\n" * 60, encoding="utf-8")
            else:
                target.write_bytes(("fixture:" + relative).encode("ascii"))
        (root / "helper.json").write_text('{"mode":"local"}', encoding="utf-8")

    def _archive(self, source: Path, target: Path) -> None:
        with tarfile.open(target, "w:gz") as archive:
            for path in sorted(source.rglob("*")):
                if path.is_file():
                    archive.add(path, arcname=path.relative_to(source).as_posix())

    def test_registration_hashes_without_importing_main(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            package = base / "agent"
            marker = base / "imported.txt"
            package.mkdir()
            self._package(package, marker=marker)

            manifest, report = register_local_artifact(package)

            self.assertTrue(report.verified, report.issues)
            self.assertEqual(report.trust_mode, "local_registered")
            self.assertTrue(report.manifest_id.startswith("local-"))
            self.assertIsNone(report.submission_id)
            self.assertFalse(marker.exists(), "registration must not import main.py")
            self.assertEqual(manifest["content_sha256"], report.content_sha256)

    def test_registered_content_change_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "agent"
            package.mkdir()
            self._package(package)
            manifest, report = register_local_artifact(package)
            self.assertTrue(report.verified)

            (package / "main.py").write_text("def agent(obs):\n    return [1]\n", encoding="utf-8")
            changed = verify_artifact(package, manifest)

            self.assertFalse(changed.verified)
            self.assertTrue(any(issue.code == "size_mismatch" or issue.code == "hash_mismatch" for issue in changed.issues))

    def test_mtime_only_change_keeps_registration_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "agent"
            package.mkdir()
            self._package(package)
            manifest, report = register_local_artifact(package)
            self.assertTrue(report.verified)
            main = package / "main.py"
            os.utime(main, (100.0, 100.0))

            self.assertTrue(verify_artifact(package, manifest).verified)

    def test_archive_and_directory_share_content_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            package = base / "agent"
            archive = base / "agent.tar.gz"
            package.mkdir()
            self._package(package)
            self._archive(package, archive)

            directory_manifest, directory_report = register_local_artifact(package)
            archive_manifest, archive_report = register_local_artifact(archive)

            self.assertTrue(directory_report.verified, directory_report.issues)
            self.assertTrue(archive_report.verified, archive_report.issues)
            self.assertEqual(directory_report.content_sha256, archive_report.content_sha256)
            self.assertEqual(directory_manifest["manifest_id"], archive_manifest["manifest_id"])

    def test_staging_uses_registered_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            package = base / "agent"
            stages = base / "stages"
            package.mkdir()
            self._package(package)
            manifest, report = register_local_artifact(package)
            self.assertTrue(report.verified)

            stage = stage_artifact(package, "match-1", root=stages, manifest=manifest)
            try:
                self.assertTrue(verify_artifact(stage, manifest).verified)
            finally:
                cleanup_stage(stage, root=stages)

    def test_local_manifest_cannot_claim_submission_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary) / "agent"
            package.mkdir()
            self._package(package)
            manifest, report = register_local_artifact(package)
            self.assertTrue(report.verified)
            manifest["submission_id"] = "55155015"

            spoofed = verify_artifact(package, manifest)

            self.assertFalse(spoofed.verified)
            self.assertTrue(any(issue.code == "invalid_manifest" for issue in spoofed.issues))

    def test_archive_rejects_parent_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "unsafe.tar.gz"
            payload = b"unsafe"
            with tarfile.open(archive, "w:gz") as bundle:
                info = tarfile.TarInfo("../main.py")
                info.size = len(payload)
                bundle.addfile(info, io.BytesIO(payload))

            _, report = register_local_artifact(archive)

            self.assertFalse(report.verified)
            self.assertTrue(any(issue.code == "registration_failed" for issue in report.issues))


if __name__ == "__main__":
    unittest.main()
