import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List, Optional


MODULE_PATH = Path(__file__).parents[3] / "infrastructure" / "tools" / "generate_deck_factorial.py"
SPEC = importlib.util.spec_from_file_location("generate_deck_factorial", MODULE_PATH)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = generator
SPEC.loader.exec_module(generator)


class GenerateDeckFactorialTests(unittest.TestCase):
    def make_baseline(self, root: Path, cards: Optional[List[str]] = None) -> Path:
        baseline = root / "baseline"
        baseline.mkdir(parents=True)
        default_cards = ["cut_a", "cut_b"] + [f"card_{index}" for index in range(1, 59)]
        (baseline / "deck.csv").write_text("\n".join(cards or default_cards) + "\n")
        (baseline / "agent.py").write_text("preserved\n")
        return baseline

    def test_generates_two_by_two_and_skips_noop_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest = generator.generate(
                self.make_baseline(root), root / "output",
                [generator.Change("alpha", "add_a"), generator.Change("noop", "cut_b")],
                [generator.Change("first", "cut_a"), generator.Change("second", "cut_b")], set(),
            )
            self.assertEqual(3, len(manifest["candidates"]))
            self.assertEqual(3, len(list((root / "output").glob("add_*"))))
            for candidate in manifest["candidates"]:
                directory = root / "output" / candidate["directory"]
                self.assertEqual(60, len(generator.read_deck(directory / "deck.csv")))
                self.assertEqual("preserved\n", (directory / "agent.py").read_text())
            on_disk = json.loads((root / "output" / generator.MANIFEST_NAME).read_text())
            self.assertEqual(manifest, on_disk)

    def test_rejects_invalid_source_and_copy_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            invalid_source = ["too_many"] * 5 + [f"card_{index}" for index in range(55)]
            with self.assertRaisesRegex(ValueError, "more than four"):
                generator.generate(self.make_baseline(root, invalid_source), root / "output", [generator.Change("add", "new")], [generator.Change("cut", "too_many")], set())

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            cards = ["add_target"] * 4 + ["cut_target"] + [f"card_{index}" for index in range(55)]
            with self.assertRaisesRegex(ValueError, "more than four"):
                generator.generate(self.make_baseline(root, cards), root / "output", [generator.Change("add", "add_target")], [generator.Change("cut", "cut_target")], set())
            generator.generate(self.make_baseline(root / "other", cards), root / "unlimited", [generator.Change("add", "add_target")], [generator.Change("cut", "cut_target")], {"add_target"})

    def test_resume_rejects_modified_deck(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            baseline = self.make_baseline(root)
            output = root / "output"
            generator.generate(baseline, output, [generator.Change("add", "new")], [generator.Change("cut", "cut_a")], set())
            candidate = next(output.glob("add_*"))
            (candidate / "deck.csv").write_text("tampered\n")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                generator.generate(baseline, output, [generator.Change("add", "new")], [generator.Change("cut", "cut_a")], set(), resume=True)


if __name__ == "__main__":
    unittest.main()
