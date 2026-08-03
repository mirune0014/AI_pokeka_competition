from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "infrastructure" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import alakazam_staged_metrics as metrics
import summarize_alakazam_staged_metrics as summarizer
class _MonkeyPatch:
    def __init__(self):
        self._previous = {}

    def setenv(self, key: str, value: str) -> None:
        if key not in self._previous:
            self._previous[key] = os.environ.get(key)
        os.environ[key] = value

    def undo(self) -> None:
        for key, value in self._previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class _Raises:
    def __init__(self, exception_type, match: str | None = None):
        self.exception_type = exception_type
        self.match = match

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        if exception_type is None:
            raise AssertionError(f"{self.exception_type.__name__} was not raised")
        if not issubclass(exception_type, self.exception_type):
            return False
        if self.match is not None and self.match not in str(exception):
            raise AssertionError(f"{exception!r} does not contain {self.match!r}")
        return True


class _PytestCompat:
    MonkeyPatch = _MonkeyPatch

    @staticmethod
    def raises(exception_type, match: str | None = None):
        return _Raises(exception_type, match)


pytest = _PytestCompat()


def minimal_obs() -> dict:
    return {
        "current": {
            "turn": 3,
            "turnActionCount": 4,
            "yourIndex": 0,
            "firstPlayer": 0,
            "result": -1,
            "players": [
                {
                    "hand": [{"id": 1184, "serial": 40}],
                    "active": [
                        {
                            "id": 743,
                            "serial": 9,
                            "hp": 310,
                            "energyCards": [{"id": 1231, "serial": 45}],
                        }
                    ],
                    "bench": [{"id": 741, "serial": 1}],
                    "discard": [{"id": 1197, "serial": 41}],
                },
                {
                    "hand": None,
                    "active": [
                        {
                            "id": 100,
                            "serial": 70,
                            "hp": 120,
                            "energyCards": [{"id": 1231, "serial": 101}],
                        }
                    ],
                    "bench": [],
                    "discard": [],
                },
            ],
        },
        "select": {
            "context": 0,
            "type": 0,
            "minCount": 1,
            "maxCount": 1,
            "option": [
                {"type": 7, "index": 0},
                {"type": 13, "attackId": metrics.HAND_POWER_ATTACK_ID},
            ],
        },
        "logs": [
            {
                "type": 10,
                "playerIndex": 0,
                "cardId": 1197,
                "serial": 41,
            }
        ],
    }


def callback(
    *,
    ordinal: int,
    turn: int,
    attack: bool,
    hand: int = 6,
    trace: dict | None = None,
) -> dict:
    option = (
        {"option_index": 0, "type": 13, "attack_id": metrics.HAND_POWER_ATTACK_ID}
        if attack
        else {"option_index": 0, "type": 14}
    )
    return {
        "start": {
            "version": "v0",
            "opponent": "test",
            "policy_seat": 0,
            "game": 0,
            "seed": 1,
            "callback_ordinal": ordinal,
            "observation": {
                "turn": turn,
                "context": 0,
                "own_hand": [[1, value] for value in range(hand)],
                "own_active": [743, 9],
                "own_bench": [],
                "own_discard": [],
                "opponent_active": [100, 70],
                "opponent_active_hp": 130,
                "logs_raw": [],
            },
        },
        "end": {
            "selected_options": [option],
            "decision_ns": 100 + ordinal,
            "structurally_valid": True,
            "exception": None,
            "parent_fallback_selected": False,
            "first_legal_fallback_selected": False,
            "generic_fallback_status": "UNKNOWN",
            "generic_handler_hits": [],
            "removed_rule_hit_status": "UNKNOWN",
            "version_trace": trace,
        },
    }


def test_snapshot_preserves_serials_and_raw_log_serial_fields():
    snapshot = metrics.observation_snapshot(minimal_obs())
    assert snapshot["own_hand"] == [[1184, 40]]
    assert snapshot["own_active"] == [743, 9]
    assert snapshot["opponent_active"] == [100, 70]
    assert snapshot["opponent_active_energy"] == [[1231, 101]]
    assert snapshot["log_serial_fields"][0]["serial"] == 41


def test_structural_legality_rejects_duplicate_and_out_of_range():
    obs = minimal_obs()
    assert metrics.structural_action_status(obs, [1])["valid"] is True
    status = metrics.structural_action_status(obs, [2, 2])
    assert status["valid"] is False
    assert "DUPLICATE_INDEX" in status["reasons"]
    assert "INDEX_OUT_OF_RANGE" in status["reasons"]


