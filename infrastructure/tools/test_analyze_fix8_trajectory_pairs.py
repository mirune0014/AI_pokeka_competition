from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

import analyze_fix8_trajectory_pairs as trajectory

def option(index: int, typ: int, card_id: int | None = None, serial: int | None = None) -> dict:
    return {
        "option_index": index, "type": typ, "card_id": card_id, "serial": serial,
        "attack_id": None, "area": None, "in_play_area": None,
        "in_play_index": None, "player_index": None,
    }

def callback(
    ordinal: int, selected: dict, *, options: list[dict] | None = None,
    turn: int = 1, context: int = 0, marker: int = 0,
) -> trajectory.Callback:
    legal = list(options or [selected])
    selected_index = legal.index(selected)
    observation = {
        "turn": turn, "turn_action_count": ordinal + 1, "context": context,
        "select_type": 0, "min_count": 1, "max_count": 1,
        "option_count": len(legal), "options": legal, "own_hand": [[741, 1]],
        "own_active": [305, 2], "own_bench": [], "own_discard": [],
        "opponent_active": None, "opponent_active_hp": None, "result": -1,
    }
    snapshot = {
        "turn": turn, "turn_action_count": ordinal + 1, "your_index": 0,
        "p0_deck": 40 - marker, "p0_hand": 1, "p0_prizes": 6, "p0_bench_max": 5,
        "p0_active": 305, "p0_active_hp": 70, "p0_active_max_hp": 70,
        "p0_active_energy": 0, "p0_active_energy_ids": [], "p0_active_tool_ids": [],
        "p0_bench": [], "p0_bench_hp": [], "p0_bench_max_hp": [],
        "p0_bench_energy": [], "p0_bench_energy_ids": [], "p0_bench_tool_ids": [],
        "p1_deck": 40, "p1_hand": 7, "p1_prizes": 6, "p1_bench_max": 5,
        "p1_active": 900, "p1_active_hp": 100, "p1_active_max_hp": 100,
        "p1_active_energy": 1, "p1_active_energy_ids": [19], "p1_active_tool_ids": [],
        "p1_bench": [], "p1_bench_hp": [], "p1_bench_max_hp": [],
        "p1_bench_energy": [], "p1_bench_energy_ids": [], "p1_bench_tool_ids": [],
    }
    return trajectory.Callback(
        ordinal,
        {"callback_ordinal": ordinal, "observation": observation},
        {
            "callback_ordinal": ordinal, "selected_action": [selected_index],
            "selected_options": [selected], "structurally_valid": True,
            "exception": None,
        },
        {
            "game": 0, "step": ordinal, "player": 0, "context": context,
            "select_type": 0, "min_count": 1, "max_count": 1,
            "option_count": len(legal), "action": [selected_index],
            "own_hand_ids": [741], "snapshot": snapshot, "logs": [],
        },
    )

class SemanticTests(unittest.TestCase):
    def test_option_index_is_not_semantic_but_serial_is(self) -> None:
        left = option(0, 7, 1086, 26)
        reordered = option(3, 7, 1086, 26)
        other_serial = option(0, 7, 1086, 99)
        self.assertEqual(trajectory.semantic_multiset([left]), trajectory.semantic_multiset([reordered]))
        self.assertNotEqual(trajectory.semantic_multiset([left]), trajectory.semantic_multiset([other_serial]))
        self.assertEqual(
            trajectory.semantic_multiset([left], include_serial=False),
            trajectory.semantic_multiset([other_serial], include_serial=False),
        )

class PairingTests(unittest.TestCase):
    def test_strict_callback_pairing(self) -> None:
        rows = []
        for ordinal in range(2):
            common = {
                "callback_ordinal": ordinal, "run_id": "run", "version": "fix8",
                "opponent": "opp", "policy_seat": 0, "game": 0, "seed": 123, "seed_base": 123,
            }
            rows.extend([{**common, "event": "CALL_START"}, {**common, "event": "CALL_END"}])
        pairs = trajectory.pair_callback_events(
            rows, version="fix8", opponent="opp", seat=0, seed=123,
        )
        self.assertEqual([pair[0]["callback_ordinal"] for pair in pairs], [0, 1])

    def test_orphan_is_rejected(self) -> None:
        with self.assertRaises(trajectory.IntegrityError):
            trajectory.pair_callback_events([{
                "callback_ordinal": 0, "run_id": "run", "version": "fix8",
                "opponent": "opp", "policy_seat": 0, "game": 0,
                "seed": 123, "seed_base": 123, "event": "CALL_START",
            }])

class DivergenceTests(unittest.TestCase):
    def test_equal_pre_state_semantic_action_split(self) -> None:
        poffin, end = option(0, 7, 1086, 26), option(1, 14)
        legal = [poffin, end]
        baseline = [callback(0, poffin, options=legal)]
        candidate = [callback(0, end, options=legal)]
        result = trajectory.first_semantic_divergence(baseline, candidate)
        self.assertTrue(result["found"])
        self.assertEqual(result["ordinal"], 0)
        self.assertTrue(result["divergence_pre_observation_equal"])
        self.assertTrue(result["divergence_semantic_legal_equal"])

    def test_no_split_is_retained_as_mechanical_status(self) -> None:
        end = option(0, 14)
        rows = [callback(0, end)]
        result = trajectory.first_semantic_divergence(rows, rows)
        self.assertFalse(result["found"])
        self.assertEqual(result["reason"], "NO_SEMANTIC_ACTION_SPLIT")

class RejoinTests(unittest.TestCase):
    def test_rejoin_requires_three_following_callbacks(self) -> None:
        end = option(0, 14)
        baseline = [callback(i, end, turn=i + 1) for i in range(5)]
        candidate = [
            callback(i, end, turn=i + 1, marker=1 if i == 0 else 0)
            for i in range(5)
        ]
        result = trajectory.find_certified_observable_rejoin(
            baseline, candidate, baseline_start=1, candidate_start=1, seat=0,
        )
        self.assertTrue(result["certified_observable_rejoin"])
        self.assertEqual(result["following_callbacks_verified"], 3)
        result = trajectory.find_certified_observable_rejoin(
            baseline[:-1], candidate[:-1], baseline_start=1, candidate_start=1, seat=0,
        )
        self.assertFalse(result["certified_observable_rejoin"])


class SuiteLayoutTests(unittest.TestCase):
    def test_single_and_per_opponent_suite_layouts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            child = trajectory.resolve_suite_layout(root, ["a", "b"])
            self.assertEqual(child["a"], (root / "a").resolve())
            (root / "suite_execution_summary.json").write_text("{}", encoding="utf-8")
            single = trajectory.resolve_suite_layout(root, ["a", "b"])
            self.assertEqual(set(single.values()), {root.resolve()})

class OutcomeAndTraceTests(unittest.TestCase):
    def test_policy_side_outcome_check(self) -> None:
        self.assertTrue(trajectory.outcome_check({"result": 1}, 1, 1)["matches_source"])
        self.assertFalse(trajectory.outcome_check({"result": 0}, 1, 1)["matches_source"])

    def test_nested_fix8_trace_is_preferred(self) -> None:
        trace, path = trajectory.fix8_trace_from_end({
            "version_trace": {
                "stage": "OUTER",
                "parent_trace": {
                    "LAST_V4_POFFIN_ZERO_VETO_TRACE": {"stage": "HOLD", "reason": "TEST"}
                },
            }
        })
        self.assertEqual(trace["stage"], "HOLD")
        self.assertEqual(path, "version_trace.parent_trace.LAST_V4_POFFIN_ZERO_VETO_TRACE")

if __name__ == "__main__":
    unittest.main()
