import importlib.util
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "infrastructure" / "tools"
    / "audit_cynthia_crustle_spiritomb_traces.py"
)
SPEC = importlib.util.spec_from_file_location(
    "audit_cynthia_crustle_spiritomb_traces", MODULE_PATH
)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def snapshot():
    return {
        "turn": 11,
        "p0_active": 381,
        "p0_active_hp": 90,
        "p0_active_max_hp": 330,
        "p0_active_energy": 2,
        "p0_bench": [387, 342, 342],
        "p0_bench_hp": [70, 130, 130],
        "p0_bench_max_hp": [70, 130, 130],
        "p0_bench_energy": [0, 0, 0],
        "p1_active": 345,
        "p1_active_hp": 190,
        "p1_active_max_hp": 190,
        "p1_active_energy": 1,
        "p1_bench": [],
        "p1_bench_hp": [],
        "p1_bench_max_hp": [],
        "p1_bench_energy": [],
    }


def test_approved_first_action_accepts_lethal_spiritomb_attach():
    event = {
        "player": 0,
        "context": 0,
        "options": [
            {"type": 8, "area": 2, "index": 0, "inPlayArea": 5, "inPlayIndex": 0}
        ],
        "action": [0],
        "own_hand_ids": [6],
        "snapshot": snapshot(),
    }

    approved, kind, projected = module.approved_first_action(event, 0)

    assert approved is True
    assert kind == "attach_spiritomb"
    assert projected == 300


def test_first_divergence_requires_identical_public_decision_state():
    base = {"player": 0, "context": 0, "options": [{"type": 12}, {"type": 13}], "action": [1]}
    candidate = {**base, "action": [0]}

    assert module.first_divergence([base], [candidate]) == (0, True)


def test_non_crustle_state_fails_closed():
    event = {
        "player": 0,
        "context": 0,
        "options": [{"type": 12}],
        "action": [0],
        "own_hand_ids": [],
        "snapshot": {**snapshot(), "p1_active": 756},
    }

    approved, reason, projected = module.approved_first_action(event, 0)

    assert approved is False
    assert reason == "outside_predicate"
    assert projected == 0
