from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASELINE = (
    ROOT
    / "archaludon/candidates"
    / "archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1"
)
CANDIDATE = (
    ROOT
    / "archaludon/candidates"
    / "archaludon_historical_silver_single_resolver_salvage_rule7_trial_v1"
)
sys.dont_write_bytecode = True


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


main_path = CANDIDATE / "main.py"
source = main_path.read_text(encoding="utf-8")
tree = ast.parse(source, filename=str(main_path))
compile(source, str(main_path), "exec")
for path in sorted((HERE / "tests").glob("test_*.py")) + [HERE / "run_shadow.py"]:
    compile(path.read_text(encoding="utf-8"), str(path), "exec")

top_functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
agents = [node for node in top_functions if node.name == "agent"]
resolvers = [node for node in top_functions if node.name == "_resolve"]
assert len(agents) == len(resolvers) == 1
parent_calls = [
    node
    for node in ast.walk(agents[0])
    if isinstance(node, ast.Call)
    and isinstance(node.func, ast.Attribute)
    and isinstance(node.func.value, ast.Name)
    and node.func.value.id == "_parent"
    and node.func.attr == "agent"
]
assert len(parent_calls) == 1

sys.path.insert(0, str(CANDIDATE))
spec = importlib.util.spec_from_file_location("rule7_verify_import", main_path)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert callable(module.agent)

deck = [int(line) for line in (CANDIDATE / "deck.csv").read_text().splitlines() if line]
assert len(deck) == 60
assert deck.count(1159) == 1

baseline_files = {
    path.relative_to(BASELINE)
    for path in BASELINE.rglob("*")
    if path.is_file() and "__pycache__" not in path.parts and path.name != "main.py"
}
candidate_files = {
    path.relative_to(CANDIDATE)
    for path in CANDIDATE.rglob("*")
    if path.is_file() and "__pycache__" not in path.parts and path.name != "main.py"
}
assert candidate_files == baseline_files
for relative in sorted(baseline_files):
    assert sha256(BASELINE / relative) == sha256(CANDIDATE / relative)

cache_dirs = list(CANDIDATE.rglob("__pycache__")) + list(HERE.rglob("__pycache__"))
pyc_files = list(CANDIDATE.rglob("*.pyc")) + list(HERE.rglob("*.pyc"))
assert not cache_dirs and not pyc_files

print(
    json.dumps(
        {
            "compiled_python_files": 6,
            "import_callable": True,
            "top_level_agent": len(agents),
            "top_level_resolve": len(resolvers),
            "static_parent_agent_calls": len(parent_calls),
            "candidate_file_count": 1 + len(candidate_files),
            "byte_identical_non_main_files": len(candidate_files),
            "deck_count": len(deck),
            "ace_spec_hero_cape_count": deck.count(1159),
            "cache_dirs": len(cache_dirs),
            "pyc_files": len(pyc_files),
            "main_sha256": sha256(main_path),
            "deck_sha256": sha256(CANDIDATE / "deck.csv"),
        },
        indent=2,
        sort_keys=True,
    )
)
