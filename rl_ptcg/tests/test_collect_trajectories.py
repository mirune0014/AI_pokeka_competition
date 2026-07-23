import unittest

from rl_ptcg.collect_trajectories import (
    build_episode_specs,
    build_manifest,
    label_terminal_records,
    partition_episode_specs,
    terminal_reward,
)
from rl_ptcg.trajectory import make_record


def observation():
    return {"current": {"yourIndex": 0, "players": [{}, {}]}, "select": {"option": [{"type": 1}]}}


class CollectTrajectoryTests(unittest.TestCase):
    def test_schedule_is_deterministic_balanced_and_partitioned(self):
        specs = build_episode_specs([("a", "one"), ("b", "two")], 3, 19)
        self.assertEqual([0, 1, 0, 0, 1, 0], [item["trainee_seat"] for item in specs])
        self.assertEqual([19, 20, 21, 22, 23, 24], [item["seed"] for item in specs])
        shards = partition_episode_specs(specs, 2)
        self.assertEqual([0, 2, 4], [item["episode_number"] for item in shards[0]])
        self.assertEqual([1, 3, 5], [item["episode_number"] for item in shards[1]])

    def test_terminal_labels_apply_to_every_record_and_only_last_is_terminal(self):
        records = [make_record(observation(), "episode", step) for step in range(3)]
        labeled = label_terminal_records(records, 1, 1)
        self.assertEqual([1, 1, 1], [record.result for record in labeled])
        self.assertEqual([1.0, 1.0, 1.0], [record.reward for record in labeled])
        self.assertEqual([1.0 / 3] * 3, [record.value_weight for record in labeled])
        self.assertEqual([False, False, True], [record.terminal for record in labeled])
        self.assertEqual([False, False, False], [record.terminal for record in records])
        self.assertEqual((0, -1.0), terminal_reward(0, 1))
        self.assertEqual((-1, 0.0), terminal_reward(-1, 0))

    def test_manifest_counts_records_and_statuses(self):
        config = {"engine_dir": "engine", "baseline": "baseline", "opponents": ["a"], "seed": 3,
                  "max_steps": 10, "workers": 2}
        manifest = build_manifest(config, [
            {"worker": 1, "shard": "shard-001.jsonl", "records": 1, "episodes": [{"status": "error"}]},
            {"worker": 0, "shard": "shard-000.jsonl", "records": 2, "episodes": [{"status": "complete"}, {"status": "complete"}]},
        ], 3)
        self.assertEqual(3, manifest["record_count"])
        self.assertEqual({"complete": 2, "error": 1}, manifest["status_counts"])
        self.assertEqual(["shard-000.jsonl", "shard-001.jsonl"], [item["path"] for item in manifest["shards"]])


if __name__ == "__main__":
    unittest.main()