def test_v0_generic_hold_is_handler_hit_not_generic_fallback():
    normalized = metrics.normalized_trace_fields(
        [],
        "LAST_V0_PORT_TRACE",
        {"reason_tags": ["V0_GENERIC_HOLD"]},
    )
    assert normalized["generic_handler_hits"] == ["V0_GENERIC_HOLD"]
    assert normalized["generic_fallback_selected"] is False
    assert normalized["generic_fallback_status"] == "KNOWN"
    forced = metrics.normalized_trace_fields(
        [],
        "LAST_V0_PORT_TRACE",
        {"reason_tags": ["V0_GENERIC_FORCED_DISCARD"]},
    )
    assert forced["generic_fallback_selected"] is True
    assert forced["generic_fallback_status"] == "KNOWN"
    unknown = metrics.normalized_trace_fields([], "", None)
    assert unknown["generic_fallback_selected"] is None
    assert unknown["generic_fallback_status"] == "UNKNOWN"
    for classification in (
        "ADMISSIBILITY_REJECT",
        "PLACEHOLDER_PARENT_FALLBACK",
        "PARITY_PARENT_FALLBACK",
    ):
        fallback = metrics.normalized_trace_fields(
            [{"classification": classification}], "", None
        )
        assert fallback["parent_fallback_selected"] is True
        assert fallback["first_legal_fallback_selected"] is False
    emergency = metrics.normalized_trace_fields(
        [{"classification": "EMERGENCY_LOWEST_LEGAL"}], "", None
    )
    assert emergency["parent_fallback_selected"] is False
    assert emergency["first_legal_fallback_selected"] is True


def test_integrated_suffix_detects_append_and_reset():
    module = type(sys)("trace_module")
    module.INTEGRATED_TRACE_LOG = [{"classification": "A"}]
    owner, before = metrics.integrated_log_state([module])
    module.INTEGRATED_TRACE_LOG.append({"classification": "B"})
    _, suffix, reset = metrics.integrated_suffix(owner, before, [module])
    assert suffix == [{"classification": "B"}]
    assert reset is False
    module.INTEGRATED_TRACE_LOG[:] = [{"classification": "C"}]
    _, suffix, reset = metrics.integrated_suffix(owner, before, [module])
    assert suffix == [{"classification": "C"}]
    assert reset is True


def test_pair_callback_events_keeps_start_without_end_as_diagnostic():
    common = {
        "run_id": "r",
        "version": "v",
        "opponent": "o",
        "policy_seat": 0,
        "game": 0,
        "seed": 1,
        "callback_ordinal": 0,
    }
    complete, diagnostics = metrics.pair_callback_events(
        [{**common, "event": "CALL_START"}]
    )
    assert complete == []
    assert diagnostics[0]["kind"] == "CALL_START_WITHOUT_END"


def test_game_metrics_attack_gap_units_and_unknown_ko_guard():
    assert metrics.HAND_POWER_ATTACK_ID == 1072
    callbacks = [
        callback(ordinal=0, turn=3, attack=True, hand=6),
        callback(ordinal=1, turn=5, attack=False),
        callback(ordinal=2, turn=7, attack=True, hand=7),
        callback(ordinal=3, turn=9, attack=False),
    ]
    callbacks[0]["start"]["observation"]["own_bench"] = [[741, 1]]
    summary = {
        "started": True,
        "result": 0,
        "steps": 10,
        "hit_max_steps": False,
        "action_errors": 0,
    }
    row = metrics.game_metrics(callbacks, summary, timed_out=False)
    assert row["second_alakazam_line_before_first_hand_power"] is True
    assert row["attack_gap_tail_count"] == 2
    assert row["attack_gap_tail_denominator"] == 4
    assert row["attack_gap_between_count"] == 1
    assert row["max_consecutive_attack_turns"] == 1
    assert row["hand_power_attacks"][0]["damage_counters"] == 12
    assert row["hand_power_attacks"][0]["damage"] == 120
    assert row["certified_clear_ko_miss_count"] is None
    assert row["certified_clear_ko_miss_denominator"] == 0
    single_line = [
        callback(ordinal=0, turn=3, attack=False),
        callback(ordinal=1, turn=3, attack=False),
        callback(ordinal=2, turn=3, attack=True),
    ]
    for item, pair in zip(single_line, ([741, 1], [742, 2], [743, 3])):
        item["start"]["observation"]["own_active"] = pair
    single_row = metrics.game_metrics(single_line, summary, timed_out=False)
    assert single_row["second_alakazam_line_before_first_hand_power"] is False


