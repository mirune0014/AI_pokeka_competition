from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
PARENT = (
    ROOT
    / "archaludon/candidates"
    / "archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1"
)
CANDIDATE = (
    ROOT
    / "archaludon/candidates"
    / "archaludon_historical_silver_single_resolver_salvage_rule6_trial_v1"
)
HERE = Path(__file__).resolve().parent

sys.dont_write_bytecode = True
changed_python = [CANDIDATE / "main.py"] + sorted(HERE.rglob("*.py"))
for path in changed_python:
    compile(path.read_text(encoding="utf-8"), str(path), "exec")

sys.path.insert(0, str(CANDIDATE))
spec = importlib.util.spec_from_file_location("rule6_verify", CANDIDATE / "main.py")
if spec is None or spec.loader is None:
    raise AssertionError("candidate import specification missing")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

tree = ast.parse((CANDIDATE / "main.py").read_text(encoding="utf-8"))
body_functions = [
    node.name for node in tree.body if isinstance(node, ast.FunctionDef)
]
parent_calls = sum(
    isinstance(node, ast.Call)
    and isinstance(node.func, ast.Attribute)
    and isinstance(node.func.value, ast.Name)
    and node.func.value.id == "_parent"
    and node.func.attr == "agent"
    for node in ast.walk(tree)
)
local_functions = [
    (name, value)
    for name, value in module.__dict__.items()
    if inspect.isfunction(value) and value.__module__ == module.__name__
]
deck = [
    int(line.strip())
    for line in (CANDIDATE / "deck.csv").read_text().splitlines()
    if line.strip()
]
ace_spec_count = sum(
    bool(module._parent.CARD_DB[card_id].aceSpec) for card_id in deck
)


def package_files(path):
    return {
        value.relative_to(path)
        for value in path.rglob("*")
        if value.is_file()
        and "__pycache__" not in value.parts
        and value.suffix != ".pyc"
    }


parent_files = package_files(PARENT)
candidate_files = package_files(CANDIDATE)
non_main_diffs = []
for relative in sorted(parent_files | candidate_files):
    if relative == Path("main.py"):
        continue
    left = PARENT / relative
    right = CANDIDATE / relative
    if (
        not left.exists()
        or not right.exists()
        or hashlib.sha256(left.read_bytes()).digest()
        != hashlib.sha256(right.read_bytes()).digest()
    ):
        non_main_diffs.append(str(relative))

cache_dirs = list(CANDIDATE.rglob("__pycache__")) + list(HERE.rglob("__pycache__"))
pyc_files = list(CANDIDATE.rglob("*.pyc")) + list(HERE.rglob("*.pyc"))

assert body_functions.count("agent") == 1
assert body_functions.count("_resolve") == 1
assert [name for name in body_functions if not name.startswith("_")] == ["agent"]
assert parent_calls == 1
assert local_functions[-1][0] == "agent" and callable(module.agent)
assert len(deck) == 60 and ace_spec_count == 1
assert parent_files == candidate_files and not non_main_diffs
assert not cache_dirs and not pyc_files

print(f"compiled_changed_python_files={len(changed_python)}")
print("import=passed")
print(
    f'top_level_agent={body_functions.count("agent")} '
    f'resolver={body_functions.count("_resolve")} '
    f"static_parent_calls={parent_calls}"
)
print(f"loader_last={local_functions[-1][0]} callable={callable(module.agent)}")
print(f"deck_count={len(deck)} ace_spec_count={ace_spec_count}")
print(f"package_files={len(candidate_files)} non_main_diffs={len(non_main_diffs)}")
print(f"cache_dirs={len(cache_dirs)} pyc_files={len(pyc_files)}")
