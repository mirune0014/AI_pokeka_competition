"""Tune a rule-prior bonus on development and evaluate one policy holdout."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.rl_ptcg.gold_prompt_ranker import load_phase1_examples, load_ranker
from research.rl_ptcg.gold_prompt_rule_blend import (
    DEFAULT_ALPHA_GRID,
    SCHEMA_VERSION,
    build_rule_prior_map,
    evaluate_blend,
    file_sha256,
    load_audit_rows,
    load_rule_prior_records,
    select_alpha,
)


def contained(raw: str, workspace: Path) -> Path:
    path = Path(raw)
    resolved = (path if path.is_absolute() else workspace / path).resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError as error:
        raise ValueError("path escapes workspace: %s" % raw) from error
    return resolved


def write_once(path: Path, value: dict) -> None:
    data = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError("refusing to replace non-identical blend artifact")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--audit-dir", required=True)
    parser.add_argument("--ranker-dir", required=True)
    parser.add_argument("--archetype", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--alpha", action="append", type=float)
    parser.add_argument("--fixed-alpha", type=float)
    args = parser.parse_args()
    workspace = Path(args.workspace_root).resolve()
    if not workspace.is_dir():
        raise ValueError("workspace root does not exist")
    dataset = contained(args.dataset_dir, workspace)
    audit = contained(args.audit_dir, workspace)
    ranker = contained(args.ranker_dir, workspace)
    output = contained(args.output_dir, workspace)
    model = load_ranker(
        ranker / "gold_prompt_ranker.pt",
        ranker / "gold_prompt_ranker_manifest.json",
    )
    examples, dataset_hashes = load_phase1_examples(
        dataset,
        archetype=args.archetype,
        allowed_splits=("development", "policy_family_holdout"),
        feature_dim=model.config.feature_dim,
        include_known_private=model.config.include_known_private,
        include_public_history=model.config.include_public_history,
    )
    development = [item for item in examples if item.split == "development"]
    holdout = [item for item in examples if item.split == "policy_family_holdout"]
    audit_rows, audit_hashes = load_audit_rows(audit)
    records = load_rule_prior_records(
        dataset,
        archetype=args.archetype,
        allowed_splits=("development", "policy_family_holdout"),
    )
    priors = build_rule_prior_map(records, audit_rows)
    if args.fixed_alpha is not None and args.alpha:
        parser.error("--fixed-alpha cannot be combined with --alpha")
    if args.fixed_alpha is not None:
        if args.fixed_alpha < 0:
            parser.error("--fixed-alpha must be non-negative")
        selected, sweep = float(args.fixed_alpha), []
        grid = (selected,)
        selection_mode = "fixed_before_evaluation"
    else:
        grid = tuple(args.alpha) if args.alpha else DEFAULT_ALPHA_GRID
        selected, sweep = select_alpha(model, development, priors, grid)
        selection_mode = "development_sweep"
    report = {
        "schema_version": SCHEMA_VERSION,
        "archetype": args.archetype,
        "alpha_grid": list(sorted(set(float(value) for value in grid))),
        "selected_alpha": selected,
        "alpha_selection_mode": selection_mode,
        "development_sweep": sweep,
        "development": evaluate_blend(model, development, priors, alpha=selected),
        "policy_family_holdout": evaluate_blend(model, holdout, priors, alpha=selected),
    }
    report_path = output / "report.json"
    write_once(report_path, report)
    sources = {
        **dataset_hashes,
        **audit_hashes,
        "ranker_checkpoint_sha256": file_sha256(ranker / "gold_prompt_ranker.pt"),
        "ranker_manifest_sha256": file_sha256(ranker / "gold_prompt_ranker_manifest.json"),
        "ranker_evaluation_report_sha256": file_sha256(ranker / "evaluation_report.json"),
        "blend_module_sha256": file_sha256(ROOT / "research" / "rl_ptcg" / "gold_prompt_rule_blend.py"),
        "blend_cli_sha256": file_sha256(Path(__file__).resolve()),
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "report": report_path.name,
        "report_sha256": file_sha256(report_path),
        "sources": dict(sorted(sources.items())),
        "selected_alpha": selected,
        "counts": {
            "development": len(development),
            "policy_family_holdout": len(holdout),
            "rule_prior_rows": len(priors),
        },
        "command": list(sys.argv),
    }
    manifest["manifest_sha256"] = sha256((json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ) + "\n").encode("ascii")).hexdigest()
    write_once(output / "manifest.json", manifest)
    print(json.dumps({
        "output_dir": str(output),
        "selected_alpha": selected,
        "development": report["development"]["overall:overall"],
        "policy_family_holdout": report["policy_family_holdout"]["overall:overall"],
        "manifest_sha256": manifest["manifest_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
