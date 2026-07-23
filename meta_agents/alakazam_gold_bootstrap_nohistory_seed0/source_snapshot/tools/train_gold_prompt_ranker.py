"""Train and evaluate the leakage-safe Gold prompt behavior-cloning ranker."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rl_ptcg.gold_prompt_ranker import RankerConfig, evaluate_ranker, load_phase1_examples, save_ranker, train_ranker


def contained_path(raw: str, workspace: Path) -> Path:
    path = Path(raw)
    resolved = (path if path.is_absolute() else workspace / path).resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError as error:
        raise ValueError("path escapes workspace: %s" % raw) from error
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--archetype", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--feature-dim", type=int, default=256)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--no-style-embedding", action="store_true")
    parser.add_argument("--no-known-private", action="store_true")
    parser.add_argument("--no-public-history", action="store_true")
    parser.add_argument("--fit-development", action="store_true")
    args = parser.parse_args()
    workspace = Path(args.workspace_root).resolve()
    if not workspace.is_dir():
        raise ValueError("workspace root does not exist")
    dataset_dir = contained_path(args.dataset_dir, workspace)
    output_dir = contained_path(args.output_dir, workspace)
    config = RankerConfig(
        feature_dim=args.feature_dim,
        hidden_dim=args.hidden_dim,
        epochs=args.epochs,
        batch_size=args.batch_size,
        use_style_embedding=not args.no_style_embedding,
        include_known_private=not args.no_known_private,
        include_public_history=not args.no_public_history,
    )
    examples, hashes = load_phase1_examples(
        dataset_dir,
        archetype=args.archetype,
        allowed_splits=("train", "development", "policy_family_holdout"),
        feature_dim=config.feature_dim,
        include_known_private=config.include_known_private,
        include_public_history=config.include_public_history,
    )
    train = [item for item in examples if item.split == "train"]
    development = [item for item in examples if item.split == "development"]
    holdout = [item for item in examples if item.split == "policy_family_holdout"]
    fit = train + development if args.fit_development else train
    fit_splits = ("train", "development") if args.fit_development else ("train",)
    model, losses = train_ranker(
        fit,
        config=config,
        seed=args.seed,
        fit_splits=fit_splits,
    )
    counts = {"train": len(train), "development": len(development), "policy_family_holdout": len(holdout)}
    report = {
        "schema_version": "gold_prompt_ranker_evaluation.v1",
        "archetype": args.archetype,
        "counts": counts,
        "fit_splits": list(fit_splits),
        "loss": {
            "steps": len(losses),
            "first": losses[0],
            "last": losses[-1],
            "minimum": min(losses),
        },
        "fit": evaluate_ranker(model, fit),
        "train": evaluate_ranker(model, train),
        "development": evaluate_ranker(model, development),
        "policy_family_holdout": evaluate_ranker(model, holdout),
    }
    checkpoint, manifest = save_ranker(
        output_dir,
        model,
        config=config,
        seed=args.seed,
        counts=counts,
        source_hashes=hashes,
        evaluation_report=report,
        implementation_sources={
            "rl_ptcg/gold_prompt_ranker.py": ROOT / "rl_ptcg" / "gold_prompt_ranker.py",
            "tools/train_gold_prompt_ranker.py": Path(__file__).resolve(),
        },
    )
    print(json.dumps({
        "checkpoint": str(checkpoint),
        "manifest": str(manifest),
        "loss_steps": len(losses),
        "development": report["development"],
        "policy_family_holdout": report["policy_family_holdout"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
