import csv
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "infrastructure"
    / "tools"
    / "run_seeded_paired_suite.py"
)
SPEC = importlib.util.spec_from_file_location("run_seeded_paired_suite", MODULE_PATH)
run_seeded_paired_suite = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(run_seeded_paired_suite)


def _option(command, name):
    return command[command.index(name) + 1]


def _args(tmp_path):
    return SimpleNamespace(
        engine_dir=tmp_path / "engine",
        baseline=tmp_path / "baseline",
        candidate=tmp_path / "candidate",
        opponent=[("opponent", tmp_path / "opponent")],
        games_per_seat=1,
        seed_base=[700],
        max_steps=50,
        output_dir=tmp_path / "output",
        keep_traces=True,
        trace_options=True,
    )


class FakeBattleProcess:
    def __init__(self, *, baseline_trace_mismatch=False):
        self.baseline_trace_mismatch = baseline_trace_mismatch
        self.commands = []

    def __call__(self, command, **_kwargs):
        self.commands.append(command)
        summary_path = Path(_option(command, "--summary"))
        trace_dir = Path(_option(command, "--trace-dir"))
        stem = summary_path.stem
        role = next(
            role
            for role in ("baseline_a", "baseline_b", "candidate")
            if stem.endswith("_" + role)
        )
        trace_dir.mkdir(parents=True, exist_ok=True)
        action_payload = b"baseline\n"
        if role == "candidate":
            action_payload = b"candidate\n"
        elif role == "baseline_b" and self.baseline_trace_mismatch:
            action_payload = b"baseline-mismatch\n"
        validation_payload = b'{"agent_index":0,"sequence":0}\n'
        action_path = trace_dir / "game_0000.jsonl"
        validation_path = trace_dir / "game_0000.validation.jsonl"
        action_path.write_bytes(action_payload)
        validation_path.write_bytes(validation_payload)
        record = {
            "game": 0,
            "seed": int(_option(command, "--seed-base")),
            "started": True,
            "steps": 3,
            "hit_max_steps": False,
            "result": 0,
            "turn": 2,
            "action_errors": 0,
            "trace": str(action_path),
            "trace_sha256": hashlib.sha256(action_payload).hexdigest(),
            "validation_trace": str(validation_path),
            "validation_trace_sha256": hashlib.sha256(
                validation_payload
            ).hexdigest(),
            "validation_trace_record_count": 1,
        }
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")


def test_keep_traces_preserves_files_flags_and_role_hashes(tmp_path):
    args = _args(tmp_path)
    fake = FakeBattleProcess()

    report = run_seeded_paired_suite.run_suite(args, run_process=fake)

    assert report["valid"] is True
    assert len(fake.commands) == 6
    assert all("--trace-options" in command for command in fake.commands)
    trace_dirs = [Path(_option(command, "--trace-dir")) for command in fake.commands]
    assert all(path.parent.name == "traces" for path in trace_dirs)
    assert all((path / "game_0000.jsonl").is_file() for path in trace_dirs)
    assert all((path / "game_0000.validation.jsonl").is_file() for path in trace_dirs)

    manifest = [
        json.loads(line)
        for line in (args.output_dir / "manifest.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(manifest) == 6
    assert all(len(row["trace_artifacts"]) == 1 for row in manifest)
    assert all(row["trace_artifacts"][0]["action_trace_sha256"] for row in manifest)
    assert all(
        row["trace_artifacts"][0]["validation_trace_sha256"] for row in manifest
    )

    with (args.output_dir / "paired_results.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        paired = list(csv.DictReader(handle))
    assert len(paired) == 2
    for row in paired:
        for role in ("baseline_a", "baseline_b", "candidate"):
            assert row[f"{role}_action_trace_path"]
            assert row[f"{role}_action_trace_sha256"]
            assert row[f"{role}_validation_trace_path"]
            assert row[f"{role}_validation_trace_sha256"]


def test_duplicate_baseline_trace_hash_mismatch_invalidates_kept_suite(tmp_path):
    args = _args(tmp_path)
    fake = FakeBattleProcess(baseline_trace_mismatch=True)

    report = run_seeded_paired_suite.run_suite(args, run_process=fake)

    assert report["valid"] is False
    assert report["duplicate_mismatch_count"] == 1
    assert any(
        "duplicate baseline mismatch" in reason
        for reason in report["invalid_reasons"]
    )
    assert run_seeded_paired_suite.duplicate_mismatches(
        [{"result": 0, "steps": 1}],
        [{"result": 0, "steps": 1}],
        compare_trace_hash=True,
    )
