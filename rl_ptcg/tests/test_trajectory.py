import tempfile
import unittest
from pathlib import Path

from rl_ptcg.trajectory import TrajectoryRecord, make_record, read_jsonl, write_jsonl


def observation():
    return {"current": {"yourIndex": 1, "players": [{}, {}]}, "select": {"option": [{"type": 1}, {"type": 2}]}}


class TrajectoryTests(unittest.TestCase):
    def test_record_round_trip_jsonl(self):
        record = make_record(
            observation(), "ep-1", 4, [1, 2], 0, 1, True, 1, 1.0,
            "mirror", "bot", [1, 2, 3], 8,
        )
        self.assertEqual(1, record.seat)
        self.assertEqual(1, record.selected_action)
        self.assertEqual([1, 2, 3], record.opponent_deck)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            write_jsonl(path, [record])
            self.assertEqual([record], read_jsonl(path))

    def test_value_only_record_uses_fixed_perspective(self):
        data = observation()
        data["current"]["yourIndex"] = 1
        record = make_record(data, "ep-value", 0, perspective_seat=0, policy_target=False)
        self.assertEqual(0, record.seat)
        self.assertFalse(record.policy_target)

    def test_rejects_mismatched_scores(self):
        record = make_record(observation(), "ep", 0)
        with self.assertRaises(ValueError):
            TrajectoryRecord("ep", 0, 0, record.state_vector, record.option_vectors, [1.0], None, None)


if __name__ == "__main__":
    unittest.main()
