from __future__ import annotations

import json
import unittest

from ptcg_desktop.human_view import HumanViewProjector, ProjectionError, assert_canaries_absent, assert_no_forbidden_keys, sanitize_public_logs
from ptcg_desktop.models import MatchPhase
from ptcg_desktop.protocol import encode_json, make_envelope
from ptcg_desktop.replay import ReplayBuilder

from helpers import full_frame, normal_observation


class HumanViewTests(unittest.TestCase):
    def projector(self, seat: int) -> HumanViewProjector:
        return HumanViewProjector("match-1", seat, b"x" * 32, {401: "Own One", 402: "Own Two"})

    def test_fixed_human_hand_during_agent_decision(self) -> None:
        full = full_frame(acting=1)
        normal = normal_observation(acting=1)
        view = self.projector(0).project(full, normal, revision=3, phase=MatchPhase.AGENT_THINKING)
        self.assertEqual([card["card_id"] for card in view["human"]["hand"]], [401, 402])
        self.assertNotIn("hand", view["opponent"])

    def test_secret_canaries_do_not_leak(self) -> None:
        full = full_frame(acting=0)
        view = self.projector(0).project(full, normal_observation(acting=0), revision=1, phase=MatchPhase.WAITING_FOR_HUMAN)
        assert_no_forbidden_keys(view)
        assert_canaries_absent(view, [990001, 990002, 991001, 991002, 992001])

    def test_ipc_frame_has_no_live_secret_canaries(self) -> None:
        full = full_frame(acting=1)
        view = self.projector(0).project(full, normal_observation(acting=1), revision=4, phase=MatchPhase.AGENT_THINKING)
        frame = encode_json(make_envelope("state.update", "match-1", {"state": view, "public_log": []}))
        for canary in (990001, 990002, 991001, 991002, 992001):
            self.assertNotIn(str(canary).encode("ascii"), frame)

    def test_full_replay_projection_retains_post_match_secret_canaries(self) -> None:
        builder = ReplayBuilder("match-1")
        builder.ingest_visualizer([full_frame(acting=1)], revision=0, captured_after="battle_start")
        encoded = json.dumps(builder.frames, ensure_ascii=False)
        for canary in (990001, 990002, 991001, 991002, 992001):
            self.assertIn(str(canary), encoded)

    def test_deck_and_prize_contents_are_absent(self) -> None:
        view = self.projector(0).project(full_frame(), normal_observation(), revision=1, phase=MatchPhase.WAITING_FOR_HUMAN)
        encoded = json.dumps(view)
        self.assertNotIn('"deck"', encoded)
        self.assertNotIn('"serial"', encoded)
        self.assertEqual(view["human"]["prize_count"], 1)

    def test_opponent_setup_identity_is_masked(self) -> None:
        full = full_frame(turn=0)
        view = self.projector(0).project(full, normal_observation(), revision=1, phase=MatchPhase.WAITING_FOR_HUMAN)
        opponent = view["opponent"]
        for card in opponent["active"] + opponent["bench"]:
            self.assertIsNone(card)
        self.assertNotIn("990001", json.dumps(view))

    def test_human_hand_owner_mismatch_is_rejected(self) -> None:
        full = full_frame()
        full["current"]["players"][0]["hand"][0]["playerIndex"] = 1
        with self.assertRaises(ProjectionError):
            self.projector(0).project(full, normal_observation(), revision=1, phase=MatchPhase.WAITING_FOR_HUMAN)

    def test_private_opponent_draw_is_sanitized(self) -> None:
        logs = sanitize_public_logs([{"type": "Draw", "playerIndex": 1, "cardId": 990001, "serial": 33}], human_seat=0)
        self.assertEqual(logs, [{"type": "Draw", "player_index": 1, "count": 1}])

    def test_move_card_identity_is_always_stripped(self) -> None:
        logs = sanitize_public_logs([{"type": "MoveCard", "playerIndex": 1, "cardId": 990001, "serial": 33, "fromArea": "Deck", "toArea": "Hand"}], human_seat=0)
        self.assertNotIn("card_id", logs[0])


if __name__ == "__main__":
    unittest.main()
