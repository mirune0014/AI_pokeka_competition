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
REPLAY = Path(r"C:\Users\amuam\Downloads\88844273.json")
REPLAY_SHA256 = (
    "9E749F259D90655BE4C17F1795C15D277132C02E0167310394216609B90A7EBF"
)
BASELINE = (
    REPO_ROOT
    / "alakazam_staged_20260729"
    / "versions"
    / "alakazam_newdeck_v1_package_runtime_certified_fix5"
)
CANDIDATE = (
    REPO_ROOT
    / "alakazam_staged_20260729"
    / "versions"
    / "alakazam_newdeck_v3_psychic_draw_optional_fix1"
)
ENGINE = (
    REPO_ROOT
    / "analysis_outputs"
    / "cynthia_v9_vs_v11_poffin_role_selection_20260713"
    / "seeded_engine"
)
EXPECTED = {
    67: [0],
    98: [0],
    121: [4],
    148: [7],
}
EXACT_KEYS = {
    "episode_id",
    "source_replay_sha256",
    "agent_index",
    "source_step_index",
    "semantic_label",
    "expected_baseline_action",
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


def isolated_action(policy_dir, fixture_path):
    script = (
        "import json, pathlib, sys;"
        "policy=pathlib.Path(sys.argv[1]);"
        "fixture=json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8'));"
        "sys.path.insert(0,str(policy));"
        "import main;"
        "print(json.dumps(main.agent(fixture['observation']),separators=(',',':')))"
    )
    env = dict(os.environ)
    inherited = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(ENGINE)
        if not inherited
        else os.pathsep.join((str(ENGINE), inherited))
    )
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
        raise AssertionError(
            f"{policy_dir.name} failed for {fixture_path.name}: "
            f"{completed.stderr}"
        )
    return json.loads(completed.stdout.strip().splitlines()[-1])


class Episode88844273PublicObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.replay_bytes = REPLAY.read_bytes()
        cls.replay = json.loads(cls.replay_bytes.decode("utf-8"))
        cls.fixtures = [
            (
                path,
                json.loads(path.read_text(encoding="utf-8")),
            )
            for path in sorted(FIXTURE_DIR.glob("*.json"))
        ]

    def test_replay_identity_schema_hash_and_public_boundary(self):
        self.assertEqual(
            hashlib.sha256(self.replay_bytes).hexdigest().upper(),
            REPLAY_SHA256,
        )
        self.assertEqual(len(self.fixtures), 4)
        self.assertEqual(
            {fixture["source_step_index"] for _, fixture in self.fixtures},
            set(EXPECTED),
        )
        for path, fixture in self.fixtures:
            with self.subTest(path=path.name):
                self.assertEqual(set(fixture), EXACT_KEYS)
                self.assertEqual(fixture["episode_id"], 88844273)
                self.assertEqual(
                    fixture["source_replay_sha256"], REPLAY_SHA256
                )
                self.assertEqual(fixture["agent_index"], 1)
                self.assertIsInstance(fixture["semantic_label"], str)
                self.assertTrue(fixture["semantic_label"])
                step = fixture["source_step_index"]
                observation = fixture["observation"]
                self.assertEqual(
                    observation,
                    self.replay["steps"][step][1]["observation"],
                )
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

    def test_next_step_action_alignment(self):
        for path, fixture in self.fixtures:
            with self.subTest(path=path.name):
                step = fixture["source_step_index"]
                aligned = self.replay["steps"][step + 1][1]["action"]
                self.assertEqual(aligned, EXPECTED[step])
                self.assertEqual(
                    fixture["expected_baseline_action"], aligned
                )

    def test_baseline_and_candidate_actions_are_exactly_unchanged(self):
        for path, fixture in self.fixtures:
            with self.subTest(path=path.name, policy="baseline"):
                baseline = isolated_action(BASELINE, path)
                self.assertEqual(
                    baseline, fixture["expected_baseline_action"]
                )
            with self.subTest(path=path.name, policy="candidate"):
                candidate = isolated_action(CANDIDATE, path)
                self.assertEqual(
                    candidate, fixture["expected_baseline_action"]
                )
                self.assertEqual(candidate, baseline)


if __name__ == "__main__":
    unittest.main()
