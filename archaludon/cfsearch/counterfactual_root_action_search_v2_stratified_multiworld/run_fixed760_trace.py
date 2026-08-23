"""Execute the immutable accepted-parent fixed-760 trace corpus.

The schedule mirrors the historical-Silver panel (100 games per seat) and
the seven adjacent opponent families (40 games per seat).  This runner only
executes the accepted parent; it intentionally does not invoke a candidate or
the checked paired comparison runner.  Each cell delegates to
``trace_preserving_battle.py`` and preserves the exact command, exit code, and
summary location in an orchestrator manifest.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
TRACE_RUNNER = HERE / "trace_preserving_battle.py"


def _clean_or_base(relative: str) -> Path:
    candidate = (REPO_ROOT / relative).resolve()
    if candidate.exists():
        return candidate
    base_root = (REPO_ROOT.parent / "AI_pokeka_competition").resolve()
    return (base_root / relative).resolve()


def _default_cells() -> list[dict[str, Any]]:
    return [
        {
            "panel": "historical_silver",
            "opponent_family": "historical_silver",
            "opponent_policy_id": "historical_silver_archaludon_54495224",
            "opponent_path": "archaludon/baseline/historical_silver_archaludon_54495224",
            "games": 100,
            "seed_base": 271828182,
        },
        {
            "panel": "adjacent_population",
            "opponent_family": "arch_peak",
            "opponent_policy_id": "submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710",
            "opponent_path": "archive/submissions/submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710",
            "games": 40,
            "seed_base": 271958313,
        },
        {
            "panel": "adjacent_population",
            "opponent_family": "arch_shumpei",
            "opponent_policy_id": "archaludon_shumpei_current_v3",
            "opponent_path": "opponents/meta_agents/archaludon_shumpei_current_v3",
            "games": 40,
            "seed_base": 271958313,
        },
        {
            "panel": "adjacent_population",
            "opponent_family": "alakazam_capbloo_gold",
            "opponent_policy_id": "alakazam_capbloo_gold_85357128_simple",
            "opponent_path": "opponents/meta_agents/alakazam_capbloo_gold_85357128_simple",
            "games": 40,
            "seed_base": 271958313,
        },
        {
            "panel": "adjacent_population",
            "opponent_family": "marnie_kazuki_live",
            "opponent_policy_id": "marnie_kazuki_live_85083586_simple",
            "opponent_path": "opponents/meta_agents/marnie_kazuki_live_85083586_simple",
            "games": 40,
            "seed_base": 271958313,
        },
        {
            "panel": "adjacent_population",
            "opponent_family": "mega_lucario_public",
            "opponent_policy_id": "mega_lucario_public_simple",
            "opponent_path": "opponents/meta_agents/mega_lucario_public_simple",
            "games": 40,
            "seed_base": 271958313,
        },
        {
            "panel": "adjacent_population",
            "opponent_family": "kang_crustle",
            "opponent_policy_id": "kangaskhan_crustle_mpgaming_v23_heal_role_missing160_guard",
            "opponent_path": "opponents/meta_agents/kangaskhan_crustle_mpgaming_v23_heal_role_missing160_guard",
            "games": 40,
            "seed_base": 271958313,
        },
        {
            "panel": "adjacent_population",
            "opponent_family": "cynthia_v23",
            "opponent_policy_id": "cynthia_garchomp_nasuo445_v23_allcall_before_evolve",
            "opponent_path": "opponents/meta_agents/cynthia_garchomp_nasuo445_v23_allcall_before_evolve",
            "games": 40,
            "seed_base": 271958313,
        },
    ]


def _command(
    *,
    engine_dir: Path,
    parent_dir: Path,
    opponent_dir: Path,
    output_dir: Path,
    cell: dict[str, Any],
    policy_seat: int,
    max_steps: int,
    schedule_key: str,
) -> list[str]:
    if policy_seat == 0:
        agent_a, agent_b = parent_dir, opponent_dir
    else:
        agent_a, agent_b = opponent_dir, parent_dir
    stem = f"{cell['opponent_family']}_p{policy_seat}"
    return [
        sys.executable,
        str(TRACE_RUNNER),
        "--engine-dir", str(engine_dir),
        "--agent-a", str(agent_a),
        "--agent-b", str(agent_b),
        "--deck-a", str(agent_a / "deck.csv"),
        "--deck-b", str(agent_b / "deck.csv"),
        "--games", str(cell["games"]),
        "--max-steps", str(max_steps),
        "--trace-dir", str(output_dir / "traces" / stem),
        "--summary", str(output_dir / "summaries" / f"{stem}.jsonl"),
        "--seed-base", str(cell["seed_base"]),
        "--schedule-key", schedule_key,
        "--panel", str(cell["panel"]),
        "--opponent-family", str(cell["opponent_family"]),
        "--opponent-policy-id", str(cell["opponent_policy_id"]),
        "--opponent-path", str(opponent_dir),
        "--opponent-deck-path", str(opponent_dir / "deck.csv"),
        "--policy-seat", str(policy_seat),
    ]


def run(args: argparse.Namespace) -> dict[str, Any]:
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    parent_dir = args.parent_agent.resolve()
    engine_dir = args.engine_dir.resolve()
    cells = _default_cells()
    manifest: list[dict[str, Any]] = []
    failures: list[str] = []
    sequence = 0
    for cell in cells:
        opponent_dir = _clean_or_base(str(cell["opponent_path"]))
        if not (opponent_dir / "main.py").is_file() or not (opponent_dir / "deck.csv").is_file():
            failures.append(f"missing opponent agent/deck: {opponent_dir}")
            continue
        cell_root = output_root / str(cell["panel"]) / str(cell["opponent_family"])
        for policy_seat in (0, 1):
            command = _command(
                engine_dir=engine_dir,
                parent_dir=parent_dir,
                opponent_dir=opponent_dir,
                output_dir=cell_root,
                cell=cell,
                policy_seat=policy_seat,
                max_steps=args.max_steps,
                schedule_key=args.schedule_key,
            )
            started = time.monotonic()
            completed = subprocess.run(command, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
            runtime = time.monotonic() - started
            record = {
                "sequence": sequence,
                "panel": cell["panel"],
                "opponent_family": cell["opponent_family"],
                "opponent_policy_id": cell["opponent_policy_id"],
                "policy_seat": policy_seat,
                "games": cell["games"],
                "seed_base": cell["seed_base"],
                "opponent_dir": str(opponent_dir),
                "command": command,
                "exit_code": int(completed.returncode),
                "runtime_seconds": runtime,
                "stdout_path": str((cell_root / "stdout" / f"{cell['opponent_family']}_p{policy_seat}.txt").resolve()),
                "summary_path": str((cell_root / "summaries" / f"{cell['opponent_family']}_p{policy_seat}.jsonl").resolve()),
            }
            stdout_path = Path(record["stdout_path"])
            stdout_path.parent.mkdir(parents=True, exist_ok=True)
            stdout_path.write_text((completed.stdout or "") + (completed.stderr or ""), encoding="utf-8", newline="\n")
            manifest.append(record)
            sequence += 1
            print(json.dumps(record, ensure_ascii=True, sort_keys=True), flush=True)
            if completed.returncode != 0:
                failures.append(f"cell failed: {cell['opponent_family']} seat {policy_seat} exit {completed.returncode}")
                if args.stop_on_failure:
                    break
        if failures and args.stop_on_failure:
            break

    manifest_path = output_root / "orchestrator_manifest.jsonl"
    manifest_path.write_text("".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in manifest), encoding="utf-8", newline="\n")
    report = {
        "schema_version": "archaludon_formal_realized_seeded_world_fixed760_trace_run.v1",
        "schedule_key": args.schedule_key,
        "parent_agent": str(parent_dir),
        "parent_main_sha256": __import__("hashlib").sha256((parent_dir / "main.py").read_bytes()).hexdigest(),
        "parent_deck_sha256": __import__("hashlib").sha256((parent_dir / "deck.csv").read_bytes()).hexdigest(),
        "engine_dir": str(engine_dir),
        "expected_games": 760,
        "executed_games": sum(int(row["games"]) for row in manifest if row["exit_code"] == 0),
        "cell_count": len(manifest),
        "failures": failures,
        "manifest_path": str(manifest_path.resolve()),
    }
    (output_root / "orchestrator_report.json").write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--parent-agent", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--schedule-key", default="archaludon_counterfactual_root_action_search_v2_v22_fixed760_20260816")
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--stop-on-failure", action="store_true")
    args = parser.parse_args()
    if args.max_steps <= 0:
        parser.error("--max-steps must be positive")
    return args


if __name__ == "__main__":
    report = run(parse_args())
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))
    if report["failures"]:
        raise SystemExit(1)
