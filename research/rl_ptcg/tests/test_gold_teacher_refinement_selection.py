import unittest

from research.rl_ptcg.gold_teacher_refinement_selection import select_refinement_states


class GoldTeacherRefinementSelectionTests(unittest.TestCase):
    def unit(self, state, batch, oracle, candidate_advantage):
        baseline = "baseline"
        return {
            "state_id": state, "episode_id": "episode", "batch_id": batch,
            "baseline_action": baseline, "oracle_action": oracle,
            "actions": {
                baseline: {
                    "advantage_win_probability": 0.0,
                    "one_sided_lcb90_win_probability": 0.0,
                    "opponent_group_advantages_utility": {"head": 0.0},
                },
                "candidate": {
                    "advantage_win_probability": candidate_advantage,
                    "one_sided_lcb90_win_probability": candidate_advantage - 0.01,
                    "opponent_group_advantages_utility": {
                        "head": candidate_advantage * 2.0,
                    },
                },
            },
        }

    def test_selects_only_repeated_material_improvement(self):
        units = [
            self.unit("selected", 0, "candidate", 0.08),
            self.unit("selected", 1, "candidate", 0.06),
            self.unit("selected", 2, "baseline", 0.04),
            self.unit("selected", 3, "baseline", 0.04),
            self.unit("small", 0, "candidate", 0.02),
            self.unit("small", 1, "candidate", 0.02),
            self.unit("small", 2, "baseline", 0.02),
            self.unit("small", 3, "baseline", 0.02),
        ]
        result = select_refinement_states(
            units, minimum_top_count=2,
            minimum_mean_advantage_win_probability=0.05,
        )
        by_state = {item["state_id"]: item for item in result}
        self.assertTrue(by_state["selected"]["selected"])
        self.assertFalse(by_state["small"]["selected"])

    def test_rejects_inconsistent_candidate_sets(self):
        units = [self.unit("state", 0, "candidate", 0.1), self.unit("state", 1, "candidate", 0.1)]
        del units[1]["actions"]["candidate"]
        with self.assertRaisesRegex(ValueError, "candidate action set changed"):
            select_refinement_states(
                units, minimum_top_count=2,
                minimum_mean_advantage_win_probability=0.05,
            )

    def test_optional_minimum_batch_gate_is_strict_and_backward_compatible(self):
        units = [
            self.unit("positive", 0, "candidate", 0.20),
            self.unit("positive", 1, "candidate", 0.01),
            self.unit("zero", 0, "candidate", 0.21),
            self.unit("zero", 1, "candidate", 0.00),
        ]
        legacy = select_refinement_states(
            units, minimum_top_count=2,
            minimum_mean_advantage_win_probability=0.05,
        )
        strict = select_refinement_states(
            units, minimum_top_count=2,
            minimum_mean_advantage_win_probability=0.05,
            minimum_batch_advantage_win_probability_exclusive=0.0,
        )
        self.assertTrue(all(item["selected"] for item in legacy))
        by_state = {item["state_id"]: item for item in strict}
        self.assertTrue(by_state["positive"]["selected"])
        self.assertFalse(by_state["zero"]["selected"])


if __name__ == "__main__":
    unittest.main()
