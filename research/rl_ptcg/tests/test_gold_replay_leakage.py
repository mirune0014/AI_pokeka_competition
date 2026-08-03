import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from research.rl_ptcg.replay_records import ReplayDecisionRecord, load_policy_records, write_jsonl


def _player(prefix):
    return {
        "deckCount": 20,
        "handCount": 2,
        "prizeCount": 4,
        "hand": [{"id": f"{prefix}-hand-a", "serial": 10}, {"id": f"{prefix}-hand-b", "serial": 11}],
        "deck": [{"id": f"{prefix}-hidden-deck"}],
        "prizes": [{"id": f"{prefix}-hidden-prize"}],
        "active": [{"id": f"{prefix}-active", "serial": 12}],
        "bench": [{"id": f"{prefix}-bench", "serial": 13}],
        "discard": [{"id": f"{prefix}-discard", "serial": 14}],
    }


def _observation(actor_seat=0):
    return {
        "current": {
            "yourIndex": actor_seat,
            "firstPlayer": actor_seat,
            "turn": 6,
            "players": [_player("actor"), _player("opponent")],
        },
        "select": {
            "context": "PLAY",
            "minCount": 1,
            "maxCount": 1,
            "option": [
                {"type": "PLAY", "area": 2, "index": 0, "playerIndex": actor_seat, "serial": 90},
                {"type": "PLAY", "area": 2, "index": 1, "playerIndex": actor_seat, "serial": 91},
            ],
        },
    }


def _record(observation, action, **kwargs):
    return ReplayDecisionRecord.from_observation(
        observation,
        action,
        episode_id="episode-leakage",
        submission_id="submission-leakage",
        style_id="style-leakage",
        decision_step=2,
        replay_step=9,
        timestamp="2026-07-11T00:00:00+00:00",
        **kwargs,
    )


def _all_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _all_keys(child)


class GoldReplayLeakageTests(unittest.TestCase):
    def test_same_actor_is_invariant_to_absolute_seat_relabeling(self):
        original = _observation(0)
        relabeled = copy.deepcopy(original)
        relabeled["current"]["players"] = list(reversed(relabeled["current"]["players"]))
        relabeled["current"]["yourIndex"] = 1
        relabeled["current"]["firstPlayer"] = 1
        for option in relabeled["select"]["option"]:
            option["playerIndex"] = 1

        first = _record(original, [0])
        second = _record(relabeled, [0])
        self.assertEqual(first.safe_observation, second.safe_observation)
        self.assertEqual(first.known_private_info, second.known_private_info)
        self.assertEqual(first.legal_semantic_options, second.legal_semantic_options)
        self.assertEqual(first.chosen_canonical_action, second.chosen_canonical_action)
        self.assertEqual(first.state_id, second.state_id)
        self.assertNotEqual(first.acting_seat, second.acting_seat)

    def test_hidden_zones_and_future_fields_cannot_change_policy_state(self):
        original = _observation(0)
        changed = copy.deepcopy(original)
        changed["current"]["players"][0]["deck"] = [{"id": "new-own-order"}]
        changed["current"]["players"][0]["prizes"] = [{"id": "new-own-prize"}]
        changed["current"]["players"][1]["hand"] = [{"id": "new-opponent-hand"}]
        changed["current"]["players"][1]["deck"] = [{"id": "new-opponent-order"}]
        changed["current"]["players"][1]["prizes"] = [{"id": "new-opponent-prize"}]
        changed["future_log"] = [{"draw": "future-card", "winner": 1}]
        changed["exact_top_bottom_constraints"] = {"top": [999], "bottom": [998]}

        first = _record(original, [0])
        second = _record(changed, [0])
        self.assertEqual(first.state_id, second.state_id)
        self.assertEqual(first.chosen_canonical_action, second.chosen_canonical_action)
        encoded = json.dumps(first.to_dict(), sort_keys=True)
        for secret in ("opponent-hand", "opponent-hidden-deck", "opponent-hidden-prize"):
            self.assertNotIn(secret, encoded)

        own_hand_changed = copy.deepcopy(original)
        own_hand_changed["current"]["players"][0]["hand"][0]["id"] = "known-new-own-card"
        own_hand_changed["select"]["option"][0]["index"] = 1
        self.assertNotEqual(first.state_id, _record(own_hand_changed, [0]).state_id)

    def test_option_order_and_serial_changes_do_not_change_semantic_input(self):
        original = _observation(0)
        reordered = copy.deepcopy(original)
        reordered["select"]["option"] = list(reversed(reordered["select"]["option"]))
        for serial, option in enumerate(reordered["select"]["option"], 700):
            option["serial"] = serial
        for serial, card in enumerate(reordered["current"]["players"][0]["hand"], 800):
            card["serial"] = serial

        first = _record(original, [0])
        second = _record(reordered, [1])
        self.assertEqual(first.state_id, second.state_id)
        self.assertEqual(first.chosen_canonical_action, second.chosen_canonical_action)
        self.assertEqual(first.legal_semantic_options, second.legal_semantic_options)

    def test_future_history_is_excluded_unless_explicitly_supplied(self):
        observation = _observation(0)
        first = _record(observation, [0], public_history=[{"player": 0, "event": "draw"}])
        changed = copy.deepcopy(observation)
        changed["future_history"] = [{"player": 1, "event": "wins"}]
        second = _record(changed, [0], public_history=[{"player": 0, "event": "draw"}])
        self.assertEqual(first.state_id, second.state_id)
        with_future = _record(changed, [0], public_history=[
            {"player": 0, "event": "draw"},
            {"player": 1, "event": "wins"},
        ])
        self.assertNotEqual(first.state_id, with_future.state_id)

    def test_policy_whitelist_contains_no_engine_coordinates_or_diagnostics(self):
        source = _record(
            _observation(0),
            [0],
            source_metadata={"serial": 99, "rawOption": 0, "credential": "diagnostic-only"},
            exact_hidden_diagnostics={"opponent_deck": [999]},
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            write_jsonl(path, [source])
            policy = load_policy_records([path])[0]
        keys = set(_all_keys(policy))
        self.assertTrue({"index", "serial", "ordinal", "optionIndex", "option_index"}.isdisjoint(keys))
        self.assertNotIn("source_metadata", policy)
        self.assertNotIn("exact_hidden_diagnostics", policy)
        self.assertNotIn("terminal_result", policy)

    def test_state_id_is_stable_across_python_processes(self):
        observation_json = json.dumps(_observation(0), sort_keys=True)
        code = (
            "import json; "
            "from research.rl_ptcg.replay_records import ReplayDecisionRecord; "
            f"o=json.loads({observation_json!r}); "
            "r=ReplayDecisionRecord.from_observation(o,[0],episode_id='episode-leakage',"
            "submission_id='submission-leakage',style_id='style-leakage',decision_step=2,"
            "replay_step=9,timestamp='2026-07-11T00:00:00+00:00'); "
            "print(r.state_id)"
        )
        root = Path(__file__).resolve().parents[3]
        first = subprocess.check_output([sys.executable, "-c", code], cwd=root, text=True).strip()
        second = subprocess.check_output([sys.executable, "-c", code], cwd=root, text=True).strip()
        self.assertEqual(_record(_observation(0), [0]).state_id, first)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
