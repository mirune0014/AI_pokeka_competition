import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[3] / "infrastructure" / "tools" / "analyze_cynthia_champions_call_route.py"
SPEC = importlib.util.spec_from_file_location("analyze_cynthia_champions_call_route", MODULE_PATH)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)


def call_row(hand, active, bench, legal):
    return {
        "player": 0,
        "own_hand_ids": hand,
        "snapshot": {"p0_active": active, "p0_bench": bench},
        "options": [{"cardId": card} for card in legal],
    }


def test_route_secures_garchomp_before_widening():
    row = call_row([], audit.GABITE, [audit.GIBLE], [audit.GABITE, audit.GARCHOMP_EX])
    assert audit.route_target(row) == (audit.GARCHOMP_EX, "secure first Garchomp attacker")


def test_route_secures_roselia_then_roserade_after_attacker():
    base_row = call_row(
        [audit.GARCHOMP_EX],
        audit.GABITE,
        [audit.GIBLE],
        [audit.ROSELIA, audit.ROSERADE, audit.GABITE],
    )
    assert audit.route_target(base_row) == (audit.ROSELIA, "secure missing Roselia base")

    evolution_row = call_row(
        [audit.GARCHOMP_EX, audit.ROSELIA],
        audit.GABITE,
        [audit.GIBLE],
        [audit.ROSERADE, audit.GABITE],
    )
    assert audit.route_target(evolution_row) == (audit.ROSERADE, "secure missing Roserade evolution")


def test_route_falls_back_after_attacker_and_support_are_secured():
    row = call_row(
        [audit.GARCHOMP_EX, audit.ROSERADE],
        audit.GABITE,
        [audit.GIBLE, audit.ROSELIA],
        [audit.GABITE, audit.GARCHOMP_EX],
    )
    assert audit.route_target(row) == (None, "baseline fallback")
