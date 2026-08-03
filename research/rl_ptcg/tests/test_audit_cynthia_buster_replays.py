import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[3] / "infrastructure" / "tools" / "audit_cynthia_buster_replays.py"
SPEC = importlib.util.spec_from_file_location("audit_cynthia_buster_replays", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def test_attack_id_from_action_reads_selected_attack():
    observation = {
        "select": {
            "option": [
                {"type": 7},
                {"type": 13, "attackId": 531},
                {"type": 13, "attackId": 532},
            ]
        }
    }

    assert module.attack_id_from_action(observation, [2]) == 532
    assert module.attack_id_from_action(observation, [0]) is None


def test_classify_buster_state_orders_visible_conversion_reasons():
    common = {
        "buster_ko": True,
        "corkscrew_ko": False,
        "target_prize_value": 1,
        "remaining_prizes": 3,
        "opponent_bench_empty": False,
    }
    assert module.classify_buster_state(**common) == "Buster_only_one_prize_KO"
    assert (
        module.classify_buster_state(**{**common, "target_prize_value": 2})
        == "Buster_only_multi_prize_KO"
    )
    assert (
        module.classify_buster_state(**{**common, "opponent_bench_empty": True})
        == "board_clear_KO"
    )
    assert (
        module.classify_buster_state(**{**common, "remaining_prizes": 1})
        == "game_winning_KO"
    )
    assert (
        module.classify_buster_state(**{**common, "corkscrew_ko": True})
        == "Corkscrew_also_KO"
    )
    assert (
        module.classify_buster_state(**{**common, "buster_ko": False})
        == "non_KO_Buster"
    )
