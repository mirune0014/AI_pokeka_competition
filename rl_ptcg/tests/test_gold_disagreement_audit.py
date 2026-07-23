import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace

from rl_ptcg.gold_disagreement_audit import (
    DEFAULT_SOURCES, _summary_metrics, make_sample_manifest, rank_complete_actions, sample_records,
    same_state_agreement, selection_stratum, write_once_json,
)


def record(identifier, own="neutral", opponent="other", *, disagreement=False):
    return SimpleNamespace(decision_id=identifier, own_archetype=own, opponent_archetype=opponent,
                           disagreement=disagreement)


def observation(options, minimum=1, maximum=1):
    return {"current": {"yourIndex": 0, "players": [{"hand": [], "active": [], "bench": [], "discard": []}, {"hand": [], "active": [], "bench": [], "discard": []}]},
            "select": {"context": 7, "minCount": minimum, "maxCount": maximum, "option": options}}


class GoldDisagreementAuditTests(unittest.TestCase):
    def test_deterministic_sample_is_independent_of_input_order_and_disagreement(self):
        values = [record("d%d" % value, disagreement=value % 2 == 0) for value in range(20)]
        first, _ = sample_records(values, target_count=8, seed="x")
        second, _ = sample_records(reversed(values), target_count=8, seed="x")
        self.assertEqual([item.decision_id for item in first], [item.decision_id for item in second])
        flipped = [record(item.decision_id, disagreement=not item.disagreement) for item in values]
        third, _ = sample_records(flipped, target_count=8, seed="x")
        self.assertEqual([item.decision_id for item in first], [item.decision_id for item in third])

    def test_category_quota_then_deterministic_fill(self):
        values = [record("a%d" % i, "Archaludon") for i in range(2)]
        values += [record("o%d" % i, "other", "Archaludon") for i in range(2)]
        values += [record("m%d" % i, "Mega Lucario") for i in range(2)]
        values += [record("n%d" % i) for i in range(10)]
        selected, quota = sample_records(values, target_count=10, seed="quota")
        self.assertEqual(10, len(selected))
        self.assertEqual(2, quota["realized"]["own_archaludon"])
        self.assertEqual(2, quota["realized"]["gold_opponent_vs_archaludon"])
        self.assertEqual(2, quota["realized"]["mega_lucario"])

    def test_archetype_stratum_normalizes_separators(self):
        self.assertEqual("mega_lucario", selection_stratum(record("m", "mega_lucario")))
        self.assertEqual("own_archaludon", selection_stratum(record("a", "archaludon_metal")))

    def test_manifest_has_no_blind_source(self):
        manifest = make_sample_manifest([record("one")], target_count=512, seed="s", dataset_hash="d", split_hash="p", baseline_map_hash="b")
        self.assertEqual(DEFAULT_SOURCES, tuple(manifest["source_splits"]))
        self.assertNotIn("blind", manifest["source_splits"])

    def test_manifest_write_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample_manifest.json"
            write_once_json(path, {"a": 1})
            write_once_json(path, {"a": 1})
            with self.assertRaises(FileExistsError): write_once_json(path, {"a": 2})

    def test_semantic_complete_rank_deduplicates_option_reorder(self):
        left = {"type": 1, "cardId": 7, "playerIndex": 0}
        right = {"type": 1, "cardId": 7, "playerIndex": 0}
        result = rank_complete_actions(observation([left, right], 1, 1), [3.0, 2.0], [0], [1], max_complete_actions=8)
        self.assertEqual("exact", result["scope"])
        self.assertEqual(1, result["candidate_count"])
        self.assertEqual(1, result["gold_rank"])
        reordered = rank_complete_actions(observation([right, left], 1, 1), [2.0, 3.0], [1], [0], max_complete_actions=8)
        self.assertEqual(result["gold_semantic_id"], reordered["gold_semantic_id"])

    def test_truncated_flag_and_gold_is_injected(self):
        options = [{"type": 1, "cardId": i, "playerIndex": 0} for i in range(8)]
        result = rank_complete_actions(observation(options, 1, 4), list(range(8)), [0], [6], max_complete_actions=3)
        self.assertEqual("truncated", result["scope"])
        self.assertTrue(result["gold_feasible"])
        self.assertFalse(result["gold_generated"])
        self.assertTrue(result["gold_injected_for_ranking"])

    def test_exact_generator_reports_gold_as_generated(self):
        options = [{"type": 1, "cardId": i, "playerIndex": 0} for i in range(3)]
        result = rank_complete_actions(observation(options, 1, 1), [3.0, 2.0, 1.0], [0], [2], max_complete_actions=8)
        self.assertTrue(result["gold_generated"])
        self.assertFalse(result["gold_injected_for_ranking"])

    def test_summary_excludes_unranked_rows_from_rank_denominator(self):
        rows = [
            {"semantic_equal": True, "rule_rank_available": True, "gold_top3": True, "gold_top10": True, "gold_generated": True},
            {"semantic_equal": False, "rule_rank_available": False, "gold_top3": None, "gold_top10": None, "gold_generated": True},
            {"error": "failed"},
        ]
        summary = _summary_metrics(rows)
        self.assertEqual(2, summary["valid_count"])
        self.assertEqual(1, summary["rankable_count"])
        self.assertEqual(1, summary["unranked_count"])
        self.assertEqual(1.0, summary["gold_top3_rate"])
        self.assertEqual(0.5, summary["semantic_equal_rate"])

    def test_same_state_cross_style_agreement_and_zero_coverage(self):
        rows = [{"state_id": "s", "style_id": "a", "gold_semantic_id": "x"}, {"state_id": "s", "style_id": "b", "gold_semantic_id": "x"}]
        self.assertEqual(1.0, same_state_agreement(rows)["coverage"])
        self.assertEqual(0.0, same_state_agreement(rows[:1])["coverage"])

    def test_malformed_baseline_and_source_inputs_fail_closed(self):
        with self.assertRaises(ValueError): rank_complete_actions(observation([{"type": 1}], 1, 1), [], [0], [0], max_complete_actions=2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{not-json", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError): json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