def test_post_ko_continuity_certification_and_next_main_turn():
    summary = {
        "started": True,
        "result": 0,
        "steps": 10,
        "hit_max_steps": False,
        "action_errors": 0,
    }

    def death_callback(ordinal: int, turn: int, serial: int = 9) -> dict:
        item = callback(ordinal=ordinal, turn=turn, attack=False)
        item["start"]["observation"]["context"] = 4
        item["start"]["observation"]["logs_raw"] = [
            {
                "type": metrics.LOG_MOVE_CARD,
                "playerIndex": 0,
                "fromArea": metrics.AREA_ACTIVE,
                "toArea": metrics.AREA_DISCARD,
                "cardId": metrics.ALAKAZAM_ID,
                "serial": serial,
            }
        ]
        return item

    continued = [
        callback(ordinal=0, turn=3, attack=True),
        death_callback(ordinal=1, turn=5),
        callback(ordinal=2, turn=5, attack=True),
    ]
    continued_row = metrics.game_metrics(continued, summary, timed_out=False)
    assert continued_row["post_ko_continuity_count"] == 1
    assert continued_row["post_ko_continuity_denominator"] == 1

    missed = [
        callback(ordinal=0, turn=3, attack=True),
        death_callback(ordinal=1, turn=5),
        callback(ordinal=2, turn=5, attack=False),
        callback(ordinal=3, turn=7, attack=True),
    ]
    missed_row = metrics.game_metrics(missed, summary, timed_out=False)
    assert missed_row["post_ko_continuity_count"] == 0
    assert missed_row["post_ko_continuity_denominator"] == 1

    terminal = [
        callback(ordinal=0, turn=3, attack=True),
        death_callback(ordinal=1, turn=5),
    ]
    terminal_row = metrics.game_metrics(terminal, summary, timed_out=False)
    assert terminal_row["post_ko_continuity_count"] is None
    assert terminal_row["post_ko_continuity_denominator"] == 0

    non_attack = [death_callback(ordinal=0, turn=5)]
    non_attack_row = metrics.game_metrics(non_attack, summary, timed_out=False)
    assert non_attack_row["post_ko_events"] == []
    assert non_attack_row["post_ko_continuity_denominator"] == 0


def test_metric_aggregate_required_columns_and_denominators():
    game = {
        "version": "v0",
        "opponent": "op",
        "seat": 0,
        "formal_rate_eligible": True,
        "started": True,
        "checked_join_status": "MATCH",
        "timed_out": False,
        "hit_max_steps": False,
        "callback_count": 4,
        "first_attack_turn": 3,
        "max_consecutive_attack_turns": 2,
        "attack_gap_tail_count": 1,
        "attack_gap_tail_denominator": 3,
        "attack_gap_between_count": 0,
        "attack_gap_between_denominator": 2,
        "attack_hand_sizes": [6],
        "hand_power_attacks": [{"damage_counters": 12, "damage": 120}],
        "post_ko_continuity_count": None,
        "post_ko_continuity_denominator": 0,
        "second_alakazam_line_before_first_hand_power": True,
        "certified_clear_ko_miss_count": None,
        "certified_clear_ko_miss_denominator": 0,
        "added_slot_exposed_serials": [
            {"card_id": 1184, "serial": 40},
            {"card_id": 1197, "serial": 41},
            {"card_id": 743, "serial": 9},
        ],
        "added_slot_played_serials": [{"card_id": 1184, "serial": 40}],
        "added_new_only_unused_serials": [{"card_id": 1197, "serial": 41}],
        "generic_fallback_selected_count": 0,
        "generic_fallback_known_callbacks": 4,
        "generic_handler_callback_count": 1,
        "parent_fallback_selected_count": 1,
        "first_legal_fallback_selected_count": 0,
        "removed_rule_hit_count": None,
        "removed_rule_hit_callback_count": None,
        "removed_rule_hit_known_callbacks": 0,
        "invalid_callback_count": 0,
        "exception_callback_count": 0,
        "_decision_values": [10, 20, 30, 40],
    }
    aggregate = next(
        row
        for row in summarizer.aggregate_rows([game])
        if row["opponent"] == "op" and row["seat"] == 0
    )
    assert aggregate["first_attack_turn_mean"] == 3
    assert aggregate["max_consecutive_attack_turns_mean"] == 2
    assert aggregate["attack_hand_observations"] == 1
    assert aggregate["hand_size_at_attack_mean"] == 6
    assert aggregate["hand_power_attack_count"] == 1
    assert aggregate["hand_power_counter_total"] == 12
    assert aggregate["hand_power_damage_total"] == 120
    assert aggregate["added_new_only_exposed_serial_count"] == 2
    assert aggregate["added_new_only_played_serial_count"] == 1
    assert aggregate["added_new_only_unused_serial_count"] == 1
    assert aggregate["added_card_play_rate"] == 0.5
    assert aggregate["unused_added_card_rate"] == 0.5
    assert aggregate["generic_fallback_selected_rate"] == 0.0
    assert aggregate["removed_rule_hit_count"] is None
    assert aggregate["removed_rule_hit_status"] == "UNKNOWN"
    assert aggregate["removed_rule_hit_rate"] is None
    assert aggregate["invalid_action_rate"] == 0.0
    assert aggregate["exception_game_denominator_scheduled"] == 1
    assert aggregate["timeout_game_denominator_scheduled"] == 1
    assert aggregate["max_step_game_denominator_started"] == 1


