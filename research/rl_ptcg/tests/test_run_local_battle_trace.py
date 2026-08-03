import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[3] / "infrastructure" / "tools" / "run_local_battle.py"
SPEC = importlib.util.spec_from_file_location("run_local_battle", MODULE_PATH)
run_local_battle = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(run_local_battle)


def test_compact_option_keeps_attachment_target_coordinates():
    option = {
        "type": 8,
        "area": 2,
        "index": 4,
        "inPlayArea": 5,
        "inPlayIndex": 2,
        "inPlayPlayerIndex": 0,
        "energyIndex": 1,
        "serial": 999,
        "private": "drop",
    }

    compact = run_local_battle.compact_option(option)

    assert compact == {
        "type": 8,
        "area": 2,
        "index": 4,
        "inPlayArea": 5,
        "inPlayIndex": 2,
        "inPlayPlayerIndex": 0,
        "energyIndex": 1,
    }


def test_acting_hand_ids_keeps_only_current_players_known_hand():
    obs = {
        "current": {
            "yourIndex": 1,
            "players": [
                {"hand": None},
                {"hand": [{"id": 380}, {"id": 387}]},
            ],
        }
    }

    assert run_local_battle.acting_hand_ids(obs) == [380, 387]


def test_card_id_handles_missing_selection_source():
    assert run_local_battle.card_id({"id": 380}) == 380
    assert run_local_battle.card_id(None) is None
    assert run_local_battle.card_id({}) is None


def test_visible_card_ids_preserves_hidden_positions():
    assert run_local_battle.visible_card_ids([{"id": 381}, None, {"id": 383}]) == [381, None, 383]
