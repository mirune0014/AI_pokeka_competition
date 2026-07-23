import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from rl_ptcg.gold_direct_policy_gate import (
    action_self_card_dependencies,
    build_gate_rows,
    deck_replacement_distance,
    multiset_overlap,
    run_gate,
    summarize_rows,
    verify_gate_output,
)


ROOT = Path(__file__).resolve().parents[2]


def candidate(card_id, semantic_id="gold"):
    return {
        "semantic_id": semantic_id,
        "source_tags": ["gold"],
        "canonical": {
            "minimum_count": 1,
            "maximum_count": 1,
            "selection_context": 0,
            "selections": [{
                "action_type": 7,
                "source_card_id": card_id,
                "source_relation": "self",
                "source_zone": "hand",
                "target_card_id": None,
                "target_relation": "self",
                "target_zone": None,
                "effect_source_id": None,
                "selection_context": 0,
                "attack_id": None,
                "count": None,
                "number": None,
                "remaining_cost": {"energy": 0, "damage_counter": 0},
                "special_condition": None,
            }],
        },
    }


def state(state_id, source_deck, card_id, archetype="archaludon_metal"):
    return {
        "state_id": state_id,
        "decision_id": "decision-" + state_id,
        "episode_id": "episode-" + state_id,
        "submission_id": "submission",
        "style_id": "style",
        "current_metadata": {"own_archetype": archetype},
        "own_deck": {"decklist": source_deck, "sha256": "source-sha"},
        "candidates": [candidate(card_id)],
    }


class GoldDirectPolicyGateTests(unittest.TestCase):
    def test_multiset_distance_counts_replacements_not_positions(self):
        left = [1] * 30 + [2] * 30
        right = [2] * 30 + [1] * 29 + [3]
        self.assertEqual(1, deck_replacement_distance(left, right))
        self.assertEqual(59, multiset_overlap(left, right))

    def test_action_dependencies_include_actor_cards_and_effect_source(self):
        value = candidate(1197)["canonical"]
        value["selections"][0]["target_card_id"] = 169
        value["selections"][0]["effect_source_id"] = 1182
        self.assertEqual([169, 1182, 1197], action_self_card_dependencies(
            value, [169, 1182, 1197] + [8] * 57,
        ))

    def test_gate_rejects_far_deck_and_missing_gold_card(self):
        target = [8] * 60
        source = [8] * 47 + [1197] + [9] * 12
        rows = build_gate_rows([state("s", source, 1197)], target, "archaludon_metal", 4)
        row = rows[0]
        self.assertEqual(13, row["deck_replacements"])
        self.assertFalse(row["near_deck"])
        self.assertFalse(row["gold_action_available_in_target_deck"])
        self.assertFalse(row["direct_policy_eligible"])
        self.assertEqual(
            ["deck_replacements_exceed_limit", "gold_action_cards_absent_target_deck"],
            row["exclusion_reasons"],
        )

    def test_gate_accepts_near_same_archetype_with_available_action(self):
        target = [8] * 59 + [1197]
        source = [8] * 56 + [9] * 3 + [1197]
        row = build_gate_rows(
            [state("s", source, 1197)], target, "archaludon_metal", 4,
        )[0]
        self.assertEqual(3, row["deck_replacements"])
        self.assertTrue(row["direct_policy_eligible"])
        self.assertIn("direct_policy_prior", row["allowed_uses"])

    def test_duplicate_state_ids_are_allowed_when_decisions_differ(self):
        target = [8] * 59 + [1197]
        first = state("shared", target, 1197)
        second = state("shared", target, 1197)
        second["decision_id"] = "another-decision"
        rows = build_gate_rows(
            [first, second], target, "archaludon_metal", 4,
        )
        self.assertEqual(2, len(rows))
        self.assertEqual(1, len({row["state_id"] for row in rows}))
        self.assertEqual(2, len({row["decision_id"] for row in rows}))

    def test_duplicate_decision_ids_fail_closed(self):
        target = [8] * 59 + [1197]
        first = state("first", target, 1197)
        second = state("second", target, 1197)
        second["decision_id"] = first["decision_id"]
        with self.assertRaisesRegex(ValueError, "decision IDs"):
            build_gate_rows([first, second], target, "archaludon_metal", 4)

    def test_sensitivity_does_not_override_missing_action_card(self):
        target = [8] * 60
        source = [8] * 59 + [1197]
        rows = build_gate_rows([state("s", source, 1197)], target, "archaludon_metal", 4)
        summary = summarize_rows(rows, [0, 1, 4, 13])
        self.assertEqual({"0": 0, "1": 0, "4": 0, "13": 0}, summary[
            "threshold_sensitivity_direct_eligible"
        ])

    def test_run_and_verify_bind_rows_inputs_and_source_snapshot(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            base = Path(directory)
            corpus = base / "corpus"
            corpus.mkdir()
            source = [8] * 59 + [1197]
            corpus_state = state("s", source, 1197)
            (corpus / "states.jsonl").write_text(
                json.dumps(corpus_state, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="ascii",
            )
            (corpus / "manifest.json").write_text("{}\n", encoding="ascii")
            target_path = base / "target.csv"
            target_path.write_text("\n".join(["8"] * 60) + "\n", encoding="ascii")
            output = base / "gate"
            with patch("rl_ptcg.gold_direct_policy_gate.verify_gold_oracle_states"):
                result = run_gate(
                    corpus,
                    target_path,
                    output,
                    target_archetype="archaludon_metal",
                    max_replacements=4,
                    workspace_root=ROOT,
                )
                self.assertEqual(0, result["direct_policy_eligible"])
                self.assertTrue(result["rows_recomputed"])
                self.assertEqual([], result["current_implementation_drift"])
                verified = verify_gate_output(output, ROOT)
                self.assertEqual(result["manifest_sha256"], verified["manifest_sha256"])
                (output / "rows.jsonl").write_text("{}\n", encoding="ascii")
                with self.assertRaisesRegex(ValueError, "rows hash mismatch"):
                    verify_gate_output(output, ROOT)


if __name__ == "__main__":
    unittest.main()
