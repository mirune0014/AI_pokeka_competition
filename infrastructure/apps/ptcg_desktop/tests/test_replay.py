from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from ptcg_desktop.replay import (
    ReplayBuilder,
    ReplayError,
    canonical_json,
    export_visualizer_json,
    load_replay,
    normalize_full_frame,
)

from helpers import full_frame


class ReplayTests(unittest.TestCase):
    def build(self, path: Path) -> Path:
        builder = ReplayBuilder("match-1")
        first = full_frame()
        builder.ingest_visualizer([first], revision=0, captured_after="battle_start")
        second = full_frame(acting=1, turn=2)
        builder.ingest_visualizer([first, second], revision=1, captured_after="battle_select")
        target, _ = builder.seal(
            path,
            artifact={"artifact_manifest_id": "test"},
            settings={"human_seat": 0},
            decks={"human": [1] * 60, "agent": [2] * 60},
            public_log=[{"type": "TurnStart"}],
            result={"classification": "normal", "winner_seat": 0},
            diagnostics={"steps": 1},
        )
        return target

    def test_round_trip_and_navigation_frames(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            replay = load_replay(self.build(Path(temporary) / "match.ptcgmatch"))
            self.assertEqual(len(replay.frames), 2)
            self.assertEqual(replay.frames[0]["frame_index"], 0)
            self.assertEqual(replay.frames[1]["payload"]["current"]["turn"], 2)
            self.assertTrue(replay.visualizer_exact)
            self.assertEqual(replay.visualizer[1]["current"]["turn"], 2)

    def test_single_visualizer_json_is_exported_for_other_viewers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            replay = load_replay(self.build(Path(temporary) / "match.ptcgmatch"))
            target, digest = export_visualizer_json(replay)
            self.assertEqual(target.name, "match.visualizer.json")
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest().upper(), digest)
            exported = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(exported, list(replay.visualizer))
            self.assertEqual(normalize_full_frame(exported[-1]), replay.frames[-1]["payload"])

    def test_legacy_replay_reconstructs_visualizer_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = self.build(Path(temporary) / "match.ptcgmatch")
            with zipfile.ZipFile(path, "r") as archive:
                members = {name: archive.read(name) for name in archive.namelist() if name != "visualizer.json"}
            manifest = json.loads(members["manifest.json"].decode("utf-8"))
            manifest["members"].pop("visualizer.json")
            manifest["content_sha256"] = hashlib.sha256(canonical_json(manifest["members"])).hexdigest().upper()
            members["manifest.json"] = canonical_json(manifest)
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in members.items():
                    archive.writestr(name, data)
            replay = load_replay(path)
            self.assertFalse(replay.visualizer_exact)
            self.assertEqual(len(replay.visualizer), len(replay.frames))
            self.assertEqual(normalize_full_frame(replay.visualizer[-1]), replay.frames[-1]["payload"])

    def test_visualizer_prefix_change_is_rejected(self) -> None:
        builder = ReplayBuilder("match-1")
        first = full_frame()
        builder.ingest_visualizer([first], revision=0, captured_after="battle_start")
        changed = full_frame()
        changed["current"]["turn"] = 99
        with self.assertRaises(ReplayError):
            builder.ingest_visualizer([changed], revision=1, captured_after="battle_select")

    def test_unexpected_zip_member_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = self.build(Path(temporary) / "match.ptcgmatch")
            with zipfile.ZipFile(path, "a") as archive:
                archive.writestr("unexpected.txt", b"bad")
            with self.assertRaises(ReplayError):
                load_replay(path)

    def test_no_images_are_embedded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = self.build(Path(temporary) / "match.ptcgmatch")
            with zipfile.ZipFile(path) as archive:
                self.assertFalse(any(name.lower().endswith((".jpg", ".png", ".webp")) for name in archive.namelist()))


if __name__ == "__main__":
    unittest.main()
