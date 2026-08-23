"""Collect T7 attach-target roots from formal fixed760 callback traces."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
V1_DIR = HERE.parent / "counterfactual_macro_search_v1"
for path in (REPO_ROOT, V1_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from common import legal_action, observation_hash
from common_v2 import energy_target_eligibility, public_context_tags


def _split(schedule_key: str, callback_index: int, public_hash: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"{schedule_key}|{callback_index}|{public_hash}".encode("utf-8")).hexdigest()
    bucket = int(digest, 16) % 100
    return ("discovery" if bucket <= 64 else "holdout" if bucket <= 89 else "reserve"), digest


def collect(trace_root: Path, output: Path, schedule_key: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[str, ...], str]] = set()
    callback_count = 0
    for trace_path in sorted(trace_root.glob("**/traces/**/game_*.jsonl")):
        for line in trace_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            callback_count += 1
            row = json.loads(line)
            observation = row.get("observation") or {}
            if int(row.get("acting_seat", -1)) != int(row.get("policy_seat", -2)):
                continue
            eligibility = energy_target_eligibility(observation)
            if not eligibility.get("eligible"):
                continue
            action = row.get("raw_action")
            if not legal_action(observation, action or []):
                continue
            semantic_set = tuple(sorted(str(item.get("semantic_id")) for item in row.get("legal_semantic_action_set") or []))
            key = (str(row.get("public_hash") or observation_hash(observation)), str(row.get("parent_semantic_action")), semantic_set, str(row.get("opponent_family")))
            if key in seen:
                continue
            seen.add(key)
            split, split_hash = _split(schedule_key, int(row.get("callback_index") or 0), str(row.get("public_hash")))
            root_index = len(rows)
            rows.append({
                "schema_version": "archaludon_formal_realized_t7_root.v1",
                "source_kind": "FORMAL_REALIZED_SEEDED_WORLD",
                "schedule_key": schedule_key,
                "split": split,
                "split_hash": split_hash,
                "root_id": f"{split}_{root_index:05d}_{row.get('opponent_family')}_p{row.get('policy_seat')}_g{row.get('game')}_c{row.get('callback_index')}",
                "trace_path": str(trace_path.resolve()),
                "callback_index": int(row.get("callback_index")),
                "game": int(row.get("game")),
                "seed": int(row.get("seed")),
                "panel": row.get("panel"),
                "opponent_family": row.get("opponent_family"),
                "opponent_policy_id": row.get("opponent_policy_id"),
                "opponent_path": row.get("opponent_path"),
                "opponent_deck_path": row.get("opponent_deck_path"),
                "policy_seat": int(row.get("policy_seat")),
                "acting_seat": int(row.get("acting_seat")),
                "turn": row.get("turn"),
                "turnActionCount": row.get("turnActionCount"),
                "public_hash": row.get("public_hash"),
                "parent_action": list(action),
                "parent_semantic_action": row.get("parent_semantic_action"),
                "legal_semantic_action_set": row.get("legal_semantic_action_set") or [],
                "alternative_semantics": [
                    {
                        "semantic_id": item.get("semantic_id"),
                        "action": item.get("action"),
                        "transformation": item.get("transformation"),
                    }
                    for item in row.get("transformation_candidates") or []
                    if item.get("transformation") == "T7_ATTACH_TARGET_CHANGE"
                ],
                "context_tags": public_context_tags(observation),
                "energy_target_eligibility": eligibility,
            })
    output.mkdir(parents=True, exist_ok=True)
    (output / "t7_roots.jsonl").write_text("".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows), encoding="utf-8", newline="\n")
    split_counts = {name: sum(row["split"] == name for row in rows) for name in ("discovery", "holdout", "reserve")}
    report = {
        "schema_version": "archaludon_formal_realized_t7_root_collection.v1",
        "source_kind": "FORMAL_REALIZED_SEEDED_WORLD",
        "trace_root": str(trace_root.resolve()),
        "schedule_key": schedule_key,
        "callback_count": callback_count,
        "eligible_root_count": len(rows),
        "distinct_games": len({(str(row.get("opponent_family")), int(row.get("seed"))) for row in rows}),
        "opponent_families": sorted({str(row.get("opponent_family")) for row in rows}),
        "seats": sorted({int(row.get("policy_seat")) for row in rows}),
        "split_counts": split_counts,
        "no_synthetic_worlds": True,
        "formal_world_method": "re-run_same_seed_prefix_replace_one_root_action_then_parent_resume",
    }
    (output / "REPORT.json").write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--schedule-key", required=True)
    args = parser.parse_args()
    report = collect(args.trace_root.resolve(), args.output.resolve(), args.schedule_key)
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
