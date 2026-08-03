from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "infrastructure" / "tools")]
from research.rl_ptcg.label_replay_rollout import replay_decisions


HERE = Path(__file__).resolve().parent
GOLD = ROOT / "autonomous_gold_20260715"
CANDIDATE = (
    GOLD
    / "candidates"
    / "archaludon_integrated_public_turn_plan_transaction_v1"
)
PARENT = (
    GOLD
    / "candidates"
    / "archaludon_general_visible_counterattack_ready_rotation_v1"
)
SOURCE = GOLD / "live" / "55120278" / "prewrite_20260731_1235"
EPISODE_CSV = SOURCE / "submission_55120278_20260731_1235_episodes.csv"
EXPECTED_CANDIDATE_SHA256 = (
    "3E23CC048CF87E148ACA3E7B017B5B3AAA8C422BD1580BF553222CA79BB466A2"
)
EXPECTED_PARENT_SHA256 = (
    "AC70708082882C7BA01CFBF81D29F534B95166DFF6BAD11E1EF1FA001A5F79D2"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reset(module, directory: Path) -> None:
    previous = Path.cwd()
    try:
        os.chdir(directory)
        deck = module.agent(
            {"select": None, "logs": [], "current": None, "search_begin_input": None}
        )
    finally:
        os.chdir(previous)
    assert isinstance(deck, list) and len(deck) == 60
    module.drain_cumulative_telemetry()


def valid(obs, action) -> bool:
    return (
        isinstance(action, list)
        and obs.select.minCount <= len(action) <= obs.select.maxCount
        and len(action) == len(set(action))
        and all(
            isinstance(position, int) and 0 <= position < len(obs.select.option)
            for position in action
        )
    )


def semantic(module, obs, action):
    return [
        {
            "type": int(obs.select.option[position].type),
            "context": int(obs.select.context),
            "card_id": getattr(
                module.option_card(obs, obs.select.option[position]), "id", None
            ),
            "serial": getattr(
                module.option_card(obs, obs.select.option[position]), "serial", None
            ),
            "target_id": getattr(
                module.option_target(obs, obs.select.option[position]), "id", None
            ),
            "target_serial": getattr(
                module.option_target(obs, obs.select.option[position]), "serial", None
            ),
            "attack_id": getattr(obs.select.option[position], "attackId", None),
        }
        for position in action
    ]


def replay_seat(replay: dict) -> int:
    seats = [
        index
        for index, name in enumerate((replay.get("info") or {}).get("TeamNames", []))
        if name == "rurumi"
    ]
    assert len(seats) == 1, seats
    return seats[0]


def load_public_episode_ids() -> list[int]:
    with EPISODE_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    public_ids = [
        int(row["episode_id"])
        for row in rows
        if row["type"] == "EPISODE_TYPE_PUBLIC"
    ]
    # The fetched table contains 50 rows: 49 public ladder games plus one
    # validation self-play.  Only public games have one unambiguous rurumi seat.
    assert len(public_ids) == 49
    assert len(set(public_ids)) == len(public_ids)
    assert all((SOURCE / f"episode_{episode_id}_replay.json").is_file() for episode_id in public_ids)
    return public_ids


def ablated_semantic(
    episode_id: int,
    stop_step: int,
    disabled_rule: str,
):
    module = load(f"latest50_ablation_{episode_id}", CANDIDATE / "main.py")
    replay_path = SOURCE / f"episode_{episode_id}_replay.json"
    replay = json.loads(replay_path.read_text(encoding="utf-8-sig"))
    reset(module, CANDIDATE)
    module._cum_diagnostic_disabled_rules = frozenset({disabled_rule})
    for step, raw, _recorded in replay_decisions(replay, replay_seat(replay)):
        action = module.agent(copy.deepcopy(raw))
        telemetry = module.drain_cumulative_telemetry()
        assert len(telemetry) == 1
        if step == stop_step:
            obs = module.to_observation_class(copy.deepcopy(raw))
            assert valid(obs, action)
            return semantic(module, obs, action)
    raise AssertionError((episode_id, stop_step))


def main() -> None:
    assert sha256(CANDIDATE / "main.py") == EXPECTED_CANDIDATE_SHA256
    assert sha256(PARENT / "main.py") == EXPECTED_PARENT_SHA256
    episode_ids = load_public_episode_ids()
    candidate = load("latest50_candidate", CANDIDATE / "main.py")
    parent = load("latest50_parent", PARENT / "main.py")
    rows = []
    total_callbacks = total_differences = 0
    action_errors = exceptions = telemetry_errors = 0

    for episode_id in episode_ids:
        replay_path = SOURCE / f"episode_{episode_id}_replay.json"
        replay = json.loads(replay_path.read_text(encoding="utf-8-sig"))
        seat = replay_seat(replay)
        reset(candidate, CANDIDATE)
        reset(parent, PARENT)
        differences = []
        callbacks = 0
        episode_errors = []
        try:
            for step, raw, recorded in replay_decisions(replay, seat):
                callbacks += 1
                parent_action = parent.agent(copy.deepcopy(raw))
                candidate_action = candidate.agent(copy.deepcopy(raw))
                pending = candidate.drain_cumulative_telemetry()
                parent.drain_cumulative_telemetry()
                if len(pending) != 1:
                    telemetry_errors += 1
                    episode_errors.append(
                        {"step": step, "kind": "telemetry", "count": len(pending)}
                    )
                    continue
                telemetry = pending[0]
                candidate_obs = candidate.to_observation_class(copy.deepcopy(raw))
                parent_obs = parent.to_observation_class(copy.deepcopy(raw))
                if not (
                    valid(candidate_obs, recorded)
                    and valid(candidate_obs, candidate_action)
                    and valid(parent_obs, parent_action)
                ):
                    action_errors += 1
                    episode_errors.append({"step": step, "kind": "invalid_action"})
                    continue
                parent_semantic = semantic(parent, parent_obs, parent_action)
                candidate_semantic = semantic(candidate, candidate_obs, candidate_action)
                if candidate_semantic != parent_semantic:
                    differences.append(
                        {
                            "step": step,
                            "winner": telemetry.get("winning_rule_id"),
                            "rank": telemetry.get("rank"),
                            "owner": telemetry.get("attribution_owner"),
                            "candidate": candidate_semantic,
                            "parent": parent_semantic,
                            "recorded": semantic(candidate, candidate_obs, recorded),
                        }
                    )
        except Exception as exc:
            exceptions += 1
            episode_errors.append(
                {"kind": "exception", "type": type(exc).__name__, "message": str(exc)}
            )

        first = differences[0] if differences else None
        ablation = None
        if first is not None:
            disabled_rule = first["winner"]
            assert isinstance(disabled_rule, str) and disabled_rule
            disabled_semantic = ablated_semantic(
                episode_id, int(first["step"]), disabled_rule
            )
            ablation = {
                "disabled_rule": disabled_rule,
                "matches_parent": disabled_semantic == first["parent"],
                "action": disabled_semantic,
            }
            assert ablation["matches_parent"]
        rows.append(
            {
                "episode_id": episode_id,
                "seat": seat,
                "replay_sha256": sha256(replay_path),
                "callbacks": callbacks,
                "difference_count": len(differences),
                "first_difference": first,
                "ablation": ablation,
                "errors": episode_errors,
                "differences": differences,
            }
        )
        total_callbacks += callbacks
        total_differences += len(differences)

    report = {
        "candidate_main_sha256": sha256(CANDIDATE / "main.py"),
        "parent_main_sha256": sha256(PARENT / "main.py"),
        "deck_sha256": sha256(CANDIDATE / "deck.csv"),
        "episode_csv_sha256": sha256(EPISODE_CSV),
        "episode_count": len(rows),
        "callback_count": total_callbacks,
        "difference_count": total_differences,
        "action_errors": action_errors,
        "exceptions": exceptions,
        "telemetry_errors": telemetry_errors,
        "episodes": rows,
    }
    output = HERE / "latest50_shadow.json"
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "episode_count",
                    "callback_count",
                    "difference_count",
                    "action_errors",
                    "exceptions",
                    "telemetry_errors",
                )
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
