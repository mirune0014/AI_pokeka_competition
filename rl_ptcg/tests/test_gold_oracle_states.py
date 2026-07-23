from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from rl_ptcg.gold_oracle_states import (
    SCHEMA_VERSION,
    _resolve_bound_path,
    _selection_inputs,
    build_beliefs,
    candidate_sets,
    canonical_sha256,
    compatible_decks,
    deck_signature,
    file_sha256,
    make_selection_manifest,
    portable_inventory_source,
    rank_target_actions,
    select_audited_records,
    select_known_entries,
    validate_no_leakage,
    verified_actor_deck,
    verify_inventory_source_binding,
    verify_gold_oracle_states,
    write_once,
)
from tools.build_gold_oracle_states import parse_extra_decks


def catalog_entry(archetype, deck, source="inventory-row"):
    values = sorted(deck)
    return {
        "archetype": archetype,
        "decklist": values,
        "signature": deck_signature(values),
        "deck_sha256": canonical_sha256(values),
        "sources": [{
            "source_kind": "inventory",
            "source_path": "inventory.csv",
            "source_row_id": source,
            "source_sha256": "a" * 64,
        }],
    }


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")


class GoldOracleStateTests(unittest.TestCase):
    def test_bound_path_cannot_escape_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory).resolve()
            self.assertEqual(workspace / "inside.json", _resolve_bound_path("inside.json", workspace))
            with self.assertRaisesRegex(ValueError, "escapes workspace"):
                _resolve_bound_path("../outside.json", workspace)

    def test_inventory_source_binding_accepts_cross_platform_legacy_path(self):
        bound = "analysis_outputs/inventory/all_seats.csv"
        stored = {
            "source_path": "C:\\repo\\analysis_outputs\\inventory\\all_seats.csv",
            "source_row_id": "episode_p0",
            "source_sha256": "a" * 64,
        }
        current = {
            "source_path": "/mnt/c/repo/analysis_outputs/inventory/all_seats.csv",
            "source_row_id": "episode_p0",
            "source_sha256": "a" * 64,
        }
        verify_inventory_source_binding(stored, current, bound)
        broken = dict(stored, source_row_id="other")
        with self.assertRaisesRegex(ValueError, "row or deck hash"):
            verify_inventory_source_binding(broken, current, bound)
        broken = dict(stored, source_path="C:\\repo\\not_" + bound.replace("/", "\\"))
        with self.assertRaisesRegex(ValueError, "bound input"):
            verify_inventory_source_binding(broken, current, bound)

    def test_portable_inventory_source_uses_workspace_relative_path(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory).resolve()
            inventory = workspace / "inputs" / "inventory.csv"
            inventory.parent.mkdir()
            inventory.write_text("x\n", encoding="ascii")
            source = {
                "source_path": str(inventory),
                "source_row_id": "row",
                "source_sha256": "b" * 64,
            }
            portable = portable_inventory_source(source, inventory, workspace)
            self.assertEqual("inputs/inventory.csv", portable["source_path"])
            self.assertEqual("row", portable["source_row_id"])

    def test_blind_rejection_contract(self):
        record = SimpleNamespace(decision_id="x", own_archetype="archaludon_metal")
        audit = [{
            "decision_id": "x", "scope": "exact", "rule_rank_available": True,
        }]
        with self.assertRaises(ValueError):
            select_audited_records([record], {"x": "blind"}, audit, ["x"])

    def test_extra_decks_preserve_same_archetype_multiplicity(self):
        parsed = parse_extra_decks([
            "alakazam=a.csv", "alakazam=b.csv", "okidogi=c.csv",
            "alakazam=d.csv", "okidogi=e.csv",
        ])
        self.assertEqual([Path("a.csv"), Path("b.csv"), Path("d.csv")], parsed["alakazam"])
        self.assertEqual([Path("c.csv"), Path("e.csv")], parsed["okidogi"])

    def test_archetype_isolation_rejects_foreign_donor(self):
        own = catalog_entry("alakazam", [1] * 60, "a")
        foreign = catalog_entry("okidogi", [1] * 59 + [2], "b")
        self.assertEqual([own["signature"]], [
            item["signature"]
            for item in compatible_decks([own, foreign], "alakazam", Counter())
        ])
        belief = build_beliefs(
            [own, foreign], "alakazam", Counter(), max_known=1, unknown_mass=0.15,
        )
        self.assertEqual("no_unselected_donor", belief["synthetic_status"])
        self.assertEqual(0.0, belief["unknown_mass"])

    def test_seeded_known_selection_is_order_independent_and_diverse(self):
        entries = [
            catalog_entry("a", [number] + [1] * 59, str(number))
            for number in (2, 3, 4)
        ]
        entries[1]["sources"][0]["source_kind"] = "extra_public_deck"
        first = select_known_entries(entries, 2, "seed")
        second = select_known_entries(list(reversed(entries)), 2, "seed")
        self.assertEqual(
            [item["signature"] for item in first],
            [item["signature"] for item in second],
        )
        self.assertEqual(2, len({item["sources"][0]["source_kind"] for item in first}))

    def test_late_incompatible_same_archetype_donor_can_make_synthetic(self):
        base = catalog_entry("alakazam", [99] + [1] * 59, "base")
        donor = catalog_entry("alakazam", [1] * 56 + [2] * 4, "late-donor")
        with patch("rl_ptcg.gold_oracle_states.sample_search_guess"):
            belief = build_beliefs(
                [base, donor],
                "alakazam",
                Counter({99: 1}),
                max_known=1,
                unknown_mass=0.15,
                observation={"current": {}},
                own_deck=[3] * 60,
                preflight_seed="late",
            )
        synthetic = [
            item for item in belief["hypotheses"]
            if item["kind"] == "synthetic_unknown"
        ]
        self.assertEqual(1, len(synthetic))
        self.assertEqual(60, len(synthetic[0]["decklist"]))
        self.assertGreaterEqual(Counter(synthetic[0]["decklist"])[99], 1)
        self.assertNotIn(
            synthetic[0]["signature"], {base["signature"], donor["signature"]},
        )
        self.assertEqual(0.15, belief["unknown_mass"])

    def test_preflight_rejects_stadium_only_incompatible_hypothesis(self):
        bad = catalog_entry("a", [1] * 60, "bad")
        good = catalog_entry("a", [1] * 59 + [99], "good")
        observation = {
            "current": {
                "yourIndex": 0,
                "players": [
                    {"deckCount": 0, "hand": [], "active": [], "bench": [], "discard": [], "prize": []},
                    {"deckCount": 59, "handCount": 0, "active": [], "bench": [], "discard": [], "prize": []},
                ],
                "stadium": [{"id": 99}],
            },
            "logs": [{"cardId": 99, "playerIndex": 1}],
        }
        belief = build_beliefs(
            [bad, good],
            "a",
            Counter(),
            max_known=1,
            unknown_mass=0.15,
            observation=observation,
            own_deck=[2] * 60,
        )
        self.assertEqual(1, belief["counts"]["preflight_rejected_count"])
        self.assertEqual(1, belief["counts"]["preflight_accepted_count"])
        self.assertIn("visible card count exceeds", belief["preflight_rejections"][0]["reason"])

    def test_baseline_is_in_top3_and_diverse_candidate_is_tagged(self):
        ranked = {
            "scope": "exact",
            "ranked": [
                {"semantic_id": "one", "canonical": {"selections": [{"action_type": 1}]}, "score": 4},
                {"semantic_id": "two", "canonical": {"selections": [{"action_type": 1}]}, "score": 3},
                {"semantic_id": "gold", "canonical": {"selections": [{"action_type": 2}]}, "score": 2},
                {"semantic_id": "baseline", "canonical": {"selections": [{"action_type": 3}]}, "score": 1},
            ],
        }
        with patch("rl_ptcg.gold_oracle_states.canonicalize_prompt_action") as canonicalize:
            canonicalize.side_effect = [
                SimpleNamespace(stable_id="baseline"),
                SimpleNamespace(stable_id="gold"),
            ]
            candidates, sets = candidate_sets(
                ranked, [0], [1], {}, top_k=2, max_diverse=4,
            )
        self.assertIn("baseline", sets["rule_top3"])
        self.assertLessEqual(len(sets["rule_topK"]), 4)
        self.assertLessEqual(len(sets["rule_diverse"]), 4)
        by_id = {item["semantic_id"]: item for item in candidates}
        self.assertIn("action_type_diverse", by_id["gold"]["source_tags"])

    def test_rank_target_uses_exact_4096_cap(self):
        with patch("rl_ptcg.gold_oracle_states.rank_complete_actions", return_value={}) as rank:
            rank_target_actions({}, [], [0], [1])
        self.assertEqual(4096, rank.call_args.kwargs["max_complete_actions"])

    def test_actor_replay_deck_must_exactly_match_inventory(self):
        replay = {"steps": [[{"action": [1] * 60}, {"action": [9] * 60}]]}
        with tempfile.TemporaryDirectory() as directory:
            inventory = Path(directory) / "inventory.csv"
            inventory.write_text(
                "episode_id,player_index,deck,deck_id,deck_sha256\n"
                "e,0,\"" + " ".join(["2"] * 60) + "\",e_p0," + "a" * 64 + "\n",
                encoding="ascii",
            )
            with self.assertRaisesRegex(ValueError, "exactly match"):
                verified_actor_deck(replay, inventory, "e", 0)

    def test_selection_hash_binds_all_extra_decks_and_required_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "dataset"; audit = root / "audit"; baseline = root / "baseline"; engine = root / "engine"
            for path in (dataset, audit, baseline, engine / "cg", root / "tools"):
                path.mkdir(parents=True, exist_ok=True)
            paths = [root / ("extra%d.csv" % number) for number in range(5)]
            required = [
                dataset / "dataset_manifest.json", dataset / "split_manifest.json", dataset / "decision_records.jsonl",
                audit / "checksum_manifest.json", audit / "sample_manifest.json", baseline / "main.py", baseline / "deck.csv",
                engine / "cg" / "api.py", engine / "cg" / "cg.dll", root / "inventory.csv",
            ] + paths
            for path in required:
                path.write_text("x", encoding="ascii")
            with patch("rl_ptcg.gold_oracle_states.__file__", str(root / "collector.py")):
                (root / "collector.py").write_text("collector", encoding="ascii")
                (root / "tools" / "build_gold_oracle_states.py").write_text("cli", encoding="ascii")
                extras = {"a": paths[:3], "b": paths[3:]}
                bindings = _selection_inputs(dataset, audit, baseline, engine, root / "inventory.csv", extras, root)
            manifest = make_selection_manifest(["d"], bindings, {"extra_decks": {"a": [str(path) for path in paths[:3]]}})
            extra_keys = [key for key in manifest["inputs"] if key.startswith("extra_deck:")]
            self.assertEqual(5, len(extra_keys))
            for key in extra_keys:
                self.assertEqual(file_sha256(Path(manifest["inputs"][key]["path"])), manifest["inputs"][key]["sha256"])

    def test_leakage_rejects_banned_key_segments(self):
        for key in (
            "terminal_result", "future_log", "search_begin_input", "raw_action",
            "option_index", "cardSerial", "choice_ordinal", "match_outcome",
            "gold_score",
        ):
            with self.assertRaises(ValueError):
                validate_no_leakage({key: 1})
        validate_no_leakage({"source_card_id": 1, "submission_id": "x"})

    def test_write_once_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.json"
            write_once(path, {"x": 1})
            with self.assertRaises(FileExistsError):
                write_once(path, {"x": 2})