def test_nearest_rank_p95():
    assert metrics.nearest_rank_p95([]) is None
    assert metrics.nearest_rank_p95(list(range(1, 21))) == 19


def test_wrapper_flushes_start_and_end_then_reraises_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    target = tmp_path / "target"
    target.mkdir()
    (target / "main.py").write_text(
        "def agent(obs):\n    raise ValueError('boom')\n",
        encoding="utf-8",
    )
    sidecars = tmp_path / "sidecars"
    monkeypatch.setenv("ALAKAZAM_METRIC_SIDECAR_DIR", str(sidecars))
    monkeypatch.setenv("ALAKAZAM_METRIC_RUN_ID", "test")
    monkeypatch.setenv("ALAKAZAM_METRIC_OPPONENT", "op")
    monkeypatch.setenv("ALAKAZAM_METRIC_POLICY_SEAT", "0")
    monkeypatch.setenv("ALAKAZAM_METRIC_SEED_BASE", "10")
    agent, _ = metrics.build_metric_entrypoint(
        adapter_file=str(tmp_path / "main.py"),
        module_name="agent_a_0",
        version="raise",
        target_dir=str(target),
    )
    with pytest.raises(ValueError, match="boom"):
        agent(minimal_obs())
    rows = [
        json.loads(line)
        for line in (sidecars / "game_0000.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [row["event"] for row in rows] == ["CALL_START", "CALL_END"]
    assert rows[1]["exception"]["type"] == "ValueError"


def test_callback_target_path_and_cwd_are_restored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    target = tmp_path / "target"
    target.mkdir()
    (target / "planner_probe.py").write_text("VALUE = 0\n", encoding="utf-8")
    (target / "main.py").write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "import planner_probe\n"
        "def agent(obs):\n"
        "    assert Path.cwd() == Path(__file__).resolve().parent\n"
        "    assert sys.path[0] == str(Path(__file__).resolve().parent)\n"
        "    return [planner_probe.VALUE]\n",
        encoding="utf-8",
    )
    sidecars = tmp_path / "sidecars"
    monkeypatch.setenv("ALAKAZAM_METRIC_SIDECAR_DIR", str(sidecars))
    monkeypatch.setenv("ALAKAZAM_METRIC_POLICY_SEAT", "0")
    monkeypatch.setenv("ALAKAZAM_METRIC_SEED_BASE", "10")
    before_path, before_cwd = list(sys.path), Path.cwd()
    agent, _ = metrics.build_metric_entrypoint(
        adapter_file=str(tmp_path / "main.py"),
        module_name="agent_a_0",
        version="isolation",
        target_dir=str(target),
    )
    assert list(sys.path) == before_path
    assert Path.cwd() == before_cwd
    assert agent(minimal_obs()) == [0]
    assert list(sys.path) == before_path
    assert Path.cwd() == before_cwd
class TestAlakazamStagedMetrics(unittest.TestCase):
    def test_snapshot(self):
        test_snapshot_preserves_serials_and_raw_log_serial_fields()

    def test_structural_legality(self):
        test_structural_legality_rejects_duplicate_and_out_of_range()

    def test_v0_generic_hold(self):
        test_v0_generic_hold_is_handler_hit_not_generic_fallback()

    def test_integrated_suffix(self):
        test_integrated_suffix_detects_append_and_reset()

    def test_event_pairing(self):
        test_pair_callback_events_keeps_start_without_end_as_diagnostic()

    def test_game_metrics(self):
        test_game_metrics_attack_gap_units_and_unknown_ko_guard()

    def test_post_ko_continuity(self):
        test_post_ko_continuity_certification_and_next_main_turn()

    def test_metric_aggregate(self):
        test_metric_aggregate_required_columns_and_denominators()

    def test_nearest_rank(self):
        test_nearest_rank_p95()

    def test_wrapper_exception(self):
        with tempfile.TemporaryDirectory() as raw:
            patcher = _MonkeyPatch()
            try:
                test_wrapper_flushes_start_and_end_then_reraises_original(
                    Path(raw), patcher
                )
            finally:
                patcher.undo()

    def test_callback_isolation(self):
        with tempfile.TemporaryDirectory() as raw:
            patcher = _MonkeyPatch()
            try:
                test_callback_target_path_and_cwd_are_restored(Path(raw), patcher)
            finally:
                patcher.undo()


if __name__ == "__main__":
    unittest.main()
