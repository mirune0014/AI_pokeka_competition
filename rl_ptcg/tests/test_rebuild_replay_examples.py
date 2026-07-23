import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from rl_ptcg.rebuild_replay_examples import (
    label_reports, public_belief_features, public_matchup, replay_index,
)


class RebuildReplayExamplesTests(unittest.TestCase):
    def test_aggregate_label_file_yields_every_report(self):
        with TemporaryDirectory() as root:
            path = Path(root) / "labels.json"
            path.write_text(json.dumps([
                {"episode_id": "1", "status": "complete"},
                {"episode_id": "2", "status": "skipped"},
            ]), encoding="ascii")
            reports = list(label_reports([path]))
            self.assertEqual(["1", "2"], [row[1]["episode_id"] for row in reports])

    def test_multiple_replay_directories_are_indexed(self):
        with TemporaryDirectory() as root:
            first = Path(root) / "first"
            second = Path(root) / "second"
            first.mkdir()
            second.mkdir()
            (first / "episode_11_replay.json").write_text("{}", encoding="ascii")
            (second / "episode_22_replay.json").write_text("{}", encoding="ascii")
            self.assertEqual({"11", "22"}, set(replay_index([first, second])))

    def test_public_belief_uses_only_compatible_catalog_decks(self):
        observation = {"current": {"yourIndex": 0, "players": [
            {}, {"active": [{"id": 3}], "bench": [], "discard": [], "prize": []},
        ]}}
        features = public_belief_features(
            observation, [[3] + [1] * 59, [4] + [2] * 59]
        )
        self.assertEqual(1.0, features["belief_unique"])
        self.assertEqual(1.0, features["belief_hypothesis_count=1"])
        self.assertEqual(1, sum(key.startswith("belief_signature=") for key in features))

    def test_public_matchup_extends_baseline_generic_detection(self):
        class Obj:
            def __init__(self, **values):
                self.__dict__.update(values)
        opponent = Obj(
            active=[Obj(id=647, tools=[], energyCards=[], preEvolution=[])],
            bench=[], discard=[], prize=[],
        )
        observation = Obj(current=Obj(yourIndex=0, players=[Obj(), opponent]))
        self.assertEqual("marnie", public_matchup(observation, "generic"))


if __name__ == "__main__":
    unittest.main()
