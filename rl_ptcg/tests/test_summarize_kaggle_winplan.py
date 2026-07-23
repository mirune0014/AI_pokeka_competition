import importlib.util
import json
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "summarize_kaggle_winplan.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("summarize_kaggle_winplan", MODULE_PATH)
summary = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(summary)


def card(value):
    return {"id": value}


def entry(turn, prizes, active, bench, logs, *, status="ACTIVE", your_index=1):
    return {
        "status": status,
        "observation": {
            "current": {
                "turn": turn,
                "yourIndex": your_index,
                "players": [
                    {"active": [card(90)], "bench": [], "prize": [None] * 6, "deckCount": 0},
                    {
                        "active": [card(active)],
                        "bench": [card(value) for value in bench],
                        "prize": [None] * prizes,
                    },
                ],
            },
            "logs": logs,
        },
    }


def test_kaggle_winplan_uses_submission_seat_and_deduplicates_stale_logs(tmp_path):
    attach = {"type": summary.LOG_ATTACH, "playerIndex": 1, "cardId": 18, "cardIdTarget": 344}
    attack = {"type": summary.LOG_ATTACK, "playerIndex": 1, "attackId": 500}
    replay = {
        "info": {"EpisodeId": 123, "TeamNames": ["other", "mine"]},
        "rewards": [-1, 1],
        "steps": [
            [{}, entry(1, 6, 756, [344, 344], [])],
            [{}, entry(2, 6, 756, [344, 344], [attach])],
            [{}, entry(2, 6, 756, [344, 344], [attach], status="INACTIVE")],
            [{}, entry(3, 6, 345, [344, 345], [attach, attack])],
            [{}, entry(4, 5, 345, [344, 345], [attach, attack])],
            [{}, entry(5, 5, 345, [344, 345], [attack])],
        ],
    }
    replay_path = tmp_path / "episode_123_replay.json"
    replay_path.write_text(json.dumps(replay), encoding="utf-8")

    result = summary.summarize_replay(
        replay_path,
        1,
        {756: "Mega Kangaskhan", 344: "Dwebble", 345: "Crustle"},
        {500: "Scissors"},
        line_card_ids={344, 345},
        focus_energy_ids={18},
        focus_target_ids={344},
    )

    assert result["result"] == "win"
    assert result["win_condition"] == "deckout"
    assert result["first_focus_attach_turn"] == 2
    assert result["first_focus_attach_line_count"] == 2
    assert result["first_attack_turn"] == 3
    assert result["first_attack"] == "Scissors"
    assert result["first_attack_line_count"] == 3
    assert result["first_prize_turn"] == 4
    assert result["first_prize_line_count"] == 3
    assert result["attack_count"] == 2
    assert result["top_attaches"] == "18->Dwebble x1"


def test_submission_seat_and_aggregate_are_derived_from_episode_metadata():
    episodes = {
        "teams": [{"id": 1, "teamName": "mine"}, {"id": 2, "teamName": "other"}],
        "episodes": [
            {
                "id": 123,
                "type": "EPISODE_TYPE_PUBLIC",
                "agents": [
                    {"submissionId": 9, "teamId": 2, "reward": -1},
                    {"submissionId": 42, "teamId": 1, "reward": 1, "index": 1},
                ],
            }
        ],
    }

    assert summary.target_seat_map(episodes, 42) == {123: 1}
    metadata = summary.episode_metadata(episodes, 42)
    assert metadata[123]["opponent_team"] == "other"

    aggregate = summary.aggregate(
        [
            {"episode_type": "EPISODE_TYPE_PUBLIC", "reward": 1, "first_attack_line_count": 3,
             "first_prize_line_count": 3, "first_focus_attach_turn": 2,
             "first_attack_turn": 3, "first_prize_turn": 5, "missed_attack_turns_after_first": 0},
            {"episode_type": "EPISODE_TYPE_PUBLIC", "reward": -1, "first_attack_line_count": 1,
             "first_prize_line_count": None, "first_focus_attach_turn": None,
             "first_attack_turn": 4, "first_prize_turn": None, "missed_attack_turns_after_first": 2},
        ],
        3,
    )
    assert aggregate["win_rate"] == 0.5
    assert aggregate["win_rate_with_wide_first_attack"] == 1.0
    assert aggregate["win_rate_without_wide_first_attack"] == 0.0


def test_unique_team_can_resolve_gold_replay_without_submission_metadata():
    replay = {"info": {"TeamNames": ["opponent", "MPGaming"]}}
    assert summary.target_seat_from_team(replay, "MPGaming") == 1
    assert summary.target_seat_from_team(replay, "missing") is None
    assert summary.target_seat_from_team(
        {"info": {"TeamNames": ["MPGaming", "MPGaming"]}}, "MPGaming"
    ) is None


