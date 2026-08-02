"""Collect teacher labels on states visited by one complete-action BC actor."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random
import re
import sys
from typing import Any, Mapping

from .frozen_sources import (
    checkpoint_source_hashes,
    find_repo_root,
    latest_source_dir,
    seeded_engine_dir,
    sha256_file,
    verify_frozen_sources,
)


_ACTOR_ID = re.compile(r"[a-z0-9][a-z0-9_]{0,19}")


def _runtime_imports() -> tuple[Any, Any, Any, Any, Any]:
    repo = find_repo_root()
    engine = seeded_engine_dir(repo)
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    if str(engine) not in sys.path:
        sys.path.insert(0, str(engine))
    from cg.game import battle_finish, battle_select, battle_start
    from tools.ptcg_common import load_agent, read_deck

    return battle_start, battle_select, battle_finish, load_agent, read_deck


def _seed_module_random(agent: Any, seed: int) -> None:
    module_random = getattr(getattr(agent, "module", None), "random", None)
    if hasattr(module_random, "seed"):
        module_random.seed(seed)


def _training_row(
    observation: Any,
    decision: Any,
    *,
    episode_index: int,
    catalog: Any,
) -> dict[str, Any]:
    from .complete_action import observation_complete_actions, observation_option_rows
    from .effect_features import extract_effect_features
    from .encoders import encode_action, encode_state
    from .public_state import project_public_state
    from .semantic_action import semantic_options

    projection = project_public_state(observation)
    semantic = semantic_options(observation)
    option_rows = observation_option_rows(observation)
    effects = tuple(
        extract_effect_features(projection, option, catalog) for option in semantic
    )
    state = tuple(encode_state(projection))
    option_vectors = tuple(
        tuple(encode_action(option, feature_set))
        for option, feature_set in zip(semantic, effects)
    )
    candidates = observation_complete_actions(observation)
    target = candidates.candidate_index_for(option_rows, decision.teacher_action)
    if target is None:
        raise ValueError("teacher action is not representable on an actor-visited state")
    selected_types = sorted(
        {str(option_rows[index]["payload"]["option_type"]) for index in decision.teacher_action}
    )
    select = projection.get("select") or {}
    return {
        "episode_index": episode_index,
        "state": state,
        "option_vectors": option_vectors,
        "candidate_members": tuple(
            tuple(candidate.action) for candidate in candidates.candidates
        ),
        "target": target,
        "family": "empty" if not selected_types else "+".join(selected_types),
        "optional": int(select.get("min_count", -1)) == 0,
        "multiple": len(decision.teacher_action) > 1,
        "duplicate_canonical_actions": candidates.duplicate_canonical_action_count,
    }


def _run_episode(
    *,
    episode_index: int,
    episode_id: str,
    opponent_id: str,
    opponent_dir: Path,
    seat: int,
    seed: int,
    model: Any,
    checkpoint_sha256: str,
    catalog: Any,
    max_steps: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], Counter[str]]:
    from .complete_bc_actor import CompleteActionBehaviorCloningPolicy
    from .teacher_adapter import LatestV1Teacher

    battle_start, battle_select, battle_finish, load_agent, read_deck = _runtime_imports()
    policy_deck = read_deck(latest_source_dir() / "deck.csv")
    opponent_deck = read_deck(opponent_dir / "deck.csv")
    decks = (
        (policy_deck, opponent_deck)
        if seat == 0
        else (opponent_deck, policy_deck)
    )
    random.seed(seed)
    opponent = load_agent(
        opponent_dir,
        f"_d1_opp_{episode_index}_{random.randrange(1 << 30)}",
    )
    _seed_module_random(opponent, seed)
    teacher = LatestV1Teacher(game_id=episode_id, seat=seat)
    policy = CompleteActionBehaviorCloningPolicy(
        teacher,
        model=model,
        checkpoint_sha256=checkpoint_sha256,
        catalog=catalog,
    )
    rows: list[dict[str, Any]] = []
    telemetry: Counter[str] = Counter()
    started = False
    steps = 0
    try:
        observation, start_data = battle_start(*decks, seed=seed)
        if not observation:
            raise RuntimeError(
                "checked engine failed to start battle: "
                f"{getattr(start_data, 'errorPlayer', None)}/"
                f"{getattr(start_data, 'errorType', None)}"
            )
        started = True
        while observation.get("select") and steps < max_steps:
            current = observation.get("current") or {}
            result = current.get("result")
            if result not in (None, -1):
                break
            player = int(current.get("yourIndex", 0))
            if player == seat:
                decision = policy.decide(observation)
                rows.append(
                    _training_row(
                        observation,
                        decision,
                        episode_index=episode_index,
                        catalog=catalog,
                    )
                )
                if decision.fallback_used:
                    telemetry["fallback_count"] += 1
                if decision.representability_failure:
                    telemetry["representability_failure_count"] += 1
                if decision.model_failure_kind is not None:
                    telemetry["model_failure_count"] += 1
                if decision.model_timeout:
                    telemetry["model_timeout_count"] += 1
                action = list(decision.action)
            else:
                action = opponent(observation)
            observation = battle_select(action)
            steps += 1
        current = (observation or {}).get("current") or {}
        result = current.get("result")
        max_step_hit = steps >= max_steps and result not in (0, 1, 2)
        if result not in (0, 1, 2) or max_step_hit:
            raise RuntimeError("DAgger episode did not reach a clean terminal result")
        episode = {
            "episode_id": episode_id,
            "opponent_id": opponent_id,
            "seat": seat,
            "seed": seed,
            "split": "train",
            "terminal_result": int(result),
            "action_errors": 0,
            "max_step_hit": False,
            "engine_steps": steps,
            "decision_count": len(rows),
        }
        return episode, rows, telemetry
    finally:
        if started:
            battle_finish()


def collect(args: argparse.Namespace) -> dict[str, Any]:
    if not _ACTOR_ID.fullmatch(args.actor_id):
        raise ValueError("actor-id must be short lowercase snake_case")
    if args.episodes_per_seat <= 0 or args.max_steps <= 0:
        raise ValueError("DAgger schedule values must be positive")
    output = args.output.resolve()
    report_path = args.report.resolve()
    if output.exists() or report_path.exists():
        raise FileExistsError("DAgger actor output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    from .runtime_contract import configure_single_thread_runtime

    configure_single_thread_runtime()
    from .catalog import catalog_from_cg
    from .complete_bc_dataset_ops import payload_from_dagger_rows
    from .model import load_checkpoint, sha256_checkpoint
    from .trajectory import load_opponent_population_spec
    import torch

    verification = verify_frozen_sources()
    repo = find_repo_root().resolve()
    population_receipt, opponent_table = load_opponent_population_spec(
        args.opponent_population,
        repo_root=repo,
    )
    checkpoint_path = args.checkpoint.resolve()
    checkpoint_sha = sha256_checkpoint(checkpoint_path)
    if args.expected_checkpoint_sha256 and (
        checkpoint_sha != args.expected_checkpoint_sha256.upper()
    ):
        raise ValueError("DAgger actor checkpoint SHA256 does not match the fixed input")
    model, metadata, _ = load_checkpoint(
        checkpoint_path,
        expected_source_hashes=checkpoint_source_hashes(),
        device="cpu",
    )
    training = metadata.get("training") or {}
    if training.get("algorithm") != "complete_legal_action_behavior_cloning":
        raise ValueError("DAgger input is not a complete-action BC checkpoint")
    model.eval()
    _runtime_imports()
    from cg import api as cg_api

    catalog = catalog_from_cg(cg_api)
    episodes: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    telemetry: Counter[str] = Counter()
    schedule_count = len(opponent_table) * 2 * args.episodes_per_seat
    for opponent_index, opponent in enumerate(opponent_table):
        opponent_id = str(opponent["id"])
        opponent_dir = repo.joinpath(*Path(str(opponent["path"])).parts)
        for seat in (0, 1):
            for game in range(args.episodes_per_seat):
                seed = args.seed_base + game
                episode_index = len(episodes)
                episode_id = (
                    f"d1_{args.actor_id}_o{opponent_index}_s{seat}_g{game:03d}"
                )
                episode, episode_rows, episode_telemetry = _run_episode(
                    episode_index=episode_index,
                    episode_id=episode_id,
                    opponent_id=opponent_id,
                    opponent_dir=opponent_dir,
                    seat=seat,
                    seed=seed,
                    model=model,
                    checkpoint_sha256=checkpoint_sha,
                    catalog=catalog,
                    max_steps=args.max_steps,
                )
                episodes.append(episode)
                rows.extend(episode_rows)
                telemetry.update(episode_telemetry)
                if len(episodes) % args.progress_every == 0 or len(episodes) == schedule_count:
                    print(
                        json.dumps(
                            {
                                "actor_id": args.actor_id,
                                "progress": len(episodes),
                                "total": schedule_count,
                                "decisions": len(rows),
                            }
                        ),
                        flush=True,
                    )
    if sha256_checkpoint(checkpoint_path) != checkpoint_sha:
        raise ValueError("DAgger actor checkpoint changed during collection")
    if telemetry["representability_failure_count"]:
        raise ValueError("DAgger collection encountered representability failures")
    payload = payload_from_dagger_rows(
        episodes=episodes,
        rows=rows,
        source={
            "kind": "complete-action-bc-actor-visited-teacher-labels",
            "dagger_round": 1,
            "actor_id": args.actor_id,
            "actor_checkpoint": str(checkpoint_path),
            "actor_checkpoint_sha256": checkpoint_sha,
            "opponent_population": population_receipt,
            "seed_base": args.seed_base,
            "episodes_per_seat": args.episodes_per_seat,
            "engine_runtime_manifest_sha256": verification[
                "engine_runtime_manifest_sha256"
            ],
            "teacher_labels": True,
            "actor_actions_executed": True,
        },
    )
    torch.save(payload, output)
    report = {
        "schema_version": "complete-action-bc-dagger-collection-report-v1",
        "actor_id": args.actor_id,
        "checkpoint_sha256": checkpoint_sha,
        "dataset": str(output),
        "dataset_sha256": sha256_file(output),
        "dataset_bytes": output.stat().st_size,
        "counts": payload["counts"],
        "telemetry": dict(sorted(telemetry.items())),
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--expected-checkpoint-sha256", default="")
    parser.add_argument("--actor-id", required=True)
    parser.add_argument("--opponent-population", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seed-base", type=int, required=True)
    parser.add_argument("--episodes-per-seat", type=int, default=20)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--progress-every", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    collect(build_parser().parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
