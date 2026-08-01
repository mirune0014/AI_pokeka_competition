"""Structural and package checks for the isolated Task 5 candidate."""
from __future__ import annotations

import ast
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
AUTO = ROOT / "autonomous_gold_20260715"
PARENT = (
    AUTO / "candidates"
    / "archaludon_public_pre_attack_executable_successor_bench_zero_continuity_gate_v1"
)
CANDIDATE = (
    AUTO / "candidates"
    / "archaludon_public_poke_pad_declared_executable_role_transaction_v1"
)
EXPECTED_PARENT_MAIN = "CAF2C696AE9F6102C1A4A8E67649C309104064CAABF9643865BE766D91BDE8DD"
EXPECTED_DECK = "08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def files(path):
    return tuple(sorted(
        item.relative_to(path).as_posix()
        for item in path.rglob("*")
        if item.is_file() and "__pycache__" not in item.parts and item.suffix != ".pyc"
    ))


assert sha(PARENT / "main.py") == EXPECTED_PARENT_MAIN
assert sha(PARENT / "deck.csv") == EXPECTED_DECK
assert sha(CANDIDATE / "deck.csv") == EXPECTED_DECK
parent_files = files(PARENT)
candidate_files = files(CANDIDATE)
assert len(parent_files) == len(candidate_files) == 12
assert parent_files == candidate_files
other_mismatches = [
    name for name in parent_files
    if name != "main.py" and (PARENT / name).read_bytes() != (CANDIDATE / name).read_bytes()
]
assert other_mismatches == []

source = (CANDIDATE / "main.py").read_text(encoding="utf-8")
tree = ast.parse(source)
compile(tree, str(CANDIDATE / "main.py"), "exec")
functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
assert functions and functions[-1].name == "agent"
assert "PUBLIC_POKE_PAD_DECLARED_EXECUTABLE_ROLE_TRANSACTION_V1" in source
assert "_pfc_arm_pad_watch(obs, parent_action)" not in source

sys.path.insert(0, str(CANDIDATE))
spec = importlib.util.spec_from_file_location("task5_structure_candidate", CANDIDATE / "main.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
assert callable(module.agent)
assert module.agent.__name__ == "agent"

deck_count = 0
ace_count = 0
with (CANDIDATE / "deck.csv").open(encoding="utf-8", newline="") as handle:
    for row in csv.reader(handle):
        if not row:
            continue
        card_id, count = int(row[0]), 1
        deck_count += 1
        card = module.CARD_DB.get(card_id)
        assert card is not None
        if bool(getattr(card, "aceSpec", False)):
            ace_count += count
assert deck_count == 60
assert ace_count == 1

caches = [
    str(item.relative_to(CANDIDATE))
    for item in CANDIDATE.rglob("*")
    if item.name == "__pycache__" or item.suffix == ".pyc"
]

result = {
    "parent_main_sha256": sha(PARENT / "main.py"),
    "candidate_main_sha256": sha(CANDIDATE / "main.py"),
    "deck_sha256": sha(CANDIDATE / "deck.csv"),
    "package_entry_count": len(candidate_files),
    "non_main_byte_mismatches": other_mismatches,
    "deck_card_count": deck_count,
    "ace_spec_count": ace_count,
    "ast_last_callable": functions[-1].name,
    "import_callable": callable(module.agent),
    "cache_entries_at_check": caches,
}
Path(__file__).with_name("structural_results.json").write_text(
    json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
)
print(json.dumps(result, sort_keys=True))
