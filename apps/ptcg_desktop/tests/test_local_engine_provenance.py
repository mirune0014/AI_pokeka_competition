from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

from ptcg_desktop.artifacts import manifest_file_hashes, register_local_artifact
from ptcg_desktop.deck import read_deck_csv
from ptcg_desktop.replay import load_replay
from ptcg_desktop.supervisor import MatchLaunch, MatchSupervisor


@unittest.skipUnless(
    os.environ.get("PTCG_LOCAL_AGENT_ARTIFACT") and os.environ.get("PTCG_LOCAL_HUMAN_DECK"),
    "set PTCG_LOCAL_AGENT_ARTIFACT and PTCG_LOCAL_HUMAN_DECK",
)
class LocalEngineProvenanceTests(unittest.TestCase):
    def test_both_seats_seal_local_identity_and_file_hashes(self) -> None:
        artifact = Path(os.environ["PTCG_LOCAL_AGENT_ARTIFACT"]).resolve()
        deck = read_deck_csv(os.environ["PTCG_LOCAL_HUMAN_DECK"])
        manifest, report = register_local_artifact(artifact)
        self.assertTrue(report.verified, report.issues)
        self.assertEqual(report.trust_mode, "local_registered")
        expected_hashes = manifest_file_hashes(manifest)

        with tempfile.TemporaryDirectory() as temporary:
            for seat in (0, 1):
                with self.subTest(human_seat=seat):
                    replay_path = Path(temporary) / f"local-seat-{seat}.ptcgmatch"
                    supervisor = MatchSupervisor()
                    handled: set[str] = set()
                    try:
                        supervisor.start(
                            MatchLaunch(
                                artifact_source=artifact,
                                artifact_manifest=manifest,
                                human_deck=deck,
                                human_seat=seat,
                                replay_path=replay_path,
                                max_steps=6,
                            )
                        )
                        deadline = time.monotonic() + 60
                        while time.monotonic() < deadline:
                            for event in supervisor.poll(0.05):
                                if event["message_type"] != "decision.required":
                                    continue
                                decision = event["payload"]["decision"]
                                request_id = decision["request_id"]
                                if request_id in handled:
                                    continue
                                handled.add(request_id)
                                count = decision["min_count"]
                                tokens = [option["token"] for option in decision["options"][:count]]
                                supervisor.submit_decision(request_id, decision["state_revision"], tokens)
                            if supervisor.result is not None and supervisor.finalized:
                                break

                        self.assertTrue(supervisor.finalized)
                        self.assertIsNotNone(supervisor.result)
                        self.assertTrue(supervisor.replay_available)
                        self.assertEqual(supervisor.result.artifact_manifest_id, manifest["manifest_id"])
                        replay = load_replay(replay_path)
                        self.assertIsNone(replay.manifest["submission_id"])
                        self.assertEqual(replay.manifest["artifact_manifest_id"], manifest["manifest_id"])
                        self.assertEqual(replay.manifest["used_file_hashes"], expected_hashes)
                        self.assertEqual(replay.artifact["trust_mode"], "local_registered")
                        self.assertEqual(replay.artifact["files"], expected_hashes)
                    finally:
                        supervisor.close()


if __name__ == "__main__":
    unittest.main()
