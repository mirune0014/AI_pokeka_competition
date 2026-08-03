import unittest

from research.rl_ptcg.gold_upper_tier_screen import select_additional_rows


class GoldUpperTierScreenTests(unittest.TestCase):
    def test_selects_earliest_root_per_new_turn_and_deduplicates_base(self):
        rows = [
            {"episode_id": "e", "acting_seat": 0, "replay_step": 1, "turn": 1,
             "state_id": "base", "main_menu": True, "legal_option_count": 5},
            {"episode_id": "e", "acting_seat": 0, "replay_step": 3, "turn": 2,
             "state_id": "new-a", "main_menu": True, "legal_option_count": 4},
            {"episode_id": "e", "acting_seat": 0, "replay_step": 4, "turn": 2,
             "state_id": "new-b", "main_menu": True, "legal_option_count": 6},
            {"episode_id": "e", "acting_seat": 0, "replay_step": 5, "turn": 3,
             "state_id": "not-menu", "main_menu": False, "legal_option_count": 9},
            {"episode_id": "e", "acting_seat": 0, "replay_step": 6, "turn": 4,
             "state_id": "too-small", "main_menu": True, "legal_option_count": 3},
        ]
        pool, selected = select_additional_rows(
            rows, {("e", 0, 1)}, {"base"}, minimum_legal_options=4,
        )
        self.assertEqual(2, len(pool))
        self.assertEqual([3], [row["replay_step"] for row in selected])
        self.assertTrue(pool[0]["selected_additional"])
        self.assertFalse(pool[1]["selected_additional"])


if __name__ == "__main__":
    unittest.main()
