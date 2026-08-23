"""Replace a run's root ledger with an action-identical public-feature ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest().upper()


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--feature-selection", type=Path, required=True)
    args = parser.parse_args()
    run = args.run_dir.resolve(); source = args.feature_selection.resolve()
    old = rows(run / "selected_roots.jsonl"); new = rows(source / "selected_roots.jsonl")
    old_map = {str(row["root_id"]): row for row in old}; new_map = {str(row["root_id"]): row for row in new}
    if set(old_map) != set(new_map):
        raise SystemExit("feature ledger root IDs differ")
    invariant = ("public_hash", "callback_index", "parent_semantic_action", "boss_action", "boss_semantic_action", "front_attacks", "legal_semantic_action_set")
    for rid in old_map:
        for key in invariant:
            if old_map[rid].get(key) != new_map[rid].get(key):
                raise SystemExit(f"action/root invariant changed for {rid}: {key}")
    target = run / "selected_roots.jsonl"
    target.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n" for row in new), encoding="utf-8")
    (run / "selection_summary.json").write_bytes((source / "selection_summary.json").read_bytes())
    spec_path = run / "comparison_spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["selected_roots"] = str(target)
    spec["selected_roots_sha256"] = digest(target)
    spec["public_feature_ledger"] = "selected_roots.jsonl includes only callback-visible metadata; action/root invariants verified against the original ledger"
    spec_path.write_text(json.dumps(spec, sort_keys=True, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"root_count": len(new), "selected_roots_sha256": digest(target), "feature_source_sha256": digest(source / "selected_roots.jsonl"), "invariants": list(invariant)}, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    main()
