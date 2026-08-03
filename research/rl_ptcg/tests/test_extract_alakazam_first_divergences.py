from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
TOOLS = ROOT / "infrastructure" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import extract_alakazam_first_divergences as extractor


DECK_HASH = "a" * 64
OTHER_DECK_HASH = "b" * 64


def canonical_line(value: dict) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def option(card_id: int, option_index: int, source_index: int) -> dict:
    return {
        "area": 2,
        "attack_id": None,
        "card_id": card_id,
        "in_play_area": None,
        "in_play_index": None,
        "index": source_index,
        "option_index": option_index,
        "player_index": 0,
        "raw": {"type": 7, "index": source_index},
        "serial": 1000 + card_id,
        "type": 7,
    }


def reordered(options: list[dict]) -> list[dict]:
    result = []
    for new_index, original in enumerate(reversed(options)):
        value = json.loads(json.dumps(original))
        value["option_index"] = new_index
        result.append(value)
    return result


class SyntheticFixture:
    seed_base = 100
    seed = 100
    opponent = "fixture_opponent"
    seat = 0
    game = 0

    def __init__(self, root: Path) -> None:
        self.root = root
        self.paired = root / "paired.csv"
        self.baseline_suite = root / "baseline_suite"
        self.candidate_suite = root / "candidate_suite"
        self.output = root / "output"

    @staticmethod
    def callback(
        ordinal: int,
        *,
        options: list[dict] | None = None,
        action: list[int] | None = None,
        own_active_hp: int = 70,
        context: int = 0,
    ) -> tuple[dict, dict, dict]:
        legal = options or [option(10, 0, 0), option(20, 1, 1)]
        selected = action if action is not None else [0]
        observation = {
            "context": context,
            "first_player": 0,
            "log_serial_fields": [],
            "logs_raw": [],
            "max_count": 1,
            "min_count": 1,
            "opponent_active": [99, 999],
            "opponent_active_energy": [],
            "opponent_active_hp": 90,
            "option_count": len(legal),
            "options": legal,
            "own_active": [1, 101],
            "own_active_energy": [],
            "own_active_hp": own_active_hp,
            "own_bench": [],
            "own_discard": [],
            "own_hand": [[10, 1010], [20, 1020]],
            "result": -1,
            "select_type": 0,
            "turn": ordinal + 1,
            "turn_action_count": ordinal + 2,
            "your_index": 0,
        }
        start = {
            "callback_ordinal": ordinal,
            "event": "CALL_START",
            "game": 0,
            "observation": observation,
            "opponent": SyntheticFixture.opponent,
            "policy_seat": 0,
            "run_id": "",
            "schema_version": "alakazam-staged-metrics-v1",
            "seed": SyntheticFixture.seed,
            "seed_base": SyntheticFixture.seed_base,
            "version": "",
        }
        end = {
            "added_rule_hits": [],
            "callback_ordinal": ordinal,
            "event": "CALL_END",
            "exception": None,
            "game": 0,
            "opponent": SyntheticFixture.opponent,
            "policy_seat": 0,
            "run_id": "",
            "schema_version": "alakazam-staged-metrics-v1",
            "seed": SyntheticFixture.seed,
            "seed_base": SyntheticFixture.seed_base,
            "selected_action": selected,
            "selected_options": [legal[index] for index in selected],
            "structural_invalid_reasons": [],
            "structurally_valid": True,
            "version": "",
        }
        battle = {
            "game": 0,
            "step": ordinal,
            "player": 0,
            "context": context,
            "context_card_id": None,
            "effect_card_id": None,
            "select_type": 0,
            "min_count": 1,
            "max_count": 1,
            "option_count": len(legal),
            "selection_deck_ids": [],
            "options": [value["raw"] for value in legal],
            "action": selected,
            "own_hand_ids": [10, 20],
            "snapshot": {
                "turn": ordinal + 1,
                "turn_action_count": ordinal + 2,
                "your_index": 0,
                "first_player": 0,
                "result": -1,
                "p0_active": 1,
                "p0_active_hp": own_active_hp,
            },
            "logs": [],
            "scores": [],
        }
        return start, end, battle

    def _write_paired(
        self,
        *,
        baseline_steps: int,
        candidate_steps: int,
        duplicate: bool = False,
    ) -> None:
        fieldnames = [
            "seed_base",
            "opponent",
            "seat",
            "game",
            "seed",
            "baseline_result",
            "candidate_result",
            "baseline_win",
            "candidate_win",
            "baseline_steps",
            "candidate_steps",
        ]
        row = {
            "seed_base": self.seed_base,
            "opponent": self.opponent,
            "seat": self.seat,
            "game": self.game,
            "seed": self.seed,
            "baseline_result": 0,
            "candidate_result": 0,
            "baseline_win": 1,
            "candidate_win": 1,
            "baseline_steps": baseline_steps,
            "candidate_steps": candidate_steps,
        }
        with self.paired.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerow(row)
            if duplicate:
                writer.writerow(row)

    def _write_suite(
        self,
        suite: Path,
        version: str,
        callbacks: list[tuple[dict, dict, dict]],
        *,
        sidecar_mode: str = "normal",
        battle_context_delta: int = 0,
        event_seed_delta: int = 0,
        summary_seed_delta: int = 0,
    ) -> None:
        suite.mkdir(parents=True, exist_ok=True)
        (suite / "suite_manifest.json").write_text(
            canonical_line({"versions": [{"name": version}]}) + "\n",
            encoding="utf-8",
        )
        run_dir = (
            suite
            / "runs"
            / version
            / self.opponent
            / f"seed_{self.seed_base}"
            / f"seat_{self.seat}"
        )
        sidecar_dir = run_dir / "sidecars"
        battle_dir = run_dir / "battle_traces"
        sidecar_dir.mkdir(parents=True)
        battle_dir.mkdir(parents=True)
        sidecar_events: list[dict] = []
        battle_rows: list[dict] = []
        run_id = f"{version}__{self.opponent}__{self.seed_base}__p{self.seat}"
        for start_raw, end_raw, battle_raw in callbacks:
            start = json.loads(json.dumps(start_raw))
            end = json.loads(json.dumps(end_raw))
            battle = json.loads(json.dumps(battle_raw))
            start["version"] = version
            end["version"] = version
            start["run_id"] = run_id
            end["run_id"] = run_id
            start["seed"] += event_seed_delta
            end["seed"] += event_seed_delta
            battle["context"] += battle_context_delta
            sidecar_events.extend([start, end])
            battle_rows.append(battle)
        if sidecar_mode == "missing_end":
            sidecar_events = sidecar_events[:-1]
        elif sidecar_mode == "orphan_end":
            sidecar_events = [sidecar_events[1]]
        elif sidecar_mode == "duplicate_start":
            sidecar_events.insert(1, json.loads(json.dumps(sidecar_events[0])))
        sidecar_path = sidecar_dir / "game_0000.jsonl"
        sidecar_path.write_text(
            "".join(canonical_line(value) + "\n" for value in sidecar_events),
            encoding="utf-8",
        )
        battle_path = battle_dir / "game_0000.jsonl"
        battle_path.write_text(
            "".join(canonical_line(value) + "\n" for value in battle_rows),
            encoding="utf-8",
        )
        summary = {
            "game": 0,
            "seed": self.seed + summary_seed_delta,
            "started": True,
            "steps": len(battle_rows),
            "hit_max_steps": False,
            "result": 0,
            "action_errors": 0,
            "trace": str(battle_path),
        }
        (run_dir / "summary.jsonl").write_text(
            canonical_line(summary) + "\n", encoding="utf-8"
        )

    def create(
        self,
        baseline_callbacks: list[tuple[dict, dict, dict]],
        candidate_callbacks: list[tuple[dict, dict, dict]],
        *,
        baseline_sidecar_mode: str = "normal",
        candidate_sidecar_mode: str = "normal",
        candidate_battle_context_delta: int = 0,
        candidate_event_seed_delta: int = 0,
        candidate_summary_seed_delta: int = 0,
        duplicate_schedule: bool = False,
    ) -> None:
        self._write_paired(
            baseline_steps=len(baseline_callbacks),
            candidate_steps=len(candidate_callbacks),
            duplicate=duplicate_schedule,
        )
        self._write_suite(
            self.baseline_suite,
            "v0",
            baseline_callbacks,
            sidecar_mode=baseline_sidecar_mode,
        )
        self._write_suite(
            self.candidate_suite,
            "v1",
            candidate_callbacks,
            sidecar_mode=candidate_sidecar_mode,
            battle_context_delta=candidate_battle_context_delta,
            event_seed_delta=candidate_event_seed_delta,
            summary_seed_delta=candidate_summary_seed_delta,
        )

    def config(self) -> extractor.ExtractionConfig:
        return extractor.ExtractionConfig(
            comparison="B",
            paired_results=self.paired,
            baseline_suite=self.baseline_suite,
            candidate_suite=self.candidate_suite,
            output_dir=self.output,
            output_name="first_divergence",
            baseline_version="v0",
            candidate_version="v1",
            baseline_deck_hash=DECK_HASH,
            candidate_deck_hash=DECK_HASH,
        )

    def extract_one(self) -> dict:
        rows = extractor.extract_rows(self.config())
        self.assert_single_schedule(rows)
        return rows[0]

    @staticmethod
    def assert_single_schedule(rows: list[dict]) -> None:
        if len(rows) != 1:
            raise AssertionError(f"expected one schedule row, got {len(rows)}")


