from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "infrastructure" / "tools"))

from ptcg_common import ensure_engine_on_path, load_agent, read_deck


CANDIDATE_SHA256 = (
    "4287A616E1611F5697964D9F4065978EED1CEA72CDB48C9F63F1430D69106C35"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--opponent", type=Path, required=True)
    parser.add_argument("--candidate-seat", type=int, choices=(0, 1), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-steps", type=int, default=1000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidate = args.candidate.resolve()
    opponent = args.opponent.resolve()
    if sha256(candidate / "main.py") != CANDIDATE_SHA256:
        raise AssertionError("candidate hash mismatch")

    ensure_engine_on_path(args.engine_dir.resolve())
    from cg.game import battle_finish, battle_select, battle_start

    directories = (
        (candidate, opponent)
        if args.candidate_seat == 0
        else (opponent, candidate)
    )
    agents = [
        load_agent(directory, f"telemetry_agent_{seat}")
        for seat, directory in enumerate(directories)
    ]
    decks = [read_deck(directory / "deck.csv") for directory in directories]
    random.seed(args.seed)
    for agent in agents:
        module_random = getattr(getattr(agent, "module", None), "random", None)
        if hasattr(module_random, "seed"):
            module_random.seed(args.seed)

    obs, start_data = battle_start(decks[0], decks[1], seed=args.seed)
    if not obs:
        raise AssertionError(
            f"battle did not start: {start_data.errorPlayer}/{start_data.errorType}"
        )

    rows: list[dict] = []
    steps = 0
    final_obs = obs
    try:
        while obs and obs.get("select") and steps < args.max_steps:
            current = obs.get("current") or {}
            if current.get("result") not in (None, -1):
                break
            player = int(current.get("yourIndex", 0))
            select = obs.get("select") or {}
            if not select.get("option"):
                break
            action = agents[player](obs)
            if player == args.candidate_seat:
                module = getattr(agents[player], "module", None)
                rows.append(
                    {
                        "step": steps,
                        "turn": current.get("turn"),
                        "turn_action_count": current.get("turnActionCount"),
                        "context": select.get("context"),
                        "action": list(action),
                        "telemetry": copy.deepcopy(
                            getattr(module, "_last_telemetry", None)
                        ),
                    }
                )
            obs = battle_select(action)
            final_obs = obs
            steps += 1
    finally:
        battle_finish()

    terminal = (final_obs or {}).get("current") or {}
    summary = {
        "seed": args.seed,
        "candidate_seat": args.candidate_seat,
        "steps": steps,
        "hit_max_steps": steps >= args.max_steps,
        "result": terminal.get("result"),
        "rule3_selected_callbacks": sum(
            1
            for row in rows
            if isinstance(row.get("telemetry"), dict)
            and row["telemetry"].get("rule_id")
            == "SILVER_DECLARED_ULTRA_BALL_TWO_ROUTE_TRANSACTION_REPAIR_V2"
        ),
        "rule3_completions": sum(
            1
            for row in rows
            if isinstance(row.get("telemetry"), dict)
            and row["telemetry"].get("rule3_completed") is True
        ),
        "irreversible_abort_faults": sum(
            1
            for row in rows
            if isinstance(row.get("telemetry"), dict)
            and row["telemetry"].get("irreversible_abort_fault") is True
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
