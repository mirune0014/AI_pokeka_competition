"""Extract deterministic public roots into discovery and untouched holdout strata."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
V1_DIR = HERE.parent / "counterfactual_macro_search_v1"
for path in (REPO_ROOT, V1_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from infrastructure.tools.ptcg_common import load_agent
from research.rl_ptcg.replay_reconstruction import iter_replay_decisions
from common import file_sha256, public_root_descriptor, read_json, write_json, write_jsonl
from common_v2 import (
    ACTION_TRANSFORMATIONS,
    CONTEXT_TAGS,
    STRATA,
    action_transformation,
    classify_root,
    energy_target_eligibility,
    public_context_tags,
)


def _candidate_roots(replay_path: Path, parent_dir: Path, agent: Any, min_turn: int, main_only: bool) -> tuple[list[dict[str, Any]], int]:
    replay = read_json(replay_path)
    rows: list[dict[str, Any]] = []
    skipped = 0
    for callback_index, decision in enumerate(iter_replay_decisions(replay)):
        if decision.turn is None or decision.turn < min_turn or len(decision.raw_action) != 1:
            continue
        select = decision.observation.get("select") or {}
        if main_only and (select.get("context") != 0 or select.get("type") != 0):
            continue
        try:
            parent_action = agent(dict(decision.observation))
            descriptor = public_root_descriptor(decision, parent_action)
            stratum, basis, families = classify_root(decision.observation, descriptor["target_option_semantic_ids"])
            transformations = []
            for alternative in descriptor["alternatives"]:
                transformation = action_transformation(decision.observation, parent_action, alternative["action"])
                # Keep the transformation attached to the individual legal
                # alternative.  A set-level summary is insufficient for the
                # later root/world and pattern aggregates.
                alternative["action_transformation"] = transformation
                transformations.append(transformation)
        except Exception:
            skipped += 1
            continue
        descriptor.update({
            "root_source_replay": str(replay_path.resolve()),
            "replay_sha256": file_sha256(replay_path),
            "callback_index": int(callback_index),
            "parent_agent_dir": str(parent_dir.resolve()),
            "parent_main_sha256": file_sha256(parent_dir / "main.py"),
            "parent_deck_sha256": file_sha256(parent_dir / "deck.csv"),
            "stratum": stratum,
            "classification_basis": basis,
            "visible_option_families": families,
            "action_transformations": sorted(set(transformations)),
            "context_tags": public_context_tags(decision.observation),
            "energy_target_eligibility": energy_target_eligibility(decision.observation),
        })
        rows.append(descriptor)
    return rows, skipped


def _root_key(row: dict[str, Any]) -> tuple[str, str, tuple[str, ...]]:
    return (
        row["target_observation_sha256"],
        str(row["parent_semantic_id"]),
        tuple(row["target_option_semantic_ids"]),
    )


def _callback_key(row: dict[str, Any]) -> tuple[str, int, int, str]:
    return (str(row["episode_id"]), int(row["replay_step"]), int(row["acting_seat"]), row["target_observation_sha256"])


def _split_for(row: dict[str, Any], schedule_key: str) -> tuple[str, str]:
    payload = f"{schedule_key}|{row.get('callback_index', row['replay_step'])}|{row['target_observation_sha256']}".encode("utf-8")
    digest = sha256(payload).hexdigest()
    bucket = int(digest, 16) % 100
    split = "discovery" if bucket <= 64 else "holdout" if bucket <= 89 else "reserve"
    return split, digest


def _read_excluded_manifests(paths: list[Path]) -> set[tuple[str, str, tuple[str, ...]]]:
    excluded: set[tuple[str, str, tuple[str, ...]]] = set()
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row, dict) and row.get("target_observation_sha256"):
                excluded.add(_root_key(row))
    return excluded


def build_manifest(replay_paths: list[Path], parent_dir: Path, *, min_turn: int, main_only: bool, discovery_target: int, holdout_target: int, reserve_target: int, schedule_key: str, excluded_manifests: list[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows_by_family: dict[tuple[str, str, tuple[str, ...]], list[dict[str, Any]]] = {}
    seen_callbacks: set[tuple[str, int, int, str]] = set()
    excluded = _read_excluded_manifests(excluded_manifests)
    skipped = 0
    agent = load_agent(parent_dir, "cfsearch_v2_extract_parent")
    for replay_path in replay_paths:
        rows, replay_skipped = _candidate_roots(replay_path, parent_dir, agent, min_turn, main_only)
        skipped += replay_skipped
        for row in rows:
            # The same public episode is copied into many refresh folders.  Do
            # not count those copies as distinct roots; deduplicate by the
            # public episode/step/seat/observation contract instead of the
            # storage file hash.
            key = _callback_key(row)
            if key in seen_callbacks or _root_key(row) in excluded:
                continue
            seen_callbacks.add(key)
            family = _root_key(row)
            bucket = rows_by_family.setdefault(family, [])
            if len(bucket) < 2:
                bucket.append(row)
    candidates = [row for bucket in rows_by_family.values() for row in bucket]
    # Deterministic balancing: prefer transformations that currently have
    # fewer fresh rows, then fewer opponent/seat examples, then split hash.
    transform_counts: dict[str, int] = {name: 0 for name in ACTION_TRANSFORMATIONS}
    for row in candidates:
        for name in row.get("action_transformations", []):
            transform_counts[name] = transform_counts.get(name, 0) + 1
    candidates.sort(key=lambda row: (
        min(transform_counts.get(name, 0) for name in row.get("action_transformations", ["T13_OTHER"])),
        int(row["acting_seat"]),
        str(row["episode_id"]),
        int(row["replay_step"]),
    ))
    selected: list[dict[str, Any]] = []
    split_counts = {"discovery": 0, "holdout": 0, "reserve": 0}
    for row in candidates:
        split, split_hash = _split_for(row, schedule_key)
        if split_counts[split] >= {"discovery": discovery_target, "holdout": holdout_target, "reserve": reserve_target}[split]:
            continue
        row = dict(row)
        row["split"] = split
        row["split_hash"] = split_hash
        row["root_id"] = f"{split}_{len([item for item in selected if item['split'] == split]):04d}"
        selected.append(row)
        split_counts[split] += 1
    deficits = {name: {"available_selected": split_counts[name], "requested": target, "deficit": max(0, target - split_counts[name])} for name, target in (("discovery", discovery_target), ("holdout", holdout_target), ("reserve", reserve_target))}
    meta = {
        "schema_version": "archaludon_counterfactual_root_manifest_v2_1_transformation_split.v1",
        "action_transformations": list(ACTION_TRANSFORMATIONS),
        "context_tags": list(CONTEXT_TAGS),
        "schedule_key": schedule_key,
        "discovery_count": split_counts["discovery"],
        "holdout_count": split_counts["holdout"],
        "reserve_count": split_counts["reserve"],
        "requested_discovery_count": discovery_target,
        "requested_holdout_count": holdout_target,
        "requested_reserve_count": reserve_target,
        "deficits": deficits,
        "strict_coverage": all(item["deficit"] == 0 for item in deficits.values()),
        "calibration_excluded_count": len(excluded),
        "candidate_family_count": len(rows_by_family),
        "replay_paths": [str(path.resolve()) for path in replay_paths],
        "parent_agent_dir": str(parent_dir.resolve()),
        "skipped_candidates": skipped,
    }
    return selected, meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", action="append", type=Path, default=[])
    parser.add_argument(
        "--replay-list",
        type=Path,
        default=None,
        help="newline-delimited replay paths; may be combined with --replay",
    )
    parser.add_argument("--parent-agent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-turn", type=int, default=1)
    parser.add_argument("--all-prompts", action="store_true")
    parser.add_argument("--discovery-target", type=int, default=48)
    parser.add_argument("--holdout-target", type=int, default=24)
    parser.add_argument("--reserve-target", type=int, default=16)
    parser.add_argument("--schedule-key", default="archaludon_historical_silver_fresh_v2_1")
    parser.add_argument("--exclude-manifest", action="append", type=Path, default=[])
    parser.add_argument("--fail-on-shortfall", action="store_true")
    args = parser.parse_args()
    if min(args.discovery_target, args.holdout_target, args.reserve_target) < 0:
        raise SystemExit("split counts must be non-negative")
    parent_dir = args.parent_agent.resolve()
    replay_paths = [path.resolve() for path in args.replay]
    if args.replay_list is not None:
        replay_paths.extend(
            Path(line.strip()).resolve()
            for line in args.replay_list.read_text(encoding="utf-8-sig").splitlines()
            if line.strip()
        )
    if not replay_paths or any(not path.is_file() for path in replay_paths):
        raise SystemExit("every replay path must be a file")
    if not (parent_dir / "main.py").is_file() or not (parent_dir / "deck.csv").is_file():
        raise SystemExit(f"parent agent is incomplete: {parent_dir}")
    rows, meta = build_manifest(replay_paths, parent_dir, min_turn=args.min_turn, main_only=not args.all_prompts, discovery_target=args.discovery_target, holdout_target=args.holdout_target, reserve_target=args.reserve_target, schedule_key=args.schedule_key, excluded_manifests=[path.resolve() for path in args.exclude_manifest])
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output, rows)
    for split in ("discovery", "holdout", "reserve"):
        write_jsonl(output.with_name(f"root_manifest_{split}.jsonl"), [row for row in rows if row["split"] == split])
    meta["manifest_sha256"] = file_sha256(output)
    write_json(output.with_name("root_manifest_meta.json"), meta)
    print(json.dumps({"output": str(output), **{key: meta[key] for key in ("discovery_count", "holdout_count", "reserve_count", "strict_coverage", "deficits", "manifest_sha256")}}, sort_keys=True))
    if args.fail_on_shortfall and not meta["strict_coverage"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
