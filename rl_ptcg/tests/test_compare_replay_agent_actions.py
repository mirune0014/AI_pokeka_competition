import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "compare_replay_agent_actions.py"
SPEC = importlib.util.spec_from_file_location("compare_replay_agent_actions", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def test_selected_options_uses_recorded_indices():
    observation = {
        "select": {
            "option": [
                {"type": 7, "index": 1},
                {"type": 8, "index": 2, "inPlayIndex": 0},
                {"type": 14},
            ]
        }
    }

    assert module.selected_options(observation, [1]) == [
        {"type": 8, "index": 2, "inPlayIndex": 0}
    ]
    assert module.selected_options(observation, [-1, 3]) == []


def test_explicit_target_seat_handles_same_team_self_play():
    replay = {"info": {"TeamNames": ["same", "same"]}}

    assert module.resolve_target_seat(replay, [], target_seat=1) == 1
