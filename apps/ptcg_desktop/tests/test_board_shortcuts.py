from __future__ import annotations

import unittest

from ptcg_desktop.human_view import HumanViewProjector


class BoardShortcutTests(unittest.TestCase):
    def test_card_token_is_stable_across_safe_view_zones(self) -> None:
        projector = HumanViewProjector(
            match_id="match-1",
            human_seat=0,
            secret=b"0123456789abcdef",
            card_names={25: "テストカード"},
        )
        card = {"id": 25, "serial": 901, "playerIndex": 0}

        option_token = projector.state_token_for_card(card)
        hand_token = projector.state_token_for_card(card, zone="hand")
        bench_token = projector.state_token_for_card(card, zone="bench.2")

        self.assertEqual(option_token, hand_token)
        self.assertEqual(option_token, bench_token)


if __name__ == "__main__":
    unittest.main()
