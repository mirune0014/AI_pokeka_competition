"""Deterministic structural gate for the Task 9 candidate."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
AUTO = ROOT / "archaludon"
PARENT = AUTO / "candidates/archaludon_public_lillie_physical_minimum_route_arbitration_t8_v1"
CANDIDATE = AUTO / "candidates/archaludon_public_prize_race_threat_control_t9_v1"
OUTPUT = Path(__file__).with_name("structural_results.json")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


parent_main = (PARENT / "main.py").read_bytes()
candidate_main = (CANDIDATE / "main.py").read_bytes()
assert candidate_main.startswith(parent_main)
assert sha(PARENT / "deck.csv") == sha(CANDIDATE / "deck.csv")

tree = ast.parse(candidate_main.decode("utf-8"))
callables = [
    node for node in tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    and node.name == "agent"
]
assert callables and tree.body[-1] is callables[-1]

spec = importlib.util.spec_from_file_location("task9_structure", CANDIDATE / "main.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
assert callable(module.agent)
assert module._T9_RULE_ID == "PUBLIC_PRIZE_RACE_THREAT_CONTROL_T9_V1"
assert len(module._T9_PURPOSES) == 6

rows = tuple(
    int(row.strip())
    for row in (CANDIDATE / "deck.csv").read_text(encoding="utf-8-sig").splitlines()
    if row.strip()
)
count = len(rows)
assert count == 60
ace = 0
for card_id in rows:
    data = module.CARD_DB.get(card_id)
    assert data is not None
    if bool(module._pcrd_get(data, "aceSpec", False)):
        ace += 1
assert ace == 1

caches = tuple(CANDIDATE.rglob("__pycache__")) + tuple(CANDIDATE.rglob("*.pyc"))
assert not caches
entries = tuple(sorted(path.name for path in CANDIDATE.iterdir() if path.is_file()))
assert entries == ("deck.csv", "main.py", "requirements.txt")

result = {
    "parent_main_sha256": sha(PARENT / "main.py"),
    "candidate_main_sha256": sha(CANDIDATE / "main.py"),
    "parent_prefix_byte_count": len(parent_main),
    "candidate_byte_count": len(candidate_main),
    "deck_sha256": sha(CANDIDATE / "deck.csv"),
    "deck_count": count,
    "ace_spec_count": ace,
    "top_level_agent_count": len(callables),
    "last_top_level_node": getattr(tree.body[-1], "name", type(tree.body[-1]).__name__),
    "entries": entries,
    "cache_count": len(caches),
    "status": "PASS",
}
OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(result, indent=2))