class FirstDivergenceExtractorTests(unittest.TestCase):
    def test_state_split(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = SyntheticFixture(Path(tmp))
            fixture.create(
                [fixture.callback(0, own_active_hp=70)],
                [fixture.callback(0, own_active_hp=60)],
            )
            row = fixture.extract_one()
            self.assertEqual(
                extractor.CLASS_PRE_STATE_SPLIT, row["classification"]
            )
            self.assertEqual(0, row["callback_ordinal"])

    def test_legal_split(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = SyntheticFixture(Path(tmp))
            baseline = fixture.callback(0)
            candidate_options = [option(10, 0, 0), option(30, 1, 2)]
            candidate = fixture.callback(0, options=candidate_options)
            fixture.create([baseline], [candidate])
            row = fixture.extract_one()
            self.assertEqual(
                extractor.CLASS_LEGAL_SET_SPLIT, row["classification"]
            )

    def test_semantic_policy_divergence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = SyntheticFixture(Path(tmp))
            fixture.create(
                [fixture.callback(0, action=[0])],
                [fixture.callback(0, action=[1])],
            )
            row = fixture.extract_one()
            self.assertEqual(
                extractor.CLASS_POLICY_DIVERGENCE, row["classification"]
            )
            self.assertNotEqual(
                row["baseline_semantic_action_sha256"],
                row["candidate_semantic_action_sha256"],
            )

    def test_raw_order_only_continues_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = SyntheticFixture(Path(tmp))
            original = [option(10, 0, 0), option(20, 1, 1)]
            fixture.create(
                [
                    fixture.callback(0, options=original, action=[0]),
                    fixture.callback(1),
                ],
                [
                    fixture.callback(
                        0,
                        options=reordered(original),
                        action=[1],
                    ),
                    fixture.callback(1),
                ],
            )
            row = fixture.extract_one()
            self.assertEqual(extractor.CLASS_RAW_ORDER_ONLY, row["classification"])
            self.assertEqual(0, row["first_raw_order_only_ordinal"])
            self.assertEqual(1, row["raw_order_only_count"])

    def test_earlier_state_split_stops_before_later_action_split(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = SyntheticFixture(Path(tmp))
            fixture.create(
                [
                    fixture.callback(0, own_active_hp=70),
                    fixture.callback(1, action=[0]),
                ],
                [
                    fixture.callback(0, own_active_hp=60),
                    fixture.callback(1, action=[1]),
                ],
            )
            row = fixture.extract_one()
            self.assertEqual(
                extractor.CLASS_PRE_STATE_SPLIT, row["classification"]
            )
            self.assertEqual(0, row["callback_ordinal"])

    def test_missing_orphan_and_duplicate_sidecar_events_are_invalid(self) -> None:
        for mode in ("missing_end", "orphan_end", "duplicate_start"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                fixture = SyntheticFixture(Path(tmp))
                callback = fixture.callback(0)
                fixture.create(
                    [callback],
                    [callback],
                    candidate_sidecar_mode=mode,
                )
                row = fixture.extract_one()
                self.assertEqual(
                    extractor.CLASS_TRACE_INVALID, row["classification"]
                )
                self.assertEqual("INVALID", row["trace_status"])

    def test_battle_mismatch_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = SyntheticFixture(Path(tmp))
            callback = fixture.callback(0)
            fixture.create(
                [callback],
                [callback],
                candidate_battle_context_delta=1,
            )
            row = fixture.extract_one()
            self.assertEqual(extractor.CLASS_TRACE_INVALID, row["classification"])
            self.assertIn("context mismatch", row["detail"])

    def test_sidecar_and_summary_seed_mismatches_are_invalid(self) -> None:
        cases = (
            {"candidate_event_seed_delta": 1},
            {"candidate_summary_seed_delta": 1},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as tmp:
                fixture = SyntheticFixture(Path(tmp))
                callback = fixture.callback(0)
                fixture.create([callback], [callback], **kwargs)
                row = fixture.extract_one()
                self.assertEqual(
                    extractor.CLASS_TRACE_INVALID, row["classification"]
                )
                self.assertIn("seed", row["detail"])

    def test_duplicate_schedule_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = SyntheticFixture(Path(tmp))
            callback = fixture.callback(0)
            fixture.create(
                [callback],
                [callback],
                duplicate_schedule=True,
            )
            with self.assertRaisesRegex(
                extractor.InputValidationError, "duplicate paired schedule key"
            ):
                extractor.extract_rows(fixture.config())

    def test_checked_outcome_result_and_steps_must_match_suite(self) -> None:
        for field, value in (("result", 1), ("steps", 2)):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                fixture = SyntheticFixture(Path(tmp))
                callback = fixture.callback(0)
                fixture.create([callback], [callback])
                summary_path = (
                    fixture.candidate_suite
                    / "runs"
                    / "v1"
                    / fixture.opponent
                    / f"seed_{fixture.seed_base}"
                    / f"seat_{fixture.seat}"
                    / "summary.jsonl"
                )
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                summary[field] = value
                summary_path.write_text(
                    canonical_line(summary) + "\n", encoding="utf-8"
                )
                row = fixture.extract_one()
                self.assertEqual(
                    extractor.CLASS_TRACE_INVALID, row["classification"]
                )
                self.assertIn(field, row["detail"])

    def test_hash_stability_and_ascii_canonicalization(self) -> None:
        left = {"z": ["ミュウツー", {"b": 2, "a": 1}], "a": True}
        right = {"a": True, "z": ["ミュウツー", {"a": 1, "b": 2}]}
        self.assertEqual(extractor.canonical_json(left), extractor.canonical_json(right))
        self.assertEqual(
            extractor.canonical_sha256(left), extractor.canonical_sha256(right)
        )
        self.assertIn("\\u30df", extractor.canonical_json(left))

    def test_comparison_a_records_callback_unavailable_operational_split(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = SyntheticFixture(Path(tmp))
            fixture._write_paired(baseline_steps=4, candidate_steps=5)
            config = extractor.ExtractionConfig(
                comparison="A",
                paired_results=fixture.paired,
                output_dir=fixture.output,
                output_name="comparison_a",
                baseline_version="alakazam_800_frozen",
                candidate_version="v0",
                baseline_deck_hash=OTHER_DECK_HASH,
                candidate_deck_hash=DECK_HASH,
            )
            rows = extractor.extract_rows(config)
            self.assertEqual(1, len(rows))
            self.assertEqual(
                extractor.CLASS_OPERATIONAL_SPLIT, rows[0]["classification"]
            )
            self.assertEqual(
                "CALLBACK_TRACE_UNAVAILABLE", rows[0]["trace_status"]
            )
            paths = extractor.write_outputs(config.validated(), rows)
            self.assertEqual(
                {"csv", "jsonl", "markdown"},
                set(paths),
            )
            with paths["csv"].open("r", encoding="utf-8", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertEqual(1, len(csv_rows))

    def test_role_binding_and_same_deck_hash_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = SyntheticFixture(Path(tmp))
            callback = fixture.callback(0)
            fixture.create([callback], [callback])
            bad_version = extractor.ExtractionConfig(
                **{
                    **fixture.config().__dict__,
                    "candidate_version": "v2",
                }
            )
            with self.assertRaisesRegex(
                extractor.InputValidationError, "role binding"
            ):
                bad_version.validated()
            bad_deck = extractor.ExtractionConfig(
                **{
                    **fixture.config().__dict__,
                    "candidate_deck_hash": OTHER_DECK_HASH,
                }
            )
            with self.assertRaisesRegex(
                extractor.InputValidationError, "same deck hash"
            ):
                bad_deck.validated()


if __name__ == "__main__":
    unittest.main()
