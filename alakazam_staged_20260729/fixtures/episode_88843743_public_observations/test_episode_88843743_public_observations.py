from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


FIXTURE_DIR = Path(__file__).resolve().parent
REPO_ROOT = FIXTURE_DIR.parents[2]
REPLAY = Path(r"C:\Users\amuam\Downloads\88843743.json")
REPLAY_SHA256 = (
    "B0B8752CA10D9319C667A5482323BF8A780A3038FFDD50AF7DCF588EDA882948"
)
PARENT = (
    REPO_ROOT
    / "alakazam_staged_20260729"
    / "versions"
    / "alakazam_newdeck_v4_next_attacker_distance_shadow_fix4b"
)
CANDIDATE = (
    REPO_ROOT
    / "alakazam_staged_20260729"
    / "versions"
    / "alakazam_newdeck_v4_wall_shadow_fix6"
)
ENGINE = (
    REPO_ROOT
    / "analysis_outputs"
    / "cynthia_v9_vs_v11_poffin_role_selection_20260713"
    / "seeded_engine"
)
EXPECTED = {22: [2], 23: [0]}
EXACT_KEYS = {
    "episode_id",
    "source_replay_sha256",
    "agent_index",
    "source_step_index",
    "semantic_label",
    "expected_parent_action",
    "observation_sha256",
    "observation",
}


def canonical_observation(observation):
    return json.dumps(
        observation,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def isolated_action(policy_dir: Path, fixture_path: Path):
    script = (
        "import json,pathlib,sys;"
        "policy=pathlib.Path(sys.argv[1]);"
        "fixture=json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8'));"
        "sys.path.insert(0,str(policy));"
        "import main;"
        "action=main.agent(fixture['observation']);"
        "print(json.dumps({'action':action,'rule':"
        "main.LAST_STAGED_POLICY_TRACE.get('rule_version')},separators=(',',':')))"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ENGINE)
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script, str(policy_dir), str(fixture_path)],
        cwd=policy_dir,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode:
        raise AssertionError(completed.stderr)
    return json.loads(completed.stdout.strip().splitlines()[-1])


class Episode88843743PublicObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = [
            (path, json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(FIXTURE_DIR.glob("*.json"))
        ]

    def test_durable_fixture_schema_hash_and_public_boundary(self):
        self.assertEqual(len(self.fixtures), 2)
        self.assertEqual(
            {fixture["source_step_index"] for _, fixture in self.fixtures},
            set(EXPECTED),
        )
        for path, fixture in self.fixtures:
            with self.subTest(path=path.name):
                self.assertEqual(set(fixture), EXACT_KEYS)
                self.assertEqual(fixture["episode_id"], 88843743)
                self.assertEqual(
                    fixture["source_replay_sha256"], REPLAY_SHA256
                )
                self.assertEqual(fixture["agent_index"], 1)
                self.assertEqual(
                    fixture["expected_parent_action"],
                    EXPECTED[fixture["source_step_index"]],
                )
                observation = fixture["observation"]
                self.assertEqual(
                    hashlib.sha256(
                        canonical_observation(observation)
                    ).hexdigest().upper(),
                    fixture["observation_sha256"],
                )
                self.assertEqual(observation["current"]["yourIndex"], 1)
                mine = observation["current"]["players"][1]
                opponent = observation["current"]["players"][0]
                self.assertIsInstance(mine["hand"], list)
                self.assertEqual(len(mine["hand"]), mine["handCount"])
                self.assertIsNone(opponent["hand"])
                self.assertIsNone(observation["current"]["looking"])
                self.assertTrue(
                    {"action", "reward", "info", "status"}.isdisjoint(
                        observation
                    )
                )

    def test_optional_source_replay_matches_exact_extraction(self):
        if not REPLAY.is_file():
            self.skipTest("source replay is not present; fixtures remain durable")
        payload = REPLAY.read_bytes()
        self.assertEqual(
            hashlib.sha256(payload).hexdigest().upper(), REPLAY_SHA256
        )
        replay = json.loads(payload.decode("utf-8"))
        for _, fixture in self.fixtures:
            step = fixture["source_step_index"]
            self.assertEqual(
                fixture["observation"],
                replay["steps"][step][1]["observation"],
            )
            self.assertEqual(
                fixture["expected_parent_action"],
                replay["steps"][step + 1][1]["action"],
            )

    def test_parent_and_candidate_actions_are_unchanged(self):
        for path, fixture in self.fixtures:
            with self.subTest(path=path.name):
                parent = isolated_action(PARENT, path)
                candidate = isolated_action(CANDIDATE, path)
                self.assertEqual(
                    parent["action"], fixture["expected_parent_action"]
                )
                self.assertEqual(candidate["action"], parent["action"])
                self.assertEqual(
                    parent["rule"],
                    "V4_NEXT_ATTACKER_DISTANCE_SHADOW_FIX4B",
                )
                self.assertEqual(candidate["rule"], "V4_WALL_SHADOW_FIX6")

    def test_before_after_semantics_are_replay_independent(self):
        fixtures = {
            fixture["source_step_index"]: fixture
            for _, fixture in self.fixtures
        }
        before = fixtures[22]["observation"]
        after = fixtures[23]["observation"]
        mine_before = before["current"]["players"][1]
        mine_after = after["current"]["players"][1]
        self.assertEqual(
            [(card["id"], card["serial"]) for card in mine_before["active"]],
            [(66, 79)],
        )
        self.assertEqual(mine_after["active"], [])
        self.assertEqual(before["current"]["turn"], after["current"]["turn"])
        self.assertTrue(
            any(
                option.get("type") == 10 and option.get("area") == 4
                for option in before["select"]["option"]
            )
        )
        self.assertEqual(after["select"]["context"], 4)


if __name__ == "__main__":
    unittest.main()
