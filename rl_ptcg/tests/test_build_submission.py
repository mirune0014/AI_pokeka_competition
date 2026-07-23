import ast
import tarfile
import tempfile
import unittest
import importlib.util
from pathlib import Path

from rl_ptcg.build_submission import build, move_agent_last, rename_choose_options


class BuilderTests(unittest.TestCase):
    def test_rename_requires_one_top_level_function(self):
        self.assertIn("choose_options_rule", rename_choose_options("def choose_options(obs):\n    return []\n"))
        with self.assertRaises(ValueError):
            rename_choose_options("def other():\n    pass\n")

    def test_move_agent_last_requires_one_top_level_agent(self):
        source = (
            "def agent(obs):\n    return choose_options(obs)\n\n"
            "def choose_options(obs):\n    return []\n"
        )
        moved = move_agent_last(source)
        functions = [node.name for node in ast.parse(moved).body if isinstance(node, ast.FunctionDef)]
        self.assertEqual(["choose_options", "agent"], functions)
        with self.assertRaises(ValueError):
            move_agent_last("def other():\n    pass\n")
        with self.assertRaises(ValueError):
            move_agent_last("def agent():\n    pass\n\ndef agent():\n    pass\n")

    def test_build_validates_and_packages_root_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            (source / "cg").mkdir(parents=True)
            (source / "main.py").write_text(
                "def choose_options(obs):\n    return []\n\n"
                "def agent(obs):\n    return choose_options(obs)\n",
                encoding="ascii",
            )
            (source / "deck.csv").write_text("1\n" * 60, encoding="ascii")
            (source / "cg" / "__init__.py").write_text("", encoding="ascii")
            archive = root / "base.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                for name in ("main.py", "deck.csv", "cg", "cg/__init__.py"):
                    path = source / name
                    tar.add(path, arcname=path.relative_to(source))
            with tarfile.open(archive, "r:gz") as tar:
                source_names = tar.getnames()
            weights = root / "weights.json"
            weights.write_text('{"test_weight": 0.5}', encoding="ascii")
            result = build(archive, weights, root / "out", root / "result.tar.gz")
            self.assertTrue(result.exists())
            with tarfile.open(result, "r:gz") as tar:
                names = tar.getnames()
            self.assertEqual(source_names, names)
            self.assertIn("cg", names)
            self.assertIn("main.py", names)
            self.assertNotIn("residual_policy.py", names)
            self.assertNotIn("residual_weights.json", names)
            self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))
            built_main = (root / "out" / "main.py").read_text(encoding="utf-8")
            self.assertIn("top_n=3", built_main)
            self.assertIn("residual_cap=0.35", built_main)
            self.assertNotIn("__RESIDUAL_", built_main)
            functions = [
                node.name for node in ast.parse(built_main).body
                if isinstance(node, ast.FunctionDef)
            ]
            self.assertEqual(1, functions.count("agent"))
            self.assertEqual("agent", functions[-1])
            spec = importlib.util.spec_from_file_location("isolated_built_agent", root / "out" / "main.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual({"test_weight": 0.5}, module._RESIDUAL_WEIGHTS)
            self.assertTrue(callable(module.choose_residual))


if __name__ == "__main__":
    unittest.main()
