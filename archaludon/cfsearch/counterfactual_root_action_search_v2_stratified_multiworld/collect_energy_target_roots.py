"""Collect public MAIN callbacks eligible for the T7 energy-target stratum.

This utility is evidence collection only.  It never edits the accepted parent,
does not create synthetic worlds, and does not infer an opponent policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
from common import file_sha256, legal_action, public_root_descriptor, read_json, write_json, write_jsonl
from common_v2 import energy_target_eligibility


def _seed(source_kind: str, opponent: str, seat: int, index: int) -> int:
    payload = f"energy-root-v1|{opponent}|{seat}|{index}".encode("utf-8")
    return int(hashlib.sha256(payload).hexdigest()[:8], 16)


def collect(replay_paths: list[Path], parent_dir: Path, source_kind: str, max_per_game: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    agent = load_agent(parent_dir, "energy_target_collection")
    rows: list[dict[str, Any]] = []
    skipped = 0
    callbacks = 0
    for replay_path in replay_paths:
        replay = read_json(replay_path)
        per_game = 0
        for callback_index, decision in enumerate(iter_replay_decisions(replay)):
            callbacks += 1
            if per_game >= max_per_game:
                break
            eligibility = energy_target_eligibility(decision.observation)
            if not eligibility["eligible"]:
                continue
            try:
                parent_action = agent(dict(decision.observation))
                if not legal_action(decision.observation, parent_action):
                    skipped += 1
                    continue
                descriptor = public_root_descriptor(decision, parent_action)
            except Exception:
                skipped += 1
                continue
            row = {
                "schema_version": "archaludon_energy_target_root.v2",
                "source_kind": source_kind,
                "episode_id": decision.episode_id,
                "replay_step": int(decision.replay_step),
                "callback_index": int(callback_index),
                "turn": decision.turn,
                "acting_seat": int(decision.acting_seat),
                "seed": _seed(source_kind, str(decision.episode_id), int(decision.acting_seat), per_game),
                "root_source_replay": str(replay_path.resolve()),
                "replay_sha256": file_sha256(replay_path),
                "target_observation_sha256": descriptor["target_observation_sha256"],
                "parent_action": descriptor["parent_action"],
                "parent_semantic_id": descriptor["parent_semantic_id"],
                "target_option_semantic_ids": descriptor["target_option_semantic_ids"],
                "energy_target_eligibility": eligibility,
            }
            rows.append(row)
            per_game += 1
    games = sorted({str(row["episode_id"]) for row in rows})
    report = {
        "schema_version": "archaludon_energy_target_collection_report.v2",
        "source_kind": source_kind,
        "replay_count": len(replay_paths),
        "callback_count": callbacks,
        "eligible_root_count": len(rows),
        "distinct_games": len(games),
        "distinct_game_ids": games,
        "skipped_after_eligibility": skipped,
        "status": "ENERGY_TARGET_STRUCTURALLY_SPARSE" if len(games) < 4 else "ELIGIBLE_FOR_T7_DISCOVERY",
        "parent_agent_dir": str(parent_dir.resolve()),
        "parent_main_sha256": file_sha256(parent_dir / "main.py"),
        "parent_deck_sha256": file_sha256(parent_dir / "deck.csv"),
        "no_synthetic_roots": True,
        "no_rule_adoption": True,
    }
    return rows, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", action="append", type=Path, default=[])
    parser.add_argument("--replay-list", type=Path, default=None)
    parser.add_argument("--parent-agent", type=Path, required=True)
    parser.add_argument("--source-kind", choices=("fixed760", "on_policy"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-roots-per-game", type=int, default=2)
    args = parser.parse_args()
    paths = [path.resolve() for path in args.replay]
    if args.replay_list is not None:
        paths.extend(Path(line.strip()).resolve() for line in args.replay_list.read_text(encoding="utf-8-sig").splitlines() if line.strip())
    if not paths or any(not path.is_file() for path in paths):
        raise SystemExit("every replay path must be a file")
    parent_dir = args.parent_agent.resolve()
    rows, report = collect(paths, parent_dir, args.source_kind, args.max_roots_per_game)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(output, rows)
    write_json(output.with_name("energy_target_collection_report.json"), report)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
