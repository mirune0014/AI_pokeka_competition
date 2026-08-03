from __future__ import annotations

import copy
import hashlib
import json
import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "infrastructure" / "tools"))

from ptcg_common import ensure_engine_on_path, load_agent, read_deck


CANDIDATE = ROOT / (
    "autonomous_gold_20260715/candidates/"
    "archaludon_historical_silver_single_resolver_salvage_rule3_repair_v2"
)
CANDIDATE_SHA256 = (
    "4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35"
)
ENGINE = ROOT / (
    "_local_generated/analysis_outputs/cynthia_v9_vs_v11_poffin_role_selection_20260713/"
    "seeded_engine"
)
OUTPUT = Path(__file__).with_name("fixed760_rule3_lifecycle_scan.jsonl")
RULE_ID = "SILVER_DECLARED_ULTRA_BALL_TWO_ROUTE_TRANSACTION_REPAIR_V2"
MAX_STEPS = 1000

PANELS = (
    {
        "panel": "historical_silver",
        "games": 100,
        "seed_base": 271828182,
        "opponents": (
            (
                "historical_silver",
                "_local_generated/analysis_outputs/reference_agents/"
                "historical_silver_archaludon_54495224",
            ),
        ),
    },
    {
        "panel": "adjacent_population",
        "games": 40,
        "seed_base": 271958313,
        "opponents": (
            (
                "arch_peak",
                "submission_archaludon_gtmidguard_lucariobev_"
                "crustledeckguard_archattach_ruleinline_20260710",
            ),
            (
                "arch_shumpei",
                "opponents/meta_agents/archaludon_shumpei_current_v3",
            ),
            (
                "alakazam_capbloo_gold",
                "opponents/meta_agents/alakazam_capbloo_gold_85357128_simple",
            ),
            (
                "marnie_kazuki_live",
                "opponents/meta_agents/marnie_kazuki_live_85083586_simple",
            ),
            (
                "mega_lucario_public",
                "opponents/meta_agents/mega_lucario_public_simple",
            ),
            (
                "kang_crustle",
                "opponents/meta_agents/kangaskhan_crustle_mpgaming_v23_"
                "heal_role_missing160_guard",
            ),
            (
                "cynthia_v23",
                "opponents/meta_agents/cynthia_garchomp_nasuo445_v23_"
                "allcall_before_evolve",
            ),
        ),
    },
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def run_game(panel: str, opponent_label: str, opponent: Path, seat: int, seed: int):
    from cg.game import battle_finish, battle_select, battle_start

    directories = (CANDIDATE, opponent) if seat == 0 else (opponent, CANDIDATE)
    agents = [
        load_agent(directory, f"r3_lifecycle_{panel}_{opponent_label}_{seat}_{seed}_{index}")
        for index, directory in enumerate(directories)
    ]
    decks = [read_deck(directory / "deck.csv") for directory in directories]
    random.seed(seed)
    for agent in agents:
        module_random = getattr(getattr(agent, "module", None), "random", None)
        if hasattr(module_random, "seed"):
            module_random.seed(seed)

    obs, start_data = battle_start(decks[0], decks[1], seed=seed)
    if not obs:
        raise AssertionError(
            f"battle did not start: {panel}/{opponent_label}/{seat}/{seed}: "
            f"{start_data.errorPlayer}/{start_data.errorType}"
        )

    events = []
    steps = 0
    final_obs = obs
    try:
        while obs and obs.get("select") and steps < MAX_STEPS:
            current = obs.get("current") or {}
            if current.get("result") not in (None, -1):
                break
            player = int(current.get("yourIndex", 0))
            select = obs.get("select") or {}
            if not select.get("option"):
                break
            action = agents[player](obs)
            if player == seat:
                telemetry = copy.deepcopy(
                    getattr(getattr(agents[player], "module", None), "_last_telemetry", None)
                )
                if isinstance(telemetry, dict) and telemetry.get("rule_id") == RULE_ID:
                    before = telemetry.get("owner_before") or {}
                    after = telemetry.get("owner_after") or {}
                    is_start = (
                        not before
                        and after.get("stage") == "ULTRA_EMITTED"
                        and telemetry.get("selected_source") == RULE_ID
                    )
                    is_terminal = bool(
                        telemetry.get("rule3_completed")
                        or telemetry.get("abort_reason")
                    )
                    if is_start or is_terminal:
                        events.append(
                            {
                                "step": steps,
                                "turn": current.get("turn"),
                                "turn_action_count": current.get("turnActionCount"),
                                "start": is_start,
                                "completed": bool(telemetry.get("rule3_completed")),
                                "abort_reason": telemetry.get("abort_reason"),
                                "abort_stage": telemetry.get("abort_stage"),
                                "irreversible_abort": bool(
                                    telemetry.get("irreversible_abort")
                                ),
                                "irreversible_abort_fault": bool(
                                    telemetry.get("irreversible_abort_fault")
                                ),
                                "route": after.get("route_kind")
                                or before.get("route_kind"),
                                "before_stage": before.get("stage"),
                                "after_stage": after.get("stage"),
                            }
                        )
            obs = battle_select(action)
            final_obs = obs
            steps += 1
    finally:
        battle_finish()

    terminal = (final_obs or {}).get("current") or {}
    starts = sum(event["start"] for event in events)
    completions = sum(event["completed"] for event in events)
    aborts = sum(event["abort_reason"] is not None for event in events)
    return {
        "panel": panel,
        "opponent": opponent_label,
        "seat": seat,
        "seed": seed,
        "steps": steps,
        "result": terminal.get("result"),
        "hit_max_steps": steps >= MAX_STEPS,
        "starts": starts,
        "completions": completions,
        "aborts": aborts,
        "events": events,
    }


def main() -> None:
    if sha256(CANDIDATE / "main.py") != CANDIDATE_SHA256:
        raise AssertionError("candidate hash mismatch")
    ensure_engine_on_path(ENGINE)

    rows = []
    games = 0
    for panel in PANELS:
        for opponent_label, opponent_relative in panel["opponents"]:
            opponent = ROOT / opponent_relative
            for seat in (0, 1):
                for offset in range(panel["games"]):
                    seed = panel["seed_base"] + offset
                    row = run_game(
                        panel["panel"], opponent_label, opponent, seat, seed
                    )
                    games += 1
                    if row["starts"] or row["completions"] or row["aborts"]:
                        rows.append(row)

    OUTPUT.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )
    summary = {
        "games": games,
        "event_games": len(rows),
        "starts": sum(row["starts"] for row in rows),
        "completions": sum(row["completions"] for row in rows),
        "aborts": sum(row["aborts"] for row in rows),
        "irreversible_abort_faults": sum(
            event["irreversible_abort_fault"]
            for row in rows
            for event in row["events"]
        ),
        "max_step_hits": sum(row["hit_max_steps"] for row in rows),
        "output": str(OUTPUT.relative_to(ROOT)),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
