"""Replay the immutable fixed-760 schedule once with telemetry-only adapter."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PYTHON = ROOT / ".venv-rl" / "Scripts" / "python.exe"
RUNNER = ROOT / "infrastructure" / "tools" / "run_local_battle.py"
ENGINE = (
    ROOT
     / "_local_generated" / "analysis_outputs"
    / "cynthia_v9_vs_v11_poffin_role_selection_20260713"
    / "seeded_engine"
)
ADAPTER = HERE / "diagnostic_agent"
CANDIDATE = (
    ROOT
    / "archaludon"
    / "candidates"
    / "archaludon_persistent_public_boss_access_ledger_last_copy_guard_v1"
)
TELEMETRY = HERE / "fixed760_resolver_telemetry_retry2.jsonl"
OUTPUT = HERE / "runner_outputs_retry2"

CELLS = [
    (
        "historical_silver",
        ROOT
         / "_local_generated" / "analysis_outputs"
        / "reference_agents"
        / "historical_silver_archaludon_54495224",
        100,
        271828182,
    ),
    (
        "arch_peak",
        ROOT
        / "submission_archaludon_gtmidguard_lucariobev_crustledeckguard_archattach_ruleinline_20260710",
        40,
        271958313,
    ),
    (
        "arch_shumpei",
        ROOT / "opponents" / "meta_agents" / "archaludon_shumpei_current_v3",
        40,
        271958313,
    ),
    (
        "alakazam_capbloo_gold",
        ROOT / "opponents" / "meta_agents" / "alakazam_capbloo_gold_85357128_simple",
        40,
        271958313,
    ),
    (
        "marnie_kazuki_live",
        ROOT / "opponents" / "meta_agents" / "marnie_kazuki_live_85083586_simple",
        40,
        271958313,
    ),
    (
        "mega_lucario_public",
        ROOT / "opponents" / "meta_agents" / "mega_lucario_public_simple",
        40,
        271958313,
    ),
    (
        "kang_crustle",
        ROOT
        / "opponents" / "meta_agents"
        / "kangaskhan_crustle_mpgaming_v23_heal_role_missing160_guard",
        40,
        271958313,
    ),
    (
        "cynthia_v23",
        ROOT
        / "opponents" / "meta_agents"
        / "cynthia_garchomp_nasuo445_v23_allcall_before_evolve",
        40,
        271958313,
    ),
]


def main() -> None:
    if TELEMETRY.exists() or OUTPUT.exists():
        raise FileExistsError("refusing to overwrite diagnostic output")
    OUTPUT.mkdir(parents=True)
    env = dict(os.environ)
    env["PTCG_BOSS_DIAGNOSTIC_TELEMETRY"] = str(TELEMETRY)
    manifest = []
    for label, opponent, games, seed_base in CELLS:
        for seat in (0, 1):
            stem = f"{label}_p{seat}"
            if seat == 0:
                agent_a, deck_a = ADAPTER, CANDIDATE / "deck.csv"
                agent_b, deck_b = opponent, opponent / "deck.csv"
            else:
                agent_a, deck_a = opponent, opponent / "deck.csv"
                agent_b, deck_b = ADAPTER, CANDIDATE / "deck.csv"
            command = [
                str(PYTHON),
                "-B",
                str(RUNNER),
                "--engine-dir",
                str(ENGINE),
                "--agent-a",
                str(agent_a),
                "--deck-a",
                str(deck_a),
                "--agent-b",
                str(agent_b),
                "--deck-b",
                str(deck_b),
                "--games",
                str(games),
                "--max-steps",
                "1000",
                "--seed-base",
                str(seed_base),
                "--engine-seed",
                "--summary",
                str(OUTPUT / f"{stem}.jsonl"),
                "--trace-dir",
                str(OUTPUT / f"{stem}_traces"),
            ]
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            manifest.append(
                {
                    "label": label,
                    "seat": seat,
                    "games": games,
                    "seed_base": seed_base,
                    "exit_code": completed.returncode,
                    "stderr": completed.stderr,
                }
            )
            if completed.returncode:
                raise SystemExit(completed.returncode)
    (HERE / "execution_manifest_retry2.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
