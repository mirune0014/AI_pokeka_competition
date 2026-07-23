from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from ptcg_common import ensure_engine_on_path, load_agent, read_deck
from rl_ptcg.canonical_actions import canonicalize_prompt_action
from rl_ptcg.label_replay_rollout import replay_decisions, target_seat_for_deck


def enum_name(enum_type: Any, value: Any) -> str:
    try:
        return str(enum_type(value).name)
    except (TypeError, ValueError):
        return str(value)


def selection_label(selection: dict[str, Any], option_type: Any) -> str:
    action_type = enum_name(option_type, selection.get("action_type"))
    fields = []
    for key in (
        "source_card_id",
        "target_card_id",
        "attack_id",
        "number",
        "count",
        "source_zone",
        "target_zone",
        "source_relation",
        "target_relation",
    ):
        value = selection.get(key)
        if value is not None:
            fields.append(f"{key}={value}")
    return action_type if not fields else f"{action_type}({','.join(fields)})"


def action_label(action: dict[str, Any], option_type: Any) -> str:
    selections = action.get("selections") or []
    if not selections:
        return "EMPTY"
    return " + ".join(selection_label(item, option_type) for item in selections)


def action_family(action: dict[str, Any], option_type: Any) -> str:
    selections = action.get("selections") or []
    if not selections:
        return "EMPTY"
    return "+".join(
        enum_name(option_type, item.get("action_type")) for item in selections
    )


def semantic_phase(context: str, recorded_family: str) -> str:
    if context in {
        "IS_FIRST",
        "MULLIGAN",
        "SETUP_ACTIVE_POKEMON",
        "SETUP_BENCH_POKEMON",
    }:
        return "setup"
    if context == "TO_PRIZE":
        return "prize_selection"
    if context in {"EVOLVES_FROM", "EVOLVES_TO", "EVOLVE", "DEVOLVE"} or (
        "EVOLVE" in recorded_family
    ):
        return "evolve"
    if context == "ATTACK" or "ATTACK" in recorded_family:
        return "attack"
    if context in {"TO_HAND", "LOOK"}:
        return "search_selection"
    if context == "MAIN":
        if "ABILITY" in recorded_family:
            return "main_ability"
        if "PLAY" in recorded_family:
            return "main_play"
        if "ATTACH" in recorded_family:
            return "main_attach"
        if "RETREAT" in recorded_family:
            return "main_retreat"
        if "END" in recorded_family:
            return "main_end"
        return "main_other"
    return "effect_selection"


