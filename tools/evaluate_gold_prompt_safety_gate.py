"""Select a Gold prompt override safety gate on development and freeze it for holdout."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys

import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rl_ptcg.gold_prompt_ranker import load_phase1_examples, load_ranker
from rl_ptcg.gold_prompt_rule_blend import build_rule_prior_map, load_audit_rows, load_rule_prior_records
from rl_ptcg.gold_prompt_safety_gate import (DEFAULT_CONFIDENCE_Z, DEFAULT_THRESHOLD_GRID, SCHEMA_VERSION,
    apply_gate, canonical_bytes, decision_diagnostics, evaluate_gate, file_sha256, select_rules,
    validate_ranker_evaluation_report, validate_thresholds, validate_wilson_settings, write_once, write_json_once)


def contained(raw: str, workspace: Path) -> Path:
    path = Path(raw)
    resolved = (path if path.is_absolute() else workspace / path).resolve()
    try:
        resolved.relative_to(workspace)
    except ValueError as error:
        raise ValueError("path escapes workspace: %s" % raw) from error
    return resolved


def relative(path: Path, workspace: Path) -> str:
    return str(path.resolve().relative_to(workspace)).replace("\\", "/")


def read_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("could not read gate artifact: %s" % path) from error
    if not isinstance(value, dict):
        raise ValueError("gate artifact is not an object: %s" % path)
    return value


def verify_artifact(output: Path, workspace: Path) -> dict:
    manifest_path = output / "manifest.json"
    manifest = read_object(manifest_path)
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    expected_self = sha256(canonical_bytes(unsigned)).hexdigest()
    if (
        manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("manifest_sha256") != expected_self
    ):
        raise ValueError("gate manifest self-hash mismatch")
    output_files = {
        "gate.json": "gate_sha256",
        "report.json": "report_sha256",
        "rows.jsonl": "rows_sha256",
    }
    for name, field in output_files.items():
        path = output / name
        if not path.is_file() or manifest.get(field) != file_sha256(path):
            raise ValueError("gate output hash mismatch: %s" % name)
    for label, binding in manifest.get("input_files", {}).items():
        if not isinstance(binding, dict):
            raise ValueError("invalid input binding: %s" % label)
        path = contained(str(binding.get("path", "")), workspace)
        if not path.is_file() or binding.get("sha256") != file_sha256(path):
            raise ValueError("gate input hash mismatch: %s" % label)
    implementation_drift = []
    for name, binding in manifest.get("implementation", {}).items():
        if not isinstance(binding, dict):
            raise ValueError("invalid implementation binding: %s" % name)
        snapshot = output / str(binding.get("snapshot", ""))
        if (
            not snapshot.is_file()
            or binding.get("snapshot_sha256") != file_sha256(snapshot)
            or binding.get("source_sha256") != binding.get("snapshot_sha256")
        ):
            raise ValueError("implementation snapshot mismatch: %s" % name)
        source = contained(str(binding.get("source_path", "")), workspace)
        if not source.is_file() or file_sha256(source) != binding.get("source_sha256"):
            implementation_drift.append(name)
    gate = read_object(output / "gate.json")
    report = read_object(output / "report.json")
    if gate.get("schema_version") != SCHEMA_VERSION or report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("gate/report schema mismatch")
    if gate.get("archetype") != manifest.get("archetype") or gate.get("rules") is None:
        raise ValueError("gate payload does not match manifest")
    rows = []
    for line_number, line in enumerate((output / "rows.jsonl").read_text(encoding="ascii").splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError("invalid gate row %d" % line_number) from error
        if row.get("split") not in {"development", "policy_family_holdout"}:
            raise ValueError("gate rows contain a forbidden split")
        rows.append(row)
    counts = manifest.get("counts", {})
    if (
        len({str(row.get("decision_id")) for row in rows}) != len(rows)
        or sum(row["split"] == "development" for row in rows) != counts.get("development")
        or sum(row["split"] == "policy_family_holdout" for row in rows) != counts.get("policy_family_holdout")
    ):
        raise ValueError("gate row counts or decision IDs mismatch")
    return {
        "manifest_sha256": manifest["manifest_sha256"],
        "rows": len(rows),
        "implementation_drift": sorted(implementation_drift),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir")
    parser.add_argument("--audit-dir")
    parser.add_argument("--ranker-dir")
    parser.add_argument("--archetype")
    parser.add_argument("--output-dir")
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--verify-only")
    parser.add_argument("--threshold", action="append", type=float)
    parser.add_argument("--min-discordant", type=int, default=10)
    parser.add_argument("--confidence-z", type=float, default=DEFAULT_CONFIDENCE_Z)
    parser.add_argument("--min-improvement-probability", type=float, default=0.5)
    args = parser.parse_args()
    workspace = Path(args.workspace_root).resolve()
    if not workspace.is_dir():
        raise ValueError("workspace root does not exist")
    if args.verify_only is not None:
        print(json.dumps(verify_artifact(contained(args.verify_only, workspace), workspace), sort_keys=True))
        return
    required = ("dataset_dir", "audit_dir", "ranker_dir", "archetype", "output_dir")
    missing = ["--" + name.replace("_", "-") for name in required if not getattr(args, name)]
    if missing:
        parser.error("required arguments: %s" % ", ".join(missing))
    dataset, audit, ranker, output = (contained(value, workspace) for value in
                                      (args.dataset_dir, args.audit_dir, args.ranker_dir, args.output_dir))
    thresholds = validate_thresholds(args.threshold if args.threshold is not None else DEFAULT_THRESHOLD_GRID)
    validate_wilson_settings(args.min_discordant, args.confidence_z, args.min_improvement_probability)
    evaluation_report = validate_ranker_evaluation_report(ranker / "evaluation_report.json")
    model = load_ranker(ranker / "gold_prompt_ranker.pt", ranker / "gold_prompt_ranker_manifest.json")
    development_examples, dataset_hashes = load_phase1_examples(
        dataset, archetype=args.archetype, allowed_splits=("development",),
        feature_dim=model.config.feature_dim,
        include_known_private=model.config.include_known_private,
        include_public_history=model.config.include_public_history,
    )
    audit_rows, audit_hashes = load_audit_rows(audit)
    development_records = load_rule_prior_records(
        dataset, archetype=args.archetype, allowed_splits=("development",),
    )
    development_priors = build_rule_prior_map(development_records, audit_rows)
    development = decision_diagnostics(model, development_examples, development_priors)
    rules, sweep = select_rules(development, thresholds=thresholds, min_discordant=args.min_discordant,
                                confidence_z=args.confidence_z,
                                min_improvement_probability=args.min_improvement_probability)
    # The gate is frozen before any policy-family holdout payload is parsed.
    holdout_examples, holdout_hashes = load_phase1_examples(
        dataset, archetype=args.archetype, allowed_splits=("policy_family_holdout",),
        feature_dim=model.config.feature_dim,
        include_known_private=model.config.include_known_private,
        include_public_history=model.config.include_public_history,
    )
    if holdout_hashes != dataset_hashes:
        raise ValueError("dataset bindings changed between gate selection and holdout evaluation")
    holdout_records = load_rule_prior_records(
        dataset, archetype=args.archetype, allowed_splits=("policy_family_holdout",),
    )
    holdout_priors = build_rule_prior_map(holdout_records, audit_rows)
    holdout = decision_diagnostics(model, holdout_examples, holdout_priors)
    raw_rows = development + holdout
    priors = {**development_priors, **holdout_priors}
    rows = apply_gate(raw_rows, rules)
    gate = {"schema_version": SCHEMA_VERSION, "archetype": args.archetype,
            "thresholds": list(thresholds), "min_discordant": args.min_discordant,
            "confidence_z": args.confidence_z, "min_improvement_probability": args.min_improvement_probability,
            "rules": rules, "development_sweep": sweep}
    report = {"schema_version": SCHEMA_VERSION, "archetype": args.archetype,
              "development": evaluate_gate([row for row in rows if row["split"] == "development"]),
              "policy_family_holdout": evaluate_gate([row for row in rows if row["split"] == "policy_family_holdout"])}
    write_json_once(output / "gate.json", gate)
    write_json_once(output / "report.json", report)
    write_once(output / "rows.jsonl", b"".join(canonical_bytes(row) for row in rows))
    implementation = {"rl_ptcg/gold_prompt_safety_gate.py": ROOT / "rl_ptcg" / "gold_prompt_safety_gate.py",
                      "tools/evaluate_gold_prompt_safety_gate.py": Path(__file__).resolve()}
    snapshots = {}
    for source_name, source in implementation.items():
        snapshot = output / "source_snapshot" / source_name
        write_once(snapshot, source.read_bytes())
        snapshots[source_name] = {"source_sha256": file_sha256(source),
                               "source_path": source_name,
                               "snapshot": str(snapshot.relative_to(output)).replace("\\", "/"),
                               "snapshot_sha256": file_sha256(snapshot)}
    sources = {**dataset_hashes, **audit_hashes,
               "ranker_checkpoint_sha256": file_sha256(ranker / "gold_prompt_ranker.pt"),
               "ranker_manifest_sha256": file_sha256(ranker / "gold_prompt_ranker_manifest.json"),
               "ranker_evaluation_report_sha256": file_sha256(ranker / "evaluation_report.json")}
    input_paths = {
        "dataset_manifest": dataset / "dataset_manifest.json",
        "decision_records": dataset / "decision_records.jsonl",
        "split_manifest": dataset / "split_manifest.json",
        "audit_checksum_manifest": audit / "checksum_manifest.json",
        "audit_rows": audit / "rows.jsonl",
        "audit_report": audit / "report.json",
        "audit_sample_manifest": audit / "sample_manifest.json",
        "ranker_checkpoint": ranker / "gold_prompt_ranker.pt",
        "ranker_manifest": ranker / "gold_prompt_ranker_manifest.json",
        "ranker_evaluation_report": ranker / "evaluation_report.json",
    }
    manifest = {"schema_version": SCHEMA_VERSION, "archetype": args.archetype,
                "gate_sha256": file_sha256(output / "gate.json"), "report_sha256": file_sha256(output / "report.json"),
                "rows_sha256": file_sha256(output / "rows.jsonl"), "sources": dict(sorted(sources.items())),
                "implementation": snapshots, "ranker_fit_splits": evaluation_report["fit_splits"],
                "input_files": {
                    name: {"path": relative(path, workspace), "sha256": file_sha256(path)}
                    for name, path in sorted(input_paths.items())
                },
                "command": list(sys.argv), "config": {"thresholds": list(thresholds), "min_discordant": args.min_discordant,
                    "confidence_z": args.confidence_z, "min_improvement_probability": args.min_improvement_probability},
                "counts": {"development": len(development), "policy_family_holdout": len(holdout), "priors": len(priors)},
                "environment": {"python": sys.version, "platform": platform.platform(),
                                "torch": str(torch.__version__)}}
    manifest["manifest_sha256"] = sha256(canonical_bytes(manifest)).hexdigest()
    write_json_once(output / "manifest.json", manifest)
    print(json.dumps({"output_dir": str(output), "manifest_sha256": manifest["manifest_sha256"],
                      "holdout": report["policy_family_holdout"].get("overall:overall", {})}, sort_keys=True))


if __name__ == "__main__":
    main()
