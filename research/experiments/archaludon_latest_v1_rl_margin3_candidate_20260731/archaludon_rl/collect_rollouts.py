"""Collect deterministic, on-policy training episodes with the checked engine.

This is a training-data runner, not a strength evaluator.  Promotion evidence
continues to use the repository's checked paired evaluation runner.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import re
import sys
from typing import Any, Mapping

from .catalog import catalog_from_cg
from .collector import EpisodeCollector, validate_duplicate_pair
from .frozen_sources import (
    checkpoint_source_hashes,
    find_repo_root,
    latest_source_dir,
    seeded_engine_dir,
    sha256_file,
    verify_frozen_sources,
)
from .model import load_checkpoint, sha256_checkpoint
from .policy import MODEL_TIMEOUT_SECONDS, PolicyConfig, ResidualPolicy
from .teacher_adapter import LatestV1Teacher
from .trajectory import (
    EpisodeBuilder,
    RunManifest,
    load_opponent_population_spec,
    publish_clean_episode,
    record_failure,
)

_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")


def _ensure_runtime_imports() -> tuple[Any, Any, Any, Any]:
    repo = find_repo_root()
    engine = seeded_engine_dir(repo)
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    if str(engine) not in sys.path:
        sys.path.insert(0, str(engine))
    from cg.game import battle_finish, battle_select, battle_start
    from infrastructure.tools.ptcg_common import load_agent, read_deck

    return battle_start, battle_select, battle_finish, (load_agent, read_deck)


def _seed_module_random(agent: Any, seed: int) -> None:
    module_random = getattr(getattr(agent, "module", None), "random", None)
    if hasattr(module_random, "seed"):
        module_random.seed(seed)


def _run_episode(
    *,
    run_id: str,
    episode_id: str,
    opponent_id: str,
    seat: int,
    seed: int,
    checkpoint_sha256: str,
    reference_prior_receipt: Mapping[str, Any],
    reference_prior_schema_sha256: str,
    collection_spec_sha256: str,
    schedule_sha256: str,
    model: Any,
    catalog: Any,
    opponent_dir: Path,
    output_path: Path,
    failures_ledger: Path,
    max_steps: int,
    timeout_seconds: float,
) -> Mapping[str, Any]:
    battle_start, battle_select, battle_finish, helpers = _ensure_runtime_imports()
    load_agent, read_deck = helpers
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
        f"_archaludon_rl_opponent_{episode_id}_{random.randrange(1 << 30)}",
    )
    _seed_module_random(opponent, seed)
    teacher = LatestV1Teacher(game_id=episode_id, seat=seat)
    policy = ResidualPolicy(
        teacher,
        model=model,
        checkpoint_sha256=checkpoint_sha256,
        catalog=catalog,
        config=PolicyConfig(
            mode="training",
            model_timeout_seconds=timeout_seconds,
        ),
        rng=random.Random(seed ^ 0xA5A55A5A),
    )
    builder = EpisodeBuilder(
        run_id=run_id,
        episode_id=episode_id,
        opponent_id=opponent_id,
        seat=seat,
        seed=seed,
        source_hashes=checkpoint_source_hashes(),
        checkpoint_sha256=checkpoint_sha256,
        reference_prior_receipt=reference_prior_receipt,
        reference_prior_schema_sha256=reference_prior_schema_sha256,
        collection_spec_sha256=collection_spec_sha256,
        schedule_sha256=schedule_sha256,
        mode="training",
    )
    collector = EpisodeCollector(
        policy=policy,
        builder=builder,
        output_path=output_path,
        failures_ledger=failures_ledger,
    )
    started = False
    observation: Mapping[str, Any] | None = None
    steps = 0
    try:
        observation, start_data = battle_start(*decks, seed=seed)
        if not observation:
            record_failure(
                failures_ledger,
                episode_id=episode_id,
                reason="battle_start_failed",
                details={
                    "error_player": getattr(start_data, "errorPlayer", None),
                    "error_type": getattr(start_data, "errorType", None),
                },
            )
            raise RuntimeError("checked engine failed to start battle")
        started = True
        while observation.get("select") and steps < max_steps:
            current = observation.get("current") or {}
            result = current.get("result")
            if result not in (None, -1):
                break
            player = int(current.get("yourIndex", 0))
            action = (
                collector.callback(observation)
                if player == seat
                else opponent(observation)
            )
            observation = battle_select(action)
            steps += 1
        final_current = (observation or {}).get("current") or {}
        result = final_current.get("result")
        max_step_hit = steps >= max_steps and result not in (0, 1, 2)
        episode = collector.terminal(
            int(result) if result in (0, 1, 2) else -1,
            max_step_hit=max_step_hit,
            terminal_observation=observation,
        )
        if not episode.get("clean_terminal"):
            raise RuntimeError("episode did not reach a clean terminal result")
        return episode
    except Exception as exc:
        record_failure(
            failures_ledger,
            episode_id=episode_id,
            reason="episode_exception",
            details={"type": type(exc).__name__, "message": str(exc), "steps": steps},
        )
        raise
    finally:
        if started:
            battle_finish()


def collect(args: argparse.Namespace) -> dict[str, Any]:
    if not _RUN_ID_PATTERN.fullmatch(args.run_id):
        raise ValueError(
            "run-id must match [A-Za-z0-9][A-Za-z0-9._-]{0,79}"
        )
    if args.timeout_seconds != MODEL_TIMEOUT_SECONDS:
        raise ValueError(
            "Phase 0 collection must use the deployment timeout "
            f"{MODEL_TIMEOUT_SECONDS:.3f}s"
        )
    verification = verify_frozen_sources()
    repo = find_repo_root().resolve()
    population_receipt, opponent_table = load_opponent_population_spec(
        args.opponent_population,
        repo_root=repo,
    )
    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(
            f"collection output directory is not empty: {output_dir}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.checkpoint.resolve()
    checkpoint_hash = sha256_checkpoint(checkpoint_path)
    expected_sources = checkpoint_source_hashes()
    model, metadata, _ = load_checkpoint(
        checkpoint_path,
        expected_source_hashes=expected_sources,
        device=args.device,
    )
    if metadata.get("source_hashes") != expected_sources:
        raise ValueError("checkpoint is not bound to the checked teacher/engine")
    reference_prior_receipt = dict(metadata["reference_prior_receipt"])
    reference_prior_schema_sha256 = str(
        metadata["reference_prior_schema_sha256"]
    )
    _ensure_runtime_imports()
    from cg import api as cg_api

    catalog = catalog_from_cg(cg_api)
    seats = (0, 1) if args.seat == "both" else (int(args.seat),)
    schedule_rows: list[dict[str, Any]] = []
    opponent_dirs: dict[str, Path] = {}
    for opponent_row in opponent_table:
        opponent_id = opponent_row["id"]
        opponent_dirs[opponent_id] = repo.joinpath(
            *Path(opponent_row["path"]).parts
        )
        for seat in seats:
            for game in range(args.episodes_per_seat):
                seed = args.seed_base + game
                episode_id = (
                    f"{args.run_id}_opponent_{opponent_id}_seat{seat}_seed{seed}"
                )
                schedule_rows.append(
                    {
                        "episode_id": episode_id,
                        "opponent_id": opponent_id,
                        "seat": seat,
                        "seed": seed,
                        "game": game,
                        "replicas": 2 if args.duplicate_audit else 1,
                    }
                )
    schedule = tuple(schedule_rows)
    manifest = RunManifest.create(
        run_id=args.run_id,
        source_hashes=expected_sources,
        checkpoint_sha256=checkpoint_hash,
        reference_prior_receipt=reference_prior_receipt,
        reference_prior_schema_sha256=reference_prior_schema_sha256,
        engine_receipt={
            "runtime_manifest_sha256": verification[
                "engine_runtime_manifest_sha256"
            ],
            "cg_api_path": str(Path(cg_api.__file__).resolve()),
            "cg_api_sha256": sha256_file(Path(cg_api.__file__).resolve()),
        },
        mode="training",
        duplicate_mode=args.duplicate_audit,
        schedule=schedule,
        opponent_population_receipt=population_receipt,
        opponent_table=opponent_table,
        command=tuple(sys.argv),
    )
    failures = output_dir / "failures.json"
    published: list[dict[str, Any]] = []
    for row in schedule:
        opponent_id = str(row["opponent_id"])
        opponent_dir = opponent_dirs[opponent_id]
        seat = int(row["seat"])
        seed = int(row["seed"])
        base_id = str(row["episode_id"])
        if args.duplicate_audit:
            first = _run_episode(
                run_id=args.run_id,
                episode_id=f"{base_id}_audit_a",
                opponent_id=opponent_id,
                seat=seat,
                seed=seed,
                checkpoint_sha256=checkpoint_hash,
                reference_prior_receipt=reference_prior_receipt,
                reference_prior_schema_sha256=reference_prior_schema_sha256,
                collection_spec_sha256=manifest.collection_spec_sha256,
                schedule_sha256=manifest.schedule_sha256,
                model=model,
                catalog=catalog,
                opponent_dir=opponent_dir,
                output_path=output_dir / "audit" / f"{base_id}_a.json",
                failures_ledger=failures,
                max_steps=args.max_steps,
                timeout_seconds=args.timeout_seconds,
            )
            second = _run_episode(
                run_id=args.run_id,
                episode_id=f"{base_id}_audit_b",
                opponent_id=opponent_id,
                seat=seat,
                seed=seed,
                checkpoint_sha256=checkpoint_hash,
                reference_prior_receipt=reference_prior_receipt,
                reference_prior_schema_sha256=reference_prior_schema_sha256,
                collection_spec_sha256=manifest.collection_spec_sha256,
                schedule_sha256=manifest.schedule_sha256,
                model=model,
                catalog=catalog,
                opponent_dir=opponent_dir,
                output_path=output_dir / "audit" / f"{base_id}_b.json",
                failures_ledger=failures,
                max_steps=args.max_steps,
                timeout_seconds=args.timeout_seconds,
            )
            duplicate = validate_duplicate_pair(first, second)
            if (
                first.get("terminal_result") != second.get("terminal_result")
                or first.get("clean_terminal") != second.get("clean_terminal")
            ):
                raise ValueError("A/B duplicate terminal outcomes differ")
            final_path = output_dir / "episodes" / f"{base_id}.json"
            final_episode = dict(first)
            final_episode["episode_id"] = base_id
            final_episode["duplicate_audit"] = duplicate
            publish_clean_episode(final_path, final_episode)
            episode_hash = sha256_file(final_path)
        else:
            final_path = output_dir / "episodes" / f"{base_id}.json"
            episode = _run_episode(
                run_id=args.run_id,
                episode_id=base_id,
                opponent_id=opponent_id,
                seat=seat,
                seed=seed,
                checkpoint_sha256=checkpoint_hash,
                reference_prior_receipt=reference_prior_receipt,
                reference_prior_schema_sha256=reference_prior_schema_sha256,
                collection_spec_sha256=manifest.collection_spec_sha256,
                schedule_sha256=manifest.schedule_sha256,
                model=model,
                catalog=catalog,
                opponent_dir=opponent_dir,
                output_path=final_path,
                failures_ledger=failures,
                max_steps=args.max_steps,
                timeout_seconds=args.timeout_seconds,
            )
            episode_hash = sha256_file(final_path)
        published.append(
            {
                "run_id": args.run_id,
                "episode_id": base_id,
                "opponent_id": opponent_id,
                "path": final_path.relative_to(output_dir).as_posix(),
                "bytes": final_path.stat().st_size,
                "sha256": episode_hash,
                "seat": seat,
                "seed": seed,
            }
        )
    manifest = manifest.finalize(tuple(published))
    manifest_path = output_dir / "run_manifest.json"
    manifest.write(manifest_path)
    report = {
        "run_id": args.run_id,
        "checkpoint_sha256": checkpoint_hash,
        "schedule_count": len(schedule),
        "published_count": len(published),
        "opponent_count": len(opponent_table),
        "opponent_population_sha256": population_receipt["sha256"],
        "duplicate_audit": args.duplicate_audit,
        "collection_spec_sha256": manifest.collection_spec_sha256,
        "dataset_sha256": manifest.dataset_sha256,
        "manifest_sha256": sha256_file(manifest_path),
        "episodes": published,
    }
    print(json.dumps(report, sort_keys=True))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--opponent-population", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--seed-base", type=int, required=True)
    parser.add_argument("--episodes-per-seat", type=int, default=1)
    parser.add_argument("--seat", choices=("0", "1", "both"), default="both")
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=MODEL_TIMEOUT_SECONDS,
        help=(
            "fixed Phase-0 train/deploy timeout; values other than "
            f"{MODEL_TIMEOUT_SECONDS:.3f} are rejected"
        ),
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--duplicate-audit", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.episodes_per_seat <= 0 or args.max_steps <= 0:
        raise ValueError("episode and max-step counts must be positive")
    collect(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
