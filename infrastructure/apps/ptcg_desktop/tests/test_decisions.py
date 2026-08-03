from __future__ import annotations

import unittest

from ptcg_desktop.decisions import (
    InvalidSelectionError,
    StaleDecisionError,
    UnsafeOptionError,
    build_decision_request,
    validate_agent_action,
)

from helpers import normal_observation


class DecisionTests(unittest.TestCase):
    def test_yes_no_request_contains_only_opaque_options(self) -> None:
        state = build_decision_request(normal_observation(), 7)
        request = state.request
        self.assertEqual(request["min_count"], 1)
        self.assertEqual([option["label"] for option in request["options"]], ["はい", "いいえ"])
        self.assertNotIn("index", request["options"][0])

    def test_submission_preserves_order(self) -> None:
        obs = normal_observation()
        obs["select"].update({"type": 1, "minCount": 0, "maxCount": 2})
        obs["select"]["option"] = [
            {"type": 3, "area": 2, "index": 0, "playerIndex": 0},
            {"type": 3, "area": 2, "index": 1, "playerIndex": 0},
        ]
        state = build_decision_request(obs, 8)
        tokens = [state.request["options"][1]["token"], state.request["options"][0]["token"]]
        self.assertEqual(state.submit(state.request["request_id"], 8, tokens), [1, 0])

    def test_zero_selection(self) -> None:
        obs = normal_observation()
        obs["select"].update({"type": 1, "minCount": 0, "maxCount": 1})
        obs["select"]["option"] = [{"type": 3, "area": 2, "index": 0, "playerIndex": 0}]
        state = build_decision_request(obs, 2)
        self.assertEqual(state.submit(state.request["request_id"], 2, []), [])

    def test_duplicate_token_is_rejected(self) -> None:
        state = build_decision_request(normal_observation(), 1)
        token = state.request["options"][0]["token"]
        with self.assertRaises(InvalidSelectionError):
            state.submit(state.request["request_id"], 1, [token, token])

    def test_stale_revision_is_rejected(self) -> None:
        state = build_decision_request(normal_observation(), 4)
        token = state.request["options"][0]["token"]
        with self.assertRaises(StaleDecisionError):
            state.submit(state.request["request_id"], 3, [token])

    def test_second_submission_is_rejected(self) -> None:
        state = build_decision_request(normal_observation(), 4)
        token = state.request["options"][0]["token"]
        state.submit(state.request["request_id"], 4, [token])
        with self.assertRaises(StaleDecisionError):
            state.submit(state.request["request_id"], 4, [token])

    def test_unknown_select_type_fails_closed(self) -> None:
        obs = normal_observation()
        obs["select"]["type"] = 999
        with self.assertRaises(UnsafeOptionError):
            build_decision_request(obs, 1)

    def test_incompatible_option_type_fails_closed(self) -> None:
        obs = normal_observation()
        obs["select"]["option"] = [{"type": 14}]
        with self.assertRaises(UnsafeOptionError):
            build_decision_request(obs, 1)

    def test_agent_bool_index_is_rejected(self) -> None:
        with self.assertRaises(InvalidSelectionError):
            validate_agent_action(normal_observation(), [True])

    def test_valid_agent_action(self) -> None:
        self.assertEqual(validate_agent_action(normal_observation(), [0]), [0])


if __name__ == "__main__":
    unittest.main()
