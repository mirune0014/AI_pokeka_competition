import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "run_seeded_paired_suite.py"
SPEC = importlib.util.spec_from_file_location("seeded_paired_suite", MODULE_PATH)
suite = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(suite)


def record(seed, result, steps=10, turn=5, action_errors=0, hit_max_steps=False):
    return {"seed": seed, "result": result, "steps": steps, "turn": turn,
            "action_errors": action_errors, "hit_max_steps": hit_max_steps}


def test_policy_win_is_seat_aware():
    assert suite.policy_won(record(1, 0), 0)
    assert not suite.policy_won(record(1, 1), 0)
    assert suite.policy_won(record(1, 1), 1)
    assert not suite.policy_won(record(1, 0), 1)


def test_duplicate_mismatches_compare_all_required_fields():
    left = [record(10, 0), record(11, 1)]
    assert suite.duplicate_mismatches(left, [record(10, 0), record(11, 1)]) == []
    mismatch = suite.duplicate_mismatches(left, [record(10, 0), record(11, 1, steps=11)])
    assert len(mismatch) == 1
    assert mismatch[0]["game"] == 1


def test_aggregate_deltas_are_seat_aware():
    cells = [
        {"seed_base": 7, "opponent": "alpha", "seat": 0, "baseline": [record(7, 0), record(8, 1)], "candidate": [record(7, 0), record(8, 1)]},
        {"seed_base": 7, "opponent": "alpha", "seat": 1, "baseline": [record(7, 0), record(8, 1)], "candidate": [record(7, 1), record(8, 1)]},
    ]
    result = suite.summarize_cells(cells)
    assert result["aggregates"] == {"baseline_wins": 2, "candidate_wins": 3, "games": 4, "delta_wins": 1}
    assert result["by_opponent"][0]["delta_wins"] == 1


def test_parse_opponent_supports_windows_paths():
    name, path = suite.parse_opponent(r"mirror=C:\\agents\\mirror")
    assert name == "mirror"
    assert path == Path(r"C:\\agents\\mirror")


def test_command_has_explicit_decks_and_engine_seed(tmp_path):
    command = suite.build_command(engine_dir=tmp_path / "engine", policy_dir=tmp_path / "policy", opponent_dir=tmp_path / "opponent",
                                  policy_seat=1, seed_base=42, games_per_seat=2, max_steps=100,
                                  summary_path=tmp_path / "summary.jsonl", trace_dir=tmp_path / "trace", python_executable="python.exe")
    assert command[:2] == ["python.exe", str(suite.RUN_LOCAL_BATTLE)]
    assert "--engine-seed" in command
    assert command[command.index("--agent-a") + 1] == str(tmp_path / "opponent")
    assert command[command.index("--agent-b") + 1] == str(tmp_path / "policy")
    assert command[command.index("--deck-a") + 1] == str(tmp_path / "opponent" / "deck.csv")
