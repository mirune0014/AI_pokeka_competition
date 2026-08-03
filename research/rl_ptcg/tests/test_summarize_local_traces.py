import importlib.util
import json
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[3] / "infrastructure" / "tools" / "summarize_local_traces.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("summarize_local_traces", MODULE_PATH)
summary = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(summary)


def test_win_plan_milestones_are_extracted_from_cumulative_logs(tmp_path):
    trace = tmp_path / "game.jsonl"
    rows = [
        {
            "game": 0,
            "snapshot": {
                "turn": 0,
                "result": -1,
                "p0_prizes": 0,
                "p1_prizes": 0,
                "p0_active": None,
                "p0_bench": [],
                "p1_active": None,
                "p1_bench": [],
            },
            "logs": [],
        },
        {
            "game": 0,
            "snapshot": {
                "turn": 1,
                "result": -1,
                "p0_prizes": 6,
                "p1_prizes": 6,
                "p0_active": 10,
                "p0_bench": [11],
                "p1_active": 20,
                "p1_bench": [],
            },
            "logs": [{"type": summary.LOG_EVOLVE, "playerIndex": 0, "cardId": 11}],
        },
        {
            "game": 0,
            "snapshot": {
                "turn": 2,
                "result": -1,
                "p0_prizes": 6,
                "p1_prizes": 6,
                "p0_active": 10,
                "p0_bench": [11, 12],
                "p1_active": 20,
                "p1_bench": [],
            },
            "logs": [
                {"type": summary.LOG_EVOLVE, "playerIndex": 0, "cardId": 11},
                {
                    "type": summary.LOG_ATTACH,
                    "playerIndex": 0,
                    "cardId": 1,
                    "cardIdTarget": 12,
                },
                {"type": summary.LOG_ATTACK, "playerIndex": 0, "attackId": 101},
            ],
        },
        {
            "game": 0,
            "snapshot": {
                "turn": 3,
                "result": -1,
                "p0_prizes": 5,
                "p1_prizes": 6,
                "p0_active": 10,
                "p0_bench": [11, 12],
                "p1_active": 20,
                "p1_bench": [],
            },
            "logs": [
                {"type": summary.LOG_EVOLVE, "playerIndex": 0, "cardId": 11},
                {
                    "type": summary.LOG_ATTACH,
                    "playerIndex": 0,
                    "cardId": 1,
                    "cardIdTarget": 12,
                },
                {"type": summary.LOG_ATTACK, "playerIndex": 0, "attackId": 101},
            ],
        },
        {
            "game": 0,
            "snapshot": {
                "turn": 4,
                "result": -1,
                "p0_prizes": 5,
                "p1_prizes": 6,
                "p0_active": 10,
                "p0_bench": [12],
                "p1_active": 20,
                "p1_bench": [],
            },
            "logs": [
                {"type": summary.LOG_MOVE_CARD, "playerIndex": 0, "cardId": 11, "fromArea": summary.AREA_BENCH, "toArea": summary.AREA_TRASH},
            ],
        },
        {
            "game": 0,
            "snapshot": {
                "turn": 6,
                "result": 0,
                "p0_prizes": 4,
                "p1_prizes": 6,
                "p0_active": 10,
                "p0_bench": [12],
                "p1_active": 20,
                "p1_bench": [],
            },
            "logs": [
                {"type": summary.LOG_ATTACK, "playerIndex": 0, "attackId": 101},
            ],
        },
    ]
    trace.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    result = summary.summarize_game(
        trace,
        card_names={10: "Active", 11: "Stage One", 12: "Backup", 20: "Target"},
        attack_names={101: "Tempo Attack"},
        line_card_ids={10, 11},
        focus_attach_card_ids={12},
        recovery_card_ids={11},
    )

    assert result["p0_first_evolve_turn"] == 1
    assert result["p0_first_attack_turn"] == 2
    assert result["p0_first_attack"] == "Tempo Attack"
    assert result["p0_first_attack_board"] == "Active;Stage One;Backup"
    assert result["p0_first_attack_line_count"] == 2
    assert result["p0_first_prize_turn"] == 3
    assert result["p0_first_prize_board"] == "Active;Stage One;Backup"
    assert result["p0_first_prize_line_count"] == 2
    assert result["p0_min_line_after_first_prize"] == 1
    assert result["p0_first_focus_attach_turn"] == 2
    assert result["p0_first_focus_attach_board"] == "Active;Stage One;Backup"
    assert result["p0_first_focus_attach_line_count"] == 2
    assert result["p0_first_focus_attach_prizes"] == 6
    assert result["p0_attack_count"] == 2
    assert result["p0_missed_attack_turns_after_first"] == 1
    assert result["p0_max_missed_attack_streak"] == 1
    assert result["p0_recovery_card_losses"] == 1
    assert result["p0_recovered_to_attack"] == 1
    assert result["p0_max_recovery_turns"] == 2
    assert result["p0_max_board"] == 3
    assert result["p1_first_attack_turn"] is None


def test_terminal_summary_overrides_incomplete_trace_snapshot():
    row = {
        "result": -1,
        "turn": 8,
        "p0_deck": 20,
        "p0_prizes_left": 2,
        "p0_active": "Old Active",
        "p0_active_hp": 10,
        "p0_bench": "Old Bench",
        "p1_deck": 18,
        "p1_prizes_left": 3,
        "p1_active": "Target",
        "p1_active_hp": 20,
        "p1_bench": "",
    }
    terminal = {
        "game": 0,
        "result": 0,
        "turn": 10,
        "p0_deck": 17,
        "p0_prizes": 0,
        "p0_active": 10,
        "p0_active_hp": 80,
        "p0_bench": [11, 12],
        "p1_deck": 15,
        "p1_prizes": 3,
        "p1_active": None,
        "p1_active_hp": None,
        "p1_bench": [20],
    }

    summary.merge_terminal_summary(
        row,
        terminal,
        {10: "Active", 11: "Stage One", 12: "Backup", 20: "Target"},
    )

    assert row["result"] == 0
    assert row["turn"] == 10
    assert row["p0_prizes_left"] == 0
    assert row["p0_active"] == "Active"
    assert row["p0_bench"] == "Stage One;Backup"
    assert row["p1_active"] == ""
    assert row["terminal_source"] == "game_summary"


def test_delta_logs_with_equal_lengths_do_not_skip_later_attacks(tmp_path):
    trace = tmp_path / "delta.jsonl"
    rows = [
        {
            "game": 0,
            "snapshot": {
                "turn": 1,
                "result": -1,
                "p0_prizes": 6,
                "p1_prizes": 6,
                "p0_active": 10,
                "p0_bench": [],
                "p1_active": 20,
                "p1_bench": [],
            },
            "logs": [{"type": summary.LOG_ATTACK, "playerIndex": 0, "attackId": 101}],
        },
        {
            "game": 0,
            "snapshot": {
                "turn": 3,
                "result": 0,
                "p0_prizes": 5,
                "p1_prizes": 6,
                "p0_active": 10,
                "p0_bench": [],
                "p1_active": 20,
                "p1_bench": [],
            },
            "logs": [{"type": summary.LOG_ATTACK, "playerIndex": 0, "attackId": 102}],
        },
    ]
    trace.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    result = summary.summarize_game(
        trace,
        card_names={10: "Active", 20: "Target"},
        attack_names={101: "First", 102: "Second"},
    )

    assert result["p0_attack_count"] == 2
    assert result["p0_first_attack"] == "First"
    assert "p0:Second x1" in result["top_attacks"]
