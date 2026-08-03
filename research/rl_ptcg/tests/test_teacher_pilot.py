import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from research.rl_ptcg import teacher_pilot as pilot


def row(name, stratum="neutral"):
    return {"public_state_hash": name, "replay_path": "C:/" + name, "step": 0, "sampling_stratum": stratum}


class TeacherPilotTests(unittest.TestCase):
    def test_selection_is_deterministic_and_deduplicated(self):
        rows = [row("w" + str(i), "weak") for i in range(3)] + [row("s" + str(i), "strong") for i in range(2)] + [row("n" + str(i)) for i in range(2)]
        rows.append(dict(rows[0]))
        one = pilot.select_states(rows, 4, 7)
        two = pilot.select_states(list(reversed(rows)), 4, 7)
        self.assertEqual([item["state_id"] for item in one], [item["state_id"] for item in two])
        self.assertEqual(4, len(one))

    def test_quota_shortage_fills_remaining_states(self):
        selected = pilot.select_states([row("w", "weak"), row("n1"), row("n2"), row("n3")], 4, 3)
        self.assertEqual(4, len(selected))
        self.assertEqual(1, sum(item["sampling_stratum"] == "weak" for item in selected))

    def test_insufficient_states_raises(self):
        with self.assertRaisesRegex(ValueError, "insufficient"):
            pilot.select_states([row("only")], 2, 0)

    def test_seed_and_frozen_state_reuse_across_batches(self):
        state = {"state_id": "s", "episode_id": "e", "seat": 0, "observation": {"x": 1}, "target_deck": [1] * 60, "opponent_deck": [2] * 60, "baseline_scores": [0, 1], "baseline_action": [0], "matchup": "m", "opponent_archetype": "archetype", "sampling_stratum": "neutral"}
        args = type("Args", (), {"pilot_seed": 9, "baseline": Path("."), "opponent_catalog": None, "catalog_policy_count": 1, "deck_belief": "exact", "continuation_agent": [], "particles_per_scenario": 1, "max_rollout_steps": 3, "max_complete_actions": 4})()
        decision = type("Decision", (), {
            "scenario_values": [{"particle_index": 0, "opponent_policy_index": 0, "hypothesis_signature": "h", "hidden_world_id": "w", "action": [0], "terminal_utility": 1}],
            "reason": "accepted improvement", "determinizations": 1, "errors": 0,
        })()
        with patch.object(pilot, "load_agent", return_value=object()), patch.object(pilot, "AgentChooser", side_effect=lambda value: value), patch.object(pilot, "choose_with_rollout", return_value=decision) as rollout:
            with patch.object(pilot, "policy_paths_for_state", return_value=[Path("op")]):
                first, first_status = pilot.run_state(state, 0, args, set(), {"m": [Path("op")]})
                second, second_status = pilot.run_state(state, 1, args, set(), {"m": [Path("op")]})
        self.assertEqual(state["observation"], {"x": 1})
        self.assertNotEqual(first[0]["rollout_seed"], second[0]["rollout_seed"])
        self.assertEqual(pilot.stable_seed(9, "s", 0), first[0]["rollout_seed"])
        self.assertEqual("complete", first_status["status"])
        self.assertEqual("complete", second_status["status"])
        self.assertEqual(2, rollout.call_count)

    def test_output_schema_collect_only(self):
        states = [{"state_id": "s", "episode_id": "e", "replay_path": "replay.json", "step": 0, "seat": 0, "matchup": "m", "opponent_archetype": "archetype", "context": 0, "baseline_action": [0], "baseline_scores": [0, 1], "candidate_actions": [[0], [1]], "complete_action_count": 2, "public_state_hash": "h", "public_state": {}, "observation": {}, "target_deck": [1] * 60, "opponent_deck": [2] * 60, "sampling_stratum": "neutral"}]
        with TemporaryDirectory() as root:
            replay = Path(root) / "replay.json"; replay.write_text("{}", encoding="ascii")
            states[0]["replay_path"] = str(replay)
            with patch.object(pilot, "collect_teacher_states", return_value=states):
                pilot.main([root, "--engine-dir", root, "--baseline", root, "--output-dir", root, "--collect-only"])
            self.assertTrue((Path(root) / "states.jsonl").is_file())
            manifest = json.loads((Path(root) / "manifest.json").read_text(encoding="ascii"))
            self.assertEqual(1, manifest["schema_version"])
            stored = json.loads((Path(root) / "states.jsonl").read_text(encoding="ascii"))
            self.assertIn("candidate_actions", stored)
            self.assertIn("complete_action_count", stored)
            self.assertFalse((Path(root) / "particle_outcomes.jsonl").exists())

    def test_public_catalog_population_uses_only_visible_cards(self):
        state = {
            "seat": 0, "public_state_hash": "frozen",
            "observation": {"current": {"players": [
                {}, {"active": [{"id": 10}], "bench": [], "discard": [], "prize": []},
            ]}},
        }
        with TemporaryDirectory() as root:
            for name, deck in (
                ("compatible_a", [10] + [1] * 59),
                ("compatible_b", [10] + [2] * 59),
                ("incompatible", [3] * 60),
            ):
                directory = Path(root) / name
                directory.mkdir()
                (directory / "main.py").write_text("", encoding="ascii")
                (directory / "deck.csv").write_text("\n".join(map(str, deck)), encoding="ascii")
            selected = pilot.public_catalog_policy_paths(state, Path(root), 2)
            self.assertEqual(2, len(selected))
            self.assertTrue(all(10 in row["deck"] for row in selected))

    def test_public_catalog_repairs_unknown_variant_without_exact_deck(self):
        state = {
            "seat": 0, "public_state_hash": "unknown-variant",
            "observation": {"current": {"players": [
                {}, {"active": [{"id": 99}], "bench": [], "discard": [], "prize": []},
            ]}},
        }
        with TemporaryDirectory() as root:
            for name, card_id in (("one", 1), ("two", 2)):
                directory = Path(root) / name
                directory.mkdir()
                (directory / "main.py").write_text("", encoding="ascii")
                (directory / "deck.csv").write_text("\n".join(map(str, [card_id] * 60)), encoding="ascii")
            selected = pilot.public_catalog_policy_paths(state, Path(root), 2)
            self.assertEqual(2, len(selected))
            self.assertTrue(all(row["synthetic_unknown_variant"] for row in selected))
            self.assertTrue(all(len(row["deck"]) == 60 and 99 in row["deck"] for row in selected))


if __name__ == "__main__":
    unittest.main()
