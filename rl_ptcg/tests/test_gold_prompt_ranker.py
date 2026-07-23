from __future__ import annotations

import copy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from rl_ptcg.gold_prompt_ranker import (RankerConfig, build_examples, evaluate_ranker, load_ranker,
    _load_allowed_records, load_phase1_examples, load_teacher_examples, predict_action_id,
    save_ranker, train_ranker)


def option(card, action_type="play"):
    return {"action_type": action_type, "selection_context": "choose", "source_card_id": card,
            "source_zone": "hand", "source_relation": "self", "target_card_id": None}


def record(decision_id="d1", style="aggressive"):
    chosen = option("a")
    return {"decision_id": decision_id, "own_archetype": "arch", "style_id": style,
            "safe_observation": {"turn": 1, "result": -1, "self": {"prizes": 6}, "opponents": [{"prizes": 6}]},
            "known_private_info": {"hand": [{"id": "a"}]}, "public_history": [{"event": "start"}],
            "legal_semantic_options": [chosen, option("b", "retreat")],
            "chosen_canonical_action": {"selection_context": "choose", "minimum_count": 1, "maximum_count": 1, "selections": [chosen]}}


class GoldPromptRankerTest(unittest.TestCase):
    def test_teacher_loader_collapses_matching_artifacts_and_rejects_conflicts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); corpus = root / "corpus"; corpus.mkdir()
            value = record(); value.pop("chosen_canonical_action")
            (corpus / "states.jsonl").write_text(json.dumps(value) + "\n", encoding="ascii")
            (corpus / "manifest.json").write_text("{}\n", encoding="ascii")
            (corpus / "selection_manifest.json").write_text("{}\n", encoding="ascii")
            split = root / "split.json"; split.write_text("{}\n", encoding="ascii")
            split_hash = sha256(split.read_bytes()).hexdigest()
            labels = [root / "label_a", root / "label_b"]
            for label in labels:
                label.mkdir()
                (label / "manifest.json").write_text(json.dumps({
                    "inputs": {"teacher_split": {
                        "sha256": split_hash, "manifest_sha256": "split-manifest",
                    }},
                }) + "\n", encoding="ascii")
            verification = {
                "labels": 1, "manifest_sha256": "label-manifest",
                "target_overrides": {"d1": value["legal_semantic_options"][1]},
            }
            split_verification = {
                "states": 1, "manifest_sha256": "split-manifest",
                "split_by_decision_id": {"d1": "train"},
            }
            with patch(
                "rl_ptcg.gold_prompt_ranker.verify_gold_upper_tier_states", return_value={},
            ), patch(
                "rl_ptcg.gold_prompt_ranker.verify_teacher_state_split",
                return_value=split_verification,
            ), patch(
                "rl_ptcg.gold_prompt_ranker.verify_teacher_labels",
                return_value=verification,
            ):
                examples, hashes = load_teacher_examples(
                    corpus, labels, split, workspace_root=root, archetype="arch",
                    allowed_splits=("train",),
                )
            self.assertEqual(1, len(examples))
            self.assertEqual("train", examples[0].split)
            self.assertIn("teacher_label_001_manifest_sha256", hashes)
            conflicting = dict(verification)
            conflicting["target_overrides"] = {"d1": value["legal_semantic_options"][0]}
            with patch(
                "rl_ptcg.gold_prompt_ranker.verify_gold_upper_tier_states", return_value={},
            ), patch(
                "rl_ptcg.gold_prompt_ranker.verify_teacher_state_split",
                return_value=split_verification,
            ), patch(
                "rl_ptcg.gold_prompt_ranker.verify_teacher_labels",
                side_effect=[verification, conflicting],
            ):
                with self.assertRaisesRegex(ValueError, "conflict"):
                    load_teacher_examples(
                        corpus, labels, split, workspace_root=root, archetype="arch",
                        allowed_splits=("train",),
                    )

    def test_blind_rejection(self):
        with self.assertRaises(ValueError):
            build_examples([record()], {"d1": "blind"}, archetype="arch", allowed_splits=("blind",))

    def test_forbidden_key_rejection(self):
        bad = record()
        bad["safe_observation"]["serial"] = 9
        with self.assertRaises(ValueError):
            build_examples([bad], {"d1": "train"}, archetype="arch")

    def test_one_step_filtering(self):
        multi = record("d2")
        multi["chosen_canonical_action"]["selections"].append(option("b", "retreat"))
        missing = record("d3")
        missing["chosen_canonical_action"]["selections"][0] = option("missing")
        examples = build_examples([record(), multi, missing], {"d1": "train", "d2": "train", "d3": "train"}, archetype="arch")
        self.assertEqual(["d1"], [item.decision_id for item in examples])

    def test_teacher_target_override_changes_only_target(self):
        value = record()
        observed = build_examples([value], {"d1": "train"}, archetype="arch")[0]
        teacher = value["legal_semantic_options"][1]
        overridden = build_examples(
            [value], {"d1": "train"}, archetype="arch",
            target_overrides={"d1": teacher},
        )[0]
        self.assertEqual(observed.action_ids, overridden.action_ids)
        self.assertTrue(torch.equal(observed.state, overridden.state))
        self.assertTrue(torch.equal(observed.actions, overridden.actions))
        self.assertNotEqual(observed.target_id, overridden.target_id)
        self.assertIn(overridden.target_id, overridden.action_ids)

    def test_upper_tier_metadata_archetype_is_supported_and_conflicts_fail(self):
        value = record()
        del value["own_archetype"]
        value["current_metadata"] = {"own_archetype": "arch"}
        examples = build_examples(
            [value], {"d1": "train"}, archetype="arch",
            target_overrides={"d1": value["legal_semantic_options"][1]},
        )
        self.assertEqual(1, len(examples))
        value["own_archetype"] = "other"
        with self.assertRaisesRegex(ValueError, "archetype binding drift"):
            build_examples([value], {"d1": "train"}, archetype="arch")

    def test_illegal_teacher_target_override_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "override.*legal"):
            build_examples(
                [record()], {"d1": "train"}, archetype="arch",
                target_overrides={"d1": option("not-visible")},
            )

    def test_in_progress_result_is_omitted_not_learned(self):
        left = record()
        right = copy.deepcopy(left)
        right["safe_observation"]["result"] = 1
        a = build_examples([left], {"d1": "train"}, archetype="arch")[0]
        b = build_examples([right], {"d1": "train"}, archetype="arch")[0]
        self.assertTrue(torch.equal(a.state, b.state))

    def test_duplicate_semantic_options_are_deduplicated(self):
        value = record()
        value["legal_semantic_options"].append(copy.deepcopy(value["legal_semantic_options"][0]))
        example = build_examples([value], {"d1": "train"}, archetype="arch")[0]
        self.assertEqual(2, len(example.action_ids))
        self.assertEqual(len(example.action_ids), len(set(example.action_ids)))

    def test_option_permutation_invariance_by_semantic_id(self):
        first = build_examples([record()], {"d1": "train"}, archetype="arch")[0]
        changed = record()
        changed["legal_semantic_options"].reverse()
        second = build_examples([changed], {"d1": "train"}, archetype="arch")[0]
        model, _ = train_ranker([first], config=RankerConfig(epochs=1, hidden_dim=8), seed=3)
        a = dict(zip(first.action_ids, model.score(first.state, first.actions, first.style_id).tolist()))
        b = dict(zip(second.action_ids, model.score(second.state, second.actions, second.style_id).tolist()))
        self.assertEqual(a, b)

    def test_semantic_tie_break_is_option_order_independent(self):
        scores = torch.tensor([0.0, 0.0])
        self.assertEqual("a", predict_action_id(scores, ("b", "a")))
        self.assertEqual("a", predict_action_id(scores.flip(0), ("a", "b")))

    def test_unknown_style_fallback(self):
        example = build_examples([record(style="")], {"d1": "train"}, archetype="arch")[0]
        model, _ = train_ranker([example], config=RankerConfig(epochs=1, hidden_dim=8), seed=1)
        self.assertEqual(model.style_index("unseen"), model.style_index("__unknown_style__"))

    def test_style_free_ranker_has_no_untrained_style_path(self):
        example = build_examples([record(style="known")], {"d1": "train"}, archetype="arch")[0]
        model, _ = train_ranker(
            [example],
            config=RankerConfig(epochs=1, hidden_dim=8, use_style_embedding=False),
            seed=2,
        )
        self.assertIsNone(model.style_embedding)
        self.assertTrue(torch.equal(
            model.score(example.state, example.actions, "known"),
            model.score(example.state, example.actions, "unseen"),
        ))

    def test_public_history_component_can_be_removed_for_runtime(self):
        left = record()
        right = copy.deepcopy(left)
        right["public_history"] = [{"event": "different"}, {"event": "later"}]
        with_history_left = build_examples([left], {"d1": "train"}, archetype="arch")[0]
        with_history_right = build_examples([right], {"d1": "train"}, archetype="arch")[0]
        self.assertFalse(torch.equal(with_history_left.state, with_history_right.state))
        without_left = build_examples(
            [left], {"d1": "train"}, archetype="arch", include_public_history=False,
        )[0]
        without_right = build_examples(
            [right], {"d1": "train"}, archetype="arch", include_public_history=False,
        )[0]
        self.assertTrue(torch.equal(without_left.state, without_right.state))

    def test_explicit_nonblind_development_refit(self):
        value = build_examples([record()], {"d1": "development"}, archetype="arch")[0]
        model, losses = train_ranker(
            [value],
            config=RankerConfig(epochs=1, hidden_dim=8),
            seed=2,
            fit_splits=("development",),
        )
        self.assertTrue(losses)
        self.assertIsNotNone(model)
        with self.assertRaisesRegex(ValueError, "non-blind"):
            train_ranker([value], fit_splits=("blind",))

    def test_deterministic_tiny_training(self):
        examples = build_examples([record("d1"), record("d2")], {"d1": "train", "d2": "train"}, archetype="arch")
        config = RankerConfig(epochs=3, batch_size=1, hidden_dim=8)
        left, left_losses = train_ranker(examples, config=config, seed=8)
        right, right_losses = train_ranker(examples, config=config, seed=8)
        self.assertEqual(left_losses, right_losses)
        for key in left.state_dict(): self.assertTrue(torch.equal(left.state_dict()[key], right.state_dict()[key]))
        self.assertIn("overall:overall", evaluate_ranker(left, examples))

    def test_manifest_checkpoint_roundtrip(self):
        examples = build_examples([record()], {"d1": "train"}, archetype="arch")
        config = RankerConfig(epochs=1, hidden_dim=8)
        model, _ = train_ranker(examples, config=config, seed=4)
        with tempfile.TemporaryDirectory() as directory:
            checkpoint, manifest = save_ranker(directory, model, config=config, seed=4, counts={"train": 1, "development": 0, "policy_family_holdout": 0}, source_hashes={"decision_records_sha256": "a" * 64, "split_manifest_sha256": "b" * 64})
            raw = json.loads(manifest.read_text(encoding="ascii"))
            self.assertNotIn("blind", json.dumps(raw))
            loaded = load_ranker(checkpoint, manifest)
            self.assertTrue(torch.equal(model.score(examples[0].state, examples[0].actions, examples[0].style_id), loaded.score(examples[0].state, examples[0].actions, examples[0].style_id)))
            raw["seed"] = 99
            manifest.write_text(json.dumps(raw, sort_keys=True, indent=2) + "\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "does not match"):
                load_ranker(checkpoint, manifest)

    def test_non_allowlisted_payload_is_not_json_parsed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            allowed = record("allowed")
            path.write_text(
                '{"decision_id":"blind",this-is-not-json}\n'
                + json.dumps(allowed, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="ascii",
            )
            loaded = _load_allowed_records(path, {"allowed": "train"})
            self.assertEqual(["allowed"], [item["decision_id"] for item in loaded])


if __name__ == "__main__":
    unittest.main()
