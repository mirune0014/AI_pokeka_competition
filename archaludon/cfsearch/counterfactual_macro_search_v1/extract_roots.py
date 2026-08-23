"""Extract a small public root corpus for the counterfactual MVP."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from infrastructure.tools.ptcg_common import load_agent
from research.rl_ptcg.replay_reconstruction import iter_replay_decisions

from common import (
    canonical_sha256,
    file_sha256,
    find_replay_decision,
    public_root_descriptor,
    read_json,
    write_json,
    write_jsonl,
)


def _integer(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _candidate_roots(
    replay_path: Path,
    parent_dir: Path,
    *,
    min_turn: int,
    main_only: bool,
    module_tag: str,
) -> tuple[list[dict[str, Any]], int]:
    replay = read_json(replay_path)
    if not isinstance(replay, dict):
        raise ValueError(f"replay is not an object: {replay_path}")
    agent = load_agent(parent_dir, module_tag)
    candidates: list[dict[str, Any]] = []
    skipped = 0
    for decision in iter_replay_decisions(replay):
        if decision.turn is None or decision.turn < min_turn:
            continue
        select = decision.observation.get("select") or {}
        if main_only and (select.get("context") != 0 or select.get("type") != 0):
            continue
        if len(decision.raw_action) != 1:
            continue
        try:
            parent_action = agent(dict(decision.observation))
            descriptor = public_root_descriptor(decision, parent_action)
        except Exception:
            skipped += 1
            continue
        descriptor.update({
            "root_source_replay": str(replay_path.resolve()),
            "replay_sha256": file_sha256(replay_path),
            "parent_agent_dir": str(parent_dir.resolve()),
            "parent_main_sha256": file_sha256(parent_dir / "main.py"),
            "parent_deck_sha256": file_sha256(parent_dir / "deck.csv"),
        })
        candidates.append(descriptor)
    return candidates, skipped


def build_manifest(
    replay_paths: list[Path],
    parent_dir: Path,
    *,
    count: int,
    min_turn: int,
    main_only: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    skipped = 0
    seen: set[tuple[str, int, int]] = set()
    for replay_number, replay_path in enumerate(replay_paths):
        candidates, replay_skipped = _candidate_roots(
            replay_path,
            parent_dir,
            min_turn=min_turn,
            main_only=main_only,
            module_tag=f"cfsearch_extract_parent_{replay_number}",
        )
        skipped += replay_skipped
        for descriptor in candidates:
            key = (
                descriptor["replay_sha256"],
                int(descriptor["replay_step"]),
                int(descriptor["acting_seat"]),
            )
            if key in seen:
                continue
            seen.add(key)
            descriptor["root_id"] = f"root_{len(selected):03d}"
            selected.append(descriptor)
            if len(selected) >= count:
                break
        if len(selected) >= count:
            break
    if len(selected) < count:
        raise RuntimeError(
            f"only {len(selected)} usable roots found; requested {count} (skipped={skipped})"
        )
    meta = {
        "schema_version": "archaludon_counterfactual_root_manifest_meta.v1",
        "count": len(selected),
        "requested_count": count,
        "min_turn": min_turn,
        "main_only": main_only,
        "replay_paths": [str(path.resolve()) for path in replay_paths],
        "parent_agent_dir": str(parent_dir.resolve()),
        "selected_root_ids": [row["root_id"] for row in selected],
        "manifest_sha256": canonical_sha256(selected),
        "skipped_candidates": skipped,
    }
    return selected, meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", action="append", type=Path, required=True)
    parser.add_argument("--parent-agent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--min-turn", type=int, default=1)
    parser.add_argument(
        "--all-prompts",
        action="store_true",
        help="allow non-Main prompts; the default uses only context=0,type=0",
    )
    args = parser.parse_args()
    parent_dir = args.parent_agent.resolve()
    replay_paths = [path.resolve() for path in args.replay]
    if args.count < 1:
        raise SystemExit("--count must be positive")
    for path in replay_paths:
        if not path.is_file():
            raise SystemExit(f"replay not found: {path}")
    if not (parent_dir / "main.py").is_file() or not (parent_dir / "deck.csv").is_file():
        raise SystemExit(f"parent agent is incomplete: {parent_dir}")

    roots, meta = build_manifest(
        replay_paths,
        parent_dir,
        count=args.count,
        min_turn=args.min_turn,
        main_only=not args.all_prompts,
    )
    output = args.output.resolve()
    write_jsonl(output, roots)
    write_json(output.with_name("root_manifest_meta.json"), meta)
    print(json.dumps({
        "output": str(output),
        "roots": len(roots),
        "root_ids": [row["root_id"] for row in roots],
        "manifest_sha256": meta["manifest_sha256"],
        "skipped_candidates": meta["skipped_candidates"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
