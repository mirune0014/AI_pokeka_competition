from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import combine_staged_panel_results as combiner


class PanelFixture:
    def __init__(self, root: Path, games: int = 2) -> None:
        self.root = root
        self.panel_root = root / "panels"
        self.out_dir = root / "out"
        self.seed = 100
        self.opponent = "opponent_a"
        self.games = games
        self.spec = root / "immutable_spec.md"
        self.amendment = root / "execution_amendment.md"
        self.spec.write_text("immutable\n", encoding="utf-8")
        self.amendment.write_text("amendment\n", encoding="utf-8")

    def config(self, max_attempts: int = 3) -> combiner.CombinationConfig:
        return combiner.CombinationConfig(
            panel_root=self.panel_root,
            out_dir=self.out_dir,
            comparison_name="fixture_comparison",
            seed_bases=(self.seed,),
            opponents=(self.opponent,),
            games_per_seat=self.games,
            max_attempts=max_attempts,
            immutable_spec=self.spec,
            execution_amendments=(self.amendment,),
            max_steps=1000,
        )

    @staticmethod
    def _summary_row(game: int, seed: int, result: int, steps: int) -> dict:
        return {
            "game": game,
            "seed": seed,
            "started": True,
            "steps": steps,
            "hit_max_steps": False,
            "result": result,
            "turn": 3 + game,
            "action_errors": 0,
        }

    def create_attempt(
        self,
        number: int,
        *,
        report_valid: bool,
        summary_result_delta: int = 0,
    ) -> Path:
        attempt = (
            self.panel_root
            / f"{self.seed}_{self.opponent}"
            / f"attempt_{number}"
        )
        summaries_dir = attempt / "summaries"
        summaries_dir.mkdir(parents=True, exist_ok=True)

        summaries: dict[tuple[int, str], list[dict]] = {}
        for seat in (0, 1):
            for role in combiner.ROLES:
                rows = []
                for game in range(self.games):
                    result = (seat + game) % 2
                    if role == "candidate":
                        result = (result + 1) % 2
                    rows.append(
                        self._summary_row(
                            game,
                            self.seed + game,
                            result,
                            20 + seat * 10 + game + (5 if role == "candidate" else 0),
                        )
                    )
                summaries[(seat, role)] = rows

        manifest_rows = []
        for seat in (0, 1):
            for role_index, role in enumerate(combiner.ROLES):
                sequence = seat * 3 + role_index
                summary_path = (
                    summaries_dir
                    / (
                        f"{sequence:04d}_{self.seed}_{self.opponent}"
                        f"_p{seat}_{role}.jsonl"
                    )
                )
                summary_path.write_text(
                    "".join(
                        json.dumps(row, ensure_ascii=True) + "\n"
                        for row in summaries[(seat, role)]
                    ),
                    encoding="utf-8",
                )
                command = [
                    sys.executable,
                    str(combiner.RUN_LOCAL_BATTLE),
                    "--engine-dir",
                    "fixture_engine",
                    "--games",
                    str(self.games),
                    "--max-steps",
                    "1000",
                    "--seed-base",
                    str(self.seed),
                    "--engine-seed",
                    "--summary",
                    str(summary_path.resolve()),
                ]
                manifest_rows.append(
                    {
                        "sequence": sequence,
                        "role": role,
                        "seed_base": self.seed,
                        "opponent": self.opponent,
                        "seat": seat,
                        "command": command,
                        "exit_code": 0,
                        "runtime_seconds": 0.1,
                    }
                )
        (attempt / "manifest.jsonl").write_text(
            "".join(
                json.dumps(row, ensure_ascii=True) + "\n" for row in manifest_rows
            ),
            encoding="utf-8",
        )

        paired_rows = []
        for seat in (0, 1):
            for game in range(self.games):
                baseline = summaries[(seat, "baseline_a")][game]
                candidate = summaries[(seat, "candidate")][game]
                paired_rows.append(
                    {
                        "seed_base": self.seed,
                        "opponent": self.opponent,
                        "seat": seat,
                        "game": game,
                        "seed": self.seed + game,
                        "baseline_result": baseline["result"],
                        "candidate_result": candidate["result"],
                        "baseline_win": int(baseline["result"] == seat),
                        "candidate_win": int(candidate["result"] == seat),
                        "baseline_steps": baseline["steps"],
                        "candidate_steps": candidate["steps"],
                    }
                )
        with (attempt / "paired_results.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(combiner.PAIRED_FIELDS))
            writer.writeheader()
            writer.writerows(paired_rows)

        rollups = combiner._panel_rollups(
            paired_rows, (self.seed,), (self.opponent,)
        )
        report = {
            "valid": report_valid,
            "invalid_reasons": [] if report_valid else ["fixture failure"],
            "duplicate_mismatch_count": 0,
            **rollups,
        }
        (attempt / "report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        if summary_result_delta:
            target = summaries_dir / (
                f"0002_{self.seed}_{self.opponent}_p0_candidate.jsonl"
            )
            rows = [
                json.loads(line)
                for line in target.read_text(encoding="utf-8").splitlines()
            ]
            rows[0]["result"] = (rows[0]["result"] + summary_result_delta) % 2
            target.write_text(
                "".join(json.dumps(row) + "\n" for row in rows),
                encoding="utf-8",
            )
        return attempt


class CombineStagedPanelResultsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.fixture = PanelFixture(Path(self.temporary.name))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_first_valid_attempt_is_selected_and_outputs_are_complete(self) -> None:
        self.fixture.create_attempt(1, report_valid=True)

        result = combiner.combine_panels(self.fixture.config())

        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["selected_attempts"][0]["attempt"], 1)
        paired_path = self.fixture.out_dir / "combined_paired_results.csv"
        with paired_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), self.fixture.games * 2)
        self.assertEqual(
            tuple(rows[0]),
            combiner.PAIRED_FIELDS,
        )
        manifest_lines = (
            self.fixture.out_dir / "combined_manifest.jsonl"
        ).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(manifest_lines), 6)
        recomputation = json.loads(
            (self.fixture.out_dir / "root_recomputation.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            recomputation["expected_schedule_sha256"],
            recomputation["actual_schedule_sha256"],
        )

    def test_failed_attempt_then_valid_attempt_selects_second(self) -> None:
        self.fixture.create_attempt(1, report_valid=False)
        self.fixture.create_attempt(2, report_valid=True)

        result = combiner.combine_panels(self.fixture.config())

        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["selected_attempts"][0]["attempt"], 2)
        provenance = json.loads(
            (self.fixture.out_dir / "combination_provenance.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            [attempt["report_valid"] for attempt in provenance["attempts"]],
            [False, True],
        )

    def test_root_failure_does_not_switch_to_later_valid_attempt(self) -> None:
        first = self.fixture.create_attempt(1, report_valid=True)
        self.fixture.create_attempt(2, report_valid=True)
        paired_path = first / "paired_results.csv"
        lines = paired_path.read_text(encoding="utf-8").splitlines()
        lines.append(lines[1])
        paired_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = combiner.combine_panels(self.fixture.config())

        self.assertFalse(result["valid"])
        self.assertEqual(result["selected_attempts"][0]["attempt"], 1)
        self.assertTrue(
            any("duplicate paired schedule key" in error for error in result["errors"])
        )
        self.assertTrue(
            any("attempts exist after first report-valid" in error for error in result["errors"])
        )
        self.assertFalse(
            (self.fixture.out_dir / "combined_paired_results.csv").exists()
        )

    def test_duplicate_paired_key_fails(self) -> None:
        attempt = self.fixture.create_attempt(1, report_valid=True)
        paired_path = attempt / "paired_results.csv"
        lines = paired_path.read_text(encoding="utf-8").splitlines()
        lines[-1] = lines[1]
        paired_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = combiner.combine_panels(self.fixture.config())

        self.assertFalse(result["valid"])
        self.assertTrue(
            any("duplicate paired schedule key" in error for error in result["errors"])
        )

    def test_missing_paired_row_fails(self) -> None:
        attempt = self.fixture.create_attempt(1, report_valid=True)
        paired_path = attempt / "paired_results.csv"
        lines = paired_path.read_text(encoding="utf-8").splitlines()
        paired_path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")

        result = combiner.combine_panels(self.fixture.config())

        self.assertFalse(result["valid"])
        self.assertTrue(
            any("paired schedule mismatch" in error for error in result["errors"])
        )

    def test_summary_to_paired_mismatch_fails(self) -> None:
        self.fixture.create_attempt(
            1, report_valid=True, summary_result_delta=1
        )

        result = combiner.combine_panels(self.fixture.config())

        self.assertFalse(result["valid"])
        self.assertTrue(
            any(
                "paired candidate_result disagrees with summary" in error
                for error in result["errors"]
            )
        )


if __name__ == "__main__":
    unittest.main()