def turn_band(turn: Any) -> str:
    try:
        value = int(turn)
    except (TypeError, ValueError):
        return "unknown"
    if value <= 3:
        return "early"
    if value <= 8:
        return "mid"
    return "late"


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate semantic action mismatches between replay policy and an agent."
    )
    parser.add_argument("replays", type=Path, nargs="+")
    parser.add_argument("--engine-dir", type=Path, required=True)
    parser.add_argument("--agent-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target-team")
    args = parser.parse_args()

    ensure_engine_on_path(args.engine_dir)
    from cg.api import OptionType as EngineOptionType
    from cg.api import SelectContext as EngineSelectContext

    agent = load_agent(args.agent_dir, "replay_policy_mismatch_audit")
    deck = read_deck(args.agent_dir / "deck.csv")
    option_type = getattr(agent.module, "OptionType", EngineOptionType)
    select_context = getattr(agent.module, "SelectContext", EngineSelectContext)

    decision_rows: list[dict[str, Any]] = []
    mismatch_rows: list[dict[str, Any]] = []
    episode_rows: list[dict[str, Any]] = []
    for replay_path in args.replays:
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
        teams = (replay.get("info") or {}).get("TeamNames") or []
        if args.target_team:
            matches = [index for index, name in enumerate(teams) if name == args.target_team]
            if len(matches) != 1:
                raise ValueError(f"{replay_path}: target team is not unique")
            target_seat = matches[0]
        else:
            target_seat = target_seat_for_deck(replay, deck)

        rewards = replay.get("rewards") or []
        reward = rewards[target_seat] if target_seat < len(rewards) else None
        decisions = 0
        mismatches = 0
        for replay_step, observation, recorded_action in replay_decisions(replay, target_seat):
            decisions += 1
            agent_action = agent(observation)
            recorded = canonicalize_prompt_action(observation, recorded_action).to_dict()
            chosen = canonicalize_prompt_action(observation, agent_action).to_dict()
            current = observation.get("current") or {}
            select = observation.get("select") or {}
            context = enum_name(select_context, select.get("context"))
            recorded_label = action_label(recorded, option_type)
            agent_label = action_label(chosen, option_type)
            recorded_family = action_family(recorded, option_type)
            agent_family = action_family(chosen, option_type)
            row = {
                "episode_id": str(
                    (replay.get("info") or {}).get("EpisodeId", replay_path.stem)
                ),
                "replay": str(replay_path),
                "seat": target_seat,
                "reward": reward,
                "replay_step": replay_step,
                "turn": current.get("turn"),
                "turn_band": turn_band(current.get("turn")),
                "context": context,
                "semantic_phase": semantic_phase(context, recorded_family),
                "matched": recorded == chosen,
                "recorded_family": recorded_family,
                "agent_family": agent_family,
                "recorded_action": recorded_label,
                "agent_action": agent_label,
                "pair": f"{agent_label} -> {recorded_label}",
            }
            decision_rows.append(row)
            if row["matched"]:
                continue
            mismatches += 1
            mismatch_rows.append(row)
        episode_rows.append(
            {
                "episode_id": str((replay.get("info") or {}).get("EpisodeId", replay_path.stem)),
                "replay": str(replay_path),
                "seat": target_seat,
                "reward": reward,
                "decisions": decisions,
                "mismatches": mismatches,
                "agreement_rate": 0.0 if not decisions else (decisions - mismatches) / decisions,
            }
        )

    pair_counts = Counter(row["pair"] for row in mismatch_rows)
    recorded_counts = Counter(row["recorded_action"] for row in mismatch_rows)
    agent_counts = Counter(row["agent_action"] for row in mismatch_rows)
    context_counts = Counter(row["context"] for row in mismatch_rows)
    turn_counts = Counter(row["turn_band"] for row in mismatch_rows)
    pair_rows = [
        {"count": count, "pair": pair}
        for pair, count in sorted(pair_counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    output = args.output_dir
    decision_fields = [
        "episode_id",
        "replay",
        "seat",
        "reward",
        "replay_step",
        "turn",
        "turn_band",
        "context",
        "semantic_phase",
        "matched",
        "recorded_family",
        "agent_family",
        "recorded_action",
        "agent_action",
        "pair",
    ]
    write_csv(output / "decisions.csv", decision_rows, decision_fields)
    write_csv(
        output / "mismatches.csv",
        mismatch_rows,
        decision_fields,
    )
    write_csv(output / "mismatch_pairs.csv", pair_rows, ["count", "pair"])
    write_csv(
        output / "episodes.csv",
        episode_rows,
        ["episode_id", "replay", "seat", "reward", "decisions", "mismatches", "agreement_rate"],
    )

    total_decisions = sum(row["decisions"] for row in episode_rows)
    phase_decisions = Counter(row["semantic_phase"] for row in decision_rows)
    phase_mismatches = Counter(row["semantic_phase"] for row in mismatch_rows)
    phase_agreement = {
        phase: {
            "decisions": count,
            "mismatches": phase_mismatches.get(phase, 0),
            "agreement_rate": (count - phase_mismatches.get(phase, 0)) / count,
        }
        for phase, count in sorted(phase_decisions.items())
    }
    report = {
        "agent_dir": str(args.agent_dir),
        "episodes": len(episode_rows),
        "decisions": total_decisions,
        "mismatches": len(mismatch_rows),
        "agreement_rate": 0.0
        if not total_decisions
        else (total_decisions - len(mismatch_rows)) / total_decisions,
        "pair_counts": dict(pair_counts.most_common()),
        "recorded_action_counts": dict(recorded_counts.most_common()),
        "agent_action_counts": dict(agent_counts.most_common()),
        "context_counts": dict(context_counts.most_common()),
        "turn_band_counts": dict(turn_counts.most_common()),
        "semantic_phase_agreement": phase_agreement,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