def test_focus_play_telemetry_handles_same_turn_later_and_no_attack(tmp_path):
    focus_play = {"type": summary.LOG_PLAY, "playerIndex": 1, "cardId": 1147}
    attack = {"type": summary.LOG_ATTACK, "playerIndex": 1, "attackId": 500}
    replay = {
        "info": {"EpisodeId": 124, "TeamNames": ["other", "mine"]},
        "rewards": [-1, 1],
        "steps": [
            [{}, entry(2, 6, 1, [], [focus_play, attack])],
            [{}, entry(2, 6, 1, [], [focus_play, attack])],
            [{}, entry(4, 6, 1, [], [focus_play, attack, focus_play])],
            [{}, entry(6, 6, 1, [], [focus_play, attack, focus_play, attack])],
        ],
    }
    replay_path = tmp_path / "episode_124_replay.json"
    replay_path.write_text(json.dumps(replay), encoding="utf-8")

    result = summary.summarize_replay(
        replay_path, 1, {1147: "Jumbo Ice Cream"}, {500: "Attack"},
        line_card_ids=set(), focus_energy_ids=set(), focus_target_ids=set(), focus_play_ids={1147},
    )

    assert result["focus_play_count"] == 2
    assert result["first_focus_play_turn"] == 2
    assert result["focus_play_turns_with_attack"] == 1
    assert result["first_attack_after_focus_turn"] == 2
    assert result["first_attack_after_focus_delay"] == 0
    assert result["attacks_after_first_focus_play"] == 2
    assert result["focus_play_recovered_to_attack"] is True

    no_focus_replay = {
        "info": {"EpisodeId": 125, "TeamNames": ["other", "mine"]},
        "rewards": [-1, -1],
        "steps": [[{}, entry(2, 6, 1, [], [attack])]],
    }
    no_focus_path = tmp_path / "episode_125_replay.json"
    no_focus_path.write_text(json.dumps(no_focus_replay), encoding="utf-8")
    no_focus = summary.summarize_replay(
        no_focus_path, 1, {}, {500: "Attack"},
        line_card_ids=set(), focus_energy_ids=set(), focus_target_ids=set(), focus_play_ids={1147},
    )
    assert no_focus["focus_play_count"] == 0
    assert no_focus["first_focus_play_turn"] is None
    assert no_focus["first_attack_after_focus_turn"] is None
    assert no_focus["first_attack_after_focus_delay"] is None
    assert no_focus["attacks_after_first_focus_play"] == 0
    assert no_focus["focus_play_recovered_to_attack"] is False

    later_attack_replay = {
        "info": {"EpisodeId": 126, "TeamNames": ["other", "mine"]},
        "rewards": [-1, 1],
        "steps": [
            [{}, entry(4, 6, 1, [], [focus_play])],
            [{}, entry(6, 6, 1, [], [focus_play, attack])],
        ],
    }
    later_attack_path = tmp_path / "episode_126_replay.json"
    later_attack_path.write_text(json.dumps(later_attack_replay), encoding="utf-8")
    later_attack = summary.summarize_replay(
        later_attack_path, 1, {}, {500: "Attack"},
        line_card_ids=set(), focus_energy_ids=set(), focus_target_ids=set(), focus_play_ids={1147},
    )
    assert later_attack["focus_play_turns_with_attack"] == 0
    assert later_attack["first_attack_after_focus_turn"] == 6
    assert later_attack["first_attack_after_focus_delay"] == 1
    assert later_attack["attacks_after_first_focus_play"] == 1
    assert later_attack["focus_play_recovered_to_attack"] is True


def test_focus_play_counts_terminal_attack_visible_only_on_opponent_frame(tmp_path):
    focus_play = {"type": summary.LOG_PLAY, "playerIndex": 1, "cardId": 1147}
    attack = {"type": summary.LOG_ATTACK, "playerIndex": 1, "attackId": 500}
    replay = {
        "info": {"EpisodeId": 127, "TeamNames": ["other", "mine"]},
        "rewards": [1, -1],
        "steps": [
            [{}, entry(7, 6, 345, [], [focus_play])],
            [entry(8, 6, 90, [], [focus_play, attack], status="DONE", your_index=0), {}],
        ],
    }
    replay_path = tmp_path / "episode_127_replay.json"
    replay_path.write_text(json.dumps(replay), encoding="utf-8")

    result = summary.summarize_replay(
        replay_path, 1, {1147: "Jumbo Ice Cream", 345: "Crustle"}, {500: "Attack"},
        line_card_ids={345}, focus_energy_ids=set(), focus_target_ids=set(), focus_play_ids={1147},
    )

    assert result["focus_play_count"] == 1
    assert result["attack_count"] == 1
    assert result["first_focus_play_turn"] == 7
    assert result["first_attack_after_focus_turn"] == 7
    assert result["focus_play_turns_with_attack"] == 1
    assert result["focus_play_recovered_to_attack"] is True
    assert result["attacks_after_first_focus_play"] == 1


def test_focus_play_aggregate_metrics():
    rows = [
        {"episode_type": "EPISODE_TYPE_PUBLIC", "reward": 1, "focus_play_count": 1,
         "focus_play_recovered_to_attack": True, "focus_play_turns_with_attack": 1,
         "attacks_after_first_focus_play": 2},
        {"episode_type": "EPISODE_TYPE_PUBLIC", "reward": -1, "focus_play_count": 1,
         "focus_play_recovered_to_attack": True, "focus_play_turns_with_attack": 0,
         "attacks_after_first_focus_play": 1},
        {"episode_type": "EPISODE_TYPE_PUBLIC", "reward": 1, "focus_play_count": 0,
         "focus_play_recovered_to_attack": False, "focus_play_turns_with_attack": 0,
         "attacks_after_first_focus_play": 0},
    ]
    result = summary.aggregate(rows, 3)
    assert result["focus_play_rate"] == 2 / 3
    assert result["focus_play_win_rate"] == 0.5
    assert result["no_focus_play_win_rate"] == 1.0
    assert result["focus_play_recovery_rate"] == 1.0
    assert result["focus_play_same_turn_attack_rate"] == 0.5
    assert result["median_attacks_after_first_focus_play"] == 1.5
