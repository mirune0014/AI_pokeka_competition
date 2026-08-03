from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
OUTPUT_ROOT = HERE / "changed_trace_smoke_raw"
RUNNER = ROOT / "tools" / "run_local_battle.py"
ENGINE = (
    ROOT
    / "analysis_outputs"
    / "cynthia_v9_vs_v11_poffin_role_selection_20260713"
    / "seeded_engine"
)
HISTORICAL = (
    ROOT
    / "analysis_outputs"
    / "reference_agents"
    / "historical_silver_archaludon_54495224"
)
CANDIDATE = (
    ROOT
    / "autonomous_gold_20260715"
    / "candidates"
    / "archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2"
)

EXPECTED_RUNNER_SHA = (
    "E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B"
)
EXPECTED_HISTORICAL_SHA = (
    "F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E"
)
EXPECTED_CANDIDATE_SHA = (
    "DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8"
)

CASES = (
    {
        "label": "historical_silver_p0_seed271828201",
        "opponent": HISTORICAL,
        "seat": 0,
        "seed": 271828201,
        "expect_trace_identity": False,
    },
    {
        "label": "arch_shumpei_p1_seed271958328",
        "opponent": ROOT / "meta_agents" / "archaludon_shumpei_current_v3",
        "seat": 1,
        "seed": 271958328,
        "expect_trace_identity": False,
    },
    {
        "label": "mega_lucario_p0_seed271958329",
        "opponent": ROOT / "meta_agents" / "mega_lucario_public_simple",
        "seat": 0,
        "seed": 271958329,
        "expect_trace_identity": False,
    },
    {
        "label": "mega_lucario_p1_seed271958318",
        "opponent": ROOT / "meta_agents" / "mega_lucario_public_simple",
        "seat": 1,
        "seed": 271958318,
        "expect_trace_identity": True,
    },
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run_branch(case: dict, branch: str, policy: pathlib.Path) -> dict:
    destination = OUTPUT_ROOT / case["label"] / branch
    trace_dir = destination / "traces"
    summary_path = destination / "summary.jsonl"
    if case["seat"] == 0:
        agent_a, agent_b = policy, case["opponent"]
    else:
        agent_a, agent_b = case["opponent"], policy
    command = [
        sys.executable,
        str(RUNNER),
        "--engine-dir",
        str(ENGINE),
        "--agent-a",
        str(agent_a),
        "--agent-b",
        str(agent_b),
        "--games",
        "1",
        "--max-steps",
        "1000",
        "--trace-dir",
        str(trace_dir),
        "--trace-options",
        "--seed-base",
        str(case["seed"]),
        "--engine-seed",
        "--summary",
        str(summary_path),
    ]
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "command.json").write_text(
        json.dumps(command, indent=2) + "\n",
        encoding="utf-8",
    )
    (destination / "stdout.txt").write_text(
        completed.stdout,
        encoding="utf-8",
    )
    (destination / "stderr.txt").write_text(
        completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode:
        raise AssertionError((case["label"], branch, completed.returncode))
    summaries = [
        json.loads(line)
        for line in summary_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(summaries) != 1:
        raise AssertionError((case["label"], branch, summaries))
    summary = summaries[0]
    trace_path = trace_dir / "game_0000.jsonl"
    if (
        not summary["started"]
        or summary["action_errors"] != 0
        or summary["hit_max_steps"]
        or summary["result"] != case["seat"]
        or not trace_path.is_file()
    ):
        raise AssertionError((case["label"], branch, summary))
    return {
        "branch": branch,
        "command": command,
        "exit_code": completed.returncode,
        "summary": summary,
        "summary_sha256": sha256(summary_path),
        "trace_path": str(trace_path.relative_to(ROOT)),
        "trace_sha256": sha256(trace_path),
    }


def assert_repaired_mega_branch(row: dict) -> dict:
    candidate_trace = ROOT / row["candidate"]["trace_path"]
    trace = [
        json.loads(line)
        for line in candidate_trace.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    divergence_callback = trace[41]
    if (
        divergence_callback["player"] != 1
        or divergence_callback["action"] != [5]
        or divergence_callback["options"][5].get("attackId") != 253
    ):
        raise AssertionError(("repaired old divergence", divergence_callback))
    following_opponent_attacks = [
        {
            "trace_row": index,
            "attack_id": entry.get("attackId"),
            "snapshot": callback["snapshot"],
        }
        for index, callback in enumerate(trace[42:], start=42)
        if callback["player"] == 1
        for entry in callback["logs"]
        if entry.get("playerIndex") == 0 and entry.get("attackId") is not None
    ]
    if not following_opponent_attacks:
        raise AssertionError("no following opponent attack")
    first_attack = following_opponent_attacks[0]
    if (
        first_attack["attack_id"] != 982
        or first_attack["snapshot"]["p1_active"] != 190
        or first_attack["snapshot"]["p1_active_hp"] != 40
        or first_attack["snapshot"]["p1_active_energy"] != 3
    ):
        raise AssertionError(("Mega Brave lock not preserved", first_attack))
    return {
        "old_divergence_trace_row": 41,
        "repaired_action": divergence_callback["action"],
        "repaired_attack_id": 253,
        "following_opponent_attack": first_attack,
    }


def main() -> None:
    if OUTPUT_ROOT.exists():
        raise AssertionError(("refusing existing output", OUTPUT_ROOT))
    if sha256(RUNNER) != EXPECTED_RUNNER_SHA:
        raise AssertionError("checked battle runner changed")
    if sha256(HISTORICAL / "main.py") != EXPECTED_HISTORICAL_SHA:
        raise AssertionError("historical source changed")
    if sha256(CANDIDATE / "main.py") != EXPECTED_CANDIDATE_SHA:
        raise AssertionError("candidate source changed")

    rows = []
    for case in CASES:
        baseline = run_branch(case, "historical", HISTORICAL)
        candidate = run_branch(case, "repaired", CANDIDATE)
        trace_identity = (
            baseline["trace_sha256"] == candidate["trace_sha256"]
        )
        if trace_identity != case["expect_trace_identity"]:
            raise AssertionError(
                (case["label"], trace_identity, baseline, candidate)
            )
        if (
            case["expect_trace_identity"]
            and baseline["summary"]["steps"] != candidate["summary"]["steps"]
        ):
            raise AssertionError((case["label"], baseline, candidate))
        rows.append(
            {
                **case,
                "opponent": str(case["opponent"].relative_to(ROOT)),
                "baseline": baseline,
                "candidate": candidate,
                "trace_identity": trace_identity,
            }
        )

    mega = next(
        row for row in rows
        if row["label"] == "mega_lucario_p1_seed271958318"
    )
    mega["mechanic_assertion"] = assert_repaired_mega_branch(mega)
    report = {
        "candidate_main_sha256": EXPECTED_CANDIDATE_SHA,
        "historical_main_sha256": EXPECTED_HISTORICAL_SHA,
        "checked_runner_sha256": EXPECTED_RUNNER_SHA,
        "cases": rows,
        "faults": {
            "nonzero_exits": 0,
            "action_errors": 0,
            "max_step_hits": 0,
            "unexpected_results": 0,
        },
    }
    report_path = HERE / "changed_trace_smoke_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "case_count": len(rows),
                "identity_cases": sum(row["trace_identity"] for row in rows),
                "nonidentity_cases": sum(
                    not row["trace_identity"] for row in rows
                ),
                "report": str(report_path),
                "report_sha256": sha256(report_path),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
