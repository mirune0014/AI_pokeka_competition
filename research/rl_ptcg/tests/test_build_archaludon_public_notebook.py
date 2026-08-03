from __future__ import annotations

import csv
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from infrastructure.tools.build_archaludon_public_notebook import (
    build_notebook,
    read_archive,
    read_deck_summary,
    source_literal,
)


class ArchaludonPublicNotebookTest(unittest.TestCase):
    def test_archive_and_summary_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "agent.tar.gz"
            members = {
                "main.py": b"def agent(obs):\n    return obs\n",
                "deck.csv": ("8\n" * 60).encode(),
                "requirements.txt": b"",
            }
            with tarfile.open(archive, "w:gz") as bundle:
                for name, payload in members.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(payload)
                    bundle.addfile(info, io.BytesIO(payload))

            summary = root / "summary.csv"
            with summary.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=("card_id", "count", "name"))
                writer.writeheader()
                writer.writerow({"card_id": "8", "count": "60", "name": "Energy"})

            main_source, deck_source, requirements = read_archive(archive)
            rows = read_deck_summary(summary)
            self.assertEqual(eval(source_literal(main_source)), main_source)
            notebook = build_notebook(
                main_source=main_source,
                deck_source=deck_source,
                requirements=requirements,
                deck_summary=rows,
                archive_sha256="00",
                revalidation_submission_id=123,
            )
            self.assertGreaterEqual(len(notebook.cells), 10)
            self.assertIn("Complete policy source", notebook.cells[4].source)
            self.assertIn("submission `123`", notebook.cells[0].source)
            self.assertTrue(any("callable(module.agent)" in cell.source for cell in notebook.cells))

    def test_rejects_non_sixty_card_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "agent.tar.gz"
            members = {
                "main.py": b"def agent(obs):\n    return obs\n",
                "deck.csv": ("8\n" * 59).encode(),
                "requirements.txt": b"",
            }
            with tarfile.open(archive, "w:gz") as bundle:
                for name, payload in members.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(payload)
                    bundle.addfile(info, io.BytesIO(payload))
            with self.assertRaisesRegex(ValueError, "60 deck rows"):
                read_archive(archive)


if __name__ == "__main__":
    unittest.main()
