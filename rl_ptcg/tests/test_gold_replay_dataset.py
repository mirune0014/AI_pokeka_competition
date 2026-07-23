import csv
from hashlib import sha256
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
import uuid
import subprocess
import sys

from rl_ptcg.gold_replay_dataset import (
    _parse_timestamp,
    _terminal,
    _uuid_timestamp,
    build_gold_replay_dataset,
    load_gold_replay_split,
    verify_gold_replay_dataset,
)
from rl_ptcg.replay_records import load_policy_records
from rl_ptcg.split_manifest import load_split_manifest


def _player(prefix):
    return {"deckCount": 50, "handCount": 1, "prizeCount": 6, "hand": [{"id": f"{prefix}-hand"}],
            "deck": [{"id": f"{prefix}-secret"}], "prizes": [{"id": f"{prefix}-prize"}],
            "active": [{"id": f"{prefix}-active"}], "bench": [], "discard": []}


def _observation(seat, turn=1):
    return {"current": {"yourIndex": seat, "turn": turn, "players": [_player("zero"), _player("one")]},
            "select": {"context": 0, "type": 0, "minCount": 1, "maxCount": 1,
                       "option": [{"type": 14, "area": 2, "index": 0, "playerIndex": seat}]}}


def _replay(episode, replay_id):
    first = [{"observation": _observation(0)}, {"observation": _observation(1)}]
    second = [{"action": [0]}, {"action": [0]}]
    third = [{"observation": _observation(0, 2)}, {"observation": _observation(1, 2)}]
    fourth = [{"action": [0]}, {"action": [0]}]
    return {"id": str(replay_id), "info": {"EpisodeId": episode}, "configuration": {"seed": 44},
            "rewards": [1, -1], "steps": [first, second, third, fourth]}


