from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PARENT = (
    ROOT
    / "autonomous_gold_20260715/candidates"
    / "archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1"
)
CANDIDATE = (
    ROOT
    / "autonomous_gold_20260715/candidates"
    / "archaludon_historical_silver_single_resolver_salvage_rule8_trial_v1"
)


def sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def source_files(root: Path):
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    )


python_files = [CANDIDATE / "main.py", HERE / "run_shadow.py", Path(__file__)]
python_files.extend(sorted((HERE / "tests").glob("test_*.py")))
compiled = []
for path in python_files:
    compile(path.read_text(encoding="utf-8"), str(path), "exec")
    compiled.append(str(path.relative_to(ROOT)))

source = (CANDIDATE / "main.py").read_text(encoding="utf-8")
tree = ast.parse(source)
top_functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
agent_nodes = [node for node in top_functions if node.name == "agent"]
resolver_nodes = [node for node in top_functions if node.name == "_resolve"]
if len(agent_nodes) != 1 or len(resolver_nodes) != 1:
    raise AssertionError("single agent/resolver gate failed")
parent_calls = [
    node
    for node in ast.walk(agent_nodes[0])
    if isinstance(node, ast.Call)
    and isinstance(node.func, ast.Attribute)
    and isinstance(node.func.value, ast.Name)
    and node.func.value.id == "_parent"
    and node.func.attr == "agent"
]
if len(parent_calls) != 1 or top_functions[-1].name != "agent":
    raise AssertionError("parent-once/final-agent gate failed")
if "PARENT_TURBO_FLARE_EXACT_PRIMARY_THEN_ONE_BACKUP_TRANSACTION_V1" in source:
    raise AssertionError("forbidden Rule 7 inherited")

sys.dont_write_bytecode = True
sys.path.insert(0, str(CANDIDATE))
try:
    spec = importlib.util.spec_from_file_location("rule8_verify_candidate", CANDIDATE / "main.py")
    if spec is None or spec.loader is None:
        raise AssertionError("candidate import spec")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
finally:
    sys.path.remove(str(CANDIDATE))
local_functions = [
    (name, value)
    for name, value in module.__dict__.items()
    if inspect.isfunction(value) and value.__module__ == module.__name__
]
if local_functions[-1][0] != "agent" or not callable(module.agent):
    raise AssertionError("loader-last/final callable agent gate failed")

deck_ids = [
    int(line.strip())
    for line in (CANDIDATE / "deck.csv").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
ace_count = sum(bool(module._parent.CARD_DB[card_id].aceSpec) for card_id in deck_ids)
if len(deck_ids) != 60 or ace_count != 1:
    raise AssertionError("legal60/ACE1 gate failed")

parent_files = {
    path.relative_to(PARENT): path
    for path in source_files(PARENT)
}
candidate_files = {
    path.relative_to(CANDIDATE): path
    for path in source_files(CANDIDATE)
}
if set(parent_files) != set(candidate_files):
    raise AssertionError("candidate package layout differs from Rule 5")
preserved = {
    str(relative): sha256(candidate_files[relative])
    for relative in candidate_files
    if relative != Path("main.py")
    and sha256(candidate_files[relative]) == sha256(parent_files[relative])
}
if len(preserved) != len(candidate_files) - 1:
    raise AssertionError("non-main candidate file changed")

cache_paths = [
    str(path.relative_to(ROOT))
    for root in (CANDIDATE, HERE)
    for path in root.rglob("*")
    if path.name == "__pycache__" or path.suffix == ".pyc"
]
if cache_paths:
    raise AssertionError({"cache_paths": cache_paths})

summary = {
    "compiled_python_count": len(compiled),
    "compiled_python": compiled,
    "import_passed": True,
    "top_level_agent_count": len(agent_nodes),
    "top_level_resolver_count": len(resolver_nodes),
    "static_parent_calls_inside_agent": len(parent_calls),
    "top_level_final_function": top_functions[-1].name,
    "runtime_final_local_function": local_functions[-1][0],
    "rule7_absent": True,
    "candidate_package_file_count": len(candidate_files),
    "preserved_non_main_file_count": len(preserved),
    "deck_count": len(deck_ids),
    "ace_spec_count": ace_count,
    "cache_paths": cache_paths,
    "main_sha256": sha256(CANDIDATE / "main.py"),
    "deck_sha256": sha256(CANDIDATE / "deck.csv"),
}
(HERE / "verification_summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
)
print(json.dumps(summary, indent=2, sort_keys=True))
