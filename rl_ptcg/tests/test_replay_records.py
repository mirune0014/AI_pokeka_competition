import copy
import json
import tempfile
import unittest
from pathlib import Path

from rl_ptcg.canonical_actions import canonicalize_prompt_action
from rl_ptcg.replay_records import (
    SCHEMA_VERSION,
    ReplayDecisionRecord,
    load_diagnostic_records,
    load_policy_records,
    load_value_records,
    read_jsonl,
    write_jsonl,
)


class Item:
    def __init__(self, **values):
        self.__dict__.update(values)


def as_object(value):
    if isinstance(value, dict):
        return Item(**{key: as_object(item) for key, item in value.items()})
    if isinstance(value, list):
        return [as_object(item) for item in value]
    return value


def observation():
    return {
        "current": {
            "yourIndex": 0, "turn": 4,
            "players": [
                {"hand": [{"id": "own-hand"}], "deck": [{"id": "own-deck"}], "prizes": [{"id": "own-prize"}],
                 "active": [{"id": "own-active", "serial": 2}], "bench": [], "discard": [{"id": "own-discard"}]},
                {"hand": [{"id": "opponent-hand"}], "deck": [{"id": "opponent-deck"}], "prizes": [{"id": "opponent-prize"}],
                 "active": [{"id": "opponent-active"}], "bench": [], "discard": [{"id": "opponent-discard"}]},
            ],
        },
        "select": {"context": "PLAY", "minCount": 1, "maxCount": 1, "option": [
            {"type": "PLAY", "area": 2, "index": 0, "playerIndex": 0, "serial": 99},
        ]},
    }


def record(data=None, **kwargs):
    data = observation() if data is None else data
    defaults = {"episode_id": "episode-a", "submission_id": "submission-a", "style_id": "style-a",
                "decision_step": 3, "replay_step": 7, "timestamp": "2026-07-11T00:00:00+00:00"}
    defaults.update(kwargs)
    return ReplayDecisionRecord.from_observation(data, [0], **defaults)


class ReplayRecordsTests(unittest.TestCase):
    def test_dict_and_object_observations_preserve_actor_hand_only(self):
        first = record()
        second = record(as_object(observation()))
        self.assertEqual(first.state_id, second.state_id)
        encoded = json.dumps(first.to_dict(), sort_keys=True)
        self.assertIn("own-hand", encoded)
        self.assertNotIn("opponent-hand", encoded)
        self.assertNotIn("opponent-deck", encoded)
        self.assertNotIn("opponent-prize", encoded)

    def test_safe_payload_has_semantic_options_but_no_raw_coordinates(self):
        result = record(public_history=[{"playerIndex": 0, "serial": 12, "index": 2, "kind": "attack"}])
        encoded = json.dumps(result.to_dict(), sort_keys=True)
        self.assertNotIn('"serial"', encoded)
        self.assertNotIn('"index"', encoded)
        self.assertEqual("self", result.public_history[0]["playerIndex"])
        self.assertEqual("own-hand", result.known_private_info["hand"][0]["id"])
        self.assertEqual("own-hand", result.legal_semantic_options[0]["source_card_id"])

    def test_history_is_caller_controlled_and_affects_ids_only_when_passed(self):
        first = record()
        changed_observation = copy.deepcopy(observation())
        changed_observation["future_history"] = [{"secret": "not passed"}]
        self.assertEqual(first.state_id, record(changed_observation).state_id)
        later = record(public_history=[{"player": 1, "event": "retreat"}])
        self.assertNotEqual(first.state_id, later.state_id)
        self.assertEqual("opponent", later.public_history[0]["player"])

    def test_stable_ids_bind_replay_and_chosen_action(self):
        first = record()
        self.assertEqual(first, record())
        later_step = record(replay_step=8)
        self.assertNotEqual(first.decision_id, later_step.decision_id)
        self.assertEqual(SCHEMA_VERSION, first.schema_version)

    def test_jsonl_round_trip_and_complete_action_validation(self):
        data = observation()
        complete = canonicalize_prompt_action(data, [0])
        source = record(data, canonical_complete_actions=[complete])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            write_jsonl(path, [source])
            self.assertEqual([source], read_jsonl(path))
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["state_id"] = "bad"
            path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "IDs do not validate"):
                read_jsonl(path)

    def test_policy_whitelist_excludes_terminal_diagnostics_and_source_metadata(self):
        source = record(terminal_result={"winner": 0}, source_metadata={"token": "secret"},
                        exact_hidden_diagnostics={"opponent_deck": ["never-policy"]})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            write_jsonl(path, [source])
            policy = load_policy_records([path])[0]
            value = load_value_records([path])[0]
        self.assertNotIn("terminal_result", policy)
        self.assertNotIn("exact_hidden_diagnostics", policy)
        self.assertNotIn("source_metadata", policy)
        self.assertEqual({"winner": 0}, value["terminal_result"])
        self.assertNotIn("exact_hidden_diagnostics", value)

    def test_exact_hidden_records_are_rejected_for_policy_and_available_to_diagnostics(self):
        source = record(label_source="exact_hidden_diagnostic", exact_hidden_diagnostics={"deck": ["x"]})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "diagnostics.jsonl"
            write_jsonl(path, [source])
            with self.assertRaisesRegex(ValueError, "not valid policy"):
                load_policy_records([path])
            self.assertEqual([source.to_dict()], load_diagnostic_records([path]))

    def test_chosen_action_round_trips_semantically_and_malformed_schema_is_rejected(self):
        source = record()
        self.assertEqual(canonicalize_prompt_action(observation(), [0]).to_dict(), source.chosen_canonical_action)
        payload = source.to_dict()
        del payload["style_id"]
        with self.assertRaisesRegex(ValueError, "schema"):
            ReplayDecisionRecord.from_dict(payload)

    def test_known_search_multiset_ignores_order_but_looking_order_and_private_history_are_retained(self):
        first_observation = observation()
        first_observation["select"]["deck"] = [
            {"id": 20, "serial": 2},
            {"id": 10, "serial": 1},
            {"id": 20, "serial": 3},
        ]
        first_observation["current"]["looking"] = [{"id": 30, "serial": 4}, {"id": 40, "serial": 5}]
        private_action = canonicalize_prompt_action(first_observation, [0])
        first = record(first_observation, private_action_history=[private_action])
        self.assertEqual([10, 20, 20], first.known_private_info["searchable_deck_multiset"])
        self.assertEqual([30, 40], first.known_private_info["looking_order"])
        self.assertEqual([private_action.to_dict()], first.known_private_info["private_action_history"])

        reordered = copy.deepcopy(first_observation)
        reordered["select"]["deck"] = list(reversed(reordered["select"]["deck"]))
        for serial, card in enumerate(reordered["select"]["deck"], 100):
            card["serial"] = serial
        self.assertEqual(first.state_id, record(reordered, private_action_history=[private_action]).state_id)

        changed_known_order = copy.deepcopy(first_observation)
        changed_known_order["current"]["looking"] = list(reversed(changed_known_order["current"]["looking"]))
        self.assertNotEqual(first.state_id, record(changed_known_order, private_action_history=[private_action]).state_id)


if __name__ == "__main__":
    unittest.main()
