import tempfile
import unittest
from pathlib import Path
from research.rl_ptcg.gold_upper_tier_states import (
    _write_bytes_once, assert_no_gold_candidate_tags, eligible_state, exact_rule_candidates,
    multiset_replacement_distance, parse_state_spec, verify_gold_upper_tier_states,
)

def row(seat, deck, **extra):
    return {"episode_id": "e", "player_index": str(seat), "file": "x.json", "replay_sha256": "a" * 64, "match_timestamp_utc": "2026-07-10T00:00:00+00:00", "archetype": "archaludon_metal" if seat == 0 else "other", "deck": " ".join(map(str, deck)), **extra}

class UpperTierStatesTest(unittest.TestCase):
    def test_state_spec_and_distance(self):
        self.assertEqual(("ep", 1, 7), parse_state_spec("ep:1:7")); self.assertEqual(1, multiset_replacement_distance([1] * 59 + [2], [1] * 60))
        with self.assertRaises(ValueError): parse_state_spec("bad")
    def test_blind_rejected_before_replay_loading(self):
        deck = list(range(60)); actor, opponent = row(0, deck), row(1, deck)
        gold = row(1, deck, gold_rank="1", gold_proxy_confidence="postgame_same_submission")
        with self.assertRaisesRegex(ValueError, "blind date"):
            eligible_state("e", 0, [actor, opponent], [gold], {"2026-07-10"}, deck, 4)
    def test_exact_gold_join_required(self):
        deck = list(range(60)); actor, opponent = row(0, deck), row(1, deck)
        gold = row(1, deck, gold_rank="20", gold_proxy_confidence="postgame_same_submission")
        self.assertEqual("20", eligible_state("e", 0, [actor, opponent], [gold], set(), deck, 4)[2]["gold_rank"])
        with self.assertRaises(ValueError): eligible_state("e", 0, [actor, opponent], [], set(), deck, 4)
    def test_verifier_rejects_missing_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError): verify_gold_upper_tier_states(Path(temp))
    def test_candidate_set_never_accepts_gold_tag(self):
        assert_no_gold_candidate_tags([{"source_tags": ["baseline", "rule_diverse"]}])
        with self.assertRaisesRegex(ValueError, "Gold"):
            assert_no_gold_candidate_tags([{"source_tags": ["gold"]}])
    def test_exact_rule_candidates_never_add_recorded_gold(self):
        observation = {"current": {"yourIndex": 0}, "select": {"context": 0, "minCount": 1, "maxCount": 1,
            "option": [{"type": 1}, {"type": 2}]}}
        candidates, sets = exact_rule_candidates(observation, [2.0, 1.0], [0], top_k=1, max_diverse=2)
        self.assertEqual(sets["rule_diverse"], sets["rule_plus_gold"])
        assert_no_gold_candidate_tags(candidates)
    def test_raw_write_once_rejects_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "states.jsonl"; _write_bytes_once(path, b"{}\n")
            _write_bytes_once(path, b"{}\n")
            with self.assertRaises(FileExistsError): _write_bytes_once(path, b"{\"x\":1}\n")