class GoldOracleVerifierTests(unittest.TestCase):
    def make_output(self, root):
        root = Path(root)
        output = root / "output"; output.mkdir()
        inputs = {}
        for name in (
            "dataset_manifest", "split_manifest", "decision_records",
            "audit_checksum_manifest", "audit_sample_manifest", "inventory",
            "baseline_main", "baseline_deck", "engine_api", "engine_dll",
            "collector_module", "collector_cli",
        ):
            path = root / (name + ".bin")
            path.write_bytes((name + "\n").encode("ascii"))
            inputs[name] = path
        replay = root / "replay.json"
        replay.write_text("{}\n", encoding="ascii")
        selection = make_selection_manifest(
            ["decision"], inputs,
            {"rule_top_k": 1, "max_diverse_actions": 2, "extra_decks": {}},
        )
        (output / "selection_manifest.json").write_bytes(json_bytes(selection))
        known_deck = [1] * 60
        own_deck = [2] * 60
        base_canonical = {"selections": []}
        gold_canonical = {"selections": [{"action_type": 1}]}
        base_id = __import__("hashlib").blake2b(
            json.dumps(base_canonical, sort_keys=True, separators=(",", ":")).encode("ascii"),
            digest_size=32,
        ).hexdigest()
        gold_id = __import__("hashlib").blake2b(
            json.dumps(gold_canonical, sort_keys=True, separators=(",", ":")).encode("ascii"),
            digest_size=32,
        ).hexdigest()
        state = {
            "schema_version": SCHEMA_VERSION,
            "decision_id": "decision",
            "state_id": "state",
            "episode_id": "episode",
            "acting_seat": 0,
            "source_replay_path": str(replay),
            "replay_sha256": file_sha256(replay),
            "split": "train",
            "style_id": "style",
            "submission_id": "submission",
            "replay_step": 7,
            "safe_observation": {},
            "known_private_info": {},
            "public_history": [],
            "legal_semantic_options": [],
            "current_metadata": {"turn": 1, "own_archetype": "archaludon_metal", "opponent_archetype": "alakazam"},
            "candidates": [
                {"semantic_id": base_id, "canonical": base_canonical, "additive_rule_score": 1.0, "source_tags": ["baseline"]},
                {"semantic_id": gold_id, "canonical": gold_canonical, "additive_rule_score": 0.0, "source_tags": ["gold"]},
            ],
            "candidate_sets": {
                "baseline": [base_id], "rule_top3": [base_id, gold_id],
                "rule_topK": [base_id, gold_id], "rule_diverse": [base_id, gold_id],
                "rule_plus_gold": [base_id, gold_id],
            },
            "gold_incremental": False,
            "own_deck": {"decklist": own_deck, "sha256": canonical_sha256(own_deck), "inventory_source": {}},
            "belief": {
                "archetype": "alakazam",
                "visible_requirements": {"1": 1},
                "hypotheses": [{
                    "kind": "known", "archetype": "alakazam", "decklist": known_deck,
                    "signature": deck_signature(known_deck), "deck_sha256": canonical_sha256(known_deck),
                    "sources": [], "posterior_mass": 1.0,
                }],
                "catalog_results": [], "preflight_rejections": [],
                "synthetic_status": "no_unselected_donor", "synthetic_attempts": [],
                "unknown_mass": 0.0, "top1_mass": 1.0, "entropy": 0.0,
                "counts": {},
            },
        }
        (output / "states.jsonl").write_bytes(json_bytes(state))
        source_replays = [{
            "source_replay_path": str(replay), "replay_sha256": file_sha256(replay),
        }]
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "selection_manifest_sha256": file_sha256(output / "selection_manifest.json"),
            "states_sha256": file_sha256(output / "states.jsonl"),
            "source_replays": source_replays,
            "source_replays_sha256": canonical_sha256(source_replays),
            "engine_files_sha256": {
                "cg/api.py": file_sha256(inputs["engine_api"]),
                "cg/cg.dll": file_sha256(inputs["engine_dll"]),
            },
            "python": "test", "platform": "test", "command": ["test"],
            "counts": {
                "states": 1,
                "episodes": 1,
                "candidate_coverage": {
                    "baseline": 1, "rule_top3": 1, "rule_topK": 1,
                    "rule_diverse": 1, "rule_plus_gold": 1,
                },
                "belief": {},
                "per_episode_candidate_coverage": {
                    "episode": {
                        "baseline": 1, "rule_top3": 1, "rule_topK": 1,
                        "rule_diverse": 1, "rule_plus_gold": 1,
                    },
                },
                "per_matchup_candidate_coverage": {
                    "archaludon_metal__vs__alakazam": {
                        "baseline": 1, "rule_top3": 1, "rule_topK": 1,
                        "rule_diverse": 1, "rule_plus_gold": 1,
                    },
                },
            },
        }
        manifest["manifest_sha256"] = canonical_sha256(manifest)
        (output / "manifest.json").write_bytes(json_bytes(manifest))
        return output, replay

    def reseal_states(self, output, state):
        (output / "states.jsonl").write_bytes(json_bytes(state))
        manifest = json.loads((output / "manifest.json").read_text(encoding="ascii"))
        manifest["states_sha256"] = file_sha256(output / "states.jsonl")
        manifest.pop("manifest_sha256")
        manifest["manifest_sha256"] = canonical_sha256(manifest)
        (output / "manifest.json").write_bytes(json_bytes(manifest))

    def test_valid_output_verifies(self):
        with tempfile.TemporaryDirectory() as directory:
            output, _replay = self.make_output(directory)
            self.assertEqual(1, verify_gold_oracle_states(output, Path(directory))["states"])

    def test_rows_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output, _replay = self.make_output(directory)
            with (output / "states.jsonl").open("ab") as handle:
                handle.write(b" \n")
            with self.assertRaisesRegex(ValueError, "states file hash"):
                verify_gold_oracle_states(output, Path(directory))

    def test_candidate_dangling_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output, _replay = self.make_output(directory)
            state = json.loads((output / "states.jsonl").read_text(encoding="ascii"))
            state["candidate_sets"]["rule_top3"].append("missing")
            self.reseal_states(output, state)
            with self.assertRaisesRegex(ValueError, "dangling"):
                verify_gold_oracle_states(output, Path(directory))

    def test_posterior_mass_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output, _replay = self.make_output(directory)
            state = json.loads((output / "states.jsonl").read_text(encoding="ascii"))
            state["belief"]["hypotheses"][0]["posterior_mass"] = 0.5
            self.reseal_states(output, state)
            with self.assertRaisesRegex(ValueError, "sum to one"):
                verify_gold_oracle_states(output, Path(directory))

    def test_source_replay_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output, replay = self.make_output(directory)
            replay.write_text("{\"tampered\":true}\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "source replay current hash"):
                verify_gold_oracle_states(output, Path(directory))

    def test_bound_input_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            output, _replay = self.make_output(directory)
            selection = json.loads((output / "selection_manifest.json").read_text(encoding="ascii"))
            bound = Path(selection["inputs"]["collector_module"]["path"])
            bound.write_text("changed", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "bound input hash"):
                verify_gold_oracle_states(output, Path(directory))


if __name__ == "__main__":
    unittest.main()