class GoldReplayDatasetTests(unittest.TestCase):
    def _write_inputs(self, root, *, postdate_second=False):
        root = Path(root)
        replay_dir = root / "replays"
        replay_dir.mkdir()
        match_id = uuid.uuid1()
        (replay_dir / "one.json").write_text(json.dumps(_replay(101, match_id)), encoding="utf-8")
        cards = " ".join(str(value) for value in range(60))
        with (root / "decks.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["episode_id", "file", "player_index", "team", "reward", "archetype", "deck_id", "deck"])
            writer.writeheader()
            writer.writerow({"episode_id": 101, "file": "replays/one.json", "player_index": 0, "team": "Gold", "reward": 1, "archetype": "alpha", "deck_id": "a", "deck": cards})
            writer.writerow({"episode_id": 101, "file": "replays/one.json", "player_index": 1, "team": "Silver", "reward": -1, "archetype": "beta", "deck_id": "b", "deck": cards})
        before = datetime.now(timezone.utc) - timedelta(days=2)
        after = datetime.now(timezone.utc) + timedelta(days=2)
        with (root / "leaderboard.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["Rank", "TeamName", "TeamId", "LastSubmissionDate", "Score"])
            writer.writeheader()
            writer.writerow({"Rank": 1, "TeamName": "Gold", "TeamId": 11, "LastSubmissionDate": before.isoformat(), "Score": "99.0"})
            writer.writerow({"Rank": 99, "TeamName": "Silver", "TeamId": 12, "LastSubmissionDate": (after if postdate_second else before).isoformat(), "Score": "1.0"})
        return replay_dir, root / "decks.csv", root / "leaderboard.csv", match_id

    def _write_selection(self, root, replay_path, match_id):
        root = Path(root)
        match_time = datetime.fromtimestamp((match_id.time - 0x01B21DD213814000) / 1e7, timezone.utc)
        path = root / "selection.csv"
        fields = [
            "episode_id", "player_index", "team", "gold_rank", "gold_score", "team_id",
            "last_submission_date_utc", "submission_version_proxy", "gold_snapshot_sha256",
            "gold_snapshot_path", "gold_snapshot_timestamp_utc", "gold_proxy_confidence",
            "match_timestamp_utc", "replay_sha256", "file",
        ]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerow({
                "episode_id": 101,
                "player_index": 0,
                "team": "Gold",
                "gold_rank": 1,
                "gold_score": "99.0",
                "team_id": 11,
                "last_submission_date_utc": (match_time - timedelta(days=1)).isoformat(),
                "submission_version_proxy": "team:11:last_submission:frozen",
                "gold_snapshot_sha256": "cd" * 32,
                "gold_snapshot_path": "leaderboard/snapshot.csv",
                "gold_snapshot_timestamp_utc": (match_time + timedelta(hours=1)).isoformat(),
                "gold_proxy_confidence": "postgame_same_submission",
                "match_timestamp_utc": match_time.isoformat(),
                "replay_sha256": sha256(replay_path.read_bytes()).hexdigest(),
                "file": "replays/one.json",
            })
        return path, match_time

    def test_gold_filtering_perspective_metadata_and_rerun(self):
        with tempfile.TemporaryDirectory() as directory:
            replays, seats, board, match_id = self._write_inputs(directory)
            output = Path(directory) / "gold"
            first = build_gold_replay_dataset([replays], seat_metadata_csv=seats, leaderboard_csv=board,
                output_dir=output, gold_rank_max=20, split_seed="fixed", holdout_style_families=["Gold"])
            bytes_before = {path.name: path.read_bytes() for path in output.iterdir()}
            second = build_gold_replay_dataset([replays], seat_metadata_csv=seats, leaderboard_csv=board,
                output_dir=output, gold_rank_max=20, split_seed="fixed", holdout_style_families=["Gold"])
            self.assertEqual(first, second)
            self.assertEqual(bytes_before, {path.name: path.read_bytes() for path in output.iterdir()})
            policy = load_policy_records([output / "decision_records.jsonl"])
            self.assertEqual(2, len(policy))
            self.assertEqual({0}, {row["acting_seat"] for row in policy})
            self.assertEqual({"alpha"}, {row["own_archetype"] for row in policy})
            self.assertEqual({"beta"}, {row["opponent_archetype"] for row in policy})
            self.assertNotIn("terminal_result", policy[0])
            raw = [json.loads(line) for line in (output / "decision_records.jsonl").read_text().splitlines()]
            self.assertEqual("44", raw[0]["source_metadata"]["configuration_seed"])
            self.assertEqual(64, len(raw[0]["source_metadata"]["deck_variant_sha256"]))
            self.assertEqual("gold_snapshot_proxy", raw[0]["source_metadata"]["selection_provenance"])
            self.assertTrue(raw[0]["source_metadata"]["submission_id_is_proxy"])
            self.assertEqual(_uuid_timestamp({"id": str(match_id)}), raw[0]["timestamp"])
            self.assertNotIn("zero-secret", json.dumps(policy, sort_keys=True))
            split = load_split_manifest(output / "split_manifest.json")
            self.assertEqual({"policy_family_holdout"}, {item["split"] for item in split["items"]})
            self.assertEqual(1, split["component_count"])
            transactions = [json.loads(line) for line in (output / "retrospective_transactions.jsonl").read_text().splitlines()]
            self.assertTrue(transactions)
            self.assertIn("supervision_metadata", transactions[0])
            self.assertNotIn("child_decision_ids", raw[0])
            manifest = json.loads((output / "dataset_manifest.json").read_text())
            self.assertEqual("non_gold_team", next(iter(manifest["skips"])))
            unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
            self.assertEqual(sha256((json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")).hexdigest(), manifest["manifest_sha256"])

    def test_both_gold_seats_keep_their_own_perspectives(self):
        with tempfile.TemporaryDirectory() as directory:
            replays, seats, board, _ = self._write_inputs(directory)
            with board.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[1]["Rank"] = "2"
            with board.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            output = Path(directory) / "gold"
            build_gold_replay_dataset([replays], seat_metadata_csv=seats, leaderboard_csv=board,
                output_dir=output, gold_rank_max=20, split_seed="fixed")
            records = [json.loads(line) for line in (output / "decision_records.jsonl").read_text().splitlines()]
            self.assertEqual({0, 1}, {record["acting_seat"] for record in records})
            self.assertEqual({("alpha", "beta"), ("beta", "alpha")}, {(record["own_archetype"], record["opponent_archetype"]) for record in records})

    def test_postdated_submission_is_skipped_and_manifest_tamper_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            replays, seats, board, _ = self._write_inputs(directory, postdate_second=True)
            output = Path(directory) / "gold"
            build_gold_replay_dataset([replays], seat_metadata_csv=seats, leaderboard_csv=board,
                output_dir=output, gold_rank_max=100, split_seed="fixed")
            manifest = json.loads((output / "dataset_manifest.json").read_text())
            self.assertEqual(2, manifest["record_count"])
            self.assertEqual(1, manifest["skips"]["leaderboard_submission_postdates_replay"])
            (output / "dataset_manifest.json").write_text("{}\n", encoding="ascii")
            with self.assertRaises(FileExistsError):
                build_gold_replay_dataset([replays], seat_metadata_csv=seats, leaderboard_csv=board,
                    output_dir=output, gold_rank_max=100, split_seed="fixed")

    def test_conflicting_episode_checksums_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            replays, seats, board, _ = self._write_inputs(directory)
            changed = json.loads((replays / "one.json").read_text())
            changed["configuration"]["seed"] = 45
            (replays / "copy.json").write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "conflicting checksums for episode 101"):
                build_gold_replay_dataset([replays], seat_metadata_csv=seats, leaderboard_csv=board,
                    output_dir=Path(directory) / "gold", split_seed="fixed")

    def test_naive_kaggle_timestamp_is_utc_and_draw_has_no_winner(self):
        parsed = _parse_timestamp("2026-07-09 13:18:00")
        self.assertEqual(timezone.utc, parsed.tzinfo)
        self.assertEqual("2026-07-09T13:18:00+00:00", parsed.isoformat())
        self.assertEqual({"winner_seat": None, "seat_reward": "0"}, _terminal({"rewards": [0, 0]}, "0"))

    def test_frozen_multi_snapshot_catalog_derives_replays_and_time_blind(self):
        with tempfile.TemporaryDirectory() as directory:
            replays, seats, _board, match_id = self._write_inputs(directory)
            selection, match_time = self._write_selection(directory, replays / "one.json", match_id)
            output = Path(directory) / "catalog-gold"
            result = build_gold_replay_dataset(
                [],
                seat_metadata_csv=seats,
                gold_selection_csv=selection,
                output_dir=output,
                split_seed="catalog-fixed",
                blind_date_periods=[match_time.date().isoformat()],
                workspace=directory,
            )
            self.assertEqual(2, result["record_count"])
            policy = load_policy_records([output / "decision_records.jsonl"])
            self.assertEqual({0}, {row["acting_seat"] for row in policy})
            raw = json.loads((output / "decision_records.jsonl").read_text().splitlines()[0])
            self.assertEqual("postgame_same_submission", raw["source_metadata"]["gold_proxy_confidence"])
            self.assertEqual(sha256(selection.read_bytes()).hexdigest(), raw["source_metadata"]["selection_catalog_sha256"])
            split = load_split_manifest(output / "split_manifest.json")
            self.assertEqual({"blind"}, {row["split"] for row in split["items"]})
            manifest = json.loads((output / "dataset_manifest.json").read_text())
            self.assertEqual("frozen_gold_selection_catalog", manifest["selection_source"]["mode"])
            self.assertEqual(1, len(manifest["selected_seats"]))
            self.assertEqual(1, manifest["skips"]["not_in_frozen_gold_selection"])
            verified = verify_gold_replay_dataset(output)
            self.assertEqual(2, len(verified["records"]))
            with self.assertRaisesRegex(PermissionError, "sealed"):
                load_gold_replay_split(output, "blind")
            self.assertEqual(2, len(load_gold_replay_split(output, "blind", allow_blind=True)))

            transactions = output / "retrospective_transactions.jsonl"
            transactions.write_bytes(transactions.read_bytes() + b"{}\n")
            with self.assertRaisesRegex(ValueError, "artifact checksum"):
                verify_gold_replay_dataset(output)

    def test_cli_is_directly_runnable_from_repository_root(self):
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [sys.executable, "tools/build_gold_replay_dataset.py", "--help"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("--gold-selection-csv", result.stdout)


if __name__ == "__main__":
    unittest.main()
